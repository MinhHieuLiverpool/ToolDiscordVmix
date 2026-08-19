# 📖 TÀI LIỆU HỆ THỐNG: CƠ CHẾ VÀ ẢNH HƯỞNG CỦA TRẠNG THÁI `statusapp = OFF` (0)

---

## 📌 1. Tổng Quan về `statusapp`

Trong hệ thống **ToolDiscordVmix** (gồm `vmix_monitor_gui` Client, `server.py` Backend và `web` Dashboard), trường `statusapp` là **chỉ số cốt lõi** đại diện cho trạng thái hoạt động của ứng dụng giám sát tại từng máy trạm vMix:

| Giá trị | Trạng thái | Ý nghĩa |
| :--- | :---: | :--- |
| `statusapp = 1` | **ON (Running)** | Ứng dụng Client đang chạy, gửi dữ liệu tài nguyên, thông số vMix và các luồng SRT thời gian thực lên Server. |
| `statusapp = 0` | **OFF (Stopped)** | Ứng dụng Client đã dừng giám sát hoặc máy trạm đã thoát ứng dụng. |

---

## ⚙️ 2. Cơ Chế Chuyển Về Trạng Thái `statusapp = OFF` (0)

Quá trình chuyển trạng thái về `statusapp = 0` được kích hoạt tự động qua 2 tình huống chính tại phía Client (`vmix_monitor_gui`):

### 2.1. Thao tác Chủ động: Bấm nút `⏹️ STOP MONITORING`
Khi người dùng bấm nút **STOP MONITORING** trên giao diện Client:
1. Hàm `toggle_monitoring()` trong `vmix_monitor_gui/logic.py` gán cờ `self.is_running = False`.
2. Giao diện Client lập tức chuyển nút bấm thành `▶️ START MONITORING` (màu xanh lá) và nhãn trạng thái thành `● Stopped`.
3. Một luồng chạy ngầm (`threading.Thread`) được khởi tạo để gọi `stop_and_cleanup()`, kích hoạt hàm `send_app_status(0)`.

### 2.2. Thao tác Thoát Ứng Dụng: Đóng Cửa Sổ (Exit / Close Window)
Khi người dùng đóng cửa sổ hoặc chọn thoát ứng dụng:
1. Sự kiện `on_closing()` trong `vmix_monitor_gui/ui.py` hiển thị hộp thoại xác nhận thoát.
2. Nếu người dùng chọn **Yes (Thoát hoàn toàn)**, ứng dụng gọi `send_app_status(0)` để gửi tín hiệu OFF lên Server trước khi hủy hoàn toàn tiến trình (`sys.exit()`).

### 2.3. Quy Trình Đóng Gói Dữ Liệu của Hàm `send_app_status(0)`
Khi gọi `send_app_status(0)`:
1. **Thu thập danh tính máy**: Lấy tên máy (`hostname`), IP LAN (`ip`) và IP WAN (`ipwan`).
2. **Cập nhật trạng thái SRT**: Toàn bộ các cổng SRT đang cấu hình trên máy trạm đều được gán `status: "OFF"`.
3. **Đóng gói Payload JSON**:
   ```json
   {
     "name": "PC-POV-01",
     "ip": "192.168.1.100",
     "ipwan": "113.161.x.x",
     "statusapp": 0,
     "SRT": [
       {
         "nameSRT": "Main_Feed",
         "port": 5000,
         "quality": "1080p50",
         "status": "OFF",
         "type": "Caller",
         "hostname": "113.161.x.x",
         "stream_id": "live/feed1",
         "title": "Output 1"
       }
     ],
     "stream": []
   }
   ```
4. **Gửi HTTP POST lên Server (`/`)**:
   - Gửi yêu cầu qua `requests.post(url, json=data, timeout=15)`.
   - Cơ chế tự động thử lại tối đa **3 lần** nếu gặp lỗi mạng hoặc Server bận.

---

## ⚡ 3. Khi `statusapp = OFF` (0) Sẽ Ảnh Hưởng và Tác Động Gì?

Khi Server nhận được gói tin với `statusapp = 0`, toàn bộ các thành phần trong hệ sinh thái sẽ xử lý như sau:

```
[ vmix_monitor_gui ]
       │  (statusapp: 0)
       ▼
   [ Server (server.py) ]
       ├─► 1. Gọi _zero_out_metrics_if_offline() ──► Reset CPU, RAM, GPU, Ping, Băng thông về 0
       ├─► 2. Cập nhật In-Memory Cache & MongoDB
       ├─► 3. Loại khỏi tính toán Băng thông WAN IP
       ├─► 4. Ghi Debug Log Local (C:\VmixMonitor\debugger\...)
       └─► 5. WebSocket Broadcast Updates ────────► [ Web Dashboard & Mobile App ]
                                                      ├─► Đèn trạng thái: Chuyển sang OFF (Xám/Đỏ)
                                                      ├─► Trừ 1 vào Tổng máy Online (totalOnline)
                                                      ├─► Tất cả luồng SRT chuyển màu xám OFF
                                                      └─► Card máy hiển thị mờ, biểu đồ về 0
```

---

### 3.1. Tác Động Phía Server Backend (`server.py`)

