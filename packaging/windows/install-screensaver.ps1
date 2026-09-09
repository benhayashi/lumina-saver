# LuminaSaver Windows Screensaver Installer
# Installs LuminaSaver.scr and optionally configures it as active screensaver

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$scrSource = Join-Path $projectRoot "dist\LuminaSaver.scr"

if (-not (Test-Path $scrSource)) {
    Write-Host "LuminaSaver.scr not found in dist/. Attempting build..." -ForegroundColor Yellow
    & (Join-Path $scriptDir "build.ps1")
    if (-not (Test-Path $scrSource)) {
        Write-Error "Could not find or build LuminaSaver.scr."
        exit 1
    }
}

# Install destination in User LocalAppData (no admin required) or System32 (if elevated)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    $installDir = "$env:SystemRoot\System32"
    $targetPath = Join-Path $installDir "LuminaSaver.scr"
    Copy-Item -Path $scrSource -Destination $targetPath -Force
    Write-Host "[Success] Installed LuminaSaver.scr to Windows System32: $targetPath" -ForegroundColor Green
} else {
    $installDir = "$env:LOCALAPPDATA\LuminaSaver"
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    $targetPath = Join-Path $installDir "LuminaSaver.scr"
    Copy-Item -Path $scrSource -Destination $targetPath -Force
    
    # Also register in Windows HKCU ScreenSaver
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "SCRNSAVE.EXE" -Value $targetPath
    Write-Host "[Success] Installed LuminaSaver.scr to $targetPath and set as current user screensaver!" -ForegroundColor Green
}

# Open Windows Screen Saver Settings dialog
Write-Host "Opening Windows Screen Saver Settings..." -ForegroundColor Cyan
Start-Process "control.exe" -ArgumentList "desk.cpl,,@screensaver"
