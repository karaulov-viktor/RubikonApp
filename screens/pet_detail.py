"""
Детальная карточка питомца — Спринт 2.6 (редизайн истории назначений)

Что изменилось по сравнению со спринтом 2.5:
  1. Центрирование теперь настоящее. В Kivy halign работает ТОЛЬКО
     вместе с text_size, поэтому каждая надпись получает text_size
     (см. _wrap_label).
  2. Длинные названия переносятся по словам, карточки растут
     по содержимому (см. _grow_with_content).
  3. Тап по карточке открывает отдельный экран «Детали назначения»
     (screens/appointment_detail.py) вместо MDDialog — диалог на
     части видеокарт падает с FBO 36054, как и снекбар.
  4. Все карточки создаются с НЕнулевой высотой: виджет с высотой 0
     при рождении тоже роняет FBO на слабых видеокартах.
"""

import os
from datetime import datetime, timedelta
from functools import partial

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.image import Image
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Фирменные цвета «Рубикон Агент» — в одном месте, чтобы не дублировать
GREEN_DARK = (0.118, 0.302, 0.125, 1)   # тёмно-зелёные заголовки
GREEN_BG = (0.906, 0.937, 0.878, 1)     # фон карточек лечения
GREY_BG = (0.96, 0.96, 0.96, 1)         # фон карточек истории
GREY_TEXT = (0.45, 0.45, 0.45, 1)       # вторичный текст
DARK_TEXT = (0.13, 0.13, 0.13, 1)       # основной текст


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

    # ═══════════════════════════════════════════════════════
    # ПОМОЩНИКИ ВЁРСТКИ (мини-урок: halign без text_size молчит)
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _wrap_label(text, **kwargs):
        """
        MDLabel: по центру, с переносом по словам и авто-высотой.

        Почему так: в Kivy halign/valign учитываются только когда
        задан text_size. Поэтому мы привязываем text_size к ширине
        метки — как только вёрстка выделит метке место, текст узнает
        свою ширину, сможет центрироваться и переноситься.
        adaptive_height подтягивает высоту метки к высоте текста.
        """
        label = MDLabel(
            text=text,
            halign="center",
            adaptive_height=True,
            **kwargs,
        )
        label.bind(
            width=lambda inst, w: setattr(inst, "text_size", (w, None))
        )
        return label

    @staticmethod
    def _grow_with_content(card, birth_height):
        """
        Карточка рождается с ненулевой высотой (требование FBO —
        нулевая высота при рождении падает с ошибкой 36054),
        а дальше растёт по содержимому.

        Важно: minimum_height НЕ включает padding карточки,
        поэтому верхний и нижний отступы добавляем вручную.
        """
        card.height = birth_height
        card.bind(
            minimum_height=lambda inst, val: setattr(
                inst, "height", val + inst.padding[1] + inst.padding[3]
            )
        )

    # ═══════════════════════════════════════════════════════
    # ЗАГРУЗКА ДАННЫХ ПИТОМЦА
    # ═══════════════════════════════════════════════════════

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
                pos_hint={"center_x": 0.5, "center_y": 0.5},
            )
            photo_box.add_widget(img)
        else:
            # Явный размер + pos_hint: иначе иконка прилипает к краю
            photo_box.add_widget(
                MDIcon(
                    icon="paw",
                    font_size="80sp",
                    theme_text_color="Custom",
                    text_color=(0.18, 0.49, 0.2, 1),
                    size_hint=(None, None),
                    size=(dp(90), dp(90)),
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
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
    # НАЗНАЧЕННОЕ ЛЕЧЕНИЕ
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
                self._wrap_label(
                    "Нет назначенного лечения",
                    font_size="13sp",
                    theme_text_color="Secondary",
                )
            )
            return

        for reminder in pet_reminders:
            card = self._create_treatment_card(reminder)
            treatment_box.add_widget(card)

    def _create_treatment_card(self, reminder):
        """Карточка активного лечения. Тап → экран деталей."""
        (reminder_id, pet_id, drug_id, start_date, end_date, time) = reminder

        app = App.get_running_app()
        drug = app.db.get_drug_by_id(drug_id)
        if not drug:
            return self._wrap_label(
                "Препарат не найден",
                font_size="13sp",
                theme_text_color="Secondary",
            )

        drug_name = drug[1]
        category = drug[2] or ""
        description = drug[3] or ""
        dose_per_kg = drug[7] if len(drug) > 7 else 0
        duration_days = drug[9] if len(drug) > 9 else 0

        # НЕНУЛЕВАЯ высота при рождении — иначе FBO падает (36054)
        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(96),
            padding=[dp(14), dp(12), dp(14), dp(12)],
            spacing=dp(4),
            radius=[dp(12)],
            md_bg_color=GREEN_BG,
            elevation=1,
            ripple_behavior=True,
        )
        self._grow_with_content(card, dp(96))

        card._detail = {
            "title": drug_name,
            "subtitle": category or "Назначенное лечение",
            "fields": self._build_treatment_fields(
                description, start_date, end_date, time,
                dose_per_kg, duration_days,
            ),
        }
        card.bind(on_release=self._open_detail)

        card.add_widget(self._wrap_label(
            drug_name,
            font_size="15sp",
            bold=True,
            theme_text_color="Custom",
            text_color=GREEN_DARK,
        ))
        card.add_widget(self._wrap_label(
            f"{start_date} — {end_date} · {time}",
            font_size="12sp",
            theme_text_color="Custom",
            text_color=GREY_TEXT,
        ))
        if category:
            card.add_widget(self._wrap_label(
                category,
                font_size="11sp",
                theme_text_color="Secondary",
            ))
        return card

    def _build_treatment_fields(self, description, start_date, end_date,
                                time, dose_per_kg, duration_days):
        """Пары (подпись, значение) для экрана деталей."""
        fields = []
        if description:
            fields.append(("Описание", description))
        fields.append(("Период лечения", f"{start_date} — {end_date}"))
        fields.append(("Время приёма", str(time)))
        if dose_per_kg and dose_per_kg > 0:
            fields.append(("Дозировка", f"{self._fmt(dose_per_kg)} мг/кг"))
            if self.current_pet_weight > 0:
                dose_mg = self.current_pet_weight * dose_per_kg
                fields.append((
                    f"На вес {self._fmt(self.current_pet_weight)} кг",
                    f"{self._fmt(dose_mg)} мг на один приём",
                ))
        if duration_days and duration_days > 0:
            fields.append(("Курс лечения", f"{duration_days} дн."))
        return fields

    # ═══════════════════════════════════════════════════════
    # ИСТОРИЯ НАЗНАЧЕНИЙ
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
            history_box.add_widget(
                self._wrap_label(
                    "Назначений пока нет",
                    font_size="13sp",
                    theme_text_color="Secondary",
                )
            )
            return

        for prescription in prescriptions:
            card = self._create_history_card(prescription)
            history_box.add_widget(card)

    def _create_history_card(self, prescription):
        """Карточка истории. Тап → экран деталей."""
        (presc_id, prescribed_date, drug_name, category,
         dose_per_kg, concentration, duration_days, notes) = prescription

        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(72),
            padding=[dp(14), dp(10), dp(14), dp(10)],
            spacing=dp(6),
            radius=[dp(10)],
            md_bg_color=GREY_BG,
            elevation=0,
            ripple_behavior=True,
        )
        self._grow_with_content(card, dp(72))

        # Короткая сводка второй строкой: дата · доза · курс
        if dose_per_kg and dose_per_kg > 0:
            summary = f"Доза: {self._fmt(dose_per_kg)} мг/кг"
        else:
            summary = "Доза: по инструкции"
        if duration_days and duration_days > 0:
            summary += f" · Курс: {duration_days} дн."

        card._detail = {
            "title": drug_name,
            "subtitle": f"Назначено {prescribed_date[:10]}",
            "fields": self._build_prescription_fields(
                category, dose_per_kg, concentration, duration_days, notes,
            ),
        }
        card.bind(on_release=self._open_detail)

        # Верхняя строка: название (переносится) + стрелка
        top = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        top.add_widget(self._wrap_label(
            drug_name,
            font_size="14sp",
            bold=True,
            theme_text_color="Custom",
            text_color=DARK_TEXT,
        ))
        top.add_widget(MDIcon(
            icon="chevron-right",
            theme_text_color="Custom",
            text_color=(0.5, 0.5, 0.5, 1),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5},
        ))
        card.add_widget(top)

        # Нижняя строка: дата и доза — одной спокойной строкой
        card.add_widget(self._wrap_label(
            f"{prescribed_date[:10]} · {summary}",
            font_size="12sp",
            theme_text_color="Custom",
            text_color=GREY_TEXT,
        ))
        return card

    def _build_prescription_fields(self, category, dose_per_kg,
                                   concentration, duration_days, notes):
        """Пары (подпись, значение) для экрана деталей истории."""
        fields = []
        if category:
            fields.append(("Категория", category))
        if dose_per_kg and dose_per_kg > 0:
            fields.append(("Дозировка", f"{self._fmt(dose_per_kg)} мг/кг"))
            if self.current_pet_weight > 0:
                dose_mg = self.current_pet_weight * dose_per_kg
                fields.append((
                    f"На вес {self._fmt(self.current_pet_weight)} кг",
                    f"{self._fmt(dose_mg)} мг",
                ))
                if concentration and concentration > 0:
                    volume = dose_mg / concentration
                    fields.append((
                        "Объём в шприц",
                        f"{self._fmt(volume)} мл "
                        f"(концентрация {self._fmt(concentration)} мг/мл)",
                    ))
        else:
            fields.append(("Дозировка", "по инструкции"))
        if duration_days and duration_days > 0:
            fields.append(("Курс лечения", f"{duration_days} дн."))
        if notes:
            fields.append(("Заметки", notes))
        return fields

    def _open_detail(self, card, *args):
        """Открыть экран «Детали назначения» для карточки."""
        app = App.get_running_app()
        screen_manager = app.root.ids.screen_manager
        detail = screen_manager.get_screen("appointment_detail")
        detail.show_detail(
            card._detail["title"],
            card._detail["subtitle"],
            card._detail["fields"],
        )
        screen_manager.current = "appointment_detail"

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
