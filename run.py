"""Make one video end to end:  python run.py short|long [--no-upload] [--script-only]"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import re
import shutil
from datetime import datetime

from ytauto import config, footage, history, llm, picker, render, topics, upload, voice, writer

log = logging.getLogger("ytauto")


def pick_visual(preferred, queries, out_base, fmt, used_ids, credits, max_tries=15):
    """First usable visual: Claude's picks first, then tag ranking; must pass the brightness check.

    Returns (path, is_photo, fit).
    """
    def ordered():
        yield from preferred
        yield from footage.candidates(queries, fmt, used_ids)

    tried = set()
    for cand in ordered():
        if len(tried) >= max_tries:
            break
        if cand["id"] in tried or cand["id"] in used_ids:
            continue
        tried.add(cand["id"])
        path = footage.download(cand, out_base)
        if not path:
            continue
        is_photo = cand["kind"] == "photo"
        if not render.looks_ok(path, is_photo):
            log.info("Skipped %s (too dark or too bright)", cand["id"])
            path.unlink()
            continue
        if not cand.get("ai"):
            used_ids.add(cand["id"])
        if cand["credit"] and cand["credit"] not in credits:
            credits.append(cand["credit"])
        return path, is_photo, bool(cand.get("fit"))
    raise RuntimeError(f"No usable visual for {queries}")


def make_video(kind, do_upload=True, script_only=False):
    fmt = config.FORMATS[kind]
    video_format = topics.pick_format(kind)

    if config.TOPIC_MODE == "trending":
        brief = topics.trending_brief(video_format)
    elif kind == "short":
        brief = topics.short_brief(video_format)
    else:
        log.info("Researching a long-video topic (format: %s)", video_format)
        brief = topics.research_topic(kind, video_format)

    log.info("Writing script")
    script = writer.write_script(kind, video_format, brief)
    log.info("Title: %s", script["title"])

    slug = re.sub(r"[^a-z0-9]+", "-", script["scenes"][0]["footage_queries"][0].lower()).strip("-")[:30]
    workdir = config.OUTPUT_DIR / f"{datetime.now():%Y%m%d-%H%M}_{kind}_{slug}"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "brief.txt").write_text(brief, encoding="utf-8")
    (workdir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    if script_only:
        log.info("Script saved in %s", workdir)
        return workdir

    scene_videos, scene_audios, events, used_ids, credits = [], [], [], footage.load_used(), []
    scenes = script["scenes"]
    log.info("Shortlisting visuals for %d scenes", len(scenes))
    shortlists = [footage.shortlist(s["footage_queries"], fmt, used_ids) for s in scenes]
    with ThreadPoolExecutor(3) as pool:  # free AI illustrations (Cloudflare), one per scene
        ai = list(pool.map(lambda i: footage.ai_image(scenes[i].get("image_prompt"), workdir / f"ai_{i:03d}.jpg"),
                           range(len(scenes))))
    for sl, cand in zip(shortlists, ai):
        if cand:
            sl.append(cand)
    log.info("AI illustrations made for %d of %d scenes", sum(1 for c in ai if c), len(scenes))
    for start in range(0, len(scenes), 20):  # Claude looks at the previews, 20 scenes per request
        shortlists[start:start + 20] = picker.choose(scenes[start:start + 20], shortlists[start:start + 20])
    offset = 0.0
    for i, scene in enumerate(script["scenes"]):
        log.info("Scene %d/%d", i + 1, len(script["scenes"]))
        mp3 = workdir / f"voice_{i:03d}.mp3"
        words = voice.speak(scene["narration"], mp3)
        length = render.frame_aligned(render.duration(mp3))

        raw, is_photo, fit = pick_visual(shortlists[i], scene["footage_queries"], workdir / f"raw_{i:03d}",
                                    fmt, used_ids, credits)
        scene_videos.append(workdir / f"scene_{i:03d}.mp4")
        scene_audios.append(workdir / f"voice_{i:03d}.wav")
        render.scene_video(raw, scene_videos[-1], length, fmt, is_photo, fit)
        render.scene_audio(mp3, scene_audios[-1], length)

        events += render.captions(words, scene["narration"], offset, length, fmt["words_per_caption"])
        offset += length

    log.info("Rendering final video (%.0f s)", offset)
    video, voice_track, subs = workdir / "video.mp4", workdir / "voice.wav", workdir / "subs.ass"
    render.concat(scene_videos, video, workdir)
    render.concat(scene_audios, voice_track, workdir)
    render.subtitles_for(kind, events, subs)
    final = workdir / "final.mp4"
    render.final_mix(workdir, video, voice_track, subs, final)

    thumb = None
    if kind == "long":
        thumb = workdir / "thumbnail.jpg"
        render.thumbnail(workdir, scene_videos[0], script["thumbnail_text"], thumb)

    # Keep only what is worth keeping.
    for pattern in ("raw_*", "scene_*", "voice_*", "*_list.txt", "video.mp4", "voice.wav"):
        for p in workdir.glob(pattern):
            p.unlink()

    script["credits"] = credits
    (workdir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    video_id = None
    if do_upload:
        log.info("Uploading to YouTube (%s)", config.UPLOAD_PRIVACY)
        video_id = upload.upload(final, script, kind, thumb)
        log.info("Uploaded: https://youtu.be/%s", video_id)

    footage.save_used(used_ids)
    history.add({"kind": kind, "format": video_format, "title": script["title"], "video_id": video_id,
                 "folder": workdir.name})
    return workdir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["short", "long"])
    parser.add_argument("--no-upload", action="store_true", help="make the video but do not upload")
    parser.add_argument("--script-only", action="store_true", help="only research and write the script")
    parser.add_argument("--once-a-day", action="store_true", help="skip if this channel already uploaded one today")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    today = datetime.now().date().isoformat()
    if args.once_a_day and any(i.get("video_id") and i["kind"] == args.kind and i["date"].startswith(today)
                               for i in history.load()):
        log.info("Already uploaded a %s today; skipping this scheduled run", args.kind)
        return
    for tool in ("ffmpeg", "ffprobe"):
        if not args.script_only and not shutil.which(tool):
            raise SystemExit(f"{tool} is not installed")
    make_video(args.kind, do_upload=not args.no_upload, script_only=args.script_only)
    log.info("Claude cost for this video: $%.3f", llm.spent_usd)


if __name__ == "__main__":
    main()
