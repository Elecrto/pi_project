import pytest
import sqlite3
from datetime import datetime
from pathlib import Path


def test_database_initialization(test_db):
    """Тест инициализации базы данных"""
    # Проверяем, что таблицы созданы
    test_db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in test_db.cursor.fetchall()]
    
    assert 'audio_files' in tables
    assert 'users' in tables


def test_add_audio_file(test_db):
    """Тест добавления аудиофайла"""
    audio_id = test_db.add_audio_file(
        filename="test.mp3",
        original_filename="test_original.mp3",
        file_path="/path/to/test.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    assert audio_id is not None
    assert isinstance(audio_id, int)
    
    # Проверяем, что файл добавлен
    audio = test_db.get_audio_file(audio_id)
    assert audio is not None
    assert audio['filename'] == "test.mp3"
    assert audio['status'] == "pending"


def test_update_status(test_db):
    """Тест обновления статуса"""
    # Сначала добавляем файл
    audio_id = test_db.add_audio_file(
        filename="test.mp3",
        original_filename="test.mp3",
        file_path="/path/to/test.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    # Обновляем статус
    test_db.update_status(audio_id, "processing")
    
    audio = test_db.get_audio_file(audio_id)
    assert audio['status'] == "processing"
    
    # Обновляем с транскрипцией
    transcription = "Тестовая транскрипция"
    test_db.update_status(audio_id, "completed", transcription=transcription)
    
    audio = test_db.get_audio_file(audio_id)
    assert audio['status'] == "completed"
    assert audio['transcription'] == transcription
    assert audio['processed_at'] is not None


def test_update_duration(test_db):
    """Тест обновления длительности"""
    audio_id = test_db.add_audio_file(
        filename="test.mp3",
        original_filename="test.mp3",
        file_path="/path/to/test.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    test_db.update_duration(audio_id, 120.5)
    
    audio = test_db.get_audio_file(audio_id)
    assert audio['duration'] == 120.5


def test_toggle_favorite(test_db):
    """Тест переключения избранного"""
    audio_id = test_db.add_audio_file(
        filename="test.mp3",
        original_filename="test.mp3",
        file_path="/path/to/test.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    # Первый вызов - добавляем в избранное
    is_favorite = test_db.toggle_favorite(audio_id)
    assert is_favorite is True
    
    audio = test_db.get_audio_file(audio_id)
    assert audio['is_favorite'] == 1
    
    # Второй вызов - убираем из избранного
    is_favorite = test_db.toggle_favorite(audio_id)
    assert is_favorite is False
    
    audio = test_db.get_audio_file(audio_id)
    assert audio['is_favorite'] == 0


def test_get_all_audio_files(test_db):
    """Тест получения всех аудиофайлов"""
    # Добавляем несколько файлов
    for i in range(3):
        test_db.add_audio_file(
            filename=f"test{i}.mp3",
            original_filename=f"test{i}.mp3",
            file_path=f"/path/to/test{i}.mp3",
            file_size=1024 * i,
            audio_format=".mp3"
        )
    
    files = test_db.get_all_audio_files()
    assert len(files) == 3
    
    files = test_db.get_all_audio_files(limit=2)
    assert len(files) == 2


def test_delete_audio_file(test_db):
    """Тест удаления аудиофайла"""
    audio_id = test_db.add_audio_file(
        filename="test.mp3",
        original_filename="test.mp3",
        file_path="/path/to/test.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    # Убеждаемся, что файл существует
    audio = test_db.get_audio_file(audio_id)
    assert audio is not None
    
    # Удаляем файл
    test_db.delete_audio_file(audio_id)
    
    # Убеждаемся, что файл удален
    audio = test_db.get_audio_file(audio_id)
    assert audio is None


def test_get_total_completed_files(test_db):
    """Тест получения общего количества завершенных файлов"""
    # Добавляем файлы с разными статусами
    for i, status in enumerate(["pending", "processing", "completed", "error"]):
        audio_id = test_db.add_audio_file(
            filename=f"test{i}.mp3",
            original_filename=f"test{i}.mp3",
            file_path=f"/path/to/test{i}.mp3",
            file_size=1024,
            audio_format=".mp3"
        )
        test_db.update_status(audio_id, status)
    
    total_completed = test_db.get_total_completed_files()
    assert total_completed == 1


def test_database_connection_error():
    """Тест ошибки соединения с БД"""
    db = Database()
    db.db_path = "/nonexistent/path/database.db"
    
    # Должно возникнуть исключение при подключении
    with pytest.raises(sqlite3.OperationalError):
        db.init_db()