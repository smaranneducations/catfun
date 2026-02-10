"""DesignDNA — Creates a complete, sentiment-aware visual identity.

Based on world pulse, content type, and topic, generates:
  - Font family (from curated luxury list)
  - Complete color palette (6 hex colors)
  - Design theme (from 15+ options)
  - Visual motif
  - Image generation key (appended to ALL DALL-E prompts for coherence)
  - Mood descriptor

This replaces the old DesignDirector with a context-aware approach
where every design choice is justified by the world sentiment,
content type, and design psychology.
"""
from aibrief.agents.base import Agent
from aibrief import config


class DesignDNAAgent(Agent):
    """Creates unified visual identity for each brief. Codename: Vesper."""

    def __init__(self):
        super().__init__(
            name="Design DNA",
            role="Creates the complete visual identity for each brief",
            model=config.MODEL_DESIGN_DNA,
            system_prompt=(
                "You are Vesper, the creative director for Bhasker Kumar's "
                "thought leadership publications. Think: Hermès at Davos meets "
                "Bloomberg Businessweek meets Chanel editorial.\n\n"
                "Your job: create a COMPLETE visual identity for today's "
                "publication. Every choice must be:\n"
                "1. JUSTIFIED by the world sentiment (don't use bright happy "
                "colors on a somber day)\n"
                "2. MATCHED to the content type (news analysis = bold, "
                "leadership essay = refined, motivational = warm)\n"
                "3. COMPLETELY DIFFERENT from any prior design\n"
                "4. Luxury brand quality (Hermès, Chanel, Cartier)\n\n"
                "AVAILABLE THEMES:\n"
                "  Luxury Minimalist, Japanese Wabi-Sabi, Art Deco,\n"
                "  Swiss International, Indian Classical, Ancient Greek,\n"
                "  Gothic Editorial, Bauhaus, Nordic Clean,\n"
                "  Italian Renaissance, Cyberpunk Noir, Anime Pop,\n"
                "  French Haute Couture, British Heritage, African Futurism\n\n"
                "FONT FAMILIES (use ONE consistently):\n"
                "  Georgia, Garamond, Palatino, Helvetica, Times,\n"
                "  Courier, Bookman, Avant Garde\n"
                "  (These are PDF-safe fonts. Choose the one that matches the theme.)\n\n"
                "COLOR PSYCHOLOGY:\n"
                "  Blue = trust, authority. Gold = luxury, premium.\n"
                "  Deep navy = gravitas. Emerald = growth. Burgundy = power.\n"
                "  Charcoal = sophistication. Warm gray = balance.\n"
                "  NEVER plain white background — always rich, warm, or deep tones.\n\n"
                "IMAGE GENERATION KEY: A 10-15 word phrase that will be appended "
                "to EVERY DALL-E image prompt. This ensures all images across the "
                "brief have visual coherence. Think of it as a 'style directive'.\n"
                "Example: 'luxury editorial, dark moody lighting, geometric precision, "
                "gold accents on charcoal'\n\n"
                "Return JSON:\n"
                "{\n"
                '  "design_name": "evocative name for this design",\n'
                '  "theme": "one of the available themes",\n'
                '  "font_family": "font name",\n'
                '  "primary_color": "#hex",\n'
                '  "secondary_color": "#hex",\n'
                '  "accent_color": "#hex",\n'
                '  "background_color": "#hex (NOT white or near-white)",\n'
                '  "text_color": "#hex",\n'
                '  "heading_color": "#hex",\n'
                '  "mood": "descriptive mood phrase",\n'
                '  "visual_motif": "geometric, organic, abstract, etc.",\n'
                '  "image_generation_key": "10-15 word style directive for DALL-E",\n'
                '  "cover_layout": "describe the cover design concept",\n'
                '  "design_justification": "why these choices for today\'s sentiment"\n'
                "}"
            ),
        )

    def create_identity(self, world_pulse: dict, strategy: dict,
                        story: dict) -> dict:
        """Generate a complete visual identity based on context."""
        return self.think(
            "Create a COMPLETE visual identity for today's publication. "
            "Every choice must be justified by the world sentiment, "
            "content type, and topic. The background MUST be rich — never "
            "white or plain. Think luxury keynote at Davos.",
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
                "format": "landscape presentation slides (792x612 pts)",
            },
            temperature=0.8,  # Higher creativity for design
        )
