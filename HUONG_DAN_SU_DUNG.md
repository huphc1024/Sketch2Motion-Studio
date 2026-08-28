# Hướng dẫn cài đặt và sử dụng Sketch2Motion Studio

Sketch2Motion Studio biến ảnh hoặc bản phác thảo thành video vẽ tay nhiều cảnh,
có timeline, lời thoại tiếng Việt bằng VieNeu Local và xuất video MP4 hoàn chỉnh.

## 1. Tính năng chính

- Quản lý dự án nhiều scene trên timeline.
- Chuyển ảnh thành SVG đơn sắc hoặc giữ màu.
- Tùy chỉnh thời lượng, hiệu ứng vẽ và chuyển cảnh cho từng scene.
- VieNeu Local v3 Turbo với 20 giọng Việt có sẵn.
- Tự động đồng bộ thời lượng scene theo voice over.
- Xem trước từng scene hoặc toàn bộ dự án.
- Xuất MP4 theo tỉ lệ `16:9`, `9:16` hoặc `1:1`.
- Hỗ trợ 720p/1080p và 30/60 FPS.
- Giao diện Light/Dark và ghi nhớ theme đã chọn.
- Lưu, mở lại dự án bằng JSON.

## 2. Yêu cầu hệ thống

Khuyến nghị trên Windows:

- Windows 10 hoặc 11, 64-bit.
- Git.
- Python 3.12. Python 3.13 cũng dùng được, nhưng 3.12 có độ tương thích tốt nhất.
- FFmpeg trong biến môi trường `PATH`.
- Potrace trong `PATH` để vector hóa ảnh.
- Kết nối Internet trong lần đầu tải model VieNeu.
- Tối thiểu 8 GB RAM; khuyến nghị 16 GB RAM khi chạy VieNeu Local trên CPU.

Kiểm tra các công cụ:

```powershell
git --version
py -3.12 --version
ffmpeg -version
potrace --version
```

## 3. Clone source code

```powershell
git clone https://github.com/huphc1024/Sketch2Motion-Studio.git
cd Sketch2Motion-Studio
```

## 4. Cài môi trường cho Sketch2Motion Studio

Tạo virtual environment chính:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn script kích hoạt, chạy lệnh sau một lần trong cửa sổ hiện
tại rồi kích hoạt lại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Bạn cũng có thể không kích hoạt môi trường và gọi trực tiếp:

```powershell
.\.venv\Scripts\python.exe app.py
```

## 5. Cài VieNeu Local

VieNeu được đặt trong môi trường riêng để model không làm ảnh hưởng tiến trình
web. Không cài `requirements-vieneu.txt` vào `.venv` chính.

```powershell
py -3.12 -m venv .venv-vieneu
.\.venv-vieneu\Scripts\python.exe -m pip install --upgrade pip
.\.venv-vieneu\Scripts\python.exe -m pip install -r requirements-vieneu.txt
```

Sao chép file cấu hình mẫu nếu muốn tùy chỉnh:

```powershell
Copy-Item .env.example .env
```

Mặc định bridge dùng:

```env
VIENEU_MODE=v3turbo
VIENEU_DEVICE=cpu
VIENEU_BACKEND=auto
VIENEU_PRECISION=int8
VIENEU_BRIDGE_PORT=8001
```

Lưu ý: source hiện đọc trực tiếp các biến môi trường hệ thống. File `.env` là
mẫu cấu hình và không được commit. Khi cần thay đổi trong PowerShell, đặt biến
trước khi chạy bridge, ví dụ:

```powershell
$env:VIENEU_DEVICE = "cpu"
$env:VIENEU_PRECISION = "int8"
```

## 6. Chạy ứng dụng

Cần mở hai cửa sổ PowerShell tại thư mục dự án.

### Terminal 1 — VieNeu Local bridge

```powershell
.\.venv-vieneu\Scripts\python.exe -m services.tts.vieneu_bridge
```

Bridge chạy tại:

```text
http://127.0.0.1:8001
```

Kiểm tra trạng thái:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

Kiểm tra danh sách giọng:

```powershell
(Invoke-RestMethod http://127.0.0.1:8001/voices).voices |
    Select-Object id, name
```

Lần đầu gọi `/voices` hoặc tạo audio, VieNeu sẽ tải model về Hugging Face cache.
Không đóng terminal khi quá trình này đang chạy.

### Terminal 2 — Sketch2Motion Studio

```powershell
.\.venv\Scripts\python.exe app.py
```

Mở trình duyệt tại:

```text
http://127.0.0.1:7880/studio/
```

Kiểm tra API của ứng dụng:

```powershell
Invoke-RestMethod http://127.0.0.1:7880/api/health
```

