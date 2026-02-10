"""Fact Checker Agent — Verifies all claims in the script.

Responsibilities:
  - Checks all dates, numbers, and historical references
  - Verifies definitions are accurate
  - Flags any misleading simplifications
  - Ensures no factual errors would embarrass the channel
  - Provides confidence scores for each claim
"""
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are the Fact Checker for "FinanceCats", a YouTube finance education channel.

Your job is to verify EVERY factual claim in our scripts before they go to production.
We cannot afford errors — our credibility depends on accuracy.

For each claim in the script, check:
1. Are the dates correct?
2. Are the numbers/percentages accurate?
3. Are historical events described correctly?
4. Is the definition of the term accurate?
5. Are there any misleading simplifications?
6. Could any statement be misinterpreted?

Rating scale for each claim:
- VERIFIED: Confident this is accurate
- LIKELY_CORRECT: Probably right but worth double-checking
- NEEDS_CORRECTION: Contains an error, provide the correct information
- MISLEADING: Technically true but could mislead viewers

Be thorough but fair. Simple explanations of complex topics will naturally
lose some nuance — that's OK as long as the core message is correct.

Always respond in JSON format."""


class FactChecker(Agent):
    def __init__(self):
        super().__init__(
            name="Fact Checker",
            role="Accuracy verification",
            system_prompt=SYSTEM_PROMPT,
            model=config.LLM_MODEL_MINI,  # Cost-effective for verification
        )

    def check_script(self, script: dict, historical_research: dict) -> dict:
        """Verify all facts in the script."""
        context = {
            "script": script,
            "source_research": historical_research,
        }

        result = self.think(
            task=(
                "Fact-check this entire script. For each segment that contains "
                "factual claims:\n\n"
                "1. List every specific claim (dates, numbers, events, definitions)\n"
                "2. Rate each: VERIFIED, LIKELY_CORRECT, NEEDS_CORRECTION, MISLEADING\n"
                "3. For NEEDS_CORRECTION: provide the correct information\n"
                "4. For MISLEADING: explain how to fix it\n\n"
                "Return JSON with:\n"
                "- overall_rating: PASS, PASS_WITH_NOTES, or NEEDS_REVISION\n"
                "- total_claims_checked: number\n"
                "- issues_found: number of NEEDS_CORRECTION or MISLEADING\n"
                "- checks: list of objects with:\n"
                "    - claim: the specific claim text\n"
                "    - segment_id: which segment (1-6)\n"
                "    - rating: VERIFIED | LIKELY_CORRECT | NEEDS_CORRECTION | MISLEADING\n"
                "    - note: explanation or correction\n"
                "- summary: overall assessment (2-3 sentences)"
            ),
            context=context,
            temperature=0.2,
            max_tokens=4000,
        )
        return result
