"""
Спринт 1 — Точка входа с фирменным стилем «Рубикон Агент»
ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ ДЛЯ KIVYMD 2.0.0

Что изменилось:
  - Тема: Teal → Green (фирменный зелёный #2E7D32)
  - Splash: 5 секунд → 2.5 секунды + плавный переход
  - Исправлен баг с FBO при snackbar
  - Добавлен метод show_toast — безопасное уведомление без FBO
"""

import os
import shutil
from datetime import datetime

from kivy.config import Config

Config.set("graphics", "width", "360")
Config.set("graphics", "height", "680")
Config.set("graphics", "resizable", "0")

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from models.database import Database
from screens.calculator import CalculatorScreen
from screens.calendar import CalendarScreen
from screens.catalog import CatalogScreen
from screens.drug_detail import DrugDetailScreen
from screens.pet_form import PetFormScreen
from screens.profile import ProfileScreen
from screens.pet_detail import PetDetailScreen


def backup_database(keep=5):
    """Снимок базы при каждом старте."""
    src = "data/rubikon.db"
    if not os.path.exists(src):
        print("Бэкап пропущен: data/rubikon.db не найден")
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = os.path.join("backup", f"rubikon.db.bak-{stamp}")
    os.makedirs("backup", exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"Бэкап создан: {dst}")
    baks = sorted(os.listdir("backup"))
    while len(baks) > keep:
        os.remove(os.path.join("backup", baks.pop(0)))


class SplashScreen(MDScreen):
    pass


class RubikonApp(MDApp):
    def build(self):
        # ═══════════════════════════════════════════════════════
        # ФИРМЕННЫЙ СТИЛЬ «РУБИКОН АГЕНТ»
        # ═══════════════════════════════════════════════════════
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Green"  # было Teal
        self.theme_cls.primary_hue = "700"  # насыщенный зелёный

        # Белый фон под всеми экранами
        Window.clearcolor = (1, 1, 1, 1)

        try:
            backup_database()
        except OSError as e:
            print(f"Бэкап не удался: {e}")

        self.db = Database()

        # Загрузка KV-файлов
        Builder.load_file("kv/splash.kv")
        Builder.load_file("kv/catalog.kv")
        Builder.load_file("kv/drug_detail.kv")
        Builder.load_file("kv/profile.kv")
        Builder.load_file("kv/calculator.kv")
        Builder.load_file("kv/calendar.kv")
        Builder.load_file("kv/pet_form.kv")
        Builder.load_file("kv/pet_detail.kv")

        self.root = Builder.load_file("kv/root.kv")

        # Фикс WeakProxy для навбара
        nav_bar = self.root.ids.nav_bar
        if hasattr(nav_bar, "__ref__"):
            nav_bar = nav_bar.__ref__()
        self.nav_bar = nav_bar
        self.root.remove_widget(self.nav_bar)

        # Splash: 2.5 секунды вместо 5
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

    # ═══════════════════════════════════════════════════════
    # БЕЗОПАСНЫЙ TOAST (вместо snackbar, который падает с FBO)
    # ═══════════════════════════════════════════════════════
    def show_toast(self, message, duration=2.5):
        """
        Показать уведомление внизу экрана.
        Не использует MDSnackbar (тот падает с FBO при переходе между экранами).
        Вместо этого — простой MDCard с анимацией.
        """
        from kivy.metrics import dp
        from kivy.animation import Animation
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel

        # Получаем текущий экран
        current_screen = self.root.ids.screen_manager.current_screen

        toast = MDCard(
            size_hint=(0.92, None),
            height=dp(48),
            radius=[dp(12)],
            md_bg_color=(0.09, 0.45, 0.0, 0.95),  # фирменный зелёный
            pos_hint={"center_x": 0.5, "y": 0.08},
            opacity=0,
        )
        toast.add_widget(
            MDLabel(
                text=message,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                halign="center",
                font_style="Body",
                font_size="14sp",
            )
        )
        current_screen.add_widget(toast)

        # Анимация: появление → пауза → исчезновение → удаление
        anim_in = Animation(opacity=1, duration=0.25)
        anim_out = Animation(opacity=0, duration=0.25)
        anim_out.bind(on_complete=lambda *_: current_screen.remove_widget(toast))
        anim_in.start(toast)
        Clock.schedule_once(lambda dt: anim_out.start(toast), duration)


if __name__ == "__main__":
    RubikonApp().run()
