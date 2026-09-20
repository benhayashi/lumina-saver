@echo off
title Installing LuminaSaver Screensaver
echo ==========================================
echo  Installing LuminaSaver Screensaver
echo ==========================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-screensaver.ps1"
pause
