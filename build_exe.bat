@echo off
setlocal EnableDelayedExpansion

echo =====================================================
echo  SHARP to Splatapult  --  Build EXE
echo =====================================================
echo.

REM ── Locate the 'sharp' conda environment ─────────────────────────────────
set "SHARP_PY="
for %%B in (
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\miniconda3"
    "%LOCALAPPDATA%\anaconda3"
    "%LOCALAPPDATA%\miniconda3"
) do (
    if exist "%%~B\envs\sharp\python.exe" (
        set "SHARP_PY=%%~B\envs\sharp\python.exe"
        set "SHARP_SCRIPTS=%%~B\envs\sharp\Scripts"
        goto :found_env
    )
)

echo ERROR: Could not find the 'sharp' conda environment.
echo        Run Setup_NewPC.bat first to create it.
pause
exit /b 1

:found_env
echo [1/4] Found sharp env: %SHARP_PY%
echo.

REM ── Install PyInstaller into the sharp env ────────────────────────────────
echo [2/4] Installing PyInstaller...
"%SHARP_PY%" -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo ERROR: pip install pyinstaller failed.
    pause
    exit /b 1
)

REM ── Locate Tcl/Tk libraries (must match the version _tkinter.pyd was built with)
set "CONDA_BASE="
for %%B in (
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\miniconda3"
    "%LOCALAPPDATA%\anaconda3"
    "%LOCALAPPDATA%\miniconda3"
) do (
    if exist "%%~B\envs\sharp\python.exe" (
        set "CONDA_BASE=%%~B"
        goto :found_conda
    )
)
:found_conda
set "TCL_LIBRARY=%CONDA_BASE%\envs\sharp\Library\lib\tcl8.6"
set "TK_LIBRARY=%CONDA_BASE%\envs\sharp\Library\lib\tk8.6"
echo       TCL_LIBRARY=%TCL_LIBRARY%
echo       TK_LIBRARY=%TK_LIBRARY%

REM Put the sharp env's Library\bin FIRST on PATH so PyInstaller picks up the
REM correct tcl86t.dll (8.6.15) rather than the base conda's (8.6.14).
set "PATH=%CONDA_BASE%\envs\sharp\Library\bin;%PATH%"

REM ── Build the exe ─────────────────────────────────────────────────────────
echo.
echo [3/4] Building SHARP_to_Splatapult.exe ...
"%SHARP_SCRIPTS%\pyinstaller.exe" ^
    --onefile ^
    --windowed ^
    --name "SHARP_to_Splatapult" ^
    --hidden-import plyfile ^
    --hidden-import numpy ^
    --collect-all plyfile ^
    --add-data "%TCL_LIBRARY%;tcl" ^
    --add-data "%TK_LIBRARY%;tk" ^
    "SHARP_to_Splatapult.py"

if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

REM ── Assemble distribution folder ──────────────────────────────────────────
echo.
echo [4/4] Assembling dist\ folder...

REM Copy splatapult binaries next to the exe
if not exist "dist\splatapult" mkdir "dist\splatapult"
xcopy /E /I /Y "splatapult\build\Release\*" "dist\splatapult\" >nul

REM Copy the new-PC setup script
copy /Y "Setup_NewPC.bat" "dist\" >nul

REM Write a quick README
(
    echo SHARP to Splatapult
    echo ====================
    echo.
    echo REQUIREMENTS FOR A NEW PC
    echo   1. Windows 11, NVIDIA GPU (RTX 20/30/40/50 series with CUDA)
    echo   2. Anaconda or Miniconda - https://www.anaconda.com/download
    echo   3. Git for Windows      - https://git-scm.com/download/win
    echo.
    echo SETUP (first time only^)
    echo   Run Setup_NewPC.bat  -- installs the SHARP conda environment.
    echo.
    echo USAGE
    echo   - Double-click SHARP_to_Splatapult.exe and use the file picker, OR
    echo   - Right-click any JPEG/PNG -> Send To -> SHARP to Splatapult
    echo     (Setup_NewPC.bat creates the Send To shortcut automatically^)
    echo.
    echo FOLDER STRUCTURE
    echo   SHARP_to_Splatapult.exe   <- launcher
    echo   splatapult\               <- 3D viewer (must stay next to the exe^)
    echo   Setup_NewPC.bat           <- one-time environment installer
) > "dist\README.txt"

echo.
echo =====================================================
echo  Build complete!  Distribution is in:  dist\
echo.
echo  Contents:
dir /b dist
echo.
echo  Zip the entire dist\ folder and copy it to another PC.
echo =====================================================
pause
