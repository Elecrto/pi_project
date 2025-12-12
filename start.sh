#!/bin/bash

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

mkdir -p logs
mkdir -p uploads

if [ ! -d "venv" ]; then
    echo "Виртуальное окружение не найдено. Создание..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Установка зависимостей..."
    pip install --upgrade pip
    pip install flask fastapi uvicorn requests torch transformers librosa soundfile
else
    source venv/bin/activate
fi

if [ ! -f "api.py" ] || [ ! -f "app.py" ]; then
    echo "Ошибка: Не найдены файлы api.py или app.py"
    exit 1
fi

# Функция для освобождения порта
free_port() {
    PORT=$1
    echo "Проверка порта $PORT..."
    PID=$(lsof -ti:$PORT)
    if [ ! -z "$PID" ]; then
        echo "Порт $PORT занят процессом $PID. Освобождаем..."
        kill -9 $PID
        sleep 1
        echo "Порт $PORT освобожден"
    else
        echo "Порт $PORT свободен"
    fi
}

# Освобождаем порты
free_port 8000
free_port 5001

echo ""
nohup python3 api.py > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > logs/api.pid
echo "API сервис запущен (PID: $API_PID)"

sleep 3

nohup python3 app.py > logs/app.log 2>&1 &
APP_PID=$!
echo $APP_PID > logs/app.pid
echo "Веб-интерфейс запущен (PID: $APP_PID)"

echo ""
echo "==============================================="
echo "Система успешно запущена!"
echo "==============================================="
echo "Веб-интерфейс: http://localhost:5001"
echo "API: http://localhost:8000"
echo "API документация: http://localhost:8000/docs"
echo ""
echo "Логи:"
echo "  - API: $PROJECT_DIR/logs/api.log"
echo "  - WEB: $PROJECT_DIR/logs/app.log"
echo ""
echo "Для остановки используйте: ./stop.sh"
echo "==============================================="