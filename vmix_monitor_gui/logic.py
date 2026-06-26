import glob
import html
import json
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
import urllib.parse

try:
    from .shared import SERVER_URL, VIETNAM_TZ
except ImportError:
    try:
        from vmix_monitor_gui.shared import SERVER_URL, VIETNAM_TZ
    except ImportError:
        from shared import SERVER_URL, VIETNAM_TZ


class VmixMonitorLogicMixin:
    def get_server_url(self) -> str:
        raw = SERVER_URL
        var = getattr(self, "server_url_var", None)
        if var is not None:
            raw = str(var.get() or "").strip() or SERVER_URL

        normalized = str(raw).strip().rstrip("/")
        if not normalized:
            normalized = SERVER_URL

        if not normalized.startswith(("http://", "https://")):
            normalized = f"http://{normalized}"

        return normalized.rstrip("/")

    def apply_server_url(self):
        url = self.get_server_url()
        if hasattr(self, "server_url_var"):
            self.server_url_var.set(url)
        self.log(f"🌐 Server URL: {url}")

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
        if value_mbps < 1:
            return f"{value_mbps * 1000:.0f} kbps"
        if value_mbps >= 100:
            return f"{value_mbps:.0f} Mbps"
        if value_mbps >= 10:
            return f"{value_mbps:.1f} Mbps"
        return f"{value_mbps:.2f} Mbps"

    @staticmethod
    def _format_fps_value(fps_val: float) -> str:
        std_fps = (
            (23.976, "23.976"),
            (24.0, "24"),
            (25.0, "25"),
            (29.97, "29.97"),
            (30.0, "30"),
            (50.0, "50"),
            (59.94, "59.94"),
            (60.0, "60"),
        )
        closest_std, closest_label = min(std_fps, key=lambda item: abs(fps_val - item[0]))
        if abs(fps_val - closest_std) < 0.1:
            return closest_label
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

    @staticmethod
    def _fmt_link_speed_mbps(speed_mbps) -> str:
        try:
            speed = float(speed_mbps or 0)
        except (TypeError, ValueError):
            return "—"

        if speed <= 0:
            return "—"
        if speed >= 1000:
            return f"{speed / 1000:.2f} Gbps"
        return f"{speed:.0f} Mbps"

    def _get_primary_network_info(self) -> tuple[str, str]:
        try:
            import psutil
        except Exception:
            return "—", "—"

        local_ip = str(getattr(self, "ip_var", None).get() if getattr(self, "ip_var", None) else "").strip()
        stats_map = psutil.net_if_stats()
        addrs_map = psutil.net_if_addrs()

        def _extract_mac(addrs) -> str:
            for addr in addrs:
                fam = addr.family
                fam_text = str(fam)
                if fam_text in {"17", "18", "-1"} or "AF_LINK" in fam_text:
                    mac = str(getattr(addr, "address", "") or "").strip()
                    if mac:
                        return mac.upper()
            return ""

        preferred = None
        fallback = None
        for name, stat in stats_map.items():
            addrs = addrs_map.get(name, [])
            mac = _extract_mac(addrs)
            ipv4s = []
            for addr in addrs:
                if str(addr.family) in {"2"} or "AF_INET" in str(addr.family):
                    ipv4s.append(str(getattr(addr, "address", "") or "").strip())

            item = {
                "name": name,
                "mac": mac or "—",
                "speed": self._fmt_link_speed_mbps(getattr(stat, "speed", 0)),
                "ipv4s": ipv4s,
            }

            if not fallback:
                fallback = item
            if local_ip and local_ip in ipv4s:
                preferred = item
                break

        chosen = preferred or fallback
        if not chosen:
            return "—", "—"

        return chosen["mac"], chosen["speed"]

    def _get_primary_interface_name(self) -> str | None:
        try:
            import psutil
        except Exception:
            return None

        local_ip = str(getattr(self, "ip_var", None).get() if getattr(self, "ip_var", None) else "").strip()
        stats_map = psutil.net_if_stats()
        addrs_map = psutil.net_if_addrs()

        preferred = None
        fallback = None
        for name, stat in stats_map.items():
            if not getattr(stat, "isup", True):
                continue
            addrs = addrs_map.get(name, [])
            ipv4s = []
            for addr in addrs:
                if str(addr.family) in {"2"} or "AF_INET" in str(addr.family):
                    ip_text = str(getattr(addr, "address", "") or "").strip()
                    if ip_text:
                        ipv4s.append(ip_text)

            if local_ip and local_ip in ipv4s:
                preferred = name
                break

            if not fallback:
                for ip_text in ipv4s:
                    if not ip_text.startswith("127."):
                        fallback = name
                        break

        if preferred:
            return preferred
        if fallback:
            return fallback
        return next(iter(stats_map), None)

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
        # Use short socket timeouts to avoid blocking GUI startup on unstable networks.
        probes = (("1.1.1.1", 80), ("8.8.8.8", 80))
        for host, port in probes:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.8)
                s.connect((host, port))
                ip = s.getsockname()[0]
                s.close()
                if ip:
                    return ip
            except Exception:
                pass

        try:
            host_ip = socket.gethostbyname(socket.gethostname())
            if host_ip and host_ip != "127.0.0.1":
                return host_ip
        except Exception:
            pass

        return "127.0.0.1"

    def import_from_old_ip(self, old_ip: str):
        import requests

        try:
            current_ip = self.ip_var.get().strip()
            if old_ip == current_ip:
                self.log("⚠️ IP cũ và IP mới giống nhau!")
                return

            self.log(f"📥 Đang import data từ IP {old_ip}...")
            url = f"{self.get_server_url()}/get_by_ip?ip={old_ip}"
            response = requests.get(url, timeout=20)

            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list):
                    imported_count = 0
                    for entry in data:
                        entry_data = entry.get("data", {})
                        srt_list = entry_data.get("SRT", [])
                        if not isinstance(srt_list, list):
                            srt_list = [srt_list] if isinstance(srt_list, dict) else []
                        ipwan = entry_data.get("ipwan", "unknown")

                        for srt_item in srt_list:
                            name = srt_item.get("nameSRT", "")
                            port = srt_item.get("port", 0)
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
                                            "vmixsend": "—",
                                            "vmixreceive": "—",
                                            "pid_vmix": "—",
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
                                            port,
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
            url = f"{self.get_server_url()}/update_ip"
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
                url = f"{self.get_server_url()}/update_ip"
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
            url = f"{self.get_server_url()}/logs"
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

    def load_data_from_database_async(self):
        ip = self.ip_var.get().strip()
        server_url = self.get_server_url()
        threading.Thread(
            target=self.load_data_from_database,
            args=(ip, server_url),
            daemon=True,
        ).start()

    def load_data_from_database(self, ip: str | None = None, server_url: str | None = None):
        import requests

        try:
            current_ip = (ip or self.ip_var.get().strip()).strip()
            base_url = str(server_url or self.get_server_url()).rstrip("/")
            url = f"{base_url}/get_by_ip?ip={current_ip}"
            self.log("⏳ Đang tải dữ liệu từ server...")
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                data = response.json()
                self.root.after(0, lambda d=data, local_ip=current_ip: self._apply_loaded_data_to_ui(local_ip, d))
            elif response.status_code == 500:
                self.log("⚠️ Server đang có vấn đề (500) - có thể đang cold start, hãy thử lại sau 30s")
            else:
                self.log(f"❌ Không thể tải dữ liệu: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            self.log("⏱️ Timeout khi tải dữ liệu - server có thể đang ngủ, hãy đợi 30-60s")
        except Exception as e:
            self.log(f"❌ Lỗi khi load dữ liệu: {str(e)}")

    def _apply_loaded_data_to_ui(self, ip: str, data):
        if data and isinstance(data, list):
            self.port_list.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)

            loaded_count = 0
            for entry in data:
                entry_data = entry.get("data", {})
                entry_ip = entry_data.get("ip", ip)
                ipwan = entry_data.get("ipwan", "unknown")
                ping = entry_data.get("ping", None)
                memory = entry_data.get("memory", None)
                cpu = entry_data.get("cpu", None)
                gpu = entry_data.get("gpu", None)
                sender_mbps = entry_data.get("sender_mbps", None)
                receiver_mbps = entry_data.get("receiver_mbps", None)
                vmixsend_mbps = entry_data.get("vmixsend", None)
                vmixreceive_mbps = entry_data.get("vmixreceive", None)
                pid_vmix = str(entry_data.get("PIDVMIX", "") or "")

                # SRT is now an array
                srt_list = entry_data.get("SRT", [])
                if not isinstance(srt_list, list):
                    srt_list = [srt_list] if isinstance(srt_list, dict) else []

                for srt_item in srt_list:
                    if not isinstance(srt_item, dict):
                        continue
                    title = srt_item.get("title", "")
                    name_srt = srt_item.get("nameSRT", "")
                    # Nếu có custom name và không bằng title thì load về, ngược lại bỏ qua (để trống)
                    if title and name_srt and name_srt != title:
                        self._srt_ext_custom_names[title] = name_srt

                    name = srt_item.get("nameSRT", "")
                    port = srt_item.get("port", 0)
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
                                "vmixsend": self._format_mbps_text(self._to_float_or_none(vmixsend_mbps)),
                                "vmixreceive": self._format_mbps_text(self._to_float_or_none(vmixreceive_mbps)),
                                "pid_vmix": pid_vmix if pid_vmix else "—",
                                "rec": "—",
                                "live": "—",
                                "ext": "—",
                                "resolution": "—",
                                "srt": "—",
                            }
                        )
                        srt_quality = srt_item.get("quality", "—")
                        srt_status = srt_item.get("status", "—")
                        self.tree.insert(
                            "",
                            tk.END,
                            values=(
                                name,
                                port,
                                srt_quality,
                                srt_status,
                            ),
                        )
                        loaded_count += 1

            if loaded_count > 0:
                self.log(f"✅ Đã tải {loaded_count} port từ database (IP: {ip})")
            else:
                self.log(f"ℹ️ Không có dữ liệu cho IP {ip} trong database")
                self.check_for_old_ip_data(ip)
        else:
            self.log(f"ℹ️ Không có dữ liệu cho IP {ip} trong database")
            self.check_for_old_ip_data(ip)

    def check_for_old_ip_data(self, current_ip: str | None = None):
        ip = (current_ip or self.ip_var.get().strip()).strip()
        server_url = self.get_server_url()
        threading.Thread(
            target=self._check_for_old_ip_data_thread,
            args=(ip, server_url),
            daemon=True,
        ).start()

    def _check_for_old_ip_data_thread(self, current_ip: str, server_url: str):
        import requests

        try:
            url = f"{server_url.rstrip('/')}/logs"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                all_data = response.json()
                if all_data and isinstance(all_data, list):
                    found_ips = set()
                    for entry in all_data:
                        entry_data = entry.get("data", {})
                        entry_ip = entry_data.get("ip", "")
                        if entry_ip and entry_ip != current_ip:
                            found_ips.add(entry_ip)
                    if found_ips:
                        self.root.after(1000, lambda ips=sorted(found_ips): self.show_old_ip_notification(ips))
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
                "mac_address": "—",
                "network_speed": "—",
                "sender_bw": "—",
                "receiver_bw": "—",
                "vmixsend": "—",
                "vmixreceive": "—",
                "pid_vmix": "—",
                "rec": "—",
                "live": "—",
                "ext": "—",
                "resolution": "—",
                "srt": "—",
                "srt_status": "OFF",
            }
        )
        self.tree.insert("", tk.END, values=(name, port, "—", "—"))

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
            data = {"name": name, "ip": ip}
            url = f"{self.get_server_url()}/delete"
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=15)
            if response.status_code == 200:
                self.log(f"🗑️ Đã xóa trên DB: {name}")
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

        ip = self.ip_var.get().strip()
        if not ip:
            return

        try:
            wan_ip = self.get_wan_ip()
            machine_name = socket.gethostname()

            # Build SRT array from auto-scan external outputs
            srt_list = []
            custom_names = getattr(self, "_srt_ext_custom_names", {})
            srt_ext_data = getattr(self, "_srt_ext_latest_data", [])
            for ext_entry in srt_ext_data:
                if not ext_entry.get("port"):
                    continue
                title = ext_entry.get("title", "")
                srt_status = "OFF" if self.is_network_offline() else ext_entry.get("srt_enabled_label", "OFF")
                srt_list.append({
                    "nameSRT": custom_names.get(title, ""),
                    "port": ext_entry.get("port", 0),
                    "quality": ext_entry.get("quality", "—"),
                    "status": srt_status,
                    "type": ext_entry.get("srt_type_label", "—"),
                    "hostname": ext_entry.get("hostname", ""),
                    "stream_id": ext_entry.get("stream_id", ""),
                    "title": title,
                })

            data = {
                "name": machine_name,
                "ip": ip,
                "ipwan": wan_ip,
                "statusapp": status_value,
                "SRT": srt_list,
                "stream": [],
            }
            url = self.get_server_url()
            headers = {"Content-Type": "application/json"}

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(url, json=data, headers=headers, timeout=15)
                    if response.status_code == 200:
                        status_text = "ON" if status_value == 1 else "OFF"
                        self.log(f"✅ App status {status_text}: {len(srt_list)} SRT streams")
                        break
                    elif response.status_code == 500:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            self.log(f"⚠️ Server error 500, retry sau {wait_time}s... (lần {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            self.log(f"❌ Lỗi 500 gửi app status")
                    else:
                        self.log(f"❌ Lỗi gửi app status: HTTP {response.status_code}")
                        break
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        self.log(f"⏱️ Timeout gửi app status, retry...")
                        time.sleep(2)
                    else:
                        self.log(f"❌ Timeout sau {max_retries} lần thử")
                except requests.exceptions.ConnectionError:
                    self.log(f"❌ Không kết nối được server")
                    break
        except Exception as e:
            self.log(f"❌ ERROR gửi app status: {str(e)}")

    def toggle_monitoring(self):
        if not self.is_running:
            self.is_running = True
            self.ping_timeout_count = 0
            self.start_btn.config(text="⏹️ STOP MONITORING", bootstyle="danger")
            self.status_label.config(text="● Running", bootstyle="success")
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
                else:
                    self.ping_timeout_count = 0
            time.sleep(3)

    def is_network_offline(self) -> bool:
        with self._ping_lock:
            return (self._ping_ms is None) or (self.ping_timeout_count > 10)

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
        except Exception:
            return None, None

        iface = self._get_primary_interface_name()
        try:
            pernic = psutil.net_io_counters(pernic=True)
        except Exception:
            pernic = {}

        if iface and iface in pernic:
            counters = pernic[iface]
            key = iface
        else:
            counters = psutil.net_io_counters()
            key = "__total__"

        sent_now = int(getattr(counters, "bytes_sent", 0) or 0)
        recv_now = int(getattr(counters, "bytes_recv", 0) or 0)
        ts_now = time.time()

        if not hasattr(self, "_net_last_by_iface"):
            self._net_last_by_iface = {}

        last_state = self._net_last_by_iface.get(key)
        if not last_state:
            self._net_last_by_iface[key] = (sent_now, recv_now, ts_now)
            return None, None

        last_sent, last_recv, last_ts = last_state
        dt = max(ts_now - float(last_ts or 0.0), 1e-6)
        sent_diff = max(sent_now - int(last_sent or 0), 0)
        recv_diff = max(recv_now - int(last_recv or 0), 0)

        self._net_last_by_iface[key] = (sent_now, recv_now, ts_now)

        sender_mbps = (sent_diff * 8) / dt / 1_000_000
        receiver_mbps = (recv_diff * 8) / dt / 1_000_000
        return round(sender_mbps, 3), round(receiver_mbps, 3)

    def get_network_card_summary(self) -> tuple[str, str]:
        """Return MAC address and link speed for the primary network interface."""
        try:
            return self._get_primary_network_info()
        except Exception:
            return "—", "—"

    def _run_powershell_json(self, command: str):
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode != 0:
                return None

            output = (result.stdout or "").strip()
            if not output:
                return None

            return json.loads(output)
        except Exception:
            return None

    def measure_vmix_pid_and_bandwidth_mbps(self) -> tuple[str, float | None, float | None]:
        """Return vMix PID list plus process send/receive bandwidth (Mbps)."""
        now = time.time()
        cache_ts = float(getattr(self, "_vmix_bw_cache_ts", 0.0) or 0.0)
        if now - cache_ts < 1.0:
            return (
                str(getattr(self, "_vmix_bw_cache_pid", "") or ""),
                getattr(self, "_vmix_bw_cache_send", None),
                getattr(self, "_vmix_bw_cache_recv", None),
            )

        try:
            import psutil
        except Exception:
            return "", None, None

        pids: list[int] = []
        try:
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    pid = int(proc.info.get("pid") or 0)
                    if pid <= 0:
                        continue
                    pname = str(proc.info.get("name") or "").lower().strip()
                    pexe = str(proc.info.get("exe") or "")
                    exe_name = os.path.basename(pexe).lower().strip() if pexe else ""
                    if pname == "vmix64.exe" or exe_name == "vmix64.exe":
                        pids.append(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception:
                    continue
        except Exception:
            return "", None, None

        pids = sorted(set(pids))
        if not pids:
            self._vmix_bw_cache_ts = now
            self._vmix_bw_cache_pid = ""
            self._vmix_bw_cache_send = None
            self._vmix_bw_cache_recv = None
            return "", None, None

        raw = self._run_powershell_json(
            r"""
Get-CimInstance Win32_PerfFormattedData_PerfProc_Process |
  Where-Object { $_.IDProcess -gt 0 -and $_.Name -ne '_Total' -and $_.Name -ne 'Idle' } |
  Select-Object IDProcess,IOReadBytesPersec,IOWriteBytesPersec |
  ConvertTo-Json -Compress
"""
        )
        rows = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
        if not rows:
            pid_text = ",".join(str(pid) for pid in pids)
            self._vmix_bw_cache_ts = now
            self._vmix_bw_cache_pid = pid_text
            self._vmix_bw_cache_send = None
            self._vmix_bw_cache_recv = None
            return pid_text, None, None

        want_pids = set(pids)
        send_bps = 0.0
        recv_bps = 0.0
        for item in rows:
            if not isinstance(item, dict):
                continue
            try:
                pid = int(item.get("IDProcess", 0) or 0)
            except Exception:
                continue
            if pid not in want_pids:
                continue
            try:
                recv_bps += max(float(item.get("IOReadBytesPersec", 0) or 0), 0.0)
            except Exception:
                pass
            try:
                send_bps += max(float(item.get("IOWriteBytesPersec", 0) or 0), 0.0)
            except Exception:
                pass

        send_mbps = round((send_bps * 8) / 1_000_000, 3)
        recv_mbps = round((recv_bps * 8) / 1_000_000, 3)
        pid_text = ",".join(str(pid) for pid in pids)

        self._vmix_bw_cache_ts = now
        self._vmix_bw_cache_pid = pid_text
        self._vmix_bw_cache_send = send_mbps
        self._vmix_bw_cache_recv = recv_mbps
        return pid_text, send_mbps, recv_mbps

    def measure_ffmpeg_bandwidth_list(self) -> list[dict]:
        """Return list of dicts: {name, pid, send, recv} for all ffmpeg processes."""
        try:
            import psutil
        except ImportError:
            return []

        ffmpeg_pids = []
        pid_to_name = {}
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    name = str(proc.info.get("name") or "")
                    if name.lower().startswith("ffmpeg"):
                        pid = int(proc.info.get("pid") or 0)
                        if pid > 0:
                            ffmpeg_pids.append(pid)
                            pid_to_name[pid] = name
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            return []

        if not ffmpeg_pids:
            return []

        raw = self._run_powershell_json(
            r"""
Get-CimInstance Win32_PerfFormattedData_PerfProc_Process |
  Where-Object { $_.IDProcess -gt 0 -and $_.Name -ne '_Total' -and $_.Name -ne 'Idle' } |
  Select-Object IDProcess,IOReadBytesPersec,IOWriteBytesPersec |
  ConvertTo-Json -Compress
"""
        )
        if not raw:
            return [{"name": pid_to_name[p], "pid": p, "send": 0.0, "recv": 0.0} for p in ffmpeg_pids]

        rows = raw if isinstance(raw, list) else [raw]
        pid_stats = {}
        for item in rows:
            if not isinstance(item, dict):
                continue
            try:
                pid = int(item.get("IDProcess", 0))
                if pid in pid_to_name:
                    send_mbps = (float(item.get("IOWriteBytesPersec", 0) or 0) * 8) / 1_000_000
                    recv_mbps = (float(item.get("IOReadBytesPersec", 0) or 0) * 8) / 1_000_000
                    pid_stats[pid] = {"send": send_mbps, "recv": recv_mbps}
            except Exception:
                continue

        results = []
        for pid in sorted(ffmpeg_pids):
            stats = pid_stats.get(pid, {"send": 0.0, "recv": 0.0})
            results.append({
                "name": pid_to_name[pid],
                "pid": pid,
                "send": stats["send"],
                "recv": stats["recv"]
            })
        return results

    def update_ffmpeg_table(self, ffmpeg_list: list[dict]):
        if not hasattr(self, "ffmpeg_tree"):
            return
        tree = self.ffmpeg_tree
        for item in tree.get_children():
            tree.delete(item)
        for entry in ffmpeg_list:
            tree.insert("", tk.END, values=(
                entry["name"],
                entry["pid"],
                f"{entry['send']:.3f} Mbps",
                f"{entry['recv']:.3f} Mbps"
            ))

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

        # Use cached preset path from process scan (already updated every 10s)
        if not project_file:
            cached = getattr(self, "_proc_cache_preset", None)
            if cached and os.path.isfile(cached):
                project_file = cached

        # Also check cached API preset path
        if not project_file:
            cached_api = getattr(self, "_api_preset_path", None)
            if cached_api and os.path.isfile(cached_api):
                project_file = cached_api

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

    def _find_latest_studiocoast_config(self) -> str | None:
        """Find the latest user.config file for vMix from LocalAppData\\StudioCoast_Pty_Ltd.

        Searches ALL user profiles on the machine, not just the current user,
        so the config is found even when vMix runs under a different account.

        Uses a cached path list to avoid expensive os.walk on every call.
        Full re-scan of the directory tree every _SC_CONFIG_TTL seconds (default 60s).
        Between re-scans, just picks the most-recently-modified file from the cached list.
        """
        now = time.time()
        ttl = getattr(self, "_SC_CONFIG_TTL", 60.0)
        cached_paths = getattr(self, "_sc_config_paths", [])
        cached_ts = getattr(self, "_sc_config_paths_ts", 0.0)

        # ── Re-discover paths if cache is stale or empty ───────────────────
        if not cached_paths or (now - cached_ts) >= ttl:
            config_files: list[str] = []

            # Collect all candidate StudioCoast directories across every user profile
            studiocoast_dirs: list[str] = []

            # 1) Current user's %LOCALAPPDATA% (always try first)
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                sc = os.path.join(local_appdata, "StudioCoast_Pty_Ltd")
                if os.path.isdir(sc):
                    studiocoast_dirs.append(sc)

            # 2) Scan all user profiles on the machine
            #    e.g. C:\Users\<each_user>\AppData\Local\StudioCoast_Pty_Ltd
            try:
                sys_drive = os.environ.get("SystemDrive") or "C:"
                users_root = os.path.join(sys_drive + os.sep, "Users")
                if os.path.isdir(users_root):
                    for user_dir in os.listdir(users_root):
                        user_path = os.path.join(users_root, user_dir)
                        if not os.path.isdir(user_path):
                            continue
                        sc = os.path.join(user_path, "AppData", "Local", "StudioCoast_Pty_Ltd")
                        if os.path.isdir(sc) and sc not in studiocoast_dirs:
                            studiocoast_dirs.append(sc)
            except Exception:
                pass

            # Walk each StudioCoast directory for user.config files
            for studiocoast_dir in studiocoast_dirs:
                try:
                    for root_dir, _, filenames in os.walk(studiocoast_dir):
                        root_lower = root_dir.lower()
                        if "vmix64.exe_url_" in root_lower or "vmix.exe_url_" in root_lower:
                            for f in filenames:
                                if f.lower() == "user.config":
                                    full = os.path.join(root_dir, f)
                                    if full not in config_files:
                                        config_files.append(full)
                except (PermissionError, OSError):
                    continue

            # Fallback: glob under each StudioCoast dir
            if not config_files:
                for studiocoast_dir in studiocoast_dirs:
                    try:
                        config_files.extend(
                            glob.glob(
                                os.path.join(studiocoast_dir, "**", "user.config"),
                                recursive=True,
                            )
                        )
                    except (PermissionError, OSError):
                        continue

            self._sc_config_paths = config_files
            self._sc_config_paths_ts = now

        # ── Pick the most recent file that still exists ────────────────────
        paths = getattr(self, "_sc_config_paths", [])
        valid = [p for p in paths if os.path.isfile(p)]
        if not valid:
            return None
        return max(valid, key=os.path.getmtime)

    def _parse_srt_external_outputs(self) -> list[dict]:
        """Parse all OutputsExternal blocks to extract detailed SRT info.

        Returns a list of dicts, one per OutputsExternal block found, with keys:
          title, srt_enabled, srt_enabled_label, srt_type, srt_type_label,
          hostname, port, stream_id, codec, video_bw, audio_bw, hw_encoder, quality

        When vMix process is not running, all SRT Enabled are forced to OFF.
        """
        results: list[dict] = []

        now = time.time()

        # ── Cached psutil process check (alive + preset path from cmdline) ──
        proc_ttl = getattr(self, "_PROC_CACHE_TTL", 10.0)
        if (now - getattr(self, "_proc_cache_ts", 0.0)) >= proc_ttl:
            _alive = False
            _preset_from_proc: str | None = None
            try:
                import psutil
                for proc in psutil.process_iter(["name", "cmdline"]):
                    try:
                        pname = (proc.info.get("name") or "").lower()
                        if pname in ("vmix64.exe", "vmix.exe"):
                            _alive = True
                            for arg in (proc.info.get("cmdline") or []):
                                if arg.lower().endswith(".vmix") and os.path.isfile(arg):
                                    _preset_from_proc = arg
                                    break
                            if _preset_from_proc:
                                break
                    except Exception:
                        pass
            except Exception:
                pass
            self._proc_cache_alive = _alive
            self._proc_cache_preset = _preset_from_proc
            self._proc_cache_ts = now

        vmix_alive = getattr(self, "_proc_cache_alive", False)
        self._vmix_process_alive = vmix_alive

        # ── Source 0: manual override from user (Browse / paste) ────────────
        preset_root = None
        preset_source_path = None
        manual_path = getattr(self, "_manual_config_path", None)
        if manual_path and os.path.isfile(manual_path):
            try:
                if manual_path.lower().endswith(".vmix"):
                    preset_root = ET.parse(manual_path).getroot()
                    preset_source_path = manual_path
                else:
                    # It's a .config file — skip preset parsing, go directly to config fallback
                    if hasattr(self, "config_path_var"):
                        self.config_path_var.set(manual_path)
                    return self._parse_config_file_srt(manual_path, vmix_alive)
            except Exception:
                pass

        # ── Source 1: user.config (StudioCoast) or current.config ──────────
        #    Highest auto priority for SRT — contains actual saved SRT settings
        if preset_root is None:
            config_file = self._find_latest_studiocoast_config()
            if not config_file or not os.path.isfile(config_file):
                vmix_dir = self._vmix_data_dir()
                fallback = os.path.join(vmix_dir, "settingbackups", "current.config")
                if os.path.isfile(fallback):
                    config_file = fallback

            if config_file and os.path.isfile(config_file):
                if hasattr(self, "config_path_var"):
                    self.config_path_var.set(config_file)
                return self._parse_config_file_srt(config_file, vmix_alive)

        # ── Source 2: preset file from vMix API (cached path) ───────────────
        api_ttl = getattr(self, "_API_PRESET_TTL", 15.0)
        cached_api_path = getattr(self, "_api_preset_path", None)

        # Reuse cached API preset path if still valid
        if cached_api_path and os.path.isfile(cached_api_path) and (now - getattr(self, "_api_preset_ts", 0.0)) < api_ttl:
            try:
                preset_root = ET.parse(cached_api_path).getroot()
                preset_source_path = cached_api_path
            except Exception:
                pass

        # Re-query API if cache expired or invalid
        if preset_root is None and (now - getattr(self, "_api_preset_ts", 0.0)) >= api_ttl:
            self._api_preset_ts = now  # update timestamp regardless of result
            try:
                import requests as req
                port_str = self.vmix_api_port_var.get().strip() or "8088"
                url = f"http://127.0.0.1:{port_str}/api"
                resp = req.get(url, timeout=2)
                if resp.status_code == 200:
                    api_root = ET.fromstring(resp.content)
                    preset_path = api_root.findtext("preset", "") or api_root.findtext("Preset", "")
                    if preset_path and os.path.isfile(preset_path):
                        self._api_preset_path = preset_path
                        try:
                            preset_root = ET.parse(preset_path).getroot()
                            preset_source_path = preset_path
                        except Exception:
                            pass
            except Exception:
                pass

        # ── Source 3: preset from cached process cmdline ────────────────────
        if preset_root is None:
            proc_preset = getattr(self, "_proc_cache_preset", None)
            if proc_preset and os.path.isfile(proc_preset):
                try:
                    preset_root = ET.parse(proc_preset).getroot()
                    preset_source_path = proc_preset
                except Exception:
                    pass

        # ── Source 4: fallback — glob for *.vmix files (least reliable) ────
        if preset_root is None:
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
                    latest_file = max(candidates, key=os.path.getmtime)
                    preset_root = ET.parse(latest_file).getroot()
                    preset_source_path = latest_file
            except Exception:
                pass

        # ── Parse from preset XML (direct element access) ──────────────────────
        if preset_root is not None:
            if hasattr(self, "config_path_var") and preset_source_path:
                self.config_path_var.set(preset_source_path)

            for idx, ext_name in enumerate(
                ("OutputsExternal", "OutputsExternal2", "OutputsExternal3", "OutputsExternal4"), start=1
            ):
                ext = preset_root.find(f".//{ext_name}")
                if ext is None:
                    continue

                enabled = (ext.findtext("SRTEnabled") or "0").strip()
                srt_type = (ext.findtext("SRTType") or "").strip()
                hostname = (ext.findtext("SRTHostname") or "").strip()
                port_str_val = (ext.findtext("SRTPort") or "0").strip()
                stream_id = (ext.findtext("SRTStreamID") or "").strip()

                try:
                    port_val = int(port_str_val)
                except ValueError:
                    port_val = 0

                enabled_lbl = "ON" if enabled == "1" else "OFF"
                type_lbl = "Caller" if srt_type == "0" else "Listener"

                codec_id = (ext.findtext("SRTVideoCodec") or "").strip()
                codec = "HEVC" if codec_id == "1" else "H264"
                vbw_s = self._bw_str(ext.findtext("SRTVideoBandwidth") or "0")
                abw_s = self._bw_str(ext.findtext("SRTAudioBandwidth") or "0")
                hw = "HW" if (ext.findtext("SRTHardwareEncoder") or "0").strip() == "1" else ""
                quality = f"{codec} {vbw_s} AAC {abw_s}"
                if hw:
                    quality += f" {hw}"

                results.append({
                    "title": ext_name,
                    "srt_enabled": enabled,
                    "srt_enabled_label": enabled_lbl,
                    "srt_type": srt_type,
                    "srt_type_label": type_lbl,
                    "hostname": hostname,
                    "port": port_val,
                    "port_str": port_str_val,
                    "stream_id": stream_id,
                    "codec": codec,
                    "video_bw": vbw_s,
                    "audio_bw": abw_s,
                    "hw_encoder": hw,
                    "quality": quality,
                })
            if results:
                if not vmix_alive:
                    for entry in results:
                        entry["srt_enabled"] = "0"
                        entry["srt_enabled_label"] = "OFF"
                return results

        # No source found
        if hasattr(self, "config_path_var"):
            self.config_path_var.set("—")
        return results

    def _parse_config_file_srt(self, config_file: str, vmix_alive: bool) -> list[dict]:
        """Parse SRT external output settings from a .config file (user.config or current.config)."""
        results: list[dict] = []
        try:
            content = self._read_file_shared(config_file)
            for idx, ext_name in enumerate(
                ("OutputsExternal", "OutputsExternal2", "OutputsExternal3", "OutputsExternal4"), start=1
            ):
                m = re.search(
                    rf'name="{re.escape(ext_name)}"[^>]*>\s*<value>(.*?)</value>',
                    content, re.DOTALL,
                )
                if not m:
                    continue

                decoded = html.unescape(m.group(1).strip())
                try:
                    sub = ET.fromstring(f"<root>{decoded}</root>")
                except ET.ParseError:
                    continue

                enabled = (sub.findtext("SRTEnabled") or "0").strip()
                srt_type = (sub.findtext("SRTType") or "").strip()
                hostname = (sub.findtext("SRTHostname") or "").strip()
                port_str_val = (sub.findtext("SRTPort") or "0").strip()
                stream_id = (sub.findtext("SRTStreamID") or "").strip()

                try:
                    port_val = int(port_str_val)
                except ValueError:
                    port_val = 0

                enabled_lbl = "ON" if enabled == "1" else "OFF"
                type_lbl = "Caller" if srt_type == "0" else "Listener"

                codec_id = (sub.findtext("SRTVideoCodec") or "").strip()
                codec = "HEVC" if codec_id == "1" else "H264"
                vbw_s = self._bw_str(sub.findtext("SRTVideoBandwidth") or "0")
                abw_s = self._bw_str(sub.findtext("SRTAudioBandwidth") or "0")
                hw = "HW" if (sub.findtext("SRTHardwareEncoder") or "0").strip() == "1" else ""
                quality = f"{codec} {vbw_s} AAC {abw_s}"
                if hw:
                    quality += f" {hw}"

                results.append({
                    "title": ext_name,
                    "srt_enabled": enabled,
                    "srt_enabled_label": enabled_lbl,
                    "srt_type": srt_type,
                    "srt_type_label": type_lbl,
                    "hostname": hostname,
                    "port": port_val,
                    "port_str": port_str_val,
                    "stream_id": stream_id,
                    "codec": codec,
                    "video_bw": vbw_s,
                    "audio_bw": abw_s,
                    "hw_encoder": hw,
                    "quality": quality,
                })
        except Exception:
            pass

        # ── Override: if vMix is not running, force all SRT Enabled to OFF ────
        if not vmix_alive and results:
            for entry in results:
                entry["srt_enabled"] = "0"
                entry["srt_enabled_label"] = "OFF"

        return results

    def auto_scan_srt(self):
        """Start continuous SRT, Record, and Multi Record scanning in a background thread.
        Called automatically on app launch.
        """
        if getattr(self, "_srt_scan_running", False):
            return  # Already running

        self._srt_scan_running = True
        self.log("🔍 Auto Scan SRT, Record & Multi Record đã bắt đầu...")

        def _scan_loop():
            while getattr(self, "_srt_scan_running", False):
                try:
                    # 1) Scan SRT External Outputs
                    srt_outputs = self._parse_srt_external_outputs()
                    self.root.after(0, lambda data=srt_outputs: self._update_srt_external_table(data))
                    
                    # 2) Scan Record and Multi Record Settings
                    vmix_stats = self.get_vmix_stats()
                    multicorder_active = vmix_stats.get("connected", False) and vmix_stats.get("multicorder", False)
                    config_file = self._get_current_config_file_path()
                    if config_file:
                        record_data = self._parse_config_file_record(config_file)
                        multi_data = self._parse_config_file_multirecord(config_file, multicorder_active)
                        self._latest_record_data = record_data
                        self._latest_multi_data = multi_data
                        self.root.after(0, lambda r=record_data: self._update_record_table(r))
                        self.root.after(0, lambda m=multi_data: self._update_multirecord_table(m))
                except Exception as e:
                    self.log(f"❌ Auto Scan error: {e}")
                # Scan every 3 seconds
                for _ in range(30):
                    if not getattr(self, "_srt_scan_running", False):
                        break
                    time.sleep(0.1)

        threading.Thread(target=_scan_loop, daemon=True).start()

    def _update_srt_external_table(self, srt_outputs: list[dict]):
        """Update the SRT External Outputs table on the GUI."""
        if not hasattr(self, "srt_ext_tree"):
            return

        # Store latest data for server use
        self._srt_ext_latest_data = srt_outputs

        tree = self.srt_ext_tree
        for item in tree.get_children():
            tree.delete(item)

        if not srt_outputs:
            tree.insert("", tk.END, values=("(no data)",) + ("—",) * 7)
            return

        custom_names = getattr(self, "_srt_ext_custom_names", {})

        for entry in srt_outputs:
            # Skip entries with no port configured
            if not entry.get("port"):
                continue
            enabled_lbl = entry.get("srt_enabled_label", "—")
            type_lbl = entry.get("srt_type_label", "—")
            hostname = entry.get("hostname", "—") or "—"
            port_str = str(entry.get("port", 0) or "—")
            stream_id = entry.get("stream_id", "—") or "—"
            quality = entry.get("quality", "—")
            title = entry.get("title", "—")

            # Custom name (user-editable)
            name = custom_names.get(title, "")

            # Type icon
            if type_lbl == "Caller":
                type_display = "📤 Caller"
            elif type_lbl == "Listener":
                type_display = "📥 Listener"
            else:
                type_display = type_lbl

            # Enabled icon
            if enabled_lbl == "ON" and not self.is_network_offline():
                enabled_display = "🟢 ON"
            else:
                enabled_display = "🔴 OFF"

            tree.insert(
                "",
                tk.END,
                values=(
                    name,
                    title,
                    enabled_display,
                    port_str,
                    type_display,
                    hostname,
                    stream_id,
                    quality,
                ),
            )

    def _get_current_config_file_path(self) -> str | None:
        manual_path = getattr(self, "_manual_config_path", None)
        if manual_path and os.path.isfile(manual_path) and not manual_path.lower().endswith(".vmix"):
            return manual_path
        
        config_file = self._find_latest_studiocoast_config()
        if not config_file or not os.path.isfile(config_file):
            vmix_dir = self._vmix_data_dir()
            fallback = os.path.join(vmix_dir, "settingbackups", "current.config")
            if os.path.isfile(fallback):
                config_file = fallback
        return config_file

    def _parse_config_file_record(self, config_file: str) -> list[dict]:
        results: list[dict] = []
        if not config_file or not os.path.isfile(config_file):
            return results
        try:
            content = self._read_file_shared(config_file)
            for setting_name, label in [("RecordingSettings", "Recording 1"), ("RecordingSettings2", "Recording 2")]:
                m = re.search(
                    rf'name="{re.escape(setting_name)}"[^>]*>\s*<value>(.*?)</value>',
                    content, re.DOTALL,
                )
                if not m:
                    continue
                decoded = html.unescape(m.group(1).strip())
                if not decoded:
                    continue
                try:
                    sub = ET.fromstring(f"<root>{decoded}</root>")
                except ET.ParseError:
                    continue
                
                size = (sub.findtext("Size") or "—").strip()
                fr_ticks = (sub.findtext("FrameRate") or "").strip()
                fps_str = self._fps_from_ticks(fr_ticks) if fr_ticks else "—"
                filename = (sub.findtext("Filename") or "—").strip()
                
                selected_tab = (sub.findtext("SelectedTab") or "").strip()
                format_map = {
                    "0": "AVI",
                    "1": "WMV",
                    "2": "MPEG-2",
                    "3": "FFMPEG",
                    "4": "MP4",
                    "5": "NDI"
                }
                fmt = format_map.get(selected_tab, "—")
                if fmt == "—" and filename != "—":
                    _, ext = os.path.splitext(filename)
                    if ext:
                        fmt = ext[1:].upper()
                
                v_bitrate = (sub.findtext("MPEGBitRate") or "—").strip()
                a_bitrate = (sub.findtext("AudioBitRate") or "—").strip()
                v_bitrate_str = f"{v_bitrate} Mbps" if v_bitrate != "—" else "—"
                a_bitrate_str = f"{a_bitrate} kbps" if a_bitrate != "—" else "—"
                
                delay = (sub.findtext("AudioDelay") or "0").strip()
                delay_str = f"{delay} ms"
                
                hw = (sub.findtext("HardwareAcceleration") or "0").strip()
                hw_str = "Yes" if hw == "1" else "No"
                
                audio_enabled = "ON" if (sub.findtext("Audio") or "0").strip() == "1" else "OFF"
                audio_channel = (sub.findtext("AudioChannel") or "—").strip()
                source_channel = (sub.findtext("Channel") or "—").strip()
                fragmented = "Yes" if (sub.findtext("Fragmented") or "0").strip() == "1" else "No"
                
                results.append({
                    "profile": label,
                    "filename": filename,
                    "format": fmt,
                    "resolution": size,
                    "fps": fps_str,
                    "v_bitrate": v_bitrate_str,
                    "a_bitrate": a_bitrate_str,
                    "audio_delay": delay_str,
                    "hw_accel": hw_str,
                    "audio_enabled": audio_enabled,
                    "audio_channel": audio_channel,
                    "source_channel": source_channel,
                    "fragmented": fragmented
                })
        except Exception:
            pass
        return results

    def _parse_config_file_multirecord(self, config_file: str, vmix_alive: bool) -> list[dict]:
        results: list[dict] = []
        if not config_file or not os.path.isfile(config_file):
            return results
        try:
            content = self._read_file_shared(config_file)
            m = re.search(
                r'name="MultiCorderSettings"[^>]*>\s*<value>(.*?)</value>',
                content, re.DOTALL,
            )
            if m:
                decoded = html.unescape(m.group(1).strip())
                if decoded:
                    try:
                        sub = ET.fromstring(f"<root>{decoded}</root>")
                    except ET.ParseError:
                        return results
                    
                    selected_tab = (sub.findtext("SelectedTab") or "").strip()
                    format_map = {
                        "0": "AVI",
                        "1": "WMV",
                        "2": "MPEG-2",
                        "3": "FFMPEG",
                        "4": "MP4",
                        "5": "NDI"
                    }
                    fmt = format_map.get(selected_tab, "MP4")
                    
                    v_bitrate = (sub.findtext("MPEGBitRate") or "—").strip()
                    a_bitrate = (sub.findtext("AudioBitRate") or "—").strip()
                    v_bitrate_str = f"{v_bitrate} Mbps" if v_bitrate != "—" else "—"
                    a_bitrate_str = f"{a_bitrate} kbps" if a_bitrate != "—" else "—"
                    
                    audio_src = (sub.findtext("MultiCorderAudioSource") or "—").strip()
                    interval = (sub.findtext("Interval") or "—").strip()
                    show_all = "Yes" if (sub.findtext("ShowAllInputs") or "0").strip() == "1" else "No"
                    
                    sources_dict = {}
                    for child in sub:
                        if child.tag.startswith("MultiCorderEnabled."):
                            source_name = child.tag[len("MultiCorderEnabled."):]
                            enabled_val = (child.text or "0").strip()
                            sources_dict[source_name] = {
                                "enabled": enabled_val == "1",
                                "folder": "—"
                            }
                    
                    for child in sub:
                        if child.tag.startswith("MultiCorderFolder."):
                            source_name = child.tag[len("MultiCorderFolder."):]
                            folder_val = (child.text or "").strip()
                            if source_name in sources_dict:
                                sources_dict[source_name]["folder"] = folder_val
                    
                    global_folder = (sub.findtext("MultiCorderFolder0") or "").strip()
                    
                    sorted_sources = sorted(sources_dict.items())
                    for src_name, info in sorted_sources:
                        folder = info["folder"]
                        if folder == "—" or not folder:
                            folder = global_folder or "—"
                        
                        enabled_lbl = "ON" if (info["enabled"] and vmix_alive) else "OFF"
                        results.append({
                            "source": src_name,
                            "status": enabled_lbl,
                            "folder": folder,
                            "format": fmt,
                            "v_bitrate": v_bitrate_str,
                            "a_bitrate": a_bitrate_str,
                            "audio_src": audio_src,
                            "interval": interval,
                            "show_all": show_all
                        })
                    
                    if not results:
                        for i in range(1, 5):
                            enabled_tag = f"MultiCorderEnabled.Output{i}"
                            folder_tag = f"MultiCorderFolder.Output{i}"
                            enabled_val = (sub.findtext(enabled_tag) or "0").strip()
                            folder_val = (sub.findtext(folder_tag) or sub.findtext(f"MultiCorderFolder{i}") or global_folder or "—").strip()
                            enabled_lbl = "ON" if (enabled_val == "1" and vmix_alive) else "OFF"
                            results.append({
                                "source": f"Output{i}",
                                "status": enabled_lbl,
                                "folder": folder_val,
                                "format": fmt,
                                "v_bitrate": v_bitrate_str,
                                "a_bitrate": a_bitrate_str,
                                "audio_src": audio_src,
                                "interval": interval,
                                "show_all": show_all
                            })
        except Exception:
            pass
        return results

    def _update_record_table(self, record_data: list[dict]):
        """Update the Record Settings table on the GUI."""
        if not hasattr(self, "record_tree"):
            return

        tree = self.record_tree
        for item in tree.get_children():
            tree.delete(item)

        if not record_data:
            tree.insert("", tk.END, values=("(no data)",) + ("—",) * 7)
            return

        for entry in record_data:
            tree.insert(
                "",
                tk.END,
                values=(
                    entry.get("profile", "—"),
                    entry.get("filename", "—"),
                    entry.get("format", "—"),
                    entry.get("resolution", "—"),
                    entry.get("fps", "—"),
                    entry.get("v_bitrate", "—"),
                    entry.get("a_bitrate", "—"),
                    entry.get("audio_delay", "—"),
                ),
            )

    def _update_multirecord_table(self, multi_data: list[dict]):
        """Update the Multi Record Settings table on the GUI."""
        if not hasattr(self, "multi_record_tree"):
            return

        tree = self.multi_record_tree
        for item in tree.get_children():
            tree.delete(item)

        if not multi_data:
            tree.insert("", tk.END, values=("(no data)",) + ("—",) * 5)
            return

        for entry in multi_data:
            tree.insert(
                "",
                tk.END,
                values=(
                    entry.get("source", "—"),
                    entry.get("status", "—"),
                    entry.get("folder", "—"),
                    entry.get("format", "—"),
                    entry.get("v_bitrate", "—"),
                    entry.get("a_bitrate", "—"),
                ),
            )

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
                    "multicorder": root.findtext("multiCorder", "False").strip() == "True",
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
            "multicorder": False,
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
        import ipaddress
        import requests

        endpoints = [
            ("https://api.ipify.org?format=json", "json", "ip"),
            ("https://api64.ipify.org?format=json", "json", "ip"),
            ("https://checkip.amazonaws.com", "text", ""),
            ("https://ifconfig.me/ip", "text", ""),
            ("https://ipv4.icanhazip.com", "text", ""),
        ]

        fallback_ip = ""
        session = getattr(self, "http_session", None)

        for url, mode, key in endpoints:
            try:
                response = (session or requests).get(url, timeout=3)
                if response.status_code != 200:
                    continue

                if mode == "json":
                    payload_obj = response.json()
                    payload = payload_obj if isinstance(payload_obj, dict) else {}
                    raw_ip = str(payload.get(key, "")).strip()
                else:
                    raw_ip = (response.text or "").strip()

                if not raw_ip:
                    continue

                ip_str = raw_ip.splitlines()[0].strip()
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj.is_loopback or ip_obj.is_unspecified or ip_obj.is_link_local or ip_obj.is_multicast:
                    continue

                if ip_obj.is_global:
                    return ip_str

                if not fallback_ip:
                    fallback_ip = ip_str
            except Exception:
                continue

        if fallback_ip:
            return fallback_ip

        for entry in self.port_list:
            old_ip = str(entry.get("ipwan", "")).strip()
            if old_ip and old_ip not in {"loading...", "unknown", "—", "127.0.0.1"}:
                return old_ip

        return "unknown"

    # ── Stream quality helpers (ported from test_stream4_quality) ──────────

    @staticmethod
    def _stream_sort_key(stream_name: str) -> tuple[int, str]:
        m = re.match(r"streaming(\d+)$", stream_name.lower())
        if not m:
            return (9999, stream_name)
        return (int(m.group(1)), stream_name)

    @staticmethod
    def _find_all_streaming_blocks(raw: str) -> dict:
        blocks: dict = {}
        for m in re.finditer(r'name="(Streaming\d*)"[^>]*>\s*<value>(.*?)</value>', raw, re.DOTALL | re.IGNORECASE):
            blocks[m.group(1)] = m.group(2)
        return blocks

    @staticmethod
    def _setting_name_to_stream_key(setting_name: str) -> str:
        if setting_name.lower() == "streaming":
            return "streaming1"
        m = re.match(r"streaming(\d+)$", setting_name, re.IGNORECASE)
        if m:
            return f"streaming{m.group(1)}"
        return setting_name.lower()

    def _build_stream_info(self, root: ET.Element) -> dict:
        def _t(tag: str, default: str = "") -> str:
            return (root.findtext(tag) or default).strip()

        enabled = _t("Enabled", "0") == "1"
        if root.find("SRTEnabled") is not None or root.find("SRTHost") is not None:
            kind = "SRT"
            host = _t("SRTHost")
            port = _t("SRTPort")
            path = "(n/a)"
            video_bitrate = _t("SRTVideoBandwidth")
            audio_bitrate = _t("SRTAudioBandwidth")
            codec = _t("SRTVideoCodec")
            latency = _t("SRTLatencyMS") or _t("SRTLatency")
            passphrase = _t("SRTPassPhrase") or _t("SRTPassphrase")
            quality_label = _t("Quality") or _t("PresetName")
        else:
            kind = "RTMP/HTTP"
            host = _t("Url") or _t("Server")
            port = _t("Port")
            path = _t("StreamName") or _t("Key")
            video_bitrate = _t("VideoBitrate")
            audio_bitrate = _t("AudioBitrate")
            codec = _t("VideoCodec")
            latency = "(n/a)"
            passphrase = ""
            quality_label = _t("Quality") or _t("ProfileName") or _t("PresetName")

        return {
            "enabled": enabled,
            "kind": kind,
            "host": host,
            "port": port,
            "path": path,
            "video_bitrate": video_bitrate,
            "audio_bitrate": audio_bitrate,
            "codec": codec,
            "quality_label": quality_label,
            "latency": latency,
            "passphrase": passphrase,
        }

    def _parse_all_streams_from_config(self) -> tuple[dict, str, str | None]:
        vmix_dir = self._vmix_data_dir()
        cfg = os.path.join(vmix_dir, "settingbackups", "current.config")
        if not os.path.isfile(cfg):
            return {}, cfg, f"Không tìm thấy file: {cfg}"

        try:
            raw = self._read_file_shared(cfg)
        except Exception as ex:
            return {}, cfg, f"Lỗi đọc current.config: {ex}"

        blocks = self._find_all_streaming_blocks(raw)
        src_path = cfg

        if not blocks:
            settings_dir = os.path.join(vmix_dir, "settingbackups")
            pattern = os.path.join(settings_dir, "*.config")
            for other in sorted(glob.glob(pattern)):
                if os.path.abspath(other) == os.path.abspath(cfg):
                    continue
                try:
                    raw_other = self._read_file_shared(other)
                except Exception:
                    continue
                blocks = self._find_all_streaming_blocks(raw_other)
                if blocks:
                    src_path = other
                    break

        if not blocks:
            return {}, src_path, "Không tìm thấy block Streaming* trong current.config hoặc file backup"

        streams: dict = {}
        parsed_names: list[str] = []
        for setting_name, xml_body in blocks.items():
            try:
                inner = html.unescape(xml_body.strip())
                root = ET.fromstring(f"<root>{inner}</root>")
            except ET.ParseError:
                continue
            stream_key = self._setting_name_to_stream_key(setting_name)
            streams[stream_key] = self._build_stream_info(root)
            parsed_names.append(setting_name)

        if not streams:
            return {}, src_path, "Có block Streaming* nhưng parse XML thất bại"

        parsed_names_sorted = ", ".join(sorted(parsed_names, key=lambda n: self._stream_sort_key(self._setting_name_to_stream_key(n))))
        src_label = f"{src_path} ({parsed_names_sorted})"
        return streams, src_label, None

    def _find_latest_streaming_logs_by_stream(self) -> tuple[dict, str | None]:
        streaming_dir = os.path.join(self._vmix_data_dir(), "streaming")
        if not os.path.isdir(streaming_dir):
            return {}, f"Không tìm thấy thư mục: {streaming_dir}"

        today = datetime.now().date()
        has_any_stream_file = False
        latest_by_stream: dict = {}
        for name in os.listdir(streaming_dir):
            path = os.path.join(streaming_dir, name)
            if not os.path.isfile(path):
                continue
            m_stream = re.match(r"^(streaming\d+)\b", name, re.IGNORECASE)
            if not m_stream:
                continue

            has_any_stream_file = True

            last_write = datetime.fromtimestamp(os.path.getmtime(path))
            if last_write.date() != today:
                # Chỉ lấy file stream được ghi trong ngày hôm nay.
                continue

            stream_name = m_stream.group(1).lower()
            cur = latest_by_stream.get(stream_name)
            if cur is None or last_write > cur[1]:
                latest_by_stream[stream_name] = (path, last_write)

        if not latest_by_stream:
            if has_any_stream_file:
                return {}, "Hôm nay chưa có file streaming*"
            return {}, "Không có file streaming* trong thư mục streaming"

        result: dict = {}
        for stream_name, (latest_path, latest_write) in latest_by_stream.items():
            content, quality_line = self._read_stream_log_tail(latest_path)

            result[stream_name] = {
                "stream_name": stream_name,
                "file_path": latest_path,
                "file_name": os.path.basename(latest_path),
                "last_write": latest_write,
                "quality_line": quality_line,
                "raw_content": content,
            }

        return result, None

    def _read_stream_log_tail(self, path: str) -> tuple[str, str]:
        state = self._stream_log_state.get(path)
        if state is None:
            state = {"offset": 0, "buffer": "", "header": "", "quality_line": ""}
            self._stream_log_state[path] = state

        try:
            size = os.path.getsize(path)
        except OSError:
            return "", ""

        if not state["header"]:
            try:
                with open(path, "rb") as f:
                    head = f.read(65536)
                state["header"] = head.decode("utf-8", errors="replace")
            except Exception:
                state["header"] = ""

        if size < state["offset"]:
            state["offset"] = 0
            state["buffer"] = ""

        new_text = ""
        try:
            with open(path, "rb") as f:
                if state["offset"] == 0 and size > 65536:
                    f.seek(size - 65536)
                else:
                    f.seek(state["offset"])
                chunk = f.read()
                new_text = chunk.decode("utf-8", errors="replace")
                state["offset"] = size
        except Exception:
            new_text = ""

        if new_text:
            state["buffer"] = (state["buffer"] + new_text)[-20000:]

        quality_matches = re.findall(
            r"frame=.*?fps=.*?q=.*?(?:L?size=.*?)?bitrate=.*?kbits/s.*",
            state["buffer"],
        )
        if quality_matches:
            state["quality_line"] = quality_matches[-1].strip()

        combined = state["buffer"]
        if state["header"]:
            combined = state["header"] + "\n" + state["buffer"]

        return combined, state["quality_line"]

    @staticmethod
    def _extract_command_line(raw_content: str) -> str:
        m = re.search(r"Command line:\s*(.*?)ffmpeg version", raw_content, re.DOTALL)
        if not m:
            return ""
        return re.sub(r"\s+", " ", m.group(1)).strip()

    @staticmethod
    def _first_group(pattern: str, text: str) -> str:
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    def _build_ui_snapshot(self, raw_content: str) -> dict:
        cmd = self._extract_command_line(raw_content)

        video_bitrate = self._first_group(r"-b:v\s+(\S+)", cmd) or "(khong xac dinh)"
        width = self._first_group(r"-s:v\s+(\d+)x\d+", cmd)
        height = self._first_group(r"-s:v\s+\d+x(\d+)", cmd)
        encode_size = f"{width} x {height}" if width and height else "(khong xac dinh)"
        audio_bitrate = self._first_group(r"-b:a\s+(\S+)", cmd) or "(khong xac dinh)"

        profile = self._first_group(r"-profile:v\s+(\S+)", cmd) or "(khong xac dinh)"
        level = self._first_group(r"-level:v\s+(\S+)", cmd) or "(khong xac dinh)"
        preset = self._first_group(r"-preset:v\s+(\S+)", cmd) or "(khong xac dinh)"
        threads = self._first_group(r"-threads\s+(\S+)", cmd) or "(khong xac dinh)"

        audio_codec = self._first_group(r"-codec:a\s+(\S+)", cmd)
        audio_format = audio_codec.upper() if audio_codec else "(khong xac dinh)"

        source = "(khong xac dinh tu ffmpeg log)"
        aspect_ratio_crop = "(khong xac dinh tu ffmpeg log)"
        stream_delay = "(khong xac dinh tu ffmpeg log)"
        network_buffer = "(khong xac dinh tu ffmpeg log)"
        keyframe_aligned = "(khong xac dinh tu ffmpeg log)"

        channels = "stereo" if re.search(r"\bstereo\b", raw_content, re.IGNORECASE) else "(khong xac dinh)"

        gop = self._first_group(r"-g:v\s+(\d+)", cmd)
        fps_raw = self._first_group(r"(\d+(?:\.\d+)?)\s*fps", raw_content)
        if gop and fps_raw:
            try:
                key_sec = float(gop) / float(fps_raw)
                keyframe_frequency = f"{gop} frames (~{key_sec:.2f}s @ {fps_raw}fps)"
            except Exception:
                keyframe_frequency = f"{gop} frames"
        elif gop:
            keyframe_frequency = f"{gop} frames"
        else:
            keyframe_frequency = "(khong xac dinh)"

        has_nal = bool(re.search(r"nal[_-]hrd", cmd, re.IGNORECASE))
        has_strict = bool(re.search(r"strict[-_]cbr|nal[_-]hrd=cbr", cmd, re.IGNORECASE))
        strict_cbr = "ON" if has_strict else "OFF/Unknown"
        nal_cbr = "ON" if has_nal else "OFF/Unknown"

        return {
            "video_bitrate": video_bitrate,
            "encode_size": encode_size,
            "audio_bitrate": audio_bitrate,
            "source": source,
            "profile": profile,
            "level": level,
            "preset": preset,
            "aspect_ratio_crop": aspect_ratio_crop,
            "audio_format": audio_format,
            "channels": channels,
            "keyframe_frequency": keyframe_frequency,
            "stream_delay": stream_delay,
            "threads": threads,
            "network_buffer": network_buffer,
            "strict_cbr": strict_cbr,
            "nal_cbr": nal_cbr,
            "keyframe_aligned": keyframe_aligned,
        }

    def _compose_stream_endpoint(self, info: dict | None) -> tuple[str, str]:
        """Compose stream URL và key từ config dict (port full logic từ test_stream4_quality.py)."""
        if not info:
            return "-", ""

        host = (info.get("host") or "").strip()
        port = (info.get("port") or "").strip()
        key = (info.get("path") or "").strip().lstrip("/")
        kind = (info.get("kind") or "").strip()

        # SRT
        if kind == "SRT":
            endpoint = ""
            if host:
                endpoint = f"srt://{host}"
            if port:
                endpoint = f"{endpoint}:{port}" if endpoint else f":{port}"
            return endpoint or "(trong)", key

        # RTMP / HTTP (vMix kind field là "RTMP/HTTP")
        endpoint = ""
        if host:
            raw_url = host if "://" in host else f"rtmp://{host}"
            parsed = urllib.parse.urlparse(raw_url)
            scheme = parsed.scheme or "rtmp"
            netloc = parsed.netloc
            path_parts = [p for p in (parsed.path or "").split("/") if p]

            # Nếu URL đang chứa luôn key (ví dụ: .../live2/<key>) và config key trống,
            # tự tách key ra để hiển thị riêng.
            if not key and len(path_parts) >= 2:
                key = path_parts[-1]
                path_parts = path_parts[:-1]

            base_path = "/".join(path_parts)
            endpoint = f"{scheme}://{netloc}" if netloc else ""
            if base_path:
                endpoint = f"{endpoint}/{base_path}" if endpoint else f"/{base_path}"

        if port:
            if endpoint:
                parsed_endpoint = urllib.parse.urlparse(endpoint)
                if parsed_endpoint.port is None and parsed_endpoint.hostname:
                    netloc = f"{parsed_endpoint.hostname}:{port}"
                    path = parsed_endpoint.path or ""
                    endpoint = f"{parsed_endpoint.scheme}://{netloc}{path}"
            else:
                endpoint = f":{port}"

        return endpoint or "(trong)", key

    def _compose_stream_endpoint_from_log(self, raw_content: str) -> tuple[str, str]:
        """Tách URL và stream key từ ffmpeg command line trong log (full logic từ test_stream4_quality.py)."""
        m = re.search(r"Command line:\s*(.*?)ffmpeg version", raw_content, re.DOTALL)
        if not m:
            return "(trong)", ""
        cmd = re.sub(r"\s+", " ", m.group(1)).strip()

        urls = re.findall(r"((?:srt|rtmp|rtmps|http|https)://[^\s\"']+)", cmd, re.IGNORECASE)
        if not urls:
            return "(trong)", ""

        raw_url = urls[-1].strip()
        parsed = urllib.parse.urlparse(raw_url)
        scheme = (parsed.scheme or "").lower()

        if scheme in {"rtmp", "rtmps", "http", "https"}:
            segments = [s for s in (parsed.path or "").split("/") if s]
            key = segments[-1] if segments else ""
            base_segments = segments[:-1] if len(segments) >= 2 else segments

            endpoint = ""
            if parsed.netloc:
                endpoint = f"{scheme}://{parsed.netloc}"
                if base_segments:
                    endpoint = f"{endpoint}/{'/'.join(base_segments)}"

            key_from_query = ""
            if parsed.query:
                q = urllib.parse.parse_qs(parsed.query)
                for k in ("key", "streamkey", "name", "streamid", "stream_id"):
                    vals = q.get(k)
                    if vals:
                        key_from_query = vals[0].strip()
                        break

            if key_from_query:
                key = key_from_query
            elif key and parsed.query:
                # TikTok-style: /game/<stream-key>?<auth-params>
                key = f"{key}?{parsed.query}"

            return endpoint or raw_url, key

        if scheme == "srt":
            endpoint = f"srt://{parsed.netloc}" if parsed.netloc else raw_url
            key = ""
            if parsed.query:
                q = urllib.parse.parse_qs(parsed.query)
                stream_ids = q.get("streamid") or q.get("r")
                if stream_ids:
                    key = stream_ids[0].strip()
            return endpoint, key

        return raw_url, ""

    def _handle_stream_selection(self):
        """Update URL and Key panel based on selected stream in quality tree."""
        selection = self.stream_quality_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        stream_name = self.stream_quality_tree.item(item_id, "values")[0]

        # Get data from cache
        if not self._stream_quality_cache:
            return

        streams = self._stream_quality_cache.get("streams", [])
        entry = next((s for s in streams if s.get("stream") == stream_name), None)
        if not entry:
            return

        info = entry.get("config")
        runtime = entry.get("runtime") or {}
        latest_log = runtime.get("raw_content", "")

        # Lấy endpoint + key từ config trước
        endpoint_cfg, key_cfg = self._compose_stream_endpoint(info)
        endpoint = endpoint_cfg
        key = key_cfg
        source = "config"

        # Fallback: bổ sung/thay thế bằng log nếu config trống
        if latest_log:
            endpoint_log, key_log = self._compose_stream_endpoint_from_log(latest_log)
            if endpoint in ("", "-", "(trong)", "(khong xac dinh)") and endpoint_log and endpoint_log != "(trong)":
                endpoint = endpoint_log
                source = "log"
            if (not key) and key_log:
                key = key_log
                source = "log"

        self.sel_stream_name_var.set(stream_name)
        self.sel_stream_url_var.set(endpoint or "-")
        self.sel_stream_key_var.set(key or "(trong)")

    @staticmethod
    def _parse_k_to_kbps(raw: str) -> float:
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*k", (raw or "").lower())
        return float(m.group(1)) if m else 0.0

    @staticmethod
    def _parse_quality_metric(line: str, field: str) -> float:
        if not line:
            return 0.0
        if field == "bitrate":
            m = re.search(r"bitrate=\s*([0-9]+(?:\.[0-9]+)?)kbits/s", line)
        elif field == "fps":
            m = re.search(r"fps=\s*([0-9]+(?:\.[0-9]+)?)", line)
        elif field == "speed":
            m = re.search(r"speed=\s*([0-9]+(?:\.[0-9]+)?)x", line)
        else:
            m = None
        return float(m.group(1)) if m else 0.0

    def _assess_stream_health(self, latest: dict, ui: dict) -> dict:
        actual_bitrate = self._parse_quality_metric(latest.get("quality_line", ""), "bitrate")
        target_bitrate = self._parse_k_to_kbps(ui.get("video_bitrate", ""))
        speed = self._parse_quality_metric(latest.get("quality_line", ""), "speed")
        fps = self._parse_quality_metric(latest.get("quality_line", ""), "fps")
        raw_content = latest.get("raw_content", "")
        recent_content = raw_content[-8000:] if raw_content else ""
        dropped_warnings = len(re.findall(r"frame dropped", recent_content, re.IGNORECASE))

        ratio = (actual_bitrate / target_bitrate) if target_bitrate > 0 else 0.0
        duration_sec = 0.0
        m_time = re.search(r"time=([0-9]{2}):([0-9]{2}):([0-9]{2}(?:\.[0-9]+)?)", latest.get("quality_line", ""))
        if m_time:
            duration_sec = int(m_time.group(1)) * 3600 + int(m_time.group(2)) * 60 + float(m_time.group(3))

        overload_patterns = [
            r"past duration too large",
            r"buffer .* too full",
            r"real-time buffer .* too full",
            r"frame dropped",
        ]
        network_patterns = [
            r"connection reset by peer",
            r"resource temporarily unavailable",
            r"socket error",
            r"write error",
            r"writen",
            r"av_interleaved_write_frame\(\).*error",
            r"rtmp .*send error",
            r"srt.*error",
            r"tcp.*error",
        ]

        overload_hit = any(re.search(pat, recent_content, re.IGNORECASE) for pat in overload_patterns)
        network_hit = any(re.search(pat, recent_content, re.IGNORECASE) for pat in network_patterns)

        if (
            overload_hit
            or network_hit
            or dropped_warnings > 0
            or (target_bitrate > 0 and ratio < 0.85)
            or (speed > 0 and speed < 0.5)
            or (fps > 0 and fps < 30)
            or (duration_sec > 0 and duration_sec < 20)
        ):
            status = "VANG"
        else:
            status = "DO"

        reason = (
            f"ratio={ratio:.2f}, speed={speed:.2f}x, fps={fps:.2f}, "
            f"dropped={dropped_warnings}, duration={duration_sec:.1f}s, "
            f"overload={'1' if overload_hit else '0'}, network={'1' if network_hit else '0'}"
        )

        return {
            "status": status,
            "reason": reason,
            "actual_bitrate_kbps": actual_bitrate,
            "target_bitrate_kbps": target_bitrate,
            "bitrate_ratio": ratio,
            "speed": speed,
            "dropped_warnings": dropped_warnings,
        }

    def _build_stream_quality_entry(self, stream_name: str, info: dict | None, latest: dict | None, live_window_sec: int) -> dict:
        now = datetime.now()
        last_write_iso = "-"
        runtime_status = "-"
        latest_log_file = "-"
        quality_line = "-"
        if latest and latest.get("last_write"):
            last_write_iso = latest.get("last_write").isoformat()
            age_sec = (now - latest.get("last_write")).total_seconds()
            runtime_status = "ON" if age_sec <= live_window_sec else "OFF"
            latest_log_file = latest.get("file_name") or "-"
            quality_line = latest.get("quality_line") or "-"

        ui = self._build_ui_snapshot(latest.get("raw_content", "")) if latest else None
        health = self._assess_stream_health(latest, ui) if latest and ui else None

        return {
            "stream": stream_name,
            "config": None
            if info is None
            else {
                "enabled": info.get("enabled"),
                "kind": info.get("kind"),
                "host": info.get("host"),
                "port": info.get("port"),
                "path": info.get("path"),
                "video_bitrate": info.get("video_bitrate"),
                "audio_bitrate": info.get("audio_bitrate"),
                "codec": info.get("codec"),
                "quality": info.get("quality_label"),
                "latency": info.get("latency"),
                "passphrase_set": bool(info.get("passphrase")),
            },
            "runtime": {
                "status": runtime_status,
                "last_write": last_write_iso,
                "latest_log_file": latest_log_file,
                "quality_line": quality_line,
                "raw_content": latest.get("raw_content", "") if latest else "",
            },
            "ui_snapshot": ui,
            "health": health,
        }

    def get_stream_quality_snapshot(self, live_window_sec: int = 20) -> dict:
        now = time.time()
        if now - self._stream_quality_ts < 2 and self._stream_quality_cache:
            return self._stream_quality_cache

        streams_cfg, cfg_source, cfg_error = self._parse_all_streams_from_config()
        latest_by_stream, log_error = self._find_latest_streaming_logs_by_stream()

        all_streams = sorted(set(streams_cfg.keys()) | set(latest_by_stream.keys()), key=self._stream_sort_key)
        entries = []
        for stream_name in all_streams:
            info = streams_cfg.get(stream_name)
            latest = latest_by_stream.get(stream_name)
            entries.append(self._build_stream_quality_entry(stream_name, info, latest, live_window_sec))

        payload = {
            "generated_at": datetime.now().isoformat(),
            "config_source": cfg_source,
            "config_error": cfg_error,
            "log_error": log_error,
            "streams": entries,
        }

        self._stream_quality_cache = payload
        self._stream_quality_ts = now
        return payload

    def _build_stream_rows_for_db(self, snapshot: dict | None) -> list[dict]:
        """Convert UI stream quality snapshot to compact stream array for server/database."""
        if not isinstance(snapshot, dict):
            return []

        streams = snapshot.get("streams", [])
        if not isinstance(streams, list):
            return []

        def _int_or_zero(value) -> int:
            try:
                return int(round(float(value)))
            except (TypeError, ValueError):
                return 0

        def _fmt_or_empty(value, decimals: int) -> str:
            try:
                return f"{float(value):.{decimals}f}"
            except (TypeError, ValueError):
                return ""

        rows: list[dict] = []
        for entry in sorted(streams, key=lambda s: self._stream_sort_key(str((s or {}).get("stream", "")))):
            if not isinstance(entry, dict):
                continue

            runtime = entry.get("runtime") or {}
            health = entry.get("health") or {}
            ui_snap = entry.get("ui_snapshot") or {}

            rows.append({
                "stream": str(entry.get("stream", "") or ""),
                "runtime": str(runtime.get("status", "") or ""),
                "health": str(health.get("status", "") or ""),
                "vbit": str(ui_snap.get("video_bitrate", "") or ""),
                "size": str(ui_snap.get("encode_size", "") or ""),
                "abit": str(ui_snap.get("audio_bitrate", "") or ""),
                "level": str(ui_snap.get("level", "") or ""),
                "preset": str(ui_snap.get("preset", "") or ""),
                "aformat": str(ui_snap.get("audio_format", "") or ""),
                "channels": str(ui_snap.get("channels", "") or ""),
                "keyframe": str(ui_snap.get("keyframe_frequency", "") or ""),
                "actual": _int_or_zero(health.get("actual_bitrate_kbps", 0)),
                "target": _int_or_zero(health.get("target_bitrate_kbps", 0)),
                "ratio": _fmt_or_empty(health.get("bitrate_ratio"), 2),
                "speed": _fmt_or_empty(health.get("speed"), 2),
                "dropped": _int_or_zero(health.get("dropped_warnings", 0)),
                "file": str(runtime.get("latest_log_file", "") or ""),
            })

        return rows

    def _build_stream_keys_for_db(self, snapshot: dict | None) -> list[dict]:
        """Tạo array riêng chứa URL + stream key cho từng stream.

        Format: [{"stream": "streaming1", "url": "rtmps://...", "key": "FB-..."}, ...]
        """
        if not isinstance(snapshot, dict):
            return []

        streams = snapshot.get("streams", [])
        if not isinstance(streams, list):
            return []

        result: list[dict] = []
        for entry in sorted(streams, key=lambda s: self._stream_sort_key(str((s or {}).get("stream", "")))):
            if not isinstance(entry, dict):
                continue

            stream_name = str(entry.get("stream", "") or "")
            info        = entry.get("config") or {}
            runtime     = entry.get("runtime") or {}
            raw_content = runtime.get("raw_content", "")

            # Config trước → fallback log
            endpoint, key = self._compose_stream_endpoint(info)

            if raw_content:
                ep_log, key_log = self._compose_stream_endpoint_from_log(raw_content)
                if endpoint in ("", "-", "(trong)", "(khong xac dinh)") and ep_log and ep_log != "(trong)":
                    endpoint = ep_log
                if not key and key_log:
                    key = key_log

            result.append({
                "stream": stream_name,
                "url":    endpoint or "-",
                "key":    key or "",
            })

        return result

    # Removed SeaTalk helper methods (notifications handled by server_gui_advanced)

    def monitor_loop(self):
        import requests

        ip = self.ip_var.get().strip()
        if not ip:
            self.log("ERROR: IP trống!")
            self.is_running = False
            self.start_btn.config(text="▶ START MONITORING", bootstyle="success")
            return

        wan_ip = self.get_wan_ip()
        self.root.after(0, lambda: self.wan_ip_var.set(wan_ip or "—"))
        prev_status = {}
        last_wan_check = datetime.now(VIETNAM_TZ)
        last_ip_check = datetime.now(VIETNAM_TZ)
        wan_refresh_sec = 30
        ip_check_sec = 5
        if self.port_list:
            self.log(f"Bắt đầu giám sát {len(self.port_list)} port(s)...")
        else:
            self.log("Bắt đầu giám sát...")

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
                    self.root.after(0, lambda w=new_wan: self.wan_ip_var.set(w or "—"))
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
            mac_addr, net_speed = self.get_network_card_summary()
            pid_vmix, vmix_send_mbps, vmix_receive_mbps = self.measure_vmix_pid_and_bandwidth_mbps()
            ffmpeg_list = self.measure_ffmpeg_bandwidth_list()
            self.root.after(0, lambda fl=ffmpeg_list: self.update_ffmpeg_table(fl))

            vmix_stats = self.get_vmix_stats()
            ping_str = f"{ping_ms:.0f}" if ping_ms is not None else "—"
            timeout_str = str(self.ping_timeout_count)
            cpu_str = f"{cpu_pct:.1f}" if cpu_pct is not None else "—"
            mem_str = f"{mem_pct:.1f}" if mem_pct is not None else "—"
            gpu_str = f"{gpu_pct:.1f}" if gpu_pct is not None else "—"
            sender_bw_str = self._format_mbps_text(sender_mbps)
            receiver_bw_str = self._format_mbps_text(receiver_mbps)
            vmix_send_bw_str = self._format_mbps_text(vmix_send_mbps)
            vmix_receive_bw_str = self._format_mbps_text(vmix_receive_mbps)
            pid_vmix_str = pid_vmix if pid_vmix else "—"

            rec_str = "🔴 ON" if vmix_stats["recording"] else "OFF"
            live_str = "🔴 ON" if vmix_stats["streaming"] else "OFF"
            ext_str = "🟢 ON" if vmix_stats["external"] else "OFF"
            multirec_str = "🔴 ON" if vmix_stats.get("multicorder", False) else "OFF"
            res_str = vmix_stats.get("resolution", "—") or "—"
            srt_by_port = vmix_stats.get("srt_by_port", {})
            if not srt_by_port:
                _, srt_by_port = self.get_res_and_srt_from_file()
            srt_fallback = next(iter(srt_by_port.values()), "—")

            # Update port_list entries with machine metrics
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
                entry["mac_address"] = mac_addr
                entry["network_speed"] = net_speed
                entry["vmixsend"] = vmix_send_bw_str
                entry["vmixreceive"] = vmix_receive_bw_str
                entry["pid_vmix"] = pid_vmix_str
                entry["rec"] = rec_str
                entry["live"] = live_str
                entry["ext"] = ext_str
                entry["multirec"] = multirec_str
                entry["resolution"] = res_str
                entry["srt"] = srt_str

                vmix_running = self.is_vmix_on_port(port)
                current_status = "ON" if vmix_running else "OFF"
                entry["srt_status"] = current_status

                if prev_status.get(port) != current_status:
                    icon = "🟢" if current_status == "ON" else "🔴"
                    self.log(f"{icon} SRT {current_status}: {name} {ip}:{port}")
                    prev_status[port] = current_status

            # Build SRT array from auto-scan external outputs data
            srt_list = []
            custom_names = getattr(self, "_srt_ext_custom_names", {})
            srt_ext_data = getattr(self, "_srt_ext_latest_data", [])
            for ext_entry in srt_ext_data:
                if not ext_entry.get("port"):
                    continue
                title = ext_entry.get("title", "")
                srt_status = "OFF" if self.is_network_offline() else ext_entry.get("srt_enabled_label", "OFF")
                srt_list.append({
                    "nameSRT": custom_names.get(title, ""),
                    "port": ext_entry.get("port", 0),
                    "quality": ext_entry.get("quality", "—"),
                    "status": srt_status,
                    "type": ext_entry.get("srt_type_label", "—"),
                    "hostname": ext_entry.get("hostname", ""),
                    "stream_id": ext_entry.get("stream_id", ""),
                    "title": title,
                })


            quality_snapshot = self.get_stream_quality_snapshot()
            stream_rows = self._build_stream_rows_for_db(quality_snapshot)
            try:
                stream_keys = self._build_stream_keys_for_db(quality_snapshot)
            except Exception as _sk_err:
                self.log(f"[ERROR stream_keys] {_sk_err}")
                stream_keys = []
            self.root.after(0, lambda qs=quality_snapshot: self.update_stream_quality_table(qs))
            self.root.after(0, lambda qs=quality_snapshot: self.update_stream_url_key_panel(qs))

            # Send ONE request with all SRT streams
            try:
                machine_name = socket.gethostname()
                data = {
                    "name": machine_name,
                    "ip": ip,
                    "ipwan": wan_ip,
                    "statusapp": 1,
                    "ping": ping_ms,
                    "ping_timeouts": self.ping_timeout_count,
                    "temperature": cpu_pct,
                    "memory": mem_pct,
                    "gpu": gpu_pct,
                    "sender_mbps": sender_mbps,
                    "receiver_mbps": receiver_mbps,
                    "mac_address": mac_addr,
                    "network_speed": net_speed,
                    "vmixsend": vmix_send_mbps,
                    "vmixreceive": vmix_receive_mbps,
                    "PIDVMIX": pid_vmix,
                    "vmix_recording": vmix_stats.get("recording", False),
                    "vmix_streaming": vmix_stats.get("streaming", False),
                    "vmix_external": vmix_stats.get("external", False),
                    "vmix_multicorder": vmix_stats.get("multicorder", False),
                    "MultirecordingStatus": vmix_stats.get("multicorder", False),
                    "List_REcord": getattr(self, "_latest_record_data", []),
                    "ListMultiREcord": getattr(self, "_latest_multi_data", []),
                    "resolution": res_str,
                    "SRT": srt_list,
                    "stream": stream_rows,
                    "stream_keys": stream_keys,
                    "stream_quality": quality_snapshot,
                    "ffmpeg": ffmpeg_list,
                }
                headers = {"Content-Type": "application/json"}
                response = self.http_session.post(self.get_server_url(), json=data, headers=headers, timeout=5)
                if response.status_code == 200:
                    pass  # Status changes already logged above per-port
                elif response.status_code == 500:
                    self.log(f"⚠️ Server error 500")
                else:
                    self.log(f"❌ HTTP {response.status_code}")
            except requests.exceptions.Timeout:
                self.log(f"⏱️ Timeout gửi data")
            except requests.exceptions.ConnectionError:
                self.log(f"❌ Mất kết nối server")
            except Exception as e:
                self.log(f"❌ ERROR: {str(e)}")

            metrics_entry = {
                "ping": ping_str,
                "timeout": timeout_str,
                "cpu": cpu_str,
                "memory": mem_str,
                "gpu": gpu_str,
                "sender_bw": sender_bw_str,
                "receiver_bw": receiver_bw_str,
                "mac_address": mac_addr,
                "network_speed": net_speed,
                "vmixsend": vmix_send_bw_str,
                "vmixreceive": vmix_receive_bw_str,
                "pid_vmix": pid_vmix_str,
                "rec": rec_str,
                "live": live_str,
                "ext": ext_str,
                "multirec": multirec_str,
                "resolution": res_str,
            }
            self.root.after(0, lambda e=metrics_entry: self.update_table_display(e))



            for _ in range(10):
                if not self.is_running:
                    break
                time.sleep(0.1)
