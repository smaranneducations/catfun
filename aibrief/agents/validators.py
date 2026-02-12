"""Validation Agents — Split into PRE-VISUAL and POST-VISUAL phases.

Pre-visual (Phase 8.7 — before spending money on images):
  Content, author, architecture, guardrails, format rules that can be
  checked from the brief/design/story alone.

Post-visual (Phase 12 — after PDF is generated):
  Layout, visuals, design quality — things that only exist once images
  and the PDF are produced.

Gate threshold: 60% on BOTH passes.
"""
import json
from aibrief.agents.base import Agent
from aibrief import config

# ═══════════════════════════════════════════════════════════════
#  THE GUARDRAIL
# ═══════════════════════════════════════════════════════════════
GUARDRAIL = (
    "CORE ETHICAL GUARDRAIL (non-negotiable): "
    "'Speak the truth, but never a truth that will hurt someone "
    "in thought, action, and speech.' This means: be honest and "
    "factual, but frame everything with empathy. Never attack "
    "individuals. Critique ideas and approaches, not people. "
    "If a statement could harm someone's reputation or wellbeing, "
    "reframe it constructively or omit it."
)

# ═══════════════════════════════════════════════════════════════
#  PRE-VISUAL RULES — Can be validated from brief/design/story
#  (no images or PDF needed)
# ═══════════════════════════════════════════════════════════════
PRE_VISUAL_RULES = [
    {"id": 5,  "rule": "Author is 'Bhasker Kumar' — no fictional names", "category": "author", "weight": 3},
    {"id": 6,  "rule": "Assistant name is 'Orion Cael' — the fixed agent author identity", "category": "author", "weight": 2},
    {"id": 7,  "rule": "Credits section lists agentic system with multiple AI models", "category": "author", "weight": 2},
    {"id": 8,  "rule": "Agents actually argued and critiqued each other (not linear pipeline)", "category": "architecture", "weight": 3},
    {"id": 10, "rule": "Copy reads like luxury advertisement — polished, aspirational, premium", "category": "content", "weight": 3},
    {"id": 17, "rule": "Preparer/Reviewer pairs argued in multiple rounds", "category": "architecture", "weight": 3},
    {"id": 18, "rule": "Quality reflects genuine creative excellence, not just automation", "category": "meta", "weight": 3},
    {"id": 21, "rule": "Bullet points used, NOT paragraphs. Short punchy text.", "category": "format", "weight": 3},
    {"id": 27, "rule": "Guardrail 'truth but never hurtful' is in Director, Writer, AND Reviewer (3 places)", "category": "guardrails", "weight": 3},
    {"id": 28, "rule": "No instructions were bypassed or shortcut", "category": "meta", "weight": 3},
    {"id": 29, "rule": "Content is neutral — never negative about individuals, constructively critical only", "category": "guardrails", "weight": 3},
    {"id": 30, "rule": "Each page has ONE clear idea", "category": "format", "weight": 2},
    {"id": 32, "rule": "LinkedIn post log tracks all posts to avoid repeats", "category": "meta", "weight": 1},
    {"id": 33, "rule": "Design agent picked a distinct emotion-driven style from the catalog", "category": "design", "weight": 2},
    {"id": 34, "rule": "Multiple perspectives covered: history, economy, sociology, future", "category": "content", "weight": 2},
    {"id": 35, "rule": "Written as AI thought leader / head of consulting company", "category": "content", "weight": 2},
    {"id": 37, "rule": "STRICT: Max 1 point per slide. One powerful high-value statement + one insight. No lists of 4-6 bullets. Quality over quantity.", "category": "format", "weight": 3},
]

