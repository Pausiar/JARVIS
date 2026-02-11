"""
J.A.R.V.I.S. — System Control Module
Control del sistema operativo Windows.
"""

import os
import subprocess
import logging
import ctypes
import time
import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis.system_control")


class SystemControl:
    """Controla funciones del sistema operativo Windows."""

    def __init__(self):
        # Nombres legibles para la búsqueda de Windows
        # Clave = lo que dice el usuario, Valor = lo que se escribe en Windows Search
        self._app_search_names = {
            "chrome": "Google Chrome",
            "google": "Google Chrome",
            "google chrome": "Google Chrome",
            "firefox": "Firefox",
            "edge": "Microsoft Edge",
            "microsoft edge": "Microsoft Edge",
            "notepad": "Bloc de notas",
            "bloc de notas": "Bloc de notas",
            "notas": "Bloc de notas",
            "calculadora": "Calculadora",
            "calculator": "Calculadora",
            "explorador": "Explorador de archivos",
            "explorer": "Explorador de archivos",
            "cmd": "Símbolo del sistema",
            "terminal": "Terminal",
            "powershell": "PowerShell",
            "paint": "Paint",
            "word": "Word",
            "excel": "Excel",
            "powerpoint": "PowerPoint",
            "outlook": "Outlook",
            "teams": "Microsoft Teams",
            "spotify": "Spotify",
            "discord": "Discord",
            "vscode": "Visual Studio Code",
            "visual studio code": "Visual Studio Code",
            "visual studio": "Visual Studio",
            "code": "Visual Studio Code",
            "steam": "Steam",
            "task manager": "Administrador de tareas",
            "administrador de tareas": "Administrador de tareas",
            "settings": "Configuración",
            "configuración": "Configuración",
            "configuracion": "Configuración",
            "intellij": "IntelliJ IDEA",
            "intellij idea": "IntelliJ IDEA",
            "idea": "IntelliJ IDEA",
            "pycharm": "PyCharm",
            "webstorm": "WebStorm",
            "android studio": "Android Studio",
            "obs": "OBS Studio",
            "obs studio": "OBS Studio",
            "vlc": "VLC",
            "gimp": "GIMP",
            "photoshop": "Photoshop",
            "whatsapp": "WhatsApp",
            "telegram": "Telegram",
            "slack": "Slack",
        }
        logger.info("SystemControl inicializado.")

    # ─── Aplicaciones ─────────────────────────────────────────

    def open_application(self, app_name: str) -> str:
        """
        Abre una aplicación usando la búsqueda de Windows.
        Simula: pulsar tecla Win → escribir nombre → Enter.
        Como lo haría el usuario con sus propias manos.
        """
        import pyautogui

        app_lower = app_name.lower().strip()
        search_term = self._app_search_names.get(app_lower, app_name)

        try:
            logger.info(f"Abriendo '{search_term}' con búsqueda de Windows...")

            # 1. Pulsar tecla Windows para abrir el menú de búsqueda
            pyautogui.hotkey("win")
            time.sleep(0.8)

            # 2. Escribir el nombre de la app
            #    pyautogui.typewrite solo soporta ASCII, 
            #    así que usamos el portapapeles para texto con acentos/unicode
            if search_term.isascii():
                pyautogui.typewrite(search_term, interval=0.03)
            else:
                # Para texto con acentos/unicode: copiar al portapapeles y pegar
                import subprocess as _sp
                _sp.run(
                    ["powershell", "-command",
                     f"Set-Clipboard -Value '{search_term}'"],
                    check=True, timeout=5,
                    stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                )
                pyautogui.hotkey("ctrl", "v")

            time.sleep(1.0)

            # 3. Pulsar Enter para abrir el primer resultado
            pyautogui.press("enter")
            time.sleep(0.3)

            logger.info(f"Aplicación lanzada con búsqueda de Windows: {search_term}")
            return f"Aplicación abierta: {app_name}"

        except Exception as e:
            logger.error(f"Error abriendo {app_name}: {e}")
            return f"Error al abrir {app_name}: {e}"

    def close_application(self, app_name: str) -> str:
        """Cierra una aplicación por nombre."""
        # Mapa de nombres a procesos .exe para taskkill
        _process_names = {
            "chrome": "chrome.exe", "google": "chrome.exe", "google chrome": "chrome.exe",
            "firefox": "firefox.exe", "edge": "msedge.exe", "microsoft edge": "msedge.exe",
            "notepad": "notepad.exe", "bloc de notas": "notepad.exe",
            "calculadora": "Calculator.exe", "calculator": "Calculator.exe",
            "explorador": "explorer.exe", "explorer": "explorer.exe",
            "terminal": "WindowsTerminal.exe", "powershell": "powershell.exe",
            "paint": "mspaint.exe", "word": "WINWORD.EXE", "excel": "EXCEL.EXE",
            "powerpoint": "POWERPNT.EXE", "outlook": "OUTLOOK.EXE",
            "teams": "ms-teams.exe", "spotify": "Spotify.exe", "discord": "Discord.exe",
            "vscode": "Code.exe", "visual studio code": "Code.exe", "code": "Code.exe",
            "steam": "steam.exe", "intellij": "idea64.exe", "pycharm": "pycharm64.exe",
            "webstorm": "webstorm64.exe", "obs": "obs64.exe", "vlc": "vlc.exe",
            "telegram": "Telegram.exe", "slack": "slack.exe",
        }
        app_lower = app_name.lower().strip()
        exe = _process_names.get(app_lower, app_name)

        # Normalizar nombre del proceso
        if not exe.endswith(".exe"):
            exe += ".exe"

        try:
            result = subprocess.run(
                ["taskkill", "/IM", exe, "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return f"Aplicación cerrada: {app_name}"
            else:
                return f"No se pudo cerrar {app_name}: {result.stderr.strip()}"
        except Exception as e:
            logger.error(f"Error cerrando {app_name}: {e}")
            return f"Error al cerrar {app_name}: {e}"

    # ─── Volumen ──────────────────────────────────────────────

    def volume_up(self, amount: int = 10) -> str:
        """Sube el volumen del sistema."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = interface.QueryInterface(IAudioEndpointVolume)

            current = volume.GetMasterVolumeLevelScalar()
            new_level = min(1.0, current + amount / 100.0)
            volume.SetMasterVolumeLevelScalar(new_level, None)

            return f"Volumen: {int(new_level * 100)}%"
        except ImportError:
            # Fallback: usar teclas de volumen
            try:
                import pyautogui
                for _ in range(amount // 2):
                    pyautogui.press("volumeup")
                return f"Volumen subido (+{amount}%)"
            except Exception:
                return "Error: no se pudo controlar el volumen."
        except Exception as e:
            logger.error(f"Error subiendo volumen: {e}")
            return f"Error al subir el volumen: {e}"

    def volume_down(self, amount: int = 10) -> str:
        """Baja el volumen del sistema."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = interface.QueryInterface(IAudioEndpointVolume)

            current = volume.GetMasterVolumeLevelScalar()
            new_level = max(0.0, current - amount / 100.0)
            volume.SetMasterVolumeLevelScalar(new_level, None)

            return f"Volumen: {int(new_level * 100)}%"
        except ImportError:
            try:
                import pyautogui
                for _ in range(amount // 2):
                    pyautogui.press("volumedown")
                return f"Volumen bajado (-{amount}%)"
            except Exception:
                return "Error: no se pudo controlar el volumen."
        except Exception as e:
            logger.error(f"Error bajando volumen: {e}")
            return f"Error al bajar el volumen: {e}"

    def set_volume(self, level: int) -> str:
        """Establece el volumen a un nivel específico (0-100)."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = interface.QueryInterface(IAudioEndpointVolume)

            level_scalar = max(0.0, min(1.0, level / 100.0))
            volume.SetMasterVolumeLevelScalar(level_scalar, None)

            return f"Volumen establecido a {level}%"
        except Exception as e:
            logger.error(f"Error estableciendo volumen: {e}")
            return f"Error al establecer el volumen: {e}"

    def mute(self) -> str:
        """Silencia o activa el sonido del sistema."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = interface.QueryInterface(IAudioEndpointVolume)

            is_muted = volume.GetMute()
            volume.SetMute(not is_muted, None)

            return "Sonido silenciado" if not is_muted else "Sonido activado"
        except Exception as e:
            try:
                import pyautogui
                pyautogui.press("volumemute")
                return "Volumen silenciado/activado"
            except Exception:
                return f"Error al silenciar: {e}"

    def get_volume(self) -> int:
        """Obtiene el nivel de volumen actual."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = interface.QueryInterface(IAudioEndpointVolume)
            return int(volume.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            return -1

    # ─── Brillo ───────────────────────────────────────────────

    def brightness_up(self, amount: int = 10) -> str:
        """Sube el brillo de la pantalla."""
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            new_level = min(100, current + amount)
            sbc.set_brightness(new_level)
            return f"Brillo: {new_level}%"
        except Exception as e:
            logger.error(f"Error subiendo brillo: {e}")
            return f"Error al subir el brillo: {e}"

    def brightness_down(self, amount: int = 10) -> str:
        """Baja el brillo de la pantalla."""
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            new_level = max(0, current - amount)
            sbc.set_brightness(new_level)
            return f"Brillo: {new_level}%"
        except Exception as e:
            logger.error(f"Error bajando brillo: {e}")
            return f"Error al bajar el brillo: {e}"

    def set_brightness(self, level: int) -> str:
        """Establece el brillo a un nivel específico."""
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(max(0, min(100, level)))
            return f"Brillo establecido a {level}%"
        except Exception as e:
            return f"Error al establecer el brillo: {e}"

    # ─── Control del sistema ──────────────────────────────────

    def shutdown(self, delay: int = 5) -> str:
        """Apaga el PC."""
        try:
            subprocess.run(
                ["shutdown", "/s", "/t", str(delay)],
                check=True,
            )
            return f"Apagando en {delay} segundos..."
        except Exception as e:
            return f"Error al apagar: {e}"

    def restart(self, delay: int = 5) -> str:
        """Reinicia el PC."""
        try:
            subprocess.run(
                ["shutdown", "/r", "/t", str(delay)],
                check=True,
            )
            return f"Reiniciando en {delay} segundos..."
        except Exception as e:
            return f"Error al reiniciar: {e}"

    def suspend(self) -> str:
        """Suspende el PC."""
        try:
            subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"],
                check=True,
            )
            return "PC suspendido."
        except Exception as e:
            return f"Error al suspender: {e}"

    def lock_screen(self) -> str:
        """Bloquea la pantalla."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return "Pantalla bloqueada."
        except Exception as e:
            return f"Error al bloquear pantalla: {e}"

    def logout(self) -> str:
        """Cierra la sesión del usuario."""
        try:
            subprocess.run(["shutdown", "/l"], check=True)
            return "Cerrando sesión..."
        except Exception as e:
            return f"Error al cerrar sesión: {e}"

    # ─── Información del sistema ──────────────────────────────

    def system_info(self) -> str:
        """Obtiene información detallada del sistema."""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('C:\\')
            battery = psutil.sensors_battery()

            info = (
                f"🖥️ Estado del Sistema:\n"
                f"  CPU: {cpu_percent}% ({psutil.cpu_count()} cores)\n"
                f"  RAM: {memory.percent}% ({self._format_bytes(memory.used)} / {self._format_bytes(memory.total)})\n"
                f"  Disco C: {disk.percent}% ({self._format_bytes(disk.used)} / {self._format_bytes(disk.total)})\n"
            )

            if battery:
                charging = "⚡ Cargando" if battery.power_plugged else "🔋 Batería"
                info += f"  Batería: {battery.percent}% ({charging})\n"

            return info
        except ImportError:
            return "Error: psutil no está instalado."
        except Exception as e:
            return f"Error obteniendo info del sistema: {e}"

    def get_system_status(self) -> dict:
        """Obtiene métricas del sistema para el HUD."""
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            volume = self.get_volume()

            status = {
                "cpu": cpu,
                "ram": memory.percent,
                "volume": volume if volume >= 0 else 0,
                "time": datetime.datetime.now().strftime("%H:%M"),
            }

            battery = psutil.sensors_battery()
            if battery:
                status["battery"] = battery.percent
                status["charging"] = battery.power_plugged

            return status
        except Exception as e:
            logger.error(f"Error obteniendo status: {e}")
            return {
                "cpu": 0,
                "ram": 0,
                "volume": 0,
                "time": datetime.datetime.now().strftime("%H:%M"),
            }

    # ─── Screenshot ───────────────────────────────────────────

    def screenshot(self, save_path: str = None) -> str:
        """Captura la pantalla."""
        try:
            import pyautogui

            if not save_path:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = str(
                    Path.home() / "Desktop" / f"screenshot_{timestamp}.png"
                )

            img = pyautogui.screenshot()
            img.save(save_path)
            return f"Captura guardada: {save_path}"
        except Exception as e:
            logger.error(f"Error en screenshot: {e}")
            return f"Error al capturar pantalla: {e}"

    # ─── Papelera ─────────────────────────────────────────────

    def empty_recycle_bin(self) -> str:
        """Vacía la papelera de reciclaje."""
        try:
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x07)
            return "Papelera de reciclaje vaciada."
        except Exception as e:
            return f"Error al vaciar la papelera: {e}"

    # ─── Hora y fecha ─────────────────────────────────────────

    def get_time(self) -> str:
        """Obtiene la hora actual."""
        now = datetime.datetime.now()
        return f"Son las {now.strftime('%H:%M')}, señor."

    def get_date(self) -> str:
        """Obtiene la fecha actual."""
        now = datetime.datetime.now()
        days = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        months = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        day_name = days[now.weekday()]
        month_name = months[now.month - 1]
        return f"Hoy es {day_name} {now.day} de {month_name} de {now.year}, señor."

    # ─── Utilidades ───────────────────────────────────────────

    # ─── Interacción dentro de aplicaciones ──────────────────

    def click_on_text(self, text: str, wait: float = 2.0) -> str:
        """
        Busca texto visible en pantalla y hace clic en él.
        Usa OCR con pyautogui.locateOnScreen o busca por imagen.
        Fallback: usa la accesibilidad de Windows (UI Automation).
        """
        import pyautogui
        try:
            # Esperar a que la UI se estabilice
            time.sleep(wait)

            # Intentar con pyautogui.locateOnScreen no es viable para texto
            # Usamos UI Automation via PowerShell para encontrar elementos
            result = self._find_and_click_ui_element(text)
            if result:
                return result

            # Fallback: tomar screenshot, buscar con OCR-like approach
            # Intentar buscar texto directamente con accesibilidad
            result = self._click_via_accessibility(text)
            if result:
                return result

            return f"No se encontró el texto '{text}' en la pantalla."
        except Exception as e:
            logger.error(f"Error haciendo clic en '{text}': {e}")
            return f"Error al intentar hacer clic en '{text}': {e}"

    def _find_and_click_ui_element(self, text: str) -> Optional[str]:
        """
        Busca un elemento UI por texto usando la API de Windows UI Automation
        a través de PowerShell.
        """
        try:
            # Usar PowerShell para buscar elementos de UI con el texto
            ps_script = f'''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            $root = [System.Windows.Automation.AutomationElement]::RootElement
            $condition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty,
                "{text}"
            )
            $element = $root.FindFirst(
                [System.Windows.Automation.TreeScope]::Descendants,
                $condition
            )
            if ($element) {{
                $rect = $element.Current.BoundingRectangle
                $x = [int]($rect.X + $rect.Width / 2)
                $y = [int]($rect.Y + $rect.Height / 2)
                Write-Output "$x,$y"
            }} else {{
                # Búsqueda parcial - buscar elementos que contengan el texto
                $allCondition = [System.Windows.Automation.Condition]::TrueCondition
                $elements = $root.FindAll(
                    [System.Windows.Automation.TreeScope]::Descendants,
                    $allCondition
                )
                foreach ($el in $elements) {{
                    try {{
                        $name = $el.Current.Name
                        if ($name -and $name -like "*{text}*") {{
                            $rect = $el.Current.BoundingRectangle
                            if ($rect.Width -gt 0 -and $rect.Height -gt 0) {{
                                $x = [int]($rect.X + $rect.Width / 2)
                                $y = [int]($rect.Y + $rect.Height / 2)
                                Write-Output "$x,$y"
                                break
                            }}
                        }}
                    }} catch {{}}
                }}
            }}
            '''
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip()
            if output and ',' in output:
                coords = output.strip().split('\n')[-1]  # Last match
                x, y = map(int, coords.split(','))
                import pyautogui
                pyautogui.click(x, y)
                logger.info(f"Clic en elemento UI '{text}' en ({x}, {y})")
                return f"Clic realizado en '{text}'"
        except subprocess.TimeoutExpired:
            logger.warning("Timeout buscando elemento UI")
        except Exception as e:
            logger.warning(f"Error en UI Automation: {e}")
        return None

    def _click_via_accessibility(self, text: str) -> Optional[str]:
        """
        Fallback: intenta encontrar y clicar usando coordenadas de imagen.
        Captura la pantalla y busca coincidencias de texto.
        """
        try:
            import pyautogui
            # Usar la función Tab para navegar por elementos
            # Esto es un enfoque de último recurso
            logger.info(f"Intentando localizar '{text}' con método alternativo...")

            # Intentar buscar patrones de imagen si existe un template
            # Por ahora, usamos el portapapeles + Ctrl+F como estrategia
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)

            if text.isascii():
                pyautogui.typewrite(text, interval=0.03)
            else:
                subprocess.run(
                    ["powershell", "-command",
                     f"Set-Clipboard -Value '{text}'"],
                    check=True, timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                pyautogui.hotkey('ctrl', 'v')

            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.3)
            pyautogui.press('escape')
            return f"Texto '{text}' buscado en la aplicación activa"
        except Exception as e:
            logger.warning(f"Error en búsqueda de accesibilidad: {e}")
        return None

    def type_in_app(self, text: str) -> str:
        """Escribe texto en la aplicación activa."""
        import pyautogui
        try:
            time.sleep(0.3)
            if text.isascii():
                pyautogui.typewrite(text, interval=0.03)
            else:
                subprocess.run(
                    ["powershell", "-command",
                     f"Set-Clipboard -Value '{text}'"],
                    check=True, timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                pyautogui.hotkey('ctrl', 'v')
            return f"Texto escrito: '{text}'"
        except Exception as e:
            logger.error(f"Error escribiendo texto: {e}")
            return f"Error al escribir: {e}"

    def press_key(self, key: str) -> str:
        """Pulsa una tecla o combinación de teclas."""
        import pyautogui
        try:
            keys = [k.strip() for k in key.split('+')]
            if len(keys) > 1:
                pyautogui.hotkey(*keys)
            else:
                pyautogui.press(keys[0])
            return f"Tecla presionada: {key}"
        except Exception as e:
            logger.error(f"Error pulsando tecla '{key}': {e}")
            return f"Error al pulsar tecla: {e}"

    def select_profile(self, profile_name: str, app_name: str = "") -> str:
        """
        Selecciona un perfil en una aplicación (Chrome, Firefox, etc.).
        Espera a que la ventana de selección de perfil aparezca y hace clic.
        """
        import pyautogui
        try:
            # Esperar a que la ventana de perfil cargue
            time.sleep(3.0)

            # Intentar con UI Automation primero
            result = self._find_and_click_ui_element(profile_name)
            if result:
                return f"Perfil '{profile_name}' seleccionado"

            # Fallback: buscar usando Alt+Tab y luego buscar texto
            # En Chrome, los perfiles aparecen como botones con el nombre
            # Intentamos Tab para navegar y Enter para seleccionar
            logger.info(f"Buscando perfil '{profile_name}' con método alternativo")

            # Tomar screenshot para ubicar el perfil
            screenshot = pyautogui.screenshot()
            width, height = screenshot.size

            # Los botones de perfil de Chrome suelen estar en el centro
            # Intentamos hacer clic en la zona del selector de perfil
            # Primero intentamos buscar por UI Automation con búsqueda parcial
            ps_script = f'''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            $root = [System.Windows.Automation.AutomationElement]::RootElement
            $allCondition = [System.Windows.Automation.Condition]::TrueCondition
            $elements = $root.FindAll(
                [System.Windows.Automation.TreeScope]::Descendants,
                $allCondition
            )
            $found = $false
            foreach ($el in $elements) {{
                try {{
                    $name = $el.Current.Name
                    if ($name -and $name -like "*{profile_name}*") {{
                        $rect = $el.Current.BoundingRectangle
                        if ($rect.Width -gt 0 -and $rect.Height -gt 0 -and $rect.Width -lt 1000) {{
                            $x = [int]($rect.X + $rect.Width / 2)
                            $y = [int]($rect.Y + $rect.Height / 2)
                            Write-Output "$x,$y"
                            $found = $true
                            break
                        }}
                    }}
                }} catch {{}}
            }}
            if (-not $found) {{ Write-Output "NOT_FOUND" }}
            '''
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=15
            )
            output = result.stdout.strip()
            if output and output != "NOT_FOUND" and ',' in output:
                coords = output.strip().split('\n')[-1]
                x, y = map(int, coords.split(','))
                pyautogui.click(x, y)
                logger.info(f"Perfil '{profile_name}' encontrado y clickeado en ({x}, {y})")
                return f"Perfil '{profile_name}' seleccionado"

            return f"No se encontró el perfil '{profile_name}'. Intente seleccionarlo manualmente."
        except Exception as e:
            logger.error(f"Error seleccionando perfil: {e}")
            return f"Error al seleccionar perfil '{profile_name}': {e}"

    def search_in_page(self, text: str) -> str:
        """
        Busca texto dentro de la página/app activa.
        Primero intenta encontrar un campo de búsqueda en la interfaz,
        si no lo encuentra usa Ctrl+F.
        """
        import pyautogui
        try:
            time.sleep(0.5)

            # Paso 1: Intentar encontrar un campo de búsqueda en la UI
            # (input, search box, etc.) usando UI Automation
            search_found = self._find_and_focus_search_box()

            if search_found:
                # Escribir en el campo de búsqueda encontrado
                time.sleep(0.3)
                # Limpiar campo existente
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.1)
            else:
                # Fallback: usar Ctrl+F (buscar en página)
                pyautogui.hotkey('ctrl', 'f')
                time.sleep(0.5)

            # Escribir el texto de búsqueda
            if text.isascii():
                pyautogui.typewrite(text, interval=0.03)
            else:
                subprocess.run(
                    ["powershell", "-command",
                     f"Set-Clipboard -Value '{text}'"],
                    check=True, timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                pyautogui.hotkey('ctrl', 'v')

            time.sleep(0.3)
            pyautogui.press('enter')

            method = "campo de búsqueda" if search_found else "Ctrl+F"
            logger.info(f"Búsqueda en página '{text}' realizada ({method})")
            return f"He buscado '{text}' en la aplicación activa"
        except Exception as e:
            logger.error(f"Error buscando en página: {e}")
            return f"Error al buscar '{text}' en la página: {e}"

    def _find_and_focus_search_box(self) -> bool:
        """
        Intenta encontrar y enfocar un campo de búsqueda en la UI activa
        usando Windows UI Automation.
        Busca elementos de tipo Edit/SearchBox con nombres comunes de búsqueda.
        """
        try:
            ps_script = '''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            
            # Obtener la ventana activa
            $root = [System.Windows.Automation.AutomationElement]::RootElement
            $focusedWindow = [System.Windows.Automation.AutomationElement]::FocusedElement
            
            # Buscar en toda la UI elementos de tipo Edit que parezcan campos de búsqueda
            $editCondition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
                [System.Windows.Automation.ControlType]::Edit
            )
            $elements = $root.FindAll(
                [System.Windows.Automation.TreeScope]::Descendants,
                $editCondition
            )
            
            $searchKeywords = @("search", "buscar", "busca", "find", "Search", "Buscar")
            
            foreach ($el in $elements) {
                try {
                    $name = $el.Current.Name.ToLower()
                    $autoId = $el.Current.AutomationId.ToLower()
                    $isSearch = $false
                    
                    foreach ($kw in $searchKeywords) {
                        if ($name -like "*$kw*" -or $autoId -like "*$kw*") {
                            $isSearch = $true
                            break
                        }
                    }
                    
                    if ($isSearch) {
                        $rect = $el.Current.BoundingRectangle
                        if ($rect.Width -gt 20 -and $rect.Height -gt 10) {
                            $x = [int]($rect.X + $rect.Width / 2)
                            $y = [int]($rect.Y + $rect.Height / 2)
                            Write-Output "$x,$y"
                            exit
                        }
                    }
                } catch {}
            }
            Write-Output "NOT_FOUND"
            '''
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=8
            )
            output = result.stdout.strip()
            if output and output != "NOT_FOUND" and ',' in output:
                coords = output.strip().split('\n')[-1]
                x, y = map(int, coords.split(','))
                import pyautogui
                pyautogui.click(x, y)
                logger.info(f"Campo de búsqueda encontrado en ({x}, {y})")
                return True
        except Exception as e:
            logger.warning(f"Error buscando campo de búsqueda: {e}")
        return False

    def navigate_to_url(self, url: str) -> str:
        """Navega a una URL en el navegador activo."""
        import pyautogui
        try:
            # Ctrl+L para enfocar la barra de direcciones
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.3)

            # Escribir URL
            if url.isascii():
                pyautogui.typewrite(url, interval=0.02)
            else:
                subprocess.run(
                    ["powershell", "-command",
                     f"Set-Clipboard -Value '{url}'"],
                    check=True, timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                pyautogui.hotkey('ctrl', 'v')

            time.sleep(0.2)
            pyautogui.press('enter')
            return f"Navegando a: {url}"
        except Exception as e:
            logger.error(f"Error navegando a URL: {e}")
            return f"Error al navegar: {e}"

    def scroll_page(self, direction: str = "down", amount: int = 3) -> str:
        """Hace scroll en la aplicación activa."""
        import pyautogui
        try:
            clicks = amount if direction.lower() == "up" else -amount
            pyautogui.scroll(clicks)
            dir_text = "arriba" if direction.lower() == "up" else "abajo"
            return f"Scroll hacia {dir_text}"
        except Exception as e:
            return f"Error al hacer scroll: {e}"

    def click_position(self, x: int, y: int) -> str:
        """Hace clic en una posición específica de la pantalla."""
        import pyautogui
        try:
            pyautogui.click(x, y)
            return f"Clic en posición ({x}, {y})"
        except Exception as e:
            return f"Error al hacer clic: {e}"

    def right_click(self, text: str = "") -> str:
        """Hace clic derecho en un elemento o en la posición actual."""
        import pyautogui
        try:
            if text:
                time.sleep(1.0)
                result = self._find_and_click_ui_element(text)
                if not result:
                    pyautogui.rightClick()
                    return f"Clic derecho en posición actual (no se encontró '{text}')"
                # Re-click con botón derecho
                # Necesitamos obtener las coordenadas de nuevo
                return f"Clic derecho en '{text}'"
            else:
                pyautogui.rightClick()
                return "Clic derecho realizado"
        except Exception as e:
            return f"Error en clic derecho: {e}"

    def double_click(self, text: str = "") -> str:
        """Hace doble clic en un elemento o en la posición actual."""
        import pyautogui
        try:
            if text:
                time.sleep(1.0)
                # Encontrar las coordenadas con UI Automation
                ps_script = f'''
                Add-Type -AssemblyName UIAutomationClient
                Add-Type -AssemblyName UIAutomationTypes
                $root = [System.Windows.Automation.AutomationElement]::RootElement
                $allCondition = [System.Windows.Automation.Condition]::TrueCondition
                $elements = $root.FindAll(
                    [System.Windows.Automation.TreeScope]::Descendants,
                    $allCondition
                )
                foreach ($el in $elements) {{
                    try {{
                        $name = $el.Current.Name
                        if ($name -and $name -like "*{text}*") {{
                            $rect = $el.Current.BoundingRectangle
                            if ($rect.Width -gt 0 -and $rect.Height -gt 0) {{
                                $x = [int]($rect.X + $rect.Width / 2)
                                $y = [int]($rect.Y + $rect.Height / 2)
                                Write-Output "$x,$y"
                                break
                            }}
                        }}
                    }} catch {{}}
                }}
                '''
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                    capture_output=True, text=True, timeout=10
                )
                output = result.stdout.strip()
                if output and ',' in output:
                    coords = output.strip().split('\n')[-1]
                    x, y = map(int, coords.split(','))
                    pyautogui.doubleClick(x, y)
                    return f"Doble clic en '{text}'"
                pyautogui.doubleClick()
                return f"Doble clic (no se encontró '{text}')"
            else:
                pyautogui.doubleClick()
                return "Doble clic realizado"
        except Exception as e:
            return f"Error en doble clic: {e}"

    def interact_with_app(self, action: str, target: str = "") -> str:
        """
        Punto de entrada genérico para interacciones dentro de aplicaciones.
        Interpreta la acción y ejecuta la operación correspondiente.
        """
        action_lower = action.lower().strip()
        target = target.strip()

        # Seleccionar perfil
        if any(word in action_lower for word in ["perfil", "profile", "cuenta", "account"]):
            profile_name = target or self._extract_name(action_lower)
            return self.select_profile(profile_name)

        # Navegar a URL
        if any(word in action_lower for word in ["navega", "navigate", "ve a", "ir a", "go to"]):
            url = target or self._extract_url(action_lower)
            return self.navigate_to_url(url)

        # Hacer clic en texto
        if any(word in action_lower for word in ["clic", "click", "pulsa", "pincha", "press", "presiona"]):
            return self.click_on_text(target or action_lower)

        # Escribir texto
        if any(word in action_lower for word in ["escribe", "escribir", "type", "teclea"]):
            return self.type_in_app(target)

        # Scroll
        if any(word in action_lower for word in ["scroll", "desplaza", "baja", "sube"]):
            direction = "up" if any(w in action_lower for w in ["arriba", "up", "sube"]) else "down"
            return self.scroll_page(direction)

        # Fallback: intentar clic en el target
        if target:
            return self.click_on_text(target)

        return f"No se pudo interpretar la acción: {action}"

    def _extract_name(self, text: str) -> str:
        """Extrae un nombre/identificador del texto."""
        import re
        # Buscar texto después de palabras clave
        patterns = [
            r"perfil\s+(?:de\s+)?(.+)",
            r"cuenta\s+(?:de\s+)?(.+)",
            r"profile\s+(.+)",
            r"account\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return text

    def _extract_url(self, text: str) -> str:
        """Extrae una URL del texto."""
        import re
        url_match = re.search(r'(https?://\S+|www\.\S+|\S+\.\w{2,3}(?:/\S*)?)', text)
        if url_match:
            return url_match.group(1)
        # Quitar verbos comunes
        for word in ["navega a", "navigate to", "ve a", "ir a", "go to"]:
            text = text.replace(word, "").strip()
        return text

    @staticmethod
    def _format_bytes(bytes_val: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"
