"""Demo bridge: HTTP + WebSocket API for the web app, LIBERO sim on the laptop, X-VLA on the board.

Contract: "X-VLA Board Demo - Web Integration Spec" (claude.ai/artifact/4KCDYz7i5oRPXHjzyqB6k6).
Run in WSL from the repo root:
    MUJOCO_GL=egl GALLIUM_DRIVER=d3d12 ~/libero/bin/python -m demo_bridge.app --board-host 10.1.0.119
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from .board import BoardClient, summarize_status
from .episode import Episode, EpisodeSpec, jpeg_b64, public_goal, upright
from .goals import resolve
from .sim import RECOMMENDED, SceneCache

log = logging.getLogger("bridge")
MAX_INSTRUCTION_CHARS = 300
QUEUE_SIZE = 64
HEALTH_POLL_S = 5.0


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


class Hub:
    """Fans an episode's messages out to its WebSocket clients and keeps the latest of each type."""

    REPLAY = ("started", "chunk", "frame", "error", "ended")

    def __init__(self):
        self._latest: dict[str, dict[str, dict]] = {}
        self._subs: dict[str, set[asyncio.Queue]] = {}

    def publish(self, episode_id: str, msg: dict) -> None:
        self._latest.setdefault(episode_id, {})[msg["type"]] = msg
        for q in list(self._subs.get(episode_id, ())):
            if q.full():  # slow client: drop its oldest message, never the newest
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            q.put_nowait(msg)

    def subscribe(self, episode_id: str) -> tuple[asyncio.Queue, list[dict]]:
        q: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._subs.setdefault(episode_id, set()).add(q)
        latest = self._latest.get(episode_id, {})
        return q, [latest[t] for t in self.REPLAY if t in latest]

    def latest(self, episode_id: str, msg_type: str) -> dict | None:
        return self._latest.get(episode_id, {}).get(msg_type)

    def unsubscribe(self, episode_id: str, q: asyncio.Queue) -> None:
        self._subs.get(episode_id, set()).discard(q)


@dataclass
class BridgeConfig:
    max_steps: int = 400
    video_dir: Path = Path.home() / "outputs" / "bridge"
    fps: int = 20
    realtime: bool = True
    preload: tuple = RECOMMENDED
    cors_origins: tuple = ("*",)
    default_seed: int = 1000


@dataclass
class BridgeState:
    board: BoardClient
    scenes: list[dict]
    cache: SceneCache
    config: BridgeConfig
    sim: ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(1, thread_name_prefix="sim"))
    hub: Hub = field(default_factory=Hub)
    episodes: dict[str, Episode] = field(default_factory=dict)
    current: Episode | None = None
    board_status: dict | None = None
    board_checked_at: float = 0.0
    scenes_ready: list[str] = field(default_factory=list)
    preview_jpeg: dict = field(default_factory=dict)  # starting view of the prepared demo scene
    loop: asyncio.AbstractEventLoop | None = None
    _refreshing: asyncio.Future | None = None

    def scene(self, suite: str, task_id: int) -> dict | None:
        return next((s for s in self.scenes if s["suite"] == suite and s["task_id"] == task_id), None)

    @property
    def running(self) -> bool:
        return self.current is not None and self.current.state != "ended"

    async def refresh_board(self) -> dict | None:
        """One board check at a time. While the simulator holds Python's lock (a scene reset),
        polls queue up; without this each would start its own check on the thread pool."""
        if self._refreshing is None or self._refreshing.done():
            self._refreshing = asyncio.ensure_future(self._check_board())
        return await asyncio.shield(self._refreshing)

    def kick_refresh(self) -> None:
        """Start a board check in the background if none is running; never waits."""
        if self._refreshing is None or self._refreshing.done():
            self._refreshing = asyncio.ensure_future(self._check_board())

    async def _check_board(self) -> dict | None:
        self.board_status = await asyncio.to_thread(self.board.status)
        self.board_checked_at = time.monotonic()
        return self.board_status


