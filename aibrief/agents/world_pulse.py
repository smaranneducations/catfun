"""WorldPulseScanner — Scans global sentiment before any content decision.

Uses Gemini with Google Search grounding for real-time data:
  - Top trending topics globally
  - Major AI news in last 24-48 hours
  - Stock market sentiment
  - Viral content
  - Overall world mood

Returns a structured sentiment assessment that drives all downstream agents.
"""
import json
from aibrief import config

# Sentiment boundaries (calibrated: 80% of days should be NORMAL)
MOOD_BOUNDARIES = {
    "extreme_sad":  (-100, -60),   # global tragedy, war, pandemic
    "anxious":      (-60, -20),    # market crash, rising tensions
    "normal":       (-20, 20),     # business as usual
    "optimistic":   (20, 60),      # breakthrough, rally, momentum
    "euphoric":     (60, 100),     # peace deal, revolutionary invention
}

SYSTEM_PROMPT = (
    "You are a global intelligence analyst codenamed Aria. "
    "You scan the world's information landscape in real-time to assess "
    "the current mood of humanity and the AI industry.\n\n"
    "You are CALIBRATED: most days are NORMAL. Only flag extreme if "
    "genuinely extreme (war, market crash, major tragedy). "
    "80% of days should score between -20 and 20.\n\n"
    "SENTIMENT SCALE:\n"
    "  -100 to -60: EXTREME_SAD (global tragedy, war, pandemic peak)\n"
    "  -60 to -20:  ANXIOUS (market crash, rising tensions, tech scare)\n"
    "  -20 to  20:  NORMAL (business as usual, regular news cycle)\n"
    "   20 to  60:  OPTIMISTIC (breakthrough, market rally, momentum)\n"
    "   60 to 100:  EUPHORIC (major peace deal, revolution, celebration)\n\n"
    "Your assessment drives what content gets published and how it's designed. "
    "Be honest and precise. Don't be dramatic for no reason."
)


