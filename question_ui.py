# -*- coding: utf-8 -*-
"""Форма вопроса: тип, варианты, модификаторы, предпросмотр."""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from constants import QUESTION_TYPES, MEDIA_EXTS, MEDIA_FOLDERS
from models import Atom


def show_preview(parent, question):
    win = tk.Toplevel(parent)
    win.title("Предпросмотр вопроса")
    win.geometry("520x560")
    win.transient(parent)
    txt = tk.Text(win, wrap=tk.WORD, font=("", 11), padx=10, pady=10)
    txt.pack(fill=tk.BOTH, expand=True)
    try:
        body = question.preview_text().replace("\\n", "\n")
    except Exception:
        body = str(question)
    txt.insert("1.0", body)
    txt.config(state=tk.DISABLED)
    ttk.Button(win, text="Закрыть", command=win.destroy).pack(pady=8)


def pick_question_type(parent, current="simple"):
    """Диалог быстрого выбора типа. Возвращает ключ типа или None."""
    win = tk.Toplevel(parent)
    win.title("Тип вопроса")
    win.geometry("360x320")
    win.transient(parent)
    win.grab_set()
    result = {"value": None}

    ttk.Label(win, text="Выберите тип вопроса:", font=("", 11, "bold")).pack(
        anchor="w", padx=12, pady=8
    )
    var = tk.StringVar(value=current)
    for key, label in QUESTION_TYPES:
        ttk.Radiobutton(
            win, text="%s — %s" % (key, label), variable=var, value=key
        ).pack(anchor="w", padx=20, pady=3)

    def ok():
        result["value"] = var.get()
        win.destroy()

    def cancel():
        win.destroy()

    bf = ttk.Frame(win)
    bf.pack(pady=12)
    ttk.Button(bf, text="OK", command=ok).pack(side=tk.LEFT, padx=6)
    ttk.Button(bf, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=6)
    win.wait_window()
    return result["value"]


