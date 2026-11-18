"""python tools/make_narrator.py  --  design this channel's own narrator voice with OmniVoice (no real person).

Writes assets/voice/narrator_<CHANNEL_PROFILE>.wav; voice.py clones it for every video of that channel.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from omnivoice import OmniVoice  # noqa: E402

from ytauto import config  # noqa: E402
from ytauto.voice import NARRATOR_TEXT  # noqa: E402

instruct = config.PROFILES[config.PROFILE]["narrator"]
model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu", dtype=torch.float32)
torch.manual_seed(7)
audio = model.generate(text=NARRATOR_TEXT, instruct=instruct, speed=1.0)[0]
out = config.ROOT / "assets" / "voice" / f"narrator_{config.PROFILE}.wav"
sf.write(str(out), audio, 24000)
print(f"wrote {out} ({instruct})")
