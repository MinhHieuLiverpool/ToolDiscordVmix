"""
check_gpu_bandwidth.py
----------------------
Kiểm tra nhanh thông số GPU và băng thông mạng Sender/Receiver.

Tính năng:
- Đọc GPU stats qua nvidia-smi (nếu có NVIDIA GPU)
- Đo băng thông mạng theo thời gian thực (TX=Sender, RX=Receiver)
- Chạy một lần hoặc watch liên tục

Ví dụ:
  python check_gpu_bandwidth.py
  python check_gpu_bandwidth.py --watch --interval 1.5
  python check_gpu_bandwidth.py --watch --interval 2 --no-clear
"""

from __future__ import annotations

import argparse
import csv
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


@dataclass
class GpuInfo:
    index: str
    name: str
    util_gpu: str
    util_mem: str
    mem_used: str
    mem_total: str
    temp: str
    power: str


def format_bytes_per_sec(num_bytes_per_sec: float) -> str:
    if num_bytes_per_sec < 1024:
        return f"{num_bytes_per_sec:.0f} B/s"
    if num_bytes_per_sec < 1024**2:
        return f"{num_bytes_per_sec / 1024:.2f} KB/s"
    if num_bytes_per_sec < 1024**3:
        return f"{num_bytes_per_sec / (1024**2):.2f} MB/s"
    return f"{num_bytes_per_sec / (1024**3):.2f} GB/s"


def format_mbps(num_bytes_per_sec: float) -> str:
    mbps = (num_bytes_per_sec * 8) / 1_000_000
    return f"{mbps:.2f} Mbps"


