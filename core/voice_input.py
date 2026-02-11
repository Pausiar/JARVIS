"""
J.A.R.V.I.S. — Voice Input (Speech-to-Text)
Reconocimiento de voz usando Whisper local (faster-whisper).
"""

import logging
import threading
import queue
import tempfile
import wave
import struct
from pathlib import Path
from typing import Callable, Optional

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    WHISPER_MODEL,
    WHISPER_LANGUAGE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    WAKE_WORD,
    DATA_DIR,
)

logger = logging.getLogger("jarvis.voice_input")


class VoiceInput:
    """Motor de reconocimiento de voz usando faster-whisper."""

    def __init__(self):
        self.model = None
        self.is_listening = False
        self.is_recording = False
        self._audio_queue = queue.Queue()
        self._listen_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.sample_rate = 16000
        self.channels = 1
        self.on_transcription: Optional[Callable[[str], None]] = None
        self.on_wake_word: Optional[Callable[[], None]] = None
        self.on_listening_state: Optional[Callable[[bool], None]] = None
        self._model_loaded = False
        logger.info("VoiceInput inicializado.")

    # ─── Carga del modelo ─────────────────────────────────────

    def load_model(self) -> bool:
        """Carga el modelo de Whisper."""
        try:
            from faster_whisper import WhisperModel

            logger.info(f"Cargando modelo Whisper '{WHISPER_MODEL}'...")
            self.model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            self._model_loaded = True
            logger.info("Modelo Whisper cargado correctamente.")
            return True
        except ImportError:
            logger.error(
                "faster-whisper no está instalado. "
                "Instálalo con: pip install faster-whisper"
            )
            return False
        except Exception as e:
            logger.error(f"Error cargando modelo Whisper: {e}")
            return False

    @property
    def is_model_loaded(self) -> bool:
        return self._model_loaded

    # ─── Transcripción de audio ───────────────────────────────

    def transcribe_audio(self, audio_data: np.ndarray) -> str:
        """
        Transcribe un array de audio numpy a texto.

        Args:
            audio_data: Array numpy con los datos de audio (float32, mono, 16kHz).

        Returns:
            Texto transcrito.
        """
        if not self._model_loaded:
            logger.error("Modelo no cargado. Llama a load_model() primero.")
            return ""

        try:
            # Asegurar formato correcto
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Normalizar si es necesario
            max_val = np.max(np.abs(audio_data))
            if max_val > 1.0:
                audio_data = audio_data / max_val

            segments, info = self.model.transcribe(
                audio_data,
                language=WHISPER_LANGUAGE,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
            )

            text = " ".join(segment.text for segment in segments).strip()

            if text:
                lang = info.language if hasattr(info, 'language') else "unknown"
                logger.info(
                    f"Transcripción: '{text}' "
                    f"(idioma: {lang}, prob: {info.language_probability:.2f})"
                )

            return text

        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            return ""

    def transcribe_file(self, file_path: str) -> str:
        """Transcribe un archivo de audio a texto."""
        if not self._model_loaded:
            logger.error("Modelo no cargado.")
            return ""

        try:
            segments, info = self.model.transcribe(
                file_path,
                language=WHISPER_LANGUAGE,
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(segment.text for segment in segments).strip()
            logger.info(f"Archivo transcrito: '{text[:100]}...'")
            return text

        except Exception as e:
            logger.error(f"Error transcribiendo archivo: {e}")
            return ""

    # ─── Grabación de audio ───────────────────────────────────

    def start_recording(self) -> None:
        """Inicia la grabación de audio del micrófono."""
        if self.is_recording:
            logger.warning("Ya se está grabando audio.")
            return

        self._stop_event.clear()
        self._audio_queue = queue.Queue()
        self.is_recording = True

        if self.on_listening_state:
            self.on_listening_state(True)

        self._listen_thread = threading.Thread(
            target=self._record_audio,
            daemon=True,
        )
        self._listen_thread.start()
        logger.info("Grabación de audio iniciada.")

    def stop_recording(self) -> str:
        """
        Detiene la grabación y transcribe el audio capturado.

        Returns:
            Texto transcrito del audio grabado.
        """
        if not self.is_recording:
            return ""

        self._stop_event.set()
        self.is_recording = False

        if self.on_listening_state:
            self.on_listening_state(False)

        if self._listen_thread:
            self._listen_thread.join(timeout=3)

        # Recoger todo el audio grabado
        audio_chunks = []
        while not self._audio_queue.empty():
            try:
                chunk = self._audio_queue.get_nowait()
                audio_chunks.append(chunk)
            except queue.Empty:
                break

        if not audio_chunks:
            logger.warning("No se capturó audio.")
            return ""

        # Concatenar chunks y transcribir
        audio_data = np.concatenate(audio_chunks)
        logger.info(f"Audio capturado: {len(audio_data)} muestras ({len(audio_data)/self.sample_rate:.1f}s)")

        return self.transcribe_audio(audio_data)

    def _record_audio(self) -> None:
        """Hilo de grabación de audio."""
        try:
            import sounddevice as sd

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.warning(f"Audio status: {status}")
                if not self._stop_event.is_set():
                    self._audio_queue.put(indata[:, 0].copy())

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                blocksize=int(self.sample_rate * 0.1),  # 100ms bloques
                callback=audio_callback,
            ):
                while not self._stop_event.is_set():
                    self._stop_event.wait(timeout=0.1)

        except ImportError:
            logger.error("sounddevice no instalado. pip install sounddevice")
        except Exception as e:
            logger.error(f"Error en grabación: {e}")
            self.is_recording = False

    # ─── Escucha continua (wake word) ─────────────────────────

    def start_wake_word_listener(self) -> None:
        """Inicia la escucha continua para detectar la palabra de activación."""
        if self.is_listening:
            return

        self.is_listening = True
        self._stop_event.clear()

        self._listen_thread = threading.Thread(
            target=self._wake_word_loop,
            daemon=True,
        )
        self._listen_thread.start()
        logger.info(f"Escuchando wake word: '{WAKE_WORD}'")

    def stop_wake_word_listener(self) -> None:
        """Detiene la escucha de wake word."""
        self._stop_event.set()
        self.is_listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=3)
        logger.info("Wake word listener detenido.")

    def _wake_word_loop(self) -> None:
        """Bucle de escucha para wake word."""
        try:
            import sounddevice as sd

            buffer_duration = 3  # segundos de buffer
            buffer_size = int(self.sample_rate * buffer_duration)
            audio_buffer = np.zeros(buffer_size, dtype=np.float32)
            check_interval = 2  # Verificar cada 2 segundos

            def audio_callback(indata, frames, time_info, status):
                nonlocal audio_buffer
                if not self._stop_event.is_set():
                    new_data = indata[:, 0]
                    audio_buffer = np.roll(audio_buffer, -len(new_data))
                    audio_buffer[-len(new_data):] = new_data

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                blocksize=int(self.sample_rate * 0.5),
                callback=audio_callback,
            ):
                while not self._stop_event.is_set():
                    self._stop_event.wait(timeout=check_interval)
                    if self._stop_event.is_set():
                        break

                    # Verificar si hay actividad de audio (nivel de energía)
                    energy = np.sqrt(np.mean(audio_buffer**2))
                    if energy > 0.01:  # Umbral de actividad
                        text = self.transcribe_audio(audio_buffer.copy())
                        if WAKE_WORD.lower() in text.lower():
                            logger.info("Wake word detectado!")
                            if self.on_wake_word:
                                self.on_wake_word()

        except ImportError:
            logger.error("sounddevice no instalado para wake word listener.")
        except Exception as e:
            logger.error(f"Error en wake word loop: {e}")
            self.is_listening = False

    # ─── Utilidades ───────────────────────────────────────────

    def get_audio_devices(self) -> list[dict]:
        """Lista los dispositivos de audio disponibles."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = []
            for i, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    input_devices.append({
                        "id": i,
                        "name": dev["name"],
                        "channels": dev["max_input_channels"],
                        "sample_rate": dev["default_samplerate"],
                    })
            return input_devices
        except Exception as e:
            logger.error(f"Error listando dispositivos: {e}")
            return []
