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
    win.geometry("520x480")
    win.transient(parent)
    txt = tk.Text(win, wrap=tk.WORD, font=("", 12), padx=14, pady=12)
    txt.pack(fill=tk.BOTH, expand=True)
    txt.insert(
        "1.0",
        "СиПак — редактор вопросов для «Своей игры»\n\n"
        "Три шага\n\n"
        "1. Слева нажмите «Раунд», потом «Тему», потом «Вопрос».\n"
        "   Так собирается табло: раунды → темы → цены.\n\n"
        "2. Справа впишите текст вопроса и правильный ответ.\n"
        "   Нажмите «Сохранить вопрос».\n"
        "   Фото, звук, аукцион и «кот» — по желанию, ниже на форме.\n\n"
        "3. «Сохранить» — получится файл .siq.\n"
        "   «Играть» — откроется сайт SIGame, загрузите этот файл.\n"
        "   «Играть» — откроется сайт и QR на SIGame для команд.\n\n"
        "Игра для класса (команды, ответ вслух)\n"
        "• Команда = один вход в комнату.\n"
        "• Жмут «Ответить» → говорят ответ вслух → ведущий судит.\n"
        "• Если нет «Устная игра» — всё равно можно: главное кнопка и голос.\n"
        "• Подробнее: меню «Игра» → «Шпаргалка ведущего».\n\n"
        "Не обязательно заполнять всё сразу.\n"
        "Можно открыть готовый .siq и только подправить вопросы.\n\n"
        "Если что-то неясно — меню «Помощь» → «Справка».",
    )
    txt.config(state=tk.DISABLED)
    ttk.Button(win, text="Понятно, закрыть", command=win.destroy).pack(pady=10)




