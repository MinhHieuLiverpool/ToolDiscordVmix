# -*- coding: utf-8 -*-
"""
File Converter Extension
========================
Hỗ trợ convert:
  - Video:  MP4 ↔ MOV
  - Audio:  MP4 → MP3, MP4 → WAV
  - Image:  JPG ↔ PNG, → JPEG
  - Doc:    Word → PDF, PDF → Word

Yêu cầu:
  - FFmpeg (phải có trong PATH) cho video/audio
  - pip install -r requirements.txt
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ── Image conversions (Pillow) ──────────────────────────────────────────────

def jpg_to_png(input_path: str, output_path: str = None) -> str:
    """Convert JPG/JPEG → PNG"""
    from PIL import Image
    output_path = output_path or _swap_ext(input_path, ".png")
    img = Image.open(input_path)
    img = img.convert("RGBA")
    img.save(output_path, "PNG")
    print(f"✓ JPG → PNG: {output_path}")
    return output_path


def png_to_jpg(input_path: str, output_path: str = None, quality: int = 95) -> str:
    """Convert PNG → JPG"""
    from PIL import Image
    output_path = output_path or _swap_ext(input_path, ".jpg")
    img = Image.open(input_path)
    img = img.convert("RGB")
    img.save(output_path, "JPEG", quality=quality)
    print(f"✓ PNG → JPG: {output_path}")
    return output_path


def to_jpeg(input_path: str, output_path: str = None, quality: int = 95) -> str:
    """Convert bất kỳ ảnh nào → JPEG"""
    from PIL import Image
    output_path = output_path or _swap_ext(input_path, ".jpeg")
    img = Image.open(input_path)
    img = img.convert("RGB")
    img.save(output_path, "JPEG", quality=quality)
    print(f"✓ {Path(input_path).suffix.upper()} → JPEG: {output_path}")
    return output_path


# ── Video conversions (FFmpeg) ──────────────────────────────────────────────

def mp4_to_mov(input_path: str, output_path: str = None) -> str:
    """Convert MP4 → MOV"""
    _check_ffmpeg()
    output_path = output_path or _swap_ext(input_path, ".mov")
    _run_ffmpeg([
        "-i", input_path,
        "-c:v", "copy",
        "-c:a", "copy",
        output_path
    ])
    print(f"✓ MP4 → MOV: {output_path}")
    return output_path


def mov_to_mp4(input_path: str, output_path: str = None) -> str:
    """Convert MOV → MP4"""
    _check_ffmpeg()
    output_path = output_path or _swap_ext(input_path, ".mp4")
    _run_ffmpeg([
        "-i", input_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "fast",
        "-crf", "23",
        output_path
    ])
    print(f"✓ MOV → MP4: {output_path}")
    return output_path


# ── Audio conversions (FFmpeg) ──────────────────────────────────────────────

def mp4_to_mp3(input_path: str, output_path: str = None, bitrate: str = "192k") -> str:
    """Convert MP4 → MP3 (extract audio)"""
    _check_ffmpeg()
    output_path = output_path or _swap_ext(input_path, ".mp3")
    _run_ffmpeg([
        "-i", input_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-b:a", bitrate,
        output_path
    ])
    print(f"✓ MP4 → MP3: {output_path}")
    return output_path


def mp4_to_wav(input_path: str, output_path: str = None) -> str:
    """Convert MP4 → WAV (extract audio, lossless)"""
    _check_ffmpeg()
    output_path = output_path or _swap_ext(input_path, ".wav")
    _run_ffmpeg([
        "-i", input_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "2",
        output_path
    ])
    print(f"✓ MP4 → WAV: {output_path}")
    return output_path


# ── Document conversions ────────────────────────────────────────────────────

def word_to_pdf(input_path: str, output_path: str = None) -> str:
    """Convert Word (.docx) → PDF
    Trên Windows sử dụng Microsoft Word COM nếu có, fallback sang docx2pdf.
    """
    output_path = output_path or _swap_ext(input_path, ".pdf")
    try:
        from docx2pdf import convert
        convert(input_path, output_path)
    except Exception as e:
        print(f"⚠ docx2pdf failed: {e}")
        # Fallback: thử dùng LibreOffice CLI
        _convert_with_libreoffice(input_path, output_path, "pdf")
    print(f"✓ Word → PDF: {output_path}")
    return output_path


def pdf_to_word(input_path: str, output_path: str = None) -> str:
    """Convert PDF → Word (.docx)"""
    output_path = output_path or _swap_ext(input_path, ".docx")
    from pdf2docx import Converter
    cv = Converter(input_path)
    cv.convert(output_path)
    cv.close()
    print(f"✓ PDF → Word: {output_path}")
    return output_path


# ── Internal helpers ────────────────────────────────────────────────────────

def _swap_ext(filepath: str, new_ext: str) -> str:
    """Đổi extension của file, thêm suffix nếu trùng tên."""
    p = Path(filepath)
    out = p.with_suffix(new_ext)
    if out == p:
        out = p.with_stem(p.stem + "_converted").with_suffix(new_ext)
    return str(out)


def get_ffmpeg_path() -> str:
    """Trả về đường dẫn tới ffmpeg executable hoặc directory chứa ffmpeg."""
    candidates = []
    # 0. PyInstaller temp dir (_MEIPASS)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(getattr(sys, "_MEIPASS"), "bin", "ffmpeg.exe"))
        candidates.append(os.path.join(getattr(sys, "_MEIPASS"), "ffmpeg.exe"))

    # 1. Next to EXE or script
    candidates.append(os.path.join(os.path.dirname(sys.executable), "bin", "ffmpeg.exe"))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe"))
    candidates.append(os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe"))

    for c in candidates:
        if os.path.exists(c):
            return c

    # 2. Check imageio_ffmpeg and copy to project local bin
    try:
        import imageio_ffmpeg
        exe_p = imageio_ffmpeg.get_ffmpeg_exe()
        if exe_p and os.path.exists(exe_p):
            local_bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
            os.makedirs(local_bin_dir, exist_ok=True)
            local_bin = os.path.join(local_bin_dir, "ffmpeg.exe")
            try:
                shutil.copy2(exe_p, local_bin)
                if os.path.exists(local_bin):
                    return local_bin
            except Exception:
                return exe_p
    except Exception:
        pass

    # 3. Check system PATH
    which_p = shutil.which("ffmpeg")
    if which_p:
        return which_p

    # 4. Check standard Windows candidate paths
    for c in [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        r"C:\vMix\ffmpeg.exe",
    ]:
        if os.path.exists(c):
            return c
    return None


def _find_and_setup_ffmpeg():
    """Tự động tìm FFmpeg và Deno trong hệ thống và thêm vào PATH."""
    exe_p = get_ffmpeg_path()
    if exe_p:
        exe_dir = os.path.dirname(exe_p)
        if exe_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = exe_dir + os.pathsep + os.environ.get("PATH", "")

    # Auto setup Deno JS engine in PATH for YouTube challenge solver
    deno_candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        deno_candidates.append(os.path.join(getattr(sys, "_MEIPASS"), "bin", "deno.exe"))
        deno_candidates.append(os.path.join(getattr(sys, "_MEIPASS"), "deno.exe"))
    deno_candidates.extend([
        os.path.join(os.path.dirname(sys.executable), "bin", "deno.exe"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "deno.exe"),
        r"C:\Users\ACER\AppData\Local\Programs\Python\Python313\Scripts\deno.exe",
    ])
    for d_path in deno_candidates:
        if os.path.exists(d_path):
            d_dir = os.path.dirname(d_path)
            if d_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d_dir + os.pathsep + os.environ.get("PATH", "")
            break
    return bool(exe_p)

# Initialize environment search on load
_find_and_setup_ffmpeg()


def _check_ffmpeg():
    """Kiểm tra FFmpeg có sẵn trong PATH không."""
    _find_and_setup_ffmpeg()
    if not get_ffmpeg_path():
        raise RuntimeError(
            "FFmpeg không tìm thấy trong PATH!\n"
            "Tải FFmpeg: https://ffmpeg.org/download.html\n"
            "Sau đó thêm ffmpeg.exe vào PATH."
        )


def _run_ffmpeg(args: list):
    """Chạy FFmpeg với arguments, ghi đè output nếu có."""
    _check_ffmpeg()
    ffmpeg_exe = get_ffmpeg_path() or "ffmpeg"
    cmd = [ffmpeg_exe, "-y"] + args
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\n{result.stderr}")


def _convert_with_libreoffice(input_path: str, output_path: str, fmt: str):
    """Fallback: dùng LibreOffice CLI để convert."""
    lo_path = shutil.which("soffice") or shutil.which("libreoffice")
    if not lo_path:
        raise RuntimeError(
            "Không tìm thấy Microsoft Word hoặc LibreOffice để convert.\n"
            "Cài LibreOffice: https://www.libreoffice.org/download/"
        )
    out_dir = str(Path(output_path).parent)
    subprocess.run([
        lo_path, "--headless", "--convert-to", fmt, "--outdir", out_dir, input_path
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _get_node_path() -> str:
    """Tìm đường dẫn tới Node.js binary."""
    which_node = shutil.which("node")
    if which_node:
        return which_node
    for cand in [
        r"C:\nvm4w\nodejs\node.exe",
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
    ]:
        if os.path.exists(cand):
            return cand
    return "node"


# ── YouTube download (yt-dlp) ──────────────────────────────────────────────

def download_youtube(url: str, output_dir: str = None, format_type: str = "mp4",
                     quality: str = "best",
                     progress_callback=None,
                     cancel_check=None) -> str:
    """
    Download video từ YouTube.
    Tự động hỗ trợ cả khi có và không có FFmpeg trên máy.
    Hỗ trợ hủy tải qua callback cancel_check.

    Args:
        url: YouTube URL
        output_dir: Thư mục lưu (default: thư mục hiện tại)
        format_type: "mp4", "mp3", "wav"
        quality: "best", "2160", "1440", "1080", "720", "480", "360"
        progress_callback: callback(percent, speed, eta) cho GUI
        cancel_check: callable() -> bool để hủy tải

    Returns:
        Đường dẫn file đã tải
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp chưa cài! Chạy: pip install yt-dlp")

    try:
        from yt_dlp.utils import DownloadCancelled
    except ImportError:
        class DownloadCancelled(Exception):
            pass

    _find_and_setup_ffmpeg()
    ffmpeg_exe = get_ffmpeg_path()
    has_ffmpeg = bool(ffmpeg_exe)
    node_exe = _get_node_path()

    if not output_dir:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    downloaded_file = [None]

    def _progress_hook(d):
        if cancel_check and cancel_check():
            raise DownloadCancelled("Đã dừng tải video theo yêu cầu!")

        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            percent = (downloaded / total * 100) if total > 0 else 0
            if progress_callback:
                speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "..."
                eta_str = f"{int(eta)}s" if eta else "..."
                progress_callback(percent, speed_str, eta_str)
        elif d["status"] == "finished":
            downloaded_file[0] = d.get("filename", "")
            if progress_callback:
                progress_callback(100, "Done", "0s")

    def _post_hook(d):
        if cancel_check and cancel_check():
            raise DownloadCancelled("Đã dừng tải video theo yêu cầu!")

    ydl_opts = {
        "outtmpl": output_template,
        "overwrites": True,
        "progress_hooks": [_progress_hook],
        "postprocessor_hooks": [_post_hook],
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["web_embedded", "android", "web"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    if ffmpeg_exe:
        ydl_opts["ffmpeg_location"] = ffmpeg_exe

    if format_type in ("mp3", "wav"):
        if has_ffmpeg:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": format_type,
                "preferredquality": "320" if format_type == "mp3" else None,
            }]
        else:
            ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    else:
        # Video MP4 (Tải chất lượng chuẩn Max / 4K / 2K / 1080p 60fps)
        if has_ffmpeg:
            if quality == "best":
                # Max / Tốt nhất: Ưu tiên 4K/2K -> 1080p -> 720p -> best
                ydl_opts["format"] = "bestvideo[height>=2160]+bestaudio/bestvideo[height>=1440]+bestaudio/bestvideo[height>=1080]+bestaudio/bestvideo+bestaudio/best"
            elif quality == "2160":
                ydl_opts["format"] = "bestvideo[height<=2160][height>1440]+bestaudio/bestvideo[height<=2160]+bestaudio/bestvideo+bestaudio/best"
            elif quality == "1440":
                ydl_opts["format"] = "bestvideo[height<=1440][height>1080]+bestaudio/bestvideo[height<=1440]+bestaudio/bestvideo+bestaudio/best"
            elif quality == "1080":
                ydl_opts["format"] = "bestvideo[height<=1080][height>720]+bestaudio/bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best"
            elif quality == "720":
                ydl_opts["format"] = "bestvideo[height<=720][height>480]+bestaudio/bestvideo[height<=720]+bestaudio/bestvideo+bestaudio/best"
            else:
                ydl_opts["format"] = f"bestvideo[height<={quality}]+bestaudio/bestvideo+bestaudio/best"
            ydl_opts["merge_output_format"] = "mp4"
        else:
            if quality == "best":
                ydl_opts["format"] = "best[height<=1080]/best[ext=mp4]/best"
            elif quality == "1080":
                ydl_opts["format"] = "best[height<=1080]/best"
            elif quality == "720":
                ydl_opts["format"] = "best[height<=720]/best"
            else:
                ydl_opts["format"] = f"best[height<={quality}]/best"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")
    except Exception as e:
        if (cancel_check and cancel_check()) or "dừng" in str(e).lower() or "cancel" in str(e).lower():
            raise
        print(f"[Fallback] Stage 1 error ({e}), switching to resilient fallback...")
        # Stage 2: Resilient fallback (bypasses 403)
        ydl_opts_fallback = {
            "outtmpl": output_template,
            "overwrites": True,
            "progress_hooks": [_progress_hook],
            "postprocessor_hooks": [_post_hook],
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "android", "web"],
                }
            },
        }
        if ffmpeg_exe:
            ydl_opts_fallback["ffmpeg_location"] = ffmpeg_exe

        if format_type in ("mp3", "wav"):
            if has_ffmpeg:
                ydl_opts_fallback["format"] = "bestaudio/best"
                ydl_opts_fallback["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": format_type,
                    "preferredquality": "320" if format_type == "mp3" else None,
                }]
            else:
                ydl_opts_fallback["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        else:
            if has_ffmpeg:
                ydl_opts_fallback["format"] = "22/18/best[ext=mp4]/best"
                ydl_opts_fallback["merge_output_format"] = "mp4"
            else:
                ydl_opts_fallback["format"] = "22/18/best[ext=mp4]/best"

        with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")

    # Find the downloaded file
    if downloaded_file[0] and os.path.exists(downloaded_file[0]):
        result = downloaded_file[0]
    else:
        for ext in (format_type, "mp4", "mp3", "wav", "m4a", "webm"):
            candidate = os.path.join(output_dir, f"{title}.{ext}")
            if os.path.exists(candidate):
                result = candidate
                break
        else:
            result = output_template.replace("%(title)s", title).replace("%(ext)s", format_type)

    print(f"✓ YouTube → {format_type.upper()}: {result}")
    return result


def get_youtube_playlist_info(url: str) -> dict:
    """
    Kiểm tra và lấy danh sách video nếu URL là Playlist hoặc video đơn.
    Dùng extract_flat='in_playlist' để quét playlist nhanh chóng.
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp chưa cài!")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["web_embedded", "android", "web"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("Không thể lấy thông tin từ URL YouTube này!")

        is_playlist = "entries" in info and bool(info.get("entries"))
        if is_playlist:
            entries = []
            for item in info.get("entries", []):
                if not item:
                    continue
                v_id = item.get("id", "")
                v_url = item.get("url") or (f"https://www.youtube.com/watch?v={v_id}" if v_id else "")
                if not v_url and v_id:
                    v_url = f"https://www.youtube.com/watch?v={v_id}"
                entries.append({
                    "id": v_id,
                    "title": item.get("title") or "Video không rõ tiêu đề",
                    "duration": item.get("duration") or 0,
                    "url": v_url,
                    "uploader": item.get("uploader") or item.get("channel") or "",
                })
            return {
                "is_playlist": True,
                "title": info.get("title", "Danh sách phát YouTube"),
                "entries": entries,
            }
        else:
            formats = info.get("formats", [])
            heights = [f.get("height") for f in formats if f.get("height")]
            max_height = max(heights) if heights else None
            return {
                "is_playlist": False,
                "title": info.get("title", ""),
                "duration": info.get("duration", 0),
                "url": url,
                "uploader": info.get("uploader", ""),
                "max_height": max_height,
            }


def get_youtube_info(url: str) -> dict:
    """Lấy thông tin video YouTube (title, thumbnail, duration)."""
    return get_youtube_playlist_info(url)


# ── Image download from URL ────────────────────────────────────────────────

def download_image(url: str, output_path: str = None, output_dir: str = None) -> str:
    """
    Download ảnh từ URL.

    Args:
        url: URL ảnh
        output_path: Đường dẫn file output (optional)
        output_dir: Thư mục lưu (optional, dùng khi không có output_path)

    Returns:
        Đường dẫn file đã tải
    """
    import requests
    from urllib.parse import urlparse, unquote

    response = requests.get(url, stream=True, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    response.raise_for_status()

    # Determine filename
    if output_path:
        filename = output_path
    else:
        # Try to get filename from URL
        parsed = urlparse(url)
        url_filename = unquote(os.path.basename(parsed.path))
        if not url_filename or "." not in url_filename:
            # Try from Content-Disposition header
            cd = response.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                url_filename = cd.split("filename=")[-1].strip('"').strip("'")
            else:
                # Guess extension from Content-Type
                content_type = response.headers.get("Content-Type", "")
                ext_map = {
                    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
                    "image/webp": ".webp", "image/bmp": ".bmp", "image/svg+xml": ".svg",
                }
                ext = ext_map.get(content_type.split(";")[0].strip(), ".jpg")
                url_filename = f"downloaded_image{ext}"

        save_dir = output_dir or os.getcwd()
        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.join(save_dir, url_filename)

    # Avoid overwrite
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filename):
        filename = f"{base}_{counter}{ext}"
        counter += 1

    with open(filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    file_size = os.path.getsize(filename)
    size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / 1024 / 1024:.1f} MB"
    print(f"✓ Image downloaded ({size_str}): {filename}")
    return filename


# ── Conversion registry ────────────────────────────────────────────────────

CONVERTERS = {
    (".mp4", ".mov"): mp4_to_mov,
    (".mov", ".mp4"): mov_to_mp4,
    (".mp4", ".mp3"): mp4_to_mp3,
    (".mp4", ".wav"): mp4_to_wav,
    (".jpg", ".png"): jpg_to_png,
    (".jpeg", ".png"): jpg_to_png,
    (".png", ".jpg"): png_to_jpg,
    (".png", ".jpeg"): to_jpeg,
    (".jpg", ".jpeg"): to_jpeg,
    (".bmp", ".jpeg"): to_jpeg,
    (".webp", ".jpeg"): to_jpeg,
    (".tiff", ".jpeg"): to_jpeg,
    (".docx", ".pdf"): word_to_pdf,
    (".pdf", ".docx"): pdf_to_word,
}


def convert_file(input_path: str, target_format: str, output_path: str = None) -> str:
    """
    Convert file tự động dựa trên extension đầu vào và format đích.
    
    Args:
        input_path: Đường dẫn file nguồn
        target_format: Format đích (vd: "png", "mp4", "pdf", ".mov")
        output_path: Đường dẫn output (optional, tự tạo nếu bỏ trống)
    
    Returns:
        Đường dẫn file đã convert
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File không tồn tại: {input_path}")

    src_ext = Path(input_path).suffix.lower()
    tgt_ext = target_format.lower() if target_format.startswith(".") else f".{target_format.lower()}"

    key = (src_ext, tgt_ext)
    converter = CONVERTERS.get(key)

    if not converter:
        raise ValueError(
            f"Không hỗ trợ convert {src_ext} → {tgt_ext}\n"
            f"Các format hỗ trợ: {list(CONVERTERS.keys())}"
        )

    return converter(input_path, output_path)


def batch_convert(input_dir: str, target_format: str, output_dir: str = None) -> list:
    """
    Convert hàng loạt tất cả file trong thư mục.
    
    Args:
        input_dir: Thư mục chứa file nguồn
        target_format: Format đích
        output_dir: Thư mục output (optional)
    
    Returns:
        Danh sách file đã convert
    """
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Thư mục không tồn tại: {input_dir}")

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    tgt_ext = target_format.lower() if target_format.startswith(".") else f".{target_format.lower()}"

    for file_path in sorted(input_dir.iterdir()):
        if not file_path.is_file():
            continue
        src_ext = file_path.suffix.lower()
        key = (src_ext, tgt_ext)
        if key not in CONVERTERS:
            continue

        out_path = None
        if output_dir:
            out_path = str(output_dir / file_path.with_suffix(tgt_ext).name)

        try:
            result = convert_file(str(file_path), target_format, out_path)
            results.append(result)
        except Exception as e:
            print(f"✗ Lỗi convert {file_path.name}: {e}")

    print(f"\n{'='*50}")
    print(f"Hoàn thành: {len(results)} file đã convert")
    return results


# ── CLI interface ───────────────────────────────────────────────────────────

def _print_help():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              MEDIA STUDIO TOOLKIT & CONVERTER                        ║
╠══════════════════════════════════════════════════════════════════════╣
║  1. File Conversions:                                                ║
║     • Video:    MP4 → MOV  |  MOV → MP4                              ║
║     • Audio:    MP4 → MP3  |  MP4 → WAV                              ║
║     • Image:    JPG → PNG  |  PNG → JPG  |  * → JPEG                 ║
║     • Document: Word → PDF |  PDF → Word                             ║
║                                                                      ║
║  2. Media Downloader:                                                ║
║     • YouTube Video / Audio (MP4 / MP3 / WAV)                        ║
║     • Image Downloader from Direct URL                               ║
╠══════════════════════════════════════════════════════════════════════╣
║  Usage:                                                              ║
║    python converter.py <file> <format> [output]                      ║
║    python converter.py --batch <dir> <format> [out_dir]              ║
║    python converter.py --yt <url> [format: mp4/mp3/wav] [out_dir]    ║
║    python converter.py --img <url> [out_dir_or_file]                 ║
║    python converter_gui.py   (Giao diện GUI hiện đại)                ║
║                                                                      ║
║  Examples:                                                           ║
║    python converter.py video.mp4 mov                                 ║
║    python converter.py photo.jpg png                                 ║
║    python converter.py doc.docx pdf                                  ║
║    python converter.py --yt "https://youtu.be/..." mp3 ./downloads   ║
║    python converter.py --img "https://example.com/pic.jpg" ./images  ║
╚══════════════════════════════════════════════════════════════════════╝
""")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        _print_help()
        return

    # YouTube downloader CLI
    if args[0] in ("--yt", "--youtube"):
        if len(args) < 2:
            print("Usage: python converter.py --yt <url> [format: mp4/mp3/wav] [out_dir]")
            return
        url = args[1]
        fmt = args[2] if len(args) > 2 else "mp4"
        out_dir = args[3] if len(args) > 3 else None
        try:
            res = download_youtube(url, output_dir=out_dir, format_type=fmt)
            print(f"\n✅ Đã tải YouTube thành công: {res}")
        except Exception as e:
            print(f"\n❌ Lỗi tải YouTube: {e}")
            sys.exit(1)
        return

    # Image downloader CLI
    if args[0] in ("--img", "--image"):
        if len(args) < 2:
            print("Usage: python converter.py --img <url> [out_dir_or_file]")
            return
        url = args[1]
        out_dest = args[2] if len(args) > 2 else None
        out_dir = out_dest if out_dest and os.path.isdir(out_dest) else None
        out_file = out_dest if out_dest and not os.path.isdir(out_dest) else None
        try:
            res = download_image(url, output_path=out_file, output_dir=out_dir)
            print(f"\n✅ Đã tải ảnh thành công: {res}")
        except Exception as e:
            print(f"\n❌ Lỗi tải ảnh: {e}")
            sys.exit(1)
        return

    # Batch conversion CLI
    if args[0] == "--batch":
        if len(args) < 3:
            print("Usage: python converter.py --batch <dir> <format> [output_dir]")
            return
        input_dir = args[1]
        target_fmt = args[2]
        output_dir = args[3] if len(args) > 3 else None
        batch_convert(input_dir, target_fmt, output_dir)
        return

    if len(args) < 2:
        print("Usage: python converter.py <file> <format> [output]")
        return

    input_file = args[0]
    target_fmt = args[1]
    output_file = args[2] if len(args) > 2 else None

    try:
        result = convert_file(input_file, target_fmt, output_file)
        print(f"\n✅ Convert thành công: {result}")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        sys.exit(1)



if __name__ == "__main__":
    main()
