"""
Health failover tester between primary LAN server and Render backup.

Priority rule:
1. Primary: http://192.168.30.216:8000
2. Backup:  https://tooldiscordvmix.onrender.com

Behavior:
- Always prefer PRIMARY when /health is OK.
- If PRIMARY is down, switch to BACKUP.
- If PRIMARY comes back, switch back automatically.

Usage:
    python tests/test_server_onrender.py
    python tests/test_server_onrender.py --watch
    python tests/test_server_onrender.py --interval 5
"""

from __future__ import annotations

import argparse
import time
from typing import Any

import requests

PRIMARY_BASE_URL = "http://192.168.30.216:8000"
BACKUP_BASE_URL = "https://tooldiscordvmix.onrender.com"


def _normalize_base_url(raw: str) -> str:
    url = str(raw or "").strip().rstrip("/")
    if not url:
        url = BACKUP_BASE_URL
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url.rstrip("/")


def _print_result(name: str, ok: bool, details: str) -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {details}")


def _safe_json(response: requests.Response) -> tuple[bool, Any]:
    try:
        return True, response.json()
    except ValueError:
        return False, None


def check_health(session: requests.Session, base_url: str, timeout: float) -> tuple[bool, str]:
    url = f"{base_url}/health"
    started = time.perf_counter()
    try:
        response = session.get(url, timeout=timeout)
    except requests.RequestException as exc:
        return False, f"request error: {exc}"

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if response.status_code != 200:
        return False, f"HTTP {response.status_code} in {elapsed_ms:.0f}ms"

    is_json, payload = _safe_json(response)
    if not is_json or not isinstance(payload, dict):
        return False, f"HTTP 200 in {elapsed_ms:.0f}ms but invalid JSON"

    status = str(payload.get("status", "")).lower()
    if status not in ("ok", "healthy", "up"):
        return False, f"HTTP 200 in {elapsed_ms:.0f}ms but status={status or 'unknown'}"

    return True, f"HTTP 200 in {elapsed_ms:.0f}ms"


def choose_active_server(
    session: requests.Session,
    primary_url: str,
    backup_url: str,
    timeout: float,
) -> tuple[str | None, dict[str, str]]:
    notes: dict[str, str] = {}

    primary_ok, primary_note = check_health(session, primary_url, timeout)
    notes[primary_url] = primary_note
    if primary_ok:
        return primary_url, notes

    backup_ok, backup_note = check_health(session, backup_url, timeout)
    notes[backup_url] = backup_note
    if backup_ok:
        return backup_url, notes

    return None, notes


def main() -> int:
    parser = argparse.ArgumentParser(description="Health failover tester (primary -> backup -> primary)")
    parser.add_argument("--primary", default=PRIMARY_BASE_URL, help="Primary server base URL")
    parser.add_argument("--backup", default=BACKUP_BASE_URL, help="Backup server base URL")
    parser.add_argument("--timeout", type=float, default=3.0, help="Timeout seconds per health check")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously monitor and auto switch/failback",
    )
    parser.add_argument("--interval", type=float, default=3.0, help="Polling interval in watch mode")
    args = parser.parse_args()

    primary_url = _normalize_base_url(args.primary)
    backup_url = _normalize_base_url(args.backup)
    print(f"Primary: {primary_url}")
    print(f"Backup : {backup_url}")

    session = requests.Session()

    if not args.watch:
        active_url, _ = choose_active_server(session, primary_url, backup_url, args.timeout)
        if active_url is None:
            print("Current server: NONE")
            return 1

        print(f"Current server: {active_url}")
        return 0

    current_active = None
    print("Watch mode started. Press Ctrl+C to stop.")
    try:
        while True:
            active_url, _ = choose_active_server(session, primary_url, backup_url, args.timeout)
            now_text = time.strftime("%H:%M:%S")

            if active_url is None:
                print(f"[{now_text}] Current server: NONE")
            else:
                print(f"[{now_text}] Current server: {active_url}")
            current_active = active_url

            time.sleep(max(args.interval, 0.5))
    except KeyboardInterrupt:
        print("Stopped by user.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
