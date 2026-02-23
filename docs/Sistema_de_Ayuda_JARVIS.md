# Sistema de Ayuda — J.A.R.V.I.S.

## Actividad 1 · Tema 7: Diseño de un sistema de ayuda

---

# FASE 1 — Definir el contexto

## 1️⃣ Aplicación elegida

**J.A.R.V.I.S. (Just A Rather Very Intelligent System)**

Asistente de escritorio con inteligencia artificial para Windows 10/11, inspirado en el J.A.R.V.I.S. de Iron Man. Es una aplicación de escritorio que combina múltiples funciones:

| Módulo | Descripción |
|--------|-------------|
| 🧠 Cerebro IA | Conversación natural con modelos de lenguaje (local o cloud) |
| 🎙️ Voz | Entrada por voz (reconocimiento) + salida TTS (voz sintetizada en español) |
| 👁️ Visión OCR | Lee la pantalla, localiza texto y hace clic inteligente |
| ⚙️ Sistema | Abre/cierra apps, controla volumen, brillo, ventanas |
| 🌐 Web | Búsquedas en Google, navegación automática |
| 📁 Archivos | Abrir, crear, mover, copiar, buscar y organizar archivos |
| 📄 Documentos | Leer y resumir PDF, Word, Excel, CSV |
| 📝 Resolución | Lee ejercicios de un PDF y escribe las soluciones en Word/Google Docs |
| 📧 Email | Envío de correos electrónicos |
| 💻 Código | Ejecución de scripts Python en sandbox seguro |
| ⏰ Automatización | Timers, recordatorios, tareas programadas |
| 🧠 Memoria | Recuerda conversaciones y preferencias del usuario |
| 🎵 Multimedia | Control de Spotify, YouTube, media keys |
| 📋 Portapapeles | Leer y escribir en el portapapeles de Windows |

Se trata de una aplicación con suficiente complejidad y variedad de funciones como para justificar un sistema de ayuda completo.

---

## 2️⃣ Definir el usuario

**¿Quién usará la aplicación?**
Usuarios de Windows (10/11) que quieran automatizar tareas cotidianas en su ordenador mediante lenguaje natural (texto o voz). Perfil principal: estudiantes y usuarios domésticos de entre 16-40 años.

**¿Qué nivel digital tiene?**
Nivel medio. Saben usar un ordenador, instalar programas y navegar por internet, pero no necesariamente tienen conocimientos de programación ni de inteligencia artificial. Pueden necesitar ayuda con la terminal (PowerShell) durante la instalación.

**¿Qué dificultades puede tener?**

- Instalación de dependencias (Python, Ollama, paquetes pip)
- Configuración del modelo de IA (local vs. cloud)
- Formulación correcta de comandos de voz/texto
- Entender por qué el OCR no hace clic donde espera
- Configurar el micrófono correctamente
- Comprender qué puede y qué no puede hacer JARVIS

**¿Qué tipo de ayuda necesitará?**

- **Guías paso a paso** para la instalación y primera configuración
- **Catálogo de comandos** con ejemplos claros por categoría
- **Resolución de problemas frecuentes** (FAQ / troubleshooting)
- **Explicaciones contextuales** sobre cada módulo y sus capacidades
- **Configuración avanzada** para personalizar el comportamiento

---

---

# FASE 2 — Diseño de la estructura de la ayuda

## 3️⃣ Tabla de contenidos (formato jerárquico)

