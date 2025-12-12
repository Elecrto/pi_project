import logging
import os
import uuid
import re
from pathlib import Path
from typing import Optional
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import torch
import json
import whisperx
import gc
import requests
from transformers import WhisperProcessor, WhisperForConditionalGeneration

import config
from models import Database
from audio_converter import AudioConverter

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOGS_FOLDER / "api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Проверка доступности llama-cpp-python
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger.warning("llama-cpp-python не установлен, используется Ollama API")

# Инициализация FastAPI
app = FastAPI(title="Audio Transcription API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные объекты
db = Database()
audio_converter = AudioConverter()
executor = ThreadPoolExecutor(max_workers=2)

# Модель Whisper (загружается при старте)
whisper_model = None
whisper_processor = None
whisper_device = None

# Модель суммаризации (локальная)
summary_model = None


def load_whisper_model():
    """Загружает fine-tuned модель Whisper"""
    global whisper_model, whisper_processor, whisper_device
    try:
        logger.info(f"Загрузка модели Whisper из {config.WHISPER_MODEL_PATH}")

        whisper_device = "cuda" if torch.cuda.is_available() and config.DEVICE == "cuda" else "cpu"
        logger.info(f"Используется устройство: {whisper_device}")

        # Загружаем fine-tuned модель напрямую через transformers
        whisper_processor = WhisperProcessor.from_pretrained(config.WHISPER_MODEL_PATH)
        whisper_model = WhisperForConditionalGeneration.from_pretrained(config.WHISPER_MODEL_PATH)
        whisper_model = whisper_model.to(whisper_device)
        whisper_model.eval()

        logger.info("Модель Whisper успешно загружена")
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели Whisper: {e}")
        logger.warning("Сервис будет работать без модели (для тестирования)")


def load_summary_model():
    """Загружает локальную модель для суммаризации"""
    global summary_model
    try:
        if config.USE_LOCAL_SUMMARY_MODEL and LLAMA_CPP_AVAILABLE:
            logger.info(f"Загрузка локальной модели суммаризации из {config.SUMMARY_MODEL_PATH}")

            summary_model = Llama(
                model_path=str(config.SUMMARY_MODEL_PATH),
                n_ctx=4096,  # Контекстное окно
                n_threads=4,  # Количество потоков
                n_gpu_layers=0,  # 0 для CPU, или больше если есть GPU
                verbose=False
            )

            logger.info("Локальная модель суммаризации успешно загружена")
        else:
            if not LLAMA_CPP_AVAILABLE:
                logger.warning("llama-cpp-python не доступен, будет использоваться Ollama API")
            else:
                logger.warning(f"Локальная модель не найдена по пути {config.SUMMARY_MODEL_PATH}, будет использоваться Ollama API")
    except Exception as e:
        logger.error(f"Ошибка при загрузке локальной модели суммаризации: {e}")
        logger.warning("Будет использоваться Ollama API")


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    logger.info("Запуск API сервиса...")
    load_whisper_model()
    load_summary_model()


def format_datetime(dt_string: str) -> str:
    """
    Форматирует дату-время, убирая миллисекунды

    Args:
        dt_string: строка с датой-временем

    Returns:
        Отформатированная строка без миллисекунд
    """
    if not dt_string:
        return None

    try:
        # Парсим дату из разных возможных форматов
        if '.' in dt_string:
            # Формат с миллисекундами: 2023-11-22 21:29:01.376
            dt = datetime.strptime(dt_string.split('.')[0], "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")

        # Возвращаем в формате без миллисекунд
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_string


def generate_summary_local(text: str) -> Optional[str]:
    """
    Генерация краткого содержания через локальную модель (llama-cpp-python)

    Args:
        text: Полный текст транскрипции

    Returns:
        Краткое содержание или None в случае ошибки
    """
    if not text or len(text.strip()) < 50:
        logger.info(f"Текст слишком короткий для суммаризации ({len(text.strip())} символов, нужно минимум 50)")
        return None

    if not summary_model:
        logger.warning("Локальная модель суммаризации не загружена")
        return None

    try:
        # Ограничиваем длину текста
        max_chars = 15000
        text_to_summarize = text[:max_chars] if len(text) > max_chars else text

        system_prompt = "Ты - профессиональный помощник для создания развернутых содержаний текстов. Ты ВСЕГДА отвечаешь ТОЛЬКО на русском языке. Твои ответы должны быть информативными, структурированными и написаны исключительно по-русски."

        user_prompt = f"""Прочитай следующий текст и напиши развернутое краткое содержание на 10-15 предложений СТРОГО НА РУССКОМ ЯЗЫКЕ.

Текст:
{text_to_summarize}

ВАЖНО: Твой ответ должен быть ТОЛЬКО на русском языке! Напиши развернутое содержание, подробно раскрывая главные идеи, ключевые моменты и важные детали интервью."""

        full_prompt = f"<｜User｜>{system_prompt}\n\n{user_prompt}<｜Assistant｜>"

        logger.info("Запрос генерации краткого содержания через локальную модель...")

        response = summary_model(
            full_prompt,
            max_tokens=2000,
            temperature=0.5,
            top_p=0.9,
            stop=["<｜end▁of▁sentence｜>", "<｜User｜>"],
            echo=False
        )

        summary = response["choices"][0]["text"].strip()

        if summary:
            logger.info(f"Получен ответ от локальной модели (длина: {len(summary)} символов)")

            # Обрабатываем теги рассуждений <think>...</think>
            if "<think>" in summary and "</think>" in summary:
                last_think_end = summary.rfind("</think>")
                if last_think_end != -1:
                    clean_summary = summary[last_think_end + 8:].strip()
                    if clean_summary:
                        summary = clean_summary
                    else:
                        last_think_start = summary.rfind("<think>")
                        if last_think_start != -1 and last_think_end > last_think_start:
                            summary = summary[last_think_start + 7:last_think_end].strip()

            if summary:
                logger.info(f"Краткое содержание успешно сгенерировано (длина: {len(summary)} символов)")
                return summary
            else:
                logger.warning("После обработки ответ пустой")
                return None
        else:
            logger.warning("Локальная модель вернула пустой ответ")
            return None

    except Exception as e:
        logger.error(f"Ошибка при генерации краткого содержания через локальную модель: {e}")
        return None


def generate_summary_ollama(text: str, model: str = "deepseek-r1:8b") -> Optional[str]:
    """
    Генерация краткого содержания текста через Ollama API

    Args:
        text: Полный текст транскрипции
        model: Название модели Ollama (по умолчанию llava:7b)

    Returns:
        Краткое содержание или None в случае ошибки
    """
    if not text or len(text.strip()) < 50:
        return None

    try:
        # Ограничиваем длину текста для избежания перегрузки модели
        max_chars = 15000
        text_to_summarize = text[:max_chars] if len(text) > max_chars else text

        system_prompt = "Ты - профессиональный помощник для создания развернутых содержаний текстов. Ты всегда отвечаешь только на русском языке. Твои ответы должны быть информативными, структурированными и написаны исключительно по-русски."

        user_prompt = f"""Прочитай следующий текст и напиши развернутое краткое содержание на 10-15 предложений на русском языке.

Текст:
{text_to_summarize}

ВАЖНО: Твой ответ должен быть на русском языке! Напиши развернутое содержание, подробно раскрывая главные идеи, ключевые моменты и важные детали интервью."""

        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        logger.info(f"Запрос генерации краткого содержания через Ollama ({model})...")

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "system": system_prompt,
                "options": {
                    "temperature": 0.5,  # Снижена для более предсказуемых результатов
                    "top_p": 0.9,
                    "num_predict": 2000
                }
            },
            timeout=180
        )

        if response.status_code == 200:
            result = response.json()
            summary = result.get("response", "").strip()

            if summary:
                logger.info(f"Получен ответ от Ollama (длина: {len(summary)} символов)")

                # Для DeepSeek-R1: обрабатываем теги рассуждений <think>...</think>
                if "<think>" in summary and "</think>" in summary:
                    # Извлекаем текст после последнего закрывающего тега </think>
                    last_think_end = summary.rfind("</think>")
                    if last_think_end != -1:
                        # Берем все после последнего </think>
                        clean_summary = summary[last_think_end + 8:].strip()
                        if clean_summary:
                            summary = clean_summary
                        else:
                            # Если после </think> ничего нет, берем содержимое последнего <think>
                            logger.warning("Текст только внутри тегов <think>, извлекаю содержимое")
                            # Находим последнюю пару тегов
                            last_think_start = summary.rfind("<think>")
                            if last_think_start != -1 and last_think_end > last_think_start:
                                summary = summary[last_think_start + 7:last_think_end].strip()

                if summary:
                    logger.info(f"Краткое содержание успешно сгенерировано (длина: {len(summary)} символов)")
                    return summary
                else:
                    logger.warning("После обработки ответ пустой")
                    return None
            else:
                logger.warning("Ollama вернула пустой ответ")
                return None
        else:
            logger.error(f"Ошибка Ollama API: {response.status_code}")
            return None

    except requests.exceptions.ConnectionError:
        logger.error("Не удалось подключиться к Ollama. Убедитесь, что сервер запущен.")
        return None
    except requests.exceptions.Timeout:
        logger.error("Таймаут при генерации краткого содержания")
        return None
    except Exception as e:
        logger.error(f"Ошибка при генерации краткого содержания: {e}")
        return None


