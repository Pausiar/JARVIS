"""
J.A.R.V.I.S. — Memory Module
Memoria persistente y contexto usando SQLite.
"""

import json
import sqlite3
import logging
import datetime
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MEMORY_DB

logger = logging.getLogger("jarvis.memory")


class Memory:
    """Sistema de memoria persistente para JARVIS usando SQLite."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(MEMORY_DB)
        self._init_db()
        logger.info(f"Memory inicializado: {self.db_path}")

    def _init_db(self) -> None:
        """Inicializa la base de datos y las tablas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Tabla de conversaciones
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT
                    )
                """)

                # Tabla de preferencias del usuario
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS preferences (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Tabla de hechos / notas
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS facts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT,
                        content TEXT NOT NULL,
                        source TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Tabla de archivos procesados
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processed_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        file_name TEXT,
                        file_type TEXT,
                        summary TEXT,
                        processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Tabla de correcciones del usuario (aprendizaje)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS corrections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_input TEXT NOT NULL,
                        wrong_action TEXT,
                        correct_action TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        times_applied INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.commit()
                logger.info("Base de datos inicializada.")

        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")

    # ─── Conversaciones ───────────────────────────────────────

    def save_message(self, role: str, content: str, session_id: str = None) -> None:
        """Guarda un mensaje en el historial."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO conversations (role, content, session_id) VALUES (?, ?, ?)",
                    (role, content, session_id),
                )
        except Exception as e:
            logger.error(f"Error guardando mensaje: {e}")

    def get_recent_messages(self, limit: int = 20) -> list[dict]:
        """Obtiene los mensajes más recientes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT role, content, timestamp FROM conversations "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                messages = [
                    {"role": r[0], "content": r[1], "timestamp": r[2]}
                    for r in reversed(rows)
                ]
                return messages
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}")
            return []

    def get_conversation_history(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        """Obtiene el historial completo de conversación."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT role, content, timestamp FROM conversations "
                    "ORDER BY id DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                rows = cursor.fetchall()
                return [
                    {"role": r[0], "content": r[1], "timestamp": r[2]}
                    for r in reversed(rows)
                ]
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return []

    def search_conversations(self, query: str, limit: int = 10) -> list[dict]:
        """Busca en el historial de conversaciones."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT role, content, timestamp FROM conversations "
                    "WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                    (f"%{query}%", limit),
                )
                rows = cursor.fetchall()
                return [
                    {"role": r[0], "content": r[1], "timestamp": r[2]}
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Error buscando en conversaciones: {e}")
            return []

    # ─── Preferencias del usuario ─────────────────────────────

    def set_preference(self, key: str, value: str) -> None:
        """Guarda una preferencia del usuario."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO preferences (key, value, updated_at) "
                    "VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (key, value),
                )
        except Exception as e:
            logger.error(f"Error guardando preferencia: {e}")

    def get_preference(self, key: str, default: str = None) -> Optional[str]:
        """Obtiene una preferencia del usuario."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT value FROM preferences WHERE key = ?",
                    (key,),
                )
                row = cursor.fetchone()
                return row[0] if row else default
        except Exception as e:
            logger.error(f"Error obteniendo preferencia: {e}")
            return default

    def get_all_preferences(self) -> dict:
        """Obtiene todas las preferencias."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT key, value FROM preferences")
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Error obteniendo preferencias: {e}")
            return {}

    # ─── Hechos / Notas ──────────────────────────────────────

    def save_fact(self, content: str, category: str = "general", source: str = None) -> None:
        """Guarda un hecho o nota."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO facts (category, content, source) VALUES (?, ?, ?)",
                    (category, content, source),
                )
        except Exception as e:
            logger.error(f"Error guardando hecho: {e}")

    def recall(self, query: str, limit: int = 5) -> str:
        """
        Busca en la memoria (conversaciones, hechos, archivos procesados).

        Args:
            query: Búsqueda.
            limit: Máximo de resultados.

        Returns:
            Resultados formateados como texto.
        """
        results = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Buscar en conversaciones
                cursor = conn.execute(
                    "SELECT role, content, timestamp FROM conversations "
                    "WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                    (f"%{query}%", limit),
                )
                convs = cursor.fetchall()
                if convs:
                    results.append("📝 Conversaciones encontradas:")
                    for role, content, ts in convs:
                        short = content[:150] + "..." if len(content) > 150 else content
                        results.append(f"  [{ts}] {role}: {short}")

                # Buscar en hechos
                cursor = conn.execute(
                    "SELECT content, category, created_at FROM facts "
                    "WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                    (f"%{query}%", limit),
                )
                facts = cursor.fetchall()
                if facts:
                    results.append("\n🧠 Notas/hechos encontrados:")
                    for content, cat, ts in facts:
                        results.append(f"  [{cat}] {content}")

                # Buscar en archivos procesados
                cursor = conn.execute(
                    "SELECT file_name, summary, processed_at FROM processed_files "
                    "WHERE file_name LIKE ? OR summary LIKE ? ORDER BY id DESC LIMIT ?",
                    (f"%{query}%", f"%{query}%", limit),
                )
                files = cursor.fetchall()
                if files:
                    results.append("\n📂 Archivos procesados:")
                    for fname, summary, ts in files:
                        results.append(f"  [{ts}] {fname}: {summary[:100]}")

        except Exception as e:
            logger.error(f"Error en recall: {e}")

        if results:
            return "\n".join(results)
        return f"No encontré nada relacionado con '{query}' en mi memoria, señor."

    # ─── Correcciones / Aprendizaje ──────────────────────────

    def save_correction(
        self,
        user_input: str,
        wrong_action: str,
        correct_action: str,
        category: str = "general",
    ) -> None:
        """
        Guarda una corrección del usuario para aprender del error.
        Ej: usuario dijo "abre google" y JARVIS buscó en Google,
        pero el usuario quería abrir la app Google Chrome.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Comprobar si ya existe una corrección similar
                cursor = conn.execute(
                    "SELECT id, times_applied FROM corrections "
                    "WHERE user_input LIKE ? AND correct_action = ?",
                    (f"%{user_input}%", correct_action),
                )
                row = cursor.fetchone()
                if row:
                    conn.execute(
                        "UPDATE corrections SET times_applied = times_applied + 1 "
                        "WHERE id = ?",
                        (row[0],),
                    )
                else:
                    conn.execute(
                        "INSERT INTO corrections "
                        "(user_input, wrong_action, correct_action, category) "
                        "VALUES (?, ?, ?, ?)",
                        (user_input, wrong_action, correct_action, category),
                    )
            logger.info(f"Corrección guardada: '{user_input}' → '{correct_action}'")
        except Exception as e:
            logger.error(f"Error guardando corrección: {e}")

    def get_corrections(self, user_input: str, limit: int = 5) -> list[dict]:
        """
        Busca correcciones previas relevantes para un input del usuario.
        Devuelve las correcciones más relevantes ordenadas por frecuencia.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Buscar correcciones que coincidan con el input
                cursor = conn.execute(
                    "SELECT user_input, wrong_action, correct_action, "
                    "times_applied FROM corrections "
                    "WHERE user_input LIKE ? "
                    "ORDER BY times_applied DESC LIMIT ?",
                    (f"%{user_input}%", limit),
                )
                return [
                    {
                        "user_input": r[0],
                        "wrong_action": r[1],
                        "correct_action": r[2],
                        "times_applied": r[3],
                    }
                    for r in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error buscando correcciones: {e}")
            return []

    def get_all_corrections(self) -> str:
        """Muestra todas las correcciones guardadas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT user_input, wrong_action, correct_action, "
                    "times_applied, created_at FROM corrections "
                    "ORDER BY times_applied DESC"
                )
                rows = cursor.fetchall()

            if not rows:
                return "No hay correcciones guardadas, señor."

            lines = ["📝 Correcciones aprendidas:\n"]
            for inp, wrong, correct, count, ts in rows:
                lines.append(
                    f"  • \"{inp}\" → {correct} "
                    f"(aplicada {count}x)"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    def clear_corrections(self) -> str:
        """Elimina todas las correcciones."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM corrections")
                conn.commit()
            return "Correcciones eliminadas."
        except Exception as e:
            return f"Error: {e}"

    # ─── Archivos procesados ──────────────────────────────────

    def save_processed_file(
        self, file_path: str, summary: str, file_type: str = None
    ) -> None:
        """Registra un archivo procesado."""
        try:
            path = Path(file_path)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO processed_files (file_path, file_name, file_type, summary) "
                    "VALUES (?, ?, ?, ?)",
                    (str(path), path.name, file_type or path.suffix, summary),
                )
        except Exception as e:
            logger.error(f"Error guardando archivo procesado: {e}")

    # ─── Limpieza ─────────────────────────────────────────────

    def clear_memory(self) -> str:
        """Limpia toda la memoria (conversaciones y hechos)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM conversations")
                conn.execute("DELETE FROM facts")
                conn.execute("DELETE FROM processed_files")
                conn.commit()
            logger.info("Memoria limpiada completamente.")
            return "Memoria limpiada completamente, señor."
        except Exception as e:
            logger.error(f"Error limpiando memoria: {e}")
            return f"Error al limpiar la memoria: {e}"

    def clear_conversations(self) -> str:
        """Limpia solo las conversaciones."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM conversations")
                conn.commit()
            return "Historial de conversaciones eliminado."
        except Exception as e:
            return f"Error: {e}"

    def get_stats(self) -> str:
        """Obtiene estadísticas de la memoria."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                msgs = conn.execute(
                    "SELECT COUNT(*) FROM conversations"
                ).fetchone()[0]
                facts = conn.execute(
                    "SELECT COUNT(*) FROM facts"
                ).fetchone()[0]
                files = conn.execute(
                    "SELECT COUNT(*) FROM processed_files"
                ).fetchone()[0]
                prefs = conn.execute(
                    "SELECT COUNT(*) FROM preferences"
                ).fetchone()[0]

            return (
                f"🧠 Estadísticas de memoria:\n"
                f"  Mensajes: {msgs}\n"
                f"  Hechos/notas: {facts}\n"
                f"  Archivos procesados: {files}\n"
                f"  Preferencias: {prefs}"
            )
        except Exception as e:
            return f"Error obteniendo estadísticas: {e}"
