"""
test_vmix_resolution_srt.py
────────────────────────────────────────────────────────────────────────────────
Standalone tester cho vMix Resolution & SRT Quality.

Ba phương pháp được test:
  1. file-based  – doc C:/ProgramData/vMix/video.txt + settingbackups/current.config
  2. preset-based – tìm file *.vmix mới nhất rồi parse XML
  3. HTTP API     – GET http://localhost:{port}/api

Chạy:  python test_vmix_resolution_srt.py [--port 8088]
────────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import glob
import html
import re
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime

# ─── màu ANSI (tắt tự động nếu stdout không phải terminal / Windows cũ) ───────
_USE_COLOR = sys.stdout.isatty() or os.environ.get("TERM") not in (None, "")
_R  = "\033[91m" if _USE_COLOR else ""
_G  = "\033[92m" if _USE_COLOR else ""
_Y  = "\033[93m" if _USE_COLOR else ""
_C  = "\033[96m" if _USE_COLOR else ""
_B  = "\033[1m"  if _USE_COLOR else ""
_X  = "\033[0m"  if _USE_COLOR else ""

SEP = f"{_C}{'─' * 70}{_X}"


def header(text: str):
    print(f"\n{SEP}")
    print(f"{_B}{_C}  {text}{_X}")
    print(SEP)


def ok(label: str, value: str):
    print(f"  {_G}✔{_X}  {_B}{label:<28}{_X}  {value}")


def warn(label: str, value: str):
    print(f"  {_Y}⚠{_X}  {_B}{label:<28}{_X}  {value}")


def err(label: str, value: str):
    print(f"  {_R}✘{_X}  {_B}{label:<28}{_X}  {value}")


# ══════════════════════════════════════════════════════════════════════════════
# Helpers chung
# ══════════════════════════════════════════════════════════════════════════════

def _vmix_data_dir() -> str:
    base = (os.environ.get("PROGRAMDATA")
            or os.environ.get("ALLUSERSPROFILE")
            or r"C:\ProgramData")
    return os.path.join(base, "vMix")


def _read_file_shared(filepath: str) -> str:
    """
    Đọc file ngay cả khi bị vMix lock (Windows).
    Dùng CreateFileW với FILE_SHARE_READ|WRITE|DELETE để bypass exclusive lock.
    """
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    GENERIC_READ        = 0x80000000
    FILE_SHARE_ALL      = 0x07  # READ | WRITE | DELETE
    OPEN_EXISTING       = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE      = ctypes.c_void_p(-1).value

    handle = kernel32.CreateFileW(
        filepath, GENERIC_READ, FILE_SHARE_ALL,
        None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None,
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
        return buf.raw[:read.value].decode('utf-8', errors='replace')
    finally:
        kernel32.CloseHandle(handle)


def _fps_from_ticks(ticks_str: str) -> str:
    """Chuyển ticks (100 ns/frame) → chuỗi fps thân thiện."""
    try:
        ticks = int(ticks_str)
        if ticks <= 0:
            return "?"
        fps_val = 10_000_000 / ticks
        for std, lbl in [
            (23.976, "23.976"), (24, "24"), (25, "25"),
            (29.97,  "29.97"),  (30, "30"), (50, "50"),
            (59.94,  "59.94"),  (60, "60"),
        ]:
            if abs(fps_val - std) < 0.1:
                return lbl
        return f"{fps_val:.4g}"
    except (ValueError, ZeroDivisionError):
        return "?"


def _bw_str(bps_str: str) -> str:
    """Chuyển bandwidth bps → chuỗi dễ đọc."""
    try:
        bps = int(bps_str)
        if bps >= 1_000_000:
            return f"{bps // 1_000_000}Mbps"
        return f"{bps // 1_000}kbps"
    except ValueError:
        return "?"


# ══════════════════════════════════════════════════════════════════════════════
# Method 1 – File-based (video.txt + current.config)
# ══════════════════════════════════════════════════════════════════════════════

def test_file_based() -> tuple[str, dict]:
    """
    Đọc Resolution từ <ProgramData>\\vMix\\video.txt
    Đọc SRT Quality từ <ProgramData>\\vMix\\settingbackups\\current.config
    Trả về: (resolution_str, {port: quality_str})
    """
    header("METHOD 1 – File-based  (video.txt + current.config)")

    vmix_dir    = _vmix_data_dir()
    video_txt   = os.path.join(vmix_dir, "video.txt")
    config_file = os.path.join(vmix_dir, "settingbackups", "current.config")

    print(f"  Thư mục vMix ProgramData : {vmix_dir}")
    print(f"  video.txt                : {video_txt}")
    print(f"  current.config           : {config_file}")
    print()

    # ── Resolution ──────────────────────────────────────────────────────────
    resolution = "—"
    if not os.path.isfile(video_txt):
        err("video.txt", "KHÔNG TÌM THẤY")
    else:
        try:
            raw_text = _read_file_shared(video_txt)
            lines = [ln.strip() for ln in raw_text.splitlines()]

            raw_w   = lines[0] if len(lines) > 0 else ""
            raw_h   = lines[1] if len(lines) > 1 else ""
            raw_fps = lines[2] if len(lines) > 2 else ""

            ok("video.txt line 0 (width)", raw_w  or "(trống)")
            ok("video.txt line 1 (height)", raw_h or "(trống)")
            ok("video.txt line 2 (ticks)", raw_fps or "(trống)")

            fps_str = _fps_from_ticks(raw_fps) if raw_fps else ""
            if raw_h:
                resolution = f"{raw_h}p{fps_str}" if fps_str else f"{raw_h}p"
                ok("→ Resolution (canvas)", resolution)
                warn("⚠ Lưu ý",
                     "video.txt = canvas/master resolution (có thể KHÁC output resolution)")
            else:
                warn("→ Resolution", "Không đọc được height")
        except Exception as ex:
            err("Đọc video.txt", str(ex))

    # ── Cross-check: đọc OutputFormat từ last.vmix trong APPDATA ────────────
    appdata_preset = os.path.join(os.environ.get("APPDATA", ""), "last.vmix")
    if os.path.isfile(appdata_preset):
        try:
            _pt = ET.parse(appdata_preset)
            _of = _pt.getroot().find(".//OutputFormat")
            if _of is not None:
                _size = _of.get("OutputSize", "")
                _fr_t = _of.get("OutputFrameRate", "")
                _h    = _size.split("x")[1] if "x" in _size else ""
                _fps  = _fps_from_ticks(_fr_t) if _fr_t else ""
                cross_res = f"{_h}p{_fps}" if _h and _fps else (f"{_h}p" if _h else "—")
                ok("→ Output resolution (preset)", cross_res)
                if cross_res != resolution and cross_res != "—":
                    warn("→ KHÁC NHAU vì",
                         f"canvas={resolution}  |  output={cross_res}  "
                         "← output/stream dùng giá trị này")
        except Exception:
            pass
    else:
        warn("Cross-check preset", f"{appdata_preset}  không tìm thấy")

    # ── SRT Quality ─────────────────────────────────────────────────────────
    srt_by_port: dict = {}
    if not os.path.isfile(config_file):
        err("current.config", "KHÔNG TÌM THẤY")
    else:
        try:
            content = _read_file_shared(config_file)

            found_any = False
            for ext_name in ("OutputsExternal", "OutputsExternal2",
                             "OutputsExternal3", "OutputsExternal4"):
                m = re.search(
                    rf'name="{re.escape(ext_name)}"[^>]*>\s*<value>(.*?)</value>',
                    content, re.DOTALL,
                )
                if not m:
                    continue

                decoded = html.unescape(m.group(1).strip())
                try:
                    sub = ET.fromstring(f"<root>{decoded}</root>")
                except ET.ParseError as pe:
                    warn(ext_name, f"Parse lỗi XML: {pe}")
                    continue

                found_any = True
                port_str  = (sub.findtext("SRTPort") or "0").strip()
                try:
                    port = int(port_str)
                except ValueError:
                    port = 0

                enabled  = (sub.findtext("SRTEnabled") or "0").strip()
                codec_id = (sub.findtext("SRTVideoCodec") or "").strip()
                warn(f"{ext_name} SRTVideoCodec (raw)", repr(codec_id) + "  (0=H264, 1=HEVC)")
                codec    = "HEVC" if codec_id == "1" else "H264"
                vbw_s    = _bw_str(sub.findtext("SRTVideoBandwidth") or "0")
                abw_s    = _bw_str(sub.findtext("SRTAudioBandwidth") or "0")
                hw       = " HW" if (sub.findtext("SRTHardwareEncoder") or "0").strip() == "1" else ""
                quality  = f"{codec} {vbw_s} AAC {abw_s}{hw}"

                label = f"{ext_name} (port {port or 'N/A'})"
                if enabled == "1" and port:
                    ok(label, f"{quality}  [ENABLED]")
                    srt_by_port[port] = quality
                elif port:
                    warn(label, f"{quality}  [disabled]")
                else:
                    warn(ext_name, f"{quality}  [port=0, bỏ qua]")

            if not found_any:
                warn("SRT", "Không tìm thấy khối OutputsExternal* trong current.config")
        except Exception as ex:
            err("Đọc current.config", str(ex))

    print()
    print(f"  {_B}KẾT QUẢ Method 1:{_X}")
    ok("Resolution", resolution)
    if srt_by_port:
        for p, q in srt_by_port.items():
            ok(f"SRT (port {p})", q)
    else:
        warn("SRT", "Không có SRT nào đang bật")

    return resolution, srt_by_port


# ══════════════════════════════════════════════════════════════════════════════
# Method 2 – Preset-based (*.vmix file XML)
# ══════════════════════════════════════════════════════════════════════════════

def _find_vmix_preset() -> str | None:
    """Tìm file *.vmix từ process cmdline → documents → desktop."""
    # Thử lấy từ cmdline tiến trình vMix
    try:
        import psutil
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                if "vmix" in (proc.info["name"] or "").lower():
                    for arg in (proc.info.get("cmdline") or []):
                        if arg.lower().endswith(".vmix") and os.path.isfile(arg):
                            return arg
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        pass

    # Tìm file mới nhất trong các thư mục phổ biến
    search_dirs = []
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        search_dirs.append(os.path.join(appdata, "vMix"))
    home = os.path.expanduser("~")
    search_dirs += [
        os.path.join(home, "Documents", "vMix"),
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
    ]
    candidates = []
    for d in search_dirs:
        candidates.extend(glob.glob(os.path.join(d, "*.vmix")))
    if candidates:
        return max(candidates, key=os.path.getmtime)
    return None


def test_preset_based() -> tuple[str, dict]:
    """Parse file *.vmix – lấy Resolution từ <OutputFormat> và SRT từ <OutputsExternal*>."""
    header("METHOD 2 – Preset-based  (*.vmix XML file)")

    preset = _find_vmix_preset()
    if not preset:
        err("File *.vmix", "Không tìm thấy (vMix chưa mở hoặc chưa lưu preset)")
        print()
        return "—", {}

    mtime = datetime.fromtimestamp(os.path.getmtime(preset)).strftime("%Y-%m-%d %H:%M:%S")
    ok("Preset file", preset)
    ok("Modified", mtime)
    print()

    resolution = "—"
    srt_by_port: dict = {}

    try:
        tree = ET.parse(preset)
        root = tree.getroot()

        # ── Resolution ────────────────────────────────────────────────────────
        out_fmt = root.find(".//OutputFormat")
        if out_fmt is not None:
            size   = out_fmt.get("OutputSize", "")        # "1920x1080"
            fr_t   = out_fmt.get("OutputFrameRate", "")   # ticks
            h      = size.split("x")[1] if "x" in size else ""
            fps_str = _fps_from_ticks(fr_t) if fr_t else ""
            ok("<OutputFormat> OutputSize",       size or "(trống)")
            ok("<OutputFormat> OutputFrameRate",  fr_t or "(trống)")
            if h:
                resolution = f"{h}p{fps_str}" if fps_str else f"{h}p"
                ok("→ Resolution", resolution)
        else:
            warn("<OutputFormat>", "Không tìm thấy – thử fallback <output>")
            # Fallback
            for path in [".//output", ".//Output", ".//settings/output"]:
                out_e = root.find(path)
                if out_e is not None:
                    h  = out_e.get("height") or out_e.findtext("height", "")
                    fr = (out_e.get("framerate") or out_e.get("frameRate")
                          or out_e.findtext("framerate") or out_e.findtext("frameRate", ""))
                    if h:
                        fps_str = ""
                        if fr:
                            try:
                                fps_str = f"{float(str(fr).replace(',', '.')):.4g}"
                            except ValueError:
                                fps_str = fr
                        resolution = f"{h}p{fps_str}" if fps_str else f"{h}p"
                        ok(f"→ Resolution (fallback {path})", resolution)
                        break
            else:
                warn("→ Resolution", "Không đọc được từ preset")

        # ── SRT Quality ────────────────────────────────────────────────────────
        for ext_name in ("OutputsExternal", "OutputsExternal2",
                          "OutputsExternal3", "OutputsExternal4"):
            ext = root.find(f".//{ext_name}")
            if ext is None:
                continue
            enabled = (ext.findtext("SRTEnabled") or "0").strip()
            port_str = (ext.findtext("SRTPort") or "0").strip()
            try:
                port = int(port_str)
            except ValueError:
                port = 0

            codec_id = (ext.findtext("SRTVideoCodec") or "").strip()
            warn(f"<{ext_name}> SRTVideoCodec (raw)", repr(codec_id) + "  (0=H264, 1=HEVC)")
            codec    = "HEVC" if codec_id == "1" else "H264"
            vbw_s    = _bw_str(ext.findtext("SRTVideoBandwidth") or "0")
            abw_s    = _bw_str(ext.findtext("SRTAudioBandwidth") or "0")
            hw       = " HW" if (ext.findtext("SRTHardwareEncoder") or "0").strip() == "1" else ""
            quality  = f"{codec} {vbw_s} AAC {abw_s}{hw}"

            label = f"<{ext_name}> port={port or 'N/A'}"
            if enabled == "1" and port:
                ok(label, f"{quality}  [ENABLED]")
                srt_by_port[port] = quality
            elif port:
                warn(label, f"{quality}  [disabled]")
            else:
                warn(f"<{ext_name}>", f"{quality}  [port=0, bỏ qua]")

    except ET.ParseError as pe:
        err("Parse XML preset", str(pe))
    except Exception as ex:
        err("Đọc preset", str(ex))

    print()
    print(f"  {_B}KẾT QUẢ Method 2:{_X}")
    ok("Resolution", resolution)
    if srt_by_port:
        for p, q in srt_by_port.items():
            ok(f"SRT (port {p})", q)
    else:
        warn("SRT", "Không có SRT nào đang bật")

    return resolution, srt_by_port


# ══════════════════════════════════════════════════════════════════════════════
# Method 3 – HTTP API  (localhost:{port}/api)
# ══════════════════════════════════════════════════════════════════════════════

def test_http_api(api_port: int = 8088) -> tuple[str, dict]:
    """GET http://localhost:{api_port}/api rồi parse XML response."""
    header(f"METHOD 3 – HTTP API  (http://localhost:{api_port}/api)")

    try:
        import requests as req
    except ImportError:
        err("requests", "Module 'requests' chưa được cài – pip install requests")
        return "—", {}

    url = f"http://localhost:{api_port}/api"
    print(f"  URL: {url}")
    print()

    resolution = "—"
    srt_by_port: dict = {}

    try:
        resp = req.get(url, timeout=3)
        ok("HTTP status", str(resp.status_code))

        if resp.status_code != 200:
            err("Response", f"Không phải 200 OK – vMix có đang chạy không?")
            return "—", {}

        root = ET.fromstring(resp.content)

        # ── Thông tin chung ───────────────────────────────────────────────────
        version   = root.findtext("version",   "—")
        edition   = root.findtext("edition",   "—")
        recording = root.findtext("recording", "False")
        streaming = root.findtext("streaming", "False")
        external  = root.findtext("external",  "False")
        ok("version", version)
        ok("edition", edition)
        ok("recording",  recording)
        ok("streaming",  streaming)
        ok("external",   external)
        print()

        # ── Resolution từ API root ────────────────────────────────────────────
        h = (root.get("height", "") or root.findtext("height", "")
             or root.findtext("outputHeight", ""))
        fps_raw = (root.findtext("masterFrameRate", "")
                   or root.findtext("frameRate", "")
                   or root.findtext("outputFrameRate", ""))

        # Thử lấy từ inputs/input đầu tiên nếu root chưa có
        inputs_elem = root.find("inputs")
        if not h and inputs_elem is not None:
            first_inp = inputs_elem.find("input")
            if first_inp is not None:
                h       = first_inp.get("height", "")
                fps_raw = fps_raw or first_inp.get("framerate", "") or first_inp.get("frameRate", "")

        ok("height (raw)",    h       or "(trống)")
        ok("fps_raw",         fps_raw or "(trống)")

        fps_str = "—"
        if fps_raw:
            try:
                fps_val = float(fps_raw.replace(",", "."))
                fps_str = f"{fps_val:.4g}"
            except ValueError:
                fps_str = fps_raw

        if h:
            resolution = f"{h}p{fps_str}" if fps_str != "—" else f"{h}p"

        # ── Dùng preset_path từ API → đọc lại OutputFormat nếu cần ─────────
        preset_path = root.findtext("preset", "") or root.findtext("Preset", "")
        if preset_path:
            ok("preset path (từ API)", preset_path)
            if os.path.isfile(preset_path):
                try:
                    _pt = ET.parse(preset_path)
                    _pr = _pt.getroot()
                    _of = _pr.find(".//OutputFormat")
                    if _of is not None and resolution == "—":
                        _size = _of.get("OutputSize", "")
                        _fr_t = _of.get("OutputFrameRate", "")
                        _h    = _size.split("x")[1] if "x" in _size else ""
                        _fps  = _fps_from_ticks(_fr_t) if _fr_t else ""
                        if _h:
                            resolution = f"{_h}p{_fps}" if _fps else f"{_h}p"
                            ok("→ Resolution (từ preset)", resolution)
                    # SRT từ preset
                    for ext_name in ("OutputsExternal", "OutputsExternal2",
                                     "OutputsExternal3", "OutputsExternal4"):
                        ext = _pr.find(f".//{ext_name}")
                        if ext is None:
                            continue
                        enabled  = (ext.findtext("SRTEnabled") or "0").strip()
                        port_str = (ext.findtext("SRTPort") or "0").strip()
                        try:
                            port = int(port_str)
                        except ValueError:
                            port = 0
                        codec_id = (ext.findtext("SRTVideoCodec") or "").strip()
                        warn(f"<{ext_name}> SRTVideoCodec (raw)", repr(codec_id) + "  (0=H264, 1=HEVC)")
                        codec    = "HEVC" if codec_id == "1" else "H264"
                        vbw_s    = _bw_str(ext.findtext("SRTVideoBandwidth") or "0")
                        abw_s    = _bw_str(ext.findtext("SRTAudioBandwidth") or "0")
                        hw       = " HW" if (ext.findtext("SRTHardwareEncoder") or "0") == "1" else ""
                        quality  = f"{codec} {vbw_s} AAC {abw_s}{hw}"
                        label    = f"<{ext_name}> port={port or 'N/A'}"
                        if enabled == "1" and port:
                            ok(label, f"{quality}  [ENABLED]")
                            srt_by_port[port] = quality
                        elif port:
                            warn(label, f"{quality}  [disabled]")
                except Exception as ex:
                    warn("Đọc preset từ API path", str(ex))
            else:
                warn("preset path", "File không tồn tại trên ổ đĩa – skip")
        else:
            warn("preset path", "API không trả về <preset> (vMix cũ hơn 26?)")

    except req.exceptions.ConnectionError:
        err("Kết nối", f"Không thể kết nối localhost:{api_port}  – vMix có đang chạy không?")
        return "—", {}
    except req.exceptions.Timeout:
        err("Timeout", f"API không phản hồi trong 3 giây")
        return "—", {}
    except ET.ParseError as pe:
        err("Parse XML", str(pe))
        return "—", {}
    except Exception as ex:
        err("Lỗi không xác định", str(ex))
        return "—", {}

    print()
    print(f"  {_B}KẾT QUẢ Method 3:{_X}")
    ok("Resolution", resolution)
    if srt_by_port:
        for p, q in srt_by_port.items():
            ok(f"SRT (port {p})", q)
    else:
        warn("SRT", "Không có SRT nào đang bật (hoặc preset không trả về)")

    return resolution, srt_by_port


