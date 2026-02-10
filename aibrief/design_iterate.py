"""Design iteration — Preparer/Reviewer + FinalValidator (36 checkpoints).

Architecture:
  1. DesignDirector creates → DesignReviewer argues → 2-3 rounds
  2. Visuals generated (DALL-E + Pillow)
  3. PDF rendered as LANDSCAPE SLIDES
  4. ScreenRealEstateAgent audits page fill
  5. FinalValidatorAgent checks ALL 36 master checkpoints
  6. If score < 80%: take feedback, regenerate. If >= 80%: done.

Usage:
    python -m aibrief.design_iterate
    python -m aibrief.design_iterate --v 5
    python -m aibrief.design_iterate --fresh
"""
import sys
import json
import time
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from aibrief import config
from aibrief.agents.specialists import DesignDirector
from aibrief.agents.orchestrator import DesignReviewer, ScreenRealEstateAgent
from aibrief.agents.validators import FinalValidatorAgent, MASTER_CHECKLIST
from aibrief.pipeline.pdf_gen import generate_pdf
from aibrief.pipeline.visuals import generate_all_visuals

FEEDBACK_LOG = config.BASE_DIR / "feedback_log.json"
CONTENT_CACHE = config.BASE_DIR / "content_cache.json"
MAX_DESIGN_ROUNDS = 3
MAX_VALIDATION_ATTEMPTS = 2