```
📖 Sistema de Ayuda de J.A.R.V.I.S.
│
├── 🏠 Página de inicio
│   ├── Bienvenida
│   └── Novedades de la versión actual
│
├── 📘 Introducción
│   ├── ¿Qué es J.A.R.V.I.S.?
│   ├── Características principales
│   └── Requisitos del sistema
│       ├── Hardware mínimo y recomendado
│       └── Software necesario (Python, Ollama, Git)
│
├── 🚀 Primeros pasos
│   ├── Instalación
│   │   ├── Paso 1 — Clonar el repositorio
│   │   ├── Paso 2 — Crear entorno virtual
│   │   ├── Paso 3 — Instalar dependencias
│   │   ├── Paso 4 — Descargar el modelo de IA
│   │   └── Paso 5 — Ejecutar JARVIS
│   ├── Primera ejecución
│   │   ├── La interfaz HUD
│   │   └── Tu primer comando
│   └── Configuración inicial
│       ├── Modo local vs. cloud
│       └── Configurar API Key (GitHub / Gemini)
│
├── ⚙️ Funciones principales
│   ├── Conversación con la IA
│   │   ├── Escribir mensajes
│   │   └── Usar la voz
│   ├── Control del sistema
│   │   ├── Abrir y cerrar aplicaciones
│   │   ├── Volumen y brillo
│   │   ├── Gestión de ventanas
│   │   └── Información del sistema
│   ├── Interacción visual (OCR)
│   │   ├── Clic por texto en pantalla
│   │   ├── Lectura de pantalla
│   │   └── Doble clic y clic derecho
│   ├── Navegación web
│   │   └── Búsquedas en Google
│   ├── Gestión de archivos
│   │   ├── Abrir y crear archivos
│   │   ├── Mover y copiar
│   │   └── Buscar archivos
│   ├── Documentos
│   │   ├── Leer PDF, Word, Excel
│   │   └── Resolver ejercicios de un PDF
│   ├── Automatización
│   │   ├── Recordatorios y timers
│   │   └── Tareas programadas
│   ├── Multimedia
│   │   ├── Controles de reproducción
│   │   └── Control de Spotify / YouTube
│   ├── Email
│   │   └── Enviar correos
│   └── Memoria y aprendizaje
│       ├── Memoria conversacional
│       └── Procedimientos aprendidos
│
├── 🔧 Configuración avanzada
│   ├── Archivo config.py
│   │   ├── Modelo de IA
│   │   ├── Modelo de voz (Whisper)
│   │   ├── Voz TTS (Piper)
│   │   ├── Atajos de teclado
│   │   └── Interfaz (opacidad, tema)
│   ├── Archivo data/config.json
│   └── Sistema de plugins
│       ├── Cómo crear un plugin
│       └── Carga automática (hot-reload)
│
├── ❌ Resolución de problemas
│   ├── "Ollama no disponible"
│   ├── JARVIS no abre aplicaciones
│   ├── No entiende lo que digo (voz)
│   ├── No hace clic donde debería (OCR)
│   ├── Error con el micrófono
│   ├── Ventanas de PowerShell aparecen
│   └── Error "keyboard requires root"
│
└── ❓ Preguntas frecuentes (FAQ)
    ├── ¿JARVIS funciona sin internet?
    ├── ¿Puedo cambiar el modelo de IA?
    ├── ¿Es compatible con macOS/Linux?
    ├── ¿Puedo usar mi propia API Key?
    ├── ¿Cómo desactivo la voz?
    └── ¿Cómo actualizo JARVIS?
```

---

## 4️⃣ Índice alfabético

