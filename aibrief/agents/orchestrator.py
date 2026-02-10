"""Multi-agent DISCUSSION orchestrator — Preparer/Reviewer pairs.

Architecture:
  Every agent has a PREPARER (creates) and REVIEWER (critiques).
  They argue 2-3 rounds until quality bar is met.
  Then a ROUND-TABLE where all agents see all work and challenge each other.
  Finally, ScreenRealEstateAgent audits the PDF and demands fixes.

This is NOT a linear pipeline. It is a structured debate.
"""
import json
import time
from aibrief.agents.specialists import (
    NewsScout, Historian, Economist, Sociologist, Futurist,
    ContentWriter, DesignDirector, ContentReviewer, EditorInChief,
    LinkedInExpert,
)
from aibrief.agents.base import Agent
from aibrief import config


# ═══════════════════════════════════════════════════════════════
#  REVIEWER AGENTS — one per preparer, dedicated critics
# ═══════════════════════════════════════════════════════════════

class AnalysisReviewer(Agent):
    """Reviews analyst perspectives. Demands depth, accuracy, uniqueness."""
    def __init__(self, review_target: str):
        super().__init__(
            name=f"{review_target} Reviewer",
            role=f"Senior reviewer for {review_target} analysis",
            model=config.MODEL_CONTENT_REVIEWER,
            system_prompt=(
                f"You are a demanding senior reviewer at McKinsey specializing in "
                f"{review_target} analysis. You review work with the eye of someone "
                f"who has seen 10,000 consulting reports.\n\n"
                f"REVIEW CRITERIA:\n"
                f"1. DEPTH — Is the analysis superficial or genuinely insightful?\n"
                f"2. SPECIFICITY — Are there concrete data points, dates, names?\n"
                f"3. ORIGINALITY — Is this a fresh take or generic boilerplate?\n"
                f"4. LUXURY TONE — Does it read like a premium consulting brief?\n"
                f"5. ACTIONABILITY — Does a C-suite reader gain something concrete?\n\n"
                f"Be brutally honest. Score 1-10 on each criterion.\n"
                f"If score < 7 on any criterion, provide specific improvement demands.\n\n"
                f"Return JSON:\n"
                f"{{\n"
                f"  overall_score: number (1-10),\n"
                f"  depth_score: number, specificity_score: number,\n"
                f"  originality_score: number, tone_score: number,\n"
                f"  actionability_score: number,\n"
                f"  approved: boolean (true only if ALL scores >= 7),\n"
                f"  demands: [string] (specific improvements required),\n"
                f"  strengths: [string],\n"
                f"  missing_elements: [string]\n"
                f"}}"
            ),
        )


class CopyReviewer(Agent):
    """Reviews written copy. Demands luxury ad quality."""
    def __init__(self):
        super().__init__(
            name="Copy Reviewer",
            role="Luxury copywriting critic",
            model=config.MODEL_EDITOR_IN_CHIEF,
            system_prompt=(
                "You are the creative director at a luxury brand agency (LVMH level). "
                "You review copy with the standards of Hermès editorial campaigns. "
                "Every word must earn its place. Every sentence must feel premium.\n\n"
                "REVIEW CRITERIA:\n"
                "1. Does each slide have EXACTLY ONE point? NOT a list of bullets. ONE.\n"
                "2. Is the point high-value? Would a CEO quote it in a board meeting?\n"
                "3. Is there exactly ONE supporting insight with a concrete number/name/date?\n"
                "4. Does it read like luxury advertising — not a textbook?\n"
                "5. Would a CEO frame this on their wall?\n"
                "6. Does every slide have a compelling pull quote?\n\n"
                "STRICT GUARDRAIL: Any slide with more than 1 point or a list of "
                "4-6 bullets MUST be rejected. One point. One insight. That's the rule.\n\n"
                "Return JSON:\n"
                "{\n"
                "  overall_score: number (1-10),\n"
                "  approved: boolean,\n"
                "  page_scores: [{page_type: string, score: number, word_count: number, "
                "issues: [string]}],\n"
                "  demands: [string],\n"
                "  tone_verdict: string\n"
                "}"
            ),
        )


