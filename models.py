import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Dict
import time
import config

class Database:
    """Класс для работы с базой данных аудиофайлов"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self.init_db()

    @staticmethod
    def get_moscow_time():
        """Возвращает текущее московское время (UTC+3)"""
        moscow_tz = timezone(timedelta(hours=3))
        return datetime.now(moscow_tz).replace(tzinfo=None)

    def get_connection(self):
        """Создает подключение к БД"""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Включаем WAL режим для параллельных чтений и записи
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def execute_with_retry(self, operation, max_retries=3):
        """
        Выполняет операцию с базой данных с повторными попытками при блокировке

        Args:
            operation: Функция для выполнения
            max_retries: Максимальное количество повторных попыток

        Returns:
            Результат выполнения операции
        """
        for attempt in range(max_retries):
            try:
                return operation()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Экспоненциальная задержка
                    continue
                raise

    def init_db(self):
        """Инициализирует базу данных"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                duration REAL,
                format TEXT,
                status TEXT DEFAULT 'uploaded',
                transcription TEXT,
                created_at TIMESTAMP,
                processed_at TIMESTAMP,
                error_message TEXT,
                is_favorite INTEGER DEFAULT 0
            )
        """)

        # Добавляем поле is_favorite если его еще нет (миграция)
        try:
            cursor.execute("ALTER TABLE audio_files ADD COLUMN is_favorite INTEGER DEFAULT 0")
        except:
            pass  # Поле уже существует

        # Добавляем поле word_timestamps если его еще нет (миграция)
        try:
            cursor.execute("ALTER TABLE audio_files ADD COLUMN word_timestamps TEXT")
        except:
            pass  # Поле уже существует

        # Добавляем поле summary если его еще нет (миграция)
        try:
            cursor.execute("ALTER TABLE audio_files ADD COLUMN summary TEXT")
        except:
            pass  # Поле уже существует

        # Создаем таблицу для статистики
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_completed_files INTEGER DEFAULT 0
            )
        """)

        # Инициализируем статистику если ее нет
        cursor.execute("SELECT COUNT(*) FROM statistics WHERE id = 1")
        exists = cursor.fetchone()[0]

        if not exists:
            # Считаем количество существующих файлов со статусом completed
            cursor.execute("SELECT COUNT(*) FROM audio_files WHERE status = 'completed'")
            existing_completed = cursor.fetchone()[0]

            # Инициализируем счетчик
            cursor.execute("INSERT INTO statistics (id, total_completed_files) VALUES (1, ?)", (existing_completed,))

        conn.commit()
        conn.close()

    def add_audio_file(self, filename: str, original_filename: str,
                      file_path: str, file_size: int,
                      audio_format: str, duration: float = None) -> int:
        """Добавляет новый аудиофайл в БД"""
        def operation():
            conn = self.get_connection()
            cursor = conn.cursor()

            moscow_time = self.get_moscow_time()

            cursor.execute("""
                INSERT INTO audio_files
                (filename, original_filename, file_path, file_size, format, duration, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'uploaded', ?)
            """, (filename, original_filename, file_path, file_size, audio_format, duration, moscow_time))

            audio_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return audio_id

        return self.execute_with_retry(operation, max_retries=5)

    def update_status(self, audio_id: int, status: str,
                     transcription: str = None, error_message: str = None,
                     word_timestamps: str = None, summary: str = None):
        """Обновляет статус обработки аудиофайла"""
        def operation():
            conn = self.get_connection()
            cursor = conn.cursor()

            # Проверяем предыдущий статус
            cursor.execute("SELECT status FROM audio_files WHERE id = ?", (audio_id,))
            row = cursor.fetchone()
            previous_status = row[0] if row else None

            if status == 'completed':
                moscow_time = self.get_moscow_time()
                cursor.execute("""
                    UPDATE audio_files
                    SET status = ?, transcription = ?, word_timestamps = ?, summary = ?, processed_at = ?
                    WHERE id = ?
                """, (status, transcription, word_timestamps, summary, moscow_time, audio_id))

                # Если это первый раз переход в статус completed, инкрементируем счетчик
                if previous_status != 'completed':
                    cursor.execute("""
                        UPDATE statistics
                        SET total_completed_files = total_completed_files + 1
                        WHERE id = 1
                    """)
            elif status == 'error':
                cursor.execute("""
                    UPDATE audio_files
                    SET status = ?, error_message = ?
                    WHERE id = ?
                """, (status, error_message, audio_id))
            else:
                cursor.execute("""
                    UPDATE audio_files
                    SET status = ?
                    WHERE id = ?
                """, (status, audio_id))

            conn.commit()
            conn.close()

        self.execute_with_retry(operation, max_retries=5)  # Больше попыток для операций записи

    def get_audio_file(self, audio_id: int) -> Optional[Dict]:
        """Получает информацию об аудиофайле по ID"""
        def operation():
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audio_files WHERE id = ?", (audio_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

        return self.execute_with_retry(operation)

    def get_all_audio_files(self, limit: int = 100) -> List[Dict]:
        """Получает список всех аудиофайлов"""
        def operation():
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audio_files
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

        return self.execute_with_retry(operation)

    def delete_audio_file(self, audio_id: int) -> bool:
        """Удаляет аудиофайл из БД"""
        def operation():
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audio_files WHERE id = ?", (audio_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted

        return self.execute_with_retry(operation, max_retries=5)

    def toggle_favorite(self, audio_id: int) -> bool:
        """Переключает статус избранного для файла"""
        def operation():
            conn = self.get_connection()
            cursor = conn.cursor()

            # Получаем текущее значение
            cursor.execute("SELECT is_favorite FROM audio_files WHERE id = ?", (audio_id,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                return False

            current_favorite = row[0]
            new_favorite = 0 if current_favorite else 1

            cursor.execute("UPDATE audio_files SET is_favorite = ? WHERE id = ?", (new_favorite, audio_id))
            conn.commit()
            conn.close()

            return bool(new_favorite)

        return self.execute_with_retry(operation)

    def get_total_completed_files(self) -> int:
        """Получает общее количество когда-либо завершенных файлов"""
        def operation():
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT total_completed_files FROM statistics WHERE id = 1")
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else 0

        return self.execute_with_retry(operation)

    def update_duration(self, audio_id: int, duration: float):
        """Обновляет длительность аудиофайла"""
        def operation():
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE audio_files
                SET duration = ?
                WHERE id = ?
            """, (duration, audio_id))
            conn.commit()
            conn.close()

        self.execute_with_retry(operation, max_retries=5)