```
A
  Aplicaciones
    · abrir ............................ Funciones > Control del sistema
    · cerrar ........................... Funciones > Control del sistema
  API Key
    · configurar ....................... Primeros pasos > Configuración inicial
    · GitHub Models .................... Configuración avanzada > config.py
    · Gemini ........................... Configuración avanzada > config.py
  Archivos
    · abrir ............................ Funciones > Gestión de archivos
    · buscar ........................... Funciones > Gestión de archivos
    · mover / copiar ................... Funciones > Gestión de archivos
  Automatización
    · recordatorios .................... Funciones > Automatización
    · tareas programadas ............... Funciones > Automatización

B
  Brillo
    · ajustar .......................... Funciones > Control del sistema
  Búsqueda web ......................... Funciones > Navegación web

C
  Comandos de voz ...................... Funciones > Conversación con la IA
  Configuración
    · config.py ........................ Configuración avanzada
    · config.json ...................... Configuración avanzada
    · inicial .......................... Primeros pasos > Configuración inicial
  Conversación ......................... Funciones > Conversación con la IA

D
  Documentos
    · leer PDF ......................... Funciones > Documentos
    · resolver ejercicios .............. Funciones > Documentos
  Doble clic ........................... Funciones > Interacción visual (OCR)

E
  Email
    · enviar correo .................... Funciones > Email
  Errores (ver Resolución de problemas)

I
  Instalación .......................... Primeros pasos > Instalación
  Interfaz HUD ......................... Primeros pasos > Primera ejecución

M
  Memoria
    · conversacional ................... Funciones > Memoria y aprendizaje
    · procedimientos ................... Funciones > Memoria y aprendizaje
  Micrófono
    · configurar ....................... Primeros pasos > Configuración inicial
    · errores .......................... Resolución de problemas
  Modelo de IA
    · cambiar .......................... Configuración avanzada > config.py
    · local vs. cloud .................. Primeros pasos > Configuración inicial
  Multimedia ........................... Funciones > Multimedia

O
  OCR
    · clic por texto ................... Funciones > Interacción visual
    · leer pantalla .................... Funciones > Interacción visual
    · problemas ........................ Resolución de problemas
  Ollama
    · instalar ......................... Primeros pasos > Instalación
    · no disponible .................... Resolución de problemas

P
  Plugins .............................. Configuración avanzada > Sistema de plugins
  Portapapeles ......................... Funciones > Control del sistema
  Python
    · instalar ......................... Primeros pasos > Instalación
    · ejecutar código .................. Funciones (sandbox)

R
  Recordatorios ........................ Funciones > Automatización
  Requisitos del sistema ............... Introducción > Requisitos

S
  Spotify .............................. Funciones > Multimedia

V
  Ventanas
    · gestionar ........................ Funciones > Control del sistema
    · enfocar .......................... Funciones > Control del sistema
  Volumen
    · ajustar .......................... Funciones > Control del sistema
  Voz
    · entrada (Whisper) ................ Funciones > Conversación
    · salida (Piper TTS) ............... Funciones > Conversación
    · configurar ....................... Configuración avanzada > config.py
```

---

## 5️⃣ Enlaces cruzados (referencias internas)

Se incluyen al menos **5 referencias internas** entre temas del sistema de ayuda:

1. **Introducción → Primeros pasos**
   > "Si es la primera vez que usa J.A.R.V.I.S., consulte la sección **Primeros pasos > Instalación** para comenzar."

2. **Primeros pasos > Configuración inicial → Configuración avanzada**
   > "Para opciones más detalladas como cambiar el modelo de IA o la voz, consulte **Configuración avanzada > Archivo config.py**."

3. **Funciones > Interacción visual (OCR) → Resolución de problemas**
   > "Si J.A.R.V.I.S. no detecta el texto correctamente, consulte **Resolución de problemas > No hace clic donde debería (OCR)**."

4. **Resolución de problemas > "Ollama no disponible" → Primeros pasos > Instalación**
   > "Asegúrese de haber completado el **Paso 4 — Descargar el modelo de IA** en la guía de instalación."

5. **FAQ > "¿Puedo cambiar el modelo de IA?" → Configuración avanzada**
   > "Sí, cambie el parámetro `OLLAMA_MODEL` en el archivo `config.py`. Véase **Configuración avanzada > Modelo de IA**."

6. **Funciones > Memoria y aprendizaje → Funciones > Automatización**
   > "J.A.R.V.I.S. puede recordar procedimientos completos y repetirlos en el futuro. Esto funciona de manera similar a las **tareas programadas** de la sección Automatización."

---

---

# FASE 3 — Diseño de la interfaz

## 6️⃣ Ventana principal del sistema de ayuda

