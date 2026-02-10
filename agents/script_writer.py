"""Script Writer Agent — Writes TWO scripts: AI Anchor + Cat Conversation.

V3: The video has two distinct parts:

  PART 1 — AI NEWS ANCHOR (60-90 seconds)
    A professional female anchor reads a compelling news report about the
    most viral economic/geopolitical story of the week. The script naturally
    EMBEDS a financial term that becomes the teaching topic.
    The anchor always starts: "OK, this news is from [date]..."

  PART 2 — CAT CONVERSATION (120-180 seconds)
    Professor Whiskers and Cleo explain the embedded financial term.
    This plays over a FROZEN frame of the anchor (anchor visible on one
    side, cats overlaid on the other side, slightly smaller).

Total video: 3-4 minutes.

The key insight: pick the viral news FIRST, then embed a relevant
financial term into the anchor's script. This catches viral trends
regardless of whether they explicitly mention a textbook term.
"""
import config
from agents.base_agent import Agent


ANCHOR_SYSTEM_PROMPT = """You are a script writer for an AI news anchor on "FinanceCats", a YouTube finance education channel.

You write scripts for a FEMALE news anchor who reads viral economic/geopolitical news
in a professional, high-end studio setting. She is articulate, warm, and authoritative.

THE ANCHOR'S PERSONA:
  - Professional female news presenter
  - Sitting in a modern, high-end studio
  - Clear, confident delivery — like a CNN or Bloomberg anchor
  - Warm but authoritative tone
  - Makes complex news accessible to everyday viewers

SCRIPT RULES:
  1. The anchor ALWAYS starts with: "OK, this news is from [exact date]."
     Example: "OK, this news is from February 8th, 2026."
  2. The script covers the viral news story in a compelling, easy-to-understand way
  3. A specific financial/economic TERM must be naturally woven into the report
     — NOT as a forced definition, but as a natural part of the news narration
  4. The term should appear 2-3 times in the script, each time adding context
  5. The script should end with a hook that leads to the cats' explanation:
     Something like: "Now, [term] is something that affects all of us, and
     understanding it could change how you see your own finances."
  6. Total duration: 60-90 seconds of spoken text (~150-225 words)
  7. Short, punchy sentences. Conversational but professional.
  8. Include specific numbers, dates, and names — real journalism.
  9. The script must feel like real TV news, not a lecture.

TONE: Think BBC World News meets friendly explainer. Professional but not stiff.
The audience should feel like they're watching a real news broadcast.

Always respond in JSON format."""


CAT_SYSTEM_PROMPT = """You are the Script Writer for "FinanceCats", a YouTube finance education channel.

You write scripts for a 2-3 minute segment where TWO professional cat characters explain
a financial term that was just mentioned by a news anchor. The cats' conversation plays
OVER a frozen frame of the anchor — anchor visible on one side, cats on the other.

THE TWO CATS:
  - Professor Whiskers (Cat A): The expert. Calm, clear British male voice. Explains
    things simply, uses vivid real-life analogies. Never condescending.
  - Cleo (Cat B): The curious one. Warm, friendly female voice. Asks the questions
    the audience is thinking. Says "Wait, I don't get it..." to push for simpler
    explanations. Represents the everyday person.

GOLDEN RULE: This is a CONVERSATION, not a lecture.
  - Cleo asks → Professor explains simply → Cleo reacts
  - Cleo pushes back: "But what does that actually mean for normal people?"
  - Professor uses real-life analogies (grocery shopping, rent, borrowing from a friend)
  - Cleo has "aha" moments: "Ohh, so it's like when..."
  - It should feel like two friends chatting over coffee

SIMPLICITY RULE: Explain like the viewer has ZERO finance knowledge.
  - No jargon without an immediate plain-English explanation
  - "Think of it like..." is your best friend
  - If a 12-year-old can't understand it, simplify further

CONVERSATION STRUCTURE (120-180 seconds total):

  a) REACT TO THE ANCHOR (15-20s)
     Cleo: "Did you hear that? The anchor just said [term]..."
     Professor: "Yes, and it's one of those terms that sounds complicated but..."

  b) THE SIMPLE DEFINITION (25-35s)
     Cleo: "So what IS [term]?"
     Professor explains with a vivid real-life analogy.
     Cleo repeats it back in her own words.

  c) WHY IT MATTERS NOW (30-40s)
     Cleo: "OK but why is this in the news right now?"
     Professor connects to the specific viral story the anchor reported.
     Makes it personal: how it affects savings, jobs, prices.

  d) HISTORICAL EXAMPLE (30-40s)
     Cleo: "Has something like this happened before?"
     Professor tells a vivid story with specific dates and numbers.
     Cleo reacts with surprise.

  e) THE TAKEAWAY (20-30s)
     Cleo summarises in plain English.
     Professor adds one practical tip.
     Professor teases the next episode's term.
     Cleo: "Ooh, what's that?"

WRITING RULES:
- British English spelling
- Short sentences. Conversational. Use contractions.
- Each dialogue line: 1-3 sentences MAX
- Total: 120-180 seconds (~300-450 words of dialogue)
- Must reference what the anchor said to create continuity

Always respond in JSON format."""


