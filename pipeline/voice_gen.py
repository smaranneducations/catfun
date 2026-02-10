"""Voice generation for FinanceCats using ElevenLabs TTS.

Single narrator voice: clear British accent (Daniel).
Generates TTS audio for all cat-narrated segments.
"""
import os
import json
import requests
from mutagen.mp3 import MP3
import config


ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


def generate_speech(text: str, output_path: str,
                    voice_id: str = None) -> str:
    """Generate speech audio using ElevenLabs API.

    Returns path to generated MP3, or empty string on failure.
    """
    voice_id = voice_id or config.NARRATOR_VOICE_ID
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    data = {
        "text": text,
        "model_id": config.ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": 0.6,       # Slightly more stable for educational tone
            "similarity_boost": 0.8,
            "style": 0.3,           # Less dramatic, more clear
            "use_speaker_boost": True,
        },
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        print(f"    TTS Error: {response.status_code} {response.text[:200]}")
        return ""

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def get_audio_duration(path: str) -> float:
    """Get duration of an MP3 file in seconds."""
    try:
        audio = MP3(path)
        return audio.info.length
    except Exception:
        return 0.0


def generate_segment_voices(script: dict) -> dict:
    """Generate TTS audio for all narrated segments in the script.

    Returns updated script with audio_path and actual_duration added to each
    narrated segment/section.
    """
    print("\n=== VOICE GENERATION ===")

    voice_dir = os.path.join(config.TEMP_DIR, "voices")
    os.makedirs(voice_dir, exist_ok=True)

    segments = script.get("segments", [])
    total_generated = 0

    for seg in segments:
        seg_type = seg.get("type", "")

        if seg_type == "cat_intro":
            # Single narration
            narration = seg.get("narration", "")
            if narration:
                path = os.path.join(voice_dir, "seg2_cat_intro.mp3")
                result = generate_speech(narration, path)
                if result:
                    duration = get_audio_duration(path)
                    seg["audio_path"] = path
                    seg["actual_duration"] = duration
                    total_generated += 1
                    print(f"  [cat_intro] {duration:.1f}s generated")

        elif seg_type == "lecture":
            # Multiple sections
            sections = seg.get("sections", [])
            for i, section in enumerate(sections):
                narration = section.get("narration", "")
                if narration:
                    path = os.path.join(voice_dir, f"seg4_lecture_{i}.mp3")
                    result = generate_speech(narration, path)
                    if result:
                        duration = get_audio_duration(path)
                        section["audio_path"] = path
                        section["actual_duration"] = duration
                        total_generated += 1
                        title = section.get("section_title", f"Section {i+1}")
                        print(f"  [lecture/{title}] {duration:.1f}s generated")

        elif seg_type == "cat_wrapup":
            # Single narration
            narration = seg.get("narration", "")
            if narration:
                path = os.path.join(voice_dir, "seg6_cat_wrapup.mp3")
                result = generate_speech(narration, path)
                if result:
                    duration = get_audio_duration(path)
                    seg["audio_path"] = path
                    seg["actual_duration"] = duration
                    total_generated += 1
                    print(f"  [cat_wrapup] {duration:.1f}s generated")

    print(f"  Total audio segments generated: {total_generated}")

    # Save updated script with audio info
    script_path = os.path.join(config.TEMP_DIR, "script_with_audio.json")
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    return script
