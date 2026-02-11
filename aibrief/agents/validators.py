"""FinalValidatorAgent — Checks ALL 36 master checkpoints before publishing.

This agent receives the completed PDF brief data and scores it against
every single rule the client has ever given. If score < 80%, it returns
specific failures and the PDF must be regenerated.

Also includes the guardrail text that must be embedded at 3 layers.
"""
import json
from aibrief.agents.base import Agent
from aibrief import config

# ═══════════════════════════════════════════════════════════════
#  THE GUARDRAIL — Must appear in Director, Content Writer,
#  AND Final Reviewer system prompts (3 places, not 1)
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
#  MASTER CHECKLIST — All 36 rules from the client
# ═══════════════════════════════════════════════════════════════
MASTER_CHECKLIST = [
    {"id": 1, "rule": "Every page has a visual element (DALL-E image, infographic, data viz, or artistic graphic)", "category": "visuals", "weight": 3},
    {"id": 2, "rule": "Layout is balanced — not too empty, not too crowded. Luxury fashion brand quality.", "category": "layout", "weight": 3},
    {"id": 3, "rule": "Design is COMPLETELY DIFFERENT from any prior version — unique palette, layout, motifs", "category": "design", "weight": 3},
    {"id": 4, "rule": "Uses creative tools: DALL-E images, Pillow infographics, data visualizations", "category": "visuals", "weight": 2},
    {"id": 5, "rule": "Author is 'Bhasker Kumar' — no fictional names", "category": "author", "weight": 3},
    {"id": 6, "rule": "Assistant name is 'Orion Cael' — the fixed agent author identity", "category": "author", "weight": 2},
    {"id": 7, "rule": "Credits mention agentic system with Claude, Gemini, and ChatGPT", "category": "author", "weight": 2},
    {"id": 8, "rule": "Agents actually argued and critiqued each other (not linear pipeline)", "category": "architecture", "weight": 3},
    {"id": 9, "rule": "Design quality matches luxury product website (Hermes, Chanel, LV level)", "category": "design", "weight": 3},
    {"id": 10, "rule": "Copy reads like luxury advertisement — polished, aspirational, premium", "category": "content", "weight": 3},
    {"id": 11, "rule": "No empty/dull dead space on any page bottom", "category": "layout", "weight": 3},
    {"id": 12, "rule": "Author and assistant text is PROMINENT and visible, not tiny", "category": "author", "weight": 3},
    {"id": 13, "rule": "ScreenRealEstateAgent reviewed the PDF", "category": "architecture", "weight": 2},
    {"id": 14, "rule": "Golden ratio (1.618) used for proportions", "category": "design_psychology", "weight": 2},
    {"id": 15, "rule": "Color psychology applied (blue=trust, gold=luxury, gray=authority)", "category": "design_psychology", "weight": 2},
    {"id": 16, "rule": "Typography hierarchy: 3+ levels (display, body, caption)", "category": "design_psychology", "weight": 2},
    {"id": 17, "rule": "Preparer/Reviewer pairs argued in multiple rounds", "category": "architecture", "weight": 3},
    {"id": 18, "rule": "Quality reflects genuine creative excellence, not just automation", "category": "meta", "weight": 3},
    {"id": 19, "rule": "PDF looks like PRESENTATION SLIDES (PPT style), not a text document", "category": "format", "weight": 3},
    {"id": 20, "rule": "Big commanding headers on every page (36pt+ display text)", "category": "format", "weight": 3},
    {"id": 21, "rule": "Bullet points used, NOT paragraphs. Short punchy text.", "category": "format", "weight": 3},
    {"id": 22, "rule": "EVERY page has exciting background — rich, artistic, never plain", "category": "layout", "weight": 3},
    {"id": 23, "rule": "Cover page (first slide) is SUPER exciting — dramatic, wow factor", "category": "layout", "weight": 3},
    {"id": 24, "rule": "Every page background has light artistic pattern/texture — subtle but present", "category": "layout", "weight": 3},
    {"id": 25, "rule": "Author 'Bhasker Kumar' on cover is >= 75% of header font size", "category": "author", "weight": 3},
    {"id": 26, "rule": "FinalValidatorAgent checked all 36 rules and scored 80%+", "category": "architecture", "weight": 3},
    {"id": 27, "rule": "Guardrail 'truth but never hurtful' is in Director, Writer, AND Reviewer (3 places)", "category": "guardrails", "weight": 3},
    {"id": 28, "rule": "No instructions were bypassed or shortcut", "category": "meta", "weight": 3},
    {"id": 29, "rule": "Content is neutral — never negative about individuals, constructively critical only", "category": "guardrails", "weight": 3},
    {"id": 30, "rule": "Each page has ONE clear idea", "category": "format", "weight": 2},
    {"id": 31, "rule": "User feedback log is maintained and comprehensive", "category": "meta", "weight": 2},
    {"id": 32, "rule": "LinkedIn post log tracks all posts to avoid repeats", "category": "meta", "weight": 1},
    {"id": 33, "rule": "Design agent imagination is unleashed — different style every time", "category": "design", "weight": 2},
    {"id": 34, "rule": "Multiple perspectives covered: history, economy, sociology, future", "category": "content", "weight": 2},
    {"id": 35, "rule": "Written as AI thought leader / head of consulting company", "category": "content", "weight": 2},
    {"id": 36, "rule": "LinkedIn expert uses proper Unicode formatting for bold/italic", "category": "linkedin", "weight": 1},
    {"id": 37, "rule": "STRICT: Max 1 point per slide. One powerful high-value statement + one insight. No lists of 4-6 bullets. Quality over quantity.", "category": "format", "weight": 3},
]


