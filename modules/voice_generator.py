import os
import wave
import struct
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

# Gemini TTS voices — all sound natural and expressive
# Options: Aoede, Charon, Fenrir, Kore, Puck, Schedar, Sulafat, Orus, Zephyr
VOICE = "Aoede"   # warm female voice, great for storytelling


def generate_voice(text: str, output_path: str) -> str:
    """Generate voice using Gemini 2.5 Flash TTS — free, no IP blocking, high quality."""
    if not text.strip():
        raise ValueError("Script cannot be empty")

    client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=VOICE
                    )
                )
            ),
        ),
    )

    # Extract raw PCM audio bytes
    audio_data = response.candidates[0].content.parts[0].inline_data.data

    # Save as WAV (Gemini returns 16-bit PCM at 24kHz mono)
    wav_path = output_path.replace(".mp3", ".wav")
    _save_wav(audio_data, wav_path, sample_rate=24000, channels=1, sampwidth=2)

    # Convert to mp3 + speed up 1.2x to match the energetic pace of the channel
    mp3_path = output_path if output_path.endswith(".mp3") else output_path.replace(".wav", ".mp3")
    os.system(
        f'ffmpeg -y -i "{wav_path}" '
        f'-filter:a "atempo=1.15" '
        f'-q:a 2 "{mp3_path}" -loglevel quiet'
    )
    if os.path.exists(wav_path) and wav_path != mp3_path:
        os.remove(wav_path)

    return mp3_path


def _save_wav(pcm_data: bytes, path: str, sample_rate: int, channels: int, sampwidth: int):
    """Write raw PCM bytes to a WAV file."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
