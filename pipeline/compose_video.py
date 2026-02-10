"""Video composition for FinanceCats V3 — AI Anchor + Cat Conversation.

V3 Layout:
  PART 1: Animated anchor segment plays (DALL-E image + TTS + Ken Burns zoom)
  PART 2: Frame FREEZES on the anchor. Layout becomes:
    - LEFT SIDE: Frozen anchor frame (she's still visible)
    - RIGHT SIDE: Cat overlay (slightly smaller), cats explain the term
    - Text overlays between/below the cats
"""
import os
import json
import subprocess
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from rembg import remove as remove_bg
import config

# Cache for background-removed cat images (avoid reprocessing)
_cat_cutout_cache = {}


# ─── FFmpeg Helpers ─────────────────────────────────────────────

def _ffmpeg(args: list, desc: str = "") -> subprocess.CompletedProcess:
    """Run an FFmpeg command with error handling."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    FFmpeg error ({desc}): {result.stderr[:500]}")
    return result


def _ffprobe_duration(path: str) -> float:
    """Get duration of a media file in seconds."""
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 2.0


def _ffprobe_resolution(path: str) -> tuple[int, int]:
    """Get video width and height."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "stream=width,height",
        "-of", "json", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        for stream in data.get("streams", []):
            w = stream.get("width")
            h = stream.get("height")
            if w and h:
                return int(w), int(h)
    except Exception:
        pass
    return 1920, 1080


# ─── Image Composition ─────────────────────────────────────────

def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font, falling back to default."""
    for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "FreeSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _get_bold_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a bold font."""
    for name in ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return _get_font(size)


def extract_freeze_frame(video_path: str, timestamp: float,
                         output_path: str) -> str:
    """Extract a single frame from the video at the given timestamp."""
    _ffmpeg([
        "-ss", str(max(0, timestamp)),
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ], "extract freeze frame")
    return output_path if os.path.exists(output_path) else ""


