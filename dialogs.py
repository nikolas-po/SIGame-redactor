# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import webbrowser
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox

from constants import SIGAME_ONLINE_URL
from version import __version__
from siq_io import user_data_dir


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
    """QR на компьютере, без интернета. Не блокирует окно."""
    import threading
    from qr_local import make_qr_png

    win = tk.Toplevel(parent)
    win.title("QR-код комнаты")
    win.geometry("440x520")
    win.transient(parent)

    ttk.Label(
        win,
        text="1. На сайте SIGame создайте комнату\n"
        "2. Скопируйте ссылку приглашения (кнопка «ссылка» / «пригласить»)\n"
        "3. Вставьте её сюда → «Сделать QR»\n\n"
        "QR только кодирует ссылку — в комнату пускает сайт SIGame.\n"
        "Если при создании комнаты вы поставили пароль или ПИН —\n"
        "игрокам нужно сказать его отдельно (в QR пароль сам не попадёт).\n"
        "Без пароля достаточно отсканировать QR и ввести ник.",
        justify=tk.LEFT,
    ).pack(anchor="w", padx=12, pady=8)

    url_var = tk.StringVar()
    ent = ttk.Entry(win, textvariable=url_var, width=52)
    ent.pack(padx=12, fill=tk.X)
    ent.focus_set()

    status_lbl = ttk.Label(win, text="", foreground="#333")
    status_lbl.pack(anchor="w", padx=12, pady=4)

    img_label = ttk.Label(win)
    img_label.pack(pady=8)
    path_var = tk.StringVar(value="")
    ttk.Label(win, textvariable=path_var, wraplength=400).pack(padx=12)

    state = {"busy": False, "photo": None}

    def set_status(msg):
        status_lbl.config(text=msg)

    def show_image(path):
        if path.lower().endswith(".svg"):
            img_label.configure(
                image="",
                text="QR сохранён как SVG:\n" + path + "\nОткройте файл двойным кликом.",
            )
            return
        try:
            from PIL import Image, ImageTk

            im = Image.open(path)
            im.thumbnail((280, 280))
            photo = ImageTk.PhotoImage(im)
            state["photo"] = photo
            img_label.configure(image=photo, text="")
        except Exception:
            img_label.configure(
                image="",
                text="QR сохранён.\nОткройте файл:\n" + path,
            )

    def finish_ok(out_path):
        state["busy"] = False
        btn_gen.config(state=tk.NORMAL)
        set_status("Готово — QR на вашем компьютере.")
        path_var.set(out_path)
        show_image(out_path)
        if status_callback:
            try:
                status_callback("QR: " + out_path)
            except Exception:
                pass

    def finish_fail(err):
        state["busy"] = False
        btn_gen.config(state=tk.NORMAL)
        set_status("Ошибка")
        messagebox.showerror(
            "QR",
            "Не удалось создать QR на компьютере.\n\n%s\n\n"
            "Установите:\n  pip install qrcode pillow" % err,
            parent=win,
        )

    def worker(url):
        try:
            out_dir = user_data_dir()
            out_path = os.path.join(out_dir, "qr_komnata.png")
            result = make_qr_png(url, out_path)
            win.after(0, lambda: finish_ok(result))
        except Exception as e:
            win.after(0, lambda: finish_fail(str(e)))

    def generate():
        if state["busy"]:
            return
        url = (url_var.get() or "").strip()
        if not url:
            messagebox.showinfo("QR", "Вставьте ссылку на комнату.", parent=win)
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            messagebox.showinfo(
                "QR",
                "Ссылка должна начинаться с http:// или https://",
                parent=win,
            )
            return
        state["busy"] = True
        btn_gen.config(state=tk.DISABLED)
        set_status("Создаю QR на компьютере…")
        img_label.configure(image="", text="")
        path_var.set("")
        threading.Thread(target=worker, args=(url,), daemon=True).start()

    def open_folder():
        folder = user_data_dir()
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except Exception as e:
            messagebox.showinfo("Папка", folder + "\n\n" + str(e), parent=win)

    bf = ttk.Frame(win)
    bf.pack(pady=8)
    btn_gen = ttk.Button(bf, text="Сделать QR", command=generate)
    btn_gen.pack(side=tk.LEFT, padx=4)
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
        "СиПак — редактор пакетов SIGame\n"
        "Версия %s\n\n"
        "Текст, фото, звук, видео\n"
        "Аукцион, кот, финал, без риска\n\n"
        % __version__
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


