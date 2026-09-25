# -*- coding: utf-8 -*-
"""Пути к корню проекта и ресурсам."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def project_root() -> Path:
    """Корень репозитория (рядом с assets/, requirements.txt)."""
    if getattr(sys, "frozen", False):
        # PyInstaller onefile: ресурсы рядом с exe или в _MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            p = Path(meipass)
            if (p / "assets").is_dir():
                return p
        return Path(sys.executable).resolve().parent
    # src/utils.py -> parent=src, parent.parent=root
    return Path(__file__).resolve().parent.parent


def assets_dir() -> Path:
    return project_root() / "assets"


def asset_path(*parts: str) -> Path:
    return assets_dir().joinpath(*parts)


def src_dir() -> Path:
    if getattr(sys, "frozen", False):
        return project_root()
    return Path(__file__).resolve().parent
