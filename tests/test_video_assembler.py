import pytest
from modules.video_assembler import get_random_gameplay_segment, build_subtitle_file


def test_get_random_gameplay_segment_returns_valid_times():
    start, end = get_random_gameplay_segment(total_duration=3600, clip_duration=75)
    assert end - start == pytest.approx(75)
    assert start >= 0
    assert end <= 3600


def test_build_subtitle_file_creates_srt(tmp_path):
    script = "You will not believe this story. It happened last Tuesday."
    audio_duration = 10.0
    srt_path = str(tmp_path / "captions.srt")

    result = build_subtitle_file(script, audio_duration, srt_path)

    assert result == srt_path
    with open(srt_path) as f:
        content = f.read()
    assert "1" in content
    assert "-->" in content
