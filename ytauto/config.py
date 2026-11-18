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
        "publish_slots": "12:30",  # IST time the daily Short goes public
        "angle": "Prefer facts about things Indians use every day (phones, UPI, internet, trains, chargers, "
                 "SIMs, everyday gadgets): these got the most views.",
        "art_style": "clean glossy 3D render, soft studio lighting, vivid blue and orange colours, high detail",
    },
    "trending": {
        "name": "Trending Kya Hai",
        "niche": "India's trending topics explained in 40 seconds in Hindi: cricket and sports, movies and OTT, "
                 "tech and gadget launches, science and space, festivals and viral internet trends",
        "voice": "hi-IN-SwaraNeural",
        "topic_mode": "trending",
        "data_dir": "data/trending",
        "publish_slots": "19:00",
        "category": "24",
        "art_style": "vibrant cinematic digital illustration, dramatic lighting, rich colours, high detail",
    },
    # New channels (Nov 2026): one Short a day each, own voice, look and posting time.
    "cricket": {
        "name": "Cricket Ki Kahaniyan",
        "niche": "cricket history, records, rules and legendary moments explained in Hindi: Indian legends, "
                 "World Cups, IPL history, strange rules and unbreakable records",
        "angle": "Indian players and India's matches first (Sachin, Dhoni, Kohli, Rohit, Bumrah, World Cups, IPL). "
                 "Hook with a star's name plus a record or number. Only records you are certain of; no live scores.",
        "voice": "hi-IN-MadhurNeural",
        "narrator": "male, young adult, high pitch",
        "topic_mode": "evergreen",
        "data_dir": "data/cricket",
        "publish_slots": "18:00",
        "category": "17",
        "art_style": "dramatic cinematic sports illustration, stadium floodlights, motion and dust, rich colours, "
                     "generic anonymous players only",
    },
    "animals": {
        "name": "Janwar Ki Duniya",
        "niche": "amazing animal, bird, insect and ocean-life facts in Hindi, from Indian wildlife to the deep sea",
        "angle": "Shocking abilities, records and 'why does it do that' questions; animals Indians know first "
                 "(tiger, cobra, elephant, crow, cat, dog, cow, peacock), then exotic ones.",
        "voice": "hi-IN-SwaraNeural",
        "narrator": "female, young adult, moderate pitch",
        "topic_mode": "evergreen",
        "data_dir": "data/animals",
        "publish_slots": "16:00",
        "category": "15",
        "art_style": "stunning National-Geographic-style wildlife illustration, natural light, sharp detail, vivid colours",
    },
    "places": {
        "name": "Ajab Gajab Duniya",
        "niche": "strange places, countries, cities, world wonders and geography facts in Hindi, including "
                 "unbelievable places in India",
        "angle": "One unbelievable place or country fact per Short: weird laws, record-breaking places, hidden "
                 "villages, natural wonders. Mix India and the world. No politics, borders or conflicts.",
        "voice": "hi-IN-MadhurNeural",
        "narrator": "male, middle-aged, moderate pitch",
        "topic_mode": "evergreen",
        "data_dir": "data/places",
        "publish_slots": "14:00",
        "category": "19",
        "art_style": "breathtaking cinematic travel illustration, golden hour light, epic wide view, vivid colours",
    },
    "money": {
        "name": "Paisa Gyaan",
        "niche": "how money, business and famous brands work, explained in Hindi: brand origin stories, how "
                 "companies earn, how banks, UPI, cards and taxes work, money history and big business facts",
        "angle": "Brand stories Indians know (Parle-G, Amul, Tata, Zomato, Maggi, Jio) and how everyday money "
                 "things work. Education only: never investment, loan or tax advice, never tips to buy or sell, "
                 "no current prices or rates.",
        "voice": "hi-IN-MadhurNeural",
        "narrator": "male, young adult, moderate pitch",
        "topic_mode": "evergreen",
        "data_dir": "data/money",
        "publish_slots": "09:00",
        "category": "27",
        "art_style": "clean premium 3D illustration, warm studio light, gold and deep green colours, high detail",
    },
}
PROFILE = os.getenv("CHANNEL_PROFILE", "main")
_profile = PROFILES[PROFILE]
TOPIC_MODE = _profile["topic_mode"]

OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / _profile["data_dir"]
MUSIC_DIR = ROOT / "assets" / "music"
CLIENT_SECRET_FILE = ROOT / os.getenv("CLIENT_SECRET_FILE", "client_secret.json")
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
if os.getenv("PUBLISH_NOW", "").lower() == "true":  # manual runs: public right away
    PUBLISH_SLOTS = []
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID") or _profile.get("category", "27")

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
