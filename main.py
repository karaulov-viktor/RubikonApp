# -*- coding: utf-8 -*-
"""RubikonApp — точка входа.

Спринт «Питомцы» (3) НА БАЗЕ полного функционала спринтов 1-2.6:
каталог 61 препарат, карточка препарата, лечение, календарь,
калькулятор доз, история назначений — всё сохранено.

Что добавил спринт 3:
  - дисклеймер первого запуска (юртексты, models/legal.py)
  - карточки питомцев нового дизайна + личная страница
    (галереи фото/видео, диета, вес, лекарства, кормление)
  - дата рождения вместо возраста + поздравление
  - напоминания при ЗАКРЫТОМ приложении (Планировщик Windows)
  - подсветка активного пункта нижнего меню

ВАЖНО (урок FactoryException): классы экранов импортируются здесь
только ради регистрации в Factory — kv ссылается на них по имени.
"""
import os
import subprocess
import sys

from kivy.config import Config

Config.set("graphics", "width", "360")
Config.set("graphics", "height", "680")
Config.set("graphics", "resizable", "0")

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.label import Label
import kivymd
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from models import database as db
from models.database import Database
from models import theme as T
from models.legal import LEGAL_TEXT
from models.notifier import scan as scan_notifications

# --- регистрация экранов в Factory (НЕ УДАЛЯТЬ импорты!) ---
from screens.appointment_detail import AppointmentDetailScreen
from screens.calculator import CalculatorScreen
from screens.calendar import CalendarScreen
from screens.catalog import CatalogScreen
from screens.disclaimer import DisclaimerScreen
from screens.drug_detail import DrugDetailScreen
from screens.media_viewer import MediaViewerScreen
from screens.pet_detail import PetDetailScreen
from screens.pet_form import PetFormScreen
from screens.pet_treatment import PetTreatmentScreen
from screens.profile import ProfileScreen

# скины элементов меню — для подсветки активного экрана
from kivymd.uix.navigationbar.navigationbar import (
    MDNavigationItem,
    MDNavigationItemLabel,
)

TASK_NAME = "RubikonAppReminder"

# Показывать экран согласия (дисклеймер) при КАЖДОМ запуске —
# удобно для тестирования и демонстрации. ПЕРЕД РЕЛИЗОМ поставить
# False: тогда согласие покажется только один раз (первый запуск)
# и запомнится в базе.
SHOW_DISCLAIMER_EVERY_LAUNCH = True


def _patch_kivymd_fbo():
    """Fbo(size=self.size) при нулевом размере виджета роняет слабые
    GPU (FBO Incomplete attachment, 36054): GT 710, llvmpipe и т.д.
    Нулевой размер бывает у карточек с adaptive_height в момент
    создания (например, панель расчёта нормы кормления).

    Правим на месте — так же починено в актуальном master KivyMD
    (Fbo фиксированного размера 50x50). Заменяет старый внешний
    fix_kivymd_fbo.py: патч применяется сам при каждом старте.
    """
    try:
        from kivy.graphics import (
            ClearBuffers as _CB,
            ClearColor as _CC,
            Color as _C,
            Fbo as _F,
            Rectangle as _R,
        )
        import kivymd.uix.behaviors.ripple_behavior as _rb

        def _init_fbos(self):
            """Тело оригинала, но Fbo фиксированного размера 50x50
            (self.rect растягивается нормально, падает лишь создание
            нулевого Fbo)."""
            self._phase = 0.0
            self.ripple_pos = (0, 0)
            self.fbo = _F(size=[50, 50], group="m3_ripple_behavior")
            self.set_shader(self.fbo)
            with self.fbo:
                _CC(0, 0, 0, 0)
                _CB()
                _C(1, 1, 1, 1)
                self.rect = _R(pos=(0, 0), size=self.size)

        patched = 0
        for obj in list(vars(_rb).values()):
            if isinstance(obj, type) and "init_fbos" in vars(obj):
                obj.init_fbos = _init_fbos
                patched += 1
        if patched:
            print(f"[RubikonApp] FBO-патч применён ({patched} класс(ов))")
    except Exception as _e:
        print(f"[RubikonApp] FBO-патч не применён: {_e}")


_patch_kivymd_fbo()

# экран -> подпись пункта меню; подэкраны наследуют раздел
NAV_LABELS = {
    "catalog": "Каталог",
    "profile": "Профиль",
    "calculator": "Калькулятор",
    "calendar": "Календарь",
}
SUB_NAV_LABELS = {
    "drug_detail": "Каталог",
    "pet_detail": "Профиль",      # личная страница питомца
    "pet_form": "Профиль",
    "pet_treatment": "Профиль",   # лечение и назначения
    "appointment_detail": "Профиль",
    "media_viewer": "Профиль",    # просмотр фото/видео на весь экран
}

KV_FILES = (
    "kv/splash.kv",
    "kv/catalog.kv",
    "kv/drug_detail.kv",
    "kv/profile.kv",
    "kv/pet_form.kv",
    "kv/pet_detail.kv",
    "kv/pet_treatment.kv",
    "kv/appointment_detail.kv",
    "kv/disclaimer.kv",
    "kv/calculator.kv",
    "kv/calendar.kv",
    "kv/media_viewer.kv",
)