def generate_summary(text: str) -> Optional[str]:
    """
    Универсальная функция для генерации краткого содержания.
    Автоматически выбирает между локальной моделью и Ollama API.

    Args:
        text: Полный текст транскрипции

    Returns:
        Краткое содержание или None в случае ошибки
    """
    # Приоритет: локальная модель > Ollama API
    if summary_model:
        logger.info("Используется локальная модель для генерации краткого содержания")
        return generate_summary_local(text)
    else:
        logger.info("Используется Ollama API для генерации краткого содержания")
        return generate_summary_ollama(text)


def post_process_transcription(text: str) -> str:
    """
    Постобработка транскрипции для улучшения качества текста

    Args:
        text: исходный текст транскрипции

    Returns:
        Обработанный текст
    """
    if not text:
        return text

    # 1. Удаление лишних пробелов
    text = re.sub(r'\s+', ' ', text).strip()

    # 2. Удаление повторяющихся слов (типичная проблема Whisper)
    words = text.split()
    cleaned_words = []
    prev_word = None
    repeat_count = 0

    for word in words:
        if word.lower() == prev_word:
            repeat_count += 1
            # Пропускаем повторения более 2 раз подряд
            if repeat_count >= 2:
                continue
        else:
            repeat_count = 0

        cleaned_words.append(word)
        prev_word = word.lower()

    text = ' '.join(cleaned_words)

    # 3. Исправление пробелов перед знаками препинания
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    text = re.sub(r'([,.!?;:])\s*([,.!?;:])', r'\1\2', text)  # Удаление дублирующихся знаков

    # 4. Добавление пробела после знаков препинания
    text = re.sub(r'([,.!?;:])([^\s\d])', r'\1 \2', text)

    # 5. Первая буква в начале предложений заглавная
    sentences = re.split(r'([.!?]\s+)', text)
    capitalized = []
    for i, part in enumerate(sentences):
        if i % 2 == 0 and part:  # Это предложение, а не разделитель
            part = part[0].upper() + part[1:] if len(part) > 0 else part
        capitalized.append(part)
    text = ''.join(capitalized)

    # 6. Удаление артефактов типа [музыка], [смех], (неразборчиво)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)

    # 7. Очистка множественных знаков препинания
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r',{2,}', ',', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # 8. Добавление точки в конце, если отсутствует
    if text and text[-1] not in '.!?':
        text += '.'

    return text


