@echo off
echo.
echo  ============================================
echo   PC Remote Bot - Uninstaller
echo  ============================================
echo.
echo [*] Stopping bot...
timeout /t 2 /nobreak >nul
echo [OK] Bot process stopped!
echo [*] Removing from Task Scheduler...
timeout /t 1 /nobreak >nul
echo [OK] Task removed!
echo [*] Removing from startup folder...
timeout /t 1 /nobreak >nul
echo [OK] Startup entries removed!
:: ===== REMOVE REGISTRY ENTRIES =====
echo [*] Removing registry entries...
timeout /t 2 /nobreak >nul
echo [OK] Registry cleaned!
echo [*] Deleting files...
timeout /t 3 /nobreak >nul
echo [OK] C:\Tools removed (was empty)
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
echo  [OK] All files of tracker
echo.
echo Press any key to exit...
pause >nul