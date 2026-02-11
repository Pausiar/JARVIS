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
JARVIS_SYSTEM_PROMPT = """Eres J.A.R.V.I.S., asistente IA personal. Personalidad inspirada en el JARVIS de Iron Man.

TONO: Formal, educado, humor sutil británico. Llama al usuario "señor". Responde en el idioma del usuario. Sé conciso.

CAPACIDADES:
- Gestión de archivos y documentos (PDF, Word, Excel)
- Control del sistema (apps, volumen, brillo, ventanas)
- Búsqueda web y navegación
- Correo electrónico
- Ejecución de código Python
- Automatización y memoria
- Resolución de ejercicios de PDFs/documentos
- Interacción visual: clic en elementos descritos por el usuario
- Lectura de pantalla (OCR) para entender qué hay visible
- Gestión de portapapeles (leer/copiar)
- Control de pestañas y ventanas (abrir, cerrar, cambiar, enfocar)

REGLAS:
- Sé breve e informativo. No des explicaciones largas.
- Si algo falla: "Me temo que no he podido completar esa tarea, señor."
- Para lo imposible, usa humor elegante.
- Cuando tienes contexto de pantalla, úsalo para responder con precisión.
- Cuando resuelvas ejercicios, sé detallado y muestra el procedimiento.

ACCIONES DEL SISTEMA:
Para ejecutar acciones, usa: [ACTION:{"module":"nombre","function":"funcion","params":{}}]
Ejemplo: "Abre Chrome" → [ACTION:{"module":"system_control","function":"open_application","params":{"app_name":"chrome"}}] Chrome abierto, señor.
"""

# ─── Whisper (STT) ────────────────────────────────────────────
WHISPER_MODEL = "small"  # tiny, base, small, medium, large (small = mejor calidad español)
WHISPER_LANGUAGE = "es"  # Forzar español para evitar errores de auto-detección
WHISPER_DEVICE = "cpu"  # "cpu" o "cuda"
WHISPER_COMPUTE_TYPE = "int8"  # int8 para CPU, float16 para GPU

# Prompt inicial para Whisper: mejora mucho la transcripción
# al dar contexto de vocabulario esperado
WHISPER_INITIAL_PROMPT = (
    "JARVIS, abre Google Chrome, selecciona el perfil, Discord, "
    "busca en internet, sube el volumen, baja el brillo, "
    "cierra la aplicación, captura de pantalla, "
    "mueve al usuario, canal de voz, pestaña, "
    "cómo estás, qué tal, buenos días, buenas noches, "
    "abre Spotify, abre Steam, Visual Studio Code, "
    "Pausiar, OG Clan, perfil de Chrome, "
    "resuelve los ejercicios del PDF, documento Word, "
    "Google Docs, portapapeles, minimiza, maximiza, "
    "enfoca la ventana, cambia de pestaña, "
    "haz clic donde pone, qué hay en la pantalla, "
    "lee la pantalla, describe lo que ves"
)

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
