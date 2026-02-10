"""Voice generation for FinanceCats using ElevenLabs TTS.

V3: Two phases of voice generation:
  1. Cat conversation voices (Professor Whiskers + Cleo) — same as V2
  2. Anchor voice (handled separately in anchor_video.py)

The anchor's voice is generated via ElevenLabs TTS in anchor_video.py.
Only the cat dialogue uses ElevenLabs.
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
    voice_id = voice_id or config.CAT_A_VOICE_ID
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    # Adjust voice settings per character
    if voice_id == config.CAT_B_VOICE_ID:
        # Cleo: slightly more expressive, curious tone
        voice_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.4,
            "use_speaker_boost": True,
        }
    else:
        # Professor Whiskers: calm, authoritative
        voice_settings = {
            "stability": 0.6,
            "similarity_boost": 0.8,
            "style": 0.3,
            "use_speaker_boost": True,
        }

    data = {
        "text": text,
        "model_id": config.ELEVENLABS_MODEL,
        "voice_settings": voice_settings,
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


def _get_voice_id(speaker: str) -> str:
    """Map speaker tag to ElevenLabs voice ID."""
    if speaker == "cat_b":
        return config.CAT_B_VOICE_ID
    return config.CAT_A_VOICE_ID


def _generate_dialogue(dialogue: list[dict], voice_dir: str,
                        prefix: str) -> list[dict]:
    """Generate TTS for a list of dialogue turns.

    Each turn: {speaker: 'cat_a'|'cat_b', line: '...'}
    Returns list of dicts with audio_path, duration, speaker added.
    """
    results = []
    for i, turn in enumerate(dialogue):
        speaker = turn.get("speaker", "cat_a")
        line = turn.get("line", "")
        if not line:
            continue

        voice_id = _get_voice_id(speaker)
        filename = f"{prefix}_turn_{i:02d}_{speaker}.mp3"
        path = os.path.join(voice_dir, filename)

        result = generate_speech(line, path, voice_id=voice_id)
        if result:
            duration = get_audio_duration(path)
            turn["audio_path"] = path
            turn["actual_duration"] = duration
            results.append(turn)

    return results


def generate_cat_voices(cat_script: dict) -> dict:
    """Generate TTS audio for all cat dialogue exchanges.

    V3: Only generates cat voices. The anchor's voice is in anchor_video.py
    (or the fallback TTS is handled separately in anchor_video.py).

    Args:
        cat_script: The cat conversation script with exchanges

    Returns:
        Updated cat_script with audio paths and durations
    """
    print("\n=== VOICE GENERATION (Cat Conversation) ===")

    voice_dir = os.path.join(config.TEMP_DIR, "voices")
    os.makedirs(voice_dir, exist_ok=True)

    exchanges = cat_script.get("exchanges", [])
    total_generated = 0

    for j, exchange in enumerate(exchanges):
        dialogue = exchange.get("dialogue", [])
        if dialogue:
            title = exchange.get("exchange_title", f"Exchange {j+1}")
            results = _generate_dialogue(
                dialogue, voice_dir, f"cat_ex_{j:02d}"
            )
            total_generated += len(results)
            ex_dur = sum(
                t.get("actual_duration", 0)
                for t in dialogue
                if "actual_duration" in t
            )
            exchange["actual_duration"] = ex_dur
            print(f"  [cat/{title}] {len(results)} turns, {ex_dur:.1f}s")

    total_dur = sum(
        ex.get("actual_duration", 0)
        for ex in exchanges
    )

    print(f"  Total cat audio: {total_generated} segments, {total_dur:.1f}s")

    # Save updated script with audio info
    script_path = os.path.join(config.TEMP_DIR, "cat_script_with_audio.json")
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(cat_script, f, indent=2, ensure_ascii=False)

    return cat_script


# Legacy V2 compat (in case old code calls this)
def generate_segment_voices(script: dict) -> dict:
    """V2 backward-compat wrapper. Redirects to generate_cat_voices."""
    return generate_cat_voices(script)