class DesignReviewer(Agent):
    """Reviews design concepts. Demands luxury-tier visual quality."""
    def __init__(self):
        super().__init__(
            name="Design Reviewer",
            role="Luxury design critic",
            model=config.MODEL_DESIGN_DIRECTOR,
            system_prompt=(
                "You are the art director at a luxury fashion house. "
                "You have designed for Chanel, Dior, and Cartier. "
                "You judge design concepts against the highest possible bar.\n\n"
                "REVIEW CRITERIA:\n"
                "1. COLOR PSYCHOLOGY — Do the colors evoke the right emotions?\n"
                "2. GOLDEN RATIO — Are proportions mathematically harmonious?\n"
                "3. TYPOGRAPHY HIERARCHY — 3+ clear levels (display, body, caption)?\n"
                "4. VISUAL WEIGHT — Is the layout balanced on the page?\n"
                "5. UNIQUENESS — Have I seen this palette/mood before? It must surprise.\n"
                "6. BACKGROUNDS — Rich textures/gradients, never plain white?\n\n"
                "Return JSON:\n"
                "{\n"
                "  overall_score: number (1-10),\n"
                "  approved: boolean,\n"
                "  color_verdict: string,\n"
                "  proportion_verdict: string,\n"
                "  demands: [string],\n"
                "  suggested_improvements: [string]\n"
                "}"
            ),
        )


class ScreenRealEstateAgent(Agent):
    """Post-production auditor. Ensures no page has too much empty space."""
    def __init__(self):
        super().__init__(
            name="Screen Real Estate Auditor",
            role="Page fill and balance auditor",
            model=config.MODEL_CONTENT_REVIEWER,
            system_prompt=(
                "You are a senior UX designer who audits page layouts for luxury brands. "
                "Your job is to ensure every page of a PDF uses space according to "
                "design psychology principles.\n\n"
                "GOLDEN RULE: A luxury page should be 55-65% filled with content/visuals "
                "and 35-45% breathing room. NEVER more than 45% empty. NEVER more than "
                "70% filled.\n\n"
                "DESIGN PSYCHOLOGY PRINCIPLES:\n"
                "- Golden Ratio (1.618): content zones should relate by this ratio\n"
                "- Rule of Thirds: key elements at intersection points\n"
                "- Z-pattern reading flow: top-left → top-right → bottom-left → bottom-right\n"
                "- Visual weight: images/dark blocks anchor the page\n"
                "- Typography hierarchy: 3 sizes create order and rhythm\n"
                "- Color panels/backgrounds eliminate dead white space\n\n"
                "For each page, estimate content fill percentage and diagnose issues.\n\n"
                "Return JSON:\n"
                "{\n"
                "  pages: [\n"
                "    {\n"
                "      page_number: number,\n"
                "      estimated_fill_pct: number (0-100),\n"
                "      passes_golden_rule: boolean,\n"
                "      issues: [string],\n"
                "      fix_suggestions: [string]\n"
                "    }\n"
                "  ],\n"
                "  overall_verdict: string,\n"
                "  approved: boolean\n"
                "}"
            ),
        )


# ═══════════════════════════════════════════════════════════════
#  ORCHESTRATOR — Structured debate, not pipeline
# ═══════════════════════════════════════════════════════════════

