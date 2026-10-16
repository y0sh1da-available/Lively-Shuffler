"""
Lively Wallpaper Shuffler - High-DPI Smooth GUI Dashboard
Features:
- High-DPI awareness (pixel-perfect sharpness on Windows 10/11)
- Virtual windowed scrolling (renders only visible wallpapers for silky 60fps performance)
- High-contrast, modern dark UI (pill buttons, segmented switches, no messy combobox overlaps)
- Live wallpaper gallery with thumbnails, search filtering, and click-to-activate
"""

import os
import sys
import math
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk

# Enable High-DPI awareness before Tkinter windows are created
def enable_dpi_awareness():
    try:
        # PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback for older Windows 10
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

enable_dpi_awareness()

# Clean High-Contrast Dark Palette
C_BG = "#10111a"
C_SIDEBAR = "#161724"
C_CARD = "#1c1e2e"
C_CARD_HOVER = "#25283d"
C_BORDER = "#2b2e46"
C_BORDER_LIGHT = "#3d4263"
C_TEXT_WHITE = "#ffffff"
C_TEXT_PRIMARY = "#f0f2f8"
C_TEXT_MUTED = "#8f96b3"
C_ACCENT_BLUE = "#3b82f6"
C_ACCENT_BLUE_HOVER = "#2563eb"
C_ACCENT_GREEN = "#10b981"
C_ACCENT_AMBER = "#f59e0b"

