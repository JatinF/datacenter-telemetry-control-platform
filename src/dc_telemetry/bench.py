"""Measure one in-process pass over the bench hall. No sockets are opened."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

from dc_telemetry.hall import NOTICE
from dc_telemetry.lab import Lab


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--devices", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/latest.json"))
    args = parser.parse_args(argv)
    lab = Lab("bench", device_count=args.devices)
    started = time.perf_counter()
    summary_counts = lab.collect_all()
    elapsed = time.perf_counter() - started
    ordered = sorted(lab.samples)
    payload = {
        "notice": NOTICE,
        "deployment": "NO-GO",
        "profile": "bench",
        "transport": "in-process-documents",
        "tcp_sessions": 0,
        "configured_interval_seconds": 5,
        "interval_was_slept": False,
        "devices": summary_counts["devices"],
        "stored_readings": summary_counts["stored"],
        "errors": summary_counts["errors"],
        "drops": summary_counts["drops"],
        "error_rate": summary_counts["errors"] / summary_counts["devices"],
        "elapsed_seconds": elapsed,
        "throughput_readings_per_second": summary_counts["stored"] / elapsed if elapsed else 0.0,
        "per_device_seconds": _stats(ordered),
        "hardware": _hardware(),
        "python": platform.python_version(),
        "postgres": "not-run",
        "grafana": "not-run",
        "prometheus_server": "not-run",
        "price": "none",
        "real_equipment": "not-contacted",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"devices": payload["devices"], "elapsed_seconds": elapsed}))
    return 0


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0, "calls": 0}
    ordered = sorted(values)
    return {
        "min": ordered[0],
        "p50": ordered[len(ordered) // 2],
        "p95": ordered[max(0, int(0.95 * (len(ordered) - 1)))],
        "max": ordered[-1],
        "calls": float(len(ordered)),
    }


def _hardware() -> dict[str, Any]:
    script = (
        "Get-CimInstance Win32_Processor | "
        "Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors | "
        "ConvertTo-Json -Compress; "
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object FreePhysicalMemory,TotalVisibleMemorySize | ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return {"source": "unavailable"}
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip().startswith("{")]
    if len(lines) < 2:
        return {"source": "unavailable"}
    cpu = json.loads(lines[0])
    memory = json.loads(lines[1])
    return {
        "processor": cpu.get("Name"),
        "cores": cpu.get("NumberOfCores"),
        "logical_processors": cpu.get("NumberOfLogicalProcessors"),
        "free_physical_memory_kb": memory.get("FreePhysicalMemory"),
        "total_visible_memory_kb": memory.get("TotalVisibleMemorySize"),
        "system": platform.system(),
    }
