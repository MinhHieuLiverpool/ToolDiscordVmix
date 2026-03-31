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

import argparse
import json
import glob
import html
import os
import re
import sys
import time
from datetime import datetime
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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


def _stream_sort_key(stream_name: str) -> Tuple[int, str]:
    m = re.match(r"streaming(\d+)$", stream_name.lower())
    if not m:
        return (9999, stream_name)
    return (int(m.group(1)), stream_name)


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
    stream_name: str
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


@dataclass
class StreamMonitorRow:
    stream_name: str
    enabled_config: str
    runtime_status: str
    health_status: str
    last_write: str
    file_name: str
    bitrate_actual: str
    bitrate_target: str


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


def _find_all_streaming_blocks(raw: str) -> Dict[str, str]:
    """Lấy toàn bộ block Streaming, Streaming2, Streaming3... trong config."""

    blocks: Dict[str, str] = {}
    for m in re.finditer(
        r'name="(Streaming\d*)"[^>]*>\s*<value>(.*?)</value>',
        raw,
        re.DOTALL | re.IGNORECASE,
    ):
        blocks[m.group(1)] = m.group(2)
    return blocks


def _setting_name_to_stream_key(setting_name: str) -> str:
    if setting_name.lower() == "streaming":
        return "streaming1"
    m = re.match(r"streaming(\d+)$", setting_name, re.IGNORECASE)
    if m:
        return f"streaming{m.group(1)}"
    return setting_name.lower()


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


def _parse_all_streams_from_config() -> Tuple[Dict[str, StreamInfo], str, Optional[str]]:
    vmix_dir = _vmix_data_dir()
    cfg = os.path.join(vmix_dir, "settingbackups", "current.config")
    if not os.path.isfile(cfg):
        return {}, cfg, f"Không tìm thấy file: {cfg}"

    try:
        raw = _read_file_shared(cfg)
    except Exception as ex:
        return {}, cfg, f"Lỗi đọc current.config: {ex}"

    blocks = _find_all_streaming_blocks(raw)
    src_path = cfg

    if not blocks:
        settings_dir = os.path.join(vmix_dir, "settingbackups")
        pattern = os.path.join(settings_dir, "*.config")
        for other in sorted(glob.glob(pattern)):
            if os.path.abspath(other) == os.path.abspath(cfg):
                continue
            try:
                raw_other = _read_file_shared(other)
            except Exception:
                continue
            blocks = _find_all_streaming_blocks(raw_other)
            if blocks:
                src_path = other
                break

    if not blocks:
        _debug_scan_vmix_for_streaming(vmix_dir)
        return {}, src_path, "Không tìm thấy block Streaming* trong current.config hoặc file backup"

    streams: Dict[str, StreamInfo] = {}
    parsed_names: List[str] = []
    for setting_name, xml_body in blocks.items():
        try:
            inner = html.unescape(xml_body.strip())
            root = ET.fromstring(f"<root>{inner}</root>")
        except ET.ParseError:
            continue
        stream_key = _setting_name_to_stream_key(setting_name)
        streams[stream_key] = _build_stream_info(root)
        parsed_names.append(setting_name)

    if not streams:
        return {}, src_path, "Có block Streaming* nhưng parse XML thất bại"

    parsed_names_sorted = ", ".join(sorted(parsed_names, key=lambda n: _stream_sort_key(_setting_name_to_stream_key(n))))
    src_label = f"{src_path} ({parsed_names_sorted})"
    return streams, src_label, None


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


def _find_latest_streaming_logs_by_stream() -> Tuple[Dict[str, LatestStreamingLog], Optional[str]]:
    streaming_dir = os.path.join(_vmix_data_dir(), "streaming")
    if not os.path.isdir(streaming_dir):
        return {}, f"Không tìm thấy thư mục: {streaming_dir}"

    latest_by_stream: Dict[str, Tuple[str, datetime]] = {}

    for name in os.listdir(streaming_dir):
        path = os.path.join(streaming_dir, name)
        if not os.path.isfile(path):
            continue

        # Chỉ nhận file bắt đầu bằng streaming<so>, ví dụ: streaming1 ....log/txt
        m_stream = re.match(r"^(streaming\d+)\b", name, re.IGNORECASE)
        if not m_stream:
            continue

        last_write = datetime.fromtimestamp(os.path.getmtime(path))
        stream_name = m_stream.group(1).lower()
        cur = latest_by_stream.get(stream_name)
        if cur is None or last_write > cur[1]:
            latest_by_stream[stream_name] = (path, last_write)

    if not latest_by_stream:
        return {}, "Không có file streaming* trong thư mục streaming"

    result: Dict[str, LatestStreamingLog] = {}
    for stream_name, (latest_path, latest_write) in latest_by_stream.items():
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

        result[stream_name] = LatestStreamingLog(
            stream_name=stream_name,
            file_path=latest_path,
            file_name=os.path.basename(latest_path),
            last_write=latest_write,
            quality_line=quality_line,
            raw_content=content,
        )

    return result, None


