# -*- coding: utf-8 -*-
"""
Studio Media Toolkit & Converter GUI
====================================
Giao diện chuyển đổi đa định dạng & công cụ tải media:
  • Video:  MP4 ↔ MOV
  • Audio:  MP4 → MP3, MP4 → WAV
  • Image:  JPG ↔ PNG, Convert All → JPEG
  • Doc:    Word ↔ PDF
  • YouTube Downloader (Video MP4 / Audio MP3, WAV)
  • URL Image Downloader (Single & Batch)
"""

import os
import sys
import threading
import subprocess
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Import core converter & downloaders
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from converter import (
    convert_file,
    download_youtube,
    get_youtube_info,
    get_youtube_playlist_info,
    download_image,
    get_ffmpeg_path,
    _find_and_setup_ffmpeg,
    CONVERTERS,
)

_find_and_setup_ffmpeg()

# ── Color Palette (Studio Dark Cyber Theme) ──────────────────────────────────
THEME = {
    "bg_main": "#0b0f19",        # Nền chính siêu tối, hiện đại
    "bg_sidebar": "#111827",     # Sidebar xám đen
    "bg_card": "#1f2937",        # Card / panel
    "bg_card_inner": "#151d2a",  # Card con / input background
    "bg_hover": "#283548",       # Hover element
    "primary": "#6366f1",        # Indigo primary
    "primary_hover": "#4f46e5",  # Indigo hover
    "accent": "#ec4899",         # Pink accent
    "accent_hover": "#db2777",
    "success": "#10b981",        # Emerald green
    "warning": "#f59e0b",        # Amber
    "danger": "#ef4444",         # Rose red
    "danger_hover": "#dc2626",
    "text_main": "#f9fafb",      # White text
    "text_muted": "#9ca3af",     # Gray text
    "text_dim": "#6b7280",       # Dark gray
    "border": "#374151",         # Border color
    "border_focus": "#6366f1",   # Border focus
}


class StudioToolkitApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Studio Media Toolkit & Converter v2.0")
        self.root.geometry("1020x680")
        self.root.minsize(940, 620)
        self.root.configure(bg=THEME["bg_main"])

        # Try to set modern font
        self.font_family = "Segoe UI"
        self.default_output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(self.default_output_dir):
            self.default_output_dir = os.getcwd()

        self.current_tab = "video_audio"
        self.selected_files = []
        self.is_processing = False
        self.stop_requested = False
        self.current_playlist = None
        self.playlist_check_vars = []

        self._setup_styles()
        self._build_ui()
        self._select_tab("video_audio")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Configure Scrollbar
        style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background=THEME["bg_card"],
            darkcolor=THEME["bg_card"],
            lightcolor=THEME["bg_card"],
            troughcolor=THEME["bg_main"],
            bordercolor=THEME["bg_main"],
            arrowcolor=THEME["text_muted"],
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("active", THEME["primary"])],
        )

        # Progressbar
        style.configure(
            "Studio.Horizontal.TProgressbar",
            troughcolor=THEME["bg_card_inner"],
            background=THEME["primary"],
            darkcolor=THEME["primary"],
            lightcolor=THEME["accent"],
            bordercolor=THEME["bg_card"],
            thickness=8,
        )

    def _build_ui(self):
        # ── Main Grid Container ──────────────────────────────────────────────
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ── 1. LEFT SIDEBAR ──────────────────────────────────────────────────
        self.sidebar = tk.Frame(self.root, bg=THEME["bg_sidebar"], width=230)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self._build_sidebar()

        # ── 2. RIGHT MAIN CONTENT ────────────────────────────────────────────
        self.main_container = tk.Frame(self.root, bg=THEME["bg_main"])
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.rowconfigure(1, weight=1)

        # Top Header (Global output path + actions)
        self._build_top_header()

        # Dynamic Content Body
        self.content_frame = tk.Frame(self.main_container, bg=THEME["bg_main"])
        self.content_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        # Bottom Global Status & Progress Bar
        self._build_bottom_status()

    def _build_sidebar(self):
        # Logo / Brand
        brand_frame = tk.Frame(self.sidebar, bg=THEME["bg_sidebar"])
        brand_frame.pack(fill="x", padx=18, pady=(20, 24))

        lbl_icon = tk.Label(
            brand_frame,
            text="⚡",
            font=(self.font_family, 22),
            fg=THEME["accent"],
            bg=THEME["bg_sidebar"],
        )
        lbl_icon.pack(side="left")

        brand_text_frame = tk.Frame(brand_frame, bg=THEME["bg_sidebar"])
        brand_text_frame.pack(side="left", padx=(8, 0))

        lbl_brand = tk.Label(
            brand_text_frame,
            text="MEDIA STUDIO",
            font=(self.font_family, 13, "bold"),
            fg=THEME["text_main"],
            bg=THEME["bg_sidebar"],
        )
        lbl_brand.pack(anchor="w")

        lbl_subbrand = tk.Label(
            brand_text_frame,
            text="TOOLKIT & CONVERTER",
            font=(self.font_family, 8, "bold"),
            fg=THEME["primary"],
            bg=THEME["bg_sidebar"],
        )
        lbl_subbrand.pack(anchor="w")

        # Separator line
        sep = tk.Frame(self.sidebar, bg=THEME["border"], height=1)
        sep.pack(fill="x", padx=14, pady=(0, 16))

        # Nav Buttons Container
        self.nav_buttons = {}
        nav_items = [
            ("video_audio", "🎬  Video & Audio", "MP4, MOV, MP3, WAV"),
            ("image_conv", "🖼️  Image Converter", "JPG, PNG, JPEG"),
            ("doc_conv", "📄  Doc Converter", "Word ↔ PDF"),
            ("youtube_dl", "📥  YouTube Downloader", "Video & Audio HD"),
            ("image_dl", "🌐  URL Image Downloader", "Single & Batch URL"),
        ]

        for tab_id, title, subtitle in nav_items:
            btn_frame = tk.Frame(self.sidebar, bg=THEME["bg_sidebar"], cursor="hand2")
            btn_frame.pack(fill="x", padx=10, pady=4)

            # Left Active Indicator Bar
            bar = tk.Frame(btn_frame, bg=THEME["bg_sidebar"], width=4)
            bar.pack(side="left", fill="y")

            text_frame = tk.Frame(btn_frame, bg=THEME["bg_sidebar"])
            text_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            lbl_t = tk.Label(
                text_frame,
                text=title,
                font=(self.font_family, 10, "bold"),
                fg=THEME["text_muted"],
                bg=THEME["bg_sidebar"],
                anchor="w",
            )
            lbl_t.pack(fill="x")

            lbl_s = tk.Label(
                text_frame,
                text=subtitle,
                font=(self.font_family, 8),
                fg=THEME["text_dim"],
                bg=THEME["bg_sidebar"],
                anchor="w",
            )
            lbl_s.pack(fill="x")

            # Store references
            self.nav_buttons[tab_id] = {
                "frame": btn_frame,
                "bar": bar,
                "title": lbl_t,
                "sub": lbl_s,
                "text_frame": text_frame,
            }

            # Bind clicks
            for widget in (btn_frame, bar, text_frame, lbl_t, lbl_s):
                widget.bind("<Button-1>", lambda e, tid=tab_id: self._select_tab(tid))

        # Sidebar Bottom Footer
        footer_frame = tk.Frame(self.sidebar, bg=THEME["bg_sidebar"])
        footer_frame.pack(side="bottom", fill="x", padx=14, pady=16)

        ff_path = get_ffmpeg_path()
        ffmpeg_status = "✅ FFmpeg Active (Max/4K)" if ff_path else "⚠️ FFmpeg Missing"
        lbl_ff = tk.Label(
            footer_frame,
            text=ffmpeg_status,
            font=(self.font_family, 8, "bold" if ff_path else "normal"),
            fg=THEME["success"] if ff_path else THEME["warning"],
            bg=THEME["bg_sidebar"],
        )
        lbl_ff.pack(anchor="w")

        lbl_ver = tk.Label(
            footer_frame,
            text="Team Studio • v2.0 Pro",
            font=(self.font_family, 8),
            fg=THEME["text_dim"],
            bg=THEME["bg_sidebar"],
        )
        lbl_ver.pack(anchor="w", pady=(2, 0))

    def _select_tab(self, tab_id):
        self.current_tab = tab_id

        # Update sidebar styling
        for tid, items in self.nav_buttons.items():
            if tid == tab_id:
                items["frame"].configure(bg=THEME["bg_card"])
                items["text_frame"].configure(bg=THEME["bg_card"])
                items["bar"].configure(bg=THEME["primary"])
                items["title"].configure(fg=THEME["text_main"], bg=THEME["bg_card"])
                items["sub"].configure(fg=THEME["primary"], bg=THEME["bg_card"])
            else:
                items["frame"].configure(bg=THEME["bg_sidebar"])
                items["text_frame"].configure(bg=THEME["bg_sidebar"])
                items["bar"].configure(bg=THEME["bg_sidebar"])
                items["title"].configure(fg=THEME["text_muted"], bg=THEME["bg_sidebar"])
                items["sub"].configure(fg=THEME["text_dim"], bg=THEME["bg_sidebar"])

        # Render corresponding page in content frame
        for child in self.content_frame.winfo_children():
            child.destroy()

        if tab_id == "video_audio":
            self._render_video_audio_page()
        elif tab_id == "image_conv":
            self._render_image_conv_page()
        elif tab_id == "doc_conv":
            self._render_doc_conv_page()
        elif tab_id == "youtube_dl":
            self._render_youtube_dl_page()
        elif tab_id == "image_dl":
            self._render_image_dl_page()

    def _build_top_header(self):
        header_card = tk.Frame(self.main_container, bg=THEME["bg_card"], padx=14, pady=10)
        header_card.grid(row=0, column=0, sticky="ew")

        # Destination Folder Settings
        lbl_dest = tk.Label(
            header_card,
            text="📂 Thư mục lưu đầu ra (Output):",
            font=(self.font_family, 9, "bold"),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        lbl_dest.pack(side="left", padx=(4, 8))

        self.output_dir_var = tk.StringVar(value=self.default_output_dir)
        ent_output = tk.Entry(
            header_card,
            textvariable=self.output_dir_var,
            font=(self.font_family, 9),
            bg=THEME["bg_card_inner"],
            fg=THEME["text_main"],
            insertbackground=THEME["text_main"],
            relief="flat",
            bd=5,
        )
        ent_output.pack(side="left", fill="x", expand=True, padx=4)

        btn_browse_output = tk.Button(
            header_card,
            text="Chọn...",
            font=(self.font_family, 9, "bold"),
            bg=THEME["bg_hover"],
            fg=THEME["text_main"],
            activebackground=THEME["primary"],
            activeforeground="#fff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._choose_output_dir,
        )
        btn_browse_output.pack(side="left", padx=4)

        btn_open_output = tk.Button(
            header_card,
            text="Mở Thư Mục",
            font=(self.font_family, 9, "bold"),
            bg=THEME["primary"],
            fg="#ffffff",
            activebackground=THEME["primary_hover"],
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._open_output_dir,
        )
        btn_open_output.pack(side="left", padx=(4, 0))

    def _build_bottom_status(self):
        bottom_frame = tk.Frame(self.main_container, bg=THEME["bg_main"])
        bottom_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progressbar = ttk.Progressbar(
            bottom_frame,
            variable=self.progress_var,
            maximum=100,
            style="Studio.Horizontal.TProgressbar",
        )
        self.progressbar.pack(fill="x")

        status_info_frame = tk.Frame(bottom_frame, bg=THEME["bg_main"])
        status_info_frame.pack(fill="x", pady=(4, 0))

        self.lbl_status = tk.Label(
            status_info_frame,
            text="Sẵn sàng thực hiện",
            font=(self.font_family, 9),
            fg=THEME["text_muted"],
            bg=THEME["bg_main"],
        )
        self.lbl_status.pack(side="left")

        self.lbl_extra_status = tk.Label(
            status_info_frame,
            text="",
            font=(self.font_family, 9, "bold"),
            fg=THEME["accent"],
            bg=THEME["bg_main"],
        )
        self.lbl_extra_status.pack(side="right")

    def _choose_output_dir(self):
        d = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if d:
            self.output_dir_var.set(d)

    def _open_output_dir(self):
        d = self.output_dir_var.get()
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        os.startfile(d)

    def _update_status(self, text, progress=None, extra=""):
        self.lbl_status.config(text=text)
        self.lbl_extra_status.config(text=extra)
        if progress is not None:
            self.progress_var.set(progress)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1: VIDEO & AUDIO CONVERTER
    # ══════════════════════════════════════════════════════════════════════════
    def _render_video_audio_page(self):
        self._build_generic_converter_page(
            title="🎬 Chuyển Đổi Video & Audio",
            subtitle="Chuyển đổi định dạng Video và trích xuất Audio chất lượng cao",
            options=[
                ("MP4 → MOV", "mp4", "mov", "Đổi sang định dạng Apple QuickTime MOV"),
                ("MOV → MP4", "mov", "mp4", "Đổi MOV sang MP4 tương thích đa nền tảng"),
                ("MP4 → MP3", "mp4", "mp3", "Trích xuất âm thanh MP3 192kbps"),
                ("MP4 → WAV", "mp4", "wav", "Trích xuất âm thanh chuẩn không nén WAV"),
            ],
            filetypes=[
                ("Video/Audio Files", "*.mp4 *.mov *.mkv *.avi *.flv"),
                ("All Files", "*.*"),
            ],
        )

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2: IMAGE CONVERTER
    # ══════════════════════════════════════════════════════════════════════════
    def _render_image_conv_page(self):
        self._build_generic_converter_page(
            title="🖼️ Chuyển Đổi Hình Ảnh",
            subtitle="Chuyển đổi qua lại giữa JPG, PNG và nén JPEG tối ưu",
            options=[
                ("JPG → PNG", "jpg", "png", "Chuyển JPG sang PNG giữ nguyên chất lượng"),
                ("PNG → JPG", "png", "jpg", "Chuyển PNG sang JPG tối ưu dung lượng"),
                ("Any → JPEG", "any", "jpeg", "Chuyển mọi định dạng (WebP, BMP, PNG...) sang JPEG"),
            ],
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff"),
                ("All Files", "*.*"),
            ],
        )

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3: DOCUMENT CONVERTER
    # ══════════════════════════════════════════════════════════════════════════
    def _render_doc_conv_page(self):
        self._build_generic_converter_page(
            title="📄 Chuyển Đổi Văn Bản (Word ↔ PDF)",
            subtitle="Convert tài liệu Word .docx sang PDF hoặc trích xuất PDF thành Word .docx",
            options=[
                ("Word (.docx) → PDF", "docx", "pdf", "Chuyển đổi Word DOCX sang tài liệu PDF"),
                ("PDF → Word (.docx)", "pdf", "docx", "Chuyển đổi file PDF sang Word DOCX để chỉnh sửa"),
            ],
            filetypes=[
                ("Documents", "*.docx *.pdf"),
                ("Word Documents", "*.docx"),
                ("PDF Documents", "*.pdf"),
                ("All Files", "*.*"),
            ],
        )

    def _build_generic_converter_page(self, title, subtitle, options, filetypes):
        self.selected_files = []

        container = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        container.pack(fill="both", expand=True)

        # Title card
        t_card = tk.Frame(container, bg=THEME["bg_card"], padx=16, pady=12)
        t_card.pack(fill="x", pady=(0, 10))

        lbl_t = tk.Label(
            t_card,
            text=title,
            font=(self.font_family, 13, "bold"),
            fg=THEME["text_main"],
            bg=THEME["bg_card"],
        )
        lbl_t.pack(anchor="w")

        lbl_sub = tk.Label(
            t_card,
            text=subtitle,
            font=(self.font_family, 9),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Radio options in card
        opt_card = tk.Frame(container, bg=THEME["bg_card"], padx=16, pady=10)
        opt_card.pack(fill="x", pady=(0, 10))

        self.conv_mode_var = tk.StringVar(value=options[0][2])
        self.conv_opt_map = {}

        for name, src, tgt, desc in options:
            self.conv_opt_map[tgt] = (src, tgt)
            r_frame = tk.Frame(opt_card, bg=THEME["bg_card"])
            r_frame.pack(fill="x", pady=2)

            rb = tk.Radiobutton(
                r_frame,
                text=name,
                variable=self.conv_mode_var,
                value=tgt,
                font=(self.font_family, 10, "bold"),
                fg=THEME["text_main"],
                bg=THEME["bg_card"],
                selectcolor=THEME["bg_sidebar"],
                activebackground=THEME["bg_card"],
                activeforeground=THEME["accent"],
            )
            rb.pack(side="left")

            lbl_desc = tk.Label(
                r_frame,
                text=f"— {desc}",
                font=(self.font_family, 9),
                fg=THEME["text_dim"],
                bg=THEME["bg_card"],
            )
            lbl_desc.pack(side="left", padx=8)

        # File List card
        list_card = tk.Frame(container, bg=THEME["bg_card"], padx=14, pady=12)
        list_card.pack(fill="both", expand=True)

        btn_row = tk.Frame(list_card, bg=THEME["bg_card"])
        btn_row.pack(fill="x", pady=(0, 8))

        btn_add = tk.Button(
            btn_row,
            text="📂  Chọn File...",
            font=(self.font_family, 10, "bold"),
            bg=THEME["primary"],
            fg="#fff",
            activebackground=THEME["primary_hover"],
            activeforeground="#fff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: self._select_converter_files(filetypes),
        )
        btn_add.pack(side="left", padx=(0, 8))

        btn_clear = tk.Button(
            btn_row,
            text="Xóa Danh Sách",
            font=(self.font_family, 9),
            bg=THEME["bg_hover"],
            fg=THEME["text_muted"],
            activebackground=THEME["danger"],
            activeforeground="#fff",
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._clear_converter_files,
        )
        btn_clear.pack(side="left")

        self.lbl_file_count = tk.Label(
            btn_row,
            text="Chưa chọn file nào",
            font=(self.font_family, 9),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        self.lbl_file_count.pack(side="left", padx=14)

        # Start convert action button
        self.btn_convert = tk.Button(
            btn_row,
            text="⚡  BẮT ĐẦU CHUYỂN ĐỔI",
            font=(self.font_family, 10, "bold"),
            bg=THEME["success"],
            fg="#fff",
            activebackground="#059669",
            activeforeground="#fff",
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
            command=self._start_batch_conversion,
        )
        self.btn_convert.pack(side="right")

        # Listbox with scrollbar
        list_inner = tk.Frame(list_card, bg=THEME["bg_card_inner"])
        list_inner.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_inner, orient="vertical", style="Vertical.TScrollbar")
        self.file_listbox = tk.Listbox(
            list_inner,
            font=("Consolas", 10),
            bg=THEME["bg_card_inner"],
            fg=THEME["text_main"],
            selectbackground=THEME["primary"],
            selectforeground="#fff",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.file_listbox.yview)

        self.file_listbox.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        scrollbar.pack(side="right", fill="y", pady=6, padx=(0, 6))

    def _select_converter_files(self, filetypes):
        files = filedialog.askopenfilenames(
            title="Chọn các file cần chuyển đổi",
            filetypes=filetypes,
        )
        if files:
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self._refresh_converter_file_list()

    def _clear_converter_files(self):
        self.selected_files = []
        self._refresh_converter_file_list()

    def _refresh_converter_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for i, f in enumerate(self.selected_files, 1):
            sz = os.path.getsize(f) / 1024
            sz_str = f"{sz:.1f} KB" if sz < 1024 else f"{sz/1024:.1f} MB"
            self.file_listbox.insert(tk.END, f" {i:02d}. [{sz_str}]  {Path(f).name}  —  {f}")
        self.lbl_file_count.config(
            text=f"{len(self.selected_files)} file đã chọn",
            fg=THEME["success"] if self.selected_files else THEME["text_muted"],
        )

    def _start_batch_conversion(self):
        if self.is_processing:
            messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang chạy, vui lòng chờ!")
            return

        if not self.selected_files:
            messagebox.showwarning("Chưa có file", "Vui lòng thêm ít nhất 1 file để chuyển đổi!")
            return

        target_fmt = self.conv_mode_var.get()
        out_dir = self.output_dir_var.get()
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        files = list(self.selected_files)

        # Instant visual feedback
        self.btn_convert.config(text="⏳  ĐANG CHUYỂN ĐỔI...", bg="#374151", state="disabled")
        self._update_status(f"⏳ Bắt đầu chuyển đổi {len(files)} file...", 2, "Đang xử lý...")

        def _worker():
            self.is_processing = True
            total = len(files)
            success = 0
            errors = []

            for i, fpath in enumerate(files):
                fname = Path(fpath).name
                self.root.after(0, lambda i=i, fn=fname: self._update_status(
                    f"Đang convert ({i+1}/{total}): {fn}...",
                    (i / total) * 100,
                    f"{i+1}/{total}",
                ))

                out_path = os.path.join(out_dir, Path(fpath).with_suffix(f".{target_fmt}").name)
                try:
                    convert_file(fpath, target_fmt, out_path)
                    success += 1
                except Exception as ex:
                    errors.append(f"{fname}: {ex}")

            self.is_processing = False
            self.root.after(0, lambda: self.btn_convert.config(text="⚡  BẮT ĐẦU CHUYỂN ĐỔI", bg=THEME["success"], state="normal"))
            self.root.after(0, lambda s=success, t=total: self._update_status("Chuyển đổi hoàn tất!", 100, f"✅ {s}/{t}"))

            msg = f"Đã chuyển đổi thành công {success}/{total} file vào thư mục đầu ra!"
            if errors:
                msg += "\n\n❌ Lỗi:\n" + "\n".join(errors[:4])
            self.root.after(100, lambda m=msg: messagebox.showinfo("Kết quả", m))

        threading.Thread(target=_worker, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4: YOUTUBE DOWNLOADER (SINGLE & PLAYLIST + STOP BUTTON)
    # ══════════════════════════════════════════════════════════════════════════
    def _render_youtube_dl_page(self):
        container = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        container.pack(fill="both", expand=True)

        # Header card
        t_card = tk.Frame(container, bg=THEME["bg_card"], padx=16, pady=12)
        t_card.pack(fill="x", pady=(0, 10))

        lbl_t = tk.Label(
            t_card,
            text="📥 Tải Video, Audio & Playlist Từ YouTube",
            font=(self.font_family, 13, "bold"),
            fg=THEME["text_main"],
            bg=THEME["bg_card"],
        )
        lbl_t.pack(anchor="w")

        lbl_sub = tk.Label(
            t_card,
            text="Dán link Video đơn hoặc Playlist YouTube để chọn lọc và tải hàng loạt (hỗ trợ nút Dừng tải)",
            font=(self.font_family, 9),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # URL Input Card
        url_card = tk.Frame(container, bg=THEME["bg_card"], padx=16, pady=12)
        url_card.pack(fill="x", pady=(0, 10))

        lbl_url = tk.Label(
            url_card,
            text="🔗 Nhập hoặc dán URL YouTube (Video hoặc Playlist):",
            font=(self.font_family, 10, "bold"),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        lbl_url.pack(anchor="w", pady=(0, 6))

        row_input = tk.Frame(url_card, bg=THEME["bg_card"])
        row_input.pack(fill="x")

        self.yt_url_var = tk.StringVar()
        ent_yt = tk.Entry(
            row_input,
            textvariable=self.yt_url_var,
            font=(self.font_family, 11),
            bg=THEME["bg_card_inner"],
            fg=THEME["text_main"],
            insertbackground=THEME["text_main"],
            relief="flat",
            bd=6,
        )
        ent_yt.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_paste = tk.Button(
            row_input,
            text="📋 Dán Link",
            font=(self.font_family, 9, "bold"),
            bg=THEME["bg_hover"],
            fg=THEME["text_main"],
            activebackground=THEME["primary"],
            activeforeground="#fff",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._paste_yt_url,
        )
        btn_paste.pack(side="left", padx=(0, 6))

        self.btn_check_yt = tk.Button(
            row_input,
            text="🔍 Kiểm Tra Link",
            font=(self.font_family, 9, "bold"),
            bg=THEME["primary"],
            fg="#fff",
            activebackground=THEME["primary_hover"],
            activeforeground="#fff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._check_yt_info,
        )
        self.btn_check_yt.pack(side="left")

        # Format & Quality Selection
        fmt_card = tk.Frame(container, bg=THEME["bg_card"], padx=16, pady=10)
        fmt_card.pack(fill="x", pady=(0, 10))

        lbl_fmt = tk.Label(
            fmt_card,
            text="🎯 Chọn Định Dạng & Chất Lượng Xuất:",
            font=(self.font_family, 10, "bold"),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        lbl_fmt.pack(anchor="w", pady=(0, 6))

        self.yt_format_var = tk.StringVar(value="mp4:best")

        radio_row = tk.Frame(fmt_card, bg=THEME["bg_card"])
        radio_row.pack(fill="x")

        yt_opts = [
            ("🎬 Video MP4 (Max / 4K / 2K / 1080p 60fps - Tốt nhất)", "mp4", "best"),
            ("🎬 Video MP4 (2160p 4K Ultra HD)", "mp4", "2160"),
            ("🎬 Video MP4 (1440p 2K QHD)", "mp4", "1440"),
            ("🎬 Video MP4 (1080p Full HD)", "mp4", "1080"),
            ("🎬 Video MP4 (720p HD)", "mp4", "720"),
            ("🎵 Nhạc MP3 (320kbps Cao cấp)", "mp3", "best"),
            ("🎵 Nhạc WAV (Lossless Không nén)", "wav", "best"),
        ]

        for text, fmt, q in yt_opts:
            rb = tk.Radiobutton(
                radio_row,
                text=text,
                variable=self.yt_format_var,
                value=f"{fmt}:{q}",
                font=(self.font_family, 9, "bold"),
                fg=THEME["text_main"],
                bg=THEME["bg_card"],
                selectcolor=THEME["bg_sidebar"],
                activebackground=THEME["bg_card"],
                activeforeground=THEME["accent"],
            )
            rb.pack(anchor="w", pady=2)
            if fmt == "mp4" and q == "best":
                rb.select()

        # Dynamic Info & Playlist Card
        self.yt_info_card = tk.Frame(container, bg=THEME["bg_card"], padx=16, pady=12)
        self.yt_info_card.pack(fill="both", expand=True)

        self.lbl_yt_title = tk.Label(
            self.yt_info_card,
            text="ℹ️ Dán link Video hoặc Playlist YouTube và bấm 'Kiểm Tra Link' hoặc 'Bắt Đầu Tải'",
            font=(self.font_family, 10),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
            wraplength=700,
            justify="left",
        )
        self.lbl_yt_title.pack(anchor="w", pady=(0, 8))

        # Playlist Container Frame (Hidden by default, shown when playlist is detected)
        self.playlist_frame = tk.Frame(self.yt_info_card, bg=THEME["bg_card"])

        # Playlist Toolbar
        pl_toolbar = tk.Frame(self.playlist_frame, bg=THEME["bg_card"])
        pl_toolbar.pack(fill="x", pady=(0, 6))

        btn_select_all = tk.Button(
            pl_toolbar,
            text="☑️ Chọn Tất Cả",
            font=(self.font_family, 8, "bold"),
            bg=THEME["bg_hover"],
            fg=THEME["text_main"],
            activebackground=THEME["primary"],
            activeforeground="#fff",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._select_all_playlist,
        )
        btn_select_all.pack(side="left", padx=(0, 6))

        btn_deselect_all = tk.Button(
            pl_toolbar,
            text="◻️ Bỏ Chọn",
            font=(self.font_family, 8),
            bg=THEME["bg_hover"],
            fg=THEME["text_muted"],
            activebackground=THEME["danger"],
            activeforeground="#fff",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._deselect_all_playlist,
        )
        btn_deselect_all.pack(side="left")

        self.lbl_pl_selected_count = tk.Label(
            pl_toolbar,
            text="Đã chọn: 0/0 video",
            font=(self.font_family, 9, "bold"),
            fg=THEME["success"],
            bg=THEME["bg_card"],
        )
        self.lbl_pl_selected_count.pack(side="right")

        # Scrollable Playlist Checklist (Canvas + Frame)
        pl_scroll_card = tk.Frame(self.playlist_frame, bg=THEME["bg_card_inner"])
        pl_scroll_card.pack(fill="both", expand=True, pady=(0, 8))

        self.pl_canvas = tk.Canvas(
            pl_scroll_card,
            bg=THEME["bg_card_inner"],
            highlightthickness=0,
            borderwidth=0,
        )
        pl_scrollbar = ttk.Scrollbar(pl_scroll_card, orient="vertical", command=self.pl_canvas.yview, style="Vertical.TScrollbar")
        self.pl_items_frame = tk.Frame(self.pl_canvas, bg=THEME["bg_card_inner"])

        self.pl_items_frame.bind(
            "<Configure>",
            lambda e: self.pl_canvas.configure(scrollregion=self.pl_canvas.bbox("all"))
        )
        self.pl_canvas_window = self.pl_canvas.create_window((0, 0), window=self.pl_items_frame, anchor="nw")
        self.pl_canvas.configure(yscrollcommand=pl_scrollbar.set)

        self.pl_canvas.bind("<Configure>", lambda e: self.pl_canvas.itemconfig(self.pl_canvas_window, width=e.width))

        self.pl_canvas.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        pl_scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=4)

        # Action Buttons Row (Download + Stop)
        act_row = tk.Frame(self.yt_info_card, bg=THEME["bg_card"])
        act_row.pack(fill="x", pady=(8, 0))

        self.btn_download_yt = tk.Button(
            act_row,
            text="⬇️  BẮT ĐẦU TẢI YOUTUBE",
            font=(self.font_family, 11, "bold"),
            bg=THEME["accent"],
            fg="#fff",
            activebackground=THEME["accent_hover"],
            activeforeground="#fff",
            relief="flat",
            padx=24,
            pady=10,
            cursor="hand2",
            command=self._start_youtube_download,
        )
        self.btn_download_yt.pack(side="left", padx=(0, 10))

        self.btn_stop_yt = tk.Button(
            act_row,
            text="🛑  DỪNG TẢI (STOP)",
            font=(self.font_family, 11, "bold"),
            bg=THEME["bg_card_inner"],
            fg=THEME["text_dim"],
            activebackground=THEME["danger_hover"],
            activeforeground="#fff",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            state="disabled",
            command=self._stop_youtube_download,
        )
        self.btn_stop_yt.pack(side="left")

    def _paste_yt_url(self):
        try:
            txt = self.root.clipboard_get()
            if txt:
                self.yt_url_var.set(txt.strip())
        except Exception:
            pass

    def _check_yt_info(self):
        url = self.yt_url_var.get().strip()
        if not url:
            messagebox.showwarning("Thiếu URL", "Vui lòng nhập link YouTube!")
            return

        self._update_status("Đang quét link YouTube...", 10, "Đang phân tích...")
        self.btn_check_yt.config(state="disabled", text="⏳ Đang quét...")

        def _worker():
            try:
                info = get_youtube_playlist_info(url)
                self.current_playlist = info

                if info.get("is_playlist"):
                    # Playlist detected
                    pl_title = info.get("title", "YouTube Playlist")
                    entries = info.get("entries", [])
                    disp = f"📋 PLAYLIST: {pl_title} ({len(entries)} video)"
                    self.root.after(0, lambda: self._show_playlist_ui(disp, entries))
                else:
                    # Single video
                    dur = info.get("duration", 0)
                    dur_str = f"{dur//60}m {dur%60}s" if dur else "N/A"
                    title = info.get("title", "Không rõ")
                    uploader = info.get("uploader", "N/A")
                    max_h = info.get("max_height")
                    res_str = f"🎞️ Độ phân giải gốc trên YouTube: {max_h}p" if max_h else ""
                    disp = f"🎬 {title}\n👤 Kênh: {uploader}  |  ⏱️ Thời lượng: {dur_str}"
                    if res_str:
                        disp += f"  |  {res_str}"
                    self.root.after(0, lambda: self._show_single_video_ui(disp))

                self.root.after(0, lambda: self._update_status("Đã nhận diện URL YouTube thành công!", 100, "Sẵn sàng"))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda m=err_msg: self.lbl_yt_title.config(text=f"❌ Lỗi: {m}", fg=THEME["danger"]))
                self.root.after(0, lambda: self._update_status("Không thể lấy thông tin YouTube", 0, "❌ Lỗi"))
            finally:
                self.root.after(0, lambda: self.btn_check_yt.config(state="normal", text="🔍 Kiểm Tra Link"))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_single_video_ui(self, title_text):
        self.playlist_frame.pack_forget()
        self.lbl_yt_title.config(text=title_text, fg=THEME["text_main"])
        self.btn_download_yt.config(text="⬇️  BẮT ĐẦU TẢI VIDEO", state="normal", bg=THEME["accent"])

    def _show_playlist_ui(self, title_text, entries):
        self.lbl_yt_title.config(text=title_text, fg=THEME["accent"])
        self.playlist_frame.pack(fill="both", expand=True, pady=(0, 6))

        # Clear existing items
        for child in self.pl_items_frame.winfo_children():
            child.destroy()

        self.playlist_check_vars = []

        for idx, entry in enumerate(entries, 1):
            var = tk.BooleanVar(value=True)
            self.playlist_check_vars.append(var)

            dur = entry.get("duration", 0)
            dur_str = f"{dur//60:02d}:{dur%60:02d}" if dur else ""
            t = entry.get("title", "No Title")
            up = entry.get("uploader", "")

            label_text = f"{idx:02d}. {t}"
            if dur_str:
                label_text += f" [{dur_str}]"
            if up:
                label_text += f" — {up}"

            cb_row = tk.Frame(self.pl_items_frame, bg=THEME["bg_card_inner"])
            cb_row.pack(fill="x", padx=4, pady=2)

            cb = tk.Checkbutton(
                cb_row,
                text=label_text,
                variable=var,
                font=(self.font_family, 9),
                fg=THEME["text_main"],
                bg=THEME["bg_card_inner"],
                selectcolor=THEME["bg_sidebar"],
                activebackground=THEME["bg_card_inner"],
                activeforeground=THEME["accent"],
                anchor="w",
                command=self._on_playlist_check_changed,
            )
            cb.pack(side="left", fill="x", expand=True)

        self._on_playlist_check_changed()

    def _select_all_playlist(self):
        for var in self.playlist_check_vars:
            var.set(True)
        self._on_playlist_check_changed()

    def _deselect_all_playlist(self):
        for var in self.playlist_check_vars:
            var.set(False)
        self._on_playlist_check_changed()

    def _on_playlist_check_changed(self):
        selected_count = sum(1 for v in self.playlist_check_vars if v.get())
        total = len(self.playlist_check_vars)
        self.lbl_pl_selected_count.config(text=f"Đã chọn: {selected_count}/{total} video")
        if selected_count > 0:
            self.btn_download_yt.config(
                text=f"⬇️  TẢI CÁC VIDEO ĐÃ CHỌN ({selected_count} video)",
                state="normal",
                bg=THEME["accent"],
            )
        else:
            self.btn_download_yt.config(
                text="⬇️  CHƯA CHỌN VIDEO NÀO",
                state="disabled",
                bg=THEME["bg_hover"],
            )

    def _stop_youtube_download(self):
        if self.is_processing:
            self.stop_requested = True
            self.btn_stop_yt.config(text="⏳ ĐANG DỪNG...", state="disabled")
            self._update_status("🛑 Đang dừng tiến trình tải video...", None, "Đang dừng...")

    def _start_youtube_download(self):
        if self.is_processing:
            messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang chạy, vui lòng chờ!")
            return

        url = self.yt_url_var.get().strip()
        if not url:
            messagebox.showwarning("Thiếu URL", "Vui lòng nhập link YouTube!")
            return

        raw_val = self.yt_format_var.get()
        if ":" in raw_val:
            fmt, quality = raw_val.split(":", 1)
        else:
            fmt, quality = "mp4", "best"

        out_dir = self.output_dir_var.get()
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # Determine target download list (playlist vs single)
        if self.current_playlist and self.current_playlist.get("is_playlist"):
            selected_items = [
                entry for entry, var in zip(self.current_playlist["entries"], self.playlist_check_vars)
                if var.get()
            ]
            if not selected_items:
                messagebox.showwarning("Chưa chọn video", "Vui lòng tick chọn ít nhất 1 video trong danh sách để tải!")
                return
        else:
            selected_items = [{"title": "Video YouTube", "url": url}]

        # Prepare state & visual feedback
        self.is_processing = True
        self.stop_requested = False

        self.btn_download_yt.config(text="⏳  ĐANG TẢI XUỐNG...", bg="#374151", state="disabled")
        self.btn_stop_yt.config(text="🛑  DỪNG TẢI (STOP)", bg=THEME["danger"], fg="#ffffff", state="normal")
        self._update_status(f"⏳ Chuẩn bị tải {len(selected_items)} video...", 2, "Bắt đầu...")

        def _worker():
            total = len(selected_items)
            success = 0
            errors = []
            was_stopped = False

            for i, item in enumerate(selected_items):
                if self.stop_requested:
                    break

                v_url = item.get("url") or url
                v_title = item.get("title") or "video"

                def _progress(percent, speed, eta, idx=i, t=total, vt=v_title):
                    overall = ((idx + (percent / 100)) / t) * 100
                    self.root.after(0, lambda p=overall, sp=speed, et=eta, cur=idx+1, ttl=t: self._update_status(
                        f"Đang tải ({cur}/{ttl}): {vt[:35]}...",
                        p,
                        f"⚡ {sp}  |  ⏱️ {et}",
                    ))

                try:
                    download_youtube(
                        url=v_url,
                        output_dir=out_dir,
                        format_type=fmt,
                        quality=quality,
                        progress_callback=_progress,
                        cancel_check=lambda: self.stop_requested,
                    )
                    success += 1
                except Exception as ex:
                    if self.stop_requested or "dừng" in str(ex).lower() or "cancel" in str(ex).lower():
                        was_stopped = True
                        break
                    errors.append(f"{v_title[:40]}: {ex}")

            self.is_processing = False
            was_stopped = was_stopped or self.stop_requested
            self.stop_requested = False

            # Restore button states
            self.root.after(0, lambda: self.btn_download_yt.config(
                text="⬇️  BẮT ĐẦU TẢI YOUTUBE" if not self.current_playlist or not self.current_playlist.get("is_playlist") else f"⬇️  TẢI CÁC VIDEO ĐÃ CHỌN ({len(selected_items)} video)",
                bg=THEME["accent"],
                state="normal",
            ))
            self.root.after(0, lambda: self.btn_stop_yt.config(
                text="🛑  DỪNG TẢI (STOP)",
                bg=THEME["bg_card_inner"],
                fg=THEME["text_dim"],
                state="disabled",
            ))

            if was_stopped:
                self.root.after(0, lambda s=success, t=total: self._update_status(f"🛑 Đã dừng tải! ({s}/{t} video hoàn thành)", 0, "Đã dừng"))
                self.root.after(100, lambda s=success, t=total: messagebox.showinfo("Đã Dừng", f"Đã dừng tải theo yêu cầu!\nĐã tải xong: {s}/{t} video."))
            else:
                self.root.after(0, lambda s=success, t=total: self._update_status("Tải YouTube hoàn tất!", 100, f"✅ {s}/{t}"))
                msg = f"Đã tải thành công {success}/{total} video vào thư mục đầu ra!"
                if errors:
                    msg += "\n\n❌ Lỗi:\n" + "\n".join(errors[:4])
                self.root.after(100, lambda m=msg: messagebox.showinfo("Kết quả", m))

        threading.Thread(target=_worker, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 5: URL IMAGE DOWNLOADER
    # ══════════════════════════════════════════════════════════════════════════
    def _render_image_dl_page(self):
        container = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        container.pack(fill="both", expand=True)

        # Header card
        t_card = tk.Frame(container, bg=THEME["bg_card"], padx=16, pady=12)
        t_card.pack(fill="x", pady=(0, 10))

        lbl_t = tk.Label(
            t_card,
            text="🌐 Tải Ảnh Hàng Loạt Từ URL Trực Tiếp",
            font=(self.font_family, 13, "bold"),
            fg=THEME["text_main"],
            bg=THEME["bg_card"],
        )
        lbl_t.pack(anchor="w")

        lbl_sub = tk.Label(
            t_card,
            text="Dán một hoặc nhiều link ảnh trực tiếp (mỗi link 1 dòng) để tải tự động về máy",
            font=(self.font_family, 9),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Main text box card
        body_card = tk.Frame(container, bg=THEME["bg_card"], padx=16, pady=12)
        body_card.pack(fill="both", expand=True)

        row_btn = tk.Frame(body_card, bg=THEME["bg_card"])
        row_btn.pack(fill="x", pady=(0, 8))

        lbl_hint = tk.Label(
            row_btn,
            text="🔗 Danh sách link ảnh (mỗi dòng 1 URL):",
            font=(self.font_family, 10, "bold"),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        lbl_hint.pack(side="left")

        btn_paste_all = tk.Button(
            row_btn,
            text="📋 Dán Clipboard",
            font=(self.font_family, 9),
            bg=THEME["bg_hover"],
            fg=THEME["text_main"],
            activebackground=THEME["primary"],
            activeforeground="#fff",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._paste_image_urls,
        )
        btn_paste_all.pack(side="right", padx=(6, 0))

        btn_clear_txt = tk.Button(
            row_btn,
            text="Xóa Hết",
            font=(self.font_family, 9),
            bg=THEME["bg_hover"],
            fg=THEME["text_muted"],
            activebackground=THEME["danger"],
            activeforeground="#fff",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: self.txt_urls.delete("1.0", tk.END),
        )
        btn_clear_txt.pack(side="right")

        # Multiline text input
        text_frame = tk.Frame(body_card, bg=THEME["bg_card_inner"])
        text_frame.pack(fill="both", expand=True, pady=(0, 10))

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", style="Vertical.TScrollbar")
        self.txt_urls = tk.Text(
            text_frame,
            font=("Consolas", 10),
            bg=THEME["bg_card_inner"],
            fg=THEME["text_main"],
            insertbackground=THEME["text_main"],
            relief="flat",
            bd=6,
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.txt_urls.yview)

        self.txt_urls.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bottom action row
        act_row = tk.Frame(body_card, bg=THEME["bg_card"])
        act_row.pack(fill="x")

        self.btn_download_imgs = tk.Button(
            act_row,
            text="⬇️  BẮT ĐẦU TẢI TẤT CẢ ẢNH",
            font=(self.font_family, 11, "bold"),
            bg=THEME["success"],
            fg="#fff",
            activebackground="#059669",
            activeforeground="#fff",
            relief="flat",
            padx=24,
            pady=10,
            cursor="hand2",
            command=self._start_image_urls_download,
        )
        self.btn_download_imgs.pack(side="left")

    def _paste_image_urls(self):
        try:
            txt = self.root.clipboard_get()
            if txt:
                self.txt_urls.insert(tk.END, ("\n" if self.txt_urls.get("1.0", tk.END).strip() else "") + txt.strip())
        except Exception:
            pass

    def _start_image_urls_download(self):
        if self.is_processing:
            messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang chạy, vui lòng chờ!")
            return

        raw_text = self.txt_urls.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showwarning("Chưa có link", "Vui lòng nhập ít nhất 1 link ảnh!")
            return

        urls = [line.strip() for line in raw_text.splitlines() if line.strip() and line.strip().startswith("http")]
        if not urls:
            messagebox.showwarning("Link không hợp lệ", "Không tìm thấy URL hợp lệ nào (bắt đầu bằng http/https)!")
            return

        out_dir = self.output_dir_var.get()
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # Instant visual feedback
        self.btn_download_imgs.config(text="⏳  ĐANG TẢI ẢNH...", bg="#374151", state="disabled")
        self._update_status(f"⏳ Bắt đầu tải {len(urls)} ảnh...", 2, "Đang xử lý...")

        def _worker():
            self.is_processing = True
            total = len(urls)
            success = 0
            errors = []

            for i, u in enumerate(urls):
                self.root.after(0, lambda i=i, url_curr=u: self._update_status(
                    f"Đang tải ảnh ({i+1}/{total}): {url_curr[:40]}...",
                    (i / total) * 100,
                    f"{i+1}/{total}",
                ))
                try:
                    download_image(u, output_dir=out_dir)
                    success += 1
                except Exception as ex:
                    errors.append(f"{u[:50]}...: {ex}")

            self.is_processing = False
            self.root.after(0, lambda: self.btn_download_imgs.config(text="⬇️  BẮT ĐẦU TẢI TẤT CẢ ẢNH", bg=THEME["success"], state="normal"))
            self.root.after(0, lambda s=success, t=total: self._update_status("Tải ảnh hoàn tất!", 100, f"✅ {s}/{t}"))

            msg = f"Đã tải thành công {success}/{total} ảnh vào thư mục đầu ra!"
            if errors:
                msg += "\n\n❌ Lỗi:\n" + "\n".join(errors[:4])
            self.root.after(100, lambda m=msg: messagebox.showinfo("Kết quả tải ảnh", m))

        threading.Thread(target=_worker, daemon=True).start()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = StudioToolkitApp()
    app.run()
