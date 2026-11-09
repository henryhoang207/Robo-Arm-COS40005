# SO-101 Unified Simulation — MuJoCo + Web + VENTUNO Q

**Một mô phỏng / một chương trình chạy chính:** `models/SO101/workspace.xml` + `app.py`.

## Có trong ZIP

- SO-101 follower, **6 actuator**; initial pose đọc từ `ready_pose.json` và áp dụng theo **joint names** (không áp dụng nhầm vào freejoints của bóng).
- Bàn thao tác, **4 bóng đỏ/xanh lá/xanh dương/vàng** với freejoint, hộp chứa, camera **overhead** và **wrist**; physics MuJoCo.
- Dashboard web theo dõi hai camera (nếu OpenGL render được), joint feedback, trạng thái và sequence.
- Một cổng TCP newline-delimited JSON để IQ8 trên VENTUNO Q kết nối; `HELLO`, `PING`, `GET_STATE`, `ACTION`; nhận command 6D radians, trajectory mềm, kiểm tra giới hạn, timeout, heartbeat.
- Chế độ **local** cho smoke-test trên laptop, chế độ **board** chỉ nhận action từ TCP gateway của VENTUNO. Web là read-only trong board mode.

> **Quan trọng:** STL trong ZIP là **proxy đơn giản tự tạo** vì bản upload của bạn **không có assets/STL chính thức**. Bộ ZIP có thể nạp được khi cài MuJoCo, nhưng hình dáng/collision là placeholder và **không được dùng để đo chất lượng grasp**. Hãy thay bằng STL thật để khôi phục hình dáng SO-101 như bạn đang dùng trên laptop.

> **Chưa hoàn thành:** Firmware STM32H5F5, Arduino App Lab Bridge/RPC, SmolVLA và IQ8 gateway dùng MCU thật, chính sách watchdog trên MCU, kiểm chứng thực tế. TCP handshake từ IQ8 **không chứng minh** MCU đã kiểm tra lệnh. `board/iq8_gateway_integration.py` cố ý chặn hoạt động cho đến khi kết nối được firmware thật.

## 1. Cài đặt trên Ubuntu WSL2 (laptop của bạn)

Giải nén vào ví dụ `C:\RobotArm\SO101_Unified_VentunoQ` trên Windows. Mở Ubuntu WSL:

```bash
cd /mnt/c/RobotArm/SO101_Unified_VentunoQ
source ~/.venvs/so101sim/bin/activate
python -m pip install -r requirements.txt
```

Nếu chưa có môi trường ảo:

```bash
python3 -m venv ~/.venvs/so101sim
source ~/.venvs/so101sim/bin/activate
python -m pip install -r requirements.txt
```

## 2. Thay STL proxy bằng STL **thật** đang có trên máy

Dùng đúng folder chứa `base_so101_v2.stl`, `upper_arm_so101_v1.stl`, v.v. **Nếu bạn vẫn còn project MuJoCo đã chạy đẹp trên laptop, ưu tiên chép từ chính project cũ:**

```bash
python scripts/import_official_assets.py \
  --source /mnt/c/RobotArm/so101sim/models/SO101/assets
```

Hoặc nếu có nguyên repo gốc:

```bash
python scripts/import_official_assets.py \
  --source /mnt/c/RobotArm/SO-ARM100-main/Simulation/SO101/assets
```

Nếu không đúng đường dẫn, tìm `base_so101_v2.stl` trong ổ C rồi đưa đường dẫn thư mục chứa file vào `--source`. Script sao lưu proxy và không sửa XML scene hay pose. Nguồn STL gốc: https://github.com/TheRobotStudio/SO-ARM100/tree/main/Simulation/SO101/assets

## 3. Kiểm tra model

```bash
python -m unittest discover -s tests -v
python self_test.py
```

`self_test.py` xác minh XML, 6 actuator, 4 bóng, hộp, 2 camera và pose; chỉ xác minh tải model, **không chứng minh grasp task thành công**.

