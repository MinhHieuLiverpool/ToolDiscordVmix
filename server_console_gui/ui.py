"""
Server Console GUI - UI Module
Premium dark-mode interface with Start/Stop controls and real-time log viewer.
"""

import os
import tkinter as tk
from datetime import datetime

import customtkinter as ctk
from PIL import Image

import pytz

try:
    from .logic import get_local_ip, get_wan_ip
except ImportError:
    try:
        from server_console_gui.logic import get_local_ip, get_wan_ip
    except ImportError:
        from logic import get_local_ip, get_wan_ip

VIETNAM_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

# ── Color Palette ────────────────────────────────────────────────────────────
# A premium dark palette with accent colors for status indicators
COLORS = {
    "bg_dark": "#0d1117",
    "bg_card": "#161b22",
    "bg_input": "#0d1117",
    "bg_log": "#010409",
    "border": "#30363d",
    "border_focus": "#58a6ff",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#484f58",
    "accent_blue": "#58a6ff",
    "accent_green": "#3fb950",
    "accent_red": "#f85149",
    "accent_orange": "#d29922",
    "accent_purple": "#bc8cff",
    "tag_stdout": "#58a6ff",
    "tag_stderr": "#f85149",
    "tag_uvicorn": "#bc8cff",
    "tag_system": "#d29922",
    "tag_error": "#f85149",
    "btn_start_bg": "#238636",
    "btn_start_hover": "#2ea043",
    "btn_stop_bg": "#da3633",
    "btn_stop_hover": "#f85149",
    "btn_clear_bg": "#30363d",
    "btn_clear_hover": "#484f58",
    "scrollbar": "#30363d",
    "scrollbar_hover": "#484f58",
}


