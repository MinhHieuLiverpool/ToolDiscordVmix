
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
from datetime import datetime


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
        self.root.geometry("320x200")
        self.ip_var = tk.StringVar(value=self.get_local_ip())
        self.port_var = tk.StringVar(value="")
        self.is_running = False
        self.log_queue = queue.Queue()
        self.setup_ui()
        self.check_log_queue()

    def setup_ui(self):
        # Cố định kích thước cửa sổ
        win_w, win_h = 420, 240
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.resizable(False, False)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (win_w // 2)
        y = (self.root.winfo_screenheight() // 2) - (win_h // 2)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        main_frame = tk.Frame(self.root, relief=tk.RIDGE, borderwidth=2, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Dùng pack để căn giữa các thành phần
        input_frame = tk.Frame(main_frame, bg='#f0f0f0')
        input_frame.pack(pady=10)
        row1 = tk.Frame(input_frame, bg='#f0f0f0')
        row1.pack(fill=tk.X, pady=4)
        tk.Label(row1, text="IP máy:", bg='#f0f0f0', anchor='e', width=10).pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(row1, textvariable=self.ip_var, width=22, justify='center')
        self.ip_entry.pack(side=tk.LEFT, padx=8)
        row2 = tk.Frame(input_frame, bg='#f0f0f0')
        row2.pack(fill=tk.X, pady=4)
        tk.Label(row2, text="Port:", bg='#f0f0f0', anchor='e', width=10).pack(side=tk.LEFT)
        self.port_entry = tk.Entry(row2, textvariable=self.port_var, width=22, justify='center')
        self.port_entry.pack(side=tk.LEFT, padx=8)

        # Nút Start căn giữa
        self.start_btn = tk.Button(main_frame, text="START", command=self.toggle_monitoring, bg='#4CAF50', fg='white', width=16, font=('Arial', 11, 'bold'))
        self.start_btn.pack(pady=8)

        # Log nhỏ gọn phía dưới
        log_frame = tk.LabelFrame(main_frame, text="LOGS:", relief=tk.RIDGE, borderwidth=2, bg='#f0f0f0', labelanchor='nw')
        log_frame.pack(fill=tk.X, padx=2, pady=2)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=3, bg='black', fg='#00ff00', font=('Consolas', 10), state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        # (Đã loại bỏ các dòng dùng grid để tránh lỗi mix pack và grid)

    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
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

    def toggle_monitoring(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(text="STOP", bg="#f44336")
            # Disable IP và Port khi đang chạy
            self.ip_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.log("Bắt đầu gửi dữ liệu...")
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_running = False
            self.start_btn.config(text="START", bg="#4CAF50")
            # Enable IP và Port khi dừng
            self.ip_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            self.log("Đã dừng gửi dữ liệu.")

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
        
        # Kiểm tra IP và Port có hợp lệ không
        ip = self.ip_var.get().strip()
        port_str = self.port_var.get().strip()
        
        if not ip or not port_str:
            self.log("ERROR: IP và Port không được để trống!")
            self.is_running = False
            self.start_btn.config(text="START", bg="#4CAF50")
            self.ip_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            return
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError()
        except:
            self.log("ERROR: Port phải là số từ 1-65535!")
            self.is_running = False
            self.start_btn.config(text="START", bg="#4CAF50")
            self.ip_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            return
        
        wan_ip = self.get_wan_ip()
        name = "MÁY CHÍNH"  # hoặc cho phép nhập tên nếu cần
        while self.is_running:
            try:
                data = {
                    "name": name,
                    "ip": ip,
                    "ipwan": wan_ip,
                    "status": "ON",
                    "port": port
                }
                url = "http://localhost:8088"
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json=data, headers=headers, timeout=10)
                if response.status_code == 200:
                    self.log(f"Đã gửi: {ip}:{port} - {data['status']}")
                else:
                    self.log(f"Lỗi gửi: {response.status_code} {response.content}")
            except Exception as e:
                self.log(f"ERROR gửi HTTP: {str(e)}")
            import time
            for _ in range(10):
                if not self.is_running:
                    # Gửi trạng thái OFF khi dừng
                    try:
                        data = {
                            "name": name,
                            "ip": ip,
                            "ipwan": wan_ip,
                            "status": "OFF",
                            "port": port
                        }
                        url = "http://localhost:8088"
                        headers = {"Content-Type": "application/json"}
                        requests.post(url, json=data, headers=headers, timeout=5)
                        self.log(f"Đã gửi: {ip}:{port} - OFF")
                    except Exception:
                        pass
                    break
                time.sleep(0.5)


        # Đã loại bỏ code camera list/canvas/scrollbar vì GUI tối giản
        
        # Add button
        add_btn_frame = tk.Frame(monitor_frame, bg='#f0f0f0')
        add_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(add_btn_frame, text="[ + Add New Camera ]", command=self.add_camera, bg='#e0e0e0').pack(anchor=tk.W)
        
        # Advanced section

        tk.Button(btn_frame, text="Clear Logs", command=self.clear_logs, 
                  bg='#9E9E9E', fg='white', width=15).pack(side=tk.LEFT, padx=5)
            # Nút Start/Stop đã được thêm ở trên, không cần btn_frame hoặc nút Clear Logs nữa
        
        # Store entry widgets to read current values
        self.camera_entries = []
        
        # Display cameras
        for idx, cam in enumerate(self.cameras):
            cam_frame = tk.Frame(self.camera_list_frame, bg='#f0f0f0')
            cam_frame.pack(fill=tk.X, pady=2)
            
            # Editable name entry (without brackets)
            name_var = tk.StringVar(value=cam['name'])
            name_entry = tk.Entry(cam_frame, textvariable=name_var, width=22, 
                                  relief=tk.RIDGE, borderwidth=1, bg='white')
            name_entry.pack(side=tk.LEFT, padx=2)
            name_entry.bind('<FocusOut>', lambda e, i=idx, v=name_var: self.update_camera_name(i, v.get()))
            name_entry.bind('<Return>', lambda e, i=idx, v=name_var: self.update_camera_name(i, v.get()))
            
            # Editable port entry (without brackets)
            port_var = tk.StringVar(value=str(cam['port']))
            port_entry = tk.Entry(cam_frame, textvariable=port_var, width=17, 
                                  relief=tk.RIDGE, borderwidth=1, bg='white')
            port_entry.pack(side=tk.LEFT, padx=2)
            port_entry.bind('<FocusOut>', lambda e, i=idx, v=port_var: self.update_camera_port(i, v.get()))
            port_entry.bind('<Return>', lambda e, i=idx, v=port_var: self.update_camera_port(i, v.get()))
            
            # Store entry widgets
            self.camera_entries.append({'name_var': name_var, 'port_var': port_var})
            
            delete_btn = tk.Button(cam_frame, text="XÓA", command=lambda i=idx: self.delete_camera(i), 
                                   bg='#f44336', fg='white', font=('Arial', 9, 'bold'), 
                                   relief=tk.FLAT, cursor='hand2')
            delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Show/hide scrollbar based on number of cameras
        if len(self.cameras) > 4:
            self.camera_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.camera_scrollbar.pack_forget()
    
    def update_camera_name(self, index, new_name):
        """Update camera name when edited"""
        if 0 <= index < len(self.cameras):
            self.cameras[index]['name'] = new_name.strip()
    
    def update_camera_port(self, index, new_port):
        """Update camera port when edited"""
        if 0 <= index < len(self.cameras):
            try:
                port = int(new_port.strip())
                if 1 <= port <= 65535:
                    self.cameras[index]['port'] = port
                else:
                    messagebox.showerror("Error", "Port must be between 1 and 65535!")
                    self.refresh_camera_list()
            except ValueError:
                messagebox.showerror("Error", "Invalid port number!")
                self.refresh_camera_list()
    
    def add_camera(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Camera")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog on main window
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="Camera Name:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        name_entry = tk.Entry(dialog, width=20)
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        
        tk.Label(dialog, text="Port:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        port_entry = tk.Entry(dialog, width=20)
        port_entry.grid(row=1, column=1, padx=10, pady=10)
        
        def save_camera():
            name = name_entry.get().strip()
            port = port_entry.get().strip()
            
            if not name or not port:
                messagebox.showwarning("Warning", "Please fill all fields!")
                return
            
            try:
                port = int(port)
                if port < 1 or port > 65535:
                    raise ValueError()
            except:
                messagebox.showerror("Error", "Invalid port number!")
                return
            
            self.cameras.append({"name": name, "port": port, "enabled": True})
            self.refresh_camera_list()
            dialog.destroy()
        
        tk.Button(dialog, text="Add", command=save_camera, bg='#4CAF50', fg='white', width=10).grid(row=2, column=0, columnspan=2, pady=10)
    
    def delete_camera(self, index):
        if messagebox.askyesno("Confirm", f"Delete camera {self.cameras[index]['name']}?"):
            self.cameras.pop(index)
            self.refresh_camera_list()
    
    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
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
    
    def start_monitoring(self):
        if not self.cameras:
            messagebox.showwarning("Warning", "Please add at least one camera!")
            return
        
        webhook = self.webhook_var.get().strip()
        if not webhook:
            messagebox.showerror("Error", "Webhook URL is required!")
            return
        
        # Read current values from entry widgets before sending
        if hasattr(self, 'camera_entries'):
            for idx, entry_data in enumerate(self.camera_entries):
                if idx < len(self.cameras):
                    # Update name
                    new_name = entry_data['name_var'].get().strip()
                    if new_name:
                        self.cameras[idx]['name'] = new_name
                    
                    # Update port
                    try:
                        new_port = int(entry_data['port_var'].get().strip())
                        if 1 <= new_port <= 65535:
                            self.cameras[idx]['port'] = new_port
                    except ValueError:
                        pass  # Keep existing port if invalid
        
        self.log("Sending notification...")
        
        # Run PowerShell script once (no loop)
        thread = threading.Thread(target=self.run_monitoring_script, daemon=True)
        thread.start()
    
    def run_monitoring_script(self):
        import requests
        try:
            wan_ip = self.get_wan_ip()
            open_ports = self.scan_udp_ports(10000, 90000)
            # Chuẩn bị dữ liệu gửi lên server
            data = {
                "webhook": self.webhook_var.get(),
                "prefix": self.prefix_var.get(),
                "scan_speed_ms": self.scan_speed_var.get(),
                "check_ip_sec": self.check_ip_var.get(),
                "cameras": self.cameras,
                "ipwan": wan_ip,
                "open_ports": open_ports
            }
            url = "http://localhost:8088"  # Địa chỉ server nhận dữ liệu
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=15)
            if response.status_code == 200:
                self.log(f"Gửi dữ liệu thành công tới server! IP WAN: {wan_ip}, Open UDP Ports: {open_ports}")
            else:
                self.log(f"Lỗi gửi dữ liệu: {response.status_code} {response.content}")
        except Exception as e:
            self.log(f"ERROR gửi HTTP: {str(e)}")
    
    def clear_logs(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def save_config(self):
        """Save configuration to JSON file"""
        if not self.cameras:
            messagebox.showwarning("Warning", "No cameras to save!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="vmix_config.json"
        )
        
        if not file_path:
            return
        
        try:
            config = {
                "webhook": self.webhook_var.get(),
                "prefix": self.prefix_var.get(),
                "scan_speed_ms": self.scan_speed_var.get(),
                "check_ip_sec": self.check_ip_var.get(),
                "cameras": self.cameras
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Success", f"Configuration saved to:\n{file_path}")
            self.log(f"Configuration saved: {os.path.basename(file_path)}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{str(e)}")
            self.log(f"ERROR saving config: {str(e)}")
    
    def open_config(self):
        """Open configuration from JSON file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="vmix_config.json"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Load configuration
            self.webhook_var.set(config.get("webhook", ""))
            self.prefix_var.set(config.get("prefix", ""))
            self.scan_speed_var.set(config.get("scan_speed_ms", 1000))
            self.check_ip_var.set(config.get("check_ip_sec", 300))
            
            # Load cameras
            cameras = config.get("cameras", [])
            if cameras:
                self.cameras = cameras
                self.refresh_camera_list()
            
            messagebox.showinfo("Success", f"Configuration loaded from:\n{file_path}")
            self.log(f"Configuration loaded: {os.path.basename(file_path)}")
        
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON format:\n{str(e)}")
            self.log(f"ERROR: Invalid JSON file")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration:\n{str(e)}")
            self.log(f"ERROR loading config: {str(e)}")

def main():
    root = tk.Tk()
    app = VmixMonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
