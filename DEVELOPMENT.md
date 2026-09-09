# LuminaSaver Development Guide 🛠️

This guide outlines how to clone, set up, develop, test, and build **LuminaSaver** on any Windows or Linux workstation.

---

## 1. Prerequisites

### Recommended Tool: [`uv`](https://github.com/astral-sh/uv) (Fast Python Package Manager)

- **Windows**:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Linux / macOS**:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### System Libraries

- **Windows**:
  - All decoders (QtMultimedia, PyAV FFmpeg) are bundled within python wheels. Optional: `mpv-1.dll` in system PATH for direct libmpv hardware acceleration.
- **Linux (Ubuntu / Debian)**:
  ```bash
  sudo apt-get update
  sudo apt-get install -y libmpv-dev mpv libegl1 libgl1 libxkbcommon-x11-0 libpulse0
  ```
- **Linux (Arch / Fedora)**:
  - Arch: `sudo pacman -S mpv qt6-multimedia`
  - Fedora: `sudo dnf install mpv qt6-qtmultimedia`

---

## 2. Setting Up the Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/lumina-saver.git
   cd lumina-saver
   ```

2. **Sync Virtual Environment**:
   ```bash
   uv sync
   ```
   *This automatically creates `.venv/` and installs all dependencies (`PySide6`, `python-mpv`, `pillow-heif`, `piexif`, `av`, `watchdog`).*

3. **Alternative (Standard `pip`)**:
   ```bash
   python3 -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux:
   source .venv/bin/activate

   pip install -e .
   ```

---

## 3. Running LuminaSaver in Development

- **Launch Settings GUI**:
  ```bash
  uv run lumina-saver
  ```

- **Launch Standalone Windowed Mode (1280×720)**:
  ```bash
  uv run lumina-saver --windowed
  ```

- **Launch Standalone Fullscreen Mode**:
  ```bash
  uv run lumina-saver --fullscreen
  ```

- **Test Screensaver Mode** (mouse movement or `Esc` exits):
  ```bash
  uv run lumina-saver --screensaver
  ```

- **Windows Screensaver Flags**:
  ```bash
  uv run lumina-saver /s     # Fullscreen screensaver
  uv run lumina-saver /c     # Settings dialog
  ```

- **Linux XScreenSaver Flags**:
  ```bash
  uv run lumina-saver -root
  ```

---

## 4. Running Automated Tests

Run the unit test suite:
```bash
uv run python -m unittest discover tests
```

---

## 5. Building Standalone Packages

### On Windows
Run the Windows build script:
```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
```
Output:
- `dist/LuminaSaver.exe` (Standalone portable application)
- `dist/LuminaSaver.scr` (Windows Screensaver)

To install the screensaver on Windows:
```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\install-screensaver.ps1
```

### On Linux
Run the Linux build script:
```bash
chmod +x packaging/linux/build.sh packaging/linux/install.sh
./packaging/linux/build.sh
```
Output:
- `dist/lumina-saver` (Standalone Linux ELF x64 executable)

To install to system/user desktop menu:
```bash
./packaging/linux/install.sh
```

---

## 6. Project Architecture

```
lumina_saver/
├── config.py          # Settings manager persisted in ~/.lumina_saver/config.json
├── exif_reader.py     # Fast EXIF metadata & GPS coordinate parser
├── ff_player.py       # PyAV / FFmpeg software frame engine fallback
├── indexer.py         # Incremental SQLite database scanner & weighted randomizer
├── main.py            # CLI entrypoint, argument parser & Settings dialog
├── media_loader.py    # Pillow / pillow-heif / JXL / RAW high-res decoder
├── multi_monitor.py   # Multi-screen coordinator & interlocked hotkey router
├── player_window.py   # Primary QMainWindow, video player & HUD coordinator
├── transitions.py     # Ken Burns & crossfade transition curves
└── ui_overlay.py      # Glassmorphism translucent HUD overlay
```

---

## 7. Multi-Monitor Keyboard Routing

| Key | Action |
| :--- | :--- |
| `Right Arrow` / `N` | Advance Screen 1 |
| `Up Arrow` / `Page Up` | Advance Screen 2 |
| `Left Arrow` / `P` | Previous Screen 1 |
| `Down Arrow` / `Page Down` | Previous Screen 2 |
| `Space` | Pause / Resume all screens |
| `O` | Toggle HUD overlay |
| `Esc` / `Q` | Close all screens |
