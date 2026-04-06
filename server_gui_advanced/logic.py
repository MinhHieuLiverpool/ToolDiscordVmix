import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime
from tkinter import filedialog, messagebox

import requests
import websocket

try:
    from .shared import DEFAULT_SERVER_URL, VIETNAM_TZ, get_first_srt, get_srt_ports_str
except ImportError:
    try:
        from server_gui_advanced.shared import DEFAULT_SERVER_URL, VIETNAM_TZ, get_first_srt, get_srt_ports_str
    except ImportError:
        from shared import DEFAULT_SERVER_URL, VIETNAM_TZ, get_first_srt, get_srt_ports_str


class ServerDataGUILogicMixin:
    def _normalize_api_url(self, raw_url: str) -> str:
        url = str(raw_url or "").strip().rstrip("/")
        if not url:
            url = DEFAULT_SERVER_URL
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"http://{url}"
        return url.rstrip("/")

    def _build_ws_url(self, api_url: str) -> str:
        if api_url.startswith("https://"):
            return f"wss://{api_url[len('https://'): ]}/ws"
        if api_url.startswith("http://"):
            return f"ws://{api_url[len('http://'): ]}/ws"
        return f"ws://{api_url}/ws"

    def apply_server_url(self, reconnect: bool = True, announce: bool = True):
        candidate = self.api_url
        if hasattr(self, "server_url_var"):
            candidate = self.server_url_var.get()

        new_api_url = self._normalize_api_url(candidate)
        new_ws_url = self._build_ws_url(new_api_url)
        old_api_url = getattr(self, "api_url", "")

        self.api_url = new_api_url
        self.ws_url = new_ws_url

        if hasattr(self, "server_url_var"):
            self.server_url_var.set(new_api_url)

        if announce:
            print(f"🌐 API URL: {self.api_url}")
            print(f"📡 WS URL: {self.ws_url}")

        if reconnect and old_api_url and old_api_url != new_api_url and self.use_websocket:
            if self.ws is not None:
                try:
                    self.ws.close()
                except Exception:
                    pass
            elif not self.ws_connected:
                self.connect_websocket()

        if reconnect:
            self.refresh_data(show_dialog=False)

    def connect_websocket(self):
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if not isinstance(data, list):
                    return
                seen = set()
                deduped = []
                for entry in data:
                    d = entry.get("data", {})
                    key = d.get("name", d.get("ip", ""))
                    if key not in seen:
                        seen.add(key)
                        deduped.append(entry)
                data = deduped

                has_list_changed = self.has_data_changed(self.data, data)
                self.data = data

                if has_list_changed:
                    self.root.after(0, self.update_all_table)

                self.update_selected_data()
                self.root.after(0, self.update_selected_table)

                if self.auto_send_enabled:
                    self.send_to_discord_auto()
            except json.JSONDecodeError as e:
                print(f"✗ WebSocket JSON error: {e}")
            except Exception as e:
                print(f"✗ WebSocket message error: {e}")

        def on_error(ws, error):
            print(f"✗ WebSocket error: {error}")
            self.ws_connected = False

        def on_close(ws, close_status_code, close_msg):
            print(f"⚠ WebSocket closed: {close_status_code} - {close_msg}")
            self.ws_connected = False
            self.root.after(0, lambda: self.status_label.configure(text="🔴 Disconnected", text_color="#f44336"))
            if not self.rest_polling_active:
                self.start_rest_polling_backup()
            if self.use_websocket:
                self.ws_reconnect_attempts += 1
                wait_time = min(5 * self.ws_reconnect_attempts, 30)
                print(f"🔄 Reconnecting in {wait_time} seconds... (attempt {self.ws_reconnect_attempts})")
                time.sleep(wait_time)
                self.connect_websocket()

        def on_open(ws):
            print("✓ WebSocket connected!")
            self.ws_connected = True
            self.ws_reconnect_attempts = 0
            self.rest_polling_active = False
            self.root.after(0, lambda: self.status_label.configure(text="🟢 Connected", text_color="#4CAF50"))

        def run_ws():
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    on_open=on_open,
                )
                self.ws.run_forever()
            except Exception as e:
                print(f"✗ WebSocket connection failed: {e}")
                print("⚠ Falling back to REST API polling...")
                self.ws_connected = False
                self.use_websocket = False
                self.start_rest_polling()

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()

    def start_rest_polling(self):
        if self.auto_send_enabled and not self.ws_connected:
            self.check_for_changes()

    def start_rest_polling_backup(self):
        if self.rest_polling_active or self.ws_connected:
            return
        self.rest_polling_active = True
        print("🔄 Starting REST polling backup...")
        self.rest_poll_loop()

    def rest_poll_loop(self):
        if not self.rest_polling_active or self.ws_connected:
            self.rest_polling_active = False
            return

        def poll():
            try:
                resp = requests.get(f"{self.api_url}/logs", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        seen = set()
                        unique = []
                        for entry in data:
                            d = entry.get("data", {})
                            key = d.get("name", d.get("ip", "")) or d.get("ip", "")
                            if key not in seen:
                                seen.add(key)
                                unique.append(entry)
                        data = unique
                        has_list_changed = self.has_data_changed(self.data, data)
                        self.data = data
                        if has_list_changed:
                            self.root.after(0, self.update_all_table)
                        self.update_selected_data()
                        self.root.after(0, self.update_selected_table)
                        if self.auto_send_enabled:
                            current_snapshot = self.get_data_snapshot()
                            if current_snapshot != self.previous_data:
                                self.send_to_discord_auto()
                                self.previous_data = current_snapshot
            except Exception as e:
                print(f"⚠ REST polling error: {e}")

        threading.Thread(target=poll, daemon=True).start()
        self.root.after(1500, self.rest_poll_loop)

    def toggle_auto_send(self):
        self.auto_send_enabled = not self.auto_send_enabled
        if self.auto_send_enabled:
            self.toggle_btn.configure(text="AUTO SEND: ON", fg_color="#4CAF50")
            print("✓ Auto-send to Discord: ENABLED")
            self.webhook_entry.configure(state="disabled")
            self.prefix_entry.configure(state="disabled")
            self.previous_data = self.get_data_snapshot()
            print(f"📸 Đã lưu snapshot ban đầu: {len(self.previous_data)} items")
            self.send_full_list_to_discord()
            if not self.ws_connected:
                self.check_for_changes()
        else:
            self.toggle_btn.configure(text="AUTO SEND: OFF", fg_color="#9E9E9E")
            print("✗ Auto-send to Discord: DISABLED")
            self.webhook_entry.configure(state="normal")
            self.prefix_entry.configure(state="normal")

    def get_data_snapshot(self):
        snapshot = []
        for entry in self.selected_data:
            d = entry.get("data", {})
            ip = d.get("ip", "")
            ipwan = d.get("ipwan", "")
            for row in self._build_discord_rows(d):
                snapshot.append(
                    {
                        "name": row["name"],
                        "ip": ip,
                        "ipwan": ipwan,
                        "port": row["port"],
                        "status": row["status"],
                    }
                )
        return sorted(snapshot, key=lambda x: (x["name"], x["port"]))

    def _build_discord_rows(self, d):
        """Build per-row Discord payload data using nameSRT when available."""
        if d.get("ptz", False):
            return [
                {
                    "name": d.get("name", ""),
                    "port": str(d.get("port", "")),
                    "status": d.get("status", ""),
                }
            ]

        base_name = d.get("name", "")
        srt_raw = d.get("SRT", [])
        if isinstance(srt_raw, dict):
            srt_items = [srt_raw]
        elif isinstance(srt_raw, list):
            srt_items = [item for item in srt_raw if isinstance(item, dict)]
        else:
            srt_items = []

        rows = []
        for s in srt_items:
            rows.append(
                {
                    "name": str(s.get("nameSRT", "")).strip() or base_name,
                    "port": str(s.get("port", "")),
                    "status": s.get("status", d.get("status", "")),
                }
            )

        if rows:
            return rows

        srt = get_first_srt(d)
        return [
            {
                "name": base_name,
                "port": str(get_srt_ports_str(d) or d.get("port", "")),
                "status": srt.get("status", d.get("status", "")),
            }
        ]

    def send_full_list_to_discord(self):
        webhook = self.webhook_var.get().strip()
        if not webhook or not self.selected_data:
            print("⚠ Không có webhook hoặc selected data để gửi")
            return

        def send():
            try:
                prefix = self.prefix_var.get().strip()
                messages = []
                now = datetime.now(VIETNAM_TZ)
                title = f"=== FULL STATUS LIST - {now.strftime('%d/%m/%Y %H:%M:%S')} ==="
                messages.append(title)

                for entry in self.selected_data:
                    d = entry.get("data", {})
                    ipwan = d.get("ipwan", "")
                    for row in self._build_discord_rows(d):
                        msg = f"[{prefix}][{row['name']}] SRT {row['status']} | IPWAN: {ipwan} | PORT: {row['port']}"
                        messages.append(msg)

                payload = {"content": "\n".join(messages)}
                resp = requests.post(webhook, json=payload, timeout=10)
                if resp.status_code in [200, 204]:
                    print(f"✓ Sent FULL LIST ({len(self.selected_data)} items) to Discord")
                else:
                    print(f"✗ Discord error: {resp.status_code}")
            except Exception as e:
                print(f"✗ Failed to send full list: {e}")

        threading.Thread(target=send, daemon=True).start()

    def check_for_changes(self):
        if not self.auto_send_enabled:
            return

        def check():
            url = f"{self.api_url}/logs"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        seen = set()
                        unique = []
                        for entry in data:
                            d = entry.get("data", {})
                            key = d.get("name", d.get("ip", "")) or d.get("ip", "")
                            if key not in seen:
                                seen.add(key)
                                unique.append(entry)
                        data = unique

                        if not self.has_data_changed(self.data, data):
                            return

                        self.data = data
                        self.update_selected_data()
                        self.update_selected_table()
                        self.send_to_discord_auto()
            except Exception as e:
                print(f"Error checking: {e}")

        threading.Thread(target=check, daemon=True).start()
        if self.auto_send_enabled:
            self.root.after(5000, self.check_for_changes)

    def send_to_discord_auto(self):
        if self.is_sending:
            return

        webhook = self.webhook_var.get().strip()
        if not webhook or not self.selected_data:
            return

        current_snapshot = self.get_data_snapshot()
        if not self.previous_data:
            self.previous_data = current_snapshot
            return
        if current_snapshot == self.previous_data:
            return

        print(f"📊 DEBUG: Snapshot thay đổi! {len(current_snapshot)} items")
        for c, p in zip(current_snapshot, self.previous_data):
            if c != p:
                print(f"  Δ [{c.get('name','')}] status: {p.get('status','')} → {c.get('status','')}, ipwan: {p.get('ipwan','')} → {c.get('ipwan','')}")

        self.is_sending = True

        def send():
            try:
                prefix = self.prefix_var.get().strip()
                prev_dict = {f"{item['ip']}:{item['name']}:{item['port']}": item for item in self.previous_data}
                curr_dict = {f"{item['ip']}:{item['name']}:{item['port']}": item for item in current_snapshot}

                changed_items = []
                for key, curr_item in curr_dict.items():
                    prev_item = prev_dict.get(key)
                    if prev_item:
                        status_changed = prev_item["status"] != curr_item["status"]
                        ipwan_changed = prev_item["ipwan"] != curr_item["ipwan"]
                        if status_changed or ipwan_changed:
                            changed_items.append(curr_item)
                            print(
                                f"🔔 Thay đổi [{curr_item['name']}]: Status {prev_item['status']}→{curr_item['status']}, "
                                f"IPWAN {prev_item['ipwan']}→{curr_item['ipwan']}"
                            )
                    else:
                        changed_items.append(curr_item)

                if changed_items:
                    messages = []
                    now = datetime.now(VIETNAM_TZ)
                    title = f"=== STATUS CHANGED - {now.strftime('%d/%m/%Y %H:%M:%S')} ==="
                    messages.append(title)

                    for item in changed_items:
                        msg = f"[{prefix}][{item['name']}] SRT {item['status']} | IPWAN: {item['ipwan']} | PORT: {item['port']}"
                        messages.append(msg)

                    payload = {"content": "\n".join(messages)}
                    resp = requests.post(webhook, json=payload, timeout=10)
                    if resp.status_code in [200, 204]:
                        print(f"✓ Sent {len(changed_items)} changed items to Discord")
                    else:
                        print(f"✗ Discord error: {resp.status_code}")

                self.previous_data = current_snapshot
            except Exception as e:
                print(f"✗ Failed to send: {e}")
            finally:
                self.is_sending = False

        threading.Thread(target=send, daemon=True).start()

    def refresh_data(self, show_dialog=True):
        if show_dialog:
            self.open_scan_dialog()
            return

        def fetch():
            url = f"{self.api_url}/logs"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        seen = set()
                        unique = []
                        for entry in data:
                            d = entry.get("data", {})
                            key = d.get("name", d.get("ip", "")) or d.get("ip", "")
                            if key not in seen:
                                seen.add(key)
                                unique.append(entry)
                        data = unique
                        if self.has_data_changed(self.data, data):
                            print("✓ Data changed, refreshing table...")
                            self.data = data
                            self.root.after(0, self.update_all_table)
                            self.update_selected_data()
                            self.root.after(0, self.update_selected_table)
                        else:
                            self.update_selected_data()
                            self.root.after(0, self.update_selected_table)
                    else:
                        self.data = []
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"HTTP {resp.status_code}: {resp.text}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"ERROR: {str(e)}"))

        threading.Thread(target=fetch, daemon=True).start()

    def has_data_changed(self, old_data, new_data):
        def build_set(data_list):
            s = set()
            for entry in data_list:
                d = entry.get("data", {})
                key = d.get("name", d.get("ip", "")) or d.get("ip", "")
                s.add(key)
            return s

        return build_set(old_data) != build_set(new_data)

    def is_in_selected(self, entry):
        """Check if entry is in selected list - Check by Name or IP"""
        d = entry.get("data", {})
        name = d.get("name", "")
        ip = d.get("ip", "")
        for sel in self.selected_data:
            sel_d = sel.get("data", {})
            if name and sel_d.get("name") == name:
                return True
            if ip and sel_d.get("ip") == ip:
                return True
        return False

    def toggle_select_all(self):
        if not self.left_table_checkboxes:
            return
        state = self.select_all_var.get()
        for _, (_, var, _) in self.left_table_checkboxes.items():
            var.set(state)

    def on_checkbox_toggle(self, entry, checkbox_var):
        all_checked = all(var.get() for _, var, _ in self.left_table_checkboxes.values())
        self.select_all_var.set(all_checked)

    def add_to_selected(self, event=None):
        added_count = 0
        print("\n=== ADD TO SELECTED DEBUG ===")
        print(f"Total checkboxes: {len(self.left_table_checkboxes)}")

        for idx, (_, var, entry) in self.left_table_checkboxes.items():
            ip = entry.get("data", {}).get("ip", "")
            port = entry.get("data", {}).get("port", "")
            is_checked = var.get()
            already_in = self.is_in_selected(entry)
            print(f"  [{idx}] IP:{ip} Port:{port} - Checked:{is_checked} AlreadyIn:{already_in}")
            if is_checked and not already_in:
                self.selected_data.append(entry)
                added_count += 1
                print("    → ADDED!")

        unique = {}
        for entry in self.selected_data:
            d = entry.get("data", {})
            key = d.get("name", d.get("ip", "")) or d.get("ip", "")
            if key not in unique:
                unique[key] = entry
        self.selected_data = list(unique.values())

        print(f"Total added: {added_count}")
        if added_count > 0:
            print(f"✓ Successfully added: {added_count} item(s)")
            self.save_selected_to_database()
            self.update_all_table()
            self.update_selected_table()
        else:
            messagebox.showinfo("Info", "No new items to add. Check the boxes first!")

    def remove_single_item(self, idx):
        if idx < len(self.selected_data):
            removed = self.selected_data.pop(idx)
            rd = removed.get("data", {})
            print(f"✗ Removed: {rd.get('name', 'Unknown')}")
            if rd.get("ptz", False):
                ptz_key = f"{rd.get('name','')}:{rd.get('port','')}"
                self._stop_ptz_ping(ptz_key)
            self.update_all_table()
            self.update_selected_table()

    def remove_from_selected(self):
        if not self.selected_data:
            messagebox.showwarning("Warning", "No items in the selected list")
            return
        result = messagebox.askyesno("Confirm", f"Remove all {len(self.selected_data)} items?")
        if result:
            self.selected_data = []
            self.update_all_table()
            self.update_selected_table()
            print("✓ Cleared all selected items")

    def edit_name_dialog(self, idx):
        if idx >= len(self.selected_data):
            return

        old_name = self.selected_data[idx].get("data", {}).get("name", "")
        dialog = self._create_name_input_dialog(idx)
        new_name = dialog.get_input()
        if new_name and new_name.strip() and new_name != old_name:
            old_ip = self.selected_data[idx].get("data", {}).get("ip", "")
            self.selected_data[idx]["data"]["name"] = new_name.strip()

            def update_name():
                try:
                    update_data = {"old_name": old_name, "new_name": new_name.strip(), "ip": old_ip}
                    resp = requests.post(f"{self.api_url}/update_name", json=update_data, timeout=5)
                    if resp.status_code == 200:
                        print(f"✓ Updated: {old_name} → {new_name}")
                        self.refresh_data(show_dialog=False)
                    else:
                        print(f"✗ Update error: {resp.status_code}")
                except Exception as e:
                    print(f"✗ Error: {e}")

            threading.Thread(target=update_name, daemon=True).start()
            self.update_selected_table()

    def _create_name_input_dialog(self, idx):
        import customtkinter as ctk

        return ctk.CTkInputDialog(
            text=f"Edit name for {self.selected_data[idx].get('data', {}).get('ip', '')}:",
            title="Edit Name",
        )

    def _write_ptz_log(self, name, ms_or_timeout, status_changed=False, new_status=None):
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            today = datetime.now(VIETNAM_TZ).strftime("%d-%m-%Y")
            debug_dir = os.path.join(desktop, f"Debug {today}")
            os.makedirs(debug_dir, exist_ok=True)

            now_str = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
            safe_name = "".join(c for c in name if c.isalnum() or c in " _-.").strip() or "unknown"

            fpath = os.path.join(debug_dir, f"{safe_name}.txt")
            result_str = f"{ms_or_timeout}ms" if isinstance(ms_or_timeout, (int, float)) else "timeout"
            with open(fpath, "a", encoding="utf-8") as f:
                f.write(f"[{now_str}] - {result_str}\n")

            if status_changed and new_status in ("ON", "OFF"):
                epath = os.path.join(debug_dir, "error.txt")
                with open(epath, "a", encoding="utf-8") as f:
                    f.write(f"[{now_str}] [{name}] - {new_status}  ({result_str})\n")
        except Exception as e:
            print(f"⚠ PTZ log write error: {e}")

    def _write_debug_log(self, name, d, is_error=False):
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            today = datetime.now(VIETNAM_TZ).strftime("%d-%m-%Y")
            debug_dir = os.path.join(desktop, f"Debug {today}")
            os.makedirs(debug_dir, exist_ok=True)

            if is_error:
                fpath = os.path.join(debug_dir, "error.txt")
            else:
                safe_name = "".join(c for c in name if c.isalnum() or c in " _-.").strip() or "unknown"
                fpath = os.path.join(debug_dir, f"{safe_name}.txt")

            now_str = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
            ping_val = d.get("ping", None)
            ping_s = f"{ping_val:.0f}ms" if ping_val is not None else "—"
            cpu_val = d.get("cpu", None)
            cpu_s = f"{cpu_val:.1f}%" if cpu_val is not None else "—"
            mem_val = d.get("memory", None)
            mem_s = f"{mem_val:.1f}%" if mem_val is not None else "—"
            temp_val = d.get("temperature", None)
            temp_s = f"{temp_val}°C" if temp_val is not None else "—"
            app_s = "ON" if d.get("statusapp", 0) == 1 else "OFF"

            parts = [
                f"ip: {d.get('ip','')}  ",
                f"ipwan: {d.get('ipwan','')}  ",
            ]
            srt = get_first_srt(d)
            if d.get("ptz", False):
                parts.append(f"status: {d.get('status','')}  ")
                parts.append(f"port: {d.get('port','')}  ")
            else:
                parts.append(f"status: {srt.get('status', d.get('status',''))}  ")
                parts.append(f"port: {get_srt_ports_str(d) or d.get('port','')}  ")
            parts.extend([
                f"app: {app_s}  ",
                f"ping: {ping_s}  ",
                f"timeouts: {d.get('ping_timeouts', 0)}  ",
                f"cpu: {cpu_s}  ",
                f"ram: {mem_s}  ",
                f"temp: {temp_s}",
            ])
            line = f"[{now_str}] [{name}] - " + "".join(parts) + "\n" if is_error else f"[{now_str}] - " + "".join(parts) + "\n"

            with open(fpath, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            print(f"⚠ Log write error: {e}")

    def update_selected_data(self):
        for i, sel_entry in enumerate(self.selected_data):
            sel_d = sel_entry.get("data", {})
            if sel_d.get("ptz", False):
                continue

            sel_name = sel_d.get("name", "")
            matched = False
            for entry in self.data:
                entry_d = entry.get("data", {})
                entry_name = entry_d.get("name", "")

                if sel_name and entry_name and sel_name == entry_name:
                    self.selected_data[i] = entry
                    matched = True
                    break
                elif not sel_name and sel_d.get("ip", "") and sel_d.get("ip", "") == entry_d.get("ip", ""):
                    self.selected_data[i] = entry
                    matched = True
                    break

            if matched:
                new_d = self.selected_data[i].get("data", {})
                disp_name = new_d.get("name", "") or sel_name
                new_srt = get_first_srt(new_d)
                old_srt = get_first_srt(sel_d)
                old_status = old_srt.get("status", sel_d.get("status", ""))
                new_status = new_srt.get("status", new_d.get("status", ""))
                status_changed = old_status != new_status and new_status in ("ON", "OFF") and old_status in ("ON", "OFF")
                now_ts = time.time()
                since_last = now_ts - self._log_last_write.get(disp_name, 0)
                if since_last >= 5 or status_changed:
                    self._log_last_write[disp_name] = now_ts
                    threading.Thread(target=self._write_debug_log, args=(disp_name, new_d, False), daemon=True).start()
                if status_changed:
                    threading.Thread(target=self._write_debug_log, args=(disp_name, new_d, True), daemon=True).start()

    def clear_selected(self):
        self._stop_all_ptz_pings()
        self.selected_data = []
        self.save_selected_to_database()
        self.update_selected_table()
        self.update_all_table()
        self.detail_text.delete("1.0", "end")

    def _start_ptz_ping(self, ptz_key):
        if ptz_key in self.ptz_ping_threads:
            return
        self.ptz_ping_threads[ptz_key] = {"running": True}
        t = threading.Thread(target=self._ptz_ping_loop, args=(ptz_key,), daemon=True)
        self.ptz_ping_threads[ptz_key]["thread"] = t
        t.start()
        print(f"📡 Started PTZ ping for [{ptz_key}]")

    def _stop_ptz_ping(self, ptz_key):
        if ptz_key in self.ptz_ping_threads:
            self.ptz_ping_threads[ptz_key]["running"] = False
            del self.ptz_ping_threads[ptz_key]
            print(f"⏹ Stopped PTZ ping for [{ptz_key}]")

    def _stop_all_ptz_pings(self):
        for key in list(self.ptz_ping_threads.keys()):
            self.ptz_ping_threads[key]["running"] = False
        self.ptz_ping_threads.clear()
        print("⏹ Stopped all PTZ pings")

    def _ptz_ping_loop(self, ptz_key):
        while ptz_key in self.ptz_ping_threads and self.ptz_ping_threads[ptz_key]["running"]:
            try:
                ptz_entry = None
                ptz_idx = None
                for i, entry in enumerate(self.selected_data):
                    d = entry.get("data", {})
                    if d.get("ptz", False) and f"{d.get('name','')}:{d.get('port','')}" == ptz_key:
                        ptz_entry = entry
                        ptz_idx = i
                        break

                if ptz_entry is None:
                    break

                ip = ptz_entry.get("data", {}).get("ip", "")
                if not ip:
                    time.sleep(5)
                    continue

                result = subprocess.run(["ping", "-n", "1", "-w", "2000", ip], capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    output = result.stdout.decode("cp1252", errors="ignore")
                except Exception:
                    output = result.stdout.decode("utf-8", errors="ignore")

                is_up = "ttl=" in output.lower()
                new_status = "ON" if is_up else "OFF"
                old_status = ptz_entry.get("data", {}).get("status", "")
                status_changed = new_status != old_status and old_status in ("ON", "OFF") and new_status in ("ON", "OFF")

                ms_match = re.search(r"time[=<](\d+)", output, re.IGNORECASE)
                ping_ms = int(ms_match.group(1)) if ms_match else None

                if new_status != old_status:
                    self.selected_data[ptz_idx]["data"]["status"] = new_status
                    print(f"📡 PTZ [{ptz_key}] status: {old_status or '—'} → {new_status}")
                    self.root.after(0, self.update_selected_table)
                    if self.auto_send_enabled:
                        self.root.after(100, self.send_to_discord_auto)

                ptz_name = ptz_entry.get("data", {}).get("name", ptz_key)
                log_val = ping_ms if is_up else "timeout"
                threading.Thread(target=self._write_ptz_log, args=(ptz_name, log_val, status_changed, new_status), daemon=True).start()
            except Exception as e:
                print(f"⚠ PTZ ping error [{ptz_key}]: {e}")

            time.sleep(5)

    def save_selected_to_file(self):
        vmping_list = []
        if hasattr(self, "ping_hosts"):
            for host, info in self.ping_hosts.items():
                vmping_list.append({"host": host, "name": info.get("name", "")})
        ptz_list = []
        for entry in self.selected_data:
            d = entry.get("data", {})
            if d.get("ptz", False):
                ptz_list.append({"name": d.get("name", ""), "ip": d.get("ip", ""), "port": d.get("port", ""), "ipwan": d.get("ipwan", "")})

        data_to_save = {"webhook": self.webhook_var.get(), "prefix": self.prefix_var.get(), "vmping": vmping_list, "ptz": ptz_list}
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")], initialfile="selected_monitors.json")
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Success", f"Saved monitor config to:\n{filename}")
                print(f"✓ Saved monitor config to: {filename} (including {len(ptz_list)} PTZ entries)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
                print(f"✗ Save error: {e}")

    def load_selected_from_file(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")], title="Open Monitor Config")
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                if not isinstance(loaded_data, dict):
                    messagebox.showerror("Error", "Invalid file format. Expected a JSON object.")
                    return
                if "webhook" in loaded_data:
                    self.webhook_var.set(loaded_data["webhook"])
                if "prefix" in loaded_data:
                    self.prefix_var.set(loaded_data["prefix"])
                if "vmping" in loaded_data and isinstance(loaded_data["vmping"], list):
                    self.clear_all_pings()
                    for ping_item in loaded_data["vmping"]:
                        host = ""
                        name = ""

                        if isinstance(ping_item, str):
                            # Backward compatibility: old files only store host string
                            host = ping_item.strip()
                        elif isinstance(ping_item, dict):
                            host = str(ping_item.get("host", "")).strip()
                            name = str(ping_item.get("name", "")).strip()

                        if host:
                            self._create_ping_card(host, name)
                    self.start_all_pings()
                    self.ping_count_label.configure(text=f"{len(self.ping_hosts)} monitors")

                ptz_count = 0
                if "ptz" in loaded_data and isinstance(loaded_data["ptz"], list):
                    now = datetime.now(VIETNAM_TZ).isoformat()
                    for ptz in loaded_data["ptz"]:
                        name = ptz.get("name", "")
                        port = ptz.get("port", "")
                        already_exists = False
                        for sel in self.selected_data:
                            sel_d = sel.get("data", {})
                            if sel_d.get("name", "") == name and sel_d.get("port", "") == port:
                                already_exists = True
                                break
                        if not already_exists:
                            ptz_entry = {
                                "timestamp": now,
                                "data": {
                                    "name": name,
                                    "ip": ptz.get("ip", ""),
                                    "ipwan": ptz.get("ipwan", ""),
                                    "status": "",
                                    "port": port,
                                    "statusapp": 0,
                                    "ptz": True,
                                },
                            }
                            self.selected_data.append(ptz_entry)
                            ptz_count += 1
                            self._start_ptz_ping(f"{name}:{port}")
                    self.update_selected_table()
                    if ptz_count > 0:
                        print(f"✓ Loaded {ptz_count} PTZ entries from file")

                messagebox.showinfo("Success", f"Loaded config from:\n{filename}")
                print(f"✓ Loaded config from: {filename}")
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON file:\n{str(e)}")
                print(f"✗ JSON decode error: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
                print(f"✗ Load error: {e}")

    def save_selected_to_database(self):
        def save():
            try:
                url = f"{self.api_url}/save_selected_list"
                payload = {"selected_data": self.selected_data}
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    print(f"✓ Saved {len(self.selected_data)} items to database")
                else:
                    print(f"✗ Save error: {resp.status_code}")
            except Exception as e:
                print(f"✗ Failed to save to database: {e}")

        threading.Thread(target=save, daemon=True).start()

    def load_selected_from_database(self):
        def load():
            try:
                url = f"{self.api_url}/load_selected_list"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    loaded_data = resp.json()
                    if isinstance(loaded_data, list):
                        unique = {}
                        for entry in loaded_data:
                            d = entry.get("data", {})
                            key = d.get("name", d.get("ip", "")) or d.get("ip", "")
                            if key not in unique:
                                unique[key] = entry
                        self.selected_data = list(unique.values())
                        print(f"✓ Loaded {len(self.selected_data)} items from database (unique)")
                        for entry in self.selected_data:
                            d = entry.get("data", {})
                            if d.get("ptz", False):
                                ptz_key = f"{d.get('name','')}:{d.get('port','')}"
                                self.root.after(0, lambda k=ptz_key: self._start_ptz_ping(k))
                        self.root.after(0, self.update_selected_table)
                        self.root.after(0, self.update_all_table)
                    else:
                        print("⚠ Invalid data format from database")
                else:
                    print(f"✗ Load error: {resp.status_code}")
            except Exception as e:
                print(f"✗ Failed to load from database: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _looks_like_ping_target(self, value):
        v = str(value or "").strip()
        if not v or " " in v or "|" in v:
            return False
        if v.lower() == "localhost":
            return True
        # Common ping target patterns: IPv4, domain-like host, or IPv6-like.
        if "." in v or ":" in v:
            return True
        return False

    def _normalize_ping_input(self, name, host):
        n = str(name or "").strip()
        h = str(host or "").strip()
        # Keep add behavior deterministic: Name stays name, Host stays host.
        # Only when host is empty and name looks like a ping target, treat it as host.
        if not h and self._looks_like_ping_target(n):
            return "", n
        return n, h

    def add_ping_host(self):
        raw_name = self.ping_name_entry.get().strip() if hasattr(self, "ping_name_entry") else ""
        raw_host = self.ping_ip_entry.get().strip()
        name, host = self._normalize_ping_input(raw_name, raw_host)
        if not host:
            return
        if host in self.ping_hosts:
            messagebox.showwarning("vmPing", f"{host} đang được monitor!")
            return
        if hasattr(self, "ping_name_entry"):
            self.ping_name_entry.delete(0, "end")
        self.ping_ip_entry.delete(0, "end")
        self._create_ping_card(host, name)
        self.start_ping_host(host)
        self.ping_count_label.configure(text=f"{len(self.ping_hosts)} monitors")

    def start_ping_host(self, host):
        if host not in self.ping_hosts:
            return
        info = self.ping_hosts[host]
        if info["running"]:
            return
        info["running"] = True
        info["toggle_btn"].configure(text="⏹")
        t = threading.Thread(target=self._ping_loop, args=(host,), daemon=True)
        info["thread"] = t
        t.start()

    def stop_ping_host(self, host):
        if host not in self.ping_hosts:
            return
        self.ping_hosts[host]["running"] = False
        self.ping_hosts[host]["toggle_btn"].configure(text="▶")
        self.ping_hosts[host]["title_bar"].configure(fg_color="#555555")

    def toggle_ping_host(self, host):
        if host not in self.ping_hosts:
            return
        if self.ping_hosts[host]["running"]:
            self.stop_ping_host(host)
        else:
            self.start_ping_host(host)

    def _resolve_ping_target(self, host):
        info = self.ping_hosts.get(host, {})
        target = str(info.get("host", host)).strip() or str(host).strip()
        alt_name = str(info.get("name", "")).strip()

        # Handle legacy/swapped input where machine name was accidentally used as host
        # and the actual IP/hostname ended up in name.
        if (" " in target or "|" in target) and alt_name and (" " not in alt_name and "|" not in alt_name):
            target = alt_name

        return target

    def _ping_loop(self, host):
        info = self.ping_hosts[host]
        while info["running"]:
            try:
                ping_target = self._resolve_ping_target(host)
                result = subprocess.run(["ping", "-n", "1", "-w", "1000", ping_target], capture_output=True, timeout=4, creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    output = result.stdout.decode("cp1252", errors="ignore")
                except Exception:
                    output = result.stdout.decode("utf-8", errors="ignore")

                is_up = ("TTL=" in output.upper()) or (result.returncode == 0 and "ttl=" in output.lower())
                ms_val = None
                if is_up:
                    m = re.search(r"[=<](\d+)ms", output, re.IGNORECASE)
                    if m:
                        ms_val = int(m.group(1))

                info["sent"] += 1
                if is_up:
                    info["recv"] += 1
                    if ms_val is not None:
                        info["total_ms"] += ms_val
                    line = f"Reply from {ping_target}: time={ms_val}ms" if ms_val is not None else f"Reply from {ping_target}"
                else:
                    line = f"Request timeout for {ping_target}"

                lost = info["sent"] - info["recv"]
                avg_ms = f"{info['total_ms'] // info['recv']}ms" if info["recv"] > 0 else "—"
                stats_text = f"Sent: {info['sent']} | Recv: {info['recv']} | Lost: {lost} | Avg: {avg_ms}"
                title_color = "#4CAF50" if is_up else "#f44336"
                line_color = "#00ff00" if is_up else "#ff4444"

                def _upd(h=host, ln=line, lc=line_color, st=stats_text, tc=title_color):
                    if h not in self.ping_hosts:
                        return
                    inf = self.ping_hosts[h]
                    if not inf["running"]:
                        return
                    txt = inf["output_text"]
                    txt.configure(text_color=lc)
                    txt.insert("end", ln + "\n")
                    content = txt.get("1.0", "end-1c")
                    lines = content.split("\n")
                    if len(lines) > 200:
                        txt.delete("1.0", f"{len(lines)-200}.0")
                    txt.see("end")
                    inf["stats_label"].configure(text=st)
                    inf["title_bar"].configure(fg_color=tc)

                self.root.after(0, _upd)
            except Exception as exc:
                def _err(h=host, e=str(exc)):
                    if h not in self.ping_hosts:
                        return
                    inf = self.ping_hosts[h]
                    inf["output_text"].configure(text_color="#FF9800")
                    inf["output_text"].insert("end", f"Error: {e}\n")
                    inf["title_bar"].configure(fg_color="#FF9800")

                self.root.after(0, _err)

            time.sleep(1)

    def remove_ping_card(self, host):
        if host not in self.ping_hosts:
            return
        self.ping_hosts[host]["running"] = False
        self.ping_hosts[host]["card"].destroy()
        del self.ping_hosts[host]
        self._rebuild_ping_grid()
        self.ping_count_label.configure(text=f"{len(self.ping_hosts)} monitors")

    def stop_all_pings(self):
        for host in list(self.ping_hosts.keys()):
            self.stop_ping_host(host)

    def start_all_pings(self):
        for host in list(self.ping_hosts.keys()):
            self.start_ping_host(host)

    def clear_all_pings(self):
        for host in list(self.ping_hosts.keys()):
            self.ping_hosts[host]["running"] = False
            self.ping_hosts[host]["card"].destroy()
        self.ping_hosts.clear()
        self.ping_count_label.configure(text="0 monitors")
