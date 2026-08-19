"""
Server Console GUI - Logic Module
Handles server lifecycle (start/stop), stdout/stderr redirection, and log queue management.
"""

import io
import logging
import os
import queue
import sys
import threading
import time
import urllib.request
from datetime import datetime

import socket
import pytz

VIETNAM_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def get_local_ip() -> str:
    """Get LAN IP address of current machine (e.g. 192.168.x.x, 10.x.x.x)."""
    # 1. Socket connection probes
    for target in [("8.8.8.8", 80), ("1.1.1.1", 80), ("10.255.255.255", 1)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(target)
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass

    # 2. Hostname lookup fallback
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass

    # 3. Network interface scan fallback via psutil
    try:
        import psutil
        for _iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address and not addr.address.startswith("127."):
                    return addr.address
    except Exception:
        pass

    return "127.0.0.1"


def get_wan_ip(timeout: float = 5.0) -> str:
    """Get the public (WAN) IP address of this machine via external API.

    Tries multiple services in order; falls back to LAN IP if all fail.
    """
    import sys as _sys
    services = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://api4.my-ip.io/ip",
        "https://checkip.amazonaws.com",
    ]
    last_err = None
    for url in services:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ip = resp.read().decode("utf-8").strip()
                # Validate it looks like an IP
                if ip and len(ip.split(".")) == 4:
                    return ip
        except Exception as e:
            last_err = e
            continue
    # Fallback to LAN IP if no WAN service responds
    lan = get_local_ip()
    raise RuntimeError(f"Tất cả WAN services thất bại (last: {last_err}). Dùng LAN IP: {lan}")


def update_web_env(wan_ip: str, port: int, lan_ip: str = "") -> bool:
    """Update web/.env to point BACKEND URLs at WAN IP and (optionally) LAN IP.

    Writes:
      VITE_BACKEND_BASE_URL        = http://<wan_ip>:<port>   (for external access)
      VITE_BACKEND_WS_URL          = ws://<wan_ip>:<port>/ws
      VITE_BACKEND_BASE_URL_LOCAL  = http://<lan_ip>:<port>   (for same-LAN access)
      VITE_BACKEND_WS_URL_LOCAL    = ws://<lan_ip>:<port>/ws

    Works both when running from source and when bundled as a PyInstaller EXE.
    Returns True if the file was updated successfully.
    """
    import sys as _sys
    try:
        if getattr(_sys, "frozen", False):
            exe_dir = os.path.dirname(os.path.abspath(_sys.executable))
            project_root = os.path.dirname(exe_dir)
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        env_path = os.path.join(project_root, "web", ".env")
        if not os.path.exists(env_path):
            return False

        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Keys we want to manage
        managed_keys = {
            "VITE_BACKEND_BASE_URL",
            "VITE_BACKEND_WS_URL",
            "VITE_BACKEND_BASE_URL_LOCAL",
            "VITE_BACKEND_WS_URL_LOCAL",
        }

        # Build replacement map
        replacements: dict[str, str] = {
            "VITE_BACKEND_BASE_URL": f"VITE_BACKEND_BASE_URL=http://{wan_ip}:{port}\n",
            "VITE_BACKEND_WS_URL": f"VITE_BACKEND_WS_URL=ws://{wan_ip}:{port}/ws\n",
        }
        if lan_ip:
            replacements["VITE_BACKEND_BASE_URL_LOCAL"] = f"VITE_BACKEND_BASE_URL_LOCAL=http://{lan_ip}:{port}\n"
            replacements["VITE_BACKEND_WS_URL_LOCAL"] = f"VITE_BACKEND_WS_URL_LOCAL=ws://{lan_ip}:{port}/ws\n"

        new_lines = []
        written = set()
        for line in lines:
            key = line.split("=")[0].strip() if "=" in line else ""
            if key in managed_keys:
                if key in replacements:
                    new_lines.append(replacements[key])
                    written.add(key)
                # If key not in replacements (e.g. LOCAL keys when no lan_ip), keep original
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Append any keys that weren't in the file yet
        for key, value in replacements.items():
            if key not in written:
                new_lines.append(value)

        with open(env_path, "w", encoding="utf-8", newline="") as f:
            f.writelines(new_lines)

        return True
    except Exception:
        return False


