# Protocols

Redfish paths on 127.0.0.1:

- `GET /redfish/v1/Systems/1`
- `GET /redfish/v1/Chassis/1/Thermal`
- `GET /redfish/v1/Chassis/1/Power`

The adapter uses `http.client` and refuses any host other than loopback before it connects. Reference: [DMTF Redfish Developer Hub](https://www.dmtf.org/standards/redfish).

Modbus is function code 3, holding registers 0 and 1. Register 0 is deci-watts. Register 1 is 1 when quality is good. The client is PyModbus 3.16.2 `ModbusTcpClient.read_holding_registers`. Reference: [PyModbus](https://pymodbus.readthedocs.io/).

BACnet/IP was not started. BACpypes3 is not imported. Reference for a later implementation: [BACpypes3](https://bacpypes3.readthedocs.io/).

SNMP was not started. No agent listens.

The C++ program prints one compiled-in JSON reading and does not open a device file. The Go collector polls HTTP URLs with a worker pool. `TrySend` drops a submit when its buffer is full. That drop is a unit-test of the channel, not a fleet measurement.
