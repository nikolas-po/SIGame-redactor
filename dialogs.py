# -*- coding: utf-8 -*-

import os
import sys
import webbrowser
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox

from constants import SIGAME_ONLINE_URL


def show_beginner_guide(parent):
    win = tk.Toplevel(parent)
    win.title("Как начать")
    win.geometry("560x520")
    win.transient(parent)
    txt = tk.Text(win, wrap=tk.WORD, font=("", 11), padx=12, pady=12)
    txt.pack(fill=tk.BOTH, expand=True)
    txt.insert(
        "1.0",
        "ЧТО ЭТО\n"
        "Вы собираете набор вопросов (пакет). Потом открываете его "
        "в игре «Своя игра» на сайте и играете с друзьями.\n\n"
        "ТРИ СЛОВА\n"
        "• Раунд — часть игры\n"
        "• Тема — столбец на табло\n"
        "• Вопрос — текст и ответ\n\n"
        "ПОШАГОВО\n"
        "1. «+ Раунд» → название → ОК\n"
        "2. «+ Тема» → например «Деньги»\n"
        "3. «+ Вопрос»\n"
        "4. Слева выберите вопрос\n"
        "5. Справа введите текст и ответ\n"
        "6. «Применить изменения»\n"
        "7. «Сохранить» → файл .siq\n"
        "8. «Играть на сайте» → загрузить пакет\n\n"
        "ДРУЗЬЯ В КОМНАТУ\n"
        "1. Создайте комнату на сайте, скопируйте ссылку\n"
        "2. «QR комнаты» → вставьте ссылку → «Сделать QR»\n"
        "3. Покажите картинку — вход по камере телефона\n\n"
        "ВО ВРЕМЯ ИГРЫ\n"
        "Кнопка «Подсказки ведущему» — шпаргалка рядом с игрой.\n",
    )
    txt.config(state=tk.DISABLED)
    ttk.Button(win, text="Понятно", command=win.destroy).pack(pady=8)


