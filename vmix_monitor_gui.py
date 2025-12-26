import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import queue
import re
import os
import sys
import json
from datetime import datetime

class VmixMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Vmix tool")
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        
        # Set icon
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "Discord-Logo.png")
            if os.path.exists(icon_path):
                self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
        except Exception as e:
            pass  # If icon fails, continue without it
        
        # Variables
        self.webhook_var = tk.StringVar(value="")
        self.prefix_var = tk.StringVar(value="")
        self.scan_speed_var = tk.IntVar(value=1000)
        self.check_ip_var = tk.IntVar(value=300)
        
        self.process = None
        self.is_running = False
        self.log_queue = queue.Queue()
        
        # Camera list - empty by default
        self.cameras = []
        
        self.setup_ui()
        self.check_log_queue()
        
    def setup_ui(self):
        # Navigation bar at top
        nav_frame = tk.Frame(self.root, relief=tk.RAISED, borderwidth=2, bg='#e0e0e0')
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(nav_frame, text="OPEN", command=self.open_config, 
                  bg='#2196F3', fg='white', width=12, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(nav_frame, text="SAVE", command=self.save_config, 
                  bg='#FF9800', fg='white', width=12, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Main container with border
        main_frame = tk.Frame(self.root, relief=tk.RIDGE, borderwidth=2, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Webhook and Prefix section
        config_frame = tk.LabelFrame(main_frame, text="", relief=tk.RIDGE, borderwidth=2, bg='#f0f0f0')
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(config_frame, text="WEBHOOK URL: [", bg='#f0f0f0').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        webhook_entry = tk.Entry(config_frame, textvariable=self.webhook_var, width=50, show="*")
        webhook_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(config_frame, text="]", bg='#f0f0f0').grid(row=0, column=2, sticky=tk.W)
        
        tk.Label(config_frame, text="PREFIX:", bg='#f0f0f0').grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        tk.Entry(config_frame, textvariable=self.prefix_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Monitor List section
        monitor_frame = tk.LabelFrame(main_frame, text="MONITOR LIST:", relief=tk.RIDGE, borderwidth=2, bg='#f0f0f0')
        monitor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Table headers
        header_frame = tk.Frame(monitor_frame, bg='#f0f0f0')
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(header_frame, text="NAME", width=20, anchor=tk.W, relief=tk.RIDGE, borderwidth=1, bg='#f0f0f0').pack(side=tk.LEFT, padx=2)
        tk.Label(header_frame, text="PORT", width=15, anchor=tk.W, relief=tk.RIDGE, borderwidth=1, bg='#f0f0f0').pack(side=tk.LEFT, padx=2)
        
        # Camera list container with scrollbar
        list_container = tk.Frame(monitor_frame, bg='#f0f0f0')
        list_container.pack(fill=tk.BOTH, expand=True, padx=5)
        
        self.camera_canvas = tk.Canvas(list_container, bg='#f0f0f0', highlightthickness=0, height=120)
        self.camera_scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.camera_canvas.yview)
        self.camera_list_frame = tk.Frame(self.camera_canvas, bg='#f0f0f0')
        
        self.camera_list_frame.bind(
            "<Configure>",
            lambda e: self.camera_canvas.configure(scrollregion=self.camera_canvas.bbox("all"))
        )
        
        self.canvas_frame = self.camera_canvas.create_window((0, 0), window=self.camera_list_frame, anchor="nw")
        self.camera_canvas.configure(yscrollcommand=self.camera_scrollbar.set)
        
        self.camera_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.camera_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.refresh_camera_list()
        
        # Add button
        add_btn_frame = tk.Frame(monitor_frame, bg='#f0f0f0')
        add_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(add_btn_frame, text="[ + Add New Camera ]", command=self.add_camera, bg='#e0e0e0').pack(anchor=tk.W)
        
        # Advanced section
        advanced_frame = tk.LabelFrame(main_frame, text="ADVANCED:", relief=tk.RIDGE, borderwidth=2, bg='#f0f0f0')
        advanced_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(advanced_frame, text="Scan Speed: [", bg='#f0f0f0').grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        tk.Entry(advanced_frame, textvariable=self.scan_speed_var, width=8).grid(row=0, column=1, sticky=tk.W)
        tk.Label(advanced_frame, text="] ms    Check IP: [", bg='#f0f0f0').grid(row=0, column=2, sticky=tk.W, padx=5)
        tk.Entry(advanced_frame, textvariable=self.check_ip_var, width=8).grid(row=0, column=3, sticky=tk.W)
        tk.Label(advanced_frame, text="] sec", bg='#f0f0f0').grid(row=0, column=4, sticky=tk.W)
        
        # Logs section
        log_frame = tk.LabelFrame(main_frame, text="LOGS:", relief=tk.RIDGE, borderwidth=2, bg='#f0f0f0')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, bg='black', fg='#00ff00', 
                                                   font=('Consolas', 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Control buttons
        btn_frame = tk.Frame(main_frame, bg='#f0f0f0')
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.start_btn = tk.Button(btn_frame, text="START", command=self.start_monitoring, 
                                    bg='#4CAF50', fg='white', width=15, font=('Arial', 10, 'bold'))
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Clear Logs", command=self.clear_logs, 
                  bg='#9E9E9E', fg='white', width=15).pack(side=tk.LEFT, padx=5)
        
    def refresh_camera_list(self):
        # Clear existing widgets
        for widget in self.camera_list_frame.winfo_children():
            widget.destroy()
        
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
        try:
            # Build PowerShell command
            ports = ",".join([str(cam['port']) for cam in self.cameras])
            names = ",".join([f"'{cam['name']}'" for cam in self.cameras])
            
            script_path = os.path.join(os.path.dirname(__file__), "monitor_script.ps1")
            
            cmd = [
                "powershell.exe",
                "-WindowStyle", "Hidden",
                "-ExecutionPolicy", "Bypass",
                "-File", script_path,
                "-Ports", ports,
                "-Names", names,
                "-Webhook", self.webhook_var.get(),
                "-Prefix", self.prefix_var.get(),
                "-PollMs", str(self.scan_speed_var.get()),
                "-WanRefreshSec", str(self.check_ip_var.get())
            ]
            
            # Hide console window on Windows
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            for line in self.process.stdout:
                line = line.strip()
                if line:
                    self.log(line)
            
            self.process.wait()
            self.log("Notification sent.")
            
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
    
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
