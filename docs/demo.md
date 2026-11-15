# Demo

Twelve minutes. Stop when a service would have to be contacted.

1. Show the notice `SIMULATED_DATACENTER_NOT_A_CUSTOMER_SITE` and the deployment decision NO-GO.
2. `GET /api/v1/devices` lists `SYN-SRV-0001`, `SYN-PDU-0001`, `SYN-COOL-0001`, and `SYN-SENS-0001`.
3. Telemetry for the server comes from loopback Redfish. Intake is 23.0 C. Telemetry for the PDU comes from loopback Modbus. Power is 418.0 W.
4. Fault the sensor. The alert reason is `quality`.
5. Submit a fan command as `lab-observer` and show 403. Submit as `lab-operator`, approve as `lab-approver`, and show `executed_on_equipment` false.
6. Show `benchmarks/latest.json`. The 100-device pass is in-process. It does not open 100 TCP sessions and it does not sleep the 5 second interval.
7. Stop. BACnet, SNMP, PostgreSQL, Grafana, Kubernetes, and real equipment were not run.
