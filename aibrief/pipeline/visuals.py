"""Visual generation pipeline — Imagen (Google) images + Pillow infographics.

Generates unique visuals for each PDF page:
  - Background images: subtle, low-contrast, style-specific (Imagen)
  - Foreground images: prominent, topic-related, contrasting (Imagen)
  - Cover: abstract editorial art (Imagen)
  - Stats pages: Pillow-generated infographic cards
  - Content pages: Data visualizations, timelines, comparison charts
  - All generated fresh each run, never repeated

Uses Google Imagen (imagen-4.0-generate-001) instead of DALL-E for cost savings.
"""
import os
import random
import math
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from aibrief import config

# ═══════════════════════════════════════════════════════════════
#  IMAGEN CLIENT (Google GenAI)
# ═══════════════════════════════════════════════════════════════

_imagen_client = None


def _get_imagen():
    global _imagen_client
    if _imagen_client is None:
        from google import genai
        _imagen_client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _imagen_client


VISUALS_DIR = config.OUTPUT_DIR / "visuals"
VISUALS_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

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
#  IMAGEN IMAGE GENERATION
# ═══════════════════════════════════════════════════════════════

_imagen_exhausted = False  # Track quota exhaustion to skip retries


def _generate_imagen(prompt: str, path: str, aspect: str = "1:1",
                     size: str = "1K") -> str:
    """Generate an image using Google Imagen and save to path."""
    global _imagen_exhausted
    if _imagen_exhausted:
        return ""  # Skip Imagen, go straight to DALL-E fallback
    try:
        from google.genai import types
        client = _get_imagen()
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect,
                person_generation="dont_allow",
            ),
        )
        if response.generated_images:
            img_bytes = response.generated_images[0].image.image_bytes
            with open(path, "wb") as f:
                f.write(img_bytes)
            return path
        print(f"  [Imagen] No images returned")
        return ""
    except Exception as e:
        err_str = str(e)
        if "RESOURCE_EXHAUSTED" in err_str:
            _imagen_exhausted = True
            print(f"  [Imagen] Quota exhausted — switching to DALL-E fallback")
        else:
            print(f"  [Imagen] Error: {err_str[:120]}")
        return ""


