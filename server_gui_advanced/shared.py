from datetime import datetime

import pytz

VIETNAM_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
DEFAULT_SERVER_URL = "http://192.168.30.119:8000"


def get_first_srt(d: dict) -> dict:
    """Safely extract the first SRT dict from data.
    Handles both old dict format and new array format."""
    srt_raw = d.get("SRT", {})
    if isinstance(srt_raw, dict):
        return srt_raw
    if isinstance(srt_raw, list):
        for item in srt_raw:
            if isinstance(item, dict):
                return item
    return {}


def get_srt_ports_str(d: dict) -> str:
    """Get a display string of all SRT ports from data."""
    srt_raw = d.get("SRT", [])
    if isinstance(srt_raw, dict):
        return str(srt_raw.get("port", ""))
    if isinstance(srt_raw, list):
        ports = []
        for item in srt_raw:
            if isinstance(item, dict) and item.get("port"):
                ports.append(str(item["port"]))
        return ", ".join(ports)
    return ""


def get_srt_quality_str(d: dict) -> str:
    """Get a display string of SRT quality info from all SRT streams."""
    srt_raw = d.get("SRT", [])
    if isinstance(srt_raw, dict):
        return srt_raw.get("quality", "") or "—"
    if isinstance(srt_raw, list):
        qualities = []
        for item in srt_raw:
            if isinstance(item, dict):
                q = item.get("quality", "")
                name = item.get("nameSRT", "")
                port = item.get("port", "")
                status = item.get("status", "")
                label = name or str(port)
                if label:
                    qualities.append(f"{label}:{status}" + (f"({q})" if q else ""))
        return " | ".join(qualities) if qualities else "—"
    return "—"


def pretty_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is not None:
            dt = dt.astimezone(VIETNAM_TZ)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return ts
