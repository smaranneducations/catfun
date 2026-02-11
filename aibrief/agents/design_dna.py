"""DesignDNA — Emotion detection + hardcoded design resolution.

The LLM's ONLY job is to detect the dominant EMOTION of the news story.
Everything else (style, palette, font, image keywords) comes from the
hardcoded EMOTION_DESIGN_MAP in design_catalog.py.

This eliminates the LLM's tendency to always pick the same style.

Flow:
  1. Agent reads headline + summary → returns ONE emotion word
  2. design_catalog.resolve_design(emotion) → full design config
  3. Imagen prompt built from: hardcoded theme + dynamic topic
"""
from aibrief.agents.base import Agent
from aibrief import config
from aibrief.pipeline.design_catalog import (
    VALID_EMOTIONS, resolve_design, lookup_palette,
)


class DesignDNAAgent(Agent):
    """Detects emotion, then resolves hardcoded design. Codename: Vesper."""

    def __init__(self):
        emotions_list = ", ".join(VALID_EMOTIONS)
        super().__init__(
            name="Design DNA",
            role="Detects the dominant emotion of the news to drive visual design",
            model=config.MODEL_DESIGN_DNA,
            system_prompt=(
                "You are Vesper, an emotion analyst. Your ONLY job is to read "
                "a news story and determine the SINGLE dominant emotion it "
                "evokes in the reader.\n\n"
                f"VALID EMOTIONS (pick EXACTLY ONE): {emotions_list}\n\n"
                "RULES:\n"
                "1. Read the headline, summary, and context\n"
                "2. Determine: what does the READER feel when reading this?\n"
                "3. Return ONLY the emotion word — nothing else\n"
                "4. If unsure, pick 'trust' (safe default)\n\n"
                "EMOTION GUIDE:\n"
                "  trust      — corporate deals, partnerships, stability\n"
                "  excitement — breakthroughs, launches, records, celebrations\n"
                "  calm       — routine updates, mild progress, steady growth\n"
                "  urgency    — breaking news, deadlines, critical events\n"
                "  fear       — risks, warnings, market crashes, threats\n"
                "  anger      — injustice, scandals, conflicts, outrages\n"
                "  sadness    — tragedies, losses, memorials, grief\n"
                "  hope       — recovery, progress, optimism, new beginnings\n"
                "  mystery    — investigations, unknowns, surprising reveals\n"
                "  rebellion  — disruptions, protests, counter-culture, defiance\n\n"
                "Return JSON:\n"
                "{\n"
                '  "emotion": "one word from the list above",\n'
                '  "reasoning": "one sentence why this emotion"\n'
                "}"
            ),
        )

    def create_identity(self, world_pulse: dict, strategy: dict,
                        story: dict) -> dict:
        """Detect emotion → resolve full design from hardcoded map."""

        # Step 1: Ask LLM to detect emotion only
        result = self.think(
            "Read this news story and tell me the SINGLE dominant emotion "
            "a reader would feel. Return ONLY the emotion word from the "
            "valid list.",
            context={
                "headline": story.get("headline", ""),
                "summary": story.get("summary", ""),
                "why_viral": story.get("why_viral", ""),
                "world_mood": world_pulse.get("mood", "normal"),
                "content_type": strategy.get("content_type", ""),
            },
            temperature=0.3,  # Low temp for consistent classification
        )

        emotion = result.get("emotion", "trust").lower().strip()
        reasoning = result.get("reasoning", "")
        print(f"  [Vesper] Detected emotion: {emotion}")
        print(f"  [Vesper] Reasoning: {reasoning}")

        # Step 2: Resolve full design from hardcoded map
        design = resolve_design(emotion)

        # Step 3: Build the complete design dict for downstream
        palette = lookup_palette(design["palette_id"])

        full_design = {
            "emotion": emotion,
            "emotion_reasoning": reasoning,
            "style_id": design["style_id"],
            "palette_id": design["palette_id"],
            "font_id": design["font_id"],
            "design_name": design["design_name"],
            "mood": design["mood"],
            "imagen_style": design["imagen_style"],
            "bg_motifs": design["bg_motifs"],
            "fg_mood": design["fg_mood"],
            "image_generation_key": (
                f"{design['imagen_style']}, {design['fg_mood']}"
            ),
            "visual_motif": design["bg_motifs"],
            # Colors from palette
            "primary_color": palette["primary"],
            "secondary_color": palette["secondary"],
            "accent_color": palette["accent"],
            "background_color": palette["background"],
            "text_color": palette["text"],
            "heading_color": palette["heading"],
        }

        print(f"  \u25b8 Design: {full_design['design_name']}")
        print(f"  \u25b8 Style: {full_design['style_id']}")
        print(f"  \u25b8 Palette: {full_design['palette_id']}")
        print(f"  \u25b8 Font: {full_design['font_id']}")
        print(f"  \u25b8 Imagen style: {full_design['imagen_style']}")

        return full_design
