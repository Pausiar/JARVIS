"""
J.A.R.V.I.S. — HUD Styles
Estilos QSS para la interfaz futurista tipo Arc Reactor.
"""

# ─── Colores principales ─────────────────────────────────────
ACCENT = "#00D4FF"      # Azul cyan (Arc Reactor)
ACCENT_DIM = "#0099BB"  # Cyan más oscuro
ACCENT_GLOW = "#00E5FF" # Cyan brillante
BG_PRIMARY = "#0A0A0F"  # Negro casi puro
BG_SECONDARY = "#0F1118"  # Negro con tinte azul
BG_TERTIARY = "#151822"   # Gris muy oscuro
TEXT_PRIMARY = "#E0E0E0"   # Blanco suave
TEXT_SECONDARY = "#8899AA" # Gris azulado
TEXT_ACCENT = "#00D4FF"    # Cyan
ERROR_COLOR = "#FF4444"    # Rojo
WARNING_COLOR = "#FFAA00"  # Ámbar
SUCCESS_COLOR = "#44FF44"  # Verde
BORDER_COLOR = "#1A2030"   # Borde sutil

# ─── Stylesheet principal ─────────────────────────────────────

MAIN_STYLESHEET = f"""
/* ═══════════════════════════════════════════════ */
/*  J.A.R.V.I.S. HUD — Main Stylesheet           */
/* ═══════════════════════════════════════════════ */

/* ─── Ventana principal ───────────────────────── */
QMainWindow {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
}}

QWidget {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
    font-size: 13px;
}}

/* ─── Barra de título personalizada ───────────── */
#titleBar {{
    background-color: {BG_SECONDARY};
    border-bottom: 1px solid {ACCENT_DIM};
    padding: 4px 8px;
    min-height: 36px;
}}

#titleLabel {{
    color: {ACCENT};
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 3px;
}}

#titleBar QPushButton {{
    background: transparent;
    border: none;
    color: {TEXT_SECONDARY};
    font-size: 16px;
    padding: 4px 10px;
    border-radius: 3px;
}}

#titleBar QPushButton:hover {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
}}

#closeButton:hover {{
    background-color: {ERROR_COLOR};
    color: white;
}}

/* ─── Área de chat ────────────────────────────── */
#chatArea {{
    background-color: {BG_PRIMARY};
    border: none;
    padding: 12px;
}}

#chatScroll {{
    background-color: {BG_PRIMARY};
    border: none;
}}

QScrollBar:vertical {{
    background: {BG_SECONDARY};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {ACCENT_DIM};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ─── Mensajes ────────────────────────────────── */
.userMessage {{
    background-color: rgba(0, 212, 255, 0.08);
    border-left: 3px solid {ACCENT};
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 6px 40px 6px 12px;
    color: {TEXT_PRIMARY};
}}

.assistantMessage {{
    background-color: rgba(15, 17, 24, 0.9);
    border-left: 3px solid {ACCENT_DIM};
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 6px 12px 6px 40px;
    color: {TEXT_PRIMARY};
}}

#messageLabel {{
    line-height: 1.5;
    font-size: 13px;
}}

#messageSender {{
    font-weight: bold;
    font-size: 11px;
    margin-bottom: 4px;
}}

/* ─── Barra de input ──────────────────────────── */
#inputBar {{
    background-color: {BG_SECONDARY};
    border-top: 1px solid {BORDER_COLOR};
    padding: 8px 12px;
}}

#inputField {{
    background-color: {BG_TERTIARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 20px;
    padding: 10px 16px;
    color: {TEXT_PRIMARY};
    font-size: 14px;
    selection-background-color: {ACCENT_DIM};
}}

#inputField:focus {{
    border: 1px solid {ACCENT};
}}

#inputField::placeholder {{
    color: {TEXT_SECONDARY};
}}

/* ─── Botones ─────────────────────────────────── */
#micButton {{
    background-color: {BG_TERTIARY};
    border: 2px solid {ACCENT_DIM};
    border-radius: 22px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    font-size: 18px;
    color: {ACCENT};
}}

#micButton:hover {{
    background-color: rgba(0, 212, 255, 0.15);
    border-color: {ACCENT};
}}

#micButton:pressed,
#micButton[recording="true"] {{
    background-color: rgba(255, 68, 68, 0.2);
    border-color: {ERROR_COLOR};
    color: {ERROR_COLOR};
}}

#sendButton {{
    background-color: {ACCENT};
    border: none;
    border-radius: 22px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    font-size: 16px;
    color: {BG_PRIMARY};
    font-weight: bold;
}}

#sendButton:hover {{
    background-color: {ACCENT_GLOW};
}}

#sendButton:pressed {{
    background-color: {ACCENT_DIM};
}}

#sendButton:disabled {{
    background-color: {BG_TERTIARY};
    color: {TEXT_SECONDARY};
}}

/* ─── Barra de estado / métricas ──────────────── */
#statusBar {{
    background-color: {BG_SECONDARY};
    border-top: 1px solid {BORDER_COLOR};
    padding: 4px 12px;
    min-height: 28px;
}}

#statusLabel {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: normal;
}}

#metricValue {{
    color: {ACCENT};
    font-weight: bold;
    font-size: 11px;
}}

#statusIndicator {{
    border-radius: 5px;
    min-width: 10px;
    max-width: 10px;
    min-height: 10px;
    max-height: 10px;
}}

/* ─── Indicadores de estado ───────────────────── */
#stateIdle {{
    background-color: {ACCENT_DIM};
}}

#stateListening {{
    background-color: #4488FF;
}}

#stateProcessing {{
    background-color: {WARNING_COLOR};
}}

#stateSpeaking {{
    background-color: {SUCCESS_COLOR};
}}

#stateError {{
    background-color: {ERROR_COLOR};
}}

/* ─── Menú contextual ─────────────────────────── */
QMenu {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px;
    border-radius: 4px;
    color: {TEXT_PRIMARY};
}}

QMenu::item:selected {{
    background-color: rgba(0, 212, 255, 0.15);
    color: {ACCENT};
}}

/* ─── Tooltips ────────────────────────────────── */
QToolTip {{
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT_DIM};
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
}}

/* ─── Checkbox / Settings ─────────────────────── */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {ACCENT_DIM};
    border-radius: 4px;
    background-color: {BG_TERTIARY};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
"""

# ─── Animaciones CSS adicionales ──────────────────────────────

GLOW_ANIMATION_CSS = f"""
@keyframes glow {{
    0% {{ border-color: {ACCENT_DIM}; }}
    50% {{ border-color: {ACCENT_GLOW}; }}
    100% {{ border-color: {ACCENT_DIM}; }}
}}
"""
