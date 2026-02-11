"""ContentStrategist — Decides content TYPE and tone based on world pulse.

Output is ALWAYS poster format:
  Page 1: Cover
  Page 2: News Summary (6 bullet points)
  Pages 3-6: Content (5 points each)
  Then: Agent credits, Run info, Decision architecture
"""
from aibrief.agents.base import Agent
from aibrief import config

CONTENT_TYPES = [
    "Breaking News Analysis — a major event just happened, analyze it now",
    "Historical Retrospective — connecting past to present, patterns and parallels",
    "Contrarian Take — challenging conventional wisdom, the unpopular smart take",
    "Trend Roundup — 3-5 trends shaping the world right now",
    "Bold Prediction — forward-looking forecast with conviction",
    "Deep Explainer — one complex topic made accessible to executives",
    "Leadership Essay — what leaders should do about this development",
    "Calming Perspective — grounding anxieties with facts and context",
    "Data-Driven Analysis — numbers and evidence about real-world impact",
    "Motivational — inspiring action in a rapidly changing world",
    "Human Psychology — cognitive biases and decision-making lessons",
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
                "a globally recognised thought leader who keynotes Davos "
                "and advises heads of state.\n\n"
                "Your job: decide WHAT to publish today.\n\n"
                "CONTENT FOCUS:\n"
                "We publish about the TOP TRENDING news of the day — ANY topic. "
                "Whatever the world is talking about most right now. "
                "This is a thought leader's personal publication that provides "
                "unique perspectives on the most viral global stories.\n\n"
                "FORMAT: Always poster format. 1 news summary (6 pts) + 4 content pages (5 pts each). Fixed.\n\n"
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

        # Fixed: always poster, always 4 content pages (2 findings each)
        result["output_format"] = "poster"
        result["page_count"] = 4

        ct = result.get("content_type", "")
        print(f"  [Marcus] Content type: {ct}")
        print(f"  [Marcus] Tone: {result.get('tone', '?')}")
        print(f"  [Marcus] Format: poster (4 content pages, 2 findings each)")
        return result
