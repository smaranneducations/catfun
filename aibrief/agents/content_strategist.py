"""ContentStrategist — Decides content TYPE and tone based on world pulse.

Output is ALWAYS poster format with 3 content pages.
The strategist decides:
  - Content type (from 12+ options)
  - Tone
  - Topic direction

Page count is FIXED at 3 content pages (plus cover, agent credits, mind map).
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
            role="Decides content type and tone based on world sentiment",
            model=config.MODEL_CONTENT_STRATEGIST,
            system_prompt=(
                "You are Marcus, the content strategist for Bhasker Kumar — "
                "a globally recognised AI thought leader who keynotes Davos "
                "and advises heads of state.\n\n"
                "Your job: decide WHAT to publish today.\n\n"
                "CRITICAL ANCHOR (non-negotiable):\n"
                "Everything published must reinforce Bhasker Kumar as THE voice "
                "on AI's impact on business, leadership, and human experience. "
                "This is not a general news outlet. This is a thought leader's "
                "personal publication. Every piece must connect to AI.\n\n"
                "FORMAT: Always poster format. 3 content pages. Fixed.\n\n"
                "CONTENT TYPE SELECTION RULES:\n"
                "- EXTREME_SAD: 'Silent' (don't post) or 'Calming Perspective'\n"
                "- ANXIOUS: 'Calming Perspective' or 'Data-Driven Analysis'\n"
                "- NORMAL: Full range available. Prefer variety.\n"
                "- OPTIMISTIC: 'Bold Prediction' or 'Breaking News Analysis'\n"
                "- EUPHORIC: 'Breaking News Analysis' or 'Contrarian Take' "
                "(ground the hype)\n\n"
                "VARIETY RULE: Never repeat the same content type twice in a row. "
                "Deliberately choose something different from recent posts.\n\n"
                "Return JSON:\n"
                "{\n"
                '  "content_type": "exact type name from the list",\n'
                '  "tone": "descriptive tone for this piece",\n'
                '  "topic_direction": "what kind of topic to look for",\n'
                '  "reasoning": "why this content type for today\'s sentiment",\n'
                '  "anchor_connection": "how this connects to AI thought leadership"\n'
                "}"
            ),
        )

    def strategize(self, world_pulse: dict, recent_types: list[str] = None) -> dict:
        """Choose content type based on world pulse."""
        ctx = {
            "world_pulse": world_pulse,
            "available_content_types": CONTENT_TYPES,
        }
        if recent_types:
            ctx["recent_content_types_posted"] = recent_types

        result = self.think(
            "Based on the current world pulse, decide what content type "
            "to publish today. Remember: this is Bhasker Kumar's personal "
            "AI thought leadership publication. Every choice must reinforce "
            "that positioning. Choose wisely.",
            context=ctx,
        )

        # Fixed: always poster, always 3 content pages
        result["output_format"] = "poster"
        result["page_count"] = 3

        ct = result.get("content_type", "")
        print(f"  [Marcus] Content type: {ct}")
        print(f"  [Marcus] Tone: {result.get('tone', '?')}")
        print(f"  [Marcus] Format: poster (3 content pages)")
        return result
