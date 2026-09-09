# LuminaSaver 🌟

[![CI Test Suite](https://github.com/benhayashi/lumina-saver/actions/workflows/ci.yml/badge.svg)](https://github.com/benhayashi/lumina-saver/actions/workflows/ci.yml)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Docker-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)]()

**LuminaSaver** is a modern, high-performance, cross-platform photo and video screensaver and slideshow player built to handle massive media collections (60,000+ files on local or network shares) with hardware acceleration, modern format decoding, interlocked multi-display support, and sleek translucent HUD overlays.

Inspired by and built as a modern successor to the classic [Random Photo Screensaver](https://github.com/marijnkampf/Random-Photo-Screensaver) by Marijn Kampf.

---

## ✨ Features

- **🚀 Instant Incremental Indexing**: SQLite-backed caching engine scans 60,000+ files in sub-seconds, skipping unmodified files automatically.
- **🎥 Tri-Engine Video Architecture**:
  - `libmpv` (direct hardware acceleration for 4K 60fps, 10-bit HDR, AV1, HEVC/H.265, VP9).
  - `PySide6.QtMultimedia` (native Windows WMF & Linux GStreamer hardware acceleration).
  - `PyAV` (bundled FFmpeg software frame engine fallback).
- **📸 Modern Image Format Support**: Full-resolution decoding for **JPEG XL (`.jxl`)**, **HEIC/HEIF**, **AVIF**, **WebP**, **PNG**, **JPEG**, and camera **RAW** formats (`.cr2`, `.nef`, `.arw`).
- **🖥️ Dual & Multi-Monitor Independent Streams**: Spans across multiple monitors, playing unique, desynchronized photo/video streams on each screen.
- **🎮 Interlocked Multi-Display Controls**: Keyboard arrow routing allowing interleaved navigation across displays from a single keyboard.
- **🪟 Standalone & Screensaver Dual-Mode**:
  - **Standalone Desktop App**: Launch in resizable Windowed mode (`--windowed`) or Fullscreen mode (`--fullscreen`) with visible cursor and window controls.
  - **Screensaver Mode**: Fullscreen mode exiting on mouse motion or `Esc` (`--screensaver`, Windows `/s`, or Linux `-root`).
- **✨ Fluid GPU Transitions**: Hardware-accelerated crossfades, subtle Ken Burns pan/zoom motion, and soft blur dissolves.
- **🎨 Glassmorphism Overlays**: Translucent HUD cards displaying folder location, file name, camera EXIF details (ISO, Shutter, Aperture, Date Taken), and progress.
- **🔍 Display Filters**: Minimum resolution filter (HD 720p+, Full HD 1080p+, 4K 2160p+) and orientation filter (Landscape only, Portrait only).

---

## 🎮 Keyboard Controls

| Key | Single Monitor | Dual / Multi-Monitor |
| :--- | :--- | :--- |
| `Right Arrow` / `N` | Next photo or video | Next photo on **Screen 1** |
| `Up Arrow` / `Page Up` | Skip to next folder | Next photo on **Screen 2** |
| `Left Arrow` / `P` | Previous photo or video | Previous photo on **Screen 1** |
| `Down Arrow` / `Page Down` | Jump 10 items ahead | Previous photo on **Screen 2** |
| `Tab` | Switch active screen focus | Switch active screen focus |
| `Space` | Pause / Resume | Pause / Resume **ALL** screens |
| `O` | Cycle overlay (Off $\rightarrow$ Minimal $\rightarrow$ Full) | Cycle overlay on **ALL** screens |
| `F` | Reveal current file in File Explorer / Manager | Reveal file on active screen |
| `Esc` / `Q` | Exit application or screensaver | Exit **ALL** screens |

---

## 📦 Quick Start

### Prerequisites
- Python 3.10+
- Recommended: [`uv`](https://github.com/astral-sh/uv) (fast Python package manager)

### 1. Clone & Run with `uv`
```bash
# Clone the repository
git clone https://github.com/benhayashi/lumina-saver.git
cd lumina-saver

# Sync environment and run
uv sync
uv run lumina-saver
```

### 2. Command Line Options
```bash
# Open Settings Dialog
uv run lumina-saver --config

# Run Standalone in a 1280x720 Window
uv run lumina-saver --windowed

# Run Standalone in Fullscreen Mode
uv run lumina-saver --fullscreen

# Run in Screensaver Mode (Mouse movement or Esc exits)
uv run lumina-saver --screensaver
```

---

## 🖥️ Platform Deployment

### Windows Setup

#### 1. Build Executable & Screensaver
```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
```
Builds `dist\LuminaSaver.exe` (Standalone Application) and `dist\LuminaSaver.scr` (Windows Screensaver).

#### 2. Install as Windows Screensaver
```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\install-screensaver.ps1
```
Installs `LuminaSaver.scr` and opens the Windows Screen Saver Settings dialog.

---

### Linux Setup

#### 1. System Dependencies (Debian / Ubuntu)
```bash
sudo apt-get update
sudo apt-get install -y libmpv-dev mpv libegl1 libgl1 libxkbcommon-x11-0 libpulse0
```

#### 2. Build & Install to Desktop
```bash
chmod +x packaging/linux/build.sh packaging/linux/install.sh
./packaging/linux/install.sh
```
Installs:
- Binary: `~/.local/bin/lumina-saver`
- Desktop Launcher: `~/.local/share/applications/lumina-saver.desktop`
- Application Icon: `~/.local/share/icons/hicolor/scalable/apps/lumina-saver.svg`
- XScreenSaver config: `/usr/share/xscreensaver/config/lumina-saver.xml`

---

### Docker Deployment 🐳

LuminaSaver can run inside a containerized Ubuntu environment with full GPU hardware acceleration and X11 display forwarding.

#### 1. Quick Start with Docker Compose
```bash
# Allow local Docker container to connect to X11 display
xhost +local:root

# Start with default settings mounting ./media
docker compose up
```

#### 2. Run with Custom Photo Directory via `docker run`
```bash
# Allow local X11 connections
xhost +local:root

# Run fullscreen with GPU acceleration and host photos mounted
docker run --rm -it \
    --net=host \
    -e DISPLAY=$DISPLAY \
    -e QT_X11_NO_MITSHM=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v $HOME/.Xauthority:/root/.Xauthority:ro \
    -v /path/to/your/photos:/media:ro \
    -v lumina-config:/root/.lumina_saver \
    --device /dev/dri:/dev/dri \
    lumina-saver:latest --fullscreen
```

---

## 🛠️ Multi-Workstation Development

For instructions on cloning and developing LuminaSaver across multiple computers, see the [Development Guide (DEVELOPMENT.md)](DEVELOPMENT.md).

---

## 📜 Acknowledgments & Citation

This project was inspired by and inherits concepts from:
- [Random Photo Screensaver](https://github.com/marijnkampf/Random-Photo-Screensaver) by Marijn Kampf (GPL License).
- [mpv media player](https://mpv.io) & [libmpv](https://github.com/mpv-player/mpv).
- [PySide6 / Qt for Python](https://www.qt.io/qt-for-python).

Licensed under **GNU General Public License v3.0 (GPL-3.0)**.
