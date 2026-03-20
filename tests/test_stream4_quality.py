"""
test_stream4_quality.py
──────────────────────────────────────────────────────────────────────────────
Standalone tester cho chất lượng Stream 4 của vMix.

Ý tưởng:
- Lấy thông tin cấu hình Stream 4 (SRT hoặc RTMP) từ preset / current.config
- In ra các thông số chính để kiểm tra nhanh:
  • Enabled / Disabled
  • Server / Host / Port / Path
  • Video bitrate, Audio bitrate
  • Codec, Latency, Passphrase (nếu là SRT)

Chạy:
  python test_stream4_quality.py

Lưu ý:
- Script NÀY CHỈ ĐỌC FILE cấu hình của vMix, KHÔNG xem được realtime bitrate
  giống như Task Manager. Dùng để confirm cấu hình stream4 đã đúng.
"""

from __future__ import annotations

import glob
import html
import os
import re
import sys
from datetime import datetime
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional, Tuple

# ─── Màu ANSI ────────────────────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty() or os.environ.get("TERM") not in (None, "")
_R = "\033[91m" if _USE_COLOR else ""
_G = "\033[92m" if _USE_COLOR else ""
_Y = "\033[93m" if _USE_COLOR else ""
_C = "\033[96m" if _USE_COLOR else ""
_B = "\033[1m" if _USE_COLOR else ""
_X = "\033[0m" if _USE_COLOR else ""


def _sep(title: str) -> None:
    bar = f"{_C}{'─' * 70}{_X}"
    print(f"\n{bar}")
    print(f"{_B}{_C}  {title}{_X}")
    print(bar)


def _ok(label: str, value: str) -> None:
    print(f"  {_G}✔{_X}  {_B}{label:<26}{_X}  {value}")


def _warn(label: str, value: str) -> None:
    print(f"  {_Y}⚠{_X}  {_B}{label:<26}{_X}  {value}")


def _err(label: str, value: str) -> None:
    print(f"  {_R}✘{_X}  {_B}{label:<26}{_X}  {value}")


# ─── Helpers đọc file vMix (shared read) ────────────────────────────────────


def _vmix_data_dir() -> str:
    base = (
        os.environ.get("PROGRAMDATA")
        or os.environ.get("ALLUSERSPROFILE")
        or r"C:\\ProgramData"
    )
    return os.path.join(base, "vMix")


