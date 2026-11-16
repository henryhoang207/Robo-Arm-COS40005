# Board mode — SmolVLA ONNX trên Ventuno Q điều khiển MuJoCo trên laptop (Sprint 1)

```
Laptop (WSL, C:\RobotArm\so101sim)                 Ventuno Q (host IQ8, Linux)
python app.py --mode board        (board_mode.py)
 ├─ board_server/app.py  :5050 điều khiển  <── ADB reverse 5050 ──┐
 │   (MuJoCo, schema v2) :8000 web/camera  <── ADB reverse 18000 ─┤
 └─ adb shell <venv>/python -u -  ──(stdin: bootstrap + token)──> board_runner.py   (so101arm/python)
                                                                   │  smolvla_runner.py: prefix_fp16 (CPU) + denoise core (NPU, QNN HTP)
                                                                   │  GET 127.0.0.1:18000/api/observation (2 ảnh + 6 khớp, cùng frame)
                                                                   └─ ACTION_CHUNK qua 127.0.0.1:5050 (schema v2) -> MuJoCo
```

- Một cáp USB-C, không LAN/Wi-Fi. Không có STM32, Bridge, relay hay App Lab trong đường đi này (Sprint 2 mới thêm).
- Laptop gửi bootstrap qua stdin của ADB; bootstrap ghi `board_runner.py`, `smolvla_runner.py`, `smolvla_config.json`
  vào `~/ArduinoApps/so101arm/python/` trên board (để code trên board luôn trùng laptop) rồi chạy.
  PID của runner: `/tmp/so101-board-runner.pid`.
- Token phiên tạo mới mỗi lần chạy, đi qua stdin, không nằm trong lệnh/log.
- Model (684 MB) phải có trên board ở `~/ArduinoApps/so101arm/python/ai/` hoặc `/home/arduino/`
  (`smolvla_prefix/`, `smolvla_w8a16/`). Chưa có thì chạy một lần với `--push-models`.
- Python trên board mặc định `/home/arduino/onnx-qnn-experiment/venv/bin/python` (cần numpy, Pillow, tokenizers,
  onnxruntime có QNNExecutionProvider). Đổi bằng `--board-python`.

## Một vòng (cycle)

1. Vòng đầu: `RESET` (seed, bóng mục tiêu).
2. Quan sát: `/api/observation` → ảnh overhead + wrist (JPEG) và 6 góc khớp (rad) của cùng một frame.
3. Suy luận trên board: tiền xử lý → prefix (CPU) → 10 bước denoise (NPU) → 50×6 target (rad), lấy K target đầu.
4. Kiểm tra tay robot không lệch quá 0,02 rad so với lúc quan sát.
5. Runner kẹp target vào giới hạn khớp và **giãn thời gian** ở bước nào vượt 90 % tốc độ cho phép
   ([2,2,2,3,3,4] rad/s) vì simulator từ chối CẢ chunk nếu một điểm sai; rồi gửi `ACTION_CHUNK`.
6. Chờ simulator báo `completed_sequence`. `EXECUTION_TIMEOUT` (tay bị chặn, ví dụ tì vào bàn) được ghi là
   `blocked` và vòng sau quan sát lại; lỗi khác thì dừng.

Trong lúc model suy nghĩ:

| `--think` | Simulator | Chấm điểm lượt chạy |
|---|---|---|
| `hold` (mặc định, cách đã chạy thật 09/11) | đóng phiên → HOLD, thời gian mô phỏng dừng | luôn ABORTED (simulator coi mỗi lần HOLD là hủy lượt) |
| `live` | giữ phiên, PING mỗi 0,5 s; thời gian vẫn chạy, tay giữ nguyên | RUNNING → SUCCESS / FAILURE (giới hạn 60 s mô phỏng) |

## Lệnh

```bash
cd /mnt/c/RobotArm/so101sim && source ~/.venvs/so101sim/bin/activate
python app.py --mode board                         # 3 vòng × 25 target, NPU
python app.py --mode board --push-models           # lần đầu, nếu board chưa có model
python app.py --mode board --cycles 20 --think live --target red_ball
python app.py --mode board --core-provider cpu     # so sánh: core chạy CPU của board
```

