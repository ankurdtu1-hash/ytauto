"""Free stock visuals from Pixabay: videos first, photos (with a zoom) when no video matches."""
import json
import re

import requests

from . import config

VIDEO_URL = "https://pixabay.com/api/videos/"
PHOTO_URL = "https://pixabay.com/api/"
FALLBACK_QUERIES = ["technology", "city timelapse", "nature landscape", "space stars"]
BLOCKED_TAGS = ("green screen", "greenscreen", "chroma", "blue screen", "watermark")
STOPWORDS = {"a", "an", "the", "of", "in", "on", "and", "with", "to", "for", "at", "closeup", "close", "up", "view"}
USED_FILE = config.DATA_DIR / "used_clips.json"


def load_used():
    """Clip/photo ids used in earlier videos, so the channel never repeats visuals."""
    if USED_FILE.exists():
        return {str(i) for i in json.loads(USED_FILE.read_text(encoding="utf-8"))}
    return set()


def save_used(used_ids):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    USED_FILE.write_text(json.dumps(sorted(used_ids)[-5000:]), encoding="utf-8")


def _get(url, query, **params):
    resp = requests.get(
        url,
        params={"key": config.PIXABAY_API_KEY, "q": query[:100], "per_page": 30, "safesearch": "true", **params},
        timeout=30,
    )
    resp.raise_for_status()
    return [h for h in resp.json().get("hits", []) if not any(t in h.get("tags", "").lower() for t in BLOCKED_TAGS)]


def _relevance(query, tags):
    """How many meaningful query words appear in the clip's tags (0 = unrelated)."""
    words = {w for w in re.findall(r"[a-z]+", query.lower()) if w not in STOPWORDS}
    tag_text = tags.lower()
    return sum(1 for w in words if w in tag_text or w.rstrip("s") in tag_text)


def _best_video_file(video, fmt):
    files = [f for f in video["videos"].values() if f.get("url") and f.get("width")]
    target = max(fmt["width"], fmt["height"]) * 0.66
    big_enough = [f for f in files if max(f["width"], f["height"]) >= target]
    if big_enough:
        return min(big_enough, key=lambda f: f["width"] * f["height"])
    return max(files, key=lambda f: f["width"] * f["height"], default=None)


def _download(url, out_path):
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def _try_video(query, fmt, used_ids, min_score):
    portrait = fmt["orientation"] == "portrait"
    best = None
    for rank, v in enumerate(_get(VIDEO_URL, query)):
        if f"v{v['id']}" in used_ids or str(v["id"]) in used_ids:
            continue
        file = _best_video_file(v, fmt)
        if not file:
            continue
        score = _relevance(query, v.get("tags", ""))
        if score < min_score:
            continue
        orientation_ok = (file["height"] > file["width"]) == portrait
        key = (score, orientation_ok, -rank)
        if best is None or key > best[0]:
            best = (key, v["id"], file["url"])
    return best


def _try_photo(query, fmt, used_ids, min_score):
    orientation = "vertical" if fmt["orientation"] == "portrait" else "horizontal"
    for p in _get(PHOTO_URL, query, image_type="photo", orientation=orientation):
        if f"p{p['id']}" not in used_ids and _relevance(query, p.get("tags", "")) >= min_score:
            return p["id"], p.get("largeImageURL") or p["webformatURL"]
    return None


def fetch_visual(queries, out_base, fmt, used_ids):
    """Download the best-matching visual for a scene.

    Returns (path, is_photo). Tries each query for a tag-matching video, then a tag-matching photo,
    and only then falls back to a loosely related video.
    """
    for q in queries:
        hit = _try_video(q, fmt, used_ids, min_score=1)
        if hit:
            _, vid, url = hit
            path = out_base.with_suffix(".mp4")
            _download(url, path)
            used_ids.add(f"v{vid}")
            return path, False
        photo = _try_photo(q, fmt, used_ids, min_score=1)
        if photo:
            pid, url = photo
            path = out_base.with_suffix(".jpg")
            _download(url, path)
            used_ids.add(f"p{pid}")
            return path, True

    for q in [*queries, *FALLBACK_QUERIES]:
        hit = _try_video(q, fmt, used_ids, min_score=0)
        if hit:
            _, vid, url = hit
            path = out_base.with_suffix(".mp4")
            _download(url, path)
            used_ids.add(f"v{vid}")
            return path, False
    raise RuntimeError(f"No stock visual found for {queries}")
