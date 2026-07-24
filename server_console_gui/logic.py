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

        # Disable notifications in dev/GUI mode
        os.environ["DISABLE_NOTIFICATIONS"] = "1"

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