def create_app(board: BoardClient, scenes: list[dict], cache: SceneCache, config: BridgeConfig | None = None) -> FastAPI:
    st = BridgeState(board=board, scenes=scenes, cache=cache, config=config or BridgeConfig())

    def prepare(suite: str, task_id: int) -> None:
        """Build (if needed) and reset a scene ahead of its next episode. Runs on the sim thread."""
        t0 = time.perf_counter()
        try:
            st.cache.prepare(suite, task_id, st.config.default_seed)
            name = f"{suite}/{task_id}"
            if name not in st.scenes_ready:
                st.scenes_ready.append(name)
            log.info("scene %s/%d ready in %.1f s", suite, task_id, time.perf_counter() - t0)
        except Exception:
            log.exception("preparing %s/%d failed", suite, task_id)

    async def poll_board() -> None:
        while True:
            try:
                await st.refresh_board()
            except Exception:
                log.exception("board status poll failed")
            await asyncio.sleep(HEALTH_POLL_S)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        st.loop = asyncio.get_running_loop()
        # Demo scene (first in the list) last, so it is the one left prepared and ready to start at once.
        for suite, task_id in reversed(st.config.preload):
            st.sim.submit(prepare, suite, task_id)
        poller = asyncio.create_task(poll_board())
        try:
            yield
        finally:
            poller.cancel()
            if st.current is not None:
                st.current.request_stop()
            st.sim.submit(st.cache.close)
            st.sim.shutdown(wait=False)

    app = FastAPI(title="X-VLA demo bridge", lifespan=lifespan)
    app.state.bridge = st
    app.add_middleware(CORSMiddleware, allow_origins=list(st.config.cors_origins),
                       allow_methods=["GET", "POST"], allow_headers=["*"])

    @app.get("/api/health")
    async def health():
        if time.monotonic() - st.board_checked_at > HEALTH_POLL_S + 1:
            await st.refresh_board()
        return {
            "bridge": "ok",
            "episode_running": st.running,
            "board": summarize_status(st.board.host, st.board_status),
            "scenes_ready": list(st.scenes_ready),
        }

    @app.get("/api/scenes")
    async def list_scenes():
        return st.scenes

    @app.post("/api/episodes", status_code=201)
    async def start_episode(request: Request):
        try:
            body = await request.json()
        except Exception:
            return error(422, "bad_request", "body must be JSON")
        if not isinstance(body, dict):
            return error(422, "bad_request", "body must be a JSON object")
        suite, task_id = body.get("suite"), body.get("task_id")
        scene = st.scene(suite, task_id) if isinstance(suite, str) and type(task_id) is int else None
        if scene is None:
            return error(422, "bad_scene", f"unknown scene {suite!r} / {task_id!r}; see GET /api/scenes")
        seed = body.get("seed", st.config.default_seed)
        if seed is None:
            seed = st.config.default_seed
        if type(seed) is not int or not 0 <= seed < 2**31:
            return error(422, "bad_request", "seed must be a non-negative integer")
        text = body.get("instruction")
        if text is not None and not isinstance(text, str):
            return error(422, "bad_request", "instruction must be a string or null")
        text = (text or "").strip() or scene["instruction"]
        if len(text) > MAX_INSTRUCTION_CHARS:
            return error(422, "bad_request", f"instruction is longer than {MAX_INSTRUCTION_CHARS} characters")
        if st.running:
            return error(409, "episode_running", "an episode is already running")
        # A reachable status from the last poll is good enough: callers such as the web backend
        # give the start about 2 s, and a fresh check can take up to 2 s on its own.
        fresh = time.monotonic() - st.board_checked_at <= HEALTH_POLL_S + 1
        if not (fresh and st.board_status is not None) and await st.refresh_board() is None:
            return error(503, "board_unreachable", f"board {st.board.host} is not answering; start the App Lab app")
        if st.running:  # another start won the race while we checked the board
            return error(409, "episode_running", "an episode is already running")

        episode_id = time.strftime("ep_%Y%m%d_%H%M%S")
        n = 1
        while episode_id in st.episodes:
            n += 1
            episode_id = f"{time.strftime('ep_%Y%m%d_%H%M%S')}_{n}"
        goal = resolve(suite, scene["instruction"], text)
        spec = EpisodeSpec(episode_id, suite, task_id, text, text != scene["instruction"], seed,
                           st.config.max_steps, goal)
        loop = st.loop or asyncio.get_running_loop()
        episode = Episode(spec, lambda msg: loop.call_soon_threadsafe(st.hub.publish, episode_id, msg))
        st.episodes[episode_id] = episode
        st.current = episode
        st.sim.submit(episode.run, st.cache, st.board, st.config.video_dir,
                      fps=st.config.fps, realtime=st.config.realtime)
        if (suite, task_id) in st.config.preload:  # reset it again now, so the next run starts at once
            st.sim.submit(prepare, suite, task_id)
        host = request.headers.get("host", "localhost:8002")
        return {"episode_id": episode_id, "ws_url": f"ws://{host}/ws/episodes/{episode_id}",
                "instruction": text, "custom_instruction": spec.custom_instruction, "goal": public_goal(goal)}

    @app.post("/api/goals/parse")
    async def parse_goal(request: Request):
        """What a prompt would be scored against, without starting anything (for the prompt box)."""
        try:
            body = await request.json()
        except Exception:
            return error(422, "bad_request", "body must be JSON")
        suite, task_id = body.get("suite"), body.get("task_id")
        scene = st.scene(suite, task_id) if isinstance(suite, str) and type(task_id) is int else None
        if scene is None:
            return error(422, "bad_scene", f"unknown scene {suite!r} / {task_id!r}; see GET /api/scenes")
        text = body.get("instruction")
        if text is not None and not isinstance(text, str):
            return error(422, "bad_request", "instruction must be a string or null")
        text = (text or "").strip() or scene["instruction"]
        return {"instruction": text, "custom_instruction": text != scene["instruction"],
                "goal": public_goal(resolve(suite, scene["instruction"], text))}

    @app.get("/api/episodes/{episode_id}")
    async def get_episode(episode_id: str):
        episode = st.episodes.get(episode_id)
        if episode is None:
            return error(404, "not_found", f"no episode {episode_id}")
        return episode.summary()

    @app.post("/api/episodes/{episode_id}/stop", status_code=202)
    async def stop_episode(episode_id: str):
        episode = st.episodes.get(episode_id)
        if episode is None:
            return error(404, "not_found", f"no episode {episode_id}")
        if episode.state == "ended":
            return error(409, "not_running", f"episode {episode_id} has already ended")
        episode.request_stop()
        return {"episode_id": episode_id, "stopping": True}

    @app.get("/api/episodes/{episode_id}/video")
    async def episode_video(episode_id: str):
        episode = st.episodes.get(episode_id)
        if episode is None or episode.state != "ended" or episode.video_path is None or not episode.video_path.exists():
            return error(404, "not_found", f"no video for episode {episode_id}")
        return FileResponse(episode.video_path, media_type="video/mp4", filename=episode.video_path.name)

    @app.get("/api/state")
    async def bridge_state():
        """One poll for clients that do not use the WebSocket (the web backend's adapter):
        the board, and the current or most recent episode. Answers from the cached board status
        (the background poll keeps it fresh), so a poll never waits on the board."""
        if st.board_checked_at == 0.0:
            await st.refresh_board()
        elif time.monotonic() - st.board_checked_at > HEALTH_POLL_S + 1:
            st.kick_refresh()
        episode = st.current.summary() if st.current is not None else None
        if episode is not None:
            frame = st.hub.latest(episode["episode_id"], "frame")
            if frame is not None:
                episode["eef_pos_m"] = frame["eef_pos_m"]
                episode["gripper"] = frame["gripper"]
                episode["joint_pos_rad"] = frame["joint_pos_rad"]
        return {
            "bridge": "ok",
            "episode_running": st.running,
            "board": summarize_status(st.board.host, st.board_status),
            "scenes_ready": list(st.scenes_ready),
            "episode": episode,
        }

    @app.get("/api/camera/{camera}")
    async def camera_frame(camera: str):
        """Live JPEG of the running episode. While idle: the demo scene's starting view once it is
        prepared, otherwise the last frame of the most recent episode. `agentview` or `wrist`."""
        if camera not in ("agentview", "wrist"):
            return error(404, "not_found", f"no camera {camera}; use agentview or wrist")
        if not st.running and st.config.preload:
            suite, task_id = st.config.preload[0]
            obs = st.cache.prepared_observation(suite, task_id, st.config.default_seed)
            if obs is not None:
                cache = st.preview_jpeg  # encoded once per prepared scene and camera
                if cache.get("obs_id") != id(obs):
                    cache.clear()
                    cache["obs_id"] = id(obs)
                if camera not in cache:
                    image = obs.agentview if camera == "agentview" else obs.wrist
                    cache[camera] = base64.b64decode(jpeg_b64(upright(image)))
                return Response(cache[camera], media_type="image/jpeg", headers={"Cache-Control": "no-store"})
        frame = st.hub.latest(st.current.spec.episode_id, "frame") if st.current is not None else None
        if frame is None:
            return error(404, "not_found", "no frame yet")
        return Response(base64.b64decode(frame[camera]), media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})

    @app.websocket("/ws/episodes/{episode_id}")
    async def episode_stream(ws: WebSocket, episode_id: str):
        await ws.accept()
        if episode_id not in st.episodes:
            await ws.close(code=4404, reason="unknown episode")
            return
        q, replay = st.hub.subscribe(episode_id)
        try:
            for msg in replay:
                await ws.send_json(msg)
                if msg["type"] == "ended":
                    await ws.close()
                    return
            while True:
                msg = await q.get()
                await ws.send_json(msg)
                if msg["type"] == "ended":
                    await ws.close()
                    return
        except WebSocketDisconnect:
            pass
        finally:
            st.hub.unsubscribe(episode_id, q)

    return app


