"""In-process reading history. PostgreSQL is not opened."""

from __future__ import annotations

import threading

from dc_telemetry.models import Reading


class MemoryStore:
    def __init__(self) -> None:
        self._rows: list[Reading] = []
        self._lock = threading.Lock()

    def add(self, readings: list[Reading]) -> None:
        with self._lock:
            self._rows.extend(readings)

    def latest(self, device_id: str) -> list[Reading]:
        with self._lock:
            rows = [row for row in self._rows if row.device_id == device_id]
        if not rows:
            return []
        newest = max(row.timestamp for row in rows)
        return [row for row in rows if row.timestamp == newest]

    def history(self, device_id: str) -> list[Reading]:
        with self._lock:
            return [row for row in self._rows if row.device_id == device_id]
