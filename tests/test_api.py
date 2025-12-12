import pytest
import json
from unittest.mock import Mock, patch
import tempfile
import os


def test_health_check(api_client):
    """Тест health check эндпоинта"""
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_audio(api_client, sample_audio_file, mocker):
    """Тест загрузки аудиофайла"""
    # Мокаем background_tasks
    mocker.patch('api.BackgroundTasks.add_task')
    
    with open(sample_audio_file, 'rb') as f:
        files = {'file': ('test.mp3', f, 'audio/mpeg')}
        response = api_client.post("/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "audio_id" in data


def test_upload_unsupported_format(api_client):
    """Тест загрузки неподдерживаемого формата"""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'not an audio file')
        f.flush()
        
        with open(f.name, 'rb') as file:
            files = {'file': ('test.txt', file, 'text/plain')}
            response = api_client.post("/upload", files=files)
    
    os.unlink(f.name)
    assert response.status_code == 400
    assert "Неподдерживаемый формат" in response.json()["detail"]


def test_get_status(api_client, test_db):
    """Тест получения статуса"""
    # Сначала добавляем файл
    audio_id = test_db.add_audio_file(
        filename="test.mp3",
        original_filename="test.mp3",
        file_path="/path/to/test.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    response = api_client.get(f"/status/{audio_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["audio_id"] == audio_id
    assert data["status"] == "pending"


def test_get_status_not_found(api_client):
    """Тест получения статуса несуществующего файла"""
    response = api_client.get("/status/999999")
    assert response.status_code == 404


def test_list_audio_files(api_client, test_db):
    """Тест получения списка файлов"""
    # Добавляем несколько файлов
    for i in range(3):
        test_db.add_audio_file(
            filename=f"test{i}.mp3",
            original_filename=f"test{i}.mp3",
            file_path=f"/path/to/test{i}.mp3",
            file_size=1024,
            audio_format=".mp3"
        )
    
    response = api_client.get("/list")
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 3


def test_list_audio_files_with_limit(api_client, test_db):
    """Тест получения списка файлов с лимитом"""
    # Добавляем несколько файлов
    for i in range(5):
        test_db.add_audio_file(
            filename=f"test{i}.mp3",
            original_filename=f"test{i}.mp3",
            file_path=f"/path/to/test{i}.mp3",
            file_size=1024,
            audio_format=".mp3"
        )
    
    response = api_client.get("/list?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 2


def test_delete_audio(api_client, test_db, mocker):
    """Тест удаления аудиофайла"""
    # Мокаем удаление файла
    mocker.patch('pathlib.Path.unlink')
    
    # Добавляем файл
    audio_id = test_db.add_audio_file(
        filename="test.mp3",
        original_filename="test.mp3",
        file_path="/path/to/test.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    response = api_client.delete(f"/delete/{audio_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Проверяем, что файл удален из БД
    audio = test_db.get_audio_file(audio_id)
    assert audio is None


def test_delete_audio_not_found(api_client):
    """Тест удаления несуществующего файла"""
    response = api_client.delete("/delete/999999")
    assert response.status_code == 404


def test_toggle_favorite(api_client, test_db):
    """Тест переключения избранного"""
    # Добавляем файл
    audio_id = test_db.add_audio_file(
        filename="test.mp3",
        original_filename="test.mp3",
        file_path="/path/to/test.mp3",
        file_size=1024,
        audio_format=".mp3"
    )
    
    response = api_client.post(f"/toggle_favorite/{audio_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["is_favorite"] is True
    
    # Проверяем, что статус сохранился
    audio = test_db.get_audio_file(audio_id)
    assert audio["is_favorite"] == 1


def test_get_total_completed(api_client, test_db):
    """Тест получения общего количества завершенных файлов"""
    # Добавляем и завершаем несколько файлов
    for i in range(3):
        audio_id = test_db.add_audio_file(
            filename=f"test{i}.mp3",
            original_filename=f"test{i}.mp3",
            file_path=f"/path/to/test{i}.mp3",
            file_size=1024,
            audio_format=".mp3"
        )
        if i < 2:  # Два файла завершены
            test_db.update_status(audio_id, "completed")
    
    response = api_client.get("/statistics/total_completed")
    assert response.status_code == 200
    data = response.json()
    assert data["total_completed_files"] == 2


def test_format_datetime():
    """Тест форматирования даты-времени"""
    from api import format_datetime
    
    # Тест с миллисекундами
    dt_string = "2023-11-22 21:29:01.376"
    result = format_datetime(dt_string)
    assert result == "2023-11-22 21:29:01"
    
    # Тест без миллисекунд
    dt_string = "2023-11-22 21:29:01"
    result = format_datetime(dt_string)
    assert result == "2023-11-22 21:29:01"
    
    # Тест с некорректной датой
    dt_string = "invalid date"
    result = format_datetime(dt_string)
    assert result == "invalid date"
    
    # Тест с None
    result = format_datetime(None)
    assert result is None


def test_post_process_transcription():
    """Тест постобработки транскрипции"""
    from api import post_process_transcription
    
    # Тест с лишними пробелами
    text = "Это   тест    с   лишними   пробелами"
    result = post_process_transcription(text)
    assert result == "Это тест с лишними пробелами."
    
    # Тест с повторяющимися словами
    text = "Это это тест с повторяющимися повторяющимися словами"
    result = post_process_transcription(text)
    assert "Это тест с повторяющимися словами." in result
    
    # Тест с пробелами перед знаками препинания
    text = "Это тест , с неправильными . знаками препинания !"
    result = post_process_transcription(text)
    assert result == "Это тест, с неправильными. знаками препинания!"
    
    # Тест с артефактами
    text = "Это тест с [музыка] артефактами (неразборчиво) в тексте"
    result = post_process_transcription(text)
    assert "[музыка]" not in result
    assert "(неразборчиво)" not in result
    
    # Тест с пустым текстом
    result = post_process_transcription("")
    assert result == ""
    
    # Тест с None
    result = post_process_transcription(None)
    assert result is None


@patch('api.summary_model')
def test_generate_summary_local(mock_summary_model, mocker):
    """Тест генерации краткого содержания через локальную модель"""
    from api import generate_summary_local
    
    # Мокаем модель
    mock_model = Mock()
    mock_model.return_value = {
        "choices": [{"text": "Это тестовое краткое содержание на русском языке."}]
    }
    mock_summary_model.__bool__.return_value = True
    mock_summary_model.return_value = mock_model
    
    text = "Это длинный текст для тестирования генерации краткого содержания. " * 10
    result = generate_summary_local(text)
    
    assert result is not None
    assert "тестовое краткое содержание" in result


def test_generate_summary_ollama(mocker):
    """Тест генерации краткого содержания через Ollama"""
    from api import generate_summary_ollama
    
    # Мокаем requests.post
    mock_post = mocker.patch('requests.post')
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "Это тестовое краткое содержание через Ollama"
    }
    mock_post.return_value = mock_response
    
    text = "Это длинный текст для тестирования. " * 10
    result = generate_summary_ollama(text)
    
    assert result is not None
    assert "тестовое краткое содержание" in result
    mock_post.assert_called_once()


def test_generate_summary_ollama_error(mocker):
    """Тест ошибки при генерации через Ollama"""
    from api import generate_summary_ollama
    
    # Мокаем ошибку соединения
    mocker.patch('requests.post', side_effect=ConnectionError("Connection failed"))
    
    text = "Тестовый текст"
    result = generate_summary_ollama(text)
    
    assert result is None


def test_generate_summary_short_text():
    """Тест генерации краткого содержания для короткого текста"""
    from api import generate_summary
    
    text = "Короткий текст"
    result = generate_summary(text)
    
    assert result is None