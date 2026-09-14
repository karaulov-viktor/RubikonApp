# -*- coding: utf-8 -*-
"""Личная страница питомца.

Сверху вниз:
  - аватар НА ВСЮ ШИРИНУ экрана (260dp) + кнопки назад/правка/удаление
  - карточка информации: имя / вид / порода · возраст · дата рождения
  - Лечение и назначения (старый функционал, тап -> экран)
  - Галерея фото (плитки 96dp, тап -> полноэкранный просмотр) и видео
    (карточки, тап -> просмотрщик; видео грузится ТОЛЬКО при открытии)
  - Лекарства (список + добавление) -> уведомления по времени
  - Кормление: РАСЧЁТ НОРМЫ по виду/весу/возрасту (RER/MER, WSAVA),
    расписание с порциями в граммах, ручное добавление
  - Диета: ПОДБОР рациона по профилю (возраст, стерилизация, тренд
    веса), активная диета с целью и калорийностью, ручная форма
  - Вес: список замеров + запись (Canvas-график убран по решению
    владельца — отображался некорректно, список информативнее)

Все списки строятся кодом; kv держит каркас и заголовки секций.

Уроки прошлых пакетов (учтены):
  - MDIcon в kivymd.uix.label, FitImage в kivymd.uix.fitimage (2.0);
  - self.app недоступен без AppMixin (screens/__init__.py);
  - фиксированная высота многострочных label = наложения текста
    (теперь авто-высота по texture_size);
  - юникод-стрелки ↑/↓ не рендерятся Roboto на Windows -> слова.
"""
import datetime as _dt

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.fitimage import FitImage
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.progressindicator import MDLinearProgressIndicator
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText

from models import database as db
from models import nutrition as nutr
from models import theme as T
from models.age_utils import fmt_display, format_age, parse_date
from models.image_utils import (
    copy_media_to,
    delete_media_file,
    pick_media_src,
    resolve_media,
)
from models.legal import SHORT_DISCLAIMER

from screens import AppMixin

try:
    import ffpyplayer  # noqa: F401
    HAS_FFPY = True
except Exception:
    HAS_FFPY = False

# Точная команда установки для подсказки (Windows, venv проекта)
FFPY_INSTALL_HINT = ("venv\\Scripts\\python.exe -m pip install ffpyplayer")


def _esc(s: str) -> str:
    """Квадратные скобки в пользовательском тексте ломают markup."""
    return str(s or "").replace("[", "(")


def _auto_label(text: str = "", color=None, font_size: str = "13sp",
                bold: bool = False, halign: str = "left",
                wrap_width=dp(290), wrap=None) -> MDLabel:
    """MDLabel с АВТО-высотой по фактическому размеру текста.

    Урок v2 (наложения): фиксированная высота 40dp у трёхстрочного
    текста рисует строки поверх соседних виджетов. Здесь высота
    подтягивается к texture_size после компоновки.
    """
    if wrap is not None:
        wrap_width = wrap
    lbl = MDLabel(
        text=text, markup=bold, halign=halign,
        theme_text_color="Custom", text_color=color or T.TEXT_MAIN,
        font_size=font_size, size_hint_y=None, height=dp(20),
    )
    lbl.text_size = (wrap_width, None)
    lbl.bind(texture_size=lambda inst, sz: setattr(
        inst, "height", max(dp(18), sz[1])))
    return lbl


def _field(hint: str, width_hint: float, cb=None) -> MDTextField:
    """MDTextField с подсказкой (заполненный стиль), как в kv."""
    tf = MDTextField(mode="filled", size_hint_x=width_hint)
    tf.add_widget(MDTextFieldHintText(text=hint))
    if cb is not None:
        tf.bind(text=cb)
    return tf


