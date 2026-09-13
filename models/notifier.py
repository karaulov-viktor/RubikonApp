# -*- coding: utf-8 -*-
"""Планировщик напоминаний RubikonApp.

Один скан обслуживает ДВА потребителя:
  1) приложение (Clock каждые 30 сек, пока оно запущено)
  2) notifier.py из Планировщика Windows (когда приложение закрыто)

Дедупликация — через data/notifier_state.json: ключ события
запоминается, чтобы не уведомлять дважды (и чтобы приложение и
планировщик не сработали вместе).

Ключи содержат дату, поэтому хранилище самоочищается.
"""
import datetime as _dt
import json
import os

from models import database as db
from models.age_utils import is_birthday_today, parse_date

STATE_PATH = os.path.join(db.DATA_DIR, "notifier_state.json")

# Окно срабатывания для времени (кормление/лекарства):
# слот считается «просроченным и подлежащим уведомлению», если сейчас
# не позднее чем WINDOW минут после него. Планировщик запускается
# каждые 15 минут -> окно 30 мин покрывает гарантированно.
WINDOW_MINUTES = 30


def _load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(state: dict):
    try:
        os.makedirs(db.DATA_DIR, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except OSError:
        pass


def _prune_state(state: dict, today: str) -> dict:
    """Храним только ключи с сегодняшней датой — самозатирающееся."""
    return {k: v for k, v in state.items() if today in k}


def scan(now=None) -> list[dict]:
    """Возвращает список событий {key, text}, подлежащих уведомлению,
    и сразу помечает их в state (дедупликация)."""
    now = now or _dt.datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    state = _prune_state(_load_state(), today_str)
    events = []

    def due(key: str) -> bool:
        if key in state:
            return False
        state[key] = 1
        return True

    pets = db.get_pets()
    for pet in pets:
        pid, name = pet["id"], pet["name"]

        # --- кормление по расписанию ---
        for f in db.get_feedings(pid):
            hh, mm = _parse_hhmm(f["time"])
            if hh is None:
                continue
            slot = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if slot <= now <= slot + _dt.timedelta(minutes=WINDOW_MINUTES):
                key = f"feeding:{f['id']}:{today_str}:{hh:02d}:{mm:02d}"
                note = f" ({f['note']})" if f["note"] else ""
                if due(key):
                    events.append({
                        "key": key,
                        "text": f"Пора покормить {name}{note}",
                        "pet_id": pid,
                    })

        # --- лекарства ---
        for m in db.get_meds(pid):
            if not m["active"]:
                continue
            hh, mm = _parse_hhmm(m["time"])
            if hh is None:
                continue
            slot = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if slot <= now <= slot + _dt.timedelta(minutes=WINDOW_MINUTES):
                key = f"med:{m['id']}:{today_str}:{hh:02d}:{mm:02d}"
                if due(key):
                    events.append({
                        "key": key,
                        "text": f"Приём лекарства: {m['title']} — {name}",
                        "pet_id": pid,
                    })

        # --- день рождения ---
        if is_birthday_today(pet["birth_date"], now.date()):
            key = f"bday:{pid}:{today_str}"
            if due(key):
                events.append({
                    "key": key,
                    "text": f"Сегодня день рождения {name}! Поздравьте любимца",
                    "pet_id": pid,
                })

        # --- диета: день взвешивания ---
        diet = db.get_active_diet(pid)
        if diet:
            start = parse_date(diet["start_date"])
            if start and diet["days"] > 0:
                end = start + _dt.timedelta(days=diet["days"])
                if end == now.date():
                    key = f"diet:{diet['id']}:{today_str}"
                    if due(key):
                        events.append({
                            "key": key,
                            "text": f"Диета «{diet['title']}» для {name} "
                                    f"завершена — взвесьте питомца!",
                            "pet_id": pid,
                        })

    _save_state(state)
    return events


def _parse_hhmm(s: str):
    """'09:30' -> (9, 30) | (None, None)."""
    try:
        parts = str(s).strip().split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError, AttributeError):
        return None, None


def system_notify(title: str, text: str) -> bool:
    """Системный Windows-тост (winotify). Работает из любого процесса."""
    try:
        from winotify import Notification
        n = Notification(app_id="RubikonApp", title=title, msg=text)
        n.show()
        return True
    except Exception:
        return False


def run_once() -> int:
    """Точка входа для notifier.py (Планировщик Windows).
    Никогда не падает наружу: ошибка -> журнал data/notifier.log."""
    try:
        events = scan()
        fired = 0
        for ev in events:
            if system_notify("Рубиконт-Агент", ev["text"]):
                fired += 1
        _log(f"scan: {len(events)} событий, отправлено {fired}")
        return fired
    except Exception as e:  # noqa: BLE001
        _log(f"ERROR: {e}")
        return 0


def _log(line: str):
    try:
        os.makedirs(db.DATA_DIR, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join(db.DATA_DIR, "notifier.log"),
                  "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {line}\n")
    except OSError:
        pass