# ══════════════════════════════════════════════════════════════════════════════
# Method 4 – External Output hardware settings (Device / SDI / HDMI)
# ══════════════════════════════════════════════════════════════════════════════

def _parse_ext_output_elem(ext, ext_name: str, idx: int) -> dict:
    """Extract hardware external-output fields from an XML element."""
    def _t(name: str) -> str:
        return (ext.findtext(name) or "").strip()

    info: dict = {}

    # ── trạng thái tổng ──────────────────────────────────────────────────────
    info["Enabled"]               = _t("Enabled") or _t("enabled")
    info["UseStreamingSettings"]  = _t("UseStreamingSettings")
    info["UseDisplaySettings"]    = _t("UseDisplaySettings")
    info["ExternalRenderer"]      = _t("ExternalRenderer")
    info["VMixVideoStreaming"]     = _t("VMixVideoStreaming") or _t("vMixVideoStreaming")

    # ── thông số output ───────────────────────────────────────────────────────
    size = _t("OutputSize") or _t("ExternalOutputSize")
    info["OutputSize"]  = size

    fr = (_t("FrameRate") or _t("OutputFrameRate") or _t("ExternalFrameRate"))
    if not fr:
        ticks = _t("FrameRateTicks") or _t("OutputFrameRateTicks")
        fr = _fps_from_ticks(ticks) if ticks else ""
    info["FrameRate"]   = fr

    info["Device"]        = _t("DeviceName") or _t("Device")
    info["Port"]          = _t("Port") or _t("OutputPort")
    info["AudioChannels"] = _t("AudioChannels") or _t("AudioChannel")
    info["AlphaChannel"]  = _t("AlphaChannel")
    info["AudioDelay"]    = _t("AudioDelay")

    # ── SRT (tóm tắt) ─────────────────────────────────────────────────────────
    info["SRTEnabled"]  = _t("SRTEnabled")
    info["SRTPort"]     = _t("SRTPort")
    codec_id = _t("SRTVideoCodec")
    info["SRTCodec"]    = ("HEVC" if codec_id == "1" else "H264") if codec_id else ""
    info["SRTVideoBW"]  = _bw_str(_t("SRTVideoBandwidth") or "0") if _t("SRTVideoBandwidth") else ""
    info["SRTAudioBW"]  = _bw_str(_t("SRTAudioBandwidth")  or "0") if _t("SRTAudioBandwidth") else ""
    info["SRTHW"]       = _t("SRTHardwareEncoder")

    return info


