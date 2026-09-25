# -*- coding: utf-8 -*-
"""Главное окно редактора пакетов SIGame."""

import os
from datetime import date
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from constants import (
    APP_NAME,
    APP_NAME_FULL,

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
from siq_io import save_siq, load_siq, validate_package, cleanup_extract_dirs, user_data_dir
import dialogs
from version import __version__
import question_ui


class SIQEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME_FULL)
        self.geometry("1200x750")
        try:
            from utils import asset_path
            icon = str(asset_path("logo_sipak_64.png"))
            if os.path.isfile(icon):
                self._icon_img = tk.PhotoImage(file=icon)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass
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
        self.after(1500, self._startup_update_check)

    def _new_defaults(self):
        self.pkg = Package()
        self.pkg.name = "Моя игра"
        self.pkg.comments = ""
        self.pkg.date = date.today().strftime("%d.%m.%Y")
        self.current_file = None

    def _build_ui(self):
        # ----- меню (второстепенное) -----
        menubar = tk.Menu(self)
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="Новый пакет", command=self.new_package)
        m_file.add_command(label="Открыть…", command=self.open_package)
        m_file.add_command(label="Сохранить", command=self.save_package)
        m_file.add_command(label="Сохранить как…", command=self.save_package_as)
        m_file.add_separator()
        m_file.add_command(label="Выход", command=self._on_close)
        menubar.add_cascade(label="Файл", menu=m_file)

        m_play = tk.Menu(menubar, tearoff=0)
        m_play.add_command(label="Играть на сайте", command=self.play_online)
        m_play.add_command(label="QR для игроков", command=self.make_room_qr)
        m_play.add_command(label="Шпаргалка ведущего", command=self.show_host_hints)
        menubar.add_cascade(label="Игра", menu=m_play)

        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="Как начать (3 шага)", command=self.show_beginner_guide)
        m_help.add_command(label="Что такое «Своя игра»?", command=self.show_sigame_lore)
        m_help.add_command(label="Справка", command=self.show_help)
        m_help.add_command(label="Обновления", command=self.check_updates)
        m_help.add_separator()
        m_help.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Помощь", menu=m_help)
        self.config(menu=menubar)

        # ----- главные кнопки (мало и крупно) -----
        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill=tk.X)
        ttk.Label(top, text="СиПак", font=("", 14, "bold")).pack(side=tk.LEFT, padx=(0, 12))
        for text, cmd in [
            ("Открыть", self.open_package),
            ("Сохранить", self.save_package),
            ("Играть", self.play_online),
        ]:
            ttk.Button(top, text=text, command=cmd).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Как начать?", command=self.show_beginner_guide).pack(
            side=tk.RIGHT, padx=4
        )

        # подсказка-строка
        self.guide_bar = ttk.Label(
            self,
            text="Шаги: 1) Добавьте раунд и тему слева → 2) Вопросы → 3) Сохраните → 4) Играть",
            padding=(12, 4),
            background="#e3f2fd",
            foreground="#0d47a1",
        )
        self.guide_bar.pack(fill=tk.X, padx=8, pady=(0, 4))

        main = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # ----- слева: дерево -----
        left = ttk.Frame(main, padding=6)
        main.add(left, weight=1)
        ttk.Label(left, text="Содержание игры", font=("", 11, "bold")).pack(anchor="w")
        ttk.Label(
            left,
            text="Раунд → тема → вопросы (как в телеигре)",
            foreground="#555",
        ).pack(anchor="w", pady=(0, 4))

        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, selectmode="browse", show="tree")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_tree_double)

        bf = ttk.LabelFrame(left, text="Добавить", padding=6)
        bf.pack(fill=tk.X, pady=(8, 4))
        row = ttk.Frame(bf)
        row.pack(fill=tk.X)
        for text, cmd in [
            ("Раунд", self.add_round),
            ("Тему", self.add_theme),
            ("Вопрос", self.add_question),
        ]:
            ttk.Button(row, text=text, command=cmd).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)

        row2 = ttk.Frame(left)
        row2.pack(fill=tk.X, pady=2)
        for text, cmd in [
            ("↑", lambda: self._move(-1)),
            ("↓", lambda: self._move(1)),
            ("Копия", self.duplicate),
            ("Удалить", self.delete_selected),
        ]:
            ttk.Button(row2, text=text, command=cmd, width=8).pack(side=tk.LEFT, padx=2)

        # ----- справа: редактор -----
        right = ttk.Frame(main, padding=6)
        main.add(right, weight=3)
        self.editor_title = ttk.Label(
            right, text="Выберите слева раунд, тему или вопрос", font=("", 12, "bold")
        )
        self.editor_title.pack(anchor="w")
        self.hint_label = ttk.Label(
            right,
            text="Подсказка появится здесь",
            foreground="#444",
            wraplength=560,
            justify=tk.LEFT,
        )
        self.hint_label.pack(anchor="w", pady=(2, 8))

        canvas_host = ttk.Frame(right)
        canvas_host.pack(fill=tk.BOTH, expand=True)
        self._canvas = tk.Canvas(canvas_host, highlightthickness=0)
        scroll = ttk.Scrollbar(canvas_host, orient="vertical", command=self._canvas.yview)
        self.form_frame = ttk.Frame(self._canvas)
        self.form_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scroll.set)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def _wheel(event):
            if event.delta:
                self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 5:
                self._canvas.yview_scroll(1, "units")
            elif event.num == 4:
                self._canvas.yview_scroll(-1, "units")

        self._canvas.bind_all("<MouseWheel>", _wheel)
        self._canvas.bind_all("<Button-4>", _wheel)
        self._canvas.bind_all("<Button-5>", _wheel)

        self.status = ttk.Label(self, text="Готово. Нажмите «Как начать?», если впервые.", padding=6)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

        # на случай старых вызовов меню
        self._legacy_menu_ok = True

    def _clear_form(self):
        # Снимаем всё с панели, иначе остаются старые «Кот: можно взять себе» и т.п.
        for w in list(self.form_widgets):
            try:
                w.destroy()
            except Exception:
                pass
        self.form_widgets.clear()
        self.form_vars.clear()
        self._listboxes.clear()
        for child in list(self.form_frame.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
        self._atom_listbox = None
        self._answer_atom_listbox = None

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

    def on_tree_double(self, event=None):
        path = self._get_path()
        if not path or path[0] != "question":
            return
        ri, ti, qi = path[1], path[2], path[3]
        q = self.pkg.rounds[ri].themes[ti].questions[qi]
        new_type = question_ui.pick_question_type(self, q.qtype or "simple")
        if new_type and new_type != q.qtype:
            q.qtype = new_type
            self._mark_dirty()
            self._refresh_tree(("question", ri, ti, qi))
            self.on_select()
            self.status.config(text="Тип: " + new_type)

    def preview_selected(self):
        path = self._get_path()
        if not path or path[0] != "question":
            messagebox.showinfo("Предпросмотр", "Выберите вопрос в дереве.")
            return
        ri, ti, qi = path[1], path[2], path[3]
        q = self.pkg.rounds[ri].themes[ti].questions[qi]
        question_ui.show_preview(self, q)

    def on_select(self, event=None):
        path = self._get_path()
        self._clear_form()
        if not path:
            self.editor_title.config(text="Выберите элемент слева")
            self.hint_label.config(text="")
            return

        if path[0] == "package":
            self.editor_title.config(text="Свойства пакета")
            self.hint_label.config(text="Это «обложка» набора: название увидят игроки. Остальное — по желанию.")
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
            self.hint_label.config(text="Раунд — часть игры. В конце можно сделать «Финал» (ставки).")
            self._field("Название", "name", rnd.name)
            self._check("Финальный раунд", "is_final", rnd.is_final)
            self._add_apply(lambda: self.apply_round(ri))

        elif path[0] == "theme":
            ri, ti = path[1], path[2]
            theme = self.pkg.rounds[ri].themes[ti]
            self.editor_title.config(text="Тема: " + theme.name)
            self.hint_label.config(text="Тема — колонка на игровом табло (например «История», «Кино»).")
            self._field("Название темы", "name", theme.name)
            self._add_apply(lambda: self.apply_theme(ri, ti))

        elif path[0] == "question":
            ri, ti, qi = path[1], path[2], path[3]
            q = self.pkg.rounds[ri].themes[ti].questions[qi]
            self._editing_question = (ri, ti, qi)
            self.editor_title.config(text="Вопрос")
            self.hint_label.config(
                text="Сначала выберите тип клетки и прочитайте, что он значит. "
                     "Потом цена, текст вопроса и ответ."
            )
            builder = question_ui.QuestionFormBuilder(self, self.form_frame, q, (ri, ti, qi))
            builder.build()
            self.form_widgets.extend(builder.widgets)

        self._canvas.yview_moveto(0)

    def _add_apply(self, cmd):
        btn = ttk.Button(self.form_frame, text="Сохранить эти правки", command=cmd)
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
        name = self._get("name")
        if name:
            self.pkg.rounds[ri].themes[ti].name = name[:200]
            self._refresh_tree(("theme", ri, ti))
            self._mark_dirty()
            self.status.config(text="Тема обновлена")
        else:
            self.status.config(text="Название темы не может быть пустым")

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
        moved = False
        if path[0] == "round":
            i, j = path[1], path[1] + d
            if 0 <= j < len(self.pkg.rounds):
                self.pkg.rounds[i], self.pkg.rounds[j] = self.pkg.rounds[j], self.pkg.rounds[i]
                self._refresh_tree(("round", j))
                moved = True
        elif path[0] == "theme":
            ri, ti = path[1], path[2]
            th = self.pkg.rounds[ri].themes
            j = ti + d
            if 0 <= j < len(th):
                th[ti], th[j] = th[j], th[ti]
                self._refresh_tree(("theme", ri, j))
                moved = True
        elif path[0] == "question":
            ri, ti, qi = path[1], path[2], path[3]
            qs = self.pkg.rounds[ri].themes[ti].questions
            j = qi + d
            if 0 <= j < len(qs):
                qs[qi], qs[j] = qs[j], qs[qi]
                self._refresh_tree(("question", ri, ti, j))
                moved = True
        if moved:
            self._mark_dirty()

    def duplicate(self):
        path = self._get_path()
        if not path or path[0] == "package":
            return
        if path[0] == "round":
            ri = path[1]
            self.pkg.rounds.insert(ri + 1, self.pkg.rounds[ri].copy())
            self._refresh_tree(("round", ri + 1))
            self._mark_dirty()
        elif path[0] == "theme":
            ri, ti = path[1], path[2]
            self.pkg.rounds[ri].themes.insert(ti + 1, self.pkg.rounds[ri].themes[ti].copy())
            self._refresh_tree(("theme", ri, ti + 1))
            self._mark_dirty()
        elif path[0] == "question":
            ri, ti, qi = path[1], path[2], path[3]
            self.pkg.rounds[ri].themes[ti].questions.insert(
                qi + 1, self.pkg.rounds[ri].themes[ti].questions[qi].copy()
            )
            self._refresh_tree(("question", ri, ti, qi + 1))
            self._mark_dirty()

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
        cleanup_extract_dirs()
        self._new_defaults()
        self.dirty = False
        self._clear_form()
        self._refresh_tree()
        self.title(APP_NAME)
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
            cleanup_extract_dirs()
            self.pkg = load_siq(path)
            self.current_file = path
            self._clear_form()
            self._refresh_tree()
            self.title(APP_NAME + " — " + os.path.basename(path))
            self._mark_clean()
            self.status.config(
                text="Открыт: %s (%d медиа)"
                % (os.path.basename(path), len(self.pkg.media_files))
            )
        except Exception as e:
            messagebox.showerror("Не удалось открыть", str(e), parent=self)

    def save_package(self):
        errors, warnings = validate_package(self.pkg)
        if errors:
            messagebox.showerror(
                "Нельзя сохранить",
                "Исправьте:\n• " + "\n• ".join(errors),
                parent=self,
            )
            return
        if warnings:
            messagebox.showwarning(
                "Проверка",
                "Замечания:\n• " + "\n• ".join(warnings[:12]),
                parent=self,
            )
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
            self.title(APP_NAME + " — " + os.path.basename(path))
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
            path = os.path.join(user_data_dir(), safe_name[:40] + ".siq")
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
            try:
                cleanup_extract_dirs()
            except Exception:
                pass
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

    def _startup_update_check(self):
        try:
            dialogs.startup_auto_update(self)
        except Exception:
            pass

    def show_beginner_guide(self):
        dialogs.show_beginner_guide(self)

    def show_sigame_lore(self):
        dialogs.show_sigame_lore(self)

    def make_room_qr(self):
        dialogs.make_room_qr(self, status_callback=lambda t: self.status.config(text=t))

    def show_host_hints(self):
        dialogs.show_host_hints(self)

    def show_help(self):
        dialogs.show_help(self)

    def check_updates(self):
        from utils import project_root
        dialogs.check_for_updates(self, project_dir=str(project_root()))

    def show_about(self):

        dialogs.show_about(self)

