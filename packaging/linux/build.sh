#!/usr/bin/env bash
# LuminaSaver Linux Build Script
# Builds standalone ELF binary for Linux using PyInstaller

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo " Building LuminaSaver for Linux "
echo "=========================================="

# Check for uv
if command -v uv &> /dev/null; then
    echo "[1/3] Syncing dependencies with uv..."
    uv sync
    echo "[2/3] Checking PyInstaller..."
    uv pip install pyinstaller
    PYINSTALLER_CMD="uv run pyinstaller"
else
    echo "[1/3] Using system python..."
    python3 -m pip install --upgrade pip pyinstaller
    python3 -m pip install -e .
    PYINSTALLER_CMD="pyinstaller"
fi

echo "[3/3] Compiling standalone Linux executable..."
$PYINSTALLER_CMD --noconfirm --clean \
    --onefile \
    --windowed \
    --name "lumina-saver" \
    --add-data "resources:resources" \
    --hidden-import "PySide6.QtMultimedia" \
    --hidden-import "PySide6.QtMultimediaWidgets" \
    --hidden-import "av" \
    --hidden-import "pillow_heif" \
    --hidden-import "watchdog" \
    lumina_saver/main.py

chmod +x dist/lumina-saver
echo ""
echo "Build succeeded! Executable located at: dist/lumina-saver"
