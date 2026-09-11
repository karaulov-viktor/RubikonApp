# RubikonApp (Rubikon_vet) — Контекст беседы
## Чекпоинт: 2026-09-11 — преемник чекпоинта от 2026-09-06 (rubikon_context_v2.md)

---

## Профиль пользователя
- Статус: самоучка, начальный уровень Python/Kivy; цель — рабочее приложение для ветеринарного производства
- Роль ассистента (Super Z): менторская. У каждой команды — пояснение «что делает»; мини-уроки по ходу; засыпки-загадки в конце ответа; честное признание своих ошибок; все задачи фиксируются в worklog
- Работа с БД: SQLiteStudio

## Машины и окружения (КРИТИЧНО: патч ставится на КАЖДОЕ окружение!)
| Машина | Проект | Python | GPU | Патч FBO |
|---|---|---|---|---|
| Основная (I:) | I:\Rubikon_vet | D:\PYTHON\python.exe, 3.11.3 | NVIDIA GT 710, драйвер 475.14, OpenGL 4.6 | УСТАНОВЛЕН (проверено 2026-09-11: диалог открылся без краша) |
| Вторая (D:) | D:\Rubikon_vet | python 3.12.6 | Intel UHD 630 | Ставить при возврате к этой машине |

- Патч: fix_kivymd_fbo.py (в корне пакета rubikon_history_v2.zip). Запуск тем же python, которым запускается приложение. Меняет Fbo(size=self.size) → Fbo(size=[50]*2) в site-packages/kivymd/uix/behaviors/ripple_behavior.py (init_fbos). Бэкап .bak, идемпотентен. Стирается при переустановке KivyMD!

## Источник истины
- GitHub: https://github.com/karaulov-viktor/RubikonApp (ветка main)
- Локальный клон ассистента: /home/z/my-project/repos/RubikonApp
- Актуальный коммит на 2026-09-11: 40f2d99 «работа с карточкой питомца»
- Пользователь откатился к этой версии 2026-09-11; все правки выдаются от базовой коммитной версии
- ВАЖНО: data/rubikon.db затрекан git — откат/синхронизация перетирает базу! Спасают бэкапы backup/rubikon.db.bak-* (папка backup/ вне git, создаётся при каждом старте приложения)

