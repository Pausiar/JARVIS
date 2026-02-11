"""
J.A.R.V.I.S. — Automation Module
Automatización de tareas y rutinas.
"""

import json
import time
import threading
import logging
import datetime
from pathlib import Path
from typing import Callable, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR

logger = logging.getLogger("jarvis.automation")

ROUTINES_FILE = DATA_DIR / "routines.json"


class AutomationManager:
    """Gestiona rutinas, macros y tareas programadas."""

    def __init__(self):
        self.routines: dict = {}
        self.timers: dict[str, threading.Timer] = {}
        self._running = True
        self._load_routines()
        logger.info("AutomationManager inicializado.")

    # ─── Rutinas ──────────────────────────────────────────────

    def create_routine(self, name: str, steps: list[dict], description: str = "") -> str:
        """
        Crea una nueva rutina (secuencia de comandos).

        Args:
            name: Nombre de la rutina.
            steps: Lista de pasos [{"module": "...", "function": "...", "params": {...}}]
            description: Descripción opcional.

        Returns:
            Mensaje de confirmación.
        """
        self.routines[name] = {
            "name": name,
            "description": description,
            "steps": steps,
            "created": datetime.datetime.now().isoformat(),
            "last_run": None,
            "run_count": 0,
        }
        self._save_routines()
        logger.info(f"Rutina creada: {name} ({len(steps)} pasos)")
        return f"Rutina '{name}' creada con {len(steps)} pasos."

    def execute_routine(self, name: str, executor: Callable = None) -> str:
        """
        Ejecuta una rutina guardada.

        Args:
            name: Nombre de la rutina.
            executor: Función para ejecutar cada paso.

        Returns:
            Resultado de la ejecución.
        """
        if name not in self.routines:
            return f"Rutina '{name}' no encontrada."

        routine = self.routines[name]
        steps = routine["steps"]
        results = []

        logger.info(f"Ejecutando rutina: {name}")

        for i, step in enumerate(steps, 1):
            try:
                if executor:
                    result = executor(step)
                    results.append(f"  Paso {i}: ✅ {result}")
                else:
                    results.append(
                        f"  Paso {i}: {step.get('module')}.{step.get('function')}"
                    )

                # Pausa entre pasos si se especifica
                delay = step.get("delay", 0.5)
                time.sleep(delay)

            except Exception as e:
                results.append(f"  Paso {i}: ❌ Error: {e}")
                logger.error(f"Error en paso {i} de rutina '{name}': {e}")

        # Actualizar estadísticas
        routine["last_run"] = datetime.datetime.now().isoformat()
        routine["run_count"] = routine.get("run_count", 0) + 1
        self._save_routines()

        return f"Rutina '{name}' ejecutada:\n" + "\n".join(results)

    def delete_routine(self, name: str) -> str:
        """Elimina una rutina."""
        if name not in self.routines:
            return f"Rutina '{name}' no encontrada."

        del self.routines[name]
        self._save_routines()
        return f"Rutina '{name}' eliminada."

    def list_routines(self) -> str:
        """Lista todas las rutinas disponibles."""
        if not self.routines:
            return "No hay rutinas creadas, señor."

        lines = ["📋 Rutinas disponibles:\n"]
        for name, routine in self.routines.items():
            steps_count = len(routine["steps"])
            run_count = routine.get("run_count", 0)
            desc = routine.get("description", "Sin descripción")
            lines.append(
                f"  • {name}: {desc} ({steps_count} pasos, ejecutada {run_count} veces)"
            )

        return "\n".join(lines)

    # ─── Temporizadores ───────────────────────────────────────

    def set_timer(
        self,
        name: str,
        seconds: int,
        callback: Callable = None,
        message: str = None,
    ) -> str:
        """
        Programa un temporizador.

        Args:
            name: Nombre del temporizador.
            seconds: Segundos hasta que se active.
            callback: Función a ejecutar cuando termine.
            message: Mensaje a mostrar.
        """
        # Cancelar temporizador existente con mismo nombre
        if name in self.timers:
            self.timers[name].cancel()

        def timer_handler():
            logger.info(f"Temporizador '{name}' activado.")
            if callback:
                callback(message or f"Temporizador '{name}' completado.")
            del self.timers[name]

        timer = threading.Timer(seconds, timer_handler)
        timer.daemon = True
        timer.start()
        self.timers[name] = timer

        # Formatear tiempo
        if seconds >= 3600:
            time_str = f"{seconds // 3600}h {(seconds % 3600) // 60}m"
        elif seconds >= 60:
            time_str = f"{seconds // 60}m {seconds % 60}s"
        else:
            time_str = f"{seconds}s"

        logger.info(f"Temporizador '{name}' configurado: {time_str}")
        return f"Temporizador '{name}' configurado para {time_str}."

    def set_reminder(
        self,
        message: str,
        minutes: int = 0,
        hours: int = 0,
        callback: Callable = None,
    ) -> str:
        """Programa un recordatorio."""
        total_seconds = minutes * 60 + hours * 3600
        if total_seconds <= 0:
            return "Especifique un tiempo válido para el recordatorio."

        name = f"reminder_{int(time.time())}"
        return self.set_timer(name, total_seconds, callback, message)

    def cancel_timer(self, name: str) -> str:
        """Cancela un temporizador activo."""
        if name in self.timers:
            self.timers[name].cancel()
            del self.timers[name]
            return f"Temporizador '{name}' cancelado."
        return f"No se encontró el temporizador '{name}'."

    def list_timers(self) -> str:
        """Lista los temporizadores activos."""
        if not self.timers:
            return "No hay temporizadores activos."

        lines = ["⏱️ Temporizadores activos:\n"]
        for name, timer in self.timers.items():
            remaining = timer.interval - (time.time() - timer.start_time if hasattr(timer, 'start_time') else 0)
            lines.append(f"  • {name}")

        return "\n".join(lines)

    # ─── Tareas programadas ───────────────────────────────────

    def schedule_task(
        self,
        name: str,
        time_str: str,
        command: str,
    ) -> str:
        """
        Programa una tarea para una hora específica usando el Programador
        de Tareas de Windows.

        Args:
            name: Nombre de la tarea.
            time_str: Hora en formato HH:MM.
            command: Comando a ejecutar.
        """
        try:
            import subprocess
            result = subprocess.run(
                [
                    "schtasks", "/create",
                    "/tn", f"JARVIS_{name}",
                    "/tr", command,
                    "/sc", "once",
                    "/st", time_str,
                    "/f",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return f"Tarea '{name}' programada para las {time_str}."
            else:
                return f"Error programando tarea: {result.stderr}"
        except Exception as e:
            return f"Error al programar tarea: {e}"

    # ─── Persistencia ─────────────────────────────────────────

    def _save_routines(self) -> None:
        """Guarda las rutinas en disco."""
        try:
            with open(ROUTINES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.routines, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando rutinas: {e}")

    def _load_routines(self) -> None:
        """Carga las rutinas desde disco."""
        if ROUTINES_FILE.exists():
            try:
                with open(ROUTINES_FILE, 'r', encoding='utf-8') as f:
                    self.routines = json.load(f)
                logger.info(f"Rutinas cargadas: {len(self.routines)}")
            except Exception as e:
                logger.error(f"Error cargando rutinas: {e}")
                self.routines = {}

    def cleanup(self) -> None:
        """Limpia todos los temporizadores."""
        for name, timer in self.timers.items():
            timer.cancel()
        self.timers.clear()
        self._running = False
