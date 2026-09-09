# Changelog

All notable changes to **LuminaSaver** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-09

### Added
- **High-Performance Incremental Media Indexer**:
  - SQLite database backend with Write-Ahead Logging (`WAL` mode) and synchronous normal mode.
  - Sub-second scanning for massive collections (60,000+ files) via cached `(file_size, mtime)` checks.
  - Support for both random shuffle and sequential playback order with restart resume.
- **Tri-Engine Video Playback Cascade**:
  - **Engine 1 (`libmpv`)**: Direct hardware acceleration for 4K 60fps, 10-bit HDR, AV1, HEVC/H.265, and VP9.
  - **Engine 2 (`PySide6.QtMultimedia`)**: Native OS hardware decoding (Windows WMF and Linux GStreamer).
  - **Engine 3 (`PyAV` / `ff_player.py`)**: Bundled FFmpeg software decoding fallback painting to Qt canvas.
- **Modern Image Format Support**:
  - Full-resolution decoding for JPEG XL (`.jxl`), Apple HEIC/HEIF, AVIF, WebP, PNG, JPEG, and camera RAW formats (`.cr2`, `.nef`, `.arw`).
  - Automatic EXIF orientation normalization and full pixel buffer loading.
- **Dual & Multi-Monitor Independent Streams**:
  - Unique, desynchronized photo and video playback across all connected physical displays.
  - Interlocked keyboard controls (`Right Arrow` for Screen 1, `Up Arrow` for Screen 2, `Space` for global pause).
  - `Tab` key cycling to select active focus between displays with temporary HUD toast feedback.
- **Glassmorphism HUD Overlays**:
  - Translucent glass cards displaying folder, file name, camera EXIF metadata (camera model, shutter speed, aperture, ISO), and date taken.
  - Slide timer progress bar with accent blue styling.
  - Centered pause card and interactive toast message alerts.
  - Three overlay modes: `Full`, `Minimal`, and `Off` (toggled via `O` key).
- **Dual-Mode Operation**:
  - Standalone desktop application with resizable windowed (`--windowed`) and fullscreen (`--fullscreen`) modes.
  - Native screensaver mode (`--screensaver`, Windows `/s`, Linux `-root`) with sensitive mouse motion wake-up.
- **Display Filters**:
  - Resolution filtering: HD (`720p+`), Full HD (`1080p+`), and 4K (`2160p+`).
  - Orientation filtering: Landscape only, Portrait only, or All.
- **Multi-Platform Packaging**:
  - Linux standalone ELF binary packaging (`packaging/linux/build.sh`, `packaging/linux/install.sh`).
  - Windows executable and screensaver packaging (`packaging/windows/build.ps1`, `packaging/windows/install-screensaver.ps1`).
  - Docker containerization support (`Dockerfile`, `docker-compose.yml`) with X11 GUI display pass-through.
- **Comprehensive Test Suite**:
  - Automated unit tests covering EXIF parsing, SQLite indexing, configuration management, transitions, MediaLoader decoders, UI HUD overlay, and multi-monitor key routing.
