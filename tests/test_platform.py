"""Discovery, normalized protocols, faults, history, and commands."""

from __future__ import annotations

import socket

from fastapi.testclient import TestClient

from dc_telemetry.__main__ import main
from dc_telemetry.adapters import (
    AdapterError,
    fetch_redfish,
    in_process_modbus,
    normalize_modbus,
    read_holding,
)
from dc_telemetry.api import create_app
from dc_telemetry.hall import PDU_ID, SENSOR_ID, SERVER_ID
from dc_telemetry.lab import Lab
from dc_telemetry.modbus_sim import ModbusSim
from dc_telemetry.models import Device
from dc_telemetry.safety import RemoteBlocked


class Clock:
    def __init__(self) -> None:
        self.n = 0

    def __call__(self) -> str:
        self.n += 1
        return f"2026-11-14T00:00:{self.n:02d}Z"


def test_discovery_redfish_and_modbus() -> None:
    lab = Lab("demo", clock=Clock())
    try:
        client = TestClient(create_app(lab))
        devices = client.get("/api/v1/devices")
        assert devices.status_code == 200
        ids = {item["device_id"] for item in devices.json()["devices"]}
        assert {SERVER_ID, PDU_ID, "SYN-COOL-0001", SENSOR_ID} <= ids
        server = client.get(f"/api/v1/devices/{SERVER_ID}/telemetry")
        assert server.status_code == 200
        metrics = {row["metric"]: row for row in server.json()["readings"]}
        assert metrics["intake_temperature_c"]["value"] == 23.0
        assert metrics["intake_temperature_c"]["protocol"] == "redfish"
        assert metrics["intake_temperature_c"]["quality"] == "good"
        pdu = client.get(f"/api/v1/devices/{PDU_ID}/telemetry")
        power = pdu.json()["readings"][0]
        assert power["protocol"] == "modbus"
        assert power["metric"] == "power_watts"
        assert power["value"] == 418.0
        assert power["unit"] == "W"
        cool = client.get("/api/v1/devices/SYN-COOL-0001/telemetry")
        assert cool.json()["readings"][0]["protocol"] == "simulation"
        health = client.get("/api/v1/racks/SYN-RACK-01/health")
        assert health.json()["worst_quality"] == "good"
    finally:
        lab.close()


def test_fault_creates_one_alert_and_history_is_queryable() -> None:
    lab = Lab("demo", clock=Clock())
    try:
        client = TestClient(create_app(lab))
        fault = client.post("/api/v1/simulations/faults", json={"device_id": SENSOR_ID})
        assert fault.status_code == 200
        first = client.get(f"/api/v1/devices/{SENSOR_ID}/telemetry?history=true")
        second = client.get(f"/api/v1/devices/{SENSOR_ID}/telemetry?history=true")
        assert first.json()["readings"][0]["quality"] == "bad"
        assert len(second.json()["readings"]) == 2
        alerts = client.get("/api/v1/alerts").json()["alerts"]
        assert len(alerts) == 1
        assert alerts[0]["reason"] == "quality"
        missing = client.get("/api/v1/devices/SYN-NONE/telemetry")
        assert missing.status_code == 404
    finally:
        lab.close()


def test_unauthorized_command_is_rejected_and_approval_stays_simulated() -> None:
    lab = Lab("demo", clock=Clock())
    try:
        client = TestClient(create_app(lab))
        denied = client.post(
            "/api/v1/commands",
            headers={"authorization": "Bearer lab-observer"},
            json={"device_id": SERVER_ID, "action": "set_fan_duty", "duty_percent": 40},
        )
        assert denied.status_code == 403
        assert lab.hall.fan_duty.get(SERVER_ID) is None
        missing = client.post("/api/v1/commands", json={"device_id": SERVER_ID, "duty_percent": 40})
        assert missing.status_code == 401
        created = client.post(
            "/api/v1/commands",
            headers={"authorization": "Bearer lab-operator"},
            json={"device_id": SERVER_ID, "action": "set_fan_duty", "duty_percent": 40},
        )
        assert created.status_code == 200
        command_id = created.json()["command_id"]
        assert created.json()["state"] == "pending"
        assert created.json()["executed_on_equipment"] is False
        operator_decide = client.post(
            f"/api/v1/commands/{command_id}/decision",
            headers={"authorization": "Bearer lab-operator"},
            json={"decision": "approve"},
        )
        assert operator_decide.status_code == 403
        approved = client.post(
            f"/api/v1/commands/{command_id}/decision",
            headers={"authorization": "Bearer lab-approver"},
            json={"decision": "approve"},
        )
        assert approved.status_code == 200
        assert approved.json()["state"] == "executed-in-simulation"
        assert lab.hall.fan_duty[SERVER_ID] == 40
        status = client.get(f"/api/v1/commands/{command_id}")
        assert status.json()["decided_by"] == "approver"
    finally:
        lab.close()


