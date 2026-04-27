import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext

import pystray
import ttkbootstrap as ttk
from PIL import Image, ImageDraw
from ttkbootstrap.constants import *

try:
    from .shared import VIETNAM_TZ
except ImportError:
    try:
        from vmix_monitor_gui.shared import VIETNAM_TZ
    except ImportError:
        from shared import VIETNAM_TZ


class VmixMonitorUIMixin:
    def setup_ui(self):
        win_w, win_h = 1400, 900
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.resizable(True, False)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (win_w // 2)
        y = (self.root.winfo_screenheight() // 2) - (win_h // 2)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=BOTH, expand=YES)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 15))

        ttk.Label(
            header_frame,
            text="🎥 vMix Monitor Pro",
            font=("Segoe UI", 18, "bold"),
            bootstyle="primary",
        ).pack(side=LEFT)

        right_header = ttk.Frame(header_frame)
        right_header.pack(side=RIGHT)

        ip_frame = ttk.Frame(right_header)
        ip_frame.pack(side=TOP, anchor=E)

        ttk.Label(
            ip_frame,
            text="IP Local:",
            font=("Segoe UI", 10, "bold"),
            bootstyle="secondary",
        ).pack(side=LEFT, padx=(0, 5))

        self.ip_entry = ttk.Entry(
            ip_frame,
            textvariable=self.ip_var,
            width=18,
            state="readonly",
            font=("Segoe UI", 10),
            bootstyle="info",
        )
        self.ip_entry.pack(side=LEFT, padx=(0, 5))

        server_frame = ttk.Frame(right_header)
        server_frame.pack(side=TOP, anchor=E, pady=(6, 0))

        ttk.Label(
            server_frame,
            text="Server:",
            font=("Segoe UI", 10, "bold"),
            bootstyle="secondary",
        ).pack(side=LEFT, padx=(0, 5))

        self.server_entry = ttk.Entry(
            server_frame,
            textvariable=self.server_url_var,
            width=28,
            font=("Segoe UI", 10),
            bootstyle="info",
        )
        self.server_entry.pack(side=LEFT, padx=(0, 5))
        self.server_entry.bind("<Return>", lambda _e: self.apply_server_url())

        ttk.Button(
            server_frame,
            text="Áp dụng",
            command=self.apply_server_url,
            bootstyle="info-outline",
            width=9,
        ).pack(side=LEFT)

        add_frame = ttk.Labelframe(
            main_frame,
            text="➕ Thêm Port Mới",
            padding=15,
            bootstyle="primary",
        )
        add_frame.pack(fill=X, pady=(0, 15))

        input_grid = ttk.Frame(add_frame)
        input_grid.pack(fill=X)

        ttk.Label(input_grid, text="Tên máy:", font=("Segoe UI", 10), width=12).grid(
            row=0, column=0, padx=5, pady=5, sticky=E
        )

        self.name_entry = ttk.Entry(
            input_grid,
            textvariable=self.name_var,
            width=30,
            font=("Segoe UI", 10),
        )
        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=EW)

        ttk.Label(input_grid, text="Port:", font=("Segoe UI", 10), width=12).grid(
            row=0, column=2, padx=5, pady=5, sticky=E
        )

        self.port_entry = ttk.Entry(
            input_grid,
            textvariable=self.port_var,
            width=15,
            font=("Segoe UI", 10),
        )
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)

        self.add_btn = ttk.Button(
            input_grid,
            text="➕ Thêm",
            command=self.add_port_entry,
            bootstyle="success",
            width=12,
        )
        self.add_btn.grid(row=0, column=4, padx=10, pady=5)

        input_grid.columnconfigure(1, weight=1)

        table_frame = ttk.Labelframe(
            main_frame,
            text="📋 Danh Sách Port",
            padding=10,
            bootstyle="info",
        )
        table_frame.pack(fill=BOTH, expand=YES, pady=(0, 15))

        table_container = ttk.Frame(table_frame)
        table_container.pack(fill=BOTH, expand=YES)

        style = ttk.Style()
        style.configure("Treeview", font=("Segoe UI", 8), rowheight=22)
        style.configure("Treeview.Heading", font=("Segoe UI", 8, "bold"))

        columns = (
            "name",
            "ip",
            "ipwan",
            "port",
            "ping",
            "timeout",
            "cpu",
            "memory",
            "gpu",
            "sender_bw",
            "receiver_bw",
            "vmixsend",
            "vmixreceive",
            "pid_vmix",
            "rec",
            "live",
            "ext",
            "resolution",
            "srt",
        )
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show="headings",
            height=8,
            bootstyle="info",
        )

        self.tree.heading("name", text="Ten may", anchor=CENTER)
        self.tree.heading("ip", text="IP Local", anchor=CENTER)
        self.tree.heading("ipwan", text="IP WAN", anchor=CENTER)
        self.tree.heading("port", text="Port", anchor=CENTER)
        self.tree.heading("ping", text="Ping", anchor=CENTER)
        self.tree.heading("timeout", text="Timeout", anchor=CENTER)
        self.tree.heading("cpu", text="CPU%", anchor=CENTER)
        self.tree.heading("memory", text="RAM%", anchor=CENTER)
        self.tree.heading("gpu", text="GPU%", anchor=CENTER)
        self.tree.heading("sender_bw", text="Sender", anchor=CENTER)
        self.tree.heading("receiver_bw", text="Receiver", anchor=CENTER)
        self.tree.heading("vmixsend", text="vMix Send", anchor=CENTER)
        self.tree.heading("vmixreceive", text="vMix Receive", anchor=CENTER)
        self.tree.heading("pid_vmix", text="PID vMix", anchor=CENTER)
        self.tree.heading("rec", text="REC", anchor=CENTER)
        self.tree.heading("live", text="LIVE", anchor=CENTER)
        self.tree.heading("ext", text="EXT", anchor=CENTER)
        self.tree.heading("resolution", text="Resolution", anchor=CENTER)
        self.tree.heading("srt", text="SRT Quality", anchor=CENTER)

        self.tree.column("name", width=150, anchor=CENTER)
        self.tree.column("ip", width=110, anchor=CENTER)
        self.tree.column("ipwan", width=110, anchor=CENTER)
        self.tree.column("port", width=70, anchor=CENTER)
        self.tree.column("ping", width=75, anchor=CENTER)
        self.tree.column("timeout", width=85, anchor=CENTER)
        self.tree.column("cpu", width=70, anchor=CENTER)
        self.tree.column("memory", width=70, anchor=CENTER)
        self.tree.column("gpu", width=70, anchor=CENTER)
        self.tree.column("sender_bw", width=110, anchor=CENTER)
        self.tree.column("receiver_bw", width=110, anchor=CENTER)
        self.tree.column("vmixsend", width=110, anchor=CENTER)
        self.tree.column("vmixreceive", width=110, anchor=CENTER)
        self.tree.column("pid_vmix", width=95, anchor=CENTER)
        self.tree.column("rec", width=55, anchor=CENTER)
        self.tree.column("live", width=55, anchor=CENTER)
        self.tree.column("ext", width=55, anchor=CENTER)
        self.tree.column("resolution", width=100, anchor=CENTER)
        self.tree.column("srt", width=220, anchor=CENTER)

        scrollbar = ttk.Scrollbar(
            table_container,
            orient=VERTICAL,
            command=self.tree.yview,
            bootstyle="info-round",
        )
        x_scrollbar = ttk.Scrollbar(
            table_container,
            orient="horizontal",
            command=self.tree.xview,
            bootstyle="info-round",
        )
        self.tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=x_scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        x_scrollbar.pack(side="bottom", fill="x")
        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)

        btn_frame = ttk.Frame(table_frame)
        btn_frame.pack(fill=X, pady=(10, 0))

        self.delete_btn = ttk.Button(
            btn_frame,
            text="🗑️ Xóa mục đã chọn",
            command=self.delete_selected,
            bootstyle="danger",
            width=20,
        )
        self.delete_btn.pack()

        vmix_cfg_frame = ttk.Frame(main_frame)
        vmix_cfg_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(
            vmix_cfg_frame,
            text="vMix HTTP Port:",
            font=("Segoe UI", 9),
            bootstyle="secondary",
        ).pack(side=LEFT, padx=(0, 4))
        ttk.Entry(
            vmix_cfg_frame,
            textvariable=self.vmix_api_port_var,
            width=7,
            font=("Segoe UI", 9),
        ).pack(side=LEFT)
        ttk.Label(
            vmix_cfg_frame,
            text="(mặc định: 8088)",
            font=("Segoe UI", 8),
            bootstyle="secondary",
        ).pack(side=LEFT, padx=(6, 0))
        ttk.Button(
            vmix_cfg_frame,
            text="🔍 Test API",
            command=self.test_vmix_api,
            bootstyle="warning-outline",
            width=10,
        ).pack(side=LEFT, padx=(10, 0))

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=X, pady=(0, 15))

        btn_container = ttk.Frame(control_frame)
        btn_container.pack()

        self.start_btn = ttk.Button(
            btn_container,
            text="▶️ START MONITORING",
            command=self.toggle_monitoring,
            bootstyle="success",
            width=30,
        )
        self.start_btn.pack(side=LEFT, padx=5)

        ttk.Button(
            btn_container,
            text="🔍 Kiểm tra Server",
            command=self.check_server_status,
            bootstyle="info",
            width=20,
        ).pack(side=LEFT, padx=5)

        self.status_label = ttk.Label(
            control_frame,
            text="● Stopped",
            font=("Segoe UI", 10, "bold"),
            bootstyle="secondary",
        )
        self.status_label.pack(pady=(5, 0))

        quality_frame = ttk.Labelframe(
            main_frame,
            text="📡 Stream Quality Snapshot",
            padding=10,
            bootstyle="secondary",
        )
        quality_frame.pack(fill=BOTH, expand=YES, pady=(0, 15))

        q_columns = (
            "stream",
            "runtime",
            "health",
            "vbit",
            "size",
            "abit",
            "level",
            "preset",
            "aformat",
            "channels",
            "keyframe",
            "actual",
            "target",
            "ratio",
            "speed",
            "dropped",
            "file",
        )
        self.stream_quality_tree = ttk.Treeview(
            quality_frame,
            columns=q_columns,
            show="headings",
            height=6,
            bootstyle="secondary",
        )
        for col, label, width in (
            ("stream", "Stream", 90),
            ("runtime", "Runtime", 70),
            ("health", "Health", 70),
            ("vbit", "Video", 90),
            ("size", "Size", 110),
            ("abit", "Audio", 80),
            ("level", "Level", 70),
            ("preset", "Preset", 90),
            ("aformat", "AudioFmt", 80),
            ("channels", "Channels", 80),
            ("keyframe", "Keyframe", 210),
            ("actual", "Actual kbps", 90),
            ("target", "Target kbps", 90),
            ("ratio", "Ratio", 70),
            ("speed", "Speed", 70),
            ("dropped", "Dropped", 80),
            ("file", "LatestFile", 200),
        ):
            self.stream_quality_tree.heading(col, text=label, anchor=CENTER)
            self.stream_quality_tree.column(col, width=width, anchor=CENTER)

        q_scrollbar = ttk.Scrollbar(
            quality_frame,
            orient=VERTICAL,
            command=self.stream_quality_tree.yview,
            bootstyle="info-round",
        )
        q_xscrollbar = ttk.Scrollbar(
            quality_frame,
            orient="horizontal",
            command=self.stream_quality_tree.xview,
            bootstyle="info-round",
        )
        self.stream_quality_tree.configure(yscrollcommand=q_scrollbar.set, xscrollcommand=q_xscrollbar.set)
        q_scrollbar.pack(side=RIGHT, fill=Y)
        q_xscrollbar.pack(side="bottom", fill="x")
        self.stream_quality_tree.pack(side=LEFT, fill=BOTH, expand=YES)

        log_frame = ttk.Labelframe(
            main_frame,
            text="📝 Activity Logs",
            padding=10,
            bootstyle="dark",
        )
        log_frame.pack(fill=BOTH, expand=YES)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=6,
            bg="#1e1e1e",
            fg="#00ff88",
            font=("Consolas", 9),
            state=tk.DISABLED,
            wrap=tk.WORD,
        )
        self.log_text.pack(fill=BOTH, expand=YES)

    def update_stream_quality_table(self, snapshot: dict | None):
        if not hasattr(self, "stream_quality_tree"):
            return
        tree = self.stream_quality_tree
        for item in tree.get_children():
            tree.delete(item)

        if not snapshot:
            tree.insert("", tk.END, values=("(no data)",) + ("-",) * (len(tree["columns"]) - 1))
            return

        streams = snapshot.get("streams", []) if isinstance(snapshot, dict) else []
        if not streams:
            tree.insert("", tk.END, values=("(empty)",) + ("-",) * (len(tree["columns"]) - 1))
            return

        def _sort_key(entry):
            return self._stream_sort_key(entry.get("stream", "")) if hasattr(self, "_stream_sort_key") else entry.get("stream", "")

        for entry in sorted(streams, key=_sort_key):
            cfg = entry.get("config") or {}
            run = entry.get("runtime") or {}
            health = entry.get("health") or {}
            ui_snap = entry.get("ui_snapshot") or {}

            def _health_dot(status: str) -> str:
                s = (status or "").upper()
                if s == "XANH":
                    return "🟢"
                if s == "VANG":
                    return "🟡"
                if s == "DO":
                    return "🔴"
                return "⚪"

            tree.insert(
                "",
                tk.END,
                values=(
                    entry.get("stream", ""),
                    run.get("status", "-"),
                    _health_dot(health.get("status", "")) if health else "-",
                    ui_snap.get("video_bitrate", "-"),
                    ui_snap.get("encode_size", "-"),
                    ui_snap.get("audio_bitrate", "-"),
                    ui_snap.get("level", "-"),
                    ui_snap.get("preset", "-"),
                    ui_snap.get("audio_format", "-"),
                    ui_snap.get("channels", "-"),
                    ui_snap.get("keyframe_frequency", "-"),
                    f"{health.get('actual_bitrate_kbps', 0):.0f}" if health else "-",
                    f"{health.get('target_bitrate_kbps', 0):.0f}" if health else "-",
                    f"{health.get('bitrate_ratio', 0):.2f}" if health else "-",
                    f"{health.get('speed', 0):.2f}" if health else "-",
                    str(health.get("dropped_warnings", "-")) if health else "-",
                    run.get("latest_log_file", "-"),
                ),
            )

    def create_tray_image(self):
        image = Image.new("RGB", (64, 64), color="green")
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill="white")
        return image

    def setup_tray(self):
        if self.tray_icon is not None:
            return
        try:
            image = self.create_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem("Mở", self.show_window),
                pystray.MenuItem("Thoát", self.quit_app),
            )
            self.tray_icon = pystray.Icon("VmixMonitor", image, "Vmix Monitor", menu)
        except Exception as e:
            self.tray_icon = None
            self.log(f"⚠️ Không thể khởi tạo system tray: {e}")

    def hide_to_tray(self):
        self.root.withdraw()
        if self.tray_icon is None:
            self.setup_tray()
        if self.tray_icon and not self.tray_icon.visible:
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def on_closing(self):
        if self.is_running:
            result = messagebox.askyesnocancel(
                "Thoát ứng dụng?",
                "Ứng dụng đang chạy.\n\n"
                "Yes: Thoát hoàn toàn (sẽ gửi statusapp=OFF)\n"
                "No: Ẩn xuống taskbar\n"
                "Cancel: Tiếp tục chạy",
                icon="question",
            )
            if result is True:
                self.quit_app()
            elif result is False:
                self.hide_to_tray()
        else:
            result = messagebox.askyesno(
                "Thoát ứng dụng?",
                "Bạn có muốn thoát hoàn toàn không?\n\n"
                "(Chọn No để ẩn xuống taskbar)",
                icon="question",
            )
            if result:
                self.quit_app()
            else:
                self.hide_to_tray()

    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_app(self, icon=None, item=None):
        if self.is_running:
            import time

            self.is_running = False
            self.send_app_status(0)
            time.sleep(1)

        if self.tray_icon:
            self.tray_icon.stop()

        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def show_import_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("📥 Import từ IP khác")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"400x200+{x}+{y}")

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=BOTH, expand=YES)

        ttk.Label(
            frame,
            text="Nhập IP cũ để import data:",
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=(0, 10))

        old_ip_var = tk.StringVar()
        ip_entry = ttk.Entry(frame, textvariable=old_ip_var, width=30, font=("Segoe UI", 10))
        ip_entry.pack(pady=10)
        ip_entry.focus()

        ttk.Label(
            frame,
            text="Ví dụ: 192.168.1.86",
            font=("Segoe UI", 9),
            bootstyle="secondary",
        ).pack(pady=(0, 15))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        def do_import():
            old_ip = old_ip_var.get().strip()
            if not old_ip:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập IP!")
                return
            dialog.destroy()
            threading.Thread(target=lambda: self.import_from_old_ip(old_ip), daemon=True).start()

        ttk.Button(
            btn_frame,
            text="📥 Import",
            command=do_import,
            bootstyle="success",
            width=15,
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Hủy",
            command=dialog.destroy,
            bootstyle="secondary",
            width=15,
        ).pack(side=LEFT, padx=5)

        ip_entry.bind("<Return>", lambda e: do_import())

    def log(self, message):
        timestamp = datetime.now(VIETNAM_TZ).strftime("[%H:%M:%S]")
        self.log_queue.put(f"{timestamp} {message}")

    def check_log_queue(self):
        import queue

        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_log_queue)

    def update_table_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for entry in self.port_list:
            name = entry["name"]
            ip = entry["ip"]
            ipwan = entry["ipwan"]
            port = entry["port"]
            ping = entry.get("ping", "—")
            timeout = entry.get("timeout", "0")
            cpu = entry.get("cpu", "—")
            memory = entry.get("memory", "—")
            gpu = entry.get("gpu", "—")
            sender_bw = entry.get("sender_bw", "—")
            receiver_bw = entry.get("receiver_bw", "—")
            vmixsend = entry.get("vmixsend", "—")
            vmixreceive = entry.get("vmixreceive", "—")
            pid_vmix = entry.get("pid_vmix", "—")
            rec = entry.get("rec", "—")
            live = entry.get("live", "—")
            ext = entry.get("ext", "—")
            resolution = entry.get("resolution", "—")
            srt = entry.get("srt", "—")
            self.tree.insert(
                "",
                tk.END,
                values=(
                    name,
                    ip,
                    ipwan,
                    port,
                    ping,
                    timeout,
                    cpu,
                    memory,
                    gpu,
                    sender_bw,
                    receiver_bw,
                    vmixsend,
                    vmixreceive,
                    pid_vmix,
                    rec,
                    live,
                    ext,
                    resolution,
                    srt,
                ),
            )
