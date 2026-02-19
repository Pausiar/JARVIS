@echo off
title J.A.R.V.I.S.
cd /d "%~dp0"

:: Activar venv y lanzar JARVIS
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py
) else if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe main.py
) else (
    echo [ERROR] No se encontro el entorno virtual.
    echo Ejecuta: python -m venv .venv
    echo Y luego: .venv\Scripts\pip install -r requirements.txt
    pause
)
