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

class ServerDataGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Server Log Viewer - Dual Panel")
        self.root.geometry("2000x750")

        self.api_url = "https://tooldiscordvmix.onrender.com/logs"
        self.ws_url = "wss://tooldiscordvmix.onrender.com/ws"
        self.webhook_var = ctk.StringVar(value="")
        self.prefix_var = ctk.StringVar(value="SRT")
        self.data = []  # All data from database
        self.selected_data = []  # Selected items to monitor
        self.previous_data = []
        self.auto_send_enabled = False
        self.is_sending = False  # Flag để tránh gửi duplicate
        
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
        ctk.CTkLabel(row1, text="Discord Webhook:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.webhook_entry = ctk.CTkEntry(row1, textvariable=self.webhook_var, width=600)
        self.webhook_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Row 2: Prefix and buttons
        row2 = ctk.CTkFrame(top_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Prefix:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.prefix_entry = ctk.CTkEntry(row2, textvariable=self.prefix_var, width=80)
        self.prefix_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(row2, text="� Scan máy", command=self.refresh_data, fg_color="#4CAF50", hover_color="#45a049", width=110, font=("Arial", 12, "bold")).pack(side="left", padx=3)
        self.toggle_btn = ctk.CTkButton(row2, text="AUTO SEND: OFF", command=self.toggle_auto_send, fg_color="#9E9E9E", hover_color="#757575", width=140, font=("Arial", 12, "bold"))
        self.toggle_btn.pack(side="left", padx=3)
        ctk.CTkButton(row2, text="➡️ Add", command=self.add_to_selected, fg_color="#2196F3", hover_color="#1976D2", width=90).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="🗑️ Clear", command=self.clear_selected, fg_color="#f44336", hover_color="#d32f2f", width=90).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="💾 Save", command=self.save_selected_to_file, fg_color="#9C27B0", hover_color="#7B1FA2", width=90).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="📂 Open", command=self.load_selected_from_file, fg_color="#673AB7", hover_color="#512DA8", width=90).pack(side="left", padx=3)
        
        # Connection status
        self.status_label = ctk.CTkLabel(row2, text="⚪ Disconnected", font=("Arial", 11, "bold"), text_color="#9E9E9E")
        self.status_label.pack(side="right", padx=10)

        # Main content area - Split into 2 panels
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Configure grid
        # Configure grid - Thu nhỏ tối đa cột 0 (trái), mở rộng cột 1 (phải)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=6)
        main_frame.grid_rowconfigure(0, weight=1)

        # LEFT PANEL - All logs from database (scan)
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        ctk.CTkLabel(left_frame, text="📡 ALL LOGS FROM DATABASE", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Left table - Custom with checkboxes
        self.table_frame_left = ctk.CTkScrollableFrame(left_frame, fg_color="#2b2b2b")
        self.table_frame_left.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header
        header_frame = ctk.CTkFrame(self.table_frame_left, fg_color="#1a1a1a", height=40)
        header_frame.pack(fill="x", pady=(0, 5))
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(header_frame, text="☑",   font=("Arial", 13, "bold"), width=35).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="STT", font=("Arial", 13, "bold"), width=40).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="IP MÁY", font=("Arial", 13, "bold"), width=120).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="PORT",  font=("Arial", 13, "bold"), width=70).pack(side="left", padx=2)
        
        self.left_table_rows = []
        self.left_table_checkboxes = {}

        # RIGHT PANEL - Selected logs to monitor
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        ctk.CTkLabel(right_frame, text="⭐ SELECTED MONITOR LIST", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Right table - Custom scrollable
        self.table_frame_right = ctk.CTkScrollableFrame(right_frame, fg_color="#2b2b2b")
        self.table_frame_right.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header
        header_frame_right = ctk.CTkFrame(self.table_frame_right, fg_color="#1a1a1a", height=40)
        header_frame_right.pack(fill="x", pady=(0, 5))
        header_frame_right.pack_propagate(False)
        
        ctk.CTkLabel(header_frame_right, text="STT",     font=("Arial", 13, "bold"), width=40).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="TÊN",     font=("Arial", 13, "bold"), width=120).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="IP MÁY",   font=("Arial", 13, "bold"), width=120).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="IP WAN",   font=("Arial", 13, "bold"), width=120).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="STATUS",   font=("Arial", 13, "bold"), width=80).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="PORT",     font=("Arial", 13, "bold"), width=70).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="APP",      font=("Arial", 13, "bold"), width=55).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="📡 PING",   font=("Arial", 13, "bold"), width=80).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="❌ TIMEOUT",font=("Arial", 13, "bold"), width=80).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="⚡ CPU%",   font=("Arial", 13, "bold"), width=75).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="💾 RAM%",   font=("Arial", 13, "bold"), width=75).pack(side="left", padx=2)
        ctk.CTkLabel(header_frame_right, text="TIME",     font=("Arial", 13, "bold"), width=145).pack(side="left", padx=2)
        
        self.right_table_rows = []

        # Detail area
        detail_frame = ctk.CTkFrame(self.root)
        detail_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        ctk.CTkLabel(detail_frame, text="📄 DETAIL (select a row)", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.detail_text = ctk.CTkTextbox(detail_frame, height=100, font=("Consolas", 10), fg_color="#1e1e1e", text_color="#00ff00")
        self.detail_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Load initial data once
        self.refresh_data()
        
        # Load selected list from database
        self.load_selected_from_database()
        
        # Start WebSocket connection if enabled
        if self.use_websocket:
            self.connect_websocket()
        else:
            # Fallback to REST polling
            self.start_rest_polling_backup()

    def connect_websocket(self):
        """Kết nối WebSocket để nhận realtime updates"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                print(f"📩 WebSocket received: {len(data)} items")
                
                # Update data
                if isinstance(data, list):
                    # Check if có thay đổi về danh sách IP+Port
                    has_list_changed = self.has_data_changed(self.data, data)
                    
                    self.data = data
                    
                    # Nếu có thay đổi danh sách -> update bảng trái
                    if has_list_changed:
                        print("✓ WebSocket: Danh sách máy thay đổi, update bảng trái")
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
                resp = requests.get(self.api_url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
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
            url = self.api_url
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
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
            print("⏳ Đang gửi, bỏ qua request...")
            return
        
        webhook = self.webhook_var.get().strip()
        if not webhook or not self.selected_data:
            return
        
        # Lấy snapshot hiện tại
        current_snapshot = self.get_data_snapshot()
        
        # Nếu chưa có previous_data (lần đầu), chỉ lưu snapshot, không gửi
        if not self.previous_data:
            self.previous_data = current_snapshot
            print("📸 Lưu snapshot đầu tiên, không gửi Discord")
            return
        
        # So sánh với previous_data
        if current_snapshot == self.previous_data:
            print("✓ Không có thay đổi, không gửi Discord")
            return
        
        self.is_sending = True
        
        def send():
            try:
                prefix = self.prefix_var.get().strip()
                
                # Tạo dict để so sánh nhanh
                prev_dict = {f"{item['name']}:{item['port']}": item for item in self.previous_data}
                curr_dict = {f"{item['name']}:{item['port']}": item for item in current_snapshot}
                
                # Tìm những item có thay đổi về STATUS hoặc IPWAN (KHÔNG BAO GỒM APP STATUS)
                changed_items = []
                
                for key, curr_item in curr_dict.items():
                    prev_item = prev_dict.get(key)
                    
                    # Chỉ check thay đổi về STATUS (SRT) và IPWAN
                    if not prev_item or (
                        prev_item['status'] != curr_item['status'] or
                        prev_item['ipwan'] != curr_item['ipwan']
                    ):
                        changed_items.append(curr_item)
                        if prev_item:
                            print(f"🔔 Thay đổi [{curr_item['name']}]: Status {prev_item['status']}→{curr_item['status']}, IPWAN {prev_item['ipwan']}→{curr_item['ipwan']}")
                
                # Nếu có thay đổi, chỉ gửi những item thay đổi
                if changed_items:
                    messages = []
                    
                    # Thêm tiêu đề với thời gian
                    now = datetime.now(VIETNAM_TZ)
                    title = f"=== STATUS CHANGED - {now.strftime('%d/%m/%Y %H:%M:%S')} ==="
                    messages.append(title)
                    
                    # Chỉ gửi những item có thay đổi
                    for curr_item in changed_items:
                        name = curr_item['name']
                        ipwan = curr_item['ipwan']
                        port = curr_item['port']
                        status = curr_item['status']
                        
                        msg = f"[{prefix}][{name}] SRT {status} | IPWAN: {ipwan} | PORT: {port}"
                        messages.append(msg)
                    
                    payload = {"content": "\n".join(messages)}
                    
                    resp = requests.post(webhook, json=payload, timeout=10)
                    if resp.status_code in [200, 204]:
                        print(f"✓ Sent {len(changed_items)} changed items to Discord")
                        # CẬP NHẬT previous_data sau khi gửi thành công
                        self.previous_data = current_snapshot
                    else:
                        print(f"✗ Discord error: {resp.status_code}")
                else:
                    print("✓ Không có item nào thay đổi về STATUS hoặc IPWAN")
                    # Vẫn cập nhật previous_data
                    self.previous_data = current_snapshot
                    
            except Exception as e:
                print(f"✗ Failed to send: {e}")
            finally:
                self.is_sending = False
        
        threading.Thread(target=send, daemon=True).start()

    def refresh_data(self):
        """Refresh all logs from database"""
        def fetch():
            url = self.api_url
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, list):
                            # So sánh data mới với data cũ
                            if self.has_data_changed(self.data, data):
                                print("✓ Data changed, refreshing table...")
                                self.data = data
                                self.update_all_table()
                                # Also update selected data with new info
                                self.update_selected_data()
                                self.update_selected_table()
                            else:
                                # Chỉ update selected table (để cập nhật status realtime)
                                self.update_selected_data()
                                self.update_selected_table()
                        else:
                            self.data = []
                    except Exception as e:
                        messagebox.showerror("Error", f"JSON decode error: {e}")
                else:
                    messagebox.showerror("Error", f"HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                messagebox.showerror("Error", f"ERROR: {str(e)}")
        threading.Thread(target=fetch, daemon=True).start()
    
    def has_data_changed(self, old_data, new_data):
        """Check if data has changed (compare IP+Port list)"""
        if len(old_data) != len(new_data):
            return True
        
        # So sánh danh sách IP+Port
        old_set = set()
        for entry in old_data:
            d = entry.get("data", {})
            old_set.add(f"{d.get('ip', '')}:{d.get('port', '')}")
        
        new_set = set()
        for entry in new_data:
            d = entry.get("data", {})
            new_set.add(f"{d.get('ip', '')}:{d.get('port', '')}")
        
        return old_set != new_set

    def update_all_table(self):
        """Update left table with all logs - Custom view with checkboxes"""
        # Clear old rows
        for row in self.left_table_rows:
            row.destroy()
        self.left_table_rows = []
        self.left_table_checkboxes = {}
        
        stt = 1
        for idx, entry in enumerate(self.data):
            d = entry.get("data", {})
            ip = d.get("ip", "")
            port = d.get("port", "")
            statusapp = d.get("statusapp", 0)
            
            # Create row frame
            row_frame = ctk.CTkFrame(self.table_frame_left, 
                                     fg_color="#3a3a3a" if stt % 2 == 0 else "#2b2b2b", 
                                     height=45)
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
            stt_label = ctk.CTkLabel(row_frame, text=str(stt), font=("Arial", 12, "bold"), width=40, anchor="center")
            stt_label.pack(side="left", padx=2)
            
            # IP
            ip_color = "#4CAF50" if statusapp == 1 else "#f44336"
            ip_label = ctk.CTkLabel(row_frame, text=ip, font=("Arial", 12, "bold"), width=120, text_color=ip_color, anchor="center")
            ip_label.pack(side="left", padx=2)
            
            # Port
            port_label = ctk.CTkLabel(row_frame, text=port, font=("Arial", 12, "bold"), width=70, anchor="center")
            port_label.pack(side="left", padx=2)
            
            # Bind click event for details (only on labels, not checkbox)
            for widget in [row_frame, stt_label, ip_label, port_label]:
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
            name = d.get("name", "").strip()
            if not name:
                name = f"MÁY {stt}"
            ip          = d.get("ip", "")
            ipwan       = d.get("ipwan", "")
            status      = d.get("status", "")
            port        = d.get("port", "")
            statusapp   = d.get("statusapp", 0)
            statusapp_text = "ON" if statusapp == 1 else "OFF"
            # ── Thông số mới ──
            ping         = d.get("ping", None)
            ping_timeouts= d.get("ping_timeouts", 0)
            cpu          = d.get("cpu", None)
            memory       = d.get("memory", None)
            ping_str     = f"{ping:.0f} ms" if ping is not None else "—"
            timeout_str  = str(ping_timeouts) if ping_timeouts is not None else "0"
            cpu_str      = f"{cpu:.1f}%"   if cpu    is not None else "—"
            mem_str      = f"{memory:.1f}%" if memory is not None else "—"
            
            # Create row frame
            row_frame = ctk.CTkFrame(self.table_frame_right,
                                     fg_color="#3a3a3a" if stt % 2 == 0 else "#2b2b2b",
                                     height=45)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)
            
            # Hàm helper để tạo label và bind click
            def create_clickable_label(parent, text, width, font=("Arial", 12, "bold"), text_color=None, anchor="center"):
                lbl = ctk.CTkLabel(parent, text=text, font=font, width=width, text_color=text_color, anchor=anchor)
                lbl.pack(side="left", padx=2)
                lbl.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))
                return lbl

            # STT
            create_clickable_label(row_frame, str(stt), 40)
            
            # Name (editable on double-click)
            name_frame = ctk.CTkFrame(row_frame, fg_color="transparent", width=120)
            name_frame.pack(side="left", padx=2)
            name_frame.pack_propagate(False)
            name_label = ctk.CTkLabel(name_frame, text=name, font=("Arial", 12, "bold"), anchor="center")
            name_label.pack(fill="both", expand=True)
            name_label.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))
            name_label.bind("<Double-1>", lambda e, idx=stt-1, frame=name_frame, lbl=name_label: self.edit_name_inline(idx, frame, lbl))
            
            # Các cột thông tin
            create_clickable_label(row_frame, ip,    120)
            create_clickable_label(row_frame, ipwan, 120)
            
            status_color = "#4CAF50" if status == "ON" else "#f44336"
            create_clickable_label(row_frame, status, 80, text_color=status_color)
            
            create_clickable_label(row_frame, port, 70)
            
            app_color = "#4CAF50" if statusapp == 1 else "#f44336"
            create_clickable_label(row_frame, statusapp_text, 55, text_color=app_color)
            
            ping_color = "#4CAF50" if ping is not None else "#9E9E9E"
            create_clickable_label(row_frame, ping_str, 80, font=("Arial", 11), text_color=ping_color)
            
            to_color = "#f44336" if ping_timeouts and int(ping_timeouts) > 0 else "#9E9E9E"
            create_clickable_label(row_frame, timeout_str, 80, font=("Arial", 11, "bold"), text_color=to_color)
            
            create_clickable_label(row_frame, cpu_str, 75, font=("Arial", 11))
            create_clickable_label(row_frame, mem_str, 75, font=("Arial", 11))
            create_clickable_label(row_frame, ts, 145, font=("Arial", 10))
            
            # Delete button (Không bind click detail vào đây)
            delete_btn = ctk.CTkButton(row_frame, text="❌", width=30, height=30, fg_color="#f44336", hover_color="#d32f2f",
                                       command=lambda idx=stt-1: self.remove_single_item(idx))
            delete_btn.pack(side="right", padx=5)
            
            # Bind click cho cả frame background
            row_frame.bind("<Button-1>", lambda e, ent=entry: self.show_detail_from_entry(ent))
            
            self.right_table_rows.append(row_frame)
            stt += 1

    def is_in_selected(self, entry):
        """Check if entry is in selected list - Check by IP + PORT"""
        d = entry.get("data", {})
        ip = d.get("ip", "")
        port = d.get("port", "")
        for sel in self.selected_data:
            sel_d = sel.get("data", {})
            if sel_d.get("ip", "") == ip and sel_d.get("port", "") == port:
                return True
        return False

    def on_checkbox_toggle(self, entry, checkbox_var):
        """Handle checkbox toggle - Just mark, don't add yet"""
        # Chỉ đánh dấu, không add/remove ngay
        # User sẽ phải ấn button "Add" để chuyển sang list
        pass
    
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
        
        print(f"Total added: {added_count}")
        
        if added_count > 0:
            print(f"✓ Successfully added: {added_count} item(s)")
            self.save_selected_to_database()  # Lưu vào database
            self.update_all_table()  # Refresh to update checkbox states
            self.update_selected_table()
        else:
            messagebox.showinfo("Info", "No new items to add. Check the boxes first!")

    def remove_single_item(self, idx):
        """Remove single item from selected list"""
        if idx < len(self.selected_data):
            removed = self.selected_data.pop(idx)
            print(f"✗ Removed: {removed.get('data', {}).get('name', 'Unknown')}")
            self.save_selected_to_database()  # Lưu vào database
            self.update_all_table()
            self.update_selected_table()
    
    def remove_from_selected(self):
        """Remove all selected items"""
        if not self.selected_data:
            messagebox.showwarning("Warning", "No items in the selected list")
            return
        
        result = messagebox.askyesno("Confirm", f"Remove all {len(self.selected_data)} items?")
        if result:
            self.selected_data = []
            self.save_selected_to_database()  # Lưu vào database
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
                        self.refresh_data()
                    else:
                        print(f"✗ Update error: {resp.status_code}")
                except Exception as e:
                    print(f"✗ Error: {e}")
            
            threading.Thread(target=update_name, daemon=True).start()
            self.update_selected_table()

    def update_selected_data(self):
        """Update selected data with latest info from database - Match by NAME or PORT"""
        for i, sel_entry in enumerate(self.selected_data):
            sel_d = sel_entry.get("data", {})
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
                    print(f"🔄 Updated by NAME: {sel_name} - New IP: {entry_d.get('ip', '')}, New IPWAN: {entry_d.get('ipwan', '')}")
                    break
                # Nếu không có name, match theo PORT
                elif not sel_name and sel_port and sel_port == entry_port:
                    self.selected_data[i] = entry
                    matched = True
                    print(f"🔄 Updated by PORT: {sel_port} - New IP: {entry_d.get('ip', '')}, New IPWAN: {entry_d.get('ipwan', '')}")
                    break
            
            if not matched:
                print(f"⚠ Cannot find match for: {sel_name or sel_port}")

    def clear_selected(self):
        """Clear selected list"""
        self.selected_data = []
        self.save_selected_to_database()  # Lưu vào database (rỗng)
        self.update_selected_table()
        self.update_all_table()
        self.detail_text.delete("1.0", "end")

    def save_selected_to_file(self):
        """Save selected list to JSON file"""
        if not self.selected_data:
            messagebox.showwarning("Warning", "No data to save. Please add items to the monitor list first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="selected_monitors.json"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.selected_data, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Success", f"Saved {len(self.selected_data)} items to:\n{filename}")
                print(f"✓ Saved {len(self.selected_data)} items to: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
                print(f"✗ Save error: {e}")

    def load_selected_from_file(self):
        """Load selected list from JSON file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Open Monitor List"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                if not isinstance(loaded_data, list):
                    messagebox.showerror("Error", "Invalid file format. Expected a JSON array.")
                    return
                
                # Replace current selected data
                self.selected_data = loaded_data
                self.save_selected_to_database()  # Lưu vào database
                self.update_selected_table()
                self.update_all_table()
                
                messagebox.showinfo("Success", f"Loaded {len(self.selected_data)} items from:\n{filename}")
                print(f"✓ Loaded {len(self.selected_data)} items from: {filename}")
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
                url = "https://tooldiscordvmix.onrender.com/save_selected_list"
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
                url = "https://tooldiscordvmix.onrender.com/load_selected_list"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    loaded_data = resp.json()
                    if isinstance(loaded_data, list):
                        self.selected_data = loaded_data
                        print(f"✓ Loaded {len(self.selected_data)} items from database")
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
