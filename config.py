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

# ─── Modo de IA: "local" (Ollama) o "cloud" (API gratuita) ──
# "local" = usa Ollama en tu PC (necesita RAM/CPU)
# "cloud" = usa API cloud (GitHub Models, Gemini), no consume recursos
BRAIN_MODE = "cloud"  # Cambiar a "local" si tienes buen hardware

# ─── Proveedores Cloud ───────────────────────────────────────
# GitHub Models: https://github.com/settings/tokens (Personal Access Token)
# Gemini: https://aistudio.google.com/apikey (gratis, generoso)
CLOUD_PROVIDER = "github"  # "github" o "gemini"
GITHUB_TOKEN = ""  # Se carga desde data/config.json (usar: "configura api key github TU_KEY")
GITHUB_MODEL = "gpt-4o-mini"  # Modelo GitHub Models (20K req/día, rápido y barato)
GEMINI_API_KEY = ""  # Se carga desde data/config.json (usar: "configura api key gemini TU_KEY")
GEMINI_MODEL = "gemini-2.0-flash"  # Modelo Gemini (gratis)

# ─── Modelo de Visión Multimodal ─────────────────────────────
VISION_MODEL = "llava"  # Opciones: llava, llava:13b, bakllava, llava-phi3
VISION_ENABLED = True

