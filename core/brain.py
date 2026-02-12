"""
J.A.R.V.I.S. — Brain (Cerebro)
Motor de inteligencia dual: Local (Ollama) y Cloud (Groq/Gemini).
Gestiona la conversación, personalidad y razonamiento de JARVIS.
"""

import json
import logging
import re
import time
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
    BRAIN_MODE,
    CLOUD_PROVIDER,
    GROQ_API_KEY,
    GROQ_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)

logger = logging.getLogger("jarvis.brain")


class JarvisBrain:
    """Motor de inteligencia de JARVIS — dual: local (Ollama) o cloud (Groq/Gemini)."""

    # ─── Configuración de proveedores cloud ───────────────────
    CLOUD_ENDPOINTS = {
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    }

    def __init__(self, model: str = None, host: str = None):
        self.model = model or OLLAMA_MODEL
        self.host = host or OLLAMA_HOST
        self.system_prompt = JARVIS_SYSTEM_PROMPT
        self.conversation_history: list[dict] = []
        self.max_history = 6
        self._available = None
        self._available_checked_at = 0
        self._warmed_up = False

        # Modo de operación: "local" o "cloud"
        self.mode = USER_CONFIG.get("brain_mode", BRAIN_MODE)
        self.cloud_provider = USER_CONFIG.get("cloud_provider", CLOUD_PROVIDER)
        self.groq_api_key = USER_CONFIG.get("groq_api_key", GROQ_API_KEY)
        self.groq_model = USER_CONFIG.get("groq_model", GROQ_MODEL)
        self.gemini_api_key = USER_CONFIG.get("gemini_api_key", GEMINI_API_KEY)
        self.gemini_model = USER_CONFIG.get("gemini_model", GEMINI_MODEL)

        mode_label = f"CLOUD ({self.cloud_provider})" if self.mode == "cloud" else f"LOCAL ({self.model})"
        logger.info(f"JarvisBrain inicializado en modo: {mode_label}")

    def set_mode(self, mode: str) -> str:
        """Cambia entre modo 'local' y 'cloud'."""
        mode = mode.lower().strip()
        if mode not in ("local", "cloud"):
            return f"Modo '{mode}' no válido. Use 'local' o 'cloud'."

        old_mode = self.mode
        self.mode = mode

        # Persistir en config.json
        try:
            from config import load_config, save_config
            cfg = load_config()
            cfg["brain_mode"] = mode
            save_config(cfg)
        except Exception as e:
            logger.warning(f"No se pudo guardar modo en config: {e}")

        if mode == "cloud":
            provider = self.cloud_provider
            has_key = bool(self._get_cloud_api_key())
            if not has_key:
                return (
                    f"Modo cambiado a CLOUD ({provider}), pero falta la API key. "
                    f"Configure '{provider}_api_key' en data/config.json o config.py."
                )
            return f"Modo cambiado a CLOUD ({provider}). Las respuestas serán más rápidas, señor."
        else:
            return "Modo cambiado a LOCAL (Ollama). Usando procesamiento en su equipo, señor."

    def set_cloud_provider(self, provider: str) -> str:
        """Cambia el proveedor cloud (groq o gemini)."""
        provider = provider.lower().strip()
        if provider not in ("groq", "gemini"):
            return f"Proveedor '{provider}' no soportado. Use 'groq' o 'gemini'."
        self.cloud_provider = provider
        try:
            from config import load_config, save_config
            cfg = load_config()
            cfg["cloud_provider"] = provider
            save_config(cfg)
        except Exception:
            pass
        return f"Proveedor cloud cambiado a {provider}."

    def _get_cloud_api_key(self) -> str:
        """Obtiene la API key del proveedor cloud actual."""
        if self.cloud_provider == "groq":
            return self.groq_api_key
        elif self.cloud_provider == "gemini":
            return self.gemini_api_key
        return ""

    def get_mode_info(self) -> str:
        """Devuelve info sobre el modo actual."""
        if self.mode == "cloud":
            provider = self.cloud_provider
            has_key = "✅" if self._get_cloud_api_key() else "❌ sin API key"
            model = self.groq_model if provider == "groq" else self.gemini_model
            return f"Modo: CLOUD | Proveedor: {provider} | Modelo: {model} | API key: {has_key}"
        else:
            return f"Modo: LOCAL | Modelo: {self.model} | Host: {self.host}"

    def warmup(self) -> bool:
        """Pre-carga el modelo en RAM sin generar texto.
        
        Usa el endpoint /api/generate con prompt vacío, que solo
        carga el modelo y lo mantiene en RAM (keep_alive). No genera
        tokens, así que es rápido y no bloquea peticiones posteriores.
        """
        if self._warmed_up:
            return True
        try:
            logger.info("Cargando modelo en RAM...")
            # Prompt vacío = solo cargar modelo, no generar nada
            resp = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": "",
                    "keep_alive": "15m",
                },
                timeout=120,
            )
            self._warmed_up = resp.status_code == 200
            if self._warmed_up:
                logger.info("Modelo cargado en RAM y listo.")
            return self._warmed_up
        except Exception as e:
            logger.warning(f"Error cargando modelo: {e}")
            return False

    # ─── Verificación de disponibilidad ───────────────────────

    def is_available(self) -> bool:
        """Verifica si Ollama está corriendo y el modelo está disponible.
        
        Cachea el resultado durante 30s para evitar llamadas repetidas
        al API que podrían competir con peticiones de generación.
        """
        now = time.time()
        # Si ya verificamos recientemente y estaba disponible, no re-chequear
        if self._available and (now - self._available_checked_at) < 30:
            return True

        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                self._available = self.model in model_names
                self._available_checked_at = now
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
        Envía un mensaje al LLM y obtiene la respuesta.
        Enruta automáticamente entre modo local (Ollama) y cloud (Groq/Gemini).
        """
        if context:
            full_message = f"[CONTEXTO ADICIONAL: {context}]\n\nUsuario: {user_message}"
        else:
            full_message = user_message

        messages = self._build_messages(full_message)

        # Enrutar según modo
        if self.mode == "cloud":
            result = self._chat_cloud(messages)
        else:
            result = self._chat_local(messages)

        if result and not result.startswith(("Me temo", "No he podido", "La respuesta", "Error")):
            # Guardar en historial solo si fue exitoso
            self.conversation_history.append(
                {"role": "user", "content": user_message}
            )
            self.conversation_history.append(
                {"role": "assistant", "content": result}
            )

        return result

    # ─── Chat Cloud (Groq / Gemini) ──────────────────────────

    def _chat_cloud(self, messages: list[dict]) -> str:
        """Chat usando API cloud (Groq o Gemini). Rápido, sin consumo local."""
        api_key = self._get_cloud_api_key()
        if not api_key:
            return (
                f"No hay API key configurada para {self.cloud_provider}, señor. "
                f"Añada '{self.cloud_provider}_api_key' en data/config.json."
            )

        if self.cloud_provider == "groq":
            return self._chat_groq(messages, api_key)
        elif self.cloud_provider == "gemini":
            return self._chat_gemini(messages, api_key)
        else:
            return f"Proveedor cloud '{self.cloud_provider}' no soportado."

    def _chat_groq(self, messages: list[dict], api_key: str) -> str:
        """Chat con Groq API (formato OpenAI-compatible)."""
        try:
            # Calcular max_tokens dinámicamente:
            # - Mensajes largos (ejercicios, documentos) → necesitan respuestas largas
            # - Chat normal → 1024 es suficiente
            user_content = messages[-1].get("content", "") if messages else ""
            if len(user_content) > 2000:
                max_tokens = 4096  # Respuesta larga para ejercicios/documentos
                timeout = 60  # Más tiempo para respuestas largas
            else:
                max_tokens = 1024
                timeout = 30

            resp = requests.post(
                self.CLOUD_ENDPOINTS["groq"],
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.groq_model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": max_tokens,
                },
                timeout=timeout,
            )

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(f"Groq: respuesta de {len(content)} chars")
                return content
            elif resp.status_code == 429:
                logger.warning("Groq: rate limit alcanzado")
                return "He alcanzado el límite de peticiones por minuto, señor. Espere un momento."
            elif resp.status_code == 401:
                logger.error("Groq: API key inválida")
                return "La API key de Groq no es válida, señor. Verifique la configuración."
            else:
                error = resp.text[:200]
                logger.error(f"Groq error HTTP {resp.status_code}: {error}")
                return f"Error con Groq (HTTP {resp.status_code}), señor."

        except requests.Timeout:
            return "Groq ha tardado demasiado en responder, señor."
        except requests.ConnectionError:
            return "No puedo conectar con Groq, señor. Verifique su conexión a internet."
        except Exception as e:
            logger.error(f"Error con Groq: {e}")
            return f"Error inesperado con Groq: {e}"

    def _chat_gemini(self, messages: list[dict], api_key: str) -> str:
        """Chat con Google Gemini API."""
        try:
            # Convertir formato OpenAI → formato Gemini
            gemini_contents = []
            system_instruction = None

            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    system_instruction = content
                elif role == "user":
                    gemini_contents.append({
                        "role": "user",
                        "parts": [{"text": content}]
                    })
                elif role == "assistant":
                    gemini_contents.append({
                        "role": "model",
                        "parts": [{"text": content}]
                    })

            url = self.CLOUD_ENDPOINTS["gemini"].format(model=self.gemini_model)
            url += f"?key={api_key}"

            body = {
                "contents": gemini_contents,
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024,
                },
            }
            if system_instruction:
                body["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }

            resp = requests.post(url, json=body, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    text = "".join(p.get("text", "") for p in parts)
                    logger.info(f"Gemini: respuesta de {len(text)} chars")
                    return text
                return "No he obtenido respuesta de Gemini, señor."
            elif resp.status_code == 429:
                return "He alcanzado el límite de Gemini, señor. Espere un momento."
            elif resp.status_code in (401, 403):
                return "La API key de Gemini no es válida, señor. Verifique la configuración."
            else:
                error = resp.text[:200]
                logger.error(f"Gemini error HTTP {resp.status_code}: {error}")
                return f"Error con Gemini (HTTP {resp.status_code}), señor."

        except requests.Timeout:
            return "Gemini ha tardado demasiado en responder, señor."
        except requests.ConnectionError:
            return "No puedo conectar con Gemini, señor. Verifique su conexión a internet."
        except Exception as e:
            logger.error(f"Error con Gemini: {e}")
            return f"Error inesperado con Gemini: {e}"

    # ─── Chat Local (Ollama) ─────────────────────────────────

    def _chat_local(self, messages: list[dict]) -> str:
        """Chat usando Ollama local con streaming y reintentos."""
        if not self.is_available():
            return (
                "Me temo que no puedo conectar con Ollama, señor. "
                "¿Podría verificar que esté ejecutándose? "
                "O cambie a modo cloud: 'modo cloud'."
            )

        max_retries = 2
        for attempt in range(max_retries):
          try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "keep_alive": "15m",
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 512,
                        "num_ctx": 2048,
                    },
                },
                timeout=(10, 90),  # (connect 10s, read 90s por chunk)
                stream=True,
            )

            if resp.status_code == 200:
                assistant_message = ""
                last_token_time = time.time()
                start_time = last_token_time
                # Timeouts basados en INACTIVIDAD, no en tiempo total:
                # - 60s sin recibir ningún token (carga del modelo)
                # - 15s sin token nuevo una vez empezó a generar
                # - 90s máximo absoluto como red de seguridad
                idle_timeout_initial = 60
                idle_timeout_streaming = 15
                max_total_seconds = 90

                has_started = False

                for line in resp.iter_lines():
                    now = time.time()

                    if line:
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        token = data.get("message", {}).get("content", "")
                        if token:
                            assistant_message += token
                            last_token_time = now
                            has_started = True
                        if data.get("done", False):
                            break

                    # Comprobar timeouts
                    idle = now - last_token_time
                    total = now - start_time

                    if total > max_total_seconds:
                        logger.warning(f"LLM: límite total de {max_total_seconds}s alcanzado")
                        resp.close()
                        break

                    if has_started and idle > idle_timeout_streaming:
                        logger.warning(f"LLM: sin tokens durante {idle:.0f}s (streaming)")
                        resp.close()
                        break

                    if not has_started and idle > idle_timeout_initial:
                        logger.warning(f"LLM: sin respuesta tras {idle:.0f}s esperando primer token")
                        resp.close()
                        break

                elapsed = time.time() - start_time

                if not assistant_message:
                    if attempt < max_retries - 1:
                        logger.warning(f"LLM: respuesta vacía tras {elapsed:.1f}s, reintentando...")
                        time.sleep(1)
                        continue  # Reintentar
                    logger.error(f"LLM: respuesta vacía tras {elapsed:.1f}s (sin reintentos)")
                    return "No he podido generar una respuesta, señor. Inténtelo de nuevo."

                logger.info(f"Respuesta local ({len(assistant_message)} chars, {elapsed:.1f}s)")
                return assistant_message
            else:
                error_msg = f"Error del LLM (HTTP {resp.status_code}): {resp.text}"
                logger.error(error_msg)
                if attempt < max_retries - 1:
                    logger.info("Reintentando...")
                    time.sleep(2)
                    continue
                return (
                    "Me temo que he tenido un problema técnico, señor. "
                    "No he podido procesar su solicitud."
                )

          except requests.ConnectionError:
            logger.error("No se puede conectar con Ollama.")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return (
                "Me temo que no puedo conectar con mi motor de razonamiento, señor. "
                "¿Podría verificar que Ollama esté ejecutándose?"
            )
          except requests.Timeout:
            logger.warning(f"Timeout HTTP con Ollama (intento {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return (
                "La respuesta está tardando demasiado, señor. "
                "Intente de nuevo con una pregunta más corta."
            )
          except Exception as e:
            logger.error(f"Error inesperado en chat: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return (
                f"Me temo que algo inesperado ha ocurrido, señor. "
                f"Error: {str(e)}"
            )

        # Should not reach here but just in case
        return "No he podido conectar con el modelo, señor."

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
                    "keep_alive": "10m",
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 1024,
                        "num_ctx": 2048,
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
