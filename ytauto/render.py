"""Assemble scenes, voice, captions and music into the final video with FFmpeg."""
import math
import json
import random
import re
import subprocess

from . import config


def _run(args, cwd=None):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], cwd=cwd, check=True)


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _mean_luma(path, at):
    seek = ["-ss", f"{at:.2f}"] if at else []  # seeking a single still image skips its only frame
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *seek, "-i", str(path), "-frames:v", "1",
         "-vf", "scale=64:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    m = re.search(r"YAVG=([\d.]+)", out.stdout)
    return float(m.group(1)) if m else None


def looks_ok(path, is_photo):
    """Reject near-black or blown-out white visuals (fade-ins, light flashes, dark intros)."""
    points = [0] if is_photo else [0.3, min(2.0, max(duration(path) / 2, 0.3))]
    for at in points:
        luma = _mean_luma(path, at)
        if luma is None or not 35 <= luma <= 215:
            return False
    return True


def frame_aligned(seconds, pause=0.08):
    """Scene length rounded up to whole frames so audio and video stay in sync."""
    return math.ceil((seconds + pause) * config.FPS) / config.FPS


# One consistent, slightly punchy colour grade so clips from different sources look like one video.
GRADE = "eq=contrast=1.06:saturation=1.15:gamma=0.98"


def scene_video(src, dst, seconds, fmt, is_photo=False, fit=False):
    w, h = fmt["width"], fmt["height"]
    if is_photo:
        # Slow Ken Burns zoom so a still photo still feels like motion. Upscale first to avoid zoom jitter.
        # fit=True (photos of people): show the whole photo over a blurred copy, so heads are never cropped.
        frames = math.ceil(seconds * config.FPS)
        step = 0.30 / max(frames, 1)  # 30% zoom over the scene: clearly moving, like a camera push
        move = sum(map(ord, dst.name)) % 4  # vary the move from scene to scene
        zoom = f"1.30-{step}*on" if move == 1 else f"min(1+{step}*on,1.30)"
        x = {2: f"(iw-iw/zoom)*on/{frames}", 3: f"(iw-iw/zoom)*(1-on/{frames})"}.get(move, "iw/2-(iw/zoom/2)")
        if fit:
            base = (f"split[a][b];[a]scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
                    f"boxblur=40:4,eq=brightness=-0.12[bg];[b]scale={w * 2}:{h * 2}:force_original_aspect_ratio=decrease[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2,")
        else:
            base = f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
        _run([
            "-i", str(src), "-t", f"{seconds:.3f}",
            "-vf", (base +
                    f"zoompan=z='{zoom}':d={frames}:x='{x}':y='ih/2-(ih/zoom/2)'"
                    f":s={w}x{h}:fps={config.FPS},setsar=1,{GRADE},scale=out_range=tv:out_color_matrix=bt709,format=yuv420p"),
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", str(dst),
        ])
        return
    _run([
        "-stream_loop", "-1", "-i", str(src), "-t", f"{seconds:.3f}",
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={config.FPS},setsar=1,{GRADE},format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", str(dst),
    ])


def scene_audio(src, dst, seconds):
    _run(["-i", str(src), "-af", "apad", "-t", f"{seconds:.3f}", "-ar", "48000", "-ac", "2", str(dst)])


def concat(paths, out, workdir):
    list_file = workdir / f"{out.stem}_list.txt"
    list_file.write_text("".join(f"file '{p.name}'\n" for p in paths), encoding="utf-8")
    _run(["-f", "concat", "-safe", "0", "-i", list_file.name, "-c", "copy", out.name], cwd=workdir)


# ---------- captions (ASS, rendered by libass so Devanagari shapes correctly) ----------