class Orchestrator:
    """Runs multi-agent discussion with preparer/reviewer pairs."""

    MAX_ROUNDS = 3
    MIN_SCORE = 7

    def __init__(self):
        # Preparers
        self.scout = NewsScout()
        self.historian = Historian()
        self.economist = Economist()
        self.sociologist = Sociologist()
        self.futurist = Futurist()
        self.writer = ContentWriter()
        self.designer = DesignDirector()
        self.editor = EditorInChief()
        self.linkedin = LinkedInExpert()

        # Dedicated reviewers (one per domain)
        self.hist_reviewer = AnalysisReviewer("historical")
        self.econ_reviewer = AnalysisReviewer("economic")
        self.soc_reviewer = AnalysisReviewer("sociological")
        self.fut_reviewer = AnalysisReviewer("future/predictions")
        self.copy_reviewer = CopyReviewer()
        self.design_reviewer = DesignReviewer()
        self.neutrality_reviewer = ContentReviewer()
        self.screen_auditor = ScreenRealEstateAgent()

    def _argue(self, preparer, reviewer, initial_work: dict,
               label: str, story: dict) -> dict:
        """Preparer and Reviewer argue until quality bar is met or max rounds."""
        work = initial_work
        for round_num in range(1, self.MAX_ROUNDS + 1):
            # Reviewer critiques
            review = reviewer.think(
                f"Review this {label} work. Be demanding. Round {round_num}/{self.MAX_ROUNDS}.",
                context={"work": work, "story_context": story},
            )

            score = review.get("overall_score", 0)
            approved = review.get("approved", False)
            demands = review.get("demands", [])

            print(f"    Round {round_num}: score={score}/10, "
                  f"approved={approved}, demands={len(demands)}")

            if approved and score >= self.MIN_SCORE:
                print(f"    ✓ {label} APPROVED after {round_num} round(s)")
                return work

            if round_num < self.MAX_ROUNDS:
                # Preparer revises based on demands
                work = preparer.respond_to_feedback(work, review)
                print(f"    → {preparer.name} revised")

        print(f"    ✓ {label} accepted after {self.MAX_ROUNDS} rounds (best effort)")
        return work

    def _round_table(self, story: dict, perspectives: dict) -> dict:
        """All analysts see ALL perspectives and can challenge any."""
        print("\n  ROUND TABLE — All agents challenge each other:")
        challenges = {}

        pairs = [
            (self.economist, "economic", "historical", "Historian"),
            (self.historian, "historical", "future", "Futurist"),
            (self.futurist, "future", "social", "Sociologist"),
            (self.sociologist, "social", "economic", "Economist"),
        ]

        for challenger, own_key, target_key, target_name in pairs:
            challenge = challenger.think(
                f"You are reading {target_name}'s analysis. Challenge it from "
                f"YOUR perspective as a {challenger.role}. Point out what they "
                f"missed, where they're wrong, and what needs deeper analysis. "
                f"Also acknowledge what they got right.",
                context={
                    "your_own_work": perspectives.get(own_key, {}),
                    f"{target_name}_work": perspectives.get(target_key, {}),
                    "all_perspectives": {k: v.get("perspective_title", "?")
                                         for k, v in perspectives.items()},
                },
            )
            challenges[f"{challenger.name}→{target_name}"] = challenge
            summary = challenge.get("raw", str(challenge))[:100]
            print(f"    {challenger.name} → {target_name}: {summary}")

        # Now each agent incorporates cross-challenges
        for challenger, own_key, target_key, target_name in pairs:
            # Find challenges directed AT this agent
            incoming = {k: v for k, v in challenges.items()
                        if k.endswith(f"→{challenger.name.split()[0]}")}
            if incoming:
                perspectives[own_key] = challenger.respond_to_feedback(
                    perspectives[own_key],
                    {"cross_challenges": incoming}
                )
                print(f"    {challenger.name} incorporated {len(incoming)} challenge(s)")

        return perspectives

    def run(self) -> dict:
        """Run the full multi-agent discussion."""
        t0 = time.time()

        # ──────────────────────────────────────────────────────
        #  PHASE 1: FIND THE STORY + SEMANTIC DEDUP CHECK
        #  This runs FIRST — before any analysis. If the story
        #  is too similar to a previous post (>=70%), we skip it
        #  and ask NewsScout for a different one. Up to 3 tries.
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 1: FIND TOP AI STORY (with semantic dedup)")
        print("=" * 60)

        from aibrief.pipeline.dedup import is_duplicate, backfill_embeddings

        # Ensure existing posts have embeddings
        backfill_embeddings()

        MAX_TOPIC_ATTEMPTS = 3
        story = None
        excluded_headlines = []

        for attempt in range(1, MAX_TOPIC_ATTEMPTS + 1):
            print(f"\n  Attempt {attempt}/{MAX_TOPIC_ATTEMPTS}...")

            if attempt == 1:
                candidate = self.scout.find_top_story()
            else:
                # Ask for a DIFFERENT story, excluding previous attempts
                excluded = ", ".join(f'"{h}"' for h in excluded_headlines)
                candidate = self.scout.think(
                    f"Find a DIFFERENT top AI story. Do NOT pick any of these "
                    f"topics (already covered): {excluded}. "
                    f"Find something completely new and different.",
                    context={"excluded_topics": excluded_headlines},
                )

            if isinstance(candidate, list):
                candidate = candidate[0] if candidate else {}

            headline = candidate.get("headline", "?")
            print(f"  ▸ Candidate: {headline}")

            # Semantic dedup check
            is_dup, similarity, matched = is_duplicate(candidate)

            if is_dup:
                print(f"  ✗ BLOCKED: {similarity:.0%} similar to '{matched}'")
                excluded_headlines.append(headline)
                continue
            else:
                print(f"  ✓ UNIQUE: max similarity {similarity:.0%} (threshold 70%)")
                story = candidate
                break

        if story is None:
            print("  ⚠ All attempts matched existing topics. Using last candidate.")
            story = candidate

        print(f"\n  ▸ Final story: {story.get('headline', '?')}")

        # ──────────────────────────────────────────────────────
        #  PHASE 2: ANALYST PAIRS — Preparer + Reviewer argue
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 2: ANALYST PAIRS (Prepare → Review → Argue)")
        print("=" * 60)

        perspectives = {}
        analyst_pairs = [
            ("historical", self.historian, self.hist_reviewer),
            ("economic", self.economist, self.econ_reviewer),
            ("social", self.sociologist, self.soc_reviewer),
            ("future", self.futurist, self.fut_reviewer),
        ]

        for key, preparer, reviewer in analyst_pairs:
            print(f"\n  [{key.upper()}]")
            print(f"    Preparer: {preparer.name} | Reviewer: {reviewer.name}")
            initial = preparer.analyse(story)
            perspectives[key] = self._argue(
                preparer, reviewer, initial, key, story)

        # ──────────────────────────────────────────────────────
        #  PHASE 3: ROUND TABLE — Agents challenge each other
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 3: ROUND TABLE DEBATE")
        print("=" * 60)
        perspectives = self._round_table(story, perspectives)

        # ──────────────────────────────────────────────────────
        #  PHASE 4: EDITOR OVERSIGHT — final quality gate
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 4: EDITORIAL OVERSIGHT")
        print("=" * 60)
        editor_review = self.editor.review_perspectives(story, perspectives)
        score = editor_review.get("quality_score", "?")
        print(f"  ▸ Editor score: {score}/10")

        if not editor_review.get("ready_for_synthesis", False):
            feedback = editor_review.get("feedback_per_agent", {})
            agent_map = {
                "Historian": ("historical", self.historian),
                "Economist": ("economic", self.economist),
                "Sociologist": ("social", self.sociologist),
                "Futurist": ("future", self.futurist),
            }
            for agent_name, (key, agent) in agent_map.items():
                agent_fb = feedback.get(agent_name, {})
                if agent_fb and agent_fb.get("score", 10) < 8:
                    perspectives[key] = agent.respond_to_feedback(
                        perspectives[key], agent_fb)
                    print(f"  ▸ {agent_name} revised per editor demands")

        # ──────────────────────────────────────────────────────
        #  PHASE 5: CONTENT WRITER + COPY REVIEWER — argue
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 5: CONTENT SYNTHESIS (Writer + Copy Reviewer argue)")
        print("=" * 60)
        brief = self.writer.synthesise(story, perspectives)
        brief = self._argue(self.writer, self.copy_reviewer, brief,
                            "content_brief", story)
        pages = brief.get("pages", [])
        print(f"  ▸ Final brief: {brief.get('brief_title', '?')}, {len(pages)} pages")

        # ──────────────────────────────────────────────────────
        #  PHASE 6: NEUTRALITY CHECK
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 6: NEUTRALITY & TONE CHECK")
        print("=" * 60)
        review = self.neutrality_reviewer.review(brief)
        approved = review.get("approved", False)
        print(f"  ▸ Approved: {approved}, tone: {review.get('tone_score', '?')}/10")
        if not approved:
            editor_fix = self.editor.review_final_brief(brief, review)
            brief = self.writer.synthesise(story, perspectives,
                                          editor_notes=editor_fix)
            print(f"  ▸ Revised after neutrality feedback")

        # ──────────────────────────────────────────────────────
        #  PHASE 7: DESIGN + DESIGN REVIEWER — argue
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 7: VISUAL DESIGN (Designer + Design Reviewer argue)")
        print("=" * 60)
        design = self.designer.design(story)
        design = self._argue(self.designer, self.design_reviewer, design,
                             "visual_design", story)
        print(f"  ▸ Final design: {design.get('design_name', '?')}")

        # ──────────────────────────────────────────────────────
        #  PHASE 8: LINKEDIN POST
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 8: LINKEDIN POST COPY")
        print("=" * 60)
        li_post = self.linkedin.craft_post(story, brief)
        print(f"  ▸ Post: {len(li_post.get('post_text', ''))} chars")

        elapsed = time.time() - t0
        print(f"\n{'=' * 60}")
        print(f"  ALL AGENTS COMPLETE | {elapsed:.0f}s | "
              f"Architecture: Preparer/Reviewer pairs + Round Table")
        print(f"{'=' * 60}")

        return {
            "story": story,
            "perspectives": perspectives,
            "brief": brief,
            "design": design,
            "linkedin_post": li_post,
            "elapsed_seconds": elapsed,
        }

    def audit_pdf(self, brief: dict, pdf_path: str) -> dict:
        """Post-production: ScreenRealEstateAgent audits the generated PDF."""
        print("\n" + "=" * 60)
        print("  POST-PRODUCTION: SCREEN REAL ESTATE AUDIT")
        print("=" * 60)

        pages_summary = []
        for i, page in enumerate(brief.get("pages", [])):
            body = page.get("body", "")
            word_count = len(body.split()) if body else 0
            has_quote = bool(page.get("quote"))
            pages_summary.append({
                "page_number": i + 1,
                "page_type": page.get("page_type", "?"),
                "title": page.get("title", "?"),
                "body_word_count": word_count,
                "has_quote": has_quote,
                "has_visual_placeholder": True,
            })

        audit = self.screen_auditor.think(
            "Audit this PDF layout. For each page estimate fill percentage "
            "based on word count and visual elements. A page with < 80 words "
            "of body text and no visual will look empty. Pages need 80-150 "
            "words minimum plus a visual element to achieve the golden ratio "
            "of 55-65% fill.",
            context={"pages": pages_summary, "pdf_path": pdf_path},
        )

        approved = audit.get("approved", False)
        print(f"  ▸ Audit verdict: {'PASS' if approved else 'NEEDS FIXES'}")

        for pg in audit.get("pages", []):
            fill = pg.get("estimated_fill_pct", "?")
            ok = pg.get("passes_golden_rule", False)
            issues = pg.get("issues", [])
            print(f"    Page {pg.get('page_number', '?')}: "
                  f"fill={fill}%, golden={'✓' if ok else '✗'}, "
                  f"issues={len(issues)}")

        return audit
