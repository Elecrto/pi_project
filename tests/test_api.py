import pytest
from fastapi.testclient import TestClient
from api import app
import tempfile
import os

client = TestClient(app)

def test_health_check():
    """Проверка работоспособности API"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_list_files():
    """Проверка получения списка файлов"""
    response = client.get("/list?limit=10")
    assert response.status_code == 200
    assert "files" in response.json()

def test_upload_invalid_format():
    """Проверка загрузки неподдерживаемого формата"""
    # Создаем временный файл с неподдерживаемым форматом
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Test content")
        temp_file = f.name
    
    try:
        with open(temp_file, "rb") as file:
            response = client.post("/upload", files={"file": ("test.txt", file, "text/plain")})
        assert response.status_code == 400
        assert "Неподдерживаемый формат" in response.json()["detail"]
    finally:
        os.unlink(temp_file)

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