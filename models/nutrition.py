# -*- coding: utf-8 -*-
"""Ветеринарные расчёты питания RubikonApp — чистый Python без Kivy.

Модуль можно тестировать в песочнице без окна и GPU.

Методика (стандарт ветеринарных калькуляторов кормления — WSAVA/
BSAVA, так же считают калькуляторы Royal Canin, Veterical и др.):

  1. RER (энергия покоя) = 70 x (вес, кг)^0.75      [ккал/сутки]
  2. MER (суточная норма) = RER x коэффициент стадии жизни
       - котёнок/щенок до 4 мес.   x2.5 / x3.0
       - молодняк 4-12 мес.        x2.0
       - кошка стерилизованная     x1.2   (нестерилизованная x1.4)
       - собака стерилизованная    x1.6   (нестерилизованная x1.8)
       - пожилые                   x1.1-1.4 (по активности)
       - снижение веса             x0.8 (кошки) / x1.0 (собаки)
  3. Граммов в сутки = ккал x 100 / калорийность корма [ккал/100 г]
  4. Кратность: до 4 мес. — 4 раза, 4-6 — 3, 6-12 — 2-3, взрослые — 2.

Диеты подбираются по профилю: вид, возраст, стерилизация и ТРЕНД веса
(по истории замеров): рост -> рацион роста; набор веса -> снижение;
пожилой кот -> поддержка почек; стерилизованным -> лёгкий рацион.
"""
import datetime as _dt

# ------------------------------------------------------------------
# Базовые определения
# ------------------------------------------------------------------
DEFAULT_FOOD_KCAL = 350        # типичная калорийность сухого корма
KITTEN_MONTHS = 12             # котята/щенки до 12 мес.
SENIOR_MONTHS = 84             # пожилые с 7 лет

ACTIVITY_LEVELS = ("низкая", "средняя", "высокая")

# Предложить время кормлений равномерно с 07:00 до 22:00
_MEAL_TIMES = {
    1: ["08:00"],
    2: ["08:00", "20:00"],
    3: ["08:00", "14:00", "20:00"],
    4: ["07:00", "12:00", "17:00", "22:00"],
}


_DOG_PREFIXES = ("соб", "пёс", "пес", "dog")


def is_cat(species: str) -> bool:
    """Вид -> кошка? Узнаём «Кошка», «Кот», «Кошка британская» и т.д.;
    собакой считаем «Собака», «Пёс», «Пес», «dog». Пусто/неизвестно ->
    кошка (их в базе большинство, и коэффициенты кошек ниже — безопаснее)."""
    s = (species or "").strip().lower()
    if not s:
        return True
    if s.startswith(_DOG_PREFIXES):
        return False
    return True


def age_months(birth_date: str, today=None):
    """Полных месяцев по дате рождения YYYY-MM-DD. None — даты нет."""
    from models.age_utils import parse_date
    birth = parse_date(birth_date)
    if birth is None:
        return None
    today = today or _dt.date.today()
    if birth > today:
        return None
    months = (today.year - birth.year) * 12 + (today.month - birth.month)
    if today.day < birth.day:
        months -= 1
    return max(months, 0)


def life_stage(species: str, birth_date: str, today=None) -> dict:
    """Стадия жизни для расчётов: key, title.

    Нет даты рождения -> считаем взрослым (и пишем об этом в title).
    """
    m = age_months(birth_date, today)
    cat = is_cat(species)
    junior = "котёнок" if cat else "щенок"
    if m is None:
        return {"key": "adult", "title": "возраст не указан"}
    if m < KITTEN_MONTHS:
        return {"key": "junior", "title": junior}
    if m < SENIOR_MONTHS:
        return {"key": "adult", "title": "взрослый" if cat else "взрослая"}
    return {"key": "senior", "title": "пожилой" if cat else "пожилая"}


