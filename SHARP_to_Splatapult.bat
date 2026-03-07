@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  SHARP to Splatapult - Right-click "Send To" integration
REM  Converts a JPEG/PNG image to 3D Gaussian Splats using SHARP
REM  and opens the result in Splatapult viewer.
REM ============================================================

set "SCRIPT_DIR=%~dp0"
set "CONDA_ENV=sharp"
set "SPLATAPULT_EXE=%SCRIPT_DIR%splatapult\splatapult.exe"

REM --- Auto-detect conda base (Anaconda or Miniconda, user or local install) ---
set "CONDA_BASE="
for %%B in (
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\miniconda3"
    "%USERPROFILE%\Anaconda3"
    "%USERPROFILE%\Miniconda3"
    "%LOCALAPPDATA%\anaconda3"
    "%LOCALAPPDATA%\miniconda3"
    "%LOCALAPPDATA%\Anaconda3"
    "%LOCALAPPDATA%\Miniconda3"
) do (
    if exist "%%~B\condabin\conda.bat" (
        set "CONDA_BASE=%%~B"
        goto :found_conda
    )
)
echo ERROR: Could not find Anaconda/Miniconda. Run Setup_NewPC.bat first.
pause
exit /b 1
:found_conda

REM --- Validate input ---
if "%~1"=="" (
    echo ERROR: No input file provided.
    echo Usage: Drag and drop an image onto this script, or use "Send To".
    pause
    exit /b 1
)

set "INPUT_FILE=%~1"
set "INPUT_NAME=%~n1"
set "INPUT_EXT=%~x1"

REM --- Check file extension ---
set "VALID_EXT=0"
if /i "%INPUT_EXT%"==".jpg"  set "VALID_EXT=1"
if /i "%INPUT_EXT%"==".jpeg" set "VALID_EXT=1"
if /i "%INPUT_EXT%"==".png"  set "VALID_EXT=1"

if "%VALID_EXT%"=="0" (
    echo ERROR: Unsupported file type "%INPUT_EXT%".
    echo Supported formats: .jpg, .jpeg, .png
    pause
    exit /b 1
)

REM --- Set output location next to the input image ---
REM Strip trailing backslash from %~dp1 to avoid quote-escaping in CLI args
set "OUTPUT_DIR=%~dp1"
set "OUTPUT_DIR=%OUTPUT_DIR:~0,-1%"
set "OUTPUT_PLY=%OUTPUT_DIR%\%INPUT_NAME%.ply"

echo ============================================================
echo  SHARP to Splatapult
echo ============================================================
echo.
echo Input image : %INPUT_FILE%
echo Output file : %OUTPUT_PLY%
echo.

REM --- Activate conda environment and run SHARP ---
echo [1/3] Running SHARP prediction (this may take a moment on first run)...
echo.

call "%CONDA_BASE%\condabin\conda.bat" activate %CONDA_ENV%
if errorlevel 1 (
    echo ERROR: Failed to activate conda environment "%CONDA_ENV%".
    echo Make sure you have run: conda create -n sharp python=3.13
    echo Then: cd ml-sharp ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

sharp predict -i "%INPUT_FILE%" -o "%OUTPUT_DIR%" --device cuda
if errorlevel 1 (
    echo.
    echo ERROR: SHARP prediction failed.
    pause
    exit /b 1
)

REM --- Verify output PLY exists ---
if not exist "%OUTPUT_PLY%" (
    echo ERROR: Expected output file not found: %OUTPUT_PLY%
    echo Checking output directory contents:
    dir "%OUTPUT_DIR%\*.ply" 2>nul
    pause
    exit /b 1
)

REM --- Clean PLY: strip Apple metadata + fix coordinate system for splatapult ---
echo [2/3] Cleaning PLY and converting coordinate system...
set "CLEAN_PLY=%OUTPUT_DIR%\%INPUT_NAME%_clean.ply"
python -c "from plyfile import PlyData,PlyElement; import numpy as np; d=PlyData.read(r'%OUTPUT_PLY%'); v=d['vertex'].data.copy(); v['y']=-v['y']; v['z']=-v['z']; v['rot_2']=-v['rot_2']; v['rot_3']=-v['rot_3']; PlyData([PlyElement.describe(v,'vertex')],text=False).write(r'%CLEAN_PLY%'); print('Done:',len(v),'gaussians')"
if errorlevel 1 (
    echo WARNING: PLY transform failed, trying to open original...
    set "CLEAN_PLY=%OUTPUT_PLY%"
) else (
    del "%OUTPUT_PLY%"
    move "%CLEAN_PLY%" "%OUTPUT_PLY%" >nul
)

REM --- Convert PLY to SPZ format ---
echo [3/3] Converting PLY to SPZ format...
set "OUTPUT_SPZ=%OUTPUT_DIR%\%INPUT_NAME%.spz"
3dgsconverter -i "%OUTPUT_PLY%" -f spz --force
if exist "%OUTPUT_SPZ%" (
    echo SPZ conversion successful.
    del "%OUTPUT_PLY%"
    set "VIEWER_FILE=%OUTPUT_SPZ%"
) else (
    echo WARNING: SPZ conversion failed, keeping PLY...
    set "VIEWER_FILE=%OUTPUT_PLY%"
)

echo.
echo Opening result in Splatapult viewer...
echo.

REM --- Launch splatapult from its own directory so it finds shaders/data/DLLs ---
set "SPLATAPULT_DIR=%SCRIPT_DIR%splatapult"
start "" /D "%SPLATAPULT_DIR%" "%SPLATAPULT_EXE%" "%VIEWER_FILE%"

echo Done! Splatapult should be opening.
echo The Gaussian splat file is saved at: %VIEWER_FILE%
echo.
timeout /t 5