# ═══════════════════════════════════════════════════════════════
#  POST-VISUAL RULES — Need images/PDF to validate
# ═══════════════════════════════════════════════════════════════
POST_VISUAL_RULES = [
    {"id": 1,  "rule": "Every page has a visual element (DALL-E image, infographic, or artistic graphic)", "category": "visuals", "weight": 3},
    {"id": 2,  "rule": "Layout is balanced — not too empty, not too crowded. Luxury fashion brand quality.", "category": "layout", "weight": 3},
    {"id": 3,  "rule": "Design is COMPLETELY DIFFERENT from any prior version — unique palette, layout, motifs", "category": "design", "weight": 3},
    {"id": 4,  "rule": "Uses creative tools: DALL-E images, Pillow infographics, data visualizations", "category": "visuals", "weight": 2},
    {"id": 9,  "rule": "Design quality matches luxury product website (Hermes, Chanel, LV level)", "category": "design", "weight": 3},
    {"id": 11, "rule": "No empty/dull dead space on any page bottom", "category": "layout", "weight": 3},
    {"id": 12, "rule": "Author and assistant text is PROMINENT and visible, not tiny", "category": "author", "weight": 3},
    {"id": 13, "rule": "ScreenRealEstateAgent reviewed the PDF", "category": "architecture", "weight": 2},
    {"id": 14, "rule": "Golden ratio (1.618) used for proportions", "category": "design_psychology", "weight": 2},
    {"id": 15, "rule": "Color psychology applied (blue=trust, gold=luxury, gray=authority)", "category": "design_psychology", "weight": 2},
    {"id": 16, "rule": "Typography hierarchy: 3+ levels (display, body, caption)", "category": "design_psychology", "weight": 2},
    {"id": 19, "rule": "PDF looks like PRESENTATION SLIDES (PPT style), not a text document", "category": "format", "weight": 3},
    {"id": 20, "rule": "Big commanding headers on every page (36pt+ display text)", "category": "format", "weight": 3},
    {"id": 22, "rule": "EVERY page has exciting background — rich, artistic, never plain", "category": "layout", "weight": 3},
    {"id": 23, "rule": "Cover page (first slide) is SUPER exciting — dramatic, wow factor", "category": "layout", "weight": 3},
    {"id": 24, "rule": "Every page background has light artistic pattern/texture — subtle but present", "category": "layout", "weight": 3},
    {"id": 25, "rule": "Author 'Bhasker Kumar' on cover is >= 75% of header font size", "category": "author", "weight": 3},
    {"id": 36, "rule": "LinkedIn expert uses proper Unicode formatting for bold/italic", "category": "linkedin", "weight": 1},
]

# Combined for backward compat
MASTER_CHECKLIST = PRE_VISUAL_RULES + POST_VISUAL_RULES

PASS_THRESHOLD = 60   # 60% gate on each pass


def _build_validator_prompt(rules: list, phase_name: str) -> str:
    """Build the system prompt for a validator pass."""
    checklist_text = "\n".join(
        f"  [{c['id']}] (weight:{c['weight']}) {c['rule']}"
        for c in rules
    )
    total_weight = sum(c["weight"] for c in rules)
    return (
        f"You are the {phase_name} quality gate for a luxury PDF brief. "
        f"You check EVERY rule assigned to you. Be fair but thorough.\n\n"
        f"{GUARDRAIL}\n\n"
        f"CHECKLIST ({len(rules)} rules, total weight {total_weight}):\n"
        f"{checklist_text}\n\n"
        f"SCORING:\n"
        f"- Check each rule: PASS (full weight) or FAIL (0 weight)\n"
        f"- Calculate: (sum of passed weights / sum of all weights) * 100\n"
        f"- PASS threshold: {PASS_THRESHOLD}%\n"
        f"- If < {PASS_THRESHOLD}%: REJECT with specific failures\n"
        f"- If >= {PASS_THRESHOLD}%: APPROVE but still list failures\n\n"
        f"IMPORTANT — For every FAILED rule you MUST explain:\n"
        f"  1. What specific evidence you looked at\n"
        f"  2. Why it fails (concrete reason, not vague)\n"
        f"  3. What exactly needs to change to pass\n\n"
        f"Return JSON:\n"
        f"{{\n"
        f"  total_score: number (0-100),\n"
        f"  approved: boolean (true only if total_score >= {PASS_THRESHOLD}),\n"
        f"  rules_checked: [\n"
        f"    {{id: number, passed: boolean, reasoning: string}}\n"
        f"  ],\n"
        f"  critical_failures: [string] (weight-3 rules that failed),\n"
        f"  fix_instructions: [string] (specific actions to fix),\n"
        f"  explanation: string (2-3 sentence summary of WHY the overall score "
        f"is what it is — what dragged it down or what was strong),\n"
        f"  verdict: string (one-line summary)\n"
        f"}}"
    )


