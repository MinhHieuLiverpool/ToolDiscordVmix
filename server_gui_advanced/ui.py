import json
import threading
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
import requests

try:
    from .shared import VIETNAM_TZ, pretty_time
except ImportError:
    try:
        from server_gui_advanced.shared import VIETNAM_TZ, pretty_time
    except ImportError:
        from shared import VIETNAM_TZ, pretty_time


class ServerDataGUIUIMixin:
    def setup_main_ui(self):
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
        self.vertical_splitter = self._create_vertical_splitter()
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

        ctk.CTkLabel(header_frame_right, text="STT", font=("Arial", 10, "bold"), width=35).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="TÊN", font=("Arial", 10, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="IP MÁY", font=("Arial", 10, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="IP WAN", font=("Arial", 10, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="STATUS", font=("Arial", 10, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="PORT", font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="APP", font=("Arial", 10, "bold"), width=45).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="📡 PING", font=("Arial", 10, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="❌ TIMEOUT", font=("Arial", 10, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="⚡ CPU%", font=("Arial", 10, "bold"), width=65).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="💾 RAM%", font=("Arial", 10, "bold"), width=65).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="● REC", font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🔴 LIVE", font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🟢 EXT", font=("Arial", 10, "bold"), width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="🖥 RES", font=("Arial", 10, "bold"), width=90).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="📹 SRT", font=("Arial", 10, "bold"), width=180).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="TIME", font=("Arial", 10, "bold"), width=130).pack(side="left", padx=2)

        self.right_table_rows = []

        # vmPing panel
        vmping_outer = ctk.CTkFrame(self.vertical_splitter, fg_color="#181818")
        self.vertical_splitter.add(vmping_outer, minsize=170)

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
        dlg_w = min(700, max(520, int(root_w * 0.4)))
        dlg_h = min(460, max(460, int(root_h * 0.5)))
        x = self.root.winfo_x() + (root_w - dlg_w) // 2
        y = self.root.winfo_y() + (root_h - dlg_h) // 2
        self.scan_dialog.geometry(f"{dlg_w}x{dlg_h}+{x}+{y}")
        self.scan_dialog.minsize(520, 420)

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
            ip = d.get("ip", "")
            port = d.get("port", "")
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

            ip_color = "#4CAF50" if statusapp == 1 else "#f44336"
            ip_label = ctk.CTkLabel(row_frame, text=ip, font=("Arial", 11, "bold"), width=110, text_color=ip_color, anchor="center")
            ip_label.pack(side="left", padx=2)

            port_label = ctk.CTkLabel(row_frame, text=port, font=("Arial", 11, "bold"), width=60, anchor="center")
            port_label.pack(side="left", padx=2)

            for widget in [row_frame, stt_label, ip_label, port_label]:
                widget.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))

            self.left_table_rows.append(row_frame)
            stt += 1

    def update_selected_table(self):
        for row in self.right_table_rows:
            row.destroy()
        self.right_table_rows = []

        stt = 1
        for entry in self.selected_data:
            ts = pretty_time(entry.get("timestamp", ""))
            d = entry.get("data", {})
            name = d.get("name", "").strip() or f"MÁY {stt}"
            ip = d.get("ip", "")
            ipwan = d.get("ipwan", "")
            status = d.get("status", "")
            port = d.get("port", "")
            statusapp = d.get("statusapp", 0)
            statusapp_text = "ON" if statusapp == 1 else "OFF"

            ping = d.get("ping", None)
            ping_timeouts = d.get("ping_timeouts", 0)
            cpu = d.get("cpu", None)
            memory = d.get("memory", None)
            ping_str = f"{ping:.0f} ms" if ping is not None else "—"
            timeout_str = str(ping_timeouts) if ping_timeouts is not None else "0"
            cpu_str = f"{cpu:.1f}%" if cpu is not None else "—"
            mem_str = f"{memory:.1f}%" if memory is not None else "—"
            vmix_rec = d.get("vmix_recording", False)
            vmix_live = d.get("vmix_streaming", False)
            vmix_ext = d.get("vmix_external", False)
            resolution = d.get("resolution", "—") or "—"
            srt_quality = d.get("srt_quality", "—") or "—"

            row_frame = ctk.CTkFrame(self.table_frame_right, fg_color="#3a3a3a" if stt % 2 == 0 else "#2b2b2b", height=35)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)

            def create_clickable_label(parent, text, width, font=("Arial", 10, "bold"), text_color=None, anchor="center"):
                lbl = ctk.CTkLabel(parent, text=text, font=font, width=width, text_color=text_color, anchor=anchor)
                lbl.pack(side="left", padx=2)
                lbl.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))
                return lbl

            create_clickable_label(row_frame, str(stt), 35)

            name_frame = ctk.CTkFrame(row_frame, fg_color="transparent", width=110)
            name_frame.pack(side="left", padx=2)
            name_frame.pack_propagate(False)
            name_label = ctk.CTkLabel(name_frame, text=name, font=("Arial", 10, "bold"), anchor="center")
            name_label.pack(fill="both", expand=True)
            name_label.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))
            name_label.bind("<Double-1>", lambda e, idx=stt - 1, frame=name_frame, lbl=name_label: self.edit_name_inline(idx, frame, lbl))

            create_clickable_label(row_frame, ip, 110)
            create_clickable_label(row_frame, ipwan, 110)

            status_color = "#4CAF50" if status == "ON" else "#f44336"
            create_clickable_label(row_frame, status, 70, text_color=status_color)
            create_clickable_label(row_frame, port, 60)

            app_color = "#4CAF50" if statusapp == 1 else "#f44336"
            create_clickable_label(row_frame, statusapp_text, 45, text_color=app_color)

            ping_color = "#4CAF50" if ping is not None else "#9E9E9E"
            create_clickable_label(row_frame, ping_str, 70, font=("Arial", 10), text_color=ping_color)
            to_color = "#f44336" if ping_timeouts and int(ping_timeouts) > 0 else "#9E9E9E"
            create_clickable_label(row_frame, timeout_str, 70, font=("Arial", 10, "bold"), text_color=to_color)

            create_clickable_label(row_frame, cpu_str, 65, font=("Arial", 10))
            create_clickable_label(row_frame, mem_str, 65, font=("Arial", 10))

            rec_color = "#f44336" if vmix_rec else "#555555"
            live_color = "#f44336" if vmix_live else "#555555"
            ext_color = "#4CAF50" if vmix_ext else "#555555"
            create_clickable_label(row_frame, "● ON" if vmix_rec else "○ OFF", 60, font=("Arial", 9), text_color=rec_color)
            create_clickable_label(row_frame, "● ON" if vmix_live else "○ OFF", 60, font=("Arial", 9), text_color=live_color)
            create_clickable_label(row_frame, "● ON" if vmix_ext else "○ OFF", 60, font=("Arial", 9), text_color=ext_color)
            create_clickable_label(row_frame, resolution, 90, font=("Arial", 9, "bold"), text_color="#4CAF50")
            create_clickable_label(row_frame, srt_quality, 180, font=("Arial", 9, "bold"), text_color="#f44336")
            create_clickable_label(row_frame, ts, 130, font=("Arial", 9))

            delete_btn = ctk.CTkButton(row_frame, text="❌", width=30, height=30, fg_color="#f44336", hover_color="#d32f2f", command=lambda idx=stt - 1: self.remove_single_item(idx))
            delete_btn.pack(side="right", padx=5)
            row_frame.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))

            self.right_table_rows.append(row_frame)
            stt += 1

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

    def _create_ping_card(self, host):
        idx = len(self.ping_hosts)
        col = idx % self.ping_grid_cols
        row = idx // self.ping_grid_cols

        card = ctk.CTkFrame(self.ping_cards_frame, fg_color="#2b2b2b", corner_radius=6, border_width=2, border_color="#3a3a3a")
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        title_bar = ctk.CTkFrame(card, fg_color="#9E9E9E", height=28, corner_radius=0)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        ctk.CTkLabel(title_bar, text=host, font=("Arial", 11, "bold"), text_color="#ffffff").pack(side="left", padx=8)

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

    def _rebuild_ping_grid(self):
        for idx, (host, info) in enumerate(self.ping_hosts.items()):
            col = idx % self.ping_grid_cols
            row = idx // self.ping_grid_cols
            info["card"].grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

    def on_double_click(self, event):
        pass

    def show_detail_from_entry(self, entry):
        self.detail_text.delete("1.0", "end")
        if entry:
            self.detail_text.insert("1.0", json.dumps(entry, indent=2, ensure_ascii=False))

    def show_detail_all(self, event):
        pass

    def show_detail_selected(self, event):
        pass
