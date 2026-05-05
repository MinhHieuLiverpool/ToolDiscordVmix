"""
test_network_cards.py
──────────────────────────────────────────────────────────────────────────────
Kiểm tra thông tin tất cả card mạng (Network Interface Cards) trên máy.

Hiển thị:
  • Tên card, trạng thái (UP/DOWN)
  • Địa chỉ IPv4 / IPv6 / MAC
  • Tốc độ link (Mbps) nếu đọc được
  • Byte gửi / nhận tích lũy
  • Băng thông thực tế (Mbps) tại thời điểm đo (2 giây)
  • Packet gửi / nhận, số lỗi / drop

Yêu cầu:
  pip install psutil

Chạy:
  python test_network_cards.py
  python test_network_cards.py --watch        # tự động refresh mỗi 2s
  python test_network_cards.py --interval 5   # refresh mỗi 5s
  python test_network_cards.py --iface Ethernet  # chỉ hiện card khớp tên
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

# ─── Màu ANSI ────────────────────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty() or os.environ.get("TERM") not in (None, "")
_R  = "\033[91m" if _USE_COLOR else ""
_G  = "\033[92m" if _USE_COLOR else ""
_Y  = "\033[93m" if _USE_COLOR else ""
_C  = "\033[96m" if _USE_COLOR else ""
_W  = "\033[97m" if _USE_COLOR else ""
_B  = "\033[1m"  if _USE_COLOR else ""
_DIM = "\033[2m" if _USE_COLOR else ""
_X  = "\033[0m"  if _USE_COLOR else ""

# ─── Helpers hiển thị ────────────────────────────────────────────────────────

def _sep(title: str) -> None:
    bar = f"{_C}{'─' * 72}{_X}"
    print(f"\n{bar}")
    print(f"  {_B}{_C}{title}{_X}")
    print(bar)


def _row(label: str, value: str, color: str = "") -> None:
    print(f"    {_B}{label:<28}{_X}  {color}{value}{_X}")


def _fmt_bytes(b: int) -> str:
    """Chuyển bytes → chuỗi dễ đọc (B/KB/MB/GB)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _fmt_mbps(mbps: float) -> str:
    if mbps >= 1000:
        return f"{mbps / 1000:.2f} Gbps"
    if mbps >= 1:
        return f"{mbps:.2f} Mbps"
    return f"{mbps * 1000:.1f} Kbps"


# ─── Đọc thông tin card mạng ────────────────────────────────────────────────

def _require_psutil():
    try:
        import psutil
        return psutil
    except ImportError:
        print(f"{_R}✘  psutil chưa cài. Chạy: pip install psutil{_X}")
        sys.exit(1)


def _snapshot_io() -> Dict[str, object]:
    """Lấy psutil.net_io_counters(pernic=True) tại một thời điểm."""
    ps = _require_psutil()
    return ps.net_io_counters(pernic=True)


def _measure_bandwidth(interval: float = 2.0) -> Dict[str, Tuple[float, float]]:
    """
    Đo băng thông thực tế (Mbps) bằng cách lấy 2 snapshot cách nhau `interval` giây.
    Trả về {iface: (send_mbps, recv_mbps)}.
    """
    before = _snapshot_io()
    time.sleep(interval)
    after  = _snapshot_io()

    result: Dict[str, Tuple[float, float]] = {}
    for iface in after:
        a = after[iface]
        b = before.get(iface)
        if b is None:
            result[iface] = (0.0, 0.0)
            continue
        delta_sent = max(0, a.bytes_sent - b.bytes_sent)
        delta_recv = max(0, a.bytes_recv - b.bytes_recv)
        send_mbps = (delta_sent * 8) / (interval * 1_000_000)
        recv_mbps = (delta_recv * 8) / (interval * 1_000_000)
        result[iface] = (send_mbps, recv_mbps)
    return result


def _get_all_cards(filter_name: Optional[str] = None) -> List[dict]:
    """
    Tổng hợp thông tin tất cả card mạng.
    Mỗi dict chứa: name, is_up, speed, addrs, io, bw_send, bw_recv, stats.
    """
    ps = _require_psutil()

    stats_map  = ps.net_if_stats()
    addrs_map  = ps.net_if_addrs()
    io_map     = _snapshot_io()

    # Đo băng thông (mất ~2s)
    print(f"{_DIM}  Đang đo băng thông (2s)...{_X}", end="\r", flush=True)
    bw_map = _measure_bandwidth(2.0)
    print(" " * 40, end="\r")  # xóa dòng

    cards = []
    for name, stat in sorted(stats_map.items()):
        if filter_name and filter_name.lower() not in name.lower():
            continue

        addrs = addrs_map.get(name, [])
        io    = io_map.get(name)
        bw    = bw_map.get(name, (0.0, 0.0))

        ipv4_list, ipv6_list, mac = [], [], ""
        for addr in addrs:
            fam = str(addr.family)
            if "AF_INET " in fam or fam == "2":       # IPv4
                ipv4_list.append(addr.address)
            elif "AF_INET6" in fam or fam == "10":    # IPv6
                ipv6_list.append(addr.address)
            elif "AF_LINK" in fam or fam in ("18", "17", "-1"):  # MAC
                mac = addr.address

        cards.append({
            "name":      name,
            "is_up":     stat.isup,
            "speed":     stat.speed,      # Mbps (0 = không đọc được)
            "mtu":       stat.mtu,
            "duplex":    str(stat.duplex).replace("NicDuplex.", ""),
            "ipv4":      ipv4_list,
            "ipv6":      ipv6_list,
            "mac":       mac,
            "io":        io,
            "bw_send":   bw[0],
            "bw_recv":   bw[1],
        })

    return cards


