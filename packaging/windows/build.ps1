# LuminaSaver Windows Build Script
# Builds standalone LuminaSaver.exe and LuminaSaver.scr

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Building LuminaSaver for Windows " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Ensure uv is in PATH
if (Test-Path "C:\Users\$env:USERNAME\.local\bin") {
    $env:Path = "C:\Users\$env:USERNAME\.local\bin;" + $env:Path
}

# Ensure dependencies installed
Write-Host "`n[1/3] Syncing dependencies..." -ForegroundColor Yellow
uv sync --extra build 2>$null
if ($LASTEXITCODE -ne 0) {
    uv sync
}

# Install PyInstaller if missing
Write-Host "`n[2/3] Checking PyInstaller..." -ForegroundColor Yellow
uv pip install pyinstaller

# Build Executable and Screensaver
Write-Host "`n[3/3] Compiling LuminaSaver.exe and LuminaSaver.scr..." -ForegroundColor Yellow
uv run pyinstaller --noconfirm --clean `
    --onefile `
    --windowed `
    --name "LuminaSaver" `
    --add-data "resources;resources" `
    --hidden-import "PySide6.QtMultimedia" `
    --hidden-import "PySide6.QtMultimediaWidgets" `
    --hidden-import "av" `
    --hidden-import "pillow_heif" `
    --hidden-import "watchdog" `
    lumina_saver/main.py

# Create .scr copy for native Windows Screensaver integration
if (Test-Path "dist\LuminaSaver.exe") {
    Copy-Item -Path "dist\LuminaSaver.exe" -Destination "dist\LuminaSaver.scr" -Force
    Write-Host "`nBuild succeeded!" -ForegroundColor Green
    Write-Host "  -> Standalone Application: dist\LuminaSaver.exe" -ForegroundColor White
    Write-Host "  -> Windows Screensaver:   dist\LuminaSaver.scr" -ForegroundColor White
} else {
    Write-Error "Build failed: dist\LuminaSaver.exe was not created."
}
