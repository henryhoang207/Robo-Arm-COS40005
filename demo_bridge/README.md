# Demo bridge — web integration guide

The bridge is the only backend the web app talks to. It runs the LIBERO simulation on the demo laptop, sends camera images to X-VLA on the VENTUNO Q board's NPU, plays back the actions the board returns, and streams camera frames and stats to the browser.

```
Browser ──WS──▶ Web backend (robo-arm-app-main, :8001) ──HTTP──▶ Bridge (WSL, :8002) ──TCP 8766──▶ VENTUNO Q board
                SO101_SIM_LINK=libero, SO101_BOARD_LINK=libero     runs the LIBERO sim         (X-VLA on the NPU)
```

**The web app reaches the bridge through its own backend.** Run that backend in LIBERO mode: `robo-arm-app-main/backend/libero.env.example` and the "X-VLA LIBERO" section of `robo-arm-app-main/backend/README.md`. Its adapter, `backend/app/libero_link.py`, polls `GET /api/state` and `GET /api/camera/{agentview|wrist}` (§4). The page then shows a prompt box, both cameras and the run's result. Verified live on 26 Nov 2026: "put the bowl on the stove" succeeded in 92 steps, and STOP and Ready worked through the web page.

The rest of this README is the bridge's own API. Use it for direct clients, or to change the adapter.

**The demo is one scene, LIBERO Goal task 8, where the user types their own prompt.** The bridge works out what success means for that prompt, then checks it in the simulator every step.

Status, 26 Nov 2026: 61 tests passing. In that scene on the board, all 10 LIBERO Goal instructions succeeded and all 3 new object/place combinations failed (§2 and [`recordings/2026-11-26/`](recordings/2026-11-26/README.md)).

