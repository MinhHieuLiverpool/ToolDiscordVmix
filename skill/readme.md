# Hướng dẫn & Nhật ký Cập nhật Hệ thống Giám sát vMix SRT

Tài liệu này ghi lại chi tiết các thay đổi cấu trúc, vá lỗi và tối ưu hóa hệ thống vMix Monitor Client & Dashboard Server trong phiên làm việc.

---

## 1. Sửa Lỗi Tên SRT Mặc Định Khi Mở App
* **Vấn đề**: Khi khởi chạy Client, các luồng SRT chưa cấu hình tên tùy chỉnh bị tự động lấy tên kênh vMix (ví dụ: `OutputsExternal1`) làm tên hiển thị thay vì để trống.
* **Khắc phục**:
  * Đổi fallback tìm kiếm tên SRT từ `custom_names.get(title, title)` thành `custom_names.get(title, "")` tại các hàm `send_app_status`, `_update_srt_external_table` và vòng lặp giám sát định kỳ trong [vmix_monitor_gui/logic.py](file:///d:/ToolDiscordVmix/vmix_monitor_gui/logic.py).
  * Cập nhật hàm `_save` chỉnh sửa tên trực tiếp trong [vmix_monitor_gui/ui.py](file:///d:/ToolDiscordVmix/vmix_monitor_gui/ui.py) để cho phép xóa trắng tên (set về `""`) và bọc lệnh cập nhật trong khối `try...except` với check `tree.exists(item)` nhằm ngăn chặn crash lỗi `_tkinter.TclError: Item not found` nếu bảng bị xóa và vẽ lại khi đang gõ tên.

---

## 2. Xử Lý Trạng Thái SRT Khi Rớt Mạng / Timeout
* **Vấn đề**: Khi client bị mất mạng internet hoặc mất kết nối tới server, trạng thái SRT trên Dashboard vẫn hiển thị xanh `ON` do giữ cache cũ, và Client cũng không tự cập nhật trạng thái mất mạng.
* **Khắc phục**:
  * **Phía Client**:
    * Thêm hàm `is_network_offline()` kiểm tra trạng thái mất mạng thông qua bộ đếm ping và giá trị ping.
    * Sửa lỗi trong vòng lặp ping để reset `ping_timeout_count` về `0` ngay khi ping thành công (trước đây bộ đếm bị cộng dồn vô hạn).
    * Ép trạng thái SRT hiển thị trên GUI của Client và đẩy lên Server thành `"OFF"` (màu đỏ) ngay khi mất kết nối mạng.
  * **Phía Server**:
    * Cập nhật task chạy ngầm `check_inactive_machines()` trong [server.py](file:///d:/ToolDiscordVmix/server.py): Khi phát hiện máy client offline (quá 1 phút không gửi dữ liệu), tự động chuyển toàn bộ các luồng SRT của máy đó đang `ON` thành `OFF` trong database/cache và lập tức gửi thông báo Discord báo mất kết nối luồng.
  * **Phía Dashboard**:
    * Cập nhật [server_gui_advanced/ui.py](file:///d:/ToolDiscordVmix/server_gui_advanced/ui.py): Nếu trạng thái máy `statusapp == 0` (Offline), Dashboard sẽ tự động hiển thị tất cả các cổng SRT của máy đó là `OFF` (màu đỏ) trên giao diện để tránh hiển thị thông tin sai lệch từ cache.

---

## 3. Tinh Gọn và Cải Tiến Giao Diện Client
* **Vấn đề**: Khung cấu hình thủ công "Add New Port" chiếm nhiều diện tích và không còn cần thiết, các thông tin Local IP và Server URL nằm rời rạc ngoài Header.
* **Khắc phục**:
  * Ẩn khung **Add New Port** khỏi giao diện (vẫn giữ khai báo ngầm để tránh lỗi logic gọi phần tử).
  * Di chuyển các cấu hình **Local IP**, **WAN IP** mới tích hợp, và **Server URL** cùng nút **Apply** vào trong khung **Monitoring Controls** trên cùng 1 dòng ngang (canh lề phải), giúp giao diện Client cực kỳ tinh gọn và chuyên nghiệp.

---

## 4. Vá Lỗi Độc Quyền File Config vMix Khi Chạy Đa Máy
* **Vấn đề**: Khi cài đặt tool trên một số máy tính khác có cài các công cụ StudioCoast khác (ví dụ `vMixSocial`, `vMixDesktopCapture`), tool đọc sai file `.config` của các công cụ phụ này thay vì file chính của vMix (do các tiện ích này được mở gần nhất).
* **Khắc phục**:
  * Viết lại hàm `_find_latest_studiocoast_config` trong [vmix_monitor_gui/logic.py](file:///d:/ToolDiscordVmix/vmix_monitor_gui/logic.py).
  * Thay vì quét chung tất cả các file `*.config`, hàm mới sử dụng `os.walk` quét chính xác các tệp có tên chuẩn là `user.config` và nằm trong các thư mục của ứng dụng chính: `vMix64.exe_Url_` hoặc `vMix.exe_Url_`.

---

## 5. Khắc Phục Lỗi Crash Khi Đóng Gói EXE Không Có Console
* **Vấn đề**: Sau khi build exe ở chế độ `--noconsole` hoặc `--windowed`, biến hệ thống `sys.stdout` trả về `None`, dẫn đến gọi hàm `sys.stdout.write` trong trình in log bị lỗi `'NoneType' object has no attribute 'write'` và crash app.
* **Khắc phục**:
  * Thêm đoạn kiểm tra `if not sys.stdout: return` tại đầu hàm `safe_print` trong [server_gui_advanced/logic.py](file:///d:/ToolDiscordVmix/server_gui_advanced/logic.py) để bỏ qua việc ghi console khi đóng gói EXE dạng Windowed.
