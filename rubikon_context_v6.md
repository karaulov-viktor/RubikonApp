# RubikonApp — чекпоинт контекста v6 (2026-09-15)

> Назначение: старт новой беседы. Загрузи этот файл ассистенту и напиши:
> «Продолжаем по чекпоинту v6». Полная история задач — worklog.md.

## Проект

- **RubikonApp** — офлайн ветеринарное приложение для владельцев питомцев (Windows)
- Стек: Python 3.12 + Kivy 2.3.1 + **KivyMD 2.0.0 (пин, см. requirements.txt)**,
  ffpyplayer (видео), winotify (уведомления), pillow
- Данные: `data/rubikon.db` (SQLite, только локально): 61 препарат, питомцы Кузя и Тишка
- GitHub: https://github.com/karaulov-viktor/RubikonApp
- Владелец/автор коммитов: Viktor <Karaylov-Viktor@mai.ru>

## Состояние на 2026-09-15 (пакет v4)

- **origin/main = e411349** «добавление функций в карточку питомца» — Спринт 3
  УСПЕШНО ЗАПУШЕН пользователем (чекпоинт v5 это ещё не знал).
- **Песочница**: коммит **1d9ba20** «Пакет v4: просмотр фото и видео на весь
  экран, вес списком, палитра whitegreen-4» поверх e411349. **ПУША НЕТ** —
  первое действие новой беседы: `git ls-remote ... main` и сравнить с 1d9ba20.
- Палитра **whitegreen-4** (выбор владельца): белое приложение,
  тёмно-зелёные шрифты (#1B3A28), акцент #14532D, мята/бирюза убраны.
  При старте печатается `[RubikonApp] ... тема whitegreen-4`.
- График веса (Canvas) УДАЛЁН по решению владельца — остался список
  всех замеров (свежие сверху, динамика словами) + сводка.

## Что сделано в v4 (для понимания кода)

1. **Фото**: тап по плитке -> полноэкранный MediaViewerScreen
   (листание, счётчик, имя файла). AsyncImage + fit_mode="contain"
   (FitImage обрезал бы фото).
2. **Видео**: в списке БОЛЬШЕ НЕТ плееров (каждый инлайн-плеер грузил
   клип сразу — экран вис). Тап по карточке -> просмотрщик, плеер
   создаётся ОДИН и только при открытии; при закрытии unload.
   Без ffpyplayer — подсказка с командой
   `venv\Scripts\python.exe -m pip install ffpyplayer`.
3. **Вес**: секция «Вес и замеры» — id l_weight_stats (сводка) +
   weights_list (все замеры, свежие сверху).
4. **Тема**: только models/theme.py (PALETTE_VERSION = whitegreen-4);
   apply_instructions.py: #177300 -> #14532D в текстах инструкций;
   main.py: primary_hue "900", проверка версии whitegreen-4,
   media_viewer в списке «без нижнего меню» и KV_FILES.

## Компьютеры

| Где | Что |
|-----|-----|
| Старый ПК | D:\Rubikon_vet, Python 3.12.6, venv рабочий |
| НОВЫЙ ПК (текущий) | проект на флешке; venv пересоздан по инструкции v5 |
| Песочница | repos/RubikonApp с 1d9ba20; download/RubikonApp_v4_git_push.zip |

## Развертывание пакета v4 (Windows, флешка)

```powershell
cd <буква>:\Rubikon_vet
# 1) скопировать файлы пакета поверх проекта (с заменой)
# 2) обновить зависимости и установить ffpyplayer:
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m pip show ffpyplayer   # должен найтись
python main.py
```

## Пуш пакета v4 (вариант А — с машины пользователя)

```powershell
cd <папка проекта с .git>
git pull origin main                 # если на флешке старее e411349
# либо применить патч: git am rubikon_v4_1d9ba20.patch
git push origin main
```

Вариант Б: zip `download/RubikonApp_v4_git_push.zip` (репо с .git,
коммит 1d9ba20) — распаковать, `git push origin main`, креды
возьмутся/спросятся. Пуши из песочницы невозможны (нет кредов) —
пушит только пользователь.

## Правило двух ПК

- **Код** — через git (push/pull)
- **data/ (БД), media/ (фото/видео), backup/** — в git НЕ входят, возить только флешкой

## Открытые дела

1. Пуш 1d9ba20 (см. выше)
2. Тест видео с установленным ffpyplayer на реальном ПК (в песочнице
   ffpyplayer нет — проверен путь «без плеера», сам плеер нет)
3. Тест системных уведомлений через планировщик Windows
4. Идея: скрипт бэкапа data/ на флешку одним действием

## Уроки / мины (соблюдать обязательно)

- **venv непереносим** между машинами — всегда пересоздавать
- **CREATE TABLE IF NOT EXISTS не добавляет колонки** -> миграции
  _ensure_columns по PRAGMA table_info (models/database.py)
- **KivyMD 2.0**: MDIcon в kivymd.uix.label, FitImage в
  kivymd.uix.fitimage; вложенные kv-виджеты не попадают в Factory
  -> Factory.register
- **MDCard.on_release** работает (с ripple_behavior True) — тап по
  дочерней MDIconButton карточку НЕ триггерит (кнопка гасит касание)
- **Вертикальный BoxLayout**: визуальный верх = ПЕРВЫЙ добавленный
  виджет; children[0] = добавленный ПОСЛЕДНИМ (он внизу)
- **VideoPlayer без ffpyplayer** не создавать вообще — Kivy без
  провайдера ffmpeg всё равно не сыграет; плеер выгружать
  (state="stopped" + unload) при уходе с экрана
- **fit_mode="contain"** (Kivy 2.3) для просмотра фото целиком;
  FitImage = «cover», обрезает
- юникод-стрелки ↑↓ не рендерит Roboto в Kivy — писать словами
- QA-минимум: py_compile + kv Parser + import main + Xvfb smoke
  (в песочнице: qa_venv с kivy/kivymd, скрипт scripts/rubikon_qa_smoke.py)
- gofile бывает недоступен; tmpfiles у пользователя заблокирован

## Артефакты песочницы

- `repos/RubikonApp` — коммит 1d9ba20, готов к пушу (нужны креды пользователя)
- `download/RubikonApp_v4_git_push.zip` — репо с .git (58 МБ)
- `download/rubikon_v4_1d9ba20.patch` — патч для `git am` (62 КБ)
- `download/rubikon_context_v6.md` — этот файл
- `scripts/rubikon_qa_smoke.py` — smoke-тест (Xvfb), 26 проверок
- `worklog.md` — журнал работ
