"""AI Brief — AI Thought Leadership PDF + LinkedIn Publisher.

Scans for viral AI news, creates a multi-perspective analysis through
a team of AI agents who discuss and critique each other, generates a
high-end PDF brief, and posts to LinkedIn with proper formatting.

Usage:
    python -m aibrief.main              # Full pipeline: research → PDF → post
    python -m aibrief.main --no-post    # Generate PDF only, don't post
"""
import sys
import time
import json
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from aibrief import config
from aibrief.agents.orchestrator import Orchestrator
from aibrief.pipeline.pdf_gen import generate_pdf
from aibrief.pipeline.linkedin import post_brief


def print_banner():
    print("""
    ╔═══════════════════════════════════════════════╗
    ║          A I   B R I E F   v 1 . 0            ║
    ║   AI Thought Leadership • PDF + LinkedIn      ║
    ║                                               ║
    ║   Multi-Agent Discussion → High-End PDF       ║
    ║   Gemini Flash + GPT-4o • Unicode LinkedIn    ║
    ╚═══════════════════════════════════════════════╝
    """)


def run(no_post: bool = False):
    """Run the full pipeline."""
    t0 = time.time()

    # ── Phase 1-8: Multi-agent research + discussion ──
    orchestrator = Orchestrator()
    result = orchestrator.run()

    story = result["story"]
    brief = result["brief"]
    design = result["design"]
    li_post = result["linkedin_post"]

    # ── Phase 9: Generate PDF ──
    print("\n" + "=" * 60)
    print("  PHASE 9: GENERATE PDF")
    print("=" * 60)

    pdf_path = generate_pdf(brief, design, story)
    if not pdf_path:
        print("  ERROR: PDF generation failed!")
        return

    # ── Phase 10: Post to LinkedIn ──
    if no_post:
        print("\n  [--no-post] Skipping LinkedIn. PDF is ready.")
    else:
        print("\n" + "=" * 60)
        print("  PHASE 10: POST TO LINKEDIN")
        print("=" * 60)

        post_text = li_post.get("post_text", "")
        if not post_text:
            print("  ERROR: No LinkedIn post text!")
        else:
            li_result = post_brief(pdf_path, post_text)
            print(f"  Result: {li_result.get('status', '?')}")
            if li_result.get("url"):
                print(f"  URL: {li_result['url']}")

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE COMPLETE | {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Story: {story.get('headline', '?')}")
    print(f"  PDF: {pdf_path}")
    print(f"  Design: {design.get('design_name', '?')}")
    print(f"  Pages: {len(brief.get('pages', []))}")
    print(f"{'=' * 60}")


def main():
    print_banner()
    no_post = "--no-post" in sys.argv
    run(no_post=no_post)


if __name__ == "__main__":
    main()
