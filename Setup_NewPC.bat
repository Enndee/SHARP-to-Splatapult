@echo off
setlocal EnableDelayedExpansion

echo =====================================================
echo  SHARP to Splatapult  --  New PC Setup
echo =====================================================
echo.
echo This script will:
echo   1. Verify conda and git are installed
echo   2. Create the 'sharp' conda environment (Python 3.13)
echo   3. Install ml-sharp (Apple's 3D Gaussian Splatting model)
echo   4. Install PyTorch with CUDA 12.8 (for NVIDIA GPUs)
echo   5. Create a Send To shortcut for easy use
echo.
echo Press any key to continue, or Ctrl+C to cancel.
pause >nul

REM ── Check conda ───────────────────────────────────────────────────────────
echo.
echo [1/5] Checking for conda...
where conda >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: conda not found in PATH.
    echo.
    echo Please install Anaconda or Miniconda first:
    echo   https://www.anaconda.com/download
    echo.
    echo After installing, open a fresh terminal and run this script again.
    pause
    exit /b 1
)
echo       OK - conda found.

REM ── Check git ─────────────────────────────────────────────────────────────
echo.
echo [2/5] Checking for git...
where git >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: git not found in PATH.
    echo.
    echo Please install Git for Windows:
    echo   https://git-scm.com/download/win
    echo.
    echo After installing, open a fresh terminal and run this script again.
    pause
    exit /b 1
)
echo       OK - git found.

REM ── Create conda environment ───────────────────────────────────────────────
echo.
echo [3/5] Creating conda environment 'sharp' with Python 3.13...
conda env list | findstr /C:"sharp" >nul 2>&1
if not errorlevel 1 (
    echo       Environment 'sharp' already exists -- skipping creation.
    goto :install_sharp
)
conda create -n sharp python=3.13 -y
if errorlevel 1 (
    echo ERROR: Failed to create conda environment.
    pause
    exit /b 1
)

:install_sharp
REM ── Install ml-sharp ──────────────────────────────────────────────────────
echo.
echo [4/5] Installing ml-sharp from GitHub (this may take several minutes)...
conda run -n sharp pip install "git+https://github.com/apple/ml-sharp.git"
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install ml-sharp.
    echo        Make sure git is installed and you have internet access.
    pause
    exit /b 1
)

echo.
echo       Installing PyTorch with CUDA 12.8 support...
echo       (Required for NVIDIA RTX 20/30/40/50 series GPUs)
conda run -n sharp pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
if errorlevel 1 (
    echo.
    echo WARNING: PyTorch CUDA install failed.
    echo          You can still use CPU mode (much slower).
)

echo.
echo       Installing 3dgsconverter (PLY to SPZ conversion)...
conda run -n sharp pip install "git+https://github.com/francescofugazzi/3dgsconverter.git"
if errorlevel 1 (
    echo WARNING: 3dgsconverter install failed. SPZ conversion will be skipped.
)

REM ── Create Send To shortcut ───────────────────────────────────────────────
echo.
echo [5/5] Creating Send To shortcut...
set "EXE_PATH=%~dp0SHARP_to_Splatapult.exe"
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$lnk = $ws.CreateShortcut([Environment]::GetFolderPath('SendTo') + '\SHARP to Splatapult.lnk'); " ^
    "$lnk.TargetPath = '%EXE_PATH:\=\\%'; " ^
    "$lnk.Save()"
if errorlevel 1 (
    echo       WARNING: Could not create Send To shortcut automatically.
    echo       You can create it manually by right-clicking the .exe and
    echo       choosing 'Send to -^> Desktop (create shortcut)', then
    echo       moving that shortcut to:
    echo       %%APPDATA%%\Microsoft\Windows\SendTo\
) else (
    echo       OK - shortcut created.
    echo       Right-click any JPEG/PNG -^> Send To -^> SHARP to Splatapult
)

echo.
echo =====================================================
echo  Setup complete!
echo.
echo  FIRST RUN NOTE:
echo    On the first conversion, SHARP will download its model
echo    weights (~500MB) from Apple's servers automatically.
echo    This only happens once.
echo =====================================================
pause
