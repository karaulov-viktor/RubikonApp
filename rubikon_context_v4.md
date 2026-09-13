# RubikonApp (Rubikon_vet) — Контекст беседы
## Чекпоинт v4: 2026-09-13 — преемник чекпоинта от 2026-09-11 (rubikon_context_v3.md)

> ИНСТРУКЦИЯ НОВОЙ СЕССИИ (для ассистента): этот файл — единственный источник
> контекста, песочница между беседами очищается. Порядок старта:
> 1) прочитать файл целиком; 2) создать worklog.md и перенести раздел «История задач»;
> 3) git clone https://github.com/karaulov-viktor/RubikonApp + git fetch — сверить
> актуальный коммит (пользователь пушит между сессиями, цифры ниже могут отстать);
> 4) продолжить с раздела «Открытые дела». Язык — русский, стиль менторский,
> в конце каждого ответа — «засыпка на подумать».

---

## Профиль пользователя
- Статус: самоучка, начальный уровень Python/Kivy; цель — рабочее приложение для ветеринарного производства
- Город: Витебск, Беларусь (важно для оценок рынка/стоимости — см. Task 83)
- Роль ассистента (Super Z): менторская. Пояснение «что делает» у каждого блока; мини-уроки по ходу; «засыпка на подумать» в конце ответа; честное признание ошибок; все задачи по Task-номерам с фиксацией в worklog.md
- Ритуал пользователя: коммит перед установкой каждого пакета («сохраниться перед битвой»)
- Работа с БД: SQLiteStudio; запуск: PyCharm, D:\PYTHON\python.exe (3.11.3)

## Машины и окружения (КРИТИЧНО: патч ставится на КАЖДОЕ окружение!)
| Машина | Проект | Python | GPU | Патч FBO |
|---|---|---|---|---|
| Основная (I:) | I:\Rubikon_vet | D:\PYTHON\python.exe, 3.11.3 | NVIDIA GT 710, драйвер 475.14, OpenGL 4.6 | УСТАНОВЛЕН (2026-09-11) |
| Вторая (D:) | D:\Rubikon_vet | python 3.12.6 | Intel UHD 630 | Ставить при возврате к этой машине |

- Патч: fix_kivymd_fbo.py (лежал в корне пакета rubikon_history_v2.zip). Запуск тем же python, которым запускается приложение. Меняет Fbo(size=self.size) → Fbo(size=[50]*2) в site-packages/kivymd/uix/behaviors/ripple_behavior.py (init_fbos). Бэкап .bak, идемпотентен. Стирается при переустановке KivyMD!

## Источник истины
- GitHub: https://github.com/karaulov-viktor/RubikonApp (ветка main)
- Актуальный коммит на 2026-09-13: **891b9d7 «картинки без фона»**
- Цепочка: 40f2d99 → caeae0e → 00b0dfd → e42e6d6 (спринт 2.6 «Детали назначения») → 891b9d7
- ПРАВИЛО: перед сборкой любого пакета — git fetch и сверка origin/main. Урок Task 80: пакет v1, собранный с 40f2d99, затёр 3 новых коммита пользователя → FactoryException
- data/rubikon.db в git: откат/синхронизация перетирает базу! Спасают бэкапы backup/rubikon.db.bak-* (папка backup/ вне git, создаётся при каждом старте приложения)

## Текущее состояние (что УСТАНОВЛЕНО у пользователя на 2026-09-13)
- Редизайн «PetsHealth» v2: палитра-токены в models/theme.py; перекрашены 9 kv + 7 py (каталог, профиль, календарь, калькулятор, анкета, карточка питомца, карточка препарата, детали назначения)
- 61 фото препаратов .PNG без белого фона в img/drugs/; пути .png в БД 61/61 (jpg = 0)
- Recolor разметки Tilda в БД: #177300 → #1F7F9C (61 запись, скрипт выполнен)
- Фикс режима редактирования питомца (5 дыр: go_back без сброса, FAB без сброса, мёртвые label_title/btn_save_text, нет валидации клички, str(age) ест 0)
- Фикс сброса поисковой строки при переходе в карточку препарата (catalog.py)
- Фикс путей фото: models/image_utils.py → drug_image_source() через BASE_DIR
- Каталог: 61 препарат (импорт из 2 CSV Tilda: Кошки 25 + Собаки 59, пересечение 23 по UID)
- НЕ УСТАНОВЛЕНО: **main.py v2-версии** (у пользователя main.py от e42e6d6: clearcolor белый 1,1,1,1, дефолтная палитра, старый комментарий «2.5с». Приложение при этом работает — импорт appointment_detail в нём есть. Замена безопасна: в v2-main импорт тоже есть)

