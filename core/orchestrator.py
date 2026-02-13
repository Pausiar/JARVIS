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

        Flujo:
        1. Enfocar la app/pestaña fuente (donde está el contenido a leer)
        2. Minimizar JARVIS para no tapar el contenido
        3. Ctrl+A Ctrl+C para copiar TODO el contenido al portapapeles
        4. Leer el portapapeles → eso es el texto del ejercicio
        5. Restaurar JARVIS, enviar al LLM
        6. Enfocar la app/pestaña destino, escribir soluciones
        """
        import pyautogui
        sc = self.modules.get("system_control")
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

            # 3. Dar foco al contenido (clic en zona derecha, evitando sidebars)
            screen_w, screen_h = pyautogui.size()
            click_x = int(screen_w * 0.65)
            click_y = int(screen_h * 0.40)
            pyautogui.click(click_x, click_y)
            time.sleep(0.5)

            # 4. CAPTURA VÍA PORTAPAPELES  (Ctrl+A → Ctrl+C)
            #    Mucho más fiable que OCR para contenido web/PDFs en browser
            logger.info("Capturando contenido vía Ctrl+A + Ctrl+C...")
            pyautogui.hotkey('ctrl', 'a')   # Seleccionar todo
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'c')   # Copiar
            time.sleep(0.5)

            # Leer el portapapeles
            import subprocess
            clip_result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5
            )
            clipboard_text = clip_result.stdout.strip()
            logger.info(f"Portapapeles: {len(clipboard_text)} chars capturados")

            # Deseleccionar para no dejar marcado (clic en cualquier sitio)
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

            if not solutions or solutions.startswith(("Me temo", "No he podido")):
                return "No pude resolver los ejercicios. " + (solutions or "")

            logger.info(f"Soluciones generadas: {len(solutions)} caracteres")

            # 6. Minimizar JARVIS de nuevo para escribir en el documento
            self._minimize_jarvis_window()
            time.sleep(0.5)

            # 7. Enfocar la app/pestaña destino
            if target_app:
                logger.info(f"Enfocando app destino: {target_app}")
                focus_result = sc.focus_window(target_app)
                logger.info(f"Focus destino: {focus_result}")
                time.sleep(2.0)
            else:
                # Fallback: cambiar de pestaña en la misma app
                logger.info(f"Cambiando a pestaña {target_tab}...")
                sc.switch_tab(target_tab)
                time.sleep(2.0)

            # 8. Hacer clic en el cuerpo del documento/editor para asegurar foco
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

    def research_topic(self, topic: str) -> str:
        """Investiga proactivamente cómo hacer algo."""
        logger.info(f"Investigación solicitada: '{topic}'")
        return self.learner.research_and_learn(
            topic, failure_context="Investigación solicitada por el usuario"
        )

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
