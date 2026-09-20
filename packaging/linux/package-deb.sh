#!/usr/bin/env bash
# LuminaSaver Debian/Ubuntu Package Builder (.deb)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

VERSION="1.0.0"
PACKAGE_NAME="lumina-saver"
ARCH="amd64"
DEB_NAME="${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
STAGING_DIR="$PROJECT_ROOT/build/deb_staging"

echo "=========================================="
echo " Packaging ${DEB_NAME} "
echo "=========================================="

# 1. Ensure binary is built
if [ ! -f "dist/lumina-saver" ]; then
    echo "[1/4] Binary not found. Building dist/lumina-saver..."
    bash "$SCRIPT_DIR/build.sh"
else
    echo "[1/4] Found existing binary dist/lumina-saver"
fi

# 2. Prepare staging directory
echo "[2/4] Preparing package directory structure..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR/DEBIAN"
mkdir -p "$STAGING_DIR/usr/bin"
mkdir -p "$STAGING_DIR/usr/share/applications"
mkdir -p "$STAGING_DIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$STAGING_DIR/usr/share/xscreensaver/config"

# 3. Copy files
echo "[3/4] Copying files..."
cp "dist/lumina-saver" "$STAGING_DIR/usr/bin/lumina-saver"
chmod 755 "$STAGING_DIR/usr/bin/lumina-saver"

cp "packaging/linux/lumina-saver.desktop" "$STAGING_DIR/usr/share/applications/lumina-saver.desktop"
chmod 644 "$STAGING_DIR/usr/share/applications/lumina-saver.desktop"

cp "resources/icon.svg" "$STAGING_DIR/usr/share/icons/hicolor/scalable/apps/lumina-saver.svg"
chmod 644 "$STAGING_DIR/usr/share/icons/hicolor/scalable/apps/lumina-saver.svg"

cp "packaging/linux/lumina-saver.xml" "$STAGING_DIR/usr/share/xscreensaver/config/lumina-saver.xml"
chmod 644 "$STAGING_DIR/usr/share/xscreensaver/config/lumina-saver.xml"

# Control file
cat << EOF > "$STAGING_DIR/DEBIAN/control"
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: Ben Hayashi <ben@local>
Depends: libmpv-dev | libmpv2 | libmpv1, mpv, libegl1, libgl1, libxkbcommon-x11-0, libpulse0
Description: Modern photo and video screensaver & slideshow viewer
 LuminaSaver is a high-performance, cross-platform photo and video screensaver
 and slideshow player built to handle massive media collections (60,000+ files)
 with hardware acceleration, modern format decoding, interlocked multi-display
 support, and translucent HUD overlays.
EOF

# 4. Build .deb package
echo "[4/4] Building .deb package with dpkg-deb..."
dpkg-deb --build --root-owner-group "$STAGING_DIR" "dist/${DEB_NAME}"

echo ""
echo "=========================================================="
echo " Successfully created: dist/${DEB_NAME}"
echo " Install on Ubuntu with:"
echo "   sudo apt install ./dist/${DEB_NAME}"
echo "   or"
echo "   sudo dpkg -i ./dist/${DEB_NAME}"
echo "=========================================================="
