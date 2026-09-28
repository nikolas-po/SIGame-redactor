#!/bin/sh
cd "$(dirname "$0")"
python -m Cpip install -r requirements-build.txt
python -m pyinstaller --noconfirm --clean --onefile --windowed --name "SIGameEditor" --paths src --hidden-import models --hidden-import siq_io --hidden-import dialogs --hidden-import constants --hidden-import app --icon "assets/icon.ico" src/main.py
echo "Готово: dist/SiPak"
