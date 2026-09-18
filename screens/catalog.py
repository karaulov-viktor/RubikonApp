# -*- coding: utf-8 -*-
"""Каталог препаратов — RubikonApp.

Этот экран:
  - грузит 61 препарат из БД (app.db.get_all_drugs);
  - строит сетку 2×N карточек DrugCard;
  - поиск фильтрует список (с дебаунсом 250 мс — запрос к БД
    только после того, как пользователь перестал печатать);
  - при возврате из карточки препарата НЕ пересоздаёт сетку —
    использует кеш (_loaded). Это критично на флешке USB 2.0,
    где создание 61 карточки с картинками занимает 2-5 секунд.

Цвета — бело-зелёный фирменный:
  - фон карточек: C.CARD (белый #FFFFFF)
  - рамка карточек: C.BRAND_GREEN_BORDER (нейтральная серо-зелёная)
  - подложка фото: C.BRAND_GREEN_SOFT (мятная #F1F5EF)
  - текст названия: C.BRAND_GREEN (тёмно-зелёный #14532D)
  - текст категории: C.TEXT_SUB (нейтральный серый #616161)
"""
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextFieldTrailingIcon

from models.image_utils import drug_image_source
from models.theme import (
    CARD,
    CARD_BORDER,
    TEXT_MAIN,
    TEXT_SUB,
    BRAND_GREEN,
    BRAND_GREEN_SOFT,
    BRAND_GREEN_BORDER,
)


class ClickableTrailingIcon(ButtonBehavior, MDTextFieldTrailingIcon):
    """Trailing-иконка с событием on_release.

    У базовой MDTextFieldTrailingIcon в KivyMD 2.0.0 НЕТ ButtonBehavior —
    это просто MDIcon. Поэтому on_release в kv падал с AttributeError:
    release. Добавляем ButtonBehavior — on_release теперь работает.

    Используется в kv/catalog.kv для кнопки «× очистить» в поиске.
    """
    pass


