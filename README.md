# СиПак

Редактор пакетов `.siq` для SIGame.

```
SiPak/
├── src/           # исходники Python
├── assets/        # иконки и логотипы
├── build/         # временные файлы PyInstaller
├── dist/          # готовый SiPak.exe
├── main.spec      # настройки сборки
├── requirements.txt
└── .gitignore
```

## Запуск из исходников

```bash
cd SiPak
pip install -r requirements.txt
python src/main.py
```

## Сборка exe

Windows: `build.bat`  
Linux/macOS: `./build.sh`  

Или: `pyinstaller main.spec` → `dist/SiPak.exe`

## Обновления

В `.env` в корне или в `src/constants.py`:

```
UPDATE_GITHUB_REPO=user/repo
```
