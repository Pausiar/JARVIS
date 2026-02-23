"""
J.A.R.V.I.S. — Code Executor Module
Generación y ejecución segura de código Python.
"""

import subprocess
import tempfile
import logging
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CODE_EXEC_TIMEOUT, CODE_EXEC_MAX_MEMORY

logger = logging.getLogger("jarvis.code_executor")

# ─── Helper: ocultar consolas en subprocess (.pyw) ────────
_STARTUPINFO = None
_CREATION_FLAGS = 0
if os.name == 'nt':
    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _STARTUPINFO.wShowWindow = 0
    _CREATION_FLAGS = subprocess.CREATE_NO_WINDOW


class CodeExecutor:
    """Genera y ejecuta código Python en un sandbox seguro."""

    def __init__(self):
        self.output_dir = Path.home() / "Desktop" / "JARVIS_code"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("CodeExecutor inicializado.")

    # ─── Ejecución de código ──────────────────────────────────

    def execute_code(self, code: str, timeout: int = None) -> str:
        """
        Ejecuta código Python en un proceso separado (sandbox).

        Args:
            code: Código Python a ejecutar.
            timeout: Timeout en segundos.

        Returns:
            Salida de la ejecución o mensaje de error.
        """
        timeout = timeout or CODE_EXEC_TIMEOUT

        # Verificar seguridad básica
        security_check = self._security_check(code)
        if security_check:
            return f"⚠️ Código bloqueado por seguridad: {security_check}"

        try:
            # Escribir código a archivo temporal
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8',
                dir=str(self.output_dir),
            ) as f:
                f.write(code)
                temp_file = f.name

            # Ejecutar en proceso separado
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.output_dir),
                env=self._safe_env(),
                startupinfo=_STARTUPINFO, creationflags=_CREATION_FLAGS,
            )

            output = ""
            if result.stdout:
                output += f"📤 Salida:\n{result.stdout}"
            if result.stderr:
                output += f"\n⚠️ Errores:\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n❌ Código de salida: {result.returncode}"
            if not output.strip():
                output = "✅ Código ejecutado sin salida."

            logger.info(f"Código ejecutado (exit: {result.returncode})")
            return output

        except subprocess.TimeoutExpired:
            return (
                f"⏱️ La ejecución excedió el tiempo límite ({timeout}s). "
                "El proceso fue terminado."
            )
        except Exception as e:
            logger.error(f"Error ejecutando código: {e}")
            return f"Error al ejecutar el código: {e}"
        finally:
            # Limpiar archivo temporal
            try:
                Path(temp_file).unlink(missing_ok=True)
            except Exception:
                pass

    def execute_file(self, file_path: str, timeout: int = None) -> str:
        """Ejecuta un archivo Python existente."""
        path = Path(file_path)
        if not path.exists():
            return f"Archivo no encontrado: {file_path}"
        if path.suffix != ".py":
            return f"Solo se pueden ejecutar archivos .py (recibido: {path.suffix})"

        try:
            code = path.read_text(encoding="utf-8")
            return self.execute_code(code, timeout)
        except Exception as e:
            return f"Error leyendo archivo: {e}"

    # ─── Generación de código ─────────────────────────────────

    def generate_code(self, description: str) -> str:
        """
        Placeholder para generación de código.
        La generación real la hace el LLM a través del orquestador.

        Returns:
            Mensaje indicando que se debe usar el LLM.
        """
        return (
            f"Para generar código basado en: '{description}', "
            "se requiere el motor de razonamiento (LLM)."
        )

    def save_code(self, code: str, filename: str = None) -> str:
        """Guarda código generado en un archivo."""
        if not filename:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jarvis_code_{timestamp}.py"

        file_path = self.output_dir / filename
        try:
            file_path.write_text(code, encoding="utf-8")
            logger.info(f"Código guardado: {file_path}")
            return f"Código guardado en: {file_path}"
        except Exception as e:
            return f"Error guardando código: {e}"

    def execute_and_save(self, code: str, filename: str = None) -> str:
        """Ejecuta código y lo guarda en un archivo."""
        save_result = self.save_code(code, filename)
        exec_result = self.execute_code(code)
        return f"{save_result}\n\n{exec_result}"

    # ─── Seguridad ────────────────────────────────────────────

    def _security_check(self, code: str) -> Optional[str]:
        """
        Verifica que el código no contenga operaciones peligrosas.

        Returns:
            Mensaje de error si hay riesgo, None si es seguro.
        """
        dangerous_patterns = [
            ("import os\nos.system", "Ejecución de comandos del sistema"),
            ("shutil.rmtree('/'", "Eliminación recursiva del sistema"),
            ("shutil.rmtree('C:\\'", "Eliminación recursiva del disco"),
            ("format(", "Posible formateo"),
            ("__import__('os').system", "Importación oculta de os.system"),
            ("eval(input", "Evaluación de entrada del usuario"),
            ("exec(input", "Ejecución de entrada del usuario"),
            ("subprocess.call(['rm'", "Eliminación de archivos"),
            ("ctypes.windll", "Acceso directo a DLLs de Windows"),
        ]

        code_lower = code.lower()
        for pattern, description in dangerous_patterns:
            if pattern.lower() in code_lower:
                logger.warning(f"Código bloqueado: {description}")
                return description

        # Verificar imports peligrosos específicos
        dangerous_imports = ["ctypes", "winreg"]
        import_lines = [
            line.strip() for line in code.split('\n')
            if line.strip().startswith(('import ', 'from '))
        ]
        for line in import_lines:
            for imp in dangerous_imports:
                if imp in line:
                    return f"Import potencialmente peligroso: {imp}"

        return None

    def _safe_env(self) -> dict:
        """Crea un entorno de variables seguro para la ejecución."""
        import os
        safe = os.environ.copy()
        # No heredar variables sensibles
        for key in ["API_KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL"]:
            for env_key in list(safe.keys()):
                if key in env_key.upper():
                    del safe[env_key]
        return safe
