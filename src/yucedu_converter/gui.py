"""YUCEdu 离线转换器正式版图形界面。"""

from __future__ import annotations

import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import APP_NAME, APP_VERSION, VERIFIED_PROFILE_KEY
from .converter import (
    SUPPORTED_VIDEO_EXTENSIONS,
    ConversionCancelled,
    ConversionError,
    ConversionOptions,
    ConversionProgress,
    ConversionResult,
    convert_file,
    parse_key,
)
from .player import open_folder, play_media, play_protected_media, reveal_file
from .settings import AppSettings, load_settings, log_path, resource_path, save_settings
from .theme import COLORS, FONT_SECTION, FONT_SMALL, FONT_SUBTITLE, FONT_TITLE, FONT_UI, apply_theme


TERMINAL_STATES = {"已完成", "转换失败", "已取消", "已跳过"}
RETRY_STATES = {"等待中", "转换失败", "已取消", "已跳过"}
VIDEO_PATTERN = " ".join(f"*{extension}" for extension in sorted(SUPPORTED_VIDEO_EXTENSIONS))

ERROR_MESSAGES = {
    "input_missing": "源文件已移动或删除，请重新添加。",
    "invalid_key": "转换配置填写有误，请检查高级设置。",
    "key_mismatch_or_protected_branch": "该文件与当前转换配置不匹配。",
    "invalid_mp4": "文件不完整、已损坏，或与当前转换配置不匹配。",
    "unsupported_media": "转换结果不是当前版本支持的 MP4 格式。",
    "disk_full": "输出磁盘剩余空间不足，请更换输出位置。",
    "write_denied": "当前输出位置没有写入权限，请更换文件夹。",
    "output_exists": "输出文件已经存在，请调整同名文件处理方式。",
    "same_path": "输入文件和输出文件不能是同一个文件。",
    "missing_component": "程序文件不完整，请重新解压正式交付包。",
    "component_invalid": "程序组件校验失败，请重新解压正式交付包。",
    "component_read_error": "程序组件读取失败，请检查文件权限。",
    "missing_trailer": "缺少 YUCEdu 兼容组件，请重新解压正式交付包。",
    "trailer_invalid": "YUCEdu 兼容组件校验失败，请重新解压正式交付包。",
    "trailer_read_error": "YUCEdu 兼容组件读取失败，请检查文件权限。",
    "unsupported_input": "请选择受支持的常见视频格式。",
    "empty_input": "输入视频是空文件。",
    "encrypt_size_mismatch": "加密结果长度校验失败。",
    "io_error": "文件读写失败，请检查磁盘、文件权限或文件是否被占用。",
    "cancelled": "任务已经取消。",
}


@dataclass
class TaskRecord:
    iid: str
    source: Path
    planned_output: Path
    size: int
    mode: str = "decrypt"
    status: str = "等待中"
    progress: float = 0.0
    processed: int = 0
    actual_output: Path | None = None
    error_code: str = ""
    error_message: str = ""
    started_at: float = 0.0


def format_size(size: int | float) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def normalized_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


