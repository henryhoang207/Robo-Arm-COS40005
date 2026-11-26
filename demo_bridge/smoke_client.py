"""End-to-end smoke check against a running bridge: start one episode and summarise its stream.

    ~/libero/bin/python -m demo_bridge.smoke_client --suite libero_spatial --task-id 0
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import urllib.request

import websockets


def http(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://localhost:8000")
    p.add_argument("--suite", default="libero_spatial")
    p.add_argument("--task-id", type=int, default=0)
    args = p.parse_args()

    health = http("GET", f"{args.base}/api/health")
    print("health:", json.dumps(health))
    t0 = time.perf_counter()
    ep = http("POST", f"{args.base}/api/episodes", {"suite": args.suite, "task_id": args.task_id})
    print("episode:", ep["episode_id"], "|", ep["instruction"])
    counts: dict[str, int] = {}
    totals, rtts, frame_bytes = [], [], 0
    t_started = None
    async with websockets.connect(ep["ws_url"], max_size=2**24) as ws:
        async for raw in ws:
            msg = json.loads(raw)
            counts[msg["type"]] = counts.get(msg["type"], 0) + 1
            if msg["type"] == "started":
                t_started = time.perf_counter()
                print(f"started after {t_started - t0:.1f} s:", {k: msg[k] for k in ("max_steps", "fps", "image_size")})
            elif msg["type"] == "chunk":
                totals.append(msg["board"]["total_ms"])
                rtts.append(msg["rtt_ms"])
                print(f"  chunk {msg['chunk']} at step {msg['step']}: board {msg['board']['total_ms']:.0f} ms, rtt {msg['rtt_ms']:.0f} ms")
            elif msg["type"] == "frame":
                frame_bytes += len(raw)
            elif msg["type"] in ("ended", "error"):
                print(msg["type"], json.dumps(msg))
    n = counts.get("frame", 1)
    print("messages:", counts, f"| avg frame message {frame_bytes / n / 1024:.0f} KiB")
    if totals:
        print(f"board total_ms {min(totals):.0f}-{max(totals):.0f}, rtt {min(rtts):.0f}-{max(rtts):.0f} ms")
    if t_started:
        print(f"stream time after started: {time.perf_counter() - t_started:.1f} s")
    print("summary:", json.dumps(http("GET", f"{args.base}/api/episodes/{ep['episode_id']}")))


if __name__ == "__main__":
    asyncio.run(main())
