"""Record a set of prompts in the demo Goal scene through a running bridge.

For each prompt: start an episode, save the MP4, a frame strip (front camera every 60 steps plus the
final frame) and one results row. Already-recorded prompts are skipped, so a run that stops because
the board went away can simply be started again.

    ~/libero/bin/python -m demo_bridge.record_prompts --out demo_bridge/recordings/2026-11-26
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import websockets

SCENE = ("libero_goal", 8)
PROMPTS = [
    ("own_bowl_plate", "put the bowl on the plate"),
    ("task1_bowl_stove", "put the bowl on the stove"),
    ("task7_stove_on", "turn on the stove"),
    ("task0_middle_drawer", "open the middle drawer of the cabinet"),
    ("task9_wine_rack", "put the wine bottle on the rack"),
    ("task2_wine_cabinet", "put the wine bottle on top of the cabinet"),
    ("task6_cheese_bowl", "put the cream cheese in the bowl"),
    ("task5_plate_front", "push the plate to the front of the stove"),
    ("task4_bowl_cabinet", "put the bowl on top of the cabinet"),
    ("task3_bowl_drawer", "open the top drawer and put the bowl inside"),
    ("new_cheese_plate", "put the cream cheese on the plate"),
    ("new_wine_plate", "put the wine bottle on the plate"),
    ("new_cheese_stove", "put the cream cheese on the stove"),
    ("unscored_wave", "wave hello"),
]
UNSCORED_STOP_AFTER_STEPS = 120


def http(method, url, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = resp.read()
    return payload if raw else json.loads(payload)


def decode(b64):
    return cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)


def tag(img, text):
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 22), (0, 0, 0), -1)
    cv2.putText(out, text, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return out


async def record(base, out, name, prompt):
    t0 = time.perf_counter()
    ep = http("POST", f"{base}/api/episodes", {"suite": SCENE[0], "task_id": SCENE[1], "instruction": prompt})
    strip, last, ended, error, board_ms, rtt = {}, None, None, None, [], []
    t_started = None
    async with websockets.connect(ep["ws_url"], max_size=2**24) as ws:
        async for raw in ws:
            m = json.loads(raw)
            if m["type"] == "started":
                t_started = time.perf_counter()
            elif m["type"] == "frame":
                if m["step"] % 60 == 0:
                    strip[m["step"]] = decode(m["agentview"])
                last = m
                if not ep["goal"]["scored"] and m["step"] == UNSCORED_STOP_AFTER_STEPS:
                    http("POST", f"{base}/api/episodes/{ep['episode_id']}/stop")
            elif m["type"] == "chunk":
                board_ms.append(m["board"]["total_ms"])
                rtt.append(m["rtt_ms"])
            elif m["type"] == "error":
                error = m
            elif m["type"] == "ended":
                ended = m
    tiles = [tag(img, f"step {s}") for s, img in sorted(strip.items())][-7:]
    tiles.append(tag(decode(last["agentview"]), f"final step {last['step']}"))
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.concatenate([np.concatenate(tiles[i:i + 4], axis=1) for i in range(0, len(tiles), 4)], axis=0)
    sheet = cv2.resize(sheet, (sheet.shape[1] // 2, sheet.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out / f"{name}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if ended and ended.get("video_url"):
        (out / f"{name}.mp4").write_bytes(http("GET", base + ended["video_url"], raw=True))
    row = {
        "name": name, "prompt": prompt, "episode_id": ep["episode_id"],
        "goal_source": ep["goal"]["source"], "goal_label": ep["goal"]["label"], "conditions": ep["goal"]["conditions"],
        "result": ended and ended["result"], "steps": ended and ended["steps"], "chunks": len(board_ms),
        "start_s": round(t_started - t0, 1) if t_started else None, "wall_s": ended and ended["wall_s"],
        "board_total_ms": [round(min(board_ms)), round(max(board_ms))] if board_ms else None,
        "rtt_ms": [round(min(rtt)), round(max(rtt))] if rtt else None, "error": error,
    }
    print(json.dumps(row), flush=True)
    return row


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://localhost:8000")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results_path = args.out / "results.json"
    rows = json.loads(results_path.read_text()) if results_path.exists() else []
    done = {r["name"] for r in rows if r.get("result") and not r.get("error")}
    rows = [r for r in rows if r["name"] in done]
    for name, prompt in PROMPTS:
        if name in done:
            continue
        try:
            row = await record(args.base, args.out, name, prompt)
        except urllib.error.HTTPError as exc:
            print(json.dumps({"name": name, "http_error": exc.code, "body": exc.read().decode()}), flush=True)
            if exc.code == 503:
                print("board unreachable: stopping; restart the App Lab app and run again to resume", flush=True)
                break
            continue
        rows.append(row)
        results_path.write_text(json.dumps(rows, indent=2))
        if row.get("error") and row["error"].get("code", "").startswith("board"):
            print("board failure: stopping; run again to resume", flush=True)
            break
    order = [n for n, _ in PROMPTS]
    rows.sort(key=lambda r: order.index(r["name"]))
    results_path.write_text(json.dumps(rows, indent=2))
    print(f"recorded {len(rows)}/{len(PROMPTS)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
