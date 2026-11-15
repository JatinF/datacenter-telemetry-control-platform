"""Refuse any host that is not this machine's loopback interface."""

from __future__ import annotations


class RemoteBlocked(Exception):
    """A non-loopback address was refused before a socket was opened."""


def require_loopback(host: str) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise RemoteBlocked(host)
