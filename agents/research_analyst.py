"""Research Analyst Agent — Finds trending finance news clips from top-tier newsrooms.

V2: Prioritises major news channels (CNBC, Bloomberg, BBC, CNN, etc.)
    to ensure professional, recognisable source footage.

Responsibilities:
  - Searches YouTube for recent finance news clips from leading newsrooms
  - Identifies clips where anchors use the target terminology
  - Validates clips have usable transcripts
  - Finds the exact timestamps where terms are mentioned
  - Returns ranked candidates with metadata
"""
import json
import os
from datetime import datetime, timedelta, timezone
import requests
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are a Research Analyst for "FinanceCats", a YouTube finance education channel.

Your job is to find the BEST news clip for our next video. The ideal clip:
1. MUST be from a MAJOR newsroom — CNBC, Bloomberg, BBC, CNN, Reuters, Fox Business,
   Yahoo Finance, Sky News, Al Jazeera, Financial Times, WSJ, The Economist, etc.
   NO small YouTubers, NO personal channels, NO crypto bros, NO reaction channels.
2. Has a news anchor or reporter clearly using/explaining the target financial term
3. Is recent (within last 6 months ideally)
4. Has clear audio and professional studio production
5. Is long enough to extract 60-90 seconds of usable footage
6. The moment where the term is used should be dramatic or important

When analyzing transcripts, identify:
- The EXACT timestamp where the term is first mentioned
- A "hook" moment — the most compelling 10-20 seconds to open with
- The best 20-40 second segment for additional context
- Any emotional/dramatic moments that make good TV

