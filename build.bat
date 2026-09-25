@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>&1 && set PY=py || set PY=python

echo [1/3] Установка PyInstaller...
%PY% -m pip install -r requirements-build.txt
if errorlevel 1 (
  echo Ошибка pip. Установите Python с python.org и повторите.
  pause
  exit /b 1
)

echo [2/3] Сборка одного exe...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name "SiPak" --paths . --hidden-import models --hidden-import siq_io --hidden-import dialogs --hidden-import constants --hidden-import app --collect-all PIL main.py
if errorlevel 1 (
  echo Ошибка сборки.
  pause
  exit /b 1
)

echo [3/3] Готово!
echo.
echo Файл: %cd%\dist\SiPak.exe
echo Скопируйте SiPak.exe куда угодно — Python на другом ПК не нужен.
echo.
pause
