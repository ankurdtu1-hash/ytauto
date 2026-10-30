"""Remembers past topics so the channel never repeats itself."""
import json
from datetime import datetime

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