# ─── Hiển thị ────────────────────────────────────────────────────────────────

def _print_card(card: dict) -> None:
    name   = card["name"]
    is_up  = card["is_up"]
    status_str = f"{_G}▲ UP{_X}"   if is_up else f"{_R}▼ DOWN{_X}"
    speed_str  = _fmt_mbps(card["speed"]) if card["speed"] > 0 else "(không đọc được)"

    _sep(f"{name}  {status_str}")

    # Địa chỉ
    for ip in card["ipv4"]:
        _row("IPv4", ip, _W)
    for ip in card["ipv6"]:
        short = ip.split("%")[0]  # bỏ phần zone ID
        _row("IPv6", short, _DIM)
    if card["mac"]:
        _row("MAC", card["mac"].upper(), _Y)

    # Thông số link
    _row("Trạng thái", "UP" if is_up else "DOWN", _G if is_up else _R)
    _row("Tốc độ link", speed_str)
    _row("MTU", str(card["mtu"]))
    _row("Duplex", card["duplex"])

    # Băng thông realtime
    send_c = _G if card["bw_send"] > 0.1 else _DIM
    recv_c = _C if card["bw_recv"] > 0.1 else _DIM
    _row("Băng thông ▲ Gửi",  _fmt_mbps(card["bw_send"]),  send_c)
    _row("Băng thông ▼ Nhận", _fmt_mbps(card["bw_recv"]),  recv_c)

    # IO tích lũy
    io = card["io"]
    if io:
        _row("Tổng gửi",   _fmt_bytes(io.bytes_sent), _DIM)
        _row("Tổng nhận",  _fmt_bytes(io.bytes_recv), _DIM)
        _row("Packet gửi", f"{io.packets_sent:,}",    _DIM)
        _row("Packet nhận",f"{io.packets_recv:,}",    _DIM)
        errs = io.errin + io.errout
        drops = io.dropin + io.dropout
        _row("Lỗi (in+out)", str(errs),  _R if errs  > 0 else _DIM)
        _row("Drop (in+out)",str(drops), _Y if drops > 0 else _DIM)


def _print_summary(cards: List[dict]) -> None:
    _sep("TỔNG HỢP CÁC CARD MẠNG")

    # Header
    w_name = max(len(c["name"]) for c in cards) + 2
    hdr = (
        f"  {'Tên card':<{w_name}} {'ST':^5} {'Speed':>10} "
        f"{'▲ Gửi (Mbps)':>14} {'▼ Nhận (Mbps)':>14}  {'IPv4'}"
    )
    print(f"\n{_B}{_C}{hdr}{_X}")
    print("  " + "─" * (w_name + 55))

    for c in cards:
        st     = f"{_G}UP{_X}  " if c["is_up"] else f"{_R}DOWN{_X}"
        speed  = _fmt_mbps(c["speed"]) if c["speed"] > 0 else "—"
        send_s = f"{c['bw_send']:.2f}"
        recv_s = f"{c['bw_recv']:.2f}"
        ipv4   = ", ".join(c["ipv4"]) or "—"
        send_c = _G if c["bw_send"] > 0.1 else ""
        recv_c = _C if c["bw_recv"] > 0.1 else ""
        print(
            f"  {c['name']:<{w_name}} {st} {speed:>9} "
            f"  {send_c}{send_s:>12}{_X}   {recv_c}{recv_s:>12}{_X}  {ipv4}"
        )

    total_send = sum(c["bw_send"] for c in cards)
    total_recv = sum(c["bw_recv"] for c in cards)
    print("\n  " + "─" * (w_name + 55))
    print(f"  {'TỔNG':<{w_name + 6}}  {_G}{total_send:>12.2f} Mbps{_X}   {_C}{total_recv:>12.2f} Mbps{_X}")


# ─── Main ────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Kiểm tra card mạng")
    p.add_argument("--watch",    action="store_true", help="Tự động refresh liên tục")
    p.add_argument("--interval", type=float, default=2.0, help="Giây giữa mỗi lần refresh (mặc định: 2)")
    p.add_argument("--iface",    type=str,   default="",  help="Lọc theo tên card (ví dụ: Ethernet, Wi-Fi)")
    p.add_argument("--summary",  action="store_true", help="Chỉ hiện bảng tổng hợp, không chi tiết")
    return p.parse_args()


def run_once(args: argparse.Namespace) -> None:
    from datetime import datetime
    os.system("cls" if os.name == "nt" else "clear") if args.watch else None

    print(f"\n{_B}{'═' * 72}{_X}")
    print(f"  {_B}🌐 NETWORK CARD CHECKER{_X}  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Interval đo băng thông: {args.interval:.1f}s")
    print(f"{_B}{'═' * 72}{_X}")

    cards = _get_all_cards(filter_name=args.iface or None)

    if not cards:
        print(f"\n{_Y}⚠  Không tìm thấy card mạng nào{f' khớp: {args.iface}' if args.iface else ''}.{_X}")
        return

    _print_summary(cards)

    if not args.summary:
        for card in cards:
            _print_card(card)

    print()


def main() -> None:
    args = _parse_args()

    if args.watch:
        try:
            while True:
                run_once(args)
                time.sleep(max(0, args.interval - 2.0))  # bù 2s đo bandwidth
        except KeyboardInterrupt:
            print(f"\n{_Y}Đã dừng.{_X}")
    else:
        run_once(args)


if __name__ == "__main__":
    main()
