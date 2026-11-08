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
                    "footage_queries": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["narration", "footage_queries"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "description", "tags", "hashtags", "thumbnail_text", "scenes"],
    "additionalProperties": False,
}

# Built on the channel's reference prompts ("refer prompt" folder): elite strategist/producer,
# optimise click-through rate and audience retention, hooks, storytelling structure, CTA.
SYSTEM = f"""You are an elite YouTube content strategist and video producer for "{config.CHANNEL_NAME}",
a faceless Hindi channel ({config.CHANNEL_NICHE}). Every script you write is engineered for two numbers:
click-through rate (the title and thumbnail make people tap) and audience retention (they watch to the end).

Retention craft you always apply:
- Hook in the first 2 seconds: a shocking fact, a bold claim or a "what if" that opens a curiosity gap.
- Never slow down: one idea per sentence, short punchy sentences, no filler, no greetings, no "दोस्तों आज हम".
- Keep an open loop running ("लेकिन असली वजह इससे भी अजीब है...") and pay it off near the end.
- Pattern interrupt every few sentences: a surprising number, a comparison, a direct question to the viewer.
- End on the strongest payoff, then one short call to action.

Voice: a fast, excited, friendly narrator talking to a friend in everyday Hindi (Devanagari), keeping common
English words (phone, internet, AI, battery) in English the way people actually speak.

Accuracy is non-negotiable: every claim comes from the research brief or, when there is no research, is a
well-established fact you are certain of. Never invent numbers. Curiosity, yes; clickbait lies, never."""

VISUALS = """- footage_queries: 3 English stock-footage searches for THIS sentence, most specific first, e.g.
  ["tv remote infrared light", "remote control closeup", "living room television"].
  Describe what should literally be ON SCREEN while this sentence is spoken: concrete, filmable nouns
  (objects, places, actions), 1-3 words each. The visual must match the words being spoken, so a viewer
  with the sound off still follows. No abstract ideas, no brand names, no famous people."""


def write_script(kind, video_format, brief):
    fmt = config.FORMATS[kind]
    if kind == "short":
        structure = (
            "Scene 1 is the hook (max 10 words). Middle scenes deliver fast facts with an open loop. "
            "Last scene: the payoff plus a one-line question that makes people comment. No 'like and subscribe'."
        )
    else:
        structure = (
            "Open with a 10-second hook and a one-line promise of what the viewer will get. Build the body as a "
            "story in clear sections, each ending with a mini cliffhanger into the next. Put a strong curiosity "
            "hook at the midpoint. End with the biggest payoff, a 2-line recap and a natural call to subscribe."
        )

    prompt = f"""Write a Hindi YouTube {kind} in the format "{video_format}" based on this brief:

{brief}

Script rules:
- Total narration: {fmt['words']}, split into {fmt['scenes']} scenes. Each scene is ONE short spoken sentence
  (max ~12 words) so the picture changes every 2-4 seconds.
- {structure}
- Narration is written exactly as it should be spoken by a Hindi text-to-speech voice: Devanagari only,
  numbers written as words where natural, no emojis, no stage directions, no brackets.
{VISUALS}

Metadata rules (optimise click-through rate):
- title: Hindi/Hinglish, under 60 characters, front-load the most surprising word, create a curiosity gap,
  but stay honest.
- description: first line repeats the hook; then 2-4 Hindi lines summarising the video; then a "Sources:" line;
  then this disclosure on its own line: "इस वीडियो में AI voice और stock footage (Pixabay, NASA, Openverse) का इस्तेमाल किया गया है।"
- tags: 12-18 search phrases people actually type, in Hindi, Hinglish and English.
- hashtags: 3-5 hashtags starting with #{' and include #Shorts' if kind == 'short' else ''}.
- thumbnail_text: 2-4 bold Hindi words that tease the payoff without giving it away."""
    return llm.structured(prompt, SCHEMA, system=SYSTEM, effort="low" if kind == "short" else "medium")
