"""
J.A.R.V.I.S. — Setup Script
Script de instalación y configuración inicial.

Uso: python setup.py
"""

import os
import sys
import json
import shutil
import subprocess
import platform
from pathlib import Path

# ─── Constantes ───────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.resolve()
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
CONFIG_FILE = DATA_DIR / "config.json"
REQUIREMENTS = ROOT_DIR / "requirements.txt"

MIN_PYTHON = (3, 11)

BANNER = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║        ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗           ║
║        ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝           ║
║        ██║███████║██████╔╝██║   ██║██║███████╗           ║
║   ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║           ║
║   ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║           ║
║    ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝           ║
║                                                          ║
║     Just A Rather Very Intelligent System                ║
║     Setup & Configuration                                ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""


def print_step(step: int, total: int, message: str):
    """Imprime un paso del setup con formato."""
    print(f"\n  [{step}/{total}] {message}")
    print("  " + "─" * 50)


def print_ok(message: str):
    print(f"  ✅ {message}")


def print_warn(message: str):
    print(f"  ⚠️  {message}")


def print_error(message: str):
    print(f"  ❌ {message}")


def check_python() -> bool:
    """Paso 1: Verifica la versión de Python."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version >= MIN_PYTHON:
        print_ok(f"Python {version_str} detectado.")
        return True
    else:
        print_error(
            f"Python {version_str} detectado, pero se requiere "
            f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}+."
        )
        return False


def install_dependencies() -> bool:
    """Paso 2: Instala las dependencias del proyecto."""
    if not REQUIREMENTS.exists():
        print_error("requirements.txt no encontrado.")
        return False

    try:
        print("  Instalando dependencias (esto puede tardar unos minutos)...")
        result = subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "-r", str(REQUIREMENTS),
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode == 0:
            print_ok("Dependencias instaladas correctamente.")
            return True
        else:
            print_error(f"Error instalando dependencias:\n{result.stderr}")
            # Intentar instalar una por una
            print("  Intentando instalación individual...")
            return _install_individual()
    except subprocess.TimeoutExpired:
        print_error("Instalación de dependencias excedió el tiempo límite.")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def _install_individual() -> bool:
    """Instala dependencias una por una, ignorando las que fallen."""
    success_count = 0
    fail_count = 0

    with open(REQUIREMENTS, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            pkg_name = line.split(">=")[0].split("==")[0].split("[")[0]
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", line, "--quiet"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    success_count += 1
                else:
                    print_warn(f"No se pudo instalar: {pkg_name}")
                    fail_count += 1
            except Exception:
                print_warn(f"Error instalando: {pkg_name}")
                fail_count += 1

    print_ok(f"Instalados: {success_count} | Fallidos: {fail_count}")
    return success_count > 0


def check_ollama() -> bool:
    """Paso 3: Verifica si Ollama está instalado y corriendo."""
    # Verificar si Ollama está instalado
    ollama_path = shutil.which("ollama")
    if not ollama_path:
        print_warn(
            "Ollama no encontrado en el PATH.\n"
            "  📥 Descárgalo desde: https://ollama.com/download\n"
            "  Una vez instalado, ejecuta: ollama serve"
        )
        return False

    print_ok(f"Ollama encontrado: {ollama_path}")

    # Verificar si está corriendo
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            print_ok(f"Ollama corriendo. Modelos: {model_names or 'ninguno'}")

            # Descargar modelo si no hay ninguno
            if not model_names:
                print("  Descargando modelo 'mistral' (puede tardar varios minutos)...")
                try:
                    subprocess.run(
                        ["ollama", "pull", "mistral"],
                        timeout=1200,
                    )
                    print_ok("Modelo 'mistral' descargado.")
                except subprocess.TimeoutExpired:
                    print_warn("Descarga del modelo cancelada por timeout.")
                except Exception as e:
                    print_warn(f"Error descargando modelo: {e}")

            return True
        else:
            print_warn("Ollama instalado pero no responde. Ejecuta: ollama serve")
            return False
    except ImportError:
        print_warn("requests no instalado. No se puede verificar Ollama.")
        return False
    except Exception:
        print_warn(
            "Ollama instalado pero no está corriendo.\n"
            "  Ejecuta en otra terminal: ollama serve"
        )
        return False


def setup_whisper() -> bool:
    """Paso 4: Verifica el modelo de Whisper para STT."""
    try:
        from faster_whisper import WhisperModel
        print("  Descargando modelo Whisper 'base' (primera vez)...")
        model = WhisperModel("base", device="cpu", compute_type="int8")
        print_ok("Modelo Whisper 'base' disponible.")
        del model
        return True
    except ImportError:
        print_warn(
            "faster-whisper no instalado.\n"
            "  Instálalo con: pip install faster-whisper\n"
            "  STT no estará disponible."
        )
        return False
    except Exception as e:
        print_warn(f"Error con Whisper: {e}")
        return False


def setup_tts() -> bool:
    """Paso 5: Verifica el sistema TTS."""
    # Intentar piper-tts
    try:
        import piper
        print_ok("Piper TTS disponible.")
        return True
    except ImportError:
        pass

    # Intentar pyttsx3 como fallback
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        print_ok(f"pyttsx3 (fallback) disponible. {len(voices)} voces encontradas.")
        del engine
        return True
    except ImportError:
        pass

    print_warn(
        "No se encontró motor TTS.\n"
        "  Opciones:\n"
        "  - pip install piper-tts  (recomendado)\n"
        "  - pip install pyttsx3    (fallback, usa voces del sistema)"
    )

    # Instalar pyttsx3 como fallback
    try:
        print("  Instalando pyttsx3 como fallback...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyttsx3", "--quiet"],
            capture_output=True,
            timeout=60,
        )
        print_ok("pyttsx3 instalado como fallback para TTS.")
        return True
    except Exception:
        return False


def create_directories() -> bool:
    """Paso 6: Crea la estructura de carpetas."""
    dirs = [
        DATA_DIR,
        LOGS_DIR,
        ROOT_DIR / "ui" / "assets" / "fonts",
        ROOT_DIR / "ui" / "assets" / "sounds",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    print_ok("Estructura de carpetas creada.")
    return True


def create_config() -> bool:
    """Paso 7: Genera config.json con valores por defecto."""
    default_config = {
        "user_name": "Señor",
        "language": "es",
        "ollama_model": "mistral",
        "whisper_model": "base",
        "tts_enabled": True,
        "hud_always_on_top": False,
        "hud_opacity": 0.95,
        "wake_word": "jarvis",
        "hotkey_activate": "ctrl+shift+j",
        "email_smtp_server": "smtp.gmail.com",
        "email_smtp_port": 587,
        "favorite_apps": ["chrome", "notepad", "explorer"],
        "frequent_paths": [],
    }

    if CONFIG_FILE.exists():
        print_ok("config.json ya existe. No se sobreescribe.")
    else:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        print_ok("config.json generado con valores por defecto.")

    return True


def run_tests() -> bool:
    """Paso 8: Ejecuta un test rápido."""
    print("  Ejecutando verificación rápida...")

    checks = {
        "Importar config": False,
        "Importar brain": False,
        "Importar modules": False,
        "SQLite (memoria)": False,
    }

    try:
        sys.path.insert(0, str(ROOT_DIR))
        import config
        checks["Importar config"] = True
    except Exception as e:
        print_warn(f"Error en config: {e}")

    try:
        from core.brain import JarvisBrain
        brain = JarvisBrain()
        checks["Importar brain"] = True
    except Exception as e:
        print_warn(f"Error en brain: {e}")

    try:
        from modules.file_manager import FileManager
        from modules.system_control import SystemControl
        from modules.memory import Memory
        checks["Importar modules"] = True
    except Exception as e:
        print_warn(f"Error en modules: {e}")

    try:
        from modules.memory import Memory
        mem = Memory()
        mem.save_message("system", "JARVIS setup completado.")
        msgs = mem.get_recent_messages(1)
        checks["SQLite (memoria)"] = len(msgs) > 0
    except Exception as e:
        print_warn(f"Error en memoria: {e}")

    passed = sum(checks.values())
    total = len(checks)

    for name, ok in checks.items():
        icon = "✅" if ok else "❌"
        print(f"    {icon} {name}")

    if passed == total:
        print_ok(f"Todas las verificaciones pasaron ({passed}/{total}).")
    else:
        print_warn(f"Verificaciones: {passed}/{total} pasaron.")

    return passed >= 2  # Al menos config y brain deben funcionar


def main():
    """Ejecuta el setup completo de JARVIS."""
    print(BANNER)

    total_steps = 8
    results = {}

    # Paso 1: Python
    print_step(1, total_steps, "Verificando Python...")
    results["python"] = check_python()
    if not results["python"]:
        print_error("Python 3.11+ es requerido. Abortando.")
        sys.exit(1)

    # Paso 2: Dependencias
    print_step(2, total_steps, "Instalando dependencias...")
    results["deps"] = install_dependencies()

    # Paso 3: Ollama
    print_step(3, total_steps, "Verificando Ollama (LLM)...")
    results["ollama"] = check_ollama()

    # Paso 4: Whisper (STT)
    print_step(4, total_steps, "Configurando Whisper (STT)...")
    results["whisper"] = setup_whisper()

    # Paso 5: TTS
    print_step(5, total_steps, "Configurando TTS (voz)...")
    results["tts"] = setup_tts()

    # Paso 6: Directorios
    print_step(6, total_steps, "Creando estructura de carpetas...")
    results["dirs"] = create_directories()

    # Paso 7: Config
    print_step(7, total_steps, "Generando configuración...")
    results["config"] = create_config()

    # Paso 8: Tests
    print_step(8, total_steps, "Ejecutando verificación...")
    results["tests"] = run_tests()

    # ── Resumen ──
    print("\n" + "═" * 60)
    print("  📋 RESUMEN DE INSTALACIÓN")
    print("═" * 60)

    for name, ok in results.items():
        icon = "✅" if ok else "⚠️"
        print(f"  {icon} {name}")

    passed = sum(results.values())
    total = len(results)

    if passed == total:
        print(f"\n  🎉 ¡JARVIS instalado correctamente! ({passed}/{total})")
        print("\n  Para iniciar JARVIS:")
        print("    python main.py")
    elif passed >= 4:
        print(f"\n  ⚡ JARVIS parcialmente configurado ({passed}/{total}).")
        print("  Algunos componentes opcionales no están disponibles.")
        print("\n  Para iniciar JARVIS:")
        print("    python main.py")
    else:
        print(f"\n  ⚠️  Configuración incompleta ({passed}/{total}).")
        print("  Revise los errores arriba e intente de nuevo.")

    print("\n  Antes de iniciar, asegúrese de ejecutar:")
    print("    ollama serve")
    print("  en una terminal separada.\n")


if __name__ == "__main__":
    main()
