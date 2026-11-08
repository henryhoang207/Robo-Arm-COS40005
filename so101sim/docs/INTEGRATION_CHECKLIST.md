# Bàn giao tích hợp VENTUNO Q và Web

## Thực sự đã có trong project này

| Lớp | Tình trạng |
|---|---|
| MuJoCo single scene (`workspace.xml`) | Đã tạo, static XML tested; compile cần MuJoCo trên WSL |
| Model follower SO-101 6 joints | Model original đã đưa vào; proxy STLs có sẵn, cần thay bằng official STL |
| Overhead camera + wrist camera | Đã khai báo MuJoCo, cần test OpenGL/camera quality |
| Ready pose (`ready_pose.json`) | Được nạp từ tên khớp trong `engine.py` |
| Physics, 4 balls, drop box | Đã mô tả MJCF, pick success chưa chứng minh |
| Website / 2 image feeds / joint feedback | HTTP app + polling có sẵn; phụ thuộc renderer/OpenGL |
| IQ8 ⇄ laptop connection | TCP protocol + `board/connectivity_probe.py`; chưa chạy trên VENTUNO thật |
| STM32H5F5 real firmware + App Lab RPC | CHƯA có; `iq8_gateway_integration.py` cố tình fail closed |
| SmolVLA inference + normalization + visual input on IQ8 | CHƯA có |
| Physical SO-101 bus, safety, controller timing | CHƯA kiểm chứng |

## Contract TCP từ IQ8 đến laptop

- Transport: TCP trusted LAN. Port 5050; one active board client. Newline-delimited JSON UTF-8.
- HELLO: `{ "type":"HELLO", "token":"..." }` → `WELCOME`.
- Keepalive: `PING` → `PONG` at least once per second; `GET_STATE` also refreshes alive clock.
- Action: `{"type":"ACTION", "sequence_id":1,"joint_targets":[0,0,0,0,0,0],"duration":2,"timeout":4}` → `ACK` or `REJECTED`.
- Feedback: `GET_STATE` → `STATE` with six `joint_positions`, `status`, `accepted_sequence`, `applied_sequence`, etc.
- `ACK` is acceptance into *queue*, not arrival at target.
- `duration` and `timeout` seconds; targets in radians in required order: shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper.
- Protocol is **not** the original 46-byte CRC binary frame or STM32 native transport. Conversion must be performed by IQ8 gateway **after actual MCU approval**.

## Những điều phải làm ở lab

1. Board's IQ8 Linux reachable from laptop WSL2: identify IP and firewall; if WSL2 NAT cannot receive LAN clients, setup mirrored networking or Windows port proxy (only private trusted network).
2. Prove handshake via `connectivity_probe.py`; note this only validates TCP and state transport.
3. Deploy real STM32H5F5 firmware, validation, timing, watchdog and joint mapping. Verify unit conversion from SmolVLA model outputs and gripper conventions.
4. IQ8 Python gateway must submit a candidate to STM32 via App Lab Bridge/RPC, verify MCU response/correlation and forward **only approved actions** to TCP server.
5. Compare IQ8 commanded targets with `STATE.joint_positions` and trajectory progress; observe missed packets, stale sequences, disconnect, invalid targets.
6. Expose HTTP image URLs to IQ8 if needed; integrate actual frame acquisition into the AI input preprocessing pipeline, including timestamps.
7. Replace proxy mesh assets with original STL before claiming task/contact accuracy. Validate pose collision and grasp success quantitatively, not from a screenshot.

## Security

No TLS and no cryptographic evidence of STM32 approval. Auth token identifies TCP session only. Never expose ports to the public internet. A paused simulator does not stop a physical servo. These are demonstration interfaces, NOT a safety-certified controller.
