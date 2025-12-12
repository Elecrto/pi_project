import logging
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, abort
from werkzeug.utils import secure_filename
from functools import wraps
from pathlib import Path

import config
from models import Database

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOGS_FOLDER / "app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация Flask
app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY

# Инициализация БД
db = Database()

# URL API сервиса
API_BASE_URL = f"http://localhost:{config.API_PORT}"


@app.route("/")
def index():
    """Перенаправление на главную страницу"""
    # if "user" in session:
    return redirect(url_for("main"))
    # return redirect(url_for("login"))


@app.route("/main")
def main():
    """Главная страница с списком аудиофайлов"""
    try:
        # Получаем список файлов из API
        response = requests.get(f"{API_BASE_URL}/list", timeout=5)

        if response.status_code == 200:
            files = response.json().get("files", [])
        else:
            files = []
            flash("Ошибка при получении списка файлов", "error")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {e}")
        files = []
        flash("Сервис обработки аудио недоступен", "error")

    return render_template("main.html", files=files, user=session.get("user"))


@app.route("/search")
def search():
    """Страница поиска по транскрипциям"""
    query = request.args.get("q", "")
    results = []

    if query:
        try:
            # Получаем все файлы и фильтруем по поисковому запросу
            response = requests.get(f"{API_BASE_URL}/list", timeout=5)
            if response.status_code == 200:
                all_files = response.json().get("files", [])
                # Фильтруем файлы с завершенной транскрипцией, содержащие поисковый запрос
                results = [
                    f for f in all_files
                    if f.get("status") == "completed" and
                    f.get("transcription") and
                    query.lower() in f.get("transcription", "").lower()
                ]
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при поиске: {e}")
            flash("Ошибка при выполнении поиска", "error")

    return render_template("search.html", query=query, results=results, user=session.get("user"))


@app.route("/statistics")
def statistics():
    """Страница статистики"""
    try:
        response = requests.get(f"{API_BASE_URL}/list", timeout=5)
        if response.status_code == 200:
            files = response.json().get("files", [])

            # Получаем общее количество когда-либо завершенных файлов
            stats_response = requests.get(f"{API_BASE_URL}/statistics/total_completed", timeout=5)
            total_completed = 0
            if stats_response.status_code == 200:
                total_completed = stats_response.json().get("total_completed_files", 0)

            # Подсчет статистики по текущим файлам
            total_files = len(files)
            processing_files = len([f for f in files if f.get("status") == "processing"])
            error_files = len([f for f in files if f.get("status") == "error"])

            # Общая длительность аудио
            total_duration = sum(f.get("duration", 0) or 0 for f in files)

            # Общий размер файлов в байтах
            total_size = sum(f.get("file_size", 0) or 0 for f in files)

            # Подсчет процента успеха на основе текущих файлов
            current_completed = len([f for f in files if f.get("status") == "completed"])
            success_rate = (current_completed / total_files * 100) if total_files > 0 else 0

            stats = {
                "total_files": total_files,
                "completed_files": total_completed,  # Общее количество завершенных файлов (включая удаленные)
                "processing_files": processing_files,
                "error_files": error_files,
                "total_duration": total_duration,
                "avg_duration": total_duration / total_files if total_files > 0 else 0,
                "total_size": total_size,  # Общий размер в байтах
                "success_rate": success_rate
            }
        else:
            stats = {}
            flash("Ошибка при получении статистики", "error")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        stats = {}
        flash("Сервис обработки аудио недоступен", "error")

    return render_template("statistics.html", stats=stats, user=session.get("user"))


@app.route("/favorites")
def favorites():
    """Страница избранных файлов"""
    try:
        response = requests.get(f"{API_BASE_URL}/list", timeout=5)
        if response.status_code == 200:
            all_files = response.json().get("files", [])
            # Фильтруем файлы с флагом is_favorite
            favorite_files = [f for f in all_files if f.get("is_favorite", False)]
        else:
            favorite_files = []
            flash("Ошибка при получении списка файлов", "error")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {e}")
        favorite_files = []
        flash("Сервис обработки аудио недоступен", "error")

    return render_template("favorites.html", files=favorite_files, user=session.get("user"))


