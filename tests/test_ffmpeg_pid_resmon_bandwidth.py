"""
test_ffmpeg_pid_resmon_bandwidth.py
-----------------------------------
Standalone test: find ffmpeg PID(s) and read per-process bandwidth similar to
Windows Resource Monitor.

Also attempts to map each ffmpeg process to a vMix stream slot
(streaming1/streaming2/...) using vMix stream config + ffmpeg cmdline +
remote endpoint matches.

Data source:
- Win32_PerfFormattedData_PerfProc_Process (via PowerShell/Get-CimInstance)
- Send (B/sec)    ~= IOWriteBytesPersec
- Receive (B/sec) ~= IOReadBytesPersec
- Total (B/sec)   = Receive + Send

Usage:
  python tests/test_ffmpeg_pid_resmon_bandwidth.py
  python tests/test_ffmpeg_pid_resmon_bandwidth.py --watch --interval 1.5
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


@dataclass
class FfmpegProcess:
    pid: int
    name: str
    exe: str
    cmdline: str
    remote_ips: Set[str]
    remote_ports: Set[int]


@dataclass
class PerfProcSample:
    pid: int
    instance_name: str
    recv_bps: float
    send_bps: float
    total_bps: float
    io_other_bps: float


@dataclass
class StreamEndpoint:
    stream_name: str
    kind: str
    host: str
    port: str
    path: str
    enabled: bool
    host_ips: Set[str]


def _format_mbps(value_bytes_per_sec: float) -> str:
    return f"{(value_bytes_per_sec * 8) / 1_000_000:.3f} Mbps"


def _run_powershell_json(command: str) -> Optional[object]:
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        return None
    except Exception:
        return None

    if proc.returncode != 0:
        return None

    output = (proc.stdout or "").strip()
    if not output:
        return None

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def _get_perfproc_samples() -> Dict[int, PerfProcSample]:
    ps_script = r"""
Get-CimInstance Win32_PerfFormattedData_PerfProc_Process |
  Where-Object { $_.IDProcess -gt 0 -and $_.Name -ne '_Total' -and $_.Name -ne 'Idle' } |
    Select-Object Name,IDProcess,IOReadBytesPersec,IOWriteBytesPersec,IOOtherBytesPersec |
  ConvertTo-Json -Compress
