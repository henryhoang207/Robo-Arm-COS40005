"""The LIBERO link (SO101_SIM_LINK=libero, SO101_BOARD_LINK=libero) against a fake demo bridge.

The fake speaks the bridge's HTTP API (demo_bridge/README.md) through httpx.MockTransport, and
each /api/state poll advances the episode by a few steps. The BE runs for real, as in test_flow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app import adapter
from app.libero_link import LiberoBoard, LiberoSim, parse_scene
from app.main import create_app
from app.ports import ArmSample, BoardError, SimRejected
from app.settings import BACKEND_DIR, Settings
from tests.conftest import BE, FAST, WS, _Server

PROMPT = "put the bowl on the stove"
JPEG = b"\xff\xd8fake-jpeg\xff\xd9"
CMD = {
    "type": "command",
    "text": PROMPT,
    "templateId": "libero_prompt",
    "params": {"object": "libero_goal/8"},
    "profileId": "xvla-libero-w8a16",
}


def cmd(cid: str, **over: Any) -> dict[str, Any]:
    return {**CMD, "id": cid, **over}


class FakeBridge:
    """result: success | failure | unscored | error; end_step: when the episode ends."""

    def __init__(self, result: str = "success", end_step: int = 12, steps_per_poll: int = 1,
                 panda_joints: int | None = None) -> None:  # fmt: skip
        # panda_joints: add the latest frame's Panda data to the episode (the real bridge does);
        # None leaves it out, as before the first frame.
        self.panda_joints = panda_joints
        self.result = result
        self.end_step = end_step
        self.steps_per_poll = steps_per_poll
        self.reachable = True
        self.down = False
        self.start_status = 201
        self.episode: dict[str, Any] | None = None
        self.posts: list[dict[str, Any]] = []
        self.stops: list[str] = []
        self.n = 0

    def _advance(self) -> None:
        ep = self.episode
        if ep is None or ep["state"] == "ended":
            return
        if ep.get("_stop"):
            ep.update(state="ended", result="stopped")
            return
        ep["state"] = "running"
        ep["step"] = min(ep["step"] + self.steps_per_poll, self.end_step)
        ep["chunks"] = ep["step"] // 30 + 1
        if self.panda_joints is not None:
            s = ep["step"]
            ep["joint_pos_rad"] = [round(0.05 * s + 0.1 * i, 4) for i in range(self.panda_joints)]
            ep["gripper"] = "open" if s < 6 else "closed"
            ep["eef_pos_m"] = [-0.2016, round(0.001 * s, 4), 1.1648]
            ep["planned_eef_pos_m"] = [
                [round(-0.2016 + 0.001 * k, 4), round(0.001 * s, 4), 1.1648] for k in range(30)
            ]
        if ep["step"] >= self.end_step:
            ep.update(state="ended", result=self.result)
            if self.result == "error":
                ep["error"] = {"code": "board_timeout", "message": "no reply"}

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("bridge down", request=request)
        path, method = request.url.path, request.method
        if path == "/api/state":
            self._advance()
            ep = {k: v for k, v in self.episode.items() if not k.startswith("_")} if self.episode else None
            running = bool(ep and ep["state"] != "ended")
            board = {"reachable": self.reachable, "host": "10.1.0.119"}
            return httpx.Response(200, json={"bridge": "ok", "episode_running": running, "board": board,
                                             "scenes_ready": ["libero_goal/8"], "episode": ep})  # fmt: skip
        if path == "/api/episodes" and method == "POST":
            body = json.loads(request.content)
            self.posts.append(body)
            if self.start_status != 201:
                return httpx.Response(self.start_status, json={"error": {"code": "board_unreachable", "message": "board down"}})
            self.n += 1
            self.episode = {"episode_id": f"ep_{self.n}", "state": "starting", "step": 0, "chunks": 0,
                            "result": None, "error": None, "instruction": body["instruction"]}  # fmt: skip
            return httpx.Response(201, json={"episode_id": f"ep_{self.n}"})
        if path.endswith("/stop") and method == "POST":
            self.stops.append(path)
            if self.episode is None or self.episode["state"] == "ended":
                return httpx.Response(409, json={"error": {"code": "not_running"}})
            self.episode["_stop"] = True
            return httpx.Response(202, json={"stopping": True})
        if path.startswith("/api/camera/"):
            if self.episode is None:
                return httpx.Response(404, json={"error": {"code": "not_found"}})
            return httpx.Response(200, content=JPEG + path.rsplit("/", 1)[1].encode())
        if path == "/api/goals/parse":
            text = json.loads(request.content)["instruction"]
            return httpx.Response(200, json={"instruction": text, "goal": {"scored": True, "label": text}})
        return httpx.Response(404)


def libero_settings(tmp_path: Path, **over: Any) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        sim_link="libero",
        board_link="libero",
        protocol_file=BACKEND_DIR / "config" / "protocol.libero.json",
        profiles_file=BACKEND_DIR / "config" / "profiles.libero.json",
        **{**FAST, **over},
    )


def make_sim(settings: Settings, bridge: FakeBridge) -> LiberoSim:
    client = httpx.AsyncClient(transport=httpx.MockTransport(bridge.handle), base_url="http://bridge")
    return LiberoSim(settings, client=client)


@pytest.fixture
def make_libero(tmp_path: Path):
    servers: list[tuple[_Server, httpx.Client]] = []

    def make(bridge: FakeBridge | None = None, **over: Any) -> tuple[BE, FakeBridge]:
        bridge = bridge or FakeBridge()
        settings = libero_settings(tmp_path, **over)
        sim = make_sim(settings, bridge)
        app = create_app(settings, sim=sim, board=LiberoBoard(sim))
        server = _Server(app)
        server.start()
        url = f"http://127.0.0.1:{server.port}"
        http = httpx.Client(base_url=url, timeout=10)
        servers.append((server, http))
        be = BE(url, f"ws://127.0.0.1:{server.port}/ws", http, sim, None, app, settings)  # type: ignore[arg-type]
        be.wait(lambda: be.core.state.sim_ok is True)
        return be, bridge

    yield make
    for server, http in servers:
        http.close()
        server.stop()


# --- end to end through the real BE -------------------------------------------


def test_free_prompt_run_succeeds_and_reaches_the_bridge(make_libero):
    be, bridge = make_libero()
    ws = be.ws()
    status = ws.status(lambda m: True)
    assert status["link"]["driver"] == "board"
    ws.send(cmd("c1"))
    assert ws.reply("c1")["type"] == "ack"
    running = ws.task("running")
    assert running["task"]["profileId"] == "xvla-libero-w8a16" and running["task"]["seed"] == 1000
    done = ws.task("done", timeout=6)
    assert done["task"]["outcome"] == "success"
    assert bridge.posts == [{"suite": "libero_goal", "task_id": 8, "instruction": PROMPT, "seed": 1000}]
    row = be.db("SELECT phase, outcome, policy_task_text, ui_text FROM runs")[0]
    assert row == ("finished", "success", PROMPT, PROMPT)
    # No SO-101 joints exist here: no joint telemetry, and nothing quarantined.
    assert not [m for m in ws.seen if m["type"] == "telemetry"]
    assert be.db("SELECT COUNT(*) FROM quarantine")[0][0] == 0
    ws.close()


@pytest.mark.parametrize("result,outcome,code", [
    ("failure", "timeout", "timeout"),
    ("unscored", "failure", "unscored"),
])
def test_bridge_results_map_to_be_outcomes(make_libero, result, outcome, code):
    be, _ = make_libero(FakeBridge(result=result))
    ws = be.ws()
    ws.send(cmd("c1"))
    ws.task("running")
    ws.until(lambda m: m["type"] == "task" and m["task"]["state"] in ("done", "failed"), timeout=6)
    assert be.db("SELECT outcome, reason_code FROM runs")[0] == (outcome, code)
    ws.close()


def test_bridge_error_ends_the_run_with_its_code(make_libero):
    be, _ = make_libero(FakeBridge(result="error"))
    ws = be.ws()
    ws.send(cmd("c1"))
    ws.task("running")
    ws.until(lambda m: m["type"] == "task" and m["task"]["state"] == "failed", timeout=6)
    assert be.db("SELECT outcome, reason_code FROM runs")[0] == ("error", "board_timeout")
    ws.close()


def test_stop_waits_for_the_bridge_then_ready_allows_the_next_run(make_libero):
    be, bridge = make_libero(FakeBridge(end_step=10_000))
    ws = be.ws()
    ws.send(cmd("c1"))
    ws.task("running")
    ws.send({"type": "stop", "id": "s1"})
    ws.until(lambda m: m["type"] == "stop_ack")
    assert bridge.stops == ["/api/episodes/ep_1/stop"]
    assert be.db("SELECT outcome FROM runs")[0] == ("aborted",)
    ws.send(cmd("c2"))
    assert ws.reply("c2")["code"] == "needs_ready"
    ws.send({"type": "ready", "id": "r1"})
    ws.status(lambda m: m["robot"]["state"] == "ready")
    bridge.end_step = 5  # the next episode ends normally
    ws.send(cmd("c3"))
    assert ws.reply("c3")["type"] == "ack"
    ws.task("done", timeout=6)
    ws.close()


def test_bridge_refusing_the_start_fails_the_run_before_it_runs(make_libero):
    bridge = FakeBridge()
    bridge.start_status = 503
    be, _ = make_libero(bridge)
    ws = be.ws()
    ws.send(cmd("c1"))
    ws.until(lambda m: m["type"] == "task" and m["task"]["state"] == "failed", timeout=6)
    assert be.db("SELECT outcome, reason_code FROM runs")[0] == ("error", "prompt_failed")
    ws.close()


@pytest.mark.parametrize("over,code", [
    ({"text": "   "}, "text_empty"),
    ({"text": "x" * 301}, "text_too_long"),
    ({"templateId": "pick_into_box"}, "bad_template"),
    ({"params": {"object": "red_ball"}}, "bad_object"),
    ({"profileId": "smolvla-fp16"}, "unknown_profile"),
])
def test_command_checks_in_free_text_mode(make_libero, over, code):
    be, bridge = make_libero()
    ws = be.ws()
    ws.send(cmd("c1", **over))
    assert ws.reply("c1")["code"] == code
    assert bridge.posts == []
    ws.close()


def test_board_unreachable_blocks_the_command(make_libero):
    bridge = FakeBridge()
    bridge.reachable = False
    be, _ = make_libero(bridge)
    ws = be.ws()
    ws.send(cmd("c1"))
    assert ws.reply("c1")["code"] == "board_offline"
    ws.close()


def test_bridge_down_is_sim_offline(make_libero):
    be, bridge = make_libero()
    bridge.down = True
    be.wait(lambda: be.core.state.sim_ok is False)
    ws = be.ws()
    ws.send(cmd("c1"))
    assert ws.reply("c1")["code"] == "sim_offline"
    ws.close()


def test_protocol_and_goal_preview_endpoints(make_libero):
    be, _ = make_libero()
    proto = be.http.get("/api/v1/protocol").json()
    assert proto["free_text"] is True and proto["template_id"] == "libero_prompt"
    assert proto["object"] == "libero_goal/8" and PROMPT in proto["suggestions"]
    preview = be.http.post("/api/v1/goal-preview", json={"text": PROMPT}).json()
    assert preview["goal"]["label"] == PROMPT
    assert be.http.post("/api/v1/goal-preview", json={"text": 3}).status_code == 422
    profiles = [p["profile_id"] for p in be.http.get("/api/v1/profiles").json()["profiles"]]
    assert profiles == ["xvla-libero-w8a16"]


# --- the adapter on its own ----------------------------------------------------


async def test_reset_hides_the_previous_episode_result(tmp_path):
    bridge = FakeBridge(end_step=1)
    sim = make_sim(libero_settings(tmp_path), bridge)
    await sim.reset(1000, 1, "libero_goal/8")
    await sim.start(PROMPT, 1000)
    await sim.get_state()  # the episode ends
    assert (await sim.get_evaluation()).outcome == "success"
    await sim.reset(1000, 2, "libero_goal/8")
    ev = await sim.get_evaluation()
    assert ev.final is False and ev.sim_run_id == "libero-2"  # not run 1's success
    await sim.aclose()


async def test_stop_before_the_prompt_holds_at_once_and_blocks_the_prompt(tmp_path):
    bridge = FakeBridge()
    sim = make_sim(libero_settings(tmp_path), bridge)
    await sim.reset(1000, 1, "libero_goal/8")
    await sim.stop()
    state = await sim.get_state()
    assert state.hold and state.hold_reason == "stop" and state.raw["hold_origin"] == "USER_ABORT"
    with pytest.raises(BoardError):
        await sim.start(PROMPT, 1000)
    assert bridge.posts == [] and bridge.stops == []
    await sim.release_hold()
    assert not (await sim.get_state()).hold
    await sim.aclose()


async def test_hold_only_after_the_bridge_reports_stopped(tmp_path):
    bridge = FakeBridge(end_step=10_000, steps_per_poll=0)
    sim = make_sim(libero_settings(tmp_path), bridge)
    await sim.reset(1000, 1, "libero_goal/8")
    await sim.start(PROMPT, 1000)
    assert (await sim.get_state()).status == "RUNNING"
    await sim.stop()
    assert sim._stop_requested and bridge.episode["state"] != "ended"
    state = await sim.get_state()  # the fake ends the episode as "stopped" on this poll
    assert state.hold and (await sim.get_evaluation()).outcome == "aborted"
    await sim.aclose()


async def test_frames_and_scene_parsing(tmp_path):
    bridge = FakeBridge()
    sim = make_sim(libero_settings(tmp_path), bridge)
    assert await sim.get_frame("overhead") == b""  # nothing yet
    await sim.reset(1000, 1, "libero_goal/8")
    await sim.start(PROMPT, 1000)
    assert await sim.get_frame("overhead") == JPEG + b"agentview"
    assert await sim.get_frame("wrist") == JPEG + b"wrist"
    assert parse_scene("libero_spatial/0") == ("libero_spatial", 0)
    for bad in ("red_ball", "libero_goal", "libero_goal/x"):
        with pytest.raises(SimRejected):
            parse_scene(bad)
    await sim.aclose()



# --- Panda joints (arm_state) -----------------------------------------------------


def test_panda_joints_reach_the_web_as_arm_state(make_libero):
    be, _ = make_libero(FakeBridge(panda_joints=7))
    ws = be.ws()
    ws.status(lambda m: True)
    ws.send(cmd("c1"))
    ws.task("done", timeout=6)
    arms = [m for m in ws.seen if m["type"] == "arm_state"]
    assert arms, "no arm_state reached the web"
    last = arms[-1]
    assert last["arm"] == "panda" and len(last["jointsDeg"]) == 7
    assert last["gripper"] in ("open", "closed") and len(last["eefMm"]) == 3
    assert last["eefMm"][0] == -201.6  # metres -> millimetres
    assert len(last["plannedEefMm"]) == 30 and last["plannedEefMm"][0] == [-201.6, last["eefMm"][1], 1164.8]
    assert last["plannedEefMm"][-1][0] == -172.6
    # Still never under SO-101 names, and nothing quarantined.
    assert not [m for m in ws.seen if m["type"] == "telemetry"]
    assert be.db("SELECT COUNT(*) FROM quarantine")[0][0] == 0
    ws.close()


def test_malformed_panda_frame_is_quarantined_not_sent(make_libero):
    be, _ = make_libero(FakeBridge(panda_joints=6))
    ws = be.ws()
    ws.status(lambda m: True)
    ws.send(cmd("c1"))
    ws.task("done", timeout=6)
    assert not [m for m in ws.seen if m["type"] == "arm_state"]
    assert be.db("SELECT COUNT(*) FROM quarantine WHERE error LIKE 'adapter (arm)%'")[0][0] > 0
    ws.close()


async def test_panda_sample_only_from_this_run(tmp_path):
    bridge = FakeBridge(panda_joints=7, end_step=1)
    sim = make_sim(libero_settings(tmp_path), bridge)
    await sim.reset(1000, 1, "libero_goal/8")
    assert (await sim.get_state()).arm is None  # no episode yet
    await sim.start(PROMPT, 1000)
    state = await sim.get_state()  # step 1: the episode ends on this poll
    assert state.arm is not None and state.arm.arm == "panda" and len(state.arm.joints_rad) == 7
    assert state.joint_positions == ()  # the SO-101 joints stay empty
    await sim.reset(1000, 2, "libero_goal/8")
    assert (await sim.get_state()).arm is None  # run 1's frame is not shown for run 2
    await sim.aclose()


def test_to_arm_state_converts_and_refuses_bad_frames():
    msg = adapter.to_arm_state(
        ArmSample(arm="panda", joints_rad=(0.0, 0.5, 0, -1.5708, 0, 1.5708, 0.7854),
                  gripper="closed", eef_m=(-0.2016, 0.0124, 1.1648), step=31,
                  planned_eef_m=((-0.202, -0.0023, 1.1878), (-0.19, 0.01, 1.15))),  # fmt: skip
        123,
    ).wire()
    assert msg["type"] == "arm_state" and msg["ts"] == 123 and msg["step"] == 31
    assert msg["jointsDeg"][3] == -90.0 and msg["jointsDeg"][5] == 90.0
    assert msg["eefMm"] == [-201.6, 12.4, 1164.8] and msg["gripper"] == "closed"
    assert msg["plannedEefMm"] == [[-202.0, -2.3, 1187.8], [-190.0, 10.0, 1150.0]]
    no_extras = adapter.to_arm_state(ArmSample(arm="panda", joints_rad=(0.0,) * 7, gripper="?"), 1).wire()
    assert "gripper" not in no_extras and "eefMm" not in no_extras and "plannedEefMm" not in no_extras
    for bad in (
        ArmSample(arm="panda", joints_rad=(0.0,) * 6),
        ArmSample(arm="panda", joints_rad=(float("nan"),) + (0.0,) * 6),
        ArmSample(arm="ur5", joints_rad=(0.0,) * 7),
        ArmSample(arm="panda", joints_rad=(0.0,) * 7, planned_eef_m=((0.1, 0.2),)),
        ArmSample(arm="panda", joints_rad=(0.0,) * 7, planned_eef_m=((0.1, float("inf"), 0.3),)),
    ):
        with pytest.raises(ValueError):
            adapter.to_arm_state(bad, 1)


# --- the bridge stalls while it resets its scene -------------------------------


class StallingBridge(FakeBridge):
    """Every request hangs for one window mid-run, like the real bridge while a scene reset
    holds Python's lock: requests made during the window answer only when it ends."""

    def __init__(self, stall_s: float, at_step: int, **kw: Any) -> None:
        super().__init__(**kw)
        self.stall_s, self.at_step, self.stalled = stall_s, at_step, False
        self._until: float | None = None

    async def ahandle(self, request: httpx.Request) -> httpx.Response:
        import asyncio
        import time

        ep = self.episode
        if self._until is None and ep and ep["step"] >= self.at_step:
            self._until, self.stalled = time.monotonic() + self.stall_s, True
        if self._until is not None and time.monotonic() < self._until:
            await asyncio.sleep(self._until - time.monotonic())
        return self.handle(request)