class WorldPulseScanner:
    """Scans global sentiment. Primary: Gemini + Google Search. Fallback: Gemini only."""

    def __init__(self):
        from google import genai
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)

    def scan(self) -> dict:
        """Return structured sentiment assessment."""
        print("\n  [WorldPulse] Scanning global sentiment...")
        try:
            return self._scan_with_search()
        except Exception as e:
            print(f"  [WorldPulse] Google Search grounding failed: {e}")
            print(f"  [WorldPulse] Falling back to model knowledge...")
            return self._scan_fallback()

    def _scan_with_search(self) -> dict:
        """Use Gemini with Google Search grounding for real-time data."""
        from google.genai import types

        prompt = (
            "Today is February 2026. Scan the current global state:\n\n"
            "1. Top 3 trending news topics globally right now\n"
            "2. Any major AI news in the last 24-48 hours\n"
            "3. Stock market sentiment (up/down/volatile?)\n"
            "4. Any major world events (geopolitical, disasters, etc.)\n"
            "5. What's going viral on social media today?\n"
            "6. Overall internet mood: anxious, normal, optimistic?\n\n"
            "Based on all this, provide your sentiment assessment.\n\n"
            "Respond in this EXACT JSON format (no markdown, no explanation):\n"
            "{\n"
            '  "sentiment_score": <-100 to 100>,\n'
            '  "mood": "<extreme_sad|anxious|normal|optimistic|euphoric>",\n'
            '  "trending_topics": ["topic1", "topic2", "topic3"],\n'
            '  "major_events": ["event1 if any"],\n'
            '  "ai_news": ["ai_news_1", "ai_news_2"],\n'
            '  "market_sentiment": "<bullish|bearish|mixed|volatile>",\n'
            '  "viral_content": ["content1", "content2"],\n'
            '  "reasoning": "Brief explanation of sentiment score",\n'
            '  "recommended_tone": "<somber|thoughtful|neutral|confident|celebratory>"\n'
            "}"
        )

        try:
            search_tool = types.Tool(google_search=types.GoogleSearch())
            cfg = types.GenerateContentConfig(
                tools=[search_tool],
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
            )
        except (AttributeError, TypeError):
            # google_search not available in this SDK version
            raise RuntimeError("GoogleSearch tool not available")

        resp = self._client.models.generate_content(
            model=config.MODEL_WORLD_PULSE,
            contents=prompt,
            config=cfg,
        )

        text = resp.text
        it = getattr(resp.usage_metadata, 'prompt_token_count', 0) or 0
        ot = getattr(resp.usage_metadata, 'candidates_token_count', 0) or 0
        cost = (it * 0.10 + ot * 0.40) / 1e6
        print(f"    [Aria] Gemini+Search | {it + ot} tok | ${cost:.6f}")

        return self._parse_response(text)

    def _scan_fallback(self) -> dict:
        """Use Gemini Flash without search grounding (training data only)."""
        from google.genai import types

        prompt = (
            "Today is February 10, 2026. Based on your knowledge of recent "
            "world events, AI industry developments, and general global "
            "sentiment trends, provide your best assessment of the current "
            "world mood.\n\n"
            "Consider: recent AI breakthroughs, geopolitical tensions, "
            "market conditions, and trending topics.\n\n"
            "Respond in this EXACT JSON format:\n"
            "{\n"
            '  "sentiment_score": <-100 to 100>,\n'
            '  "mood": "<extreme_sad|anxious|normal|optimistic|euphoric>",\n'
            '  "trending_topics": ["topic1", "topic2", "topic3"],\n'
            '  "major_events": ["event1 if any"],\n'
            '  "ai_news": ["ai_news_1", "ai_news_2"],\n'
            '  "market_sentiment": "<bullish|bearish|mixed|volatile>",\n'
            '  "viral_content": ["content1", "content2"],\n'
            '  "reasoning": "Brief explanation of sentiment score",\n'
            '  "recommended_tone": "<somber|thoughtful|neutral|confident|celebratory>"\n'
            "}"
        )

        cfg = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            response_mime_type="application/json",
        )

        resp = self._client.models.generate_content(
            model=config.MODEL_WORLD_PULSE,
            contents=prompt,
            config=cfg,
        )

        text = resp.text
        it = getattr(resp.usage_metadata, 'prompt_token_count', 0) or 0
        ot = getattr(resp.usage_metadata, 'candidates_token_count', 0) or 0
        cost = (it * 0.10 + ot * 0.40) / 1e6
        print(f"    [Aria] Gemini Flash | {it + ot} tok | ${cost:.6f}")

        return self._parse_response(text)

    def _parse_response(self, text: str) -> dict:
        """Parse the sentiment response, handling various formats."""
        try:
            result = json.loads(text)
            if isinstance(result, list):
                result = result[0] if result else {}
        except json.JSONDecodeError:
            # Try stripping markdown code fences
            clean = text.strip()
            if clean.startswith("```"):
                clean = "\n".join(
                    l for l in clean.split("\n")
                    if not l.strip().startswith("```"))
            try:
                result = json.loads(clean)
                if isinstance(result, list):
                    result = result[0] if result else {}
            except json.JSONDecodeError:
                print(f"  [WorldPulse] Could not parse response, using defaults")
                result = self._default_pulse()

        # Validate and normalize
        score = result.get("sentiment_score", 0)
        if not isinstance(score, (int, float)):
            score = 0
        result["sentiment_score"] = max(-100, min(100, int(score)))
        result["mood"] = self._score_to_mood(result["sentiment_score"])

        print(f"  [WorldPulse] Score: {result['sentiment_score']}, "
              f"Mood: {result['mood']}, "
              f"Tone: {result.get('recommended_tone', '?')}")
        return result

    @staticmethod
    def _score_to_mood(score: int) -> str:
        for mood, (lo, hi) in MOOD_BOUNDARIES.items():
            if lo <= score <= hi:
                return mood
        return "normal"

    @staticmethod
    def _default_pulse() -> dict:
        return {
            "sentiment_score": 0,
            "mood": "normal",
            "trending_topics": ["AI developments", "global economy", "tech innovation"],
            "major_events": [],
            "ai_news": ["Continued AI advancement"],
            "market_sentiment": "mixed",
            "viral_content": [],
            "reasoning": "Default assessment — could not parse live data",
            "recommended_tone": "neutral",
        }
