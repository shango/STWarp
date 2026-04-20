@echo off
rem -------------------------------------------------------------------------
rem STMesh — Windows build script
rem
rem Expected location when you run this: C:\Users\shann\Documents\STMesh
rem (You sync the repo here after each commit, then run this file.)
rem
rem What it does:
rem   1. Creates a local .venv if missing
rem   2. Installs/updates build requirements
rem   3. Runs PyInstaller using STMesh.spec
rem   4. Leaves the final executable at dist\STMesh.exe
rem
rem Run options:
rem   build.bat           -> build
rem   build.bat clean     -> wipe build / dist / __pycache__ first, then build
rem   build.bat run       -> build, then launch dist\STMesh.exe
rem   build.bat dev       -> skip build, just launch from source (no venv activate)
rem -------------------------------------------------------------------------
setlocal EnableExtensions EnableDelayedExpansion

rem Always work from the folder this .bat lives in — i.e. the repo root.
pushd "%~dp0"

set "MODE=%~1"
if "%MODE%"=="" set "MODE=build"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYLAUNCH=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYLAUNCH=python"
    ) else (
        echo [ERROR] Python 3.10+ is required but was not found on PATH.
        echo         Install from https://www.python.org/downloads/ and retry.
        popd
        exit /b 1
    )
)

if /I "%MODE%"=="clean" (
    echo [1/4] Cleaning previous build artefacts...
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist
    for /d /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"
    set "MODE=build"
)

if not exist .venv (
    echo [2/4] Creating virtual environment .venv...
    %PYLAUNCH% -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo [2/4] Reusing existing .venv
)

set "VENV_PY=.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [ERROR] .venv appears corrupt (no Scripts\python.exe).
    echo         Delete .venv and run "build.bat clean".
    goto :fail
)

if /I "%MODE%"=="dev" (
    echo [dev] Launching from source (no build)...
    "%VENV_PY%" -m pip install --upgrade pip >nul
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 goto :fail
    "%VENV_PY%" -m stmesh
    goto :done
)

echo [3/4] Installing build requirements...
"%VENV_PY%" -m pip install --upgrade pip >nul
"%VENV_PY%" -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail

echo [4/4] Running PyInstaller...
"%VENV_PY%" -m PyInstaller --noconfirm --clean STMesh.spec
if errorlevel 1 goto :fail

if not exist "dist\STMesh.exe" (
    echo [ERROR] PyInstaller reported success but dist\STMesh.exe is missing.
    goto :fail
)

echo.
echo Build complete: "%CD%\dist\STMesh.exe"

if /I "%MODE%"=="run" (
    echo Launching STMesh...
    start "" "dist\STMesh.exe"
)

:done
popd
endlocal
exit /b 0

:fail
echo.
echo Build FAILED. See messages above.
popd
endlocal
exit /b 1
