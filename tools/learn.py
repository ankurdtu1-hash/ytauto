"""python tools/learn.py <token file>  --  weekly self-review for the channel picked by CHANNEL_PROFILE.

Reads this channel's video stats (read-only), looks up what works for Indian Shorts right now (Gemini with
Google Search, free), and writes data/<profile>/insights.json. Every new video's brief includes those
insights, so the channel keeps learning what its viewers want. A dated summary goes to insights_log.md.
"""
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ytauto import config, llm

sys.stdout.reconfigure(encoding="utf-8")
OUT = config.DATA_DIR / "insights.json"
LOG = config.DATA_DIR / "insights_log.md"

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "3-4 plain English sentences: what worked, what flopped, what changes"},
        "do_more": {"type": "array", "items": {"type": "string"}},
        "avoid": {"type": "array", "items": {"type": "string"}},
        "hook_tips": {"type": "array", "items": {"type": "string"}},
        "title_tips": {"type": "array", "items": {"type": "string"}},
        "hot_keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "do_more", "avoid", "hook_tips", "title_tips", "hot_keywords"],
}


def video_stats(token):
    creds = Credentials.from_authorized_user_file(token)
    if not creds.valid:
        creds.refresh(Request())  # in memory only
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    ch = yt.channels().list(part="statistics,contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in
           yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50).execute()["items"]]
    vids = yt.videos().list(part="snippet,statistics,status", id=",".join(ids)).execute()["items"] if ids else []
    now, rows = datetime.now(timezone.utc), []
    for v in vids:
        if v["status"]["privacyStatus"] != "public":
            continue
        published = datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
        s = v["statistics"]
        rows.append({"title": v["snippet"]["title"], "age_days": round((now - published).total_seconds() / 86400, 1),
                     "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                     "comments": int(s.get("commentCount", 0))})
    return ch["statistics"], rows


def web_research():
    """What is working for Hindi/Indian YouTube Shorts right now (free Gemini + Google Search). Empty on failure."""
    prompt = (f"Using Google Search, summarise in 8-12 bullet points what is working right now ({date.today():%B %Y}) "
              f"for Hindi/Indian YouTube Shorts channels like \"{config.CHANNEL_NAME}\" ({config.CHANNEL_NICHE}): "
              "topics Indians are watching this month and coming weeks (matches, releases, launches, festivals, exams), "
              "hook and title styles, Shorts length, and any recent YouTube Shorts algorithm or policy changes. "
              "Facts only, no fluff.")
    for model in llm.GEMINI_MODELS:
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                              headers={"x-goog-api-key": llm.GEMINI_KEY}, timeout=150,
                              json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                                    "tools": [{"google_search": {}}]})
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            if text:
                return text
        except (requests.RequestException, KeyError, IndexError) as e:
            print(f"research with {model} failed: {str(e)[:120]}")
    return ""


def main(token):
    channel, rows = video_stats(token)
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    research = web_research()
    table = "\n".join(f"- {r['views']} views, {r['likes']} likes, {r['comments']} comments, {r['age_days']} days old: "
                      f"{r['title']}" for r in sorted(rows, key=lambda r: -r["views"])) or "(no public videos yet)"
    prompt = f"""You are the growth strategist for the Hindi YouTube Shorts channel "{config.CHANNEL_NAME}"
(niche: {config.CHANNEL_NICHE}). Channel: {channel.get('subscriberCount')} subscribers, {channel['viewCount']} views.
Goal: more views and subscribers, towards YouTube monetisation (1,000 subs + 10M Shorts views in 90 days).

Every public Short, most viewed first (videos under 2 days old are still growing; judge them gently):
{table}

Last week's insights (keep what the numbers still support, drop what they don't):
{json.dumps(old, ensure_ascii=False, indent=1) if old else "(first review)"}

Fresh web research on what works for Indian Shorts right now:
{research or "(not available this week)"}

Find the patterns that separate the winners from the flops (topic, named stars, numbers in the hook, title
style, format) and turn them into concrete instructions for the scriptwriter. Each list: 3-6 short, specific
items. hook_tips / title_tips may give Hinglish examples in Roman letters. hot_keywords: 5-15 lowercase words
or names (1-3 words each) of topics, people or events viewers want now or in the next weeks; they move matching
trends to the front. Stay inside YouTube's rules: no clickbait that the video does not deliver, no misleading
claims, no politics/religion/crime/gossip, no copyrighted material, no look-alikes of real people."""
    ins = llm.structured(prompt, SCHEMA)
    ins = {k: [str(x).strip()[:200] for x in ins[k]][:15 if k == "hot_keywords" else 6]
           if isinstance(ins[k], list) else str(ins[k])[:800] for k in SCHEMA["required"]}
    ins["hot_keywords"] = [k.lower() for k in ins.get("hot_keywords", []) if re.fullmatch(r"[a-z0-9 .'-]{2,30}", k.lower())]
    ins["updated"] = date.today().isoformat()
    OUT.write_text(json.dumps(ins, ensure_ascii=False, indent=2), encoding="utf-8")

    top = sorted(rows, key=lambda r: -r["views"])
    entry = (f"\n## {ins['updated']}: {channel.get('subscriberCount')} subs, {channel['viewCount']} views, "
             f"{len(rows)} public Shorts\n\n{ins['summary']}\n\n"
             + "Best: " + "; ".join(f"{r['title'][:50]} ({r['views']})" for r in top[:3]) + "\n\n"
             + "Weakest: " + "; ".join(f"{r['title'][:50]} ({r['views']})" for r in top[-3:]) + "\n")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(entry)
    print(entry)
    print(json.dumps(ins, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(config.TOKEN_FILE))
