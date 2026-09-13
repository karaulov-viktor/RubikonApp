# -*- coding: utf-8 -*-
"""Утилиты путей к картинкам и медиафайлам (объединённый модуль).

Часть 1 (старая, спринт 1.5): drug_image_source() — пути к фото
ПРЕПАРАТОВ из img/drugs/. База хранит ОТНОСИТЕЛЬНЫЙ путь, Kivy
резолвит его от CWD, а CWD зависит от того, откуда запущено
приложение — поэтому НЕ ДОВЕРЯЕМ CWD, собираем абсолютный путь
через BASE_DIR (урок «Not found img/drugs/...»).

Часть 2 (новая, спринт «Питомцы»): выбор медиа через диалог,
копирование в media/pets/pet_<id>/, относительные пути в БД.
"""
import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Заглушка, если фото препарата отсутствует на диске
FALLBACK_IMAGE = os.path.join(BASE_DIR, "img", "logo.png")

# Относительная заглушка для resolve_media (медиа питомцев)
FALLBACK = os.path.join("img", "logo.png")

MEDIA_EXT = {
    "photo": (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"),
    "video": (".mp4", ".avi", ".mkv", ".mov", ".webm"),
}


# ------------------------------------------------------------------
# Часть 1: фото препаратов (старый интерфейс)
# ------------------------------------------------------------------
def drug_image_source(rel_path):
    """Относительный путь из БД -> абсолютный; файла нет — заглушка."""
    if not rel_path:
        return FALLBACK_IMAGE
    full = os.path.join(BASE_DIR, str(rel_path).replace("/", os.sep))
    return full if os.path.exists(full) else FALLBACK_IMAGE


# ------------------------------------------------------------------
# Часть 2: медиа питомцев (новый интерфейс)
# ------------------------------------------------------------------
def resolve_media(rel_path: str) -> str:
    """Относительный путь из БД -> абсолютный, если файл существует,
    иначе — логотип (fallback). Никогда не возвращает пустоту."""
    if not rel_path:
        return os.path.join(BASE_DIR, FALLBACK)
    rel = str(rel_path).replace("\\", "/").lstrip("/")
    abs_path = os.path.join(BASE_DIR, rel)
    if os.path.exists(abs_path):
        return abs_path
    return os.path.join(BASE_DIR, FALLBACK)


def pick_media_src(kind: str = "photo") -> str | None:
    """Диалог выбора файла -> АБСОЛЮТНЫЙ путь источника | None.

    Копирование — отдельным шагом copy_media_to(): при добавлении
    питомца id ещё не существует, копируем ПОСЛЕ сохранения записи.
    tkinter вызывается лениво и только на стороне пользователя.
    """
    import tkinter as tk
    from tkinter import filedialog

    exts = MEDIA_EXT.get(kind, MEDIA_EXT["photo"])
    patterns = [
        (f"{'Видео' if kind == 'video' else 'Изображения'}",
         " ".join("*" + e for e in exts)),
        ("Все файлы", "*.*"),
    ]

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        src = filedialog.askopenfilename(title="Выберите файл",
                                         filetypes=patterns)
    finally:
        root.destroy()
    if not src:
        return None
    if os.path.splitext(src)[1].lower() not in exts:
        return None
    return src


def copy_media_to(src_abs: str, pet_id: int) -> str | None:
    """Копия файла в media/pets/pet_<id>/ -> ОТНОСИТЕЛЬНЫЙ путь | None."""
    if not src_abs or not os.path.exists(src_abs):
        return None
    dest_dir = os.path.join(BASE_DIR, "media", "pets", f"pet_{pet_id}")
    os.makedirs(dest_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(
        dest_dir, f"{stamp}-{os.path.basename(src_abs)}"
    )
    try:
        shutil.copy2(src_abs, dest)
    except OSError:
        return None
    return os.path.relpath(dest, BASE_DIR).replace("\\", "/")


def delete_media_file(rel_path: str):
    """Удаляет файл медиа (файлы лежат в media/pets/pet_<id>/)."""
    if not rel_path:
        return
    rel = str(rel_path).replace("\\", "/").lstrip("/")
    abs_path = os.path.join(BASE_DIR, rel)
    try:
        if os.path.exists(abs_path) and \
                "media/pets/" in rel.replace("\\", "/"):
            os.remove(abs_path)
    except OSError:
        pass
