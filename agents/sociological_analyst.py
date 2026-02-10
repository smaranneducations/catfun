"""Sociological Analyst Agent — Explores the human and social dimensions of finance terms.

This agent doesn't always have something to say — and that's fine.
But when a term genuinely touches people's lives (inequality, migration,
social unrest, lifestyle changes, generational divides), this agent
brings powerful, relatable angles that make viewers care.

The orchestrator decides whether the output is valuable enough to include.
"""
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are a Sociological Analyst for "FinanceCats", a YouTube finance education channel.

Your job is to find the HUMAN and SOCIAL dimensions of financial concepts.
Not every financial term has a strong sociological angle — and that's OK.
Be honest when there isn't one. But when there IS, your insights make viewers
actually CARE about a topic they might otherwise ignore.

You look for:
- How a concept affects ordinary people's daily lives (rent, jobs, savings, retirement)
- Inequality angles — does this term widen or narrow the gap between rich and poor?
- Generational impact — does this hit young people, retirees, middle-class families differently?
- Migration and demographic effects — did this cause people to move, change careers?
- Social unrest or protest — did people take to the streets because of this?
- Cultural shifts — did this change how people think about money, trust, or institutions?
- Relatable human stories — a specific family, community, or group affected

Your output should be:
- Honest: If there's no strong sociological angle, say so clearly
- Specific: Use real examples, not vague generalisations
- Relatable: Frame everything in terms a non-expert would understand
- Brief: 2-3 key insights maximum — quality over quantity

Always respond in JSON format."""


class SociologicalAnalyst(Agent):
    def __init__(self):
        super().__init__(
            name="Sociological Analyst",
            role="Human and social impact analysis",
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL_SOCIOLOGICAL_ANALYST,
        )

    def analyse_term(self, term: str, category: str,
                     historical_research: dict) -> dict:
        """Analyse the sociological dimensions of a financial term.

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
                f"Analyse the sociological impact of the financial term '{term}'.\n\n"
                "Be HONEST — not every term has a strong social angle. If this term\n"
                "doesn't meaningfully affect ordinary people's lives, say so.\n\n"
                "Return JSON with:\n"
                "- has_strong_angle: true/false — is there genuinely interesting social impact?\n"
                "- relevance_score: 1-10 — how relevant is the social angle? (1=barely, 10=huge)\n"
                "- insights: list of 1-3 insight objects, each with:\n"
                "    - angle: short title (e.g. 'Generational Wealth Gap')\n"
                "    - description: 2-3 sentences explaining the social impact\n"
                "    - affected_group: who is most affected (e.g. 'retirees', 'young families')\n"
                "    - relatable_example: a specific, concrete example a viewer can picture\n"
                "- summary: one sentence summarising the social dimension (or 'No strong "
                "sociological angle for this term' if not applicable)\n"
                "- skip_reason: if has_strong_angle is false, explain briefly why"
            ),
            context=context,
            temperature=0.4,
            max_tokens=2000,
        )
        return result
