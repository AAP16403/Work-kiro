@echo off
setlocal enableextensions enabledelayedexpansion

rem Build a distributable package (exe + zip) using PyInstaller.
rem Usage: double-click or run from a terminal:  build_exe.bat

cd /d "%~dp0"

set "APP_NAME=Blocksoft"
set "SPEC_FILE=Blocksoft.spec"
set "VENV_DIR=.venv"
set "RELEASE_DIR=release"
set "KEEP_STAGING=0"

echo === Privacy Screen Guard: Build EXE ===
echo Working dir: %CD%

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
set "LOG_PATH=%RELEASE_DIR%\\build_%TS%.log"
echo Log: %LOG_PATH%
echo. > "%LOG_PATH%"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>nul || (
    echo ERROR: Python not found. Install Python 3.x and try again.
    exit /b 1
  )
  set "PY=python"
)

if not exist "%VENV_DIR%\\Scripts\\python.exe" (
  echo Creating venv: %VENV_DIR%
  %PY% -m venv "%VENV_DIR%" >> "%LOG_PATH%" 2>&1 || (
    echo ERROR: Failed to create venv. See %LOG_PATH%
    exit /b 1
  )
)

call "%VENV_DIR%\\Scripts\\activate.bat" >> "%LOG_PATH%" 2>&1 || (
  echo ERROR: Failed to activate venv. See %LOG_PATH%
  exit /b 1
)

echo Upgrading pip...
python -m pip install -U pip wheel >> "%LOG_PATH%" 2>&1 || (
  echo ERROR: pip upgrade failed. See %LOG_PATH%
  exit /b 1
)

echo Installing build deps...
if exist requirements.txt (
  python -m pip install -r requirements.txt >> "%LOG_PATH%" 2>&1 || (
    echo ERROR: requirements install failed. See %LOG_PATH%
    exit /b 1
  )
)
python -m pip install pyinstaller pystray pywin32 >> "%LOG_PATH%" 2>&1 || (
  echo ERROR: build deps install failed. See %LOG_PATH%
  exit /b 1
)

echo Cleaning old build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

if not exist "icon.ico" (
  echo WARNING: icon.ico not found. EXE will use default icon.
)

echo Building with PyInstaller spec: %SPEC_FILE%
python -m PyInstaller "%SPEC_FILE%" --noconfirm --clean >> "%LOG_PATH%" 2>&1 || (
  echo ERROR: PyInstaller build failed. See %LOG_PATH%
  exit /b 1
)

set "OUT_DIR=%RELEASE_DIR%\\%APP_NAME%_%TS%"
if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
mkdir "%OUT_DIR%" || exit /b 1

echo Staging release folder: %OUT_DIR%
if exist "dist\\%APP_NAME%.exe" (
  copy /y "dist\\%APP_NAME%.exe" "%OUT_DIR%\\" >nul || exit /b 1
) else if exist "dist\\%APP_NAME%\\%APP_NAME%.exe" (
  xcopy /e /i /y "dist\\%APP_NAME%" "%OUT_DIR%\\%APP_NAME%" >nul || exit /b 1
) else (
  echo ERROR: Could not find built exe under dist\\
  dir dist
  exit /b 1
)

if exist "icon.ico" copy /y "icon.ico" "%OUT_DIR%\\" >nul
if exist "README.md" copy /y "README.md" "%OUT_DIR%\\" >nul
if exist "psg_config.json" copy /y "psg_config.json" "%OUT_DIR%\\psg_config.example.json" >nul

set "ZIP_PATH=%RELEASE_DIR%\\%APP_NAME%_%TS%.zip"
if exist "%ZIP_PATH%" del /q "%ZIP_PATH%"

echo Creating zip: %ZIP_PATH%
powershell -NoProfile -Command "Compress-Archive -Path '%OUT_DIR%\\*' -DestinationPath '%ZIP_PATH%' -Force" >> "%LOG_PATH%" 2>&1 || (
  echo ERROR: Failed to create zip. See %LOG_PATH%
  exit /b 1
)

echo Cleaning temporary build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

if "%KEEP_STAGING%"=="0" (
  rmdir /s /q "%OUT_DIR%" >nul 2>nul
  echo Staging folder removed (KEEP_STAGING=0)
)

echo.
echo Done.
if "%KEEP_STAGING%"=="1" echo Release folder: %OUT_DIR%
echo Zip file:       %ZIP_PATH%
echo.
pause
