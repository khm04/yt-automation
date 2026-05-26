from gtts import gTTS
import subprocess
import os


def generate_voice(text: str, output_path: str) -> str:
    """Generate voice audio using gTTS (Google TTS — free, no blocks in CI)."""
    if not text.strip():
        raise ValueError("Script cannot be empty")

    # gTTS outputs mp3 directly
    tts = gTTS(text=text, lang="en", tld="com", slow=False)
    tts.save(output_path)
    return output_path
