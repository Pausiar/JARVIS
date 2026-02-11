"""
J.A.R.V.I.S. — Voice Output (Text-to-Speech)
Síntesis de voz usando Piper TTS o pyttsx3 como fallback.
"""

import logging
import subprocess
import threading
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Callable

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    PIPER_MODEL_PATH,
    PIPER_VOICE,
    TTS_RATE,
    TTS_ENABLED,
    DATA_DIR,
)

logger = logging.getLogger("jarvis.voice_output")


class VoiceOutput:
    """Motor de síntesis de voz para JARVIS."""

    def __init__(self):
        self.enabled = TTS_ENABLED
        self.is_speaking = False
        self._stop_event = threading.Event()
        self._speak_thread: Optional[threading.Thread] = None
        self._engine = None
        self._engine_type: Optional[str] = None  # "piper" o "pyttsx3"
        self.on_speaking_state: Optional[Callable[[bool], None]] = None
        self.rate = TTS_RATE
        logger.info("VoiceOutput inicializado.")

    # ─── Inicialización del motor TTS ─────────────────────────

    def initialize(self) -> bool:
        """Inicializa el motor TTS. Intenta Piper primero, luego pyttsx3."""
        # Intentar Piper TTS
        if self._init_piper():
            self._engine_type = "piper"
            logger.info("Motor TTS: Piper")
            return True

        # Fallback a pyttsx3
        if self._init_pyttsx3():
            self._engine_type = "pyttsx3"
            logger.info("Motor TTS: pyttsx3 (fallback)")
            return True

        logger.error("No se pudo inicializar ningún motor TTS.")
        return False

    def _init_piper(self) -> bool:
        """Inicializa Piper TTS."""
        try:
            # Verificar si el modelo de Piper existe antes de intentar usarlo
            model_path = Path(PIPER_MODEL_PATH)
            if not model_path.exists():
                logger.info("Modelo Piper no encontrado. Saltando a fallback.")
                return False

            piper_path = shutil.which("piper")
            if piper_path:
                self._engine = piper_path
                logger.info(f"Piper encontrado en: {piper_path}")
                return True

            # Verificar si piper-tts está instalado como paquete Python
            try:
                import piper
                self._engine = "piper_python"
                return True
            except ImportError:
                pass

            logger.info("Piper TTS no encontrado. Intentando fallback.")
            return False
        except Exception as e:
            logger.error(f"Error inicializando Piper: {e}")
            return False

    def _init_pyttsx3(self) -> bool:
        """Inicializa pyttsx3 como motor TTS de fallback."""
        try:
            import pyttsx3
            engine = pyttsx3.init()

            # Configurar voz masculina
            voices = engine.getProperty('voices')
            for voice in voices:
                if "male" in voice.name.lower() or "david" in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break

            # Velocidad
            engine.setProperty('rate', int(150 * self.rate))
            engine.setProperty('volume', 0.9)

            self._engine = engine
            return True
        except ImportError:
            logger.info("pyttsx3 no instalado.")
            return False
        except Exception as e:
            logger.error(f"Error inicializando pyttsx3: {e}")
            return False

    # ─── Síntesis de voz ──────────────────────────────────────

    def speak(self, text: str, blocking: bool = False) -> None:
        """
        Convierte texto a voz y lo reproduce.

        Args:
            text: Texto a hablar.
            blocking: Si True, espera a que termine de hablar.
        """
        if not self.enabled or not text.strip():
            return

        if self.is_speaking:
            self.stop()

        self._stop_event.clear()

        if blocking:
            self._speak_impl(text)
        else:
            self._speak_thread = threading.Thread(
                target=self._speak_impl,
                args=(text,),
                daemon=True,
            )
            self._speak_thread.start()

    def _speak_impl(self, text: str) -> None:
        """Implementación interna de la síntesis de voz."""
        self.is_speaking = True
        if self.on_speaking_state:
            self.on_speaking_state(True)

        try:
            if self._engine_type == "piper":
                self._speak_piper(text)
            elif self._engine_type == "pyttsx3":
                self._speak_pyttsx3(text)
            else:
                logger.warning("No hay motor TTS disponible.")
        except Exception as e:
            logger.error(f"Error en síntesis de voz: {e}")
        finally:
            self.is_speaking = False
            if self.on_speaking_state:
                self.on_speaking_state(False)

    def _speak_piper(self, text: str) -> None:
        """Síntesis usando Piper TTS."""
        try:
            if self._engine == "piper_python":
                # Usar piper como paquete Python
                import piper as piper_tts
                import wave
                import io

                model_path = Path(PIPER_MODEL_PATH)
                if not model_path.exists():
                    logger.error(f"Modelo Piper no encontrado en: {model_path}")
                    # Fallback a pyttsx3
                    if self._init_pyttsx3():
                        self._engine_type = "pyttsx3"
                        self._speak_pyttsx3(text)
                    return

                voice = piper_tts.PiperVoice.load(str(model_path))
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name
                    with wave.open(f, 'wb') as wav:
                        voice.synthesize(text, wav)

                # Reproducir el archivo
                self._play_audio_file(temp_path)

            else:
                # Usar piper como ejecutable
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name

                cmd = [
                    self._engine,
                    "--model", PIPER_VOICE,
                    "--output_file", temp_path,
                ]

                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                process.communicate(input=text.encode("utf-8"), timeout=30)

                if process.returncode == 0:
                    self._play_audio_file(temp_path)
                else:
                    logger.error("Piper TTS falló. Usando fallback.")
                    if self._init_pyttsx3():
                        self._engine_type = "pyttsx3"
                        self._speak_pyttsx3(text)

        except Exception as e:
            logger.error(f"Error en Piper TTS: {e}")
            # Fallback
            if self._init_pyttsx3():
                self._engine_type = "pyttsx3"
                self._speak_pyttsx3(text)

    def _speak_pyttsx3(self, text: str) -> None:
        """Síntesis usando pyttsx3."""
        try:
            if self._stop_event.is_set():
                return
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            logger.error(f"Error en pyttsx3: {e}")

    def _play_audio_file(self, file_path: str) -> None:
        """Reproduce un archivo de audio WAV."""
        try:
            import sounddevice as sd
            import numpy as np
            import wave

            with wave.open(file_path, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                sr = wf.getframerate()

            if not self._stop_event.is_set():
                sd.play(audio, sr)
                sd.wait()

        except ImportError:
            # Fallback: usar el reproductor del sistema
            try:
                if not self._stop_event.is_set():
                    subprocess.run(
                        ["powershell", "-c",
                         f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()"],
                        timeout=60,
                        capture_output=True,
                    )
            except Exception as e:
                logger.error(f"Error reproduciendo audio: {e}")
        except Exception as e:
            logger.error(f"Error reproduciendo audio: {e}")
        finally:
            # Limpiar archivo temporal
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception:
                pass

    # ─── Control ──────────────────────────────────────────────

    def stop(self) -> None:
        """Detiene la reproducción de voz actual."""
        self._stop_event.set()
        if self._engine_type == "pyttsx3" and self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        self.is_speaking = False
        logger.info("Voz detenida.")

    def toggle(self) -> bool:
        """Alterna entre activar/desactivar TTS. Devuelve el nuevo estado."""
        self.enabled = not self.enabled
        if not self.enabled:
            self.stop()
        logger.info(f"TTS {'activado' if self.enabled else 'desactivado'}.")
        return self.enabled

    def set_enabled(self, enabled: bool) -> None:
        """Activa o desactiva el TTS."""
        self.enabled = enabled
        if not enabled:
            self.stop()

    def set_rate(self, rate: float) -> None:
        """Ajusta la velocidad de habla (0.5 - 2.0)."""
        self.rate = max(0.5, min(2.0, rate))
        if self._engine_type == "pyttsx3" and self._engine:
            self._engine.setProperty('rate', int(150 * self.rate))
        logger.info(f"Velocidad TTS: {self.rate}")