"""
    raw = _run_powershell_json(ps_script)
    if raw is None:
        return {}

    rows = raw if isinstance(raw, list) else [raw]
    results: Dict[int, PerfProcSample] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        try:
            pid = int(item.get("IDProcess", 0) or 0)
        except Exception:
            pid = 0
        if pid <= 0:
            continue

        name = str(item.get("Name", "") or "")

        try:
            recv_bps = float(item.get("IOReadBytesPersec", 0) or 0)
        except Exception:
            recv_bps = 0.0

        try:
            send_bps = float(item.get("IOWriteBytesPersec", 0) or 0)
        except Exception:
            send_bps = 0.0

        try:
            io_other = float(item.get("IOOtherBytesPersec", 0) or 0)
        except Exception:
            io_other = 0.0

        recv_bps = max(recv_bps, 0.0)
        send_bps = max(send_bps, 0.0)
        total_bps = recv_bps + send_bps

        results[pid] = PerfProcSample(
            pid=pid,
            instance_name=name,
            recv_bps=recv_bps,
            send_bps=send_bps,
            total_bps=total_bps,
            io_other_bps=max(io_other, 0.0),
        )
    return results


def _stream_sort_key(stream_name: str) -> Tuple[int, str]:
    m = re.match(r"streaming(\d+)$", stream_name.lower())
    if not m:
        return (9999, stream_name)
    return (int(m.group(1)), stream_name)


def _normalize_stream_setting_name(raw_name: str) -> str:
    name = (raw_name or "").strip().lower()
    if name == "streaming":
        return "streaming1"
    m = re.match(r"streaming(\d+)$", name)
    if m:
        return f"streaming{m.group(1)}"
    return name or "streaming?"


def _resolve_host_ips(host: str) -> Set[str]:
    host = (host or "").strip()
    if not host:
        return set()

    results: Set[str] = set()
    try:
        socket.inet_aton(host)
        results.add(host)
    except OSError:
        pass

    try:
        info = socket.getaddrinfo(host, None)
    except OSError:
        return results

    for entry in info:
        addr = entry[4]
        if not addr:
            continue
        ip = str(addr[0]).strip()
        if ip:
            results.add(ip)
    return results


def _parse_stream_endpoint(setting_name: str, raw_xml: str) -> Optional[StreamEndpoint]:
    try:
        inner = html.unescape((raw_xml or "").strip())
        root = ET.fromstring(inner)
    except Exception:
        return None

    def _t(tag: str, default: str = "") -> str:
        return (root.findtext(tag) or default).strip()

    stream_name = _normalize_stream_setting_name(setting_name)
    enabled = _t("Enabled", "0").lower() in {"1", "true"}

    has_srt = (
        root.find("SRTEnabled") is not None
        or root.find("SRTHost") is not None
        or root.find("SRTPort") is not None
    )

    if has_srt:
        host = _t("SRTHost")
        port = _t("SRTPort")
        path = ""
        kind = "SRT"
    else:
        url_or_server = _t("Url") or _t("Server")
        path = (_t("StreamName") or _t("Key")).lstrip("/")
        host = ""
        port = ""

        if url_or_server:
            parsed = urllib.parse.urlparse(
                url_or_server if "://" in url_or_server else f"rtmp://{url_or_server}"
            )
            host = (parsed.hostname or "").strip()
            port = str(parsed.port) if parsed.port else ""
            parsed_path = (parsed.path or "").strip().lstrip("/")
            if parsed_path and not path:
                path = parsed_path

            if not host:
                m = re.match(r"^([^/:]+)(?::(\d+))?", url_or_server.strip())
                if m:
                    host = (m.group(1) or "").strip()
                    if not port:
                        port = (m.group(2) or "").strip()

        kind = "RTMP/HTTP"

    return StreamEndpoint(
        stream_name=stream_name,
        kind=kind,
        host=host,
        port=port,
        path=path,
        enabled=enabled,
        host_ips=_resolve_host_ips(host),
    )


def _load_vmix_stream_endpoints() -> Dict[str, StreamEndpoint]:
    base = (
        os.environ.get("PROGRAMDATA")
        or os.environ.get("ALLUSERSPROFILE")
        or r"C:\ProgramData"
    )
    vmix_dir = os.path.join(base, "vMix")
    candidates = [
        os.path.join(vmix_dir, "settingbackups", "current.config"),
        os.path.join(vmix_dir, "current.config"),
    ]

    settings_pattern = re.compile(
        r'name="(Streaming\d*)"[^>]*>\s*<value>(.*?)</value>',
        re.IGNORECASE | re.DOTALL,
    )

    results: Dict[str, StreamEndpoint] = {}
    for path in candidates:
        if not os.path.isfile(path):
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
        except Exception:
            continue

        for m in settings_pattern.finditer(raw):
            endpoint = _parse_stream_endpoint(m.group(1), m.group(2))
            if endpoint is None:
                continue
            if endpoint.stream_name not in results:
                results[endpoint.stream_name] = endpoint

    return results


def _is_ffmpeg_name(image_name: str) -> bool:
    normalized = image_name.lower().strip()
    if not normalized:
        return False
    if normalized in {"ffmpeg", "ffmpeg.exe"}:
        return True
    return normalized.startswith("ffmpeg") and normalized.endswith(".exe")


def _extract_remote_endpoints(proc: Any) -> Tuple[Set[str], Set[int]]:
    remote_ips: Set[str] = set()
    remote_ports: Set[int] = set()

    try:
        conns = proc.net_connections(kind="inet")
    except Exception:
        return remote_ips, remote_ports

    for conn in conns:
        raddr = conn.raddr
        if not raddr:
            continue

        ip = ""
        port = 0
        try:
            ip = str(getattr(raddr, "ip", "") or "").strip()
            port = int(getattr(raddr, "port", 0) or 0)
        except Exception:
            ip = ""
            port = 0

        if (not ip or port <= 0) and isinstance(raddr, tuple) and len(raddr) >= 2:
            ip = str(raddr[0]).strip()
            try:
                port = int(raddr[1])
            except Exception:
                port = 0

        if ip:
            remote_ips.add(ip)
        if port > 0:
            remote_ports.add(port)

    return remote_ips, remote_ports


def _find_ffmpeg_processes() -> List[FfmpegProcess]:
    if psutil is None:
        return []

    out: List[FfmpegProcess] = []
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            pid = int(proc.info.get("pid") or 0)
            pname = str(proc.info.get("name") or "")
            pexe = str(proc.info.get("exe") or "")
            cmdline_parts = proc.info.get("cmdline") or []
            cmdline = " ".join(str(x) for x in cmdline_parts if x).strip()

            image_name = pname.lower().strip()
            exe_name = os.path.basename(pexe).lower().strip() if pexe else ""
            if not _is_ffmpeg_name(image_name) and not _is_ffmpeg_name(exe_name):
                continue

            remote_ips, remote_ports = _extract_remote_endpoints(proc)

            out.append(
                FfmpegProcess(
                    pid=pid,
                    name=pname or "(unknown)",
                    exe=pexe,
                    cmdline=cmdline,
                    remote_ips=remote_ips,
                    remote_ports=remote_ports,
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    out.sort(key=lambda x: x.pid)
    return out


def _clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _score_stream_match(proc: FfmpegProcess, stream: StreamEndpoint) -> Tuple[int, List[str]]:
    cmd = proc.cmdline.lower()
    score = 0
    reasons: List[str] = []

    if stream.host:
        host = stream.host.lower()
        if host and host in cmd:
            score += 40
            reasons.append("host-in-cmd")
        if proc.remote_ips and stream.host_ips:
            overlap = sorted(proc.remote_ips.intersection(stream.host_ips))
            if overlap:
                score += 45
                reasons.append(f"ip-match={overlap[0]}")

    if stream.port:
        try:
            port_num = int(stream.port)
        except ValueError:
            port_num = 0

        if port_num > 0 and port_num in proc.remote_ports:
            score += 40
            reasons.append("remote-port-match")

        if re.search(rf"[:/]({re.escape(stream.port)})(?:\b|/)", cmd):
            score += 30
            reasons.append("port-in-cmd")

    if stream.path:
        path = stream.path.lower().lstrip("/")
        if path and path in cmd:
            score += 25
            reasons.append("path-in-cmd")

    if stream.kind == "SRT" and "srt://" in cmd:
        score += 5
    if stream.kind == "RTMP/HTTP" and (
        "rtmp://" in cmd or "http://" in cmd or "https://" in cmd
    ):
        score += 5

    if not stream.enabled:
        score -= 20
        reasons.append("stream-disabled")

    return score, reasons


def _guess_stream_for_ffmpeg(
    proc: FfmpegProcess,
    stream_endpoints: Dict[str, StreamEndpoint],
) -> Tuple[str, int, str]:
    if not stream_endpoints:
        return "(unknown)", 0, "no-vmix-stream-config"

    best_stream = ""
    best_score = -999
    best_reasons: List[str] = []

    for stream_name, endpoint in stream_endpoints.items():
        score, reasons = _score_stream_match(proc, endpoint)
        if score > best_score:
            best_stream = stream_name
            best_score = score
            best_reasons = reasons

    if best_score < 25:
        return "(unknown)", best_score, ",".join(best_reasons) if best_reasons else "weak-match"

    if best_score >= 75:
        conf = "high"
    elif best_score >= 45:
        conf = "medium"
    else:
        conf = "low"

    reason_text = ",".join(best_reasons) if best_reasons else "heuristic"
    return f"{best_stream} [{conf}]", best_score, reason_text


def _format_stream_endpoint(stream: StreamEndpoint) -> str:
    if stream.kind == "SRT":
        endpoint = f"{stream.host}:{stream.port}" if stream.host or stream.port else "(missing endpoint)"
    else:
        base = stream.host
        if stream.port:
            base = f"{base}:{stream.port}" if base else f":{stream.port}"
        if stream.path:
            endpoint = f"{base}/{stream.path}" if base else f"/{stream.path}"
        else:
            endpoint = base or "(missing endpoint)"
    status = "ON" if stream.enabled else "OFF"
    return f"{stream.kind} {status} {endpoint}"


def _print_once() -> int:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    print(now)
    print("=" * 136)
    print("ffmpeg PID + bandwidth test (Resmon-like + vmix stream mapping)")
    print("Counters: IOWriteBytesPersec (Send), IOReadBytesPersec (Receive), Total = Send + Receive")
    print("Name match: ffmpeg, ffmpeg.exe, or ffmpeg*.exe")
    print("-" * 136)

    ffmpeg_procs = _find_ffmpeg_processes()
    if not ffmpeg_procs:
        print("No process matched ffmpeg image pattern (ffmpeg / ffmpeg.exe / ffmpeg*.exe)")
        print("Tip: ensure ffmpeg is running, then retry with --watch.")
        return 1

    perf_by_pid = _get_perfproc_samples()
    if not perf_by_pid:
        print("Could not read Windows perf counters. Try running terminal as Administrator.")
        return 2

    stream_endpoints = _load_vmix_stream_endpoints()
    if stream_endpoints:
        print(f"Detected vMix stream slots: {len(stream_endpoints)}")
        for stream_name in sorted(stream_endpoints.keys(), key=_stream_sort_key):
            print(f"  - {stream_name:<10} {_format_stream_endpoint(stream_endpoints[stream_name])}")
    else:
        print("Detected vMix stream slots: 0 (current.config not found or no Streaming* blocks)")

    print()

    print(f"Matched process count: {len(ffmpeg_procs)}")
    print()
    print(
        f"{'PID':>8}  {'Process':<20}  {'Stream Guess':<26}  {'Send(B/s)':>10}  {'Receive(B/s)':>12}  "
        f"{'Total(B/s)':>10}  {'Total(Mbps)':>12}"
    )
    print("-" * 136)

    total_recv = 0.0
    total_send = 0.0
    total_bps = 0.0
    for proc in ffmpeg_procs:
        sample = perf_by_pid.get(proc.pid)
        recv_bps = sample.recv_bps if sample else 0.0
        send_bps = sample.send_bps if sample else 0.0
        bps = sample.total_bps if sample else 0.0
        total_recv += recv_bps
        total_send += send_bps
        total_bps += bps

        stream_guess, score, reason = _guess_stream_for_ffmpeg(proc, stream_endpoints)

        print(
            f"{proc.pid:>8}  "
            f"{proc.name[:20]:<20}  "
            f"{stream_guess[:26]:<26}  "
            f"{send_bps:>10.0f}  "
            f"{recv_bps:>12.0f}  "
            f"{bps:>10.0f}  "
            f"{_format_mbps(bps):>12}"
        )

        if stream_guess != "(unknown)":
            print(f"{'':>8}  {'':<20}  reason={reason} score={score}")

    print("-" * 136)
    print(
        f"{'TOTAL':>8}  {'(all matched ffmpeg)':<20}  {'':<26}  "
        f"{total_send:>10.0f}  {total_recv:>12.0f}  {total_bps:>10.0f}  {_format_mbps(total_bps):>12}"
    )
    print("Hint: stream guess is heuristic (cmdline + remote endpoint + vmix config), not 100% guaranteed.")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test ffmpeg PID and per-process bandwidth from Windows Resmon-like counters"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch continuously",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.5,
        help="Watch refresh interval in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear screen when watch mode is enabled",
    )
    return parser.parse_args()


def main() -> None:
    if os.name != "nt":
        print("This script is intended for Windows only.")
        sys.exit(2)

    args = _parse_args()
    interval = max(float(args.interval), 0.5)

    if not args.watch:
        code = _print_once()
        sys.exit(code)

    while True:
        try:
            if not args.no_clear:
                _clear_screen()
            _print_once()
            print("\nPress Ctrl+C to stop.")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped by user.")
            return


if __name__ == "__main__":
    main()
