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
| 🎙️ **Voz** | Entrada por voz (faster-whisper) + Salida TTS (Piper, voz natural en español) |
| 👁️ **Visión OCR** | Lee la pantalla con Windows.Media.Ocr nativo — clic inteligente por descripción |
| ⚙️ **Sistema** | Abre/cierra apps, volumen, brillo, ventanas, pestañas |
| 🌐 **Web** | "Busca X" abre una pestaña real de Google en tu navegador |
| 📁 **Archivos** | Abrir, crear, mover, copiar, buscar, organizar archivos |
| 📄 **Documentos** | Leer PDF, Word, Excel, CSV, JSON, TXT |
| 📝 **Resolver ejercicios** | Lee un PDF con ejercicios, los resuelve y escribe las soluciones en Word/Google Docs |
| 📧 **Email** | Envío de correos con SMTP |
| 💻 **Código** | Ejecutar Python en sandbox seguro |
| ⏰ **Automatización** | Timers, recordatorios, tareas programadas |
| 🧠 **Memoria** | Recuerda conversaciones y preferencias (SQLite) |
| 📋 **Portapapeles** | Leer y escribir en el portapapeles de Windows |
| 🪟 **Gestión de ventanas** | Enfocar, minimizar, maximizar, snap (ajustar a lados) |

---

## 📋 Requisitos previos

### 1. Python 3.11 o superior

