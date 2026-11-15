"""FastAPI surface for the simulated hall."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from dc_telemetry.adapters import AdapterError
from dc_telemetry.control import AuthError
from dc_telemetry.lab import Lab


class FaultBody(BaseModel):
    device_id: str


class CommandBody(BaseModel):
    device_id: str
    action: str = "set_fan_duty"
    duty_percent: int = Field(ge=0, le=100)


class DecisionBody(BaseModel):
    decision: str


def create_app(lab: Lab | None = None) -> FastAPI:
    app = FastAPI(title="Simulated data-center telemetry")
    app.state.lab = lab or Lab("demo")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready", "postgres": "not-run", "equipment": "not-contacted"}

    @app.get("/metrics")
    def metrics(request: Request) -> Response:
        lab_state: Lab = request.app.state.lab
        payload = generate_latest(lab_state.instruments.registry)
        return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/devices")
    def devices(request: Request) -> dict[str, object]:
        lab_state = _lab(request)
        return {"devices": [_device(item) for item in lab_state.discover()]}

    @app.get("/api/v1/devices/{device_id}")
    def device(device_id: str, request: Request) -> dict[str, object]:
        lab_state = _lab(request)
        found = lab_state.hall.device(device_id)
        if found is None:
            raise HTTPException(404)
        body = _device(found)
        body["fan_duty_percent"] = lab_state.hall.fan_duty.get(device_id)
        return body

    @app.get("/api/v1/devices/{device_id}/telemetry")
    def telemetry(device_id: str, request: Request, history: bool = False) -> dict[str, object]:
        lab_state = _lab(request)
        if lab_state.hall.device(device_id) is None:
            raise HTTPException(404)
        try:
            lab_state.collect(lab_state.hall.device(device_id) or _missing())
        except AdapterError as exc:
            raise HTTPException(504, detail=exc.kind) from exc
        rows = lab_state.store.history(device_id) if history else lab_state.store.latest(device_id)
        return {"device_id": device_id, "readings": [row.as_dict() for row in rows]}

    @app.get("/api/v1/racks/{rack_id}/health")
    def rack_health(rack_id: str, request: Request) -> dict[str, object]:
        return _lab(request).rack_health(rack_id)

    @app.get("/api/v1/alerts")
    def alerts(request: Request) -> dict[str, object]:
        return {"alerts": list(_lab(request).alerts)}

    @app.post("/api/v1/simulations/faults")
    def faults(body: FaultBody, request: Request) -> dict[str, str]:
        lab_state = _lab(request)
        try:
            lab_state.inject_fault(body.device_id)
        except KeyError as exc:
            raise HTTPException(404) from exc
        return {"device_id": body.device_id, "state": "faulted"}

    @app.post("/api/v1/commands")
    def commands(body: CommandBody, request: Request) -> dict[str, object]:
        if body.action != "set_fan_duty":
            raise HTTPException(400)
        try:
            command = _lab(request).submit_command(
                request.headers.get("authorization"),
                body.device_id,
                body.duty_percent,
            )
        except AuthError as exc:
            raise HTTPException(exc.status) from exc
        except KeyError as exc:
            raise HTTPException(404) from exc
        return command.as_dict()

    @app.post("/api/v1/commands/{command_id}/decision")
    def decision(command_id: str, body: DecisionBody, request: Request) -> dict[str, object]:
        try:
            command = _lab(request).decide_command(
                request.headers.get("authorization"),
                command_id,
                body.decision,
            )
        except AuthError as exc:
            raise HTTPException(exc.status) from exc
        except KeyError as exc:
            raise HTTPException(404) from exc
        return command.as_dict()

    @app.get("/api/v1/commands/{command_id}")
    def command_status(command_id: str, request: Request) -> dict[str, object]:
        command = _lab(request).commands.get(command_id)
        if command is None:
            raise HTTPException(404)
        return command.as_dict()

    return app


def _lab(request: Request) -> Lab:
    lab_state: Any = request.app.state.lab
    if not isinstance(lab_state, Lab):
        raise HTTPException(500)
    return lab_state


def _device(item: Any) -> dict[str, object]:
    return {
        "device_id": item.device_id,
        "rack_id": item.rack_id,
        "kind": item.kind,
        "protocol": item.protocol,
        "host": item.host,
        "port": item.port,
        "live": item.live,
    }


def _missing() -> Any:
    raise HTTPException(404)
