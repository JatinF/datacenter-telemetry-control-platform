.PHONY: test gates bench
test:
	python -m pytest
gates:
	python -m dc_telemetry gates
bench:
	python scripts/run_benchmark.py
