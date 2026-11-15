# Architecture

The lab is an in-process hall plus two loopback listeners. A Redfish HTTP subset serves one server. A Modbus TCP function-3 responder serves one PDU. Cooling and the humidity sensor are in-process documents. The API reads those sources, stores readings in memory, and raises an alert when quality is bad or a temperature is at least 40 C.

Commands change a simulated fan duty after a different role approves them. They do not open a socket.

PostgreSQL, Grafana, a Prometheus server, BACnet, SNMP, Kubernetes, and real equipment are not contacted. The SQL file, the Helm chart, the Prometheus file, and the Grafana JSON are present and unapplied.
