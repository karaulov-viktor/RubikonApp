"""
Спринт 1.5 — Анкета питомца с историей назначений
"""

import os
import shutil
from datetime import datetime
from functools import partial
from tkinter import Tk, filedialog

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SPECIES = ["Собака", "Кошка", "Птица"]
BREEDS = {
    "Собака": ["Дворняга", "Лабрадор", "Немецкая овчарка", "Пудель", "Хаски"],
    "Кошка": ["Британская", "Мейн-кун", "Сиамская", "Сфинкс", "Дворовая"],
    "Птица": ["Волнистый попугай", "Канарейка", "Корелла"],
}
SIZES = ["Мелкий", "Средний", "Крупный"]


class PetFormScreen(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.photo_path = ""
        self.species = ""
        self.breed = ""
        self.pet_size = ""
        self.editing_pet_id = None

    # ---------- выпадающие списки ----------

    def _close_menu(self):
        menu = getattr(self, "_menu", None)
        if menu is not None:
            menu.dismiss()
        self._menu = None

    def _open_menu(self, caller, values, on_pick):
        self._close_menu()
        menu_items = [
            {"text": value, "on_release": partial(on_pick, value)}
            for value in values
        ]
        self._menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            width=dp(280),
            position="auto",
        )
        self._menu.open()
        caller.focus = False

    def open_species_menu(self, field, focused):
        if not focused:
            return
        self._open_menu(field, SPECIES, self.select_species)

    def select_species(self, species):
        self._close_menu()
        self.species = species
        self.ids.field_species.text = species
        self.breed = ""
        self.ids.field_breed.text = ""

    def open_breed_menu(self, field, focused):
        if not focused:
            return
        breeds = BREEDS.get(self.species, [])
        if not breeds:
            return
        self._open_menu(field, breeds, self.select_breed)

    def select_breed(self, breed):
        self._close_menu()
        self.breed = breed
        self.ids.field_breed.text = breed

    def open_size_menu(self, field, focused):
        if not focused:
            return
        self._open_menu(field, SIZES, self.select_size)

    def select_size(self, size):
        self._close_menu()
        self.pet_size = size
        self.ids.field_size.text = size

    # ---------- фото ----------

    def choose_photo(self):
        root = Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="Фото питомца",
            filetypes=[("Картинки", "*.png *.jpg *.jpeg *.bmp *.webp")],
        )
        root.destroy()
        if not path:
            return
        self.photo_path = self._make_copy(path)
        self.ids.label_photo.text = os.path.basename(self.photo_path)

    def _make_copy(self, src):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        ext = os.path.splitext(src)[1].lower()
        os.makedirs(os.path.join(BASE_DIR, "media", "pets"), exist_ok=True)
        rel_path = os.path.join("media", "pets", f"pet-{stamp}{ext}")
        shutil.copyfile(src, os.path.join(BASE_DIR, rel_path))
        return rel_path

    # ---------- загрузка данных для редактирования ----------

    def load_pet_data(self, pet):
        """Заполнить форму данными питомца для редактирования."""
        pet_id, name, species, breed, size, age, weight, history, photo = pet
        self.editing_pet_id = pet_id
        self.ids.field_name.text = name or ""
        self.ids.field_species.text = species or ""
        self.ids.field_breed.text = breed or ""
        self.ids.field_size.text = size or ""
        self.ids.field_age.text = str(age) if age else ""
        self.ids.field_weight.text = str(weight) if weight else ""
        self.ids.field_history.text = history or ""
        self.species = species or ""
        self.breed = breed or ""
        self.pet_size = size or ""
        self.photo_path = photo or ""
        if photo:
            self.ids.label_photo.text = os.path.basename(photo)
        else:
            self.ids.label_photo.text = "Фото не выбрано"

    # ---------- сохранение ----------

    def save_pet(self):
        name = self.ids.field_name.text
        age = self.ids.field_age.text
        weight = self.ids.field_weight.text
        history = self.ids.field_history.text

        db = App.get_running_app().db

        if self.editing_pet_id:
            db.update_pet(
                self.editing_pet_id,
                name, self.species, self.breed, self.pet_size,
                age, weight, history, self.photo_path,
            )
            message = f"Питомец «{name}» обновлён"
        else:
            db.add_pet(
                name, self.species, self.breed, self.pet_size,
                age, weight, history, self.photo_path,
            )
            message = f"Питомец «{name}» добавлен"

        print(f"Сохранено: {message}")

        # ═══ ПОЛНАЯ ОЧИСТКА ВСЕХ ПОЛЕЙ ═══
        self._reset_all_fields()

        self.manager.current = "profile"
        Clock.schedule_once(
            lambda dt: App.get_running_app().show_toast(message),
            0.3,
        )

    def _reset_all_fields(self):
        """Полная очистка всех полей формы после сохранения."""
        # Очищаем все текстовые поля
        for field_id in (
                "field_name", "field_species", "field_breed",
                "field_size", "field_age", "field_weight", "field_history",
        ):
            try:
                self.ids[field_id].text = ""
            except KeyError:
                pass  # поле может отсутствовать

        # Сбрасываем внутренние переменные
        self.species = ""
        self.breed = ""
        self.pet_size = ""
        self.photo_path = ""
        self.editing_pet_id = None

        # Сбрасываем метку фото
        try:
            self.ids.label_photo.text = "Фото не выбрано"
        except KeyError:
            pass

        print("Все поля формы очищены")

    # ---------- навигация ----------

    def go_back(self, *args):
        """Вернуться в профиль."""
        self.manager.current = "profile"