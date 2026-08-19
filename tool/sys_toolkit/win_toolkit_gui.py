"""
Windows Admin & System Tweaker Pro v3.5
Giao diện quản trị, tối ưu hệ thống, cấu hình mạng IP Tĩnh/Động, CPU-Z & Quản lý Driver lỗi/thiếu.
"""
import os
import sys
import threading
import time
import socket
import getpass
import json
import tkinter as tk
from tkinter import ttk, messagebox

# Import backend actions
try:
    from toolkit_actions import (
        is_admin,
        request_admin_elevation,
        disable_windows_update,
        enable_windows_update,
        get_local_users,
        change_user_password,
        get_current_device_name,
        rename_device,
        unblock_smb_file_sharing_win11,
        get_active_network_adapters,
        get_adapter_ip_details,
        set_static_ip,
        set_network_dhcp,
        get_power_schemes,
        unlock_ultimate_performance,
        save_power_plan_settings,
        disable_windows_power_sleep,
        restart_windows_explorer,
        restart_computer,
        get_hardware_specs,
        scan_driver_problems_and_status,
        check_driver_updates_online,
        rescan_hardware_devices,
        open_device_manager,
    )
except ImportError:
    try:
        from tool.sys_toolkit.toolkit_actions import *
    except ImportError:
        from sys_toolkit.toolkit_actions import *


# ── Theme Palette ─────────────────────────────────────────────────────────────
THEME = {
    "bg_main": "#0b0d14",
    "bg_sidebar": "#10131d",
    "bg_sidebar_active": "#1e2438",
    "bg_card": "#131722",
    "bg_card_inner": "#0d1019",
    "border": "#23293d",
    "border_light": "#333d59",
    "accent_blue": "#3b82f6",
    "accent_cyan": "#06b6d4",
    "accent_emerald": "#10b981",
    "accent_purple": "#8b5cf6",
    "accent_amber": "#f59e0b",
    "accent_rose": "#f43f5e",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "console_bg": "#06080d",
    "console_fg": "#38bdf8",
    "entry_bg": "#090c15",
}

TIMEOUT_OPTIONS = [
    ("Không bao giờ (Never)", 0),
    ("1 phút", 1),
    ("2 phút", 2),
    ("3 phút", 3),
    ("5 phút", 5),
    ("10 phút", 10),
    ("15 phút", 15),
    ("20 phút", 20),
    ("25 phút", 25),
    ("30 phút", 30),
    ("45 phút", 45),
    ("1 giờ (60 phút)", 60),
    ("2 giờ (120 phút)", 120),
    ("3 giờ (180 phút)", 180),
    ("4 giờ (240 phút)", 240),
    ("5 giờ (300 phút)", 300),
]

DISK_TIMEOUT_OPTIONS = [
    ("Không bao giờ (Never)", 0),
    ("10 phút", 10),
    ("20 phút", 20),
    ("30 phút", 30),
    ("45 phút", 45),
    ("1 giờ (60 phút)", 60),
    ("2 giờ (120 phút)", 120),
]


class WinToolkitApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("⚡ Windows Admin & System Tweaker Pro - Tool Quản Trị Hệ Thống")
        self.root.geometry("1320x900")
        self.root.minsize(1160, 780)
        self.root.configure(bg=THEME["bg_main"])

        # State
        self.is_busy = False
        self.has_admin = is_admin()
        self.active_tab = "cpuz"
        self.sidebar_buttons = {}
        self.tab_frames = {}
        self.power_schemes_data = []
        self.hardware_data = {}
        self.driver_data = {}

        self._init_styles()
        self._build_ui()
        self._load_system_info()

        if self.has_admin:
            self.log_success("🛡️ Khởi động ứng dụng với QUYỀN ADMINISTRATOR thành công.")
        else:
            self.log_warning("⚠️ Cảnh báo: Ứng dụng chưa có quyền Administrator! Vui lòng bấm 'Cấp Quyền Admin' phía trên để chạy đầy đủ các lệnh hệ thống.")

    def _init_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TCombobox",
                        fieldbackground=THEME["entry_bg"],
                        background=THEME["bg_card"],
                        foreground=THEME["text_primary"],
                        bordercolor=THEME["border"],
                        darkcolor=THEME["border"],
                        lightcolor=THEME["border"],
                        arrowcolor=THEME["text_primary"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", THEME["entry_bg"])],
                  selectbackground=[("readonly", THEME["accent_blue"])],
                  selectforeground=[("readonly", "#ffffff")])

        style.configure("Vertical.TScrollbar",
                        background=THEME["border"],
                        troughcolor=THEME["console_bg"],
                        bordercolor=THEME["console_bg"],
                        arrowcolor=THEME["text_secondary"])

    def _build_ui(self):
        # ── Top Header ────────────────────────────────────────────────────────
        header_frame = tk.Frame(self.root, bg=THEME["bg_sidebar"], height=68, bd=0)
        header_frame.pack(fill="x", side="top", padx=0, pady=0)

        h_inner = tk.Frame(header_frame, bg=THEME["bg_sidebar"])
        h_inner.pack(fill="both", expand=True, padx=20, pady=12)

        title_box = tk.Frame(h_inner, bg=THEME["bg_sidebar"])
        title_box.pack(side="left", fill="y")

        lbl_logo = tk.Label(title_box, text="⚡", font=("Segoe UI Emoji", 20), bg=THEME["bg_sidebar"], fg=THEME["accent_cyan"])
        lbl_logo.pack(side="left", padx=(0, 10))

        title_text_box = tk.Frame(title_box, bg=THEME["bg_sidebar"])
        title_text_box.pack(side="left")

        lbl_title = tk.Label(title_text_box, text="WINDOWS ADMIN & SYSTEM TWEAKER PRO", font=("Segoe UI", 13, "bold"), bg=THEME["bg_sidebar"], fg=THEME["text_primary"])
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(title_text_box, text="CPU-Z Specs • Driver Manager • Power Plan • IP Tĩnh / DHCP • Windows Update", font=("Segoe UI", 8), bg=THEME["bg_sidebar"], fg=THEME["text_secondary"])
        lbl_sub.pack(anchor="w")

        # Badges Box
        badges_box = tk.Frame(h_inner, bg=THEME["bg_sidebar"])
        badges_box.pack(side="right", fill="y")

        self.lbl_device_badge = tk.Label(badges_box, text=f"💻 {get_current_device_name()}", font=("Segoe UI", 9, "bold"), bg=THEME["border"], fg=THEME["text_primary"], padx=12, pady=5)
        self.lbl_device_badge.pack(side="left", padx=6)

        admin_text = "🛡️ Admin: YES" if self.has_admin else "⚠️ Cấp Quyền Admin"
        admin_bg = THEME["accent_emerald"] if self.has_admin else THEME["accent_rose"]
        self.btn_admin_badge = tk.Button(
            badges_box,
            text=admin_text,
            font=("Segoe UI", 9, "bold"),
            bg=admin_bg,
            fg="#ffffff",
            activebackground=admin_bg,
            activeforeground="#ffffff",
            bd=0,
            cursor="hand2" if not self.has_admin else "arrow",
            padx=12,
            pady=5,
            command=self._elevate_admin
        )
        self.btn_admin_badge.pack(side="left", padx=6)

        # ── Body: Sidebar Left | Main Center/Right ────────────────────────────
        body_frame = tk.Frame(self.root, bg=THEME["bg_main"])
        body_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Left Sidebar (Categories)
        sidebar = tk.Frame(body_frame, bg=THEME["bg_sidebar"], width=275)
        sidebar.pack(side="left", fill="y", padx=0, pady=0)
        sidebar.pack_propagate(False)

        self._build_sidebar(sidebar)

        # Right Area Split: (Top: Tab Content Panels | Bottom: Live Console Log)
        right_area = tk.Frame(body_frame, bg=THEME["bg_main"])
        right_area.pack(side="right", fill="both", expand=True, padx=14, pady=12)

        # Top Tab Container
        self.tab_container = tk.Frame(right_area, bg=THEME["bg_main"])
        self.tab_container.pack(side="top", fill="both", expand=True)

        # Bottom Live Terminal Panel
        self.console_panel = tk.Frame(right_area, bg=THEME["bg_card"], height=220)
        self.console_panel.pack(side="bottom", fill="x", pady=(12, 0))
        self.console_panel.pack_propagate(False)

        self._build_console_panel(self.console_panel)

        # Build all tab pages
        self._build_tab_cpuz(self.tab_container)
        self._build_tab_driver(self.tab_container)
        self._build_tab_power(self.tab_container)
        self._build_tab_network(self.tab_container)
        self._build_tab_update(self.tab_container)
        self._build_tab_account(self.tab_container)

        # Show initial tab
        self._switch_tab("cpuz")

        # ── Footer Status Bar ────────────────────────────────────────────────
        footer = tk.Frame(self.root, bg=THEME["bg_sidebar"], height=26)
        footer.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(footer, text="🟢 Sẵn sàng thực thi lệnh", font=("Segoe UI", 9), bg=THEME["bg_sidebar"], fg=THEME["accent_emerald"])
        self.lbl_status.pack(side="left", padx=16, pady=3)

        lbl_version = tk.Label(footer, text="v3.5 Pro • Driver & Specs Suite", font=("Segoe UI", 8), bg=THEME["bg_sidebar"], fg=THEME["text_muted"])
        lbl_version.pack(side="right", padx=16, pady=3)

    def _build_sidebar(self, parent):
        lbl_nav = tk.Label(parent, text="DANH MỤC TÍNH NĂNG", font=("Segoe UI", 8, "bold"), bg=THEME["bg_sidebar"], fg=THEME["text_muted"], padx=18, pady=12)
        lbl_nav.pack(anchor="w")

        categories = [
            ("cpuz", "💻  Cấu Hình Máy (CPU-Z)", "CPU, RAM, GPU, Main, SSD"),
            ("driver", "🛠️  Kiểm Tra Driver", "Driver Lỗi, Thiếu & Update"),
            ("power", "🔋  Quản Lý Nguồn Điện", "Power Plan & Tắt Sleep"),
            ("network", "🌐  Mạng & IP Tĩnh / DHCP", "IP Tĩnh, Gateway, DNS, SMB"),
            ("update", "🔄  Windows Update", "Bật / Tắt Update & Tiện ích"),
            ("account", "🔑  Tài Khoản & Tên Máy", "Đổi Pass Rỗng & Rename"),
        ]

        for tab_id, title, desc in categories:
            btn_frame = tk.Frame(parent, bg=THEME["bg_sidebar"], cursor="hand2")
            btn_frame.pack(fill="x", padx=8, pady=3)

            btn = tk.Button(
                btn_frame,
                text=f"{title}\n   {desc}",
                font=("Segoe UI", 9, "bold"),
                bg=THEME["bg_sidebar"],
                fg=THEME["text_primary"],
                activebackground=THEME["bg_sidebar_active"],
                activeforeground="#ffffff",
                bd=0,
                justify="left",
                anchor="w",
                padx=12,
                pady=9,
                cursor="hand2",
                command=lambda t=tab_id: self._switch_tab(t)
            )
            btn.pack(fill="both", expand=True)
            self.sidebar_buttons[tab_id] = btn

    def _switch_tab(self, tab_id):
        self.active_tab = tab_id
        for t_id, btn in self.sidebar_buttons.items():
            if t_id == tab_id:
                btn.configure(bg=THEME["bg_sidebar_active"], fg=THEME["accent_cyan"])
            else:
                btn.configure(bg=THEME["bg_sidebar"], fg=THEME["text_primary"])

        for t_id, frame in self.tab_frames.items():
            if t_id == tab_id:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    # ── TAB 1: Cấu Hình Máy (CPU-Z Specs) ─────────────────────────────────────

    def _build_tab_cpuz(self, parent):
        frame = tk.Frame(parent, bg=THEME["bg_main"])
        self.tab_frames["cpuz"] = frame

        top_bar = tk.Frame(frame, bg=THEME["bg_main"])
        top_bar.pack(fill="x", pady=(0, 10))

        lbl_head = tk.Label(top_bar, text="📊  THÔNG TIN CẤU HÌNH PHẦN CỨNG CHI TIẾT (CPU-Z SPECS)", font=("Segoe UI", 11, "bold"), bg=THEME["bg_main"], fg=THEME["accent_cyan"])
        lbl_head.pack(side="left")

        btn_copy_specs = tk.Button(top_bar, text="📋 Copy Báo Cáo", font=("Segoe UI", 9, "bold"), bg=THEME["border"], fg=THEME["text_primary"], bd=0, cursor="hand2", padx=12, pady=5, command=self._copy_hardware_report)
        btn_copy_specs.pack(side="right", padx=(8, 0))

        btn_refresh_specs = tk.Button(top_bar, text="🔄 Quét Lại Cấu Hình", font=("Segoe UI", 9, "bold"), bg=THEME["accent_blue"], fg="#ffffff", bd=0, cursor="hand2", padx=12, pady=5, command=self._reload_hardware_specs)
        btn_refresh_specs.pack(side="right")

        canvas = tk.Canvas(frame, bg=THEME["bg_main"], bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.cpuz_scroll_content = tk.Frame(canvas, bg=THEME["bg_main"])

        self.cpuz_scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=self.cpuz_scroll_content, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Cards
        self.c_cpu = self._create_card(self.cpuz_scroll_content, "🧠  BỘ VI XỬ LÝ (PROCESSOR / CPU)", THEME["accent_cyan"])
        self.lbl_cpu_info = tk.Label(self.c_cpu, text="⏳ Đang tải dữ liệu CPU...", font=("Consolas", 9), bg=THEME["bg_card"], fg=THEME["text_primary"], justify="left", anchor="w", padx=16, pady=4)
        self.lbl_cpu_info.pack(fill="x", pady=(0, 10))

        self.c_board = self._create_card(self.cpuz_scroll_content, "🖥️  BO MẠCH CHỦ & BIOS (MAINBOARD & BIOS)", THEME["accent_amber"])
        self.lbl_board_info = tk.Label(self.c_board, text="⏳ Đang tải dữ liệu Mainboard...", font=("Consolas", 9), bg=THEME["bg_card"], fg=THEME["text_primary"], justify="left", anchor="w", padx=16, pady=4)
        self.lbl_board_info.pack(fill="x", pady=(0, 10))

        self.c_ram = self._create_card(self.cpuz_scroll_content, "💾  BỘ NHỚ TRONG (MEMORY / RAM)", THEME["accent_emerald"])
        self.lbl_ram_info = tk.Label(self.c_ram, text="⏳ Đang tải dữ liệu RAM...", font=("Consolas", 9), bg=THEME["bg_card"], fg=THEME["text_primary"], justify="left", anchor="w", padx=16, pady=4)
        self.lbl_ram_info.pack(fill="x", pady=(0, 10))

        self.c_gpu = self._create_card(self.cpuz_scroll_content, "🎮  CARD ĐỒ HỌA (GRAPHICS / GPU)", THEME["accent_purple"])
        self.lbl_gpu_info = tk.Label(self.c_gpu, text="⏳ Đang tải dữ liệu GPU...", font=("Consolas", 9), bg=THEME["bg_card"], fg=THEME["text_primary"], justify="left", anchor="w", padx=16, pady=4)
        self.lbl_gpu_info.pack(fill="x", pady=(0, 10))

        self.c_disk = self._create_card(self.cpuz_scroll_content, "💽  Ổ ĐĨA LƯU TRỮ (STORAGE / SSD & HDD)", THEME["accent_rose"])
        self.lbl_disk_info = tk.Label(self.c_disk, text="⏳ Đang tải dữ liệu Ổ cứng...", font=("Consolas", 9), bg=THEME["bg_card"], fg=THEME["text_primary"], justify="left", anchor="w", padx=16, pady=4)
        self.lbl_disk_info.pack(fill="x", pady=(0, 10))

        self.c_os = self._create_card(self.cpuz_scroll_content, "🪟  HỆ ĐIỀU HÀNH (OPERATING SYSTEM / WINDOWS)", THEME["border"])
        self.lbl_os_info = tk.Label(self.c_os, text="⏳ Đang tải dữ liệu Windows...", font=("Consolas", 9), bg=THEME["bg_card"], fg=THEME["text_primary"], justify="left", anchor="w", padx=16, pady=4)
        self.lbl_os_info.pack(fill="x", pady=(0, 10))

    def _reload_hardware_specs(self):
        self.lbl_cpu_info.config(text="⏳ Đang quét dữ liệu CPU...")
        self.lbl_board_info.config(text="⏳ Đang quét dữ liệu Mainboard & BIOS...")
        self.lbl_ram_info.config(text="⏳ Đang quét dữ liệu RAM...")
        self.lbl_gpu_info.config(text="⏳ Đang quét dữ liệu GPU...")
        self.lbl_disk_info.config(text="⏳ Đang quét dữ liệu Ổ cứng...")
        self.lbl_os_info.config(text="⏳ Đang quét dữ liệu Windows...")

        def _w():
            specs = get_hardware_specs()
            self.root.after(0, lambda: self._apply_hardware_specs(specs))
        threading.Thread(target=_w, daemon=True).start()

    def _apply_hardware_specs(self, specs):
        self.hardware_data = specs
        if not specs:
            self.lbl_cpu_info.config(text="❌ Không thể quét dữ liệu cấu hình phần cứng.")
            return

        cpu = specs.get("CPU", {}) or {}
        l2 = f"{round(cpu.get('L2CacheKB', 0)/1024, 1)} MB" if cpu.get('L2CacheKB') else "N/A"
        l3 = f"{round(cpu.get('L3CacheKB', 0)/1024, 1)} MB" if cpu.get('L3CacheKB') else "N/A"
        cpu_text = (
            f"• Tên Bộ Xử Lý (CPU Name) : {cpu.get('Name', 'Unknown')}\n"
            f"• Số Nhân / Luồng (Cores) : {cpu.get('Cores', 'N/A')} Cores / {cpu.get('Threads', 'N/A')} Threads\n"
            f"• Xung Nhịp (Max Speed)   : {cpu.get('MaxClockMHz', 'N/A')} MHz\n"
            f"• Bộ Nhớ Đệm (Cache)      : L2: {l2} | L3: {l3}\n"
            f"• Socket / Chân Cắm       : {cpu.get('Socket', 'N/A')}"
        )
        self.lbl_cpu_info.config(text=cpu_text)

        mb = specs.get("Motherboard", {}) or {}
        bios = specs.get("BIOS", {}) or {}
        board_text = (
            f"• Nhà Sản Xuất (Vendor)   : {mb.get('Manufacturer', 'Unknown')}\n"
            f"• Model / Dòng Máy        : {mb.get('Product', 'Unknown')}\n"
            f"• Serial Number (Bo Mạch) : {mb.get('SerialNumber', 'N/A')}\n"
            f"• Phiên Bản BIOS (Version): {bios.get('SMBIOSBIOSVersion', 'N/A')} ({bios.get('Vendor', '')})\n"
            f"• Ngày Phát Hành BIOS     : {bios.get('ReleaseDate', 'N/A')}"
        )
        self.lbl_board_info.config(text=board_text)

        ram_list = specs.get("RAM", []) or []
        if isinstance(ram_list, dict):
            ram_list = [ram_list]
        total_ram_gb = sum([round(int(r.get('Capacity', 0))/(1024**3), 1) for r in ram_list])
        ram_lines = [f"• Tổng Dung Lượng RAM      : {total_ram_gb:.1f} GB ({len(ram_list)} thanh / Slot cắm)"]
        for i, r in enumerate(ram_list):
            cap_gb = round(int(r.get('Capacity', 0))/(1024**3), 1)
            ram_lines.append(f"  └─ Slot {i+1} [{r.get('DeviceLocator', f'Stick {i+1}')}]: {cap_gb} GB • {r.get('Speed', 'N/A')} MHz • Hãng: {r.get('Manufacturer', 'N/A')} (Part: {r.get('PartNumber', 'N/A')})")
        self.lbl_ram_info.config(text="\n".join(ram_lines))

        gpu_list = specs.get("GPU", []) or []
        if isinstance(gpu_list, dict):
            gpu_list = [gpu_list]
        gpu_lines = []
        for i, g in enumerate(gpu_list):
            vram_mb = round(int(g.get('AdapterRAM', 0))/(1024**2), 0)
            vram_str = f"{round(vram_mb/1024, 1)} GB ({vram_mb:.0f} MB)" if vram_mb > 0 else "Shared VRAM"
            gpu_lines.append(f"• GPU {i+1}: {g.get('Name', 'Unknown')}")
            gpu_lines.append(f"  ├─ Dung Lượng VRAM      : {vram_str}")
            gpu_lines.append(f"  ├─ Phiên Bản Driver     : {g.get('DriverVersion', 'N/A')}")
            gpu_lines.append(f"  └─ Độ Phân Giải / Tần Số: {g.get('VideoModeDescription', 'N/A')} @ {g.get('CurrentRefreshRate', 'N/A')} Hz")
        self.lbl_gpu_info.config(text="\n".join(gpu_lines) if gpu_lines else "• Không nhận diện được Card đồ họa.")

        disk_list = specs.get("Disks", []) or []
        if isinstance(disk_list, dict):
            disk_list = [disk_list]
        disk_lines = []
        for i, d in enumerate(disk_list):
            size_gb = round(int(d.get('Size', 0))/(1024**3), 0)
            disk_lines.append(f"• Ổ Đĩa {i+1}: {d.get('Model', 'Unknown')} ({size_gb:.0f} GB)")
            disk_lines.append(f"  └─ Loại Ổ / Chuẩn Giao Tiếp: {d.get('MediaType', 'Disk')} • Interface: {d.get('InterfaceType', 'N/A')}")
        self.lbl_disk_info.config(text="\n".join(disk_lines) if disk_lines else "• Không nhận diện được Ổ cứng.")

        os_info = specs.get("OS", {}) or {}
        os_text = (
            f"• Phiên Bản Windows       : {os_info.get('Caption', 'Windows')}\n"
            f"• Kiến Trúc (Architecture): {os_info.get('OSArchitecture', '64-bit')}\n"
            f"• Build Number / Version  : Build {os_info.get('BuildNumber', 'N/A')} (Version {os_info.get('Version', 'N/A')})\n"
            f"• Ngày Cài Đặt Windows    : {os_info.get('InstallDate', 'N/A')}"
        )
        self.lbl_os_info.config(text=os_text)

    def _copy_hardware_report(self):
        if not self.hardware_data:
            messagebox.showwarning("Chưa Có Dữ Liệu", "Vui lòng đợi quét cấu hình xong trước khi copy!")
            return
        report = (
            "====================================================\n"
            "         BÁO CÁO CẤU HÌNH MÁY TÍNH (CPU-Z SPECS)     \n"
            "====================================================\n\n"
            f"[BỘ XỬ LÝ / CPU]\n{self.lbl_cpu_info.cget('text')}\n\n"
            f"[BO MẠCH CHỦ & BIOS]\n{self.lbl_board_info.cget('text')}\n\n"
            f"[BỘ NHỚ RAM]\n{self.lbl_ram_info.cget('text')}\n\n"
            f"[CARD ĐỒ HỌA / GPU]\n{self.lbl_gpu_info.cget('text')}\n\n"
            f"[Ổ CỨNG / DISKS]\n{self.lbl_disk_info.cget('text')}\n\n"
            f"[HỆ ĐIỀU HÀNH]\n{self.lbl_os_info.cget('text')}\n\n"
            "===================================================="
        )
        self.root.clipboard_clear()
        self.root.clipboard_append(report)
        messagebox.showinfo("Đã Sao Chép", "Đã copy toàn bộ thông số cấu hình máy tính vào Clipboard!")
        self.log_info("📋 Đã copy toàn bộ Báo cáo Cấu hình vào Clipboard.")

    # ── TAB 2: Quản Lý & Kiểm Tra Driver (Thiếu / Lỗi / Update) ───────────────

    def _build_tab_driver(self, parent):
        frame = tk.Frame(parent, bg=THEME["bg_main"])
        self.tab_frames["driver"] = frame

        # Top Control Bar
        top_bar = tk.Frame(frame, bg=THEME["bg_main"])
        top_bar.pack(fill="x", pady=(0, 10))

        lbl_head = tk.Label(top_bar, text="🛠️  KIỂM TRA DRIVER CHƯA CÀI ĐẶT, CHƯA UPDATE & LỖI", font=("Segoe UI", 11, "bold"), bg=THEME["bg_main"], fg=THEME["accent_amber"])
        lbl_head.pack(side="left")

        btn_devmgmt = tk.Button(top_bar, text="🖥️ Mở Device Manager", font=("Segoe UI", 8), bg=THEME["border"], fg=THEME["text_primary"], bd=0, cursor="hand2", padx=10, pady=5, command=lambda: self._run_async(open_device_manager, "Mở Device Manager"))
        btn_devmgmt.pack(side="right", padx=(6, 0))

        btn_rescan = tk.Button(top_bar, text="⚡ Quét Lại Phần Cứng", font=("Segoe UI", 8), bg=THEME["accent_purple"], fg="#ffffff", bd=0, cursor="hand2", padx=10, pady=5, command=lambda: self._run_async(rescan_hardware_devices, "Quét Lại Thiết Bị Phần Cứng"))
        btn_rescan.pack(side="right", padx=(6, 0))

        btn_check_update = tk.Button(top_bar, text="🌐 Kiểm Tra Update Online", font=("Segoe UI", 8, "bold"), bg=THEME["accent_cyan"], fg="#ffffff", bd=0, cursor="hand2", padx=10, pady=5, command=self._check_driver_updates_gui)
        btn_check_update.pack(side="right", padx=(6, 0))

        btn_scan_drivers = tk.Button(top_bar, text="🔄 Quét Lỗi Driver", font=("Segoe UI", 8, "bold"), bg=THEME["accent_amber"], fg="#ffffff", bd=0, cursor="hand2", padx=12, pady=5, command=self._reload_driver_status)
        btn_scan_drivers.pack(side="right")

        # Scrollable container
        canvas = tk.Canvas(frame, bg=THEME["bg_main"], bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.driver_scroll_content = tk.Frame(canvas, bg=THEME["bg_main"])

        self.driver_scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=self.driver_scroll_content, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Card 1: Thiết Bị Lỗi & Thiếu Driver ──────────────────────────────
        self.c_drv_problems = self._create_card(self.driver_scroll_content, "⚠️  THIẾT BỊ BÁO LỖI, THIẾU DRIVER HOẶC BỊ DISABLE (DEVICE MANAGER PROBLEMS)", THEME["accent_rose"])
        self.lbl_drv_problems = tk.Label(self.c_drv_problems, text="⏳ Đang kiểm tra thiết bị lỗi & thiếu driver...", font=("Consolas", 9), bg=THEME["bg_card"], fg=THEME["accent_rose"], justify="left", anchor="w", padx=16, pady=4)
        self.lbl_drv_problems.pack(fill="x", pady=(0, 10))

        # ── Card 2: Driver Phần Cứng Đã Cài Đặt ──────────────────────────────
        self.c_drv_installed = self._create_card(self.driver_scroll_content, "📋  DANH SÁCH DRIVER PHẦN CỨNG CHÍNH ĐÃ CÀI ĐẶT (INSTALLED DRIVERS)", THEME["accent_emerald"])
        self.lbl_drv_installed = tk.Label(self.c_drv_installed, text="⏳ Đang tải danh sách driver đã cài...", font=("Consolas", 9), bg=THEME["bg_card"], fg=THEME["text_primary"], justify="left", anchor="w", padx=16, pady=4)
        self.lbl_drv_installed.pack(fill="x", pady=(0, 10))

    def _reload_driver_status(self):
        self.lbl_drv_problems.config(text="⏳ Đang quét Device Manager kiểm tra driver lỗi & thiếu...")
        self.lbl_drv_installed.config(text="⏳ Đang quét danh sách driver đã cài...")

        def _w():
            data = scan_driver_problems_and_status()
            self.root.after(0, lambda: self._apply_driver_status(data))
        threading.Thread(target=_w, daemon=True).start()

    def _apply_driver_status(self, data):
        self.driver_data = data
        if not data:
            self.lbl_drv_problems.config(text="❌ Không thể quét dữ liệu Driver.")
            return

        problems = data.get("Problems", []) or []
        if isinstance(problems, dict):
            problems = [problems]

        if not problems:
            self.lbl_drv_problems.config(
                text="🟢 TUYỆT VỜI: Không phát hiện bất kỳ thiết bị nào bị thiếu Driver hoặc báo lỗi trong Device Manager!\n• Tất cả phần cứng đang hoạt động bình thường (Status: OK).",
                fg=THEME["accent_emerald"]
            )
        else:
            lines = [f"⚠️ PHÁT HIỆN {len(problems)} THIẾT BỊ CÓ VẤN ĐỀ / THIẾU DRIVER / BỊ TẮT:\n"]
            for i, p in enumerate(problems):
                code = p.get('ErrorCode', 0)
                meaning = p.get('ErrorMeaning', 'Lỗi không xác định')
                icon = "⚠️" if code == 28 else ("⏸️" if code == 22 else "❌")
                lines.append(f"{icon} Thiết bị {i+1}: {p.get('Name', 'Unknown Device')} [{p.get('Class', 'Unknown Class')}]")
                lines.append(f"   ├─ Chi tiết sự cố : Mã lỗi {code} ──► {meaning}")
                lines.append(f"   ├─ Nhà sản xuất   : {p.get('Manufacturer', 'N/A')}")
                lines.append(f"   └─ Device ID      : {p.get('DeviceID', 'N/A')}\n")
            self.lbl_drv_problems.config(text="\n".join(lines), fg=THEME["accent_rose"])

        installed = data.get("Installed", []) or []
        if isinstance(installed, dict):
            installed = [installed]

        ins_lines = [f"• Tổng số Driver phần cứng chính đã nhận diện: {len(installed)} Drivers\n"]
        by_class = {}
        for drv in installed:
            c = drv.get("Class", "Other")
            if c not in by_class:
                by_class[c] = []
            by_class[c].append(drv)

        class_names = {
            "Display": "🎮 Card Đồ Họa (Display / GPU)",
            "Net": "🌐 Card Mạng (Network & Wi-Fi)",
            "MEDIA": "🔊 Âm Thanh (Sound & Audio)",
            "SCSIAdapter": "💾 Ổ Đĩa & Controller (Storage / NVMe)",
            "Bluetooth": "📶 Bluetooth & Không Dây",
            "System": "🧠 Chipset & Bo Mạch (System)",
            "USB": "🔌 Cổng USB & Hub",
            "Keyboard": "⌨️ Bàn Phím",
            "Mouse": "🖱️ Chuột & Cảm Ứng",
        }

        for c, drv_list in by_class.items():
            header = class_names.get(c, f"📦 Thiết Bị [{c}]")
            ins_lines.append(f"【{header}】")
            for d in drv_list:
                ver = d.get('DriverVersion', 'N/A')
                dt = d.get('DriverDate', 'N/A')
                mfg = d.get('Manufacturer', 'N/A')
                ins_lines.append(f"  └─ {d.get('Name', 'Unknown')} (v{ver} • {dt} • {mfg})")
            ins_lines.append("")

        self.lbl_drv_installed.config(text="\n".join(ins_lines))
        self.log_info(f"🛠️ Đã quét xong Driver: Phát hiện {len(problems)} thiết bị có vấn đề | {len(installed)} driver chính đã cài.")

    def _check_driver_updates_gui(self):
        self._run_async(check_driver_updates_online, "Kiểm Tra Cập Nhật Driver Online")

    # ── TAB 3: Quản Lý Nguồn Điện & Power Plan (Tách Riêng Từng Mục) ───────────

    def _build_tab_power(self, parent):
        frame = tk.Frame(parent, bg=THEME["bg_main"])
        self.tab_frames["power"] = frame

        canvas = tk.Canvas(frame, bg=THEME["bg_main"], bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=THEME["bg_main"])

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Scheme Card
        c_scheme = self._create_card(scroll_content, "⚡  CHỌN POWER PLAN (GÓI HIỆU NĂNG NGUỒN ĐIỆN)", THEME["accent_amber"])

        f_scheme_row = tk.Frame(c_scheme, bg=THEME["bg_card"])
        f_scheme_row.pack(fill="x", padx=16, pady=(0, 10))

        lbl_s = tk.Label(f_scheme_row, text="Power Scheme:", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_s.pack(side="left", padx=(0, 10))

        self.cb_power_schemes = ttk.Combobox(f_scheme_row, state="readonly", width=34)
        self.cb_power_schemes.pack(side="left", padx=(0, 10))

        btn_reload_schemes = tk.Button(f_scheme_row, text="🔄 Quét Plan", font=("Segoe UI", 8), bg=THEME["border"], fg=THEME["text_primary"], bd=0, cursor="hand2", padx=8, pady=3, command=self._reload_power_schemes)
        btn_reload_schemes.pack(side="left", padx=(0, 8))

        btn_unlock_ult = tk.Button(f_scheme_row, text="🚀 Mở Khóa Ultimate Performance", font=("Segoe UI", 8, "bold"), bg=THEME["accent_purple"], fg="#ffffff", bd=0, cursor="hand2", padx=10, pady=3, command=self._handle_unlock_ultimate)
        btn_unlock_ult.pack(side="left")

        # Detail Settings Grid
        c_settings = self._create_card(scroll_content, "🛠️  TÙY CHỈNH CHI TIẾT TỪNG MỤC (CHOOSE & CUSTOMIZE SETTINGS)", THEME["accent_cyan"])

        grid_frame = tk.Frame(c_settings, bg=THEME["bg_card_inner"], bd=1, relief="solid")
        grid_frame.pack(fill="x", padx=16, pady=(0, 12))

        lbl_h_setting = tk.Label(grid_frame, text="Mục Cài Đặt (Setting)", font=("Segoe UI", 9, "bold"), bg=THEME["border"], fg=THEME["text_primary"], pady=6)
        lbl_h_setting.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        lbl_h_ac = tk.Label(grid_frame, text="🔌 Cắm Sạc (Plugged In - AC)", font=("Segoe UI", 9, "bold"), bg=THEME["border"], fg=THEME["accent_cyan"], pady=6)
        lbl_h_ac.grid(row=0, column=1, sticky="nsew", padx=1, pady=1)

        lbl_h_dc = tk.Label(grid_frame, text="🔋 Dùng Pin (On Battery - DC)", font=("Segoe UI", 9, "bold"), bg=THEME["border"], fg=THEME["accent_amber"], pady=6)
        lbl_h_dc.grid(row=0, column=2, sticky="nsew", padx=1, pady=1)

        grid_frame.grid_columnconfigure(0, weight=3)
        grid_frame.grid_columnconfigure(1, weight=3)
        grid_frame.grid_columnconfigure(2, weight=3)

        # Row 1: Turn off display
        lbl_r1 = tk.Label(grid_frame, text="🖥️ Tắt màn hình (Turn off display):", font=("Segoe UI", 9), bg=THEME["bg_card_inner"], fg=THEME["text_primary"], anchor="w", padx=10, pady=8)
        lbl_r1.grid(row=1, column=0, sticky="nsew", padx=1, pady=1)

        self.cb_monitor_ac = ttk.Combobox(grid_frame, state="readonly", values=[label for label, _ in TIMEOUT_OPTIONS])
        self.cb_monitor_ac.grid(row=1, column=1, padx=8, pady=8, sticky="ew")
        self.cb_monitor_ac.current(0)

        self.cb_monitor_dc = ttk.Combobox(grid_frame, state="readonly", values=[label for label, _ in TIMEOUT_OPTIONS])
        self.cb_monitor_dc.grid(row=1, column=2, padx=8, pady=8, sticky="ew")
        self.cb_monitor_dc.current(0)

        # Row 2: Sleep timeout
        lbl_r2 = tk.Label(grid_frame, text="🌙 Đặt máy ở chế độ Sleep (Sleep timeout):", font=("Segoe UI", 9), bg=THEME["bg_card_inner"], fg=THEME["text_primary"], anchor="w", padx=10, pady=8)
        lbl_r2.grid(row=2, column=0, sticky="nsew", padx=1, pady=1)

        self.cb_sleep_ac = ttk.Combobox(grid_frame, state="readonly", values=[label for label, _ in TIMEOUT_OPTIONS])
        self.cb_sleep_ac.grid(row=2, column=1, padx=8, pady=8, sticky="ew")
        self.cb_sleep_ac.current(0)

        self.cb_sleep_dc = ttk.Combobox(grid_frame, state="readonly", values=[label for label, _ in TIMEOUT_OPTIONS])
        self.cb_sleep_dc.grid(row=2, column=2, padx=8, pady=8, sticky="ew")
        self.cb_sleep_dc.current(0)

        # Row 3: Hard disk timeout
        lbl_r3 = tk.Label(grid_frame, text="💾 Tắt ổ cứng sau (Turn off hard disk):", font=("Segoe UI", 9), bg=THEME["bg_card_inner"], fg=THEME["text_primary"], anchor="w", padx=10, pady=8)
        lbl_r3.grid(row=3, column=0, sticky="nsew", padx=1, pady=1)

        self.cb_disk_ac = ttk.Combobox(grid_frame, state="readonly", values=[label for label, _ in DISK_TIMEOUT_OPTIONS])
        self.cb_disk_ac.grid(row=3, column=1, padx=8, pady=8, sticky="ew")
        self.cb_disk_ac.current(0)

        self.cb_disk_dc = ttk.Combobox(grid_frame, state="readonly", values=[label for label, _ in DISK_TIMEOUT_OPTIONS])
        self.cb_disk_dc.grid(row=3, column=2, padx=8, pady=8, sticky="ew")
        self.cb_disk_dc.current(0)

        # Row 4: Hibernate Option
        f_hib_row = tk.Frame(c_settings, bg=THEME["bg_card"])
        f_hib_row.pack(fill="x", padx=16, pady=(4, 10))

        self.var_hibernate = tk.BooleanVar(value=False)
        chk_hib = tk.Checkbutton(
            f_hib_row,
            text="Bật chế độ ngủ đông (Hibernate) - [Khuyên tắt để tối ưu tốc độ vMix & giải phóng dung lượng ổ C]",
            variable=self.var_hibernate,
            font=("Segoe UI", 9),
            bg=THEME["bg_card"],
            fg=THEME["text_primary"],
            selectcolor=THEME["entry_bg"],
            activebackground=THEME["bg_card"],
            activeforeground=THEME["text_primary"]
        )
        chk_hib.pack(side="left")

        # Save Card
        c_actions = self._create_card(scroll_content, "💾  ÁP DỤNG & LƯU CẤU HÌNH (SAVE & UPDATE)", THEME["accent_emerald"])

        f_btn_row = tk.Frame(c_actions, bg=THEME["bg_card"])
        f_btn_row.pack(fill="x", padx=16, pady=(0, 14))

        btn_preset_vmix = self._create_button(
            f_btn_row,
            "⚡  Preset vMix (Always ON - Tối Ưu Tối Đa)",
            THEME["accent_purple"],
            self._apply_preset_vmix
        )
        btn_preset_vmix.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_preset_default = self._create_button(
            f_btn_row,
            "🍃  Preset Mặc Định (Balanced)",
            THEME["border"],
            self._apply_preset_balanced
        )
        btn_preset_default.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_save_power = self._create_button(
            f_btn_row,
            "💾  LƯU & CẬP NHẬT POWER PLAN (SAVE UPDATE)",
            THEME["accent_emerald"],
            self._handle_save_power_settings
        )
        btn_save_power.pack(side="right", fill="x", expand=True, padx=(6, 0))

    # ── TAB 4: Mạng & IP Tĩnh / IP Động (Network & IP Settings) ───────────────

    def _build_tab_network(self, parent):
        frame = tk.Frame(parent, bg=THEME["bg_main"])
        self.tab_frames["network"] = frame

        canvas = tk.Canvas(frame, bg=THEME["bg_main"], bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=THEME["bg_main"])

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Adapter Selector Card
        c_adapter = self._create_card(scroll_content, "🌐  CHỌN CARD MẠNG & THÔNG TIN HIỆN TẠI", THEME["accent_cyan"])

        f_ad_row = tk.Frame(c_adapter, bg=THEME["bg_card"])
        f_ad_row.pack(fill="x", padx=16, pady=(0, 8))

        lbl_ad = tk.Label(f_ad_row, text="Card Mạng:", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_ad.pack(side="left", padx=(0, 8))

        self.cb_adapters = ttk.Combobox(f_ad_row, state="readonly", width=26)
        self.cb_adapters.pack(side="left", padx=(0, 8))
        self.cb_adapters.bind("<<ComboboxSelected>>", lambda e: self._on_adapter_selected())

        btn_reload_adapters = tk.Button(f_ad_row, text="🔄 Quét Card", font=("Segoe UI", 8), bg=THEME["border"], fg=THEME["text_primary"], bd=0, cursor="hand2", padx=8, pady=2, command=self._reload_adapters)
        btn_reload_adapters.pack(side="left", padx=(0, 8))

        btn_fetch_ip = tk.Button(f_ad_row, text="🔍 Đọc IP Hiện Tại", font=("Segoe UI", 8, "bold"), bg=THEME["accent_blue"], fg="#ffffff", bd=0, cursor="hand2", padx=10, pady=2, command=self._fetch_current_ip_to_fields)
        btn_fetch_ip.pack(side="left")

        self.lbl_adapter_status = tk.Label(c_adapter, text="⏳ Đang tải thông tin card mạng...", font=("Consolas", 9), bg=THEME["bg_card_inner"], fg=THEME["accent_cyan"], justify="left", anchor="w", padx=14, pady=8)
        self.lbl_adapter_status.pack(fill="x", padx=16, pady=(0, 10))

        # Static IP Card
        c_static = self._create_card(scroll_content, "🔧  ĐẶT IP TĨNH CHO CARD MẠNG (STATIC IP CONFIGURATION)", THEME["accent_amber"])

        f_inputs = tk.Frame(c_static, bg=THEME["bg_card"])
        f_inputs.pack(fill="x", padx=16, pady=(0, 10))

        lbl_ip = tk.Label(f_inputs, text="Địa chỉ IP (IP Address):", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_ip.grid(row=0, column=0, sticky="w", pady=4, padx=(0, 10))
        self.entry_ip = tk.Entry(f_inputs, font=("Segoe UI", 10), bg=THEME["entry_bg"], fg=THEME["text_primary"], insertbackground="#ffffff", bd=1, relief="solid", width=22)
        self.entry_ip.grid(row=0, column=1, sticky="w", pady=4)
        self.entry_ip.insert(0, "192.168.1.150")

        lbl_mask = tk.Label(f_inputs, text="Subnet Mask:", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_mask.grid(row=0, column=2, sticky="w", pady=4, padx=(20, 10))
        self.entry_mask = tk.Entry(f_inputs, font=("Segoe UI", 10), bg=THEME["entry_bg"], fg=THEME["text_primary"], insertbackground="#ffffff", bd=1, relief="solid", width=22)
        self.entry_mask.grid(row=0, column=3, sticky="w", pady=4)
        self.entry_mask.insert(0, "255.255.255.0")

        lbl_gw = tk.Label(f_inputs, text="Default Gateway:", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_gw.grid(row=1, column=0, sticky="w", pady=4, padx=(0, 10))
        self.entry_gw = tk.Entry(f_inputs, font=("Segoe UI", 10), bg=THEME["entry_bg"], fg=THEME["text_primary"], insertbackground="#ffffff", bd=1, relief="solid", width=22)
        self.entry_gw.grid(row=1, column=1, sticky="w", pady=4)
        self.entry_gw.insert(0, "192.168.1.1")

        lbl_dns1 = tk.Label(f_inputs, text="Preferred DNS (Chính):", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_dns1.grid(row=2, column=0, sticky="w", pady=4, padx=(0, 10))
        self.entry_dns1 = tk.Entry(f_inputs, font=("Segoe UI", 10), bg=THEME["entry_bg"], fg=THEME["text_primary"], insertbackground="#ffffff", bd=1, relief="solid", width=22)
        self.entry_dns1.grid(row=2, column=1, sticky="w", pady=4)
        self.entry_dns1.insert(0, "8.8.8.8")

        lbl_dns2 = tk.Label(f_inputs, text="Alternate DNS (Phụ):", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_dns2.grid(row=2, column=2, sticky="w", pady=4, padx=(20, 10))
        self.entry_dns2 = tk.Entry(f_inputs, font=("Segoe UI", 10), bg=THEME["entry_bg"], fg=THEME["text_primary"], insertbackground="#ffffff", bd=1, relief="solid", width=22)
        self.entry_dns2.grid(row=2, column=3, sticky="w", pady=4)
        self.entry_dns2.insert(0, "8.8.4.4")

        f_dns_presets = tk.Frame(c_static, bg=THEME["bg_card"])
        f_dns_presets.pack(fill="x", padx=16, pady=(0, 10))

        lbl_p_dns = tk.Label(f_dns_presets, text="Gợi ý DNS nhanh:", font=("Segoe UI", 8), bg=THEME["bg_card"], fg=THEME["text_muted"])
        lbl_p_dns.pack(side="left", padx=(0, 8))

        btn_google_dns = tk.Button(f_dns_presets, text="🌐 Google DNS (8.8.8.8)", font=("Segoe UI", 8), bg=THEME["border"], fg=THEME["text_primary"], bd=0, cursor="hand2", padx=8, pady=2, command=lambda: self._set_dns_preset("8.8.8.8", "8.8.4.4"))
        btn_google_dns.pack(side="left", padx=4)

        btn_cf_dns = tk.Button(f_dns_presets, text="🛡️ Cloudflare (1.1.1.1)", font=("Segoe UI", 8), bg=THEME["border"], fg=THEME["text_primary"], bd=0, cursor="hand2", padx=8, pady=2, command=lambda: self._set_dns_preset("1.1.1.1", "1.0.0.1"))
        btn_cf_dns.pack(side="left", padx=4)

        btn_opendns = tk.Button(f_dns_presets, text="⚡ OpenDNS", font=("Segoe UI", 8), bg=THEME["border"], fg=THEME["text_primary"], bd=0, cursor="hand2", padx=8, pady=2, command=lambda: self._set_dns_preset("208.67.222.222", "208.67.220.220"))
        btn_opendns.pack(side="left", padx=4)

        btn_apply_static = self._create_button(
            c_static,
            "💾  ÁP DỤNG CẤU HÌNH IP TĨNH (APPLY STATIC IP)",
            THEME["accent_emerald"],
            self._handle_apply_static_ip
        )
        btn_apply_static.pack(fill="x", padx=16, pady=(0, 14))

        # DHCP Card
        c_dhcp = self._create_card(scroll_content, "⚡  CHUYỂN SANG IP ĐỘNG & TẮT CHẶN SHARE FILE WIN 11", THEME["accent_purple"])

        f_dhcp_box = tk.Frame(c_dhcp, bg=THEME["bg_card"])
        f_dhcp_box.pack(fill="x", padx=16, pady=(0, 14))

        btn_dhcp = self._create_button(
            f_dhcp_box,
            "⚡  CHUYỂN SANG IP ĐỘNG (DHCP) & TỰ ĐỘNG DNS",
            THEME["accent_cyan"],
            self._handle_set_dhcp
        )
        btn_dhcp.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_unblock_smb = self._create_button(
            f_dhcp_box,
            "🚀  TẮT CHẶN SHARE FILE WIN 11 (SMB GUEST)",
            THEME["accent_purple"],
            lambda: self._run_async(unblock_smb_file_sharing_win11, "Tắt Chặn Share File Win 11 (SMB)")
        )
        btn_unblock_smb.pack(side="right", fill="x", expand=True, padx=(6, 0))

    # ── TAB 5: Windows Update & Hệ Thống ──────────────────────────────────────

    def _build_tab_update(self, parent):
        frame = tk.Frame(parent, bg=THEME["bg_main"])
        self.tab_frames["update"] = frame

        c1 = self._create_card(frame, "🔄  Quản Lý Dịch Vụ Windows Update", THEME["accent_cyan"])
        
        lbl_desc = tk.Label(
            c1,
            text="Khóa triệt để cấp Kernel (Start=4: Disabled) cho wuauserv, WaaSMedicSvc, UsoSvc, bits và vô hiệu hóa Task Scheduler.",
            font=("Segoe UI", 9),
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"],
            justify="left"
        )
        lbl_desc.pack(anchor="w", padx=16, pady=(0, 10))

        btn_box = tk.Frame(c1, bg=THEME["bg_card"])
        btn_box.pack(fill="x", padx=16, pady=(0, 14))

        btn_off = self._create_button(btn_box, "🔴  TẮT TRIỆT ĐỂ Windows Update (Khuyên dùng)", THEME["accent_rose"], lambda: self._run_async(disable_windows_update, "Tắt Windows Update"))
        btn_off.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_on = self._create_button(btn_box, "🟢  BẬT LẠI Windows Update", THEME["accent_emerald"], lambda: self._run_async(enable_windows_update, "Bật Windows Update"))
        btn_on.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Utilities
        c2 = self._create_card(frame, "🛠️  Tiện Ích Nhanh Hệ Thống", THEME["border"])

        btn_box2 = tk.Frame(c2, bg=THEME["bg_card"])
        btn_box2.pack(fill="x", padx=16, pady=(0, 14))

        btn_restart_exp = self._create_button(btn_box2, "🔄  Restart Windows Explorer", THEME["border"], lambda: self._run_async(restart_windows_explorer, "Khởi Động Lại Explorer"))
        btn_restart_exp.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_restart_pc = self._create_button(btn_box2, "🔁  Khởi Động Lại Máy (Restart PC)", THEME["accent_rose"], self._handle_restart_pc)
        btn_restart_pc.pack(side="right", fill="x", expand=True, padx=(6, 0))

    # ── TAB 6: Tài Khoản & Tên Thiết Bị ───────────────────────────────────────

    def _build_tab_account(self, parent):
        frame = tk.Frame(parent, bg=THEME["bg_main"])
        self.tab_frames["account"] = frame

        # Password
        c1 = self._create_card(frame, "🔑  Đổi Mật Khẩu Tài Khoản Windows (Pass Rỗng / Pass Mới)", THEME["accent_amber"])

        f_user_row = tk.Frame(c1, bg=THEME["bg_card"])
        f_user_row.pack(fill="x", padx=16, pady=(0, 8))

        lbl_u = tk.Label(f_user_row, text="Tài khoản (User):", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_u.pack(side="left", padx=(0, 8))

        self.cb_users = ttk.Combobox(f_user_row, state="readonly", width=24)
        self.cb_users.pack(side="left", padx=(0, 8))

        btn_reload_users = tk.Button(f_user_row, text="🔄 Quét User", font=("Segoe UI", 8), bg=THEME["border"], fg=THEME["text_primary"], bd=0, cursor="hand2", padx=8, pady=2, command=self._reload_users)
        btn_reload_users.pack(side="left")

        f_pass_row = tk.Frame(c1, bg=THEME["bg_card"])
        f_pass_row.pack(fill="x", padx=16, pady=(0, 10))

        lbl_p = tk.Label(f_pass_row, text="Mật khẩu mới:", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_p.pack(side="left", padx=(0, 20))

        self.entry_password = tk.Entry(f_pass_row, font=("Segoe UI", 10), bg=THEME["entry_bg"], fg=THEME["text_primary"], insertbackground="#ffffff", bd=1, relief="solid")
        self.entry_password.pack(side="left", fill="x", expand=True)

        btn_box = tk.Frame(c1, bg=THEME["bg_card"])
        btn_box.pack(fill="x", padx=16, pady=(0, 14))

        btn_empty_pass = self._create_button(btn_box, "📭  Đổi Pass = RỖNG (Xóa mật khẩu)", THEME["accent_purple"], self._handle_empty_password)
        btn_empty_pass.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_custom_pass = self._create_button(btn_box, "🔐  Đổi Pass Đã Nhập", THEME["accent_blue"], self._handle_custom_password)
        btn_custom_pass.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Rename Device
        c2 = self._create_card(frame, "💻  Rename Device (Đổi Tên Máy Tính)", THEME["accent_blue"])

        f_rename_row = tk.Frame(c2, bg=THEME["bg_card"])
        f_rename_row.pack(fill="x", padx=16, pady=(0, 10))

        lbl_rn = tk.Label(f_rename_row, text="Tên máy tính mới:", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl_rn.pack(side="left", padx=(0, 10))

        self.entry_new_device_name = tk.Entry(f_rename_row, font=("Segoe UI", 10), bg=THEME["entry_bg"], fg=THEME["text_primary"], insertbackground="#ffffff", bd=1, relief="solid")
        self.entry_new_device_name.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_new_device_name.insert(0, f"PC-{get_current_device_name()[:8]}")

        btn_rename = self._create_button(f_rename_row, "✏️  Đổi Tên Máy", THEME["accent_blue"], self._handle_rename_device)
        btn_rename.pack(side="right")

    # ── Console Panel ─────────────────────────────────────────────────────────

    def _build_console_panel(self, parent):
        con_header = tk.Frame(parent, bg=THEME["bg_card"], height=30)
        con_header.pack(fill="x", side="top", padx=12, pady=(6, 4))

        lbl_con_title = tk.Label(con_header, text="💻  TERMINAL & COMMAND LOGS", font=("Segoe UI", 9, "bold"), bg=THEME["bg_card"], fg=THEME["accent_cyan"])
        lbl_con_title.pack(side="left")

        btn_clear = tk.Button(con_header, text="🗑️ Xóa Log", font=("Segoe UI", 8), bg=THEME["border"], fg=THEME["text_secondary"], bd=0, cursor="hand2", padx=8, pady=2, command=self._clear_console)
        btn_clear.pack(side="right", padx=(4, 0))

        btn_copy = tk.Button(con_header, text="📋 Copy Log", font=("Segoe UI", 8), bg=THEME["border"], fg=THEME["text_secondary"], bd=0, cursor="hand2", padx=8, pady=2, command=self._copy_console)
        btn_copy.pack(side="right")

        con_body = tk.Frame(parent, bg=THEME["console_bg"], bd=1, relief="solid")
        con_body.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.txt_console = tk.Text(
            con_body,
            bg=THEME["console_bg"],
            fg=THEME["console_fg"],
            insertbackground="#ffffff",
            font=("Consolas", 9),
            bd=0,
            wrap="word",
            padx=10,
            pady=6
        )
        con_scroll = ttk.Scrollbar(con_body, orient="vertical", command=self.txt_console.yview)
        self.txt_console.configure(yscrollcommand=con_scroll.set)

        self.txt_console.pack(side="left", fill="both", expand=True)
        con_scroll.pack(side="right", fill="y")

        self.txt_console.tag_config("SUCCESS", foreground="#34d399")
        self.txt_console.tag_config("ERROR", foreground="#f87171")
        self.txt_console.tag_config("WARNING", foreground="#fbbf24")
        self.txt_console.tag_config("INFO", foreground="#38bdf8")
        self.txt_console.tag_config("TIME", foreground="#64748b")

    def _create_card(self, parent, title, border_color):
        card = tk.Frame(parent, bg=THEME["bg_card"], bd=1, relief="solid", highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(fill="x", pady=(0, 12))

        title_frame = tk.Frame(card, bg=THEME["bg_card"])
        title_frame.pack(fill="x", padx=16, pady=(10, 8))

        bar = tk.Frame(title_frame, bg=border_color, width=4, height=16)
        bar.pack(side="left", padx=(0, 8))

        lbl = tk.Label(title_frame, text=title, font=("Segoe UI", 10, "bold"), bg=THEME["bg_card"], fg=THEME["text_primary"])
        lbl.pack(side="left")

        return card

    def _create_button(self, parent, text, bg_color, command):
        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 9, "bold"),
            bg=bg_color,
            fg="#ffffff",
            activebackground="#ffffff",
            activeforeground=bg_color,
            bd=0,
            cursor="hand2",
            padx=14,
            pady=8,
            command=command
        )
        return btn

    # ── Console Log Helpers ───────────────────────────────────────────────────

    def log(self, text, tag="INFO"):
        time_str = time.strftime("[%H:%M:%S] ")
        self.txt_console.insert(tk.END, time_str, "TIME")
        self.txt_console.insert(tk.END, f"{text}\n", tag)
        self.txt_console.see(tk.END)

    def log_info(self, text):
        self.log(text, "INFO")

    def log_success(self, text):
        self.log(text, "SUCCESS")

    def log_warning(self, text):
        self.log(text, "WARNING")

    def log_error(self, text):
        self.log(text, "ERROR")

    def _clear_console(self):
        self.txt_console.delete("1.0", tk.END)

    def _copy_console(self):
        content = self.txt_console.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.log_info("📋 Đã copy toàn bộ nội dung Log vào Clipboard.")

    # ── Async Task Runner ─────────────────────────────────────────────────────

    def _run_async(self, func, task_name, *args):
        if self.is_busy:
            messagebox.showwarning("Đang Xử Lý", "Hệ thống đang thực thi một lệnh khác, vui lòng đợi!")
            return

        if not self.has_admin and func not in [restart_windows_explorer, open_device_manager]:
            if messagebox.askyesno(
                "🛡️ Yêu Cầu Quyền Administrator",
                f"Lệnh [{task_name}] yêu cầu quyền Administrator để thay đổi cấu hình hệ thống & Registry.\n\n"
                "Bạn có muốn nâng quyền Admin ngay bây giờ (UAC Prompt)?\n"
                "• Bấm YES: Khởi động lại tool với quyền Admin\n"
                "• Bấm NO: Tiếp tục thử chạy với quyền hiện tại"
            ):
                request_admin_elevation()
                return

        self.is_busy = True
        self.lbl_status.config(text=f"⏳ Đang thực thi: {task_name}...", fg=THEME["accent_amber"])
        self.log_info(f"▶️ Bắt đầu thực thi lệnh: [{task_name}]...")

        def _worker():
            try:
                success, out = func(*args)
                if success:
                    self.root.after(0, lambda: self.log_success(f"[{task_name}] THÀNH CÔNG:\n{out}"))
                    self.root.after(0, lambda: self.lbl_status.config(text=f"✅ {task_name} thành công!", fg=THEME["accent_emerald"]))
                else:
                    self.root.after(0, lambda: self.log_error(f"[{task_name}] THẤT BẠI:\n{out}"))
                    self.root.after(0, lambda: self.lbl_status.config(text=f"❌ {task_name} thất bại!", fg=THEME["accent_rose"]))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: self.log_error(f"[{task_name}] EXCEPTION: {err_msg}"))
                self.root.after(0, lambda: self.lbl_status.config(text=f"❌ Lỗi Exception: {task_name}", fg=THEME["accent_rose"]))
            finally:
                self.is_busy = False

        threading.Thread(target=_worker, daemon=True).start()

    # ── System Info Loaders ───────────────────────────────────────────────────

    def _load_system_info(self):
        self._reload_hardware_specs()
        self._reload_driver_status()
        self._reload_power_schemes()
        self._reload_users()
        self._reload_adapters()

    def _reload_power_schemes(self):
        def _w():
            schemes = get_power_schemes()
            self.root.after(0, lambda: self._apply_power_schemes(schemes))
        threading.Thread(target=_w, daemon=True).start()

    def _apply_power_schemes(self, schemes):
        self.power_schemes_data = schemes
        display_vals = []
        active_idx = 0
        for i, s in enumerate(schemes):
            tag = " ⭐ (Active)" if s.get("is_active") else ""
            display_vals.append(f"{s.get('name', 'Unknown')}{tag}")
            if s.get("is_active"):
                active_idx = i

        self.cb_power_schemes["values"] = display_vals
        if display_vals:
            self.cb_power_schemes.current(active_idx)

    def _reload_users(self):
        def _w():
            users = get_local_users()
            self.root.after(0, lambda: self._apply_users(users))
        threading.Thread(target=_w, daemon=True).start()

    def _apply_users(self, users):
        self.cb_users["values"] = users
        curr = getpass.getuser()
        if curr in users:
            self.cb_users.set(curr)
        elif users:
            self.cb_users.current(0)

    def _reload_adapters(self):
        def _w():
            adapters = get_active_network_adapters()
            self.root.after(0, lambda: self._apply_adapters(adapters))
        threading.Thread(target=_w, daemon=True).start()

    def _apply_adapters(self, adapters):
        vals = ["Tất cả Card Mạng (All)"] + adapters
        self.cb_adapters["values"] = vals
        if len(adapters) > 0:
            self.cb_adapters.set(adapters[0])
        else:
            self.cb_adapters.current(0)
        self._on_adapter_selected()

    def _on_adapter_selected(self):
        ad_name = self.cb_adapters.get().strip()
        if not ad_name or ad_name == "Tất cả Card Mạng (All)":
            self.lbl_adapter_status.config(text="🌐 Đang chọn: Tất cả Card Mạng")
            return
        def _w():
            info = get_adapter_ip_details(ad_name)
            self.root.after(0, lambda: self._apply_adapter_details(info))
        threading.Thread(target=_w, daemon=True).start()

    def _apply_adapter_details(self, info):
        if not info:
            self.lbl_adapter_status.config(text="⚠️ Không đọc được thông tin IP của card mạng này.")
            return
        status_text = (
            f"• Card: {info.get('AdapterName', '')} [{info.get('Status', '')}] | MAC: {info.get('MacAddress', '')} | Tốc độ: {info.get('LinkSpeed', 'N/A')}\n"
            f"• Chế độ: DHCP {info.get('Dhcp', '')} | IP: {info.get('IPAddress', 'Chưa gán')} | Mask: {info.get('SubnetMask', '')} | Gateway: {info.get('Gateway', 'None')} | DNS: {info.get('DNS1', '')} {info.get('DNS2', '')}"
        )
        self.lbl_adapter_status.config(text=status_text)

    def _fetch_current_ip_to_fields(self):
        ad_name = self.cb_adapters.get().strip()
        if not ad_name or ad_name == "Tất cả Card Mạng (All)":
            messagebox.showwarning("Chọn Card Mạng", "Vui lòng chọn một Card Mạng cụ thể (không chọn Tất cả) để đọc IP!")
            return
        def _w():
            info = get_adapter_ip_details(ad_name)
            self.root.after(0, lambda: self._populate_ip_entries(info))
        threading.Thread(target=_w, daemon=True).start()

    def _populate_ip_entries(self, info):
        if not info or not info.get("IPAddress"):
            messagebox.showinfo("Thông Báo", "Card mạng này hiện chưa nhận được địa chỉ IPv4!")
            return
        self.entry_ip.delete(0, tk.END)
        self.entry_ip.insert(0, info.get("IPAddress", ""))

        self.entry_mask.delete(0, tk.END)
        self.entry_mask.insert(0, info.get("SubnetMask", "255.255.255.0"))

        self.entry_gw.delete(0, tk.END)
        self.entry_gw.insert(0, info.get("Gateway", ""))

        self.entry_dns1.delete(0, tk.END)
        self.entry_dns1.insert(0, info.get("DNS1", "8.8.8.8"))

        self.entry_dns2.delete(0, tk.END)
        self.entry_dns2.insert(0, info.get("DNS2", "8.8.4.4"))
        self.log_info(f"🔍 Đã nạp thông tin IP của [{info.get('AdapterName')}] vào các ô nhập liệu.")

    def _set_dns_preset(self, dns1: str, dns2: str):
        self.entry_dns1.delete(0, tk.END)
        self.entry_dns1.insert(0, dns1)
        self.entry_dns2.delete(0, tk.END)
        self.entry_dns2.insert(0, dns2)
        self.log_info(f"🌐 Đã chọn DNS Preset: {dns1} / {dns2}")

    # ── Power Plan Handlers ───────────────────────────────────────────────────

    def _get_selected_scheme_guid(self) -> str:
        idx = self.cb_power_schemes.current()
        if idx >= 0 and idx < len(self.power_schemes_data):
            return self.power_schemes_data[idx]["guid"]
        return ""

    def _map_timeout_label_to_minutes(self, label: str, option_list) -> int:
        for lbl, mins in option_list:
            if lbl == label:
                return mins
        return 0

    def _handle_unlock_ultimate(self):
        self._run_async(unlock_ultimate_performance, "Mở Khóa Ultimate Performance")
        self.root.after(1500, self._reload_power_schemes)

    def _apply_preset_vmix(self):
        self.cb_monitor_ac.current(0)
        self.cb_monitor_dc.current(0)
        self.cb_sleep_ac.current(0)
        self.cb_sleep_dc.current(0)
        self.cb_disk_ac.current(0)
        self.cb_disk_dc.current(0)
        self.var_hibernate.set(False)

        for i, s in enumerate(self.power_schemes_data):
            name_lower = s.get("name", "").lower()
            if "ultimate" in name_lower or "high performance" in name_lower:
                self.cb_power_schemes.current(i)
                break
        self.log_info("⚡ Đã chọn Preset vMix (Always ON - Tối Ưu Tối Đa). Bấm [LƯU & CẬP NHẬT] để áp dụng!")

    def _apply_preset_balanced(self):
        self.cb_monitor_ac.set("10 phút")
        self.cb_monitor_dc.set("5 phút")
        self.cb_sleep_ac.set("30 phút")
        self.cb_sleep_dc.set("15 phút")
        self.cb_disk_ac.set("20 phút")
        self.cb_disk_dc.set("10 phút")
        self.var_hibernate.set(True)

        for i, s in enumerate(self.power_schemes_data):
            if "balanced" in s.get("name", "").lower():
                self.cb_power_schemes.current(i)
                break
        self.log_info("🍃 Đã chọn Preset Mặc Định (Balanced). Bấm [LƯU & CẬP NHẬT] để áp dụng!")

    def _handle_save_power_settings(self):
        guid = self._get_selected_scheme_guid()
        mon_ac = self._map_timeout_label_to_minutes(self.cb_monitor_ac.get(), TIMEOUT_OPTIONS)
        mon_dc = self._map_timeout_label_to_minutes(self.cb_monitor_dc.get(), TIMEOUT_OPTIONS)
        sleep_ac = self._map_timeout_label_to_minutes(self.cb_sleep_ac.get(), TIMEOUT_OPTIONS)
        sleep_dc = self._map_timeout_label_to_minutes(self.cb_sleep_dc.get(), TIMEOUT_OPTIONS)
        disk_ac = self._map_timeout_label_to_minutes(self.cb_disk_ac.get(), DISK_TIMEOUT_OPTIONS)
        disk_dc = self._map_timeout_label_to_minutes(self.cb_disk_dc.get(), DISK_TIMEOUT_OPTIONS)
        hib = self.var_hibernate.get()

        self._run_async(
            save_power_plan_settings,
            "Cập Nhật Cấu Hình Power Plan",
            guid, mon_ac, mon_dc, sleep_ac, sleep_dc, disk_ac, disk_dc, hib
        )
        self.root.after(1500, self._reload_power_schemes)

    # ── Network Action Handlers ───────────────────────────────────────────────

    def _handle_apply_static_ip(self):
        ad = self.cb_adapters.get().strip()
        if not ad or ad == "Tất cả Card Mạng (All)":
            messagebox.showerror("Lỗi", "Vui lòng chọn một Card Mạng cụ thể (không chọn Tất cả) để đặt IP Tĩnh!")
            return
        ip = self.entry_ip.get().strip()
        mask = self.entry_mask.get().strip() or "255.255.255.0"
        gw = self.entry_gw.get().strip()
        dns1 = self.entry_dns1.get().strip()
        dns2 = self.entry_dns2.get().strip()

        if not ip:
            messagebox.showerror("Lỗi", "Địa chỉ IP không được để trống!")
            return

        if messagebox.askyesno("Xác Nhận Đặt IP Tĩnh", f"Cấu hình IP TĨNH cho [{ad}]:\n• IP: {ip}\n• Subnet: {mask}\n• Gateway: {gw}\n• DNS: {dns1} / {dns2}\n\nBạn có chắc chắn muốn áp dụng?"):
            self._run_async(set_static_ip, f"Đặt IP Tĩnh ({ad})", ad, ip, mask, gw, dns1, dns2)
            self.root.after(2000, self._on_adapter_selected)

    def _handle_set_dhcp(self):
        ad = self.cb_adapters.get().strip()
        if messagebox.askyesno("Xác Nhận Cấu Hình DHCP", f"Chuyển [{ad}] sang chế độ IP Động (DHCP) và tự động nhận DNS?"):
            self._run_async(set_network_dhcp, f"Cấu Hình DHCP ({ad})", ad)
            self.root.after(2500, self._on_adapter_selected)

    # ── Other Action Handlers ─────────────────────────────────────────────────

    def _elevate_admin(self):
        if self.has_admin:
            messagebox.showinfo("Admin Privilege", "Ứng dụng đã có đầy đủ quyền Administrator!")
            return
        if messagebox.askyesno("Nâng Quyền Admin", "Bạn có muốn khởi động lại ứng dụng với quyền Administrator (UAC)?"):
            request_admin_elevation()

    def _handle_empty_password(self):
        u = self.cb_users.get().strip()
        if not u:
            messagebox.showerror("Thiếu User", "Vui lòng chọn tài khoản User cần đổi mật khẩu!")
            return
        if messagebox.askyesno("Xác Nhận Đổi Pass Rỗng", f"Bạn có chắc chắn muốn xóa mật khẩu (đổi pass thành RỖNG) cho tài khoản [{u}]?"):
            self._run_async(change_user_password, f"Đổi Pass Rỗng cho User {u}", u, "")

    def _handle_custom_password(self):
        u = self.cb_users.get().strip()
        p = self.entry_password.get().strip()
        if not u:
            messagebox.showerror("Thiếu User", "Vui lòng chọn tài khoản User cần đổi mật khẩu!")
            return
        if not p:
            messagebox.showwarning("Mật Khẩu Trống", "Ô mật khẩu đang để trống. Nếu muốn đổi pass rỗng vui lòng dùng nút 'Đổi Pass = RỖNG'!")
            return
        if messagebox.askyesno("Xác Nhận Đổi Mật Khẩu", f"Bạn có chắc muốn đổi mật khẩu cho tài khoản [{u}] thành:\n[{p}]?"):
            self._run_async(change_user_password, f"Đổi Mật Khẩu User {u}", u, p)

    def _handle_rename_device(self):
        new_n = self.entry_new_device_name.get().strip()
        if not new_n:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên máy tính mới!")
            return
        curr_n = get_current_device_name()
        if messagebox.askyesno("Xác Nhận Đổi Tên Máy", f"Đổi tên máy tính từ [{curr_n}] sang [{new_n}]?\n\n(Lưu ý: Sẽ cần khởi động lại máy để có hiệu lực)"):
            self._run_async(rename_device, f"Đổi Tên Máy Tính Sang {new_n}", new_n)

    def _handle_restart_pc(self):
        if messagebox.askyesno("CẢNH BÁO", "Bạn có chắc chắn muốn KHỞI ĐỘNG LẠI MÁY TÍNH (Restart PC) sau 5 giây?"):
            self._run_async(restart_computer, "Khởi Động Lại Máy Tính")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    tk_root = tk.Tk()
    app = WinToolkitApp(tk_root)
    app.run()