class ScriptWriter(Agent):
    def __init__(self):
        # The agent switches system prompts depending on which script it's writing
        super().__init__(
            name="Script Writer",
            role="Anchor script + cat conversation script",
            system_prompt=ANCHOR_SYSTEM_PROMPT,
            model=config.MODEL_SCRIPT_WRITER,
        )

    def write_anchor_script(
        self,
        viral_story: dict,
        term: str,
        term_info: dict,
        story_date: str = "",
    ) -> dict:
        """Write the AI news anchor's script.

        The anchor reports the viral news and naturally embeds the financial term.

        Args:
            viral_story: The viral news story dict (headline, summary, key_facts)
            term: The financial term to embed
            term_info: Info about the term (embedding_hint, simple_definition)
            story_date: The date the story broke (for the anchor's intro)

        Returns:
            dict with: anchor_script_text, term_mentions, estimated_duration,
                       opening_line, closing_hook
        """
        self.system_prompt = ANCHOR_SYSTEM_PROMPT

        context = {
            "viral_story": viral_story,
            "term_to_embed": term,
            "term_info": term_info,
            "story_date": story_date,
            "anchor_intro_template": config.ANCHOR_INTRO_TEMPLATE,
        }

        result = self.think(
            task=(
                f"Write a news anchor script about this viral story that naturally "
                f"embeds the financial term '{term}'.\n\n"
                f"The anchor MUST start with: \"OK, this news is from {story_date}.\"\n\n"
                "The script must:\n"
                "- Cover the viral story compellingly (numbers, names, impact)\n"
                f"- Naturally weave in '{term}' 2-3 times\n"
                "- End with a hook leading to the cats' explanation\n"
                "- Be 60-90 seconds of spoken text (~150-225 words)\n"
                "- Sound like real TV news\n\n"
                "Return JSON with:\n"
                "- anchor_script_text: the FULL script the anchor will read "
                "  (as a single string, with natural pauses marked by '...')\n"
                "- estimated_duration_seconds: estimated speaking time\n"
                "- estimated_word_count: word count\n"
                "- opening_line: the first sentence\n"
                "- closing_hook: the final sentence (the bridge to cats)\n"
                "- term_mentions: list of sentences where the term appears\n"
                "- key_facts_used: which key facts from the story were included"
            ),
            context=context,
            temperature=0.5,
            max_tokens=3000,
        )
        return result

    def write_cat_script(
        self,
        term: str,
        anchor_script: dict,
        viral_story: dict,
        historical_research: dict,
        next_episode_term: str = "",
        enrichment: dict = None,
    ) -> dict:
        """Write the cat conversation script.

        The cats explain the term that the anchor just mentioned.
        This plays over a frozen frame of the anchor.

        Args:
            term: The financial term to explain
            anchor_script: The anchor script (so cats can reference it)
            viral_story: The viral news story for context
            historical_research: Historical examples and definitions
            next_episode_term: Term for next episode teaser
            enrichment: Optional sociological/geopolitical insights

        Returns:
            dict with segments and dialogue
        """
        self.system_prompt = CAT_SYSTEM_PROMPT

        context = {
            "term": term,
            "anchor_closing_hook": anchor_script.get("closing_hook", ""),
            "anchor_script_summary": anchor_script.get("anchor_script_text", "")[:500],
            "viral_story_headline": viral_story.get("headline", ""),
            "historical_research": historical_research,
            "cat_a_name": config.CAT_A_NAME,
            "cat_b_name": config.CAT_B_NAME,
        }

        if enrichment:
            context["specialist_enrichment"] = enrichment

        teaser_instruction = ""
        if next_episode_term:
            teaser_instruction = (
                f"\nIMPORTANT: The next episode's term is '{next_episode_term}'. "
                f"Professor Whiskers should tease this specific term in the wrap-up."
            )

        enrichment_instruction = ""
        if enrichment:
            if "sociological_insights" in enrichment:
                enrichment_instruction += (
                    "\nSOCIOLOGICAL INSIGHTS (weave naturally if they fit):\n"
                    f"  {enrichment.get('sociological_summary', '')}\n"
                )
            if "geopolitical_insights" in enrichment:
                enrichment_instruction += (
                    "\nGEOPOLITICAL INSIGHTS (weave naturally if they fit):\n"
                    f"  {enrichment.get('geopolitical_summary', '')}\n"
                )

        result = self.think(
            task=(
                f"Write the cat conversation script explaining '{term}'.\n\n"
                "This plays AFTER the news anchor's report, over a frozen frame "
                "of the anchor. The cats should reference what the anchor said.\n\n"
                "Structure: 5 exchanges (react, define, why now, history, takeaway)\n"
                "Duration: 120-180 seconds total\n"
                f"{teaser_instruction}\n"
                f"{enrichment_instruction}\n\n"
                "Return JSON with:\n"
                "- title_term: the financial term\n"
                "- estimated_total_duration: total seconds\n"
                "- exchanges: list of 5 exchange objects, each with:\n"
                "    - exchange_id: 1-5\n"
                "    - exchange_title: e.g. 'React to Anchor', 'Simple Definition', etc.\n"
                "    - dialogue: list of {speaker: 'cat_a'|'cat_b', line: '...'}\n"
                "      Each exchange should have 3-6 dialogue turns.\n"
                "    - key_points: 2-3 bullet points for on-screen text\n"
                "    - duration_seconds: estimated seconds (20-40s each)\n"
                "- key_takeaway: one-sentence summary for end screen\n"
                "- teaser_term: the next episode's term\n"
                "- teaser_line: one sentence teaser for next episode"
            ),
            context=context,
            temperature=0.6,
            max_tokens=5000,
        )
        return result

    def revise_script(self, script: dict, feedback: str) -> dict:
        """Revise a cat script based on feedback."""
        result = self.think(
            task=(
                f"Revise this cat conversation script based on feedback:\n\n"
                f"FEEDBACK: {feedback}\n\n"
                "Keep the same dialogue format.\n"
                "Return the complete revised script in the same JSON format."
            ),
            context={"current_script": script},
            temperature=0.5,
            max_tokens=5000,
        )
        return result
