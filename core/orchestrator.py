"""
J.A.R.V.I.S. — Orchestrator
Orquesta los módulos según la petición del usuario.
Conecta el cerebro (LLM) con los módulos de acción.
"""

import logging
import re
import time
import datetime
from typing import Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.brain import JarvisBrain
from core.command_parser import CommandParser, CommandIntent
from modules.file_manager import FileManager
from modules.document_processor import DocumentProcessor
from modules.system_control import SystemControl
from modules.web_search import WebSearch
from modules.email_manager import EmailManager
from modules.code_executor import CodeExecutor
from modules.automation import AutomationManager
from modules.memory import Memory

logger = logging.getLogger("jarvis.orchestrator")


class Orchestrator:
    """
    Orquesta JARVIS: recibe input del usuario, lo interpreta,
    ejecuta las acciones necesarias y devuelve la respuesta.
    """

    def __init__(self, brain: JarvisBrain):
        self.brain = brain
        self.parser = CommandParser()
        self.memory = Memory()

        # Módulos
        self.modules = {
            "file_manager": FileManager(),
            "document_processor": DocumentProcessor(),
            "system_control": SystemControl(),
            "web_search": WebSearch(),
            "email_manager": EmailManager(),
            "code_executor": CodeExecutor(),
            "automation": AutomationManager(),
            "memory": self.memory,
        }

        # Pasar brain reference a SystemControl para features avanzados
        sc = self.modules.get("system_control")
        if sc and hasattr(sc, 'set_brain'):
            sc.set_brain(self.brain)

        logger.info("Orchestrator inicializado con todos los módulos.")

    # ─── Procesamiento principal ──────────────────────────────

    def process(self, user_input: str) -> str:
        """
        Procesa la entrada del usuario y devuelve la respuesta de JARVIS.

        Flujo:
        1. Guardar en memoria
        2. Intentar detección rápida de comandos
        3. Si no se detecta, usar el LLM
        4. Ejecutar acciones si las hay
        5. Devolver respuesta

        Args:
            user_input: Texto del usuario (ya transcrito si fue voz).

        Returns:
            Respuesta de JARVIS como string.
        """
        user_input = user_input.strip()
        if not user_input:
            return "No he escuchado nada, señor. ¿Podría repetirlo?"

        logger.info(f"Procesando: '{user_input}'")

        # Guardar en memoria
        self.memory.save_message("user", user_input)

        # Verificar saludos / despedidas
        if self.parser.is_greeting(user_input):
            response = self._handle_greeting()
            self.memory.save_message("assistant", response)
            return response

        if self.parser.is_farewell(user_input):
            response = self._handle_farewell()
            self.memory.save_message("assistant", response)
            return response

        # Paso 1: Detección rápida — comandos compuestos ("abre X y busca Y")
        compound_intents = self.parser.parse_compound(user_input)
        if compound_intents:
            results = []
            unhandled_parts = []
            for ci in compound_intents:
                if ci.confidence >= 0.8:
                    logger.info(f"Intención compuesta detectada: {ci}")
                    r = self._execute_intent(ci)
                    if r:
                        results.append(r)

            # Detectar partes del texto que no se pudieron parsear
            # pero que podrían ser interacciones dentro de apps
            _action_verbs_re = re.compile(
                r"(?:entra|entrar|encuentra|encontrar|navega|navegar|"
                r"haz\s+clic|pulsa|pincha|selecciona|escribe\s+en)\s+.+",
                re.IGNORECASE,
            )
            # Buscar fragmentos no reconocidos en el texto original
            text_parts = re.split(
                r"\s+y\s+(?:luego\s+|después\s+|también\s+)?|\s*,\s*(?:y\s+)?",
                user_input, flags=re.IGNORECASE,
            )
            for part in text_parts:
                part = part.strip()
                if part and _action_verbs_re.search(part):
                    if not self.parser._match_patterns(part):
                        # Intentar ejecutar como interacción dentro de app
                        sc = self.modules.get("system_control")
                        if sc:
                            try:
                                interact_result = sc.interact_with_app(part)
                                results.append(interact_result)
                            except Exception as e:
                                logger.warning(f"Error en interacción: {e}")
                                unhandled_parts.append(part)
                        else:
                            unhandled_parts.append(part)

            if results:
                response = "Hecho, señor. " + " | ".join(results)
                if unhandled_parts:
                    response += (
                        "\n\nAlgunas acciones no se pudieron completar: "
                        + "; ".join(f'"{p}"' for p in unhandled_parts)
                    )
                self.memory.save_message("assistant", response)
                return response

        # Paso 1b: Detección simple por patrones
        intent = self.parser.parse(user_input)
        if intent and intent.confidence >= 0.8:
            logger.info(f"Intención directa detectada: {intent}")
            result = self._execute_intent(intent)
            if result:
                response = f"Hecho, señor. {result}"
                self.memory.save_message("assistant", response)
                return response

        # Paso 2: Usar el LLM para entender la petición
        # Detectar si el usuario se refiere a lo que hay en pantalla
        needs_screen = bool(re.search(
            r"(?:qu[eé]|que)\s+(?:hay|pone|dice|se\s+ve|aparece)"
            r"|(?:en\s+)?(?:la\s+)?pantalla"
            r"|(?:lee|leer|dime)\s+(?:lo\s+que|qu[eé]|que)\s+(?:hay|pone|dice)"
            r"|(?:describe|describir)\s+(?:lo\s+que|la)\s+(?:pantalla|se\s+ve)",
            user_input, re.IGNORECASE
        ))
        context = self._build_context(include_screen=needs_screen)
        llm_response = self.brain.chat(user_input, context=context)

        # Paso 3: Extraer y ejecutar acciones del LLM
        llm_intents = self.parser.parse_llm_actions(llm_response)
        action_results = []
        for llm_intent in llm_intents:
            result = self._execute_intent(llm_intent)
            if result:
                action_results.append(result)

        # Paso 4: Limpiar y devolver respuesta
        clean_response = self.brain.clean_response(llm_response)

        # Si hubo acciones ejecutadas, agregar info
        if action_results:
            extra_info = " | ".join(action_results)
            if extra_info not in clean_response:
                clean_response += f"\n\n[Resultado: {extra_info}]"

        self.memory.save_message("assistant", clean_response)
        return clean_response

    # ─── Ejecución de intenciones ─────────────────────────────

    def _execute_intent(self, intent: CommandIntent) -> Optional[str]:
        """Ejecuta una intención en el módulo correspondiente."""
        module_name = intent.module
        function_name = intent.function
        params = intent.params

        # Manejar funciones del orchestrator (workflows multi-paso)
        if module_name == "orchestrator":
            if hasattr(self, function_name):
                try:
                    func = getattr(self, function_name)
                    result = func(**params)
                    logger.info(f"Workflow ejecutado: {function_name}")
                    return str(result) if result is not None else "Acción completada."
                except Exception as e:
                    logger.error(f"Error en workflow {function_name}: {e}")
                    return f"Error: {e}"
            logger.warning(f"Workflow desconocido: {function_name}")
            return None

        if module_name not in self.modules:
            logger.warning(f"Módulo desconocido: {module_name}")
            return None

        module = self.modules[module_name]

        if not hasattr(module, function_name):
            logger.warning(
                f"Función desconocida: {module_name}.{function_name}"
            )
            return None

        try:
            func = getattr(module, function_name)
            result = func(**params)
            logger.info(
                f"Acción ejecutada: {module_name}.{function_name} → {str(result)[:200]}"
            )
            return str(result) if result is not None else "Acción completada."
        except TypeError as e:
            logger.error(
                f"Error de parámetros en {module_name}.{function_name}: {e}"
            )
            return f"Error: parámetros incorrectos ({e})"
        except Exception as e:
            logger.error(
                f"Error ejecutando {module_name}.{function_name}: {e}"
            )
            return f"Error ejecutando la acción: {e}"

    # ─── Helpers ──────────────────────────────────────────────

    def _build_context(self, include_screen: bool = False) -> str:
        """Construye contexto adicional para el LLM."""
        context_parts = []

        # Hora y fecha
        now = datetime.datetime.now()
        context_parts.append(
            f"Fecha y hora actual: {now.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        # Info del usuario
        user_name = self.memory.get_preference("user_name")
        if user_name:
            context_parts.append(f"Nombre del usuario: {user_name}")

        # Conversaciones recientes (resumen)
        recent = self.memory.get_recent_messages(5)
        if recent:
            context_parts.append(
                "Mensajes recientes:\n"
                + "\n".join(f"- {m['role']}: {m['content'][:100]}" for m in recent)
            )

        # Contexto visual de pantalla (si se solicita)
        if include_screen:
            sc = self.modules.get("system_control")
            if sc and hasattr(sc, 'get_screen_text'):
                try:
                    screen_text = sc.get_screen_text()
                    if screen_text and not screen_text.startswith("No se"):
                        if len(screen_text) > 3000:
                            screen_text = screen_text[:3000] + "\n[... texto truncado ...]"
                        context_parts.append(
                            f"Texto visible en la pantalla actual:\n{screen_text}"
                        )
                except Exception as e:
                    logger.warning(f"Error obteniendo contexto de pantalla: {e}")

        return "\n".join(context_parts)

    def _enhance_response(self, user_input: str, action_result: str) -> str:
        """
        Genera una respuesta JARVIS-style para un resultado de acción.
        No usa el LLM para evitar latencia — responde directamente.
        """
        return f"Hecho, señor. {action_result}"

    def _handle_greeting(self) -> str:
        """Responde a un saludo."""
        now = datetime.datetime.now()
        hour = now.hour

        if hour < 12:
            time_greeting = "Buenos días"
        elif hour < 20:
            time_greeting = "Buenas tardes"
        else:
            time_greeting = "Buenas noches"

        return (
            f"{time_greeting}, señor. JARVIS a su servicio. "
            "¿En qué puedo asistirle hoy?"
        )

    def _handle_farewell(self) -> str:
        """Responde a una despedida."""
        return (
            "Ha sido un placer servirle, señor. "
            "Estaré aquí cuando me necesite. Que tenga un excelente día."
        )

    # ─── Workflows multi-paso ────────────────────────────────

    def solve_exercises(self, file_path: str, output_app: str = "") -> str:
        """
        Lee un PDF/documento con ejercicios, los resuelve con el LLM,
        y opcionalmente escribe las respuestas en Word/Google Docs.

        Args:
            file_path: Ruta al PDF/documento con ejercicios.
            output_app: App donde escribir las soluciones (Word, Google Docs, etc.).
        """
        try:
            # 1. Leer el documento
            dp = self.modules.get("document_processor")
            if not dp:
                return "Módulo de documentos no disponible."

            content = dp.read_document(file_path)
            if content.startswith(("Error", "Archivo no")):
                return content

            # 2. Truncar si es muy largo
            if len(content) > 8000:
                content = content[:8000] + "\n[... documento truncado ...]"

            # 3. Enviar al LLM con prompt de resolución
            solving_prompt = (
                "A continuación tienes ejercicios de un documento. "
                "Resuélvelos todos de forma clara y ordenada. "
                "Para cada ejercicio:\n"
                "- Indica el número del ejercicio\n"
                "- Escribe la respuesta completa\n"
                "- Si es matemática, muestra el procedimiento paso a paso\n"
                "- Si es de programación, escribe el código completo\n"
                "- Si es de redacción, escribe la respuesta desarrollada\n\n"
                "EJERCICIOS:\n" + content
            )

            # Usar num_predict más alto para soluciones largas
            solutions = self.brain.chat(
                solving_prompt,
                context="Resolviendo ejercicios de un documento"
            )

            if not solutions or solutions.startswith("Me temo"):
                return "No pude resolver los ejercicios. " + (solutions or "")

            # 4. Si se especifica app de salida, escribir las soluciones
            if output_app:
                sc = self.modules.get("system_control")
                if sc:
                    # Abrir la aplicación
                    sc.open_application(output_app)
                    time.sleep(4.0)  # Esperar a que cargue

                    # Escribir soluciones
                    sc.type_long_text(solutions)
                    return f"Ejercicios resueltos y escritos en {output_app}."

            return f"Ejercicios resueltos:\n\n{solutions}"

        except Exception as e:
            logger.error(f"Error resolviendo ejercicios: {e}")
            return f"Error al resolver ejercicios: {e}"

    def read_and_answer(self, file_path: str, question: str = "") -> str:
        """
        Lee un documento y responde preguntas sobre su contenido.

        Args:
            file_path: Ruta al documento.
            question: Pregunta específica sobre el contenido.
        """
        try:
            dp = self.modules.get("document_processor")
            if not dp:
                return "Módulo de documentos no disponible."

            content = dp.read_document(file_path)
            if content.startswith(("Error", "Archivo no")):
                return content

            if len(content) > 8000:
                content = content[:8000] + "\n[... documento truncado ...]"

            prompt = f"Contenido del documento:\n{content}\n\n"
            if question:
                prompt += f"Pregunta del usuario: {question}"
            else:
                prompt += "Resume el contenido de este documento de forma clara y concisa."

            return self.brain.chat(prompt, context="Analizando documento")

        except Exception as e:
            logger.error(f"Error leyendo/respondiendo documento: {e}")
            return f"Error: {e}"

    # ─── Acceso directo a módulos ─────────────────────────────

    def get_module(self, name: str):
        """Obtiene un módulo por nombre."""
        return self.modules.get(name)

    def get_system_status(self) -> dict:
        """Obtiene el estado del sistema para el HUD."""
        sc = self.modules.get("system_control")
        if sc:
            return sc.get_system_status()
        return {}
