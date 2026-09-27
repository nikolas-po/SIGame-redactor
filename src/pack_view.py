# -*- coding: utf-8 -*-
"""Все вопросы: правка сразу, автосохранение без кнопки."""

import tkinter as tk
from tkinter import ttk

from models import Atom


def show_pack_overview(app):
    pkg = app.pkg
    win = tk.Toplevel(app)
    win.title("Все вопросы — правка сразу (сохраняется само)")
    win.geometry("1100x720")
    win.minsize(900, 560)
    try:
        win.transient(app)
    except Exception:
        pass

    top = ttk.Frame(win, padding=8)
    top.pack(fill=tk.X)
    ttk.Label(
        top,
        text="Меняйте текст справа — сохраняется само. Кнопка «Сохранить» в главном окне нужна только чтобы записать файл .siq на диск.",
        wraplength=1050,
        foreground="#0d47a1",
    ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    status = ttk.Label(win, text="Готово", padding=(8, 2), foreground="#2e7d32")
    status.pack(fill=tk.X)

    body = ttk.Panedwindow(win, orient=tk.HORIZONTAL)
    body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    left = ttk.Frame(body, padding=4)
    body.add(left, weight=1)
    ttk.Label(left, text="Вопросы", font=("", 11, "bold")).pack(anchor="w")
    cols = ("where", "price", "qshort")
    tree = ttk.Treeview(
        left, columns=cols, show="headings", selectmode="browse", height=28
    )
    tree.heading("where", text="Где")
    tree.heading("price", text="Цена")
    tree.heading("qshort", text="Вопрос")
    tree.column("where", width=170, minwidth=80)
    tree.column("price", width=50, minwidth=40)
    tree.column("qshort", width=280, minwidth=100)
    ys = ttk.Scrollbar(left, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=ys.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ys.pack(side=tk.RIGHT, fill=tk.Y)

    right = ttk.Frame(body, padding=8)
    body.add(right, weight=3)

    meta = ttk.Label(right, text="Выберите вопрос слева", font=("", 11, "bold"))
    meta.pack(anchor="w", pady=(0, 6))

    ttk.Label(right, text="Текст вопроса:").pack(anchor="w")
    q_text = tk.Text(right, height=12, wrap=tk.WORD, font=("", 12), undo=True)
    q_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    ttk.Label(right, text="Ответы (несколько через ; ):").pack(anchor="w")
    a_text = tk.Text(right, height=4, wrap=tk.WORD, font=("", 12), undo=True)
    a_text.pack(fill=tk.X, pady=(0, 8))

    price_row = ttk.Frame(right)
    price_row.pack(fill=tk.X, pady=4)
    ttk.Label(price_row, text="Цена:").pack(side=tk.LEFT)
    price_var = tk.StringVar()
    price_entry = ttk.Entry(price_row, textvariable=price_var, font=("", 12))
    price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

    rows = {}
    current = {"iid": None}
    job = {"id": None}
    loading = {"flag": False}  # не сохранять при подстановке текста

    def get_q_text(q):
        atoms = list(getattr(q, "atoms", None) or [])
        if getattr(q, "variants", None):
            atoms = list(q.variants[0].get("atoms") or atoms)
        parts = []
        for a in atoms:
            t = getattr(a, "atype", "")
            if t in ("text", "say") and a.value:
                parts.append(a.value.strip())
            elif t == "image":
                parts.append("[фото: %s]" % a.value)
            elif t == "voice":
                parts.append("[звук: %s]" % a.value)
            elif t == "video":
                parts.append("[видео: %s]" % a.value)
        return "\n".join(parts)

    def set_q_text(q, text):
        q.ensure_variants()
        atoms = list(q.variants[0].get("atoms") or [])
        media = [a for a in atoms if a.atype not in ("text", "say")]
        pure = []
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if (
                ln.startswith("[фото:")
                or ln.startswith("[звук:")
                or ln.startswith("[видео:")
            ):
                continue
            pure.append(ln)
        new_atoms = [Atom("text", ln) for ln in pure] if pure else [Atom("text", "")]
        new_atoms.extend(media)
        q.variants[0]["atoms"] = new_atoms
        if hasattr(q, "sync_atoms_from_primary"):
            q.sync_atoms_from_primary()
        else:
            q.atoms = list(new_atoms)

    def fill_list():
        tree.delete(*tree.get_children())
        rows.clear()
        for ri, rnd in enumerate(pkg.rounds):
            for ti, theme in enumerate(rnd.themes):
                for qi, q in enumerate(theme.questions):
                    iid = "r%dt%dq%d" % (ri, ti, qi)
                    rows[iid] = (ri, ti, qi)
                    short = get_q_text(q).replace("\n", " ")
                    if len(short) > 90:
                        short = short[:87] + "..."
                    tree.insert(
                        "",
                        "end",
                        iid=iid,
                        values=("%s / %s" % (rnd.name, theme.name), q.price, short),
                    )

    def save_current():
        iid = current["iid"]
        if not iid or iid not in rows:
            return False
        ri, ti, qi = rows[iid]
        q = pkg.rounds[ri].themes[ti].questions[qi]
        set_q_text(q, q_text.get("1.0", "end").strip())
        ans = a_text.get("1.0", "end").strip()
        parts = [p.strip() for p in ans.replace("\n", ";").split(";") if p.strip()]
        q.answers = parts or [""]
        try:
            q.price = int(str(price_var.get()).strip())
        except ValueError:
            pass
        app._mark_dirty()
        short = get_q_text(q).replace("\n", " ")
        if len(short) > 90:
            short = short[:87] + "..."
        try:
            where = tree.item(iid, "values")[0]
            tree.item(iid, values=(where, q.price, short))
        except Exception:
            pass
        status.config(
            text="Сохранено в пакет (нажмите «Сохранить» в главном окне для файла .siq)"
        )
        return True

    def schedule_save(_event=None):
        if loading["flag"]:
            return
        if job["id"]:
            try:
                win.after_cancel(job["id"])
            except Exception:
                pass
        job["id"] = win.after(400, save_current)

    def on_select(_event=None):
        sel = tree.selection()
        if not sel:
            return
        if current["iid"] and current["iid"] != sel[0]:
            save_current()
        iid = sel[0]
        if iid not in rows:
            return
        current["iid"] = iid
        ri, ti, qi = rows[iid]
        rnd = pkg.rounds[ri]
        theme = rnd.themes[ti]
        q = theme.questions[qi]
        loading["flag"] = True
        try:
            meta.config(
                text="%s → %s → %s очков · %s"
                % (rnd.name, theme.name, q.price, q.qtype or "simple")
            )
            q_text.delete("1.0", tk.END)
            q_text.insert("1.0", get_q_text(q))
            a_text.delete("1.0", tk.END)
            a_text.insert("1.0", "; ".join(q.answers or []))
            price_var.set(str(q.price))
            status.config(text="Редактирование — изменения сохраняются сами")
        finally:
            loading["flag"] = False

    tree.bind("<<TreeviewSelect>>", on_select)

    # автосохранение при наборе и уходе с поля
    q_text.bind("<KeyRelease>", schedule_save)
    a_text.bind("<KeyRelease>", schedule_save)
    q_text.bind("<FocusOut>", lambda e: save_current())
    a_text.bind("<FocusOut>", lambda e: save_current())
    price_var.trace_add("write", lambda *_: schedule_save())
    price_entry.bind("<FocusOut>", lambda e: save_current())

    bot = ttk.Frame(win, padding=8)
    bot.pack(fill=tk.X)

    def close():
        save_current()
        try:
            app._refresh_tree()
        except Exception:
            pass
        win.destroy()

    def open_main():
        save_current()
        sel = tree.selection()
        if sel and sel[0] in rows:
            try:
                app._refresh_tree(("question",) + rows[sel[0]])
            except Exception:
                pass
        win.destroy()

    ttk.Button(
        bot,
        text="Обновить дерево слева",
        command=lambda: (save_current(), app._refresh_tree()),
    ).pack(side=tk.LEFT, padx=4)
    ttk.Button(bot, text="Открыть в основном окне", command=open_main).pack(
        side=tk.LEFT, padx=4
    )
    ttk.Button(bot, text="Закрыть", command=close).pack(side=tk.RIGHT, padx=4)
    win.protocol("WM_DELETE_WINDOW", close)

    fill_list()
    kids = tree.get_children()
    if kids:
        tree.selection_set(kids[0])
        tree.focus(kids[0])
        on_select()
