@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1 && set PY=py || set PY=python
echo [1/2] Зависимости...
%PY% -m pip install -r requirements-build.txt
echo [2/2] Сборка SiPak.exe...
%PY% -m PyInstaller --noconfirm main.spec
echo.
echo Готово: dist\SiPak.exe
pause
