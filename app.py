# -*- coding: utf-8 -*-
"""Главное окно редактора пакетов SIGame."""

import os
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from constants import (
    SIGAME_ONLINE_URL,
    QUESTION_TYPES,
    MEDIA_FOLDERS,
    MEDIA_EXTS,
    DEFAULT_PRICES,
    MIN_PRICE,
    MAX_PRICE,
    MAX_NAME_LEN,
)
from models import Package, Round, Theme, Question, Atom
from siq_io import save_siq, load_siq, validate_package
import dialogs


class SIQEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SIGame Редактор — текст, фото, звук, видео")
        self.geometry("1200x750")
        self.minsize(960, 620)

        self.pkg = Package()
        self.current_file = None
        self.dirty = False
        self.form_vars = {}
        self.form_widgets = []
        self._listboxes = {}
        self._atom_listbox = None
        self._answer_atom_listbox = None
        self._editing_question = None  # (ri, ti, qi) while form open

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self._new_defaults()
        self._refresh_tree()
        self.after(400, self._soft_welcome)

    def _new_defaults(self):
        self.pkg = Package()
        self.pkg.name = "Экономика и финансы для студентов"
        self.pkg.comments = "Вопросы с медиа"
        self.pkg.date = "23.09.2026"
        self.current_file = None

    def _build_ui(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill=tk.X)
        for text, cmd in [
            ("Как начать?", self.show_beginner_guide),
            ("Справка", self.show_help),
            ("Открыть", self.open_package),
            ("Сохранить", self.save_package),
            ("Новый", self.new_package),
        ]:
            ttk.Button(top, text=text, command=cmd).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="QR комнаты", command=self.make_room_qr).pack(side=tk.RIGHT, padx=3)
        ttk.Button(top, text="Подсказки ведущему", command=self.show_host_hints).pack(side=tk.RIGHT, padx=3)
        ttk.Button(top, text="Играть на сайте", command=self.play_online).pack(side=tk.RIGHT, padx=3)

        main = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        left = ttk.Frame(main, padding=4)
        main.add(left, weight=1)
        ttk.Label(left, text="Структура пакета", font=("", 10, "bold")).pack(anchor="w")

        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, selectmode="browse", show="tree")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        bf = ttk.LabelFrame(left, text="Добавить / порядок", padding=4)
        bf.pack(fill=tk.X, pady=6)
        row1 = ttk.Frame(bf)
        row1.pack(fill=tk.X)
        ttk.Button(row1, text="+ Раунд", command=self.add_round).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(row1, text="+ Тема", command=self.add_theme).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(row1, text="+ Вопрос", command=self.add_question).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        row2 = ttk.Frame(bf)
        row2.pack(fill=tk.X, pady=3)
        ttk.Button(row2, text="Вверх", command=self.move_up).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(row2, text="Вниз", command=self.move_down).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(row2, text="Копия", command=self.duplicate).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(row2, text="Удалить", command=self.delete_selected).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        right = ttk.Frame(main, padding=4)
        main.add(right, weight=2)
        self.editor_title = ttk.Label(right, text="Выберите элемент слева", font=("", 11, "bold"))
        self.editor_title.pack(anchor="w")
        self.hint_label = ttk.Label(right, text="", foreground="#555", wraplength=540)
        self.hint_label.pack(anchor="w", pady=(0, 4))

        canvas = tk.Canvas(right, highlightthickness=0)
        form_scroll = ttk.Scrollbar(right, orient="vertical", command=canvas.yview)
        self.form_frame = ttk.Frame(canvas)
        self.form_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        canvas.configure(yscrollcommand=form_scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas = canvas

        self.status = ttk.Label(self, text="Готово", relief=tk.SUNKEN, anchor="w", padding=3)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        menubar = tk.Menu(self)
        fm = tk.Menu(menubar, tearoff=0)
        fm.add_command(label="Новый", command=self.new_package)
        fm.add_command(label="Открыть", command=self.open_package)
        fm.add_command(label="Сохранить", command=self.save_package)
        fm.add_command(label="Сохранить как", command=self.save_package_as)
        fm.add_separator()
        fm.add_command(label="Играть на сайте", command=self.play_online)
        fm.add_separator()
        fm.add_command(label="Выход", command=self.quit)
        menubar.add_cascade(label="Файл", menu=fm)
        hm = tk.Menu(menubar, tearoff=0)
        hm.add_command(label="Справка", command=self.show_help)
        hm.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Помощь", menu=hm)
        self.config(menu=menubar)

    # ---------- Дерево ----------

    def _refresh_tree(self, select_path=None):
        self.tree.delete(*self.tree.get_children())
        pkg_id = self.tree.insert("", "end", text="  " + self.pkg.name, open=True, tags=("package",))
        for ri, rnd in enumerate(self.pkg.rounds):
            fin = " [ФИНАЛ]" if rnd.is_final else ""
            r_id = self.tree.insert(pkg_id, "end", text="  " + rnd.name + fin, open=True, tags=("round:%d" % ri,))
            for ti, theme in enumerate(rnd.themes):
                t_id = self.tree.insert(
                    r_id, "end",
                    text="  %s (%d)" % (theme.name, len(theme.questions)),
                    open=True, tags=("theme:%d:%d" % (ri, ti),),
                )
                for qi, q in enumerate(theme.questions):
                    media_mark = ""
                    types_in = {a.atype for a in q.atoms + q.answer_atoms}
                    if "image" in types_in:
                        media_mark += "Ф"
                    if "voice" in types_in:
                        media_mark += "З"
                    if "video" in types_in:
                        media_mark += "В"
                    if media_mark:
                        media_mark = "[" + media_mark + "] "
                    short = ""
                    for a in q.atoms:
                        if a.atype in ("text", "say") and a.value:
                            short = a.value[:35]
                            break
                    if not short:
                        short = next((a.value for a in q.atoms if a.value), "— пусто —")
                        short = short[:35]
                    type_mark = {"auction": "А", "cat": "К", "bagcat": "К", "sponsored": "2x"}.get(q.qtype, "")
                    prefix = ("[%s] " % type_mark) if type_mark else ""
                    self.tree.insert(
                        t_id, "end",
                        text="  %s%s%d · %s" % (prefix, media_mark, q.price, short),
                        tags=("question:%d:%d:%d" % (ri, ti, qi),),
                    )
        n_q = sum(len(t.questions) for r in self.pkg.rounds for t in r.themes)
        n_m = len(self.pkg.media_files)
        self.status.config(
            text="Раундов: %d | Тем: %d | Вопросов: %d | Медиафайлов: %d" % (
                len(self.pkg.rounds),
                sum(len(r.themes) for r in self.pkg.rounds),
                n_q, n_m,
            )
        )
        if select_path:
            self._select_path(select_path)

    def _select_path(self, path):
        def walk(parent, target):
            for item in self.tree.get_children(parent):
                tags = self.tree.item(item, "tags")
                if tags and tags[0] == target:
                    self.tree.selection_set(item)
                    self.tree.see(item)
                    return True
                if walk(item, target):
                    return True
            return False
        tag = "package" if path[0] == "package" else path[0] + ":" + ":".join(str(x) for x in path[1:])
        walk("", tag)

    def _get_path(self):
        sel = self.tree.selection()
        if not sel:
            return None
        tags = self.tree.item(sel[0], "tags")
        if not tags:
            return None
        tag = tags[0]
        if tag == "package":
            return ("package",)
        parts = tag.split(":")
        return (parts[0],) + tuple(int(x) for x in parts[1:])

    # ---------- Форма ----------

    def _clear_form(self):
        for w in self.form_widgets:
            w.destroy()
        self.form_widgets.clear()
        self.form_vars.clear()
        self._listboxes.clear()
        self._atom_listbox = None
        self._answer_atom_listbox = None
        self._editing_question = None

    def _field(self, label, key, value="", multiline=False, hint=""):
        row = ttk.Frame(self.form_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=20).pack(side=tk.LEFT, anchor="n")
        if multiline:
            txt = tk.Text(row, height=3, width=48, wrap=tk.WORD, font=("", 10))
            txt.insert("1.0", value)
            txt.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.form_vars[key] = txt
        else:
            var = tk.StringVar(value=str(value))
            ttk.Entry(row, textvariable=var, width=48).pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.form_vars[key] = var
        self.form_widgets.append(row)
        if hint:
            h = ttk.Label(self.form_frame, text=hint, foreground="#666", font=("", 8))
            h.pack(anchor="w", padx=(150, 0))
            self.form_widgets.append(h)

    def _combo(self, label, key, value, choices):
        row = ttk.Frame(self.form_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
        var = tk.StringVar(value=value)
        ttk.Combobox(row, textvariable=var, values=choices, width=40, state="readonly").pack(side=tk.LEFT)
        self.form_vars[key] = var
        self.form_widgets.append(row)

    def _check(self, label, key, value):
        row = ttk.Frame(self.form_frame)
        row.pack(fill=tk.X, pady=2)
        var = tk.BooleanVar(value=bool(value))
        ttk.Checkbutton(row, text=label, variable=var).pack(side=tk.LEFT)
        self.form_vars[key] = var
        self.form_widgets.append(row)

    def _get(self, key):
        v = self.form_vars.get(key)
        if isinstance(v, tk.Text):
            return v.get("1.0", "end").strip()
        if isinstance(v, tk.StringVar):
            return v.get().strip()
        if isinstance(v, tk.BooleanVar):
            return v.get()
        return ""

    def _get_list(self, key):
        lb = self._listboxes.get(key)
        return [lb.get(i) for i in range(lb.size())] if lb else []

    def _list_editor(self, title, key, items, placeholder="…"):
        frame = ttk.LabelFrame(self.form_frame, text=title, padding=4)
        frame.pack(fill=tk.X, pady=4)
        self.form_widgets.append(frame)
        lb = tk.Listbox(frame, height=3, font=("", 10))
        lb.pack(fill=tk.X)
        for it in items:
            lb.insert(tk.END, it)
        self._listboxes[key] = lb
        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X)

        def add():
            val = simpledialog.askstring("Добавить", placeholder)
            if val is not None:
                lb.insert(tk.END, val.strip())

        def edit():
            sel = lb.curselection()
            if not sel:
                return
            val = simpledialog.askstring("Изменить", placeholder, initialvalue=lb.get(sel[0]))
            if val is not None:
                lb.delete(sel[0])
                lb.insert(sel[0], val.strip())

        def remove():
            sel = lb.curselection()
            if sel:
                lb.delete(sel[0])

        def move(d):
            sel = lb.curselection()
            if not sel:
                return
            i, j = sel[0], sel[0] + d
            if 0 <= j < lb.size():
                t = lb.get(i)
                lb.delete(i)
                lb.insert(j, t)
                lb.selection_set(j)

        for txt, cmd in [("+", add), ("Изм.", edit), ("−", remove), ("↑", lambda: move(-1)), ("↓", lambda: move(1))]:
            ttk.Button(btns, text=txt, width=4, command=cmd).pack(side=tk.LEFT, padx=1)

    def _atom_editor(self, title, atoms, is_answer=False):
        """Редактор списка атомов (сценария)."""
        frame = ttk.LabelFrame(self.form_frame, text=title, padding=4)
        frame.pack(fill=tk.X, pady=6)
        self.form_widgets.append(frame)

        lb = tk.Listbox(frame, height=5, font=("", 10))
        lb.pack(fill=tk.X)
        for a in atoms:
            lb.insert(tk.END, a.display())
        if is_answer:
            self._answer_atom_listbox = lb
            self._answer_atoms_ref = atoms
        else:
            self._atom_listbox = lb
            self._atoms_ref = atoms

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X, pady=2)

        def refresh():
            lb.delete(0, tk.END)
            for a in atoms:
                lb.insert(tk.END, a.display())

        def add_text():
            val = simpledialog.askstring("Текст", "Текст на экране:")
            if val is not None:
                atoms.append(Atom("text", val.strip()))
                refresh()

        def add_say():
            val = simpledialog.askstring("Реплика", "Что говорит ведущий:")
            if val is not None:
                atoms.append(Atom("say", val.strip()))
                refresh()

        def add_media(atype):
            labels = {"image": "Фото", "voice": "Звук", "video": "Видео"}
            exts = MEDIA_EXTS[atype]
            path = filedialog.askopenfilename(
                title="Выберите файл — " + labels[atype],
                filetypes=[
                    (labels[atype], " ".join("*" + e for e in exts)),
                    ("Все файлы", "*.*"),
                ],
            )
            if not path:
                return
            fname = os.path.basename(path)
            # уникальное имя при конфликте
            base, ext = os.path.splitext(fname)
            n = 1
            while fname in self.pkg.media_files and self.pkg.media_files[fname] != path:
                fname = "%s_%d%s" % (base, n, ext)
                n += 1
            self.pkg.media_files[fname] = path
            atoms.append(Atom(atype, fname))
            atoms[-1].local_path = path
            refresh()
            self.status.config(text="Добавлен файл: " + fname)

        def edit_sel():
            sel = lb.curselection()
            if not sel:
                return
            i = sel[0]
            atom = atoms[i]
            if atom.atype in ("text", "say"):
                val = simpledialog.askstring("Изменить", "Текст:", initialvalue=atom.value)
                if val is not None:
                    atom.value = val.strip()
                    refresh()
            else:
                # заменить файл
                path = filedialog.askopenfilename(title="Заменить файл")
                if path:
                    fname = os.path.basename(path)
                    self.pkg.media_files[fname] = path
                    atom.value = fname
                    atom.local_path = path
                    refresh()

        def remove():
            sel = lb.curselection()
            if sel:
                atoms.pop(sel[0])
                refresh()

        def move(d):
            sel = lb.curselection()
            if not sel:
                return
            i, j = sel[0], sel[0] + d
            if 0 <= j < len(atoms):
                atoms[i], atoms[j] = atoms[j], atoms[i]
                refresh()
                lb.selection_set(j)

        ttk.Button(btns, text="+ Текст", command=add_text).pack(side=tk.LEFT, padx=1)
        ttk.Button(btns, text="+ Реплика", command=add_say).pack(side=tk.LEFT, padx=1)
        ttk.Button(btns, text="+ Фото", command=lambda: add_media("image")).pack(side=tk.LEFT, padx=1)
        ttk.Button(btns, text="+ Звук", command=lambda: add_media("voice")).pack(side=tk.LEFT, padx=1)
        ttk.Button(btns, text="+ Видео", command=lambda: add_media("video")).pack(side=tk.LEFT, padx=1)

        btns2 = ttk.Frame(frame)
        btns2.pack(fill=tk.X)
        ttk.Button(btns2, text="Изменить", command=edit_sel).pack(side=tk.LEFT, padx=1)
        ttk.Button(btns2, text="Удалить", command=remove).pack(side=tk.LEFT, padx=1)
        ttk.Button(btns2, text="↑", width=3, command=lambda: move(-1)).pack(side=tk.LEFT, padx=1)
        ttk.Button(btns2, text="↓", width=3, command=lambda: move(1)).pack(side=tk.LEFT, padx=1)

    def on_select(self, event=None):
        path = self._get_path()
        self._clear_form()
        if not path:
            self.editor_title.config(text="Выберите элемент слева")
            self.hint_label.config(text="")
            return

        if path[0] == "package":
            self.editor_title.config(text="Свойства пакета")
            self.hint_label.config(text="Название и данные, которые видят игроки.")
            self._field("Название", "name", self.pkg.name)
            self._field("Автор", "author", self.pkg.author)
            self._field("Издатель", "publisher", getattr(self.pkg, "publisher", ""))
            self._field("Дата", "date", self.pkg.date)
            self._field("Сложность (1-10)", "difficulty", self.pkg.difficulty)
            self._field("Ограничение", "restriction", self.pkg.restriction, hint="12+ или 18+")
            self._field("Язык", "language", self.pkg.language)
            self._field("Теги (через запятую)", "tags", ", ".join(self.pkg.tags))
            self._field("Логотип (файл)", "logo", getattr(self.pkg, "logo", ""), hint="Сначала добавьте картинку через любой вопрос, затем укажите имя файла")
            self._field("Описание", "comments", self.pkg.comments, multiline=True)
            # кнопка выбора логотипа
            logo_row = ttk.Frame(self.form_frame)
            logo_row.pack(fill=tk.X, pady=2)
            def pick_logo():
                path = filedialog.askopenfilename(
                    title="Логотип пакета",
                    filetypes=[("Картинки", "*.jpg *.jpeg *.png *.gif *.webp"), ("Все", "*.*")],
                )
                if not path:
                    return
                fname = os.path.basename(path)
                self.pkg.media_files[fname] = path
                if "logo" in self.form_vars:
                    self.form_vars["logo"].set(fname)
                self.status.config(text="Логотип: " + fname)
            ttk.Button(logo_row, text="Выбрать файл логотипа…", command=pick_logo).pack(side=tk.LEFT)
            self.form_widgets.append(logo_row)
            self._add_apply(self.apply_package)

        elif path[0] == "round":
            ri = path[1]
            rnd = self.pkg.rounds[ri]
            self.editor_title.config(text="Раунд: " + rnd.name)
            self.hint_label.config(text="Финал — раунд со ставками в конце игры.")
            self._field("Название", "name", rnd.name)
            self._check("Финальный раунд", "is_final", rnd.is_final)
            self._add_apply(lambda: self.apply_round(ri))

        elif path[0] == "theme":
            ri, ti = path[1], path[2]
            theme = self.pkg.rounds[ri].themes[ti]
            self.editor_title.config(text="Тема: " + theme.name)
            self.hint_label.config(text="Тема = столбец на табло.")
            self._field("Название темы", "name", theme.name)
            self._add_apply(lambda: self.apply_theme(ri, ti))

        elif path[0] == "question":
            ri, ti, qi = path[1], path[2], path[3]
            q = self.pkg.rounds[ri].themes[ti].questions[qi]
            self._editing_question = (ri, ti, qi)
            # работаем с копиями атомов до «Применить»
            self._q_atoms = [a.copy() for a in q.atoms]
            self._q_answer_atoms = [a.copy() for a in q.answer_atoms]

            self.editor_title.config(text="Вопрос")
            self.hint_label.config(
                text="Добавляйте текст, фото, звук и видео. Порядок = порядок показа. "
                     "Блок «В ответе» показывается после правильного ответа."
            )
            self._field("Стоимость", "price", q.price)
            type_labels = ["%s — %s" % (k, v) for k, v in QUESTION_TYPES]
            cur = next(("%s — %s" % (k, v) for k, v in QUESTION_TYPES if k == q.qtype), type_labels[0])
            self._combo("Тип", "qtype", cur, type_labels)

            self._atom_editor("Сценарий вопроса (что видят/слышат игроки)", self._q_atoms, is_answer=False)
            self._atom_editor("В ответе (после marker — показ правильного ответа)", self._q_answer_atoms, is_answer=True)

            self._list_editor("Правильные ответы (текст)", "answers", q.answers or [""], "Правильный ответ")
            self._list_editor("Неправильные ответы", "wrong", q.wrong, "Неправильный")
            self._field("Комментарий ведущему", "comment", q.comment, multiline=True)
            self._field("Секретная тема (кот)", "secret_theme", q.secret_theme, hint="Для кота в мешке")
            self._field("Секретная стоимость", "secret_cost", q.secret_cost or "", hint="0 = как на табло")
            self._check("Кот: можно взять себе", "cat_self", getattr(q, "cat_self", True))
            knows_choices = ["before — узнают до передачи", "after — после передачи", "never — не узнают (только очки)"]
            cur_knows = getattr(q, "cat_knows", "before") or "before"
            cur_label = next((c for c in knows_choices if c.startswith(cur_knows)), knows_choices[0])
            self._combo("Кот: когда видна тема", "cat_knows", cur_label, knows_choices)
            self._add_apply(lambda: self.apply_question(ri, ti, qi))

        self._canvas.yview_moveto(0)

    def _add_apply(self, cmd):
        btn = ttk.Button(self.form_frame, text="Применить изменения", command=cmd)
        btn.pack(pady=10)
        self.form_widgets.append(btn)

    # ---------- Apply ----------

    def apply_package(self):
        self.pkg.name = (self._get("name") or self.pkg.name)[:MAX_NAME_LEN]
        self.pkg.author = self._get("author")
        self.pkg.date = self._get("date")
        try:
            self.pkg.difficulty = max(1, min(10, int(self._get("difficulty") or 4)))
        except ValueError:
            pass
        self.pkg.restriction = self._get("restriction") or "12+"
        self.pkg.language = self._get("language") or "ru-RU"
        self.pkg.publisher = self._get("publisher")
        self.pkg.logo = self._get("logo")
        self.pkg.tags = [t.strip() for t in self._get("tags").split(",") if t.strip()]
        self.pkg.comments = self._get("comments")
        self._refresh_tree(("package",))
        self._mark_dirty()
        self.status.config(text="Пакет обновлён")

    def apply_round(self, ri):
        if self._get("name"):
            self.pkg.rounds[ri].name = self._get("name")
        self.pkg.rounds[ri].is_final = bool(self._get("is_final"))
        self._refresh_tree(("round", ri))
        self._mark_dirty()
        self.status.config(text="Раунд обновлён")

    def apply_theme(self, ri, ti):
        if self._get("name"):
            self.pkg.rounds[ri].themes[ti].name = self._get("name")
            self._refresh_tree(("theme", ri, ti))
            self._mark_dirty()
        self.status.config(text="Тема обновлена")

    def apply_question(self, ri, ti, qi):
        q = self.pkg.rounds[ri].themes[ti].questions[qi]
        try:
            q.price = int(str(self._get("price") or 100).strip())
        except ValueError:
            q.price = 100
            messagebox.showwarning("Стоимость", "Нужно число. Поставлено 100.", parent=self)
        if q.price < MIN_PRICE:
            q.price = MIN_PRICE
        if q.price > MAX_PRICE:
            q.price = MAX_PRICE
        type_raw = self._get("qtype")
        q.qtype = type_raw.split(" — ")[0] if " — " in type_raw else "simple"
        q.atoms = getattr(self, "_q_atoms", q.atoms)
        q.answer_atoms = getattr(self, "_q_answer_atoms", q.answer_atoms)
        if not q.atoms:
            q.atoms = [Atom("text", "")]
        q.answers = self._get_list("answers") or [""]
        q.wrong = [w for w in self._get_list("wrong") if w]
        q.comment = self._get("comment")
        q.secret_theme = self._get("secret_theme")
        try:
            q.secret_cost = int(self._get("secret_cost") or 0)
        except ValueError:
            q.secret_cost = 0
        q.cat_self = bool(self._get("cat_self"))
        knows_raw = self._get("cat_knows")
        q.cat_knows = knows_raw.split(" — ")[0].strip() if knows_raw else "before"
        if q.cat_knows not in ("before", "after", "never"):
            q.cat_knows = "before"
        self._refresh_tree(("question", ri, ti, qi))
        self._mark_dirty()
        self.status.config(text="Вопрос обновлён")

    # ---------- Структура ----------

    def add_round(self):
        name = simpledialog.askstring("Раунд", "Название:", initialvalue="Основной раунд")
        if name:
            self.pkg.rounds.append(Round(name.strip()))
            self._mark_dirty()
            self._refresh_tree(("round", len(self.pkg.rounds) - 1))

    def add_theme(self):
        path = self._get_path()
        ri = path[1] if path and path[0] in ("round", "theme", "question") else (0 if self.pkg.rounds else None)
        if ri is None:
            messagebox.showinfo("Нужен раунд", "Сначала добавьте раунд.")
            return
        name = simpledialog.askstring("Тема", "Название:", initialvalue="Новая тема")
        if name:
            self.pkg.rounds[ri].themes.append(Theme(name.strip()))
            self._mark_dirty()
            self._refresh_tree(("theme", ri, len(self.pkg.rounds[ri].themes) - 1))

    def add_question(self):
        path = self._get_path()
        ri = ti = None
        if path and path[0] == "theme":
            ri, ti = path[1], path[2]
        elif path and path[0] == "question":
            ri, ti = path[1], path[2]
        elif path and path[0] == "round" and self.pkg.rounds[path[1]].themes:
            ri, ti = path[1], 0
        if ri is None:
            messagebox.showinfo("Нужна тема", "Сначала добавьте тему.")
            return
        theme = self.pkg.rounds[ri].themes[ti]
        q = Question()
        q.price = DEFAULT_PRICES[len(theme.questions) % len(DEFAULT_PRICES)]
        theme.questions.append(q)
        self._mark_dirty()
        self._refresh_tree(("question", ri, ti, len(theme.questions) - 1))

    def move_up(self):
        self._move(-1)

    def move_down(self):
        self._move(1)

    def _move(self, d):
        path = self._get_path()
        if not path or path[0] == "package":
            return
        if path[0] == "round":
            i, j = path[1], path[1] + d
            if 0 <= j < len(self.pkg.rounds):
                self.pkg.rounds[i], self.pkg.rounds[j] = self.pkg.rounds[j], self.pkg.rounds[i]
                self._refresh_tree(("round", j))
        elif path[0] == "theme":
            ri, ti = path[1], path[2]
            th = self.pkg.rounds[ri].themes
            j = ti + d
            if 0 <= j < len(th):
                th[ti], th[j] = th[j], th[ti]
                self._refresh_tree(("theme", ri, j))
        elif path[0] == "question":
            ri, ti, qi = path[1], path[2], path[3]
            qs = self.pkg.rounds[ri].themes[ti].questions
            j = qi + d
            if 0 <= j < len(qs):
                qs[qi], qs[j] = qs[j], qs[qi]
                self._refresh_tree(("question", ri, ti, j))

    def duplicate(self):
        path = self._get_path()
        if not path or path[0] == "package":
            return
        if path[0] == "round":
            ri = path[1]
            self.pkg.rounds.insert(ri + 1, self.pkg.rounds[ri].copy())
            self._refresh_tree(("round", ri + 1))
        elif path[0] == "theme":
            ri, ti = path[1], path[2]
            self.pkg.rounds[ri].themes.insert(ti + 1, self.pkg.rounds[ri].themes[ti].copy())
            self._refresh_tree(("theme", ri, ti + 1))
        elif path[0] == "question":
            ri, ti, qi = path[1], path[2], path[3]
            self.pkg.rounds[ri].themes[ti].questions.insert(
                qi + 1, self.pkg.rounds[ri].themes[ti].questions[qi].copy()
            )
            self._refresh_tree(("question", ri, ti, qi + 1))

    def delete_selected(self):
        path = self._get_path()
        if not path or path[0] == "package":
            messagebox.showinfo("Удаление", "Выберите раунд, тему или вопрос.")
            return
        if not messagebox.askyesno("Удалить?", "Удалить выбранное?"):
            return
        if path[0] == "round":
            del self.pkg.rounds[path[1]]
        elif path[0] == "theme":
            del self.pkg.rounds[path[1]].themes[path[2]]
        elif path[0] == "question":
            del self.pkg.rounds[path[1]].themes[path[2]].questions[path[3]]
        self._mark_dirty()
        self._clear_form()
        self._refresh_tree()

    # ---------- Файл ----------

    def new_package(self):
        if not self._confirm_discard():
            return
        if not messagebox.askyesno("Новый", "Создать пустой пакет?", parent=self):
            return
        self._new_defaults()
        self.dirty = False
        self._clear_form()
        self._refresh_tree()
        self.title("SIGame Редактор")
        self._mark_clean()

    def open_package(self):
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            title="Открыть .siq",
            filetypes=[("SIGame", "*.siq"), ("Все файлы", "*.*")],
            parent=self,
        )
        if not path:
            return
        try:
            self.pkg = load_siq(path)
            self.current_file = path
            self._clear_form()
            self._refresh_tree()
            self.title("SIGame — " + os.path.basename(path))
            self._mark_clean()
            self.status.config(
                text="Открыт: %s (%d медиа)"
                % (os.path.basename(path), len(self.pkg.media_files))
            )
        except Exception as e:
            messagebox.showerror("Не удалось открыть", str(e), parent=self)

    def save_package(self):
        if not self._check_package(for_play=False):
            # errors block; warnings already shown
            errors, _ = validate_package(self.pkg)
            if errors:
                return
        if self.current_file:
            try:
                save_siq(self.pkg, self.current_file)
                self._mark_clean()
                self.status.config(text="Сохранено: " + os.path.basename(self.current_file))
            except Exception as e:
                messagebox.showerror("Не удалось сохранить", str(e), parent=self)
        else:
            self.save_package_as()

    def save_package_as(self):
        errors, _ = validate_package(self.pkg)
        if errors:
            messagebox.showerror(
                "Нельзя сохранить",
                "Исправьте:\n• " + "\n• ".join(errors),
                parent=self,
            )
            return
        safe_name = "".join(
            c if c.isalnum() or c in "._- " else "_"
            for c in (self.pkg.name or "pack")
        ).strip() or "pack"
        path = filedialog.asksaveasfilename(
            title="Сохранить .siq",
            defaultextension=".siq",
            initialfile=(safe_name[:50] + ".siq"),
            filetypes=[("SIGame", "*.siq")],
            parent=self,
        )
        if not path:
            return
        try:
            save_siq(self.pkg, path)
            self.current_file = path
            self.title("SIGame — " + os.path.basename(path))
            self._mark_clean()
            self.status.config(text="Сохранено: " + os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Не удалось сохранить", str(e), parent=self)

    def play_online(self):
        if not self._check_package(for_play=True):
            return
        path = self.current_file
        if not path:
            safe_name = "".join(
                c if c.isalnum() or c in "._- " else "_"
                for c in (self.pkg.name or "pack")
            ).strip() or "pack"
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                safe_name[:40] + ".siq",
            )
        try:
            save_siq(self.pkg, path)
            self.current_file = path
            self._mark_clean()
        except Exception as e:
            messagebox.showerror("Не удалось сохранить", str(e), parent=self)
            return
        webbrowser.open(SIGAME_ONLINE_URL)
        messagebox.showinfo(
            "Игра",
            "Пакет сохранён:\n%s\n\n"
            "На сайте: создать игру → пакет «Из файла» → выберите этот .siq\n\n%s"
            % (path, SIGAME_ONLINE_URL),
            parent=self,
        )





    def _mark_dirty(self):
        self.dirty = True
        title = self.title()
        if not title.startswith("*"):
            self.title("*" + title)

    def _mark_clean(self):
        self.dirty = False
        title = self.title()
        if title.startswith("*"):
            self.title(title[1:])

    def _confirm_discard(self):
        if not self.dirty:
            return True
        r = messagebox.askyesnocancel(
            "Несохранено",
            "Есть несохранённые изменения.\n\n"
            "Да — сохранить\nНет — не сохранять\nОтмена — остаться",
            parent=self,
        )
        if r is None:
            return False
        if r:
            self.save_package()
            return not self.dirty
        return True

    def _on_close(self):
        if self._confirm_discard():
            self.destroy()

    def _check_package(self, for_play=False):
        errors, warnings = validate_package(self.pkg)
        if errors:
            messagebox.showerror(
                "Нельзя продолжить",
                "Исправьте:\n• " + "\n• ".join(errors),
                parent=self,
            )
            return False
        if warnings:
            msg = "Замечания:\n• " + "\n• ".join(warnings[:12])
            if len(warnings) > 12:
                msg += "\n… ещё %d" % (len(warnings) - 12)
            if for_play:
                msg += "\n\nВсё равно играть?"
                return messagebox.askyesno("Проверка", msg, parent=self)
            messagebox.showwarning("Проверка", msg, parent=self)
        return True

    def _soft_welcome(self):
        dialogs.soft_welcome(self, self.show_beginner_guide)

    def show_beginner_guide(self):
        dialogs.show_beginner_guide(self)

    def make_room_qr(self):
        dialogs.make_room_qr(self, status_callback=lambda t: self.status.config(text=t))

    def show_host_hints(self):
        dialogs.show_host_hints(self)

    def show_help(self):
        dialogs.show_help(self)

    def show_about(self):
        dialogs.show_about(self)

