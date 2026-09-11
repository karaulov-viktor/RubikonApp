"""
Спринт 1 — Календарь лечения (полноценный)
ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ ДЛЯ KIVYMD 2.0.0

Что реализовано:
  - Сетка месяца с навигацией (предыдущий/следующий)
  - Подсветка дней с напоминаниями
  - Форма создания напоминания (питомец, препарат, период, время)
  - Список активных будильников с возможностью удаления
  - Звуковой сигнал в момент приёма (через winsound на Windows)
  - Проверка будильников каждую секунду

ИСПРАВЛЕНИЯ ДЛЯ KIVYMD 2.0.0:
  - MDDatePicker → MDModalDatePicker
  - MDTimePicker → MDBaseTimePicker (из подмодуля)
"""

import sys
from datetime import datetime
from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers import MDModalDatePicker
from kivymd.uix.pickers.timepicker.timepicker import MDBaseTimePicker
from kivymd.uix.screen import MDScreen


class CalendarScreen(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_date = datetime.now()
        self.selected_pet_id = None
        self.selected_drug_id = None
        self.selected_hours = ""  # ← НОВОЕ
        self.selected_minutes = ""  # ← НОВОЕ
        self._menu = None
        Clock.schedule_interval(self.check_alarms, 1.0)

    def prefill_from_pet(self, pet_id, pet_name, drug_id, drug_name, start_date, end_date):
        """Заполнить поля календаря данными из карточки питомца."""
        self.selected_pet_id = pet_id
        self.selected_drug_id = drug_id

        self.ids.reminder_pet_field.text = pet_name
        self.ids.reminder_drug_field.text = drug_name
        self.ids.reminder_start_field.text = start_date
        self.ids.reminder_end_field.text = end_date
        # Время оставляем по умолчанию — пользователь выберет сам

    def on_enter(self):
        """При входе на экран — обновляем сетку и список."""
        self.update_calendar()
        self.update_reminders_list()

    # ═══════════════════════════════════════════════════════
    # СЕТКА МЕСЯЦА
    # ═══════════════════════════════════════════════════════

    def update_calendar(self):
        """Обновить сетку календаря для текущего месяца."""
        # Заголовок месяца
        month_names = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        self.ids.month_label.text = f"{month_names[self.current_date.month - 1]} {self.current_date.year}"

        # Очищаем сетку
        grid = self.ids.days_grid
        grid.clear_widgets()

        # Первый день месяца
        first_day = datetime(self.current_date.year, self.current_date.month, 1)
        # День недели (0=понедельник, 6=воскресенье)
        weekday = first_day.weekday()
        # Количество дней в месяце
        if self.current_date.month == 12:
            next_month = datetime(self.current_date.year + 1, 1, 1)
        else:
            next_month = datetime(self.current_date.year, self.current_date.month + 1, 1)
        days_in_month = (next_month - first_day).days

        # Пустые ячейки до первого дня
        for _ in range(weekday):
            grid.add_widget(MDLabel(text="", halign="center"))

        # Дни месяца
        today = datetime.now().date()
        for day in range(1, days_in_month + 1):
            date = datetime(self.current_date.year, self.current_date.month, day)
            date_key = date.strftime("%Y-%m-%d")
            is_today = date.date() == today

            # Проверяем, есть ли напоминания на этот день
            reminders = self.get_reminders_for_date(date_key)
            has_reminders = len(reminders) > 0

            # Создаём ячейку
            cell = MDCard(
                size_hint=(1, None),
                height=dp(40),
                radius=[dp(8)],
                md_bg_color=(0.18, 0.49, 0.2, 1) if is_today else (0.906, 0.937, 0.878, 1) if has_reminders else (1, 1, 1, 1),
                elevation=0,
            )
            label = MDLabel(
                text=str(day),
                halign="center",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1) if is_today else (0.13, 0.13, 0.13, 1),
                bold=is_today,
            )
            cell.add_widget(label)
            grid.add_widget(cell)

    def prev_month(self):
        """Переключить на предыдущий месяц."""
        if self.current_date.month == 1:
            self.current_date = datetime(self.current_date.year - 1, 12, 1)
        else:
            self.current_date = datetime(self.current_date.year, self.current_date.month - 1, 1)
        self.update_calendar()

    def next_month(self):
        """Переключить на следующий месяц."""
        if self.current_date.month == 12:
            self.current_date = datetime(self.current_date.year + 1, 1, 1)
        else:
            self.current_date = datetime(self.current_date.year, self.current_date.month + 1, 1)
        self.update_calendar()

    # ═══════════════════════════════════════════════════════
    # ВЫПАДАЮЩИЕ СПИСКИ
    # ═══════════════════════════════════════════════════════

    def _close_menu(self):
        if self._menu:
            self._menu.dismiss()
        self._menu = None

    def open_pet_menu(self, field, focused):
        if not focused:
            return
        self._close_menu()
        app = App.get_running_app()
        pets = app.db.get_pets()
        if not pets:
            field.text = ""
            app.show_toast("Сначала добавьте питомца в Профиле")
            return
        menu_items = [
            {"text": f"{p[1]} ({p[2]})", "on_release": partial(self.select_pet, p[0], p[1])}
            for p in pets
        ]
        self._menu = MDDropdownMenu(caller=field, items=menu_items, width=dp(280))
        self._menu.open()
        field.focus = False

    def select_pet(self, pet_id, pet_name):
        self._close_menu()
        self.selected_pet_id = pet_id
        self.ids.reminder_pet_field.text = pet_name

    def open_drug_menu(self, field, focused):
        if not focused:
            return
        self._close_menu()
        app = App.get_running_app()
        drugs = app.db.get_all_drugs()
        menu_items = [
            {"text": d[1], "on_release": partial(self.select_drug, d[0], d[1])}
            for d in drugs
        ]
        self._menu = MDDropdownMenu(caller=field, items=menu_items, width=dp(280))
        self._menu.open()
        field.focus = False

    def select_drug(self, drug_id, drug_name):
        self._close_menu()
        self.selected_drug_id = drug_id
        self.ids.reminder_drug_field.text = drug_name

    # ═══════════════════════════════════════════════════════
    # ВЫБОР ДАТ И ВРЕМЕНИ (ИСПРАВЛЕНО ДЛЯ KIVYMD 2.0.0)
    # ═══════════════════════════════════════════════════════

    def show_start_date_picker(self, focus):
        """Показать пикер даты начала (KivyMD 2.0.0)."""
        if not focus:
            return
        date_dialog = MDModalDatePicker(
            text_button_ok="ОК",
            text_button_cancel="Отмена"
        )
        date_dialog.bind(on_ok=self.on_start_date_selected)
        date_dialog.open()

    def on_start_date_selected(self, instance):
        """Обработчик выбора даты начала."""
        dates = instance.get_date()
        if dates:
            # get_date() возвращает список, берём первый элемент
            date_obj = dates[0] if isinstance(dates, list) else dates
            self.ids.reminder_start_field.text = date_obj.strftime("%d.%m.%Y")
        instance.dismiss()

    def show_end_date_picker(self, focus):
        """Показать пикер даты окончания (KivyMD 2.0.0)."""
        if not focus:
            return
        date_dialog = MDModalDatePicker(
            text_button_ok="ОК",
            text_button_cancel="Отмена"
        )
        date_dialog.bind(on_ok=self.on_end_date_selected)
        date_dialog.open()

    def on_end_date_selected(self, instance):
        """Обработчик выбора даты окончания."""
        dates = instance.get_date()
        if dates:
            date_obj = dates[0] if isinstance(dates, list) else dates
            self.ids.reminder_end_field.text = date_obj.strftime("%d.%m.%Y")
        instance.dismiss()

    # ═══════════════════════════════════════════════════════
    # ВЫБОР ВРЕМЕНИ — ДВА ВЫПАДАЮЩИХ СПИСКА
    # ═══════════════════════════════════════════════════════

    def open_hours_menu(self, field, focused):
        """Открыть выпадающий список часов (00-23)."""
        if not focused:
            return
        self._close_menu()

        menu_items = []
        for h in range(24):
            hour_str = f"{h:02d}"
            menu_items.append({
                "text": hour_str,
                "on_release": partial(self.select_hours, hour_str),
            })

        self._menu = MDDropdownMenu(
            caller=field,
            items=menu_items,
            width=dp(120),
            position="auto",
        )
        self._menu.open()
        field.focus = False

    def select_hours(self, hour_str, *args):
        """Выбрать час."""
        self._close_menu()
        self.selected_hours = hour_str
        self.ids.time_hours_field.text = hour_str
        self._update_combined_time()

    def open_minutes_menu(self, field, focused):
        """Открыть выпадающий список минут (00, 01, 02... 59)."""
        if not focused:
            return
        self._close_menu()

        menu_items = []
        for m in range(0, 60, 1):  # шаг 1 минута — 60 пунктов
            minute_str = f"{m:02d}"
            menu_items.append({
                "text": minute_str,
                "on_release": partial(self.select_minutes, minute_str),
            })

        self._menu = MDDropdownMenu(
            caller=field,
            items=menu_items,
            width=dp(120),
            position="auto",
        )
        self._menu.open()
        field.focus = False

    def select_minutes(self, minute_str, *args):
        """Выбрать минуты."""
        self._close_menu()
        self.selected_minutes = minute_str
        self.ids.time_minutes_field.text = minute_str
        self._update_combined_time()

    def _update_combined_time(self):
        """Обновить скрытое поле с объединённым временем."""
        hours = getattr(self, 'selected_hours', '')
        minutes = getattr(self, 'selected_minutes', '')
        if hours and minutes:
            self.ids.reminder_time_field.text = f"{hours}:{minutes}"

    def validate_time(self, instance):
        """Проверить и отформатировать введённое время."""
        text = instance.text.strip().replace(".", ":")
        try:
            parts = text.split(":")
            if len(parts) != 2:
                raise ValueError
            hours, minutes = int(parts[0]), int(parts[1])
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError
            instance.text = f"{hours:02d}:{minutes:02d}"
        except (ValueError, IndexError):
            instance.text = ""
            App.get_running_app().show_toast("Введите время в формате ЧЧ:ММ")

    # ═══════════════════════════════════════════════════════
    # СОХРАНЕНИЕ НАПОМИНАНИЯ
    # ═══════════════════════════════════════════════════════

    def save_reminder(self):
        app = App.get_running_app()
        pet_name = self.ids.reminder_pet_field.text
        drug_name = self.ids.reminder_drug_field.text
        start_str = self.ids.reminder_start_field.text
        end_str = self.ids.reminder_end_field.text
        # Собираем время из двух полей
        hours = getattr(self, 'selected_hours', '')
        minutes = getattr(self, 'selected_minutes', '')
        time_str = f"{hours}:{minutes}" if hours and minutes else ""

        # Валидация
        if not self.selected_pet_id:
            app.show_toast("Выберите питомца")
            return
        if not self.selected_drug_id:
            app.show_toast("Выберите препарат")
            return
        if not start_str or not end_str or not time_str:
            app.show_toast("Заполните все поля")
            return
        if not start_str or not end_str or not time_str:
            app.show_toast("Выберите время приёма")
            return

        # Сохраняем в БД
        app.db.add_reminder(
            self.selected_pet_id,
            self.selected_drug_id,
            start_str,
            end_str,
            time_str,
        )

        # Сбрасываем форму
        self.ids.reminder_pet_field.text = ""
        self.ids.reminder_drug_field.text = ""
        self.ids.reminder_start_field.text = ""
        self.ids.reminder_end_field.text = ""
        self.ids.time_hours_field.text = ""  # ← НОВОЕ
        self.ids.time_minutes_field.text = ""  # ← НОВОЕ
        self.ids.reminder_time_field.text = ""
        self.selected_pet_id = None
        self.selected_drug_id = None
        self.selected_hours = ""  # ← НОВОЕ
        self.selected_minutes = ""  # ← НОВОЕ

        # Обновляем интерфейс
        self.update_calendar()
        self.update_reminders_list()
        app.show_toast("Будильник заведён")

    # ═══════════════════════════════════════════════════════
    # СПИСОК АКТИВНЫХ БУДИЛЬНИКОВ
    # ═══════════════════════════════════════════════════════

    def update_reminders_list(self):
        """Обновить список активных будильников."""
        box = self.ids.reminders_list
        box.clear_widgets()
        app = App.get_running_app()
        reminders = app.db.get_active_reminders()

        if not reminders:
            box.add_widget(
                MDLabel(
                    text="Нет активных будильников",
                    halign="center",
                    theme_text_color="Secondary",
                    adaptive_height=True,
                )
            )
            return

        for r in reminders:
            reminder_id, pet_id, drug_id, start, end, time = r
            pet = app.db.get_pet_by_id(pet_id)
            drug = app.db.get_drug_by_id(drug_id)
            pet_name = pet[1] if pet else "?"
            drug_name = drug[1] if drug else "?"

            card = MDCard(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(60),
                padding=dp(10),
                spacing=dp(10),
                radius=[dp(10)],
                md_bg_color=(0.97, 0.97, 0.97, 1),
            )
            card.add_widget(
                MDLabel(
                    text=f"{pet_name} · {drug_name}\n{start} — {end} в {time}",
                    font_style="Body",
                    adaptive_height=True,
                    theme_text_color="Custom",
                    text_color=(0.13, 0.13, 0.13, 1),
                )
            )
            card.add_widget(
                MDIconButton(
                    icon="trash-can",
                    icon_color=(0.85, 0.25, 0.25, 1),
                    pos_hint={"center_y": 0.5},
                    on_release=partial(self.delete_reminder, reminder_id),
                )
            )
            box.add_widget(card)

    def delete_reminder(self, reminder_id, *args):
        app = App.get_running_app()
        # Сначала архивируем в историю
        app.db.archive_reminder(reminder_id)
        # Потом удаляем из активных
        app.db.delete_reminder(reminder_id)
        self.update_calendar()
        self.update_reminders_list()
        app.show_toast("Будильник удалён (сохранён в истории)")

    # ═══════════════════════════════════════════════════════
    # ПРОВЕРКА БУДИЛЬНИКОВ (каждую секунду)
    # ═══════════════════════════════════════════════════════

    def check_alarms(self, dt):
        """Проверить, не пора ли сработать будильнику."""
        app = App.get_running_app()
        now = datetime.now()
        today_key = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")

        reminders = app.db.get_active_reminders()
        for r in reminders:
            reminder_id, pet_id, drug_id, start, end, time = r
            # Проверяем, попадает ли сегодня в период
            start_date = datetime.strptime(start, "%d.%m.%Y").date()
            end_date = datetime.strptime(end, "%d.%m.%Y").date()
            today_date = now.date()

            if start_date <= today_date <= end_date and time == current_time:
                # Проверяем, не срабатывал ли уже сегодня
                if not app.db.is_reminder_fired_today(reminder_id, today_key):
                    self.trigger_alarm(reminder_id, pet_id, drug_id, today_key)

    def trigger_alarm(self, reminder_id, pet_id, drug_id, today_key):
        """Сработать будильник: звук + уведомление + отметка в БД."""
        app = App.get_running_app()
        pet = app.db.get_pet_by_id(pet_id)
        drug = app.db.get_drug_by_id(drug_id)
        pet_name = pet[1] if pet else "Питомец"
        drug_name = drug[1] if drug else "Препарат"

        # Звуковой сигнал
        if sys.platform == "win32":
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            print("\a")

        # Уведомление
        app.show_toast(f"⏰ Пора давать {drug_name} для {pet_name}!")

        # Отмечаем, что сработало сегодня
        app.db.mark_reminder_fired(reminder_id, today_key)

    # ═══════════════════════════════════════════════════════
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════

    def get_reminders_for_date(self, date_key):
        """Получить напоминания на указанную дату."""
        app = App.get_running_app()
        reminders = app.db.get_active_reminders()
        result = []
        date = datetime.strptime(date_key, "%Y-%m-%d").date()
        for r in reminders:
            reminder_id, pet_id, drug_id, start, end, time = r
            start_date = datetime.strptime(start, "%d.%m.%Y").date()
            end_date = datetime.strptime(end, "%d.%m.%Y").date()
            if start_date <= date <= end_date:
                result.append(r)
        return result
