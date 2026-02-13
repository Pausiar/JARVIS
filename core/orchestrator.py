"""
J.A.R.V.I.S. — Orchestrator
Orquesta los módulos según la petición del usuario.
Conecta el cerebro (LLM) con los módulos de acción.
"""

import logging
import re
import time
import datetime
import os
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
from modules.vision import VisionEngine
from modules.media_control import MediaControl
from modules.notifications import NotificationManager
from modules.calendar_manager import CalendarManager
from modules.plugin_loader import PluginLoader
from modules.learner import LearningEngine

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
            "vision": VisionEngine(),
            "media_control": MediaControl(),
            "notifications": NotificationManager(),
            "calendar": CalendarManager(),
        }

        # Plugin loader
        self.plugin_loader = PluginLoader()
        try:
            loaded = self.plugin_loader.load_all()
            if loaded:
                logger.info(f"Plugins cargados: {loaded}")
            from config import PLUGINS_HOT_RELOAD
            if PLUGINS_HOT_RELOAD:
                self.plugin_loader.start_watching()
        except Exception as e:
            logger.warning(f"Error cargando plugins: {e}")

        # Pasar brain reference a SystemControl para features avanzados
        sc = self.modules.get("system_control")
        if sc and hasattr(sc, 'set_brain'):
            sc.set_brain(self.brain)

        # Iniciar notificaciones proactivas
        try:
            from config import NOTIFICATIONS_ENABLED
            if NOTIFICATIONS_ENABLED:
                notif = self.modules.get("notifications")
                if notif:
                    notif.start()
        except Exception as e:
            logger.warning(f"Error iniciando notificaciones: {e}")

        # Iniciar recordatorios del calendario
        try:
            cal = self.modules.get("calendar")
            if cal:
                cal.start_reminders()
        except Exception as e:
            logger.warning(f"Error iniciando recordatorios: {e}")

        # Motor de aprendizaje
        self.learner = LearningEngine()
        self.learner.set_brain(self.brain)

        # Último input para aprendizaje de correcciones
        self._last_user_input = ""
        self._last_action = ""

        logger.info(f"Orchestrator inicializado. {self.learner.get_skill_count()} habilidades aprendidas.")

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

        # Comprobar si es una corrección ("no, me refería a X")
        correction_result = self._check_correction(user_input)
        if correction_result:
            self.memory.save_message("assistant", correction_result)
            return correction_result

        # Guardar para posible corrección futura
        self._last_user_input = user_input

        # Paso 0: Verificar si tenemos una habilidad aprendida para esto
        learned_skill = self.learner.find_skill(user_input)
        if learned_skill:
            logger.info(f"Usando habilidad aprendida: '{learned_skill['name']}'")
            result = self.learner.execute_skill(learned_skill, user_input)
            if result and not result.startswith("Error"):
                response = f"Hecho, señor. (habilidad aprendida) {result}"
                self.memory.save_message("assistant", response)
                return response

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
        # Detectar si el usuario EXPLÍCITAMENTE pide leer/ver la pantalla
        # Solo cuando el usuario hace una pregunta directa sobre lo que hay
        # en pantalla. NO activar por menciones casuales de "pantalla".
        needs_screen = bool(re.search(
            r"(?:qu[eé]|que)\s+(?:hay|pone|dice|se\s+ve|aparece)\s+(?:en\s+)?(?:la\s+)?(?:pantalla|la\s+pantalla)"
            r"|(?:lee|leer|dime)\s+(?:lo\s+que|qu[eé]|que)\s+(?:hay|pone|dice|se\s+ve)\s+(?:en\s+)?(?:la\s+)?pantalla"
            r"|(?:describe|describir)\s+(?:lo\s+que|la)\s+(?:pantalla|se\s+ve\s+en\s+pantalla)"
            r"|(?:lee|leer)\s+(?:la\s+)?pantalla"
            r"|(?:qu[eé]|que)\s+(?:hay|pone|dice)\s+(?:aqu[ií]|ah[ií])",
            user_input, re.IGNORECASE
        ))

        # Detectar si es una pregunta conversacional simple (no necesita contexto pesado)
        is_simple_chat = bool(re.search(
            r"^(?:cu[eé]ntame|dime|sabes|conoces|qu[eé]\s+(?:es|son|significa|opinas)|"
            r"c[oó]mo\s+(?:est[aá]s|funciona|se\s+hace)|"
            r"por\s+qu[eé]|qui[eé]n|cu[aá]ndo|cu[aá]nto|d[oó]nde|"
            r"haz(?:me)?\s+(?:un|una)\s+(?:chiste|broma|historia|resumen)|"
            r"explica|define|traduce|escribe|recomienda|sugiere|"
            r"cu[aá]l\s+es|hab[ií]a\s+una\s+vez|hab[ií]a|"
            r"hola|hey|oye|mira|a\s+ver)",
            user_input, re.IGNORECASE
        ))

        # Para chat simple, contexto mínimo. Para pantalla, incluir OCR.
        if is_simple_chat and not needs_screen:
            context = self._build_context_minimal()
        else:
            context = self._build_context(include_screen=needs_screen)

        llm_response = self.brain.chat(user_input, context=context)

        # Paso 3: Extraer y ejecutar acciones del LLM
        llm_intents = self.parser.parse_llm_actions(llm_response)
        action_results = []
        for llm_intent in llm_intents:
            result = self._execute_intent(llm_intent)
            if result:
                action_results.append(result)

        # Paso 3b: Safety net — detectar si el LLM afirmó haber hecho algo
        # sin generar ACTION tags (alucinación de acción)
        if not llm_intents:
            fallback_result = self._detect_and_fix_hallucinated_action(
                user_input, llm_response
            )
            if fallback_result:
                action_results.append(fallback_result)

        # Paso 4: Limpiar y devolver respuesta
        clean_response = self.brain.clean_response(llm_response)

        # Si hubo acciones ejecutadas, agregar info
        if action_results:
            extra_info = " | ".join(action_results)
            # Reemplazar la respuesta falsa del LLM por confirmación real
            clean_response = f"Hecho, señor. {extra_info}"

        # Paso 5: Detectar si JARVIS no supo hacer algo → investigar y aprender
        if self._should_learn(user_input, clean_response, llm_intents, action_results):
            logger.info("Detectado que no sé hacer esto. Investigando...")
            learn_result = self.learner.research_and_learn(
                user_input, failure_context=clean_response
            )
            if learn_result and not learn_result.startswith("Error"):
                clean_response = learn_result
            else:
                # Escalada: preguntar a ChatGPT si el LLM propio no pudo
                logger.info("LLM propio no pudo resolver. Escalando a ChatGPT...")
                chatgpt_result = self.learner.ask_chatgpt_for_help(
                    user_input, failure_context=clean_response
                )
                if chatgpt_result and not chatgpt_result.startswith("Error"):
                    clean_response = chatgpt_result

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
            # Guardar última acción para correcciones
            self._last_action = f"{module_name}.{function_name}"
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

    # ─── Detección de necesidad de aprendizaje ─────────────────

    def _should_learn(self, user_input: str, response: str,
                      llm_intents: list, action_results: list) -> bool:
        """
        Detecta si JARVIS no supo hacer lo que el usuario pidió
        y debería intentar investigar y aprender.

        Condiciones para aprender:
        - El LLM respondió que no puede hacerlo
        - No se ejecutó ninguna acción
        - El usuario parece querer una acción (no solo conversar)
        """
        # Si se ejecutaron acciones con éxito, no hay que aprender
        if action_results:
            return False

        # Si hubo intenciones del LLM que se ejecutaron, no aprender
        if llm_intents:
            return False

        # Detectar si la respuesta indica que no supo hacerlo
        failure_indicators = [
            "no puedo", "no he podido", "me temo",
            "no sé cómo", "no tengo acceso", "no soy capaz",
            "no puedo acceder", "no dispongo", "no es posible",
            "no tengo la capacidad", "fuera de mi alcance",
            "no puedo completar", "i can't", "i cannot",
        ]
        response_lower = response.lower()
        is_failure = any(f in response_lower for f in failure_indicators)

        if not is_failure:
            return False

        # Verificar que el usuario quería una acción (no solo conversar)
        action_indicators = [
            r"\b(?:haz|hacer|hazme|hazmelo)\b",
            r"\b(?:abre|abrir|abrirme|ábreme)\b",
            r"\b(?:pon|poner|ponme)\b",
            r"\b(?:busca|buscar)\b",
            r"\b(?:crea|crear)\b",
            r"\b(?:escribe|escribir|escríbelo)\b",
            r"\b(?:mira|mirar|lee|leer)\b",
            r"\b(?:cambia|cambiar)\b",
            r"\b(?:instala|instalar)\b",
            r"\b(?:configura|configurar)\b",
            r"\b(?:mueve|mover)\b",
            r"\b(?:resuelve|resolver)\b",
            r"\b(?:ejecuta|ejecutar)\b",
            r"\b(?:descarga|descargar)\b",
        ]
        user_wants_action = any(
            re.search(p, user_input, re.IGNORECASE)
            for p in action_indicators
        )

        return user_wants_action

    # ─── Correcciones / aprendizaje ─────────────────────────

    def _check_correction(self, user_input: str) -> Optional[str]:
        """Detecta si el usuario está corrigiendo la acción anterior."""
        correction_match = re.match(
            r"(?:no,?\s*)?(?:me\s+refer[ií]a\s+a|quer[ií]a\s+decir|"
            r"no\s+(?:era\s+)?eso,?\s*(?:sino|quiero)|"
            r"eso\s+no,?\s*(?:quiero|pon|haz))\s+(.+)",
            user_input, re.IGNORECASE,
        )
        if correction_match and self._last_user_input and self._last_action:
            correct_action = correction_match.group(1).strip()
            self.memory.save_correction(
                self._last_user_input,
                self._last_action,
                correct_action,
            )
            logger.info(
                f"Corrección guardada: '{self._last_user_input}' → '{correct_action}'"
            )
            # Re-procesar con la acción corregida
            self._last_user_input = None
            self._last_action = None
            return self.process(correct_action)
        return None

    # ─── Helpers ──────────────────────────────────────────────

    def _detect_and_fix_hallucinated_action(
        self, user_input: str, llm_response: str
    ) -> Optional[str]:
        """
        Safety net: detecta cuando el LLM afirma haber ejecutado una acción
        física (pegar, escribir, abrir) sin haber generado ACTION tags.
        Si el usuario pidió pegar/escribir, lo ejecuta realmente.

        Returns:
            Resultado de la acción ejecutada, o None si no aplica.
        """
        # ¿El usuario pidió una acción de pegar/escribir/insertar?
        paste_request = re.search(
            r"(?:pega|pegar|paste|mete|meter|inserta|insertar|pon|poner)\s+"
            r"(?:la\s+)?(?:respuesta|eso|esto|el\s+texto|lo\s+anterior|lo|la)"
            r"|(?:p[eé]gal[oa]|escr[ií]bel[oa]|p[oó]nl[oa]|m[eé]tel[oa]|ins[eé]rtal[oa])"
            r"|(?:pega|mete|pon|escribe|inserta)\s+(?:en\s+el\s+documento|ah[ií]|aqu[ií])",
            user_input, re.IGNORECASE
        )

        if not paste_request:
            return None

        # ¿El LLM afirmó falsamente haberlo hecho?
        false_claim = re.search(
            r"(?:ha\s+sido|fue|he)\s+(?:pegad|insertad|escrit|colocad|puest)"
            r"|(?:respuest|text|contenid)\w*\s+(?:ha\s+sido\s+)?(?:pegad|insertad|escrit|colocad)"
            r"|(?:listo|hecho).*(?:pegad|insertad|escrit)"
            r"|(?:ya\s+(?:est[aá]|qued[oó]|se\s+ha)\s+(?:pegad|insertad|escrit|puest))",
            llm_response, re.IGNORECASE
        )

        if false_claim:
            logger.warning(
                "LLM alucinó una acción de pegado. Ejecutando realmente..."
            )
            result = self.paste_last_response()
            return result

        return None

    def _build_context(self, include_screen: bool = False) -> str:
        """Construye contexto adicional para el LLM."""
        context_parts = []

        # Hora y fecha
        now = datetime.datetime.now()
        context_parts.append(
            f"Fecha: {now.strftime('%d/%m/%Y %H:%M')}"
        )

        # Info del usuario
        user_name = self.memory.get_preference("user_name")
        if user_name:
            context_parts.append(f"Usuario: {user_name}")

        # Contexto visual de pantalla (si se solicita)
        if include_screen:
            sc = self.modules.get("system_control")
            if sc and hasattr(sc, 'get_screen_text'):
                try:
                    screen_text = sc.get_screen_text()
                    if screen_text and not screen_text.startswith("No se"):
                        if len(screen_text) > 2000:
                            screen_text = screen_text[:2000] + "\n[... truncado ...]"
                        context_parts.append(
                            f"Pantalla:\n{screen_text}"
                        )
                except Exception as e:
                    logger.warning(f"Error obteniendo contexto de pantalla: {e}")

        return "\n".join(context_parts)

    def _build_context_minimal(self) -> str:
        """Contexto mínimo para consultas conversacionales — solo fecha/hora."""
        now = datetime.datetime.now()
        return f"Fecha: {now.strftime('%d/%m/%Y %H:%M')}"

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

    def solve_screen_exercises(self, target_tab: str = "next",
                                source_app: str = "", target_app: str = "",
                                content_hint: str = "") -> str:
        """
        Lee ejercicios de una aplicación/pestaña (ej: Chrome con PDF), los resuelve
        con el LLM, y escribe las soluciones en otra aplicación (ej: IntelliJ, Google Docs).
        """
        import pyautogui
        import subprocess
        sc = self.modules.get("system_control")
        if not sc:
            return "Módulo de control del sistema no disponible."

        # Normalizar target_app: "el segundo", "la otra", "el otro tab" → siguiente pestaña
        tab_synonyms = [
            "el segundo", "la segunda", "el otro", "la otra",
            "otro tab", "otra pestaña", "segundo tab", "segunda pestaña",
            "next", "siguiente",
        ]
        if target_app and target_app.lower().strip() in tab_synonyms:
            logger.info(f"target_app '{target_app}' normalizado a → siguiente pestaña (tab switch)")
            target_app = ""  # Vaciar para que use switch_tab en vez de focus_window
        if not sc:
            return "Módulo de control del sistema no disponible."

        try:
            # 1. ENFOCAR la app/pestaña fuente si se especificó
            if source_app:
                logger.info(f"Enfocando app fuente: {source_app}")
                focus_result = sc.focus_window(source_app)
                logger.info(f"Focus result: {focus_result}")
                time.sleep(1.5)

            # 2. MINIMIZAR la ventana de JARVIS para que no tape el contenido
            logger.info("Minimizando JARVIS para capturar contenido...")
            self._minimize_jarvis_window()
            time.sleep(2.0)

            screen_w, screen_h = pyautogui.size()
            click_x = int(screen_w * 0.65)
            click_y = int(screen_h * 0.40)

            # 3. INTENTAR OBTENER LA URL de la barra de direcciones
            #    Esto nos permite detectar si es un PDF local y leerlo directamente
            clipboard_text = ""
            pdf_path = self._try_extract_pdf_path()

            # LIMPIAR el portapapeles para que la URL no contamine el fallback
            try:
                subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-command",
                     "Set-Clipboard -Value $null"],
                    capture_output=True, text=True, timeout=3
                )
            except Exception:
                pass

            if pdf_path:
                # 4a. PDF LOCAL detectado → leer directamente con PyMuPDF
                logger.info(f"PDF local detectado: {pdf_path}")
                clipboard_text = self._read_pdf_direct(pdf_path)
                logger.info(f"PDF leído directamente: {len(clipboard_text)} chars")
            
            if not clipboard_text or len(clipboard_text.strip()) < 20:
                # 4b. FALLBACK: Ctrl+A Ctrl+C para contenido seleccionable
                logger.info("Intentando captura vía Ctrl+A + Ctrl+C...")
                
                # Clic en la zona de contenido
                pyautogui.click(click_x, click_y)
                time.sleep(0.5)
                
                pyautogui.hotkey('ctrl', 'a')   # Seleccionar todo
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'c')   # Copiar
                time.sleep(0.5)

                # Leer el portapapeles
                clip_result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=5
                )
                clipboard_text = clip_result.stdout.strip()
                logger.info(f"Portapapeles (Ctrl+A+C): {len(clipboard_text)} chars")

                # Deseleccionar
                pyautogui.click(click_x, click_y)
                time.sleep(0.3)

            # 5. Restaurar ventana de JARVIS
            self._restore_jarvis_window()

            if not clipboard_text or len(clipboard_text.strip()) < 20:
                return (
                    "No pude leer texto de la pantalla, señor. "
                    "Asegúrese de que el contenido esté visible y seleccionable "
                    "en la pestaña activa (PDF, Google Docs, web, etc.)."
                )

            full_content = clipboard_text

            # Truncar si es excesivamente largo para el LLM
            if len(full_content) > 15000:
                full_content = full_content[:15000] + "\n[... texto truncado ...]"

            logger.info(f"Contenido total capturado: {len(full_content)} caracteres")

            # 5. Enviar al LLM para resolver
            hint_instruction = ""
            if content_hint:
                hint_instruction = (
                    f"IMPORTANTE: El usuario ha pedido específicamente: '{content_hint}'. "
                    f"Céntrate SOLO en eso del texto capturado. Si pide un ejercicio concreto "
                    f"(ej: 'ejercicio 2'), resuelve SOLO ese ejercicio.\n\n"
                )

            solving_prompt = (
                hint_instruction +
                "A continuación tienes contenido capturado de la pantalla del usuario. "
                "Resuélvelo de forma clara y ordenada. "
                "Para cada ejercicio:\n"
                "- Indica el número del ejercicio\n"
                "- Escribe la respuesta completa\n"
                "- Si es matemática, muestra el procedimiento paso a paso\n"
                "- Si es de programación, escribe el código completo\n"
                "- Si es de redacción, escribe la respuesta desarrollada\n\n"
                "CONTENIDO CAPTURADO:\n" + full_content
            )

            logger.info("Enviando ejercicios al LLM para resolverlos...")
            solutions = self.brain.chat(
                solving_prompt,
                context="Resolviendo ejercicios capturados de pantalla"
            )

            # Detectar si el LLM NO pudo resolver (no pegar errores en la app destino)
            failure_phrases = (
                "Me temo", "No he podido", "No pude", "Lo siento",
                "no hay ejercicio", "no encuentro", "no proporciona",
                "no puedo resolver", "no es posible", "información insuficiente",
                "no hay contenido", "no se puede", "No hay ejercicio",
                "Could not", "cannot", "I'm sorry",
            )
            if not solutions or any(solutions.lower().startswith(f.lower()) for f in failure_phrases):
                logger.warning(f"LLM no pudo resolver. Respuesta: {solutions[:200]}")
                return (
                    "No pude resolver los ejercicios del contenido capturado, señor. "
                    "Puede que el texto no contenga ejercicios claros o que el "
                    "ejercicio solicitado no exista en la página. "
                    + (solutions[:300] if solutions else "")
                )

            # Detectar también si la respuesta parece un mensaje de error (no un ejercicio resuelto)
            if len(solutions) < 30 or "no hay" in solutions.lower()[:100]:
                logger.warning(f"Respuesta demasiado corta o parece error: {solutions[:200]}")
                return f"El LLM no generó soluciones válidas, señor. Respuesta: {solutions[:300]}"

            logger.info(f"Soluciones generadas: {len(solutions)} caracteres")

            # 6. Minimizar JARVIS de nuevo para escribir en el documento
            self._minimize_jarvis_window()
            time.sleep(2.0)  # Esperar bien a que se minimice

            # 7. Enfocar la app/pestaña destino (con reintento)
            if target_app:
                logger.info(f"Enfocando app destino: {target_app}")
                focus_result = sc.focus_window(target_app)
                logger.info(f"Focus destino (intento 1): {focus_result}")
                time.sleep(2.0)

                # Verificar que realmente se enfocó — si no, reintentar
                active_title = sc.get_active_window_title()
                logger.info(f"Ventana activa tras focus: {active_title}")
                target_lower = target_app.lower()
                if active_title and target_lower not in active_title.lower():
                    logger.warning(f"Focus falló, reintentando con Alt+Tab y focus_window...")
                    # Intento 2: Alt+Tab para sacar algo a primer plano + focus_window
                    pyautogui.hotkey('alt', 'tab')
                    time.sleep(1.5)
                    focus_result = sc.focus_window(target_app)
                    logger.info(f"Focus destino (intento 2): {focus_result}")
                    time.sleep(2.0)
            else:
                # Fallback: cambiar de pestaña en la misma app
                logger.info(f"Cambiando a pestaña {target_tab}...")
                sc.switch_tab(target_tab)
                time.sleep(2.0)

            # 8. Hacer clic en el cuerpo del documento/editor para asegurar foco teclado
            pyautogui.click(screen_w // 2, screen_h // 2)
            time.sleep(1.0)

            # 9. Escribir las soluciones
            logger.info("Escribiendo soluciones en el documento...")
            result = sc.type_long_text(solutions)

            # 10. Restaurar JARVIS
            self._restore_jarvis_window()

            dest_name = target_app if target_app else "la siguiente pestaña"
            return (
                f"Ejercicios resueltos y escritos en {dest_name}, señor. "
                f"({len(solutions)} caracteres)."
            )

        except Exception as e:
            logger.error(f"Error en solve_screen_exercises: {e}")
            self._restore_jarvis_window()  # Asegurar que JARVIS vuelve
            return f"Error al resolver ejercicios de pantalla: {e}"

    # ─── Aprendizaje ──────────────────────────────────────────

    def list_learned_skills(self) -> str:
        """Lista todas las habilidades que JARVIS ha aprendido."""
        return self.learner.list_skills()

    def forget_skill(self, skill_name: str) -> str:
        """Elimina una habilidad aprendida."""
        return self.learner.forget_skill(skill_name)

    def format_in_app(self, app_name: str, format_instruction: str) -> str:
        """
        Va a una app (Word, Google Docs, etc.) y aplica formato usando el LLM
        para decidir qué teclas usar. Usa Ctrl+A para seleccionar si es necesario.
        
        El LLM analiza el formato pedido y genera secuencias de hotkeys.
        
        Args:
            app_name: App donde formatear (word, google docs, etc.)
            format_instruction: Qué formato aplicar (ej: "pon en negrita los enunciados")
        """
        import pyautogui
        sc = self.modules.get("system_control")
        if not sc:
            return "Módulo de control del sistema no disponible."

        try:
            # 1. Minimizar JARVIS y enfocar la app
            self._minimize_jarvis_window()
            time.sleep(1.5)

            logger.info(f"Formateando en: {app_name}")
            focus_result = sc.focus_window(app_name)
            logger.info(f"Focus para formato: {focus_result}")
            time.sleep(2.0)

            screen_w, screen_h = pyautogui.size()

            # 2. Primero, leer el contenido actual del documento (Ctrl+A Ctrl+C)
            pyautogui.click(screen_w // 2, screen_h // 2)
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)

            import subprocess
            clip_result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5
            )
            current_text = clip_result.stdout.strip()
            
            # Deseleccionar
            pyautogui.press('home')
            time.sleep(0.3)

            logger.info(f"Texto actual del documento: {len(current_text)} chars")

            # 3. Pedir al LLM que genere el texto ya formateado y una estrategia 
            format_prompt = (
                f"El usuario tiene este texto en un documento ({app_name}):\n\n"
                f"{current_text[:5000]}\n\n"
                f"El usuario quiere: '{format_instruction}'\n\n"
                f"IMPORTANTE: No puedo manipular el ratón con precisión para seleccionar "
                f"texto específico en el documento. La mejor estrategia es:\n"
                f"1. Seleccionar TODO (Ctrl+A)\n"
                f"2. Borrar todo\n"
                f"3. Re-escribir el contenido ya formateado\n\n"
                f"Re-escribe el texto completo tal como debe quedar en el documento. "
                f"Aplica el formato pedido. Si pide negrita en ciertos textos, "
                f"usa **texto** para indicar dónde va negrita (yo luego lo proceso). "
                f"Si pide subrayado, usa __texto__. "
                f"Mantén el resto del contenido EXACTAMENTE igual.\n\n"
                f"Devuelve SOLO el texto formateado, nada más."
            )

            formatted_text = self.brain.chat(
                format_prompt,
                context="Formateando documento"
            )

            if not formatted_text or len(formatted_text) < 20:
                self._restore_jarvis_window()
                return "No pude generar el formato, señor."

            # 4. Seleccionar todo y reemplazar con el texto formateado
            #    Para apps como Word/Google Docs que soportan formato real:
            #    Procesamos los markers **bold** y __underline__ con hotkeys
            pyautogui.click(screen_w // 2, screen_h // 2)
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            pyautogui.press('delete')
            time.sleep(0.5)

            # 5. Escribir el texto con formato real usando hotkeys
            self._type_with_formatting(formatted_text, sc)

            # 6. Restaurar JARVIS
            self._restore_jarvis_window()
            return f"Formato aplicado en {app_name}, señor."

        except Exception as e:
            logger.error(f"Error formateando: {e}")
            self._restore_jarvis_window()
            return f"Error al formatear: {e}"

    def _type_with_formatting(self, text: str, sc):
        """
        Escribe texto aplicando formato real vía hotkeys.
        **texto** → Ctrl+B antes, escribe, Ctrl+B después (negrita)
        __texto__ → Ctrl+U antes, escribe, Ctrl+U después (subrayado)
        """
        import pyautogui
        import re

        # Parsear segmentos de texto con formato
        # Procesamos por líneas para mantener estructura
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            if i > 0:
                pyautogui.press('enter')
                time.sleep(0.05)

            if not line.strip():
                continue

            # Buscar segmentos con formato en la línea
            pos = 0
            remaining = line

            while remaining:
                # Buscar el próximo marcador de formato
                bold_match = re.search(r'\*\*(.+?)\*\*', remaining)
                underline_match = re.search(r'__(.+?)__', remaining)

                # Encontrar cuál viene primero
                next_match = None
                fmt_type = None
                
                if bold_match and underline_match:
                    if bold_match.start() < underline_match.start():
                        next_match = bold_match
                        fmt_type = 'bold'
                    else:
                        next_match = underline_match
                        fmt_type = 'underline'
                elif bold_match:
                    next_match = bold_match
                    fmt_type = 'bold'
                elif underline_match:
                    next_match = underline_match
                    fmt_type = 'underline'

                if next_match:
                    # Escribir texto antes del formato
                    before = remaining[:next_match.start()]
                    if before:
                        sc.type_long_text(before)
                        time.sleep(0.1)

                    # Activar formato, escribir, desactivar
                    format_text = next_match.group(1)
                    hotkey = 'b' if fmt_type == 'bold' else 'u'
                    
                    pyautogui.hotkey('ctrl', hotkey)  # Activar formato
                    time.sleep(0.1)
                    sc.type_long_text(format_text)
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', hotkey)  # Desactivar formato
                    time.sleep(0.1)

                    remaining = remaining[next_match.end():]
                else:
                    # No más formato — escribir el resto
                    if remaining:
                        sc.type_long_text(remaining)
                    remaining = ""

            time.sleep(0.05)

    def research_topic(self, topic: str) -> str:
        """Investiga proactivamente cómo hacer algo."""
        logger.info(f"Investigación solicitada: '{topic}'")
        return self.learner.research_and_learn(
            topic, failure_context="Investigación solicitada por el usuario"
        )

    def ask_chatgpt(self, question: str) -> str:
        """Pregunta directamente a ChatGPT abriendo el navegador."""
        logger.info(f"Pregunta a ChatGPT solicitada: '{question}'")
        return self.learner.ask_chatgpt_for_help(question)

    # ─── Helpers para lectura de contenido ────────────────────

    def _try_extract_pdf_path(self) -> str:
        """
        Intenta obtener la URL de la barra de direcciones del navegador (Ctrl+L → Ctrl+C).
        Si es un PDF local (file:/// o chrome-extension con file:///), extrae la ruta.
        
        Returns:
            Ruta local al PDF, o "" si no es un PDF local.
        """
        import pyautogui
        import subprocess
        import urllib.parse

        try:
            # Ctrl+L selecciona la barra de direcciones en Chrome/Edge/Firefox
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)
            # Escape para cerrar la barra de direcciones sin cambiar nada
            pyautogui.press('escape')
            time.sleep(0.3)

            clip_result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5
            )
            url = clip_result.stdout.strip()
            logger.info(f"URL de la barra de direcciones: {url[:150]}")

            if not url:
                return ""

            # Detectar PDFs locales:
            # 1. file:///C:/Users/.../file.pdf
            # 2. chrome-extension://efaidnbmnnnibpcajpcglclefindmkaj/file:///C:/Users/.../file.pdf
            local_path = ""

            if "file:///" in url:
                # Extraer la parte después de file:///
                file_idx = url.index("file:///")
                raw_path = url[file_idx + 8:]  # Quitar "file:///"
                # Decodificar %20 → espacios, etc.
                local_path = urllib.parse.unquote(raw_path)
                # Limpiar query params o hashes si los hubiera
                for sep in ['?', '#']:
                    if sep in local_path:
                        local_path = local_path[:local_path.index(sep)]

            if local_path and local_path.lower().endswith('.pdf'):
                # Normalizar path para Windows
                local_path = local_path.replace('/', '\\')
                if not local_path[0] == '\\':
                    # Ya tiene forma C:\Users\...
                    pass
                logger.info(f"PDF local detectado: {local_path}")
                if os.path.exists(local_path):
                    return local_path
                else:
                    logger.warning(f"PDF path no existe: {local_path}")

            return ""

        except Exception as e:
            logger.warning(f"Error extrayendo URL del navegador: {e}")
            return ""

    def _read_pdf_direct(self, pdf_path: str) -> str:
        """
        Lee un PDF directamente usando PyMuPDF (fitz).
        Mucho más fiable que OCR o Ctrl+A en Adobe Acrobat.
        
        Args:
            pdf_path: Ruta absoluta al archivo PDF.
            
        Returns:
            Texto completo del PDF.
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            all_text = []

            for page_num in range(num_pages):
                page = doc[page_num]
                text = page.get_text()
                if text and text.strip():
                    all_text.append(f"--- Página {page_num + 1} ---\n{text.strip()}")

            doc.close()

            full_text = "\n\n".join(all_text)
            logger.info(f"PDF leído: {num_pages} páginas, {len(full_text)} chars")
            return full_text

        except ImportError:
            logger.warning("PyMuPDF (fitz) no está instalado.")
            return ""
        except Exception as e:
            logger.error(f"Error leyendo PDF '{pdf_path}': {e}")
            return ""

    def _minimize_jarvis_window(self):
        """Minimiza la ventana de JARVIS para no tapar la pantalla."""
        try:
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32
            from config import HUD_WINDOW_TITLE

            # Buscar ventana por título
            hwnd = user32.FindWindowW(None, HUD_WINDOW_TITLE)
            if hwnd:
                SW_MINIMIZE = 6
                user32.ShowWindow(hwnd, SW_MINIMIZE)
                logger.info(f"Ventana '{HUD_WINDOW_TITLE}' minimizada")
            else:
                # Fallback: Alt+Tab para cambiar a otra ventana
                import pyautogui
                pyautogui.hotkey('alt', 'tab')
                logger.warning("No se encontró ventana JARVIS, usando Alt+Tab")
        except Exception as e:
            logger.warning(f"Error minimizando JARVIS: {e}")

    def _restore_jarvis_window(self):
        """Restaura la ventana de JARVIS después de capturar pantalla."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            from config import HUD_WINDOW_TITLE

            hwnd = user32.FindWindowW(None, HUD_WINDOW_TITLE)
            if hwnd:
                SW_RESTORE = 9
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
                logger.info(f"Ventana '{HUD_WINDOW_TITLE}' restaurada")
        except Exception as e:
            logger.warning(f"Error restaurando JARVIS: {e}")

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

    def list_plugins(self) -> str:
        """Lista los plugins cargados."""
        if not hasattr(self, 'plugin_loader') or not self.plugin_loader:
            return "El sistema de plugins no está disponible."
        plugins = self.plugin_loader.get_all_plugins()
        if not plugins:
            return "No hay plugins cargados."
        lines = ["Plugins cargados:"]
        for p in plugins:
            lines.append(f"  • {p.name} v{p.version} — {p.description}")
        return "\n".join(lines)

    def reload_plugins(self) -> str:
        """Recarga todos los plugins."""
        if not hasattr(self, 'plugin_loader') or not self.plugin_loader:
            return "El sistema de plugins no está disponible."
        self.plugin_loader.reload_all()
        count = len(self.plugin_loader.get_all_plugins())
        return f"Plugins recargados. {count} plugin(s) activos."

    def toggle_notifications(self, enabled: bool = True) -> str:
        """Activa o desactiva las notificaciones proactivas."""
        notif = self.modules.get("notifications")
        if not notif:
            return "El módulo de notificaciones no está disponible."
        if enabled:
            notif.start()
            return "Notificaciones proactivas activadas."
        else:
            notif.stop()
            return "Notificaciones proactivas desactivadas."

    def toggle_continuous_listening(self, enabled: bool = True) -> str:
        """Activa o desactiva la escucha continua."""
        from config import CONTINUOUS_LISTENING
        import config
        config.CONTINUOUS_LISTENING = enabled
        status = "activada" if enabled else "desactivada"
        return f"Escucha continua {status}."

    def switch_brain_mode(self, mode: str) -> str:
        """Cambia entre modo local (Ollama) y cloud (API)."""
        return self.brain.set_mode(mode)

    def switch_cloud_provider(self, provider: str) -> str:
        """Cambia el proveedor cloud (groq o gemini)."""
        return self.brain.set_cloud_provider(provider)

    def get_brain_mode_info(self) -> str:
        """Devuelve información sobre el modo actual del cerebro."""
        return self.brain.get_mode_info()

    def set_cloud_api_key(self, provider: str, api_key: str) -> str:
        """Configura la API key de un proveedor cloud."""
        provider = provider.lower().strip()
        api_key = api_key.strip()

        if provider not in ("groq", "gemini"):
            return f"Proveedor '{provider}' no soportado. Use 'groq' o 'gemini'."

        # Guardar en brain
        if provider == "groq":
            self.brain.groq_api_key = api_key
        else:
            self.brain.gemini_api_key = api_key

        # Persistir en config.json
        try:
            from config import load_config, save_config
            cfg = load_config()
            cfg[f"{provider}_api_key"] = api_key
            save_config(cfg)
        except Exception as e:
            logger.warning(f"No se pudo guardar API key: {e}")

        return f"API key de {provider} configurada correctamente, señor."

    def paste_last_response(self) -> str:
        """
        Pega la última respuesta del asistente en la aplicación activa.
        Usa type_long_text para escribir el texto via portapapeles+Ctrl+V.
        """
        try:
            # Obtener mensajes recientes
            messages = self.memory.get_recent_messages(limit=20)

            # Encontrar la última respuesta del asistente
            last_response = None
            for msg in reversed(messages):
                if msg["role"] == "assistant":
                    candidate = msg["content"]
                    # Saltar respuestas meta/sistema (saludos, confirmaciones cortas)
                    if candidate and len(candidate) > 30 and not candidate.startswith(("Hecho, señor", "No he escuchado")):
                        last_response = candidate
                        break
                    elif candidate and not last_response:
                        last_response = candidate

            if not last_response:
                return "No tengo una respuesta previa para pegar, señor."

            # Limpiar meta-texto de JARVIS
            clean = re.sub(r"^\s*Hecho, señor\.?\s*", "", last_response)
            clean = re.sub(r"\s*\[Resultado:.*?\]\s*$", "", clean)
            clean = clean.strip()

            if not clean:
                return "La última respuesta está vacía, señor."

            # Escribir en la app activa
            sc = self.modules.get("system_control")
            if sc:
                result = sc.type_long_text(clean)
                return f"Respuesta pegada en la aplicación activa ({len(clean)} caracteres)."

            return "No pude acceder al módulo de control del sistema."
        except Exception as e:
            logger.error(f"Error pegando última respuesta: {e}")
            return f"Error al pegar la respuesta: {e}"

    def get_module(self, name: str):
        """Obtiene un módulo por nombre."""
        return self.modules.get(name)

    def get_system_status(self) -> dict:
        """Obtiene el estado del sistema para el HUD."""
        sc = self.modules.get("system_control")
        if sc:
            return sc.get_system_status()
        return {}
