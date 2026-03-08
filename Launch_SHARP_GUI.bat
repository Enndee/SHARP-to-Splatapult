@echo off
REM ============================================================
REM  SHARP -> Splatapult  |  GUI launcher (Send To / drag-drop)
REM  Place a SHORTCUT to this file in your Send To folder:
REM    Win+R  ->  shell:sendto
REM ============================================================

REM Locate conda (same search order as the Python script)
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
    "%APPDATA%\anaconda3"
    "%APPDATA%\miniconda3"
    "%ProgramData%\anaconda3"
    "%ProgramData%\miniconda3"
    "%ProgramData%\Anaconda3"
    "%ProgramData%\Miniconda3"
    "C:\anaconda3"
    "C:\miniconda3"
    "D:\anaconda3"
    "D:\miniconda3"
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
REM Activate the sharp environment and launch the Python GUI
call "%CONDA_BASE%\condabin\conda.bat" activate sharp
python "%~dp0SHARP_to_Splatapult.py" %1
