"""
test_vmix_external.py
────────────────────────────────────────────────────────────────────────────────
Standalone tester cho vMix External Output hardware settings.

Hiển thị đầy đủ thông số External 1 / External 2 / External 3 / External 4:
  • Frame Rate, Output Size
  • Device, Port (SDI / HDMI / ...)
  • Audio Channels, Alpha Channel, Audio Delay
  • Checkbox: vMix Video/Streaming, External Renderer,
              Use Streaming Settings, Use Display Settings
  • SRT status (enabled/disabled + port, không hiện raw codec warning)

Nguồn dữ liệu (theo thứ tự ưu tiên):
  1. File *.vmix mới nhất (preset)
  2. C:/ProgramData/vMix/settingbackups/current.config

Chạy:  python test_vmix_external.py [--watch [GIÂY]]
────────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import glob
import html
import re
import argparse
import ctypes
import xml.etree.ElementTree as ET
from datetime import datetime
from ctypes import wintypes

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── màu ANSI ─────────────────────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty() or os.environ.get("TERM") not in (None, "")
_R = "\033[91m" if _USE_COLOR else ""
_G = "\033[92m" if _USE_COLOR else ""
_Y = "\033[93m" if _USE_COLOR else ""
_C = "\033[96m" if _USE_COzLOR else ""
_B = "\033[1m"  if _USE_COLOR else ""
_X = "\033[0m"  if _USE_COLOR else ""

SEP = f"{_C}{'─' * 72}{_X}"

EXT_NAMES = (
    "OutputsExternal",
    "OutputsExternal2",
    "OutputsExternal3",
    "OutputsExternal4",
)

# ── helpers hiển thị ──────────────────────────────────────────────────────────

def _ok(label: str, value: str):
    print(f"    {_G}✔{_X}  {_B}{label:<30}{_X}  {value}")

def _warn(label: str, value: str):
    print(f"    {_Y}⚠{_X}  {_B}{label:<30}{_X}  {value}")

def _err(label: str, value: str):
    print(f"    {_R}✘{_X}  {_B}{label:<30}{_X}  {value}")

def _checkbox(val: str) -> str:
    """'True'/'1' → ☑  else → ☐"""
    return f"{_G}☑  Yes{_X}" if val.lower() in ("true", "1") else f"{_Y}☐  No{_X}"

def _enabled_str(val: str) -> str:
    return f"{_G}ENABLED{_X}" if val.lower() in ("true", "1") else f"{_Y}disabled{_X}"

# ── helpers đọc file ──────────────────────────────────────────────────────────

def _vmix_data_dir() -> str:
    base = (os.environ.get("PROGRAMDATA")
            or os.environ.get("ALLUSERSPROFILE")
            or r"C:\ProgramData")
    return os.path.join(base, "vMix")


def _read_file_shared(filepath: str) -> str:
    """Đọc file ngay cả khi bị vMix lock (dùng FILE_SHARE_ALL)."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    GENERIC_READ          = 0x80000000
    FILE_SHARE_ALL        = 0x07
    OPEN_EXISTING         = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE        = ctypes.c_void_p(-1).value

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
        buf  = ctypes.create_string_buffer(size)
        read = wintypes.DWORD(0)
        if not kernel32.ReadFile(handle, buf, size, ctypes.byref(read), None):
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.raw[: read.value].decode("utf-8", errors="replace")
    finally:
        kernel32.CloseHandle(handle)


def _fps_from_ticks(ticks_str: str) -> str:
    """100-ns ticks/frame → chuỗi fps thân thiện."""
    try:
        t = int(ticks_str)
        if t <= 0:
            return "?"
        fps = 10_000_000 / t
        std_fps = [
            (23.976, "23.976"), (24, "24"), (25, "25"),
            (29.97, "29.97"),   (30, "30"), (50, "50"),
            (59.94, "59.94"),   (60, "60"),
        ]
        std, lbl = min(std_fps, key=lambda item: abs(fps - item[0]))
        if abs(fps - std) < 0.1:
            return lbl
        return f"{fps:.4g}"
    except (ValueError, ZeroDivisionError):
        return "?"


def _bw_str(bps_str: str) -> str:
    try:
        bps = int(bps_str)
        if bps >= 1_000_000:
            return f"{bps // 1_000_000}Mbps"
        return f"{bps // 1_000}kbps"
    except ValueError:
        return "?"


