"""Agent Orchestrator — Coordinates all agents for V3 pipeline.

V3 Flow (AI Anchor + Cat Conversation):
  1. Viral News Scout finds the most viral story of the week
  2. Scout picks the best financial term to embed in the story
  3. Financial Historian researches the term
  4. (Optional) Sociological + Geopolitical analysts add depth
  5. Script Writer creates the ANCHOR script (embeds term in news)
  6. Script Writer creates the CAT script (explains the term)
  7. Fact Checker verifies all claims
  8. Executive Producer approves
  9. Creative Director selects two cats + designs overlays
  10. YouTube Strategist creates SEO package
  11. Return everything to pipeline for production
"""
import json
import os
import time
import config
from agents.executive_producer import ExecutiveProducer
from agents.viral_news_scout import ViralNewsScout
from agents.financial_historian import FinancialHistorian
from agents.sociological_analyst import SociologicalAnalyst
from agents.geopolitical_analyst import GeopoliticalAnalyst
from agents.script_writer import ScriptWriter
from agents.fact_checker import FactChecker
from agents.creative_director import CreativeDirector
from agents.youtube_strategist import YouTubeStrategist

# Minimum relevance score for specialist insights
SPECIALIST_RELEVANCE_THRESHOLD = 5


class AgentOrchestrator:
    """Orchestrates all agents for FinanceCats V3 video production."""

    def __init__(self):
        print("\n  Initialising Agent System (V3: AI Anchor + Cat Conversation)...")
        self.producer = ExecutiveProducer()
        self.scout = ViralNewsScout()
        self.historian = FinancialHistorian()
        self.sociologist = SociologicalAnalyst()
        self.geopolitician = GeopoliticalAnalyst()
        self.writer = ScriptWriter()
        self.checker = FactChecker()
        self.creative = CreativeDirector()
        self.strategist = YouTubeStrategist()
        print("  All agents ready.\n")

    def run_full_pipeline(self) -> dict:
        """Run the complete V3 agent pipeline.

        Returns:
            dict with: viral_story, term, anchor_script, cat_script,
                       cat_selection, youtube_package, episode_data, etc.
        """
        start = time.time()

        # ═══════════════════════════════════════════════
        # PHASE 1: FIND VIRAL NEWS
        # ═══════════════════════════════════════════════
        print("=" * 60)
        print("  PHASE 1: FIND VIRAL NEWS (Last 7 Days)")
        print("=" * 60)

        # Get previously covered stories to avoid repeats
        log = self.producer.load_episode_log()
        covered_stories = [
            ep.get("viral_story_headline", ep.get("term", ""))
            for ep in log.get("episodes", [])
        ]

        viral_result = self.scout.find_viral_news(excluded_stories=covered_stories)
        stories = viral_result.get("stories", [])
        top_pick = viral_result.get("top_pick", {})

        print(f"\n  >> Found {len(stories)} viral stories:")
        for i, s in enumerate(stories[:5]):
            score = s.get("virality_score", "?")
            print(f"     {i+1}. [{score}/10] {s.get('headline', '?')[:80]}")

        if not stories:
            print("  ERROR: No viral stories found!")
            return {}

        # Use the top story
        chosen_story = stories[0]
        print(f"\n  >> TOP PICK: {chosen_story.get('headline', 'N/A')}")
        print(f"  >> Date: {chosen_story.get('date', 'N/A')}")
        print(f"  >> Why viral: {chosen_story.get('virality_reason', 'N/A')[:120]}")

        # ═══════════════════════════════════════════════
        # PHASE 2: PICK TEACHING TERM
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  PHASE 2: PICK TEACHING TERM")
        print("=" * 60)

        # Get terms already covered
        all_terms = [ep.get("term", "") for ep in log.get("episodes", [])]

        # Check for queued term from series continuity
        queued_term = self.producer.get_queued_next_term()

        if queued_term and queued_term not in all_terms:
            print(f"\n  >> Series continuity: using queued term '{queued_term}'")
            term = queued_term
            term_info = {
                "term": queued_term,
                "category": "series_continuation",
                "why_this_term": f"Queued from previous episode teaser",
                "embedding_hint": "",
                "simple_definition": "",
                "difficulty": 3,
            }
        else:
            term_result = self.scout.pick_teaching_term(
                story=chosen_story,
                covered_terms=all_terms,
            )
            term = term_result.get("term", "Unknown")
            term_info = term_result

        print(f"\n  >> Teaching term: {term}")
        print(f"  >> Category: {term_info.get('category', 'N/A')}")
        print(f"  >> Why this term: {term_info.get('why_this_term', 'N/A')[:120]}")
        print(f"  >> Embedding hint: {term_info.get('embedding_hint', 'N/A')[:120]}")

        # ═══════════════════════════════════════════════
        # PHASE 3: HISTORICAL RESEARCH
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  PHASE 3: HISTORICAL RESEARCH")
        print("=" * 60)

        covered_events = []
        for ep in log.get("episodes", []):
            covered_events.extend(ep.get("historical_events_covered", []))

        category = term_info.get("category", "general")
        history = self.historian.research_term(term, category, covered_events)

        events = history.get("historical_events", [])
        print(f"\n  >> Found {len(events)} historical events:")
        for ev in events:
            print(f"     - {ev.get('event_name', '?')} ({ev.get('date', '?')})")
        print(f"  >> Definition: {history.get('simple_definition', 'N/A')[:100]}...")

        # ═══════════════════════════════════════════════
        # PHASE 3b: SPECIALIST ANALYSIS (optional)
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  PHASE 3b: SPECIALIST ANALYSIS")
        print("=" * 60)

        socio_analysis = self.sociologist.analyse_term(term, category, history)
        geo_analysis = self.geopolitician.analyse_term(term, category, history)

        socio_score = socio_analysis.get("relevance_score", 0)
        geo_score = geo_analysis.get("relevance_score", 0)
        socio_useful = (socio_analysis.get("has_strong_angle", False)
                        and socio_score >= SPECIALIST_RELEVANCE_THRESHOLD)
        geo_useful = (geo_analysis.get("has_strong_angle", False)
                      and geo_score >= SPECIALIST_RELEVANCE_THRESHOLD)

        print(f"\n  >> Sociological: {'INCLUDED' if socio_useful else 'SKIPPED'} "
              f"(score {socio_score}/10)")
        print(f"  >> Geopolitical: {'INCLUDED' if geo_useful else 'SKIPPED'} "
              f"(score {geo_score}/10)")

        enrichment = {}
        if socio_useful:
            enrichment["sociological_insights"] = socio_analysis.get("insights", [])
            enrichment["sociological_summary"] = socio_analysis.get("summary", "")
        if geo_useful:
            enrichment["geopolitical_insights"] = geo_analysis.get("insights", [])
            enrichment["geopolitical_summary"] = geo_analysis.get("summary", "")

        # ═══════════════════════════════════════════════
        # PHASE 4: WRITE ANCHOR SCRIPT
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  PHASE 4: WRITE ANCHOR SCRIPT")
        print("=" * 60)

        story_date = chosen_story.get("date", "")
        anchor_script = self.writer.write_anchor_script(
            viral_story=chosen_story,
            term=term,
            term_info=term_info,
            story_date=story_date,
        )

        anchor_text = anchor_script.get("anchor_script_text", "")
        anchor_dur = anchor_script.get("estimated_duration_seconds", 0)
        anchor_words = anchor_script.get("estimated_word_count", 0)
        print(f"\n  >> Anchor script: ~{anchor_dur}s, ~{anchor_words} words")
        print(f"  >> Opening: {anchor_script.get('opening_line', 'N/A')[:100]}")
        print(f"  >> Closing hook: {anchor_script.get('closing_hook', 'N/A')[:100]}")
        print(f"  >> Term mentions: {len(anchor_script.get('term_mentions', []))}")

        # ═══════════════════════════════════════════════
        # PHASE 5: WRITE CAT SCRIPT
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  PHASE 5: WRITE CAT CONVERSATION SCRIPT")
        print("=" * 60)

        cat_script = self.writer.write_cat_script(
            term=term,
            anchor_script=anchor_script,
            viral_story=chosen_story,
            historical_research=history,
            enrichment=enrichment or None,
        )

        exchanges = cat_script.get("exchanges", [])
        cat_dur = cat_script.get("estimated_total_duration", 0)
        print(f"\n  >> Cat script: {len(exchanges)} exchanges, ~{cat_dur}s total")
        for ex in exchanges:
            title = ex.get("exchange_title", "?")
            dur = ex.get("duration_seconds", "?")
            num_turns = len(ex.get("dialogue", []))
            print(f"     [{title}] ~{dur}s, {num_turns} turns")

        # ═══════════════════════════════════════════════
        # PHASE 6: FACT CHECK
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  PHASE 6: FACT CHECK")
        print("=" * 60)

        # Check both scripts
        combined_for_check = {
            "anchor_script": anchor_script,
            "cat_script": cat_script,
        }
        fact_check = self.checker.check_script(combined_for_check, history)

        rating = fact_check.get("overall_rating", "UNKNOWN")
        issues = fact_check.get("issues_found", 0)
        print(f"\n  >> Rating: {rating}")
        print(f"  >> Issues: {issues}")

        if rating == "NEEDS_REVISION" and issues > 0:
            print("  >> Sending cat script for revision...")
            corrections = [
                c for c in fact_check.get("checks", [])
                if c.get("rating") in ("NEEDS_CORRECTION", "MISLEADING")
            ]
            feedback = "Fix these issues:\n" + "\n".join(
                f"- {c.get('claim', '')}: {c.get('note', '')}"
                for c in corrections
            )
            cat_script = self.writer.revise_script(cat_script, feedback)
            print("  >> Cat script revised.")

        # ═══════════════════════════════════════════════
        # PHASE 7: EXECUTIVE APPROVAL
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  PHASE 7: EXECUTIVE APPROVAL")
        print("=" * 60)

        approval = self.producer.approve_script(
            {"anchor_script": anchor_script, "cat_script": cat_script},
            fact_check,
        )
        approved = approval.get("approved", True)
        print(f"\n  >> Approved: {approved}")
        if not approved:
            changes = approval.get("suggested_changes", [])
            if changes:
                feedback = "Executive Producer feedback:\n" + "\n".join(
                    f"- {c}" for c in changes
                )
                cat_script = self.writer.revise_script(cat_script, feedback)
                print("  >> Cat script revised per Executive Producer.")

        # ═══════════════════════════════════════════════
        # PHASE 8: CREATIVE + YOUTUBE PACKAGE
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  PHASE 8: CREATIVE + YOUTUBE PACKAGE")
        print("=" * 60)

        # Select TWO cats
        recent_cats = []
        published_eps = self.producer._get_published_episodes(log)
        for ep in published_eps[-5:]:
            recent_cats.append(ep.get("cat_a_id", ""))
            recent_cats.append(ep.get("cat_b_id", ""))
        recent_cats = [c for c in recent_cats if c]

        cat_selection = self.creative.select_cats(recent_cats)
        cat_a = cat_selection.get("cat_a", {})
        cat_b = cat_selection.get("cat_b", {})
        print(f"\n  >> Cat A (Professor): {cat_a.get('cat_id', 'N/A')}")
        print(f"  >> Cat B (Cleo): {cat_b.get('cat_id', 'N/A')}")

        # Design overlays
        overlay_design = self.creative.design_overlays(term, cat_script)

        # YouTube package
        yt_package = self.strategist.create_package(
            term, cat_script, log.get("episodes", [])
        )

        titles = yt_package.get("titles", {})
        print(f"  >> Title: {titles.get('primary', 'N/A')}")
        print(f"  >> Tags: {len(yt_package.get('tags', []))} tags")

        # ═══════════════════════════════════════════════
        # EXTRACT TEASER TERM FOR SERIES CHAINING
        # ═══════════════════════════════════════════════
        teaser_term = cat_script.get("teaser_term", "")
        if teaser_term:
            print(f"  >> Next episode teaser: '{teaser_term}'")

        # ═══════════════════════════════════════════════
        # COMPILE RESULTS
        # ═══════════════════════════════════════════════
        elapsed = time.time() - start
        print("\n" + "=" * 60)
        print(f"  ALL AGENTS COMPLETE | {elapsed:.1f}s")
        print("=" * 60)

        # Series tracking
        series = self.producer._get_current_series(log)

        episode_data = {
            "term": term,
            "category": category,
            "viral_story_headline": chosen_story.get("headline", ""),
            "viral_story_date": story_date,
            "viral_story_summary": chosen_story.get("summary", "")[:500],
            "historical_events_covered": [
                ev.get("event_name", "") for ev in events
            ],
            "cat_a_id": cat_a.get("cat_id", ""),
            "cat_b_id": cat_b.get("cat_id", ""),
            "title": titles.get("primary", ""),
            "tags": yt_package.get("tags", []),
            "description": yt_package.get("description", ""),
            "next_episode_term": teaser_term,
            "video_type": "v3_anchor_cats",
        }

        return {
            "viral_story": chosen_story,
            "term": term,
            "term_info": term_info,
            "category": category,
            "historical_research": history,
            "anchor_script": anchor_script,
            "cat_script": cat_script,
            "fact_check": fact_check,
            "approval": approval,
            "cat_selection": cat_selection,
            "overlay_design": overlay_design,
            "youtube_package": yt_package,
            "episode_data": episode_data,
        }
