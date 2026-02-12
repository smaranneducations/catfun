"""Run data storage — writes structured debate and run data for meta-analysis.

Two outputs per run:
  1. data/debates/{run_id}.json — Full debate conversations (chat-style)
  2. data/runs_index.json — Append one row to the cross-run index

The debates file stores the FULL text of every exchange:
  - Preparer's submission (key arguments, perspective title, pull quote)
  - Reviewer's feedback (score, verdict, demands with full text, strengths)
  - Preparer's revision (what changed, new arguments)
  - Final outcome

The runs index is a lightweight table for quick analytics.
"""
import json
from pathlib import Path
from datetime import datetime

from aibrief import config

DATA_DIR = config.BASE_DIR / "data"
DEBATES_DIR = DATA_DIR / "debates"
VALIDATIONS_DIR = DATA_DIR / "validations"
INDEX_PATH = DATA_DIR / "runs_index.json"

for _d in [DEBATES_DIR, VALIDATIONS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
#  DEBATE CONVERSATION STORAGE
# ═══════════════════════════════════════════════════════════════

def _extract_preparer_summary(work: dict) -> dict:
    """Extract the most meaningful fields from a preparer's output.

    Different analyst types return different keys, so we capture
    the common ones and a general 'key_arguments' summary.
    """
    if not work or not isinstance(work, dict):
        return {"raw": str(work)[:500]}

    summary = {}

    # Common across all analysts
    for key in ["perspective_title", "brief_title", "headline"]:
        if work.get(key):
            summary["title"] = str(work[key])[:200]
            break

    # Pull quote / key insight
    for key in ["pull_quote", "key_quote", "market_signal"]:
        if work.get(key):
            summary["key_insight"] = str(work[key])[:300]
            break

    # Confidence
    if work.get("confidence"):
        summary["confidence"] = work["confidence"]

    # Key arguments (varies by analyst type)
    args = []
    for key in ["economic_impact", "historical_context", "social_impact",
                "future_scenario", "winners", "losers", "implications",
                "hero_statement", "supporting_line", "summary_points",
                "cultural_impact", "policy_recommendations"]:
        val = work.get(key)
        if val:
            if isinstance(val, list):
                args.extend([str(v)[:150] for v in val[:4]])
            else:
                args.append(str(val)[:300])
    if args:
        summary["key_arguments"] = args[:5]

    # For content briefs, capture page titles
    pages = work.get("pages", [])
    if pages:
        summary["page_titles"] = [
            p.get("page_title", p.get("page_type", "?"))[:80]
            for p in pages[:6]
        ]

    return summary


def _extract_reviewer_feedback(review: dict) -> dict:
    """Extract structured reviewer feedback."""
    if not review or not isinstance(review, dict):
        return {"raw": str(review)[:500]}

    return {
        "score": review.get("overall_score", 0),
        "approved": review.get("approved", False),
        "verdict": str(review.get("verdict",
                       review.get("summary", "")))[:500],
        "demands": [str(d)[:300] for d in review.get("demands", [])[:6]],
        "strengths": [str(s)[:200] for s in review.get("strengths", [])[:4]],
        "weaknesses": [str(w)[:200] for w in review.get("weaknesses", [])[:4]],
    }


def store_debate(run_id: str, debate: dict):
    """Append a debate to the run's debates file.

    Called from orchestrator._argue() after each debate completes.

    Args:
        run_id: The run identifier (e.g., 'run_20260212_102911')
        debate: Structured debate dict with full conversation
    """
    path = DEBATES_DIR / f"{run_id}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"run_id": run_id, "debates": []}

    data["debates"].append(debate)

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ═══════════════════════════════════════════════════════════════
#  VALIDATION STORAGE
# ═══════════════════════════════════════════════════════════════

def store_validation(run_id: str, pre_val: dict, post_val: dict,
                     combined_score: float):
    """Store validation results for a run."""
    path = VALIDATIONS_DIR / f"{run_id}.json"
    data = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "combined_score": combined_score,
        "pre_visual": {
            "score": pre_val.get("total_score", 0),
            "approved": pre_val.get("approved", False),
            "explanation": pre_val.get("explanation", ""),
            "critical_failures": pre_val.get("critical_failures", []),
            "rules_checked": pre_val.get("rules_checked", []),
        },
        "post_visual": {
            "score": post_val.get("total_score", 0),
            "approved": post_val.get("approved", False),
            "explanation": post_val.get("explanation", ""),
            "critical_failures": post_val.get("critical_failures", []),
            "rules_checked": post_val.get("rules_checked", []),
        },
    }
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════
#  RUNS INDEX (cross-run analytics)
# ═══════════════════════════════════════════════════════════════

def index_run(run_id: str, *, topic: str, news_url: str = "",
              publisher: str = "", content_type: str = "",
              emotion: str = "", style_id: str = "",
              palette_id: str = "", design_name: str = "",
              pre_visual_score: float = 0, post_visual_score: float = 0,
              combined_score: float = 0, discussion_score: float = 0,
              posted: bool = False, post_url: str = "",
              total_debates: int = 0, total_rounds: int = 0,
              total_agents: int = 0, duration_seconds: float = 0,
              pdf_path: str = "", world_mood: str = ""):
    """Append a run summary to the cross-run index.

    This is the main table for meta-analysis — one row per run,
    lightweight and fast to load for analytics.
    """
    if INDEX_PATH.exists():
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    else:
        index = {"runs": [], "schema_version": 1}

    # Don't duplicate
    existing_ids = {r["run_id"] for r in index["runs"]}
    if run_id in existing_ids:
        return

    index["runs"].append({
        "run_id": run_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topic": topic[:200],
        "news_url": news_url,
        "publisher": publisher,
        "content_type": content_type,
        "emotion": emotion,
        "style_id": style_id,
        "palette_id": palette_id,
        "design_name": design_name,
        "world_mood": world_mood,
        "pre_visual_score": pre_visual_score,
        "post_visual_score": post_visual_score,
        "combined_score": combined_score,
        "discussion_score": discussion_score,
        "posted": posted,
        "post_url": post_url,
        "total_debates": total_debates,
        "total_rounds": total_rounds,
        "total_agents": total_agents,
        "duration_seconds": round(duration_seconds, 1),
        "pdf_path": pdf_path,
    })

    INDEX_PATH.write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
