import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import threading
import json
from datetime import datetime

def pretty_time(ts):
    try:
        return datetime.fromisoformat(ts).strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        return ts

class ServerDataGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Server Log Viewer")
        self.root.geometry("1000x600")
        self.root.resizable(False, False)

        self.api_url = "https://tooldiscordvmix.onrender.com"
        self.webhook_var = tk.StringVar(value="https://discord.com/api/webhooks/1448559948408684669/s6plN6AIy9IFBo6coyNCF9YmmHIfIIVe-tEntpPnArRGI0JdIyl1pCz10rL5TyTP1JV6")
        self.prefix_var = tk.StringVar(value="SRT")
        self.data = []
        self.previous_data = []
        self.auto_send_enabled = False
        self.is_sending = False  # Flag để tránh gửi duplicate

        # Top controls
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Row 1: Webhook
        row1 = tk.Frame(top_frame)
        row1.pack(fill=tk.X, pady=2)
        tk.Label(row1, text="Discord Webhook:").pack(side=tk.LEFT)
        self.webhook_entry = tk.Entry(row1, textvariable=self.webhook_var, width=60)
        self.webhook_entry.pack(side=tk.LEFT, padx=5)
        
        # Row 2: Prefix and buttons
        row2 = tk.Frame(top_frame)
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="Prefix:").pack(side=tk.LEFT)
        self.prefix_entry = tk.Entry(row2, textvariable=self.prefix_var, width=10)
        self.prefix_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(row2, text="Refresh", command=self.refresh_data, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        self.toggle_btn = tk.Button(row2, text="AUTO SEND: OFF", command=self.toggle_auto_send, bg="#9E9E9E", fg="white", width=15, font=('Arial', 9, 'bold'))
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(row2, text="Clear Table", command=self.clear_table, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

        # Table
        columns = ("stt", "name", "ip", "ipwan", "status", "port", "timestamp")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=20)
        self.tree.heading("stt", text="STT")
        self.tree.heading("name", text="Tên")
        self.tree.heading("ip", text="IP máy")
        self.tree.heading("ipwan", text="IP WAN")
        self.tree.heading("status", text="Status SRT")
        self.tree.heading("port", text="Port")
        self.tree.heading("timestamp", text="Time")
        self.tree.column("stt", width=50, anchor=tk.CENTER)
        self.tree.column("name", width=120, anchor=tk.CENTER)
        self.tree.column("ip", width=120, anchor=tk.CENTER)
        self.tree.column("ipwan", width=120, anchor=tk.CENTER)
        self.tree.column("status", width=90, anchor=tk.CENTER)
        self.tree.column("port", width=80, anchor=tk.CENTER)
        self.tree.column("timestamp", width=150, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Bind double-click để edit tên
        self.tree.bind("<Double-1>", self.on_double_click)

        # Detail area
        detail_frame = tk.LabelFrame(self.root, text="Detail (select a row)")
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.detail_text = scrolledtext.ScrolledText(detail_frame, height=8, font=("Consolas", 10), bg="#222", fg="#00FF00")
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.config(state=tk.DISABLED)

        self.tree.bind("<<TreeviewSelect>>", self.show_detail)
        self.auto_refresh()

    def toggle_auto_send(self):
        """Bật/Tắt chế độ tự động gửi Discord khi có thay đổi"""
        self.auto_send_enabled = not self.auto_send_enabled
        if self.auto_send_enabled:
            self.toggle_btn.config(text="AUTO SEND: ON", bg="#4CAF50")
            print("✓ Auto-send to Discord: ENABLED")
            # Disable editing khi đang ON
            self.webhook_entry.config(state=tk.DISABLED)
            self.prefix_entry.config(state=tk.DISABLED)
            # Lấy snapshot ban đầu
            self.previous_data = self.get_data_snapshot()
            # Gửi ngay lập tức 1 lần trước
            self.send_to_discord_auto()
            # Bắt đầu auto-check
            self.check_for_changes()
        else:
            self.toggle_btn.config(text="AUTO SEND: OFF", bg="#9E9E9E")
            print("✗ Auto-send to Discord: DISABLED")
            # Enable editing khi tắt OFF
            self.webhook_entry.config(state=tk.NORMAL)
            self.prefix_entry.config(state=tk.NORMAL)
    
    def get_data_snapshot(self):
        """Lấy snapshot của dữ liệu hiện tại (không bao gồm timestamp)"""
        snapshot = []
        for entry in self.data:
            d = entry.get("data", {})
            snapshot.append({
                "name": d.get("name", ""),
                "ip": d.get("ip", ""),
                "ipwan": d.get("ipwan", ""),
                "port": d.get("port", ""),
                "status": d.get("status", "")
            })
        return snapshot
    
    def check_for_changes(self):
        """Kiểm tra thay đổi và tự động gửi Discord"""
        if not self.auto_send_enabled:
            return
        
        # Refresh data
        def check():
            url = self.api_url
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        self.data = data
                        self.update_table()
                        
                        # So sánh với dữ liệu cũ
                        current_snapshot = self.get_data_snapshot()
                        if current_snapshot != self.previous_data:
                            print("⚠ Phát hiện thay đổi! Gửi Discord...")
                            self.send_to_discord_auto()
                            self.previous_data = current_snapshot
            except Exception as e:
                print(f"Error checking: {e}")
        
        threading.Thread(target=check, daemon=True).start()
        
        # Schedule next check (5 seconds)
        if self.auto_send_enabled:
            self.root.after(5000, self.check_for_changes)
    
    def send_to_discord_auto(self):
        """Gửi toàn bộ trạng thái hiện tại lên Discord (tự động)"""
        # Tránh gửi duplicate nếu đang trong quá trình gửi
        if self.is_sending:
            print("⏳ Đang gửi, bỏ qua request...")
            return
        
        webhook = self.webhook_var.get().strip()
        if not webhook or not self.data:
            return
        
        self.is_sending = True
        
        def send():
            try:
                prefix = self.prefix_var.get().strip()
                messages = []
                
                for entry in self.data:
                    d = entry.get("data", {})
                    name = d.get("name", "Unknown")
                    ipwan = d.get("ipwan", "unknown")
                    port = d.get("port", "N/A")
                    status = d.get("status", "UNKNOWN")
                    
                    msg = f"[{prefix}][{name}] SRT {status} | IPWAN: {ipwan} | PORT: {port}"
                    messages.append(msg)
                
                payload = {"content": "\n".join(messages)}
                
                resp = requests.post(webhook, json=payload, timeout=10)
                if resp.status_code in [200, 204]:
                    print(f"✓ Sent {len(messages)} notifications to Discord")
                else:
                    print(f"✗ Discord error: {resp.status_code}")
            except Exception as e:
                print(f"✗ Failed to send: {e}")
            finally:
                self.is_sending = False
        
        threading.Thread(target=send, daemon=True).start()

    def refresh_data(self):
        def fetch():
            url = self.api_url
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, list):
                            self.data = data
                        else:
                            self.data = []
                        self.update_table()
                    except Exception as e:
                        messagebox.showerror("Error", f"JSON decode error: {e}")
                else:
                    messagebox.showerror("Error", f"HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                messagebox.showerror("Error", f"ERROR: {str(e)}")
        threading.Thread(target=fetch, daemon=True).start()

    def update_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        stt = 1
        for entry in self.data:
            ts = pretty_time(entry.get("timestamp", ""))
            d = entry.get("data", {})
            # Nếu có trường 'cameras' (dạng cũ), hiển thị từng camera
            if isinstance(d.get("cameras", None), list):
                ipwan = d.get("ipwan", "")
                for cam in d["cameras"]:
                    name = cam.get("name", "")
                    ip = cam.get("ip", d.get("ip", ""))
                    port = cam.get("port", "")
                    status = cam.get("status", "")
                    self.tree.insert("", tk.END, values=(stt, name, ip, ipwan, status, port, ts))
                    stt += 1
            # Nếu là dạng đơn giản (dạng mới)
            else:
                name = d.get("name", "").strip()
                # Nếu tên trống, đặt mặc định là MÁY + STT
                if not name:
                    name = f"MÁY {stt}"
                ip = d.get("ip", "")
                ipwan = d.get("ipwan", "")
                status = d.get("status", "")
                port = d.get("port", "")
                self.tree.insert("", tk.END, values=(stt, name, ip, ipwan, status, port, ts))
                stt += 1

    def on_double_click(self, event):
        """Xử lý double-click để edit tên"""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        column = self.tree.identify_column(event.x)
        # Chỉ cho edit cột "name" (column #1)
        if column != "#2":
            return
        
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        idx = self.tree.index(item)
        
        if idx >= len(self.data):
            return
        
        # Lấy giá trị hiện tại
        values = self.tree.item(item, "values")
        old_name = values[1]
        
        # Tạo Entry widget để edit
        x, y, width, height = self.tree.bbox(item, column)
        entry = tk.Entry(self.tree, justify="center")
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, old_name)
        entry.select_range(0, tk.END)
        entry.focus()
        
        def save_edit(event=None):
            new_name = entry.get().strip()
            entry.destroy()
            if new_name and new_name != old_name:
                # Cập nhật vào MongoDB
                entry_data = self.data[idx]
                old_data = entry_data.get("data", {})
                old_ip = old_data.get("ip", "")
                
                # Gửi request update name
                def update_name():
                    try:
                        # Cập nhật local
                        self.data[idx]["data"]["name"] = new_name
                        
                        # Gửi lên server để update MongoDB
                        update_data = {
                            "old_name": old_name,
                            "new_name": new_name,
                            "ip": old_ip
                        }
                        resp = requests.post(f"{self.api_url}/update_name", json=update_data, timeout=5)
                        if resp.status_code == 200:
                            print(f"✓ Đã đổi tên: {old_name} → {new_name}")
                            # Refresh lại data từ server
                            self.refresh_data()
                        else:
                            print(f"✗ Lỗi đổi tên: {resp.status_code}")
                    except Exception as e:
                        print(f"✗ Lỗi: {e}")
                
                threading.Thread(target=update_name, daemon=True).start()
        
        def cancel_edit(event=None):
            entry.destroy()
        
        entry.bind("<Return>", save_edit)
        entry.bind("<Escape>", cancel_edit)
    
    def show_detail(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        idx = self.tree.index(selected[0])
        entry = self.data[idx] if idx < len(self.data) else None
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        if entry:
            self.detail_text.insert(tk.END, json.dumps(entry, indent=2, ensure_ascii=False))
        self.detail_text.config(state=tk.DISABLED)

    def clear_table(self):
        self.data = []
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.config(state=tk.DISABLED)

    def auto_refresh(self):
        self.refresh_data()
        self.root.after(10000, self.auto_refresh)

def main():
    root = tk.Tk()
    app = ServerDataGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
