"""
J.A.R.V.I.S. — Punto de Entrada Principal
Just A Rather Very Intelligent System

Asistente de escritorio IA para Windows 10/11.
100% local, sin APIs externas de pago.
"""

import sys
import logging
import threading
from pathlib import Path

# Asegurar que el directorio raíz está en el PATH
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from config import (
    HOTKEY_ACTIVATE,
    WAKE_WORD,
    HUD_WINDOW_TITLE,
    USER_CONFIG,
    DATA_DIR,
    LOGS_DIR,
)

# ── Configurar logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("jarvis.main")


def initialize_core():
    """Inicializa los componentes core de JARVIS."""
    logger.info("=" * 60)
    logger.info("  J.A.R.V.I.S. — Inicializando...")
    logger.info("  Just A Rather Very Intelligent System")
    logger.info("=" * 60)

    # ── Brain (LLM) ──
    from core.brain import JarvisBrain
    brain = JarvisBrain()

    # Mostrar modo de operación
    if brain.mode == "cloud":
        logger.info(f"  Modo: ☁️ CLOUD ({brain.cloud_provider})")
        if brain._get_cloud_api_key():
            logger.info(f"  API key: ✅ Configurada")
        else:
            logger.warning(f"  API key: ❌ No configurada — configure 'github_token' o 'gemini_api_key' en data/config.json")
    else:
        ollama_available = brain.is_available()
        ollama_status = "✅ Conectado" if ollama_available else "❌ No disponible"
        logger.info(f"  Modo: 💻 LOCAL (Ollama)")
        logger.info(f"  LLM (Ollama): {ollama_status}")

        # Calentar el modelo en background solo en modo local
        if ollama_available:
            import threading
            warmup_thread = threading.Thread(target=brain.warmup, daemon=True)
            warmup_thread.start()
            logger.info("  Modelo cargándose en background.")

    # ── Voice Input (STT) ──
    from core.voice_input import VoiceInput
    voice_input = VoiceInput()

    stt_status = "❌ No disponible"
    try:
        if voice_input.load_model():
            stt_status = "✅ Listo"
    except Exception as e:
        logger.warning(f"  STT no disponible: {e}")
    logger.info(f"  STT (Whisper): {stt_status}")

    # ── Voice Output (TTS) ──
    from core.voice_output import VoiceOutput
    voice_output = VoiceOutput()

    tts_status = "❌ No disponible"
    try:
        if voice_output.initialize():
            tts_status = "✅ Listo"
    except Exception as e:
        logger.warning(f"  TTS no disponible: {e}")
    logger.info(f"  TTS: {tts_status}")

    # ── Orchestrator ──
    from core.orchestrator import Orchestrator
    orchestrator = Orchestrator(brain)
    logger.info("  Orquestador: ✅ Listo")

    # Restaurar historial de conversación de la memoria
    try:
        recent = orchestrator.memory.get_recent_messages(20)
        if recent:
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in recent
            ]
            brain.set_history(history)
            logger.info(f"  Historial restaurado: {len(history)} mensajes")
    except Exception as e:
        logger.warning(f"  No se pudo restaurar historial: {e}")

    logger.info("=" * 60)
    logger.info("  JARVIS inicializado correctamente.")
    logger.info("=" * 60)

    return brain, voice_input, voice_output, orchestrator


def setup_hotkeys(hud):
    """Configura los hotkeys globales."""
    try:
        import keyboard

        def on_hotkey():
            """Callback del hotkey de activación."""
            logger.info("Hotkey de activación presionado.")
            # Mostrar la ventana y enfocar el campo de texto
            if hud:
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    hud, "_show_from_tray",
                    Qt.QueuedConnection,
                )

        keyboard.add_hotkey(HOTKEY_ACTIVATE, on_hotkey, suppress=False)
        logger.info(f"Hotkey global registrado: {HOTKEY_ACTIVATE}")

    except ImportError:
        logger.warning(
            "Módulo 'keyboard' no instalado. "
            "Hotkeys globales no disponibles."
        )
    except Exception as e:
        logger.warning(f"Error configurando hotkeys: {e}")


