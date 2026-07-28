"""FastAPI wrapper for AI Brief pipeline — stage-by-stage execution.

User provides a URL → pipeline extracts content → runs analysis → generates PDF.
No more autonomous news discovery. User-driven workflow.

Features:
  - URL-based caching: reuse previous results for the same URL
  - Full debate conversations returned (every round, every turn)
  - Rich data from ALL stages (not summaries)
  - User comment injection with 5x weight

Usage:
    python -m aibrief.api          # Starts on port 8900
    python -m aibrief.api --port 9000
"""

import sys
import os
import json
import time
import uuid
import traceback
import re
from pathlib import Path
from typing import Optional

# Fix Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from aibrief import config

app = FastAPI(
    title="AI Brief Pipeline API",
    description="Stage-by-stage multi-agent content pipeline — user provides URL",
    version="3.0.0",
)

# ═══════════════════════════════════════════════════════════════
#  URL CACHE — check runs_index.json for previously processed URLs
# ═══════════════════════════════════════════════════════════════

CACHE_DIR = config.BASE_DIR / "data"
INDEX_PATH = CACHE_DIR / "runs_index.json"
DEBATES_DIR = CACHE_DIR / "debates"
TRACES_DIR = config.BASE_DIR / "traces"
VALIDATIONS_DIR = CACHE_DIR / "validations"


def _find_cached_run(url: str) -> Optional[dict]:
    """Check if this URL was previously processed. Returns the run index entry or None."""
    if not url or not INDEX_PATH.exists():
        return None
    try:
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        for run in reversed(index.get("runs", [])):
            if run.get("news_url") == url:
                return run
        return None
    except Exception:
        return None


def _load_cached_debates(run_id: str) -> Optional[dict]:
    """Load full debate conversations from a previous run."""
    path = DEBATES_DIR / f"{run_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _load_cached_trace(run_id: str) -> Optional[dict]:
    """Load the full trace from a previous run."""
    path = TRACES_DIR / f"{run_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _load_cached_validations(run_id: str) -> Optional[dict]:
    """Load validation results from a previous run."""
    path = VALIDATIONS_DIR / f"{run_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


# ═══════════════════════════════════════════════════════════════
#  SESSION STORE (in-memory; SQLite is on the Discord side)
# ═══════════════════════════════════════════════════════════════

class PipelineSession:
    """Holds a live orchestrator + accumulated state for one pipeline run."""

    def __init__(self, source_url: str, source_text: str, pages: int):
        from aibrief.agents.orchestrator import AutonomousOrchestrator

        self.session_id = str(uuid.uuid4())[:8]
        self.source_url = source_url
        self.source_text = source_text
        self.pages = pages
        self.status = "created"
        self.current_stage = ""
        self.stages_completed: list[str] = []
        self.stage_results: dict[str, dict] = {}
        self.user_comments: dict[str, list[str]] = {}
        self.created_at = time.time()

        # Create orchestrator (loads config, instantiates all agents)
        self.orch = AutonomousOrchestrator()

        # Intermediate state passed between stages
        self.extracted_content: dict = {}
        self.pulse: dict = {}
        self.strategy: dict = {}
        self.story: dict = {}
        self.design: dict = {}
        self.perspectives: dict = {}
        self.brief: dict = {}
        self.discussion: dict = {}
        self.pre_val: dict = {}
        self.visuals: dict = {}
        self.audit: dict = {}
        self.post_val: dict = {}
        self.pdf_path: str = ""
        self.elapsed: float = 0

        # Cache info
        self.cached_run_id: Optional[str] = None
        self.cached_debates: Optional[dict] = None
        self.cached_trace: Optional[dict] = None

        # Check URL cache
        if source_url:
            cached = _find_cached_run(source_url)
            if cached:
                self.cached_run_id = cached.get("run_id")
                self.cached_debates = _load_cached_debates(self.cached_run_id)
                self.cached_trace = _load_cached_trace(self.cached_run_id)
                print(f"  [CACHE] Found previous run {self.cached_run_id} for this URL")
                if self.cached_debates:
                    print(f"  [CACHE] Loaded {len(self.cached_debates.get('debates', []))} cached debates")


SESSIONS: dict[str, PipelineSession] = {}


# ═══════════════════════════════════════════════════════════════
#  REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class CreateSessionRequest(BaseModel):
    source_url: str = ""
    source_text: str = ""
    pages: int = 4

class RunStageRequest(BaseModel):
    user_comments: list[str] = []

class PublishLinkedInRequest(BaseModel):
    post_text: str = ""
    document_title: str = ""
    pdf_path: str = ""
    story: dict = {}

class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    current_stage: str
    stages_completed: list[str]
    cached_run_id: Optional[str] = None

class StageResultResponse(BaseModel):
    stage_id: str
    status: str
    result: dict
    duration_seconds: float
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
#  CONTENT EXTRACTION — fetch URL, extract text
# ═══════════════════════════════════════════════════════════════

