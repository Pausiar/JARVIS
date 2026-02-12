"""
J.A.R.V.I.S. — Calendar Manager Module
Gestión de calendario local con recordatorios.
Almacena eventos en SQLite y puede sincronizar con Google Calendar / Outlook.
"""

import json
import sqlite3
import logging
import datetime
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR

logger = logging.getLogger("jarvis.calendar")

CALENDAR_DB = DATA_DIR / "calendar.db"


class CalendarManager:
    """Gestión de calendario local con recordatorios."""

    def __init__(self, on_reminder: Callable[[str], None] = None):
        self.db_path = str(CALENDAR_DB)
        self._on_reminder = on_reminder
        self._reminder_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._init_db()
        logger.info("CalendarManager inicializado.")

    def _init_db(self) -> None:
        """Crea las tablas del calendario."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        start_time DATETIME NOT NULL,
                        end_time DATETIME,
                        location TEXT DEFAULT '',
                        category TEXT DEFAULT 'general',
                        recurring TEXT DEFAULT '',
                        reminder_minutes INTEGER DEFAULT 15,
                        reminded INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error inicializando BD del calendario: {e}")

    # ─── CRUD de eventos ──────────────────────────────────────

    def add_event(
        self,
        title: str,
        start_time: str,
        end_time: str = "",
        description: str = "",
        location: str = "",
        category: str = "general",
        recurring: str = "",
        reminder_minutes: int = 15,
    ) -> str:
        """
        Añade un evento al calendario.

        Args:
            title: Título del evento.
            start_time: Fecha/hora de inicio (formato: YYYY-MM-DD HH:MM o HH:MM para hoy).
            end_time: Fecha/hora de fin (opcional).
            description: Descripción del evento.
            location: Ubicación.
            category: Categoría (general, trabajo, personal, etc.).
            recurring: Recurrencia (daily, weekly, monthly, yearly, o vacío).
            reminder_minutes: Minutos antes para recordar.
        """
        try:
            start_dt = self._parse_datetime(start_time)
            if not start_dt:
                return f"Formato de fecha/hora no válido: {start_time}"

            end_dt = self._parse_datetime(end_time) if end_time else None

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO events "
                    "(title, description, start_time, end_time, location, "
                    "category, recurring, reminder_minutes) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        title,
                        description,
                        start_dt.isoformat(),
                        end_dt.isoformat() if end_dt else None,
                        location,
                        category,
                        recurring,
                        reminder_minutes,
                    ),
                )

            time_str = start_dt.strftime("%d/%m/%Y a las %H:%M")
            logger.info(f"Evento creado: '{title}' para {time_str}")
            return f"Evento '{title}' creado para el {time_str}."
        except Exception as e:
            logger.error(f"Error creando evento: {e}")
            return f"Error al crear el evento: {e}"

    def remove_event(self, event_id: int = 0, title: str = "") -> str:
        """Elimina un evento por ID o título."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if event_id > 0:
                    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
                elif title:
                    conn.execute(
                        "DELETE FROM events WHERE title LIKE ?",
                        (f"%{title}%",),
                    )
                else:
                    return "Especifique un ID o título del evento a eliminar."
            return f"Evento eliminado."
        except Exception as e:
            return f"Error eliminando evento: {e}"

    def get_today_events(self) -> str:
        """Obtiene los eventos de hoy."""
        today = datetime.date.today()
        return self._get_events_for_date(today)

    def get_tomorrow_events(self) -> str:
        """Obtiene los eventos de mañana."""
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        return self._get_events_for_date(tomorrow)

    def get_week_events(self) -> str:
        """Obtiene los eventos de esta semana."""
        today = datetime.date.today()
        end = today + datetime.timedelta(days=7)
        return self._get_events_range(today, end)

    def get_upcoming_events(self, limit: int = 10) -> str:
        """Obtiene los próximos eventos."""
        try:
            now = datetime.datetime.now().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id, title, start_time, end_time, location, category "
                    "FROM events WHERE start_time >= ? "
                    "ORDER BY start_time ASC LIMIT ?",
                    (now, limit),
                )
                rows = cursor.fetchall()

            if not rows:
                return "No tiene eventos próximos, señor."

            lines = ["📅 Próximos eventos:\n"]
            for row in rows:
                eid, title, start, end, loc, cat = row
                dt = datetime.datetime.fromisoformat(start)
                date_str = dt.strftime("%d/%m/%Y %H:%M")
                loc_str = f" 📍 {loc}" if loc else ""
                lines.append(f"  [{eid}] {date_str} — {title}{loc_str}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error obteniendo eventos: {e}"

    def search_events(self, query: str) -> str:
        """Busca eventos por título o descripción."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id, title, start_time, description FROM events "
                    "WHERE title LIKE ? OR description LIKE ? "
                    "ORDER BY start_time DESC LIMIT 10",
                    (f"%{query}%", f"%{query}%"),
                )
                rows = cursor.fetchall()

            if not rows:
                return f"No se encontraron eventos con '{query}'."

            lines = [f"🔍 Eventos encontrados para '{query}':\n"]
            for eid, title, start, desc in rows:
                dt = datetime.datetime.fromisoformat(start)
                date_str = dt.strftime("%d/%m/%Y %H:%M")
                lines.append(f"  [{eid}] {date_str} — {title}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error buscando eventos: {e}"

    # ─── Recordatorios ────────────────────────────────────────

    def start_reminders(self, callback: Callable[[str], None] = None) -> None:
        """Inicia el servicio de recordatorios."""
        if self._reminder_thread and self._reminder_thread.is_alive():
            return

        if callback:
            self._on_reminder = callback

        self._stop_event.clear()
        self._reminder_thread = threading.Thread(
            target=self._reminder_loop, daemon=True
        )
        self._reminder_thread.start()
        logger.info("Servicio de recordatorios iniciado.")

    def stop_reminders(self) -> None:
        """Detiene el servicio de recordatorios."""
        self._stop_event.set()
        if self._reminder_thread:
            self._reminder_thread.join(timeout=5)

    def _reminder_loop(self) -> None:
        """Bucle de verificación de recordatorios."""
        while not self._stop_event.is_set():
            try:
                now = datetime.datetime.now()
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT id, title, start_time, reminder_minutes "
                        "FROM events "
                        "WHERE reminded = 0 AND start_time > ?",
                        (now.isoformat(),),
                    )
                    for eid, title, start_str, reminder_min in cursor.fetchall():
                        start_dt = datetime.datetime.fromisoformat(start_str)
                        delta = start_dt - now
                        minutes_until = delta.total_seconds() / 60

                        if 0 < minutes_until <= reminder_min:
                            # Enviar recordatorio
                            if minutes_until < 1:
                                time_msg = "¡ahora!"
                            elif minutes_until < 60:
                                time_msg = f"en {int(minutes_until)} minutos"
                            else:
                                hours = int(minutes_until // 60)
                                mins = int(minutes_until % 60)
                                time_msg = f"en {hours}h {mins}m"

                            msg = f"📅 Recordatorio: '{title}' {time_msg}"
                            logger.info(msg)

                            if self._on_reminder:
                                self._on_reminder(msg)

                            # Marcar como recordado
                            conn.execute(
                                "UPDATE events SET reminded = 1 WHERE id = ?",
                                (eid,),
                            )
                            conn.commit()

            except Exception as e:
                logger.debug(f"Error en bucle de recordatorios: {e}")

            self._stop_event.wait(timeout=30)

    # ─── Helpers ──────────────────────────────────────────────

    def _parse_datetime(self, text: str) -> Optional[datetime.datetime]:
        """
        Parsea texto de fecha/hora en múltiples formatos.
        Soporta: HH:MM, YYYY-MM-DD HH:MM, DD/MM/YYYY HH:MM,
                  mañana HH:MM, hoy HH:MM, en X minutos/horas.
        """
        text = text.strip().lower()

        if not text:
            return None

        now = datetime.datetime.now()

        # "en X minutos"
        import re
        m = re.match(r"en\s+(\d+)\s*min(?:utos?)?", text)
        if m:
            return now + datetime.timedelta(minutes=int(m.group(1)))

        # "en X horas"
        m = re.match(r"en\s+(\d+)\s*h(?:oras?)?", text)
        if m:
            return now + datetime.timedelta(hours=int(m.group(1)))

        # "mañana HH:MM" / "mañana a las HH:MM"
        m = re.match(r"mañana\s+(?:a\s+las?\s+)?(\d{1,2})[:\.](\d{2})", text)
        if m:
            tomorrow = now + datetime.timedelta(days=1)
            return tomorrow.replace(
                hour=int(m.group(1)), minute=int(m.group(2)),
                second=0, microsecond=0,
            )

        # "hoy HH:MM" / "hoy a las HH:MM"
        m = re.match(r"(?:hoy\s+)?(?:a\s+las?\s+)?(\d{1,2})[:\.](\d{2})", text)
        if m:
            return now.replace(
                hour=int(m.group(1)), minute=int(m.group(2)),
                second=0, microsecond=0,
            )

        # Formatos estándar
        formats = [
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%dT%H:%M",
            "%d-%m-%Y %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.datetime.strptime(text, fmt)
            except ValueError:
                continue

        return None

    def _get_events_for_date(self, date: datetime.date) -> str:
        """Obtiene eventos para una fecha específica."""
        start = datetime.datetime.combine(date, datetime.time.min).isoformat()
        end = datetime.datetime.combine(date, datetime.time.max).isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id, title, start_time, end_time, location "
                    "FROM events "
                    "WHERE start_time BETWEEN ? AND ? "
                    "ORDER BY start_time ASC",
                    (start, end),
                )
                rows = cursor.fetchall()

            if not rows:
                day_name = self._day_name(date)
                return f"No tiene eventos para {day_name}, señor."

            day_name = self._day_name(date)
            lines = [f"📅 Eventos para {day_name}:\n"]
            for eid, title, start_str, end_str, loc in rows:
                dt = datetime.datetime.fromisoformat(start_str)
                time_str = dt.strftime("%H:%M")
                loc_str = f" 📍 {loc}" if loc else ""
                lines.append(f"  [{eid}] {time_str} — {title}{loc_str}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    def _get_events_range(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> str:
        """Obtiene eventos en un rango de fechas."""
        start = datetime.datetime.combine(
            start_date, datetime.time.min
        ).isoformat()
        end = datetime.datetime.combine(
            end_date, datetime.time.max
        ).isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id, title, start_time, end_time, location "
                    "FROM events "
                    "WHERE start_time BETWEEN ? AND ? "
                    "ORDER BY start_time ASC",
                    (start, end),
                )
                rows = cursor.fetchall()

            if not rows:
                return "No tiene eventos para esta semana, señor."

            lines = ["📅 Eventos de esta semana:\n"]
            current_day = None
            for eid, title, start_str, end_str, loc in rows:
                dt = datetime.datetime.fromisoformat(start_str)
                day = dt.date()
                if day != current_day:
                    current_day = day
                    day_name = self._day_name(day)
                    lines.append(f"\n  {day_name}:")

                time_str = dt.strftime("%H:%M")
                loc_str = f" 📍 {loc}" if loc else ""
                lines.append(f"    [{eid}] {time_str} — {title}{loc_str}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def _day_name(date: datetime.date) -> str:
        """Obtiene el nombre del día en español."""
        days = ["lunes", "martes", "miércoles", "jueves",
                "viernes", "sábado", "domingo"]
        months = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre",
            "diciembre",
        ]
        return (
            f"{days[date.weekday()]} {date.day} de "
            f"{months[date.month - 1]}"
        )

    def cleanup(self) -> None:
        """Limpieza al cerrar."""
        self.stop_reminders()
