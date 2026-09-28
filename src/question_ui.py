# -*- coding: utf-8 -*-
"""Форма вопроса: правка прямо в полях, без «Изменить»."""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from constants import QUESTION_TYPES, MEDIA_EXTS, TYPE_HELP
from models import Atom


def show_preview(parent, question):
    win = tk.Toplevel(parent)
    win.title("Как увидят игроки")
    win.geometry("560x520")
    win.transient(parent)
    txt = tk.Text(win, wrap=tk.WORD, font=("", 12), padx=12, pady=12)
    txt.pack(fill=tk.BOTH, expand=True)
    try:
        body = question.preview_text()
    except Exception:
        body = ""
    txt.insert("1.0", body)
    txt.config(state=tk.DISABLED)
    ttk.Button(win, text="Закрыть", command=win.destroy).pack(pady=8)


class QuestionFormBuilder:
    def __init__(self, app, form_frame, question, path):
        self.app = app
        self.form = form_frame
        self.q = question
        self.path = path
        self.widgets = []
        self.vars = {}
        self._auto_job = None
        self.q.ensure_variants()
        # media atoms only (text goes to big field)
        atoms = list(self.q.variants[0].get("atoms") or self.q.atoms or [])
        self.media_atoms = [a.copy() for a in atoms if a.atype not in ("text", "say")]
        self.answer_atoms = [a.copy() for a in (self.q.answer_atoms or []) if a.atype not in ("text", "say")]

    def _text_from_question(self):
        atoms = list(self.q.variants[0].get("atoms") or self.q.atoms or [])
        parts = []
        for a in atoms:
            if a.atype in ("text", "say") and a.value:
                parts.append(a.value.strip())
        return "\n".join(parts)

    def build(self):
        q = self.q

        # 1. Тип
        tf = ttk.LabelFrame(self.form, text="1. Тип вопроса", padding=8)
        tf.pack(fill=tk.X, pady=4)
        self.widgets.append(tf)
        self.type_frame = tf
        self.type_var = tk.StringVar(value=q.qtype or "simple")
        row = ttk.Frame(tf)
        row.pack(fill=tk.X)
        for key, label in QUESTION_TYPES:
            ttk.Radiobutton(
                row, text=label, value=key, variable=self.type_var, command=self._on_type_change
            ).pack(side=tk.LEFT, padx=4)
        self.type_help = ttk.Label(
            tf, text="", wraplength=640, justify=tk.LEFT,
            foreground="#0d47a1", background="#e3f2fd", padding=8,
        )
        self.type_help.pack(fill=tk.X, pady=(8, 4))

        # кот ДО _on_type_change
        self.cat_frame = ttk.LabelFrame(self.form, text="Настройки «Кота»", padding=6)
        self.widgets.append(self.cat_frame)
        self._entry(self.cat_frame, "Секретная тема", "secret_theme", q.secret_theme or "")
        self._entry(self.cat_frame, "Секретная цена (0 = как на табло)", "secret_cost", q.secret_cost or "")
        self.cat_self = tk.BooleanVar(value=bool(q.cat_self))
        ttk.Checkbutton(
            self.cat_frame, text="Можно оставить себе", variable=self.cat_self,
            command=self._schedule_auto,
        ).pack(anchor="w")
        self._combo(
            self.cat_frame, "Когда узнают тему", "cat_knows",
            {"before": "до передачи", "after": "после", "never": "никогда"}.get(q.cat_knows, "до передачи"),
            ["до передачи", "после", "никогда"],
        )
        self._on_type_change()

        # 2. Цена
        pf = ttk.LabelFrame(self.form, text="2. Цена", padding=6)
        pf.pack(fill=tk.X, pady=4)
        self.widgets.append(pf)
        self._entry(pf, "Очки", "price", q.price)

        # 3. Текст вопроса — главное поле, правим прямо здесь
        qf = ttk.LabelFrame(self.form, text="3. Текст вопроса (пишите прямо здесь)", padding=6)
        qf.pack(fill=tk.BOTH, expand=True, pady=4)
        self.widgets.append(qf)
        self.q_body = tk.Text(qf, height=8, wrap=tk.WORD, font=("", 12), undo=True)
        self.q_body.pack(fill=tk.BOTH, expand=True)
        self.q_body.insert("1.0", self._text_from_question())
        self.q_body.bind("<KeyRelease>", lambda e: self._schedule_auto())
        self.q_body.bind("<FocusOut>", lambda e: self._auto_apply())

        # медиа
        mf = ttk.LabelFrame(self.form, text="Фото / звук / видео (по желанию)", padding=6)
        mf.pack(fill=tk.X, pady=4)
        self.widgets.append(mf)
        self.media_lb = tk.Listbox(mf, height=3, font=("", 11))
        self.media_lb.pack(fill=tk.X)
        self._refresh_media()
        mb = ttk.Frame(mf)
        mb.pack(fill=tk.X, pady=2)
        for txt, cmd in [
            ("+ Фото", lambda: self._add_media("image")),
            ("+ Звук", lambda: self._add_media("voice")),
            ("+ Видео", lambda: self._add_media("video")),
            ("Удалить", self._del_media),
        ]:
            ttk.Button(mb, text=txt, command=cmd).pack(side=tk.LEFT, padx=2)

        # 4. Ответы — прямо в поле
        af = ttk.LabelFrame(
            self.form,
            text="4. Правильные ответы (каждый с новой строки)",
            padding=6,
        )
        af.pack(fill=tk.X, pady=4)
        self.widgets.append(af)
        self.ans_body = tk.Text(af, height=4, wrap=tk.WORD, font=("", 12), undo=True)
        self.ans_body.pack(fill=tk.X)
        self.ans_body.insert("1.0", "\n".join(q.answers or [""]))
        self.ans_body.bind("<KeyRelease>", lambda e: self._schedule_auto())
        self.ans_body.bind("<FocusOut>", lambda e: self._auto_apply())

        ttk.Label(af, text="Явно неверные (необязательно, с новой строки):").pack(anchor="w", pady=(6, 0))
        self.wrong_body = tk.Text(af, height=2, wrap=tk.WORD, font=("", 11), undo=True)
        self.wrong_body.pack(fill=tk.X)
        self.wrong_body.insert("1.0", "\n".join(q.wrong or []))
        self.wrong_body.bind("<KeyRelease>", lambda e: self._schedule_auto())
        self.wrong_body.bind("<FocusOut>", lambda e: self._auto_apply())

        # заметки
        nf = ttk.LabelFrame(self.form, text="Заметки ведущему (по желанию)", padding=6)
        nf.pack(fill=tk.X, pady=4)
        self.widgets.append(nf)
        self.mod_partial = tk.BooleanVar(value=bool(q.mod_partial))
        self.mod_no_penalty = tk.BooleanVar(value=bool(q.mod_no_penalty))
        for text, var in [
            ("Можно принять близкий ответ", self.mod_partial),
            ("Без штрафа за ошибку", self.mod_no_penalty),
        ]:
            ttk.Checkbutton(nf, text=text, variable=var, command=self._schedule_auto).pack(anchor="w")
        self._entry(nf, "Комментарий", "comment", q.comment or "", multi=True)

        bf = ttk.Frame(self.form)
        bf.pack(fill=tk.X, pady=8)
        self.widgets.append(bf)
        ttk.Button(bf, text="Как увидят игроки", command=self._preview).pack(side=tk.LEFT, padx=4)
        ttk.Label(bf, text="Правки сохраняются сами — кнопка «Изменить» не нужна", foreground="#555").pack(
            side=tk.LEFT, padx=10
        )

    def _on_type_change(self):
        key = self.type_var.get()
        if hasattr(self, "type_help"):
            self.type_help.config(text=(TYPE_HELP.get(key, "") or "").replace("\\n", "\n"))
        self._sync_cat()
        self._schedule_auto()

    def _sync_cat(self):
        if not getattr(self, "cat_frame", None):
            return
        try:
            if self.type_var.get() in ("cat", "bagcat"):
                self.cat_frame.pack(fill=tk.X, pady=4, after=self.type_frame)
            else:
                self.cat_frame.pack_forget()
        except Exception:
            pass

    def _entry(self, parent, label, key, value, multi=False):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=3)
        ttk.Label(row, text=label, width=22).pack(side=tk.LEFT, anchor="n")
        if multi:
            w = tk.Text(row, height=3, wrap=tk.WORD, font=("", 11), undo=True)
            w.insert("1.0", value or "")
            w.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            w.bind("<KeyRelease>", lambda e: self._schedule_auto())
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

    def _combo(self, parent, label, key, value, choices):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
        var = tk.StringVar(value=value)
        ttk.Combobox(row, textvariable=var, values=choices, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
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

    def _refresh_media(self):
        self.media_lb.delete(0, tk.END)
        for a in self.media_atoms:
            self.media_lb.insert(tk.END, a.display())

    def _add_media(self, atype):
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
        self.media_atoms.append(a)
        self._refresh_media()
        self._auto_apply()

    def _del_media(self):
        sel = self.media_lb.curselection()
        if not sel:
            return
        self.media_atoms.pop(sel[0])
        self._refresh_media()
        self._auto_apply()

    def _preview(self):
        from models import Question
        tmp = Question()
        self._fill_question(tmp)
        show_preview(self.app, tmp)

    def _lines(self, widget):
        return [ln.strip() for ln in widget.get("1.0", "end").splitlines() if ln.strip()]

    def _fill_question(self, q):
        try:
            q.price = int(str(self._get("price") or 100).strip())
        except ValueError:
            q.price = 100
        q.qtype = self.type_var.get() or "simple"
        body = self.q_body.get("1.0", "end").strip()
        text_atoms = [Atom("text", ln) for ln in body.splitlines() if ln.strip()] or [Atom("text", "")]
        atoms = text_atoms + [a.copy() for a in self.media_atoms]
        q.variants = [{"name": "Основной", "atoms": atoms}]
        if hasattr(q, "sync_atoms_from_primary"):
            q.sync_atoms_from_primary()
        else:
            q.atoms = list(atoms)
        q.answer_atoms = [a.copy() for a in self.answer_atoms]
        q.answers = self._lines(self.ans_body) or [""]
        q.wrong = self._lines(self.wrong_body)
        q.comment = self._get("comment")
        q.secret_theme = self._get("secret_theme")
        try:
            q.secret_cost = int(self._get("secret_cost") or 0)
        except ValueError:
            q.secret_cost = 0
        q.cat_self = bool(self.cat_self.get())
        knows = self._get("cat_knows")
        q.cat_knows = {"до передачи": "before", "после": "after", "никогда": "never"}.get(knows, "before")
        q.mod_partial = bool(self.mod_partial.get())
        q.mod_no_penalty = bool(self.mod_no_penalty.get())

    def _schedule_auto(self):
        if self._auto_job:
            try:
                self.app.after_cancel(self._auto_job)
            except Exception:
                pass
        self._auto_job = self.app.after(350, self._auto_apply)

    def _auto_apply(self):
        try:
            ri, ti, qi = self.path
            q = self.app.pkg.rounds[ri].themes[ti].questions[qi]
            self._fill_question(q)
            self.app._mark_dirty()
            self.app.status.config(text="Сохранено")
        except Exception:
            pass
