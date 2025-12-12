import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_fastapi_app_exists():
    """Проверяем что FastAPI приложение создается"""
    try:
        from api import app
        assert app is not None
        assert hasattr(app, 'routes')
        print("✅ FastAPI приложение создано")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания FastAPI приложения: {e}")
        return False

def test_api_endpoints_defined():
    """Проверяем что эндпоинты определены"""
    try:
        from api import app
        
        # Собираем все зарегистрированные маршруты
        routes = []
        for route in app.routes:
            routes.append({
                'path': route.path,
                'methods': getattr(route, 'methods', None),
                'name': getattr(route, 'name', None)
            })
        
        # Проверяем наличие ключевых эндпоинтов
        required_paths = [
            '/health',
            '/upload',
            '/list',
            '/status/{audio_id}',
            '/delete/{audio_id}',
        ]
        
        existing_paths = [route['path'] for route in routes]
        missing_paths = [p for p in required_paths if p not in existing_paths]
        
        if missing_paths:
            print(f"⚠️  Отсутствуют эндпоинты: {missing_paths}")
            print(f"   Существующие: {existing_paths}")
            return False
        
        print(f"✅ Все ключевые эндпоинты определены: {required_paths}")
        return True
    except Exception as e:
        print(f"❌ Ошибка проверки эндпоинтов: {e}")
        return False

def test_config_import():
    """Проверяем что конфигурация импортируется"""
    try:
        import config
        # Проверяем обязательные настройки
        assert hasattr(config, 'API_HOST')
        assert hasattr(config, 'API_PORT')
        assert hasattr(config, 'SUPPORTED_FORMATS')
        print("✅ Конфигурация импортирована корректно")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта конфигурации: {e}")
        return False

def test_models_import():
    """Проверяем что модели импортируются"""
    try:
        from models import Database
        # Пробуем создать подключение к тестовой БД
        import tempfile
        import sqlite3
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Создаем тестовую БД
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                original_filename TEXT,
                file_path TEXT,
                file_size INTEGER,
                format TEXT,
                status TEXT DEFAULT 'pending',
                duration REAL,
                transcription TEXT,
                word_timestamps TEXT,
                summary TEXT,
                error_message TEXT,
                is_favorite INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        
        # Тестируем Database класс
        db = Database(db_path=db_path)
        assert db.conn is not None
        
        # Удаляем тестовую БД
        os.unlink(db_path)
        
        print("✅ Модели импортированы корректно")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта моделей: {e}")
        if 'db_path' in locals() and os.path.exists(db_path):
            os.unlink(db_path)
        return False

def test_audio_converter_import():
    """Проверяем что аудио конвертер импортируется"""
    try:
        from audio_converter import AudioConverter
        converter = AudioConverter()
        assert converter is not None
        print("✅ AudioConverter импортирован корректно")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта AudioConverter: {e}")
        return False

def run_all_tests():
    """Запуск всех минимальных тестов"""
    tests = [
        test_fastapi_app_exists,
        test_api_endpoints_defined,
        test_config_import,
        test_models_import,
        test_audio_converter_import,
    ]
    
    results = []
    print("=" * 60)
    print("Запуск минимальных тестов API")
    print("=" * 60)
    
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"❌ Тест {test.__name__} упал с ошибкой: {e}")
            results.append((test.__name__, False))
    
    # Вывод результатов
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        if result:
            print(f"✅ {name}: ПРОШЕЛ")
            passed += 1
        else:
            print(f"❌ {name}: УПАЛ")
            failed += 1
    
    print("=" * 60)
    print(f"ИТОГО: {passed} пройдено, {failed} упало")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 Все тесты пройдены успешно!")
        return True
    else:
        print("⚠️  Некоторые тесты не пройдены")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)