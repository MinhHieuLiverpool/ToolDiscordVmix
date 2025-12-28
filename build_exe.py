"""
Script tự động build file EXE cho ứng dụng Vmix Monitor
Sử dụng PyInstaller để đóng gói Python + tất cả dependencies
"""
import subprocess
import sys
import os

def install_pyinstaller():
    """Cài đặt PyInstaller nếu chưa có"""
    print("Đang kiểm tra PyInstaller...")
    try:
        import PyInstaller
        print("PyInstaller đã được cài đặt.")
    except ImportError:
        print("Đang cài đặt PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller đã được cài đặt thành công!")

def build_vmix_monitor_exe():
    """Build file EXE cho Vmix Monitor GUI"""
    print("\n" + "="*50)
    print("Building Vmix Monitor Tool...")
    print("="*50 + "\n")
    
    cmd = [
        "pyinstaller",
        "--onefile",  # Gom thành 1 file EXE duy nhất
        "--windowed",  # Không hiện console window
        "--name=VmixMonitor",
        "--icon=assets/Discord-Logo.ico",
        "--add-data=assets/Discord-Logo.ico;assets",
        "--add-data=assets/Discord-Logo.png;assets",
        "--add-data=config.py;.",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=pystray",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageDraw",
        "vmix_monitor_gui.py"
    ]
    
    subprocess.run(cmd, check=True)
    print("\n✅ VmixMonitor.exe đã được tạo thành công trong thư mục 'dist'!")

def build_server_gui_exe():
    """Build file EXE cho Server GUI Advanced"""
    print("\n" + "="*50)
    print("Building Server Log Viewer...")
    print("="*50 + "\n")
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=ServerLogViewer",
        "--icon=assets/Discord-Logo.ico",
        "--add-data=config.py;.",
        "--hidden-import=tkinter",
        "--hidden-import=requests",
        "server_gui_advanced.py"
    ]
    
    subprocess.run(cmd, check=True)
    print("\n✅ ServerLogViewer.exe đã được tạo thành công trong thư mục 'dist'!")

def build_server_exe():
    """Build file EXE cho Server (console)"""
    print("\n" + "="*50)
    print("Building Server Console...")
    print("="*50 + "\n")
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name=ServerConsole",
        "--icon=assets/Discord-Logo.ico",
        "--add-data=config.py;.",
        "--hidden-import=pymongo",
        "--hidden-import=requests",
        "server.py"
    ]
    
    subprocess.run(cmd, check=True)
    print("\n✅ ServerConsole.exe đã được tạo thành công trong thư mục 'dist'!")

def main():
    """Main function"""
    print("="*60)
    print("    BUILD EXE CHO DỰ ÁN VMIX MONITOR    ")
    print("="*60)
    
    # Kiểm tra và cài đặt PyInstaller
    install_pyinstaller()
    
    # Hiển thị menu
    print("\nChọn ứng dụng cần build:")
    print("1. VmixMonitor (GUI chính)")
    print("2. ServerLogViewer (GUI xem log)")
    print("3. ServerConsole (Console server)")
    print("4. Build tất cả")
    print("0. Thoát")
    
    choice = input("\nNhập lựa chọn (0-4): ").strip()
    
    try:
        if choice == "1":
            build_vmix_monitor_exe()
        elif choice == "2":
            build_server_gui_exe()
        elif choice == "3":
            build_server_exe()
        elif choice == "4":
            build_vmix_monitor_exe()
            build_server_gui_exe()
            build_server_exe()
        elif choice == "0":
            print("Thoát chương trình.")
            return
        else:
            print("Lựa chọn không hợp lệ!")
            return
        
        print("\n" + "="*60)
        print("    BUILD HOÀN TẤT!    ")
        print("="*60)
        print(f"\nCác file EXE được tạo trong thư mục: {os.path.abspath('dist')}")
        print("\nNgười dùng có thể chạy file EXE mà KHÔNG CẦN cài đặt Python!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Lỗi khi build: {e}")
        print("Vui lòng kiểm tra lại cấu hình và thử lại.")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")

if __name__ == "__main__":
    main()
