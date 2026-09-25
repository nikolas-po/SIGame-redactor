# -*- coding: utf-8 -*-
"""Локальная генерация QR без интернета."""

from __future__ import annotations

import os


def make_qr_png(data: str, out_path: str, box_size: int = 8, border: int = 2) -> str:
    """
    Сохраняет PNG с QR. Нужен пакет qrcode (и желательно pillow).
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
            "Не установлен модуль qrcode.\n"
            "Выполните: pip install qrcode pillow"
        ) from e

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Pillow-путь (обычный)
    try:
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(out_path)
        if not os.path.isfile(out_path) or os.path.getsize(out_path) < 50:
            raise OSError("файл не записался")
        return out_path
    except Exception:
        pass

    # без Pillow — SVG рядом, а PNG через простую матрицу в SVG
    svg_path = os.path.splitext(out_path)[0] + ".svg"
    matrix = qr.get_matrix()
    n = len(matrix)
    scale = box_size
    pad = border * scale
    size = n * scale + pad * 2
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        % (size, size, size, size),
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]
    for y, row in enumerate(matrix):
        for x, cell in enumerate(row):
            if cell:
                parts.append(
                    '<rect x="%d" y="%d" width="%d" height="%d" fill="#000000"/>'
                    % (pad + x * scale, pad + y * scale, scale, scale)
                )
    parts.append("</svg>")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    # если просили png, а получился svg — сообщим через путь
    if out_path.lower().endswith(".png"):
        # попытка записать хоть что-то полезное
        return svg_path
    return svg_path
