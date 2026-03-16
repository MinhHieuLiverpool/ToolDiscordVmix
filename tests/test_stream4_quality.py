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


def main() -> None:
    info, src_or_err = _parse_stream4_from_config()
    if info is None:
        # src_or_err đang là thông báo lỗi
        print_stream4(None, "current.config", src_or_err)
    else:
        print_stream4(info, src_or_err, None)


if __name__ == "__main__":
    main()