La ventana del sistema de ayuda sigue la estética futurista de J.A.R.V.I.S. (tema Arc Reactor, colores cyan sobre fondo oscuro) para mantener coherencia visual con la aplicación.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ◄ J.A.R.V.I.S. — Sistema de Ayuda                    _ □ ✕      │
├─────────────────────────────────────────────────────────────────────┤
│  🏠 Inicio  │  🔍 Buscar...                        │  📑 Índice   │
├─────────────┼───────────────────────────────────────────────────────┤
│             │                                                       │
│  📖 CONTENIDO│                                                      │
│             │          ┌─────────────────────────┐                  │
│  ▼ Introducción       │                         │                  │
│    · ¿Qué es?  │      │   ZONA CENTRAL          │                  │
│    · Características   │                         │                  │
│    · Requisitos │      │   Aquí se muestra       │                  │
│             │          │   el contenido del      │                  │
│  ▼ Primeros pasos     │   tema seleccionado     │                  │
│    · Instalación│      │                         │                  │
│    · Primera    │      │   Texto, imágenes,      │                  │
│      ejecución  │      │   pasos, tablas...      │                  │
│    · Configuración     │                         │                  │
│             │          │                         │                  │
│  ▶ Funciones│          │                         │                  │
│  ▶ Configuración       │                         │                  │
│     avanzada│          │                         │                  │
│  ▶ Resolución          └─────────────────────────┘                  │
│     problemas│                                                      │
│  ▶ FAQ      │                                                       │
│             │──────────────────────────────────────────────────────  │
│             │   ◀ Anterior                       Siguiente ▶       │
├─────────────┴───────────────────────────────────────────────────────┤
│  💡 Sugerencia: Pulse Ctrl+Shift+J para mostrar JARVIS rápidamente │
└─────────────────────────────────────────────────────────────────────┘
```

**Componentes de la interfaz:**

| Zona | Descripción |
|------|-------------|
| **Barra superior** | Botón Inicio (volver a portada), barra de búsqueda con texto predictivo y botón Índice (abre índice alfabético). Los botones de ventana (minimizar, maximizar, cerrar) están a la derecha. |
| **Panel lateral izquierdo** | Árbol de contenidos colapsable. Las secciones principales se expanden con ▶/▼ al hacer clic. El tema activo se resalta en cyan (`#00D4FF`). |
| **Zona central** | Muestra el contenido del tema seleccionado: texto explicativo, capturas de pantalla, tablas de comandos, listas numeradas para procedimientos paso a paso. |
| **Botones Anterior / Siguiente** | Navegación secuencial entre temas. Aparecen en la parte inferior de la zona central. Deshabilitados (gris) si no hay tema anterior/siguiente. |
| **Barra inferior** | Sugerencias contextuales y atajos de teclado útiles. Cambia según la sección consultada. |

---

## 7️⃣ Pantallas diseñadas

### Pantalla 1 — Página de inicio

