# -*- coding: utf-8 -*-

import uuid
from datetime import date


class Atom:
    def __init__(self, atype="text", value="", duration=0):
        self.atype = atype
        self.value = value if value is not None else ""
        try:
            self.duration = max(0, int(duration) if duration else 0)
        except (TypeError, ValueError):
            self.duration = 0
        self.local_path = None

    def copy(self):
        a = Atom(self.atype, self.value, self.duration)
        a.local_path = self.local_path
        return a

    def display(self):
        icons = {"text": "Т", "say": "Р", "image": "Ф", "voice": "З", "video": "В"}
        ic = icons.get(self.atype, "?")
        if self.atype in ("text", "say"):
            short = (self.value[:50] + "…") if len(self.value) > 50 else self.value
            return "[%s] %s" % (ic, short or "—")
        return "[%s] %s" % (ic, self.value or "файл не выбран")

    def is_empty(self):
        return not (self.value or "").strip()


class Question:
    def __init__(self):
        self.price = 100
        self.qtype = "simple"
        self.atoms = [Atom("text", "")]
        self.answer_atoms = []
        self.answers = [""]
        self.wrong = []
        self.comment = ""
        self.secret_theme = ""
        self.secret_cost = 0
        self.cat_self = True
        self.cat_knows = "before"
        # Варианты подачи (текст / аудио / фото…) — список {"name", "atoms"}
        self.variants = []
        # Модификаторы
        self.mod_partial = False       # можно принять близкий ответ
        self.mod_no_penalty = False    # без снятия очков за неверный
        self.mod_host_choice = False   # ведущий выбирает вариант показа
        self.mod_timer_sec = 0         # подсказка таймера ведущему (0 = по умолчанию)
        self.mod_note = ""             # заметка-модификатор

    def ensure_variants(self):
        """Если variants пуст — один вариант из atoms."""
        if not self.variants:
            self.variants = [{"name": "Основной", "atoms": [a.copy() for a in (self.atoms or [Atom("text", "")])]}]
        return self.variants

    def sync_atoms_from_primary(self):
        vs = self.ensure_variants()
        self.atoms = [a.copy() for a in vs[0]["atoms"]] if vs else [Atom("text", "")]

    def all_question_atoms(self):
        """Все атомы для проверки «есть контент»."""
        atoms = []
        if self.variants:
            for v in self.variants:
                atoms.extend(v.get("atoms") or [])
        else:
            atoms = list(self.atoms or [])
        return atoms

    def copy(self):
        q = Question()
        q.price = self.price
        q.qtype = self.qtype
        q.atoms = [a.copy() for a in self.atoms]
        q.answer_atoms = [a.copy() for a in self.answer_atoms]
        q.answers = list(self.answers)
        q.wrong = list(self.wrong)
        q.comment = self.comment
        q.secret_theme = self.secret_theme
        q.secret_cost = self.secret_cost
        q.cat_self = self.cat_self
        q.cat_knows = self.cat_knows
        q.variants = [
            {"name": v.get("name", "Вариант"), "atoms": [a.copy() for a in v.get("atoms") or []]}
            for v in (self.variants or [])
        ]
        q.mod_partial = self.mod_partial
        q.mod_no_penalty = self.mod_no_penalty
        q.mod_host_choice = self.mod_host_choice
        q.mod_timer_sec = self.mod_timer_sec
        q.mod_note = self.mod_note
        return q

    def has_text_or_media(self):
        return any(not a.is_empty() for a in self.all_question_atoms())

    def has_answer(self):
        return any((a or "").strip() for a in self.answers)

    def preview_text(self):
        lines = []
        lines.append("Тип: %s | Цена: %s" % (self.qtype, self.price))
        mods = []
        if self.mod_partial:
            mods.append("близкий ответ")
        if self.mod_no_penalty:
            mods.append("без штрафа")
        if self.mod_host_choice:
            mods.append("выбор ведущего")
        if self.mod_timer_sec:
            mods.append("таймер %s с" % self.mod_timer_sec)
        if mods:
            lines.append("Модификаторы: " + ", ".join(mods))
        if self.mod_note:
            lines.append("Заметка: " + self.mod_note)
        vs = self.variants if self.variants else [{"name": "Основной", "atoms": self.atoms}]
        for i, v in enumerate(vs):
            lines.append("")
            lines.append("— Вариант %d: %s —" % (i + 1, v.get("name") or "?"))
            for a in v.get("atoms") or []:
                lines.append("  " + a.display())
        if self.answer_atoms:
            lines.append("")
            lines.append("— В ответе —")
            for a in self.answer_atoms:
                lines.append("  " + a.display())
        lines.append("")
        lines.append("Правильно: " + " / ".join(self.answers or ["—"]))
        if self.wrong:
            lines.append("Неправильно: " + " / ".join(self.wrong))
        if self.comment:
            lines.append("Комментарий: " + self.comment)
        if self.qtype in ("cat", "bagcat"):
            lines.append("Секрет: %s (cost %s)" % (self.secret_theme or "—", self.secret_cost))
        return "\n".join(lines)


class Theme:
    def __init__(self, name="Новая тема"):
        self.name = (name or "Новая тема").strip() or "Новая тема"
        self.questions = []

    def copy(self):
        t = Theme(self.name)
        t.questions = [q.copy() for q in self.questions]
        return t


class Round:
    def __init__(self, name="Новый раунд"):
        self.name = (name or "Новый раунд").strip() or "Новый раунд"
        self.is_final = False
        self.themes = []

    def copy(self):
        r = Round(self.name)
        r.is_final = self.is_final
        r.themes = [t.copy() for t in self.themes]
        return r


class Package:
    def __init__(self):
        self.name = "Мой набор вопросов"
        self.date = date.today().strftime("%d.%m.%Y")
        self.difficulty = 4
        self.restriction = "12+"
        self.language = "ru-RU"
        self.author = ""
        self.publisher = ""
        self.comments = ""
        self.tags = []
        self.logo = ""
        self.rounds = []
        self.package_id = str(uuid.uuid4())
        self.media_files = {}

    def question_count(self):
        return sum(len(t.questions) for r in self.rounds for t in r.themes)

    def theme_count(self):
        return sum(len(r.themes) for r in self.rounds)
