"""Find a trending, fresh topic and gather verified facts for it."""
import random
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


def google_trends_india():
    try:
        resp = requests.get(TRENDS_RSS, timeout=20)
        resp.raise_for_status()
        return [item.findtext("title") for item in ET.fromstring(resp.content).iter("item")][:25]
    except (requests.RequestException, ET.ParseError):
        return []


def pick_format(kind):
    recent = history.recent_formats(kind, n=3)
    choices = [f for f in FORMATS[kind] if f not in recent] or FORMATS[kind]
    return random.choice(choices)


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
