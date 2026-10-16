# Lively Wallpaper Shuffler

<p align="center">
  <img src="app_icon.png" alt="Lively Wallpaper Shuffler Logo" width="128" height="128">
</p>

<p align="center">
  <strong>A lightweight, zero-configuration Windows companion app and background shuffler for <a href="https://github.com/rocksdanister/lively">Lively Wallpaper</a> (v2.x+).</strong>
  <br>
  Features a modern GUI dashboard, visual wallpaper gallery with previews, multi-directory auto-discovery, and full system-tray controls.
</p>

<p align="center">
  <a href="https://github.com/y0sh1da-available/Lively-Shuffler/releases"><img src="https://img.shields.io/github/v/release/y0sh1da-available/Lively-Shuffler?color=success&include_prereleases&label=Release" alt="GitHub Release"></a>
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?logo=windows&logoColor=white" alt="Windows Support">
  <img src="https://img.shields.io/badge/Lively%20Wallpaper-v2.0%2B-blueviolet" alt="Lively Compatibility">
  <img src="https://img.shields.io/badge/Interface-GUI%20%2B%20System%20Tray-informational" alt="Interface">
  <img src="https://img.shields.io/badge/Configuration-Zero%20Config-brightgreen" alt="Zero Config">
  <img src="https://img.shields.io/badge/Made%20with-AI%20Assistance-8A2BE2.svg" alt="Made with AI Assistance">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
</p>

---