def show_play_qr(parent, pack_path="", site_url=None):
    """QR только на сайт SIGame (не на комнату)."""
    import threading
    from qr_local import make_qr_png

    url0 = (site_url or SIGAME_ONLINE_URL or "").strip()
    if not url0:
        url0 = "https://sigame.vladimirkhil.com/"

    win = tk.Toplevel(parent)
    win.title("QR — сайт SIGame")
    win.geometry("420x520")
    win.transient(parent)

    ttk.Label(
        win,
        text="Команды сканируют код и открывают сайт SIGame.",
        font=("", 11),
        wraplength=380,
    ).pack(anchor="w", padx=14, pady=(12, 4))

    if pack_path:
        ttk.Label(
            win,
            text="Пакет для ведущего:\n%s" % pack_path,
            wraplength=380,
            foreground="#444",
            justify=tk.LEFT,
        ).pack(anchor="w", padx=14, pady=4)

    ttk.Label(win, text=url0, foreground="#0d47a1", wraplength=380).pack(
        anchor="w", padx=14, pady=2
    )

    status_lbl = ttk.Label(win, text="Создаю QR…")
    status_lbl.pack(anchor="w", padx=14, pady=4)
    img_label = ttk.Label(win)
    img_label.pack(pady=10)
    state = {"photo": None}

    def finish_ok(path):
        photo = None
        err = ""
        # 1) tk.PhotoImage — PNG/PPM/GIF
        try:
            photo = tk.PhotoImage(file=path)
            # уменьшим, если слишком большой
            try:
                w, h = photo.width(), photo.height()
                if w > 300 or h > 300:
                    factor = max(1, max(w, h) // 280)
                    if factor > 1:
                        photo = photo.subsample(factor, factor)
            except Exception:
                pass
        except Exception as e1:
            err = str(e1)
            # 2) Pillow
            try:
                from PIL import Image, ImageTk
                im = Image.open(path)
                im.thumbnail((280, 280))
                photo = ImageTk.PhotoImage(im)
            except Exception as e2:
                err = "%s / %s" % (e1, e2)
        if photo is not None:
            state["photo"] = photo
            img_label.configure(image=state["photo"], text="")
            status_lbl.config(text="Готово — покажите командам")
        else:
            img_label.configure(
                text="QR сохранён, но картинка не открылась.\n%s\n%s" % (path, err)
            )
            status_lbl.config(text="Файл есть — откройте его вручную")

    def finish_fail(err):
        status_lbl.config(text="Ошибка QR")
        messagebox.showerror(
            "QR",
            "Не удалось создать QR.\n%s\n\npip install qrcode pillow" % err,
            parent=win,
        )

    def worker():
        try:
            out_path = os.path.join(user_data_dir(), "qr_sigame_site.png")
            result = make_qr_png(url0, out_path)
            win.after(0, lambda: finish_ok(result))
        except Exception as e:
            msg = str(e)
            win.after(0, lambda m=msg: finish_fail(m))

    bf = ttk.Frame(win)
    bf.pack(fill=tk.X, padx=14, pady=10)
    ttk.Button(bf, text="Открыть сайт", command=lambda: webbrowser.open(url0)).pack(
        side=tk.LEFT, padx=4
    )
    ttk.Button(bf, text="Закрыть", command=win.destroy).pack(side=tk.RIGHT, padx=4)

    threading.Thread(target=worker, daemon=True).start()


def make_room_qr(parent, status_callback=None):
    """QR на компьютере. Ссылка + опционально PIN."""
    import threading
    from qr_local import make_qr_png

    win = tk.Toplevel(parent)
    win.title("QR-код комнаты")
    win.geometry("460x580")
    win.transient(parent)

    ttk.Label(
        win,
        text="1. Создайте комнату на сайте SIGame\n"
        "2. Скопируйте ссылку для игроков\n"
        "3. Если есть PIN — вставьте ниже\n"
        "4. «Сделать QR» (всё на этом ПК, без интернета)",
        justify=tk.LEFT,
    ).pack(anchor="w", padx=12, pady=8)

    ttk.Label(win, text="Ссылка на комнату:").pack(anchor="w", padx=12)
    url_var = tk.StringVar()
    ent = ttk.Entry(win, textvariable=url_var, width=54)
    ent.pack(padx=12, fill=tk.X)
    ent.focus_set()

    ttk.Label(win, text="PIN-код (необязательно):").pack(anchor="w", padx=12, pady=(8, 0))
    pin_var = tk.StringVar()
    ttk.Entry(win, textvariable=pin_var, width=20).pack(anchor="w", padx=12)

    ttk.Label(
        win,
        text="SIGame часто принимает вход по ссылке ИЛИ по PIN отдельно.\n"
        "Мы добавим pin в URL (на всякий случай) и подпишем код под QR.",
        foreground="#555",
        wraplength=420,
        justify=tk.LEFT,
    ).pack(anchor="w", padx=12, pady=6)

    status_lbl = ttk.Label(win, text="", foreground="#333")
    status_lbl.pack(anchor="w", padx=12, pady=2)

    img_label = ttk.Label(win)
    img_label.pack(pady=6)
    path_var = tk.StringVar(value="")
    ttk.Label(win, textvariable=path_var, wraplength=420).pack(padx=12)
    pin_hint = ttk.Label(win, text="", font=("", 12, "bold"), foreground="#0d47a1")
    pin_hint.pack(pady=4)

    state = {"busy": False, "photo": None}

    def set_status(msg):
        status_lbl.config(text=msg)

    def build_qr_payload(url, pin):
        """Ссылка для QR: пробуем вшить pin в query; текст под QR — сам PIN."""
        url = (url or "").strip()
        pin = "".join(c for c in (pin or "").strip() if c.isalnum())
        if not pin:
            return url, ""
        # не дублируем, если pin уже в ссылке
        low = url.lower()
        if "pin=" + pin.lower() in low or "password=" + pin.lower() in low:
            return url, pin
        sep = "&" if ("?" in url) else "?"
        # распространённые имена параметра; клиент SIGame может игнорировать —
        # тогда поможет подпись под QR
        enriched = url + sep + "pin=" + urllib.parse.quote(pin)
        return enriched, pin

    def show_image(path):
        if path.lower().endswith(".svg"):
            img_label.configure(
                image="",
                text="QR сохранён как SVG:\n" + path,
            )
            return
        try:
            from PIL import Image, ImageTk

            im = Image.open(path)
            im.thumbnail((260, 260))
            photo = ImageTk.PhotoImage(im)
            state["photo"] = photo
            img_label.configure(image=photo, text="")
        except Exception:
            img_label.configure(image="", text="QR сохранён:\n" + path)

    def finish_ok(out_path, pin):
        state["busy"] = False
        btn_gen.config(state=tk.NORMAL)
        set_status("Готово.")
        path_var.set(out_path)
        show_image(out_path)
        if pin:
            pin_hint.config(text="PIN для входа: %s" % pin)
        else:
            pin_hint.config(text="")
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
            "Не удалось создать QR.\n\n%s\n\n"
            "Установите:\n  pip install qrcode pillow" % err,
            parent=win,
        )

    def worker(url, pin):
        try:
            payload, pin_clean = build_qr_payload(url, pin)
            out_dir = user_data_dir()
            out_path = os.path.join(out_dir, "qr_komnata.png")
            result = make_qr_png(payload, out_path)
            # рядом текстовая шпаргалка
            try:
                tip = os.path.join(out_dir, "qr_komnata.txt")
                with open(tip, "w", encoding="utf-8") as f:
                    f.write("Ссылка: %s\n" % payload)
                    if pin_clean:
                        f.write("PIN: %s\n" % pin_clean)
                        f.write(
                            "\nЕсли сайт не подставил PIN сам — введите его вручную.\n"
                        )
            except Exception:
                pass
            win.after(0, lambda: finish_ok(result, pin_clean))
        except Exception as e:
            err_msg = str(e)
            win.after(0, lambda m=err_msg: finish_fail(m))

    def generate():
        if state["busy"]:
            return
        url = (url_var.get() or "").strip()
        pin = (pin_var.get() or "").strip()
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
        set_status("Создаю QR…")
        img_label.configure(image="", text="")
        path_var.set("")
        pin_hint.config(text="")
        threading.Thread(target=worker, args=(url, pin), daemon=True).start()

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
        "КЛАСС / НЕСКОЛЬКО КОМАНД, ОТВЕТ ВСЛУХ\n"
        "• Каждая команда — один игрок в комнате (ник «Команда 1»…)\n"
        "• Один телефон или ноутбук на команду\n"
        "• В правилах комнаты: «Сообщать ведущему ответы заранее» — вкл\n"
        "• Фальстарты — лучше вкл (не жать до конца вопроса)\n"
        "• Пункта «Устная игра» может не быть — не страшно\n"
        "• Игроки ЖМУТ «Ответить», ответ ГОВОРЯТ ВСЛУХ\n"
        "• Текст в поле можно не писать — судите по голосу\n"
        "• Вы жмёте верно / неверно\n\n"
        "Что сказать классу (30 сек)\n"
        "«Открываем вопрос. Кто знает — жмёт Ответить.\n"
        " Кому дали слово — говорит вслух. Я скажу верно или нет.\n"
        " Ошибся — могут отвечать другие. Без кнопки не кричим.»\n\n"
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
        "Первый раз здесь?\n\nДа — покажем 3 простых шага.\nНет — сразу к редактору.",
        parent=parent,
    ):
        open_guide()


