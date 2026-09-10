"""
Детальная карточка питомца с назначенным лечением — Спринт 2
"""

import os
from datetime import datetime, timedelta
from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import Image
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PetDetailScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_pet_id = None
        self.current_pet_weight = 0
        self.current_species = ""
        self.selected_drug_id = None
        self.selected_drug_name = ""
        self._menu = None

    def on_enter(self):
        if self.current_pet_id:
            self.load_pet_details(self.current_pet_id)

    def load_pet_details(self, pet_id):
        """Загрузить полную информацию о питомце и назначенном лечении."""
        app = App.get_running_app()
        pet = app.db.get_pet_by_id(pet_id)
        if not pet:
            return

        self.current_pet_id = pet_id
        (pet_id_db, name, species, breed, size,
         age, weight, history, photo) = pet

        self.current_pet_weight = weight or 0
        self.current_species = species or ""

        # Заполняем поля
        self.ids.pet_name.text = name or ""

        species_text = species if species else ""
        if breed:
            species_text = f"{species_text} · {breed}" if species_text else breed
        self.ids.pet_species.text = species_text

        self.ids.pet_size.text = size if size else "—"
        self.ids.pet_age.text = f"{age} лет" if age else "—"
        self.ids.pet_weight.text = f"{weight} кг" if weight else "—"
        self.ids.pet_history.text = (
            history if history else "Нет дополнительных сведений"
        )

        # Фото
        photo_box = self.ids.photo_box
        photo_box.clear_widgets()
        if photo and os.path.exists(os.path.join(BASE_DIR, photo)):
            img = Image(
                source=os.path.join(BASE_DIR, photo),
                fit_mode="cover",
                size_hint=(None, None),
                size=(dp(120), dp(120)),
                pos_hint={"center_x": 0.5},
            )
            photo_box.add_widget(img)
        else:
            photo_box.add_widget(
                MDIcon(
                    icon="paw",
                    font_size="80sp",
                    theme_text_color="Custom",
                    text_color=(0.18, 0.49, 0.2, 1),
                    halign="center",
                )
            )

        # Сбрасываем выбор препарата
        self.selected_drug_id = None
        self.selected_drug_name = ""
        self.ids.drug_field.text = ""
        self._reset_dose_info()

        # Загружаем подходящие препараты
        self._load_drugs_menu()

        # ═══ ЗАГРУЖАЕМ НАЗНАЧЕННОЕ ЛЕЧЕНИЕ ═══
        self._load_prescribed_treatment()

    def _load_prescribed_treatment(self):
        """Загрузить назначенное лечение (активные напоминания)."""
        app = App.get_running_app()
        reminders = app.db.get_active_reminders()

        # Фильтруем напоминания для текущего питомца
        pet_reminders = [r for r in reminders if r[1] == self.current_pet_id]

        treatment_box = self.ids.treatment_list
        treatment_box.clear_widgets()

        if not pet_reminders:
            treatment_box.add_widget(
                MDLabel(
                    text="Назначенное лечение отсутствует",
                    halign="center",
                    theme_text_color="Secondary",
                    adaptive_height=True,
                    font_style="Body",
                    role="medium",
                )
            )
            return

        for reminder in pet_reminders:
            card = self._create_treatment_card(reminder)
            treatment_box.add_widget(card)

    def _create_treatment_card(self, reminder):
        """Создать карточку назначенного лечения."""
        (reminder_id, pet_id, drug_id, start_date, end_date, time) = reminder

        app = App.get_running_app()
        drug = app.db.get_drug_by_id(drug_id)
        if not drug:
            return MDLabel(text="Препарат не найден")

        drug_name = drug[1]
        category = drug[2] or ""

        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(100),
            padding=dp(12),
            spacing=dp(6),
            radius=[dp(10)],
            md_bg_color=(0.906, 0.937, 0.878, 1),  # светло-зелёный
            elevation=1,
        )

        # Название препарата и время
        header = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        header.add_widget(
            MDLabel(
                text=drug_name,
                font_style="Title",
                role="small",
                theme_text_color="Custom",
                text_color=(0.18, 0.49, 0.2, 1),
                bold=True,
            )
        )
        header.add_widget(
            MDLabel(
                text=f"⏰ {time}",
                font_style="Label",
                role="small",
                theme_text_color="Custom",
                text_color=(0.4, 0.4, 0.4, 1),
                halign="right",
            )
        )
        card.add_widget(header)

        # Период лечения
        card.add_widget(
            MDLabel(
                text=f"Период: {start_date} — {end_date}",
                font_style="Body",
                role="small",
                theme_text_color="Custom",
                text_color=(0.4, 0.4, 0.4, 1),
            )
        )

        # Категория
        if category:
            card.add_widget(
                MDLabel(
                    text=category,
                    font_style="Label",
                    role="small",
                    theme_text_color="Secondary",
                )
            )

        return card

    def _load_drugs_menu(self):
        """Подготовить список препаратов для выпадающего меню."""
        app = App.get_running_app()
        self._suitable_drugs = app.db.get_drugs_for_species(
            self.current_species
        )
        count = len(self._suitable_drugs)
        self.ids.drugs_count.text = (
            f"Подходит {count} "
            f"{'препарат' if count == 1 else 'препарата' if count < 5 else 'препаратов'}"
        )

    def open_drug_menu(self, field, focused):
        if not focused:
            return
        self._close_menu()

        if not self._suitable_drugs:
            App.get_running_app().show_toast("Нет подходящих препаратов")
            return

        menu_items = []
        for drug in self._suitable_drugs:
            drug_id = drug[0]
            drug_name = drug[1]
            category = drug[2] or ""
            menu_items.append({
                "text": f"{drug_name}  ({category})",
                "on_release": partial(self.select_drug, drug_id, drug_name),
            })

        self._menu = MDDropdownMenu(
            caller=field,
            items=menu_items,
            width=dp(300),
            position="auto",
        )
        self._menu.open()
        field.focus = False

    def _close_menu(self):
        if self._menu:
            self._menu.dismiss()
        self._menu = None

    def select_drug(self, drug_id, drug_name, *args):
        self._close_menu()
        self.selected_drug_id = drug_id
        self.selected_drug_name = drug_name
        self.ids.drug_field.text = drug_name
        self._calculate_dose(drug_id)

    def _calculate_dose(self, drug_id):
        """Рассчитать дозу на основе веса питомца."""
        app = App.get_running_app()
        drug = app.db.get_drug_by_id(drug_id)
        if not drug:
            return

        (drug_id, name, category, description, instruction,
         image, icon, dose_per_kg, concentration,
         duration_days, species_list) = drug

        weight = self.current_pet_weight

        self.ids.dose_box.adaptive_height = True
        self.ids.dose_box.size_hint_y = None

        if dose_per_kg and dose_per_kg > 0 and weight > 0:
            dose_mg = weight * dose_per_kg

            self.ids.dose_weight.text = f"{self._fmt(weight)} кг"
            self.ids.dose_single.text = f"{self._fmt(dose_mg)} мг"
            self.ids.dose_formula.text = (
                f"{self._fmt(weight)} × {self._fmt(dose_per_kg)} мг/кг"
            )

            if concentration and concentration > 0:
                volume_ml = dose_mg / concentration
                self.ids.dose_volume.text = f"{self._fmt(volume_ml)} мл"
                self.ids.dose_volume_row.opacity = 1
                self.ids.dose_volume_row.height = dp(30)
            else:
                self.ids.dose_volume.text = "—"
                self.ids.dose_volume_row.opacity = 0
                self.ids.dose_volume_row.height = 0
        else:
            self.ids.dose_weight.text = f"{self._fmt(weight)} кг"
            self.ids.dose_single.text = "по инструкции"
            self.ids.dose_formula.text = instruction or "—"
            self.ids.dose_volume.text = "—"
            self.ids.dose_volume_row.opacity = 0
            self.ids.dose_volume_row.height = 0

        self.ids.dose_duration.text = (
            f"{duration_days} "
            f"{'день' if duration_days == 1 else 'дня' if duration_days < 5 else 'дней'}"
        )

    def _reset_dose_info(self):
        self.ids.dose_box.opacity = 0
        self.ids.dose_box.size_hint_y = None
        self.ids.dose_box.height = dp(1)

    @staticmethod
    def _fmt(value):
        if value < 1:
            text = f"{value:.3f}"
        else:
            text = f"{value:.2f}"
        text = text.rstrip("0").rstrip(".")
        return text if text else "0"

    def add_to_calendar(self, *args):
        """Создать напоминание в календаре и сохранить в историю."""
        app = App.get_running_app()

        if not self.selected_drug_id:
            app.show_toast("Сначала выберите препарат")
            return

        if self.current_pet_weight <= 0:
            app.show_toast("Укажите вес питомца")
            return

        drug = app.db.get_drug_by_id(self.selected_drug_id)
        if not drug:
            return

        (drug_id, name, category, description, instruction,
         image, icon, dose_per_kg, concentration,
         duration_days, species_list) = drug

        if not duration_days or duration_days <= 0:
            duration_days = 7

        today = datetime.now()
        start_str = today.strftime("%d.%m.%Y")
        end_date = today + timedelta(days=duration_days - 1)
        end_str = end_date.strftime("%d.%m.%Y")
        time_str = "09:00"

        app.db.add_reminder(
            self.current_pet_id,
            self.selected_drug_id,
            start_str,
            end_str,
            time_str,
        )

        notes = f"Курс с {start_str} по {end_str}"
        app.db.add_prescription(
            self.current_pet_id,
            self.selected_drug_id,
            dose_per_kg,
            concentration,
            duration_days,
            notes
        )

        pet_name = self.ids.pet_name.text
        app.show_toast(
            f"✓ Напоминание создано: {pet_name} — "
            f"{self.selected_drug_name}, {duration_days} дн."
        )

        # Обновляем назначенное лечение
        self._load_prescribed_treatment()

    def go_back(self):
        self.manager.current = "profile"