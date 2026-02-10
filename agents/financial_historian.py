"""Financial Historian Agent — Researches historical context for terms.

Responsibilities:
  - Finds 2-3 major historical events where the term was central
  - Builds compelling narratives around each event
  - Provides specific dates, numbers, and names
  - Creates "aha moment" connections between history and present
  - Makes complex history accessible and dramatic
"""
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are a Financial Historian for "FinanceCats", a YouTube finance education channel.

Your expertise is turning dry financial concepts into gripping historical stories.
You find the most dramatic, memorable moments in financial history where a specific
term or concept was at the centre of major events.

Your storytelling principles:
1. SPECIFICITY: Use exact dates, names, numbers — "On September 15, 2008..."
2. DRAMA: Find the human stories — who lost, who won, who saw it coming
3. PATTERN: Show how history rhymes — the same concepts repeat across decades
4. STAKES: Make clear WHY it mattered — jobs lost, fortunes made, economies collapsed
5. SIMPLICITY: Explain as if to a smart 16-year-old, never use jargon without explaining it

For each historical event, provide:
- The event name and date
- What happened (2-3 sentences, dramatic)
- How the financial term was central to it
- A memorable "hook" fact or quote
- Key numbers (dollar amounts, percentages, people affected)

Always respond in JSON format."""


class FinancialHistorian(Agent):
    def __init__(self):
        super().__init__(
            name="Financial Historian",
            role="Historical context and storytelling",
            system_prompt=SYSTEM_PROMPT,
            model=config.LLM_MODEL,
        )

    def research_term(self, term: str, category: str,
                      already_covered_events: list[str] = None) -> dict:
        """Research historical context for a financial term."""
        context = {
            "term": term,
            "category": category,
            "events_to_avoid": already_covered_events or [],
        }

        result = self.think(
            task=(
                f"Research the financial term '{term}' and find 2-3 major historical events\n"
                f"where this term was absolutely central to what happened.\n\n"
                "For EACH event, provide:\n"
                "1. event_name: Short, dramatic name\n"
                "2. date: Specific date or year\n"
                "3. narrative: 3-4 sentence dramatic account of what happened\n"
                "4. term_role: How the term was central (1-2 sentences)\n"
                "5. hook_fact: One memorable statistic or quote\n"
                "6. key_numbers: Dict of important figures (amounts, percentages)\n"
                "7. impact: Who was affected and how\n\n"
                "Also provide:\n"
                "- simple_definition: Plain-English definition of the term (2 sentences max)\n"
                "- why_it_matters: Why ordinary people should understand this (1-2 sentences)\n"
                "- common_misconception: What most people get wrong about this term\n"
                "- modern_relevance: How this term is relevant RIGHT NOW in 2025-2026\n\n"
                "Return JSON with: term, simple_definition, why_it_matters, "
                "common_misconception, modern_relevance, historical_events (list)"
            ),
            context=context,
            temperature=0.4,
            max_tokens=4000,
        )
        return result
