"""Video composition for FinanceCats — assembles the final education video.

Takes the script (with audio paths), source news clip, cat image, and overlay
design, and produces the final 4-6.5 minute video using FFmpeg.

Segment types:
  1. news_clip      — straight segment from source video
  2. cat_intro      — blurred BG + cat image + narration + text
  3. news_context   — straight segment from source video
  4. lecture         — blurred BG + cat image + narration + text overlays
  5. news_clip_final— straight segment from source video
  6. cat_wrapup     — blurred BG + cat image + narration + text
"""
import os
import json
import subprocess
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import config


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


def extract_freeze_frame(video_path: str, timestamp: float,
                         output_path: str) -> str:
    """Extract a single frame from the video."""
    _ffmpeg([
        "-ss", str(max(0, timestamp)),
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ], "extract freeze frame")
    return output_path if os.path.exists(output_path) else ""


def create_blurred_background(frame_path: str, width: int, height: int,
                              blur_radius: int = 25) -> Image.Image:
    """Create a blurred + darkened background from a video frame."""
    if frame_path and os.path.exists(frame_path):
        bg = Image.open(frame_path).convert("RGB")
        bg = bg.resize((width, height), Image.LANCZOS)
    else:
        bg = Image.new("RGB", (width, height), (20, 25, 40))

    # Apply gaussian blur
    bg = bg.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Darken with semi-transparent overlay
    dark = Image.new("RGB", (width, height), (0, 0, 0))
    bg = Image.blend(bg, dark, 0.4)

    return bg


