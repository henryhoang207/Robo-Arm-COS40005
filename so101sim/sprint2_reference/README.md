# sprint2_reference — phần laptop của đường "model → STM32 → simulator" (tham khảo cho Sprint 2)

Lấy từ `RobotArm_backup_2026-11-08.zip`, giữ nguyên nội dung. **Chưa nối vào bố cục hiện tại**: các đường dẫn trong
file còn trỏ tới bố cục cũ (`C:\RobotArm\robo-arm`, `C:\RobotArm\SO101`), phải sửa trước khi chạy.

| File | Vai trò |
|---|---|
| `tests/test_bridge.py`, `native_driver.cpp` | Chạy đúng `controller.h` của firmware (biên dịch bằng g++) thay cho Arduino Bridge; test gateway |
| `tests/test_policy.py`, `test_robot_app.py` | Vòng model → MCU duyệt → simulator với supervisor C++ thật, model giả |
| `tests/build_firmware.ps1` | Chỉ biên dịch thử firmware bằng arduino-cli của App Lab (không nạp) |
| `usb_board_mode.py` | Giám sát USB + khởi động `host_relay.py` trên board (`UsbBoardMonitor.start_board_link`) |
| `upload_board_app.py` | Chép app lên `~/ArduinoApps/...` qua ADB, có backup và kiểm tra SHA-256 |
| `USB_BOARD_MODE_VI.md` | Hướng dẫn cũ của chế độ này |

Firmware và gateway tương ứng: `C:\RobotArm\so101arm\mcu_v1_reference\`.
Simulator schema v2 mà các test này nói chuyện cùng hiện ở `../board_server/`.
