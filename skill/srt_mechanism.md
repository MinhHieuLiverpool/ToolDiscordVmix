# Cơ chế Lấy Trạng thái SRT (SRT Status Extraction Mechanism)

Tài liệu này giải thích chi tiết cách client `vmix_monitor_gui` tự động dò quét và lấy trạng thái hoạt động của các luồng SRT (SRT External Outputs) trong vMix thông qua file [vmix_monitor_gui/logic.py](file:///d:/ToolDiscordVmix/vmix_monitor_gui/logic.py).

---

## 1. Chu kỳ dò quét chạy ngầm (Auto Scan Loop)
Hàm `auto_scan_srt()` khởi chạy một luồng chạy ngầm (background thread) chạy song song với ứng dụng:
- Thực hiện quét định kỳ mỗi **3 giây**.
- Gọi hàm `_parse_srt_external_outputs()` để phân tích cấu hình SRT hiện tại.
- Cập nhật kết quả lên giao diện bảng GUI (`srt_ext_tree`) thông qua hàm `_update_srt_external_table()`.
- Lưu trữ danh sách SRT mới nhất vào biến `self._srt_ext_latest_data` để gửi dữ liệu telemetry lên Dashboard Server qua HTTP POST.

---

## 2. Các bước xác định trạng thái SRT

### Bước 2.1: Kiểm tra tiến trình vMix (Process Verification)
Sử dụng thư viện `psutil` (được cache trong 10 giây để tối ưu hiệu năng) để kiểm tra xem tiến trình `vmix64.exe` hoặc `vmix.exe` có đang chạy trên máy hay không:
- **Nếu vMix KHÔNG chạy**: Ép toàn bộ trạng thái SRT (`srt_enabled`) về `0` (`OFF`), kể cả khi cấu hình file trước đó ghi nhận là ON.
- **Nếu vMix ĐANG chạy**: Giữ nguyên trạng thái cấu hình thực tế được phân tích từ các nguồn bên dưới.

### Bước 2.2: Tìm kiếm và Phân tích Cấu hình (Sources Priority)
Để lấy được danh sách cấu hình SRT External Outputs (gồm 4 kênh: `OutputsExternal`, `OutputsExternal2`, `OutputsExternal3`, `OutputsExternal4`), hệ thống sẽ quét các nguồn theo thứ tự ưu tiên từ cao xuống thấp:

1. **Nguồn 0: Đường dẫn cấu hình thủ công (Manual Configuration Override)**
   - Nếu người dùng chọn thủ công một file cấu hình `.vmix` hoặc `.config` qua giao diện (biến `_manual_config_path`), hệ thống sẽ ưu tiên đọc trực tiếp từ file này.

2. **Nguồn 1: File cấu hình người dùng của StudioCoast (StudioCoast user.config)**
   - Đây là **nguồn tự động có độ ưu tiên cao nhất**. Hệ thống tìm kiếm tệp cấu hình lưu trữ gần nhất của vMix (`user.config`) nằm trong thư mục `%LOCALAPPDATA%\StudioCoast_Pty_Ltd\` bằng cách quét qua tất cả các thư mục profile User trên máy (đảm bảo tìm thấy file cấu hình kể cả khi vMix chạy bằng quyền Administrator hoặc một tài khoản User khác).
   - Nếu không tìm thấy, hệ thống sẽ sử dụng file backup dự phòng: `settingbackups\current.config` nằm trong thư mục dữ liệu vMix.
   - Định dạng file là XML, dữ liệu SRT của các luồng external được mã hóa HTML và lưu trong các thẻ `<value>` có thuộc tính `name="OutputsExternal"`, `OutputsExternal2`, v.v.

3. **Nguồn 2: Đọc từ vMix Web API**
   - Nếu không lấy được từ các nguồn trên, hệ thống sẽ thực hiện truy vấn HTTP GET tới local API của vMix tại địa chỉ `http://127.0.0.1:8088/api` (port được lấy từ cấu hình client).
   - API trả về XML chứa đường dẫn Preset (`.vmix`) hiện tại đang mở trong vMix. Hệ thống sẽ đọc và parse XML preset này.

4. **Nguồn 3: Đọc Preset từ tham số dòng lệnh của vMix (Command Line)**
   - Hệ thống dùng `psutil` duyệt danh sách tiến trình, lấy tham số dòng lệnh (`cmdline`) của `vmix64.exe`/`vmix.exe` để trích xuất file `.vmix` đang được vMix mở trực tiếp, rồi thực hiện parse XML.

5. **Nguồn 4: Quét toàn bộ thư mục mặc định (Glob Fallback)**
   - Quét tìm tất cả các file đuôi `.vmix` trong các thư mục `AppData\vMix`, `Documents\vMix`, `Desktop`, `Documents` và chọn file có thời gian chỉnh sửa mới nhất để parse.

---

## 3. Trích xuất thông số kỹ thuật chi tiết
Sau khi parse XML từ Preset hoặc Config, hệ thống trích xuất các thẻ XML con của mỗi block `OutputsExternal` để lấy thông tin:
- `SRTEnabled`: Trạng thái bật/tắt của luồng (`1` -> `ON`, `0` -> `OFF`).
- `SRTType`: Chế độ hoạt động của SRT (`0` -> `Caller`, `1` -> `Listener`).
- `SRTHostname`: Địa chỉ IP/Domain đích.
- `SRTPort`: Cổng UDP kết nối luồng.
- `SRTStreamID`: Stream ID cấu hình SRT.
- `SRTVideoCodec` & `SRTVideoBandwidth` & `SRTAudioBandwidth`: Video codec (`1` -> `HEVC`, `0`/khác -> `H264`), bitrate video, bitrate audio.
- `SRTHardwareEncoder`: Có sử dụng tăng tốc phần cứng hay không (`1` -> `HW`).

Từ đó, hệ thống sinh ra chuỗi thông tin chất lượng hiển thị (`quality`) có dạng: 
> **`{Codec} {VideoBandwidth} Mbps AAC {AudioBandwidth} Kbps [HW]`** (ví dụ: `HEVC 6000 Kbps AAC 128 Kbps HW`).
