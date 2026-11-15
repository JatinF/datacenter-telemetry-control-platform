# Threat model

The trust boundary is the process. Adapters call `require_loopback` before `HTTPConnection` or `ModbusTcpClient`. A non-loopback host raises `RemoteBlocked` and no socket is opened for that call.

`gates` reads `DATABASE_URL` only to label it. An empty value is not-run. A localhost value is local-configured. Any other value is remote-blocked. The URL is not printed and not dialed.

Command execution writes `fan_duty` on the hall object. The command record sets `executed_on_equipment` to false.

The Helm chart and the SQL schema are not applied. A container image is built in GitHub Actions and is not run here.
