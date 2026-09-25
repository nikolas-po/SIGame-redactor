# -*- coding: utf-8 -*-
"""Загрузка .env рядом с программой."""

import os
import sys
from pathlib import Path


def env_paths():
    paths = []
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).resolve().parent / ".env")
    here = Path(__file__).resolve().parent  # src/
    paths.append(here.parent / ".env")  # корень проекта
    paths.append(here / ".env")
    paths.append(Path.cwd() / ".env")
    # уникальные, по порядку
    seen = set()
    out = []
    for p in paths:
        key = str(p.resolve()) if p.exists() else str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def load_env(path=None):
    """Читает .env. Значения из файла имеют приоритет."""
    files = [Path(path)] if path else env_paths()
    loaded = None
    for p in files:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                os.environ[key] = val
        loaded = p
        break
    return loaded


def get(key, default=""):
    return (os.environ.get(key) if os.environ.get(key) is not None else default) or default


def get_int(key, default=0):
    try:
        return int(str(get(key, default)).strip())
    except (TypeError, ValueError):
        return int(default)
