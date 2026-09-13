# -*- coding: utf-8 -*-
"""Экран согласия с условиями (первый запуск).

kv-файл использует root.app.accept_disclaimer() — поэтому нужен
AppMixin (иначе kv не найдёт атрибут app у экрана).
"""
from kivymd.uix.screen import MDScreen

from screens import AppMixin


class DisclaimerScreen(AppMixin, MDScreen):
    pass
