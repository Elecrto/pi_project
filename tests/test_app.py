import pytest
from app import app as flask_app
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.test_client() as client:
        yield client

def test_index_redirect(client):
    """Проверка редиректа с главной страницы"""
    response = client.get("/")
    assert response.status_code == 302  # Редирект на /main
    assert "/main" in response.location

def test_main_page(client):
    """Проверка доступности главной страницы"""
    with patch('app.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"files": []}
        mock_get.return_value = mock_response
        
        response = client.get("/main")
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.data

def test_search_page(client):
    """Проверка страницы поиска"""
    with patch('app.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"files": []}
        mock_get.return_value = mock_response
        
        response = client.get("/search?q=test")
        assert response.status_code == 200

def test_statistics_page(client):
    """Проверка страницы статистики"""
    with patch('app.requests.get') as mock_get:
        # Мок для списка файлов
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {"files": []}
        
        # Мок для статистики
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"total_completed_files": 0}
        
        mock_get.side_effect = [mock_response1, mock_response2]
        
        response = client.get("/statistics")
        assert response.status_code == 200

def test_favorites_page(client):
    """Проверка страницы избранного"""
    with patch('app.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"files": []}
        mock_get.return_value = mock_response
        
        response = client.get("/favorites")
        assert response.status_code == 200

def test_audio_detail_page(client):
    """Проверка детальной страницы аудио"""
    with patch('app.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "status": "completed",
            "filename": "test.wav",
            "transcription": "Тестовая транскрипция"
        }
        mock_get.return_value = mock_response
        
        response = client.get("/audio/1")
        assert response.status_code == 200

def test_audio_detail_not_found(client):
    """Проверка несуществующей детальной страницы"""
    with patch('app.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        response = client.get("/audio/999")
        assert response.status_code == 302  # Редирект с flash сообщением

def test_refresh_status_endpoint(client):
    """Проверка AJAX эндпоинта для обновления статуса"""
    with patch('app.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "completed"}
        mock_get.return_value = mock_response
        
        response = client.get("/refresh_status/1")
        assert response.status_code == 200
        assert response.is_json
        assert response.json["status"] == "completed"