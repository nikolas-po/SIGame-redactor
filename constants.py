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
