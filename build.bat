@echo off
title Building EXE...
color 0A

echo.
echo  ============================================
echo   Building tracker.exe - Please Wait...
echo  ============================================
echo.

set ALARM=
if exist "alarm.wav" (
    set ALARM=--add-data "alarm.wav;."
)

pyinstaller --onefile --noconsole --clean ^
%ALARM% ^
--collect-all pyautogui ^
--collect-all cv2 ^
--hidden-import=pythoncom ^
--hidden-import=pywintypes ^
--hidden-import=win32api ^
--hidden-import=win32con ^
--hidden-import=win32gui ^
--hidden-import=PIL.Image ^
--hidden-import=PIL.ImageGrab ^
tracker.py

if exist "dist\tracker.exe" (
    echo.
    echo  [OK] Build Successful!
    for %%A in ("dist\tracker.exe") do echo  [OK] Size: %%~zA bytes
) else (
    echo.
    echo  [FAIL] Build Failed!
)

rmdir /s /q build >nul 2>&1
del /q tracker.spec >nul 2>&1

echo.
pause