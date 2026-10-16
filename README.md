# Lively Wallpaper Shuffler

<p align="center">
  <img src="app_icon.png" alt="Lively Wallpaper Shuffler Logo" width="128" height="128">
</p>

<p align="center">
  <strong>A lightweight, zero-configuration Windows background companion for <a href="https://github.com/rocksdanister/lively">Lively Wallpaper</a> (v2.x+).</strong>
  <br>
  Automatically cycles and shuffles live wallpapers on your desktop with full system-tray controls.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?logo=windows&logoColor=white" alt="Windows Support">
  <img src="https://img.shields.io/badge/Lively%20Wallpaper-v2.0%2B-blueviolet" alt="Lively Compatibility">
  <img src="https://img.shields.io/badge/Release-Single%20.exe-success" alt="Single Executable">
  <img src="https://img.shields.io/badge/Configuration-Zero%20Config-brightgreen" alt="Zero Config">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
</p>

---

## 💡 Why This Utility?

Legacy community shufflers (such as *lively-wallpaper-playlist*) rely on an obsolete IPC TCP socket interface (`port 65432`) and hardcoded configuration paths that are **broken** on modern Lively Wallpaper v2.x+ installations.

**Lively Wallpaper Shuffler** solves this cleanly:
- **Direct Process Invocation:** Modern Lively Wallpaper v2.x+ accepts commands natively via process arguments:
  ```cmd
  "<Lively_Directory>\Lively.exe" setwp --file "<Wallpaper_Folder_Path>"
  ```
- **Zero-Config Auto-Discovery:** Automatically detects both the Lively executable and your wallpaper library (`%LOCALAPPDATA%\Lively Wallpaper\Library\wallpapers` or custom library directories defined in `Settings.json`).
- **Silent Background Execution:** Commands run using `CREATE_NO_WINDOW` and hidden process flags—no annoying black terminal windows popping up on screen.
- **Single Portable Binary:** Self-contained single-file `.exe`. No Python runtime, dependencies, or installers required.

---

## 🚀 Quick Start (End Users)

1. Download **`LivelyWallpaperShuffler.exe`** from the **[Latest Releases](https://github.com/)** tab.
2. Double-click **`LivelyWallpaperShuffler.exe`**.
3. That's it! Look for the icon in your Windows system tray (near the clock).
4. *(Optional)* Right-click the tray icon and enable **"Start with Windows"** to cycle wallpapers automatically every time you log in.

---

## 🎛️ System Tray Features

Right-click the icon in your system tray to access options:

| Control | Description |
| :--- | :--- |
| **Current Wallpaper** | Displays the title of the active wallpaper; click to open the wallpaper folder in File Explorer. |
| **Next Wallpaper** | Immediately switch to another wallpaper (Random or Sequential). Default action on double-click. |
| **Previous Wallpaper** | Revisit previously viewed wallpapers in history. |
| **Pause / Resume** | Freeze on the current wallpaper or resume the timer cycle. |
| **Interval Submenu** | Choose presets: `30 sec`, `1 min`, `5 min`, `10 min`, `15 min`, `30 min`, `1 hr`, `2 hr`, `4 hr`. |
| **Mode Submenu** | Choose between `Shuffle (Random)` or `Sequential (In Order)`. |
| **Wallpapers Submenu** | Direct pick list of all detected wallpapers in your library. |
| **Open Wallpapers Folder** | Opens `%LOCALAPPDATA%\Lively Wallpaper\Library\wallpapers` in File Explorer. |
| **Start with Windows** | Adds or removes the utility from the Windows Registry Run key (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`). |
| **Reload Wallpapers** | Re-scans library folders when you install or delete wallpapers. |
| **Exit** | Gracefully cleans up threads and shuts down the shuffler. |

---

## ⚡ CLI / Hotkey Support

You can bind keyboard shortcuts, stream decks, or scripts to trigger actions:

```cmd
:: Switch to next wallpaper immediately and exit
LivelyWallpaperShuffler.exe --next

:: Switch to previous wallpaper immediately and exit
LivelyWallpaperShuffler.exe --prev

:: Inspect detected environment, Lively executable, and active wallpaper
LivelyWallpaperShuffler.exe --status

:: Display command-line help
LivelyWallpaperShuffler.exe --help
```

---

## 🔍 Auto-Discovery Architecture

The utility requires **zero configuration** by resolving paths across multiple discovery layers:

### 1. Wallpaper Library Detection
- **Lively Settings:** Parses `%LOCALAPPDATA%\Lively Wallpaper\Settings.json` to extract custom `WallpaperDir` if configured by the user.
- **Standard Default:** Scans `%LOCALAPPDATA%\Lively Wallpaper\Library\wallpapers`.
- **Validation:** Iterates subfolders and parses `LivelyInfo.json` to verify title, type, and valid project metadata.

### 2. Lively Executable Detection
1. **Active Process Inspection:** Queries running processes via Win32 Toolhelp API (`CreateToolhelp32Snapshot`) looking for `Lively.exe` or companion processes.
2. **User Installation Path:** Checks `%LOCALAPPDATA%\Programs\Lively Wallpaper\Lively.exe` and `livelycu.exe`.
3. **System Installation Paths:** Checks `%ProgramFiles%\Lively Wallpaper\` and `%ProgramFiles(x86)%\Lively Wallpaper\`.
4. **Windows Registry:** Queries `HKCU` and `HKLM` under `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Lively.exe`.
5. **MS Store Alias:** Checks `%LOCALAPPDATA%\Microsoft\WindowsApps\Lively.exe`.

### 3. Active Wallpaper Sync
- Parses `%LOCALAPPDATA%\Lively Wallpaper\WallpaperLayout.json` on startup to detect the active screen arrangement and pre-select the currently active wallpaper.

### 4. Single-Instance Protection
- Uses a named Win32 mutex (`Global\LivelyWallpaperShuffler_SingleInstance_Mutex`) to ensure multiple background tray loops never collide.

---

## 🛠️ Building from Source

### Prerequisites
- Windows 10 or 11
- Python 3.10+
- Git

### Build Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/lively-wallpaper-shuffler.git
   cd lively-wallpaper-shuffler
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run directly with Python:
   ```bash
   python lively_shuffler.py
   ```

4. Compile into a standalone Windows `.exe`:
   ```bash
   python build.py
   # Or double click build.bat
   ```
   The compiled single-file binary will be generated at `dist/LivelyWallpaperShuffler.exe`.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
Lively Wallpaper is developed by [rocksdanister](https://github.com/rocksdanister/lively) under GPL-3.0.
