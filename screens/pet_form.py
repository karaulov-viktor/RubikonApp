import os
import shutil
from datetime import datetime
from functools import partial
from tkinter import Tk, filedialog

from kivy.app import App
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
        self.photo_path = ""  # относительный путь выбранного фото
        self.species = ""     # выбранное значение; поле — только витрина
        self.breed = ""
        self.pet_size = ""    # НЕ size! имя size занято самим Kivy (ширина+высота)

    # ---------- выпадающие списки ----------

    def _close_menu(self):
        """Закрыть меню, если оно открыто."""
        menu = getattr(self, "_menu", None)
        if menu is not None:
            menu.dismiss()
        self._menu = None

    def _open_menu(self, caller, values, on_pick):
        """Собрать меню из справочника и показать у поля."""
        self._close_menu()
        menu_items = [
            {"text": value, "on_release": partial(on_pick, value)}
            for value in values
        ]
        self._menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            width=dp(280),    # иначе ширина соберётся по самому длинному пункту
            position="auto",  # меню само решает: раскрыться вверх или вниз
        )
        self._menu.open()
        caller.focus = False  # снимаем фокус — следующий клик снова даст on_focus

    def open_species_menu(self, field, focused):
        if not focused:
            return  # реагируем только на взятие фокуса, не на снятие
        self._open_menu(field, SPECIES, self.select_species)

    def select_species(self, species):
        self._close_menu()
        self.species = species
        self.ids.field_species.text = species
        self.breed = ""  # вид сменился — старая порода больше не честна
        self.ids.field_breed.text = ""

    def open_breed_menu(self, field, focused):
        if not focused:
            return
        breeds = BREEDS.get(self.species, [])
        if not breeds:
            return  # вид ещё не выбран — показывать нечего
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
        """Диалог выбора файла + копия в media/pets/."""
        root = Tk()
        root.withdraw()  # tkinter хочет своё окно — прячем, оставляем только диалог
        path = filedialog.askopenfilename(
            title="Фото питомца",
            filetypes=[("Картинки", "*.png *.jpg *.jpeg *.bmp *.webp")],
        )
        root.destroy()
        if not path:
            return  # человек передумал — ничего не делаем
        self.photo_path = self._make_copy(path)
        self.ids.label_photo.text = os.path.basename(self.photo_path)

    def _make_copy(self, src):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")  # noqa: DTZ005
        ext = os.path.splitext(src)[1].lower()  # ".jpg", ".png"
        os.makedirs(os.path.join(BASE_DIR, "media", "pets"), exist_ok=True)
        rel_path = os.path.join("media", "pets", f"pet-{stamp}{ext}")
        shutil.copyfile(src, os.path.join(BASE_DIR, rel_path))
        return rel_path

    # ---------- сохранение ----------

    def save_pet(self):
        name = self.ids.field_name.text
        age = self.ids.field_age.text
        weight = self.ids.field_weight.text
        history = self.ids.field_history.text

        db = App.get_running_app().db  # одна база на всё приложение
        db.add_pet(
            name, self.species, self.breed, self.pet_size,
            age, weight, history, self.photo_path,
        )
        print("Сохранил!")

        for field_id in (
            "field_name",
            "field_species",
            "field_breed",
            "field_size",
            "field_age",
            "field_weight",
            "field_history",
        ):
            self.ids[field_id].text = ""
        self.species = self.breed = self.pet_size = ""
        self.photo_path = ""  # не тащить фото в следующего питомца
        self.ids.label_photo.text = "Фото не выбрано"
        self.manager.current = "profile"