Always respond in JSON format."""


class ResearchAnalyst(Agent):
    def __init__(self):
        super().__init__(
            name="Research Analyst",
            role="News clip finder and validator",
            system_prompt=SYSTEM_PROMPT,
            model=config.LLM_MODEL,
        )

    def _is_preferred_channel(self, channel_name: str) -> bool:
        """Check if a channel is on our preferred list (fuzzy match)."""
        channel_lower = channel_name.lower()
        for preferred in config.PREFERRED_NEWS_CHANNELS:
            if preferred.lower() in channel_lower or channel_lower in preferred.lower():
                return True
        return False

    def _clean_query(self, query: str) -> str:
        """Remove Google-style operators that don't work with YouTube API."""
        import re
        # Remove site: operators
        query = re.sub(r'site:\S+', '', query)
        # Remove other search operators
        query = re.sub(r'(inurl|intitle|filetype):\S+', '', query)
        return query.strip()

    def search_youtube(self, queries: list[str], max_results_per_query: int = 10) -> list[dict]:
        """Search YouTube for finance news clips ONLY from top-tier channels.

        Searches broadly, then HARD-FILTERS to major newsrooms only.
        If no major newsroom clips found, retries with channel-specific queries
        before falling back (with a warning flag) to non-newsroom results.
        """
        if not config.YOUTUBE_API_KEY:
            print("    [Research Analyst] No YouTube API key — using LLM suggestions instead")
            return []

        all_results = []
        seen_ids = set()

        # Only search for clips published within the last N days
        cutoff = datetime.now(timezone.utc) - timedelta(days=config.MAX_CLIP_AGE_DAYS)
        published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Clean queries + add channel-specific queries for better newsroom hits
        cleaned = [self._clean_query(q) for q in queries]
        term_part = cleaned[0].split("2025")[0].split("2026")[0].strip() if cleaned else ""

        # Phase 1: Run original queries
        self._run_youtube_searches(cleaned, max_results_per_query, published_after,
                                   all_results, seen_ids)

        preferred = [r for r in all_results if r["is_major_newsroom"]]

        # Phase 2: If not enough major newsroom results, run channel-specific queries
        if len(preferred) < 3 and term_part:
            print(f"    [Research Analyst] Only {len(preferred)} major newsroom clips — "
                  f"running targeted newsroom searches...")
            newsroom_queries = [
                f"{term_part} CNBC",
                f"{term_part} Bloomberg",
                f"{term_part} BBC news",
                f"{term_part} CNN",
                f"{term_part} Reuters",
                f"{term_part} Fox Business",
                f"{term_part} Yahoo Finance",
                f"{term_part} Financial Times",
                f"{term_part} Sky News",
                f"{term_part} Wall Street Journal",
            ]
            self._run_youtube_searches(newsroom_queries, max_results_per_query,
                                       published_after, all_results, seen_ids)
            preferred = [r for r in all_results if r["is_major_newsroom"]]

        others = [r for r in all_results if not r["is_major_newsroom"]]

        print(f"    [Research Analyst] Found {len(all_results)} total candidates "
              f"({len(preferred)} from major newsrooms, "
              f"{len(others)} from other channels)")

        # HARD FILTER: Only return major newsroom clips
        if preferred:
            print(f"    [Research Analyst] Returning {len(preferred)} major newsroom clips ONLY "
                  f"(filtered out {len(others)} non-newsroom results)")
            return preferred

        # Last resort: if absolutely zero newsroom clips found, return others
        # with a warning flag so downstream code knows these are fallbacks
        if others:
            print(f"    [Research Analyst] WARNING: No major newsroom clips found! "
                  f"Returning {len(others)} non-newsroom clips as last resort.")
            for r in others:
                r["is_fallback_non_newsroom"] = True
            return others

        return []

    def _run_youtube_searches(self, queries: list[str], max_results: int,
                              published_after: str, results: list, seen_ids: set):
        """Execute a batch of YouTube search queries and accumulate results."""
        for query in queries:
            try:
                url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "order": "date",            # Most recent first
                    "maxResults": max_results,
                    "videoDuration": "medium",  # 4-20 minutes
                    "publishedAfter": published_after,
                    "key": config.YOUTUBE_API_KEY,
                }
                resp = requests.get(url, params=params)
                if resp.status_code != 200:
                    print(f"    [Research Analyst] YouTube API error: {resp.status_code}")
                    continue

                data = resp.json()
                for item in data.get("items", []):
                    vid_id = item["id"]["videoId"]
                    if vid_id not in seen_ids:
                        seen_ids.add(vid_id)
                        channel = item["snippet"]["channelTitle"]
                        results.append({
                            "video_id": vid_id,
                            "url": f"https://www.youtube.com/watch?v={vid_id}",
                            "title": item["snippet"]["title"],
                            "channel": channel,
                            "description": item["snippet"]["description"][:300],
                            "published_at": item["snippet"]["publishedAt"],
                            "is_major_newsroom": self._is_preferred_channel(channel),
                        })
            except Exception as e:
                print(f"    [Research Analyst] Search error for '{query}': {e}")

    def select_best_clip(self, term: str, candidates: list[dict],
                         transcripts: dict) -> dict:
        """Use LLM to select the best clip from candidates."""
        context = {
            "target_term": term,
            "candidates": candidates[:10],
            "available_transcripts": {
                vid_id: transcript[:2000]
                for vid_id, transcript in transcripts.items()
            },
        }

        result = self.think(
            task=(
                f"Select the BEST news clip for explaining '{term}'.\n"
                "Analyze each candidate and its transcript.\n"
                "STRONG PREFERENCE for major newsrooms (CNBC, Bloomberg, BBC, CNN, etc.).\n"
                "Pick the one where:\n"
                "1. The anchor clearly says and discusses the term\n"
                "2. The context is dramatic or newsworthy\n"
                "3. The clip is from a MAJOR, RECOGNISABLE news channel\n"
                "4. There's enough content for our 60-90 seconds of clip footage\n\n"
                "Return JSON with:\n"
                "- selected_video_id: the chosen video ID\n"
                "- selected_url: full YouTube URL\n"
                "- reason: why this clip is best\n"
                "- hook_start: timestamp (seconds) for the opening hook (10-20s)\n"
                "- hook_end: end of hook\n"
                "- context_start: timestamp for context segment (20-40s)\n"
                "- context_end: end of context\n"
                "- final_start: timestamp for final clip segment (15-25s)\n"
                "- final_end: end of final\n"
                "- term_timestamp: exact second when the term is first mentioned"
            ),
            context=context,
            temperature=0.3,
            max_tokens=2000,
        )
        return result

    def suggest_clips_via_llm(self, term: str, search_queries: list[str]) -> dict:
        """If YouTube API fails, ask LLM to suggest specific video URLs."""
        result = self.think(
            task=(
                f"I need to find a YouTube news clip where a news anchor discusses '{term}'.\n"
                f"The clip MUST be from a major newsroom: CNBC, Bloomberg, BBC, CNN, "
                f"Reuters, Fox Business, Yahoo Finance, etc.\n"
                f"Suggest 3 specific, real YouTube search queries that would find the best clips.\n"
                f"Also suggest what kind of clip would be ideal (channel, type of segment, etc).\n\n"
                f"My search queries were: {search_queries}\n\n"
                "Return JSON with:\n"
                "- refined_queries: list of 3 better search queries\n"
                "- ideal_clip_description: what the perfect clip looks like\n"
                "- suggested_channels: list of major newsroom channels likely to have good clips"
            ),
            context={"term": term},
            temperature=0.6,
        )
        return result
