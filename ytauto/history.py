"""Remembers past topics so the channel never repeats itself."""
import json
from datetime import datetime, timedelta, timezone

from . import config

HISTORY_FILE = config.DATA_DIR / "history.json"


def load():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def add(entry):
    items = load()
    items.append({"date": datetime.now().isoformat(timespec="minutes"), **entry})
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def recent_titles(n=60):
    return [f"{i['kind']}: {i['title']}" for i in load()[-n:]]


def recent_formats(kind, n=5):
    return [i.get("format") for i in load() if i["kind"] == kind][-n:]


IST = timezone(timedelta(hours=5, minutes=30))


def next_slot(min_lead_minutes=20):
    """Earliest publish slot (India time) at least min_lead_minutes away that no earlier video has taken.
    Returns an RFC 3339 UTC string for YouTube's publishAt, or None if no slots are configured."""
    if not config.PUBLISH_SLOTS:
        return None
    taken = {i["publish_at"] for i in load() if i.get("publish_at")}
    earliest = datetime.now(timezone.utc) + timedelta(minutes=min_lead_minutes)
    day = earliest.astimezone(IST).date()
    for d in range(30):
        for slot in sorted(config.PUBLISH_SLOTS):
            h, m = map(int, slot.split(":"))
            t = datetime(day.year, day.month, day.day, h, m, tzinfo=IST) + timedelta(days=d)
            iso = t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if t >= earliest and iso not in taken:
                return iso
    return None


def slot_due(ahead_hours):
    """True when the next free publish slot is within ahead_hours, i.e. a video should be made now."""
    slot = next_slot()
    if not slot:
        return False
    when = datetime.strptime(slot, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return when - datetime.now(timezone.utc) <= timedelta(hours=ahead_hours)
