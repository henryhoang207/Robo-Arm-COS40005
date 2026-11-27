"""SimPort + BoardPort over the X-VLA demo bridge (`demo_bridge/` at the repo root).

`SO101_SIM_LINK=libero` and `SO101_BOARD_LINK=libero`, used together. The bridge runs the
LIBERO simulation (Franka Panda) and calls X-VLA W8A16 on the VENTUNO Q board's NPU itself,
so it is both the simulator and the AI path here:

| Port            | Bridge                                                         |
|-----------------|----------------------------------------------------------------|
| get_state       | GET  /api/state  (board + current episode, one poll)           |
| reset           | nothing to send: the bridge keeps its scene reset ahead of time |
| send_prompt     | POST /api/episodes {suite, task_id, instruction, seed}          |
| get_evaluation  | GET  /api/state  -> episode.result                              |
| stop            | POST /api/episodes/{id}/stop                                    |
| release_hold    | local only (the bridge has no HOLD)                             |
| get_frame       | GET  /api/camera/{agentview|wrist}                              |

Mapping choices:
- The scene is the protocol's `object`, e.g. "libero_goal/8".
- There are no SO-101 joints. `joint_positions` is empty and the runner sends no SO-101
  `telemetry`. The Panda's 7 measured joints, gripper (open/closed, from the action) and
  end-effector position from this run's latest frame go in `SimState.arm` and reach the web
  as `arm_state`, never under SO-101 joint names.
- STOP counts as held only once the bridge reports the episode ended with `stopped`
  (never on the 202), or at once if no episode was started yet.
- Bridge results: success -> success; failure (step cap) -> timeout; unscored -> failure
  with code `unscored`; stopped -> aborted; error -> error with the bridge's code.
"""

from __future__ import annotations

from typing import Any

import httpx

from .ports import (
    ArmSample,
    BoardError,
    Evaluation,
    ResetResult,
    SimBadPayload,
    SimError,
    SimRejected,
    SimState,
)
from .settings import Settings

CAMERA_MAP = {"overhead": "agentview", "wrist": "wrist"}
FPS = 20


def parse_scene(target: str) -> tuple[str, int]:
    suite, _, task = target.partition("/")
    if not suite.startswith("libero_") or not task.isdigit():
        raise SimRejected(f"scene must look like libero_goal/8, got {target!r}")
    return suite, int(task)


