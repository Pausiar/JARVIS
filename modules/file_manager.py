"""
J.A.R.V.I.S. — File Manager Module
Gestión de archivos y carpetas del sistema.
"""

import os
import shutil
import logging
import subprocess
import zipfile
import tarfile
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger("jarvis.file_manager")


class FileManager:
    """Gestiona archivos y carpetas del sistema."""

    def __init__(self):
        self.desktop = Path.home() / "Desktop"
        self.documents = Path.home() / "Documents"
        self.downloads = Path.home() / "Downloads"
        logger.info("FileManager inicializado.")

    # ─── Abrir archivos ───────────────────────────────────────

    def open_file(self, file_path: str) -> str:
        """Abre un archivo con la aplicación predeterminada."""
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"No se encontró el archivo: {file_path}"
        try:
            os.startfile(str(path))
            return f"Archivo abierto: {path.name}"
        except Exception as e:
            logger.error(f"Error abriendo archivo: {e}")
            return f"Error al abrir el archivo: {e}"

    # ─── Crear archivos y carpetas ────────────────────────────

    def create_file(self, file_path: str, content: str = "") -> str:
        """Crea un nuevo archivo con contenido opcional."""
        path = self._resolve_path(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"Archivo creado: {path}"
        except Exception as e:
            logger.error(f"Error creando archivo: {e}")
            return f"Error al crear el archivo: {e}"

    def create_directory(self, dir_name: str, base_path: str = None) -> str:
        """Crea una nueva carpeta."""
        if base_path:
            path = Path(base_path) / dir_name
        else:
            path = self.desktop / dir_name
        try:
            path.mkdir(parents=True, exist_ok=True)
            return f"Carpeta creada: {path}"
        except Exception as e:
            logger.error(f"Error creando carpeta: {e}")
            return f"Error al crear la carpeta: {e}"

    # ─── Mover, copiar, renombrar ─────────────────────────────

    def move_file(self, source: str, destination: str) -> str:
        """Mueve un archivo o carpeta a otra ubicación."""
        src = self._resolve_path(source)
        dst = self._resolve_path(destination)
        if not src.exists():
            return f"No se encontró: {source}"
        try:
            shutil.move(str(src), str(dst))
            return f"Movido: {src.name} → {dst}"
        except Exception as e:
            logger.error(f"Error moviendo: {e}")
            return f"Error al mover: {e}"

    def copy_file(self, source: str, destination: str) -> str:
        """Copia un archivo o carpeta."""
        src = self._resolve_path(source)
        dst = self._resolve_path(destination)
        if not src.exists():
            return f"No se encontró: {source}"
        try:
            if src.is_dir():
                shutil.copytree(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
            return f"Copiado: {src.name} → {dst}"
        except Exception as e:
            logger.error(f"Error copiando: {e}")
            return f"Error al copiar: {e}"

    def rename_file(self, file_path: str, new_name: str) -> str:
        """Renombra un archivo o carpeta."""
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"No se encontró: {file_path}"
        try:
            new_path = path.parent / new_name
            path.rename(new_path)
            return f"Renombrado: {path.name} → {new_name}"
        except Exception as e:
            logger.error(f"Error renombrando: {e}")
            return f"Error al renombrar: {e}"

    # ─── Eliminar ─────────────────────────────────────────────

    def delete_file(self, file_path: str) -> str:
        """Elimina un archivo o carpeta (a la papelera si es posible)."""
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"No se encontró: {file_path}"
        try:
            # Intentar enviar a la papelera
            try:
                from send2trash import send2trash
                send2trash(str(path))
                return f"Enviado a la papelera: {path.name}"
            except ImportError:
                pass

            # Eliminación directa
            if path.is_dir():
                shutil.rmtree(str(path))
            else:
                path.unlink()
            return f"Eliminado: {path.name}"
        except Exception as e:
            logger.error(f"Error eliminando: {e}")
            return f"Error al eliminar: {e}"

    # ─── Búsqueda ─────────────────────────────────────────────

    def search_files(
        self, query: str, directory: str = None, max_results: int = 20
    ) -> str:
        """Busca archivos por nombre en el sistema."""
        search_dir = Path(directory) if directory else Path.home()
        results = []

        try:
            for item in search_dir.rglob(f"*{query}*"):
                if len(results) >= max_results:
                    break
                # Saltar directorios del sistema
                parts_lower = [p.lower() for p in item.parts]
                if any(skip in parts_lower for skip in [
                    "appdata", ".git", "node_modules", "__pycache__",
                    "windows", "program files", "programdata",
                ]):
                    continue
                results.append(str(item))
        except PermissionError:
            pass
        except Exception as e:
            logger.error(f"Error buscando: {e}")

        if results:
            result_text = "\n".join(f"  • {r}" for r in results)
            return f"Encontrados {len(results)} resultados:\n{result_text}"
        return f"No se encontraron archivos con '{query}'."

    # ─── Organización automática ──────────────────────────────

    def organize_files(self, directory: str = None) -> str:
        """Organiza archivos por tipo en carpetas."""
        dir_path = Path(directory) if directory else self.downloads

        if not dir_path.exists():
            return f"Directorio no encontrado: {directory}"

        categories = {
            "Imágenes": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
            "Documentos": [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls", ".pptx", ".csv", ".md"],
            "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
            "Música": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
            "Archivos": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
            "Programas": [".exe", ".msi", ".bat", ".cmd", ".ps1"],
            "Código": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".h", ".json"],
        }

        moved_count = 0
        try:
            for file in dir_path.iterdir():
                if file.is_file():
                    ext = file.suffix.lower()
                    for category, extensions in categories.items():
                        if ext in extensions:
                            cat_dir = dir_path / category
                            cat_dir.mkdir(exist_ok=True)
                            new_path = cat_dir / file.name
                            if not new_path.exists():
                                shutil.move(str(file), str(new_path))
                                moved_count += 1
                            break
        except Exception as e:
            logger.error(f"Error organizando: {e}")
            return f"Error organizando archivos: {e}"

        return f"Archivos organizados: {moved_count} archivos movidos en {dir_path}."

    # ─── Compresión ───────────────────────────────────────────

    def compress(self, source: str, output: str = None, format: str = "zip") -> str:
        """Comprime archivos o carpetas."""
        src = self._resolve_path(source)
        if not src.exists():
            return f"No se encontró: {source}"

        if output:
            out_path = self._resolve_path(output)
        else:
            out_path = src.parent / f"{src.stem}.{format}"

        try:
            if format == "zip":
                with zipfile.ZipFile(str(out_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                    if src.is_dir():
                        for file in src.rglob("*"):
                            zf.write(file, file.relative_to(src.parent))
                    else:
                        zf.write(str(src), src.name)
            elif format in ("tar", "tar.gz", "tgz"):
                mode = "w:gz" if format in ("tar.gz", "tgz") else "w"
                with tarfile.open(str(out_path), mode) as tf:
                    tf.add(str(src), arcname=src.name)
            else:
                return f"Formato no soportado: {format}"

            return f"Comprimido: {out_path}"
        except Exception as e:
            logger.error(f"Error comprimiendo: {e}")
            return f"Error al comprimir: {e}"

    def decompress(self, archive: str, destination: str = None) -> str:
        """Descomprime un archivo."""
        src = self._resolve_path(archive)
        if not src.exists():
            return f"No se encontró: {archive}"

        dst = Path(destination) if destination else src.parent / src.stem

        try:
            if src.suffix == ".zip":
                with zipfile.ZipFile(str(src), 'r') as zf:
                    zf.extractall(str(dst))
            elif src.suffix in (".tar", ".gz", ".tgz", ".bz2"):
                with tarfile.open(str(src), 'r:*') as tf:
                    tf.extractall(str(dst))
            else:
                return f"Formato no soportado: {src.suffix}"

            return f"Descomprimido en: {dst}"
        except Exception as e:
            logger.error(f"Error descomprimiendo: {e}")
            return f"Error al descomprimir: {e}"

    # ─── Información de archivos ──────────────────────────────

    def file_info(self, file_path: str) -> str:
        """Obtiene información detallada de un archivo."""
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"No se encontró: {file_path}"

        try:
            stat = path.stat()
            size = self._format_size(stat.st_size)
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%d/%m/%Y %H:%M")

            info = (
                f"📄 {path.name}\n"
                f"  Ruta: {path}\n"
                f"  Tamaño: {size}\n"
                f"  Tipo: {'Carpeta' if path.is_dir() else path.suffix or 'Archivo'}\n"
                f"  Modificado: {modified}\n"
                f"  Creado: {created}"
            )
            return info
        except Exception as e:
            return f"Error obteniendo información: {e}"

    def list_directory(self, directory: str = None) -> str:
        """Lista el contenido de un directorio."""
        dir_path = Path(directory) if directory else self.desktop
        if not dir_path.exists():
            return f"Directorio no encontrado: {directory}"

        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            lines = []
            for item in items[:50]:
                icon = "📁" if item.is_dir() else "📄"
                size = ""
                if item.is_file():
                    size = f" ({self._format_size(item.stat().st_size)})"
                lines.append(f"  {icon} {item.name}{size}")

            count = len(list(dir_path.iterdir()))
            header = f"📂 {dir_path} ({count} elementos):"
            return header + "\n" + "\n".join(lines)
        except Exception as e:
            return f"Error listando directorio: {e}"

    # ─── Utilidades ───────────────────────────────────────────

    def _resolve_path(self, file_path: str) -> Path:
        """Resuelve una ruta relativa o con alias."""
        path = Path(file_path)
        if path.is_absolute():
            return path

        # Intentar en ubicaciones comunes
        for base in [Path.cwd(), self.desktop, self.documents, self.downloads]:
            candidate = base / file_path
            if candidate.exists():
                return candidate

        # Devolver la ruta relativa al escritorio
        return self.desktop / file_path

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Formatea un tamaño en bytes a formato legible."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
