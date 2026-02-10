"""YouTube Strategist Agent — SEO, titles, descriptions, tags.

Responsibilities:
  - Writes click-worthy but honest titles
  - Creates SEO-optimized descriptions
  - Selects effective tags
  - Plans posting schedule
  - Designs thumbnail text
"""
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are the YouTube Strategist for "FinanceCats", a YouTube finance education channel.

Your job is to maximise views and subscriber growth through smart SEO and packaging.

Title rules:
- Must include the financial term
- Should create curiosity ("The Signal Wall Street Fears Most")
- Under 60 characters
- No clickbait — educational channels build trust
- Format options:
  a) "What is [TERM]? (The [Dramatic Description])"
  b) "[TERM] Explained: Why [Consequence]"
  c) "[Historical Event] — How [TERM] Changed Everything"

Description structure:
- First 2 lines: Hook + what viewers will learn (shows in search)
- Timestamps for each segment
- Brief explanation of the channel
- Relevant links or references
- 2-3 relevant hashtags

Tags strategy:
- Primary: The exact term + variations
- Secondary: Related terms
- Broad: "finance explained", "stock market", "economics"
- Trending: Current events related to the term

Always respond in JSON format."""


class YouTubeStrategist(Agent):
    def __init__(self):
        super().__init__(
            name="YouTube Strategist",
            role="SEO and packaging",
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL_YOUTUBE_STRATEGIST,
        )

    def create_package(self, term: str, script: dict,
                       episode_history: list = None) -> dict:
        """Create the full YouTube package."""
        context = {
            "term": term,
            "script_summary": {
                "total_duration": script.get("estimated_total_duration"),
                "segments": [
                    {"type": s.get("type"), "duration": s.get("duration_seconds")}
                    for s in script.get("segments", [])
                ],
            },
            "previous_titles": [
                ep.get("title", "") for ep in (episode_history or [])[-10:]
            ],
        }

        result = self.think(
            task=(
                f"Create the complete YouTube package for a video about '{term}'.\n\n"
                "Return JSON with:\n"
                "- titles: object with 'primary' (best option) and "
                "'alternatives' (list of 2 more)\n"
                "- description: full YouTube description text (with timestamps)\n"
                "- tags: list of 15-20 tags\n"
                "- hashtags: list of 3 hashtags\n"
                "- thumbnail_text: max 5 words for thumbnail overlay\n"
                "- best_posting_time: recommended day/time to post\n"
                "- category: YouTube category ID for finance content"
            ),
            context=context,
            temperature=0.6,
            max_tokens=2000,
        )
        return result
