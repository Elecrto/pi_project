#!/usr/bin/env python3
"""
Скрипт для обновления длительности аудиофайлов в БД
"""
import logging
from pathlib import Path
from models import Database
from audio_converter import AudioConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    db = Database()
    audio_converter = AudioConverter()

    # Получаем все файлы
    files = db.get_all_audio_files(limit=1000)

    updated_count = 0
    skipped_count = 0

    for file in files:
        file_id = file['id']
        file_path = file['file_path']
        current_duration = file.get('duration')

        # Если duration уже установлена, пропускаем
        if current_duration is not None and current_duration > 0:
            logger.info(f"ID={file_id}: duration уже установлена ({current_duration:.2f}с), пропускаем")
            skipped_count += 1
            continue

        # Проверяем, существует ли файл
        if not Path(file_path).exists():
            logger.warning(f"ID={file_id}: файл не найден: {file_path}")
            skipped_count += 1
            continue

        try:
            # Получаем информацию о файле
            info = audio_converter.get_audio_info(file_path)
            duration = info['duration']

            # Обновляем duration в БД
            db.update_duration(file_id, duration)

            logger.info(f"ID={file_id}: обновлена duration = {duration:.2f}с")
            updated_count += 1

        except Exception as e:
            logger.error(f"ID={file_id}: ошибка при обработке: {e}")
            skipped_count += 1

    logger.info(f"\nГотово! Обновлено: {updated_count}, Пропущено: {skipped_count}")

if __name__ == "__main__":
    main()
