"""
test_vmix_pid_resmon_bandwidth.py
---------------------------------
Standalone test: find vMix PID(s) and read per-process bandwidth similar to
Windows Resource Monitor.

Data source:
- Win32_PerfFormattedData_PerfProc_Process (via PowerShell/Get-CimInstance)
- Send (B/sec)    ~= IOWriteBytesPersec
- Receive (B/sec) ~= IOReadBytesPersec
- Total (B/sec)   = Receive + Send

Usage:
  python tests/test_vmix_pid_resmon_bandwidth.py
  python tests/test_vmix_pid_resmon_bandwidth.py --watch --interval 1.5
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


@dataclass
class VmixProcess:
    pid: int
    name: str
    exe: str


@dataclass
class PerfProcSample:
    pid: int
    instance_name: str
    recv_bps: float
    send_bps: float
    total_bps: float
    io_other_bps: float


def _format_bytes_per_sec(value: float) -> str:
    if value < 1024:
        return f"{value:.0f} B/s"
    if value < 1024**2:
        return f"{value / 1024:.2f} KB/s"
    if value < 1024**3:
        return f"{value / (1024**2):.2f} MB/s"
    return f"{value / (1024**3):.2f} GB/s"


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
        # Map counters to Resource Monitor-like columns per PID.
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


def _find_vmix_processes() -> List[VmixProcess]:
    if psutil is None:
        return []

    target = "vmix64.exe"

    out: List[VmixProcess] = []
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            pid = int(proc.info.get("pid") or 0)
            pname = str(proc.info.get("name") or "")
            pexe = str(proc.info.get("exe") or "")

            image_name = pname.lower().strip()
            exe_name = os.path.basename(pexe).lower().strip() if pexe else ""
            if image_name != target and exe_name != target:
                continue

            out.append(VmixProcess(pid=pid, name=pname or "(unknown)", exe=pexe))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    out.sort(key=lambda x: x.pid)
    return out


def _clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _print_once() -> int:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    print(now)
    print("=" * 96)
    print("vMix PID + bandwidth test (Resmon-like)")
    print("Counters: IOWriteBytesPersec (Send), IOReadBytesPersec (Receive), Total = Send + Receive")
    print("Note    : This follows Resmon column layout by PID and is usually very close.")
    print("-" * 96)

    vmix_procs = _find_vmix_processes()
    if not vmix_procs:
        print("No process matched exact image: 'vmix64.exe'")
        print("Tip: ensure vMix is running as vMix64.exe, then retry with --watch.")
        return 1

    perf_by_pid = _get_perfproc_samples()
    if not perf_by_pid:
        print("Could not read Windows perf counters. Try running terminal as Administrator.")
        return 2

    print(f"Matched process count: {len(vmix_procs)}")
    print()
    print(
        f"{'PID':>8}  {'Process':<20}  {'Send(B/s)':>10}  {'Receive(B/s)':>12}  "
        f"{'Total(B/s)':>10}  {'Total(Mbps)':>12}"
    )
    print("-" * 96)

    total_recv = 0.0
    total_send = 0.0
    total_bps = 0.0
    for proc in vmix_procs:
        sample = perf_by_pid.get(proc.pid)
        recv_bps = sample.recv_bps if sample else 0.0
        send_bps = sample.send_bps if sample else 0.0
        bps = sample.total_bps if sample else 0.0
        total_recv += recv_bps
        total_send += send_bps
        total_bps += bps

        print(
            f"{proc.pid:>8}  "
            f"{proc.name[:20]:<20}  "
            f"{send_bps:>10.0f}  "
            f"{recv_bps:>12.0f}  "
            f"{bps:>10.0f}  "
            f"{_format_mbps(bps):>12}"
        )

    print("-" * 96)
    print(
        f"{'TOTAL':>8}  {'(all matched vmix)':<20}  "
        f"{total_send:>10.0f}  {total_recv:>12.0f}  {total_bps:>10.0f}  {_format_mbps(total_bps):>12}"
    )
    print(
        f"Hint: Resmon-like columns are Receive/Send/Total; this script also supports --watch."
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test vMix PID and per-process bandwidth from Windows Resmon-like counters"
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
