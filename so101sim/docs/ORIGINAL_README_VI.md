# SO-101 Unified Remote Simulation — Hướng dẫn từ số 0

Đây là **starter project chưa kết nối board**: một scene MuJoCo, 3 cube, bàn, hộp, camera overhead và Python server remote-only. Chưa có SmolVLA, STM32 firmware hay automatic grasping. Trong chế độ preview, scene không tự sinh chuyển động. Trong chế độ remote, server chỉ cho phép kết nối với IP được cho phép và token hợp lệ.

## 1. Anaconda Prompt (Windows 11)

```bat
conda --version
conda create -n so101sim python=3.11 -y
conda activate so101sim
python -m pip install -r requirements.txt
```

Mở đúng thư mục chứa `requirements.txt` trước khi pip install, ví dụ:

```bat
cd /d C:\RobotArm\so101_remote_starter
```

## 2. Lấy official SO-101 MJCF

Truy cập https://github.com/TheRobotStudio/SO-ARM100, chọn Code → Download ZIP, Extract All vào `C:\RobotArm`. Sau giải nén tìm thư mục có `Simulation\SO101\scene.xml`. Ví dụ:

`C:\RobotArm\SO-ARM100-main\Simulation\SO101`

## 3. Tạo workspace

```bat
cd /d C:\RobotArm\so101_remote_starter
python build_workspace.py --source "C:\RobotArm\SO-ARM100-main\Simulation\SO101"
python verify_model.py
```

Output `PASS: robot, 6 actuators, cubes, box, camera` là model compile và cấu trúc đúng. Chưa phải grasp success.

## 4. Mở scene ở chế độ không có controller

```bat
python server.py --mode preview
```

MuJoCo sẽ hiển thị arm và scene. Arm không tự nhận trajectory; simulator không có network server trong mode này và physics được pause khi không có controller. Đóng cửa sổ MuJoCo để thoát.

## 5. Test loopback tại nhà, CHỈ development

Mở Anaconda Prompt số 1:

```bat
conda activate so101sim
cd /d C:\RobotArm\so101_remote_starter
python server.py --mode dev-local --token MY_DEV_TOKEN_LONG_123456
```

Mở Anaconda Prompt số 2:

```bat
conda activate so101sim
cd /d C:\RobotArm\so101_remote_starter
python dev_client.py --token MY_DEV_TOKEN_LONG_123456
```

Lệnh trên cho phép laptop giả lập VENTUNO Q trong **developer test mode**. Không được báo cáo đây là kết nối board thành công. Đóng terminal client sẽ ngừng session, không còn lệnh điều khiển.

## 6. Lúc đến lab

1. Kết nối Windows laptop và VENTUNO Q trên mạng LAN có thể truy cập lẫn nhau; ghi lại IP thật (Windows: `ipconfig`; VENTUNO Linux: `hostname -I`).
2. Cấu hình Windows firewall cho TCP 5050 trong trusted private network (khi cần); không mở port ra internet.
3. Trên laptop chạy `python server.py --mode remote --allowed-ip <IP_VENTUNO> --token <LONG_RANDOM_TOKEN>`.
4. Trên IQ8 qua App Lab, viết Python TCP client theo `CONTRACT.md`, nhưng **gateway chỉ được gửi action đã được STM32 thực thi bước validation/scheduling qua Arduino Bridge/RPC**.
5. Đo logs RPC, state frames, timeout và latency; không kết luận firmware hoạt động trước khi đã test trên board.

## 7. Những điều chưa xong

- State/action normalization (LeRobot 0..100 gripper vs MJCF range); camera-to-model mapping; visual rendering to IQ8; calibration.
- Simulation grasp-contact behavior, arm reach, drop-box task success chưa kiểm chứng.
- Real Arduino App Lab RPC, firmware STM32H5F5 và SmolVLA runtime chưa được triển khai trong starter.
- MuJoCo chỉ là robot ảo, không kiểm chứng servo bus điện và real-world timing.

Xem `CONTRACT.md` trước khi bắt đầu tích hợp AI hoặc MCU.
