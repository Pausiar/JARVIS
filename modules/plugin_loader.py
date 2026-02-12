"""
J.A.R.V.I.S. — Plugin Loader
Sistema de plugins: carga automática de módulos desde la carpeta plugins/.
Cada plugin es un archivo .py que registra funciones nuevas sin tocar el core.
Soporta hot-reload (recarga en caliente).
"""

import importlib
import importlib.util
import logging
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import BASE_DIR

logger = logging.getLogger("jarvis.plugins")

PLUGINS_DIR = BASE_DIR / "plugins"
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


class PluginInfo:
    """Metadatos de un plugin cargado."""

    def __init__(self, name: str, module, file_path: str):
        self.name = name
        self.module = module
        self.file_path = file_path
        self.load_time = time.time()
        self.mtime = os.path.getmtime(file_path)
        self.commands: dict[str, Callable] = {}
        self.description: str = ""
        self.version: str = "1.0"
        self.author: str = ""

    def __repr__(self):
        return f"Plugin({self.name}, commands={list(self.commands.keys())})"


class PluginLoader:
    """
    Carga y gestiona plugins de la carpeta plugins/.

    Cada plugin debe tener:
    - Una función `register(registry)` que recibe un dict y registra sus comandos.
    - Opcionalmente: PLUGIN_NAME, PLUGIN_DESCRIPTION, PLUGIN_VERSION, PLUGIN_AUTHOR.

    Ejemplo de plugin (plugins/saludo.py):
        PLUGIN_NAME = "Saludo"
        PLUGIN_DESCRIPTION = "Responde saludos personalizados"

        def saludar(nombre: str = "señor") -> str:
            return f"¡Hola, {nombre}! ¿En qué puedo ayudarte?"

        def register(registry: dict):
            registry["saludar"] = saludar
    """

    def __init__(self):
        self.plugins: dict[str, PluginInfo] = {}
        self.commands: dict[str, Callable] = {}
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        logger.info(f"PluginLoader inicializado. Directorio: {PLUGINS_DIR}")

    def load_all(self) -> list[str]:
        """
        Carga todos los plugins del directorio plugins/.
        Returns: Lista de nombres de plugins cargados.
        """
        loaded = []
        if not PLUGINS_DIR.exists():
            PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
            self._create_example_plugin()
            return loaded

        for file_path in sorted(PLUGINS_DIR.glob("*.py")):
            if file_path.name.startswith("_"):
                continue
            name = file_path.stem
            try:
                self._load_plugin(name, str(file_path))
                loaded.append(name)
            except Exception as e:
                logger.error(f"Error cargando plugin '{name}': {e}")

        logger.info(f"Plugins cargados: {loaded}")
        return loaded

    def _load_plugin(self, name: str, file_path: str) -> None:
        """Carga un plugin específico por nombre y ruta."""
        spec = importlib.util.spec_from_file_location(
            f"jarvis_plugin_{name}", file_path
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"No se pudo cargar spec para {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        info = PluginInfo(name, module, file_path)
        info.description = getattr(module, "PLUGIN_DESCRIPTION", "")
        info.version = getattr(module, "PLUGIN_VERSION", "1.0")
        info.author = getattr(module, "PLUGIN_AUTHOR", "")

        plugin_name = getattr(module, "PLUGIN_NAME", name)
        info.name = plugin_name

        # Registrar comandos
        if hasattr(module, "register"):
            registry = {}
            module.register(registry)
            info.commands = registry
            for cmd_name, cmd_func in registry.items():
                full_name = f"plugin.{name}.{cmd_name}"
                self.commands[full_name] = cmd_func
                # Registrar también con nombre corto si no hay conflicto
                if cmd_name not in self.commands:
                    self.commands[cmd_name] = cmd_func
        else:
            # Auto-registrar funciones públicas que no empiecen con _
            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(module, attr_name)
                if callable(attr) and attr_name not in (
                    "PLUGIN_NAME", "PLUGIN_DESCRIPTION",
                    "PLUGIN_VERSION", "PLUGIN_AUTHOR",
                ):
                    info.commands[attr_name] = attr
                    full_name = f"plugin.{name}.{attr_name}"
                    self.commands[full_name] = attr
                    if attr_name not in self.commands:
                        self.commands[attr_name] = attr

        self.plugins[name] = info
        logger.info(
            f"Plugin cargado: '{plugin_name}' v{info.version} "
            f"({len(info.commands)} comandos)"
        )

    def reload_plugin(self, name: str) -> str:
        """Recarga un plugin (hot-reload)."""
        if name not in self.plugins:
            return f"Plugin '{name}' no encontrado."

        info = self.plugins[name]
        file_path = info.file_path

        # Limpiar comandos antiguos
        for cmd_name in info.commands:
            full_name = f"plugin.{name}.{cmd_name}"
            self.commands.pop(full_name, None)
            if cmd_name in self.commands:
                # Solo eliminar si es de este plugin
                if self.commands.get(cmd_name) in info.commands.values():
                    del self.commands[cmd_name]

        del self.plugins[name]

        try:
            self._load_plugin(name, file_path)
            return f"Plugin '{name}' recargado correctamente."
        except Exception as e:
            logger.error(f"Error recargando plugin '{name}': {e}")
            return f"Error recargando plugin '{name}': {e}"

    def reload_all(self) -> str:
        """Recarga todos los plugins."""
        # Limpiar todo
        self.plugins.clear()
        self.commands.clear()
        loaded = self.load_all()
        return f"Plugins recargados: {', '.join(loaded) if loaded else 'ninguno'}"

    def unload_plugin(self, name: str) -> str:
        """Descarga un plugin."""
        if name not in self.plugins:
            return f"Plugin '{name}' no encontrado."

        info = self.plugins[name]
        for cmd_name in info.commands:
            full_name = f"plugin.{name}.{cmd_name}"
            self.commands.pop(full_name, None)
            if cmd_name in self.commands:
                if self.commands.get(cmd_name) in info.commands.values():
                    del self.commands[cmd_name]

        del self.plugins[name]
        logger.info(f"Plugin '{name}' descargado.")
        return f"Plugin '{name}' descargado."

    def execute_command(self, command_name: str, **kwargs) -> str:
        """Ejecuta un comando de plugin."""
        func = self.commands.get(command_name)
        if not func:
            return f"Comando de plugin '{command_name}' no encontrado."
        try:
            result = func(**kwargs)
            return str(result) if result is not None else "Comando ejecutado."
        except Exception as e:
            logger.error(f"Error ejecutando comando '{command_name}': {e}")
            return f"Error: {e}"

    def list_plugins(self) -> str:
        """Lista todos los plugins cargados."""
        if not self.plugins:
            return "No hay plugins cargados. Coloca archivos .py en la carpeta plugins/."

        lines = ["🔌 Plugins cargados:\n"]
        for name, info in self.plugins.items():
            desc = info.description or "Sin descripción"
            cmds = ", ".join(info.commands.keys()) or "ninguno"
            lines.append(
                f"  • {info.name} v{info.version}: {desc}\n"
                f"    Comandos: {cmds}"
            )
        return "\n".join(lines)

    def list_commands(self) -> str:
        """Lista todos los comandos disponibles de plugins."""
        if not self.commands:
            return "No hay comandos de plugins disponibles."

        lines = ["🔌 Comandos de plugins:\n"]
        for cmd_name, func in sorted(self.commands.items()):
            if "." in cmd_name:
                continue  # Mostrar solo nombres cortos
            doc = (func.__doc__ or "").strip().split("\n")[0]
            lines.append(f"  • {cmd_name}: {doc}")
        return "\n".join(lines)

    # ─── Hot-reload (vigilar cambios) ─────────────────────────

    def start_watching(self) -> None:
        """Inicia la vigilancia de cambios en plugins/ para hot-reload."""
        if self._watch_thread and self._watch_thread.is_alive():
            return

        self._stop_event.clear()
        self._watch_thread = threading.Thread(
            target=self._watch_loop, daemon=True
        )
        self._watch_thread.start()
        logger.info("Hot-reload de plugins activado.")

    def stop_watching(self) -> None:
        """Detiene la vigilancia de cambios."""
        self._stop_event.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=3)
        logger.info("Hot-reload de plugins desactivado.")

    def _watch_loop(self) -> None:
        """Bucle que vigila cambios en archivos de plugins."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=3.0)
            if self._stop_event.is_set():
                break

            for file_path in PLUGINS_DIR.glob("*.py"):
                if file_path.name.startswith("_"):
                    continue

                name = file_path.stem
                current_mtime = os.path.getmtime(str(file_path))

                if name in self.plugins:
                    if current_mtime > self.plugins[name].mtime:
                        logger.info(f"Cambio detectado en plugin '{name}', recargando...")
                        self.reload_plugin(name)
                else:
                    # Nuevo plugin
                    logger.info(f"Nuevo plugin detectado: '{name}', cargando...")
                    try:
                        self._load_plugin(name, str(file_path))
                    except Exception as e:
                        logger.error(f"Error cargando nuevo plugin '{name}': {e}")

    def _create_example_plugin(self) -> None:
        """Crea un plugin de ejemplo en la carpeta plugins/."""
        example_path = PLUGINS_DIR / "example_plugin.py"
        if example_path.exists():
            return

        example_code = '''"""