def _find_vmix_preset() -> str | None:
    """Tìm file *.vmix từ process cmdline → APPDATA → Documents → Desktop."""
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
    return max(candidates, key=os.path.getmtime) if candidates else None

# ── Port number → human-readable string ──────────────────────────────────────
# (Decklink / generic mapping – hiển thị số nếu không nhận ra)
_PORT_MAP = {
    "0": "HDMI / Component",
    "1": "SDI",
    "2": "DVI",
    "3": "VGA",
    "4": "HDMI",
    "5": "Composite",
    "6": "S-Video",
    "7": "SDI",
}

def _port_str(raw: str) -> str:
    return _PORT_MAP.get(raw, f"Port {raw}") if raw else "(không có)"

# ── AudioChannel number → human-readable ─────────────────────────────────────
_AUDIO_CH_MAP = {
    "0": "Master",
    "1": "Headphones",
    "2": "Bus A",
    "3": "Bus B",
    "4": "Bus C",
    "5": "Bus D",
}

def _audio_ch_str(raw: str) -> str:
    return _AUDIO_CH_MAP.get(raw, f"Ch {raw}") if raw else "(không có)"

# ── parse một element OutputsExternal* ───────────────────────────────────────

def _parse_ext_elem(elem) -> dict:
    def _t(*names) -> str:
        for n in names:
            v = (elem.findtext(n) or "").strip()
            if v:
                return v
        return ""

    d: dict = {}

    # ── Checkboxes (tên field thực tế từ XML) ────────────────────────────────
    d["Virtual"]            = _t("Virtual")           # vMix Video / Streaming
    d["ExternalEnabled"]    = _t("External")           # External hardware enabled
    d["ExternalRenderer"]   = _t("ExternalRenderer")
    d["VirtualUseStreaming"] = _t("VirtualUseStreaming")  # Use Streaming Settings
    d["ExternalUseDisplay"]  = _t("ExternalUseDisplay")   # Use Display Settings

    # ── Frame rate (ticks) ───────────────────────────────────────────────────
    ticks = _t("ExternalFrameRate", "VirtualFrameRate")
    d["FrameRate"] = _fps_from_ticks(ticks) if ticks else ""
    d["FrameRateInterlaced"] = _t("ExternalFrameRateInterlaced", "VirtualFrameRateInterlaced")

    # ── Output size ──────────────────────────────────────────────────────────
    d["ExternalSize"] = _t("ExternalSize")   # hardware output e.g. "1920x1080"
    d["VirtualSize"]  = _t("VirtualSize")    # streaming/virtual output

    # ── Device & port ────────────────────────────────────────────────────────
    d["Device"]      = _t("ExternalDevice")
    d["PortRaw"]     = _t("ExternalPort")
    d["Port"]        = _port_str(_t("ExternalPort"))
    d["AudioDevice"] = _t("ExternalAudioDevice")

    # ── Audio / Alpha ────────────────────────────────────────────────────────
    d["AudioChannel"]  = _audio_ch_str(_t("ExternalAudioChannel"))
    d["AlphaChannel"]  = _t("ExternalAlphaChannel")
    d["AudioDelay"]    = _t("ExternalAudioDelay")

    # ── SRT (status only) ────────────────────────────────────────────────────
    d["SRTEnabled"]  = _t("SRTEnabled")
    d["SRTPort"]     = _t("SRTPort")
    codec_id         = _t("SRTVideoCodec")
    d["SRTCodec"]    = ("HEVC" if codec_id == "1" else "H264") if codec_id else "H264"
    vbw = _t("SRTVideoBandwidth")
    abw = _t("SRTAudioBandwidth")
    d["SRTVideoBW"]  = _bw_str(vbw) if vbw else ""
    d["SRTAudioBW"]  = _bw_str(abw) if abw else ""
    d["SRTHardware"] = _t("SRTHardwareEncoder")
    d["SRTLatency"]  = _t("SRTLatencyMS", "SRTLatency")
    d["SRTPassphrase"] = _t("SRTPassPhrase", "SRTPassphrase")

    return d


