import pytest
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_index_redirect(client):
    """Проверка редиректа с главной страницы"""
    response = client.get("/")
    assert response.status_code == 302  # Редирект на /main

def test_main_page(client):
    """Проверка доступности главной страницы"""
    response = client.get("/main")
    assert response.status_code == 200
    assert "Аудиофайлы" in response.data or b"audio" in response.data.lower()

def test_search_page(client):
    """Проверка страницы поиска"""
    response = client.get("/search?q=test")
    assert response.status_code == 200

def test_statistics_page(client):
    """Проверка страницы статистики"""
    response = client.get("/statistics")
    assert response.status_code == 200

def test_favorites_page(client):
    """Проверка страницы избранного"""
    response = client.get("/favorites")
    assert response.status_code == 200

def test_upload_without_file(client):
    """Проверка загрузки без файла"""
    response = client.post("/upload", data={})
    assert response.status_code == 302  # Редирект с флеш-сообщением

def test_audio_detail_nonexistent(client):
    """Проверка детальной страницы несуществующего файла"""
    response = client.get("/audio/999999")
    assert response.status_code == 302  # Редирект с флеш-сообщением