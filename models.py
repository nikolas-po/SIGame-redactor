# -*- coding: utf-8 -*-

import uuid


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
        return q

    def has_text_or_media(self):
        return any(not a.is_empty() for a in self.atoms)

    def has_answer(self):
        return any((a or "").strip() for a in self.answers)


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
        self.date = "23.09.2026"
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
