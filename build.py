"""
Build script for Lively Wallpaper Shuffler
Compiles the application into a standalone, single-file Windows executable (.exe).
"""

import os
import sys
import subprocess
import shutil

APP_NAME = "LivelyWallpaperShuffler"
SCRIPT_FILE = "lively_shuffler.py"
ICON_FILE = "app_icon.ico"
PNG_ICON = "app_icon.png"

def build():
    print(f"[*] Starting build process for {APP_NAME}...")

    # Ensure icon exists
    if not os.path.exists(ICON_FILE):
        print(f"[!] Warning: {ICON_FILE} not found.")

    # Terminate any running instances so the output binary is not locked
    subprocess.run(["taskkill", "/F", "/IM", f"{APP_NAME}.exe"], capture_output=True)

    # Clean previous build artifacts
    for folder in ("build", "dist"):
        if os.path.isdir(folder):
            print(f"[*] Removing existing {folder}/ directory...")
            shutil.rmtree(folder, ignore_errors=True)

    # PyInstaller arguments
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--name={APP_NAME}",
        f"--icon={ICON_FILE}",
        f"--add-data={ICON_FILE};.",
        f"--add-data={PNG_ICON};.",
        "--hidden-import=pystray._win32",
        "--hidden-import=PIL._tkinter_finder",
        "--clean",
        SCRIPT_FILE,
    ]

    print(f"[*] Running PyInstaller command:\n{' '.join(cmd)}\n")
    res = subprocess.run(cmd)

    if res.returncode != 0:
        print(f"\n[X] Build failed with exit code {res.returncode}")
        sys.exit(res.returncode)

    exe_path = os.path.join("dist", f"{APP_NAME}.exe")
    if os.path.isfile(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n[+] Build successful!")
        print(f"[+] Output executable: {os.path.abspath(exe_path)} ({size_mb:.2f} MB)")
    else:
        print("\n[!] Warning: dist output executable was not found.")

if __name__ == "__main__":
    build()
