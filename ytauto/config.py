import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
MUSIC_DIR = ROOT / "assets" / "music"
CLIENT_SECRET_FILE = ROOT / "client_secret.json"
TOKEN_FILE = ROOT / "token.json"

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

CHANNEL_NAME = os.getenv("CHANNEL_NAME", "TechSeekho AI")
CHANNEL_NICHE = os.getenv(
    "CHANNEL_NICHE",
    "Hindi facts and explainers about AI, technology, gadgets, the internet and science, for curious Indian viewers",
)

TTS_VOICE = os.getenv("TTS_VOICE", "hi-IN-MadhurNeural")
TTS_RATE = os.getenv("TTS_RATE", "+8%")

UPLOAD_PRIVACY = os.getenv("UPLOAD_PRIVACY", "private")
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "27")

SUBTITLE_FONT = os.getenv("SUBTITLE_FONT", "Noto Sans Devanagari")
FPS = 30

# Per-format settings. Hindi narration runs at roughly 130-150 words per minute.
FORMATS = {
    "short": {
        "width": 1080,
        "height": 1920,
        "orientation": "portrait",
        "words": "110 to 140 words (about 45-55 seconds)",
        "scenes": "6 to 9",
        "font_size": 96,
        "words_per_caption": 3,
    },
    "long": {
        "width": 1920,
        "height": 1080,
        "orientation": "landscape",
        "words": "900 to 1100 words (about 7-8 minutes)",
        "scenes": "35 to 45",
        "font_size": 58,
        "words_per_caption": 6,
    },
}