def check_for_updates(parent, project_dir=None):
    """Проверка GitHub Releases и/или git; скачивание и установка."""
    import tkinter as tk
    from tkinter import ttk, messagebox
    import updater

    win = tk.Toplevel(parent)
    win.title("Обновления")
    win.geometry("480x420")
    win.transient(parent)

    ttk.Label(win, text="Текущая версия: %s" % __version__, font=("", 11, "bold")).pack(
        anchor="w", padx=12, pady=8
    )
    status = tk.Text(win, height=14, wrap=tk.WORD, font=("", 10))
    status.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

    def log(msg):
        status.insert(tk.END, msg + "\n")
        status.see(tk.END)
        win.update_idletasks()

    state = {"info": None}

    def do_check():
        status.delete("1.0", tk.END)
        log("Проверка…")
        from constants import UPDATE_GITHUB_REPO

        repo = (UPDATE_GITHUB_REPO or "").strip()
        if not repo:
            log("В constants.py не задан UPDATE_GITHUB_REPO (вид: user/repo).")
            log("Пока репозиторий не указан — автопроверка при запуске отключена.")
            log("Пробую git…")
        info = None
        if repo:
            info = updater.check_github_release(repo)
            if info and info.get("error"):
                log("GitHub: " + info["error"])
                info = None
            elif info and info.get("up_to_date"):
                log("GitHub: у вас актуальная версия (%s)." % info.get("version"))
                state["info"] = info
                return
            elif info:
                log("Доступна версия %s (сейчас %s)." % (info.get("version"), __version__))
                if info.get("notes"):
                    log("---")
                    log(info["notes"][:800])
                state["info"] = info
                return

        if project_dir:
            g = updater.check_git_update(project_dir)
            if g and g.get("error"):
                log("Git: " + g["error"])
            elif g and g.get("up_to_date"):
                log("Git: уже последняя ревизия.")
                state["info"] = g
            elif g and not g.get("up_to_date"):
                log("Git: есть новые коммиты на origin (%s → %s)." % (g.get("local"), g.get("remote")))
                state["info"] = g
            else:
                log("Нет .git и не задан GitHub-репозиторий.")
                log("Укажите UPDATE_GITHUB_REPO в constants.py после публикации релизов.")
        else:
            log("Папка проекта не найдена.")

    def do_install():
        info = state.get("info")
        if not info or info.get("up_to_date"):
            messagebox.showinfo("Обновления", "Сначала проверка. Или обновлений нет.", parent=win)
            return
        if info.get("kind") == "git":
            if not messagebox.askyesno("Git pull", "Выполнить git pull --ff-only?", parent=win):
                return
            ok, msg = updater.git_pull(info.get("project_dir") or project_dir)
            log(msg)
            if ok:
                messagebox.showinfo("Готово", "Перезапустите программу.", parent=win)
            else:
                messagebox.showerror("Ошибка", msg, parent=win)
            return

        url = info.get("download_url") or ""
        if not url:
            messagebox.showinfo(
                "Ссылка",
                "Нет файла для скачивания.\nОткройте страницу релиза в браузере.",
                parent=win,
            )
            if info.get("html_url"):
                import webbrowser
                webbrowser.open(info["html_url"])
            return

        if not messagebox.askyesno(
            "Установить",
            "Скачать и установить версию %s?\n\n%s"
            % (info.get("version"), url[:120]),
            parent=win,
        ):
            return
        log("Скачивание…")
        # exe asset vs zipball
        if url.endswith(".exe") or info.get("asset_name", "").endswith(".exe") or "releases/download" in url:
            ok, msg = updater.install_exe_update(url)
        else:
            ok, msg = updater.install_zip_source(url, project_dir or os.path.dirname(__file__))
        log(msg)
        if ok:
            if messagebox.askyesno("Готово", msg + "\n\nЗакрыть программу сейчас?", parent=win):
                parent.destroy()
        else:
            messagebox.showerror("Ошибка", msg, parent=win)

    bf = ttk.Frame(win)
    bf.pack(fill=tk.X, pady=8, padx=12)
    ttk.Button(bf, text="Проверить", command=do_check).pack(side=tk.LEFT, padx=4)
    ttk.Button(bf, text="Скачать и установить", command=do_install).pack(side=tk.LEFT, padx=4)
    ttk.Button(bf, text="Закрыть", command=win.destroy).pack(side=tk.RIGHT, padx=4)
    do_check()

def startup_auto_update(parent):
    """Тихая проверка релиза exe при запуске. Без репо / без сети — молча выходим."""
    import threading
    from tkinter import messagebox
    import updater
    from constants import UPDATE_GITHUB_REPO

    repo = (UPDATE_GITHUB_REPO or "").strip()
    if not repo or "/" not in repo:
        return

    def work():
        try:
            info = updater.check_github_release(repo)
        except Exception:
            return
        if not info or info.get("up_to_date") or info.get("error"):
            return
        ver = info.get("version") or ""
        if ver and ver == updater.get_skipped_version():
            return
        if not info.get("download_url"):
            return

        def ask():
            notes = (info.get("notes") or "").strip()
            msg = (
                "Доступна новая версия СиПак: %s\n"
                "(сейчас %s)\n\n"
                "Обновить программу?\n"
                "Заменятся только файлы приложения. Ваши пакеты .siq не трогаем."
                % (ver, updater.current_version())
            )
            if notes:
                msg += "\n\n" + notes[:400]
            # yes / no — обновить или позже; отдельной кнопки skip нет в messagebox
            if messagebox.askyesno("Обновление СиПак", msg, parent=parent):
                parent.config(cursor="watch")
                parent.update_idletasks()
                ok, text = updater.install_exe_update(info["download_url"])
                parent.config(cursor="")
                if ok:
                    messagebox.showinfo(
                        "Обновление",
                        text + "\n\nЗакройте окно — запустится новая версия.",
                        parent=parent,
                    )
                    try:
                        parent.destroy()
                    except Exception:
                        pass
                else:
                    messagebox.showerror("Обновление", "Не удалось:\n" + text, parent=parent)
            else:
                # предложить пропустить версию
                if messagebox.askyesno(
                    "Пропустить?",
                    "Больше не напоминать про версию %s?" % ver,
                    parent=parent,
                ):
                    updater.set_skipped_version(ver)

        try:
            parent.after(0, ask)
        except Exception:
            pass

    threading.Thread(target=work, daemon=True).start()


