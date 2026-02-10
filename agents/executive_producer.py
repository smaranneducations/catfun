"""Executive Producer Agent — The CEO of FinanceCats.

V3: AI Anchor + Cat Conversation format.
  - Tracks next_episode_term from each video's teaser
  - Groups episodes into series (10-15 episodes each)
  - Approves anchor + cat scripts for brand consistency
  - Manages series continuity (episode chaining)
  - No longer picks topics directly — the Viral News Scout does that

Responsibilities:
  - Reads episode_log.json to know what we've already covered
  - Provides queued next_episode_term for series continuity
  - Ensures no repeats of terms, cats, or historical events
  - Maintains brand consistency across episodes
  - Makes final go/no-go decisions on scripts (anchor + cat)
  - Manages series continuity (episode chaining)
"""
import json
import os
import config
from agents.base_agent import Agent


SYSTEM_PROMPT = """You are the Executive Producer of "FinanceCats" — an AI-powered YouTube channel
that creates 3-4 minute finance education videos.

V3 Format: Each video has TWO parts:
  1. An AI-generated female news anchor reads viral economic/geopolitical news
     (she naturally embeds a financial term into her report)
  2. Two cat characters explain that term in a warm, conversational way
     (playing over a frozen frame of the anchor)

Your brand identity:
- AI female news anchor: professional, attractive, high-end studio
- Two cats: Professor Whiskers (calm British expert) and Cleo (curious female questioner)
- Conversational, ultra-simple explanations with real-life analogies
- Each video covers ONE financial term embedded in viral news
- Every episode teases the NEXT term, creating binge-worthy series
- 100% original content (no third-party clips)

Your job:
1. Review the episode log to know what's been covered
2. Provide the queued next_episode_term for series continuity
3. Approve or reject BOTH anchor + cat scripts for brand consistency
4. Manage series: group episodes into series of 10-15, track series_id
5. Ensure the anchor script sounds like real news (not a lecture)
6. Ensure the cat script is warm, educational, and genuinely helpful

Always respond in JSON format."""


