@echo off
title PC Remote Bot - Uninstaller
color 0C

:: ===== AUTO REQUEST ADMIN =====
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Requesting Administrator...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit
)

echo.
echo  ============================================
echo   PC Remote Bot - Uninstaller
echo  ============================================
echo.

:: ===== CONFIRM UNINSTALL =====
set /p CONFIRM="Are you sure you want to uninstall? (Y/N): "
if /i "%CONFIRM%" neq "Y" (
    echo [*] Uninstall cancelled!
    pause
    exit
)

:: ===== STOP BOT =====
echo [*] Stopping bot...
taskkill /f /im tracker.exe >nul 2>&1
taskkill /f /im PCRemoteBot.exe >nul 2>&1
powershell -Command "Get-Process | Where-Object {$_.MainWindowTitle -eq 'PCRemoteBot'} | Stop-Process -Force" >nul 2>&1
echo [OK] Bot stopped!

:: ===== REMOVE TASK SCHEDULER =====
echo [*] Removing from Task Scheduler...
schtasks /delete /tn "PCRemoteBot" /f >nul 2>&1
echo [OK] Task removed!

:: ===== REMOVE FROM STARTUP FOLDER =====
echo [*] Removing from startup folder...
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
del /q "%STARTUP%\PCRemoteBot.bat" >nul 2>&1
del /q "%STARTUP%\PCRemoteBot.vbs" >nul 2>&1
del /q "%STARTUP%\PCRemoteBot.exe" >nul 2>&1
echo [OK] Startup entries removed!

:: ===== REMOVE REGISTRY ENTRIES =====
echo [*] Removing registry entries...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "PCRemoteBot" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "PCRemoteBot" /f >nul 2>&1
echo [OK] Registry cleaned!

:: ===== DELETE FILES =====
echo [*] Deleting files...
timeout /t 2 /nobreak >nul
rmdir /s /q "C:\Tools\tracker" >nul 2>&1

if not exist "C:\Tools\tracker" (
    echo [OK] Files deleted!
) else (
    echo [!] Some files could not be deleted
    echo [!] Please delete C:\Tools\tracker manually
)

:: ===== CLEAN C:\TOOLS IF EMPTY =====
for /f %%i in ('dir /b /a "C:\Tools" 2^>nul') do goto TOOLS_NOT_EMPTY
rmdir "C:\Tools" >nul 2>&1
echo [OK] C:\Tools removed (was empty)
:TOOLS_NOT_EMPTY

echo.
echo  ============================================
echo   Uninstalled Successfully!
echo  ============================================
echo.
echo  Removed:
echo  [OK] Bot process stopped
echo  [OK] Task Scheduler entry
echo  [OK] Startup folder entry
echo  [OK] Registry entries
echo  [OK] All files in C:\Tools\tracker
echo.
pause