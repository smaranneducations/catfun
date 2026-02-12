"""All specialist agents for AI Brief."""
import json
from aibrief import config
from aibrief.agents.base import Agent
from aibrief.agents.validators import GUARDRAIL

# ═══════════════════════════════════════════════════════════════
#  NEWS SCOUT — Google Search grounded (real URLs, not hallucinated)
# ═══════════════════════════════════════════════════════════════

class NewsScout:
    """Finds trending news using Gemini + Google Search grounding.

    NOT a base Agent — uses Google Search tool directly so URLs come
    from actual Google Search results (grounding metadata), not LLM
    hallucination.

    Flow:
      1. Gemini + Google Search finds trending articles
      2. We extract REAL URLs from grounding_metadata.grounding_chunks
      3. Follow redirect URLs to get the actual article URLs
      4. HTTP-verify each URL, pick the first that returns 200
      5. Give the verified URL + article info back to the pipeline
    """

    def __init__(self):
        from google import genai
        self.name = "News Scout"
        self.role = "Finds trending news via Google Search grounding"
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)

    @staticmethod
    def _is_category_page(url: str) -> bool:
        """Detect if a URL is a category/index/listing page rather than
        an actual article.

        Category signals:
          - Path ends with a generic segment (no slug, no ID, no date)
          - All segments are short generic words (news, topic, science, etc.)
          - No alphanumeric slug or date pattern in the final segment
          - URL path has no query string with article ID
        """
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if not path:
            return True  # homepage

        segments = [s for s in path.split("/") if s]
        if not segments:
            return True

        # Known category path patterns (any segment matches → category)
        category_words = {
            "news", "topic", "topics", "category", "categories", "section",
            "sections", "tag", "tags", "archive", "archives", "latest",
            "trending", "popular", "featured", "index", "browse",
            "computers_math", "markets_and_finance", "artificial_intelligence",
            "science", "technology", "business", "health", "environment",
            "politics", "sports", "entertainment", "education",
        }

        # If ALL segments are generic category words → category page
        if all(s.lower().replace("-", "_") in category_words for s in segments):
            return True

        # If last segment is a category word and has no digits → category
        last = segments[-1].lower().replace("-", "_")
        if last in category_words:
            return True

        # Short path with no slug characteristics (digits, hyphens, long words)
        has_digit = any(c.isdigit() for c in segments[-1])
        has_slug = "-" in segments[-1] and len(segments[-1]) > 15
        has_id = parsed.query and ("id=" in parsed.query or "article" in parsed.query)
        if len(segments) <= 2 and not has_digit and not has_slug and not has_id:
            return True

        return False

    @staticmethod
    def _resolve_grounding_url(redirect_url: str) -> str | None:
        """Follow a Vertex AI grounding redirect to get the real URL."""
        import requests
        try:
            resp = requests.head(
                redirect_url, allow_redirects=True, timeout=10,
                headers={"User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )},
            )
            final = resp.url
            if "404" in final.lower():
                return None
            if NewsScout._is_category_page(final):
                return None
            return final
        except Exception:
            return None

    @staticmethod
    def _verify_url(url: str) -> bool:
        """Check if a URL actually loads (HTTP 200)."""
        import requests
        try:
            resp = requests.get(
                url, timeout=10, allow_redirects=True, stream=True,
                headers={"User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )},
            )
            resp.close()
            return resp.status_code < 400
        except Exception:
            return False

    def find_story(self, content_type: str, pulse: dict,
                   excluded: list = None) -> dict:
        """Search Google for a real trending news article.

        Uses grounding metadata to extract verified URLs.
        """
        from google.genai import types

        excluded_str = ""
        if excluded:
            excluded_str = (
                "\n\nDO NOT pick any of these (already covered): "
                + ", ".join(f'"{h}"' for h in excluded)
            )

        trending = pulse.get("trending_topics", [])
        viral = pulse.get("top_viral_news", "")
        mood = pulse.get("mood", "normal")

        prompt = (
            f"Search Google News for the most trending, viral news story "
            f"happening right now. Find a specific article with details.\n\n"
            f"CATEGORY FILTER — Only pick stories from these categories:\n"
            f"  - Economics / Finance / Markets\n"
            f"  - Technology / AI / Software / Hardware\n"
            f"  - Science / Research / Space / Health\n"
            f"  - Media / Entertainment / Digital Culture\n"
            f"Do NOT pick: politics, sports, crime, celebrity gossip, weather.\n\n"
            f"World mood: {mood}. Trending: {', '.join(trending[:3])}.\n"
            f"Viral today: {viral}.\n"
            f"Content angle: {content_type}.\n"
            f"{excluded_str}\n\n"
            f"Return the story details as JSON:\n"
            f'{{\n'
            f'  "headline": "your punchy headline",\n'
            f'  "exact_news_headline": "exact original headline",\n'
            f'  "publisher": "publication name",\n'
            f'  "summary": "3-4 sentence summary",\n'
            f'  "summary_points": ["pt1","pt2","pt3","pt4","pt5","pt6"],\n'
            f'  "date": "YYYY-MM-DD",\n'
            f'  "source": "who broke it",\n'
            f'  "why_viral": "why trending",\n'
            f'  "key_quote": "a real quote",\n'
            f'  "quote_attribution": "who said it",\n'
            f'  "impact_areas": ["area1","area2","area3"],\n'
            f'  "news_category": "category",\n'
            f'  "virality_score": 8\n'
            f'}}'
        )

        search_tool = types.Tool(google_search=types.GoogleSearch())
        cfg = types.GenerateContentConfig(
            tools=[search_tool],
            system_instruction=(
                "You are a news intelligence agent. Use Google Search to "
                "find real trending news with specific articles and details."
            ),
            temperature=0.3,
        )

        resp = self._client.models.generate_content(
            model=config.MODEL_NEWS_SCOUT,
            contents=prompt,
            config=cfg,
        )

        text = resp.text
        it = getattr(resp.usage_metadata, 'prompt_token_count', 0) or 0
        ot = getattr(resp.usage_metadata, 'candidates_token_count', 0) or 0
        cost = (it * 0.10 + ot * 0.40) / 1e6
        print(f"    [News Scout] Gemini+Search | {it + ot} tok | ${cost:.6f}")

        # ── Extract REAL URLs from grounding metadata ──
        real_urls = []
        for cand in resp.candidates:
            gm = getattr(cand, "grounding_metadata", None)
            if not gm:
                continue
            chunks = getattr(gm, "grounding_chunks", None) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if not web:
                    continue
                uri = getattr(web, "uri", "")
                title = getattr(web, "title", "")
                if uri:
                    real_urls.append({"uri": uri, "title": title})

        print(f"    [Grounding] {len(real_urls)} source URLs from Google Search")

        # ── Resolve redirect URLs and verify ──
        # Try ALL grounding URLs, skip category pages, pick first real article
        verified_url = None
        verified_publisher = None
        for src in real_urls:
            uri = src["uri"]
            resolved = None
            if "vertexaisearch.cloud.google.com" in uri:
                resolved = self._resolve_grounding_url(uri)
                if not resolved:
                    print(f"    [Skip] {src['title']} → category/index page")
                    continue
            elif uri.startswith("http"):
                # Apply category filter to ALL URLs, not just Vertex redirects
                if self._is_category_page(uri):
                    print(f"    [Skip] {src['title']} → category/index page: {uri[:70]}")
                    continue
                resolved = uri
            else:
                continue

            print(f"    [Redirect] {src['title']} → {resolved[:80]}")
            if self._verify_url(resolved):
                verified_url = resolved
                verified_publisher = src["title"]
                print(f"    [Verified] ✓ HTTP 200: {resolved[:80]}")
                break
            else:
                print(f"    [Verified] ✗ not accessible")

        # ── Parse LLM response (may contain prose + JSON) ──
        import re
        result = None
        # Try direct parse
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try stripping markdown fences
        if result is None:
            clean = text.strip()
            if "```" in clean:
                clean = "\n".join(
                    l for l in clean.split("\n")
                    if not l.strip().startswith("```"))
                try:
                    result = json.loads(clean)
                except json.JSONDecodeError:
                    pass
        # Try extracting JSON object from prose text
        if result is None:
            match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        # Last resort: build result from the text + grounding
        if result is None:
            # Extract headline-like content from the prose
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            headline = lines[0][:120] if lines else "Trending News"
            result = {
                "headline": headline,
                "exact_news_headline": headline,
                "summary": text[:300],
                "summary_points": [l[:80] for l in lines[1:7]],
                "date": "",
                "source": "",
                "why_viral": "trending on Google",
                "impact_areas": [],
                "news_category": "general",
                "virality_score": 7,
            }

        if isinstance(result, list):
            result = result[0] if result else {}

        # ── Inject verified URL (overrides any hallucinated URL) ──
        if verified_url:
            result["news_url"] = verified_url
            if verified_publisher:
                result["publisher"] = (
                    result.get("publisher") or verified_publisher
                )
        elif not result.get("news_url", "").startswith("http"):
            result["abort"] = True
            result["reason"] = "No verified URL from search grounding"

        return result


# ═══════════════════════════════════════════════════════════════
#  HISTORIAN — Historical perspective
# ═══════════════════════════════════════════════════════════════
class Historian(Agent):
    def __init__(self):
        super().__init__(
            name="Historian",
            role="Historical perspective and pattern recognition",
            model=config.MODEL_HISTORIAN,
            system_prompt=(
                "You are a technology historian specialising in the evolution of "
                "computing, AI, and their societal impact. You find powerful parallels "
                "between today's events and historical precedents.\n\n"
                "Your analysis should:\n"
                "- Find 2-3 historical parallels (from tech history, industrial "
                "revolutions, or science)\n"
                "- Draw non-obvious connections\n"
                "- Use specific dates, names, and numbers\n"
                "- Write in the voice of a senior partner at McKinsey\n\n"
                "Return JSON with:\n"
                "  perspective_title: string (compelling section title)\n"
                "  historical_parallels: list of {event, year, connection}\n"
                "  key_insight: string (one paragraph, max 80 words)\n"
                "  pull_quote: string (a memorable one-liner, 15 words max)\n"
                "  confidence: int (1-10)\n"
            ),
        )

    def analyse(self, story: dict) -> dict:
        return self.think(
            "Provide the historical perspective on this news story.",
            context={"story": story},
        )


# ═══════════════════════════════════════════════════════════════
#  ECONOMIST — Economic impact analysis
# ═══════════════════════════════════════════════════════════════
class Economist(Agent):
    def __init__(self):
        super().__init__(
            name="Economist",
            role="Economic impact and market analysis",
            model=config.MODEL_ECONOMIST,
            system_prompt=(
                "You are a chief economist at a top-tier investment bank. You analyse "
                "major news through the lens of markets, labour, productivity, "
                "and macroeconomics.\n\n"
                "Your analysis should:\n"
                "- Quantify the economic impact where possible ($ figures, % changes)\n"
                "- Identify winners and losers (sectors, companies, regions)\n"
                "- Connect to broader economic trends (inflation, labour market, GDP)\n"
                "- Write with authority but accessibility\n\n"
                "Return JSON with:\n"
                "  perspective_title: string\n"
                "  economic_impact: string (one paragraph, max 80 words)\n"
                "  winners: list[string]\n"
                "  losers: list[string]\n"
                "  market_signal: string (bullish/bearish/mixed + reasoning)\n"
                "  pull_quote: string (one-liner, 15 words max)\n"
                "  confidence: int (1-10)\n"
            ),
        )

    def analyse(self, story: dict) -> dict:
        return self.think(
            "Provide the economic impact analysis of this news story.",
            context={"story": story},
        )


# ═══════════════════════════════════════════════════════════════
#  SOCIOLOGIST — Social implications
# ═══════════════════════════════════════════════════════════════
class Sociologist(Agent):
    def __init__(self):
        super().__init__(
            name="Sociologist",
            role="Social implications and human impact",
            model=config.MODEL_SOCIOLOGIST,
            system_prompt=(
                "You are a sociologist and public intellectual who studies how "
                "technology reshapes human behaviour, work, and society. You write "
                "for Harvard Business Review and The Atlantic.\n\n"
                "Your analysis should:\n"
                "- Focus on human impact (workers, communities, culture)\n"
                "- Address inequality and access dimensions\n"
                "- Consider psychological and behavioural effects\n"
                "- Be empathetic but rigorous\n\n"
                "Return JSON with:\n"
                "  perspective_title: string\n"
                "  social_impact: string (one paragraph, max 80 words)\n"
                "  who_is_affected: list[string]\n"
                "  opportunity: string (positive angle)\n"
                "  risk: string (concern to watch)\n"
                "  pull_quote: string (one-liner, 15 words max)\n"
                "  confidence: int (1-10)\n"
            ),
        )

    def analyse(self, story: dict) -> dict:
        return self.think(
            "Provide the sociological perspective on this news story.",
            context={"story": story},
        )


# ═══════════════════════════════════════════════════════════════
#  FUTURIST — Forward-looking predictions
# ═══════════════════════════════════════════════════════════════
class Futurist(Agent):
    def __init__(self):
        super().__init__(
            name="Futurist",
            role="Future impact predictions and scenario planning",
            model=config.MODEL_FUTURIST,
            system_prompt=(
                "You are a futurist and strategic foresight consultant who advises "
                "Fortune 500 CEOs. You think in scenarios and time horizons.\n\n"
                "Your analysis should:\n"
                "- Project 3 scenarios: optimistic, likely, pessimistic\n"
                "- Give specific time horizons (6 months, 2 years, 5 years)\n"
                "- Identify second-order effects most people miss\n"
                "- Be bold but grounded\n\n"
                "Return JSON with:\n"
                "  perspective_title: string\n"
                "  prediction_6mo: string (what happens in 6 months)\n"
                "  prediction_2yr: string (what happens in 2 years)\n"
                "  prediction_5yr: string (what happens in 5 years)\n"
                "  wildcard: string (the thing nobody is talking about)\n"
                "  pull_quote: string (one-liner, 15 words max)\n"
                "  confidence: int (1-10)\n"
            ),
        )

    def analyse(self, story: dict) -> dict:
        return self.think(
            "Provide your future predictions based on this news story.",
            context={"story": story},
        )


# ═══════════════════════════════════════════════════════════════
#  CONTENT WRITER — Synthesises everything into page-by-page content
# ═══════════════════════════════════════════════════════════════
class ContentWriter(Agent):
    def __init__(self):
        super().__init__(
            name="Content Writer",
            role="Synthesises perspectives into polished poster content",
            model=config.MODEL_CONTENT_WRITER,
            system_prompt=(
                "You are the ghostwriter for Bhasker Kumar — a globally recognised "
                "thought leader who keynotes Davos and advises heads of state. "
                "You write like a luxury brand writes copy: every word is intentional, "
                "every sentence is crafted to feel premium and aspirational.\n\n"
                f"{GUARDRAIL}\n\n"
                "FORMAT: You create POSTER content — NOT slides, NOT documents.\n"
                "Think: Nike poster, Apple keynote, Vogue cover, Porsche ad.\n\n"
                "PAGE STRUCTURE (in exact order):\n\n"
                "PAGE 1 — 'hero' (cover/landing page):\n"
                "  Massive title, subtitle, author name. No bullet points.\n\n"
                "PAGE 2 — 'news_summary' (the original news source):\n"
                "  This page presents the original news article.\n"
                "  Fields: news_headline (exact original headline from the source),\n"
                "          news_publisher (e.g. 'Bloomberg', 'Reuters'),\n"
                "          news_url (direct link to the article),\n"
                "          summary_points: list of EXACTLY 6 bullet points summarising\n"
                "            the news facts (each 10-15 words)\n\n"
                "PAGES 3-6 — content pages (mix of 'impact', 'stat', 'quote'):\n"
                "  Each content page has EXACTLY 5 bullet points.\n"
                "  Each point: a bold statement (5-10 words) + supporting detail (10-15 words)\n"
                "  Format each point as: {point: string, detail: string}\n"
                "  - At least 1 stat page with a HERO NUMBER\n"
                "  - At least 1 powerful quote page\n"
                "  - Each page has a page_title (5-8 words, the theme of that page)\n\n"
                "STRICT GUARDRAILS:\n"
                "- Maximum 10 words per point statement\n"
                "- Maximum 15 words per detail line\n"
                "- Use specific numbers, dates, names — precision is luxury\n"
                "- Neutral tone — never negative about individuals. May critique ideas.\n"
                "- Author is ALWAYS 'Bhasker Kumar'\n\n"
                "Return JSON with:\n"
                "  brief_title: string (5-8 words, punchy)\n"
                "  subtitle: string (one line)\n"
                "  author_name: 'Bhasker Kumar'\n"
                "  author_title: string\n"
                "  pages: list of 6 objects:\n"
                "    [0] page_type: 'hero', hero_statement, supporting_line\n"
                "    [1] page_type: 'news_summary', news_headline, news_publisher, "
                "news_url, summary_points (6 strings)\n"
                "    [2-5] page_type: 'impact'|'stat'|'quote', page_title, "
                "points: [{point, detail}, ...] (5 items each),\n"
                "           hero_number (for stat), hero_label (for stat), "
                "quote (for quote), attribution (for quote),\n"
                "           visual_mood: string\n"
            ),
        )

    def synthesise(self, story: dict, perspectives: dict,
                   editor_notes: dict = None) -> dict:
        """Synthesise into poster format — news summary + 4 content pages."""
        ctx = {"story": story, "perspectives": perspectives}
        if editor_notes:
            ctx["editor_revision_notes"] = editor_notes
        return self.think(
            "CREATE A 6-PAGE POSTER (1 hero + 1 news summary + 4 content pages).\n\n"
            "This is a POSTER, not a document. Think: Nike, Apple, Vogue, Porsche.\n\n"
            "RULES:\n"
            "- Page 1: 'hero' (cover — massive title)\n"
            "- Page 2: 'news_summary' (original news: headline, publisher, URL, "
            "6 summary bullet points)\n"
            "- Pages 3-6: mix of 'impact', 'stat', 'quote'\n"
            "  - Each has page_title + EXACTLY 5 points [{point, detail}]\n"
            "  - At least 1 stat page with a HERO NUMBER\n"
            "  - At least 1 powerful quote page\n\n"
            "The news_summary page MUST use the EXACT original headline, publisher, "
            "and URL from the story context. The 6 summary points must be factual "
            "and concise (10-15 words each).\n\n"
            "EXACTLY 6 pages. Author: 'Bhasker Kumar'.\n"
            "Every word earns its place. Less is everything.",
            context=ctx,
            max_tokens=6000,
        )



# ═══════════════════════════════════════════════════════════════
#  CONTENT REVIEWER — Quality, neutrality, and tone check
# ═══════════════════════════════════════════════════════════════
class ContentReviewer(Agent):
    def __init__(self):
        super().__init__(
            name="Content Reviewer",
            role="Quality, neutrality, and tone guardian",
            model=config.MODEL_CONTENT_REVIEWER,
            system_prompt=(
                "You are the chief compliance officer and editorial standards editor. "
                "Your job is PARAMOUNT: ensure all content is:\n\n"
                f"{GUARDRAIL}\n\n"
                "1. NEUTRAL — never takes sides on political or corporate disputes\n"
                "2. NEVER NEGATIVE — about specific individuals (critique ideas, not people)\n"
                "3. NEVER ABUSIVE — no insults, no dismissive language\n"
                "4. MAY BE CRITICAL — constructive criticism of approaches, strategies, "
                "or decisions is encouraged\n"
                "5. FACTUALLY SOUND — no made-up statistics, no false attributions\n"
                "6. PROFESSIONAL — suitable for C-suite readership\n\n"
                "Return JSON with:\n"
                "  approved: bool\n"
                "  overall_score: int (1-10)\n"
                "  tone_score: int (1-10, 10=perfectly neutral)\n"
                "  issues: list of {page_type: str, issue: str, severity: str, fix: str}\n"
                "  strengths: list[string]\n"
                "  revision_required: bool\n"
            ),
        )

    def review(self, brief_content: dict) -> dict:
        return self.think(
            "Review this entire brief for neutrality, tone, quality, and "
            "professionalism. This check is PARAMOUNT — flag any issues.",
            context={"brief_to_review": brief_content},
            max_tokens=3000,
        )


# ═══════════════════════════════════════════════════════════════
#  EDITOR-IN-CHIEF — Orchestrates discussion between agents
# ═══════════════════════════════════════════════════════════════
class EditorInChief(Agent):
    def __init__(self):
        super().__init__(
            name="Editor-in-Chief",
            role="Orchestrates the editorial discussion",
            model=config.MODEL_EDITOR_IN_CHIEF,
            system_prompt=(
            "You are the editor-in-chief of the most prestigious strategy "
            "publication in the world. You orchestrate a team of brilliant analysts "
                "and hold them to the highest standards.\n\n"
                f"{GUARDRAIL}\n\n"
                "When reviewing perspectives, you:\n"
                "- Identify overlapping arguments (ask agents to differentiate)\n"
                "- Spot missing angles (request additions)\n"
                "- Challenge weak reasoning (demand evidence)\n"
                "- Ensure each perspective adds unique value\n"
                "- Push for sharper, more memorable insights\n\n"
                "Return JSON with:\n"
                "  overall_assessment: string\n"
                "  quality_score: int (1-10)\n"
                "  feedback_per_agent: dict mapping agent_name to:\n"
                "    {score: int, strengths: list[str], improve: list[str]}\n"
                "  missing_angles: list[string]\n"
                "  ready_for_synthesis: bool\n"
            ),
        )

    def review_perspectives(self, story: dict, perspectives: dict) -> dict:
        return self.think(
            "Review all analyst perspectives. Identify overlaps, gaps, and "
            "weaknesses. Be demanding — this brief goes to Fortune 500 CEOs.",
            context={"story": story, "all_perspectives": perspectives},
            max_tokens=4000,
        )

    def review_final_brief(self, brief: dict, reviewer_feedback: dict) -> dict:
        return self.think(
            "The Content Reviewer has flagged issues. Decide which fixes are "
            "essential and provide specific revision instructions to the writer.",
            context={"brief": brief, "reviewer_feedback": reviewer_feedback},
        )


# ═══════════════════════════════════════════════════════════════
#  DISCUSSION POTENTIAL — Evaluates if content can spark engagement
# ═══════════════════════════════════════════════════════════════

class DiscussionPotentialAgent(Agent):
    """Evaluates whether the content has potential to instigate meaningful
    discussion and engagement on LinkedIn.

    How it works:
    1. Receives the synthesized brief (title, pages, key points) + story
    2. Scores on 5 engagement dimensions (1-10 each):
       - Controversy: Does the topic have two valid sides people will debate?
       - Relevance: Does it affect a large professional audience *right now*?
       - Novelty: Is this genuinely new, or recycled common knowledge?
       - Actionability: Can readers do something with this information?
       - Emotional Resonance: Does it trigger curiosity, fear, hope, or surprise?
    3. Produces a composite engagement_score (0-100) and a verdict:
       - >= 70: HIGH potential → proceed
       - 50-69: MEDIUM → proceed with a suggested hook adjustment
       - < 50: LOW → flag it (too generic / no debate angle)
    4. Suggests 2-3 "discussion hooks" — provocative questions or angles
       that the LinkedIn post can lead with to maximise comments.
    """

    def __init__(self):
        super().__init__(
            name="Discussion Potential Analyst",
            role="Evaluates content engagement and discussion potential",
            model=config.MODEL_DISCUSSION_POTENTIAL,
            system_prompt=(
                "You are a LinkedIn engagement strategist with deep expertise in "
                "what makes professional content go viral. You analyse content and "
                "predict whether it will spark meaningful discussion.\n\n"
                "You score on five dimensions (1-10 each):\n"
                "  1. CONTROVERSY — Are there two legitimate sides to debate?\n"
                "  2. RELEVANCE — Does this affect many professionals right now?\n"
                "  3. NOVELTY — Is this genuinely new information or insight?\n"
                "  4. ACTIONABILITY — Can readers act on this knowledge?\n"
                "  5. EMOTIONAL RESONANCE — Does it trigger curiosity/fear/hope/surprise?\n\n"
                "You also suggest 2-3 'discussion hooks' — provocative opening "
                "questions that would maximise comments on LinkedIn.\n\n"
                "Return JSON only:\n"
                "{\n"
                '  "controversy": {score, reasoning},\n'
                '  "relevance": {score, reasoning},\n'
                '  "novelty": {score, reasoning},\n'
                '  "actionability": {score, reasoning},\n'
                '  "emotional_resonance": {score, reasoning},\n'
                '  "engagement_score": number (0-100),\n'
                '  "verdict": "HIGH" | "MEDIUM" | "LOW",\n'
                '  "discussion_hooks": ["question1", "question2", "question3"],\n'
                '  "suggested_angle": "how to reframe if LOW",\n'
                '  "reasoning": "overall assessment"\n'
                "}\n"
            ),
        )

    def evaluate(self, story: dict, brief: dict) -> dict:
        """Evaluate discussion potential of the content."""
        title = brief.get("brief_title", "")
        pages = brief.get("pages", [])

        # Extract key content for analysis
        content_summary = []
        for p in pages:
            pt = p.get("page_type", "")
            title_p = p.get("page_title", "")
            points = p.get("points", [])
            quote = p.get("quote", "")
            if title_p:
                content_summary.append(f"[{pt}] {title_p}")
            for pt_item in points[:3]:
                if isinstance(pt_item, dict):
                    content_summary.append(f"  - {pt_item.get('point', '')}")
                else:
                    content_summary.append(f"  - {str(pt_item)[:80]}")
            if quote:
                content_summary.append(f'  Quote: "{quote[:100]}"')

        prompt = (
            f"Evaluate the discussion potential of this LinkedIn thought "
            f"leadership brief:\n\n"
            f"HEADLINE: {story.get('headline', '?')}\n"
            f"BRIEF TITLE: {title}\n"
            f"CATEGORY: {story.get('news_category', '?')}\n"
            f"WHY VIRAL: {story.get('why_viral', '?')}\n"
            f"SUMMARY: {story.get('summary', '?')}\n\n"
            f"CONTENT STRUCTURE:\n"
            + "\n".join(content_summary[:20])
            + "\n\nWill this spark meaningful professional discussion on LinkedIn? "
            f"Score each dimension and provide discussion hooks."
        )

        return self.think(prompt, context={
            "story_headline": story.get("headline"),
            "brief_title": title,
            "page_count": len(pages),
        })


# ═══════════════════════════════════════════════════════════════
#  LINKEDIN EXPERT — Crafts the post with unicode formatting
# ═══════════════════════════════════════════════════════════════
class LinkedInExpert(Agent):
    def __init__(self):
        super().__init__(
            name="LinkedIn Expert",
            role="Crafts viral LinkedIn posts with proper formatting",
            model=config.MODEL_LINKEDIN_EXPERT,
            system_prompt=(
                "You are the top LinkedIn ghostwriter in the world. Your posts "
                "consistently get 50K+ impressions.\n\n"
                "CRITICAL FORMATTING RULES FOR LINKEDIN:\n"
                "LinkedIn does NOT support markdown or HTML. You MUST use Unicode "
                "characters for formatting:\n\n"
                "BOLD TEXT: Use Unicode Mathematical Bold Sans-Serif characters:\n"
                "  𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭\n"
                "  𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇\n"
                "  𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵\n\n"
                "ITALIC TEXT: Use Unicode Mathematical Italic Sans-Serif characters:\n"
                "  𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡\n\n"
                "VISUAL SEPARATORS: ━━━━━━━━━━━ or ─────────── or ◆◆◆\n\n"
                "BULLET POINTS: ▸ or • or ◇\n\n"
                "HOOK: First 2 lines must stop the scroll. Use a bold provocative "
                "statement or surprising statistic.\n\n"
                "STRUCTURE:\n"
                "1. Hook (2 lines, bold) — stops the scroll\n"
                "2. One blank line\n"
                "3. Context (2-3 short lines)\n"
                "4. Key insights (3-5 bullet points using ▸)\n"
                "5. Personal take (2-3 lines, thoughtful)\n"
                "6. CTA (question to drive comments)\n"
                "7. Blank line\n"
                "8. Hashtags (5-8, mix of broad and niche)\n\n"
                "LENGTH: 1200-1800 characters (sweet spot for engagement)\n\n"
                "MANDATORY — SOURCE REFERENCE:\n"
                "At the end of the post (before hashtags), ALWAYS include:\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "📰 𝗦𝗼𝘂𝗿𝗰𝗲: Publisher Name\n"
                "🔗 https://example.com/full-article-url\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "This makes the source clickable in LinkedIn. NEVER skip this.\n\n"
                "CRITICAL URL FORMAT RULE:\n"
                "LinkedIn does NOT render Markdown. NEVER use [text](url) format.\n"
                "Just paste the raw URL on its own line: https://...\n"
                "LinkedIn auto-detects URLs and makes them clickable.\n"
                "WRONG: [Read the article](https://example.com)\n"
                "WRONG: [https://example.com](https://example.com)\n"
                "RIGHT: https://example.com\n\n"
                "Return JSON with:\n"
                "  post_text: string (the full LinkedIn post with unicode formatting "
                "INCLUDING the source reference block at the end)\n"
                "  document_title: string (catchy, attention-grabbing title for the "
                "PDF carousel view in LinkedIn — NOT 'AI Strategy Brief' — must be "
                "topic-specific, scroll-stopping, 5-10 words, e.g. 'The $4T Race: "
                "Who Owns AI Infrastructure?' or 'Why Your AI Strategy Is Already "
                "Obsolete')\n"
                "  hashtags: list[string]\n"
                "  best_posting_time: string (suggested time)\n"
                "  expected_reach: string (estimated impressions)\n"
            ),
        )

    @staticmethod
    def _clean_linkedin_links(text: str) -> str:
        """Strip Markdown link syntax — LinkedIn doesn't render it.

        [text](url) → url
        [url](url) → url
        """
        import re
        # [any text](https://...) → just the URL
        text = re.sub(
            r'\[([^\]]*)\]\((https?://[^\)]+)\)',
            r'\2',
            text,
        )
        return text

    def craft_post(self, story: dict, brief_content: dict,
                   hooks: list = None) -> dict:
        news_url = story.get("news_url", "")
        publisher = story.get("publisher", "")

        hooks_instruction = ""
        if hooks:
            hooks_instruction = (
                "\n\nDISCUSSION HOOKS (from engagement analysis — use one as "
                "the CTA or weave into the post to spark comments):\n"
                + "\n".join(f"  • {h}" for h in hooks[:3])
            )

        result = self.think(
            "Write a LinkedIn post promoting this brief. The post should "
            "stand on its own as valuable content — not just a promo. Use "
            "Unicode bold characters for the header and key phrases. The post "
            "should feel like it came from a senior strategy partner.\n\n"
            "MANDATORY: Include the source reference at the end of the post "
            f"(before hashtags). Publisher: {publisher}. URL: {news_url}. "
            "The URL must be a PLAIN URL on its own line (NO Markdown). "
            "LinkedIn auto-detects URLs and makes them clickable. "
            "NEVER use [text](url) format."
            + hooks_instruction,
            context={"story": story, "brief_summary": brief_content,
                     "news_url": news_url, "publisher": publisher},
            max_tokens=3000,
        )
        # Post-process: strip any Markdown links the LLM still outputs
        if isinstance(result, dict) and "post_text" in result:
            result["post_text"] = self._clean_linkedin_links(result["post_text"])
        return result