def _print_ext_block(d: dict, label: str, idx: int):
    """In một External Output block theo dạng UI vMix."""
    ext_on    = d.get("ExternalEnabled", "").lower() in ("true", "1")
    virtual   = d.get("Virtual", "").lower() in ("true", "1")
    color     = _G if ext_on or virtual else _Y

    print()
    print(f"  {_B}{color}┌─ {label}  (External {idx})")
    print(f"  {_C}│{_X}     {'External hardware':<30}  {_enabled_str(d.get('ExternalEnabled','0'))}")
    print(f"  {_C}│{_X}     {'vMix Video/Streaming':<30}  {_enabled_str(d.get('Virtual','0'))}")

    # ── Checkboxes ────────────────────────────────────────────────────────────
    print(f"  {_C}│{_X}")
    print(f"  {_C}│{_X}  Checkboxes")
    for key, lbl in (
        ("Virtual",             "vMix Video / Streaming"),
        ("ExternalEnabled",     "External Renderer (SDI/HDMI)"),
        ("VirtualUseStreaming",  "Use Streaming Settings"),
        ("ExternalUseDisplay",   "Use Display Settings"),
    ):
        val = d.get(key, "")
        cb  = _checkbox(val) if val else f"{_Y}(không có dữ liệu){_X}"
        print(f"  {_C}│{_X}      {_B}{lbl:<30}{_X}  {cb}")

    # ── Output settings ───────────────────────────────────────────────────────
    print(f"  {_C}│{_X}")
    print(f"  {_C}│{_X}  Output  (External hardware)")

    fr   = d.get("FrameRate", "")
    interlaced = d.get("FrameRateInterlaced", "0")
    intl_str   = "  (Interlaced)" if interlaced == "1" else ""

    if fr:
        print(f"  {_C}│{_X}      {_B}{'Frame Rate':<30}{_X}  {_G}{fr}fps{intl_str}{_X}")
    else:
        print(f"  {_C}│{_X}      {_B}{'Frame Rate':<30}{_X}  {_Y}(không có){_X}")

    ext_size = d.get("ExternalSize", "")
    vir_size = d.get("VirtualSize", "")
    if ext_size:
        print(f"  {_C}│{_X}      {_B}{'Output Size (External)':<30}{_X}  {_G}{ext_size}{_X}")
    if vir_size:
        print(f"  {_C}│{_X}      {_B}{'Output Size (Virtual/Stream)':<30}{_X}  {vir_size}")

    for key, lbl in (
        ("Device",       "Device"),
        ("Port",         "Port"),
        ("AudioDevice",  "Audio Device"),
        ("AudioChannel", "Audio Channels"),
        ("AlphaChannel", "Alpha Channel"),
        ("AudioDelay",   "Audio Delay (ms)"),
    ):
        val = d.get(key, "")
        if val and val not in ("(không có)", "Ch ", "Port "):
            print(f"  {_C}│{_X}      {_B}{lbl:<30}{_X}  {val}")
        else:
            print(f"  {_C}│{_X}      {_B}{lbl:<30}{_X}  {_Y}(không có){_X}")

    # ── SRT ───────────────────────────────────────────────────────────────────
    print(f"  {_C}│{_X}")
    print(f"  {_C}│{_X}  SRT")
    srt_on = d.get("SRTEnabled", "0").strip() == "1"
    if srt_on:
        port  = d.get("SRTPort", "?")
        codec = d.get("SRTCodec", "H264")
        vbw   = d.get("SRTVideoBW", "?")
        abw   = d.get("SRTAudioBW", "?")
        lat   = d.get("SRTLatency", "")
        hw    = d.get("SRTHardware", "0") == "1"
        pp    = d.get("SRTPassphrase", "")
        print(f"  {_C}│{_X}      {_B}{'Enabled':<30}{_X}  {_G}☑  Yes{_X}")
        print(f"  {_C}│{_X}      {_B}{'Port':<30}{_X}  {port}")
        print(f"  {_C}│{_X}      {_B}{'Codec':<30}{_X}  {codec}")
        print(f"  {_C}│{_X}      {_B}{'Video Bandwidth':<30}{_X}  {vbw}")
        print(f"  {_C}│{_X}      {_B}{'Audio Bandwidth':<30}{_X}  {abw}")
        if lat:
            print(f"  {_C}│{_X}      {_B}{'Latency':<30}{_X}  {lat}ms")
        if hw:
            print(f"  {_C}│{_X}      {_B}{'Hardware Encoder':<30}{_X}  Yes")
        if pp:
            print(f"  {_C}│{_X}      {_B}{'Passphrase':<30}{_X}  (đặt)")
    else:
        print(f"  {_C}│{_X}      {_B}{'Enabled':<30}{_X}  {_Y}☐  No{_X}")

    print(f"  {_C}└{'─' * 68}{_X}")


