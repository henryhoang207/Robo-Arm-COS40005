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

from app.libero_link import LiberoBoard, LiberoSim, parse_scene
from app.main import create_app
from app.ports import BoardError, SimRejected
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

    def __init__(self, result: str = "success", end_step: int = 12, steps_per_poll: int = 1) -> None:
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