def main():
    """Función principal de JARVIS."""
    # Verificar Python 3.11+
    if sys.version_info < (3, 11):
        print("⚠️  JARVIS requiere Python 3.11 o superior.")
        print(f"   Versión actual: {sys.version}")
        sys.exit(1)

    # Crear directorios necesarios
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Inicializar componentes core
    try:
        brain, voice_input, voice_output, orchestrator = initialize_core()
    except Exception as e:
        logger.critical(f"Error fatal inicializando JARVIS: {e}")
        print(f"❌ Error fatal: {e}")
        sys.exit(1)

    # Iniciar la aplicación Qt
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFont
        from ui.hud import JarvisHUD

        app = QApplication(sys.argv)
        app.setApplicationName(HUD_WINDOW_TITLE)
        app.setOrganizationName("JARVIS")

        # Fuente predeterminada
        font = QFont("JetBrains Mono", 11)
        font.setStyleHint(QFont.Monospace)
        app.setFont(font)

        # Crear y mostrar el HUD
        hud = JarvisHUD(
            orchestrator=orchestrator,
            voice_input=voice_input,
            voice_output=voice_output,
        )
        hud.show()

        # Configurar hotkeys globales
        setup_hotkeys(hud)

        logger.info("JARVIS está listo. Esperando instrucciones...")

        # Ejecutar el loop de la aplicación
        exit_code = app.exec()

        # Limpieza
        logger.info("Cerrando JARVIS...")
        voice_input.stop_wake_word_listener()
        if voice_output:
            voice_output.stop()

        automation = orchestrator.get_module("automation")
        if automation:
            automation.cleanup()

        # Limpiar nuevos módulos
        notifications = orchestrator.get_module("notifications")
        if notifications and hasattr(notifications, 'stop'):
            notifications.stop()

        calendar = orchestrator.get_module("calendar")
        if calendar and hasattr(calendar, 'stop_reminders'):
            calendar.stop_reminders()

        if hasattr(orchestrator, 'plugin_loader') and orchestrator.plugin_loader:
            orchestrator.plugin_loader.cleanup()

        logger.info("JARVIS cerrado correctamente. Hasta pronto, señor.")
        sys.exit(exit_code)

    except ImportError as e:
        logger.error(f"PySide6 no instalado: {e}")
        print("❌ PySide6 no está instalado. Instálalo con: pip install PySide6")
        print("\nIniciando modo solo texto (sin interfaz gráfica)...")
        run_text_mode(orchestrator, voice_input, voice_output)

    except Exception as e:
        logger.critical(f"Error fatal en la aplicación: {e}")
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_text_mode(orchestrator, voice_input=None, voice_output=None):
    """Modo de interacción solo por texto (fallback sin GUI)."""
    print("\n" + "=" * 60)
    print("  J.A.R.V.I.S. — Modo Texto")
    print("  Escriba 'salir' para terminar.")
    print("=" * 60 + "\n")

    print("JARVIS: Buenos días, señor. Estoy operando en modo texto.")
    print("        ¿En qué puedo asistirle?\n")

    while True:
        try:
            user_input = input("Usted: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("salir", "exit", "quit", "adiós", "bye"):
                print("\nJARVIS: Ha sido un placer servirle, señor. Hasta pronto.\n")
                break

            # Procesar con el orquestador
            response = orchestrator.process(user_input)
            print(f"\nJARVIS: {response}\n")

            # TTS si está disponible
            if voice_output and voice_output.enabled:
                voice_output.speak(response)

        except KeyboardInterrupt:
            print("\n\nJARVIS: Entendido, señor. Cerrando. Hasta pronto.\n")
            break
        except Exception as e:
            print(f"\nJARVIS: Me temo que ha ocurrido un error: {e}\n")
            logger.error(f"Error en modo texto: {e}")


if __name__ == "__main__":
    main()
