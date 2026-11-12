"""Hindi text-to-speech with word timings.

Main engine: OmniVoice (k2-fsa, Apache 2.0), free and local, cloning the channel narrator from
assets/voice/narrator.wav (a voice generated with OmniVoice voice design, so no real person is cloned).
Backup engine: Microsoft neural voices via edge-tts, used if OmniVoice is unavailable or fails.
"""
import asyncio
import logging
import os
import re
import time

import edge_tts

from . import config

TICKS_PER_SECOND = 10_000_000  # edge-tts reports offsets in 100 ns units
log = logging.getLogger("ytauto")

ENGINE = os.getenv("TTS_ENGINE", "omnivoice")
NARRATOR_WAV = config.ROOT / "assets" / "voice" / "narrator.wav"
NARRATOR_TEXT = ("क्या आप जानते हैं? भारत ने सिर्फ बानवे रन पर पूरी टीम आउट कर दी! "
                 "आज हर कोई यही सर्च कर रहा है, और इसके पीछे की कहानी सच में हैरान कर देगी।")
OMNI_SPEED = float(os.getenv("OMNI_SPEED", "1.1"))
OMNI_STEPS = int(os.getenv("OMNI_STEPS", "16"))
_omni = None  # (model, voice prompt), loaded once per run


# ---------- OmniVoice ----------

def _load_omni():
    global _omni
    if _omni is None:
        import torch
        from omnivoice import OmniVoice
        torch.set_num_threads(os.cpu_count() or 4)
        model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu", dtype=torch.float32)
        prompt = model.create_voice_clone_prompt(ref_audio=str(NARRATOR_WAV), ref_text=NARRATOR_TEXT)
        _omni = (model, prompt)
        log.info("OmniVoice narrator loaded")
    return _omni


def _estimate_words(text, seconds):
    """OmniVoice gives no word timings: spread words over the clip by length (good enough for 3-word captions)."""
    words = text.split()
    if not words:
        return []
    lead, tail = min(0.12, seconds * 0.05), min(0.15, seconds * 0.05)
    span = max(seconds - lead - tail, 0.1)
    weights = [len(re.sub(r"[^\w]", "", w)) + 2 for w in words]
    total, t, out = sum(weights), lead, []
    for w, wt in zip(words, weights):
        d = span * wt / total
        out.append((t, t + d, w))
        t += d
    return out


def _speak_omni(text, out_path):
    import soundfile as sf
    model, prompt = _load_omni()
    audio = model.generate(text=text, voice_clone_prompt=prompt, speed=OMNI_SPEED, num_step=OMNI_STEPS)[0]
    sf.write(str(out_path), audio, 24000, format="WAV")
    return _estimate_words(text, len(audio) / 24000)


# ---------- edge-tts backup ----------

async def _speak_edge_async(text, out_path):
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


def _speak_edge(text, out_path, retries=6):
    for attempt in range(retries):
        try:
            return asyncio.run(_speak_edge_async(text, out_path))
        except Exception as e:  # the free service drops requests now and then (NoAudioReceived, network)
            if attempt == retries - 1:
                raise
            log.warning("TTS attempt %d failed (%s); retrying", attempt + 1, e)
            time.sleep(10 * (attempt + 1))
            # A stray symbol can make the service return nothing; speak plain words on later tries.
            if attempt >= 2:
                text = re.sub(r"[^\w\s।,.?!-]", " ", text)


def speak(text, out_path):
    """Write audio to out_path and return [(start_s, end_s, word), ...]."""
    global ENGINE
    if ENGINE == "omnivoice":
        try:
            return _speak_omni(text, out_path)
        except Exception as e:  # never lose a video over the voice: switch to the backup for the rest of the run
            log.warning("OmniVoice failed (%s); using edge-tts for this video", e)
            ENGINE = "edge"
    return _speak_edge(text, out_path)
