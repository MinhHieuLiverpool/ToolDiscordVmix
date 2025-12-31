
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

# Timezone configuration - Vietnam
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


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
        self.root.title("🎥 vMix Monitor Pro")
        
        # Set icon if exists
        try:
            self.root.iconbitmap('assets/icon.ico')
        except:
            pass
        
        self.ip_var = tk.StringVar(value=self.get_local_ip())
        self.name_var = tk.StringVar(value="")
        self.port_var = tk.StringVar(value="")
        self.is_running = False
        self.log_queue = queue.Queue()
        self.tray_icon = None
        self.port_list = []  # Danh sách các port entries
        self.setup_ui()
        self.setup_tray()
        self.check_log_queue()
        
        # Load dữ liệu từ database theo IP máy hiện tại
        self.load_data_from_database()
        
        # Override close button để hỏi user
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # Cố định kích thước cửa sổ
        win_w, win_h = 900, 700
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.resizable(False, False)
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
        
        # Refresh IP button
        refresh_ip_btn = ttk.Button(
            ip_frame,
            text="🔄",
            command=self.refresh_ip,
            bootstyle="info-outline",
            width=3
        )
        refresh_ip_btn.pack(side=LEFT, padx=(0, 5))
        
        # Import from old IP button
        import_btn = ttk.Button(
            ip_frame,
            text="📥",
            command=self.show_import_dialog,
            bootstyle="warning-outline",
            width=3
        )
        import_btn.pack(side=LEFT)
        
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
        add_btn = ttk.Button(
            input_grid, 
            text="➕ Thêm", 
            command=self.add_port_entry,
            bootstyle="success",
            width=12
        )
        add_btn.grid(row=0, column=4, padx=10, pady=5)
        
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
        
        # Create Treeview
        columns = ("name", "ip", "ipwan", "port")
        self.tree = ttk.Treeview(
            table_container, 
            columns=columns, 
            show='headings',
            height=8,
            bootstyle="info"
        )
        
        # Headings with icons
        self.tree.heading("name", text="📌 Tên máy", anchor=CENTER)
        self.tree.heading("ip", text="🖥️ IP Local", anchor=CENTER)
        self.tree.heading("ipwan", text="🌐 IP WAN", anchor=CENTER)
        self.tree.heading("port", text="🔌 Port", anchor=CENTER)
        
        # Column widths
        self.tree.column("name", width=280, anchor=CENTER)
        self.tree.column("ip", width=180, anchor=CENTER)
        self.tree.column("ipwan", width=180, anchor=CENTER)
        self.tree.column("port", width=120, anchor=CENTER)
        
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
            url = f"https://tooldiscordvmix.onrender.com/get_by_ip?ip={old_ip}"
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
                                self.port_list.append({"name": name, "port": port, "ip": current_ip, "ipwan": ipwan})
                                # Add to tree
                                self.tree.insert("", tk.END, values=(name, current_ip, ipwan, port))
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
            url = "https://tooldiscordvmix.onrender.com/update_ip"
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
                url = "https://tooldiscordvmix.onrender.com/update_ip"
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
            url = "https://tooldiscordvmix.onrender.com/"
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
            url = f"https://tooldiscordvmix.onrender.com/get_by_ip?ip={ip}"
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
                        name = entry_data.get('name', '')
                        port = entry_data.get('port', 0)
                        entry_ip = entry_data.get('ip', ip)
                        ipwan = entry_data.get('ipwan', 'unknown')
                        
                        if name and port:
                            # Add to list
                            self.port_list.append({"name": name, "port": port, "ip": entry_ip, "ipwan": ipwan})
                            # Add to tree
                            self.tree.insert("", tk.END, values=(name, entry_ip, ipwan, port))
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
            url = "https://tooldiscordvmix.onrender.com/"
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
        wan_ip = self.get_wan_ip()
        
        # Check duplicate - Kiểm tra trùng TÊN MÁY hoặc trùng PORT
        for entry in self.port_list:
            if entry['name'] == name:
                messagebox.showwarning("Cảnh báo", f"Tên máy '{name}' đã tồn tại!")
                return
            if entry['port'] == port:
                messagebox.showwarning("Cảnh báo", f"Port {port} đã được sử dụng!")
                return
        
        # Add to list
        self.port_list.append({"name": name, "port": port, "ip": ip, "ipwan": wan_ip})
        
        # Add to tree
        self.tree.insert("", tk.END, values=(name, ip, wan_ip, port))
        
        # Clear input fields
        self.name_var.set("")
        self.port_var.set("")
        
        self.log(f"Đã thêm: {name} - {ip} - Port {port}")
    
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
                port = int(values[3])
                
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
            url = "https://tooldiscordvmix.onrender.com/delete"
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
                url = "https://tooldiscordvmix.onrender.com/delete"
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
                url = "https://tooldiscordvmix.onrender.com"
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
            self.start_btn.config(text="⏹️ STOP MONITORING", bootstyle="danger")
            self.status_label.config(text="● Running", bootstyle="success")
            self.delete_btn.config(state=tk.DISABLED)  # Disable nút xóa khi START
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
    
    def stop_and_cleanup(self):
        """Dừng và cập nhật trạng thái: chỉ gửi statusapp=0"""
        # Gửi statusapp = 0 (OFF)
        self.send_app_status(0)
        self.log("Đã dừng và cập nhật trạng thái OFF.")


    def is_vmix_on_port(self, port):
        """Kiểm tra xem vMix có đang lắng nghe trên port UDP không"""
        try:
            result = subprocess.run(
                ['netstat', '-ano', '-p', 'udp'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Parse netstat output
            for line in result.stdout.splitlines():
                if 'UDP' in line and f':{port} ' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            pid = int(parts[-1])
                            # Kiểm tra process name
                            proc_result = subprocess.run(
                                ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                                capture_output=True,
                                text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                            if 'vmix' in proc_result.stdout.lower():
                                return True
                        except:
                            pass
            return False
        except Exception as e:
            self.log(f"ERROR kiểm tra vMix: {str(e)}")
            return False
    
    def get_wan_ip(self):
        import requests
        urls = [
            'https://api.ipify.org',
            'https://ifconfig.me/ip',
            'https://ipinfo.io/ip',
            'https://checkip.amazonaws.com'
        ]
        for u in urls:
            try:
                ip = requests.get(u, timeout=5).text.strip()
                if ip and ('.' in ip or ':' in ip):
                    return ip
            except Exception:
                pass
        return "unknown"

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
        wan_refresh_sec = 300  # Refresh WAN IP every 5 minutes
        ip_check_sec = 60  # Check local IP every 60 seconds
        
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
                    threading.Thread(target=lambda: self.update_ip_in_database(old_ip, new_local_ip), daemon=True).start()
                    # Update port_list
                    for entry in self.port_list:
                        entry['ip'] = new_local_ip
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
                last_wan_check = now
            
            # Check each port
            for entry in self.port_list:
                port = entry['port']
                name = entry['name']
                
                # Kiểm tra trạng thái thực tế của vMix
                vmix_running = self.is_vmix_on_port(port)
                current_status = "ON" if vmix_running else "OFF"
                
                # Chỉ gửi khi có thay đổi trạng thái hoặc lần đầu tiên
                if prev_status.get(port) != current_status:
                    try:
                        data = {
                            "name": name,
                            "ip": ip,
                            "ipwan": wan_ip,
                            "status": current_status,
                            "port": port,
                            "statusapp": 1  # App is running (1=ON)
                        }
                        url = "https://tooldiscordvmix.onrender.com"
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(url, json=data, headers=headers, timeout=15)
                        if response.status_code == 200:
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
            
            # Sleep 1 second (check every second)
            for _ in range(10):
                if not self.is_running:
                    break
                time.sleep(0.1)


def main():
    root = ttk.Window(
        title="vMix Monitor Pro",
        themename="darkly",  # Modern dark theme: darkly, superhero, cyborg, vapor, solar
        size=(900, 700)
    )
    app = VmixMonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
