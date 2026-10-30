"""Turn a research brief into a Hindi script plus YouTube metadata."""
from . import config, llm

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "thumbnail_text": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string"},
                    "footage_query": {"type": "string"},
                },
                "required": ["narration", "footage_query"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "description", "tags", "hashtags", "thumbnail_text", "scenes"],
    "additionalProperties": False,
}

SYSTEM = f"""You write scripts for "{config.CHANNEL_NAME}", a Hindi YouTube channel ({config.CHANNEL_NICHE}).
The voice is a friendly, curious narrator talking to a friend: simple everyday Hindi (Devanagari script),
with common English words (phone, internet, AI, battery) kept in English the way people actually speak.
Every claim must come from the research brief; never invent numbers. Each video should feel hand-made:
a strong hook, a clear payoff, and an original angle rather than a generic list."""


def write_script(kind, video_format, brief):
    fmt = config.FORMATS[kind]
    if kind == "short":
        structure = (
            "First scene is a 1-sentence hook that creates curiosity in under 3 seconds. "
            "End with a one-line question to the viewer to drive comments. No 'like and subscribe' speech."
        )
    else:
        structure = (
            "Open with a 15-second hook, then a one-line promise of what the viewer will learn. "
            "Build the body in clear sections, add a mid-video curiosity hook, and end with a short summary "
            "and a natural call to subscribe."
        )

    prompt = f"""Write a Hindi YouTube {kind} in the format "{video_format}" from this research brief:

{brief}

Script rules:
- Total narration: {fmt['words']}, split into {fmt['scenes']} scenes. Each scene is 1-3 spoken sentences.
- {structure}
- Narration is written exactly as it should be spoken by a Hindi text-to-speech voice: Devanagari only,
  numbers written as words where natural, no emojis, no stage directions, no brackets.
- footage_query: 2-4 English words describing generic stock footage that fits the scene
  (e.g. "smartphone charging closeup", "night sky stars"). No brand names or famous people.

Metadata rules:
- title: Hindi/Hinglish, under 70 characters, curiosity-driven but honest (no clickbait lies).
- description: 3-5 Hindi lines summarising the video, then a "Sources:" line with the main URLs from the brief,
  then this disclosure on its own line: "इस वीडियो में AI voice और stock footage (Pixabay) का इस्तेमाल किया गया है।"
- tags: 12-18 search phrases in Hindi, Hinglish and English.
- hashtags: 3-5 hashtags starting with #{' and include #Shorts' if kind == 'short' else ''}.
- thumbnail_text: 2-4 bold Hindi words for the thumbnail."""
    return llm.structured(prompt, SCHEMA, system=SYSTEM)
