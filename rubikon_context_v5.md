# RubikonApp — чекпоинт контекста v5 (2026-09-14)

> Назначение: старт новой беседы. Загрузи этот файл ассистенту и напиши:
> «Продолжаем по чекпоинту v5». Полная история задач — worklog.md (Tasks 0–93).

## Проект

- **RubikonApp** — офлайн ветеринарное приложение для владельцев питомцев (Windows)
- Стек: Python 3.12 + Kivy 2.3.1 + **KivyMD 2.0.0 (пин, см. requirements.txt)**,
  ffpyplayer (видео), winotify (уведомления), pillow
- Данные: `data/rubikon.db` (SQLite, только локально): 61 препарат, питомцы Кузя и Тишка
- GitHub: https://github.com/karaulov-viktor/RubikonApp
- Владелец/автор коммитов: Viktor <Karaylov-Viktor@mai.ru>

## Состояние на 2026-09-14

- **Код = финальный пакет v3** (установлен пользователем): кормление по норме WSAVA
  (models/nutrition.py: RER = 70×вес^0.75, MER-коэффициенты), диеты по профилю,
  график веса v3 (Canvas, слова вместо стрелок), белые экраны, elevation 0,
  FBO-патч встроен в main.py, notifier (winotify + schtasks)
- **Песочница ассистента**: репо repos/RubikonApp собрано, коммит
  **f995d87** «Спринт 3: профили питомцев, норма кормления, диеты, график веса,
  напоминания» (50 файлов, +7034/−229) поверх 894cea3; сохранена ветка
  backup/sprint2-full-891b9d7 (старый полный проект)
- **origin/main = 894cea3** («Спринт 2», squash) — Спринт 3 туда НЕ попал
- **Пуш НЕ подтверждён** — первое действие новой беседы: проверить
  `git ls-remote https://github.com/karaulov-viktor/RubikonApp main`
  (894cea3 = не запушено; f995d87 или новее = запушено)

## Компьютеры

| Где | Что |
|-----|-----|
| Старый ПК | D:\Rubikon_vet, Python 3.12.6, venv рабочий, всё запускалось |
| НОВЫЙ ПК (текущий) | проект на флешке (буква неизвестна); Python не проверен; venv с флешки НЕ работает |
| Песочница | repos/RubikonApp с f995d87; download/RubikonApp_git_push.zip (43MB, репо с .git) |

## Развертывание на новом ПК (флешка)

```powershell
cd <буква>:\Rubikon_vet
py -0p                    # нужен Python 3.11 или 3.12 (Kivy 2.3.1 на 3.13 не встанет)
Remove-Item -Recurse -Force venv, venv_old -ErrorAction SilentlyContinue
py -3.12 -m venv venv     # или py -3.11
.\venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py            # или run.bat
```

База data/rubikon.db не трогается — миграции только ДОБАВЛЯЮТ колонки.

## Пуш Спринта 3 (вариант А — с машины пользователя, где есть .git и креды)

```powershell
cd <папка проекта>        # там, где есть .git
Add-Content .gitignore "`nvenv/`nvenv_old/"
git rm -r --cached --ignore-unmatch .idea screens/__pycache__
git add -A
git status                # в списке НЕ должно быть venv/, venv_old/, data/
git commit -m "Спринт 3: профили питомцев, норма кормления, диеты, график веса, напоминания"
git push origin main
# если push отклонён: git pull --rebase origin main, затем повторить push
```

Вариант Б: временный fine-grained токен (только этот репозиторий, Contents: Read+write,
срок 1 день, отозвать после пуша) — тогда ассистент пушит f995d87 из песочницы.

Если .git на флешке НЕТ: `git clone https://github.com/karaulov-viktor/RubikonApp`,
скопировать код с флешки поверх (всё кроме venv/data/media/backup), commit + push,
вернуть data/rubikon.db в клон.

## Правило двух ПК

- **Код** — через git (push/pull)
- **data/ (БД), media/ (фото/видео), backup/** — в git НЕ входят, возить только флешкой

## Открытые дела

1. Пуш Спринта 3 — статус неизвестен, проверить ls-remote (см. выше)
2. Прогнать чек-лист v3 из README пакета (кормление, диета, график веса)
3. Тест системных уведомлений через планировщик Windows — ещё не проверялся пользователем
4. Удалить venv_old на обоих ПК
5. Идея: скрипт бэкапа data/ на флешку одним действием

## Уроки / мины (соблюдать обязательно)

- **venv непереносим** между машинами — всегда пересоздавать
- **CREATE TABLE IF NOT EXISTS не добавляет колонки** существующим таблицам →
  миграции _ensure_columns по PRAGMA table_info (models/database.py)
- **SQLiteStudio: SQL без BEGIN/COMMIT** (auto-begin; «cannot start a transaction»)
- **KivyMD 2.0 vs 1.x**: FitImage → kivymd.uix.fitimage, MDIcon → kivymd.uix.label;
  вложенные kv-виджеты не попадают в Factory → Factory.register
- **QA-минимум пакета**: py_compile + kv Parser + import main + Xvfb smoke
  (py_compile/Parser ловят НЕ все мины)
- юникод-стрелки ↑↓ не рендерит Roboto в Kivy — писать словами
- gofile бывает недоступен; tmpfiles у пользователя заблокирован
- пуши из песочницы невозможны (нет кредов) — пушит только пользователь

## Артефакты песочницы

- `repos/RubikonApp` — коммит f995d87, готов к пушу (нужен токен)
- `download/RubikonApp_git_push.zip` — репо с .git (43 МБ): распаковать на любом ПК,
  `git push origin main`, креды возьмутся/спросятся
- `scripts/rubikon_pets_v3/` — эталонные исходники v3 (35 файлов)
- `download/rubikon_context_v5.md` — этот файл
- `worklog.md` — журнал Tasks 0–93
