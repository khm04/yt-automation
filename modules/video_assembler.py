import os
import random
import subprocess
from moviepy.editor import VideoFileClip, AudioFileClip
from faster_whisper import WhisperModel
from modules.reddit_card import generate_reddit_card
from config import (
    GAMEPLAY_VIDEOS, OUTPUT_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS
)

MIN_DURATION = 55.0  # 55s after 1.15x speedup = ~63s of natural speech
MAX_DURATION = 90.0  # allow up to 90s so story never gets cut off mid-sentence
CARD_DISPLAY_SECS = 4  # how long the Reddit card stays on screen

_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        print("   Loading Whisper model (first run only)...")
        _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _whisper_model


def _remove_silence(audio_path: str, out_path: str):
    """Strip silences aggressively — no dead air between phrases."""
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-af", "silenceremove=stop_periods=-1:stop_duration=0.15:stop_threshold=-35dB",
        out_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)


CONNECTORS = {
    "i", "a", "an", "the", "and", "but", "or", "so", "as", "if",
    "in", "on", "at", "to", "of", "for", "by", "up", "is", "it",
    "he", "she", "we", "my", "his", "her", "me", "us", "you",
    "am", "are", "was", "were", "be", "do", "did", "got", "get",
    "not", "no", "had", "has", "that", "this", "with", "from",
}


def build_subtitle_file(audio_path: str, output_path: str) -> str:
    """Build SRT: one word per caption, connectors attached to the next word."""
    model = _get_whisper()
    segments, _ = model.transcribe(audio_path, word_timestamps=True)

    words = []
    for segment in segments:
        for word in segment.words:
            words.append((word.start, word.end, word.word.strip()))

    chunks = []
    i = 0
    while i < len(words):
        w = words[i]
        clean = w[2].lower().strip(".,!?")
        if clean in CONNECTORS and i + 1 < len(words):
            nw = words[i + 1]
            chunks.append((w[0], nw[1], w[2] + " " + nw[2]))
            i += 2
        else:
            chunks.append(w)
            i += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for idx, (start, end, text) in enumerate(chunks, 1):
            f.write(f"{idx}\n{_seconds_to_srt_time(start)} --> {_seconds_to_srt_time(end)}\n{text.upper()}\n\n")

    return output_path


def _seconds_to_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def assemble_video(audio_path: str, script: str, output_path: str,
                   subreddit: str = "AmItheAsshole", story_title: str = "",
                   video_index: int = 0) -> str:
    """Combine gameplay + voice + captions + Reddit card into 1080x1920 MP4."""

    # Step 1: Remove silence — no dead air
    clean_audio = audio_path.replace(".mp3", "_clean.mp3")
    _remove_silence(audio_path, clean_audio)

    # Step 2: Check duration
    audio_clip = AudioFileClip(clean_audio)
    duration = min(audio_clip.duration, MAX_DURATION)
    audio_clip.close()

    if duration < MIN_DURATION:
        raise ValueError(f"Audio too short: {duration:.1f}s — must be at least {MIN_DURATION}s")

    # Step 3: Pick gameplay video by index (ensures 2 minecraft + 2 rocket league)
    gameplay_video, intro_skip = GAMEPLAY_VIDEOS[video_index % len(GAMEPLAY_VIDEOS)]
    gameplay_clip = VideoFileClip(gameplay_video)
    total_duration = gameplay_clip.duration
    gameplay_clip.close()
    max_start = total_duration - duration
    start = random.uniform(intro_skip, max_start)

    # Step 4: Generate Reddit card image
    card_path = output_path.replace(".mp4", "_card.png")
    generate_reddit_card(subreddit, story_title, card_path)

    # Step 5: Build Whisper-synced subtitles
    srt_path = output_path.replace(".mp4", ".srt")
    build_subtitle_file(clean_audio, srt_path)

    subtitle_style = (
        "FontName=Arial,"
        "FontSize=15,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H00000000,"
        "Outline=3,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginV=150"
    )

    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
    card_escaped = card_path.replace("\\", "/").replace(":", "\\:")

    # Card: centered horizontally, top third of screen, fades out after CARD_DISPLAY_SECS
    card_x = "(W-overlay_w)/2"
    card_y = "H*0.12"
    card_filter = (
        f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"subtitles='{srt_escaped}':force_style='{subtitle_style}'[bg];"
        f"[1:v]scale=880:-1[card];"
        f"[bg][card]overlay={card_x}:{card_y}:"
        f"enable='between(t,0,{CARD_DISPLAY_SECS})',"
        f"fade=t=out:st={CARD_DISPLAY_SECS - 0.5}:d=0.5:alpha=1"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-t", str(duration), "-i", gameplay_video,
        "-ss", "0", "-t", str(duration), "-i", clean_audio,
        "-i", card_path,
        "-filter_complex", card_filter,
        "-map", "[fade]" if False else "0:v:0",  # placeholder, overridden below
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-r", str(VIDEO_FPS),
        output_path
    ]

    # Build correct filter_complex command
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-t", str(duration), "-i", gameplay_video,
        "-ss", "0", "-t", str(duration), "-i", clean_audio,
        "-i", card_path,
        "-filter_complex", (
            f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"subtitles='{srt_escaped}':force_style='{subtitle_style}'[bg];"
            f"[2:v]scale=880:-1,fade=t=out:st={CARD_DISPLAY_SECS - 0.5}:d=0.5[card];"
            f"[bg][card]overlay={card_x}:{card_y}:enable='between(t,0,{CARD_DISPLAY_SECS})'[out]"
        ),
        "-map", "[out]",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-r", str(VIDEO_FPS),
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(clean_audio)
    if os.path.exists(card_path):
        os.remove(card_path)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-2000:]}")

    return output_path