Plugin de ejemplo para J.A.R.V.I.S.
Muestra cómo crear un plugin personalizado.
"""

PLUGIN_NAME = "Ejemplo"
PLUGIN_DESCRIPTION = "Plugin de ejemplo — muestra la estructura básica"
PLUGIN_VERSION = "1.0"
PLUGIN_AUTHOR = "JARVIS"


def saludar_personalizado(nombre: str = "señor") -> str:
    """Saluda de forma personalizada."""
    return f"¡Un placer conocerle, {nombre}!"


def dado(caras: int = 6) -> str:
    """Lanza un dado virtual."""
    import random
    resultado = random.randint(1, caras)
    return f"🎲 Resultado del dado (d{caras}): {resultado}"


def chiste() -> str:
    """Cuenta un chiste aleatorio."""
    import random
    chistes = [
        "¿Por qué los programadores prefieren el frío? Porque tienen muchos bugs en verano.",
        "Hay 10 tipos de personas: las que entienden binario y las que no.",
        "¿Cuál es el animal más antiguo? La cebra, porque está en blanco y negro.",
        "- ¿Qué hace un if en la calle? - Espera su else.",
    ]
    return random.choice(chistes)


def register(registry: dict):
    """Registra los comandos del plugin."""
    registry["saludar_personalizado"] = saludar_personalizado
    registry["dado"] = dado
    registry["chiste"] = chiste
'''
        example_path.write_text(example_code, encoding="utf-8")
        logger.info("Plugin de ejemplo creado.")

    def cleanup(self) -> None:
        """Limpieza al cerrar JARVIS."""
        self.stop_watching()
