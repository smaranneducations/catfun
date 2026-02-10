"""Script Writer Agent — Crafts the full video script.

Responsibilities:
  - Writes the complete 4-6.5 minute script following the segment structure
  - Integrates news clip context, term explanation, and historical stories
  - Maintains a clear British, educational tone
  - Creates natural transitions between segments
  - Ensures the cat narrator sounds knowledgeable but approachable
"""
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are the Script Writer for "FinanceCats", a YouTube finance education channel.

You write scripts for 4-6.5 minute videos where a professional cat character pauses
a real news clip to explain a complex financial term. Your scripts follow this EXACT structure:

SEGMENT 1 — NEWS HOOK (10-20 seconds)
  The original news clip plays. The anchor uses the target term.
  [No narration needed — just identify which part of the clip to use]

SEGMENT 2 — CAT INTRO (20-40 seconds)
  The cat appears on a blurred background. It introduces what we just heard,
  previews what we'll explain, and tells viewers what to watch for.
  Tone: Friendly, intriguing, "Did you catch that?"

SEGMENT 3 — NEWS CONTEXT (20-40 seconds)
  The original clip plays again — more context. Now the viewer knows what to listen for.
  [No narration — identify the clip segment]

SEGMENT 4 — THE LECTURE (120-200 seconds)
  The meat of the video. Blurred background, cat on screen, text overlays.
  Structure within the lecture:
    a) Simple definition (20-30s) — What the term actually means
    b) Historical Example 1 (30-45s) — A dramatic past event
    c) Historical Example 2 (30-45s) — Another event, different era
    d) Why it matters NOW (30-45s) — Connect to current news
  Use bullet points and key figures as on-screen text.

SEGMENT 5 — NEWS CLIP FINAL (15-25 seconds)
  Last bit of the original clip — now the viewer understands the context.
  [No narration — identify clip segment]

SEGMENT 6 — CAT WRAP-UP (15-25 seconds)
  Cat summarises the key takeaway in one sentence.
  Teases the next episode's term.
  Tone: Confident, warm, "Now you know."

WRITING RULES:
- British English spelling (favour, colour, realise)
- Short sentences. No jargon without immediate explanation.
- Every historical reference must have a specific date and number.
- The narration should sound like a calm, clear British professor.
- Each narration section should specify approximate speaking duration.
- Total video duration must be between 4:00 and 6:30.

Always respond in JSON format."""


class ScriptWriter(Agent):
    def __init__(self):
        super().__init__(
            name="Script Writer",
            role="Full video script creation",
            system_prompt=SYSTEM_PROMPT,
            model=config.LLM_MODEL,
        )

    def write_script(self, term: str, news_clip_info: dict,
                     historical_research: dict, transcript: str) -> dict:
        """Write the full video script."""
        context = {
            "term": term,
            "news_clip": news_clip_info,
            "historical_research": historical_research,
            "transcript_excerpt": transcript[:3000],
        }

        result = self.think(
            task=(
                f"Write a complete video script about '{term}'.\n\n"
                "The script must follow the 6-segment structure exactly.\n"
                "Total duration: 4:00 to 6:30 (vary naturally based on complexity).\n\n"
                "Return JSON with:\n"
                "- title_term: the financial term\n"
                "- estimated_total_duration: total seconds\n"
                "- segments: list of 6 segment objects, each containing:\n"
                "    - segment_id: 1-6\n"
                "    - type: 'news_clip' | 'cat_intro' | 'news_context' | 'lecture' | "
                "'news_clip_final' | 'cat_wrapup'\n"
                "    - duration_seconds: estimated duration\n"
                "    - For news_clip segments:\n"
                "        - clip_start: start time in source video (seconds)\n"
                "        - clip_end: end time in source video (seconds)\n"
                "    - For cat_intro segment:\n"
                "        - narration: full text the cat says\n"
                "        - bullet_points: list of 2-3 preview points shown on screen\n"
                "    - For lecture segment:\n"
                "        - sections: list of lecture sub-sections, each with:\n"
                "            - section_title: e.g. 'Simple Definition', 'The 2008 Crisis'\n"
                "            - narration: full text for this section\n"
                "            - key_points: list of 2-3 bullet points for on-screen text\n"
                "            - duration_seconds: seconds for this section\n"
                "    - For cat_wrapup segment:\n"
                "        - narration: wrap-up text\n"
                "        - key_takeaway: one-sentence takeaway for on-screen\n"
                "        - teaser_term: the term we'll cover next episode\n"
                "        - teaser_line: one teaser sentence about next episode"
            ),
            context=context,
            temperature=0.6,
            max_tokens=6000,
        )
        return result

    def revise_script(self, script: dict, feedback: str) -> dict:
        """Revise a script based on feedback."""
        result = self.think(
            task=(
                f"Revise this script based on feedback:\n\n"
                f"FEEDBACK: {feedback}\n\n"
                "Return the complete revised script in the same JSON format."
            ),
            context={"current_script": script},
            temperature=0.5,
            max_tokens=6000,
        )
        return result
