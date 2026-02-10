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

NICE-TO-HAVE — DEEP HISTORY (if it exists, don't force it):
  - If a concept has genuine roots in the 1500s, 1600s, 1700s — prefer those.
  - Ancient banking, Renaissance money lending, tulip mania, the South Sea Bubble
    — these are fascinating when they naturally fit.
  - A viewer learning "this same thing happened 500 years ago" is powerful.
  - But only include old examples if they genuinely relate to the term. Don't
    stretch or force a connection that isn't there.

NOTE: Sociological and geopolitical dimensions are handled by separate specialist
agents. Focus on the FINANCIAL HISTORY and the HUMAN STORIES within those events.

Your storytelling principles:
1. SPECIFICITY: Use exact dates, names, numbers — "On September 15, 2008..."
2. DRAMA: Find the human stories — who lost, who won, who saw it coming
3. PATTERN: Show how history rhymes — the same concepts repeat across CENTURIES
4. STAKES: Make clear WHY it mattered to ORDINARY PEOPLE — jobs lost, savings wiped out
5. SIMPLICITY: Explain as if to a smart 16-year-old, never use jargon without explaining it
6. DEPTH: Go as far back in history as the concept allows — centuries, not just decades

For each historical event, provide:
- The event name and date
- What happened (2-3 sentences, dramatic)
- How the financial term was central to it
- A memorable "hook" fact or quote
- Key numbers (dollar amounts, percentages, people affected)
- How it impacted ordinary people / the common person

Always respond in JSON format."""


class FinancialHistorian(Agent):
    def __init__(self):
        super().__init__(
            name="Financial Historian",
            role="Historical context and storytelling",
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL_FINANCIAL_HISTORIAN,
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
                f"Research the financial term '{term}' THOROUGHLY and find 3-4 major\n"
                f"historical events where this term was central to what happened.\n"
                f"If there are genuine examples from centuries ago (1500s-1800s), prefer those\n"
                f"— but only if they truly relate. Don't force old history where it doesn't fit.\n"
                f"Also include a modern example so viewers see the pattern across time.\n\n"
                "We need DEEP material because our video conversation is 5-7 minutes long.\n"
                "The more vivid detail you provide, the richer the cats' conversation will be.\n\n"
                "For EACH event, provide:\n"
                "1. event_name: Short, dramatic name\n"
                "2. date: Specific date or year\n"
                "3. narrative: 5-7 sentence dramatic account of what happened — include\n"
                "   the CHARACTERS (who made the decision, who suffered), the TENSION\n"
                "   (what was at stake), and the AFTERMATH (what changed)\n"
                "4. term_role: How the term was central (2-3 sentences)\n"
                "5. hook_fact: One memorable statistic or quote\n"
                "6. key_numbers: Dict of important figures (amounts, percentages)\n"
                "7. impact: Who was affected and how (be specific — names, institutions)\n"
                "8. common_person_impact: How it affected ordinary people's daily lives\n"
                "   (jobs lost, savings wiped, prices changed — be concrete)\n"
                "9. everyday_analogy: How to explain this event using a simple everyday\n"
                "   analogy (e.g. 'It's like if your bank suddenly said your savings\n"
                "   were worth half of what they were yesterday')\n"
                "10. sociological_impact: Broader social effects (empty string if not applicable)\n"
                "11. geopolitical_impact: Trade wars, sanctions, shifts (empty string if not applicable)\n\n"
                "Also provide:\n"
                "- simple_definition: Plain-English definition of the term (2-3 sentences)\n"
                "- how_it_works: Step-by-step explanation of the MECHANISM (3-4 sentences,\n"
                "  using an everyday analogy throughout)\n"
                "- why_it_matters: Why ordinary people should understand this (2-3 sentences)\n"
                "- common_misconception: What most people get wrong about this term + the truth\n"
                "- modern_relevance: How this term is relevant RIGHT NOW in 2025-2026 and\n"
                "  how it affects regular people's savings, jobs, or cost of living\n\n"
                "Return JSON with: term, simple_definition, how_it_works, why_it_matters, "
                "common_misconception, modern_relevance, historical_events (list)"
            ),
            context=context,
            temperature=0.4,
            max_tokens=6000,
        )
        return result
