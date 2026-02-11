"""
J.A.R.V.I.S. — Command Parser
Interpreta las intenciones del usuario y las traduce en acciones.
"""

import re
import json
import logging
from typing import Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("jarvis.command_parser")


class CommandIntent:
    """Representa una intención de comando del usuario."""

    def __init__(
        self,
        module: str,
        function: str,
        params: dict = None,
        confidence: float = 1.0,
        raw_text: str = "",
    ):
        self.module = module
        self.function = function
        self.params = params or {}
        self.confidence = confidence
        self.raw_text = raw_text

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "function": self.function,
            "params": self.params,
            "confidence": self.confidence,
        }

    def __repr__(self):
        return (
            f"CommandIntent(module={self.module!r}, "
            f"function={self.function!r}, "
            f"params={self.params!r}, "
            f"confidence={self.confidence:.2f})"
        )


class CommandParser:
    """
    Analiza el texto del usuario y determina la intención.
    Combina detección por patrones (rápido) con análisis LLM (complejo).
    """

    def __init__(self):
        self._patterns = self._build_patterns()
        logger.info("CommandParser inicializado.")

    def _build_patterns(self) -> list:
        """
        Construye patrones regex para detección rápida de intenciones.
        Cada patrón es una tupla: (regex_compilado, módulo, función, extractor_params)
        """
        patterns = []

        # ─── Gestión de archivos ──────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:abre|abrir|open)\s+(?:el\s+)?(?:archivo\s+)?(.+\.(?:pdf|docx?|xlsx?|txt|csv|json|md|py|js|html))",
                    re.IGNORECASE,
                ),
                "file_manager", "open_file",
                lambda m: {"file_path": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:crea|crear|create)\s+(?:una?\s+)?(?:carpeta|directorio|folder)\s+(?:llamada?\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "file_manager", "create_directory",
                lambda m: {"dir_name": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:busca|buscar|search|encuentra|find)\s+(?:el\s+)?archivo\s+(.+)",
                    re.IGNORECASE,
                ),
                "file_manager", "search_files",
                lambda m: {"query": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:organiza|organizar|organize)\s+(?:los\s+)?(?:archivos\s+)?(?:de\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "file_manager", "organize_files",
                lambda m: {"directory": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:elimina|eliminar|borra|borrar|delete|remove)\s+(?:el\s+)?(?:archivo\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "file_manager", "delete_file",
                lambda m: {"file_path": m.group(1).strip()},
            ),
        ])

        # ─── Documentos ──────────────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:lee|leer|read)\s+(?:el\s+)?(?:pdf|documento)\s+(.+)",
                    re.IGNORECASE,
                ),
                "document_processor", "read_document",
                lambda m: {"file_path": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:resume|resumir|summarize)\s+(?:el\s+)?(?:pdf|documento|archivo)\s+(.+)",
                    re.IGNORECASE,
                ),
                "document_processor", "summarize_document",
                lambda m: {"file_path": m.group(1).strip()},
            ),
        ])

        # ─── Control del Sistema ──────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:abre|abrir|open|ejecuta|ejecutar|lanza|launch|inicia|start|arranca|abrirme|ábrema|ábreme|abrirme)\s+(?:la\s+)?(?:app\s+|aplicaci[oó]n\s+)?(.+?)(?:\s+(?:y\s+)?(?:busca|buscar|entra|entrar|encuentra|encontrar|cierra|cerrar|pon|poner|después|luego|manda|envía|ejecuta|haz)|[,;.]|\s*$)",
                    re.IGNORECASE,
                ),
                "system_control", "open_application",
                lambda m: {"app_name": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:puedes?\s+)?(?:abrirme|abrirle|abrir)\s+(?:la\s+)?(?:app\s+|aplicaci[oó]n\s+)?(.+?)(?:\s+(?:y\s+)?(?:busca|buscar|entra|entrar|encuentra|encontrar|cierra|cerrar)|[,;.]|\s*\??$)",
                    re.IGNORECASE,
                ),
                "system_control", "open_application",
                lambda m: {"app_name": m.group(1).strip().rstrip("?")},
            ),
            (
                re.compile(
                    r"(?:cierra|cerrar|close|kill|termina)\s+(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "close_application",
                lambda m: {"app_name": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:sube|subir|aumenta|aumentar|up)\s+(?:el\s+)?volumen(?:\s+(?:a|al)\s+(\d+))?",
                    re.IGNORECASE,
                ),
                "system_control", "volume_up",
                lambda m: {"amount": int(m.group(1)) if m.group(1) else 10},
            ),
            (
                re.compile(
                    r"(?:baja|bajar|reduce|reducir|down)\s+(?:el\s+)?volumen(?:\s+(?:a|al)\s+(\d+))?",
                    re.IGNORECASE,
                ),
                "system_control", "volume_down",
                lambda m: {"amount": int(m.group(1)) if m.group(1) else 10},
            ),
            (
                re.compile(
                    r"(?:pon|poner|set)\s+(?:el\s+)?volumen\s+(?:a|al|en)\s+(\d+)",
                    re.IGNORECASE,
                ),
                "system_control", "set_volume",
                lambda m: {"level": int(m.group(1))},
            ),
            (
                re.compile(r"(?:silencia|silenciar|mute|mutear)", re.IGNORECASE),
                "system_control", "mute", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:sube|subir|aumenta|aumentar)\s+(?:el\s+)?brillo(?:\s+(?:a|al)\s+(\d+))?",
                    re.IGNORECASE,
                ),
                "system_control", "brightness_up",
                lambda m: {"amount": int(m.group(1)) if m.group(1) else 10},
            ),
            (
                re.compile(
                    r"(?:baja|bajar|reduce|reducir)\s+(?:el\s+)?brillo(?:\s+(?:a|al)\s+(\d+))?",
                    re.IGNORECASE,
                ),
                "system_control", "brightness_down",
                lambda m: {"amount": int(m.group(1)) if m.group(1) else 10},
            ),
            (
                re.compile(
                    r"(?:apaga|apagar|shutdown)\s+(?:el\s+)?(?:pc|ordenador|computador|equipo)",
                    re.IGNORECASE,
                ),
                "system_control", "shutdown", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:reinicia|reiniciar|restart|reboot)\s*(?:el\s+)?(?:pc|ordenador|computador|equipo)?",
                    re.IGNORECASE,
                ),
                "system_control", "restart", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:captura|capturar|screenshot|pantallazo)\s*(?:de\s+)?(?:pantalla)?",
                    re.IGNORECASE,
                ),
                "system_control", "screenshot", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:info|información|informacion|status)\s+(?:del\s+)?(?:sistema|system)",
                    re.IGNORECASE,
                ),
                "system_control", "system_info", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:bloquea|bloquear|lock)\s+(?:la\s+)?(?:pantalla|screen)",
                    re.IGNORECASE,
                ),
                "system_control", "lock_screen", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:vacía|vaciar|empty)\s+(?:la\s+)?(?:papelera|trash|recycle)",
                    re.IGNORECASE,
                ),
                "system_control", "empty_recycle_bin", lambda m: {},
            ),
        ])

        # ─── Búsqueda en página/app activa (ANTES de web search) ──
        # SOLO se activa cuando hay contexto explícito de estar en una app/web
        patterns.extend([
            (
                re.compile(
                    r"(?:en\s+(?:la\s+)?(?:pestaña|página|pagina|interfaz|web|app|aplicación|aplicacion|ventana)\s+.+?)(?:busca|buscar|search|encuentra|encontrar)\s+(?:a\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "search_in_page",
                lambda m: {"text": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:dentro\s+de\s+(?:la\s+)?(?:interfaz|web|app|aplicación|pagina|página)\s+.+?)(?:busca|buscar|search|encuentra|encontrar)\s+(?:a\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "search_in_page",
                lambda m: {"text": m.group(1).strip()},
            ),
        ])

        # ─── Búsqueda Web ────────────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:busca|buscar|search|google)\s+en\s+(?:internet|la\s+web|google|chrome)\s+(.+)",
                    re.IGNORECASE,
                ),
                "web_search", "search",
                lambda m: {"query": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:busca|buscar|search|googlea|googlear)\s+(?!el\s+archivo)(.+)",
                    re.IGNORECASE,
                ),
                "web_search", "search",
                lambda m: {"query": m.group(1).strip()},
            ),
        ])

        # ─── Email ──────────────────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:envía|enviar|send|manda|mandar)\s+(?:un\s+)?(?:correo|email|mail)\s+(?:a\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "email_manager", "send_email",
                lambda m: {"recipient": m.group(1).strip()},
            ),
        ])

        # ─── Código ─────────────────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:ejecuta|ejecutar|run|corre|correr)\s+(?:el\s+)?(?:script|código|code|programa)\s+(.+)",
                    re.IGNORECASE,
                ),
                "code_executor", "execute_file",
                lambda m: {"file_path": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:escribe|escribir|write|genera|generar|crea|crear)\s+(?:un\s+)?(?:script|código|code|programa)\s+(?:que\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "code_executor", "generate_code",
                lambda m: {"description": m.group(1).strip()},
            ),
        ])

        # ─── Interacción con aplicaciones ─────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:selecciona|seleccionar|select|elige|elegir|choose)\s+(?:el\s+)?(?:perfil|profile|cuenta|account)\s+(?:de\s+|que\s+(?:pone|dice|se\s+llama)\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "select_profile",
                lambda m: {"profile_name": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:selecciona|seleccionar|select|elige|elegir|choose|entra|entrar)\s+(?:en\s+)?(?:la\s+)?(?:pestaña|página|pagina|ventana|interfaz|web|app)\s+.*?(?:perfil|profile|cuenta|account)\s+(?:de\s+|que\s+(?:pone|dice|se\s+llama)\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "select_profile",
                lambda m: {"profile_name": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:en\s+(?:la\s+)?(?:pestaña|página|ventana)\s+.+?)(?:selecciona|seleccionar|elige|elegir)\s+(?:el\s+)?(?:perfil|profile|cuenta)\s+(?:de\s+|que\s+(?:pone|dice|se\s+llama)\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "select_profile",
                lambda m: {"profile_name": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:haz\s+clic|clic|click|pulsa|pincha|presiona|press)\s+(?:en\s+)?(?:el\s+|la\s+|los\s+|las\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "click_on_text",
                lambda m: {"text": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:escribe|escribir|type|teclea|teclear)\s+(?:en\s+\w+\s+)?[\"']?(.+?)[\"']?\s*$",
                    re.IGNORECASE,
                ),
                "system_control", "type_in_app",
                lambda m: {"text": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:navega|navegar|navigate|ve|ir)\s+(?:a|to)\s+(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "navigate_to_url",
                lambda m: {"url": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:doble\s+clic|double\s+click)\s+(?:en\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "double_click",
                lambda m: {"text": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:scroll|desplaza|desplazar)\s+(?:hacia\s+)?(?:arriba|abajo|up|down)",
                    re.IGNORECASE,
                ),
                "system_control", "scroll_page",
                lambda m: {"direction": "up" if any(w in m.group(0).lower() for w in ["arriba", "up"]) else "down"},
            ),
            (
                re.compile(
                    r"(?:entra|entrar|enter|accede|acceder)\s+(?:a|en|al|to)\s+(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "click_on_text",
                lambda m: {"text": m.group(1).strip()},
            ),
        ])

        # ─── Hora / Fecha ────────────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:qué|que|what)\s+hora\s+(?:es|time)",
                    re.IGNORECASE,
                ),
                "system_control", "get_time", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:qué|que|what)\s+(?:día|dia|fecha|date)\s+(?:es)?",
                    re.IGNORECASE,
                ),
                "system_control", "get_date", lambda m: {},
            ),
        ])

        # ─── Memoria ────────────────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:recuerdas?|remember)\s+(.+)",
                    re.IGNORECASE,
                ),
                "memory", "recall",
                lambda m: {"query": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:borra|borrar|clear|limpia|limpiar)\s+(?:el\s+)?(?:historial|memoria|history|memory)",
                    re.IGNORECASE,
                ),
                "memory", "clear_memory", lambda m: {},
            ),
        ])

        return patterns

    # ─── Parsing ──────────────────────────────────────────────

    def parse(self, text: str) -> Optional[CommandIntent]:
        """
        Analiza el texto y devuelve la intención detectada.

        Args:
            text: Texto del usuario.

        Returns:
            CommandIntent o None si no se detecta intención directa.
        """
        text = text.strip()
        if not text:
            return None

        # Detectar contexto in-app
        in_app_context = bool(re.search(
            r"(?:en\s+la\s+)?(?:pestaña|página|pagina|interfaz|ventana)"
            r"|dentro\s+de\s+(?:la\s+)?(?:interfaz|web|app|aplicación|pagina|página)"
            r"|(?:en\s+la\s+)?(?:web|app)\s+(?:del|de la|de)",
            text, re.IGNORECASE
        ))

        # Intentar detección por patrones
        intent = self._match_patterns(text)
        if intent:
            # Si hay contexto in-app, redirigir búsquedas web a búsqueda en página
            if in_app_context and intent.module == "web_search" and intent.function == "search":
                query = intent.params.get("query", "")
                query = re.sub(
                    r"^(?:a|en|al|la|el|del|de la)\s+",
                    "", query, flags=re.IGNORECASE
                ).strip()
                intent = CommandIntent(
                    module="system_control",
                    function="search_in_page",
                    params={"text": query},
                    confidence=0.9,
                    raw_text=text,
                )
            logger.info(f"Intención detectada por patrón: {intent}")
            return intent

        # Si no se detecta patrón, devolver None (el orquestador usará el LLM)
        logger.info("No se detectó intención por patrón. Se usará el LLM.")
        return None

    def parse_compound(self, text: str) -> list[CommandIntent]:
        """
        Analiza texto que puede contener múltiples comandos.
        Divide en límites de verbos de acción, no solo por 'y'.
        Ej: 'abre chrome y busca hola' → [open_application(chrome), search(hola)]
        Ej: 'abre google busca hola' → [open_application(google), search(hola)]
        """
        intents = []

        # Verbos de acción que inician un nuevo comando
        _action_verbs = (
            r"abre|abrir|open|ejecuta|ejecutar|lanza|launch|inicia|start|arranca"
            r"|busca|buscar|search|googlea|googlear"
            r"|cierra|cerrar|close|kill|termina"
            r"|pon|poner|set|sube|subir|baja|bajar"
            r"|entra|entrar|encuentra|encontrar"
            r"|envía|enviar|send|manda|mandar"
            r"|haz|hacer|captura|capturar"
            r"|selecciona|seleccionar|elige|elegir"
            r"|clic|click|pulsa|pincha|presiona"
            r"|navega|navegar|escribe|escribir|teclea"
            r"|scroll|desplaza"
        )

        # Paso 1: dividir por 'y' / 'y luego' / 'y después' / comas
        parts = re.split(
            r"\s+y\s+(?:luego\s+|después\s+|también\s+)?"
            r"|\s*,\s*(?:y\s+)?",
            text, flags=re.IGNORECASE
        )

        # Paso 2: dentro de cada parte, dividir en límites de verbos de acción
        # Ej: "abre google busca hola" → ["abre google", "busca hola"]
        expanded_parts = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            sub_parts = re.split(
                rf"\s+(?=(?:{_action_verbs})\s)",
                part, flags=re.IGNORECASE
            )
            expanded_parts.extend(p.strip() for p in sub_parts if p.strip())

        # Paso 3: detectar contexto global del input
        # Si el texto menciona "pestaña actual", "dentro de", "interfaz",
        # "en la web", las acciones de buscar deben ser en-app, no web.
        in_app_context = bool(re.search(
            r"(?:en\s+la\s+)?(?:pestaña|página|pagina|interfaz|ventana)"
            r"|dentro\s+de\s+(?:la\s+)?(?:interfaz|web|app|aplicación|pagina|página)"
            r"|(?:en\s+la\s+)?(?:web|app)\s+(?:del|de la|de)",
            text, re.IGNORECASE
        ))

        # Paso 4: intentar detectar intención en cada fragmento
        for part in expanded_parts:
            intent = self._match_patterns(part)
            if intent:
                # Si hay contexto in-app y el intent es web_search,
                # convertirlo en search_in_page
                if in_app_context and intent.module == "web_search" and intent.function == "search":
                    query = intent.params.get("query", "")
                    # Limpiar prefijos comunes del query
                    query = re.sub(
                        r"^(?:a|en|al|la|el|del|de la)\s+",
                        "", query, flags=re.IGNORECASE
                    ).strip()
                    intent = CommandIntent(
                        module="system_control",
                        function="search_in_page",
                        params={"text": query},
                        confidence=0.9,
                        raw_text=part,
                    )
                intents.append(intent)

        # Si no se encontró nada con el split, intentar como comando único
        if not intents:
            intent = self._match_patterns(text)
            if intent:
                intents.append(intent)

        return intents

    def _match_patterns(self, text: str) -> Optional[CommandIntent]:
        """Intenta coincidir el texto con patrones conocidos."""
        for pattern, module, function, param_extractor in self._patterns:
            match = pattern.search(text)
            if match:
                try:
                    params = param_extractor(match)
                    return CommandIntent(
                        module=module,
                        function=function,
                        params=params,
                        confidence=0.85,
                        raw_text=text,
                    )
                except Exception as e:
                    logger.warning(f"Error extrayendo parámetros: {e}")
                    continue
        return None

    def parse_llm_actions(self, llm_response: str) -> list[CommandIntent]:
        """
        Extrae intenciones de acción de una respuesta del LLM.

        Args:
            llm_response: Respuesta del LLM que puede contener [ACTION:{...}]

        Returns:
            Lista de CommandIntent extraídas.
        """
        intents = []
        pattern = r'\[ACTION:(.*?)\]'
        matches = re.findall(pattern, llm_response)

        for match in matches:
            try:
                data = json.loads(match)
                intent = CommandIntent(
                    module=data.get("module", ""),
                    function=data.get("function", ""),
                    params=data.get("params", {}),
                    confidence=0.95,
                    raw_text=llm_response,
                )
                intents.append(intent)
            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando acción JSON: {e}")

        return intents

    def is_greeting(self, text: str) -> bool:
        """Detecta si el texto es un saludo (solo si es predominantemente un saludo)."""
        text_clean = text.lower().strip().rstrip("?!.,")
        # Eliminar "jarvis" del texto para el análisis
        text_clean = re.sub(r"\bjarvis\b", "", text_clean).strip()

        # Solo es saludo si el texto es corto (menos de 6 palabras)
        if len(text_clean.split()) > 5:
            return False

        greetings = [
            r"^hola$", r"^hey$", r"^hello$", r"^hi$",
            r"^buenos\s+días$", r"^buenas\s+tardes$", r"^buenas\s+noches$",
            r"^good\s+morning$", r"^good\s+afternoon$", r"^good\s+evening$",
            r"^qué\s+tal$", r"^cómo\s+estás$", r"^que\s+tal$",
            r"^hola\s+que\s+tal$", r"^hola\s+qué\s+tal$",
            r"^buenas$", r"^saludos$",
        ]
        for greeting in greetings:
            if re.search(greeting, text_clean):
                return True
        return False

    def is_farewell(self, text: str) -> bool:
        """Detecta si el texto es una despedida (solo si es predominantemente una despedida)."""
        text_clean = text.lower().strip().rstrip("?!.,")
        text_clean = re.sub(r"\bjarvis\b", "", text_clean).strip()

        if len(text_clean.split()) > 5:
            return False

        farewells = [
            r"^adiós$", r"^adios$", r"^chao$", r"^bye$", r"^goodbye$",
            r"^hasta\s+luego$", r"^nos\s+vemos$", r"^hasta\s+mañana$",
            r"^hasta\s+pronto$", r"^buenas\s+noches$",
        ]
        for farewell in farewells:
            if re.search(farewell, text_clean):
                return True
        return False

    def is_confirmation(self, text: str) -> bool:
        """Detecta si el texto es una confirmación."""
        confirmations = [
            r"\bsí\b", r"\bsi\b", r"\byes\b", r"\bok\b", r"\bokay\b",
            r"claro", r"por\s+supuesto", r"adelante", r"hazlo",
            r"dale", r"vale", r"perfecto", r"sure", r"go\s+ahead",
        ]
        for conf in confirmations:
            if re.search(conf, text.lower()):
                return True
        return False

    def is_negation(self, text: str) -> bool:
        """Detecta si el texto es una negación."""
        negations = [
            r"\bno\b", r"nope", r"negativo", r"cancel", r"cancela",
            r"olvídalo", r"olvidalo", r"déjalo", r"dejalo", r"para",
        ]
        for neg in negations:
            if re.search(neg, text.lower()):
                return True
        return False
