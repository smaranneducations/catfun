"""Design iteration mode — same content, new design + visuals each time.

Generates DALL-E images, Pillow infographics, and a luxury PDF.
Reads feedback_log.json and applies ALL feedback to every iteration.

Usage:
    python -m aibrief.design_iterate
"""
import sys
import json
import time
import random
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from aibrief import config
from aibrief.agents.specialists import DesignDirector
from aibrief.pipeline.pdf_gen import generate_pdf
from aibrief.pipeline.visuals import generate_all_visuals

FEEDBACK_LOG = config.BASE_DIR / "feedback_log.json"
CONTENT_CACHE = config.BASE_DIR / "content_cache.json"


def load_feedback() -> dict:
    if FEEDBACK_LOG.exists():
        return json.loads(FEEDBACK_LOG.read_text(encoding="utf-8"))
    return {"feedback_history": [], "design_rules": {"always": [], "never": [], "preferences": []},
            "iteration_count": 0}


def save_feedback(data: dict):
    data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    FEEDBACK_LOG.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_content() -> dict:
    if CONTENT_CACHE.exists():
        return json.loads(CONTENT_CACHE.read_text(encoding="utf-8"))
    return {}


def save_content(data: dict):
    CONTENT_CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_content_once():
    from aibrief.agents.orchestrator import Orchestrator
    print("\n  [First run] Generating content with full agent discussion...\n")
    orch = Orchestrator()
    result = orch.run()
    cache = {
        "story": result["story"],
        "brief": result["brief"],
        "perspectives": result["perspectives"],
    }
    save_content(cache)
    return cache


def iterate_design(version: int = None):
    fb = load_feedback()

    content = load_content()
    if not content or not content.get("brief"):
        content = generate_content_once()

    story = content["story"]
    brief = content["brief"]
    perspectives = content.get("perspectives", {})

    fb["iteration_count"] += 1
    v = version or fb["iteration_count"]
    run_id = f"v{v}_{int(time.time()) % 100000}"

    print(f"\n{'=' * 60}")
    print(f"  DESIGN ITERATION v{v}")
    print(f"{'=' * 60}")

    # Build feedback context for the designer
    rules = fb.get("design_rules", {})
    feedback_ctx = ""
    if rules.get("always"):
        feedback_ctx += "\n\nMANDATORY RULES (must follow):\n"
        feedback_ctx += "\n".join(f"  - {r}" for r in rules["always"])
    if rules.get("never"):
        feedback_ctx += "\n\nNEVER DO:\n"
        feedback_ctx += "\n".join(f"  - {r}" for r in rules["never"])
    if rules.get("preferences"):
        feedback_ctx += "\n\nCLIENT PREFERENCES:\n"
        feedback_ctx += "\n".join(f"  - {r}" for r in rules["preferences"])

    recent = fb.get("feedback_history", [])[-5:]
    if recent:
        feedback_ctx += "\n\nRECENT FEEDBACK (address ALL):\n"
        feedback_ctx += "\n".join(f"  - {f['feedback']}" for f in recent)

    # Get design from Design Director
    print("\n  [1] Design Director creating visual concept...")
    designer = DesignDirector()
    design = designer.think(
        f"Create a COMPLETELY UNIQUE luxury design for v{v}. "
        f"This must look like it came from a luxury brand creative director — "
        f"think Hermès, Chanel, Louis Vuitton editorial. Premium, bold, "
        f"balanced. NEVER repeat a previous design. Surprise the client.{feedback_ctx}",
        context={"headline": story.get("headline", ""),
                 "version": v},
    )
    print(f"  Design: {design.get('design_name', '?')}")
    print(f"  Palette: {design.get('primary_color', '?')} + {design.get('accent_color', '?')}")
    print(f"  Mood: {design.get('mood', '?')}")
    print(f"  Motif: {design.get('visual_motif', '?')}")

    # Generate visuals (DALL-E + Pillow infographics)
    print("\n  [2] Generating visuals (DALL-E + infographics)...")
    visuals = generate_all_visuals(brief, story, design, perspectives, run_id)

    # Generate PDF
    import re
    slug = brief.get("brief_title", "AI_Brief")[:30]
    slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
    output_path = str(config.OUTPUT_DIR / f"{slug}_v{v}.pdf")

    print("\n  [3] Generating luxury PDF...")
    pdf_path = generate_pdf(brief, design, story, visuals=visuals,
                            output_path=output_path)

    save_feedback(fb)

    print(f"\n{'=' * 60}")
    print(f"  v{v} COMPLETE")
    print(f"  PDF: {pdf_path}")
    print(f"  Design: {design.get('design_name', '?')}")
    print(f"  Visuals: {len(visuals)} elements")
    print(f"  Open the PDF and give feedback.")
    print(f"{'=' * 60}")
    return pdf_path, v


if __name__ == "__main__":
    v = None
    for i, arg in enumerate(sys.argv):
        if arg == "--v" and i + 1 < len(sys.argv):
            try:
                v = int(sys.argv[i + 1])
            except ValueError:
                pass
    iterate_design(version=v)