```
┌─────────────────────────────────────────────────────────────────────┐
│  ◄ J.A.R.V.I.S. — Sistema de Ayuda                    _ □ ✕      │
├─────────────────────────────────────────────────────────────────────┤
│  🏠 Inicio  │  🔍 Buscar...                        │  📑 Índice   │
├─────────────┼───────────────────────────────────────────────────────┤
│             │                                                       │
│  📖 CONTENIDO│       ╔═══════════════════════════════╗              │
│             │       ║                               ║              │
│  ● Inicio   │       ║    🤖 J.A.R.V.I.S.            ║              │
│  ▶ Introducción     ║    Sistema de Ayuda           ║              │
│  ▶ Primeros │       ║    v2.0                       ║              │
│    pasos    │       ║                               ║              │
│  ▶ Funciones│       ╚═══════════════════════════════╝              │
│  ▶ Config.  │                                                       │
│    avanzada │    Bienvenido al sistema de ayuda de                  │
│  ▶ Resolución       J.A.R.V.I.S., su asistente personal de IA     │
│    problemas│       para Windows.                                   │
│  ▶ FAQ      │                                                       │
│             │    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━             │
│             │                                                       │
│             │    🚀 INICIO RÁPIDO                                    │
│             │    ┌──────────────────────────────────────┐           │
│             │    │ 1. Instale Python 3.11+ y Ollama     │           │
│             │    │ 2. Clone el repositorio               │           │
│             │    │ 3. Instale las dependencias (pip)     │           │
│             │    │ 4. Descargue el modelo: ollama pull   │           │
│             │    │    mistral                             │           │
│             │    │ 5. Ejecute: python main.py            │           │
│             │    │                                        │           │
│             │    │ → Ver guía completa de instalación    │           │
│             │    └──────────────────────────────────────┘           │
│             │                                                       │
│             │    📌 TEMAS POPULARES                                  │
│             │    · Catálogo de comandos de voz                      │
│             │    · Cómo funciona la visión OCR                      │
│             │    · Resolver ejercicios de un PDF                    │
│             │    · Configurar modo cloud (sin GPU)                  │
│             │                                                       │
│             │    ❓ ¿NECESITA AYUDA?                                 │
│             │    Escriba su consulta en la barra de búsqueda       │
│             │    o navegue por el panel lateral.                    │
│             │                                                       │
│             │────────────────────────────────────────────────────   │
│             │                                    Siguiente ▶       │
├─────────────┴───────────────────────────────────────────────────────┤
│  💡 ¿Primera vez? Vaya a Primeros pasos > Instalación              │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Pantalla 2 — Procedimiento paso a paso: "Instalación de JARVIS"

```
┌─────────────────────────────────────────────────────────────────────┐
│  ◄ J.A.R.V.I.S. — Sistema de Ayuda                    _ □ ✕      │
├─────────────────────────────────────────────────────────────────────┤
│  🏠 Inicio  │  🔍 Buscar...                        │  📑 Índice   │
├─────────────┼───────────────────────────────────────────────────────┤
│             │                                                       │
│  📖 CONTENIDO│  🚀 Primeros pasos > Instalación                    │
│             │  ═══════════════════════════════════════              │
│  ▶ Introducción                                                     │
│  ▼ Primeros │  Siga estos pasos para instalar J.A.R.V.I.S. en     │
│    pasos    │  su equipo Windows.                                   │
│   ● Instalación                                                     │
│    · Primera │  ┌─────────────────────────────────────────────┐     │
│      ejecución   │ ⚠️ REQUISITOS PREVIOS                      │     │
│    · Config. │   │ · Python 3.11 o superior                   │     │
│  ▶ Funciones│   │ · Ollama (motor de IA)                      │     │
│  ▶ Config.  │   │ · Git                                       │     │
│    avanzada │   │ → Ver Introducción > Requisitos del sistema │     │
│  ▶ Resolución   └─────────────────────────────────────────────┘     │
│    problemas│                                                       │
│  ▶ FAQ      │  PASO 1 — Clonar el repositorio                      │
│             │  ─────────────────────────────                        │
│             │  Abra PowerShell y ejecute:                           │
│             │  ┌────────────────────────────────────────────┐       │
│             │  │ git clone https://github.com/.../JARVIS    │       │
│             │  │ cd JARVIS                                   │       │
│             │  └────────────────────────────────────────────┘       │
│             │                                                       │
│             │  PASO 2 — Crear entorno virtual                       │
│             │  ─────────────────────────────                        │
│             │  ┌────────────────────────────────────────────┐       │
│             │  │ python -m venv .venv                        │       │
│             │  │ .\.venv\Scripts\Activate.ps1                │       │
│             │  └────────────────────────────────────────────┘       │
│             │                                                       │
│             │  PASO 3 — Instalar dependencias                       │
│             │  ─────────────────────────────                        │
│             │  ┌────────────────────────────────────────────┐       │
│             │  │ pip install -r requirements.txt             │       │
│             │  └────────────────────────────────────────────┘       │
│             │  Si alguna falla, vea Resolución de problemas.       │
│             │                                                       │
│             │  PASO 4 — Descargar el modelo de IA                   │
│             │  ─────────────────────────────────                    │
│             │  ┌────────────────────────────────────────────┐       │
│             │  │ ollama serve      ← en una terminal        │       │
│             │  │ ollama pull mistral  ← en otra (~4.4 GB)   │       │
│             │  └────────────────────────────────────────────┘       │
│             │  → Si prefiere no descargar nada, use modo cloud.    │
│             │  Vea Configuración avanzada > Modo local vs. cloud.  │
│             │                                                       │
│             │  PASO 5 — Ejecutar JARVIS                             │
│             │  ────────────────────────                             │
│             │  ┌────────────────────────────────────────────┐       │
│             │  │ python main.py                              │       │
│             │  └────────────────────────────────────────────┘       │
│             │  Se abrirá la ventana HUD con el tema Arc Reactor.   │
│             │                                                       │
│             │  ✅ ¡Listo! Vea Primera ejecución para empezar.      │
│             │                                                       │
│             │────────────────────────────────────────────────────   │
│             │  ◀ Anterior                       Siguiente ▶        │
├─────────────┴───────────────────────────────────────────────────────┤
│  💡 Si tiene problemas, consulte Resolución de problemas           │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Pantalla 3 — Página de error / problema frecuente: "No hace clic donde debería (OCR)"