## 7. Quy trình sử dụng

### Tạo scene đầu tiên

1. Nhập tên dự án tại **Project title**.
2. Trong **Scene Properties**, nhập tên scene.
3. Tải ảnh lên tại mục **Image**.
4. Bật **Preserve colors** nếu muốn giữ màu gốc.
5. Chọn số màu tại **Palette**.
6. Nhập lời thoại vào **Script / Voice Over**.
7. Bấm **Generate sketch** để tạo SVG.

### Tạo giọng đọc

1. Chọn **Language → Vietnamese**.
2. Chọn **Provider → VieNeu Local · v3 Turbo**.
3. Bấm **Refresh voices** để đồng bộ voice từ bridge.
4. Chọn một trong 20 giọng Bắc, Trung hoặc Nam.
5. Điều chỉnh **Speed** và **Volume** nếu cần.
6. Bấm **Preview voice** để nghe thử.
7. Bấm **Generate Voice** để tạo voice cho scene hiện tại.
8. Dùng **Generate All Voices** để tạo lần lượt cho toàn bộ scene.

Khi **Auto duration from voice** được bật, thời lượng scene sẽ tự cập nhật theo
độ dài audio. VieNeu được chạy tuần tự để tránh tràn RAM/VRAM.

### Quản lý nhiều scene

- **＋ Add**: thêm scene mới.
- **⧉ Duplicate**: nhân bản scene đang chọn.
- **Delete** hoặc dấu `×`: xóa scene.
- Kéo thả card trên timeline để đổi thứ tự.
- Chọn **Transition** và thời lượng chuyển cảnh cho từng scene.

### Xem trước và xuất video

1. Bấm **Preview scene** để dựng scene đang chọn.
2. Mở tab **Full project** để kiểm tra toàn bộ timeline.
3. Chọn tỉ lệ khung hình, FPS và độ phân giải ở **Video Settings**.
4. Bấm **Export MP4**.
5. Tải file MP4 sau khi quá trình render hoàn tất.

Video và audio sinh ra được lưu trong thư mục `generated/`. Thư mục này đã được
Git ignore.

## 8. Lưu và mở lại dự án

- Bấm **Save project** để tải file JSON dự án.
- Dùng **Load project JSON** để mở lại.
- File JSON lưu cấu hình scene và đường dẫn tài nguyên. Khi chuyển dự án sang máy
  khác, cần chuyển cả các file ảnh nguồn tương ứng.

## 9. Dark theme

Bấm **🌙 Dark** ở thanh tiêu đề để chuyển sang giao diện tối. Nút đổi thành
**☀ Light** để quay lại giao diện sáng. Lựa chọn được lưu trong trình duyệt và
được giữ nguyên khi tải lại trang.

## 10. Chạy kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

## 11. Xử lý lỗi thường gặp

### Không thấy đủ voice

- Kiểm tra bridge `http://127.0.0.1:8001/health`.
- Đợi model tải xong trong lần chạy đầu tiên.
- Bấm **Refresh voices** trên giao diện.
- Kiểm tra `VIENEU_TTS_URL` có trỏ đến `http://127.0.0.1:8001` hay không.

### Lỗi `Cannot reach VieNeu`

Bridge chưa chạy hoặc cổng 8001 đang bị chặn. Khởi động lại Terminal 1 và kiểm
tra firewall.

### Lỗi cài `kaldi-native-fbank`

Không dùng Python 3.14 trên Windows. Xóa môi trường VieNeu cũ, tạo lại bằng
Python 3.12 rồi cài lại dependencies:

```powershell
py -3.12 -m venv --clear .venv-vieneu
.\.venv-vieneu\Scripts\python.exe -m pip install -r requirements-vieneu.txt
```

### Lỗi `ffmpeg` hoặc `potrace` không tồn tại

Cài công cụ tương ứng và thêm thư mục chứa file thực thi vào biến `PATH`, sau
đó mở cửa sổ PowerShell mới.

### Cổng 7880 hoặc 8001 đã được sử dụng

Đổi cổng qua biến môi trường:

```powershell
$env:SKETCH2MOTION_PORT = "7881"
$env:VIENEU_BRIDGE_PORT = "8002"
$env:VIENEU_TTS_URL = "http://127.0.0.1:8002"
```

### VieNeu hết RAM hoặc VRAM

- Giữ `VIENEU_PRECISION=int8` khi chạy CPU.
- Đóng ứng dụng nặng khác.
- Chỉ chạy một VieNeu bridge.
- Không tăng concurrency tạo voice lên quá 1.

## 12. Dừng ứng dụng

Tại mỗi terminal đang chạy server, nhấn `Ctrl+C`.
