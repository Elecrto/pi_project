.PHONY: test lint format clean

# Тесты
test:
	python -m pytest tests/ -v --cov=./ --cov-report=html

test-fast:
	python -m pytest tests/ -v

# Линтинг
lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Форматирование
format:
	black .
	isort .

# Проверка форматирования
check-format:
	black --check .
	isort --check-only .

# Очистка
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +

# Запуск всех проверок
all: test check-format lint