Tùy chọn khác: `--k` (1..50), `--task "..."`, `--seed`, `--board-python`, `--board-dir`, `--web-port`, `--no-viewer`, `--adb`.

Kết quả: `runtime/board-runs/<thời gian>-runner.log` và `-summary.json` (mỗi vòng: thời gian preprocess / prefix /
core / postprocess, số target, số bị kẹp, thời lượng chunk, `first_jump_rad`, đích/đạt, trạng thái lượt chạy).
Log simulator: `runtime/board_simulator.log`; log từng lượt: `runtime/runs/<run_id>.jsonl`.
Chép những lượt muốn dùng làm bằng chứng sang `C:\RobotArm\docs\evidence\`.

## Diễn tập không cần board (`--rehearsal`)

```bash
python app.py --mode board --rehearsal                      # 3 vòng × 25 target, think=hold
python app.py --mode board --rehearsal --cycles 20 --think live
```

Đi đúng đường board mode, chỉ thay ADB bằng "board = laptop này": mở `board_server` thật (MuJoCo + dashboard), gửi bootstrap
qua stdin, chạy `board_runner.py` với **2 model ONNX thật**, gửi `ACTION_CHUNK` qua TCP 5050. Khác board thật ở 3 điểm:
không có USB-C/ADB, denoise core chạy **CPU** (không NPU, chậm hơn nhiều), runner dùng Python của venv WSL
(cần `pip install onnxruntime tokenizers`). Model lấy từ `C:\RobotArm\ai`.

Kết quả ghi vào `runtime/board-runs/<thời gian>-rehearsal-*.{log,json}` và `summary.mode = "laptop_rehearsal_no_board"`,
để không bị nhầm với lượt chạy trên Ventuno Q. Số đo thời gian ở đây là của CPU laptop, không dùng làm số liệu NPU.

## Kiểm tra không cần board

```bash
python -B -m unittest tests.test_board_mode -v      # runner + điều phối với simulator giả; 3 test dùng MuJoCo thật
cd board_server && python -B -m unittest discover -s tests -v && python -B tests/self_test.py
```

## Lỗi thường gặp

| Thông báo | Cách xử lý |
|---|---|
| Đang chờ Ventuno Q qua USB-C… (mãi) | Cáp chỉ sạc, board chưa khởi động xong, hoặc App Lab chưa từng mở trên laptop (cần adb.exe của App Lab) |
| Cổng 8000/5050 đang bận | Đang có simulation khác chạy; Ctrl+C cửa sổ đó, hoặc `--web-port 8001` |
| Trên board không có Python của model | Sai đường dẫn venv; dùng `--board-python` |
| Python trên board thiếu thư viện | `pip install tokenizers pillow` trong venv đó (board cần Internet hoặc chép wheel) |
| không có QNNExecutionProvider | venv không phải bản onnxruntime-qnn; thử `--core-provider cpu` để tách lỗi |
| Trên board chưa có model | `--push-models` |
| Simulator từ chối: Chunk exceeds configured target speed | Không nên xảy ra (runner đã giãn thời gian); gửi log `-runner.log` |
| Ảnh simulator thiếu hoặc cũ | Camera trên laptop chưa render được; xem `runtime/board_simulator.log` |

## Trạng thái kiểm chứng (11/11/2026)

- Simulator `board_server/` là code đã chạy thật với board ngày 09/11 (model PyTorch), chỉ đổi đường dẫn khi chuyển vào đây.
- `board_mode.py` (bản sửa) và `board_runner.py` (mới): 12 test với simulator giả + ADB giả đều qua; runner với 2 model ONNX
  thật trên CPU gửi được 2 chunk hợp lệ. **Chưa chạy** với MuJoCo thật, board thật, hay NPU.
- Đây là kiểm tra đường ống model → simulation, không phải tỷ lệ gắp thành công.

## Sprint 2: thêm STM32

Runner sẽ đưa chunk cho STM32 duyệt/lên lịch qua Bridge trước khi gửi sang simulator; giao thức phía laptop không đổi.
Code đã chạy thật 05/11 (duyệt từng action): `C:\RobotArm\so101arm\mcu_v1_reference\` và `sprint2_reference/`.
Nếu app chạy trong container App Lab thì cần `host_relay.py` vì container không thấy cổng ADB reverse của host.