```
┌─────────────────────────────────────────────────────────────────────┐
│  ◄ J.A.R.V.I.S. — Sistema de Ayuda                    _ □ ✕      │
├─────────────────────────────────────────────────────────────────────┤
│  🏠 Inicio  │  🔍 Buscar...                        │  📑 Índice   │
├─────────────┼───────────────────────────────────────────────────────┤
│             │                                                       │
│  📖 CONTENIDO│  ❌ Resolución de problemas                          │
│             │  ═══════════════════════════                          │
│  ▶ Introducción     No hace clic donde debería (OCR)               │
│  ▶ Primeros │  ─────────────────────────────────                    │
│    pasos    │                                                       │
│  ▶ Funciones│  SÍNTOMA                                              │
│  ▶ Config.  │  J.A.R.V.I.S. intenta hacer clic en un texto de     │
│    avanzada │  la pantalla pero hace clic en una posición           │
│  ▼ Resolución       incorrecta, no encuentra el texto, o solo      │
│    problemas│       selecciona en vez de abrir.                     │
│   · Ollama  │                                                       │
│   · Apps    │  ┌────────────────────────────────────────────┐       │
│   · Voz     │  │ 💡 CONSEJO RÁPIDO                          │       │
│   ● OCR     │  │ En el Explorador de archivos y el          │       │
│   · Micro   │  │ escritorio, se necesita DOBLE CLIC para    │       │
│   · PowerShell     │ abrir archivos y carpetas. JARVIS lo  │       │
│   · Permisos│  │ detecta automáticamente. Si no funciona,   │       │
│  ▶ FAQ      │  │ diga: "haz doble clic en [nombre]".       │       │
│             │  └────────────────────────────────────────────┘       │
│             │                                                       │
│             │  CAUSAS POSIBLES Y SOLUCIONES                         │
│             │                                                       │
│             │  1. Idioma OCR no instalado                           │
│             │     El OCR nativo de Windows necesita el paquete      │
│             │     de idioma es-ES instalado.                        │
│             │     → Vaya a: Configuración de Windows >              │
│             │       Hora e idioma > Idioma y región >               │
│             │       Español (España)                                │
│             │                                                       │
│             │  2. Texto poco legible o fondo con ruido              │
│             │     El OCR funciona mejor con texto claro sobre      │
│             │     fondos limpios. Iconos pequeños, texto sobre     │
│             │     imágenes o fuentes decorativas pueden causar      │
│             │     problemas.                                        │
│             │     → Intente ampliar el zoom del navegador o la      │
│             │       resolución de pantalla.                         │
│             │                                                       │
│             │  3. Elemento fuera de pantalla                        │
│             │     Si el texto no es visible (hay que hacer          │
│             │     scroll), JARVIS no podrá encontrarlo.             │
│             │     → Diga "baja" o "scroll down" antes del clic.    │
│             │                                                       │
│             │  4. Texto duplicado en pantalla                       │
│             │     Si el mismo texto aparece varias veces,           │
│             │     JARVIS hará clic en la primera coincidencia.      │
│             │     → Sea más específico: "haz clic en [texto más    │
│             │       largo y único]"                                  │
│             │                                                       │
│             │  → Vea también: Funciones > Interacción visual (OCR) │
│             │                                                       │
│             │────────────────────────────────────────────────────   │
│             │  ◀ Anterior                       Siguiente ▶        │
├─────────────┴───────────────────────────────────────────────────────┤
│  💡 ¿Sigue sin funcionar? Revise los logs en data/logs/jarvis.log  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Pantalla 4 — Página de configuración: "Archivo config.py"

```
┌─────────────────────────────────────────────────────────────────────┐
│  ◄ J.A.R.V.I.S. — Sistema de Ayuda                    _ □ ✕      │
├─────────────────────────────────────────────────────────────────────┤
│  🏠 Inicio  │  🔍 Buscar...                        │  📑 Índice   │
├─────────────┼───────────────────────────────────────────────────────┤
│             │                                                       │
│  📖 CONTENIDO│  🔧 Configuración avanzada > config.py               │
│             │  ═══════════════════════════════════════════          │
│  ▶ Introducción                                                     │
│  ▶ Primeros │  El archivo config.py es el centro de configuración  │
│    pasos    │  de J.A.R.V.I.S. Puede editarlo con cualquier        │
│  ▶ Funciones│  editor de texto.                                     │
│  ▼ Config.  │                                                       │
│    avanzada │  📍 Ubicación: JARVIS/config.py                       │
│   ● config.py                                                       │
│    · config.json    PARÁMETROS PRINCIPALES                          │
│    · Plugins │  ─────────────────────────                           │
│  ▶ Resolución                                                       │
│    problemas│  ┌──────────────┬──────────────┬───────────────────┐  │
│  ▶ FAQ      │  │ Parámetro    │ Valor x def. │ Descripción       │  │
│             │  ├──────────────┼──────────────┼───────────────────┤  │
│             │  │ BRAIN_MODE   │ "cloud"      │ "local" (Ollama)  │  │
│             │  │              │              │ o "cloud" (API)   │  │
│             │  ├──────────────┼──────────────┼───────────────────┤  │
│             │  │ OLLAMA_MODEL │ "mistral"    │ Modelo IA local   │  │
│             │  │              │              │ (mistral, llama3) │  │
│             │  ├──────────────┼──────────────┼───────────────────┤  │
│             │  │ CLOUD_       │ "github"     │ Proveedor cloud:  │  │
│             │  │ PROVIDER     │              │ "github"/"gemini" │  │
│             │  ├──────────────┼──────────────┼───────────────────┤  │
│             │  │ WHISPER_     │ "small"      │ Modelo de voz:    │  │
│             │  │ MODEL        │              │ tiny/base/small/  │  │
│             │  │              │              │ medium            │  │
│             │  ├──────────────┼──────────────┼───────────────────┤  │
│             │  │ WHISPER_     │ "es"         │ Idioma de voz     │  │
│             │  │ LANGUAGE     │              │ forzado           │  │
│             │  ├──────────────┼──────────────┼───────────────────┤  │
│             │  │ TTS_ENABLED  │ True         │ Activar/desact.   │  │
│             │  │              │              │ la voz de salida  │  │
│             │  ├──────────────┼──────────────┼───────────────────┤  │
│             │  │ PIPER_VOICE  │ "es_ES-      │ Modelo de voz TTS │  │
│             │  │              │ davefx-      │ sintética         │  │
│             │  │              │ medium"      │                   │  │
│             │  ├──────────────┼──────────────┼───────────────────┤  │
│             │  │ HOTKEY_      │ ctrl+shift+j │ Atajo global para │  │
│             │  │ ACTIVATE     │              │ mostrar JARVIS    │  │
│             │  ├──────────────┼──────────────┼───────────────────┤  │
│             │  │ HUD_OPACITY  │ 0.95         │ Transparencia del │  │
│             │  │              │              │ HUD (0.0 a 1.0)   │  │
│             │  └──────────────┴──────────────┴───────────────────┘  │
│             │                                                       │
│             │  ⚠️ IMPORTANTE                                        │
│             │  Después de modificar config.py, reinicie JARVIS      │
│             │  para que los cambios surtan efecto.                  │
│             │                                                       │
│             │  → Para configurar API Keys sin editar archivos,      │
│             │  diga: "configura api key github TU_KEY"              │
│             │  Vea Primeros pasos > Configuración inicial.          │
│             │                                                       │
│             │────────────────────────────────────────────────────   │
│             │  ◀ Anterior                       Siguiente ▶        │
├─────────────┴───────────────────────────────────────────────────────┤
│  💡 Modo cloud recomendado si no tiene GPU dedicada                │
└─────────────────────────────────────────────────────────────────────┘
```

---

---

# FASE 4 — Mejora y justificación

## 8️⃣ Prueba de usabilidad

Se realizó un intercambio con otra pareja. Se les pidió las siguientes tareas de prueba:

### Tarea 1: "Encuentra cómo cambiar el modelo de IA"
- **Resultado**: Lo encontraron por el índice alfabético (Modelo de IA → Configuración avanzada > config.py). ✅
- **Tiempo**: ~15 segundos
- **Observación**: "Fácil, el índice ayuda mucho"

### Tarea 2: "¿Cómo se resuelven ejercicios de un PDF?"
- **Resultado**: Usaron la barra de búsqueda → "ejercicios PDF" → llevó a Funciones > Documentos > Resolver ejercicios. ✅
- **Tiempo**: ~10 segundos
- **Observación**: "¿Pero cómo se escribe el comando exacto?" → **Detectado: faltaba un ejemplo de comando concreto en esa sección**

### Tarea 3: "JARVIS no me escucha, ¿qué hago?"
- **Resultado**: Fueron a Resolución de problemas, pero dudaron entre "No entiende lo que digo (voz)" y "Error con el micrófono". ✅ parcial
- **Tiempo**: ~25 segundos
- **Observación**: "Los dos títulos se parecen mucho, no sé cuál elegir" → **Detectado: confusión entre dos secciones similares**

### Tarea 4: "¿Funciona sin internet?"
- **Resultado**: Fueron directamente a FAQ > "¿JARVIS funciona sin internet?". ✅
- **Tiempo**: ~5 segundos

### Errores de navegación detectados:
- No hubo problemas con la estructura del panel lateral ni con los botones Anterior/Siguiente
- El enlace cruzado de "Resolución de problemas > OCR → Funciones > Interacción visual" fue útil

---

## 9️⃣ Mejoras aplicadas (basadas en el feedback)

### Mejora 1: Añadir ejemplos de comandos en cada sección de funciones

**Problema detectado**: En la prueba de "resolver ejercicios de un PDF", el evaluador encontró la sección correcta pero no sabía el comando exacto a escribir.

**Solución**: Se añade un bloque de **"Ejemplos de uso"** con comandos reales al final de cada sección de funciones principales. Por ejemplo, en Documentos > Resolver ejercicios:

```
EJEMPLOS DE USO
─────────────────
  · "Resuelve los ejercicios del PDF C:/docs/mates.pdf"
  · "Haz los ejercicios del PDF examen.pdf en Word"
  · "Contesta las preguntas del PDF test.pdf en Google Docs"
