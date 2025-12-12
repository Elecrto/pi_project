import pytest
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(autouse=True)
def setup_test_env():
    """Настройка тестового окружения"""
    # Устанавливаем тестовые переменные окружения
    original_env = {}
    
    # Сохраняем оригинальные значения
    env_vars = [
        "LOG_LEVEL", "API_HOST", "API_PORT", 
        "FLASK_HOST", "FLASK_PORT", "UPLOAD_FOLDER"
    ]
    
    for var in env_vars:
        original_env[var] = os.environ.get(var)
    
    # Устанавливаем тестовые значения
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ["API_HOST"] = "localhost"
    os.environ["API_PORT"] = "8000"
    os.environ["FLASK_HOST"] = "localhost"
    os.environ["FLASK_PORT"] = "5000"
    os.environ["UPLOAD_FOLDER"] = str(project_root / "test_uploads")
    
    # Создаем тестовые директории
    test_dirs = ["test_uploads", "test_logs"]
    for dir_name in test_dirs:
        dir_path = project_root / dir_name
        dir_path.mkdir(exist_ok=True)
    
    yield
    
    # Восстанавливаем оригинальные настройки
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value
        else:
            os.environ.pop(var, None)
    
    # Удаляем тестовые директории
    for dir_name in test_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            # Удаляем файлы в директории
            for file in dir_path.iterdir():
                if file.is_file():
                    file.unlink()
            dir_path.rmdir()

@pytest.fixture
def temp_audio_file():
    """Создает временный аудиофайл для тестов"""
    import tempfile
    import wave
    import struct
    
    # Создаем временный WAV файл
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # Создаем простой WAV файл (1 секунда тишины)
        nchannels = 1
        sampwidth = 2
        framerate = 44100
        nframes = framerate
        
        with wave.open(f.name, 'wb') as wav_file:
            wav_file.setnchannels(nchannels)
            wav_file.setsampwidth(sampwidth)
            wav_file.setframerate(framerate)
            
            # Записываем тишину (нулевые значения)
            silent_data = struct.pack('h' * nframes, *([0] * nframes))
            wav_file.writeframes(silent_data)
        
        yield f.name
    
    # Удаляем временный файл
    if os.path.exists(f.name):
        os.unlink(f.name)