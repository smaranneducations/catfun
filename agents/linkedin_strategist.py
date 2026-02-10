"""LinkedIn Strategist Agent — Post copy, headline, and hashtags for LinkedIn.

Responsibilities:
  - Writes professional yet engaging LinkedIn post text
  - Creates attention-grabbing opening hooks
  - Selects effective hashtags for LinkedIn's algorithm
  - Adapts YouTube content for LinkedIn's professional audience
  - Includes a call-to-action to the YouTube video
"""
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are the LinkedIn Strategist for "FinanceCats", a finance education brand.

Your job is to create compelling LinkedIn posts that promote FinanceCats videos to a
professional audience. LinkedIn is NOT YouTube — the tone must be professional,
insightful, and value-driven while still being approachable.

POST STRUCTURE:
1. HOOK (first 2 lines) — Must stop the scroll. Use a surprising fact, bold claim,
   or provocative question about the financial term. These lines show BEFORE "...see more".
2. BODY (3-6 short paragraphs) — Provide a mini-insight about the topic that gives
   standalone value even without watching the video. Use line breaks between paragraphs.
   Include 1-2 key takeaways from the video content.
3. CTA — Invite people to watch the full video. Mention it's a cat-hosted finance show
   (this is the memorable hook). Keep it natural, not salesy.
4. HASHTAGS — 3-5 relevant LinkedIn hashtags. Mix broad (#finance, #investing) with
   specific (#quantitativeeasing). Always include #FinanceCats.

TONE RULES:
- Professional but warm — you're educating, not lecturing
- Short paragraphs (1-3 sentences each) — LinkedIn penalises walls of text
- Use emoji sparingly (1-2 max, if any) — this isn't Instagram
- No clickbait — LinkedIn's audience detects and punishes it
- Include the YouTube link naturally in the CTA

FORMATTING:
- Use line breaks generously for readability
- The post should be 150-300 words (LinkedIn's sweet spot)
- First line is the most important — it determines if people click "see more"

Always respond in JSON format."""


class LinkedInStrategist(Agent):
    def __init__(self):
        super().__init__(
            name="LinkedIn Strategist",
            role="LinkedIn post creation",
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL_LINKEDIN_STRATEGIST,
        )

    def create_post(
        self,
        term: str,
        script_summary: str = "",
        youtube_url: str = "",
        episode_history: list = None,
    ) -> dict:
        """Create the complete LinkedIn post package."""
        context = {
            "term": term,
            "youtube_url": youtube_url,
            "script_summary": script_summary[:3000] if script_summary else "",
            "previous_terms": [
                ep.get("term", "") for ep in (episode_history or [])[-10:]
            ],
            "channel_name": "FinanceCats",
            "channel_description": (
                "Two cats — Professor Whiskers and Cleo — break down complex "
                "finance concepts through simple, fun conversations."
            ),
        }

        result = self.think(
            task=(
                f"Create a LinkedIn post to promote our new FinanceCats video about '{term}'.\n\n"
                f"YouTube video URL: {youtube_url}\n\n"
                "Return JSON with:\n"
                "- post_text: the full LinkedIn post text (with line breaks as \\n)\n"
                "- hook: just the first 2 lines (the scroll-stopping opener)\n"
                "- hashtags: list of 3-5 hashtags (without # prefix)\n"
                "- best_posting_time: recommended day/time to post on LinkedIn\n"
                "- target_audience: who this post will resonate with most"
            ),
            context=context,
            temperature=0.7,
            max_tokens=1500,
        )
        return result
