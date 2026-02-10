"""Agent Orchestrator — Coordinates all 7 agents to produce a finance education video.

Flow:
  1. Executive Producer decides topic + reads episode log
  2. Research Analyst finds news clips on YouTube
  3. Download clip + get transcript (pipeline)
  4. Financial Historian researches the term
  5. Script Writer creates the full 6-segment script
  6. Fact Checker verifies all claims
  7. Executive Producer approves (or sends back for revision)
  8. Creative Director selects cat + designs overlays
  9. YouTube Strategist creates SEO package
  10. Return everything to pipeline for production
"""
import json
import os
import time
import config
from agents.executive_producer import ExecutiveProducer
from agents.research_analyst import ResearchAnalyst
from agents.financial_historian import FinancialHistorian
from agents.script_writer import ScriptWriter
from agents.fact_checker import FactChecker
from agents.creative_director import CreativeDirector
from agents.youtube_strategist import YouTubeStrategist


class AgentOrchestrator:
    """Orchestrates all 7 agents for FinanceCats video production."""

    def __init__(self):
        print("\n  Initialising 7-Agent System...")
        self.producer = ExecutiveProducer()
        self.researcher = ResearchAnalyst()
        self.historian = FinancialHistorian()
        self.writer = ScriptWriter()
        self.checker = FactChecker()
        self.creative = CreativeDirector()
        self.strategist = YouTubeStrategist()
        print("  All agents ready.\n")

    def run_full_pipeline(self, transcript: str = None,
                          clip_info: dict = None) -> dict:
        """Run the complete 7-agent pipeline.

        Args:
            transcript: Formatted transcript from the news clip (if already downloaded)
            clip_info: Info about a pre-selected clip (url, timestamps, etc.)

        Returns:
            dict with: topic, script, fact_check, creative, youtube_package, episode_data
        """
        start = time.time()
        total_cost = 0.0

        # ═══════════════════════════════════════════════
        # PHASE 1: TOPIC SELECTION
        # ═══════════════════════════════════════════════
        print("=" * 60)
        print("  PHASE 1: TOPIC SELECTION")
        print("=" * 60)

        topic = self.producer.decide_next_topic()
        term = topic.get("term", "Unknown Term")
        category = topic.get("category", "general")
        search_queries = topic.get("search_queries", [f"{term} news", f"{term} explained"])

        print(f"\n  >> Topic: {term}")
        print(f"  >> Category: {category}")
        print(f"  >> Why now: {topic.get('why_now', 'N/A')}")
        print(f"  >> Search queries: {search_queries}\n")

        # ═══════════════════════════════════════════════
        # PHASE 2: FIND NEWS CLIP
        # ═══════════════════════════════════════════════
        print("=" * 60)
        print("  PHASE 2: FIND NEWS CLIP")
        print("=" * 60)

        if clip_info and clip_info.get("url"):
            print("  Using pre-selected clip.")
            selected_clip = clip_info
        else:
            # Search YouTube
            candidates = self.researcher.search_youtube(search_queries)

            if candidates:
                # Get transcripts for top candidates (done in main pipeline)
                # For now, return candidates for the pipeline to process
                selected_clip = {
                    "candidates": candidates,
                    "search_queries": search_queries,
                    "needs_transcript_check": True,
                }
            else:
                # Ask LLM for suggestions
                suggestions = self.researcher.suggest_clips_via_llm(term, search_queries)
                selected_clip = {
                    "candidates": [],
                    "suggestions": suggestions,
                    "needs_manual_selection": True,
                }

        print(f"  >> Clip status: {len(selected_clip.get('candidates', []))} candidates found\n")

        # ═══════════════════════════════════════════════
        # PHASE 3: HISTORICAL RESEARCH
        # ═══════════════════════════════════════════════
        print("=" * 60)
        print("  PHASE 3: HISTORICAL RESEARCH")
        print("=" * 60)

        log = self.producer.load_episode_log()
        covered_events = []
        for ep in log.get("episodes", []):
            covered_events.extend(ep.get("historical_events_covered", []))

        history = self.historian.research_term(term, category, covered_events)

        events = history.get("historical_events", [])
        print(f"\n  >> Found {len(events)} historical events:")
        for ev in events:
            print(f"     - {ev.get('event_name', '?')} ({ev.get('date', '?')})")
        print(f"  >> Definition: {history.get('simple_definition', 'N/A')[:100]}...\n")

        # ═══════════════════════════════════════════════
        # PHASE 4: SCRIPT WRITING
        # ═══════════════════════════════════════════════
        print("=" * 60)
        print("  PHASE 4: SCRIPT WRITING")
        print("=" * 60)

        script = self.writer.write_script(
            term=term,
            news_clip_info=selected_clip,
            historical_research=history,
            transcript=transcript or "",
        )

        segments = script.get("segments", [])
        total_dur = script.get("estimated_total_duration", 0)
        print(f"\n  >> Script: {len(segments)} segments, ~{total_dur}s total")
        for seg in segments:
            print(f"     [{seg.get('type', '?')}] {seg.get('duration_seconds', '?')}s")
        print()

        # ═══════════════════════════════════════════════
        # PHASE 5: FACT CHECK
        # ═══════════════════════════════════════════════
        print("=" * 60)
        print("  PHASE 5: FACT CHECK")
        print("=" * 60)

        fact_check = self.checker.check_script(script, history)

        rating = fact_check.get("overall_rating", "UNKNOWN")
        issues = fact_check.get("issues_found", 0)
        print(f"\n  >> Rating: {rating}")
        print(f"  >> Claims checked: {fact_check.get('total_claims_checked', 0)}")
        print(f"  >> Issues: {issues}")

        # If issues, revise script
        if rating == "NEEDS_REVISION" and issues > 0:
            print("  >> Sending script back for revision...\n")
            corrections = [
                c for c in fact_check.get("checks", [])
                if c.get("rating") in ("NEEDS_CORRECTION", "MISLEADING")
            ]
            feedback = "Fix these issues:\n" + "\n".join(
                f"- {c.get('claim', '')}: {c.get('note', '')}"
                for c in corrections
            )
            script = self.writer.revise_script(script, feedback)
            print("  >> Script revised.\n")

        # ═══════════════════════════════════════════════
        # PHASE 6: EXECUTIVE APPROVAL
        # ═══════════════════════════════════════════════
        print("=" * 60)
        print("  PHASE 6: EXECUTIVE APPROVAL")
        print("=" * 60)

        approval = self.producer.approve_script(script, fact_check)
        approved = approval.get("approved", True)
        print(f"\n  >> Approved: {approved}")
        print(f"  >> Feedback: {approval.get('feedback', 'N/A')[:200]}")

        if not approved:
            # One more revision attempt
            changes = approval.get("suggested_changes", [])
            if changes:
                feedback = "Executive Producer feedback:\n" + "\n".join(
                    f"- {c}" for c in changes
                )
                script = self.writer.revise_script(script, feedback)
                print("  >> Script revised per Executive Producer.\n")

        # ═══════════════════════════════════════════════
        # PHASE 7: CREATIVE + YOUTUBE PACKAGE
        # ═══════════════════════════════════════════════
        print("=" * 60)
        print("  PHASE 7: CREATIVE + YOUTUBE PACKAGE")
        print("=" * 60)

        # Select cat
        recent_cats = [
            ep.get("cat_id") for ep in log.get("episodes", [])[-5:]
        ]
        cat_selection = self.creative.select_cat(recent_cats)
        print(f"\n  >> Cat: {cat_selection.get('cat_id', 'N/A')}")

        # Design overlays
        overlay_design = self.creative.design_overlays(term, script)

        # YouTube package
        yt_package = self.strategist.create_package(
            term, script, log.get("episodes", [])
        )

        titles = yt_package.get("titles", {})
        print(f"  >> Title: {titles.get('primary', 'N/A')}")
        print(f"  >> Tags: {len(yt_package.get('tags', []))} tags")
        print(f"  >> Thumbnail: {yt_package.get('thumbnail_text', 'N/A')}\n")

        # ═══════════════════════════════════════════════
        # COMPILE RESULTS
        # ═══════════════════════════════════════════════
        elapsed = time.time() - start
        print("=" * 60)
        print(f"  ALL AGENTS COMPLETE | {elapsed:.1f}s")
        print("=" * 60)

        # Prepare episode data for logging (will be saved after video is rendered)
        episode_data = {
            "term": term,
            "category": category,
            "news_source": selected_clip.get("channel", ""),
            "news_clip_url": selected_clip.get("url", ""),
            "historical_events_covered": [
                ev.get("event_name", "") for ev in events
            ],
            "cat_id": cat_selection.get("cat_id", ""),
            "title": titles.get("primary", ""),
            "tags": yt_package.get("tags", []),
            "description": yt_package.get("description", ""),
        }

        return {
            "topic": topic,
            "term": term,
            "category": category,
            "selected_clip": selected_clip,
            "historical_research": history,
            "script": script,
            "fact_check": fact_check,
            "approval": approval,
            "cat_selection": cat_selection,
            "overlay_design": overlay_design,
            "youtube_package": yt_package,
            "episode_data": episode_data,
        }
