#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app import SIQEditor


def main():
    try:
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
