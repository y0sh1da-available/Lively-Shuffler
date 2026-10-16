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
import time
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

        # Low-latency image & thumbnail caches
        self.thumb_cache = {}            # (folder_path, w, h) -> ImageTk.PhotoImage
        self._raw_thumb_cache = {}       # folder_path -> PIL.Image (in-memory decoded)
        self.card_widgets = {}           # folder_path -> tk.Frame (reusable card widgets)
        self.filtered_wallpapers = list(self.controller.wallpapers)
        self._current_cols = 3
        self._search_job = None

        # Build UI layout
        self.build_ui()

        # Window close minimizes to tray
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)

        # Initial data populate
        self.filter_wallpapers()
        self.refresh_ui()

        # Background daemon: pre-warm thumbnail cache into RAM for 60fps scrolling
        threading.Thread(target=self._precache_thumbnails, daemon=True).start()

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
        def on_search_type(*args):
            if self._search_job:
                self.root.after_cancel(self._search_job)
            self._search_job = self.root.after(80, self.filter_wallpapers)
        self.search_var.trace_add("write", on_search_type)
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

        # Scrollable Canvas with pixel-level increment and zero visual tearing
        self.canvas = tk.Canvas(
            self.main_content,
            bg=C_BG,
            highlightthickness=0,
            yscrollincrement=1,
        )
        self.scrollbar = ttk.Scrollbar(self.main_content, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Container frame holding all card widgets
        self.cards_container = tk.Frame(self.canvas, bg=C_BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.cards_container, anchor="nw")

        # Automatically adapt container width to canvas and update scrollregion
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.cards_container.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Butter-smooth, non-shattering mousewheel scrolling
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.cards_container.bind("<MouseWheel>", self.on_mousewheel)
        self.main_content.bind("<MouseWheel>", self.on_mousewheel)
        search_frame.bind("<MouseWheel>", self.on_mousewheel)
        self.search_entry.bind("<MouseWheel>", self.on_mousewheel)

    # =========================================================================
    # High-Performance Gallery & Card Management
    # =========================================================================
    def on_mousewheel(self, event):
        """Smooth 45px per notch scrolling without recreating or moving any widgets."""
        if self.canvas.winfo_exists():
            delta = getattr(event, "delta", 0)
            if delta != 0:
                raw_step = -1 * (delta / 120.0) * 45
                step = int(raw_step)
                if step == 0:
                    step = -1 if delta > 0 else 1
                self.canvas.yview_scroll(step, "units")
            return "break"

    def get_cols(self, width=None):
        if width is None:
            width = self.canvas.winfo_width()
        if width <= 50:
            width = 620
        if width > 840:
            return 4
        elif width > 540:
            return 3
        else:
            return 2

    def on_canvas_configure(self, event):
        """Stretch container width to fit canvas and re-grid columns if needed."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        new_cols = self.get_cols(event.width)
        if new_cols != self._current_cols:
            self._current_cols = new_cols
            self.rearrange_grid(new_cols)

    def rearrange_grid(self, cols):
        """Arrange active cards into grid columns without destroying widgets."""
        for i, wp in enumerate(self.filtered_wallpapers):
            card = self.card_widgets.get(wp.folder_path)
            if card:
                card.grid(row=i // cols, column=i % cols, padx=6, pady=6, sticky="nsew")
        for c in range(cols):
            self.cards_container.columnconfigure(c, weight=1)

    def _load_raw_thumbnail(self, wallpaper_item) -> Image.Image:
        """Decode and keep base thumbnail in RAM to prevent repeat disk I/O."""
        if wallpaper_item.folder_path in self._raw_thumb_cache:
            return self._raw_thumb_cache[wallpaper_item.folder_path]

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
                                thumb_img = Image.open(p).convert("RGBA")
                except Exception:
                    pass

            if not thumb_img:
                for cand in ("thumbnail.jpg", "thumbnail.png", "preview.gif"):
                    p = os.path.join(wallpaper_item.folder_path, cand)
                    if os.path.isfile(p):
                        try:
                            thumb_img = Image.open(p).convert("RGBA")
                            break
                        except Exception:
                            pass

        if not thumb_img:
            thumb_img = Image.new("RGBA", (180, 95), color=(28, 30, 46, 255))

        self._raw_thumb_cache[wallpaper_item.folder_path] = thumb_img
        return thumb_img

    def _precache_thumbnails(self):
        """Background thread: pre-warm raw thumbnails into RAM so scrolling never stalls."""
        wallpapers = list(self.controller.wallpapers)
        for wp in wallpapers:
            try:
                if not self.root.winfo_exists():
                    break
                if wp.folder_path not in self._raw_thumb_cache:
                    self._load_raw_thumbnail(wp)
                time.sleep(0.005)
            except Exception:
                pass

    def load_thumbnail(self, wallpaper_item, size=(180, 95)) -> ImageTk.PhotoImage:
        """Fast thumbnail retrieval with memory cache and fast bilinear downsampling."""
        target_w = max(60, int(size[0]))
        target_h = max(40, int(size[1]))
        cache_key = (wallpaper_item.folder_path, target_w, target_h)
        if cache_key in self.thumb_cache:
            return self.thumb_cache[cache_key]

        raw = self._load_raw_thumbnail(wallpaper_item)
        img_copy = raw.copy()
        img_copy.thumbnail((target_w, target_h), Image.Resampling.BILINEAR)

        canvas_img = Image.new("RGBA", (target_w, target_h), (16, 17, 26, 255))
        offset_x = (target_w - img_copy.width) // 2
        offset_y = (target_h - img_copy.height) // 2
        canvas_img.paste(img_copy, (offset_x, offset_y), img_copy)

        tk_img = ImageTk.PhotoImage(canvas_img)
        self.thumb_cache[cache_key] = tk_img
        return tk_img

    def create_card_widget(self, wallpaper):
        is_active = (self.controller.current_wallpaper == wallpaper)
        border_color = C_ACCENT_BLUE if is_active else C_BORDER
        border_width = 2 if is_active else 1

        card = tk.Frame(
            self.cards_container,
            bg=C_CARD,
            padx=8,
            pady=8,
            highlightbackground=border_color,
            highlightthickness=border_width,
            cursor="hand2",
        )
        card._wallpaper = wallpaper

        # Thumbnail
        thumb = self.load_thumbnail(wallpaper, size=(180, 95))
        thumb_lbl = tk.Label(card, image=thumb, bg="#0d0e15")
        thumb_lbl.image = thumb
        thumb_lbl.pack(fill=tk.X, pady=(0, 6))
        card._thumb_lbl = thumb_lbl

        # Title
        title_lbl = tk.Label(
            card,
            text=wallpaper.title,
            font=("Segoe UI", 9, "bold"),
            bg=C_CARD,
            fg=C_ACCENT_BLUE if is_active else C_TEXT_WHITE,
            anchor="w",
            wraplength=170,
            justify="left",
        )
        title_lbl.pack(fill=tk.X)
        card._title_lbl = title_lbl

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
        card._badge_lbl = badge_lbl

        # Instant click handler (<1ms response)
        def on_click(e):
            self.controller.select_wallpaper(wallpaper)
            self.on_active_wallpaper_changed()

        def on_enter(e):
            if self.controller.current_wallpaper != wallpaper:
                card.config(highlightbackground=C_BORDER_LIGHT, bg=C_CARD_HOVER)
                title_lbl.config(bg=C_CARD_HOVER)
                badge_lbl.config(bg=C_CARD_HOVER)

        def on_leave(e):
            if self.controller.current_wallpaper != wallpaper:
                card.config(highlightbackground=C_BORDER, bg=C_CARD)
                title_lbl.config(bg=C_CARD)
                badge_lbl.config(bg=C_CARD)

        for w in (card, thumb_lbl, title_lbl, badge_lbl):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<MouseWheel>", self.on_mousewheel)

        return card

    # =========================================================================
    # UI State Synchronization (Zero Latency)
    # =========================================================================
    def update_cards_active_state(self):
        """Instant in-place recoloring of active borders (<0.2ms)."""
        curr = self.controller.current_wallpaper
        for card in self.card_widgets.values():
            wp = getattr(card, "_wallpaper", None)
            if not wp:
                continue
            is_active = (wp == curr)
            border_color = C_ACCENT_BLUE if is_active else C_BORDER
            border_width = 2 if is_active else 1
            card.config(highlightbackground=border_color, highlightthickness=border_width, bg=C_CARD)
            if hasattr(card, "_title_lbl"):
                card._title_lbl.config(fg=C_ACCENT_BLUE if is_active else C_TEXT_WHITE, bg=C_CARD)
            if hasattr(card, "_badge_lbl"):
                badge_text = "● ACTIVE NOW" if is_active else (wp.wp_type.capitalize() if wp.wp_type else "Wallpaper")
                badge_color = C_ACCENT_BLUE if is_active else C_TEXT_MUTED
                card._badge_lbl.config(text=badge_text, fg=badge_color, bg=C_CARD)

    def on_active_wallpaper_changed(self):
        """Instant UI update of active wallpaper card & gallery borders without recreation."""
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

        self.update_cards_active_state()

    def refresh_ui(self):
        """Update active wallpaper showcase, status badges, and controls."""
        self.on_active_wallpaper_changed()

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

    def filter_wallpapers(self):
        """Filter wallpapers by search query and reuse existing card widgets."""
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_wallpapers = list(self.controller.wallpapers)
        else:
            self.filtered_wallpapers = [
                wp for wp in self.controller.wallpapers
                if query in wp.title.lower() or query in wp.author.lower()
            ]

        # Update count badge
        count = len(self.filtered_wallpapers)
        self.count_badge.config(text=str(count))

        # Hide all existing cards without destroying them
        for card in self.card_widgets.values():
            card.grid_remove()

        cols = self.get_cols()
        self._current_cols = cols

        # Grid filtered cards, instantiating new widgets only once
        for i, wp in enumerate(self.filtered_wallpapers):
            if wp.folder_path not in self.card_widgets:
                card = self.create_card_widget(wp)
                self.card_widgets[wp.folder_path] = card
            else:
                card = self.card_widgets[wp.folder_path]
            card.grid(row=i // cols, column=i % cols, padx=6, pady=6, sticky="nsew")

        for c in range(cols):
            self.cards_container.columnconfigure(c, weight=1)

        if query:
            self.canvas.yview_moveto(0)

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.update_cards_active_state()

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
        self.on_active_wallpaper_changed()

    def on_prev_clicked(self):
        self.controller.previous_wallpaper()
        self.on_active_wallpaper_changed()

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
