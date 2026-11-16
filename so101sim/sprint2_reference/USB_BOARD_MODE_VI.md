# Board Mode tự động qua USB-C

## Sử dụng

Thiết lập một lần trong Windows PowerShell (không cần Administrator):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\RobotArm\SO101\usb_board_mode.ps1 -Install
```

Bộ theo dõi chạy nền ngay, và được thêm vào Startup của người dùng Windows hiện tại.
Sau khi đăng nhập Windows:

1. Cấp nguồn riêng cho Ventuno Q và chờ Linux khởi động.
2. Nối máy tính trực tiếp với cổng USB-C của board bằng cáp có truyền dữ liệu.
3. Khi máy nhận đúng Ventuno Q qua ADB, simulation tự khởi động và client trên IQ8 tự kết nối.
4. Mở **http://localhost:8000**. Dashboard hiển thị **BOARD / USB-C** và **Connected** sau handshake.

Không cần Wi-Fi, Ethernet, Internet, nhập IP hoặc chạy thủ công client mỗi lần cắm.
Board phải được thiết lập ban đầu và cho phép kết nối ADB qua USB. Cáp chỉ sạc hoặc
cắm vào bộ nguồn thay vì cổng dữ liệu của board không tạo được kết nối với máy tính.
Arduino hướng dẫn cấp nguồn board trước khi nối USB với máy tính; không mặc định
cổng USB laptop đủ cấp nguồn cho board.

Rút cáp: heartbeat mất thì simulation dừng tick (tối đa khoảng 2 giây nếu kết nối
chưa báo đóng), hủy ngay lệnh đang chạy và lệnh chờ, xóa vận tốc, dashboard tiếp tục hiển thị cảnh hiện tại.
Cắm lại: tự dựng lại kết nối và giữ nguyên scene nếu tiến trình simulation còn chạy.
Kết nối lại vẫn giữ HOLD; gateway cần gửi RESET hoặc RESUME rõ ràng. Lệnh cũ không chạy lại.
Không tự chuyển sang local control khi mất USB.

Trước lần cắm đầu tiên, chỉ bộ theo dõi chạy; dashboard chưa mở. Bộ theo dõi không
hoạt động khi Windows tắt, đang ngủ hoặc chưa đăng nhập.

## Kiểm tra, dừng, gỡ tự khởi động

```powershell
# Trạng thái hiện tại; running=true nghĩa là bộ theo dõi đang chạy.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\RobotArm\SO101\usb_board_mode.ps1 -Status

# Dừng bộ theo dõi và simulation do nó mở (giữ thiết lập Startup).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\RobotArm\SO101\usb_board_mode.ps1 -Stop

# Chạy lại ngay, không thay đổi Startup.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\RobotArm\SO101\usb_board_mode.ps1

# Dừng và bỏ tự chạy khi đăng nhập.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\RobotArm\SO101\usb_board_mode.ps1 -Uninstall
```

Chạy lặp lại lệnh khởi động không tạo thêm bộ theo dõi hoặc thêm simulation. Nếu
simulation local/LAN khác đang chiếm cổng 5050/8000, chương trình báo lỗi và chờ bạn
dừng bản đó; nó không tự đóng chương trình khác.

Log và trạng thái nằm trong thư mục runtime/ của simulation:

- `usb_board_mode.log`: nhận USB, khởi động, mất kết nối, thử lại.
- `usb_simulator.log`: MuJoCo và camera.
- `usb_board_client.log`: client chạy trên IQ8 qua ADB.
- `.usb-board-status.json`: trạng thái mới nhất, không chứa token.

`WAITING_FOR_USB` là bình thường khi chưa có board. Nếu có nhiều thiết bị ADB cắm
USB, tháo các thiết bị khác; chương trình không tự chọn ngẫu nhiên. Điện thoại,
emulator, UNO Q và kết nối ADB qua Wi-Fi không kích hoạt Board Mode.

Nếu ADB không thấy board, kiểm tra cáp dữ liệu, nguồn và thiết lập USB ban đầu trong
Arduino App Lab. Nếu Python trên board không chạy hoặc handshake lỗi, xem
`usb_board_client.log`. Bộ theo dõi tự thử lại sau lỗi, không sửa firmware.

## Cách hoạt động

- `usb_board_mode.ps1` tìm ADB đi kèm App Lab/Arduino hoặc Android SDK trên Windows.
- `start_board_mode.sh` mặc định chạy bộ theo dõi bằng Python trong môi trường WSL sẵn có.
- `usb_board_mode.py` dùng `adb -d get-serialno` để chỉ chọn USB vật lý, đọc device tree
  để xác nhận Ventuno Q, rồi tạo ADB reverse cho lệnh và ảnh camera.
- Simulation chỉ nghe `127.0.0.1:5050` và `127.0.0.1:8000`, không nghe IP LAN.
  Windows chuyển localhost vào WSL theo cấu hình WSL hiện tại.
- Trên IQ8: lệnh/trạng thái dùng `127.0.0.1:5050`; camera dùng
  `http://127.0.0.1:18000/api/observation` cho hai ảnh và góc khớp đồng bộ;
  `/api/camera/overhead` và `/api/camera/wrist` vẫn cung cấp JPEG riêng.
