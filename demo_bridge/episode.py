"""One closed-loop episode: LIBERO sim on the laptop, X-VLA on the board, messages out to the browser."""
from __future__ import annotations

import base64
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Imported here, at bridge start, not lazily: a cold `import av` took 1.6 s on 26 Nov and holds
# Python's lock. Inside the first episode that stalled every HTTP poll long enough for the web
# backend to call the bridge offline.
import av
import cv2
import numpy as np

from .board import BoardClient, BoardError

log = logging.getLogger("bridge.episode")
Emit = Callable[[dict], None]


@dataclass(frozen=True)
class EpisodeSpec:
    episode_id: str
    suite: str
    task_id: int
    instruction: str
    custom_instruction: bool
    seed: int
    max_steps: int
    goal: dict  # from goals.resolve(): what success is checked against


def public_goal(goal: dict) -> dict:
    return {k: goal[k] for k in ("scored", "source", "label", "conditions", "reason")}


def upright(img: np.ndarray) -> np.ndarray:
    """LIBERO renders upside down; rotate 180 degrees for display."""
    return np.ascontiguousarray(img[::-1, ::-1])


def jpeg_b64(rgb: np.ndarray, quality: int = 80) -> str:
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


class VideoWriter:
    """Writes agentview | wrist side by side as an MP4 while the episode runs. Never raises."""

    def __init__(self, path: Path, fps: int):
        self.path = path
        self.fps = fps
        self._container = None
        self._stream = None
        self.ok = True

    def add(self, left: np.ndarray, right: np.ndarray) -> None:
        if not self.ok:
            return
        try:
            frame = np.concatenate([left, right], axis=1)
            if self._container is None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._container = av.open(str(self.path), mode="w")
                try:
                    self._stream = self._container.add_stream("libx264", rate=self.fps)
                except Exception:
                    self._stream = self._container.add_stream("mpeg4", rate=self.fps)
                self._stream.width = frame.shape[1]
                self._stream.height = frame.shape[0]
                self._stream.pix_fmt = "yuv420p"
            for packet in self._stream.encode(av.VideoFrame.from_ndarray(frame, format="rgb24")):
                self._container.mux(packet)
        except Exception as exc:
            log.warning("video disabled for %s: %s", self.path.name, exc)
            self.ok = False

    def close(self) -> bool:
        """Finish the file; True when a playable MP4 was written."""
        if self._container is None:
            return False
        try:
            for packet in self._stream.encode():
                self._container.mux(packet)
            self._container.close()
        except Exception as exc:
            log.warning("video finalise failed for %s: %s", self.path.name, exc)
            self.ok = False
        return self.ok


