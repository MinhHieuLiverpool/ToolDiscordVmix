import json
import os
import pytz

VIETNAM_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

# ── Defaults (hardcoded fallback) ─────────────────────────────────────────
_DEFAULT_SERVER_URL = "https://tooldiscordvmix.onrender.com"

# ── Local JSON cache ─────────────────────────────────────────────────────
# Settings are cached to C:\VmixMonitor\Setting\vmix_gui_settings.json
# so they persist across restarts. The defaults above are used as fallback.
_SETTINGS_DIR = r"C:\VmixMonitor\Setting"
_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "vmix_gui_settings.json")


def _load_settings() -> dict:
    """Load cached settings from local JSON file."""
    try:
        if os.path.exists(_SETTINGS_FILE):
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"⚠ Warning: Failed to load settings from {_SETTINGS_FILE}: {e}")
    return {}


def _save_settings(data: dict):
    """Save settings to local JSON file."""
    try:
        os.makedirs(_SETTINGS_DIR, exist_ok=True)
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠ Warning: Failed to save settings to {_SETTINGS_FILE}: {e}")


def get_setting(key: str, default=None):
    """Get a single setting value from the cache, with fallback to default."""
    settings = _load_settings()
    return settings.get(key, default)


def set_setting(key: str, value):
    """Set a single setting value and persist to cache."""
    settings = _load_settings()
    settings[key] = value
    _save_settings(settings)


def get_all_settings() -> dict:
    """Get all cached settings."""
    return _load_settings()


def save_all_settings(data: dict):
    """Overwrite all settings."""
    _save_settings(data)


# ── Exported SERVER_URL ──────────────────────────────────────────────────
# Read from cache first, fallback to hardcoded default.
SERVER_URL = get_setting("server_url", _DEFAULT_SERVER_URL)
