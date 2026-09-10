import os  # работа с файлами и папками
import shutil  # копирование файлов
from datetime import datetime  # текущая дата-время для имени копии

from kivy.config import Config

Config.set("graphics", "width", "340")
Config.set("graphics", "height", "640")
Config.set("graphics", "resizable", "0")

# сторонние библиотеки
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

# твой код
from models.database import Database
from screens.calculator import CalculatorScreen  # noqa: F401
from screens.calendar import CalendarScreen  # noqa: F401
from screens.catalog import CatalogScreen  # noqa: F401
from screens.drug_detail import DrugDetailScreen  # noqa: F401
from screens.pet_form import PetFormScreen  # noqa: F401
from screens.profile import ProfileScreen  # noqa: F401


def backup_database(keep=5):
    """Снимок базы при каждом старте: последний удачный запуск всегда восстановим."""
    src = "data/rubikon.db"
    if not os.path.exists(src):  # базы ещё нет (первый запуск) — снимать нечего
        print("Бэкап пропущен: data/rubikon.db не найден")
        return
        # DTZ005 отклоняем: метка в имени файла — подпись для человека, нужно местное время ПК.
        # Правило про серверные системы, где времена сравниваются между собой, — у нас сравнений нет.
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")  # noqa: DTZ005
    dst = os.path.join("backup", f"rubikon.db.bak-{stamp}")
    os.makedirs("backup", exist_ok=True)  # нет папки — создай, есть — молчи
    shutil.copyfile(src, dst)  # copyfile, НЕ copy2! (PermissionError на флешке, Спринт 2)
    print(f"Бэкап создан: {dst}")
    baks = sorted(os.listdir("backup"))  # старые копии первые — спасибо штампу в имени
    while len(baks) > keep:  # храним последние 5, устаревшие удаляем
        os.remove(os.path.join("backup", baks.pop(0)))


class SplashScreen(MDScreen):
    pass


class RubikonApp(MDApp):
    def build(self):

        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"

        # Белая подложка под всеми экранами (вместо чёрной по умолчанию)
        Window.clearcolor = (1, 1, 1, 1)

        try:
            backup_database()  # снимок ДО того, как приложение что-то изменит в базе
        except OSError as e:
            print(f"Бэкап не удался, работаем дальше: {e}")

        self.db = Database()

        Builder.load_file("kv/splash.kv")
        Builder.load_file("kv/catalog.kv")
        Builder.load_file("kv/drug_detail.kv")
        Builder.load_file("kv/profile.kv")
        Builder.load_file("kv/calculator.kv")
        Builder.load_file("kv/calendar.kv")
        Builder.load_file("kv/pet_form.kv")

        self.root = Builder.load_file("kv/root.kv")

        # ------------------------------------------------------------
        # ФИКС КРАША "weakly-referenced object no longer exists".
        # В Kivy 2.1+ ids из kv — это WeakProxy: слабая обёртка, которая
        # НЕ держит виджет живым. После remove_widget навбар оставался
        # только под слабой ссылкой, и сборщик мусора мог уничтожить его
        # в любой момент (проверено на Kivy 2.3.1 — воспроизводится).
        # Разыменовываем обёртку: получаем РЕАЛЬНЫЙ виджет и сильную
        # ссылку на него — теперь он не исчезнет ни при каком GC.
        # ------------------------------------------------------------
        nav_bar = self.root.ids.nav_bar
        if hasattr(nav_bar, "__ref__"):  # WeakProxy? (Kivy 2.1+)
            nav_bar = nav_bar.__ref__()  # реальный виджет
        self.nav_bar = nav_bar
        self.root.remove_widget(self.nav_bar)

        Clock.schedule_once(self.go_to_catalog, 5)

        return self.root

    def go_to_catalog(self, dt):
        self.root.ids.screen_manager.current = "catalog"
        self.root.add_widget(self.nav_bar)

    def open_drug_detail(self, drug_id):
        """Открыть детальную карточку препарата."""
        self.selected_drug_id = drug_id
        self.root.ids.screen_manager.current = "drug_detail"

    def on_switch_tabs(self, bar, item, item_icon, item_text):
        screen_map = {
            "Каталог": "catalog",
            "Профиль": "profile",
            "Калькулятор": "calculator",
            "Календарь": "calendar",
        }
        target = screen_map.get(item_text, "catalog")
        self.root.ids.screen_manager.current = target

    def add_pet(self):
        print("Добавить питомца")

    def calculate_dose(self):
        print("Рассчитать дозу")

    def set_reminder(self):
        print("Установить напоминание")

    def on_stop(self):
        if hasattr(self, "db") and self.db:
            self.db.close()


if __name__ == "__main__":
    RubikonApp().run()