def check_for_updates(parent, project_dir=None):
    """Проверка GitHub Releases; скачивание и установка exe."""
    import tkinter as tk
    from tkinter import ttk, messagebox
    import webbrowser
    import updater

    win = tk.Toplevel(parent)
    win.title("Обновления СиПак")
    win.geometry("520x460")
    win.transient(parent)

    ttk.Label(win, text="Текущая версия: %s" % __version__, font=("", 11, "bold")).pack(
        anchor="w", padx=12, pady=8
    )
    status = tk.Text(win, height=16, wrap=tk.WORD, font=("", 10))
    status.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

    def log(msg):
        status.insert(tk.END, msg + "\n")
        status.see(tk.END)
        win.update_idletasks()

    state = {"info": None}

    def do_check():
        status.delete("1.0", tk.END)
        log("Проверка обновлений…")
        repo = updater.get_configured_repo()
        if not repo:
            log("Автообновление не подключено при сборке.")
            log("Программа работает как обычно.")
            log("")
            log("Разработчику: в src/constants.py укажите")
            log('  BUILTIN_UPDATE_REPO = "логин/репозиторий"')
            log("и соберите exe снова. Либо рядом с SiPak.exe файл")
            log("update_repo.txt с одной строкой: логин/репозиторий")
            return
        log("Репозиторий: %s" % repo)
        info = updater.check_github_release(repo)
        state["info"] = info
        if not info:
            log("Пустой ответ.")
            return
        if info.get("message"):
            log(info["message"])
        elif info.get("error"):
            log("Ошибка: " + str(info["error"]))
        if info.get("up_to_date") and not info.get("error"):
            log("Всё актуально.")
        elif not info.get("up_to_date") and info.get("download_url"):
            log("Файл: %s" % (info.get("asset_name") or ""))
            log("Можно нажать «Скачать и установить».")
        if info.get("html_url") and (info.get("error") or not info.get("up_to_date")):
            log("Страница: %s" % info["html_url"])

    def do_install():
        info = state.get("info") or {}
        if info.get("up_to_date") and not info.get("download_url"):
            messagebox.showinfo("Обновления", "Уже последняя версия или нечего ставить.", parent=win)
            return
        url = info.get("download_url") or ""
        if not url:
            messagebox.showinfo(
                "Нет файла",
                info.get("message")
                or "В релизе нет SiPak.exe.\nОткройте страницу релиза и прикрепите exe.",
                parent=win,
            )
            if info.get("html_url"):
                webbrowser.open(info["html_url"])
            return
        if not messagebox.askyesno(
            "Установить",
            "Скачать и установить версию %s?\n\n%s"
            % (info.get("version"), info.get("asset_name") or url[:80]),
            parent=win,
        ):
            return
        log("Скачивание…")
        ok, msg = updater.install_exe_update(url)
        log(msg)
        if ok:
            if messagebox.askyesno("Готово", msg + "\n\nЗакрыть программу сейчас?", parent=win):
                try:
                    parent.destroy()
                except Exception:
                    pass
        else:
            messagebox.showerror("Ошибка", msg, parent=win)

    def open_page():
        info = state.get("info") or {}
        url = info.get("html_url") or ""
        if not url:
            repo = updater.get_configured_repo()
            url = ("https://github.com/%s/releases" % repo) if repo else "https://github.com"
        webbrowser.open(url)

    bf = ttk.Frame(win)
    bf.pack(fill=tk.X, pady=8, padx=12)
    ttk.Button(bf, text="Проверить", command=do_check).pack(side=tk.LEFT, padx=4)
    ttk.Button(bf, text="Скачать и установить", command=do_install).pack(side=tk.LEFT, padx=4)
    ttk.Button(bf, text="Открыть релизы", command=open_page).pack(side=tk.LEFT, padx=4)
    ttk.Button(bf, text="Закрыть", command=win.destroy).pack(side=tk.RIGHT, padx=4)
    do_check()


def startup_auto_update(parent):
    """Тихая проверка релиза exe при запуске. Без репо / без сети — молча выходим."""
    import threading
    from tkinter import messagebox
    import updater
    try:
        from env_load import load_env
        load_env()
        from constants import _reload_env_values
        _reload_env_values()
    except Exception:
        pass
    import updater as _upd
    repo = _upd.get_configured_repo()
    if not repo:
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


def show_sigame_lore(parent):
    """Что такое Своя игра — простыми словами."""
    from constants import SIGAME_LORE

    win = tk.Toplevel(parent)
    win.title("Что такое «Своя игра»")
    win.geometry("540x560")
    win.transient(parent)
    txt = tk.Text(win, wrap=tk.WORD, font=("", 12), padx=14, pady=12)
    txt.pack(fill=tk.BOTH, expand=True)
    txt.insert("1.0", SIGAME_LORE)
    txt.config(state=tk.DISABLED)
    ttk.Button(win, text="Закрыть", command=win.destroy).pack(pady=8)