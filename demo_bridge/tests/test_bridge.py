"""Bridge tests with a fake board (real TCP framing) and a fake scene; no MuJoCo or board needed.

Run from the repo root:  ~/libero/bin/python -m pytest demo_bridge/tests -q
"""
from __future__ import annotations

import json
import socket
import struct
import threading
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from demo_bridge.app import BridgeConfig, create_app
from demo_bridge.board import FRAME, BoardClient, BoardError
from demo_bridge.sim import Observation, SceneCache

STATUS = {
    "ok": True, "mode": "full-onboard-stage1+stage2", "chunks_served": 3, "started_at": "2026-11-26 03:03:56",
    "providers": {k: ["QNNExecutionProvider", "CPUExecutionProvider"] for k in ("vision", "bart", "core")},
    "nsp_temps_c": {"nsp-0-0-0-thermal": 36.8},
}
TIMINGS = {"pre_ms": 10.0, "vision_2v_ms": 84.0, "bart_ms": 6.5, "proj_ms": 12.0, "core10_ms": 225.0, "total_ms": 337.5}


def _recv(conn, n):
    b = b""
    while len(b) < n:
        c = conn.recv(n - len(b))
        if not c:
            raise EOFError
        b += c
    return b


class FakeBoardServer:
    """Speaks the board's TCP protocol. mode: 'ok' | 'error' | 'silent'."""

    def __init__(self, mode="ok"):
        self.mode = mode
        self.requests: list[tuple[dict, int]] = []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._client, args=(conn,), daemon=True).start()

    def _client(self, conn):
        try:
            while True:
                hl, pl = FRAME.unpack(_recv(conn, 8))
                hdr = json.loads(_recv(conn, hl))
                _recv(conn, pl)
                self.requests.append((hdr, pl))
                if self.mode == "silent":
                    time.sleep(5)
                    return
                if self.mode == "error":
                    out, body = {"ok": False, "error": "QNN graph execute failed"}, b""
                else:
                    a = np.zeros((30, 7), np.float32)
                    a[:, :3] = np.linspace(0, 0.1, 30)[:, None]
                    a[:, 6] = -1.0
                    out, body = {"ok": True, "shape": [30, 7], "timings": TIMINGS}, a.tobytes()
                hb = json.dumps(out).encode()
                conn.sendall(struct.pack("<II", len(hb), len(body)) + hb + body)
        except (EOFError, OSError):
            pass
        finally:
            conn.close()

    def close(self):
        self.sock.close()


class FakeBoard(BoardClient):
    def __init__(self, server: FakeBoardServer, reachable=True, timeout_s=2.0):
        super().__init__("127.0.0.1", server.port, 1, timeout_s)
        self.reachable = reachable

    def status(self, timeout_s: float = 2.0):
        return dict(STATUS) if self.reachable else None


class FakeScene:
    def __init__(self, suite, task_id, max_steps, succeed_at=45, step_delay=0.0, reset_delay=0.3, goal_at=None):
        self.succeed_at = succeed_at  # step at which the scene's own goal is met
        self.goal_at = goal_at  # step from which check() reports any custom goal as met
        self.checked: list = []
        self.step_delay = step_delay
        self.reset_delay = reset_delay  # gives the test's WebSocket time to connect before frames flow
        self.t = 0

    def _obs(self):
        img = np.full((16, 16, 3), self.t % 255, np.uint8)
        img[0, 0] = 255  # marks the raw top-left corner
        return Observation(img, img.copy(), np.array([0.1, 0.0, 1.0], np.float32), np.eye(3, dtype=np.float32),
                           np.zeros(7, np.float32))

    resets = 0

    def reset(self, seed):
        time.sleep(self.reset_delay)
        self.resets += 1
        self.t = 0
        return self._obs()

    def step(self, action):
        if self.step_delay:
            time.sleep(self.step_delay)
        self.t += 1
        success = self.succeed_at is not None and self.t >= self.succeed_at
        return self._obs(), float(success), success, False

    def has_states(self, names):
        return all(not n.startswith("missing") for n in names)

    def check(self, conditions):
        self.checked.append(conditions)
        return self.goal_at is not None and self.t >= self.goal_at

    def close(self):
        pass


SCENES = [
    {"suite": "libero_spatial", "suite_label": "Spatial", "task_id": 0, "max_steps": 100, "recommended": True,
     "instruction": "pick up the black bowl between the plate and the ramekin and place it on the plate"},
    {"suite": "libero_goal", "suite_label": "Goal", "task_id": 7, "max_steps": 100, "recommended": False,
     "instruction": "turn on the stove"},
]


