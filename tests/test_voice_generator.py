import os
from unittest.mock import patch, MagicMock
from modules.voice_generator import generate_voice


def test_generate_voice_saves_mp3(tmp_path):
    fake_audio = b"fake_mp3_bytes"

    with patch("modules.voice_generator.ElevenLabs") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.text_to_speech.convert.return_value = iter([fake_audio])

        output_path = str(tmp_path / "test_voice.mp3")
        result = generate_voice("Hello this is a test script.", output_path)

    assert result == output_path
    assert os.path.exists(output_path)


def test_generate_voice_raises_on_empty_script():
    try:
        generate_voice("", "output/test.mp3")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
