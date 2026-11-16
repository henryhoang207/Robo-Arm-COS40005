# Hợp đồng simulation — schema v2

> Áp dụng cho simulator board mode trong `so101sim/board_server/` (app.py, engine.py, protocol.py). Local mode ở
> `so101sim/app.py` dùng giao thức web đơn giản riêng (xem README_VI.md). Log lượt chạy: `so101sim/runtime/runs/`.

Đơn vị: mét, giây, radian. Thứ tự khớp cố định:
shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper.
Gripper cũng là góc radian; không tự coi là giá trị LeRobot 0–100.
Giới hạn khớp trả về trong /api/state lấy từ MJCF thực tế.

## Phiên và lượt chạy

- TCP là JSON UTF-8, một object mỗi dòng kết thúc bằng newline, tối đa 64 KiB/dòng.
- USB: TCP 127.0.0.1:5050 và HTTP 127.0.0.1:8000 phía laptop; ADB reverse đưa
  HTTP thành cổng 18000 phía IQ8 host. Không có tự chuyển sang LAN.
- HELLO có token; WELCOME trả schema_version=2, run_id, session_id,
  requires_resume và accepted_sequence. Chỉ một session điều khiển tại một thời điểm.
- Mọi lệnh thay đổi trạng thái phải có schema_version=2, run_id và session_id
  đúng hiện tại. RESET thay run_id; reconnect thay session_id. Lệnh từ lượt/phiên cũ bị từ chối.
- sequence_id là số nguyên uint32 tăng nghiêm ngặt trong lượt chạy; RESET đưa
  accepted/applied/completed về -1. Không tự gửi lại lệnh sau reconnect.
- GET_STATE/PING không cần các trường context; gửi ít nhất mỗi 0,5 giây.
  Quá 2 giây không có heartbeat, socket đóng hoặc lỗi thực thi sẽ HOLD và hủy queue.
  Heartbeat đến muộn không tự bỏ HOLD. Timeout socket là 2,5 giây.
- Khôi phục: heartbeat hợp lệ rồi RESUME rõ ràng, hoặc RESET để bắt đầu lượt mới.
  RESUME không biến lượt ABORTED thành RUNNING; muốn chấm lượt mới thì RESET.

## Lệnh

Ví dụ ACTION; thay run_id/session_id bằng giá trị vừa đọc từ simulator:

```json
{
  "type": "ACTION",
  "schema_version": 2,
  "run_id": "run-id-from-state",
  "session_id": "session-id-from-state",
  "sequence_id": 0,
  "joint_targets": [-0.63, -0.2, 0.2, 1.4, 0.0, 0.8],
  "duration": 2.0,
  "timeout": 5.0,
  "valid_for_s": 10.0,
  "allow_gripper_contact": false
}
```

ACTION dùng quỹ đạo nối mượt bậc 5 từ góc đo lúc bắt đầu. duration 0,1–30 giây;
timeout phải lớn hơn duration và không quá 60 giây. valid_for_s là tuổi tối đa
**tính bằng đồng hồ thực của server kể từ lúc nhận** trước khi bắt đầu thực thi
(0,05–60 giây, mặc định 10). timeout thực thi dùng thời gian mô phỏng từ lúc áp dụng.
Không so sánh trực tiếp monotonic clock của board với laptop.

allow_gripper_contact=true cho phép hoàn tất khi năm khớp tay đã đạt góc và ngón
kẹp đang đóng bị một trong bốn bóng chặn bởi tiếp xúc cả hai ngón. Kết quả ghi
GRIPPER_CONTACT; không giả báo góc đã đến đích. Khi không có tiếp xúc, vẫn phải
đạt góc gripper. Không coi chỉ một ngón chạm là đã gắp.

ACTION_CHUNK dùng cùng context và sequence_id, thay joint_targets/duration bằng:

```json
{
  "points": [
    {"time_from_start": 0.5, "joint_targets": [-0.70, -0.2, 0.2, 1.4, 0.0, 0.8]},
    {"time_from_start": 1.0, "joint_targets": [-0.63, -0.2, 0.2, 1.4, 0.0, 0.8]}
  ],
  "timeout": 4.0
}
```

Đây là phần payload thêm vào envelope có type=ACTION_CHUNK, không phải message
đầy đủ. Có 1–64 điểm, thời gian tăng ít nhất 0,01 giây, tổng không quá 10 giây.
Simulator nội suy tuyến tính mục tiêu giữa các điểm; không tự làm trơn vận tốc ở
các góc nối. Cả chunk phải hợp lệ mới được nhận, không thực hiện nửa chunk lỗi.

