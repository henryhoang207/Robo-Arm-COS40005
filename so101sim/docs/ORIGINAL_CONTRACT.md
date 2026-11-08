# Integration contract (draft, NOT hardware-validated)

## Required execution route (team decision 20 October 2026)
AI / SmolVLA on IQ8 -> Arduino Bridge/RPC -> STM32H5F5 validates and schedules
-> IQ8 Python network gateway -> Windows TCP server -> MuJoCo SO-101.
Feedback: MuJoCo qpos -> IQ8 gateway -> STM32 state processing -> IQ8/SmolVLA.

* No approved STM32H5F5 firmware, IQ8 gateway, AI inference, or real-board RPC has been tested by this starter.
* The server's IP/token handshake authenticates a network session, not proof that a command passed through STM32. The gateway MUST enforce the actual MCU gate when integrated.
* Server currently expects one 6D joint-target vector per message, not 50-step SmolVLA chunks.
* Units are raw MJCF actuator position units (radians for these joints). Do NOT send normalized LeRobot outputs directly. Gripper mapping remains TODO.
* No IK, autonomous grasp, or solved grasp trajectory is supplied.

## Debug network protocol (newline-delimited JSON)
Client -> server:
  {"type":"HELLO", "token":"..."}
  {"type":"ACTION","sequence_id":1,"joint_targets":[0,0,0,0,0,0]}
  {"type":"GET_STATE"}
  {"type":"PING"}
Server -> client:
  {"type":"WELCOME", ...}
  {"type":"ACK","sequence_id":1,"meaning":"Accepted into queue, not reached target"}
  {"type":"STATE","joint_positions":[...],"sim_time":...,"executed_sequence":...,"status":"ACTIVE"}
  {"type":"PONG"}
  {"type":"REJECTED","reason":"..."}

TCP is a byte stream; messages are framed by newline, and `readline()` enforces the 16KiB ceiling. This is NOT the 46-byte binary Action/State PoC framing and NOT the Feetech servo protocol.

## Future STM32 design obligations
STM32 must meaningfully own validation, bounded scheduling, watchdog, fault handling, and execution-state decisions. IQ8 gateway must forward *only MCU-approved* actions to MuJoCo. Define action frequency, calibration, normalization, timestamp and units before integrating the AI checkpoint. Implement board-side code via the officially supported Arduino App Lab Bridge/RPC examples. All real-board tests and observed timing remain pending.

## Safety limitations
No LAN token scheme alone certifies a physical VENTUNO Q, and this sample provides no TLS. Keep the demo on a trusted isolated LAN; use a long random token and allowlist the board IP. Do not forward TCP/5050 to the public internet. The MuJoCo disconnected-state physics freeze is not an emergency stop for a physical arm.
