import pytest
import json
from unittest.mock import Mock, patch
import io


def test_index(flask_client):
    """Тест главной страницы"""
    response = flask_client.get("/")
    assert response.status_code == 302  # Перенаправление на /main


def test_main_page(flask_client, mocker):
    """Тест страницы со списком файлов"""
    # Мокаем запрос к API
    mock_get = mocker.patch('requests.get')
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"files": [
        {"id": 1, "filename": "test.mp3", "status": "completed"}
    ]}
    mock_get.return_value = mock_response
    
    response = flask_client.get("/main")
    assert response.status_code == 200
    assert b"test.mp3" in response.data


def test_search_page(flask_client, mocker):
    """Тест страницы поиска"""
    # Мокаем запрос к API
    mock_get = mocker.patch('requests.get')
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"files": [
        {"id": 1, "filename": "test.mp3", "status": "completed", "transcription": "искомый текст"}
    ]}
    mock_get.return_value = mock_response
    
    response = flask_client.get("/search?q=искомый")
    assert response.status_code == 200
    assert "искомый" in response.data


def test_statistics_page(flask_client, mocker):
    """Тест страницы статистики"""
    # Мокаем запросы к API
    mock_get = mocker.patch('requests.get')
    
    # Первый запрос - список файлов
    mock_response1 = Mock()
    mock_response1.status_code = 200
    mock_response1.json.return_value = {"files": [
        {"id": 1, "filename": "test.mp3", "status": "completed", "duration": 60, "file_size": 1024}
    ]}
    
    # Второй запрос - статистика
    mock_response2 = Mock()
    mock_response2.status_code = 200
    mock_response2.json.return_value = {"total_completed_files": 1}
    
    mock_get.side_effect = [mock_response1, mock_response2]
    
    response = flask_client.get("/statistics")
    assert response.status_code == 200
    assert "Статистика" in response.data
    assert b"1" in response.data  # Проверяем, что отображается количество файлов


def test_favorites_page(flask_client, mocker):
    """Тест страницы избранного"""
    # Мокаем запрос к API
    mock_get = mocker.patch('requests.get')
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"files": [
        {"id": 1, "filename": "test.mp3", "status": "completed", "is_favorite": True}
    ]}
    mock_get.return_value = mock_response
    
    response = flask_client.get("/favorites")
    assert response.status_code == 200
    assert b"test.mp3" in response.data


def test_upload_file(flask_client, mocker):
    """Тест загрузки файла"""
    # Мокаем запрос к API
    mock_post = mocker.patch('requests.post')
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_post.return_value = mock_response
    
    # Создаем тестовый файл
    data = {
        'file': (io.BytesIO(b'test audio content'), 'test.mp3')
    }
    
    response = flask_client.post("/upload", data=data, content_type='multipart/form-data')
    assert response.status_code == 302  # Перенаправление
    mock_post.assert_called_once()


def test_upload_no_file(flask_client):
    """Тест загрузки без файла"""
    response = flask_client.post("/upload")
    assert response.status_code == 302  # Перенаправление с ошибкой


def test_toggle_favorite(flask_client, mocker):
    """Тест переключения избранного через Flask"""
    # Мокаем запрос к API
    mock_post = mocker.patch('requests.post')
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "is_favorite": True}
    mock_post.return_value = mock_response
    
    response = flask_client.post("/toggle_favorite/1")
    assert response.status_code == 302  # Перенаправление
    mock_post.assert_called_once()


def test_audio_detail(flask_client, mocker):
    """Тест детальной страницы аудио"""
    # Мокаем запрос к API
    mock_get = mocker.patch('requests.get')
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 1,
        "filename": "test.mp3",
        "status": "completed",
        "transcription": "Тестовая транскрипция",
        "summary": "Тестовое краткое содержание"
    }
    mock_get.return_value = mock_response
    
    response = flask_client.get("/audio/1")
    assert response.status_code == 200
    assert "Тестовая транскрипция" in response.data
    assert "Тестовое краткое содержание" in response.data


def test_audio_detail_not_found(flask_client, mocker):
    """Тест детальной страницы несуществующего аудио"""
    # Мокаем ошибку 404
    mock_get = mocker.patch('requests.get')
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    
    response = flask_client.get("/audio/999")
    assert response.status_code == 302  # Перенаправление на главную


def test_delete_audio(flask_client, mocker):
    """Тест удаления аудио"""
    # Мокаем запрос к API
    mock_delete = mocker.patch('requests.delete')
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_delete.return_value = mock_response
    
    response = flask_client.post("/delete/1")
    assert response.status_code == 302  # Перенаправление
    mock_delete.assert_called_once()


def test_refresh_status(flask_client, mocker):
    """Тест обновления статуса через AJAX"""
    # Мокаем запрос к API
    mock_get = mocker.patch('requests.get')
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "processing"}
    mock_get.return_value = mock_response
    
    response = flask_client.get("/refresh_status/1")
    assert response.status_code == 200
    assert response.json["status"] == "processing"


def test_error_handlers(flask_client):
    """Тест обработчиков ошибок"""
    # Тест 404
    response = flask_client.get("/nonexistent")
    assert response.status_code == 404
    
    # Тест 500 (имитируем ошибку)
    with patch('app.requests.get', side_effect=Exception("Test error")):
        response = flask_client.get("/main")
        assert response.status_code == 302  # Перенаправление с ошибкой


def test_get_audio_file(flask_client, test_db, mocker):
    """Тест получения аудиофайла для проигрывания"""
    # Добавляем файл в БД
    audio_id = test_db.add_audio_file(
        filename="test.mp3",
        original_filename="test.mp3",
        file_path="/tmp/test.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    # Создаем временный файл
    with open("/tmp/test.mp3", "wb") as f:
        f.write(b"fake audio content")
    
    try:
        # Мокаем send_file
        mock_send_file = mocker.patch('app.send_file')
        mock_send_file.return_value = "audio content"
        
        response = flask_client.get(f"/get_audio/{audio_id}")
        
        # В этом тесте мы проверяем, что функция вызывается правильно
        # Фактический ответ будет от mock_send_file
        mock_send_file.assert_called_once_with("/tmp/test.mp3", mimetype="audio/mpeg")
    finally:
        import os
        if os.path.exists("/tmp/test.mp3"):
            os.unlink("/tmp/test.mp3")


def test_get_audio_file_not_found(flask_client, test_db):
    """Тест получения несуществующего аудиофайла"""
    response = flask_client.get("/get_audio/999999")
    assert response.status_code == 404


def test_get_audio_file_missing_file(flask_client, test_db):
    """Тест получения аудиофайла, которого нет на диске"""
    audio_id = test_db.add_audio_file(
        filename="missing.mp3",
        original_filename="missing.mp3",
        file_path="/tmp/nonexistent.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    response = flask_client.get(f"/get_audio/{audio_id}")
    assert response.status_code == 404