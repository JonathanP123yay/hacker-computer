@echo off
setlocal

cd /d "%~dp0"

echo Checking for PyInstaller...
py -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller is not installed. Installing it...
    py -m pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller.
        exit /b 1
    )
)

if not exist "face_landmarker.task" (
    echo ERROR: face_landmarker.task was not found next to build.bat.
    exit /b 1
)

set "HAND_DATA="
if exist "hand_landmarker.task" (
    set "HAND_DATA=--add-data hand_landmarker.task;."
) else (
    echo WARNING: hand_landmarker.task was not found. Gestures will be disabled.
)

echo Cleaning previous build files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "eye_tracker.spec" del /q "eye_tracker.spec"

echo Building eye_tracker.exe...
py -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --console ^
    --name eye_tracker ^
    --add-data "face_landmarker.task;." ^
    %HAND_DATA% ^
    --collect-all mediapipe ^
    main.py

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo.
echo Build complete:
echo dist\eye_tracker.exe
exit /b 0