def create_cat_overlay_frame(
    bg_image: Image.Image,
    cat_path: str,
    narration_text: str,
    bullet_points: list[str] = None,
    section_title: str = "",
    key_takeaway: str = "",
    teaser_line: str = "",
    width: int = 1920,
    height: int = 1080,
) -> Image.Image:
    """Create a single frame with blurred BG, cat image, and text overlays.

    Layout:
      - Cat on the RIGHT side (~30% width)
      - Text on the LEFT side (~60% width)
      - Section title at top if provided
      - Bullet points below narration text
    """
    frame = bg_image.copy()
    draw = ImageDraw.Draw(frame)

    # ── Load and place cat ──
    cat_size = (int(width * 0.28), int(height * 0.65))
    cat_x = int(width * 0.68)
    cat_y = int(height * 0.20)

    if cat_path and os.path.exists(cat_path):
        cat_img = Image.open(cat_path).convert("RGBA")
        cat_img = cat_img.resize(cat_size, Image.LANCZOS)
        # Paste with alpha
        frame.paste(cat_img, (cat_x, cat_y), cat_img)
    else:
        # Placeholder rectangle
        draw.rectangle(
            [cat_x, cat_y, cat_x + cat_size[0], cat_y + cat_size[1]],
            fill=(60, 60, 80), outline=(100, 100, 120), width=3,
        )
        font_ph = _get_font(24)
        draw.text((cat_x + 50, cat_y + cat_size[1] // 2), "CAT",
                  fill="white", font=font_ph)

    # ── Text area (left 60%) ──
    text_left = int(width * 0.05)
    text_right = int(width * 0.62)
    text_width = text_right - text_left
    y_cursor = int(height * 0.12)

    # Semi-transparent text backdrop
    backdrop = Image.new("RGBA", (text_width + 40, int(height * 0.76)), (0, 0, 0, 140))
    frame.paste(
        Image.new("RGB", backdrop.size, (0, 0, 0)),
        (text_left - 20, y_cursor - 20),
        backdrop,
    )

    # Section title (gold)
    if section_title:
        font_title = _get_font(38)
        draw.text((text_left, y_cursor), section_title,
                  fill=(255, 215, 80), font=font_title)
        y_cursor += 55

    # Narration text (white, word-wrapped)
    font_body = _get_font(28)
    wrapped = _word_wrap(narration_text, font_body, text_width)
    for line in wrapped[:12]:  # Max 12 lines
        draw.text((text_left, y_cursor), line, fill="white", font=font_body)
        y_cursor += 38

    y_cursor += 20

    # Bullet points (light blue)
    if bullet_points:
        font_bullet = _get_font(26)
        for bp in bullet_points[:5]:
            draw.text((text_left + 10, y_cursor), f"  {bp}",
                      fill=(150, 200, 255), font=font_bullet)
            y_cursor += 36

    # Key takeaway (bottom, gold box)
    if key_takeaway:
        y_cursor = int(height * 0.82)
        font_key = _get_font(30)
        # Gold background bar
        draw.rectangle(
            [text_left - 10, y_cursor - 8, text_right + 10, y_cursor + 45],
            fill=(40, 35, 10),
        )
        draw.text((text_left, y_cursor), key_takeaway,
                  fill=(255, 215, 80), font=font_key)

    # Teaser line (very bottom)
    if teaser_line:
        y_cursor = int(height * 0.90)
        font_tease = _get_font(24)
        draw.text((text_left, y_cursor), teaser_line,
                  fill=(180, 180, 200), font=font_tease)

    # Channel watermark (bottom right)
    font_wm = _get_font(18)
    draw.text((width - 200, height - 35), "FinanceCats",
              fill=(120, 120, 140), font=font_wm)

    return frame


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


# ─── Segment Builders ──────────────────────────────────────────

def build_news_clip_segment(video_path: str, start: float, end: float,
                            output_path: str, width: int, height: int) -> str:
    """Extract a segment from the source news clip."""
    duration = end - start
    if duration <= 0:
        return ""

    _ffmpeg([
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        "-pix_fmt", "yuv420p",
        output_path,
    ], "news clip segment")

    return output_path if os.path.exists(output_path) else ""


def build_cat_segment(
    video_path: str,
    freeze_timestamp: float,
    cat_path: str,
    audio_path: str,
    narration_text: str,
    output_path: str,
    width: int,
    height: int,
    bullet_points: list[str] = None,
    section_title: str = "",
    key_takeaway: str = "",
    teaser_line: str = "",
    music_path: str = None,
) -> str:
    """Build a cat-narrated segment (intro, lecture section, or wrapup).

    1. Create blurred BG from freeze frame
    2. Overlay cat + text
    3. Combine with TTS audio (+ optional background music)
    """
    seg_dir = os.path.dirname(output_path)

    # Extract freeze frame for background
    frame_path = os.path.join(seg_dir, f"freeze_{os.path.basename(output_path)}.png")
    extract_freeze_frame(video_path, freeze_timestamp, frame_path)

    # Create blurred background
    bg = create_blurred_background(frame_path, width, height)

    # Create the composed frame
    composed = create_cat_overlay_frame(
        bg_image=bg,
        cat_path=cat_path,
        narration_text=narration_text,
        bullet_points=bullet_points,
        section_title=section_title,
        key_takeaway=key_takeaway,
        teaser_line=teaser_line,
        width=width,
        height=height,
    )

    # Save composed frame
    frame_file = os.path.join(seg_dir, f"frame_{os.path.basename(output_path)}.png")
    composed.save(frame_file, "PNG")

    # Determine duration from audio
    if audio_path and os.path.exists(audio_path):
        audio_dur = _ffprobe_duration(audio_path)

        if music_path and os.path.exists(music_path):
            # Mix voice + background music
            mixed_audio = os.path.join(seg_dir, f"mixed_{os.path.basename(output_path)}.mp3")
            _ffmpeg([
                "-i", audio_path,
                "-i", music_path,
                "-filter_complex",
                f"[1:a]volume={config.MUSIC_VOLUME}[music];"
                f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[out]",
                "-map", "[out]",
                "-t", str(audio_dur + 0.5),
                mixed_audio,
            ], "mix voice + music")
            final_audio = mixed_audio if os.path.exists(mixed_audio) else audio_path
        else:
            final_audio = audio_path

        # Create video from still frame + audio
        _ffmpeg([
            "-loop", "1",
            "-i", frame_file,
            "-i", final_audio,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-t", str(audio_dur + 0.5),
            "-vf", f"scale={width}:{height}",
            output_path,
        ], "cat segment with audio")
    else:
        # No audio — use estimated 5 seconds
        _ffmpeg([
            "-loop", "1",
            "-i", frame_file,
            "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-t", "5",
            "-an",
            "-vf", f"scale={width}:{height}",
            output_path,
        ], "cat segment (no audio)")

    return output_path if os.path.exists(output_path) else ""


# ─── Main Composition ──────────────────────────────────────────

def compose_video(
    video_path: str,
    script: dict,
    cat_path: str,
    metadata: dict,
    music_path: str = None,
) -> str:
    """Compose the final FinanceCats education video.

    Args:
        video_path: Path to the downloaded news clip
        script: The script dict with segments and audio paths
        cat_path: Path to the selected cat image
        metadata: Video metadata (title, channel, etc.)
        music_path: Optional path to background music track

    Returns:
        Path to the final output video
    """
    print("\n=== COMPOSING FINAL VIDEO ===")

    # Get source video resolution
    src_w, src_h = _ffprobe_resolution(video_path)
    # Standardise to 1080p
    width = config.VIDEO_WIDTH
    height = config.VIDEO_HEIGHT
    print(f"  Source: {src_w}x{src_h} -> Output: {width}x{height}")

    # Find a background music track if not provided
    if not music_path:
        music_path = _find_music_track()

    # Working directory
    work_dir = os.path.join(config.TEMP_DIR, "compose")
    os.makedirs(work_dir, exist_ok=True)

    segments = script.get("segments", [])
    all_clips = []
    clip_idx = 0

    # Use the first news clip timestamp as freeze frame source
    first_news_ts = 0
    for seg in segments:
        if seg.get("type") in ("news_clip", "news_context"):
            first_news_ts = seg.get("clip_start", 0)
            break

    for seg in segments:
        seg_type = seg.get("type", "")
        clip_path = os.path.join(work_dir, f"clip_{clip_idx:03d}.mp4")

        if seg_type in ("news_clip", "news_context", "news_clip_final"):
            # Direct clip from source video
            start = seg.get("clip_start", 0)
            end = seg.get("clip_end", start + 15)
            print(f"  [{seg_type}] {start:.1f}s -> {end:.1f}s from source")
            result = build_news_clip_segment(
                video_path, start, end, clip_path, width, height,
            )
            if result:
                all_clips.append(result)
                clip_idx += 1

        elif seg_type == "cat_intro":
            print(f"  [cat_intro] Building with narration...")
            result = build_cat_segment(
                video_path=video_path,
                freeze_timestamp=first_news_ts,
                cat_path=cat_path,
                audio_path=seg.get("audio_path", ""),
                narration_text=seg.get("narration", ""),
                output_path=clip_path,
                width=width,
                height=height,
                bullet_points=seg.get("bullet_points", []),
                section_title="What To Watch For",
                music_path=music_path,
            )
            if result:
                all_clips.append(result)
                clip_idx += 1

        elif seg_type == "lecture":
            sections = seg.get("sections", [])
            for i, section in enumerate(sections):
                section_path = os.path.join(work_dir, f"clip_{clip_idx:03d}.mp4")
                title = section.get("section_title", f"Part {i+1}")
                print(f"  [lecture/{title}] Building section...")
                result = build_cat_segment(
                    video_path=video_path,
                    freeze_timestamp=first_news_ts + (i * 5),
                    cat_path=cat_path,
                    audio_path=section.get("audio_path", ""),
                    narration_text=section.get("narration", ""),
                    output_path=section_path,
                    width=width,
                    height=height,
                    bullet_points=section.get("key_points", []),
                    section_title=title,
                    music_path=music_path,
                )
                if result:
                    all_clips.append(result)
                    clip_idx += 1

        elif seg_type == "cat_wrapup":
            print(f"  [cat_wrapup] Building wrap-up...")
            result = build_cat_segment(
                video_path=video_path,
                freeze_timestamp=first_news_ts,
                cat_path=cat_path,
                audio_path=seg.get("audio_path", ""),
                narration_text=seg.get("narration", ""),
                output_path=clip_path,
                width=width,
                height=height,
                key_takeaway=seg.get("key_takeaway", ""),
                teaser_line=seg.get("teaser_line", ""),
                section_title="Key Takeaway",
                music_path=music_path,
            )
            if result:
                all_clips.append(result)
                clip_idx += 1

    if not all_clips:
        print("  ERROR: No clips produced!")
        return ""

    print(f"\n  Normalising {len(all_clips)} clips...")

    # Normalise all clips to same resolution/framerate
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
        ], f"normalise clip {idx}")
        if os.path.exists(norm_path):
            normalised.append(norm_path)
        else:
            normalised.append(clip)

    # Concat all clips
    concat_file = os.path.join(work_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for clip in normalised:
            # Use forward slashes for FFmpeg compatibility
            safe_path = clip.replace("\\", "/")
            f.write(f"file '{safe_path}'\n")

    # Generate output filename
    term = script.get("title_term", "finance")
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
        print(f"\n  DONE! {output_path}")
        print(f"  Size: {size_mb:.1f} MB | Duration: {duration:.1f}s ({duration/60:.1f} min)")
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
        print("  [Music] Add royalty-free ambient tracks for better production value.")
        return ""
    chosen = random.choice(tracks)
    print(f"  [Music] Using background track: {chosen}")
    return os.path.join(config.MUSIC_DIR, chosen)