def test_timeout_and_reconnect_and_remote_block() -> None:
    try:
        fetch_redfish("10.1.1.1", 443, 0.2)
    except RemoteBlocked:
        pass
    else:
        raise AssertionError("remote host was not blocked")
    blackhole = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blackhole.bind(("127.0.0.1", 0))
    blackhole.listen(1)
    port = int(blackhole.getsockname()[1])
    try:
        fetch_redfish("127.0.0.1", port, 0.2)
    except AdapterError as exc:
        assert exc.kind == "timeout"
    else:
        raise AssertionError("timeout was not raised")
    finally:
        blackhole.close()
    try:
        read_holding("127.0.0.1", 1, 0.2)
    except AdapterError as exc:
        assert exc.kind == "refused"
    else:
        raise AssertionError("refused connection was not reported")
    sim = ModbusSim([4180, 1])
    try:
        assert read_holding("127.0.0.1", sim.port, 1.0) == [4180, 1]
    finally:
        sim.close()


def test_health_metrics_and_server_fault() -> None:
    lab = Lab("demo", clock=Clock())
    try:
        client = TestClient(create_app(lab))
        assert client.get("/healthz").json()["status"] == "ok"
        ready = client.get("/readyz").json()
        assert ready["postgres"] == "not-run"
        fault = client.post("/api/v1/simulations/faults", json={"device_id": SERVER_ID})
        assert fault.status_code == 200
        reading = client.get(f"/api/v1/devices/{SERVER_ID}/telemetry").json()["readings"]
        intake = next(row for row in reading if row["metric"] == "intake_temperature_c")
        assert intake["value"] == 85.0
        assert intake["quality"] == "bad"
        body = client.get("/metrics").text
        assert "dc_readings_total" in body
        assert "dc_collect_seconds" in body
        assert client.get(f"/api/v1/devices/{SERVER_ID}").status_code == 200
        assert client.get("/api/v1/devices/SYN-NONE").status_code == 404
        assert client.get("/api/v1/commands/SYN-CMD-9999").status_code == 404
        bad_action = client.post(
            "/api/v1/commands",
            headers={"authorization": "Bearer lab-operator"},
            json={"device_id": SERVER_ID, "action": "power_off", "duty_percent": 1},
        )
        assert bad_action.status_code == 400
        unknown = client.post(
            "/api/v1/commands",
            headers={"authorization": "Bearer lab-operator"},
            json={"device_id": "SYN-NONE", "duty_percent": 1},
        )
        assert unknown.status_code == 404
        missing_fault = client.post(
            "/api/v1/simulations/faults",
            json={"device_id": "SYN-NONE"},
        )
        assert missing_fault.status_code == 404
        assert b"unknown" in lab.redfish_body("/nope")
        assert lab.status()["notice"] == "SIMULATED_DATACENTER_NOT_A_CUSTOMER_SITE"
    finally:
        lab.close()


def test_cli_short_frame_and_pdu_fault() -> None:
    assert main(["gates"]) == 0
    assert main(["nope"]) == 2
    try:
        normalize_modbus("SYN-PDU-0001", [1], "2026-11-14T00:00:01Z", "test")
    except AdapterError as exc:
        assert exc.kind == "short-frame"
    else:
        raise AssertionError("short frame was accepted")
    device = Device("SYN-PDU-0099", "SYN-RACK-05", "pdu", "modbus-registers", "127.0.0.1", 0, False)
    faulted = in_process_modbus(device, True, "2026-11-14T00:00:01Z")
    assert faulted[0].quality == "bad"
    lab = Lab("demo", clock=Clock())
    try:
        client = TestClient(create_app(lab))
        pdu_fault = client.post("/api/v1/simulations/faults", json={"device_id": PDU_ID})
        assert pdu_fault.status_code == 200
        power = client.get(f"/api/v1/devices/{PDU_ID}/telemetry").json()["readings"][0]
        assert power["quality"] == "bad"
        created = client.post(
            "/api/v1/commands",
            headers={"authorization": "Bearer lab-operator"},
            json={"device_id": SERVER_ID, "duty_percent": 10},
        )
        command_id = created.json()["command_id"]
        client.post(
            f"/api/v1/commands/{command_id}/decision",
            headers={"authorization": "Bearer lab-approver"},
            json={"decision": "approve"},
        )
        again = client.post(
            f"/api/v1/commands/{command_id}/decision",
            headers={"authorization": "Bearer lab-approver"},
            json={"decision": "approve"},
        )
        assert again.status_code == 409
        missing = client.post(
            "/api/v1/commands/SYN-CMD-9999/decision",
            headers={"authorization": "Bearer lab-approver"},
            json={"decision": "approve"},
        )
        assert missing.status_code == 404
    finally:
        lab.close()
