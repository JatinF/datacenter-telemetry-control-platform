"""Readiness table. This module does not open a socket."""

from __future__ import annotations

import os


def report() -> dict[str, str]:
    database = os.environ.get("DATABASE_URL", "")
    if database == "":
        postgres = "not-run"
    elif _loopback_database(database):
        postgres = "local-configured"
    else:
        postgres = "remote-blocked"
    return {
        "postgres": postgres,
        "grafana": "not-run",
        "prometheus_server": "not-run",
        "bacnet": "not-run",
        "snmp": "not-run",
        "kubernetes": "not-run",
        "docker_local": "not-run",
        "real_equipment": "not-contacted",
        "deployment": "NO-GO",
        "price": "none",
    }


def _loopback_database(url: str) -> bool:
    lowered = url.lower()
    return "127.0.0.1" in lowered or "localhost" in lowered
