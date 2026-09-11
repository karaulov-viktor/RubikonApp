-- ОПЦИЯ: перекраска зелёных заголовков (#177300) в инструкциях препаратов
-- под бирюзовый редизайн (#1F7F9C).
-- Затрагивает ТОЛЬКО текст разметки, не данные о дозировках.
-- Выполнять в SQLiteStudio при открытой базе data\rubikon.db.
-- Без BEGIN/COMMIT: SQLiteStudio сам управляет транзакцией
-- (BEGIN внутри скрипта даёт «cannot start a transaction»).
-- Откат (если что): выполни второй REPLACE в обратную сторону
-- (замена '#1F7F9C' на '#177300').

UPDATE drugs
   SET instruction = REPLACE(instruction, '#177300', '#1F7F9C')
 WHERE instruction LIKE '%#177300%';

-- Проверка (должно быть 0):
-- SELECT COUNT(*) FROM drugs WHERE instruction LIKE '%#177300%';
-- Сколько заголовков теперь бирюзовые:
-- SELECT COUNT(*) FROM drugs WHERE instruction LIKE '%#1F7F9C%';