def run_command(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {' '.join(cmd)}"
    except Exception as exc:
        return 1, "", str(exc)


def get_gpu_info_nvidia() -> Tuple[List[GpuInfo], Optional[str]]:
    query = (
        "index,name,utilization.gpu,utilization.memory,"
        "memory.used,memory.total,temperature.gpu,power.draw"
    )
    cmd = [
        "nvidia-smi",
        f"--query-gpu={query}",
        "--format=csv,noheader,nounits",
    ]

    code, out, err = run_command(cmd)
    if code != 0 or not out.strip():
        reason = err or "nvidia-smi unavailable or no NVIDIA GPU detected"
        return [], reason

    gpus: List[GpuInfo] = []
    reader = csv.reader(out.splitlines())
    for row in reader:
        if len(row) < 8:
            continue
        gpus.append(
            GpuInfo(
                index=row[0].strip(),
                name=row[1].strip(),
                util_gpu=row[2].strip(),
                util_mem=row[3].strip(),
                mem_used=row[4].strip(),
                mem_total=row[5].strip(),
                temp=row[6].strip(),
                power=row[7].strip(),
            )
        )

    return gpus, None


def get_gpu_info_wmi() -> Tuple[List[GpuInfo], Optional[str]]:
    """Fallback: đọc danh sách GPU qua WMI (Windows), áp dụng được cho AMD/Intel.

    Chỉ lấy được thông tin tĩnh (tên, VRAM, driver), không có %util/temp.
    """

    if not platform.system().lower().startswith("win"):
        return [], "WMI only available on Windows"

    # Định dạng CSV cho dễ parse: Node,AdapterRAM,DriverVersion,Name
    code, out, err = run_command([
        "wmic",
        "path",
        "Win32_VideoController",
        "get",
        "Name,AdapterRAM,DriverVersion",
        "/format:csv",
    ])
    if code != 0 or not out.strip():
        reason = err or "wmic Win32_VideoController failed"
        return [], reason

    lines = [ln for ln in out.splitlines() if ln.strip()]
    if len(lines) <= 1:
        return [], "No GPU rows from WMI"

    # CSV: Node,AdapterRAM,DriverVersion,Name
    reader = csv.reader(lines)
    headers = next(reader, None)
    if not headers or len(headers) < 4:
        # Thử parse thủ công nếu header bị thiếu
        headers = ["Node", "AdapterRAM", "DriverVersion", "Name"]

    gpus: List[GpuInfo] = []
    idx = 0
    for row in reader:
        if not row or len(row) < 4:
            continue
        # Map theo thứ tự chuẩn hoặc cuối 3 cột
        if len(row) >= 4:
            node, adapter_ram, driver_ver, name = row[-4:]  # an toàn cho mọi layout
        else:
            continue

        name = name.strip() or "Unknown GPU"
        try:
            ram_bytes = int(adapter_ram.strip() or "0")
            ram_mb = ram_bytes // (1024 * 1024)
            mem_total = f"{ram_mb}"
        except ValueError:
            mem_total = "?"

        gpus.append(
            GpuInfo(
                index=str(idx),
                name=f"{name} (driver {driver_ver.strip()})",
                util_gpu="N/A",
                util_mem="N/A",
                mem_used="?",
                mem_total=mem_total,
                temp="N/A",
                power="N/A",
            )
        )
        idx += 1

    if not gpus:
        return [], "No GPU info from WMI"
    return gpus, None


def get_gpu_info() -> Tuple[List[GpuInfo], Optional[str]]:
    """Kết hợp thông tin GPU từ NVIDIA (nvidia-smi) và WMI (AMD/Intel)."""

    all_gpus: List[GpuInfo] = []
    nvidia_gpus, nvidia_err = get_gpu_info_nvidia()
    all_gpus.extend(nvidia_gpus)

    wmi_gpus, wmi_err = get_gpu_info_wmi()

    # Tránh trùng lặp: nếu tên GPU đã xuất hiện từ nvidia-smi thì bỏ qua bản WMI
    existing_names = {g.name.split("(")[0].strip() for g in all_gpus}
    for g in wmi_gpus:
        base_name = g.name.split("(")[0].strip()
        if base_name not in existing_names:
            all_gpus.append(g)

    # Đánh lại index tuần tự để tránh trùng (GPU 0 cho NVIDIA, GPU 1 cho AMD/Intel, ...)
    if all_gpus:
        for new_idx, gpu in enumerate(all_gpus):
            gpu.index = str(new_idx)
        return all_gpus, None

    # Không lấy được gì cả
    err_msg = nvidia_err or wmi_err or "No GPU info available"
    return [], err_msg


def get_total_net_bytes_psutil() -> Tuple[int, int]:
    counters = psutil.net_io_counters()  # type: ignore[union-attr]
    return int(counters.bytes_sent), int(counters.bytes_recv)


def get_total_net_bytes_netstat_windows() -> Tuple[int, int]:
    code, out, _ = run_command(["netstat", "-e"])
    if code != 0 or not out:
        return 0, 0

    # netstat -e (Windows) có dòng:
    # Bytes                    <received>            <sent>
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    for idx, line in enumerate(lines):
        if line.lower().startswith("bytes"):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    return int(parts[2]), int(parts[1])  # sent, recv
                except ValueError:
                    pass
            if idx + 1 < len(lines):
                nums = lines[idx + 1].split()
                if len(nums) >= 2:
                    try:
                        recv = int(nums[0].replace(",", ""))
                        sent = int(nums[1].replace(",", ""))
                        return sent, recv
                    except ValueError:
                        pass

    return 0, 0


def get_total_net_bytes() -> Tuple[int, int, str]:
    if psutil is not None:
        sent, recv = get_total_net_bytes_psutil()
        return sent, recv, "psutil"

    if platform.system().lower().startswith("win"):
        sent, recv = get_total_net_bytes_netstat_windows()
        return sent, recv, "netstat"

    return 0, 0, "unavailable"


def collect_bandwidth(interval_sec: float) -> dict:
    sent_1, recv_1, source = get_total_net_bytes()
    t1 = time.time()
    time.sleep(interval_sec)
    sent_2, recv_2, _ = get_total_net_bytes()
    t2 = time.time()

    dt = max(t2 - t1, 1e-6)
    tx_bps = max(sent_2 - sent_1, 0) / dt
    rx_bps = max(recv_2 - recv_1, 0) / dt

    return {
        "source": source,
        "interval": dt,
        "tx_bps": tx_bps,
        "rx_bps": rx_bps,
        "tx_total": sent_2,
        "rx_total": recv_2,
    }


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_gpu(gpus: List[GpuInfo], error: Optional[str]) -> None:
    print("GPU STATUS")
    print("-" * 80)
    if not gpus:
        print(f"Khong doc duoc GPU: {error or 'unknown error'}")
        return

    for gpu in gpus:
        print(
            f"GPU {gpu.index}: {gpu.name} | "
            f"GPU={gpu.util_gpu}% | MEM={gpu.util_mem}% | "
            f"VRAM={gpu.mem_used}/{gpu.mem_total} MB | "
            f"TEMP={gpu.temp} C | POWER={gpu.power} W"
        )


def print_bandwidth(bw: dict) -> None:
    print("\nNETWORK BANDWIDTH (Sender/Receiver)")
    print("-" * 80)
    print(f"Data source         : {bw['source']}")
    print(f"Measure interval    : {bw['interval']:.2f} s")
    print(f"Sender (TX)         : {format_bytes_per_sec(bw['tx_bps'])} ({format_mbps(bw['tx_bps'])})")
    print(f"Receiver (RX)       : {format_bytes_per_sec(bw['rx_bps'])} ({format_mbps(bw['rx_bps'])})")
    print(f"Total sent          : {bw['tx_total']:,} bytes")
    print(f"Total received      : {bw['rx_total']:,} bytes")


def run_once(interval_sec: float) -> None:
    gpus, gpu_error = get_gpu_info()
    bw = collect_bandwidth(interval_sec)

    print(time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)
    print_gpu(gpus, gpu_error)
    print_bandwidth(bw)


def run_watch(interval_sec: float, no_clear: bool) -> None:
    while True:
        if not no_clear:
            clear_screen()
        try:
            run_once(interval_sec)
            print("\nNhan Ctrl+C de thoat.")
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nDa dung theo yeu cau.")
            return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check GPU stats + Sender/Receiver bandwidth"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Chay lien tuc"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Khoang thoi gian do bandwidth (giay), mac dinh 1.0"
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Khong clear man hinh khi watch"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    interval = max(args.interval, 0.2)

    if args.watch:
        run_watch(interval, args.no_clear)
    else:
        run_once(interval)


if __name__ == "__main__":
    main()