def _load_cat_image(cat_path: str, size: tuple[int, int]) -> Image.Image:
    """Load a cat image as a CUTOUT (background removed) using rembg."""
    if not cat_path or not os.path.exists(cat_path):
        img = Image.new("RGBA", size, (60, 60, 80, 255))
        draw = ImageDraw.Draw(img)
        font = _get_font(24)
        draw.text((size[0] // 3, size[1] // 2), "CAT", fill="white", font=font)
        return img

    cache_key = cat_path
    if cache_key in _cat_cutout_cache:
        return _cat_cutout_cache[cache_key].resize(size, Image.LANCZOS)

    try:
        img = Image.open(cat_path).convert("RGBA")
        cutout = remove_bg(img)
        _cat_cutout_cache[cache_key] = cutout
        return cutout.resize(size, Image.LANCZOS)
    except Exception as e:
        print(f"    [Cutout] Background removal failed: {e}, using original")
        img = Image.open(cat_path).convert("RGBA")
        return img.resize(size, Image.LANCZOS)


def _word_wrap(text: str, font, max_width: int) -> list[str]:
    """Wrap text to fit within a pixel width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        try:
            bbox = font.getbbox(test)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(test) * 14
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def create_cat_on_anchor_frame(
    anchor_freeze: Image.Image,
    cat_a_path: str,
    cat_b_path: str,
    active_speaker: str,
    dialogue_line: str = "",
    section_title: str = "",
    key_points: list[str] = None,
    key_takeaway: str = "",
    teaser_line: str = "",
    width: int = 1920,
    height: int = 1080,
) -> Image.Image:
    """Create a frame with the frozen anchor on the LEFT and cats on the RIGHT.

    Layout:
      ┌──────────────────────────────────────────────┐
      │                                              │
      │  [FROZEN ANCHOR FRAME]   [CAT A]   [CAT B]  │
      │  (takes ~55% width)      (smaller, ~40% w)  │
      │                          [text below cats]   │
      │                                              │
      └──────────────────────────────────────────────┘

    The anchor frame fills the left ~55% of the screen.
    The cats are overlaid on the right ~42%, slightly smaller.
    A subtle dark gradient separates the two areas.
    """
    frame = anchor_freeze.copy().resize((width, height), Image.LANCZOS)
    draw = ImageDraw.Draw(frame)

    # ── Dark overlay on right side for cat area (fast approach) ──
    cat_area_x = int(width * 0.55)
    gradient_w = int(width * 0.08)  # Smooth transition zone

    # Build a full-width alpha gradient mask (0=transparent, 255=opaque dark)
    # Left side: 0, transition zone: gradual, right side: 200
    gradient_mask = Image.new("L", (width, height), 0)
    draw_mask = ImageDraw.Draw(gradient_mask)

    # Solid dark on the right
    draw_mask.rectangle([cat_area_x, 0, width, height], fill=200)

    # Gradient in the transition zone
    grad_start = cat_area_x - gradient_w
    for i in range(gradient_w):
        alpha = int(200 * (i / gradient_w))
        x = grad_start + i
        if 0 <= x < width:
            draw_mask.line([(x, 0), (x, height)], fill=alpha)

    # Dark overlay composited via the gradient mask
    dark_overlay = Image.new("RGB", (width, height), (10, 12, 25))
    frame = Image.composite(dark_overlay, frame, gradient_mask.point(lambda p: 255 - p))

    # ── Cat sizing and positions (right side) ──
    cat_area_width = width - cat_area_x
    cat_size = (int(cat_area_width * 0.38), int(height * 0.45))

    cat_a_x = cat_area_x + int(cat_area_width * 0.05)
    cat_b_x = cat_area_x + int(cat_area_width * 0.52)
    cat_y = int(height * 0.08)

    cat_a_img = _load_cat_image(cat_a_path, cat_size)
    cat_b_img = _load_cat_image(cat_b_path, cat_size)

    # Dim inactive speaker
    if active_speaker == "cat_b":
        enhancer = ImageEnhance.Brightness(cat_a_img)
        cat_a_img = enhancer.enhance(0.55)
    elif active_speaker == "cat_a":
        enhancer = ImageEnhance.Brightness(cat_b_img)
        cat_b_img = enhancer.enhance(0.55)

    frame.paste(cat_a_img, (cat_a_x, cat_y), cat_a_img)
    frame.paste(cat_b_img, (cat_b_x, cat_y), cat_b_img)

    # ── Name labels below cats ──
    font_name = _get_font(20)
    label_y = cat_y + cat_size[1] + 5

    a_label = config.CAT_A_NAME
    a_color = (255, 215, 80) if active_speaker in ("cat_a", "both") else (120, 120, 140)
    a_label_w = font_name.getbbox(a_label)[2] if hasattr(font_name, 'getbbox') else len(a_label) * 11
    draw.text((cat_a_x + (cat_size[0] - a_label_w) // 2, label_y), a_label,
              fill=a_color, font=font_name)

    b_label = config.CAT_B_NAME
    b_color = (255, 215, 80) if active_speaker in ("cat_b", "both") else (120, 120, 140)
    b_label_w = font_name.getbbox(b_label)[2] if hasattr(font_name, 'getbbox') else len(b_label) * 11
    draw.text((cat_b_x + (cat_size[0] - b_label_w) // 2, label_y), b_label,
              fill=b_color, font=font_name)

    # ── Text area (below cats, right side) ──
    text_left = cat_area_x + int(cat_area_width * 0.05)
    text_right = width - int(cat_area_width * 0.05)
    text_width = text_right - text_left
    y_cursor = label_y + 35

    # Section title (gold)
    if section_title:
        font_title = _get_bold_font(28)
        draw.text((text_left, y_cursor), section_title,
                  fill=(255, 215, 80), font=font_title)
        y_cursor += 40

    # Dialogue line (white, quoted)
    if dialogue_line:
        font_body = _get_font(22)
        wrapped = _word_wrap(f'"{dialogue_line}"', font_body, text_width)
        for wl in wrapped[:5]:
            draw.text((text_left, y_cursor), wl, fill="white", font=font_body)
            y_cursor += 28

    y_cursor += 10

    # Key points (light blue bullets)
    if key_points:
        font_bullet = _get_font(20)
        for bp in key_points[:4]:
            wrapped = _word_wrap(f"  {bp}", font_bullet, text_width - 20)
            for wl in wrapped:
                draw.text((text_left + 10, y_cursor), wl,
                          fill=(150, 200, 255), font=font_bullet)
                y_cursor += 26

    # Key takeaway (bottom, gold bar)
    if key_takeaway:
        y_cursor = int(height * 0.85)
        font_key = _get_font(24)
        draw.rectangle(
            [text_left - 10, y_cursor - 5, text_right + 10, y_cursor + 35],
            fill=(40, 35, 10),
        )
        draw.text((text_left, y_cursor), key_takeaway,
                  fill=(255, 215, 80), font=font_key)

    # Teaser line
    if teaser_line:
        y_cursor = int(height * 0.92)
        font_tease = _get_font(20)
        draw.text((text_left, y_cursor), teaser_line,
                  fill=(180, 180, 200), font=font_tease)

    # Watermark
    font_wm = _get_font(16)
    draw.text((width - 160, height - 30), "FinanceCats",
              fill=(120, 120, 140), font=font_wm)

    return frame


# ─── Segment Builders ──────────────────────────────────────────

def build_anchor_segment(
    anchor_video_path: str,
    output_path: str,
    width: int,
    height: int,
) -> str:
    """Build the anchor video segment (Part 1 of the video).

    Normalises the pre-composed anchor segment (image + TTS + animation).
    """
    if anchor_video_path and os.path.exists(anchor_video_path):
        # Normalise resolution and codec
        _ffmpeg([
            "-i", anchor_video_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={config.FPS}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-pix_fmt", "yuv420p",
            output_path,
        ], "normalise anchor video")
        return output_path if os.path.exists(output_path) else ""

    return ""


def build_anchor_fallback_segment(
    anchor_audio_path: str,
    output_path: str,
    width: int,
    height: int,
) -> str:
    """Fallback: build anchor segment from TTS audio + static background.

    Used when DALL-E image generation fails.
    """
    if not anchor_audio_path or not os.path.exists(anchor_audio_path):
        return ""

    # Create a professional-looking static frame
    bg = Image.new("RGB", (width, height), (10, 15, 30))
    draw = ImageDraw.Draw(bg)

    # Studio-style gradient
    for y in range(height):
        r = int(10 + 15 * (y / height))
        g = int(15 + 10 * (y / height))
        b = int(30 + 20 * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # "LIVE" badge
    font_badge = _get_bold_font(28)
    draw.rectangle([50, 50, 170, 90], fill=(200, 20, 20))
    draw.text((65, 55), "LIVE", fill="white", font=font_badge)

    # "FinanceCats News" title
    font_title = _get_bold_font(48)
    draw.text((width // 2 - 200, height // 2 - 30), "FinanceCats News",
              fill=(255, 215, 80), font=font_title)

    # Lower third bar
    draw.rectangle([0, height - 120, width, height - 60], fill=(20, 25, 50))
    font_lower = _get_font(24)
    draw.text((50, height - 110), "BREAKING: Economic Analysis",
              fill="white", font=font_lower)

    frame_path = output_path.replace(".mp4", "_frame.png")
    bg.save(frame_path, "PNG")

    audio_dur = _ffprobe_duration(anchor_audio_path)

    _ffmpeg([
        "-loop", "1",
        "-i", frame_path,
        "-i", anchor_audio_path,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-t", str(audio_dur + 0.5),
        "-vf", f"scale={width}:{height}",
        output_path,
    ], "anchor fallback segment")

    return output_path if os.path.exists(output_path) else ""


def build_cat_conversation_segment(
    anchor_video_path: str,
    cat_a_path: str,
    cat_b_path: str,
    exchanges: list[dict],
    output_path: str,
    width: int,
    height: int,
    key_takeaway: str = "",
    teaser_line: str = "",
    music_path: str = None,
) -> str:
    """Build the cat conversation segment (Part 2) over frozen anchor frame.

    Extracts the LAST frame from the anchor video as the freeze frame,
    then overlays the cats on the right side for each dialogue turn.
    """
    seg_dir = os.path.dirname(output_path)
    base_name = os.path.splitext(os.path.basename(output_path))[0]

    # Extract the last frame from anchor video for the freeze
    anchor_dur = _ffprobe_duration(anchor_video_path)
    freeze_ts = max(0, anchor_dur - 0.5)  # Last half-second
    freeze_path = os.path.join(seg_dir, f"anchor_freeze_{base_name}.png")
    extract_freeze_frame(anchor_video_path, freeze_ts, freeze_path)

    if not os.path.exists(freeze_path):
        # Fallback: extract at 50%
        extract_freeze_frame(anchor_video_path, anchor_dur * 0.5, freeze_path)

    # Load the freeze frame
    if os.path.exists(freeze_path):
        anchor_freeze = Image.open(freeze_path).convert("RGB")
    else:
        anchor_freeze = Image.new("RGB", (width, height), (10, 15, 30))

    turn_clips = []

    for ex_idx, exchange in enumerate(exchanges):
        title = exchange.get("exchange_title", f"Part {ex_idx + 1}")
        dialogue = exchange.get("dialogue", [])
        points = exchange.get("key_points", [])

        for i, turn in enumerate(dialogue):
            speaker = turn.get("speaker", "cat_a")
            audio_path = turn.get("audio_path", "")
            line = turn.get("line", "")

            if not audio_path or not os.path.exists(audio_path):
                continue

            # Show takeaway/teaser only on the very last turn of the last exchange
            is_last_exchange = (ex_idx == len(exchanges) - 1)
            is_last_turn = (i == len(dialogue) - 1)

            frame = create_cat_on_anchor_frame(
                anchor_freeze=anchor_freeze,
                cat_a_path=cat_a_path,
                cat_b_path=cat_b_path,
                active_speaker=speaker,
                dialogue_line=line,
                section_title=title if i == 0 else "",
                key_points=points if i == 0 else None,
                key_takeaway=key_takeaway if (is_last_exchange and is_last_turn) else "",
                teaser_line=teaser_line if (is_last_exchange and is_last_turn) else "",
                width=width,
                height=height,
            )

            turn_frame = os.path.join(seg_dir, f"{base_name}_ex{ex_idx:02d}_t{i:02d}.png")
            frame.save(turn_frame, "PNG")

            audio_dur = _ffprobe_duration(audio_path)
            turn_video = os.path.join(seg_dir, f"{base_name}_ex{ex_idx:02d}_t{i:02d}.mp4")

            _ffmpeg([
                "-loop", "1",
                "-i", turn_frame,
                "-i", audio_path,
                "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-t", str(audio_dur + 0.3),
                "-vf", f"scale={width}:{height}",
                turn_video,
            ], f"cat turn ex{ex_idx} t{i}")

            if os.path.exists(turn_video):
                turn_clips.append(turn_video)

    if not turn_clips:
        return ""

    if len(turn_clips) == 1:
        os.replace(turn_clips[0], output_path)
        return output_path if os.path.exists(output_path) else ""

    # Concatenate all turn clips
    concat_file = os.path.join(seg_dir, f"{base_name}_cat_turns.txt")
    with open(concat_file, "w") as f:
        for clip in turn_clips:
            safe = clip.replace("\\", "/")
            f.write(f"file '{safe}'\n")

    _ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        "-pix_fmt", "yuv420p",
        output_path,
    ], "concat cat conversation")

    return output_path if os.path.exists(output_path) else ""


# ─── Main Composition ──────────────────────────────────────────

def compose_video(
    anchor_video_path: str,
    anchor_audio_path: str,
    cat_script: dict,
    cat_a_path: str,
    cat_b_path: str,
    metadata: dict,
    music_path: str = None,
) -> str:
    """Compose the final FinanceCats V3 video.

    Two-part structure:
      Part 1: AI anchor video (or TTS fallback) — 60-90 seconds
      Part 2: Frozen anchor + cat overlay — 120-180 seconds

    Args:
        anchor_video_path: Path to anchor segment video (DALL-E + TTS + animation)
        anchor_audio_path: Path to TTS fallback audio (used if no video)
        cat_script: The cat conversation script with exchanges + audio paths
        cat_a_path: Path to Cat A (Professor) image
        cat_b_path: Path to Cat B (Cleo) image
        metadata: Video metadata (title, term, story_date, etc.)
        music_path: Optional background music

    Returns:
        Path to the final output video
    """
    print("\n=== COMPOSING FINAL VIDEO (V3: Anchor + Cats) ===")

    width = config.VIDEO_WIDTH
    height = config.VIDEO_HEIGHT

    if not music_path:
        music_path = _find_music_track()

    work_dir = os.path.join(config.TEMP_DIR, "compose")
    os.makedirs(work_dir, exist_ok=True)

    all_clips = []

    # ── Part 1: Anchor Video ──
    print("  [Part 1] Building anchor segment...")
    anchor_clip = os.path.join(work_dir, "part1_anchor.mp4")

    has_anchor_video = anchor_video_path and os.path.exists(anchor_video_path)

    if has_anchor_video:
        result = build_anchor_segment(anchor_video_path, anchor_clip, width, height)
    else:
        result = build_anchor_fallback_segment(
            anchor_audio_path, anchor_clip, width, height,
        )

    if result:
        anchor_dur = _ffprobe_duration(result)
        print(f"  [Part 1] Anchor segment: {anchor_dur:.1f}s")
        all_clips.append(result)
    else:
        print("  [Part 1] ERROR: Could not create anchor segment!")
        return ""

    # The source for freeze frame: use the anchor segment video
    freeze_source = anchor_video_path if has_anchor_video else anchor_clip

    # ── Part 2: Cat Conversation over frozen anchor ──
    print("  [Part 2] Building cat conversation over frozen anchor...")
    cat_clip = os.path.join(work_dir, "part2_cats.mp4")

    exchanges = cat_script.get("exchanges", [])
    key_takeaway = cat_script.get("key_takeaway", "")
    teaser_line = cat_script.get("teaser_line", "")

    result = build_cat_conversation_segment(
        anchor_video_path=freeze_source,
        cat_a_path=cat_a_path,
        cat_b_path=cat_b_path,
        exchanges=exchanges,
        output_path=cat_clip,
        width=width,
        height=height,
        key_takeaway=key_takeaway,
        teaser_line=teaser_line,
        music_path=music_path,
    )

    if result:
        cat_dur = _ffprobe_duration(result)
        print(f"  [Part 2] Cat conversation: {cat_dur:.1f}s")
        all_clips.append(result)
    else:
        print("  [Part 2] ERROR: Could not create cat conversation segment!")
        return ""

    # ── Normalise and concatenate ──
    print(f"\n  Normalising {len(all_clips)} parts...")

    normalised = []
    for idx, clip in enumerate(all_clips):
        norm_path = os.path.join(work_dir, f"norm_{idx:03d}.mp4")
        _ffmpeg([
            "-i", clip,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={config.FPS}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-pix_fmt", "yuv420p",
            norm_path,
        ], f"normalise part {idx}")
        if os.path.exists(norm_path):
            normalised.append(norm_path)
        else:
            normalised.append(clip)

    concat_file = os.path.join(work_dir, "concat_final.txt")
    with open(concat_file, "w") as f:
        for clip in normalised:
            safe_path = clip.replace("\\", "/")
            f.write(f"file '{safe_path}'\n")

    term = metadata.get("term", "finance")
    safe_term = "".join(c for c in term[:40] if c.isalnum() or c in " -_").strip()
    safe_term = safe_term.replace(" ", "_")
    output_filename = f"FinanceCats_{safe_term}.mp4"
    output_path = os.path.join(config.OUTPUT_DIR, output_filename)

    print(f"  Assembling final video...")
    _ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ], "final assembly")

    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        duration = _ffprobe_duration(output_path)

        anchor_secs = anchor_dur
        cat_secs = cat_dur

        print(f"\n  DONE! {output_path}")
        print(f"  Size: {size_mb:.1f} MB | Duration: {duration:.1f}s ({duration/60:.1f} min)")
        print(f"  Anchor segment: ~{anchor_secs:.0f}s")
        print(f"  Cat conversation: ~{cat_secs:.0f}s")
        print(f"  100% original content (no third-party clips)")

        return output_path
    else:
        print("  ERROR: Final video not created!")
        return ""


def _find_music_track() -> str:
    """Find a background music track from the music directory."""
    if not os.path.exists(config.MUSIC_DIR):
        return ""
    tracks = [
        f for f in os.listdir(config.MUSIC_DIR)
        if f.lower().endswith(('.mp3', '.wav', '.m4a', '.ogg'))
    ]
    if not tracks:
        print("  [Music] No background tracks found in assets/music/")
        return ""
    chosen = random.choice(tracks)
    print(f"  [Music] Using background track: {chosen}")
    return os.path.join(config.MUSIC_DIR, chosen)
