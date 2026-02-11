"""DesignDNA — Creates a complete, sentiment-aware visual identity.

Now FORCED to pick from the design catalog:
  - style_id from 12 curated styles
  - palette_id from 10 curated color palettes
  - font_id from 10 curated fonts

The LLM chooses based on content context, world sentiment, and topic.
Every choice must be justified. This ensures:
  1. Forced variety (can never repeat the same look)
  2. Quality control (all options are pre-vetted)
  3. Technical reliability (fonts are tested)
"""
from aibrief.agents.base import Agent
from aibrief import config
from aibrief.pipeline.design_catalog import get_catalog_for_prompt


class DesignDNAAgent(Agent):
    """Creates unified visual identity for each brief. Codename: Vesper."""

    def __init__(self):
        catalog = get_catalog_for_prompt()
        super().__init__(
            name="Design DNA",
            role="Creates the complete visual identity for each brief",
            model=config.MODEL_DESIGN_DNA,
            system_prompt=(
                "You are Vesper, the creative director for Bhasker Kumar's "
                "thought leadership publications. Think: Hermès at Davos meets "
                "Bloomberg Businessweek meets Chanel editorial.\n\n"
                "Your job: pick a COMPLETE visual identity from the catalog below. "
                "You MUST pick from these lists — no freestyle.\n\n"
                f"{catalog}\n\n"
                "SELECTION RULES:\n"
                "1. Pick style_id based on the CONTENT TYPE and TOPIC (anime for "
                "energetic/fun, gothic for dramatic, luxury for authority, etc.)\n"
                "2. Pick palette_id based on the WORLD SENTIMENT (dark palettes "
                "for anxious times, warm for optimistic, cool for analytical)\n"
                "3. Pick font_id based on the STYLE (serif for classical, "
                "sans for modern, mono for tech). Use the recommended pairings "
                "as guidance but you CAN mix.\n"
                "4. NEVER repeat the same combination. Deliberately surprise.\n"
                "5. Justify EVERY choice with design psychology.\n\n"
                "You must also provide:\n"
                "- image_generation_key: 10-15 word phrase appended to ALL "
                "DALL-E prompts for visual coherence. Include the style's "
                "dall_e_hint essence.\n"
                "- design_name: an evocative name for this specific design\n\n"
                "Return JSON:\n"
                "{\n"
                '  "style_id": "from catalog",\n'
                '  "palette_id": "from catalog",\n'
                '  "font_id": "from catalog",\n'
                '  "design_name": "evocative name for this design",\n'
                '  "image_generation_key": "10-15 word DALL-E style directive",\n'
                '  "mood": "descriptive mood phrase",\n'
                '  "visual_motif": "geometric / organic / abstract / etc.",\n'
                '  "design_justification": "why these choices for today",\n'
                '  "primary_color": "#hex (from chosen palette)",\n'
                '  "secondary_color": "#hex",\n'
                '  "accent_color": "#hex",\n'
                '  "background_color": "#hex",\n'
                '  "text_color": "#hex",\n'
                '  "heading_color": "#hex"\n'
                "}"
            ),
        )

    def create_identity(self, world_pulse: dict, strategy: dict,
                        story: dict) -> dict:
        """Generate a complete visual identity from the catalog."""
        return self.think(
            "Pick a COMPLETE visual identity from the catalog. "
            "You MUST use style_id, palette_id, font_id from the lists. "
            "Every choice must be justified by the world sentiment, "
            "content type, and topic. The background MUST be rich — never "
            "white or plain. Think luxury keynote at Davos.\n\n"
            "CRITICAL: Pick something that MATCHES the content. "
            "If the topic is dramatic → gothic or heavy metal. "
            "If the topic is about innovation → cyberpunk or swiss. "
            "If the topic is about leadership → luxury or haute couture. "
            "Be bold. Surprise me.",
            context={
                "world_pulse": {
                    "mood": world_pulse.get("mood"),
                    "sentiment_score": world_pulse.get("sentiment_score"),
                    "recommended_tone": world_pulse.get("recommended_tone"),
                },
                "content_strategy": {
                    "content_type": strategy.get("content_type"),
                    "tone": strategy.get("tone"),
                    "page_count": strategy.get("page_count"),
                },
                "topic": {
                    "headline": story.get("headline", ""),
                    "why_viral": story.get("why_viral", ""),
                },
                "format": "portrait poster (612x792 pts, 3 content pages)",
            },
            temperature=0.9,  # High creativity for design
        )
