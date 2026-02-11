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
  Phase 9:  Visuals → DALL-E + Pillow infographics
  Phase 10: PDF → luxury landscape slide deck
  Phase 11: Screen Audit → golden ratio page fill
  Phase 12: Final Validation → 37 master checkpoints
  Phase 13: LinkedIn → post with dynamic document title

Every phase TRACED with full input/output provenance.

Usage:
    python -m aibrief.main                # Full autonomous run
    python -m aibrief.main --no-post      # Generate PDF only, skip LinkedIn
    python -m aibrief.main --dry-run      # World Pulse + Content Strategy only
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
    ║              A I   B R I E F   v 3 . 0                  ║
    ║   Autonomous AI Thought Leadership Publisher            ║
    ║                                                         ║
    ║   POSTER + Agent Credits + Decision Architecture        ║
    ║   12 Styles • 10 Fonts • 10 Palettes (from catalog)    ║
    ║                                                         ║
    ║   13 Phases • 20+ Agents • Full Run Tracer             ║
    ║   Gemini Flash + GPT-4o + DALL-E 3 + Pillow            ║
    ╚═════════════════════════════════════════════════════════╝
    """)


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


def main():
    print_banner()
    no_post = "--no-post" in sys.argv
    dry_run = "--dry-run" in sys.argv
    run(no_post=no_post, dry_run=dry_run)


if __name__ == "__main__":
    main()
