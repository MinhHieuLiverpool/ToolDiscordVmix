import json
import re
import threading
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import requests

try:
    from .shared import VIETNAM_TZ, pretty_time, get_first_srt, get_srt_ports_str, get_srt_quality_str, GLOBAL_LOG_QUEUE
except ImportError:
    try:
        from server_gui_advanced.shared import VIETNAM_TZ, pretty_time, get_first_srt, get_srt_ports_str, get_srt_quality_str, GLOBAL_LOG_QUEUE
    except ImportError:
        from shared import VIETNAM_TZ, pretty_time, get_first_srt, get_srt_ports_str, get_srt_quality_str, GLOBAL_LOG_QUEUE


class ServerDataGUIUIMixin:
    def setup_main_ui(self):
        # Top controls
        top_frame = ctk.CTkFrame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)

        # Row 1: Server and Prefix
        row1 = ctk.CTkFrame(top_frame, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        ctk.CTkLabel(row1, text="Server:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.server_entry = ctk.CTkEntry(row1, textvariable=self.server_url_var, width=350, font=("Arial", 10))
        self.server_entry.pack(side="left", padx=5)
        self.server_entry.bind("<Return>", lambda _e: self.apply_server_url(reconnect=True, announce=True))
        ctk.CTkButton(
            row1,
            text="Áp dụng",
            command=lambda: self.apply_server_url(reconnect=True, announce=True),
            width=88,
            fg_color="#2196F3",
            hover_color="#1976D2",
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Prefix:", font=("Arial", 10, "bold")).pack(side="left", padx=(20, 5))
        self.prefix_entry = ctk.CTkEntry(row1, textvariable=self.prefix_var, width=120, font=("Arial", 10))
        self.prefix_entry.pack(side="left", padx=5)

        # Row 2: buttons
        row2 = ctk.CTkFrame(top_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)

        ctk.CTkButton(row2, text="🔍 Scan máy", command=self.open_scan_dialog, fg_color="#4CAF50", hover_color="#45a049", width=110, font=("Arial", 10, "bold")).pack(side="left", padx=3)
        self.toggle_btn = ctk.CTkButton(row2, text="AUTO SEND: OFF", command=self.toggle_auto_send, fg_color="#9E9E9E", hover_color="#757575", width=130, font=("Arial", 10, "bold"))
        self.toggle_btn.pack(side="left", padx=3)
        ctk.CTkButton(row2, text="🗑️ Clear", command=self.clear_selected, fg_color="#f44336", hover_color="#d32f2f", width=90).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="💾 Save", command=self.save_selected_to_file, fg_color="#9C27B0", hover_color="#7B1FA2", width=90).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="📂 Open", command=self.load_selected_from_file, fg_color="#673AB7", hover_color="#512DA8", width=90).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="🌐 Web", command=self.open_web_dialog, fg_color="#00ACC1", hover_color="#00838F", width=90, font=("Arial", 10, "bold")).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="➕ Add PTZ", command=self.add_ptz_manual, fg_color="#FF9800", hover_color="#F57C00", width=100, font=("Arial", 10, "bold")).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="🔑 StreamKey", command=self.open_stream_keys_dialog, fg_color="#26A69A", hover_color="#1F857A", width=110, font=("Arial", 10, "bold")).pack(side="left", padx=3)

        self.setting_nav_btn = ctk.CTkButton(
            row2,
            text="⚙️ Setting",
            command=self.toggle_setting_page,
            fg_color="#607D8B",
            hover_color="#455A64",
            width=105,
            font=("Arial", 10, "bold")
        )
        self.setting_nav_btn.pack(side="left", padx=3)

        self.import_log_nav_btn = ctk.CTkButton(
            row2,
            text="📄 Import Log",
            command=self.toggle_import_log_page,
            fg_color="#FF5722",
            hover_color="#E64A19",
            width=110,
            font=("Arial", 10, "bold"),
        )
        self.import_log_nav_btn.pack(side="left", padx=3)

        self.debug_nav_btn = ctk.CTkButton(row2, text="🐞 Debug", command=self.toggle_debug_page, fg_color="#7e57c2", hover_color="#5e35b1", width=95, font=("Arial", 10, "bold"))
        self.debug_nav_btn.pack(side="left", padx=3)

        # Connection status
        self.status_label = ctk.CTkLabel(row2, text="⚪ Disconnected", font=("Arial", 9, "bold"), text_color="#9E9E9E")
        self.status_label.pack(side="right", padx=10)

        # Main content area with draggable splitter between table and vmPing
        self.vertical_splitter = self._create_vertical_splitter()
        self.vertical_splitter.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Create Debug Frame (hidden by default)
        self.showing_debug = False
        self.debug_frame = ctk.CTkFrame(self.root, fg_color="#181818")

        # Create Import Log Frame (hidden by default)
        self.showing_import_log = False
        self.import_log_frame = ctk.CTkFrame(self.root, fg_color="#181818")
        self.setup_import_log_ui()

        # Create Setting Frame (hidden by default)
        self.showing_setting = False
        self.setting_frame = ctk.CTkFrame(self.root, fg_color="#181818")
        self.setup_setting_ui()
        
        # Header inside debug frame
        db_hdr = ctk.CTkFrame(self.debug_frame, fg_color="#1a1a1a", height=38)
        db_hdr.pack(fill="x", padx=0, pady=(0, 2))
        db_hdr.pack_propagate(False)
        ctk.CTkLabel(db_hdr, text="🐞 System Debug Logs", font=("Arial", 10, "bold"), text_color="#FFB300").pack(side="left", padx=10)
        
        ctk.CTkButton(db_hdr, text="🗑️ Clear Logs", command=self.clear_debug_logs, fg_color="#f44336", hover_color="#d32f2f", width=100, height=26, font=("Arial", 9, "bold")).pack(side="right", padx=10)

        # Textbox for logs
        self.debug_textbox = ctk.CTkTextbox(self.debug_frame, font=("Consolas", 10), fg_color="#1e1e1e", text_color="#00ff00")
        self.debug_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure custom tag colors for log segments
        self.debug_textbox.tag_config("log_time", foreground="#7F8C8D")      # cool gray
        self.debug_textbox.tag_config("log_sep", foreground="#555555")       # dark gray
        self.debug_textbox.tag_config("log_device", foreground="#3498DB")    # sky blue
        self.debug_textbox.tag_config("metric_lbl", foreground="#E67E22")    # orange
        self.debug_textbox.tag_config("metric_val", foreground="#1ABC9C")    # turquoise
        self.debug_textbox.tag_config("srt_port", foreground="#BDC3C7")      # light gray
        self.debug_textbox.tag_config("srt_on", foreground="#2ECC71")        # bright green
        self.debug_textbox.tag_config("srt_off", foreground="#E74C3C")       # bright red
        
        # Start queue processing
        self.root.after(200, self.update_debug_logs_from_queue)

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

        # Right table - canvas + both scrollbars (supports horizontal scrolling)
        import tkinter as tk

        try:
            tk_scale = float(self.root.tk.call("tk", "scaling"))
        except Exception:
            tk_scale = 1.3333
        scale_factor = max(1.0, tk_scale / 1.3333)
        self.selected_table_total_width = int(3250 * scale_factor) + 60
        table_outer = ctk.CTkFrame(right_frame, fg_color="#2b2b2b")
        table_outer.pack(fill="both", expand=True, padx=5, pady=5)

        self.table_canvas = tk.Canvas(table_outer, bg="#2b2b2b", highlightthickness=0)
        table_vscroll = ctk.CTkScrollbar(
            table_outer,
            orientation="vertical",
            command=self.table_canvas.yview,
            fg_color="#1f2329",
            button_color="#4b5563",
            button_hover_color="#6b7280",
        )
        table_hscroll = ctk.CTkScrollbar(
            table_outer,
            orientation="horizontal",
            command=self.table_canvas.xview,
            fg_color="#1f2329",
            button_color="#4b5563",
            button_hover_color="#6b7280",
        )
        self.table_canvas.configure(yscrollcommand=table_vscroll.set, xscrollcommand=table_hscroll.set)

        table_vscroll.pack(side="right", fill="y")
        table_hscroll.pack(side="bottom", fill="x")
        self.table_canvas.pack(side="left", fill="both", expand=True)

        self.table_frame_right = ctk.CTkFrame(self.table_canvas, fg_color="#2b2b2b")
        self._table_window_id = self.table_canvas.create_window((0, 0), window=self.table_frame_right, anchor="nw")
        self.table_frame_right.bind("<Configure>", lambda e: self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all")))
        self.table_canvas.bind("<Configure>", self._on_selected_table_canvas_configure)

        # Header
        header_frame_right = ctk.CTkFrame(self.table_frame_right, fg_color="#1a1a1a", height=40, width=self.selected_table_total_width)
        header_frame_right.pack(anchor="w", pady=(0, 5))
        header_frame_right.pack_propagate(False)

        ctk.CTkLabel(header_frame_right, text="STT", font=("Arial", 10, "bold"), width=35).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="TÊN", font=("Arial", 10, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="IP MÁY", font=("Arial", 10, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="IP WAN", font=("Arial", 10, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="STATUS", font=("Arial", 10, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="PORT", font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="NAME SRT", font=("Arial", 10, "bold"), width=100).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="HOSTNAME", font=("Arial", 10, "bold"), width=150).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="STREAM ID", font=("Arial", 10, "bold"), width=220).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="QUALITY", font=("Arial", 10, "bold"), width=180).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="APP", font=("Arial", 10, "bold"), width=45).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="📡 PING", font=("Arial", 10, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="❌ TIMEOUT", font=("Arial", 10, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="NET SPEED", font=("Arial", 10, "bold"), width=100).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="MAC", font=("Arial", 10, "bold"), width=120).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="⚡ CPU%", font=("Arial", 10, "bold"), width=65).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="💾 RAM%", font=("Arial", 10, "bold"), width=65).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🎮 GPU%", font=("Arial", 10, "bold"), width=65).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="⬆ SEND", font=("Arial", 10, "bold"), width=88).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="⬇ RECV", font=("Arial", 10, "bold"), width=88).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="PID VMIX", font=("Arial", 10, "bold"), width=95).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="● REC", font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🔴 LIVE", font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🟢 EXT", font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🖥 RES", font=("Arial", 10, "bold"), width=90).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="TIME", font=("Arial", 10, "bold"), width=200).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="THAO TÁC", font=("Arial", 10, "bold"), width=240).pack(side="left", padx=2)

        self.right_table_rows = []
        # Cache widget refs for in-place updates (no flicker)
        self.right_table_row_widgets = []

        # vmPing panel
        vmping_outer = ctk.CTkFrame(self.vertical_splitter, fg_color="#181818")
        self.vertical_splitter.add(vmping_outer, minsize=170)

        vmping_header = ctk.CTkFrame(vmping_outer, fg_color="#1a1a1a", height=38)
        vmping_header.pack(fill="x", padx=0, pady=(0, 2))
        vmping_header.pack_propagate(False)

        ctk.CTkLabel(vmping_header, text="📡 vmPING", font=("Arial", 10, "bold"), text_color="#4CAF50").pack(side="left", padx=10)
        self.ping_name_entry = ctk.CTkEntry(vmping_header, placeholder_text="Tên máy (tuỳ chọn)...", width=170, font=("Arial", 10))
        self.ping_name_entry.pack(side="left", padx=(0, 4))
        self.ping_ip_entry = ctk.CTkEntry(vmping_header, placeholder_text="Nhập IP hoặc hostname...", width=200, font=("Arial", 10))
        self.ping_ip_entry.pack(side="left", padx=5)
        self.ping_name_entry.bind("<Return>", lambda e: self.add_ping_host())
        self.ping_ip_entry.bind("<Return>", lambda e: self.add_ping_host())
        ctk.CTkButton(vmping_header, text="+ Add", command=self.add_ping_host, fg_color="#4CAF50", hover_color="#45a049", width=60, font=("Arial", 10, "bold")).pack(side="left", padx=3)
        ctk.CTkButton(vmping_header, text="▶ Start All", command=self.start_all_pings, fg_color="#2196F3", hover_color="#1976D2", width=85, font=("Arial", 10)).pack(side="left", padx=3)
        ctk.CTkButton(vmping_header, text="⏹ Stop All", command=self.stop_all_pings, fg_color="#f44336", hover_color="#d32f2f", width=80, font=("Arial", 10)).pack(side="left", padx=3)
        ctk.CTkButton(vmping_header, text="🗑 Clear All", command=self.clear_all_pings, fg_color="#555555", hover_color="#444444", width=80, font=("Arial", 10)).pack(side="left", padx=3)
        self.ping_count_label = ctk.CTkLabel(vmping_header, text="0 monitors", font=("Arial", 9), text_color="#9E9E9E")
        self.ping_count_label.pack(side="right", padx=10)

        self.ping_cards_frame = ctk.CTkScrollableFrame(vmping_outer, fg_color="#1e1e1e")
        self.ping_cards_frame.pack(fill="both", expand=True)
        for col in range(4):
            self.ping_cards_frame.grid_columnconfigure(col, weight=1)

        self.root.after(120, self._set_default_split_position)

        self.ping_hosts = {}
        self.ping_grid_cols = 4

        self.detail_text = ctk.CTkTextbox(vmping_outer, height=0, font=("Consolas", 10), fg_color="#1e1e1e", text_color="#00ff00")

    def _create_vertical_splitter(self):
        import tkinter as tk

        return tk.PanedWindow(
            self.root,
            orient=tk.VERTICAL,
            sashwidth=8,
            sashrelief=tk.RAISED,
            showhandle=True,
            bg="#1f1f1f",
        )

    def _set_default_split_position(self):
        try:
            total_h = self.root.winfo_height()
            y = max(260, int(total_h * 0.62))
            self.vertical_splitter.sash_place(0, 0, y)
        except Exception:
            pass

    def _on_selected_table_canvas_configure(self, event):
        try:
            target_w = max(int(event.width), int(self.selected_table_total_width))
            self.table_canvas.itemconfigure(self._table_window_id, width=target_w)
        except Exception:
            pass

    def open_web_dialog(self):
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
        ctk.CTkEntry(pass_row, textvariable=password_var, placeholder_text="Nhập mật khẩu", show="*").pack(side="left", fill="x", expand=True)

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
                password_view_var = ctk.StringVar(value=f"Mật khẩu: {masked_password}")
                is_revealed = {"value": False}

                local_pass_row = ctk.CTkFrame(text_col, fg_color="transparent")
                local_pass_row.pack(fill="x")
                ctk.CTkLabel(local_pass_row, textvariable=password_view_var, font=("Arial", 10), anchor="w").pack(side="left", anchor="w")

                def toggle_password_view(var=password_view_var, reveal=is_revealed, real=shown_password, masked=masked_password):
                    reveal["value"] = not reveal["value"]
                    var.set(f"Mật khẩu: {real if reveal['value'] else masked}")

                ctk.CTkButton(local_pass_row, text="👁", width=52, height=24, fg_color="#5E35B1", hover_color="#4527A0", command=toggle_password_view).pack(side="left", padx=(8, 0))
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
                endpoints = [f"{self.api_url}/create_account", f"{self.api_url}/register"]
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

    def open_scan_dialog(self):
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
        ctk.CTkButton(top_bar, text="Refresh", width=90, command=lambda: self.refresh_data(show_dialog=False), fg_color="#4CAF50", hover_color="#45a049").pack(side="right", padx=4)
        ctk.CTkButton(top_bar, text="Add Selected", width=110, command=self.add_to_selected, fg_color="#2196F3", hover_color="#1976D2").pack(side="right", padx=4)

        self.table_frame_left = ctk.CTkScrollableFrame(dialog_root, fg_color="#2b2b2b")
        self.table_frame_left.pack(fill="both", expand=True)

        header_frame = ctk.CTkFrame(self.table_frame_left, fg_color="#1a1a1a", height=40)
        header_frame.pack(fill="x", pady=(0, 5))
        header_frame.pack_propagate(False)

        self.select_all_var.set(False)
        self.select_all_cb = ctk.CTkCheckBox(header_frame, text="", variable=self.select_all_var, width=35, command=self.toggle_select_all)
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

    def update_all_table(self):
        if self.table_frame_left is None or not self.table_frame_left.winfo_exists():
            self.left_table_rows = []
            self.left_table_checkboxes = {}
            return

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

            row_frame = ctk.CTkFrame(self.table_frame_left, fg_color="#3a3a3a" if stt % 2 == 0 else "#2b2b2b", height=35)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)

            is_selected = self.is_in_selected(entry)
            checkbox_var = ctk.BooleanVar(value=is_selected)
            checkbox = ctk.CTkCheckBox(row_frame, text="", variable=checkbox_var, width=35, command=lambda e=entry, v=checkbox_var: self.on_checkbox_toggle(e, v))
            checkbox.pack(side="left", padx=2)
            self.left_table_checkboxes[idx] = (checkbox, checkbox_var, entry)

            stt_label = ctk.CTkLabel(row_frame, text=str(stt), font=("Arial", 11, "bold"), width=35, anchor="center")
            stt_label.pack(side="left", padx=2)

            name_label = ctk.CTkLabel(row_frame, text=name or "—", font=("Arial", 11, "bold"), width=140, anchor="center", text_color="#90CAF9")
            name_label.pack(side="left", padx=2)

            ip_color = "#4CAF50" if statusapp == 1 else "#f44336"
            ip_label = ctk.CTkLabel(row_frame, text=ip, font=("Arial", 11, "bold"), width=110, text_color=ip_color, anchor="center")
            ip_label.pack(side="left", padx=2)
            port_label = ctk.CTkLabel(row_frame, text=port, font=("Arial", 11, "bold"), width=60, anchor="center")
            port_label.pack(side="left", padx=2)

            for widget in [row_frame, stt_label, name_label, ip_label, port_label]:
                widget.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))

            self.left_table_rows.append(row_frame)
            stt += 1

    def _build_row_data(self, entry, stt):
        """Extract all display data from an entry dict."""
        ts = pretty_time(entry.get("timestamp", ""))
        d = entry.get("data", {})
        name = d.get("name", "").strip() or f"MÁY {stt}"
        ip = d.get("ip", "")
        ipwan = d.get("ipwan", "")
        statusapp = d.get("statusapp", 0)
        statusapp_text = "ON" if statusapp == 1 else "OFF"

        srt_list = d.get("SRT", [])
        if isinstance(srt_list, dict): srt_list = [srt_list]
        if not isinstance(srt_list, list): srt_list = []

        if d.get("ptz", False) or not srt_list:
            raw_status = d.get("status", "—")
            display_status = "OFF" if statusapp == 0 else raw_status
            srt_rows = [{
                "status": display_status,
                "port": d.get("port", "—"),
                "name": "—",
                "hostname": "—",
                "stream_id": "—",
                "quality": d.get("srt_quality", "—") or "—",
                "color": "#4CAF50" if display_status == "ON" else "#f44336"
            }]
        else:
            srt_rows = []
            for s in srt_list:
                if not isinstance(s, dict): continue
                st = s.get("status", "—")
                if statusapp == 0:
                    st = "OFF"
                q = s.get("quality", "")
                sn = s.get("nameSRT", "")
                sp = s.get("port", "")
                sh = s.get("hostname", "")
                sid = s.get("stream_id", "")
                srt_rows.append({
                    "status": st,
                    "port": str(sp),
                    "name": sn or "—",
                    "hostname": sh or "—",
                    "stream_id": sid or "—",
                    "quality": q or "—",
                    "color": "#4CAF50" if st == "ON" else "#f44336"
                })

        ping = d.get("ping", None)
        ping_timeouts = d.get("ping_timeouts", 0)
        cpu = d.get("temperature", d.get("cpu", None))
        memory = d.get("memory", None)
        gpu = d.get("gpu", None)
        sender_mbps = d.get("sender_mbps", d.get("sender_bw", None))
        receiver_mbps = d.get("receiver_mbps", d.get("receiver_bw", None))
        net_speed = d.get("network_speed", d.get("netspeed", None))
        mac_address = d.get("mac_address", d.get("mac", ""))
        pid_vmix = d.get("PIDVMIX", d.get("pid_vmix", d.get("pidvmix", "")))

        def _pct_text(v):
            try:
                return f"{float(v):.1f}%"
            except (TypeError, ValueError):
                return "—"

        def _mbps_text(v):
            if v is None:
                return "—"
            if isinstance(v, str):
                value_text = v.strip()
                if not value_text:
                    return "—"
                try:
                    v = float(value_text)
                except ValueError:
                    return value_text
            try:
                value = float(v)
            except (TypeError, ValueError):
                return "—"
            if value >= 100:
                return f"{value:.0f} Mbps"
            if value >= 10:
                return f"{value:.1f} Mbps"
            return f"{value:.2f} Mbps"

        def _net_speed_text(v):
            if v is None:
                return "—"
            if isinstance(v, (int, float)):
                return _mbps_text(v)
            v_str = str(v).strip()
            return v_str or "—"

        return {
            "ts": ts,
            "name": name,
            "ip": ip,
            "ipwan": ipwan,
            "statusapp": statusapp,
            "statusapp_text": statusapp_text,
            "app_color": "#4CAF50" if statusapp == 1 else "#f44336",
            "srt_rows": srt_rows,
            "ping": ping,
            "ping_str": f"{ping:.0f} ms" if ping is not None else "—",
            "ping_timeouts": ping_timeouts,
            "timeout_str": str(ping_timeouts) if ping_timeouts is not None else "0",
            "net_speed_str": _net_speed_text(net_speed),
            "mac_str": str(mac_address).strip() if str(mac_address).strip() else "—",
            "cpu_str": _pct_text(cpu),
            "mem_str": _pct_text(memory),
            "gpu_str": _pct_text(gpu),
            "sender_str": _mbps_text(sender_mbps),
            "receiver_str": _mbps_text(receiver_mbps),
            "pid_vmix_str": str(pid_vmix).strip() if str(pid_vmix).strip() else "—",
            "vmix_rec": d.get("vmix_recording", False),
            "vmix_live": d.get("vmix_streaming", False),
            "vmix_ext": d.get("vmix_external", False),
            "res": d.get("resolution", "—") or "—",
        }

    @staticmethod
    def _normalize_stream_list(d: dict) -> list:
        stream_raw = d.get("stream", [])
        if isinstance(stream_raw, dict):
            return [stream_raw]
        if isinstance(stream_raw, list):
            return [item for item in stream_raw if isinstance(item, dict)]
        return []

    @staticmethod
    def _normalize_dict_list(raw) -> list:
        if isinstance(raw, dict):
            return [raw]
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        return []

    def _create_selected_row(self, entry, stt, rd):
        """Create a brand-new row frame with all widgets. Returns (row_frame, widget_cache)."""

        row_h = max(40, len(rd["srt_rows"]) * 22 + 10)
        row_frame = ctk.CTkFrame(self.table_frame_right,
                                  fg_color="#3a3a3a" if stt % 2 == 0 else "#2b2b2b",
                                  height=row_h,
                                  width=self.selected_table_total_width)
        row_frame.pack(anchor="w", pady=1)
        row_frame.pack_propagate(False)

        def create_cell(parent, width, expand=False):
            f = ctk.CTkFrame(parent, fg_color="transparent", width=width)
            f.pack(side="left", padx=2, fill="both", expand=expand)
            f.pack_propagate(False)
            return f

        def create_centered_srt_container(parent):
            inner = ctk.CTkFrame(parent, fg_color="transparent")
            inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0)
            return inner

        wc = {}  # widget cache

        # STT
        c = create_cell(row_frame, 35)
        ctk.CTkLabel(c, text=str(stt), font=("Arial", 10, "bold")).place(relx=0.5, rely=0.5, anchor="center")

        # Name
        c = create_cell(row_frame, 110)
        name_lbl = ctk.CTkLabel(c, text=rd["name"], font=("Arial", 10, "bold"), wraplength=100)
        name_lbl.place(relx=0.5, rely=0.5, anchor="center")
        name_lbl.bind("<Double-1>", lambda e, idx=stt-1, frame=c, lbl=name_lbl: self.edit_name_inline(idx, frame, lbl))
        wc["name_lbl"] = name_lbl

        # IP MÁY
        c = create_cell(row_frame, 110)
        wc["ip_lbl"] = ctk.CTkLabel(c, text=rd["ip"], font=("Arial", 10))
        wc["ip_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # IP WAN
        c = create_cell(row_frame, 110)
        wc["ipwan_lbl"] = ctk.CTkLabel(c, text=rd["ipwan"], font=("Arial", 10))
        wc["ipwan_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # SRT multi-row columns
        c_status = create_cell(row_frame, 70)
        inner_status = create_centered_srt_container(c_status)
        c_port = create_cell(row_frame, 60)
        inner_port = create_centered_srt_container(c_port)
        c_name_srt = create_cell(row_frame, 100)
        inner_name_srt = create_centered_srt_container(c_name_srt)
        c_hostname = create_cell(row_frame, 150)
        inner_hostname = create_centered_srt_container(c_hostname)
        c_stream_id = create_cell(row_frame, 220)
        inner_stream_id = create_centered_srt_container(c_stream_id)
        c_quality = create_cell(row_frame, 180)
        inner_quality = create_centered_srt_container(c_quality)

        srt_lbl_groups = []
        for s_info in rd["srt_rows"]:
            sl = ctk.CTkLabel(inner_status, text=s_info["status"], font=("Arial", 9, "bold"), text_color=s_info["color"], anchor="center")
            sl.pack(fill="x")
            pl = ctk.CTkLabel(inner_port, text=s_info["port"], font=("Arial", 9), anchor="center")
            pl.pack(fill="x")
            nl = ctk.CTkLabel(inner_name_srt, text=s_info["name"], font=("Arial", 9, "bold"), text_color="#90CAF9", anchor="center")
            nl.pack(fill="x")
            hl = ctk.CTkLabel(inner_hostname, text=s_info["hostname"], font=("Arial", 9), text_color="#E0E0E0", anchor="center")
            hl.pack(fill="x")
            sil = ctk.CTkLabel(inner_stream_id, text=s_info["stream_id"], font=("Arial", 9), text_color="#E0E0E0", anchor="center")
            sil.pack(fill="x")
            ql = ctk.CTkLabel(inner_quality, text=s_info["quality"], font=("Arial", 9), text_color=s_info["color"], anchor="center")
            ql.pack(fill="x")
            srt_lbl_groups.append({"status": sl, "port": pl, "name": nl, "hostname": hl, "stream_id": sil, "quality": ql})
        wc["srt_lbl_groups"] = srt_lbl_groups

        # App status
        c = create_cell(row_frame, 45)
        wc["app_lbl"] = ctk.CTkLabel(c, text=rd["statusapp_text"], font=("Arial", 10, "bold"), text_color=rd["app_color"])
        wc["app_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # Ping
        c = create_cell(row_frame, 70)
        wc["ping_lbl"] = ctk.CTkLabel(c, text=rd["ping_str"], font=("Arial", 10),
                                        text_color="#4CAF50" if rd["ping"] else "#9E9E9E")
        wc["ping_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # Timeout
        c = create_cell(row_frame, 70)
        wc["timeout_lbl"] = ctk.CTkLabel(c, text=rd["timeout_str"], font=("Arial", 10, "bold"),
                                           text_color="#f44336" if rd["ping_timeouts"] else "#9E9E9E")
        wc["timeout_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # Net speed
        c = create_cell(row_frame, 100)
        wc["net_speed_lbl"] = ctk.CTkLabel(c, text=rd["net_speed_str"], font=("Arial", 10))
        wc["net_speed_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # MAC address
        c = create_cell(row_frame, 120)
        wc["mac_lbl"] = ctk.CTkLabel(c, text=rd["mac_str"], font=("Arial", 10))
        wc["mac_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # CPU
        c = create_cell(row_frame, 65)
        wc["cpu_lbl"] = ctk.CTkLabel(c, text=rd["cpu_str"], font=("Arial", 10))
        wc["cpu_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # RAM
        c = create_cell(row_frame, 65)
        wc["mem_lbl"] = ctk.CTkLabel(c, text=rd["mem_str"], font=("Arial", 10))
        wc["mem_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # GPU
        c = create_cell(row_frame, 65)
        wc["gpu_lbl"] = ctk.CTkLabel(c, text=rd["gpu_str"], font=("Arial", 10))
        wc["gpu_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # Sender / Receiver bandwidth
        c = create_cell(row_frame, 88)
        wc["sender_lbl"] = ctk.CTkLabel(c, text=rd["sender_str"], font=("Arial", 10))
        wc["sender_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        c = create_cell(row_frame, 88)
        wc["receiver_lbl"] = ctk.CTkLabel(c, text=rd["receiver_str"], font=("Arial", 10))
        wc["receiver_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        c = create_cell(row_frame, 95)
        wc["pid_vmix_lbl"] = ctk.CTkLabel(c, text=rd["pid_vmix_str"], font=("Arial", 10))
        wc["pid_vmix_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # vMix flags
        c = create_cell(row_frame, 60)
        wc["rec_lbl"] = ctk.CTkLabel(c, text="● ON" if rd["vmix_rec"] else "○ OFF", font=("Arial", 9),
                                       text_color="#f44336" if rd["vmix_rec"] else "#555555")
        wc["rec_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        c = create_cell(row_frame, 60)
        wc["live_lbl"] = ctk.CTkLabel(c, text="● ON" if rd["vmix_live"] else "○ OFF", font=("Arial", 9),
                                        text_color="#f44336" if rd["vmix_live"] else "#555555")
        wc["live_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        c = create_cell(row_frame, 60)
        wc["ext_lbl"] = ctk.CTkLabel(c, text="● ON" if rd["vmix_ext"] else "○ OFF", font=("Arial", 9),
                                       text_color="#4CAF50" if rd["vmix_ext"] else "#555555")
        wc["ext_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        c = create_cell(row_frame, 90)
        wc["res_lbl"] = ctk.CTkLabel(c, text=rd["res"], font=("Arial", 9, "bold"), text_color="#4CAF50")
        wc["res_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # Time
        c = create_cell(row_frame, 200)
        wc["ts_lbl"] = ctk.CTkLabel(c, text=rd["ts"], font=("Arial", 9))
        wc["ts_lbl"].place(relx=0.5, rely=0.5, anchor="center")

        # Action
        c = create_cell(row_frame, 240)
        actions = ctk.CTkFrame(c, fg_color="transparent", width=220, height=28)
        actions.place(relx=0.5, rely=0.5, anchor="center")
        actions.pack_propagate(False)

        wc["stream_btn"] = ctk.CTkButton(
            actions,
            text="Xem Stream",
            width=150,
            height=26,
            fg_color="#1976D2",
            hover_color="#1565C0",
            command=lambda idx=stt - 1: self.show_stream_dialog_by_index(idx),
            font=("Arial", 9, "bold"),
        )
        wc["stream_btn"].pack(side="left", padx=(0, 8))

        wc["remove_btn"] = ctk.CTkButton(
            actions,
            text="❌",
            width=40,
            height=26,
            fg_color="#f44336",
            hover_color="#d32f2f",
            command=lambda idx=stt - 1: self.remove_single_item(idx),
        )
        wc["remove_btn"].pack(side="left")

        row_frame.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))
        self._patch_selected_row(wc, rd)
        return row_frame, wc

    def _patch_selected_row(self, wc, rd):
        """Update only the changed text/color values in existing widgets (no flicker)."""
        wc["name_lbl"].configure(text=rd["name"])
        wc["ip_lbl"].configure(text=rd["ip"])
        wc["ipwan_lbl"].configure(text=rd["ipwan"])
        
        app_color = self.get_metric_color("status_app", rd["statusapp_text"], rd["app_color"])
        wc["app_lbl"].configure(text=rd["statusapp_text"], text_color=app_color)
        
        default_ping_color = "#4CAF50" if rd["ping"] else "#9E9E9E"
        ping_color = self.get_metric_color("ping", rd["ping_str"], default_ping_color)
        wc["ping_lbl"].configure(text=rd["ping_str"], text_color=ping_color)
        
        default_timeout_color = "#f44336" if rd["ping_timeouts"] else "#9E9E9E"
        timeout_color = self.get_metric_color("timeout", rd["timeout_str"], default_timeout_color)
        wc["timeout_lbl"].configure(text=rd["timeout_str"], text_color=timeout_color)
        
        net_speed_color = self.get_metric_color("netspeed", rd["net_speed_str"], "#ffffff")
        wc["net_speed_lbl"].configure(text=rd["net_speed_str"], text_color=net_speed_color)
        
        wc["mac_lbl"].configure(text=rd["mac_str"])
        
        cpu_color = self.get_metric_color("cpu", rd["cpu_str"], "#ffffff")
        wc["cpu_lbl"].configure(text=rd["cpu_str"], text_color=cpu_color)
        
        mem_color = self.get_metric_color("ram", rd["mem_str"], "#ffffff")
        wc["mem_lbl"].configure(text=rd["mem_str"], text_color=mem_color)
        
        gpu_color = self.get_metric_color("gpu", rd["gpu_str"], "#ffffff")
        wc["gpu_lbl"].configure(text=rd["gpu_str"], text_color=gpu_color)
        
        sender_color = self.get_metric_color("sender", rd["sender_str"], "#ffffff")
        wc["sender_lbl"].configure(text=rd["sender_str"], text_color=sender_color)
        
        receiver_color = self.get_metric_color("receiver", rd["receiver_str"], "#ffffff")
        wc["receiver_lbl"].configure(text=rd["receiver_str"], text_color=receiver_color)
        
        wc["pid_vmix_lbl"].configure(text=rd["pid_vmix_str"])
        wc["rec_lbl"].configure(text="● ON" if rd["vmix_rec"] else "○ OFF",
                                 text_color="#f44336" if rd["vmix_rec"] else "#555555")
        wc["live_lbl"].configure(text="● ON" if rd["vmix_live"] else "○ OFF",
                                  text_color="#f44336" if rd["vmix_live"] else "#555555")
        wc["ext_lbl"].configure(text="● ON" if rd["vmix_ext"] else "○ OFF",
                                 text_color="#4CAF50" if rd["vmix_ext"] else "#555555")
        wc["res_lbl"].configure(text=rd["res"])
        wc["ts_lbl"].configure(text=rd["ts"])

        for i, s_info in enumerate(rd["srt_rows"]):
            if i < len(wc["srt_lbl_groups"]):
                g = wc["srt_lbl_groups"][i]
                srt_color = self.get_metric_color("srt_status", s_info["status"], s_info["color"])
                g["status"].configure(text=s_info["status"], text_color=srt_color)
                g["port"].configure(text=s_info["port"])
                g["name"].configure(text=s_info["name"])
                g["hostname"].configure(text=s_info["hostname"])
                g["stream_id"].configure(text=s_info["stream_id"])
                g["quality"].configure(text=s_info["quality"], text_color=s_info["color"])

    def update_selected_table(self):
        """Rebuild rows only when structure changes; otherwise patch in-place (no flicker)."""
        new_count = len(self.selected_data)
        old_count = len(self.right_table_rows)

        # Compute new row data list
        new_rds = [self._build_row_data(entry, i + 1)
                   for i, entry in enumerate(self.selected_data)]

        # Check if we need a full rebuild: row count or srt_row count per row changed
        need_rebuild = (new_count != old_count)
        if not need_rebuild:
            for i, (rd, wc_pair) in enumerate(zip(new_rds, self.right_table_row_widgets)):
                _, wc = wc_pair
                old_srt_count = len(wc.get("srt_lbl_groups", []))
                if len(rd["srt_rows"]) != old_srt_count:
                    need_rebuild = True
                    break

        if need_rebuild:
            # Full rebuild — unavoidable when structure changes
            for row, _ in self.right_table_row_widgets:
                row.destroy()
            self.right_table_rows = []
            self.right_table_row_widgets = []

            for stt, (entry, rd) in enumerate(zip(self.selected_data, new_rds), start=1):
                row_frame, wc = self._create_selected_row(entry, stt, rd)
                self.right_table_rows.append(row_frame)
                self.right_table_row_widgets.append((row_frame, wc))
        else:
            # In-place update — just reconfigure label text/color, zero flicker
            for idx, (rd, (row_frame, wc)) in enumerate(zip(new_rds, self.right_table_row_widgets)):
                self._patch_selected_row(wc, rd)
                if "stream_btn" in wc:
                    wc["stream_btn"].configure(command=lambda i=idx: self.show_stream_dialog_by_index(i))

    def edit_name_inline(self, idx, frame, label):
        if idx >= len(self.selected_data):
            return

        old_name = label.cget("text")
        label.pack_forget()

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

                def update_name():
                    try:
                        update_data = {"old_name": old_name, "new_name": new_name, "ip": old_ip}
                        resp = requests.post(f"{self.api_url}/update_name", json=update_data, timeout=5)
                        if resp.status_code == 200:
                            print(f"✓ Updated: {old_name} → {new_name}")
                        else:
                            print(f"✗ Update error: {resp.status_code}")
                    except Exception as e:
                        print(f"✗ Error: {e}")

                threading.Thread(target=update_name, daemon=True).start()

            entry_widget.destroy()
            label.configure(text=new_name if new_name else old_name)
            label.pack(fill="both", expand=True)

        def cancel_edit(event=None):
            entry_widget.destroy()
            label.pack(fill="both", expand=True)

        entry_widget.bind("<Return>", save_name)
        entry_widget.bind("<FocusOut>", save_name)
        entry_widget.bind("<Escape>", cancel_edit)

    def add_ptz_manual(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("➕ Add PTZ")
        dialog.geometry("400x280")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 140
        dialog.geometry(f"400x280+{x}+{y}")

        ctk.CTkLabel(dialog, text="➕ THÊM PTZ THỦ CÔNG", font=("Arial", 14, "bold")).pack(pady=(15, 10))

        form_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        form_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(form_frame, text="Tên:", font=("Arial", 11, "bold"), width=80, anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        name_entry = ctk.CTkEntry(form_frame, width=250, font=("Arial", 11), placeholder_text="VD: PTZ CAM 1")
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="IP:", font=("Arial", 11, "bold"), width=80, anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ip_entry = ctk.CTkEntry(form_frame, width=250, font=("Arial", 11), placeholder_text="VD: 192.168.1.100")
        ip_entry.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Port:", font=("Arial", 11, "bold"), width=80, anchor="w").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        port_entry = ctk.CTkEntry(form_frame, width=250, font=("Arial", 11), placeholder_text="VD: 9000")
        port_entry.grid(row=2, column=1, padx=5, pady=5)

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
                    "ptz": True,
                },
            }

            for sel in self.selected_data:
                sel_d = sel.get("data", {})
                if sel_d.get("name", "") == name and sel_d.get("port", "") == port:
                    messagebox.showwarning("Warning", f"PTZ [{name}] port [{port}] đã tồn tại!", parent=dialog)
                    return

            self.selected_data.append(ptz_entry)
            self.update_selected_table()
            ptz_key = f"{name}:{port}"
            self._start_ptz_ping(ptz_key)
            print(f"✓ Added PTZ: [{name}] IP:{ip} IPWAN:{ipwan} PORT:{port}")
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="✅ Thêm", command=on_add, fg_color="#4CAF50", hover_color="#45a049", width=120, font=("Arial", 11, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="❌ Hủy", command=dialog.destroy, fg_color="#f44336", hover_color="#d32f2f", width=120, font=("Arial", 11, "bold")).pack(side="left", padx=10)
        name_entry.focus_set()

    def _create_ping_card(self, host, display_name=""):
        idx = len(self.ping_hosts)
        col = idx % self.ping_grid_cols
        row = idx // self.ping_grid_cols

        card = ctk.CTkFrame(self.ping_cards_frame, fg_color="#2b2b2b", corner_radius=6, border_width=2, border_color="#3a3a3a")
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        title_bar = ctk.CTkFrame(card, fg_color="#9E9E9E", height=28, corner_radius=0)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        shown_name = (display_name or "").strip()
        title_text = f"{shown_name} | {host}" if shown_name else host
        title_label = ctk.CTkLabel(title_bar, text=title_text, font=("Arial", 11, "bold"), text_color="#ffffff")
        title_label.pack(side="left", padx=8)

        toggle_btn = ctk.CTkButton(title_bar, text="⏹", width=26, height=22, fg_color="transparent", hover_color="#666666", command=lambda h=host: self.toggle_ping_host(h), font=("Arial", 11))
        toggle_btn.pack(side="right", padx=2)

        remove_btn = ctk.CTkButton(title_bar, text="✕", width=26, height=22, fg_color="transparent", hover_color="#666666", command=lambda h=host: self.remove_ping_card(h), font=("Arial", 11, "bold"))
        remove_btn.pack(side="right", padx=2)

        output_text = ctk.CTkTextbox(card, height=90, font=("Consolas", 9), fg_color="#111111", text_color="#cccccc", wrap="none")
        output_text.pack(fill="both", expand=True, padx=2, pady=(2, 0))

        stats_frame = ctk.CTkFrame(card, fg_color="#1a1a1a", height=20, corner_radius=0)
        stats_frame.pack(fill="x")
        stats_frame.pack_propagate(False)
        stats_label = ctk.CTkLabel(stats_frame, text="Sent: 0 | Recv: 0 | Lost: 0 | Avg: —ms", font=("Consolas", 8), text_color="#9E9E9E")
        stats_label.pack(side="left", padx=5)

        self.ping_hosts[host] = {
            "host": host,
            "name": shown_name,
            "card": card,
            "title_bar": title_bar,
            "title_label": title_label,
            "toggle_btn": toggle_btn,
            "output_text": output_text,
            "stats_label": stats_label,
            "running": False,
            "thread": None,
            "sent": 0,
            "recv": 0,
            "total_ms": 0,
        }

    def _rebuild_ping_grid(self):
        for idx, (host, info) in enumerate(self.ping_hosts.items()):
            col = idx % self.ping_grid_cols
            row = idx // self.ping_grid_cols
            info["card"].grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

    def on_double_click(self, event):
        pass

    def show_stream_dialog_by_index(self, idx: int):
        if idx < 0 or idx >= len(self.selected_data):
            return
        self.open_stream_dialog(self.selected_data[idx])

    def open_stream_dialog(self, entry):
        d = (entry or {}).get("data", {}) if isinstance(entry, dict) else {}
        name = str(d.get("name", "") or "Unknown")
        ip = str(d.get("ip", "") or "")

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Stream Details - {name}")
        dialog.geometry("1180x340")
        dialog.transient(self.root)
        dialog.grab_set()

        self.root.update_idletasks()
        x = self.root.winfo_x() + max(0, (self.root.winfo_width() - 1180) // 2)
        y = self.root.winfo_y() + max(0, (self.root.winfo_height() - 340) // 2)
        dialog.geometry(f"1180x340+{x}+{y}")

        top = ctk.CTkFrame(dialog, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(top, text=f"📡 STREAM DETAIL | {name} | {ip}", font=("Arial", 13, "bold")).pack(side="left")

        holder = ctk.CTkFrame(dialog)
        holder.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        import tkinter as tk

        table_canvas = tk.Canvas(holder, bg="#171a1f", highlightthickness=0)
        vsb = ctk.CTkScrollbar(
            holder,
            orientation="vertical",
            command=table_canvas.yview,
            fg_color="#1f2329",
            button_color="#4b5563",
            button_hover_color="#6b7280",
        )
        hsb = ctk.CTkScrollbar(
            holder,
            orientation="horizontal",
            command=table_canvas.xview,
            fg_color="#1f2329",
            button_color="#4b5563",
            button_hover_color="#6b7280",
        )
        table_canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        table_canvas.pack(side="left", fill="both", expand=True)

        cols = (
            ("stream", "Stream", 90),
            ("runtime", "Runtime", 70),
            ("health", "Health", 70),
            ("vbit", "Video", 90),
            ("size", "Size", 120),
            ("abit", "Audio", 80),
            ("level", "Level", 70),
            ("preset", "Preset", 90),
            ("aformat", "AudioFmt", 80),
            ("channels", "Channels", 80),
            ("keyframe", "Keyframe", 230),
            ("actual", "Actual kbps", 95),
            ("target", "Target kbps", 95),
            ("ratio", "Ratio", 70),
            ("speed", "Speed", 70),
            ("dropped", "Dropped", 80),
            ("file", "LatestFile", 270),
        )

        total_w = sum(w + 4 for _, _, w in cols) + 8
        table_inner = ctk.CTkFrame(table_canvas, fg_color="#171a1f", corner_radius=0, width=total_w)
        table_window_id = table_canvas.create_window((0, 0), window=table_inner, anchor="nw")

        def _on_inner_configure(_event=None):
            table_canvas.configure(scrollregion=table_canvas.bbox("all"))

        def _on_canvas_configure(event):
            table_canvas.itemconfigure(table_window_id, width=max(int(event.width), int(total_w)))

        table_inner.bind("<Configure>", _on_inner_configure)
        table_canvas.bind("<Configure>", _on_canvas_configure)

        def _make_cell(parent, text, width, text_color="#e5e7eb", bold=False):
            lbl = ctk.CTkLabel(
                parent,
                text=text,
                width=width,
                font=("Segoe UI", 11, "bold" if bold else "normal"),
                text_color=text_color,
                anchor="center",
            )
            lbl.pack(side="left", padx=2, pady=0)
            return lbl

        header = ctk.CTkFrame(table_inner, fg_color="#111827", height=36, width=total_w, corner_radius=0)
        header.pack(anchor="w", pady=(0, 2))
        header.pack_propagate(False)
        for _, label, width in cols:
            _make_cell(header, label, width, text_color="#e5e7eb", bold=True)

        body_frame = ctk.CTkFrame(table_inner, fg_color="transparent", width=total_w, corner_radius=0)
        body_frame.pack(anchor="w")

        target_name = name
        target_ip = ip

        def _sort_key(s: dict):
            name_val = str(s.get("stream", "") or "")
            low = name_val.lower()
            if low.startswith("streaming"):
                try:
                    return int(low.replace("streaming", "", 1) or "0")
                except ValueError:
                    return 9999
            return 9999

        def _resolve_live_data() -> dict:
            # Prefer exact IP match because selected_data gets replaced by websocket updates.
            for item in self.selected_data:
                cur = item.get("data", {}) if isinstance(item, dict) else {}
                if not isinstance(cur, dict):
                    continue
                if target_ip and str(cur.get("ip", "") or "") == target_ip:
                    return cur
            for item in self.selected_data:
                cur = item.get("data", {}) if isinstance(item, dict) else {}
                if not isinstance(cur, dict):
                    continue
                if target_name and str(cur.get("name", "") or "") == target_name:
                    return cur
            return d

        def _render_rows(streams: list):
            for child in body_frame.winfo_children():
                child.destroy()

            if not streams:
                empty_row = ctk.CTkFrame(body_frame, fg_color="#1f2937", height=34, width=total_w, corner_radius=0)
                empty_row.pack(anchor="w", pady=(0, 1))
                empty_row.pack_propagate(False)
                _make_cell(empty_row, "(empty)", cols[0][2], text_color="#9ca3af")
                for _, _, width in cols[1:]:
                    _make_cell(empty_row, "", width, text_color="#9ca3af")
                return

            for idx, s in enumerate(sorted(streams, key=_sort_key)):
                health = str(s.get("health", "") or "").upper()
                if health == "DO":
                    row_color = "#ef4444"
                elif health == "VANG":
                    row_color = "#f59e0b"
                elif health == "XANH":
                    row_color = "#22c55e"
                else:
                    row_color = "#e5e7eb"

                row = ctk.CTkFrame(
                    body_frame,
                    fg_color="#1b1f27" if idx % 2 == 0 else "#20242c",
                    height=34,
                    width=total_w,
                    corner_radius=0,
                )
                row.pack(anchor="w", pady=(0, 1))
                row.pack_propagate(False)

                row_values = {
                    "stream": str(s.get("stream", "") or ""),
                    "runtime": str(s.get("runtime", "") or ""),
                    "health": health,
                    "vbit": str(s.get("vbit", "") or ""),
                    "size": str(s.get("size", "") or ""),
                    "abit": str(s.get("abit", "") or ""),
                    "level": str(s.get("level", "") or ""),
                    "preset": str(s.get("preset", "") or ""),
                    "aformat": str(s.get("aformat", "") or ""),
                    "channels": str(s.get("channels", "") or ""),
                    "keyframe": str(s.get("keyframe", "") or ""),
                    "actual": str(s.get("actual", 0) or 0),
                    "target": str(s.get("target", 0) or 0),
                    "ratio": str(s.get("ratio", "") or ""),
                    "speed": str(s.get("speed", "") or ""),
                    "dropped": str(s.get("dropped", 0) or 0),
                    "file": str(s.get("file", "") or ""),
                }

                for key, _, width in cols:
                    _make_cell(row, row_values.get(key, ""), width, text_color=row_color)

        def _refresh_loop():
            try:
                if not dialog.winfo_exists():
                    return
            except Exception:
                return

            live_data = _resolve_live_data()
            _render_rows(self._normalize_stream_list(live_data))
            dialog.after(1000, _refresh_loop)

        _refresh_loop()

    def open_stream_keys_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Stream Keys")
        dialog.geometry("1120x360")
        dialog.transient(self.root)
        dialog.grab_set()

        self.root.update_idletasks()
        x = self.root.winfo_x() + max(0, (self.root.winfo_width() - 1120) // 2)
        y = self.root.winfo_y() + max(0, (self.root.winfo_height() - 360) // 2)
        dialog.geometry(f"1120x360+{x}+{y}")

        top = ctk.CTkFrame(dialog, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(top, text="🔑 STREAM KEYS (ALL MACHINES)", font=("Arial", 13, "bold")).pack(side="left")

        holder = ctk.CTkFrame(dialog)
        holder.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        import tkinter as tk

        table_canvas = tk.Canvas(holder, bg="#171a1f", highlightthickness=0)
        vsb = ctk.CTkScrollbar(
            holder,
            orientation="vertical",
            command=table_canvas.yview,
            fg_color="#1f2329",
            button_color="#4b5563",
            button_hover_color="#6b7280",
        )
        hsb = ctk.CTkScrollbar(
            holder,
            orientation="horizontal",
            command=table_canvas.xview,
            fg_color="#1f2329",
            button_color="#4b5563",
            button_hover_color="#6b7280",
        )
        table_canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        table_canvas.pack(side="left", fill="both", expand=True)

        cols = (
            ("machine", "Machine", 170),
            ("ip", "IP", 110),
            ("stream", "Stream", 90),
            ("url", "URL", 440),
            ("key", "Key", 250),
        )

        total_w = sum(w + 4 for _, _, w in cols) + 8
        table_inner = ctk.CTkFrame(table_canvas, fg_color="#171a1f", corner_radius=0, width=total_w)
        table_window_id = table_canvas.create_window((0, 0), window=table_inner, anchor="nw")

        def _on_inner_configure(_event=None):
            table_canvas.configure(scrollregion=table_canvas.bbox("all"))

        def _on_canvas_configure(event):
            table_canvas.itemconfigure(table_window_id, width=max(int(event.width), int(total_w)))

        table_inner.bind("<Configure>", _on_inner_configure)
        table_canvas.bind("<Configure>", _on_canvas_configure)

        def _make_cell(parent, text, width, text_color="#e5e7eb", bold=False):
            lbl = ctk.CTkLabel(
                parent,
                text=text,
                width=width,
                font=("Segoe UI", 11, "bold" if bold else "normal"),
                text_color=text_color,
                anchor="center",
            )
            lbl.pack(side="left", padx=2, pady=0)
            return lbl

        header = ctk.CTkFrame(table_inner, fg_color="#111827", height=36, width=total_w, corner_radius=0)
        header.pack(anchor="w", pady=(0, 2))
        header.pack_propagate(False)
        for _, label, width in cols:
            _make_cell(header, label, width, text_color="#e5e7eb", bold=True)

        body_frame = ctk.CTkFrame(table_inner, fg_color="transparent", width=total_w, corner_radius=0)
        body_frame.pack(anchor="w")

        def _collect_rows():
            rows = []
            for entry in self.selected_data:
                d = entry.get("data", {}) if isinstance(entry, dict) else {}
                machine = str(d.get("name", "") or "")
                ip = str(d.get("ip", "") or "")
                for sk in self._normalize_dict_list(d.get("stream_keys", [])):
                    rows.append({
                        "machine": machine,
                        "ip": ip,
                        "stream": str(sk.get("stream", "") or ""),
                        "url": str(sk.get("url", "") or ""),
                        "key": str(sk.get("key", "") or ""),
                    })
            return rows

        def _render_rows(rows: list):
            for child in body_frame.winfo_children():
                child.destroy()

            if not rows:
                empty_row = ctk.CTkFrame(body_frame, fg_color="#1f2937", height=34, width=total_w, corner_radius=0)
                empty_row.pack(anchor="w", pady=(0, 1))
                empty_row.pack_propagate(False)
                _make_cell(empty_row, "(empty)", cols[0][2], text_color="#9ca3af")
                for _, _, width in cols[1:]:
                    _make_cell(empty_row, "", width, text_color="#9ca3af")
                return

            for idx, row in enumerate(rows):
                row_frame = ctk.CTkFrame(
                    body_frame,
                    fg_color="#1b1f27" if idx % 2 == 0 else "#20242c",
                    height=34,
                    width=total_w,
                    corner_radius=0,
                )
                row_frame.pack(anchor="w", pady=(0, 1))
                row_frame.pack_propagate(False)
                for key, _, width in cols:
                    _make_cell(row_frame, row.get(key, ""), width, text_color="#e5e7eb")

        def _refresh_loop():
            try:
                if not dialog.winfo_exists():
                    return
            except Exception:
                return

            _render_rows(_collect_rows())
            dialog.after(1000, _refresh_loop)

        _refresh_loop()

    def open_ffmpeg_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("FFmpeg")
        dialog.geometry("900x320")
        dialog.transient(self.root)
        dialog.grab_set()

        self.root.update_idletasks()
        x = self.root.winfo_x() + max(0, (self.root.winfo_width() - 900) // 2)
        y = self.root.winfo_y() + max(0, (self.root.winfo_height() - 320) // 2)
        dialog.geometry(f"900x320+{x}+{y}")

        top = ctk.CTkFrame(dialog, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(top, text="🎞️ FFMPEG (ALL MACHINES)", font=("Arial", 13, "bold")).pack(side="left")

        holder = ctk.CTkFrame(dialog)
        holder.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        import tkinter as tk

        table_canvas = tk.Canvas(holder, bg="#171a1f", highlightthickness=0)
        vsb = ctk.CTkScrollbar(
            holder,
            orientation="vertical",
            command=table_canvas.yview,
            fg_color="#1f2329",
            button_color="#4b5563",
            button_hover_color="#6b7280",
        )
        hsb = ctk.CTkScrollbar(
            holder,
            orientation="horizontal",
            command=table_canvas.xview,
            fg_color="#1f2329",
            button_color="#4b5563",
            button_hover_color="#6b7280",
        )
        table_canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        table_canvas.pack(side="left", fill="both", expand=True)

        cols = (
            ("machine", "Machine", 170),
            ("ip", "IP", 110),
            ("name", "Name", 170),
            ("pid", "PID", 80),
            ("send", "Send", 120),
            ("recv", "Recv", 120),
        )

        total_w = sum(w + 4 for _, _, w in cols) + 8
        table_inner = ctk.CTkFrame(table_canvas, fg_color="#171a1f", corner_radius=0, width=total_w)
        table_window_id = table_canvas.create_window((0, 0), window=table_inner, anchor="nw")

        def _on_inner_configure(_event=None):
            table_canvas.configure(scrollregion=table_canvas.bbox("all"))

        def _on_canvas_configure(event):
            table_canvas.itemconfigure(table_window_id, width=max(int(event.width), int(total_w)))

        table_inner.bind("<Configure>", _on_inner_configure)
        table_canvas.bind("<Configure>", _on_canvas_configure)

        def _make_cell(parent, text, width, text_color="#e5e7eb", bold=False):
            lbl = ctk.CTkLabel(
                parent,
                text=text,
                width=width,
                font=("Segoe UI", 11, "bold" if bold else "normal"),
                text_color=text_color,
                anchor="center",
            )
            lbl.pack(side="left", padx=2, pady=0)
            return lbl

        header = ctk.CTkFrame(table_inner, fg_color="#111827", height=36, width=total_w, corner_radius=0)
        header.pack(anchor="w", pady=(0, 2))
        header.pack_propagate(False)
        for _, label, width in cols:
            _make_cell(header, label, width, text_color="#e5e7eb", bold=True)

        body_frame = ctk.CTkFrame(table_inner, fg_color="transparent", width=total_w, corner_radius=0)
        body_frame.pack(anchor="w")

        def _format_mbps(value):
            try:
                return f"{float(value):.3f} Mbps"
            except (TypeError, ValueError):
                return "—"

        def _collect_rows():
            rows = []
            for entry in self.selected_data:
                d = entry.get("data", {}) if isinstance(entry, dict) else {}
                machine = str(d.get("name", "") or "")
                ip = str(d.get("ip", "") or "")
                for ff in self._normalize_dict_list(d.get("ffmpeg", [])):
                    rows.append({
                        "machine": machine,
                        "ip": ip,
                        "name": str(ff.get("name", "") or ""),
                        "pid": str(ff.get("pid", "") or ""),
                        "send": _format_mbps(ff.get("send", None)),
                        "recv": _format_mbps(ff.get("recv", None)),
                    })
            return rows

        def _render_rows(rows: list):
            for child in body_frame.winfo_children():
                child.destroy()

            if not rows:
                empty_row = ctk.CTkFrame(body_frame, fg_color="#1f2937", height=34, width=total_w, corner_radius=0)
                empty_row.pack(anchor="w", pady=(0, 1))
                empty_row.pack_propagate(False)
                _make_cell(empty_row, "(empty)", cols[0][2], text_color="#9ca3af")
                for _, _, width in cols[1:]:
                    _make_cell(empty_row, "", width, text_color="#9ca3af")
                return

            for idx, row in enumerate(rows):
                row_frame = ctk.CTkFrame(
                    body_frame,
                    fg_color="#1b1f27" if idx % 2 == 0 else "#20242c",
                    height=34,
                    width=total_w,
                    corner_radius=0,
                )
                row_frame.pack(anchor="w", pady=(0, 1))
                row_frame.pack_propagate(False)
                for key, _, width in cols:
                    _make_cell(row_frame, row.get(key, ""), width, text_color="#e5e7eb")

        def _refresh_loop():
            try:
                if not dialog.winfo_exists():
                    return
            except Exception:
                return

            _render_rows(_collect_rows())
            dialog.after(1000, _refresh_loop)

        _refresh_loop()

    def show_detail_from_entry(self, entry):
        self.detail_text.delete("1.0", "end")
        if entry:
            self.detail_text.insert("1.0", json.dumps(entry, indent=2, ensure_ascii=False))

    def show_detail_all(self, event):
        pass

    def show_detail_selected(self, event):
        pass

    def toggle_debug_page(self):
        if not hasattr(self, "showing_debug"):
            self.showing_debug = False
        
        if not self.showing_debug:
            if getattr(self, "showing_import_log", False):
                self.toggle_import_log_page()
            if getattr(self, "showing_setting", False):
                self.toggle_setting_page()
            # Switch to Debug page
            self.vertical_splitter.pack_forget()
            self.debug_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
            self.debug_nav_btn.configure(text="🖥️ Monitor", fg_color="#455a64", hover_color="#37474f")
            self.showing_debug = True
            self.refresh_debug_textbox()
        else:
            # Switch back to Monitor page
            self.debug_frame.pack_forget()
            self.vertical_splitter.pack(fill="both", expand=True, padx=10, pady=(5, 10))
            self._set_default_split_position()
            self.debug_nav_btn.configure(text="🐞 Debug", fg_color="#7e57c2", hover_color="#5e35b1")
            self.showing_debug = False

    def clear_debug_logs(self):
        if hasattr(self, "debug_textbox") and self.debug_textbox.winfo_exists():
            self.debug_textbox.delete("1.0", "end")

    def update_debug_logs_from_queue(self):
        try:
            has_new = False
            while not GLOBAL_LOG_QUEUE.empty():
                msg = GLOBAL_LOG_QUEUE.get_nowait()
                if hasattr(self, "debug_textbox") and self.debug_textbox.winfo_exists():
                    if isinstance(msg, list):
                        for text, tag in msg:
                            self.debug_textbox.insert("end", text, tag)
                        self.debug_textbox.insert("end", "\n")
                    else:
                        self.debug_textbox.insert("end", str(msg) + "\n")
                    has_new = True
            if has_new:
                # Keep at most 2000 lines to prevent memory issues
                num_lines = int(self.debug_textbox.index('end-1c').split('.')[0])
                if num_lines > 2000:
                    self.debug_textbox.delete("1.0", f"{num_lines - 2000}.0")
                self.debug_textbox.see("end")
        except Exception:
            pass
        self.root.after(200, self.update_debug_logs_from_queue)

    def refresh_debug_textbox(self):
        self.update_debug_logs_from_queue()

    def setup_import_log_ui(self):
        import tkinter as tk
        from tkinter import filedialog

        # Header inside import log frame
        hdr = ctk.CTkFrame(self.import_log_frame, fg_color="#1a1a1a", height=38)
        hdr.pack(fill="x", padx=0, pady=(0, 2))
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="📄 Import & Check Log File", font=("Arial", 10, "bold"), text_color="#FFB300").pack(side="left", padx=10)
        
        # Select file button
        ctk.CTkButton(hdr, text="📂 Chọn file Log (.txt)", command=self.select_and_import_log_file, fg_color="#4CAF50", hover_color="#45a049", width=160, height=26, font=("Arial", 9, "bold")).pack(side="left", padx=10)

        # Clear button
        ctk.CTkButton(hdr, text="🗑️ Clear Logs", command=self.clear_imported_logs, fg_color="#f44336", hover_color="#d32f2f", width=100, height=26, font=("Arial", 9, "bold")).pack(side="right", padx=10)

        # File path display label
        self.import_file_label = ctk.CTkLabel(hdr, text="Chưa chọn file log nào...", font=("Arial", 9), text_color="#9E9E9E")
        self.import_file_label.pack(side="left", padx=10)

        # Control/Filter bar
        ctrl_bar = ctk.CTkFrame(self.import_log_frame, fg_color="#1e1e1e", height=45)
        ctrl_bar.pack(fill="x", padx=5, pady=5)
        ctrl_bar.pack_propagate(False)

        # Machine Name filter (ComboBox)
        ctk.CTkLabel(ctrl_bar, text="Tên máy:", font=("Arial", 9, "bold")).pack(side="left", padx=(10, 2))
        self.import_machine_cb = ctk.CTkComboBox(
            ctrl_bar,
            values=["Tất cả"],
            width=160,
            font=("Arial", 10),
            dropdown_font=("Arial", 10),
            corner_radius=6,
            border_width=1,
            border_color="#555555",
            button_color="#2b2b2b",
            button_hover_color="#3a3a3a",
            dropdown_fg_color="#1e1e1e",
            dropdown_hover_color="#2b2b2b",
            dropdown_text_color="#ffffff",
            command=lambda e: self.apply_log_filters()
        )
        self.import_machine_cb.pack(side="left", padx=5)

        # IP filter
        ctk.CTkLabel(ctrl_bar, text="IP / WAN IP:", font=("Arial", 9, "bold")).pack(side="left", padx=(15, 2))
        self.import_ip_entry = ctk.CTkEntry(ctrl_bar, placeholder_text="Nhập IP để tìm...", width=160, font=("Arial", 9))
        self.import_ip_entry.pack(side="left", padx=5)
        self.import_ip_entry.bind("<KeyRelease>", self.apply_log_filters)

        # Time filter (Start - End)
        ctk.CTkLabel(ctrl_bar, text="Từ:", font=("Arial", 9, "bold")).pack(side="left", padx=(15, 2))
        self.import_start_time_entry = ctk.CTkEntry(ctrl_bar, placeholder_text="HH:MM:SS (VD: 08:00)", width=120, font=("Arial", 9))
        self.import_start_time_entry.pack(side="left", padx=5)
        self.import_start_time_entry.bind("<KeyRelease>", self.apply_log_filters)

        ctk.CTkLabel(ctrl_bar, text="Đến:", font=("Arial", 9, "bold")).pack(side="left", padx=(5, 2))
        self.import_end_time_entry = ctk.CTkEntry(ctrl_bar, placeholder_text="HH:MM:SS (VD: 17:00)", width=120, font=("Arial", 9))
        self.import_end_time_entry.pack(side="left", padx=5)
        self.import_end_time_entry.bind("<KeyRelease>", self.apply_log_filters)

        # Reset button
        ctk.CTkButton(ctrl_bar, text="🔄 Reset Bộ Lọc", command=self.reset_log_filters, fg_color="#555555", hover_color="#444444", width=120, height=26, font=("Arial", 9, "bold")).pack(side="left", padx=15)

        # Textbox for logs (similar to debug_textbox)
        self.import_textbox = ctk.CTkTextbox(self.import_log_frame, font=("Consolas", 10), fg_color="#1e1e1e", text_color="#00ff00")
        self.import_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        # Configure tags matching debug_textbox
        self.import_textbox.tag_config("log_time", foreground="#7F8C8D")      # cool gray
        self.import_textbox.tag_config("log_sep", foreground="#555555")       # dark gray
        self.import_textbox.tag_config("log_device", foreground="#3498DB")    # sky blue
        self.import_textbox.tag_config("metric_lbl", foreground="#E67E22")    # orange
        self.import_textbox.tag_config("metric_val", foreground="#1ABC9C")    # turquoise
        self.import_textbox.tag_config("srt_port", foreground="#BDC3C7")      # light gray
        self.import_textbox.tag_config("srt_on", foreground="#2ECC71")        # bright green
        self.import_textbox.tag_config("srt_off", foreground="#E74C3C")       # bright red

        self.parsed_log_entries = []

    def parse_log_line(self, line: str) -> dict | None:
        import re
        line = line.strip()
        if not line:
            return None

        # Extract timestamp
        timestamp_match = re.match(r"^\[\s*([^\]]+)\s*\]\s*-\s*(.*)$", line)
        if not timestamp_match:
            return None

        time_date_str = timestamp_match.group(1).strip()
        remaining = timestamp_match.group(2).strip()

        # Split time and date
        if "," in time_date_str:
            parts = time_date_str.split(",", 1)
            time_part = parts[0].strip()
            date_part = parts[1].strip()
        else:
            time_part = time_date_str
            date_part = ""

        # Extract machine name
        if remaining.startswith("["):
            machine_match = re.match(r"^\[\s*([^\]]+)\s*\]\s*-\s*(.*)$", remaining)
            if machine_match:
                machine_name = machine_match.group(1).strip()
                rest = machine_match.group(2).strip()
            else:
                parts = remaining.split(" - ", 1)
                machine_name = parts[0].strip()
                rest = parts[1].strip() if len(parts) > 1 else ""
        else:
            parts = remaining.split(" - ", 1)
            machine_name = parts[0].strip()
            rest = parts[1].strip() if len(parts) > 1 else ""

        # Parse fields using simple regular expressions
        def find_val(pattern, text):
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1).strip() if match else "—"

        ip_val = find_val(r"\b(?<!wan )ip:\s*([^\s\|]+)", rest)
        ipwan_val = find_val(r"\bwan\s+ip:\s*([^\s\|]+)", rest) or find_val(r"\bipwan:\s*([^\s\|]+)", rest)
        cpu_val = find_val(r"\bcpu:\s*([^\|]+)", rest)
        ram_val = find_val(r"\bram:\s*([^\|]+)", rest)
        gpu_val = find_val(r"\bgpu:\s*([^\|]+)", rest)
        ping_val = find_val(r"\bping:\s*([^\|]+)", rest)
        timeout_val = find_val(r"\btimeout:\s*([^\|]+)", rest) or find_val(r"\btimeouts:\s*([^\|]+)", rest)
        send_val = find_val(r"\bsend:\s*([^\|]+)", rest)
        recv_val = find_val(r"\brecv:\s*([^\|]+)", rest)
        res_val = find_val(r"\bres:\s*([^\|]+)", rest)
        rec_val = find_val(r"\brec:\s*([^\|]+)", rest)
        live_val = find_val(r"\blive:\s*([^\|]+)", rest)
        ext_val = find_val(r"\bext:\s*([^\|]+)", rest)
        srt_val = find_val(r"\bsrt\s+([^\|]+)", rest)

        datetime_str = f"{time_part}  {date_part}".strip()
        return {
            "raw": line,
            "time": time_part,
            "date": date_part,
            "datetime_str": datetime_str,
            "machine": machine_name,
            "ip": ip_val,
            "ipwan": ipwan_val,
            "cpu": cpu_val,
            "ram": ram_val,
            "gpu": gpu_val,
            "ping": ping_val,
            "timeout": timeout_val,
            "send": send_val,
            "recv": recv_val,
            "res": res_val,
            "rec": rec_val,
            "live": live_val,
            "ext": ext_val,
            "srt": srt_val,
        }

    def reconstruct_log_tags(self, line: str) -> list:
        import re
        line = line.strip()
        if not line:
            return []

        # 1. Extract timestamp
        timestamp_match = re.match(r"^(\[\s*[^\]]+\s*\])\s*-\s*(.*)$", line)
        if not timestamp_match:
            return [(line, "text")]
        
        time_part = timestamp_match.group(1)
        remaining = timestamp_match.group(2).strip()

        # 2. Extract machine name
        if remaining.startswith("["):
            machine_match = re.match(r"^(\[\s*[^\]]+\s*\])\s*-\s*(.*)$", remaining)
            if machine_match:
                device_name = machine_match.group(1)
                rest = machine_match.group(2).strip()
            else:
                parts = remaining.split(" - ", 1)
                device_name = parts[0]
                rest = parts[1] if len(parts) > 1 else ""
        else:
            parts = remaining.split(" - ", 1)
            device_name = parts[0]
            rest = parts[1] if len(parts) > 1 else ""

        parts_list = [
            (time_part, "log_time"),
            (" - ", "log_sep"),
            (device_name, "log_device"),
            (" - ", "log_sep")
        ]

        metrics_parts = rest.split(" | ")
        for idx, mp in enumerate(metrics_parts):
            mp = mp.strip()
            if not mp:
                continue

            if mp.upper().startswith("SRT"):
                srt_split = mp.split(" ", 1)
                parts_list.append((srt_split[0] + " ", "metric_lbl"))
                if len(srt_split) > 1:
                    ports_list = srt_split[1].split(", ")
                    for p_idx, port_status in enumerate(ports_list):
                        if ":" in port_status:
                            p_num, p_state = port_status.split(":", 1)
                            parts_list.append((p_num + ":", "srt_port"))
                            parts_list.append((p_state, "srt_on" if p_state.upper() == "ON" else "srt_off"))
                        else:
                            parts_list.append((port_status, "metric_val"))
                        if p_idx < len(ports_list) - 1:
                            parts_list.append((", ", "log_sep"))
            else:
                if ":" in mp:
                    k, v = mp.split(":", 1)
                    parts_list.append((k + ": ", "metric_lbl"))
                    v_clean = v.strip()
                    if v_clean in ("ON", "OFF"):
                        parts_list.append((v_clean, "srt_on" if v_clean == "ON" else "srt_off"))
                    else:
                        parts_list.append((v_clean, "metric_val"))
                else:
                    parts_list.append((mp, "metric_val"))

            if idx < len(metrics_parts) - 1:
                parts_list.append((" | ", "log_sep"))

        return parts_list

    def select_and_import_log_file(self):
        fpath = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Chọn file Log (.txt)"
        )
        if not fpath:
            return

        self.import_file_label.configure(text=f"Đang đọc: {fpath}...")
        self.root.update_idletasks()

        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            parsed_entries = []
            for line in lines:
                entry = self.parse_log_line(line)
                if entry:
                    parsed_entries.append(entry)

            if not parsed_entries:
                messagebox.showwarning("Cảnh báo", "Không tìm thấy dòng log hợp lệ nào trong file đã chọn!")
                self.import_file_label.configure(text="Chưa chọn file log nào...")
                return

            self.parsed_log_entries = parsed_entries
            self.import_file_label.configure(text=f"File: {fpath} ({len(parsed_entries)} dòng log)")

            # Populate machine filter dropdown values
            machines = sorted(list(set(entry["machine"] for entry in self.parsed_log_entries)))
            self.import_machine_cb.configure(values=["Tất cả"] + machines)
            self.import_machine_cb.set("Tất cả")

            # Apply filters (repopulates tree)
            self.apply_log_filters()
            messagebox.showinfo("Thành công", f"Đã import thành công {len(parsed_entries)} dòng log!")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Lỗi", f"Không thể import file log:\n{str(e)}")
            self.import_file_label.configure(text="Lỗi đọc file...")

    def apply_log_filters(self, event=None):
        if not hasattr(self, "parsed_log_entries") or not self.parsed_log_entries:
            return

        machine_filter = self.import_machine_cb.get()
        ip_filter = self.import_ip_entry.get().strip().lower()
        
        start_time_str = self.import_start_time_entry.get().strip()
        end_time_str = self.import_end_time_entry.get().strip()

        def parse_time_to_seconds(s: str) -> int | None:
            s = s.strip()
            if not s:
                return None
            parts = s.split(":")
            try:
                h = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 else 0
                sec = int(parts[2]) if len(parts) > 2 else 0
                return h * 3600 + m * 60 + sec
            except Exception:
                return None

        start_secs = parse_time_to_seconds(start_time_str)
        end_secs = parse_time_to_seconds(end_time_str)

        # Clear textbox
        self.import_textbox.configure(state="normal")
        self.import_textbox.delete("1.0", "end")

        for entry in self.parsed_log_entries:
            # Filter by machine name
            if machine_filter != "Tất cả" and entry["machine"] != machine_filter:
                continue

            # Filter by IP or WAN IP
            if ip_filter:
                ip_match = ip_filter in entry["ip"].lower()
                ipwan_match = ip_filter in entry["ipwan"].lower()
                if not (ip_match or ipwan_match):
                    continue

            # Filter by Time Range
            if start_secs is not None or end_secs is not None:
                entry_secs = parse_time_to_seconds(entry["time"])
                if entry_secs is not None:
                    if start_secs is not None and entry_secs < start_secs:
                        continue
                    if end_secs is not None and entry_secs > end_secs:
                        continue
                else:
                    # Exclude lines that don't have a valid parseable time if range filter is active
                    continue

            # Reconstruct tags and insert
            tag_parts = self.reconstruct_log_tags(entry["raw"])
            for text, tag in tag_parts:
                self.import_textbox.insert("end", text, tag)
            self.import_textbox.insert("end", "\n")

        self.import_textbox.configure(state="disabled")
        self.import_textbox.see("end")

    def reset_log_filters(self):
        self.import_machine_cb.set("Tất cả")
        self.import_ip_entry.delete(0, "end")
        self.import_start_time_entry.delete(0, "end")
        self.import_end_time_entry.delete(0, "end")
        self.apply_log_filters()

    def clear_imported_logs(self):
        self.parsed_log_entries = []
        self.import_file_label.configure(text="Chưa chọn file log nào...")
        self.import_machine_cb.configure(values=["Tất cả"])
        self.import_machine_cb.set("Tất cả")
        self.import_ip_entry.delete(0, "end")
        self.import_start_time_entry.delete(0, "end")
        self.import_end_time_entry.delete(0, "end")
        self.import_textbox.configure(state="normal")
        self.import_textbox.delete("1.0", "end")
        self.import_textbox.configure(state="disabled")

    def toggle_import_log_page(self):
        if not hasattr(self, "showing_import_log"):
            self.showing_import_log = False
 
        if not self.showing_import_log:
            # Close debug page if open
            if getattr(self, "showing_debug", False):
                self.toggle_debug_page()
            if getattr(self, "showing_setting", False):
                self.toggle_setting_page()
 
            self.vertical_splitter.pack_forget()
            self.import_log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
            self.import_log_nav_btn.configure(text="🖥️ Monitor", fg_color="#455a64", hover_color="#37474f")
            self.showing_import_log = True
        else:
            self.import_log_frame.pack_forget()
            self.vertical_splitter.pack(fill="both", expand=True, padx=10, pady=(5, 10))
            self._set_default_split_position()
            self.import_log_nav_btn.configure(text="📄 Import Log", fg_color="#FF5722", hover_color="#E64A19")
            self.showing_import_log = False

    def toggle_setting_page(self):
        if not hasattr(self, "showing_setting"):
            self.showing_setting = False

        if not self.showing_setting:
            if getattr(self, "showing_debug", False):
                self.toggle_debug_page()
            if getattr(self, "showing_import_log", False):
                self.toggle_import_log_page()

            self.vertical_splitter.pack_forget()
            self.setting_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
            self.setting_nav_btn.configure(text="🖥️ Monitor", fg_color="#455a64", hover_color="#37474f")
            self.showing_setting = True
        else:
            self.setting_frame.pack_forget()
            self.vertical_splitter.pack(fill="both", expand=True, padx=10, pady=(5, 10))
            self._set_default_split_position()
            self.setting_nav_btn.configure(text="⚙️ Setting", fg_color="#607D8B", hover_color="#455A64")
            self.showing_setting = False

    def setup_setting_ui(self):
        hdr = ctk.CTkFrame(self.setting_frame, fg_color="#1a1a1a", height=38)
        hdr.pack(fill="x", padx=0, pady=(0, 2))
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⚙️ App Settings & Webhooks", font=("Arial", 11, "bold"), text_color="#2196F3").pack(side="left", padx=10)

        container = ctk.CTkScrollableFrame(self.setting_frame, fg_color="#181818")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # ── 🔔 Webhooks Configuration Section ─────────────────────────────
        self.webhook_section = ctk.CTkFrame(container, fg_color="#1d1d1d", corner_radius=8)
        self.webhook_section.pack(fill="x", pady=(0, 15), padx=5)
        
        wh_title_bar = ctk.CTkFrame(self.webhook_section, fg_color="#2b2b2b", height=36, corner_radius=8)
        wh_title_bar.pack(fill="x")
        wh_title_bar.pack_propagate(False)
        
        ctk.CTkLabel(wh_title_bar, text="🔔 Notification Webhooks List", font=("Arial", 11, "bold"), text_color="#FFB300").pack(side="left", padx=15)
        
        # Add (+) Webhook button
        ctk.CTkButton(
            wh_title_bar, text="➕ Add Webhook", command=self.add_webhook_row,
            fg_color="#4CAF50", hover_color="#45a049", width=120, height=26, font=("Arial", 9, "bold")
        ).pack(side="right", padx=10)
        
        self.webhook_row_widgets = []

        # Populate existing webhooks
        existing_webhooks = self.settings_data.get("webhooks", [])
        if not existing_webhooks:
            legacy_webhook = self.settings_data.get("webhook", "")
            if not legacy_webhook and hasattr(self, "webhook_var"):
                legacy_webhook = self.webhook_var.get().strip()
            if legacy_webhook:
                existing_webhooks = [{"type": "Discord", "url": legacy_webhook}]
        
        for wh in existing_webhooks:
            self.add_webhook_row(wh.get("type", "Discord"), wh.get("url", ""))

        # ── 📈 Metric Validation Settings Section ──────────────────────────
        ctk.CTkLabel(container, text="📈 Metric Validation Settings", font=("Arial", 11, "bold"), text_color="#90CAF9", anchor="w").pack(fill="x", pady=(10, 5), padx=10)

        # Column headers
        header_row = ctk.CTkFrame(container, fg_color="#1a1a1a", height=36)
        header_row.pack(fill="x", pady=(0, 6), padx=5)
        header_row.pack_propagate(False)
        ctk.CTkLabel(header_row, text="METRIC", font=("Arial", 10, "bold"), width=150, anchor="w", text_color="#90CAF9").pack(side="left", padx=15)
        ctk.CTkLabel(header_row, text="CONDITION", font=("Arial", 10, "bold"), width=120, anchor="center", text_color="#90CAF9").pack(side="left", padx=10)
        ctk.CTkLabel(header_row, text="VALUE / THRESHOLD", font=("Arial", 10, "bold"), width=280, anchor="w", text_color="#90CAF9").pack(side="left", padx=10)
        ctk.CTkLabel(header_row, text="ĐƠN VỊ", font=("Arial", 10, "bold"), width=90, anchor="center", text_color="#90CAF9").pack(side="left", padx=5)
        ctk.CTkLabel(header_row, text="ERROR REPORT MODE", font=("Arial", 10, "bold"), width=250, anchor="w", text_color="#90CAF9").pack(side="left", padx=10)

        metrics_config = [
            ("status_app", "Status APP", True, False),
            ("srt_status", "SRT Status", True, False),
            ("ping", "Ping (ms)", False, False),
            ("timeout", "Time out", False, False),
            ("netspeed", "Net Speed", False, True),
            ("cpu", "CPU (%)", False, False),
            ("gpu", "GPU (%)", False, False),
            ("ram", "RAM (%)", False, False),
            ("sender", "Sender", False, True),
            ("receiver", "Receiver", False, True)
        ]

        self.setting_widgets = {}

        for idx, (key, label, is_status, has_unit) in enumerate(metrics_config):
            row = ctk.CTkFrame(container, fg_color="#242424" if idx % 2 == 0 else "transparent", height=50)
            row.pack(fill="x", pady=2, padx=5)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=label, font=("Arial", 11, "bold"), width=150, anchor="w").pack(side="left", padx=15)

            types = ["None", "Equal"] if is_status else ["None", "Equal", ">", "<", "Range"]
            type_var = ctk.StringVar(value=self.settings_data.get(key, {}).get("type", "None"))
            val1_var = ctk.StringVar(value=self.settings_data.get(key, {}).get("val1", ""))
            val2_var = ctk.StringVar(value=self.settings_data.get(key, {}).get("val2", ""))
            status_val_var = ctk.StringVar(value=self.settings_data.get(key, {}).get("val", "ON"))
            unit_var = ctk.StringVar(value=self.settings_data.get(key, {}).get("unit", "Mbps"))
            error_interval_var = ctk.StringVar(value=str(self.settings_data.get(key, {}).get("error_interval", 15)))

            widgets = {}
            cb_type = ctk.CTkComboBox(
                row, values=types, width=120, font=("Arial", 10),
                dropdown_font=("Arial", 10), variable=type_var,
                corner_radius=6, border_width=1, border_color="#555555"
            )
            cb_type.pack(side="left", padx=10)

            input_frame = ctk.CTkFrame(row, fg_color="transparent", width=280)
            input_frame.pack(side="left", padx=5)
            input_frame.pack_propagate(False)

            # Unit combobox area
            unit_frame = ctk.CTkFrame(row, fg_color="transparent", width=90)
            unit_frame.pack(side="left", padx=5)
            unit_frame.pack_propagate(False)
            if has_unit:
                cb_unit = ctk.CTkComboBox(
                    unit_frame, values=["Mbps", "Kbps", "Gbps"], width=85,
                    font=("Arial", 10), dropdown_font=("Arial", 10),
                    variable=unit_var, corner_radius=6, border_width=1, border_color="#555555"
                )
                cb_unit.pack(side="left", padx=2, pady=8)
                widgets["cb_unit"] = cb_unit
            else:
                ctk.CTkLabel(unit_frame, text="—", font=("Arial", 10), text_color="#555555").pack(side="left", padx=2, pady=8)

            # Error mode area
            error_frame = ctk.CTkFrame(row, fg_color="transparent", width=250)
            error_frame.pack(side="left", padx=10)
            error_frame.pack_propagate(False)
            if is_status:
                mode_inner = ctk.CTkFrame(error_frame, fg_color="#2a3a2a", corner_radius=6, height=32)
                mode_inner.pack(side="left", padx=2, pady=8)
                mode_inner.pack_propagate(False)
                ctk.CTkLabel(mode_inner, text="🔔 Báo 1 lần khi đổi trạng thái",
                             font=("Arial", 9, "bold"), text_color="#4CAF50", width=220).pack(padx=8, pady=4)
            else:
                mode_inner = ctk.CTkFrame(error_frame, fg_color="transparent")
                mode_inner.pack(side="left", padx=2, pady=8)
                ctk.CTkLabel(mode_inner, text="🔄 Loop mỗi", font=("Arial", 9, "bold"),
                             text_color="#FF9800").pack(side="left", padx=(0, 4))
                interval_entry = ctk.CTkEntry(
                    mode_inner, width=55, font=("Arial", 10), textvariable=error_interval_var,
                    placeholder_text="15", corner_radius=6, border_width=1,
                    border_color="#555555", justify="center"
                )
                interval_entry.pack(side="left", padx=2)
                ctk.CTkLabel(mode_inner, text="giây", font=("Arial", 9, "bold"),
                             text_color="#FF9800").pack(side="left", padx=(4, 0))
                widgets["interval_entry"] = interval_entry

            widgets["cb_type"] = cb_type
            widgets["val1_var"] = val1_var
            widgets["val2_var"] = val2_var
            widgets["status_val_var"] = status_val_var
            widgets["unit_var"] = unit_var
            widgets["error_interval_var"] = error_interval_var
            widgets["is_status"] = is_status
            widgets["has_unit"] = has_unit
            widgets["input_frame"] = input_frame

            def update_inputs(k=key, w=widgets):
                for child in w["input_frame"].winfo_children():
                    child.destroy()
                t = w["cb_type"].get()
                if t == "None":
                    ctk.CTkLabel(w["input_frame"], text="Không kiểm tra", font=("Arial", 10, "italic"), text_color="#777777").pack(side="left", padx=10, pady=8)
                elif w["is_status"]:
                    cb_val = ctk.CTkComboBox(
                        w["input_frame"], values=["ON", "OFF"], width=100,
                        font=("Arial", 10), dropdown_font=("Arial", 10),
                        variable=w["status_val_var"], corner_radius=6,
                        border_width=1, border_color="#555555"
                    )
                    cb_val.pack(side="left", padx=10, pady=8)
                else:
                    if t in ("Equal", ">", "<"):
                        entry1 = ctk.CTkEntry(
                            w["input_frame"], width=120, font=("Arial", 10),
                            textvariable=w["val1_var"], placeholder_text="Giá trị...",
                            corner_radius=6, border_width=1, border_color="#555555"
                        )
                        entry1.pack(side="left", padx=10, pady=8)
                    elif t == "Range":
                        ctk.CTkLabel(w["input_frame"], text="Từ:", font=("Arial", 10)).pack(side="left", padx=(10, 2), pady=8)
                        ctk.CTkEntry(
                            w["input_frame"], width=100, font=("Arial", 10),
                            textvariable=w["val1_var"], placeholder_text="Min...",
                            corner_radius=6, border_width=1, border_color="#555555"
                        ).pack(side="left", padx=2, pady=8)
                        ctk.CTkLabel(w["input_frame"], text="Đến:", font=("Arial", 10)).pack(side="left", padx=(10, 2), pady=8)
                        ctk.CTkEntry(
                            w["input_frame"], width=100, font=("Arial", 10),
                            textvariable=w["val2_var"], placeholder_text="Max...",
                            corner_radius=6, border_width=1, border_color="#555555"
                        ).pack(side="left", padx=2, pady=8)

            update_func = lambda k=key, w=widgets: update_inputs(k, w)
            widgets["update_func"] = update_func
            cb_type.configure(command=lambda e, uf=update_func: uf())
            update_func()

            self.setting_widgets[key] = widgets

        footer = ctk.CTkFrame(container, fg_color="transparent")
        footer.pack(fill="x", pady=20, padx=5)
        ctk.CTkButton(
            footer, text="💾 Save Settings", command=self.save_settings_action,
            fg_color="#4CAF50", hover_color="#45a049", width=160, font=("Arial", 10, "bold")
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            footer, text="🔄 Reset", command=self.reset_settings_action,
            fg_color="#f44336", hover_color="#d32f2f", width=120, font=("Arial", 10, "bold")
        ).pack(side="left", padx=10)

    def add_webhook_row(self, w_type="Discord", w_url=""):
        row_frame = ctk.CTkFrame(self.webhook_section, fg_color="transparent")
        row_frame.pack(fill="x", pady=5, padx=10)
        
        # Combobox for Type
        type_var = ctk.StringVar(value=w_type)
        cb_type = ctk.CTkComboBox(
            row_frame, values=["Discord", "Seatalk"], width=120, font=("Arial", 10),
            dropdown_font=("Arial", 10), variable=type_var,
            corner_radius=6, border_width=1, border_color="#555555"
        )
        cb_type.pack(side="left", padx=5)
        
        # Entry for URL
        url_entry = ctk.CTkEntry(
            row_frame, placeholder_text="Enter Webhook URL...", font=("Arial", 10),
            corner_radius=6, border_width=1, border_color="#555555"
        )
        url_entry.insert(0, w_url)
        url_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Delete button
        btn_del = ctk.CTkButton(
            row_frame, text="❌", width=36, height=28,
            fg_color="#f44336", hover_color="#d32f2f",
            command=lambda: self.remove_webhook_row(row_frame)
        )
        btn_del.pack(side="right", padx=5)
        
        self.webhook_row_widgets.append({
            "frame": row_frame,
            "cb_type": cb_type,
            "url_entry": url_entry
        })

    def remove_webhook_row(self, row_frame):
        for item in list(self.webhook_row_widgets):
            if item["frame"] == row_frame:
                row_frame.destroy()
                self.webhook_row_widgets.remove(item)
                break

    def save_settings_action(self):
        # Collect webhooks
        webhooks_list = []
        for item in self.webhook_row_widgets:
            w_type = item["cb_type"].get()
            w_url = item["url_entry"].get().strip()
            if w_url:
                webhooks_list.append({"type": w_type, "url": w_url})
        
        self.settings_data["webhooks"] = webhooks_list
        if webhooks_list:
            self.settings_data["webhook"] = webhooks_list[0]["url"]
            if hasattr(self, "webhook_var"):
                self.webhook_var.set(webhooks_list[0]["url"])
        else:
            self.settings_data["webhook"] = ""
            if hasattr(self, "webhook_var"):
                self.webhook_var.set("")

        for key, w in self.setting_widgets.items():
            t = w["cb_type"].get()
            self.settings_data[key]["type"] = t
            if w["is_status"]:
                self.settings_data[key]["val"] = w["status_val_var"].get()
                self.settings_data[key]["error_mode"] = "once"
            else:
                self.settings_data[key]["val1"] = w["val1_var"].get()
                self.settings_data[key]["val2"] = w["val2_var"].get()
                self.settings_data[key]["error_mode"] = "loop"
                try:
                    self.settings_data[key]["error_interval"] = max(1, int(w["error_interval_var"].get()))
                except (ValueError, TypeError):
                    self.settings_data[key]["error_interval"] = 15
            if w.get("has_unit"):
                self.settings_data[key]["unit"] = w["unit_var"].get()
        
        self.save_settings()
        self.update_selected_table()
        messagebox.showinfo("Thành công", "Đã lưu cài đặt và áp dụng thành công!")

    def reset_settings_action(self):
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn đặt lại tất cả cài đặt giới hạn về mặc định?"):
            return
        
        # Clear webhooks
        for item in list(self.webhook_row_widgets):
            item["frame"].destroy()
        self.webhook_row_widgets.clear()
        self.settings_data["webhooks"] = []
        if hasattr(self, "webhook_var"):
            self.webhook_var.set("")

        for key, w in self.setting_widgets.items():
            w["cb_type"].set("None")
            if w["is_status"]:
                w["status_val_var"].set("ON")
                self.settings_data[key] = {"type": "None", "val": "ON", "error_mode": "once"}
            else:
                w["val1_var"].set("")
                w["val2_var"].set("")
                w["error_interval_var"].set("15")
                default_entry = {"type": "None", "val1": "", "val2": "", "error_mode": "loop", "error_interval": 15}
                if w.get("has_unit"):
                    w["unit_var"].set("Mbps")
                    default_entry["unit"] = "Mbps"
                self.settings_data[key] = default_entry
            w["update_func"]()
            
        self.save_settings()
        self.update_selected_table()
        messagebox.showinfo("Thành công", "Đã đặt lại cài đặt về mặc định!")

    def check_violation(self, key, value_str) -> bool:
        if not hasattr(self, "settings_data"):
            return False
        rule = self.settings_data.get(key)
        if not rule or rule.get("type") == "None":
            return False

        rule_type = rule.get("type")
        val1_str = rule.get("val1", "")
        val2_str = rule.get("val2", "")

        if key in ("status_app", "srt_status"):
            target = rule.get("val", "ON")
            actual = str(value_str).strip().upper()
            return actual != target.upper()

        def parse_numeric(v):
            if v is None:
                return None
            v_str = str(v).strip().lower()
            if not v_str or v_str in ("—", "off", "none", "null"):
                return None
            v_clean = re.sub(r"[^\d\.]", "", v_str)
            try:
                value = float(v_clean)
                if "gbps" in v_str:
                    value *= 1000
                elif "kbps" in v_str:
                    value /= 1000
                return value
            except ValueError:
                return None

        def convert_threshold_to_mbps(v_str):
            """Convert user-entered threshold value to Mbps based on the rule's unit setting."""
            if v_str is None:
                return None
            v_str_clean = str(v_str).strip()
            if not v_str_clean:
                return None
            try:
                value = float(v_str_clean)
            except ValueError:
                return parse_numeric(v_str_clean)
            unit = rule.get("unit", "Mbps")
            if unit == "Kbps":
                value /= 1000
            elif unit == "Gbps":
                value *= 1000
            return value

        val = parse_numeric(value_str)
        if val is None:
            # If checking is active but reported value is offline/empty, mark as violation
            return True

        # Use unit-aware conversion for threshold values if metric has unit
        has_unit = key in ("netspeed", "sender", "receiver")
        if has_unit:
            v1 = convert_threshold_to_mbps(val1_str)
            v2 = convert_threshold_to_mbps(val2_str)
        else:
            v1 = parse_numeric(val1_str)
            v2 = parse_numeric(val2_str)

        if rule_type == "Equal":
            if v1 is None: return False
            return abs(val - v1) > 0.001
        elif rule_type == ">":
            if v1 is None: return False
            return val > v1
        elif rule_type == "<":
            if v1 is None: return False
            return val < v1
        elif rule_type == "Range":
            if v1 is None or v2 is None: return False
            return not (v1 <= val <= v2)

        return False

    def get_metric_color(self, key, val_str, default_color="#ffffff") -> str:
        if self.check_violation(key, val_str):
            return "#f44336"
        return default_color