Descárgalo de [python.org](https://www.python.org/downloads/).  
**Importante**: Marca la casilla **"Add Python to PATH"** durante la instalación.

```powershell
python --version
# Debe mostrar Python 3.11.x o superior
```

### 2. Ollama (motor de IA local)

Descárgalo de [ollama.com](https://ollama.com/download) e instálalo normalmente.

```powershell
ollama --version
```

### 3. Git

Descárgalo de [git-scm.com](https://git-scm.com/download/win) si no lo tienes.

---

## 🚀 Instalación paso a paso

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

> Si usas CMD: `.\.venv\Scripts\activate.bat`

### Paso 3 — Instalar dependencias

```powershell
pip install -r requirements.txt
```

Si alguna dependencia falla, instala las esenciales:
```powershell
pip install PySide6 requests psutil keyboard pynput pyautogui faster-whisper numpy sounddevice pycaw comtypes PyMuPDF python-docx openpyxl Pillow piper-tts
```

### Paso 4 — Descargar el modelo de IA

```powershell
ollama serve          # En una terminal (si no está corriendo ya)
ollama pull mistral   # En otra terminal (~4.4 GB)
```

### Paso 5 — Ejecutar JARVIS

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

Se abrirá la ventana HUD con el tema Arc Reactor (cian).

---

## 🎮 Cómo usar JARVIS

### Interfaz gráfica (HUD)

- **Escribir**: Barra de texto en la parte inferior
- **Hablar**: Botón del micrófono 🎙️
- **Atajo global**: `Ctrl+Shift+J` para mostrar/ocultar desde cualquier sitio

### Catálogo de comandos

#### 🖥️ Control del sistema
| Comando | Qué hace |
|---|---|
| `Abre Chrome` | Abre Google Chrome con la búsqueda de Windows |
| `Cierra Discord` | Cierra Discord |
| `Sube el volumen` | +10% de volumen |
| `Pon el volumen al 50` | Volumen al 50% |
| `Silencia` | Mute/unmute |
| `Sube el brillo` | +10% de brillo |
| `Captura de pantalla` | Screenshot al escritorio |
| `¿Qué hora es?` / `¿Qué día es?` | Hora y fecha actual |
| `Info del sistema` | CPU, RAM, disco, batería |
| `Apaga el PC` / `Reinicia` | Apagar/reiniciar |

#### 👁️ Interacción visual (OCR)
| Comando | Qué hace |
|---|---|
| `Haz clic donde pone Configuración` | Busca el texto en pantalla por OCR y hace clic |
| `Pulsa en el botón de enviar` | Clic inteligente por descripción con LLM |
| `Entra en el primer resultado` | Clic en el primer resultado de Google |
| `¿Qué hay en la pantalla?` | Lee todo el texto visible con OCR |
| `Lee la pantalla` | Igual que arriba |

#### 🪟 Ventanas y pestañas
| Comando | Qué hace |
|---|---|
| `Enfoca la ventana de Discord` | Trae Discord al primer plano |
| `Cambia a Chrome` | Foco a Chrome |
| `Nueva pestaña` | Ctrl+T |
| `Cierra la pestaña` | Ctrl+W |
| `Cambia de pestaña` | Ctrl+Tab |
| `Minimiza la ventana` | Minimiza la ventana activa |
| `Maximiza` | Maximiza la ventana activa |
| `Ajusta la ventana a la izquierda` | Snap left |

#### 📝 Documentos y ejercicios
| Comando | Qué hace |
|---|---|
| `Lee el PDF C:/docs/resumen.pdf` | Lee y devuelve el contenido |
| `Resume el documento C:/docs/trabajo.docx` | Resumen con IA |
| `Resuelve los ejercicios del PDF C:/docs/mates.pdf` | Resuelve con IA y muestra las soluciones |
| `Haz los ejercicios del PDF examen.pdf en Word` | Resuelve y escribe automáticamente en Word |
| `Contesta las preguntas del PDF test.pdf en Google Docs` | Resuelve y escribe en Google Docs |

#### 🔊 Discord
| Comando | Qué hace |
|---|---|
| `Mueve al usuario "Pausiar" al canal de voz "sala"` | Drag & drop por OCR |

#### 📋 Portapapeles
| Comando | Qué hace |
|---|---|
| `Lee el portapapeles` | Muestra el contenido actual |
| `Copia al portapapeles hola mundo` | Copia texto |

#### 🌐 Búsqueda web
| Comando | Qué hace |
|---|---|
| `Busca recetas de pasta` | Abre Google con la búsqueda |
| `Busca noticias sobre IA` | Abre Google News |

#### 🎙️ Conversación
Cualquier cosa que no sea un comando directo se envía al LLM (Mistral) para respuesta conversacional en español.

---

## 🏗️ Estructura del proyecto

```
JARVIS/
├── main.py                   # Punto de entrada
├── config.py                 # Configuración global
├── requirements.txt          # Dependencias Python
├── setup.py                  # Script de instalación alternativo
│
├── core/                     # Núcleo del sistema
│   ├── brain.py              # Conexión con Ollama (LLM local)
│   ├── voice_input.py        # Reconocimiento de voz (faster-whisper)
│   ├── voice_output.py       # Síntesis de voz (Piper TTS)
│   ├── command_parser.py     # Detección de intenciones por regex
│   └── orchestrator.py       # Orquestador central + workflows multi-paso
│
├── modules/                  # Módulos funcionales
│   ├── system_control.py     # Apps, volumen, brillo, OCR, ventanas, pestañas, portapapeles
│   ├── web_search.py         # Búsquedas en Google (pestaña real)
│   ├── file_manager.py       # Gestión de archivos
│   ├── document_processor.py # PDF, Word, Excel, CSV, JSON
│   ├── email_manager.py      # Envío de email SMTP
│   ├── code_executor.py      # Ejecutar código Python
│   ├── automation.py         # Timers, recordatorios, rutinas
│   └── memory.py             # Memoria persistente (SQLite)
│
├── ui/                       # Interfaz gráfica
│   ├── hud.py                # Ventana HUD principal (PySide6)
│   ├── styles.py             # Estilos QSS (tema cyan Arc Reactor)
│   └── widgets.py            # Widgets personalizados
│
├── tests/                    # Tests unitarios
│   ├── test_brain.py
│   ├── test_modules.py
│   └── test_voice.py
│
└── data/                     # Datos (se genera automáticamente)
    ├── memory.db             # Base de datos conversaciones
    └── logs/                 # Logs del sistema
```

---

## ⚙️ Configuración

Archivo `config.py`:

| Parámetro | Valor | Descripción |
|---|---|---|
| `OLLAMA_MODEL` | `mistral` | Modelo de IA (`llama3`, `phi3`, etc.) |
| `WHISPER_MODEL` | `small` | Modelo de voz (`tiny`, `base`, `small`, `medium`) |
| `WHISPER_LANGUAGE` | `es` | Idioma forzado para transcripción |
| `HOTKEY_ACTIVATE` | `ctrl+shift+j` | Atajo para activar JARVIS |
| `TTS_ENABLED` | `True` | Activar/desactivar voz |
| `PIPER_VOICE` | `es_ES-davefx-medium` | Voz TTS en español |
| `HUD_OPACITY` | `0.95` | Transparencia de la ventana |

También puedes editar `data/config.json` para preferencias de usuario.

---

## 🔧 Tecnologías

| Componente | Tecnología |
|---|---|
| LLM | Ollama + Mistral (100% local) |
| STT | faster-whisper (modelo `small`, español forzado) |
| TTS | Piper TTS (`es_ES-davefx-medium`) |
| OCR | Windows.Media.Ocr nativo (Win10/11, es-ES) |
| GUI | PySide6 (Qt for Python) |
| Automatización | pyautogui + Win32 API via PowerShell |
| UI Automation | System.Windows.Automation via PowerShell |
| Base de datos | SQLite3 (stdlib) |

---

## 🚀 Roadmap — Ideas para futuras mejoras

### 🔴 Prioridad alta

- [x] **Modelo de visión (multimodal)** — LLaVA integrado via Ollama. JARVIS puede analizar screenshots, describir la pantalla, buscar elementos visuales y leer texto de imágenes locales.
- [x] **Modo conversación continua** — Escucha activa sin necesidad de pulsar el botón del micrófono cada vez. Wake word "JARVIS" para activar, detección de silencio automática.
- [x] **Programación de tareas / Calendario** — Calendario local con SQLite, recordatorios automáticos. Comandos tipo *"recuérdame en 30 minutos"*, *"crea evento reunión mañana a las 15"*, *"eventos de hoy"*.

### 🟡 Prioridad media

- [x] **Sistema de plugins** — Carpeta `plugins/` con carga automática, hot-reload por watchdog, ejemplo auto-generado. Cada plugin registra funciones sin tocar el core.
- [x] **Aprendizaje de correcciones** — Si el usuario dice *"no, me refería a X"*, JARVIS guarda la corrección en SQLite y la aplica en el futuro. Tabla `corrections` con conteo de frecuencia.
- [x] **Notificaciones proactivas** — Vigila CPU/RAM/batería/disco en background. Toast nativo de Windows via PowerShell WinRT. Cooldown anti-spam configurable.
- [x] **Control multimedia avanzado** — Media keys globales (play/pause/next/prev), detección de Spotify (now playing), controles de YouTube en navegador, volumen per-app via pycaw.
- [x] **Multi-monitor** — OCR soporta captura por monitor individual (screeninfo). Vision engine también soporta monitor específico.
- [x] **Integración con calendario** — Calendario local SQLite con eventos, recordatorios automáticos, búsqueda y parseo de fechas en lenguaje natural.

### 🟢 Prioridad baja (nice to have)

- [ ] **Detección multi-idioma dinámica** — Detectar automáticamente el idioma del usuario y cambiar respuesta/transcripción.
- [ ] **Interfaz web alternativa** — Servidor local con WebSocket para acceder desde navegador o móvil.
- [ ] **Control de domótica** — Integración con Home Assistant, Phillips Hue, IoT local.
- [ ] **Modo gaming** — Overlay transparente para juegos con métricas y quick commands.
- [ ] **Exportar conversaciones** — Guardar charlas como Markdown o PDF.
- [ ] **Temas personalizables** — Temas custom además del Arc Reactor (cian).
- [ ] **Perfil de voz** — Ajustar velocidad, tono, elegir entre varias voces.
- [ ] **OCR de imágenes locales** — *"Lee la imagen C:/fotos/captura.png"*.
- [ ] **Traducción en tiempo real** — *"Traduce esto al inglés"* con portapapeles o documento.
- [ ] **Resumen de páginas web** — *"Resume la página que tengo abierta"* con OCR + LLM.
- [ ] **Control de Git** — *"Haz commit con mensaje 'fix'"*, *"push al repo"*.
- [ ] **Dictado continuo** — Modo dictado donde todo se escribe en el documento activo con puntuación automática.

---

## ❓ Solución de problemas

### "Ollama no disponible" / LLM ❌

1. Verifica que Ollama está corriendo: `ollama serve`
2. Comprueba el modelo: `ollama list`
3. Si falta: `ollama pull mistral`

### JARVIS no abre aplicaciones

- Usa la **búsqueda de Windows** (simula Win + escribir + Enter)
- La app debe aparecer en la búsqueda de Windows

### No entiende bien lo que digo (STT)

- El modelo Whisper `small` es el equilibrio calidad/velocidad para español
- Puedes cambiar a `medium` en `config.py` (más preciso pero más lento)
- Asegúrate de que `WHISPER_LANGUAGE = "es"` en `config.py`

### No hace clic en lo correcto (OCR)

- El OCR nativo de Windows requiere el idioma `es-ES` instalado
- Verifica: `Configuración → Hora e idioma → Idioma y región → Español (España)`
- Funciona mejor con texto claro y fondos limpios

### Error con el micrófono

```powershell
pip install faster-whisper sounddevice numpy
```
- Configura tu micrófono como dispositivo predeterminado en Windows

### Error "keyboard requires root"

- Ejecuta la terminal como **Administrador**

---

## 📋 Requisitos del sistema

| | Mínimo | Recomendado |
|---|---|---|
| **OS** | Windows 10 | Windows 11 |
| **RAM** | 8 GB | 16 GB |
| **Disco** | ~5 GB | ~10 GB |
| **CPU** | x64 moderno | i5/Ryzen 5 o superior |
| **GPU** | No necesaria | NVIDIA (CUDA) para acelerar Whisper |

---

## 📄 Licencia

MIT License — ver [LICENSE](LICENSE) para más detalles.

---

<p align="center">
  <em>"Es un placer asistirle, señor."</em> — J.A.R.V.I.S.
</p>
