"""
J.A.R.V.I.S. — HUD Widgets
Componentes personalizados para la interfaz futurista.
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy,
    QFrame,
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter, QFont

from ui.styles import (
    ACCENT, ACCENT_DIM, ACCENT_GLOW, BG_SECONDARY, BG_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR,
)


class StatusIndicator(QWidget):
    """Indicador visual de estado (punto coloreado con animación)."""

    STATES = {
        "idle": ACCENT_DIM,
        "listening": "#4488FF",
        "processing": WARNING_COLOR,
        "speaking": SUCCESS_COLOR,
        "error": ERROR_COLOR,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._color = QColor(ACCENT_DIM)
        self._state = "idle"
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_value = 255

    def set_state(self, state: str):
        """Cambia el estado del indicador."""
        self._state = state
        color_hex = self.STATES.get(state, ACCENT_DIM)
        self._color = QColor(color_hex)

        if state in ("listening", "processing"):
            self._pulse_timer.start(50)
        else:
            self._pulse_timer.stop()
            self._pulse_value = 255

        self.update()

    def _pulse(self):
        import math
        t = self._pulse_timer.interval()
        self._pulse_value = int(180 + 75 * math.sin(
            self._pulse_timer.remainingTime() * 0.01
        ))
        self._pulse_value = max(100, min(255, self._pulse_value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(self._color)
        color.setAlpha(self._pulse_value)

        # Glow exterior
        glow_color = QColor(color)
        glow_color.setAlpha(50)
        painter.setBrush(glow_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 14, 14)

        # Punto interior
        painter.setBrush(color)
        painter.drawEllipse(3, 3, 8, 8)
        painter.end()


class MessageBubble(QFrame):
    """Burbuja de mensaje en el chat."""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Nombre del remitente
        sender_label = QLabel("Usted" if is_user else "J.A.R.V.I.S.")
        sender_label.setObjectName("messageSender")
        sender_label.setStyleSheet(
            f"color: {ACCENT if not is_user else TEXT_SECONDARY}; "
            f"font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(sender_label)

        # Contenido del mensaje
        content_label = QLabel(text)
        content_label.setObjectName("messageLabel")
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        layout.addWidget(content_label)

        # Estilos de la burbuja
        if is_user:
            self.setStyleSheet(f"""
                MessageBubble {{
                    background-color: rgba(0, 212, 255, 0.06);
                    border-left: 3px solid {ACCENT};
                    border-radius: 0px 8px 8px 0px;
                    margin-right: 40px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                MessageBubble {{
                    background-color: rgba(15, 17, 24, 0.8);
                    border-left: 3px solid {ACCENT_DIM};
                    border-radius: 0px 8px 8px 0px;
                    margin-left: 40px;
                }}
            """)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)


class SystemMetricWidget(QWidget):
    """Widget para mostrar una métrica del sistema (CPU, RAM, etc.)."""

    def __init__(self, label: str, value: str = "0%", icon: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)

        self._label = label
        self._icon = icon

        # Etiqueta
        self.label_widget = QLabel(f"{icon} {label}:")
        self.label_widget.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px;"
        )
        layout.addWidget(self.label_widget)

        # Valor
        self.value_widget = QLabel(value)
        self.value_widget.setObjectName("metricValue")
        self.value_widget.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(self.value_widget)

    def set_value(self, value: str):
        """Actualiza el valor de la métrica."""
        self.value_widget.setText(value)

        # Colorear según el valor si es porcentaje
        try:
            num = int(value.replace("%", "").strip())
            if num > 80:
                color = ERROR_COLOR
            elif num > 60:
                color = WARNING_COLOR
            else:
                color = ACCENT
            self.value_widget.setStyleSheet(
                f"color: {color}; font-size: 11px; font-weight: bold;"
            )
        except ValueError:
            pass


class TitleBar(QWidget):
    """Barra de título personalizada (frameless window)."""

    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, title: str = "J.A.R.V.I.S.", parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(40)
        self._dragging = False
        self._drag_position = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 4, 0)
        layout.setSpacing(8)

        # Indicador de estado
        self.status_indicator = StatusIndicator()
        layout.addWidget(self.status_indicator)

        # Título
        title_label = QLabel(title)
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet(
            f"color: {ACCENT}; font-size: 15px; font-weight: bold; "
            f"letter-spacing: 3px;"
        )
        layout.addWidget(title_label)

        layout.addStretch()

        # Botones de ventana
        btn_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {TEXT_SECONDARY};
                font-size: 14px;
                padding: 6px 12px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {BG_TERTIARY};
                color: {TEXT_PRIMARY};
            }}
        """

        from PySide6.QtWidgets import QPushButton

        # Minimizar
        min_btn = QPushButton("─")
        min_btn.setStyleSheet(btn_style)
        min_btn.setFixedSize(40, 30)
        min_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(min_btn)

        # Maximizar
        max_btn = QPushButton("□")
        max_btn.setStyleSheet(btn_style)
        max_btn.setFixedSize(40, 30)
        max_btn.clicked.connect(self.maximize_clicked.emit)
        layout.addWidget(max_btn)

        # Cerrar
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeButton")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {TEXT_SECONDARY};
                font-size: 14px;
                padding: 6px 12px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {ERROR_COLOR};
                color: white;
            }}
        """)
        close_btn.setFixedSize(40, 30)
        close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(close_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.window().pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_position:
            self.window().move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._drag_position = None

    def mouseDoubleClickEvent(self, event):
        self.maximize_clicked.emit()