class ExecutiveProducer(Agent):
    def __init__(self):
        super().__init__(
            name="Executive Producer",
            role="Brand guardian, decision maker, and series manager",
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL_EXECUTIVE_PRODUCER,
        )

    def load_episode_log(self) -> dict:
        """Load the episode history.

        Includes a migration step: backfills publish_status for old episodes
        that were created before this field existed.
        """
        if os.path.exists(config.EPISODE_LOG_PATH):
            with open(config.EPISODE_LOG_PATH, "r", encoding="utf-8") as f:
                log = json.load(f)

            # Migration: backfill publish_status for legacy episodes
            migrated = False
            for ep in log.get("episodes", []):
                if "publish_status" not in ep:
                    # Infer status from whether youtube_video_id was set
                    if ep.get("youtube_video_id"):
                        ep["publish_status"] = "published"
                    elif ep.get("linkedin_post_id"):
                        ep["publish_status"] = "partial"
                    else:
                        ep["publish_status"] = "failed"
                    migrated = True

            # Migration: backfill published_count on series
            for series in log.get("series", []):
                if "published_count" not in series:
                    sid = series.get("series_id")
                    series["published_count"] = sum(
                        1 for ep in log.get("episodes", [])
                        if ep.get("series_id") == sid
                        and ep.get("publish_status") == "published"
                    )
                    migrated = True

            if migrated:
                self.save_episode_log(log)

            return log

        return {
            "channel_name": "FinanceCats",
            "brand_voice": "Two cats in conversation: Professor Whiskers explains, "
                           "Cleo asks questions. Ultra-simple, real-life analogies.",
            "series": [],
            "episodes": [],
        }

    def save_episode_log(self, log: dict):
        """Save updated episode history."""
        with open(config.EPISODE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

    def _get_published_episodes(self, log: dict) -> list[dict]:
        """Get only episodes that were successfully published."""
        return [
            ep for ep in log.get("episodes", [])
            if ep.get("publish_status") == "published"
        ]

    def _get_current_series(self, log: dict) -> dict:
        """Get the current active series, or create a new one.

        Only counts published episodes toward series capacity.
        """
        series_list = log.get("series", [])

        if series_list:
            latest = series_list[-1]
            # Count only published episodes in this series
            published_in_series = sum(
                1 for ep in log.get("episodes", [])
                if ep.get("series_id") == latest.get("series_id")
                and ep.get("publish_status") == "published"
            )
            latest["published_count"] = published_in_series
            if published_in_series < config.MAX_SERIES_LENGTH:
                return latest

        # Create a new series
        series_id = len(series_list) + 1
        new_series = {
            "series_id": series_id,
            "series_name": f"FinanceCats Series {series_id}",
            "episode_count": 0,
            "published_count": 0,
            "terms_covered": [],
            "status": "active",
        }
        if "series" not in log:
            log["series"] = []
        log["series"].append(new_series)
        return new_series

    def _get_queued_next_term(self, log: dict) -> str:
        """Check if the last PUBLISHED episode teased a specific next term.

        Only follows the teaser chain from published episodes — if the last
        episode failed to upload, we don't chain from it (viewers never saw
        the teaser, so there's no continuity to maintain).
        """
        # Find the last published episode
        published = self._get_published_episodes(log)
        if not published:
            return ""
        last_published = published[-1]
        return last_published.get("next_episode_term", "")

    def get_queued_next_term(self) -> str:
        """Public convenience: get the queued next term from the log."""
        log = self.load_episode_log()
        return self._get_queued_next_term(log)

    def log_episode(self, episode_data: dict):
        """Add a completed episode to the log with series tracking.

        publish_status must be set in episode_data:
          - "published": All uploads verified (YouTube + LinkedIn)
          - "partial": Some uploads succeeded, some failed
          - "failed": All uploads failed
          - "draft": Video composed but uploads skipped (--no-upload)

        Only "published" episodes count toward series progression.
        """
        log = self.load_episode_log()

        # Get/create current series
        series = self._get_current_series(log)
        episode_number = len(log["episodes"]) + 1
        publish_status = episode_data.get("publish_status", "failed")

        # Add series info to episode
        episode_data["episode_number"] = episode_number
        episode_data["series_id"] = series["series_id"]

        # Series position is based on published episodes only
        published_in_series = series.get("published_count", 0)
        if publish_status == "published":
            episode_data["series_position"] = published_in_series + 1
            series["published_count"] = published_in_series + 1
            series["terms_covered"] = series.get("terms_covered", []) + [
                episode_data.get("term", "")
            ]
        else:
            # Not published — don't advance series position
            episode_data["series_position"] = 0  # 0 = not in series yet

        # Always increment total episode_count (for numbering)
        series["episode_count"] = series.get("episode_count", 0) + 1

        # Check if series is now complete (only published episodes count)
        if series.get("published_count", 0) >= config.DEFAULT_SERIES_LENGTH:
            series["status"] = "complete"

        log["episodes"].append(episode_data)
        self.save_episode_log(log)

        status_icon = {"published": "OK", "partial": "PARTIAL",
                       "failed": "FAIL", "draft": "DRAFT"}.get(publish_status, "?")
        print(f"    [Episode Log] [{status_icon}] Episode #{episode_number} "
              f"(Series {series['series_id']}, "
              f"publish_status={publish_status})")

        if publish_status == "published":
            print(f"    [Episode Log] Series position: {episode_data['series_position']} "
                  f"(published: {series.get('published_count', 0)}/{config.DEFAULT_SERIES_LENGTH})")
            next_term = episode_data.get("next_episode_term", "")
            if next_term:
                print(f"    [Episode Log] Next episode queued: '{next_term}'")
        elif publish_status in ("failed", "partial"):
            print(f"    [Episode Log] Upload incomplete — this episode can be retried with: "
                  f"python main.py --retry")

        return episode_number

    def update_episode_status(self, episode_number: int, updates: dict):
        """Update an existing episode's status (used for retry).

        Args:
            episode_number: The episode number to update
            updates: Dict of fields to update (e.g. publish_status, youtube_video_id, etc.)
        """
        log = self.load_episode_log()
        episodes = log.get("episodes", [])

        for ep in episodes:
            if ep.get("episode_number") == episode_number:
                old_status = ep.get("publish_status", "")
                ep.update(updates)
                new_status = ep.get("publish_status", "")

                # If upgrading to "published", update series tracking
                if old_status != "published" and new_status == "published":
                    series_id = ep.get("series_id")
                    for s in log.get("series", []):
                        if s.get("series_id") == series_id:
                            s["published_count"] = s.get("published_count", 0) + 1
                            term = ep.get("term", "")
                            if term and term not in s.get("terms_covered", []):
                                s["terms_covered"] = s.get("terms_covered", []) + [term]
                            # Set series position
                            ep["series_position"] = s["published_count"]
                            # Check if series is complete
                            if s["published_count"] >= config.DEFAULT_SERIES_LENGTH:
                                s["status"] = "complete"
                            break

                self.save_episode_log(log)
                print(f"    [Episode Log] Updated episode #{episode_number}: "
                      f"{old_status} -> {new_status}")
                return True

        print(f"    [Episode Log] Episode #{episode_number} not found!")
        return False

    def get_last_unpublished_episode(self) -> dict | None:
        """Find the most recent episode that wasn't fully published.

        Used by --retry to find what needs re-uploading.
        """
        log = self.load_episode_log()
        episodes = log.get("episodes", [])

        # Search from most recent backward
        for ep in reversed(episodes):
            status = ep.get("publish_status", "")
            if status in ("failed", "partial", "draft"):
                return ep

        return None

    def decide_next_topic(self) -> dict:
        """Decide what finance term/topic to cover next.

        Logic:
          1. If there's an unpublished episode (failed/partial), suggest retrying it
          2. If the last PUBLISHED episode teased a term, use that (series continuity)
          3. Otherwise, pick a fresh term

        Only PUBLISHED episodes count as "covered" for term dedup.
        All episodes (including failed) are checked to avoid re-generating
        the same video file.
        """
        log = self.load_episode_log()

        # Check for queued next term from series continuity (published only)
        queued_term = self._get_queued_next_term(log)

        # Published terms = truly covered (viewers have seen them)
        published_eps = self._get_published_episodes(log)
        published_terms = [ep.get("term", "") for ep in published_eps]

        # All terms ever attempted (to avoid regenerating same content)
        all_terms = [ep.get("term", "") for ep in log.get("episodes", [])]

        covered_categories = [ep.get("category", "") for ep in published_eps]
        covered_events = []
        for ep in published_eps:
            covered_events.extend(ep.get("historical_events_covered", []))

        series = self._get_current_series(log)

        context = {
            "total_episodes_published": len(published_eps),
            "total_episodes_attempted": len(log.get("episodes", [])),
            "terms_already_published": published_terms,
            "terms_already_covered": all_terms,
            "categories_used_recently": covered_categories[-5:],
            "historical_events_used": covered_events[-10:],
            "cats_used_recently": [ep.get("cat_a_id") for ep in published_eps[-5:]],
            "current_series": {
                "series_id": series.get("series_id", 1),
                "published_in_series": series.get("published_count", 0),
                "terms_in_series": series.get("terms_covered", []),
                "target_length": config.DEFAULT_SERIES_LENGTH,
            },
            "queued_next_term": queued_term,
        }

        if queued_term and queued_term not in all_terms:
            # Use the teased term from previous episode
            result = self.think(
                task=(
                    f"The previous episode teased '{queued_term}' as the next topic.\n"
                    f"Use this term to maintain series continuity.\n\n"
                    "Return JSON with: term, category, why_now (what recent news uses "
                    "this term), search_queries (3 simple YouTube search queries — "
                    "do NOT use site: or other Google operators, just plain keywords "
                    "like 'quantitative tightening CNBC 2026'), "
                    "difficulty (1-5 how complex to explain), "
                    "is_series_continuation (true)"
                ),
                context=context,
                temperature=0.5,
            )
        else:
            result = self.think(
                task=(
                    "Decide the next finance term to cover. Pick a term that:\n"
                    "1. Is currently relevant in financial news (2025-2026)\n"
                    "2. Has NOT been covered before\n"
                    "3. Is in a different category than the last 2-3 episodes\n"
                    "4. Has rich historical examples to draw from\n"
                    "5. Would be searched by people trying to understand finance news\n"
                    "6. Sounds complex but can be explained simply\n"
                    "7. Flows naturally from previous topics in the series\n\n"
                    "Return JSON with: term, category, why_now (what recent news uses "
                    "this term), search_queries (3 simple YouTube search queries — "
                    "do NOT use site: or other Google operators, just plain keywords "
                    "like 'quantitative tightening CNBC 2026' or 'interest rate hike "
                    "Bloomberg news'), difficulty (1-5 how complex to explain), "
                    "is_series_continuation (false)"
                ),
                context=context,
                temperature=0.7,
            )
        return result

    def approve_script(self, scripts: dict, fact_check: dict) -> dict:
        """Review and approve/reject anchor + cat scripts.

        Args:
            scripts: dict with 'anchor_script' and 'cat_script'
            fact_check: Fact checker results
        """
        result = self.think(
            task=(
                "Review BOTH the anchor script and cat conversation script for V3.\n\n"
                "CHECK THE ANCHOR SCRIPT:\n"
                "1. Does it start with 'OK, this news is from [date]'?\n"
                "2. Does it sound like a real TV news broadcast?\n"
                "3. Is the financial term naturally embedded (not forced)?\n"
                "4. Does it end with a hook leading to the cats?\n"
                "5. Is it 60-90 seconds (not too long)?\n\n"
                "CHECK THE CAT SCRIPT:\n"
                "1. Does the conversation feel NATURAL?\n"
                "2. Are explanations ultra-simple with real-life analogies?\n"
                "3. Does Cleo push for simpler explanations when needed?\n"
                "4. Do historical examples enhance understanding?\n"
                "5. Is the pacing right for 2-3 minutes?\n"
                "6. Does the teaser for next episode create curiosity?\n"
                "7. Do the cats reference what the anchor said?\n\n"
                "Return JSON with: approved (bool), feedback (str), "
                "suggested_changes (list of specific changes if not approved)"
            ),
            context={"scripts": scripts, "fact_check_results": fact_check},
            temperature=0.3,
        )
        return result