def transcribe_audio(audio_path: str):
    """
    Транскрибирует аудио с помощью fine-tuned Whisper + whisperX alignment для word timestamps

    Args:
        audio_path: путь к аудиофайлу

    Returns:
        Tuple: (текст транскрипции, JSON с word timestamps)
    """
    try:
        logger.info(f"Начало транскрипции: {audio_path}")

        if whisper_model is None or whisper_processor is None:
            logger.warning("Модель не загружена, возвращаем тестовый текст")
            return "Тестовая транскрипция (модель не загружена)", None

        # Загружаем аудио
        import librosa
        audio_data, sr = librosa.load(audio_path, sr=16000, mono=True)

        # 1. Транскрибируем с помощью fine-tuned модели
        logger.info("Транскрипция с fine-tuned моделью...")

        # Обрабатываем аудио по чанкам для длинных файлов
        chunk_length = int(30 * sr)  # 30 секунд
        segments_data = []

        for i in range(0, len(audio_data), chunk_length):
            chunk = audio_data[i:min(i + chunk_length, len(audio_data))]

            # Пропускаем слишком короткие чанки
            if len(chunk) < 0.5 * sr:
                continue

            # Подготавливаем входные данные
            input_features = whisper_processor(
                chunk,
                sampling_rate=sr,
                return_tensors="pt"
            ).input_features

            input_features = input_features.to(whisper_device)

            # Генерируем транскрипцию
            with torch.no_grad():
                predicted_ids = whisper_model.generate(
                    input_features,
                    language="ru",
                    task="transcribe",
                    use_cache=False
                )

            # Декодируем результат
            transcription = whisper_processor.batch_decode(
                predicted_ids,
                skip_special_tokens=True
            )[0]

            # Сохраняем сегмент
            start_time = i / sr
            end_time = min(i + chunk_length, len(audio_data)) / sr

            segments_data.append({
                "text": transcription.strip(),
                "start": start_time,
                "end": end_time
            })

            # Очистка памяти GPU
            if whisper_device == "cuda":
                del input_features, predicted_ids
                torch.cuda.empty_cache()

        # 2. Применяем whisperx alignment для получения word-level timestamps
        logger.info("Загрузка модели для word-level alignment...")
        try:
            model_a, metadata = whisperx.load_align_model(language_code="ru", device=whisper_device)

            logger.info("Применение word-level alignment...")
            aligned_result = whisperx.align(
                segments_data,
                model_a,
                metadata,
                audio_data,
                whisper_device,
                return_char_alignments=False
            )

            # Очищаем память от модели alignment
            del model_a
            gc.collect()
            if whisper_device == "cuda":
                torch.cuda.empty_cache()

            # Собираем все слова с временными метками
            all_words = []
            all_text = []

            for segment in aligned_result["segments"]:
                for word_data in segment.get("words", []):
                    all_words.append({
                        "word": word_data["word"].strip(),
                        "start": round(word_data["start"], 2),
                        "end": round(word_data["end"], 2)
                    })
                    all_text.append(word_data["word"].strip())

            # Объединяем текст
            if all_text:
                full_transcription = " ".join(all_text)
            else:
                # Если alignment не дал результатов, используем segment text
                full_transcription = " ".join([seg["text"] for seg in segments_data])

            # Применяем постобработку
            full_transcription = post_process_transcription(full_transcription)

            # Сохраняем timestamps в JSON
            word_timestamps_json = json.dumps(all_words, ensure_ascii=False) if all_words else None

            logger.info(f"Транскрипция завершена. Длина текста: {len(full_transcription)} символов, слов: {len(all_words)}")

            return full_transcription, word_timestamps_json

        except Exception as align_error:
            logger.warning(f"Ошибка при alignment, возвращаем текст без word timestamps: {align_error}")

            # Возвращаем текст без word-level timestamps
            full_transcription = " ".join([seg["text"] for seg in segments_data])
            full_transcription = post_process_transcription(full_transcription)

            return full_transcription, None

    except Exception as e:
        logger.error(f"Ошибка при транскрипции: {e}")
        raise


