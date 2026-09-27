# -*- coding: utf-8 -*-
"""Форма вопроса: тип → объяснение → содержимое. Автосохранение."""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from constants import QUESTION_TYPES, MEDIA_EXTS, MEDIA_FOLDERS, TYPE_HELP
from models import Atom


def show_preview(parent, question):
    win = tk.Toplevel(parent)
    win.title("Как увидят игроки")
    win.geometry("560x600")
    win.transient(parent)
    txt = tk.Text(win, wrap=tk.WORD, font=("", 12), padx=12, pady=12)
    txt.pack(fill=tk.BOTH, expand=True)
    try:
        body = question.preview_text()
    except Exception:
        body = str(question)
    txt.insert("1.0", body)
    txt.config(state=tk.DISABLED)
    ttk.Button(win, text="Закрыть", command=win.destroy).pack(pady=8)


def pick_question_type(parent, current="simple"):
    win = tk.Toplevel(parent)
    win.title("Тип вопроса")
    win.geometry("500x420")
    win.transient(parent)
    win.grab_set()
    result = {"value": None}
    ttk.Label(win, text="Выберите тип клетки", font=("", 12, "bold")).pack(
        anchor="w", padx=12, pady=8
    )
    var = tk.StringVar(value=current or "simple")
    help_lbl = ttk.Label(win, text="", wraplength=460, justify=tk.LEFT)
    help_lbl.pack(anchor="w", padx=12, pady=8, fill=tk.X)

    def refresh(*_):
        help_lbl.config(text=(TYPE_HELP.get(var.get(), "") or "").replace("\\n", "\n"))

    for key, label in QUESTION_TYPES:
        ttk.Radiobutton(
            win, text=label, variable=var, value=key, command=refresh
        ).pack(anchor="w", padx=20, pady=3)
    refresh()

    def ok():
        result["value"] = var.get()
        win.destroy()

    bf = ttk.Frame(win)
    bf.pack(pady=12)
    ttk.Button(bf, text="Выбрать", command=ok).pack(side=tk.LEFT, padx=6)
    ttk.Button(bf, text="Отмена", command=win.destroy).pack(side=tk.LEFT, padx=6)
    win.wait_window()
    return result["value"]


