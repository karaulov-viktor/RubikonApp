# -*- coding: utf-8 -*-
"""Калькулятор дозировок v2 — RubikonApp.

ЧТО ИЗМЕНИЛОСЬ (редизайн под разные лекарственные формы):
Прежде экран умел один расчёт: объём инъекции
(вес × доза ÷ концентрация) с тремя ручными полями. Теперь препарат
выбирается из базы (61 наименование), и способ расчёта подстраивается
под лекарственную форму по колонке dose_unit (models/database.py):

    dose_unit        форма                  что получаем
    ---------------------------------------------------------------
    mg_kg + конц.    раствор/суспензия      мг ДВ + объём в шприц:
                                            мл = вес × доза ÷ конц.
    mg_kg + таб.мг   таблетки               число таблеток:
                                            таб = вес × доза ÷ таб.мг
    ml_kg            готовый препарат       мл = вес × доза (мл/кг)
    tab_kg           «1 табл. на N кг»      таб = вес × доза (таб/кг)
    per_animal       доза на животное       мл = доза (вес не нужен)
    none             наружный/дезинфекция   расчёт не требуется

Пункт «Ручной расчёт (без препарата)» (и препараты без дозовых данных
в базе) работают как прежде: три поля — вес, доза мг/кг, концентрация.

Совместимость (как и раньше): экран самодостаточный, класс называется
CalculatorScreen — регистрация экрана и пункт нижнего меню в main.py
продолжают работать. Старые id weight_field/dose_field/conc_field
сохранены. Добавлено: main.open_calculator_for_drug() предвыбирает
препарат при переходе из карточки (кнопка «Рассчитать дозу»).

Уроки проекта учтены:
  - MDDropdownMenu ровно как в screens/calendar.py (caller, items —
    словари, functools.partial, ширина задана явно, field.focus=False
    после открытия);
  - KivyMD 2.0.0: MDButton/MDButtonText, тексты полей — только
    вложенные классы (MDTextFieldHintText и т.д.);
  - результат и ошибки — StringProperty, KV привязывается сам;
  - «12,5» меняем на точку перед float();
  - вертикальный BoxLayout: children[0] — добавленный ПОСЛЕДНИМ.
"""
from functools import partial

from kivy.app import App
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.menu import MDDropdownMenu

# осмысленные значения dose_unit (колонка drugs; см. models/database.py)
KNOWN_UNITS = ("mg_kg", "ml_kg", "tab_kg", "per_animal", "none")

# подпись дозировки в карточке препарата
UNIT_LABELS = {
    "mg_kg": "мг/кг",
    "ml_kg": "мл/кг",
    "tab_kg": "таб/кг",
}