## 📖 Table of Contents
- [About The Project](#-about-the-project)
- [System Requirements](#-system-requirements)
- [Why This Utility?](#-why-this-utility)
- [Setup Tutorial](#-setup-tutorial)
- [How to Use](#-how-to-use)
  - [1. Modern GUI Dashboard](#1-modern-gui-dashboard)
  - [2. System Tray Controls](#2-system-tray-controls)
  - [3. Hotkeys & CLI Commands](#3-hotkeys--cli-commands)
- [How It Works (Architecture)](#-how-it-works-architecture)
- [Developer Guide (Building from Source)](#-developer-guide-building-from-source)
- [Support & Sponsorship](#-support--sponsorship)
- [License & Ownership](#-license--ownership)
- [Built with AI](#-built-with-ai)

---

## 🌟 About The Project

**Lively Wallpaper Shuffler** is a lightweight, zero-configuration desktop companion utility engineered specifically for [Lively Wallpaper](https://github.com/rocksdanister/lively) (v2.x+).

While Lively Wallpaper provides a great engine for interactive, animated, and video desktop backgrounds, it currently lacks an out-of-the-box automatic playlist shuffler. Existing community solutions relied on deprecated local network sockets and static path configurations that break on modern Windows installations.

This project delivers:
- **Zero Configuration:** Automatically locates Lively's running process, default library directories, and custom user-imported wallpapers.
- **Modern Visual GUI:** Browse all your live wallpapers in an interactive card gallery with high-resolution thumbnails, live search, and one-click activation.
- **Silent Background Shuffling:** Shuffles your desktop wallpaper at customizable intervals (`30s` to `4h`) completely invisibly without annoying console popup windows.
- **System Tray Controls:** Quick actions right by your Windows taskbar clock with single-instance mutex protection.
- **Portable Single-File Binary:** Self-contained executable with zero dependencies or runtime installers needed.

---

## 💻 System Requirements

| Component | Requirement |
| :--- | :--- |
| **Operating System** | Windows 10 (Build 1809+) or Windows 11 (64-bit) |
| **Lively Wallpaper** | Version **2.0 or newer** (Desktop Installer or Microsoft Store Edition) |
| **Runtimes** | **None** — Standalone single-file executable (`.exe`). Python is not required. |

---

## 💡 Why This Utility?

Legacy community shufflers (such as *lively-wallpaper-playlist*) rely on an obsolete IPC socket protocol (`port 65432`) and hardcoded directory paths that fail on modern Lively Wallpaper v2.x+ installations.

**Lively Wallpaper Shuffler** interfaces directly with modern Lively:
- **Direct Process Execution:** Sends native command-line instructions:
  ```cmd
  "<Lively_Directory>\Lively.exe" setwp --file "<Wallpaper_Folder_Path>"
  ```
- **Zero Configuration:** Dynamically finds your running Lively binary and scans all library paths without asking you to type paths.
- **Full Custom Wallpaper Support:** Automatically scans both default pre-installed wallpapers (`wallpapers\`) and your imported custom wallpapers (`SaveData\wptmp\`).
- **Silent Background Operation:** Commands run invisibly (`CREATE_NO_WINDOW`) so no command prompt windows flash on screen.
- **Standalone Portable Executable:** Download, run, and enjoy. No installers or administrative privileges required.

---

## 🚀 Setup Tutorial

### Step 1: Download
Download **`LivelyWallpaperShuffler.exe`** from the **[Latest Releases](https://github.com/y0sh1da-available/Lively-Shuffler/releases)** page.

### Step 2: Run the Application
1. Make sure **Lively Wallpaper** is installed and running.
2. Double-click **`LivelyWallpaperShuffler.exe`**.
3. The modern **Dashboard GUI** will appear, and a companion icon will appear in your **Windows System Tray** (near the clock).

### Step 3: Configure Autostart (Optional)
In the dashboard sidebar or by right-clicking the tray icon, check **"Start with Windows"**.  
*When enabled, the app launches quietly in the system tray every time you log in to Windows.*

---

## 🎮 How to Use

### 1. Modern GUI Dashboard
Double-click `LivelyWallpaperShuffler.exe` or click **"Open Dashboard"** from the system tray menu to open the dashboard window.

- **Now Playing Card:** Displays the current active wallpaper with high-resolution thumbnail preview, title, author, and an *Open Folder* shortcut.
- **Quick Controls:**
  - **⏭ Next Wallpaper:** Immediately cycle to the next wallpaper.
  - **⏮ Previous:** Revisit previously shuffled wallpapers in your history.
  - **⏸ Pause / Resume:** Pause the timer loop on your favorite wallpaper or resume shuffling.
- **Interval Presets:** Quick dropdown selector for `30 seconds`, `1 minute`, `5 minutes`, `10 minutes`, `15 minutes`, `30 minutes`, `1 hour`, `2 hours`, or `4 hours`.
- **Shuffle Mode:** Choose between **Shuffle (Random)** or **Sequential (In Order)**.
- **Wallpaper Gallery:**
  - Visual grid of all wallpapers (default + imported + custom).
  - Live search bar to quickly filter wallpapers by name or author.
  - Click any card to **instantly set it as your active wallpaper**.
- **+ Add Folder Button:** Browse and link external folders containing wallpapers or video clips (`.mp4`, `.webm`, `.mkv`, `.gif`).
- **Minimize to Tray:** Clicking the window's close (`X`) button hides the dashboard to the system tray so it runs quietly in the background.

---

### 2. System Tray Controls
Right-click the tray icon near the Windows clock to access quick actions:

| Menu Item | Action |
| :--- | :--- |
| **Open Dashboard** | Opens the visual GUI Dashboard (Default double-click action). |
| **Current: [Title]** | Shows the active wallpaper name; click to open the GUI. |
| **Next Wallpaper** | Immediately switch to the next wallpaper. |
| **Previous Wallpaper** | Step backward in shuffle history. |
| **Pause / Resume** | Freeze on the current wallpaper or resume the timer loop. |
| **Interval** | Select cycle duration presets. |
| **Mode** | Toggle between Shuffle (Random) and Sequential. |
| **Wallpapers (N)** | Quick-pick dropdown listing all wallpapers in your library. |
| **Open Wallpapers Folder** | Opens your active Lively library folder in File Explorer. |
| **Start with Windows** | Toggle automatic startup via Windows Registry (`HKCU\...\Run`). |
| **Reload Wallpapers** | Re-scans library folders when you add or delete wallpapers. |
| **Exit** | Shuts down the background timer and closes the application completely. |

---

### 3. Hotkeys & CLI Commands
You can map keyboard shortcuts (e.g. using AutoHotkey, Windows shortcuts, or Stream Deck) directly to these one-shot command-line actions:

```cmd
:: Switch to next wallpaper immediately and exit
LivelyWallpaperShuffler.exe --next

:: Switch to previous wallpaper immediately and exit
LivelyWallpaperShuffler.exe --prev

:: Print detected Lively path, library folder, and active wallpaper
LivelyWallpaperShuffler.exe --status

:: Configure a custom Lively.exe location and exit
LivelyWallpaperShuffler.exe --set-lively "D:\Lively Wallpaper\Lively.exe"

:: Start directly in system tray without opening the GUI window
LivelyWallpaperShuffler.exe --minimized

:: Display CLI help
LivelyWallpaperShuffler.exe --help
```

---

## 🔍 How It Works (Architecture)

### Multi-Tier Auto-Discovery Engine
Lively Wallpaper Shuffler automatically finds your installation, regardless of how or where you installed it:

1. **Lively Executable Detection:**
   - **User Custom Override:** Checks `config.json` for any user-configured executable path.
   - **Active Process Snapshot:** Uses Win32 Toolhelp API (`CreateToolhelp32Snapshot` & `QueryFullProcessImageNameW`) to detect `Lively.exe` or companion processes running on **any drive or folder** (including portable or custom drives).
   - **Microsoft Store Edition:** Scans Store execution aliases (`%LOCALAPPDATA%\Microsoft\WindowsApps\Lively.exe`) and Store package directories (`%LOCALAPPDATA%\Packages\12030rocksdanister.LivelyWallpaper_*\`).
   - **Windows Registry Uninstall Keys:** Inspects `HKCU` and `HKLM` `Uninstall` registry keys to find custom installation paths (`InstallLocation` and `DisplayIcon`).
   - **Windows Registry App Paths:** Checks `HKCU` and `HKLM` `App Paths\Lively.exe`.
   - **Standard & Multi-Drive Fallback:** Checks standard directories (`%LOCALAPPDATA%\Programs\Lively Wallpaper\`, `%ProgramFiles%\Lively Wallpaper\`, `D:\`, `E:\`, and adjacent portable folders).
   - **Manual GUI Locator:** If ever needed, click the **Locate...** button in the dashboard or run `--set-lively <path>` to pick your executable.

2. **Wallpaper Library Resolution:**
   - Detects data directories from both standard installations and Microsoft Store package AppData (`%LOCALAPPDATA%\Packages\12030rocksdanister.LivelyWallpaper_*\LocalCache\Local\Lively Wallpaper`).
   - Parses `Settings.json` in all detected data directories to discover custom `WallpaperDir` folders.
   - Scans built-in default library (`.../Library/wallpapers`).
   - Scans user-imported live wallpapers (`.../Library/SaveData/wptmp`).
   - Validates subfolders containing `LivelyInfo.json` to extract titles, authors, and preview thumbnails.
   - Fully supports user-added custom directories via the GUI **+ Add Folder** button or `config.json`.

3. **Synchronization & Single-Instance:**
   - Reads `WallpaperLayout.json` across standard and Store data directories to detect active wallpapers across multi-monitor setups.
   - Enforces a named Win32 mutex (`Global\LivelyWallpaperShuffler_SingleInstance_Mutex`) to prevent duplicate instances.

---

## 🛠️ Developer Guide (Building from Source)

### Prerequisites
- Windows 10 or 11
- Python 3.10+
- Git

### Setup & Run
```bash
git clone https://github.com/y0sh1da-available/Lively-Shuffler.git
cd Lively-Shuffler
pip install -r requirements.txt
python lively_shuffler.py
```

### Compile Standalone Executable
```bash
python build.py
# Or double-click build.bat
```
The compiled single-file binary will be generated at `dist/LivelyWallpaperShuffler.exe`.

---

## 💖 Support & Sponsorship

If you find **Lively Wallpaper Shuffler** helpful and would like to support its ongoing development, donations are gratefully appreciated!

### 🌍 International (PayPal)
[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?logo=paypal&style=for-the-badge)](https://paypal.me/y0sh1da)

> **Link:** [paypal.me/y0sh1da](https://paypal.me/y0sh1da)

---

### <img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/1f1fb-1f1f3.svg" width="22" height="22" alt="Vietnam Flag" style="vertical-align: middle;"> Vietnam (BIDV Transfer & VietQR)

| Bank Details | Information |
| :--- | :--- |
| **Ngân hàng (Bank)** | Bank for Investment and Development of Vietnam (BIDV) |
| **Số tài khoản (Account No.)** | `4605007300` |
| **Chủ tài khoản (Account Name)** | `DANG HUU CUONG` |

<details>
<summary>📱 <strong>Scan VietQR Code (Click to Expand)</strong></summary>

<br>

<p align="center">
  <img src="https://img.vietqr.io/image/bidv-4605007300-compact2.png?amount=0&accountName=DANG%20HUU%20CUONG" alt="BIDV VietQR Code" width="300">
</p>

</details>

---

## 📄 License & Ownership

Copyright (c) 2026 **y0sh1da-available**.

Licensed under the **[MIT License](LICENSE)**.

### Ownership & Attribution Terms:
- You are free to download, run, fork, study, and contribute to this repository.
- **You may NOT claim ownership of this software or remove the original copyright and author attribution.**
- Any redistribution or derivative work must include the original copyright notice and attribution to **y0sh1da-available**.

---

## 🤖 Built with AI

This project was designed, implemented, and refined with **AI assistance** (Google DeepMind Antigravity pair programming), conceived and maintained by **y0sh1da-available**.

---
*Lively Wallpaper is an open-source project created by [rocksdanister](https://github.com/rocksdanister/lively).*
