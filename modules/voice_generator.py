import asyncio
import edge_tts

VOICE = "en-US-ChristopherNeural"  # deep male voice, great for storytelling


def generate_voice(text: str, output_path: str) -> str:
    """Generate voice audio using Edge TTS (free, no API key needed)."""
    if not text.strip():
        raise ValueError("Script cannot be empty")
    asyncio.run(_generate(text, output_path))
    return output_path


async def _generate(text: str, audio_path: str):
    communicate = edge_tts.Communicate(text, VOICE, rate="+25%", volume="+10%")
    await communicate.save(audio_path)
