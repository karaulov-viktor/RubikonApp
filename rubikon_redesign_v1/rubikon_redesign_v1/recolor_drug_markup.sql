-- ОПЦИЯ: перекраска зелёных заголовков (#177300) в инструкциях препаратов
-- под бирюзовый редизайн (#1F7F9C).
-- Затрагивает ТОЛЬКО текст разметки, не данные о дозировках.
-- Выполнять в SQLiteStudio при открытой базе data\rubikon.db.
-- Откат (если что): замените '#1F7F9C' обратно на '#177300'.

BEGIN;

UPDATE drugs
   SET instruction = REPLACE(instruction, '#177300', '#1F7F9C')
 WHERE instruction LIKE '%#177300%';

COMMIT;

-- Сколько строк перекрасилось / осталось:
-- SELECT COUNT(*) FROM drugs WHERE instruction LIKE '%#1F7F9C%';
