# -*- coding: utf-8 -*-
"""SQLite-хранилище RubikonApp — ОБЪЕДИНЁННОЕ (спринты 1-2.6 + «Питомцы»).

К одной базе data/rubikon.db есть ДВА интерфейса:

  1. class Database — СТАРЫЙ интерфейс (каталог препаратов, лечение,
     календарь, история назначений). Один постоянный коннект, методы
     get_all_drugs(), add_reminder() и т.д. Код спринтов 1-2.6.

  2. Модульные функции — НОВЫЙ интерфейс (питомцы: галереи, диеты,
     вес, лекарства, кормление; нотификатор). Короткоживущие коннекты,
     WAL-режим: приложение и планировщик читают базу одновременно.

УРОК СПРИНТА 3 (KeyError: 'birth_date'): у пользователя таблица pets
УЖЕ существовала со старыми колонками (size/age/weight/history) —
CREATE TABLE IF NOT EXISTS её не обновил. Поэтому здесь есть
_migrate(): добавляет в pets недостающие колонки В ОБЕ СТОРОНЫ:
  - старым базам — birth_date (и защищается от NULL-видов);
  - свежим базам — size/age/weight/history/icon (нужны старым экранам).
Так оба интерфейса работают с любой базой: и со старой, и с новой.

Правила проекта:
  - ВСЕ пути к файлам в БД — ОТНОСИТЕЛЬНЫЕ (от корня проекта);
  - бэкап data/rubikon.db -> backup/ при каждом старте приложения;
  - драг-база (61 препарат) миграциями НЕ трогается вообще.
"""
import os
import shutil
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUP_DIR = os.path.join(BASE_DIR, "backup")
MEDIA_DIR = os.path.join(BASE_DIR, "media", "pets")
DB_PATH = os.path.join(DATA_DIR, "rubikon.db")


def py_lower(value):
    """SQL-функция поиска без регистра (старый каталог)."""
    if value:
        return str(value).lower()
    return value


# ------------------------------------------------------------------
# Схемы таблиц
# ------------------------------------------------------------------

# Старые таблицы (спринты 1-2.6) — схемы НЕ менялись, только
# CREATE TABLE IF NOT EXISTS для свежих установок.
SCHEMA_OLD = """
CREATE TABLE IF NOT EXISTS drugs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    description TEXT,
    instruction TEXT,
    image TEXT,
    icon  TEXT DEFAULT "pill",
    dose_per_kg REAL DEFAULT 0,
    concentration REAL DEFAULT 0,
    duration_days INTEGER DEFAULT 7,
    species_list TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    drug_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    time TEXT NOT NULL,
    last_fired TEXT,
    FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
    FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    drug_id INTEGER NOT NULL,
    prescribed_date TEXT NOT NULL,
    dose_per_kg REAL,
    concentration REAL,
    duration_days INTEGER,
    notes TEXT,
    FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
    FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
);
"""

