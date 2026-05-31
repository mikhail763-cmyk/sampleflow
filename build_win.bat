@echo off
setlocal enabledelayedexpansion
title SampleFlow — Windows Build
cd /d "%~dp0"

echo.
echo ============================================================
echo  SampleFlow v2.0  --  Windows Installer Build
echo ============================================================
echo.

:: ── Step 1: check Python ────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo         Install Python 3.11/3.12 from https://python.org
    goto :fail
)
echo [1/4] Python OK

:: ── Step 2: install / upgrade PyInstaller ───────────────────────
echo [2/4] Installing PyInstaller...
python -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 ( echo [ERROR] pip failed & goto :fail )

:: ── Step 3: PyInstaller — build the executable bundle ───────────
echo [3/4] Building executable with PyInstaller...
echo        (first run takes 5-15 min due to librosa/numba)
echo.
python -m PyInstaller SampleFlow.spec --clean --noconfirm
if errorlevel 1 ( echo [ERROR] PyInstaller failed & goto :fail )

if not exist "dist\SampleFlow\SampleFlow.exe" (
    echo [ERROR] dist\SampleFlow\SampleFlow.exe not found after build
    goto :fail
)
echo.
echo [OK] Executable bundle ready: dist\SampleFlow\

:: ── Step 4: Inno Setup — create the installer .exe ─────────────
echo [4/4] Looking for Inno Setup 6...

set ISCC=
for %%P in (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) do (
    if exist %%P set ISCC=%%P
)

if "%ISCC%"=="" (
    echo [SKIP] Inno Setup not installed — создаю ZIP-дистрибутив...
    mkdir "dist\installer" 2>nul
    powershell -NoProfile -Command ^
        "Compress-Archive -Path 'dist\SampleFlow\*' -DestinationPath 'dist\installer\SampleFlow_v2.0_portable.zip' -Force; $s=[math]::Round((Get-Item 'dist\installer\SampleFlow_v2.0_portable.zip').Length/1MB); Write-Host \"ZIP ready: $s MB\""
    echo.
    echo ============================================================
    echo  Портативный ZIP:  dist\installer\SampleFlow_v2.0_portable.zip
    echo  Просто распакуйте и запустите SampleFlow.exe
    echo.
    echo  Для .exe-установщика установите Inno Setup 6 (бесплатно):
    echo  https://jrsoftware.org/isdownload.php
    echo  Затем запустите:  build_win.bat  снова
    echo ============================================================
    goto :ok
)

mkdir "dist\installer" 2>nul
%ISCC% "installer\SampleFlow.iss"
if errorlevel 1 ( echo [ERROR] Inno Setup compilation failed & goto :fail )

echo.
echo ============================================================
echo  Installer ready:  dist\installer\SampleFlow_v2.0_Setup.exe
echo ============================================================

:ok
endlocal
pause
exit /b 0

:fail
echo.
echo [BUILD FAILED] — см. текст ошибки выше
echo.
endlocal
pause
exit /b 1