def main() -> None:
    p = argparse.ArgumentParser(description="X-VLA demo bridge (LIBERO sim + VENTUNO Q board)")
    p.add_argument("--board-host", default="10.1.0.119")
    p.add_argument("--board-port", type=int, default=8766)
    p.add_argument("--status-port", type=int, default=8080)
    p.add_argument("--board-timeout", type=float, default=10.0, help="seconds to wait for one board reply")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8002)
    p.add_argument("--max-steps", type=int, default=400, help="step cap per episode; LIBERO Goal demos need at most 270")
    p.add_argument("--video-dir", type=Path, default=Path.home() / "outputs" / "bridge")
    p.add_argument("--no-preload", action="store_true", help="do not build the recommended scenes at startup")
    p.add_argument("--no-realtime", action="store_true", help="play actions as fast as the sim runs")
    p.add_argument("--cors", default="*", help="comma-separated allowed origins")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    import uvicorn

    from .sim import load_scenes

    config = BridgeConfig(
        max_steps=args.max_steps,
        video_dir=args.video_dir,
        realtime=not args.no_realtime,
        preload=() if args.no_preload else RECOMMENDED,
        cors_origins=tuple(o.strip() for o in args.cors.split(",") if o.strip()),
    )
    board = BoardClient(args.board_host, args.board_port, args.status_port, args.board_timeout)
    app = create_app(board, load_scenes(args.max_steps), SceneCache(args.max_steps), config)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
