-- Rubikon: переключение фото препаратов с .jpg на прозрачные .png
-- Выполнять в SQLiteStudio при открытой базе I:\Rubikon_vet\data\rubikon.db

BEGIN;

UPDATE drugs
   SET image = REPLACE(image, '.jpg', '.png')
 WHERE image LIKE '%.jpg';

COMMIT;

-- ПРОВЕРКА: должно вывести 0
SELECT COUNT(*) AS ostalos_jpg FROM drugs WHERE image LIKE '%.jpg';
-- и 61, если каталог полностью из нового пакета:
-- SELECT COUNT(*) FROM drugs WHERE image LIKE '%.png';