# ── load từ preset XML ────────────────────────────────────────────────────────

def _load_from_preset(preset_path: str) -> list[tuple[str, dict]]:
    root = ET.parse(preset_path).getroot()
    results = []
    for idx, name in enumerate(EXT_NAMES, start=1):
        elem = root.find(f".//{name}")
        if elem is None:
            continue
        results.append((name, _parse_ext_elem(elem)))
    return results


def _load_from_config(config_path: str) -> list[tuple[str, dict]]:
    content = _read_file_shared(config_path)
    results = []
    for idx, name in enumerate(EXT_NAMES, start=1):
        m = re.search(
            rf'name="{re.escape(name)}"[^>]*>\s*<value>(.*?)</value>',
            content, re.DOTALL,
        )
        if not m:
            continue
        decoded = html.unescape(m.group(1).strip())
        try:
            sub = ET.fromstring(f"<root>{decoded}</root>")
        except ET.ParseError:
            continue
        results.append((name, _parse_ext_elem(sub)))
    return results


# ── main display ──────────────────────────────────────────────────────────────

def run():
    print(f"\n{SEP}")
    print(f"{_B}{_C}  vMix External Output Settings{_X}")
    print(f"  {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    print(SEP)

    # ── tìm nguồn dữ liệu ────────────────────────────────────────────────────
    items  = []
    source = ""

    preset = _find_vmix_preset()
    if preset:
        try:
            items  = _load_from_preset(preset)
            mtime  = datetime.fromtimestamp(os.path.getmtime(preset)).strftime("%Y-%m-%d %H:%M:%S")
            source = f"Preset: {os.path.basename(preset)}  [{mtime}]"
        except Exception as ex:
            print(f"  {_Y}⚠  Đọc preset lỗi: {ex} – thử current.config{_X}")

    if not items:
        cfg = os.path.join(_vmix_data_dir(), "settingbackups", "current.config")
        if os.path.isfile(cfg):
            try:
                items  = _load_from_config(cfg)
                source = f"Config: {cfg}"
            except Exception as ex:
                print(f"  {_R}✘  Đọc current.config lỗi: {ex}{_X}")
        else:
            print(f"  {_R}✘  Không tìm thấy preset *.vmix hay current.config{_X}\n")
            return

    if not items:
        print(f"  {_Y}⚠  Không tìm thấy khối OutputsExternal* trong file{_X}\n")
        return

    print(f"  {_G}✔{_X}  {_B}Nguồn:{_X}  {source}\n")

    for idx, (name, d) in enumerate(items, start=1):
        _print_ext_block(d, name, idx)

    print()


def scan_all_files():
    """Quét tất cả file trong vMix ProgramData + preset để tìm External Output fields."""
    print(f"\n{SEP}")
    print(f"{_B}{_C}  SCAN – Tìm External Output trong tất cả file vMix{_X}")
    print(SEP)

    vmix_dir = _vmix_data_dir()
    keywords = re.compile(r"external|outputsize|framerate|devicename|outputport|audiochannel|alphachannel|audiodelay", re.I)

    # Tập hợp các file cần scan
    scan_files: list[str] = []

    # 1. Tất cả file trong ProgramData\vMix (*.config, *.xml, *.txt, *.vmix)
    for ext in ("*.config", "*.xml", "*.txt", "*.vmix", "*.settings"):
        scan_files.extend(glob.glob(os.path.join(vmix_dir, "**", ext), recursive=True))

    # 2. Preset *.vmix
    preset = _find_vmix_preset()
    if preset and preset not in scan_files:
        scan_files.append(preset)

    # 3. AppData\Roaming\vMix
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        for ext in ("*.config", "*.xml", "*.vmix", "*.settings"):
            scan_files.extend(glob.glob(os.path.join(appdata, "vMix", "**", ext), recursive=True))

    scan_files = list(dict.fromkeys(scan_files))  # dedupe, preserve order
    print(f"  Thư mục vMix ProgramData  : {vmix_dir}")
    print(f"  Số file sẽ scan           : {len(scan_files)}\n")

    for fpath in scan_files:
        try:
            # đọc raw text
            if fpath.lower().endswith(".vmix") or not os.path.isfile(fpath):
                try:
                    raw = _read_file_shared(fpath)
                except Exception:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        raw = f.read()
            else:
                raw = _read_file_shared(fpath)

            hits = []
            for i, line in enumerate(raw.splitlines(), 1):
                if keywords.search(line):
                    hits.append((i, line.strip()))

            if hits:
                relpath = os.path.relpath(fpath, vmix_dir) if fpath.startswith(vmix_dir) else fpath
                print(f"  {_G}✔{_X}  {_B}{relpath}{_X}  ({len(hits)} dòng khớp)")
                for lineno, text in hits[:30]:  # max 30 dòng/file
                    # highlight keyword
                    print(f"      L{lineno:<5} {text[:120]}")
                if len(hits) > 30:
                    print(f"      ... ({len(hits) - 30} dòng nữa bị ẩn)")
                print()
        except Exception as ex:
            print(f"  {_Y}⚠  {os.path.basename(fpath)} – {ex}{_X}")

    print()


def dump_raw():
    """In toàn bộ tag/value thô của mỗi OutputsExternal* để debug field names."""
    print(f"\n{SEP}")
    print(f"{_B}{_C}  RAW XML DUMP – OutputsExternal*{_X}")
    print(SEP)

    root = None
    source = ""

    preset = _find_vmix_preset()
    if preset:
        try:
            root = ET.parse(preset).getroot()
            source = f"Preset: {os.path.basename(preset)}"
        except Exception as ex:
            print(f"  {_Y}⚠  {ex}{_X}")

    if root is None:
        cfg = os.path.join(_vmix_data_dir(), "settingbackups", "current.config")
        if os.path.isfile(cfg):
            # parse từng block bằng regex rồi in như XML
            try:
                content = _read_file_shared(cfg)
                source  = "current.config"
                for name in EXT_NAMES:
                    m = re.search(
                        rf'name="{re.escape(name)}"[^>]*>\s*<value>(.*?)</value>',
                        content, re.DOTALL,
                    )
                    if not m:
                        print(f"\n  {_Y}[{name}] không tìm thấy{_X}")
                        continue
                    decoded = html.unescape(m.group(1).strip())
                    print(f"\n  {_B}{_C}── {name}{_X}")
                    try:
                        sub = ET.fromstring(f"<root>{decoded}</root>")
                        for child in sub:
                            print(f"    {_B}{child.tag:<40}{_X}  {repr(child.text or '')}")
                    except ET.ParseError as pe:
                        print(f"  {_R}ParseError: {pe}{_X}")
                        print(decoded[:500])
                print(f"\n  {_G}Nguồn:{_X}  {source}\n")
                return
            except Exception as ex:
                print(f"  {_R}✘  {ex}{_X}")
        print(f"  {_R}✘  Không tìm thấy dữ liệu{_X}\n")
        return

    print(f"  {_G}Nguồn:{_X}  {source}\n")
    for name in EXT_NAMES:
        elem = root.find(f".//{name}")
        if elem is None:
            print(f"\n  {_Y}[{name}] không tìm thấy trong preset{_X}")
            continue
        print(f"\n  {_B}{_C}── {name}{_X}")
        for child in elem:
            print(f"    {_B}{child.tag:<40}{_X}  {repr(child.text or '')}")
        # cũng in attributes của element nếu có
        if elem.attrib:
            for k, v in elem.attrib.items():
                print(f"    {_Y}@{k:<39}{_X}  {repr(v)}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Hiển thị thông số vMix External Output (hardware settings)."
    )
    parser.add_argument(
        "--watch", type=int, metavar="GIÂY", nargs="?", const=3,
        help="Tự động refresh mỗi N giây (mặc định 3s). Ctrl+C để thoát.",
    )
    parser.add_argument(
        "--dump", action="store_true",
        help="In raw XML fields của OutputsExternal* để debug field names.",
    )
    parser.add_argument(
        "--scan", action="store_true",
        help="Quét tất cả file vMix để tìm nơi lưu External Output settings.",
    )
    args = parser.parse_args()

    if args.scan:
        scan_all_files()
        return

    if args.dump:
        dump_raw()
        return

    if args.watch is None:
        run()
    else:
        import time
        interval = max(1, args.watch)
        try:
            while True:
                os.system("cls" if os.name == "nt" else "clear")
                run()
                print(f"  {_Y}Refresh sau {interval}s ...  Ctrl+C = thoát{_X}\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n{_Y}Đã thoát.{_X}\n")


if __name__ == "__main__":
    main()
