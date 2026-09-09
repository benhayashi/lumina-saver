# AGENTS.md - LuminaSaver Developer & AI Agent Context Guide

> **To Any AI Coding Agent (Antigravity, Claude, Cursor, Copilot, ChatGPT, etc.)**:
> This document is your primary onboarding file. Read this entire document before writing or modifying code in this repository. It documents the architecture, design principles, hard-won debugging insights, and operational rules for LuminaSaver.

---

## 1. Project Mission & Overview

**LuminaSaver** is a high-performance, cross-platform photo and video screensaver and slideshow player built in Python (PySide6 / Qt6). It is designed as a modern, 64-bit successor to the classic Windows utility *Random Photo Screensaver* by Marijn Kampf.

### Core Problems Solved:
1. **Handling Massive Collections (60,000+ files)** without startup freeze, UI lag, or SMB/NFS network share bottlenecks.
2. **Tri-Engine Video Playback**: Seamless playback of modern codecs (H.264, HEVC/H.265, AV1, VP9) with automatic zero-dependency fallbacks.
3. **Modern Image Decoding**: Full-resolution decoding for JPEG XL (`.jxl`), HEIC/HEIF, AVIF, WebP, PNG, JPEG, and camera RAW formats (`.cr2`, `.nef`, `.arw`).
4. **Dual & Multi-Monitor Support**: Unique, independent photo streams across dual displays with interlocked keyboard controls.
5. **Dual-Mode Operation**: Runs both as a **standalone desktop application** (resizable windowed or fullscreen) and as a **native screensaver** (Windows `.scr` and Linux XScreenSaver).

---

## 2. Codebase Architecture

```
lumina_saver/
├── config.py          # Settings manager persisting to ~/.lumina_saver/config.json
├── exif_reader.py     # High-speed EXIF metadata & GPS parser using piexif & Pillow
├── ff_player.py       # Engine 3: PyAV (bundled FFmpeg) software frame engine fallback
├── indexer.py         # Incremental SQLite database scanner, cache, and weighted randomizer
├── main.py            # CLI entrypoint, argument parser, and SettingsDialog GUI
├── media_loader.py    # High-resolution image decoding pipeline with EXIF auto-rotation
├── multi_monitor.py   # Multi-display coordinator & interlocked keyboard routing
├── player_window.py   # Main QMainWindow, slide timer, and rendering controller
├── transitions.py     # GPU-friendly Ken Burns pan/zoom and crossfade transitions
└── ui_overlay.py      # Translucent glassmorphism HUD overlay (metadata, counter, progress)
```

---

## 3. Critical Technical Lessons & Gotchas (DO NOT BREAK)

### ⚠️ A. The "First-Photo Thumbnail" Race Condition
- **The Issue**: On startup, `showMaximized()` or `showFullScreen()` signals Windows/X11 to expand the window. However, the OS window manager takes ~50–100ms to complete the resize event loop. If the first photo loads immediately at `t=0ms`, `self.size()` returns an unmaximized fallback geometry (e.g. 800x600). The 7000px photo was previously getting scaled down to 800x600, appearing like a small thumbnail in the center of a 4K screen!
- **The Fix in Place**:
  1. `player.start()` defers initial media load using `QTimer.singleShot(100, self.next_media)` to allow window maximization to settle.
  2. `PlayerWindow.resizeEvent` stores `self.current_raw_pixmap` and dynamically rescales the active photo whenever the window geometry changes.
  3. `MediaLoader.load_image_pixmap()` calls `img.load()` to force the full-resolution pixel buffer and **never** calls in-place `img.thumbnail()`.

### ⚠️ B. Tri-Engine Video Architecture
Different machines running Windows or Linux have varying codec support. LuminaSaver uses a 3-tier cascade:
1. **Engine 1 (`libmpv`)**: Hardware-accelerated MPV player. Tested via `ctypes.cdll.LoadLibrary("mpv-1.dll")` on Windows before instantiating.
2. **Engine 2 (`PySide6.QtMultimedia`)**: `QMediaPlayer` + `QVideoWidget` + `QAudioOutput`. Uses native Windows Media Foundation (WMF) or Linux GStreamer.
   - *Crucial Rule*: `QVideoWidget` must be added directly into `QStackedLayout` on the central widget. Wrapping it in an un-managed generic `QWidget` causes Qt to calculate 0x0 size and render a black screen.
3. **Engine 3 (`PyAV` / `ff_player.py`)**: Guaranteed fallback using bundled FFmpeg libraries. Decodes video frames into NumPy arrays and paints directly onto `QLabel` via a high-precision `QTimer`.

### ⚠️ C. Multi-Monitor Interlocked Keyboard Controls
On dual monitors, two `PlayerWindow` instances exist (`players = [player1, player2]`). Standard Qt routing sends keystrokes only to the window with OS focus.
- `MultiMonitorController` intercepts keystrokes across all windows:
  - **`Right Arrow` / `N`**: Advances **Screen 1** (Left).
  - **`Up Arrow` / `Page Up`**: Advances **Screen 2** (Right).
  - **`Left Arrow` / `P`**: Previous on **Screen 1**.
  - **`Down Arrow` / `Page Down`**: Previous on **Screen 2**.
  - **`Spacebar`**: Toggles pause on **ALL** screens simultaneously.
  - **`Escape` / `Q`**: Closes **ALL** screens simultaneously.

### ⚠️ D. Incremental SQLite Indexer
- The SQLite database uses `WAL` mode (`PRAGMA journal_mode=WAL;`).
- `scan_directories()` maintains a preloaded cache of `(file_size, mtime)` for all indexed files. If a file's size and mtime have not changed, it skips opening the file with Pillow, scanning 60,000+ files in **~0.01 seconds**.
- Files containing `thumbnail`, `_thumb`, `.thumb`, `thumbs.db`, `albumart`, or `.cache` in their path are intentionally skipped to avoid caching low-resolution thumbnails.

---

## 4. Development Commands

### Environment Setup (Using `uv`)
```bash
# Sync dependencies (creates clean .venv on the new machine)
uv sync

# Run the application (Settings dialog & launcher)
uv run lumina-saver

# Run standalone windowed mode (1280x720)
uv run lumina-saver --windowed

# Run standalone fullscreen mode
uv run lumina-saver --fullscreen

# Run screensaver mode (mouse move / Esc exits)
uv run lumina-saver --screensaver

# Run unit tests
uv run python -m unittest discover tests
```

---

## 5. Cross-Platform Guidelines for Future Agents
- **Path Handling**: Always use `pathlib.Path` or `os.path.join()`. Never assume Windows drive letters or forward/backward slashes.
- **Default Directory**: `C:\lumina` on Windows, `~/lumina` on Linux/macOS.
- **Virtual Environment Note**: Never copy the `.venv` folder between different computers or operating systems. Run `uv sync` on the target computer to generate a native `.venv` instantly from `uv.lock`.