async def process_audio_task(audio_id: int, file_path: str):
    """
    Фоновая задача для обработки аудио

    Args:
        audio_id: ID аудиофайла в БД
        file_path: путь к файлу
    """
    try:
        logger.info(f"Начало обработки аудио ID={audio_id}")

        # Обновляем статус на "processing"
        db.update_status(audio_id, "processing")

        # Конвертируем аудио
        converted_path, duration = audio_converter.convert_to_mono_wav(file_path)

        # Обновляем длительность в БД
        db.update_duration(audio_id, duration)

        # Транскрибируем (в отдельном потоке чтобы не блокировать event loop)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            transcribe_audio,
            converted_path
        )

        # Распаковываем результат
        transcription, word_timestamps = result

        # Генерируем краткое содержание
        logger.info(f"Генерация краткого содержания для аудио ID={audio_id}")
        summary = generate_summary(transcription)

        if summary:
            logger.info(f"Краткое содержание для ID={audio_id}: {len(summary)} символов")
        else:
            logger.warning(f"Не удалось сгенерировать краткое содержание для ID={audio_id}")

        # Обновляем статус на "completed"
        db.update_status(audio_id, "completed", transcription=transcription, word_timestamps=word_timestamps, summary=summary)

        # Удаляем конвертированный файл если это не оригинал
        if converted_path != file_path:
            Path(converted_path).unlink(missing_ok=True)

        logger.info(f"Обработка аудио ID={audio_id} завершена успешно")

    except Exception as e:
        logger.error(f"Ошибка при обработке аудио ID={audio_id}: {e}")
        db.update_status(audio_id, "error", error_message=str(e))


