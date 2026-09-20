@echo off
title Building LuminaSaver for Windows
echo ==========================================
echo  Building LuminaSaver for Windows (.exe / .scr)
echo ==========================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1"
pause