class DrugCard(MDCard):
    """Карточка препарата — белая с мятной подложкой под фото.

    theme_bg_color="Custom" обязателен — иначе KivyMD 2.0.0 заменяет
    md_bg_color на Material You surfaceContainerColor (серый оттенок).
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("md_bg_color", CARD)
        kwargs.setdefault("theme_bg_color", "Custom")
        kwargs.setdefault("line_color", BRAND_GREEN_BORDER)
        kwargs.setdefault("theme_line_color", "Custom")
        kwargs.setdefault("radius", [dp(14)])
        super().__init__(**kwargs)
        self.bind(width=self._update_height)

    def _update_height(self, instance, width):
        # Соотношение сторон ~3:2, минимум 180dp для маленьких экранов
        self.height = max(width * 1.5, dp(180))


class CatalogScreen(MDScreen):
    """Экран каталога препаратов.

    Оптимизации:
      - _loaded — флаг, что сетка уже построена. on_enter НЕ пересоздаёт
        карточки, если они уже на экране. Возврат из карточки препарата —
        мгновенный.
      - _silence_search — флаг, чтобы программный сброс search_field.text
        (в open_drug_detail) не дёргал on_search.
      - _search_sched — дебаунс: on_search планирует запрос к БД через
        250 мс. Если пользователь печатает дальше — отмена и новый план.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._loaded = False            # каталог уже построен?
        self._silence_search = False    # программный сброс поиска?
        self._search_sched = None       # отложенный запрос к БД
        self._search_query = ""         # последний запрос

    # ------------------------------------------------------------------
    # Жизненный цикл
    # ------------------------------------------------------------------
    def on_enter(self):
        """Загружаем каталог только при первом входе за сессию."""
        app = MDApp.get_running_app()
        if not (hasattr(app, "db") and app.db):
            return
        if not self._loaded:
            self.load_drugs()
            self._loaded = True

    def refresh(self):
        """Принудительная перезагрузка (для будущей кнопки обновить)."""
        self._loaded = False
        self.on_enter()

    # ------------------------------------------------------------------
    # Данные
    # ------------------------------------------------------------------
    def load_drugs(self):
        """Загрузить все препараты из БД."""
        app = MDApp.get_running_app()
        drugs = app.db.get_all_drugs()
        self.update_grid(drugs)

    def update_grid(self, drugs):
        """Очистить сетку и построить карточки для каждого препарата."""
        grid = self.ids.drug_grid
        grid.clear_widgets()
        for drug in drugs:
            # Берём только первые 7 полей, игнорируя новые (dose_per_kg и т.д.)
            drug_id, name, category, _desc, _instr, image, _icon = drug[:7]
            card = self._create_card(drug_id, name, category, image)
            grid.add_widget(card)

    def _create_card(self, drug_id, name, category, image_path):
        """Собрать одну карточку препарата с фото и текстом."""
        card = DrugCard(
            orientation="vertical",
            size_hint_y=None,
            height="220dp",
            padding="0dp",
            spacing="0dp",
            # ripple_behavior=False — убираем для скорости на GT 710
            # (каждый ripple = отдельный FBO 50x50, 61 шт = 0.5-1 с).
            # Если нужна визуальная обратная связь — верните True.
            ripple_behavior=False,
        )
        card.bind(
            on_release=lambda x, did=drug_id: self.open_drug_detail(did)
        )

        # --- Фото препарата на мятной подложке ---
        photo_container = MDBoxLayout(
            size_hint_y=None,
            height="120dp",
            md_bg_color=BRAND_GREEN_SOFT,
            theme_bg_color="Custom",
        )

        def update_photo_height(instance, width):
            photo_container.height = width * 1  # квадратная картинка

        card.bind(width=update_photo_height)

        img = Image(
            source=drug_image_source(image_path),
            size_hint=(1, 1),
            fit_mode="contain",
            # nocache=True — 61 уникальная картинка, кеш не нужен
            nocache=True,
            allow_stretch=True,
        )
        photo_container.add_widget(img)

        # --- Текстовый блок ---
        text_box = MDBoxLayout(
            orientation="vertical",
            padding=["12dp", "8dp", "12dp", "8dp"],
            spacing="2dp",
            size_hint_y=None,
            adaptive_height=True,
            pos_hint={"bottom": 0.0},
        )

        title = MDLabel(
            text=name or "",
            font_style="Title",
            role="medium",
            halign="left",
            valign="top",
            size_hint_y=None,
            adaptive_height=True,
            text_size=(self.width, None),
            theme_text_color="Custom",
            text_color=BRAND_GREEN,        # тёмно-зелёный бренд (был TEXT_MAIN)
            max_lines=2,
            shorten=True,
            shorten_from="right",
        )

        cat = MDLabel(
            text=category or "",
            theme_text_color="Custom",
            text_color=TEXT_SUB,           # нейтральный серый
            halign="left",
            valign="top",
            size_hint_y=None,
            adaptive_height=True,
            text_size=(self.width, None),
            font_style="Body",
            role="small",
            max_lines=1,
            shorten=True,
            shorten_from="right",
        )

        text_box.add_widget(title)
        text_box.add_widget(cat)
        card.add_widget(photo_container)
        card.add_widget(text_box)
        return card

    # ------------------------------------------------------------------
    # Поиск
    # ------------------------------------------------------------------
    def on_search(self, query):
        """Дебаунс 250 мс — запрос к БД только после паузы в печати."""
        if self._silence_search:
            return
        self._search_query = query.strip()
        if self._search_sched:
            Clock.unschedule(self._search_sched)
        self._search_sched = Clock.schedule_once(self._do_search, 0.25)

    def _do_search(self, dt):
        """Фактический запрос к БД после 250 мс паузы."""
        app = MDApp.get_running_app()
        if not hasattr(app, "db") or not app.db:
            return
        q = self._search_query
        if q:
            drugs = app.db.search_drugs(q)
        else:
            drugs = app.db.get_all_drugs()
        self.update_grid(drugs)

    # ------------------------------------------------------------------
    # Навигация
    # ------------------------------------------------------------------
    def open_drug_detail(self, drug_id):
        """Перейти в карточку препарата. НЕ пересоздаём каталог при возврате."""
        # _silence_search=True — чтобы сброс search_field.text не дёрнул
        # on_search (иначе пересоздаст все 61 карточку, что и так сделано).
        self._silence_search = True
        self.ids.search_field.text = ""
        self._silence_search = False
        app = MDApp.get_running_app()
        app.open_drug_detail(drug_id)