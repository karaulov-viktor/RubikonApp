import os
from functools import partial

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.image import Image
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.screen import MDScreen

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ProfileScreen(MDScreen):
    def on_pre_enter(self, *args):
        """Kivy вызывает это ПЕРЕД каждым показом экрана — карточки всегда свежие."""
        self.refresh_cards()

    def refresh_cards(self):
        box = self.ids.cards_box
        box.clear_widgets()  # стёрли доску — рисуем заново
        pets = App.get_running_app().db.get_pets()
        if not pets:
            box.add_widget(MDLabel(
                text="Питомцев пока нет. Нажми + чтобы добавить.",
                halign="center",
                theme_text_color="Secondary",
                adaptive_height=True,
            ))
            return
        for pet in pets:
            box.add_widget(self._make_card(pet))

    def _make_card(self, pet):
        pet_id, name, species, breed, _size, _age, _weight, _history, photo = pet

        card = MDCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(72),
            padding=dp(8),
            spacing=dp(8),
            radius=[dp(12)],
            md_bg_color=(0.96, 0.96, 0.96, 1),
        )

        # фото слева; нет фото — серая лапка
        if photo:
            avatar = Image(
                source=os.path.join(BASE_DIR, photo),
                fit_mode="cover",
                size_hint=(None, None),
                size=(dp(56), dp(56)),
                pos_hint={"center_y": 0.5},
            )
        else:
            avatar = MDIcon(
                icon="paw",
                icon_color=(0.6, 0.6, 0.6, 1),
                size_hint=(None, None),
                size=(dp(56), dp(56)),
                halign="center",
                pos_hint={"center_y": 0.5},
            )
        card.add_widget(avatar)

        # кличка + вид · порода посередине
        texts = MDBoxLayout(orientation="vertical")
        texts.add_widget(MDLabel(text=name, font_style="Title", adaptive_height=True))
        subtitle = species if species else ""
        if breed:
            subtitle = f"{subtitle} · {breed}" if subtitle else breed
        texts.add_widget(MDLabel(
            text=subtitle if subtitle else " ",
            font_style="Body",
            theme_text_color="Secondary",
            adaptive_height=True,
        ))
        card.add_widget(texts)

        # постаменты: поведение прикрутим на Шаге 5
        edit_btn = MDIconButton(
            icon="pencil",
            pos_hint={"center_y": 0.5},
            on_release=partial(self.open_edit, pet_id),
        )
        del_btn = MDIconButton(
            icon="trash-can",
            icon_color=(0.85, 0.25, 0.25, 1),
            pos_hint={"center_y": 0.5},
            on_release=partial(self.confirm_delete, pet_id),
        )
        card.add_widget(edit_btn)
        card.add_widget(del_btn)
        return card

    def open_edit(self, pet_id, *args):
        print(f"Правка питомца №{pet_id} — научимся на Шаге 5")

    def confirm_delete(self, pet_id, *args):
        print(f"Удаление питомца №{pet_id} — научимся на Шаге 5")