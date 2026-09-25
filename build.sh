#!/bin/sh
cd "$(dirname "$0")"
python3 -m pip install -r requirements-build.txt
pyinstaller --noconfirm --clean --onefile --windowed --name "SiPak" \
  --paths . \
  --hidden-import models \
  --hidden-import siq_io \
  --hidden-import dialogs \
  --hidden-import constants \
  --hidden-import app \
  main.py
echo "Готово: dist/SiPak"