class ServerConsoleUIMixin:
    """Mixin providing the GUI layout and log display logic."""

    def setup_ui(self):
        """Build the entire UI."""
        self.root.configure(fg_color=COLORS["bg_dark"])

        # ── Main container ────────────────────────────────────────────────
        self.main_frame = ctk.CTkFrame(self.root, fg_color=COLORS["bg_dark"])
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_header()
        self._build_control_bar()
        self._build_config_panel()   # ← collapsible config panel
        self._build_log_viewer()
        self._build_status_bar()

        self._auto_scroll = True
        self._config_panel_visible = False  # bắt đầu collapsed

    # ── Header ────────────────────────────────────────────────────────────
    def _build_header(self):
        header = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            height=60,
        )
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Inner padding
        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=0)

        # Left side: title
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="y")

        # Load cloud server icon
        self.logo_image = None
        icon_png_path = os.path.join(os.path.dirname(__file__), "cloud-server.png")
        if not os.path.exists(icon_png_path):
            icon_png_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets",
                "cloud-server.png",
            )
        if os.path.exists(icon_png_path):
            try:
                pil_img = Image.open(icon_png_path)
                self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
            except Exception as e:
                print(f"Warning: Failed to load icon image: {e}")

        if self.logo_image:
            icon_label = ctk.CTkLabel(left, image=self.logo_image, text="")
            icon_label.pack(side="left", padx=(0, 10), pady=12)

        title_label = ctk.CTkLabel(
            left,
            text="Server Console",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title_label.pack(side="left", pady=12)

        subtitle = ctk.CTkLabel(
            left,
            text="  FastAPI + Uvicorn",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_muted"],
        )
        subtitle.pack(side="left", pady=12)

        # Right side: config toggle + status badge
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right", fill="y")

        self.status_badge = ctk.CTkLabel(
            right,
            text="  ● STOPPED  ",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=COLORS["accent_red"],
            fg_color=COLORS["bg_dark"],
            corner_radius=12,
        )
        self.status_badge.pack(side="right", pady=15, padx=5)

        # Config panel toggle button
        self.config_toggle_btn = ctk.CTkButton(
            right,
            text="⚙ Database",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=COLORS["btn_clear_bg"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            corner_radius=6,
            width=100,
            height=28,
            command=self._toggle_config_panel,
        )
        self.config_toggle_btn.pack(side="right", pady=15, padx=(0, 8))

        # Separator line
        sep = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["border"],
            height=1,
            corner_radius=0,
        )
        sep.pack(fill="x", side="top")

    # ── Config Panel (collapsible) ────────────────────────────────────────
    def _build_config_panel(self):
        """Build the collapsible database configuration panel."""
        self._config_panel_visible = False

        # Outer wrapper — hidden by default
        self.config_panel_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
        )
        # Don't pack yet — will show/hide via toggle

        # Separator on top of panel
        ctk.CTkFrame(self.config_panel_frame, fg_color=COLORS["accent_purple"], height=2, corner_radius=0).pack(fill="x")

        # Inner content
        content = ctk.CTkFrame(self.config_panel_frame, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=12)

        # Title
        ctk.CTkLabel(
            content,
            text="⚙  Cấu hình Database MongoDB",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLORS["accent_purple"],
        ).pack(anchor="w", pady=(0, 10))

        # Row 1: MongoDB URI
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            row1,
            text="MongoDB URI:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
            width=110,
            anchor="w",
        ).pack(side="left", padx=(0, 8))

        self._config_uri_var = ctk.StringVar(value=self._load_config_value("MONGODB_URI"))
        self.config_uri_entry = ctk.CTkEntry(
            row1,
            textvariable=self._config_uri_var,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text="mongodb+srv://user:pass@cluster.mongodb.net/",
            show="*",
            height=32,
        )
        self.config_uri_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Show/hide toggle for URI
        self._uri_hidden = True
        self.uri_eye_btn = ctk.CTkButton(
            row1,
            text="👁",
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["btn_clear_bg"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            width=36,
            height=32,
            corner_radius=6,
            command=self._toggle_uri_visibility,
        )
        self.uri_eye_btn.pack(side="left")

        # Row 2: Database Name + Collection
        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            row2,
            text="Database:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
            width=110,
            anchor="w",
        ).pack(side="left", padx=(0, 8))

        self._config_db_var = ctk.StringVar(value=self._load_config_value("DATABASE_NAME", "vmix_monitor"))
        ctk.CTkEntry(
            row2,
            textvariable=self._config_db_var,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text="vmix_monitor",
            height=32,
            width=200,
        ).pack(side="left", padx=(0, 20))

        ctk.CTkLabel(
            row2,
            text="Collection:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
            width=80,
            anchor="w",
        ).pack(side="left", padx=(0, 8))

        self._config_col_var = ctk.StringVar(value=self._load_config_value("COLLECTION_NAME", "logs"))
        ctk.CTkEntry(
            row2,
            textvariable=self._config_col_var,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text="logs",
            height=32,
            width=160,
        ).pack(side="left")

        # Row 3: Buttons + status
        row3 = ctk.CTkFrame(content, fg_color="transparent")
        row3.pack(fill="x", pady=(4, 0))

        self.config_test_btn = ctk.CTkButton(
            row3,
            text="🔌 Test Kết Nối",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLORS["accent_purple"],
            hover_color="#9d6fe8",
            text_color="#ffffff",
            corner_radius=8,
            width=140,
            height=32,
            command=self._on_test_db_click,
        )
        self.config_test_btn.pack(side="left", padx=(0, 8))

        self.config_save_btn = ctk.CTkButton(
            row3,
            text="💾 Lưu Config",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLORS["btn_start_bg"],
            hover_color=COLORS["btn_start_hover"],
            text_color="#ffffff",
            corner_radius=8,
            width=130,
            height=32,
            command=self._on_save_config_click,
        )
        self.config_save_btn.pack(side="left", padx=(0, 16))

        self.config_status_label = ctk.CTkLabel(
            row3,
            text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"],
        )
        self.config_status_label.pack(side="left")

        # Bottom separator
        ctk.CTkFrame(self.config_panel_frame, fg_color=COLORS["border"], height=1, corner_radius=0).pack(fill="x")

    def _toggle_config_panel(self):
        """Show/hide the config panel."""
        if self._config_panel_visible:
            self.config_panel_frame.pack_forget()
            self._config_panel_visible = False
            self.config_toggle_btn.configure(
                fg_color=COLORS["btn_clear_bg"],
                text_color=COLORS["text_secondary"],
                text="⚙ Database",
            )
        else:
            # Insert after control bar separator — before log viewer
            self.config_panel_frame.pack(fill="x", side="top", before=self._log_container_ref)
            self._config_panel_visible = True
            self.config_toggle_btn.configure(
                fg_color=COLORS["accent_purple"],
                text_color="#ffffff",
                text="⚙ Database ▲",
            )

    def _toggle_uri_visibility(self):
        """Toggle MongoDB URI show/hide."""
        if self._uri_hidden:
            self.config_uri_entry.configure(show="")
            self.uri_eye_btn.configure(text="🙈")
            self._uri_hidden = False
        else:
            self.config_uri_entry.configure(show="*")
            self.uri_eye_btn.configure(text="👁")
            self._uri_hidden = True

    def _load_config_value(self, key: str, default: str = "") -> str:
        """Load a value from config.py."""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", os.path.join(project_root, "config.py"))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return str(getattr(mod, key, default))
        except Exception:
            pass
        return os.getenv(key, default)

    def _on_test_db_click(self):
        """Test MongoDB connection in background thread."""
        uri = self._config_uri_var.get().strip()
        if not uri:
            self.config_status_label.configure(text="⚠ URI không được trống!", text_color=COLORS["accent_orange"])
            return
        self.config_test_btn.configure(state="disabled", text="⏳ Đang test...")
        self.config_status_label.configure(text="Đang kết nối...", text_color=COLORS["text_muted"])

        import threading
        def _test():
            try:
                from pymongo import MongoClient
                kwargs = {"serverSelectionTimeoutMS": 5000}
                if uri.startswith("mongodb+srv://"):
                    kwargs["tls"] = True
                    kwargs["tlsAllowInvalidCertificates"] = True
                c = MongoClient(uri, **kwargs)
                c.admin.command("ping")
                db_name = self._config_db_var.get().strip() or "vmix_monitor"
                cols = c[db_name].list_collection_names()
                c.close()
                msg = f"✓ Kết nối thành công! DB: {db_name} ({len(cols)} collections)"
                color = COLORS["accent_green"]
            except Exception as e:
                msg = f"✗ Lỗi: {e}"
                color = COLORS["accent_red"]
            self.root.after(0, lambda: self._set_test_result(msg, color))
        threading.Thread(target=_test, daemon=True, name="db-test").start()

    def _set_test_result(self, msg: str, color: str):
        """Update test result on main thread."""
        self.config_status_label.configure(text=msg, text_color=color)
        self.config_test_btn.configure(state="normal", text="🔌 Test Kết Nối")

    def _on_save_config_click(self):
        """Save MongoDB config to config.py."""
        uri = self._config_uri_var.get().strip()
        db = self._config_db_var.get().strip() or "vmix_monitor"
        col = self._config_col_var.get().strip() or "logs"

        if not uri:
            self.config_status_label.configure(text="⚠ URI không được trống!", text_color=COLORS["accent_orange"])
            return
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, "config.py")

            # Read existing file to preserve other values (DISCORD_WEBHOOK, PREFIX...)
            existing_lines = []
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    existing_lines = f.readlines()

            keys_managed = {"MONGODB_URI", "DATABASE_NAME", "COLLECTION_NAME"}
            new_values = {
                "MONGODB_URI": uri,
                "DATABASE_NAME": db,
                "COLLECTION_NAME": col,
            }
            written = set()
            new_lines = []
            for line in existing_lines:
                key = line.split("=")[0].strip().strip('#').strip()
                if key in keys_managed and not line.strip().startswith("#"):
                    val = new_values[key]
                    new_lines.append(f"{key} = \"{val}\"\n")
                    written.add(key)
                else:
                    new_lines.append(line)
            for k, v in new_values.items():
                if k not in written:
                    new_lines.append(f"{k} = \"{v}\"\n")

            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            self.config_status_label.configure(
                text=f"✓ Đã lưu vào config.py — Restart server để áp dụng!",
                text_color=COLORS["accent_green"]
            )
            self.config_save_btn.configure(text="✓ Đã Lưu!")
            self.root.after(2500, lambda: self.config_save_btn.configure(text="💾 Lưu Config"))
        except Exception as e:
            self.config_status_label.configure(text=f"✗ Lỗi lưu: {e}", text_color=COLORS["accent_red"])

    # ── Control Bar ───────────────────────────────────────────────────────

    def _build_control_bar(self):
        bar = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            height=55,
        )
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=8)

        # Start button
        self.start_btn = ctk.CTkButton(
            inner,
            text="▶  Start Server",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLORS["btn_start_bg"],
            hover_color=COLORS["btn_start_hover"],
            text_color="#ffffff",
            corner_radius=8,
            width=160,
            height=36,
            command=self._on_start_click,
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        # Stop button
        self.stop_btn = ctk.CTkButton(
            inner,
            text="■  Stop Server",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLORS["btn_stop_bg"],
            hover_color=COLORS["btn_stop_hover"],
            text_color="#ffffff",
            corner_radius=8,
            width=140,
            height=36,
            command=self._on_stop_click,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 8))

        # Open Server button
        self.open_server_btn = ctk.CTkButton(
            inner,
            text="🌐  Mở Server",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["border_focus"],
            text_color="#ffffff",
            corner_radius=8,
            width=140,
            height=36,
            command=self._on_open_server_click,
        )
        self.open_server_btn.pack(side="left", padx=(0, 4))

        # LAN / WAN toggle button
        self._url_mode = "WAN"   # "WAN" or "LAN"
        self._wan_ip: str = ""
        self._lan_ip: str = get_local_ip()
        self.toggle_ip_btn = ctk.CTkButton(
            inner,
            text="WAN",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["border_focus"],
            text_color="#ffffff",
            corner_radius=8,
            width=52,
            height=36,
            command=self._on_toggle_ip_mode,
        )
        self.toggle_ip_btn.pack(side="left", padx=(0, 8))

        # Separator
        sep_v = ctk.CTkFrame(inner, fg_color=COLORS["border"], width=1)
        sep_v.pack(side="left", fill="y", padx=12, pady=4)

        # Clear log button
        self.clear_btn = ctk.CTkButton(
            inner,
            text="🗑  Clear Logs",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=COLORS["btn_clear_bg"],
            hover_color=COLORS["btn_clear_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=8,
            width=130,
            height=36,
            command=self._on_clear_click,
        )
        self.clear_btn.pack(side="left", padx=(0, 8))

        # Auto-scroll toggle
        self.auto_scroll_var = ctk.BooleanVar(value=True)
        self.auto_scroll_chk = ctk.CTkCheckBox(
            inner,
            text="Auto-scroll",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"],
            variable=self.auto_scroll_var,
            onvalue=True,
            offvalue=False,
            checkbox_height=18,
            checkbox_width=18,
            corner_radius=4,
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["border_focus"],
            border_color=COLORS["border"],
        )
        self.auto_scroll_chk.pack(side="left", padx=(8, 0))

        # Right side info: Server URL & Copy button
        right_info = ctk.CTkFrame(inner, fg_color="transparent")
        right_info.pack(side="right")

        self.copy_btn = ctk.CTkButton(
            right_info,
            text="📋 Copy Link",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=COLORS["btn_clear_bg"],
            hover_color=COLORS["btn_clear_hover"],
            text_color=COLORS["accent_blue"],
            corner_radius=6,
            width=90,
            height=28,
            command=self._on_copy_link_click,
        )
        self.copy_btn.pack(side="right", padx=(8, 0))

        initial_lan = get_local_ip()
        self.server_url_label = ctk.CTkLabel(
            right_info,
            text=f"http://{initial_lan}:8001",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=COLORS["accent_blue"],
        )
        self.server_url_label.pack(side="right", padx=(4, 0))

        # Fetch real WAN IP in background so UI doesn't freeze
        import threading
        def _init_wan_label():
            port = int(os.getenv("PORT", 8001))
            lan = get_local_ip()
            try:
                wan = get_wan_ip(timeout=8.0)
                try:
                    self.root.after(0, lambda: self._update_server_url_label(wan, port, lan_ip=lan))
                except Exception:
                    pass
            except Exception:
                try:
                    self.root.after(0, lambda: self._update_server_url_label(lan, port, lan_ip=lan))
                except Exception:
                    pass
        threading.Thread(target=_init_wan_label, daemon=True, name="init-wan-label").start()

        self.url_title_label = ctk.CTkLabel(
            right_info,
            text="🌐 NK SEF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLORS["text_secondary"],
        )
        self.url_title_label.pack(side="right", padx=(12, 0))

        # Separator line
        sep = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["border"],
            height=1,
            corner_radius=0,
        )
        sep.pack(fill="x", side="top")

    # ── Log Viewer ────────────────────────────────────────────────────────
    def _build_log_viewer(self):
        log_container = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_log"],
            corner_radius=0,
        )
        log_container.pack(fill="both", expand=True, side="top")
        self._log_container_ref = log_container  # used by _toggle_config_panel


        # Use a raw tkinter Text widget for maximum performance with large logs
        # wrapped in a CTk frame for styling consistency
        text_frame = ctk.CTkFrame(log_container, fg_color=COLORS["bg_log"], corner_radius=0)
        text_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Scrollbar
        self.log_scrollbar = ctk.CTkScrollbar(
            text_frame,
            orientation="vertical",
            fg_color=COLORS["bg_log"],
            button_color=COLORS["scrollbar"],
            button_hover_color=COLORS["scrollbar_hover"],
        )
        self.log_scrollbar.pack(side="right", fill="y", padx=(4, 0))

        # Text widget
        self.log_text = tk.Text(
            text_frame,
            wrap="word",
            font=("Cascadia Code", 11),
            bg=COLORS["bg_log"],
            fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
            selectbackground=COLORS["accent_blue"],
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=8,
            yscrollcommand=self.log_scrollbar.set,
            state="disabled",
            spacing1=2,
            spacing3=2,
        )
        self.log_text.pack(fill="both", expand=True)

        self.log_scrollbar.configure(command=self.log_text.yview)

        # Configure text tags for colored output
        self.log_text.tag_configure("timestamp", foreground=COLORS["text_muted"],
                                    font=("Cascadia Code", 10))
        self.log_text.tag_configure("tag_stdout", foreground=COLORS["tag_stdout"],
                                    font=("Cascadia Code", 10, "bold"))
        self.log_text.tag_configure("tag_stderr", foreground=COLORS["tag_stderr"],
                                    font=("Cascadia Code", 10, "bold"))
        self.log_text.tag_configure("tag_uvicorn", foreground=COLORS["tag_uvicorn"],
                                    font=("Cascadia Code", 10, "bold"))
        self.log_text.tag_configure("tag_system", foreground=COLORS["tag_system"],
                                    font=("Cascadia Code", 10, "bold"))
        self.log_text.tag_configure("tag_error", foreground=COLORS["tag_error"],
                                    font=("Cascadia Code", 10, "bold"))
        self.log_text.tag_configure("msg_normal", foreground=COLORS["text_primary"])
        self.log_text.tag_configure("msg_error", foreground=COLORS["accent_red"])
        self.log_text.tag_configure("msg_success", foreground=COLORS["accent_green"])
        self.log_text.tag_configure("msg_warning", foreground=COLORS["accent_orange"])
        self.log_text.tag_configure("separator", foreground=COLORS["text_muted"])

        # Welcome message
        self._insert_welcome_message()

    def _insert_welcome_message(self):
        """Show a welcome banner when the app starts."""
        self.log_text.configure(state="normal")
        now = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")

        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║            ⚡ Server Console GUI                        ║",
            "║          FastAPI + Uvicorn Server Manager               ║",
            "╚══════════════════════════════════════════════════════════╝",
            "",
            "  Nhấn  ▶ Start Server  để khởi động server.",
            "  Các máy khác có thể truy cập qua LINK SERVER ở góc trên phải.",
            "",
            "─────────────────────────────────────────────────────────────",
        ]
        for line in lines:
            self.log_text.insert("end", f"  {line}\n", "msg_success")

        self.log_text.configure(state="disabled")

    # ── Status Bar ────────────────────────────────────────────────────────
    def _build_status_bar(self):
        status_bar = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            height=30,
        )
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        # Separator
        sep = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["border"],
            height=1,
            corner_radius=0,
        )
        sep.pack(fill="x", side="bottom")

        inner = ctk.CTkFrame(status_bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=0)

        self.status_uptime_label = ctk.CTkLabel(
            inner,
            text="Uptime: —",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"],
        )
        self.status_uptime_label.pack(side="left", padx=(0, 20))

        self.status_lines_label = ctk.CTkLabel(
            inner,
            text="Lines: 0",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"],
        )
        self.status_lines_label.pack(side="left", padx=(0, 20))

        self.status_time_label = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"],
        )
        self.status_time_label.pack(side="right")

        # Start clock update
        self._update_clock()

    # ── UI Actions ────────────────────────────────────────────────────────
    def _on_copy_link_click(self):
        """Copy current server URL to clipboard."""
        url = self.server_url_label.cget("text")
        if url:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(url)
                self.copy_btn.configure(text="✓ Copied!", fg_color=COLORS["btn_start_bg"])
                self.root.after(1500, lambda: self.copy_btn.configure(text="📋 Copy Link", fg_color=COLORS["btn_clear_bg"]))
            except Exception as e:
                print(f"Copy error: {e}")

    def _on_open_server_click(self):
        """Open current server URL (WAN or LAN depending on toggle) in default browser."""
        import webbrowser
        url = self.server_url_label.cget("text") if hasattr(self, "server_url_label") else ""
        if not url or url == "—":
            url = f"http://{self._lan_ip}:8001"
        webbrowser.open(url)

    def _on_toggle_ip_mode(self):
        """Toggle between WAN and LAN URL display."""
        port = int(os.getenv("PORT", 8001))
        if self._url_mode == "WAN":
            # Switch to LAN
            self._url_mode = "LAN"
            lan_url = f"http://{self._lan_ip}:{port}" if self._lan_ip else "—"
            if hasattr(self, "server_url_label"):
                self.server_url_label.configure(text=lan_url)
            if hasattr(self, "toggle_ip_btn"):
                self.toggle_ip_btn.configure(
                    text="LAN",
                    fg_color=COLORS["accent_green"],
                    hover_color=COLORS["btn_start_hover"],
                )
            if hasattr(self, "url_title_label"):
                self.url_title_label.configure(text="🖧 NK SEF")
        else:
            # Switch to WAN
            self._url_mode = "WAN"
            wan_url = f"http://{self._wan_ip}:{port}" if self._wan_ip else f"http://{self._lan_ip}:{port}"
            if hasattr(self, "server_url_label"):
                self.server_url_label.configure(text=wan_url)
            if hasattr(self, "toggle_ip_btn"):
                self.toggle_ip_btn.configure(
                    text="WAN",
                    fg_color=COLORS["accent_blue"],
                    hover_color=COLORS["border_focus"],
                )
            if hasattr(self, "url_title_label"):
                self.url_title_label.configure(text="🌐 NK SEF")

    def _update_server_url_label(self, ip: str, port: int, lan_ip: str = ""):
        """Update the server URL label. Called from main thread after WAN IP resolved.

        ip     = WAN IP (or LAN as fallback)
        lan_ip = LAN IP (optional, to store for toggle)
        """
        # Store both IPs for toggle
        self._wan_ip = ip
        if lan_ip:
            self._lan_ip = lan_ip

        # Only update label if currently showing WAN mode
        if self._url_mode == "WAN":
            url = f"http://{ip}:{port}"
            if hasattr(self, "server_url_label"):
                self.server_url_label.configure(text=url)
        if hasattr(self, "port_label"):
            self.port_label.configure(text=f"PORT: {port}")

    def _on_start_click(self):
        """Handle Start button click."""
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._update_status("RUNNING", COLORS["accent_green"])
        timestamp = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
        self.log_queue.put((timestamp, "system", "🚀 Đang khởi động server..."))
        self.start_server()

    def _on_stop_click(self):
        """Handle Stop button click."""
        self.stop_btn.configure(state="disabled")
        self.stop_server()

    def _on_clear_click(self):
        """Clear the log viewer."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._log_line_count = 0
        self._update_status_bar()

    def _update_ui_state(self):
        """Sync UI widgets with current server state."""
        if self.server_running:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self._update_status("RUNNING", COLORS["accent_green"])
        else:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self._update_status("STOPPED", COLORS["accent_red"])

    def _update_status(self, text: str, color: str):
        """Update the status badge."""
        self.status_badge.configure(text=f"  ● {text}  ", text_color=color)

    def _update_status_bar(self):
        """Update the bottom status bar."""
        uptime = self.get_uptime_str() if hasattr(self, "get_uptime_str") else "—"
        self.status_uptime_label.configure(text=f"Uptime: {uptime}")
        self.status_lines_label.configure(text=f"Lines: {self._log_line_count}")

    def _update_clock(self):
        """Update the clock in the status bar."""
        now = datetime.now(VIETNAM_TZ).strftime("%d/%m/%Y  %H:%M:%S")
        self.status_time_label.configure(text=now)

        # Also refresh uptime
        if self.server_running:
            self._update_status_bar()

        self.root.after(1000, self._update_clock)

    # ── Log Rendering ─────────────────────────────────────────────────────
    def _append_log_lines(self, batch: list):
        """Append a batch of log lines to the text widget.

        Each item is a tuple: (timestamp, tag, message)
        """
        self.log_text.configure(state="normal")

        # Limit total lines to prevent memory bloat (keep last 5000 lines)
        max_lines = 5000
        current_lines = int(self.log_text.index("end-1c").split(".")[0])
        if current_lines > max_lines:
            excess = current_lines - max_lines + len(batch)
            if excess > 0:
                self.log_text.delete("1.0", f"{excess}.0")

        for timestamp, tag, message in batch:
            # Timestamp
            self.log_text.insert("end", f" {timestamp} ", "timestamp")

            # Tag badge
            tag_display = tag.upper()
            tag_style = f"tag_{tag}" if f"tag_{tag}" in (
                "tag_stdout", "tag_stderr", "tag_uvicorn", "tag_system", "tag_error"
            ) else "tag_stdout"
            self.log_text.insert("end", f" [{tag_display}] ", tag_style)

            # Message with color hints
            msg_style = self._detect_msg_style(message)
            self.log_text.insert("end", f" {message}\n", msg_style)

        # Auto-scroll if enabled
        if self.auto_scroll_var.get():
            self.log_text.see("end")

        self.log_text.configure(state="disabled")

    def _detect_msg_style(self, message: str) -> str:
        """Detect message type and return appropriate tag for coloring."""
        lower = message.lower()
        if any(kw in lower for kw in ["error", "✗", "exception", "traceback", "failed"]):
            return "msg_error"
        if any(kw in lower for kw in ["✓", "success", "connected", "started"]):
            return "msg_success"
        if any(kw in lower for kw in ["⚠", "warning", "warn", "⚠️"]):
            return "msg_warning"
        return "msg_normal"
