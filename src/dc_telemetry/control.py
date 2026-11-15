"""Simulated commands. Approval stays in process and does not open a socket."""

from __future__ import annotations

import hmac
from dataclasses import dataclass, field

TOKENS = {
    "lab-observer": "observer",
    "lab-operator": "operator",
    "lab-approver": "approver",
}


class AuthError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(str(status))
        self.status = status


def role_for(authorization: str | None) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise AuthError(401)
    token = authorization.removeprefix("Bearer ")
    for known, role in TOKENS.items():
        if len(token) == len(known) and hmac.compare_digest(token, known):
            return role
    raise AuthError(401)


@dataclass
class Command:
    command_id: str
    device_id: str
    action: str
    duty_percent: int
    state: str
    requested_by: str
    decided_by: str | None = None
    audit: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "command_id": self.command_id,
            "device_id": self.device_id,
            "action": self.action,
            "duty_percent": self.duty_percent,
            "state": self.state,
            "requested_by": self.requested_by,
            "decided_by": self.decided_by,
            "audit": list(self.audit),
            "executed_on_equipment": False,
        }
