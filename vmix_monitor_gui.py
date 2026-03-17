
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import subprocess
import threading
import queue
from datetime import datetime
import pytz
from PIL import Image, ImageDraw
import pystray
import socket
import sys

# Timezone configuration - Vietnam
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# Server URL - FastAPI server
SERVER_URL = "http://localhost:8000"

# Global socket for single instance
SINGLE_INSTANCE_SOCKET = None


class VmixMonitorGUI:
    def get_local_ip(self):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def __init__(self, root):
        self.root = root
        self.root.title("vMix Monitor Pro")
        
        # Set icon if exists
        try:
            self.root.iconbitmap('assets/Discord-Logo.ico')
        except:
            pass
        
        self.ip_var = tk.StringVar(value=self.get_local_ip())
        self.name_var = tk.StringVar(value="")
        self.port_var = tk.StringVar(value="")
        self.is_running = False
        self.log_queue = queue.Queue()
        self.tray_icon = None
        self.port_list = []  # Danh sách các port entries
        self.ping_timeout_count = 0  # Đếm số lần ping 8.8.8.8 timeout trong session
        self.vmix_api_port_var = tk.StringVar(value="8088")  # vMix HTTP API port

        # ── Tối ưu tốc độ ──
        import requests as _req
        self.http_session = _req.Session()   # Tái dùng TCP connection
        self._ping_ms   = None               # Giá trị ping mới nhất (background thread)
        self._ping_lock = threading.Lock()
        # Prime CPU counter – lần đầu trả 0.0, không block
        try:
            import psutil as _ps
            _ps.cpu_percent(interval=None)
        except Exception:
            pass
        # Bắt đầu background ping thread (ping mỗi 3 giây, non-blocking trong monitor loop)
        threading.Thread(target=self._ping_bg_loop, daemon=True).start()

        # Cache cho file-based vMix resolution/SRT (Python-only, không dùng API)
        self._vmix_file_cache: tuple = ('—', {})
        self._vmix_file_ts: float    = 0.0

        self.setup_ui()
        self.setup_tray()
        self.check_log_queue()
        
        # Load dữ liệu từ database theo IP máy hiện tại
        self.load_data_from_database()
        
        # Override close button để hỏi user
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # Cố định kích thước cửa sổ
        win_w, win_h = 1400, 750
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.resizable(True, False)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (win_w // 2)
        y = (self.root.winfo_screenheight() // 2) - (win_h // 2)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # Main container
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=BOTH, expand=YES)

        # === HEADER SECTION ===
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 15))
        
        # Title
        title_label = ttk.Label(
            header_frame, 
            text="🎥 vMix Monitor Pro", 
            font=('Segoe UI', 18, 'bold'),
            bootstyle="primary"
        )
        title_label.pack(side=LEFT)
        
        # IP Display (right side)
        ip_frame = ttk.Frame(header_frame)
        ip_frame.pack(side=RIGHT)
        
        ttk.Label(
            ip_frame, 
            text="IP Local:", 
            font=('Segoe UI', 10, 'bold'),
            bootstyle="secondary"
        ).pack(side=LEFT, padx=(0, 5))
        
        self.ip_entry = ttk.Entry(
            ip_frame, 
            textvariable=self.ip_var, 
            width=18,
            state='readonly',
            font=('Segoe UI', 10),
            bootstyle="info"
        )
        self.ip_entry.pack(side=LEFT, padx=(0, 5))
        
        # === ADD PORT SECTION ===
        add_frame = ttk.Labelframe(
            main_frame, 
            text="➕ Thêm Port Mới",
            padding=15,
            bootstyle="primary"
        )
        add_frame.pack(fill=X, pady=(0, 15))
        
        # Input grid
        input_grid = ttk.Frame(add_frame)
        input_grid.pack(fill=X)
        
        # Tên máy
        ttk.Label(
            input_grid, 
            text="Tên máy:", 
            font=('Segoe UI', 10),
            width=12
        ).grid(row=0, column=0, padx=5, pady=5, sticky=E)
        
        self.name_entry = ttk.Entry(
            input_grid, 
            textvariable=self.name_var, 
            width=30,
            font=('Segoe UI', 10)
        )
        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=EW)
        
        # Port
        ttk.Label(
            input_grid, 
            text="Port:", 
            font=('Segoe UI', 10),
            width=12
        ).grid(row=0, column=2, padx=5, pady=5, sticky=E)
        
        self.port_entry = ttk.Entry(
            input_grid, 
            textvariable=self.port_var, 
            width=15,
            font=('Segoe UI', 10)
        )
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Add button
        self.add_btn = ttk.Button(
            input_grid, 
            text="➕ Thêm", 
            command=self.add_port_entry,
            bootstyle="success",
            width=12
        )
        self.add_btn.grid(row=0, column=4, padx=10, pady=5)
        
        input_grid.columnconfigure(1, weight=1)
        
        # === TABLE SECTION ===
        table_frame = ttk.Labelframe(
            main_frame, 
            text="📋 Danh Sách Port",
            padding=10,
            bootstyle="info"
        )
        table_frame.pack(fill=BOTH, expand=YES, pady=(0, 15))
        
        # Table container với scrollbar
        table_container = ttk.Frame(table_frame)
        table_container.pack(fill=BOTH, expand=YES)
        
        # Smaller font for table
        style = ttk.Style()
        style.configure('Treeview', font=('Segoe UI', 8), rowheight=22)
        style.configure('Treeview.Heading', font=('Segoe UI', 8, 'bold'))

        # Create Treeview
        columns = ("name", "ip", "ipwan", "port", "ping", "timeout", "cpu", "memory",
                   "rec", "live", "ext", "resolution", "srt")
        self.tree = ttk.Treeview(
            table_container, 
            columns=columns, 
            show='headings',
            height=8,
            bootstyle="info"
        )
        
        # Headings with icons
        self.tree.heading("name",       text="📌 Tên máy",    anchor=CENTER)
        self.tree.heading("ip",         text="🖥️ IP Local",   anchor=CENTER)
        self.tree.heading("ipwan",      text="🌐 IP WAN",      anchor=CENTER)
        self.tree.heading("port",       text="🔌 Port",        anchor=CENTER)
        self.tree.heading("ping",       text="📡 Ping",        anchor=CENTER)
        self.tree.heading("timeout",    text="❌ Timeout",     anchor=CENTER)
        self.tree.heading("cpu",        text="⚡ CPU%",        anchor=CENTER)
        self.tree.heading("memory",     text="💾 RAM%",        anchor=CENTER)
        self.tree.heading("rec",        text="🔴 REC",        anchor=CENTER)
        self.tree.heading("live",       text="📡 LIVE",       anchor=CENTER)
        self.tree.heading("ext",        text="📤 EXT",        anchor=CENTER)
        self.tree.heading("resolution", text="📺 Res",        anchor=CENTER)
        self.tree.heading("srt",        text="📶 SRT Quality", anchor=CENTER)
        
        # Column widths
        self.tree.column("name",       width=150, anchor=CENTER)
        self.tree.column("ip",         width=110, anchor=CENTER)
        self.tree.column("ipwan",      width=110, anchor=CENTER)
        self.tree.column("port",       width=55,  anchor=CENTER)
        self.tree.column("ping",       width=60,  anchor=CENTER)
        self.tree.column("timeout",    width=65,  anchor=CENTER)
        self.tree.column("cpu",        width=55,  anchor=CENTER)
        self.tree.column("memory",     width=55,  anchor=CENTER)
        self.tree.column("rec",        width=45,  anchor=CENTER)
        self.tree.column("live",       width=45,  anchor=CENTER)
        self.tree.column("ext",        width=45,  anchor=CENTER)
        self.tree.column("resolution", width=80,  anchor=CENTER)
        self.tree.column("srt",        width=180, anchor=CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(
            table_container, 
            orient=VERTICAL, 
            command=self.tree.yview,
            bootstyle="info-round"
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)
        
        # Delete button
        btn_frame = ttk.Frame(table_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        
        self.delete_btn = ttk.Button(
            btn_frame, 
            text="🗑️ Xóa mục đã chọn", 
            command=self.delete_selected,
            bootstyle="danger",
            width=20
        )
        self.delete_btn.pack()

        # === VMIX API PORT CONFIG ===
        vmix_cfg_frame = ttk.Frame(main_frame)
        vmix_cfg_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(
            vmix_cfg_frame,
            text="vMix HTTP Port:",
            font=('Segoe UI', 9),
            bootstyle="secondary"
        ).pack(side=LEFT, padx=(0, 4))
        ttk.Entry(
            vmix_cfg_frame,
            textvariable=self.vmix_api_port_var,
            width=7,
            font=('Segoe UI', 9)
        ).pack(side=LEFT)
        ttk.Label(
            vmix_cfg_frame,
            text="(mặc định: 8088)",
            font=('Segoe UI', 8),
            bootstyle="secondary"
        ).pack(side=LEFT, padx=(6, 0))
        ttk.Button(
            vmix_cfg_frame,
            text="🔍 Test API",
            command=self.test_vmix_api,
            bootstyle="warning-outline",
            width=10
        ).pack(side=LEFT, padx=(10, 0))

        # === CONTROL SECTION ===
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=X, pady=(0, 15))
        
        # Button container
        btn_container = ttk.Frame(control_frame)
        btn_container.pack()
        
        self.start_btn = ttk.Button(
            btn_container, 
            text="▶️ START MONITORING", 
            command=self.toggle_monitoring,
            bootstyle="success",
            width=30
        )
        self.start_btn.pack(side=LEFT, padx=5)
        
        # Check server button
        check_btn = ttk.Button(
            btn_container, 
            text="🔍 Kiểm tra Server", 
            command=self.check_server_status,
            bootstyle="info",
            width=20
        )
        check_btn.pack(side=LEFT, padx=5)
        
        # Status indicator
        self.status_label = ttk.Label(
            control_frame,
            text="● Stopped",
            font=('Segoe UI', 10, 'bold'),
            bootstyle="secondary"
        )
        self.status_label.pack(pady=(5, 0))

        # === LOG SECTION ===
        log_frame = ttk.Labelframe(
            main_frame, 
            text="📝 Activity Logs",
            padding=10,
            bootstyle="dark"
        )
        log_frame.pack(fill=BOTH, expand=YES)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=6,
            bg='#1e1e1e', 
            fg='#00ff88',
            font=('Consolas', 9),
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=BOTH, expand=YES)
    
    def create_tray_image(self):
        """Tạo icon cho system tray"""
        # Tạo icon đơn giản (hình vuông màu xanh)
        image = Image.new('RGB', (64, 64), color='green')
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill='white')
        return image
    
    def setup_tray(self):
        """Thiết lập system tray icon"""
        image = self.create_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem("Mở", self.show_window),
            pystray.MenuItem("Thoát", self.quit_app)
        )
        self.tray_icon = pystray.Icon("VmixMonitor", image, "Vmix Monitor", menu)
    
    def hide_to_tray(self):
        """Ẩn cửa sổ xuống system tray"""
        self.root.withdraw()  # Ẩn cửa sổ
        if self.tray_icon and not self.tray_icon.visible:
            # Chạy tray icon trong thread riêng
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def on_closing(self):
        """Xử lý khi user đóng cửa sổ (click nút X)"""
        if self.is_running:
            # Nếu đang chạy, hỏi có muốn thoát không
            result = messagebox.askyesnocancel(
                "Thoát ứng dụng?",
                "Ứng dụng đang chạy.\n\n"
                "Yes: Thoát hoàn toàn (sẽ gửi statusapp=OFF)\n"
                "No: Ẩn xuống taskbar\n"
                "Cancel: Tiếp tục chạy",
                icon='question'
            )
            
            if result is True:  # Yes - Thoát hoàn toàn
                self.quit_app()
            elif result is False:  # No - Ẩn xuống tray
                self.hide_to_tray()
            # else: Cancel - không làm gì
        else:
            # Nếu không chạy, hỏi đơn giản hơn
            result = messagebox.askyesno(
                "Thoát ứng dụng?",
                "Bạn có muốn thoát hoàn toàn không?\n\n"
                "(Chọn No để ẩn xuống taskbar)",
                icon='question'
            )
            
            if result:
                self.quit_app()
            else:
                self.hide_to_tray()
    
    def show_window(self, icon=None, item=None):
        """Hiện lại cửa sổ từ system tray"""
        self.root.deiconify()  # Hiện cửa sổ
        self.root.lift()  # Đưa lên trên cùng
        self.root.focus_force()  # Focus vào cửa sổ
    
    def quit_app(self, icon=None, item=None):
        """Thoát hoàn toàn ứng dụng"""
        # Dừng monitor nếu đang chạy
        if self.is_running:
            self.is_running = False
            # Gửi statusapp = 0 trước khi thoát
            import time
            self.send_app_status(0)
            time.sleep(1)  # Đợi để gửi xong
        
        # Dừng tray icon
        if self.tray_icon:
            self.tray_icon.stop()
        
        # Thoát ứng dụng
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
    
    def show_import_dialog(self):
        """Hiển thị dialog để import data từ IP khác"""
        # Tạo dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("📥 Import từ IP khác")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"400x200+{x}+{y}")
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=BOTH, expand=YES)
        
        ttk.Label(
            frame,
            text="Nhập IP cũ để import data:",
            font=('Segoe UI', 11, 'bold')
        ).pack(pady=(0, 10))
        
        old_ip_var = tk.StringVar()
        ip_entry = ttk.Entry(
            frame,
            textvariable=old_ip_var,
            width=30,
            font=('Segoe UI', 10)
        )
        ip_entry.pack(pady=10)
        ip_entry.focus()
        
        info_label = ttk.Label(
            frame,
            text="Ví dụ: 192.168.1.86",
            font=('Segoe UI', 9),
            bootstyle="secondary"
        )
        info_label.pack(pady=(0, 15))
        
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
            width=15
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Hủy",
            command=dialog.destroy,
            bootstyle="secondary",
            width=15
        ).pack(side=LEFT, padx=5)
        
        # Enter key to import
        ip_entry.bind('<Return>', lambda e: do_import())
    
    def import_from_old_ip(self, old_ip: str):
        """Import và migrate data từ IP cũ sang IP mới"""
        import requests
        
        try:
            current_ip = self.ip_var.get().strip()
            
            if old_ip == current_ip:
                self.log("⚠️ IP cũ và IP mới giống nhau!")
                return
            
            self.log(f"📥 Đang import data từ IP {old_ip}...")
            
            # Lấy data từ IP cũ
            url = f"{SERVER_URL}/get_by_ip?ip={old_ip}"
            response = requests.get(url, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list):
                    imported_count = 0
                    
                    for entry in data:
                        entry_data = entry.get('data', {})
                        name = entry_data.get('name', '')
                        port = entry_data.get('port', 0)
                        ipwan = entry_data.get('ipwan', 'unknown')
                        
                        if name and port:
                            # Check if already exists
                            exists = False
                            for existing in self.port_list:
                                if existing['name'] == name or existing['port'] == port:
                                    exists = True
                                    self.log(f"⚠️ Bỏ qua {name} (đã tồn tại)")
                                    break
                            
                            if not exists:
                                # Add to list
                                self.port_list.append({"name": name, "port": port, "ip": current_ip, "ipwan": ipwan,
                                                       "ping": '—', "timeout": '0', "cpu": '—', "memory": '—',
                                                       "rec": '—', "live": '—', "ext": '—', "resolution": '—', "srt": '—'})
                                # Add to tree
                                self.tree.insert("", tk.END, values=(name, current_ip, ipwan, port, '—', '0', '—', '—', '—', '—', '—', '—', '—'))
                                imported_count += 1
                                
                                # Update database với IP mới
                                threading.Thread(
                                    target=lambda n=name, p=port: self.update_single_ip_in_database(old_ip, current_ip, n, p),
                                    daemon=True
                                ).start()
                    
                    if imported_count > 0:
                        self.log(f"✅ Đã import {imported_count} port từ IP {old_ip}")
                    else:
                        self.log(f"ℹ️ Không có port mới để import từ IP {old_ip}")
                else:
                    self.log(f"ℹ️ Không có dữ liệu cho IP {old_ip}")
            else:
                self.log(f"❌ Lỗi lấy data từ IP {old_ip}: HTTP {response.status_code}")
        except Exception as e:
            self.log(f"❌ Lỗi import: {str(e)}")
    
    def update_single_ip_in_database(self, old_ip: str, new_ip: str, name: str, port: int):
        """Cập nhật IP cho một entry cụ thể"""
        import requests
        try:
            data = {
                "old_ip": old_ip,
                "new_ip": new_ip,
                "port": port,
                "name": name
            }
            url = f"{SERVER_URL}/update_ip"
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.log(f"✅ Đã migrate {name} từ {old_ip} → {new_ip}")
            else:
                self.log(f"⚠️ Lỗi migrate {name}: {response.status_code}")
        except Exception as e:
            self.log(f"❌ ERROR migrate {name}: {str(e)}")
    
    def refresh_ip(self):
        """Refresh IP và cập nhật database"""
        old_ip = self.ip_var.get().strip()
        new_ip = self.get_local_ip()
        
        if old_ip == new_ip:
            self.log(f"ℹ️ IP không đổi: {new_ip}")
            return
        
        self.log(f"🔄 IP thay đổi: {old_ip} → {new_ip}")
        self.ip_var.set(new_ip)
        
        # Update IP trong port_list
        for entry in self.port_list:
            entry['ip'] = new_ip
        
        # Update IP trong table display
        for item in self.tree.get_children():
            values = list(self.tree.item(item, 'values'))
            values[1] = new_ip  # IP column
            self.tree.item(item, values=values)
        
        # Update database
        if self.port_list:
            threading.Thread(target=lambda: self.update_ip_in_database(old_ip, new_ip), daemon=True).start()
    
    def update_ip_in_database(self, old_ip: str, new_ip: str):
        """Cập nhật IP trong database cho tất cả ports của máy này"""
        import requests
        
        try:
            # Cập nhật từng port
            for entry in self.port_list:
                data = {
                    "old_ip": old_ip,
                    "new_ip": new_ip,
                    "port": entry['port'],
                    "name": entry['name']
                }
                url = f"{SERVER_URL}/update_ip"
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json=data, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    self.log(f"✅ Đã cập nhật IP trên DB: {entry['name']}")
                else:
                    self.log(f"⚠️ Lỗi cập nhật IP ({entry['name']}): {response.status_code}")
        except Exception as e:
            self.log(f"❌ ERROR cập nhật IP: {str(e)}")
    
    def check_server_status(self):
        """Kiểm tra trạng thái server"""
        import requests
        threading.Thread(target=self._check_server_thread, daemon=True).start()
    
    def _check_server_thread(self):
        """Thread để kiểm tra server"""
        import requests
        import time
        
        self.log("🔍 Đang kiểm tra server...")
        start_time = time.time()
        
        try:
            url = f"{SERVER_URL}/logs"
            response = requests.get(url, timeout=30)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                self.log(f"✅ Server hoạt động tốt! (Phản hồi trong {elapsed:.1f}s)")
            elif response.status_code == 500:
                self.log(f"⚠️ Server đang có vấn đề (500). Có thể đang khởi động lại...")
            else:
                self.log(f"❓ Server phản hồi: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            self.log("⏱️ Server timeout (>30s) - có thể đang cold start, hãy thử lại sau 1 phút")
        except requests.exceptions.ConnectionError:
            self.log("❌ Không kết nối được server - kiểm tra internet hoặc server đang down")
        except Exception as e:
            self.log(f"❌ Lỗi kiểm tra server: {str(e)}")
    
    def load_data_from_database(self):
        """Load dữ liệu từ database theo IP máy hiện tại"""
        import requests
        try:
            ip = self.ip_var.get().strip()
            url = f"{SERVER_URL}/get_by_ip?ip={ip}"
            self.log(f"⏳ Đang tải dữ liệu từ server...")
            response = requests.get(url, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list):
                    # Clear existing data
                    self.port_list.clear()
                    for item in self.tree.get_children():
                        self.tree.delete(item)
                    
                    # Load data from database
                    loaded_count = 0
                    for entry in data:
                        entry_data = entry.get('data', {})
                        name    = entry_data.get('name', '')
                        port    = entry_data.get('port', 0)
                        entry_ip = entry_data.get('ip', ip)
                        ipwan   = entry_data.get('ipwan', 'unknown')
                        ping    = entry_data.get('ping', None)
                        temperature = entry_data.get('temperature', None)
                        memory  = entry_data.get('memory', None)
                        
                        if name and port:
                            # Add to list
                            cpu = entry_data.get('temperature', None)  # server lưu cpu% vào field temperature
                            self.port_list.append({
                                "name": name, "port": port, "ip": entry_ip, "ipwan": ipwan,
                                "ping":   f"{ping:.0f}"  if ping   is not None else '—',
                                "cpu":    f"{cpu:.1f}"   if cpu    is not None else '—',
                                "memory": f"{memory:.1f}" if memory is not None else '—',
                                "rec": '—', "live": '—', "ext": '—', "resolution": '—', "srt": '—',
                            })
                            # Add to tree
                            ping_str = f"{ping:.0f}"  if ping   is not None else '—'
                            cpu_str  = f"{cpu:.1f}"   if cpu    is not None else '—'
                            mem_str  = f"{memory:.1f}" if memory is not None else '—'
                            self.tree.insert("", tk.END, values=(name, entry_ip, ipwan, port, ping_str, '0', cpu_str, mem_str, '—', '—', '—', '—', '—'))
                            loaded_count += 1
                    
                    if loaded_count > 0:
                        self.log(f"✅ Đã tải {loaded_count} port từ database (IP: {ip})")
                    else:
                        self.log(f"ℹ️ Không có dữ liệu cho IP {ip} trong database")
                        # Check if there's data with other IPs
                        self.check_for_old_ip_data()
                else:
                    self.log(f"ℹ️ Không có dữ liệu cho IP {ip} trong database")
                    # Check if there's data with other IPs
                    self.check_for_old_ip_data()
            elif response.status_code == 500:
                self.log(f"⚠️ Server đang có vấn đề (500) - có thể đang cold start, hãy thử lại sau 30s")
            else:
                self.log(f"❌ Không thể tải dữ liệu: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            self.log(f"⏱️ Timeout khi tải dữ liệu - server có thể đang ngủ, hãy đợi 30-60s")
        except Exception as e:
            self.log(f"❌ Lỗi khi load dữ liệu: {str(e)}")
    
    def check_for_old_ip_data(self):
        """Kiểm tra xem có data với IP cũ không và hỏi user có muốn import không"""
        import requests
        try:
            # Get all data from database
            url = f"{SERVER_URL}/logs"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                all_data = response.json()
                if all_data and isinstance(all_data, list):
                    current_ip = self.ip_var.get().strip()
                    found_ips = set()
                    
                    # Find unique IPs in database (exclude current IP)
                    for entry in all_data:
                        entry_data = entry.get('data', {})
                        entry_ip = entry_data.get('ip', '')
                        if entry_ip and entry_ip != current_ip:
                            found_ips.add(entry_ip)
                    
                    if found_ips:
                        # Show notification với dialog
                        self.root.after(1000, lambda: self.show_old_ip_notification(list(found_ips)))
        except Exception as e:
            pass  # Ignore errors in background check
    
    def show_old_ip_notification(self, old_ips: list):
        """Hiển thị thông báo có data với IP cũ"""
        if not old_ips:
            return
        
        ip_list = "\\n".join(f"  • {ip}" for ip in old_ips[:5])  # Show max 5 IPs
        
        result = messagebox.askyesno(
            "📥 Phát hiện dữ liệu IP cũ",
            f"Tìm thấy dữ liệu trong database với IP khác:\\n\\n{ip_list}\\n\\n"
            f"Bạn có muốn import dữ liệu từ IP cũ không?",
            icon='question'
        )
        
        if result:
            self.show_import_dialog()
    
    def log(self, message):
        timestamp = datetime.now(VIETNAM_TZ).strftime("[%H:%M:%S]")
        self.log_queue.put(f"{timestamp} {message}")

    def check_log_queue(self):
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

    def add_port_entry(self):
        """Thêm một port entry vào danh sách"""
        name = self.name_var.get().strip()
        port_str = self.port_var.get().strip()
        
        if not name:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên máy!")
            return
        
        if not port_str:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập port!")
            return
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError()
        except:
            messagebox.showerror("Lỗi", "Port phải là số từ 1-65535!")
            return
        
        ip = self.ip_var.get().strip()
        
        # Check duplicate - Kiểm tra trùng TÊN MÁY hoặc trùng PORT
        for entry in self.port_list:
            if entry['name'] == name:
                messagebox.showwarning("Cảnh báo", f"Tên máy '{name}' đã tồn tại!")
                return
            if entry['port'] == port:
                messagebox.showwarning("Cảnh báo", f"Port {port} đã được sử dụng!")
                return
        
        # Add to list NGAY (với wan_ip tạm thời là "loading...")
        self.port_list.append({"name": name, "port": port, "ip": ip, "ipwan": "loading...",
                               "ping": '—', "timeout": '0', "cpu": '—', "memory": '—',
                               "rec": '—', "live": '—', "ext": '—', "resolution": '—', "srt": '—'})
        
        # Add to tree NGAY
        self.tree.insert("", tk.END, values=(name, ip, "loading...", port, '—', '0', '—', '—', '—', '—', '—', '—', '—'))
        
        # Clear input fields
        self.name_var.set("")
        self.port_var.set("")
        
        self.log(f"Đã thêm: {name} - {ip} - Port {port}")
        
        # Lấy WAN IP bất đồng bộ (async) để KHÔNG block UI
        def fetch_wan_async():
            wan_ip = self.get_wan_ip()
            # Update lại ipwan trong port_list
            for entry in self.port_list:
                if entry['name'] == name and entry['port'] == port:
                    entry['ipwan'] = wan_ip
                    break
            # Update lại tree display
            self.root.after(0, self.update_table_display)
            self.log(f"✅ Đã cập nhật IPWAN cho {name}: {wan_ip}")
        
        threading.Thread(target=fetch_wan_async, daemon=True).start()
    
    def delete_selected(self):
        """Xóa mục đã chọn trong table và xóa trên database"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một mục để xóa!")
            return
        
        for item in selected:
            values = self.tree.item(item, 'values')
            if values:
                name = values[0]
                ip = values[1]
                port = int(values[3]) if values[3] else 0
                
                # Remove from list
                self.port_list = [e for e in self.port_list if not (e['name'] == name and e['port'] == port)]
                
                # Remove from tree
                self.tree.delete(item)
                
                # Xóa trên database ngay lập tức
                threading.Thread(target=lambda n=name, i=ip, p=port: self.delete_single_from_database(n, i, p), daemon=True).start()
                
                self.log(f"Đã xóa: {name} - {ip} - Port {port}")

    def delete_single_from_database(self, name, ip, port):
        """Xóa một entry cụ thể khỏi database"""
        import requests
        try:
            data = {
                "name": name,
                "ip": ip,
                "port": port
            }
            url = f"{SERVER_URL}/delete"
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=15)
            if response.status_code == 200:
                self.log(f"🗑️ Đã xóa trên DB: {name} - Port {port}")
            elif response.status_code == 500:
                self.log(f"⚠️ Server error 500 khi xóa {name} (có thể server đang cold start)")
            else:
                self.log(f"❌ Lỗi xóa DB ({name}): HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            self.log(f"⏱️ Timeout xóa DB: {name}")
        except Exception as e:
            self.log(f"❌ ERROR xóa DB: {str(e)}")

    def delete_all_from_database(self):
        """Xóa dữ liệu của tất cả các port entries khỏi database (khi STOP) - CHỈ XÓA CỦA MÁY NÀY"""
        import requests
        
        if not self.port_list:
            return
        
        # Lấy IP hiện tại của máy này để đảm bảo chỉ xóa dữ liệu của máy này
        current_ip = self.ip_var.get().strip()
        
        try:
            for entry in self.port_list:
                data = {
                    "name": entry['name'],
                    "ip": current_ip,  # Dùng IP hiện tại của máy này
                    "port": entry['port']
                }
                url = f"{SERVER_URL}/delete"
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json=data, headers=headers, timeout=10)
                if response.status_code == 200:
                    self.log(f"Đã xóa DB: {entry['name']} ({current_ip}:{entry['port']})")
                else:
                    self.log(f"Lỗi xóa DB: {entry['name']} - {response.status_code}")
        except Exception as e:
            self.log(f"ERROR xóa DB: {str(e)}")

    def send_app_status(self, status_value):
        """Gửi trạng thái app (1=ON, 0=OFF) cho tất cả các port entries"""
        import requests
        import time
        
        if not self.port_list:
            self.log("⚠️ Không có port nào trong danh sách!")
            return
        
        ip = self.ip_var.get().strip()
        if not ip:
            return
        
        try:
            wan_ip = self.get_wan_ip()
            
            # Gửi từng port entry lên server
            for entry in self.port_list:
                data = {
                    "name": entry['name'],
                    "ip": ip,
                    "ipwan": wan_ip,
                    "status": "OFF",  # vMix status (will be updated in monitor_loop)
                    "port": entry['port'],
                    "statusapp": status_value  # App status: 1=ON, 0=OFF
                }
                url = SERVER_URL
                headers = {"Content-Type": "application/json"}
                
                # Retry logic (3 attempts)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post(url, json=data, headers=headers, timeout=15)
                        if response.status_code == 200:
                            status_text = "ON" if status_value == 1 else "OFF"
                            self.log(f"✅ App status {status_text}: {entry['name']} - Port {entry['port']}")
                            break
                        elif response.status_code == 500:
                            error_detail = ""
                            try:
                                error_detail = response.json().get('detail', '')
                            except:
                                error_detail = response.text[:100]
                            
                            if attempt < max_retries - 1:
                                wait_time = (attempt + 1) * 2
                                self.log(f"⚠️ Server error 500 ({entry['name']}), retry sau {wait_time}s... (lần {attempt + 1}/{max_retries})")
                                time.sleep(wait_time)
                            else:
                                self.log(f"❌ Lỗi 500 {entry['name']}: {error_detail}")
                        else:
                            self.log(f"❌ Lỗi gửi {entry['name']}: HTTP {response.status_code}")
                            break
                    except requests.exceptions.Timeout:
                        if attempt < max_retries - 1:
                            self.log(f"⏱️ Timeout ({entry['name']}), retry...")
                            time.sleep(2)
                        else:
                            self.log(f"❌ Timeout sau {max_retries} lần thử: {entry['name']}")
                    except requests.exceptions.ConnectionError:
                        self.log(f"❌ Không kết nối được server: {entry['name']}")
                        break
        except Exception as e:
            self.log(f"❌ ERROR gửi app status: {str(e)}")

    def toggle_monitoring(self):
        if not self.is_running:
            if not self.port_list:
                messagebox.showwarning("Cảnh báo", "Vui lòng thêm ít nhất một port!")
                return
            
            self.is_running = True
            self.ping_timeout_count = 0  # Reset bộ đếm timeout khi START mới
            self.start_btn.config(text="⏹️ STOP MONITORING", bootstyle="danger")
            self.status_label.config(text="● Running", bootstyle="success")
            self.delete_btn.config(state=tk.DISABLED)  # Disable nút xóa khi START
            # Disable input và nút thêm
            self.name_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.add_btn.config(state=tk.DISABLED)
            self.log("✅ Bắt đầu gửi dữ liệu...")
            # Gửi statusapp = 1 (ON)
            threading.Thread(target=lambda: self.send_app_status(1), daemon=True).start()
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_running = False
            self.log("⏹️ Đang dừng và cập nhật trạng thái...")
            # Bước 1: Gửi statusapp = 0 (OFF) để frontend fetch trước
            threading.Thread(target=self.stop_and_cleanup, daemon=True).start()
            self.start_btn.config(text="▶️ START MONITORING", bootstyle="success")
            self.status_label.config(text="● Stopped", bootstyle="secondary")
            self.delete_btn.config(state=tk.NORMAL)  # Enable lại nút xóa khi STOP
            # Enable lại input và nút thêm
            self.name_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            self.add_btn.config(state=tk.NORMAL)
    
    def stop_and_cleanup(self):
        """Dừng và cập nhật trạng thái: chỉ gửi statusapp=0"""
        # Gửi statusapp = 0 (OFF)
        self.send_app_status(0)
        self.log("Đã dừng và cập nhật trạng thái OFF.")

    def update_table_display(self):
        """Cập nhật lại table hiển thị với dữ liệu mới từ port_list"""
        # Clear table
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Reload từ port_list
        for entry in self.port_list:
            name    = entry['name']
            ip      = entry['ip']
            ipwan   = entry['ipwan']
            port    = entry['port']
            ping    = entry.get('ping', '—')
            timeout = entry.get('timeout', '0')
            cpu     = entry.get('cpu', '—')
            memory  = entry.get('memory', '—')
            rec     = entry.get('rec', '—')
            live    = entry.get('live', '—')
            ext     = entry.get('ext', '—')
            resolution = entry.get('resolution', '—')
            srt     = entry.get('srt', '—')
            self.tree.insert("", tk.END, values=(name, ip, ipwan, port, ping, timeout, cpu, memory, rec, live, ext, resolution, srt))

    # ── Background ping thread ──────────────────────────────────────────────
    def _ping_bg_loop(self):
        """Chạy liên tục trong background thread – cập nhật _ping_ms mỗi 3 giây"""
        import time
        while True:
            val = self.measure_ping()
            with self._ping_lock:
                self._ping_ms = val
                if val is None:
                    self.ping_timeout_count += 1
            time.sleep(3)

    # ── Đo thông số hệ thống ──────────────────────────────────────────────
    def measure_ping(self, host="8.8.8.8") -> float | None:
        """Ping tới host, trả về latency (ms) hoặc None nếu lỗi"""
        import subprocess, re
        try:
            result = subprocess.run(
                ["ping", "-n", "1", "-w", "1000", host],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=3
            )
            match = re.search(r'Average\s*=\s*(\d+)ms', result.stdout)
            if not match:
                match = re.search(r'Minimum\s*=\s*(\d+)ms', result.stdout)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None

    def measure_cpu(self) -> float | None:
        """Trả về % CPU – non-blocking (dùng giá trị tích lũy từ lần gọi trước)"""
        try:
            import psutil
            return round(psutil.cpu_percent(interval=None), 1)
        except Exception:
            pass
        return None

    def measure_memory(self) -> float | None:
        """Trả về % RAM đang dùng"""
        try:
            import psutil
            return round(psutil.virtual_memory().percent, 1)
        except Exception:
            pass
        return None

    # ── vMix HTTP API ─────────────────────────────────────────────────────────
    def get_vmix_resolution_from_file(self, preset_path: str = '') -> str:
        """Đọc output resolution từ file project .vmix trên ổ đĩa (không cần HTTP API)"""
        import os, glob
        import xml.etree.ElementTree as ET

        # Ưu tiên dùng preset path lấy từ API response (chính xác nhất)
        project_file = preset_path if preset_path and os.path.isfile(preset_path) else None

        # Bước 1: Lấy đường dẫn file project từ command line của tiến trình vMix
        if not project_file:
            try:
                import psutil
                for proc in psutil.process_iter(['name', 'cmdline']):
                    try:
                        if 'vmix' in (proc.info['name'] or '').lower():
                            for arg in (proc.info.get('cmdline') or []):
                                if arg.lower().endswith('.vmix') and os.path.isfile(arg):
                                    project_file = arg
                                    break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    if project_file:
                        break
            except Exception:
                pass

        # Bước 2: Tìm file .vmix mới nhất trong các thư mục phổ biến
        if not project_file:
            try:
                search_dirs = []
                appdata = os.environ.get('APPDATA', '')
                if appdata:
                    search_dirs.append(os.path.join(appdata, 'vMix'))
                home = os.path.expanduser('~')
                search_dirs += [
                    os.path.join(home, 'Documents', 'vMix'),
                    os.path.join(home, 'Desktop'),
                    os.path.join(home, 'Documents'),
                ]
                candidates = []
                for d in search_dirs:
                    candidates.extend(glob.glob(os.path.join(d, '*.vmix')))
                if candidates:
                    project_file = max(candidates, key=os.path.getmtime)
            except Exception:
                pass

        if not project_file:
            return '—'

        try:
            xml_text = self._read_file_shared(project_file)
            root = ET.fromstring(xml_text)

            # vMix 26: resolution trong <OutputFormat OutputSize="1920x1080" OutputFrameRate="333667">
            out_fmt = root.find('.//OutputFormat')
            if out_fmt is not None:
                size = out_fmt.get('OutputSize', '')   # e.g. "1920x1080"
                fr_ticks = out_fmt.get('OutputFrameRate', '')  # e.g. "333667" (100ns ticks/frame)
                h = size.split('x')[1] if 'x' in size else ''
                fps_str = ''
                if fr_ticks:
                    try:
                        ticks = int(fr_ticks)
                        fps_val = 10_000_000 / ticks if ticks else 0
                        fps_str = f"{fps_val:.4g}"
                    except Exception:
                        pass
                if h:
                    return f"{h}p{fps_str}" if fps_str else f"{h}p"

            # Fallback cũ cho các phiên bản khác
            w, h, fr = None, None, None
            for path in ['.//output', './/Output', './/settings/output', './/Settings/Output']:
                out_e = root.find(path)
                if out_e is not None:
                    w  = out_e.get('width')  or out_e.findtext('width')
                    h  = out_e.get('height') or out_e.findtext('height')
                    fr = (out_e.get('framerate') or out_e.get('frameRate')
                          or out_e.findtext('framerate') or out_e.findtext('frameRate'))
                    if h:
                        break

            if h:
                if fr:
                    try:
                        fps_val = float(str(fr).replace(',', '.'))
                        fps_str = f"{fps_val:.4g}"
                    except ValueError:
                        fps_str = str(fr)
                    return f"{h}p{fps_str}"
                return f"{h}p"
        except Exception:
            pass

        return '—'

    # ── Python-only: tìm file preset + đọc Resolution/SRT ──────────────────

    @staticmethod
    def _vmix_data_dir() -> str:
        import os
        base = (os.environ.get('PROGRAMDATA')
                or os.environ.get('ALLUSERSPROFILE')
                or r'C:\ProgramData')
        return os.path.join(base, 'vMix')

    @staticmethod
    def _read_file_shared(filepath: str) -> str:
        """Đọc file ngay cả khi bị vMix lock (Windows API)."""
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        GENERIC_READ        = 0x80000000
        FILE_SHARE_ALL      = 0x07
        OPEN_EXISTING       = 3
        FILE_ATTRIBUTE_NORMAL = 0x80
        INVALID_HANDLE      = ctypes.c_void_p(-1).value
        handle = kernel32.CreateFileW(
            filepath, GENERIC_READ, FILE_SHARE_ALL,
            None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None,
        )
        if handle == INVALID_HANDLE:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            size = kernel32.GetFileSize(handle, None)
            if size == 0xFFFFFFFF:
                raise ctypes.WinError(ctypes.get_last_error())
            buf = ctypes.create_string_buffer(size)
            read = wintypes.DWORD(0)
            if not kernel32.ReadFile(handle, buf, size, ctypes.byref(read), None):
                raise ctypes.WinError(ctypes.get_last_error())
            return buf.raw[:read.value].decode('utf-8', errors='replace')
        finally:
            kernel32.CloseHandle(handle)

    def get_res_and_srt_from_file(self) -> tuple:
        """
        Lấy Resolution và SRT Quality từ C:\\ProgramData\\vMix\\ (Python thuần, không API).
        - Resolution : video.txt  →  dòng 1=height, dòng 2=ticks(100ns/frame)
        - SRT Quality: current.config → OutputsExternal* → các field SRTPort/SRTVideo*/SRTAudio*
        Cache 5 giây. Trả về: (resolution_str, {port: quality_str, ...})
        """
        import time, os, re, html
        import xml.etree.ElementTree as ET

        if time.time() - self._vmix_file_ts < 5:
            return self._vmix_file_cache

        vmix_dir    = self._vmix_data_dir()
        video_txt   = os.path.join(vmix_dir, 'video.txt')
        config_file = os.path.join(vmix_dir, 'settingbackups', 'current.config')

        # ── Resolution từ video.txt ──────────────────────────────────────────
        # Định dạng: line0=width  line1=height  line2=frame_rate_ticks(100ns/frame)
        resolution = '—'
        try:
            raw_text = self._read_file_shared(video_txt)
            v = [l.strip() for l in raw_text.splitlines()]
            h = v[1] if len(v) > 1 else ''
            fps_str = ''
            if len(v) > 2:
                ticks = int(v[2])
                fps_val = 10_000_000 / ticks if ticks > 0 else 0
                for std, lbl in [(23.976,'23.976'),(24,'24'),(25,'25'),
                                  (29.97,'29.97'),(30,'30'),(50,'50'),
                                  (59.94,'59.94'),(60,'60')]:
                    if abs(fps_val - std) < 0.1:
                        fps_str = lbl; break
                else:
                    fps_str = f'{fps_val:.4g}'
            if h:
                resolution = f'{h}p{fps_str}' if fps_str else f'{h}p'
        except Exception:
            pass

        # ── SRT Quality từ current.config ────────────────────────────────────
        # current.config là .NET Application Settings XML.
        # Mỗi OutputsExternal* lưu một đoạn XML bị HTML-encode trong thẻ <value>…</value>.
        # Dùng regex để bắt đúng khối, rồi parse XML con để lấy SRT fields.
        srt_by_port: dict = {}
        try:
            content = self._read_file_shared(config_file)

            for ext_name in ('OutputsExternal', 'OutputsExternal2',
                             'OutputsExternal3', 'OutputsExternal4'):
                # Tìm đoạn: name="OutputsExternal*"  …  <value>…</value>
                m = re.search(
                    rf'name="{re.escape(ext_name)}"[^>]*>\s*<value>(.*?)</value>',
                    content, re.DOTALL
                )
                if not m:
                    continue
                decoded = html.unescape(m.group(1).strip())
                try:
                    sub = ET.fromstring(f'<root>{decoded}</root>')
                except Exception:
                    continue

                # Lấy SRTPort — bỏ qua nếu port = 0
                try:
                    port = int((sub.findtext('SRTPort') or '0').strip())
                except ValueError:
                    port = 0
                if not port:
                    continue

                # Codec: SRTVideoCodec  0=H264  1=HEVC
                codec = 'HEVC' if (sub.findtext('SRTVideoCodec') or '0').strip() == '1' else 'H264'

                # Video bandwidth (bps)
                try:
                    vbw = int(sub.findtext('SRTVideoBandwidth') or '0')
                    vbw_s = (f'{vbw // 1_000_000}Mbps' if vbw >= 1_000_000
                             else f'{vbw // 1000}kbps')
                except Exception:
                    vbw_s = '?'

                # Audio bandwidth (bps)
                try:
                    abw = int(sub.findtext('SRTAudioBandwidth') or '0')
                    abw_s = f'{abw // 1000}kbps'
                except Exception:
                    abw_s = '?'

                hw = ' HW' if (sub.findtext('SRTHardwareEncoder') or '0').strip() == '1' else ''
                srt_by_port[port] = f'{codec} {vbw_s} AAC {abw_s}{hw}'

        except Exception:
            pass

        result = (resolution, srt_by_port)
        self._vmix_file_cache = result
        self._vmix_file_ts    = time.time()
        return result

    def test_vmix_api(self):
        """Dump raw vMix XML vào log để debug"""
        import requests
        def _run():
            try:
                port = self.vmix_api_port_var.get().strip() or "8088"
                url = f"http://127.0.0.1:{port}/api"
                self.log(f"[vMix Test] GET {url}")
                resp = requests.get(url, timeout=3)
                self.log(f"[vMix Test] Status: {resp.status_code}")
                if resp.status_code == 200:
                    text = resp.text
                    # Log từng 300 ký tự
                    for i in range(0, min(len(text), 900), 300):
                        self.log(f"[vMix XML] {text[i:i+300]}")
                else:
                    self.log(f"[vMix Test] Body: {resp.text[:200]}")
            except Exception as e:
                self.log(f"[vMix Test] Error: {e}")
        import threading
        threading.Thread(target=_run, daemon=True).start()

    def get_vmix_stats(self) -> dict:
        """Lấy thông số vMix từ HTTP API tại localhost (mặc định port 8088)"""
        import xml.etree.ElementTree as ET
        import requests
        try:
            port = self.vmix_api_port_var.get().strip() or "8088"
            url = f"http://127.0.0.1:{port}/api"
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                inputs_elem = root.find('inputs')
                input_count = len(list(inputs_elem)) if inputs_elem is not None else 0

                # FPS – thử child element trước (vMix mới), rồi fallback attribute của input đầu tiên
                fps_raw = (root.findtext('masterFrameRate', '')
                           or root.findtext('frameRate', '')
                           or root.findtext('outputFrameRate', ''))
                if not fps_raw and inputs_elem is not None:
                    first_inp = inputs_elem.find('input')
                    if first_inp is not None:
                        # vMix lưu fps trong attribute 'framerate' (thường là số nguyên như "25", "30")
                        fps_raw = (first_inp.get('framerate', '')
                                   or first_inp.get('frameRate', '')
                                   or first_inp.get('fps', ''))
                try:
                    fps_val = float(fps_raw.replace(',', '.')) if fps_raw else None
                    fps_str = f"{fps_val:.4g}" if fps_val is not None else '—'
                except (ValueError, AttributeError):
                    fps_str = fps_raw.replace(',', '.') if fps_raw else '—'

                # Height/Width – vMix thường không có ở root, chủ yếu lấy từ input
                h = (root.get('height', '')
                     or root.findtext('height', '')
                     or root.findtext('outputHeight', ''))
                w = (root.get('width', '')
                     or root.findtext('width', '')
                     or root.findtext('outputWidth', ''))
                # Fallback: sub-element <output>
                if not (h and w):
                    out_e = root.find('output')
                    if out_e is not None:
                        h = h or out_e.get('height', '') or out_e.findtext('height', '')
                        w = w or out_e.get('width', '') or out_e.findtext('width', '')
                # Primary fallback: lấy từ input đầu tiên (vMix lưu resolution tại đây)
                if not (h and w) and inputs_elem is not None:
                    first_inp = inputs_elem.find('input')
                    if first_inp is not None:
                        h = h or first_inp.get('height', '')
                        w = w or first_inp.get('width', '')

                if h:
                    resolution = f"{h}p{fps_str}" if fps_str != '—' else f"{h}p"
                elif fps_str != '—':
                    resolution = fps_str
                else:
                    resolution = '—'

                # Lấy preset path từ API response (vMix 26 trả về <preset>)
                preset_path = root.findtext('preset', '') or root.findtext('Preset', '')

                # Đọc resolution + SRT quality từ file preset
                srt_quality = '—'
                srt_by_port = {}  # {port_number: quality_string}
                if preset_path and __import__('os').path.isfile(preset_path):
                    try:
                        _pt = ET.parse(preset_path)
                        _pr = _pt.getroot()

                        # Resolution từ <OutputFormat OutputSize="1920x1080" OutputFrameRate="333667">
                        if resolution == '—':
                            _of = _pr.find('.//OutputFormat')
                            if _of is not None:
                                _size = _of.get('OutputSize', '')
                                _fr_t = _of.get('OutputFrameRate', '')
                                _h = _size.split('x')[1] if 'x' in _size else ''
                                _fps = ''
                                if _fr_t:
                                    try:
                                        _fps = f"{10_000_000 / int(_fr_t):.4g}"
                                    except Exception:
                                        pass
                                if _h:
                                    resolution = f"{_h}p{_fps}" if _fps else f"{_h}p"
                                    # Cập nhật fps_str nếu chưa có
                                    if fps_str == '—' and _fps:
                                        fps_str = _fps

                        # SRT quality từ OutputsExternal*/SRTEnabled=1 — thu thập TẤT CẢ theo port
                        for _ext_tag in ['OutputsExternal', 'OutputsExternal2',
                                         'OutputsExternal3', 'OutputsExternal4']:
                            _ext = _pr.find(f'.//{_ext_tag}')
                            if _ext is None:
                                continue
                            _srt_on = _ext.findtext('SRTEnabled', '0')
                            if _srt_on.strip() != '1':
                                continue
                            # Lấy SRT port
                            _srt_port_str = _ext.findtext('SRTPort', '0').strip()
                            try:
                                _srt_port = int(_srt_port_str)
                            except ValueError:
                                _srt_port = 0
                            # Giải mã codec
                            _codec_id = _ext.findtext('SRTVideoCodec', '0')
                            _codec = 'HEVC' if _codec_id.strip() == '1' else 'H264'
                            # Bandwidth
                            try:
                                _vbw = int(_ext.findtext('SRTVideoBandwidth', '0'))
                                _vbw_s = f"{_vbw // 1_000_000}Mbps" if _vbw >= 1_000_000 else f"{_vbw // 1000}kbps"
                            except Exception:
                                _vbw_s = '?'
                            try:
                                _abw = int(_ext.findtext('SRTAudioBandwidth', '0'))
                                _abw_s = f"{_abw // 1000}kbps"
                            except Exception:
                                _abw_s = '?'
                            _hw = ' HW' if _ext.findtext('SRTHardwareEncoder', '0') == '1' else ''
                            _q = f"{_codec} {_vbw_s} AAC {_abw_s}{_hw}"
                            if _srt_port:
                                srt_by_port[_srt_port] = _q
                            # Giữ lại giá trị chung (fallback)
                            if srt_quality == '—':
                                srt_quality = _q
                    except Exception:
                        pass

                return {
                    'connected':   True,
                    'recording':   root.findtext('recording',  'False').strip() == 'True',
                    'streaming':   root.findtext('streaming',  'False').strip() == 'True',
                    'external':    root.findtext('external',   'False').strip() == 'True',
                    'fullscreen':  root.findtext('fullscreen', 'False').strip() == 'True',
                    'version':     root.findtext('version',    '—'),
                    'edition':     root.findtext('edition',    '—'),
                    'input_count': input_count,
                    'fps':         fps_str,
                    'resolution':  resolution,
                    'srt_quality': srt_quality,
                    'srt_by_port': srt_by_port,
                }
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass  # vMix không chạy hoặc chưa khởi động – bình thường
        except Exception as e:
            self.log(f"[vMix] Error: {e}")
        res_from_file = self.get_vmix_resolution_from_file()
        return {
            'connected': False, 'recording': False, 'streaming': False,
            'external': False,  'fullscreen': False, 'version': '—',
            'edition': '—',     'input_count': 0,   'fps': '—',
            'resolution': res_from_file, 'srt_quality': '—', 'srt_by_port': {},
        }

    def is_vmix_on_port(self, port):
        """Kiểm tra vMix có đang lắng nghe trên port UDP không – dùng psutil (nhanh hơn netstat)"""
        try:
            import psutil
            port_int = int(port)
            for conn in psutil.net_connections(kind='udp'):
                if conn.laddr and conn.laddr.port == port_int and conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        if 'vmix' in proc.name().lower():
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            return False
        except Exception as e:
            self.log(f"ERROR kiểm tra vMix: {str(e)}")
            return False
    
    def get_wan_ip(self):
        # Local mode: always use loopback WAN placeholder to avoid external calls.
        return "127.0.0.1"

    def monitor_loop(self):
        import requests
        import time
        
        ip = self.ip_var.get().strip()
        
        if not ip or not self.port_list:
            self.log("ERROR: IP hoặc danh sách port trống!")
            self.is_running = False
            self.start_btn.config(text="START", bg="#4CAF50")
            return
        
        wan_ip = self.get_wan_ip()
        # Track previous status for each port
        prev_status = {}  # {port: "ON"/"OFF"}
        last_wan_check = datetime.now(VIETNAM_TZ)
        last_ip_check = datetime.now(VIETNAM_TZ)
        wan_refresh_sec = 30  # Refresh WAN IP every 30 seconds
        ip_check_sec = 5  # Check local IP every 5 seconds
        
        self.log(f"Bắt đầu giám sát {len(self.port_list)} port(s)...")
        
        while self.is_running:
            now = datetime.now(VIETNAM_TZ)
            
            # Check if Local IP changed
            if (now - last_ip_check).total_seconds() >= ip_check_sec:
                new_local_ip = self.get_local_ip()
                if new_local_ip != ip:
                    self.log(f"🔄 Phát hiện IP thay đổi: {ip} → {new_local_ip}")
                    old_ip = ip
                    ip = new_local_ip
                    # Update UI và database
                    self.root.after(0, lambda: self.ip_var.set(new_local_ip))
                    # Update port_list
                    for entry in self.port_list:
                        entry['ip'] = new_local_ip
                    # Update table display
                    self.root.after(0, self.update_table_display)
                    # GỬI NGAY data mới lên server với IP mới
                    for entry in self.port_list:
                        port = entry['port']
                        name = entry['name']
                        current_status = "ON" if self.is_vmix_on_port(port) else "OFF"
                        try:
                            data = {
                                "name": name,
                                "ip": new_local_ip,
                                "ipwan": wan_ip,
                                "status": current_status,
                                "port": port,
                                "statusapp": 1
                            }
                            url = SERVER_URL
                            headers = {"Content-Type": "application/json"}
                            response = requests.post(url, json=data, headers=headers, timeout=10)
                            if response.status_code == 200:
                                self.log(f"✅ Đã cập nhật IP mới: {name}")
                        except Exception as e:
                            self.log(f"❌ Lỗi update IP: {name}")
                last_ip_check = now
            
            # Check if WAN IP needs refresh
            if (now - last_wan_check).total_seconds() >= wan_refresh_sec:
                new_wan = self.get_wan_ip()
                if new_wan != wan_ip:
                    self.log(f"🌐 WAN IP thay đổi: {wan_ip} → {new_wan}")
                    wan_ip = new_wan
                    # Update port_list
                    for entry in self.port_list:
                        entry['ipwan'] = new_wan
                    # Update table display
                    self.root.after(0, self.update_table_display)
                    # GỬI NGAY data mới lên server với IPWAN mới
                    for entry in self.port_list:
                        port = entry['port']
                        name = entry['name']
                        current_status = "ON" if self.is_vmix_on_port(port) else "OFF"
                        try:
                            data = {
                                "name": name,
                                "ip": ip,
                                "ipwan": new_wan,
                                "status": current_status,
                                "port": port,
                                "statusapp": 1
                            }
                            url = SERVER_URL
                            headers = {"Content-Type": "application/json"}
                            response = requests.post(url, json=data, headers=headers, timeout=10)
                            if response.status_code == 200:
                                self.log(f"✅ Đã cập nhật IPWAN mới: {name}")
                        except Exception as e:
                            self.log(f"❌ Lỗi update IPWAN: {name}")
                last_wan_check = now
            
            # ── Đo thông số hệ thống (1 lần / vòng lặp, dùng chung cho mọi port) ──
            # Lấy ping từ background thread (non-blocking)
            with self._ping_lock:
                ping_ms = self._ping_ms
            cpu_pct = self.measure_cpu()   # non-blocking
            mem_pct = self.measure_memory()

            # ── vMix API Stats (một lần mỗi chu kỳ, dùng localhost) ──
            vmix_stats = self.get_vmix_stats()

            ping_str    = f"{ping_ms:.0f}" if ping_ms is not None else '—'
            timeout_str = str(self.ping_timeout_count)
            cpu_str     = f"{cpu_pct:.1f}" if cpu_pct is not None else '—'
            mem_str     = f"{mem_pct:.1f}" if mem_pct is not None else '—'

            # vMix status strings for table
            rec_str  = '🔴 ON' if vmix_stats['recording'] else 'OFF'
            live_str = '🔴 ON' if vmix_stats['streaming'] else 'OFF'
            ext_str  = '🟢 ON' if vmix_stats['external']  else 'OFF'

            # ── Resolution: ưu tiên API/preset (output res), fallback file ──
            res_str = vmix_stats.get('resolution', '—') or '—'

            # ── SRT Quality: ưu tiên API/preset (real-time), fallback current.config ──
            srt_by_port = vmix_stats.get('srt_by_port', {})
            if not srt_by_port:
                _, srt_by_port = self.get_res_and_srt_from_file()
            srt_fallback = next(iter(srt_by_port.values()), '—')

            # Check each port
            for entry in self.port_list:
                port = entry['port']
                name = entry['name']

                # SRT quality: ưu tiên match theo port, fallback giá trị chung
                srt_str = srt_by_port.get(port, srt_fallback)

                # Cập nhật thông số vào port_list để update_table_display dùng
                entry['ping']    = ping_str
                entry['timeout'] = timeout_str
                entry['cpu']     = cpu_str
                entry['memory']  = mem_str
                entry['rec']     = rec_str
                entry['live']    = live_str
                entry['ext']     = ext_str
                entry['resolution'] = res_str
                entry['srt']     = srt_str
                
                # Kiểm tra trạng thái thực tế của vMix
                vmix_running = self.is_vmix_on_port(port)
                current_status = "ON" if vmix_running else "OFF"
                
                # Luôn gửi (để server nhận ping/temp/mem), nhưng chỉ log khi thay đổi status
                try:
                    data = {
                        "name": name,
                        "ip": ip,
                        "ipwan": wan_ip,
                        "status": current_status,
                        "port": port,
                        "statusapp": 1,
                        # ── Thông số hệ thống ──
                        "ping": ping_ms,
                        "ping_timeouts": self.ping_timeout_count,
                        "temperature": cpu_pct,
                        "memory": mem_pct,
                        # ── vMix Status ──
                        "vmix_recording": vmix_stats.get('recording', False),
                        "vmix_streaming": vmix_stats.get('streaming', False),
                        "vmix_external":  vmix_stats.get('external',  False),
                        # ── Resolution & SRT Quality ──
                        "resolution":  res_str,
                        "srt_quality": srt_str,
                    }
                    url = SERVER_URL
                    headers = {"Content-Type": "application/json"}
                    response = self.http_session.post(url, json=data, headers=headers, timeout=5)
                    if response.status_code == 200:
                        if prev_status.get(port) != current_status:
                            icon = "🟢" if current_status == "ON" else "🔴"
                            self.log(f"{icon} SRT {current_status}: {name} {ip}:{port}")
                            prev_status[port] = current_status
                    elif response.status_code == 500:
                        error_msg = ""
                        try:
                            error_msg = response.json().get('detail', response.text[:100])
                        except:
                            error_msg = response.text[:100]
                        self.log(f"⚠️ Server error 500 ({name}): {error_msg}")
                    else:
                        self.log(f"❌ HTTP {response.status_code} gửi {name}")
                except requests.exceptions.Timeout:
                    self.log(f"⏱️ Timeout gửi {name}")
                except requests.exceptions.ConnectionError:
                    self.log(f"❌ Mất kết nối ({name})")
                except Exception as e:
                    self.log(f"❌ ERROR {name}: {str(e)}")

            # Cập nhật table hiển thị ping/temp/mem
            self.root.after(0, self.update_table_display)

            # Sleep 1 giây
            for _ in range(10):
                if not self.is_running:
                    break
                time.sleep(0.1)


def ensure_single_instance():
    """Đảm bảo chỉ có 1 instance của app đang chạy"""
    global SINGLE_INSTANCE_SOCKET
    try:
        # Bind to localhost với port unique (51234 cho VmixMonitor)
        SINGLE_INSTANCE_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        SINGLE_INSTANCE_SOCKET.bind(('127.0.0.1', 51234))
        return True
    except socket.error:
        # Port đã được bind = app đã chạy rồi
        return False

def focus_existing_window():
    """Focus vào cửa sổ đang chạy (Windows only)"""
    try:
        import win32gui
        import win32con
        
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "vMix Monitor Pro" in title:
                    # Restore window nếu bị minimize
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    # Bring to front
                    win32gui.SetForegroundWindow(hwnd)
                    return False  # Stop enumeration
            return True
        
        win32gui.EnumWindows(callback, None)
        return True
    except (ImportError, Exception):
        # Không có pywin32 hoặc EnumWindows lỗi
        return False

def main():
    # Set taskbar icon BEFORE creating window
    try:
        import ctypes
        myappid = 'vmixmonitor.pro.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass
    
    # Kiểm tra single instance
    if not ensure_single_instance():
        # App đã chạy rồi, thử focus vào cửa sổ hiện tại
        if not focus_existing_window():
            # Không focus được (không có pywin32), show message
            import tkinter.messagebox as mb
            root = tk.Tk()
            root.withdraw()
            mb.showwarning(
                "Ứng dụng đang chạy",
                "vMix Monitor Pro đang chạy rồi!\n\n"
                "Kiểm tra taskbar hoặc system tray.",
                parent=root
            )
            root.destroy()
        sys.exit(0)
    
    # Tạo app nếu chưa có instance nào chạy
    root = ttk.Window(
        title="vMix Monitor Pro",
        themename="darkly",  # Modern dark theme: darkly, superhero, cyborg, vapor, solar
        size=(900, 700)
    )
    app = VmixMonitorGUI(root)
    root.mainloop()
    
    # Cleanup socket khi thoát
    if SINGLE_INSTANCE_SOCKET:
        SINGLE_INSTANCE_SOCKET.close()

if __name__ == "__main__":
    main()