The original design doc is "X-VLA Board Demo — Web Integration Spec" (https://claude.ai/artifact/4KCDYz7i5oRPXHjzyqB6k6). Where it differs from this README, this README is current: free prompts, goals and the 400-step cap came later.

## 1. Run it

Do these in order on the demo laptop.

1. **Board.** In Arduino App Lab, start **X-VLA LIBERO NPU** (`user:xvla-libero-npu`). Check that `http://10.1.0.119:8080/api/status` answers. The board's IP has changed before, so check it on the day.
2. **Bridge.** In WSL, from the folder that contains `demo_bridge/` (the repo root), run the command below. It needs the `~/libero` venv: LeRobot 0.6.1 with LIBERO, FastAPI 0.165.0 and Uvicorn 0.54.0.

   ```bash
   MUJOCO_GL=egl GALLIUM_DRIVER=d3d12 ~/libero/bin/python -m demo_bridge.app --board-host 10.1.0.119
   ```

   Wait about a minute, until the log shows `scene libero_goal/8 ready`. At startup the bridge builds Spatial task 0 as a backup, then the Goal demo scene, leaving the Goal scene reset and ready to start at once.
3. **Web app.** Start the web backend in LIBERO mode (see above) and open `http://localhost:8001`. A direct client can also use the bridge at `http://localhost:8002`; WSL forwards both ports to Windows.

| Flag | Default | Use |
| --- | --- | --- |
| `--board-host` | `10.1.0.119` | The board's current IP |
| `--host` | `127.0.0.1` | Set `0.0.0.0` only if the web app runs on another machine on the network |
| `--port` | `8002` | Bridge port (8000 is left free for the SO-101 MuJoCo server) |
| `--cors` | `*` | Comma-separated allowed origins, e.g. `http://localhost:5173` |
| `--max-steps` | `400` | Step cap per episode. LIBERO's Goal demonstrations take at most 270 steps |
| `--no-preload` | off | Skip preparing scenes at startup |
| `--no-realtime` | off | Play actions as fast as the sim runs instead of at 20 Hz |

Episode videos are saved to `~/outputs/bridge/` in WSL.

## 2. The free-prompt demo

### Why this scene

LIBERO has four suites. Only in the Goal suite do all 10 tasks share one table, so the instruction alone decides what the robot should do. That's why X-VLA follows the wording there.

In the Spatial suite, each table layout comes with exactly one instruction, so the model ignores the wording. A test on 26 Nov confirmed it: asked to move the ramekin, it moved the bowl to the plate anyway.

The demo scene is Goal task 8, which contains:
- **Objects to move:** a bowl, a plate, a cream cheese and a wine bottle.
- **Places:** a stove, a cabinet with 3 drawers, and a wine rack.

### How a prompt is scored

The bridge turns every prompt into a **goal**: the conditions it checks in the simulator after each step, using LIBERO's own predicate functions. The episode ends with `success` the moment they hold. Prompts fall into three groups:

| Prompt | `goal.source` | How it's checked |
| --- | --- | --- |
| The scene's own instruction, "put the bowl on the plate" | `scene's own LIBERO goal` | LIBERO's built-in success check |
| One of the other 9 Goal instructions, e.g. "turn on the stove" | `LIBERO Goal task N` | That task's exact goal from LIBERO's task file |
| A new request the parser understands, e.g. "put the cream cheese on the plate" | `parsed prompt` | Conditions built from the sentence |
| Anything else, e.g. "wave hello" | `null`, `scored: false` | Not checked: runs to the step cap as `unscored`, or until Stop |

The parser understands these forms (wording is case- and punctuation-insensitive; "the", "please" etc. are ignored):

| Form | Example | Condition |
| --- | --- | --- |
| put / place / move / push … `<object>` on / onto / in / to `<place>` | put the wine bottle on the plate | `On(wine bottle, plate)` |
| … in / into the top / middle / bottom drawer | put the bowl in the middle drawer | `In(bowl, middle drawer)` |
| open / close the top / middle / bottom drawer | close the top drawer | `Close(top drawer)` |
| turn on / off the stove | turn off the stove | `TurnOff(stove)` |
| pick up `<object>` and put it … | pick up the bowl and place it on the stove | `On(bowl, stove)` |
| open the `<drawer>` and put `<object>` inside | open the bottom drawer and put the cream cheese inside | `In(cream cheese, bottom drawer)` |
| two requests joined by "and" | turn on the stove and put the bowl on the plate | both must hold |

The words it recognises:
- **Objects:** bowl (or black bowl), plate, cream cheese, wine bottle.
- **Places:** stove, plate, bowl, top of the cabinet, wine rack, front of the stove, top / middle / bottom drawer.

Use `POST /api/goals/parse` (§4) as the user types, to show "Will check: the bowl on the stove" or "Not scored" before they press Start.

### What to expect (recorded 26 Nov, one try each)

| Prompt type | Result |
| --- | --- |
| The 10 LIBERO Goal instructions | **10/10 success**, 76–192 steps, 14–62 s per episode |
| New object/place combinations | **0/3.** Cream cheese to the plate, and to the stove: the arm carried it to the target but never let go. Wine bottle to the plate: it put the bottle on the rack (its trained habit) |
| Unscored ("wave hello") | Moved around until stopped |

Full table, videos and frame strips: [`recordings/2026-11-26/`](recordings/2026-11-26/README.md).

So, for the prompt box:
- **Lead with the suggestions** from `scene.prompt_suggestions`: the 10 Goal instructions and 4 new examples. Expect the first 10 to work and the new ones to usually fail.
- **Accept free text,** but show what will be checked (or "Not scored") before Start.
- **For a reliable live demo,** use the 10 Goal instructions; present new combinations as "let's see if it generalises".

### Other things to design for

- **One episode at a time.** The board serves one connection at a time. Disable Start while `health.episode_running` is true; a second start gets 409 `episode_running`.
- **The arm moves in bursts.** It plays 30 steps, then holds still for 0.5–1 s while the board computes the next 30. Label the pause "Board computing…"; it isn't a stall.
- **Start time** (from `POST /api/episodes` to `started`):
  - 0.5 s when the demo scene is prepared and idle.
  - 7.5–20 s when started straight after the previous episode, because the bridge is still resetting the scene.
  - About 30–60 s the first time another scene is used.

  Show "Loading scene…" until `started` arrives.
- **Failed episodes take about 1.5–2 minutes.** The sim runs at about 4–6 steps/s, so the 400-step cap takes 89–115 s. Make Stop easy to reach.
- **Episodes end the moment the goal holds,** as in LIBERO, sometimes with the object still in the gripper.
- **The board app can stop on its own.** On 26 Nov it stopped three times, 11–40 min after being started, with no error in its log; the cause is unknown. `health.board.reachable` turns `false` within 5 s. Show a "Board offline" banner and disable Start; the operator restarts the app in App Lab.

## 3. Call order

1. On load: `GET /api/scenes`. The demo scene is the first item (`recommended`, `free_prompts: true`). Poll `GET /api/health` every 5 s.
2. While the user types: `POST /api/goals/parse` to preview the goal (debounce about 300 ms).
3. On Start: `POST /api/episodes`, then open the WebSocket at the returned `ws_url`.
4. Draw `frame` messages (cameras, arm state) and `chunk` messages (board timings). Show `started.goal.label` as "Checking: …".
5. The stream ends with one `ended` message (after an `error` message if something failed). Keep the last frame and offer the video.

## 4. HTTP API

Base URL `http://localhost:8002`. Every response is JSON except the video. Every error has this shape:

```json
{"error": {"code": "episode_running", "message": "an episode is already running"}}
```

| Method and path | Returns | Errors |
| --- | --- | --- |
| `GET /api/health` | Bridge and board status | none |
| `GET /api/scenes` | The 40 scenes, the demo scene first | none |
| `POST /api/goals/parse` | The goal a prompt would be scored against; starts nothing and needs no board | 422 `bad_request` / `bad_scene` |
| `POST /api/episodes` | 201 with `episode_id`, `ws_url`, `goal` | 422 `bad_request` / `bad_scene`, 409 `episode_running`, 503 `board_unreachable` |
| `GET /api/episodes/{id}` | Episode summary (live or final) | 404 `not_found` |
| `POST /api/episodes/{id}/stop` | 202; the stream then ends with `stopped`, normally within about 1 s | 404 `not_found`, 409 `not_running` |
| `GET /api/episodes/{id}/video` | `video/mp4`: both cameras side by side, 20 fps | 404 `not_found` |
| `GET /api/state` | One poll for clients without the WebSocket (the web backend's adapter): `bridge`, `episode_running`, `board`, `scenes_ready`, and `episode`. `episode` is the current or latest episode summary plus `eef_pos_m`, `gripper`, `joint_pos_rad` from its latest frame and `planned_eef_pos_m` from its latest chunk; `null` before the first | none |
| `GET /api/camera/{agentview\|wrist}` | `image/jpeg`. During an episode: its latest frame. While idle: the demo scene's starting view once it is prepared, otherwise the last frame of the latest episode | 404 `not_found` before any frame |

`GET /api/health`:

```json
{
  "bridge": "ok",
  "episode_running": false,
  "board": {
    "reachable": true, "host": "10.1.0.119", "mode": "full-onboard-stage1+stage2", "all_on_npu": true,
    "chunks_served": 0, "started_at": "2026-11-26 04:17:45",
    "nsp_temps_c": {"nsp-0-0-0-thermal": 36.0, "nsp-0-1-0-thermal": 35.7, "nsp-0-2-0-thermal": 36.4,
                    "pmm8620au-0-therm": 35.7, "pmm8650au_1_sdram": 39.8, "cpu-1-1-1-thermal": 36.0}
  },
  "scenes_ready": ["libero_spatial/0", "libero_goal/8"]
}
```

- When the board is down, `board` is only `{"reachable": false, "host": "10.1.0.119"}`.
- `scenes_ready` lists scenes already built, which skip the first-load wait.
- For the NPU temperature, show the highest `nsp-*` value.
- `started_at` is the board's clock (UTC).

`GET /api/scenes` returns a list; the first item:

```json
{"suite": "libero_goal", "suite_label": "Goal", "task_id": 8, "instruction": "put the bowl on the plate",
 "max_steps": 400, "recommended": true, "free_prompts": true,
 "prompt_suggestions": ["open the middle drawer of the cabinet", "put the bowl on the stove",
   "put the wine bottle on top of the cabinet", "open the top drawer and put the bowl inside",
   "put the bowl on top of the cabinet", "push the plate to the front of the stove",
   "put the cream cheese in the bowl", "turn on the stove", "put the bowl on the plate",
   "put the wine bottle on the rack", "put the cream cheese on the plate", "put the wine bottle on the plate",
   "put the cream cheese on the stove", "close the middle drawer"]}
```

The other 39 scenes (suites `libero_spatial`, `libero_object`, `libero_goal`, `libero_10`) are still available. In a non-Goal scene, a custom prompt is not scored, and the scene ignores it anyway.

`POST /api/goals/parse` and `POST /api/episodes` take the same body:

```json
{"suite": "libero_goal", "task_id": 8, "instruction": "put the bowl on the stove", "seed": 1000}
```

- `instruction`: `null` or empty means the scene's own instruction. It's trimmed, and at most 300 characters.
- `seed`: optional, default `1000`; parse ignores it. Leave it out for the demo, because only the default seed is prepared in advance.

`POST /api/goals/parse` response:

```json
{"instruction": "put the bowl on the stove", "custom_instruction": true,
 "goal": {"scored": true, "source": "LIBERO Goal task 1", "label": "put the bowl on the stove",
          "conditions": [["on", "akita_black_bowl_1", "flat_stove_1_cook_region"]], "reason": null}}
```

An unscored prompt returns `"goal": {"scored": false, "source": null, "label": null, "conditions": null, "reason": "not understood; try 'put the <object> on the <place>', 'open the top drawer' or 'turn on the stove'"}`. Show `reason` to the user.

`POST /api/episodes` response (201):

```json
{"episode_id": "ep_20261126_123823", "ws_url": "ws://localhost:8002/ws/episodes/ep_20261126_123823",
 "instruction": "put the bowl on the stove", "custom_instruction": true,
 "goal": {"scored": true, "source": "LIBERO Goal task 1", "label": "put the bowl on the stove",
          "conditions": [["on", "akita_black_bowl_1", "flat_stove_1_cook_region"]], "reason": null}}
```

`GET /api/episodes/{id}`:

```json
{"episode_id": "ep_20261126_123823", "state": "ended", "suite": "libero_goal", "task_id": 8,
 "instruction": "put the bowl on the stove", "custom_instruction": true, "seed": 1000, "max_steps": 400,
 "goal": {"scored": true, "source": "LIBERO Goal task 1", "label": "put the bowl on the stove",
          "conditions": [["on", "akita_black_bowl_1", "flat_stove_1_cook_region"]], "reason": null},
 "step": 87, "chunks": 3, "result": "success", "wall_s": 23.14,
 "video_url": "/api/episodes/ep_20261126_123823/video"}
```

`state` is `starting`, `running` or `ended`. `result`, `wall_s` and `video_url` are `null` until they're known. `error` is `{"code", "message"}` when `result` is `error`, else `null`.

A start reuses the board status from the last 5 s poll when it was reachable, so `POST /api/episodes` answers well inside the web backend's 2 s budget.

`GET /api/state` answers from the cached board status and never waits on the board; at most one board check runs at a time. The bridge's HTTP server pauses for 1–3 s while a scene resets after each episode, because the reset holds Python's lock. Clients must tolerate that pause: the web backend's `libero.env.example` does (offline after 8 s, stale after 6 s). The video library is imported at startup, because a cold import inside the first episode stalled the server for 1.6 s.

## 5. WebSocket stream

`ws://localhost:8002/ws/episodes/{id}`. The server sends JSON text messages; the client sends nothing. The server closes the socket after `ended`. For an unknown id it closes with code `4404`.

Connect straight after `POST /api/episodes`. If you reconnect mid-episode, or connect after it ended, the bridge first replays the latest `started`, `chunk`, `frame`, `error` and `ended` messages, so the page can redraw.

| `type` | When |
| --- | --- |
| `started` | Once, when the scene is ready |
| `frame` | Once at step 0, then once per sim step, at up to 20 per second. About 40 KB each, so up to about 1 MB/s while the arm moves |
| `chunk` | Each time the board returns 30 actions, every 30 steps |
| `error` | At most once, just before `ended` |
| `ended` | Once, last |

Examples (images cut short; `goal` shortened after its first appearance):

```json
{"type": "started", "episode_id": "ep_20261126_123823", "suite": "libero_goal", "task_id": 8,
 "instruction": "put the bowl on the stove", "custom_instruction": true, "max_steps": 400, "fps": 20,
 "cameras": ["agentview", "wrist"], "image_size": [360, 360],
 "goal": {"scored": true, "source": "LIBERO Goal task 1", "label": "put the bowl on the stove",
          "conditions": [["on", "akita_black_bowl_1", "flat_stove_1_cook_region"]], "reason": null}}

{"type": "frame", "step": 31, "t_sim_s": 1.55, "agentview": "/9j/4AAQ...", "wrist": "/9j/4AAQ...",
 "eef_pos_m": [-0.2016, 0.0124, 1.1648], "gripper": "open",
 "joint_pos_rad": [0.0112, 0.2031, -0.0154, -2.4127, 0.0041, 2.6203, 0.7913], "reward": 0.0}

{"type": "chunk", "chunk": 2, "step": 30, "rtt_ms": 523.4,
 "board": {"pre_ms": 11.9, "vision_2v_ms": 83.3, "bart_ms": 6.7, "proj_ms": 12.6, "core10_ms": 223.1, "total_ms": 357.6},
 "planned_eef_pos_m": [[-0.202, -0.0023, 1.1878], "... 30 points"]}

{"type": "error", "code": "board_timeout", "message": "no reply from the board within the timeout"}

{"type": "ended", "result": "success", "goal": {"...": "same as started"}, "steps": 87, "chunks": 3,
 "wall_s": 23.14, "video_url": "/api/episodes/ep_20261126_123823/video"}
```

Fields:

- `agentview` (front camera) and `wrist` (eye-in-hand camera) are base64 JPEG, 360 × 360, already the right way up. Show them with `src = "data:image/jpeg;base64," + frame.agentview`.
- `eef_pos_m` is the measured end-effector position in metres. `planned_eef_pos_m` holds the 30 targets the board just planned, also in metres. The arm usually ends a chunk a few centimetres short of the last target (46 mm in one check), and that's normal.
- `joint_pos_rad` holds the 7 joints of the Franka Panda, measured. There is no per-joint command.
- `gripper` is `open` or `closed`, taken from the current action.
- `result` is one of:

  | `result` | Meaning |
  | --- | --- |
  | `success` | The goal held |
  | `failure` | Scored, but the step cap was reached |
  | `unscored` | Not scored, and the step cap was reached |
  | `stopped` | Stop was pressed |
  | `error` | Something failed; an `error` message comes first |
- `error.code` is `board_unreachable`, `board_timeout` (no reply within 10 s), `board_error` (the board replied with an error) or `sim_error`.
- `video_url` and `wall_s` can be `null`, for example if the episode failed before it started.

## 6. Stats panel

| Label | Field | Typical (26 Nov) |
| --- | --- | --- |
| Board time per chunk (headline) | `chunk.board.total_ms` | 335–432 ms |
| Vision encoder, NPU | `chunk.board.vision_2v_ms` | about 84 ms |
| Language encoder, NPU | `chunk.board.bart_ms` | about 6–7 ms |
| Action generator, 10 steps, NPU | `chunk.board.core10_ms` | about 225 ms |
| Image + text prep, CPU | `chunk.board.pre_ms` | 7–92 ms |
| Projector, CPU | `chunk.board.proj_ms` | 12–23 ms |
| Round trip laptop ↔ board | `chunk.rtt_ms` | 476–1085 ms (includes Wi-Fi) |
| Goal | `started.goal.label`, or "Not scored" | — |
| Step | `frame.step` / `started.max_steps` | — |
| Chunks | `chunk.chunk` | — |
| Result | `ended.result` | — |
| NPU temperature | highest `nsp-*` in `health.board.nsp_temps_c` | 36–38 °C |

NPU time alone is `vision_2v_ms + bart_ms + core10_ms`, about 315 ms. Don't label `rtt_ms` as model time: most of the difference is Wi-Fi.

## 7. Mapping to the web app's mock transport

`robo-arm-app-main/docs/requirements.md` §13 defines a `Transport` (connect, send, stop, subscribe) with a mock. The `WebSocketTransport` should translate the bridge like this:

| Web app message | Bridge source |
| --- | --- |
| telemetry (10 Hz, per-joint action/state) | `frame`: `joint_pos_rad` as state, no per-joint action; `eef_pos_m` for the trajectory |
| status + 500 ms heartbeat | `GET /api/health` every 5 s, plus `started` / `ended` for the task state. `link.usb` becomes "board reachable" |
| task events, plan points | `started`, `ended`; plan points come from `chunk.planned_eef_pos_m` |
| command ack / nack | `POST /api/episodes` 201 / 4xx; the command form previews with `POST /api/goals/parse` |
| stop ack | `POST /api/episodes/{id}/stop` 202, then `ended` with `stopped` |
| camera meta | `started.cameras`, `started.image_size` |
| pipeline timings | `chunk.board`, `chunk.rtt_ms` |

The demo arm is LIBERO's 7-joint Franka Panda, not the SO-101. Hide the SO-101 3D viewer, or replace it with a static image. Plot the end-effector x, y and z (measured as a solid line, planned as dashed) instead of per-joint command against state.

Types for `src/types/messages.ts`:

```ts
export type BoardTimings = {
  pre_ms: number; vision_2v_ms: number; bart_ms: number; proj_ms: number; core10_ms: number; total_ms: number;
};
export type Vec3 = [number, number, number];
export type Goal = {
  scored: boolean;
  source: string | null;          // "scene's own LIBERO goal" | "LIBERO Goal task N" | "parsed prompt" | null
  label: string | null;           // e.g. "the cream cheese on the plate"
  conditions: string[][] | null;  // e.g. [["on", "cream_cheese_1", "plate_1"]]
  reason: string | null;          // why it isn't scored
};

export type StartedMsg = {
  type: "started"; episode_id: string; suite: string; task_id: number; instruction: string;
  custom_instruction: boolean; max_steps: number; fps: number; cameras: ["agentview", "wrist"];
  image_size: [number, number]; goal: Goal;
};
export type FrameMsg = {
  type: "frame"; step: number; t_sim_s: number; agentview: string; wrist: string; // base64 JPEG
  eef_pos_m: Vec3; gripper: "open" | "closed"; joint_pos_rad: number[]; reward: number;
};
export type ChunkMsg = {
  type: "chunk"; chunk: number; step: number; rtt_ms: number; board: BoardTimings; planned_eef_pos_m: Vec3[];
};
export type ErrorMsg = {
  type: "error"; code: "board_unreachable" | "board_timeout" | "board_error" | "sim_error"; message: string;
};
export type EndedMsg = {
  type: "ended"; result: "success" | "failure" | "unscored" | "stopped" | "error"; goal: Goal;
  steps: number; chunks: number; wall_s: number | null; video_url: string | null;
};
export type BridgeMsg = StartedMsg | FrameMsg | ChunkMsg | ErrorMsg | EndedMsg;

export type Scene = {
  suite: string; suite_label: string; task_id: number; instruction: string; max_steps: number;
  recommended: boolean; free_prompts: boolean; prompt_suggestions: string[];
};
export type GoalPreview = { instruction: string; custom_instruction: boolean; goal: Goal };
export type StartResponse = {
  episode_id: string; ws_url: string; instruction: string; custom_instruction: boolean; goal: Goal;
};
export type Health = {
  bridge: "ok"; episode_running: boolean; scenes_ready: string[];
  board: { reachable: boolean; host: string; mode?: string; all_on_npu?: boolean; chunks_served?: number;
           nsp_temps_c?: Record<string, number>; started_at?: string };
};
export type ApiError = { error: { code: string; message: string } };
```

## 8. Test without the board

The tests use a fake board (real TCP protocol) and a fake scene, so they need neither MuJoCo nor the board:

```bash
~/libero/bin/python -B -m pytest demo_bridge/tests -q -p no:cacheprovider
```

Against a running bridge and board:

```bash
~/libero/bin/python -m demo_bridge.smoke_client --suite libero_goal --task-id 8      # one episode, printed summary
~/libero/bin/python -m demo_bridge.record_prompts --out demo_bridge/recordings/<date>  # the 14-prompt recording
```

There is no mock mode in the bridge itself. To develop the UI without the board, keep using the web app's `MockTransport`, shaped to the messages above. `POST /api/goals/parse` works without the board.

## 9. Files

| File | Contents |
| --- | --- |
| `app.py` | FastAPI routes, WebSocket fan-out, board health polling, the single sim thread |
| `episode.py` | One closed-loop episode: board call every 30 steps, 20 Hz playback, goal check each step, JPEG frames, MP4 |
| `goals.py` | Prompt → goal: the 10 LIBERO Goal goals and the parser for new requests |
| `board.py` | The board's TCP protocol (port 8766) and `/api/status` (port 8080) |
| `sim.py` | LIBERO scenes through LeRobot 0.6.1, the scene list, the scene cache with ahead-of-time resets |
| `smoke_client.py`, `record_prompts.py` | Live checks against a running bridge |
| `tests/` | 61 tests: `test_bridge.py` (API, streaming, board protocol), `test_goals.py` (parser, scene cache) |
| `recordings/2026-11-26/` | The 14-prompt recording: results, videos, frame strips |

**Simulator threading.** All MuJoCo work runs on one thread, because the offscreen GL context belongs to the thread that created it. Building or resetting one scene takes that context away from the others. A prepared scene is therefore reused only if no other scene has run since; otherwise it's reset again first. Without that rule, it renders blank frames.
