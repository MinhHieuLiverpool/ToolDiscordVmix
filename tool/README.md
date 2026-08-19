# 🧰 BỘ CÔNG CỤ QUẢN TRỊ & TIỆN ÍCH HỆ THỐNG (TOOL SUITE)

Thư mục tổng hợp các công cụ chuyên dụng cho máy trạm vMix / Live Broadcast & Media Processing:

---

## 📁 Cấu Trúc Thư Mục

```
d:\ToolDiscordVmix\tool\
├── 🛠️ sys_toolkit/                 # Windows Admin & System Tweaker Pro
│   ├── win_toolkit_gui.py           # Giao diện chính (CPU-Z, Driver, Power, IP Static/DHCP, WinUpdate)
│   ├── toolkit_actions.py           # Backend script PowerShell/CMD/WMI
│   ├── build_toolkit_exe.py         # Script đóng gói EXE kèm quyền Admin (--uac-admin)
│   ├── dist/WinAdminToolkit.exe     # File EXE đã đóng gói sẵn
│   └── README.md                    # Hướng dẫn chi tiết sys_toolkit
│
└── 🎬 extension/                   # Studio Media Toolkit & Converter
    ├── converter_gui.py             # Giao diện tải YouTube 4K & Chuyển đổi Media/Office
    ├── converter.py                 # Backend Engine (yt-dlp, FFmpeg, Deno, docx/pdf, PIL, cv2)
    ├── build_extension_exe.py       # Script đóng gói EXE độc lập
    ├── dist/StudioMediaToolkit.exe  # File EXE đã đóng gói sẵn
    └── requirements.txt             # Thư viện phụ thuộc
```

---

## 🚀 Hướng Dẫn Khởi Chạy Nhanh

### 1. ⚡ Windows Admin & System Tweaker Pro:
```powershell
cd d:\ToolDiscordVmix\tool\sys_toolkit
py win_toolkit_gui.py
```
*(Hoặc chạy trực tiếp file EXE: `tool\sys_toolkit\dist\WinAdminToolkit.exe`)*

### 2. 🎬 Studio Media Toolkit & Converter:
```powershell
cd d:\ToolDiscordVmix\tool\extension
py converter_gui.py
```
*(Hoặc chạy trực tiếp file EXE: `tool\extension\dist\StudioMediaToolkit.exe`)*
