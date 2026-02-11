# 🤖 J.A.R.V.I.S.

> **Just A Rather Very Intelligent System**

Asistente de escritorio con IA para Windows 10/11, inspirado en el J.A.R.V.I.S. de Iron Man.  
100% local, sin APIs de pago, con interacción por voz y texto.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20+%20Mistral-green)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ ¿Qué hace?

| Módulo | Descripción |
|--------|-------------|
| 🧠 **Cerebro IA** | Conversación natural con Ollama (Mistral), 100% local |
| 🎙️ **Voz** | Entrada por voz (Whisper) + Salida TTS (pyttsx3) |
| ⚙️ **Sistema** | Abre apps usando la búsqueda de Windows (como lo harías tú) |
| 🌐 **Web** | "Busca X" abre una pestaña real de Google en tu navegador |
| 📁 **Archivos** | Abrir, crear, mover, copiar, buscar, organizar archivos |
| 📄 **Documentos** | Leer PDF, Word, Excel, CSV, JSON, TXT |
| 📧 **Email** | Envío de correos con SMTP |
| 💻 **Código** | Ejecutar Python en sandbox seguro |
| ⏰ **Automatización** | Timers, recordatorios, tareas programadas |
| 🧠 **Memoria** | Recuerda conversaciones y preferencias (SQLite) |

---

## 📋 Requisitos previos

Antes de instalar JARVIS necesitas tener instalado:

### 1. Python 3.11 o superior

