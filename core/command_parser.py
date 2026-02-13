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

        # ─── Resolución de ejercicios (workflow multi-paso) ───
        patterns.extend([
            # ─── NUEVO: Patrón flexible con app fuente y app destino ──
            # "mira el ejercicio 2 en el tab de google y hazmelo en intellij"
            # "lee el ejercicio 3 en chrome y escríbelo en word"
            # "coge el ejercicio 1 de google y resuélvelo en intellij"
            # "mira lo de google y ponlo en intellij"
            (
                re.compile(
                    r"(?:mira|lee|coge|abre|ve)\s+"
                    r"(.+?)\s+"
                    r"(?:en\s+)?(?:el\s+)?(?:tab|pestaña|ventana)?\s*(?:de\s+|en\s+)"
                    r"([\w]+(?:\s+[\w]+)?)\s+"
                    r"y\s+(?:h[aá]zmelo|escr[ií]belo|resu[eé]lvelo|ponlo|m[eé]telo|h[aá]zlo|p[aá]samo)\s+"
                    r"(?:en\s+)"
                    r"([\w]+(?:\s+[\w]+)?)",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_screen_exercises",
                lambda m: {
                    "source_app": m.group(2).strip(),
                    "target_app": m.group(3).strip(),
                    "content_hint": m.group(1).strip(),
                },
            ),
            # "resuelve el ejercicio 2 de google en intellij"
            # "haz el ejercicio 5 de chrome en word"
            (
                re.compile(
                    r"(?:resuelve|haz|soluciona|completa)\s+"
                    r"(.+?)\s+"
                    r"(?:de|del?|que\s+(?:hay|está?)\s+en)\s+"
                    r"(\w+(?:\s+\w+)?)\s+"
                    r"(?:en|y\s+(?:escr[ií]be|pon|mete|p[oó]n)(?:lo|los?)?\s+en)\s+"
                    r"(\w+(?:\s+\w+)?)",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_screen_exercises",
                lambda m: {
                    "source_app": m.group(2).strip(),
                    "target_app": m.group(3).strip(),
                    "content_hint": m.group(1).strip(),
                },
            ),
            # "mira lo que hay en google y hazmelo en intellij"
            # "lee lo de chrome y escríbelo en word"
            (
                re.compile(
                    r"(?:mira|lee|coge)\s+"
                    r"(?:lo\s+(?:que\s+(?:hay|se\s+ve|está?|aparece)|del?)\s+)"
                    r"(?:en\s+)?(\w+(?:\s+\w+)?)\s+"
                    r"(?:y\s+)?(?:h[aá]zmelo|escr[ií]belo|resu[eé]lvelo|ponlo|m[eé]telo|h[aá]zlo|p[aá]samo)\s+"
                    r"(?:en\s+)"
                    r"(\w+(?:\s+\w+)?)",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_screen_exercises",
                lambda m: {
                    "source_app": m.group(1).strip(),
                    "target_app": m.group(2).strip(),
                    "content_hint": "",
                },
            ),
            # "haz lo de google en intellij" / "resuelve lo de chrome en word"
            (
                re.compile(
                    r"(?:haz|resuelve|soluciona|completa|pon|mete|escribe)\s+"
                    r"(?:lo\s+(?:de|del?|que\s+(?:hay|está?)\s+en)\s+)"
                    r"(\w+(?:\s+\w+)?)\s+"
                    r"en\s+"
                    r"(\w+(?:\s+\w+)?)",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_screen_exercises",
                lambda m: {
                    "source_app": m.group(1).strip(),
                    "target_app": m.group(2).strip(),
                    "content_hint": "",
                },
            ),
            # ─── Resolver ejercicios de PANTALLA/PESTAÑA y escribir en documento ──
            # "resuelve los ejercicios del PDF y escríbelos en el documento de Google"
            # "haz los ejercicios de la pantalla y ponlos en la otra pestaña"
            # "resuelve lo que hay en la pestaña del PDF y mételo en el documento"
            (
                re.compile(
                    r"(?:resuelve|resolver|haz|hacer|soluciona|solucionar|completa|completar)\s+"
                    r"(?:(?:los?|el)\s+)?(?:ejercicios?|preguntas?|problemas?|actividades?)\s+"
                    r"(?:(?:del?|que\s+hay\s+en)\s+)?(?:(?:la\s+)?(?:pantalla|pestaña|p[aá]gina|ventana)|(?:el\s+)?pdf|(?:ese|este|el)\s+pdf)\s*"
                    r"(?:(?:y\s+)?(?:escr[ií]be|pon|mete|pega|p[oó]n|inserta)(?:los?|las?|l[oa])?\s+"
                    r"(?:en\s+)?(?:el\s+|la\s+|otra?\s+)?(?:documento|google\s*docs?|doc|pestaña|word|hoja))?",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_screen_exercises",
                lambda m: {"target_tab": "next"},
            ),
            # "resuelve los ejercicios y ponlos en el documento"
            # (sin especificar "del PDF" — asume que el PDF está en pantalla)
            (
                re.compile(
                    r"(?:resuelve|resolver|haz|hacer|soluciona)\s+"
                    r"(?:(?:los?|el)\s+)?(?:ejercicios?|preguntas?|problemas?)\s+"
                    r"(?:y\s+)?(?:escr[ií]be|pon|mete|pega|p[oó]n|inserta)(?:los?|las?|l[oa])?\s+"
                    r"(?:en\s+)?(?:el\s+|la\s+|otra?\s+)?(?:documento|google\s*docs?|doc|pestaña|word|hoja)",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_screen_exercises",
                lambda m: {"target_tab": "next"},
            ),
            # "resuelve lo que hay en pantalla y escríbelo en la otra pestaña"
            (
                re.compile(
                    r"(?:resuelve|resolver|haz|hacer|soluciona)\s+"
                    r"(?:lo\s+que\s+(?:hay|ves?|se\s+ve|aparece)\s+(?:en\s+)?(?:la\s+)?(?:pantalla|pestaña)|esto|eso)\s*"
                    r"(?:(?:y\s+)?(?:escr[ií]be|pon|mete|pega|inserta)(?:lo|los?|las?|l[oa])?\s+"
                    r"(?:en\s+)?(?:el\s+|la\s+|otra?\s+)?(?:documento|google\s*docs?|doc|pestaña|word|hoja))?",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_screen_exercises",
                lambda m: {"target_tab": "next"},
            ),
            # "resuelve los ejercicios del PDF" (sin especificar destino — solo lee y resuelve)
            (
                re.compile(
                    r"(?:resuelve|resolver|haz|hacer|soluciona)\s+"
                    r"(?:(?:los?|el)\s+)?(?:ejercicios?|preguntas?|problemas?|actividades?)\s+"
                    r"(?:del?\s+)?(?:(?:ese|este|el)\s+)?pdf\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_screen_exercises",
                lambda m: {"target_tab": "next"},
            ),
            # ─── Resolver ejercicios de ARCHIVO local ──
            (
                re.compile(
                    r"(?:resuelve|resolver|haz|hacer|soluciona|solucionar|completa|completar)\s+"
                    r"(?:(?:los?|el)\s+)?(?:ejercicios?\s+)?(?:del?\s+)?(?:pdf|documento|archivo)\s+"
                    r"(.+?)(?:\s+en\s+(.+?))?\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_exercises",
                lambda m: {
                    "file_path": m.group(1).strip().strip("\"'"),
                    "output_app": m.group(2).strip().strip("\"'") if m.group(2) else "",
                },
            ),
            (
                re.compile(
                    r"(?:resuelve|resolver|haz|hacer)\s+(?:los?\s+)?ejercicios?\s+(?:que\s+)?(?:hay|tiene|están?)\s+"
                    r"(?:en\s+)?(?:el\s+)?(?:pdf|documento|archivo)\s+(.+?)(?:\s+(?:y\s+)?(?:escr[ií]be|pon|mete)(?:los?)?\s+en\s+(.+?))?\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_exercises",
                lambda m: {
                    "file_path": m.group(1).strip().strip("\"'"),
                    "output_app": m.group(2).strip().strip("\"'") if m.group(2) else "",
                },
            ),
            # "contesta las preguntas del PDF X"
            (
                re.compile(
                    r"(?:contesta|contestar|responde|responder)\s+(?:las?\s+)?(?:preguntas?|cuestiones?)\s+"
                    r"(?:del?\s+)?(?:pdf|documento|archivo)\s+(.+?)(?:\s+en\s+(.+?))?\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "solve_exercises",
                lambda m: {
                    "file_path": m.group(1).strip().strip("\"'"),
                    "output_app": m.group(2).strip().strip("\"'") if m.group(2) else "",
                },
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
            # ─── Pegar / escribir la última respuesta en app activa ──
            # Estos patrones DEBEN ir ANTES del genérico "escribe X"
            # para evitar que "escribe la respuesta ahí" se interprete
            # como type_in_app(text="la respuesta ahí")
            (
                re.compile(
                    r"(?:pega|pegar|paste|mete|meter|inserta|insertar|pon|poner)\s+"
                    r"(?:la\s+)?(?:respuesta|eso|esto|el\s+texto|lo\s+(?:anterior|que\s+dijiste|que\s+me\s+dijiste))\s*"
                    r"(?:en\s+(?:el\s+)?(?:documento|doc|word|google\s*docs?|archivo|editor|bloc|app|aplicaci[oó]n))?\s*"
                    r"(?:ah[ií]|aqu[ií]|all[ií])?\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "paste_last_response",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:p[eé]gal[oa]|escr[ií]bel[oa]|p[oó]nl[oa]|m[eé]tel[oa]|ins[eé]rtal[oa])\s*"
                    r"(?:en\s+(?:el\s+)?(?:documento|doc|word|google\s*docs?|archivo|editor|bloc))?\s*"
                    r"(?:ah[ií]|aqu[ií]|all[ií])?\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "paste_last_response",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:pega|pegar|paste|mete|meter|inserta|insertar|pon|poner)\s*"
                    r"(?:la|lo|el|le|me|se)?\s*"
                    r"(?:en\s+(?:el\s+)?(?:documento|doc|word|google\s*docs?|archivo|editor|bloc))\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "paste_last_response",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:ahora\s+)?(?:pega|mete|pon|inserta|escribe)\s*"
                    r"(?:la|lo|el|eso|esto)?\s*"
                    r"(?:ah[ií]|aqu[ií]|all[ií])\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "paste_last_response",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:escribe|escribir)\s+(?:la\s+)?(?:respuesta|eso|esto|lo\s+anterior|lo\s+que\s+dijiste)\s+"
                    r"(?:en\s+(?:el\s+)?(?:documento|doc|word|google\s*docs?|archivo|editor|bloc)\s*)?"
                    r"(?:ah[ií]|aqu[ií]|all[ií])?\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "paste_last_response",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:pega|paste)\s+(?:ah[ií]|aqu[ií]|all[ií])\s*$",
                    re.IGNORECASE,
                ),
                "orchestrator", "paste_last_response",
                lambda m: {},
            ),
            # ───────────────────────────────────────────────────────
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
            # ─── Describe and click (clic por descripción con LLM) ──
            (
                re.compile(
                    r"(?:haz\s+clic|clic|click|pulsa|pincha)\s+(?:en\s+)?"
                    r"(?:donde\s+(?:pone|dice|hay|est[aá]|esta)|lo\s+que\s+(?:dice|pone))\s+(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "describe_and_click",
                lambda m: {"description": m.group(1).strip()},
            ),
            (
                re.compile(
                    r"(?:haz\s+clic|clic|click|pulsa|pincha)\s+(?:en\s+)?"
                    r"(?:el\s+|la\s+|los\s+|las\s+)?(?:bot[oó]n|enlace|link|icono|opci[oó]n)\s+"
                    r"(?:de\s+|que\s+(?:dice|pone)\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "describe_and_click",
                lambda m: {"description": m.group(1).strip()},
            ),
            # ─── Focus window / enfoque de ventana ──
            (
                re.compile(
                    r"(?:enfoca|enfocar|cambia\s+a|switch\s+to|focus|trae|traer)\s+"
                    r"(?:la\s+)?(?:ventana\s+(?:de\s+)?|window\s+)?(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "focus_window",
                lambda m: {"app_name": m.group(1).strip()},
            ),
            # ─── Portapapeles ──
            (
                re.compile(
                    r"(?:lee|leer|qu[eé]\s+hay|que\s+hay|muestra|mostrar|dime)\s+"
                    r"(?:en\s+)?(?:el\s+)?(?:portapapeles|clipboard)",
                    re.IGNORECASE,
                ),
                "system_control", "read_clipboard",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:copia|copiar|copy)\s+(?:al\s+)?(?:portapapeles|clipboard)\s+(.+)",
                    re.IGNORECASE,
                ),
                "system_control", "copy_to_clipboard",
                lambda m: {"text": m.group(1).strip()},
            ),
            # ─── Lectura de pantalla (qué hay en pantalla) ──
            (
                re.compile(
                    r"(?:qu[eé]|que|what)\s+(?:hay|pone|dice[n]?|se\s+ve|aparece)\s+"
                    r"(?:en\s+)?(?:la\s+)?(?:pantalla|screen)",
                    re.IGNORECASE,
                ),
                "system_control", "get_screen_text",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:lee|leer|describe|describir|dime)\s+(?:lo\s+que\s+(?:hay|dice|pone)\s+en\s+)?(?:la\s+)?(?:pantalla|screen)",
                    re.IGNORECASE,
                ),
                "system_control", "get_screen_text",
                lambda m: {},
            ),
            # ─── Gestión de pestañas ──
            (
                re.compile(
                    r"(?:abre|abrir|open)\s+(?:una\s+)?(?:nueva\s+)?(?:pesta[\u00f1n]a|tab)",
                    re.IGNORECASE,
                ),
                "system_control", "new_tab",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:cierra|cerrar|close)\s+(?:la\s+|esta\s+)?(?:pesta[\u00f1n]a|tab)",
                    re.IGNORECASE,
                ),
                "system_control", "close_tab",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:cambia|cambiar|switch|pasa|pasar)\s+(?:de\s+|a\s+(?:la\s+)?)?"
                    r"(?:(?:siguiente|anterior|next|previous|prev)\s+)?"
                    r"(?:pesta[\u00f1n]a|tab)(?:\s+(?:siguiente|anterior|next|previous|prev))?",
                    re.IGNORECASE,
                ),
                "system_control", "switch_tab",
                lambda m: {"direction": "previous" if any(w in m.group(0).lower()
                           for w in ["anterior", "previous", "prev"]) else "next"},
            ),
            # ─── Gestión de ventanas ──
            (
                re.compile(
                    r"(?:minimiza|minimizar|minimize)\s+(?:la\s+)?(?:ventana|window)?",
                    re.IGNORECASE,
                ),
                "system_control", "minimize_window",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:maximiza|maximizar|maximize)\s+(?:la\s+)?(?:ventana|window)?",
                    re.IGNORECASE,
                ),
                "system_control", "maximize_window",
                lambda m: {},
            ),
            (
                re.compile(
                    r"(?:ajusta|ajustar|snap)\s+(?:la\s+)?(?:ventana|window)\s+"
                    r"(?:a\s+)?(?:la\s+)?(izquierda|derecha|left|right)",
                    re.IGNORECASE,
                ),
                "system_control", "snap_window",
                lambda m: {"position": m.group(1).strip()},
            ),
            # ─── Primer link/resultado (ANTES de 'entra en' genérico) ──
            (
                re.compile(
                    r"(?:entra|entrar|enter|abre|abrir|open|haz\s+clic|clic|click|pulsa|pincha)\s+"
                    r"(?:en\s+)?(?:el\s+)?(?:primer|first|1(?:er|ro)?)\s+"
                    r"(?:link|enlace|resultado|result)(?:\s+(?:de\s+)?(?:google|bing|la\s+búsqueda|busqueda|la\s+página|pagina))?",
                    re.IGNORECASE,
                ),
                "system_control", "click_first_result",
                lambda m: {},
            ),
            # ─── Mover usuario a canal de voz (Discord, TeamSpeak, etc.) ──
            (
                re.compile(
                    r"(?:mueve|mover|muevas|mueva|move|arrastra|arrastrar|lleva|llevar|traslada|trasladar)\s+"
                    r"(?:al?\s+)?(?:usuario\s+)?(.+?)\s+"
                    r"(?:al?\s+)?(?:el\s+)?canal\s+(?:de\s+voz\s+)?(.+?)\s*$",
                    re.IGNORECASE,
                ),
                "system_control", "move_discord_user",
                lambda m: {
                    "username": m.group(1).strip().strip("\"'"),
                    "channel": m.group(2).strip().strip("\"'"),
                },
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

        # ─── Vision / Análisis de pantalla con IA ─────────────
        patterns.extend([
            # "analiza la pantalla" → vision IA (LLaVA), NO coincide con "describe"
            (
                re.compile(
                    r"(?:analiza|analizar)\s+(?:la\s+)?pantalla"
                    r"(?:\s+(?:del\s+)?monitor\s+(\d+))?",
                    re.IGNORECASE,
                ),
                "vision", "describe_screen",
                lambda m: {"monitor": int(m.group(1)) - 1 if m.group(1) else 0},
            ),
            (
                re.compile(
                    r"(?:qu[eé]|que)\s+(?:ves|observas|detectas)\s+"
                    r"(?:en\s+)?(?:la\s+)?(?:pantalla|screen)"
                    r"(?:\s+(?:del\s+)?monitor\s+(\d+))?",
                    re.IGNORECASE,
                ),
                "vision", "describe_screen",
                lambda m: {"monitor": int(m.group(1)) - 1 if m.group(1) else 0},
            ),
            # "analiza la imagen X"
            (
                re.compile(
                    r"(?:analiza|analizar|describe|describir)\s+(?:la\s+)?imagen\s+(.+)",
                    re.IGNORECASE,
                ),
                "vision", "analyze_local_image",
                lambda m: {"image_path": m.group(1).strip().strip('"\'')},
            ),
            # "busca el botón X en pantalla"
            (
                re.compile(
                    r"(?:busca|buscar|encuentra|encontrar|localiza|localizar)\s+"
                    r"(?:el\s+|la\s+|los\s+|las\s+)?"
                    r"(?:bot[oó]n|icono|texto|elemento|campo)\s+(.+?)"
                    r"\s+(?:en\s+)?(?:la\s+)?pantalla",
                    re.IGNORECASE,
                ),
                "vision", "find_element",
                lambda m: {"element_description": m.group(1).strip()},
            ),
            # "lee el texto de la imagen X"
            (
                re.compile(
                    r"(?:lee|leer|extrae|extraer)\s+(?:el\s+)?texto\s+"
                    r"(?:de\s+)?(?:la\s+)?imagen\s+(.+)",
                    re.IGNORECASE,
                ),
                "vision", "read_image_text",
                lambda m: {"image_path": m.group(1).strip().strip('"\'')},
            ),
        ])

        # ─── Control multimedia ───────────────────────────────
        patterns.extend([
            # ─── YouTube (específico, ANTES de genérico) ──
            # Pausa YouTube / video
            (
                re.compile(
                    r"(?:pausa|pausar|pause|para|parar)\s+(?:el\s+)?(?:youtube|v[ií]deo|video)",
                    re.IGNORECASE,
                ),
                "media_control", "youtube_play_pause", lambda m: {},
            ),
            # YouTube fullscreen
            (
                re.compile(
                    r"(?:pon|poner|activa|activar)\s+(?:pantalla\s+completa|fullscreen)\s+"
                    r"(?:en\s+)?(?:el\s+)?(?:youtube|v[ií]deo|video)",
                    re.IGNORECASE,
                ),
                "media_control", "youtube_fullscreen", lambda m: {},
            ),
            # ─── Play/Pause genérico ──
            (
                re.compile(
                    r"(?:reproduce|reproducir|play|reanuda|reanudar)\s+(?:la\s+)?(?:m[uú]sica|canci[oó]n|audio|media)?",
                    re.IGNORECASE,
                ),
                "media_control", "play_pause", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:pausa|pausar|pause|para|parar)\s+(?:la\s+)?(?:m[uú]sica|canci[oó]n|audio|media|reproducci[oó]n)?",
                    re.IGNORECASE,
                ),
                "media_control", "play_pause", lambda m: {},
            ),
            # Siguiente canción
            (
                re.compile(
                    r"(?:siguiente|next)\s+(?:canci[oó]n|pista|track|tema|v[ií]deo|video)?",
                    re.IGNORECASE,
                ),
                "media_control", "next_track", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:pasa|pasar|skip)\s+(?:de\s+)?(?:canci[oó]n|pista|track|tema)?",
                    re.IGNORECASE,
                ),
                "media_control", "next_track", lambda m: {},
            ),
            # Canción anterior
            (
                re.compile(
                    r"(?:anterior|previous|prev)\s+(?:canci[oó]n|pista|track|tema)?",
                    re.IGNORECASE,
                ),
                "media_control", "previous_track", lambda m: {},
            ),
            (
                re.compile(
                    r"(?:vuelve|volver|pon)\s+(?:la\s+)?(?:canci[oó]n|pista|tema)\s+anterior",
                    re.IGNORECASE,
                ),
                "media_control", "previous_track", lambda m: {},
            ),
            # ¿Qué suena? / Now playing
            (
                re.compile(
                    r"(?:qu[eé]|que)\s+(?:est[aá]s?\s+)?(?:suena|sonando|reproduci[eé]ndo|playing|escuchando)"
                    r"|(?:qu[eé]|que)\s+canci[oó]n\s+(?:es|suena)",
                    re.IGNORECASE,
                ),
                "media_control", "spotify_now_playing", lambda m: {},
            ),
            # Volumen de app: "pon el volumen de spotify al 50"
            (
                re.compile(
                    r"(?:pon|poner|set|ajusta|ajustar)\s+(?:el\s+)?volumen\s+"
                    r"(?:de|del)\s+(.+?)\s+(?:a|al|en)\s+(\d+)",
                    re.IGNORECASE,
                ),
                "media_control", "set_app_volume",
                lambda m: {"app_name": m.group(1).strip(), "volume": int(m.group(2)) / 100},
            ),
            # Mutear app: "silencia spotify"
            (
                re.compile(
                    r"(?:silencia|silenciar|mutea|mutear|mute)\s+(.+)",
                    re.IGNORECASE,
                ),
                "media_control", "mute_app",
                lambda m: {"app_name": m.group(1).strip()},
            ),
        ])

        # ─── Calendario ──────────────────────────────────────
        patterns.extend([
            # "añade evento X en 30 minutos" (formato específico: en X tiempo)
            (
                re.compile(
                    r"(?:crea|crear|a[ñn]ade|a[ñn]adir|agenda|agendar|programa|programar)\s+"
                    r"(?:un\s+)?(?:evento|cita|reunión|reunion|recordatorio)\s+"
                    r"(.+?)\s+en\s+(\d+)\s+(minutos?|horas?|min|h|segundos?|seg)",
                    re.IGNORECASE,
                ),
                "calendar", "add_event",
                lambda m: {
                    "title": m.group(1).strip(),
                    "start_time": f"en {m.group(2)} {'minutos' if 'seg' in m.group(3).lower() or 'segundo' in m.group(3).lower() else m.group(3)}",
                },
            ),
            # "crea un evento X a las HH:MM" / "añade evento X mañana a las 15"
            (
                re.compile(
                    r"(?:crea|crear|a[ñn]ade|a[ñn]adir|agenda|agendar|programa|programar)\s+"
                    r"(?:un\s+)?(?:evento|cita|reunión|reunion|recordatorio)\s+"
                    r"(.+?)(?:\s+(?:para|el|a\s+las?)\s+(.+))?\s*$",
                    re.IGNORECASE,
                ),
                "calendar", "add_event",
                lambda m: {
                    "title": m.group(1).strip().rstrip(" para el a las"),
                    "start_time": m.group(2).strip() if m.group(2) else "",
                    "description": "",
                },
            ),
            # "recuérdame X en 30 minutos"
            (
                re.compile(
                    r"(?:recu[eé]rdame|recordar|rem[ií]ndeme|reminder)\s+"
                    r"(.+?)\s+(?:en|dentro\s+de)\s+(\d+)\s+(?:minutos?|horas?|min|h)",
                    re.IGNORECASE,
                ),
                "calendar", "add_event",
                lambda m: {
                    "title": m.group(1).strip(),
                    "start_time": f"en {m.group(2)} {'minutos' if any(x in m.group(0).lower() for x in ['min']) else 'horas' if 'hora' in m.group(0).lower() else 'minutos'}",
                    "description": "Recordatorio",
                },
            ),
            # "recuérdame X a las 5pm" / "recuérdame X mañana"
            (
                re.compile(
                    r"(?:recu[eé]rdame|recordar|rem[ií]ndeme)\s+(.+?)\s+"
                    r"(?:a\s+las?\s+|para\s+(?:las?\s+)?|(?:para\s+)?ma[ñn]ana|(?:para\s+)?hoy)(.+)?\s*$",
                    re.IGNORECASE,
                ),
                "calendar", "add_event",
                lambda m: {
                    "title": m.group(1).strip(),
                    "start_time": (m.group(2) or "").strip() if m.group(2) else "mañana" if "mañana" in m.group(0).lower() else "hoy",
                    "description": "Recordatorio",
                },
            ),
            # "eventos de hoy" / "qué tengo hoy"
            (
                re.compile(
                    r"(?:eventos?|citas?|agenda|qu[eé]\s+(?:\w+\s+)?tengo|que\s+(?:\w+\s+)?tengo)\s+"
                    r"(?:de\s+|para\s+)?hoy",
                    re.IGNORECASE,
                ),
                "calendar", "get_today_events", lambda m: {},
            ),
            # "eventos de mañana"
            (
                re.compile(
                    r"(?:eventos?|citas?|agenda|qu[eé]\s+(?:\w+\s+)?tengo|que\s+(?:\w+\s+)?tengo)\s+"
                    r"(?:de\s+|para\s+)?ma[ñn]ana",
                    re.IGNORECASE,
                ),
                "calendar", "get_upcoming_events",
                lambda m: {"hours": 48},
            ),
            # "eventos de la semana"
            (
                re.compile(
                    r"(?:eventos?|citas?|agenda|qu[eé]\s+(?:\w+\s+)?tengo|que\s+(?:\w+\s+)?tengo)\s+"
                    r"(?:de\s+|para\s+)?(?:la\s+|esta\s+)?semana",
                    re.IGNORECASE,
                ),
                "calendar", "get_week_events", lambda m: {},
            ),
            # "elimina el evento X"
            (
                re.compile(
                    r"(?:elimina|eliminar|borra|borrar|cancela|cancelar)\s+"
                    r"(?:el\s+)?(?:evento|cita|reunión|reunion)\s+(.+)",
                    re.IGNORECASE,
                ),
                "calendar", "remove_event",
                lambda m: {"event_id": m.group(1).strip()},
            ),
        ])

        # ─── Plugins ─────────────────────────────────────────
        patterns.extend([
            # "lista plugins" / "qué plugins hay"
            (
                re.compile(
                    r"(?:lista|listar|muestra|mostrar|qu[eé]\s+|que\s+)"
                    r"(?:los\s+)?plugins?\s*(?:hay|tengo|cargados?|instalados?)?",
                    re.IGNORECASE,
                ),
                "orchestrator", "list_plugins", lambda m: {},
            ),
            # "recarga plugins"
            (
                re.compile(
                    r"(?:recarga|recargar|reload|actualiza|actualizar)\s+"
                    r"(?:los\s+)?plugins?",
                    re.IGNORECASE,
                ),
                "orchestrator", "reload_plugins", lambda m: {},
            ),
        ])

        # ─── Notificaciones ──────────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:activa|activar|enciende|encender|habilita|habilitar|enable)\s+"
                    r"(?:las\s+)?notificaciones?",
                    re.IGNORECASE,
                ),
                "orchestrator", "toggle_notifications",
                lambda m: {"enabled": True},
            ),
            (
                re.compile(
                    r"(?:desactiva|desactivar|apaga|apagar|deshabilita|deshabilitar|disable)\s+"
                    r"(?:las\s+)?notificaciones?",
                    re.IGNORECASE,
                ),
                "orchestrator", "toggle_notifications",
                lambda m: {"enabled": False},
            ),
        ])

        # ─── Escucha continua ─────────────────────────────────
        patterns.extend([
            (
                re.compile(
                    r"(?:activa|activar|enciende|encender|modo)\s+"
                    r"(?:la\s+)?(?:escucha\s+continua|modo\s+continuo|conversaci[oó]n\s+continua)",
                    re.IGNORECASE,
                ),
                "orchestrator", "toggle_continuous_listening",
                lambda m: {"enabled": True},
            ),
            (
                re.compile(
                    r"(?:desactiva|desactivar|apaga|apagar)\s+"
                    r"(?:la\s+)?(?:escucha\s+continua|modo\s+continuo|conversaci[oó]n\s+continua)",
                    re.IGNORECASE,
                ),
                "orchestrator", "toggle_continuous_listening",
                lambda m: {"enabled": False},
            ),
        ])

        # ─── Modo IA (local/cloud) ───────────────────────────
        patterns.extend([
            # "modo cloud", "cambia a modo cloud", "usa la nube"
            (
                re.compile(
                    r"(?:modo|cambia\s+a(?:\s+modo)?|usa(?:r)?|activa(?:r)?)\s+"
                    r"(?:cloud|nube|online|remoto|api)",
                    re.IGNORECASE,
                ),
                "orchestrator", "switch_brain_mode",
                lambda m: {"mode": "cloud"},
            ),
            # "modo local", "cambia a modo local", "usa ollama"
            (
                re.compile(
                    r"(?:modo|cambia\s+a(?:\s+modo)?|usa(?:r)?|activa(?:r)?)\s+"
                    r"(?:local|offline|ollama)",
                    re.IGNORECASE,
                ),
                "orchestrator", "switch_brain_mode",
                lambda m: {"mode": "local"},
            ),
            # "usa groq", "proveedor groq", "cambia a groq/gemini"
            (
                re.compile(
                    r"(?:usa(?:r)?|cambia\s+a|proveedor)\s+"
                    r"(groq|gemini)",
                    re.IGNORECASE,
                ),
                "orchestrator", "switch_cloud_provider",
                lambda m: {"provider": m.group(1).lower()},
            ),
            # "qué modo usas", "en qué modo estás"
            (
                re.compile(
                    r"(?:qu[eé]\s+modo|en\s+qu[eé]\s+modo|modo\s+actual|estado\s+(?:del\s+)?(?:modo|ia|cerebro))",
                    re.IGNORECASE,
                ),
                "orchestrator", "get_brain_mode_info",
                lambda m: {},
            ),
            # "configura api key groq/gemini XXXXX"
            (
                re.compile(
                    r"(?:configura(?:r)?|establece(?:r)?|pon(?:er)?|set)\s+"
                    r"(?:la\s+)?(?:api\s*key|clave|key)\s+"
                    r"(?:de\s+)?(groq|gemini)\s+(.+)",
                    re.IGNORECASE,
                ),
                "orchestrator", "set_cloud_api_key",
                lambda m: {"provider": m.group(1).lower(), "api_key": m.group(2).strip()},
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
            r"|mueve|mover|muevas|mueva|arrastra|arrastrar|lleva|llevar"
            r"|resuelve|resolver|soluciona|completa|contesta|responde"
            r"|enfoca|enfocar|cambia|minimiza|maximiza"
            r"|copia|copiar|lee|leer|describe"
            r"|pega|pegar|paste|mete|meter|inserta|insertar"
            r"|reproduce|reproducir|play|pausa|pausar|pause|para|parar"
            r"|siguiente|next|anterior|previous|prev|pasa|skip"
            r"|silencia|silenciar|mutea|mutear"
            r"|crea|crear|a[ñn]ade|a[ñn]adir|agenda|programa|programar"
            r"|recu[eé]rdame|recordar"
            r"|lista|listar|recarga|recargar|reload"
            r"|activa|activar|desactiva|desactivar"
            r"|analiza|analizar"
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
            r"^buenos\s+d[ií]as$", r"^buenas\s+tardes$", r"^buenas\s+noches$",
            r"^good\s+morning$", r"^good\s+afternoon$", r"^good\s+evening$",
            r"^qu[eé]\s+tal$", r"^c[oó]mo\s+est[aá]s$", r"^como\s+estas$",
            r"^como\s+andas$", r"^c[oó]mo\s+andas$",
            r"^como\s+va\s+(?:eso|todo)$", r"^c[oó]mo\s+va\s+(?:eso|todo)$",
            r"^hola\s+qu[eé]\s+tal$", r"^hola\s+como\s+est[aá]s$",
            r"^buenas$", r"^saludos$",
            r"^qu[eé]\s+hay$", r"^que\s+hay$",
            r"^hola\s+jarvis$",
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
