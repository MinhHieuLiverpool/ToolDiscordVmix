"""
Script đóng gói ứng dụng Studio Media Toolkit & Converter thành file EXE độc lập.
Tự động bundle: FFmpeg, Deno JS Engine, yt-dlp, docx2pdf, pdf2docx, PIL, OpenCV...
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
    bin_dir = os.path.join(base_dir, "bin")
    entry_script = os.path.join(base_dir, "converter_gui.py")
    exe_name = "StudioMediaToolkit.exe"

    print("=" * 60)
    print("🚀 BẮT ĐẦU ĐÓNG GÓI EXE: Studio Media Toolkit & Converter")
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

    # 3. Check and ensure ffmpeg.exe & deno.exe exist in bin/
    os.makedirs(bin_dir, exist_ok=True)
    ffmpeg_target = os.path.join(bin_dir, "ffmpeg.exe")
    if not os.path.exists(ffmpeg_target):
        try:
            import imageio_ffmpeg
            src_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            if src_ffmpeg and os.path.exists(src_ffmpeg):
                shutil.copy2(src_ffmpeg, ffmpeg_target)
                print(f"✓ Đã copy FFmpeg vào: {ffmpeg_target}")
        except Exception as e:
            print(f"⚠️ Không thể copy ffmpeg từ imageio: {e}")

    deno_target = os.path.join(bin_dir, "deno.exe")
    if not os.path.exists(deno_target):
        src_deno = r"C:\Users\ACER\AppData\Local\Programs\Python\Python313\Scripts\deno.exe"
        if os.path.exists(src_deno):
            shutil.copy2(src_deno, deno_target)
            print(f"✓ Đã copy Deno vào: {deno_target}")

    # 4. Prepare PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        f"--name={os.path.splitext(exe_name)[0]}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={base_dir}",
    ]

    # Add bin data
    if os.path.exists(ffmpeg_target):
        cmd.append(f"--add-data={ffmpeg_target};bin")
    if os.path.exists(deno_target):
        cmd.append(f"--add-data={deno_target};bin")

    # Add modules and hidden imports
    modules_to_collect = [
        "yt_dlp",
        "yt_dlp_ejs",
        "curl_cffi",
        "docx",
        "docx2pdf",
        "pdf2docx",
        "PIL",
        "cv2",
    ]
    for mod in modules_to_collect:
        cmd.append(f"--collect-all={mod}")

    hidden_imports = [
        "PIL.ImageTk",
        "requests",
        "imageio_ffmpeg",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ]
    for h in hidden_imports:
        cmd.append(f"--hidden-import={h}")

    cmd.append(entry_script)

    print("\n🔨 Đang tiến hành biên dịch với PyInstaller...")
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
