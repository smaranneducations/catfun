"""Geopolitical Analyst Agent — Explores the global power and trade dimensions of finance terms.

This agent doesn't always have something to say — and that's fine.
But when a term touches trade wars, sanctions, currency power, global alliances,
or shifts in economic dominance, this agent brings context that makes the topic
feel bigger and more important.

The orchestrator decides whether the output is valuable enough to include.
"""
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are a Geopolitical Analyst for "FinanceCats", a YouTube finance education channel.

Your job is to find the GLOBAL POWER and TRADE dimensions of financial concepts.
Not every financial term has a geopolitical angle — and that's OK.
Be honest when there isn't one. But when there IS, your insights make viewers
understand why a "boring" financial term actually shapes the world.

You look for:
- Trade wars and tariffs — did this term play a role in trade disputes?
- Sanctions — was this concept used as an economic weapon between nations?
- Currency power — does this affect which currencies dominate global trade?
- Shifts in economic dominance — US vs China, EU dynamics, emerging markets
- Global alliances — did financial decisions reshape who works with whom?
- Resource control — oil, rare earth, food supply chain implications
- Historical geopolitics — Bretton Woods, gold standard, petrodollar, etc.
- Current tensions — how does this term relate to today's geopolitical landscape?

Your output should be:
- Honest: If there's no strong geopolitical angle, say so clearly
- Specific: Name countries, treaties, dates — not vague "global tensions"
- Accessible: Explain power dynamics simply, no political science jargon
- Brief: 2-3 key insights maximum — quality over quantity

Always respond in JSON format."""


class GeopoliticalAnalyst(Agent):
    def __init__(self):
        super().__init__(
            name="Geopolitical Analyst",
            role="Global power and trade impact analysis",
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL_GEOPOLITICAL_ANALYST,
        )

    def analyse_term(self, term: str, category: str,
                     historical_research: dict) -> dict:
        """Analyse the geopolitical dimensions of a financial term.

        Returns insights only if genuinely valuable. Includes a
        relevance_score so the orchestrator can decide whether to use them.
        """
        context = {
            "term": term,
            "category": category,
            "historical_events": historical_research.get("historical_events", []),
            "simple_definition": historical_research.get("simple_definition", ""),
        }

        result = self.think(
            task=(
                f"Analyse the geopolitical impact of the financial term '{term}'.\n\n"
                "Be HONEST — not every term has a strong geopolitical angle. If this term\n"
                "doesn't meaningfully affect global power dynamics, say so.\n\n"
                "Return JSON with:\n"
                "- has_strong_angle: true/false — is there genuinely interesting geopolitical impact?\n"
                "- relevance_score: 1-10 — how relevant is the geopolitical angle? (1=barely, 10=huge)\n"
                "- insights: list of 1-3 insight objects, each with:\n"
                "    - angle: short title (e.g. 'The Petrodollar System')\n"
                "    - description: 2-3 sentences explaining the geopolitical impact\n"
                "    - countries_involved: list of key countries/regions\n"
                "    - relatable_example: a specific, concrete example a viewer can picture\n"
                "- summary: one sentence summarising the geopolitical dimension (or 'No strong "
                "geopolitical angle for this term' if not applicable)\n"
                "- skip_reason: if has_strong_angle is false, explain briefly why"
            ),
            context=context,
            temperature=0.4,
            max_tokens=2000,
        )
        return result
