"""Hindi text-to-speech with word timings (Microsoft neural voices via edge-tts)."""
import asyncio
import logging
import re
import time

import edge_tts

from . import config

TICKS_PER_SECOND = 10_000_000  # edge-tts reports offsets in 100 ns units
log = logging.getLogger("ytauto")


async def _speak(text, out_path):
    communicate = edge_tts.Communicate(text, config.TTS_VOICE, rate=config.TTS_RATE, boundary="WordBoundary")
    words = []
    with open(out_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / TICKS_PER_SECOND
                words.append((start, start + chunk["duration"] / TICKS_PER_SECOND, chunk["text"]))
    return words


def speak(text, out_path, retries=6):
    """Write an MP3 to out_path and return [(start_s, end_s, word), ...]."""
    for attempt in range(retries):
        try:
            return asyncio.run(_speak(text, out_path))
        except Exception as e:  # the free service drops requests now and then (NoAudioReceived, network)
            if attempt == retries - 1:
                raise
            log.warning("TTS attempt %d failed (%s); retrying", attempt + 1, e)
            time.sleep(10 * (attempt + 1))
            # A stray symbol can make the service return nothing; speak plain words on later tries.
            if attempt >= 2:
                text = re.sub(r"[^\w\s।,.?!-]", " ", text)