def _ts(seconds):
    cs = int(round(seconds * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _clean(text):
    return text.replace("{", "(").replace("}", ")").replace("\n", " ")


def captions(words, narration, offset, scene_len, per_caption):
    """Group word timings into on-screen caption events for one scene."""
    if not words:  # no timings from TTS: spread words evenly
        tokens = narration.split()
        step = (scene_len - 0.3) / max(len(tokens), 1)
        words = [(i * step, (i + 1) * step, t) for i, t in enumerate(tokens)]
    events = []
    groups = [words[i:i + per_caption] for i in range(0, len(words), per_caption)]
    for i, group in enumerate(groups):
        start = group[0][0]
        end = groups[i + 1][0][0] if i + 1 < len(groups) else min(group[-1][1] + 0.3, scene_len)
        events.append((offset + start, offset + end, " ".join(w[2] for w in group)))
    return events


def write_ass(path, events, width, height, font_size, alignment, margin_v, colour="&H00FFFFFF", outline=5):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{config.SUBTITLE_FONT},{font_size},{colour},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},2,{alignment},60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f"Dialogue: 0,{_ts(s)},{_ts(e)},Default,,0,0,0,,{_clean(t)}" for s, e, t in events]
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def subtitles_for(kind, events, path):
    fmt = config.FORMATS[kind]
    if kind == "short":
        write_ass(path, events, fmt["width"], fmt["height"], fmt["font_size"], alignment=5, margin_v=0)
    else:
        write_ass(path, events, fmt["width"], fmt["height"], fmt["font_size"], alignment=2, margin_v=70)


# ---------- final mix ----------

def _split_title(text):
    """Two balanced lines; the second (yellow) line carries the punch."""
    words = text.split()
    if len(words) < 2:
        return "", text
    best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:]))))
    return " ".join(words[:best]), " ".join(words[best:])


YELLOW, WHITE, BLACK = "&H0000D8FF", "&H00FFFFFF", "&H00000000"


def _cover_ass(path, text, seconds, w, h, tagline=None, still=False):
    """Thumbnail-style title block: big two-colour title, optional yellow tagline ribbon.
    Rendered by libass, so Devanagari shapes correctly."""
    line1, line2 = _split_title(_clean(text))
    longest = max(len(line1), len(line2), 1)
    size = max(110, min(200, int((w - 120) / (0.50 * longest))))
    top = int(h * 0.10)
    styles = [
        f"Style: T1,{config.SUBTITLE_FONT},{size},{WHITE},{WHITE},{BLACK},&H64000000,-1,0,0,0,100,100,0,0,1,14,8,8,0,0,0,1",
        f"Style: T2,{config.SUBTITLE_FONT},{int(size * 1.08)},{YELLOW},{YELLOW},{BLACK},&H64000000,-1,0,0,0,100,100,0,0,1,15,9,8,0,0,0,1",
        f"Style: Tag,{config.SUBTITLE_FONT},74,{BLACK},{BLACK},{YELLOW},{YELLOW},-1,0,0,0,100,100,0,0,3,20,0,2,0,0,0,1",
    ]
    end = _ts(seconds)
    fade = "" if still else "\\fad(0,200)"
    y1 = top
    y2 = y1 + (int(size * 1.12) if line1 else 0)
    events = []
    if line1:
        events.append(f"Dialogue: 2,{_ts(0)},{end},T1,,0,0,0,,{{\\pos({w // 2},{y1})\\frz2{fade}}}{line1}")
    events.append(f"Dialogue: 2,{_ts(0)},{end},T2,,0,0,0,,{{\\pos({w // 2},{y2})\\frz2{fade}}}{line2}")
    if tagline:
        events.append(f"Dialogue: 1,{_ts(0)},{end},Tag,,0,0,0,,{{\\pos({w // 2},{int(h * 0.80)})}}{_clean(tagline)}")
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
""" + "\n".join(styles) + """

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def cover_image(workdir, src, text, out, tagline=None, w=1080, h=1920):
    """The thumbnail: AI cover art, punchy grade, dark fades top and bottom, title and tagline."""
    ass = workdir / "cover_still.ass"
    _cover_ass(ass, text, 10, w, h, tagline=tagline, still=True)
    # smooth dark fades at the top (behind the title) and bottom (behind the ribbon), no banding
    fade = "255*(0.62*clip(1-Y/(H*0.52),0,1)+0.55*clip((Y-H*0.66)/(H*0.34),0,1))"
    _run([
        "-i", str(src), "-f", "lavfi", "-i", f"color=black:s={w}x{h}", "-frames:v", "1",
        "-filter_complex", (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"eq=contrast=1.15:saturation=1.4:brightness=0.02,unsharp=5:5:0.8,vignette=PI/4.5[bg];"
            f"[1:v]format=rgba,geq=r=0:g=0:b=0:a='{fade}'[g];"
            f"[bg][g]overlay=format=auto,ass={ass.name}"),
        "-q:v", "2", out.name,
    ], cwd=workdir)