class LiberoSim:
    kind = "libero"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._http = client or httpx.AsyncClient(
            base_url=settings.libero_url, timeout=settings.sim_timeout_ms / 1000
        )
        self._scene: tuple[str, int] | None = None
        self._sim_run_id: str | None = None
        self._episode_id: str | None = None
        self._stop_requested = False

    async def aclose(self) -> None:
        await self._http.aclose()

    # --- bridge I/O ------------------------------------------------------------

    async def _bridge_state(self) -> dict[str, Any]:
        try:
            resp = await self._http.get("/api/state")
        except httpx.HTTPError as exc:
            raise SimError(f"demo bridge unreachable: {exc.__class__.__name__}") from exc
        if resp.status_code != 200:
            raise SimError(f"GET /api/state returned HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise SimBadPayload("GET /api/state: not JSON", resp.text[:200]) from exc
        if not isinstance(data, dict) or data.get("bridge") != "ok" or not isinstance(data.get("board"), dict):
            raise SimBadPayload("not a demo bridge /api/state", data)
        return data

    def _ours(self, data: dict[str, Any]) -> dict[str, Any] | None:
        ep = data.get("episode")
        if isinstance(ep, dict) and self._episode_id and ep.get("episode_id") == self._episode_id:
            return ep
        return None

    def _held(self, ours: dict[str, Any] | None) -> bool:
        return self._stop_requested and (ours is None or ours.get("state") == "ended")

    # --- SimPort ---------------------------------------------------------------

    async def get_state(self) -> SimState:
        data = await self._bridge_state()
        ours = self._ours(data)
        hold = self._held(ours)
        running = ours is not None and ours.get("state") in ("starting", "running")
        status = "HOLD" if hold else "RUNNING" if running else "READY"
        episode_status = _episode_status(ours)
        step = int(ours.get("step") or 0) if ours else 0
        chunks = int(ours.get("chunks") or 0) if ours else 0
        raw = {
            "source": "demo_bridge",
            "run_id": self._sim_run_id,
            "status": status,
            "hold_latched": hold,
            "hold_origin": "USER_ABORT" if hold else None,
            "episode": {"status": episode_status, "reason": (ours or {}).get("result")},
            "bridge": data,
        }
        return SimState(
            status=status,
            board_connected=bool(data["board"].get("reachable")),
            sim_time=step / FPS,
            accepted_sequence=chunks * 30,
            applied_sequence=step,
            joint_positions=(),
            joint_targets=None,
            hold=hold,
            hold_reason="stop" if hold else None,
            local=False,
            sim_run_id=self._sim_run_id,
            episode_status=episode_status,
            arm=_panda_sample(ours),
            raw=raw,
        )

    async def reset(self, seed: int, run_id: int, target: str) -> ResetResult:
        """Nothing to send: the bridge prepares its scene itself. Clears the previous episode so
        its result can never finish this run, and gives this run its own sim id."""
        scene = parse_scene(target)
        data = await self._bridge_state()
        if data.get("episode_running"):
            raise SimRejected("demo bridge is still running another episode")
        self._scene = scene
        self._episode_id = None
        self._stop_requested = False
        self._sim_run_id = f"libero-{run_id}"
        raw = {"scene": target, "seed": seed, "scenes_ready": data.get("scenes_ready"),
               "board": data["board"]}  # fmt: skip
        return ResetResult(sim_run_id=self._sim_run_id, raw=raw)

    async def start(self, task_text: str, seed: int) -> None:
        """Called by LiberoBoard.send_prompt: the bridge starts the episode on the board."""
        if self._scene is None:
            raise BoardError("no scene: reset was not called")
        if self._stop_requested:
            raise BoardError("stopped before the prompt was sent")
        suite, task_id = self._scene
        body = {"suite": suite, "task_id": task_id, "instruction": task_text, "seed": seed}
        try:
            resp = await self._http.post("/api/episodes", json=body)
        except httpx.HTTPError as exc:
            raise BoardError(f"demo bridge unreachable: {exc.__class__.__name__}") from exc
        if resp.status_code != 201:
            try:
                err = resp.json().get("error", {})
            except (ValueError, AttributeError):
                err = {}
            raise BoardError(f"bridge refused ({resp.status_code} {err.get('code')}): {err.get('message')}")
        self._episode_id = resp.json()["episode_id"]

    async def stop(self) -> None:
        self._stop_requested = True
        if self._episode_id is None:
            return  # nothing started: held at once
        try:
            resp = await self._http.post(f"/api/episodes/{self._episode_id}/stop")
        except httpx.HTTPError as exc:
            raise SimError(f"stop failed: {exc.__class__.__name__}") from exc
        if resp.status_code not in (202, 409):  # 409: it had already ended
            raise SimError(f"stop returned HTTP {resp.status_code}")

    async def release_hold(self) -> None:
        self._stop_requested = False

    async def get_evaluation(self) -> Evaluation | None:
        ours = self._ours(await self._bridge_state())
        base: dict[str, Any] = {"sim_run_id": self._sim_run_id, "raw": ours or {}}
        if ours is None or ours.get("state") != "ended":
            return Evaluation(final=False, **base)
        result = ours.get("result")
        if result == "success":
            return Evaluation(final=True, outcome="success", **base)
        if result == "failure":
            return Evaluation(final=True, outcome="timeout", reason_code="timeout", **base)
        if result == "unscored":
            return Evaluation(final=True, outcome="failure", reason_code="unscored",
                              reason_text="prompt not scored", **base)  # fmt: skip
        if result == "stopped":
            return Evaluation(final=True, outcome="aborted", reason_code="user_abort", **base)
        code = (ours.get("error") or {}).get("code") or "bridge_error"
        return Evaluation(final=True, outcome="error", reason_code=code, **base)

    async def get_frame(self, camera: str) -> bytes:
        name = CAMERA_MAP.get(camera)
        if name is None:
            raise SimError(f"unknown camera {camera}")
        try:
            resp = await self._http.get(f"/api/camera/{name}")
        except httpx.HTTPError as exc:
            raise SimError(f"camera {camera} unreachable: {exc.__class__.__name__}") from exc
        if resp.status_code == 404:
            return b""  # no episode yet: the web shows no picture
        if resp.status_code != 200:
            raise SimError(f"camera {camera} returned HTTP {resp.status_code}")
        return resp.content

    async def preview_goal(self, text: str, scene: str) -> dict[str, Any]:
        """What the bridge would score this prompt against in `scene` (for the prompt box)."""
        suite, task_id = parse_scene(scene)
        try:
            resp = await self._http.post(
                "/api/goals/parse", json={"suite": suite, "task_id": task_id, "instruction": text}
            )
        except httpx.HTTPError as exc:
            raise SimError(f"demo bridge unreachable: {exc.__class__.__name__}") from exc
        if resp.status_code != 200:
            raise SimError(f"goal preview returned HTTP {resp.status_code}")
        return resp.json()


def _panda_sample(ours: dict[str, Any] | None) -> ArmSample | None:
    """This run's latest Panda frame from the bridge's episode summary, or None.

    Shape problems are not fixed up here: `adapter.to_arm_state` refuses them and the
    runner quarantines the raw state.
    """
    if not ours or not isinstance(ours.get("joint_pos_rad"), list):
        return None
    eef = ours.get("eef_pos_m")
    step = ours.get("step")
    raw_plan = ours.get("planned_eef_pos_m")
    planned = (
        tuple(tuple(pt) for pt in raw_plan)
        if isinstance(raw_plan, list) and raw_plan and all(isinstance(pt, list) for pt in raw_plan)
        else None
    )
    return ArmSample(
        arm="panda",
        joints_rad=tuple(ours["joint_pos_rad"]),
        gripper=ours.get("gripper") if isinstance(ours.get("gripper"), str) else None,
        eef_m=tuple(eef) if isinstance(eef, list) and len(eef) == 3 else None,
        step=step if isinstance(step, int) else None,
        planned_eef_m=planned,
    )


def _episode_status(ours: dict[str, Any] | None) -> str:
    if ours is None:
        return "READY"
    if ours.get("state") != "ended":
        return "RUNNING"
    return {"success": "SUCCESS", "stopped": "ABORTED", "error": "ABORTED"}.get(ours.get("result"), "FAILURE")


class LiberoBoard:
    """BoardPort: the bridge drives the board, so delivering the prompt = starting the episode."""

    kind = "libero"

    def __init__(self, sim: Any) -> None:
        if not isinstance(sim, LiberoSim):
            raise ValueError("SO101_BOARD_LINK=libero needs SO101_SIM_LINK=libero")
        self.sim = sim

    async def send_prompt(self, run_id: int, profile_id: str, task_text: str, seed: int) -> None:
        await self.sim.start(task_text, seed)
