"""
База данных RubikonApp — Спринт 1.5 + История назначений
"""

import os
import sqlite3
from datetime import datetime


def py_lower(value):
    if value:
        return str(value).lower()
    return value


class Database:
    """SQLite база препаратов, питомцев, напоминаний и истории назначений"""

    def __init__(self, db_path="data/rubikon.db"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.create_function("py_lower", 1, py_lower)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        """Создание таблиц и миграция"""
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
                FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
                FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
            )
        """)

        # ═══ НОВАЯ ТАБЛИЦА: История назначений ═══
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
                FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
                FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
            )
        """)

        self._seed_data()
        self.conn.commit()

    def _seed_data(self):
        """Заполнение таблицы тестовыми данными"""
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
        """Получить препараты, подходящие для данного вида животного."""
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
    # ПИТОМЦЫ
    # ═══════════════════════════════════════════════════════

    def add_pet(self, name, species, breed, size, age, weight, history, photo=""):
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

    def update_pet(self, pet_id, name, species, breed, size, age, weight, history, photo):
        self.cursor.execute(
            """UPDATE pets
               SET name=?, species=?, breed=?, size=?,
                   age=?, weight=?, history=?, photo=?
               WHERE id=?""",
            (name, species, breed, size, age, weight, history, photo, pet_id)
        )
        self.conn.commit()

    def delete_pet(self, pet_id):
        self.cursor.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
        self.conn.commit()

    # ═══════════════════════════════════════════════════════
    # НАПОМИНАНИЯ
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
            (today_key, reminder_id)
        )
        self.conn.commit()

    # ═══════════════════════════════════════════════════════
    # ИСТОРИЯ НАЗНАЧЕНИЙ
    # ═══════════════════════════════════════════════════════

    def add_prescription(self, pet_id, drug_id, dose_per_kg, concentration, duration_days, notes=""):
        """Добавить запись в историю назначений."""
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
        """Получить историю назначений для питомца."""
        self.cursor.execute(
            """SELECT p.id, p.prescribed_date, d.name, d.category,
                      p.dose_per_kg, p.concentration, p.duration_days, p.notes
               FROM prescriptions p
               JOIN drugs d ON p.drug_id = d.id
               WHERE p.pet_id = ?
               ORDER BY p.prescribed_date DESC""",
            (pet_id,)
        )
        return self.cursor.fetchall()

    def archive_reminder(self, reminder_id):
        """Перенести будильник в историю перед удалением."""
        # Получаем данные будильника
        self.cursor.execute(
            """SELECT pet_id, drug_id, start_date, end_date, time
               FROM reminders WHERE id = ?""",
            (reminder_id,)
        )
        row = self.cursor.fetchone()
        if not row:
            return

        pet_id, drug_id, start_date, end_date, time = row

        # Получаем данные препарата
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

        # Проверяем, нет ли уже такой записи в истории
        self.cursor.execute(
            """SELECT COUNT(*) FROM prescriptions
               WHERE pet_id = ? AND drug_id = ? AND prescribed_date LIKE ?""",
            (pet_id, drug_id, f"{start_date[:10]}%")
        )
        if self.cursor.fetchone()[0] > 0:
            return  # уже есть

        # Сохраняем в историю
        from datetime import datetime
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