class PetDetailScreen(AppMixin, MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pet_id = None
        # пути медиа текущего питомца для полноэкранного просмотрщика
        self._photo_paths = []
        self._video_paths = []
        # --- состояние панели расчёта нормы ---
        self._nutr_open = False
        self._nutr_ster = False
        self._nutr_act = "средняя"
        self._nutr_weight_s = ""   # текст поля «вес»
        self._nutr_kcal_s = ""     # текст поля «ккал/100 г»
        self._nutr_result_lbl = None
        self._last_plan = None
        # --- состояние панели подбора диеты ---
        self._diet_reco_open = False
        self._pending_goal = None

    # ================================================== открытие экрана
    def open_pet(self, pet_id: int):
        self.pet_id = pet_id
        self._nutr_open = False
        self._nutr_weight_s = ""
        self._nutr_kcal_s = ""
        self._diet_reco_open = False
        self._pending_goal = None
        self._nutr_ster = self._saved_ster()
        self._nutr_act = self._saved_activity()
        self.refresh_all()
        self.app.go_to("pet_detail")

    def refresh_all(self):
        pet = db.get_pet(self.pet_id)
        if not pet:
            self.app.go_to("profile")
            return
        # .get() — потому что в базе могут быть и СТАРЫЕ питомцы
        # (спринты 1-2.6): после миграции поля есть, но не полагаемся
        # на это лишний раз
        self.ids.hdr_avatar.source = resolve_media(pet.get("photo") or "")
        self.ids.l_name.text = pet.get("name") or "Без имени"
        self.ids.l_species.text = (
            pet.get("species") or "").strip() or "вид не указан"
        birth = pet.get("birth_date") or ""
        age = format_age(birth)
        third = (pet.get("breed") or "").strip() or "порода не указана"
        if age:
            third += f"  ·  {age}"
        if birth:
            third += f"  ·  род. {fmt_display(birth)}"
        self.ids.l_line3.text = third

        self._build_photos()
        self._build_videos()
        self._build_meds()
        self._build_feedings()
        self._build_nutr_panel()
        self._build_diet()
        self._build_diet_reco()
        self._build_weights()

    def back(self):
        self.app.go_to("profile")

    # ================================================ лечение и правка
    def open_treatment(self):
        """Экран «Лечение и назначения» (функционал спринтов 1-2.6):
        выбор препарата, будильники, история назначений."""
        self.app.open_treatment(self.pet_id)

    def edit_pet(self):
        """Анкета питомца в режиме редактирования."""
        self.app.edit_pet(self.pet_id)

    def confirm_delete_pet(self):
        """Диалог подтверждения удаления питомца (как в старом профиле:
        MDDialog проверен на GT 710, FBO-мины в нём нет)."""
        from kivymd.uix.dialog import (
            MDDialog,
            MDDialogButtonContainer,
            MDDialogHeadlineText,
            MDDialogSupportingText,
        )
        from kivymd.uix.button import MDButton, MDButtonText

        pet = db.get_pet(self.pet_id)
        pet_name = (pet or {}).get("name") or "питомца"

        def do_delete(*_args):
            dialog.dismiss()
            db.delete_pet(self.pet_id)
            self.app.show_toast("Питомец удалён")
            self.app.go_to("profile")

        dialog = MDDialog(
            MDDialogHeadlineText(text="Удалить питомца?"),
            MDDialogSupportingText(
                text=f"Вы уверены, что хотите удалить «{pet_name}»? "
                     f"Будут удалены также его галереи, диеты, вес и "
                     f"напоминания. Это действие нельзя отменить."
            ),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Отмена"),
                    on_release=lambda *_: dialog.dismiss(),
                ),
                MDButton(
                    MDButtonText(text="Удалить"),
                    on_release=do_delete,
                    theme_bg_color="Custom",
                    md_bg_color=T.DANGER,
                ),
                spacing=dp(8),
            ),
        )
        dialog.open()

    # ================================================== галерея фото
    def _build_photos(self):
        box = self.ids.photos_box
        box.clear_widgets()
        photos = db.get_media(self.pet_id, "photo")
        # порядок показа в просмотрщике = порядок плиток в галерее
        self._photo_paths = [resolve_media(m["path"]) for m in photos]
        if not photos:
            box.add_widget(self._hint("Фото пока нет — добавьте первое!"))
        for idx, m in enumerate(photos):
            tile = MDCard(
                size_hint=(None, None), size=(dp(96), dp(96)),
                radius=[dp(12)], md_bg_color=T.GREEN_SOFT,
                ripple_behavior=True,
            )
            # тап по плитке (не по крестику) -> полноэкранный просмотр
            tile.bind(on_release=lambda *a, i=idx: self.open_photo(i))
            tile.add_widget(FitImage(
                source=resolve_media(m["path"]), radius=[dp(12)],
            ))
            del_btn = MDIconButton(
                icon="close-circle", pos_hint={"right": 0.98, "top": 0.98},
                theme_icon_color="Custom", icon_color=T.DANGER,
                md_bg_color=T.WHITE, icon_size="18sp",
            )
            del_btn.bind(
                on_release=lambda *a, mid=m["id"], p=m["path"]:
                self.delete_photo(mid, p)
            )
            tile.add_widget(del_btn)
            box.add_widget(tile)

    def open_photo(self, index: int):
        """Полноэкранный просмотр фото с листанием по галерее."""
        self.app.root.ids.screen_manager.get_screen(
            "media_viewer").open_photos(self._photo_paths, index)

    def add_photo(self):
        src = pick_media_src("photo")
        if not src:
            return
        rel = copy_media_to(src, self.pet_id)
        if rel:
            db.add_media(self.pet_id, rel, "photo")
            self._build_photos()
            self.app.show_toast("Фото добавлено")

    def delete_photo(self, media_id: int, path: str):
        db.delete_media(media_id)
        delete_media_file(path)
        self._build_photos()
        self.app.show_toast("Фото удалено")

    # ================================================== галерея видео
    def _build_videos(self):
        """Карточки клипов БЕЗ плееров: раньше каждый клип в списке
        создавал свой VideoPlayer — все видео грузились одновременно,
        экран вис, а без ffpyplayer всё секция показывала заглушку.
        Теперь список лёгкий (иконка + имя файла), а плеер создаётся
        один раз и только когда пользователь открыл клип."""
        box = self.ids.videos_box
        box.clear_widgets()
        videos = db.get_media(self.pet_id, "video")
        self._video_paths = [resolve_media(m["path"]) for m in videos]
        if not videos:
            box.add_widget(self._hint(
                "Видео пока нет. Добавьте клип — он откроется в "
                "полноэкранном плеере"
            ))
            return
        for idx, m in enumerate(videos):
            card = MDCard(
                orientation="horizontal",
                md_bg_color=T.GREEN_SOFT,
                radius=[dp(12)],
                size_hint_y=None, height=dp(56),
                padding=[dp(12), 0],
                spacing=dp(8),
                ripple_behavior=True,
            )
            card.bind(on_release=lambda *a, i=idx: self.open_video(i))
            card.add_widget(MDIcon(
                icon="play-circle-outline",
                theme_icon_color="Custom", icon_color=T.GREEN,
                size_hint_x=None, size_hint_y=None,
                size=(dp(28), dp(28)),
                pos_hint={"center_y": 0.5},
            ))
            card.add_widget(MDLabel(
                text=_esc(m["path"].split("/")[-1]),
                theme_text_color="Custom", text_color=T.TEXT_MAIN,
                valign="middle",
                size_hint_x=1,
                text_size=(None, None),
            ))
            del_btn = MDIconButton(
                icon="delete-outline", theme_icon_color="Custom",
                icon_color=T.DANGER, icon_size="20sp",
                pos_hint={"center_y": 0.5},
            )
            del_btn.bind(
                on_release=lambda *a, mid=m["id"], p=m["path"]:
                self.delete_video(mid, p)
            )
            card.add_widget(del_btn)
            box.add_widget(card)

    def open_video(self, index: int):
        """Полноэкранный плеер; видео грузится только сейчас."""
        if not HAS_FFPY:
            self.app.show_toast(
                "Нужен ffpyplayer: " + FFPY_INSTALL_HINT, duration=4)
        self.app.root.ids.screen_manager.get_screen(
            "media_viewer").open_videos(self._video_paths, index)

    def add_video(self):
        src = pick_media_src("video")
        if not src:
            return
        rel = copy_media_to(src, self.pet_id)
        if rel:
            db.add_media(self.pet_id, rel, "video")
            self._build_videos()
            self.app.show_toast("Видео добавлено")

    def delete_video(self, media_id: int, path: str):
        db.delete_media(media_id)
        delete_media_file(path)
        self._build_videos()
        self.app.show_toast("Видео удалено")

    # ================================================== лекарства
    def _build_meds(self):
        box = self.ids.meds_box
        box.clear_widgets()
        meds = db.get_meds(self.pet_id)
        if not meds:
            box.add_widget(self._hint("Напоминаний о лекарствах нет"))
        for m in meds:
            row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
            row.add_widget(MDLabel(
                text=f"[b]{m['time']}[/b]  {_esc(m['title'])}",
                markup=True, theme_text_color="Custom",
                text_color=T.TEXT_MAIN, valign="middle",
                text_size=(self.width - dp(70), None),
            ))
            row.add_widget(self._del_btn(
                lambda *a, mid=m["id"]: self.delete_med(mid)))
            box.add_widget(row)

    def add_med(self):
        title = self.ids.med_title.text.strip()
        time_s = self.ids.med_time.text.strip()
        if not title or ":" not in time_s:
            self.app.show_toast("Укажите название и время (ЧЧ:ММ)")
            return
        try:
            hh, mm = time_s.split(":")
            _dt.time(int(hh), int(mm))
        except ValueError:
            self.app.show_toast("Время должно быть ЧЧ:ММ, например 09:30")
            return
        db.add_med(self.pet_id, title, f"{int(hh):02d}:{int(mm):02d}")
        self.ids.med_title.text = ""
        self.ids.med_time.text = ""
        self._build_meds()
        self.app.show_toast("Напоминание о лекарстве добавлено")

    def delete_med(self, med_id: int):
        db.delete_med(med_id)
        self._build_meds()

    # ================================================== кормление
    def _build_feedings(self):
        box = self.ids.feed_box
        box.clear_widgets()
        items = db.get_feedings(self.pet_id)
        if not items:
            box.add_widget(self._hint(
                "Расписания кормления нет. Нажмите иконку калькулятора,"
                " чтобы рассчитать норму, или добавьте время вручную"
            ))
        for f in items:
            row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
            text = f"[b]{f['time']}[/b]"
            grams = f.get("grams") or 0
            if grams:
                text += f"  ·  [b]{grams:.0f} г[/b]"
            note = _esc(f.get("note") or "")
            if note:
                text += f"  ·  {note}"
            row.add_widget(MDLabel(
                text=text,
                markup=True, theme_text_color="Custom",
                text_color=T.TEXT_MAIN, valign="middle",
                text_size=(self.width - dp(70), None),
            ))
            row.add_widget(self._del_btn(
                lambda *a, fid=f["id"]: self.delete_feeding(fid)))
            box.add_widget(row)

    def add_feeding(self):
        time_s = self.ids.feed_time.text.strip()
        note = self.ids.feed_note.text.strip()
        if ":" not in time_s:
            self.app.show_toast("Укажите время кормления (ЧЧ:ММ)")
            return
        try:
            hh, mm = time_s.split(":")
            _dt.time(int(hh), int(mm))
        except ValueError:
            self.app.show_toast("Время должно быть ЧЧ:ММ, например 18:00")
            return
        db.add_feeding(self.pet_id, f"{int(hh):02d}:{int(mm):02d}", note)
        self.ids.feed_time.text = ""
        self.ids.feed_note.text = ""
        self._build_feedings()
        self.app.show_toast("Кормление добавлено в расписание")

    def delete_feeding(self, feeding_id: int):
        db.delete_feeding(feeding_id)
        self._build_feedings()

    # ===================================== кормление: расчёт нормы
    def _saved_nutr(self) -> tuple:
        """Сохранённые параметры расчёта: 'ster|activity|kcal'."""
        raw = db.get_setting(f"nutr:{self.pet_id}", "") or ""
        parts = raw.split("|")
        parts = (parts + ["", "", ""])[:3]
        ster = parts[0] == "1" if parts[0] else False
        act = parts[1] if parts[1] in nutr.ACTIVITY_LEVELS else "средняя"
        return ster, act, parts[2]

    def _saved_ster(self) -> bool:
        return self._saved_nutr()[0]

    def _saved_activity(self) -> str:
        return self._saved_nutr()[1]

    def _pet_context(self) -> dict:
        """Вид, дата рождения, последний вес — общий контекст расчётов."""
        pet = db.get_pet(self.pet_id) or {}
        last = db.get_last_weight(self.pet_id)
        weight = None
        if last:
            weight = float(last["kg"])
        elif pet.get("weight"):
            try:
                weight = float(pet["weight"])
            except (TypeError, ValueError):
                weight = None
        return {
            "species": (pet.get("species") or "").strip() or "Кошка",
            "birth": pet.get("birth_date") or "",
            "weight": weight,
            "name": pet.get("name") or "",
        }

    def toggle_nutr(self):
        self._nutr_open = not self._nutr_open
        self._build_nutr_panel()

    def _on_nutr_text(self, instance, value):
        """Поля панели меняются -> сохранить и пересчитать результат."""
        if instance is getattr(self, "_nutr_w_field", None):
            self._nutr_weight_s = value
        elif instance is getattr(self, "_nutr_k_field", None):
            self._nutr_kcal_s = value
        self.refresh_nutr_result()

    @staticmethod
    def _parse_float(s) -> float | None:
        try:
            v = float(str(s).strip().replace(",", "."))
        except (TypeError, ValueError):
            return None
        return v if v > 0 else None

    def _current_plan(self):
        """Расчёт нормы по текущим значениям полей (или None)."""
        ctx = self._pet_context()
        weight = self._parse_float(self._nutr_weight_s) or ctx["weight"]
        if not weight:
            return None
        food_kcal = self._parse_float(self._nutr_kcal_s) \
            or nutr.DEFAULT_FOOD_KCAL
        # если активна диета на снижение — считаем по её коэффициенту
        diet = db.get_active_diet(self.pet_id)
        goal = (diet or {}).get("goal") or "normal"
        return nutr.calc_daily(
            ctx["species"], weight, ctx["birth"],
            self._nutr_ster, self._nutr_act, food_kcal, goal=goal,
        )

    def _build_nutr_panel(self):
        box = self.ids.nutr_box
        box.clear_widgets()
        self._nutr_result_lbl = None
        if not self._nutr_open:
            return
        _, _, kcal_saved = self._saved_nutr()
        if not self._nutr_weight_s:
            ctx = self._pet_context()
            if ctx["weight"]:
                self._nutr_weight_s = f"{ctx['weight']:.2f}".rstrip("0") \
                    .rstrip(".")
        if not self._nutr_kcal_s:
            self._nutr_kcal_s = kcal_saved or str(nutr.DEFAULT_FOOD_KCAL)

        ctx = self._pet_context()
        stage = nutr.life_stage(ctx["species"], ctx["birth"])
        who = f"{ctx['species']} · {stage['title']}"
        if ctx["weight"]:
            who += f" · {ctx['weight']:.2f} кг"

        panel = MDCard(
            orientation="vertical", md_bg_color=T.GREEN_SOFT,
            radius=[dp(12)], padding=dp(12), spacing=dp(8),
            adaptive_height=True,
        )
        panel.add_widget(_auto_label(
            "[b]Расчёт суточной нормы[/b]", T.GREEN, "14sp", wrap=dp(280)))
        panel.add_widget(_auto_label(
            who + " · метод RER/MER (WSAVA)", T.TEXT_SUB, "12sp",
            wrap=dp(280)))

        row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        self._nutr_w_field = _field("Вес, кг", 0.5, self._on_nutr_text)
        self._nutr_w_field.text = self._nutr_weight_s
        self._nutr_k_field = _field("Корм, ккал/100 г", 0.5,
                                    self._on_nutr_text)
        self._nutr_k_field.text = self._nutr_kcal_s
        row.add_widget(self._nutr_w_field)
        row.add_widget(self._nutr_k_field)
        panel.add_widget(row)

        tog = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        tog.add_widget(self._toggle_btn(
            f"Стерилизован: {'да' if self._nutr_ster else 'нет'}",
            self._nutr_ster, self._toggle_ster))
        tog.add_widget(self._toggle_btn(
            f"Активность: {self._nutr_act}",
            self._nutr_act != "низкая", self._cycle_activity))
        panel.add_widget(tog)

        self._nutr_result_lbl = _auto_label("", T.TEXT_MAIN, "13sp",
                                            wrap=dp(280))
        panel.add_widget(self._nutr_result_lbl)

        apply_btn = MDButton(style="filled", size_hint_y=None,
                             height=dp(40))
        apply_btn.add_widget(MDButtonText(
            text="Применить к расписанию кормлений"))
        apply_btn.bind(on_release=lambda *a: self.apply_nutr_plan())
        panel.add_widget(apply_btn)
        panel.add_widget(_auto_label(
            "Заменит текущее расписание кормлений (время + порции)",
            T.TEXT_SUB, "11sp", wrap=dp(280)))

        box.add_widget(panel)
        self.refresh_nutr_result()

    def _toggle_btn(self, text: str, active: bool, cb) -> MDButton:
        btn = MDButton(
            style="outlined", size_hint_y=None, height=dp(38),
            theme_bg_color="Custom",
            md_bg_color=T.GREEN_SOFT if active else T.WHITE,
            theme_line_color="Custom",
            line_color=T.GREEN,
        )
        btn.add_widget(MDButtonText(
            text=text, theme_text_color="Custom",
            text_color=T.GREEN if active else T.TEXT_SUB,
            font_size="12sp"))
        btn.bind(on_release=lambda *a: cb())
        return btn

    def _toggle_ster(self):
        self._nutr_ster = not self._nutr_ster
        self._build_nutr_panel()

    def _cycle_activity(self):
        i = nutr.ACTIVITY_LEVELS.index(self._nutr_act)
        self._nutr_act = nutr.ACTIVITY_LEVELS[
            (i + 1) % len(nutr.ACTIVITY_LEVELS)]
        self._build_nutr_panel()

    def refresh_nutr_result(self, *args):
        if not self._nutr_open or self._nutr_result_lbl is None:
            return
        plan = self._current_plan()
        self._last_plan = plan
        if plan is None:
            self._nutr_result_lbl.text = (
                "Укажите вес питомца (или запишите замер веса) — "
                "и здесь появится норма по формуле RER/MER")
            return
        self._nutr_result_lbl.text = "\n".join(plan["lines"])

    def apply_nutr_plan(self):
        plan = self._current_plan()
        if plan is None:
            self.app.show_toast("Сначала укажите вес питомца")
            return
        if not plan["grams_meal"]:
            self.app.show_toast("Укажите калорийность корма, ккал/100 г")
            return
        note = f"норма {plan['grams_day']} г/сутки"
        rows = [(t, plan["grams_meal"], note) for t in plan["times"]]
        db.replace_feedings(self.pet_id, rows)
        db.set_setting(
            f"nutr:{self.pet_id}",
            f"{int(self._nutr_ster)}|{self._nutr_act}|{self._nutr_kcal_s}",
        )
        self._nutr_open = False
        self._build_nutr_panel()
        self._build_feedings()
        self.app.show_toast(
            f"Готово: {plan['meals']} кормления по {plan['grams_meal']} г")

    # ================================================== диета
    def toggle_diet_reco(self):
        self._diet_reco_open = not self._diet_reco_open
        self._build_diet_reco()

    def _build_diet_reco(self):
        box = self.ids.diet_reco_box
        box.clear_widgets()
        if not self._diet_reco_open:
            return
        ctx = self._pet_context()
        ws = db.get_weights(self.pet_id)
        trend = (ws[-1]["kg"] - ws[-2]["kg"]) if len(ws) >= 2 else 0.0
        weight = ctx["weight"]
        opts = nutr.diet_options(
            ctx["species"], weight, ctx["birth"], self._nutr_ster, trend)

        box.add_widget(_auto_label(
            "Подобрано по виду, возрасту, стерилизации и динамике веса:",
            T.TEXT_SUB, "12sp", wrap=dp(280)))
        for opt in opts:
            card = MDCard(
                orientation="vertical", md_bg_color=T.CARD,
                line_color=T.CARD_BORDER, radius=[dp(12)],
                padding=dp(10), spacing=dp(4), adaptive_height=True,
            )
            card.add_widget(_auto_label(
                f"[b]{opt['title']}[/b]", T.GREEN, "14sp", wrap=dp(270)))
            card.add_widget(_auto_label(
                opt["why"], T.TEXT_SUB, "12sp", wrap=dp(270)))
            if weight:
                plan = nutr.calc_daily(
                    ctx["species"], weight, ctx["birth"],
                    self._nutr_ster, self._nutr_act, goal=opt["goal"])
                meta = f"~{plan['kcal']} ккал/день · {opt['days']} дн."
            else:
                meta = f"{opt['days']} дн. · запишите вес для расчёта ккал"
            card.add_widget(_auto_label(meta, T.TEXT_MAIN, "12sp",
                                        wrap=dp(270)))
            row = BoxLayout(size_hint_y=None, height=dp(34))
            btn = MDButton(style="filled", size_hint_x=None,
                           width=dp(110), pos_hint={"x": 0})
            btn.add_widget(MDButtonText(text="Начать", font_size="13sp"))
            btn.bind(on_release=lambda *a, o=dict(opt):
                     self.start_diet_from_reco(o))
            row.add_widget(btn)
            card.add_widget(row)
            box.add_widget(card)
        box.add_widget(_auto_label(
            "«Начать» подставит параметры в форму ниже — останется "
            "проверить и нажать «Начать»", T.TEXT_SUB, "11sp",
            wrap=dp(280)))

    def start_diet_from_reco(self, opt: dict):
        """Кнопка «Начать» у варианта диеты: подставить в форму."""
        ctx = self._pet_context()
        self._pending_goal = opt
        self.ids.diet_title.text = opt["title"]
        self.ids.diet_days.text = str(opt["days"])
        meals = nutr.meals_per_day(
            ctx["species"], nutr.age_months(ctx["birth"]))
        self.ids.diet_times.text = ", ".join(nutr.meal_times(meals))
        self._diet_reco_open = False
        self._build_diet_reco()
        self.app.show_toast(
            "Параметры подставлены — проверьте форму и нажмите «Начать»")

    def _build_diet(self):
        box = self.ids.diet_box
        box.clear_widgets()
        diet = db.get_active_diet(self.pet_id)
        if not diet:
            box.add_widget(self._hint(
                "Активной диеты нет. Нажмите иконку лампочки, чтобы "
                "подобрать рацион, или создайте свой ниже"
            ))
            return

        start = parse_date(diet["start_date"])
        today = _dt.date.today()
        day_no = (today - start).days + 1 if start else 1
        total = diet["days"]
        finished = day_no > total

        card = MDCard(
            orientation="vertical", md_bg_color=T.GREEN_SOFT,
            radius=[dp(14)], padding=dp(12), spacing=dp(4),
            adaptive_height=True,
        )
        card.add_widget(_auto_label(
            f"[b]Диета «{_esc(diet['title'])}»[/b]", T.GREEN, "14sp",
            wrap=dp(270)))
        lines = [
            f"Старт {fmt_display(diet['start_date'])} · {total} дн. · "
            f"день {min(day_no, total)} из {total}"
        ]
        if diet.get("kcal"):
            lines.append(f"Норма ~{diet['kcal']} ккал/день")
        if diet.get("target_weight"):
            ctx = self._pet_context()
            now_s = (f"{ctx['weight']:.2f}" if ctx["weight"] else "?")
            lines.append(
                f"Цель: {diet['target_weight']:.1f} кг (сейчас {now_s})")
        goal_txt = nutr.goal_factor(diet.get("goal") or "")
        if goal_txt and goal_txt != "normal":
            lines.append(f"Тип: {goal_txt}")
        card.add_widget(_auto_label("\n".join(lines), T.TEXT_SUB, "12sp",
                                    wrap=dp(270)))
        card.add_widget(MDLinearProgressIndicator(
            value=min(100.0, max(0.0, day_no / total * 100.0)),
            size_hint_y=None, height=dp(6), radius=[dp(3)],
        ))

        row = BoxLayout(size_hint_y=None, height=dp(36))
        if finished:
            btn = MDButton(style="filled", size_hint_x=None, width=dp(250))
            btn.add_widget(MDButtonText(
                text="Диета завершена — записать вес"))
            btn.bind(on_release=lambda *a: self.focus_weight())
            row.add_widget(btn)
        else:
            btn = MDButton(style="text", size_hint_x=None, width=dp(140),
                           pos_hint={"right": 1})
            btn.add_widget(MDButtonText(
                text="Завершить досрочно", font_size="12sp"))
            btn.bind(on_release=lambda *a: self.finish_diet())
            row.add_widget(btn)
        card.add_widget(row)
        box.add_widget(card)

    def create_diet(self):
        title = self.ids.diet_title.text.strip()
        days_s = self.ids.diet_days.text.strip()
        times_s = self.ids.diet_times.text.strip()
        if not title or not days_s.isdigit() or not (1 <= int(days_s) <= 365):
            self.app.show_toast("Укажите название и срок диеты (1–365 дней)")
            return
        goal = (self._pending_goal or {}).get("goal", "")
        ctx = self._pet_context()
        weight = ctx["weight"]
        food_kcal = self._parse_float(self._nutr_kcal_s) \
            or nutr.DEFAULT_FOOD_KCAL

        plan = None
        if weight:
            plan = nutr.calc_daily(
                ctx["species"], weight, ctx["birth"], self._nutr_ster,
                self._nutr_act, food_kcal, goal=goal or "normal")
        kcal = plan["kcal"] if plan else 0
        target = round(weight * 0.9, 2) \
            if (weight and goal == "weight_loss") else 0.0

        start = _dt.date.today().strftime("%Y-%m-%d")
        db.add_diet(self.pet_id, title, start, int(days_s),
                    goal=goal, kcal=kcal, target_weight=target)
        # времена кормления диеты -> в общий график кормления (с порциями)
        added = 0
        for t in times_s.replace(";", ",").split(","):
            t = t.strip()
            if not t or ":" not in t:
                continue
            try:
                hh, mm = t.split(":")
                _dt.time(int(hh), int(mm))
            except ValueError:
                continue
            grams = plan["grams_meal"] if plan else 0
            db.add_feeding(self.pet_id, f"{int(hh):02d}:{int(mm):02d}",
                           f"диета «{title}»", grams=grams)
            added += 1
        self.ids.diet_title.text = ""
        self.ids.diet_days.text = ""
        self.ids.diet_times.text = ""
        self._pending_goal = None
        self._build_diet()
        self._build_feedings()
        msg = f"Диета начата. Кормлений в расписании: +{added}"
        if kcal:
            msg += f" · норма ~{kcal} ккал/день"
        self.app.show_toast(msg)

    def finish_diet(self):
        diet = db.get_active_diet(self.pet_id)
        if diet:
            db.finish_diet(diet["id"])
            self._build_diet()
            self.app.show_toast("Диета завершена. Теперь взвесьте питомца")

    def focus_weight(self):
        self.ids.weight_input.focus = True

    # ================================================== вес
    def _build_weights(self):
        weights = db.get_weights(self.pet_id)
        last = weights[-1] if weights else None
        if last:
            delta = ""
            if len(weights) >= 2:
                diff = last["kg"] - weights[-2]["kg"]
                # юникод-стрелки не рендерятся Roboto на Windows —
                # только слова (урок: квадратик вместо символа)
                if diff > 0:
                    delta = f"  ·  рост +{diff:.2f} кг"
                elif diff < 0:
                    delta = f"  ·  снижение {abs(diff):.2f} кг"
                else:
                    delta = "  ·  без изменений"
            self.ids.l_last_weight.text = (
                f"Последний замер: {last['kg']:.2f} кг "
                f"({fmt_display(last['weighed_at'])}){delta}"
            )
        else:
            self.ids.l_last_weight.text = "Замеров пока нет"

        # список последних 6 замеров
        lst = self.ids.weights_list
        lst.clear_widgets()
        # ВСЕ замеры, свежие сверху, со словесной динамикой
        # (юникод-стрелки не рендерятся Roboto на Windows — слова)
        for i in range(len(weights) - 1, -1, -1):
            w = weights[i]
            text = f"{fmt_display(w['weighed_at'])} — {w['kg']:.2f} кг"
            if i > 0:
                d = w["kg"] - weights[i - 1]["kg"]
                if d > 0:
                    text += f"  ·  рост +{d:.2f}"
                elif d < 0:
                    text += f"  ·  снижение {abs(d):.2f}"
            lst.add_widget(MDLabel(
                text=text,
                theme_text_color="Custom", text_color=T.TEXT_MAIN,
                size_hint_y=None, height=dp(24),
            ))

        # сводка по истории (вместо убранного Canvas-графика)
        if len(weights) >= 2:
            kgs = [w["kg"] for w in weights]
            diff = kgs[-1] - kgs[0]
            diff_s = (f"+{diff:.2f}" if diff > 0
                      else f"{diff:.2f}")  # знак уже в числе
            self.ids.l_weight_stats.text = (
                f"Всего замеров: {len(kgs)} · мин {min(kgs):.2f} · "
                f"макс {max(kgs):.2f} · разница "
                f"{abs(max(kgs) - min(kgs)):.2f} кг · "
                f"за период {diff_s} кг"
            )
        elif len(weights) == 1:
            self.ids.l_weight_stats.text = (
                "Запишите вес ещё раз — появится сводка изменений")
        else:
            self.ids.l_weight_stats.text = ""

    def add_weight(self):
        s = self.ids.weight_input.text.strip().replace(",", ".")
        try:
            kg = float(s)
            if not (0.01 <= kg <= 2000):
                raise ValueError
        except ValueError:
            self.app.show_toast("Введите вес в кг, например 4.2")
            return
        db.add_weight(self.pet_id, kg)
        self.ids.weight_input.text = ""
        self._build_weights()
        self._build_diet_reco()   # тренд изменился — пересчитать подбор
        self.app.show_toast(f"Записано: {kg:.2f} кг")

    # ================================================== утилиты
    def _hint(self, text: str) -> MDLabel:
        """Подсказка секции с АВТО-высотой (без наложений)."""
        return _auto_label(text, T.TEXT_SUB, "13sp", halign="center",
                           wrap_width=dp(280))

    def _del_btn(self, callback) -> MDIconButton:
        btn = MDIconButton(
            icon="delete-outline", theme_icon_color="Custom",
            icon_color=T.DANGER, icon_size="20sp",
            size_hint=(None, None), size=(dp(30), dp(30)),
            pos_hint={"center_y": 0.5},
        )
        btn.bind(on_release=callback)
        return btn
