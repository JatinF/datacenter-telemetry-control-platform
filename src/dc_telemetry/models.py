"""Normalized device and reading records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    device_id: str
    rack_id: str
    kind: str
    protocol: str
    host: str
    port: int
    live: bool


@dataclass(frozen=True)
class Reading:
    device_id: str
    protocol: str
    metric: str
    value: float
    unit: str
    quality: str
    timestamp: str
    source: str

    def as_dict(self) -> dict[str, object]:
        return {
            "device_id": self.device_id,
            "protocol": self.protocol,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "quality": self.quality,
            "timestamp": self.timestamp,
            "source": self.source,
        }