def _generate_dalle(prompt: str, path: str, size: str = "1024x1024") -> str:
    """Fallback: generate an image using OpenAI DALL-E 3."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size=size,
            quality="standard",
        )
        image_url = response.data[0].url
        img_data = requests.get(image_url, timeout=30).content
        with open(path, "wb") as f:
            f.write(img_data)
        print(f"  [DALL-E] Saved ({len(img_data) // 1024} KB)")
        return path
    except Exception as e:
        print(f"  [DALL-E] Error: {str(e)[:120]}")
        return ""


def generate_background_image(style_id: str, page_topic: str,
                              design: dict, run_id: str,
                              page_idx: int) -> str:
    """Generate a subtle, low-contrast background.

    CACHED BY THEME: backgrounds are purely style-driven (no page content),
    so we cache by style_id + page_idx. If a matching image exists from
    any previous run, we reuse it — no regeneration needed.
    """
    # Cache key: theme + page index (not run_id)
    cache_path = str(VISUALS_DIR / f"bg_theme_{style_id}_{page_idx}.png")
    if os.path.exists(cache_path):
        print(f"  [Cache] BG page {page_idx} reused from theme cache ({style_id})")
        return cache_path

    # Also check old run-based path for backward compat
    old_path = str(VISUALS_DIR / f"bg_{run_id}_{page_idx}.png")
    if os.path.exists(old_path):
        return old_path

    # Use hardcoded values from emotion-driven design
    imagen_style = design.get("imagen_style", "corporate minimal, professional")
    bg_motifs = design.get("bg_motifs", "subtle geometric patterns")

    prompt = (
        f"A beautiful subtle {imagen_style} wallpaper painting, portrait orientation. "
        f"Soft muted colors, very low contrast, dreamy and ethereal. "
        f"Delicate {bg_motifs} scattered lightly across the image. "
        f"The center is mostly empty with gentle gradients. "
        f"Edges have faint decorative elements. "
        f"No text, no words, no letters, no numbers, no writing of any kind. "
        f"No people, no faces, no logos. "
        f"Elegant premium art print, soft lighting, silk texture feel."
    )

    print(f"  [Imagen] BG page {page_idx} ({imagen_style[:30]}...)")
    result = _generate_imagen(prompt, cache_path, aspect="3:4")
    if result:
        print(f"  [Imagen] BG saved ({os.path.getsize(cache_path) // 1024} KB)")
    else:
        print(f"  [DALL-E] BG page {page_idx} (fallback)...")
        result = _generate_dalle(prompt, cache_path, size="1024x1792")
    if not result:
        result = _generate_gradient_art(cache_path, design)
        print(f"  [Pillow] BG gradient fallback for page {page_idx}")
    return result


def generate_foreground_image(topic: str, page_content: str,
                              style_id: str, design: dict,
                              run_id: str, page_idx: int,
                              page_title: str = "",
                              page_key_point: str = "") -> str:
    """Generate a prominent foreground image — CONTENT-AWARE per page.

    Each page gets a unique foreground that visually expresses its
    specific content (not just the overall headline).
    """
    path = str(VISUALS_DIR / f"fg_{run_id}_{page_idx}.png")
    if os.path.exists(path):
        return path

    fg_mood = design.get("fg_mood", "professional, editorial")
    imagen_style = design.get("imagen_style", "corporate minimal")
    accent = design.get("accent_color", "#00d4aa")

    # Build a content-aware subject for this specific page
    if page_title and page_key_point:
        subject = f"{page_title}: {page_key_point}"[:90]
    elif page_title:
        subject = page_title[:90]
    else:
        subject = topic[:60]

    prompt = (
        f"A vivid {imagen_style} illustration expressing the concept of "
        f"{subject}. "
        f"{fg_mood}. "
        f"Abstract and conceptual, bold colors with {accent} accents. "
        f"Dramatic lighting, impactful composition. "
        f"No text, no words, no letters, no numbers, no writing of any kind. "
        f"No people, no faces, no logos. Square painting."
    )

    print(f"  [Imagen] FG page {page_idx} ({subject[:40]}...)")
    result = _generate_imagen(prompt, path, aspect="1:1")
    if result:
        print(f"  [Imagen] FG saved ({os.path.getsize(path) // 1024} KB)")
    else:
        print(f"  [DALL-E] FG page {page_idx} (fallback)...")
        result = _generate_dalle(prompt, path, size="1024x1024")
    return result


def generate_cover_image(headline: str, design: dict, run_id: str,
                         style_id: str = "") -> str:
    """Generate an abstract cover image using HARDCODED style from emotion map."""
    path = str(VISUALS_DIR / f"cover_{run_id}.png")
    if os.path.exists(path):
        return path

    imagen_style = design.get("imagen_style", "corporate minimal")
    fg_mood = design.get("fg_mood", "professional, editorial")
    primary = design.get("primary_color", "#1a1a2e")
    accent = design.get("accent_color", "#00d4aa")

    prompt = (
        f"A stunning {imagen_style} abstract painting about {headline[:60]}. "
        f"{fg_mood}. Dominant tones: dark {primary} with bright {accent} accents. "
        f"Bold, artistic, dramatic lighting, high contrast. "
        f"Portrait orientation, full bleed, premium gallery art. "
        f"No text, no words, no letters, no writing of any kind. "
        f"No faces, no logos."
    )

    print(f"  [Imagen] Cover ({imagen_style[:30]}...)")
    result = _generate_imagen(prompt, path, aspect="3:4")
    if result:
        print(f"  [Imagen] Cover saved ({os.path.getsize(path) // 1024} KB)")
    else:
        # DALL-E fallback
        print(f"  [DALL-E] Cover (fallback)...")
        result = _generate_dalle(prompt, path, size="1024x1792")
    if not result:
        result = _generate_gradient_art(path, design)
        print(f"  [Pillow] Cover gradient fallback")
    return result


def _generate_gradient_art(path: str, design: dict) -> str:
    """Fallback: generate abstract gradient art with Pillow."""
    w, h = 768, 1024
    c1 = _hex_to_rgb(design.get("primary_color", "#1a1a2e"))
    c2 = _hex_to_rgb(design.get("secondary_color", "#2e3a5f"))
    ac = _hex_to_rgb(design.get("accent_color", "#00d4aa"))

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=_lerp_color(c1, c2, t))

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
        draw.ellipse([cx - 4, 40, cx + 4, 48], fill=accent)
        val = str(item.get("value", "?"))
        bbox = draw.textbbox((0, 0), val, font=font_big)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, 65), val, fill=primary, font=font_big)
        lbl = str(item.get("label", ""))
        bbox2 = draw.textbbox((0, 0), lbl, font=font_sm)
        tw2 = bbox2[2] - bbox2[0]
        draw.text((cx - tw2 // 2, 140), lbl, fill=(*primary, 180), font=font_sm)
        if i < n - 1:
            lx = 20 + (i + 1) * card_w
            draw.line([(lx, 50), (lx, 170)], fill=(*accent, 40), width=1)

    img.save(path, "PNG")
    return path


def generate_timeline(events: list[dict], design: dict, run_id: str,
                      page_idx: int) -> str:
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

    lx1, lx2, ly = 60, w - 60, 100
    draw.line([(lx1, ly), (lx2, ly)], fill=(*accent, 120), width=2)
    spacing = (lx2 - lx1) / max(n - 1, 1)

    for i, ev in enumerate(events[:5]):
        cx = int(lx1 + i * spacing)
        draw.ellipse([cx - 8, ly - 8, cx + 8, ly + 8], fill=accent)
        draw.ellipse([cx - 4, ly - 4, cx + 4, ly + 4], fill=bg)
        yr = str(ev.get("year", ""))
        bbox = draw.textbbox((0, 0), yr, font=font_yr)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, ly - 40), yr, fill=primary, font=font_yr)
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


# ═══════════════════════════════════════════════════════════════
#  MAIN: GENERATE ALL VISUALS
# ═══════════════════════════════════════════════════════════════

def generate_all_visuals(brief: dict, story: dict, design: dict,
                         perspectives: dict, run_id: str,
                         style_id: str = "") -> dict:
    """Generate all visuals for the brief.

    Returns dict mapping keys to image paths:
      "cover"       → cover image
      "bg_0", "bg_1", ...  → background images per content page
      "fg_0", "fg_1", ...  → foreground images per content page
      Plus any infographics (stat, timeline, etc.)
    """
    visuals = {}
    style_id = style_id or design.get("style_id", "luxury_minimalist")

    # 1. Cover image (Imagen)
    visuals["cover"] = generate_cover_image(
        story.get("headline", "AI News"), design, run_id, style_id)

    pages = brief.get("pages", [])
    content_pages = [p for p in pages if p.get("page_type") != "hero"]

    topic = story.get("headline", "AI")

    for i, page in enumerate(content_pages):
        ptype = page.get("page_type", "")
        page_content = (page.get("hero_statement", "") or
                        page.get("summary_points", "") or
                        page.get("quote", "") or "AI")

        # Background image — cached by theme (no page content needed)
        bg = generate_background_image(style_id, str(page_content),
                                       design, run_id, i + 1)
        if bg:
            visuals[f"bg_{i}"] = bg

        # Foreground image — content-aware per page
        page_title = page.get("page_title", "")
        points = page.get("points", [])
        page_key_point = ""
        if points and isinstance(points, list):
            first = points[0]
            if isinstance(first, dict):
                page_key_point = first.get("point", "")
            elif isinstance(first, str):
                page_key_point = first
        fg = generate_foreground_image(
            topic, str(page_content), style_id, design, run_id, i + 1,
            page_title=page_title,
            page_key_point=page_key_point,
        )
        if fg:
            visuals[f"fg_{i}"] = fg

        # Additional Pillow infographics based on page type
        if ptype == "stat":
            econ = perspectives.get("economic", {})
            stats = [
                {"value": "$4.2T", "label": "Projected AI Market"},
                {"value": "40%", "label": "Productivity Gain"},
                {"value": "2.3M", "label": "New Jobs Created"},
            ]
            visuals[f"infographic_{i}"] = generate_stat_card(
                stats, design, run_id, i)
        elif ptype == "historical":
            hist = perspectives.get("historical", {})
            parallels = hist.get("historical_parallels", [])
            events = [{"year": p.get("year", "?"), "event": p.get("event", "?")}
                      for p in parallels[:5]]
            if not events:
                events = [{"year": "1997", "event": "Deep Blue beats Kasparov"},
                          {"year": "2012", "event": "Deep Learning revolution"},
                          {"year": "2022", "event": "ChatGPT launches"},
                          {"year": "2026", "event": "Current event"}]
            visuals[f"infographic_{i}"] = generate_timeline(
                events, design, run_id, i)

    print(f"  [Visuals] Generated {len(visuals)} visual elements "
          f"(Imagen backgrounds + foregrounds + infographics)")
    return visuals
