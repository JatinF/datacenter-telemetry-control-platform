"""Prometheus instruments for the in-process collector."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram


class Instruments:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.readings = Counter(
            "dc_readings_total",
            "Normalized readings stored.",
            registry=self.registry,
        )
        self.errors = Counter(
            "dc_adapter_errors_total",
            "Adapter failures by kind.",
            ["kind"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "dc_collect_seconds",
            "In-process collection latency.",
            registry=self.registry,
        )
