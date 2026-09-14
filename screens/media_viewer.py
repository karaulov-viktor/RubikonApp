# -*- coding: utf-8 -*-
"""Полноэкранный просмотрщик медиа питомца (фото и видео).

Зачем отдельный экран (вместо инлайн-плееров в списке):
  - фото по тапу открываются на весь экран с листанием
    (назад/вперёд по галерее);
  - видео грузится ТОЛЬКО когда пользователь его открыл — один
    плеер на всё приложение. Раньше каждый клип в списке создавал
    свой VideoPlayer: все видео начинали грузиться одновременно,
    экран «Анкета» тормозил, а без ffpyplayer показывалась заглушка;
  - экран открывается без нижнего меню (main.go_to это учитывает).

Почему AsyncImage, а не FitImage: FitImage обрезает фото под контейнер
(«cover»), для просмотрщика это неприемлемо — головы и лапы срезаются.
AsyncImage с fit_mode="contain" (Kivy 2.3) показывает фото целиком.

Видео: без ffpyplayer плеер НЕ создаётся вовсе (Kivy без провайдера
ffmpeg всё равно не сыграет) — вместо этого понятная подсказка с
точной командой установки. Плеер выгружается при закрытии/выходе
(unload), иначе файл держится открытым до конца работы приложения.
"""
from kivy.metrics import dp
from kivy.uix.videoplayer import VideoPlayer
from kivymd.uix.screen import MDScreen

from screens import AppMixin

try:
    import ffpyplayer  # noqa: F401
    HAS_FFPY = True
except Exception:
    HAS_FFPY = False

FFPY_HINT = (
    "Для просмотра видео нужен ffpyplayer.\n\n"
    "Установите его в venv проекта одной командой:\n"
    "venv\\Scripts\\python.exe -m pip install ffpyplayer\n\n"
    "Затем перезапустите приложение."
)


class MediaViewerScreen(AppMixin, MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._kind = "photo"       # "photo" | "video"
        self._paths = []
        self._index = 0
        self._player = None

    # ================================================== открытие
    def open_photos(self, paths: list, index: int = 0):
        """Открыть фото на весь экран. paths — абсолютные пути в
        ПОРЯДКЕ ОТОБРАЖЕНИЯ галереи, index — с какого начать."""
        self._open("photo", paths, index)

    def open_videos(self, paths: list, index: int = 0):
        self._open("video", paths, index)

    def _open(self, kind: str, paths: list, index: int):
        self._unload_player()
        self._kind = kind
        self._paths = list(paths or [])
        if not self._paths:
            return
        self._index = max(0, min(int(index), len(self._paths) - 1))
        self._show()
        self.app.go_to("media_viewer")

    # ================================================== показ слайда
    def _show(self):
        n = len(self._paths)
        pos = self._index + 1
        fname = self._paths[self._index].replace("\\", "/").split("/")[-1]

        # сцена: спрятать плеер/сообщения прошлых показов
        self.ids.video_stage.clear_widgets()
        self._unload_player()
        self.ids.l_msg.opacity = 0

        if self._kind == "photo":
            self.ids.photo_view.opacity = 1
            self.ids.photo_view.source = self._paths[self._index]
            self.ids.l_counter.text = f"Фото {pos} из {n}"
        else:
            # фото скрыто, видео — только по требованию
            self.ids.photo_view.opacity = 0
            self.ids.photo_view.source = ""
            self.ids.l_counter.text = f"Видео {pos} из {n}"
            if HAS_FFPY:
                self._start_player(self._paths[self._index])
            else:
                self.ids.l_msg.text = FFPY_HINT
                self.ids.l_msg.opacity = 1

        # листание нужно только когда элементов больше одного
        multi = n > 1
        self.ids.btn_prev.opacity = 1 if multi else 0
        self.ids.btn_next.opacity = 1 if multi else 0
        self.ids.btn_prev.disabled = not multi
        self.ids.btn_next.disabled = not multi

        # имя файла внизу (одна строка, ужимается по ширине)
        self.ids.l_fname.text = fname
        self.ids.l_fname.text_size = (self.ids.l_fname.width, None)

    def _start_player(self, path: str):
        player = VideoPlayer(
            source=path,
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            options={"allow_stretch": True},
        )
        self._player = player
        self.ids.video_stage.add_widget(player)

    # ================================================== навигация
    def next_media(self):
        if len(self._paths) > 1:
            self._index = (self._index + 1) % len(self._paths)
            self._show()

    def prev_media(self):
        if len(self._paths) > 1:
            self._index = (self._index - 1) % len(self._paths)
            self._show()

    # ================================================== закрытие
    def close(self):
        self._unload_player()
        self.app.go_to("pet_detail")

    def _unload_player(self):
        """Остановить и выгрузить видео (файл не держится открытым)."""
        if self._player is None:
            return
        try:
            self._player.state = "stopped"
        except Exception:
            pass
        try:
            self._player.unload()
        except Exception:
            pass
        self._player = None

    def on_leave(self, *args):
        """Страховка: уходим с экрана любым путём — выгрузить видео."""
        super().on_leave(*args)
        self._unload_player()

    def on_pre_enter(self, *args):
        # ширина нижней строки имени файла известна только после лэйаута
        super().on_pre_enter(*args)
        self.ids.l_fname.text_size = (self.ids.l_fname.width, None)
