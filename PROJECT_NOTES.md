# Project Notes & Engineering Handover: LuminaSaver

**Project Name**: LuminaSaver  
**Version**: 1.0.0  
**License**: GNU General Public License v3.0 (GPL-3.0)  
**Primary Language**: Python 3.10+ (PySide6 / Qt6, Pillow, libmpv, PyAV)  

---

## 1. Project Background & Vision

LuminaSaver was developed as a modern, high-performance, 64-bit successor to the classic Windows software [Random Photo Screensaver](https://github.com/marijnkampf/Random-Photo-Screensaver) by Marijn Kampf.

The original utility was beloved for its ability to shuffle through vast local and network photo directories, but modern setups introduced new demands:
- 4K, 5K, and OLED HDR displays requiring GPU acceleration.
- Modern image formats: Apple HEIC/HEIF, Google/Web WebP, JPEG XL (`.jxl`), and camera RAW files.
- Video playback integration: Family video clips (H.264, HEVC 4K, VP9, AV1) mixed seamlessly into the photo stream.
- Multi-monitor setups: Two or more screens displaying independent photos simultaneously.
- Cross-platform support: Ability to run on Windows as a native `.scr` or on Linux/Raspberry Pi as a dedicated photo display or screensaver.

---

## 2. Iteration History & Solved Challenges

| Version / Phase | Challenge Encountered | Solution Implemented |
| :--- | :--- | :--- |
| **Initial Prototype** | High startup delay scanning 60,000+ files on network shares. | Migrated to an asynchronous SQLite indexing engine (`indexer.py`) with WAL mode. |
| **Media Scanning** | Scanning every startup took several seconds. | Added cached `mtime` and `file_size` checks. Unmodified files skip image header decoding, dropping scan time to **0.01s**. |
| **Video Engine** | System `libmpv` DLL missing on Windows systems caused crashes or black screen. | Created a 3-tier cascade: `libmpv` $\rightarrow$ `PySide6.QtMultimedia` $\rightarrow$ `PyAV` (bundled FFmpeg software decoder fallback). |
| **Geometry Glitch** | First photo rendered as a small centered thumbnail on 4K screens while metadata reported 7000+ pixels. | Fixed OS window maximization race condition: added 100ms startup delay buffer and dynamic image rescaling in `resizeEvent`. |
| **Display Filters** | User wanted to avoid tiny low-res images or wrong aspect ratios on high-res displays. | Added SQLite-level resolution filters (`720p`, `1080p`, `4K`) and orientation filters (`Landscape`, `Portrait`). |
| **Multi-Display** | Dual monitors were running separately with disjointed controls. | Created `MultiMonitorController` allowing interlocked arrow keys (`Right Arrow` for Screen 1, `Up Arrow` for Screen 2, `Space` to pause all). |
| **Standalone Mode** | Needed ability to run as a normal desktop app, not just a screensaver. | Added `--windowed`, `--fullscreen`, and `--config` CLI flags and Settings GUI options. |

---

## 3. Data Flow & Subsystems

```
+-------------------------------------------------------------+
|                      Settings GUI / CLI                     |
|            (main.py / SettingsDialog / ConfigManager)       |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                     MediaIndexer (indexer.py)               |
|      - Scans local & network media folders (C:\lumina)      |
|      - Stores path, size, mtime, width, height in SQLite    |
|      - Weighted random picker or sequential order resume    |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                 PlayerWindow (player_window.py)             |
|      - Handles slide timer & crossfade animations           |
|      - Dispatches image decoding to MediaLoader             |
|      - Dispatches video decoding to mpv/Qt/PyAV             |
|      - Updates translucent UIOverlay (HUD card & progress)  |
+------------------------------+------------------------------+
                               ^
                               |
+------------------------------+------------------------------+
|            MultiMonitorController (multi_monitor.py)        |
|      - Coordinates multiple PlayerWindow instances          |
|      - Interlocked keyboard routing for dual screens        |
+-------------------------------------------------------------+
```

---

## 4. Key Configuration Keys (`~/.lumina_saver/config.json`)

- `media_directories`: List of directories to scan (default: `["C:\\lumina"]` on Windows, `["~/lumina"]` on Linux).
- `window_mode`: `"fullscreen"` or `"windowed"`.
- `multi_monitor_mode`: `"dual_independent"` (separate stream per screen) or `"primary_only"`.
- `interlocked_multi_monitor`: `true` (enables cross-screen arrow key navigation).
- `image_duration`: Display duration in seconds per slide (default: `6.0`).
- `display_order`: `"random"` or `"sequential"`.
- `last_sequential_id`: Saved position for resuming sequential playback across restarts.
- `min_resolution`: `"none"`, `"720p"`, `"1080p"`, or `"4k"`.
- `orientation_filter`: `"all"`, `"landscape"`, or `"portrait"`.
- `mute_videos`: `true` or `false`.
- `video_duration_mode`: `"full"` (plays entire video clip), `"photo_duration"` (clips video to photo time), or `"custom"`.
- `show_progress_bar`: `true` or `false` (toggles blue progress indicator at bottom).

---

## 5. Transferring to a New Machine (No Git / Offline Transfer)

When moving this project folder to another computer:
1. **Do NOT copy the `.venv` folder**. Virtual environments contain machine-specific absolute paths and binaries.
2. Copy the project folder containing:
   - `lumina_saver/`
   - `packaging/`
   - `resources/`
   - `tests/`
   - `pyproject.toml`
   - `uv.lock`
   - `AGENTS.md`
   - `PROJECT_NOTES.md`
   - `DEVELOPMENT.md`
   - `README.md`
   - `LICENSE`
3. On the new machine, install `uv` and run:
   ```bash
   uv sync
   uv run lumina-saver
   ```
   *`uv` will build the fresh local virtual environment and install all dependencies in under 10 seconds.*
