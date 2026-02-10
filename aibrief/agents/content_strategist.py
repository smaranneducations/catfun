"""ContentStrategist — Decides content TYPE and length based on world pulse.

Receives the WorldPulse output and decides:
  - Content type (from 12+ options)
  - Page count (2-10)
  - Tone
  - Topic direction

Always filtered through the AI thought leadership anchor.
"""
from aibrief.agents.base import Agent
from aibrief import config

CONTENT_TYPES = [
    "Breaking News Analysis — a major AI event just happened",
    "Historical Retrospective — connecting past to present through AI lens",
    "Contrarian Take — challenging conventional wisdom about AI",
    "Trend Roundup — 3-5 trends reshaping the AI landscape",
    "Bold Prediction — forward-looking AI forecast with conviction",
    "Deep Explainer — one AI concept made accessible to executives",
    "Leadership Essay — how to lead in the AI era",
    "Calming Perspective — grounding anxieties about AI with facts",
    "Data-Driven Analysis — numbers and evidence about AI's real impact",
    "Motivational (AI lens) — inspiring action in an AI-transformed world",
    "Human Psychology (AI lens) — cognitive biases in AI decision-making",
    "Silent — don't post today, sentiment is too extreme/sensitive",
]


class ContentStrategistAgent(Agent):
    """Decides what to publish today. Agent codename: Marcus."""

    def __init__(self):
        super().__init__(
            name="Content Strategist",
            role="Decides content type and length based on world sentiment",
            model=config.MODEL_CONTENT_STRATEGIST,
            system_prompt=(
                "You are Marcus, the content strategist for Bhasker Kumar — "
                "a globally recognised AI thought leader who keynotes Davos "
                "and advises heads of state.\n\n"
                "Your job: decide WHAT to publish today and HOW LONG it should be.\n\n"
                "CRITICAL ANCHOR (non-negotiable):\n"
                "Everything published must reinforce Bhasker Kumar as THE voice "
                "on AI's impact on business, leadership, and human experience. "
                "This is not a general news outlet. This is a thought leader's "
                "personal publication. Every piece must connect to AI.\n\n"
                "CONTENT TYPE SELECTION RULES:\n"
                "- EXTREME_SAD: 'Silent' (don't post) or 'Calming Perspective'\n"
                "- ANXIOUS: 'Calming Perspective' or 'Data-Driven Analysis'\n"
                "- NORMAL: Full range available. Prefer variety.\n"
                "- OPTIMISTIC: 'Bold Prediction' or 'Breaking News Analysis'\n"
                "- EUPHORIC: 'Breaking News Analysis' or 'Contrarian Take' "
                "(ground the hype)\n\n"
                "VARIETY RULE: Never repeat the same content type twice in a row. "
                "Deliberately choose something different from recent posts.\n\n"
                "PAGE COUNT GUIDE:\n"
                "- Breaking News Analysis: 6-10 pages (deep, multi-angle)\n"
                "- Historical Retrospective: 5-8 pages\n"
                "- Contrarian Take: 4-6 pages (punchy, provocative)\n"
                "- Trend Roundup: 6-8 pages (one trend per page)\n"
                "- Bold Prediction: 5-7 pages\n"
                "- Deep Explainer: 6-8 pages (build understanding)\n"
                "- Leadership Essay: 4-6 pages (elegant, concise)\n"
                "- Calming Perspective: 4-6 pages\n"
                "- Data-Driven Analysis: 6-10 pages (charts and evidence)\n"
                "- Motivational: 3-5 pages (short, punchy, inspiring)\n"
                "- Human Psychology: 5-7 pages\n\n"
                "OUTPUT FORMAT DECISION:\n"
                "You must also choose the output format:\n"
                "- 'slides': Landscape presentation deck (6-10 pages). Best for: "
                "analytical, multi-perspective, data-heavy, trend roundups, "
                "deep explainers, historical retrospectives.\n"
                "- 'poster': Portrait bold poster/banner (3-5 pages). Best for: "
                "motivational, bold predictions, contrarian takes, leadership essays, "
                "short punchy impact statements. Think Nike ad, Apple keynote, Vogue cover.\n\n"
                "GUIDELINE: If the content needs DEPTH and EVIDENCE → slides. "
                "If the content needs IMPACT and EMOTION → poster.\n\n"
                "Return JSON:\n"
                "{\n"
                '  "content_type": "exact type name from the list",\n'
                '  "output_format": "slides or poster",\n'
                '  "format_reasoning": "why this format fits the content type and mood",\n'
                '  "page_count": number (2-10),\n'
                '  "tone": "descriptive tone for this piece",\n'
                '  "topic_direction": "what kind of topic to look for",\n'
                '  "reasoning": "why this content type for today\'s sentiment",\n'
                '  "anchor_connection": "how this connects to AI thought leadership"\n'
                "}"
            ),
        )

    def strategize(self, world_pulse: dict, recent_types: list[str] = None) -> dict:
        """Choose content type and length based on world pulse."""
        ctx = {
            "world_pulse": world_pulse,
            "available_content_types": CONTENT_TYPES,
        }
        if recent_types:
            ctx["recent_content_types_posted"] = recent_types

        result = self.think(
            "Based on the current world pulse, decide what content type and "
            "length to publish today. Remember: this is Bhasker Kumar's personal "
            "AI thought leadership publication. Every choice must reinforce "
            "that positioning. Choose wisely.",
            context=ctx,
        )

        # Validate page count
        pc = result.get("page_count", 8)
        if not isinstance(pc, int) or pc < 2:
            pc = 6
        if pc > 10:
            pc = 10
        result["page_count"] = pc

        ct = result.get("content_type", "")
        print(f"  [Marcus] Content type: {ct}")
        print(f"  [Marcus] Pages: {pc}, Tone: {result.get('tone', '?')}")
        return result