def mer_factor(species: str, age_m, sterilized: bool,
               activity: str, goal: str = "normal") -> float:
    """Коэффициент MER по таблицам WSAVA (упрощённо, для домашнего питомца)."""
    cat = is_cat(species)
    act = activity if activity in ACTIVITY_LEVELS else "средняя"

    if goal == "weight_loss":
        return 0.8 if cat else 1.0

    if age_m is None:
        age_m = 24  # "взрослый по умолчанию"
    if age_m < 4:
        return 2.5 if cat else 3.0
    if age_m < KITTEN_MONTHS:
        return 2.0

    if cat:
        base = 1.2 if sterilized else 1.4
        if age_m >= SENIOR_MONTHS:
            base = min(base, 1.3)          # пожилым чуть меньше энергии
        if act == "низкая":
            base -= 0.1
        elif act == "высокая":
            base += 0.2
    else:
        base = 1.6 if sterilized else 1.8
        if age_m >= SENIOR_MONTHS:
            base -= 0.2
        if act == "низкая":
            base -= 0.2
        elif act == "высокая":
            base += 0.3
    return round(max(base, 0.8), 2)


def meals_per_day(species: str, age_m) -> int:
    """Сколько раз в день кормить."""
    if age_m is None:
        return 2
    if age_m < 4:
        return 4
    if age_m < 6:
        return 3
    if age_m < KITTEN_MONTHS:
        return 3 if is_cat(species) else 2
    return 2


def meal_times(n: int) -> list[str]:
    """Предложение времени кормлений."""
    return _MEAL_TIMES.get(n, _MEAL_TIMES[2])


# ------------------------------------------------------------------
# Главный расчёт суточной нормы
# ------------------------------------------------------------------
def calc_daily(species: str, weight_kg: float, birth_date: str,
               sterilized: bool, activity: str,
               food_kcal: float = DEFAULT_FOOD_KCAL,
               goal: str = "normal") -> dict:
    """Суточная норма: калории, граммы, кратность, время.

    Возвращает dict: rer, factor, kcal, meals, times, grams_day,
    grams_meal, water_ml, stage, lines (готовые строки для экрана).
    grams_day/grams_meal = None, если калорийность корма не задана.
    """
    weight = max(float(weight_kg or 0), 0.1)
    rer = 70.0 * (weight ** 0.75)
    stage = life_stage(species, birth_date)
    age_m = age_months(birth_date)
    factor = mer_factor(species, age_m, sterilized, activity, goal)
    kcal = int(round(rer * factor))
    meals = meals_per_day(species, age_m)
    times = meal_times(meals)

    grams_day = grams_meal = None
    try:
        fk = float(food_kcal)
        if fk > 0:
            grams_day = int(round(kcal * 100.0 / fk))
            grams_meal = int(round(grams_day / meals))
    except (TypeError, ValueError):
        pass

    water = int(round(weight * (50 if is_cat(species) else 55) / 10.0) * 10)

    lines = [
        f"Норма: ~{kcal} ккал/сутки  (RER {int(round(rer))} x {factor})",
    ]
    if grams_day is not None:
        lines.append(
            f"Это ~{grams_day} г корма в сутки при {int(food_kcal)} "
            f"ккал/100 г")
    lines.append(f"Режим: {meals} кормления по {grams_meal or '?'} г"
                 + (f"  ({times[0]} и {times[-1]})" if meals <= 2
                    else f"  ({', '.join(times)})"))
    lines.append(f"Вода: ~{water} мл/сутки")
    if goal == "weight_loss":
        lines.append("Цель снижения: −1–2% веса в неделю, "
                     "взвешивайте раз в 2 недели")

    return {
        "rer": int(round(rer)),
        "factor": factor,
        "kcal": kcal,
        "meals": meals,
        "times": times,
        "grams_day": grams_day,
        "grams_meal": grams_meal,
        "water_ml": water,
        "stage": stage,
        "lines": lines,
    }


