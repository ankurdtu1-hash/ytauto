import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# One codebase, several channels. CHANNEL_PROFILE picks which one this run is for.
PROFILES = {
    "main": {
        "name": "TechSeekho AI",
        "niche": "Hindi facts and explainers about AI, technology, gadgets, the internet and science, "
                 "for curious Indian viewers",
        "voice": "hi-IN-MadhurNeural",
        "topic_mode": "evergreen",
        "data_dir": "data",
        "publish_slots": "11:00,20:30",  # IST times the Shorts go public
        "art_style": "clean glossy 3D render, soft studio lighting, vivid blue and orange colours, high detail",
    },
    "trending": {
        "name": "Trending Kya Hai",
        "niche": "India's trending topics explained in 40 seconds in Hindi: cricket and sports, movies and OTT, "
                 "tech and gadget launches, science and space, festivals and viral internet trends",
        "voice": "hi-IN-SwaraNeural",
        "topic_mode": "trending",
        "data_dir": "data/trending",
        "publish_slots": "08:30,13:30,19:00",
        "art_style": "vibrant cinematic digital illustration, dramatic lighting, rich colours, high detail",
    },
}
PROFILE = os.getenv("CHANNEL_PROFILE", "main")
_profile = PROFILES[PROFILE]
TOPIC_MODE = _profile["topic_mode"]

OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / _profile["data_dir"]
MUSIC_DIR = ROOT / "assets" / "music"
CLIENT_SECRET_FILE = ROOT / "client_secret.json"
TOKEN_FILE = ROOT / os.getenv("TOKEN_FILE", "token.json")

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
ART_STYLE = _profile["art_style"]

CHANNEL_NAME = os.getenv("CHANNEL_NAME") or _profile["name"]
CHANNEL_NICHE = os.getenv("CHANNEL_NICHE") or _profile["niche"]

TTS_VOICE = os.getenv("TTS_VOICE") or _profile["voice"]
TTS_RATE = os.getenv("TTS_RATE", "+30%")  # about 1.2x the earlier pace

UPLOAD_PRIVACY = os.getenv("UPLOAD_PRIVACY", "private")
# Each video goes public at the next free one of these India-time slots (YouTube scheduled publish),
# so Shorts are spread through the day even when GitHub starts several runs close together.
PUBLISH_SLOTS = [s.strip() for s in (os.getenv("PUBLISH_SLOTS") or _profile["publish_slots"]).split(",") if s.strip()]
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "27")

SUBTITLE_FONT = os.getenv("SUBTITLE_FONT", "Noto Sans Devanagari")
FPS = 30

# Per-format settings. Hindi narration runs at roughly 130-150 words per minute.
FORMATS = {
    "short": {
        "width": 1080,
        "height": 1920,
        "orientation": "portrait",
        "words": "70 to 85 words — never more than 90 (about 35-40 seconds)",
        "scenes": "8 to 10",
        "font_size": 96,
        "words_per_caption": 3,
    },
    "long": {
        "width": 1920,
        "height": 1080,
        "orientation": "landscape",
        "words": "900 to 1100 words (about 7-8 minutes)",
        "scenes": "70 to 90",
        "font_size": 58,
        "words_per_caption": 6,
    },
}
