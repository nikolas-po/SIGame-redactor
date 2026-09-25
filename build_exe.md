# Сборка через PyInstaller

## 1. Установка

```bash
cd siq_project
python -m pip install -r requirements-build.txt
```

Windows: если `python` не находится — `py -m pip install -r requirements-build.txt`

## 2. Сборка (один файл, без консоли)

Из папки `siq_project`:

**Windows:**
```bash
pyinstaller --noconfirm --clean --onefile --windowed --name "SIGameEditor" main.py
```

**Linux / macOS:**
```bash
pyinstaller --noconfirm --clean --onefile --windowed --name "SIGameEditor" main.py
```

Готовый файл:
- Windows: `dist/SIGameEditor.exe`
- Linux/macOS: `dist/SIGameEditor`

## 3. Если ругается на модули

Явно добавить путь к проекту:

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name "SIGameEditor" ^
  --paths . ^
  --hidden-import models ^
  --hidden-import siq_io ^
  --hidden-import dialogs ^
  --hidden-import constants ^
  --hidden-import app ^
  main.py
```

(Linux/macOS: `^` замените на `\` в конце строк или одной строкой.)

## 4. Опционально: иконка

Положите `icon.ico` (Windows) рядом и:

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name "SIGameEditor" --icon=icon.ico main.py
```

## 5. Замечания

- Антивирус иногда ругается на onefile-сборки PyInstaller — это часто ложное срабатывание.
- На другом ПК с Windows обычно достаточно просто `.exe`, Python ставить не нужно.
- `tkinter` должен быть в том Python, которым собираете (официальный установщик Python с python.org — галочка tcl/tk).