def _read_file_shared(path: str) -> str:
    """Đọc file ngay cả khi vMix đang mở (Windows)."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    GENERIC_READ = 0x80000000
    FILE_SHARE_ALL = 0x07
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE = ctypes.c_void_p(-1).value

    handle = kernel32.CreateFileW(
        path,
        GENERIC_READ,
        FILE_SHARE_ALL,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == INVALID_HANDLE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = kernel32.GetFileSize(handle, None)
        if size == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        buf = ctypes.create_string_buffer(size)
        read = wintypes.DWORD(0)
        if not kernel32.ReadFile(handle, buf, size, ctypes.byref(read), None):
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.raw[: read.value].decode("utf-8", errors="replace")
    finally:
        kernel32.CloseHandle(handle)


def _debug_scan_vmix_for_streaming(vmix_dir: str) -> None:
    """Quét toàn bộ thư mục vMix để xem file nào có chứa chữ 'Streaming'.

    Chỉ để debug khi không tìm được block Streaming* trong các file config chính.
    """

    _sep("DEBUG – Scan thư mục vMix tìm Streaming*")
    patterns = ("*.config", "*.xml", "*.vmix", "*.settings")
    candidates = []
    for root_dir, _dirs, _files in os.walk(vmix_dir):
        for pat in patterns:
            candidates.extend(glob.glob(os.path.join(root_dir, pat)))

    seen = set()
    found_any = False
    for path in sorted(candidates):
        if path in seen:
            continue
        seen.add(path)
        try:
            txt = _read_file_shared(path)
        except Exception:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    txt = f.read()
            except Exception:
                continue
        if "Streaming" in txt:
            found_any = True
            _ok("Found", path)

    if not found_any:
        _warn("Scan", "Không tìm thấy chữ 'Streaming' trong bất kỳ file *.config/xml/vmix/settings nào")


# ─── Data model ──────────────────────────────────────────────────────────────


@dataclass
class StreamInfo:
    enabled: bool
    kind: str  # "SRT" hoặc "RTMP" hoặc "Unknown"
    host: str
    port: str
    path: str
    video_bitrate: str
    audio_bitrate: str
    codec: str
    quality_label: str
    latency: str
    passphrase: str


@dataclass
class LatestStreamingLog:
    file_path: str
    file_name: str
    last_write: datetime
    quality_line: str
    raw_content: str


@dataclass
class StreamingQualitySnapshot:
    video_bitrate: str
    encode_size: str
    audio_bitrate: str
    source: str
    profile: str
    level: str
    preset: str
    aspect_ratio_crop: str
    audio_format: str
    channels: str
    keyframe_frequency: str
    stream_delay: str
    threads: str
    network_buffer: str
    strict_cbr: str
    nal_cbr: str
    keyframe_aligned: str


@dataclass
class StreamHealth:
    status: str
    reason: str
    actual_bitrate_kbps: float
    target_bitrate_kbps: float
    bitrate_ratio: float
    speed: float
    dropped_warnings: int


# ─── Helpers tìm & parse block Streaming* ────────────────────────────────────


def _find_streaming_block(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """Tìm block Streaming*/value trong một file cấu hình, trả về XML bên trong.

    Ưu tiên theo thứ tự: Streaming4 → Streaming3 → Streaming2 → Streaming.
    """

    for name in ("Streaming4", "Streaming3", "Streaming2", "Streaming"):
        m = re.search(
            rf'name="{name}"[^>]*>\s*<value>(.*?)</value>',
            raw,
            re.DOTALL,
        )
        if m:
            return m.group(1), name
    return None, None


def _build_stream_info(root: ET.Element) -> StreamInfo:
    def _t(tag: str, default: str = "") -> str:
        return (root.findtext(tag) or default).strip()

    enabled = _t("Enabled", "0") == "1"

    # SRT vs RTMP: heuristic dựa trên field có mặt
    if root.find("SRTEnabled") is not None or root.find("SRTHost") is not None:
        kind = "SRT"
        host = _t("SRTHost")
        port = _t("SRTPort")
        path = "(n/a)"
        video_bitrate = _t("SRTVideoBandwidth")
        audio_bitrate = _t("SRTAudioBandwidth")
        codec = _t("SRTVideoCodec")
        latency = _t("SRTLatencyMS") or _t("SRTLatency")
        passphrase = _t("SRTPassPhrase") or _t("SRTPassphrase")
        quality_label = _t("Quality") or _t("PresetName")
    else:
        kind = "RTMP/HTTP"
        host = _t("Url") or _t("Server")
        port = _t("Port")
        path = _t("StreamName") or _t("Key")
        video_bitrate = _t("VideoBitrate")
        audio_bitrate = _t("AudioBitrate")
        codec = _t("VideoCodec")
        latency = "(n/a)"
        passphrase = ""
        # Một số version vMix lưu chất lượng preset trong field Quality / ProfileName
        quality_label = _t("Quality") or _t("ProfileName") or _t("PresetName")

    return StreamInfo(
        enabled=enabled,
        kind=kind,
        host=host,
        port=port,
        path=path,
        video_bitrate=video_bitrate,
        audio_bitrate=audio_bitrate,
        codec=codec,
        quality_label=quality_label,
        latency=latency,
        passphrase=passphrase,
    )


# ─── Parse Streaming* từ current.config hoặc file *.config khác ─────────────


def _parse_stream4_from_config() -> Tuple[Optional[StreamInfo], str]:
    vmix_dir = _vmix_data_dir()
    cfg = os.path.join(vmix_dir, "settingbackups", "current.config")
    if not os.path.isfile(cfg):
        return None, f"Không tìm thấy file: {cfg}"

    # 1) Thử current.config trước
    try:
        raw = _read_file_shared(cfg)
    except Exception as ex:
        return None, f"Lỗi đọc current.config: {ex}"

    streaming_xml, streaming_name = _find_streaming_block(raw)
    src_path = cfg

    # 2) Nếu không có trong current.config → quét các file *.config khác trong settingbackups
    if not streaming_xml:
        settings_dir = os.path.join(vmix_dir, "settingbackups")
        pattern = os.path.join(settings_dir, "*.config")
        for other in sorted(glob.glob(pattern)):
            if os.path.abspath(other) == os.path.abspath(cfg):
                continue
            try:
                raw_other = _read_file_shared(other)
            except Exception:
                continue
            streaming_xml, streaming_name = _find_streaming_block(raw_other)
            if streaming_xml:
                src_path = other
                break

    if not streaming_xml:
        # Không tìm thấy trong current.config & settingbackups/*.config → quét toàn thư mục vMix để user xem file nào có Streaming
        _debug_scan_vmix_for_streaming(vmix_dir)
        return None, "Không tìm thấy block Streaming/2/3/4 trong current.config hoặc các file *.config khác"

    try:
        inner = html.unescape(streaming_xml.strip())
        root = ET.fromstring(f"<root>{inner}</root>")
    except ET.ParseError as ex:
        return None, f"Lỗi parse Streaming* XML: {ex}"

    info = _build_stream_info(root)
    src_label = f"{src_path} ({streaming_name})" if streaming_name else src_path
    return info, src_label


# ─── Hiển thị kết quả ───────────────────────────────────────────────────────


def print_stream4(info: Optional[StreamInfo], source: str, error: Optional[str]) -> None:
    _sep("STREAM 4 QUALITY – current.config")
    _ok("Nguồn", source)

    if error:
        _err("Trạng thái", error)
        return

    if info is None:
        _err("Trạng thái", "Không có dữ liệu Stream4")
        return

    _ok("Enabled", "YES" if info.enabled else "NO")
    _ok("Loại", info.kind)
    _ok("Host / Server", info.host or "(trống)")
    _ok("Port", info.port or "(trống)")
    _ok("Path / Stream name", info.path or "(trống)")

    _sep("Bitrate & Codec")
    if info.quality_label:
        _ok("Quality preset", info.quality_label)
    _ok("Video bitrate", info.video_bitrate or "(trống)")
    _ok("Audio bitrate", info.audio_bitrate or "(trống)")
    _ok("Codec", info.codec or "(trống)")

    if info.kind == "SRT":
        _sep("SRT Extra")
        _ok("Latency", info.latency or "(trống)")
        _ok("Passphrase", "(đã đặt)" if info.passphrase else "(không)")


def _find_latest_streaming_log_today() -> Tuple[Optional[LatestStreamingLog], Optional[str]]:
    streaming_dir = os.path.join(_vmix_data_dir(), "streaming")
    if not os.path.isdir(streaming_dir):
        return None, f"Không tìm thấy thư mục: {streaming_dir}"

    now = datetime.now()
    today = now.date()
    today_logs = []

    for name in os.listdir(streaming_dir):
        path = os.path.join(streaming_dir, name)
        if not os.path.isfile(path) or not name.lower().endswith(".log"):
            continue

        last_write = datetime.fromtimestamp(os.path.getmtime(path))
        if last_write.date() == today:
            today_logs.append((path, last_write))

    if not today_logs:
        return None, f"Không có file streaming .log trong ngày {today.isoformat()}"

    latest_path, latest_write = max(today_logs, key=lambda x: x[1])

    try:
        content = _read_file_shared(latest_path)
    except Exception:
        with open(latest_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    quality_matches = re.findall(
        r"frame=.*?fps=.*?q=.*?(?:L?size=.*?)?bitrate=.*?kbits/s.*",
        content,
    )
    quality_line = quality_matches[-1].strip() if quality_matches else ""

    return (
        LatestStreamingLog(
            file_path=latest_path,
            file_name=os.path.basename(latest_path),
            last_write=latest_write,
            quality_line=quality_line,
            raw_content=content,
        ),
        None,
    )


def _extract_command_line(raw_content: str) -> str:
    m = re.search(r"Command line:\s*(.*?)ffmpeg version", raw_content, re.DOTALL)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()


def _first_group(pattern: str, text: str) -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


def _build_ui_snapshot(raw_content: str) -> StreamingQualitySnapshot:
    cmd = _extract_command_line(raw_content)

    video_bitrate = _first_group(r"-b:v\s+(\S+)", cmd) or "(khong xac dinh)"
    width = _first_group(r"-s:v\s+(\d+)x\d+", cmd)
    height = _first_group(r"-s:v\s+\d+x(\d+)", cmd)
    encode_size = f"{width} x {height}" if width and height else "(khong xac dinh)"
    audio_bitrate = _first_group(r"-b:a\s+(\S+)", cmd) or "(khong xac dinh)"

    profile = _first_group(r"-profile:v\s+(\S+)", cmd) or "(khong xac dinh)"
    level = _first_group(r"-level:v\s+(\S+)", cmd) or "(khong xac dinh)"
    preset = _first_group(r"-preset:v\s+(\S+)", cmd) or "(khong xac dinh)"
    threads = _first_group(r"-threads\s+(\S+)", cmd) or "(khong xac dinh)"

    audio_codec = _first_group(r"-codec:a\s+(\S+)", cmd)
    audio_format = audio_codec.upper() if audio_codec else "(khong xac dinh)"

    # vMix log khong luu truc tiep cac field nay theo ten UI.
    source = "(khong xac dinh tu ffmpeg log)"
    aspect_ratio_crop = "(khong xac dinh tu ffmpeg log)"
    stream_delay = "(khong xac dinh tu ffmpeg log)"
    network_buffer = "(khong xac dinh tu ffmpeg log)"
    keyframe_aligned = "(khong xac dinh tu ffmpeg log)"

    channels = "stereo" if re.search(r"\bstereo\b", raw_content, re.IGNORECASE) else "(khong xac dinh)"

    gop = _first_group(r"-g:v\s+(\d+)", cmd)
    fps_raw = _first_group(r"(\d+(?:\.\d+)?)\s*fps", raw_content)
    if gop and fps_raw:
        try:
            key_sec = float(gop) / float(fps_raw)
            keyframe_frequency = f"{gop} frames (~{key_sec:.2f}s @ {fps_raw}fps)"
        except Exception:
            keyframe_frequency = f"{gop} frames"
    elif gop:
        keyframe_frequency = f"{gop} frames"
    else:
        keyframe_frequency = "(khong xac dinh)"

    has_nal = bool(re.search(r"nal[_-]hrd", cmd, re.IGNORECASE))
    has_strict = bool(re.search(r"strict[-_]cbr|nal[_-]hrd=cbr", cmd, re.IGNORECASE))
    strict_cbr = "ON" if has_strict else "OFF/Unknown"
    nal_cbr = "ON" if has_nal else "OFF/Unknown"

    return StreamingQualitySnapshot(
        video_bitrate=video_bitrate,
        encode_size=encode_size,
        audio_bitrate=audio_bitrate,
        source=source,
        profile=profile,
        level=level,
        preset=preset,
        aspect_ratio_crop=aspect_ratio_crop,
        audio_format=audio_format,
        channels=channels,
        keyframe_frequency=keyframe_frequency,
        stream_delay=stream_delay,
        threads=threads,
        network_buffer=network_buffer,
        strict_cbr=strict_cbr,
        nal_cbr=nal_cbr,
        keyframe_aligned=keyframe_aligned,
    )


def _parse_k_to_kbps(raw: str) -> float:
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*k", raw.lower())
    return float(m.group(1)) if m else 0.0


def _parse_quality_metric(line: str, field: str) -> float:
    if not line:
        return 0.0
    if field == "bitrate":
        m = re.search(r"bitrate=\s*([0-9]+(?:\.[0-9]+)?)kbits/s", line)
    elif field == "speed":
        m = re.search(r"speed=\s*([0-9]+(?:\.[0-9]+)?)x", line)
    else:
        m = None
    return float(m.group(1)) if m else 0.0


def _assess_stream_health(latest: LatestStreamingLog, ui: StreamingQualitySnapshot) -> StreamHealth:
    actual_bitrate = _parse_quality_metric(latest.quality_line, "bitrate")
    target_bitrate = _parse_k_to_kbps(ui.video_bitrate)
    speed = _parse_quality_metric(latest.quality_line, "speed")
    dropped_warnings = len(re.findall(r"frame dropped", latest.raw_content, re.IGNORECASE))

    ratio = (actual_bitrate / target_bitrate) if target_bitrate > 0 else 0.0

    # Quy tắc thực dụng:
    # - DO: ratio < 0.5 hoặc có frame dropped nhiều.
    # - VANG: ratio thấp vừa, speed không đạt realtime, hoặc stream quá ngắn.
    # - XANH: bitrate bám cấu hình và không có cảnh báo drop.
    duration_sec = 0.0
    m_time = re.search(r"time=([0-9]{2}):([0-9]{2}):([0-9]{2}(?:\.[0-9]+)?)", latest.quality_line)
    if m_time:
        duration_sec = int(m_time.group(1)) * 3600 + int(m_time.group(2)) * 60 + float(m_time.group(3))

    if dropped_warnings >= 20 or (target_bitrate > 0 and ratio < 0.5):
        status = "DO"
    elif (
        dropped_warnings > 0
        or (target_bitrate > 0 and ratio < 0.85)
        or (speed > 0 and speed < 0.95)
        or (duration_sec > 0 and duration_sec < 20)
    ):
        status = "VANG"
    else:
        status = "XANH"

    reason = (
        f"ratio={ratio:.2f}, speed={speed:.2f}x, dropped={dropped_warnings}, duration={duration_sec:.1f}s"
    )

    return StreamHealth(
        status=status,
        reason=reason,
        actual_bitrate_kbps=actual_bitrate,
        target_bitrate_kbps=target_bitrate,
        bitrate_ratio=ratio,
        speed=speed,
        dropped_warnings=dropped_warnings,
    )


def print_latest_streaming_log_today(
    latest: Optional[LatestStreamingLog],
    error: Optional[str],
) -> None:
    _sep("STREAMING LOG HOM NAY - FILE MOI NHAT")
    if error:
        _err("Trang thai", error)
        return

    if latest is None:
        _err("Trang thai", "Khong co du lieu")
        return

    _ok("File moi nhat", latest.file_name)
    _ok("LastWrite", latest.last_write.strftime("%Y-%m-%d %H:%M:%S"))
    _ok("Duong dan", latest.file_path)
    if latest.quality_line:
        _ok("Quality line", latest.quality_line)
    else:
        _warn("Quality line", "Khong tim thay dong quality trong log")

    ui = _build_ui_snapshot(latest.raw_content)
    _sep("DOI CHIEU STREAMING QUALITY (TU LOG)")
    _ok("Video Bit Rates", ui.video_bitrate)
    _ok("Encode Size", ui.encode_size)
    _ok("Audio Bit Rate", ui.audio_bitrate)
    _ok("Source", ui.source)
    _ok("Profile", ui.profile)
    _ok("Level", ui.level)
    _ok("Preset", ui.preset)
    _ok("Aspect Ratio / Crop", ui.aspect_ratio_crop)
    _ok("Audio Format", ui.audio_format)
    _ok("Channels", ui.channels)
    _ok("Keyframe Frequency", ui.keyframe_frequency)
    _ok("Stream Delay", ui.stream_delay)
    _ok("Threads", ui.threads)
    _ok("Network Buffer", ui.network_buffer)
    _ok("Strict CBR", ui.strict_cbr)
    _ok("NAL CBR", ui.nal_cbr)
    _ok("Keyframe Aligned", ui.keyframe_aligned)

    health = _assess_stream_health(latest, ui)
    _sep("DANH GIA MAU STREAM")
    if health.status == "DO":
        _err("Trang thai", "DO")
    elif health.status == "VANG":
        _warn("Trang thai", "VANG")
    else:
        _ok("Trang thai", "XANH")

    _ok("Bitrate thuc te (kbps)", f"{health.actual_bitrate_kbps:.1f}")
    _ok("Bitrate muc tieu (kbps)", f"{health.target_bitrate_kbps:.1f}")
    _ok("Ti le bitrate", f"{health.bitrate_ratio:.2f}")
    _ok("Toc do encode", f"{health.speed:.2f}x")
    _ok("Canh bao frame dropped", str(health.dropped_warnings))
    _ok("Ly do", health.reason)


def main() -> None:
    latest, error = _find_latest_streaming_log_today()
    print_latest_streaming_log_today(latest, error)


if __name__ == "__main__":
    main()