class SplashScreen(MDScreen):
    """Заставка: зелёный логотип, 2.5 секунды (описан в kv/splash.kv)."""


class ToastLabel(Label):
    """Самодельный тост поверх окна (без MDSnackbar — обход FBO-бага)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        green = T.GREEN_DARK
        with self.canvas.before:
            Color(green[0], green[1], green[2], 0.97)
            self._rect = RoundedRectangle(radius=[dp(22)])
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class RubikonApp(MDApp):

    # ============================================================= build
    def build(self):
        self.theme_cls.theme_style = "Light"       # белая база
        self.theme_cls.primary_palette = "Green"   # фирменный зелёный
        self.theme_cls.primary_hue = "900"         # тёмный, ближе к #14532D

        # БЕЛЫЙ фон окна — литералом, а не через T.BG: если у пользователя
        # остался старый theme.py, окно всё равно будет белым.
        Window.clearcolor = (1, 1, 1, 1)

        # Самопроверка окружения: в консоли должна быть строка
        # с версией темы whitegreen-4 (белое приложение, тёмно-зелёные
        # шрифты; бирюза/мята убраны).
        print(f"[RubikonApp] KivyMD {getattr(kivymd, '__version__', '?')}"
              f", тема {getattr(T, 'PALETTE_VERSION', 'НЕИЗВЕСТНА')}")
        # маркер сборки main.py: если этой строки НЕТ в логе при
        # запуске — на диске старый main.py, замените файл из пакета
        print("[RubikonApp] main.py v2.2 — дисклеймер при каждом "
              "запуске + псевдонимы кнопок согласия")
        if getattr(T, "PALETTE_VERSION", "") != "whitegreen-4":
            print("[RubikonApp] ВНИМАНИЕ: models/theme.py устарел —"
                  " скопируйте файл из пакета v4, иначе цвета будут"
                  " неправильными!")
        if getattr(kivymd, "__version__", "2.0.0") != "2.0.0":
            print("[RubikonApp] ВНИМАНИЕ: требуется KivyMD 2.0.0"
                  " (pip install -r requirements.txt). На dev-версиях"
                  " карточки могут рисоваться с тонировкой!")

        # --- БД: инициализация + миграция + бэкап при каждом старте ---
        db.init_db()
        try:
            db.backup_db()
        except Exception:
            pass

        # Старый интерфейс БД (каталог/лечение/календарь): app.db
        self.db = Database()

        for f in KV_FILES:
            Builder.load_file(f)

        self.root = Builder.load_file("kv/root.kv")

        # юридический текст на экран согласия
        self.root.ids.screen_manager.get_screen(
            "disclaimer").ids.legal_text.text = LEGAL_TEXT

        # меню на заставке не нужно
        self.nav_bar = self.root.ids.nav_bar
        self.root.remove_widget(self.nav_bar)

        Clock.schedule_once(self._after_splash, 2.5)
        # проверка напоминаний каждые 30 секунд, пока приложение запущено
        Clock.schedule_interval(self._check_notifications, 30)

        return self.root

    def _after_splash(self, dt):
        """Заставка -> дисклеймер (каждый запуск или первый) -> каталог."""
        if (not SHOW_DISCLAIMER_EVERY_LAUNCH
                and db.get_setting("disclaimer_accepted") == "1"):
            self.go_to("catalog")
        else:
            self.go_to("disclaimer")

    # ====================================================== навигация
    def go_to(self, screen_name: str):
        """Единая точка переходов: экран + подсветка нижнего меню."""
        self.root.ids.screen_manager.current = screen_name
        if screen_name in ("splash", "disclaimer", "media_viewer"):
            # заставка, согласие и полноэкранный просмотрщик медиа
            # идут без нижнего меню
            if self.nav_bar.parent is not None:
                self.root.remove_widget(self.nav_bar)
        elif self.nav_bar.parent is None:
            self.root.add_widget(self.nav_bar)
        self._sync_nav(screen_name)

    def on_switch_tabs(self, bar, item, item_icon, item_text):
        """Тап по нижнему меню."""
        screen_map = {
            "Каталог": "catalog",
            "Профиль": "profile",
            "Калькулятор": "calculator",
            "Календарь": "calendar",
        }
        self.go_to(screen_map.get(item_text, "catalog"))

    def _sync_nav(self, screen_name: str):
        """Подсветка пункта меню: точное совпадение или раздел-родитель."""
        want = NAV_LABELS.get(screen_name) or SUB_NAV_LABELS.get(screen_name)
        for item in self.nav_bar.children:
            if not isinstance(item, MDNavigationItem):
                continue
            item.active = (
                want is not None and self._nav_label(item) == want
            )

    @staticmethod
    def _nav_label(item) -> str:
        """Достаёт текст подписи пункта меню (она вложена в контейнеры)."""
        for child in item.children:
            for grandchild in child.children:
                if isinstance(grandchild, MDNavigationItemLabel):
                    return grandchild.text
        return ""

    # ====================================== мосты kv->py (старый код)
    def open_drug_detail(self, drug_id):
        """Открыть детальную карточку препарата."""
        self.selected_drug_id = drug_id
        self.go_to("drug_detail")

    def open_calculator_for_drug(self):
        """Кнопка «Рассчитать дозу» в карточке препарата: калькулятор
        открывается сразу с выбранным препаратом (drug_id берётся из
        selected_drug_id, куда его кладёт open_drug_detail)."""
        drug_id = getattr(self, "selected_drug_id", None)
        if drug_id:
            self.root.ids.screen_manager.get_screen(
                "calculator").preselect_drug(drug_id)
        self.go_to("calculator")

    # ====================================== мосты экранов питомцев
    def add_pet(self):
        self.root.ids.screen_manager.get_screen("pet_form").start_add()
        self.go_to("pet_form")

    def open_pet(self, pet_id: int):
        self.root.ids.screen_manager.get_screen("pet_detail").open_pet(
            pet_id)

    def edit_pet(self, pet_id: int):
        self.root.ids.screen_manager.get_screen("pet_form").start_edit(
            pet_id)
        self.go_to("pet_form")

    def open_treatment(self, pet_id: int):
        """Лечение и назначения (экран спринтов 1-2.6)."""
        screen = self.root.ids.screen_manager.get_screen("pet_treatment")
        screen.current_pet_id = pet_id
        self.go_to("pet_treatment")

    # ======================================================= дисклеймер
    def accept_disclaimer(self):
        db.set_setting("disclaimer_accepted", "1")
        self.go_to("catalog")

    def decline_disclaimer(self):
        self.show_toast(
            "Для работы приложения нужно принять условия использования")

    # Совместимость со старыми версиями kv/disclaimer.kv, где кнопки
    # вызывают app.on_disclaimer_accept() / app.on_disclaimer_decline().
    # Оба имени ведут к одним и тем же методам — работает любой kv.
    on_disclaimer_accept = accept_disclaimer
    on_disclaimer_decline = decline_disclaimer

    # ==================================================== уведомления
    def _check_notifications(self, dt):
        """В-приложении: тосты по расписанию (кормление, лекарства,
        день рождения, конец диеты). Дедупликация — общий state-файл
        с системным нотификатором."""
        try:
            for ev in scan_notifications():
                self.show_toast(ev["text"], duration=5)
        except Exception:
            pass

    def is_system_notifications_enabled(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            r = subprocess.run(
                ["schtasks", "/Query", "/TN", TASK_NAME],
                capture_output=True,
            )
            return r.returncode == 0
        except Exception:
            return False

    def toggle_system_notifications(self):
        """Вкл/выкл напоминаний ПРИ ЗАКРЫТОМ приложении: задача
        Планировщика Windows каждые 15 минут запускает notifier.py."""
        if sys.platform != "win32":
            self.show_toast("Доступно только на Windows")
            return
        if self.is_system_notifications_enabled():
            subprocess.run(
                ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
                capture_output=True,
            )
            self.show_toast("Системные напоминания выключены")
        else:
            pythonw = os.path.join(
                os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable  # fallback: будет мигать консоль
            notifier_py = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "notifier.py")
            subprocess.run(
                ["schtasks", "/Create", "/SC", "MINUTE", "/MO", "15",
                 "/TN", TASK_NAME, "/F",
                 "/TR", f'"{pythonw}" "{notifier_py}"'],
                capture_output=True,
            )
            if self.is_system_notifications_enabled():
                self.show_toast(
                    "Готово! Напоминания будут приходить даже при закрытом "
                    "приложении")
            else:
                self.show_toast(
                    "Не удалось создать задачу планировщика — запустите "
                    "приложение от имени администратора")
        try:
            self.root.ids.screen_manager.get_screen(
                "profile").refresh_pets()
        except Exception:
            pass

    # ============================================================= тост
    def show_toast(self, message, duration=2.5):
        """Безопасный тост (старый, проверенный на GT 710: без FBO).

        Крепится к текущему экрану, а не к Window: на слабых
        видеокартах виджеты поверх ScreenManager падали с FBO 36054.
        """
        try:
            from kivy.animation import Animation as _A
            from kivymd.uix.card import MDCard
            from kivymd.uix.label import MDLabel

            current_screen = self.root.ids.screen_manager.current_screen
            if current_screen is None:
                return

            toast = MDCard(
                size_hint=(0.92, None),
                height=dp(48),
                radius=[dp(12)],
                md_bg_color=T.GREEN_DARK,
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

            anim_in = _A(opacity=1, duration=0.25)
            anim_out = _A(opacity=0, duration=0.25)
            anim_out.bind(
                on_complete=lambda *_: current_screen.remove_widget(toast))
            anim_in.start(toast)
            Clock.schedule_once(
                lambda dt: anim_out.start(toast), duration)
        except Exception:
            # тост не критичен — не даём ему ронять приложение
            print(f"[toast] {message}")


if __name__ == "__main__":
    RubikonApp().run()