# ═══════════════════════════════════════════════════════════════
#  PRE-VISUAL VALIDATOR (Phase 8.7 — before image generation)
# ═══════════════════════════════════════════════════════════════

class PreVisualValidator(Agent):
    """Validates content, author, architecture, guardrails, and format
    rules that can be checked from the brief/design/story alone —
    BEFORE spending money on image generation."""

    def __init__(self):
        super().__init__(
            name="Pre-Visual Validator",
            role="Content & structure quality gate — runs before image generation",
            model="gpt-4o",
            system_prompt=_build_validator_prompt(
                PRE_VISUAL_RULES, "PRE-VISUAL"),
        )

    def validate(self, brief: dict, design: dict, story: dict,
                 agent_rounds: dict) -> dict:
        return self.think(
            "Validate the content, structure, and architecture BEFORE images "
            "are generated. You are checking whether the CONTENT is ready. "
            "Do NOT check visuals/layout/images — that comes later.\n\n"
            "For each failed rule, explain exactly WHY it failed and what "
            "specific evidence you examined.",
            context={
                "brief": brief,
                "design": design,
                "story": story,
                "agent_argument_rounds": agent_rounds,
                "author_name": "Bhasker Kumar",
                "assistant_name": "Orion Cael",
                "guardrail_text": GUARDRAIL,
                "guardrail_locations": [
                    "EditorInChief (layer 1)",
                    "ContentWriter (layer 2)",
                    "ContentReviewer (layer 3)",
                ],
            },
            max_tokens=4000,
        )


# ═══════════════════════════════════════════════════════════════
#  POST-VISUAL VALIDATOR (Phase 12 — after PDF is generated)
# ═══════════════════════════════════════════════════════════════

class PostVisualValidator(Agent):
    """Validates layout, visuals, design quality, and typography —
    things that only exist once images and the PDF are produced."""

    def __init__(self):
        super().__init__(
            name="Post-Visual Validator",
            role="Visual & layout quality gate — runs after PDF generation",
            model="gpt-4o",
            system_prompt=_build_validator_prompt(
                POST_VISUAL_RULES, "POST-VISUAL"),
        )

    def validate(self, brief: dict, design: dict, story: dict,
                 visuals_count: int, audit_result: dict) -> dict:
        return self.think(
            "Validate the VISUAL and LAYOUT aspects of the PDF. "
            "Content quality was already checked in the pre-visual pass. "
            "Focus ONLY on: images present, layout balance, design quality, "
            "typography, backgrounds, cover excitement, author prominence.\n\n"
            "For each failed rule, explain exactly WHY it failed and what "
            "specific evidence you examined.",
            context={
                "brief": brief,
                "design": design,
                "story": story,
                "visuals_generated": visuals_count,
                "visual_types_used": [
                    "DALL-E 3 (cover + section images)",
                    "Background images per page",
                    "Foreground content-aware images per page",
                ],
                "screen_audit": audit_result,
                "pdf_format": "portrait poster (612x792 pts, 8.5x11 inches)",
                "artistic_backgrounds": (
                    "6 rotating styles (gradient, diagonal, wash, "
                    "color-block, mesh, radial) on every page"
                ),
            },
            max_tokens=4000,
        )


# ═══════════════════════════════════════════════════════════════
#  LEGACY — keep FinalValidatorAgent for backward compatibility
# ═══════════════════════════════════════════════════════════════

class FinalValidatorAgent(Agent):
    """Legacy combined validator — now unused by the orchestrator
    but kept so old code doesn't break on import."""

    def __init__(self):
        super().__init__(
            name="Final Validator",
            role="Master quality gate",
            model="gpt-4o",
            system_prompt="Legacy validator — see PreVisualValidator / PostVisualValidator.",
        )

    def validate(self, **kwargs) -> dict:
        return {"total_score": 0, "approved": False,
                "verdict": "Use PreVisualValidator + PostVisualValidator instead."}