## Палитра PetsHealth (models/theme.py) — ЕДИНЫЙ источник цветов
| Токен | Значение | Назначение |
|---|---|---|
| BG | #F3F7FA | фон окон |
| CARD / CARD_BORDER | #FFFFFF / #E7EDF2 | карточки + их обводка |
| PRIMARY | #2FA5C5 | акценты, иконки |
| PRIMARY_DARK | #1F7F9C | заголовки, титулы полей |
| PRIMARY_SOFT | #E3F3F9 | фоновые подложки |
| TEXT_MAIN / TEXT_SUB | #1F2A33 / #8A97A6 | основной/вторичный текст |
| MINT | #D9F2E7 / #27996F | успех |
| DANGER | #E25C5C | удаление, противопоказания |
- Перекраска экрана = замена старых локальных констант (GREEN_DARK/GREEN_BG/GREY_BG/GREY_TEXT/DARK_TEXT) на импорт токенов; в kv — `#:import C models.theme` → `C.PRIMARY` и т.д.
- Старый фирменный зелёный (0.18,0.49,0.2,1 ≈ #2E7D33) и #177300 — ЛЕГАТ (не использовать)

## Структура проекта
```
Rubikon_vet/
├── main.py              # RubikonApp; бэкап БД при старте; show_toast (Label, БЕЗ MDSnackbar); ScreenManager; MDNavigationBar. ⚠ у пользователя СТАРАЯ версия (v2 не установлен)
├── models/
│   ├── database.py      # SQLite; py_lower(); get_all_drugs, get_drugs_for_species, search_drugs, get_drug_by_id; pets CRUD; reminders (active/fired/mark/archive); prescriptions
│   ├── theme.py         # НОВОЕ: токены палитры PetsHealth (см. таблицу выше)
│   └── image_utils.py   # НОВОЕ: drug_image_source() — BASE_DIR + exists-check + fallback img/logo.png
├── screens/             # splash, catalog, drug_detail, calculator, calendar, profile, pet_form, pet_detail, appointment_detail
├── kv/                  # root, splash, catalog, drug_detail, calculator, calendar, profile, pet_form, pet_detail, appointment_detail
├── img/drugs/           # 61 PNG препаратов (без белого фона)
├── media/pets/          # фото питомцев — КОПИИ, в БД ОТНОСИТЕЛЬНЫЙ путь
├── data/rubikon.db      # ⚠ в git (решено оставить осознанно — см. Открытые дела №2)
├── backup/              # бэкапы БД при каждом старте (вне git)
└── fix_kivymd_fbo.py    # патч библиотеки
```

## Схема БД (models/database.py)
- **drugs**: id, name, category, description, instruction, image, icon("pill"), dose_per_kg, concentration, duration_days(7), species_list — 61 запись; ⚠ dose_per_kg>0 = 0 из 61, concentration>0 = 0 из 61 (калькулятор «мёртв» без данных); категория «Прочее» у 48 из 61
- **pets**: id, name(NOT NULL), species, breed, size, age(INTEGER), weight(REAL), history, photo, icon("paw") — 10 колонок; экраны берут явные 9 (без icon)
- **reminders**: id, pet_id FK, drug_id FK, start_date, end_date, time, last_fired
- **prescriptions**: id, pet_id FK, drug_id FK, prescribed_date, dose_per_kg, concentration, duration_days, notes
- species-нормализация: Собака, Кошка, Птица, КРС, Свинья, МРС, Лошадь (7 видов)

## Что работает (2026-09-13)
- [x] Splash → каталог; нижняя навигация (Каталог/Профиль/Калькулятор/Календарь)
- [x] Каталог 61 препарат + поиск (со сбросом строки при уходе в карточку); карточка с markup-инструкциями (бирюзовые заголовки #1F7F9C, красные противопоказания, РЕКВИЗИТЫ, дисклеймер); «Рассчитать дозу» → калькулятор
- [x] Калькулятор: 20 кг / 5 мг/кг / 50 мг/мл → 100 мг / 2 мл (эталонный тест)
- [x] Календарь: напоминания, отметки о приёме
- [x] Профиль: карточки питомцев; FAB → анкета (сброс режима); редактирование; удаление (импорт-фикс)
- [x] pet_detail: карточка, «Подходящие препараты», лечение, история назначений 2.0 (тап → appointment_detail)
- [x] pet_form: анкета с фото (tkinter.filedialog), валидация клички, guard age/weight
- [x] Редизайн PetsHealth на всех экранах (v2)
- [ ] Чек-лист 10 тестов из README v2 — НЕ подтверждён пользователем

## КРИТИЧЕСКИЙ БАГ KivyMD 2.0.0: FBO 36054 (закрыт патчем, но помнить!)
- Симптом: `FBO Initialization failed: Incomplete attachment (36054)` при создании MDCard/MDSnackbar/MDDialog с нулевой высотой
- Механизм: M3CommonRipple.__init__ → init_fbos() → Fbo(size=self.size); kv-правила «height: self.minimum_height» дают 0 при рождении → GL отказывается создавать пустую текстуру. GT 710 (475.14) и Intel UHD 630 — стабильно
- Лечения: (1) патч site-packages (стоит на основной машине); (2) не создавать карточки с height=0 (_grow_with_content в pet_detail)

## Критические правила KivyMD 2.0.0 (проверены по исходнику)
- **MDDialog принимает ТОЛЬКО служебные классы**: MDDialogIcon/HeadlineText/SupportingText/ContentContainer/ButtonContainer. Сырой MDBoxLayout уходит мимо контейнеров → пустые отсёки. MDDialog(content) = позиционный аргумент = add_widget
- **halign без text_size не работает**: центрирование/перенос = пары `halign` + `text_size: self.width, None` (для динамических карточек — bind width→text_size); вертикальное центрирование в фиксированной строке = `valign:"middle"` + `text_size: self.width, self.height`
- **adaptive_height** (MDAdaptiveWidget): у Label из коробки, у контейнеров = size_hint_y None + bind minimum_height
- **height карточки с padding**: minimum_height НЕ включает свой padding → высота = minimum_height + padding_v; kv-виджет рождается 100x100 — это спасает от FBO
- **Цвета Kivy**: RGBA float 0.0–1.0 (не hex)
- **Составные кнопки**: MDButton(MDButtonText(...), style="filled"|"tonal"|"text"...); MDIcon живёт в kivymd/uix/label (НЕ kivymd.uix.icon!)
- **Kivy 2.3.1**: в kv НЕТ тега [br] — перенос это настоящий \n
- **Deprecation padding_x на MDLabel** — шум библиотеки, игнорировать

## Железные правила сессий 74–83 — НЕ НАРУШАТЬ
1. **SQL для SQLiteStudio — БЕЗ BEGIN/COMMIT** (студия сама открывает транзакцию → «cannot start a transaction within a transaction»). Проверять КАЖДЫЙ пакет при сборке (ловили дважды: Task 79 и 81)
2. **git fetch перед сборкой пакета** — пользователь пушит между сессиями, чекпоинт-коммит устаревает (Task 80)
3. **QA-пайплайн пакета**: `python -m py_compile` → pyflakes (ложные срабатывания на импорты в main.py для kv-Factory — известный техдолг, не чинить) → kivy `Parser(content=...)` по всем kv. Нюансы: правильный API — Parser(content=...); `#:import` исполняется РЕАЛЬНО → нужен sys.path.insert(0, staging)
4. **zip без мусора**: py_compile создаёт __pycache__ → исключать из архива (было 31 файл вместо 21)
5. **.gitignore не действует на уже отслеживаемые файлы** → только git rm --cached
6. **Данные — относительные пути в БД; чтение — всегда через BASE_DIR** (drug_image_source); не доверять CWD (запуск из чужой папки)
7. **Доставка файлов**: только gofile legacy-эндпоинт: `curl --http1.1 -H "Expect:" -F "file=@..." https://store1.gofile.io/uploadFile`. tmpfiles.org у провайдера пользователя ЗАБЛОКИРОВАН; без -H "Expect:" большие файлы падают (100-continue)
8. **MultiEdit не атомарен** (применяет до первой ошибки); после копии файла проверять, что правка не дублирует существующее (дважды ловили дубли импорта); после перекраски — контрольный rg по старым цветам
9. Ритуал сборки пакета: staging-папка → QA → zip → gofile → README с чек-листом тестов и инструкцией отката (`git checkout <коммит> -- <файлы>`)

## Архитектурные решения
- **Фото**: копия в media/pets (питомцы) / img/drugs (препараты); в БД относительный путь; чтение через BASE_DIR (флешка меняет букву — не убить)
- **Инструкции препаратов**: текст в БД с Kivy-markup (бирюзовые заголовки #1F7F9C, красные противопоказания #b3261e, «•»-списки, секция РЕКВИЗИТЫ, дисклеймер); без PDF; «дизайн живёт в данных» — перекраска через SQL REPLACE
- **Toasts**: app.show_toast — самодельный Label поверх окна (БЕЗ MDSnackbar — обход FBO); 5 сек (в v2-main комментарий «2.5с» поправлен)
- **История назначений**: тап открывает ЭКРАН appointment_detail (не диалог); карточки несут _detail-словарь
- **Расчёт объёма**: dose_mg = вес × dose_per_kg; объём = dose_mg / concentration
- **Импорт main.py**: классы экранов импортируются в main.py только для регистрации в Factory (kv ссылается по имени) — удаление импорта = FactoryException «Unknown class»

## Отчёт об оценке стоимости (Task 83, готов — PDF 10 стр.)
- Файл: RubikonApp_otchet_ocenki_stoimosti.pdf (download/, 229 КБ, обложка «Crystal Blue», TOC, 4 таблицы, диаграмма готовности)
- Фактура проекта: 2546 py + 1371 kv строк, 9 экранов, 4 таблицы БД, 61 препарат, 7 видов
- Вердикты: desktop-MVP «как есть» $1.5–3k; готовый desktop $3–5k; мобильный продукт с пилотом $5–10k; капитализация при 500 подписчиках $9–27k; сейчас как бизнес ≈ 0 — ценность в портфолио (+$200–400 к офферу джуна)
- Рынок РБ: junior $700–1500/мес, middle $1700–3000/мес; MVP-контракты от $3k; ориентир SaaS — Vetmanager 1092–3828 RUB/мес; ВГАВМ (Витебск) ~3500 студентов; в Витебске 10+ ветклиник (потенциал пилота)
- Трудозатраты: 200–280 ч — текущий MVP; 320–460 ч — готовый мобильный продукт

## Открытые дела (план следующей сессии)
1. **Пользователю: заменить main.py на v2-версию** (файл в пакете rubikon_redesign_v2.zip, ссылка ниже) — безопасно, импорт appointment_detail там есть. Даст: фон BG, палитру Cyan 600, исправленный комментарий тоста
2. **Пользователю: чистка репо (36 МБ мусора)** — команды выданы 2026-09-13:
   `git rm --cached` на: rubikon_drugs_png_v1.zip, rubikon_drugs_v1.zip, rubikon_history_v2.zip, rubikon_redesign_v2.zip, "rubikon_redesign_v2 (1).zip", папки пакетов rubikon_drugs_v1/ rubikon_drugs_png_v1/ rubikon_redesign_v1/ rubikon_redesign_v2/, 2 CSV store-23222356-*.csv, .idea/ (рекурсивно)
   + .gitignore дополнить: `*.zip`, `store-*.csv`, папки пакетов. По data/rubikon.db — РЕШЕНО: оставить в git (единственный облачный бэкап учебного проекта), коммитить осознанно отдельными коммитами «база: …»
3. **Прогнать и подтвердить чек-лист 10 тестов** из README v2
4. **Контент БД** (руками в SQLiteStudio): заполнить dose_per_kg/concentration (сейчас 0 у всех — калькулятор не работает по-настоящему), проставить категории (48 «Прочее»)
5. Техдолг: calendar.py (unused pet_name/drug_name), ревизия requirements.txt (KivyMD 2.0.0 устаревшая — обновление закроет FBO-баг изкоробки, но патч/код уже страхуют)
6. Идея на будущее: мобильная версия (оценка — в PDF, раздел 4)

## Пакеты и доставки (история)
| Пакет | Ссылка | Статус |
|---|---|---|
| rubikon_redesign_v2.zip (21 файл, 40 КБ) | https://gofile.io/d/KUlRVhRI | УСТАНОВЛЕН, кроме main.py |
| rubikon_drugs_png_v1.zip (61 PNG + SQL) | https://gofile.io/d/V2sHjxAi | УСТАНОВЛЕН |
| rubikon_redesign_v1 | https://gofile.io/d/IS3yflOi | поглощён v2 |
| rubikon_editmode_v1 | https://gofile.io/d/CEfFfb3J | установлен (Task 74) |
| rubikon_imgfix_v1 | https://gofile.io/d/2KzDi9Ap | установлен (Task 76) |
| rubikon_drugs_v1 | https://gofile.io/d/lAk0OlcE | установлен (Task 75) |
- Старые gofile-ссылки могут умереть — всё актуальное уже в git у пользователя (891b9d7)
- Локальные копии пакетов: download/*.zip (уцелели) и scripts/rubikon_redesign_v2/ (staging — эталон v2)

## Инструменты ассистента (создать заново при старте сессии)
- worklog: /home/z/my-project/worklog.md — создать и перенести туда «Историю задач» (раздел ниже)
- Клон: /home/z/my-project/repos/RubikonApp — git clone, затем git fetch и checkout актуального коммита
- QA: scripts/qa_kv_v2.py (Parser по 9 kv; помнит sys.path-трюк)
- Staging последнего пакета: scripts/rubikon_redesign_v2/ — эталон всех v2-файлов
- download/ (если уцелела): отчёт PDF, zips всех пакетов, этот чекпоинт

## История задач (кратко) — перенести в worklog новой сессии
- Task 0–73: см. rubikon_context_v3.md (спринты 1–2.6: каркас, каталог, калькулятор, напоминания, карточки, история назначений, FBO-патч)
- Task 74: восстановление песочницы по v3; мины №1 (импорт диалога удаления) и №2 (режим редактирования: 5 дыр) → rubikon_editmode_v1
- Task 75: база 61 препарат из 2 CSV Tilda (слияние по UID, нормализация видов, категории, HTML→Kivy-markup, фото 800px) → rubikon_drugs_v1
- Task 76: «Not found img/drugs/...» — запуск из чужой папки; models/image_utils.py + BASE_DIR → rubikon_imgfix_v1
- Task 77: удаление белого фона у 61 фото (flood-fill от краёв, scipy, без нейросетей; QA на шахматке) → PNG + update_drugs_img_png.sql → rubikon_drugs_png_v1
- Task 78: gofile legacy-маршрут (tmpfiles заблокирован у пользователя); сброс поиска; редизайн PetsHealth (theme.py + 8 kv + 4 py) → rubikon_redesign_v1
- Task 79: «cannot start a transaction within a transaction» — SQLiteStudio auto-begin → правило «SQL без BEGIN/COMMIT»
- Task 80: FactoryException AppointmentDetailScreen — пакет v1 затёр 3 коммита; пересборка v2 от e42e6d6 (21 файл) → rubikon_redesign_v2
- Task 81: в recolor_drug_markup.sql повторилась ловушка BEGIN/COMMIT; фикс + перезалив (KUlRVhRI)
- Task 82: ревью коммита 891b9d7 — миграция подтверждена (png 61/61, recolor 61/61, исходники v2 в гите); пропуски: main.py не заменён, чистка репо не выполнена (команды выданы)
- Task 83: отчёт об оценке стоимости для рынка Беларуси/Витебска (PDF, 10 стр., навык pdf, Report + обложка T07)
- Task 84: ЭТОТ чекпоинт v4

## Чекпоинты
- 2026-09-04: rubikon_context.md (Спринт 2, итерация 3)
- 2026-09-06: rubikon_context_v2.md (итерация 4; калькулятор, drug_detail-разметка)
- 2026-09-11: rubikon_context_v3.md (репо 40f2d99; FBO-патч; история 2.0 + appointment_detail)
- 2026-09-13: **ЭТОТ ФАЙЛ** (репо 891b9d7; редизайн PetsHealth v2; PNG-миграция; каталог 61; отчёт об оценке стоимости)
