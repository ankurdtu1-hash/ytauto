"""Channel branding: logo (800x800) and banner (2560x1440) for the current CHANNEL_PROFILE.

AI background art from Cloudflare Workers AI (FLUX.1 schnell), text by libass. Output in output/branding/.
Upload them yourself in YouTube Studio > Customisation > Branding (the API cannot set profile pictures).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ytauto import config, footage  # noqa: E402
from ytauto.render import _run  # noqa: E402

BRAND = {
    "trending": {
        "logo_art": "abstract glowing upward arrow made of fire and light, red orange and gold, burst of sparks, "
                    "dark background, centred emblem, bold and simple",
        "banner_art": "wide panoramic collage of India's buzz: cricket stadium under floodlights, cinema lights, "
                      "smartphone glowing, fireworks over a city skyline at night, vibrant red and orange tones",
        "mono": "TKH", "colour": "&H002A2AE8",
        "name": "TRENDING KYA HAI",
        "tagline": "India mein aaj kya trend kar raha hai, sirf 40 second mein",
        "sub": "Roz naye Shorts  |  Cricket  |  Movies  |  Tech  |  Viral",
    },
    "main": {
        "logo_art": "glowing futuristic AI microchip with neon blue circuit lines and an orange spark, "
                    "dark background, centred emblem, bold and simple",
        "banner_art": "wide panoramic futuristic technology scene: glowing circuit board city, robot hand, "
                      "smartphone, satellites and stars, neon blue and orange light",
        "mono": "TS", "colour": "&H00E5881E",
        "name": "TECHSEEKHO AI",
        "tagline": "AI, Tech aur Science ki baatein, aasaan Hindi mein",
        "sub": "Roz naye Shorts  |  AI  |  Gadgets  |  Internet  |  Science",
    },
    "cricket": {
        "logo_art": "glowing red cricket ball with bright seam, sparks and motion trail, dark background, "
                    "centred emblem, bold and simple",
        "banner_art": "wide panoramic cricket stadium at night under floodlights, packed crowd, fireworks, "
                      "green pitch, blue and gold tones, no people in focus",
        "mono": "CKK", "colour": "&H00B5761A", "label": "CRICKET",
        "name": "CRICKET KI KAHANIYAN",
        "tagline": "Cricket ke records, kisse aur kamaal, aasaan Hindi mein",
        "sub": "Roz naye Shorts  |  Records  |  Legends  |  World Cup  |  IPL",
    },
    "animals": {
        "logo_art": "majestic tiger face made of glowing golden light, jungle leaves, dark green background, "
                    "centred emblem, bold and simple",
        "banner_art": "wide panoramic wildlife scene: tiger, elephant, peacock, eagle and dolphin in a lush jungle "
                      "meeting the ocean, golden sunlight, vivid greens",
        "mono": "JKD", "colour": "&H00359C2E", "label": "WILDLIFE",
        "name": "JANWAR KI DUNIYA",
        "tagline": "Janwaron ki hairan kar dene wali duniya",
        "sub": "Roz naye Shorts  |  Jungle  |  Samundar  |  Pakshi  |  Facts",
    },
    "places": {
        "logo_art": "glowing globe with a golden compass rose and light trails, deep blue background, "
                    "centred emblem, bold and simple",
        "banner_art": "wide panoramic collage of world wonders: mountains, desert dunes, ancient fort, ice cave, "
                      "floating village, golden hour light, epic travel feel",
        "mono": "AGD", "colour": "&H00A0522D", "label": "DUNIYA",
        "name": "AJAB GAJAB DUNIYA",
        "tagline": "Duniya ki sabse anokhi jagah, sirf 40 second mein",
        "sub": "Roz naye Shorts  |  Desh  |  Shehar  |  Ajoobe  |  Geography",
    },
    "money": {
        "logo_art": "shining gold rupee coin with glowing upward arrow, deep green background, "
                    "centred emblem, bold and simple",
        "banner_art": "wide panoramic premium business scene: city skyline at dusk, glowing gold coins, "
                      "growth arrows, factory and shop fronts, deep green and gold tones",
        "mono": "PG", "colour": "&H00347A1E", "label": "BUSINESS",
        "name": "PAISA GYAAN",
        "tagline": "Paisa, business aur brands ki kahani, aasaan Hindi mein",
        "sub": "Roz naye Shorts  |  Brands  |  Business  |  Banking  |  Money",
    },
}[config.PROFILE]

OUT = config.OUTPUT_DIR / "branding"
FONT = "Noto Sans"
YELLOW, WHITE, BLACK = "&H0000D8FF", "&H00FFFFFF", "&H00000000"


def ass(path, w, h, styles, events):
    path.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{chr(10).join(styles)}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(f"Dialogue: 1,0:00:00.00,0:00:10.00,{e}" for e in events)}
""", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for kind in ("logo", "banner"):
        art = OUT / f"{kind}_art.jpg"
        for attempt in range(4):  # Cloudflare sometimes answers 500 for a moment
            if footage.ai_image(BRAND[f"{kind}_art"], art):
                break
            time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f"AI art failed for {kind}")

    # Logo: art inside a coloured ring, big monogram in the middle (YouTube shows it as a circle).
    a = OUT / "logo.ass"
    ass(a, 800, 800, [
        f"Style: C,{FONT},20,{BRAND['colour']},{BRAND['colour']},{WHITE},&H00000000,0,0,0,0,100,100,0,0,1,14,0,7,0,0,0,1",
        f"Style: M,{FONT},300,{WHITE},{WHITE},{BLACK},&H80000000,-1,0,0,0,100,100,-6,0,1,16,10,5,0,0,0,1",
        f"Style: S,{FONT},62,{BLACK},{BLACK},{YELLOW},{YELLOW},-1,0,0,0,100,100,4,0,3,14,0,5,0,0,0,1",
    ], [
        "C,,0,0,0,,{\\pos(0,0)\\1a&H50&\\p1}m 400 70 b 582 70 730 218 730 400 b 730 582 582 730 400 730 "
        "b 218 730 70 582 70 400 b 70 218 218 70 400 70{\\p0}",
        f"M,,0,0,0,,{{\\pos(400,370)}}{BRAND['mono']}",
        f"S,,0,0,0,,{{\\pos(400,585)}} {BRAND.get('label') or ('TRENDING' if config.PROFILE == 'trending' else 'AI • TECH')} ",
    ])
    _run(["-y", "-i", str(OUT / "logo_art.jpg"), "-frames:v", "1", "-vf",
          "scale=800:800:force_original_aspect_ratio=increase,crop=800:800,eq=contrast=1.15:saturation=1.4,"
          "eq=brightness=0.06:saturation=1.3,vignette=PI/5,"
          f"ass={a.name}", "-q:v", "2", "logo.jpg"], cwd=OUT)

    # Banner: everything important inside the 1546x423 centre box that shows on every device.
    b = OUT / "banner.ass"
    ass(b, 2560, 1440, [
        f"Style: N,{FONT},150,{WHITE},{WHITE},{BLACK},&H80000000,-1,0,0,0,100,100,4,0,1,10,8,5,0,0,0,1",
        f"Style: T,{FONT},56,{BLACK},{BLACK},{YELLOW},{YELLOW},-1,0,0,0,100,100,0,0,3,16,0,5,0,0,0,1",
        f"Style: U,{FONT},44,{WHITE},{WHITE},{BLACK},&H80000000,-1,0,0,0,100,100,1,0,1,4,3,5,0,0,0,1",
    ], [
        f"N,,0,0,0,,{{\\pos(1280,640)}}{BRAND['name']}",
        f"T,,0,0,0,,{{\\pos(1280,760)}} {BRAND['tagline']} ",
        f"U,,0,0,0,,{{\\pos(1280,845)}}{BRAND['sub']}",
    ])
    _run(["-y", "-i", str(OUT / "banner_art.jpg"), "-frames:v", "1", "-vf",
          "scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,eq=contrast=1.1:saturation=1.35,"
          "boxblur=6:1,drawbox=x=0:y=500:w=iw:h=440:color=black@0.45:t=fill,vignette=PI/4,"
          f"ass={b.name}", "-q:v", "2", "banner.jpg"], cwd=OUT)
    print("made", OUT / "logo.jpg", OUT / "banner.jpg")


if __name__ == "__main__":
    main()
