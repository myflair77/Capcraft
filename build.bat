@echo off
setlocal
chcp 65001 > nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Create the Python 3.12 environment first: python -m venv .venv
    exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
call npm ci --ignore-scripts --omit=optional
if errorlevel 1 exit /b 1
call npm run vendor
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m unittest discover -s tests
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath dist-dev --workpath build\v1.2.1 Capcraft_v1.2.spec
if errorlevel 1 exit /b 1
echo v1.2.1 development build: dist-dev\Capcraft v1.2.1
echo Existing releases in dist are preserved.