Queue: tối đa 8 lệnh chờ, tổng thời lượng dự kiến tối đa 30 giây gồm phần còn lại
của lệnh đang chạy. Tốc độ mục tiêu tối đa cấu hình là [2,2,2,3,3,4] rad/s;
ACTION tính cả vận tốc đỉnh của nội suy bậc 5. Đây là giới hạn vận hành simulation,
chưa phải thông số an toàn của servo thật. Queue chạy tuần tự; ACK không phải DONE.

Các lệnh khác có cùng context:

| type | Ý nghĩa |
|---|---|
| ABORT | Dừng thời gian, hủy queue/lệnh hiện tại, xóa vận tốc, giữ HOLD |
| RESUME | Bỏ HOLD khi phiên đang khỏe; không chạy lại lệnh cũ |
| RESET | Đưa scene về pose gốc, tạo run_id mới; tùy chọn seed, target, randomize |

RESET nhận seed uint32, randomize boolean (mặc định false), target một trong
red_ball/green_ball/blue_ball/yellow_ball (mặc định red_ball). Randomize dịch vị
trí XY của cả bốn bóng trong ±8 mm; cùng seed cho cùng scene ban đầu.

## HTTP và dữ liệu quan sát

GET /api/state trả góc/ vận tốc đo, mục tiêu hiện tại, mục tiêu cuối, số lệnh đã nhận/
áp dụng/hoàn tất, queue, fault, HOLD và trạng thái episode. Trường units=radians.
GET /api/identity trả hash model+settings+pose+13 STL để đối chiếu môi trường.

GET /api/observation trả cùng một frame_id cho cả hai camera:

- images.overhead và images.wrist: JPEG base64, 640×480 mặc định.
- joint_positions, joint_velocities, target_positions: cùng bản sao vật lý với ảnh.
- run_id/session_id, sim_time, captured_monotonic_ns, captured_unix_ns,
  frame_age_s và stale. Ảnh cũ sau RESET không được công bố vào lượt mới.
- Không chứa tọa độ thật của các vật. Dùng frame_id để tránh suy luận lại ảnh trùng.

GET /api/camera/overhead và /api/camera/wrist là JPEG riêng, có header X-Frame-Id,
X-Run-Id, X-Sim-Time, X-Captured-Monotonic-Ns. Hai request riêng có thể rơi vào hai
frame khác nhau; dùng /api/observation khi cần cặp ảnh đồng bộ.

GET /api/evaluation chứa tọa độ thật của vật/hộp và đánh giá. Chỉ dùng cho chấm kết
quả hoặc controller tham chiếu; không đưa ground truth vào vision policy rồi
báo cáo đó là nhận diện từ ảnh.

POST /api/action, /api/reset, /api/abort, /api/resume, /api/reference chỉ được bật
trong local mode từ loopback và cùng origin. Board mode trả 403 cho tất cả.
Payload ghi luôn cần context. Lệnh được nhận trả HTTP 202; sai payload/context
trả 400. /api/reference chỉ hỗ trợ bài bóng đỏ, yêu cầu lượt mới READY.

## Chấm bài gắp–thả

READY → RUNNING khi nhận lệnh đầu tiên. SUCCESS khi bóng mục tiêu từng có tiếp xúc
cả hai ngón, được nâng cao hơn 5 cm, đã rời cả hai ngón và nằm trong lòng hộp với
tốc độ dưới 0,03 m/s liên tục 0,5 giây mô phỏng. Đặt sẵn bóng vào hộp không đủ.
Rơi khỏi bàn hoặc quá 60 giây mô phỏng là FAILURE; ABORT/mất kết nối là ABORTED.
Các ngưỡng này chấm scene hiện tại, không phải chuẩn benchmark được nhóm AI nghiệm thu.

Ghi log tại so101sim/runtime/runs/<run_id>.jsonl: run_start/end, accepted/applied/completed,
hold/resumed, state và episode_result. Log chứa hash, phiên bản MuJoCo, settings,
seed, góc đo, mục tiêu và ground truth đánh giá; không ghi toàn bộ ảnh liên tục.

## Ranh giới bằng chứng

Token xác thực một gateway, không chứng minh STM32 đã duyệt lệnh. Trường
mcu_execution_verified luôn false. Gateway cần firmware/Bridge thật, liên kết
sequence, đơn vị/calibration và nguồn lệnh được kiểm chứng trước khi báo MCU
execution. Không đặt true chỉ vì thấy ACK hoặc robot mô phỏng chuyển động.
