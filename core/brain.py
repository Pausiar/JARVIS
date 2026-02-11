"""
J.A.R.V.I.S. — Brain (Cerebro)
Integración con Ollama para LLM local.
Gestiona la conversación, personalidad y razonamiento de JARVIS.
"""

import json
import logging
import re
from typing import Optional, Generator

import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    JARVIS_SYSTEM_PROMPT,
    USER_CONFIG,
)

logger = logging.getLogger("jarvis.brain")


class JarvisBrain:
    """Motor de inteligencia de JARVIS usando Ollama (LLM local)."""

    def __init__(self, model: str = None, host: str = None):
        self.model = model or OLLAMA_MODEL
        self.host = host or OLLAMA_HOST
        self.system_prompt = JARVIS_SYSTEM_PROMPT
        self.conversation_history: list[dict] = []
        self.max_history = 10  # Máximo de mensajes en el historial activo
        self._available = None
        self._warmed_up = False
        logger.info(f"JarvisBrain inicializado con modelo: {self.model}")

    def warmup(self) -> bool:
        """Calienta el modelo con un mensaje corto para evitar el lag de primera carga."""
        if self._warmed_up:
            return True
        try:
            logger.info("Calentando modelo (primera carga)...")
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Hola"}],
                    "stream": False,
                    "options": {"num_predict": 1},
                },
                timeout=120,
            )
            self._warmed_up = resp.status_code == 200
            if self._warmed_up:
                logger.info("Modelo calentado y listo.")
            return self._warmed_up
        except Exception as e:
            logger.warning(f"Error calentando modelo: {e}")
            return False

    # ─── Verificación de disponibilidad ───────────────────────

    def is_available(self) -> bool:
        """Verifica si Ollama está corriendo y el modelo está disponible."""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                self._available = self.model in model_names
                if not self._available:
                    logger.warning(
                        f"Modelo '{self.model}' no encontrado. "
                        f"Modelos disponibles: {model_names}"
                    )
                return self._available
        except requests.ConnectionError:
            logger.warning("Ollama no responde. Intentando reiniciar...")
            if self._try_restart_ollama():
                return self.is_available()  # Reintentar una vez
            logger.error("No se pudo conectar con Ollama.")
        except Exception as e:
            logger.error(f"Error verificando Ollama: {e}")
        self._available = False
        return False

    def _try_restart_ollama(self) -> bool:
        """Intenta reiniciar Ollama automáticamente."""
        try:
            import subprocess
            import time
            logger.info("Intentando iniciar Ollama...")
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x00000008,  # DETACHED_PROCESS en Windows
            )
            # Esperar a que arranque
            for _ in range(10):
                time.sleep(1)
                try:
                    resp = requests.get(f"{self.host}/api/tags", timeout=2)
                    if resp.status_code == 200:
                        logger.info("Ollama reiniciado correctamente.")
                        return True
                except Exception:
                    continue
            logger.warning("Ollama no pudo arrancarse automáticamente.")
        except Exception as e:
            logger.warning(f"Error intentando reiniciar Ollama: {e}")
        return False

    def list_models(self) -> list[str]:
        """Lista los modelos disponibles en Ollama."""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m.get("name", "") for m in models]
        except Exception as e:
            logger.error(f"Error listando modelos: {e}")
        return []

    def pull_model(self, model_name: str = None) -> bool:
        """Descarga un modelo en Ollama."""
        model = model_name or self.model
        logger.info(f"Descargando modelo '{model}'...")
        try:
            resp = requests.post(
                f"{self.host}/api/pull",
                json={"name": model},
                timeout=600,
                stream=True,
            )
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if "error" in data:
                        logger.error(f"Error descargando modelo: {data['error']}")
                        return False
                    logger.info(f"Pull: {status}")
            logger.info(f"Modelo '{model}' descargado correctamente.")
            return True
        except Exception as e:
            logger.error(f"Error descargando modelo: {e}")
            return False

    # ─── Chat con el LLM ─────────────────────────────────────

    def _build_messages(self, user_message: str) -> list[dict]:
        """Construye la lista de mensajes para la API de Ollama."""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Incluir historial de conversación reciente
        history_slice = self.conversation_history[-self.max_history:]
        messages.extend(history_slice)

        # Agregar mensaje actual del usuario
        messages.append({"role": "user", "content": user_message})
        return messages

    def chat(self, user_message: str, context: str = "") -> str:
        """
        Envía un mensaje al LLM y obtiene la respuesta completa.

        Args:
            user_message: Mensaje del usuario.
            context: Contexto adicional (ej: contenido de un archivo).

        Returns:
            Respuesta de JARVIS como string.
        """
        # Check availability first
        if not self.is_available():
            return (
                "Me temo que no puedo conectar con mi motor de razonamiento, señor. "
                "¿Podría verificar que Ollama esté ejecutándose con el modelo mistral?"
            )

        if context:
            full_message = f"[CONTEXTO ADICIONAL: {context}]\n\nUsuario: {user_message}"
        else:
            full_message = user_message

        messages = self._build_messages(full_message)

        try:
            # Usar streaming interno para evitar timeout por bloqueo total
            # El servidor empieza a devolver tokens de inmediato
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 200,
                        "num_ctx": 2048,
                    },
                },
                timeout=60,
                stream=True,
            )

            if resp.status_code == 200:
                assistant_message = ""
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            assistant_message += token
                        if data.get("done", False):
                            break

                # Guardar en historial
                self.conversation_history.append(
                    {"role": "user", "content": user_message}
                )
                self.conversation_history.append(
                    {"role": "assistant", "content": assistant_message}
                )

                logger.info(f"Respuesta generada ({len(assistant_message)} chars)")
                return assistant_message
            else:
                error_msg = f"Error del LLM (HTTP {resp.status_code}): {resp.text}"
                logger.error(error_msg)
                return (
                    "Me temo que he tenido un problema técnico, señor. "
                    "No he podido procesar su solicitud."
                )

        except requests.ConnectionError:
            logger.error("No se puede conectar con Ollama.")
            return (
                "Me temo que no puedo conectar con mi motor de razonamiento, señor. "
                "¿Podría verificar que Ollama esté ejecutándose?"
            )
        except requests.Timeout:
            logger.error("Timeout en la respuesta del LLM.")
            return (
                "La solicitud ha tardado demasiado, señor. "
                "Permítame intentarlo de nuevo si lo desea."
            )
        except Exception as e:
            logger.error(f"Error inesperado en chat: {e}")
            return (
                f"Me temo que algo inesperado ha ocurrido, señor. "
                f"Error: {str(e)}"
            )

    def chat_stream(self, user_message: str, context: str = "") -> Generator[str, None, None]:
        """
        Envía un mensaje al LLM y obtiene la respuesta en streaming.

        Yields:
            Tokens de la respuesta uno a uno.
        """
        if context:
            full_message = f"[CONTEXTO ADICIONAL: {context}]\n\nUsuario: {user_message}"
        else:
            full_message = user_message

        messages = self._build_messages(full_message)
        full_response = ""

        try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 1024,
                    },
                },
                timeout=120,
                stream=True,
            )

            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        full_response += token
                        yield token
                    if data.get("done", False):
                        break

            # Guardar en historial
            self.conversation_history.append(
                {"role": "user", "content": user_message}
            )
            self.conversation_history.append(
                {"role": "assistant", "content": full_response}
            )

        except Exception as e:
            logger.error(f"Error en streaming: {e}")
            yield f"Error: {str(e)}"

    # ─── Gestión de historial ─────────────────────────────────

    def clear_history(self) -> None:
        """Limpia el historial de conversación."""
        self.conversation_history.clear()
        logger.info("Historial de conversación limpiado.")

    def get_history(self) -> list[dict]:
        """Devuelve el historial de conversación."""
        return self.conversation_history.copy()

    def set_history(self, history: list[dict]) -> None:
        """Establece el historial de conversación (para restaurar sesiones)."""
        self.conversation_history = history
        logger.info(f"Historial restaurado ({len(history)} mensajes).")

    def add_context(self, context: str) -> None:
        """Agrega contexto adicional al sistema prompt."""
        self.conversation_history.append(
            {"role": "system", "content": f"[CONTEXTO]: {context}"}
        )

    # ─── Extracción de acciones ───────────────────────────────

    @staticmethod
    def extract_actions(response: str) -> list[dict]:
        """
        Extrae acciones JSON de la respuesta de JARVIS.

        Returns:
            Lista de diccionarios con las acciones a ejecutar.
        """
        actions = []
        pattern = r'\[ACTION:(.*?)\]'
        matches = re.findall(pattern, response)
        for match in matches:
            try:
                action = json.loads(match)
                actions.append(action)
            except json.JSONDecodeError:
                logger.warning(f"No se pudo parsear acción: {match}")
        return actions

    @staticmethod
    def clean_response(response: str) -> str:
        """Elimina las etiquetas de acción de la respuesta para mostrar al usuario."""
        pattern = r'\[ACTION:.*?\]\s*'
        return re.sub(pattern, '', response).strip()

    # ─── Análisis de intención rápido (sin LLM) ──────────────

    @staticmethod
    def quick_intent(text: str) -> Optional[dict]:
        """
        Intenta detectar intenciones simples sin usar el LLM.
        Para comandos directos como "abre Chrome", "sube el volumen", etc.

        Returns:
            Dict con módulo y acción, o None si no se detecta.
        """
        text_lower = text.lower().strip()

        # Patrones de apertura de aplicaciones
        open_patterns = [
            r"(?:abre|abrir|ejecuta|ejecutar|lanza|lanzar|inicia|iniciar|open|launch|start)\s+(.+)",
        ]
        for pattern in open_patterns:
            match = re.match(pattern, text_lower)
            if match:
                app = match.group(1).strip()
                return {
                    "module": "system_control",
                    "function": "open_application",
                    "params": {"app_name": app},
                }

        # Cierre de aplicaciones
        close_patterns = [
            r"(?:cierra|cerrar|close|kill|termina|terminar)\s+(.+)",
        ]
        for pattern in close_patterns:
            match = re.match(pattern, text_lower)
            if match:
                app = match.group(1).strip()
                return {
                    "module": "system_control",
                    "function": "close_application",
                    "params": {"app_name": app},
                }

        # Control de volumen
        if any(w in text_lower for w in ["sube el volumen", "volume up", "más volumen"]):
            return {"module": "system_control", "function": "volume_up", "params": {}}
        if any(w in text_lower for w in ["baja el volumen", "volume down", "menos volumen"]):
            return {"module": "system_control", "function": "volume_down", "params": {}}
        if any(w in text_lower for w in ["silencia", "mute", "silencio"]):
            return {"module": "system_control", "function": "mute", "params": {}}

        # Control del sistema
        if any(w in text_lower for w in ["apaga el pc", "apagar", "shutdown"]):
            return {"module": "system_control", "function": "shutdown", "params": {}}
        if any(w in text_lower for w in ["reinicia", "reiniciar", "restart"]):
            return {"module": "system_control", "function": "restart", "params": {}}
        if any(w in text_lower for w in ["captura de pantalla", "screenshot", "pantallazo"]):
            return {"module": "system_control", "function": "screenshot", "params": {}}

        # Hora
        if any(w in text_lower for w in ["qué hora es", "hora actual", "what time"]):
            return {"module": "system_control", "function": "get_time", "params": {}}

        return None
