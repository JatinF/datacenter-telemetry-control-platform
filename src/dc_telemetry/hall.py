"""Deterministic simulated racks. Values are constants, not equipment measurements."""

from __future__ import annotations

from dataclasses import dataclass, field

from dc_telemetry.models import Device

SITE = "SYN-SITE-LABHALL"
NOTICE = "SIMULATED_DATACENTER_NOT_A_CUSTOMER_SITE"
RACK = "SYN-RACK-01"
SERVER_ID = "SYN-SRV-0001"
PDU_ID = "SYN-PDU-0001"
COOL_ID = "SYN-COOL-0001"
SENSOR_ID = "SYN-SENS-0001"

INTAKE_C = 23.0
EXHAUST_C = 31.0
FAN_RPM = 4200.0
SERVER_WATTS = 186.0
PDU_WATTS = 418.0
SUPPLY_C = 16.0
RETURN_C = 24.0
HUMIDITY = 45.0
FAULT_INTAKE_C = 85.0
TEMPERATURE_ALERT_C = 40.0


@dataclass
class Hall:
    devices: list[Device]
    faults: set[str] = field(default_factory=set)
    fan_duty: dict[str, int] = field(default_factory=dict)

    def device(self, device_id: str) -> Device | None:
        for item in self.devices:
            if item.device_id == device_id:
                return item
        return None

    def faulty(self, device_id: str) -> bool:
        return device_id in self.faults


def demo_devices(server_port: int, pdu_port: int) -> list[Device]:
    return [
        Device(SERVER_ID, RACK, "server", "redfish", "127.0.0.1", server_port, True),
        Device(PDU_ID, RACK, "pdu", "modbus", "127.0.0.1", pdu_port, True),
        Device(COOL_ID, RACK, "cooling", "simulation", "127.0.0.1", 0, False),
        Device(SENSOR_ID, RACK, "sensor", "simulation", "127.0.0.1", 0, False),
    ]


def bench_devices(count: int = 100) -> list[Device]:
    devices: list[Device] = []
    for index in range(1, count + 1):
        if index <= 80:
            devices.append(
                Device(
                    f"SYN-SRV-{index:04d}",
                    f"SYN-RACK-{(index - 1) // 20 + 1:02d}",
                    "server",
                    "redfish-document",
                    "127.0.0.1",
                    0,
                    False,
                )
            )
        else:
            devices.append(
                Device(
                    f"SYN-PDU-{index:04d}",
                    f"SYN-RACK-{(index - 1) // 20 + 1:02d}",
                    "pdu",
                    "modbus-registers",
                    "127.0.0.1",
                    0,
                    False,
                )
            )
    return devices


def redfish_system(device_id: str, fault: bool) -> dict[str, object]:
    return {
        "Id": device_id,
        "Status": {"Health": "Critical" if fault else "OK"},
        "PowerConsumedWatts": SERVER_WATTS,
    }


def redfish_thermal(fault: bool) -> dict[str, object]:
    intake = FAULT_INTAKE_C if fault else INTAKE_C
    quality = "bad" if fault else "good"
    return {
        "Fans": [{"Name": "Fan1", "Reading": FAN_RPM, "ReadingUnits": "RPM"}],
        "Temperatures": [
            {"Name": "Intake", "ReadingCelsius": intake, "Quality": quality},
            {"Name": "Exhaust", "ReadingCelsius": EXHAUST_C, "Quality": "good"},
        ],
    }


def redfish_power() -> dict[str, object]:
    return {"PowerControl": [{"PowerConsumedWatts": SERVER_WATTS}]}


def pdu_registers(fault: bool) -> list[int]:
    deciwatts = int(PDU_WATTS * 10)
    return [deciwatts, 0 if fault else 1]


def cooling_points(fault: bool) -> list[tuple[str, float, str, str]]:
    quality = "bad" if fault else "good"
    supply = FAULT_INTAKE_C if fault else SUPPLY_C
    return [
        ("supply_temperature_c", supply, "C", quality),
        ("return_temperature_c", RETURN_C, "C", "good"),
    ]


def sensor_points(fault: bool) -> list[tuple[str, float, str, str]]:
    if fault:
        return [("humidity_percent", HUMIDITY, "%", "bad")]
    return [("humidity_percent", HUMIDITY, "%", "good")]
