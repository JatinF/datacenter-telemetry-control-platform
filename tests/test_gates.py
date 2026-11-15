"""Gates stay local. The bench file is produced only by the benchmark script."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import yaml

from dc_telemetry.bench import _hardware, _stats, main
from dc_telemetry.gates import report


def test_gates_do_not_open_a_socket(monkeypatch: object) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "socket", boom)  # type: ignore[attr-defined]
    body = report()
    assert body["deployment"] == "NO-GO"
    assert body["postgres"] == "not-run"
    assert body["bacnet"] == "not-run"
    assert body["snmp"] == "not-run"
    assert body["real_equipment"] == "not-contacted"


def test_remote_database_url_is_not_contacted(monkeypatch: object) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/lab")  # type: ignore[attr-defined]
    assert report()["postgres"] == "remote-blocked"


def test_local_database_url_is_labeled_and_not_contacted(monkeypatch: object) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/lab")  # type: ignore[attr-defined]
    assert report()["postgres"] == "local-configured"


def test_alert_rule_file_parses() -> None:
    text = Path("monitoring/alert-rules.yml").read_text(encoding="utf-8")
    loaded = yaml.safe_load(text)
    expr = loaded["groups"][0]["rules"][0]["expr"]
    assert "dc_adapter_errors_total" in expr


def test_bench_writes_in_process_counts(tmp_path: object, monkeypatch: object) -> None:
    def hardware() -> dict[str, object]:
        return {"processor": "test", "cores": 1, "logical_processors": 1}

    monkeypatch.setattr("dc_telemetry.bench._hardware", hardware)  # type: ignore[attr-defined]
    output = Path(str(tmp_path)) / "bench.json"
    assert main(["--devices", "4", "--output", str(output)]) == 0
    text = output.read_text(encoding="utf-8")
    assert '"tcp_sessions": 0' in text
    assert '"drops": 0' in text
    assert '"interval_was_slept": false' in text
    assert _stats([])["calls"] == 0
    hardware = _hardware()
    assert "processor" in hardware or hardware.get("source") == "unavailable"


def test_readme_quotes_the_benchmark_when_present() -> None:
    bench = Path("benchmarks/latest.json")
    readme = Path("README.md")
    if not bench.exists():
        return
    summary = json.loads(bench.read_text(encoding="utf-8"))
    text = readme.read_text(encoding="utf-8")
    assert str(summary["elapsed_seconds"]) in text
    assert str(summary["throughput_readings_per_second"]) in text
    assert str(summary["per_device_seconds"]["p95"]) in text
    assert "in-process-documents" in text
