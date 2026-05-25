from unittest.mock import patch, MagicMock
from modules.script_writer import rewrite_as_script


def test_rewrite_returns_string():
    mock_response = MagicMock()
    mock_response.text = "Hook: You won't believe what happened...\n\nSo there I was..."

    with patch("modules.script_writer.genai.GenerativeModel") as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.generate_content.return_value = mock_response

        result = rewrite_as_script(
            title="I told my boss I hated him",
            body="This happened last Tuesday..."
        )

    assert isinstance(result, str)
    assert len(result) > 50


def test_rewrite_raises_on_empty_response():
    mock_response = MagicMock()
    mock_response.text = ""

    with patch("modules.script_writer.genai.GenerativeModel") as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.generate_content.return_value = mock_response

        try:
            rewrite_as_script(title="Test", body="Test body")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