def make_client(tmp_path, server, reachable=True, **scene_kw):
    cache = SceneCache(100, factory=lambda s, t, m: FakeScene(s, t, m, **scene_kw))
    cfg = BridgeConfig(max_steps=100, video_dir=tmp_path, realtime=False, preload=())
    app = create_app(FakeBoard(server, reachable), SCENES, cache, cfg)
    return TestClient(app), app


def collect(client, episode_id, limit=500):
    msgs = []
    with client.websocket_connect(f"/ws/episodes/{episode_id}") as ws:
        while len(msgs) < limit:
            msgs.append(ws.receive_json())
            if msgs[-1]["type"] == "ended":
                break
    return msgs


@pytest.fixture
def server():
    s = FakeBoardServer()
    yield s
    s.close()


# ---------------- board protocol ----------------

def test_infer_round_trip_and_header(server):
    board = FakeBoard(server)
    img = np.zeros((16, 16, 3), np.uint8)
    with board.connect() as session:
        actions, timings, rtt = session.infer(img, img, "turn on the stove", np.zeros(3), np.eye(3),
                                              np.zeros((1, 30, 20), np.float32))
    assert actions.shape == (30, 7) and timings == TIMINGS and rtt >= 0
    hdr, plen = server.requests[-1]
    assert hdr["cmd"] == "infer_e2e" and hdr["domain_id"] == 3 and hdr["steps"] == 10 and hdr["flip_view0"] is True
    assert hdr["view0_shape"] == [16, 16, 3] and hdr["has_noise"] is True
    assert plen == 2 * 16 * 16 * 3 + 12 + 36 + 600 * 4


@pytest.mark.parametrize("mode,code", [("error", "board_error"), ("silent", "board_timeout")])
def test_board_failures_map_to_codes(mode, code):
    s = FakeBoardServer(mode)
    try:
        img = np.zeros((16, 16, 3), np.uint8)
        with pytest.raises(BoardError) as e, FakeBoard(s, timeout_s=0.5).connect() as session:
            session.infer(img, img, "x", np.zeros(3), np.eye(3))
        assert e.value.code == code
    finally:
        s.close()


def test_unreachable_board():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()  # nothing listens on this port now
    with pytest.raises(BoardError) as e:
        BoardClient("127.0.0.1", port, timeout_s=0.5).connect()
    assert e.value.code == "board_unreachable"


# ---------------- HTTP + WebSocket API ----------------

def test_health_and_scenes(tmp_path, server):
    client, _ = make_client(tmp_path, server)
    with client:
        h = client.get("/api/health").json()
        assert h["bridge"] == "ok" and h["episode_running"] is False
        assert h["board"]["reachable"] and h["board"]["all_on_npu"] and h["board"]["host"] == "127.0.0.1"
        assert client.get("/api/scenes").json() == SCENES


def test_successful_episode_streams_spec_messages(tmp_path, server):
    client, _ = make_client(tmp_path, server, succeed_at=45)
    with client:
        r = client.post("/api/episodes", json={"suite": "libero_spatial", "task_id": 0, "instruction": None})
        assert r.status_code == 201
        body = r.json()
        assert body["custom_instruction"] is False and body["ws_url"].endswith(body["episode_id"])
        msgs = collect(client, body["episode_id"])
        types = [m["type"] for m in msgs]
        assert types[0] == "started" and types[-1] == "ended"
        started, ended = msgs[0], msgs[-1]
        assert started["cameras"] == ["agentview", "wrist"] and started["image_size"] == [16, 16]
        assert ended["result"] == "success" and ended["steps"] == 45 and ended["chunks"] == 2
        chunk = next(m for m in msgs if m["type"] == "chunk")
        assert chunk["board"] == TIMINGS and len(chunk["planned_eef_pos_m"]) == 30
        frames = [m for m in msgs if m["type"] == "frame"]
        assert frames[0]["step"] == 0 and frames[-1]["step"] == 45
        assert set(frames[-1]) >= {"agentview", "wrist", "eef_pos_m", "gripper", "joint_pos_rad", "t_sim_s"}
        assert frames[-1]["gripper"] == "open"
        summary = client.get(f"/api/episodes/{body['episode_id']}").json()
        assert summary["state"] == "ended" and summary["result"] == "success"
        video = client.get(ended["video_url"])
        assert video.status_code == 200 and video.headers["content-type"] == "video/mp4" and len(video.content) > 0
        # a client that connects after the end gets the replay and the end
        late = collect(client, body["episode_id"])
        assert late[-1]["type"] == "ended" and late[0]["type"] == "started"


