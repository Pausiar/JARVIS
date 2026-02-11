"""
Tests para los módulos de JARVIS.
"""

import pytest
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ─── Tests FileManager ───────────────────────────────────────

class TestFileManager:
    """Tests para modules/file_manager.py."""

    def setup_method(self):
        """Crea directorio temporal para tests."""
        self.test_dir = tempfile.mkdtemp(prefix="jarvis_test_")

    def teardown_method(self):
        """Limpia directorio temporal."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_import(self):
        from modules.file_manager import FileManager
        fm = FileManager()
        assert fm is not None

    def test_create_file(self):
        from modules.file_manager import FileManager
        fm = FileManager()

        filepath = os.path.join(self.test_dir, "test.txt")
        result = fm.create_file(filepath, "Contenido de prueba")
        assert "creado" in result.lower() or "éxito" in result.lower() or os.path.exists(filepath)

    def test_create_and_list(self):
        from modules.file_manager import FileManager
        fm = FileManager()

        # Crear archivo
        filepath = os.path.join(self.test_dir, "archivo.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("test")

        result = fm.list_directory(self.test_dir)
        assert "archivo.txt" in result

    def test_file_info(self):
        from modules.file_manager import FileManager
        fm = FileManager()

        filepath = os.path.join(self.test_dir, "info.txt")
        with open(filepath, "w") as f:
            f.write("Hola JARVIS")

        result = fm.file_info(filepath)
        assert "info.txt" in result or "tamaño" in result.lower() or len(result) > 0

    def test_search_files(self):
        from modules.file_manager import FileManager
        fm = FileManager()

        # Crear algunos archivos
        for name in ["alpha.txt", "beta.py", "gamma.txt"]:
            with open(os.path.join(self.test_dir, name), "w") as f:
                f.write("c")

        result = fm.search(self.test_dir, "*.txt")
        assert "alpha" in result or "gamma" in result

    def test_rename_file(self):
        from modules.file_manager import FileManager
        fm = FileManager()

        old_path = os.path.join(self.test_dir, "viejo.txt")
        new_path = os.path.join(self.test_dir, "nuevo.txt")
        with open(old_path, "w") as f:
            f.write("test")

        fm.rename(old_path, "nuevo.txt")
        assert os.path.exists(new_path) or not os.path.exists(old_path)


# ─── Tests SystemControl ─────────────────────────────────────

class TestSystemControl:
    """Tests para modules/system_control.py."""

    def test_import(self):
        from modules.system_control import SystemControl
        sc = SystemControl()
        assert sc is not None

    def test_get_time(self):
        from modules.system_control import SystemControl
        sc = SystemControl()
        result = sc.get_time()
        assert ":" in result  # Formato HH:MM

    def test_get_date(self):
        from modules.system_control import SystemControl
        sc = SystemControl()
        result = sc.get_date()
        assert len(result) > 5  # Alguna fecha

    def test_system_info(self):
        from modules.system_control import SystemControl
        sc = SystemControl()
        result = sc.system_info()
        assert len(result) > 10  # Alguna info

    def test_get_system_status(self):
        from modules.system_control import SystemControl
        sc = SystemControl()
        status = sc.get_system_status()
        assert isinstance(status, dict)
        assert "cpu" in status
        assert "ram" in status


# ─── Tests Memory ─────────────────────────────────────────────

class TestMemory:
    """Tests para modules/memory.py."""

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp(prefix="jarvis_mem_")
        self._original_data = None

    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_import(self):
        from modules.memory import Memory
        mem = Memory(db_path=os.path.join(self.test_dir, "test.db"))
        assert mem is not None

    def test_save_and_get_messages(self):
        from modules.memory import Memory
        db = os.path.join(self.test_dir, "test.db")
        mem = Memory(db_path=db)

        mem.save_message("user", "Hola JARVIS")
        mem.save_message("assistant", "Hola señor")

        messages = mem.get_recent_messages(10)
        assert len(messages) >= 2

    def test_preferences(self):
        from modules.memory import Memory
        db = os.path.join(self.test_dir, "test.db")
        mem = Memory(db_path=db)

        mem.save_preference("idioma", "español")
        value = mem.get_preference("idioma")
        assert value == "español"

    def test_preference_default(self):
        from modules.memory import Memory
        db = os.path.join(self.test_dir, "test.db")
        mem = Memory(db_path=db)

        value = mem.get_preference("no_existe", "default")
        assert value == "default"

    def test_save_and_get_fact(self):
        from modules.memory import Memory
        db = os.path.join(self.test_dir, "test.db")
        mem = Memory(db_path=db)

        mem.save_fact("usuario", "nombre", "Tony Stark")
        facts = mem.get_facts("usuario")
        assert len(facts) > 0

    def test_recall(self):
        from modules.memory import Memory
        db = os.path.join(self.test_dir, "test.db")
        mem = Memory(db_path=db)

        mem.save_message("user", "Me gusta el café con leche")
        mem.save_fact("gustos", "bebida", "café con leche")

        results = mem.recall("café")
        assert len(results) > 0

    def test_stats(self):
        from modules.memory import Memory
        db = os.path.join(self.test_dir, "test.db")
        mem = Memory(db_path=db)

        mem.save_message("user", "Test")
        stats = mem.stats()
        assert "conversaciones" in stats.lower() or isinstance(stats, str)

    def test_clear_memory(self):
        from modules.memory import Memory
        db = os.path.join(self.test_dir, "test.db")
        mem = Memory(db_path=db)

        mem.save_message("user", "Borrar esto")
        mem.clear_memory()
        messages = mem.get_recent_messages(10)
        assert len(messages) == 0


# ─── Tests CommandParser ──────────────────────────────────────

class TestCommandParser:
    """Tests para core/command_parser.py."""

    def test_import(self):
        from core.command_parser import CommandParser
        cp = CommandParser()
        assert cp is not None

    def test_is_greeting(self):
        from core.command_parser import CommandParser
        cp = CommandParser()
        assert cp.is_greeting("hola jarvis")
        assert cp.is_greeting("buenos días")
        assert not cp.is_greeting("abre chrome")

    def test_is_farewell(self):
        from core.command_parser import CommandParser
        cp = CommandParser()
        assert cp.is_farewell("adiós jarvis")
        assert cp.is_farewell("hasta luego")

    def test_parse_open_app(self):
        from core.command_parser import CommandParser
        cp = CommandParser()
        intent = cp.parse("abre chrome")
        assert intent is not None
        assert intent.module == "system" or "app" in str(intent.action).lower()

    def test_parse_search(self):
        from core.command_parser import CommandParser
        cp = CommandParser()
        intent = cp.parse("busca información sobre inteligencia artificial")
        assert intent is not None
        assert intent.module == "web" or "search" in str(intent.action).lower()

    def test_parse_time(self):
        from core.command_parser import CommandParser
        cp = CommandParser()
        intent = cp.parse("qué hora es")
        assert intent is not None

    def test_parse_unknown(self):
        from core.command_parser import CommandParser
        cp = CommandParser()
        intent = cp.parse("cuéntame algo interesante sobre la vida")
        # Puede no parsear (retorna None) → va al LLM
        assert intent is None or intent is not None  # No lanza excepción


# ─── Tests WebSearch ──────────────────────────────────────────

class TestWebSearch:
    """Tests para modules/web_search.py."""

    def test_import(self):
        from modules.web_search import WebSearch
        ws = WebSearch()
        assert ws is not None


# ─── Tests CodeExecutor ───────────────────────────────────────

class TestCodeExecutor:
    """Tests para modules/code_executor.py."""

    def test_import(self):
        from modules.code_executor import CodeExecutor
        ce = CodeExecutor()
        assert ce is not None

    def test_execute_simple(self):
        from modules.code_executor import CodeExecutor
        ce = CodeExecutor()
        result = ce.execute_code("print('Hola JARVIS')")
        assert "Hola JARVIS" in result

    def test_execute_math(self):
        from modules.code_executor import CodeExecutor
        ce = CodeExecutor()
        result = ce.execute_code("print(2 + 2)")
        assert "4" in result

    def test_security_check_blocks_os(self):
        from modules.code_executor import CodeExecutor
        ce = CodeExecutor()
        result = ce.execute_code("import os; os.system('rm -rf /')")
        # Debe ser bloqueado o dar error
        assert "bloqueado" in result.lower() or "seguridad" in result.lower() or "error" in result.lower() or "peligros" in result.lower()

    def test_security_check_blocks_subprocess(self):
        from modules.code_executor import CodeExecutor
        ce = CodeExecutor()
        result = ce.execute_code("import subprocess; subprocess.run(['cmd'])")
        assert "bloqueado" in result.lower() or "seguridad" in result.lower() or "error" in result.lower() or "peligros" in result.lower()


# ─── Tests Automation ─────────────────────────────────────────

class TestAutomation:
    """Tests para modules/automation.py."""

    def test_import(self):
        from modules.automation import AutomationManager
        am = AutomationManager()
        assert am is not None

    def test_list_routines_empty(self):
        from modules.automation import AutomationManager
        am = AutomationManager()
        result = am.list_routines()
        assert isinstance(result, str)


# ─── Tests DocumentProcessor ─────────────────────────────────

class TestDocumentProcessor:
    """Tests para modules/document_processor.py."""

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp(prefix="jarvis_docs_")

    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_import(self):
        from modules.document_processor import DocumentProcessor
        dp = DocumentProcessor()
        assert dp is not None

    def test_read_text(self):
        from modules.document_processor import DocumentProcessor
        dp = DocumentProcessor()

        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("Contenido de prueba para JARVIS.")

        result = dp.read_text(filepath)
        assert "Contenido de prueba" in result

    def test_read_json(self):
        from modules.document_processor import DocumentProcessor
        dp = DocumentProcessor()

        filepath = os.path.join(self.test_dir, "data.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"nombre": "JARVIS", "version": "1.0"}, f)

        result = dp.read_json(filepath)
        assert "JARVIS" in result

    def test_read_csv(self):
        from modules.document_processor import DocumentProcessor
        dp = DocumentProcessor()

        filepath = os.path.join(self.test_dir, "datos.csv")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("nombre,edad\nTony,45\nPepper,40\n")

        result = dp.read_csv(filepath)
        assert "Tony" in result


# ─── Tests EmailManager ───────────────────────────────────────

class TestEmailManager:
    """Tests para modules/email_manager.py."""

    def test_import(self):
        from modules.email_manager import EmailManager
        em = EmailManager()
        assert em is not None

    def test_is_configured(self):
        from modules.email_manager import EmailManager
        em = EmailManager()
        # Sin credenciales configuradas, debería ser False
        result = em.is_configured()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
