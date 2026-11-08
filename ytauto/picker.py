"""Claude looks at small previews of the candidate visuals and picks the one that fits each sentence."""
import logging
from concurrent.futures import ThreadPoolExecutor

from . import footage, llm

log = logging.getLogger("ytauto")

SCHEMA = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"scene": {"type": "integer"}, "option": {"type": "integer"}},
                "required": ["scene", "option"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["picks"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You are the video editor of a Hindi YouTube channel. For each scene below you get the spoken
sentence and numbered preview images of candidate stock visuals. Pick the option that best shows what is being
said, so a viewer with the sound off still understands it.

Rules:
- Prefer a visual that literally shows the subject of the sentence over a vaguely related mood shot.
- Never pick religious symbols, flags, political imagery, gore, visible logos or watermarks, or text in a
  foreign language.
- Avoid near-duplicate visuals across neighbouring scenes.
- If none of the options fits at all, answer option -1.
Return one pick per scene."""


def choose(scenes, shortlists):
    """Reorder each scene's shortlist so Claude's pick comes first. Returns the reordered shortlists."""
    with ThreadPoolExecutor(8) as pool:
        thumbs = [list(pool.map(footage.thumbnail_b64, sl)) for sl in shortlists]

    content = [{"type": "text", "text": INSTRUCTIONS}]
    for i, (scene, sl, th) in enumerate(zip(scenes, shortlists, thumbs)):
        content.append({"type": "text", "text": f"\nScene {i}: {scene['narration']}"})
        for k, (cand, img) in enumerate(zip(sl, th)):
            if img:
                content.append({"type": "text", "text": f"Scene {i} option {k} ({cand['kind']}):"})
                content.append({"type": "image", "source": {"type": "base64", "media_type": img[0], "data": img[1]}})

    try:
        picks = llm.structured(content, SCHEMA, effort="low")["picks"]
    except Exception as e:  # never lose a video because the picker failed; fall back to tag ranking
        log.warning("Visual picker failed (%s); using tag ranking", e)
        return shortlists

    ordered = [list(sl) for sl in shortlists]
    for p in picks:
        i, k = p["scene"], p["option"]
        if 0 <= i < len(ordered) and 0 <= k < len(ordered[i]):
            ordered[i].insert(0, ordered[i].pop(k))
    log.info("Visual picker chose for %d of %d scenes", sum(1 for p in picks if p["option"] >= 0), len(scenes))
    return ordered