def test_frames_are_flipped_upright(tmp_path, server):
    import base64

    import cv2

    client, _ = make_client(tmp_path, server, succeed_at=1)
    with client:
        ep = client.post("/api/episodes", json={"suite": "libero_spatial", "task_id": 0}).json()["episode_id"]
        frame = next(m for m in collect(client, ep) if m["type"] == "frame")
        img = cv2.imdecode(np.frombuffer(base64.b64decode(frame["agentview"]), np.uint8), cv2.IMREAD_COLOR)
        assert img.shape == (16, 16, 3)
        assert img[-1, -1].mean() > 200 and img[0, 0].mean() < 100  # raw top-left is now bottom-right


def test_one_episode_at_a_time_and_stop(tmp_path, server):
    client, _ = make_client(tmp_path, server, succeed_at=None, step_delay=0.01)
    with client:
        ep = client.post("/api/episodes", json={"suite": "libero_goal", "task_id": 7}).json()["episode_id"]
        second = client.post("/api/episodes", json={"suite": "libero_spatial", "task_id": 0})
        assert second.status_code == 409 and second.json()["error"]["code"] == "episode_running"
        assert client.get("/api/health").json()["episode_running"] is True
        time.sleep(0.2)
        assert client.post(f"/api/episodes/{ep}/stop").status_code == 202
        msgs = collect(client, ep)
        assert msgs[-1]["result"] == "stopped"
        again = client.post(f"/api/episodes/{ep}/stop")
        assert again.status_code == 409 and again.json()["error"]["code"] == "not_running"


def test_custom_instruction_is_sent_to_board_and_unparsed_prompt_is_unscored(tmp_path, server):
    client, _ = make_client(tmp_path, server, succeed_at=1)
    with client:
        r = client.post("/api/episodes", json={"suite": "libero_goal", "task_id": 7, "instruction": "  turn on the oven "})
        assert r.json()["custom_instruction"] is True and r.json()["instruction"] == "turn on the oven"
        assert r.json()["goal"]["scored"] is False and r.json()["goal"]["reason"]
        msgs = collect(client, r.json()["episode_id"])
        assert server.requests[-1][0]["task_text"] == "turn on the oven"
        # the scene's own goal (met at step 1) must not end or score it
        assert msgs[-1]["result"] == "unscored" and msgs[-1]["steps"] == 100


def test_goal_scene_scores_the_prompt_not_the_scene_goal(tmp_path, server):
    client, app = make_client(tmp_path, server, succeed_at=5, goal_at=20)
    with client:
        r = client.post("/api/episodes", json={"suite": "libero_goal", "task_id": 7,
                                               "instruction": "put the bowl on the stove"}).json()
        assert r["goal"] == {"scored": True, "source": "LIBERO Goal task 1", "label": "put the bowl on the stove",
                             "conditions": [["on", "akita_black_bowl_1", "flat_stove_1_cook_region"]], "reason": None}
        msgs = collect(client, r["episode_id"])
        assert msgs[0]["goal"]["conditions"] == r["goal"]["conditions"]
        assert msgs[-1]["result"] == "success" and msgs[-1]["steps"] == 20  # not 5: the scene's goal is ignored
        scene = app.state.bridge.cache.get("libero_goal", 7)
        assert scene.checked[-1] == [["on", "akita_black_bowl_1", "flat_stove_1_cook_region"]]


def test_goal_prompt_that_is_never_met_fails_at_the_cap(tmp_path, server):
    client, _ = make_client(tmp_path, server, succeed_at=None, goal_at=None)
    with client:
        r = client.post("/api/episodes", json={"suite": "libero_goal", "task_id": 7,
                                               "instruction": "put the cream cheese on the plate"}).json()
        assert r["goal"]["source"] == "parsed prompt"
        assert collect(client, r["episode_id"])[-1]["result"] == "failure"


def test_custom_prompt_outside_goal_suite_is_unscored(tmp_path, server):
    client, _ = make_client(tmp_path, server, succeed_at=10)
    with client:
        r = client.post("/api/episodes", json={"suite": "libero_spatial", "task_id": 0,
                                               "instruction": "pick up the ramekin and place it on the plate"}).json()
        assert r["goal"]["scored"] is False
        ended = collect(client, r["episode_id"])[-1]
        assert ended["result"] == "unscored" and ended["steps"] == 100


