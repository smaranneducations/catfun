"""Multi-agent discussion orchestrator.

Agents don't just work sequentially — they critique each other's work
and revise based on editorial feedback. The Editor-in-Chief drives the
discussion, and the Content Reviewer has veto power on tone/neutrality.
"""
import time
from aibrief.agents.specialists import (
    NewsScout, Historian, Economist, Sociologist, Futurist,
    ContentWriter, DesignDirector, ContentReviewer, EditorInChief,
    LinkedInExpert,
)


class Orchestrator:
    """Runs the full multi-agent pipeline with discussion rounds."""

    def __init__(self):
        self.scout = NewsScout()
        self.historian = Historian()
        self.economist = Economist()
        self.sociologist = Sociologist()
        self.futurist = Futurist()
        self.writer = ContentWriter()
        self.designer = DesignDirector()
        self.reviewer = ContentReviewer()
        self.editor = EditorInChief()
        self.linkedin = LinkedInExpert()

    def run(self) -> dict:
        """Run the full pipeline and return all outputs."""
        t0 = time.time()

        # ──────────────────────────────────────────────────────
        #  PHASE 1: FIND THE STORY
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 1: FIND TOP AI STORY")
        print("=" * 60)
        story = self.scout.find_top_story()
        # Gemini may return a list; take the first item
        if isinstance(story, list):
            story = story[0] if story else {}
        headline = story.get("headline", "?")
        print(f"\n  ▸ {headline}")
        print(f"  ▸ Date: {story.get('date', '?')}")
        print(f"  ▸ Virality: {story.get('virality_score', '?')}/10")
        print(f"  ▸ Quote: \"{story.get('key_quote', '?')[:80]}...\"")

        # ──────────────────────────────────────────────────────
        #  PHASE 2: INDEPENDENT ANALYSIS (all perspectives)
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 2: INDEPENDENT ANALYSIS (4 perspectives)")
        print("=" * 60)

        perspectives = {}
        for name, agent in [("historical", self.historian),
                            ("economic", self.economist),
                            ("social", self.sociologist),
                            ("future", self.futurist)]:
            perspectives[name] = agent.analyse(story)
            title = perspectives[name].get("perspective_title", "?")
            quote = perspectives[name].get("pull_quote", "?")
            print(f"  ▸ {name.title()}: \"{quote}\"")

        # ──────────────────────────────────────────────────────
        #  PHASE 3: EDITORIAL DISCUSSION — Editor critiques
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 3: EDITORIAL DISCUSSION")
        print("=" * 60)

        editor_review = self.editor.review_perspectives(story, perspectives)
        score = editor_review.get("quality_score", "?")
        ready = editor_review.get("ready_for_synthesis", False)
        print(f"  ▸ Editor score: {score}/10")
        print(f"  ▸ Ready for synthesis: {ready}")

        # If not ready, agents revise based on feedback
        if not ready:
            print("  ▸ Revision round — agents improving their work...")
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
                    revised = agent.respond_to_feedback(perspectives[key], agent_fb)
                    perspectives[key] = revised
                    print(f"    ▸ {agent_name} revised")

        # ──────────────────────────────────────────────────────
        #  PHASE 4: CROSS-CRITIQUE — Agents review each other
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 4: CROSS-CRITIQUE")
        print("=" * 60)

        # Economist critiques Historian, Futurist critiques Sociologist
        critique_1 = self.economist.critique(perspectives["historical"], "Historian")
        critique_2 = self.futurist.critique(perspectives["social"], "Sociologist")
        print(f"  ▸ Economist → Historian: {critique_1.get('raw', str(critique_1))[:80]}")
        print(f"  ▸ Futurist → Sociologist: {critique_2.get('raw', str(critique_2))[:80]}")

        # ──────────────────────────────────────────────────────
        #  PHASE 5: SYNTHESIS — Content Writer creates the brief
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 5: CONTENT SYNTHESIS")
        print("=" * 60)

        brief = self.writer.synthesise(story, perspectives)
        pages = brief.get("pages", [])
        title = brief.get("brief_title", "?")
        print(f"  ▸ Title: {title}")
        print(f"  ▸ Pages: {len(pages)}")
        for p in pages:
            print(f"    - [{p.get('page_type', '?')}] {p.get('title', '?')}")

        # ──────────────────────────────────────────────────────
        #  PHASE 6: NEUTRALITY CHECK — Content Reviewer
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 6: NEUTRALITY & QUALITY CHECK")
        print("=" * 60)

        review = self.reviewer.review(brief)
        approved = review.get("approved", False)
        tone = review.get("tone_score", "?")
        issues = review.get("issues", [])
        print(f"  ▸ Approved: {approved}")
        print(f"  ▸ Tone score: {tone}/10")
        print(f"  ▸ Issues: {len(issues)}")

        # If not approved, revise
        if not approved and review.get("revision_required", False):
            print("  ▸ Revision required — Editor directing fixes...")
            editor_fix = self.editor.review_final_brief(brief, review)
            brief = self.writer.synthesise(story, perspectives,
                                          editor_notes=editor_fix)
            pages = brief.get("pages", [])
            print(f"  ▸ Revised brief: {len(pages)} pages")

            # Second neutrality check
            review2 = self.reviewer.review(brief)
            print(f"  ▸ Re-check: approved={review2.get('approved', '?')}, "
                  f"tone={review2.get('tone_score', '?')}/10")

        # ──────────────────────────────────────────────────────
        #  PHASE 7: VISUAL DESIGN
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 7: VISUAL DESIGN")
        print("=" * 60)

        design = self.designer.design(story)
        print(f"  ▸ Design: {design.get('design_name', '?')}")
        print(f"  ▸ Palette: {design.get('primary_color', '?')} / "
              f"{design.get('accent_color', '?')}")
        print(f"  ▸ Mood: {design.get('mood', '?')}")
        print(f"  ▸ Motif: {design.get('visual_motif', '?')}")

        # ──────────────────────────────────────────────────────
        #  PHASE 8: LINKEDIN POST
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  PHASE 8: LINKEDIN POST COPY")
        print("=" * 60)

        li_post = self.linkedin.craft_post(story, brief)
        post_text = li_post.get("post_text", "")
        print(f"  ▸ Post length: {len(post_text)} chars")
        print(f"  ▸ Hashtags: {li_post.get('hashtags', [])}")
        print(f"  ▸ Preview:\n{post_text[:200]}...")

        elapsed = time.time() - t0
        print(f"\n{'=' * 60}")
        print(f"  ALL AGENTS COMPLETE | {elapsed:.0f}s")
        print(f"{'=' * 60}")

        return {
            "story": story,
            "perspectives": perspectives,
            "brief": brief,
            "design": design,
            "linkedin_post": li_post,
            "elapsed_seconds": elapsed,
        }
