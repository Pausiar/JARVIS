"""
J.A.R.V.I.S. — Vision Module
Visión multimodal con LLaVA u otro modelo de Ollama.
Permite analizar screenshots reales — no solo OCR de texto.
Entiende iconos, imágenes, colores, layout, contexto visual.
"""

import base64
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import requests

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OLLAMA_HOST, DATA_DIR

logger = logging.getLogger("jarvis.vision")

# Modelo multimodal — se descarga automáticamente si no existe
VISION_MODEL = "llava"  # Alternativas: llava:13b, bakllava, llava-phi3


class VisionEngine:
    """Motor de visión multimodal usando LLaVA (Ollama)."""

    def __init__(self, host: str = None, model: str = None):
        self.host = host or OLLAMA_HOST
        self.model = model or VISION_MODEL
        self._available = None
        logger.info(f"VisionEngine inicializado con modelo: {self.model}")

    # ─── Disponibilidad ───────────────────────────────────────

    def is_available(self) -> bool:
        """Verifica si el modelo de visión está disponible en Ollama."""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                self._available = self.model.split(":")[0] in model_names
                if not self._available:
                    logger.info(
                        f"Modelo de visión '{self.model}' no encontrado. "
                        f"Disponibles: {model_names}. "
                        f"Instálalo con: ollama pull {self.model}"
                    )
                return self._available
        except Exception as e:
            logger.warning(f"Error verificando modelo de visión: {e}")
        self._available = False
        return False

    def ensure_model(self) -> bool:
        """Descarga el modelo de visión si no está disponible."""
        if self.is_available():
            return True
        logger.info(f"Descargando modelo de visión '{self.model}'...")
        try:
            resp = requests.post(
                f"{self.host}/api/pull",
                json={"name": self.model},
                timeout=1800,
                stream=True,
            )
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if "error" in data:
                        logger.error(f"Error descargando modelo: {data['error']}")
                        return False
                    if "completed" in str(status).lower() or "success" in str(status).lower():
                        logger.info(f"Modelo de visión '{self.model}' descargado.")
            self._available = True
            return True
        except Exception as e:
            logger.error(f"Error descargando modelo de visión: {e}")
            return False

    # ─── Captura de pantalla ──────────────────────────────────

    def _capture_screen(self, monitor: int = 0) -> Optional[str]:
        """
        Captura la pantalla y devuelve la ruta del archivo temporal PNG.

        Args:
            monitor: Índice del monitor (0 = principal, -1 = todos).
        """
        try:
            import pyautogui
            from PIL import Image

            temp_path = os.path.join(
                tempfile.gettempdir(), "jarvis_vision_screen.png"
            )

            if monitor == 0 or monitor == -1:
                screenshot = pyautogui.screenshot()
            else:
                # Captura de monitor específico con screeninfo
                try:
                    from screeninfo import get_monitors
                    monitors = get_monitors()
                    if 0 <= monitor < len(monitors):
                        m = monitors[monitor]
                        screenshot = pyautogui.screenshot(
                            region=(m.x, m.y, m.width, m.height)
                        )
                    else:
                        screenshot = pyautogui.screenshot()
                except ImportError:
                    screenshot = pyautogui.screenshot()

            # Redimensionar para no saturar el modelo (max 1280px de ancho)
            max_width = 1280
            if screenshot.width > max_width:
                ratio = max_width / screenshot.width
                new_size = (max_width, int(screenshot.height * ratio))
                screenshot = screenshot.resize(new_size, Image.LANCZOS)

            screenshot.save(temp_path, "PNG")
            return temp_path

        except Exception as e:
            logger.error(f"Error capturando pantalla: {e}")
            return None

    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """Convierte una imagen a base64."""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Error codificando imagen: {e}")
            return None

    # ─── Chat con visión ──────────────────────────────────────

    def analyze_image(
        self,
        prompt: str,
        image_path: str = None,
        monitor: int = 0,
    ) -> str:
        """
        Analiza una imagen (o screenshot) con el modelo multimodal.

        Args:
            prompt: Pregunta o instrucción sobre la imagen.
            image_path: Ruta a la imagen. Si es None, captura la pantalla.
            monitor: Monitor del que capturar (0 = principal).

        Returns:
            Respuesta descriptiva del modelo.
        """
        if not self.is_available():
            return (
                "El modelo de visión no está disponible, señor. "
                f"Instálelo con: ollama pull {self.model}"
            )

        # Obtener imagen
        if image_path and os.path.exists(image_path):
            img_path = image_path
            cleanup = False
        else:
            img_path = self._capture_screen(monitor)
            cleanup = True

        if not img_path:
            return "No se pudo obtener la imagen para analizar."

        img_b64 = self._image_to_base64(img_path)
        if not img_b64:
            return "Error procesando la imagen."

        try:
            # Construir prompt en español
            full_prompt = (
                f"Responde en español. Eres JARVIS, un asistente de IA. "
                f"Analiza esta imagen y responde: {prompt}"
            )

            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": full_prompt,
                            "images": [img_b64],
                        }
                    ],
                    "stream": True,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 512,
                    },
                },
                timeout=120,
                stream=True,
            )

            if resp.status_code == 200:
                result = ""
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            result += token
                        if data.get("done", False):
                            break
                logger.info(f"Análisis visual completado ({len(result)} chars)")
                return result
            else:
                return f"Error del modelo de visión (HTTP {resp.status_code})"

        except requests.Timeout:
            return "El análisis visual ha tardado demasiado."
        except Exception as e:
            logger.error(f"Error en análisis visual: {e}")
            return f"Error analizando imagen: {e}"
        finally:
            if cleanup and img_path:
                try:
                    os.remove(img_path)
                except Exception:
                    pass

    def describe_screen(self, monitor: int = 0) -> str:
        """Describe lo que hay en la pantalla actual."""
        return self.analyze_image(
            "Describe detalladamente qué se ve en esta pantalla. "
            "Menciona qué aplicación está abierta, qué textos/iconos/botones "
            "hay visibles, y qué parece estar haciendo el usuario.",
            monitor=monitor,
        )

    def find_element(self, description: str, monitor: int = 0) -> str:
        """
        Encuentra un elemento visual por descripción.
        Devuelve una descripción de dónde está y qué hay alrededor.
        """
        return self.analyze_image(
            f"Necesito encontrar esto en la pantalla: '{description}'. "
            f"Describe exactamente dónde está (arriba/abajo, izquierda/derecha, "
            f"centro), qué texto tiene cerca, y cómo se ve el elemento.",
            monitor=monitor,
        )

    def analyze_local_image(self, image_path: str, question: str = "") -> str:
        """
        Analiza una imagen local del disco.

        Args:
            image_path: Ruta a la imagen (PNG, JPG, BMP, etc.).
            question: Pregunta sobre la imagen.
        """
        if not os.path.exists(image_path):
            return f"Imagen no encontrada: {image_path}"

        prompt = question or (
            "Describe detalladamente qué se ve en esta imagen. "
            "Incluye texto, objetos, colores y cualquier detalle relevante."
        )
        return self.analyze_image(prompt, image_path=image_path)

    def compare_screens(self, description: str = "") -> str:
        """
        Captura la pantalla actual y la compara con la expectativa del usuario.
        Útil para verificar si una acción tuvo efecto.
        """
        prompt = (
            "Analiza esta captura de pantalla. "
            f"El usuario esperaba ver: '{description}'. "
            "¿La pantalla muestra lo que se esperaba? "
            "¿Hay algún error, diálogo o popup inesperado?"
        )
        return self.analyze_image(prompt)

    def read_image_text(self, image_path: str) -> str:
        """
        Lee todo el texto de una imagen local usando visión multimodal.
        Complementa al OCR para capturas con fuentes decorativas, memes, etc.
        """
        if not os.path.exists(image_path):
            return f"Imagen no encontrada: {image_path}"

        return self.analyze_image(
            "Extrae y transcribe TODO el texto visible en esta imagen. "
            "Incluye textos en botones, títulos, subtítulos, cuerpo de texto, "
            "watermarks, etc. Responde solo con el texto encontrado.",
            image_path=image_path,
        )