class QuestionFormBuilder:
    def __init__(self, app, form_frame, question, path):
        self.app = app
        self.form = form_frame
        self.q = question
        self.path = path
        self.widgets = []
        self.vars = {}
        self.listboxes = {}
        self.variant_index = 0
        self._auto_job = None
        self.q.ensure_variants()
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

        # --- 1. Тип ---
        tf = ttk.LabelFrame(self.form, text="1. Тип вопроса", padding=8)
        tf.pack(fill=tk.X, pady=4)
        self.widgets.append(tf)
        self.type_frame = tf
        self.type_var = tk.StringVar(value=q.qtype or "simple")
        row = ttk.Frame(tf)
        row.pack(fill=tk.X)
        for key, label in QUESTION_TYPES:
            ttk.Radiobutton(
                row,
                text=label,
                value=key,
                variable=self.type_var,
                command=self._on_type_change,
            ).pack(side=tk.LEFT, padx=4)
        self.type_help = ttk.Label(
            tf, text="", wraplength=640, justify=tk.LEFT,
            foreground="#0d47a1", background="#e3f2fd", padding=8,
        )
        self.type_help.pack(fill=tk.X, pady=(8, 4))

        # --- кот (создаём ДО _on_type_change) ---
        self.cat_frame = ttk.LabelFrame(
            self.form, text="Настройки «Кота»", padding=6
        )
        self.widgets.append(self.cat_frame)
        self._field_in(self.cat_frame, "Секретная тема", "secret_theme", q.secret_theme or "")
        self._field_in(self.cat_frame, "Секретная цена (0 = как на табло)", "secret_cost", q.secret_cost or "")
        self.cat_self = tk.BooleanVar(value=bool(q.cat_self))
        ttk.Checkbutton(
            self.cat_frame, text="Можно оставить себе", variable=self.cat_self,
            command=self._schedule_auto,
        ).pack(anchor="w")
        self._combo_in(
            self.cat_frame, "Когда узнают тему", "cat_knows",
            {"before": "before — до передачи", "after": "after — после", "never": "never — никогда"}.get(
                q.cat_knows, "before — до передачи"
            ),
            ["before — до передачи", "after — после", "never — никогда"],
        )
        self._on_type_change()

        # --- 2. Цена ---
        pf = ttk.LabelFrame(self.form, text="2. Цена на табло", padding=6)
        pf.pack(fill=tk.X, pady=4)
        self.widgets.append(pf)
        self._field_in(pf, "Очки", "price", q.price)

        # --- 3. Содержимое ---
        vf = ttk.LabelFrame(
            self.form, text="3. Вопрос (текст / фото / звук / видео)", padding=6
        )
        vf.pack(fill=tk.BOTH, expand=True, pady=4)
        self.widgets.append(vf)

        topv = ttk.Frame(vf)
        topv.pack(fill=tk.X, pady=4)
        self.variant_list = tk.Listbox(topv, height=3, exportselection=False, font=("", 11))
        self.variant_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._refresh_variant_list()
        self.variant_list.bind("<<ListboxSelect>>", self._on_variant_select)
        vb = ttk.Frame(topv)
        vb.pack(side=tk.LEFT, padx=4)
        ttk.Button(vb, text="+ Вариант", command=self._add_variant).pack(fill=tk.X, pady=1)
        ttk.Button(vb, text="Имя", command=self._rename_variant).pack(fill=tk.X, pady=1)
        ttk.Button(vb, text="Удалить", command=self._del_variant).pack(fill=tk.X, pady=1)

        self.atom_frame = ttk.LabelFrame(vf, text="Содержимое варианта", padding=4)
        self.atom_frame.pack(fill=tk.BOTH, expand=True, pady=4)
        self.atom_listbox = tk.Listbox(self.atom_frame, height=6, font=("", 11))
        self.atom_listbox.pack(fill=tk.BOTH, expand=True)
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

        # --- 4. Ответ ---
        af = ttk.LabelFrame(self.form, text="4. Правильный ответ", padding=6)
        af.pack(fill=tk.X, pady=4)
        self.widgets.append(af)
        self._list_editor_in(af, "Засчитывать как верно", "answers", q.answers or [""])
        self._list_editor_in(af, "Неверные (необязательно)", "wrong", q.wrong or [])
        self._atom_block_answer()

        # --- доп ---
        mf = ttk.LabelFrame(self.form, text="Заметки ведущему (по желанию)", padding=6)
        mf.pack(fill=tk.X, pady=4)
        self.widgets.append(mf)
        self.mod_partial = tk.BooleanVar(value=bool(q.mod_partial))
        self.mod_no_penalty = tk.BooleanVar(value=bool(q.mod_no_penalty))
        self.mod_host_choice = tk.BooleanVar(value=bool(q.mod_host_choice))
        for text, var in [
            ("Можно принять близкий ответ", self.mod_partial),
            ("Без штрафа за ошибку", self.mod_no_penalty),
            ("Ведущий выбирает вариант показа", self.mod_host_choice),
        ]:
            ttk.Checkbutton(mf, text=text, variable=var, command=self._schedule_auto).pack(anchor="w")
        tr = ttk.Frame(mf)
        tr.pack(fill=tk.X, pady=2)
        ttk.Label(tr, text="Таймер (сек):").pack(side=tk.LEFT)
        self.timer_var = tk.StringVar(value=str(q.mod_timer_sec or 0))
        ttk.Entry(tr, textvariable=self.timer_var, width=8).pack(side=tk.LEFT, padx=6)
        self.timer_var.trace_add("write", lambda *_: self._schedule_auto())
        self._field_in(mf, "Заметка", "mod_note", q.mod_note or "")
        self._field_in(mf, "Комментарий", "comment", q.comment or "", multi=True)

        bf = ttk.Frame(self.form)
        bf.pack(fill=tk.X, pady=10)
        self.widgets.append(bf)
        ttk.Button(bf, text="Как увидят игроки", command=self._preview).pack(side=tk.LEFT, padx=4)
        ttk.Label(
            bf, text="Правки пишутся сами при уходе с поля", foreground="#555"
        ).pack(side=tk.LEFT, padx=10)

    def _on_type_change(self):
        key = self.type_var.get()
        text = (TYPE_HELP.get(key, "") or "").replace("\\n", "\n")
        if hasattr(self, "type_help"):
            self.type_help.config(text=text)
        self._sync_cat_visibility()
        self._schedule_auto()

    def _sync_cat_visibility(self):
        if not getattr(self, "cat_frame", None):
            return
        key = self.type_var.get()
        try:
            if key in ("cat", "bagcat"):
                self.cat_frame.pack(fill=tk.X, pady=4, after=self.type_frame)
            else:
                self.cat_frame.pack_forget()
        except Exception:
            pass

    def _field_in(self, parent, label, key, value, multi=False):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=3)
        ttk.Label(row, text=label, width=20).pack(side=tk.LEFT, anchor="n")
        if multi:
            w = tk.Text(row, height=4, wrap=tk.WORD, font=("", 11))
            w.insert("1.0", value or "")
            w.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            w.bind("<FocusOut>", lambda e: self._auto_apply())
            self.vars[key] = w
        else:
            var = tk.StringVar(value=str(value if value is not None else ""))
            ent = ttk.Entry(row, textvariable=var, font=("", 11))
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
            var.trace_add("write", lambda *_: self._schedule_auto())
            ent.bind("<FocusOut>", lambda e: self._auto_apply())
            self.vars[key] = var
        self.widgets.append(row)

    def _combo_in(self, parent, label, key, value, choices):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
        var = tk.StringVar(value=value)
        cb = ttk.Combobox(row, textvariable=var, values=choices, state="readonly")
        cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        var.trace_add("write", lambda *_: self._schedule_auto())
        self.vars[key] = var
        self.widgets.append(row)

    def _get(self, key):
        v = self.vars.get(key)
        if isinstance(v, tk.Text):
            return v.get("1.0", "end").strip()
        if isinstance(v, tk.StringVar):
            return v.get().strip()
        return ""

    def _list_editor_in(self, parent, title, key, items):
        frame = ttk.LabelFrame(parent, text=title, padding=4)
        frame.pack(fill=tk.X, pady=4)
        self.widgets.append(frame)
        lb = tk.Listbox(frame, height=3, font=("", 11))
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
                self._auto_apply()

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
                self._auto_apply()

        def rem():
            sel = lb.curselection()
            if sel:
                lb.delete(sel[0])
                self._auto_apply()

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
                tk.END, "%d. %s (%d)" % (i + 1, v.get("name") or "?", n)
            )
        if self.variants:
            self.variant_list.selection_set(
                min(self.variant_index, len(self.variants) - 1)
            )

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
        name = simpledialog.askstring("Вариант", "Название:", parent=self.app)
        if not name:
            return
        self.variants.append({"name": name.strip(), "atoms": [Atom("text", "")]})
        self.variant_index = len(self.variants) - 1
        self._refresh_variant_list()
        self._load_atoms_for_variant()
        self.mod_host_choice.set(True)
        self._auto_apply()

    def _rename_variant(self):
        if not self.variants:
            return
        cur = self.variants[self.variant_index]
        name = simpledialog.askstring(
            "Имя", "Название:", initialvalue=cur.get("name", ""), parent=self.app
        )
        if name:
            cur["name"] = name.strip()
            self._refresh_variant_list()
            self._auto_apply()

    def _del_variant(self):
        if len(self.variants) <= 1:
            messagebox.showinfo("Варианты", "Нужен хотя бы один.", parent=self.app)
            return
        del self.variants[self.variant_index]
        self.variant_index = max(0, self.variant_index - 1)
        self._refresh_variant_list()
        self._load_atoms_for_variant()
        self._auto_apply()

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
        self._auto_apply()

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
        self._auto_apply()

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
        self._auto_apply()

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
            self._auto_apply()

    def _atom_block_answer(self):
        frame = ttk.LabelFrame(
            self.form, text="После ответа (фото/звук) — по желанию", padding=4
        )
        frame.pack(fill=tk.X, pady=4)
        self.widgets.append(frame)
        self.ans_lb = tk.Listbox(frame, height=3, font=("", 11))
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
            self._auto_apply()

        def rem():
            sel = self.ans_lb.curselection()
            if sel:
                self.answer_atoms.pop(sel[0])
                refresh()
                self._auto_apply()

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
        if hasattr(q, "sync_atoms_from_primary"):
            q.sync_atoms_from_primary()
        else:
            q.atoms = list(self.variants[0]["atoms"]) if self.variants else [Atom("text", "")]
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

    def _schedule_auto(self):
        if self._auto_job:
            try:
                self.app.after_cancel(self._auto_job)
            except Exception:
                pass
        self._auto_job = self.app.after(500, self._auto_apply)

    def _auto_apply(self):
        try:
            ri, ti, qi = self.path
            q = self.app.pkg.rounds[ri].themes[ti].questions[qi]
            self._fill_question(q)
            self.app._mark_dirty()
            self.app.status.config(text="Сохранено")
        except Exception:
            pass
