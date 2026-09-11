"""
fix_kivymd_fbo.py — одноразовый фикс KivyMD 2.0.0 для ошибки:

    FBO Initialization failed: Incomplete attachment (36054)

Откуда ошибка: в установленной KivyMD 2.0.0 виджеты с ripple-эффектом
(MDCard, MDSnackbar, MDDialog...) при СОЗДАНИИ рисуют невидимый холст
Fbo размером с себя. Если виджет в этот момент имеет нулевую ширину
или высоту, видеокарта отказывается создавать пустой холст — приложение
падает. На GT 710 / драйвер 475.14 это происходит всегда.

Что делает скрипт:
  1. Находит KivyMD в site-packages ТЕКУЩЕГО python (без импорта —
     скрипту не нужен ни экран, ни работающий kivy).
  2. Делает резервную копию ripple_behavior.py -> .bak.
  3. Меняет Fbo(size=self.size) на Fbo(size=[50] * 2) в init_fbos —
     ровно так это уже исправлено в актуальной ветке master KivyMD
     (kivymd/uix/behaviors/ripple_behavior.py, функция init_fbos).

Запуск на КАЖДОЙ машине, где стоит приложение:
    python fix_kivymd_fbo.py

Если KivyMD ставился без --user, запускайте от администратора.
Скрипт можно запускать повторно — он увидит, что уже пропатчено.
"""

import os
import re
import shutil
import sysconfig

SITE = sysconfig.get_paths()["purelib"]
TARGET = os.path.join(SITE, "kivymd", "uix", "behaviors", "ripple_behavior.py")

OLD_FBO = 'Fbo(size=self.size, group="m3_ripple_behavior")'
NEW_FBO = 'Fbo(size=[50] * 2, group="m3_ripple_behavior")'
OLD_RECT = "Rectangle(pos=(0, 0), size=self.size)"
NEW_RECT = "Rectangle(pos=(0, 0), size=[50] * 2)"


def main():
    if not os.path.exists(TARGET):
        raise SystemExit(
            f"KivyMD не найден: {TARGET}\n"
            "Запустите скрипт тем python, которым запускается приложение."
        )

    # Версию читаем текстом, чтобы НЕ импортировать kivymd
    # (импорт kivymd сам создаёт окно и без дисплея падает).
    version = "?"
    try:
        version_file = os.path.join(SITE, "kivymd", "_version.py")
        with open(version_file, encoding="utf-8") as f:
            match = re.search(
                r"__version__\s*=\s*['\"]([^'\"]+)['\"]", f.read()
            )
        if match:
            version = match.group(1)
    except OSError:
        pass

    print(f"KivyMD {version}")
    print(f"Файл: {TARGET}")

    with open(TARGET, encoding="utf-8", newline="") as f:
        src = f.read()

    if NEW_FBO in src:
        print("Уже пропатчено — ничего не делаю.")
        return

    if OLD_FBO not in src:
        raise SystemExit(
            "Не нашёл ожидаемую строку Fbo(size=self.size...). "
            "Похоже, другая версия KivyMD — напишите автору патча."
        )

    shutil.copyfile(TARGET, TARGET + ".bak")
    print(f"Резервная копия: {TARGET}.bak")

    src = src.replace(OLD_FBO, NEW_FBO)
    fixed_rect = OLD_RECT in src
    src = src.replace(OLD_RECT, NEW_RECT)

    with open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write(src)

    print("Патч применён: Fbo(size=self.size) -> Fbo(size=[50] * 2)")
    if fixed_rect:
        print("Дополнительно исправлен Rectangle в init_fbos.")
    print("Готово! Запустите приложение и проверьте.")


if __name__ == "__main__":
    main()
