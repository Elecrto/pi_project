import pytest
import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def setup_test_env():
    """Настройка тестового окружения"""
    # Можно установить тестовые переменные окружения
    original_log_level = os.environ.get("LOG_LEVEL", "INFO")
    os.environ["LOG_LEVEL"] = "ERROR"  # Уменьшаем логирование для тестов
    yield
    # Восстанавливаем оригинальные настройки
    os.environ["LOG_LEVEL"] = original_log_level