```

Esto se aplica a las 10 secciones funcionales, con 2-3 ejemplos de comandos cada una.

### Mejora 2: Unificar secciones de problemas de audio

**Problema detectado**: El evaluador no distinguía entre "No entiende lo que digo (voz)" y "Error con el micrófono" — ambas secciones tratan problemas de audio/voz.

**Solución**: Se unifican en una sola sección llamada **"Problemas con la voz y el micrófono"** que cubre:

1. **No entiende lo que digo** → Configuración de Whisper (modelo, idioma)
2. **El micrófono no funciona** → Configuración de hardware, dependencias
3. **No habla / no emite sonido** → Configuración de Piper TTS

De esta forma, el usuario que tenga cualquier problema de audio llega a un solo lugar y encuentra la subsección correcta.

### Mejora 3 (adicional): Añadir breadcrumbs de ubicación

**Observación**: Aunque no fue un error grave, algunos evaluadores "se perdían" al profundizar en secciones anidadas y no sabían dónde estaban dentro del árbol.

**Solución**: Se añade un **breadcrumb** (ruta de migas) en la parte superior de la zona central:

```
📍 Inicio > Primeros pasos > Instalación > Paso 3
```

Cada nivel del breadcrumb es clickable para volver a niveles superiores.

---

---

# Resumen del diseño

| Elemento | Implementado |
|----------|:---:|
| Aplicación con varias funciones | ✅ |
| Perfil de usuario definido | ✅ |
| Tabla de contenidos jerárquica | ✅ |
| Índice alfabético (12+ palabras clave con subniveles) | ✅ |
| Enlaces cruzados (6 referencias internas) | ✅ |
| Ventana principal con barra, panel, zona central, botones nav | ✅ |
| Pantalla 1: Página de inicio | ✅ |
| Pantalla 2: Procedimiento paso a paso (Instalación) | ✅ |
| Pantalla 3: Error frecuente (OCR no funciona) | ✅ |
| Pantalla 4: Página de configuración (config.py) | ✅ |
| Prueba con otra pareja | ✅ |
| Al menos 2 mejoras aplicadas (3 realizadas) | ✅ |

---

> *"Es un placer asistirle, señor."* — J.A.R.V.I.S.
