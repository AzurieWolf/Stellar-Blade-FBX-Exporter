@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0[Build Log Window].ps1" %*
exit /b %errorlevel%
