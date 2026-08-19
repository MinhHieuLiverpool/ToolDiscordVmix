"""
Launcher Hub - Bộ điều khiển trung tâm khởi chạy các Tool trong d:\\ToolDiscordVmix\\tool
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox

THEME = {
    "bg": "#0b0d14",
    "card": "#131722",
    "border": "#23293d",
    "text": "#f8fafc",
    "text_sub": "#94a3b8",
    "accent_blue": "#3b82f6",
    "accent_cyan": "#06b6d4",
    "accent_emerald": "#10b981",
    "accent_purple": "#8b5cf6",
}


def launch_sys_toolkit():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(base_dir, "sys_toolkit", "win_toolkit_gui.py")
    subprocess.Popen([sys.executable, target], cwd=os.path.join(base_dir, "sys_toolkit"))


def launch_media_toolkit():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(base_dir, "extension", "converter_gui.py")
    subprocess.Popen([sys.executable, target], cwd=os.path.join(base_dir, "extension"))


def main():
    root = tk.Tk()
    root.title("⚡ Tool Launcher Hub - Bộ Công Cụ vMix Studio")
    root.geometry("640x420")
    root.resizable(False, False)
    root.configure(bg=THEME["bg"])

    # Header
    h_frame = tk.Frame(root, bg=THEME["bg"])
    h_frame.pack(fill="x", padx=24, pady=(24, 16))

    lbl_title = tk.Label(h_frame, text="⚡ TOOL LAUNCHER HUB", font=("Segoe UI", 14, "bold"), bg=THEME["bg"], fg=THEME["text"])
    lbl_title.pack(anchor="w")

    lbl_sub = tk.Label(h_frame, text="Chọn công cụ bạn muốn khởi chạy bên dưới:", font=("Segoe UI", 9), bg=THEME["bg"], fg=THEME["text_sub"])
    lbl_sub.pack(anchor="w", pady=(4, 0))

    # Tool 1 Card: Windows Admin & Tweaker Pro
    c1 = tk.Frame(root, bg=THEME["card"], bd=1, relief="solid", highlightbackground=THEME["border"], highlightthickness=1)
    c1.pack(fill="x", padx=24, pady=8)

    c1_inner = tk.Frame(c1, bg=THEME["card"])
    c1_inner.pack(fill="both", expand=True, padx=16, pady=14)

    c1_left = tk.Frame(c1_inner, bg=THEME["card"])
    c1_left.pack(side="left", fill="both", expand=True)

    lbl_t1 = tk.Label(c1_left, text="🛠️ Windows Admin & System Tweaker Pro", font=("Segoe UI", 11, "bold"), bg=THEME["card"], fg=THEME["accent_cyan"])
    lbl_t1.pack(anchor="w")

    lbl_d1 = tk.Label(c1_left, text="CPU-Z Specs, Quản lý Driver, Power Plan, IP Tĩnh/Động, Tắt Win Update, SMB", font=("Segoe UI", 8), bg=THEME["card"], fg=THEME["text_sub"])
    lbl_d1.pack(anchor="w", pady=(2, 0))

    btn1 = tk.Button(c1_inner, text="🚀 Mở Tool", font=("Segoe UI", 9, "bold"), bg=THEME["accent_blue"], fg="#ffffff", bd=0, cursor="hand2", padx=14, pady=6, command=launch_sys_toolkit)
    btn1.pack(side="right", padx=(10, 0))

    # Tool 2 Card: Studio Media Toolkit & Converter
    c2 = tk.Frame(root, bg=THEME["card"], bd=1, relief="solid", highlightbackground=THEME["border"], highlightthickness=1)
    c2.pack(fill="x", padx=24, pady=8)

    c2_inner = tk.Frame(c2, bg=THEME["card"])
    c2_inner.pack(fill="both", expand=True, padx=16, pady=14)

    c2_left = tk.Frame(c2_inner, bg=THEME["card"])
    c2_left.pack(side="left", fill="both", expand=True)

    lbl_t2 = tk.Label(c2_left, text="🎬 Studio Media Toolkit & Converter", font=("Segoe UI", 11, "bold"), bg=THEME["card"], fg=THEME["accent_emerald"])
    lbl_t2.pack(anchor="w")

    lbl_d2 = tk.Label(c2_left, text="Tải YouTube 4K/8K/MP3, Chuyển đổi Video/Audio/Image, Convert Word ⇄ PDF", font=("Segoe UI", 8), bg=THEME["card"], fg=THEME["text_sub"])
    lbl_d2.pack(anchor="w", pady=(2, 0))

    btn2 = tk.Button(c2_inner, text="🚀 Mở Tool", font=("Segoe UI", 9, "bold"), bg=THEME["accent_emerald"], fg="#ffffff", bd=0, cursor="hand2", padx=14, pady=6, command=launch_media_toolkit)
    btn2.pack(side="right", padx=(10, 0))

    root.mainloop()


if __name__ == "__main__":
    main()
