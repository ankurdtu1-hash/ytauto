"""Free stock footage from Pixabay."""
import json

import requests

from . import config

SEARCH_URL = "https://pixabay.com/api/videos/"
FALLBACK_QUERIES = ["technology", "city timelapse", "nature landscape", "space stars"]
BLOCKED_TAGS = ("green screen", "greenscreen", "chroma", "blue screen", "watermark")
USED_FILE = config.DATA_DIR / "used_clips.json"
TOP_HITS = 8  # beyond this Pixabay results drift off-topic


def load_used():
    """Clip ids used in earlier videos, so the channel never repeats footage."""
    if USED_FILE.exists():
        return set(json.loads(USED_FILE.read_text(encoding="utf-8")))
    return set()


def save_used(used_ids):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    USED_FILE.write_text(json.dumps(sorted(used_ids)[-3000:]), encoding="utf-8")


def _search(query):
    resp = requests.get(
        SEARCH_URL,
        params={"key": config.PIXABAY_API_KEY, "q": query[:100], "per_page": 20, "safesearch": "true"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("hits", [])


def _best_file(video, fmt):
    files = [f for f in video["videos"].values() if f.get("url") and f.get("width")]
    target = max(fmt["width"], fmt["height"]) * 0.66
    big_enough = [f for f in files if max(f["width"], f["height"]) >= target]
    if big_enough:
        return min(big_enough, key=lambda f: f["width"] * f["height"])
    return max(files, key=lambda f: f["width"] * f["height"], default=None)


def _candidates(query, fmt):
    """Most relevant hits first; among them, clips matching the output orientation first."""
    portrait = fmt["orientation"] == "portrait"
    hits = [v for v in _search(query)[:TOP_HITS] if not any(t in v.get("tags", "").lower() for t in BLOCKED_TAGS)]
    files = [(v["id"], _best_file(v, fmt)) for v in hits]
    files = [(i, f) for i, f in files if f]
    return sorted(files, key=lambda x: (x[1]["height"] > x[1]["width"]) != portrait)


def fetch_clip(query, out_path, fmt, used_ids):
    """Download one clip matching query that has not been used before. Returns True on success."""
    for q in [query, *FALLBACK_QUERIES]:
        for video_id, file in _candidates(q, fmt):
            if video_id in used_ids:
                continue
            with requests.get(file["url"], stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            used_ids.add(video_id)
            return True
    return False
