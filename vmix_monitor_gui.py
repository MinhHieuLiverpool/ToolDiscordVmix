
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
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
        self.root.title("Vmix Monitor Tool")
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
        
        # Override close button để ẩn xuống tray thay vì đóng
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    def setup_ui(self):
        # Cố định kích thước cửa sổ lớn hơn
        win_w, win_h = 750, 600
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.resizable(False, False)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (win_w // 2)
        y = (self.root.winfo_screenheight() // 2) - (win_h // 2)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        main_frame = tk.Frame(self.root, relief=tk.RIDGE, borderwidth=2, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # === TOP SECTION: IP máy (read-only) ===
        top_frame = tk.Frame(main_frame, bg='#f0f0f0')
        top_frame.pack(pady=8)
        
        tk.Label(top_frame, text="IP máy:", bg='#f0f0f0', font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)
        self.ip_entry = tk.Entry(top_frame, textvariable=self.ip_var, width=20, justify='center', 
                                state='readonly', font=('Arial', 11), relief=tk.SUNKEN, bd=2)
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        
        # === INPUT SECTION: Add new port entry ===
        input_frame = tk.LabelFrame(main_frame, text="Thêm Port mới", bg='#f0f0f0', 
                                    font=('Arial', 10, 'bold'), padx=10, pady=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Tên máy
        tk.Label(input_frame, text="Tên máy:", bg='#f0f0f0', width=10, anchor='e').grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = tk.Entry(input_frame, textvariable=self.name_var, width=25, font=('Arial', 10))
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Port
        tk.Label(input_frame, text="Port:", bg='#f0f0f0', width=10, anchor='e').grid(row=0, column=2, padx=5, pady=5)
        self.port_entry = tk.Entry(input_frame, textvariable=self.port_var, width=15, font=('Arial', 10))
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Nút Thêm
        add_btn = tk.Button(input_frame, text="Thêm", command=self.add_port_entry, 
                          bg='#2196F3', fg='white', width=10, font=('Arial', 10, 'bold'))
        add_btn.grid(row=0, column=4, padx=10, pady=5)
        
        # === TABLE SECTION: List of ports (CHIỀU CAO GIẢM) ===
        table_frame = tk.LabelFrame(main_frame, text="Danh sách Port", bg='#f0f0f0', 
                                   font=('Arial', 10, 'bold'))
        table_frame.pack(fill=tk.BOTH, padx=10, pady=5)
        
        # Create Treeview với chiều cao thấp hơn (height=6)
        columns = ("name", "ip", "ipwan", "port")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=6)
        
        # Căn giữa title và các giá trị
        self.tree.heading("name", text="Tên máy", anchor='center')
        self.tree.heading("ip", text="IP", anchor='center')
        self.tree.heading("ipwan", text="IP WAN", anchor='center')
        self.tree.heading("port", text="Port", anchor='center')
        
        self.tree.column("name", width=250, anchor='center')
        self.tree.column("ip", width=150, anchor='center')
        self.tree.column("ipwan", width=150, anchor='center')
        self.tree.column("port", width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Nút Xóa (delete selected item)
        self.delete_btn = tk.Button(table_frame, text="Xóa mục đã chọn", command=self.delete_selected, 
                             bg='#f44336', fg='white', font=('Arial', 9, 'bold'))
        self.delete_btn.pack(pady=5)
        
        # === CONTROL SECTION: Start/Stop button ===
        control_frame = tk.Frame(main_frame, bg='#f0f0f0')
        control_frame.pack(pady=10)
        
        self.start_btn = tk.Button(control_frame, text="START", command=self.toggle_monitoring, 
                                  bg='#4CAF50', fg='white', width=20, height=2, font=('Arial', 12, 'bold'))
        self.start_btn.pack()

        # === LOG SECTION (HIỂN THỊ RÕ) ===
        log_frame = tk.LabelFrame(main_frame, text="LOGS:", relief=tk.RIDGE, borderwidth=2, 
                                 bg='#f0f0f0', labelanchor='nw', font=('Arial', 10, 'bold'))
        log_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=5, bg='black', fg='#00ff00', 
                                                 font=('Consolas', 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    
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
    
    def show_window(self, icon=None, item=None):
        """Hiện lại cửa sổ từ system tray"""
        self.root.deiconify()  # Hiện cửa sổ
        self.root.lift()  # Đưa lên trên cùng
        self.root.focus_force()  # Focus vào cửa sổ
    
    def quit_app(self, icon=None, item=None):
        """Thoát hoàn toàn ứng dụng"""
        self.is_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()
    
    def load_data_from_database(self):
        """Load dữ liệu từ database theo IP máy hiện tại"""
        import requests
        try:
            ip = self.ip_var.get().strip()
            url = f"https://tooldiscordvmix.onrender.com/get_by_ip?ip={ip}"
            response = requests.get(url, timeout=10)
            
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
                        self.log(f"Đã tải {loaded_count} port từ database (IP: {ip})")
                    else:
                        self.log(f"Không có dữ liệu cho IP {ip} trong database")
                else:
                    self.log(f"Không có dữ liệu cho IP {ip} trong database")
            else:
                self.log(f"Không thể tải dữ liệu: {response.status_code}")
        except Exception as e:
            self.log(f"Lỗi khi load dữ liệu: {str(e)}")
    
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
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                self.log(f"Đã xóa trên DB: {name} - Port {port}")
            else:
                self.log(f"Lỗi xóa trên DB: {response.status_code}")
        except Exception as e:
            self.log(f"ERROR xóa DB: {str(e)}")

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
        
        if not self.port_list:
            self.log("Không có port nào trong danh sách!")
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
                response = requests.post(url, json=data, headers=headers, timeout=10)
                if response.status_code == 200:
                    status_text = "ON" if status_value == 1 else "OFF"
                    self.log(f"App status {status_text}: {entry['name']} - Port {entry['port']}")
                else:
                    self.log(f"Lỗi gửi {entry['name']}: {response.status_code}")
        except Exception as e:
            self.log(f"ERROR gửi app status: {str(e)}")

    def toggle_monitoring(self):
        if not self.is_running:
            if not self.port_list:
                messagebox.showwarning("Cảnh báo", "Vui lòng thêm ít nhất một port!")
                return
            
            self.is_running = True
            self.start_btn.config(text="STOP", bg="#f44336")
            self.delete_btn.config(state=tk.DISABLED)  # Disable nút xóa khi START
            self.log("Bắt đầu gửi dữ liệu...")
            # Gửi statusapp = 1 (ON)
            threading.Thread(target=lambda: self.send_app_status(1), daemon=True).start()
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_running = False
            self.log("Đang dừng và cập nhật trạng thái...")
            # Bước 1: Gửi statusapp = 0 (OFF) để frontend fetch trước
            threading.Thread(target=self.stop_and_cleanup, daemon=True).start()
            self.start_btn.config(text="START", bg="#4CAF50")
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
        wan_refresh_sec = 300  # Refresh WAN IP every 5 minutes
        
        self.log(f"Bắt đầu giám sát {len(self.port_list)} port(s)...")
        
        while self.is_running:
            # Check if WAN IP needs refresh
            now = datetime.now(VIETNAM_TZ)
            if (now - last_wan_check).total_seconds() >= wan_refresh_sec:
                new_wan = self.get_wan_ip()
                if new_wan != wan_ip:
                    self.log(f"WAN IP thay đổi: {wan_ip} -> {new_wan}")
                    wan_ip = new_wan
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
                        response = requests.post(url, json=data, headers=headers, timeout=10)
                        if response.status_code == 200:
                            self.log(f"SRT {current_status}: {name} {ip}:{port}")
                        else:
                            self.log(f"Lỗi gửi {name}: {response.status_code}")
                        prev_status[port] = current_status
                    except Exception as e:
                        self.log(f"ERROR gửi HTTP ({name}): {str(e)}")
            
            # Sleep 1 second (check every second)
            for _ in range(10):
                if not self.is_running:
                    break
                time.sleep(0.1)


def main():
    root = tk.Tk()
    app = VmixMonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
