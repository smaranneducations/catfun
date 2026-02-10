"""Creative Director Agent — Visual design decisions.

Responsibilities:
  - Selects a cat image from the 30-cat repository
  - Designs the on-screen text overlay layout
  - Specifies blur intensity and visual transitions
  - Plans thumbnail composition
  - Ensures visual consistency across episodes
"""
import os
import random
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are the Creative Director for "FinanceCats", a YouTube finance education channel.

You handle all visual decisions for each video:
1. SELECT a cat from our repository of 30 professional cat photos
2. DESIGN the on-screen text overlays (fonts, positions, colours)
3. PLAN the blur effect for background when cat speaks
4. DESIGN the thumbnail concept

Visual brand guidelines:
- Cat is positioned on the RIGHT side of the screen (roughly 30% width)
- Text overlays on the LEFT side (roughly 60% width)
- Blurred background uses a freeze frame from the news clip
- Blur intensity: strong gaussian (radius 20-30px)
- Semi-transparent dark overlay behind text for readability
- Colour scheme: Dark blue/navy background tones, white text, gold accent for key terms
- Font: Clean sans-serif (Arial/Helvetica style)
- Key term always highlighted in gold/yellow
- Bullet points use subtle dot markers

Thumbnail guidelines:
- Must be readable at small size (mobile)
- Cat face prominent on one side
- Key term in large, bold text
- Dramatic background from the news clip
- Max 5 words of text

Always respond in JSON format."""


class CreativeDirector(Agent):
    def __init__(self):
        super().__init__(
            name="Creative Director",
            role="Visual design and cat selection",
            system_prompt=SYSTEM_PROMPT,
            model=config.LLM_MODEL_MINI,
        )

    def select_cat(self, recently_used_cats: list[str] = None) -> dict:
        """Select a cat image from the repository."""
        available_cats = []
        if os.path.exists(config.CATS_DIR):
            available_cats = [
                f for f in os.listdir(config.CATS_DIR)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            ]

        if not available_cats:
            print("    [Creative Director] No cat images in repository!")
            return {"cat_id": "placeholder", "cat_path": "", "note": "No cats generated yet"}

        # Exclude recently used cats
        recently_used = set(recently_used_cats or [])
        eligible = [c for c in available_cats if c not in recently_used]

        # If all cats are recently used, reset
        if not eligible:
            eligible = available_cats

        # Random selection
        chosen = random.choice(eligible)
        cat_path = os.path.join(config.CATS_DIR, chosen)

        print(f"    [Creative Director] Selected cat: {chosen}")
        return {
            "cat_id": chosen,
            "cat_path": cat_path,
        }

    def design_overlays(self, term: str, script: dict) -> dict:
        """Design the visual overlay specifications for each segment."""
        result = self.think(
            task=(
                f"Design the visual overlays for a video about '{term}'.\n\n"
                "For each cat-narrated segment (cat_intro, lecture sections, cat_wrapup), "
                "specify:\n"
                "1. text_layout: where text appears (positions as % of screen)\n"
                "2. highlight_color: colour for the key term (hex)\n"
                "3. bullet_style: how bullet points look\n"
                "4. transition: how we enter/exit the segment\n\n"
                "Also design:\n"
                "- thumbnail: text (max 5 words), layout description, mood\n"
                "- blur_radius: pixel radius for background blur (20-30)\n"
                "- overlay_opacity: 0.0-1.0 for dark overlay behind text\n\n"
                "Return JSON with: overlay_specs, thumbnail_design, blur_radius, "
                "overlay_opacity"
            ),
            context={"term": term, "segments": script.get("segments", [])},
            temperature=0.5,
            max_tokens=2000,
        )
        return result
