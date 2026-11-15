"""Read loopback simulators and normalize them. Non-loopback hosts are refused."""

from __future__ import annotations

import json
import socket
from http.client import HTTPConnection
from typing import Any

from pymodbus.client import ModbusTcpClient

from dc_telemetry.hall import (
    cooling_points,
    pdu_registers,
    redfish_power,
    redfish_system,
    redfish_thermal,
    sensor_points,
)
from dc_telemetry.models import Device, Reading
from dc_telemetry.safety import require_loopback


class AdapterError(Exception):
    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


def normalize_redfish(
    device_id: str,
    thermal: dict[str, Any],
    power: dict[str, Any],
    timestamp: str,
    source: str,
) -> list[Reading]:
    readings: list[Reading] = []
    fans = thermal.get("Fans", [])
    if isinstance(fans, list):
        for fan in fans:
            if isinstance(fan, dict) and isinstance(fan.get("Reading"), (int, float)):
                readings.append(
                    Reading(
                        device_id,
                        "redfish",
                        "fan_rpm",
                        float(fan["Reading"]),
                        "RPM",
                        "good",
                        timestamp,
                        source,
                    )
                )
    temps = thermal.get("Temperatures", [])
    if isinstance(temps, list):
        for temp in temps:
            celsius = temp.get("ReadingCelsius") if isinstance(temp, dict) else None
            if not isinstance(temp, dict) or not isinstance(celsius, (int, float)):
                continue
            name = str(temp.get("Name", "temp")).lower()
            metric = "intake_temperature_c" if name == "intake" else "exhaust_temperature_c"
            quality = str(temp.get("Quality", "good"))
            readings.append(
                Reading(
                    device_id,
                    "redfish",
                    metric,
                    float(celsius),
                    "C",
                    quality,
                    timestamp,
                    source,
                )
            )
    controls = power.get("PowerControl", [])
    if isinstance(controls, list) and controls and isinstance(controls[0], dict):
        watts = controls[0].get("PowerConsumedWatts")
        if isinstance(watts, (int, float)):
            readings.append(
                Reading(
                    device_id,
                    "redfish",
                    "power_watts",
                    float(watts),
                    "W",
                    "good",
                    timestamp,
                    source,
                )
            )
    return readings


def normalize_modbus(
    device_id: str,
    registers: list[int],
    timestamp: str,
    source: str,
) -> list[Reading]:
    if len(registers) < 2:
        raise AdapterError("short-frame")
    quality = "good" if registers[1] == 1 else "bad"
    return [
        Reading(
            device_id,
            "modbus",
            "power_watts",
            registers[0] / 10.0,
            "W",
            quality,
            timestamp,
            source,
        )
    ]


def normalize_points(
    device_id: str,
    protocol: str,
    points: list[tuple[str, float, str, str]],
    timestamp: str,
    source: str,
) -> list[Reading]:
    return [
        Reading(device_id, protocol, metric, value, unit, quality, timestamp, source)
        for metric, value, unit, quality in points
    ]


def fetch_redfish(host: str, port: int, timeout: float) -> tuple[dict[str, Any], dict[str, Any]]:
    require_loopback(host)
    thermal = _get_json(host, port, "/redfish/v1/Chassis/1/Thermal", timeout)
    power = _get_json(host, port, "/redfish/v1/Chassis/1/Power", timeout)
    return thermal, power


def _get_json(host: str, port: int, path: str, timeout: float) -> dict[str, Any]:
    conn = HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read()
    except TimeoutError as exc:
        raise AdapterError("timeout") from exc
    except OSError as exc:
        if getattr(exc, "winerror", None) == 10060 or isinstance(exc, socket.timeout):
            raise AdapterError("timeout") from exc
        raise AdapterError("refused") from exc
    finally:
        conn.close()
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise AdapterError("bad-document")
    return payload


def read_holding(host: str, port: int, timeout: float) -> list[int]:
    require_loopback(host)
    client = ModbusTcpClient(host, port=port, timeout=timeout)
    try:
        connected = client.connect()  # type: ignore[no-untyped-call]
        if not connected:
            raise AdapterError("refused")
        result: Any = client.read_holding_registers(0, count=2, device_id=1)
    except AdapterError:
        raise
    except Exception as exc:
        raise AdapterError("timeout") from exc
    finally:
        client.close()  # type: ignore[no-untyped-call]
    if getattr(result, "isError", lambda: True)():
        raise AdapterError("modbus-error")
    registers = getattr(result, "registers", None)
    if not isinstance(registers, list):
        raise AdapterError("modbus-error")
    return [int(item) for item in registers]


def in_process_redfish(device: Device, fault: bool, timestamp: str) -> list[Reading]:
    _ = redfish_system(device.device_id, fault)
    return normalize_redfish(
        device.device_id,
        redfish_thermal(fault),
        redfish_power(),
        timestamp,
        "in-process-redfish-document",
    )


def in_process_modbus(device: Device, fault: bool, timestamp: str) -> list[Reading]:
    return normalize_modbus(
        device.device_id,
        pdu_registers(fault),
        timestamp,
        "in-process-modbus-registers",
    )


def in_process_sim(device: Device, fault: bool, timestamp: str) -> list[Reading]:
    if device.kind == "cooling":
        points = cooling_points(fault)
    else:
        points = sensor_points(fault)
    return normalize_points(
        device.device_id,
        "simulation",
        points,
        timestamp,
        "in-process-simulation",
    )
