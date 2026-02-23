/* ═══════════════════════════════════════════════════════════
   J.A.R.V.I.S. — Documentation Site Scripts
   Sidebar, search, navigation
   ═══════════════════════════════════════════════════════════ */

// ─── Search index ──────────────────────────────────────────
const SEARCH_INDEX = [
  { title: "Página de inicio",            url: "index.html",            tags: "inicio bienvenida home jarvis", desc: "Página principal del sistema de ayuda" },
  { title: "¿Qué es J.A.R.V.I.S.?",      url: "introduccion.html",     tags: "que es introduccion características funciones resumen", desc: "Introducción y características principales" },
  { title: "Requisitos del sistema",       url: "introduccion.html#requisitos", tags: "requisitos hardware ram cpu python ollama", desc: "Hardware y software necesario" },
  { title: "Instalación paso a paso",      url: "instalacion.html",      tags: "instalar instalación setup clonar pip dependencias", desc: "Guía completa de instalación" },
  { title: "Entorno virtual (venv)",       url: "instalacion.html#paso2", tags: "venv entorno virtual python activar", desc: "Crear y activar el entorno virtual" },
  { title: "Descargar modelo IA",          url: "instalacion.html#paso4", tags: "ollama modelo mistral descargar pull", desc: "Descargar el modelo de inteligencia artificial" },
  { title: "Primera ejecución",            url: "interfaz.html",         tags: "primera ejecucion ejecutar hud ventana interfaz", desc: "Ejecutar JARVIS por primera vez" },
  { title: "Interfaz HUD",                url: "interfaz.html#hud",     tags: "hud interfaz chat burbuja micrófono atajo", desc: "La ventana principal del asistente" },
  { title: "Comandos del sistema",        url: "comandos.html",          tags: "comandos abrir cerrar volumen brillo sistema ventanas", desc: "Catálogo completo de comandos" },
  { title: "Abrir / cerrar aplicaciones", url: "comandos.html#sistema",  tags: "abrir cerrar app aplicación chrome discord", desc: "Controlar aplicaciones del sistema" },
  { title: "Volumen y brillo",            url: "comandos.html#sistema",  tags: "volumen brillo subir bajar silenciar mute", desc: "Ajustar volumen y brillo" },
  { title: "Gestión de ventanas",         url: "comandos.html#ventanas", tags: "ventana enfocar minimizar maximizar snap", desc: "Enfocar, minimizar, snap" },
  { title: "Búsqueda web",               url: "comandos.html#web",      tags: "buscar web google búsqueda internet", desc: "Buscar en Google" },
  { title: "Gestión de archivos",         url: "comandos.html#archivos", tags: "archivos abrir crear mover copiar buscar", desc: "Operaciones con archivos" },
  { title: "Documentos (PDF, Word...)",   url: "comandos.html#documentos", tags: "pdf word excel documento leer resumir ejercicios resolver", desc: "Leer, resumir y resolver ejercicios" },
  { title: "Email",                       url: "comandos.html#email",    tags: "email correo enviar smtp", desc: "Enviar correos electrónicos" },
  { title: "Automatización",             url: "comandos.html#automatizacion", tags: "timer recordatorio tarea programada automatizar", desc: "Timers, recordatorios, tareas" },
  { title: "Multimedia",                 url: "comandos.html#multimedia", tags: "spotify youtube play pause música media", desc: "Control multimedia" },
  { title: "Interacción visual (OCR)",    url: "ocr.html",               tags: "ocr clic texto pantalla visual leer doble click", desc: "Cómo JARVIS lee e interactúa con la pantalla" },
  { title: "Clic por texto",             url: "ocr.html#clic",           tags: "clic click texto ocr botón pulsar", desc: "Hacer clic buscando texto en pantalla" },
  { title: "Doble clic",                 url: "ocr.html#doble-clic",     tags: "doble clic double click explorador escritorio abrir", desc: "Cuándo se usa doble clic automáticamente" },
  { title: "Lectura de pantalla",        url: "ocr.html#lectura",        tags: "leer pantalla qué hay screen", desc: "Leer todo el texto visible" },
  { title: "Configuración (config.py)",  url: "configuracion.html",      tags: "configurar config modelo whisper voz tts atajo", desc: "Parámetros de configuración" },
  { title: "Modo local vs. cloud",       url: "configuracion.html#modo", tags: "local cloud api github gemini gpt-4o-mini ollama modo proveedor", desc: "Elegir entre IA local o cloud (GPT-4o-mini, Gemini)" },
  { title: "API Key",                    url: "configuracion.html#apikey", tags: "api key token github gemini configurar clave gpt", desc: "Configurar claves de API gratuitas" },
  { title: "Plugins",                    url: "configuracion.html#plugins", tags: "plugin extensión crear cargar hot reload", desc: "Sistema de plugins" },
  { title: "Memoria y aprendizaje",      url: "configuracion.html#memoria", tags: "memoria recordar aprendizaje procedimiento sqlite", desc: "Memoria conversacional y procedimientos" },
  { title: "Resolución de problemas",    url: "problemas.html",          tags: "error problema fallo no funciona solución", desc: "Soluciones a problemas frecuentes" },
  { title: "Ollama no disponible",       url: "problemas.html#ollama",   tags: "ollama no disponible error modelo", desc: "Solucionar error de Ollama" },
  { title: "Problemas con voz / micrófono", url: "problemas.html#voz",  tags: "voz micrófono no entiende whisper piper tts", desc: "Soluciones para audio y voz" },
  { title: "Problemas con OCR / clic",   url: "problemas.html#ocr",     tags: "ocr clic no funciona idioma visual", desc: "Solucionar problemas de OCR" },
  { title: "Preguntas frecuentes",       url: "problemas.html#faq",     tags: "faq preguntas frecuentes internet modelo actualizar", desc: "Respuestas rápidas" },
  { title: "Índice alfabético",          url: "indice.html",             tags: "indice alfabético buscar palabra clave", desc: "Búsqueda por palabra clave" },
];

