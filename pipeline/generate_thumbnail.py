"""Thumbnail generator for FinanceCats V3.

Creates a 1280x720 YouTube thumbnail with:
  - Frozen anchor frame as background (from anchor segment)
  - Both cats as cutouts overlaid on the right side
  - Large bold term text
  - "BREAKING" / news-style badge
  - Channel branding
"""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import config

try:
    from rembg import remove as remove_bg
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

THUMB_W = 1280
THUMB_H = 720


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font, preferring bold for thumbnails."""
    names = ["arialbd.ttf", "Arial Bold.ttf", "arial.ttf", "Arial.ttf",
             "DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "FreeSans.ttf"]
    if not bold:
        names = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "FreeSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _load_cat_cutout(cat_path: str, size: tuple[int, int]) -> Image.Image:
    """Load a cat image as a cutout (background removed)."""
    if not cat_path or not os.path.exists(cat_path):
        return Image.new("RGBA", size, (0, 0, 0, 0))

    img = Image.open(cat_path).convert("RGBA")
    if HAS_REMBG:
        try:
            img = remove_bg(img)
        except Exception:
            pass
    return img.resize(size, Image.LANCZOS)


def generate_thumbnail(
    anchor_video_path: str,
    cat_a_path: str,
    cat_b_path: str,
    term: str,
    thumbnail_text: str = "",
    output_path: str = None,
    freeze_timestamp: float = None,
) -> str:
    """Generate a YouTube thumbnail image (V3).

    Args:
        anchor_video_path: Path to anchor video (to extract background frame)
        cat_a_path: Path to Cat A (Professor) image
        cat_b_path: Path to Cat B (Cleo) image
        term: The financial term
        thumbnail_text: Short text for overlay (max 5 words)
        output_path: Where to save the thumbnail
        freeze_timestamp: Which frame to grab (default: near end of video)

    Returns:
        Path to the generated thumbnail PNG
    """
    if not output_path:
        safe_term = "".join(c for c in term[:30] if c.isalnum() or c in " -_").strip()
        safe_term = safe_term.replace(" ", "_")
        output_path = os.path.join(config.OUTPUT_DIR, f"thumb_{safe_term}.png")

    # ── Background: frame from anchor video ──
    frame_path = os.path.join(config.TEMP_DIR, "thumb_frame.png")

    if freeze_timestamp is None:
        # Use a frame near the end of the anchor video
        try:
            from pipeline.compose_video import _ffprobe_duration
            dur = _ffprobe_duration(anchor_video_path)
            freeze_timestamp = max(0, dur * 0.7)  # 70% through
        except Exception:
            freeze_timestamp = 10.0

    _extract_frame(anchor_video_path, freeze_timestamp, frame_path)

    if os.path.exists(frame_path):
        bg = Image.open(frame_path).convert("RGB").resize((THUMB_W, THUMB_H), Image.LANCZOS)
    else:
        # Fallback: dark professional background
        bg = Image.new("RGB", (THUMB_W, THUMB_H), (10, 15, 30))

    # Slight darken for text readability
    dark = Image.new("RGB", (THUMB_W, THUMB_H), (0, 0, 0))
    bg = Image.blend(bg, dark, 0.25)

    # Boost saturation
    enhancer = ImageEnhance.Color(bg)
    bg = enhancer.enhance(1.3)

    draw = ImageDraw.Draw(bg)

    # ── Dark overlay on right side for cats ──
    cat_area_x = int(THUMB_W * 0.58)
    overlay = Image.new("RGBA", (THUMB_W - cat_area_x, THUMB_H), (10, 12, 25, 180))
    right_section = bg.crop((cat_area_x, 0, THUMB_W, THUMB_H)).convert("RGBA")
    composited = Image.alpha_composite(right_section, overlay).convert("RGB")
    bg.paste(composited, (cat_area_x, 0))
    draw = ImageDraw.Draw(bg)

    # ── Cats on right side ──
    cat_size = (int(THUMB_W * 0.18), int(THUMB_H * 0.55))

    cat_a = _load_cat_cutout(cat_a_path, cat_size)
    cat_b = _load_cat_cutout(cat_b_path, cat_size)

    cat_a_x = cat_area_x + int((THUMB_W - cat_area_x) * 0.05)
    cat_b_x = THUMB_W - cat_size[0] - int((THUMB_W - cat_area_x) * 0.05)
    cat_y = THUMB_H - cat_size[1] - 60

    bg.paste(cat_a, (cat_a_x, cat_y), cat_a)
    bg.paste(cat_b, (cat_b_x, cat_y), cat_b)

    # ── "BREAKING" badge (top left) ──
    font_badge = _get_font(26, bold=True)
    draw.rectangle([30, 30, 200, 70], fill=(200, 20, 20))
    draw.text((50, 35), "BREAKING", fill="white", font=font_badge)

    # ── Main text (left side, over anchor) ──
    display_text = thumbnail_text or term
    words = display_text.upper().split()
    if len(words) > 3:
        mid = len(words) // 2
        lines = [" ".join(words[:mid]), " ".join(words[mid:])]
    else:
        lines = [display_text.upper()]

    font_big = _get_font(64, bold=True)
    y_text = int(THUMB_H * 0.12)

    for line in lines:
        bbox = font_big.getbbox(line) if hasattr(font_big, 'getbbox') else (0, 0, len(line) * 35, 65)
        text_w = bbox[2] - bbox[0]
        text_x = int(cat_area_x * 0.5) - text_w // 2  # Centre in left half

        # Black outline
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                draw.text((text_x + dx, y_text + dy), line, fill="black", font=font_big)
        draw.text((text_x, y_text), line, fill="white", font=font_big)
        y_text += 80

    # ── Subtitle: "What is [term]?" ──
    font_sub = _get_font(36, bold=True)
    subtitle = f"What is {term}?"
    bbox = font_sub.getbbox(subtitle) if hasattr(font_sub, 'getbbox') else (0, 0, len(subtitle) * 20, 40)
    sub_w = bbox[2] - bbox[0]
    sub_x = int(cat_area_x * 0.5) - sub_w // 2
    sub_y = y_text + 10

    # Gold background bar
    bar_pad = 12
    draw.rectangle(
        [sub_x - bar_pad, sub_y - 5, sub_x + sub_w + bar_pad, sub_y + 45],
        fill=(220, 180, 20),
    )
    draw.text((sub_x, sub_y), subtitle, fill="black", font=font_sub)

    # ── "FinanceCats" branding (bottom) ──
    font_brand = _get_font(22, bold=True)
    brand = "FinanceCats"
    bbox = font_brand.getbbox(brand) if hasattr(font_brand, 'getbbox') else (0, 0, 130, 26)
    brand_w = bbox[2] - bbox[0]
    draw.text(((cat_area_x - brand_w) // 2, THUMB_H - 40), brand,
              fill=(255, 255, 255), font=font_brand)

    # Save
    bg.save(output_path, "PNG", quality=95)
    print(f"  [Thumbnail] Saved: {output_path}")
    size_kb = os.path.getsize(output_path) / 1024
    print(f"  [Thumbnail] Size: {size_kb:.0f} KB ({THUMB_W}x{THUMB_H})")

    return output_path


def _extract_frame(video_path: str, timestamp: float, output_path: str):
    """Extract a single frame from a video using FFmpeg."""
    if not video_path or not os.path.exists(video_path):
        return
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-ss", str(max(0, timestamp)),
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True)
