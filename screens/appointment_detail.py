"""
Экран «Детали назначения» — Спринт 2.6 (новый)

Заменяет MDDialog из спринта 2.5. Почему экран, а не диалог:
  1. MDDialog рождается с нулевой высотой контейнера и на части
     видеокарт падает с «FBO Initialization failed (36054)» —
     той же миной, что и MDSnackbar. Экран таких трюков не требует.
  2. У экрана есть место: каждая деталь — пара «подпись → значение»,
     всё по центру, с переносом строк и воздухом между блоками.

Экран ничего не знает о базе данных: ему передают готовый заголовок,
подзаголовок и список пар (подпись, значение). Так экран остаётся
простым рендерером, а всю логику расчётов держит pet_detail.
"""

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

GREY_TEXT = (0.5, 0.5, 0.5, 1)      # подписи полей
DARK_TEXT = (0.13, 0.13, 0.13, 1)   # значения полей


class AppointmentDetailScreen(MDScreen):

    def show_detail(self, title, subtitle, fields):
        """Заполнить экран данными.

        fields — список пар (подпись, значение). Пустые значения
        пропускаем, чтобы в карточке не было «дырок».
        """
        self.ids.detail_title.text = title or ""
        self.ids.detail_subtitle.text = subtitle or ""

        box = self.ids.fields_box
        box.clear_widgets()
        for label_text, value_text in fields:
            if value_text is None or str(value_text).strip() == "":
                continue
            box.add_widget(self._make_field(str(label_text), str(value_text)))

    @staticmethod
    def _wrap_label(text, **kwargs):
        """
        MDLabel по центру с переносом по словам.

        Урок из pet_detail: halign работает только вместе с
        text_size, а adaptive_height подтягивает высоту метки
        к высоте текста. Привязываем text_size к ширине метки.
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

    def _make_field(self, label_text, value_text):
        """Пара «подпись → значение» с воздухом вокруг."""
        row = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(2),
        )
        row.add_widget(self._wrap_label(
            label_text.upper(),
            font_size="11sp",
            theme_text_color="Custom",
            text_color=GREY_TEXT,
        ))
        row.add_widget(self._wrap_label(
            value_text,
            font_size="15sp",
            theme_text_color="Custom",
            text_color=DARK_TEXT,
        ))
        return row

    def go_back(self):
        self.manager.current = "pet_detail"
