@echo off
chcp 65001 > nul
echo ===========================================
echo Capcraft v1.0 Build Script
echo ===========================================
echo.

echo 1. 패키지 설치를 확인합니다...
pip install -r requirements.txt

echo.
echo 2. 기존 빌드 폴더를 정리합니다...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "Capcraft v1.0.spec" del /q "Capcraft v1.0.spec"

echo.
echo 3. PyInstaller를 통해 exe 파일을 빌드합니다...
:: --noconsole 옵션으로 도스창이 뜨지 않게 하고, index.html과 guide.html을 내부에 포함시킵니다.
pyinstaller --noconfirm --onedir --windowed --add-data "index.html;." --add-data "guide.html;." --name "Capcraft v1.0" main.py

echo.
echo 4. 빌드 완료! dist\Capcraft v1.0 폴더를 확인하세요.
pause
