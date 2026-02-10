"""Creative Director Agent — Visual design decisions.

V2: Selects TWO cats (one for each character) and designs dual-cat layout.

Responsibilities:
  - Selects two distinct cat images from the repository
  - Designs the on-screen text overlay layout for two-cat format
  - Specifies blur intensity and visual transitions
  - Plans thumbnail composition with both cats
  - Ensures visual consistency across episodes
"""
import os
import random
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are the Creative Director for "FinanceCats", a YouTube finance education channel.

Each video features TWO cat characters having a conversation:
  - Cat A (Professor Whiskers): The knowledgeable explainer (positioned LEFT)
  - Cat B (Cleo): The curious questioner (positioned RIGHT)

You handle all visual decisions for each video:
1. SELECT two distinct cats from our repository of 30 professional cat photos
2. DESIGN the on-screen text overlays (fonts, positions, colours)
3. PLAN the blur effect for background when cats speak
4. DESIGN the thumbnail concept with both cats

Visual brand guidelines:
- Cat A (Professor) on the LEFT side (~25% width), Cat B (Cleo) on the RIGHT side (~25%)
- Text overlays in the CENTRE (~40% width, between the cats)
- Active speaker is highlighted (brighter), inactive speaker is slightly dimmed
- Speaker name label below each cat
- Blurred background uses a freeze frame from the news clip
- Blur intensity: strong gaussian (radius 20-30px)
- Semi-transparent dark overlay behind text for readability
- Colour scheme: Dark blue/navy background tones, white text, gold accent for key terms
- Font: Clean sans-serif (Arial/Helvetica style)
- Key term always highlighted in gold/yellow
- Bullet points use subtle dot markers

Thumbnail guidelines:
- Both cats visible, facing each other (conversation feel)
- Key term in large, bold text between them
- Dramatic background from the news clip
- Max 5 words of text
- Must be readable at small size (mobile)

Always respond in JSON format."""


class CreativeDirector(Agent):
    def __init__(self):
        super().__init__(
            name="Creative Director",
            role="Visual design and dual-cat selection",
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL_CREATIVE_DIRECTOR,
        )

    def select_cats(self, recently_used_cats: list[str] = None) -> dict:
        """Select TWO distinct cat images from the repository.

        Returns dict with cat_a (Professor) and cat_b (Cleo) info.
        """
        available_cats = []
        if os.path.exists(config.CATS_DIR):
            available_cats = [
                f for f in os.listdir(config.CATS_DIR)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            ]

        if not available_cats:
            print("    [Creative Director] No cat images in repository!")
            return {
                "cat_a": {"cat_id": "placeholder", "cat_path": ""},
                "cat_b": {"cat_id": "placeholder", "cat_path": ""},
            }

        # Exclude recently used cats
        recently_used = set(recently_used_cats or [])
        eligible = [c for c in available_cats if c not in recently_used]

        # If too few eligible, reset
        if len(eligible) < 2:
            eligible = available_cats

        # Pick two distinct cats
        chosen = random.sample(eligible, min(2, len(eligible)))

        # If only one cat available, use it for both (edge case)
        if len(chosen) == 1:
            chosen.append(chosen[0])

        cat_a_path = os.path.join(config.CATS_DIR, chosen[0])
        cat_b_path = os.path.join(config.CATS_DIR, chosen[1])

        print(f"    [Creative Director] Cat A (Professor): {chosen[0]}")
        print(f"    [Creative Director] Cat B (Cleo): {chosen[1]}")

        return {
            "cat_a": {
                "cat_id": chosen[0],
                "cat_path": cat_a_path,
                "name": config.CAT_A_NAME,
                "role": "explainer",
            },
            "cat_b": {
                "cat_id": chosen[1],
                "cat_path": cat_b_path,
                "name": config.CAT_B_NAME,
                "role": "questioner",
            },
        }

    def design_overlays(self, term: str, script: dict) -> dict:
        """Design the visual overlay specifications for dual-cat layout."""
        result = self.think(
            task=(
                f"Design the visual overlays for a two-cat conversation video about '{term}'.\n\n"
                "Layout: Cat A (Professor) on LEFT, Cat B (Cleo) on RIGHT, text in CENTRE.\n\n"
                "For each segment (cat_intro, conversation exchanges, cat_wrapup), specify:\n"
                "1. text_layout: where text appears (positions as % of screen)\n"
                "2. highlight_color: colour for the key term (hex)\n"
                "3. active_speaker_brightness: how much brighter the active speaker is\n"
                "4. speaker_labels: name labels under each cat\n"
                "5. transition: how we enter/exit the segment\n\n"
                "Also design:\n"
                "- thumbnail: text (max 5 words), layout with both cats, mood\n"
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
