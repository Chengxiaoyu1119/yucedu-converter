"""YUCEdu 正式版的桌面视觉规范。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "window": "#F5F7FA",
    "card": "#FFFFFF",
    "text": "#172033",
    "muted": "#667085",
    "border": "#D9E0EA",
    "blue": "#2563EB",
    "blue_hover": "#1D4ED8",
    "blue_soft": "#EAF2FF",
    "navy": "#102A43",
    "navy_light": "#173B5E",
    "success": "#16803C",
    "success_soft": "#ECFDF3",
    "warning": "#B25E09",
    "warning_soft": "#FFF7E8",
    "danger": "#C43232",
    "danger_hover": "#A72A2A",
    "danger_soft": "#FEF1F1",
    "disabled": "#A6B0BF",
    "row_alt": "#F9FBFD",
}

FONT_UI = ("Microsoft YaHei UI", 10)
FONT_SMALL = ("Microsoft YaHei UI", 9)
FONT_SECTION = ("Microsoft YaHei UI", 11, "bold")
FONT_TITLE = ("Microsoft YaHei UI", 20, "bold")
FONT_SUBTITLE = ("Microsoft YaHei UI", 10)
FONT_BUTTON = ("Microsoft YaHei UI", 10, "bold")


def apply_theme(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")

    root.option_add("*Font", FONT_UI)
    root.option_add("*Menu.Font", FONT_UI)
    root.option_add("*TCombobox*Listbox.Font", FONT_UI)

    style.configure(".", font=FONT_UI, background=COLORS["window"], foreground=COLORS["text"])
    style.configure("App.TFrame", background=COLORS["window"])
    style.configure(
        "Card.TFrame",
        background=COLORS["card"],
        bordercolor=COLORS["border"],
        borderwidth=1,
        relief="solid",
    )
    style.configure("CardInner.TFrame", background=COLORS["card"], borderwidth=0, relief="flat")
    style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"])
    style.configure("Section.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=FONT_SECTION)
    style.configure("Muted.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=FONT_SMALL)
    style.configure("Status.TLabel", background=COLORS["card"], foreground=COLORS["blue"], font=FONT_SMALL)

    style.configure(
        "Primary.TButton",
        background=COLORS["blue"],
        foreground="#FFFFFF",
        bordercolor=COLORS["blue"],
        darkcolor=COLORS["blue"],
        lightcolor=COLORS["blue"],
        focuscolor=COLORS["blue"],
        borderwidth=1,
        padding=(18, 10),
        font=FONT_BUTTON,
    )
    style.map(
        "Primary.TButton",
        background=[("disabled", COLORS["disabled"]), ("active", COLORS["blue_hover"]), ("pressed", COLORS["blue_hover"])],
        bordercolor=[("disabled", COLORS["disabled"]), ("active", COLORS["blue_hover"])],
        foreground=[("disabled", "#F7F8FA"), ("!disabled", "#FFFFFF")],
    )

    style.configure(
        "Secondary.TButton",
        background=COLORS["card"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        darkcolor=COLORS["card"],
        lightcolor=COLORS["card"],
        focuscolor=COLORS["blue_soft"],
        borderwidth=1,
        padding=(13, 8),
        font=FONT_UI,
    )
    style.map(
        "Secondary.TButton",
        background=[("disabled", "#F3F5F8"), ("active", COLORS["blue_soft"]), ("pressed", "#DCEAFF")],
        bordercolor=[("active", COLORS["blue"]), ("focus", COLORS["blue"])],
        foreground=[("disabled", COLORS["disabled"]), ("!disabled", COLORS["text"])],
    )

    style.configure(
        "Danger.TButton",
        background=COLORS["card"],
        foreground=COLORS["danger"],
        bordercolor="#E8B8B8",
        darkcolor=COLORS["card"],
        lightcolor=COLORS["card"],
        borderwidth=1,
        padding=(13, 8),
        font=FONT_UI,
    )
    style.map(
        "Danger.TButton",
        background=[("disabled", "#F3F5F8"), ("active", COLORS["danger_soft"]), ("pressed", "#FBE3E3")],
        foreground=[("disabled", COLORS["disabled"]), ("!disabled", COLORS["danger"])],
    )

    style.configure(
        "Treeview",
        background=COLORS["card"],
        fieldbackground=COLORS["card"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        rowheight=34,
        font=FONT_UI,
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["blue_soft"])],
        foreground=[("selected", COLORS["text"])],
    )
    style.configure(
        "Treeview.Heading",
        background="#F7F9FC",
        foreground=COLORS["muted"],
        bordercolor=COLORS["border"],
        relief="flat",
        padding=(10, 9),
        font=("Microsoft YaHei UI", 9, "bold"),
    )
    style.map("Treeview.Heading", background=[("active", "#EEF3F8")])

    # 移除经典滚动条的上下/左右箭头，仅保留细轨道和圆润感更强的滑块。
    style.layout(
        "Modern.Vertical.TScrollbar",
        [
            (
                "Vertical.Scrollbar.trough",
                {
                    "sticky": "ns",
                    "children": [
                        ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"}),
                    ],
                },
            )
        ],
    )
    style.layout(
        "Modern.Horizontal.TScrollbar",
        [
            (
                "Horizontal.Scrollbar.trough",
                {
                    "sticky": "ew",
                    "children": [
                        ("Horizontal.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"}),
                    ],
                },
            )
        ],
    )
    for scrollbar_style in ("Modern.Vertical.TScrollbar", "Modern.Horizontal.TScrollbar"):
        style.configure(
            scrollbar_style,
            background="#C5D0DD",
            troughcolor=COLORS["card"],
            bordercolor=COLORS["card"],
            lightcolor="#C5D0DD",
            darkcolor="#C5D0DD",
            relief="flat",
            borderwidth=0,
            width=9,
        )
        style.map(
            scrollbar_style,
            background=[("pressed", "#8293A8"), ("active", "#9CABB9")],
            lightcolor=[("pressed", "#8293A8"), ("active", "#9CABB9")],
            darkcolor=[("pressed", "#8293A8"), ("active", "#9CABB9")],
        )

    style.configure(
        "Current.Horizontal.TProgressbar",
        troughcolor="#E7EDF4",
        background=COLORS["blue"],
        bordercolor="#E7EDF4",
        lightcolor=COLORS["blue"],
        darkcolor=COLORS["blue"],
        thickness=12,
    )
    style.configure(
        "Overall.Horizontal.TProgressbar",
        troughcolor="#E7EDF4",
        background="#4A8FE7",
        bordercolor="#E7EDF4",
        lightcolor="#4A8FE7",
        darkcolor="#4A8FE7",
        thickness=8,
    )
    style.configure(
        "TEntry",
        fieldbackground="#FFFFFF",
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=(9, 7),
    )
    style.map("TEntry", bordercolor=[("focus", COLORS["blue"])])
    style.configure(
        "TCombobox",
        fieldbackground="#FFFFFF",
        background="#FFFFFF",
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        arrowsize=14,
        padding=(8, 6),
    )
    style.map("TCombobox", bordercolor=[("focus", COLORS["blue"])])
    style.configure("TCheckbutton", background=COLORS["card"], foreground=COLORS["text"], padding=(0, 3))
    style.map("TCheckbutton", background=[("active", COLORS["card"])])
    style.configure("TSeparator", background=COLORS["border"])
    return style