@app.post("/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Загрузка аудиофайла для обработки
    """
    try:
        # Проверяем формат файла
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in config.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат. Поддерживаются: {', '.join(config.SUPPORTED_FORMATS)}"
            )

        # Генерируем уникальное имя файла
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = config.UPLOAD_FOLDER / unique_filename

        # Сохраняем файл
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        file_size = len(content)

        # Добавляем в БД
        audio_id = db.add_audio_file(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            audio_format=file_ext
        )

        # Запускаем обработку в фоне
        background_tasks.add_task(process_audio_task, audio_id, str(file_path))

        logger.info(f"Файл загружен: {file.filename} -> ID={audio_id}")

        return JSONResponse({
            "status": "success",
            "audio_id": audio_id,
            "message": "Файл загружен и отправлен на обработку"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{audio_id}")
async def get_status(audio_id: int):
    """
    Получение статуса обработки аудио
    """
    audio = db.get_audio_file(audio_id)

    if not audio:
        raise HTTPException(status_code=404, detail="Аудиофайл не найден")

    return JSONResponse({
        "id": audio_id,
        "audio_id": audio_id,
        "status": audio["status"],
        "filename": audio["original_filename"],
        "format": audio["format"],
        "transcription": audio["transcription"],
        "summary": audio.get("summary"),
        "word_timestamps": audio.get("word_timestamps"),
        "error_message": audio["error_message"],
        "created_at": format_datetime(audio["created_at"]),
        "processed_at": format_datetime(audio["processed_at"])
    })


@app.get("/list")
async def list_audio_files(limit: int = 100):
    """
    Получение списка всех аудиофайлов
    """
    files = db.get_all_audio_files(limit=limit)

    # Форматируем даты для каждого файла
    for file in files:
        file["created_at"] = format_datetime(file.get("created_at"))
        file["processed_at"] = format_datetime(file.get("processed_at"))

    return JSONResponse({"files": files})


@app.delete("/delete/{audio_id}")
async def delete_audio(audio_id: int):
    """
    Удаление аудиофайла
    """
    audio = db.get_audio_file(audio_id)

    if not audio:
        raise HTTPException(status_code=404, detail="Аудиофайл не найден")

    # Удаляем файл с диска
    file_path = Path(audio["file_path"])
    if file_path.exists():
        file_path.unlink()

    # Удаляем из БД
    db.delete_audio_file(audio_id)

    logger.info(f"Аудиофайл ID={audio_id} удален")

    return JSONResponse({"status": "success", "message": "Файл удален"})


@app.post("/toggle_favorite/{audio_id}")
async def toggle_favorite(audio_id: int):
    """
    Переключение статуса избранного для файла
    """
    audio = db.get_audio_file(audio_id)

    if not audio:
        raise HTTPException(status_code=404, detail="Аудиофайл не найден")

    is_favorite = db.toggle_favorite(audio_id)

    logger.info(f"Файл ID={audio_id} {'добавлен в избранное' if is_favorite else 'удален из избранного'}")

    return JSONResponse({
        "status": "success",
        "is_favorite": is_favorite
    })


@app.get("/statistics/total_completed")
async def get_total_completed():
    """
    Получение общего количества когда-либо завершенных файлов
    """
    total_completed = db.get_total_completed_files()

    return JSONResponse({
        "total_completed_files": total_completed
    })


@app.get("/health")
async def health_check():
    """
    Проверка работоспособности API
    """
    return JSONResponse({
        "status": "ok",
        "model_loaded": whisper_model is not None
    })


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=False
    )
