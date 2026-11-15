"""Loopback Modbus TCP server for function code 3, holding registers."""

from __future__ import annotations

import socket
import threading


class ModbusSim:
    def __init__(self, registers: list[int]) -> None:
        self.registers = list(registers)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(8)
        self.port = int(self._sock.getsockname()[1])
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def update(self, registers: list[int]) -> None:
        with self._lock:
            self.registers = list(registers)

    def close(self) -> None:
        self._stop.set()
        self._sock.close()
        self._thread.join(timeout=2)

    def _serve(self) -> None:
        self._sock.settimeout(0.2)
        while not self._stop.is_set():
            try:
                conn, _addr = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with conn:
                self._reply(conn)

    def _reply(self, conn: socket.socket) -> None:
        try:
            frame = conn.recv(256)
        except OSError:
            return
        if len(frame) < 12 or frame[7] != 3:
            return
        start = int.from_bytes(frame[8:10], "big")
        count = int.from_bytes(frame[10:12], "big")
        with self._lock:
            window = self.registers[start : start + count]
        if len(window) != count:
            return
        payload = bytes([3, count * 2])
        for value in window:
            payload += int(value).to_bytes(2, "big")
        length = len(payload) + 1
        header = frame[0:2] + b"\x00\x00" + length.to_bytes(2, "big") + frame[6:7]
        try:
            conn.sendall(header + payload)
        except OSError:
            return
