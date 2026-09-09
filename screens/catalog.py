from kivy.metrics import dp
from kivy.uix.image import Image
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen


class DrugCard(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(width=self._update_height)

    def _update_height(self, instance, width):
        self.height = max(width * 1.5, dp(180))  # Минимум 180dp


class CatalogScreen(MDScreen):
    def on_enter(self):
        app = MDApp.get_running_app()
        if hasattr(app, "db") and app.db:
            self.load_drugs()

    def load_drugs(self):
        app = MDApp.get_running_app()
        drugs = app.db.get_all_drugs()
        self.update_grid(drugs)

    def update_grid(self, drugs):
        grid = self.ids.drug_grid
        grid.clear_widgets()
        for drug in drugs:
            drug_id, name, category, _description, _instruction, image, _icon = drug
            card = self._create_card(drug_id, name, category, image)
            grid.add_widget(card)

    def _create_card(self, drug_id, name, category, image_path):
        card = DrugCard(
            orientation="vertical",
            size_hint_y=None,
            height="220dp",
            padding="0dp",
            spacing="0dp",
            ripple_behavior=True,
        )
        card.bind(on_release=lambda x, did=drug_id: self.open_drug_detail(did))

        photo_container = MDBoxLayout(size_hint_y=None, height="120dp")

        def update_photo_height(instance, width):
            photo_container.height = width * 1  # Высота картинки

        card.bind(width=update_photo_height)

        img = Image(
            source=image_path,
            size_hint=(1, 1),
            fit_mode="contain",
        )
        photo_container.add_widget(img)

        text_box = MDBoxLayout(
            orientation="vertical",
            padding=["12dp", "8dp", "12dp", "8dp"],
            spacing="2dp",
            size_hint_y=None,
            adaptive_height=True,
            pos_hint={"bottom": 0.0}
        )

        title = MDLabel(
            text=name or "",
            font_style="Title",
            role="medium",
            halign="left",
            valign="top",
            size_hint_y=None,
            adaptive_height=True,
            text_size=(self.width, None),
            max_lines=2,  # <--- Ограничиваем до 2 строк
            shorten=True,  # <--- Обрезаем лишнее
            shorten_from="right",  # <--- Обрезаем справа
        )

        cat = MDLabel(
            text=category or "",
            theme_text_color="Secondary",
            halign="left",
            valign="top",
            size_hint_y=None,
            adaptive_height=True,
            text_size=(self.width, None),
            font_style="Body",
            role="small",
            max_lines=1,  # <--- Ограничиваем до 1 строки
            shorten=True,
            shorten_from="right",
        )

        text_box.add_widget(title)
        text_box.add_widget(cat)
        card.add_widget(photo_container)
        card.add_widget(text_box)
        return card

    def open_drug_detail(self, drug_id):
        app = MDApp.get_running_app()
        app.open_drug_detail(drug_id)

    def on_search(self, query):
        app = MDApp.get_running_app()
        if not hasattr(app, "db") or not app.db:
            return
        if query.strip():
            drugs = app.db.search_drugs(query)
        else:
            drugs = app.db.get_all_drugs()
        self.update_grid(drugs)