# ------------------------------------------------------------------
# Подбор диеты по профилю питомца
# ------------------------------------------------------------------
def diet_options(species: str, weight_kg, birth_date: str,
                 sterilized: bool, weight_trend_kg=0.0) -> list[dict]:
    """Список подходящих рационов (первый — самый приоритетный).

    Каждый вариант: key, title, why, days, goal, tips.
    goal потом превращается в коэффициент MER и цель по калориям.
    """
    cat = is_cat(species)
    stage = life_stage(species, birth_date).get("key")
    age_m = age_months(birth_date)
    options = []

    # --- приоритет 1: молодняк ---
    if stage == "junior":
        options.append({
            "key": "growth",
            "title": "Рацион роста",
            "why": ("Энергия x2.0–3.0 и больше белка: идёт активный "
                    "рост. Кормите чаще (по расчёту нормы) и "
                    "контролируйте вес раз в неделю"),
            "days": 90,
            "goal": "growth",
            "tips": "Корм для котят/щенков, взвешивание раз в неделю",
        })

    # --- приоритет: набор веса по тренду ---
    try:
        trend = float(weight_trend_kg or 0)
    except (TypeError, ValueError):
        trend = 0.0
    prev = None
    if weight_kg:
        prev = float(weight_kg) - trend
    grew_pct = (trend / prev * 100.0) if (prev and prev > 0) else 0.0
    if grew_pct >= 5:
        options.append({
            "key": "weight_loss",
            "title": "Снижение веса",
            "why": (f"Вес вырос на {grew_pct:.0f}% между замерами. "
                    f"Норма с коэффициентом "
                    f"{'0.8' if cat else '1.0'} (ниже поддержки), "
                    f"цель — минус 1–2% в неделю"),
            "days": 60,
            "goal": "weight_loss",
            "tips": "Лёгкий корм, больше движения, взвешивание раз в "
                    "2 недели",
        })

    # --- стерилизованным — лёгкий рацион ---
    if sterilized and stage == "adult":
        options.append({
            "key": "light",
            "title": "Лёгкий рацион после стерилизации",
            "why": ("После стерилизации потребность в энергии падает "
                    f"до {'x1.2' if cat else 'x1.6'} — обычный корм "
                    "ведёт к набору веса. Нужен корм с пониженным "
                    "жиром"),
            "days": 30,
            "goal": "light",
            "tips": "Корм «для стерилизованных», порции по расчёту",
        })

    # --- пожилой кот: почки; пожилой пёс: суставы/ЖКТ ---
    if stage == "senior":
        if cat:
            options.append({
                "key": "senior_care",
                "title": "Поддержка почек и суставов",
                "why": ("После 7 лет у кошек растёт риск хронической "
                        "болезни почек. Нужен рацион для пожилых: "
                        "контроль фосфора, легкоусвояемый белок, "
                        "больше влаги в рационе"),
                "days": 45,
                "goal": "senior",
                "tips": "Корм 7+ / renal-линейка, анализ крови раз в год",
            })
        else:
            options.append({
                "key": "senior_care",
                "title": "Поддержка суставов и ЖКТ",
                "why": ("После 7 лет собакам нужен рацион для пожилых: "
                        "хондропротекторы, легкоусвояемый белок, "
                        "умеренная калорийность при сниженной "
                        "активности"),
                "days": 45,
                "goal": "senior",
                "tips": "Корм 7+, хондропротекторы, контроль веса "
                        "раз в 2 недели",
            })

    # --- всегда: сбалансированное поддержание ---
    options.append({
        "key": "maintenance",
        "title": "Сбалансированное поддержание",
        "why": ("Порядок в расписании и норма по весу/возрасту. "
                "Достаточно, если ветеринарных ограничений нет"),
        "days": 30,
        "goal": "normal",
        "tips": "Порции по расчёту нормы, 2 кормления в одно время",
    })

    return options[:4]


def goal_factor(goal: str) -> str:
    """Человекочитаемое пояснение коэффициента для карточки диеты."""
    return {
        "weight_loss": "снижение веса (пониженная калорийность)",
        "light": "лёгкий рацион (контроль веса)",
        "growth": "рост (повышенная калорийность)",
        "senior": "поддержка пожилого питомца",
        "normal": "поддержание формы",
    }.get(goal, goal)
