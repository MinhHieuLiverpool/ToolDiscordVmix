"""
Server Console GUI - Main Entry Point
Combines UI and Logic mixins into a single application class.
"""

import os
import socket
import sys
import tkinter as tk

import customtkinter as ctk

try:
    from .logic import ServerConsoleLogicMixin
    from .ui import ServerConsoleUIMixin
except ImportError:
    try:
        from server_console_gui.logic import ServerConsoleLogicMixin
        from server_console_gui.ui import ServerConsoleUIMixin
    except ImportError:
        from logic import ServerConsoleLogicMixin
        from ui import ServerConsoleUIMixin


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


SINGLE_INSTANCE_SOCKET = None


class ServerConsoleGUI(ServerConsoleUIMixin, ServerConsoleLogicMixin):
    """Main application class combining UI and server logic."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Server Console GUI")
        self.root.geometry("1100x700")
        self.root.minsize(800, 500)

        # Set icon
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "cloud-server.ico")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "assets",
                    "cloud-server.ico",
                )
            if not os.path.exists(icon_path):
                icon_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "assets",
                    "Discord-Logo.ico",
                )
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        # Initialize logic state
        self._init_logic()

        # Build the UI
        self.setup_ui()

        # Update port label with actual port from config
        self._load_port_info()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _load_port_info(self):
        """Try to read PORT from server config and update the server URL label.

        WAN IP is fetched asynchronously so the GUI doesn't freeze on startup.
        """
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            try:
                from .logic import get_wan_ip
            except ImportError:
                from logic import get_wan_ip

            port = int(os.getenv("PORT", 8001))

            # _update_server_url_label is defined in ui.py (UIMixin);
            # call it on the main thread once WAN IP is resolved.
            def _resolve():
                try:
                    wan_ip = get_wan_ip(timeout=8.0)
                    self.root.after(0, lambda: self._update_server_url_label(wan_ip, port))
                except Exception as exc:
                    print(f"Warning: _load_port_info WAN fetch error: {exc}")
                    # Fallback to LAN IP
                    try:
                        from .logic import get_local_ip
                    except ImportError:
                        from logic import get_local_ip
                    lan_ip = get_local_ip()
                    try:
                        self.root.after(0, lambda: self._update_server_url_label(lan_ip, port))
                    except Exception:
                        pass

            import threading
            threading.Thread(target=_resolve, daemon=True, name="port-info-wan").start()
        except Exception as e:
            print(f"Warning: _load_port_info error: {e}")

    def _on_closing(self):
        """Handle window close - stop server if running."""
        if self.server_running:
            self.stop_server()
        self.root.destroy()


def ensure_single_instance() -> bool:
    """Prevent multiple instances by binding a unique port."""
    global SINGLE_INSTANCE_SOCKET
    try:
        SINGLE_INSTANCE_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        SINGLE_INSTANCE_SOCKET.bind(("127.0.0.1", 51237))  # Unique port for this app
        return True
    except socket.error:
        return False


def focus_existing_window() -> bool:
    """Try to bring existing window to foreground (Windows only)."""
    try:
        import win32con
        import win32gui

        found = {"value": False}

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "Server Console GUI" in title:
                    found["value"] = True
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
            return True

        win32gui.EnumWindows(callback, None)
        return found["value"]
    except (ImportError, Exception):
        return False


def main():
    """Application entry point."""
    # Set Windows app ID for taskbar grouping
    try:
        import ctypes

        myappid = "serverconsole.gui.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    # Single instance check
    if not ensure_single_instance():
        focused = focus_existing_window()
        print("[INFO] Server Console GUI đang chạy sẵn.")
        if not focused:
            import tkinter.messagebox as mb

            tmp_root = tk.Tk()
            tmp_root.withdraw()
            mb.showwarning(
                "Ứng dụng đang chạy",
                "Server Console GUI đang chạy rồi!\n\n"
                "Kiểm tra taskbar.",
                parent=tmp_root,
            )
            tmp_root.destroy()
        sys.exit(0)

    root = ctk.CTk()
    root.title("Server Console GUI")
    ServerConsoleGUI(root)
    root.mainloop()

    if SINGLE_INSTANCE_SOCKET:
        SINGLE_INSTANCE_SOCKET.close()


if __name__ == "__main__":
    main()
