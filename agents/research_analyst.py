"""Research Analyst Agent — Finds trending finance news clips.

Responsibilities:
  - Searches YouTube for recent finance news clips
  - Identifies clips where anchors use the target terminology
  - Validates clips have usable transcripts
  - Finds the exact timestamps where terms are mentioned
  - Returns ranked candidates with metadata
"""
import json
import os
import requests
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are a Research Analyst for "FinanceCats", a YouTube finance education channel.

Your job is to find the BEST news clip for our next video. The ideal clip:
1. Is from a major, recognizable news source (CNBC, Bloomberg, BBC, Reuters, etc.)
2. Has a news anchor clearly using/explaining the target financial term
3. Is recent (within last 6 months ideally)
4. Has clear audio and professional production
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

    def search_youtube(self, queries: list[str], max_results_per_query: int = 5) -> list[dict]:
        """Search YouTube for finance news clips using the Data API."""
        if not config.YOUTUBE_API_KEY:
            print("    [Research Analyst] No YouTube API key — using LLM suggestions instead")
            return []

        all_results = []
        seen_ids = set()

        for query in queries:
            try:
                url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "order": "relevance",
                    "maxResults": max_results_per_query,
                    "videoDuration": "medium",  # 4-20 minutes
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
                        all_results.append({
                            "video_id": vid_id,
                            "url": f"https://www.youtube.com/watch?v={vid_id}",
                            "title": item["snippet"]["title"],
                            "channel": item["snippet"]["channelTitle"],
                            "description": item["snippet"]["description"][:300],
                            "published_at": item["snippet"]["publishedAt"],
                        })
            except Exception as e:
                print(f"    [Research Analyst] Search error for '{query}': {e}")

        print(f"    [Research Analyst] Found {len(all_results)} candidate videos")
        return all_results

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
                "Pick the one where:\n"
                "1. The anchor clearly says and discusses the term\n"
                "2. The context is dramatic or newsworthy\n"
                "3. The clip is from a reputable source\n"
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
                f"Suggest 3 specific, real YouTube search queries that would find the best clips.\n"
                f"Also suggest what kind of clip would be ideal (channel, type of segment, etc).\n\n"
                f"My search queries were: {search_queries}\n\n"
                "Return JSON with:\n"
                "- refined_queries: list of 3 better search queries\n"
                "- ideal_clip_description: what the perfect clip looks like\n"
                "- suggested_channels: list of channels likely to have good clips"
            ),
            context={"term": term},
            temperature=0.6,
        )
        return result
