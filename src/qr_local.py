# -*- coding: utf-8 -*-
"""Локальная генерация QR без интернета. Всегда даёт файл, который читает Tk."""

from __future__ import annotations

import os


def make_qr_png(data: str, out_path: str, box_size: int = 8, border: int = 2) -> str:
    """
    Сохраняет изображение QR.
    Предпочтительно PNG (pillow). Иначе PPM — его понимает tk.PhotoImage.
    Возвращает путь к файлу.
    """
    data = (data or "").strip()
    if not data:
        raise ValueError("Пустая ссылка")

    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except ImportError as e:
        raise ImportError(
            "Не установлен модуль qrcode.\nВыполните: pip install qrcode pillow"
        ) from e

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

    # 1) PNG через Pillow
    try:
        img = qr.make_image(fill_color="black", back_color="white")
        png_path = out_path if out_path.lower().endswith(".png") else (os.path.splitext(out_path)[0] + ".png")
        img.save(png_path)
        if os.path.isfile(png_path) and os.path.getsize(png_path) > 50:
            return png_path
    except Exception:
        pass

    # 2) PPM (P3) — всегда читается tk.PhotoImage без Pillow
    matrix = qr.get_matrix()
    n = len(matrix)
    scale = max(2, int(box_size))
    pad = max(1, int(border)) * scale
    size = n * scale + pad * 2
    ppm_path = os.path.splitext(out_path)[0] + ".ppm"
    # строим пиксели
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            ix = (x - pad) // scale
            iy = (y - pad) // scale
            if 0 <= ix < n and 0 <= iy < n and matrix[iy][ix]:
                row.append("0 0 0")
            else:
                row.append("255 255 255")
        rows.append(" ".join(row))
    with open(ppm_path, "w", encoding="ascii") as f:
        f.write("P3\n%d %d\n255\n" % (size, size))
        f.write("\n".join(rows))
        f.write("\n")
    if not os.path.isfile(ppm_path):
        raise OSError("Не удалось записать QR")
    return ppm_path