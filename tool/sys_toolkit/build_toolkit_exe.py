"""
Script đóng gói Windows Admin & System Tweaker Pro thành file EXE độc lập (Single EXE).
"""
import os
import sys
import shutil
import subprocess
import time


def build_exe():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")
    entry_script = os.path.join(base_dir, "win_toolkit_gui.py")
    exe_name = "WinAdminToolkit.exe"

    print("=" * 60)
    print("🚀 BẮT ĐẦU ĐÓNG GÓI EXE: Windows Admin & System Tweaker Pro")
    print("=" * 60)

    # 1. Kill any existing instance of the exe
    try:
        subprocess.run(["taskkill", "/F", "/IM", exe_name], capture_output=True)
        time.sleep(0.5)
    except Exception:
        pass

    # 2. Check PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("📦 Đang cài đặt PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 3. Prepare PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--uac-admin",  # Auto-request Administrator rights on launch!
        f"--name={os.path.splitext(exe_name)[0]}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={base_dir}",
        f"--add-data={os.path.join(base_dir, 'toolkit_actions.py')};.",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        entry_script
    ]

    print("\n🔨 Đang tiến hành biên dịch với PyInstaller (kèm cờ --uac-admin)...")
    start_time = time.time()
    result = subprocess.run(cmd)

    if result.returncode == 0:
        elapsed = time.time() - start_time
        final_exe = os.path.join(dist_dir, exe_name)
        file_size_mb = os.path.getsize(final_exe) / (1024 * 1024) if os.path.exists(final_exe) else 0

        # Also copy to root dist folder if it exists
        root_dist = os.path.join(os.path.dirname(base_dir), "dist")
        if os.path.exists(root_dist):
            root_target = os.path.join(root_dist, exe_name)
            try:
                shutil.copy2(final_exe, root_target)
                print(f"✓ Đã copy thêm vào thư mục dist gốc: {root_target}")
            except Exception:
                pass

        print("=" * 60)
        print("🎉 ĐÓNG GÓI EXE THÀNH CÔNG!")
        print(f"📁 Đường dẫn file EXE: {final_exe}")
        print(f"📦 Dung lượng file: {file_size_mb:.1f} MB")
        print(f"⏱️ Thời gian đóng gói: {elapsed:.1f} giây")
        print("=" * 60)
    else:
        print(f"❌ Đóng gói thất bại với mã lỗi: {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build_exe()