def test_parse_endpoint(tmp_path, server):
    client, _ = make_client(tmp_path, server)
    with client:
        r = client.post("/api/goals/parse", json={"suite": "libero_goal", "task_id": 7, "instruction": "turn off the stove"})
        assert r.status_code == 200 and r.json()["goal"]["conditions"] == [["turnoff", "flat_stove_1"]]
        own = client.post("/api/goals/parse", json={"suite": "libero_goal", "task_id": 7, "instruction": None}).json()
        assert own["custom_instruction"] is False and own["goal"]["source"] == "scene's own LIBERO goal"
        assert client.post("/api/goals/parse", json={"suite": "x", "task_id": 0}).status_code == 422


@pytest.mark.parametrize("body,status,code", [
    ({"suite": "libero_spatial", "task_id": 99}, 422, "bad_scene"),
    ({"suite": "nope", "task_id": 0}, 422, "bad_scene"),
    ({"suite": "libero_spatial", "task_id": "0"}, 422, "bad_scene"),
    ({"suite": "libero_spatial", "task_id": 0, "seed": -1}, 422, "bad_request"),
    ({"suite": "libero_spatial", "task_id": 0, "instruction": "x" * 301}, 422, "bad_request"),
])
def test_bad_requests(tmp_path, server, body, status, code):
    client, _ = make_client(tmp_path, server)
    with client:
        r = client.post("/api/episodes", json=body)
        assert r.status_code == status and r.json()["error"]["code"] == code


def test_board_unreachable_blocks_start(tmp_path, server):
    client, _ = make_client(tmp_path, server, reachable=False)
    with client:
        r = client.post("/api/episodes", json={"suite": "libero_spatial", "task_id": 0})
        assert r.status_code == 503 and r.json()["error"]["code"] == "board_unreachable"
        assert client.get("/api/health").json()["board"] == {"reachable": False, "host": "127.0.0.1"}


def test_board_error_ends_episode_with_error(tmp_path):
    s = FakeBoardServer("error")
    try:
        client, _ = make_client(tmp_path, s)
        with client:
            ep = client.post("/api/episodes", json={"suite": "libero_spatial", "task_id": 0}).json()["episode_id"]
            msgs = collect(client, ep)
            err = next(m for m in msgs if m["type"] == "error")
            assert err["code"] == "board_error" and "QNN" in err["message"]
            assert msgs[-1]["type"] == "ended" and msgs[-1]["result"] == "error"
            assert client.get("/api/health").json()["episode_running"] is False
    finally:
        s.close()


def test_prepared_reset_is_used_once_and_only_for_its_seed():
    cache = SceneCache(100, factory=lambda s, t, m: FakeScene(s, t, m, reset_delay=0))
    scene = cache.get("libero_spatial", 0)
    cache.prepare("libero_spatial", 0, 1000)
    assert scene.resets == 1 and cache.is_prepared("libero_spatial", 0, 1000)
    cache.reset("libero_spatial", 0, 1000)
    assert scene.resets == 1 and not cache.is_prepared("libero_spatial", 0, 1000)  # taken, no new reset
    cache.reset("libero_spatial", 0, 1000)
    assert scene.resets == 2  # nothing prepared: fresh reset
    cache.prepare("libero_spatial", 0, 1000)
    cache.reset("libero_spatial", 0, 7)
    assert scene.resets == 4  # other seed: prepared one discarded, fresh reset


def test_preload_prepares_scenes_and_reprepares_after_episode(tmp_path, server):
    cache = SceneCache(100, factory=lambda s, t, m: FakeScene(s, t, m, succeed_at=1, reset_delay=0))
    cfg = BridgeConfig(max_steps=100, video_dir=tmp_path, realtime=False, preload=(("libero_spatial", 0),))
    with TestClient(create_app(FakeBoard(server), SCENES, cache, cfg)) as client:
        deadline = time.time() + 5
        while client.get("/api/health").json()["scenes_ready"] != ["libero_spatial/0"] and time.time() < deadline:
            time.sleep(0.05)
        assert cache.is_prepared("libero_spatial", 0, 1000)
        scene = cache.get("libero_spatial", 0)
        ep = client.post("/api/episodes", json={"suite": "libero_spatial", "task_id": 0}).json()["episode_id"]
        collect(client, ep)
        deadline = time.time() + 5
        while not cache.is_prepared("libero_spatial", 0, 1000) and time.time() < deadline:
            time.sleep(0.05)
        assert scene.resets == 2  # one at preload (used by the episode), one re-prepare after it


def test_unknown_episode(tmp_path, server):
    client, _ = make_client(tmp_path, server)
    with client:
        assert client.get("/api/episodes/ep_missing").status_code == 404
        assert client.post("/api/episodes/ep_missing/stop").status_code == 404
        assert client.get("/api/episodes/ep_missing/video").status_code == 404
