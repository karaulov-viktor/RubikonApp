import os
import sqlite3


def py_lower(value):
    if value:
        return str(value).lower()
    return value


class Database:
    """SQLite база препаратов"""

    def __init__(self, db_path="data/rubikon.db"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.create_function("py_lower", 1, py_lower)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        """Создание таблиц"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS drugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                description TEXT,
                instruction TEXT,
                image TEXT,
                icon  TEXT DEFAULT "pill"
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
        self._seed_data()
        self.conn.commit()

    def _seed_data(self):
        """Заполнение таблицы тестовыми данными"""
        self.cursor.execute("SELECT COUNT(*) FROM drugs")
        if self.cursor.fetchone()[0] > 0:
            return

        drugs = [
            ("Аспирин", "Обезболивающее", "Снимает боль и воспаление", "По 1 таблетке 2 раза в день после еды",
             "img/logo.png", "pill"),
            ("Амоксициллин", "Антибиотик", "Антибиотик широкого спектра для собак и кошек",
             "5-10 мг/кг веса 2 раза в день", "img/logo.png", "pill"),
            ("Фоспренил", "Противовирусный", "Противовирусный препарат для животных", "Подкожно 0,2 мл/кг",
             "img/logo.png", "virus-off"),
            ("Витамин B", "Витамин", "Комплекс витаминов группы B", "1 мл на 10 кг веса", "img/logo.png", "needle"),
            ("Ивермектин", "Антипаразитарный", "От гельминтов и клещей", "0,2 мг/кг перорально", "img/logo.png", "bug"),
        ]
        self.cursor.executemany(
            "INSERT INTO drugs (name, category, description, instruction, image, icon) VALUES (?, ?, ?, ?, ?, ?)",
            drugs
        )
        self.conn.commit()

    def get_all_drugs(self):
        self.cursor.execute("SELECT id, name, category, description, instruction, image, icon FROM drugs ORDER BY name")
        return self.cursor.fetchall()

    def search_drugs(self, query):
        like = f"%{query.lower()}%"
        self.cursor.execute(
            "SELECT id, name, category, description, instruction, image, icon FROM drugs WHERE py_lower(name) LIKE ? OR py_lower(category) LIKE ? ORDER BY name",
            (like, like)
        )
        return self.cursor.fetchall()

    def get_drug_by_id(self, drug_id):
        self.cursor.execute(
            "SELECT id, name, category, description, instruction, image, icon FROM drugs WHERE id = ?",
            (drug_id,)
        )
        return self.cursor.fetchone()

    def add_pet(self, name, species, breed, size, age, weight, history, photo=""):
        self.cursor.execute(
            "INSERT INTO pets (name, species, breed, size, age, weight, history, photo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, species, breed, size, age, weight, history, photo)
        )
        self.conn.commit()

    def get_pets(self):
        self.cursor.execute(
            "SELECT id, name, species, breed, size, age, weight, history, photo FROM pets ORDER BY name")
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