class CalculatorScreen(Screen):
    # ---- свойства, к которым привязан KV ----
    # формула-подсказка сверху (меняется вместе с формой препарата)
    formula_text = StringProperty(
        "Объём, мл = Вес, кг × Доза, мг/кг ÷ Концентрация, мг/мл")
    # подпись поля дозировки (мг/кг -> мл/кг -> таб/кг ...)
    dose_hint = StringProperty("Дозировка препарата, мг/кг")
    # показ полей ручного ввода (скрываются, если форме они не нужны)
    dose_field_visible = BooleanProperty(True)
    conc_field_visible = BooleanProperty(True)
    tab_field_visible = BooleanProperty(False)
    # строка-описание выбранного препарата и курс
    drug_info_text = StringProperty("")
    course_text = StringProperty("")
    # результат: две строки A/B + совет под ними
    result_a_title = StringProperty("Нужно действующего вещества")
    result_a_value = StringProperty("—")
    result_b_title = StringProperty("Объём препарата в шприц")
    result_b_value = StringProperty("—")
    result_b_visible = BooleanProperty(True)
    hint_text = StringProperty("")
    error_text = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self._menu = None
        self._drugs = []          # нормализованные строки из базы
        self._loaded = False
        self.selected_drug = None  # dict препарата или None (ручной)
        self._pending_id = None    # предвыбор из карточки препарата

    # ==================================================================
    # Жизненный цикл экрана
    # ==================================================================
    def on_enter(self, *args):
        """Ленивая загрузка базы препаратов + предвыбор из карточки."""
        self._ensure_loaded()
        if self._pending_id is not None:
            drug_id, self._pending_id = self._pending_id, None
            for d in self._drugs:
                if d["id"] == drug_id:
                    self._apply_drug(d)
                    break

    def preselect_drug(self, drug_id):
        """Точка входа для app.open_calculator_for_drug(): препарат
        будет выбран при следующем показе экрана (on_enter)."""
        self._pending_id = drug_id

    def _ensure_loaded(self):
        """Один раз читает базу. Если метода нет (старый database.py)
        или база недоступна — остаётся только ручной ввод."""
        if self._loaded:
            return
        rows = []
        try:
            app = App.get_running_app()
            rows = app.db.get_all_drugs_dosing()
        except Exception as e:  # AttributeError/sqlite — не роняем экран
            print(f"[calculator] дозовая база недоступна ({e}) — "
                  f"доступен только ручной расчёт")
        self._drugs = [self._normalize(r) for r in rows]
        self._loaded = True
        # маркер сборки экрана: если строки нет в логе — на диске
        # старый calculator.py
        print(f"[calculator] v2.1 — расчёт по формам, препаратов: "
              f"{len(self._drugs)}")

    @staticmethod
    def _normalize(row):
        """Приводит строку базы к устойчивому словарю (NULL -> 0/'')."""
        return {
            "id": row.get("id"),
            "name": str(row.get("name") or ""),
            "dose_per_kg": float(row.get("dose_per_kg") or 0),
            "concentration": float(row.get("concentration") or 0),
            "dose_unit": str(row.get("dose_unit") or "").strip(),
            "tab_mg": float(row.get("tab_mg") or 0),
            "form": str(row.get("form") or "").strip(),
            "duration_days": int(row.get("duration_days") or 0),
        }

    # ==================================================================
    # Выбор препарата (меню — как в calendar.py)
    # ==================================================================
    def open_drug_menu(self):
        """Выпадающий список препаратов (readonly-поле -> on_focus)."""
        self._ensure_loaded()
        self._close_menu()
        items = [{
            "text": "Ручной расчёт (без препарата)",
            "on_release": partial(self._pick, None),
        }]
        for d in self._drugs:
            items.append({
                "text": d["name"],
                "trailing_text": self._menu_tail(d),
                "on_release": partial(self._pick, d),
            })
        self._menu = MDDropdownMenu(
            caller=self.ids.drug_field,
            items=items,
            width=dp(328),
            max_height=dp(340),
        )
        self._menu.open()
        self.ids.drug_field.focus = False

    def _close_menu(self):
        if self._menu:
            self._menu.dismiss()
        self._menu = None

    def _pick(self, drug, *args):
        """Выбор пункта меню: drug=None — ручной расчёт."""
        self._close_menu()
        if drug is None:
            self._clear_drug()
        else:
            self._apply_drug(drug)

    # ==================================================================
    # Применение выбранного препарата
    # ==================================================================
    def _apply_drug(self, d):
        """Подставляет препарат: поля-параметры (их можно править),
        описания, формулу и видимость полей под его форму."""
        self.selected_drug = d
        self.ids.drug_field.text = d["name"]
        unit = self._unit_of(d)

        dose = d["dose_per_kg"]
        self.ids.dose_field.text = self._fmt(dose) if dose > 0 else ""
        self.ids.conc_field.text = (
            self._fmt(d["concentration"])
            if unit == "mg_kg" and d["concentration"] > 0 else "")
        self.ids.tab_field.text = (
            self._fmt(d["tab_mg"])
            if unit == "mg_kg" and d["tab_mg"] > 0 else "")
        self._set_mode(unit, d)

    def _clear_drug(self):
        """Возврат к ручному расчёту (вес сохраняем)."""
        self.selected_drug = None
        self.ids.drug_field.text = ""
        self.ids.dose_field.text = ""
        self.ids.conc_field.text = ""
        self.ids.tab_field.text = ""
        self._set_mode("manual")

    def _unit_of(self, d):
        """Режим расчёта препарата. Старая база без dose_unit трактуется
        по-старому: доза = мг/кг + концентрация."""
        unit = d["dose_unit"]
        if unit in KNOWN_UNITS:
            return unit
        if d["concentration"] > 0 or d["dose_per_kg"] > 0:
            return "mg_kg"
        return "none"

    def _set_mode(self, unit, d=None):
        """Настраивает UI под режим: формулу, подписи, видимость полей."""
        vis_dose, vis_conc, vis_tab = True, False, False
        tab = bool(d and d["tab_mg"] > 0)
        conc = bool(d and d["concentration"] > 0)

        if unit == "manual":
            vis_conc = True
            self.formula_text = ("Объём, мл = Вес, кг × Доза, мг/кг ÷ "
                                 "Концентрация, мг/мл")
            self.dose_hint = "Дозировка препарата, мг/кг"
        elif unit == "mg_kg":
            vis_conc = not tab
            vis_tab = tab or not (tab or conc)
            if tab:
                self.formula_text = ("Таблеток = Вес, кг × Доза, мг/кг ÷ "
                                     "Таблетка, мг")
            else:
                self.formula_text = ("Объём, мл = Вес, кг × Доза, мг/кг ÷ "
                                     "Концентрация, мг/мл")
            self.dose_hint = "Дозировка препарата, мг/кг"
        elif unit == "ml_kg":
            self.formula_text = "Объём, мл = Вес, кг × Доза, мл/кг"
            self.dose_hint = "Дозировка препарата, мл/кг"
        elif unit == "tab_kg":
            self.formula_text = "Таблеток = Вес, кг × Таблеток на кг"
            self.dose_hint = "Таблеток на кг веса"
        elif unit == "per_animal":
            self.formula_text = "Объём, мл = доза на животное (вес не нужен)"
            self.dose_hint = "Доза на животное, мл"
        else:  # none — наружный/дезинфекция
            vis_dose = False
            self.formula_text = ("Расчёт системной дозы не требуется — "
                                 "препарат не для приёма внутрь/инъекций")
            self.dose_hint = ""

        self.dose_field_visible = vis_dose
        self.conc_field_visible = vis_conc
        self.tab_field_visible = vis_tab
        self.drug_info_text = self._make_info(d, unit) if d else ""
        self.course_text = self._make_course(d) if d else ""

    def _make_info(self, d, unit):
        """Строка «раствор · доза 2 мг/кг · концентрация 20 мг/мл»."""
        parts = []
        if d["form"]:
            parts.append(d["form"])
        label = UNIT_LABELS.get(unit)
        if unit == "per_animal" and d["dose_per_kg"] > 0:
            parts.append(f"доза {self._fmt(d['dose_per_kg'])} мл "
                         f"на животное")
        elif label and d["dose_per_kg"] > 0:
            parts.append(f"доза {self._fmt(d['dose_per_kg'])} {label}")
        elif unit == "none":
            parts.append("наружное применение / дезинфекция")
        if unit == "mg_kg" and d["tab_mg"] > 0:
            parts.append(f"в таблетке {self._fmt(d['tab_mg'])} мг")
        elif unit == "mg_kg" and d["concentration"] > 0:
            parts.append(f"концентрация "
                         f"{self._fmt(d['concentration'])} мг/мл")
        return " · ".join(parts)

    def _make_course(self, d):
        """«Однократно» / «Курс: N дн» / «»."""
        days = d["duration_days"]
        if days <= 0:
            return ""
        if days == 1:
            return "Однократно"
        return f"Курс: {days} дн"

    def _menu_tail(self, d):
        """Короткая пометка справа в меню: форма и содержание."""
        unit = self._unit_of(d)
        if unit == "none":
            return "наружный"
        if unit == "per_animal":
            return "на животное"
        if unit == "tab_kg":
            return "таблетки"
        if unit == "ml_kg":
            return d["form"] or "мл/кг"
        # mg_kg
        if d["tab_mg"] > 0:
            return f"таблетки {self._fmt(d['tab_mg'])} мг"
        if d["concentration"] > 0:
            return (f"{d['form'] or 'раствор'} "
                    f"{self._fmt(d['concentration'])} мг/мл")
        return d["form"] or ""

    # ==================================================================
    # Основной расчёт
    # ==================================================================
    def calculate(self, *args):
        """Считает результат по режиму выбранного препарата."""
        self.error_text = ""
        self.hint_text = ""

        d = self.selected_drug
        unit = self._unit_of(d) if d else "manual"

        try:
            if unit == "none":
                return self._fail(
                    "Препарат наружный / для дезинфекции — системной дозы "
                    "нет. Руководствуйтесь инструкцией к препарату.")

            weight = None
            if unit != "per_animal":
                weight = self._num(
                    "weight_field", "Введите вес животного, кг.")
                if weight <= 0:
                    return self._fail("Вес должен быть больше нуля.")

            dose = self._num(
                "dose_field",
                "Заполните дозировку препарата (или выберите препарат "
                "из списка).")
            if dose <= 0:
                return self._fail("Дозировка должна быть больше нуля.")

            if unit in ("manual", "mg_kg"):
                tab = self._num("tab_field") or 0
                conc = self._num("conc_field") or 0
                if tab > 0:
                    mg = weight * dose
                    tabs = mg / tab
                    self._show(
                        "Количество таблеток", f"{self._fmt(tabs)} табл.",
                        "Нужно действующего вещества", f"{self._fmt(mg)} мг",
                        hint=self._tablet_hint(tabs))
                elif conc > 0:
                    mg = weight * dose
                    ml = mg / conc
                    self._show(
                        "Нужно действующего вещества", f"{self._fmt(mg)} мг",
                        "Объём препарата в шприц", f"{self._fmt(ml)} мл")
                else:
                    return self._fail(
                        "Нет данных для расчёта: заполните концентрацию "
                        "(мг/мл) или содержание таблетки (мг).")

            elif unit == "ml_kg":
                ml = weight * dose
                self._show("Объём препарата в шприц", f"{self._fmt(ml)} мл")

            elif unit == "tab_kg":
                tabs = weight * dose
                self._show(
                    "Количество таблеток", f"{self._fmt(tabs)} табл.",
                    hint=self._tablet_hint(tabs))

            elif unit == "per_animal":
                self._show("Объём на одно животное",
                           f"{self._fmt(dose)} мл")

        except ValueError as e:
            return self._fail(str(e))

    # ==================================================================
    # Сброс
    # ==================================================================
    def reset(self, *args):
        """Очищает препарат, поля и результат."""
        self._close_menu()
        self.selected_drug = None
        for field_id in ("drug_field", "weight_field",
                         "dose_field", "conc_field", "tab_field"):
            self.ids[field_id].text = ""
        self._set_mode("manual")
        self.result_a_title = "Нужно действующего вещества"
        self.result_a_value = "—"
        self.result_b_title = "Объём препарата в шприц"
        self.result_b_value = "—"
        self.result_b_visible = True
        self.hint_text = ""
        self.error_text = ""

    # ==================================================================
    # Служебные методы
    # ==================================================================
    def _num(self, field_id, required_msg=None):
        """Число из поля (запятая -> точка). None — пусто; ValueError —
        не число/обязательное поле пустое."""
        raw = self.ids[field_id].text.strip().replace(",", ".")
        if not raw:
            if required_msg:
                raise ValueError(required_msg)
            return None
        try:
            return float(raw)
        except ValueError:
            raise ValueError(
                f"«{raw}» — не число. Пример: 12.5 или 12,5")

    @staticmethod
    def _tablet_hint(tabs):
        """Совет по округлению таблеток до целой/половины."""
        half = round(tabs * 2) / 2
        if abs(tabs - half) < 1e-9:
            return ""
        return (f"Практически: {CalculatorScreen._fmt(half)} табл. "
                f"Делить таблетку можно только если это разрешено "
                f"инструкцией.")

    def _show(self, a_title, a_value, b_title=None, b_value=None,
              hint=""):
        """Пишет результат (строка B опциональна)."""
        self.result_a_title = a_title
        self.result_a_value = a_value
        if b_title is None:
            self.result_b_title = ""
            self.result_b_value = "—"
            self.result_b_visible = False
        else:
            self.result_b_title = b_title
            self.result_b_value = b_value
            self.result_b_visible = True
        self.hint_text = hint
        self.error_text = ""

    def _fail(self, message):
        """Показывает ошибку и прячет прежний результат."""
        self.error_text = message
        self.result_a_value = "—"
        self.result_b_value = "—"

    @staticmethod
    def _fmt(value):
        """Красивое число: до 1 — 3 знака, выше — 2; нули убираем
        (2.50 -> "2.5", 100.00 -> "100")."""
        if value < 1:
            text = f"{value:.3f}"
        else:
            text = f"{value:.2f}"
        text = text.rstrip("0").rstrip(".")
        return text if text else "0"
