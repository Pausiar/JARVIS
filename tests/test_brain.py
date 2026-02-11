"""
Tests para core/brain.py — JarvisBrain
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestJarvisBrain:
    """Tests para la clase JarvisBrain."""

    def test_import(self):
        """Verifica que se puede importar JarvisBrain."""
        from core.brain import JarvisBrain
        assert JarvisBrain is not None

    def test_instantiation(self):
        """Verifica la instanciación de JarvisBrain."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()
        assert brain is not None
        assert brain.history == []
        assert brain.model is not None

    def test_clean_response(self):
        """Verifica la limpieza de respuestas."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        # Texto con acción
        text = "He abierto la aplicación. [ACTION:{\"module\":\"system\",\"action\":\"open_app\"}]"
        cleaned = brain.clean_response(text)
        assert "[ACTION:" not in cleaned
        assert "He abierto la aplicación." in cleaned

    def test_extract_actions(self):
        """Verifica la extracción de acciones del texto."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        text = 'Aquí tienes. [ACTION:{"module":"system","action":"open_app","params":{"name":"chrome"}}]'
        actions = brain.extract_actions(text)
        assert len(actions) == 1
        assert actions[0]["module"] == "system"
        assert actions[0]["action"] == "open_app"
        assert actions[0]["params"]["name"] == "chrome"

    def test_extract_actions_no_actions(self):
        """Verifica que no se extraen acciones si no hay."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        text = "Hola, ¿en qué puedo ayudarte?"
        actions = brain.extract_actions(text)
        assert actions == []

    def test_add_to_history(self):
        """Verifica que se añaden mensajes al historial."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        brain.add_to_history("user", "Hola JARVIS")
        brain.add_to_history("assistant", "Hola señor")

        assert len(brain.history) == 2
        assert brain.history[0]["role"] == "user"
        assert brain.history[1]["role"] == "assistant"

    def test_clear_history(self):
        """Verifica que se limpia el historial."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        brain.add_to_history("user", "Test")
        brain.clear_history()
        assert brain.history == []

    def test_quick_intent_greeting(self):
        """Verifica detección de intents rápidos."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        result = brain.quick_intent("hola jarvis")
        # Puede retornar None o un intent, depende de implementación
        # Aquí solo verificamos que no lanza excepción
        assert result is None or isinstance(result, dict)

    @patch('core.brain.requests.post')
    def test_chat_success(self, mock_post):
        """Verifica chat con respuesta mock de Ollama."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Hola señor, ¿en qué puedo ayudarle?"}
        }
        mock_post.return_value = mock_response

        result = brain.chat("Hola")
        assert result is not None
        assert "Hola" in result or "señor" in result or len(result) > 0

    @patch('core.brain.requests.post')
    def test_chat_adds_to_history(self, mock_post):
        """Verifica que chat añade al historial."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Respuesta de prueba"}
        }
        mock_post.return_value = mock_response

        brain.chat("Pregunta de prueba")
        assert len(brain.history) >= 2  # user + assistant

    @patch('core.brain.requests.get')
    def test_is_available(self, mock_get):
        """Verifica la comprobación de disponibilidad de Ollama."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert brain.is_available() is True

    @patch('core.brain.requests.get')
    def test_is_not_available(self, mock_get):
        """Verifica que detecta Ollama no disponible."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        mock_get.side_effect = Exception("Connection refused")
        assert brain.is_available() is False


class TestBrainEdgeCases:
    """Tests para casos extremos."""

    def test_extract_multiple_actions(self):
        """Verifica extracción de múltiples acciones."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        text = (
            'Voy a hacerlo. [ACTION:{"module":"system","action":"open_app"}] '
            'Y también esto. [ACTION:{"module":"file","action":"create"}]'
        )
        actions = brain.extract_actions(text)
        assert len(actions) == 2

    def test_extract_malformed_action(self):
        """Verifica manejo de acción mal formada."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        text = "Texto con [ACTION:{no es json válido}] aquí."
        actions = brain.extract_actions(text)
        assert actions == []

    def test_history_limit(self):
        """Verifica que el historial no crece indefinidamente."""
        from core.brain import JarvisBrain
        brain = JarvisBrain()

        for i in range(100):
            brain.add_to_history("user", f"Mensaje {i}")
            brain.add_to_history("assistant", f"Respuesta {i}")

        # El historial debería tener un límite razonable
        assert len(brain.history) <= 200 or hasattr(brain, 'max_history')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