## Установленный поверх репо пакет: rubikon_history_v2.zip (v2.1, 2026-09-11)
- screens/pet_detail.py — переписан: карточки лечения/истории adaptive_height, тап по записи → экран деталей (MDDialog удалены), _wrap_label c bind width→text_size, _grow_with_content (карточки рождаются с ненулевой высотой — защита от FBO)
- screens/appointment_detail.py + kv/appointment_detail.kv — НОВЫЙ экран «Детали назначения»: пары «подпись → значение», заголовок по центру (halign + text_size: self.width, None), стрелка ← назад
- kv/pet_detail.kv — text_size для переносов, spacing 10 между карточками
- main.py (+импорт/+load_file appointment_detail), kv/root.kv (+экран "appointment_detail")
- v2.1: шапка appointment_detail БЕЛАЯ (md_bg_color 1,1,1), стрелка и заголовок — фирменный зелёный 0.18,0.49,0.2,1 (≈#2E7D33)
- Проверено пользователем: история разворачивается, тап открывает экран, «работает»

## Структура проекта
```
Rubikon_vet/
├── main.py              # RubikonApp, бэкап БД при старте, show_toast (Label, БЕЗ MDSnackbar — обход FBO), ScreenManager, MDNavigationBar
├── models/database.py   # SQLite; py_lower(); get_all_drugs, get_drugs_for_species, search_drugs, get_drug_by_id; pets CRUD; reminders (active/fired/mark/archive); prescriptions (add/get_for_pet)
├── screens/             # splash, catalog, drug_detail, calculator, calendar, profile, pet_form, pet_detail, appointment_detail(новый)
├── kv/                  # root, splash, catalog, drug_detail, calculator, calendar, profile, pet_form, pet_detail, appointment_detail(новый)
├── img/                 # фото препаратов (12 шт)
├── media/pets/          # фото питомцев — КОПИИ, в БД ОТНОСИТЕЛЬНЫЙ путь (флешка меняет букву — не убить)
├── data/rubikon.db      # ⚠ в git — риск перетирания при синхронизации
├── backup/              # бэкапы БД при каждом старте (вне git)
└── fix_kivymd_fbo.py    # патч библиотеки (дубль в пакете)
```

## Схема БД (models/database.py, коммит 40f2d99)
- **drugs**: id, name, category, description, instruction, image, icon("pill"), dose_per_kg, concentration, duration_days(7), species_list
- **pets**: id, name(NOT NULL), species, breed, size, age(INTEGER), weight(REAL), history, photo, icon("paw") — 10 колонок! Экраны берут явные 9 (без icon)
- **reminders**: id, pet_id FK, drug_id FK, start_date, end_date, time, last_fired
- **prescriptions**: id, pet_id FK, drug_id FK, prescribed_date, dose_per_kg, concentration, duration_days, notes

## Что работает (2026-09-11)
- [x] Splash → каталог; нижняя навигация (Каталог/Профиль/Калькулятор/Календарь)
- [x] Каталог препаратов из БД + поиск; карточка препарата с markup-инструкциями (зелёные заголовки, красные противопоказания, РЕКВИЗИТЫ, дисклеймер); «Рассчитать дозу» → калькулятор
- [x] Калькулятор: 20 кг / 5 мг/кг / 50 мг/мл → 100 мг / 2 мл (эталонный тест)
- [x] Календарь: напоминания (таблица reminders), отметки о приёме
- [x] Профиль: карточки питомцев с фото; FAB → анкета; создание питомца (проверено: «Кузя» добавлен)
- [x] pet_detail: карточка питомца, «Подходящие препараты» (get_drugs_for_species), лечение (reminders), «Отметить напоминание в календаре», ИСТОРИЯ НАЗНАЧЕНИЙ 2.0 (тап → экран деталей)
- [x] pet_form: анкета с выбором фото (tkinter.filedialog)
- [x] Удаление питомца: dialog «Удалить питомца?» — код правильный, но требуется ИМПОРТ-ФИКС (см. Мины, №1 — только что найдено)

## КРИТИЧЕСКИЙ БАГ KivyMD 2.0.0: FBO 36054 (закрыт патчем, но помнить!)
- Симптом: `FBO Initialization failed: Incomplete attachment (36054)` при создании MDCard/MDSnackbar/MDDialog с нулевой высотой в момент рождения
- Механизм: M3CommonRipple.__init__ вызывает init_fbos() → Fbo(size=self.size); kv-правила вида «height: self.minimum_height» дают 0 при рождении детей → GL отказывается создавать пустую текстуру. GT 710 (475.14) и Intel UHD 630 — стабильно
- Лечения: (1) патч site-packages (стоит); (2) не создавать карточки с height=0 — новые pet_detail рождает их с расчётной высотой (_grow_with_content)

## Критические правила KivyMD 2.0.0 (проверены по исходнику)
- **MDDialog принимает ТОЛЬКО служебные классы**: MDDialogIcon/HeadlineText/SupportingText/ContentContainer/ButtonContainer (позиционными детьми). Сырой MDBoxLayout уходит super().add_widget() МИМО контейнеров → все отсеки пустые, карточка схлопывается, тексты теряются (было: «белая колбаска с Закрыть»). MDDialog(content) = позиционный аргумент = add_widget
- **halign без text_size не работает**: текстовый бокс равен тексту. Центрирование = пары `halign:"center"` + `text_size: self.width, None`; перенос = то же самое (bind width→text_size для динамических карточек)
- **adaptive_height** (MDAdaptiveWidget): у Label работает из коробки (text_size по умолчанию), у контейнеров = size_hint_y None + bind minimum_height. Пустой контейнер с adaptive_height → высота 0
- **height карточки с padding**: minimum_height НЕ включает свой padding → финальная высота = minimum_height + padding_v. Плюс kv-виджет рождается 100x100 — это спасает от FBO
- **Цвета Kivy**: RGBA float 0.0–1.0 (не hex). Фирменный зелёный 0.18,0.49,0.2,1; красный удаления (0.85,0.25,0.25,1)
- **Составные кнопки**: MDButton(MDButtonText(...), style="filled"|"tonal"|"text"...), иконки MDIconButton(icon=...); MDIcon живёт в kivymd/uix/label (НЕ kivymd.uix.icon!)
- **Kivy 2.3.1**: Builder из kivy.lang; в kv НЕТ тега [br] — перенос это настоящий \n
- **Deprecation padding_x на MDLabel** — шум библиотеки, игнорировать

## История ошибок (уроки)
1. KivyMD 2.0.0 FBO 36054 на MDSnackbar/MDDialog/MDCard → патч ripple_behavior.py (официальное решение из master)
2. Импорт MDIcon из kivymd.uix.icon (модуля нет в 2.0.x) → from kivymd.uix.label import MDIcon, MDLabel
3. MDDialog с сырым MDBoxLayout (старый pet_detail) → визуальный мусор «колбаска с Закрыть» → редизайн на экран appointment_detail
4. NameError MDDialogHeadlineText (profile.py:15 импортирован только MDDialog) → добавить 3 класса в импорт. УРОК: ruff check перед запуском ловит F821 Undefined name
5. Клик по MDIconButton внутри кликабельной MDCard НЕ просачивается в карточку (ButtonBehavior: дети-приоритет) — конфликтов нет, проверено по исходникам
6. Откат git вернул и data/rubikon.db → записи после коммита пропали; фото media/ и backup/ не тронуты (вне git)

## Архитектурные решения
- **Фото питомцев**: копия в media/pets/pet-{штамп}{ext}, в БД относительный путь, чтение через BASE_DIR (не доверять CWD)
- **Инструкции препаратов**: текст в БД с Kivy-markup (зелёные заголовки #177300, красные противопоказания #b3261e, «•»-списки, секция РЕКВИЗИТЫ, дисклеймер); без PDF
- **Toasts**: app.show_toast — самодельный Label поверх окна (БЕЗ MDSnackbar — обход FBO); 5 сек несмотря на комментарий «2.5»
- **История назначений**: тап открывает ЭКРАН appointment_detail (не диалог); карточки историй несут _detail-словарь с данными
- **Расчёт объёма**: dose_mg = вес × dose_per_kg; объём = dose_mg / concentration

## Открытые мины (план следующего занятия)
1. ⚠ СЕЙЧАС: profile.py:15 — импорт только MDDialog, confirm_delete использует MDDialogHeadlineText/SupportingText/ButtonContainer → NameError при клике корзины. ФИКС ВЫДАН (строка 15 → 4 класса)
2. **5 мин режима редактирования питомца** (pet_form/profile репо-версии):
   - go_back() не сбрасывает editing_pet_id → отмена правки + FAB = UPDATE чужой карточки (сценарий-ужастик подтверждён архитектурно)
   - FAB open_create() не сбрасывает режим
   - Заголовок/кнопка формы не переключаются на «Изменение карточки» (id label_title/btn_save_text в kv есть, python молчит)
   - Нет валидации пустой клички (SQLite NOT NULL пропускает "")
   - str(age) if age else "" съедает возраст 0; нужен guard `"" if age is None else str(age)`
3. data/rubikon.db + .bak затреканы git (бинарные диффы, перетирание баз) → git rm --cached + .gitignore
4. .idea затрекана до добавления в .gitignore
5. requirements.txt отсутствует; KivyMD 2.0.0 устаревшая — обновление закроет FBO-баг изкоробки (но патч/код уже страхуют)
6. Косметика: шапка «Карточки питомца» (pet_detail) всё ещё зелёная — унифицировать с белой шапкой appointment_detail?
7. Техдолг: splash.py-дубль класса, pet_name/drug_name unused в calendar.py, комментарий «2.5 сек» у show_toast

## Инструменты ассистента (наследуются между сессиями)
- worklog: /home/z/my-project/worklog.md (Task ID 0–73; хронология всех решений)
- Клон репо: /home/z/my-project/repos/RubikonApp (сброшен к 40f2d99, чистый)
- Тест-стенд: /home/z/my-project/scripts/_kivymd_check/ (venv Python 3.12 + KivyMD master 2.0.1.dev0 исходники для сверок; pyflakes установлен в venv)
- Архив прошлых выдач: /home/z/my-project/scripts/_archive_download_20260911/ (старые эталоны calculator/drug_detail/pet_form — СПРАВОЧНИК, не истина)
- Актуальная поставка: /home/z/my-project/download/rubikon_history_v2.zip (v2.1) + rubikon_context_v3.md
- Доставка файлов пользователю: панель файлов чата НЕ работает → gofile.io (curl -F file=@... https://store1.gofile.io/uploadFile)

## Чекпоинты
- 2026-09-04: rubikon_context.md (Спринт 2, итерация 3)
- 2026-09-06: rubikon_context_v2.md (итерация 4; калькулятор, drug_detail-разметка)
- 2026-09-11: ЭТОТ ФАЙЛ (репо 40f2d99; FBO-патч; история 2.0 + appointment_detail; шапка белая; импорт-фикс удаления)
