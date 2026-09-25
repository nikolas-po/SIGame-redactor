# -*- coding: utf-8 -*-
"""Настройки: важное из .env, остальное по умолчанию."""

from env_load import load_env, get as env_get

load_env()


def _reload_env_values():
    global UPDATE_GITHUB_REPO, SIGAME_ONLINE_URL
    UPDATE_GITHUB_REPO = env_get("UPDATE_GITHUB_REPO", "").strip()
    SIGAME_ONLINE_URL = env_get(
        "SIGAME_ONLINE_URL", "https://sigame.vladimirkhil.com/"
    ).strip()


UPDATE_GITHUB_REPO = ""
SIGAME_ONLINE_URL = "https://sigame.vladimirkhil.com/"
_reload_env_values()

APP_NAME = "СиПак"
APP_NAME_FULL = "СиПак — редактор пакетов SIGame"
APP_TAGLINE = "Собери пакет. Запусти игру."
APP_EXE_NAME = "SiPak"
APP_VERSION = "1.1.0"

NS = "https://github.com/VladimirKhil/SI/blob/master/assets/ygpackage3.1.xsd"
DEFAULT_PACKAGE_NAME = "Мой набор вопросов"
DEFAULT_LANGUAGE = "ru-RU"
DEFAULT_RESTRICTION = "16+"
DEFAULT_DIFFICULTY = 5
DEFAULT_PRICES = [100, 200, 300, 400, 500]
MAX_NAME_LEN = 200
MAX_TEXT_LEN = 5000
MIN_PRICE = 1
MAX_PRICE = 999999

UPDATE_ASSET_WIN = "SiPak.exe"
UPDATE_ASSET_LINUX = "SiPak"
UPDATE_ASSET_MAC = "SiPak"
GITHUB_API_URL = "https://api.github.com/repos/{repo}/releases/latest"

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
MEDIA_FOLDERS = {"image": "Images", "voice": "Audio", "video": "Video"}
MEDIA_EXTS = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    "voice": [".mp3", ".wav", ".ogg", ".m4a", ".aac"],
    "video": [".mp4", ".webm", ".mkv", ".avi", ".mov"],
}


# Простые объяснения типов для новичка
TYPE_HELP = {
    "simple": (
        "Обычный вопрос — как в классической «Своей игре».\n"
        "Игрок выбирает тему и цену, читает (или слышит) вопрос, отвечает.\n"
        "Верно — плюс очки, неверно — минус."
    ),
    "auction": (
        "Аукцион (вопрос со ставкой).\n"
        "Сначала игроки торгуются: кто готов рискнуть большей суммой.\n"
        "Победитель торгов отвечает на вопрос. Можно поставить «ва-банк»."
    ),
    "cat": (
        "Кот в мешке.\n"
        "Игрок открыл клетку, но вопрос (и часто тема) — сюрприз.\n"
        "Обычно кот «отдаётся» другому игроку — тот и отвечает."
    ),
    "bagcat": (
        "Кот в мешке с полными настройками.\n"
        "Можно задать секретную тему и стоимость,\n"
        "можно ли оставить вопрос себе и когда игроки узнают тему."
    ),
    "sponsored": (
        "Без риска (×2).\n"
        "Отвечает только тот, кто открыл клетку.\n"
        "За верный ответ — обычно двойная цена; за ошибку очки часто не снимают."
    ),
}

# Короткий «лор» игры
SIGAME_LORE = (
    "Что такое «Своя игра»\n\n"
    "Это викторина вроде Jeopardy: на табло темы и цены.\n"
    "Игроки по очереди выбирают клетку, слышат или читают вопрос, отвечают.\n\n"
    "Словарь\n\n"
    "• Пакет (.siq) — файл со всеми раундами и вопросами.\n"
    "• Раунд — часть игры (например «1 курс», «Финал»).\n"
    "• Тема — столбец на табло («Кино», «История»).\n"
    "• Цена — сколько очков стоит клетка (100, 200…).\n"
    "• Ведущий — человек за компьютером, запускает вопросы и засчитывает ответы.\n"
    "• Игроки — отвечают, набирают очки.\n"
    "• Финал — последний раунд: обычно все делают ставки и отвечают на один вопрос.\n\n"
    "Типы клеток\n\n"
    "• Обычный — стандартный вопрос.\n"
    "• Аукцион — сначала ставки, потом ответ.\n"
    "• Кот в мешке — сюрприз, часто отдают другому.\n"
    "• Без риска — отвечает открывший, за успех ×2.\n\n"
    "Как играют онлайн\n\n"
    "1. Ведущий создаёт комнату на сайте SIGame.\n"
    "2. Загружает ваш файл .siq.\n"
    "3. Шлёт друзьям ссылку или PIN (можно QR из СиПак).\n"
    "4. Когда все зашли — старт.\n"
)
