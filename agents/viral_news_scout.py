"""Viral News Scout Agent — Finds the most viral economic/geopolitical news.

V3: Instead of searching for a specific financial term's clip, we now
find the most VIRAL news story from the last 7 days in economics or
geopolitics. The financial term is then embedded into the anchor script
later — this ensures we always catch trending stories regardless of
whether they explicitly mention a textbook finance term.

Responsibilities:
  - Finds the top viral economic/geopolitical stories from the last 7 days
  - Ranks stories by virality (social media buzz, search trends, news coverage)
  - Returns structured story data: headline, summary, key facts, date, sources
  - Does NOT pick the financial term — that happens in the script writing phase
"""
import json
from datetime import datetime, timedelta
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are a Viral News Scout for "FinanceCats", a YouTube finance education channel.

Your ONLY job: Find the MOST VIRAL economic, financial, or geopolitical news story
from the LAST 7 DAYS. You are an expert at identifying what's dominating social media,
news cycles, and public conversation.

WHAT MAKES A STORY "VIRAL":
  - Everyone is talking about it (Twitter/X, Reddit, LinkedIn, news sites)
  - It affects everyday people (not just Wall Street insiders)
  - It has emotional impact (fear, outrage, hope, surprise)
  - Major publications have all covered it extensively
  - People are searching for it on Google

STORY CATEGORIES (in order of preference):
  1. Economic shocks (market crashes, inflation spikes, rate decisions, job reports)
  2. Geopolitical events with economic impact (trade wars, sanctions, conflicts)
  3. Corporate scandals/collapses (company failures, fraud revelations)
  4. Policy changes (tax changes, regulation, government spending)
  5. Technology disruptions (AI impact on jobs, crypto events, tech layoffs)

WHAT TO AVOID:
  - Stories older than 7 days (stale)
  - Niche stories that only specialists care about
  - Celebrity/entertainment news (even if it mentions money)
  - Crypto-only stories (unless they affect mainstream markets)

For each story, provide:
  - A compelling headline
  - A 3-4 sentence summary explaining what happened and why people care
  - Key facts (specific numbers, dates, names)
  - Why this story is viral RIGHT NOW
  - Which financial/economic concepts are at play (these will become teaching terms)

Always respond in JSON format."""


class ViralNewsScout(Agent):
    def __init__(self):
        super().__init__(
            name="Viral News Scout",
            role="Finds the most viral economic/geopolitical news",
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL_VIRAL_NEWS_SCOUT,
        )

    def find_viral_news(self, excluded_stories: list[str] = None) -> dict:
        """Find the most viral economic/geopolitical news from the last 7 days.

        Args:
            excluded_stories: List of story headlines already covered (avoid repeats)

        Returns:
            dict with:
              - stories: list of 3-5 ranked viral stories
              - top_pick: the #1 most viral story (recommended)
              - date_range: "YYYY-MM-DD to YYYY-MM-DD"
        """
        today = datetime.now()
        week_ago = today - timedelta(days=config.VIRAL_NEWS_LOOKBACK_DAYS)
        date_range = f"{week_ago.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}"

        context = {
            "today": today.strftime("%Y-%m-%d"),
            "lookback_days": config.VIRAL_NEWS_LOOKBACK_DAYS,
            "date_range": date_range,
            "excluded_stories": excluded_stories or [],
        }

        result = self.think(
            task=(
                f"Find the TOP 3-5 most VIRAL economic, financial, or geopolitical "
                f"news stories from the last {config.VIRAL_NEWS_LOOKBACK_DAYS} days "
                f"(from {date_range}).\n\n"
                f"Today's date is {today.strftime('%B %d, %Y')}.\n\n"
                "For EACH story, return:\n"
                "- headline: compelling, clear headline\n"
                "- summary: 3-4 sentences explaining what happened and why people care\n"
                "- key_facts: list of 4-6 specific facts (numbers, dates, names)\n"
                "- virality_reason: why this story is dominating the news cycle\n"
                "- virality_score: 1-10 (10 = absolutely everyone is talking about it)\n"
                "- affected_people: how this impacts everyday people\n"
                "- date: when this story broke (YYYY-MM-DD)\n"
                "- sources: list of major outlets covering it\n"
                "- related_finance_concepts: list of 3-5 financial/economic terms "
                "that relate to this story (e.g. 'inflation', 'tariffs', 'yield curve')\n"
                "  These will be candidates for the teaching term.\n\n"
                "IMPORTANT: Rank by VIRALITY — what is the #1 story that EVERYONE "
                "is talking about this week?\n\n"
                "Return JSON with:\n"
                "- stories: list of story objects (ranked by virality, highest first)\n"
                "- top_pick: object with 'headline' and 'reason' for the #1 recommendation\n"
                "- date_range: the date range searched"
            ),
            context=context,
            temperature=0.5,
            max_tokens=5000,
        )
        return result

    def pick_teaching_term(self, story: dict, covered_terms: list[str] = None) -> dict:
        """Given a viral news story, pick the best financial term to teach.

        The term should:
          1. Naturally connect to the story (can be embedded into anchor's script)
          2. Be educational — something viewers will learn from
          3. Not have been covered in recent episodes

        Args:
            story: The viral news story dict
            covered_terms: Terms already covered (avoid repeats)

        Returns:
            dict with: term, category, why_this_term, embedding_hint
        """
        context = {
            "story": story,
            "terms_already_covered": covered_terms or [],
        }

        result = self.think(
            task=(
                "Given this viral news story, pick the BEST financial/economic term "
                "to teach our audience.\n\n"
                "The term should:\n"
                "1. Naturally connect to the story — the anchor can mention it while "
                "   reporting the news without it feeling forced\n"
                "2. Be educational — most viewers won't know this term well\n"
                "3. Be specific enough to explain in 2-3 minutes (not too broad like "
                "   'economics' or too narrow like 'SOFR overnight rate')\n"
                "4. NOT be one we've already covered\n\n"
                "GOOD terms: 'tariffs', 'yield curve inversion', 'quantitative tightening', "
                "'stagflation', 'credit default swaps', 'debt ceiling', 'currency devaluation'\n"
                "BAD terms: 'the economy', 'stocks', 'money', 'trading'\n\n"
                "Return JSON with:\n"
                "- term: the chosen financial/economic term\n"
                "- category: broad category (Macro Economics, Markets & Trading, etc.)\n"
                "- why_this_term: why this term fits the viral story\n"
                "- embedding_hint: a sentence showing HOW the anchor can naturally "
                "  mention this term while reporting the news\n"
                "- simple_definition: a one-sentence plain-English definition\n"
                "- difficulty: 1-5 how complex to explain"
            ),
            context=context,
            temperature=0.5,
            max_tokens=2000,
        )
        return result
