#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Точка входа СиПак."""

import sys
from pathlib import Path

# чтобы импорты работали и при python src/main.py, и при python -m src.main
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from env_load import load_env

load_env()


def main():
    try:
        from app import SIQEditor

        app = SIQEditor()
        app.mainloop()
    except Exception as e:
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Ошибка запуска", str(e))
        except Exception:
            print("Ошибка запуска:", e)
            raise


if __name__ == "__main__":
    main()
