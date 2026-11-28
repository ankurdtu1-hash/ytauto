"""Turn a research brief into a Hindi script plus YouTube metadata."""
import logging

from . import config, history, llm

log = logging.getLogger("ytauto")

SCHEMA = {
    "type": "object",
    "properties": {
        "title_options": {"type": "array", "items": {"type": "string"}},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "thumbnail_text": {"type": "string"},
        "cover_prompt": {"type": "string"},
        "cover_tagline": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string"},
                    "footage_queries": {"type": "array", "items": {"type": "string"}},
                    "image_prompt": {"type": "string"},
                },
                "required": ["narration", "footage_queries", "image_prompt"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title_options", "title", "description", "tags", "hashtags", "thumbnail_text", "cover_prompt", "cover_tagline", "scenes"],
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
  (objects, places, actions), 1-3 words each. Best is the real thing IN ACTION, the way stock video is
  tagged: thing + action, e.g. "excavator digging rock", "bullet train passing", "ship launching sea",
  "tiger running", "molten steel pouring". Moving footage of the actual subject keeps viewers watching. The visual must match the words being spoken, so a viewer
  with the sound off still follows. No abstract ideas, no brand logos.
  When the sentence is about a real, named person (actor, cricketer, scientist), place or event, the FIRST
  query must be just that exact full name in English, e.g. ["Ranbir Kapoor", "film shooting set", "cinema audience"].
  Those are searched in freely licensed photo libraries (Wikimedia Commons); the other two stay generic as a backup.
  Never ask for movie posters, film stills, trailers, match broadcasts or news photos: they are copyrighted.
- image_prompt: one English sentence (max 35 words) describing an illustration that shows THIS sentence,
  for an AI image generator. Concrete scene, subject, setting, mood. Generic people only: never a real
  person's name or likeness, no text, letters, numbers, logos, flags or religious symbols in the image."""


def write_script(kind, video_format, brief):
    fmt = config.FORMATS[kind]
    if kind == "short":
        structure = (
            "Scene 1 is the hook: a curiosity question or a surprising claim (max 10 words). Middle scenes deliver "
            "fast facts with an open loop and ONE twist the viewer does not expect. Last scene: the payoff, ending "
            "with a half-sentence that flows straight back into scene 1's first words, so when the Short replays it "
            "sounds like one continuous sentence (viewers rewatch without noticing). Put a one-line question that "
            "makes people comment as the FIRST line of the description instead. No 'like and subscribe'."
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
- Total narration: {fmt['words']}, split into {fmt['scenes']} scenes. {fmt['scene_rule']}
- {structure}
- Narration is written exactly as it should be spoken by a Hindi text-to-speech voice: Devanagari only,
  numbers written as words where natural, no emojis, no stage directions, no brackets.
{VISUALS}

Metadata rules (optimise click-through rate):
- title_options: first brainstorm 5 different titles, each built on a different trigger: curiosity gap,
  shock number, "forbidden"/little-known knowledge, comparison/status, fear of missing out. All follow the
  title rules below and stay honest.
- title: the strongest of title_options (the one a scrolling Indian viewer would tap first). Hinglish in Roman (English) letters, never Devanagari; 45-75 characters. Formula used by the biggest
  Hindi fact channels: ONE fitting emoji first, then a specific big number from the facts (tonnes, km/h, crore,
  years, records) when there is one, then a "kaise/kyu/kya" question or a bold claim, ending with "😱" or "?",
  e.g. "🚄 350 km/h ki train! 2.5 ghante ka safar 68 minute mein 😱", "🐦 Kauwa aapki shakal 5 saal yaad rakhta hai? 😱".
  Front-load the most surprising part. Stay honest. Never promise photos, videos, leaks, "exclusive" or "unseen" footage: the video only
  shows stock visuals.
- description: first line repeats the hook; then 3-4 Hindi lines summarising the video (name the key things,
  numbers and places, since search reads them); then a blank line and "Keywords:" followed by 15-20 search
  phrases, one per line (Hindi, Hinglish and English mix, specific to this video first, then the niche); then a
  "Sources:" line;
  then this disclosure on its own line: "इस वीडियो में AI voice, AI images और stock footage (Pixabay, Pexels, NASA, Openverse, Wikimedia Commons) का इस्तेमाल किया गया है।"
- tags: 15-20 specific search phrases people actually type (names of the exact things in the video first, then
  broader niche phrases), in Hindi, Hinglish and English; together under 450 characters.
- hashtags: 10-15 hashtags starting with #, the first three the most important (YouTube shows them above the
  title), specific to the video and the niche,{' and include #Shorts' if kind == 'short' else ''}.
- thumbnail_text: the big words on the cover, 2-4 Hinglish words in Roman letters (max 22 characters) that make people tap:
  a shocking number, a bold claim or a question that teases the payoff without giving it away,
  e.g. "21 Chhakke!", "Ye Sach Hai?", "AI ne kar dikhaya". Never Devanagari. Honest: it must match what the video says.
- cover_tagline: the attractive hook line on a yellow ribbon at the bottom of the cover: 3-6 Hinglish words
  in Roman letters, emotional and curious, ending in "!" or "?", that makes people NEED to watch and does not
  repeat thumbnail_text, e.g. "Sach jaan ke hil jaoge!", "Ye kisi ne socha bhi nahi tha!",
  "Aapke phone mein bhi hai ye?". Never Devanagari. Honest: no promise the video does not keep.
- cover_prompt: one English sentence (max 40 words) for an AI image generator: the scroll-stopping cover
  image of this video. One big, clear subject filling the frame, close-up, dramatic lighting, bold
  saturated colours, strong contrast, a sense of drama or wonder; a generic person with a strong
  emotion (shocked, amazed) when it fits. Generic people only: never a real person's name or likeness.
  If the video is about a real, named person, show NO person who could be mistaken for them: show the
  setting or objects instead (stadium under floodlights, cricket ball and bat, trophy, film camera, phone).
  No text, letters, numbers, brand logos, flags or religious symbols anywhere, including on clothing."""
    effort = "low" if kind == "short" else "medium"
    script = llm.structured(prompt, SCHEMA, system=SYSTEM, effort=effort)
    for _ in range(2):  # hard check: never the same topic twice
        repeat = history.similar_title(script["title"])
        if not repeat:
            break
        log.warning("Topic repeats a past video (%s); asking for a different topic", repeat)
        script = llm.structured(prompt + f"\n\nIMPORTANT: \"{script['title']}\" repeats the past video \"{repeat}\". "
                                "Choose a completely different topic.", SCHEMA, system=SYSTEM, effort=effort)
    else:
        if history.similar_title(script["title"]):
            raise RuntimeError("Could not find a topic that is not a repeat; skipping today rather than duplicating")
    words = sum(len(s["narration"].split()) for s in script["scenes"])
    if words < MIN_WORDS[kind]:
        log.warning("Script has only %d words; asking for a longer one", words)
        longer = llm.structured(prompt + f"\n\nIMPORTANT: your last draft had only {words} words of narration. "
                                f"Write {fmt['words']}, in {fmt['scenes']} scenes.", SCHEMA, system=SYSTEM, effort=effort)
        if sum(len(s["narration"].split()) for s in longer["scenes"]) > words:
            script = longer
    return script


MIN_WORDS = {"short": 110, "long": 800}
