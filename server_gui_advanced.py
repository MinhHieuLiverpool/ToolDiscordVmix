import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import threading
import json
from datetime import datetime
import pytz
import websocket
import time
import subprocess
import re
import os

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "dark", "light", "system"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

# Timezone configuration - Vietnam
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

def pretty_time(ts):
    try:
        dt = datetime.fromisoformat(ts)
        # Convert to Vietnam timezone if aware, otherwise assume it's already in Vietnam time
        if dt.tzinfo is not None:
            dt = dt.astimezone(VIETNAM_TZ)
        return dt.strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        return ts

def get_first_srt(d: dict) -> dict:
    """Safely extract the first SRT dict from data.
    Handles both old dict format and new array format."""
    srt_raw = d.get("SRT", {})
    if isinstance(srt_raw, dict):
        return srt_raw
    if isinstance(srt_raw, list):
        for item in srt_raw:
            if isinstance(item, dict):
                return item
    return {}

def get_srt_ports_str(d: dict) -> str:
    """Get a display string of all SRT ports from data."""
    srt_raw = d.get("SRT", [])
    if isinstance(srt_raw, dict):
        return str(srt_raw.get("port", ""))
    if isinstance(srt_raw, list):
        ports = []
        for item in srt_raw:
            if isinstance(item, dict) and item.get("port"):
                ports.append(str(item["port"]))
        return ", ".join(ports)
    return ""

def get_srt_quality_str(d: dict) -> str:
    """Get a display string of SRT quality info from all SRT streams."""
    srt_raw = d.get("SRT", [])
    if isinstance(srt_raw, dict):
        return srt_raw.get("quality", "") or "—"
    if isinstance(srt_raw, list):
        qualities = []
        for item in srt_raw:
            if isinstance(item, dict):
                q = item.get("quality", "")
                name = item.get("nameSRT", "")
                port = item.get("port", "")
                status = item.get("status", "")
                label = name or str(port)
                if label:
                    qualities.append(f"{label}:{status}" + (f"({q})" if q else ""))
        return " | ".join(qualities) if qualities else "—"
    return "—"

class ServerDataGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Server Log Viewer - Dual Panel")
        self.root.geometry("2000x750")
        # Mo fullscreen (maximized) khi khoi chay
        self.root.after(100, lambda: self.root.state('zoomed'))

        # Use local server
        self.api_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws"
        self.webhook_var = ctk.StringVar(value="")
        self.prefix_var = ctk.StringVar(value="SRT")
        self.data = []  # All data from database
        self.selected_data = []  # Selected items to monitor
        self.previous_data = []
        self.auto_send_enabled = False
        self.is_sending = False  # Flag để tránh gửi duplicate
        self.ptz_ping_threads = {}  # PTZ ping threads: key=name:port, value={running, thread}
        self._log_last_write = {}    # Tracking thời gian ghi log: key=name, value=timestamp
        
        # WebSocket variables
        self.ws = None
        self.ws_connected = False
        self.ws_thread = None
        self.use_websocket = True  # Set False to fallback to REST API
        self.ws_reconnect_attempts = 0
        self.rest_polling_active = False  # Flag cho REST polling backup

        # Top controls
        top_frame = ctk.CTkFrame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        # Row 1: Webhook
        row1 = ctk.CTkFrame(top_frame, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        ctk.CTkLabel(row1, text="Discord Webhook:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.webhook_entry = ctk.CTkEntry(row1, textvariable=self.webhook_var, width=600, font=("Arial", 10))
        self.webhook_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Row 2: Prefix and buttons
        row2 = ctk.CTkFrame(top_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Prefix:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.prefix_entry = ctk.CTkEntry(row2, textvariable=self.prefix_var, width=80, font=("Arial", 10))
        self.prefix_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(row2, text="🔍 Scan máy", command=self.open_scan_dialog, fg_color="#4CAF50", hover_color="#45a049", width=110, font=("Arial", 10, "bold")).pack(side="left", padx=3)
        self.toggle_btn = ctk.CTkButton(row2, text="AUTO SEND: OFF", command=self.toggle_auto_send, fg_color="#9E9E9E", hover_color="#757575", width=130, font=("Arial", 10, "bold"))
        self.toggle_btn.pack(side="left", padx=3)
        ctk.CTkButton(row2, text="🗑️ Clear", command=self.clear_selected, fg_color="#f44336", hover_color="#d32f2f", width=90).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="💾 Save", command=self.save_selected_to_file, fg_color="#9C27B0", hover_color="#7B1FA2", width=90).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="📂 Open", command=self.load_selected_from_file, fg_color="#673AB7", hover_color="#512DA8", width=90).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="🌐 Web", command=self.open_web_dialog, fg_color="#00ACC1", hover_color="#00838F", width=90, font=("Arial", 10, "bold")).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="➕ Add PTZ", command=self.add_ptz_manual, fg_color="#FF9800", hover_color="#F57C00", width=100, font=("Arial", 10, "bold")).pack(side="left", padx=3)
        
        # Connection status
        self.status_label = ctk.CTkLabel(row2, text="⚪ Disconnected", font=("Arial", 9, "bold"), text_color="#9E9E9E")
        self.status_label.pack(side="right", padx=10)

        # Main content area with draggable splitter between table and vmPing
        self.vertical_splitter = tk.PanedWindow(
            self.root,
            orient=tk.VERTICAL,
            sashwidth=8,
            sashrelief=tk.RAISED,
            showhandle=True,
            bg="#1f1f1f",
        )
        self.vertical_splitter.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        main_frame = ctk.CTkFrame(self.vertical_splitter)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        self.vertical_splitter.add(main_frame, minsize=260)

        # Scan dialog state (All logs table lives in this popup)
        self.scan_dialog = None
        self.table_frame_left = None
        self.select_all_var = ctk.BooleanVar(value=False)
        self.select_all_cb = None
        
        self.left_table_rows = []
        self.left_table_checkboxes = {}

        # Selected logs to monitor (full width)
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(right_frame, text="⭐ SELECTED MONITOR LIST", font=("Arial", 11, "bold")).pack(pady=5)
        
        # Right table - Custom scrollable
        self.table_frame_right = ctk.CTkScrollableFrame(right_frame, fg_color="#2b2b2b")
        self.table_frame_right.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header
        header_frame_right = ctk.CTkFrame(self.table_frame_right, fg_color="#1a1a1a", height=40)
        header_frame_right.pack(fill="x", pady=(0, 5))
        header_frame_right.pack_propagate(False)
        
        ctk.CTkLabel(header_frame_right, text="STT",        font=("Arial", 10, "bold"), width=35).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="TÊN",        font=("Arial", 10, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="IP MÁY",     font=("Arial", 10, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="IP WAN",     font=("Arial", 10, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="STATUS",     font=("Arial", 10, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="PORT",       font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="NAME SRT",   font=("Arial", 10, "bold"), width=100).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="QUALITY",    font=("Arial", 10, "bold"), width=180).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="APP",        font=("Arial", 10, "bold"), width=45).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="📡 PING",    font=("Arial", 10, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="❌ TIMEOUT", font=("Arial", 10, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="⚡ CPU%",    font=("Arial", 10, "bold"), width=65).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="💾 RAM%",    font=("Arial", 10, "bold"), width=65).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="● REC",      font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🔴 LIVE",    font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🟢 EXT",     font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🖥 RES",      font=("Arial", 10, "bold"), width=90).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="TIME",       font=("Arial", 10, "bold"), width=130).pack(side="left", padx=2)
        
        self.right_table_rows = []

        # ── vmPing Panel ────────────────────────────────────────────────────
        vmping_outer = ctk.CTkFrame(self.vertical_splitter, fg_color="#181818")
        self.vertical_splitter.add(vmping_outer, minsize=170)

        # Header bar
        vmping_header = ctk.CTkFrame(vmping_outer, fg_color="#1a1a1a", height=38)
        vmping_header.pack(fill="x", padx=0, pady=(0, 2))
        vmping_header.pack_propagate(False)

        ctk.CTkLabel(vmping_header, text="📡 vmPING", font=("Arial", 10, "bold"), text_color="#4CAF50").pack(side="left", padx=10)
        self.ping_ip_entry = ctk.CTkEntry(vmping_header, placeholder_text="Nhập IP hoặc hostname...", width=200, font=("Arial", 10))
        self.ping_ip_entry.pack(side="left", padx=5)
        self.ping_ip_entry.bind("<Return>", lambda e: self.add_ping_host())
        ctk.CTkButton(vmping_header, text="+ Add", command=self.add_ping_host, fg_color="#4CAF50", hover_color="#45a049", width=60, font=("Arial", 10, "bold")).pack(side="left", padx=3)
        ctk.CTkButton(vmping_header, text="▶ Start All", command=self.start_all_pings, fg_color="#2196F3", hover_color="#1976D2", width=85, font=("Arial", 10)).pack(side="left", padx=3)
        ctk.CTkButton(vmping_header, text="⏹ Stop All", command=self.stop_all_pings, fg_color="#f44336", hover_color="#d32f2f", width=80, font=("Arial", 10)).pack(side="left", padx=3)
        ctk.CTkButton(vmping_header, text="🗑 Clear All", command=self.clear_all_pings, fg_color="#555555", hover_color="#444444", width=80, font=("Arial", 10)).pack(side="left", padx=3)
        self.ping_count_label = ctk.CTkLabel(vmping_header, text="0 monitors", font=("Arial", 9), text_color="#9E9E9E")
        self.ping_count_label.pack(side="right", padx=10)

        # Scrollable grid of ping cards
        self.ping_cards_frame = ctk.CTkScrollableFrame(vmping_outer, fg_color="#1e1e1e")
        self.ping_cards_frame.pack(fill="both", expand=True)
        for col in range(4):
            self.ping_cards_frame.grid_columnconfigure(col, weight=1)

        # Default split ratio: table section a bit larger than vmPing section.
        self.root.after(120, self._set_default_split_position)

        # vmPing state
        self.ping_hosts = {}   # host -> info dict
        self.ping_grid_cols = 4

        # Detail textbox (hidden but keep for show_detail_from_entry)
        self.detail_text = ctk.CTkTextbox(vmping_outer, height=0, font=("Consolas", 10), fg_color="#1e1e1e", text_color="#00ff00")
        # (not packed – kept only so show_detail_from_entry doesn't crash)

        # Load initial data once (without opening scan dialog)
        self.refresh_data(show_dialog=False)
        
        # Load selected list from database
        self.load_selected_from_database()
        
        # Start WebSocket connection if enabled
        if self.use_websocket:
            self.connect_websocket()
        else:
            # Fallback to REST polling
            self.start_rest_polling_backup()

    def _set_default_split_position(self):
        """Place splitter so top table area is larger than vmPing by default."""
        try:
            total_h = self.root.winfo_height()
            y = max(260, int(total_h * 0.62))
            self.vertical_splitter.sash_place(0, 0, y)
        except Exception:
            pass

    def open_web_dialog(self):
        """Open web account dialog with create and delete account actions."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Web Account")
        dialog.geometry("520x520")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 260
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 260
        dialog.geometry(f"520x520+{x}+{y}")

        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=16, pady=14)

        ctk.CTkLabel(container, text="TẠO TÀI KHOẢN WEB", font=("Arial", 14, "bold")).pack(pady=(2, 12))

        username_var = ctk.StringVar(value="")
        password_var = ctk.StringVar(value="")

        user_row = ctk.CTkFrame(container, fg_color="transparent")
        user_row.pack(fill="x", pady=4)
        ctk.CTkLabel(user_row, text="Username:", width=90, anchor="w", font=("Arial", 10, "bold")).pack(side="left")
        user_entry = ctk.CTkEntry(user_row, textvariable=username_var, placeholder_text="Nhập tài khoản")
        user_entry.pack(side="left", fill="x", expand=True)

        pass_row = ctk.CTkFrame(container, fg_color="transparent")
        pass_row.pack(fill="x", pady=4)
        ctk.CTkLabel(pass_row, text="Password:", width=90, anchor="w", font=("Arial", 10, "bold")).pack(side="left")
        pass_entry = ctk.CTkEntry(pass_row, textvariable=password_var, placeholder_text="Nhập mật khẩu", show="*")
        pass_entry.pack(side="left", fill="x", expand=True)

        status_label = ctk.CTkLabel(container, text="", text_color="#9E9E9E", font=("Arial", 10))
        status_label.pack(anchor="w", pady=(8, 2))

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        create_btn = ctk.CTkButton(btn_row, text="Tạo tài khoản", fg_color="#4CAF50", hover_color="#45a049", width=120)
        create_btn.pack(side="left", padx=(0, 8))
        refresh_btn = ctk.CTkButton(btn_row, text="Làm mới", fg_color="#2196F3", hover_color="#1976D2", width=90)
        refresh_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Đóng", fg_color="#616161", hover_color="#4E4E4E", width=90, command=dialog.destroy).pack(side="left")

        ctk.CTkLabel(container, text="Danh sách tài khoản", font=("Arial", 11, "bold")).pack(anchor="w", pady=(12, 4))
        accounts_frame = ctk.CTkScrollableFrame(container, fg_color="#242424", height=250)
        accounts_frame.pack(fill="both", expand=True)

        def render_accounts(accounts: list):
            for child in accounts_frame.winfo_children():
                child.destroy()

            if not accounts:
                ctk.CTkLabel(accounts_frame, text="Chưa có tài khoản", text_color="#9E9E9E").pack(anchor="w", padx=6, pady=6)
                return

            for acc in accounts:
                username = acc.get("username", "")
                password = acc.get("password", "")
                created_at = acc.get("created_at", "")

                row = ctk.CTkFrame(accounts_frame, fg_color="#2e2e2e", corner_radius=6)
                row.pack(fill="x", pady=3, padx=2)

                text_col = ctk.CTkFrame(row, fg_color="transparent")
                text_col.pack(side="left", fill="x", expand=True, padx=8, pady=6)
                ctk.CTkLabel(text_col, text=f"Tài khoản: {username}", font=("Arial", 10, "bold"), anchor="w").pack(anchor="w")

                shown_password = password if password else "(không có dữ liệu cũ)"
                masked_password = "*" * max(8, len(password)) if password else "********"
                password_var = ctk.StringVar(value=f"Mật khẩu: {masked_password}")
                is_revealed = {"value": False}

                pass_row = ctk.CTkFrame(text_col, fg_color="transparent")
                pass_row.pack(fill="x")
                pass_label = ctk.CTkLabel(pass_row, textvariable=password_var, font=("Arial", 10), anchor="w")
                pass_label.pack(side="left", anchor="w")

                def toggle_password_view(var=password_var, reveal=is_revealed, real=shown_password, masked=masked_password):
                    reveal["value"] = not reveal["value"]
                    if reveal["value"]:
                        var.set(f"Mật khẩu: {real}")
                    else:
                        var.set(f"Mật khẩu: {masked}")

                ctk.CTkButton(
                    pass_row,
                    text="👁",
                    width=52,
                    height=24,
                    fg_color="#5E35B1",
                    hover_color="#4527A0",
                    command=toggle_password_view,
                ).pack(side="left", padx=(8, 0))

                ctk.CTkLabel(text_col, text=created_at, font=("Arial", 9), text_color="#9E9E9E", anchor="w").pack(anchor="w", pady=(2, 0))

                def do_delete(u=username):
                    if not messagebox.askyesno("Xác nhận", f"Xóa tài khoản '{u}'?"):
                        return

                    def worker_delete():
                        try:
                            resp = requests.post(f"{self.api_url}/delete_account", json={"username": u}, timeout=8)
                            if resp.status_code == 200:
                                self.root.after(0, lambda: status_label.configure(text=f"Đã xóa tài khoản: {u}", text_color="#4CAF50"))
                                self.root.after(0, load_accounts)
                            else:
                                self.root.after(0, lambda: status_label.configure(text=f"Xóa thất bại: HTTP {resp.status_code}", text_color="#ff6b6b"))
                        except Exception as e:
                            self.root.after(0, lambda err=str(e): status_label.configure(text=f"Lỗi kết nối: {err}", text_color="#ff6b6b"))

                    threading.Thread(target=worker_delete, daemon=True).start()

                ctk.CTkButton(row, text="Xóa", width=64, fg_color="#f44336", hover_color="#d32f2f", command=do_delete).pack(side="right", padx=8, pady=6)

        def load_accounts():
            status_label.configure(text="Đang tải danh sách tài khoản...", text_color="#9E9E9E")

            def worker_list():
                try:
                    resp = requests.get(f"{self.api_url}/accounts", timeout=8)
                    if resp.status_code == 200:
                        payload = resp.json()
                        accounts = payload if isinstance(payload, list) else []
                        self.root.after(0, lambda data=accounts: render_accounts(data))
                        self.root.after(0, lambda: status_label.configure(text=f"Đã tải {len(accounts)} tài khoản", text_color="#9E9E9E"))
                    else:
                        self.root.after(0, lambda: status_label.configure(text=f"Không tải được danh sách: HTTP {resp.status_code}", text_color="#ff6b6b"))
                except Exception as e:
                    self.root.after(0, lambda err=str(e): status_label.configure(text=f"Lỗi kết nối: {err}", text_color="#ff6b6b"))

            threading.Thread(target=worker_list, daemon=True).start()

        def do_create_account():
            username = username_var.get().strip()
            password = password_var.get().strip()

            if not username:
                status_label.configure(text="Vui lòng nhập username", text_color="#ff6b6b")
                return
            if len(password) < 4:
                status_label.configure(text="Mật khẩu tối thiểu 4 ký tự", text_color="#ff6b6b")
                return

            create_btn.configure(state="disabled")
            status_label.configure(text="Đang tạo tài khoản...", text_color="#9E9E9E")

            def worker():
                payload = {"username": username, "password": password}
                endpoints = [
                    f"{self.api_url}/create_account",
                    f"{self.api_url}/register",
                ]

                not_found_count = 0
                for url in endpoints:
                    try:
                        resp = requests.post(url, json=payload, timeout=8)
                        if resp.status_code in (200, 201):
                            self.root.after(0, lambda: status_label.configure(text="Tạo tài khoản thành công", text_color="#4CAF50"))
                            self.root.after(0, lambda: create_btn.configure(state="normal"))
                            self.root.after(0, load_accounts)
                            self.root.after(0, lambda: password_var.set(""))
                            return
                        if resp.status_code in (404, 405):
                            not_found_count += 1
                            continue
                        self.root.after(0, lambda: status_label.configure(text=f"Tạo thất bại: HTTP {resp.status_code}", text_color="#ff6b6b"))
                        self.root.after(0, lambda: create_btn.configure(state="normal"))
                        return
                    except Exception as e:
                        self.root.after(0, lambda err=str(e): status_label.configure(text=f"Lỗi kết nối: {err}", text_color="#ff6b6b"))
                        self.root.after(0, lambda: create_btn.configure(state="normal"))
                        return

                if not_found_count == len(endpoints):
                    self.root.after(0, lambda: status_label.configure(text="Server chưa có API tạo tài khoản", text_color="#ffb74d"))
                    self.root.after(0, lambda: create_btn.configure(state="normal"))

            threading.Thread(target=worker, daemon=True).start()

        create_btn.configure(command=do_create_account)
        refresh_btn.configure(command=load_accounts)

        load_accounts()
        user_entry.focus_set()

    def connect_websocket(self):
        """Kết nối WebSocket để nhận realtime updates"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                # ensure we always work with a list
                if not isinstance(data, list):
                    return
                # dedupe incoming list by ip:port key to avoid duplicates when
                # the server accidentally sends the same payload twice.
                seen = set()
                deduped = []
                for entry in data:
                    d = entry.get("data", {})
                    key = f"{d.get('ip','')}:{d.get('port','')}"
                    if key not in seen:
                        seen.add(key)
                        deduped.append(entry)
                data = deduped
                
                # Update data
                # Check if có thay đổi về danh sách IP+Port
                has_list_changed = self.has_data_changed(self.data, data)
                # always replace internal list with deduped version
                self.data = data
                
                # Nếu có thay đổi danh sách -> update bảng trái
                if has_list_changed:
                    self.root.after(0, self.update_all_table)
                
                # Luôn update selected data và bảng phải
                self.update_selected_data()
                self.root.after(0, self.update_selected_table)
                
                # Check for changes and send Discord
                if self.auto_send_enabled:
                    self.send_to_discord_auto()
            except json.JSONDecodeError as e:
                print(f"✗ WebSocket JSON error: {e}")
            except Exception as e:
                print(f"✗ WebSocket message error: {e}")
        
        def on_error(ws, error):
            print(f"✗ WebSocket error: {error}")
            self.ws_connected = False
        
        def on_close(ws, close_status_code, close_msg):
            print(f"⚠ WebSocket closed: {close_status_code} - {close_msg}")
            self.ws_connected = False
            self.root.after(0, lambda: self.status_label.configure(text="🔴 Disconnected", text_color="#f44336"))
            # Start REST polling as backup
            if not self.rest_polling_active:
                self.start_rest_polling_backup()
            # Auto reconnect with exponential backoff
            if self.use_websocket:
                self.ws_reconnect_attempts += 1
                wait_time = min(5 * self.ws_reconnect_attempts, 30)  # Max 30s
                print(f"🔄 Reconnecting in {wait_time} seconds... (attempt {self.ws_reconnect_attempts})")
                time.sleep(wait_time)
                self.connect_websocket()
        
        def on_open(ws):
            print("✓ WebSocket connected!")
            self.ws_connected = True
            self.ws_reconnect_attempts = 0  # Reset counter
            self.rest_polling_active = False  # Stop REST polling
            self.root.after(0, lambda: self.status_label.configure(text="🟢 Connected", text_color="#4CAF50"))
        
        def run_ws():
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    on_open=on_open
                )
                self.ws.run_forever()
            except Exception as e:
                print(f"✗ WebSocket connection failed: {e}")
                print("⚠ Falling back to REST API polling...")
                self.ws_connected = False
                self.use_websocket = False
                # Start REST API polling as fallback
                self.start_rest_polling()
        
        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()
    
    def start_rest_polling(self):
        """Fallback: Polling REST API nếu WebSocket không hoạt động"""
        if self.auto_send_enabled and not self.ws_connected:
            self.check_for_changes()
    
    def start_rest_polling_backup(self):
        """Backup polling khi WebSocket mất kết nối"""
        if self.rest_polling_active or self.ws_connected:
            return
        
        self.rest_polling_active = True
        print("🔄 Starting REST polling backup...")
        self.rest_poll_loop()
    
    def rest_poll_loop(self):
        """Loop polling REST API"""
        if not self.rest_polling_active or self.ws_connected:
            self.rest_polling_active = False
            return
        
        def poll():
            try:
                resp = requests.get(f"{self.api_url}/logs", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        # dedupe incoming data
                        seen = set()
                        unique = []
                        for entry in data:
                            d = entry.get("data", {})
                            key = f"{d.get('ip','')}:{d.get('port','')}"
                            if key not in seen:
                                seen.add(key)
                                unique.append(entry)
                        data = unique
                        # Check if có thay đổi
                        has_list_changed = self.has_data_changed(self.data, data)
                        self.data = data
                        
                        if has_list_changed:
                            self.root.after(0, self.update_all_table)
                        
                        # Always update selected data
                        self.update_selected_data()
                        self.root.after(0, self.update_selected_table)
                        
                        # Check for changes and send Discord
                        if self.auto_send_enabled:
                            current_snapshot = self.get_data_snapshot()
                            if current_snapshot != self.previous_data:
                                self.send_to_discord_auto()
                                self.previous_data = current_snapshot
            except Exception as e:
                print(f"⚠ REST polling error: {e}")
        
        threading.Thread(target=poll, daemon=True).start()
        
        # Schedule next poll (3 seconds)
        self.root.after(3000, self.rest_poll_loop)

    def toggle_auto_send(self):
        """Bật/Tắt chế độ tự động gửi Discord khi có thay đổi"""
        self.auto_send_enabled = not self.auto_send_enabled
        if self.auto_send_enabled:
            self.toggle_btn.configure(text="AUTO SEND: ON", fg_color="#4CAF50")
            print("✓ Auto-send to Discord: ENABLED")
            # Disable editing khi đang ON
            self.webhook_entry.configure(state="disabled")
            self.prefix_entry.configure(state="disabled")
            # Lấy snapshot ban đầu
            self.previous_data = self.get_data_snapshot()
            print(f"📸 Đã lưu snapshot ban đầu: {len(self.previous_data)} items")
            # GỬI TOÀN BỘ LIST NGAY LẦN ĐẦU khi bật ON
            self.send_full_list_to_discord()
            # Bắt đầu auto-check (chỉ nếu không dùng WebSocket)
            if not self.ws_connected:
                self.check_for_changes()
        else:
            self.toggle_btn.configure(text="AUTO SEND: OFF", fg_color="#9E9E9E")
            print("✗ Auto-send to Discord: DISABLED")
            # Enable editing khi tắt OFF
            self.webhook_entry.configure(state="normal")
            self.prefix_entry.configure(state="normal")
    
    def get_data_snapshot(self):
        """Lấy snapshot của dữ liệu hiện tại - CHỈ các field quan trọng: name, port, status, ipwan, ip"""
        snapshot = []
        for entry in self.selected_data:
            d = entry.get("data", {})
            snapshot.append({
                "name": d.get("name", ""),
                "ip": d.get("ip", ""),
                "ipwan": d.get("ipwan", ""),
                "port": d.get("port", ""),
                "status": d.get("status", "")
            })
        # Sort để đảm bảo thứ tự nhất quán
        return sorted(snapshot, key=lambda x: (x["name"], x["port"]))
    
    def send_full_list_to_discord(self):
        """Gửi TOÀN BỘ list lên Discord khi bật AUTO SEND ON"""
        webhook = self.webhook_var.get().strip()
        if not webhook or not self.selected_data:
            print("⚠ Không có webhook hoặc selected data để gửi")
            return
        
        def send():
            try:
                prefix = self.prefix_var.get().strip()
                messages = []
                
                # Thêm tiêu đề
                now = datetime.now(VIETNAM_TZ)
                title = f"=== FULL STATUS LIST - {now.strftime('%d/%m/%Y %H:%M:%S')} ==="
                messages.append(title)
                
                # Gửi toàn bộ danh sách
                for entry in self.selected_data:
                    d = entry.get("data", {})
                    name = d.get("name", "")
                    ipwan = d.get("ipwan", "")
                    port = d.get("port", "")
                    status = d.get("status", "")
                    
                    msg = f"[{prefix}][{name}] SRT {status} | IPWAN: {ipwan} | PORT: {port}"
                    messages.append(msg)
                
                payload = {"content": "\n".join(messages)}
                
                resp = requests.post(webhook, json=payload, timeout=10)
                if resp.status_code in [200, 204]:
                    print(f"✓ Sent FULL LIST ({len(self.selected_data)} items) to Discord")
                else:
                    print(f"✗ Discord error: {resp.status_code}")
            except Exception as e:
                print(f"✗ Failed to send full list: {e}")
        
        threading.Thread(target=send, daemon=True).start()
    
    def check_for_changes(self):
        """Kiểm tra thay đổi và tự động gửi Discord - CHỈ monitor selected list, KHÔNG refresh bảng trái"""
        if not self.auto_send_enabled:
            return
        
        # Chỉ check status của selected items, không update bảng trái
        def check():
            url = f"{self.api_url}/logs"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        # dedupe incoming list before comparing
                        seen = set()
                        unique = []
                        for entry in data:
                            d = entry.get("data", {})
                            key = f"{d.get('ip','')}:{d.get('port','')}"
                            if key not in seen:
                                seen.add(key)
                                unique.append(entry)
                        data = unique

                        # if nothing actually changed we can skip entirely
                        if not self.has_data_changed(self.data, data):
                            return

                        self.data = data
                        # CHỈ update selected data và bảng phải, KHÔNG update bảng trái
                        self.update_selected_data()
                        self.update_selected_table()
                        
                        # So sánh với dữ liệu cũ
                        self.send_to_discord_auto()
            except Exception as e:
                print(f"Error checking: {e}")
        
        threading.Thread(target=check, daemon=True).start()
        
        # Schedule next check (5 seconds)
        if self.auto_send_enabled:
            self.root.after(5000, self.check_for_changes)
    
    def send_to_discord_auto(self):
        """Gửi CHỈ những item có thay đổi về SRT STATUS hoặc IPWAN lên Discord"""
        # Tránh gửi duplicate nếu đang trong quá trình gửi
        if self.is_sending:
            return
        
        webhook = self.webhook_var.get().strip()
        if not webhook or not self.selected_data:
            return
        
        # Lấy snapshot hiện tại
        current_snapshot = self.get_data_snapshot()
        
        # Nếu chưa có previous_data (lần đầu), chỉ lưu snapshot, không gửi
        if not self.previous_data:
            self.previous_data = current_snapshot
            return
        
        # So sánh với previous_data
        if current_snapshot == self.previous_data:
            return
        
        print(f"📊 DEBUG: Snapshot thay đổi! {len(current_snapshot)} items")
        for i, (c, p) in enumerate(zip(current_snapshot, self.previous_data)):
            if c != p:
                print(f"  Δ [{c.get('name','')}] status: {p.get('status','')} → {c.get('status','')}, ipwan: {p.get('ipwan','')} → {c.get('ipwan','')}")
        
        self.is_sending = True
        
        def send():
            try:
                prefix = self.prefix_var.get().strip()
                
                # Tạo dict để so sánh nhanh
                prev_dict = {f"{item['name']}:{item['port']}": item for item in self.previous_data}
                curr_dict = {f"{item['name']}:{item['port']}": item for item in current_snapshot}
                
                # Tìm những item có thay đổi về STATUS (SRT) hoặc IPWAN
                changed_items = []
                
                for key, curr_item in curr_dict.items():
                    prev_item = prev_dict.get(key)
                    
                    if prev_item:
                        status_changed = prev_item['status'] != curr_item['status']
                        ipwan_changed = prev_item['ipwan'] != curr_item['ipwan']
                        
                        if status_changed or ipwan_changed:
                            # Ghi nhận chi tiết thay đổi để hiển thị trong Discord message
                            change_info = {
                                **curr_item,
                                '_status_changed': status_changed,
                                '_ipwan_changed': ipwan_changed,
                                '_old_status': prev_item['status'],
                                '_old_ipwan': prev_item['ipwan'],
                            }
                            changed_items.append(change_info)
                            print(f"🔔 Thay đổi [{curr_item['name']}]: Status {prev_item['status']}→{curr_item['status']}, IPWAN {prev_item['ipwan']}→{curr_item['ipwan']}")
                    else:
                        # Item mới xuất hiện
                        change_info = {
                            **curr_item,
                            '_status_changed': True,
                            '_ipwan_changed': False,
                            '_old_status': '',
                            '_old_ipwan': '',
                        }
                        changed_items.append(change_info)
                
                # Gửi notification cho TẤT CẢ item có thay đổi (không lọc ipwan nữa)
                if changed_items:
                    messages = []
                    # Thêm tiêu đề với thời gian
                    now = datetime.now(VIETNAM_TZ)
                    title = f"=== STATUS CHANGED - {now.strftime('%d/%m/%Y %H:%M:%S')} ==="
                    messages.append(title)
                    
                    for item in changed_items:
                        name = item['name']
                        port = item['port']
                        status = item['status']
                        ipwan = item['ipwan']
                        
                        msg = f"[{prefix}][{name}] SRT {status} | IPWAN: {ipwan} | PORT: {port}"
                        messages.append(msg)
                    
                    payload = {"content": "\n".join(messages)}
                    resp = requests.post(webhook, json=payload, timeout=10)
                    if resp.status_code in [200, 204]:
                        print(f"✓ Sent {len(changed_items)} changed items to Discord")
                    else:
                        print(f"✗ Discord error: {resp.status_code}")
                
                # Luôn cập nhật previous_data
                self.previous_data = current_snapshot
                    
            except Exception as e:
                print(f"✗ Failed to send: {e}")
            finally:
                self.is_sending = False
        
        threading.Thread(target=send, daemon=True).start()

    def open_scan_dialog(self):
        """Open centered dialog that contains the All Logs table."""
        if self.scan_dialog is not None and self.scan_dialog.winfo_exists():
            self.scan_dialog.lift()
            self.scan_dialog.focus_force()
            self.refresh_data(show_dialog=False)
            return

        self.scan_dialog = ctk.CTkToplevel(self.root)
        self.scan_dialog.title("All Logs From Database")
        self.scan_dialog.transient(self.root)
        self.scan_dialog.grab_set()

        self.root.update_idletasks()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        # Keep scan dialog clearly smaller in both width and height
        dlg_w = min(850, max(620, int(root_w * 0.45)))
        dlg_h = min(460, max(460, int(root_h * 0.5)))
        x = self.root.winfo_x() + (root_w - dlg_w) // 2
        y = self.root.winfo_y() + (root_h - dlg_h) // 2
        self.scan_dialog.geometry(f"{dlg_w}x{dlg_h}+{x}+{y}")
        self.scan_dialog.minsize(620, 420)

        dialog_root = ctk.CTkFrame(self.scan_dialog)
        dialog_root.pack(fill="both", expand=True, padx=10, pady=10)

        top_bar = ctk.CTkFrame(dialog_root, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(top_bar, text="📡 ALL LOGS FROM DATABASE", font=("Arial", 12, "bold")).pack(side="left")
        ctk.CTkButton(top_bar, text="Refresh", width=90, command=lambda: self.refresh_data(show_dialog=False),
                      fg_color="#4CAF50", hover_color="#45a049").pack(side="right", padx=4)
        ctk.CTkButton(top_bar, text="Add Selected", width=110, command=self.add_to_selected,
                      fg_color="#2196F3", hover_color="#1976D2").pack(side="right", padx=4)

        self.table_frame_left = ctk.CTkScrollableFrame(dialog_root, fg_color="#2b2b2b")
        self.table_frame_left.pack(fill="both", expand=True)

        header_frame = ctk.CTkFrame(self.table_frame_left, fg_color="#1a1a1a", height=40)
        header_frame.pack(fill="x", pady=(0, 5))
        header_frame.pack_propagate(False)

        self.select_all_var.set(False)
        self.select_all_cb = ctk.CTkCheckBox(header_frame, text="", variable=self.select_all_var,
                                             width=35, command=self.toggle_select_all)
        self.select_all_cb.pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="STT", font=("Arial", 11, "bold"), width=35).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="TÊN MÁY", font=("Arial", 11, "bold"), width=140).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="IP MÁY", font=("Arial", 11, "bold"), width=130).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="PORT", font=("Arial", 11, "bold"), width=80).pack(side="left", padx=2)

        self.scan_dialog.protocol("WM_DELETE_WINDOW", self._close_scan_dialog)

        self.update_all_table()
        self.refresh_data(show_dialog=False)

    def _close_scan_dialog(self):
        if self.scan_dialog is not None and self.scan_dialog.winfo_exists():
            self.scan_dialog.destroy()
        self.scan_dialog = None
        self.table_frame_left = None
        self.select_all_var.set(False)
        self.select_all_cb = None
        self.left_table_rows = []
        self.left_table_checkboxes = {}

    def refresh_data(self, show_dialog=True):
        """Refresh all logs from database."""
        if show_dialog:
            self.open_scan_dialog()
            return

        def fetch():
            url = f"{self.api_url}/logs"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, list):
                            # dedupe fetched list
                            seen = set()
                            unique = []
                            for entry in data:
                                d = entry.get("data", {})
                                # Use name and ip for unique key as port is now in array
                                key = d.get("name", d.get("ip", "")) or d.get("ip", "")
                                if key not in seen:
                                    seen.add(key)
                                    unique.append(entry)
                            data = unique
                            # So sánh data mới với data cũ
                            if self.has_data_changed(self.data, data):
                                print("✓ Data changed, refreshing table...")
                                self.data = data
                                self.root.after(0, self.update_all_table)
                                # Also update selected data with new info
                                self.update_selected_data()
                                self.root.after(0, self.update_selected_table)
                            else:
                                # Chỉ update selected table (để cập nhật status realtime)
                                self.update_selected_data()
                                self.root.after(0, self.update_selected_table)
                        else:
                            self.data = []
                    except Exception as e:
                        self.root.after(0, lambda: messagebox.showerror("Error", f"JSON decode error: {e}"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"HTTP {resp.status_code}: {resp.text}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"ERROR: {str(e)}"))
        threading.Thread(target=fetch, daemon=True).start()
    
    def has_data_changed(self, old_data, new_data):
        def build_set(data_list):
            s = set()
            for entry in data_list:
                d = entry.get("data", {})
                key = d.get("name", d.get("ip", "")) or d.get("ip", "")
                s.add(key)
            return s
        old_set = build_set(old_data)
        new_set = build_set(new_data)
        return old_set != new_set

    def update_all_table(self):
        """Update left table with all logs - Custom view with checkboxes"""
        if self.table_frame_left is None or not self.table_frame_left.winfo_exists():
            self.left_table_rows = []
            self.left_table_checkboxes = {}
            return

        # Clear old rows
        for row in self.left_table_rows:
            row.destroy()
        self.left_table_rows = []
        self.left_table_checkboxes = {}
        self.select_all_var.set(False)
        
        stt = 1
        for idx, entry in enumerate(self.data):
            d = entry.get("data", {})
            srt = get_first_srt(d)
            name = d.get("name", "").strip()
            ip = d.get("ip", "")
            port = get_srt_ports_str(d) or d.get("port", "")
            statusapp = d.get("statusapp", 0)
            
            # Create row frame
            row_frame = ctk.CTkFrame(self.table_frame_left, 
                                     fg_color="#3a3a3a" if stt % 2 == 0 else "#2b2b2b", 
                                     height=35)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)
            
            # Checkbox
            is_selected = self.is_in_selected(entry)
            checkbox_var = ctk.BooleanVar(value=is_selected)
            checkbox = ctk.CTkCheckBox(row_frame, text="", variable=checkbox_var, width=35,
                                       command=lambda e=entry, v=checkbox_var: self.on_checkbox_toggle(e, v))
            checkbox.pack(side="left", padx=2)
            self.left_table_checkboxes[idx] = (checkbox, checkbox_var, entry)
            
            # STT
            stt_label = ctk.CTkLabel(row_frame, text=str(stt), font=("Arial", 11, "bold"), width=35, anchor="center")
            stt_label.pack(side="left", padx=2)
            
            # TÊN MÁY
            name_label = ctk.CTkLabel(row_frame, text=name or "—", font=("Arial", 11, "bold"), width=140, anchor="center", text_color="#90CAF9")
            name_label.pack(side="left", padx=2)
            
            # IP
            ip_color = "#4CAF50" if statusapp == 1 else "#f44336"
            ip_label = ctk.CTkLabel(row_frame, text=ip, font=("Arial", 11, "bold"), width=110, text_color=ip_color, anchor="center")
            ip_label.pack(side="left", padx=2)
            
            # Port
            port_label = ctk.CTkLabel(row_frame, text=port, font=("Arial", 11, "bold"), width=60, anchor="center")
            port_label.pack(side="left", padx=2)
            
            # Bind click event for details (only on labels, not checkbox)
            for widget in [row_frame, stt_label, name_label, ip_label]:
                widget.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))
            
            self.left_table_rows.append(row_frame)
            stt += 1

    def update_selected_table(self):
        """Update right table with selected logs - Custom view"""
        # Clear old rows
        for row in self.right_table_rows:
            row.destroy()
        self.right_table_rows = []
        
        stt = 1
        for entry in self.selected_data:
            ts = pretty_time(entry.get("timestamp", ""))
            d = entry.get("data", {})
            name = d.get("name", "").strip() or f"MÁY {stt}"
            ip          = d.get("ip", "")
            ipwan       = d.get("ipwan", "")
            statusapp   = d.get("statusapp", 0)
            statusapp_text = "ON" if statusapp == 1 else "OFF"
            
            # Extract SRT streams
            srt_list = d.get("SRT", [])
            if isinstance(srt_list, dict): srt_list = [srt_list]
            if not isinstance(srt_list, list): srt_list = []
            
            # PTZ fallback
            if d.get("ptz", False) or not srt_list:
                srt_rows = [{
                    "status": d.get("status", "—"),
                    "port": d.get("port", "—"),
                    "name": "—",
                    "quality": d.get("srt_quality", "—") or "—",
                    "color": "#4CAF50" if d.get("status") == "ON" else "#f44336"
                }]
            else:
                srt_rows = []
                for s in srt_list:
                    if not isinstance(s, dict): continue
                    st = s.get("status", "—")
                    q = s.get("quality", "")
                    sn = s.get("nameSRT", "")
                    sp = s.get("port", "")
                    srt_rows.append({
                        "status": st,
                        "port": str(sp),
                        "name": sn or "—",
                        "quality": q or "—",
                        "color": "#4CAF50" if st == "ON" else "#f44336"
                    })

            # Calculate row height based on number of SRT streams
            row_h = max(40, len(srt_rows) * 22 + 10)
            
            # Create row frame
            row_frame = ctk.CTkFrame(self.table_frame_right,
                                     fg_color="#3a3a3a" if stt % 2 == 0 else "#2b2b2b",
                                     height=row_h)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)
            
            # Helper to create vertically centered cells
            def create_cell(parent, width, expand=False):
                f = ctk.CTkFrame(parent, fg_color="transparent", width=width)
                f.pack(side="left", padx=2, fill="both", expand=expand)
                f.pack_propagate(False)
                return f

            # STT
            c = create_cell(row_frame, 35)
            ctk.CTkLabel(c, text=str(stt), font=("Arial", 10, "bold")).place(relx=0.5, rely=0.5, anchor="center")
            
            # Name
            c = create_cell(row_frame, 110)
            name_lbl = ctk.CTkLabel(c, text=name, font=("Arial", 10, "bold"), wraplength=100)
            name_lbl.place(relx=0.5, rely=0.5, anchor="center")
            name_lbl.bind("<Double-1>", lambda e, idx=stt-1, frame=c, lbl=name_lbl: self.edit_name_inline(idx, frame, lbl))
            
            # IPs
            c = create_cell(row_frame, 110)
            ctk.CTkLabel(c, text=ip, font=("Arial", 10)).place(relx=0.5, rely=0.5, anchor="center")
            c = create_cell(row_frame, 110)
            ctk.CTkLabel(c, text=ipwan, font=("Arial", 10)).place(relx=0.5, rely=0.5, anchor="center")

            # --- SRT MULTI-ROW SECTION ---
            # To center multiple packed rows vertically, we pack them into an inner frame 
            # and then 'place' that frame in the middle of the cell.
            def create_centered_srt_container(parent):
                inner = ctk.CTkFrame(parent, fg_color="transparent")
                inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0)
                return inner

            # Status
            c_status = create_cell(row_frame, 70)
            inner_status = create_centered_srt_container(c_status)
            
            # Port
            c_port = create_cell(row_frame, 60)
            inner_port = create_centered_srt_container(c_port)
            
            # Name SRT
            c_name_srt = create_cell(row_frame, 100)
            inner_name_srt = create_centered_srt_container(c_name_srt)
            
            # Quality
            c_quality = create_cell(row_frame, 180)
            inner_quality = create_centered_srt_container(c_quality)
            
            for s_info in srt_rows:
                ctk.CTkLabel(inner_status, text=s_info["status"], font=("Arial", 9, "bold"), text_color=s_info["color"], anchor="center").pack(fill="x")
                ctk.CTkLabel(inner_port, text=s_info["port"], font=("Arial", 9), anchor="center").pack(fill="x")
                ctk.CTkLabel(inner_name_srt, text=s_info["name"], font=("Arial", 9, "bold"), text_color="#90CAF9", anchor="center").pack(fill="x")
                ctk.CTkLabel(inner_quality, text=s_info["quality"], font=("Arial", 9), text_color=s_info["color"], anchor="center").pack(fill="x")

            # App Status
            app_color = "#4CAF50" if statusapp == 1 else "#f44336"
            c = create_cell(row_frame, 45)
            ctk.CTkLabel(c, text=statusapp_text, font=("Arial", 10, "bold"), text_color=app_color).place(relx=0.5, rely=0.5, anchor="center")
            
            # Stats (Ping, CPU, RAM)
            ping         = d.get("ping", None)
            ping_timeouts= d.get("ping_timeouts", 0)
            cpu          = d.get("cpu", None)
            memory       = d.get("memory", None)
            ping_str     = f"{ping:.0f} ms" if ping is not None else "—"
            timeout_str  = str(ping_timeouts) if ping_timeouts is not None else "0"
            cpu_str      = f"{cpu:.1f}%"   if cpu    is not None else "—"
            mem_str      = f"{memory:.1f}%" if memory is not None else "—"
            
            c = create_cell(row_frame, 70)
            ctk.CTkLabel(c, text=ping_str, font=("Arial", 10), text_color="#4CAF50" if ping else "#9E9E9E").place(relx=0.5, rely=0.5, anchor="center")
            c = create_cell(row_frame, 70)
            ctk.CTkLabel(c, text=timeout_str, font=("Arial", 10, "bold"), text_color="#f44336" if ping_timeouts else "#9E9E9E").place(relx=0.5, rely=0.5, anchor="center")
            c = create_cell(row_frame, 65)
            ctk.CTkLabel(c, text=cpu_str, font=("Arial", 10)).place(relx=0.5, rely=0.5, anchor="center")
            c = create_cell(row_frame, 65)
            ctk.CTkLabel(c, text=mem_str, font=("Arial", 10)).place(relx=0.5, rely=0.5, anchor="center")

            # vMix Flags
            vmix_rec     = d.get("vmix_recording", False)
            vmix_live    = d.get("vmix_streaming", False)
            vmix_ext     = d.get("vmix_external",  False)
            res          = d.get("resolution", "—") or "—"
            
            c = create_cell(row_frame, 60)
            ctk.CTkLabel(c, text="● ON" if vmix_rec else "○ OFF", font=("Arial", 9), text_color="#f44336" if vmix_rec else "#555555").place(relx=0.5, rely=0.5, anchor="center")
            c = create_cell(row_frame, 60)
            ctk.CTkLabel(c, text="● ON" if vmix_live else "○ OFF", font=("Arial", 9), text_color="#f44336" if vmix_live else "#555555").place(relx=0.5, rely=0.5, anchor="center")
            c = create_cell(row_frame, 60)
            ctk.CTkLabel(c, text="● ON" if vmix_ext else "○ OFF", font=("Arial", 9), text_color="#4CAF50" if vmix_ext else "#555555").place(relx=0.5, rely=0.5, anchor="center")
            c = create_cell(row_frame, 90)
            ctk.CTkLabel(c, text=res, font=("Arial", 9, "bold"), text_color="#4CAF50").place(relx=0.5, rely=0.5, anchor="center")
            
            # Time
            c = create_cell(row_frame, 130)
            ctk.CTkLabel(c, text=ts, font=("Arial", 9)).place(relx=0.5, rely=0.5, anchor="center")
            
            # Delete button
            delete_btn = ctk.CTkButton(row_frame, text="❌", width=30, height=30, fg_color="#f44336", hover_color="#d32f2f",
                                       command=lambda idx=stt-1: self.remove_single_item(idx))
            delete_btn.pack(side="right", padx=5)
            
            # Bind click cho cả frame background
            row_frame.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))
            
            self.right_table_rows.append(row_frame)
            stt += 1

    def is_in_selected(self, entry):
        """Check if entry is in selected list - Check by Name or IP"""
        d = entry.get("data", {})
        name = d.get("name", "")
        ip = d.get("ip", "")
        for sel in self.selected_data:
            sel_d = sel.get("data", {})
            if name and sel_d.get("name") == name:
                return True
            if ip and sel_d.get("ip") == ip:
                return True
        return False

    def toggle_select_all(self):
        """Select / deselect all checkboxes in the left table"""
        if not self.left_table_checkboxes:
            return
        state = self.select_all_var.get()
        for idx, (checkbox, var, entry) in self.left_table_checkboxes.items():
            var.set(state)

    def on_checkbox_toggle(self, entry, checkbox_var):
        """Handle checkbox toggle - recalculate select-all state"""
        all_checked = all(var.get() for _, var, _ in self.left_table_checkboxes.values())
        self.select_all_var.set(all_checked)
    
    def edit_name_inline(self, idx, frame, label):
        """Edit name inline - tại chỗ"""
        if idx >= len(self.selected_data):
            return
        
        old_name = label.cget("text")
        
        # Hide label
        label.pack_forget()
        
        # Create entry
        entry_widget = ctk.CTkEntry(frame, font=("Arial", 12, "bold"))
        entry_widget.insert(0, old_name)
        entry_widget.pack(fill="both", expand=True)
        entry_widget.focus_set()
        entry_widget.select_range(0, "end")
        
        def save_name(event=None):
            new_name = entry_widget.get().strip()
            
            if new_name and new_name != old_name:
                old_ip = self.selected_data[idx].get("data", {}).get("ip", "")
                self.selected_data[idx]["data"]["name"] = new_name
                
                # Update to server
                def update_name():
                    try:
                        update_data = {
                            "old_name": old_name,
                            "new_name": new_name,
                            "ip": old_ip
                        }
                        resp = requests.post(f"{self.api_url}/update_name", json=update_data, timeout=5)
                        if resp.status_code == 200:
                            print(f"✓ Updated: {old_name} → {new_name}")
                        else:
                            print(f"✗ Update error: {resp.status_code}")
                    except Exception as e:
                        print(f"✗ Error: {e}")
                
                threading.Thread(target=update_name, daemon=True).start()
            
            # Restore label
            entry_widget.destroy()
            label.configure(text=new_name if new_name else old_name)
            label.pack(fill="both", expand=True)
        
        def cancel_edit(event=None):
            entry_widget.destroy()
            label.pack(fill="both", expand=True)
        
        # Bind events
        entry_widget.bind("<Return>", save_name)
        entry_widget.bind("<FocusOut>", save_name)
        entry_widget.bind("<Escape>", cancel_edit)
    
    def add_to_selected(self, event=None):
        """Add checked items to selected list"""
        added_count = 0
        print(f"\n=== ADD TO SELECTED DEBUG ===")
        print(f"Total checkboxes: {len(self.left_table_checkboxes)}")
        
        for idx, (checkbox, var, entry) in self.left_table_checkboxes.items():
            ip = entry.get("data", {}).get("ip", "")
            port = entry.get("data", {}).get("port", "")
            is_checked = var.get()
            already_in = self.is_in_selected(entry)
            print(f"  [{idx}] IP:{ip} Port:{port} - Checked:{is_checked} AlreadyIn:{already_in}")
            
            if is_checked and not already_in:
                self.selected_data.append(entry)
                added_count += 1
                print(f"    → ADDED!")
        # Remove duplicates (unique IP+PORT only)
        unique = {}
        for entry in self.selected_data:
            d = entry.get("data", {})
            key = f"{d.get('ip','')}:{d.get('port','')}"
            if key not in unique:
                unique[key] = entry
        self.selected_data = list(unique.values())
        print(f"Total added: {added_count}")
        if added_count > 0:
            print(f"✓ Successfully added: {added_count} item(s)")
            self.save_selected_to_database()  # Lưu vào database
            self.update_all_table()  # Refresh to update checkbox states
            self.update_selected_table()
        else:
            messagebox.showinfo("Info", "No new items to add. Check the boxes first!")

    def remove_single_item(self, idx):
        """Remove single item from selected list (không xóa khỏi database)"""
        if idx < len(self.selected_data):
            removed = self.selected_data.pop(idx)
            rd = removed.get('data', {})
            print(f"✗ Removed: {rd.get('name', 'Unknown')}")
            # Nếu là PTZ, stop ping thread
            if rd.get('ptz', False):
                ptz_key = f"{rd.get('name','')}:{rd.get('port','')}"
                self._stop_ptz_ping(ptz_key)
            # Không xóa khỏi database, chỉ update selected_data
            self.update_all_table()
            self.update_selected_table()
    
    def remove_from_selected(self):
        """Remove all selected items (không xóa khỏi database)"""
        if not self.selected_data:
            messagebox.showwarning("Warning", "No items in the selected list")
            return
        result = messagebox.askyesno("Confirm", f"Remove all {len(self.selected_data)} items?")
        if result:
            self.selected_data = []
            # Không xóa khỏi database, chỉ update UI
            self.update_all_table()
            self.update_selected_table()
            print("✓ Cleared all selected items")
    
    def edit_name_dialog(self, idx):
        """Edit name via dialog"""
        if idx >= len(self.selected_data):
            return
        
        old_name = self.selected_data[idx].get("data", {}).get("name", "")
        
        dialog = ctk.CTkInputDialog(text=f"Edit name for {self.selected_data[idx].get('data', {}).get('ip', '')}:",
                                     title="Edit Name")
        new_name = dialog.get_input()
        
        if new_name and new_name.strip() and new_name != old_name:
            old_ip = self.selected_data[idx].get("data", {}).get("ip", "")
            self.selected_data[idx]["data"]["name"] = new_name.strip()
            
            # Update to server
            def update_name():
                try:
                    update_data = {
                        "old_name": old_name,
                        "new_name": new_name.strip(),
                        "ip": old_ip
                    }
                    resp = requests.post(f"{self.api_url}/update_name", json=update_data, timeout=5)
                    if resp.status_code == 200:
                        print(f"✓ Updated: {old_name} → {new_name}")
                        self.refresh_data(show_dialog=False)
                    else:
                        print(f"✗ Update error: {resp.status_code}")
                except Exception as e:
                    print(f"✗ Error: {e}")
            
            threading.Thread(target=update_name, daemon=True).start()
            self.update_selected_table()

    # ── Debug File Logging ───────────────────────────────────────────────

    def _write_ptz_log(self, name, ms_or_timeout, status_changed=False, new_status=None):
        """Ghi log PTZ đơn giản: [HH:MM:SS] - 30ms  hoặc  [HH:MM:SS] - timeout"""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            today = datetime.now(VIETNAM_TZ).strftime("%d-%m-%Y")
            debug_dir = os.path.join(desktop, f"Debug {today}")
            os.makedirs(debug_dir, exist_ok=True)

            now_str = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")

            safe_name = "".join(c for c in name if c.isalnum() or c in " _-.").strip() or "unknown"

            # Ghi vào file riêng của PTZ
            fpath = os.path.join(debug_dir, f"{safe_name}.txt")
            result_str = f"{ms_or_timeout}ms" if isinstance(ms_or_timeout, (int, float)) else "timeout"
            line = f"[{now_str}] - {result_str}\n"
            with open(fpath, "a", encoding="utf-8") as f:
                f.write(line)

            # Ghi vào error.txt chung khi status thay đổi ON↔OFF
            if status_changed and new_status in ("ON", "OFF"):
                epath = os.path.join(debug_dir, "error.txt")
                err_line = f"[{now_str}] [{name}] - {new_status}  ({result_str})\n"
                with open(epath, "a", encoding="utf-8") as f:
                    f.write(err_line)
        except Exception as e:
            print(f"⚠ PTZ log write error: {e}")

    def _write_debug_log(self, name, d, is_error=False):
        """Ghi log vào Desktop/Debug DD-MM-YYYY/{name}.txt hoặc error.txt (chung)"""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            today = datetime.now(VIETNAM_TZ).strftime("%d-%m-%Y")
            debug_dir = os.path.join(desktop, f"Debug {today}")
            os.makedirs(debug_dir, exist_ok=True)

            if is_error:
                # Tất cả error ghi vào 1 file chung
                fpath = os.path.join(debug_dir, "error.txt")
            else:
                # Mỗi máy 1 file riêng
                safe_name = "".join(c for c in name if c.isalnum() or c in " _-.").strip()
                if not safe_name:
                    safe_name = "unknown"
                fpath = os.path.join(debug_dir, f"{safe_name}.txt")

            now_str = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")

            ping_val = d.get('ping', None)
            ping_s   = f"{ping_val:.0f}ms" if ping_val is not None else "—"
            cpu_val  = d.get('cpu', None)
            cpu_s    = f"{cpu_val:.1f}%" if cpu_val is not None else "—"
            mem_val  = d.get('memory', None)
            mem_s    = f"{mem_val:.1f}%" if mem_val is not None else "—"
            temp_val = d.get('temperature', None)
            temp_s   = f"{temp_val}°C" if temp_val is not None else "—"
            app_s    = "ON" if d.get('statusapp', 0) == 1 else "OFF"

            parts = [
                f"ip: {d.get('ip','')}  ",
                f"ipwan: {d.get('ipwan','')}  ",
                f"status: {d.get('status','')}  ",
                f"port: {d.get('port','')}  ",
                f"app: {app_s}  ",
                f"ping: {ping_s}  ",
                f"timeouts: {d.get('ping_timeouts', 0)}  ",
                f"cpu: {cpu_s}  ",
                f"ram: {mem_s}  ",
                f"temp: {temp_s}",
            ]
            if is_error:
                line = f"[{now_str}] [{name}] - " + "".join(parts) + "\n"
            else:
                line = f"[{now_str}] - " + "".join(parts) + "\n"

            with open(fpath, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            print(f"⚠ Log write error: {e}")

    # ─────────────────────────────────────────────────────────────────────────

    def update_selected_data(self):
        """Update selected data with latest info from database - Match by NAME or PORT"""
        for i, sel_entry in enumerate(self.selected_data):
            sel_d = sel_entry.get("data", {})
            
            # Skip PTZ entries - chúng được quản lý riêng bởi ping thread
            if sel_d.get("ptz", False):
                continue
            
            sel_name = sel_d.get("name", "")
            sel_port = sel_d.get("port", "")
            
            # Tìm matching entry: ưu tiên match theo NAME (nếu có), không thì match theo PORT
            matched = False
            for entry in self.data:
                entry_d = entry.get("data", {})
                entry_name = entry_d.get("name", "")
                entry_port = entry_d.get("port", "")
                
                # Match theo NAME nếu có và không rỗng
                if sel_name and entry_name and sel_name == entry_name:
                    # Update toàn bộ thông tin (bao gồm IP, IPWAN mới)
                    self.selected_data[i] = entry
                    matched = True
                    break
                # Nếu không có name, match theo PORT
                elif not sel_name and sel_port and sel_port == entry_port:
                    self.selected_data[i] = entry
                    matched = True
                    break
            
            if matched:
                new_d = self.selected_data[i].get("data", {})
                disp_name = new_d.get("name", "") or sel_name
                old_status = sel_d.get("status", "")
                new_status = new_d.get("status", "")
                status_changed = (old_status != new_status
                                  and new_status in ("ON", "OFF")
                                  and old_status in ("ON", "OFF"))
                # Ghi regular log: mỗi 5 giây HOẶC khi status thay đổi
                now_ts = time.time()
                since_last = now_ts - self._log_last_write.get(disp_name, 0)
                if since_last >= 5 or status_changed:
                    self._log_last_write[disp_name] = now_ts
                    threading.Thread(target=self._write_debug_log,
                                     args=(disp_name, new_d, False), daemon=True).start()
                # Ghi error log CHỈ khi status thay đổi ON↔OFF
                if status_changed:
                    threading.Thread(target=self._write_debug_log,
                                     args=(disp_name, new_d, True), daemon=True).start()

    def clear_selected(self):
        """Clear selected list"""
        self._stop_all_ptz_pings()  # Stop tất cả PTZ ping threads
        self.selected_data = []
        self.save_selected_to_database()  # Lưu vào database (rỗng)
        self.update_selected_table()
        self.update_all_table()
        self.detail_text.delete("1.0", "end")

    def add_ptz_manual(self):
        """Mở dialog để thêm PTZ thủ công (tên, IP, port, IPWAN)"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("➕ Add PTZ")
        dialog.geometry("400x280")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 140
        dialog.geometry(f"400x280+{x}+{y}")
        
        ctk.CTkLabel(dialog, text="➕ THÊM PTZ THỦ CÔNG", font=("Arial", 14, "bold")).pack(pady=(15, 10))
        
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        form_frame.pack(fill="x", padx=20, pady=5)
        
        # Tên
        ctk.CTkLabel(form_frame, text="Tên:", font=("Arial", 11, "bold"), width=80, anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        name_entry = ctk.CTkEntry(form_frame, width=250, font=("Arial", 11), placeholder_text="VD: PTZ CAM 1")
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # IP
        ctk.CTkLabel(form_frame, text="IP:", font=("Arial", 11, "bold"), width=80, anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ip_entry = ctk.CTkEntry(form_frame, width=250, font=("Arial", 11), placeholder_text="VD: 192.168.1.100")
        ip_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Port
        ctk.CTkLabel(form_frame, text="Port:", font=("Arial", 11, "bold"), width=80, anchor="w").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        port_entry = ctk.CTkEntry(form_frame, width=250, font=("Arial", 11), placeholder_text="VD: 9000")
        port_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # IPWAN
        ctk.CTkLabel(form_frame, text="IP WAN:", font=("Arial", 11, "bold"), width=80, anchor="w").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ipwan_entry = ctk.CTkEntry(form_frame, width=250, font=("Arial", 11), placeholder_text="VD: 1.2.3.4")
        ipwan_entry.grid(row=3, column=1, padx=5, pady=5)
        
        def on_add():
            name = name_entry.get().strip()
            ip = ip_entry.get().strip()
            port = port_entry.get().strip()
            ipwan = ipwan_entry.get().strip()
            
            if not name:
                messagebox.showwarning("Warning", "Vui lòng nhập tên!", parent=dialog)
                return
            if not port:
                messagebox.showwarning("Warning", "Vui lòng nhập port!", parent=dialog)
                return
            
            # Tạo entry giống format data từ server
            now = datetime.now(VIETNAM_TZ).isoformat()
            ptz_entry = {
                "timestamp": now,
                "data": {
                    "name": name,
                    "ip": ip,
                    "ipwan": ipwan,
                    "status": "",
                    "port": port,
                    "statusapp": 0,
                    "ptz": True  # Đánh dấu là PTZ thủ công
                }
            }
            
            # Check trùng
            for sel in self.selected_data:
                sel_d = sel.get("data", {})
                if sel_d.get("name", "") == name and sel_d.get("port", "") == port:
                    messagebox.showwarning("Warning", f"PTZ [{name}] port [{port}] đã tồn tại!", parent=dialog)
                    return
            
            self.selected_data.append(ptz_entry)
            self.update_selected_table()
            # Start ping thread cho PTZ
            ptz_key = f"{name}:{port}"
            self._start_ptz_ping(ptz_key)
            print(f"✓ Added PTZ: [{name}] IP:{ip} IPWAN:{ipwan} PORT:{port}")
            dialog.destroy()
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="✅ Thêm", command=on_add, fg_color="#4CAF50", hover_color="#45a049", width=120, font=("Arial", 11, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="❌ Hủy", command=dialog.destroy, fg_color="#f44336", hover_color="#d32f2f", width=120, font=("Arial", 11, "bold")).pack(side="left", padx=10)
        
        name_entry.focus_set()

    def _start_ptz_ping(self, ptz_key):
        """Start ping thread cho một PTZ entry"""
        if ptz_key in self.ptz_ping_threads:
            return  # Đã có thread chạy rồi
        
        self.ptz_ping_threads[ptz_key] = {"running": True}
        t = threading.Thread(target=self._ptz_ping_loop, args=(ptz_key,), daemon=True)
        self.ptz_ping_threads[ptz_key]["thread"] = t
        t.start()
        print(f"📡 Started PTZ ping for [{ptz_key}]")

    def _stop_ptz_ping(self, ptz_key):
        """Stop ping thread cho một PTZ entry"""
        if ptz_key in self.ptz_ping_threads:
            self.ptz_ping_threads[ptz_key]["running"] = False
            del self.ptz_ping_threads[ptz_key]
            print(f"⏹ Stopped PTZ ping for [{ptz_key}]")

    def _stop_all_ptz_pings(self):
        """Stop tất cả PTZ ping threads"""
        for key in list(self.ptz_ping_threads.keys()):
            self.ptz_ping_threads[key]["running"] = False
        self.ptz_ping_threads.clear()
        print("⏹ Stopped all PTZ pings")

    def _ptz_ping_loop(self, ptz_key):
        """Background thread: ping IP của PTZ và cập nhật status ON/OFF"""
        while ptz_key in self.ptz_ping_threads and self.ptz_ping_threads[ptz_key]["running"]:
            try:
                # Tìm PTZ entry trong selected_data
                ptz_entry = None
                ptz_idx = None
                for i, entry in enumerate(self.selected_data):
                    d = entry.get("data", {})
                    if d.get("ptz", False) and f"{d.get('name','')}:{d.get('port','')}" == ptz_key:
                        ptz_entry = entry
                        ptz_idx = i
                        break
                
                if ptz_entry is None:
                    break  # PTZ đã bị xóa
                
                ip = ptz_entry.get("data", {}).get("ip", "")
                if not ip:
                    time.sleep(5)
                    continue
                
                # Ping IP
                result = subprocess.run(
                    ["ping", "-n", "1", "-w", "2000", ip],
                    capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                try:
                    output = result.stdout.decode('cp1252', errors='ignore')
                except Exception:
                    output = result.stdout.decode('utf-8', errors='ignore')
                
                is_up = "ttl=" in output.lower()
                new_status = "ON" if is_up else "OFF"
                old_status = ptz_entry.get("data", {}).get("status", "")
                status_changed = (new_status != old_status
                                  and old_status in ("ON", "OFF")
                                  and new_status in ("ON", "OFF"))

                # Parse ms từ output ping
                ms_match = re.search(r"time[=<](\d+)", output, re.IGNORECASE)
                ping_ms = int(ms_match.group(1)) if ms_match else None

                # Cập nhật status nếu thay đổi
                if new_status != old_status:
                    self.selected_data[ptz_idx]["data"]["status"] = new_status
                    print(f"📡 PTZ [{ptz_key}] status: {old_status or '—'} → {new_status}")
                    # Refresh table trên UI thread
                    self.root.after(0, self.update_selected_table)
                    # Trigger Discord notification nếu auto_send đang bật
                    if self.auto_send_enabled:
                        self.root.after(100, self.send_to_discord_auto)

                # Ghi PTZ log đơn giản mỗi vòng (5 giây)
                ptz_name = ptz_entry.get("data", {}).get("name", ptz_key)
                log_val = ping_ms if is_up else "timeout"
                threading.Thread(target=self._write_ptz_log,
                                 args=(ptz_name, log_val, status_changed, new_status),
                                 daemon=True).start()
                
            except Exception as e:
                print(f"⚠ PTZ ping error [{ptz_key}]: {e}")
            
            time.sleep(5)  # Ping mỗi 5 giây

    def save_selected_to_file(self):
        """Save selected list, webhook, prefix, vmping hosts, and PTZ entries to JSON file"""
        # Collect vmping hosts (just the hostnames/ips)
        vmping_list = list(self.ping_hosts.keys()) if hasattr(self, 'ping_hosts') else []
        
        # Collect PTZ entries từ selected_data
        ptz_list = []
        for entry in self.selected_data:
            d = entry.get("data", {})
            if d.get("ptz", False):  # Chỉ lưu items có flag ptz=True
                ptz_list.append({
                    "name": d.get("name", ""),
                    "ip": d.get("ip", ""),
                    "port": d.get("port", ""),
                    "ipwan": d.get("ipwan", "")
                })
        
        data_to_save = {
            "webhook": self.webhook_var.get(),
            "prefix": self.prefix_var.get(),
            "vmping": vmping_list,
            "ptz": ptz_list
        }
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="selected_monitors.json"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Success", f"Saved monitor config to:\n{filename}")
                print(f"✓ Saved monitor config to: {filename} (including {len(ptz_list)} PTZ entries)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
                print(f"✗ Save error: {e}")

    def load_selected_from_file(self):
        """Load config (webhook, prefix, vmping, ptz) from JSON file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Open Monitor Config"
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                if not isinstance(loaded_data, dict):
                    messagebox.showerror("Error", "Invalid file format. Expected a JSON object.")
                    return
                # Set webhook
                if 'webhook' in loaded_data:
                    self.webhook_var.set(loaded_data['webhook'])
                # Set prefix
                if 'prefix' in loaded_data:
                    self.prefix_var.set(loaded_data['prefix'])
                # Set vmping hosts
                if 'vmping' in loaded_data and isinstance(loaded_data['vmping'], list):
                    # Clear all current ping hosts
                    self.clear_all_pings()
                    # Add hosts from file
                    for host in loaded_data['vmping']:
                        if host:
                            self._create_ping_card(host)
                    self.start_all_pings()
                    self.ping_count_label.configure(text=f"{len(self.ping_hosts)} monitors")
                # Load PTZ entries
                ptz_count = 0
                if 'ptz' in loaded_data and isinstance(loaded_data['ptz'], list):
                    now = datetime.now(VIETNAM_TZ).isoformat()
                    for ptz in loaded_data['ptz']:
                        name = ptz.get('name', '')
                        port = ptz.get('port', '')
                        # Check trùng trong selected_data
                        already_exists = False
                        for sel in self.selected_data:
                            sel_d = sel.get("data", {})
                            if sel_d.get("name", "") == name and sel_d.get("port", "") == port:
                                already_exists = True
                                break
                        if not already_exists:
                            ptz_entry = {
                                "timestamp": now,
                                "data": {
                                    "name": name,
                                    "ip": ptz.get('ip', ''),
                                    "ipwan": ptz.get('ipwan', ''),
                                    "status": "",
                                    "port": port,
                                    "statusapp": 0,
                                    "ptz": True
                                }
                            }
                            self.selected_data.append(ptz_entry)
                            ptz_count += 1
                            # Start ping thread cho PTZ
                            self._start_ptz_ping(f"{name}:{port}")
                    self.update_selected_table()
                    if ptz_count > 0:
                        print(f"✓ Loaded {ptz_count} PTZ entries from file")
                messagebox.showinfo("Success", f"Loaded config from:\n{filename}")
                print(f"✓ Loaded config from: {filename}")
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON file:\n{str(e)}")
                print(f"✗ JSON decode error: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
                print(f"✗ Load error: {e}")

    def save_selected_to_database(self):
        """Đồng bộ selected list lên database"""
        def save():
            try:
                url = f"{self.api_url}/save_selected_list"
                payload = {"selected_data": self.selected_data}
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    print(f"✓ Saved {len(self.selected_data)} items to database")
                else:
                    print(f"✗ Save error: {resp.status_code}")
            except Exception as e:
                print(f"✗ Failed to save to database: {e}")
        
        threading.Thread(target=save, daemon=True).start()

    def load_selected_from_database(self):
        """Load selected list từ database"""
        def load():
            try:
                url = f"{self.api_url}/load_selected_list"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    loaded_data = resp.json()
                    if isinstance(loaded_data, list):
                        # Lọc unique IP+PORT
                        unique = {}
                        for entry in loaded_data:
                            d = entry.get("data", {})
                            key = f"{d.get('ip','')}:{d.get('port','')}"
                            if key not in unique:
                                unique[key] = entry
                        self.selected_data = list(unique.values())
                        print(f"✓ Loaded {len(self.selected_data)} items from database (unique)")
                        # Start ping threads for PTZ entries
                        for entry in self.selected_data:
                            d = entry.get("data", {})
                            if d.get("ptz", False):
                                ptz_key = f"{d.get('name','')}:{d.get('port','')}"
                                self.root.after(0, lambda k=ptz_key: self._start_ptz_ping(k))
                        # Update UI
                        self.root.after(0, self.update_selected_table)
                        self.root.after(0, self.update_all_table)
                    else:
                        print("⚠ Invalid data format from database")
                else:
                    print(f"✗ Load error: {resp.status_code}")
            except Exception as e:
                print(f"✗ Failed to load from database: {e}")
        threading.Thread(target=load, daemon=True).start()

    # ── vmPing methods ──────────────────────────────────────────────────────

    def add_ping_host(self):
        """Add a new ping card for the entered IP/hostname"""
        host = self.ping_ip_entry.get().strip()
        if not host:
            return
        if host in self.ping_hosts:
            messagebox.showwarning("vmPing", f"{host} đang được monitor!")
            return
        self.ping_ip_entry.delete(0, "end")
        self._create_ping_card(host)
        self.start_ping_host(host)
        self.ping_count_label.configure(text=f"{len(self.ping_hosts)} monitors")

    def _create_ping_card(self, host):
        """Build the visual card widget for a host"""
        idx = len(self.ping_hosts)
        col = idx % self.ping_grid_cols
        row = idx // self.ping_grid_cols

        card = ctk.CTkFrame(self.ping_cards_frame, fg_color="#2b2b2b",
                            corner_radius=6, border_width=2, border_color="#3a3a3a")
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        # Title bar (serves as status colour strip)
        title_bar = ctk.CTkFrame(card, fg_color="#9E9E9E", height=28, corner_radius=0)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        host_lbl = ctk.CTkLabel(title_bar, text=host, font=("Arial", 11, "bold"), text_color="#ffffff")
        host_lbl.pack(side="left", padx=8)

        toggle_btn = ctk.CTkButton(title_bar, text="⏹", width=26, height=22,
                                   fg_color="transparent", hover_color="#666666",
                                   command=lambda h=host: self.toggle_ping_host(h),
                                   font=("Arial", 11))
        toggle_btn.pack(side="right", padx=2)

        remove_btn = ctk.CTkButton(title_bar, text="✕", width=26, height=22,
                                   fg_color="transparent", hover_color="#666666",
                                   command=lambda h=host: self.remove_ping_card(h),
                                   font=("Arial", 11, "bold"))
        remove_btn.pack(side="right", padx=2)

        # Output area
        output_text = ctk.CTkTextbox(card, height=90, font=("Consolas", 9),
                                     fg_color="#111111", text_color="#cccccc", wrap="none")
        output_text.pack(fill="both", expand=True, padx=2, pady=(2, 0))

        # Stats bar
        stats_frame = ctk.CTkFrame(card, fg_color="#1a1a1a", height=20, corner_radius=0)
        stats_frame.pack(fill="x")
        stats_frame.pack_propagate(False)
        stats_label = ctk.CTkLabel(stats_frame,
                                   text="Sent: 0 | Recv: 0 | Lost: 0 | Avg: —ms",
                                   font=("Consolas", 8), text_color="#9E9E9E")
        stats_label.pack(side="left", padx=5)

        self.ping_hosts[host] = {
            "card": card,
            "title_bar": title_bar,
            "toggle_btn": toggle_btn,
            "output_text": output_text,
            "stats_label": stats_label,
            "running": False,
            "thread": None,
            "sent": 0,
            "recv": 0,
            "total_ms": 0,
        }

    def start_ping_host(self, host):
        """Start the ping loop thread for a host"""
        if host not in self.ping_hosts:
            return
        info = self.ping_hosts[host]
        if info["running"]:
            return
        info["running"] = True
        info["toggle_btn"].configure(text="⏹")
        t = threading.Thread(target=self._ping_loop, args=(host,), daemon=True)
        info["thread"] = t
        t.start()

    def stop_ping_host(self, host):
        """Signal the ping loop to stop"""
        if host not in self.ping_hosts:
            return
        self.ping_hosts[host]["running"] = False
        self.ping_hosts[host]["toggle_btn"].configure(text="▶")
        # Grey out title bar
        self.ping_hosts[host]["title_bar"].configure(fg_color="#555555")

    def toggle_ping_host(self, host):
        """Toggle ping on/off"""
        if host not in self.ping_hosts:
            return
        if self.ping_hosts[host]["running"]:
            self.stop_ping_host(host)
        else:
            self.start_ping_host(host)

    def _ping_loop(self, host):
        """Background thread: continuously ping host and update card"""
        info = self.ping_hosts[host]
        while info["running"]:
            try:
                result = subprocess.run(
                    ["ping", "-n", "1", "-w", "1000", host],
                    capture_output=True, timeout=4,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                # Decode with system codepage (cp1252/cp850 on Vietnamese Windows)
                try:
                    output = result.stdout.decode('cp1252', errors='ignore')
                except Exception:
                    output = result.stdout.decode('utf-8', errors='ignore')
                is_up = ("TTL=" in output.upper()) or (result.returncode == 0 and "ttl=" in output.lower())

                ms_val = None
                if is_up:
                    m = re.search(r'[=<](\d+)ms', output, re.IGNORECASE)
                    if m:
                        ms_val = int(m.group(1))

                info["sent"] += 1
                if is_up:
                    info["recv"] += 1
                    if ms_val is not None:
                        info["total_ms"] += ms_val
                    line = f"Reply from {host}: time={ms_val}ms" if ms_val is not None else f"Reply from {host}"
                else:
                    line = f"Request timeout for {host}"

                lost = info["sent"] - info["recv"]
                avg_ms = f"{info['total_ms'] // info['recv']}ms" if info["recv"] > 0 else "—"
                stats_text = f"Sent: {info['sent']} | Recv: {info['recv']} | Lost: {lost} | Avg: {avg_ms}"
                title_color = "#4CAF50" if is_up else "#f44336"
                line_color = "#00ff00" if is_up else "#ff4444"

                def _upd(h=host, ln=line, lc=line_color, st=stats_text, tc=title_color):
                    if h not in self.ping_hosts:
                        return
                    inf = self.ping_hosts[h]
                    if not inf["running"]:
                        return
                    txt = inf["output_text"]
                    # Insert coloured-ish line (CTkTextbox doesn't support tags;
                    # we update title bar colour for overall status instead)
                    txt.configure(text_color=lc)
                    txt.insert("end", ln + "\n")
                    # Trim to last 200 lines
                    content = txt.get("1.0", "end-1c")
                    lines = content.split("\n")
                    if len(lines) > 200:
                        txt.delete("1.0", f"{len(lines)-200}.0")
                    txt.see("end")
                    inf["stats_label"].configure(text=st)
                    inf["title_bar"].configure(fg_color=tc)

                self.root.after(0, _upd)

            except Exception as exc:
                def _err(h=host, e=str(exc)):
                    if h not in self.ping_hosts:
                        return
                    inf = self.ping_hosts[h]
                    inf["output_text"].configure(text_color="#FF9800")
                    inf["output_text"].insert("end", f"Error: {e}\n")
                    inf["title_bar"].configure(fg_color="#FF9800")
                self.root.after(0, _err)

            time.sleep(1)

    def remove_ping_card(self, host):
        """Remove a ping card and rebuild the grid"""
        if host not in self.ping_hosts:
            return
        self.ping_hosts[host]["running"] = False
        self.ping_hosts[host]["card"].destroy()
        del self.ping_hosts[host]
        self._rebuild_ping_grid()
        self.ping_count_label.configure(text=f"{len(self.ping_hosts)} monitors")

    def _rebuild_ping_grid(self):
        """Re-place all cards into a clean grid after a removal"""
        for idx, (host, info) in enumerate(self.ping_hosts.items()):
            col = idx % self.ping_grid_cols
            row = idx // self.ping_grid_cols
            info["card"].grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

    def stop_all_pings(self):
        for host in list(self.ping_hosts.keys()):
            self.stop_ping_host(host)

    def start_all_pings(self):
        for host in list(self.ping_hosts.keys()):
            self.start_ping_host(host)

    def clear_all_pings(self):
        for host in list(self.ping_hosts.keys()):
            self.ping_hosts[host]["running"] = False
            self.ping_hosts[host]["card"].destroy()
        self.ping_hosts.clear()
        self.ping_count_label.configure(text="0 monitors")

    # ── original helpers ────────────────────────────────────────────────────

    def on_double_click(self, event):
        """Not used with custom table"""
        pass
    
    def show_detail_from_entry(self, entry):
        """Show detail from entry object"""
        self.detail_text.delete("1.0", "end")
        if entry:
            self.detail_text.insert("1.0", json.dumps(entry, indent=2, ensure_ascii=False))
    
    def show_detail_all(self, event):
        """Show detail when selecting from left table"""
        # Not used anymore with custom table
        pass

    def show_detail_selected(self, event):
        """Not used with custom table"""
        pass

def main():
    root = ctk.CTk()
    app = ServerDataGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
