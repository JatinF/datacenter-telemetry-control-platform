"""Own the simulated hall, the loopback servers, and the command audit."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime

from dc_telemetry.adapters import (
    AdapterError,
    fetch_redfish,
    in_process_modbus,
    in_process_redfish,
    in_process_sim,
    normalize_modbus,
    normalize_redfish,
    read_holding,
)
from dc_telemetry.control import AuthError, Command, role_for
from dc_telemetry.hall import (
    NOTICE,
    RACK,
    SENSOR_ID,
    SITE,
    TEMPERATURE_ALERT_C,
    Hall,
    bench_devices,
    demo_devices,
    pdu_registers,
    redfish_power,
    redfish_system,
    redfish_thermal,
)
from dc_telemetry.metrics import Instruments
from dc_telemetry.modbus_sim import ModbusSim
from dc_telemetry.models import Device, Reading
from dc_telemetry.redfish_sim import RedfishSim, encode
from dc_telemetry.store import MemoryStore

Clock = Callable[[], str]


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Lab:
    def __init__(
        self,
        profile: str = "demo",
        clock: Clock | None = None,
        device_count: int = 100,
    ) -> None:
        self.profile = profile
        self.clock = clock or utc_now
        self.store = MemoryStore()
        self.instruments = Instruments()
        self.alerts: list[dict[str, object]] = []
        self.samples: list[float] = []
        self.commands: dict[str, Command] = {}
        self._seq = 0
        self._lock = threading.Lock()
        self._redfish: RedfishSim | None = None
        self._modbus: ModbusSim | None = None
        self._closed = False
        if profile == "bench":
            self.hall = Hall(bench_devices(device_count))
        else:
            self._redfish = RedfishSim(self)
            self._modbus = ModbusSim(pdu_registers(False))
            self.hall = Hall(demo_devices(self._redfish.port, self._modbus.port))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._redfish is not None:
            self._redfish.close()
        if self._modbus is not None:
            self._modbus.close()

    def redfish_body(self, path: str) -> bytes:
        fault = self.hall.faulty(self.hall.devices[0].device_id) if self.hall.devices else False
        server = next(item for item in self.hall.devices if item.kind == "server" and item.live)
        if path == "/redfish/v1/Systems/1":
            return encode(redfish_system(server.device_id, fault))
        if path == "/redfish/v1/Chassis/1/Thermal":
            return encode(redfish_thermal(fault))
        if path == "/redfish/v1/Chassis/1/Power":
            return encode(redfish_power())
        return encode({"error": "unknown"})

    def discover(self) -> list[Device]:
        return list(self.hall.devices)

    def inject_fault(self, device_id: str) -> None:
        device = self.hall.device(device_id)
        if device is None:
            raise KeyError(device_id)
        self.hall.faults.add(device_id)
        if device.kind == "pdu" and self._modbus is not None and device.live:
            self._modbus.update(pdu_registers(True))

    def collect(self, device: Device, timeout: float = 1.0) -> list[Reading]:
        started = time.perf_counter()
        timestamp = self.clock()
        try:
            readings = self._read(device, timestamp, timeout)
        except AdapterError as exc:
            elapsed = time.perf_counter() - started
            self.samples.append(elapsed)
            self.instruments.errors.labels(kind=exc.kind).inc()
            self.instruments.latency.observe(elapsed)
            raise
        elapsed = time.perf_counter() - started
        self.samples.append(elapsed)
        self.store.add(readings)
        self.instruments.readings.inc(len(readings))
        self.instruments.latency.observe(elapsed)
        self._raise_alerts(readings)
        return readings

    def collect_all(self, timeout: float = 1.0) -> dict[str, int]:
        errors = 0
        stored = 0
        for device in self.hall.devices:
            try:
                stored += len(self.collect(device, timeout))
            except AdapterError:
                errors += 1
        return {"stored": stored, "errors": errors, "drops": 0, "devices": len(self.hall.devices)}

    def _read(self, device: Device, timestamp: str, timeout: float) -> list[Reading]:
        fault = self.hall.faulty(device.device_id)
        if device.live and device.protocol == "redfish":
            thermal, power = fetch_redfish(device.host, device.port, timeout)
            return normalize_redfish(
                device.device_id,
                thermal,
                power,
                timestamp,
                "loopback-redfish",
            )
        if device.live and device.protocol == "modbus":
            registers = read_holding(device.host, device.port, timeout)
            return normalize_modbus(device.device_id, registers, timestamp, "loopback-modbus")
        if device.protocol == "redfish-document":
            return in_process_redfish(device, fault, timestamp)
        if device.protocol == "modbus-registers":
            return in_process_modbus(device, fault, timestamp)
        return in_process_sim(device, fault, timestamp)

    def _raise_alerts(self, readings: list[Reading]) -> None:
        existing = {
            (str(item["device_id"]), str(item["metric"]), str(item["reason"]))
            for item in self.alerts
        }
        for reading in readings:
            hot = reading.metric.endswith("temperature_c") and reading.value >= TEMPERATURE_ALERT_C
            if reading.quality != "bad" and not hot:
                continue
            reason = "temperature" if hot else "quality"
            key = (reading.device_id, reading.metric, reason)
            if key in existing:
                continue
            existing.add(key)
            self.alerts.append(
                {
                    "device_id": reading.device_id,
                    "metric": reading.metric,
                    "reason": reason,
                    "timestamp": reading.timestamp,
                    "state": "active",
                }
            )

    def rack_health(self, rack_id: str) -> dict[str, object]:
        devices = [item for item in self.hall.devices if item.rack_id == rack_id]
        qualities: list[str] = []
        for device in devices:
            qualities.extend(row.quality for row in self.store.latest(device.device_id))
        worst = "bad" if "bad" in qualities else "good"
        active = [item for item in self.alerts if item.get("state") == "active"]
        return {
            "rack_id": rack_id,
            "site": SITE,
            "devices": len(devices),
            "worst_quality": worst if qualities else "unknown",
            "active_alerts": len(active),
        }

    def submit_command(
        self,
        authorization: str | None,
        device_id: str,
        duty_percent: int,
    ) -> Command:
        role = role_for(authorization)
        if role != "operator":
            self._audit_denial(device_id, role, "submit")
            raise AuthError(403)
        device = self.hall.device(device_id)
        if device is None or device.kind != "server":
            raise KeyError(device_id)
        with self._lock:
            self._seq += 1
            command_id = f"SYN-CMD-{self._seq:04d}"
        command = Command(command_id, device_id, "set_fan_duty", duty_percent, "pending", role)
        command.audit.append({"actor": role, "event": "submitted", "state": "pending"})
        self.commands[command_id] = command
        return command

    def decide_command(self, authorization: str | None, command_id: str, decision: str) -> Command:
        role = role_for(authorization)
        command = self.commands.get(command_id)
        if command is None:
            raise KeyError(command_id)
        if role != "approver" or decision != "approve":
            command.audit.append({"actor": role, "event": "denied", "state": command.state})
            raise AuthError(403)
        if command.state != "pending":
            raise AuthError(409)
        self.hall.fan_duty[command.device_id] = command.duty_percent
        command.state = "executed-in-simulation"
        command.decided_by = role
        command.audit.append({"actor": role, "event": "approved", "state": command.state})
        return command

    def _audit_denial(self, device_id: str, role: str, event: str) -> None:
        with self._lock:
            self._seq += 1
            command_id = f"SYN-CMD-{self._seq:04d}"
        command = Command(command_id, device_id, "set_fan_duty", 0, "rejected", role)
        command.audit.append({"actor": role, "event": event, "state": "rejected"})
        self.commands[command_id] = command

    def status(self) -> dict[str, object]:
        return {
            "site": SITE,
            "notice": NOTICE,
            "rack": RACK,
            "sensor": SENSOR_ID,
            "profile": self.profile,
        }


