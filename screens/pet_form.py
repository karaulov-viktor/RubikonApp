from kivymd.uix.screen import MDScreen

from models.database import Database


class PetFormScreen(MDScreen):
    def save_pet(self):
        name = self.ids.field_name.text
        species = self.ids.field_species.text
        breed = self.ids.field_breed.text
        size = self.ids.field_size.text
        age = self.ids.field_age.text
        weight = self.ids.field_weight.text
        history = self.ids.field_history.text

        db = Database()
        db.add_pet(name, species, breed, size, age, weight, history)
        print("Сохранил!")

        for field_id in ("field_name", "field_species", "field_breed", "field_size", "field_age", "field_weight", "field_history"):
            self.ids[field_id].text = ""
        self.manager.current = "profile"
