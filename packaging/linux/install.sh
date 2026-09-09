#!/usr/bin/env bash
# LuminaSaver Linux Desktop & Screensaver Installer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=========================================="
echo " Installing LuminaSaver on Linux "
echo "=========================================="

BIN_SOURCE="$PROJECT_ROOT/dist/lumina-saver"

if [ ! -f "$BIN_SOURCE" ]; then
    echo "Compiled binary not found in dist/. Running build script..."
    bash "$SCRIPT_DIR/build.sh"
fi

# Target directories (user-level, no root required)
PREFIX="${HOME}/.local"
BIN_DIR="${PREFIX}/bin"
APP_DIR="${PREFIX}/share/applications"
ICON_DIR="${PREFIX}/share/icons/hicolor/scalable/apps"

mkdir -p "$BIN_DIR" "$APP_DIR" "$ICON_DIR"

# 1. Install binary
echo "[1/4] Installing binary to $BIN_DIR/lumina-saver..."
cp "$BIN_SOURCE" "$BIN_DIR/lumina-saver"
chmod +x "$BIN_DIR/lumina-saver"

# 2. Install icon
echo "[2/4] Installing application icon to $ICON_DIR..."
cp "$PROJECT_ROOT/resources/icon.svg" "$ICON_DIR/lumina-saver.svg"

# 3. Install desktop launcher
echo "[3/4] Installing desktop entry to $APP_DIR..."
cp "$SCRIPT_DIR/lumina-saver.desktop" "$APP_DIR/lumina-saver.desktop"
sed -i "s|Exec=lumina-saver|Exec=$BIN_DIR/lumina-saver|g" "$APP_DIR/lumina-saver.desktop"

# 4. XScreenSaver integration (if available)
echo "[4/4] Checking screensaver integrations..."
if [ -d "/usr/share/xscreensaver/config" ] && [ -w "/usr/share/xscreensaver/config" ]; then
    cp "$SCRIPT_DIR/lumina-saver.xml" /usr/share/xscreensaver/config/
    echo "  -> Added LuminaSaver to system XScreenSaver config."
fi

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t "${PREFIX}/share/icons/hicolor" 2>/dev/null || true
fi

echo ""
echo "=========================================================="
echo " LuminaSaver successfully installed!"
echo " - Run standalone:      lumina-saver"
echo " - Open settings:       lumina-saver --config"
echo " - Run screensaver:     lumina-saver --screensaver"
echo " - Desktop menu:        Search for 'LuminaSaver' in app launcher"
echo "=========================================================="