def _print_ext_output_info(info: dict, idx: int, ext_name: str):
    """Format and print one External Output block."""
    def _show(label: str, key: str, fn=None):
        val = info.get(key, "")
        if val:
            display = fn(val) if fn else val
            ok(f"[Ext{idx}] {label}", display)
        else:
            warn(f"[Ext{idx}] {label}", "(không có)")

    enabled = info.get("Enabled", "—")
    color = _G if enabled.lower() in ("true", "1") else _Y
    print(f"\n  {_B}{color}── {ext_name}  (External {idx})  Enabled={enabled}{_X}")

    _show("Output Size",             "OutputSize")
    _show("Frame Rate",              "FrameRate")
    _show("Device",                  "Device")
    _show("Port",                    "Port")
    _show("Audio Channels",          "AudioChannels")
    _show("Alpha Channel",           "AlphaChannel")
    _show("Audio Delay (ms)",        "AudioDelay")
    _show("Use Streaming Settings",  "UseStreamingSettings")
    _show("Use Display Settings",    "UseDisplaySettings")
    _show("External Renderer",       "ExternalRenderer")
    _show("vMix Video/Streaming",    "VMixVideoStreaming")

    srt_enabled = info.get("SRTEnabled", "0")
    if srt_enabled == "1":
        port = info.get("SRTPort", "?")
        codec = info.get("SRTCodec", "H264")
        vbw   = info.get("SRTVideoBW", "?")
        abw   = info.get("SRTAudioBW", "?")
        hw    = " HW" if info.get("SRTHW") == "1" else ""
        ok(f"[Ext{idx}] SRT",
           f"port={port}  {codec} {vbw} AAC {abw}{hw}  [ENABLED]")
    else:
        warn(f"[Ext{idx}] SRT", "disabled")


