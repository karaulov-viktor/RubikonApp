r"""
Утилиты путей к картинкам препаратов.

База хранит ОТНОСИТЕЛЬНЫЙ путь (img/drugs/xxx.jpg) — так база остаётся
переносимой: флешка меняет букву диска, проект переезжает — данные целы.

Но Kivy резолвит такой путь от ТЕКУЩЕГО РАБОЧЕГО КАТАЛОГА (CWD),
а CWD зависит от того, ОТКУДА запущено приложение:
    cd I:\Rubikon_vet && python main.py      -> CWD = проект, всё работает
    python I:\Rubikon_vet\main.py            -> CWD = где стояла консоль!

Поэтому «Not found <img/drugs/...>» при рабочей базе.

Правило проекта (урок с фото питомцев — profile.py, pet_detail.py):
НЕ ДОВЕРЯТЬ CWD. Собираем абсолютный путь через BASE_DIR — папку,
в которой лежит проект, вычисленную от расположения этого файла.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Заглушка, если фото препарата отсутствует на диске
FALLBACK_IMAGE = os.path.join(BASE_DIR, "img", "logo.png")


def drug_image_source(rel_path):
    """Относительный путь из БД -> абсолютный; файла нет — заглушка."""
    if not rel_path:
        return FALLBACK_IMAGE
    full = os.path.join(BASE_DIR, str(rel_path).replace("/", os.sep))
    return full if os.path.exists(full) else FALLBACK_IMAGE
