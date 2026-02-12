"""
J.A.R.V.I.S. — HUD (Heads-Up Display)
Interfaz gráfica principal — ventana frameless futurista.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QLabel,
    QSystemTrayIcon, QMenu, QApplication, QSizePolicy,
    QFrame,
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QSize, QThread, QObject,
)
from PySide6.QtGui import (
    QIcon, QAction, QFont, QKeySequence, QShortcut,
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    HUD_WINDOW_TITLE, HUD_WIDTH, HUD_HEIGHT, HUD_OPACITY,
    HUD_ALWAYS_ON_TOP, HUD_ACCENT_COLOR, HOTKEY_MUTE,
)
from ui.styles import MAIN_STYLESHEET, ACCENT, BG_SECONDARY, TEXT_SECONDARY
from ui.widgets import (
    TitleBar, MessageBubble, SystemMetricWidget, StatusIndicator,
)

logger = logging.getLogger("jarvis.hud")


# ─── Worker para procesar mensajes en hilo separado ──────────

class MessageWorker(QObject):
    """Worker que procesa mensajes en un hilo separado."""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, orchestrator, message):
        super().__init__()
        self.orchestrator = orchestrator
        self.message = message

    @Slot()
    def process(self):
        try:
            response = self.orchestrator.process(self.message)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))


class JarvisHUD(QMainWindow):
    """Ventana principal del HUD de JARVIS."""

    # Señales
    message_received = Signal(str)
    tts_requested = Signal(str)

    def __init__(self, orchestrator=None, voice_input=None, voice_output=None):
        super().__init__()

        self.orchestrator = orchestrator
        self.voice_input = voice_input
        self.voice_output = voice_output
        self._is_recording = False
        self._is_maximized = False
        self._is_processing = False
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[MessageWorker] = None

        self._setup_window()
        self._setup_ui()
        self._setup_tray()
        self._setup_timers()
        self._setup_shortcuts()

        logger.info("HUD inicializado.")

    # ─── Configuración de la ventana ──────────────────────────

    def _setup_window(self):
        """Configura la ventana principal."""
        self.setWindowTitle(HUD_WINDOW_TITLE)
        self.setMinimumSize(600, 400)
        self.resize(HUD_WIDTH, HUD_HEIGHT)

        # Ventana sin bordes
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Window
        )

        if HUD_ALWAYS_ON_TOP:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Transparencia
        self.setWindowOpacity(HUD_OPACITY)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Icono
        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Estilo
        self.setStyleSheet(MAIN_STYLESHEET)

    # ─── Layout principal ─────────────────────────────────────

    def _setup_ui(self):
        """Construye la interfaz principal del HUD."""
        central = QWidget()
        central.setStyleSheet(f"background-color: #0A0A0F;")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Barra de título ──
        self.title_bar = TitleBar(HUD_WINDOW_TITLE)
        self.title_bar.minimize_clicked.connect(self._minimize)
        self.title_bar.maximize_clicked.connect(self._toggle_maximize)
        self.title_bar.close_clicked.connect(self._close)
        main_layout.addWidget(self.title_bar)

        # ── Área de chat ──
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chatScroll")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.chat_container = QWidget()
        self.chat_container.setObjectName("chatArea")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(4)
        self.chat_layout.setAlignment(Qt.AlignTop)

        self.chat_scroll.setWidget(self.chat_container)
        main_layout.addWidget(self.chat_scroll, 1)

        # ── Mensaje de bienvenida ──
        self._add_assistant_message(
            "Buenos días, señor. JARVIS a su servicio. "
            "¿En qué puedo asistirle hoy?"
        )

        # ── Barra de input ──
        input_bar = QWidget()
        input_bar.setObjectName("inputBar")
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        # Botón de micrófono (toggle: clic para grabar, clic para parar)
        self.mic_button = QPushButton("🎤")
        self.mic_button.setObjectName("micButton")
        self.mic_button.setToolTip("Clic para hablar / Clic para parar")
        self.mic_button.clicked.connect(self._toggle_recording)
        input_layout.addWidget(self.mic_button)

        # Campo de texto
        self.input_field = QLineEdit()
        self.input_field.setObjectName("inputField")
        self.input_field.setPlaceholderText("Escriba un mensaje, señor...")
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field, 1)

        # Botón enviar
        self.send_button = QPushButton("➤")
        self.send_button.setObjectName("sendButton")
        self.send_button.setToolTip("Enviar mensaje")
        self.send_button.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_button)

        main_layout.addWidget(input_bar)

        # ── Barra de estado / métricas ──
        status_bar = QWidget()
        status_bar.setObjectName("statusBar")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(12, 4, 12, 4)
        status_layout.setSpacing(16)

        # Estado
        self.status_indicator = StatusIndicator()
        status_layout.addWidget(self.status_indicator)

        self.status_label = QLabel("Listo")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        # Métricas del sistema
        self.cpu_metric = SystemMetricWidget("CPU", "0%", "🔲")
        status_layout.addWidget(self.cpu_metric)

        separator1 = QLabel("│")
        separator1.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        status_layout.addWidget(separator1)

        self.ram_metric = SystemMetricWidget("RAM", "0%", "💾")
        status_layout.addWidget(self.ram_metric)

        separator2 = QLabel("│")
        separator2.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        status_layout.addWidget(separator2)

        self.vol_metric = SystemMetricWidget("Vol", "0%", "🔊")
        status_layout.addWidget(self.vol_metric)

        separator3 = QLabel("│")
        separator3.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        status_layout.addWidget(separator3)

        self.time_label = QLabel("00:00")
        self.time_label.setObjectName("metricValue")
        self.time_label.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: bold;"
        )
        status_layout.addWidget(self.time_label)

        main_layout.addWidget(status_bar)

    # ─── System Tray ──────────────────────────────────────────

    def _setup_tray(self):
        """Configura el icono en la bandeja del sistema."""
        self.tray_icon = QSystemTrayIcon(self)

        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(
                self.style().StandardPixmap.SP_ComputerIcon
            ))

        # Menú de la bandeja
        tray_menu = QMenu()
        show_action = QAction("Mostrar JARVIS", self)
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addAction(show_action)

        mute_action = QAction("Silenciar/Activar voz", self)
        mute_action.triggered.connect(self._toggle_tts)
        tray_menu.addAction(mute_action)

        tray_menu.addSeparator()

        quit_action = QAction("Salir", self)
        quit_action.triggered.connect(self._quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.setToolTip("J.A.R.V.I.S. — Asistente IA")
        self.tray_icon.show()

    # ─── Timers ───────────────────────────────────────────────

    def _setup_timers(self):
        """Configura los timers para actualizaciones periódicas."""
        # Actualización de métricas del sistema cada 2 segundos
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self._update_metrics)
        self.metrics_timer.start(2000)

        # Actualización del reloj cada segundo
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        # Primera actualización inmediata
        self._update_metrics()
        self._update_clock()

    # ─── Shortcuts ────────────────────────────────────────────

    def _setup_shortcuts(self):
        """Configura los atajos de teclado."""
        # Ctrl+Shift+M para silenciar TTS
        QShortcut(QKeySequence("Ctrl+Shift+M"), self, self._toggle_tts)

        # Escape para minimizar
        QShortcut(QKeySequence("Escape"), self, self._minimize)

    # ─── Manejo de mensajes ───────────────────────────────────

    @Slot()
    def _send_message(self):
        """Envía el mensaje del campo de texto."""
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()
        self._add_user_message(text)
        self._process_message(text)

    def _process_message(self, text: str):
        """Procesa un mensaje del usuario en un hilo separado."""
        if not self.orchestrator:
            self._add_assistant_message(
                "Me temo que mi motor de razonamiento no está disponible, señor."
            )
            return

        # Bloquear si ya hay un mensaje en proceso
        if self._is_processing:
            self._add_assistant_message(
                "Un momento, señor. Aún estoy procesando su solicitud anterior."
            )
            return

        self._is_processing = True

        # Cambiar estado a procesando y deshabilitar toda la entrada
        self._set_state("processing", "Procesando...")
        self._set_input_enabled(False)

        # Limpiar hilo anterior si existe
        if self._worker_thread is not None:
            if self._worker_thread.isRunning():
                self._worker_thread.quit()
                self._worker_thread.wait(2000)
            self._worker_thread.deleteLater()
            self._worker_thread = None
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

        # Ejecutar en hilo separado
        self._worker_thread = QThread()
        self._worker = MessageWorker(self.orchestrator, text)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.process)
        self._worker.finished.connect(self._on_response)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)

        self._worker_thread.start()

    def _set_input_enabled(self, enabled: bool):
        """Habilita o deshabilita todos los controles de entrada."""
        self.send_button.setEnabled(enabled)
        self.input_field.setEnabled(enabled)
        self.mic_button.setEnabled(enabled)

    @Slot(str)
    def _on_response(self, response: str):
        """Callback cuando el LLM responde."""
        self._is_processing = False
        self._add_assistant_message(response)
        self._set_state("idle", "Listo")
        self._set_input_enabled(True)
        self.input_field.setFocus()

        # TTS
        if self.voice_output and self.voice_output.enabled:
            self._set_state("speaking", "Hablando...")
            self.voice_output.speak(response)
            # Restaurar estado cuando termine de hablar
            QTimer.singleShot(500, lambda: self._set_state("idle", "Listo"))

    @Slot(str)
    def _on_error(self, error: str):
        """Callback en caso de error."""
        self._is_processing = False
        self._add_assistant_message(
            f"Me temo que ha ocurrido un error, señor: {error}"
        )
        self._set_state("error", "Error")
        self._set_input_enabled(True)
        self.input_field.setFocus()
        QTimer.singleShot(3000, lambda: self._set_state("idle", "Listo"))

    # ─── Chat UI ──────────────────────────────────────────────

    def _add_user_message(self, text: str):
        """Agrega un mensaje del usuario al chat."""
        bubble = MessageBubble(text, is_user=True)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def _add_assistant_message(self, text: str):
        """Agrega un mensaje de JARVIS al chat."""
        bubble = MessageBubble(text, is_user=False)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def add_message(self, text: str, is_user: bool = False):
        """Método público para agregar mensajes."""
        if is_user:
            self._add_user_message(text)
        else:
            self._add_assistant_message(text)

    def _scroll_to_bottom(self):
        """Scrollea al final del chat."""
        QTimer.singleShot(100, lambda: (
            self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            )
        ))

    def clear_chat(self):
        """Limpia todos los mensajes del chat."""
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ─── Grabación de voz ─────────────────────────────────────

    def _toggle_recording(self):
        """Toggle: iniciar o detener grabación de voz."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Inicia la grabación de voz."""
        if not self.voice_input or not self.voice_input.is_model_loaded:
            self._add_assistant_message(
                "El sistema de reconocimiento de voz no está disponible, señor."
            )
            return

        self._is_recording = True
        self._set_state("listening", "Escuchando... (clic 🎤 para parar)")
        self.mic_button.setProperty("recording", True)
        self.mic_button.style().unpolish(self.mic_button)
        self.mic_button.style().polish(self.mic_button)
        self.mic_button.setText("⏹")
        self.voice_input.start_recording()

        # Auto-stop después de 15 segundos para evitar grabación infinita
        self._recording_timer = QTimer()
        self._recording_timer.setSingleShot(True)
        self._recording_timer.timeout.connect(self._stop_recording)
        self._recording_timer.start(15000)

    def _stop_recording(self):
        """Detiene la grabación y procesa el audio."""
        if not self._is_recording:
            return

        self._is_recording = False
        self.mic_button.setProperty("recording", False)
        self.mic_button.style().unpolish(self.mic_button)
        self.mic_button.style().polish(self.mic_button)
        self.mic_button.setText("🎤")

        # Cancelar el timer de auto-stop
        if hasattr(self, '_recording_timer') and self._recording_timer.isActive():
            self._recording_timer.stop()

        self._set_state("processing", "Transcribiendo...")

        if self.voice_input:
            text = self.voice_input.stop_recording()
            if text:
                self._add_user_message(text)
                self._process_message(text)
            else:
                self._add_assistant_message(
                    "No he podido escuchar nada, señor. "
                    "Inténtelo de nuevo hablándo más cerca del micrófono."
                )
                self._set_state("idle", "Listo")

    # ─── Estado ───────────────────────────────────────────────

    def _set_state(self, state: str, label: str):
        """Cambia el estado visual del HUD."""
        self.status_indicator.set_state(state)
        self.title_bar.status_indicator.set_state(state)
        self.status_label.setText(label)

    # ─── Métricas ─────────────────────────────────────────────

    @Slot()
    def _update_metrics(self):
        """Actualiza las métricas del sistema en la barra de estado."""
        if self.orchestrator:
            try:
                status = self.orchestrator.get_system_status()
                self.cpu_metric.set_value(f"{status.get('cpu', 0):.0f}%")
                self.ram_metric.set_value(f"{status.get('ram', 0):.0f}%")
                vol = status.get("volume", 0)
                self.vol_metric.set_value(f"{vol}%" if vol >= 0 else "N/A")
            except Exception:
                pass
        else:
            # Fallback: usar psutil directamente
            try:
                import psutil
                self.cpu_metric.set_value(f"{psutil.cpu_percent():.0f}%")
                self.ram_metric.set_value(f"{psutil.virtual_memory().percent:.0f}%")
            except ImportError:
                pass

    @Slot()
    def _update_clock(self):
        """Actualiza el reloj."""
        import datetime
        now = datetime.datetime.now()
        self.time_label.setText(now.strftime("%H:%M"))

    # ─── Control de ventana ───────────────────────────────────

    def _minimize(self):
        """Minimiza a la bandeja del sistema."""
        self.hide()
        if self.tray_icon:
            self.tray_icon.showMessage(
                "J.A.R.V.I.S.",
                "Minimizado a la bandeja del sistema. "
                "Haga clic para restaurar.",
                QSystemTrayIcon.Information,
                2000,
            )

    def _toggle_maximize(self):
        """Alterna entre maximizar y restaurar."""
        if self._is_maximized:
            self.showNormal()
        else:
            self.showMaximized()
        self._is_maximized = not self._is_maximized

    def _close(self):
        """Cierra la ventana (minimiza a tray)."""
        self._minimize()

    def _show_from_tray(self):
        """Restaura la ventana desde la bandeja."""
        self.show()
        self.activateWindow()
        self.raise_()

    def _tray_activated(self, reason):
        """Callback cuando se interactúa con el icono de la bandeja."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _toggle_tts(self):
        """Activa/desactiva el TTS."""
        if self.voice_output:
            enabled = self.voice_output.toggle()
            status = "activada" if enabled else "silenciada"
            self._add_assistant_message(f"Voz {status}, señor.")

    def _quit(self):
        """Cierra completamente la aplicación."""
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    # ─── Método público para entrada externa ──────────────────

    def process_external_input(self, text: str):
        """Procesa input que viene de fuera del HUD (hotkey, wake word)."""
        self._show_from_tray()
        self._add_user_message(text)
        self._process_message(text)

    # ─── Override closeEvent ──────────────────────────────────

    def closeEvent(self, event):
        """Intercepta el cierre para minimizar a tray."""
        event.ignore()
        self._minimize()
