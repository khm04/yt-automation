import os
from dotenv import load_dotenv

load_dotenv()

# Reddit (public API — no credentials needed)
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AutoYouTubeBot/1.0")

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # default: Rachel

# YouTube
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

# Video settings
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
MAX_VIDEO_DURATION = 90  # seconds
MIN_VIDEO_DURATION = 45  # seconds

# Paths
ASSETS_DIR = "assets"
OUTPUT_DIR = "output"
# Ordered rotation: minecraft, rocket league, minecraft, rocket league
GAMEPLAY_VIDEOS = [
    (f"{ASSETS_DIR}/minecraft_1080p.mp4", 0),
    (f"{ASSETS_DIR}/satisfying.mp4", 5),
    (f"{ASSETS_DIR}/minecraft_1080p.mp4", 0),
    (f"{ASSETS_DIR}/satisfying.mp4", 5),
]

# Reddit sources
SUBREDDITS = ["AmItheAsshole", "tifu", "relationship_advice", "confessions", "TrueOffMyChest"]
POSTS_LIMIT = 20  # fetch top 20, pick best one
VIDEOS_PER_DAY = 4

# Allow GitHub Actions to override videos per run
VIDEOS_PER_DAY = int(os.getenv("VIDEOS_PER_DAY_OVERRIDE", VIDEOS_PER_DAY))