class FinalValidatorAgent(Agent):
    """Validates the complete output against ALL 36 master checkpoints.

    Rejects if score < 80%. Returns specific failures with fix instructions.
    """
    def __init__(self):
        checklist_text = "\n".join(
            f"  [{c['id']}] (weight:{c['weight']}) {c['rule']}"
            for c in MASTER_CHECKLIST
        )
        super().__init__(
            name="Final Validator",
            role="Master quality gate — checks all 36 client rules",
            model="gpt-4o",  # Must be the smartest model for this critical task
            system_prompt=(
                "You are the FINAL quality gate before a luxury PDF brief is published. "
                "You are the client's representative. You check EVERY SINGLE RULE the "
                "client has specified. You do NOT let anything slide.\n\n"
                f"{GUARDRAIL}\n\n"
                "MASTER CHECKLIST (36 rules):\n"
                f"{checklist_text}\n\n"
                "SCORING:\n"
                "- Check each rule: PASS (full weight) or FAIL (0 weight)\n"
                "- Calculate: (sum of passed weights / sum of all weights) * 100\n"
                "- PASS threshold: 80%\n"
                "- If < 80%: REJECT with specific failures and fix instructions\n"
                "- If >= 80%: APPROVE but still list any failures for improvement\n\n"
                "Return JSON:\n"
                "{\n"
                "  total_score: number (0-100),\n"
                "  approved: boolean (true only if total_score >= 80),\n"
                "  rules_checked: [\n"
                "    {id: number, passed: boolean, reasoning: string}\n"
                "  ],\n"
                "  critical_failures: [string] (rules with weight 3 that failed),\n"
                "  fix_instructions: [string] (specific actions to fix failures),\n"
                "  verdict: string (summary)\n"
                "}"
            ),
        )

    def validate(self, brief: dict, design: dict, story: dict,
                 visuals_count: int, audit_result: dict,
                 agent_rounds: dict) -> dict:
        """Run the full 36-point validation."""
        return self.think(
            "Validate this complete output against ALL 36 master checkpoints. "
            "Be extremely thorough. The client specifically said 'do not try to "
            "bypass me, build exactly as I say.' Check EVERY rule.\n\n"
            "EVIDENCE PROVIDED:\n"
            "- visuals_generated: number of DALL-E images + Pillow infographics created\n"
            "- assistant_name: the luxury brand name generated for 'Assisted by' credit\n"
            "- agent_argument_rounds: proof of multi-round arguments between agents\n"
            "- guardrail_locations: the 3 agents that have the ethical guardrail\n"
            "- screen_audit: ScreenRealEstateAgent audit results\n"
            "- format: landscape slide deck (PPT style)\n",
            context={
                "brief": brief,
                "design": design,
                "story": story,
                "visuals_generated": visuals_count,
                "visual_types_used": ["DALL-E 3 (cover + section images)", "Pillow stat cards", "Pillow timelines", "Pillow bar charts", "Pillow donut charts"],
                "screen_audit": audit_result,
                "agent_argument_rounds": agent_rounds,
                "author_name": "Bhasker Kumar",
                "assistant_name": brief.get("_assistant_name", "Luxury Name Generated"),
                "guardrail_text": GUARDRAIL,
                "guardrail_locations": ["EditorInChief (layer 1)", "ContentWriter (layer 2)", "ContentReviewer (layer 3)"],
                "pdf_format": "landscape slide deck (792x612 pts, 11x8.5 inches)",
                "artistic_backgrounds": "6 rotating styles (gradient, diagonal, wash, color-block, mesh, radial) on every page",
                "final_validator_running": True,
            },
            max_tokens=6000,
        )
