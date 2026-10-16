"""
Lively Wallpaper Shuffler - Zero-Config Desktop Utility
A lightweight, standalone Windows background companion for Lively Wallpaper.
Automatically cycles and shuffles wallpapers with modern process execution and system-tray controls.
"""

import os
import sys
import json
import time
import random
import ctypes
import ctypes.wintypes
import winreg
import logging
import threading
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import pystray

APP_NAME = "Lively Wallpaper Shuffler"
APP_VERSION = "1.0.0"
MUTEX_NAME = "Global\\LivelyWallpaperShuffler_SingleInstance_Mutex"

# Common intervals (in seconds)
INTERVAL_PRESETS = [
    ("30 seconds", 30),
    ("1 minute", 60),
    ("5 minutes", 300),
    ("10 minutes", 600),
    ("15 minutes", 900),
    ("30 minutes", 1800),
    ("1 hour", 3600),
    ("2 hours", 7200),
    ("4 hours", 14400),
]

# Configure AppData directory & logger
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
CONFIG_DIR = os.path.join(LOCAL_APPDATA, "Lively Wallpaper Shuffler")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LOG_FILE = os.path.join(CONFIG_DIR, "shuffler.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("LivelyShuffler")


# ==============================================================================
# Windows Process Discovery via Win32 Toolhelp32Snapshot
# ==============================================================================
TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("cntUsage", ctypes.wintypes.DWORD),
        ("th32ProcessID", ctypes.wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", ctypes.wintypes.DWORD),
        ("cntThreads", ctypes.wintypes.DWORD),
        ("th32ParentProcessID", ctypes.wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def find_lively_process_path() -> str | None:
    """Find the path of the running Lively.exe or livelycu.exe process using Win32 API."""
    kernel32 = ctypes.windll.kernel32
    h_snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h_snap == -1:
        return None

    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    found_path = None

    if kernel32.Process32FirstW(h_snap, ctypes.byref(pe)):
        while True:
            exe_name = pe.szExeFile.lower()
            if exe_name in ("lively.exe", "livelycu.exe"):
                h_proc = kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION, False, pe.th32ProcessID
                )
                if h_proc:
                    buf = ctypes.create_unicode_buffer(1024)
                    size = ctypes.wintypes.DWORD(len(buf))
                    if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                        found_path = buf.value
                        kernel32.CloseHandle(h_proc)
                        break
                    kernel32.CloseHandle(h_proc)
            elif exe_name.startswith("lively"):
                h_proc = kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION, False, pe.th32ProcessID
                )
                if h_proc:
                    buf = ctypes.create_unicode_buffer(1024)
                    size = ctypes.wintypes.DWORD(len(buf))
                    if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                        folder = os.path.dirname(buf.value)
                        for cand in ("Lively.exe", "livelycu.exe"):
                            cand_path = os.path.join(folder, cand)
                            if os.path.isfile(cand_path):
                                found_path = cand_path
                                break
                    kernel32.CloseHandle(h_proc)
                    if found_path:
                        break
            if not kernel32.Process32NextW(h_snap, ctypes.byref(pe)):
                break

    kernel32.CloseHandle(h_snap)
    return found_path


# ==============================================================================
# Auto-Discovery Engine
# ==============================================================================
class DiscoveryEngine:
    @staticmethod
    def find_lively_executable() -> str | None:
        """Dynamically detect Lively executable through process snapshot, standard paths, or registry."""
        # 1. Fallback / Priority: Check active running process
        proc_path = find_lively_process_path()
        if proc_path and os.path.isfile(proc_path):
            logger.info("Discovered Lively executable via active process: %s", proc_path)
            return proc_path

        # 2. Check standard installation directories
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        candidates = [
            # User install (default modern desktop installer)
            os.path.join(LOCAL_APPDATA, "Programs", "Lively Wallpaper", "Lively.exe"),
            os.path.join(LOCAL_APPDATA, "Programs", "Lively Wallpaper", "livelycu.exe"),
            # System wide installs
            os.path.join(prog_files, "Lively Wallpaper", "Lively.exe"),
            os.path.join(prog_files, "Lively Wallpaper", "livelycu.exe"),
            os.path.join(prog_files_x86, "Lively Wallpaper", "Lively.exe"),
            os.path.join(prog_files_x86, "Lively Wallpaper", "livelycu.exe"),
            # Microsoft Store version alias
            os.path.join(LOCAL_APPDATA, "Microsoft", "WindowsApps", "Lively.exe"),
        ]

        for path in candidates:
            if os.path.isfile(path):
                logger.info("Discovered Lively executable at standard path: %s", path)
                return path

        # 3. Check Windows Registry App Paths
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(
                    root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Lively.exe"
                ) as key:
                    val, _ = winreg.QueryValueEx(key, "")
                    if val and os.path.isfile(val):
                        logger.info("Discovered Lively executable via Registry App Paths: %s", val)
                        return val
            except OSError:
                pass

        logger.warning("Could not auto-discover Lively executable.")
        return None

    @staticmethod
    def find_wallpapers_directory() -> str | None:
        """Resolve the active wallpapers library directory."""
        # 1. Check Lively's Settings.json for custom WallpaperDir
        settings_file = os.path.join(LOCAL_APPDATA, "Lively Wallpaper", "Settings.json")
        if os.path.isfile(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    custom_dir = data.get("WallpaperDir")
                    if custom_dir:
                        # Lively usually stores wallpapers under WallpaperDir\wallpapers
                        candidate_sub = os.path.join(custom_dir, "wallpapers")
                        if os.path.isdir(candidate_sub):
                            logger.info("Discovered wallpapers dir via Settings.json: %s", candidate_sub)
                            return candidate_sub
                        if os.path.isdir(custom_dir):
                            logger.info("Discovered wallpapers dir via Settings.json: %s", custom_dir)
                            return custom_dir
            except Exception as e:
                logger.warning("Failed parsing Settings.json: %s", e)

        # 2. Default standard path
        default_dir = os.path.join(LOCAL_APPDATA, "Lively Wallpaper", "Library", "wallpapers")
        if os.path.isdir(default_dir):
            logger.info("Discovered default wallpapers directory: %s", default_dir)
            return default_dir

        # 3. Alternative fallback
        alt_dir = os.path.join(LOCAL_APPDATA, "Lively Wallpaper", "Library")
        if os.path.isdir(alt_dir):
            return alt_dir

        logger.warning("Wallpapers library directory not found.")
        return None

    @staticmethod
    def get_currently_active_wallpaper() -> tuple[str | None, str | None]:
        """Read WallpaperLayout.json to find the currently active wallpaper path and title."""
        layout_file = os.path.join(LOCAL_APPDATA, "Lively Wallpaper", "WallpaperLayout.json")
        if not os.path.isfile(layout_file):
            return None, None

        try:
            with open(layout_file, "r", encoding="utf-8") as f:
                screens = json.load(f)
                if isinstance(screens, list) and len(screens) > 0:
                    info_path = screens[0].get("LivelyInfoPath")
                    if info_path:
                        folder_path = (
                            info_path if os.path.isdir(info_path) else os.path.dirname(info_path)
                        )
                        json_file = (
                            os.path.join(folder_path, "LivelyInfo.json")
                            if os.path.isdir(folder_path)
                            else info_path
                        )
                        title = None
                        if os.path.isfile(json_file):
                            try:
                                with open(json_file, "r", encoding="utf-8") as jf:
                                    info_data = json.load(jf)
                                    title = info_data.get("Title")
                            except Exception:
                                pass
                        return folder_path, (title or os.path.basename(folder_path))
        except Exception as e:
            logger.debug("Error checking active wallpaper: %s", e)

        return None, None


# ==============================================================================
# Autostart (Windows Registry) Manager
# ==============================================================================
class AutostartManager:
    REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_KEY_NAME = "LivelyWallpaperShuffler"

    @classmethod
    def is_enabled(cls) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, cls.APP_KEY_NAME)
                return True
        except OSError:
            return False

    @classmethod
    def set_enabled(cls, enable: bool):
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                if enable:
                    exe_path = sys.executable
                    # Quote path if needed
                    val = f'"{exe_path}"'
                    winreg.SetValueEx(key, cls.APP_KEY_NAME, 0, winreg.REG_SZ, val)
                    logger.info("Enabled auto-start with Windows: %s", val)
                else:
                    try:
                        winreg.DeleteValue(key, cls.APP_KEY_NAME)
                        logger.info("Disabled auto-start with Windows")
                    except FileNotFoundError:
                        pass
        except OSError as e:
            logger.error("Failed to update Run registry key: %s", e)


# ==============================================================================
# Shuffler Engine & State Management
# ==============================================================================
class WallpaperItem:
    def __init__(self, folder_path: str, title: str, author: str = "", wp_type: str = ""):
        self.folder_path = folder_path
        self.title = title
        self.author = author
        self.wp_type = wp_type

    def __repr__(self):
        return f"<Wallpaper: {self.title}>"


class ShufflerController:
    def __init__(self):
        self.lively_exe: str | None = None
        self.wallpapers_dir: str | None = None
        self.wallpapers: list[WallpaperItem] = []
        self.current_wallpaper: WallpaperItem | None = None
        self.history: list[WallpaperItem] = []
        self.history_index: int = -1

        # Configuration defaults
        self.interval_seconds = 300
        self.mode = "shuffle"  # 'shuffle' or 'sequential'
        self.is_paused = False
        self.start_with_windows = False
        self.sequential_index = 0

        # Concurrency & loop control
        self.lock = threading.Lock()
        self.wake_event = threading.Event()
        self.is_running = True
        self.worker_thread: threading.Thread | None = None
        self.tray_icon: pystray.Icon | None = None

        self.load_config()
        self.discover_environment()
        self.scan_wallpapers()

    def load_config(self):
        """Load user preferences from config file."""
        if os.path.isfile(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.interval_seconds = cfg.get("interval_seconds", 300)
                    self.mode = cfg.get("mode", "shuffle")
                    self.is_paused = cfg.get("is_paused", False)
            except Exception as e:
                logger.error("Failed loading config: %s", e)
        self.start_with_windows = AutostartManager.is_enabled()

    def save_config(self):
        """Persist user preferences."""
        try:
            cfg = {
                "interval_seconds": self.interval_seconds,
                "mode": self.mode,
                "is_paused": self.is_paused,
                "start_with_windows": self.start_with_windows,
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            logger.error("Failed saving config: %s", e)

    def discover_environment(self):
        """Auto-discover Lively and Wallpapers path."""
        self.lively_exe = DiscoveryEngine.find_lively_executable()
        self.wallpapers_dir = DiscoveryEngine.find_wallpapers_directory()

    def scan_wallpapers(self):
        """Scan wallpapers directory for valid Lively wallpapers (folders with LivelyInfo.json)."""
        with self.lock:
            self.wallpapers.clear()
            if not self.wallpapers_dir or not os.path.isdir(self.wallpapers_dir):
                logger.warning("Scan skipped: invalid wallpapers directory.")
                return

            try:
                for entry in os.scandir(self.wallpapers_dir):
                    if entry.is_dir():
                        info_file = os.path.join(entry.path, "LivelyInfo.json")
                        if os.path.isfile(info_file):
                            title = entry.name
                            author = ""
                            wp_type = ""
                            try:
                                with open(info_file, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    title = data.get("Title") or entry.name
                                    author = data.get("Author") or ""
                                    wp_type = data.get("Type") or ""
                            except Exception as e:
                                logger.debug("Error reading %s: %s", info_file, e)

                            item = WallpaperItem(entry.path, title, author, wp_type)
                            self.wallpapers.append(item)

                # Sort naturally by title
                self.wallpapers.sort(key=lambda x: x.title.lower())
                logger.info("Scanned %d wallpapers from %s", len(self.wallpapers), self.wallpapers_dir)

                # Detect currently active wallpaper on startup
                active_path, active_title = DiscoveryEngine.get_currently_active_wallpaper()
                if active_path:
                    for wp in self.wallpapers:
                        if os.path.normpath(wp.folder_path) == os.path.normpath(active_path):
                            self.current_wallpaper = wp
                            if not self.history:
                                self.history.append(wp)
                                self.history_index = 0
                            break
            except Exception as e:
                logger.error("Error during scan_wallpapers: %s", e)

    def set_wallpaper(self, wallpaper: WallpaperItem) -> bool:
        """Execute Lively command silently to switch wallpaper."""
        if not self.lively_exe or not os.path.isfile(self.lively_exe):
            self.lively_exe = DiscoveryEngine.find_lively_executable()
            if not self.lively_exe:
                logger.error("Cannot set wallpaper: Lively executable not found.")
                if self.tray_icon:
                    self.tray_icon.notify(
                        "Lively Wallpaper executable not found!\nPlease ensure Lively is installed or running.",
                        title="Lively Shuffler Warning",
                    )
                return False

        cmd = [self.lively_exe, "setwp", "--file", wallpaper.folder_path]
        logger.info("Switching wallpaper to: %s (%s)", wallpaper.title, wallpaper.folder_path)

        try:
            # CREATE_NO_WINDOW ensures no command prompt or terminal window pops up
            creation_flags = 0x08000000  # CREATE_NO_WINDOW
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = 0  # SW_HIDE

            res = subprocess.run(
                cmd,
                creationflags=creation_flags,
                startupinfo=startup_info,
                capture_output=True,
                check=False,
            )

            if res.returncode == 0:
                self.current_wallpaper = wallpaper
                logger.info("Successfully switched wallpaper to: %s", wallpaper.title)
                self.update_tray_tooltip()
                return True
            else:
                logger.warning(
                    "Lively returned non-zero code %d: %s",
                    res.returncode,
                    res.stderr.decode(errors="replace"),
                )
                return False
        except Exception as e:
            logger.error("Failed to execute Lively command: %s", e)
            return False

    def next_wallpaper(self, explicit_user_trigger: bool = True):
        """Advance to the next wallpaper based on current mode."""
        with self.lock:
            if not self.wallpapers:
                self.scan_wallpapers()
            if not self.wallpapers:
                logger.warning("No wallpapers available to switch.")
                return

            # If user had gone back into history and clicks next
            if (
                explicit_user_trigger
                and self.history
                and 0 <= self.history_index < len(self.history) - 1
            ):
                self.history_index += 1
                selected = self.history[self.history_index]
            else:
                if self.mode == "shuffle":
                    # Avoid picking the exact same wallpaper if multiple are available
                    candidates = (
                        [wp for wp in self.wallpapers if wp != self.current_wallpaper]
                        if len(self.wallpapers) > 1
                        else self.wallpapers
                    )
                    selected = random.choice(candidates)
                else:
                    # Sequential
                    if self.current_wallpaper in self.wallpapers:
                        idx = (self.wallpapers.index(self.current_wallpaper) + 1) % len(
                            self.wallpapers
                        )
                    else:
                        idx = self.sequential_index % len(self.wallpapers)
                    selected = self.wallpapers[idx]
                    self.sequential_index = (idx + 1) % len(self.wallpapers)

                self.history.append(selected)
                # Keep history reasonable size (last 50)
                if len(self.history) > 50:
                    self.history.pop(0)
                self.history_index = len(self.history) - 1

        self.set_wallpaper(selected)

        # Reset timer countdown on explicit trigger
        if explicit_user_trigger:
            self.wake_event.set()

    def previous_wallpaper(self):
        """Go back to the previously active wallpaper in history."""
        with self.lock:
            if self.history and self.history_index > 0:
                self.history_index -= 1
                selected = self.history[self.history_index]
                self.set_wallpaper(selected)
                self.wake_event.set()
            else:
                logger.info("No earlier wallpaper in history.")

    def select_wallpaper(self, wallpaper: WallpaperItem):
        """Directly switch to a specific wallpaper."""
        with self.lock:
            self.history.append(wallpaper)
            self.history_index = len(self.history) - 1
        self.set_wallpaper(wallpaper)
        self.wake_event.set()

    def toggle_pause(self):
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        self.save_config()
        self.update_tray_tooltip()
        self.wake_event.set()
        logger.info("Shuffler pause state toggled to: %s", self.is_paused)

    def set_interval(self, seconds: int):
        """Update interval preset."""
        self.interval_seconds = seconds
        self.save_config()
        self.update_tray_tooltip()
        self.wake_event.set()
        logger.info("Interval changed to: %d seconds", seconds)

    def set_mode(self, mode: str):
        """Update shuffle mode."""
        if mode in ("shuffle", "sequential"):
            self.mode = mode
            self.save_config()
            self.wake_event.set()
            logger.info("Mode changed to: %s", mode)

    def toggle_start_with_windows(self):
        """Toggle autostart in Windows Registry."""
        self.start_with_windows = not self.start_with_windows
        AutostartManager.set_enabled(self.start_with_windows)
        self.save_config()

    def update_tray_tooltip(self):
        """Update system tray tooltip and menu labels."""
        if not self.tray_icon:
            return
        status = "Paused" if self.is_paused else f"Every {self.format_interval(self.interval_seconds)}"
        title = self.current_wallpaper.title if self.current_wallpaper else "None"
        tooltip = f"{APP_NAME}\nWallpaper: {title}\nStatus: {status} ({self.mode.capitalize()})"
        # Max tooltip length on Windows is ~128 chars
        self.tray_icon.title = tooltip[:127]
        try:
            self.tray_icon.update_menu()
        except Exception:
            pass

    @staticmethod
    def format_interval(seconds: int) -> str:
        for label, sec in INTERVAL_PRESETS:
            if sec == seconds:
                return label
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        else:
            return f"{seconds // 3600}h"

    def background_loop(self):
        """Daemon thread running the timed shuffle loop."""
        logger.info("Background timer loop started.")
        while self.is_running:
            if self.is_paused:
                # Sleep and wait for wake event or resume
                self.wake_event.wait(timeout=1.0)
                self.wake_event.clear()
                continue

            # Wait for interval duration, wake up early if event is triggered
            woken = self.wake_event.wait(timeout=self.interval_seconds)
            self.wake_event.clear()

            if not self.is_running:
                break

            # If awakened by user action, don't double-trigger, continue next cycle
            if woken:
                continue

            # Timer expired naturally: cycle wallpaper
            if not self.is_paused and self.is_running:
                self.next_wallpaper(explicit_user_trigger=False)

        logger.info("Background timer loop finished.")

    def start(self):
        """Start the background worker thread."""
        self.is_running = True
        self.worker_thread = threading.Thread(target=self.background_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """Terminate the background worker thread."""
        self.is_running = False
        self.wake_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        logger.info("Shuffler controller stopped.")


# ==============================================================================
# Icon Generation & Tray UI
# ==============================================================================
def get_tray_image() -> Image.Image:
    """Load or generate the system tray icon."""
    # Look in PyInstaller temp dir or alongside executable/script
    base_dirs = [
        getattr(sys, "_MEIPASS", ""),
        os.path.dirname(os.path.abspath(sys.argv[0])),
        os.path.dirname(os.path.abspath(__file__)),
    ]
    for b in base_dirs:
        if not b:
            continue
        for candidate in ("app_icon.png", "app_icon.ico"):
            p = os.path.join(b, candidate)
            if os.path.isfile(p):
                try:
                    return Image.open(p)
                except Exception:
                    pass

    # Dynamic fallback icon generation (modern vibrant 64x64 icon)
    w, h = 64, 64
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([2, 2, 61, 61], radius=14, fill=(30, 27, 75, 255), outline=(129, 140, 248, 255), width=2)
    draw.rounded_rectangle([18, 12, 52, 46], radius=6, fill=(59, 130, 246, 200), outline=(147, 197, 253, 255), width=1)
    draw.rounded_rectangle([12, 18, 46, 52], radius=6, fill=(139, 92, 246, 230), outline=(216, 180, 254, 255), width=1)
    draw.ellipse([25, 31, 33, 39], fill=(245, 158, 11, 240))
    return img


def build_system_tray(controller: ShufflerController) -> pystray.Icon:
    """Build the pystray context menu and icon."""

    def on_next(icon, item):
        controller.next_wallpaper(explicit_user_trigger=True)

    def on_prev(icon, item):
        controller.previous_wallpaper()

    def on_toggle_pause(icon, item):
        controller.toggle_pause()

    def make_interval_action(sec):
        return lambda icon, item: controller.set_interval(sec)

    def make_interval_check(sec):
        return lambda item: controller.interval_seconds == sec

    def make_mode_action(m):
        return lambda icon, item: controller.set_mode(m)

    def make_mode_check(m):
        return lambda item: controller.mode == m

    def make_select_action(wp):
        return lambda icon, item: controller.select_wallpaper(wp)

    def make_select_check(wp):
        return lambda item: controller.current_wallpaper == wp

    def on_open_folder(icon, item):
        if controller.wallpapers_dir and os.path.isdir(controller.wallpapers_dir):
            os.startfile(controller.wallpapers_dir)
        else:
            local = os.environ.get("LOCALAPPDATA", "")
            p = os.path.join(local, "Lively Wallpaper", "Library", "wallpapers")
            if os.path.exists(p):
                os.startfile(p)

    def on_autostart_toggle(icon, item):
        controller.toggle_start_with_windows()

    def on_reload(icon, item):
        controller.discover_environment()
        controller.scan_wallpapers()
        controller.update_tray_tooltip()

    def on_exit(icon, item):
        controller.stop()
        icon.stop()

    # Dynamic Menu Generators
    def get_interval_items():
        for label, sec in INTERVAL_PRESETS:
            yield pystray.MenuItem(
                label,
                make_interval_action(sec),
                checked=make_interval_check(sec),
                radio=True,
            )

    def get_mode_items():
        yield pystray.MenuItem(
            "Shuffle (Random)",
            make_mode_action("shuffle"),
            checked=make_mode_check("shuffle"),
            radio=True,
        )
        yield pystray.MenuItem(
            "Sequential (In Order)",
            make_mode_action("sequential"),
            checked=make_mode_check("sequential"),
            radio=True,
        )

    def get_wallpaper_items():
        if not controller.wallpapers:
            yield pystray.MenuItem("No wallpapers found", lambda i, item: None, enabled=False)
            return

        for wp in controller.wallpapers[:40]:
            wp_label = wp.title
            if len(wp_label) > 30:
                wp_label = wp_label[:27] + "..."
            yield pystray.MenuItem(
                wp_label,
                make_select_action(wp),
                checked=make_select_check(wp),
                radio=True,
            )

    def get_root_menu():
        current_name = (
            controller.current_wallpaper.title if controller.current_wallpaper else "None"
        )
        curr_label = f"Current: {current_name}"
        if len(curr_label) > 36:
            curr_label = curr_label[:33] + "..."

        pause_label = "Resume Shuffle" if controller.is_paused else "Pause Shuffle"
        wallpapers_menu_title = f"Wallpapers ({len(controller.wallpapers)})"

        yield pystray.MenuItem(f"{APP_NAME} v{APP_VERSION}", lambda i, item: None, enabled=False)
        yield pystray.MenuItem(curr_label, on_open_folder)
        yield pystray.Menu.SEPARATOR
        yield pystray.MenuItem("Next Wallpaper", on_next, default=True)
        yield pystray.MenuItem("Previous Wallpaper", on_prev)
        yield pystray.MenuItem(
            pause_label,
            on_toggle_pause,
            checked=lambda item: controller.is_paused,
        )
        yield pystray.Menu.SEPARATOR
        yield pystray.MenuItem("Interval", pystray.Menu(get_interval_items))
        yield pystray.MenuItem("Mode", pystray.Menu(get_mode_items))
        yield pystray.MenuItem(wallpapers_menu_title, pystray.Menu(get_wallpaper_items))
        yield pystray.Menu.SEPARATOR
        yield pystray.MenuItem("Open Wallpapers Folder", on_open_folder)
        yield pystray.MenuItem(
            "Start with Windows",
            on_autostart_toggle,
            checked=lambda item: controller.start_with_windows,
        )
        yield pystray.MenuItem("Reload Wallpapers", on_reload)
        yield pystray.Menu.SEPARATOR
        yield pystray.MenuItem("Exit", on_exit)

    icon = pystray.Icon(
        name="LivelyShuffler",
        icon=get_tray_image(),
        title=f"{APP_NAME} - Ready",
        menu=pystray.Menu(get_root_menu),
    )
    controller.tray_icon = icon
    return icon


# ==============================================================================
# Single Instance Check & Main Entrypoint
# ==============================================================================
def acquire_single_instance_mutex():
    """Ensure only one instance of the tray app runs at a time."""
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    last_error = kernel32.GetLastError()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(mutex)
        return None
    return mutex


def handle_cli_args(args: list[str]) -> bool:
    """Handle one-off command-line actions like --next or --status without launching tray."""
    if not args:
        return False

    arg = args[0].lower()
    if arg in ("--help", "-h", "/?"):
        print(f"{APP_NAME} v{APP_VERSION}")
        print("Usage:")
        print("  LivelyWallpaperShuffler.exe          Launch background system tray shuffler")
        print("  LivelyWallpaperShuffler.exe --next   Immediately switch to next wallpaper and exit")
        print("  LivelyWallpaperShuffler.exe --prev   Switch to previous wallpaper and exit")
        print("  LivelyWallpaperShuffler.exe --status Show detected environment & active wallpaper")
        return True

    if arg in ("--status", "-s"):
        exe = DiscoveryEngine.find_lively_executable()
        folder = DiscoveryEngine.find_wallpapers_directory()
        active_path, active_title = DiscoveryEngine.get_currently_active_wallpaper()
        print(f"{APP_NAME} v{APP_VERSION}")
        print(f"Lively Executable : {exe or 'Not found'}")
        print(f"Wallpapers Folder : {folder or 'Not found'}")
        print(f"Active Wallpaper  : {active_title or 'None'} ({active_path})")
        return True

    if arg in ("--next", "-n"):
        ctrl = ShufflerController()
        if ctrl.wallpapers:
            ctrl.next_wallpaper()
            print(f"Switched to: {ctrl.current_wallpaper.title if ctrl.current_wallpaper else 'Unknown'}")
        else:
            print("No wallpapers found to switch.")
        return True

    if arg in ("--prev", "-p"):
        ctrl = ShufflerController()
        if ctrl.wallpapers:
            ctrl.previous_wallpaper()
            print(f"Switched to: {ctrl.current_wallpaper.title if ctrl.current_wallpaper else 'Unknown'}")
        else:
            print("No wallpapers found to switch.")
        return True

    return False


def main():
    if handle_cli_args(sys.argv[1:]):
        sys.exit(0)

    mutex = acquire_single_instance_mutex()
    if not mutex:
        logger.info("Another instance is already running. Exiting.")
        # Show Windows MessageBox to inform user
        ctypes.windll.user32.MessageBoxW(
            0,
            "Lively Wallpaper Shuffler is already running in the system tray.\nLook for the icon near the Windows clock.",
            APP_NAME,
            0x40 | 0x00000000,  # MB_ICONINFORMATION | MB_OK
        )
        sys.exit(0)

    try:
        controller = ShufflerController()
        controller.start()

        # Build & launch system tray icon
        tray_icon = build_system_tray(controller)
        controller.update_tray_tooltip()

        # Display initial startup balloon notification
        if controller.wallpapers:
            tray_icon.notify(
                f"Lively Shuffler is active! Found {len(controller.wallpapers)} wallpapers.\nInterval: {ShufflerController.format_interval(controller.interval_seconds)} ({controller.mode.capitalize()})",
                title="Lively Wallpaper Shuffler",
            )
        else:
            tray_icon.notify(
                "Running in system tray, but no wallpapers found in Lively library.",
                title="Lively Wallpaper Shuffler",
            )

        # Run tray loop (blocking call on main thread)
        tray_icon.run()

    except Exception as e:
        logger.exception("Fatal error in main: %s", e)
    finally:
        if mutex:
            ctypes.windll.kernel32.ReleaseMutex(mutex)
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()