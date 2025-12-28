# 🚀 HƯỚNG DẪN TẠO FILE EXE CHO DỰ ÁN VMIX MONITOR

## 📋 Yêu cầu ban đầu

Chỉ cần có **Python** đã cài đặt trên máy (Python 3.8 trở lên).

## 🔧 CÁCH 1: Sử dụng Script Tự Động (ĐỀ XUẤT)

### Bước 1: Chạy script build
```bash
python build_exe.py
```

### Bước 2: Chọn ứng dụng cần build
Script sẽ hiển thị menu:
```
1. VmixMonitor (GUI chính)
2. ServerLogViewer (GUI xem log)
3. ServerConsole (Console server)
4. Build tất cả
0. Thoát
```

### Bước 3: Lấy file EXE
Sau khi build xong, các file EXE sẽ nằm trong thư mục `dist/`:
- `VmixMonitor.exe` - Ứng dụng chính
- `ServerLogViewer.exe` - Xem log từ server
- `ServerConsole.exe` - Server console

## 🔨 CÁCH 2: Build Thủ Công

### Bước 1: Cài đặt PyInstaller
```bash
pip install pyinstaller
```

### Bước 2: Cài đặt các dependencies
```bash
pip install -r requirements.txt
```

### Bước 3: Build từng ứng dụng

#### Build VmixMonitor (GUI chính):
```bash
pyinstaller --onefile --windowed --name=VmixMonitor --icon=assets/Discord-Logo.ico --add-data="assets/Discord-Logo.ico;assets" --add-data="assets/Discord-Logo.png;assets" --add-data="config.py;." --hidden-import=PIL._tkinter_finder --hidden-import=pystray vmix_monitor_gui.py
```

#### Build ServerLogViewer:
```bash
pyinstaller --onefile --windowed --name=ServerLogViewer --icon=assets/Discord-Logo.ico --add-data="config.py;." server_gui_advanced.py
```

#### Build ServerConsole:
```bash
pyinstaller --onefile --name=ServerConsole --icon=assets/Discord-Logo.ico --add-data="config.py;." server.py
```

## 📦 Kết quả

Sau khi build xong:
- Thư mục `dist/` chứa các file EXE
- Thư mục `build/` chứa các file tạm (có thể xóa)
- File `.spec` chứa cấu hình build (có thể giữ lại để build lại sau)

## ✅ Phân phối cho người dùng

### File cần gửi cho người dùng:
1. File EXE từ thư mục `dist/`
2. File `config.example.py` (đổi tên thành `config.py` và điền thông tin)
3. Thư mục `assets/` (nếu cần thiết)

### Người dùng chỉ cần:
1. **KHÔNG CẦN** cài đặt Python
2. **KHÔNG CẦN** cài đặt các thư viện (pymongo, requests, pillow, pystray)
3. Chỉ cần double-click vào file EXE để chạy!

## 🔍 Kiểm tra kích thước

File EXE sẽ có kích thước khoảng:
- VmixMonitor.exe: ~15-25 MB
- ServerLogViewer.exe: ~10-15 MB
- ServerConsole.exe: ~10-15 MB

## 🐛 Xử lý lỗi thường gặp

### Lỗi: "Failed to execute script"
- Đảm bảo file `config.py` ở cùng thư mục với EXE
- Hoặc sử dụng đường dẫn tuyệt đối trong code

### Lỗi: "ImportError: No module named..."
- Thêm `--hidden-import=<tên_module>` vào lệnh PyInstaller

### Lỗi: Icon không hiển thị
- Kiểm tra đường dẫn đến file .ico
- Đảm bảo file .ico có định dạng đúng

## 📝 Tùy chỉnh nâng cao

### Build với cửa sổ console (để debug):
Bỏ flag `--windowed`:
```bash
pyinstaller --onefile --name=VmixMonitor vmix_monitor_gui.py
```

### Build thành thư mục thay vì 1 file:
Bỏ flag `--onefile`:
```bash
pyinstaller --windowed --name=VmixMonitor vmix_monitor_gui.py
```

### Thêm file dữ liệu:
```bash
--add-data="đường_dẫn_nguồn;đường_dẫn_đích"
```

## 🎯 Lưu ý quan trọng

1. **File EXE chỉ chạy trên Windows**
2. **Kích thước EXE lớn** vì đã gom cả Python runtime
3. **Antivirus có thể cảnh báo** - đây là bình thường với EXE mới build
4. **Thời gian khởi động** có thể chậm hơn chạy bằng Python trực tiếp
5. **Build trên Windows 64-bit** sẽ tạo EXE 64-bit

## 📧 Hỗ trợ

Nếu gặp vấn đề, kiểm tra:
1. Python version: `python --version`
2. PyInstaller version: `pyinstaller --version`
3. Log build trong thư mục `build/`

---

**Chúc bạn build thành công! 🎉**
