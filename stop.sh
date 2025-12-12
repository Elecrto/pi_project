#!/bin/bash

echo "Остановка системы транскрибации аудио..."

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

if [ -f "logs/api.pid" ]; then
    API_PID=$(cat logs/api.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        echo "Остановка API сервиса (PID: $API_PID)..."
        kill $API_PID
        sleep 2
        if ps -p $API_PID > /dev/null 2>&1; then
            echo "Принудительная остановка API сервиса..."
            kill -9 $API_PID
        fi
        echo "API сервис остановлен"
    else
        echo "API сервис не запущен"
    fi
    rm -f logs/api.pid
else
    echo "Файл logs/api.pid не найден, пытаемся найти процесс..."
    pkill -f "python3 api.py" && echo "API сервис остановлен" || echo "API сервис не найден"
fi

if [ -f "logs/app.pid" ]; then
    APP_PID=$(cat logs/app.pid)
    if ps -p $APP_PID > /dev/null 2>&1; then
        echo "Остановка веб-интерфейса (PID: $APP_PID)..."
        kill $APP_PID
        sleep 2
        if ps -p $APP_PID > /dev/null 2>&1; then
            echo "Принудительная остановка веб-интерфейса..."
            kill -9 $APP_PID
        fi
        echo "Веб-интерфейс остановлен"
    else
        echo "Веб-интерфейс не запущен"
    fi
    rm -f logs/app.pid
else
    echo "Файл logs/app.pid не найден, пытаемся найти процесс..."
    pkill -f "python3 app.py" && echo "Веб-интерфейс остановлен" || echo "Веб-интерфейс не найден"
fi

echo ""
echo "==============================================="
echo "Система остановлена"
echo "==============================================="
