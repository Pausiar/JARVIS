"""
J.A.R.V.I.S. — Notifications Module
Notificaciones proactivas de Windows.
Monitoriza CPU, RAM, batería, disco y avisa al usuario.
Usa toast notifications nativas de Windows 10/11.
"""

import logging
import os
import subprocess
import threading
import time
from typing import Callable, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("jarvis.notifications")

# ─── Helper: ocultar consolas en subprocess (.pyw) ────────
_STARTUPINFO = None
_CREATION_FLAGS = 0
if os.name == 'nt':
    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _STARTUPINFO.wShowWindow = 0
    _CREATION_FLAGS = subprocess.CREATE_NO_WINDOW

# Umbrales por defecto
DEFAULT_THRESHOLDS = {
    "cpu_percent": 90,          # Avisar si CPU > 90%
    "ram_percent": 85,          # Avisar si RAM > 85%
    "disk_percent": 90,         # Avisar si disco > 90%
    "battery_low": 15,          # Avisar si batería < 15%
    "battery_critical": 5,      # Avisar urgente si batería < 5%
    "check_interval": 60,       # Verificar cada 60 segundos
    "cooldown": 300,            # No repetir la misma alerta en 5 minutos
}


class NotificationManager:
    """Monitoriza el sistema y envía notificaciones proactivas."""

    def __init__(self, thresholds: dict = None):
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_alerts: dict[str, float] = {}  # timestamp de última alerta por tipo
        self._on_notification: Optional[Callable[[str, str], None]] = None
        self._enabled = True
        logger.info("NotificationManager inicializado.")

    # ─── Control del monitor ──────────────────────────────────

    def start(self, callback: Callable[[str, str], None] = None) -> str:
        """
        Inicia el monitoreo proactivo del sistema.

        Args:
            callback: Función a llamar cuando hay una alerta.
                      Recibe (título, mensaje).
        """
        if self._running:
            return "El monitoreo ya está activo."

        self._on_notification = callback
        self._running = True
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._thread.start()
        logger.info("Monitoreo proactivo iniciado.")
        return "Monitoreo proactivo del sistema activado."

    def stop(self) -> str:
        """Detiene el monitoreo proactivo."""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Monitoreo proactivo detenido.")
        return "Monitoreo proactivo desactivado."

    def toggle(self) -> str:
        """Activa/desactiva las notificaciones."""
        self._enabled = not self._enabled
        state = "activadas" if self._enabled else "desactivadas"
        return f"Notificaciones proactivas {state}."

    # ─── Configuración de umbrales ────────────────────────────

    def set_threshold(self, metric: str, value: int) -> str:
        """Cambia el umbral de una métrica."""
        if metric not in self.thresholds:
            valid = ", ".join(self.thresholds.keys())
            return f"Métrica desconocida. Válidas: {valid}"
        self.thresholds[metric] = value
        return f"Umbral de '{metric}' establecido a {value}."

    def get_thresholds(self) -> str:
        """Muestra los umbrales configurados."""
        lines = ["⚠️ Umbrales de notificación:\n"]
        labels = {
            "cpu_percent": "CPU máxima",
            "ram_percent": "RAM máxima",
            "disk_percent": "Disco máximo",
            "battery_low": "Batería baja",
            "battery_critical": "Batería crítica",
            "check_interval": "Intervalo de chequeo (s)",
            "cooldown": "Cooldown entre alertas (s)",
        }
        for key, value in self.thresholds.items():
            label = labels.get(key, key)
            lines.append(f"  • {label}: {value}")
        return "\n".join(lines)

    # ─── Bucle de monitoreo ───────────────────────────────────

    def _monitor_loop(self) -> None:
        """Bucle principal de monitoreo."""
        try:
            import psutil
        except ImportError:
            logger.error("psutil no disponible para monitoreo.")
            return

        while self._running and not self._stop_event.is_set():
            if self._enabled:
                self._check_system(psutil)

            self._stop_event.wait(timeout=self.thresholds["check_interval"])

    def _check_system(self, psutil) -> None:
        """Verifica todas las métricas del sistema."""
        now = time.time()
        cooldown = self.thresholds["cooldown"]

        # 1. CPU
        try:
            cpu = psutil.cpu_percent(interval=2)
            if cpu > self.thresholds["cpu_percent"]:
                if self._can_alert("cpu", now, cooldown):
                    self._send_alert(
                        "⚠️ CPU Alta",
                        f"El uso de CPU está al {cpu:.0f}%, señor. "
                        f"Puede que algún proceso esté consumiendo demasiados recursos.",
                    )
        except Exception as e:
            logger.debug(f"Error monitorizando CPU: {e}")

        # 2. RAM
        try:
            ram = psutil.virtual_memory()
            if ram.percent > self.thresholds["ram_percent"]:
                if self._can_alert("ram", now, cooldown):
                    used_gb = ram.used / (1024**3)
                    total_gb = ram.total / (1024**3)
                    self._send_alert(
                        "⚠️ RAM Alta",
                        f"Uso de RAM al {ram.percent:.0f}% "
                        f"({used_gb:.1f} GB / {total_gb:.1f} GB). "
                        f"Considere cerrar aplicaciones no esenciales.",
                    )
        except Exception as e:
            logger.debug(f"Error monitorizando RAM: {e}")

        # 3. Disco
        try:
            disk = psutil.disk_usage("C:\\")
            if disk.percent > self.thresholds["disk_percent"]:
                if self._can_alert("disk", now, cooldown):
                    free_gb = disk.free / (1024**3)
                    self._send_alert(
                        "⚠️ Disco Casi Lleno",
                        f"El disco C: está al {disk.percent:.0f}% de capacidad. "
                        f"Solo quedan {free_gb:.1f} GB libres.",
                    )
        except Exception as e:
            logger.debug(f"Error monitorizando disco: {e}")

        # 4. Batería
        try:
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged:
                percent = battery.percent

                if percent <= self.thresholds["battery_critical"]:
                    if self._can_alert("battery_critical", now, cooldown // 2):
                        self._send_alert(
                            "🔴 Batería Crítica",
                            f"¡Batería al {percent}%! Conecte el cargador inmediatamente.",
                        )
                elif percent <= self.thresholds["battery_low"]:
                    if self._can_alert("battery_low", now, cooldown):
                        secs = battery.secsleft
                        if secs > 0:
                            mins = secs // 60
                            time_str = f" (~{mins} minutos restantes)"
                        else:
                            time_str = ""
                        self._send_alert(
                            "🟡 Batería Baja",
                            f"Batería al {percent}%{time_str}. "
                            f"Recomiendo conectar el cargador pronto.",
                        )
        except Exception as e:
            logger.debug(f"Error monitorizando batería: {e}")

    def _can_alert(self, alert_type: str, now: float, cooldown: float) -> bool:
        """Verifica si se puede enviar una alerta (respeta cooldown)."""
        last = self._last_alerts.get(alert_type, 0)
        if now - last >= cooldown:
            self._last_alerts[alert_type] = now
            return True
        return False

    def _send_alert(self, title: str, message: str) -> None:
        """Envía una notificación al usuario."""
        logger.warning(f"Alerta: {title} — {message}")

        # 1. Callback al HUD (si está configurado)
        if self._on_notification:
            try:
                self._on_notification(title, message)
            except Exception as e:
                logger.debug(f"Error en callback de notificación: {e}")

        # 2. Toast notification de Windows (nativa)
        self._send_windows_toast(title, message)

    def _send_windows_toast(self, title: str, message: str) -> None:
        """Envía un toast notification nativo de Windows 10/11."""
        try:
            import subprocess
            # PowerShell para toast notification
            escaped_title = title.replace("'", "''").replace('"', '`"')
            escaped_msg = message.replace("'", "''").replace('"', '`"')

            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

            $template = @"
            <toast>
                <visual>
                    <binding template="ToastGeneric">
                        <text>J.A.R.V.I.S. — {escaped_title}</text>
                        <text>{escaped_msg}</text>
                    </binding>
                </visual>
                <audio src="ms-winsoundevent:Notification.Default"/>
            </toast>
"@

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("JARVIS")
            $notifier.Show($toast)
            '''
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=10,
                startupinfo=_STARTUPINFO, creationflags=_CREATION_FLAGS,
            )
        except Exception as e:
            logger.debug(f"Error enviando toast: {e}")
            # Fallback: usar BalloonTip del system tray
            try:
                self._send_balloon_tip(title, message)
            except Exception:
                pass

    def _send_balloon_tip(self, title: str, message: str) -> None:
        """Fallback: BalloonTip (más compatible)."""
        try:
            import subprocess
            ps = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $notify = New-Object System.Windows.Forms.NotifyIcon
            $notify.Icon = [System.Drawing.SystemIcons]::Information
            $notify.BalloonTipTitle = "J.A.R.V.I.S. — {title.replace('"', '`"')}"
            $notify.BalloonTipText = "{message.replace('"', '`"')}"
            $notify.Visible = $true
            $notify.ShowBalloonTip(5000)
            Start-Sleep -Seconds 6
            $notify.Dispose()
            '''
            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=_STARTUPINFO, creationflags=_CREATION_FLAGS,
            )
        except Exception as e:
            logger.debug(f"Error en balloon tip: {e}")

    # ─── Notificación manual ──────────────────────────────────

    def notify(self, title: str, message: str) -> str:
        """Envía una notificación manual al usuario."""
        self._send_alert(title, message)
        return f"Notificación enviada: {title}"

    def cleanup(self) -> None:
        """Limpieza al cerrar JARVIS."""
        self.stop()
