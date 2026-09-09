"""
Калькулятор дозировок — RubikonApp
Спринт 2, пункт №7 (был заглушкой).

Формула:
    объём (мл) = вес (кг) × доза (мг/кг) ÷ концентрация (мг/мл)

Экран самодостаточный: не использует БД и не требует правок в main.py —
имя класса CalculatorScreen совпадает с прежней заглушкой, поэтому
регистрация экрана в ScreenManager и пункт нижнего меню продолжат работать.

Как это устроено (кратко):
    1. Пользователь заполняет три поля: вес, дозировка, концентрация.
    2. calculate() читает поля по id из KV, валидирует и считает.
    3. Результат пишется в свойства result_mg / result_ml,
       KV подхватывает их автоматически (KV-привязка к свойству).
    4. Ошибки показываются текстом в экране, без всплывающих окон.
"""

from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen


class CalculatorScreen(Screen):
    # ---- свойства, к которым привязан KV (результат и ошибка) ----
    result_mg = StringProperty("—")    # сколько мг действующего вещества
    result_ml = StringProperty("—")    # сколько мл препарата набирать в шприц
    error_text = StringProperty("")    # текст ошибки (пусто = ошибки нет)

    # ------------------------------------------------------------------
    # Основной расчёт
    # ------------------------------------------------------------------
    def calculate(self, *args):
        """Читает три поля, проверяет их и считает дозу в мг и объём в мл."""
        # 1. Читаем поля. Запятую меняем на точку: пользователи часто
        #    вводят "12,5" — float() такую строку не примет.
        weight_raw = self.ids.weight_field.text.strip().replace(",", ".")
        dose_raw = self.ids.dose_field.text.strip().replace(",", ".")
        conc_raw = self.ids.conc_field.text.strip().replace(",", ".")

        # 2. Все ли поля заполнены?
        if not weight_raw or not dose_raw or not conc_raw:
            self._fail("Заполните все три поля.")
            return

        # 3. А числа ли это вообще?
        try:
            weight = float(weight_raw)
            dose = float(dose_raw)
            conc = float(conc_raw)
        except ValueError:
            self._fail("В полях должны быть числа. Пример: 12.5 или 12,5")
            return

        # 4. Имеют ли числа физический смысл?
        if weight <= 0:
            self._fail("Вес должен быть больше нуля.")
            return
        if dose <= 0:
            self._fail("Дозировка (мг/кг) должна быть больше нуля.")
            return
        if conc <= 0:
            self._fail("Концентрация (мг/мл) должна быть больше нуля — на ноль делить нельзя.")
            return

        # 5. Сам расчёт.
        total_mg = weight * dose      # мг действующего вещества на животное
        volume_ml = total_mg / conc   # мл готового препарата в шприц

        self.result_mg = self._fmt(total_mg) + " мг"
        self.result_ml = self._fmt(volume_ml) + " мл"
        self.error_text = ""

    # ------------------------------------------------------------------
    # Сброс
    # ------------------------------------------------------------------
    def reset(self, *args):
        """Очищает поля и результат."""
        for field_id in ("weight_field", "dose_field", "conc_field"):
            self.ids[field_id].text = ""
        self.result_mg = "—"
        self.result_ml = "—"
        self.error_text = ""

    # ------------------------------------------------------------------
    # Служебные методы
    # ------------------------------------------------------------------
    def _fail(self, message):
        """Показывает ошибку и прячет прежний результат."""
        self.error_text = message
        self.result_mg = "—"
        self.result_ml = "—"

    @staticmethod
    def _fmt(value):
        """
        Красивое число для вывода.
        До 1 мл показываем 3 знака (мелкие объёмы нельзя грубо округлять),
        выше — 2 знака. Лишние нули убираем: 2.50 -> "2.5", 100.00 -> "100".
        """
        if value < 1:
            text = f"{value:.3f}"
        else:
            text = f"{value:.2f}"
        text = text.rstrip("0").rstrip(".")
        return text if text else "0"
