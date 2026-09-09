# main.py — RubikonApp
# Изменения от 2026-09-06 (остальной код не тронут):
#
#   1) ФИКСИРОВАННЫЙ РАЗМЕР ОКНА: 720 x 1280, растягивать нельзя.
#      ВАЖНО: блок Config стоит в САМОМ ВЕРХУ файла, до всех остальных
#      kivy-импортов. Kivy читает эти настройки один раз — в момент
#      СОЗДАНИЯ ОКНА (при первых импортах kivy.core.*). Если перенести
#      блок ниже, окно уже успеет создаться, и настройки молча не сработают.
#
#      Если окно высотой 1280 не влезает в экран (маленький ноутбук) —
#      просто уменьшите число в строке height, например на 1024.
#      Интерфейс адаптируется, содержимое прокручивается.
#
#      На телефоне (будущий APK) эти настройки игнорируются — там окно
#      всегда на весь экран, поэтому вреда от них нет.
#
#   2) Window.clearcolor = белый (без него вокруг карточек просвечивал
#      чёрный цвет "очистки окна" Kivy).
#
#   3) ФИКС КРАША "weakly-referenced object no longer exists"
#      (падение через 2.5 секунды после запуска, в go_to_catalog).
#      Причина: в Kivy 2.1+ значения id из kv-файлов — слабые обёртки
#      (WeakProxy), они НЕ держат виджет живым. После remove_widget
#      навбар держала только слабая ссылка, сборщик мусора уничтожал
#      виджет в случайный момент — раньше везло и краша не было,
#      теперь не повезло. Решение: разыменовать обёртку и хранить
#      сильную ссылку на реальный виджет (см. build()).

from kivy.config import Config

Config.set("graphics", "width", "340")
Config.set("graphics", "height", "640")
Config.set("graphics", "resizable", "0")

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from models.database import Database
from screens.catalog import CatalogScreen
from screens.drug_detail import DrugDetailScreen
from screens.profile import ProfileScreen
from screens.calculator import CalculatorScreen
from screens.calendar import CalendarScreen
from screens.pet_form import PetFormScreen


class SplashScreen(MDScreen):
    pass


class RubikonApp(MDApp):
    def build(self):

        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"

        # Белая подложка под всеми экранами (вместо чёрной по умолчанию)
        Window.clearcolor = (1, 1, 1, 1)

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
        if hasattr(nav_bar, "__ref__"):        # WeakProxy? (Kivy 2.1+)
            nav_bar = nav_bar.__ref__()        # реальный виджет
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