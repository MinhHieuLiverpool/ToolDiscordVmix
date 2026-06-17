import os
import sys
import socket
import ctypes

class IN_ADDR(ctypes.Structure):
    _fields_ = [("s_addr", ctypes.c_uint32)]

class SOCKADDR_IN(ctypes.Structure):
    _fields_ = [
        ("sin_family", ctypes.c_short),
        ("sin_port", ctypes.c_ushort),
        ("sin_addr", IN_ADDR),
        ("sin_zero", ctypes.c_char * 8)
    ]

# Cấu trúc thống kê SRT_TRACEBSTATS (CBytePerfMon) từ thư viện SRT SDK
class SRT_TRACEBSTATS(ctypes.Structure):
    _fields_ = [
        # global measurements
        ("msTimeStamp", ctypes.c_int64),
        ("pktSentTotal", ctypes.c_int64),
        ("pktRecvTotal", ctypes.c_int64),
        ("pktSndLossTotal", ctypes.c_int),
        ("pktRcvLossTotal", ctypes.c_int),
        ("pktRetransTotal", ctypes.c_int),
        ("pktSentACKTotal", ctypes.c_int),
        ("pktRecvACKTotal", ctypes.c_int),
        ("pktSentNAKTotal", ctypes.c_int),
        ("pktRecvNAKTotal", ctypes.c_int),
        ("usSndDuration", ctypes.c_int64),

        # local measurements
        ("pktSent", ctypes.c_int64),
        ("pktRecv", ctypes.c_int64),
        ("pktSndLoss", ctypes.c_int),
        ("pktRcvLoss", ctypes.c_int),
        ("pktRetrans", ctypes.c_int),
        ("mbpsSendRate", ctypes.c_double),
        ("mbpsRecvRate", ctypes.c_double),
        ("usSndDurationPeriod", ctypes.c_int64),

        # instant measurements
        ("usPktSndPeriod", ctypes.c_double),
        ("pktFlowWindow", ctypes.c_int),
        ("pktCongestionWindow", ctypes.c_int),
        ("pktFlightSize", ctypes.c_int),
        ("msRTT", ctypes.c_double),
        ("mbpsBandwidth", ctypes.c_double),
        ("byteAvailSndBuf", ctypes.c_int),
        ("byteAvailRcvBuf", ctypes.c_int),

        # added in SRT
        ("pktSndDropTotal", ctypes.c_int),
        ("pktRcvDropTotal", ctypes.c_int),
        ("pktRcvUndecryptTotal", ctypes.c_int),
        ("pktSndDrop", ctypes.c_int),
        ("pktRcvDrop", ctypes.c_int),
        ("pktRcvUndecrypt", ctypes.c_int),
        ("byteSndBuf", ctypes.c_int),
        ("byteRcvBuf", ctypes.c_int),
        ("byteSndBufClientId", ctypes.c_int),
        ("byteRcvBufClientId", ctypes.c_int),
        ("mbpsMaxBW", ctypes.c_double),
        ("byteRxBuf", ctypes.c_int),
        ("byteRxBufClientId", ctypes.c_int),
        
        # Buffer dự phòng để tránh tràn bộ nhớ khi libsrt được cập nhật cấu trúc lớn hơn
        ("padding", ctypes.c_byte * 256)
    ]

