from unittest.mock import patch, MagicMock
from modules.uploader import upload_to_youtube


def test_upload_returns_video_id():
    mock_youtube = MagicMock()
    mock_request = MagicMock()
    mock_youtube.videos.return_value.insert.return_value = mock_request
    mock_request.next_chunk.return_value = (None, {"id": "abc123xyz"})

    with patch("modules.uploader.build_youtube_client", return_value=mock_youtube), \
         patch("modules.uploader.MediaFileUpload") as mock_media:
        mock_media.return_value = MagicMock()
        video_id = upload_to_youtube(
            video_path="output/test.mp4",
            title="Test Video Title",
            description="Test description",
            tags=["test", "reddit", "story"]
        )

    assert video_id == "abc123xyz"