// ─── Sidebar toggle ────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Hamburger
  const hamburger = document.querySelector(".hamburger");
  const sidebar = document.querySelector(".sidebar");
  if (hamburger && sidebar) {
    hamburger.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.querySelector(".main")?.addEventListener("click", () => sidebar.classList.remove("open"));
  }

  // Sidebar sections
  document.querySelectorAll(".sidebar-section-title").forEach(title => {
    title.addEventListener("click", () => {
      title.classList.toggle("open");
    });
    // Auto-open if contains current page link
    const links = title.nextElementSibling;
    if (links && links.querySelector(".current")) {
      title.classList.add("open");
    }
  });

  // ─── Search ───────────────────────────────────────────────
  const searchInput = document.getElementById("searchInput");
  const searchResults = document.getElementById("searchResults");

  if (searchInput && searchResults) {
    searchInput.addEventListener("input", () => {
      const q = searchInput.value.trim().toLowerCase();
      if (q.length < 2) {
        searchResults.classList.remove("active");
        searchResults.innerHTML = "";
        return;
      }
      const words = q.split(/\s+/);
      const matches = SEARCH_INDEX.filter(item => {
        const haystack = (item.title + " " + item.tags + " " + item.desc).toLowerCase();
        return words.every(w => haystack.includes(w));
      }).slice(0, 8);

      if (matches.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item"><span class="sr-title">Sin resultados</span></div>';
      } else {
        searchResults.innerHTML = matches.map(m =>
          `<a href="${m.url}" class="search-result-item">
            <div class="sr-title">${m.title}</div>
            <div class="sr-desc">${m.desc}</div>
          </a>`
        ).join("");
      }
      searchResults.classList.add("active");
    });

    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        searchResults.classList.remove("active");
        searchInput.blur();
      }
    });

    document.addEventListener("click", (e) => {
      if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.classList.remove("active");
      }
    });
  }
});
