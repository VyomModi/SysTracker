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

:: ===== CONFIRM =====
set /p CONFIRM="Are you sure you want to uninstall? (Y/N): "
if /i "%CONFIRM%" neq "Y" (
    echo [*] Uninstall cancelled!
    pause
    exit
)

echo.

:: ===== ASK EXE NAME =====
set EXE_NAME=PCRemoteBot
set /p EXE_NAME="Enter exe name (default: PCRemoteBot): "
if "%EXE_NAME%"=="" set EXE_NAME=PCRemoteBot

echo.
echo [*] Uninstalling: %EXE_NAME%
echo.

:: ===== STOP ALL PROCESSES =====
echo [*] Stopping processes...
taskkill /f /im "%EXE_NAME%.exe"  >nul 2>&1
taskkill /f /im "tracker.exe"     >nul 2>&1
taskkill /f /im "PCRemoteBot.exe" >nul 2>&1
powershell -Command "Stop-Process -Name '%EXE_NAME%' -Force -ErrorAction SilentlyContinue" >nul 2>&1
timeout /t 2 /nobreak >nul
echo [OK] Processes stopped!

:: ===== REMOVE TASK SCHEDULER =====
echo [*] Removing Task Scheduler...
schtasks /delete /tn "%EXE_NAME%"  /f >nul 2>&1
schtasks /delete /tn "PCRemoteBot" /f >nul 2>&1
schtasks /delete /tn "tracker"     /f >nul 2>&1
echo [OK] Task Scheduler removed!

:: ===== REMOVE STARTUP FOLDER =====
echo [*] Removing startup entries...
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
del /q "%STARTUP%\%EXE_NAME%.bat"  >nul 2>&1
del /q "%STARTUP%\%EXE_NAME%.exe"  >nul 2>&1
del /q "%STARTUP%\PCRemoteBot.bat" >nul 2>&1
del /q "%STARTUP%\PCRemoteBot.exe" >nul 2>&1
del /q "%STARTUP%\PCRemoteBot.vbs" >nul 2>&1
del /q "%STARTUP%\tracker.bat"     >nul 2>&1
del /q "%STARTUP%\tracker.exe"     >nul 2>&1
del /q "%STARTUP%\tracker.vbs"     >nul 2>&1
echo [OK] Startup entries removed!

:: ===== REMOVE REGISTRY =====
echo [*] Cleaning registry...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "%EXE_NAME%"  /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "PCRemoteBot" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "tracker"     /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "%EXE_NAME%"  /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "PCRemoteBot" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "tracker"     /f >nul 2>&1
echo [OK] Registry cleaned!

:: ===== DELETE FILES =====
echo [*] Deleting files...
timeout /t 1 /nobreak >nul
rmdir /s /q "C:\Tools\tracker" >nul 2>&1

if not exist "C:\Tools\tracker" (
    echo [OK] C:\Tools\tracker deleted!
) else (
    echo [!] Could not delete C:\Tools\tracker
    echo [!] Please delete manually
)

:: ===== CLEAN C:\TOOLS IF EMPTY =====
for /f %%i in ('dir /b /a "C:\Tools" 2^>nul') do goto SKIP
rmdir "C:\Tools" >nul 2>&1
echo [OK] C:\Tools removed
:SKIP

:: ===== CLEAR ICON CACHE =====
echo [*] Clearing icon cache...
ie4uinit.exe -show >nul 2>&1
echo [OK] Icon cache cleared!

echo.
echo  ============================================
echo   Uninstalled Successfully!
echo  ============================================
echo.
echo  Removed:
echo  [OK] %EXE_NAME%.exe process
echo  [OK] Task Scheduler entry
echo  [OK] Startup folder entries
echo  [OK] Registry entries (HKCU + HKLM)
echo  [OK] All files in C:\Tools\tracker
echo.
pause