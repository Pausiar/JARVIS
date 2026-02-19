"""
J.A.R.V.I.S. — Lanzador sin consola
Doble clic en este archivo para iniciar JARVIS directamente.
"""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).parent.resolve()
venv_python = root / ".venv" / "Scripts" / "pythonw.exe"
if not venv_python.exists():
    venv_python = root / "venv" / "Scripts" / "pythonw.exe"
if not venv_python.exists():
    # Fallback: usar python normal (mostrará consola)
    venv_python = root / ".venv" / "Scripts" / "python.exe"

main_py = root / "main.py"
subprocess.Popen([str(venv_python), str(main_py)], cwd=str(root))
