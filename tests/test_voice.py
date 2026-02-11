"""
Tests para core/voice_input.py y core/voice_output.py
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─── Tests VoiceInput ─────────────────────────────────────────

class TestVoiceInput:
    """Tests para core/voice_input.py."""

    def test_import(self):
        """Verifica importación."""
        from core.voice_input import VoiceInput
        assert VoiceInput is not None

    def test_instantiation(self):
        """Verifica instanciación sin cargar modelo."""
        from core.voice_input import VoiceInput
        vi = VoiceInput()
        assert vi is not None
        assert vi.model is None  # No cargado aún

    @patch('core.voice_input.WhisperModel')
    def test_load_model(self, mock_whisper):
        """Verifica carga de modelo con mock."""
        from core.voice_input import VoiceInput
        vi = VoiceInput()

        mock_model = MagicMock()
        mock_whisper.return_value = mock_model

        vi.load_model()
        assert vi.model is not None

    @patch('core.voice_input.WhisperModel')
    def test_transcribe_returns_text(self, mock_whisper):
        """Verifica transcripción con mock."""
        from core.voice_input import VoiceInput
        vi = VoiceInput()

        # Mock del modelo
        mock_segment = MagicMock()
        mock_segment.text = "Hola JARVIS"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], MagicMock())
        mock_whisper.return_value = mock_model

        vi.load_model()
        result = vi.transcribe_audio("fake_path.wav")
        assert isinstance(result, str)


# ─── Tests VoiceOutput ────────────────────────────────────────

class TestVoiceOutput:
    """Tests para core/voice_output.py."""

    def test_import(self):
        """Verifica importación."""
        from core.voice_output import VoiceOutput
        assert VoiceOutput is not None

    def test_instantiation(self):
        """Verifica instanciación."""
        from core.voice_output import VoiceOutput
        vo = VoiceOutput()
        assert vo is not None

    def test_toggle(self):
        """Verifica toggle de TTS."""
        from core.voice_output import VoiceOutput
        vo = VoiceOutput()
        original = vo.enabled
        vo.toggle()
        assert vo.enabled != original
        vo.toggle()
        assert vo.enabled == original

    @patch('core.voice_output.pyttsx3')
    def test_initialize_pyttsx3(self, mock_pyttsx3):
        """Verifica inicialización con pyttsx3 mock."""
        from core.voice_output import VoiceOutput

        mock_engine = MagicMock()
        mock_engine.getProperty.return_value = [MagicMock()]
        mock_pyttsx3.init.return_value = mock_engine

        vo = VoiceOutput()
        vo.initialize()
        # No debería lanzar excepción


# ─── Tests de integración voz ─────────────────────────────────

class TestVoiceIntegration:
    """Tests de integración del sistema de voz."""

    def test_voice_modules_compatible(self):
        """Verifica que los módulos de voz se importan sin conflicto."""
        from core.voice_input import VoiceInput
        from core.voice_output import VoiceOutput

        vi = VoiceInput()
        vo = VoiceOutput()
        assert vi is not None
        assert vo is not None

    def test_voice_output_stop_no_error(self):
        """Verifica que stop() no da error sin estar hablando."""
        from core.voice_output import VoiceOutput
        vo = VoiceOutput()
        vo.stop()  # No debe lanzar excepción


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
