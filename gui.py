"""
Lively Wallpaper Shuffler - Modern GUI Dashboard
Provides an interactive desktop interface with wallpaper previews, gallery selection,
timer intervals, mode settings, and system environment status.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# Color Palette (Modern Dark Theme)
BG_DARK = "#13141c"
BG_CARD = "#1c1e2d"
BG_CARD_HOVER = "#26293d"
BG_SIDEBAR = "#181a27"
BORDER_COLOR = "#2d3148"
TEXT_PRIMARY = "#f0f2f8"
TEXT_SECONDARY = "#939ab7"
TEXT_MUTED = "#686e8a"
ACCENT_BLUE = "#3b82f6"
ACCENT_BLUE_HOVER = "#2563eb"
ACCENT_GREEN = "#10b981"
ACCENT_AMBER = "#f59e0b"
ACCENT_PURPLE = "#8b5cf6"

class ShufflerGUI:
    def __init__(self, controller, root: tk.Tk):
        self.controller = controller
        self.root = root

        self.root.title("Lively Wallpaper Shuffler")
        self.root.geometry("980x680")
        self.root.minsize(860, 560)
        self.root.configure(bg=BG_DARK)

        # Set window icon
        self.set_window_icon()

        # Image cache to prevent garbage collection
        self.image_cache = {}
        self.thumb_cache = {}
        self.filtered_wallpapers = list(self.controller.wallpapers)

        # Configure styles
        self.setup_styles()

        # Build Layout
        self.build_ui()

        # Handle window close (minimize to tray)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)

        # Initial populate
        self.refresh_ui()

    def set_window_icon(self):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        if os.path.isfile(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=BG_DARK, foreground=TEXT_PRIMARY, font=("Segoe UI", 9))
        style.configure("Sidebar.TFrame", background=BG_SIDEBAR)
        style.configure("Card.TFrame", background=BG_CARD)

        # Combobox
        style.configure(
            "TCombobox",
            fieldbackground=BG_CARD,
            background=BG_CARD,
            foreground=TEXT_PRIMARY,
            bordercolor=BORDER_COLOR,
            darkcolor=BG_CARD,
            lightcolor=BG_CARD,
            arrowcolor=TEXT_PRIMARY,
            padding=5,
        )

        # Scrollbar
        style.configure(
            "Vertical.TScrollbar",
            background=BG_CARD,
            troughcolor=BG_DARK,
            bordercolor=BG_DARK,
            arrowcolor=TEXT_MUTED,
            width=10,
        )

    def build_ui(self):
        # Main Split: Left Sidebar (Controls & Active WP) + Right Panel (Gallery)
        self.sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=340, padx=18, pady=18)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.main_content = tk.Frame(self.root, bg=BG_DARK, padx=20, pady=18)
        self.main_content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.build_sidebar()
        self.build_gallery_panel()

    def build_sidebar(self):
        # App Header
        header_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR)
        header_frame.pack(fill=tk.X, pady=(0, 16))

        title_lbl = tk.Label(
            header_frame,
            text="Lively Shuffler",
            font=("Segoe UI", 16, "bold"),
            bg=BG_SIDEBAR,
            fg=TEXT_PRIMARY,
        )
        title_lbl.pack(anchor="w")

        self.status_badge = tk.Label(
            header_frame,
            text="● Active",
            font=("Segoe UI", 9, "bold"),
            bg=BG_SIDEBAR,
            fg=ACCENT_GREEN,
        )
        self.status_badge.pack(anchor="w", pady=(2, 0))

        # --- Active Wallpaper Card ---
        self.active_card = tk.Frame(self.sidebar, bg=BG_CARD, padx=12, pady=12, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.active_card.pack(fill=tk.X, pady=(0, 16))

        active_header = tk.Label(
            self.active_card,
            text="NOW PLAYING",
            font=("Segoe UI", 8, "bold"),
            bg=BG_CARD,
            fg=TEXT_MUTED,
        )
        active_header.pack(anchor="w", pady=(0, 6))

        self.active_thumb_label = tk.Label(self.active_card, bg="#0d0e14", height=110)
        self.active_thumb_label.pack(fill=tk.X, pady=(0, 8))

        self.active_title_label = tk.Label(
            self.active_card,
            text="Scanning wallpapers...",
            font=("Segoe UI", 11, "bold"),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            wraplength=280,
            justify="left",
        )
        self.active_title_label.pack(anchor="w")

        self.active_info_label = tk.Label(
            self.active_card,
            text="",
            font=("Segoe UI", 8),
            bg=BG_CARD,
            fg=TEXT_SECONDARY,
            wraplength=280,
            justify="left",
        )
        self.active_info_label.pack(anchor="w", pady=(2, 6))

        open_folder_btn = tk.Button(
            self.active_card,
            text="📁 Open Folder",
            font=("Segoe UI", 8, "bold"),
            bg=BG_CARD_HOVER,
            fg=TEXT_PRIMARY,
            activebackground=BORDER_COLOR,
            activeforeground=TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.on_open_current_folder,
        )
        open_folder_btn.pack(anchor="e")

        # --- Playback Quick Actions ---
        btn_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR)
        btn_frame.pack(fill=tk.X, pady=(0, 16))

        self.prev_btn = tk.Button(
            btn_frame,
            text="⏮ Previous",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            activebackground=BG_CARD_HOVER,
            activeforeground=TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=10,
            pady=7,
            cursor="hand2",
            command=self.on_prev_clicked,
        )
        self.prev_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        self.next_btn = tk.Button(
            btn_frame,
            text="⏭ Next",
            font=("Segoe UI", 9, "bold"),
            bg=ACCENT_BLUE,
            fg="#ffffff",
            activebackground=ACCENT_BLUE_HOVER,
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
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            activebackground=BG_CARD_HOVER,
            activeforeground=TEXT_PRIMARY,
            relief=tk.FLAT,
            pady=6,
            cursor="hand2",
            command=self.on_toggle_pause_clicked,
        )
        self.pause_btn.pack(fill=tk.X, pady=(0, 16))

        # --- Settings Section ---
        settings_label = tk.Label(
            self.sidebar,
            text="SETTINGS",
            font=("Segoe UI", 8, "bold"),
            bg=BG_SIDEBAR,
            fg=TEXT_MUTED,
        )
        settings_label.pack(anchor="w", pady=(0, 6))

        # Interval selector
        interval_row = tk.Frame(self.sidebar, bg=BG_SIDEBAR)
        interval_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(interval_row, text="Interval:", font=("Segoe UI", 9), bg=BG_SIDEBAR, fg=TEXT_SECONDARY).pack(side=tk.LEFT)

        self.interval_var = tk.StringVar()
        interval_labels = [label for label, _ in self.controller.get_interval_presets()]
        self.interval_combo = ttk.Combobox(
            interval_row,
            textvariable=self.interval_var,
            values=interval_labels,
            state="readonly",
            width=14,
        )
        self.interval_combo.pack(side=tk.RIGHT)
        self.interval_combo.bind("<<ComboboxSelected>>", self.on_interval_selected)

        # Mode selector (Shuffle vs Sequential)
        mode_row = tk.Frame(self.sidebar, bg=BG_SIDEBAR)
        mode_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(mode_row, text="Mode:", font=("Segoe UI", 9), bg=BG_SIDEBAR, fg=TEXT_SECONDARY).pack(side=tk.LEFT)

        self.mode_var = tk.StringVar(value=self.controller.mode)
        mode_combo = ttk.Combobox(
            mode_row,
            textvariable=self.mode_var,
            values=["shuffle", "sequential"],
            state="readonly",
            width=14,
        )
        mode_combo.pack(side=tk.RIGHT)
        mode_combo.bind("<<ComboboxSelected>>", self.on_mode_selected)

        # Start with Windows checkbox
        self.autostart_var = tk.BooleanVar(value=self.controller.start_with_windows)
        self.autostart_check = tk.Checkbutton(
            self.sidebar,
            text="Start with Windows",
            variable=self.autostart_var,
            font=("Segoe UI", 9),
            bg=BG_SIDEBAR,
            fg=TEXT_PRIMARY,
            selectcolor=BG_CARD,
            activebackground=BG_SIDEBAR,
            activeforeground=TEXT_PRIMARY,
            command=self.on_autostart_toggled,
        )
        self.autostart_check.pack(anchor="w", pady=(0, 14))

        # Environment status indicators
        env_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR)
        env_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        exe_found = bool(self.controller.lively_exe)
        exe_color = ACCENT_GREEN if exe_found else "#ef4444"
        exe_text = "● Lively.exe detected" if exe_found else "● Lively.exe not found"
        self.exe_status_lbl = tk.Label(env_frame, text=exe_text, font=("Segoe UI", 8), bg=BG_SIDEBAR, fg=exe_color)
        self.exe_status_lbl.pack(anchor="w")

        lib_count = len(self.controller.wallpapers)
        self.lib_status_lbl = tk.Label(
            env_frame,
            text=f"● Library: {lib_count} wallpapers loaded",
            font=("Segoe UI", 8),
            bg=BG_SIDEBAR,
            fg=ACCENT_GREEN if lib_count > 0 else ACCENT_AMBER,
        )
        self.lib_status_lbl.pack(anchor="w")

    def build_gallery_panel(self):
        # Gallery Top Controls Bar
        top_bar = tk.Frame(self.main_content, bg=BG_DARK)
        top_bar.pack(fill=tk.X, pady=(0, 14))

        title_frame = tk.Frame(top_bar, bg=BG_DARK)
        title_frame.pack(side=tk.LEFT)

        self.gallery_title = tk.Label(
            title_frame,
            text="Wallpaper Library",
            font=("Segoe UI", 15, "bold"),
            bg=BG_DARK,
            fg=TEXT_PRIMARY,
        )
        self.gallery_title.pack(side=tk.LEFT)

        self.count_badge = tk.Label(
            title_frame,
            text="0",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD,
            fg=ACCENT_BLUE,
            padx=8,
            pady=2,
        )
        self.count_badge.pack(side=tk.LEFT, padx=(10, 0))

        # Top Buttons (Refresh + Add Folder)
        btn_box = tk.Frame(top_bar, bg=BG_DARK)
        btn_box.pack(side=tk.RIGHT)

        add_folder_btn = tk.Button(
            btn_box,
            text="+ Add Folder",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            activebackground=BG_CARD_HOVER,
            activeforeground=TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.on_add_custom_folder,
        )
        add_folder_btn.pack(side=tk.LEFT, padx=(0, 6))

        rescan_btn = tk.Button(
            btn_box,
            text="🔄 Rescan",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            activebackground=BG_CARD_HOVER,
            activeforeground=TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.on_rescan_clicked,
        )
        rescan_btn.pack(side=tk.LEFT)

        # Search Bar
        search_frame = tk.Frame(self.main_content, bg=BG_CARD, padx=10, pady=6, highlightbackground=BORDER_COLOR, highlightthickness=1)
        search_frame.pack(fill=tk.X, pady=(0, 14))

        tk.Label(search_frame, text="🔍", bg=BG_CARD, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_wallpapers())
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=("Segoe UI", 10),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Scrollable Gallery Area
        self.canvas = tk.Canvas(self.main_content, bg=BG_DARK, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_content, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_DARK)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    def on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_thumbnail(self, wallpaper_item, size=(160, 95)):
        """Load and cache wallpaper thumbnail image."""
        if wallpaper_item.folder_path in self.thumb_cache:
            return self.thumb_cache[wallpaper_item.folder_path]

        thumb_img = None
        # Try finding thumbnail in folder
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
                for candidate in ("thumbnail.jpg", "thumbnail.png", "preview.gif"):
                    p = os.path.join(wallpaper_item.folder_path, candidate)
                    if os.path.isfile(p):
                        try:
                            thumb_img = Image.open(p)
                            break
                        except Exception:
                            pass

        if not thumb_img:
            # Fallback placeholder image
            thumb_img = Image.new("RGB", size, color="#1e2030")

        thumb_img = thumb_img.convert("RGBA")
        thumb_img.thumbnail(size, Image.Resampling.LANCZOS)

        # Create canvas of exact size and paste centered
        canvas_img = Image.new("RGBA", size, (20, 22, 34, 255))
        offset_x = (size[0] - thumb_img.width) // 2
        offset_y = (size[1] - thumb_img.height) // 2
        canvas_img.paste(thumb_img, (offset_x, offset_y), thumb_img)

        tk_img = ImageTk.PhotoImage(canvas_img)
        self.thumb_cache[wallpaper_item.folder_path] = tk_img
        return tk_img

    def refresh_ui(self):
        """Update all elements on the dashboard."""
        # 1. Update current wallpaper info
        curr = self.controller.current_wallpaper
        if curr:
            self.active_title_label.config(text=curr.title)
            info_str = f"Type: {curr.wp_type.capitalize() if curr.wp_type else 'Wallpaper'}"
            if curr.author:
                info_str += f" • Author: {curr.author}"
            self.active_info_label.config(text=info_str)

            # Load active thumbnail
            active_img = self.load_thumbnail(curr, size=(280, 120))
            self.active_thumb_label.config(image=active_img)
            self.active_thumb_label.image = active_img
        else:
            self.active_title_label.config(text="No wallpaper active")
            self.active_info_label.config(text="")

        # 2. Update status badge & pause button
        if self.controller.is_paused:
            self.status_badge.config(text="● Paused", fg=ACCENT_AMBER)
            self.pause_btn.config(text="▶ Resume Shuffle", bg=ACCENT_GREEN, fg="#ffffff")
        else:
            label = self.controller.format_interval(self.controller.interval_seconds)
            self.status_badge.config(
                text=f"● Active ({self.controller.mode.capitalize()} • {label})",
                fg=ACCENT_GREEN,
            )
            self.pause_btn.config(text="⏸ Pause Shuffle", bg=BG_CARD, fg=TEXT_PRIMARY)

        # 3. Update interval combo selection
        curr_label = self.controller.format_interval(self.controller.interval_seconds)
        self.interval_var.set(curr_label)

        # 4. Update count badge & library status
        count = len(self.controller.wallpapers)
        self.count_badge.config(text=str(count))
        self.lib_status_lbl.config(
            text=f"● Library: {count} wallpapers loaded",
            fg=ACCENT_GREEN if count > 0 else ACCENT_AMBER,
        )

        # 5. Render wallpapers gallery
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
        self.render_gallery()

    def render_gallery(self):
        # Clear existing items
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.filtered_wallpapers:
            no_lbl = tk.Label(
                self.scrollable_frame,
                text="No wallpapers found matching your search.",
                font=("Segoe UI", 11),
                bg=BG_DARK,
                fg=TEXT_MUTED,
                pady=40,
            )
            no_lbl.pack()
            return

        # Render rows of cards (3 columns or 2 columns based on width)
        cols = 3
        for idx, wp in enumerate(self.filtered_wallpapers):
            row = idx // cols
            col = idx % cols

            card = self.create_wallpaper_card(self.scrollable_frame, wp)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        # Equal column weights
        for c in range(cols):
            self.scrollable_frame.columnconfigure(c, weight=1)

    def create_wallpaper_card(self, parent, wallpaper):
        is_active = (self.controller.current_wallpaper == wallpaper)
        border_c = ACCENT_BLUE if is_active else BORDER_COLOR

        card = tk.Frame(
            parent,
            bg=BG_CARD,
            padx=8,
            pady=8,
            highlightbackground=border_c,
            highlightthickness=2 if is_active else 1,
            cursor="hand2",
        )

        # Thumbnail
        thumb = self.load_thumbnail(wallpaper, size=(180, 100))
        thumb_lbl = tk.Label(card, image=thumb, bg="#0d0e14")
        thumb_lbl.image = thumb
        thumb_lbl.pack(fill=tk.X, pady=(0, 6))

        # Title
        display_title = wallpaper.title
        if len(display_title) > 28:
            display_title = display_title[:25] + "..."
        title_lbl = tk.Label(
            card,
            text=display_title,
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD,
            fg=TEXT_PRIMARY if not is_active else ACCENT_BLUE,
            anchor="w",
        )
        title_lbl.pack(fill=tk.X)

        # Subtitle / active badge
        if is_active:
            sub_lbl = tk.Label(
                card,
                text="ACTIVE NOW",
                font=("Segoe UI", 7, "bold"),
                bg=BG_CARD,
                fg=ACCENT_BLUE,
                anchor="w",
            )
            sub_lbl.pack(fill=tk.X, pady=(2, 0))
        else:
            sub_text = wallpaper.wp_type.capitalize() if wallpaper.wp_type else "Wallpaper"
            sub_lbl = tk.Label(
                card,
                text=sub_text,
                font=("Segoe UI", 7),
                bg=BG_CARD,
                fg=TEXT_MUTED,
                anchor="w",
            )
            sub_lbl.pack(fill=tk.X, pady=(2, 0))

        # Click handler to switch wallpaper
        def on_click(e):
            self.controller.select_wallpaper(wallpaper)
            self.refresh_ui()

        card.bind("<Button-1>", on_click)
        thumb_lbl.bind("<Button-1>", on_click)
        title_lbl.bind("<Button-1>", on_click)
        sub_lbl.bind("<Button-1>", on_click)

        return card

    # --- Action Handlers ---
    def on_next_clicked(self):
        self.controller.next_wallpaper(explicit_user_trigger=True)
        self.refresh_ui()

    def on_prev_clicked(self):
        self.controller.previous_wallpaper()
        self.refresh_ui()

    def on_toggle_pause_clicked(self):
        self.controller.toggle_pause()
        self.refresh_ui()

    def on_interval_selected(self, event):
        selected_label = self.interval_var.get()
        for label, sec in self.controller.get_interval_presets():
            if label == selected_label:
                self.controller.set_interval(sec)
                self.refresh_ui()
                break

    def on_mode_selected(self, event):
        self.controller.set_mode(self.mode_var.get())
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

    def on_rescan_clicked(self):
        self.controller.discover_environment()
        self.controller.scan_wallpapers()
        self.thumb_cache.clear()
        self.refresh_ui()

    def on_close_window(self):
        # Minimize/hide to system tray instead of destroying
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.refresh_ui()
