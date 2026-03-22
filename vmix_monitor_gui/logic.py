import glob
import html
import os
import re
import socket
import subprocess
import threading
import time
import tkinter as tk
import xml.etree.ElementTree as ET
from datetime import datetime
from tkinter import messagebox

try:
    from .shared import SERVER_URL, VIETNAM_TZ
except ImportError:
    try:
        from vmix_monitor_gui.shared import SERVER_URL, VIETNAM_TZ
    except ImportError:
        from shared import SERVER_URL, VIETNAM_TZ


class VmixMonitorLogicMixin:
    @staticmethod
    def _to_float_or_none(value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_mbps_text(value_mbps: float | None) -> str:
        if value_mbps is None:
            return "—"
        if value_mbps >= 100:
            return f"{value_mbps:.0f} Mbps"
        if value_mbps >= 10:
            return f"{value_mbps:.1f} Mbps"
        return f"{value_mbps:.2f} Mbps"

    @staticmethod
    def _format_fps_value(fps_val: float) -> str:
        for std in (23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0):
            if abs(fps_val - std) < 0.1:
                return f"{std:g}"
        return f"{fps_val:.4g}"

    def _fps_from_ticks(self, ticks_str: str) -> str:
        try:
            ticks = int(ticks_str)
            if ticks <= 0:
                return ""
            fps_val = 10_000_000 / ticks
            return self._format_fps_value(fps_val)
        except (TypeError, ValueError, ZeroDivisionError):
            return ""

    def _fps_from_api_value(self, raw_value: str) -> str:
        if not raw_value:
            return "—"

        value = raw_value.strip().replace(",", ".")
        if not value:
            return "—"

        try:
            num = float(value)
        except ValueError:
            return value

        if num <= 0:
            return "—"

        # vMix có thể trả frame rate dạng ticks (100ns/frame), ví dụ 333333.
        if num > 1000:
            from_ticks = self._fps_from_ticks(str(int(num)))
            return from_ticks or value

        return self._format_fps_value(num)

    @staticmethod
    def _bw_str(bps_str: str) -> str:
        try:
            bps = int(bps_str)
            if bps >= 1_000_000:
                return f"{bps // 1_000_000}Mbps"
            return f"{bps // 1000}kbps"
        except (TypeError, ValueError):
            return "?"

    def _parse_resolution_and_srt_from_preset(self, preset_path: str) -> tuple[str, dict]:
        if not preset_path or not os.path.isfile(preset_path):
            return "—", {}

        resolution = "—"
        srt_by_port = {}
        try:
            root = ET.parse(preset_path).getroot()

            out_fmt = root.find(".//OutputFormat")
            if out_fmt is not None:
                size = out_fmt.get("OutputSize", "")
                fr_ticks = out_fmt.get("OutputFrameRate", "")
                h = size.split("x")[1] if "x" in size else ""
                fps_str = self._fps_from_ticks(fr_ticks)
                if h:
                    resolution = f"{h}p{fps_str}" if fps_str else f"{h}p"

            for ext_name in ("OutputsExternal", "OutputsExternal2", "OutputsExternal3", "OutputsExternal4"):
                ext = root.find(f".//{ext_name}")
                if ext is None:
                    continue

                enabled = (ext.findtext("SRTEnabled") or "0").strip()
                port_str = (ext.findtext("SRTPort") or "0").strip()
                try:
                    port = int(port_str)
                except ValueError:
                    port = 0
                if enabled != "1" or not port:
                    continue

                codec_id = (ext.findtext("SRTVideoCodec") or "").strip()
                codec = "HEVC" if codec_id == "1" else "H264"
                vbw_s = self._bw_str(ext.findtext("SRTVideoBandwidth") or "0")
                abw_s = self._bw_str(ext.findtext("SRTAudioBandwidth") or "0")
                hw = " HW" if (ext.findtext("SRTHardwareEncoder") or "0").strip() == "1" else ""
                srt_by_port[port] = f"{codec} {vbw_s} AAC {abw_s}{hw}"
        except Exception:
            pass

        return resolution, srt_by_port

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def import_from_old_ip(self, old_ip: str):
        import requests

        try:
            current_ip = self.ip_var.get().strip()
            if old_ip == current_ip:
                self.log("⚠️ IP cũ và IP mới giống nhau!")
                return

            self.log(f"📥 Đang import data từ IP {old_ip}...")
            url = f"{SERVER_URL}/get_by_ip?ip={old_ip}"
            response = requests.get(url, timeout=20)

            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list):
                    imported_count = 0
                    for entry in data:
                        entry_data = entry.get("data", {})
                        name = entry_data.get("name", "")
                        port = entry_data.get("port", 0)
                        ipwan = entry_data.get("ipwan", "unknown")
                        if name and port:
                            exists = False
                            for existing in self.port_list:
                                if existing["name"] == name or existing["port"] == port:
                                    exists = True
                                    self.log(f"⚠️ Bỏ qua {name} (đã tồn tại)")
                                    break

                            if not exists:
                                self.port_list.append(
                                    {
                                        "name": name,
                                        "port": port,
                                        "ip": current_ip,
                                        "ipwan": ipwan,
                                        "ping": "—",
                                        "timeout": "0",
                                        "cpu": "—",
                                        "memory": "—",
                                        "gpu": "—",
                                        "sender_bw": "—",
                                        "receiver_bw": "—",
                                        "rec": "—",
                                        "live": "—",
                                        "ext": "—",
                                        "resolution": "—",
                                        "srt": "—",
                                    }
                                )
                                self.tree.insert(
                                    "",
                                    tk.END,
                                    values=(
                                        name,
                                        current_ip,
                                        ipwan,
                                        port,
                                        "—",
                                        "0",
                                        "—",
                                        "—",
                                        "—",
                                        "—",
                                        "—",
                                        "—",
                                        "—",
                                        "—",
                                        "—",
                                        "—",
                                    ),
                                )
                                imported_count += 1
                                threading.Thread(
                                    target=lambda n=name, p=port: self.update_single_ip_in_database(
                                        old_ip, current_ip, n, p
                                    ),
                                    daemon=True,
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
        import requests

        try:
            data = {"old_ip": old_ip, "new_ip": new_ip, "port": port, "name": name}
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
        old_ip = self.ip_var.get().strip()
        new_ip = self.get_local_ip()
        if old_ip == new_ip:
            self.log(f"ℹ️ IP không đổi: {new_ip}")
            return

        self.log(f"🔄 IP thay đổi: {old_ip} → {new_ip}")
        self.ip_var.set(new_ip)
        for entry in self.port_list:
            entry["ip"] = new_ip

        for item in self.tree.get_children():
            values = list(self.tree.item(item, "values"))
            values[1] = new_ip
            self.tree.item(item, values=values)

        if self.port_list:
            threading.Thread(target=lambda: self.update_ip_in_database(old_ip, new_ip), daemon=True).start()

    def update_ip_in_database(self, old_ip: str, new_ip: str):
        import requests

        try:
            for entry in self.port_list:
                data = {
                    "old_ip": old_ip,
                    "new_ip": new_ip,
                    "port": entry["port"],
                    "name": entry["name"],
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
        threading.Thread(target=self._check_server_thread, daemon=True).start()

    def _check_server_thread(self):
        import requests

        self.log("🔍 Đang kiểm tra server...")
        start_time = time.time()
        try:
            url = f"{SERVER_URL}/logs"
            response = requests.get(url, timeout=30)
            elapsed = time.time() - start_time
            if response.status_code == 200:
                self.log(f"✅ Server hoạt động tốt! (Phản hồi trong {elapsed:.1f}s)")
            elif response.status_code == 500:
                self.log("⚠️ Server đang có vấn đề (500). Có thể đang khởi động lại...")
            else:
                self.log(f"❓ Server phản hồi: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            self.log("⏱️ Server timeout (>30s) - có thể đang cold start, hãy thử lại sau 1 phút")
        except requests.exceptions.ConnectionError:
            self.log("❌ Không kết nối được server - kiểm tra internet hoặc server đang down")
        except Exception as e:
            self.log(f"❌ Lỗi kiểm tra server: {str(e)}")

    def load_data_from_database(self):
        import requests

        try:
            ip = self.ip_var.get().strip()
            url = f"{SERVER_URL}/get_by_ip?ip={ip}"
            self.log("⏳ Đang tải dữ liệu từ server...")
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list):
                    self.port_list.clear()
                    for item in self.tree.get_children():
                        self.tree.delete(item)

                    loaded_count = 0
                    for entry in data:
                        entry_data = entry.get("data", {})
                        name = entry_data.get("name", "")
                        port = entry_data.get("port", 0)
                        entry_ip = entry_data.get("ip", ip)
                        ipwan = entry_data.get("ipwan", "unknown")
                        ping = entry_data.get("ping", None)
                        memory = entry_data.get("memory", None)
                        cpu = entry_data.get("temperature", entry_data.get("cpu", None))
                        gpu = entry_data.get("gpu", None)
                        sender_mbps = entry_data.get("sender_mbps", None)
                        receiver_mbps = entry_data.get("receiver_mbps", None)

                        if name and port:
                            self.port_list.append(
                                {
                                    "name": name,
                                    "port": port,
                                    "ip": entry_ip,
                                    "ipwan": ipwan,
                                    "ping": f"{ping:.0f}" if ping is not None else "—",
                                    "cpu": f"{cpu:.1f}" if cpu is not None else "—",
                                    "memory": f"{memory:.1f}" if memory is not None else "—",
                                    "gpu": f"{gpu:.1f}" if gpu is not None else "—",
                                    "sender_bw": self._format_mbps_text(self._to_float_or_none(sender_mbps)),
                                    "receiver_bw": self._format_mbps_text(self._to_float_or_none(receiver_mbps)),
                                    "rec": "—",
                                    "live": "—",
                                    "ext": "—",
                                    "resolution": "—",
                                    "srt": "—",
                                }
                            )
                            self.tree.insert(
                                "",
                                tk.END,
                                values=(
                                    name,
                                    entry_ip,
                                    ipwan,
                                    port,
                                    f"{ping:.0f}" if ping is not None else "—",
                                    "0",
                                    f"{cpu:.1f}" if cpu is not None else "—",
                                    f"{memory:.1f}" if memory is not None else "—",
                                    f"{gpu:.1f}" if gpu is not None else "—",
                                    self._format_mbps_text(self._to_float_or_none(sender_mbps)),
                                    self._format_mbps_text(self._to_float_or_none(receiver_mbps)),
                                    "—",
                                    "—",
                                    "—",
                                    "—",
                                    "—",
                                ),
                            )
                            loaded_count += 1

                    if loaded_count > 0:
                        self.log(f"✅ Đã tải {loaded_count} port từ database (IP: {ip})")
                    else:
                        self.log(f"ℹ️ Không có dữ liệu cho IP {ip} trong database")
                        self.check_for_old_ip_data()
                else:
                    self.log(f"ℹ️ Không có dữ liệu cho IP {ip} trong database")
                    self.check_for_old_ip_data()
            elif response.status_code == 500:
                self.log("⚠️ Server đang có vấn đề (500) - có thể đang cold start, hãy thử lại sau 30s")
            else:
                self.log(f"❌ Không thể tải dữ liệu: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            self.log("⏱️ Timeout khi tải dữ liệu - server có thể đang ngủ, hãy đợi 30-60s")
        except Exception as e:
            self.log(f"❌ Lỗi khi load dữ liệu: {str(e)}")

    def check_for_old_ip_data(self):
        import requests

        try:
            url = f"{SERVER_URL}/logs"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                all_data = response.json()
                if all_data and isinstance(all_data, list):
                    current_ip = self.ip_var.get().strip()
                    found_ips = set()
                    for entry in all_data:
                        entry_data = entry.get("data", {})
                        entry_ip = entry_data.get("ip", "")
                        if entry_ip and entry_ip != current_ip:
                            found_ips.add(entry_ip)
                    if found_ips:
                        self.root.after(1000, lambda: self.show_old_ip_notification(list(found_ips)))
        except Exception:
            pass

    def show_old_ip_notification(self, old_ips: list):
        if not old_ips:
            return

        ip_list = "\n".join(f"  • {ip}" for ip in old_ips[:5])
        result = messagebox.askyesno(
            "📥 Phát hiện dữ liệu IP cũ",
            f"Tìm thấy dữ liệu trong database với IP khác:\n\n{ip_list}\n\n"
            f"Bạn có muốn import dữ liệu từ IP cũ không?",
            icon="question",
        )
        if result:
            self.show_import_dialog()

    def add_port_entry(self):
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
        except Exception:
            messagebox.showerror("Lỗi", "Port phải là số từ 1-65535!")
            return

        ip = self.ip_var.get().strip()
        for entry in self.port_list:
            if entry["name"] == name:
                messagebox.showwarning("Cảnh báo", f"Tên máy '{name}' đã tồn tại!")
                return
            if entry["port"] == port:
                messagebox.showwarning("Cảnh báo", f"Port {port} đã được sử dụng!")
                return

        self.port_list.append(
            {
                "name": name,
                "port": port,
                "ip": ip,
                "ipwan": "loading...",
                "ping": "—",
                "timeout": "0",
                "cpu": "—",
                "memory": "—",
                "gpu": "—",
                "sender_bw": "—",
                "receiver_bw": "—",
                "rec": "—",
                "live": "—",
                "ext": "—",
                "resolution": "—",
                "srt": "—",
            }
        )
        self.tree.insert("", tk.END, values=(name, ip, "loading...", port, "—", "0", "—", "—", "—", "—", "—", "—", "—", "—", "—", "—"))

        self.name_var.set("")
        self.port_var.set("")
        self.log(f"Đã thêm: {name} - {ip} - Port {port}")

        def fetch_wan_async():
            wan_ip = self.get_wan_ip()
            for entry in self.port_list:
                if entry["name"] == name and entry["port"] == port:
                    entry["ipwan"] = wan_ip
                    break
            self.root.after(0, self.update_table_display)
            self.log(f"✅ Đã cập nhật IPWAN cho {name}: {wan_ip}")

        threading.Thread(target=fetch_wan_async, daemon=True).start()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một mục để xóa!")
            return

        for item in selected:
            values = self.tree.item(item, "values")
            if values:
                name = values[0]
                ip = values[1]
                port = int(values[3]) if values[3] else 0
                self.port_list = [e for e in self.port_list if not (e["name"] == name and e["port"] == port)]
                self.tree.delete(item)
                threading.Thread(target=lambda n=name, i=ip, p=port: self.delete_single_from_database(n, i, p), daemon=True).start()
                self.log(f"Đã xóa: {name} - {ip} - Port {port}")

    def delete_single_from_database(self, name, ip, port):
        import requests

        try:
            data = {"name": name, "ip": ip, "port": port}
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

    def send_app_status(self, status_value):
        import requests

        if not self.port_list:
            self.log("⚠️ Không có port nào trong danh sách!")
            return

        ip = self.ip_var.get().strip()
        if not ip:
            return

        try:
            wan_ip = self.get_wan_ip()
            for entry in self.port_list:
                data = {
                    "name": entry["name"],
                    "ip": ip,
                    "ipwan": wan_ip,
                    "status": "OFF",
                    "port": entry["port"],
                    "statusapp": status_value,
                }
                url = SERVER_URL
                headers = {"Content-Type": "application/json"}

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post(url, json=data, headers=headers, timeout=15)
                        if response.status_code == 200:
                            status_text = "ON" if status_value == 1 else "OFF"
                            self.log(f"✅ App status {status_text}: {entry['name']} - Port {entry['port']}")
                            break
                        elif response.status_code == 500:
                            if attempt < max_retries - 1:
                                wait_time = (attempt + 1) * 2
                                self.log(f"⚠️ Server error 500 ({entry['name']}), retry sau {wait_time}s... (lần {attempt + 1}/{max_retries})")
                                time.sleep(wait_time)
                            else:
                                self.log(f"❌ Lỗi 500 {entry['name']}")
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
            self.ping_timeout_count = 0
            self.start_btn.config(text="⏹️ STOP MONITORING", bootstyle="danger")
            self.status_label.config(text="● Running", bootstyle="success")
            self.delete_btn.config(state=tk.DISABLED)
            self.name_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.add_btn.config(state=tk.DISABLED)
            self.log("✅ Bắt đầu gửi dữ liệu...")
            threading.Thread(target=lambda: self.send_app_status(1), daemon=True).start()
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_running = False
            self.log("⏹️ Đang dừng và cập nhật trạng thái...")
            threading.Thread(target=self.stop_and_cleanup, daemon=True).start()
            self.start_btn.config(text="▶️ START MONITORING", bootstyle="success")
            self.status_label.config(text="● Stopped", bootstyle="secondary")
            self.delete_btn.config(state=tk.NORMAL)
            self.name_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            self.add_btn.config(state=tk.NORMAL)

    def stop_and_cleanup(self):
        self.send_app_status(0)
        self.log("Đã dừng và cập nhật trạng thái OFF.")

    def _ping_bg_loop(self):
        while True:
            val = self.measure_ping()
            with self._ping_lock:
                self._ping_ms = val
                if val is None:
                    self.ping_timeout_count += 1
            time.sleep(3)

    def measure_ping(self, host="8.8.8.8") -> float | None:
        try:
            result = subprocess.run(
                ["ping", "-n", "1", "-w", "1000", host],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=3,
            )
            match = re.search(r"Average\s*=\s*(\d+)ms", result.stdout)
            if not match:
                match = re.search(r"Minimum\s*=\s*(\d+)ms", result.stdout)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None

    def measure_cpu(self) -> float | None:
        try:
            import psutil

            return round(psutil.cpu_percent(interval=None), 1)
        except Exception:
            pass
        return None

    def measure_memory(self) -> float | None:
        try:
            import psutil

            return round(psutil.virtual_memory().percent, 1)
        except Exception:
            pass
        return None

    def measure_gpu(self) -> float | None:
        # Ưu tiên nvidia-smi để lấy % GPU, lấy trung bình nếu có nhiều GPU.
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode != 0:
                return None

            values = []
            for line in result.stdout.splitlines():
                text = line.strip().replace("%", "")
                if not text:
                    continue
                try:
                    values.append(float(text))
                except ValueError:
                    continue

            if values:
                return round(sum(values) / len(values), 1)
        except Exception:
            pass

        return None

    def measure_network_sender_receiver_mbps(self) -> tuple[float | None, float | None]:
        try:
            import psutil

            counters = psutil.net_io_counters()
            sent_now = int(counters.bytes_sent)
            recv_now = int(counters.bytes_recv)
            ts_now = time.time()

            if self._net_last_ts is None:
                self._net_last_sent = sent_now
                self._net_last_recv = recv_now
                self._net_last_ts = ts_now
                return None, None

            dt = max(ts_now - self._net_last_ts, 1e-6)
            sent_diff = max(sent_now - int(self._net_last_sent or 0), 0)
            recv_diff = max(recv_now - int(self._net_last_recv or 0), 0)

            self._net_last_sent = sent_now
            self._net_last_recv = recv_now
            self._net_last_ts = ts_now

            sender_mbps = (sent_diff * 8) / dt / 1_000_000
            receiver_mbps = (recv_diff * 8) / dt / 1_000_000
            return round(sender_mbps, 3), round(receiver_mbps, 3)
        except Exception:
            return None, None

    @staticmethod
    def _vmix_data_dir() -> str:
        base = os.environ.get("PROGRAMDATA") or os.environ.get("ALLUSERSPROFILE") or r"C:\ProgramData"
        return os.path.join(base, "vMix")

    @staticmethod
    def _read_file_shared(filepath: str) -> str:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        GENERIC_READ = 0x80000000
        FILE_SHARE_ALL = 0x07
        OPEN_EXISTING = 3
        FILE_ATTRIBUTE_NORMAL = 0x80
        INVALID_HANDLE = ctypes.c_void_p(-1).value
        handle = kernel32.CreateFileW(filepath, GENERIC_READ, FILE_SHARE_ALL, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
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
            return buf.raw[: read.value].decode("utf-8", errors="replace")
        finally:
            kernel32.CloseHandle(handle)

    def get_vmix_resolution_from_file(self, preset_path: str = "") -> str:
        project_file = preset_path if preset_path and os.path.isfile(preset_path) else None
        if not project_file:
            try:
                import psutil

                for proc in psutil.process_iter(["name", "cmdline"]):
                    try:
                        if "vmix" in (proc.info["name"] or "").lower():
                            for arg in (proc.info.get("cmdline") or []):
                                if arg.lower().endswith(".vmix") and os.path.isfile(arg):
                                    project_file = arg
                                    break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    if project_file:
                        break
            except Exception:
                pass

        if not project_file:
            try:
                search_dirs = []
                appdata = os.environ.get("APPDATA", "")
                if appdata:
                    search_dirs.append(os.path.join(appdata, "vMix"))
                home = os.path.expanduser("~")
                search_dirs += [
                    os.path.join(home, "Documents", "vMix"),
                    os.path.join(home, "Desktop"),
                    os.path.join(home, "Documents"),
                ]
                candidates = []
                for d in search_dirs:
                    candidates.extend(glob.glob(os.path.join(d, "*.vmix")))
                if candidates:
                    project_file = max(candidates, key=os.path.getmtime)
            except Exception:
                pass

        if not project_file:
            return "—"

        try:
            xml_text = self._read_file_shared(project_file)
            root = ET.fromstring(xml_text)
            out_fmt = root.find(".//OutputFormat")
            if out_fmt is not None:
                size = out_fmt.get("OutputSize", "")
                fr_ticks = out_fmt.get("OutputFrameRate", "")
                h = size.split("x")[1] if "x" in size else ""
                fps_str = self._fps_from_ticks(fr_ticks)
                if h:
                    return f"{h}p{fps_str}" if fps_str else f"{h}p"
        except Exception:
            pass

        return "—"

    def get_res_and_srt_from_file(self) -> tuple:
        if time.time() - self._vmix_file_ts < 5:
            return self._vmix_file_cache

        vmix_dir = self._vmix_data_dir()
        video_txt = os.path.join(vmix_dir, "video.txt")
        config_file = os.path.join(vmix_dir, "settingbackups", "current.config")

        resolution = "—"
        try:
            raw_text = self._read_file_shared(video_txt)
            v = [l.strip() for l in raw_text.splitlines()]
            h = v[1] if len(v) > 1 else ""
            fps_str = self._fps_from_ticks(v[2]) if len(v) > 2 else ""
            if h:
                resolution = f"{h}p{fps_str}" if fps_str else f"{h}p"
        except Exception:
            pass

        srt_by_port: dict = {}
        try:
            content = self._read_file_shared(config_file)
            for ext_name in ("OutputsExternal", "OutputsExternal2", "OutputsExternal3", "OutputsExternal4"):
                m = re.search(rf'name="{re.escape(ext_name)}"[^>]*>\s*<value>(.*?)</value>', content, re.DOTALL)
                if not m:
                    continue
                decoded = html.unescape(m.group(1).strip())
                try:
                    sub = ET.fromstring(f"<root>{decoded}</root>")
                except Exception:
                    continue

                try:
                    port = int((sub.findtext("SRTPort") or "0").strip())
                except ValueError:
                    port = 0
                if not port:
                    continue

                codec = "HEVC" if (sub.findtext("SRTVideoCodec") or "0").strip() == "1" else "H264"
                try:
                    vbw = int(sub.findtext("SRTVideoBandwidth") or "0")
                    vbw_s = f"{vbw // 1_000_000}Mbps" if vbw >= 1_000_000 else f"{vbw // 1000}kbps"
                except Exception:
                    vbw_s = "?"
                try:
                    abw = int(sub.findtext("SRTAudioBandwidth") or "0")
                    abw_s = f"{abw // 1000}kbps"
                except Exception:
                    abw_s = "?"

                hw = " HW" if (sub.findtext("SRTHardwareEncoder") or "0").strip() == "1" else ""
                srt_by_port[port] = f"{codec} {vbw_s} AAC {abw_s}{hw}"
        except Exception:
            pass

        result = (resolution, srt_by_port)
        self._vmix_file_cache = result
        self._vmix_file_ts = time.time()
        return result

    def test_vmix_api(self):
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
                    for i in range(0, min(len(text), 900), 300):
                        self.log(f"[vMix XML] {text[i:i+300]}")
                else:
                    self.log(f"[vMix Test] Body: {resp.text[:200]}")
            except Exception as e:
                self.log(f"[vMix Test] Error: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def get_vmix_stats(self) -> dict:
        import requests

        try:
            port = self.vmix_api_port_var.get().strip() or "8088"
            url = f"http://127.0.0.1:{port}/api"
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                inputs_elem = root.find("inputs")
                input_count = len(list(inputs_elem)) if inputs_elem is not None else 0
                fps_raw = root.findtext("masterFrameRate", "") or root.findtext("frameRate", "") or root.findtext("outputFrameRate", "")
                if not fps_raw and inputs_elem is not None:
                    first_inp = inputs_elem.find("input")
                    if first_inp is not None:
                        fps_raw = first_inp.get("framerate", "") or first_inp.get("frameRate", "") or first_inp.get("fps", "")

                fps_str = self._fps_from_api_value(fps_raw)

                h = root.get("height", "") or root.findtext("height", "") or root.findtext("outputHeight", "")
                if not h and inputs_elem is not None:
                    first_inp = inputs_elem.find("input")
                    if first_inp is not None:
                        h = first_inp.get("height", "")

                resolution = f"{h}p{fps_str}" if h else (fps_str if fps_str != "—" else "—")
                srt_by_port = {}
                srt_quality = "—"
                preset_path = root.findtext("preset", "") or root.findtext("Preset", "")
                if preset_path:
                    preset_res, preset_srt = self._parse_resolution_and_srt_from_preset(preset_path)
                    if resolution == "—" and preset_res != "—":
                        resolution = preset_res
                    if preset_srt:
                        srt_by_port = preset_srt
                else:
                    _, srt_by_port = self.get_res_and_srt_from_file()

                if resolution == "—":
                    file_res, file_srt = self.get_res_and_srt_from_file()
                    if file_res != "—":
                        resolution = file_res
                    if not srt_by_port and file_srt:
                        srt_by_port = file_srt
                return {
                    "connected": True,
                    "recording": root.findtext("recording", "False").strip() == "True",
                    "streaming": root.findtext("streaming", "False").strip() == "True",
                    "external": root.findtext("external", "False").strip() == "True",
                    "fullscreen": root.findtext("fullscreen", "False").strip() == "True",
                    "version": root.findtext("version", "—"),
                    "edition": root.findtext("edition", "—"),
                    "input_count": input_count,
                    "fps": fps_str,
                    "resolution": resolution,
                    "srt_quality": srt_quality,
                    "srt_by_port": srt_by_port,
                }
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass
        except Exception as e:
            self.log(f"[vMix] Error: {e}")

        res_from_file = self.get_vmix_resolution_from_file()
        return {
            "connected": False,
            "recording": False,
            "streaming": False,
            "external": False,
            "fullscreen": False,
            "version": "—",
            "edition": "—",
            "input_count": 0,
            "fps": "—",
            "resolution": res_from_file,
            "srt_quality": "—",
            "srt_by_port": {},
        }

    def is_vmix_on_port(self, port):
        try:
            import psutil

            port_int = int(port)
            for conn in psutil.net_connections(kind="udp"):
                if conn.laddr and conn.laddr.port == port_int and conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        if "vmix" in proc.name().lower():
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            return False
        except Exception as e:
            self.log(f"ERROR kiểm tra vMix: {str(e)}")
            return False

    def get_wan_ip(self):
        return "127.0.0.1"

    def monitor_loop(self):
        import requests

        ip = self.ip_var.get().strip()
        if not ip or not self.port_list:
            self.log("ERROR: IP hoặc danh sách port trống!")
            self.is_running = False
            self.start_btn.config(text="START", bg="#4CAF50")
            return

        wan_ip = self.get_wan_ip()
        prev_status = {}
        last_wan_check = datetime.now(VIETNAM_TZ)
        last_ip_check = datetime.now(VIETNAM_TZ)
        wan_refresh_sec = 30
        ip_check_sec = 5
        self.log(f"Bắt đầu giám sát {len(self.port_list)} port(s)...")

        while self.is_running:
            now = datetime.now(VIETNAM_TZ)

            if (now - last_ip_check).total_seconds() >= ip_check_sec:
                new_local_ip = self.get_local_ip()
                if new_local_ip != ip:
                    self.log(f"🔄 Phát hiện IP thay đổi: {ip} → {new_local_ip}")
                    ip = new_local_ip
                    self.root.after(0, lambda: self.ip_var.set(new_local_ip))
                    for entry in self.port_list:
                        entry["ip"] = new_local_ip
                    self.root.after(0, self.update_table_display)
                last_ip_check = now

            if (now - last_wan_check).total_seconds() >= wan_refresh_sec:
                new_wan = self.get_wan_ip()
                if new_wan != wan_ip:
                    self.log(f"🌐 WAN IP thay đổi: {wan_ip} → {new_wan}")
                    wan_ip = new_wan
                    for entry in self.port_list:
                        entry["ipwan"] = new_wan
                    self.root.after(0, self.update_table_display)
                last_wan_check = now

            with self._ping_lock:
                ping_ms = self._ping_ms
            cpu_pct = self.measure_cpu()
            mem_pct = self.measure_memory()
            gpu_pct = self.measure_gpu()
            sender_mbps, receiver_mbps = self.measure_network_sender_receiver_mbps()

            vmix_stats = self.get_vmix_stats()
            ping_str = f"{ping_ms:.0f}" if ping_ms is not None else "—"
            timeout_str = str(self.ping_timeout_count)
            cpu_str = f"{cpu_pct:.1f}" if cpu_pct is not None else "—"
            mem_str = f"{mem_pct:.1f}" if mem_pct is not None else "—"
            gpu_str = f"{gpu_pct:.1f}" if gpu_pct is not None else "—"
            sender_bw_str = self._format_mbps_text(sender_mbps)
            receiver_bw_str = self._format_mbps_text(receiver_mbps)

            rec_str = "🔴 ON" if vmix_stats["recording"] else "OFF"
            live_str = "🔴 ON" if vmix_stats["streaming"] else "OFF"
            ext_str = "🟢 ON" if vmix_stats["external"] else "OFF"
            res_str = vmix_stats.get("resolution", "—") or "—"
            srt_by_port = vmix_stats.get("srt_by_port", {})
            if not srt_by_port:
                _, srt_by_port = self.get_res_and_srt_from_file()
            srt_fallback = next(iter(srt_by_port.values()), "—")

            for entry in self.port_list:
                port = entry["port"]
                name = entry["name"]
                srt_str = srt_by_port.get(port, srt_fallback)

                entry["ping"] = ping_str
                entry["timeout"] = timeout_str
                entry["cpu"] = cpu_str
                entry["memory"] = mem_str
                entry["gpu"] = gpu_str
                entry["sender_bw"] = sender_bw_str
                entry["receiver_bw"] = receiver_bw_str
                entry["rec"] = rec_str
                entry["live"] = live_str
                entry["ext"] = ext_str
                entry["resolution"] = res_str
                entry["srt"] = srt_str

                vmix_running = self.is_vmix_on_port(port)
                current_status = "ON" if vmix_running else "OFF"
                try:
                    data = {
                        "name": name,
                        "ip": ip,
                        "ipwan": wan_ip,
                        "status": current_status,
                        "port": port,
                        "statusapp": 1,
                        "ping": ping_ms,
                        "ping_timeouts": self.ping_timeout_count,
                        "temperature": cpu_pct,
                        "memory": mem_pct,
                        "gpu": gpu_pct,
                        "sender_mbps": sender_mbps,
                        "receiver_mbps": receiver_mbps,
                        "vmix_recording": vmix_stats.get("recording", False),
                        "vmix_streaming": vmix_stats.get("streaming", False),
                        "vmix_external": vmix_stats.get("external", False),
                        "resolution": res_str,
                        "srt_quality": srt_str,
                    }
                    headers = {"Content-Type": "application/json"}
                    response = self.http_session.post(SERVER_URL, json=data, headers=headers, timeout=5)
                    if response.status_code == 200:
                        if prev_status.get(port) != current_status:
                            icon = "🟢" if current_status == "ON" else "🔴"
                            self.log(f"{icon} SRT {current_status}: {name} {ip}:{port}")
                            prev_status[port] = current_status
                    elif response.status_code == 500:
                        self.log(f"⚠️ Server error 500 ({name})")
                    else:
                        self.log(f"❌ HTTP {response.status_code} gửi {name}")
                except requests.exceptions.Timeout:
                    self.log(f"⏱️ Timeout gửi {name}")
                except requests.exceptions.ConnectionError:
                    self.log(f"❌ Mất kết nối ({name})")
                except Exception as e:
                    self.log(f"❌ ERROR {name}: {str(e)}")

            self.root.after(0, self.update_table_display)

            for _ in range(10):
                if not self.is_running:
                    break
                time.sleep(0.1)
