#!/bin/sh
cd "$(dirname "$0")"
python3 -m pip install -r requirements-build.txt
python3 -m PyInstaller --noconfirm main.spec
echo "Готово: dist/SiPak"