class SRTServer:
    def __init__(self, dll_path=None):
        self.dll_path = dll_path
        self.srt = None
        self.server_sock = -1
        self.client_sock = -1
        self.is_started = False
        self._load_library()
        self._init_prototypes()

    def _load_library(self):
        if self.dll_path:
            paths = [self.dll_path]
        else:
            paths = [
                r"D:\vMix\libsrt.dll",
                r"D:\vMix\streaming\libsrt.dll",
                r"D:\vMix\filters64\libsrt.dll",
                r"C:\Program Files\vMix\libsrt.dll",
                r"C:\Program Files (x86)\vMix\libsrt.dll",
            ]

        loaded_path = None
        for path in paths:
            if os.path.exists(path):
                loaded_path = path
                # Thêm các thư mục tìm kiếm DLL để Windows tìm thấy các file phụ thuộc (dependencies)
                dll_dir = os.path.dirname(path)
                vmix_root = os.path.dirname(dll_dir) if "avplugins" in dll_dir.lower() else dll_dir
                if hasattr(os, "add_dll_directory"):
                    try:
                        os.add_dll_directory(dll_dir)
                        if dll_dir != vmix_root:
                            os.add_dll_directory(vmix_root)
                    except Exception as dll_err:
                        print(f"[DEBUG] Không thể thêm dll directory: {dll_err}")
                break

        if not loaded_path:
            # Thử tìm trong thư mục hiện tại
            if os.path.exists("libsrt.dll"):
                loaded_path = os.path.abspath("libsrt.dll")
                if hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(os.path.dirname(loaded_path))
            else:
                loaded_path = "libsrt.dll"  # Thử tìm trong PATH hệ thống

        try:
            print(f"Loading SRT library from: {loaded_path}")
            # Sử dụng CDLL với winmode=0 để đảm bảo sử dụng các đường dẫn DLL đã thêm qua add_dll_directory
            if sys.platform == "win32" and hasattr(ctypes, "WinDLL"):
                self.srt = ctypes.CDLL(loaded_path, winmode=0)
            else:
                self.srt = ctypes.CDLL(loaded_path)
        except Exception as e:
            raise RuntimeError(
                f"Không thể load libsrt.dll từ path '{loaded_path}': {e}\n"
                "Mẹo: Đảm bảo bạn đã cài đặt vMix trên máy này hoặc copy file libsrt.dll vào thư mục chạy script."
            )

    def _init_prototypes(self):
        # Khởi tạo các nguyên mẫu hàm (Function Prototypes) trong DLL
        self.srt.srt_startup.argtypes = []
        self.srt.srt_startup.restype = ctypes.c_int

        self.srt.srt_cleanup.argtypes = []
        self.srt.srt_cleanup.restype = ctypes.c_int

        self.srt.srt_create_socket.argtypes = []
        self.srt.srt_create_socket.restype = ctypes.c_int

        self.srt.srt_bind.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        self.srt.srt_bind.restype = ctypes.c_int

        self.srt.srt_listen.argtypes = [ctypes.c_int, ctypes.c_int]
        self.srt.srt_listen.restype = ctypes.c_int

        self.srt.srt_accept.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
        self.srt.srt_accept.restype = ctypes.c_int

        self.srt.srt_recv.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        self.srt.srt_recv.restype = ctypes.c_int

        self.srt.srt_bstats.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        self.srt.srt_bstats.restype = ctypes.c_int

        self.srt.srt_close.argtypes = [ctypes.c_int]
        self.srt.srt_close.restype = ctypes.c_int

    def startup(self):
        if self.srt.srt_startup() != 0:
            raise RuntimeError("srt_startup failed")
        self.is_started = True

    def create_socket(self):
        self.server_sock = self.srt.srt_create_socket()
        if self.server_sock < 0:
            raise RuntimeError("Cannot create SRT socket")
        return self.server_sock

    def bind(self, ip, port):
        addr = SOCKADDR_IN()
        addr.sin_family = 2  # AF_INET
        addr.sin_port = socket.htons(port)
        addr.sin_addr.s_addr = ctypes.c_uint32.from_buffer_copy(socket.inet_aton(ip)).value

        if self.srt.srt_bind(self.server_sock, ctypes.byref(addr), ctypes.sizeof(addr)) != 0:
            raise RuntimeError(f"Cannot bind to {ip}:{port}. Đảm bảo port này chưa bị phần mềm khác sử dụng.")

    def listen(self, backlog=5):
        if self.srt.srt_listen(self.server_sock, backlog) != 0:
            raise RuntimeError("srt_listen failed")

    def accept(self):
        client_addr = SOCKADDR_IN()
        addr_len = ctypes.c_int(ctypes.sizeof(client_addr))
        self.client_sock = self.srt.srt_accept(self.server_sock, ctypes.byref(client_addr), ctypes.byref(addr_len))
        if self.client_sock < 0:
            raise RuntimeError("Accept connection failed")
        return self.client_sock

    def recv(self, data_buffer, buf_size):
        return self.srt.srt_recv(self.client_sock, data_buffer, buf_size)

    def bstats(self, stats_struct, clear=1):
        return self.srt.srt_bstats(self.client_sock, ctypes.byref(stats_struct), clear)

    def close_client(self):
        if self.client_sock >= 0:
            self.srt.srt_close(self.client_sock)
            self.client_sock = -1

    def close_server(self):
        if self.server_sock >= 0:
            self.srt.srt_close(self.server_sock)
            self.server_sock = -1

    def cleanup(self):
        if self.is_started:
            self.srt.srt_cleanup()
            self.is_started = False
