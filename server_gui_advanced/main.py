import customtkinter as ctk

try:
    from .logic import ServerDataGUILogicMixin
    from .ui import ServerDataGUIUIMixin
    from .shared import DEFAULT_SERVER_URL
except ImportError:
    try:
        # PyInstaller / script execution with package available
        from server_gui_advanced.logic import ServerDataGUILogicMixin
        from server_gui_advanced.ui import ServerDataGUIUIMixin
        from server_gui_advanced.shared import DEFAULT_SERVER_URL
    except ImportError:
        # Allow running this file directly: python main.py
        from logic import ServerDataGUILogicMixin
        from ui import ServerDataGUIUIMixin
        from shared import DEFAULT_SERVER_URL


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ServerDataGUI(ServerDataGUIUIMixin, ServerDataGUILogicMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("Server Log Viewer - Dual Panel")
        self.root.geometry("2000x750")
        self.root.after(100, lambda: self.root.state("zoomed"))

        self.server_url_var = ctk.StringVar(value=DEFAULT_SERVER_URL)
        self.api_url = ""
        self.ws_url = ""
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

        self.load_settings()
        self.setup_main_ui()
        self.apply_server_url(reconnect=False, announce=False)

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
