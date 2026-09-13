# -*- coding: utf-8 -*-
"""Автономный нотификатор RubikonApp — запускается Планировщиком Windows
когда ПРИЛОЖЕНИЕ ЗАКРЫТО.

Регистрация задачи (делает кнопка в приложении):
  schtasks /Create /SC MINUTE /MO 15 /TN RubikonAppReminder /F
           /TR "\"C:\\...\\pythonw.exe\" \"I:\\Rubikon_vet\\notifier.py\""

Тихий процесс: без окна консоли (pythonw), без интерфейса,
ошибки — в data/notifier.log. Запуск вручную для проверки:
  D:\\PYTHON\\python.exe notifier.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.notifier import run_once  # noqa: E402

if __name__ == "__main__":
    run_once()