class QuestionFormBuilder:
    """Строит виджеты формы вопроса внутри parent frame."""

    def __init__(self, app, form_frame, question, path):
        self.app = app
        self.form = form_frame
        self.q = question
        self.path = path  # (ri, ti, qi)
        self.widgets = []
        self.vars = {}
        self.listboxes = {}
        self.variant_index = 0
        self.q.ensure_variants()
        # рабочие копии
        self.variants = [
            {
                "name": v.get("name", "Вариант"),
                "atoms": [a.copy() for a in v.get("atoms") or [Atom("text", "")]],
            }
            for v in self.q.variants
        ]
        self.answer_atoms = [a.copy() for a in (self.q.answer_atoms or [])]

    def build(self):
        q = self.q
        self._label("Нажмите тип или смените ниже. Двойной клик по вопросу в дереве — быстрый выбор типа.")
        # --- тип кнопками ---
        tf = ttk.LabelFrame(self.form, text="Тип вопроса", padding=6)
        tf.pack(fill=tk.X, pady=4)
        self.widgets.append(tf)
        self.type_var = tk.StringVar(value=q.qtype or "simple")
        row = ttk.Frame(tf)
        row.pack(fill=tk.X)
        for key, label in QUESTION_TYPES:
            ttk.Radiobutton(
                row, text=label, value=key, variable=self.type_var
            ).pack(side=tk.LEFT, padx=4)

        self._field("Стоимость", "price", q.price)

        # --- модификаторы ---
        mf = ttk.LabelFrame(self.form, text="Модификаторы", padding=6)
        mf.pack(fill=tk.X, pady=4)
        self.widgets.append(mf)
        self.mod_partial = tk.BooleanVar(value=bool(q.mod_partial))
        self.mod_no_penalty = tk.BooleanVar(value=bool(q.mod_no_penalty))
        self.mod_host_choice = tk.BooleanVar(value=bool(q.mod_host_choice))
        ttk.Checkbutton(
            mf, text="Можно принять близкий ответ", variable=self.mod_partial
        ).pack(anchor="w")
        ttk.Checkbutton(
            mf, text="Без штрафа за неверный ответ", variable=self.mod_no_penalty
        ).pack(anchor="w")
        ttk.Checkbutton(
            mf,
            text="Ведущий выбирает вариант показа (текст/аудио/…)",
            variable=self.mod_host_choice,
        ).pack(anchor="w")
        tr = ttk.Frame(mf)
        tr.pack(fill=tk.X, pady=2)
        ttk.Label(tr, text="Таймер (сек, 0=обычный):").pack(side=tk.LEFT)
        self.timer_var = tk.StringVar(value=str(q.mod_timer_sec or 0))
        ttk.Entry(tr, textvariable=self.timer_var, width=8).pack(side=tk.LEFT, padx=6)
        self._field("Заметка модификатора", "mod_note", q.mod_note or "")

        # --- варианты ---
        vf = ttk.LabelFrame(
            self.form,
            text="Варианты показа (например: Текст и Аудио — на выбор)",
            padding=6,
        )
        vf.pack(fill=tk.X, pady=4)
        self.widgets.append(vf)

        topv = ttk.Frame(vf)
        topv.pack(fill=tk.X)
        self.variant_list = tk.Listbox(topv, height=3, exportselection=False)
        self.variant_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._refresh_variant_list()
        self.variant_list.bind("<<ListboxSelect>>", self._on_variant_select)

        vb = ttk.Frame(topv)
        vb.pack(side=tk.LEFT, padx=4)
        ttk.Button(vb, text="+ Вариант", command=self._add_variant).pack(fill=tk.X, pady=1)
        ttk.Button(vb, text="Имя", command=self._rename_variant).pack(fill=tk.X, pady=1)
        ttk.Button(vb, text="Удалить", command=self._del_variant).pack(fill=tk.X, pady=1)

        self.atom_frame = ttk.LabelFrame(vf, text="Содержимое варианта", padding=4)
        self.atom_frame.pack(fill=tk.X, pady=4)
        self.atom_listbox = tk.Listbox(self.atom_frame, height=5)
        self.atom_listbox.pack(fill=tk.X)
        ab = ttk.Frame(self.atom_frame)
        ab.pack(fill=tk.X)
        for txt, cmd in [
            ("+ Текст", lambda: self._add_atom("text")),
            ("+ Реплика", lambda: self._add_atom("say")),
            ("+ Фото", lambda: self._add_atom("image")),
            ("+ Звук", lambda: self._add_atom("voice")),
            ("+ Видео", lambda: self._add_atom("video")),
            ("Изм.", self._edit_atom),
            ("−", self._del_atom),
            ("↑", lambda: self._move_atom(-1)),
            ("↓", lambda: self._move_atom(1)),
        ]:
            ttk.Button(ab, text=txt, command=cmd).pack(side=tk.LEFT, padx=1)
        self._load_atoms_for_variant()

        # ответ
        self._atom_block_answer()
        self._list_editor("Правильные ответы", "answers", q.answers or [""])
        self._list_editor("Неправильные", "wrong", q.wrong or [])
        self._field("Комментарий ведущему", "comment", q.comment or "", multi=True)
        self._field("Секретная тема (кот)", "secret_theme", q.secret_theme or "")
        self._field("Секретная стоимость", "secret_cost", q.secret_cost or "")
        self.cat_self = tk.BooleanVar(value=bool(q.cat_self))
        cat_row = ttk.Frame(self.form)
        cat_row.pack(fill=tk.X, anchor="w")
        ttk.Checkbutton(
            cat_row, text="Кот: можно взять себе", variable=self.cat_self
        ).pack(anchor="w")
        self.widgets.append(cat_row)
        self._combo(
            "Кот: когда видна тема",
            "cat_knows",
            {"before": "before — до передачи", "after": "after — после", "never": "never — никогда"}.get(
                q.cat_knows, "before — до передачи"
            ),
            ["before — до передачи", "after — после", "never — никогда"],
        )

        bf = ttk.Frame(self.form)
        bf.pack(fill=tk.X, pady=10)
        self.widgets.append(bf)
        ttk.Button(bf, text="Предпросмотр", command=self._preview).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(bf, text="Применить изменения", command=self._apply).pack(
            side=tk.LEFT, padx=4
        )

    def _label(self, text):
        w = ttk.Label(self.form, text=text, foreground="#555", wraplength=520)
        w.pack(anchor="w")
        self.widgets.append(w)

    def _field(self, label, key, value, multi=False):
        row = ttk.Frame(self.form)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=22).pack(side=tk.LEFT, anchor="n")
        if multi:
            w = tk.Text(row, height=3, width=42, wrap=tk.WORD)
            w.insert("1.0", value or "")
            w.pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            var = tk.StringVar(value=str(value if value is not None else ""))
            w = ttk.Entry(row, textvariable=var, width=42)
            w.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.vars[key] = var
            self.widgets.append(row)
            return
        self.vars[key] = w
        self.widgets.append(row)

    def _combo(self, label, key, value, choices):
        row = ttk.Frame(self.form)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
        var = tk.StringVar(value=value)
        ttk.Combobox(row, textvariable=var, values=choices, width=36, state="readonly").pack(
            side=tk.LEFT
        )
        self.vars[key] = var
        self.widgets.append(row)

    def _get(self, key):
        v = self.vars.get(key)
        if isinstance(v, tk.Text):
            return v.get("1.0", "end").strip()
        if isinstance(v, tk.StringVar):
            return v.get().strip()
        return ""

    def _list_editor(self, title, key, items):
        frame = ttk.LabelFrame(self.form, text=title, padding=4)
        frame.pack(fill=tk.X, pady=4)
        self.widgets.append(frame)
        lb = tk.Listbox(frame, height=3)
        lb.pack(fill=tk.X)
        for it in items:
            lb.insert(tk.END, it)
        self.listboxes[key] = lb
        bf = ttk.Frame(frame)
        bf.pack(fill=tk.X)

        def add():
            val = simpledialog.askstring("Добавить", title, parent=self.app)
            if val is not None:
                lb.insert(tk.END, val.strip())

        def edit():
            sel = lb.curselection()
            if not sel:
                return
            val = simpledialog.askstring(
                "Изменить", title, initialvalue=lb.get(sel[0]), parent=self.app
            )
            if val is not None:
                lb.delete(sel[0])
                lb.insert(sel[0], val.strip())

        def rem():
            sel = lb.curselection()
            if sel:
                lb.delete(sel[0])

        for t, c in [("+", add), ("Изм.", edit), ("−", rem)]:
            ttk.Button(bf, text=t, width=4, command=c).pack(side=tk.LEFT, padx=1)

    def _get_list(self, key):
        lb = self.listboxes.get(key)
        return [lb.get(i) for i in range(lb.size())] if lb else []

    def _refresh_variant_list(self):
        self.variant_list.delete(0, tk.END)
        for i, v in enumerate(self.variants):
            n = len(v.get("atoms") or [])
            self.variant_list.insert(
                tk.END, "%d. %s (%d эл.)" % (i + 1, v.get("name") or "?", n)
            )
        if self.variants:
            self.variant_list.selection_set(min(self.variant_index, len(self.variants) - 1))

    def _on_variant_select(self, _event=None):
        sel = self.variant_list.curselection()
        if not sel:
            return
        self.variant_index = sel[0]
        self._load_atoms_for_variant()

    def _current_atoms(self):
        if not self.variants:
            self.variants = [{"name": "Основной", "atoms": [Atom("text", "")]}]
        return self.variants[self.variant_index]["atoms"]

    def _load_atoms_for_variant(self):
        self.atom_listbox.delete(0, tk.END)
        for a in self._current_atoms():
            self.atom_listbox.insert(tk.END, a.display())

    def _add_variant(self):
        name = simpledialog.askstring(
            "Вариант", "Название (например: Текст, Аудио, Фото):", parent=self.app
        )
        if not name:
            return
        self.variants.append({"name": name.strip(), "atoms": [Atom("text", "")]})
        self.variant_index = len(self.variants) - 1
        self._refresh_variant_list()
        self._load_atoms_for_variant()
        self.mod_host_choice.set(True)

    def _rename_variant(self):
        if not self.variants:
            return
        cur = self.variants[self.variant_index]
        name = simpledialog.askstring(
            "Имя", "Название варианта:", initialvalue=cur.get("name", ""), parent=self.app
        )
        if name:
            cur["name"] = name.strip()
            self._refresh_variant_list()

    def _del_variant(self):
        if len(self.variants) <= 1:
            messagebox.showinfo("Варианты", "Нужен хотя бы один вариант.", parent=self.app)
            return
        del self.variants[self.variant_index]
        self.variant_index = max(0, self.variant_index - 1)
        self._refresh_variant_list()
        self._load_atoms_for_variant()

    def _add_atom(self, atype):
        atoms = self._current_atoms()
        if atype in ("text", "say"):
            val = simpledialog.askstring(
                "Текст" if atype == "text" else "Реплика", "Текст:", parent=self.app
            )
            if val is None:
                return
            atoms.append(Atom(atype, val.strip()))
        else:
            labels = {"image": "Фото", "voice": "Звук", "video": "Видео"}
            path = filedialog.askopenfilename(
                title=labels.get(atype, "Файл"),
                filetypes=[
                    (labels.get(atype, "Файл"), " ".join("*" + e for e in MEDIA_EXTS.get(atype, []))),
                    ("Все", "*.*"),
                ],
                parent=self.app,
            )
            if not path:
                return
            fname = os.path.basename(path)
            base, ext = os.path.splitext(fname)
            n = 1
            while fname in self.app.pkg.media_files and self.app.pkg.media_files[fname] != path:
                fname = "%s_%d%s" % (base, n, ext)
                n += 1
            self.app.pkg.media_files[fname] = path
            a = Atom(atype, fname)
            a.local_path = path
            atoms.append(a)
        self._load_atoms_for_variant()
        self._refresh_variant_list()

    def _edit_atom(self):
        sel = self.atom_listbox.curselection()
        if not sel:
            return
        atoms = self._current_atoms()
        atom = atoms[sel[0]]
        if atom.atype in ("text", "say"):
            val = simpledialog.askstring(
                "Изменить", "Текст:", initialvalue=atom.value, parent=self.app
            )
            if val is not None:
                atom.value = val.strip()
        else:
            path = filedialog.askopenfilename(title="Заменить файл", parent=self.app)
            if path:
                fname = os.path.basename(path)
                self.app.pkg.media_files[fname] = path
                atom.value = fname
                atom.local_path = path
        self._load_atoms_for_variant()

    def _del_atom(self):
        sel = self.atom_listbox.curselection()
        if not sel:
            return
        atoms = self._current_atoms()
        if len(atoms) <= 1:
            atoms[0] = Atom("text", "")
        else:
            atoms.pop(sel[0])
        self._load_atoms_for_variant()
        self._refresh_variant_list()

    def _move_atom(self, d):
        sel = self.atom_listbox.curselection()
        if not sel:
            return
        atoms = self._current_atoms()
        i, j = sel[0], sel[0] + d
        if 0 <= j < len(atoms):
            atoms[i], atoms[j] = atoms[j], atoms[i]
            self._load_atoms_for_variant()
            self.atom_listbox.selection_set(j)

    def _atom_block_answer(self):
        frame = ttk.LabelFrame(self.form, text="В ответе (после правильного)", padding=4)
        frame.pack(fill=tk.X, pady=4)
        self.widgets.append(frame)
        self.ans_lb = tk.Listbox(frame, height=3)
        self.ans_lb.pack(fill=tk.X)
        for a in self.answer_atoms:
            self.ans_lb.insert(tk.END, a.display())

        def refresh():
            self.ans_lb.delete(0, tk.END)
            for a in self.answer_atoms:
                self.ans_lb.insert(tk.END, a.display())

        def add(atype):
            if atype in ("text", "say"):
                val = simpledialog.askstring("Текст", "Текст:", parent=self.app)
                if val is None:
                    return
                self.answer_atoms.append(Atom(atype, val.strip()))
            else:
                path = filedialog.askopenfilename(parent=self.app)
                if not path:
                    return
                fname = os.path.basename(path)
                self.app.pkg.media_files[fname] = path
                a = Atom(atype, fname)
                a.local_path = path
                self.answer_atoms.append(a)
            refresh()

        def rem():
            sel = self.ans_lb.curselection()
            if sel:
                self.answer_atoms.pop(sel[0])
                refresh()

        bf = ttk.Frame(frame)
        bf.pack(fill=tk.X)
        for t, c in [
            ("+ Текст", lambda: add("text")),
            ("+ Фото", lambda: add("image")),
            ("+ Звук", lambda: add("voice")),
            ("+ Видео", lambda: add("video")),
            ("−", rem),
        ]:
            ttk.Button(bf, text=t, command=c).pack(side=tk.LEFT, padx=1)

    def _preview(self):
        # временный объект для превью
        from models import Question

        tmp = Question()
        self._fill_question(tmp)
        show_preview(self.app, tmp)

    def _fill_question(self, q):
        try:
            q.price = int(str(self._get("price") or 100).strip())
        except ValueError:
            q.price = 100
        q.qtype = self.type_var.get() or "simple"
        q.variants = [
            {"name": v["name"], "atoms": [a.copy() for a in v["atoms"]]}
            for v in self.variants
        ]
        q.sync_atoms_from_primary()
        q.answer_atoms = [a.copy() for a in self.answer_atoms]
        q.answers = self._get_list("answers") or [""]
        q.wrong = [w for w in self._get_list("wrong") if w]
        q.comment = self._get("comment")
        q.secret_theme = self._get("secret_theme")
        try:
            q.secret_cost = int(self._get("secret_cost") or 0)
        except ValueError:
            q.secret_cost = 0
        q.cat_self = bool(self.cat_self.get())
        knows = self._get("cat_knows")
        q.cat_knows = knows.split(" — ")[0].strip() if knows else "before"
        q.mod_partial = bool(self.mod_partial.get())
        q.mod_no_penalty = bool(self.mod_no_penalty.get())
        q.mod_host_choice = bool(self.mod_host_choice.get())
        try:
            q.mod_timer_sec = max(0, int(self.timer_var.get() or 0))
        except ValueError:
            q.mod_timer_sec = 0
        q.mod_note = self._get("mod_note")

    def _apply(self):
        ri, ti, qi = self.path
        q = self.app.pkg.rounds[ri].themes[ti].questions[qi]
        self._fill_question(q)
        self.app._mark_dirty()
        self.app._refresh_tree(("question", ri, ti, qi))
        self.app.status.config(text="Вопрос сохранён (варианты и модификаторы)")
