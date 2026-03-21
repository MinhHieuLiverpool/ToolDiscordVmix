"""
Script tự động build file EXE cho ứng dụng Vmix Monitor.
Hỗ trợ build từ 1 file .py hoặc từ cả folder package.
"""
import os
import subprocess
import sys
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None


def kill_running_exe(exe_name: str):
    """Kill tiến trình EXE đang chạy trước khi build (tránh PermissionError)"""
    if psutil is None:
        return

    killed = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == exe_name.lower():
                proc.kill()
                killed.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if killed:
        print(f"⚠️  Đã dừng tiến trình {exe_name} (PID: {', '.join(map(str, killed))}) trước khi build.")

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


def resolve_entry_script(entry: str) -> str:
    """Resolve entry point. Nếu entry là folder thì tìm main.py hoặc __main__.py."""
    p = Path(entry)
    if p.is_file():
        return str(p)

    if p.is_dir():
        main_py = p / "main.py"
        dunder_main = p / "__main__.py"
        if main_py.exists():
            return str(main_py)
        if dunder_main.exists():
            return str(dunder_main)
        raise FileNotFoundError(
            f"Không tìm thấy main.py hoặc __main__.py trong folder: {entry}"
        )

    raise FileNotFoundError(f"Không tìm thấy entry: {entry}")


def build_executable(
    *,
    exe_name: str,
    entry: str,
    windowed: bool = False,
    icon: str | None = None,
    add_data: list[str] | None = None,
    hidden_imports: list[str] | None = None,
    collect_submodules: list[str] | None = None,
):
    """Build exe với PyInstaller từ file hoặc folder."""
    entry_script = resolve_entry_script(entry)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        f"--name={exe_name}",
    ]

    if windowed:
        cmd.append("--windowed")
    if icon:
        cmd.append(f"--icon={icon}")

    for item in add_data or []:
        cmd.append(f"--add-data={item}")
    for item in hidden_imports or []:
        cmd.append(f"--hidden-import={item}")
    for item in collect_submodules or []:
        cmd.append(f"--collect-submodules={item}")

    cmd.append(entry_script)

    kill_running_exe(f"{exe_name}.exe")
    subprocess.run(cmd, check=True)
    print(f"\n✅ {exe_name}.exe đã được tạo thành công trong thư mục 'dist'!")

def build_vmix_monitor_exe():
    """Build file EXE cho Vmix Monitor GUI"""
    print("\n" + "="*50)
    print("Building Vmix Monitor Tool...")
    print("="*50 + "\n")
    
    build_executable(
        exe_name="VmixMonitor",
        entry="vmix_monitor_gui.py",
        windowed=True,
        icon="assets/Discord-Logo.ico",
        add_data=[
            "assets/Discord-Logo.ico;assets",
            "assets/Discord-Logo.png;assets",
            "config.py;.",
        ],
        hidden_imports=[
            "PIL._tkinter_finder",
            "pystray",
            "PIL.Image",
            "PIL.ImageDraw",
            "pytz",
        ],
        collect_submodules=["vmix_monitor_gui"],
    )

def build_server_gui_exe():
    """Build file EXE cho Server GUI Advanced (hỗ trợ package folder)."""
    print("\n" + "="*50)
    print("Building Server Log Viewer...")
    print("="*50 + "\n")
    
    build_executable(
        exe_name="ServerLogViewer",
        # Dùng launcher ổn định ở root, đồng thời gom toàn bộ module trong folder package
        entry="server_gui_advanced.py",
        windowed=True,
        icon="assets/Discord-Logo.ico",
        add_data=[
            "config.py;.",
            "assets/Discord-Logo.ico;assets",
        ],
        hidden_imports=[
            "tkinter",
            "customtkinter",
            "requests",
            "pytz",
            "websocket",
            "websocket._app",
        ],
        collect_submodules=["server_gui_advanced"],
    )

def build_server_exe():
    """Build file EXE cho Server (console)"""
    print("\n" + "="*50)
    print("Building Server Console...")
    print("="*50 + "\n")
    
    build_executable(
        exe_name="ServerConsole",
        entry="server.py",
        icon="assets/Discord-Logo.ico",
        add_data=["config.py;."],
        hidden_imports=["pymongo", "requests", "pytz"],
    )

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
