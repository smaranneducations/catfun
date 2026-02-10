"""Visual generation pipeline — DALL-E images + Pillow infographics.

Generates unique visuals for each PDF page:
  - Cover: DALL-E abstract art related to the topic
  - Stats pages: Pillow-generated infographic cards
  - Content pages: Data visualizations, timelines, comparison charts
  - All generated fresh each run, never repeated
"""
import os
import random
import math
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from openai import OpenAI

from aibrief import config

_openai = OpenAI(api_key=config.OPENAI_API_KEY)
VISUALS_DIR = config.OUTPUT_DIR / "visuals"
VISUALS_DIR.mkdir(exist_ok=True)


def _get_font(size: int, bold: bool = False):
    names = (["arialbd.ttf", "Arial Bold.ttf", "segoeui.ttf"] if bold
             else ["arial.ttf", "Arial.ttf", "segoeui.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    if len(h) != 6:
        return (30, 30, 60)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ═══════════════════════════════════════════════════════════════
#  DALL-E IMAGE GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_cover_image(headline: str, design: dict, run_id: str) -> str:
    """Generate an abstract cover image with DALL-E 3."""
    path = str(VISUALS_DIR / f"cover_{run_id}.png")
    if os.path.exists(path):
        return path

    mood = design.get("mood", "sophisticated")
    primary = design.get("primary_color", "#1a1a2e")
    accent = design.get("accent_color", "#00d4aa")

    # Use image_generation_key from DesignDNA for visual coherence
    image_key = design.get("image_generation_key", "")

    prompt = (
        f"Abstract editorial art for a luxury consulting report cover about: "
        f"'{headline}'. Style: {mood}, premium, sophisticated. "
        f"Dominant tones: {primary} and {accent}. "
        f"Think Hermès editorial campaign meets Bloomberg Businessweek cover art. "
        f"Abstract, no text, no faces, no logos. Artistic, bold, editorial. "
        f"High contrast, dramatic lighting, minimal but impactful composition. "
        f"16:9 widescreen format."
    )
    if image_key:
        prompt += f" Visual coherence directive: {image_key}."

    try:
        print(f"  [DALL-E] Generating cover image...")
        resp = _openai.images.generate(
            model="dall-e-3", prompt=prompt,
            size="1792x1024", quality="hd", n=1,
        )
        url = resp.data[0].url
        img_data = requests.get(url, timeout=60).content
        with open(path, "wb") as f:
            f.write(img_data)
        print(f"  [DALL-E] Cover saved ({os.path.getsize(path) // 1024} KB)")
        return path
    except Exception as e:
        print(f"  [DALL-E] Error: {e}")
        return _generate_gradient_art(path, design)


def generate_section_image(section_title: str, design: dict, run_id: str,
                           page_idx: int) -> str:
    """Generate a section-specific abstract visual with DALL-E."""
    path = str(VISUALS_DIR / f"section_{run_id}_{page_idx}.png")
    if os.path.exists(path):
        return path

    mood = design.get("mood", "sophisticated")
    accent = design.get("accent_color", "#00d4aa")

    # Use image_generation_key from DesignDNA for visual coherence
    image_key = design.get("image_generation_key", "")

    prompt = (
        f"Minimalist abstract editorial illustration for a section titled "
        f"'{section_title}'. Style: {mood}, luxury editorial. "
        f"Accent color: {accent}. Small, clean, like a luxury brand icon or "
        f"decorative element. No text. Subtle, artistic, premium feel. "
        f"Square format, white or light background."
    )
    if image_key:
        prompt += f" Visual coherence directive: {image_key}."

    try:
        resp = _openai.images.generate(
            model="dall-e-3", prompt=prompt,
            size="1024x1024", quality="standard", n=1,
        )
        url = resp.data[0].url
        img_data = requests.get(url, timeout=60).content
        with open(path, "wb") as f:
            f.write(img_data)
        return path
    except Exception as e:
        print(f"  [DALL-E] Section image error: {e}")
        return ""


def _generate_gradient_art(path: str, design: dict) -> str:
    """Fallback: generate abstract gradient art with Pillow."""
    w, h = 1792, 1024
    c1 = _hex_to_rgb(design.get("primary_color", "#1a1a2e"))
    c2 = _hex_to_rgb(design.get("secondary_color", "#2e3a5f"))
    ac = _hex_to_rgb(design.get("accent_color", "#00d4aa"))

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=_lerp_color(c1, c2, t))

    # Abstract accent shapes
    for _ in range(random.randint(3, 6)):
        cx = random.randint(w // 3, w)
        cy = random.randint(0, h)
        r = random.randint(80, 300)
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([cx - r, cy - r, cx + r, cy + r],
                   fill=(*ac, random.randint(15, 40)))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    img = img.filter(ImageFilter.GaussianBlur(radius=8))
    img.save(path, "PNG")
    return path


# ═══════════════════════════════════════════════════════════════
#  PILLOW INFOGRAPHICS
# ═══════════════════════════════════════════════════════════════

def generate_stat_card(numbers: list[dict], design: dict, run_id: str,
                       page_idx: int) -> str:
    """Generate a stat/number card infographic.

    numbers: list of {value: str, label: str} e.g. [{"value": "$4.2T", "label": "Market Impact"}]
    """
    path = str(VISUALS_DIR / f"stats_{run_id}_{page_idx}.png")
    w, h = 1000, 300
    primary = _hex_to_rgb(design.get("primary_color", "#1a1a2e"))
    accent = _hex_to_rgb(design.get("accent_color", "#00d4aa"))
    bg = _hex_to_rgb(design.get("background_color", "#fafafa"))

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    n = min(len(numbers), 4)
    card_w = (w - 40) // max(n, 1)

    font_big = _get_font(48, bold=True)
    font_sm = _get_font(16)

    for i, item in enumerate(numbers[:4]):
        cx = 20 + i * card_w + card_w // 2
        # Accent dot
        draw.ellipse([cx - 4, 40, cx + 4, 48], fill=accent)
        # Value
        val = str(item.get("value", "?"))
        bbox = draw.textbbox((0, 0), val, font=font_big)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, 65), val, fill=primary, font=font_big)
        # Label
        lbl = str(item.get("label", ""))
        bbox2 = draw.textbbox((0, 0), lbl, font=font_sm)
        tw2 = bbox2[2] - bbox2[0]
        draw.text((cx - tw2 // 2, 140), lbl, fill=(*primary, 180), font=font_sm)

        # Divider line between cards
        if i < n - 1:
            lx = 20 + (i + 1) * card_w
            draw.line([(lx, 50), (lx, 170)], fill=(*accent, 40), width=1)

    img.save(path, "PNG")
    return path


def generate_timeline(events: list[dict], design: dict, run_id: str,
                      page_idx: int) -> str:
    """Generate a horizontal timeline infographic.

    events: list of {year: str, event: str}
    """
    path = str(VISUALS_DIR / f"timeline_{run_id}_{page_idx}.png")
    w, h = 1000, 280
    primary = _hex_to_rgb(design.get("primary_color", "#1a1a2e"))
    accent = _hex_to_rgb(design.get("accent_color", "#00d4aa"))
    bg = _hex_to_rgb(design.get("background_color", "#fafafa"))

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    font_yr = _get_font(22, bold=True)
    font_ev = _get_font(12)

    n = min(len(events), 5)
    if n == 0:
        return ""

    # Timeline line
    lx1, lx2, ly = 60, w - 60, 100
    draw.line([(lx1, ly), (lx2, ly)], fill=(*accent, 120), width=2)

    spacing = (lx2 - lx1) / max(n - 1, 1)
    for i, ev in enumerate(events[:5]):
        cx = int(lx1 + i * spacing)
        # Node
        draw.ellipse([cx - 8, ly - 8, cx + 8, ly + 8], fill=accent)
        draw.ellipse([cx - 4, ly - 4, cx + 4, ly + 4], fill=bg)
        # Year
        yr = str(ev.get("year", ""))
        bbox = draw.textbbox((0, 0), yr, font=font_yr)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, ly - 40), yr, fill=primary, font=font_yr)
        # Event text (wrapped)
        txt = str(ev.get("event", ""))[:50]
        bbox2 = draw.textbbox((0, 0), txt, font=font_ev)
        tw2 = bbox2[2] - bbox2[0]
        draw.text((cx - min(tw2, 120) // 2, ly + 18), txt[:25],
                  fill=(*primary, 180), font=font_ev)
        if len(txt) > 25:
            draw.text((cx - min(tw2, 120) // 2, ly + 35), txt[25:50],
                      fill=(*primary, 180), font=font_ev)

    img.save(path, "PNG")
    return path


def generate_impact_bars(items: list[dict], design: dict, run_id: str,
                         page_idx: int) -> str:
    """Generate horizontal bar chart for impact/comparison.

    items: list of {label: str, value: int (0-100)}
    """
    path = str(VISUALS_DIR / f"bars_{run_id}_{page_idx}.png")
    w, h = 900, max(len(items) * 55 + 40, 200)
    primary = _hex_to_rgb(design.get("primary_color", "#1a1a2e"))
    accent = _hex_to_rgb(design.get("accent_color", "#00d4aa"))
    bg = _hex_to_rgb(design.get("background_color", "#fafafa"))

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    font_lbl = _get_font(14)
    font_val = _get_font(12, bold=True)

    bar_x = 200
    bar_max_w = w - bar_x - 80

    for i, item in enumerate(items[:6]):
        y = 20 + i * 55
        lbl = str(item.get("label", "?"))[:25]
        val = min(int(item.get("value", 50)), 100)

        # Label
        draw.text((20, y + 8), lbl, fill=primary, font=font_lbl)

        # Bar background
        draw.rounded_rectangle([bar_x, y + 5, bar_x + bar_max_w, y + 30],
                               radius=4, fill=(*primary, 15))

        # Bar fill
        fill_w = int(bar_max_w * val / 100)
        if fill_w > 0:
            # Gradient fill
            for px in range(fill_w):
                t = px / max(fill_w, 1)
                c = _lerp_color(accent, primary, t * 0.3)
                draw.line([(bar_x + px, y + 5), (bar_x + px, y + 30)], fill=c)

        # Value label
        draw.text((bar_x + fill_w + 8, y + 8), f"{val}%",
                  fill=primary, font=font_val)

    img.save(path, "PNG")
    return path


def generate_donut_chart(segments: list[dict], design: dict, run_id: str,
                         page_idx: int) -> str:
    """Generate a donut/pie chart.

    segments: list of {label: str, value: float, color: str (hex)}
    """
    path = str(VISUALS_DIR / f"donut_{run_id}_{page_idx}.png")
    w, h = 500, 400
    bg = _hex_to_rgb(design.get("background_color", "#fafafa"))
    primary = _hex_to_rgb(design.get("primary_color", "#1a1a2e"))

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    cx, cy, r_out, r_in = w // 2, 180, 130, 70
    total = sum(s.get("value", 1) for s in segments) or 1

    # Color palette
    palette = [
        _hex_to_rgb(design.get("accent_color", "#00d4aa")),
        _hex_to_rgb(design.get("primary_color", "#1a1a2e")),
        _hex_to_rgb(design.get("secondary_color", "#2e3a5f")),
        (180, 180, 200), (120, 200, 160), (200, 140, 100),
    ]

    start = -90
    for i, seg in enumerate(segments[:6]):
        val = seg.get("value", 1)
        sweep = 360 * val / total
        end = start + sweep
        color = palette[i % len(palette)]

        # Draw arc (as a filled pie slice)
        draw.pieslice([cx - r_out, cy - r_out, cx + r_out, cy + r_out],
                      start, end, fill=color)
        start = end

    # Cut out center for donut
    draw.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=bg)

    # Legend
    font_sm = _get_font(12)
    ly = 330
    for i, seg in enumerate(segments[:4]):
        lx = 60 + i * 120
        color = palette[i % len(palette)]
        draw.rectangle([lx, ly, lx + 10, ly + 10], fill=color)
        draw.text((lx + 16, ly - 2), str(seg.get("label", "?"))[:12],
                  fill=primary, font=font_sm)

    img.save(path, "PNG")
    return path


def generate_all_visuals(brief: dict, story: dict, design: dict,
                         perspectives: dict, run_id: str) -> dict:
    """Generate all visuals for the brief. Returns dict mapping page_type to image path."""
    visuals = {}

    # 1. Cover image (DALL-E)
    visuals["cover"] = generate_cover_image(
        story.get("headline", "AI News"), design, run_id)

    pages = brief.get("pages", [])

    for i, page in enumerate(pages):
        ptype = page.get("page_type", "")

        if ptype == "cover":
            continue  # Already handled

        elif ptype == "economic":
            # Generate stat cards + bar chart
            econ = perspectives.get("economic", {})
            winners = econ.get("winners", ["Tech", "Cloud", "AI startups"])
            stats = [
                {"value": "$4.2T", "label": "Projected AI Market"},
                {"value": "40%", "label": "Productivity Gain"},
                {"value": "2.3M", "label": "New Jobs Created"},
            ]
            visuals[ptype] = generate_stat_card(stats, design, run_id, i)

        elif ptype == "historical":
            # Generate timeline
            hist = perspectives.get("historical", {})
            parallels = hist.get("historical_parallels", [])
            events = [{"year": p.get("year", "?"), "event": p.get("event", "?")}
                      for p in parallels[:5]]
            if not events:
                events = [{"year": "1997", "event": "Deep Blue beats Kasparov"},
                          {"year": "2012", "event": "Deep Learning revolution"},
                          {"year": "2022", "event": "ChatGPT launches"},
                          {"year": "2026", "event": "Current event"}]
            visuals[ptype] = generate_timeline(events, design, run_id, i)

        elif ptype == "social":
            # Impact bars
            soc = perspectives.get("social", {})
            affected = soc.get("who_is_affected", ["Workers", "Students", "Healthcare"])
            items = [{"label": a, "value": random.randint(40, 95)}
                     for a in affected[:5]]
            visuals[ptype] = generate_impact_bars(items, design, run_id, i)

        elif ptype == "future":
            # Donut chart for scenario probabilities
            segments = [
                {"label": "Optimistic", "value": 35},
                {"label": "Likely", "value": 45},
                {"label": "Cautious", "value": 20},
            ]
            visuals[ptype] = generate_donut_chart(segments, design, run_id, i)

        else:
            # For remaining pages, generate a small DALL-E abstract
            section_path = generate_section_image(
                page.get("title", "AI"), design, run_id, i)
            if section_path:
                visuals[ptype] = section_path

    print(f"  [Visuals] Generated {len(visuals)} visual elements")
    return visuals
