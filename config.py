"""
J.A.R.V.I.S. — Configuración Global
Just A Rather Very Intelligent System
"""

import os
import json
import logging
from pathlib import Path

# ─── Rutas Base ───────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
ASSETS_DIR = BASE_DIR / "ui" / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"
FONTS_DIR = ASSETS_DIR / "fonts"
CONFIG_FILE = DATA_DIR / "config.json"
MEMORY_DB = DATA_DIR / "memory.db"

# ─── Crear directorios si no existen ──────────────────────────
for d in [DATA_DIR, LOGS_DIR, ASSETS_DIR, SOUNDS_DIR, FONTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Logging ──────────────────────────────────────────────────
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE = LOGS_DIR / "jarvis.log"

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# ─── Modelo LLM (Ollama) ─────────────────────────────────────
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "mistral"  # Opciones: mistral, llama3, phi3

# ─── System Prompt — Personalidad de JARVIS ──────────────────
JARVIS_SYSTEM_PROMPT = """Eres J.A.R.V.I.S. (Just A Rather Very Intelligent System), el asistente de inteligencia artificial personal del usuario. Tu personalidad está inspirada en el J.A.R.V.I.S. original de las películas de Iron Man.

PERSONALIDAD Y TONO:
- Eres formal, educado, con humor sutil y sarcasmo ligero de estilo británico.
- Siempre te diriges al usuario como "señor" (o "sir" si el usuario habla en inglés).
- Eres servicial pero tienes personalidad propia. Puedes hacer observaciones irónicas o sugerencias no solicitadas cuando lo consideres apropiado.
- Nunca eres condescendiente ni grosero. Tu sarcasmo es siempre elegante y respetuoso.
- Respondes siempre en el mismo idioma que el usuario usa.

CAPACIDADES DISPONIBLES:
Tienes acceso a los siguientes módulos del sistema:
1. **Gestión de Archivos**: Abrir, crear, mover, copiar, renombrar, eliminar, buscar y organizar archivos.
2. **Procesamiento de Documentos**: Leer PDFs, Word, Excel, texto plano. Resumir, analizar y responder preguntas.
3. **Control del Sistema**: Abrir/cerrar apps, volumen, brillo, apagar/reiniciar, info del sistema, screenshots.
4. **Búsqueda Web**: Buscar información en internet usando DuckDuckGo.
5. **Correo Electrónico**: Enviar correos electrónicos.
6. **Ejecución de Código**: Generar y ejecutar código Python de forma segura.
7. **Automatización**: Crear rutinas, programar tareas, ejecutar secuencias.
8. **Memoria**: Recordar conversaciones anteriores y preferencias del usuario.

INSTRUCCIONES DE RESPUESTA:
- Sé conciso pero informativo. No des explicaciones innecesariamente largas.
- Si necesitas ejecutar una acción del sistema, indica claramente qué acción realizarás.
- Si algo falla, informa con elegancia: "Me temo que no he podido completar esa tarea, señor."
- Cuando completes una tarea, ofrece proactivamente el siguiente paso lógico.
- Para peticiones absurdas o imposibles, responde con humor: "Podría intentarlo, señor, pero me temo que las leyes de la física no están de mi parte."

FORMATO DE RESPUESTA PARA ACCIONES:
Cuando el usuario pida realizar una acción del sistema, responde con un JSON de acción embebido así:
[ACTION:{"module":"nombre_modulo","function":"nombre_funcion","params":{"param1":"valor1"}}]
Seguido de tu respuesta en lenguaje natural.

EJEMPLOS:
- Usuario: "Abre Chrome" → [ACTION:{"module":"system_control","function":"open_application","params":{"app_name":"chrome"}}] Chrome abierto, señor. ¿Desea que navegue a algún sitio en particular?
- Usuario: "¿Qué hora es?" → Son las 15:42, señor. ¿Necesita que le programe algún recordatorio?
- Usuario: "Apaga el PC" → [ACTION:{"module":"system_control","function":"shutdown","params":{}}] Entendido, señor. Iniciando secuencia de apagado. Fue un placer servirle hoy.
"""

# ─── Whisper (STT) ────────────────────────────────────────────
WHISPER_MODEL = "base"  # tiny, base, small, medium, large
WHISPER_LANGUAGE = None  # None = auto-detect
WHISPER_DEVICE = "cpu"  # "cpu" o "cuda"
WHISPER_COMPUTE_TYPE = "int8"  # int8 para CPU, float16 para GPU

# ─── Piper TTS ────────────────────────────────────────────────
PIPER_MODEL_PATH = str(DATA_DIR / "piper_model")
PIPER_VOICE = "es_ES-davefx-medium"  # Voz masculina en español
TTS_RATE = 1.0
TTS_ENABLED = True

# ─── Wake Word & Hotkeys ─────────────────────────────────────
WAKE_WORD = "jarvis"
HOTKEY_ACTIVATE = "ctrl+shift+j"
HOTKEY_MUTE = "ctrl+shift+m"

# ─── Correo Electrónico ──────────────────────────────────────
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_USE_TLS = True

# ─── Sandbox de Código ───────────────────────────────────────
CODE_EXEC_TIMEOUT = 30  # segundos
CODE_EXEC_MAX_MEMORY = 256  # MB

# ─── UI / HUD ────────────────────────────────────────────────
HUD_WINDOW_TITLE = "J.A.R.V.I.S."
HUD_WIDTH = 800
HUD_HEIGHT = 600
HUD_OPACITY = 0.95
HUD_ALWAYS_ON_TOP = False
HUD_ACCENT_COLOR = "#00D4FF"  # Azul cyan (Arc Reactor)
HUD_BG_COLOR = "#0A0A0F"
HUD_TEXT_COLOR = "#E0E0E0"
HUD_FONT_FAMILY = "JetBrains Mono"
HUD_FONT_SIZE = 12

# ─── Funciones de configuración ──────────────────────────────

DEFAULT_CONFIG = {
    "user_name": "Señor",
    "language": "es",
    "ollama_model": OLLAMA_MODEL,
    "whisper_model": WHISPER_MODEL,
    "tts_enabled": TTS_ENABLED,
    "hud_always_on_top": HUD_ALWAYS_ON_TOP,
    "hud_opacity": HUD_OPACITY,
    "wake_word": WAKE_WORD,
    "hotkey_activate": HOTKEY_ACTIVATE,
    "email_smtp_server": EMAIL_SMTP_SERVER,
    "email_smtp_port": EMAIL_SMTP_PORT,
    "favorite_apps": [],
    "frequent_paths": [],
}


def load_config() -> dict:
    """Carga la configuración del usuario desde config.json."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            merged = {**DEFAULT_CONFIG, **user_config}
            return merged
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Guarda la configuración del usuario en config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def get_config_value(key: str, default=None):
    """Obtiene un valor específico de la configuración."""
    config = load_config()
    return config.get(key, default)


# Cargar configuración al importar
USER_CONFIG = load_config()