class QueueWriter(io.TextIOBase):
    """Custom stream writer that forwards all writes to a queue for GUI consumption.

    Also passes through to the original stream so console output still works
    when running outside the GUI (e.g. during development).
    """

    def __init__(self, log_queue: queue.Queue, original_stream, tag: str = ""):
        super().__init__()
        self.queue = log_queue
        self.original = original_stream
        self.tag = tag  # "stdout" or "stderr"

    def write(self, text: str):
        if text and text.strip():
            timestamp = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
            self.queue.put((timestamp, self.tag, text.rstrip("\n\r")))
        # Pass through to original stream
        if self.original:
            try:
                self.original.write(text)
                self.original.flush()
            except Exception:
                pass
        return len(text) if text else 0

    def flush(self):
        if self.original:
            try:
                self.original.flush()
            except Exception:
                pass

    def writable(self):
        return True

    # Required for uvicorn's logging compatibility
    def isatty(self):
        return False

    @property
    def encoding(self):
        return "utf-8"


class UvicornLogHandler(logging.Handler):
    """Capture uvicorn's logger output into the queue as well."""

    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            timestamp = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
            tag = "uvicorn"
            self.log_queue.put((timestamp, tag, msg))
        except Exception:
            pass


class ServerConsoleLogicMixin:
    """Mixin providing server start/stop logic and log redirection."""

    def _init_logic(self):
        self.log_queue: queue.Queue = queue.Queue()
        self.server_thread: threading.Thread | None = None
        self.server_running: bool = False
        self._uvicorn_server = None
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._start_time: float | None = None
        self._log_line_count: int = 0
        self._stop_event = threading.Event()

    def start_server(self):
        """Start the FastAPI/uvicorn server in a background thread."""
        if self.server_running:
            return

        self._stop_event.clear()
        self._start_time = time.time()
        self._log_line_count = 0

        # NOTE: Notifications được bật bình thường — server này là production local server
        # Để tắt notification thì set DISABLE_NOTIFICATIONS=1 trong môi trường trước khi chạy

        # Redirect stdout/stderr to queue
        sys.stdout = QueueWriter(self.log_queue, self._original_stdout, "stdout")
        sys.stderr = QueueWriter(self.log_queue, self._original_stderr, "stderr")

        self.server_running = True
        self.server_thread = threading.Thread(
            target=self._run_uvicorn,
            daemon=True,
            name="uvicorn-server",
        )
        self.server_thread.start()

        # Start the GUI log consumer
        self._schedule_log_poll()

    def _run_uvicorn(self):
        """Run uvicorn inside a thread with a controllable server instance."""
        try:
            import uvicorn

            # We need to import server.app here so all the module-level init
            # (MongoDB, Redis, etc.) runs while stdout is redirected → logs show in GUI.
            # Adjust sys.path so `server.py` can be imported from project root.
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            # Also set CWD to project root so relative file paths in server.py work
            try:
                os.chdir(project_root)
            except Exception:
                pass

            from server import app, PORT

            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=PORT,
                use_colors=False,
                log_level="info",
            )
            self._uvicorn_server = uvicorn.Server(config)

            # Inject our queue handler into uvicorn's loggers
            handler = UvicornLogHandler(self.log_queue)
            handler.setFormatter(logging.Formatter("%(message)s"))
            for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
                logger = logging.getLogger(logger_name)
                logger.addHandler(handler)

            lan_ip = get_local_ip()
            timestamp = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
            self.log_queue.put((timestamp, "system", f"🖧  LAN: http://{lan_ip}:{PORT}"))

            # Fetch WAN IP in background to avoid blocking server startup
            def _fetch_wan_and_notify():
                try:
                    wan_ip = get_wan_ip(timeout=8.0)
                    ts = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
                    self.log_queue.put((ts, "system", f"🌐 WAN: http://{wan_ip}:{PORT}"))
                    self.log_queue.put((ts, "system", f"🖧  LAN: http://{lan_ip}:{PORT}"))
                    self.log_queue.put((ts, "system", f"💡 Mẹo: Mở cổng {PORT} trong Windows Firewall & router port-forward để truy cập ngoài mạng."))

                    # Auto-update web/.env: ghi cả WAN + LAN để web tự detect
                    ok = update_web_env(wan_ip, PORT, lan_ip=lan_ip)
                    if ok:
                        self.log_queue.put((ts, "system", f"✓ web/.env đã cập nhật → WAN: {wan_ip}  |  LAN: {lan_ip}"))
                    else:
                        self.log_queue.put((ts, "system", "⚠ Không tìm thấy web/.env — cập nhật thủ công."))

                    # Notify the UI label with WAN IP (safe only if root still alive)
                    try:
                        self.root.after(0, lambda: self._update_server_url_label(wan_ip, PORT, lan_ip=lan_ip))
                    except Exception:
                        pass
                except RuntimeError as exc:
                    # get_wan_ip raises RuntimeError when all services fail
                    ts = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
                    self.log_queue.put((ts, "system", f"⚠ {exc}"))
                    # Fallback: still update .env with LAN-only
                    update_web_env(lan_ip, PORT, lan_ip=lan_ip)
                    try:
                        self.root.after(0, lambda: self._update_server_url_label(lan_ip, PORT, lan_ip=lan_ip))
                    except Exception:
                        pass
                except Exception as exc:
                    ts = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
                    self.log_queue.put((ts, "system", f"⚠ Lỗi lấy WAN IP: {exc}"))

            threading.Thread(target=_fetch_wan_and_notify, daemon=True, name="wan-ip-fetch").start()

            self._uvicorn_server.run()
        except Exception as e:
            timestamp = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
            self.log_queue.put((timestamp, "error", f"✗ Server error: {e}"))
        finally:
            self.server_running = False
            # Schedule UI update on main thread
            try:
                self.root.after(0, self._on_server_stopped)
            except Exception:
                pass

    def stop_server(self):
        """Gracefully stop the uvicorn server."""
        if not self.server_running:
            return

        timestamp = datetime.now(VIETNAM_TZ).strftime("%H:%M:%S")
        self.log_queue.put((timestamp, "system", "⏹ Đang dừng server..."))

        self._stop_event.set()
        if self._uvicorn_server:
            self._uvicorn_server.should_exit = True

        # Wait for thread to finish (max 5s)
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)

        self.server_running = False

        # Restore original stdout/stderr
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

        self._on_server_stopped()

    def _on_server_stopped(self):
        """Called when server thread exits (on main/UI thread)."""
        # Restore streams
        if sys.stdout is not self._original_stdout:
            sys.stdout = self._original_stdout
        if sys.stderr is not self._original_stderr:
            sys.stderr = self._original_stderr

        self.server_running = False
        self._uvicorn_server = None
        self._update_ui_state()

    def _schedule_log_poll(self):
        """Schedule periodic log queue polling on the GUI main thread."""
        if hasattr(self, "root"):
            self._poll_log_queue()

    def _poll_log_queue(self):
        """Drain the log queue and append lines to the GUI log widget."""
        batch = []
        try:
            while True:
                item = self.log_queue.get_nowait()
                batch.append(item)
        except queue.Empty:
            pass

        if batch:
            self._append_log_lines(batch)
            self._log_line_count += len(batch)

        # Update status bar
        if hasattr(self, "_update_status_bar"):
            self._update_status_bar()

        # Continue polling while server is running OR there are items in queue
        if self.server_running or not self.log_queue.empty():
            self.root.after(100, self._poll_log_queue)

    def get_uptime_str(self) -> str:
        """Get human-readable uptime string."""
        if not self._start_time or not self.server_running:
            return "—"
        elapsed = int(time.time() - self._start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
