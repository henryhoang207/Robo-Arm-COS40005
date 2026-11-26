# Goal-scene prompt recording, 26 Nov 2026

14 prompts in the demo scene (LIBERO Goal task 8, seed 1000), run through the bridge with X-VLA W8A16 on the VENTUNO Q board's NPU. One episode per prompt; step cap 400. Each prompt has `<name>.mp4` (front | wrist camera, 20 fps), a frame strip `<name>.jpg` (front camera every 60 steps plus the final frame) and a row in `results.json`. Recorded with `python -m demo_bridge.record_prompts`.

**All 10 LIBERO Goal instructions succeeded in this one scene. All 3 new combinations failed. The unscored prompt was stopped as intended.**

| Prompt | Scored against | Result | Steps | Episode time | What the arm did |
| --- | --- | --- | --- | --- | --- |
| put the bowl on the plate | Scene's own goal | success | 76 | 13.7 s | Bowl onto plate |
| put the bowl on the stove | Goal task 1 | success | 87 | 23.1 s | Bowl onto stove |
| turn on the stove | Goal task 7 | success | 80 | 23.6 s | Turned the stove knob |
| open the middle drawer of the cabinet | Goal task 0 | success | 122 | 29.5 s | Opened middle drawer |
| put the wine bottle on the rack | Goal task 9 | success | 136 | 35.6 s | Bottle onto rack |
| put the wine bottle on top of the cabinet | Goal task 2 | success | 98 | 29.9 s | Bottle onto cabinet top |
| put the cream cheese in the bowl | Goal task 6 | success | 86 | 24.5 s | Cream cheese into bowl |
| push the plate to the front of the stove | Goal task 5 | success | 142 | 46.6 s | Pushed plate |
| put the bowl on top of the cabinet | Goal task 4 | success | 89 | 36.7 s | Bowl onto cabinet top |
| open the top drawer and put the bowl inside | Goal task 3 | success | 192 | 62.0 s | Opened drawer, bowl inside |
| put the cream cheese on the plate | Parsed: cream cheese on plate | failure | 400 | 112.4 s | Carried it to the plate, but held it there and never let go |
| put the wine bottle on the plate | Parsed: wine bottle on plate | failure | 400 | 114.6 s | Put the bottle on the rack instead (its trained habit for the bottle) |
| put the cream cheese on the stove | Parsed: cream cheese on stove | failure | 400 | 89.4 s | Carried it to the stove, held it there, never let go |
| wave hello | Not scored | stopped | 120 | 24.2 s | Moved around; stopped by the recorder at step 120 |

- **Board, every episode:** 340–432 ms per 30-step chunk; round trip from the laptop 476–1085 ms.
- **Start time** (request to `started`):
  - 0.5 s for the first episode, with the scene prepared and idle.
  - 7.5–20 s for back-to-back episodes, which waited for the bridge to finish re-resetting the scene.
- **How success was judged:** by LIBERO's own predicate functions on the simulator state, not by eye. For the 10 Goal instructions these are the exact goal conditions from LIBERO's task files. The "what the arm did" column comes from the frame strips and final frames, which match every result.
- **When episodes end:** the moment the condition holds, as in LIBERO. Several final frames still show the object in the gripper (bowl on plate, bowl on cabinet).
- **Rendering bug, found and fixed during this recording.** The first take of "put the bowl on the plate" rendered blank white frames after step 0 and failed. Building a second scene after preparing this one had taken over the renderer. The bridge now re-resets a prepared scene if another scene ran since; the take above was re-recorded after the fix. The invalid take is kept in `../_invalid_blank_frames/`.
