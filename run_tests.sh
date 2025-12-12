#!/bin/bash

echo "🧪 Запуск тестов..."

# Создаем необходимые директории
mkdir -p uploads logs

# Запускаем тесты
echo "1. Запуск unit тестов..."
python -m pytest tests/ -v --cov=./ --cov-report=html --cov-report=term

echo "2. Проверка форматирования кода..."
black --check .

echo "3. Проверка сортировки импортов..."
isort --check-only .

echo "4. Линтинг..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

echo "✅ Все проверки завершены!"