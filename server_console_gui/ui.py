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
    from .logic import get_local_ip
except ImportError:
    try:
        from server_console_gui.logic import get_local_ip
    except ImportError:
        from logic import get_local_ip

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
        self._build_log_viewer()
        self._build_status_bar()

        self._auto_scroll = True

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

        # Right side: status badge
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

        # Separator line
        sep = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["border"],
            height=1,
            corner_radius=0,
        )
        sep.pack(fill="x", side="top")

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
        self.open_server_btn.pack(side="left", padx=(0, 8))

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

        initial_ip = get_local_ip()
        self.server_url_label = ctk.CTkLabel(
            right_info,
            text=f"http://{initial_ip}:8001",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=COLORS["accent_blue"],
        )
        self.server_url_label.pack(side="right", padx=(4, 0))

        self.url_title_label = ctk.CTkLabel(
            right_info,
            text="🌐 LINK SERVER:",
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
        """Open current server URL in default browser."""
        import webbrowser
        url = self.server_url_label.cget("text") if hasattr(self, "server_url_label") else ""
        if not url or url == "—":
            try:
                from .logic import get_local_ip
            except ImportError:
                from logic import get_local_ip
            url = f"http://{get_local_ip()}:8001"
        webbrowser.open(url)

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