@app.route("/toggle_favorite/<int:audio_id>", methods=["POST"])
def toggle_favorite(audio_id):
    """Переключение статуса избранного"""
    try:
        response = requests.post(f"{API_BASE_URL}/toggle_favorite/{audio_id}", timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get("is_favorite"):
                flash("Файл добавлен в избранное", "success")
            else:
                flash("Файл удален из избранного", "success")
        else:
            flash("Ошибка при изменении статуса", "error")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при изменении статуса избранного: {e}")
        flash("Ошибка при изменении статуса", "error")

    # Возвращаемся на предыдущую страницу
    return redirect(request.referrer or url_for("main"))


@app.route("/upload", methods=["POST"])
def upload():
    """Загрузка аудиофайла"""
    if "file" not in request.files:
        flash("Файл не выбран", "error")
        return redirect(url_for("main"))

    file = request.files["file"]

    if file.filename == "":
        flash("Файл не выбран", "error")
        return redirect(url_for("main"))

    # Проверяем формат
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in config.SUPPORTED_FORMATS:
        flash(f"Неподдерживаемый формат. Поддерживаются: {', '.join(config.SUPPORTED_FORMATS)}", "error")
        return redirect(url_for("main"))

    try:
        # Отправляем файл в API
        files = {"file": (file.filename, file.stream, file.content_type)}
        response = requests.post(f"{API_BASE_URL}/upload", files=files, timeout=30)

        if response.status_code == 200:
            result = response.json()
            flash(f"Файл успешно загружен", "success")
            logger.info(f"Файл {file.filename} загружен пользователем {session.get('user')}")
        else:
            flash("Ошибка при загрузке файла", "error")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при загрузке файла: {e}")
        flash("Ошибка при загрузке файла", "error")

    return redirect(url_for("main"))


@app.route("/audio/<int:audio_id>")
def audio_detail(audio_id):
    """Страница детальной информации об аудиофайле"""
    try:
        # Получаем информацию о файле из API
        response = requests.get(f"{API_BASE_URL}/status/{audio_id}", timeout=5)

        if response.status_code == 200:
            audio = response.json()
        elif response.status_code == 404:
            flash("Аудиофайл не найден", "error")
            return redirect(url_for("main"))
        else:
            flash("Ошибка при получении информации о файле", "error")
            return redirect(url_for("main"))

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {e}")
        flash("Сервис обработки аудио недоступен", "error")
        return redirect(url_for("main"))

    return render_template("audio_detail.html", audio=audio, user=session.get("user"))


@app.route("/get_audio/<int:audio_id>")
def get_audio(audio_id):
    """Отдача аудиофайла для проигрывания"""
    try:
        # Получаем информацию о файле из БД
        audio = db.get_audio_file(audio_id)

        if not audio:
            logger.warning(f"Аудиофайл ID={audio_id} не найден")
            abort(404)

        file_path = Path(audio["file_path"])

        if not file_path.exists():
            logger.error(f"Физический файл не найден: {file_path}")
            abort(404)

        # Определяем MIME-тип по формату
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
            ".wma": "audio/x-ms-wma",
            ".aac": "audio/aac"
        }

        file_ext = file_path.suffix.lower()
        mime_type = mime_types.get(file_ext, "audio/wav")

        logger.info(f"Отдача аудиофайла ID={audio_id} пользователю {session.get('user')}")
        return send_file(str(file_path), mimetype=mime_type)

    except Exception as e:
        logger.error(f"Ошибка при отдаче аудиофайла ID={audio_id}: {e}")
        abort(500)


@app.route("/delete/<int:audio_id>", methods=["POST"])
def delete(audio_id):
    """Удаление аудиофайла"""
    try:
        response = requests.delete(f"{API_BASE_URL}/delete/{audio_id}", timeout=5)

        if response.status_code == 200:
            flash("Файл успешно удален", "success")
            logger.info(f"Файл ID={audio_id} удален пользователем {session.get('user')}")
        else:
            flash("Ошибка при удалении файла", "error")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при удалении файла: {e}")
        flash("Ошибка при удалении файла", "error")

    return redirect(url_for("main"))


@app.route("/refresh_status/<int:audio_id>")
def refresh_status(audio_id):
    """AJAX эндпоинт для обновления статуса"""
    try:
        response = requests.get(f"{API_BASE_URL}/status/{audio_id}", timeout=5)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Не удалось получить статус"}), 500

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {e}")
        return jsonify({"error": "Сервис недоступен"}), 500


@app.errorhandler(404)
def not_found(error):
    """Обработчик 404 ошибки"""
    return render_template("login.html"), 404


@app.errorhandler(500)
def internal_error(error):
    """Обработчик 500 ошибки"""
    logger.error(f"Внутренняя ошибка сервера: {error}")
    flash("Внутренняя ошибка сервера", "error")
    return redirect(url_for("main"))


if __name__ == "__main__":
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=False
    )
