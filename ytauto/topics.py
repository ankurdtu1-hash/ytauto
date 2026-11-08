"""Find a trending, fresh topic and gather verified facts for it."""
import html
import random
import re
import xml.etree.ElementTree as ET
from datetime import date

import requests

from . import config, history, llm

TRENDS_RSS = "https://trends.google.com/trending/rss?geo=IN"

# Rotating formats keep videos from looking templated (YouTube's "inauthentic content" rule).
FORMATS = {
    "short": [
        "one surprising fact explained",
        "myth vs fact",
        "3 quick facts",
        "why does this happen?",
        "what would happen if...?",
        "a little-known story from history or science",
    ],
    "long": [
        "deep explainer: how it works",
        "top 10 countdown",
        "story / documentary style",
        "comparison: X vs Y",
        "complete beginner's guide",
        "myths busted",
    ],
}


TRENDING_FORMATS = [
    "what happened and why India is searching it",
    "3 things to know about this trend",
    "the story behind the trend",
    "the surprising fact behind today's trend",
]
HT = "{https://trends.google.com/trending/rss}"


def google_trends_india():
    try:
        resp = requests.get(TRENDS_RSS, timeout=20)
        resp.raise_for_status()
        return [item.findtext("title") for item in ET.fromstring(resp.content).iter("item")][:25]
    except (requests.RequestException, ET.ParseError):
        return []


def pick_format(kind):
    formats = TRENDING_FORMATS if config.TOPIC_MODE == "trending" else FORMATS[kind]
    recent = history.recent_formats(kind, n=3)
    choices = [f for f in formats if f not in recent] or formats
    return random.choice(choices)


def _traffic(text):
    """'2K+' -> 2000, '200+' -> 200."""
    m = re.match(r"([\d.]+)\s*([KM]?)", text or "")
    if not m:
        return 0
    return float(m.group(1)) * {"": 1, "K": 1_000, "M": 1_000_000}[m.group(2)]


def _article_text(url, max_words=180):
    """Readable paragraph text from a news article (free, no API). Empty if the site blocks us."""
    try:
        resp = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0 (ytauto news reader)"})
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    paras = [html.unescape(re.sub(r"<[^>]+>", " ", p)) for p in re.findall(r"<p[^>]*>(.*?)</p>", resp.text, re.S)]
    words = " ".join(" ".join(p.split()) for p in paras if len(p.split()) > 8).split()
    return " ".join(words[:max_words])


def trending_items(limit=6):
    """Top Google Trends India searches right now, each with its news headlines and one article excerpt."""
    resp = requests.get(TRENDS_RSS, timeout=20)
    resp.raise_for_status()
    items = []
    for item in ET.fromstring(resp.content).iter("item"):
        news = [{"title": n.findtext(f"{HT}news_item_title") or "", "url": n.findtext(f"{HT}news_item_url") or "",
                 "source": n.findtext(f"{HT}news_item_source") or ""} for n in item.iter(f"{HT}news_item")]
        items.append({"query": item.findtext("title"), "traffic": item.findtext(f"{HT}approx_traffic"), "news": news})
    items.sort(key=lambda i: _traffic(i["traffic"]), reverse=True)
    items = items[:limit]
    for it in items:
        it["excerpt"] = next((t for t in (_article_text(n["url"]) for n in it["news"][:2] if n["url"]) if len(t.split()) > 60), "")
    return items


def trending_brief(video_format):
    """Brief for the trending channel: today's real trends plus article excerpts, no paid web search."""
    past = "\n".join(f"- {t}" for t in history.recent_titles()) or "(none yet)"
    blocks = []
    for n, it in enumerate(trending_items(), 1):
        heads = "\n".join(f"    - {x['title']} ({x['source']}) {x['url']}" for x in it["news"][:3])
        blocks.append(f"{n}. Search: \"{it['query']}\" ({it['traffic']} searches)\n  Headlines:\n{heads}\n"
                      f"  Article excerpt: {it['excerpt'] or '(not available)'}")
    trends = "\n\n".join(blocks)
    return f"""Today is {date.today():%d %B %Y}. These are the top Google Trends searches in India right now, with news
headlines and an excerpt from one article for each:

{trends}

Pick the ONE trend that will make the most viewers stop scrolling, and explain it in the format "{video_format}".

Rules:
- Allowed: cricket and sports, movies, OTT and music releases, tech and gadget launches, science and space,
  festivals, exams and results, viral internet trends, weather (when nobody was hurt).
- Never pick: politics or elections, religion or communal topics, crime, deaths, accidents, disasters, war,
  celebrity gossip or personal lives, medical or financial advice. If a trend touches these, skip it.
- Do not repeat a trend already covered:
{past}
- Facts come ONLY from the headlines and excerpt above. If a detail is not there, leave it out; never guess
  scores, dates, prices or quotes. You may add widely known background facts you are certain of.
- Write it in your own words; never copy sentences from the articles.
- Say "आज" / "अभी" naturally so it feels current, and explain WHY everyone is searching it.
- In the description's "Sources:" line, list the article URLs you used."""


def _context():
    trends = "\n".join(f"- {t}" for t in google_trends_india()) or "(unavailable today)"
    past = "\n".join(f"- {t}" for t in history.recent_titles()) or "(none yet)"
    return trends, past


def short_brief(video_format):
    """Shorts skip paid web search: Claude picks an evergreen, well-documented fact itself."""
    trends, past = _context()
    return f"""No web research for this Short. Choose ONE topic yourself, in the format "{video_format}".

- Pick a fact about {config.CHANNEL_NICHE} that is well established and widely documented,
  that you are certain is correct, and that would surprise an Indian viewer. Prefer facts that relate
  to things Indians use every day (phones, UPI, internet, trains, weather, food science, space missions).
- If a Google Trends India item below fits the niche and you know solid facts about it, you may use it:
{trends}
- Skip politics, religion, tragedies, crime, celebrity gossip, medical or financial advice, and anything
  that may have changed recently (prices, rankings, "latest" records) since you cannot check it.
- Do not repeat or closely resemble any past video:
{past}
- In the description's "Sources:" line, name the kind of source (e.g. NASA, ISRO, IEEE) instead of URLs."""


def research_topic(kind, video_format):
    trends_text, past = _context()
    length = "a 50-second YouTube Short" if kind == "short" else "a 7-8 minute YouTube video"

    prompt = f"""Today is {date.today():%d %B %Y}. You are the researcher for a Hindi YouTube channel called "{config.CHANNEL_NAME}".
Channel niche: {config.CHANNEL_NICHE}.

Pick ONE topic for {length} in the format "{video_format}".

Choose a topic Indian viewers are curious about right now. Use web search to check what is trending in India
(news, tech launches, science discoveries, viral questions). Google Trends India today:
{trends_text}

Rules:
- Stay inside the channel niche. Skip politics, religion, tragedies, crime, celebrity gossip, medical or financial advice.
- Do not repeat or closely resemble any past video:
{past}
- Only use facts you have verified from reliable sources in your searches.

Reply in English with:
TOPIC: <one line>
WHY NOW: <one line on why it is timely or evergreen>
FACTS: <8-15 verified bullet points with numbers, names and dates where relevant>
SOURCES: <the URLs you relied on>"""
    return llm.research(prompt)
