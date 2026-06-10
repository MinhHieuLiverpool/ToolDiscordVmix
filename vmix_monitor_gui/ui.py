import re
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
    @staticmethod
    def _format_stream_bitrate(raw_value: object) -> str:
        text = str(raw_value or "").strip()
        if not text:
            return "-"

        normalized = "".join(text.split()).lower()
        m = re.match(r"^([\d.]+)([a-z]+)?$", normalized)
        if not m:
            return text

        try:
            value = float(m.group(1))
        except ValueError:
            return text

        unit = m.group(2) or ""
        if unit in {"kbps", "k"}:
            return f"{value / 1000:.2f} Mbps" if value >= 1000 else f"{value:.0f} kbps"
        if unit in {"mbps", "m"}:
            return f"{value:.2f} Mbps"
        if unit == "bps":
            return f"{(value / 1_000_000):.2f} Mbps"

        return f"{value / 1000:.2f} Mbps" if value >= 1000 else f"{value:.0f} kbps"

    def setup_ui(self):
        win_w, win_h = 1450, 920
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.resizable(True, True)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (win_w // 2)
        y = (self.root.winfo_screenheight() // 2) - (win_h // 2)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        style = ttk.Style()
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("warning.Treeview", font=("Segoe UI", 10), rowheight=26)
        style.configure("secondary.Treeview", font=("Segoe UI", 10), rowheight=26)
        style.configure("Header.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Metric.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("MetricTitle.TLabel", font=("Segoe UI", 9), foreground="#cccccc")

        # -- Main Scrollable Canvas --
        canvas = tk.Canvas(self.root, highlightthickness=0, bg="#1a1a1a")
        main_scroll = ttk.Scrollbar(self.root, orient=VERTICAL, command=canvas.yview, bootstyle="secondary-round")
        canvas.configure(yscrollcommand=main_scroll.set)
        main_scroll.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=YES)

        main_container = ttk.Frame(canvas, padding=20)
        main_container_id = canvas.create_window((0, 0), window=main_container, anchor=NW)

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(main_container_id, width=canvas.winfo_width())

        main_container.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_configure)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # ========== HEADER SECTION ==========
        header_card = ttk.Frame(main_container, padding=10)
        header_card.pack(fill=X, pady=(0, 20))

        title_frame = ttk.Frame(header_card)
        title_frame.pack(side=LEFT)
        ttk.Label(title_frame, text="🎥", font=("Segoe UI", 24)).pack(side=LEFT, padx=(0, 10))
        ttk.Label(title_frame, text="vMix Monitor", font=("Segoe UI", 20, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Label(title_frame, text="PRO", font=("Segoe UI", 10, "bold"), bootstyle="inverse-primary", padding=(4, 2)).pack(side=LEFT, padx=8, pady=(8, 0))



        # ========== QUICK ACTIONS & STATUS ==========
        action_row = ttk.Frame(main_container)
        action_row.pack(fill=X, pady=(0, 20))

        # LEFT: Add Port Card (Created but not packed to hide from UI while keeping code references valid)
        add_card = ttk.Labelframe(action_row, text=" ➕ Add New Port ", padding=15, bootstyle="primary")
        # add_card.pack(side=LEFT, fill=Y, expand=YES, padx=(0, 10))

        ttk.Label(add_card, text="Machine Name:").grid(row=0, column=0, sticky=W, padx=5)
        self.name_entry = ttk.Entry(add_card, textvariable=self.name_var, width=25)
        self.name_entry.grid(row=1, column=0, padx=5, pady=(2, 0), sticky=EW)

        ttk.Label(add_card, text="Port:").grid(row=0, column=1, sticky=W, padx=5)
        self.port_entry = ttk.Entry(add_card, textvariable=self.port_var, width=12)
        self.port_entry.grid(row=1, column=1, padx=5, pady=(2, 0), sticky=EW)

        self.add_btn = ttk.Button(add_card, text="Add Port", command=self.add_port_entry, bootstyle="success", width=12)
        self.add_btn.grid(row=1, column=2, padx=5, pady=(2, 0))

        self.scan_status_label = ttk.Label(add_card, text="🔄 SRT Auto Scan", font=("Segoe UI", 9), bootstyle="info")
        self.scan_status_label.grid(row=1, column=3, padx=(0, 10), pady=(2, 0))

        add_card.columnconfigure(0, weight=2)
        add_card.columnconfigure(1, weight=1)

        # RIGHT: Control Card (Expanded to take full horizontal width)
        ctrl_card = ttk.Labelframe(action_row, text=" ⚙️ Monitoring Controls ", padding=15, bootstyle="info")
        ctrl_card.pack(fill=X, expand=YES)

        v_cfg = ttk.Frame(ctrl_card)
        v_cfg.pack(fill=X, pady=(0, 10))

        # Left side: vMix Port configuration
        ttk.Label(v_cfg, text="vMix Port:").pack(side=LEFT)
        self.vmix_entry = ttk.Entry(v_cfg, textvariable=self.vmix_api_port_var, width=8, justify=CENTER)
        self.vmix_entry.pack(side=LEFT, padx=5)
        ttk.Button(v_cfg, text="Test API", command=self.test_vmix_api, bootstyle="warning-outline", width=10).pack(side=LEFT, padx=5)

        # Right side: Local IP & Server URL Configuration (packed right-to-left)
        ttk.Button(v_cfg, text="Apply", command=self.apply_server_url, bootstyle="info-outline", width=8).pack(side=RIGHT, padx=(5, 0))
        self.server_entry = ttk.Entry(v_cfg, textvariable=self.server_url_var, width=30, font=("Segoe UI", 10), bootstyle="info")
        self.server_entry.pack(side=RIGHT, padx=(0, 5))
        self.server_entry.bind("<Return>", lambda _e: self.apply_server_url())
        ttk.Label(v_cfg, text="Server URL:", font=("Segoe UI", 9, "bold"), bootstyle="secondary").pack(side=RIGHT, padx=(15, 5))

        self.wan_ip_entry = ttk.Entry(v_cfg, textvariable=self.wan_ip_var, width=15, state="readonly", font=("Consolas", 10), bootstyle="dark", justify=CENTER)
        self.wan_ip_entry.pack(side=RIGHT, padx=(0, 5))
        ttk.Label(v_cfg, text="WAN IP:", font=("Segoe UI", 9, "bold"), bootstyle="secondary").pack(side=RIGHT, padx=(15, 5))

        self.ip_entry = ttk.Entry(v_cfg, textvariable=self.ip_var, width=15, state="readonly", font=("Consolas", 10), bootstyle="dark", justify=CENTER)
        self.ip_entry.pack(side=RIGHT, padx=(0, 5))
        ttk.Label(v_cfg, text="Local IP:", font=("Segoe UI", 9, "bold"), bootstyle="secondary").pack(side=RIGHT, padx=(10, 5))

        btn_box = ttk.Frame(ctrl_card)
        btn_box.pack(fill=X)
        self.start_btn = ttk.Button(btn_box, text="▶ START MONITORING", command=self.toggle_monitoring, bootstyle="success", width=22)
        self.start_btn.pack(side=LEFT, padx=(0, 5))
        ttk.Button(btn_box, text="Check Server", command=self.check_server_status, bootstyle="info", width=15).pack(side=LEFT)

        self.status_label = ttk.Label(ctrl_card, text="● Stopped", font=("Segoe UI", 10, "bold"), bootstyle="secondary")
        self.status_label.pack(side=BOTTOM, pady=(10, 0))

        # ========== METRICS DASHBOARD ==========
        metrics_frame = ttk.Labelframe(main_container, text=" 📊 System Performance ", padding=15, bootstyle="secondary")
        metrics_frame.pack(fill=X, pady=(0, 20))

        self._machine_labels = {}
        metrics_data = [
            ("Ping", "ping", "⏱️", "warning"),
            ("Timeout", "timeout", "⚠️", "danger"),
            ("CPU Load", "cpu", "🖥️", "info"),
            ("RAM Usage", "memory", "💾", "info"),
            ("GPU Load", "gpu", "🎮", "success"),
            ("MAC Address", "mac_address", "🆔", "secondary"),
            ("Net Speed", "network_speed", "⚡", "primary"),
            ("Network UP", "sender_bw", "📤", "primary"),
            ("Network DL", "receiver_bw", "📥", "primary"),
            ("vMix PID", "pid_vmix", "🔧", "secondary"),
            ("Recording", "rec", "🔴", "danger"),
            ("Streaming", "live", "📡", "danger"),
            ("External", "ext", "🟢", "success"),
            ("Resolution", "resolution", "📐", "secondary"),
        ]

        m_cols = 7
        for idx, (label, key, icon, bstyle) in enumerate(metrics_data):
            r, c = divmod(idx, m_cols)
            m_card = ttk.Frame(metrics_frame, padding=5)
            m_card.grid(row=r, column=c, padx=10, pady=8, sticky=NSEW)
            
            ttk.Label(m_card, text=f"{icon} {label}", style="MetricTitle.TLabel").pack(anchor=W)
            val_lbl = ttk.Label(m_card, text="—", style="Metric.TLabel", bootstyle=bstyle)
            val_lbl.pack(anchor=W)
            self._machine_labels[key] = val_lbl

        for c in range(m_cols):
            metrics_frame.columnconfigure(c, weight=1)

        # Hidden tree for backward compatibility (used by port_list management in logic.py)
        self.tree = ttk.Treeview(main_container, columns=("name", "port", "quality", "status"), show="headings", height=0)
        self.delete_btn = ttk.Button(main_container)
        # Not packed — invisible

        # ========== SRT EXTERNAL OUTPUTS (AUTO-SCAN) ==========
        srt_ext_wrap = ttk.Labelframe(main_container, text=" 🔌 SRT External Outputs (Auto-Scan) ", padding=10, bootstyle="warning")
        srt_ext_wrap.pack(fill=X, pady=(0, 20))

        srt_ext_cols = ("name", "title", "srt_enabled", "port", "type", "hostname", "stream_id", "quality")
        self.srt_ext_tree = ttk.Treeview(srt_ext_wrap, columns=srt_ext_cols, show="headings", height=5, bootstyle="warning")
        for col, label, width in (
            ("name", "Name", 140),
            ("title", "Title", 150),
            ("srt_enabled", "SRT Enabled", 100),
            ("port", "Port", 80),
            ("type", "Type", 120),
            ("hostname", "Hostname", 160),
            ("stream_id", "StreamID", 200),
            ("quality", "Quality", 200),
        ):
            self.srt_ext_tree.heading(col, text=label)
            self.srt_ext_tree.column(col, width=width, anchor=CENTER)

        srt_ext_sb = ttk.Scrollbar(srt_ext_wrap, orient=VERTICAL, command=self.srt_ext_tree.yview, bootstyle="warning-round")
        self.srt_ext_tree.configure(yscrollcommand=srt_ext_sb.set)
        srt_ext_sb.pack(side=RIGHT, fill=Y)
        self.srt_ext_tree.pack(side=LEFT, fill=BOTH, expand=YES)

        # Double-click on Name column to edit
        self.srt_ext_tree.bind("<Double-1>", self._on_srt_ext_name_dblclick)
        self._srt_ext_custom_names: dict[str, str] = {}  # title -> custom name

        # Placeholder row
        self.srt_ext_tree.insert("", tk.END, values=("⏳ Đang scan...",) + ("—",) * 7)

        # ========== STREAM QUALITY SNAPSHOT ==========
        quality_wrap = ttk.Labelframe(main_container, text=" 📋 Stream Quality Health ", padding=10, bootstyle="secondary")
        quality_wrap.pack(fill=X, pady=(0, 20))

        q_cols = ("stream", "runtime", "health", "vbit", "size", "abit", "level", "preset", "aformat", "channels", "keyframe", "actual", "target", "ratio", "speed", "dropped", "file")
        self.stream_quality_tree = ttk.Treeview(quality_wrap, columns=q_cols, show="headings", height=8, bootstyle="secondary")
        for col, label, width in (
            ("stream", "Stream", 100), ("runtime", "Runtime", 80), ("health", "Health", 70),
            ("vbit", "Video", 100), ("size", "Size", 120), ("abit", "Audio", 90),
            ("level", "Level", 80), ("preset", "Preset", 100), ("aformat", "AudioFmt", 90),
            ("channels", "Ch", 60), ("keyframe", "Keyframe", 180), ("actual", "Act kbps", 90),
            ("target", "Tgt kbps", 90), ("ratio", "Ratio", 70), ("speed", "Speed", 70),
            ("dropped", "Drops", 80), ("file", "Log File", 250),
        ):
            self.stream_quality_tree.heading(col, text=label)
            self.stream_quality_tree.column(col, width=width, anchor=CENTER)

        q_sb_v = ttk.Scrollbar(quality_wrap, orient=VERTICAL, command=self.stream_quality_tree.yview, bootstyle="secondary-round")
        q_sb_h = ttk.Scrollbar(quality_wrap, orient=HORIZONTAL, command=self.stream_quality_tree.xview, bootstyle="secondary-round")
        self.stream_quality_tree.configure(yscrollcommand=q_sb_v.set, xscrollcommand=q_sb_h.set)
        q_sb_v.pack(side=RIGHT, fill=Y)
        q_sb_h.pack(side=BOTTOM, fill=X)
        self.stream_quality_tree.pack(side=LEFT, fill=BOTH, expand=YES)
        
        self.stream_quality_tree.bind("<<TreeviewSelect>>", self.on_stream_selected)

        # ========== STREAM URL & KEY SCANNER PANEL ==========
        self.stream_url_key_frame = ttk.Labelframe(
            main_container,
            text=" 🔗 Stream URL & Key (Auto-Scan) ",
            padding=15,
            bootstyle="info",
        )
        self.stream_url_key_frame.pack(fill=X, pady=(0, 20))

        # Header row
        hdr = ttk.Frame(self.stream_url_key_frame)
        hdr.pack(fill=X, pady=(0, 6))
        ttk.Label(hdr, text="Stream",    width=14, font=("Segoe UI", 9, "bold"), bootstyle="secondary").pack(side=LEFT, padx=2)
        ttk.Label(hdr, text="URL",       width=1,  font=("Segoe UI", 9, "bold"), bootstyle="secondary").pack(side=LEFT, fill=X, expand=YES, padx=2)
        ttk.Label(hdr, text="      ",    width=8,  font=("Segoe UI", 9)).pack(side=LEFT)  # Copy btn spacer
        ttk.Label(hdr, text="Key",       width=1,  font=("Segoe UI", 9, "bold"), bootstyle="secondary").pack(side=LEFT, fill=X, expand=YES, padx=2)
        ttk.Label(hdr, text="      ",    width=8,  font=("Segoe UI", 9)).pack(side=LEFT)  # Copy btn spacer
        ttk.Separator(self.stream_url_key_frame, orient=HORIZONTAL).pack(fill=X, pady=(0, 8))

        # Scrollable inner area for stream rows
        self._stream_url_key_rows_frame = ttk.Frame(self.stream_url_key_frame)
        self._stream_url_key_rows_frame.pack(fill=X)
        self._stream_url_key_row_widgets = []  # list of (url_var, key_var)

        # Placeholder label shown when no data yet
        self._stream_url_key_placeholder = ttk.Label(
            self._stream_url_key_rows_frame,
            text="⏳ Chờ scan lần đầu...",
            font=("Segoe UI", 9),
            bootstyle="secondary",
        )
        self._stream_url_key_placeholder.pack(anchor=W)

        # Compat aliases for _handle_stream_selection (still used on tree click)
        self.sel_stream_name_var = tk.StringVar(value="")
        self.sel_stream_url_var  = tk.StringVar(value="")
        self.sel_stream_key_var  = tk.StringVar(value="")

        # ========== LOGS SECTION ==========
        log_card = ttk.Labelframe(main_container, text=" 📝 Activity System Logs ", padding=10, bootstyle="dark")
        log_card.pack(fill=X)

        self.log_text = scrolledtext.ScrolledText(log_card, height=6, bg="#121212", fg="#00ffcc", font=("Consolas", 10), state=tk.DISABLED, wrap=tk.WORD, border=0)
        self.log_text.pack(fill=BOTH, expand=YES)

    def _update_machine_cards(self, entry: dict):
        """Update the machine status info cards from a port_list entry."""
        if not hasattr(self, "_machine_labels"):
            return
        mapping = {
            "ping": entry.get("ping", "—"),
            "timeout": entry.get("timeout", "0"),
            "cpu": entry.get("cpu", "—"),
            "memory": entry.get("memory", "—"),
            "gpu": entry.get("gpu", "—"),
            "mac_address": entry.get("mac_address", "—"),
            "network_speed": entry.get("network_speed", "—"),
            "sender_bw": entry.get("sender_bw", "—"),
            "receiver_bw": entry.get("receiver_bw", "—"),
            "pid_vmix": entry.get("pid_vmix", "—"),
            "rec": entry.get("rec", "—"),
            "live": entry.get("live", "—"),
            "ext": entry.get("ext", "—"),
            "resolution": entry.get("resolution", "—"),
        }
        for key, val in mapping.items():
            lbl = self._machine_labels.get(key)
            if lbl:
                lbl.config(text=str(val))

    def update_stream_url_key_panel(self, snapshot: dict | None):
        """Auto-populate the Stream URL & Key panel from a fresh quality snapshot.

        Rebuilds one row per stream showing [stream-name | URL (readonly) | Copy | Key (readonly) | Copy].
        Called automatically every time update_stream_quality_table receives new data.
        """
        if not hasattr(self, "_stream_url_key_rows_frame"):
            return

        container = self._stream_url_key_rows_frame

        # Remove old stream rows (keep placeholder)
        for w in container.winfo_children():
            w.destroy()
        self._stream_url_key_row_widgets = []

        streams = (snapshot or {}).get("streams", []) if isinstance(snapshot, dict) else []

        # Sort helper — reuse logic mixin if available
        def _sort_key(entry):
            return self._stream_sort_key(entry.get("stream", "")) if hasattr(self, "_stream_sort_key") else entry.get("stream", "")

        if not streams:
            placeholder = ttk.Label(container, text="⏳ Chờ scan lần đầu...", font=("Segoe UI", 9), bootstyle="secondary")
            placeholder.pack(anchor=W)
            return

        for entry in sorted(streams, key=_sort_key):
            stream_name = entry.get("stream", "")
            info        = entry.get("config") or {}
            runtime     = entry.get("runtime") or {}
            raw_content = runtime.get("raw_content", "")

            # ── Compose endpoint + key (same logic as _handle_stream_selection) ──
            if hasattr(self, "_compose_stream_endpoint"):
                endpoint, key = self._compose_stream_endpoint(info)
            else:
                endpoint, key = "-", ""

            if hasattr(self, "_compose_stream_endpoint_from_log") and raw_content:
                ep_log, key_log = self._compose_stream_endpoint_from_log(raw_content)
                if endpoint in ("", "-", "(trong)", "(khong xac dinh)") and ep_log and ep_log != "(trong)":
                    endpoint = ep_log
                if not key and key_log:
                    key = key_log

            endpoint = endpoint or "-"
            key      = key      or "(trong)"

            # Enabled badge color
            enabled = info.get("enabled")
            if enabled is True:
                badge_style = "success"
                badge_text  = f"✅ {stream_name}"
            elif enabled is False:
                badge_style = "secondary"
                badge_text  = f"⬜ {stream_name}"
            else:
                badge_style = "warning"
                badge_text  = f"❓ {stream_name}"

            # ── Build row ──────────────────────────────────────────────────────
            row = ttk.Frame(container)
            row.pack(fill=X, pady=3)

            # Stream name label
            ttk.Label(row, text=badge_text, width=16, font=("Segoe UI", 9, "bold"), bootstyle=badge_style, anchor=W).pack(side=LEFT, padx=(0, 6))

            # URL field
            url_var = tk.StringVar(value=endpoint)
            url_entry = ttk.Entry(row, textvariable=url_var, font=("Consolas", 9), state="readonly", bootstyle="dark")
            url_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0, 4))
            ttk.Button(
                row, text="Copy URL",
                command=lambda v=url_var: self.copy_to_clipboard(v.get()),
                bootstyle="info-outline", width=10,
            ).pack(side=LEFT, padx=(0, 10))

            # Key field
            key_var = tk.StringVar(value=key)
            key_entry = ttk.Entry(row, textvariable=key_var, font=("Consolas", 9), state="readonly", bootstyle="dark")
            key_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0, 4))
            ttk.Button(
                row, text="Copy Key",
                command=lambda v=key_var: self.copy_to_clipboard(v.get()),
                bootstyle="warning-outline", width=10,
            ).pack(side=LEFT)

            self._stream_url_key_row_widgets.append((url_var, key_var))

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
                    return "Xanh"
                if s == "VANG":
                    return "Vang"
                if s == "DO":
                    return "Do"
                return "-"

            tree.insert(
                "",
                tk.END,
                values=(
                    entry.get("stream", ""),
                    run.get("status", "-"),
                    _health_dot(health.get("status", "")) if health else "-",
                    self._format_stream_bitrate(ui_snap.get("video_bitrate", "-")),
                    ui_snap.get("encode_size", "-"),
                    self._format_stream_bitrate(ui_snap.get("audio_bitrate", "-")),
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

        ttk.Label(frame, text="Nhập IP cũ để import data:", font=("Segoe UI", 11, "bold")).pack(pady=(0, 10))

        old_ip_var = tk.StringVar()
        ip_entry = ttk.Entry(frame, textvariable=old_ip_var, width=30, font=("Segoe UI", 10))
        ip_entry.pack(pady=10)
        ip_entry.focus()

        ttk.Label(frame, text="Ví dụ: 192.168.1.86", font=("Segoe UI", 9), bootstyle="secondary").pack(pady=(0, 15))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        def do_import():
            old_ip = old_ip_var.get().strip()
            if not old_ip:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập IP!")
                return
            dialog.destroy()
            threading.Thread(target=lambda: self.import_from_old_ip(old_ip), daemon=True).start()

        ttk.Button(btn_frame, text="📥 Import", command=do_import, bootstyle="success", width=15).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Hủy", command=dialog.destroy, bootstyle="secondary", width=15).pack(side=LEFT, padx=5)
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
        # Update machine info cards from first entry (all entries share same machine stats)
        if self.port_list:
            self._update_machine_cards(self.port_list[0])

    def _on_srt_ext_name_dblclick(self, event):
        """Handle double-click on SRT External Outputs table to edit Name column."""
        tree = self.srt_ext_tree
        region = tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        col = tree.identify_column(event.x)
        # col is like "#1", "#2", etc. — Name is column #1
        if col != "#1":
            return

        item = tree.identify_row(event.y)
        if not item:
            return

        # Get current values
        values = tree.item(item, "values")
        if not values or len(values) < 2:
            return

        current_name = values[0]
        title = values[1]  # Title (OutputsExternal, etc.)

        # Get cell bounding box
        bbox = tree.bbox(item, column="name")
        if not bbox:
            return

        x, y, w, h = bbox

        # Create inline entry
        entry_var = tk.StringVar(value=current_name)
        entry = tk.Entry(
            tree,
            textvariable=entry_var,
            font=("Segoe UI", 10),
            justify=CENTER,
            bd=1,
            relief="solid",
            bg="#2e2e2e",
            fg="white",
            insertbackground="white"
        )
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        entry.select_range(0, tk.END)

        def _save(e=None):
            new_name = entry_var.get().strip()
            self._srt_ext_custom_names[title] = new_name
            # Update current row safely
            try:
                if tree.exists(item):
                    new_values = list(values)
                    new_values[0] = new_name
                    tree.item(item, values=new_values)
            except Exception:
                pass
            if new_name:
                self.log(f"✏️ Đổi tên {title} → {new_name}")
            else:
                self.log(f"✏️ Xóa tên SRT cho {title}")
            entry.destroy()

        def _cancel(e=None):
            entry.destroy()

        entry.bind("<Return>", _save)
        entry.bind("<Escape>", _cancel)
        entry.bind("<FocusOut>", _save)

    def copy_to_clipboard(self, text):
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log(f"📋 Copied to clipboard: {text[:50]}...")
        messagebox.showinfo("Clipboard", "Đã copy vào bộ nhớ tạm!")

    def on_stream_selected(self, event=None):
        """Handler when a stream is selected in the quality tree."""
        # This will be implemented in LogicMixin to have access to full snapshot
        if hasattr(self, "_handle_stream_selection"):
            self._handle_stream_selection()
