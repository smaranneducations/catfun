"""Executive Producer Agent — The CEO of FinanceCats.

Responsibilities:
  - Reads episode_log.json to know what we've already covered
  - Decides which finance category/term to target next
  - Ensures no repeats of terms, cats, or historical events
  - Maintains brand consistency across episodes
  - Makes final go/no-go decisions on scripts
"""
import json
import os
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are the Executive Producer of "FinanceCats" — an AI-powered YouTube channel
that creates 4-6.5 minute finance education videos. Each video features a professional-looking
cat photo that pauses a real news clip and explains a complex financial term.

Your brand identity:
- Clear, authoritative British voice
- Professional cat images (glasses, hats, bow ties)
- Educational but never boring — use storytelling, not lectures
- Each video covers ONE financial term from recent news
- Historical examples bring terms to life

Your job:
1. Review the episode log to know what's been covered
2. Choose the next term/category — avoid repeats, balance coverage
3. Approve or reject scripts for brand consistency
4. Ensure each episode feels fresh while maintaining channel identity

Categories to rotate through:
- Macro Economics (GDP, inflation, interest rates, yield curves)
- Markets & Trading (short selling, margin calls, circuit breakers)
- Corporate Finance (earnings, buybacks, P/E ratios, debt restructuring)
- Banking & Credit (credit default swaps, bank runs, reserve ratios)
- Central Banking (quantitative easing, tapering, repo rates)
- Crypto & Fintech (staking, DeFi, tokenization)
- Geopolitics & Trade (tariffs, sanctions, currency manipulation)

Always respond in JSON format."""


class ExecutiveProducer(Agent):
    def __init__(self):
        super().__init__(
            name="Executive Producer",
            role="Brand guardian and decision maker",
            system_prompt=SYSTEM_PROMPT,
            model=config.LLM_MODEL,
        )

    def load_episode_log(self) -> dict:
        """Load the episode history."""
        if os.path.exists(config.EPISODE_LOG_PATH):
            with open(config.EPISODE_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"channel_name": "FinanceCats", "episodes": []}

    def save_episode_log(self, log: dict):
        """Save updated episode history."""
        with open(config.EPISODE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

    def log_episode(self, episode_data: dict):
        """Add a completed episode to the log."""
        log = self.load_episode_log()
        episode_number = len(log["episodes"]) + 1
        episode_data["episode_number"] = episode_number
        log["episodes"].append(episode_data)
        self.save_episode_log(log)
        print(f"    [Episode Log] Saved episode #{episode_number}")
        return episode_number

    def decide_next_topic(self) -> dict:
        """Decide what finance term/topic to cover next."""
        log = self.load_episode_log()

        covered_terms = [ep.get("term", "") for ep in log.get("episodes", [])]
        covered_categories = [ep.get("category", "") for ep in log.get("episodes", [])]
        covered_events = []
        for ep in log.get("episodes", []):
            covered_events.extend(ep.get("historical_events_covered", []))

        context = {
            "total_episodes_so_far": len(log.get("episodes", [])),
            "terms_already_covered": covered_terms,
            "categories_used_recently": covered_categories[-5:],
            "historical_events_used": covered_events[-10:],
            "cats_used_recently": [ep.get("cat_id") for ep in log.get("episodes", [])[-5:]],
        }

        result = self.think(
            task=(
                "Decide the next finance term to cover. Pick a term that:\n"
                "1. Is currently relevant in financial news (2025-2026)\n"
                "2. Has NOT been covered before\n"
                "3. Is in a different category than the last 2-3 episodes\n"
                "4. Has rich historical examples to draw from\n"
                "5. Would be searched by people trying to understand finance news\n"
                "6. Sounds complex but can be explained simply\n\n"
                "Return JSON with: term, category, why_now (what recent news uses this term), "
                "search_queries (3 YouTube search queries to find news clips using this term), "
                "difficulty (1-5 how complex to explain)"
            ),
            context=context,
            temperature=0.7,
        )
        return result

    def approve_script(self, script: dict, fact_check: dict) -> dict:
        """Review and approve/reject a script."""
        result = self.think(
            task=(
                "Review this script for brand consistency and quality.\n"
                "Check:\n"
                "1. Is the explanation clear and accurate?\n"
                "2. Do historical examples enhance understanding?\n"
                "3. Is the tone educational but engaging (not dry)?\n"
                "4. Is the pacing right for 4-6.5 minutes?\n"
                "5. Does it maintain our British, professional tone?\n"
                "6. Are the fact-checker's concerns addressed?\n\n"
                "Return JSON with: approved (bool), feedback (str), "
                "suggested_changes (list of specific changes if not approved)"
            ),
            context={"script": script, "fact_check_results": fact_check},
            temperature=0.3,
        )
        return result