class ShufflerGUI:
    def __init__(self, controller, root: tk.Tk):
        self.controller = controller
        self.root = root

        self.root.title("Lively Wallpaper Shuffler")
        self.root.geometry("1020x720")
        self.root.minsize(880, 580)
        self.root.configure(bg=C_BG)

        self.set_window_icon()

        # Image & thumbnail cache
        self.thumb_cache = {}
        self.rendered_card_widgets = {}  # index -> (window_id, widget)
        self.filtered_wallpapers = list(self.controller.wallpapers)

        # Build UI layout
        self.build_ui()

        # Window close minimizes to tray
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)

        # Initial data populate
        self.refresh_ui()

    def set_window_icon(self):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        if os.path.isfile(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

    def build_ui(self):
        # Left Sidebar (Controls & Active Wallpaper)
        self.sidebar = tk.Frame(self.root, bg=C_SIDEBAR, width=340, padx=20, pady=20)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Right Main Content (Gallery)
        self.main_content = tk.Frame(self.root, bg=C_BG, padx=22, pady=20)
        self.main_content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.build_sidebar()
        self.build_gallery()

    def build_sidebar(self):
        # App Title & Status Badge
        title_box = tk.Frame(self.sidebar, bg=C_SIDEBAR)
        title_box.pack(fill=tk.X, pady=(0, 16))

        tk.Label(
            title_box,
            text="Lively Shuffler",
            font=("Segoe UI", 16, "bold"),
            bg=C_SIDEBAR,
            fg=C_TEXT_WHITE,
        ).pack(anchor="w")

        self.status_badge = tk.Label(
            title_box,
            text="● Active",
            font=("Segoe UI", 9, "bold"),
            bg=C_SIDEBAR,
            fg=C_ACCENT_GREEN,
        )
        self.status_badge.pack(anchor="w", pady=(3, 0))

        # --- Active Wallpaper Preview Card ---
        self.active_card = tk.Frame(
            self.sidebar,
            bg=C_CARD,
            padx=12,
            pady=12,
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        self.active_card.pack(fill=tk.X, pady=(0, 16))

        tk.Label(
            self.active_card,
            text="CURRENT ACTIVE WALLPAPER",
            font=("Segoe UI", 8, "bold"),
            bg=C_CARD,
            fg=C_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 6))

        self.active_thumb_lbl = tk.Label(self.active_card, bg="#0d0e15", height=115)
        self.active_thumb_lbl.pack(fill=tk.X, pady=(0, 8))

        self.active_title_lbl = tk.Label(
            self.active_card,
            text="Loading...",
            font=("Segoe UI", 11, "bold"),
            bg=C_CARD,
            fg=C_TEXT_WHITE,
            wraplength=275,
            justify="left",
        )
        self.active_title_lbl.pack(anchor="w")

        self.active_info_lbl = tk.Label(
            self.active_card,
            text="",
            font=("Segoe UI", 8),
            bg=C_CARD,
            fg=C_TEXT_MUTED,
            wraplength=275,
            justify="left",
        )
        self.active_info_lbl.pack(anchor="w", pady=(2, 8))

        tk.Button(
            self.active_card,
            text="📁 Open Folder",
            font=("Segoe UI", 8, "bold"),
            bg="#2a2e45",
            fg=C_TEXT_WHITE,
            activebackground=C_ACCENT_BLUE,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.on_open_current_folder,
        ).pack(anchor="e")

        # --- Quick Action Buttons (Prev / Next) ---
        nav_box = tk.Frame(self.sidebar, bg=C_SIDEBAR)
        nav_box.pack(fill=tk.X, pady=(0, 12))

        self.prev_btn = tk.Button(
            nav_box,
            text="⏮ Previous",
            font=("Segoe UI", 9, "bold"),
            bg=C_CARD,
            fg=C_TEXT_WHITE,
            activebackground=C_CARD_HOVER,
            activeforeground=C_TEXT_WHITE,
            relief=tk.FLAT,
            padx=10,
            pady=7,
            cursor="hand2",
            command=self.on_prev_clicked,
        )
        self.prev_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        self.next_btn = tk.Button(
            nav_box,
            text="⏭ Next",
            font=("Segoe UI", 9, "bold"),
            bg=C_ACCENT_BLUE,
            fg="#ffffff",
            activebackground=C_ACCENT_BLUE_HOVER,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=7,
            cursor="hand2",
            command=self.on_next_clicked,
        )
        self.next_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        # Pause / Resume Button
        self.pause_btn = tk.Button(
            self.sidebar,
            text="⏸ Pause Shuffle",
            font=("Segoe UI", 9, "bold"),
            bg=C_CARD,
            fg=C_TEXT_WHITE,
            activebackground=C_CARD_HOVER,
            activeforeground=C_TEXT_WHITE,
            relief=tk.FLAT,
            pady=7,
            cursor="hand2",
            command=self.on_toggle_pause_clicked,
        )
        self.pause_btn.pack(fill=tk.X, pady=(0, 18))

        # --- Mode Segmented Pill Switch (High Contrast) ---
        tk.Label(
            self.sidebar,
            text="SHUFFLE MODE",
            font=("Segoe UI", 8, "bold"),
            bg=C_SIDEBAR,
            fg=C_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 6))

        mode_switch_frame = tk.Frame(self.sidebar, bg=C_CARD, padx=3, pady=3, highlightbackground=C_BORDER, highlightthickness=1)
        mode_switch_frame.pack(fill=tk.X, pady=(0, 16))

        self.mode_shuffle_btn = tk.Button(
            mode_switch_frame,
            text="🔀 Random",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=5,
            cursor="hand2",
            command=lambda: self.set_mode_ui("shuffle"),
        )
        self.mode_shuffle_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))

        self.mode_seq_btn = tk.Button(
            mode_switch_frame,
            text="🔁 Sequential",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=5,
            cursor="hand2",
            command=lambda: self.set_mode_ui("sequential"),
        )
        self.mode_seq_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        # --- Interval Selector Grid (High Contrast Pills) ---
        tk.Label(
            self.sidebar,
            text="TIMER INTERVAL",
            font=("Segoe UI", 8, "bold"),
            bg=C_SIDEBAR,
            fg=C_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 6))

        interval_grid = tk.Frame(self.sidebar, bg=C_SIDEBAR)
        interval_grid.pack(fill=tk.X, pady=(0, 16))

        self.interval_buttons = {}
        presets = [
            ("30s", 30),
            ("1m", 60),
            ("5m", 300),
            ("10m", 600),
            ("15m", 900),
            ("30m", 1800),
            ("1h", 3600),
            ("2h", 7200),
        ]

        for i, (label, sec) in enumerate(presets):
            row = i // 4
            col = i % 4
            btn = tk.Button(
                interval_grid,
                text=label,
                font=("Segoe UI", 8, "bold"),
                relief=tk.FLAT,
                cursor="hand2",
                pady=4,
                command=lambda s=sec: self.set_interval_ui(s),
            )
            btn.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
            interval_grid.columnconfigure(col, weight=1)
            self.interval_buttons[sec] = btn

        # --- Options (Autostart) ---
        self.autostart_var = tk.BooleanVar(value=self.controller.start_with_windows)
        self.autostart_check = tk.Checkbutton(
            self.sidebar,
            text="Start with Windows",
            variable=self.autostart_var,
            font=("Segoe UI", 9),
            bg=C_SIDEBAR,
            fg=C_TEXT_PRIMARY,
            selectcolor=C_CARD,
            activebackground=C_SIDEBAR,
            activeforeground=C_TEXT_WHITE,
            cursor="hand2",
            command=self.on_autostart_toggled,
        )
        self.autostart_check.pack(anchor="w", pady=(4, 14))

        # --- Status at Bottom of Sidebar ---
        status_box = tk.Frame(self.sidebar, bg=C_SIDEBAR)
        status_box.pack(side=tk.BOTTOM, fill=tk.X)

        exe_row = tk.Frame(status_box, bg=C_SIDEBAR)
        exe_row.pack(fill=tk.X, pady=(0, 3))

        exe_found = bool(self.controller.lively_exe)
        exe_color = C_ACCENT_GREEN if exe_found else "#ef4444"
        exe_msg = "● Lively.exe detected" if exe_found else "● Lively.exe not found"
        self.exe_lbl = tk.Label(exe_row, text=exe_msg, font=("Segoe UI", 8), bg=C_SIDEBAR, fg=exe_color)
        self.exe_lbl.pack(side=tk.LEFT)

        self.locate_btn = tk.Button(
            exe_row,
            text="Change..." if exe_found else "Locate...",
            font=("Segoe UI", 7, "bold"),
            bg=C_CARD,
            fg=C_TEXT_WHITE,
            activebackground=C_ACCENT_BLUE,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self.on_locate_lively,
        )
        self.locate_btn.pack(side=tk.RIGHT)

        count = len(self.controller.wallpapers)
        self.lib_lbl = tk.Label(
            status_box,
            text=f"● Library: {count} wallpapers",
            font=("Segoe UI", 8),
            bg=C_SIDEBAR,
            fg=C_ACCENT_GREEN if count > 0 else C_ACCENT_AMBER,
        )
        self.lib_lbl.pack(anchor="w")

    def build_gallery(self):
        # Top Gallery Bar
        top_bar = tk.Frame(self.main_content, bg=C_BG)
        top_bar.pack(fill=tk.X, pady=(0, 12))

        title_box = tk.Frame(top_bar, bg=C_BG)
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="Wallpaper Library",
            font=("Segoe UI", 15, "bold"),
            bg=C_BG,
            fg=C_TEXT_WHITE,
        ).pack(side=tk.LEFT)

        self.count_badge = tk.Label(
            title_box,
            text="0",
            font=("Segoe UI", 9, "bold"),
            bg=C_CARD,
            fg=C_ACCENT_BLUE,
            padx=8,
            pady=2,
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        self.count_badge.pack(side=tk.LEFT, padx=(10, 0))

        # Action Buttons (Add Folder + Rescan)
        btn_box = tk.Frame(top_bar, bg=C_BG)
        btn_box.pack(side=tk.RIGHT)

        tk.Button(
            btn_box,
            text="+ Add Folder",
            font=("Segoe UI", 9, "bold"),
            bg=C_CARD,
            fg=C_TEXT_WHITE,
            activebackground=C_CARD_HOVER,
            activeforeground=C_TEXT_WHITE,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.on_add_custom_folder,
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            btn_box,
            text="🔄 Rescan",
            font=("Segoe UI", 9, "bold"),
            bg=C_CARD,
            fg=C_TEXT_WHITE,
            activebackground=C_CARD_HOVER,
            activeforeground=C_TEXT_WHITE,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.on_rescan_clicked,
        ).pack(side=tk.LEFT)

        # Search Bar
        search_frame = tk.Frame(
            self.main_content,
            bg=C_CARD,
            padx=10,
            pady=7,
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        search_frame.pack(fill=tk.X, pady=(0, 14))

        tk.Label(search_frame, text="🔍", bg=C_CARD, fg=C_TEXT_MUTED, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_wallpapers())
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=("Segoe UI", 10),
            bg=C_CARD,
            fg=C_TEXT_WHITE,
            insertbackground=C_TEXT_WHITE,
            relief=tk.FLAT,
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Scrollable Virtual Canvas
        self.canvas = tk.Canvas(self.main_content, bg=C_BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_content, orient="vertical", command=self.on_scrollbar_scroll)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bindings for Smooth Virtual Scrolling
        self.canvas.bind("<Configure>", lambda e: self.on_canvas_configure())
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    # =========================================================================
    # Virtual Windowed Gallery Rendering (Renders only visible items)
    # =========================================================================
    CARD_H = 145
    ROW_GAP = 12
    COL_GAP = 12

    def on_scrollbar_scroll(self, *args):
        self.canvas.yview(*args)
        self.update_visible_cards()

    def on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            # Smooth scrolling step
            step = int(-1 * (event.delta / 120) * 2)
            self.canvas.yview_scroll(step, "units")
            self.update_visible_cards()

    def on_canvas_configure(self):
        self.update_virtual_scrollregion()
        self.update_visible_cards()

    def get_cols(self):
        width = self.canvas.winfo_width()
        if width <= 50:
            width = 620
        if width > 800:
            return 4
        elif width > 520:
            return 3
        else:
            return 2

    def update_virtual_scrollregion(self):
        total = len(self.filtered_wallpapers)
        cols = self.get_cols()
        total_rows = math.ceil(total / cols) if cols > 0 else 0
        total_height = total_rows * (self.CARD_H + self.ROW_GAP) + 20
        cw = max(self.canvas.winfo_width(), 620)
        ch = max(self.canvas.winfo_height(), 400)
        self.canvas.config(scrollregion=(0, 0, cw, max(total_height, ch)))

    def update_visible_cards(self):
        """Virtual render: dynamically creates widgets only for cards in the current viewport."""
        total = len(self.filtered_wallpapers)
        if total == 0:
            # Clear all
            for win_id, widget in list(self.rendered_card_widgets.values()):
                self.canvas.delete(win_id)
                widget.destroy()
            self.rendered_card_widgets.clear()
            return

        cols = self.get_cols()
        row_height = self.CARD_H + self.ROW_GAP
        total_rows = math.ceil(total / cols)
        total_height = max(total_rows * row_height + 20, 1)

        # Calculate visible pixel bounds
        y_top_ratio, y_bottom_ratio = self.canvas.yview()
        top_px = y_top_ratio * total_height
        bottom_px = y_bottom_ratio * total_height

        # Determine visible row range with 1 buffer row above and below
        first_row = max(0, int(top_px // row_height) - 1)
        last_row = min(total_rows - 1, int(bottom_px // row_height) + 1)

        visible_start = first_row * cols
        visible_end = min(total, (last_row + 1) * cols)
        needed_indices = set(range(visible_start, visible_end))

        # 1. Remove cards that scrolled out of view
        current_indices = set(self.rendered_card_widgets.keys())
        for idx in current_indices - needed_indices:
            win_id, widget = self.rendered_card_widgets.pop(idx)
            self.canvas.delete(win_id)
            widget.destroy()

        # 2. Add or reposition cards that entered view
        canvas_width = self.canvas.winfo_width()
        if canvas_width <= 50:
            canvas_width = 620
        col_width = max(140, (canvas_width - (cols - 1) * self.COL_GAP - 10) // cols)

        for idx in needed_indices:
            wp = self.filtered_wallpapers[idx]
            r = idx // cols
            c = idx % cols
            x = c * (col_width + self.COL_GAP) + 5
            y = r * row_height + 10

            if idx not in self.rendered_card_widgets:
                card = self.create_card_widget(wp, col_width)
                win_id = self.canvas.create_window(x, y, window=card, anchor="nw", width=col_width, height=self.CARD_H)
                self.rendered_card_widgets[idx] = (win_id, card)
            else:
                win_id, card = self.rendered_card_widgets[idx]
                self.canvas.coords(win_id, x, y)
                self.canvas.itemconfigure(win_id, width=col_width)

    def load_thumbnail(self, wallpaper_item, size=(160, 90)):
        """Load and cache wallpaper thumbnail image."""
        size = (max(60, int(size[0])), max(40, int(size[1])))
        if wallpaper_item.folder_path in self.thumb_cache:
            return self.thumb_cache[wallpaper_item.folder_path]

        thumb_img = None
        if os.path.isdir(wallpaper_item.folder_path):
            info_path = os.path.join(wallpaper_item.folder_path, "LivelyInfo.json")
            if os.path.isfile(info_path):
                try:
                    with open(info_path, "r", encoding="utf-8") as f:
                        import json
                        meta = json.load(f)
                        thumb_name = meta.get("Thumbnail")
                        if thumb_name:
                            p = os.path.join(wallpaper_item.folder_path, thumb_name)
                            if os.path.isfile(p):
                                thumb_img = Image.open(p)
                except Exception:
                    pass

            if not thumb_img:
                for cand in ("thumbnail.jpg", "thumbnail.png", "preview.gif"):
                    p = os.path.join(wallpaper_item.folder_path, cand)
                    if os.path.isfile(p):
                        try:
                            thumb_img = Image.open(p)
                            break
                        except Exception:
                            pass

        if not thumb_img:
            thumb_img = Image.new("RGB", size, color="#1c1f30")

        thumb_img = thumb_img.convert("RGBA")
        thumb_img.thumbnail(size, Image.Resampling.LANCZOS)

        canvas_img = Image.new("RGBA", size, (16, 17, 26, 255))
        offset_x = (size[0] - thumb_img.width) // 2
        offset_y = (size[1] - thumb_img.height) // 2
        canvas_img.paste(thumb_img, (offset_x, offset_y), thumb_img)

        tk_img = ImageTk.PhotoImage(canvas_img)
        self.thumb_cache[wallpaper_item.folder_path] = tk_img
        return tk_img

    def create_card_widget(self, wallpaper, width):
        is_active = (self.controller.current_wallpaper == wallpaper)
        border_color = C_ACCENT_BLUE if is_active else C_BORDER
        border_width = 2 if is_active else 1

        card = tk.Frame(
            self.canvas,
            bg=C_CARD,
            padx=8,
            pady=8,
            highlightbackground=border_color,
            highlightthickness=border_width,
            cursor="hand2",
        )

        # Thumbnail
        thumb = self.load_thumbnail(wallpaper, size=(width - 16, 85))
        thumb_lbl = tk.Label(card, image=thumb, bg="#0d0e15")
        thumb_lbl.image = thumb
        thumb_lbl.pack(fill=tk.X, pady=(0, 6))

        # Title
        display_title = wallpaper.title
        max_chars = max(18, width // 10)
        if len(display_title) > max_chars:
            display_title = display_title[: max_chars - 3] + "..."

        title_lbl = tk.Label(
            card,
            text=display_title,
            font=("Segoe UI", 9, "bold"),
            bg=C_CARD,
            fg=C_ACCENT_BLUE if is_active else C_TEXT_WHITE,
            anchor="w",
        )
        title_lbl.pack(fill=tk.X)

        # Badge
        badge_text = "● ACTIVE NOW" if is_active else (wallpaper.wp_type.capitalize() if wallpaper.wp_type else "Wallpaper")
        badge_color = C_ACCENT_BLUE if is_active else C_TEXT_MUTED
        badge_lbl = tk.Label(
            card,
            text=badge_text,
            font=("Segoe UI", 7, "bold"),
            bg=C_CARD,
            fg=badge_color,
            anchor="w",
        )
        badge_lbl.pack(fill=tk.X, pady=(1, 0))

        # Click handler
        def on_click(e):
            self.controller.select_wallpaper(wallpaper)
            self.refresh_ui()

        card.bind("<Button-1>", on_click)
        thumb_lbl.bind("<Button-1>", on_click)
        title_lbl.bind("<Button-1>", on_click)
        badge_lbl.bind("<Button-1>", on_click)

        return card

    # =========================================================================
    # UI State Synchronization
    # =========================================================================
    def refresh_ui(self):
        """Update active wallpaper showcase, status badges, and gallery."""
        curr = self.controller.current_wallpaper
        if curr:
            self.active_title_lbl.config(text=curr.title)
            info = f"Type: {curr.wp_type.capitalize() if curr.wp_type else 'Wallpaper'}"
            if curr.author:
                info += f" • By {curr.author}"
            self.active_info_lbl.config(text=info)

            active_thumb = self.load_thumbnail(curr, size=(280, 115))
            self.active_thumb_lbl.config(image=active_thumb)
            self.active_thumb_lbl.image = active_thumb
        else:
            self.active_title_lbl.config(text="No wallpaper active")
            self.active_info_lbl.config(text="")

        # Status badge & pause button
        if self.controller.is_paused:
            self.status_badge.config(text="● Paused", fg=C_ACCENT_AMBER)
            self.pause_btn.config(text="▶ Resume Shuffle", bg=C_ACCENT_GREEN, fg="#ffffff")
        else:
            label = self.controller.format_interval(self.controller.interval_seconds)
            self.status_badge.config(
                text=f"● Active ({self.controller.mode.capitalize()} • {label})",
                fg=C_ACCENT_GREEN,
            )
            self.pause_btn.config(text="⏸ Pause Shuffle", bg=C_CARD, fg=C_TEXT_WHITE)

        # Mode buttons highlight
        if self.controller.mode == "shuffle":
            self.mode_shuffle_btn.config(bg=C_ACCENT_BLUE, fg="#ffffff")
            self.mode_seq_btn.config(bg=C_CARD, fg=C_TEXT_MUTED)
        else:
            self.mode_shuffle_btn.config(bg=C_CARD, fg=C_TEXT_MUTED)
            self.mode_seq_btn.config(bg=C_ACCENT_BLUE, fg="#ffffff")

        # Interval buttons highlight
        for sec, btn in self.interval_buttons.items():
            if sec == self.controller.interval_seconds:
                btn.config(bg=C_ACCENT_BLUE, fg="#ffffff")
            else:
                btn.config(bg=C_CARD, fg=C_TEXT_PRIMARY)

        # Counts
        count = len(self.controller.wallpapers)
        self.count_badge.config(text=str(count))
        self.lib_lbl.config(
            text=f"● Library: {count} wallpapers",
            fg=C_ACCENT_GREEN if count > 0 else C_ACCENT_AMBER,
        )

        # Lively executable status & locate button text
        exe_found = bool(self.controller.lively_exe)
        exe_color = C_ACCENT_GREEN if exe_found else "#ef4444"
        exe_msg = "● Lively.exe detected" if exe_found else "● Lively.exe not found"
        self.exe_lbl.config(text=exe_msg, fg=exe_color)
        self.locate_btn.config(text="Change..." if exe_found else "Locate...")

        # Refresh gallery
        self.filter_wallpapers()

    def filter_wallpapers(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_wallpapers = list(self.controller.wallpapers)
        else:
            self.filtered_wallpapers = [
                wp for wp in self.controller.wallpapers
                if query in wp.title.lower() or query in wp.author.lower()
            ]
        # Clear currently rendered widgets before repopulating
        for win_id, widget in list(self.rendered_card_widgets.values()):
            self.canvas.delete(win_id)
            widget.destroy()
        self.rendered_card_widgets.clear()

        self.update_virtual_scrollregion()
        self.update_visible_cards()

    # =========================================================================
    # Action Handlers
    # =========================================================================
    def set_mode_ui(self, mode: str):
        self.controller.set_mode(mode)
        self.refresh_ui()

    def set_interval_ui(self, seconds: int):
        self.controller.set_interval(seconds)
        self.refresh_ui()

    def on_next_clicked(self):
        self.controller.next_wallpaper(explicit_user_trigger=True)
        self.refresh_ui()

    def on_prev_clicked(self):
        self.controller.previous_wallpaper()
        self.refresh_ui()

    def on_toggle_pause_clicked(self):
        self.controller.toggle_pause()
        self.refresh_ui()

    def on_autostart_toggled(self):
        self.controller.toggle_start_with_windows()

    def on_open_current_folder(self):
        curr = self.controller.current_wallpaper
        if curr and os.path.exists(curr.folder_path):
            os.startfile(curr.folder_path)
        else:
            primary = self.controller.wallpapers_dir
            if primary and os.path.exists(primary):
                os.startfile(primary)

    def on_add_custom_folder(self):
        folder = filedialog.askdirectory(title="Select Folder Containing Wallpapers or Videos")
        if folder and os.path.isdir(folder):
            self.controller.add_custom_directory(folder)
            self.controller.scan_wallpapers()
            self.thumb_cache.clear()
            self.refresh_ui()

    def on_locate_lively(self):
        filepath = filedialog.askopenfilename(
            title="Locate Lively Executable (Lively.exe or livelycu.exe)",
            filetypes=[
                ("Lively Executable", "Lively.exe;livelycu.exe"),
                ("Executable Files", "*.exe"),
                ("All Files", "*.*"),
            ],
        )
        if filepath and os.path.isfile(filepath):
            self.controller.set_custom_lively_exe(filepath)
            self.refresh_ui()

    def on_rescan_clicked(self):
        self.controller.discover_environment()
        self.controller.scan_wallpapers()
        self.thumb_cache.clear()
        self.refresh_ui()

    def on_close_window(self):
        # Minimize / hide to system tray
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.refresh_ui()