def _render_table(headers: List[str], rows: List[List[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def _line(parts: List[str]) -> str:
        return "| " + " | ".join(parts[i].ljust(widths[i]) for i in range(len(parts))) + " |"

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    print(sep)
    print(_line(headers))
    print(sep)
    for row in rows:
        print(_line(row))
    print(sep)


def _build_monitor_rows(
    streams_cfg: Dict[str, StreamInfo],
    latest_by_stream: Dict[str, LatestStreamingLog],
    live_window_sec: int,
) -> List[StreamMonitorRow]:
    rows: List[StreamMonitorRow] = []
    now = datetime.now()

    all_streams = sorted(set(streams_cfg.keys()) | set(latest_by_stream.keys()), key=_stream_sort_key)
    for stream_name in all_streams:
        info = streams_cfg.get(stream_name)
        latest = latest_by_stream.get(stream_name)

        if info is None:
            enabled_label = "UNKNOWN"
        else:
            enabled_label = "ON" if info.enabled else "OFF"

        if latest is None:
            runtime = "OFF"
            health_status = "-"
            last_write = "-"
            file_name = "-"
            bitrate_actual = "-"
        else:
            age_sec = (now - latest.last_write).total_seconds()
            runtime = "ON" if age_sec <= live_window_sec else "OFF"

            ui = _build_ui_snapshot(latest.raw_content)
            health = _assess_stream_health(latest, ui)
            health_status = health.status
            last_write = latest.last_write.strftime("%Y-%m-%d %H:%M:%S")
            file_name = latest.file_name
            bitrate_actual = f"{health.actual_bitrate_kbps:.0f}"

        target = _parse_k_to_kbps(info.video_bitrate) if info and info.video_bitrate else 0.0
        bitrate_target = f"{target:.0f}" if target > 0 else "-"

        rows.append(
            StreamMonitorRow(
                stream_name=stream_name,
                enabled_config=enabled_label,
                runtime_status=runtime,
                health_status=health_status,
                last_write=last_write,
                file_name=file_name,
                bitrate_actual=bitrate_actual,
                bitrate_target=bitrate_target,
            )
        )

    return rows


def _build_json_stream_entry(
    stream_name: str,
    info: Optional[StreamInfo],
    latest: Optional[LatestStreamingLog],
    ui: Optional[StreamingQualitySnapshot],
    health: Optional[StreamHealth],
    live_window_sec: int,
) -> Dict[str, object]:
    now = datetime.now()
    last_write_iso = latest.last_write.isoformat() if latest else None
    runtime_status = None
    if latest:
        age_sec = (now - latest.last_write).total_seconds()
        runtime_status = "ON" if age_sec <= live_window_sec else "OFF"

    return {
        "stream": stream_name,
        "config": {
            "enabled": info.enabled if info else None,
            "kind": info.kind if info else None,
            "host": info.host if info else None,
            "port": info.port if info else None,
            "path": info.path if info else None,
            "video_bitrate": info.video_bitrate if info else None,
            "audio_bitrate": info.audio_bitrate if info else None,
            "codec": info.codec if info else None,
            "quality": info.quality_label if info else None,
            "latency": info.latency if info else None,
            "passphrase_set": bool(info.passphrase) if info else None,
        },
        "runtime": {
            "status": runtime_status,
            "last_write": last_write_iso,
            "latest_log_file": latest.file_name if latest else None,
            "quality_line": latest.quality_line if latest else None,
        },
        "ui_snapshot": None
        if ui is None
        else {
            "video_bitrate": ui.video_bitrate,
            "encode_size": ui.encode_size,
            "audio_bitrate": ui.audio_bitrate,
            "profile": ui.profile,
            "level": ui.level,
            "preset": ui.preset,
            "aspect_ratio_crop": ui.aspect_ratio_crop,
            "audio_format": ui.audio_format,
            "channels": ui.channels,
            "keyframe_frequency": ui.keyframe_frequency,
            "stream_delay": ui.stream_delay,
            "threads": ui.threads,
            "network_buffer": ui.network_buffer,
            "strict_cbr": ui.strict_cbr,
            "nal_cbr": ui.nal_cbr,
            "keyframe_aligned": ui.keyframe_aligned,
        },
        "health": None
        if health is None
        else {
            "status": health.status,
            "reason": health.reason,
            "actual_bitrate_kbps": health.actual_bitrate_kbps,
            "target_bitrate_kbps": health.target_bitrate_kbps,
            "bitrate_ratio": health.bitrate_ratio,
            "encode_speed": health.speed,
            "dropped_warnings": health.dropped_warnings,
        },
    }


def _export_json_snapshot(
    streams_cfg: Dict[str, StreamInfo],
    latest_by_stream: Dict[str, LatestStreamingLog],
    cfg_source: str,
    cfg_error: Optional[str],
    log_error: Optional[str],
    live_window_sec: int,
    json_out_path: str | None,
    json_stdout: bool,
) -> None:
    payload: Dict[str, object] = {
        "generated_at": datetime.now().isoformat(),
        "config_source": cfg_source,
        "config_error": cfg_error,
        "log_error": log_error,
        "streams": [],
    }

    all_streams = sorted(set(streams_cfg.keys()) | set(latest_by_stream.keys()), key=_stream_sort_key)
    for stream_name in all_streams:
        info = streams_cfg.get(stream_name)
        latest = latest_by_stream.get(stream_name)
        ui = _build_ui_snapshot(latest.raw_content) if latest else None
        health = _assess_stream_health(latest, ui) if latest and ui else None
        payload["streams"].append(
            _build_json_stream_entry(stream_name, info, latest, ui, health, live_window_sec)
        )

    text = json.dumps(payload, ensure_ascii=True, indent=2)

    if json_out_path:
        with open(json_out_path, "w", encoding="utf-8") as f:
            f.write(text)

    if json_stdout:
        print("\nJSON SNAPSHOT:")
        print(text)


def _render_monitor_screen(
    interval_sec: int,
    live_window_sec: int,
    json_out_path: str | None = None,
    json_stdout: bool = False,
) -> None:
    streams_cfg, cfg_source, cfg_error = _parse_all_streams_from_config()
    latest_by_stream, log_error = _find_latest_streaming_logs_by_stream()

    os.system("cls" if os.name == "nt" else "clear")
    _sep("LOOP STREAM MONITOR")
    _ok("Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    _ok("Config source", cfg_source)
    _ok("Refresh", f"{interval_sec}s")
    _ok("Live window", f"{live_window_sec}s")
    print()

    if cfg_error:
        _warn("Config", cfg_error)
    if log_error:
        _warn("Logs", log_error)

    rows = _build_monitor_rows(streams_cfg, latest_by_stream, live_window_sec)
    if not rows:
        _warn("Monitor", "Khong co stream nao de hien thi")
        return

    headers = [
        "Stream",
        "Enabled",
        "Runtime",
        "Health",
        "Actual(kbps)",
        "Target(kbps)",
        "LastWrite",
        "LatestFile",
    ]
    table_rows = [
        [
            r.stream_name,
            r.enabled_config,
            r.runtime_status,
            r.health_status,
            r.bitrate_actual,
            r.bitrate_target,
            r.last_write,
            r.file_name,
        ]
        for r in rows
    ]
    _render_table(headers, table_rows)
    print("\nNhan Ctrl+C de thoat monitor")

    if json_out_path or json_stdout:
        _export_json_snapshot(
            streams_cfg,
            latest_by_stream,
            cfg_source,
            cfg_error,
            log_error,
            live_window_sec,
            json_out_path,
            json_stdout,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Loop monitor cho cac stream vMix")
    parser.add_argument("--interval", type=int, default=2, help="So giay refresh man hinh")
    parser.add_argument("--live-window", type=int, default=15, help="So giay de xep stream la ON")
    parser.add_argument("--once", action="store_true", help="Render mot lan roi thoat")
    parser.add_argument("--json-out", type=str, default="", help="Ghi snapshot JSON ra file (overwrite moi lan)")
    parser.add_argument("--json-stdout", action="store_true", help="In snapshot JSON ra stdout")
    return parser.parse_args()


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


def print_latest_streaming_logs_today(
    latest_by_stream: Dict[str, LatestStreamingLog],
    error: Optional[str],
) -> None:
    _sep("STREAMING LOG HOM NAY - MOI STREAM 1,2,3...")
    if error:
        _err("Trang thai", error)
        return

    if not latest_by_stream:
        _err("Trang thai", "Khong co du lieu")
        return

    for stream_name in sorted(latest_by_stream.keys(), key=_stream_sort_key):
        latest = latest_by_stream[stream_name]
        _sep(f"{stream_name.upper()} - FILE MOI NHAT TRONG NGAY")

        _ok("File moi nhat", latest.file_name)
        _ok("LastWrite", latest.last_write.strftime("%Y-%m-%d %H:%M:%S"))
        _ok("Duong dan", latest.file_path)
        if latest.quality_line:
            _ok("Quality line", latest.quality_line)
        else:
            _warn("Quality line", "Khong tim thay dong quality trong log")

        ui = _build_ui_snapshot(latest.raw_content)
        _sep(f"{stream_name.upper()} - DOI CHIEU STREAMING QUALITY (TU LOG)")
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
        _sep(f"{stream_name.upper()} - DANH GIA MAU STREAM")
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
    args = _parse_args()

    if args.once:
        _render_monitor_screen(
            interval_sec=args.interval,
            live_window_sec=args.live_window,
            json_out_path=args.json_out or None,
            json_stdout=args.json_stdout,
        )
        return

    while True:
        try:
            _render_monitor_screen(
                interval_sec=args.interval,
                live_window_sec=args.live_window,
                json_out_path=args.json_out or None,
                json_stdout=args.json_stdout,
            )
            time.sleep(max(1, args.interval))
        except KeyboardInterrupt:
            print("\nThoat loop monitor")
            break


if __name__ == "__main__":
    main()
