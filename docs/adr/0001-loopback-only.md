# ADR 0001 — Loopback simulators, not a hardware lab

Date: 2026-11-14

## Status

Accepted.

## Context

A portfolio lab can show protocol adapters without a rack. A real BMC, PDU, or building controller is out of scope.

## Decision

Redfish and Modbus listeners bind only `127.0.0.1`. The client refuses every other host before connecting. The 100-device benchmark reads in-process documents so it does not open 100 sockets and does not pretend to be a plant network.

BACnet and SNMP stay not-run until a loopback agent is actually started and measured. PostgreSQL stays not-run until a server is started and the schema is applied. Helm stays unapplied.

## Consequences

The acceptance item "Docker Compose starts the full demonstration" is unmet on this workstation because Docker is not installed and Compose was not started. Image proof has to come from the Actions `docker-build` job.
