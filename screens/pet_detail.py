"""
Детальная карточка питомца — Спринт 2.5 (исправленная версия)
"""

import os
from datetime import datetime, timedelta
from functools import partial

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.image import Image
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PetDetailScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_pet_id = None
        self.current_pet_weight = 0
        self.current_pet_name = ""
        self.current_species = ""
        self.selected_drug_id = None
        self.selected_drug_name = ""
        self._menu = None
        self._history_expanded = False

    def on_enter(self):
        if self.current_pet_id:
            self.load_pet_details(self.current_pet_id)

    def load_pet_details(self, pet_id):
        """Загрузить полную информацию о питомце."""
        app = App.get_running_app()
        pet = app.db.get_pet_by_id(pet_id)
        if not pet:
            return

        self.current_pet_id = pet_id
        (pet_id_db, name, species, breed, size,
         age, weight, history, photo) = pet

        self.current_pet_weight = weight or 0
        self.current_pet_name = name or ""
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

        # Загружаем подходящие препараты
        self._load_drugs_menu()

        # Загружаем назначенное лечение
        self._load_prescribed_treatment()

        # Загружаем историю
        self._load_prescriptions_history()

    # ═══════════════════════════════════════════════════════
    # ВЫБОР ПРЕПАРАТА
    # ═══════════════════════════════════════════════════════

    def _load_drugs_menu(self):
        """Подготовить список препаратов."""
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

    # ═══════════════════════════════════════════════════════
    # КНОПКА → ПЕРЕХОД В КАЛЕНДАРЬ
    # ═══════════════════════════════════════════════════════

    def go_to_calendar(self, *args):
        """Перейти в календарь с предзаполненными данными."""
        app = App.get_running_app()

        if not self.selected_drug_id:
            app.show_toast("Сначала выберите препарат")
            return

        # Получаем данные препарата
        drug = app.db.get_drug_by_id(self.selected_drug_id)
        if not drug:
            return

        duration_days = drug[9] if len(drug) > 9 else 7
        if not duration_days or duration_days <= 0:
            duration_days = 7

        # Формируем даты
        today = datetime.now()
        start_str = today.strftime("%d.%m.%Y")
        end_date = today + timedelta(days=duration_days - 1)
        end_str = end_date.strftime("%d.%m.%Y")

        # Передаём данные в календарь
        calendar_screen = app.root.ids.screen_manager.get_screen("calendar")
        calendar_screen.prefill_from_pet(
            pet_id=self.current_pet_id,
            pet_name=self.current_pet_name,
            drug_id=self.selected_drug_id,
            drug_name=self.selected_drug_name,
            start_date=start_str,
            end_date=end_str,
        )

        # Переходим в календарь
        app.root.ids.screen_manager.current = "calendar"

    # ═══════════════════════════════════════════════════════
    # НАЗНАЧЕННОЕ ЛЕЧЕНИЕ (исправлено)
    # ═══════════════════════════════════════════════════════

    def _load_prescribed_treatment(self):
        """Загрузить назначенное лечение."""
        app = App.get_running_app()
        reminders = app.db.get_active_reminders()
        pet_reminders = [r for r in reminders if r[1] == self.current_pet_id]

        treatment_box = self.ids.treatment_list
        treatment_box.clear_widgets()

        if not pet_reminders:
            treatment_box.add_widget(
                MDLabel(
                    text="Нет назначенного лечения",
                    halign="center",
                    theme_text_color="Secondary",
                    adaptive_height=True,
                    font_size="13sp",
                )
            )
            return

        for reminder in pet_reminders:
            card = self._create_treatment_card(reminder)
            treatment_box.add_widget(card)

    def _create_treatment_card(self, reminder):
        """Создать кликабельную карточку назначенного лечения."""
        (reminder_id, pet_id, drug_id, start_date, end_date, time) = reminder

        app = App.get_running_app()
        drug = app.db.get_drug_by_id(drug_id)
        if not drug:
            return MDLabel(text="Препарат не найден")

        drug_name = drug[1]
        category = drug[2] or ""
        description = drug[3] or ""
        dose_per_kg = drug[7] if len(drug) > 7 else 0
        duration_days = drug[9] if len(drug) > 9 else 0

        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(85),
            padding=[dp(14), dp(10), dp(14), dp(10)],
            spacing=dp(6),
            radius=[dp(12)],
            md_bg_color=(0.906, 0.937, 0.878, 1),
            elevation=1,
            ripple_behavior=True,
        )

        # Сохраняем данные для модального окна
        card._drug_data = {
            "name": drug_name,
            "category": category,
            "description": description,
            "dose_per_kg": dose_per_kg,
            "duration_days": duration_days,
            "start_date": start_date,
            "end_date": end_date,
            "time": time,
        }

        card.bind(on_release=self._show_drug_info)

        # Центрированный контейнер
        center_box = MDBoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            spacing=dp(4),
            padding=[0, dp(8), 0, dp(8)],
        )

        # Название препарата (по центру)
        center_box.add_widget(
            MDLabel(
                text=drug_name,
                font_size="15sp",
                theme_text_color="Custom",
                text_color=(0.18, 0.49, 0.2, 1),
                bold=True,
                halign="center",
            )
        )

        # Период (по центру)
        center_box.add_widget(
            MDLabel(
                text=f"{start_date} — {end_date}  ⏰ {time}",
                font_size="12sp",
                theme_text_color="Custom",
                text_color=(0.4, 0.4, 0.4, 1),
                halign="center",
            )
        )

        # Категория (по центру)
        if category:
            center_box.add_widget(
                MDLabel(
                    text=category,
                    font_size="11sp",
                    theme_text_color="Secondary",
                    halign="center",
                )
            )

        card.add_widget(center_box)
        return card

    def _show_drug_info(self, card, *args):
        """Показать модальное окно с информацией о препарате."""
        data = card._drug_data

        # Формируем текст
        lines = []

        if data['category']:
            lines.append(f"Категория: {data['category']}")

        if data['description']:
            lines.append("")
            lines.append(data['description'])

        lines.append("")
        lines.append(f"Период лечения: {data['start_date']} — {data['end_date']}")
        lines.append(f"Время приёма: {data['time']}")

        if data['dose_per_kg'] and data['dose_per_kg'] > 0:
            lines.append("")
            lines.append(f"Дозировка: {self._fmt(data['dose_per_kg'])} мг/кг")
            if self.current_pet_weight > 0:
                dose_mg = self.current_pet_weight * data['dose_per_kg']
                lines.append(f"На вес {self._fmt(self.current_pet_weight)} кг: {self._fmt(dose_mg)} мг")

        if data['duration_days'] and data['duration_days'] > 0:
            lines.append(f"Курс лечения: {data['duration_days']} дней")

        detail_text = "\n".join(lines)

        # Создаём контент диалога
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(20), dp(16), dp(20), dp(16)],
            spacing=dp(16),
        )

        # Заголовок
        content.add_widget(
            MDLabel(
                text=data['name'],
                font_size="20sp",
                halign="center",
                adaptive_height=True,
                bold=True,
                theme_text_color="Custom",
                text_color=(0.18, 0.49, 0.2, 1),
            )
        )

        # Основной текст
        content.add_widget(
            MDLabel(
                text=detail_text,
                font_size="14sp",
                halign="left",
                adaptive_height=True,
                text_size=(dp(300), None),
                theme_text_color="Custom",
                text_color=(0.2, 0.2, 0.2, 1),
            )
        )

        # Кнопка закрытия
        content.add_widget(
            MDButton(
                MDButtonText(text="Закрыть"),
                style="filled",
                theme_bg_color="Custom",
                md_bg_color=(0.18, 0.49, 0.2, 1),
                on_release=lambda *_: dialog.dismiss(),
                size_hint_x=1,
            )
        )

        dialog = MDDialog(content)
        dialog.open()

    # ═══════════════════════════════════════════════════════
    # ИСТОРИЯ НАЗНАЧЕНИЙ (исправлено)
    # ═══════════════════════════════════════════════════════

    def _load_prescriptions_history(self):
        """Загрузить историю назначений."""
        app = App.get_running_app()
        prescriptions = app.db.get_prescriptions_for_pet(self.current_pet_id)

        history_box = self.ids.prescriptions_list
        history_box.clear_widgets()

        # Обновляем заголовок с количеством
        count = len(prescriptions)
        self.ids.history_toggle_text.text = (
            f"История назначений ({count})"
        )

        if not prescriptions:
            self.ids.history_toggle_text.text = "История назначений (0)"
            return

        for prescription in prescriptions:
            card = self._create_history_card(prescription)
            history_box.add_widget(card)

    def _create_history_card(self, prescription):
        """Создать карточку истории."""
        (presc_id, prescribed_date, drug_name, category,
         dose_per_kg, concentration, duration_days, notes) = prescription

        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(70),  # Увеличена высота
            padding=[dp(14), dp(8), dp(14), dp(8)],  # Увеличен padding
            spacing=dp(4),  # Увеличен spacing
            radius=[dp(10)],
            md_bg_color=(0.96, 0.96, 0.96, 1),
            elevation=0,
            ripple_behavior=True,
        )

        card._presc_data = {
            "id": presc_id,
            "date": prescribed_date,
            "drug": drug_name,
            "category": category,
            "dose_per_kg": dose_per_kg,
            "concentration": concentration,
            "duration_days": duration_days,
            "notes": notes or "",
        }

        card.bind(on_release=self._show_prescription_detail)

        # Первая строка - дата и название
        header = MDBoxLayout(
            adaptive_height=True,
            spacing=dp(8),
        )
        header.add_widget(
            MDLabel(
                text=prescribed_date[:10],
                font_size="12sp",
                theme_text_color="Custom",
                text_color=(0.5, 0.5, 0.5, 1),
                size_hint_x=None,
                width=dp(80),
                halign="left",
            )
        )
        header.add_widget(
            MDLabel(
                text=drug_name,
                font_size="14sp",
                theme_text_color="Custom",
                text_color=(0.13, 0.13, 0.13, 1),
                bold=True,
                halign="left",
            )
        )
        header.add_widget(
            MDIcon(
                icon="chevron-right",
                icon_color=(0.5, 0.5, 0.5, 1),
                size_hint_x=None,
                width=dp(24),
                halign="right",
            )
        )
        card.add_widget(header)

        # Вторая строка - доза и курс
        details = MDBoxLayout(
            adaptive_height=True,
            spacing=dp(12),
        )

        if dose_per_kg and dose_per_kg > 0:
            dose_text = f"Доза: {self._fmt(dose_per_kg)} мг/кг"
        else:
            dose_text = "Доза: по инструкции"

        details.add_widget(
            MDLabel(
                text=dose_text,
                font_size="12sp",
                theme_text_color="Custom",
                text_color=(0.45, 0.45, 0.45, 1),
                halign="left",
            )
        )

        if duration_days and duration_days > 0:
            details.add_widget(
                MDLabel(
                    text=f"Курс: {duration_days} дн.",
                    font_size="12sp",
                    theme_text_color="Custom",
                    text_color=(0.45, 0.45, 0.45, 1),
                    halign="left",
                )
            )

        card.add_widget(details)
        return card

    def _show_prescription_detail(self, card, *args):
        """Показать модальное окно с деталями."""
        data = card._presc_data

        # Формируем текст
        lines = []
        lines.append(f"Дата назначения: {data['date'][:10]}")

        if data['category']:
            lines.append(f"Категория: {data['category']}")

        if data['dose_per_kg'] and data['dose_per_kg'] > 0:
            lines.append(f"Дозировка: {self._fmt(data['dose_per_kg'])} мг/кг")
            if self.current_pet_weight > 0:
                dose_mg = self.current_pet_weight * data['dose_per_kg']
                lines.append(f"На вес {self._fmt(self.current_pet_weight)} кг: {self._fmt(dose_mg)} мг")
                if data['concentration'] and data['concentration'] > 0:
                    volume = dose_mg / data['concentration']
                    lines.append(f"Объём в шприц: {self._fmt(volume)} мл")
        else:
            lines.append("Дозировка: по инструкции")

        if data['duration_days'] and data['duration_days'] > 0:
            lines.append(f"Курс лечения: {data['duration_days']} дней")

        if data['notes']:
            lines.append("")
            lines.append(data['notes'])

        detail_text = "\n".join(lines)

        # Создаём контент диалога
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(20), dp(16), dp(20), dp(16)],
            spacing=dp(16),
        )

        # Заголовок
        content.add_widget(
            MDLabel(
                text=data['drug'],
                font_size="20sp",
                halign="center",
                adaptive_height=True,
                bold=True,
                theme_text_color="Custom",
                text_color=(0.18, 0.49, 0.2, 1),
            )
        )

        # Основной текст
        content.add_widget(
            MDLabel(
                text=detail_text,
                font_size="14sp",
                halign="left",
                adaptive_height=True,
                text_size=(dp(300), None),
                theme_text_color="Custom",
                text_color=(0.2, 0.2, 0.2, 1),
            )
        )

        # Кнопка закрытия
        content.add_widget(
            MDButton(
                MDButtonText(text="Закрыть"),
                style="filled",
                theme_bg_color="Custom",
                md_bg_color=(0.18, 0.49, 0.2, 1),
                on_release=lambda *_: dialog.dismiss(),
                size_hint_x=1,
            )
        )

        dialog = MDDialog(content)
        dialog.open()

    def toggle_history(self, *args):
        """Развернуть/свернуть историю назначений."""
        self._history_expanded = not self._history_expanded
        history_container = self.ids.history_container

        if self._history_expanded:
            # Развернуть
            history_container.opacity = 1
            history_container.size_hint_y = None
            history_container.height = history_container.minimum_height
            self.ids.history_arrow.icon = "chevron-up"
        else:
            # Свернуть
            history_container.opacity = 0
            history_container.size_hint_y = None
            history_container.height = 0
            self.ids.history_arrow.icon = "chevron-down"

    # ═══════════════════════════════════════════════════════
    # УТИЛИТЫ
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _fmt(value):
        if value < 1:
            text = f"{value:.3f}"
        else:
            text = f"{value:.2f}"
        text = text.rstrip("0").rstrip(".")
        return text if text else "0"

    def go_back(self):
        self.manager.current = "profile"