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
import tempfile

logger = logging.getLogger("jarvis.system_control")


class SystemControl:
    """Controla funciones del sistema operativo Windows."""

    def __init__(self):
        # Nombres legibles para la búsqueda de Windows
        # Clave = lo que dice el usuario, Valor = lo que se escribe en Windows Search
        self._brain = None  # Referencia opcional al LLM para features avanzados

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

    # ─── Helpers internos ─────────────────────────────────────

    def _safe_set_clipboard(self, text: str) -> None:
        """
        Copia texto al portapapeles de forma segura.
        Usa -EncodedCommand para evitar problemas con comillas,
        apóstrofes y caracteres especiales en PowerShell.
        """
        import base64
        # PowerShell -EncodedCommand espera UTF-16LE en Base64
        ps_code = f'Set-Clipboard -Value "{text.replace(chr(34), chr(96)+chr(34))}"'
        encoded = base64.b64encode(ps_code.encode('utf-16-le')).decode('ascii')
        subprocess.run(
            ["powershell", "-NoProfile", "-EncodedCommand", encoded],
            check=True, timeout=5,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

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
                self._safe_set_clipboard(search_term)
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

    def _get_volume_interface(self):
        """Obtiene la interfaz de volumen del sistema (compatible con pycaw nuevo y viejo)."""
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        # pycaw >= 2024: AudioDevice wrapper con .EndpointVolume
        if hasattr(devices, 'EndpointVolume'):
            return devices.EndpointVolume
        # pycaw antiguo: .Activate()
        from pycaw.pycaw import IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return interface.QueryInterface(IAudioEndpointVolume)

    def volume_up(self, amount: int = 10) -> str:
        """Sube el volumen del sistema."""
        try:
            volume = self._get_volume_interface()

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
            volume = self._get_volume_interface()

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
            volume = self._get_volume_interface()

            level_scalar = max(0.0, min(1.0, level / 100.0))
            volume.SetMasterVolumeLevelScalar(level_scalar, None)

            return f"Volumen establecido a {level}%"
        except Exception as e:
            logger.error(f"Error estableciendo volumen: {e}")
            return f"Error al establecer el volumen: {e}"

    def mute(self) -> str:
        """Silencia o activa el sonido del sistema."""
        try:
            volume = self._get_volume_interface()

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
            volume = self._get_volume_interface()
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
        Estrategia escalonada:
        1. Ctrl+F para encontrar → detectar highlight naranja → clic en él
        2. UI Automation con validación estricta
        3. Último recurso: clic en la zona central donde Chrome muestra el match
        """
        import pyautogui
        try:
            # Esperar a que la UI se estabilice
            time.sleep(wait)

            # ─── Estrategia 1: Ctrl+F → detectar highlight → clic ────
            result = self._click_via_ctrlf_highlight(text)
            if result:
                time.sleep(2.5)
                return result

            # ─── Estrategia 2: UI Automation con validación estricta ──
            result = self._find_and_click_ui_element(text)
            if result:
                time.sleep(2.5)
                return result

            # ─── Estrategia 3: OCR ───────────────────────────────────
            result = self._find_and_click_via_ocr(text)
            if result:
                time.sleep(2.5)
                return result

            return f"No se encontró el texto '{text}' en la pantalla."
        except Exception as e:
            logger.error(f"Error haciendo clic en '{text}': {e}")
            return f"Error al intentar hacer clic en '{text}': {e}"

    def _click_via_ctrlf_highlight(self, text: str) -> Optional[str]:
        """
        Usa Ctrl+F para buscar el texto → Chrome lo resalta en naranja/amarillo.
        Captura screenshot → detecta el rectángulo de color del highlight → clic.
        Si no detecta el color, cierra Ctrl+F y hace clic en la zona scrolleada.
        """
        import pyautogui
        import numpy as np
        from PIL import Image
        try:
            # 1. Abrir Ctrl+F y buscar el texto
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)

            if text.isascii():
                pyautogui.typewrite(text, interval=0.03)
            else:
                self._safe_set_clipboard(text)
                pyautogui.hotkey('ctrl', 'v')

            time.sleep(0.8)
            pyautogui.press('enter')  # Ir al primer resultado
            time.sleep(0.5)

            # 2. Capturar screenshot con el highlight visible
            screenshot = pyautogui.screenshot()
            img_array = np.array(screenshot)

            # 3. Buscar el color naranja del highlight activo de Chrome
            #    Chrome usa ~RGB(255, 150, 50) para el match activo
            #    y ~RGB(255, 255, 0) para los otros matches.
            #    Buscamos el naranja (match activo) primero.
            # Rango naranja del highlight activo (Chrome)
            orange_mask = (
                (img_array[:, :, 0] >= 230) &  # R alto
                (img_array[:, :, 1] >= 120) & (img_array[:, :, 1] <= 190) &  # G medio
                (img_array[:, :, 2] <= 80)  # B bajo
            )

            # Si no hay naranja, probar con amarillo (highlight pasivo)
            if not np.any(orange_mask):
                orange_mask = (
                    (img_array[:, :, 0] >= 230) &  # R alto
                    (img_array[:, :, 1] >= 220) &  # G alto
                    (img_array[:, :, 2] <= 80)  # B bajo
                )

            # 4. Cerrar el buscador Ctrl+F
            pyautogui.press('escape')
            time.sleep(0.3)

            if np.any(orange_mask):
                # Encontrar las posiciones del highlight
                ys, xs = np.where(orange_mask)
                screen_h = img_array.shape[0]

                # FILTRAR píxeles al content area ANTES de calcular mediana
                # (excluir barra de tabs/Ctrl+F arriba y taskbar abajo)
                content_filter = (ys > 120) & (ys < (screen_h - 80))
                xs_filtered = xs[content_filter]
                ys_filtered = ys[content_filter]

                if len(xs_filtered) > 3:  # Al menos unos píxeles en el content
                    cx = int(np.median(xs_filtered))
                    cy = int(np.median(ys_filtered))
                    pyautogui.click(cx, cy)
                    logger.info(f"Ctrl+F highlight: clic en '{text}' en ({cx}, {cy})")
                    return f"Clic realizado en '{text}'"
                else:
                    logger.info(f"Highlight encontrado pero solo fuera del content area ({len(xs)} px total)")

            # 5. Si no detectamos el highlight, la página ya se scrolleó
            #    al texto. Intentar clic en la zona visible.
            logger.info(f"No se detectó highlight para '{text}'. Intentando clic en zona central.")

            # Obtener la ventana activa para limitar el clic al viewport
            screen_w, screen_h = pyautogui.size()
            # Chrome content area: ~85px desde arriba (tabs+address bar),
            # ~40px desde abajo (taskbar)
            content_center_y = 85 + (screen_h - 85 - 40) // 2
            content_center_x = screen_w // 2

            # Hacer clic en el centro del contenido
            pyautogui.click(content_center_x, content_center_y)
            time.sleep(0.3)

            return f"Clic realizado en '{text}' (zona central)"

        except Exception as e:
            logger.warning(f"Error en Ctrl+F highlight click: {e}")
            # Asegurar que cerramos Ctrl+F si hubo error
            try:
                pyautogui.press('escape')
            except Exception:
                pass
        return None

    def _find_and_click_ui_element(self, text: str) -> Optional[str]:
        """
        Busca un elemento UI por texto usando la API de Windows UI Automation.
        Validación estricta: solo elementos visibles, clicables, en el viewport.
        """
        try:
            import pyautogui
            screen_w, screen_h = pyautogui.size()

            # Escapar caracteres problemáticos para PowerShell
            safe_text = text.replace('"', '`"').replace("'", "''")
            # Buscar elementos clicables (links, botones) que contengan el texto
            # Filtrar: IsOffscreen=False, coordenadas dentro del content area
            ps_script = f'''
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            $root = [System.Windows.Automation.AutomationElement]::RootElement
            $searchText = "{safe_text}"
            
            # Buscar SOLO elementos clicables: hyperlinks, buttons, list items
            $allCondition = [System.Windows.Automation.Condition]::TrueCondition
            $elements = $root.FindAll(
                [System.Windows.Automation.TreeScope]::Descendants,
                $allCondition
            )
            
            $results = @()
            foreach ($el in $elements) {{
                try {{
                    $name = $el.Current.Name
                    if (-not $name) {{ continue }}
                    if ($name -notlike "*$searchText*") {{ continue }}
                    
                    # Verificar que NO está fuera de pantalla
                    if ($el.Current.IsOffscreen) {{ continue }}
                    
                    $rect = $el.Current.BoundingRectangle
                    $x = [int]($rect.X + $rect.Width / 2)
                    $y = [int]($rect.Y + $rect.Height / 2)
                    
                    # Validar coordenadas dentro del content area
                    # (no en tabs ni taskbar: y > 80 y y < screen_h - 40)
                    if ($x -le 0 -or $y -le 80) {{ continue }}
                    if ($x -ge {screen_w} -or $y -ge {screen_h - 40}) {{ continue }}
                    if ($rect.Width -le 5 -or $rect.Height -le 5) {{ continue }}
                    if ($rect.Width -gt {screen_w} -or $rect.Height -gt 200) {{ continue }}
                    
                    # Preferir hyperlinks y botones sobre texto estático
                    $ctrlType = $el.Current.ControlType.ProgrammaticName
                    $priority = 2
                    if ($ctrlType -eq "ControlType.Hyperlink") {{ $priority = 0 }}
                    if ($ctrlType -eq "ControlType.Button") {{ $priority = 0 }}
                    if ($ctrlType -eq "ControlType.ListItem") {{ $priority = 1 }}
                    if ($ctrlType -eq "ControlType.Text") {{ $priority = 1 }}
                    
                    $results += "$priority|$x|$y|$ctrlType|$name"
                }} catch {{}}
            }}
            
            if ($results.Count -gt 0) {{
                # Ordenar por prioridad (hyperlinks/buttons primero)
                $sorted = $results | Sort-Object
                $best = $sorted[0]
                $parts = $best -split "\\|"
                Write-Output "$($parts[1]),$($parts[2])"
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
                pyautogui.click(x, y)
                logger.info(f"UI Automation: clic en '{text}' en ({x}, {y})")
                return f"Clic realizado en '{text}'"
            else:
                logger.info(f"UI Automation: '{text}' no encontrado con validación estricta")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout buscando elemento UI")
        except Exception as e:
            logger.warning(f"Error en UI Automation: {e}")
        return None

    def _find_and_click_via_ocr(self, text: str) -> Optional[str]:
        """
        Busca texto en pantalla usando OCR de Windows (Windows.Media.Ocr).
        No requiere dependencias externas — usa el OCR nativo de Windows 10/11.
        Captura un screenshot, lo procesa con OCR y busca la coincidencia más cercana.
        """
        import pyautogui
        try:
            # 1. Capturar pantalla y guardar en archivo temporal
            temp_path = os.path.join(
                tempfile.gettempdir(), "jarvis_ocr_screen.png"
            )
            screenshot = pyautogui.screenshot()
            screenshot.save(temp_path)

            # 2. Usar Windows OCR via PowerShell (nativo Win10+)
            search_text_escaped = text.replace("'", "''").replace('"', '`"')
            ps_script = f'''
            Add-Type -AssemblyName System.Runtime.WindowsRuntime

            # Helper para await de tareas async en PowerShell
            $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{
                $_.Name -eq 'AsTask' -and
                $_.GetParameters().Count -eq 1 -and
                $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
            }})[0]
            Function Await($WinRtTask, $ResultType) {{
                $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
                $netTask = $asTask.Invoke($null, @($WinRtTask))
                $netTask.Wait(-1) | Out-Null
                $netTask.Result
            }}

            # Cargar ensamblados de OCR
            [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
            [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
            [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
            [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null

            # Abrir imagen
            $storagefile = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync("{temp_path.replace(chr(92), '/')}")) ([Windows.Storage.StorageFile])
            $stream = Await ($storagefile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
            $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
            $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

            # Crear motor OCR en español
            $lang = New-Object Windows.Globalization.Language("es-ES")
            $ocr = $null
            if ([Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($lang)) {{
                $ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
            }}
            if ($null -eq $ocr) {{
                $ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
            }}

            # Ejecutar OCR
            $result = Await ($ocr.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

            # Buscar el texto objetivo (búsqueda flexible)
            $searchText = "{search_text_escaped}".ToLower()
            $bestMatch = $null
            $bestDist = 9999
            $allWords = @()

            foreach ($line in $result.Lines) {{
                $lineText = $line.Text.ToLower()
                
                # Verificar si la línea completa contiene el texto
                if ($lineText -like "*$searchText*") {{
                    foreach ($word in $line.Words) {{
                        $rect = $word.BoundingRect
                        $allWords += @{{
                            Text = $word.Text
                            X = [int]($rect.X + $rect.Width / 2)
                            Y = [int]($rect.Y + $rect.Height / 2)
                        }}
                    }}
                    if ($allWords.Count -gt 0) {{
                        # Calcular centro del grupo de palabras que coinciden
                        $avgX = [int](($allWords | Measure-Object -Property X -Average).Average)
                        $avgY = [int](($allWords | Measure-Object -Property Y -Average).Average)
                        Write-Output "FOUND:$avgX,$avgY"
                        $stream.Dispose()
                        exit
                    }}
                }}
                
                # También buscar palabras individuales similares
                foreach ($word in $line.Words) {{
                    $wordText = $word.Text.ToLower()
                    # Comparación por similitud (contiene / empieza con)
                    if ($wordText -eq $searchText -or
                        $wordText -like "$searchText*" -or
                        $searchText -like "$wordText*" -or
                        $wordText -like "*$searchText*") {{
                        $rect = $word.BoundingRect
                        $x = [int]($rect.X + $rect.Width / 2)
                        $y = [int]($rect.Y + $rect.Height / 2)
                        # Preferir coincidencias exactas
                        $dist = [Math]::Abs($wordText.Length - $searchText.Length)
                        if ($dist -lt $bestDist) {{
                            $bestDist = $dist
                            $bestMatch = "$x,$y"
                        }}
                    }}
                }}
            }}

            if ($bestMatch) {{
                Write-Output "FOUND:$bestMatch"
            }} else {{
                Write-Output "NOT_FOUND"
            }}
            $stream.Dispose()
            '''

            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=20
            )

            output = result.stdout.strip()
            logger.debug(f"OCR output: {output}")

            if output and output.startswith("FOUND:"):
                coords_str = output.split("FOUND:")[-1].strip()
                if ',' in coords_str:
                    x, y = map(int, coords_str.split(','))
                    pyautogui.click(x, y)
                    logger.info(f"OCR: Clic en '{text}' en ({x}, {y})")
                    return f"Clic realizado en '{text}'"

            # Si no lo encontró exacto, intentar búsqueda difusa
            if output == "NOT_FOUND":
                logger.info(f"OCR: Texto '{text}' no encontrado en pantalla")

        except subprocess.TimeoutExpired:
            logger.warning("Timeout en OCR de pantalla")
        except Exception as e:
            logger.warning(f"Error en OCR de pantalla: {e}")

        # Limpiar archivo temporal
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

        return None

    def _ocr_screen_lines(self, monitor: int = None) -> list[dict]:
        """
        Captura la pantalla y devuelve TODAS las líneas de texto detectadas por OCR.
        Usa Windows.Media.Ocr (nativo Win10/11).

        Args:
            monitor: Índice del monitor (0-based). None = pantalla principal completa.

        Returns: Lista de {"text": str, "x": int, "y": int, "width": int, "height": int}
        """
        import pyautogui
        temp_path = os.path.join(tempfile.gettempdir(), "jarvis_ocr_lines.png")
        offset_x, offset_y = 0, 0
        try:
            if monitor is not None:
                try:
                    from screeninfo import get_monitors
                    monitors = get_monitors()
                    if 0 <= monitor < len(monitors):
                        m = monitors[monitor]
                        offset_x, offset_y = m.x, m.y
                        screenshot = pyautogui.screenshot(region=(m.x, m.y, m.width, m.height))
                    else:
                        logger.warning(f"Monitor {monitor} no existe, usando pantalla principal")
                        screenshot = pyautogui.screenshot()
                except ImportError:
                    logger.warning("screeninfo no disponible, usando pantalla principal")
                    screenshot = pyautogui.screenshot()
            else:
                screenshot = pyautogui.screenshot()
            screenshot.save(temp_path)
            logger.info(f"Screenshot guardado: {temp_path} ({screenshot.size[0]}x{screenshot.size[1]})")

            # Guardar copia de diagnóstico para verificar qué se capturó
            debug_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "last_ocr_capture.png")
            try:
                screenshot.save(debug_path)
            except Exception:
                pass
            ps_script = f'''
            Add-Type -AssemblyName System.Runtime.WindowsRuntime

            $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{
                $_.Name -eq 'AsTask' -and
                $_.GetParameters().Count -eq 1 -and
                $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
            }})[0]
            Function Await($WinRtTask, $ResultType) {{
                $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
                $netTask = $asTask.Invoke($null, @($WinRtTask))
                $netTask.Wait(-1) | Out-Null
                $netTask.Result
            }}

            [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
            [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
            [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
            [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null

            $storagefile = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync("{temp_path.replace(chr(92), '/')}")) ([Windows.Storage.StorageFile])
            $stream = Await ($storagefile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
            $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
            $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

            $lang = New-Object Windows.Globalization.Language("es-ES")
            $ocr = $null
            if ([Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($lang)) {{
                $ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
            }}
            if ($null -eq $ocr) {{
                $ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
            }}

            $result = Await ($ocr.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

            foreach ($line in $result.Lines) {{
                $words = $line.Words
                if ($words.Count -gt 0) {{
                    $minX = 99999; $minY = 99999; $maxX = 0; $maxY = 0
                    foreach ($w in $words) {{
                        $r = $w.BoundingRect
                        if ($r.X -lt $minX) {{ $minX = $r.X }}
                        if ($r.Y -lt $minY) {{ $minY = $r.Y }}
                        $rx = $r.X + $r.Width
                        $ry = $r.Y + $r.Height
                        if ($rx -gt $maxX) {{ $maxX = $rx }}
                        if ($ry -gt $maxY) {{ $maxY = $ry }}
                    }}
                    $cx = [int](($minX + $maxX) / 2)
                    $cy = [int](($minY + $maxY) / 2)
                    $w = [int]($maxX - $minX)
                    $h = [int]($maxY - $minY)
                    Write-Output "LINE:$cy|$cx|$w|$h|$($line.Text)"
                }}
            }}
            $stream.Dispose()
            '''

            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=30
            )

            # Log errores de PowerShell para debugging
            if result.stderr and result.stderr.strip():
                logger.warning(f"OCR PowerShell stderr: {result.stderr[:300]}")
            if result.returncode != 0:
                logger.warning(f"OCR PowerShell exit code: {result.returncode}")

            lines = []
            for raw_line in result.stdout.strip().split('\n'):
                raw_line = raw_line.strip()
                if raw_line.startswith('LINE:'):
                    parts = raw_line[5:].split('|', 4)
                    if len(parts) >= 5:
                        lines.append({
                            "y": int(parts[0]) + offset_y,
                            "x": int(parts[1]) + offset_x,
                            "width": int(parts[2]),
                            "height": int(parts[3]),
                            "text": parts[4],
                        })

            logger.info(f"OCR detectó {len(lines)} líneas de texto")
            if len(lines) == 0:
                logger.warning("OCR devolvió 0 líneas. stdout completo (primeros 500 chars):")
                logger.warning(f"  stdout: {result.stdout[:500]}")
            return lines

        except Exception as e:
            logger.warning(f"Error en OCR de pantalla: {e}", exc_info=True)
            return []
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    def _ocr_find_coords(self, text: str, lines: list[dict] = None) -> Optional[tuple]:
        """
        Busca texto en pantalla via OCR y devuelve (x, y) sin hacer clic.
        Si se pasan 'lines' ya obtenidas, las reutiliza (evita screenshot duplicado).
        """
        if lines is None:
            lines = self._ocr_screen_lines()

        search = text.lower().strip()

        # 1. Buscar en línea completa (coincidencia parcial)
        for line in lines:
            if search in line["text"].lower():
                return (line["x"], line["y"])

        # 2. Buscar por palabras sueltas similares
        best = None
        best_dist = 9999
        for line in lines:
            for word in line["text"].lower().split():
                # Limpiar signos de puntuación
                clean_word = word.strip('.,;:!?¿¡"\'()[]{}')
                if clean_word == search or search in clean_word or clean_word in search:
                    dist = abs(len(clean_word) - len(search))
                    if dist < best_dist:
                        best_dist = dist
                        best = (line["x"], line["y"])

        return best

    def click_first_result(self) -> str:
        """
        Hace clic en el primer resultado de búsqueda de la página actual.
        Funciona con Google, Bing, DuckDuckGo, etc.
        Usa OCR para encontrar el primer enlace/resultado en el área de contenido.
        """
        import pyautogui
        try:
            time.sleep(1.5)

            lines = self._ocr_screen_lines()
            if not lines:
                return "No se pudo leer la pantalla."

            screen_w, screen_h = pyautogui.size()

            # Ordenar por posición Y (de arriba a abajo)
            lines.sort(key=lambda l: l["y"])

            # Palabras de navegación que NO son resultados de búsqueda
            nav_keywords = {
                'todo', 'imágenes', 'imagenes', 'videos', 'noticias', 'más', 'mas',
                'productos', 'herramientas', 'videos cortos', 'modo ia',
                'all', 'images', 'news', 'shopping', 'more', 'tools',
                'nueva pestaña', 'nueva pestana', 'buscar',
            }

            # El umbral Y mínimo para ignorar barra de navegación/búsqueda
            # Típicamente los resultados empiezan después del 15% superior de pantalla
            min_y = int(screen_h * 0.15)

            for line in lines:
                y = line["y"]
                text = line["text"]
                text_lower = text.lower().strip()

                # Saltar zona de navegación del navegador
                if y < min_y:
                    continue

                # Saltar elementos de navegación de buscador
                if text_lower in nav_keywords:
                    continue

                # Saltar textos muy cortos (botones, iconos)
                if len(text) < 15:
                    continue

                # Saltar URLs
                if text_lower.startswith('http') or '://' in text_lower:
                    continue

                # Saltar textos que parecen metadatos (fechas, snippets de URL)
                if text_lower.startswith('https://') or '›' in text:
                    continue

                # Saltar textos que contienen solo dominios/rutas
                if all(c in 'abcdefghijklmnopqrstuvwxyz0123456789.-/' for c in text_lower.replace(' ', '')):
                    continue

                # Este debería ser el primer resultado real
                click_x = line["x"]
                click_y = line["y"]
                pyautogui.click(click_x, click_y)
                logger.info(f"Primer resultado clickeado: '{text}' en ({click_x}, {click_y})")
                return f"He entrado en el primer resultado: '{text[:60]}'"

            return "No se encontró ningún resultado de búsqueda en la página."
        except Exception as e:
            logger.error(f"Error clickeando primer resultado: {e}")
            return f"Error al entrar en el primer resultado: {e}"

    def move_discord_user(self, username: str, channel: str) -> str:
        """
        Mueve un usuario de Discord a un canal de voz usando drag & drop.
        Busca al usuario y al canal en la pantalla por OCR, luego arrastra.
        """
        import pyautogui
        try:
            time.sleep(1.0)

            # Una sola captura OCR para encontrar ambos
            lines = self._ocr_screen_lines()
            if not lines:
                return "No se pudo leer la pantalla."

            # 1. Encontrar la posición del usuario
            user_coords = self._ocr_find_coords(username, lines)
            if not user_coords:
                # Intentar con nombre parcial (solo primera parte)
                first_word = username.split()[0] if ' ' in username else username
                user_coords = self._ocr_find_coords(first_word, lines)

            if not user_coords:
                return f"No se encontró al usuario '{username}' en la pantalla."

            # 2. Encontrar la posición del canal destino
            channel_coords = self._ocr_find_coords(channel, lines)
            if not channel_coords:
                return f"No se encontró el canal '{channel}' en la pantalla."

            user_x, user_y = user_coords
            chan_x, chan_y = channel_coords

            logger.info(
                f"Moviendo usuario '{username}' ({user_x},{user_y}) "
                f"→ canal '{channel}' ({chan_x},{chan_y})"
            )

            # 3. Drag & drop: arrastrar usuario al canal
            pyautogui.moveTo(user_x, user_y)
            time.sleep(0.3)
            pyautogui.mouseDown()
            time.sleep(0.5)
            # Mover gradualmente para que Discord reconozca el drag
            pyautogui.moveTo(chan_x, chan_y, duration=0.8)
            time.sleep(0.3)
            pyautogui.mouseUp()
            time.sleep(0.5)

            logger.info(f"Drag & drop completado: '{username}' → '{channel}'")
            return f"Usuario '{username}' movido al canal '{channel}'."

        except Exception as e:
            logger.error(f"Error moviendo usuario en Discord: {e}")
            return f"Error al mover usuario: {e}"

    # ─── Brain reference (para features avanzados) ────────────

    def set_brain(self, brain):
        """Establece referencia al LLM para features como describe_and_click."""
        self._brain = brain
        logger.info("Brain reference establecida en SystemControl.")

    # ─── Foco de ventanas ──────────────────────────────────────

    def focus_window(self, app_name: str) -> str:
        """Trae una ventana al primer plano por nombre de aplicación."""
        try:
            app_lower = app_name.lower().strip()
            search = self._app_search_names.get(app_lower, app_name)

            # Nombres de proceso alternativos para apps cuyos procesos no coinciden
            _process_aliases = {
                "intellij": ["idea64", "idea"],
                "intellij idea": ["idea64", "idea"],
                "idea": ["idea64", "idea"],
                "pycharm": ["pycharm64", "pycharm"],
                "webstorm": ["webstorm64", "webstorm"],
                "android studio": ["studio64", "studio"],
                "vscode": ["Code"],
                "visual studio code": ["Code"],
                "code": ["Code"],
            }
            extra_procs = _process_aliases.get(app_lower, [])
            # Build a PowerShell array of extra process names for matching
            extra_procs_ps = ",".join(f'"{p}"' for p in extra_procs) if extra_procs else ""

            ps_script = f'''
            Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                public class JarvisWinFocus {{
                    [DllImport("user32.dll")]
                    public static extern bool SetForegroundWindow(IntPtr hWnd);
                    [DllImport("user32.dll")]
                    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                    [DllImport("user32.dll")]
                    public static extern bool IsIconic(IntPtr hWnd);
                }}
"@
            $extraNames = @({extra_procs_ps})
            $procs = Get-Process | Where-Object {{ $_.MainWindowTitle -ne "" }}
            $target = $null
            foreach ($p in $procs) {{
                $matched = $false
                # Match por título de ventana
                if ($p.MainWindowTitle -like "*{search}*") {{ $matched = $true }}
                # Match por nombre de proceso (original)
                if ($p.ProcessName -like "*{app_lower}*") {{ $matched = $true }}
                # Match por aliases de proceso (ej: idea64 para IntelliJ)
                foreach ($alias in $extraNames) {{
                    if ($p.ProcessName -eq $alias) {{ $matched = $true; break }}
                }}
                if ($matched) {{
                    $target = $p
                    break
                }}
            }}
            if ($target) {{
                $hwnd = $target.MainWindowHandle
                if ([JarvisWinFocus]::IsIconic($hwnd)) {{
                    [JarvisWinFocus]::ShowWindow($hwnd, 9)
                }}
                [JarvisWinFocus]::SetForegroundWindow($hwnd)
                Write-Output "FOCUSED:$($target.MainWindowTitle)"
            }} else {{
                Write-Output "NOT_FOUND:{search}"
            }}
            '''
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip()
            stderr = result.stderr.strip()
            if stderr:
                logger.warning(f"focus_window stderr: {stderr}")
            logger.info(f"focus_window output: {output}")

            if output.startswith("FOCUSED:"):
                title = output.split("FOCUSED:", 1)[1]
                logger.info(f"Ventana enfocada: {title}")
                return f"Ventana '{title}' en primer plano."
            if output.startswith("NOT_FOUND:"):
                searched = output.split("NOT_FOUND:", 1)[1]
                logger.warning(f"No se encontró ventana buscando: '{searched}' (proceso: {app_lower}, aliases: {extra_procs})")
            return f"No se encontró ventana de '{app_name}'."
        except Exception as e:
            logger.error(f"Error enfocando ventana: {e}")
            return f"Error al enfocar ventana: {e}"

    def get_active_window_title(self) -> str:
        """Devuelve el título de la ventana activa actualmente."""
        try:
            ps = '''
            Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                using System.Text;
                public class JarvisWinTitle {
                    [DllImport("user32.dll")]
                    public static extern IntPtr GetForegroundWindow();
                    [DllImport("user32.dll", SetLastError=true)]
                    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
                }
"@
            $hwnd = [JarvisWinTitle]::GetForegroundWindow()
            $sb = New-Object System.Text.StringBuilder 256
            [JarvisWinTitle]::GetWindowText($hwnd, $sb, 256) | Out-Null
            Write-Output $sb.ToString()
            '''
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() or "Desconocido"
        except Exception:
            return "Desconocido"

    # ─── Click inteligente por descripción ────────────────────

    def describe_and_click(self, description: str) -> str:
        """
        Hace clic en un elemento descrito en lenguaje natural.
        Usa OCR + filtrado espacial + LLM para localizar el elemento.
        Ej: "el botón de enviar", "el enlace de arriba a la derecha",
            "donde pone Configuración"
        """
        import pyautogui
        try:
            time.sleep(1.0)
            lines = self._ocr_screen_lines()
            if not lines:
                return "No se pudo leer la pantalla."

            desc_lower = description.lower()
            screen_w, screen_h = pyautogui.size()

            # ── Filtrar por posición si hay pistas espaciales ──
            filtered = lines[:]
            if any(w in desc_lower for w in ["arriba", "superior", "top", "parte de arriba"]):
                filtered = [l for l in filtered if l["y"] < screen_h * 0.4]
            elif any(w in desc_lower for w in ["abajo", "inferior", "bottom", "parte de abajo"]):
                filtered = [l for l in filtered if l["y"] > screen_h * 0.6]

            if any(w in desc_lower for w in ["izquierda", "left"]):
                filtered = [l for l in filtered if l["x"] < screen_w * 0.45]
            elif any(w in desc_lower for w in ["derecha", "right"]):
                filtered = [l for l in filtered if l["x"] > screen_w * 0.55]

            if any(w in desc_lower for w in ["centro", "center", "medio", "middle"]):
                filtered = [l for l in filtered if
                            screen_w * 0.2 < l["x"] < screen_w * 0.8
                            and screen_h * 0.2 < l["y"] < screen_h * 0.8]

            if not filtered:
                filtered = lines

            # ── Método 1: Usar LLM si está disponible ──
            if self._brain:
                options = []
                for i, line in enumerate(filtered):
                    options.append(f"{i}: \"{line['text']}\" (x={line['x']}, y={line['y']})")

                options_text = "\n".join(options[:50])  # Limitar para no saturar
                prompt = (
                    f"El usuario quiere hacer clic en: \"{description}\"\n\n"
                    f"Estos son los textos visibles en pantalla:\n{options_text}\n\n"
                    f"Responde SOLO con el número del elemento que mejor coincida. "
                    f"Si ninguno coincide, responde -1. Solo el número."
                )
                import re as _re
                llm_response = self._brain.chat(prompt).strip()
                num_match = _re.search(r'-?\d+', llm_response)
                if num_match:
                    idx = int(num_match.group())
                    if 0 <= idx < len(filtered):
                        target = filtered[idx]
                        pyautogui.click(target["x"], target["y"])
                        logger.info(f"LLM-click: '{target['text']}' en ({target['x']}, {target['y']})")
                        return f"Clic realizado en '{target['text']}'"

            # ── Método 2: Similitud de texto (fallback sin LLM) ──
            # Quitar palabras espaciales/estructurales de la descripción
            target_words = desc_lower
            for sw in ["arriba", "abajo", "izquierda", "derecha", "centro",
                        "superior", "inferior", "el", "la", "los", "las", "un", "una",
                        "botón", "boton", "enlace", "link", "icono", "imagen",
                        "de", "del", "en", "que", "dice", "pone", "se", "llama",
                        "parte", "lado", "zona", "top", "bottom", "left", "right",
                        "donde", "hay", "está", "esta"]:
                target_words = target_words.replace(sw, " ")
            target_words = " ".join(target_words.split()).strip()

            if target_words:
                best_match = None
                best_score = 0
                for line in filtered:
                    line_lower = line["text"].lower()
                    target_set = set(target_words.split())
                    line_set = set(line_lower.split())
                    overlap = len(target_set & line_set)
                    # Bonus por substring
                    if target_words in line_lower:
                        overlap += 2
                    if overlap > best_score:
                        best_score = overlap
                        best_match = line

                if best_match and best_score > 0:
                    pyautogui.click(best_match["x"], best_match["y"])
                    logger.info(f"Click por similitud: '{best_match['text']}' en ({best_match['x']}, {best_match['y']})")
                    return f"Clic realizado en '{best_match['text']}'"

            # ── Método 3: Primer elemento corto (probablemente un botón/link) ──
            for line in filtered:
                if 3 < len(line["text"]) < 50:
                    pyautogui.click(line["x"], line["y"])
                    return f"Clic en '{line['text']}' (mejor aproximación)"

            return f"No se encontró un elemento que coincida con '{description}'."
        except Exception as e:
            logger.error(f"Error en describe_and_click: {e}")
            return f"Error: {e}"

    # ─── Lectura de pantalla (contexto visual) ────────────────

    def get_screen_text(self) -> str:
        """
        Devuelve todo el texto visible en pantalla como string.
        Útil para dar contexto al LLM sobre qué hay en pantalla.
        """
        lines = self._ocr_screen_lines()
        if not lines:
            return "No se pudo leer la pantalla."
        lines.sort(key=lambda l: (l["y"], l["x"]))
        text = "\n".join(line["text"] for line in lines)
        # Truncar si es muy largo para evitar respuestas enormes
        if len(text) > 2000:
            text = text[:2000] + "\n[... texto truncado ...]"       
        return text

    def get_screen_text_full(self) -> str:
        """
        Devuelve TODO el texto visible en pantalla sin truncar.
        Para captura de ejercicios/documentos donde necesitamos el contenido completo.
        """
        lines = self._ocr_screen_lines()
        if not lines:
            return ""
        lines.sort(key=lambda l: (l["y"], l["x"]))
        return "\n".join(line["text"] for line in lines)

    # ─── Portapapeles ─────────────────────────────────────────

    def read_clipboard(self) -> str:
        """Lee el contenido actual del portapapeles."""
        try:
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5
            )
            content = result.stdout.strip()
            if content:
                return f"Contenido del portapapeles: {content}"
            return "El portapapeles está vacío."
        except Exception as e:
            return f"Error leyendo portapapeles: {e}"

    def copy_to_clipboard(self, text: str) -> str:
        """Copia texto al portapapeles."""
        try:
            escaped = text.replace("'", "''")
            subprocess.run(
                ["powershell", "-command", f"Set-Clipboard -Value '{escaped}'"],
                check=True, timeout=5,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return "Texto copiado al portapapeles."
        except Exception as e:
            return f"Error copiando al portapapeles: {e}"

    # ─── Escritura de texto largo (para soluciones, documentos) ─

    def type_long_text(self, text: str) -> str:
        """
        Escribe texto largo en la aplicación activa.
        Usa el portapapeles en bloques para manejar Unicode y velocidad.
        """
        import pyautogui
        try:
            time.sleep(0.5)
            paragraphs = text.split('\n')
            for i, para in enumerate(paragraphs):
                if not para.strip():
                    pyautogui.press('enter')
                    continue

                escaped = para.replace("'", "''")
                subprocess.run(
                    ["powershell", "-command", f"Set-Clipboard -Value '{escaped}'"],
                    check=True, timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.1)
                if i < len(paragraphs) - 1:
                    pyautogui.press('enter')
                    time.sleep(0.05)

            return f"Texto escrito ({len(text)} caracteres)."
        except Exception as e:
            logger.error(f"Error escribiendo texto largo: {e}")
            return f"Error al escribir: {e}"

    # ─── Gestión de pestañas ─────────────────────────────────

    def switch_tab(self, direction: str = "next") -> str:
        """Cambia de pestaña en el navegador/aplicación."""
        import pyautogui
        try:
            if direction.lower() in ("previous", "anterior", "prev", "izquierda"):
                pyautogui.hotkey('ctrl', 'shift', 'tab')
            else:
                pyautogui.hotkey('ctrl', 'tab')
            return f"Pestaña cambiada ({direction})."
        except Exception as e:
            return f"Error cambiando pestaña: {e}"

    def new_tab(self) -> str:
        """Abre una nueva pestaña en el navegador/aplicación."""
        import pyautogui
        try:
            pyautogui.hotkey('ctrl', 't')
            return "Nueva pestaña abierta."
        except Exception as e:
            return f"Error: {e}"

    def close_tab(self) -> str:
        """Cierra la pestaña actual."""
        import pyautogui
        try:
            pyautogui.hotkey('ctrl', 'w')
            return "Pestaña cerrada."
        except Exception as e:
            return f"Error: {e}"

    # ─── Gestión de ventanas ─────────────────────────────────

    def minimize_window(self) -> str:
        """Minimiza la ventana activa."""
        import pyautogui
        try:
            pyautogui.hotkey('win', 'down')
            return "Ventana minimizada."
        except Exception as e:
            return f"Error: {e}"

    def maximize_window(self) -> str:
        """Maximiza la ventana activa."""
        import pyautogui
        try:
            pyautogui.hotkey('win', 'up')
            return "Ventana maximizada."
        except Exception as e:
            return f"Error: {e}"

    def snap_window(self, position: str = "left") -> str:
        """Ajusta la ventana a un lado de la pantalla (snap)."""
        import pyautogui
        try:
            if position.lower() in ("left", "izquierda"):
                pyautogui.hotkey('win', 'left')
            elif position.lower() in ("right", "derecha"):
                pyautogui.hotkey('win', 'right')
            else:
                pyautogui.hotkey('win', 'up')
            return f"Ventana ajustada a {position}."
        except Exception as e:
            return f"Error: {e}"

    def type_in_app(self, text: str) -> str:
        """Escribe texto en la aplicación activa."""
        import pyautogui
        try:
            time.sleep(0.3)
            if text.isascii():
                pyautogui.typewrite(text, interval=0.03)
            else:
                self._safe_set_clipboard(text)
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
        Usa OCR como método principal (Chrome/Electron no exponen bien sus elementos).
        """
        import pyautogui
        try:
            # Esperar a que la ventana de perfil cargue completamente
            time.sleep(4.0)

            # MÉTODO 1: OCR (más fiable para Chrome, Brave, Edge, etc.)
            result = self._find_and_click_via_ocr(profile_name)
            if result:
                logger.info(f"Perfil '{profile_name}' encontrado por OCR")
                return f"Perfil '{profile_name}' seleccionado"

            # MÉTODO 2: UI Automation (funciona con algunas apps nativas)
            result = self._find_and_click_ui_element(profile_name)
            if result:
                return f"Perfil '{profile_name}' seleccionado"

            # MÉTODO 3: Buscar variantes del nombre (sin acentos, capitalizado, etc.)
            import unicodedata
            def remove_accents(s):
                nfkd = unicodedata.normalize('NFKD', s)
                return ''.join(c for c in nfkd if not unicodedata.combining(c))

            variants = [
                profile_name,
                profile_name.capitalize(),
                profile_name.upper(),
                profile_name.lower(),
                remove_accents(profile_name),
                remove_accents(profile_name).capitalize(),
            ]
            # Eliminar duplicados preservando orden
            seen = set()
            unique_variants = []
            for v in variants:
                if v not in seen:
                    seen.add(v)
                    unique_variants.append(v)

            for variant in unique_variants[1:]:  # Saltar el primero (ya probado)
                result = self._find_and_click_via_ocr(variant)
                if result:
                    logger.info(f"Perfil encontrado como '{variant}' por OCR")
                    return f"Perfil '{profile_name}' seleccionado"

            # MÉTODO 4: Último recurso - Tab para navegar entre perfiles
            logger.info(f"Intentando navegar con Tab para encontrar '{profile_name}'")
            for i in range(12):  # Navegar hasta 12 elementos
                pyautogui.press('tab')
                time.sleep(0.3)
                # Hacer Enter si estamos en el perfil correcto
                # (esto es una heurística, funciona cuando Chrome resalta el perfil)

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
                self._safe_set_clipboard(text)
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
                self._safe_set_clipboard(url)
                pyautogui.hotkey('ctrl', 'v')

            time.sleep(0.2)
            pyautogui.press('enter')
            # Esperar a que la página cargue
            time.sleep(3.0)
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
