# -*- coding: utf-8 -*-
"""Настройки приложения СиПак."""

from version import __version__

APP_NAME = "СиПак"
APP_NAME_FULL = "СиПак — редактор пакетов SIGame"
APP_TAGLINE = "Собери пакет. Запусти игру."
APP_EXE_NAME = "SiPak"

# Сайт игры
SIGAME_ONLINE_URL = "https://sigame.vladimirkhil.com/"

# Обновления: "user/repo" на GitHub Releases, пусто = выкл
UPDATE_GITHUB_REPO = ""
UPDATE_ASSET_WIN = "SiPak.exe"
UPDATE_ASSET_LINUX = "SiPak"
UPDATE_ASSET_MAC = "SiPak"

# Типы вопросов SIGame
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

MEDIA_EXTS = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    "voice": [".mp3", ".wav", ".ogg", ".m4a"],
    "video": [".mp4", ".webm", ".avi", ".mkv"],
}

MEDIA_FOLDERS = {
    "image": "Images",
    "voice": "Audio",
    "video": "Video",
}