`test_grasp.py` phát một quỹ đạo kiểm tra qua bộ điều khiển mô phỏng. Test yêu cầu nâng bóng đỏ ít nhất 7 cm và giữ bóng tiếp xúc với cả hai má kẹp. Đây là phép kiểm tra vật lý trước khi đánh giá SmolVLA.

## 4. Chạy **một môi trường duy nhất** và web

```bash
python app.py --mode local
```

Trên Windows mở **http://localhost:8000**. MuJoCo Viewer mở cùng một scene; nếu máy hỗ trợ OpenGL trong WSL2, web hiển thị ảnh của hai camera cập nhật. Chế độ `local` có nút điều khiển 6 khớp để thử; robot sẽ không tự chạy quỹ đạo khi mở.

Nếu chỉ cần web/offscreen, thử:

```bash
python app.py --mode local --no-viewer
```

**Camera không lên web?** Xem `http://localhost:8000/api/state` và trường `camera_error`. WSLg/OpenGL/EGL của máy quyết định việc offscreen render có chạy được; không đánh đồng việc viewer hiển thị với camera renderer chắc chắn hoạt động. Bạn có thể thử `MUJOCO_GL=egl` khi EGL đã được cấu hình phù hợp. Không thay đổi camera XML liên tục nếu vấn đề là driver.

### Chạy checkpoint SmolVLA trực tiếp trong MuJoCo (Windows)

Từ thư mục gốc repo, dùng Python 3.12 hoặc 3.13. Nếu đã có `so101sim\.venv` với các gói bên dưới, chạy thẳng lệnh rollout.

```powershell
python -m venv so101sim\.venv
.\so101sim\.venv\Scripts\python.exe -m pip install -r so101sim\requirements.txt
.\so101sim\.venv\Scripts\python.exe -m pip install --extra-index-url https://download.pytorch.org/whl/cu128 'torch==2.8.0+cu128' 'torchvision==0.23.0+cu128' 'lerobot[smolvla]==0.7.0'
```

```powershell
$checkpoint = 'C:\path\to\pretrained_model'
$env:HF_HUB_CACHE = Join-Path (Get-Location) 'data\models\huggingface'
.\so101sim\.venv\Scripts\python.exe so101sim\run_smolvla.py $checkpoint --task 'Place the ball into the bowl to clear the desk' --steps 1000 --desk-cleanup --viewer
```

Runner dùng scene SO-101 hiện có và đọc trọng số, bộ chuẩn hoá và cấu hình từ checkpoint. Lần đầu cần tải cấu hình và tokenizer SmolVLM2 từ Hugging Face. Bỏ `--viewer` để chạy kiểm tra ngoài màn hình, thêm `--steps 60` để chạy thử hai lượt suy luận ngắn. Thiết bị mặc định là CUDA nếu khả dụng, có thể chọn `--device cpu`.

