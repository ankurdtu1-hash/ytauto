"""Stock visuals from several free sources, ranked by how well they match the spoken sentence.

Sources:
- Pixabay videos and photos (Pixabay licence, no attribution required)
- NASA Image Library photos (public domain; great for space topics)
- Openverse photos (Creative Commons from Wikimedia, Flickr, ...; commercial-use licences only,
  attribution collected and added to the video description)
"""
import base64
import io
import json
import logging
import re

import requests
from PIL import Image

from . import config

log = logging.getLogger("ytauto")

FALLBACK_QUERIES = ["technology", "city timelapse", "nature landscape", "space stars"]
BLOCKED_TAGS = ("green screen", "greenscreen", "chroma", "blue screen", "watermark", "logo")
STOPWORDS = {"a", "an", "the", "of", "in", "on", "and", "with", "to", "for", "at", "closeup", "close", "up", "view"}
USED_FILE = config.DATA_DIR / "used_clips.json"
_disabled = set()  # sources that rate-limited us during this run


def load_used():
    """Visual ids used in earlier videos, so the channel never repeats visuals."""
    if USED_FILE.exists():
        return {str(i) for i in json.loads(USED_FILE.read_text(encoding="utf-8"))}
    return set()


def save_used(used_ids):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    USED_FILE.write_text(json.dumps(sorted(used_ids)[-5000:]), encoding="utf-8")


def _relevance(query, text):
    """How many meaningful query words appear in the item's tags/title (0 = unrelated)."""
    words = {w for w in re.findall(r"[a-z]+", query.lower()) if w not in STOPWORDS}
    text = text.lower()
    if any(t in text for t in BLOCKED_TAGS):
        return -1
    return sum(1 for w in words if w in text or w.rstrip("s") in text)


def _get_json(source, url, **params):
    if source in _disabled:
        return None
    try:
        resp = requests.get(url, params=params, timeout=30, headers={"User-Agent": "ytauto/1.0"})
        if resp.status_code == 429:
            log.warning("%s rate limit reached; skipping it for the rest of this video", source)
            _disabled.add(source)
            return None
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as e:
        log.warning("%s search failed: %s", source, e)
        return None


# ---------- sources: each returns candidate dicts ----------
# {id, kind: "video"|"photo", url, score, credit, portrait}

def _pixabay_videos(query, fmt):
    data = _get_json("pixabay", "https://pixabay.com/api/videos/", key=config.PIXABAY_API_KEY,
                     q=query[:100], per_page=30, safesearch="true") or {}
    target = max(fmt["width"], fmt["height"]) * 0.66
    out = []
    for rank, v in enumerate(data.get("hits", [])):
        files = [f for f in v["videos"].values() if f.get("url") and f.get("width")]
        big = [f for f in files if max(f["width"], f["height"]) >= target]
        f = min(big, key=lambda f: f["width"] * f["height"]) if big else max(files, key=lambda f: f["width"], default=None)
        if f:
            thumb = next((r.get("thumbnail") for r in v["videos"].values() if r.get("thumbnail")), None)
            out.append({"id": f"v{v['id']}", "kind": "video", "url": f["url"], "rank": rank, "thumb": thumb,
                        "score": _relevance(query, v.get("tags", "")), "credit": None,
                        "portrait": f["height"] > f["width"]})
    return out


def _pixabay_photos(query, fmt):
    orientation = "vertical" if fmt["orientation"] == "portrait" else "horizontal"
    data = _get_json("pixabay", "https://pixabay.com/api/", key=config.PIXABAY_API_KEY, q=query[:100],
                     image_type="photo", orientation=orientation, per_page=20, safesearch="true") or {}
    return [{"id": f"p{p['id']}", "kind": "photo", "url": p.get("largeImageURL") or p["webformatURL"],
             "thumb": p.get("previewURL") or p.get("webformatURL"),
             "rank": rank, "score": _relevance(query, p.get("tags", "")), "credit": None,
             "portrait": fmt["orientation"] == "portrait"}
            for rank, p in enumerate(data.get("hits", []))]


