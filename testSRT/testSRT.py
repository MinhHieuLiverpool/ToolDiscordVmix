import os
import sys
import time
import ctypes

# Ép buộc output encoding là UTF-8 trên Windows để không bị lỗi hiển thị tiếng Việt
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thêm thư mục hiện tại vào sys.path để import module SRTServer
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from SRTServer import SRTServer, SRT_TRACEBSTATS
except ImportError as err:
    print(f"[ERROR] Không thể import SRTServer: {err}")
    sys.exit(1)

# Chạy dịch vụ SRT Listener
def main():
    try:
        server = SRTServer()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    try:
        # Khởi tạo thư viện SRT
        server.startup()
    except Exception as e:
        print(f"[ERROR] Startup failed: {e}")
        return

    try:
        # Tạo socket SRT
        server.create_socket()
    except Exception as e:
        print(f"[ERROR] {e}")
        server.cleanup()
        return

    try:
        # Đọc IP và Port từ tham số dòng lệnh hoặc dùng mặc định
        BIND_IP = "0.0.0.0"
        PORT = 11012

        if len(sys.argv) > 1:
            BIND_IP = sys.argv[1]
        if len(sys.argv) > 2:
            try:
                PORT = int(sys.argv[2])
            except ValueError:
                print(f"[WARN] Port không hợp lệ, dùng mặc định {PORT}")

        # Bind socket
        try:
            server.bind(BIND_IP, PORT)
        except Exception as e:
            print(f"[ERROR] {e}")
            server.close_server()
            server.cleanup()
            return

        # Listen
        try:
            server.listen(5)
        except Exception as e:
            print(f"[ERROR] {e}")
            server.close_server()
            server.cleanup()
            return

        # Lấy IP hiển thị hướng dẫn
        display_ip = "127.0.0.1" if BIND_IP == "0.0.0.0" else BIND_IP

        print(f"\n=======================================================")
        print(f"📡 SRT LISTENER ĐANG CHỜ KẾT NỐI TẠI {BIND_IP}:{PORT}")
        print(f"=======================================================")
        print(f"Hướng dẫn cấu hình gửi SRT từ vMix:")
        print(f" 1. Mở vMix, bấm vào hình răng cưa ở mục 'External / Stream' (hoặc đầu ra Output).")
        print(f" 2. Chọn kiểu đầu ra là: SRT.")
        print(f" 3. Điền các thông số cấu hình:")
        print(f"    - Type: Caller")
        print(f"    - Hostname: {display_ip}")
        print(f"    - Port: {PORT}")
        print(f" 4. Bấm 'OK' và tích chọn kích hoạt phát đầu ra SRT đó.")
        print(f"=======================================================\n")

        # Chờ Caller kết nối tới
        try:
            server.accept()
        except Exception as e:
            print(f"[ERROR] {e}")
            return

        print("✔ ĐÃ KẾT NỐI! Đang nhận stream và đo thông số realtime...")
        
        # Buffer để hứng luồng data
        buf_size = 1316 * 10
        data_buffer = ctypes.create_string_buffer(buf_size)
        last_stats_time = time.time()

        while True:
            # Nhận gói tin SRT
            bytes_read = server.recv(data_buffer, buf_size)
            if bytes_read <= 0:
                print("\n🔌 Kết nối đã bị ngắt hoặc vMix dừng gửi.")
                break

            # Đo và in thông số mỗi 1 giây
            now = time.time()
            if now - last_stats_time >= 1.0:
                stats = SRT_TRACEBSTATS()
                if server.bstats(stats, 1) == 0:
                    # Clear màn hình terminal
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                    print("==================================================")
                    print("     THÔNG SỐ SRT REALTIME (NHẬN TỪ VMIX LOCAL)   ")
                    print("==================================================")
                    print(f" Thời gian kết nối (ms):   {stats.msTimeStamp}")
                    print(f" Độ trễ RTT (ms):          {stats.msRTT:.2f} ms")
                    print(f" Băng thông ước tính (BW): {stats.mbpsBandwidth:.2f} Mbps")
                    print(f" Tốc độ nhận luồng:        {stats.mbpsRecvRate:.2f} Mbps")
                    print("--------------------------------------------------")
                    print(f" Tổng số gói tin đã Nhận:  {stats.pktRecvTotal} (Unique: {stats.pktRecv})")
                    print(f" Số gói tin bị Mất (Loss): {stats.pktRcvLossTotal} (Period: {stats.pktRcvLoss})")
                    print(f" Số gói tin bị Hủy (Drop): {stats.pktRcvDropTotal} (Period: {stats.pktRcvDrop})")
                    print("==================================================")
                    print(" Bấm Ctrl + C để dừng đo và đóng socket.")
                
                last_stats_time = now

    except KeyboardInterrupt:
        print("\n🛑 Đang tắt listener và dọn dẹp tài nguyên...")
    finally:
        # Đóng các socket và dọn dẹp
        server.close_client()
        server.close_server()
        server.cleanup()
        print("✓ Đã giải phóng socket thành công.")

if __name__ == "__main__":
    main()