def _extract_content_from_url(url: str) -> dict:
    """Fetch a URL and extract article content. Returns a story-like dict."""
    import requests

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # Basic extraction — title from <title> tag
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "Untitled"
        title = re.sub(r"\s*[\|–—-]\s*.*$", "", title)  # Remove "| Site Name"

        # Extract meta description
        desc_match = re.search(
            r'<meta\s+(?:name|property)=["\'](?:description|og:description)["\']\s+content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        )
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract publisher from og:site_name
        pub_match = re.search(
            r'<meta\s+property=["\']og:site_name["\']\s+content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        )
        publisher = pub_match.group(1).strip() if pub_match else _domain_to_publisher(url)

        # Strip HTML tags for body text
        from html import unescape
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()

        # Take first ~3000 chars of body as article content
        article_text = text[:3000]

        return {
            "headline": title,
            "exact_news_headline": title,
            "news_url": url,
            "publisher": publisher,
            "description": description,
            "article_text": article_text,
            "content_length": len(text),
        }
    except Exception as e:
        return {
            "headline": f"Article from {_domain_to_publisher(url)}",
            "news_url": url,
            "publisher": _domain_to_publisher(url),
            "description": "",
            "article_text": "",
            "error": str(e),
        }


def _domain_to_publisher(url: str) -> str:
    """Extract a readable publisher name from URL domain."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        domain = domain.replace("www.", "").replace("edition.", "")
        parts = domain.split(".")
        return parts[0].title() if parts else "Unknown"
    except (ValueError, IndexError, AttributeError):
        return "Unknown"


# ═══════════════════════════════════════════════════════════════
#  USER COMMENT INJECTION
# ═══════════════════════════════════════════════════════════════

def _build_user_directive(comments: list[str]) -> str:
    """Build a high-priority user directive string from comments."""
    if not comments:
        return ""
    lines = []
    for c in comments:
        lines.append(f"[USER DIRECTIVE — HIGHEST PRIORITY — 5× WEIGHT]: {c}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  STAGE RUNNERS — each returns RICH, detailed data
# ═══════════════════════════════════════════════════════════════

def run_stage_content_extraction(session: PipelineSession, comments: list[str]) -> dict:
    """First stage: fetch the URL the user provided and extract content."""
    url = session.source_url
    if url:
        extracted = _extract_content_from_url(url)
    else:
        text = session.source_text
        extracted = {
            "headline": text[:80].strip(),
            "news_url": "",
            "publisher": "User Input",
            "description": text[:200],
            "article_text": text[:3000],
            "content_length": len(text),
        }

    session.extracted_content = extracted
    session.story = extracted

    # Build a synthetic pulse and strategy (replacing the removed stages)
    session.pulse = {
        "mood": "neutral",
        "sentiment_score": 5,
        "tone": "analytical",
        "top_events": [extracted.get("headline", "User-provided article")],
    }
    session.strategy = {
        "content_type": "Deep Analysis",
        "page_count": session.pages,
        "tone": "premium-analytical",
        "topic_direction": extracted.get("headline", ""),
    }

    return {
        "headline": extracted.get("headline", "?"),
        "publisher": extracted.get("publisher", "?"),
        "url": extracted.get("news_url", ""),
        "description": extracted.get("description", "")[:500],
        "article_text_preview": extracted.get("article_text", "")[:500],
        "content_length": extracted.get("content_length", 0),
        "status": "extracted" if not extracted.get("error") else "partial",
        "cached_run_id": session.cached_run_id,
    }


def run_stage_design_dna(session: PipelineSession, comments: list[str]) -> dict:
    session.design = session.orch._phase_design_dna(
        session.pulse, session.strategy, session.story)
    return {
        "emotion": session.design.get("emotion", "?"),
        "emotion_reasoning": session.design.get("emotion_reasoning", ""),
        "style_id": session.design.get("style_id", "?"),
        "design_name": session.design.get("design_name", "?"),
        "palette_id": session.design.get("palette_id", "?"),
        "font_id": session.design.get("font_id", "?"),
        "imagen_style": session.design.get("imagen_style", "?"),
        "mood": session.design.get("mood", ""),
        "primary_color": session.design.get("primary_color", ""),
        "secondary_color": session.design.get("secondary_color", ""),
        "accent_color": session.design.get("accent_color", ""),
        "visual_motif": session.design.get("visual_motif", ""),
    }


def run_stage_analyst_pairs(session: PipelineSession, comments: list[str]) -> dict:
    """Run analyst debates — returns FULL conversation data for every round."""
    session.perspectives = session.orch._phase_analyst_pairs(
        session.story, session.strategy)

    # ── Build perspective summaries from final analyst work ──
    debates_summary = {}
    for key, data in session.perspectives.items():
        if isinstance(data, dict):
            debates_summary[key] = {
                "perspective_title": data.get("perspective_title", data.get("title", key)),
                "pull_quote": data.get("pull_quote", data.get("key_quote", "")),
                "confidence": data.get("confidence", 0),
                "key_arguments": _extract_key_arguments(data),
            }

    # ── Get FULL debate conversations from tracer (every round, every turn) ──
    debate_entries = [e for e in session.orch.tracer.entries if e.get("phase") == "DEBATE"
                      and "RoundTable" not in e.get("pair", "")]
    full_debates = []
    for d in debate_entries:
        rounds = d.get("rounds", [])
        debate_data = {
            "label": d.get("label", "?"),
            "preparer_name": d.get("preparer_name", "?"),
            "reviewer_name": d.get("reviewer_name", "?"),
            "total_rounds": len(rounds),
            "final_score": rounds[-1].get("score", 0) if rounds else 0,
            "final_approved": rounds[-1].get("approved", False) if rounds else False,
            "rounds": [],
        }
        for r in rounds:
            round_detail = {
                "round": r.get("round", 0),
                "score": r.get("score", 0),
                "approved": r.get("approved", False),
                "demands_count": r.get("demands_count", 0),
                # Full preparer submission
                "preparer_submission": r.get("preparer_submission", {}),
                # Full reviewer feedback
                "reviewer_feedback": r.get("reviewer_feedback", {}),
                # Demands as explicit list
                "demands": r.get("demands", []),
                # Reviewer verdict
                "verdict": r.get("verdict", ""),
                # What the preparer revised (if applicable)
                "preparer_revision": r.get("preparer_revision", None),
            }
            debate_data["rounds"].append(round_detail)
        full_debates.append(debate_data)

    return {
        "perspectives": debates_summary,
        "full_debates": full_debates,
        "analyst_count": len(session.perspectives),
        "total_debate_rounds": sum(d["total_rounds"] for d in full_debates),
    }


def _extract_key_arguments(data: dict) -> list[str]:
    """Extract key arguments from any analyst type's output."""
    args = []
    for key in ["economic_impact", "historical_parallels", "social_impact",
                "prediction_6mo", "prediction_2yr", "prediction_5yr",
                "winners", "losers", "who_is_affected", "opportunity",
                "risk", "wildcard", "market_signal"]:
        val = data.get(key)
        if val:
            if isinstance(val, list):
                for item in val[:3]:
                    if isinstance(item, dict):
                        args.append(str(item.get("connection", item.get("event", str(item))))[:200])
                    else:
                        args.append(str(item)[:200])
            else:
                args.append(f"{key}: {str(val)[:200]}")
    return args[:6]


def run_stage_round_table(session: PipelineSession, comments: list[str]) -> dict:
    session.perspectives = session.orch._phase_round_table(
        session.story, session.perspectives)

    # Extract challenge details from tracer
    challenge_entries = [
        e for e in session.orch.tracer.entries
        if e.get("phase") == "DEBATE" and "RoundTable" in e.get("pair", "")
    ]

    challenges = []
    if challenge_entries:
        for entry in challenge_entries:
            for r in entry.get("rounds", []):
                raw_summary = r.get("summary", "")
                if isinstance(raw_summary, dict):
                    raw_summary = raw_summary.get("rebuttal", raw_summary.get(
                        "challenge", raw_summary.get("main_point",
                        raw_summary.get("perspective_title", str(raw_summary)))))
                raw_impact = r.get("impact", "")
                if isinstance(raw_impact, dict):
                    raw_impact = raw_impact.get("impact", raw_impact.get(
                        "conclusion", str(raw_impact)))
                challenges.append({
                    "pair": str(r.get("pair", "?")),
                    "summary": str(raw_summary)[:400],
                    "impact": str(raw_impact)[:300],
                })

    return {
        "status": "complete",
        "perspectives_updated": len(session.perspectives),
        "cross_challenges": len(challenges),
        "challenge_highlights": challenges,
        "perspectives_after": {
            key: {
                "perspective_title": data.get("perspective_title", key) if isinstance(data, dict) else key,
                "confidence": data.get("confidence", 0) if isinstance(data, dict) else 0,
            }
            for key, data in session.perspectives.items()
        },
    }


def run_stage_editorial(session: PipelineSession, comments: list[str]) -> dict:
    # Capture the editorial review result
    session.orch.tracer.begin_phase(
        phase="Editorial",
        agent_name="EditorInChief",
        agent_codename="Paramount",
        model=config.MODEL_EDITOR_IN_CHIEF,
        fixed_inputs={"core_instruction": "Review all perspectives"},
        variable_inputs={},
    )

    review = session.orch.editor.review_perspectives(
        session.story, session.perspectives)
    session.orch.tracer.end_phase(review)

    score = review.get("quality_score", "?")
    feedback = review.get("feedback_per_agent", {})

    # Build detailed feedback per agent — NO truncation, send full data
    detailed_feedback = {}
    if isinstance(feedback, dict):
        for agent_name, fb in feedback.items():
            if isinstance(fb, dict):
                detailed_feedback[agent_name] = {
                    "score": fb.get("score", "?"),
                    "strengths": fb.get("strengths", []),
                    "improvements": fb.get("improve", fb.get("improvements", [])),
                    "feedback": str(fb.get("feedback", fb.get("note", ""))),
                    "verdict": str(fb.get("verdict", "")),
                }
            else:
                detailed_feedback[agent_name] = {"feedback": str(fb)}

    if not review.get("ready_for_synthesis", False):
        agent_map = {
            "Historian": ("historical", session.orch.historian),
            "Economist": ("economic", session.orch.economist),
            "Sociologist": ("social", session.orch.sociologist),
            "Futurist": ("future", session.orch.futurist),
        }
        revisions = []
        for agent_name, (key, agent) in agent_map.items():
            agent_fb = feedback.get(agent_name, {})
            if agent_fb and agent_fb.get("score", 10) < 8:
                session.perspectives[key] = agent.respond_to_feedback(
                    session.perspectives[key], agent_fb)
                revisions.append(agent_name)

        return {
            "quality_score": score,
            "ready_for_synthesis": False,
            "revisions_requested": revisions,
            "feedback_per_agent": detailed_feedback,
            "overall_assessment": str(review.get("overall_assessment", "")),
            "missing_angles": review.get("missing_angles", []),
            "verdict": str(review.get("verdict", review.get("overall_verdict", ""))),
        }

    return {
        "quality_score": score,
        "ready_for_synthesis": True,
        "feedback_per_agent": detailed_feedback,
        "overall_assessment": str(review.get("overall_assessment", "")),
        "missing_angles": review.get("missing_angles", []),
        "verdict": str(review.get("overall_verdict", review.get("summary", "Approved"))),
    }


def run_stage_content_synthesis(session: PipelineSession, comments: list[str]) -> dict:
    session.brief = session.orch._phase_synthesis(
        session.story, session.perspectives, session.strategy, session.design)

    pages = session.brief.get("pages", [])
    detailed_pages = []
    for p in pages:
        page_info = {
            "page_type": p.get("page_type", "?"),
            "page_title": p.get("page_title", ""),
            "hero_statement": str(p.get("hero_statement", "")),
            "supporting_line": str(p.get("supporting_line", "")),
            "visual_mood": p.get("visual_mood", ""),
        }
        # Include points if available
        points = p.get("points", [])
        if points:
            page_info["points"] = [
                {
                    "point": pt.get("point", "") if isinstance(pt, dict) else str(pt),
                    "detail": pt.get("detail", "") if isinstance(pt, dict) else "",
                }
                for pt in points[:6]
            ]
            page_info["points_count"] = len(points)
        # Include summary_points for news summary pages
        if p.get("summary_points"):
            page_info["summary_points"] = p["summary_points"][:8]
        # Include quote data
        if p.get("quote"):
            page_info["quote"] = p["quote"]
            page_info["attribution"] = p.get("attribution", "")
        # Include stat data
        if p.get("hero_number"):
            page_info["hero_number"] = p["hero_number"]
            page_info["hero_label"] = p.get("hero_label", "")

        detailed_pages.append(page_info)

    return {
        "brief_title": session.brief.get("brief_title", "?"),
        "subtitle": session.brief.get("subtitle", ""),
        "pages": detailed_pages,
        "page_count": len(pages),
    }


def run_stage_neutrality_check(session: PipelineSession, comments: list[str]) -> dict:
    session.brief = session.orch._phase_neutrality(
        session.brief, session.story, session.perspectives)

    # Get the neutrality review from tracer
    neutrality_entry = None
    for e in reversed(session.orch.tracer.entries):
        if e.get("phase") == "NeutralityCheck":
            neutrality_entry = e.get("output", {})
            break

    if neutrality_entry:
        issues = neutrality_entry.get("issues", [])
        return {
            "approved": neutrality_entry.get("approved", True),
            "tone_score": neutrality_entry.get("tone_score",
                          neutrality_entry.get("overall_score", "?")),
            "bias_detected": bool(issues),
            "issues": [
                {
                    "page_type": str(iss.get("page_type", "?"))[:50],
                    "issue": str(iss.get("issue", ""))[:300],
                    "severity": str(iss.get("severity", ""))[:50],
                    "fix": str(iss.get("fix", ""))[:200],
                }
                for iss in (issues if isinstance(issues, list) else [])[:6]
            ],
            "strengths": neutrality_entry.get("strengths", []),
            "verdict": str(neutrality_entry.get("verdict",
                          neutrality_entry.get("summary", "Passed")))[:500],
            "revision_required": neutrality_entry.get("revision_required", False),
        }

    return {
        "approved": True,
        "tone_score": "?",
        "verdict": "Neutrality check completed",
        "issues": [],
        "strengths": [],
    }


def run_stage_discussion_potential(session: PipelineSession, comments: list[str]) -> dict:
    session.discussion = session.orch._phase_discussion_potential(
        session.story, session.brief)
    return {
        "engagement_score": session.discussion.get("engagement_score", 0),
        "verdict": session.discussion.get("verdict", "?"),
        "discussion_hooks": session.discussion.get("discussion_hooks", [])[:5],
        "controversy_score": session.discussion.get("controversy_score", 0),
        "relevance_score": session.discussion.get("relevance_score", 0),
        "shareability_score": session.discussion.get("shareability_score", 0),
        "suggested_angle": str(session.discussion.get("suggested_angle", ""))[:300],
        "reasoning": str(session.discussion.get("reasoning",
                        session.discussion.get("explanation", "")))[:800],
    }


def run_stage_pre_validation(session: PipelineSession, comments: list[str]) -> dict:
    session.pre_val = session.orch._phase_pre_validation(
        session.brief, session.design, session.story)

    rules = session.pre_val.get("rules_checked", [])
    return {
        "total_score": session.pre_val.get("total_score", 0),
        "approved": session.pre_val.get("approved", False),
        "explanation": str(session.pre_val.get("explanation", "")),
        "critical_failures": session.pre_val.get("critical_failures", []),
        "fix_instructions": session.pre_val.get("fix_instructions", []),
        "verdict": str(session.pre_val.get("verdict", "")),
        "rules_checked": [
            {
                "id": r.get("id", "?"),
                "passed": r.get("passed", False),
                "reasoning": str(r.get("reasoning", "")),
            }
            for r in (rules if isinstance(rules, list) else [])
        ],
    }


def run_stage_visuals(session: PipelineSession, comments: list[str]) -> dict:
    session.visuals = session.orch._phase_visuals(
        session.brief, session.story, session.design, session.perspectives)
    return {
        "visual_count": len(session.visuals),
        "types": list(session.visuals.keys()),
        "paths": {k: str(v) for k, v in session.visuals.items()},
    }


def run_stage_pdf_generation(session: PipelineSession, comments: list[str]) -> dict:
    """Generate PDF. PDF is ALWAYS delivered."""
    session.audit = session.orch._phase_screen_audit(
        session.brief, session.design, session.visuals)

    session.elapsed = time.time() - session.created_at
    session.pdf_path = session.orch._phase_pdf(
        session.brief, session.design, session.story, session.visuals,
        session.pulse, session.strategy, session.pre_val, session.elapsed)

    pdf_exists = Path(session.pdf_path).exists()
    pdf_size = round(Path(session.pdf_path).stat().st_size / 1024) if pdf_exists else 0

    return {
        "pdf_path": session.pdf_path,
        "pdf_exists": pdf_exists,
        "pdf_size_kb": pdf_size,
        "pdf_ready": True,
    }


def run_stage_post_validation(session: PipelineSession, comments: list[str]) -> dict:
    """Informational only — does NOT block PDF delivery."""
    session.post_val = session.orch._phase_post_validation(
        session.brief, session.design, session.story,
        session.visuals, session.audit)

    pre_score = session.pre_val.get("total_score", 0)
    post_score = session.post_val.get("total_score", 0)
    combined = round((pre_score + post_score) / 2, 1)

    # Save trace
    session.orch.tracer.save(final_output={
        "pdf_path": session.pdf_path,
        "validation_score": combined,
        "pre_visual_score": pre_score,
        "post_visual_score": post_score,
    })

    rules = session.post_val.get("rules_checked", [])
    return {
        "total_score": session.post_val.get("total_score", 0),
        "combined_score": combined,
        "pre_visual_score": pre_score,
        "post_visual_score": post_score,
        "approved": session.post_val.get("approved", False),
        "explanation": str(session.post_val.get("explanation", "")),
        "critical_failures": session.post_val.get("critical_failures", []),
        "fix_instructions": session.post_val.get("fix_instructions", []),
        "verdict": str(session.post_val.get("verdict", "")),
        "rules_checked": [
            {
                "id": r.get("id", "?"),
                "passed": r.get("passed", False),
                "reasoning": str(r.get("reasoning", "")),
            }
            for r in (rules if isinstance(rules, list) else [])
        ],
        "informational_only": True,
        "duration_seconds": time.time() - session.created_at,
        "headline": session.story.get("headline", ""),
    }


def run_stage_send_email(session: PipelineSession, user_comments: list[str] = None) -> dict:
    """Stage 13: Generate the LinkedIn-style email draft using LinkedInExpert."""
    from aibrief.agents.specialists import LinkedInExpert

    li_expert = LinkedInExpert()

    story = session.story or {}
    brief = session.brief or {}
    hooks = (session.discussion or {}).get("discussion_hooks", [])

    # Inject user feedback into the story context so the agent is aware of it
    if user_comments:
        feedback_block = "\n\n[USER FEEDBACK - HIGH PRIORITY (5× weight)]:\n" + "\n".join(user_comments)
        story_with_feedback = {**story, "user_feedback": feedback_block}
    else:
        story_with_feedback = story

    result = li_expert.craft_post(story_with_feedback, brief, hooks=hooks)

    # Ensure post_text is always present
    post_text = ""
    document_title = ""
    if isinstance(result, dict):
        post_text = result.get("post_text", "")
        document_title = result.get("document_title", brief.get("brief_title", "AI Brief"))
    elif isinstance(result, str):
        post_text = result
        document_title = brief.get("brief_title", "AI Brief")

    return {
        "post_text": post_text,
        "document_title": document_title,
        "hashtags": result.get("hashtags", []) if isinstance(result, dict) else [],
        "best_posting_time": result.get("best_posting_time", "") if isinstance(result, dict) else "",
        "expected_reach": result.get("expected_reach", "") if isinstance(result, dict) else "",
        "headline": story.get("headline", ""),
        "news_url": story.get("news_url", session.source_url),
    }


# Stage ID → runner function mapping
STAGE_RUNNERS = {
    "content_extraction": run_stage_content_extraction,
    "design_dna": run_stage_design_dna,
    "analyst_pairs": run_stage_analyst_pairs,
    "round_table": run_stage_round_table,
    "editorial": run_stage_editorial,
    "content_synthesis": run_stage_content_synthesis,
    "neutrality_check": run_stage_neutrality_check,
    "discussion_potential": run_stage_discussion_potential,
    "pre_validation": run_stage_pre_validation,
    "visuals": run_stage_visuals,
    "pdf_generation": run_stage_pdf_generation,
    "post_validation": run_stage_post_validation,
    "send_email": run_stage_send_email,
}


# ═══════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0", "stages": list(STAGE_RUNNERS.keys())}


@app.post("/session", response_model=SessionStatusResponse)
def create_session(req: CreateSessionRequest):
    session = PipelineSession(
        source_url=req.source_url,
        source_text=req.source_text,
        pages=req.pages,
    )
    SESSIONS[session.session_id] = session
    print(f"\n[API] Session created: {session.session_id} | URL: {req.source_url[:80]}")
    if session.cached_run_id:
        print(f"[API] Cache hit: previous run {session.cached_run_id}")
    return SessionStatusResponse(
        session_id=session.session_id,
        status="created",
        current_stage="",
        stages_completed=[],
        cached_run_id=session.cached_run_id,
    )


@app.get("/session/{session_id}/status", response_model=SessionStatusResponse)
def get_session_status(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        current_stage=session.current_stage,
        stages_completed=session.stages_completed,
        cached_run_id=session.cached_run_id,
    )


@app.post("/session/{session_id}/run/{stage_id}", response_model=StageResultResponse)
def run_stage(session_id: str, stage_id: str, req: RunStageRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    runner = STAGE_RUNNERS.get(stage_id)
    if not runner:
        raise HTTPException(400, f"Unknown stage: {stage_id}. "
                            f"Available: {list(STAGE_RUNNERS.keys())}")

    # Store + inject user comments
    if req.user_comments:
        session.user_comments[stage_id] = req.user_comments
        print(f"[API] {len(req.user_comments)} user comment(s) for {stage_id}")

    session.current_stage = stage_id
    session.status = "running"

    t0 = time.time()
    try:
        result = runner(session, req.user_comments)
        duration = time.time() - t0

        session.stages_completed.append(stage_id)
        session.stage_results[stage_id] = result
        session.status = "awaiting_approval"

        print(f"[API] Stage {stage_id} complete ({duration:.1f}s)")

        safe_result = _make_json_safe(result)

        return StageResultResponse(
            stage_id=stage_id,
            status="success",
            result=safe_result,
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        duration = time.time() - t0
        session.status = "error"
        tb = traceback.format_exc()
        print(f"[API] Stage {stage_id} FAILED: {e}\n{tb}")
        return StageResultResponse(
            stage_id=stage_id,
            status="error",
            result={"error": str(e)},
            duration_seconds=round(duration, 1),
            error=str(e),
        )


ANALYST_PAIRS = {
    "historical": ("historian", "hist_reviewer", "Clio", "Theron"),
    "economic": ("economist", "econ_reviewer", "Aurelia", "Callisto"),
    "social": ("sociologist", "soc_reviewer", "Sage", "Liora"),
    "future": ("futurist", "fut_reviewer", "Nova", "Orion"),
}


@app.post("/session/{session_id}/analyst/{perspective}", response_model=StageResultResponse)
def run_analyst_perspective(session_id: str, perspective: str, req: RunStageRequest):
    """Run a SINGLE analyst pair debate for one perspective."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    if perspective not in ANALYST_PAIRS:
        raise HTTPException(400, f"Unknown perspective: {perspective}. "
                            f"Available: {list(ANALYST_PAIRS.keys())}")

    prep_attr, rev_attr, p_code, r_code = ANALYST_PAIRS[perspective]
    preparer = getattr(session.orch, prep_attr)
    reviewer = getattr(session.orch, rev_attr)

    # Inject user comments if provided
    if req.user_comments:
        session.user_comments[f"analyst_{perspective}"] = req.user_comments
        print(f"[API] {len(req.user_comments)} user comment(s) for analyst_{perspective}")

    session.current_stage = f"analyst_{perspective}"
    session.status = "running"

    t0 = time.time()
    try:
        # Tracer phase start
        content_type = session.strategy.get("content_type", "")
        session.orch.tracer.begin_phase(
            phase=f"Analyst_{perspective}",
            agent_name=preparer.name,
            agent_codename=p_code,
            model=preparer.model,
            fixed_inputs={"core_instruction": f"Analyze from {perspective} perspective"},
            variable_inputs={
                "story": session.orch.tracer.var_ref(
                    "NewsScout", "Sable", "TopicDiscovery", session.story),
                "content_type": session.orch.tracer.var_ref(
                    "ContentStrategist", "Marcus", "ContentStrategy", content_type),
            },
        )

        # Run preparer analysis
        initial = preparer.analyse(session.story)
        session.orch.tracer.end_phase(initial)

        # Run debate (preparer vs reviewer, multiple rounds)
        result = session.orch._argue(preparer, reviewer, initial, perspective, session.story)

        # Store perspective result on the session for later stages (round_table etc.)
        if not session.perspectives:
            session.perspectives = {}
        session.perspectives[perspective] = result

        duration = time.time() - t0

        # Build summary for this perspective
        summary = {}
        if isinstance(result, dict):
            summary = {
                "perspective_title": result.get("perspective_title", result.get("title", perspective)),
                "pull_quote": result.get("pull_quote", result.get("key_quote", "")),
                "confidence": result.get("confidence", 0),
                "key_arguments": _extract_key_arguments(result),
            }

        # Get full debate data from tracer
        debate_entries = [e for e in session.orch.tracer.entries
                         if e.get("phase") == "DEBATE"
                         and perspective in e.get("label", "").lower()
                         and "RoundTable" not in e.get("pair", "")]

        full_debate = None
        if debate_entries:
            d = debate_entries[-1]  # Last (most recent) entry for this perspective
            rounds = d.get("rounds", [])
            full_debate = {
                "label": d.get("label", perspective),
                "preparer_name": d.get("preparer_name", preparer.name),
                "reviewer_name": d.get("reviewer_name", reviewer.name),
                "total_rounds": len(rounds),
                "final_score": rounds[-1].get("score", 0) if rounds else 0,
                "final_approved": rounds[-1].get("approved", False) if rounds else False,
                "rounds": [],
            }
            for r in rounds:
                full_debate["rounds"].append({
                    "round": r.get("round", 0),
                    "score": r.get("score", 0),
                    "approved": r.get("approved", False),
                    "demands_count": r.get("demands_count", 0),
                    "preparer_submission": r.get("preparer_submission", {}),
                    "reviewer_feedback": r.get("reviewer_feedback", {}),
                    "demands": r.get("demands", []),
                    "verdict": r.get("verdict", ""),
                    "preparer_revision": r.get("preparer_revision", None),
                })

        session.status = "awaiting_approval"
        print(f"[API] Analyst {perspective} complete ({duration:.1f}s)")

        safe_result = _make_json_safe({
            "perspective": perspective,
            "preparer": preparer.name,
            "reviewer": reviewer.name,
            "summary": summary,
            "full_debate": full_debate,
            "perspectives_completed": list(session.perspectives.keys()),
        })

        return StageResultResponse(
            stage_id=f"analyst_{perspective}",
            status="success",
            result=safe_result,
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        duration = time.time() - t0
        session.status = "error"
        tb = traceback.format_exc()
        print(f"[API] Analyst {perspective} FAILED: {e}\n{tb}")
        return StageResultResponse(
            stage_id=f"analyst_{perspective}",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(duration, 1),
            error=str(e),
        )


# ═══════════════════════════════════════════════════════════════
#  GRANULAR ACTION ENDPOINTS
#  Each endpoint runs ONE agent action and returns immediately.
#  The TypeScript bot orchestrates the sequence and approval gates.
# ═══════════════════════════════════════════════════════════════

class ActionRequest(BaseModel):
    """Input for granular action endpoints."""
    user_comments: list[str] = []
    previous_work: Optional[dict] = None   # output from a prior action (e.g., prepare → review)
    review_feedback: Optional[dict] = None  # reviewer feedback for revise actions


def _build_feedback_injection(user_comments: list[str]) -> str:
    """Build a string to inject user feedback into an agent's prompt.
    User feedback is weighted 5× — the agent MUST prioritize it."""
    if not user_comments:
        return ""
    feedback = "\n".join(f"  - {c}" for c in user_comments)
    return (
        "\n\n═══ USER FEEDBACK (PRIORITY — 5× WEIGHT) ═══\n"
        "The human supervisor has provided the following feedback. "
        "You MUST address every point below. Their input takes priority "
        "over your own judgment:\n"
        f"{feedback}\n"
        "═══ END USER FEEDBACK ═══\n"
    )


# ── Analyst: Prepare (initial analysis) ──
@app.post("/session/{session_id}/action/analyst/{perspective}/prepare", response_model=StageResultResponse)
def action_analyst_prepare(session_id: str, perspective: str, req: ActionRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    if perspective not in ANALYST_PAIRS:
        raise HTTPException(400, f"Unknown perspective: {perspective}")

    prep_attr, _, p_code, _ = ANALYST_PAIRS[perspective]
    preparer = getattr(session.orch, prep_attr)

    feedback_str = _build_feedback_injection(req.user_comments)

    t0 = time.time()
    try:
        # Inject user feedback into the story context if present
        story_input = session.story
        if feedback_str:
            story_input = {**session.story, "_user_feedback": feedback_str} if isinstance(session.story, dict) else session.story
            # Also inject as text if the agent uses string input
            if isinstance(story_input, dict) and "article_text" in story_input:
                story_input["article_text"] = story_input["article_text"] + feedback_str
        result = preparer.analyse(story_input)
        duration = time.time() - t0

        # Store on session for later use
        if not hasattr(session, '_action_work'):
            session._action_work = {}
        session._action_work[f"{perspective}_prepare"] = result

        return StageResultResponse(
            stage_id=f"analyst_{perspective}_prepare",
            status="success",
            result=_make_json_safe(result),
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        return StageResultResponse(
            stage_id=f"analyst_{perspective}_prepare",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(time.time() - t0, 1),
            error=str(e),
        )


# ── Analyst: Review (reviewer evaluates work) ──
@app.post("/session/{session_id}/action/analyst/{perspective}/review", response_model=StageResultResponse)
def action_analyst_review(session_id: str, perspective: str, req: ActionRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    if perspective not in ANALYST_PAIRS:
        raise HTTPException(400, f"Unknown perspective: {perspective}")

    _, rev_attr, _, r_code = ANALYST_PAIRS[perspective]
    reviewer = getattr(session.orch, rev_attr)

    # The work to review: either from request body or from session state
    work = req.previous_work
    if not work:
        work = getattr(session, '_action_work', {}).get(f"{perspective}_prepare")
    if not work:
        raise HTTPException(400, "No work to review — pass previous_work or run prepare first")

    feedback_str = _build_feedback_injection(req.user_comments)

    t0 = time.time()
    try:
        prompt = f"Review this {perspective} work. Be demanding."
        if feedback_str:
            prompt += feedback_str
        review = reviewer.think(
            prompt,
            context={"work": work, "story_context": session.story},
        )
        duration = time.time() - t0

        score = review.get("overall_score", 0) if isinstance(review, dict) else 0
        approved = review.get("approved", False) if isinstance(review, dict) else False

        # Store for revise action
        if not hasattr(session, '_action_work'):
            session._action_work = {}
        session._action_work[f"{perspective}_review"] = review

        return StageResultResponse(
            stage_id=f"analyst_{perspective}_review",
            status="success",
            result=_make_json_safe({
                "review": review,
                "score": score,
                "approved": approved,
                "demands": review.get("demands", []) if isinstance(review, dict) else [],
                "strengths": review.get("strengths", []) if isinstance(review, dict) else [],
                "verdict": review.get("verdict", "") if isinstance(review, dict) else str(review),
            }),
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        return StageResultResponse(
            stage_id=f"analyst_{perspective}_review",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(time.time() - t0, 1),
            error=str(e),
        )


# ── Analyst: Revise (preparer addresses feedback) ──
@app.post("/session/{session_id}/action/analyst/{perspective}/revise", response_model=StageResultResponse)
def action_analyst_revise(session_id: str, perspective: str, req: ActionRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    if perspective not in ANALYST_PAIRS:
        raise HTTPException(400, f"Unknown perspective: {perspective}")

    prep_attr, _, p_code, _ = ANALYST_PAIRS[perspective]
    preparer = getattr(session.orch, prep_attr)

    # Original work + reviewer feedback
    work = req.previous_work
    if not work:
        work = getattr(session, '_action_work', {}).get(f"{perspective}_prepare")
    feedback = req.review_feedback
    if not feedback:
        feedback = getattr(session, '_action_work', {}).get(f"{perspective}_review")
    if not work or not feedback:
        raise HTTPException(400, "Need previous_work and review_feedback for revise")

    feedback_str = _build_feedback_injection(req.user_comments)
    if feedback_str and isinstance(feedback, dict):
        feedback["_user_feedback"] = feedback_str

    t0 = time.time()
    try:
        revised = preparer.respond_to_feedback(work, feedback)
        duration = time.time() - t0

        # Update stored work for next review round
        if not hasattr(session, '_action_work'):
            session._action_work = {}
        session._action_work[f"{perspective}_prepare"] = revised  # overwrite for next review

        return StageResultResponse(
            stage_id=f"analyst_{perspective}_revise",
            status="success",
            result=_make_json_safe(revised),
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        return StageResultResponse(
            stage_id=f"analyst_{perspective}_revise",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(time.time() - t0, 1),
            error=str(e),
        )


# ── Analyst: Finalize (store perspective result on session) ──
@app.post("/session/{session_id}/action/analyst/{perspective}/finalize", response_model=StageResultResponse)
def action_analyst_finalize(session_id: str, perspective: str, req: ActionRequest):
    """Store the final approved perspective on the session for later stages."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    work = req.previous_work
    if not work:
        work = getattr(session, '_action_work', {}).get(f"{perspective}_prepare")
    if not work:
        raise HTTPException(400, "No work to finalize")

    if not session.perspectives:
        session.perspectives = {}
    session.perspectives[perspective] = work

    return StageResultResponse(
        stage_id=f"analyst_{perspective}_finalize",
        status="success",
        result={"perspective": perspective, "finalized": True,
                "perspectives_completed": list(session.perspectives.keys())},
        duration_seconds=0,
    )


# ── Round Table: Challenge ──
ROUND_TABLE_PAIRS = [
    ("economist", "economic", "historical", "Historian"),
    ("historian", "historical", "future", "Futurist"),
    ("futurist", "future", "social", "Sociologist"),
    ("sociologist", "social", "economic", "Economist"),
]

@app.post("/session/{session_id}/action/round_table/{challenger_key}/challenge", response_model=StageResultResponse)
def action_round_table_challenge(session_id: str, challenger_key: str, req: ActionRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    pair = next((p for p in ROUND_TABLE_PAIRS if p[0] == challenger_key), None)
    if not pair:
        raise HTTPException(400, f"Unknown challenger: {challenger_key}")

    agent_attr, own_key, target_key, target_name = pair
    challenger = getattr(session.orch, agent_attr)

    feedback_str = _build_feedback_injection(req.user_comments)

    t0 = time.time()
    try:
        prompt = (
            f"You are reading {target_name}'s analysis. Challenge it from "
            f"YOUR perspective. Point out what they missed, where they're "
            f"wrong, and what needs deeper analysis. Also acknowledge what "
            f"they got right."
        )
        if feedback_str:
            prompt += feedback_str
        challenge = challenger.think(
            prompt,
            context={
                "your_own_work": session.perspectives.get(own_key, {}),
                f"{target_name}_work": session.perspectives.get(target_key, {}),
            },
        )
        duration = time.time() - t0

        # Store challenge for response phase
        if not hasattr(session, '_challenges'):
            session._challenges = {}
        session._challenges[f"{challenger.name}->{target_name}"] = challenge

        return StageResultResponse(
            stage_id=f"round_table_{challenger_key}_challenge",
            status="success",
            result=_make_json_safe({
                "challenger": challenger.name,
                "target": target_name,
                "challenge": challenge,
            }),
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        return StageResultResponse(
            stage_id=f"round_table_{challenger_key}_challenge",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(time.time() - t0, 1),
            error=str(e),
        )


# ── Round Table: Respond (incorporate challenges) ──
@app.post("/session/{session_id}/action/round_table/{challenger_key}/respond", response_model=StageResultResponse)
def action_round_table_respond(session_id: str, challenger_key: str, req: ActionRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    pair = next((p for p in ROUND_TABLE_PAIRS if p[0] == challenger_key), None)
    if not pair:
        raise HTTPException(400, f"Unknown challenger: {challenger_key}")

    agent_attr, own_key, _, _ = pair
    challenger = getattr(session.orch, agent_attr)

    # Find challenges directed AT this agent
    all_challenges = getattr(session, '_challenges', {})
    incoming = {k: v for k, v in all_challenges.items()
                if k.endswith(f"->{challenger.name.split()[0]}")}

    feedback_str = _build_feedback_injection(req.user_comments)

    t0 = time.time()
    try:
        if incoming:
            feedback_payload = {"cross_challenges": incoming}
            if feedback_str:
                feedback_payload["_user_feedback"] = feedback_str
            updated = challenger.respond_to_feedback(
                session.perspectives.get(own_key, {}),
                feedback_payload
            )
            session.perspectives[own_key] = updated
        else:
            updated = session.perspectives.get(own_key, {})

        duration = time.time() - t0

        return StageResultResponse(
            stage_id=f"round_table_{challenger_key}_respond",
            status="success",
            result=_make_json_safe({
                "agent": challenger.name,
                "challenges_addressed": len(incoming),
                "updated_perspective": updated,
            }),
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        return StageResultResponse(
            stage_id=f"round_table_{challenger_key}_respond",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(time.time() - t0, 1),
            error=str(e),
        )


# ── Content Synthesis: Synthesise ──
@app.post("/session/{session_id}/action/synthesis/synthesise", response_model=StageResultResponse)
def action_synthesis_synthesise(session_id: str, req: ActionRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    feedback_str = _build_feedback_injection(req.user_comments)

    t0 = time.time()
    try:
        story_input = session.story
        if feedback_str and isinstance(story_input, dict):
            story_input = {**story_input, "_user_feedback": feedback_str}
        brief = session.orch.writer.synthesise(story_input, session.perspectives)
        duration = time.time() - t0

        session.brief = brief
        if not hasattr(session, '_action_work'):
            session._action_work = {}
        session._action_work["synthesis_work"] = brief

        return StageResultResponse(
            stage_id="synthesis_synthesise",
            status="success",
            result=_make_json_safe(brief),
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        return StageResultResponse(
            stage_id="synthesis_synthesise",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(time.time() - t0, 1),
            error=str(e),
        )


# ── Content Synthesis: Review (Sterling) ──
@app.post("/session/{session_id}/action/synthesis/review", response_model=StageResultResponse)
def action_synthesis_review(session_id: str, req: ActionRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    work = req.previous_work
    if not work:
        work = getattr(session, '_action_work', {}).get("synthesis_work")
    if not work:
        work = session.brief
    if not work:
        raise HTTPException(400, "No synthesis work to review")

    feedback_str = _build_feedback_injection(req.user_comments)

    t0 = time.time()
    try:
        prompt = "Review this content_brief work. Be demanding."
        if feedback_str:
            prompt += feedback_str
        review = session.orch.copy_reviewer.think(
            prompt,
            context={"work": work, "story_context": session.story},
        )
        duration = time.time() - t0

        score = review.get("overall_score", 0) if isinstance(review, dict) else 0
        approved = review.get("approved", False) if isinstance(review, dict) else False

        if not hasattr(session, '_action_work'):
            session._action_work = {}
        session._action_work["synthesis_review"] = review

        return StageResultResponse(
            stage_id="synthesis_review",
            status="success",
            result=_make_json_safe({
                "review": review,
                "score": score,
                "approved": approved,
                "demands": review.get("demands", []) if isinstance(review, dict) else [],
                "verdict": review.get("verdict", review.get("tone_verdict", "")) if isinstance(review, dict) else str(review),
            }),
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        return StageResultResponse(
            stage_id="synthesis_review",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(time.time() - t0, 1),
            error=str(e),
        )


# ── Content Synthesis: Revise (Quill) ──
@app.post("/session/{session_id}/action/synthesis/revise", response_model=StageResultResponse)
def action_synthesis_revise(session_id: str, req: ActionRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    work = req.previous_work
    if not work:
        work = getattr(session, '_action_work', {}).get("synthesis_work")
    feedback = req.review_feedback
    if not feedback:
        feedback = getattr(session, '_action_work', {}).get("synthesis_review")
    if not work or not feedback:
        raise HTTPException(400, "Need previous_work and review_feedback for revise")

    feedback_str = _build_feedback_injection(req.user_comments)
    if feedback_str and isinstance(feedback, dict):
        feedback["_user_feedback"] = feedback_str

    t0 = time.time()
    try:
        revised = session.orch.writer.respond_to_feedback(work, feedback)
        duration = time.time() - t0

        session.brief = revised
        if not hasattr(session, '_action_work'):
            session._action_work = {}
        session._action_work["synthesis_work"] = revised

        return StageResultResponse(
            stage_id="synthesis_revise",
            status="success",
            result=_make_json_safe(revised),
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        return StageResultResponse(
            stage_id="synthesis_revise",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(time.time() - t0, 1),
            error=str(e),
        )


# ── Send Email: Craft LinkedIn-style post text ──
@app.post("/session/{session_id}/action/send_email/craft", response_model=StageResultResponse)
def action_craft_email_post(session_id: str, req: ActionRequest):
    """Generate the LinkedIn-style formatted post text that will be sent via email.
    Uses LinkedInExpert.craft_post() to produce Unicode-formatted text with
    bold headers, bullet points, article URL, Discord invite, and hashtags."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    from aibrief.agents.specialists import LinkedInExpert
    linkedin_expert = LinkedInExpert()

    feedback_str = _build_feedback_injection(req.user_comments)

    # Gather brief content for the post
    brief_content = session.brief or getattr(session, '_action_work', {}).get("synthesis_work", {})
    story = session.story or {}

    # Get discussion hooks if available
    discussion = session.stage_results.get("discussion_potential", {})
    hooks = discussion.get("discussion_hooks", []) if isinstance(discussion, dict) else []

    t0 = time.time()
    try:
        result = linkedin_expert.craft_post(
            story=story,
            brief_content=brief_content,
            hooks=hooks,
        )
        duration = time.time() - t0

        post_text = result.get("post_text", "") if isinstance(result, dict) else str(result)
        document_title = result.get("document_title", "") if isinstance(result, dict) else ""

        # If user gave feedback, ask the expert to revise
        if feedback_str and post_text:
            revision_result = linkedin_expert.think(
                f"Revise this LinkedIn post based on user feedback. "
                f"Keep the Unicode formatting (bold, bullets, separators). "
                f"Keep the Discord invite link and article URL.\n\n"
                f"CURRENT POST:\n{post_text}\n"
                f"{feedback_str}",
                context={"original_post": post_text, "story": story},
                max_tokens=3000,
            )
            if isinstance(revision_result, dict) and revision_result.get("post_text"):
                post_text = revision_result["post_text"]
                document_title = revision_result.get("document_title", document_title)

        # Extract headline hook (first non-empty line)
        headline_hook = ""
        for line in post_text.split("\n"):
            stripped = line.strip()
            if stripped:
                headline_hook = stripped
                break

        return StageResultResponse(
            stage_id="send_email_craft",
            status="success",
            result=_make_json_safe({
                "post_text": post_text,
                "document_title": document_title,
                "headline_hook": headline_hook,
            }),
            duration_seconds=round(duration, 1),
        )
    except Exception as e:
        return StageResultResponse(
            stage_id="send_email_craft",
            status="error",
            result={"error": str(e)},
            duration_seconds=round(time.time() - t0, 1),
            error=str(e),
        )


@app.get("/session/{session_id}/pdf")
def get_pdf_info(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    if not session.pdf_path or not Path(session.pdf_path).exists():
        raise HTTPException(404, "PDF not generated yet")
    return {
        "pdf_path": session.pdf_path,
        "pdf_size_kb": round(Path(session.pdf_path).stat().st_size / 1024),
    }


@app.get("/session/{session_id}/pdf/download")
def download_pdf(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    if not session.pdf_path or not Path(session.pdf_path).exists():
        raise HTTPException(404, "PDF not generated yet")
    return FileResponse(
        session.pdf_path,
        media_type="application/pdf",
        filename=Path(session.pdf_path).name,
    )


@app.post("/session/{session_id}/publish/linkedin")
def publish_linkedin(session_id: str, req: PublishLinkedInRequest):
    """Publish the session PDF to LinkedIn after human approval."""
    session = SESSIONS.get(session_id)
    session_missing = session is None

    # Support cached replay sessions: allow caller to provide pdf_path + story directly.
    if session_missing:
        if not req.pdf_path:
            raise HTTPException(404, f"Session {session_id} not found")
        if not Path(req.pdf_path).exists():
            raise HTTPException(404, f"PDF not found: {req.pdf_path}")
        pdf_path = req.pdf_path
        story = req.story or {}
        brief_title = "AI Brief"
    else:
        if not session.pdf_path or not Path(session.pdf_path).exists():
            raise HTTPException(404, "PDF not generated yet")
        pdf_path = session.pdf_path
        story = session.story or {}
        brief_title = (session.brief or {}).get("brief_title", "AI Brief")

    post_text = (req.post_text or "").strip()
    document_title = (req.document_title or "").strip()

    # Prefer the send_email stage draft if caller didn't provide text (only for live sessions).
    if not post_text and not session_missing:
        send_email_result = session.stage_results.get("send_email", {})  # type: ignore[union-attr]
        if isinstance(send_email_result, dict):
            post_text = str(send_email_result.get("post_text", "")).strip()
            if not document_title:
                document_title = str(send_email_result.get("document_title", "")).strip()

    # Last fallback: craft a fresh LinkedIn draft from current session state.
    if not post_text and not session_missing:
        from aibrief.agents.specialists import LinkedInExpert
        expert = LinkedInExpert()
        hooks = (session.discussion or {}).get("discussion_hooks", [])  # type: ignore[union-attr]
        crafted = expert.craft_post(story, session.brief or {}, hooks=hooks)  # type: ignore[union-attr]
        if isinstance(crafted, dict):
            post_text = str(crafted.get("post_text", "")).strip()
            if not document_title:
                document_title = str(crafted.get("document_title", "")).strip()

    if not post_text:
        raise HTTPException(400, "No LinkedIn post text available to publish.")

    if not document_title:
        document_title = brief_title

    from aibrief.pipeline.linkedin import post_brief
    result = post_brief(
        pdf_path,
        post_text,
        story=story,
        document_title=document_title,
    )

    safe_result = _make_json_safe(result)
    if not session_missing:
        session.stage_results["linkedin_publish"] = safe_result  # type: ignore[union-attr]
        session.status = "published" if safe_result.get("status") == "success" else "publish_failed"  # type: ignore[union-attr]

    return {
        "status": safe_result.get("status", "failed"),
        "url": safe_result.get("url", ""),
        "post_id": safe_result.get("post_id", ""),
        "document_title": document_title,
        "error": safe_result.get("error", ""),
    }


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _make_json_safe(obj, depth=0):
    """Recursively make an object JSON-serializable."""
    if depth > 8:
        return str(obj)[:300]
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(item, depth + 1) for item in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        if isinstance(obj, str) and len(obj) > 3000:
            return obj[:3000] + "…"
        return obj
    return str(obj)[:500]


# ═══════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    port = 8900
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    print(f"\n{'=' * 60}")
    print(f"  AI Brief Pipeline API v3.0")
    print(f"  http://localhost:{port}")
    print(f"  Docs: http://localhost:{port}/docs")
    print(f"  Stages: {len(STAGE_RUNNERS)}")
    print(f"{'=' * 60}\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
