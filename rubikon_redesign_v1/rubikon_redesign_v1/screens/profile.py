"""
Профиль питомцев — Спринт 2
Клик на карточку открывает детальную анкету с назначенным лечением
"""

import os
from functools import partial

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.image import Image
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogButtonContainer,
    MDDialogHeadlineText,
    MDDialogSupportingText,
)
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.screen import MDScreen

from models.theme import CARD, CARD_BORDER, DANGER, PRIMARY, PRIMARY_SOFT, TEXT_MAIN, TEXT_SUB

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ProfileScreen(MDScreen):
    def on_pre_enter(self, *args):
        """Kivy вызывает это ПЕРЕД каждым показом экрана."""
        self.refresh_cards()

    def refresh_cards(self):
        box = self.ids.cards_box
        box.clear_widgets()
        pets = App.get_running_app().db.get_pets()
        if not pets:
            # Пустое состояние
            empty_box = MDBoxLayout(
                orientation="vertical",
                adaptive_height=True,
                spacing=dp(12),
                padding=dp(20),
            )
            empty_box.add_widget(
                MDIcon(
                    icon="paw",
                    font_size="64sp",
                    theme_text_color="Custom",
                    text_color=PRIMARY_SOFT,
                    halign="center",
                )
            )
            empty_box.add_widget(
                MDLabel(
                    text="Питомцев пока нет",
                    halign="center",
                    font_style="Title",
                    role="medium",
                    theme_text_color="Custom",
                    text_color=TEXT_MAIN,
                )
            )
            empty_box.add_widget(
                MDLabel(
                    text="Нажмите + чтобы добавить первого питомца",
                    halign="center",
                    font_style="Body",
                    role="medium",
                    theme_text_color="Custom",
                    text_color=TEXT_SUB,
                )
            )
            box.add_widget(empty_box)
            return
        for pet in pets:
            box.add_widget(self._make_card(pet))

    def _make_card(self, pet):
        pet_id, name, species, breed, _size, _age, _weight, _history, photo = pet

        card = MDCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(80),
            padding=dp(10),
            spacing=dp(10),
            radius=[dp(14)],
            md_bg_color=CARD,
            line_color=CARD_BORDER,
            elevation=0,
        )

        # ═══ КЛИК НА КАРТОЧКУ → ОТКРЫТЬ АНКЕТУ ═══
        card.bind(on_release=lambda instance, pid=pet_id: self.open_pet_detail(pid))

        # Аватар
        if photo:
            avatar = Image(
                source=os.path.join(BASE_DIR, photo),
                fit_mode="cover",
                size_hint=(None, None),
                size=(dp(60), dp(60)),
                pos_hint={"center_y": 0.5},
            )
        else:
            avatar = MDIcon(
                icon="paw",
                icon_color=PRIMARY,
                size_hint=(None, None),
                size=(dp(60), dp(60)),
                halign="center",
                pos_hint={"center_y": 0.5},
            )
        card.add_widget(avatar)

        # Информация
        texts = MDBoxLayout(orientation="vertical", spacing=dp(2))
        texts.add_widget(
            MDLabel(
                text=name,
                font_style="Title",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=TEXT_MAIN,
            )
        )
        subtitle = species if species else ""
        if breed:
            subtitle = f"{subtitle} · {breed}" if subtitle else breed
        texts.add_widget(
            MDLabel(
                text=subtitle if subtitle else " ",
                font_style="Body",
                role="small",
                theme_text_color="Secondary",
                adaptive_height=True,
            )
        )
        card.add_widget(texts)

        # Кнопки
        edit_btn = MDIconButton(
            icon="pencil",
            icon_color=PRIMARY,
            pos_hint={"center_y": 0.5},
            on_release=partial(self.open_edit, pet_id),
        )
        del_btn = MDIconButton(
            icon="trash-can",
            icon_color=DANGER,
            pos_hint={"center_y": 0.5},
            on_release=partial(self.confirm_delete, pet_id, name),
        )
        card.add_widget(edit_btn)
        card.add_widget(del_btn)
        return card

    def open_pet_detail(self, pet_id, *args):
        """Открыть детальную карточку питомца с назначенным лечением."""
        app = App.get_running_app()
        pet_detail = app.root.ids.screen_manager.get_screen("pet_detail")
        pet_detail.current_pet_id = pet_id
        app.root.ids.screen_manager.current = "pet_detail"

    def open_create_form(self, *args):
        """FAB: открыть форму в режиме СОЗДАНИЯ.

        Сначала ПОЛНОСТЬЮ очищаем форму, и только потом переключаем экран.
        Иначе после отменённой правки в форме остаётся живой
        editing_pet_id, и «новый» питомец перезапишет чужую карточку.
        """
        app = App.get_running_app()
        pet_form = app.root.ids.screen_manager.get_screen("pet_form")
        pet_form.reset_form()
        app.root.ids.screen_manager.current = "pet_form"

    def open_edit(self, pet_id, *args):
        """Открыть форму редактирования с данными питомца."""
        app = App.get_running_app()
        pet_form = app.root.ids.screen_manager.get_screen("pet_form")
        pet = app.db.get_pet_by_id(pet_id)
        if pet:
            pet_form.load_pet_data(pet)
        app.root.ids.screen_manager.current = "pet_form"

    def confirm_delete(self, pet_id, pet_name, *args):
        """Диалог подтверждения удаления."""
        def do_delete(*_args):
            dialog.dismiss()
            app = App.get_running_app()
            app.db.delete_pet(pet_id)
            self.refresh_cards()
            app.show_toast("Питомец удалён")

        dialog = MDDialog(
            MDDialogHeadlineText(text="Удалить питомца?"),
            MDDialogSupportingText(
                text=f"Вы уверены, что хотите удалить «{pet_name}»? "
                     f"Это действие нельзя отменить."
            ),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Отмена"),
                    on_release=lambda *_: dialog.dismiss(),
                ),
                MDButton(
                    MDButtonText(text="Удалить"),
                    on_release=do_delete,
                    theme_bg_color="Custom",
                    md_bg_color=DANGER,
                ),
                spacing=dp(8),
            ),
        )
        dialog.open()