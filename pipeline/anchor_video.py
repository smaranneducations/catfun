"""AI News Anchor — Animated image + TTS voiceover + motion graphics.

V3: Generates an animated female news anchor using DALL-E, then combines
with ElevenLabs TTS voice and subtle animation effects to create a
professional news broadcast segment.

No lip-sync — the animation (slow zoom, news graphics, lower thirds)
creates visual interest while the voiceover plays.

Flow:
  1. Generate (or reuse cached) anchor image via DALL-E 3
  2. Generate anchor voiceover via ElevenLabs TTS
  3. Combine image + audio + animation effects via FFmpeg
"""
import os
import time
import json
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from openai import OpenAI
import config


openai_client = OpenAI(api_key=config.OPENAI_API_KEY)


def _get_font(size: int, bold: bool = False):
    """Get a font."""
    names = (["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"] if bold
             else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "FreeSans.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _ffmpeg(args: list, desc: str = "") -> subprocess.CompletedProcess:
    """Run FFmpeg command."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    FFmpeg error ({desc}): {result.stderr[:500]}")
    return result


def _ffprobe_duration(path: str) -> float:
    """Get media duration in seconds."""
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


# ─── Anchor Image Generation ───────────────────────────────────

def generate_anchor_image(output_path: str = None, force_new: bool = False) -> str:
    """Generate an animated female news anchor image using DALL-E 3.

    Caches the image in assets/anchors/ so we don't regenerate every run.
    Use force_new=True to generate a fresh anchor (new look).

    Returns:
        Path to the anchor image (PNG, 1792x1024)
    """
    if not output_path:
        output_path = os.path.join(config.ANCHOR_DIR, "anchor_main.png")

    # Use cached image if available (saves $0.04 per run)
    if os.path.exists(output_path) and not force_new:
        print(f"  [Anchor] Using cached image: {output_path}")
        return output_path

    print(f"  [Anchor] Generating new anchor image via DALL-E 3...")

    try:
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=config.ANCHOR_IMAGE_PROMPT,
            size="1792x1024",  # Widescreen
            quality="hd",
            n=1,
        )

        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        print(f"  [Anchor] DALL-E prompt used: {revised_prompt[:120]}...")

        # Download the image
        img_resp = requests.get(image_url, timeout=60)
        if img_resp.status_code != 200:
            print(f"  [Anchor] Download failed: {img_resp.status_code}")
            return ""

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img_resp.content)

        size_kb = os.path.getsize(output_path) / 1024
        print(f"  [Anchor] Saved: {output_path} ({size_kb:.0f} KB)")
        return output_path

    except Exception as e:
        print(f"  [Anchor] DALL-E error: {e}")
        return ""


def generate_anchor_image_fallback(output_path: str = None) -> str:
    """Fallback: create a simple professional anchor frame (no API needed)."""
    if not output_path:
        output_path = os.path.join(config.ANCHOR_DIR, "anchor_fallback.png")

    if os.path.exists(output_path):
        return output_path

    width, height = 1920, 1080
    bg = Image.new("RGB", (width, height), (10, 15, 30))
    draw = ImageDraw.Draw(bg)

    # Studio gradient
    for y in range(height):
        r = int(10 + 20 * (y / height))
        g = int(15 + 15 * (y / height))
        b = int(30 + 30 * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # "LIVE" badge
    font_badge = _get_font(32, bold=True)
    draw.rectangle([60, 50, 190, 95], fill=(200, 20, 20))
    draw.text((78, 55), "LIVE", fill="white", font=font_badge)

    # Channel title
    font_title = _get_font(52, bold=True)
    draw.text((width // 2 - 220, height // 2 - 50), "FinanceCats News",
              fill=(255, 215, 80), font=font_title)

    # Lower third
    draw.rectangle([0, height - 130, width, height - 65], fill=(20, 25, 50, 200))
    font_lower = _get_font(26)
    draw.text((60, height - 120), "BREAKING: Economic Analysis",
              fill="white", font=font_lower)

    bg.save(output_path, "PNG")
    print(f"  [Anchor] Fallback image created: {output_path}")
    return output_path


# ─── Anchor Voice Generation ───────────────────────────────────

def generate_anchor_voice(script_text: str, output_path: str = None) -> str:
    """Generate anchor voiceover using ElevenLabs TTS.

    Uses a warm, professional female voice (Charlotte).

    Returns:
        Path to the generated MP3 file
    """
    from pipeline.voice_gen import generate_speech, get_audio_duration

    if not output_path:
        output_path = os.path.join(config.TEMP_DIR, "anchor_voice.mp3")

    print(f"  [Anchor Voice] Generating TTS ({len(script_text)} chars)...")
    result = generate_speech(script_text, output_path, voice_id=config.ANCHOR_VOICE_ID)

    if result:
        duration = get_audio_duration(output_path)
        print(f"  [Anchor Voice] Generated: {duration:.1f}s")
        return output_path

    print(f"  [Anchor Voice] TTS failed!")
    return ""


# ─── Compose Anchor Segment ────────────────────────────────────

def add_news_graphics(
    anchor_image: Image.Image,
    headline: str = "",
    story_date: str = "",
    term: str = "",
) -> Image.Image:
    """Add broadcast news graphics overlays to the anchor image.

    Adds:
      - "LIVE" badge (top left)
      - News ticker / lower third with headline
      - Date stamp
      - Channel logo
      - Subtle vignette
    """
    img = anchor_image.copy()
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # ── "LIVE" badge (top left) ──
    font_badge = _get_font(24, bold=True)
    draw.rectangle([40, 35, 140, 70], fill=(200, 20, 20))
    draw.text((55, 38), "LIVE", fill="white", font=font_badge)

    # ── Date stamp (top right) ──
    if story_date:
        font_date = _get_font(20)
        date_text = story_date
        draw.text((width - 250, 42), date_text, fill=(200, 200, 210), font=font_date)

    # ── Lower third (headline bar) ──
    lower_y = height - 120
    # Dark bar background
    draw.rectangle([0, lower_y, width, lower_y + 55], fill=(15, 20, 40))
    # Gold accent line
    draw.rectangle([0, lower_y, width, lower_y + 3], fill=(220, 180, 20))

    if headline:
        font_headline = _get_font(22, bold=True)
        # Truncate headline to fit
        display = headline[:80] + ("..." if len(headline) > 80 else "")
        draw.text((30, lower_y + 12), display, fill="white", font=font_headline)

    # ── Ticker bar (very bottom) ──
    ticker_y = lower_y + 55
    draw.rectangle([0, ticker_y, width, height], fill=(10, 12, 25))
    font_ticker = _get_font(18)
    if term:
        ticker_text = f"  FINANCE EXPLAINED  |  {term.upper()}  |  FinanceCats  |  "
        draw.text((20, ticker_y + 8), ticker_text * 3,
                  fill=(150, 160, 180), font=font_ticker)

    # ── Channel watermark (bottom right) ──
    font_wm = _get_font(16)
    draw.text((width - 150, lower_y - 25), "FinanceCats",
              fill=(100, 100, 120), font=font_wm)

    return img


def compose_anchor_segment(
    anchor_image_path: str,
    anchor_audio_path: str,
    output_path: str,
    headline: str = "",
    story_date: str = "",
    term: str = "",
) -> dict:
    """Compose the full anchor segment: image + voice + animation + graphics.

    Creates a video with:
      - Animated anchor image (slow Ken Burns zoom)
      - News broadcast graphics (LIVE badge, lower third, ticker)
      - ElevenLabs voiceover

    Args:
        anchor_image_path: Path to the DALL-E generated anchor image
        anchor_audio_path: Path to the ElevenLabs anchor voice MP3
        output_path: Where to save the final anchor segment MP4
        headline: News headline for the lower third
        story_date: Date for the on-screen stamp
        term: Financial term for the ticker

    Returns:
        dict with: video_path, duration, status
    """
    if not anchor_image_path or not os.path.exists(anchor_image_path):
        return {"status": "failed", "video_path": "", "error": "No anchor image"}
    if not anchor_audio_path or not os.path.exists(anchor_audio_path):
        return {"status": "failed", "video_path": "", "error": "No anchor audio"}

    print(f"  [Anchor Compose] Building animated anchor segment...")

    width = config.VIDEO_WIDTH
    height = config.VIDEO_HEIGHT

    # Load and resize anchor image
    anchor_img = Image.open(anchor_image_path).convert("RGB")
    anchor_img = anchor_img.resize((width, height), Image.LANCZOS)

    # Add broadcast news graphics
    anchor_with_graphics = add_news_graphics(
        anchor_img,
        headline=headline,
        story_date=story_date,
        term=term,
    )

    # Save the graphics-overlaid frame
    frame_path = output_path.replace(".mp4", "_frame.png")
    anchor_with_graphics.save(frame_path, "PNG")

    # Get audio duration
    audio_dur = _ffprobe_duration(anchor_audio_path)
    if audio_dur <= 0:
        return {"status": "failed", "video_path": "", "error": "Audio has zero duration"}

    # Build the animated video with Ken Burns effect (slow zoom)
    # Using FFmpeg zoompan filter for smooth animation
    total_frames = int(audio_dur * config.FPS) + config.FPS  # +1s buffer

    # zoompan: slow zoom from 100% to ~105% over the duration
    # Scale to 2x output (3840px) — enough headroom for zoom without excessive RAM
    _ffmpeg([
        "-loop", "1",
        "-i", frame_path,
        "-i", anchor_audio_path,
        "-filter_complex",
        (
            f"[0:v]scale=3840:-1,"
            f"zoompan=z='min(zoom+{config.ANCHOR_ZOOM_SPEED},1.06)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={width}x{height}:fps={config.FPS}[v]"
        ),
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-t", str(audio_dur + 0.5),
        output_path,
    ], "anchor segment with animation")

    if os.path.exists(output_path):
        final_dur = _ffprobe_duration(output_path)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  [Anchor Compose] Done: {final_dur:.1f}s, {size_mb:.1f} MB")
        return {
            "status": "completed",
            "video_path": output_path,
            "duration": final_dur,
        }

    return {"status": "failed", "video_path": "", "error": "FFmpeg failed"}
