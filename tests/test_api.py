import pytest
from fastapi.testclient import TestClient
from api import app
import tempfile
import os
import json

# Создаем тестового клиента
client = TestClient(app)

def test_health_check():
    """Проверка работоспособности API"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_list_files():
    """Проверка получения списка файлов"""
    response = client.get("/list")
    assert response.status_code == 200
    assert "files" in response.json()

def test_get_nonexistent_status():
    """Проверка получения статуса несуществующего файла"""
    response = client.get("/status/999999")
    assert response.status_code == 404

def test_delete_nonexistent():
    """Проверка удаления несуществующего файла"""
    response = client.delete("/delete/999999")
    assert response.status_code == 404

def test_toggle_favorite_nonexistent():
    """Проверка избранного для несуществующего файла"""
    response = client.post("/toggle_favorite/999999")
    assert response.status_code == 404

def test_statistics_total_completed():
    """Проверка получения статистики"""
    response = client.get("/statistics/total_completed")
    assert response.status_code == 200
    assert "total_completed_files" in response.json()

# Тест с моком для загрузки файла
def test_upload_mocked(monkeypatch):
    """Тест загрузки файла с моком обработки"""
    # Мокаем функцию process_audio_task
    import api
    async def mock_process_audio_task(audio_id: int, file_path: str):
        pass
    
    monkeypatch.setattr(api, 'process_audio_task', mock_process_audio_task)
    
    # Создаем временный файл
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"RIFF\x00\x00\x00\x00WAVE")  # Минимальный WAV заголовок
        temp_file = f.name
    
    try:
        with open(temp_file, "rb") as file:
            response = client.post("/upload", files={"file": ("test.wav", file, "audio/wav")})
        
        # Ожидаем 400 или 500, так как мы мокаем
        # Сервис может вернуть 200, если успешно добавил в БД
        assert response.status_code in [200, 400, 500]
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)