def _nasa(query, media_type):
    data = _get_json("nasa", "https://images-api.nasa.gov/search", q=query[:100], media_type=media_type) or {}
    out = []
    for rank, item in enumerate(data.get("collection", {}).get("items", [])[:10]):
        meta = (item.get("data") or [{}])[0]
        text = " ".join([meta.get("title", ""), " ".join(meta.get("keywords", []) or [])])
        thumb = next((l.get("href") for l in item.get("links") or [] if l.get("render") == "image"), None)
        out.append({"id": f"n{meta.get('nasa_id')}", "kind": "video" if media_type == "video" else "photo", "thumb": thumb,
                    "nasa_id": meta.get("nasa_id"), "url": None, "rank": rank, "score": _relevance(query, text),
                    "credit": "NASA", "portrait": False})
    return out


def _nasa_asset_url(candidate):
    data = _get_json("nasa", f"https://images-api.nasa.gov/asset/{candidate['nasa_id']}") or {}
    hrefs = [i["href"] for i in data.get("collection", {}).get("items", [])]
    prefs = ["~medium.mp4", "~small.mp4", "~orig.mp4"] if candidate["kind"] == "video" else ["~large.jpg", "~orig.jpg", "~medium.jpg"]
    for p in prefs:
        for h in hrefs:
            if h.endswith(p):
                return h.replace("http://", "https://")
    return None


def _openverse(query, fmt):
    data = _get_json("openverse", "https://api.openverse.org/v1/images/", q=query[:100], license_type="commercial",
                     mature="false", page_size=20) or {}
    out = []
    for rank, r in enumerate(data.get("results", [])):
        if (r.get("width") or 0) < 800:  # too small to look sharp at 1080p
            continue
        text = " ".join([r.get("title") or "", " ".join(t.get("name", "") for t in r.get("tags") or [])])
        out.append({"id": f"o{r['id']}", "kind": "photo", "url": r.get("url"), "rank": rank, "thumb": r.get("thumbnail"),
                    "score": _relevance(query, text), "credit": (r.get("attribution") or "").split(" To view")[0] or None,
                    "portrait": fmt["orientation"] == "portrait"})
    return out


# ---------- ranking ----------

def candidates(queries, fmt, used_ids):
    """Yield candidates best-first: matching videos, then matching photos, then loose fallback videos."""
    portrait = fmt["orientation"] == "portrait"
    seen = set()

    def fresh(items, min_score):
        items = [c for c in items if c["id"] not in used_ids and c["id"] not in seen
                 and c["id"][1:] not in used_ids and c["score"] >= min_score]
        return sorted(items, key=lambda c: (-c["score"], c["portrait"] != portrait, c["rank"]))

    for q in queries:
        for c in fresh(_pixabay_videos(q, fmt), 1):
            seen.add(c["id"])
            yield c
        for c in fresh(_pixabay_photos(q, fmt) + _openverse(q, fmt) + _nasa(q, "image"), 1):
            seen.add(c["id"])
            yield c
    for q in [*queries, *FALLBACK_QUERIES]:
        for c in fresh(_pixabay_videos(q, fmt), 0):
            seen.add(c["id"])
            yield c


def shortlist(queries, fmt, used_ids, videos=3, photos=3):
    """A small, mixed set of the best candidates for one scene, for Claude to choose from by looking."""
    vids, pics = [], []
    for c in candidates(queries, fmt, used_ids):
        bucket = vids if c["kind"] == "video" else pics
        if len(bucket) < (videos if bucket is vids else photos):
            bucket.append(c)
        if len(vids) >= videos and len(pics) >= photos:
            break
    return vids + pics


def thumbnail_b64(candidate):
    """(media_type, base64) of a candidate's small preview image, or None."""
    if not candidate.get("thumb"):
        return None
    try:
        r = requests.get(candidate["thumb"], timeout=15, headers={"User-Agent": "ytauto/1.0"})
        r.raise_for_status()
    except requests.RequestException:
        return None
    try:  # shrink to a small preview: cheap to send and within the many-image size limit
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        img.thumbnail((320, 320))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
    except (OSError, ValueError):
        return None
    return "image/jpeg", base64.b64encode(buf.getvalue()).decode()


def download(candidate, out_base):
    url = candidate["url"] or _nasa_asset_url(candidate)
    if not url:
        return None
    path = out_base.with_suffix(".mp4" if candidate["kind"] == "video" else ".jpg")
    try:
        with requests.get(url, stream=True, timeout=180, headers={"User-Agent": "ytauto/1.0"}) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    except requests.RequestException as e:
        log.warning("Download failed (%s): %s", candidate["id"], e)
        return None
    return path
