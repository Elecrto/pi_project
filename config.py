import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Определение окружения
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Базовые пути (всегда относительные от корня проекта)
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads")
LOGS_FOLDER = BASE_DIR / os.getenv("LOGS_FOLDER", "logs")
STATIC_FOLDER = BASE_DIR / os.getenv("STATIC_FOLDER", "static")
AUDIO_FOLDER = BASE_DIR / os.getenv("AUDIO_FOLDER", "audio")

# База данных (SQLite относительный путь)
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "audio_processing.db")

# Создание необходимых директорий
UPLOAD_FOLDER.mkdir(exist_ok=True)
LOGS_FOLDER.mkdir(exist_ok=True)
AUDIO_FOLDER.mkdir(exist_ok=True)

# Настройки Flask
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "your-secret-key-change-in-production")
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5001"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true" and not IS_PRODUCTION

# Настройки FastAPI
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Настройки модели Whisper (относительный путь или название модели)
_whisper_model_path = os.getenv("WHISPER_MODEL_PATH", "finetuned_whisper")
# Проверяем, существует ли путь к модели локально
if not Path(_whisper_model_path).is_absolute():
    model_full_path = BASE_DIR / _whisper_model_path
    if model_full_path.exists():
        _whisper_model_path = str(model_full_path)
WHISPER_MODEL_PATH = _whisper_model_path

DEVICE = os.getenv("DEVICE", "cpu")  # Или "cuda" если есть GPU

# Настройки модели для суммаризации (локальная GGUF модель)
LOCAL_MODELS_FOLDER = BASE_DIR / "local_models"
LOCAL_MODELS_FOLDER.mkdir(exist_ok=True)
SUMMARY_MODEL_PATH = LOCAL_MODELS_FOLDER / "deepseek-r1-8b.gguf"
USE_LOCAL_SUMMARY_MODEL = SUMMARY_MODEL_PATH.exists()  # Автоопределение использования локальной модели

# Настройки аудио
SUPPORTED_FORMATS = [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma", ".aac"]
TARGET_SAMPLE_RATE = 16000  # Whisper работает с 16kHz
CHUNK_LENGTH_SECONDS = 30  # Обработка по чанкам для длинных аудио (оптимально для 50+ минут)

# Логирование
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Учетные данные (используйте переменные окружения!)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

USERS = {
    ADMIN_USERNAME: ADMIN_PASSWORD
}

# Вывод конфигурации при запуске (для отладки)
if __name__ == "__main__":
    print(f"=== Конфигурация ({ENVIRONMENT}) ===")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"DB_PATH: {DB_PATH}")
    print(f"UPLOAD_FOLDER: {UPLOAD_FOLDER}")
    print(f"WHISPER_MODEL_PATH: {WHISPER_MODEL_PATH}")
    print(f"FLASK: {FLASK_HOST}:{FLASK_PORT}")
    print(f"API: {API_HOST}:{API_PORT}")