def test_external_output() -> list[dict]:
    """
    Đọc toàn bộ thông số External Output (hardware + SRT) từ preset *.vmix.
    Trả về danh sách dict thông số mỗi External Output.
    """
    header("METHOD 4 – External Output  (Device / SDI / HDMI / SRT tổng hợp)")

    # ── Tìm nguồn dữ liệu ────────────────────────────────────────────────────
    root = None
    source_label = ""

    preset = _find_vmix_preset()
    if preset:
        try:
            root = ET.parse(preset).getroot()
            mtime = datetime.fromtimestamp(os.path.getmtime(preset)).strftime("%Y-%m-%d %H:%M:%S")
            source_label = f"{os.path.basename(preset)}  [{mtime}]"
        except Exception as ex:
            warn("Đọc preset", str(ex))
            root = None

    if root is None:
        # Fallback: current.config (regex → parse inner XML value)
        config_file = os.path.join(_vmix_data_dir(), "settingbackups", "current.config")
        if os.path.isfile(config_file):
            try:
                content = _read_file_shared(config_file)
                # Ghép tất cả OutputsExternal* thành pseudo-XML để parse
                # (dùng như Method 1 đã làm)
                source_label = "current.config"
                results_list = []
                for idx, ext_name in enumerate(
                    ("OutputsExternal", "OutputsExternal2",
                     "OutputsExternal3", "OutputsExternal4"), start=1
                ):
                    m = re.search(
                        rf'name="{re.escape(ext_name)}"[^>]*>\s*<value>(.*?)</value>',
                        content, re.DOTALL,
                    )
                    if not m:
                        continue
                    decoded = html.unescape(m.group(1).strip())
                    try:
                        sub = ET.fromstring(f"<root>{decoded}</root>")
                    except ET.ParseError:
                        continue
                    info = _parse_ext_output_elem(sub, ext_name, idx)
                    results_list.append(info)
                    _print_ext_output_info(info, idx, ext_name)
                ok("Nguồn dữ liệu", source_label)
                return results_list
            except Exception as ex:
                err("Đọc current.config", str(ex))
        err("Nguồn dữ liệu", "Không tìm thấy preset *.vmix hay current.config")
        return []

    ok("Nguồn dữ liệu", source_label)

    results_list = []
    found_any = False
    for idx, ext_name in enumerate(
        ("OutputsExternal", "OutputsExternal2",
         "OutputsExternal3", "OutputsExternal4"), start=1
    ):
        ext = root.find(f".//{ext_name}")
        if ext is None:
            continue
        found_any = True
        info = _parse_ext_output_elem(ext, ext_name, idx)
        results_list.append(info)
        _print_ext_output_info(info, idx, ext_name)

    if not found_any:
        warn("External Output", "Không tìm thấy OutputsExternal* trong preset")

    print()
    return results_list


