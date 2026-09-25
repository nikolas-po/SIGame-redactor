# -*- coding: utf-8 -*-

SIGAME_ONLINE_URL = "https://sigame.vladimirkhil.com/"
NS = "https://github.com/VladimirKhil/SI/blob/master/assets/ygpackage3.1.xsd"

QUESTION_TYPES = [
    ("simple", "Обычный"),
    ("auction", "Аукцион (ставки)"),
    ("cat", "Кот в мешке"),
    ("bagcat", "Кот в мешке (полный)"),
    ("sponsored", "Без риска (x2)"),
]

ATOM_TYPES = [
    ("text", "Текст на экране"),
    ("say", "Реплика ведущего"),
    ("image", "Фото / картинка"),
    ("voice", "Звук"),
    ("video", "Видео"),
]

MEDIA_FOLDERS = {
    "image": "Images",
    "voice": "Audio",
    "video": "Video",
}

MEDIA_EXTS = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    "voice": [".mp3", ".wav", ".ogg", ".m4a", ".aac"],
    "video": [".mp4", ".webm", ".mkv", ".avi", ".mov"],
}

MAX_NAME_LEN = 200
MAX_TEXT_LEN = 5000
MIN_PRICE = 1
MAX_PRICE = 999999
DEFAULT_PRICES = [100, 200, 300, 400, 500]


# Обновления: владелец/репозиторий на GitHub (Releases)
# Пример: "username/siq-editor" — тогда проверяются
# https://github.com/username/siq-editor/releases
# Пустая строка = проверка только через git pull (если есть .git)
# Пример: "username/sipak". Пусто = без автообновления при запуске.
UPDATE_GITHUB_REPO = ""
# Имя asset в релизе для Windows (exe), Linux, macOS
UPDATE_ASSET_WIN = "SiPak.exe"
UPDATE_ASSET_LINUX = "SiPak"
UPDATE_ASSET_MAC = "SiPak"
