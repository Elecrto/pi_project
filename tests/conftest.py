import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from flask.testing import FlaskClient
import sys

# Добавляем корневую директорию в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api import app as fastapi_app
from app import app as flask_app
from models import Database


@pytest.fixture
def temp_db_path():
    """Создает временный файл базы данных для тестов"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_db(temp_db_path):
    """Создает тестовую базу данных"""
    # Меняем путь к БД в конфигурации
    import config
    original_db_path = config.DATABASE_PATH
    config.DATABASE_PATH = Path(temp_db_path)
    
    # Создаем новую БД
    db = Database()
    db.init_db()
    
    yield db
    
    # Восстанавливаем оригинальный путь
    config.DATABASE_PATH = original_db_path


@pytest.fixture
def api_client(test_db):
    """Создает тестовый клиент для FastAPI"""
    from api import db as api_db
    
    # Подменяем базу данных в API
    original_db = api_db
    api_db.conn = test_db.conn
    api_db.cursor = test_db.cursor
    
    with TestClient(fastapi_app) as client:
        yield client
    
    # Восстанавливаем оригинальную БД
    api_db.conn = original_db.conn
    api_db.cursor = original_db.cursor


@pytest.fixture
def flask_client(test_db):
    """Создает тестовый клиент для Flask"""
    from app import db as flask_db
    
    # Подменяем базу данных в Flask
    original_db = flask_db
    flask_db.conn = test_db.conn
    flask_db.cursor = test_db.cursor
    
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client
    
    # Восстанавливаем оригинальную БД
    flask_db.conn = original_db.conn
    flask_db.cursor = original_db.cursor


@pytest.fixture
def sample_audio_file():
    """Создает тестовый аудиофайл"""
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        # Создаем минимальный валидный MP3 файл
        f.write(b'\xFF\xFB\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_wav_file():
    """Создает тестовый WAV файл"""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # Минимальный WAV заголовок
        wav_header = (
            b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
            b'\x80\xbb\x00\x00\x00\x77\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        )
        f.write(wav_header)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def mock_whisper_model(mocker):
    """Мокает модель Whisper для тестов"""
    mock_model = mocker.MagicMock()
    mock_processor = mocker.MagicMock()
    
    mocker.patch('api.whisper_model', mock_model)
    mocker.patch('api.whisper_processor', mock_processor)
    mocker.patch('api.whisper_device', 'cpu')
    
    return mock_model, mock_processor


@pytest.fixture
def mock_ollama(mocker):
    """Мокает Ollama API"""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "Тестовое краткое содержание"
    }
    
    mock_post = mocker.patch('requests.post', return_value=mock_response)
    return mock_post


@pytest.fixture(autouse=True)
def cleanup():
    """Очистка после каждого теста"""
    yield
    # Очищаем временные файлы
    import glob
    temp_files = glob.glob('/tmp/test_*.mp3') + glob.glob('/tmp/test_*.wav')
    for f in temp_files:
        try:
            os.unlink(f)
        except:
            pass