# ══════════════════════════════════════════════════════════════════════════════
# Tổng hợp
# ══════════════════════════════════════════════════════════════════════════════

def print_summary(results: dict):
    header("TỔNG HỢP KẾT QUẢ")
    note = {
        "1-file":   "canvas res (video.txt) – có thể khác output",
        "2-preset": "output res từ OutputFormat trong *.vmix",
        "3-http":   "★ CHÍNH XÁC NHẤT – output res từ preset qua API",
    }
    fmt = f"  {{:<14}}  {{:<22}}  {{:<32}}  {{}}"
    print(fmt.format("Method", "Resolution", "SRT Quality", "Ghi chú"))
    print(f"  {'─'*12}  {'─'*20}  {'─'*30}  {'─'*45}")
    for method, (res, srt) in results.items():
        srt_str = ", ".join(f"port {p}: {q}" for p, q in srt.items()) if srt else "—"
        print(fmt.format(method, res, srt_str, note.get(method, "")))
    print()
    print(f"  {_Y}Lý do file khác API:{_X} video.txt lưu canvas/master resolution.")
    print(f"  OutputFormat trong preset mới là output/streaming resolution thực tế.")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def _run_once(method: str, api_port: int) -> dict:
    results = {}
    if method in ("1", "all"):
        results["1-file"]   = test_file_based()
    if method in ("2", "all"):
        results["2-preset"] = test_preset_based()
    if method in ("3", "all"):
        results["3-http"]   = test_http_api(api_port)
    if method in ("ext", "all"):
        test_external_output()
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Test vMix Resolution & SRT Quality bằng 3 phương pháp."
    )
    parser.add_argument(
        "--port", type=int, default=8088,
        help="vMix HTTP API port (mặc định: 8088)"
    )
    parser.add_argument(
        "--method", choices=["1", "2", "3", "ext", "all"], default="all",
        help="Chọn phương pháp: 1=file, 2=preset, 3=http, ext=external-output, all=tất cả (mặc định: all)"
    )
    parser.add_argument(
        "--watch", type=int, metavar="GIÂY", nargs="?", const=3,
        help="Tự động refresh mỗi N giây (mặc định 3s nếu không truyền số). Nhấn Ctrl+C để thoát."
    )
    args = parser.parse_args()

    if args.watch is None:
        # Chế độ chạy 1 lần
        print(f"\n{_B}{'=' * 70}")
        print(f"  vMix Resolution & SRT Quality Tester")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 70}{_X}")
        results = _run_once(args.method, args.port)
        if len(results) > 1:
            print_summary(results)
        print(f"{SEP}\n")
    else:
        # Chế độ watch – tự refresh
        interval = max(1, args.watch)
        print(f"\n{_B}{'=' * 70}")
        print(f"  vMix Resolution & SRT Quality Tester  [WATCH mode – {interval}s]")
        print(f"  Nhấn Ctrl+C để thoát.")
        print(f"{'=' * 70}{_X}")

        import time
        try:
            while True:
                # Xoá màn hình (Windows: cls, Unix: clear)
                os.system("cls" if os.name == "nt" else "clear")
                print(f"\n{_B}{'=' * 70}")
                print(f"  vMix Monitor  [WATCH {interval}s]   {datetime.now().strftime('%H:%M:%S')}   Ctrl+C = thoát")
                print(f"{'=' * 70}{_X}")

                results = _run_once(args.method, args.port)
                if len(results) > 1:
                    print_summary(results)
                print(f"{SEP}")
                print(f"  {_Y}Cập nhật lại sau {interval}s ...{_X}\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n{_Y}Đã thoát watch mode.{_X}\n")


if __name__ == "__main__":
    main()
