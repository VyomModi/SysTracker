@echo off
title PC Remote Bot - Universal Installer
color 0A

:: ===== AUTO REQUEST ADMIN =====
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Requesting Administrator...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit
)

echo.
echo  ============================================
echo   PC Remote Bot - Universal Installer
echo  ============================================
echo.

:: ===== CREATE FOLDER =====
echo [*] Creating folder...
if not exist "C:\Tools\tracker" mkdir "C:\Tools\tracker"
echo [OK] C:\Tools\tracker created

:: ===== COPY FILES =====
echo [*] Copying files...
copy "%~dp0tracker.exe" "C:\Tools\tracker\tracker.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] tracker.exe not found next to install.bat!
    echo        Make sure tracker.exe is in same folder as install.bat
    pause
    exit
)
echo [OK] tracker.exe copied!

if exist "%~dp0alarm.wav" (
    copy "%~dp0alarm.wav" "C:\Tools\tracker\alarm.wav" >nul 2>&1
    echo [OK] alarm.wav copied!
) else (
    echo [!] alarm.wav not found - skipping
)

:: ===== CLEAN OLD ENTRIES =====
echo [*] Cleaning old entries...
schtasks /delete /tn "PCRemoteBot" /f >nul 2>&1
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PCRemoteBot.bat" >nul 2>&1
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PCRemoteBot.vbs" >nul 2>&1
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PCRemoteBot.exe" >nul 2>&1
echo [OK] Cleaned!

:: ===== CREATE POWERSHELL LAUNCHER =====
echo [*] Creating launcher...
(
echo # PC Remote Bot Launcher
echo # Waits for internet then starts bot
echo $host.ui.RawUI.WindowTitle = "PCRemoteBot"
echo while ^($true^) {
echo     try {
echo         $test = Test-NetConnection -ComputerName "api.telegram.org" -Port 443 -WarningAction SilentlyContinue -InformationLevel Quiet
echo         if ^($test^) { break }
echo     } catch {}
echo     Start-Sleep -Seconds 5
echo }
echo Start-Process "C:\Tools\tracker\tracker.exe" -WorkingDirectory "C:\Tools\tracker"
) > "C:\Tools\tracker\launcher.ps1"
echo [OK] Launcher created!

:: ===== SETUP AUTOSTART =====
echo [*] Setting up autostart...

:: Method 1: Task Scheduler (best - no terminal)
set XMLFILE=%TEMP%\PCRemoteBot.xml
(
echo ^<?xml version="1.0" encoding="UTF-16"?^>
echo ^<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^>
echo   ^<RegistrationInfo^>
echo     ^<Description^>PC Remote Bot - Auto Start^</Description^>
echo   ^</RegistrationInfo^>
echo   ^<Triggers^>
echo     ^<LogonTrigger^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<Delay^>PT10S^</Delay^>
echo     ^</LogonTrigger^>
echo   ^</Triggers^>
echo   ^<Principals^>
echo     ^<Principal id="Author"^>
echo       ^<LogonType^>InteractiveToken^</LogonType^>
echo       ^<RunLevel^>HighestAvailable^</RunLevel^>
echo     ^</Principal^>
echo   ^</Principals^>
echo   ^<Settings^>
echo     ^<MultipleInstancesPolicy^>IgnoreNew^</MultipleInstancesPolicy^>
echo     ^<DisallowStartIfOnBatteries^>false^</DisallowStartIfOnBatteries^>
echo     ^<StopIfGoingOnBatteries^>false^</StopIfGoingOnBatteries^>
echo     ^<ExecutionTimeLimit^>PT0S^</ExecutionTimeLimit^>
echo     ^<Priority^>7^</Priority^>
echo     ^<RestartOnFailure^>
echo       ^<Interval^>PT1M^</Interval^>
echo       ^<Count^>10^</Count^>
echo     ^</RestartOnFailure^>
echo   ^</Settings^>
echo   ^<Actions Context="Author"^>
echo     ^<Exec^>
echo       ^<Command^>powershell^</Command^>
echo       ^<Arguments^>-WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Tools\tracker\launcher.ps1"^</Arguments^>
echo       ^<WorkingDirectory^>C:\Tools\tracker^</WorkingDirectory^>
echo     ^</Exec^>
echo   ^</Actions^>
echo ^</Task^>
) > "%XMLFILE%"

schtasks /create /tn "PCRemoteBot" /xml "%XMLFILE%" /f >nul 2>&1
del "%XMLFILE%" >nul 2>&1

if %errorlevel% == 0 (
    echo [OK] Task Scheduler - autostart set!
    set METHOD=Task Scheduler
) else (
    echo [!] Task Scheduler failed - using startup folder...

    :: Method 2: Startup folder (fallback)
    set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
    (
    echo @echo off
    echo powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Tools\tracker\launcher.ps1"
    ) > "%STARTUP%\PCRemoteBot.bat"

    if exist "%STARTUP%\PCRemoteBot.bat" (
        echo [OK] Startup folder - autostart set!
        set METHOD=Startup Folder
    ) else (
        echo [FAIL] Both methods failed!
        set METHOD=FAILED
    )
)

:: ===== ALLOW POWERSHELL SCRIPTS =====
echo [*] Allowing PowerShell scripts...
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force" >nul 2>&1
echo [OK] Done!

:: ===== START NOW =====
echo [*] Starting bot now...
powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Tools\tracker\launcher.ps1"
echo [OK] Bot starting - waiting for internet...

echo.
echo  ============================================
echo   Installation Complete!
echo  ============================================
echo.
echo  Autostart Method : %METHOD%
echo  Bot Location     : C:\Tools\tracker\tracker.exe
echo  Launcher         : C:\Tools\tracker\launcher.ps1
echo.
echo  Bot will:
echo  - Auto start on every login
echo  - Wait for internet before connecting
echo  - Restart automatically if crashes
echo  - Run silently in background
echo.
echo  Check Telegram for online message!
echo  ============================================
echo.
pause