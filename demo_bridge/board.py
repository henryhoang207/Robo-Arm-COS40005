"""Client for the X-VLA App Lab app on the VENTUNO Q board.

TCP 8766 carries inference: each frame is uint32 header_len, uint32 payload_len (little-endian),
a UTF-8 JSON header, then the raw payload. HTTP 8080 serves /api/status.
Protocol source: deployments/arduino_app_lab/xvla-libero-npu/python/main.py.
"""
from __future__ import annotations

import json
import socket
import struct
import time
import urllib.request

import numpy as np

FRAME = struct.Struct("<II")
CHUNK_SHAPE = (30, 7)


class BoardError(Exception):
    """A board failure with one of the spec's error codes."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray(n)
    view = memoryview(buf)
    got = 0
    while got < n:
        r = sock.recv_into(view[got:], n - got)
        if r == 0:
            raise BoardError("board_error", "board closed the connection")
        got += r
    return bytes(buf)


class BoardSession:
    """One TCP connection to the board, held for one episode."""

    def __init__(self, sock: socket.socket):
        self._sock = sock

    def __enter__(self) -> "BoardSession":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass

    def rpc(self, header: dict, payload: bytes = b"") -> tuple[dict, bytes]:
        hb = json.dumps(header).encode("utf-8")
        try:
            self._sock.sendall(FRAME.pack(len(hb), len(payload)) + hb + payload)
            hlen, plen = FRAME.unpack(_recv_exact(self._sock, FRAME.size))
            reply = json.loads(_recv_exact(self._sock, hlen).decode("utf-8"))
            body = _recv_exact(self._sock, plen) if plen else b""
        except socket.timeout as exc:
            raise BoardError("board_timeout", "no reply from the board within the timeout") from exc
        except BoardError:
            raise
        except OSError as exc:
            raise BoardError("board_unreachable", f"connection to the board failed: {exc}") from exc
        if not reply.get("ok"):
            raise BoardError("board_error", str(reply.get("error", "board replied ok: false")))
        return reply, body

    def infer(self, agentview: np.ndarray, wrist: np.ndarray, task_text: str, eef_pos: np.ndarray,
              eef_mat: np.ndarray, noise: np.ndarray | None = None) -> tuple[np.ndarray, dict, float]:
        """Send raw (not flipped) camera images; return (30x7 actions, board timings, round trip ms)."""
        v0 = np.ascontiguousarray(agentview, dtype=np.uint8)
        v1 = np.ascontiguousarray(wrist, dtype=np.uint8)
        header = {
            "cmd": "infer_e2e",
            "task_text": task_text,
            "domain_id": 3,
            "steps": 10,
            "flip_view0": True,
            "view0_shape": list(v0.shape),
            "view1_shape": list(v1.shape),
            "has_noise": noise is not None,
        }
        payload = (v0.tobytes() + v1.tobytes()
                   + np.ascontiguousarray(eef_pos, dtype=np.float32).reshape(3).tobytes()
                   + np.ascontiguousarray(eef_mat, dtype=np.float32).reshape(3, 3).tobytes())
        if noise is not None:
            payload += np.ascontiguousarray(noise, dtype=np.float32).reshape(1, 30, 20).tobytes()
        t0 = time.perf_counter()
        reply, body = self.rpc(header, payload)
        rtt_ms = (time.perf_counter() - t0) * 1000.0
        shape = tuple(reply.get("shape", ()))
        if shape != CHUNK_SHAPE or len(body) != 4 * CHUNK_SHAPE[0] * CHUNK_SHAPE[1]:
            raise BoardError("board_error", f"unexpected action chunk shape {shape}")
        actions = np.frombuffer(body, dtype=np.float32).reshape(CHUNK_SHAPE).copy()
        return actions, dict(reply.get("timings", {})), rtt_ms


class BoardClient:
    def __init__(self, host: str, port: int = 8766, status_port: int = 8080, timeout_s: float = 10.0):
        self.host = host
        self.port = port
        self.status_port = status_port
        self.timeout_s = timeout_s

    def status(self, timeout_s: float = 2.0) -> dict | None:
        """The board's /api/status JSON, or None when the board cannot be reached."""
        url = f"http://{self.host}:{self.status_port}/api/status"
        try:
            with urllib.request.urlopen(url, timeout=timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) and data.get("ok") else None

    def connect(self) -> BoardSession:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
        except socket.timeout as exc:
            raise BoardError("board_unreachable", f"board {self.host}:{self.port} did not answer") from exc
        except OSError as exc:
            raise BoardError("board_unreachable", f"board {self.host}:{self.port} refused or unreachable: {exc}") from exc
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(self.timeout_s)
        return BoardSession(sock)


def summarize_status(host: str, status: dict | None) -> dict:
    """The `board` object of GET /api/health."""
    if status is None:
        return {"reachable": False, "host": host}
    providers = status.get("providers") or {}
    all_on_npu = bool(providers) and all(
        isinstance(p, list) and p[:1] == ["QNNExecutionProvider"] for p in providers.values())
    return {
        "reachable": True,
        "host": host,
        "mode": status.get("mode"),
        "all_on_npu": all_on_npu,
        "chunks_served": status.get("chunks_served"),
        "nsp_temps_c": status.get("nsp_temps_c") or {},
        "started_at": status.get("started_at"),
    }
