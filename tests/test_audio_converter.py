import pytest
import tempfile
import os
from pathlib import Path
import sys

# Добавляем корневую директорию в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_converter import AudioConverter


def test_audio_converter_initialization():
    """Тест инициализации AudioConverter"""
    converter = AudioConverter()
    assert converter is not None
    assert converter.temp_dir is not None
    assert os.path.exists(converter.temp_dir)


def test_convert_to_mono_wav_success():
    """Тест успешной конвертации в mono WAV"""
    converter = AudioConverter()
    
    # Создаем минимальный WAV файл
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # Минимальный WAV заголовок для моно, 16kHz
        wav_header = (
            b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00'
            b'\x80\xbb\x00\x00\x00\xee\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00'
        )
        f.write(wav_header)
        f.flush()
        
        # Пытаемся конвертировать
        output_path, duration = converter.convert_to_mono_wav(f.name)
        
        assert output_path is not None
        assert isinstance(output_path, str)
        assert os.path.exists(output_path)
        assert output_path.endswith('.wav')
        
        # Проверяем, что файл был создан
        assert os.path.getsize(output_path) > 0
        
        # Очищаем
        os.unlink(output_path)
    os.unlink(f.name)


def test_convert_to_mono_wav_nonexistent_file():
    """Тест конвертации несуществующего файла"""
    converter = AudioConverter()
    
    with pytest.raises(Exception):
        converter.convert_to_mono_wav("/nonexistent/file.wav")


def test_convert_to_mono_wav_already_mono():
    """Тест конвертации уже моно файла"""
    converter = AudioConverter()
    
    # Создаем минимальный моно WAV файл
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # Моно WAV заголовок
        wav_header = (
            b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
            b'\x80\xbb\x00\x00\x00\x77\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        )
        f.write(wav_header)
        f.flush()
        
        output_path, duration = converter.convert_to_mono_wav(f.name)
        
        # Проверяем, что вернулся оригинальный путь (или конвертированный)
        assert output_path is not None
        assert os.path.exists(output_path)
        
        # Очищаем
        if output_path != f.name:
            os.unlink(output_path)
    os.unlink(f.name)


def test_audio_converter_cleanup():
    """Тест очистки временных файлов"""
    converter = AudioConverter()
    temp_dir = converter.temp_dir
    
    # Создаем временный файл в temp_dir
    temp_file = os.path.join(temp_dir, "test.txt")
    with open(temp_file, "w") as f:
        f.write("test")
    
    # Удаляем конвертер (вызывается __del__)
    del converter
    
    # Проверяем, что временная директория удалена
    assert not os.path.exists(temp_dir)


def test_audio_converter_with_different_formats():
    """Тест конвертации файлов разных форматов"""
    converter = AudioConverter()
    
    # Тест с MP3 (будет падать без ffmpeg, но проверяем обработку ошибок)
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        f.write(b'fake mp3 content')
        f.flush()
        
        try:
            output_path, duration = converter.convert_to_mono_wav(f.name)
            # Если ffmpeg установлен, тест пройдет
            if output_path:
                assert os.path.exists(output_path)
                if output_path != f.name:
                    os.unlink(output_path)
        except Exception as e:
            # Без ffmpeg ожидаем ошибку
            assert "ffmpeg" in str(e) or "конвертация" in str(e)
    os.unlink(f.name)


def test_get_audio_duration():
    """Тест получения длительности аудио"""
    converter = AudioConverter()
    
    # Создаем минимальный WAV файл
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # WAV заголовок с указанием длительности
        wav_header = (
            b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
            b'\x80\xbb\x00\x00\x00\x77\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        )
        f.write(wav_header)
        f.flush()
        
        # Используем приватный метод через рефлексию
        duration = converter._get_audio_duration(f.name)
        
        # Длительность может быть 0 для пустого файла
        assert isinstance(duration, float)
        assert duration >= 0
    
    os.unlink(f.name)