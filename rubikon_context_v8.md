# RubikonApp — чекпоинт контекста v8 (2026-09-16)

> Назначение: старт новой беседы. Загрузи этот файл ассистенту и напиши:
> «Продолжаем по чекпоинту v8». Полная история задач — worklog.md.
> Предыдущий чекпоинт: rubikon_context_v7.md (всё из v7 остаётся в силе).

## Проект

- **RubikonApp** — офлайн ветеринарное приложение для владельцев питомцев (Windows)
- Стек: Python 3.12 + Kivy 2.3.1 + **KivyMD 2.0.0 (пин)**, ffpyplayer, winotify, pillow
- Данные: `data/rubikon.db` (SQLite, только локально): 61 препарат, питомцы Кузя и Тишка
- GitHub: https://github.com/karaulov-viktor/RubikonApp (пуши только с машины владельца)
- Два ПК: PC-1 `D:\Rubikon_vet` (Python 3.12.10), PC-2 `I:\Rubikon_vet` (Python 3.12.9)

## Что нового в v8 — фикс-серия «дисклеймер + калькулятор» (поверх 3145c1f)

Установка пакета «Калькулятор v2» на PC-2 вскрыла три дефекта, все
устранены; каждая версия main.py/calculator.py печатает МАРКЕР в лог —
по нему мгновенно видно, какой файл на диске.

1. **Дисклеймер пропадал**: отметка «принято» живёт в БД; при переносе
   базы экран исчезал. В main.py добавлен флаг
   `SHOW_DISCLAIMER_EVERY_LAUNCH = True` (начало файла, рядом с
   TASK_NAME) — согласие показывается при КАЖДОМ запуске.
   **ПЕРЕД РЕЛИЗОМ → False.**
2. **Краш «Принимаю»**: старый kv/disclaimer.kv зовёт
   `app.on_disclaimer_accept()`, новый — `root.app.accept_disclaimer()`.
   В main.py добавлены псевдонимы:
   `on_disclaimer_accept = accept_disclaimer`,
   `on_disclaimer_decline = decline_disclaimer` — работает любой kv.
3. **Краш тапа «Препарат» в калькуляторе**: kv/calculator.kv в
   on_focus брал `root.focus` (у экрана его нет) — исправлено на
   `self.focus` (у поля). Урок: в KV `root` = корень правила
   (экран), `self` = виджет с обработчиком.

## Маркеры сборки (диагностика за 10 секунд)

В логе при запуске должно быть ПОДРЯД:
```
[RubikonApp] FBO-патч применён (1 класс(ов))
[RubikonApp] KivyMD 2.0.0, тема whitegreen-4
[RubikonApp] main.py v2.2 — дисклеймер при каждом запуске + псевдонимы кнопок согласия
...
[calculator] v2.1 — расчёт по формам, препаратов: 61      (при первом открытии калькулятора)
```
Нет маркера — на диске старый файл. Номер строки `RubikonApp().run()`
в трейсе тоже идентифицирует сборку: 427=calc_v2, 434=фикс-1(флаг
без псевдонимов), 440=фикс-2, 444=фикс-3, далее v2.2-финал.

## Песочница и артефакты

- repos/RubikonApp: 3145c1f -> **v5-коммит** (main.py v2.2,
  kv/calculator.kv, screens/calculator.py v2.1, + fix_doses_v2.py,
  find_color_warning.py, rubikon_context_v8.md).
- download/RubikonApp_v5_git_push.zip — ПОЛНЫЙ чекпоинт (рабочее
  дерево + .git, без data/; база создаётся скриптом на месте).
- download/rubikon_v5_<hash>.patch — git-патч 3145c1f..HEAD.
- download/find_color_warning.py — сканер источников
  ColorParser-предупреждений (ищет str(цвет), f-строки, битые
  литералы в kv/py; ничего не меняет, печатает файл:строка).
- Пакеты-фиксы этой сессии (история): dmaEoB5k (calc kv fix v2.1),
  YDXOvCQl (main.py v2.2), 7ylbQ0nN/frKfs3Wh (устарели).

## Открытые дела

1. **ColorParser ×24**: `Invalid color format for '[0.0784, 0.3255,
   0.1765, 1.0'` — цвет #14532D (T.GREEN/PRIMARY) передаётся СТРОКОЙ.
   В актуальных файлах репо чисто; источник — устаревший kv на диске
   ПК. Диагностика: `python find_color_warning.py` (прислать вывод).
   Не мешает работе.
2. Пуш на GitHub (3145c1f + v5) — только с машины владельца;
   на втором ПК git pull + `python fix_doses_v2.py`.
3. Тест видео с ffpyplayer на реальном ПК; тест системных уведомлений.
4. Перед публикацией: SHOW_DISCLAIMER_EVERY_LAUNCH = False.
5. Проверка доз ветврачом (отметки ⚠ в выводе скриптов).
6. Идея: скрипт бэкапа data/ на флешку одним действием.