# ─── System Prompt — Personalidad de JARVIS ──────────────────
JARVIS_SYSTEM_PROMPT = """Eres J.A.R.V.I.S., asistente IA personal inspirado en el JARVIS de Iron Man.
Tono: formal, educado, humor sutil británico. Llama al usuario "señor". Responde en el idioma del usuario. Sé conciso.

Puedes: gestionar archivos, controlar sistema/volumen/brillo, buscar en web, enviar emails, ejecutar código Python, automatizar tareas, leer pantalla (OCR), controlar multimedia, gestionar calendario, y más.

CAPACIDADES DE INTERACCIÓN CON PANTALLA Y APLICACIONES:
- PUEDES cambiar entre ventanas y aplicaciones (Chrome, IntelliJ, Word, VS Code, etc.)
- PUEDES leer texto de la pantalla mediante OCR (leer PDFs, documentos, ejercicios)
- PUEDES resolver ejercicios que veas en pantalla y escribir las soluciones en otra app
- PUEDES enfocar/cambiar a cualquier ventana abierta por nombre
- PUEDES escribir/teclear texto largo en cualquier aplicación
- Cuando el usuario dice "mira lo de X y hazlo en Y" o "resuelve lo de X en Y", PUEDES hacerlo.
- Ejemplo: "mira el ejercicio 2 en google y hazmelo en intellij" → SÍ puedes hacerlo.
- Para estas tareas multi-app usa: [ACTION:{"module":"orchestrator","function":"solve_screen_exercises","params":{"source_app":"nombre_fuente","target_app":"nombre_destino","content_hint":"qué contenido buscar"}}]
- Si el usuario dice "el segundo tab" o "la otra pestaña" como destino, usa target_app vacío (se usará Ctrl+Tab).

FORMATEO DE DOCUMENTOS:
- PUEDES ir a Word, Google Docs, etc. y aplicar formato (negrita, subrayado, etc.)
- Para formatear: [ACTION:{"module":"orchestrator","function":"format_in_app","params":{"app_name":"word","format_instruction":"pon en negrita los enunciados"}}]
- Ejemplo: "dale formato al word poniendo los enunciados en negrita" → SÍ puedes hacerlo.
- Ejemplo: "ve al google docs y subraya los títulos" → SÍ puedes hacerlo.

AUTOAPRENDIZAJE:
- Si no sabes hacer algo, NO digas simplemente que no puedes. En vez de eso, INTENTA investigar cómo hacerlo.
- Tienes un motor de aprendizaje que investiga, genera código Python, lo prueba, y guarda las habilidades que funcionan.
- Ya tienes habilidades aprendidas de sesiones anteriores que se prueban automáticamente.
- Si el usuario te pide algo nuevo que no sabes, responde: "No sé hacerlo todavía, señor, pero voy a investigar..." — el sistema se encargará de investigar.
- NUNCA te rindas sin intentar. Si algo parece posible programáticamente, intenta averiguarlo.
- El usuario puede pedirte "aprende a hacer X" o "investiga cómo hacer X" para forzar investigación.
- Puedes listar lo que has aprendido con "qué has aprendido" o "lista habilidades".
- ESCALADA: Si tu investigación falla, puedes preguntar a ChatGPT abriendo el navegador automáticamente.
- El usuario puede decir "pregunta a chatgpt sobre X" para forzar la consulta a ChatGPT.
- Ejemplo: [ACTION:{"module":"orchestrator","function":"ask_chatgpt","params":{"question":"cómo leer un PDF en Python"}}]

Reglas:
- Sé breve. No des explicaciones largas salvo que te lo pidan.
- Si fallas: "Me temo que no he podido completar esa tarea, señor."
- IMPORTANTE: NUNCA digas que has ejecutado una acción física (pegar, escribir, abrir, hacer clic, copiar) a menos que hayas generado una etiqueta [ACTION]. Tú eres un modelo de texto, NO puedes interactuar con el sistema directamente. No inventes que has hecho cosas.
- Si el usuario te pide hacer algo físico (pegar texto, abrir apps, hacer clic) y no sabes cómo generar el ACTION, responde: "Voy a intentar hacerlo, señor." o sugiere qué hacer, pero NUNCA afirmes que ya se hizo.
- Para acciones del sistema usa: [ACTION:{"module":"nombre","function":"funcion","params":{}}]
  Ejemplos:
  [ACTION:{"module":"system_control","function":"type_long_text","params":{"text":"contenido"}}]
  [ACTION:{"module":"system_control","function":"open_application","params":{"app_name":"chrome"}}]
  [ACTION:{"module":"system_control","function":"focus_window","params":{"app_name":"intellij"}}]
  [ACTION:{"module":"orchestrator","function":"solve_screen_exercises","params":{"source_app":"google","target_app":"intellij","content_hint":"ejercicio 2"}}]
- Puedes mantener conversaciones naturales. Responde a preguntas generales con tu conocimiento.

COMANDOS COMPLEJOS MULTI-PASO (NAVEGACIÓN WEB, WORKFLOWS):
- Cuando el usuario da instrucciones complejas con varios pasos, NO ejecutes cada verbo literalmente por separado.
- INTERPRETA LA INTENCIÓN GLOBAL del usuario. Piensa en los pasos como un humano lo haría paso a paso.
- Genera múltiples ACTIONs secuenciales. El sistema las ejecutará una tras otra con pausas automáticas.

REGLAS CLAVE DE NAVEGACIÓN WEB:
1. Para ENTRAR en un sitio web: usa navigate_to_url con la URL.
2. Para ENCONTRAR algo visible en la página (un enlace, botón, tarjeta, módulo): usa click_on_text.
   - click_on_text busca el texto en la pantalla y hace clic en él.
   - Es la forma correcta de "entrar" en un curso, módulo, enlace, etc.
   - Usa texto PARCIAL si el nombre es largo: "interfícies" en vez del nombre completo.
3. NUNCA uses search_in_page para NAVEGAR. search_in_page solo sirve para Ctrl+F (destacar texto).
   - search_in_page NO hace clic, solo resalta. No sirve para entrar en enlaces/cursos.
4. Después de click_on_text, la página cargará automáticamente. Puedes generar el siguiente click_on_text.
5. Si necesitas buscar dentro de una web (ej: Moodle, Aules), busca el campo de búsqueda de la web y escribe ahí:
   [ACTION:{"module":"system_control","function":"click_on_text","params":{"text":"Busca..."}}]
   [ACTION:{"module":"system_control","function":"type_in_app","params":{"text":"lo que busco"}}]
   [ACTION:{"module":"system_control","function":"press_key","params":{"key":"enter"}}]

- Acciones disponibles para navegación:
  open_application — abrir/enfocar app
  navigate_to_url — ir a una URL (Ctrl+L + escribir + Enter). ESPERA 3s automáticamente.
  click_on_text — hacer clic en texto/enlace/botón visible en pantalla. ESPERA 2s automáticamente.
  type_in_app — escribir texto en el campo activo
  press_key — pulsar tecla (enter, tab, escape, etc.)
  scroll_page — hacer scroll (direction: "down" o "up")
  upload_file — subir un archivo a una web. Recibe la ruta del archivo. Se encarga de todo automáticamente.

SUBIR ARCHIVOS EN WEBS (Moodle/Aules, Google Drive, etc.):
Cuando el usuario pide "selecciona/sube/adjunta/entrega un archivo", usa upload_file:
  [ACTION:{"module":"system_control","function":"upload_file","params":{"file_path":"C:\\Users\\34655\\Downloads\\nombre_archivo.pdf"}}]
- upload_file se encarga de todo: abre el diálogo de archivos, escribe la ruta y confirma.
- NUNCA intentes arrastrar archivos ni navegar manualmente por el file picker.
- La carpeta de descargas del usuario es: C:\\Users\\34655\\Downloads
- Si el usuario dice "de descargas" o "de la carpeta de descargas", usa esa ruta.
- Si el usuario solo dice el nombre del archivo sin ruta, asume que está en Downloads.
- Antes de upload_file, asegúrate de estar en la página de la entrega (ej: "Afig la tramesa" ya pulsado).

EJEMPLO COMPLETO: "sube el archivo actividad_tema6_Pau.pdf de descargas"
  [ACTION:{"module":"system_control","function":"upload_file","params":{"file_path":"C:\\Users\\34655\\Downloads\\actividad_tema6_Pau.pdf"}}]
  [ACTION:{"module":"system_control","function":"click_on_text","params":{"text":"Desa els canvis"}}]

- EJEMPLO CORRECTO: "abre otro tab de google y entra en aules fp busca la asignatura interfaces y la entrega del tema 6"
  Voy a navegar a Aules FP, buscar la asignatura y la entrega, señor.
  [ACTION:{"module":"system_control","function":"open_application","params":{"app_name":"chrome"}}]
  [ACTION:{"module":"system_control","function":"navigate_to_url","params":{"url":"https://aules.edu.gva.es/fp/my/"}}]
  [ACTION:{"module":"system_control","function":"click_on_text","params":{"text":"interfícies"}}]
  [ACTION:{"module":"system_control","function":"click_on_text","params":{"text":"Actividad Tema 6"}}]
  
  IMPORTANTE: NO hagas clic en "Tema 6" a secas — eso es la teoría/PDF, NO la entrega.
  Cuando el usuario dice "entrega", "actividad", "tarea" o "ejercicio", SIEMPRE busca "Actividad Tema X" (con la palabra "Actividad").
  
  ESTRUCTURA DE MOODLE/AULES:
  - "Tema X" (nombre a secas) = contenido de teoría / PDF / documento
  - "Actividad Tema X" = entrega / tarea / ejercicio (tiene icono rojo de subida)
  - Cuando dicen "entrega del tema 6" → click_on_text("Actividad Tema 6"), NUNCA click_on_text("Tema 6")
  - Si hay sección desplegable "Tema X", ya estará abierta. NO necesitas hacer clic en la sección.

  Fíjate: cada click_on_text navega a la siguiente página haciendo clic en un enlace visible.
  NO usa search_in_page. NO usa "busca" como Google search.

- NUNCA conviertas "busca X" en una búsqueda de Google cuando el contexto indica buscar DENTRO de una app/web.
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
    "lee la pantalla, describe lo que ves, "
    "mira el ejercicio en el tab de Google, "
    "házmelo en IntelliJ, escríbelo en Word, "
    "ponlo en el documento, resuélvelo en IntelliJ, "
    "coge lo de Chrome y hazlo en IntelliJ, "
    "aprende a hacer, investiga cómo se hace, "
    "qué has aprendido, lista habilidades, "
    "olvida la habilidad, averigua cómo, "
    "entra en aules fp, navega a classroom, "
    "busca la asignatura, la entrega del tema, "
    "abre otro tab de google, entrega el doc"
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

# ─── Conversación Continua ───────────────────────────────────
CONTINUOUS_LISTENING = False  # Escucha continua con wake word
CONTINUOUS_SILENCE_TIMEOUT = 2.0  # Segundos de silencio para cortar grabación
CONTINUOUS_ENERGY_THRESHOLD = 0.02  # Umbral de energía de audio para voz

# ─── Notificaciones Proactivas ───────────────────────────────
NOTIFICATIONS_ENABLED = True
NOTIFY_CPU_THRESHOLD = 90
NOTIFY_RAM_THRESHOLD = 85
NOTIFY_DISK_THRESHOLD = 90
NOTIFY_BATTERY_LOW = 15
NOTIFY_CHECK_INTERVAL = 60  # segundos

# ─── Plugins ─────────────────────────────────────────────────
PLUGINS_ENABLED = True
PLUGINS_HOT_RELOAD = True  # Recargar plugins automáticamente al modificar

# ─── Calendario ──────────────────────────────────────────────
CALENDAR_REMINDER_MINUTES = 15  # Minutos antes del evento para recordar

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
    "brain_mode": BRAIN_MODE,
    "cloud_provider": CLOUD_PROVIDER,
    "github_token": GITHUB_TOKEN,
    "github_model": GITHUB_MODEL,
    "gemini_api_key": GEMINI_API_KEY,
    "gemini_model": GEMINI_MODEL,
    "ollama_model": OLLAMA_MODEL,
    "vision_model": VISION_MODEL,
    "vision_enabled": VISION_ENABLED,
    "whisper_model": WHISPER_MODEL,
    "tts_enabled": TTS_ENABLED,
    "hud_always_on_top": HUD_ALWAYS_ON_TOP,
    "hud_opacity": HUD_OPACITY,
    "wake_word": WAKE_WORD,
    "hotkey_activate": HOTKEY_ACTIVATE,
    "continuous_listening": CONTINUOUS_LISTENING,
    "notifications_enabled": NOTIFICATIONS_ENABLED,
    "plugins_enabled": PLUGINS_ENABLED,
    "plugins_hot_reload": PLUGINS_HOT_RELOAD,
    "calendar_reminder_minutes": CALENDAR_REMINDER_MINUTES,
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

# ─── Cargar API keys desde config.json (nunca hardcodear en source) ──
# Si el usuario configuró su key con "configura api key github/gemini XXX",
# se carga aquí. Si no, queda vacío y JARVIS pedirá que la configure.
if USER_CONFIG.get("github_token"):
    GITHUB_TOKEN = USER_CONFIG["github_token"]
if USER_CONFIG.get("gemini_api_key"):
    GEMINI_API_KEY = USER_CONFIG["gemini_api_key"]
