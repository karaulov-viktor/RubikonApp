# -*- coding: utf-8 -*-
"""Профиль: список карточек питомцев (спринт «Питомцы»).

Карточка (по ТЗ): крупное имя, вторая строка — вид (+дата рождения),
третья — порода и возраст (вычислен из даты рождения).
Тап -> личная страница питомца (app.open_pet).
Карточки строятся кодом из БД; kv держит только каркас.

Важно: база может содержать и СТАРЫХ питомцев (спринты 1-2.6, без
birth_date) — читаем поля через .get(), чтобы карточка не падала.
"""
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.fitimage import FitImage
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.screen import MDScreen

from models import database as db
from models import theme as T
from models.age_utils import fmt_display, format_age
from models.image_utils import resolve_media
from screens import AppMixin


class ProfileScreen(AppMixin, MDScreen):

    def on_pre_enter(self, *args):
        self.refresh_pets()

    def refresh_pets(self):
        """Перестраивает список карточек из БД."""
        box = self.ids.pets_box
        empty = self.ids.empty_lbl
        box.clear_widgets()

        pets = db.get_pets()
        empty.opacity = 0 if pets else 1
        empty.text = ("Питомцев пока нет.\n"
                      "Нажмите «+», чтобы добавить первого")

        for pet in pets:
            box.add_widget(self._build_card(pet))

        # состояние кнопки системных уведомлений
        try:
            enabled = self.app.is_system_notifications_enabled()
        except Exception:
            enabled = False
        self.ids.btn_sysnotify.text = (
            "Системные уведомления: ВКЛ" if enabled
            else "Включить напоминания при закрытом приложении"
        )

    # ------------------------------------------------------------------
    def _build_card(self, pet: dict) -> MDCard:
        card = MDCard(
            orientation="horizontal",
            md_bg_color=T.CARD,
            line_color=T.CARD_BORDER,
            radius=[dp(16)],
            padding=dp(12),
            size_hint_y=None,
            height=dp(104),
            spacing=dp(12),
            ripple_behavior=True,
        )
        card.bind(on_release=lambda *a, p=pet: self.app.open_pet(p["id"]))

        # --- аватар ---
        avatar_box = MDCard(
            md_bg_color=T.GREEN_SOFT,
            radius=[dp(14)],
            size_hint=(None, None),
            size=(dp(80), dp(80)),
            pos_hint={"center_y": 0.5},
        )
        photo = pet.get("photo") or ""
        if photo:
            avatar_box.add_widget(FitImage(
                source=resolve_media(photo),
                radius=[dp(14)],
            ))
        else:
            # заглушка: зелёный листок (MDIcon вместо эмодзи — эмодзи
            # в Kivy на Windows не рендерится)
            avatar_box.add_widget(MDIcon(
                icon="leaf",
                halign="center",
                valign="middle",
                font_size="40sp",
                theme_icon_color="Custom",
                icon_color=T.GREEN,
                pos_hint={"center_x": 0.5, "center_y": 0.5},
            ))
        card.add_widget(avatar_box)

        # --- текстовый блок: имя / вид / порода+возраст ---
        name = pet.get("name") or "Без имени"
        species = (pet.get("species") or "").strip()
        breed = (pet.get("breed") or "").strip()
        birth = pet.get("birth_date") or ""

        col = BoxLayout(orientation="vertical", padding=[dp(4), 0])
        col.add_widget(MDLabel(
            text=name,
            font_style="Headline",
            role="small",
            bold=True,
            theme_text_color="Custom",
            text_color=T.GREEN,
            size_hint_y=None,
            height=dp(30),
        ))
        second = species if species else "вид не указан"
        if birth:
            second += f"  ·  род. {fmt_display(birth)}"
        col.add_widget(MDLabel(
            text=second,
            theme_text_color="Custom",
            text_color=T.TEXT_SUB,
            size_hint_y=None,
            height=dp(22),
        ))
        age = format_age(birth)
        third = breed if breed else "порода не указана"
        if age:
            third += f"  ·  {age}"
        col.add_widget(MDLabel(
            text=third,
            theme_text_color="Custom",
            text_color=T.TEXT_SUB,
            size_hint_y=None,
            height=dp(22),
        ))
        card.add_widget(col)
        return card
