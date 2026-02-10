"""Step 1: Download YouTube video and extract transcript."""
import os
import json
import subprocess
import glob as globmod
from youtube_transcript_api import YouTubeTranscriptApi
import config


def _get_env_with_ffmpeg():
    """Get environment with refreshed PATH so FFmpeg is found."""
    env = os.environ.copy()
    # Append registry PATH entries to pick up recently installed tools like FFmpeg
    # while keeping existing PATH (venv, conda, etc.)
    try:
        import winreg
        extra_paths = []
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            extra_paths.append(winreg.QueryValueEx(key, "Path")[0])
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            extra_paths.append(winreg.QueryValueEx(key, "Path")[0])
        env["PATH"] = env.get("PATH", "") + ";" + ";".join(extra_paths)
    except Exception:
        pass
    return env


def get_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    if "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]
    raise ValueError(f"Could not extract video ID from URL: {url}")


def download_video(url: str, output_dir: str = None) -> str:
    """Download YouTube video using yt-dlp. Returns path to downloaded file."""
    output_dir = output_dir or config.TEMP_DIR
    output_path = os.path.join(output_dir, "source_video.mp4")

    # Clean up any existing source_video files
    for f in globmod.glob(os.path.join(output_dir, "source_video*")):
        try:
            os.remove(f)
        except Exception:
            pass

    env = _get_env_with_ffmpeg()

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--no-playlist",
        url,
    ]

    print(f"  Downloading video...")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"  yt-dlp stderr: {result.stderr}")
        # Try simpler format as fallback
        print(f"  Trying simpler format...")
        cmd_simple = [
            "yt-dlp",
            "-f", "best[height<=1080][ext=mp4]/best",
            "-o", output_path,
            "--no-playlist",
            url,
        ]
        result = subprocess.run(cmd_simple, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to download video: {result.stderr}")

    # Verify the file exists
    if not os.path.exists(output_path):
        # Check if yt-dlp saved with a slightly different name
        candidates = globmod.glob(os.path.join(output_dir, "source_video*"))
        if candidates:
            # Rename to expected path
            os.rename(candidates[0], output_path)
        else:
            raise RuntimeError(f"Video file not found after download at {output_path}")

    print(f"  Video saved to: {output_path}")
    return output_path


def get_transcript(video_id: str) -> list[dict]:
    """Get transcript from YouTube. Returns list of {text, start, duration}."""
    print(f"  Fetching transcript for video ID: {video_id}")

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        
        # Convert to simple dict format
        entries = []
        for entry in transcript.snippets:
            entries.append({
                "text": entry.text,
                "start": entry.start,
                "duration": entry.duration,
            })

        print(f"  Got {len(entries)} transcript segments")
        return entries

    except Exception as e:
        print(f"  Could not get transcript: {e}")
        print(f"  Will attempt audio transcription as fallback...")
        return []


def format_transcript_for_llm(transcript: list[dict]) -> str:
    """Format transcript into a readable string with timestamps for LLM analysis."""
    lines = []
    for entry in transcript:
        minutes = int(entry["start"] // 60)
        seconds = int(entry["start"] % 60)
        timestamp = f"[{minutes}:{seconds:02d}]"
        lines.append(f"{timestamp} {entry['text']}")
    return "\n".join(lines)


def get_video_metadata(url: str) -> dict:
    """Get video title, channel, description using yt-dlp."""
    env = _get_env_with_ffmpeg()
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--no-playlist",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return {"title": "Unknown", "channel": "Unknown", "description": ""}
    
    data = json.loads(result.stdout)
    return {
        "title": data.get("title", "Unknown"),
        "channel": data.get("channel", data.get("uploader", "Unknown")),
        "description": data.get("description", ""),
        "duration": data.get("duration", 0),
        "view_count": data.get("view_count", 0),
    }


def run(url: str) -> dict:
    """Run the full extraction step. Returns dict with all extracted data."""
    print("\n=== STEP 1: EXTRACT ===")

    video_id = get_video_id(url)
    print(f"  Video ID: {video_id}")

    # Get metadata
    metadata = get_video_metadata(url)
    print(f"  Title: {metadata['title']}")
    print(f"  Channel: {metadata['channel']}")

    # Download video
    video_path = download_video(url)

    # Get transcript
    transcript = get_transcript(video_id)
    formatted_transcript = format_transcript_for_llm(transcript)

    # Save transcript to temp
    transcript_path = os.path.join(config.TEMP_DIR, "transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(formatted_transcript)

    return {
        "video_id": video_id,
        "video_path": video_path,
        "metadata": metadata,
        "transcript": transcript,
        "formatted_transcript": formatted_transcript,
    }