def final_mix(workdir, video, voice, subs, out, cover_text=None, cover_seconds=0):
    tracks = sorted(config.MUSIC_DIR.glob("*.mp3")) if config.MUSIC_DIR.exists() else []
    args = ["-i", video.name, "-i", voice.name]
    cover = ""
    if cover_text and cover_seconds:  # title on the opening scene, so the first frame works as a cover
        w, h = config.FORMATS["short"]["width"], config.FORMATS["short"]["height"]
        _cover_ass(workdir / "cover.ass", cover_text, cover_seconds, w, h)
        cover = "ass=cover.ass,"
    if tracks:
        # random start point so the same track sounds different across videos
        args += ["-stream_loop", "-1", "-ss", str(random.randint(0, 60)), "-i", str(random.choice(tracks))]
        audio = "[2:a]volume=0.05[m];[1:a][m]amix=inputs=2:duration=first:normalize=0[a]"
    else:
        audio = "[1:a]anull[a]"
    args += [
        "-filter_complex", f"[0:v]{cover}ass={subs.name}[v];{audio}",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out.name,
    ]
    _run(args, cwd=workdir)


def thumbnail(workdir, first_scene, text, out):
    ass = workdir / "thumb.ass"
    write_ass(ass, [(0, 10, text)], 1280, 720, font_size=130, alignment=5, margin_v=0,
              colour="&H0000FFFF", outline=9)
    _run([
        "-ss", "1", "-i", first_scene.name, "-frames:v", "1",
        "-vf", "scale=1280:720,eq=brightness=-0.12:saturation=1.3,ass=thumb.ass", "-q:v", "2", out.name,
    ], cwd=workdir)


def quality_check(path, kind):
    """Problems found in the finished video (empty list = good to upload): length, picture size, sound,
    black screens and frozen (non-moving) stretches."""
    fmt = config.FORMATS[kind]
    problems = []
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                            "-of", "json", str(path)], capture_output=True, text=True)
    info = json.loads(probe.stdout or "{}")
    seconds = float(info.get("format", {}).get("duration", 0))
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if kind == "short" and not 25 <= seconds <= 180:
        problems.append(f"length {seconds:.0f}s (Shorts must be 25-180 s)")
    if not video or (video.get("width"), video.get("height")) != (fmt["width"], fmt["height"]):
        problems.append(f"picture size {video and (video.get('width'), video.get('height'))}")
    if not any(s.get("codec_type") == "audio" for s in streams):
        problems.append("no sound track")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", "blackdetect=d=0.5:pix_th=0.08,"
                        "freezedetect=n=0.002:d=2", "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    log_text = r.stderr
    black = sum(float(m) for m in re.findall(r"black_duration:([\d.]+)", log_text))
    frozen = sum(float(m) for m in re.findall(r"freeze_duration: ([\d.]+)", log_text))
    starts = re.findall(r"freeze_start: ([\d.]+)", log_text)
    if len(starts) > len(re.findall(r"freeze_end: ", log_text)):  # still frozen when the video ends
        frozen += seconds - float(starts[-1])
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", log_text)
    if black > 1.0:
        problems.append(f"{black:.1f}s of black screen")
    if frozen > 4.0:
        problems.append(f"{frozen:.1f}s of frozen picture")
    if not mean or float(mean.group(1)) < -35:
        problems.append(f"sound too quiet ({mean.group(1) if mean else '?'} dB)")
    return problems