- Token riêng sinh ngẫu nhiên trong `runtime/.usb-board-token`; không xuất ra log hoặc tham số
  tiến trình. Mã client và token được truyền qua stdin của ADB, không ghi file lên board.
- Chỉ gỡ các reverse mapping do bộ theo dõi tạo; không ghi đè cổng của App Lab/app khác.
- Cấu hình portproxy LAN cũ không được sử dụng. Muốn dùng LAN, phải dừng bộ theo dõi
  và chọn rõ `bash start_board_mode.sh lan --allowed-ip <IP-gateway> --token-file <file>`.
  Launcher không còn đọc config của project khác. Tự thiết lập kết nối LAN phù hợp;
  các script portproxy cũ đã chuyển ra archive, không tự áp dụng lại.

## Phạm vi kết nối tự động

Client `board/usb_link_client.py` chỉ xác thực và đọc trạng thái/heartbeat.
**Connected chỉ xác nhận IQ8 trao đổi được với simulation qua USB.** Nó không xác nhận
STM32H5F5, Bridge/RPC, AI hay điều khiển servo đã hoàn thành. Client không gửi `ACTION`.
Phần `board/iq8_gateway_integration.py` hỗ trợ envelope schema v2 nhưng vẫn yêu cầu
triển khai MCU thật trước khi điều khiển. Xem [PROTOCOL_VI.md](PROTOCOL_VI.md).

Khi có gateway MCU thật, chạy bộ theo dõi với `--external-gateway` thay cho client
heartbeat mặc định, để gateway sở hữu session duy nhất:

```bash
SO101_ADB='/mnt/c/path/to/adb.exe' bash start_board_mode.sh usb --external-gateway
```

Gateway chạy trên IQ8 host dùng endpoint/token của USB. Nếu chạy trong container App Lab,
cần cấu hình quyền truy cập localhost của host; `127.0.0.1` trong container riêng không
tự trỏ tới host. Chưa tự chỉnh hay triển khai app/firmware có sẵn trên board.

## Kiểm chứng phần mềm

```bash
~/.venvs/so101sim/bin/python -B -m unittest discover -s tests -v
~/.venvs/so101sim/bin/python -B tests/check_usb_runtime.py
```

Bài kiểm tra thứ hai chạy MuJoCo thật ở cổng tạm, kiểm tra hai camera JPEG, đường
Windows → WSL localhost, khóa web control, heartbeat, mất kết nối và kết nối lại
bằng client thử nghiệm. Nó không gửi lệnh chuyển động và không thay cho thử cắm/rút
Ventuno Q thật. Người dùng chưa có board trong lần kiểm tra này.

Nguồn kỹ thuật:

- [Arduino: ADB qua USB-C và cấp nguồn Ventuno Q](https://docs.arduino.cc/tutorials/ventuno-q/llama-cpp/)
- [ADB: lựa chọn USB `-d` và chuyển tiếp `reverse`](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)
