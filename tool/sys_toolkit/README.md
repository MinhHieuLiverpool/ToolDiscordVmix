# ⚡ Windows Admin & System Tweaker Pro v3.0

Bộ công cụ quản trị, kiểm tra cấu hình phần cứng CPU-Z, cấu hình mạng IP Tĩnh/Động và tối ưu hóa hệ thống Windows chuyên dụng cho máy trạm vMix / Live Broadcast.

---

## 🗂️ Danh Mục & Tính Năng Chi Tiết

### 1. 💻 Quét Cấu Hình Máy (CPU-Z Specs)
- **🧠 Bộ Xử Lý (CPU)**: Tên chip, Số nhân / Số luồng (Cores/Threads), Xung nhịp tối đa (Max Clock Speed), Bộ nhớ đệm L2/L3 Cache, Socket chân cắm.
- **🖥️ Bo Mạch Chủ & BIOS**: Hãng sản xuất (Manufacturer), Model sản phẩm, Serial Number, Phiên bản BIOS và Ngày phát hành.
- **💾 Bộ Nhớ Trong (RAM)**: Tổng dung lượng RAM, Chi tiết từng thanh RAM theo khe cắm (Dung lượng, Bus tốc độ MHz, Hãng SX Samsung/Kingston..., Part Number, Slot Locator).
- **🎮 Card Đồ Họa (GPU)**: Nhận diện cả GPU tích hợp (iGPU) và GPU rời (NVIDIA/AMD), Dung lượng VRAM, Phiên bản Driver, Độ phân giải và Tần số quét màn hình (Hz).
- **💽 Ổ Đĩa Lưu Trữ (Disks)**: Model ổ cứng (NVMe SSD, SATA SSD, HDD), Dung lượng tổng, Chuẩn giao tiếp.
- **🪟 Hệ Điều Hành Windows**: Phiên bản Windows 10/11, Bản build, Kiến trúc 64-bit, Ngày cài đặt hệ điều hành.
- **Tiện ích**: `🔄 Quét Lại Cấu Hình` & `📋 Copy Báo Cáo Cấu Hình`.

---

### 2. 🛠️ Kiểm Tra Driver (Chưa Cài Đặt, Chưa Update, Báo Lỗi)
- **⚠️ Quét Thiết Bị Lỗi / Thiếu Driver (Device Problems)**:
  - Tự động phát hiện các thiết bị có dấu chấm than vàng ⚠️ (Thiếu Driver / Code 28).
  - Phát hiện các thiết bị báo lỗi khởi động (Code 10, Code 43, Code 31, Code 39).
  - Phát hiện các thiết bị đang bị tắt / Vô hiệu hóa (Code 22).
  - Chi tiết từng thiết bị: Tên thiết bị, Loại Class, Hãng SX, Mã lỗi và Nguyên nhân sự cố, Hardware Device ID.
- **🌐 Kiểm Tra Cập Nhật Driver Online**:
  - Kết nối trực tiếp tới Windows Update Catalog để tìm kiếm các driver mới được Microsoft phát hành cho máy tính.
- **📋 Danh Sách Toàn Bộ Driver Phần Cứng Đã Cài**:
  - Phân loại rõ ràng: Display/GPU, Network & Wi-Fi, Audio, Storage/NVMe, Bluetooth, Chipset System, USB...
  - Hiển thị Version, Ngày phát hành, Hãng sản xuất.
- **Tiện ích sửa lỗi nhanh**:
  - `🖥️ Mở Device Manager (devmgmt.msc)`
  - `⚡ Quét Lại Phần Cứng (Rescan Hardware Changes - pnputil)`

---

### 2. 🌐 Quản Lý Mạng & IP Tĩnh / IP Động / DNS
- **Chọn & Đọc Thông Tin Card Mạng**:
  - Dropdown chọn card mạng (`Ethernet`, `Wi-Fi`,...).
  - `🔍 Đọc IP Hiện Tại`: Tự động nạp thông số IP, Subnet Mask, Gateway, DNS đang dùng vào các ô nhập liệu.
  - Hiển thị: Trạng thái kết nối, Địa chỉ MAC, Tốc độ mạng (Link Speed), Chế độ DHCP (Bật/Tắt).
- **🔧 Cấu Hình IP Tĩnh (Static IP)**:
  - 🔤 **IP Address**: Nhập địa chỉ IP tĩnh cần gán.
  - 🔤 **Subnet Mask**: Gợi ý chuẩn `255.255.255.0`.
  - 🔤 **Default Gateway**: Nhập cổng mạng gateway modem/router.
  - 🔤 **Preferred DNS (DNS Chính)** & **Alternate DNS (DNS Phụ)**.
  - **Nút Preset DNS nhanh**: `Google DNS (8.8.8.8 / 8.8.4.4)`, `Cloudflare (1.1.1.1 / 1.0.0.1)`, `OpenDNS`.
  - **`💾 ÁP DỤNG CẤU HÌNH IP TĨNH (APPLY STATIC IP)`**: Gán IP tĩnh ngay lập tức qua `netsh`.
- **⚡ Chuyển Sang IP Động (DHCP)**:
  - `⚡ CHUYỂN SANG IP ĐỘNG & TỰ ĐỘNG DNS`: Tự động nhận IP từ Router.
- **📁 Tắt Chặn Share File Win 11**:
  - `🚀 TẮT CHẶN SHARE FILE WIN 11`: Sửa lỗi mạng SMB Guest & Signature cho Windows 11.

---

### 3. 🔋 Quản Lý Nguồn Điện & Power Plan (Tách Riêng Từng Mục)
- **Chọn Power Scheme**: Liệt kê các plan (`High Performance`, `Balanced`, `Power Saver`) + Nút mở khóa `Ultimate Performance`.
- **Tùy chỉnh chi tiết 2 cột (Cắm sạc AC & Dùng pin DC)**:
  - 🖥️ **Tắt màn hình (Turn off display)**: Never / 1m / 2m / 5m / 10m / 15m / 30m / 1h / 2h / 5h...
  - 🌙 **Chế độ Sleep**: Never / 1m / 2m / 5m / 10m / 15m / 30m / 1h / 2h / 5h...
  - 💾 **Tắt ổ cứng**: Never / 10m / 20m / 30m / 1h / 2h...
  - ⚡ **Chế độ ngủ đông (Hibernate)**: Tắt để giải phóng dung lượng ổ C & tăng tốc máy.
- **Preset & Lưu**:
  - `⚡ Preset vMix (Always ON)` | `🍃 Preset Mặc Định (Balanced)`.
  - **`💾 LƯU & CẬP NHẬT POWER PLAN (SAVE UPDATE)`**.

---

### 4. 🔄 Windows Update & Tiện Ích
- `🔴 TẮT TRIỆT ĐỂ Windows Update` (Khóa Kernel Registry `Start=4`, Task Scheduler & GPO).
- `🟢 BẬT LẠI Windows Update`.
- `🔄 Restart Explorer` & `🔁 Restart PC`.

---

### 5. 🔑 Tài Khoản & Tên Thiết Bị
- Đổi mật khẩu: `📭 Đổi Pass = RỖNG` hoặc `🔐 Đổi Pass Đã Nhập`.
- Đổi tên máy tính: `✏️ Rename Device`.

---

## 🚀 Khởi Chạy

```powershell
cd d:\ToolDiscordVmix\sys_toolkit
py win_toolkit_gui.py
```
*(Đóng gói EXE: `py build_toolkit_exe.py`)*
