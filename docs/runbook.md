# Runbook

A refused Modbus connection returns adapter kind `refused`. A loopback listener that accepts and does not answer returns kind `timeout`. The recovery check in `tests/test_platform.py` closes nothing persistent: it reads a closed port, then reads a new `ModbusSim`, and expects registers `[4180, 1]`.

A sensor fault is `POST /api/v1/simulations/faults` with `SYN-SENS-0001`. The next collection stores `quality=bad` and one alert. Collecting again does not add a second alert for the same device, metric, and reason.

Rollback of a simulated fan duty is another approved command. There is no equipment rollback because no equipment was changed.

PostgreSQL was not started, so there is no database failover to perform.
