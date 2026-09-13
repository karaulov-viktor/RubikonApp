# -*- coding: utf-8 -*-
"""Личная страница питомца.

Сверху вниз:
  - аватар НА ВСЮ ШИРИНУ экрана (260dp) + кнопка назад
  - карточка информации: имя / вид / порода · возраст · дата рождения
  - Галерея фото (плитки 96dp, добавление, удаление)
  - Галерея видео (инлайн-плеер как в Instagram, VideoPlayer+ffpyplayer)
  - Лекарства (список + добавление)  -> уведомления по времени
  - Кормление (расписание + добавление) -> уведомления по времени
  - Диета (активная карточка с прогрессом ИЛИ форма создания;
    в последний день — предложение взвесить питомца)
  - Вес (Canvas-график динамики + список + запись замера)

Все списки строятся кодом; kv держит каркас и заголовки секций.
"""
import datetime as _dt

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.videoplayer import VideoPlayer
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.fitimage import FitImage
from kivymd.uix.label import MDLabel
from kivymd.uix.progressindicator import MDLinearProgressIndicator
from kivymd.uix.screen import MDScreen

from kivy.factory import Factory

from models import database as db
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




class WeightChart(Widget):
    """Самодельный Canvas-график веса: линия + точки. Без библиотек."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._weights = []
        # при первом рендере width ещё 0 — перерисовка после лэйаута
        self.bind(size=self._redraw)

    def _redraw(self, *args):
        self.set_data(self._weights)

    def set_data(self, weights: list):
        self._weights = weights
        self.canvas.clear()
        if len(weights) < 2 or self.width < dp(50):
            return
        kgs = [w["kg"] for w in weights]
        n = len(kgs)
        kmin, kmax = min(kgs), max(kgs)
        if kmax - kmin < 1e-9:
            kmax = kmin + 1
        pad_x, pad_top, pad_bot = dp(14), dp(10), dp(10)
        step_x = (self.width - 2 * pad_x) / (n - 1)
        pts = []
        dots = []
        for i, kg in enumerate(kgs):
            x = pad_x + step_x * i
            y = pad_bot + (self.height - pad_top - pad_bot) * \
                (kg - kmin) / (kmax - kmin)
            pts += [x, y]
            dots.append((x, y))
        with self.canvas:
            Color(*T.CARD_BORDER)
            Line(points=[pad_x, pad_bot,
                         self.width - pad_x, pad_bot], width=1)
            Color(*T.GREEN)
            Line(points=pts, width=dp(1.6))
            Color(*T.GREEN_DARK)
            for (x, y) in dots:
                Ellipse(pos=(x - dp(3), y - dp(3)), size=(dp(6), dp(6)))


class PetDetailScreen(AppMixin, MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pet_id = None

    # ================================================== открытие экрана
    def open_pet(self, pet_id: int):
        self.pet_id = pet_id
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
        self._build_diet()
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
        if not photos:
            box.add_widget(self._hint("Фото пока нет — добавьте первое!"))
        for m in photos:
            tile = MDCard(
                size_hint=(None, None), size=(dp(96), dp(96)),
                radius=[dp(12)], md_bg_color=T.GREEN_SOFT,
            )
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
        box = self.ids.videos_box
        box.clear_widgets()
        videos = db.get_media(self.pet_id, "video")
        if not videos:
            box.add_widget(self._hint(
                "Видео пока нет. Добавьте клип — он проиграется прямо тут,"
                " как в Instagram"
            ))
            return
        if not HAS_FFPY:
            box.add_widget(self._hint(
                "Для просмотра видео установите ffpyplayer:\n"
                "pip install ffpyplayer"
            ))
            return
        for m in videos:
            card = MDCard(
                orientation="vertical",
                md_bg_color=T.CARD,
                line_color=T.CARD_BORDER,
                radius=[dp(16)],
                size_hint_y=None, height=dp(250),
            )
            player = VideoPlayer(
                source=resolve_media(m["path"]),
                size_hint=(1, 1),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
                options={"allow_stretch": True},
            )
            card.add_widget(player)
            row = BoxLayout(size_hint_y=None, height=dp(40),
                            padding=[dp(10), 0])
            row.add_widget(MDLabel(
                text=m["path"].split("/")[-1],
                theme_text_color="Custom", text_color=T.TEXT_SUB,
                valign="middle",
                size_hint_x=1,
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
            row.add_widget(del_btn)
            card.add_widget(row)
            box.add_widget(card)

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
                text=f"[b]{m['time']}[/b]  {m['title']}",
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
                "Расписания кормления нет — добавьте время и рацион"
            ))
        for f in items:
            row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
            row.add_widget(MDLabel(
                text=f"[b]{f['time']}[/b]  {f['note'] or 'кормление'}",
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

    # ================================================== диета
    def _build_diet(self):
        box = self.ids.diet_box
        box.clear_widgets()
        diet = db.get_active_diet(self.pet_id)
        if not diet:
            box.add_widget(self._hint(
                "Активной диеты нет. Создайте: название рациона, срок в днях"
                " и время кормления — приложение напомнит о каждом приёме"
            ))
            return

        start = parse_date(diet["start_date"])
        today = _dt.date.today()
        day_no = (today - start).days + 1 if start else 1
        total = diet["days"]
        finished = day_no > total

        card = MDCard(
            orientation="vertical", md_bg_color=T.GREEN_SOFT,
            radius=[dp(14)], padding=dp(14), size_hint_y=None,
            height=dp(150), spacing=dp(4),
        )
        card.add_widget(MDLabel(
            text=f"[b]Диета «{diet['title']}»[/b]", markup=True,
            theme_text_color="Custom", text_color=T.GREEN,
            size_hint_y=None, height=dp(26),
        ))
        card.add_widget(MDLabel(
            text=f"Старт {fmt_display(diet['start_date'])} · "
                 f"{total} дн. · день {min(day_no, total)} из {total}",
            theme_text_color="Custom", text_color=T.TEXT_SUB,
            size_hint_y=None, height=dp(22),
        ))
        progress = MDLinearProgressIndicator(
            value=min(100.0, max(0.0, day_no / total * 100.0)),
            size_hint_y=None, height=dp(6), radius=[dp(3)],
        )
        card.add_widget(progress)

        if finished:
            btn = MDButton(style="filled", size_hint_y=None, height=dp(40))
            btn.add_widget(MDButtonText(
                text="Диета завершена — записать вес питомца"))
            btn.bind(on_release=lambda *a: self.focus_weight())
            card.add_widget(btn)
        box.add_widget(card)

    def create_diet(self):
        title = self.ids.diet_title.text.strip()
        days_s = self.ids.diet_days.text.strip()
        times_s = self.ids.diet_times.text.strip()
        if not title or not days_s.isdigit() or not (1 <= int(days_s) <= 365):
            self.app.show_toast("Укажите название и срок диеты (1–365 дней)")
            return
        start = _dt.date.today().strftime("%Y-%m-%d")
        db.add_diet(self.pet_id, title, start, int(days_s))
        # времена кормления диеты -> в общий график кормления
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
            db.add_feeding(self.pet_id, f"{int(hh):02d}:{int(mm):02d}", title)
            added += 1
        self.ids.diet_title.text = ""
        self.ids.diet_days.text = ""
        self.ids.diet_times.text = ""
        self._build_diet()
        self._build_feedings()
        self.app.show_toast(
            f"Диета начата. Кормлений в расписании: +{added}")

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
                arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
                delta = f"  ({arrow} {abs(diff):.2f} кг)"
            self.ids.l_last_weight.text = (
                f"Последний замер: {last['kg']:.2f} кг "
                f"({fmt_display(last['weighed_at'])}){delta}"
            )
        else:
            self.ids.l_last_weight.text = "Замеров пока нет"

        # список последних 6 замеров
        lst = self.ids.weights_list
        lst.clear_widgets()
        for w in reversed(weights[-6:]):
            lst.add_widget(MDLabel(
                text=f"{fmt_display(w['weighed_at'])} — {w['kg']:.2f} кг",
                theme_text_color="Custom", text_color=T.TEXT_SUB,
                size_hint_y=None, height=dp(24),
            ))

        chart = self.ids.weight_chart
        chart.set_data(weights)
        if len(weights) >= 2:
            kgs = [w["kg"] for w in weights]
            self.ids.l_chart_stats.text = (
                f"мин {min(kgs):.2f} кг · макс {max(kgs):.2f} кг · "
                f"Δ {max(kgs) - min(kgs):.2f} кг"
            )
        else:
            self.ids.l_chart_stats.text = (
                "График появится после двух замеров")

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
        self.app.show_toast(f"Записано: {kg:.2f} кг")

    # ================================================== утилиты
    def _hint(self, text: str) -> MDLabel:
        return MDLabel(
            text=text, halign="center",
            theme_text_color="Custom", text_color=T.TEXT_SUB,
            size_hint_y=None, height=dp(40),
            text_size=(self.width - dp(60), None),
        )

    def _del_btn(self, callback) -> MDIconButton:
        btn = MDIconButton(
            icon="delete-outline", theme_icon_color="Custom",
            icon_color=T.DANGER, icon_size="20sp",
            size_hint=(None, None), size=(dp(30), dp(30)),
            pos_hint={"center_y": 0.5},
        )
        btn.bind(on_release=callback)
        return btn


# kv использует WeightChart как вложенный виджет — имя должно быть
# в Factory к моменту создания PetDetailScreen (урок FactoryException)
Factory.register("WeightChart", cls=WeightChart)
