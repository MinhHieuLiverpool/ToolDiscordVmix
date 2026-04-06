import queue
import socket
import sys
import threading
import tkinter as tk

import ttkbootstrap as ttk

try:
    from .logic import VmixMonitorLogicMixin
    from .ui import VmixMonitorUIMixin
    from .shared import SERVER_URL
except ImportError:
    try:
        from vmix_monitor_gui.logic import VmixMonitorLogicMixin
        from vmix_monitor_gui.ui import VmixMonitorUIMixin
        from vmix_monitor_gui.shared import SERVER_URL
    except ImportError:
        from logic import VmixMonitorLogicMixin
        from ui import VmixMonitorUIMixin
        from shared import SERVER_URL


SINGLE_INSTANCE_SOCKET = None


class VmixMonitorGUI(VmixMonitorUIMixin, VmixMonitorLogicMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("vMix Monitor Pro")
        try:
            self.root.iconbitmap("assets/Discord-Logo.ico")
        except Exception:
            pass

        self.ip_var = tk.StringVar(value=self.get_local_ip())
        self.server_url_var = tk.StringVar(value=SERVER_URL)
        self.name_var = tk.StringVar(value="")
        self.port_var = tk.StringVar(value="")
        self.is_running = False
        self.log_queue = queue.Queue()
        self.tray_icon = None
        self.port_list = []
        self.ping_timeout_count = 0
        self.vmix_api_port_var = tk.StringVar(value="8088")

        import requests as _req

        self.http_session = _req.Session()
        self._ping_ms = None
        self._ping_lock = threading.Lock()
        try:
            import psutil as _ps

            _ps.cpu_percent(interval=None)
        except Exception:
            pass
        threading.Thread(target=self._ping_bg_loop, daemon=True).start()

        self._vmix_file_cache = ("—", {})
        self._vmix_file_ts = 0.0
        self._net_last_sent = None
        self._net_last_recv = None
        self._net_last_ts = None
        self._stream_quality_cache = {}
        self._stream_quality_ts = 0.0
        self._vmix_bw_cache_ts = 0.0
        self._vmix_bw_cache_pid = ""
        self._vmix_bw_cache_send = None
        self._vmix_bw_cache_recv = None

        self.setup_ui()
        self.setup_tray()
        self.check_log_queue()
        self.load_data_from_database()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)


def ensure_single_instance():
    global SINGLE_INSTANCE_SOCKET
    try:
        SINGLE_INSTANCE_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        SINGLE_INSTANCE_SOCKET.bind(("127.0.0.1", 51234))
        return True
    except socket.error:
        return False


def focus_existing_window():
    try:
        import win32con
        import win32gui

        found = {"value": False}

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "vMix Monitor Pro" in title:
                    found["value"] = True
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
            return True

        win32gui.EnumWindows(callback, None)
        return found["value"]
    except (ImportError, Exception):
        return False


def main():
    try:
        import ctypes

        myappid = "vmixmonitor.pro.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    if not ensure_single_instance():
        focused = focus_existing_window()
        print("[INFO] vMix Monitor Pro đang chạy sẵn. Kiểm tra taskbar/system tray.")
        if not focused:
            import tkinter.messagebox as mb

            root = tk.Tk()
            root.withdraw()
            mb.showwarning(
                "Ứng dụng đang chạy",
                "vMix Monitor Pro đang chạy rồi!\n\n"
                "Kiểm tra taskbar hoặc system tray.",
                parent=root,
            )
            root.destroy()
        sys.exit(0)

    root = ttk.Window(
        title="vMix Monitor Pro",
        themename="darkly",
        size=(900, 700),
    )
    VmixMonitorGUI(root)
    root.mainloop()

    if SINGLE_INSTANCE_SOCKET:
        SINGLE_INSTANCE_SOCKET.close()


if __name__ == "__main__":
    main()
