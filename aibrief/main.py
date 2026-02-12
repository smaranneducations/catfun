"""AI Brief — Autonomous AI Thought Leadership Publisher.

Full autonomous pipeline:
  Phase 0:  World Pulse → scan global sentiment
  Phase 1:  Content Strategy → choose content type + length
  Phase 2:  Topic Discovery → find topic + semantic dedup
  Phase 3:  Design DNA → visual identity + debate
  Phase 4:  Analyst Pairs → 4× preparer/reviewer argue
  Phase 5:  Round Table → cross-agent challenges
  Phase 6:  Editorial Oversight → editor reviews all
  Phase 7:  Content Synthesis → writer + copy reviewer argue
  Phase 8:  Neutrality Check → ethical guardrail
  Phase 8.5: Discussion Potential → engagement hooks
  Phase 8.7: Pre-Visual Validation → content gate
  Phase 9:  Visuals → Imagen + DALL-E + Pillow
  Phase 10: PDF → luxury poster + debates section
  Phase 11: Screen Audit → golden ratio page fill
  Phase 12: Post-Visual Validation → layout gate
  Phase 13: LinkedIn → post with dynamic document title

Every phase TRACED with full input/output provenance.

Usage:
    python -m aibrief.main                # Full autonomous run
    python -m aibrief.main --no-post      # Generate PDF only, skip LinkedIn
    python -m aibrief.main --dry-run      # World Pulse + Content Strategy only
    python -m aibrief.main --sim          # Simulation: regenerate PDF from latest trace (no images, no LinkedIn)
    python -m aibrief.main --repost       # Repost last run to LinkedIn (zero regeneration)
"""
import sys
import json

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def print_banner():
    print("""
    ╔═════════════════════════════════════════════════════════╗
    ║              A I   B R I E F   v 3 . 5                  ║
    ║   Autonomous AI Thought Leadership Publisher            ║
    ║                                                         ║
    ║   POSTER + Debates + Agent Credits + Mind Map           ║
    ║   12 Styles • 10 Fonts • 10 Palettes (from catalog)    ║
    ║                                                         ║
    ║   15 Phases • 20+ Agents • Full Run Tracer             ║
    ║   Gemini Flash + GPT-4o + Imagen + DALL-E + Pillow     ║
    ╚═════════════════════════════════════════════════════════╝
    """)


