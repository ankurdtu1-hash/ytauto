"""Make one video end to end:  python run.py short|long [--no-upload] [--script-only]"""
import argparse
import json
import logging
import re
import shutil
from datetime import datetime

from ytauto import config, footage, history, llm, render, topics, upload, voice, writer

log = logging.getLogger("ytauto")


def make_video(kind, do_upload=True, script_only=False):
    fmt = config.FORMATS[kind]
    video_format = topics.pick_format(kind)

    if kind == "short":
        brief = topics.short_brief(video_format)
    else:
        log.info("Researching a long-video topic (format: %s)", video_format)
        brief = topics.research_topic(kind, video_format)

    log.info("Writing script")
    script = writer.write_script(kind, video_format, brief)
    log.info("Title: %s", script["title"])

    slug = re.sub(r"[^a-z0-9]+", "-", script["scenes"][0]["footage_query"].lower()).strip("-")[:30]
    workdir = config.OUTPUT_DIR / f"{datetime.now():%Y%m%d-%H%M}_{kind}_{slug}"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "brief.txt").write_text(brief, encoding="utf-8")
    (workdir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    if script_only:
        log.info("Script saved in %s", workdir)
        return workdir

    scene_videos, scene_audios, events, used_ids = [], [], [], footage.load_used()
    offset = 0.0
    for i, scene in enumerate(script["scenes"]):
        log.info("Scene %d/%d", i + 1, len(script["scenes"]))
        mp3 = workdir / f"voice_{i:03d}.mp3"
        words = voice.speak(scene["narration"], mp3)
        length = render.frame_aligned(render.duration(mp3))

        raw = workdir / f"raw_{i:03d}.mp4"
        if not footage.fetch_clip(scene["footage_query"], raw, fmt, used_ids):
            raise RuntimeError(f"No stock footage found for scene {i}")
        scene_videos.append(workdir / f"scene_{i:03d}.mp4")
        scene_audios.append(workdir / f"voice_{i:03d}.wav")
        render.scene_video(raw, scene_videos[-1], length, fmt)
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
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for tool in ("ffmpeg", "ffprobe"):
        if not args.script_only and not shutil.which(tool):
            raise SystemExit(f"{tool} is not installed")
    make_video(args.kind, do_upload=not args.no_upload, script_only=args.script_only)
    log.info("Claude cost for this video: $%.3f", llm.spent_usd)


if __name__ == "__main__":
    main()