Runner ánh xạ camera overhead và wrist vào `desk_view` và `wrist_left`, rồi áp dụng mục tiêu khớp ở 30 Hz. Quy đổi thử nghiệm dùng độ cho năm khớp tay và ánh xạ tuyến tính giá trị gripper 0–100 vào giới hạn MuJoCo. Checkpoint học từ [dữ liệu robot thật](https://huggingface.co/datasets/Project-IRA/TPSoSe2026_Dataset_Full_Merged_Final_LeRobot_SO101_V1), nên kết quả gắp còn phụ thuộc góc camera, vật thể và hiệu chuẩn của scene. Runner chỉ điều khiển arm mô phỏng.

Runner làm mượt và giới hạn tốc độ thay đổi mục tiêu ở mỗi bước vật lý để giảm giật. Để kiểm chứng thao tác gắp, căn camera cổ tay sao cho thấy cả hai má kẹp, đặt camera bàn theo góc nghiêng của dữ liệu, và bắt đầu với một bóng cùng một bát. Đối chiếu góc khớp và độ mở kẹp với các tư thế đã ghi, sau đó phát lại một lần gắp mẫu để kiểm tra va chạm và khả năng nhấc bóng trước khi đánh giá policy. Episode 230 của prompt trên dài khoảng 32 giây.

`--desk-cleanup` bật scene hiệu chỉnh cục bộ theo episode 230 của bộ dữ liệu Project-IRA. Scene bắt đầu ở frame 100 để tránh va chạm của tư thế gập tay, dùng một bóng và một bát, đồng thời áp dụng offset khớp và ánh xạ độ mở kẹp theo cả hai chiều. Các góc camera được ước lượng từ video. Trong MuJoCo 3.17, phát lại lệnh của episode từ frame 100 nâng bóng khoảng 14 cm và bóng rơi vào bát trước thời điểm mở kẹp trong bản ghi. Đó là phép thử quỹ đạo ghi sẵn. Lệnh trên vẫn chạy suy luận SmolVLA từ checkpoint được cung cấp.

Runner tự bật hiệu chỉnh khi `train_config.json` khớp bộ dữ liệu và revision đã dùng để hiệu chỉnh, đồng thời prompt là `Place the ball into the bowl to clear the desk`. Có thể dùng `--desk-cleanup` để chọn rõ cấu hình hoặc `--no-desk-cleanup` để mở scene mặc định. Chiều dương của `wrist_roll` được đối chiếu với video episode 267 và 338, với hai chuyển động ngược chiều có biên độ trên 110°.

Thêm `--match-dataset` vào lệnh trên để mở scene có hình ảnh bám sát episode 230 hơn. Scene dùng các mốc bàn, bóng, bát và má kẹp ở nhiều khung hình để ước lượng tiêu cự, tâm ảnh và tư thế của hai camera. Bóng có ba mảng màu, mặt bàn có các dấu đen, còn các vật nhỏ trong bát chỉ được mô phỏng về mặt hình ảnh. Runner lấy cả hai ảnh RGB ở 640×480 với cùng tỉ lệ 4:3 như bản ghi. Replay trên scene này nâng bóng khoảng 14 cm và đưa bóng vào bát. Khi thử tự chạy từ đầu với checkpoint hiện tại, cấu hình `--desk-cleanup` cho đường tiếp cận gần bóng hơn trong lượt đối chiếu.

### Phát lại lệnh đã ghi của episode 230

```powershell
.\so101sim\.venv\Scripts\python.exe so101sim\replay_desk_cleanup.py --match-dataset --viewer
```

Script phát các frame 100–948 ở 30 Hz qua cùng bộ đổi đơn vị và làm mượt của runner SmolVLA. Cửa sổ giữ lại khung hình cuối đến khi đóng. Bỏ `--viewer` để chỉ in kết quả, hoặc bỏ `--match-dataset` để so sánh với scene hiệu chỉnh mặc định.

Tệp cục bộ `data/raw/desk_cleanup_episode_230.npz` chứa mảng `action` (949 × 6) lọc theo `episode_index=230`, sắp theo `frame_index`, cùng giá trị `fps=30`. Nguồn là [Parquet của Project-IRA ở revision dùng để huấn luyện](https://huggingface.co/datasets/Project-IRA/TPSoSe2026_Dataset_Full_Merged_Final_LeRobot_SO101_V1/blob/bf6f568e9ec218fff838fb266e161724ec4f7e2c/data/chunk-000/file-000.parquet). Chạy replay chỉ cần dữ liệu này và MuJoCo.

## 5. Kết nối mạng với VENTUNO Q — giai đoạn link test

Chọn IP laptop thực sự có thể truy cập từ board; WSL2 NAT có thể yêu cầu port forwarding hoặc mirrored networking. TCP cần hai thiết bị **có đường mạng tới nhau**. **USB-C cắm vào VENTUNO không mặc định có nghĩa là có TCP/IP**; chỉ dùng nếu đã cấu hình USB networking.

Trên laptop (thay thông tin thật):

```bash
export SO101_TOKEN='GENERATE_YOUR_OWN_32_RANDOM_CHAR_TOKEN'
python app.py --mode board --allowed-ip 192.168.1.50
```

`--allowed-ip` là IPv4 của IQ8 Linux; không phải IP laptop. Server mặc định nghe TCP port `5050`; web dashboard `http://localhost:8000`, read-only. Nếu cần web xem trên thiết bị khác trong trusted LAN, thêm `--web-host 0.0.0.0` và cấu hình firewall phù hợp.

Chép `board/connectivity_probe.py` sang IQ8 Linux và chạy:

```bash
python3 connectivity_probe.py --host 192.168.1.20 \
  --token 'GENERATE_YOUR_OWN_32_RANDOM_CHAR_TOKEN'
```

`--host` phải là địa chỉ laptop mà IQ8 truy cập được. Probe kiểm tra handshake, PING, GET_STATE, **KHÔNG điều khiển robot**.

**Trạng thái sau probe thành công:** network connection IQ8 → laptop thành công. **Chưa phải** kết nối IQ8 ↔ STM32H5F5 hay AI inference.

## 6. Tích hợp STM32H5F5 / Arduino App Lab

Hệ thống đích:

`SmolVLA (IQ8) → Arduino App Lab Bridge/RPC → STM32H5F5 [validate + schedule + watchdog] → IQ8 TCP gateway → app.py/MuJoCo → joint state + images → IQ8`.

Bạn phải triển khai firmware, board-side RPC và camera bridge bên IQ8 theo giao diện thực của bản Arduino App Lab đang dùng. Đừng dùng `board/connectivity_probe.py` làm firmware. Trong folder có `board/iq8_gateway_integration.py` **là integration scaffold chưa phát lệnh**: nó cố ý dừng cho tới khi thực sự đọc được *MCU-approved action*. MuJoCo không thể tự xác nhận lệnh đã đi qua MCU từ mỗi gói JSON.

Về mặt giao thức TCP, gửi từng lệnh 6 khớp (radians), ví dụ:

```json
{"type":"ACTION","sequence_id":1,"joint_targets":[-0.75,-0.2,0.2,1.4,0,0.8],"duration":2.0,"timeout":4.0}
```

**Đơn vị**: các góc MJCF radians, **không** phải độ, servo ticks, LeRobot normalized value hoặc (0..100) gripper. Bạn phải làm mapping/calibration trên gateway/MCU trước khi gửi.

### Camera / AI

Browser đọc `GET /api/camera/overhead` và `/api/camera/wrist` (JPEG), `GET /api/state` (JSON). Đây là web endpoints trên laptop, **không phải** RPC tự động tới SmolVLA. IQ8 có thể tải ảnh qua HTTP khi có tuyến mạng; AI preprocessing, timing và đồng bộ timestamp phải được triển khai thêm. Hiện dashboard đã có chức năng xem hai luồng camera qua HTTP polling.

## 7. Các hạn chế về an toàn & validation

- Web/TCP không có TLS. Chỉ chạy trên mạng riêng tin cậy; không port-forward `5050/8000` ra Internet. Đổi token dài khó đoán.
- Demo proxy mesh không dùng để chứng minh tính khả thi gắp bóng, force/contact, reachability hay real servo safety.
- `ACK` nghĩa là **đã cho vào hàng đợi**, không phải đạt target. Theo dõi `STATE.status`, `applied_sequence` và `joint_positions`.
- Server-side joint bounds/timeout chỉ là tầng bổ trợ; **không thay firmware validation của STM32**.
- Mất kết nối board thì simulation dừng tick; **đây không phải emergency stop cho robot vật lý**.
- Camera XML trong gói dựng lại theo góc top-down đã thống nhất; vì thiếu XML cuối trên laptop nên góc có thể không trùng 100% ảnh cũ. Thay STL thật rồi kiểm tra layout trước khi đo benchmark.

## 8. Tại sao không còn nhiều môi trường?

Không dùng `scene.xml`, `preview_ready.py`, `server.py` cũ, không chạy `upgrade_workspace.py` hay `tune_cameras.py` nữa. **Chỉ chạy `app.py`, chỉ nạp `workspace.xml`.** Các công cụ trong `scripts/` không tạo một scene khác.
