import customtkinter as ctk

try:
    from .logic import ServerDataGUILogicMixin
    from .ui import ServerDataGUIUIMixin
except ImportError:
    try:
        # PyInstaller / script execution with package available
        from server_gui_advanced.logic import ServerDataGUILogicMixin
        from server_gui_advanced.ui import ServerDataGUIUIMixin
    except ImportError:
        # Allow running this file directly: python main.py
        from logic import ServerDataGUILogicMixin
        from ui import ServerDataGUIUIMixin


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ServerDataGUI(ServerDataGUIUIMixin, ServerDataGUILogicMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("Server Log Viewer - Dual Panel")
        self.root.geometry("2000x750")
        self.root.after(100, lambda: self.root.state("zoomed"))

        self.api_url = "https://tooldiscordvmix.onrender.com"
        self.ws_url = "wss://tooldiscordvmix.onrender.com/ws"
        self.webhook_var = ctk.StringVar(value="")
        self.prefix_var = ctk.StringVar(value="SRT")

        self.data = []
        self.selected_data = []
        self.previous_data = []
        self.auto_send_enabled = False
        self.is_sending = False
        self.ptz_ping_threads = {}
        self._log_last_write = {}

        self.ws = None
        self.ws_connected = False
        self.ws_thread = None
        self.use_websocket = True
        self.ws_reconnect_attempts = 0
        self.rest_polling_active = False

        self.setup_main_ui()

        self.refresh_data(show_dialog=False)
        self.load_selected_from_database()

        if self.use_websocket:
            self.connect_websocket()
        else:
            self.start_rest_polling_backup()


def main():
    root = ctk.CTk()
    ServerDataGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
