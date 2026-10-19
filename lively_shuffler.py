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
import glob
import queue
import datetime
from pathlib import Path
from PIL import Image, ImageDraw
import pystray

# Enable High-DPI awareness on Windows (eliminates font/UI blurriness)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

APP_NAME = "Lively Wallpaper Shuffler"
APP_VERSION = "1.0.4"
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
    def get_lively_data_dirs() -> list[str]:
        """
        Locate all candidate AppData / data storage directories for Lively Wallpaper.
        Supports standard Win32 desktop, Microsoft Store (UWP/MSIX), and portable installations.
        """
        candidates = []
        seen = set()

        def add_dir(d):
            if d and os.path.isdir(d):
                norm = os.path.normcase(os.path.abspath(d))
                if norm not in seen:
                    seen.add(norm)
                    candidates.append(d)

        # 1. Standard Win32 Desktop installer path
        add_dir(os.path.join(LOCAL_APPDATA, "Lively Wallpaper"))

        # 2. Microsoft Store (Centennial/MSIX container redirection)
        # Typical: %LOCALAPPDATA%\Packages\12030rocksdanister.LivelyWallpaper_<id>\LocalCache\Local\Lively Wallpaper
        store_cache_pattern = os.path.join(
            LOCAL_APPDATA, "Packages", "*LivelyWallpaper*", "LocalCache", "Local", "Lively Wallpaper"
        )
        for d in glob.glob(store_cache_pattern):
            add_dir(d)

        store_state_pattern = os.path.join(
            LOCAL_APPDATA, "Packages", "*LivelyWallpaper*", "LocalState", "Lively Wallpaper"
        )
        for d in glob.glob(store_state_pattern):
            add_dir(d)

        store_roaming_pattern = os.path.join(
            LOCAL_APPDATA, "Packages", "*LivelyWallpaper*", "LocalCache", "Roaming", "Lively Wallpaper"
        )
        for d in glob.glob(store_roaming_pattern):
            add_dir(d)

        return candidates

    @staticmethod
    def find_lively_executable(custom_path: str | None = None) -> str | None:
        """
        Dynamically detect Lively executable through multiple robust tiers:
        1. User-configured custom path (config.json)
        2. Win32 running process snapshot (detects Lively running on ANY drive or custom folder)
        3. Microsoft Store App Execution Alias & WindowsApps package directory
        4. Windows Registry Uninstall Keys (custom installation drives/folders)
        5. Windows Registry App Paths
        6. Standard program files & multi-drive fallback directories
        7. Adjacent portable directory
        """
        # --- Tier 1: Configured Custom Override ---
        if custom_path and os.path.isfile(custom_path):
            logger.info("Using configured custom Lively executable: %s", custom_path)
            return custom_path

        # --- Tier 2: Check active running process (Works for any drive/folder) ---
        proc_path = find_lively_process_path()
        if proc_path and os.path.isfile(proc_path):
            logger.info("Discovered Lively executable via active process: %s", proc_path)
            return proc_path

        # --- Tier 3: Microsoft Store Edition (App Execution Alias & Package Paths) ---
        store_alias = os.path.join(LOCAL_APPDATA, "Microsoft", "WindowsApps", "Lively.exe")
        if os.path.isfile(store_alias):
            logger.info("Discovered Lively executable via MS Store App Execution Alias: %s", store_alias)
            return store_alias

        store_alias_cu = os.path.join(LOCAL_APPDATA, "Microsoft", "WindowsApps", "livelycu.exe")
        if os.path.isfile(store_alias_cu):
            logger.info("Discovered Lively executable via MS Store livelycu alias: %s", store_alias_cu)
            return store_alias_cu

        # Wildcard match inside WindowsApps subdirectories
        store_wildcards = [
            os.path.join(LOCAL_APPDATA, "Microsoft", "WindowsApps", "*LivelyWallpaper*", "Lively.exe"),
            os.path.join(LOCAL_APPDATA, "Microsoft", "WindowsApps", "*LivelyWallpaper*", "livelycu.exe"),
        ]
        for pattern in store_wildcards:
            for m in glob.glob(pattern):
                if os.path.isfile(m):
                    logger.info("Discovered Lively executable via MS Store pattern: %s", m)
                    return m

        # Check Program Files\WindowsApps (MSIX install folder)
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        try:
            wa_matches = glob.glob(os.path.join(prog_files, "WindowsApps", "*LivelyWallpaper*", "Lively.exe"))
            for m in wa_matches:
                if os.path.isfile(m):
                    logger.info("Discovered Lively executable in WindowsApps: %s", m)
                    return m
        except (OSError, PermissionError):
            pass

        # --- Tier 4: Windows Registry Uninstall Keys (Custom installation drives) ---
        reg_uninstall_roots = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, subkey_path in reg_uninstall_roots:
            try:
                with winreg.OpenKey(hive, subkey_path) as root_key:
                    num_subkeys = winreg.QueryInfoKey(root_key)[0]
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(root_key, i)
                            with winreg.OpenKey(root_key, subkey_name) as sk:
                                display_name = ""
                                try:
                                    display_name, _ = winreg.QueryValueEx(sk, "DisplayName")
                                except OSError:
                                    pass

                                is_lively = "lively" in subkey_name.lower() or "lively" in str(display_name).lower()
                                if is_lively:
                                    # Check InstallLocation
                                    try:
                                        loc, _ = winreg.QueryValueEx(sk, "InstallLocation")
                                        if loc and os.path.isdir(loc):
                                            for cand in ("Lively.exe", "livelycu.exe", os.path.join("app", "Lively.exe")):
                                                cand_path = os.path.join(loc, cand)
                                                if os.path.isfile(cand_path):
                                                    logger.info("Discovered Lively executable via Registry Uninstall (InstallLocation): %s", cand_path)
                                                    return cand_path
                                    except OSError:
                                        pass

                                    # Check DisplayIcon
                                    try:
                                        icon_val, _ = winreg.QueryValueEx(sk, "DisplayIcon")
                                        if icon_val:
                                            clean_icon = icon_val.split(",")[0].strip('"').strip()
                                            if clean_icon.lower().endswith(".exe") and os.path.isfile(clean_icon):
                                                logger.info("Discovered Lively executable via Registry Uninstall (DisplayIcon): %s", clean_icon)
                                                return clean_icon
                                    except OSError:
                                        pass
                        except OSError:
                            pass
            except OSError:
                pass

        # --- Tier 5: Windows Registry App Paths ---
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for app_name in ("Lively.exe", "livelycu.exe"):
                try:
                    with winreg.OpenKey(
                        root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{app_name}"
                    ) as key:
                        val, _ = winreg.QueryValueEx(key, "")
                        if val and os.path.isfile(val):
                            logger.info("Discovered Lively executable via Registry App Paths: %s", val)
                            return val
                except OSError:
                    pass

        # --- Tier 6: Standard & Multi-Drive Directory Fallbacks ---
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        standard_candidates = [
            os.path.join(LOCAL_APPDATA, "Programs", "Lively Wallpaper", "Lively.exe"),
            os.path.join(LOCAL_APPDATA, "Programs", "Lively Wallpaper", "livelycu.exe"),
            os.path.join(prog_files, "Lively Wallpaper", "Lively.exe"),
            os.path.join(prog_files, "Lively Wallpaper", "livelycu.exe"),
            os.path.join(prog_files_x86, "Lively Wallpaper", "Lively.exe"),
            os.path.join(prog_files_x86, "Lively Wallpaper", "livelycu.exe"),
            # Common alternative drives (D:, E:)
            r"D:\Programs\Lively Wallpaper\Lively.exe",
            r"D:\Program Files\Lively Wallpaper\Lively.exe",
            r"D:\Lively Wallpaper\Lively.exe",
            r"E:\Lively Wallpaper\Lively.exe",
        ]
        for path in standard_candidates:
            if os.path.isfile(path):
                logger.info("Discovered Lively executable at standard path: %s", path)
                return path

        # --- Tier 7: Relative / Adjacent Portable Locations ---
        try:
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            script_dir = os.path.dirname(os.path.abspath(__file__))
            for base in (exe_dir, script_dir):
                for rel in ("Lively.exe", "livelycu.exe", os.path.join("..", "Lively.exe"), os.path.join("..", "Lively Wallpaper", "Lively.exe")):
                    cand = os.path.normpath(os.path.join(base, rel))
                    if os.path.isfile(cand):
                        logger.info("Discovered Lively executable in adjacent folder: %s", cand)
                        return cand
        except Exception:
            pass

        logger.warning("Could not auto-discover Lively executable across any known paths.")
        return None

    @staticmethod
    def find_wallpapers_directories() -> list[str]:
        """
        Resolve all active wallpaper library directories across standard Win32 desktop,
        Microsoft Store edition, custom configured directories, and Settings.json overrides.
        """
        dirs = []
        seen = set()

        def add_dir(d):
            if d and os.path.isdir(d):
                norm = os.path.normcase(os.path.abspath(d))
                if norm not in seen:
                    seen.add(norm)
                    dirs.append(d)

        # 1. Scan candidate data directories (Standard AppData and MS Store Packages)
        data_roots = DiscoveryEngine.get_lively_data_dirs()

        for data_root in data_roots:
            # Check Settings.json for custom WallpaperDir configured in Lively
            settings_file = os.path.join(data_root, "Settings.json")
            if os.path.isfile(settings_file):
                try:
                    with open(settings_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        custom_dir = data.get("WallpaperDir")
                        if custom_dir:
                            add_dir(custom_dir)
                            add_dir(os.path.join(custom_dir, "wallpapers"))
                            add_dir(os.path.join(custom_dir, "SaveData", "wptmp"))
                except Exception as e:
                    logger.warning("Failed parsing Settings.json in %s: %s", data_root, e)

            # Standard subdirectories in this data root
            lib_dir = os.path.join(data_root, "Library")
            add_dir(lib_dir)
            add_dir(os.path.join(lib_dir, "wallpapers"))
            add_dir(os.path.join(lib_dir, "SaveData", "wptmp"))
            add_dir(os.path.join(data_root, "wallpapers"))
            add_dir(os.path.join(data_root, "SaveData", "wptmp"))

        # 2. User-defined custom directories from config.json
        if os.path.isfile(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    for extra in cfg.get("custom_directories", []):
                        add_dir(extra)
            except Exception:
                pass

        return dirs

    @staticmethod
    def find_wallpapers_directory() -> str | None:
        """Return the primary wallpapers directory for UI Explorer navigation."""
        dirs = DiscoveryEngine.find_wallpapers_directories()
        for d in dirs:
            if d.lower().endswith("wallpapers"):
                return d
        return dirs[0] if dirs else None

    @staticmethod
    def get_currently_active_wallpaper() -> tuple[str | None, str | None]:
        """
        Read WallpaperLayout.json across candidate data directories (Standard or Store)
        to find the currently active wallpaper path and title.
        Prioritizes the most recently updated layout file.
        """
        data_roots = DiscoveryEngine.get_lively_data_dirs()
        layout_files = []
        for root in data_roots:
            lf = os.path.join(root, "WallpaperLayout.json")
            if os.path.isfile(lf):
                try:
                    mtime = os.path.getmtime(lf)
                    layout_files.append((mtime, lf))
                except OSError:
                    layout_files.append((0, lf))

        if not layout_files:
            return None, None

        # Sort by modification time descending (most recent first)
        layout_files.sort(key=lambda x: x[0], reverse=True)

        for _, layout_file in layout_files:
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
                logger.debug("Error checking active wallpaper in %s: %s", layout_file, e)

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
                    # Quote path and start minimized in system tray
                    val = f'"{exe_path}" --minimized'
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


def parse_time_to_minutes(time_str: str) -> int | None:
    """
    Parse a user-entered time string into minutes from midnight (0..1439).
    Supports:
      - 12-hour AM/PM: '11:00 PM', '7:30 AM', '12:45 PM', '11PM', '7am'
      - 24-hour: '23:00', '07:00', '12:45', '0:30'
      - Bare hour: '11', '23', '7'
    """
    if not time_str:
        return None
    s = str(time_str).strip().upper()

    is_pm = "PM" in s
    is_am = "AM" in s
    s = s.replace("PM", "").replace("AM", "").strip()

    parts = s.split(":")
    try:
        if len(parts) == 2:
            hour = int(parts[0].strip())
            minute = int(parts[1].strip())
        elif len(parts) == 1:
            hour = int(parts[0].strip())
            minute = 0
        else:
            return None

        if is_pm:
            if hour < 12:
                hour += 12
        elif is_am:
            if hour == 12:
                hour = 0

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        return hour * 60 + minute
    except Exception:
        return None


def format_minutes_to_12h(minutes: int) -> str:
    """Format minutes from midnight into '11:00 PM', '07:00 AM', etc."""
    h = (minutes // 60) % 24
    m = minutes % 60
    am_pm = "AM" if h < 12 else "PM"
    h12 = 12 if h % 12 == 0 else h % 12
    return f"{h12:02d}:{m:02d} {am_pm}"


def format_time_display(time_str: str) -> str:
    """Normalize any time string into clean 'HH:MM AM/PM'."""
    mins = parse_time_to_minutes(time_str)
    if mins is not None:
        return format_minutes_to_12h(mins)
    return str(time_str)


def is_time_between(start_str: str, end_str: str, check_time: datetime.time = None) -> bool:
    """
    Check if check_time (or current local time) falls within the window [start_str, end_str).
    Handles ranges that cross midnight (e.g. 11:00 PM to 07:00 AM).
    """
    try:
        start_min = parse_time_to_minutes(start_str)
        end_min = parse_time_to_minutes(end_str)
        if start_min is None or end_min is None:
            return False

        if check_time is None:
            now = datetime.datetime.now().time()
        else:
            now = check_time
        curr_min = now.hour * 60 + now.minute

        if start_min == end_min:
            return False
        elif start_min < end_min:
            return start_min <= curr_min < end_min
        else:
            # Range crosses midnight (e.g. 11:00 PM to 07:00 AM)
            return curr_min >= start_min or curr_min < end_min
    except Exception as e:
        logger.error("Error evaluating night mode window (%s - %s): %s", start_str, end_str, e)
        return False


class ShufflerController:
    def __init__(self):
        self.custom_lively_exe: str | None = None
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

        # Night mode (sleep hours auto-pause, AM/PM format)
        self.night_mode_enabled: bool = False
        self.night_mode_start: str = "11:00 PM"
        self.night_mode_end: str = "07:00 AM"

        # Concurrency & loop control
        self.lock = threading.Lock()
        self.wake_event = threading.Event()
        self.is_running = True
        self.worker_thread: threading.Thread | None = None
        self.tray_icon: pystray.Icon | None = None
        self.gui = None
        self.custom_directories: list[str] = []

        # Ultra-low-latency asynchronous switch queue & worker
        self._switch_queue = queue.Queue()
        self._switch_worker = threading.Thread(target=self._process_switch_queue, daemon=True)
        self._switch_worker.start()

        self.load_config()
        self.discover_environment()
        self.scan_wallpapers()

    @staticmethod
    def get_interval_presets():
        return INTERVAL_PRESETS

    def add_custom_directory(self, folder: str):
        """Add a custom wallpaper folder and save to config."""
        if folder and os.path.isdir(folder):
            norm = os.path.normcase(os.path.abspath(folder))
            if norm not in [os.path.normcase(os.path.abspath(d)) for d in self.custom_directories]:
                self.custom_directories.append(folder)
                self.save_config()
                logger.info("Added custom wallpaper directory: %s", folder)

    def set_custom_lively_exe(self, exe_path: str):
        """Set a user-specified Lively.exe path, persist it, and re-scan environment."""
        if exe_path and os.path.isfile(exe_path):
            self.custom_lively_exe = os.path.abspath(exe_path)
            self.lively_exe = self.custom_lively_exe
            self.save_config()
            logger.info("Saved custom Lively executable path: %s", self.custom_lively_exe)
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
                    self.night_mode_enabled = cfg.get("night_mode_enabled", False)
                    self.night_mode_start = format_time_display(cfg.get("night_mode_start", "11:00 PM"))
                    self.night_mode_end = format_time_display(cfg.get("night_mode_end", "07:00 AM"))
                    self.custom_lively_exe = cfg.get("custom_lively_exe")
                    self.custom_directories = cfg.get("custom_directories", [])
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
                "night_mode_enabled": self.night_mode_enabled,
                "night_mode_start": self.night_mode_start,
                "night_mode_end": self.night_mode_end,
                "start_with_windows": self.start_with_windows,
                "custom_lively_exe": self.custom_lively_exe,
                "custom_directories": self.custom_directories,
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            logger.error("Failed saving config: %s", e)

    def discover_environment(self):
        """Auto-discover Lively and Wallpapers path."""
        self.lively_exe = DiscoveryEngine.find_lively_executable(custom_path=self.custom_lively_exe)
        self.wallpapers_dir = DiscoveryEngine.find_wallpapers_directory()

    def scan_wallpapers(self):
        """Scan wallpapers directory for valid Lively wallpapers (folders with LivelyInfo.json or direct media files)."""
        with self.lock:
            self.wallpapers.clear()
            roots = DiscoveryEngine.find_wallpapers_directories()
            if not roots:
                logger.warning("Scan skipped: no valid wallpapers directories found.")
                return

            seen_paths = set()
            try:
                for root in roots:
                    if not os.path.isdir(root):
                        continue
                    # Recursively traverse directory tree looking for Lively wallpapers
                    for dirpath, dirnames, filenames in os.walk(root):
                        norm_path = os.path.normcase(os.path.abspath(dirpath))
                        if norm_path in seen_paths:
                            continue

                        # Case 1: Folder containing LivelyInfo.json project metadata
                        if "LivelyInfo.json" in filenames:
                            seen_paths.add(norm_path)
                            dirnames.clear()  # Do not traverse into internal asset/texture subdirectories
                            info_file = os.path.join(dirpath, "LivelyInfo.json")
                            title = os.path.basename(dirpath)
                            author = ""
                            wp_type = ""
                            try:
                                with open(info_file, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    title = data.get("Title") or data.get("FileName") or os.path.basename(dirpath)
                                    author = data.get("Author") or ""
                                    wp_type = str(data.get("Type", ""))
                            except Exception as e:
                                logger.debug("Error reading %s: %s", info_file, e)

                            item = WallpaperItem(dirpath, title, author, wp_type)
                            self.wallpapers.append(item)

                        # Case 2: Standalone media files (.mp4, .webm, .gif, .mkv) in user-added external custom folders
                        elif not norm_path.startswith(
                            os.path.normcase(os.path.abspath(os.path.join(LOCAL_APPDATA, "Lively Wallpaper")))
                        ):
                            for f in filenames:
                                if f.lower().endswith((".mp4", ".webm", ".mkv", ".gif")):
                                    file_full = os.path.join(dirpath, f)
                                    file_norm = os.path.normcase(os.path.abspath(file_full))
                                    if file_norm not in seen_paths:
                                        seen_paths.add(file_norm)
                                        name_no_ext = os.path.splitext(f)[0]
                                        item = WallpaperItem(file_full, name_no_ext, "", "media")
                                        self.wallpapers.append(item)

                # Sort naturally by title
                self.wallpapers.sort(key=lambda x: x.title.lower())
                logger.info(
                    "Scanned %d wallpapers across %d library roots.",
                    len(self.wallpapers),
                    len(roots),
                )

                # Detect currently active wallpaper on startup
                active_path, active_title = DiscoveryEngine.get_currently_active_wallpaper()
                if active_path:
                    norm_active = os.path.normcase(os.path.abspath(active_path))
                    for wp in self.wallpapers:
                        if os.path.normcase(os.path.abspath(wp.folder_path)) == norm_active:
                            self.current_wallpaper = wp
                            if not self.history:
                                self.history.append(wp)
                                self.history_index = 0
                            break
            except Exception as e:
                logger.error("Error during scan_wallpapers: %s", e)

    def _execute_lively_cmd(self, wallpaper: WallpaperItem) -> bool:
        """Low-level execution of Lively command with lightweight process spawning."""
        if not self.lively_exe or not os.path.isfile(self.lively_exe):
            self.lively_exe = DiscoveryEngine.find_lively_executable(custom_path=self.custom_lively_exe)
            if not self.lively_exe:
                logger.error("Cannot set wallpaper: Lively executable not found.")
                return False

        cmd = [self.lively_exe, "setwp", "--file", wallpaper.folder_path]
        logger.info("Switching wallpaper via Lively CLI: %s (%s)", wallpaper.title, wallpaper.folder_path)

        try:
            creation_flags = 0x08000000  # CREATE_NO_WINDOW
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = 0  # SW_HIDE

            proc = subprocess.Popen(
                cmd,
                creationflags=creation_flags,
                startupinfo=startup_info,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc.wait(timeout=10)
            logger.info("Successfully applied wallpaper: %s", wallpaper.title)
            return True
        except Exception as e:
            logger.error("Failed to execute Lively command: %s", e)
            return False

    def _process_switch_queue(self):
        """Worker thread processing wallpaper switches with latest-item coalescing."""
        while self.is_running:
            try:
                wp = self._switch_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # Rapid click coalescing: if user tapped next/cards multiple times, skip obsolete items
            while not self._switch_queue.empty():
                try:
                    wp = self._switch_queue.get_nowait()
                except queue.Empty:
                    break

            if wp and self.is_running:
                self._execute_lively_cmd(wp)

    def set_wallpaper(self, wallpaper: WallpaperItem, sync: bool = False) -> bool:
        """
        Switch wallpaper with instant optimistic state update (<1ms response).
        sync=True executes synchronously in caller thread (used by one-off CLI scripts).
        sync=False dispatches to background queue (used by GUI and tray).
        """
        self.current_wallpaper = wallpaper
        self.update_tray_tooltip()
        self.notify_gui()

        if sync:
            return self._execute_lively_cmd(wallpaper)
        else:
            self._switch_queue.put(wallpaper)
            return True

    def notify_gui(self):
        """Thread-safe, zero-delay UI update trigger."""
        if self.gui and hasattr(self.gui, "root"):
            try:
                if hasattr(self.gui, "on_active_wallpaper_changed"):
                    self.gui.root.after(0, self.gui.on_active_wallpaper_changed)
                else:
                    self.gui.root.after(0, self.gui.refresh_ui)
            except Exception:
                pass

    def next_wallpaper(self, explicit_user_trigger: bool = True, sync: bool = False):
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
                if len(self.history) > 50:
                    self.history.pop(0)
                self.history_index = len(self.history) - 1

        self.set_wallpaper(selected, sync=sync)

        # Reset timer countdown on explicit trigger
        if explicit_user_trigger:
            self.wake_event.set()

    def previous_wallpaper(self, sync: bool = False):
        """Go back to the previously active wallpaper in history."""
        with self.lock:
            if self.history and self.history_index > 0:
                self.history_index -= 1
                selected = self.history[self.history_index]
                self.set_wallpaper(selected, sync=sync)
                self.wake_event.set()
            else:
                logger.info("No earlier wallpaper in history.")

    def select_wallpaper(self, wallpaper: WallpaperItem, sync: bool = False):
        """Directly switch to a specific wallpaper."""
        with self.lock:
            self.history.append(wallpaper)
            self.history_index = len(self.history) - 1
        self.set_wallpaper(wallpaper, sync=sync)
        self.wake_event.set()

    def toggle_pause(self):
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        self.save_config()
        self.update_tray_tooltip()
        self.wake_event.set()
        self.notify_gui()
        logger.info("Shuffler pause state toggled to: %s", self.is_paused)

    def set_interval(self, seconds: int):
        """Update interval preset."""
        self.interval_seconds = seconds
        self.save_config()
        self.update_tray_tooltip()
        self.wake_event.set()
        self.notify_gui()
        logger.info("Interval changed to: %d seconds", seconds)

    def set_mode(self, mode: str):
        """Update shuffle mode."""
        if mode in ("shuffle", "sequential"):
            self.mode = mode
            self.save_config()
            self.wake_event.set()
            self.notify_gui()
            logger.info("Mode changed to: %s", mode)

    def toggle_start_with_windows(self):
        """Toggle autostart in Windows Registry."""
        self.start_with_windows = not self.start_with_windows
        AutostartManager.set_enabled(self.start_with_windows)
        self.save_config()
        self.notify_gui()

    def is_night_mode_active(self) -> bool:
        """Check if night mode is enabled and current local time is inside the configured window."""
        if not self.night_mode_enabled:
            return False
        return is_time_between(self.night_mode_start, self.night_mode_end)

    def set_night_mode(self, enabled: bool, start_time: str = None, end_time: str = None):
        """Configure and persist night mode settings with normalized AM/PM formatting."""
        self.night_mode_enabled = enabled
        if start_time:
            self.night_mode_start = format_time_display(start_time)
        if end_time:
            self.night_mode_end = format_time_display(end_time)
        self.save_config()
        self.update_tray_tooltip()
        self.wake_event.set()
        self.notify_gui()
        logger.info(
            "Night mode configured: enabled=%s, window=%s - %s",
            self.night_mode_enabled,
            self.night_mode_start,
            self.night_mode_end,
        )

    def update_tray_tooltip(self):
        """Update system tray tooltip and menu labels."""
        if not self.tray_icon:
            return
        if self.is_paused:
            status = "Paused"
        elif self.is_night_mode_active():
            s_disp = format_time_display(self.night_mode_start)
            e_disp = format_time_display(self.night_mode_end)
            status = f"🌙 Night Mode Active ({s_disp} - {e_disp})"
        else:
            status = f"Every {self.format_interval(self.interval_seconds)}"
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

            if self.is_night_mode_active():
                # Night mode is active: automatically suppress shuffling to avoid waking sleeping screen
                self.wake_event.wait(timeout=5.0)
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

            # Timer expired naturally: cycle wallpaper only if neither paused nor in night mode
            if not self.is_paused and not self.is_night_mode_active() and self.is_running:
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

    def on_open_dashboard(icon=None, item=None):
        if controller.gui and hasattr(controller.gui, "root"):
            try:
                controller.gui.root.after(0, controller.gui.show_window)
            except Exception:
                pass

    # Ensure double-click (WM_LBUTTONDBLCLK = 0x0203) and left click on tray icon opens GUI
    try:
        import pystray._win32
        _orig_on_notify = pystray._win32.Icon._on_notify

        def _enhanced_on_notify(self, wparam, lparam):
            # 0x0202 is WM_LBUTTONUP, 0x0203 is WM_LBUTTONDBLCLK
            if lparam in (0x0202, 0x0203):
                on_open_dashboard()
                self.update_menu()
            elif self._menu_handle and lparam == pystray._win32.win32.WM_RBUTTONUP:
                _orig_on_notify(self, wparam, lparam)

        pystray._win32.Icon._on_notify = _enhanced_on_notify
    except Exception as e:
        logger.debug("Could not patch pystray _on_notify: %s", e)

    def on_exit(icon, item):
        controller.stop()
        if icon:
            icon.stop()
        if controller.gui and hasattr(controller.gui, "root"):
            try:
                controller.gui.root.after(0, controller.gui.root.destroy)
            except Exception:
                pass

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

        yield pystray.MenuItem("Open Dashboard", on_open_dashboard, default=True)
        yield pystray.MenuItem(curr_label, on_open_dashboard)
        yield pystray.Menu.SEPARATOR
        yield pystray.MenuItem("Next Wallpaper", on_next)
        yield pystray.MenuItem("Previous Wallpaper", on_prev)
        yield pystray.MenuItem(
            pause_label,
            on_toggle_pause,
            checked=lambda item: controller.is_paused,
        )
        yield pystray.Menu.SEPARATOR

        def on_toggle_night_mode(icon, item):
            controller.set_night_mode(not controller.night_mode_enabled)

        s_disp = format_time_display(controller.night_mode_start)
        e_disp = format_time_display(controller.night_mode_end)
        night_label = f"Night Mode ({s_disp} - {e_disp})"
        if controller.is_night_mode_active():
            night_label += " [Active]"
        yield pystray.MenuItem(
            night_label,
            on_toggle_night_mode,
            checked=lambda item: controller.night_mode_enabled,
        )

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
        print("  LivelyWallpaperShuffler.exe             Launch GUI dashboard & system tray")
        print("  LivelyWallpaperShuffler.exe --minimized Launch directly to system tray")
        print("  LivelyWallpaperShuffler.exe --next      Immediately switch to next wallpaper and exit")
        print("  LivelyWallpaperShuffler.exe --prev      Switch to previous wallpaper and exit")
        print("  LivelyWallpaperShuffler.exe --status    Show detected environment & active wallpaper")
        print("  LivelyWallpaperShuffler.exe --set-lively <path> Save custom Lively.exe path and exit")
        return True

    if arg == "--set-lively":
        if len(args) < 2:
            print('Error: Missing executable path. Example: --set-lively "D:\\Lively\\Lively.exe"')
            return True
        target = args[1].strip('"')
        if not os.path.isfile(target):
            print(f"Error: Executable file not found at: {target}")
            return True
        ctrl = ShufflerController()
        ctrl.set_custom_lively_exe(target)
        print(f"Successfully configured and saved Lively executable: {target}")
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
            ctrl.next_wallpaper(sync=True)
            print(f"Switched to: {ctrl.current_wallpaper.title if ctrl.current_wallpaper else 'Unknown'}")
        else:
            print("No wallpapers found to switch.")
        return True

    if arg in ("--prev", "-p"):
        ctrl = ShufflerController()
        if ctrl.wallpapers:
            ctrl.previous_wallpaper(sync=True)
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

        # Build & launch system tray icon in detached thread
        tray_icon = build_system_tray(controller)
        controller.update_tray_tooltip()
        tray_icon.run_detached()

        # Initialize Tkinter GUI Dashboard
        import tkinter as tk
        from gui import ShufflerGUI
        root = tk.Tk()
        gui = ShufflerGUI(controller, root)
        controller.gui = gui

        # If started with --minimized flag (e.g. from Windows startup), hide to tray
        if "--minimized" in sys.argv:
            root.withdraw()
        else:
            gui.show_window()

        # Run Tk main loop (blocking call on main thread)
        root.mainloop()

    except Exception as e:
        logger.exception("Fatal error in main: %s", e)
    finally:
        if mutex:
            ctypes.windll.kernel32.ReleaseMutex(mutex)
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()