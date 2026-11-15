"""Loopback HTTP server that speaks a small Redfish JSON subset."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Protocol


class RedfishSource(Protocol):
    def redfish_body(self, path: str) -> bytes: ...


class RedfishSim:
    def __init__(self, source: RedfishSource) -> None:
        self._source = source
        handler = _handler(source)
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = int(self._httpd.server_address[1])
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=2)


def _handler(source: RedfishSource) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = source.redfish_body(self.path.split("?", 1)[0])
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def encode(payload: dict[str, object]) -> bytes:
    return json.dumps(payload).encode("utf-8")
