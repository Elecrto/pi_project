import logging
from pathlib import Path
from typing import Tuple
import librosa
import soundfile as sf
import numpy as np
from scipy import signal
import config

logger = logging.getLogger(__name__)


class AudioConverter:
    """Класс для конвертации аудиофайлов в формат, подходящий для Whisper с улучшенной предобработкой"""

    def __init__(self):
        self.target_sr = config.TARGET_SAMPLE_RATE

    def convert_to_mono_wav(self, input_path: str, output_path: str = None) -> Tuple[str, float]:
        """
        Конвертирует аудио в моно WAV с частотой 16kHz

        Args:
            input_path: путь к входному аудиофайлу
            output_path: путь для сохранения конвертированного файла

        Returns:
            Tuple[str, float]: путь к конвертированному файлу и его длительность в секундах
        """
        try:
            input_path = Path(input_path)

            if output_path is None:
                output_path = input_path.parent / f"{input_path.stem}_converted.wav"
            else:
                output_path = Path(output_path)

            logger.info(f"Конвертация аудио: {input_path} -> {output_path}")

            # Загружаем аудио с помощью librosa
            # mono=True автоматически конвертирует в моно
            # sr=self.target_sr ресэмплирует на нужную частоту
            audio, sr = librosa.load(str(input_path), sr=self.target_sr, mono=True)

            # Вычисляем длительность
            duration = len(audio) / sr

            # Применяем улучшенную предобработку
            audio = self.preprocess_audio(audio, sr)

            # Сохраняем в WAV формат
            sf.write(str(output_path), audio, sr, subtype='PCM_16')

            logger.info(f"Аудио успешно конвертировано. Длительность: {duration:.2f}с")

            return str(output_path), duration

        except Exception as e:
            logger.error(f"Ошибка при конвертации аудио: {e}")
            raise

    def preprocess_audio(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Комплексная предобработка аудио для улучшения качества транскрипции

        Args:
            audio: numpy array с аудио данными
            sr: частота дискретизации

        Returns:
            Предобработанный аудио сигнал
        """
        # 1. Удаление тишины в начале и конце
        audio = self.trim_silence(audio, sr)

        # 2. Шумоподавление
        audio = self.reduce_noise(audio, sr)

        # 3. Нормализация громкости (улучшенная)
        audio = self.normalize_audio(audio)

        # 4. Применение фильтра высоких частот для улучшения речи
        audio = self.apply_highpass_filter(audio, sr)

        return audio

    def trim_silence(self, audio: np.ndarray, sr: int, top_db: int = 30) -> np.ndarray:
        """
        Удаляет тишину в начале и конце аудио

        Args:
            audio: аудио сигнал
            sr: частота дискретизации
            top_db: порог в децибелах

        Returns:
            Аудио без тишины
        """
        try:
            # Обрезаем тишину
            trimmed, _ = librosa.effects.trim(audio, top_db=top_db)
            return trimmed
        except Exception as e:
            logger.warning(f"Не удалось обрезать тишину: {e}")
            return audio

    def reduce_noise(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Простое шумоподавление методом спектрального вычитания

        Args:
            audio: аудио сигнал
            sr: частота дискретизации

        Returns:
            Аудио с подавленным шумом
        """
        try:
            # Оцениваем шум по первым 0.5 секундам
            noise_sample_length = min(int(0.5 * sr), len(audio) // 4)
            if noise_sample_length < sr // 10:  # Минимум 0.1 секунды
                return audio

            noise_sample = audio[:noise_sample_length]

            # Вычисляем среднюю мощность шума
            noise_power = np.mean(noise_sample ** 2)

            # Применяем мягкое шумоподавление
            if noise_power > 0:
                # Спектральное вычитание
                threshold = np.sqrt(noise_power) * 2.0
                audio_denoised = np.where(np.abs(audio) > threshold, audio, audio * 0.1)
                return audio_denoised

            return audio

        except Exception as e:
            logger.warning(f"Не удалось применить шумоподавление: {e}")
            return audio

    def normalize_audio(self, audio: np.ndarray, target_level: float = -20.0) -> np.ndarray:
        """
        Улучшенная нормализация громкости (RMS-based)

        Args:
            audio: аудио сигнал
            target_level: целевой уровень в dB

        Returns:
            Нормализованный аудио сигнал
        """
        try:
            # Вычисляем RMS
            rms = np.sqrt(np.mean(audio ** 2))

            if rms > 0:
                # Целевой RMS
                target_rms = 10 ** (target_level / 20.0)

                # Коэффициент усиления
                gain = target_rms / rms

                # Ограничиваем усиление
                gain = min(gain, 10.0)  # Максимум 10x

                audio_normalized = audio * gain

                # Предотвращаем клиппинг
                max_val = np.abs(audio_normalized).max()
                if max_val > 0.95:
                    audio_normalized = audio_normalized / max_val * 0.95

                return audio_normalized

            return audio

        except Exception as e:
            logger.warning(f"Не удалось нормализовать аудио: {e}")
            # Fallback к простой нормализации
            max_val = np.abs(audio).max()
            if max_val > 0:
                return audio / max_val * 0.95
            return audio

    def apply_highpass_filter(self, audio: np.ndarray, sr: int, cutoff: int = 80) -> np.ndarray:
        """
        Применяет фильтр высоких частот для удаления низкочастотного шума

        Args:
            audio: аудио сигнал
            sr: частота дискретизации
            cutoff: частота среза в Гц

        Returns:
            Отфильтрованный аудио сигнал
        """
        try:
            # Создаем butterworth фильтр высоких частот
            nyquist = sr / 2
            normal_cutoff = cutoff / nyquist

            # Проверяем корректность частоты среза
            if normal_cutoff >= 1.0:
                return audio

            b, a = signal.butter(4, normal_cutoff, btype='high', analog=False)

            # Применяем фильтр
            filtered = signal.filtfilt(b, a, audio)

            return filtered

        except Exception as e:
            logger.warning(f"Не удалось применить фильтр: {e}")
            return audio

    def get_audio_info(self, file_path: str) -> dict:
        """
        Получает информацию об аудиофайле

        Args:
            file_path: путь к аудиофайлу

        Returns:
            Словарь с информацией о файле
        """
        try:
            audio, sr = librosa.load(str(file_path), sr=None)
            duration = len(audio) / sr
            channels = 1 if len(audio.shape) == 1 else audio.shape[0]

            return {
                "duration": duration,
                "sample_rate": sr,
                "channels": channels,
                "samples": len(audio)
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации об аудио: {e}")
            raise

    def validate_audio_file(self, file_path: str) -> bool:
        """
        Проверяет, является ли файл корректным аудиофайлом

        Args:
            file_path: путь к файлу

        Returns:
            True если файл корректен, False иначе
        """
        try:
            file_path = Path(file_path)

            # Проверяем расширение
            if file_path.suffix.lower() not in config.SUPPORTED_FORMATS:
                logger.warning(f"Неподдерживаемый формат: {file_path.suffix}")
                return False

            # Пытаемся загрузить файл
            audio, sr = librosa.load(str(file_path), sr=None, duration=1.0)

            return True

        except Exception as e:
            logger.error(f"Файл не является корректным аудио: {e}")
            return False
