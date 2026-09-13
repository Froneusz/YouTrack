"""Ciemny motyw wizualny dla YouTrak (ttk + tk), spójny stylistycznie z Vibrą."""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from tkinter import ttk

BG = "#0B0F14"
PANEL = "#111720"
ELEVATED = "#1A222D"
BORDER = "#26303C"
TEXT = "#EAF2F5"
TEXT_MUTED = "#8B98A5"
ACCENT = "#2DD4BF"
ACCENT_HOVER = "#5EEAD4"
ACCENT_TEXT = "#052E2B"
DANGER = "#F87171"

FONT_FAMILY = "Segoe UI"


def enable_dark_titlebar(root: tk.Tk) -> None:
    """Dociemnia pasek tytułowy okna na Windows 10/11 (DWM immersive dark mode)."""
    if sys.platform != "win32":
        return
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1)
        for attribute in (20, 19):  # 20 = Win10 20H1+, 19 = starsze buildy
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
            )
            if result == 0:
                break
    except Exception:
        pass


def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=BG)
    enable_dark_titlebar(root)

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=TEXT, font=(FONT_FAMILY, 10))

    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=PANEL)

    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Muted.TLabel", background=BG, foreground=TEXT_MUTED)
    style.configure("Card.TLabel", background=PANEL, foreground=TEXT)
    style.configure("CardMuted.TLabel", background=PANEL, foreground=TEXT_MUTED)
    style.configure(
        "Brand.TLabel", background=BG, foreground=TEXT, font=(FONT_FAMILY, 20, "bold")
    )
    style.configure(
        "Section.TLabel", background=BG, foreground=TEXT_MUTED, font=(FONT_FAMILY, 9, "bold")
    )

    style.configure(
        "TEntry",
        fieldbackground=ELEVATED,
        foreground=TEXT,
        insertcolor=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        borderwidth=1,
        padding=8,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", ACCENT)],
        lightcolor=[("focus", ACCENT)],
        darkcolor=[("focus", ACCENT)],
    )

    style.configure(
        "TCombobox",
        fieldbackground=ELEVATED,
        background=ELEVATED,
        foreground=TEXT,
        arrowcolor=TEXT_MUTED,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=6,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", ELEVATED)],
        foreground=[("readonly", TEXT)],
        bordercolor=[("focus", ACCENT)],
    )
    root.option_add("*TCombobox*Listbox.background", ELEVATED)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", ACCENT_TEXT)

    style.configure(
        "TCheckbutton",
        background=BG,
        foreground=TEXT_MUTED,
        focuscolor=BG,
    )
    style.map("TCheckbutton", foreground=[("selected", TEXT)])

    style.configure(
        "TButton",
        background=ELEVATED,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=ELEVATED,
        darkcolor=ELEVATED,
        borderwidth=1,
        focuscolor=BG,
        padding=(14, 8),
        font=(FONT_FAMILY, 10),
    )
    style.map(
        "TButton",
        background=[("active", BORDER), ("disabled", ELEVATED)],
        foreground=[("disabled", TEXT_MUTED)],
    )

    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground=ACCENT_TEXT,
        bordercolor=ACCENT,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        borderwidth=0,
        padding=(20, 11),
        font=(FONT_FAMILY, 10, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("active", ACCENT_HOVER), ("disabled", ELEVATED)],
        foreground=[("disabled", TEXT_MUTED)],
    )

    style.configure(
        "Horizontal.TProgressbar",
        background=ACCENT,
        troughcolor=ELEVATED,
        bordercolor=ELEVATED,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        thickness=7,
    )

    style.configure(
        "TScrollbar",
        background=ELEVATED,
        troughcolor=BG,
        bordercolor=BG,
        arrowcolor=TEXT_MUTED,
        gripcount=0,
    )
    style.map("TScrollbar", background=[("active", BORDER)])


def style_text_widget(widget: tk.Text) -> None:
    widget.configure(
        background=ELEVATED,
        foreground=TEXT,
        insertbackground=TEXT,
        selectbackground=ACCENT,
        selectforeground=ACCENT_TEXT,
        relief="flat",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        padx=10,
        pady=8,
        font=(FONT_FAMILY, 9),
    )