1. **Tự động làm sạch & Reset chỉ số về 0 (`_zero_out_metrics_if_offline`)**:
   - Để tránh tình trạng máy đã tắt nhưng trên Web vẫn hiển thị số liệu cũ gây hiểu nhầm, Server tự động reset:
     - `cpu = 0`, `ram = 0`, `memory = 0`, `gpu = 0`, `temperature = 0`.
     - `ping = 0`, `ping_isp = 0`, `ping_timeouts = 0`.
     - `sender_mbps = 0`, `receiver_mbps = 0`.
     - `vmixsend = 0`, `vmixreceive = 0`.
     - `PIDVMIX = ""`, `ffmpeg = []`.
   - **Tất cả các cờ hoạt động vMix bị tắt**:
     - `vmix_recording = False`, `vmix_streaming = False`, `vmix_external = False`, `vmix_multicorder = False`, `MultirecordingStatus = False`.
     - `List_REcord = []`, `ListMultiREcord = []`.
   - **Tất cả luồng SRT chuyển trạng thái `status: "OFF"`**.

2. **Loại bỏ khỏi Tổng Băng Thông WAN IP (`_get_ipwan_totals`)**:
   - Máy có `statusapp = 0` không còn được tính vào tổng lưu lượng Sender/Receiver của dải mạng IP WAN đó, đảm bảo biểu đồ phân tích băng thông WAN phản ánh chính xác các máy thực sự đang hoạt động.

3. **Phát sóng WebSocket Thời Gian Thực (`broadcast_updates`)**:
   - Gói dữ liệu làm sạch được gửi ngay lập tức tới tất cả các phiên Web đang kết nối qua WebSocket, giúp giao diện người dùng cập nhật trạng thái trong chưa đầy **1 giây**.

4. **Lưu trữ Dữ liệu & Ghi Log**:
   - Bản ghi máy trạm trong MongoDB (`logs` collection) được cập nhật trạng thái `statusapp: 0`.
   - Ghi chi tiết sự kiện vào file debug hàng ngày: `C:\VmixMonitor\debugger\<YYYY-MM-DD>.txt`.

---

### 3.2. Tác Động Phía Giao Diện Web Dashboard (`web/src/...`)

1. **Thống Kê Tổng Quan (Dashboard & Header)**:
   - Số lượng **`totalOnline`** (Tổng máy Online) giảm đi 1.
   - Badge trạng thái của máy chuyển từ `ON` (xanh lá `pill-on`) sang `OFF` (màu xám hoặc đỏ `pill-off`).
2. **Thẻ Giám Sát Máy Trạm (MachineStatusCard)**:
   - Thẻ máy trạm mờ đi (giảm opacity) để kỹ thuật viên dễ dàng nhận diện máy nào đang nghỉ.
   - Các thanh đo CPU, RAM, GPU, Ping hiển thị mức 0% hoặc gạch ngang `—`.
   - Các nút REC, LIVE, EXT, MultiCorder chuyển sang màu tối/tắt.
3. **Giám Sát Luồng SRT (SRT Monitoring Page)**:
   - Tất cả các dòng SRT thuộc máy trạm này chuyển cột Status sang `OFF`.
4. **Biểu Đồ Băng Thông (BandwidthChartSection)**:
   - Bỏ qua máy này (`if (Number(latest.statusapp) !== 1) return`), không vẽ đường dữ liệu giả.

---

### 3.3. Tác Động Phía Hệ Thống Cảnh Báo (Discord / SeaTalk Webhook)

1. **Thông Báo Trạng Thái SRT**:
   - Nếu có Webhook được cấu hình giám sát luồng SRT của máy trạm đó, Server sẽ gửi tin nhắn cảnh báo luồng đã dừng:
     ```text
     [SRT][PC-POV-01] SRT OFF | IPWAN: 113.161.x.x | PORT: 5000
     ```
2. **Triệt Tiêu Cảnh Báo Lỗi Phần Cứng Giả**:
   - Vì các chỉ số CPU/RAM/Ping đã được đưa về 0 và `statusapp = 0`, hệ thống bot cảnh báo sẽ hiểu đây là hành vi **tắt chủ động**, tránh việc gửi nhầm thông báo "Mất kết nối khẩn cấp" hoặc "Treo máy" cho đội ngũ kỹ thuật.

---

## 📋 4. Bảng Tóm Tắt So Sánh: `statusapp = 1` vs `statusapp = 0`

| Hạng mục | Khi `statusapp = 1` (ON) | Khi `statusapp = 0` (OFF) |
| :--- | :--- | :--- |
| **Nút bấm Client** | `⏹️ STOP MONITORING` (Màu đỏ) | `▶️ START MONITORING` (Màu xanh lá) |
| **Đèn trạng thái Web** | 🟢 **ON** (`pill-on`) | ⚫ **OFF** (`pill-off`) |
| **Bộ đếm `totalOnline`** | Được tính là 1 máy Online | Bị trừ khỏi danh sách Online |
| **Thông số CPU/RAM/GPU/Ping** | Cập nhật realtime theo máy thật | Tự động reset về `0` |
| **Trạng thái REC/LIVE/EXT** | Bật/Tắt theo vMix thực tế | Toàn bộ chuyển về `False` |
| **Trạng thái luồng SRT** | `ON` hoặc `OFF` tùy tín hiệu vMix | Toàn bộ bị cưỡng chế về `OFF` |
| **Băng thông WAN IP** | Được cộng vào tổng tải mạng WAN | Bị loại khỏi phép tính băng thông |
| **Webhook Cảnh báo** | Giám sát & báo động khi có sự cố | Gửi thông báo SRT OFF, ngăn cảnh báo giả |
