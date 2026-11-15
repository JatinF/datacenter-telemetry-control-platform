# API contracts

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/healthz` | Liveness |
| GET | `/readyz` | In-process lab is ready. Postgres stays not-run |
| GET | `/metrics` | Prometheus text from this process |
| GET | `/api/v1/devices` | Discovered simulated devices |
| GET | `/api/v1/devices/{id}` | Metadata and simulated fan duty |
| GET | `/api/v1/devices/{id}/telemetry` | Latest readings. `history=true` returns every stored row |
| GET | `/api/v1/racks/{id}/health` | Device count and worst quality |
| GET | `/api/v1/alerts` | Alerts raised by collection |
| POST | `/api/v1/simulations/faults` | Mark a simulated device faulty |
| POST | `/api/v1/commands` | Operator submits `set_fan_duty` |
| POST | `/api/v1/commands/{id}/decision` | Approver executes it in simulation |
| GET | `/api/v1/commands/{id}` | State and audit |

Tokens are `lab-observer`, `lab-operator`, and `lab-approver`. They authorize nothing outside this process. A missing or unknown bearer is 401. The observer and the operator cannot approve. The approver cannot submit.
