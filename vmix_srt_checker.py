import tkinter as tk
from tkinter import scrolledtext, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import subprocess
import threading
from datetime import datetime
import pytz
import socket

# Timezone configuration - Vietnam
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


class VmixSRTChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("vMix SRT Checker")
        
        # Set icon if exists
        try:
            self.root.iconbitmap('assets/Discord-Logo.ico')
        except:
            pass
        
        self.ip_var = tk.StringVar(value="")
        self.port_var = tk.StringVar(value="")
        self.is_checking = False
        self.check_thread = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # Cố định kích thước cửa sổ
        win_w, win_h = 700, 500
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
            text="🔍 vMix SRT Checker", 
            font=('Segoe UI', 18, 'bold'),
            bootstyle="primary"
        )
        title_label.pack(side=LEFT)
        
        # === INPUT SECTION ===
        input_frame = ttk.Labelframe(
            main_frame, 
            text="➕ Nhập Thông Tin Kiểm Tra",
            padding=15,
            bootstyle="primary"
        )
        input_frame.pack(fill=X, pady=(0, 15))
        
        # Input grid
        input_grid = ttk.Frame(input_frame)
        input_grid.pack(fill=X)
        
        # IP
        ttk.Label(
            input_grid, 
            text="IP đích:", 
            font=('Segoe UI', 10),
            width=12
        ).grid(row=0, column=0, padx=5, pady=5, sticky=E)
        
        self.ip_entry = ttk.Entry(
            input_grid, 
            textvariable=self.ip_var, 
            width=30,
            font=('Segoe UI', 10)
        )
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky=EW)
        
        # Port
        ttk.Label(
            input_grid, 
            text="Port:", 
            font=('Segoe UI', 10),
            width=12
        ).grid(row=1, column=0, padx=5, pady=5, sticky=E)
        
        self.port_entry = ttk.Entry(
            input_grid, 
            textvariable=self.port_var, 
            width=15,
            font=('Segoe UI', 10)
        )
        self.port_entry.grid(row=1, column=1, padx=5, pady=5, sticky=W)
        
        input_grid.columnconfigure(1, weight=1)
        
        # === STATUS DISPLAY ===
        status_frame = ttk.Labelframe(
            main_frame, 
            text="📊 Trạng Thái SRT",
            padding=15,
            bootstyle="info"
        )
        status_frame.pack(fill=X, pady=(0, 15))
        
        # Status container
        status_container = ttk.Frame(status_frame)
        status_container.pack(fill=X)
        
        ttk.Label(
            status_container,
            text="Trạng thái:",
            font=('Segoe UI', 12, 'bold')
        ).pack(side=LEFT, padx=10)
        
        self.status_display = ttk.Label(
            status_container,
            text="● Chưa kiểm tra",
            font=('Segoe UI', 14, 'bold'),
            bootstyle="secondary"
        )
        self.status_display.pack(side=LEFT, padx=10)
        
        # === CONTROL SECTION ===
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=X, pady=(0, 15))
        
        # Button container
        btn_container = ttk.Frame(control_frame)
        btn_container.pack()
        
        self.check_btn = ttk.Button(
            btn_container, 
            text="🔍 KIỂM TRA", 
            command=self.start_check,
            bootstyle="success",
            width=20
        )
        self.check_btn.pack(side=LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            btn_container, 
            text="⏹ DỪNG", 
            command=self.stop_check,
            bootstyle="danger",
            width=15,
            state=DISABLED
        )
        self.stop_btn.pack(side=LEFT, padx=5)
        
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
            height=10,
            bg='#1e1e1e', 
            fg='#00ff88',
            font=('Consolas', 9),
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=BOTH, expand=YES)
        
        # Initial log
        self.log("✅ Khởi tạo thành công. Nhập IP và Port để kiểm tra.")
    
    def log(self, message):
        """Ghi log ra màn hình"""
        timestamp = datetime.now(VIETNAM_TZ).strftime("[%H:%M:%S]")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{timestamp} {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def validate_input(self):
        """Kiểm tra input hợp lệ"""
        ip = self.ip_var.get().strip()
        port_str = self.port_var.get().strip()
        
        if not ip:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập IP đích!")
            return False
        
        if not port_str:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Port!")
            return False
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError()
        except:
            messagebox.showerror("Lỗi", "Port phải là số từ 1-65535!")
            return False
        
        # Validate IP format
        try:
            socket.inet_aton(ip)
        except socket.error:
            messagebox.showerror("Lỗi", "Địa chỉ IP không hợp lệ!")
            return False
        
        return True
    
    def is_vmix_sending_to_port(self, ip, port):
        """
        Kiểm tra xem vMix có đang gửi SRT đến IP:Port này không
        Bằng cách check netstat để xem có kết nối UDP nào đến IP:Port đích
        """
        try:
            # Sử dụng netstat để kiểm tra kết nối UDP
            result = subprocess.run(
                ['netstat', '-ano', '-p', 'udp'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Parse netstat output
            # Tìm các dòng có format: UDP  0.0.0.0:XXXXX  IP:PORT  *:*  PID
            for line in result.stdout.splitlines():
                if 'UDP' not in line:
                    continue
                
                # Check if line contains destination IP:Port
                if f"{ip}:{port}" in line:
                    # Extract PID
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
                                return True, pid, "vMix"
                            else:
                                # Có kết nối nhưng không phải vMix
                                proc_name = proc_result.stdout.split(',')[0].strip('"') if proc_result.stdout else "Unknown"
                                return True, pid, proc_name
                        except:
                            pass
            
            return False, None, None
        
        except Exception as e:
            self.log(f"❌ Lỗi khi kiểm tra: {str(e)}")
            return False, None, None
    
    def check_loop(self):
        """Vòng lặp kiểm tra liên tục"""
        ip = self.ip_var.get().strip()
        port = int(self.port_var.get().strip())
        
        self.log(f"🔍 Bắt đầu kiểm tra: {ip}:{port}")
        self.log(f"ℹ️ Đang quét kết nối UDP...")
        
        check_count = 0
        last_status = None
        
        while self.is_checking:
            check_count += 1
            
            # Kiểm tra kết nối
            is_connected, pid, proc_name = self.is_vmix_sending_to_port(ip, port)
            
            if is_connected:
                if proc_name and 'vmix' in proc_name.lower():
                    status = "🟢 ON (vMix đang gửi SRT)"
                    color = "success"
                    self.log(f"✅ [#{check_count}] vMix đang gửi SRT đến {ip}:{port} (PID: {pid})")
                else:
                    status = f"🟡 ON ({proc_name} đang gửi)"
                    color = "warning"
                    self.log(f"⚠️ [#{check_count}] {proc_name} đang gửi đến {ip}:{port} (PID: {pid})")
            else:
                status = "🔴 OFF (Không có kết nối)"
                color = "danger"
                if check_count % 10 == 0:  # Chỉ log mỗi 10 lần để tránh spam
                    self.log(f"❌ [#{check_count}] Không phát hiện kết nối đến {ip}:{port}")
            
            # Cập nhật UI nếu có thay đổi
            if status != last_status:
                self.root.after(0, lambda s=status, c=color: self.update_status(s, c))
                last_status = status
            
            # Đợi 1 giây trước khi check lại
            import time
            time.sleep(1)
        
        self.log("⏹ Đã dừng kiểm tra.")
        self.root.after(0, lambda: self.status_display.configure(text="● Đã dừng", bootstyle="secondary"))
    
    def update_status(self, status, color):
        """Cập nhật trạng thái hiển thị"""
        self.status_display.configure(text=status, bootstyle=color)
    
    def start_check(self):
        """Bắt đầu kiểm tra"""
        if not self.validate_input():
            return
        
        if self.is_checking:
            messagebox.showinfo("Thông báo", "Đang kiểm tra rồi!")
            return
        
        self.is_checking = True
        self.check_btn.configure(state=DISABLED)
        self.stop_btn.configure(state=NORMAL)
        self.ip_entry.configure(state=DISABLED)
        self.port_entry.configure(state=DISABLED)
        
        # Start check thread
        self.check_thread = threading.Thread(target=self.check_loop, daemon=True)
        self.check_thread.start()
    
    def stop_check(self):
        """Dừng kiểm tra"""
        if not self.is_checking:
            return
        
        self.is_checking = False
        self.check_btn.configure(state=NORMAL)
        self.stop_btn.configure(state=DISABLED)
        self.ip_entry.configure(state=NORMAL)
        self.port_entry.configure(state=NORMAL)


def main():
    root = ttk.Window(
        title="vMix SRT Checker",
        themename="darkly",
        size=(700, 500)
    )
    app = VmixSRTChecker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
