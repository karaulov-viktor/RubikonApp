from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen


class DrugDetailScreen(MDScreen):
    """Экран детального описания препарата."""

    # ------------------------------------------------------------------
    # Загрузка данных
    # ------------------------------------------------------------------
    def on_enter(self):
        """Загружаем данные препарата при входе на экран."""
        app = MDApp.get_running_app()
        drug_id = getattr(app, "selected_drug_id", None)
        if not drug_id or not getattr(app, "db", None):
            return

        drug = app.db.get_drug_by_id(drug_id)
        if drug:
            self.show_drug(drug)

        # Каждый раз показываем карточку с начала
        scroll = self.ids.get("detail_scroll")
        if scroll is not None:
            scroll.scroll_y = 1.0

    def show_drug(self, drug):
        """
        Заполняет карточку.
        Запись из БД: (id, name, category, description, instruction,
        image, icon). Разрезаем drug[:7] — будущие доп. поля в конце
        кортежа ничего не сломают.

        Поле description читаем, но НЕ показываем: блок «Описание»
        удалён из kv (id drug_description больше не существует).
        """
        _drug_id, name, category, _description, instruction, image, _icon = drug[:7]

        self.ids.drug_image.source = image or ""
        self.ids.drug_name.text = name or ""
        self.ids.drug_category.text = category or ""
        self.ids.drug_instruction.text = self._clean(instruction)

        # Разметку включаем и программно: экран остаётся совместимым
        # и со старым KV, где у MDLabel не было markup: True
        self.ids.drug_instruction.markup = True

    # ------------------------------------------------------------------
    # Навигация
    # ------------------------------------------------------------------
    def go_back(self):
        """Назад в каталог."""
        MDApp.get_running_app().root.ids.screen_manager.current = "catalog"

    # ------------------------------------------------------------------
    # Служебные методы
    # ------------------------------------------------------------------
    @staticmethod
    def _clean(text):
        """None -> '', CRLF -> LF, [br] -> \n.

        Kivy-разметка ожидает переводы строк \n; тег [br] из HTML
        Kivy не понимает и рисует его как обычный текст.
        """
        if not text:
            return ""
        text = str(text).replace("\r\n", "\n").replace("\r", "\n")
        return text.replace("[br]", "\n")