def run_sim():
    """Simulation mode: load latest trace, reuse images, regenerate PDF only.

    No new news download, no image generation (except persona images once),
    no LinkedIn posting. Just iterate on PDF layout.
    """
    import re
    from pathlib import Path
    from aibrief import config

    traces_dir = config.BASE_DIR / "traces"
    trace_files = sorted(traces_dir.glob("run_*.json"), reverse=True)
    if not trace_files:
        print("  ✗ No trace files found. Run a full pipeline first.")
        return

    latest_trace = trace_files[0]
    print(f"\n  [SIM] Loading trace: {latest_trace.name}")
    trace = json.loads(latest_trace.read_text(encoding="utf-8"))

    # ── Extract data from the trace ──
    phases = trace.get("phases", [])

    def _find_phase(name):
        for p in phases:
            phase_name = p.get("phase", "")
            # Exact match or starts-with (handles TopicDiscovery_attempt1 etc.)
            if phase_name == name or phase_name.startswith(name):
                out = p.get("output", {})
                if out:
                    return out
        return {}

    pulse = _find_phase("WorldPulse")
    strategy = _find_phase("ContentStrategy")
    story = _find_phase("TopicDiscovery")
    design = _find_phase("DesignDNA")
    brief = _find_phase("ContentSynthesis")

    # If brief came out empty, check for different phase name patterns
    if not brief:
        for p in phases:
            if "Synthesis" in p.get("phase", "") or "Content" in p.get("phase", ""):
                out = p.get("output", {})
                if out.get("pages") or out.get("brief_title"):
                    brief = out
                    break

    if not brief or not brief.get("pages"):
        print("  ✗ Could not find a valid brief in the trace. Run full pipeline first.")
        return

    print(f"  [SIM] Topic: {story.get('headline', '?')}")
    print(f"  [SIM] Brief: {brief.get('brief_title', '?')} ({len(brief.get('pages', []))} pages)")
    print(f"  [SIM] Design: {design.get('design_name', '?')}")

    # ── Locate existing images (check new organized dirs + old flat dir) ──
    from aibrief.pipeline.image_cache import (
        BACKGROUNDS_DIR, FOREGROUNDS_DIR, COVERS_DIR,
        migrate_legacy_images,
    )
    visuals_dir = config.OUTPUT_DIR / "visuals"
    run_id = trace.get("run_id", "")
    style_id = design.get("style_id", "")

    visuals = {}

    # Cover: check new dir, then old flat dir
    for cdir in [COVERS_DIR, visuals_dir]:
        cover_path = cdir / f"cover_{run_id}.png"
        if cover_path.exists():
            visuals["cover"] = str(cover_path)
            print(f"  [SIM] Reusing cover: {cover_path.name}")
            break

    # Background + foreground images: check organized dirs first, then flat
    for i in range(6):
        # Backgrounds (theme-cached)
        for bdir in [BACKGROUNDS_DIR, visuals_dir]:
            bg_path = bdir / f"bg_theme_{style_id}_{i}.png"
            if bg_path.exists():
                visuals[f"bg_{i}"] = str(bg_path)
                break
        else:
            # Also try old run-based path
            bg_old = visuals_dir / f"bg_{run_id}_{i}.png"
            if bg_old.exists():
                visuals[f"bg_{i}"] = str(bg_old)

        # Foregrounds (run-specific)
        for fdir in [FOREGROUNDS_DIR, visuals_dir]:
            fg_path = fdir / f"fg_{run_id}_{i}.png"
            if fg_path.exists():
                visuals[f"fg_{i}"] = str(fg_path)
                break

    print(f"  [SIM] Reusing {len(visuals)} cached images")

    # ── Generate persona images (cached — only downloads once) ──
    from aibrief.pipeline.poster_gen import generate_poster, generate_persona_images
    print(f"\n  [SIM] Generating persona images (cached)...")
    persona_paths = generate_persona_images()
    print(f"  [SIM] {len(persona_paths)} persona images ready")

    # ── Build agents_info from agent_config.json ──
    cfg_path = config.BASE_DIR / "agent_config.json"
    agents_info = []
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        for agent_name, data in cfg.get("agents", {}).items():
            agents_info.append({
                "name": agent_name,
                "codename": data.get("name", ""),
                "role": data.get("role", ""),
                "mandate": data.get("fixed_strings", {}).get(
                    "core_instruction", ""),
            })

    # ── Build tracer_flow from trace data ──
    pre_val = _find_phase("PreVisualValidation")
    post_val = _find_phase("PostVisualValidation")
    pre_score = pre_val.get("total_score", 0) if pre_val else 0
    post_score = post_val.get("total_score", 0) if post_val else 0
    combined = round((pre_score + post_score) / 2, 1) if (pre_score or post_score) else 0

    tracer_flow = {
        "entries": phases,
        "run_id": run_id,
        "agent_flow": trace.get("agent_flow", []),
        "total_duration": trace.get("total_duration_seconds", 0),
        "total_agents": trace.get("total_agent_calls", 0),
        "total_debates": trace.get("total_debates", 0),
        "key_outputs": {
            "world_mood": pulse.get("mood", "normal"),
            "content_type": strategy.get("content_type", ""),
            "emotion": design.get("emotion", ""),
            "design_name": design.get("design_name", ""),
            "imagen_style": design.get("imagen_style", ""),
            "validation_score": combined,
        },
    }

    # ── Generate PDF ──
    slug = brief.get("brief_title", "AI_Brief")[:35]
    slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
    output_path = str(config.OUTPUT_DIR / f"{slug}_SIM.pdf")

    print(f"\n  [SIM] Generating PDF...")
    pdf_path = generate_poster(
        brief, design, story,
        visuals=visuals,
        agents_info=agents_info,
        tracer_flow=tracer_flow,
        strategy=strategy,
        output_path=output_path,
        persona_paths=persona_paths,
    )

    print(f"\n  {'─' * 50}")
    print(f"  ✓ PDF: {pdf_path}")
    print(f"  ✓ Mode: SIMULATION (no images downloaded, no LinkedIn)")
    print(f"  ✓ Source trace: {latest_trace.name}")
    print(f"  {'─' * 50}")


