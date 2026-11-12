"""Make the same Hindi narration in several free voices so we can compare them by ear.

Usage: python tools/voice_samples.py edge|kokoro|parler   (writes voice_samples/*.wav|mp3)
"""
import asyncio
import pathlib
import sys

TEXT = ("क्या आप जानते हैं? भारत ने सिर्फ बानवे रन पर पूरी टीम आउट कर दी! "
        "आज हर कोई यही सर्च कर रहा है, और इसके पीछे की कहानी सच में हैरान कर देगी।")
OUT = pathlib.Path("voice_samples")
OUT.mkdir(exist_ok=True)


def edge():
    import edge_tts
    voices = ["hi-IN-SwaraNeural", "hi-IN-MadhurNeural", "en-US-AndrewMultilingualNeural",
              "en-US-AvaMultilingualNeural", "en-US-BrianMultilingualNeural", "en-US-EmmaMultilingualNeural"]

    async def run():
        for v in voices:
            for rate in ("+0%", "+30%"):
                try:
                    await edge_tts.Communicate(TEXT, v, rate=rate).save(str(OUT / f"edge_{v}_{rate[1:]}.mp3"))
                    print("ok", v, rate)
                except Exception as e:  # noqa: BLE001
                    print("failed", v, e)
    asyncio.run(run())


def kokoro():
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="h")
    for voice in ("hf_alpha", "hf_beta", "hm_omega", "hm_psi"):
        for speed in (1.0, 1.25):
            audio = [a for _, _, a in pipe(TEXT, voice=voice, speed=speed)]
            sf.write(OUT / f"kokoro_{voice}_{speed}.wav", np.concatenate(audio), 24000)
            print("ok", voice, speed)


def parler():
    import soundfile as sf
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    name = "ai4bharat/indic-parler-tts"
    model = ParlerTTSForConditionalGeneration.from_pretrained(name)
    tok = AutoTokenizer.from_pretrained(name)
    desc_tok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    speakers = {"Rohit": "his", "Divya": "her", "Aman": "his", "Rani": "her"}
    for spk, pron in speakers.items():
        desc = (f"{spk} speaks with an energetic, expressive and engaging tone at a fast pace, like a popular "
                f"YouTube narrator. The recording is very clear with no background noise, close to {pron} microphone.")
        d = desc_tok(desc, return_tensors="pt")
        p = tok(TEXT, return_tensors="pt")
        with torch.no_grad():
            gen = model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                                 prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask)
        sf.write(OUT / f"parler_{spk}.wav", gen.cpu().numpy().squeeze(), model.config.sampling_rate)
        print("ok", spk)


{"edge": edge, "kokoro": kokoro, "parler": parler}[sys.argv[1]]()