def _env_ms(name: str) -> int:
    for line in (BACKEND_DIR / "libero.env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"SO101_{name}="):
            return int(line.split("=", 1)[1])
    raise AssertionError(f"{name} missing from libero.env.example")


@pytest.fixture
def make_stalling(tmp_path: Path):
    servers: list[tuple[_Server, httpx.Client]] = []

    def make(bridge: StallingBridge, **over: Any) -> BE:
        settings = libero_settings(tmp_path, **over)
        client = httpx.AsyncClient(transport=httpx.MockTransport(bridge.ahandle), base_url="http://bridge")
        sim = LiberoSim(settings, client=client)
        app = create_app(settings, sim=sim, board=LiberoBoard(sim))
        server = _Server(app)
        server.start()
        url = f"http://127.0.0.1:{server.port}"
        http = httpx.Client(base_url=url, timeout=10)
        servers.append((server, http))
        be = BE(url, f"ws://127.0.0.1:{server.port}/ws", http, sim, None, app, settings)  # type: ignore[arg-type]
        be.wait(lambda: be.core.state.sim_ok is True)
        return be

    yield make
    for server, http in servers:
        http.close()
        server.stop()


def test_libero_env_rides_out_a_bridge_stall(make_stalling):
    """With libero.env.example's timings a 1.5 s stall mid-run does not end the run."""
    bridge = StallingBridge(stall_s=1.5, at_step=5, end_step=40)
    be = make_stalling(
        bridge,
        sim_timeout_ms=_env_ms("SIM_TIMEOUT_MS"),
        telemetry_stale_ms=_env_ms("TELEMETRY_STALE_MS"),
        run_wall_timeout_s=20.0,
    )
    ws = be.ws()
    ws.send(cmd("c1"))
    ws.task("running")
    done = ws.until(lambda m: m["type"] == "task" and m["task"]["state"] in ("done", "failed"), timeout=15)
    assert bridge.stalled and done["task"]["outcome"] == "success"
    ws.close()


def test_so101_timings_would_end_the_run_on_the_same_stall(make_stalling):
    """The control: with the SO-101 test timings (600 ms) the same stall ends the run."""
    bridge = StallingBridge(stall_s=1.5, at_step=5, end_step=40)
    be = make_stalling(bridge)
    ws = be.ws()
    ws.send(cmd("c1"))
    ws.task("running")
    ws.until(lambda m: m["type"] == "task" and m["task"]["state"] in ("done", "failed", "stopped"), timeout=15)
    outcome, code = be.db("SELECT outcome, reason_code FROM runs")[0]
    assert bridge.stalled and outcome != "success" and code in ("telemetry_stale", "sim_offline")
    ws.close()
