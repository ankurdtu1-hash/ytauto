"""Free stock footage from Pixabay."""
import requests

from . import config

SEARCH_URL = "https://pixabay.com/api/videos/"
FALLBACK_QUERIES = ["technology", "city timelapse", "nature landscape", "space stars"]


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
    # Prefer clips whose orientation matches the output so cropping keeps most of the frame.
    portrait = fmt["orientation"] == "portrait"
    if files and (files[0]["height"] > files[0]["width"]) != portrait:
        return None
    big_enough = [f for f in files if max(f["width"], f["height"]) >= max(fmt["width"], fmt["height"]) * 0.66]
    if big_enough:
        return min(big_enough, key=lambda f: f["width"] * f["height"])
    return max(files, key=lambda f: f["width"] * f["height"], default=None)


def _candidates(query, fmt):
    hits = _search(query)
    files = [(v["id"], _best_file(v, fmt)) for v in hits]
    matching = [(i, f) for i, f in files if f]
    if matching:
        return matching
    # Few vertical clips exist; for Shorts fall back to landscape clips (centre-cropped).
    return [(v["id"], max(v["videos"].values(), key=lambda f: f.get("width", 0))) for v in hits]


def fetch_clip(query, out_path, fmt, used_ids):
    """Download one clip matching query that this video has not used yet. Returns True on success."""
    for q in [query, *FALLBACK_QUERIES]:
        for video_id, file in _candidates(q, fmt):
            if video_id in used_ids or not file.get("url"):
                continue
            with requests.get(file["url"], stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            used_ids.add(video_id)
            return True
    return False