class Episode:
    def __init__(self, spec: EpisodeSpec, emit: Emit):
        self.spec = spec
        self._emit = emit
        self._stop = threading.Event()
        self.state = "starting"  # starting -> running -> ended
        self.step = 0
        self.chunks = 0
        self.result: str | None = None
        self.wall_s: float | None = None
        self.video_path: Path | None = None
        self.error: dict | None = None  # {"code", "message"} when result is "error"
        self._t_started: float | None = None

    def request_stop(self) -> None:
        self._stop.set()

    @property
    def stop_requested(self) -> bool:
        return self._stop.is_set()

    def summary(self) -> dict:
        wall = self.wall_s
        if wall is None and self._t_started is not None:
            wall = time.perf_counter() - self._t_started
        return {
            "episode_id": self.spec.episode_id,
            "state": self.state,
            "suite": self.spec.suite,
            "task_id": self.spec.task_id,
            "instruction": self.spec.instruction,
            "custom_instruction": self.spec.custom_instruction,
            "seed": self.spec.seed,
            "max_steps": self.spec.max_steps,
            "goal": public_goal(self.spec.goal),
            "step": self.step,
            "chunks": self.chunks,
            "result": self.result,
            "wall_s": None if wall is None else round(wall, 2),
            "video_url": self.video_url,
            "error": self.error,
        }

    @property
    def video_url(self) -> str | None:
        return f"/api/episodes/{self.spec.episode_id}/video" if self.video_path is not None else None

    def _frame_msg(self, obs, reward: float, gripper: str, jpeg_quality: int, fps: int) -> dict:
        return {
            "type": "frame",
            "step": self.step,
            "t_sim_s": round(self.step / fps, 3),
            "agentview": jpeg_b64(upright(obs.agentview), jpeg_quality),
            "wrist": jpeg_b64(upright(obs.wrist), jpeg_quality),
            "eef_pos_m": [round(float(v), 4) for v in obs.eef_pos],
            "gripper": gripper,
            "joint_pos_rad": [round(float(v), 4) for v in obs.joint_pos],
            "reward": round(reward, 4),
        }

    def run(self, scenes, board: BoardClient, video_dir: Path, *, fps: int = 20, realtime: bool = True,
            jpeg_quality: int = 80) -> None:
        """Blocking; call on the sim thread. Always ends with one `ended` message."""
        spec = self.spec
        video = VideoWriter(video_dir / f"{spec.episode_id}.mp4", fps)
        success = False
        mode = spec.goal["mode"]
        conditions = spec.goal["conditions"] or []
        try:
            scene = scenes.get(spec.suite, spec.task_id)
            if self.stop_requested:
                self.result = "stopped"
                return
            obs = scenes.reset(spec.suite, spec.task_id, spec.seed)
            if mode == "conditions" and not scene.has_states({n for c in conditions for n in c[1:]}):
                raise RuntimeError(f"goal names objects this scene does not have: {conditions}")
            self.state = "running"
            self._t_started = time.perf_counter()
            h, w = obs.agentview.shape[:2]
            self._emit({
                "type": "started",
                "episode_id": spec.episode_id,
                "suite": spec.suite,
                "task_id": spec.task_id,
                "instruction": spec.instruction,
                "custom_instruction": spec.custom_instruction,
                "max_steps": spec.max_steps,
                "fps": fps,
                "cameras": ["agentview", "wrist"],
                "image_size": [int(h), int(w)],
                "goal": public_goal(spec.goal),
            })
            gripper = "open"
            self._emit(self._frame_msg(obs, 0.0, gripper, jpeg_quality, fps))
            video.add(upright(obs.agentview), upright(obs.wrist))
            rng = np.random.default_rng(spec.seed)
            queue: list[np.ndarray] = []
            dt = 1.0 / fps
            with board.connect() as session:
                next_t = time.perf_counter()
                while self.step < spec.max_steps and not self.stop_requested:
                    if not queue:
                        noise = rng.standard_normal((1, 30, 20)).astype(np.float32)
                        actions, timings, rtt_ms = session.infer(
                            obs.agentview, obs.wrist, spec.instruction, obs.eef_pos, obs.eef_mat, noise)
                        self.chunks += 1
                        self._emit({
                            "type": "chunk",
                            "chunk": self.chunks,
                            "step": self.step,
                            "rtt_ms": round(rtt_ms, 1),
                            "board": timings,
                            "planned_eef_pos_m": [[round(float(v), 4) for v in a[:3]] for a in actions],
                        })
                        queue = list(actions)
                        next_t = time.perf_counter()
                        if self.stop_requested:
                            break
                    action = queue.pop(0)
                    obs, reward, scene_goal_met, horizon = scene.step(action)
                    self.step += 1
                    if mode == "scene":
                        success = scene_goal_met
                    elif mode == "conditions":
                        success = scene.check(conditions)
                    gripper = "closed" if float(action[6]) > 0 else "open"
                    self._emit(self._frame_msg(obs, reward, gripper, jpeg_quality, fps))
                    video.add(upright(obs.agentview), upright(obs.wrist))
                    if success or horizon:
                        break
                    if realtime:
                        next_t += dt
                        delay = next_t - time.perf_counter()
                        if delay > 0:
                            time.sleep(delay)
                        else:
                            next_t = time.perf_counter()
            if success:
                self.result = "success"
            elif self.stop_requested:
                self.result = "stopped"
            elif mode == "none":
                self.result = "unscored"
            else:
                self.result = "failure"
        except BoardError as exc:
            log.warning("episode %s board failure: %s", spec.episode_id, exc.message)
            self.result = "error"
            self.error = {"code": exc.code, "message": exc.message}
            self._emit({"type": "error", **self.error})
        except Exception as exc:  # sim, rendering or encoding failure
            log.exception("episode %s sim failure", spec.episode_id)
            self.result = "error"
            self.error = {"code": "sim_error", "message": f"{type(exc).__name__}: {exc}"}
            self._emit({"type": "error", **self.error})
        finally:
            if video.close():
                self.video_path = video.path
            if self._t_started is not None:
                self.wall_s = time.perf_counter() - self._t_started
            self.state = "ended"
            self._emit({
                "type": "ended",
                "result": self.result,
                "goal": public_goal(spec.goal),
                "steps": self.step,
                "chunks": self.chunks,
                "wall_s": None if self.wall_s is None else round(self.wall_s, 2),
                "video_url": self.video_url,
            })