Descárgalo de [python.org](https://www.python.org/downloads/).  
**Importante**: Marca la casilla **"Add Python to PATH"** durante la instalación.

Verifica que está instalado:
```powershell
python --version
# Debe mostrar Python 3.11.x o superior
```

### 2. Ollama (motor de IA local)

Descárgalo de [ollama.com](https://ollama.com/download) e instálalo normalmente.

Verifica que está instalado:
```powershell
ollama --version
```

### 3. Git (para clonar el repositorio)

Descárgalo de [git-scm.com](https://git-scm.com/download/win) si no lo tienes.

---

## 🚀 Instalación paso a paso

Abre una terminal (PowerShell o CMD) y ejecuta estos comandos uno por uno:

### Paso 1 — Clonar el repositorio

```powershell
git clone https://github.com/Pausiar/JARVIS.git
cd JARVIS
```

### Paso 2 — Crear entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> Si usas CMD en vez de PowerShell: `.\.venv\Scripts\activate.bat`

### Paso 3 — Instalar dependencias de Python

```powershell
pip install -r requirements.txt
```

Si alguna dependencia falla, instala las esenciales manualmente:
```powershell
pip install PySide6 requests psutil pyttsx3 keyboard pynput pyautogui faster-whisper numpy sounddevice pycaw comtypes
```

### Paso 4 — Descargar el modelo de IA

Asegúrate de que Ollama esté corriendo (se inicia automáticamente con Windows, pero si no):
```powershell
ollama serve
```

En otra terminal, descarga el modelo Mistral (~4.4 GB):
```powershell
ollama pull mistral
```

### Paso 5 — Ejecutar JARVIS

```powershell
cd JARVIS
.\.venv\Scripts\Activate.ps1
python main.py
```

Si todo está bien, verás en la terminal:
```
  J.A.R.V.I.S. — Inicializando...
  LLM (Ollama): ✅ Conectado
  STT (Whisper): ✅ Listo
  TTS: ✅ Listo
  Orquestador: ✅ Listo
  JARVIS inicializado correctamente.
  JARVIS está listo. Esperando instrucciones...
```

Y se abrirá la ventana HUD con el tema Arc Reactor (cian).

---

## 🎮 Cómo usar JARVIS

### Interfaz gráfica (HUD)

- **Escribir**: Usa la barra de texto en la parte inferior de la ventana
- **Hablar**: Pulsa el botón del micrófono 🎙️
- **Atajo global**: `Ctrl+Shift+J` para mostrar/ocultar la ventana desde cualquier sitio

### Ejemplos de comandos

| Dices / Escribes | Qué hace JARVIS |
|---|---|
| `Abre Chrome` | Abre Google Chrome usando la búsqueda de Windows |
| `Abre IntelliJ` | Busca IntelliJ IDEA en Windows y lo abre |
| `Busca recetas de pasta` | Abre una pestaña de Google con la búsqueda |
| `Abre Chrome y busca hola` | Abre Chrome Y luego busca "hola" en Google |
| `¿Qué hora es?` | Te dice la hora actual |
| `¿Qué día es?` | Te dice la fecha actual |
| `Sube el volumen` | Sube el volumen 10% |
| `Pon el volumen al 50` | Establece el volumen al 50% |
| `Haz una captura de pantalla` | Captura la pantalla y la guarda |
| `Cierra Chrome` | Cierra Google Chrome |
| `Apaga el PC` | Apaga el sistema (con 5s de delay) |

Para cualquier cosa que no sea un comando directo, JARVIS usa el LLM (Mistral) para entender tu petición y responderte de forma conversacional.

---

## 🏗️ Estructura del proyecto

```
JARVIS/
├── main.py                   # Punto de entrada — ejecutar con: python main.py
├── config.py                 # Configuración global (modelo, hotkeys, TTS, etc.)
├── requirements.txt          # Lista de dependencias Python
├── setup.py                  # Script de instalación alternativo
│
├── core/                     # Núcleo del sistema
│   ├── brain.py              # Conexión con Ollama (LLM local)
│   ├── voice_input.py        # Reconocimiento de voz (faster-whisper)
│   ├── voice_output.py       # Síntesis de voz (pyttsx3)
│   ├── command_parser.py     # Detecta intenciones por regex
│   └── orchestrator.py       # Orquestador central (conecta todo)
│
├── modules/                  # Módulos funcionales
│   ├── system_control.py     # Abrir/cerrar apps, volumen, brillo, etc.
│   ├── web_search.py         # Búsquedas en Google (abre pestaña real)
│   ├── file_manager.py       # Gestión de archivos
│   ├── document_processor.py # Lectura de PDF, Word, Excel
│   ├── email_manager.py      # Envío de email SMTP
│   ├── code_executor.py      # Ejecutar código Python
│   ├── automation.py         # Timers, recordatorios, rutinas
│   └── memory.py             # Memoria persistente (SQLite)
│
├── ui/                       # Interfaz gráfica
│   ├── hud.py                # Ventana HUD principal
│   ├── styles.py             # Estilos QSS (tema cyan Arc Reactor)
│   └── widgets.py            # Widgets personalizados
│
└── data/                     # Datos (se genera automáticamente)
    ├── memory.db             # Base de datos de conversaciones
    └── logs/                 # Logs del sistema
```

---

## ⚙️ Configuración

El archivo `config.py` contiene toda la configuración. Lo más relevante:

| Parámetro | Valor por defecto | Descripción |
|---|---|---|
| `OLLAMA_MODEL` | `mistral` | Modelo de IA (puede ser `llama3`, `phi3`, etc.) |
| `WHISPER_MODEL` | `base` | Modelo de voz (`tiny`, `base`, `small`, `medium`) |
| `HOTKEY_ACTIVATE` | `ctrl+shift+j` | Atajo para activar JARVIS |
| `TTS_ENABLED` | `True` | Activar/desactivar voz de JARVIS |
| `TTS_RATE` | `1.0` | Velocidad de habla |
| `HUD_OPACITY` | `0.95` | Transparencia de la ventana |

También puedes editar `data/config.json` para cambiar preferencias de usuario.

---

## 🔧 Dependencias principales

| Paquete | Para qué se usa |
|---|---|
| `PySide6` | Interfaz gráfica (ventana HUD) |
| `requests` | Comunicación con Ollama API local |
| `faster-whisper` | Reconocimiento de voz (Speech-to-Text) |
| `pyttsx3` | Síntesis de voz (Text-to-Speech) |
| `pyautogui` | Simulación de teclado (abrir apps con Windows Search) |
| `keyboard` | Hotkeys globales (Ctrl+Shift+J) |
| `psutil` | Info del sistema (CPU, RAM, disco) |
| `pycaw` + `comtypes` | Control de volumen de Windows |
| `sounddevice` + `numpy` | Captura de audio del micrófono |
| `PyMuPDF` | Lectura de PDFs |
| `python-docx` | Lectura/escritura de Word |
| `openpyxl` | Lectura/escritura de Excel |
| `Pillow` | Capturas de pantalla |

La lista completa está en `requirements.txt`.

---

## ❓ Solución de problemas

### "Ollama no disponible" / LLM ❌

1. Asegúrate de que Ollama está corriendo: `ollama serve`
2. Verifica que el modelo está descargado: `ollama list`
3. Si no aparece "mistral", descárgalo: `ollama pull mistral`

### JARVIS no abre aplicaciones

- JARVIS usa la **búsqueda de Windows** (simula Win + escribir + Enter)
- La app debe estar instalada y aparecer en la búsqueda de Windows
- Si una app no se abre, prueba a buscarla manualmente con la tecla Windows

### "busca X" no abre nada en el navegador

- JARVIS usa `webbrowser.open()` para abrir Google
- Si no funciona, verifica que tienes un navegador predeterminado configurado en Windows

### Error con pyttsx3 / No habla

```powershell
pip install pyttsx3
```

### Error con el micrófono / No escucha

```powershell
pip install faster-whisper sounddevice numpy
```
- Asegúrate de que tu micrófono está configurado como dispositivo predeterminado en Windows

### Error "keyboard requires root"

- Ejecuta la terminal como **Administrador** (clic derecho → "Ejecutar como administrador")

---

## 📋 Requisitos del sistema

| | Mínimo | Recomendado |
|---|---|---|
| **OS** | Windows 10 | Windows 11 |
| **RAM** | 8 GB | 16 GB |
| **Disco** | ~5 GB | ~10 GB |
| **CPU** | x64 moderno | i5/Ryzen 5 o superior |
| **GPU** | No necesaria | NVIDIA (CUDA) para acelerar IA |

---

## 📄 Licencia

MIT License — ver [LICENSE](LICENSE) para más detalles.

---

<p align="center">
  <em>"Es un placer asistirle, señor."</em> — J.A.R.V.I.S.
</p>
