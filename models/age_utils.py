# -*- coding: utf-8 -*-
"""Возраст и даты: расчёты из даты рождения питомца.

Чистый Python без Kivy — можно тестировать в песочнице.
Все даты в БД хранятся строками YYYY-MM-DD (сортируются лексикографически).
"""
import datetime as _dt

DATE_FMT = "%Y-%m-%d"
DISPLAY_FMT = "%d.%m.%Y"


def parse_date(s):
    """'2019-05-14' -> date | None (тихо, без исключений)."""
    if not s:
        return None
    try:
        return _dt.datetime.strptime(str(s).strip()[:10], DATE_FMT).date()
    except ValueError:
        return None


def fmt_display(s):
    """'2019-05-14' -> '14.05.2019' (или исходная строка, если не дата)."""
    d = parse_date(s)
    return d.strftime(DISPLAY_FMT) if d else (s or "")


def _plural(n: int, one: str, few: str, many: str) -> str:
    """Русские склонения: 1 год / 2 года / 5 лет."""
    n = abs(int(n)) % 100
    if 11 <= n <= 19:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def format_age(birth_str: str, today=None) -> str:
    """Возраст питомца human-readable: '2 г. 3 мес.', '7 мес.', '2 нед.'.

    Правила:
      >= 1 года  -> годы + месяцы (месяцы опускаем, если 0)
      < 1 года   -> только месяцы
      < 1 мес.   -> недели
      нет даты   -> ''
    """
    birth = parse_date(birth_str)
    if birth is None:
        return ""
    today = today or _dt.date.today()
    if birth > today:
        return ""

    # Полные месяцы между датами
    months = (today.year - birth.year) * 12 + (today.month - birth.month)
    if today.day < birth.day:
        months -= 1
    months = max(months, 0)

    years, rem_months = divmod(months, 12)

    if years >= 1:
        parts = [f"{years} {_plural(years, 'г.', 'г.', 'г.')}"]
        if rem_months:
            parts.append(
                f"{rem_months} {_plural(rem_months, 'мес.', 'мес.', 'мес.')}"
            )
        return " ".join(parts)

    if months >= 1:
        return f"{months} {_plural(months, 'мес.', 'мес.', 'мес.')}"

    days = (today - birth).days
    weeks = days // 7
    if weeks >= 1:
        return f"{weeks} {_plural(weeks, 'нед.', 'нед.', 'нед.')}"
    return f"{days} {_plural(days, 'день', 'дня', 'дней')}"


def is_birthday_today(birth_str: str, today=None) -> bool:
    """День рождения питомца сегодня? (сравнение день+месяц)."""
    birth = parse_date(birth_str)
    if birth is None:
        return False
    today = today or _dt.date.today()
    return (birth.month, birth.day) == (today.month, today.day)


def days_until_birthday(birth_str: str, today=None) -> int | None:
    """Сколько дней до ближайшего дня рождения (0 = сегодня)."""
    birth = parse_date(birth_str)
    if birth is None:
        return None
    today = today or _dt.date.today()
    try:
        candidate = birth.replace(year=today.year)
    except ValueError:  # 29 февраля в невисокосный год
        candidate = birth.replace(year=today.year, day=28)
    if candidate < today:
        try:
            candidate = birth.replace(year=today.year + 1)
        except ValueError:
            candidate = birth.replace(year=today.year + 1, day=28)
    return (candidate - today).days
