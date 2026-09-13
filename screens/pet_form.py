# -*- coding: utf-8 -*-
"""Анкета питомца: добавление и редактирование.

Ключевое изменение против старого проекта: вместо поля «возраст» —
ДАТА РОЖДЕНИЯ (3 спиннера: день / месяц / год). Возраст вычисляется
на лету (models/age_utils), день рождения триггерит уведомление.

Мод:  start_add()  — новый питомец
      start_edit(pet_id) — правка существующего
"""
import calendar as _cal
import datetime as _dt

from kivymd.uix.screen import MDScreen

from models import database as db
from models import image_utils
from screens import AppMixin

SPECIES = ["Кошка", "Собака", "Птица", "КРС", "Свинья", "МРС", "Лошадь"]


class PetFormScreen(AppMixin, MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "add"
        self.pet_id = None
        self._picked_src = None  # абсолютный путь выбранного фото

    # ---------------------------------------------------------- открытие
    def start_add(self):
        self.mode = "add"
        self.pet_id = None
        self._picked_src = None
        self.ids.f_name.text = ""
        self.ids.f_breed.text = ""
        self._fill_date_spinners(None)
        self._reset_photo_preview()
        self.ids.btn_save.text = "Сохранить"
        self.ids.form_title.text = "Новый питомец"

    def start_edit(self, pet_id: int):
        pet = db.get_pet(pet_id)
        if not pet:
            return
        self.mode = "edit"
        self.pet_id = pet_id
        self._picked_src = None
        self.ids.f_name.text = pet["name"]
        self.ids.f_breed.text = pet["breed"] or ""
        birth = pet["birth_date"] or ""
        if birth:
            try:
                d = _dt.datetime.strptime(birth, "%Y-%m-%d").date()
            except ValueError:
                d = None
        else:
            d = None
        self._fill_date_spinners(d)
        self.ids.f_species.text = pet.get("species") or SPECIES[0]
        self._reset_photo_preview()
        self.ids.btn_save.text = "Сохранить изменения"
        self.ids.form_title.text = "Редактирование"

    def _fill_date_spinners(self, d):
        today = _dt.date.today()
        d = d or today
        years = list(range(2000, today.year + 1))[::-1]
        self.ids.sp_day.values = [str(i) for i in range(1, 32)]
        self.ids.sp_month.values = [str(i) for i in range(1, 13)]
        self.ids.sp_year.values = [str(y) for y in years]
        self.ids.sp_day.text = str(d.day)
        self.ids.sp_month.text = str(d.month)
        self.ids.sp_year.text = str(d.year)

    def _reset_photo_preview(self):
        self._picked_src = None
        self.ids.photo_hint.text = "Фото не выбрано"

    # ---------------------------------------------------------- действия
    def choose_photo(self):
        src = image_utils.pick_media_src("photo")
        if src:
            self._picked_src = src
            self.ids.photo_hint.text = (
                "Фото выбрано: " + src.replace("\\", "/").split("/")[-1]
            )

    def save(self):
        name = self.ids.f_name.text.strip()
        if not name:
            self.app.show_toast("Введите кличку питомца")
            return

        birth = self._collect_birth_date()  # '' если год не выбран
        if birth == "INVALID":
            return  # тост уже показан

        species = self.ids.f_species.text or SPECIES[0]
        breed = self.ids.f_breed.text.strip()

        if self.mode == "add":
            pet_id = db.add_pet(name, species, breed, birth)
            photo_rel = self._copy_photo(pet_id)
            if photo_rel:
                db.update_pet(pet_id, name, species, breed, birth, photo_rel)
            self.app.show_toast(f"{name} добавлен")
        else:
            photo_rel = self._copy_photo(self.pet_id)
            db.update_pet(
                self.pet_id, name, species, breed, birth,
                photo_rel if photo_rel else None,  # None = фото не менять
            )
            self.app.show_toast("Изменения сохранены")

        self.app.go_to("profile")

    def _copy_photo(self, pet_id: int) -> str | None:
        if not self._picked_src:
            return None
        rel = image_utils.copy_media_to(self._picked_src, pet_id)
        if rel is None:
            self.app.show_toast("Не удалось скопировать фото")
        return rel

    def _collect_birth_date(self) -> str:
        """Собирает YYYY-MM-DD из трёх спиннеров.

        ''  — дата не указана (год пуст)
        'INVALID' — дата не существует (31.02) или в будущем
        """
        year_s = self.ids.sp_year.text.strip()
        if not year_s:
            return ""
        try:
            day = int(self.ids.sp_day.text)
            month = int(self.ids.sp_month.text)
            year = int(year_s)
            d = _dt.date(year, month, day)  # ValueError для 31.02
        except ValueError:
            self.app.show_toast("Такой даты не существует")
            return "INVALID"
        if d > _dt.date.today():
            self.app.show_toast("Дата рождения не может быть в будущем")
            return "INVALID"
        return d.strftime("%Y-%m-%d")

    def cancel(self):
        self.app.go_to("profile")

    # утилита для будущих правок вёрстки: максимум дней в месяце
    @staticmethod
    def _max_day(year: int, month: int) -> int:
        return _cal.monthrange(year, month)[1]
