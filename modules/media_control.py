"""
J.A.R.V.I.S. — Media Control Module
Control multimedia avanzado: play/pause, skip, volumen por app,
detección de Spotify, control de YouTube en navegador.
"""

import logging
import subprocess
import time
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("jarvis.media")


class MediaControl:
    """Control multimedia avanzado para Windows."""

    def __init__(self):
        logger.info("MediaControl inicializado.")

    # ─── Controles globales de media ──────────────────────────

    def play_pause(self) -> str:
        """Reproduce o pausa la media actual (cualquier reproductor)."""
        import pyautogui
        try:
            pyautogui.press("playpause")
            return "Reproducción/pausa alternada."
        except Exception as e:
            return f"Error: {e}"

    def next_track(self) -> str:
        """Pasa a la siguiente canción/track."""
        import pyautogui
        try:
            pyautogui.press("nexttrack")
            return "Siguiente pista."
        except Exception as e:
            return f"Error: {e}"

    def previous_track(self) -> str:
        """Pasa a la canción/track anterior."""
        import pyautogui
        try:
            pyautogui.press("prevtrack")
            return "Pista anterior."
        except Exception as e:
            return f"Error: {e}"

    def stop_media(self) -> str:
        """Detiene la reproducción."""
        import pyautogui
        try:
            pyautogui.press("stop")
            return "Reproducción detenida."
        except Exception as e:
            return f"Error: {e}"

    # ─── Spotify ──────────────────────────────────────────────

    def spotify_play_pause(self) -> str:
        """Play/pause en Spotify."""
        return self._spotify_action("playpause")

    def spotify_next(self) -> str:
        """Siguiente canción en Spotify."""
        return self._spotify_action("nexttrack")

    def spotify_previous(self) -> str:
        """Canción anterior en Spotify."""
        return self._spotify_action("prevtrack")

    def spotify_now_playing(self) -> str:
        """Obtiene la canción que está sonando en Spotify."""
        try:
            ps_script = '''
            $spotify = Get-Process -Name "Spotify" -ErrorAction SilentlyContinue |
                Where-Object { $_.MainWindowTitle -ne "" }
            if ($spotify) {
                $title = $spotify.MainWindowTitle
                if ($title -eq "Spotify" -or $title -eq "Spotify Free" -or $title -eq "Spotify Premium") {
                    Write-Output "PAUSED"
                } else {
                    Write-Output "PLAYING:$title"
                }
            } else {
                Write-Output "NOT_RUNNING"
            }
            '''
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=5,
            )
            output = result.stdout.strip()

            if output == "NOT_RUNNING":
                return "Spotify no está abierto."
            elif output == "PAUSED":
                return "Spotify está en pausa."
            elif output.startswith("PLAYING:"):
                title = output.split("PLAYING:", 1)[1]
                return f"🎵 Sonando en Spotify: {title}"
            return "No se pudo obtener la información de Spotify."
        except Exception as e:
            return f"Error: {e}"

    def _spotify_action(self, key: str) -> str:
        """Ejecuta una acción de media enfocando Spotify primero."""
        import pyautogui
        try:
            # Verificar si Spotify está corriendo
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-Process -Name Spotify -ErrorAction SilentlyContinue | "
                 "Select-Object -First 1 -ExpandProperty Id"],
                capture_output=True, text=True, timeout=5,
            )
            if not result.stdout.strip():
                return "Spotify no está abierto."

            # Usar las teclas de media (funcionan globalmente con Spotify)
            pyautogui.press(key)
            actions = {
                "playpause": "Play/Pause",
                "nexttrack": "Siguiente",
                "prevtrack": "Anterior",
            }
            return f"Spotify: {actions.get(key, key)}"
        except Exception as e:
            return f"Error controlando Spotify: {e}"

    # ─── YouTube (navegador) ──────────────────────────────────

    def youtube_play_pause(self) -> str:
        """Play/pause en YouTube (navegador activo)."""
        import pyautogui
        try:
            # YouTube usa la tecla K para play/pause
            pyautogui.press("k")
            return "YouTube: play/pause."
        except Exception as e:
            return f"Error: {e}"

    def youtube_next(self) -> str:
        """Siguiente video en YouTube."""
        import pyautogui
        try:
            pyautogui.hotkey("shift", "n")
            return "YouTube: siguiente video."
        except Exception as e:
            return f"Error: {e}"

    def youtube_fullscreen(self) -> str:
        """Pantalla completa en YouTube."""
        import pyautogui
        try:
            pyautogui.press("f")
            return "YouTube: pantalla completa."
        except Exception as e:
            return f"Error: {e}"

    def youtube_mute(self) -> str:
        """Silenciar YouTube."""
        import pyautogui
        try:
            pyautogui.press("m")
            return "YouTube: silenciado/activado."
        except Exception as e:
            return f"Error: {e}"

    def youtube_forward(self, seconds: int = 10) -> str:
        """Avanzar en el video de YouTube."""
        import pyautogui
        try:
            # L avanza 10 segundos, flechas 5 segundos
            if seconds >= 10:
                for _ in range(seconds // 10):
                    pyautogui.press("l")
            else:
                for _ in range(seconds // 5):
                    pyautogui.press("right")
            return f"YouTube: avanzado {seconds}s."
        except Exception as e:
            return f"Error: {e}"

    def youtube_rewind(self, seconds: int = 10) -> str:
        """Retroceder en el video de YouTube."""
        import pyautogui
        try:
            if seconds >= 10:
                for _ in range(seconds // 10):
                    pyautogui.press("j")
            else:
                for _ in range(seconds // 5):
                    pyautogui.press("left")
            return f"YouTube: retrocedido {seconds}s."
        except Exception as e:
            return f"Error: {e}"

    # ─── Volumen por aplicación ───────────────────────────────

    def get_app_volumes(self) -> str:
        """Muestra el volumen de cada aplicación."""
        try:
            from pycaw.pycaw import AudioUtilities

            sessions = AudioUtilities.GetAllSessions()
            lines = ["🔊 Volumen por aplicación:\n"]

            for session in sessions:
                if session.Process:
                    vol = session.SimpleAudioVolume
                    level = int(vol.GetMasterVolume() * 100)
                    muted = "🔇" if vol.GetMute() else "🔊"
                    lines.append(
                        f"  {muted} {session.Process.name()}: {level}%"
                    )

            return "\n".join(lines) if len(lines) > 1 else "No hay apps reproduciendo audio."
        except ImportError:
            return "pycaw no disponible para control de volumen por app."
        except Exception as e:
            return f"Error: {e}"

    def set_app_volume(self, app_name: str, level: int) -> str:
        """Establece el volumen de una aplicación específica."""
        try:
            from pycaw.pycaw import AudioUtilities

            sessions = AudioUtilities.GetAllSessions()
            app_lower = app_name.lower()

            for session in sessions:
                if session.Process:
                    proc_name = session.Process.name().lower()
                    if app_lower in proc_name:
                        vol = session.SimpleAudioVolume
                        vol.SetMasterVolume(max(0.0, min(1.0, level / 100)), None)
                        return f"Volumen de {session.Process.name()} al {level}%."

            return f"No se encontró la aplicación '{app_name}' reproduciendo audio."
        except ImportError:
            return "pycaw no disponible."
        except Exception as e:
            return f"Error: {e}"

    def mute_app(self, app_name: str) -> str:
        """Silencia/activa una aplicación específica."""
        try:
            from pycaw.pycaw import AudioUtilities

            sessions = AudioUtilities.GetAllSessions()
            app_lower = app_name.lower()

            for session in sessions:
                if session.Process:
                    proc_name = session.Process.name().lower()
                    if app_lower in proc_name:
                        vol = session.SimpleAudioVolume
                        is_muted = vol.GetMute()
                        vol.SetMute(not is_muted, None)
                        state = "silenciada" if not is_muted else "activada"
                        return f"{session.Process.name()} {state}."

            return f"No se encontró '{app_name}' reproduciendo audio."
        except ImportError:
            return "pycaw no disponible."
        except Exception as e:
            return f"Error: {e}"

    # ─── Detección de lo que suena ────────────────────────────

    def what_is_playing(self) -> str:
        """Detecta qué está reproduciendo audio actualmente."""
        parts = []

        # Spotify
        spotify_info = self.spotify_now_playing()
        if "Sonando" in spotify_info:
            parts.append(spotify_info)

        # Otras apps reproduciendo audio
        try:
            from pycaw.pycaw import AudioUtilities

            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process:
                    vol = session.SimpleAudioVolume
                    if vol.GetMasterVolume() > 0 and not vol.GetMute():
                        name = session.Process.name()
                        if name.lower() not in ("spotify.exe",):
                            parts.append(f"  🔊 {name}")
        except Exception:
            pass

        if parts:
            return "Reproduciendo actualmente:\n" + "\n".join(parts)
        return "No parece haber nada reproduciendo audio."
