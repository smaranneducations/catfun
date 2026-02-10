"""
FinanceCats — AI Finance Education Video Generator

A professional cat character pauses real financial news clips to explain
complex terminology, backed by historical examples and storytelling.

Powered by a 7-agent orchestration system:
  Executive Producer, Research Analyst, Financial Historian,
  Script Writer, Fact Checker, Creative Director, YouTube Strategist

Usage:
    python main.py                              # Auto-select topic and clip
    python main.py "https://youtube.com/..."    # Use a specific news clip
    python main.py --generate-cats              # Generate the 30-cat repository
    python main.py --generate-cats --count 5    # Generate 5 cats (testing)
"""
import sys
import time
import json
import os

# Fix Windows console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Append registry PATH for FFmpeg (Windows)
try:
    import winreg
    extra = []
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
        extra.append(winreg.QueryValueEx(key, "Path")[0])
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
        extra.append(winreg.QueryValueEx(key, "Path")[0])
    os.environ["PATH"] = os.environ.get("PATH", "") + ";" + ";".join(extra)
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from agents.orchestrator import AgentOrchestrator
from pipeline import step1_extract, voice_gen, compose_video


def print_banner():
    print("""
    =============================================
         F I N A N C E   C A T S
      AI Finance Education Video Generator

      "Making finance make sense since 2026"

      7-Agent Orchestration System
    =============================================
    """)


def run_pipeline(url: str = None):
    """Run the full FinanceCats pipeline."""
    start_time = time.time()

    # ── Phase 1: Agent Orchestration ──
    # Agents decide topic, find clip, research history, write script,
    # fact-check, design visuals, and create YouTube package
    orchestrator = AgentOrchestrator()

    # If user provided a URL, pass it as pre-selected clip
    clip_info = None
    transcript = None

    if url:
        print(f"\n  Pre-selected clip: {url}")
        print("  Downloading and extracting transcript...\n")
        extract_data = step1_extract.run(url)
        transcript = extract_data.get("formatted_transcript", "")
        clip_info = {
            "url": url,
            "video_id": extract_data.get("video_id", ""),
            "channel": extract_data.get("metadata", {}).get("channel", ""),
            "title": extract_data.get("metadata", {}).get("title", ""),
            "duration": extract_data.get("metadata", {}).get("duration", 0),
        }
        video_path = extract_data.get("video_path", "")
    else:
        video_path = None

    # Run the 7-agent system
    agent_output = orchestrator.run_full_pipeline(
        transcript=transcript,
        clip_info=clip_info,
    )

    # ── Phase 2: Download clip if not already done ──
    if not video_path:
        selected = agent_output.get("selected_clip", {})

        # Try to get URL from candidates
        candidates = selected.get("candidates", [])
        if candidates:
            # Use the first candidate (Research Analyst already ranked them)
            clip_url = candidates[0].get("url", "")
        else:
            clip_url = selected.get("url", "")

        if not clip_url:
            print("\n  ERROR: No clip URL found. The agents couldn't find a suitable clip.")
            print("  Try running with a specific URL: python main.py \"https://youtube.com/...\"")
            return

        print(f"\n  Downloading selected clip: {clip_url}")
        extract_data = step1_extract.run(clip_url)
        video_path = extract_data.get("video_path", "")
        transcript = extract_data.get("formatted_transcript", "")

        # If transcript wasn't available during agent phase, let Script Writer
        # know the actual timestamps (the script uses estimated timestamps)
        if not transcript:
            print("  WARNING: No transcript available. Script uses estimated timestamps.")

    if not video_path or not os.path.exists(video_path):
        print("  ERROR: Could not download video. Aborting.")
        return

    # ── Phase 3: Generate Voices ──
    script = agent_output.get("script", {})
    script = voice_gen.generate_segment_voices(script)

    # ── Phase 4: Compose Video ──
    cat_path = agent_output.get("cat_selection", {}).get("cat_path", "")
    metadata = {
        "title": agent_output.get("youtube_package", {}).get("titles", {}).get("primary", ""),
        "term": agent_output.get("term", ""),
    }

    output_path = compose_video.compose_video(
        video_path=video_path,
        script=script,
        cat_path=cat_path,
        metadata=metadata,
    )

    # ── Phase 5: Log Episode ──
    if output_path:
        episode_data = agent_output.get("episode_data", {})
        episode_data["output_file"] = output_path
        episode_data["date"] = time.strftime("%Y-%m-%d")
        orchestrator.producer.log_episode(episode_data)

    # ── Summary ──
    elapsed = time.time() - start_time
    yt_pkg = agent_output.get("youtube_package", {})
    titles = yt_pkg.get("titles", {})

    print(f"\n{'=' * 60}")
    print(f"  PIPELINE COMPLETE!")
    print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Term: {agent_output.get('term', 'N/A')}")
    print(f"  Output: {output_path or 'FAILED'}")
    if titles:
        print(f"  Suggested Title: {titles.get('primary', 'N/A')}")
    print(f"  Agents: 7 (Executive Producer, Research Analyst,")
    print(f"    Financial Historian, Script Writer, Fact Checker,")
    print(f"    Creative Director, YouTube Strategist)")
    print(f"{'=' * 60}\n")


def main():
    print_banner()

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--generate-cats":
            # Cat generation mode
            from pipeline.generate_cats import generate_all_cats
            count = 30
            if len(sys.argv) > 3 and sys.argv[2] == "--count":
                count = int(sys.argv[3])
            generate_all_cats(count)
            return

        elif arg.startswith("http"):
            # Specific URL mode
            run_pipeline(url=arg)
            return

        else:
            print(f"  Usage:")
            print(f"    python main.py                          # Auto-select")
            print(f"    python main.py \"https://youtube.com/..\" # Specific clip")
            print(f"    python main.py --generate-cats           # Generate cat images")
            sys.exit(1)
    else:
        # Auto mode — agents decide everything
        print("  Mode: Auto-select (agents will find the best topic and clip)\n")
        run_pipeline()


if __name__ == "__main__":
    main()
