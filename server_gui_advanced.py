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
import socket
import os

# Scapy import - cần chạy với quyền admin để ARP scan
try:
    from scapy.all import ARP, Ether, srp
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("[WARNING] Scapy not installed. Run: pip install scapy")

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
        self.root.title("vMix SRT Checker")
        self.root.geometry("1200x700")

        self.name_var = ctk.StringVar(value="")  # Tên máy
        self.ip_var = ctk.StringVar(value="")  # IP máy vMix
        self.port_var = ctk.StringVar(value="")  # Port đích
        self.webhook_var = ctk.StringVar(value="")  # Discord webhook
        self.subnet_wan_cache = {}  # Cache WAN IP theo subnet (vd: "192.168.100" -> "183.81.127.54")
        self.monitor_list = []  # Danh sách các máy đang monitor
        self.wan_ip = "unknown"  # WAN IP
        self.is_monitoring = False
        self.monitor_thread = None
        
        # MAC-IP tracking
        self.mac_ip_table = {}  # {"MAC": {"ip": "x.x.x.x", "name": "...", "first_seen": "..."}}
        self.ip_ranges = []  # [{"start": "192.168.1.1", "end": "192.168.1.50", "wan_ip": "...", "isp": "..."}]
        self.arp_scan_running = False

        # === NAVBAR ===
        navbar = ctk.CTkFrame(self.root, height=50)
        navbar.pack(fill="x", padx=10, pady=5)
        navbar.pack_propagate(False)
        
        ctk.CTkLabel(navbar, text="📺 vMix SRT Checker", font=("Arial", 16, "bold")).pack(side="left", padx=10)

        # === MAIN CONTAINER ===
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create view
        self.create_monitor_view()
        
        # Auto load config
        self.auto_load_config()
    
    def auto_load_config(self):
        """Tự động load config khi khởi động"""
        try:
            if os.path.exists('ip_config.json'):
                with open('ip_config.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.ip_ranges = data.get('ip_ranges', [])
                self.mac_ip_table = data.get('mac_ip_table', {})
                print(f"[AUTO] Loaded {len(self.ip_ranges)} IP ranges, {len(self.mac_ip_table)} MAC entries")
        except Exception as e:
            print(f"[AUTO] Failed to load config: {e}")
    
    def switch_view(self, view_name):
        """Chuyển đổi giữa các view"""
        self.current_view = view_name
        
        # Hide all views
        self.monitor_frame.pack_forget()
        self.ping_frame.pack_forget()
        
        # Update button styles
        if view_name == "monitor":
            self.btn_monitor.configure(fg_color="#4CAF50")
            self.btn_ping.configure(fg_color="#2b2b2b")
            self.monitor_frame.pack(fill="both", expand=True)
        elif view_name == "ping":
            self.btn_monitor.configure(fg_color="#2b2b2b")
            self.btn_ping.configure(fg_color="#4CAF50")
            self.ping_frame.pack(fill="both", expand=True)
            self.refresh_ping_chart()
    
    def create_monitor_view(self):
        """Tạo view Monitor với input IP + Port"""
        frame = ctk.CTkFrame(self.main_container)
        frame.pack(fill="both", expand=True)
        
        # === INPUT SECTION ===
        input_frame = ctk.CTkFrame(frame)
        input_frame.pack(fill="x", padx=10, pady=10)
        
        # Row 1: Tên + IP + Port + Thêm
        row1 = ctk.CTkFrame(input_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row1, text="Tên:", font=("Arial", 12, "bold"), width=40).pack(side="left", padx=5)
        self.name_entry = ctk.CTkEntry(row1, textvariable=self.name_var, width=120, font=("Arial", 12), placeholder_text="CAM LIA")
        self.name_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="IP:", font=("Arial", 12, "bold"), width=30).pack(side="left", padx=5)
        self.ip_entry = ctk.CTkEntry(row1, textvariable=self.ip_var, width=140, font=("Arial", 12), placeholder_text="192.168.100.10")
        self.ip_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Port:", font=("Arial", 12, "bold"), width=40).pack(side="left", padx=5)
        self.port_entry = ctk.CTkEntry(row1, textvariable=self.port_var, width=80, font=("Arial", 12), placeholder_text="11011")
        self.port_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(row1, text="➕ Thêm", command=self.add_to_monitor, 
                     fg_color="#2196F3", hover_color="#1976D2", width=80, 
                     font=("Arial", 12, "bold")).pack(side="left", padx=10)
        
        self.start_btn = ctk.CTkButton(row1, text="▶️ BẮT ĐẦU", command=self.toggle_monitoring, 
                                       fg_color="#4CAF50", hover_color="#45a049", width=120, 
                                       font=("Arial", 12, "bold"))
        self.start_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(row1, text="🗑️ Clear", command=self.clear_monitor_list, 
                     fg_color="#f44336", hover_color="#d32f2f", width=70).pack(side="left", padx=3)
        
        ctk.CTkButton(row1, text="💾 Save", command=self.save_monitor_list, 
                     fg_color="#607D8B", hover_color="#455A64", width=70).pack(side="left", padx=3)
        
        ctk.CTkButton(row1, text="📂 Open", command=self.load_monitor_list, 
                     fg_color="#795548", hover_color="#5D4037", width=70).pack(side="left", padx=3)
        
        self.scan_status = ctk.CTkLabel(row1, text="", font=("Arial", 11), text_color="#FFC107")
        self.scan_status.pack(side="left", padx=5)
        
        # Row 2: Discord Webhook + Cấu hình IP
        row2 = ctk.CTkFrame(input_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row2, text="📢 Webhook:", font=("Arial", 12, "bold"), width=90).pack(side="left", padx=5)
        self.webhook_entry = ctk.CTkEntry(row2, textvariable=self.webhook_var, width=600, font=("Arial", 11), 
                                         placeholder_text="https://discord.com/api/webhooks/...")
        self.webhook_entry.pack(side="left", padx=5)
        
        # Nút cấu hình IP Range
        ctk.CTkButton(row2, text="⚙️ Cấu hình IP", command=self.open_ip_config_dialog, 
                     fg_color="#FF9800", hover_color="#F57C00", width=120).pack(side="left", padx=10)

        # === MONITOR LIST ===
        main_frame = ctk.CTkFrame(frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Monitor panel
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(right_frame, text="📊 MONITOR LIST", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Monitor table
        self.table_frame = ctk.CTkScrollableFrame(right_frame, fg_color="#2b2b2b")
        self.table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="#1a1a1a", height=40)
        header_frame.pack(fill="x", pady=(0, 5))
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(header_frame, text="STT", font=("Arial", 12, "bold"), width=40).pack(side="left", padx=3)
        ctk.CTkLabel(header_frame, text="TÊN", font=("Arial", 12, "bold"), width=100).pack(side="left", padx=3)
        ctk.CTkLabel(header_frame, text="IP VMIX", font=("Arial", 12, "bold"), width=130).pack(side="left", padx=3)
        ctk.CTkLabel(header_frame, text="IPWAN", font=("Arial", 12, "bold"), width=130).pack(side="left", padx=3)
        ctk.CTkLabel(header_frame, text="ISP", font=("Arial", 12, "bold"), width=80).pack(side="left", padx=3)
        ctk.CTkLabel(header_frame, text="PORT", font=("Arial", 12, "bold"), width=60).pack(side="left", padx=3)
        ctk.CTkLabel(header_frame, text="STATUS", font=("Arial", 12, "bold"), width=100).pack(side="left", padx=3)
        ctk.CTkLabel(header_frame, text="OUTPUT", font=("Arial", 12, "bold"), width=100).pack(side="left", padx=3)
        ctk.CTkLabel(header_frame, text="TIME", font=("Arial", 12, "bold"), width=70).pack(side="left", padx=3)
        ctk.CTkLabel(header_frame, text="", font=("Arial", 12, "bold"), width=35).pack(side="left", padx=3)
        
        self.table_rows = []
    
    def refresh_wan_ip(self):
        """Lấy WAN IP từ API bên ngoài"""
        def get_ip():
            urls = ['https://api.ipify.org', 'https://ifconfig.me/ip', 'https://ipinfo.io/ip', 'https://checkip.amazonaws.com']
            for url in urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        ip = response.text.strip()
                        self.wan_ip = ip
                        print(f"[WAN] Got WAN IP: {ip}")
                        return
                except:
                    continue
            self.wan_ip = "unknown"
            print("[WAN] Could not get WAN IP")
        
        threading.Thread(target=get_ip, daemon=True).start()
    
    def open_ip_config_dialog(self):
        """Mở dialog cấu hình dải IP và IPWAN"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("⚙️ Cấu hình dải IP - IPWAN")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        ctk.CTkLabel(dialog, text="Cấu hình dải IP theo nhà mạng", 
                    font=("Arial", 16, "bold")).pack(pady=10)
        
        # Input frame
        input_frame = ctk.CTkFrame(dialog)
        input_frame.pack(fill="x", padx=20, pady=10)
        
        # Row inputs
        row1 = ctk.CTkFrame(input_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row1, text="IP Bắt đầu:", width=80).pack(side="left", padx=5)
        self.range_start_var = ctk.StringVar(value="")
        ctk.CTkEntry(row1, textvariable=self.range_start_var, width=130, 
                    placeholder_text="192.168.1.1").pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="IP Kết thúc:", width=80).pack(side="left", padx=5)
        self.range_end_var = ctk.StringVar(value="")
        ctk.CTkEntry(row1, textvariable=self.range_end_var, width=130, 
                    placeholder_text="192.168.1.50").pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(input_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row2, text="IPWAN:", width=80).pack(side="left", padx=5)
        self.range_wan_var = ctk.StringVar(value="")
        ctk.CTkEntry(row2, textvariable=self.range_wan_var, width=130, 
                    placeholder_text="113.161.x.x").pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="Nhà mạng:", width=80).pack(side="left", padx=5)
        self.range_isp_var = ctk.StringVar(value="")
        ctk.CTkEntry(row2, textvariable=self.range_isp_var, width=130, 
                    placeholder_text="VNPT/Viettel/FPT").pack(side="left", padx=5)
        
        ctk.CTkButton(row2, text="➕ Thêm", command=lambda: self.add_ip_range(dialog), 
                     fg_color="#4CAF50", width=80).pack(side="left", padx=10)
        
        # List frame
        list_frame = ctk.CTkFrame(dialog)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(list_frame, text="Danh sách dải IP đã cấu hình:", 
                    font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # Table header
        header = ctk.CTkFrame(list_frame, fg_color="#1a1a1a", height=35)
        header.pack(fill="x", pady=(0, 5))
        header.pack_propagate(False)
        
        ctk.CTkLabel(header, text="STT", width=40, font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="IP Bắt đầu", width=120, font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="IP Kết thúc", width=120, font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="IPWAN", width=120, font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Nhà mạng", width=100, font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="", width=50).pack(side="left", padx=5)
        
        # Scrollable list
        self.ip_range_list_frame = ctk.CTkScrollableFrame(list_frame, fg_color="#2b2b2b")
        self.ip_range_list_frame.pack(fill="both", expand=True, pady=5)
        
        # Load existing ranges
        self.refresh_ip_range_list()
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(btn_frame, text="💾 Lưu cấu hình", command=self.save_ip_ranges_to_file, 
                     fg_color="#2196F3", width=120).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📂 Load cấu hình", command=self.load_ip_ranges_from_file, 
                     fg_color="#9C27B0", width=120).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Đóng", command=dialog.destroy, 
                     fg_color="#666", width=80).pack(side="right", padx=5)
    
    def add_ip_range(self, dialog=None):
        """Thêm dải IP vào danh sách"""
        start = self.range_start_var.get().strip()
        end = self.range_end_var.get().strip()
        wan = self.range_wan_var.get().strip()
        isp = self.range_isp_var.get().strip()
        
        if not start or not end:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập IP bắt đầu và kết thúc!")
            return
        
        # Validate IP format
        for ip in [start, end]:
            parts = ip.split('.')
            if len(parts) != 4:
                messagebox.showerror("Lỗi", f"IP không hợp lệ: {ip}")
                return
            try:
                for p in parts:
                    if not (0 <= int(p) <= 255):
                        raise ValueError()
            except:
                messagebox.showerror("Lỗi", f"IP không hợp lệ: {ip}")
                return
        
        # Add to list
        self.ip_ranges.append({
            'start': start,
            'end': end,
            'wan_ip': wan,
            'isp': isp
        })
        
        # Clear inputs
        self.range_start_var.set("")
        self.range_end_var.set("")
        self.range_wan_var.set("")
        self.range_isp_var.set("")
        
        # Refresh list
        self.refresh_ip_range_list()
        print(f"[CONFIG] Added IP range: {start} - {end} -> WAN: {wan} ({isp})")
    
    def remove_ip_range(self, idx):
        """Xóa dải IP khỏi danh sách"""
        if 0 <= idx < len(self.ip_ranges):
            removed = self.ip_ranges.pop(idx)
            print(f"[CONFIG] Removed IP range: {removed['start']} - {removed['end']}")
            self.refresh_ip_range_list()
    
    def refresh_ip_range_list(self):
        """Cập nhật danh sách dải IP trong dialog"""
        if not hasattr(self, 'ip_range_list_frame'):
            return
        
        # Clear old items
        for widget in self.ip_range_list_frame.winfo_children():
            widget.destroy()
        
        # Add items
        for idx, item in enumerate(self.ip_ranges):
            row = ctk.CTkFrame(self.ip_range_list_frame, 
                              fg_color="#3a3a3a" if idx % 2 == 0 else "#2b2b2b", 
                              height=35)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            
            ctk.CTkLabel(row, text=str(idx + 1), width=40).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=item['start'], width=120).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=item['end'], width=120).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=item.get('wan_ip', ''), width=120, text_color="#FFC107").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=item.get('isp', ''), width=100, text_color="#4CAF50").pack(side="left", padx=5)
            
            ctk.CTkButton(row, text="X", width=30, height=25, 
                         fg_color="#f44336", hover_color="#d32f2f",
                         command=lambda i=idx: self.remove_ip_range(i)).pack(side="right", padx=5)
    
    def save_ip_ranges_to_file(self):
        """Lưu cấu hình IP ranges ra file JSON"""
        try:
            data = {
                'ip_ranges': self.ip_ranges,
                'mac_ip_table': self.mac_ip_table
            }
            with open('ip_config.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Thành công", "Đã lưu cấu hình vào ip_config.json")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")
    
    def load_ip_ranges_from_file(self):
        """Load cấu hình IP ranges từ file JSON"""
        try:
            if os.path.exists('ip_config.json'):
                with open('ip_config.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.ip_ranges = data.get('ip_ranges', [])
                self.mac_ip_table = data.get('mac_ip_table', {})
                self.refresh_ip_range_list()
                messagebox.showinfo("Thành công", f"Đã load {len(self.ip_ranges)} dải IP và {len(self.mac_ip_table)} MAC")
            else:
                messagebox.showwarning("Cảnh báo", "Chưa có file ip_config.json")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể load file: {e}")
    
    def get_wan_for_ip(self, ip):
        """Tìm IPWAN tương ứng với IP dựa trên cấu hình dải"""
        def ip_to_int(ip_str):
            parts = ip_str.split('.')
            return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
        
        try:
            ip_int = ip_to_int(ip)
            for range_item in self.ip_ranges:
                start_int = ip_to_int(range_item['start'])
                end_int = ip_to_int(range_item['end'])
                if start_int <= ip_int <= end_int:
                    return range_item.get('wan_ip', ''), range_item.get('isp', '')
        except:
            pass
        return '', ''
    
    def start_arp_scan(self):
        """Bắt đầu quét ARP để tìm MAC-IP"""
        if not SCAPY_AVAILABLE:
            messagebox.showerror("Lỗi", "Scapy chưa được cài đặt!\nChạy: pip install scapy")
            return
        
        if self.arp_scan_running:
            messagebox.showwarning("Cảnh báo", "Đang quét, vui lòng đợi...")
            return
        
        if not self.ip_ranges:
            messagebox.showwarning("Cảnh báo", "Chưa cấu hình dải IP!\nVui lòng vào 'Cấu hình IP' để thêm dải IP cần quét.")
            return
        
        self.arp_scan_running = True
        self.scan_status.configure(text="🔍 Đang quét ARP...", text_color="#00BCD4")
        
        def do_scan():
            try:
                total_found = 0
                changes = []
                
                for range_item in self.ip_ranges:
                    start_ip = range_item['start']
                    end_ip = range_item['end']
                    wan_ip = range_item.get('wan_ip', '')
                    isp = range_item.get('isp', '')
                    
                    # Tạo CIDR từ range (đơn giản hóa - quét từng IP)
                    results = self.arp_scan_range(start_ip, end_ip)
                    
                    for mac, ip in results:
                        total_found += 1
                        
                        # Check nếu MAC đã có trong bảng
                        if mac in self.mac_ip_table:
                            old_ip = self.mac_ip_table[mac]['ip']
                            if old_ip != ip:
                                # IP đã thay đổi! Cảnh báo
                                old_wan, old_isp = self.get_wan_for_ip(old_ip)
                                new_wan, new_isp = self.get_wan_for_ip(ip)
                                
                                change_msg = f"⚠️ [IP CHANGE] MAC {mac}\n"
                                change_msg += f"   IP cũ: {old_ip} (WAN: {old_wan}, ISP: {old_isp})\n"
                                change_msg += f"   IP mới: {ip} (WAN: {new_wan}, ISP: {new_isp})"
                                changes.append(change_msg)
                                print(change_msg)
                                
                                # Update IP mới
                                self.mac_ip_table[mac]['ip'] = ip
                                self.mac_ip_table[mac]['last_change'] = datetime.now(VIETNAM_TZ).isoformat()
                        else:
                            # MAC mới, thêm vào bảng
                            self.mac_ip_table[mac] = {
                                'ip': ip,
                                'wan_ip': wan_ip,
                                'isp': isp,
                                'first_seen': datetime.now(VIETNAM_TZ).isoformat(),
                                'last_change': None
                            }
                            print(f"[NEW] MAC {mac} -> IP {ip} (WAN: {wan_ip})")
                
                # Gửi thông báo nếu có thay đổi
                if changes:
                    full_msg = "\n".join(changes)
                    self.send_discord_webhook(full_msg)
                    self.root.after(0, lambda: messagebox.showwarning("Cảnh báo IP thay đổi", full_msg))
                
                self.root.after(0, lambda: self.scan_status.configure(
                    text=f"✅ Quét xong: {total_found} thiết bị", text_color="#4CAF50"))
                
            except Exception as e:
                print(f"[ERROR] ARP Scan failed: {e}")
                self.root.after(0, lambda: self.scan_status.configure(
                    text=f"❌ Lỗi: {str(e)[:30]}", text_color="#f44336"))
            finally:
                self.arp_scan_running = False
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def arp_scan_range(self, start_ip, end_ip):
        """Quét ARP trong dải IP từ start đến end"""
        results = []
        
        def ip_to_int(ip_str):
            parts = ip_str.split('.')
            return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
        
        def int_to_ip(ip_int):
            return f"{(ip_int >> 24) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 8) & 0xFF}.{ip_int & 0xFF}"
        
        try:
            start_int = ip_to_int(start_ip)
            end_int = ip_to_int(end_ip)
            
            # Giới hạn tối đa 256 IP mỗi lần quét
            if end_int - start_int > 255:
                end_int = start_int + 255
            
            # Tạo danh sách IP cần quét
            ip_list = [int_to_ip(i) for i in range(start_int, end_int + 1)]
            
            # Quét theo batch để tránh quá tải
            batch_size = 50
            for i in range(0, len(ip_list), batch_size):
                batch = ip_list[i:i + batch_size]
                
                for target_ip in batch:
                    try:
                        # Tạo ARP request
                        arp = ARP(pdst=target_ip)
                        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
                        packet = ether / arp
                        
                        # Gửi và nhận response
                        answered, _ = srp(packet, timeout=0.5, verbose=False)
                        
                        for sent, received in answered:
                            mac = received.hwsrc
                            ip = received.psrc
                            results.append((mac.upper(), ip))
                            print(f"[ARP] Found: {mac} -> {ip}")
                    except Exception as e:
                        print(f"[ARP] Error scanning {target_ip}: {e}")
                        continue
                        
        except Exception as e:
            print(f"[ARP] Range scan error: {e}")
        
        return results

    def send_discord_webhook(self, message):
        """Gửi thông báo đến Discord webhook"""
        webhook_url = self.webhook_var.get().strip()
        if not webhook_url:
            return
        
        try:
            payload = {"content": message}
            response = requests.post(webhook_url, json=payload, timeout=5)
            if response.status_code in [200, 204]:
                print(f"Webhook sent: {message}")
            else:
                print(f"Webhook error: HTTP {response.status_code}")
        except Exception as e:
            print(f"Webhook exception: {e}")
    
    def scan_subnet_click(self):
        """Xử lý khi nhấn nút Scan Subnet"""
        subnet = self.subnet_var.get().strip()
        port_str = self.port_var.get().strip()
        
        if not port_str:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Port!")
            return
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError()
        except:
            messagebox.showerror("Lỗi", "Port phải là số từ 1-65535!")
            return
        
        # Nếu không nhập subnet, lấy từ IP máy hiện tại
        if not subnet:
            import socket as sock
            try:
                local_ip = sock.gethostbyname(sock.gethostname())
                subnet = '.'.join(local_ip.split('.')[:3])
                self.subnet_var.set(subnet)
            except:
                subnet = "192.168.1"
                self.subnet_var.set(subnet)
        
        # Disable nút và bắt đầu scan
        self.scan_btn.configure(state="disabled", text="Đang scan...")
        self.scan_status.configure(text=f"Scanning {subnet}.1-254...")
        self.root.update()
        
        def do_scan():
            found = self.scan_subnet_for_port(port, subnet)
            self.root.after(0, lambda: self.on_scan_complete(found, port))
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def scan_subnet_for_port(self, port, subnet=None):
        """Scan subnet để tìm IP nào đang listen SRT trên port cụ thể"""
        import socket as sock
        import concurrent.futures
        import subprocess
        
        # Lấy subnet
        if not subnet:
            try:
                local_ip = sock.gethostbyname(sock.gethostname())
                subnet = '.'.join(local_ip.split('.')[:3])
            except:
                subnet = "192.168.1"
        
        found_ips = []
        local_ip = self.get_local_ip()
        local_subnet = '.'.join(local_ip.split('.')[:3])
        
        # CÁCH 1: Nếu đây là LOCAL subnet, check netstat trước
        if subnet == local_subnet:
            try:
                result = subprocess.run(
                    ['netstat', '-an'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                for line in result.stdout.splitlines():
                    if 'UDP' in line and f':{port}' in line:
                        if '0.0.0.0:' in line or f'{local_ip}:' in line:
                            print(f"[SCAN] LOCAL netstat: Port {port} is LISTENING on {local_ip}")
                            return [local_ip]  # Trả về IP local ngay
            except Exception as e:
                print(f"Netstat scan error: {str(e)[:50]}")
        
        # CÁCH 2: Scan tìm máy có vMix API đang chạy
        def check_vmix_ip(ip):
            """Check xem IP này có vMix đang chạy không"""
            try:
                # Check vMix API port 8088
                tcp_sock = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
                tcp_sock.settimeout(0.5)
                result = tcp_sock.connect_ex((ip, 8088))
                tcp_sock.close()
                
                if result == 0:
                    # vMix API đang chạy, check xem có SRT không
                    try:
                        response = requests.get(f"http://{ip}:8088/api", timeout=0.8)
                        if response.status_code == 200 and 'srt="True"' in response.text.lower():
                            return ip
                    except:
                        pass
            except:
                pass
            return None
        
        # Scan song song tìm vMix
        print(f"[SCAN] Scanning {subnet}.1-254 for vMix with SRT on port {port}...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(check_vmix_ip, f"{subnet}.{i}"): i for i in range(1, 255)}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    found_ips.append(result)
                    print(f"[SCAN] Found vMix with SRT at: {result}")
        
        return found_ips
    
    def add_to_monitor(self):
        """Thêm máy vào danh sách monitor (Tên + IP + Port)"""
        name = self.name_var.get().strip()
        ip = self.ip_var.get().strip()
        port_str = self.port_var.get().strip()
        
        # Validate
        if not ip:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập IP! (ví dụ: 192.168.100.10)")
            return
        
        # Validate IP format
        parts = ip.split('.')
        if len(parts) != 4:
            messagebox.showerror("Lỗi", "IP không hợp lệ! Định dạng: x.x.x.x")
            return
        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    raise ValueError()
        except:
            messagebox.showerror("Lỗi", "IP không hợp lệ! Mỗi phần phải là số từ 0-255")
            return
        
        if not port_str:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Port!")
            return
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError()
        except:
            messagebox.showerror("Lỗi", "Port phải là số từ 1-65535!")
            return
        
        if not name:
            name = f"Máy {ip}:{port}"
        
        # Check duplicate
        for item in self.monitor_list:
            if item['ip'] == ip and item['port'] == port:
                messagebox.showwarning("Cảnh báo", f"IP:Port {ip}:{port} đã có trong danh sách!")
                return
        
        # Lấy IPWAN và ISP từ cấu hình dải IP
        wan_ip, isp = self.get_wan_for_ip(ip)
        
        # Add to list
        subnet = '.'.join(ip.split('.')[:3])  # Lấy subnet từ IP
        self.monitor_list.append({
            'name': name,
            'subnet': subnet,
            'ip': ip,
            'port': port,
            'wan_ip': wan_ip,  # Lấy từ cấu hình
            'isp': isp,  # Lấy từ cấu hình
            'mac': '',
            'status': '⏳ Chờ kiểm tra',
            'outputs': '',
            'last_check': '',
            'prev_status': None
        })
        
        # Clear input
        self.name_var.set("")
        self.ip_var.set("")
        
        # Update table
        self.update_table()
    
    def on_scan_complete(self, found_ips, port):
        """Callback khi scan subnet hoàn tất"""
        self.scan_btn.configure(state="normal", text="🔎 Scan Subnet")
        self.scan_status.configure(text="")
        
        if not found_ips:
            messagebox.showinfo("Kết quả Scan", f"Không tìm thấy máy nào có vMix đang chạy trên subnet này")
            return
        
        # Thêm tất cả IP tìm được vào danh sách
        added = 0
        for ip in found_ips:
            # Check duplicate
            exists = False
            for item in self.monitor_list:
                if item['ip'] == ip and item['port'] == port:
                    exists = True
                    break
            
            if not exists:
                self.monitor_list.append({
                    'name': f"Máy {ip}",
                    'ip': ip,
                    'port': port,
                    'wan_ip': '',
                    'status': 'Chưa kiểm tra',
                    'outputs': '',
                    'last_check': '',
                    'prev_status': None
                })
                added += 1
        
        self.update_table()
        messagebox.showinfo("Kết quả Scan", f"Tìm thấy {len(found_ips)} máy, đã thêm {added} máy mới vào danh sách")
    
    def clear_monitor_list(self):
        """Xóa toàn bộ danh sách"""
        if not self.monitor_list:
            return
        
        result = messagebox.askyesno("Xác nhận", f"Xóa {len(self.monitor_list)} mục trong danh sách?")
        if result:
            self.monitor_list = []
            self.update_table()
    
    def save_monitor_list(self):
        """Lưu danh sách monitor ra file JSON"""
        if not self.monitor_list:
            messagebox.showwarning("Cảnh báo", "Danh sách monitor đang trống!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Lưu danh sách monitor",
            initialfile="monitor_list.json"
        )
        
        if file_path:
            try:
                # Chuẩn bị data để lưu
                save_data = {
                    'monitor_list': self.monitor_list,
                    'webhook': self.webhook_var.get(),
                    'ip_ranges': self.ip_ranges,
                    'saved_at': datetime.now(VIETNAM_TZ).isoformat()
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Thành công", f"Đã lưu {len(self.monitor_list)} máy vào file!")
                print(f"[SAVE] Saved {len(self.monitor_list)} items to {file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")
    
    def load_monitor_list(self):
        """Load danh sách monitor từ file JSON"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Mở danh sách monitor"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load monitor list
                loaded_list = data.get('monitor_list', [])
                if loaded_list:
                    # Hỏi có muốn thay thế hay thêm vào
                    if self.monitor_list:
                        result = messagebox.askyesnocancel(
                            "Chọn hành động",
                            f"Đã có {len(self.monitor_list)} máy trong danh sách.\n\n"
                            f"Yes = Thay thế toàn bộ\n"
                            f"No = Thêm vào danh sách hiện tại\n"
                            f"Cancel = Hủy"
                        )
                        if result is None:  # Cancel
                            return
                        elif result:  # Yes - Replace
                            self.monitor_list = loaded_list
                        else:  # No - Append
                            self.monitor_list.extend(loaded_list)
                    else:
                        self.monitor_list = loaded_list
                
                # Load webhook nếu có
                webhook = data.get('webhook', '')
                if webhook:
                    self.webhook_var.set(webhook)
                
                # Load IP ranges nếu có
                ip_ranges = data.get('ip_ranges', [])
                if ip_ranges:
                    self.ip_ranges = ip_ranges
                
                self.update_table()
                messagebox.showinfo("Thành công", f"Đã load {len(loaded_list)} máy từ file!")
                print(f"[LOAD] Loaded {len(loaded_list)} items from {file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")
    
    def remove_item(self, idx):
        """Xóa 1 item khỏi danh sách"""
        if idx < len(self.monitor_list):
            self.monitor_list.pop(idx)
            self.update_table()
    
    def toggle_monitoring(self):
        """Bật/tắt monitoring"""
        if not self.is_monitoring:
            if not self.monitor_list:
                messagebox.showwarning("Cảnh báo", "Vui lòng thêm ít nhất 1 mục!")
                return
            
            self.is_monitoring = True
            self.start_btn.configure(text="⏹️ DỪNG", fg_color="#f44336")
            self.name_entry.configure(state="disabled")
            self.ip_entry.configure(state="disabled")
            self.port_entry.configure(state="disabled")
            self.scan_status.configure(text="Đang theo dõi...")
            
            # Lấy WAN IP của máy chạy tool (dùng làm baseline)
            self.refresh_wan_ip()
            
            # Clear cache
            self.subnet_wan_cache = {}
            
            # Start monitor thread (sẽ scan IP trong loop đầu tiên)
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_monitoring = False
            self.start_btn.configure(text="▶️ BẮT ĐẦU", fg_color="#4CAF50")
            self.name_entry.configure(state="normal")
            self.ip_entry.configure(state="normal")
            self.port_entry.configure(state="normal")
            self.scan_status.configure(text="")
    
    def get_machine_wan_ip(self, vmix_ip):
        """Lấy WAN IP của máy vMix dựa trên subnet"""
        # Nếu IP không hợp lệ, không lấy WAN
        if vmix_ip in ['Không tìm thấy', '(Chưa scan)', '']:
            return ''
        
        # Lấy subnet (3 octet đầu) từ IP
        parts = vmix_ip.split('.')
        if len(parts) >= 3:
            subnet = '.'.join(parts[:3])  # vd: "192.168.100"
            
            # Kiểm tra cache
            if subnet in self.subnet_wan_cache:
                return self.subnet_wan_cache[subnet]
            
            # Nếu chưa có, thử lấy WAN IP từ máy này
            wan = self.fetch_wan_ip_from_machine(vmix_ip)
            if wan:
                self.subnet_wan_cache[subnet] = wan
                print(f"[WAN] Subnet {subnet}.* -> WAN: {wan}")
                return wan
        
        # Không fallback - chỉ trả về rỗng nếu không tìm được
        return ''
    
    def fetch_wan_ip_from_machine(self, vmix_ip):
        """Thử lấy WAN IP thông qua vMix API hoặc các cách khác"""
        # Chỉ lấy WAN nếu cùng subnet với máy chạy tool
        try:
            import socket as sock
            local_ip = sock.gethostbyname(sock.gethostname())
            local_subnet = '.'.join(local_ip.split('.')[:3])
            remote_subnet = '.'.join(vmix_ip.split('.')[:3])
            
            if local_subnet == remote_subnet:
                # Cùng subnet -> cùng WAN IP
                if self.wan_ip and self.wan_ip != "unknown":
                    return self.wan_ip
        except:
            pass
        
        # Khác subnet -> không thể lấy WAN IP (cần API riêng từ máy đó)
        return ''
    
    def send_initial_snapshot(self):
        """Gửi snapshot ban đầu của tất cả máy"""
        time.sleep(1)  # Đợi 1 giây để có dữ liệu
        messages = []
        for item in self.monitor_list:
            name = item['name']
            ip = item['ip']
            port = item['port']
            status = item['status']
            
            # Xác định ON/OFF
            if "🟢" in status:
                status_text = "ON"
            elif "🔴" in status:
                status_text = "OFF"
            else:
                status_text = "UNKNOWN"
            
            msg = f"[SRT][{name}] SRT {status_text} | IPWAN: {self.wan_ip} | VMIX: {ip}:{port}"
            messages.append(msg)
        
        if messages:
            full_message = "\n".join(messages)
            self.send_discord_webhook(full_message)
    
    def get_mac_for_ip(self, ip):
        """Lấy MAC address của IP bằng ARP"""
        if not ip or ip in ['(Chưa scan)', 'Không tìm thấy', '']:
            return ''
        
        # Cách 1: Dùng scapy nếu có
        if SCAPY_AVAILABLE:
            try:
                arp = ARP(pdst=ip)
                ether = Ether(dst="ff:ff:ff:ff:ff:ff")
                packet = ether / arp
                answered, _ = srp(packet, timeout=1, verbose=False)
                
                for sent, received in answered:
                    mac = received.hwsrc.upper()
                    print(f"[MAC] {ip} -> {mac}")
                    return mac
            except Exception as e:
                print(f"[MAC] Scapy error for {ip}: {e}")
        
        # Cách 2: Dùng ARP cache của Windows
        try:
            import subprocess
            # Ping trước để đảm bảo có trong ARP cache
            subprocess.run(['ping', '-n', '1', '-w', '500', ip], 
                          capture_output=True, 
                          creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            # Đọc ARP cache
            result = subprocess.run(['arp', '-a', ip], 
                                   capture_output=True, text=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            for line in result.stdout.splitlines():
                if ip in line:
                    parts = line.split()
                    for part in parts:
                        # MAC format: xx-xx-xx-xx-xx-xx hoặc xx:xx:xx:xx:xx:xx
                        if '-' in part and len(part) == 17:
                            mac = part.upper().replace('-', ':')
                            print(f"[MAC] {ip} -> {mac} (from arp cache)")
                            return mac
        except Exception as e:
            print(f"[MAC] ARP cache error for {ip}: {e}")
        
        return ''
    
    def check_srt_connection(self, vmix_ip, dest_port):
        """Kiểm tra máy vMix có đang bật SRT trên port cụ thể không"""
        import socket as sock
        import subprocess
        
        dest_port = int(dest_port)
        
        # Lấy IP local của máy này
        local_ip = self.get_local_ip()
        is_local = (vmix_ip == local_ip or vmix_ip == "127.0.0.1")
        
        # CÁCH 1: Nếu là máy LOCAL - dùng netstat để check chính xác port
        if is_local:
            try:
                result = subprocess.run(
                    ['netstat', '-an'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                # Tìm UDP port đang listen
                for line in result.stdout.splitlines():
                    if 'UDP' in line and f':{dest_port}' in line:
                        if '0.0.0.0:' in line or f'{vmix_ip}:' in line or '*:*' in line:
                            print(f"[OK] LOCAL: Port {dest_port} is LISTENING")
                            return True, "🟢 SRT ON", f"Port {dest_port}", None
                
                print(f"[X] LOCAL: Port {dest_port} NOT listening")
                return False, "🔴 SRT OFF", "", None
                
            except Exception as e:
                print(f"Netstat error: {str(e)[:50]}")
                return False, "🔴 SRT OFF", "", None
        
        # CÁCH 2: Máy REMOTE - gửi SRT handshake packet qua UDP để check port
        try:
            import struct
            import random
            
            # Tạo SRT Handshake Induction Packet (RFC compliant)
            header = 0x80000000  # Control bit + Type 0 (Handshake)
            additional_info = 0x00000001  # Handshake type: Induction
            timestamp = 0
            dst_socket_id = 0
            version = 4  # UDT version
            socket_type = 1  # STREAM
            initial_seq = random.randint(0, 0x7FFFFFFF)
            max_pkt_size = 1500
            max_flow_window = 8192
            handshake_type = 1  # Induction
            socket_id = random.randint(1, 0x7FFFFFFF)
            syn_cookie = 0
            peer_ip = b'\x00' * 16  # IPv4 in IPv6 format
            
            packet = struct.pack('>I', header)
            packet += struct.pack('>I', additional_info)
            packet += struct.pack('>I', timestamp)
            packet += struct.pack('>I', dst_socket_id)
            packet += struct.pack('>I', version)
            packet += struct.pack('>I', socket_type)
            packet += struct.pack('>I', initial_seq)
            packet += struct.pack('>I', max_pkt_size)
            packet += struct.pack('>I', max_flow_window)
            packet += struct.pack('>i', handshake_type)
            packet += struct.pack('>I', socket_id)
            packet += struct.pack('>I', syn_cookie)
            packet += peer_ip
            
            udp_sock = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
            udp_sock.settimeout(2)
            udp_sock.sendto(packet, (vmix_ip, dest_port))
            
            try:
                data, addr = udp_sock.recvfrom(2048)
                udp_sock.close()
                
                # Nếu nhận được response → SRT đang listen
                if addr[0] == vmix_ip and len(data) > 0:
                    print(f"[OK] REMOTE: SRT Port {dest_port} ACTIVE at {vmix_ip} (got {len(data)} bytes)")
                    return True, "🟢 SRT ON", f"Port {dest_port}", None
                    
            except sock.timeout:
                udp_sock.close()
                print(f"[X] REMOTE: SRT Port {dest_port} no response at {vmix_ip}")
                return False, "🔴 SRT OFF", "", None
                
        except Exception as e:
            print(f"[X] REMOTE: SRT check error {vmix_ip}:{dest_port} - {str(e)[:30]}")
        
        return False, "🔴 SRT OFF", "", None
    
    def get_local_ip(self):
        """Lấy IP local của máy này"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def monitor_loop(self):
        """Vòng lặp kiểm tra liên tục"""
        first_run = True
        
        while self.is_monitoring:
            changes = []
            
            if first_run:
                self.root.after(0, lambda: self.scan_status.configure(
                    text="Đang kiểm tra...", text_color="#FFC107"))
                first_run = False
            
            self.root.after(0, lambda: self.scan_status.configure(text="Đang theo dõi...", text_color="#4CAF50"))
            
            for item in self.monitor_list:
                vmix_ip = item['ip']
                dest_port = item['port']
                name = item['name']
                
                # Bỏ qua nếu không tìm thấy IP
                if vmix_ip == 'Không tìm thấy' or vmix_ip == '(Chưa scan)':
                    continue
                
                # Lấy MAC address nếu chưa có
                if not item.get('mac'):
                    mac = self.get_mac_for_ip(vmix_ip)
                    if mac:
                        item['mac'] = mac
                        # Lưu vào MAC-IP table với IP ban đầu
                        if mac not in self.mac_ip_table:
                            self.mac_ip_table[mac] = {
                                'ip': vmix_ip,
                                'name': name,
                                'first_seen': datetime.now(VIETNAM_TZ).isoformat()
                            }
                            print(f"[MAC] Saved: {mac} -> {vmix_ip} ({name})")
                else:
                    # Đã có MAC, check xem IP có thay đổi không
                    mac = item['mac']
                    if mac in self.mac_ip_table:
                        old_ip = self.mac_ip_table[mac].get('ip', '')
                        if old_ip and old_ip != vmix_ip:
                            # IP ĐÃ THAY ĐỔI!
                            old_wan, old_isp = self.get_wan_for_ip(old_ip)
                            new_wan, new_isp = self.get_wan_for_ip(vmix_ip)
                            
                            change_msg = f"⚠️ [IP CHANGE] {name}\n"
                            change_msg += f"   MAC: {mac}\n"
                            change_msg += f"   IP cũ: {old_ip} (WAN: {old_wan}, ISP: {old_isp})\n"
                            change_msg += f"   IP mới: {vmix_ip} (WAN: {new_wan}, ISP: {new_isp})"
                            changes.append(change_msg)
                            print(f"[!] IP CHANGED: {name} - {mac}: {old_ip} -> {vmix_ip}")
                            
                            # Update MAC table với IP mới
                            self.mac_ip_table[mac]['ip'] = vmix_ip
                            self.mac_ip_table[mac]['last_change'] = datetime.now(VIETNAM_TZ).isoformat()
                
                # Check vMix API
                is_streaming, status_text, outputs_info, wan_ip = self.check_srt_connection(vmix_ip, dest_port)
                
                # Đánh dấu connection failed nếu không kết nối được
                if "❌" in status_text or "timeout" in status_text.lower():
                    item['connection_failed'] = True
                else:
                    item['connection_failed'] = False
                
                # Lấy WAN IP của máy này (nếu chưa có hoặc cần cập nhật)
                if not wan_ip and not item.get('wan_ip'):
                    wan_ip = self.get_machine_wan_ip(vmix_ip)
                elif item.get('wan_ip'):
                    wan_ip = item['wan_ip']  # Giữ WAN IP đã có
                
                # Detect state change
                current_streaming = is_streaming
                prev_streaming = item.get('prev_status')
                
                if prev_streaming is not None and current_streaming != prev_streaming:
                    # State changed!
                    status_str = "ON" if current_streaming else "OFF"
                    msg = f"[SRT][{name}] SRT {status_str} | IPWAN: {wan_ip} | VMIX: {vmix_ip}:{dest_port}"
                    changes.append(msg)
                    print(f"CHANGE DETECTED: {name} ({vmix_ip}:{dest_port}) -> {status_str}")
                
                # Update status
                item['status'] = status_text
                item['outputs'] = outputs_info
                item['last_check'] = datetime.now(VIETNAM_TZ).strftime('%H:%M:%S')
                item['prev_status'] = current_streaming
                if wan_ip:
                    item['wan_ip'] = wan_ip
            
            # Send changes to Discord
            if changes:
                full_message = "\n".join(changes)
                self.send_discord_webhook(full_message)
            
            # Update UI
            self.root.after(0, self.update_table)
            
            # Sleep 1 second - kiểm tra mỗi 1 giây
            time.sleep(1)
    
    def update_table(self):
        """Cập nhật bảng hiển thị"""
        # Clear old rows
        for row in self.table_rows:
            row.destroy()
        self.table_rows = []
        
        stt = 1
        for idx, item in enumerate(self.monitor_list):
            name = item.get('name', 'N/A')
            vmix_ip = item['ip']
            wan_ip = item.get('wan_ip', '')
            isp = item.get('isp', '')
            mac = item.get('mac', '')
            port = item['port']
            status = item['status']
            outputs = item['outputs'] if item['outputs'] else ''
            last_check = item['last_check']
            
            # Tìm MAC từ bảng MAC-IP nếu chưa có
            if not mac and vmix_ip:
                for m, info in self.mac_ip_table.items():
                    if info.get('ip') == vmix_ip:
                        mac = m
                        item['mac'] = mac
                        break
            
            # Tìm WAN và ISP từ cấu hình nếu chưa có
            if not wan_ip and vmix_ip:
                found_wan, found_isp = self.get_wan_for_ip(vmix_ip)
                if found_wan:
                    wan_ip = found_wan
                    item['wan_ip'] = wan_ip
                if found_isp:
                    isp = found_isp
                    item['isp'] = isp
            
            # Create row frame
            row_frame = ctk.CTkFrame(self.table_frame,
                                     fg_color="#3a3a3a" if stt % 2 == 0 else "#2b2b2b",
                                     height=40)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)
            
            # STT
            ctk.CTkLabel(row_frame, text=str(stt), font=("Arial", 11, "bold"), width=40).pack(side="left", padx=3)
            
            # Name
            ctk.CTkLabel(row_frame, text=name[:12], font=("Arial", 11, "bold"), width=100).pack(side="left", padx=3)
            
            # IP vMix
            ip_color = "#4CAF50" if vmix_ip and vmix_ip not in ['(Chưa scan)', 'Không tìm thấy'] else "#FFC107"
            ctk.CTkLabel(row_frame, text=vmix_ip, font=("Arial", 11), width=130, text_color=ip_color).pack(side="left", padx=3)
            
            # IPWAN
            ctk.CTkLabel(row_frame, text=wan_ip, font=("Arial", 11), width=130, text_color="#FFC107").pack(side="left", padx=3)
            
            # ISP
            isp_color = "#4CAF50" if isp else "#9E9E9E"
            ctk.CTkLabel(row_frame, text=isp[:10] if isp else '', font=("Arial", 10), width=80, text_color=isp_color).pack(side="left", padx=3)
            
            # Port
            ctk.CTkLabel(row_frame, text=str(port), font=("Arial", 11, "bold"), width=60).pack(side="left", padx=3)
            
            # Status
            status_color = "#4CAF50" if "🟢" in status else "#f44336"
            if "⏱️" in status or "❌" in status or "⏳" in status:
                status_color = "#FFC107"
            ctk.CTkLabel(row_frame, text=status, font=("Arial", 10, "bold"), width=100, text_color=status_color).pack(side="left", padx=3)
            
            # Outputs streaming
            outputs_text = str(outputs)[:12] if outputs else ''
            ctk.CTkLabel(row_frame, text=outputs_text, font=("Arial", 10), width=100).pack(side="left", padx=3)
            
            # Time
            ctk.CTkLabel(row_frame, text=last_check, font=("Arial", 10), width=70).pack(side="left", padx=3)
            
            # Delete button
            delete_btn = ctk.CTkButton(row_frame, text="X", width=30, height=25, 
                                       fg_color="#f44336", hover_color="#d32f2f",
                                       command=lambda i=idx: self.remove_item(i))
            delete_btn.pack(side="right", padx=3)
            
            self.table_rows.append(row_frame)
            stt += 1

    def create_ping_view(self):
        """Placeholder - không dùng nữa"""
        pass

def main():
    root = ctk.CTk()
    app = ServerDataGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