class ModernScrollbar(tk.Canvas):
    """无箭头、无立体边框，并在内容完全可见时自动隐藏。"""

    def __init__(self, master: tk.Misc, *, orient: str, command) -> None:
        self.orient = orient
        self.command = command
        size = {"width": 10} if orient == tk.VERTICAL else {"height": 10}
        super().__init__(
            master,
            background=COLORS["card"],
            highlightthickness=0,
            borderwidth=0,
            relief=tk.FLAT,
            cursor="hand2",
            **size,
        )
        self.first = 0.0
        self.last = 1.0
        self.thumb_start = 0.0
        self.thumb_end = 0.0
        self.drag_offset = 0.0
        self.hovered = False
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)

    def set(self, first: str, last: str) -> None:
        self.first = max(0.0, min(1.0, float(first)))
        self.last = max(self.first, min(1.0, float(last)))
        if self.first <= 0.0 and self.last >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            self.after_idle(self._draw)

    def _axis_length(self) -> float:
        return float(self.winfo_height() if self.orient == tk.VERTICAL else self.winfo_width())

    def _event_position(self, event: tk.Event) -> float:
        return float(event.y if self.orient == tk.VERTICAL else event.x)

    def _draw(self) -> None:
        self.delete("all")
        length = self._axis_length()
        if length <= 6 or (self.first <= 0.0 and self.last >= 1.0):
            return
        margin = 2.0
        track = max(1.0, length - margin * 2)
        start = margin + self.first * track
        end = margin + self.last * track
        minimum = min(24.0, track)
        if end - start < minimum:
            end = min(margin + track, start + minimum)
            start = max(margin, end - minimum)
        self.thumb_start = start
        self.thumb_end = end
        color = "#8D9DAF" if self.hovered else "#B7C3D1"
        if self.orient == tk.VERTICAL:
            x = max(3.0, self.winfo_width() / 2)
            self.create_line(x, start + 3, x, end - 3, fill=color, width=6, capstyle=tk.ROUND)
        else:
            y = max(3.0, self.winfo_height() / 2)
            self.create_line(start + 3, y, end - 3, y, fill=color, width=6, capstyle=tk.ROUND)

    def _move_thumb_to(self, start: float) -> None:
        length = self._axis_length()
        margin = 2.0
        track = max(1.0, length - margin * 2)
        thumb = max(0.0, self.thumb_end - self.thumb_start)
        start = max(margin, min(margin + track - thumb, start))
        self.command("moveto", (start - margin) / track)

    def _on_press(self, event: tk.Event) -> None:
        position = self._event_position(event)
        if self.thumb_start <= position <= self.thumb_end:
            self.drag_offset = position - self.thumb_start
        else:
            thumb = self.thumb_end - self.thumb_start
            self.drag_offset = thumb / 2
            self._move_thumb_to(position - self.drag_offset)

    def _on_drag(self, event: tk.Event) -> None:
        self._move_thumb_to(self._event_position(event) - self.drag_offset)

    def _on_enter(self, _event: tk.Event) -> None:
        self.hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self.hovered = False
        self._draw()


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1080x780")
        self.minsize(900, 680)
        self.configure(background=COLORS["window"])
        self._center_window(1080, 780)
        self._app_icon = self._create_app_icon()
        self.iconphoto(True, self._app_icon)
        if sys.platform == "win32":
            try:
                self.iconbitmap(default=str(resource_path("app.ico")))
            except tk.TclError:
                pass
        apply_theme(self)

        self.settings: AppSettings = load_settings()
        self.mode = "decrypt"
        self.profile_key_text = VERIFIED_PROFILE_KEY
        self.profile_key_is_hex = False
        self.table_path = resource_path("aes_tail_table.bin")
        self.trailer_path = resource_path("compatibility_trailer.bin")
        self.tasks: dict[str, TaskRecord] = {}
        self.input_index: set[str] = set()
        self.task_counter = 0
        self.events: queue.Queue[tuple] = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.running = False
        self.close_when_done = False
        self.batch_ids: list[str] = []
        self.active_task_id: str | None = None
        self.last_success_path: Path | None = None
        self.logger = self._build_logger()

        # 输出位置由用户在每次启动后主动选择，不沿用历史目录。
        self.session_output_dirs = {"decrypt": "", "encrypt": ""}
        self.output_dir_var = tk.StringVar(value="")
        self.output_display_var = tk.StringVar(value="尚未选择，请点击“选择文件夹”")
        self.auto_play_var = tk.BooleanVar(value=self.settings.auto_play)
        self.auto_open_var = tk.BooleanVar(value=self.settings.auto_open_folder)
        self.task_summary_var = tk.StringVar(value="共 0 个 · 0 B")
        self.current_title_var = tk.StringVar(value="尚未开始转换")
        self.current_percent_var = tk.StringVar(value="0%")
        self.current_detail_var = tk.StringVar(value="添加文件后点击“开始转换”")
        self.speed_var = tk.StringVar(value="速度 --")
        self.overall_var = tk.StringVar(value="总进度 0/0")
        self.status_var = tk.StringVar(value="就绪")
        self.header_subtitle_var = tk.StringVar(value="解密 YUCEdu，或把普通视频加密为 YUCEdu")
        self.empty_title_var = tk.StringVar(value="还没有待解密文件")
        self.empty_hint_var = tk.StringVar(value="请选择一个或多个 .yucedu 文件")

        self._build_ui()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self._drain_events)
        self.logger.info("程序启动，版本 %s，资源表 %s", APP_VERSION, self.table_path)

    def _build_logger(self) -> logging.Logger:
        logger = logging.getLogger("yucedu_converter")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            try:
                handler = logging.FileHandler(log_path(), encoding="utf-8")
                handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
                logger.addHandler(handler)
            except OSError:
                logger.addHandler(logging.NullHandler())
        return logger

    def _center_window(self, width: int, height: int) -> None:
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _create_app_icon(self) -> tk.PhotoImage:
        icon = tk.PhotoImage(width=32, height=32)
        icon.put(COLORS["blue"], to=(0, 0, 32, 32))
        for x in range(10, 23):
            half = (x - 10) // 2
            y0 = 16 - half
            y1 = 16 + half + 1
            icon.put("#FFFFFF", to=(x, y0, x + 1, y1))
        return icon

    def _build_ui(self) -> None:
        self._build_header()

        body = ttk.Frame(self, style="App.TFrame", padding=(24, 18, 24, 18))
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_task_card(body)
        self._build_progress_card(body)
        self._build_action_card(body)

    def _build_header(self) -> None:
        header = tk.Frame(self, background=COLORS["navy"], height=94)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        header.columnconfigure(1, weight=1)

        logo = tk.Canvas(header, width=50, height=50, background=COLORS["navy"], highlightthickness=0)
        logo.grid(row=0, column=0, rowspan=2, padx=(24, 14), pady=22)
        logo.create_oval(2, 2, 48, 48, fill=COLORS["blue"], outline="")
        logo.create_polygon(19, 14, 19, 36, 36, 25, fill="#FFFFFF", outline="")

        tk.Label(
            header,
            text=APP_NAME,
            background=COLORS["navy"],
            foreground="#FFFFFF",
            font=FONT_TITLE,
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(18, 0))
        tk.Label(
            header,
            textvariable=self.header_subtitle_var,
            background=COLORS["navy"],
            foreground="#BFD2E4",
            font=FONT_SUBTITLE,
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", pady=(2, 17))

        link_style = {
            "background": COLORS["navy"],
            "foreground": "#DCE8F3",
            "activebackground": COLORS["navy_light"],
            "activeforeground": "#FFFFFF",
            "relief": tk.FLAT,
            "borderwidth": 0,
            "font": FONT_UI,
            "cursor": "hand2",
            "padx": 13,
            "pady": 9,
        }
        self.help_button = tk.Button(header, text="使用说明", command=self._show_help, **link_style)
        self.help_button.grid(row=0, column=2, rowspan=2, padx=(0, 2))
        self.settings_button = tk.Button(header, text="设置", command=self._open_settings, **link_style)
        self.settings_button.grid(row=0, column=3, rowspan=2, padx=(0, 20))

    def _build_task_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(4, weight=1)

        title_row = ttk.Frame(card, style="CardInner.TFrame")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.columnconfigure(0, weight=1)
        ttk.Label(title_row, text="转换任务", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(title_row, textvariable=self.task_summary_var, style="Muted.TLabel").grid(row=0, column=1, sticky="e")

        mode_shell = tk.Frame(card, background=COLORS["border"], padx=1, pady=1)
        mode_shell.grid(row=1, column=0, sticky="w", pady=(12, 4))
        mode_button_options = {
            "relief": tk.FLAT,
            "borderwidth": 0,
            "font": ("Microsoft YaHei UI", 10, "bold"),
            "cursor": "hand2",
            "width": 24,
            "pady": 9,
        }
        self.decrypt_mode_button = tk.Button(
            mode_shell,
            text="解密 YUCEdu → 视频",
            command=lambda: self._switch_mode("decrypt"),
            **mode_button_options,
        )
        self.decrypt_mode_button.pack(side=tk.LEFT)
        self.encrypt_mode_button = tk.Button(
            mode_shell,
            text="加密视频 → YUCEdu",
            command=lambda: self._switch_mode("encrypt"),
            **mode_button_options,
        )
        self.encrypt_mode_button.pack(side=tk.LEFT)
        self._refresh_mode_buttons()

        output_shell = tk.Frame(
            card,
            background="#F8FAFD",
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["blue"],
            highlightthickness=1,
            padx=12,
            pady=9,
        )
        output_shell.grid(row=2, column=0, sticky="ew", pady=(10, 2))
        output_shell.columnconfigure(1, weight=1)
        tk.Label(
            output_shell,
            text="输出文件夹",
            background="#F8FAFD",
            foreground=COLORS["text"],
            font=("Microsoft YaHei UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 14))
        self.output_path_label = tk.Label(
            output_shell,
            textvariable=self.output_display_var,
            background="#F8FAFD",
            foreground=COLORS["muted"],
            font=FONT_UI,
            anchor="w",
        )
        self.output_path_label.grid(row=0, column=1, sticky="ew")
        self.change_output_button = ttk.Button(
            output_shell,
            text="选择文件夹",
            style="Secondary.TButton",
            command=self._change_output_dir,
        )
        self.change_output_button.grid(row=0, column=2, padx=(12, 6))
        self.open_output_button = ttk.Button(
            output_shell,
            text="打开",
            style="Secondary.TButton",
            command=self._open_output_dir,
            state=tk.DISABLED,
        )
        self.open_output_button.grid(row=0, column=3)

        toolbar = ttk.Frame(card, style="CardInner.TFrame")
        toolbar.grid(row=3, column=0, sticky="ew", pady=(8, 12))
        self.add_file_button = ttk.Button(toolbar, text="添加文件", style="Secondary.TButton", command=self._choose_files)
        self.add_file_button.pack(side=tk.LEFT, padx=(0, 8))
        self.add_folder_button = ttk.Button(toolbar, text="添加文件夹", style="Secondary.TButton", command=self._choose_folder)
        self.add_folder_button.pack(side=tk.LEFT, padx=(0, 8))
        self.remove_button = ttk.Button(toolbar, text="移除所选", style="Secondary.TButton", command=self._remove_selected)
        self.remove_button.pack(side=tk.LEFT, padx=(0, 8))
        self.clear_button = ttk.Button(toolbar, text="清空列表", style="Secondary.TButton", command=self._clear_tasks)
        self.clear_button.pack(side=tk.LEFT)

        table_shell = tk.Frame(card, background=COLORS["border"], padx=1, pady=1)
        table_shell.grid(row=4, column=0, sticky="nsew")
        table_shell.columnconfigure(0, weight=1)
        table_shell.rowconfigure(0, weight=1)

        columns = ("name", "size", "status", "progress", "output")
        self.tree = ttk.Treeview(table_shell, columns=columns, show="headings", selectmode="extended")
        headings = {
            "name": "文件名",
            "size": "大小",
            "status": "状态",
            "progress": "进度",
            "output": "输出文件",
        }
        for column, text in headings.items():
            self.tree.heading(column, text=text, anchor="w")
        self.tree.column("name", width=300, minwidth=200, stretch=True, anchor="w")
        self.tree.column("size", width=90, minwidth=78, stretch=False, anchor="e")
        self.tree.column("status", width=100, minwidth=90, stretch=False, anchor="center")
        self.tree.column("progress", width=76, minwidth=68, stretch=False, anchor="center")
        self.tree.column("output", width=250, minwidth=150, stretch=True, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vertical_scrollbar = ModernScrollbar(
            table_shell,
            orient=tk.VERTICAL,
            command=self.tree.yview,
        )
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns", padx=(3, 1), pady=3)
        self.horizontal_scrollbar = ModernScrollbar(
            table_shell,
            orient=tk.HORIZONTAL,
            command=self.tree.xview,
        )
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew", padx=3, pady=(3, 1))
        self.tree.configure(
            yscrollcommand=self.vertical_scrollbar.set,
            xscrollcommand=self.horizontal_scrollbar.set,
        )
        self.tree.tag_configure("success", foreground=COLORS["success"])
        self.tree.tag_configure("error", foreground=COLORS["danger"])
        self.tree.tag_configure("warning", foreground=COLORS["warning"])
        self.tree.tag_configure("active", foreground=COLORS["blue"])

        self.empty_panel = tk.Frame(table_shell, background=COLORS["card"])
        tk.Label(
            self.empty_panel,
            textvariable=self.empty_title_var,
            background=COLORS["card"],
            foreground=COLORS["text"],
            font=FONT_SECTION,
        ).pack(pady=(0, 5))
        tk.Label(
            self.empty_panel,
            textvariable=self.empty_hint_var,
            background=COLORS["card"],
            foreground=COLORS["muted"],
            font=FONT_UI,
        ).pack()
        self.empty_panel.place(relx=0.5, rely=0.64, anchor="center")

        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._show_context_menu)
        if sys.platform == "darwin":
            self.tree.bind("<Button-2>", self._show_context_menu)
            self.tree.bind("<Control-Button-1>", self._show_context_menu)
        self.context_menu = tk.Menu(self, tearoff=False)
        self.context_menu.add_command(label="播放输出", command=self._play_selected)
        self.context_menu.add_command(label="打开输出位置", command=self._reveal_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="重试任务", command=self._retry_selected)
        self.context_menu.add_command(label="从列表移除", command=self._remove_selected)

    def _build_progress_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(16, 13))
        card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        card.columnconfigure(0, weight=1)

        current_header = ttk.Frame(card, style="CardInner.TFrame")
        current_header.grid(row=0, column=0, sticky="ew")
        current_header.columnconfigure(0, weight=1)
        ttk.Label(current_header, textvariable=self.current_title_var, style="Card.TLabel", font=FONT_SECTION).grid(row=0, column=0, sticky="w")
        ttk.Label(current_header, textvariable=self.current_percent_var, style="Status.TLabel").grid(row=0, column=1, sticky="e")
        self.current_progress = ttk.Progressbar(card, style="Current.Horizontal.TProgressbar", maximum=100, value=0)
        self.current_progress.grid(row=1, column=0, sticky="ew", pady=(8, 6))

        current_footer = ttk.Frame(card, style="CardInner.TFrame")
        current_footer.grid(row=2, column=0, sticky="ew")
        current_footer.columnconfigure(0, weight=1)
        ttk.Label(current_footer, textvariable=self.current_detail_var, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(current_footer, textvariable=self.speed_var, style="Muted.TLabel").grid(row=0, column=1, sticky="e")

        ttk.Separator(card).grid(row=3, column=0, sticky="ew", pady=10)
        overall_header = ttk.Frame(card, style="CardInner.TFrame")
        overall_header.grid(row=4, column=0, sticky="ew")
        overall_header.columnconfigure(0, weight=1)
        ttk.Label(overall_header, textvariable=self.overall_var, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.overall_percent_label = ttk.Label(overall_header, text="0%", style="Muted.TLabel")
        self.overall_percent_label.grid(row=0, column=1, sticky="e")
        self.overall_progress = ttk.Progressbar(card, style="Overall.Horizontal.TProgressbar", maximum=100, value=0)
        self.overall_progress.grid(row=5, column=0, sticky="ew", pady=(6, 0))

    def _build_action_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(16, 12))
        card.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        card.columnconfigure(1, weight=1)

        self.status_label = tk.Label(
            card,
            textvariable=self.status_var,
            background=COLORS["card"],
            foreground=COLORS["muted"],
            font=FONT_SMALL,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 18))

        options = ttk.Frame(card, style="CardInner.TFrame")
        options.grid(row=0, column=1, sticky="e")
        self.auto_play_check = ttk.Checkbutton(
            options,
            text="单个文件完成后播放",
            variable=self.auto_play_var,
            command=self._save_main_options,
        )
        self.auto_play_check.pack(side=tk.LEFT, padx=(0, 15))
        self.auto_open_check = ttk.Checkbutton(
            options,
            text="完成后打开目录",
            variable=self.auto_open_var,
            command=self._save_main_options,
        )
        self.auto_open_check.pack(side=tk.LEFT)

        self.cancel_button = ttk.Button(card, text="取消任务", style="Danger.TButton", command=self._cancel_conversion, state=tk.DISABLED)
        self.cancel_button.grid(row=0, column=2, padx=(18, 8))
        self.start_button = ttk.Button(card, text="开始转换", style="Primary.TButton", command=self._start_conversion, state=tk.DISABLED)
        self.start_button.grid(row=0, column=3)

    def _bind_shortcuts(self) -> None:
        modifier = "Command" if sys.platform == "darwin" else "Control"
        self.bind(f"<{modifier}-o>", lambda _event: self._choose_files())
        self.bind(f"<{modifier}-Shift-O>", lambda _event: self._choose_folder())
        self.bind("<Delete>", lambda _event: self._remove_selected())
        self.bind("<BackSpace>", lambda _event: self._remove_selected())
        self.bind(f"<{modifier}-Return>", lambda _event: self._start_conversion())

    def _refresh_mode_buttons(self) -> None:
        active = {
            "background": COLORS["blue"],
            "foreground": "#FFFFFF",
            "activebackground": COLORS["blue_hover"],
            "activeforeground": "#FFFFFF",
        }
        inactive = {
            "background": COLORS["card"],
            "foreground": COLORS["text"],
            "activebackground": COLORS["blue_soft"],
            "activeforeground": COLORS["text"],
        }
        self.decrypt_mode_button.configure(**(active if self.mode == "decrypt" else inactive))
        self.encrypt_mode_button.configure(**(active if self.mode == "encrypt" else inactive))

    def _sync_output_display(self) -> None:
        selected = self.output_dir_var.get().strip()
        if selected:
            self.output_display_var.set(selected)
            self.output_path_label.configure(foreground=COLORS["text"])
            self.open_output_button.configure(state=tk.NORMAL)
        else:
            self.output_display_var.set("尚未选择，请点击“选择文件夹”")
            self.output_path_label.configure(foreground=COLORS["muted"])
            self.open_output_button.configure(state=tk.DISABLED)
        self._refresh_summary()

    def _ensure_output_dir(self) -> bool:
        if self.output_dir_var.get().strip():
            return True
        self._set_notice("请先选择本次任务的输出文件夹。", "warning")
        return self._change_output_dir()

    def _switch_mode(self, mode: str) -> None:
        if self.running or mode == self.mode:
            return
        if self.tasks and not messagebox.askyesno(
            "切换转换模式",
            "切换模式会清空当前任务列表，源文件和已经生成的文件都会保留。\n\n是否继续？",
            parent=self,
        ):
            return
        self.session_output_dirs[self.mode] = self.output_dir_var.get().strip()
        if self.tasks:
            self._clear_tasks()
        self.mode = mode
        self.output_dir_var.set(self.session_output_dirs[mode])
        if mode == "decrypt":
            self.header_subtitle_var.set("把 YUCEdu 文件还原为普通视频")
            self.empty_title_var.set("还没有待解密文件")
            self.empty_hint_var.set("请选择一个或多个 .yucedu 文件")
            self.auto_play_check.configure(text="单个文件完成后播放")
            self.context_menu.entryconfigure(0, label="播放输出视频")
            notice = "已切换到解密模式。"
        else:
            self.header_subtitle_var.set("按原播放器算法把普通视频加密为 YUCEdu")
            self.empty_title_var.set("还没有待加密视频")
            self.empty_hint_var.set("请选择 MP4、MKV、AVI、MOV 等常见视频")
            self.auto_play_check.configure(text="单个文件完成后用原播放器打开")
            self.context_menu.entryconfigure(0, label="用原播放器打开")
            notice = "已切换到加密模式。"
        self._refresh_mode_buttons()
        self._sync_output_display()
        if not self.output_dir_var.get().strip():
            notice += " 请为当前模式选择输出文件夹。"
        self._set_notice(notice, "active")

    def _planned_output(self, source: Path, output_dir: Path | None = None) -> Path:
        destination = output_dir or Path(self.output_dir_var.get())
        if self.mode == "decrypt":
            return destination / f"{source.stem}.离线播放.mp4"
        return destination / f"{source.stem}.yucedu"

    def _valid_input_suffix(self, suffix: str) -> bool:
        if self.mode == "decrypt":
            return suffix.lower() == ".yucedu"
        return suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS

    def _choose_files(self) -> None:
        if self.running:
            return
        if not self._ensure_output_dir():
            return
        title = "选择一个或多个 .yucedu 文件" if self.mode == "decrypt" else "选择一个或多个普通视频"
        filetypes = (
            [("YUCEdu 文件", "*.yucedu"), ("所有文件", "*.*")]
            if self.mode == "decrypt"
            else [("常见视频", VIDEO_PATTERN), ("所有文件", "*.*")]
        )
        paths = filedialog.askopenfilenames(
            title=title,
            filetypes=filetypes,
            initialdir=str(Path.home()),
        )
        if paths:
            self._add_paths([Path(path) for path in paths])

    def _choose_folder(self) -> None:
        if self.running:
            return
        if not self._ensure_output_dir():
            return
        folder_title = "选择包含 .yucedu 文件的文件夹" if self.mode == "decrypt" else "选择包含普通视频的文件夹"
        folder = filedialog.askdirectory(title=folder_title, initialdir=str(Path.home()))
        if not folder:
            return
        found: list[Path] = []
        for root, _dirs, files in os.walk(folder):
            for filename in files:
                if self._valid_input_suffix(Path(filename).suffix):
                    found.append(Path(root) / filename)
        if not found:
            wanted = ".yucedu 文件" if self.mode == "decrypt" else "受支持的视频文件"
            messagebox.showinfo("没有找到文件", f"这个文件夹中没有找到{wanted}。", parent=self)
            return
        self._add_paths(sorted(found, key=lambda path: str(path).lower()))

    def _add_paths(self, paths: list[Path]) -> None:
        output_dir = Path(self.output_dir_var.get())
        added = 0
        duplicates = 0
        invalid = 0
        for source in paths:
            if not source.is_file() or not self._valid_input_suffix(source.suffix):
                invalid += 1
                continue
            normalized = normalized_path(source)
            if normalized in self.input_index:
                duplicates += 1
                continue
            self.task_counter += 1
            iid = f"task-{self.task_counter}"
            record = TaskRecord(
                iid=iid,
                source=source.resolve(),
                planned_output=self._planned_output(source, output_dir),
                size=source.stat().st_size,
                mode=self.mode,
            )
            self.tasks[iid] = record
            self.input_index.add(normalized)
            self.tree.insert("", tk.END, iid=iid)
            self._refresh_tree_row(record)
            added += 1

        if self.tasks:
            self.empty_panel.place_forget()
        self._refresh_summary()
        details = [f"已添加 {added} 个文件"]
        if duplicates:
            details.append(f"忽略 {duplicates} 个重复文件")
        if invalid:
            details.append(f"忽略 {invalid} 个无效文件")
        self._set_notice("，".join(details) + "。", "normal")

    def _remove_selected(self) -> None:
        if self.running:
            return
        selected = list(self.tree.selection())
        for iid in selected:
            task = self.tasks.pop(iid, None)
            if task is not None:
                self.input_index.discard(normalized_path(task.source))
            self.tree.delete(iid)
        if not self.tasks:
            self.empty_panel.place(relx=0.5, rely=0.64, anchor="center")
        self._refresh_summary()

    def _clear_tasks(self) -> None:
        if self.running or not self.tasks:
            return
        self.tasks.clear()
        self.input_index.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.empty_panel.place(relx=0.5, rely=0.64, anchor="center")
        self._reset_progress_display()
        self._refresh_summary()
        self._set_notice("任务列表已清空，源文件和已经生成的文件没有被删除。", "normal")

    def _retry_selected(self) -> None:
        if self.running:
            return
        for iid in self.tree.selection():
            task = self.tasks.get(iid)
            if task and task.status in TERMINAL_STATES and task.status != "已完成":
                task.status = "等待中"
                task.progress = 0
                task.processed = 0
                task.error_code = ""
                task.error_message = ""
                task.actual_output = None
                self._refresh_tree_row(task)
        self._refresh_summary()

    def _change_output_dir(self) -> bool:
        if self.running:
            return False
        chosen = filedialog.askdirectory(title="选择输出文件夹", initialdir=self.output_dir_var.get() or str(Path.home()))
        if not chosen:
            return False
        self.output_dir_var.set(chosen)
        self.session_output_dirs[self.mode] = chosen
        for task in self.tasks.values():
            if task.status != "已完成":
                task.planned_output = self._planned_output(task.source, Path(chosen))
                self._refresh_tree_row(task)
        self._sync_output_display()
        self._set_notice("已选择本次任务的输出文件夹。", "success")
        return True

    def _open_output_dir(self) -> None:
        if not self.output_dir_var.get().strip():
            self._change_output_dir()
            return
        try:
            open_folder(Path(self.output_dir_var.get()))
        except OSError as exc:
            messagebox.showerror("打开失败", str(exc), parent=self)

    def _start_conversion(self) -> None:
        if self.running:
            return
        candidates = [task for task in self.tasks.values() if task.status in RETRY_STATES]
        if not candidates:
            messagebox.showinfo("没有待转换任务", "请先添加文件，或选择失败任务后点击重试。", parent=self)
            return
        if not self._ensure_output_dir():
            return
        try:
            if self.profile_key_is_hex:
                key = parse_key(hex_key=self.profile_key_text)
            else:
                key = parse_key(ascii_key=self.profile_key_text)
        except ConversionError as exc:
            messagebox.showerror("转换配置错误", exc.message, parent=self)
            return

        output_dir = Path(self.output_dir_var.get()).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("输出位置不可用", f"无法创建输出文件夹：\n{exc}", parent=self)
            return

        if self.settings.existing_policy == "replace":
            existing = sum(self._planned_output(task.source, output_dir).exists() for task in candidates)
            if existing and not messagebox.askyesno(
                "确认覆盖",
                f"检测到 {existing} 个同名输出文件。继续后会覆盖这些文件，是否继续？",
                parent=self,
            ):
                return

        self.settings.auto_play = self.auto_play_var.get()
        self.settings.auto_open_folder = self.auto_open_var.get()
        self._save_settings_quietly()
        self.cancel_event.clear()
        self.batch_ids = [task.iid for task in candidates]
        self.last_success_path = None
        for task in candidates:
            task.status = "等待中"
            task.progress = 0
            task.processed = 0
            task.error_code = ""
            task.error_message = ""
            task.actual_output = None
            task.planned_output = self._planned_output(task.source, output_dir)
            task.mode = self.mode
            self._refresh_tree_row(task)

        policy = self.settings.existing_policy
        table_path = self.table_path
        trailer_path = self.trailer_path
        mode = self.mode
        snapshot = [(task.iid, task.source, task.planned_output, task.size) for task in candidates]
        self._set_running(True)
        action = "解密" if mode == "decrypt" else "加密"
        self._set_notice(f"正在{action} {len(candidates)} 个文件，请保持程序窗口打开。", "active")
        self.worker = threading.Thread(
            target=self._conversion_worker,
            args=(snapshot, key, table_path, trailer_path, policy, mode),
            daemon=True,
        )
        self.worker.start()

    def _conversion_worker(
        self,
        tasks: list[tuple[str, Path, Path, int]],
        key: bytes,
        table_path: Path,
        trailer_path: Path,
        policy: str,
        mode: str,
    ) -> None:
        success = 0
        failed = 0
        cancelled = 0
        for index, (iid, source, output, _size) in enumerate(tasks):
            if self.cancel_event.is_set():
                for remaining_iid, *_rest in tasks[index:]:
                    self.events.put(("cancelled", remaining_iid))
                    cancelled += 1
                break
            self.events.put(("state", iid, "准备中"))

            def progress_callback(progress: ConversionProgress, task_iid: str = iid) -> None:
                self.events.put(("progress", task_iid, progress))

            try:
                result = convert_file(
                    ConversionOptions(
                        input_path=source,
                        output_path=output,
                        key=key,
                        table_path=table_path,
                        trailer_path=trailer_path,
                        mode=mode,  # type: ignore[arg-type]
                        existing_policy=policy,  # type: ignore[arg-type]
                    ),
                    progress_callback=progress_callback,
                    cancel_check=self.cancel_event.is_set,
                )
            except ConversionCancelled:
                self.events.put(("cancelled", iid))
                cancelled += 1
                for remaining_iid, *_rest in tasks[index + 1 :]:
                    self.events.put(("cancelled", remaining_iid))
                    cancelled += 1
                break
            except ConversionError as exc:
                self.events.put(("error", iid, exc.code, exc.message))
                failed += 1
            except Exception as exc:
                self.events.put(("error", iid, "unexpected", repr(exc)))
                failed += 1
            else:
                self.events.put(("success", iid, result))
                success += 1
        self.events.put(("batch_done", success, failed, cancelled))

    def _cancel_conversion(self) -> None:
        if not self.running:
            return
        self.cancel_event.set()
        self.cancel_button.configure(text="正在取消…", state=tk.DISABLED)
        self._set_notice("正在停止当前任务并清理临时文件……", "warning")

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        try:
            if self.winfo_exists():
                self.after(80, self._drain_events)
        except tk.TclError:
            pass

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]
        if kind == "state":
            _, iid, status = event
            task = self.tasks.get(iid)
            if task:
                task.status = status
                task.started_at = time.monotonic()
                self.active_task_id = iid
                self.current_title_var.set(task.source.name)
                self.current_detail_var.set("正在准备转换……")
                self._refresh_tree_row(task)
        elif kind == "progress":
            _, iid, progress = event
            self._handle_progress(iid, progress)
        elif kind == "success":
            _, iid, result = event
            self._handle_success(iid, result)
        elif kind == "error":
            _, iid, code, detail = event
            self._handle_error(iid, code, detail)
        elif kind == "cancelled":
            _, iid = event
            task = self.tasks.get(iid)
            if task:
                task.status = "已取消"
                task.error_code = "cancelled"
                task.error_message = "任务已经取消。"
                self._refresh_tree_row(task)
        elif kind == "batch_done":
            _, success, failed, cancelled = event
            self._finish_batch(success, failed, cancelled)
            if self.close_when_done:
                return
        self._update_overall_progress()
        self._refresh_summary()

    def _handle_progress(self, iid: str, progress: ConversionProgress) -> None:
        task = self.tasks.get(iid)
        if task is None:
            return
        self.active_task_id = iid
        task.progress = progress.percent
        task.processed = progress.processed
        phase_names = {
            "preparing": "准备中",
            "transforming": "解密中" if task.mode == "decrypt" else "加密中",
            "validating": "正在校验",
            "committing": "正在保存",
            "done": "已完成",
        }
        task.status = phase_names.get(progress.phase, task.status)
        self.current_title_var.set(task.source.name)
        self.current_percent_var.set(f"{progress.percent:.0f}%")
        self.current_progress["value"] = progress.percent
        if progress.phase == "transforming":
            self.current_detail_var.set(f"已处理 {format_size(progress.processed)} / {format_size(progress.total)}")
        elif progress.phase == "validating":
            if task.mode == "decrypt":
                self.current_detail_var.set("正在识别视频格式并校验媒体结构……")
            else:
                self.current_detail_var.set("正在校验加密主体和 YUCEdu 兼容尾部……")
        elif progress.phase == "committing":
            target_name = "普通视频" if task.mode == "decrypt" else "YUCEdu 文件"
            self.current_detail_var.set(f"校验通过，正在保存{target_name}……")
        elapsed = max(0.001, time.monotonic() - task.started_at)
        speed = progress.processed / elapsed
        self.speed_var.set(f"速度 {format_size(speed)}/s" if progress.processed else "速度 --")
        self._refresh_tree_row(task)

    def _handle_success(self, iid: str, result: ConversionResult) -> None:
        task = self.tasks.get(iid)
        if task is None:
            return
        task.status = "已完成"
        task.progress = 100
        task.processed = task.size
        task.actual_output = result.output_path
        task.error_code = ""
        task.error_message = ""
        self.last_success_path = result.output_path
        self.current_title_var.set(task.source.name)
        self.current_percent_var.set("100%")
        self.current_progress["value"] = 100
        if result.mode == "decrypt":
            self.current_detail_var.set(
                f"已还原 {format_size(result.output_size)}，识别兼容尾部 {format_size(result.compatibility_trailer_bytes)}"
            )
        else:
            self.current_detail_var.set(
                f"已加密 {format_size(result.output_size)}，写入兼容尾部 {format_size(result.compatibility_trailer_bytes)}"
            )
        self.logger.info(
            "转换成功 input=%s output=%s size=%s sha256=%s boxes=%s",
            result.input_path,
            result.output_path,
            result.output_size,
            result.output_sha256,
            "/".join(result.boxes),
        )
        self._refresh_tree_row(task)

    def _handle_error(self, iid: str, code: str, detail: str) -> None:
        task = self.tasks.get(iid)
        if task is None:
            return
        friendly = ERROR_MESSAGES.get(code, "转换过程中发生异常，请查看任务详情。")
        task.status = "转换失败"
        task.error_code = code
        task.error_message = f"{friendly}\n\n技术详情：{detail}"
        self.current_title_var.set(task.source.name)
        self.current_detail_var.set(friendly)
        self._set_notice(f"{task.source.name}：{friendly}", "error")
        self.logger.error("转换失败 input=%s code=%s detail=%s", task.source, code, detail)
        self._refresh_tree_row(task)

    def _finish_batch(self, success: int, failed: int, cancelled: int) -> None:
        self._set_running(False)
        self.active_task_id = None
        if cancelled:
            self._set_notice(f"任务已停止：成功 {success} 个，失败 {failed} 个，取消 {cancelled} 个。", "warning")
        elif failed:
            self._set_notice(f"转换完成：成功 {success} 个，失败 {failed} 个。", "error")
        else:
            self._set_notice(f"转换完成：成功 {success} 个。", "success")
        if self.settings.auto_open_folder and success:
            try:
                open_folder(Path(self.output_dir_var.get()))
            except OSError:
                pass
        if self.settings.auto_play and success == 1 and len(self.batch_ids) == 1 and self.last_success_path:
            try:
                if self.mode == "encrypt":
                    play_protected_media(self.last_success_path, self.settings)
                else:
                    play_media(self.last_success_path, self.settings)
            except OSError as exc:
                self.logger.warning("自动播放失败：%s", exc)

        if self.close_when_done:
            self.destroy()
            return
        summary = f"成功 {success} 个\n失败 {failed} 个\n取消 {cancelled} 个"
        if failed:
            summary += "\n\n失败任务可双击查看原因，修正后选择“重试任务”。"
        messagebox.showinfo("转换任务完成", summary, parent=self)

    def _set_running(self, running: bool) -> None:
        self.running = running
        normal_or_disabled = tk.DISABLED if running else tk.NORMAL
        for widget in (self.add_file_button, self.add_folder_button, self.remove_button, self.clear_button, self.change_output_button):
            widget.configure(state=normal_or_disabled)
        self.settings_button.configure(state=normal_or_disabled)
        self.decrypt_mode_button.configure(state=normal_or_disabled)
        self.encrypt_mode_button.configure(state=normal_or_disabled)
        self.auto_play_check.configure(state=normal_or_disabled)
        self.auto_open_check.configure(state=normal_or_disabled)
        if running:
            self.start_button.configure(state=tk.DISABLED)
            self.cancel_button.configure(text="取消任务", state=tk.NORMAL)
        else:
            self.cancel_button.configure(text="取消任务", state=tk.DISABLED)
            self._refresh_summary()

    def _refresh_tree_row(self, task: TaskRecord) -> None:
        if not self.tree.exists(task.iid):
            return
        output = task.actual_output or task.planned_output
        tag = ""
        if task.status == "已完成":
            tag = "success"
        elif task.status == "转换失败":
            tag = "error"
        elif task.status in {"已取消", "已跳过"}:
            tag = "warning"
        elif task.status in {"准备中", "转换中", "解密中", "加密中", "正在校验", "正在保存"}:
            tag = "active"
        self.tree.item(
            task.iid,
            values=(task.source.name, format_size(task.size), task.status, f"{task.progress:.0f}%", output.name),
            tags=(tag,) if tag else (),
        )

    def _refresh_summary(self) -> None:
        count = len(self.tasks)
        total = sum(task.size for task in self.tasks.values())
        self.task_summary_var.set(f"共 {count} 个 · {format_size(total)}")
        ready = sum(task.status in RETRY_STATES for task in self.tasks.values())
        if not self.running:
            action = "解密" if self.mode == "decrypt" else "加密"
            text = f"开始{action} {ready} 个" if ready else f"开始{action}"
            has_output = bool(self.output_dir_var.get().strip())
            self.start_button.configure(text=text, state=tk.NORMAL if ready and has_output else tk.DISABLED)

    def _update_overall_progress(self) -> None:
        batch = [self.tasks[iid] for iid in self.batch_ids if iid in self.tasks]
        if not batch:
            self.overall_progress["value"] = 0
            self.overall_percent_label.configure(text="0%")
            self.overall_var.set("总进度 0/0")
            return
        total = sum(task.size for task in batch)
        completed_weight = 0.0
        completed_count = 0
        for task in batch:
            if task.status in TERMINAL_STATES:
                completed_weight += task.size
                completed_count += 1
            else:
                completed_weight += task.size * task.progress / 100.0
        percent = completed_weight * 100.0 / total if total else 100.0
        self.overall_progress["value"] = percent
        self.overall_percent_label.configure(text=f"{percent:.0f}%")
        self.overall_var.set(f"总进度 {completed_count}/{len(batch)}")

    def _reset_progress_display(self) -> None:
        self.batch_ids = []
        self.current_title_var.set("尚未开始转换")
        self.current_percent_var.set("0%")
        self.current_detail_var.set("添加文件后点击“开始转换”")
        self.speed_var.set("速度 --")
        self.current_progress["value"] = 0
        self._update_overall_progress()

    def _set_notice(self, text: str, kind: str) -> None:
        colors = {
            "normal": COLORS["muted"],
            "active": COLORS["blue"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["danger"],
        }
        self.status_var.set(text)
        self.status_label.configure(foreground=colors.get(kind, COLORS["muted"]))

    def _save_main_options(self) -> None:
        self.settings.auto_play = self.auto_play_var.get()
        self.settings.auto_open_folder = self.auto_open_var.get()
        self._save_settings_quietly()

    def _save_settings_quietly(self) -> None:
        try:
            save_settings(self.settings)
        except OSError as exc:
            self.logger.warning("保存设置失败：%s", exc)

    def _play_selected(self) -> None:
        selected = self.tree.selection()
        task = self.tasks.get(selected[0]) if selected else None
        target = task.actual_output if task and task.actual_output else self.last_success_path
        if target is None or not target.is_file():
            messagebox.showinfo("没有可打开文件", "请先完成至少一个转换任务。", parent=self)
            return
        try:
            task_mode = task.mode if task else self.mode
            if task_mode == "encrypt":
                used = play_protected_media(target, self.settings)
                self._set_notice(f"已调用原播放器验证：{used}", "success")
            else:
                used = play_media(target, self.settings)
                self._set_notice(f"已调用 {used} 播放视频。", "success")
        except OSError as exc:
            messagebox.showerror("打开失败", str(exc), parent=self)

    def _reveal_selected(self) -> None:
        selected = self.tree.selection()
        task = self.tasks.get(selected[0]) if selected else None
        target = task.actual_output if task and task.actual_output else None
        try:
            if target:
                reveal_file(target)
            else:
                open_folder(Path(self.output_dir_var.get()))
        except OSError as exc:
            messagebox.showerror("打开失败", str(exc), parent=self)

    def _on_tree_double_click(self, event: tk.Event) -> None:
        iid = self.tree.identify_row(event.y)
        task = self.tasks.get(iid)
        if not task:
            return
        if task.status == "已完成":
            self.tree.selection_set(iid)
            self._play_selected()
        elif task.status == "转换失败":
            self._show_task_details(task)

    def _show_context_menu(self, event: tk.Event) -> None:
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _show_task_details(self, task: TaskRecord) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("任务详情")
        dialog.geometry("680x430")
        dialog.minsize(560, 360)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(background=COLORS["window"])

        card = ttk.Frame(dialog, style="Card.TFrame", padding=18)
        card.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)
        ttk.Label(card, text=task.source.name, style="Section.TLabel").pack(anchor="w")
        ttk.Label(card, text=f"状态：{task.status}", style="Muted.TLabel").pack(anchor="w", pady=(5, 12))
        text = tk.Text(
            card,
            wrap="word",
            background="#F8FAFC",
            foreground=COLORS["text"],
            relief=tk.FLAT,
            borderwidth=0,
            font=("Consolas", 9),
            padx=12,
            pady=12,
        )
        detail = (
            f"模式：{'解密 YUCEdu → 视频' if task.mode == 'decrypt' else '加密视频 → YUCEdu'}\n\n"
            f"输入文件：{task.source}\n\n"
            f"输出文件：{task.actual_output or task.planned_output}\n\n"
            f"错误代码：{task.error_code or '无'}\n\n"
            f"{task.error_message or '任务没有错误信息。'}"
        )
        text.insert("1.0", detail)
        text.configure(state=tk.DISABLED)
        text.pack(fill=tk.BOTH, expand=True)
        buttons = ttk.Frame(card, style="CardInner.TFrame")
        buttons.pack(fill=tk.X, pady=(12, 0))

        def copy_detail() -> None:
            self.clipboard_clear()
            self.clipboard_append(detail)
            self._set_notice("任务详情已复制到剪贴板。", "success")

        ttk.Button(buttons, text="复制详情", style="Secondary.TButton", command=copy_detail).pack(side=tk.LEFT)
        ttk.Button(buttons, text="关闭", style="Primary.TButton", command=dialog.destroy).pack(side=tk.RIGHT)

    def _open_settings(self) -> None:
        if self.running:
            return
        dialog = tk.Toplevel(self)
        dialog.title("设置")
        dialog.geometry("680x640")
        dialog.minsize(620, 580)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(background=COLORS["window"])

        card = ttk.Frame(dialog, style="Card.TFrame", padding=20)
        card.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text="应用设置", style="Section.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(card, text="输出文件夹在主界面按每次任务选择，这里设置播放器和处理方式。", style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 18))

        if sys.platform == "darwin":
            player_labels = {
                "自动检测（推荐）": "auto",
                "IINA": "iina",
                "VLC": "vlc",
                "macOS 默认播放器": "system",
                "自定义播放器": "custom",
            }
        else:
            player_labels = {
                "自动检测（推荐）": "auto",
                "PotPlayer": "potplayer",
                "VLC": "vlc",
                "Windows 默认播放器": "windows",
                "自定义播放器": "custom",
            }
        current_player_label = next((label for label, value in player_labels.items() if value == self.settings.player_mode), "自动检测（推荐）")
        player_var = tk.StringVar(value=current_player_label)
        player_path_var = tk.StringVar(value=self.settings.player_path)
        original_player_var = tk.StringVar(value=self.settings.original_player_path)
        policy_labels = {
            "自动改名（推荐）": "rename",
            "已有文件时停止": "error",
            "确认后覆盖": "replace",
        }
        current_policy_label = next((label for label, value in policy_labels.items() if value == self.settings.existing_policy), "自动改名（推荐）")
        policy_var = tk.StringVar(value=current_policy_label)
        auto_play_var = tk.BooleanVar(value=self.auto_play_var.get())
        auto_open_var = tk.BooleanVar(value=self.auto_open_var.get())
        key_var = tk.StringVar(value=self.profile_key_text)
        key_hex_var = tk.BooleanVar(value=self.profile_key_is_hex)
        show_key_var = tk.BooleanVar(value=False)
        show_tech_var = tk.BooleanVar(value=False)

        ttk.Label(card, text="播放器", style="Card.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Combobox(card, textvariable=player_var, values=list(player_labels), state="readonly").grid(row=2, column=1, columnspan=2, sticky="ew", pady=6)

        ttk.Label(card, text="自定义路径", style="Card.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Entry(card, textvariable=player_path_var).grid(row=3, column=1, sticky="ew", pady=6)

        def browse_player() -> None:
            if sys.platform == "darwin":
                chosen = filedialog.askopenfilename(
                    title="选择 macOS 播放器应用",
                    filetypes=[("macOS 应用", "*.app"), ("所有文件", "*.*")],
                    parent=dialog,
                )
            else:
                chosen = filedialog.askopenfilename(
                    title="选择播放器程序",
                    filetypes=[("EXE 程序", "*.exe"), ("所有文件", "*.*")],
                    parent=dialog,
                )
            if chosen:
                player_path_var.set(chosen)
                player_var.set("自定义播放器")

        ttk.Button(card, text="选择", style="Secondary.TButton", command=browse_player).grid(row=3, column=2, padx=(8, 0), pady=6)

        ttk.Label(card, text="原播放器", style="Card.TLabel").grid(row=4, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Entry(card, textvariable=original_player_var).grid(row=4, column=1, sticky="ew", pady=6)

        def browse_original_player() -> None:
            if sys.platform == "darwin":
                chosen = filedialog.askopenfilename(
                    title="选择 MacNetPlayer.app",
                    filetypes=[("MacNetPlayer", "*.app"), ("所有文件", "*.*")],
                    parent=dialog,
                )
            else:
                chosen = filedialog.askopenfilename(
                    title="选择 WinNetPlayer1018.exe",
                    filetypes=[("WinNetPlayer1018", "WinNetPlayer1018.exe"), ("EXE 程序", "*.exe")],
                    parent=dialog,
                )
            if chosen:
                original_player_var.set(chosen)

        ttk.Button(card, text="选择", style="Secondary.TButton", command=browse_original_player).grid(row=4, column=2, padx=(8, 0), pady=6)

        ttk.Label(card, text="同名文件", style="Card.TLabel").grid(row=5, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Combobox(card, textvariable=policy_var, values=list(policy_labels), state="readonly").grid(row=5, column=1, columnspan=2, sticky="ew", pady=6)

        option_row = ttk.Frame(card, style="CardInner.TFrame")
        option_row.grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 10))
        ttk.Checkbutton(option_row, text="单个任务完成后自动打开", variable=auto_play_var).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Checkbutton(option_row, text="任务结束后打开目录", variable=auto_open_var).pack(side=tk.LEFT)

        ttk.Separator(card).grid(row=7, column=0, columnspan=3, sticky="ew", pady=10)
        ttk.Checkbutton(card, text="显示技术设置", variable=show_tech_var).grid(row=8, column=0, columnspan=3, sticky="w")
        tech = ttk.Frame(card, style="CardInner.TFrame")
        tech.columnconfigure(1, weight=1)
        ttk.Label(tech, text="转换配置", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Label(tech, text="当前已验证配置", style="Status.TLabel").grid(row=0, column=1, sticky="w", pady=6)
        ttk.Label(tech, text="密钥", style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=6)
        key_entry = ttk.Entry(tech, textvariable=key_var, show="●")
        key_entry.grid(row=1, column=1, sticky="ew", pady=6)

        def toggle_key() -> None:
            key_entry.configure(show="" if show_key_var.get() else "●")

        ttk.Checkbutton(tech, text="显示密钥", variable=show_key_var, command=toggle_key).grid(row=1, column=2, padx=(8, 0))
        ttk.Checkbutton(tech, text="密钥是 32 位十六进制", variable=key_hex_var).grid(row=2, column=1, columnspan=2, sticky="w", pady=4)
        ttk.Label(
            tech,
            text="当前配置只对应已经验证的样本/授权分支。",
            style="Muted.TLabel",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

        def toggle_tech() -> None:
            if show_tech_var.get():
                tech.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(8, 0))
            else:
                tech.grid_remove()

        show_tech_var.trace_add("write", lambda *_args: toggle_tech())

        button_row = ttk.Frame(card, style="CardInner.TFrame")
        button_row.grid(row=10, column=0, columnspan=3, sticky="sew", pady=(18, 0))
        card.rowconfigure(10, weight=1)

        def save_dialog() -> None:
            try:
                key = parse_key(hex_key=key_var.get().strip()) if key_hex_var.get() else parse_key(ascii_key=key_var.get().strip())
            except ConversionError as exc:
                messagebox.showerror("转换配置错误", exc.message, parent=dialog)
                return
            self.profile_key_text = key.hex() if key_hex_var.get() else key.decode("ascii")
            self.profile_key_is_hex = key_hex_var.get()
            self.settings.player_mode = player_labels[player_var.get()]
            self.settings.player_path = player_path_var.get().strip()
            self.settings.original_player_path = original_player_var.get().strip()
            self.settings.existing_policy = policy_labels[policy_var.get()]
            self.settings.auto_play = auto_play_var.get()
            self.settings.auto_open_folder = auto_open_var.get()
            self.auto_play_var.set(self.settings.auto_play)
            self.auto_open_var.set(self.settings.auto_open_folder)
            try:
                save_settings(self.settings)
            except OSError as exc:
                messagebox.showerror("保存失败", str(exc), parent=dialog)
                return
            dialog.destroy()
            self._set_notice("设置已保存。", "success")

        ttk.Button(button_row, text="取消", style="Secondary.TButton", command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(button_row, text="保存设置", style="Primary.TButton", command=save_dialog).pack(side=tk.RIGHT)

    def _show_help(self) -> None:
        modifier = "Command" if sys.platform == "darwin" else "Ctrl"
        original_player = "MacNetPlayer" if sys.platform == "darwin" else "WinNetPlayer1018"
        messagebox.showinfo(
            "使用说明",
            "1. 先选择“解密 YUCEdu”或“加密视频”。\n"
            "2. 点击“选择文件夹”，决定本次任务的输出位置。\n"
            "3. 点击“添加文件”或“添加文件夹”，然后开始处理。\n"
            "4. 解密结果双击后用普通播放器打开。\n"
            f"5. 加密结果双击后用 {original_player} 打开。\n\n"
            "快捷键：\n"
            f"{modifier}+O 添加文件\n"
            f"{modifier}+Shift+O 添加文件夹\n"
            "Delete/Backspace 移除所选\n"
            f"{modifier}+Enter 开始转换\n\n"
            "支持加密：MP4、MKV、AVI、MOV、M4V、WMV、FLV、WebM、TS、MPEG/MPG。\n\n"
            "当前转换配置只对应已经验证的样本/配置档案。",
            parent=self,
        )

    def _on_close(self) -> None:
        if not self.running:
            self.destroy()
            return
        if messagebox.askyesno(
            "转换正在进行",
            "退出将停止当前任务并清理临时文件，已经完成的输出文件会保留。\n\n是否退出程序？",
            parent=self,
        ):
            self.close_when_done = True
            self.cancel_event.set()
            self.cancel_button.configure(text="正在退出…", state=tk.DISABLED)


def run_app(*, smoke_test: bool = False) -> None:
    app = MainWindow()
    if smoke_test:
        app.after(800, app.destroy)
    app.mainloop()
