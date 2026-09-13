# -*- coding: utf-8 -*-
"""Общий миксин для экранов: свойство self.app.

Единая точка доступа к запущенному приложению из любого экрана
(App.get_running_app()). Нужен, потому что код экранов вызывает
self.app.go_to(...), self.app.show_toast(...) и т.д.
"""
from kivy.app import App


class AppMixin:
    """Даёт экранам self.app без копипасты."""

    @property
    def app(self):
        return App.get_running_app()
