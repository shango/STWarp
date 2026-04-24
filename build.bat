@echo off
rem -------------------------------------------------------------------------
rem STWarp - Windows build script
rem
rem Expected location: C:\Users\shann\Documents\STWarp
rem
rem Usage:
rem   build.bat           -> build dist\STWarp.exe
rem   build.bat clean     -> wipe build/dist/__pycache__, then build
rem   build.bat run       -> build, then launch dist\STWarp.exe
rem   build.bat dev       -> run from source, no freeze
rem -------------------------------------------------------------------------

rem Always work from the folder this .bat lives in.
cd /d "%~dp0"

rem Dispatch all real work to :main, then ALWAYS pause, no matter what.
call :main %*
set "EXITCODE=%ERRORLEVEL%"
echo.
echo ==== Done ^(exit %EXITCODE%^) ====
pause
exit /b %EXITCODE%


:main
set "MODE=%~1"
if "%MODE%"=="" set "MODE=build"
echo [info] Mode: %MODE%
echo [info] Working dir: %CD%

rem ---- Pick a Python launcher (flat, no nested if) ----
set "PYLAUNCH="
where py >nul 2>nul && set "PYLAUNCH=py -3"
if not defined PYLAUNCH where python >nul 2>nul && set "PYLAUNCH=python"
if not defined PYLAUNCH (
    echo [ERROR] Python 3.10+ not found on PATH.
    echo         Install from https://www.python.org/downloads/ and retry.
    exit /b 1
)
echo [info] Python launcher: %PYLAUNCH%
%PYLAUNCH% --version
if errorlevel 1 (
    echo [ERROR] Python launcher is present but failed to run.
    exit /b 1
)

rem ---- Clean mode: wipe artefacts, then fall through to build ----
if /I "%MODE%"=="clean" call :do_clean
if /I "%MODE%"=="clean" set "MODE=build"

rem ---- Ensure .venv exists ----
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment .venv ...
    %PYLAUNCH% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv.
        exit /b 1
    )
) else (
    echo [1/3] Reusing existing .venv
)

set "VPY=.venv\Scripts\python.exe"

rem ---- Dev mode: install runtime deps and launch from source ----
if /I "%MODE%"=="dev" (
    echo [2/3] Installing runtime requirements ...
    "%VPY%" -m pip install --upgrade pip
    "%VPY%" -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
    echo [3/3] Launching from source ...
    "%VPY%" -m stwarp
    exit /b %ERRORLEVEL%
)

rem ---- Build mode ----
echo [2/3] Installing build requirements ...
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install -r requirements-build.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    exit /b 1
)

echo [3/3] Running PyInstaller ...
"%VPY%" -m PyInstaller --noconfirm --clean STWarp.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller failed.
    exit /b 1
)

if not exist "dist\STWarp.exe" (
    echo [ERROR] PyInstaller finished but dist\STWarp.exe is missing.
    exit /b 1
)

echo.
echo Build complete: %CD%\dist\STWarp.exe

if /I "%MODE%"=="run" (
    echo Launching STWarp ...
    start "" "dist\STWarp.exe"
)
exit /b 0


:do_clean
echo [clean] Removing build\ dist\ __pycache__ ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for /d /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"
exit /b 0