def make_room_qr(parent, status_callback=None):
    win = tk.Toplevel(parent)
    win.title("QR-код комнаты")
    win.geometry("420x480")
    win.transient(parent)

    ttk.Label(
        win,
        text="1. Создайте комнату на сайте SIGame\n"
        "2. Скопируйте ссылку\n"
        "3. Вставьте сюда и нажмите «Сделать QR»",
        justify=tk.LEFT,
    ).pack(anchor="w", padx=12, pady=8)

    url_var = tk.StringVar()
    ent = ttk.Entry(win, textvariable=url_var, width=50)
    ent.pack(fill=tk.X, padx=12, pady=4)
    ent.focus_set()

    img_label = ttk.Label(win)
    img_label.pack(pady=8)
    path_var = tk.StringVar(value="")
    ttk.Label(win, textvariable=path_var, wraplength=380).pack(padx=12)

    def generate():
        url = url_var.get().strip()
        if not url:
            messagebox.showinfo("Ссылка", "Вставьте ссылку на комнату.", parent=win)
            return
        if len(url) > 2000:
            messagebox.showwarning("Ссылка", "Ссылка слишком длинная.", parent=win)
            return
        if not url.startswith("http"):
            url = "https://" + url
        if " " in url or "\n" in url:
            messagebox.showwarning(
                "Ссылка", "В ссылке есть пробелы — скопируйте только URL.", parent=win
            )
            return

        api = (
            "https://api.qrserver.com/v1/create-qr-code/?size=280x280&data="
            + urllib.parse.quote(url, safe="")
        )
        try:
            out_dir = os.path.dirname(os.path.abspath(__file__))
            out_path = os.path.join(out_dir, "qr_komnata.png")
            req = urllib.request.Request(api, headers={"User-Agent": "SIQEditor/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            if len(data) < 100:
                raise ValueError("пустой ответ")
            with open(out_path, "wb") as f:
                f.write(data)
            path_var.set("Сохранено:\n" + out_path)
            try:
                from PIL import Image, ImageTk
                im = Image.open(out_path)
                photo = ImageTk.PhotoImage(im)
                img_label.configure(image=photo)
                img_label.image = photo
            except Exception:
                img_label.configure(text="QR сохранён\n(откройте qr_komnata.png)")
            if status_callback:
                status_callback("QR готов: qr_komnata.png")
        except Exception as e:
            messagebox.showwarning(
                "Не скачалось",
                "Не удалось скачать QR.\nОткрою страницу в браузере.\n\n%s" % e,
                parent=win,
            )
            webbrowser.open(api)

    def open_folder():
        folder = os.path.dirname(os.path.abspath(__file__))
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                os.system('open "%s"' % folder)
            else:
                os.system('xdg-open "%s"' % folder)
        except Exception as e:
            messagebox.showinfo("Папка", folder + "\n\n" + str(e), parent=win)

    bf = ttk.Frame(win)
    bf.pack(pady=8)
    ttk.Button(bf, text="Сделать QR", command=generate).pack(side=tk.LEFT, padx=4)
    ttk.Button(bf, text="Папка с файлом", command=open_folder).pack(side=tk.LEFT, padx=4)
    ttk.Button(bf, text="Закрыть", command=win.destroy).pack(side=tk.LEFT, padx=4)


def show_host_hints(parent):
    win = tk.Toplevel(parent)
    win.title("Подсказки ведущему")
    win.geometry("480x560")
    try:
        win.attributes("-topmost", True)
    except Exception:
        pass

    txt = tk.Text(win, wrap=tk.WORD, font=("", 11), padx=10, pady=10, bg="#fffef5")
    txt.pack(fill=tk.BOTH, expand=True)
    txt.insert(
        "1.0",
        "ШПАРГАЛКА ВЕДУЩЕГО\n"
        "(можно не закрывать во время игры)\n\n"
        "СТАРТ\n"
        "• Комната на сайте → загрузить .siq\n"
        "• Ссылка или QR игрокам\n"
        "• Дождаться всех → Старт\n\n"
        "ВОПРОС\n"
        "• Кто первый нажал — тот отвечает\n"
        "• Верно: +очки; неверно: −очки\n"
        "• Аукцион: сначала ставки\n"
        "• Кот: отдают другому\n"
        "• Без риска: только открывший, за верный ответ ×2\n\n"
        "ПРОБЛЕМЫ\n"
        "• Микрофон в настройках браузера\n"
        "• Зависло — обновить страницу\n"
        "• Спорный ответ — решает ведущий\n\n"
        "ФИНАЛ\n"
        "• Следите, чтобы все успели поставить\n",
    )
    txt.config(state=tk.DISABLED)
    bot = ttk.Frame(win)
    bot.pack(fill=tk.X, pady=6)
    topmost_var = tk.BooleanVar(value=True)

    def toggle_top():
        try:
            win.attributes("-topmost", topmost_var.get())
        except Exception:
            pass

    ttk.Checkbutton(
        bot, text="Поверх других окон", variable=topmost_var, command=toggle_top
    ).pack(side=tk.LEFT, padx=8)
    ttk.Button(bot, text="Закрыть", command=win.destroy).pack(side=tk.RIGHT, padx=8)


def show_help(parent):
    messagebox.showinfo(
        "Справка",
        "Типы вопросов:\n"
        "• Обычный — кто быстрее нажал\n"
        "• Аукцион — ставки\n"
        "• Кот в мешке — отдают другому\n"
        "• Без риска (×2) — только открывший\n\n"
        "Медиа: «+ Фото» / «+ Звук» / «+ Видео»\n"
        "Потом «Применить» и «Сохранить».\n\n"
        "Форматы: jpg png gif, mp3 wav, mp4 webm",
        parent=parent,
    )


def show_about(parent):
    messagebox.showinfo(
        "О программе",
        "Редактор пакетов SIGame\n\n"
        "Текст, фото, звук, видео\n"
        "Аукцион, кот, финал, без риска\n\n"
        + SIGAME_ONLINE_URL,
        parent=parent,
    )


def soft_welcome(parent, open_guide):
    if messagebox.askyesno(
        "Добро пожаловать",
        "Первый раз?\n\n«Да» — короткая инструкция.\n«Нет» — сразу к работе.",
        parent=parent,
    ):
        open_guide()