# Новые таблицы (спринт «Питомцы»).
SCHEMA_NEW = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS pets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    species    TEXT DEFAULT 'Кошка',
    breed      TEXT DEFAULT '',
    birth_date TEXT DEFAULT '',
    photo      TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS pet_media (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id   INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    path     TEXT NOT NULL,
    kind     TEXT NOT NULL DEFAULT 'photo',
    added_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS weights (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id     INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    weighed_at TEXT NOT NULL,
    kg         REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS meds (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    title  TEXT NOT NULL,
    time   TEXT NOT NULL,
    active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS feedings (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    time   TEXT NOT NULL,
    note   TEXT DEFAULT '',
    grams  REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS diets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id     INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    start_date TEXT NOT NULL,
    days       INTEGER NOT NULL,
    active     INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
"""

# Полный набор колонок pets (объединение старой и новой схем).
# _ensure_columns() добьёт недостающие через ALTER TABLE ADD COLUMN.
PET_COLUMNS_UNION = {
    "name": "TEXT NOT NULL DEFAULT ''",
    "species": "TEXT DEFAULT 'Кошка'",
    "breed": "TEXT DEFAULT ''",
    "birth_date": "TEXT DEFAULT ''",
    "photo": "TEXT DEFAULT ''",
    "size": "TEXT DEFAULT ''",
    "age": "INTEGER",
    "weight": "REAL",
    "history": "TEXT DEFAULT ''",
    "icon": "TEXT DEFAULT 'paw'",
}

# Спринт «Кормление и диеты»: порции в расписании и цели диет.
# Свежим базам эти колонки даёт CREATE TABLE, существующим —
# _ensure_columns() через ALTER TABLE (тот же урок, что с birth_date).
FEEDING_COLUMNS_UNION = {
    "grams": "REAL DEFAULT 0",          # порция, г (0 — без нормы)
}
DIET_COLUMNS_UNION = {
    "goal": "TEXT DEFAULT ''",           # тип рациона (weight_loss/...)
    "kcal": "INTEGER DEFAULT 0",         # целевая норма, ккал/сутки
    "target_weight": "REAL DEFAULT 0",   # целевой вес, кг (0 — нет)
}


# ------------------------------------------------------------------
# Базовое: коннект, миграция, бэкап
# ------------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.create_function("py_lower", 1, py_lower)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _ensure_columns(conn: sqlite3.Connection, table: str,
                    columns: dict) -> list[str]:
    """Добавляет в таблицу недостающие колонки (ALTER TABLE ADD COLUMN).

    Возвращает список реально добавленных имён. Урок спринта 3:
    CREATE TABLE IF NOT EXISTS не обновляет существующие таблицы.
    """
    existing = {
        row[1] for row in conn.execute(f"PRAGMA table_info({table})")
    }
    added = []
    for col, ddl in columns.items():
        if col not in existing:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
            added.append(col)
    return added


def _migrate_pets(conn: sqlite3.Connection):
    """Миграция таблицы pets до объединённого набора колонок."""
    added = _ensure_columns(conn, "pets", PET_COLUMNS_UNION)
    if added:
        # у старых питомцев вид мог быть NULL — новые экраны ждут строку
        conn.execute("UPDATE pets SET species = 'Кошка' "
                     "WHERE species IS NULL OR species = ''")
        conn.execute("UPDATE pets SET breed = '' WHERE breed IS NULL")
        conn.execute("UPDATE pets SET birth_date = '' "
                     "WHERE birth_date IS NULL")
        conn.execute("UPDATE pets SET photo = '' WHERE photo IS NULL")


def init_db():
    """Создаёт все таблицы (старые + новые) и мигрирует pets."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    conn = get_conn()
    try:
        conn.executescript(SCHEMA_OLD)
        conn.executescript(SCHEMA_NEW)
        _migrate_pets(conn)
        _ensure_columns(conn, "feedings", FEEDING_COLUMNS_UNION)
        _ensure_columns(conn, "diets", DIET_COLUMNS_UNION)
        conn.commit()
    finally:
        conn.close()


def backup_db(keep: int = 20):
    """Копия БД в backup/ при каждом старте (старый ритуал проекта)."""
    if not os.path.exists(DB_PATH):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"rubikon.db.bak-{stamp}")
    try:
        shutil.copy2(DB_PATH, dest)
    except OSError:
        return None
    try:
        olds = sorted(
            f for f in os.listdir(BACKUP_DIR)
            if f.startswith("rubikon.db.bak-")
        )
        for name in olds[:-keep]:
            os.remove(os.path.join(BACKUP_DIR, name))
    except OSError:
        pass
    return dest


# ------------------------------------------------------------------
# СТАРЫЙ ИНТЕРФЕЙС: класс Database (спринты 1-2.6, код не менялся)
# ------------------------------------------------------------------
class Database:
    """SQLite база препаратов, питомцев, напоминаний и истории."""

    def __init__(self, db_path="data/rubikon.db"):
        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.create_function("py_lower", 1, py_lower)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        """Создание таблиц и миграция."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS drugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                description TEXT,
                instruction TEXT,
                image TEXT,
                icon  TEXT DEFAULT "pill",
                dose_per_kg REAL DEFAULT 0,
                concentration REAL DEFAULT 0,
                duration_days INTEGER DEFAULT 7,
                species_list TEXT DEFAULT ''
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                species TEXT,
                breed TEXT,
                size TEXT,
                age INTEGER,
                weight REAL,
                history TEXT,
                photo TEXT,
                icon TEXT DEFAULT "paw"
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pet_id INTEGER NOT NULL,
                drug_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                time TEXT NOT NULL,
                last_fired TEXT,
                FOREIGN KEY (pet_id) REFERENCES pets(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (drug_id) REFERENCES drugs(id)
                    ON DELETE CASCADE
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pet_id INTEGER NOT NULL,
                drug_id INTEGER NOT NULL,
                prescribed_date TEXT NOT NULL,
                dose_per_kg REAL,
                concentration REAL,
                duration_days INTEGER,
                notes TEXT,
                FOREIGN KEY (pet_id) REFERENCES pets(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (drug_id) REFERENCES drugs(id)
                    ON DELETE CASCADE
            )
        """)

        # Миграция pets до объединённого набора колонок (birth_date
        # для старых баз; size/age/weight/history/icon — для свежих).
        _ensure_columns(self.conn, "pets", PET_COLUMNS_UNION)

        self._seed_data()
        self.conn.commit()

    def _seed_data(self):
        """Заполнение таблицы тестовыми данными (только пустая база)."""
        self.cursor.execute("SELECT COUNT(*) FROM drugs")
        if self.cursor.fetchone()[0] > 0:
            return

        drugs = [
            ("Аспирин", "Обезболивающее",
             "Снимает боль и воспаление",
             "По 1 таблетке 2 раза в день после еды",
             "img/logo.png", "pill",
             5, 0, 5, "Собака,Кошка"),
            ("Амоксициллин", "Антибиотик",
             "Антибиотик широкого спектра для собак и кошек",
             "10 мг/кг веса 2 раза в день, курс 7 дней",
             "img/logo.png", "pill",
             10, 50, 7, "Собака,Кошка"),
            ("Фоспренил", "Противовирусный",
             "Противовирусный иммуномодулятор",
             "0,2 мл/кг подкожно 1 раз в день",
             "img/logo.png", "virus-off",
             0.2, 2.5, 5, "Собака,Кошка,Птица"),
            ("Витамин B", "Витамин",
             "Комплекс витаминов группы B",
             "1 мл на 10 кг веса внутримышечно",
             "img/logo.png", "needle",
             0, 0, 14, "Собака,Кошка,Птица"),
            ("Ивермектин", "Антипаразитарный",
             "От гельминтов и клещей",
             "0,2 мг/кг перорально однократно",
             "img/logo.png", "bug",
             0.2, 10, 3, "Собака,Кошка"),
            ("Мелоксикам", "НПВС",
             "Противовоспалительное, обезболивающее",
             "0,1 мг/кг 1 раз в день с кормом",
             "img/logo.png", "pill",
             0.1, 0.5, 5, "Собака,Кошка"),
            ("Кетопрофен 10%", "НПВС",
             "Снимает воспаление и боль",
             "3 мг/кг подкожно 1 раз в день",
             "img/logo.png", "pill",
             3, 10, 3, "Собака"),
            ("Стронгхолд", "Антипаразитарный",
             "Капли от блох, клещей, гельминтов",
             "1 пипетка на холку 1 раз в месяц",
             "img/logo.png", "bug",
             6, 60, 1, "Собака,Кошка"),
            ("Дронтал", "Антипаразитарный",
             "Таблетки от гельминтов",
             "1 таблетка на 10 кг веса однократно",
             "img/logo.png", "bug",
             0, 0, 1, "Собака"),
            ("Супрастин", "Антигистаминное",
             "При аллергиях и укусах насекомых",
             "2 мг/кг 2 раза в день",
             "img/logo.png", "pill",
             2, 25, 3, "Собака,Кошка"),
        ]
        self.cursor.executemany(
            """INSERT INTO drugs
               (name, category, description, instruction, image, icon,
                dose_per_kg, concentration, duration_days, species_list)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            drugs
        )
        self.conn.commit()

    # ═══════════════════════════════════════════════════════
    # ПРЕПАРАТЫ
    # ═══════════════════════════════════════════════════════
    def get_all_drugs(self):
        self.cursor.execute(
            """SELECT id, name, category, description, instruction,
                      image, icon, dose_per_kg, concentration,
                      duration_days, species_list
               FROM drugs ORDER BY name"""
        )
        return self.cursor.fetchall()

    def get_drugs_for_species(self, species):
        """Препараты, подходящие для данного вида животного."""
        if not species:
            return self.get_all_drugs()
        self.cursor.execute(
            """SELECT id, name, category, description, instruction,
                      image, icon, dose_per_kg, concentration,
                      duration_days, species_list
               FROM drugs
               WHERE species_list LIKE ? OR species_list = ''
               ORDER BY name""",
            (f"%{species}%",)
        )
        return self.cursor.fetchall()

    def search_drugs(self, query):
        like = f"%{query.lower()}%"
        self.cursor.execute(
            """SELECT id, name, category, description, instruction,
                      image, icon, dose_per_kg, concentration,
                      duration_days, species_list
               FROM drugs
               WHERE py_lower(name) LIKE ? OR py_lower(category) LIKE ?
               ORDER BY name""",
            (like, like)
        )
        return self.cursor.fetchall()

    def get_drug_by_id(self, drug_id):
        self.cursor.execute(
            """SELECT id, name, category, description, instruction,
                      image, icon, dose_per_kg, concentration,
                      duration_days, species_list
               FROM drugs WHERE id = ?""",
            (drug_id,)
        )
        return self.cursor.fetchone()

    # ═══════════════════════════════════════════════════════
    # ПИТОМЦЫ (старый интерфейс: кортежи из 9 полей)
    # ═══════════════════════════════════════════════════════
    def add_pet(self, name, species, breed, size, age, weight, history,
                photo=""):
        self.cursor.execute(
            """INSERT INTO pets
               (name, species, breed, size, age, weight, history, photo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, species, breed, size, age, weight, history, photo)
        )
        self.conn.commit()

    def get_pets(self):
        self.cursor.execute(
            """SELECT id, name, species, breed, size, age, weight,
                      history, photo
               FROM pets ORDER BY name"""
        )
        return self.cursor.fetchall()

    def get_pet_by_id(self, pet_id):
        self.cursor.execute(
            """SELECT id, name, species, breed, size, age, weight,
                      history, photo
               FROM pets WHERE id = ?""",
            (pet_id,)
        )
        return self.cursor.fetchone()

    def update_pet(self, pet_id, name, species, breed, size, age, weight,
                   history, photo):
        self.cursor.execute(
            """UPDATE pets
               SET name=?, species=?, breed=?, size=?,
                   age=?, weight=?, history=?, photo=?
               WHERE id=?""",
            (name, species, breed, size, age, weight, history, photo,
             pet_id)
        )
        self.conn.commit()

    def delete_pet(self, pet_id):
        self.cursor.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
        self.conn.commit()

    # ═══════════════════════════════════════════════════════
    # НАПОМИНАНИЯ (будильники лечения)
    # ═══════════════════════════════════════════════════════
    def add_reminder(self, pet_id, drug_id, start_date, end_date, time):
        self.cursor.execute(
            """INSERT INTO reminders
               (pet_id, drug_id, start_date, end_date, time)
               VALUES (?, ?, ?, ?, ?)""",
            (pet_id, drug_id, start_date, end_date, time)
        )
        self.conn.commit()

    def get_active_reminders(self):
        self.cursor.execute("""
            SELECT id, pet_id, drug_id, start_date, end_date, time
            FROM reminders ORDER BY start_date, time
        """)
        return self.cursor.fetchall()

    def delete_reminder(self, reminder_id):
        self.cursor.execute(
            "DELETE FROM reminders WHERE id = ?", (reminder_id,)
        )
        self.conn.commit()

    def is_reminder_fired_today(self, reminder_id, today_key):
        self.cursor.execute(
            "SELECT last_fired FROM reminders WHERE id = ?",
            (reminder_id,)
        )
        row = self.cursor.fetchone()
        return row and row[0] == today_key

    def mark_reminder_fired(self, reminder_id, today_key):
        self.cursor.execute(
            "UPDATE reminders SET last_fired = ? WHERE id = ?",
            (reminder_id, today_key)
        )
        self.conn.commit()

    # ═══════════════════════════════════════════════════════
    # ИСТОРИЯ НАЗНАЧЕНИЙ
    # ═══════════════════════════════════════════════════════
    def add_prescription(self, pet_id, drug_id, dose_per_kg,
                         concentration, duration_days, notes=""):
        prescribed_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute(
            """INSERT INTO prescriptions
               (pet_id, drug_id, prescribed_date, dose_per_kg,
                concentration, duration_days, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (pet_id, drug_id, prescribed_date, dose_per_kg,
             concentration, duration_days, notes)
        )
        self.conn.commit()

    def get_prescriptions_for_pet(self, pet_id):
        self.cursor.execute(
            """SELECT p.id, p.prescribed_date, d.name, d.category,
                      p.dose_per_kg, p.concentration, p.duration_days,
                      p.notes
               FROM prescriptions p
               JOIN drugs d ON p.drug_id = d.id
               WHERE p.pet_id = ?
               ORDER BY p.prescribed_date DESC""",
            (pet_id,)
        )
        return self.cursor.fetchall()

    def archive_reminder(self, reminder_id):
        """Перенести будильник в историю перед удалением."""
        self.cursor.execute(
            """SELECT pet_id, drug_id, start_date, end_date, time
               FROM reminders WHERE id = ?""",
            (reminder_id,)
        )
        row = self.cursor.fetchone()
        if not row:
            return

        pet_id, drug_id, start_date, end_date, time = row

        self.cursor.execute(
            """SELECT dose_per_kg, concentration, duration_days
               FROM drugs WHERE id = ?""",
            (drug_id,)
        )
        drug_row = self.cursor.fetchone()

        dose_per_kg = drug_row[0] if drug_row else 0
        concentration = drug_row[1] if drug_row else 0
        duration_days = drug_row[2] if drug_row else 0

        notes = f"Период: {start_date} — {end_date}, время: {time}"

        self.cursor.execute(
            """SELECT COUNT(*) FROM prescriptions
               WHERE pet_id = ? AND drug_id = ? AND prescribed_date LIKE ?""",
            (pet_id, drug_id, f"{start_date[:10]}%")
        )
        if self.cursor.fetchone()[0] > 0:
            return  # уже есть

        prescribed_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute(
            """INSERT INTO prescriptions
               (pet_id, drug_id, prescribed_date, dose_per_kg,
                concentration, duration_days, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (pet_id, drug_id, prescribed_date, dose_per_kg,
             concentration, duration_days, notes)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


# ------------------------------------------------------------------
# НОВЫЙ ИНТЕРФЕЙС: модульные функции (спринт «Питомцы», нотификатор)
# ------------------------------------------------------------------

# ------------------------------------------------------------------ settings
def get_setting(key: str, default: str = "") -> str:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key: str, value: str):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------ pets
def add_pet(name: str, species: str, breed: str = "",
            birth_date: str = "", photo: str = "") -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO pets (name, species, breed, birth_date, photo) "
            "VALUES (?, ?, ?, ?, ?)",
            (name.strip(), species, breed.strip(), birth_date, photo),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_pet(pet_id: int, name: str, species: str, breed: str = "",
               birth_date: str = "", photo: str | None = None):
    """Обновляет ТОЛЬКО новые поля — старые (size/age/weight/history)
    не трогает, чтобы не потерять данные старой анкеты."""
    conn = get_conn()
    try:
        if photo is None:  # фото не меняли
            conn.execute(
                "UPDATE pets SET name=?, species=?, breed=?, birth_date=? "
                "WHERE id=?",
                (name.strip(), species, breed.strip(), birth_date, pet_id),
            )
        else:
            conn.execute(
                "UPDATE pets SET name=?, species=?, breed=?, birth_date=?, "
                "photo=? WHERE id=?",
                (name.strip(), species, breed.strip(), birth_date, photo,
                 pet_id),
            )
        conn.commit()
    finally:
        conn.close()


def delete_pet(pet_id: int):
    """Удаляет питомца и ВСЁ, что на него ссылается (включая старые
    reminders/prescriptions — иначе в календаре остаются призраки)."""
    conn = get_conn()
    try:
        for table in ("pet_media", "weights", "meds", "feedings",
                      "diets", "reminders", "prescriptions"):
            conn.execute(f"DELETE FROM {table} WHERE pet_id = ?",
                         (pet_id,))
        conn.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
        conn.commit()
    finally:
        conn.close()
    # медиафайлы питомца тоже убираем (тихо, best-effort)
    media_dir = os.path.join(MEDIA_DIR, f"pet_{pet_id}")
    shutil.rmtree(media_dir, ignore_errors=True)


def get_pets() -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM pets ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_pet(pet_id: int) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM pets WHERE id = ?", (pet_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ------------------------------------------------------------------ media
def add_media(pet_id: int, rel_path: str, kind: str = "photo") -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO pet_media (pet_id, path, kind) VALUES (?, ?, ?)",
            (pet_id, rel_path, kind),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_media(pet_id: int, kind: str | None = None) -> list[dict]:
    conn = get_conn()
    try:
        if kind:
            rows = conn.execute(
                "SELECT * FROM pet_media WHERE pet_id=? AND kind=? "
                "ORDER BY id DESC",
                (pet_id, kind),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pet_media WHERE pet_id=? ORDER BY id DESC",
                (pet_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_media(media_id: int):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM pet_media WHERE id=?", (media_id,))
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------ weights
def add_weight(pet_id: int, kg: float, weighed_at: str = "") -> int:
    conn = get_conn()
    try:
        date_str = weighed_at or datetime.now().strftime("%Y-%m-%d")
        cur = conn.execute(
            "INSERT INTO weights (pet_id, weighed_at, kg) VALUES (?, ?, ?)",
            (pet_id, date_str, round(float(kg), 3)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_weights(pet_id: int) -> list[dict]:
    """По возрастанию даты — для графика."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM weights WHERE pet_id=? ORDER BY weighed_at, id",
            (pet_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_last_weight(pet_id: int) -> dict | None:
    ws = get_weights(pet_id)
    return ws[-1] if ws else None


# ------------------------------------------------------------------ meds
def add_med(pet_id: int, title: str, time_hhmm: str) -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO meds (pet_id, title, time) VALUES (?, ?, ?)",
            (pet_id, title.strip(), time_hhmm.strip()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_meds(pet_id: int) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM meds WHERE pet_id=? ORDER BY time", (pet_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_med(med_id: int):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM meds WHERE id=?", (med_id,))
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------ feedings
def add_feeding(pet_id: int, time_hhmm: str, note: str = "",
                grams: float = 0.0) -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO feedings (pet_id, time, note, grams) "
            "VALUES (?, ?, ?, ?)",
            (pet_id, time_hhmm.strip(), note.strip(),
             round(float(grams or 0), 1)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def replace_feedings(pet_id: int, rows: list[tuple]) -> int:
    """Замена всего расписания кормления одним расчётом нормы.

    rows = [(time, grams, note), ...]. Один conn = одна транзакция.
    Возвращает число добавленных строк.
    """
    conn = get_conn()
    try:
        conn.execute("DELETE FROM feedings WHERE pet_id=?", (pet_id,))
        for time_hhmm, grams, note in rows:
            conn.execute(
                "INSERT INTO feedings (pet_id, time, note, grams) "
                "VALUES (?, ?, ?, ?)",
                (pet_id, str(time_hhmm).strip(), str(note or "").strip(),
                 round(float(grams or 0), 1)),
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def get_feedings(pet_id: int) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM feedings WHERE pet_id=? ORDER BY time",
            (pet_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_feeding(feeding_id: int):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM feedings WHERE id=?", (feeding_id,))
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------ diets
def add_diet(pet_id: int, title: str, start_date: str, days: int,
             goal: str = "", kcal: int = 0,
             target_weight: float = 0.0) -> int:
    conn = get_conn()
    try:
        # у питомца одна активная диета
        conn.execute(
            "UPDATE diets SET active=0 WHERE pet_id=? AND active=1",
            (pet_id,),
        )
        cur = conn.execute(
            "INSERT INTO diets (pet_id, title, start_date, days, "
            "goal, kcal, target_weight) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pet_id, title.strip(), start_date, int(days),
             str(goal or ""), int(kcal or 0),
             round(float(target_weight or 0), 2)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_active_diet(pet_id: int) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM diets WHERE pet_id=? AND active=1 "
            "ORDER BY id DESC LIMIT 1",
            (pet_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def finish_diet(diet_id: int):
    conn = get_conn()
    try:
        conn.execute("UPDATE diets SET active=0 WHERE id=?", (diet_id,))
        conn.commit()
    finally:
        conn.close()


def get_diets(pet_id: int) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM diets WHERE pet_id=? ORDER BY id DESC",
            (pet_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