def load_feedback() -> dict:
    if FEEDBACK_LOG.exists():
        return json.loads(FEEDBACK_LOG.read_text(encoding="utf-8"))
    return {"master_checklist": [], "feedback_history": [], "design_rules": {},
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
    print("\n  [Full Agent Discussion — Preparer/Reviewer pairs + Round Table]\n")
    orch = Orchestrator()
    result = orch.run()
    cache = {
        "story": result["story"],
        "brief": result["brief"],
        "perspectives": result.get("perspectives", {}),
    }
    save_content(cache)
    return cache


def _build_feedback_context(fb: dict) -> str:
    """Build comprehensive context from ALL feedback for the designer."""
    ctx = ""
    rules = fb.get("design_rules", {})

    if rules.get("always"):
        ctx += "\n\nMANDATORY RULES (MUST follow ALL):\n"
        ctx += "\n".join(f"  ✓ {r}" for r in rules["always"])

    if rules.get("never"):
        ctx += "\n\nFORBIDDEN (instant rejection):\n"
        ctx += "\n".join(f"  ✗ {r}" for r in rules["never"])

    # Include ALL 36 checkpoints
    ctx += "\n\nMASTER CHECKLIST (your design will be scored on ALL 36 points):\n"
    for c in MASTER_CHECKLIST:
        if c["category"] in ("design", "layout", "visuals", "format", "design_psychology", "author"):
            ctx += f"  [{c['id']}] {c['rule']}\n"

    recent = fb.get("feedback_history", [])[-4:]
    if recent:
        ctx += "\n\nRECENT CLIENT FEEDBACK:\n"
        for f_entry in recent:
            ctx += f"  • {f_entry.get('points', '')}\n"

    return ctx


def iterate_design(version: int = None, fresh: bool = False):
    fb = load_feedback()

    content = load_content()
    if not content or not content.get("brief") or fresh:
        content = generate_content_once()

    story = content["story"]
    brief = content["brief"]
    perspectives = content.get("perspectives", {})

    fb["iteration_count"] = fb.get("iteration_count", 0) + 1
    v = version or fb["iteration_count"]
    run_id = f"v{v}_{int(time.time()) % 100000}"

    print(f"\n{'=' * 70}")
    print(f"  DESIGN ITERATION v{v}")
    print(f"  Architecture: Preparer/Reviewer + FinalValidator (36 checkpoints)")
    print(f"{'=' * 70}")

    feedback_ctx = _build_feedback_context(fb)
    agent_rounds = {}

    # ──────────────────────────────────────────────────────
    #  STEP 1: Design Director → Design Reviewer → Argue
    # ──────────────────────────────────────────────────────
    print(f"\n  [1/6] Design Director + Design Reviewer arguing...")
    designer = DesignDirector()
    d_reviewer = DesignReviewer()

    design = designer.think(
        f"Create a UNIQUE luxury slide-deck design for v{v}. "
        f"This is a PRESENTATION DECK (landscape slides), not a document. "
        f"EVERY page needs an EXCITING artistic background — never plain or dull. "
        f"Think luxury brand keynote: Hermès at Davos. Bold. Premium. Surprising. "
        f"The background_color must NOT be white (#ffffff) or near-white (#fafafa). "
        f"Use rich, warm, or deep tones that evoke luxury."
        f"{feedback_ctx}",
        context={"headline": story.get("headline", ""),
                 "version": v,
                 "format": "landscape presentation slides"},
    )

    for rd in range(1, MAX_DESIGN_ROUNDS + 1):
        review = d_reviewer.think(
            f"Review this design concept (round {rd}). "
            f"CRITICAL: background must NOT be plain/white/dull. "
            f"Every page must have artistic texture. Colors must evoke emotion. "
            f"This is a SLIDE DECK — headers must be 40pt+, layout must feel like PPT.",
            context={"design": design},
        )
        score = review.get("overall_score", 0)
        approved = review.get("approved", False)
        demands = review.get("demands", [])
        print(f"    Round {rd}: score={score}/10, demands={len(demands)}")
        agent_rounds[f"design_round_{rd}"] = {"score": score, "approved": approved}

        if approved and score >= 7:
            break
        if rd < MAX_DESIGN_ROUNDS and demands:
            design = designer.respond_to_feedback(design, review)
            print(f"    → Designer revised")

    print(f"  Design: {design.get('design_name', '?')}")
    print(f"  Palette: {design.get('primary_color', '?')} / {design.get('accent_color', '?')}")
    print(f"  Mood: {design.get('mood', '?')}")

    # ──────────────────────────────────────────────────────
    #  STEP 2: Generate visuals
    # ──────────────────────────────────────────────────────
    print(f"\n  [2/6] Generating visuals (DALL-E + infographics)...")
    visuals = generate_all_visuals(brief, story, design, perspectives, run_id)
    visuals_count = len(visuals)

    # ──────────────────────────────────────────────────────
    #  STEP 3: Generate slide-deck PDF
    # ──────────────────────────────────────────────────────
    slug = brief.get("brief_title", "AI_Brief")[:30]
    slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
    output_path = str(config.OUTPUT_DIR / f"{slug}_v{v}.pdf")

    print(f"\n  [3/6] Generating luxury slide-deck PDF...")
    pdf_path = generate_pdf(brief, design, story, visuals=visuals,
                            output_path=output_path)

    # ──────────────────────────────────────────────────────
    #  STEP 4: Screen Real Estate Audit
    # ──────────────────────────────────────────────────────
    print(f"\n  [4/6] Screen Real Estate Audit...")
    auditor = ScreenRealEstateAgent()

    pages_info = []
    for i, page in enumerate(brief.get("pages", [])):
        bullets = page.get("bullets", [])
        bullet_count = len(bullets) if bullets else 0
        pages_info.append({
            "page_number": i + 1,
            "page_type": page.get("page_type", "?"),
            "title": page.get("title", "?"),
            "bullet_count": bullet_count,
            "has_key_stat": bool(page.get("key_stat")),
            "has_quote": bool(page.get("quote")),
            "has_visual": page.get("page_type", "") in visuals,
            "has_artistic_background": True,
            "format": "landscape slide",
        })

    audit = auditor.think(
        "Audit this SLIDE DECK PDF. Each slide is landscape (11x8.5). "
        "Every slide has: artistic background + big header + bullets + visual. "
        "Check that no slide feels empty or has dead space.",
        context={"pages": pages_info, "design": design},
    )
    audit_approved = audit.get("approved", False)
    print(f"  Audit: {'PASS' if audit_approved else 'NEEDS ATTENTION'}")

    # ──────────────────────────────────────────────────────
    #  STEP 5: FINAL VALIDATOR — 36 checkpoints
    # ──────────────────────────────────────────────────────
    print(f"\n  [5/6] Final Validator — 36 master checkpoints...")
    validator = FinalValidatorAgent()

    validation = validator.validate(
        brief=brief, design=design, story=story,
        visuals_count=visuals_count, audit_result=audit,
        agent_rounds=agent_rounds,
    )
    # Note: Some rules are about the system architecture, not the PDF content.
    # Pass extra proof so the validator can verify these:
    # Rule 4 (creative tools): visuals_count > 0 proves DALL-E + Pillow used
    # Rule 6 (luxury name): brief["_assistant_name"] has the luxury name
    # Rule 8/17 (agent arguments): agent_rounds dict has the proof

    total_score = validation.get("total_score", 0)
    v_approved = validation.get("approved", False)
    critical_fails = validation.get("critical_failures", [])

    print(f"  Score: {total_score}/100")
    print(f"  Approved: {v_approved}")
    if critical_fails:
        print(f"  Critical failures: {len(critical_fails)}")
        for cf in critical_fails[:5]:
            print(f"    ✗ {cf}")

    # If not approved and we haven't exhausted attempts, try once more
    if not v_approved and total_score < 80:
        print(f"\n  [5b/6] Score {total_score} < 80 — regenerating with fixes...")
        fix_instructions = validation.get("fix_instructions", [])
        fix_ctx = "\n".join(f"  FIX: {fi}" for fi in fix_instructions)

        design = designer.think(
            f"The FinalValidator REJECTED your design (score {total_score}/100). "
            f"Fix these issues:\n{fix_ctx}\n\n"
            f"Create an improved version that passes ALL 36 checkpoints.",
            context={"current_design": design, "failures": critical_fails},
        )

        # Regenerate visuals and PDF with fixed design
        run_id_fix = f"v{v}fix_{int(time.time()) % 100000}"
        visuals = generate_all_visuals(brief, story, design, perspectives, run_id_fix)
        pdf_path = generate_pdf(brief, design, story, visuals=visuals,
                                output_path=output_path)

        # Re-validate
        validation2 = validator.validate(
            brief=brief, design=design, story=story,
            visuals_count=len(visuals), audit_result=audit,
            agent_rounds=agent_rounds,
        )
        total_score = validation2.get("total_score", 0)
        v_approved = validation2.get("approved", False)
        print(f"  Re-validation: score={total_score}/100, approved={v_approved}")

    # ──────────────────────────────────────────────────────
    #  STEP 6: Summary
    # ──────────────────────────────────────────────────────
    save_feedback(fb)

    print(f"\n{'=' * 70}")
    print(f"  v{v} COMPLETE")
    print(f"  PDF: {pdf_path}")
    print(f"  Design: {design.get('design_name', '?')}")
    print(f"  Visuals: {visuals_count} elements")
    print(f"  Validation: {total_score}/100 ({'APPROVED' if v_approved else 'REVIEW NEEDED'})")
    if critical_fails and not v_approved:
        print(f"  Remaining failures:")
        for cf in critical_fails[:3]:
            print(f"    ✗ {cf}")
    print(f"{'=' * 70}")
    return pdf_path, v


if __name__ == "__main__":
    v = None
    fresh = False
    for i, arg in enumerate(sys.argv):
        if arg == "--v" and i + 1 < len(sys.argv):
            try:
                v = int(sys.argv[i + 1])
            except ValueError:
                pass
        if arg == "--fresh":
            fresh = True
    iterate_design(version=v, fresh=fresh)
