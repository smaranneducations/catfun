"""
FinanceCats — AI Finance Education Video Generator (V3)

AI news anchor reads viral economic/geopolitical news, then two professional
cats explain the financial term embedded in the story.

V3 Features:
  - Animated female news anchor (DALL-E image + ElevenLabs voice + animation)
  - Anchor always starts with "OK, this news is from [date]..."
  - Viral news from last 7 days (economic/geopolitical)
  - Financial term naturally embedded into anchor's script
  - Cats explain the term over frozen anchor frame
  - 100% original content (no third-party clips)
  - 3-4 minute videos
  - Gemini Flash for cheap tasks, GPT-4o for critical tasks

Pipeline:
  1. Viral News Scout finds the most viral story (Gemini Flash)
  2. Scout picks a teaching term to embed
  3. Historian researches the term (Gemini Flash)
  4. Script Writer creates anchor + cat scripts (GPT-4o)
  5. DALL-E generates animated anchor image
  6. ElevenLabs generates anchor voice + cat voices
  7. Compose: animated anchor → freeze → cats overlay
  8. Upload to YouTube + LinkedIn

Usage:
    python main.py                              # Full pipeline
    python main.py --retry                      # Retry failed uploads
    python main.py --new-anchor                 # Force generate a new anchor image
    python main.py --generate-cats              # Generate the 30-cat repository
    python main.py --generate-cats --count 5    # Generate 5 cats (testing)
    python main.py --no-upload                  # Generate video without uploading
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
from pipeline import voice_gen, compose_video
from pipeline.anchor_video import (
    generate_anchor_image,
    generate_anchor_image_fallback,
    generate_anchor_voice,
    compose_anchor_segment,
)
from pipeline.generate_thumbnail import generate_thumbnail
from pipeline.youtube_upload import upload_video
from pipeline.upload_tracker import log_upload, print_dashboard
from agents.linkedin_strategist import LinkedInStrategist
from pipeline.linkedin_post import post_video_to_linkedin


def print_banner():
    print("""
    =============================================
         F I N A N C E   C A T S   v3
      AI Finance Education Video Generator

      "Making finance make sense since 2026"

      AI Anchor + Cat Conversation Format
      100% Original Content | 3-4 min videos
    =============================================
    """)


def run_pipeline():
    """Run the full FinanceCats V3 pipeline."""
    start_time = time.time()

    # ── Phase 1: Agent Orchestration ──
    # Finds viral news → picks term → writes anchor + cat scripts
    orchestrator = AgentOrchestrator()
    agent_output = orchestrator.run_full_pipeline()

    if not agent_output:
        print("\n  ERROR: Agent pipeline failed. No output produced.")
        return

    term = agent_output.get("term", "Unknown")
    anchor_script = agent_output.get("anchor_script", {})
    cat_script = agent_output.get("cat_script", {})
    viral_story = agent_output.get("viral_story", {})

    # ── Phase 2: Generate Anchor Image + Voice ──
    print("\n" + "=" * 60)
    print("  PHASE: GENERATE ANIMATED ANCHOR (DALL-E + TTS)")
    print("=" * 60)

    anchor_text = anchor_script.get("anchor_script_text", "")
    if not anchor_text:
        print("  ERROR: No anchor script text. Cannot generate video.")
        return

    # Step 2a: Generate (or reuse cached) anchor image
    anchor_image_path = generate_anchor_image()
    if not anchor_image_path:
        print("  DALL-E failed — using fallback anchor image...")
        anchor_image_path = generate_anchor_image_fallback()

    if not anchor_image_path:
        print("  ERROR: Could not generate anchor image!")
        return

    # Step 2b: Generate anchor voiceover (ElevenLabs TTS)
    anchor_audio_path = generate_anchor_voice(
        script_text=anchor_text,
        output_path=os.path.join(config.TEMP_DIR, "anchor_voice.mp3"),
    )
    if not anchor_audio_path:
        print("  ERROR: Could not generate anchor voice!")
        return

    # Step 2c: Compose anchor segment (image + voice + animation + graphics)
    anchor_result = compose_anchor_segment(
        anchor_image_path=anchor_image_path,
        anchor_audio_path=anchor_audio_path,
        output_path=os.path.join(config.TEMP_DIR, "anchor_segment.mp4"),
        headline=viral_story.get("headline", ""),
        story_date=viral_story.get("date", ""),
        term=term,
    )

    anchor_video_path = anchor_result.get("video_path", "")
    if not anchor_video_path:
        print(f"  ERROR: Anchor segment failed: {anchor_result.get('error', '?')}")
        return

    print(f"  Anchor segment ready: {anchor_result.get('duration', '?')}s")

    # ── Phase 3: Generate Cat Voices ──
    print("\n" + "=" * 60)
    print("  PHASE: GENERATE CAT VOICES")
    print("=" * 60)

    cat_script = voice_gen.generate_cat_voices(cat_script)

    # ── Phase 4: Compose Video ──
    print("\n" + "=" * 60)
    print("  PHASE: COMPOSE VIDEO")
    print("=" * 60)

    cat_selection = agent_output.get("cat_selection", {})
    cat_a_path = cat_selection.get("cat_a", {}).get("cat_path", "")
    cat_b_path = cat_selection.get("cat_b", {}).get("cat_path", "")

    metadata = {
        "title": agent_output.get("youtube_package", {}).get("titles", {}).get("primary", ""),
        "term": term,
        "story_date": viral_story.get("date", ""),
        "story_headline": viral_story.get("headline", ""),
    }

    output_path = compose_video.compose_video(
        anchor_video_path=anchor_video_path,
        anchor_audio_path="",  # Not needed — anchor_video_path already has audio
        cat_script=cat_script,
        cat_a_path=cat_a_path,
        cat_b_path=cat_b_path,
        metadata=metadata,
    )

    if not output_path or not os.path.exists(output_path):
        print("  ERROR: Video composition failed!")
        return

    # ── Phase 5: Generate Thumbnail ──
    print("\n" + "=" * 60)
    print("  PHASE: GENERATE THUMBNAIL")
    print("=" * 60)

    yt_pkg = agent_output.get("youtube_package", {})
    thumbnail_text = yt_pkg.get("thumbnail_text", term)

    # Use anchor video for thumbnail background (or the composed video as fallback)
    thumb_source = anchor_video_path if anchor_video_path else output_path

    thumbnail_path = generate_thumbnail(
        anchor_video_path=thumb_source,
        cat_a_path=cat_a_path,
        cat_b_path=cat_b_path,
        term=term,
        thumbnail_text=thumbnail_text,
    )

    # ── Phase 6: Upload to YouTube ──
    print("\n" + "=" * 60)
    print("  PHASE: UPLOAD TO YOUTUBE")
    print("=" * 60)

    titles = yt_pkg.get("titles", {})
    title = titles.get("primary", f"What is {term}?")
    description = yt_pkg.get("description", "")
    tags = yt_pkg.get("tags", [])
    category_id = "27"  # Education

    # Build playlist name from series
    ep_data_pre = agent_output.get("episode_data", {})
    log = orchestrator.producer.load_episode_log()
    series_list = log.get("series", [])
    playlist_title = None
    if series_list:
        current_series = series_list[-1]
        playlist_title = current_series.get(
            "series_name",
            f"FinanceCats Series {current_series.get('series_id', 1)}",
        )

    upload_result = {}
    should_upload = "--no-upload" not in sys.argv
    if output_path and should_upload:
        try:
            upload_result = upload_video(
                video_path=output_path,
                title=title,
                description=description,
                tags=tags,
                thumbnail_path=thumbnail_path,
                category_id=category_id,
                privacy="public",
                playlist_title=playlist_title,
            )
        except Exception as e:
            print(f"\n  YouTube upload failed: {e}")
            upload_result = {"error": str(e)}
    elif not should_upload:
        print("\n  [YouTube] Upload skipped (--no-upload flag)")
        upload_result = {"skipped": True}

    # ── Phase 6b: Track Upload ──
    if output_path:
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        from pipeline.compose_video import _ffprobe_duration
        duration_secs = _ffprobe_duration(output_path)

        upload_status = "success" if upload_result.get("video_id") else (
            "skipped" if upload_result.get("skipped") else "failed"
        )

        log_upload(
            term=term,
            title=title,
            video_path=output_path,
            thumbnail_path=thumbnail_path or "",
            youtube_video_id=upload_result.get("video_id", ""),
            youtube_url=upload_result.get("url", ""),
            playlist_id=upload_result.get("playlist_id", ""),
            playlist_name=playlist_title or "",
            privacy="public",
            category_id=category_id,
            tags=tags,
            description=description,
            status=upload_status,
            error_message=str(upload_result.get("error", "")),
            episode_number=len(log.get("episodes", [])) + 1,
            series_id=ep_data_pre.get("series_id", 0),
            series_position=ep_data_pre.get("series_position", 0),
            news_source="AI Anchor (DALL-E + ElevenLabs)",
            news_clip_date=viral_story.get("date", ""),
            duration_seconds=duration_secs,
            file_size_mb=file_size_mb,
        )

    # ── Phase 6c: Post to LinkedIn ──
    linkedin_result = {}
    should_linkedin = "--no-linkedin" not in sys.argv and should_upload
    if output_path and should_linkedin:
        try:
            print("\n  [LinkedIn] Generating post copy...")
            li_strategist = LinkedInStrategist()
            li_package = li_strategist.create_post(
                term=term,
                script_summary=json.dumps(
                    cat_script.get("exchanges", [])[:3], default=str
                )[:2000],
                youtube_url=upload_result.get("url", ""),
                episode_history=log.get("episodes", []),
            )

            li_post_text = li_package.get("post_text", "")
            li_hashtags = li_package.get("hashtags", [])
            if li_hashtags and not any(f"#{h}" in li_post_text for h in li_hashtags):
                li_post_text += "\n\n" + " ".join(f"#{h}" for h in li_hashtags)

            linkedin_result = post_video_to_linkedin(
                video_path=output_path,
                commentary=li_post_text,
                video_title=title,
            )
        except Exception as e:
            print(f"\n  LinkedIn post failed: {e}")
            linkedin_result = {"error": str(e)}
    elif not should_linkedin:
        print("\n  [LinkedIn] Post skipped")

    # ── Phase 7: Determine publish_status + Log Episode ──
    if output_path:
        episode_data = agent_output.get("episode_data", {})
        episode_data["output_file"] = output_path
        episode_data["thumbnail_file"] = thumbnail_path or ""
        episode_data["date"] = time.strftime("%Y-%m-%d")
        episode_data["youtube_video_id"] = upload_result.get("video_id", "")
        episode_data["youtube_url"] = upload_result.get("url", "")
        episode_data["youtube_playlist_id"] = upload_result.get("playlist_id", "")
        episode_data["linkedin_post_id"] = linkedin_result.get("post_id", "")
        episode_data["linkedin_post_url"] = linkedin_result.get("post_url", "")
        episode_data["youtube_verification"] = upload_result.get("verification_stages", {})
        episode_data["linkedin_verification"] = linkedin_result.get("verification_stages", {})
        episode_data["anchor_type"] = "dalle_animated"

        yt_ok = upload_result.get("verified", False)
        li_ok = linkedin_result.get("verified", False)
        li_skipped = not should_linkedin

        if not should_upload:
            episode_data["publish_status"] = "draft"
        elif yt_ok and (li_ok or li_skipped):
            episode_data["publish_status"] = "published"
        elif yt_ok or li_ok:
            episode_data["publish_status"] = "partial"
        else:
            episode_data["publish_status"] = "failed"

        orchestrator.producer.log_episode(episode_data)

    # ── Summary ──
    elapsed = time.time() - start_time
    ep_data = agent_output.get("episode_data", {})
    pub_status = episode_data.get("publish_status", "unknown") if output_path else "failed"
    status_labels = {
        "published": "PUBLISHED (all uploads verified)",
        "partial": "PARTIAL (some uploads failed — retry with: python main.py --retry)",
        "failed": "FAILED (uploads failed — retry with: python main.py --retry)",
        "draft": "DRAFT (uploads skipped)",
    }

    print(f"\n{'=' * 60}")
    print(f"  PIPELINE COMPLETE! (V3: AI Anchor + Cat Conversation)")
    print(f"  Status: {status_labels.get(pub_status, pub_status)}")
    print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Term: {term}")
    print(f"  Viral Story: {viral_story.get('headline', 'N/A')[:60]}")
    print(f"  Output: {output_path or 'FAILED'}")
    print(f"  Thumbnail: {thumbnail_path or 'FAILED'}")
    if titles:
        print(f"  Title: {titles.get('primary', 'N/A')}")
    print(f"  Anchor: DALL-E image + ElevenLabs voice + animation")

    if upload_result.get("url"):
        yt_passed = upload_result.get("verification_passed", 0)
        yt_total = upload_result.get("verification_total", 0)
        yt_label = "ALL VERIFIED" if upload_result.get("verified") else f"{yt_passed}/{yt_total} verified"
        print(f"  YouTube: {upload_result['url']} [{yt_label}]")
        yt_stages = upload_result.get("verification_stages", {})
        if yt_stages:
            for stage, ok in yt_stages.items():
                icon = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
                print(f"    [{icon}] {stage}")
    elif upload_result.get("error"):
        print(f"  YouTube: UPLOAD FAILED — {upload_result['error']}")

    if linkedin_result.get("post_url"):
        li_passed = linkedin_result.get("verification_passed", 0)
        li_total = linkedin_result.get("verification_total", 0)
        li_label = "ALL VERIFIED" if linkedin_result.get("verified") else f"{li_passed}/{li_total} verified"
        print(f"  LinkedIn: {linkedin_result['post_url']} [{li_label}]")
    elif linkedin_result.get("error"):
        print(f"  LinkedIn: POST FAILED — {linkedin_result['error']}")

    print(f"  Cats: {config.CAT_A_NAME} + {config.CAT_B_NAME}")
    next_term = cat_script.get("teaser_term", "")
    if next_term:
        print(f"  Next Episode Teaser: '{next_term}'")
    if playlist_title:
        print(f"  Playlist: {playlist_title}")
    print(f"  Content: 100% original (no third-party clips)")
    print(f"{'=' * 60}\n")

    print_dashboard()


def retry_failed_uploads():
    """Retry uploads for the most recent unpublished episode."""
    print("\n  Mode: RETRY — Re-uploading last failed episode\n")

    from agents.executive_producer import ExecutiveProducer
    producer = ExecutiveProducer()
    ep = producer.get_last_unpublished_episode()

    if not ep:
        print("  No unpublished episodes found. Nothing to retry.")
        return

    ep_num = ep.get("episode_number", "?")
    term = ep.get("term", "?")
    status = ep.get("publish_status", "?")
    output_path = ep.get("output_file", "")
    thumbnail_path = ep.get("thumbnail_file", "")

    print(f"  Found unpublished episode #{ep_num}: '{term}' (status: {status})")

    if not output_path or not os.path.exists(output_path):
        print(f"  ERROR: Video file not found: {output_path}")
        print(f"  Cannot retry — run: python main.py")
        return

    title = ep.get("title", f"What is {term}?")
    description = ep.get("description", "")
    tags = ep.get("tags", [])
    category_id = "27"

    log = producer.load_episode_log()
    series_list = log.get("series", [])
    playlist_title = None
    if series_list:
        current_series = series_list[-1]
        playlist_title = current_series.get(
            "series_name",
            f"FinanceCats Series {current_series.get('series_id', 1)}",
        )

    # Retry YouTube
    yt_already_ok = bool(ep.get("youtube_video_id"))
    upload_result = {}

    if yt_already_ok:
        print(f"\n  [YouTube] Already uploaded: {ep.get('youtube_url', '')}")
        upload_result = {"video_id": ep["youtube_video_id"],
                         "url": ep["youtube_url"], "verified": True}
    else:
        print(f"\n  [YouTube] Retrying upload...")
        if "--no-upload" not in sys.argv:
            try:
                upload_result = upload_video(
                    video_path=output_path,
                    title=title,
                    description=description,
                    tags=tags,
                    thumbnail_path=thumbnail_path if os.path.exists(thumbnail_path or "") else None,
                    category_id=category_id,
                    privacy="public",
                    playlist_title=playlist_title,
                )
            except Exception as e:
                upload_result = {"error": str(e)}
        else:
            upload_result = {"skipped": True}

    # Retry LinkedIn
    li_already_ok = bool(ep.get("linkedin_post_id"))
    linkedin_result = {}
    should_linkedin = "--no-linkedin" not in sys.argv and "--no-upload" not in sys.argv

    if li_already_ok:
        print(f"\n  [LinkedIn] Already posted: {ep.get('linkedin_post_url', '')}")
        linkedin_result = {"post_id": ep["linkedin_post_id"],
                           "post_url": ep["linkedin_post_url"], "verified": True}
    elif should_linkedin and output_path:
        try:
            print("\n  [LinkedIn] Retrying post...")
            li_strategist = LinkedInStrategist()
            li_package = li_strategist.create_post(
                term=term, script_summary="",
                youtube_url=upload_result.get("url", ep.get("youtube_url", "")),
                episode_history=log.get("episodes", []),
            )
            li_post_text = li_package.get("post_text", "")
            li_hashtags = li_package.get("hashtags", [])
            if li_hashtags and not any(f"#{h}" in li_post_text for h in li_hashtags):
                li_post_text += "\n\n" + " ".join(f"#{h}" for h in li_hashtags)

            linkedin_result = post_video_to_linkedin(
                video_path=output_path,
                commentary=li_post_text,
                video_title=title,
            )
        except Exception as e:
            linkedin_result = {"error": str(e)}

    # Update status
    yt_ok = upload_result.get("verified", False) or yt_already_ok
    li_ok = linkedin_result.get("verified", False) or li_already_ok
    li_skipped = not should_linkedin

    if yt_ok and (li_ok or li_skipped):
        new_status = "published"
    elif yt_ok or li_ok:
        new_status = "partial"
    else:
        new_status = "failed"

    updates = {
        "publish_status": new_status,
        "youtube_video_id": upload_result.get("video_id", ep.get("youtube_video_id", "")),
        "youtube_url": upload_result.get("url", ep.get("youtube_url", "")),
        "youtube_playlist_id": upload_result.get("playlist_id", ep.get("youtube_playlist_id", "")),
        "youtube_verification": upload_result.get("verification_stages", {}),
        "linkedin_post_id": linkedin_result.get("post_id", ep.get("linkedin_post_id", "")),
        "linkedin_post_url": linkedin_result.get("post_url", ep.get("linkedin_post_url", "")),
        "linkedin_verification": linkedin_result.get("verification_stages", {}),
        "retry_date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    producer.update_episode_status(ep_num, updates)

    status_labels = {
        "published": "PUBLISHED (all uploads verified)",
        "partial": "PARTIAL (some still failing)",
        "failed": "FAILED (all still failing)",
    }
    print(f"\n{'=' * 60}")
    print(f"  RETRY COMPLETE for episode #{ep_num}: '{term}'")
    print(f"  Status: {status_labels.get(new_status, new_status)}")
    if upload_result.get("url"):
        print(f"  YouTube: {upload_result['url']}")
    if linkedin_result.get("post_url"):
        print(f"  LinkedIn: {linkedin_result['post_url']}")
    if new_status != "published":
        print(f"  To retry again: python main.py --retry")
    print(f"{'=' * 60}\n")

    print_dashboard()


def generate_new_anchor():
    """Force-generate a new anchor image via DALL-E."""
    print("\n  Generating a new anchor image via DALL-E 3...\n")
    path = generate_anchor_image(force_new=True)
    if path:
        print(f"\n  New anchor saved: {path}")
        print(f"  This will be used for all future videos.")
        print(f"  Run again to generate a different look.")
    else:
        print(f"\n  Failed to generate anchor. Check your OPENAI_API_KEY.")


def main():
    print_banner()

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--generate-cats":
            from pipeline.generate_cats import generate_all_cats
            count = 30
            if len(sys.argv) > 3 and sys.argv[2] == "--count":
                count = int(sys.argv[3])
            generate_all_cats(count)
            return

        elif arg == "--retry":
            retry_failed_uploads()
            return

        elif arg == "--new-anchor":
            generate_new_anchor()
            return

        elif arg in ("--no-upload", "--no-linkedin"):
            # These are flags, not commands — run pipeline with them
            pass

        else:
            print(f"  Usage:")
            print(f"    python main.py                          # Full pipeline")
            print(f"    python main.py --retry                  # Retry failed uploads")
            print(f"    python main.py --new-anchor             # Generate new anchor image")
            print(f"    python main.py --generate-cats          # Generate cat images")
            print(f"    python main.py --no-upload              # Skip uploads")
            sys.exit(1)
    else:
        print("  Mode: Full pipeline (find viral news → anchor → cats → upload)\n")

    run_pipeline()


if __name__ == "__main__":
    main()