def run(no_post: bool = False, dry_run: bool = False):
    """Run the full autonomous pipeline."""
    from aibrief import config

    # Override LinkedIn posting if --no-post
    if no_post:
        # Temporarily patch the config
        cfg_path = config.BASE_DIR / "agent_config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["controls"]["post_to_linkedin"] = False
            cfg_path.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
            print("  [Config] LinkedIn posting DISABLED (--no-post)")

    from aibrief.agents.orchestrator import AutonomousOrchestrator

    orchestrator = AutonomousOrchestrator()

    if dry_run:
        # Only run Phase 0 and Phase 1 for testing
        print("\n  [DRY RUN] — Only running World Pulse + Content Strategy\n")
        pulse = orchestrator._phase_world_pulse()
        strategy = orchestrator._phase_content_strategy(pulse)
        orchestrator.tracer.save({"dry_run": True, "pulse": pulse, "strategy": strategy})
        print(f"\n  Pulse: {pulse.get('mood')} (score: {pulse.get('sentiment_score')})")
        print(f"  Strategy: {strategy.get('content_type')}, {strategy.get('page_count')} pages")
        return

    result = orchestrator.run()

    if result.get("decision") == "SILENT":
        print("\n  Today's decision: SILENT — world sentiment too extreme.")
        return

    print(f"\n  {'─' * 50}")
    print(f"  ✓ PDF: {result.get('pdf_path', 'N/A')}")
    print(f"  ✓ LinkedIn: {result.get('linkedin_post', {}).get('status', 'N/A')}")
    print(f"  ✓ Trace: {result.get('trace_path', 'N/A')}")
    print(f"  {'─' * 50}")


def run_repost():
    """Repost the last run to LinkedIn without regenerating anything.

    Uses stored data only — ZERO API calls to LLMs or image generators.

    Data sources (tried in order):
      1. last_run.json — preferred, has post text + PDF path + doc title
      2. post_log.json — fallback if last_run.json text is truncated
    """
    from pathlib import Path
    from aibrief import config

    last_run_path = config.BASE_DIR / "last_run.json"
    if not last_run_path.exists():
        print("  ✗ No last_run.json found. Run a full pipeline first.")
        return

    data = json.loads(last_run_path.read_text(encoding="utf-8"))
    pdf_path = data.get("pdf_path", "")
    post_text = data.get("post_text", "")
    doc_title = data.get("document_title", "")
    headline = data.get("story", {}).get("headline", "?")
    run_id = data.get("run_id", "?")
    prev_status = data.get("linkedin_status", "?")

    # ── Recovery: if post_text is truncated, pull from post_log.json ──
    if not post_text or post_text.endswith("\u2026"):
        print("  [REPOST] Post text missing or truncated — recovering from post_log.json...")
        log_path = config.BASE_DIR / "post_log.json"
        if log_path.exists():
            log = json.loads(log_path.read_text(encoding="utf-8"))
            for post in reversed(log.get("posts", [])):
                if post.get("tracer_id") == run_id:
                    full_text = post.get("post_text", "")
                    if full_text and len(full_text) > len(post_text or ""):
                        post_text = full_text
                        doc_title = doc_title or post.get("document_title", "")
                        print(f"  [REPOST] Recovered full post text ({len(post_text)} chars)")
                    break

    if not post_text:
        print("  ✗ No post text found in any stored data.")
        return
    if not pdf_path or not Path(pdf_path).exists():
        print(f"  ✗ PDF not found: {pdf_path}")
        return

    print(f"\n  [REPOST] Last run: {run_id}")
    print(f"  [REPOST] Topic: {headline}")
    print(f"  [REPOST] PDF: {Path(pdf_path).name}")
    print(f"  [REPOST] Document title: {doc_title}")
    print(f"  [REPOST] Post text: {len(post_text)} chars")
    print(f"  [REPOST] Previous status: {prev_status}")
    print(f"\n  [REPOST] Posting to LinkedIn (zero LLM/image API calls)...")

    from aibrief.pipeline.linkedin import post_brief
    story = data.get("story", {})
    result = post_brief(pdf_path, post_text, story=story,
                        document_title=doc_title)

    status = result.get("status", "?")
    url = result.get("url", "")
    print(f"\n  {'─' * 50}")
    print(f"  \u2713 Status: {status}")
    if url:
        print(f"  \u2713 URL: {url}")
    print(f"  \u2713 Mode: REPOST (zero regeneration, zero LLM calls)")
    print(f"  {'─' * 50}")


def main():
    print_banner()
    no_post = "--no-post" in sys.argv
    dry_run = "--dry-run" in sys.argv
    sim_mode = "--sim" in sys.argv
    repost_mode = "--repost" in sys.argv

    if repost_mode:
        run_repost()
    elif sim_mode:
        run_sim()
    else:
        run(no_post=no_post, dry_run=dry_run)


if __name__ == "__main__":
    main()
