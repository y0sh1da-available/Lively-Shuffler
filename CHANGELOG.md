# Changelog

All notable changes to **Lively Wallpaper Shuffler** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.4] - 2026-10-19

### Added
- **🌙 Night Time Mode (Auto-Pause Sleep Hours):**
  - Added a dedicated Night Mode toggle with customizable start time **A** and end time **B**.
  - **Manual Entry & AM/PM Format:** Allows typing any custom time (e.g., `12:45`, `12:45 PM`, `11:00 PM`, `23:00`, `11pm`) with auto-formatting, alongside convenient preset dropdown buttons.
  - Automatically suppresses timer-based wallpaper switching during sleeping hours to prevent waking up monitors or lightening dark rooms while the PC is asleep.
  - Seamlessly handles overnight time ranges that cross midnight.
  - Automatically resumes normal shuffling when the configured end time arrives without requiring manual intervention.
  - Displays dynamic status in the dashboard: `🌙 Night Mode (Paused until HH:MM AM/PM)` and updates tray tooltips.
- **System Tray Night Mode Toggle:**
  - Added a quick-toggle option for Night Mode directly in the system tray right-click menu.
- **Double-Click System Tray Icon to Open Dashboard:**
  - Double-clicking or clicking the notification area icon immediately restores, lifts, and focuses the main GUI window to the foreground.

### Fixed
- **Small Window Left-Side Overlap & Sidebar Squashing:**
  - Replaced rigid sidebar container with a smooth canvas-backed scrollable layout, preventing controls from squashing or overlapping in smaller window sizes.
  - Added screen boundary protection that guarantees the window is never spawned or positioned off the screen edges ($X \ge 20, Y \ge 20$).
  - Relaxed minimum window constraints to `760x480` for compact and high-DPI scaling displays.

---

## [1.0.3] - 2026-10-16

### Added
- **Sub-millisecond Selection Latency:**
  - Dispatched Lively CLI switches to an asynchronous background worker queue (`queue.Queue`) with rapid-click coalescing.
  - Optimistic, zero-delay UI showcase transitions and active border updates.

### Fixed
- **Eliminated Visual Scroll "Shattering":**
  - Replaced virtual window recreation with a persistent Canvas container frame (`cards_container`) and reusable card widget pool.
  - Implemented pixel-precise hardware scrolling (`yscrollincrement=1`) with unified mousewheel and trackpad event forwarding.

---

## [1.0.2] - 2026-10-16

### Changed
- Cleaned release pipeline and removed checksum assets from release artifacts.
- Improved VietQR contribution link pre-filled payment message.

---

## [1.0.1] - 2026-10-16

### Added
- **Multi-Source Discovery Engine:**
  - Auto-detection for Microsoft Store (UWP/MSIX) Lively Wallpaper package directories and execution aliases (`%LOCALAPPDATA%\Microsoft\WindowsApps\Lively.exe`).
  - Added support for custom drive letters (`D:\`, `E:\`), portable directories, and registry uninstall keys.

---

## [1.0.0] - 2026-10-16

### Added
- Initial public release of Lively Wallpaper Shuffler.
- Standalone zero-dependency Windows executable.
- High-contrast dark dashboard with live search and thumbnail gallery.
- Silent background shuffling with customizable timer intervals (30s to 4h).
- Single-instance mutex protection and system tray integration.
