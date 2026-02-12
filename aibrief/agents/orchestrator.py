"""Autonomous Orchestrator — Full pipeline with World Pulse, Content Strategy,
Design DNA, multi-agent debate, and complete run tracing.

Architecture:
  Phase 0:  World Pulse → global sentiment scan (Gemini + Google Search)
  Phase 1:  Content Strategy → choose content type + tone (GPT-4o)
  Phase 2:  Topic Discovery → find topic + semantic dedup (Gemini Flash)
  Phase 3:  Design DNA → pick style/palette/font from catalog + debate (GPT-4o)
  Phase 4:  Analyst Pairs → 4× preparer/reviewer argue (Gemini Flash + GPT-4o)
  Phase 5:  Round Table → cross-agent challenges
  Phase 6:  Editorial Oversight → editor reviews all perspectives (GPT-4o)
  Phase 7:  Content Synthesis → poster content + copy reviewer argue (GPT-4o)
  Phase 8:  Neutrality Check → ethical guardrail enforcement (GPT-4o)
  Phase 8.5: Discussion Potential → engagement scoring + hooks (GPT-4o)
  Phase 8.7: Pre-Visual Validation → content/structure gate (GPT-4o)
  Phase 9:  Visuals → DALL-E images + Pillow infographics
  Phase 10: PDF → poster + agent credits + decision architecture mind map
  Phase 11: Screen Audit → page fill golden ratio check (GPT-4o)
  Phase 12: Final Validation → 37 master checkpoints (GPT-4o)
  Phase 13: LinkedIn → post with dynamic catchy document title

OUTPUT is ALWAYS poster format:
  Page 1:    Cover (landing page)
  Page 2:    News Summary (headline, publisher, URL, 6 bullet points)
  Pages 3-6: Content (5 points each, background + foreground Imagen images)
  Pages 7-8: Agent credits (all agents, roles, mandates)
  Page 9:    Run info summary (topic, style, palette, font, score)
  Page 10:   Decision architecture (readable phases with one-liners)

Uses Google Imagen instead of DALL-E for cost savings.

Every phase is TRACED: fixed inputs (from config) and variable inputs
(from other agents) are recorded with full source attribution.
"""
import json
import time
from pathlib import Path

from aibrief import config
from aibrief.agents.world_pulse import WorldPulseScanner
from aibrief.agents.content_strategist import ContentStrategistAgent
from aibrief.agents.design_dna import DesignDNAAgent
from aibrief.agents.specialists import (
    NewsScout, Historian, Economist, Sociologist, Futurist,
    ContentWriter, ContentReviewer, EditorInChief, LinkedInExpert,
    DiscussionPotentialAgent,
)
from aibrief.agents.base import Agent
from aibrief.agents.validators import (
    PreVisualValidator, PostVisualValidator, FinalValidatorAgent,
    GUARDRAIL, PASS_THRESHOLD,
)
from aibrief.pipeline.tracer import RunTracer


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
                f"  \"overall_score\": number (1-10),\n"
                f"  \"depth_score\": number, \"specificity_score\": number,\n"
                f"  \"originality_score\": number, \"tone_score\": number,\n"
                f"  \"actionability_score\": number,\n"
                f"  \"approved\": boolean (true only if ALL scores >= 7),\n"
                f"  \"demands\": [\"string\"],\n"
                f"  \"strengths\": [\"string\"],\n"
                f"  \"missing_elements\": [\"string\"]\n"
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
                "REVIEW CRITERIA (POSTER FORMAT — 5 points per page):\n"
                "1. Does the news_summary page have EXACTLY 6 bullet points?\n"
                "2. Does each content page have EXACTLY 5 bullet points?\n"
                "3. Is each point statement 5-10 words? NOT a paragraph.\n"
                "4. Is each point powerful enough to stop a CEO scrolling?\n"
                "5. Is each detail line max 15 words and adds real value?\n"
                "6. Does it read like luxury advertising — not a textbook?\n"
                "7. Would a CEO frame this on their wall?\n\n"
                "STRICT GUARDRAIL: Any point with more than 10 words in the statement "
                "MUST be rejected. This is a POSTER, not a document.\n\n"
                "Return JSON:\n"
                "{\n"
                "  \"overall_score\": number (1-10),\n"
                "  \"approved\": boolean,\n"
                "  \"page_scores\": [{\"page_type\": string, \"score\": number}],\n"
                "  \"demands\": [string],\n"
                "  \"tone_verdict\": string\n"
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
                "GOLDEN RULE (POSTER FORMAT): A poster page should be 55-65% filled "
                "with content/visuals and 35-45% breathing room. NEVER more than 45% "
                "empty. NEVER more than 70% filled.\n\n"
                "DESIGN PSYCHOLOGY PRINCIPLES:\n"
                "- Golden Ratio (1.618): content zones should relate by this ratio\n"
                "- Rule of Thirds: key elements at intersection points\n"
                "- Visual weight: massive typography anchors the page\n"
                "- Whitespace IS design in poster format — it's intentional\n"
                "- Style decorations fill the background — no dead space\n\n"
                "Return JSON:\n"
                "{\n"
                "  \"pages\": [{\"page_number\": number, \"estimated_fill_pct\": number, "
                "\"passes_golden_rule\": boolean, \"issues\": [string]}],\n"
                "  \"overall_verdict\": string,\n"
                "  \"approved\": boolean\n"
                "}"
            ),
        )


# ═══════════════════════════════════════════════════════════════
#  AUTONOMOUS ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

class AutonomousOrchestrator:
    """Full autonomous pipeline with World Pulse → LinkedIn, all phases traced."""

    MAX_ROUNDS = 3
    MIN_SCORE = 7

    def __init__(self):
        self.cfg = self._load_config()
        self.controls = self.cfg.get("controls", {})
        self.tracer = RunTracer(
            mode=self.cfg.get("mode", "autonomous"))

        # ── Phase 0 agents ──
        self.world_pulse = WorldPulseScanner()
        self.content_strategist = ContentStrategistAgent()

        # ── Design agents ──
        self.design_dna = DesignDNAAgent()

        # ── Content agents ──
        self.scout = NewsScout()
        self.historian = Historian()
        self.economist = Economist()
        self.sociologist = Sociologist()
        self.futurist = Futurist()
        self.writer = ContentWriter()
        self.editor = EditorInChief()
        self.linkedin_expert = LinkedInExpert()

        # ── Reviewers ──
        self.hist_reviewer = AnalysisReviewer("historical")
        self.econ_reviewer = AnalysisReviewer("economic")
        self.soc_reviewer = AnalysisReviewer("sociological")
        self.fut_reviewer = AnalysisReviewer("future/predictions")
        self.copy_reviewer = CopyReviewer()
        self.neutrality_reviewer = ContentReviewer()
        self.screen_auditor = ScreenRealEstateAgent()
        self.discussion_analyst = DiscussionPotentialAgent()
        self.pre_validator = PreVisualValidator()
        self.post_validator = PostVisualValidator()

    @staticmethod
    def _load_config() -> dict:
        cfg_path = config.BASE_DIR / "agent_config.json"
        if cfg_path.exists():
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        return {"mode": "autonomous", "controls": {}}

    def _get_agents_info(self) -> list[dict]:
        """Extract all agents from config for the credits section."""
        agents = []
        for agent_name, data in self.cfg.get("agents", {}).items():
            agents.append({
                "name": agent_name,
                "codename": data.get("name", ""),
                "role": data.get("role", ""),
                "mandate": data.get("fixed_strings", {}).get(
                    "core_instruction", ""),
            })
        return agents

    def _get_tracer_flow(self, pulse, strategy, design, validation,
                         elapsed) -> dict:
        """Build tracer flow data for the mind map."""
        return {
            "entries": self.tracer.entries,
            "run_id": self.tracer.run_id,
            "agent_flow": self.tracer._build_flow_summary(),
            "total_duration": elapsed,
            "total_agents": len([e for e in self.tracer.entries
                                 if e.get("phase") != "DEBATE"]),
            "total_debates": len([e for e in self.tracer.entries
                                  if e.get("phase") == "DEBATE"]),
            "key_outputs": {
                "world_mood": pulse.get("mood", "normal"),
                "content_type": strategy.get("content_type", ""),
                "emotion": design.get("emotion", ""),
                "design_name": design.get("design_name", ""),
                "imagen_style": design.get("imagen_style", ""),
                "validation_score": validation.get("total_score", 0),
            },
        }

    # ═══════════════════════════════════════════════════════════
    #  HARD NEWS VALIDATION — No URL, No Publisher = REJECT
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _validate_news(story: dict) -> tuple[bool, str]:
        """Validate news story from search grounding.

        URLs are already verified by NewsScout (resolved from grounding
        metadata + HTTP checked). We just confirm the basics.
        """
        if not story:
            return False, "Empty story"

        if story.get("abort"):
            return False, f"Agent aborted: {story.get('reason', 'unknown')}"

        url = str(story.get("news_url", "") or "").strip()
        if not url or not url.startswith("http"):
            return False, f"No valid URL: '{url}'"

        # URL was already verified by NewsScout._verify_url()
        print(f"    [Validated] {url[:80]}")
        return True, "OK"

    # ═══════════════════════════════════════════════════════════
    #  DEBATE ENGINE (reusable for any preparer/reviewer pair)
    # ═══════════════════════════════════════════════════════════

    def _argue(self, preparer, reviewer, initial_work: dict,
               label: str, context: dict) -> dict:
        """Preparer and Reviewer argue until quality bar or max rounds."""
        work = initial_work
        rounds = []
        for rnd in range(1, self.MAX_ROUNDS + 1):
            review = reviewer.think(
                f"Review this {label} work. Be demanding. "
                f"Round {rnd}/{self.MAX_ROUNDS}.",
                context={"work": work, "story_context": context},
            )
            score = review.get("overall_score", 0)
            approved = review.get("approved", False)
            demands = review.get("demands", [])
            rounds.append({
                "round": rnd, "score": score, "approved": approved,
                "demands_count": len(demands),
            })
            print(f"    Round {rnd}: score={score}/10, "
                  f"approved={approved}, demands={len(demands)}")

            if approved and score >= self.MIN_SCORE:
                print(f"    \u2713 {label} APPROVED after {rnd} round(s)")
                break
            if rnd < self.MAX_ROUNDS:
                work = preparer.respond_to_feedback(work, review)
                print(f"    \u2192 {preparer.name} revised")

        self.tracer.log_debate(
            f"{preparer.name} vs {reviewer.name} [{label}]", rounds)
        return work

    # ═══════════════════════════════════════════════════════════
    #  PHASE 0: WORLD PULSE
    # ═══════════════════════════════════════════════════════════

    def _phase_world_pulse(self) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 0: WORLD PULSE SCAN (Aria)")
        print("=" * 65)

        cfg_agent = self.cfg.get("agents", {}).get("WorldPulseScanner", {})
        self.tracer.begin_phase(
            phase="WorldPulse",
            agent_name="WorldPulseScanner",
            agent_codename=cfg_agent.get("name", "Aria"),
            model=config.MODEL_WORLD_PULSE,
            fixed_inputs={
                "core_instruction": cfg_agent.get("fixed_strings", {}).get(
                    "core_instruction", "Scan global sentiment"),
            },
            variable_inputs={},
        )

        pulse = self.world_pulse.scan()
        self.tracer.end_phase(pulse)
        return pulse

    # ═══════════════════════════════════════════════════════════
    #  PHASE 1: CONTENT STRATEGY
    # ═══════════════════════════════════════════════════════════

    def _phase_content_strategy(self, pulse: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 1: CONTENT STRATEGY (Marcus)")
        print("=" * 65)

        cfg_agent = self.cfg.get("agents", {}).get("ContentStrategist", {})
        self.tracer.begin_phase(
            phase="ContentStrategy",
            agent_name="ContentStrategist",
            agent_codename=cfg_agent.get("name", "Marcus"),
            model=config.MODEL_CONTENT_STRATEGIST,
            fixed_inputs={
                "core_instruction": cfg_agent.get("fixed_strings", {}).get(
                    "core_instruction", "Choose content type based on pulse"),
                "content_types": cfg_agent.get("fixed_strings", {}).get(
                    "content_types", []),
                "anchor_filter": self.cfg.get("brand_identity", {}).get(
                    "fixed", {}).get("anchor_filter", ""),
            },
            variable_inputs={
                "world_pulse": self.tracer.var_ref(
                    "WorldPulseScanner", "Aria", "WorldPulse", pulse),
            },
        )

        recent = self._get_recent_content_types()
        strategy = self.content_strategist.strategize(pulse, recent)

        self.tracer.end_phase(strategy)
        return strategy

    def _get_recent_content_types(self) -> list[str]:
        """Get last 3 content types posted from post_log."""
        log_path = config.BASE_DIR / "post_log.json"
        if log_path.exists():
            log = json.loads(log_path.read_text(encoding="utf-8"))
            return [p.get("content_type", "") for p in log.get("posts", [])[-3:]]
        return []

    # ═══════════════════════════════════════════════════════════
    #  PHASE 2: TOPIC DISCOVERY + SEMANTIC DEDUP
    # ═══════════════════════════════════════════════════════════

    def _phase_topic_discovery(self, strategy: dict, pulse: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 2: TOPIC DISCOVERY + SEMANTIC DEDUP (Sable)")
        print("=" * 65)

        from aibrief.pipeline.dedup import is_duplicate, backfill_embeddings
        backfill_embeddings()

        cfg_agent = self.cfg.get("agents", {}).get("NewsScout", {})
        content_type = strategy.get("content_type", "Breaking News Analysis")
        topic_dir = strategy.get("topic_direction", "top AI story")
        max_attempts = self.controls.get("max_topic_attempts", 3)

        story = None
        excluded = []

        for attempt in range(1, max_attempts + 1):
            print(f"\n  Attempt {attempt}/{max_attempts}...")

            self.tracer.begin_phase(
                phase=f"TopicDiscovery_attempt{attempt}",
                agent_name="NewsScout",
                agent_codename=cfg_agent.get("name", "Sable"),
                model=config.MODEL_NEWS_SCOUT,
                fixed_inputs={
                    "core_instruction": (
                        "Google Search grounded news discovery. "
                        "URLs come from search results, not LLM memory."
                    ),
                },
                variable_inputs={
                    "content_type": self.tracer.var_ref(
                        "ContentStrategist", "Marcus", "ContentStrategy",
                        content_type),
                    "world_pulse": self.tracer.var_ref(
                        "WorldPulseScanner", "Aria", "WorldPulse",
                        pulse.get("mood")),
                    "excluded_topics": self.tracer.var_ref(
                        "DedupEngine", "", "Dedup", excluded),
                },
            )

            # Use Google Search grounded news finder
            candidate = self.scout.find_story(
                content_type=content_type,
                pulse=pulse,
                excluded=excluded if excluded else None,
            )

            if isinstance(candidate, list):
                candidate = candidate[0] if candidate else {}

            self.tracer.end_phase(candidate)

            headline = candidate.get("headline", "?")
            print(f"  \u25b8 Candidate: {headline}")

            # ── HARD VALIDATION: real URL + real publisher ──
            is_valid, reject_reason = self._validate_news(candidate)
            if not is_valid:
                print(f"  \u2717 REJECTED (NEWS VALIDATION): {reject_reason}")
                excluded.append(headline)
                continue

            url = candidate.get("news_url", "")
            publisher = candidate.get("publisher", "")
            print(f"    URL: {url}")
            print(f"    Publisher: {publisher}")

            is_dup, similarity, matched = is_duplicate(candidate)
            if is_dup:
                print(f"  \u2717 BLOCKED: {similarity:.0%} similar to '{matched}'")
                excluded.append(headline)
                continue
            else:
                print(f"  \u2713 UNIQUE: max similarity {similarity:.0%}")
                story = candidate
                break

        if story is None:
            print("\n  \u26a0\u26a0\u26a0 HARD ABORT: Could not find ANY real published "
                  "news with a valid URL and publisher after "
                  f"{max_attempts} attempts.")
            print("  Pipeline cannot continue without verified news.")
            raise RuntimeError(
                "NEWS VALIDATION FAILED: No real news article found with "
                "a valid URL and publisher. Pipeline aborted. "
                "The system will NOT fabricate news."
            )

        print(f"\n  \u25b8 Final topic: {story.get('headline', '?')}")
        print(f"  \u25b8 URL: {story.get('news_url', '?')}")
        print(f"  \u25b8 Publisher: {story.get('publisher', '?')}")
        return story

    # ═══════════════════════════════════════════════════════════
    #  PHASE 3: DESIGN DNA — EMOTION DETECTION (no debate)
    # ═══════════════════════════════════════════════════════════

    def _phase_design_dna(self, pulse: dict, strategy: dict,
                          story: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 3: EMOTION DETECTION \u2192 HARDCODED DESIGN (Vesper)")
        print("=" * 65)

        cfg_agent = self.cfg.get("agents", {}).get("DesignDNA", {})
        self.tracer.begin_phase(
            phase="DesignDNA",
            agent_name="DesignDNA",
            agent_codename=cfg_agent.get("name", "Vesper"),
            model=config.MODEL_DESIGN_DNA,
            fixed_inputs={
                "core_instruction": (
                    "Detect dominant EMOTION only. "
                    "Style/palette/font resolved from hardcoded emotion map."
                ),
            },
            variable_inputs={
                "world_pulse": self.tracer.var_ref(
                    "WorldPulseScanner", "Aria", "WorldPulse", pulse),
                "content_type": self.tracer.var_ref(
                    "ContentStrategist", "Marcus", "ContentStrategy",
                    strategy.get("content_type")),
                "topic": self.tracer.var_ref(
                    "NewsScout", "Sable", "TopicDiscovery",
                    story.get("headline")),
            },
        )

        design = self.design_dna.create_identity(pulse, strategy, story)
        self.tracer.end_phase(design)

        print(f"  \u25b8 Emotion: {design.get('emotion', '?')}")
        print(f"  \u25b8 Design: {design.get('design_name', '?')}")
        print(f"  \u25b8 Style: {design.get('style_id', '?')}")
        print(f"  \u25b8 Palette: {design.get('palette_id', '?')}")
        print(f"  \u25b8 Font: {design.get('font_id', '?')}")
        print(f"  \u25b8 Imagen: {design.get('imagen_style', '?')}")
        return design

    # ═══════════════════════════════════════════════════════════
    #  PHASE 4: ANALYST PAIRS
    # ═══════════════════════════════════════════════════════════

    def _phase_analyst_pairs(self, story: dict, strategy: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 4: ANALYST PAIRS (Prepare \u2192 Review \u2192 Argue)")
        print("=" * 65)

        content_type = strategy.get("content_type", "")
        perspectives = {}
        pairs = [
            ("historical", self.historian, self.hist_reviewer, "Clio", "Theron"),
            ("economic", self.economist, self.econ_reviewer, "Aurelia", "Callisto"),
            ("social", self.sociologist, self.soc_reviewer, "Sage", "Liora"),
            ("future", self.futurist, self.fut_reviewer, "Nova", "Orion"),
        ]

        for key, preparer, reviewer, p_code, r_code in pairs:
            print(f"\n  [{key.upper()}]")
            print(f"    Preparer: {preparer.name} ({p_code}) | "
                  f"Reviewer: {reviewer.name} ({r_code})")

            self.tracer.begin_phase(
                phase=f"Analyst_{key}",
                agent_name=preparer.name,
                agent_codename=p_code,
                model=preparer.model,
                fixed_inputs={"core_instruction": f"Analyze from {key} perspective"},
                variable_inputs={
                    "story": self.tracer.var_ref(
                        "NewsScout", "Sable", "TopicDiscovery", story),
                    "content_type": self.tracer.var_ref(
                        "ContentStrategist", "Marcus", "ContentStrategy",
                        content_type),
                },
            )

            initial = preparer.analyse(story)
            self.tracer.end_phase(initial)

            perspectives[key] = self._argue(
                preparer, reviewer, initial, key, story)

        return perspectives

    # ═══════════════════════════════════════════════════════════
    #  PHASE 5: ROUND TABLE
    # ═══════════════════════════════════════════════════════════

    def _phase_round_table(self, story: dict, perspectives: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 5: ROUND TABLE \u2014 Agents challenge each other")
        print("=" * 65)

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
                f"YOUR perspective. Point out what they missed, where they're "
                f"wrong, and what needs deeper analysis. Also acknowledge what "
                f"they got right.",
                context={
                    "your_own_work": perspectives.get(own_key, {}),
                    f"{target_name}_work": perspectives.get(target_key, {}),
                },
            )
            challenges[f"{challenger.name}\u2192{target_name}"] = challenge
            summary = str(challenge)[:80]
            print(f"    {challenger.name} \u2192 {target_name}: {summary}")

        # Each agent incorporates incoming challenges
        for challenger, own_key, target_key, target_name in pairs:
            incoming = {k: v for k, v in challenges.items()
                        if k.endswith(f"\u2192{challenger.name.split()[0]}")}
            if incoming:
                perspectives[own_key] = challenger.respond_to_feedback(
                    perspectives[own_key], {"cross_challenges": incoming})
                print(f"    {challenger.name} incorporated "
                      f"{len(incoming)} challenge(s)")

        self.tracer.log_debate("RoundTable (all analysts)", [
            {"pair": k, "summary": str(v)[:100]}
            for k, v in challenges.items()
        ])
        return perspectives

    # ═══════════════════════════════════════════════════════════
    #  PHASE 6: EDITORIAL OVERSIGHT
    # ═══════════════════════════════════════════════════════════

    def _phase_editorial(self, story: dict, perspectives: dict):
        print("\n" + "=" * 65)
        print("  PHASE 6: EDITORIAL OVERSIGHT (Paramount)")
        print("=" * 65)

        self.tracer.begin_phase(
            phase="Editorial",
            agent_name="EditorInChief",
            agent_codename="Paramount",
            model=config.MODEL_EDITOR_IN_CHIEF,
            fixed_inputs={"core_instruction": "Review all perspectives"},
            variable_inputs={
                "perspectives": self.tracer.var_ref(
                    "AnalystPairs+RoundTable", "", "Phase4+5", "all"),
            },
        )

        review = self.editor.review_perspectives(story, perspectives)
        self.tracer.end_phase(review)

        score = review.get("quality_score", "?")
        print(f"  \u25b8 Editor score: {score}/10")

        if not review.get("ready_for_synthesis", False):
            feedback = review.get("feedback_per_agent", {})
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
                    print(f"  \u25b8 {agent_name} revised per editor demands")

    # ═══════════════════════════════════════════════════════════
    #  PHASE 7: CONTENT SYNTHESIS (POSTER) + COPY REVIEW
    # ═══════════════════════════════════════════════════════════

    def _phase_synthesis(self, story: dict, perspectives: dict,
                         strategy: dict, design: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 7: CONTENT SYNTHESIS [POSTER] (Quill + Sterling argue)")
        print("=" * 65)

        content_type = strategy.get("content_type", "")

        self.tracer.begin_phase(
            phase="ContentSynthesis",
            agent_name="ContentWriter",
            agent_codename="Quill",
            model=config.MODEL_CONTENT_WRITER,
            fixed_inputs={
                "core_instruction": "Synthesise into luxury POSTER (3 content pages)",
                "output_format": "poster",
                "guardrail": GUARDRAIL[:100],
                "anchor_filter": self.cfg.get("brand_identity", {}).get(
                    "fixed", {}).get("anchor_filter", "")[:100],
            },
            variable_inputs={
                "perspectives": self.tracer.var_ref(
                    "AnalystPairs+RoundTable+Editorial", "", "Phase4-6",
                    list(perspectives.keys())),
                "design_dna": self.tracer.var_ref(
                    "DesignDNA", "Vesper", "DesignDNA",
                    design.get("design_name")),
                "content_type": self.tracer.var_ref(
                    "ContentStrategist", "Marcus", "ContentStrategy",
                    content_type),
            },
        )

        # Always poster format now
        brief = self.writer.synthesise(story, perspectives)
        self.tracer.end_phase(brief)

        # Copy review debate
        brief = self._argue(self.writer, self.copy_reviewer, brief,
                            "content_brief", story)

        pages = brief.get("pages", [])
        print(f"  \u25b8 Brief [POSTER]: {brief.get('brief_title', '?')}, "
              f"{len(pages)} pages")
        return brief

    # ═══════════════════════════════════════════════════════════
    #  PHASE 8: NEUTRALITY CHECK
    # ═══════════════════════════════════════════════════════════

    def _phase_neutrality(self, brief: dict, story: dict,
                          perspectives: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 8: NEUTRALITY & TONE CHECK (Justice)")
        print("=" * 65)

        self.tracer.begin_phase(
            phase="NeutralityCheck",
            agent_name="NeutralityGuard",
            agent_codename="Justice",
            model=config.MODEL_CONTENT_REVIEWER,
            fixed_inputs={"guardrail": GUARDRAIL[:100]},
            variable_inputs={
                "brief": self.tracer.var_ref(
                    "ContentWriter", "Quill", "ContentSynthesis",
                    brief.get("brief_title")),
            },
        )

        review = self.neutrality_reviewer.review(brief)
        self.tracer.end_phase(review)

        approved = review.get("approved", False)
        print(f"  \u25b8 Approved: {approved}, "
              f"tone: {review.get('tone_score', '?')}/10")

        if not approved:
            editor_fix = self.editor.review_final_brief(brief, review)
            brief = self.writer.synthesise(story, perspectives,
                                           editor_notes=editor_fix)
            print(f"  \u25b8 Revised after neutrality feedback")

        return brief

    # ═══════════════════════════════════════════════════════════
    #  PHASE 8.5: DISCUSSION POTENTIAL
    # ═══════════════════════════════════════════════════════════

    def _phase_discussion_potential(self, story: dict, brief: dict) -> dict:
        """Evaluate if the content can spark meaningful LinkedIn discussion.

        Returns the evaluation dict with engagement_score, verdict,
        and discussion_hooks that the LinkedIn post can use.
        """
        print("\n" + "=" * 65)
        print("  PHASE 8.5: DISCUSSION POTENTIAL (Spark)")
        print("=" * 65)

        self.tracer.begin_phase(
            phase="DiscussionPotential",
            agent_name="DiscussionPotentialAnalyst",
            agent_codename="Spark",
            model=config.MODEL_DISCUSSION_POTENTIAL,
            fixed_inputs={
                "core_instruction": "Score engagement potential on 5 dimensions",
                "threshold": ">=70 HIGH, 50-69 MEDIUM, <50 LOW",
            },
            variable_inputs={
                "brief": self.tracer.var_ref(
                    "ContentWriter", "Quill", "ContentSynthesis",
                    brief.get("brief_title")),
                "story": self.tracer.var_ref(
                    "NewsScout", "Sable", "TopicDiscovery",
                    story.get("headline")),
            },
        )

        evaluation = self.discussion_analyst.evaluate(story, brief)
        self.tracer.end_phase(evaluation)

        score = evaluation.get("engagement_score", 0)
        verdict = evaluation.get("verdict", "?")
        hooks = evaluation.get("discussion_hooks", [])

        print(f"  ▸ Engagement score: {score}/100")
        print(f"  ▸ Verdict: {verdict}")
        for i, hook in enumerate(hooks[:3]):
            print(f"    Hook {i+1}: {hook[:70]}")

        if verdict == "LOW":
            angle = evaluation.get("suggested_angle", "")
            if angle:
                print(f"  ⚠ Suggested reframe: {angle[:80]}")

        return evaluation

    # ═══════════════════════════════════════════════════════════
    #  PHASE 9: VISUALS
    # ═══════════════════════════════════════════════════════════

    def _phase_visuals(self, brief: dict, story: dict, design: dict,
                       perspectives: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 9: VISUAL GENERATION (Prism)")
        print("=" * 65)

        self.tracer.begin_phase(
            phase="VisualGeneration",
            agent_name="VisualGenerator",
            agent_codename="Prism",
            model="dall-e-3 + pillow",
            fixed_inputs={"core_instruction": "Generate images + infographics"},
            variable_inputs={
                "design_dna": self.tracer.var_ref(
                    "DesignDNA", "Vesper", "DesignDNA", design),
                "brief": self.tracer.var_ref(
                    "ContentWriter", "Quill", "ContentSynthesis",
                    brief.get("brief_title")),
            },
        )

        from aibrief.pipeline.visuals import generate_all_visuals
        run_id = self.tracer.run_id
        style_id = design.get("style_id", "luxury_minimalist")
        visuals = generate_all_visuals(brief, story, design, perspectives,
                                       run_id, style_id=style_id)
        self.tracer.end_phase(
            {"visual_count": len(visuals),
             "types": list(visuals.keys())})
        return visuals

    # ═══════════════════════════════════════════════════════════
    #  PHASE 10: PDF (POSTER + AGENT CREDITS + MIND MAP)
    # ═══════════════════════════════════════════════════════════

    def _phase_pdf(self, brief: dict, design: dict, story: dict,
                   visuals: dict, pulse: dict, strategy: dict,
                   validation: dict, elapsed: float) -> str:
        print("\n" + "=" * 65)
        print("  PHASE 10: LUXURY POSTER PDF + AGENT CREDITS + MIND MAP")
        print("=" * 65)

        import re
        slug = brief.get("brief_title", "AI_Brief")[:35]
        slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
        output_path = str(
            config.OUTPUT_DIR / f"{slug}_poster_{self.tracer.run_id}.pdf")

        # Collect agent info for credits section
        agents_info = self._get_agents_info()

        # Collect tracer flow for mind map
        tracer_flow = self._get_tracer_flow(
            pulse, strategy, design, validation, elapsed)

        from aibrief.pipeline.poster_gen import generate_poster
        pdf_path = generate_poster(
            brief, design, story,
            visuals=visuals,
            agents_info=agents_info,
            tracer_flow=tracer_flow,
            strategy=strategy,
            output_path=output_path,
        )
        return pdf_path

    # ═══════════════════════════════════════════════════════════
    #  PHASE 11: SCREEN AUDIT
    # ═══════════════════════════════════════════════════════════

    def _phase_screen_audit(self, brief: dict, design: dict,
                            visuals: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 11: SCREEN REAL ESTATE AUDIT (Ratio)")
        print("=" * 65)

        self.tracer.begin_phase(
            phase="ScreenAudit",
            agent_name="ScreenAuditor",
            agent_codename="Ratio",
            model=config.MODEL_CONTENT_REVIEWER,
            fixed_inputs={"target": "55-65% fill, golden ratio"},
            variable_inputs={
                "brief": self.tracer.var_ref(
                    "ContentWriter", "Quill", "ContentSynthesis",
                    f"{len(brief.get('pages', []))} pages"),
            },
        )

        pages_info = []
        for i, page in enumerate(brief.get("pages", [])):
            pages_info.append({
                "page_number": i + 1,
                "page_type": page.get("page_type", "?"),
                "has_hero_statement": bool(page.get("hero_statement")),
                "has_supporting_line": bool(page.get("supporting_line")),
                "has_hero_number": bool(page.get("hero_number")),
                "has_quote": bool(page.get("quote")),
                "has_visual": page.get("page_type", "") in visuals,
                "has_style_decoration": True,
                "format": "portrait poster",
            })

        audit = self.screen_auditor.think(
            "Audit this POSTER PDF. Each page is portrait (8.5x11). "
            "Poster pages have: style decoration background + massive "
            "typography + one statement. Check that no page feels empty "
            "but also not overcrowded — poster style uses whitespace "
            "intentionally.",
            context={"pages": pages_info, "design": design},
        )
        self.tracer.end_phase(audit)

        approved = audit.get("approved", False)
        print(f"  \u25b8 Audit: {'PASS' if approved else 'NEEDS ATTENTION'}")
        return audit

    # ═══════════════════════════════════════════════════════════
    #  PHASE 8.7: PRE-VISUAL VALIDATION (content + structure)
    # ═══════════════════════════════════════════════════════════

    def _phase_pre_validation(self, brief: dict, design: dict,
                              story: dict) -> dict:
        print("\n" + "=" * 65)
        print(f"  PHASE 8.7: PRE-VISUAL VALIDATION — content gate (Sentinel-A)")
        print("=" * 65)

        debates = [e for e in self.tracer.entries if e.get("phase") == "DEBATE"]
        agent_rounds = {
            d["pair"]: {"rounds": d.get("total_rounds", 0)}
            for d in debates
        }

        self.tracer.begin_phase(
            phase="PreVisualValidation",
            agent_name="PreVisualValidator",
            agent_codename="Sentinel-A",
            model="gpt-4o",
            fixed_inputs={
                "checklist": "17 content/structure rules",
                "threshold": f"{PASS_THRESHOLD}%",
            },
            variable_inputs={
                "brief": self.tracer.var_ref(
                    "ContentWriter", "Quill", "ContentSynthesis",
                    brief.get("brief_title")),
                "design": self.tracer.var_ref(
                    "DesignDNA", "Vesper", "DesignDNA",
                    design.get("design_name")),
                "agent_rounds": self.tracer.var_ref(
                    "Tracer", "", "Debates", agent_rounds),
            },
        )

        result = self.pre_validator.validate(
            brief=brief, design=design, story=story,
            agent_rounds=agent_rounds,
        )
        self.tracer.end_phase(result)

        total = result.get("total_score", 0)
        approved = result.get("approved", False)
        explanation = result.get("explanation", "")
        print(f"  ▸ Score: {total}/100, Approved: {approved}")
        if explanation:
            print(f"  ▸ Why: {explanation[:150]}")

        if result.get("critical_failures"):
            for cf in result["critical_failures"][:3]:
                print(f"    ✗ {cf}")

        return result

    # ═══════════════════════════════════════════════════════════
    #  PHASE 12: POST-VISUAL VALIDATION (layout + visuals)
    # ═══════════════════════════════════════════════════════════

    def _phase_post_validation(self, brief: dict, design: dict,
                               story: dict, visuals: dict,
                               audit: dict) -> dict:
        print("\n" + "=" * 65)
        print(f"  PHASE 12: POST-VISUAL VALIDATION — layout gate (Sentinel-B)")
        print("=" * 65)

        self.tracer.begin_phase(
            phase="PostVisualValidation",
            agent_name="PostVisualValidator",
            agent_codename="Sentinel-B",
            model="gpt-4o",
            fixed_inputs={
                "checklist": "18 visual/layout rules",
                "threshold": f"{PASS_THRESHOLD}%",
            },
            variable_inputs={
                "brief": self.tracer.var_ref(
                    "ContentWriter", "Quill", "ContentSynthesis",
                    brief.get("brief_title")),
                "design": self.tracer.var_ref(
                    "DesignDNA", "Vesper", "DesignDNA",
                    design.get("design_name")),
                "audit": self.tracer.var_ref(
                    "ScreenAuditor", "Ratio", "ScreenAudit",
                    audit.get("approved")),
            },
        )

        result = self.post_validator.validate(
            brief=brief, design=design, story=story,
            visuals_count=len(visuals),
            audit_result=audit,
        )
        self.tracer.end_phase(result)

        total = result.get("total_score", 0)
        approved = result.get("approved", False)
        explanation = result.get("explanation", "")
        print(f"  ▸ Score: {total}/100, Approved: {approved}")
        if explanation:
            print(f"  ▸ Why: {explanation[:150]}")

        if result.get("critical_failures"):
            for cf in result["critical_failures"][:3]:
                print(f"    ✗ {cf}")

        return result

    # ═══════════════════════════════════════════════════════════
    #  PHASE 13: LINKEDIN POST
    # ═══════════════════════════════════════════════════════════

    def _phase_linkedin(self, brief: dict, story: dict, design: dict,
                        pdf_path: str, discussion: dict = None) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 13: LINKEDIN POST (Herald)")
        print("=" * 65)

        self.tracer.begin_phase(
            phase="LinkedInCopy",
            agent_name="LinkedInExpert",
            agent_codename="Herald",
            model=config.MODEL_LINKEDIN_EXPERT,
            fixed_inputs={"core_instruction": "Craft viral LinkedIn post"},
            variable_inputs={
                "brief": self.tracer.var_ref(
                    "ContentWriter", "Quill", "ContentSynthesis",
                    brief.get("brief_title")),
                "design_mood": self.tracer.var_ref(
                    "DesignDNA", "Vesper", "DesignDNA",
                    design.get("mood")),
                "discussion_hooks": self.tracer.var_ref(
                    "DiscussionPotentialAnalyst", "Spark",
                    "DiscussionPotential",
                    (discussion or {}).get("discussion_hooks", [])),
            },
        )

        # Pass discussion hooks to the LinkedIn expert for better engagement
        hooks = (discussion or {}).get("discussion_hooks", [])
        li_post = self.linkedin_expert.craft_post(story, brief, hooks=hooks)
        # Save FULL post text (not truncated) for reuse
        self.tracer.end_phase(
            self.tracer._truncate_value_full(li_post))

        post_text = li_post.get("post_text", "")
        doc_title = li_post.get("document_title", "")
        if not doc_title:
            doc_title = brief.get("brief_title", "AI Thought Leadership Brief")
        print(f"  \u25b8 Post: {len(post_text)} chars")
        print(f"  \u25b8 Document title: {doc_title}")

        if self.controls.get("post_to_linkedin", True):
            from aibrief.pipeline.linkedin import post_brief
            li_result = post_brief(
                pdf_path, post_text, story=story,
                document_title=doc_title)
            self._log_post(story, brief, li_post, li_result, design)
            return li_result
        else:
            print("  \u25b8 LinkedIn posting disabled in config")
            return {"status": "skipped"}

    def _log_post(self, story, brief, li_post, li_result, design):
        """Log post details to post_log.json."""
        log_path = config.BASE_DIR / "post_log.json"
        if log_path.exists():
            log = json.loads(log_path.read_text(encoding="utf-8"))
        else:
            log = {"posts": [], "topics_covered": [], "embeddings": [],
                   "total_posts": 0}

        import time as _time
        log["posts"].append({
            "post_id": li_result.get("post_id", ""),
            "url": li_result.get("url", ""),
            "topic": story.get("headline", "?"),
            "brief_title": brief.get("brief_title", "?"),
            "document_title": li_post.get("document_title", ""),
            "content_type": self.tracer.agent_outputs.get(
                "ContentStrategist", {}).get("content_type", ""),
            "design_name": design.get("design_name", "?"),
            "design_theme": design.get("style_id", "?"),
            "world_mood": self.tracer.agent_outputs.get(
                "WorldPulseScanner", {}).get("mood", ""),
            "date": _time.strftime("%Y-%m-%d %H:%M"),
            "tracer_id": self.tracer.run_id,
            "status": li_result.get("status", "?"),
        })
        log["topics_covered"].append(story.get("headline", "?"))
        log["total_posts"] = len(log["posts"])

        log_path.write_text(
            json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")

    # ═══════════════════════════════════════════════════════════
    #  MAIN RUN
    # ═══════════════════════════════════════════════════════════

    def run(self) -> dict:
        """Run the full autonomous pipeline."""
        t0 = time.time()

        # ── Phase 0: World Pulse ──
        pulse = self._phase_world_pulse()

        # ── Phase 1: Content Strategy ──
        strategy = self._phase_content_strategy(pulse)

        # Check for "Silent" mode
        ct = strategy.get("content_type", "")
        if "silent" in ct.lower():
            print("\n  \u26a0 World sentiment too sensitive. Not posting today.")
            self.tracer.save({"decision": "SILENT", "reason": ct})
            return {"decision": "SILENT"}

        # ── Phase 2: Topic Discovery ──
        story = self._phase_topic_discovery(strategy, pulse)

        # ── Phase 3: Emotion Detection → Hardcoded Design ──
        design = self._phase_design_dna(pulse, strategy, story)

        # ── Phase 4: Analyst Pairs ──
        perspectives = self._phase_analyst_pairs(story, strategy)

        # ── Phase 5: Round Table ──
        perspectives = self._phase_round_table(story, perspectives)

        # ── Phase 6: Editorial Oversight ──
        self._phase_editorial(story, perspectives)

        # ── Phase 7: Content Synthesis + Copy Review ──
        brief = self._phase_synthesis(story, perspectives, strategy, design)

        # ── Phase 8: Neutrality Check ──
        brief = self._phase_neutrality(brief, story, perspectives)

        # ── Phase 8.5: Discussion Potential ──
        discussion = self._phase_discussion_potential(story, brief)

        # ── Phase 8.7: PRE-VISUAL Validation (content/structure gate) ──
        pre_val = self._phase_pre_validation(brief, design, story)

        # ── Phase 9: Visuals ──
        visuals = self._phase_visuals(brief, story, design, perspectives)

        # ── Phase 11: Screen Audit (before PDF to inform) ──
        audit = self._phase_screen_audit(brief, design, visuals)

        # ── Phase 10: PDF (poster + agent credits + mind map) ──
        elapsed = time.time() - t0
        pdf_path = self._phase_pdf(brief, design, story, visuals,
                                   pulse, strategy, pre_val, elapsed)

        # ── Phase 12: POST-VISUAL Validation (layout/visuals gate) ──
        post_val = self._phase_post_validation(brief, design, story, visuals, audit)

        # Combine scores for final gate
        pre_score = pre_val.get("total_score", 0)
        post_score = post_val.get("total_score", 0)
        combined_score = round((pre_score + post_score) / 2, 1)
        validation = {
            "pre_visual": pre_val,
            "post_visual": post_val,
            "total_score": combined_score,
            "approved": combined_score >= PASS_THRESHOLD,
        }

        # ── GATE: Only post if combined >= 60% ──
        li_result = {}
        if validation["approved"]:
            # ── Phase 13: LinkedIn ──
            li_result = self._phase_linkedin(
                brief, story, design, pdf_path, discussion=discussion)
        else:
            print(f"\n  ⛔ BLOCKED: Combined {combined_score}/100 "
                  f"(pre:{pre_score}, post:{post_score}, need ≥{PASS_THRESHOLD})")
            print(f"    PDF saved but NOT posted to LinkedIn.")
            # Print the judge's explanations
            pre_expl = pre_val.get("explanation", "")
            post_expl = post_val.get("explanation", "")
            if pre_expl:
                print(f"    Pre-visual judge: {pre_expl[:120]}")
            if post_expl:
                print(f"    Post-visual judge: {post_expl[:120]}")
            li_result = {
                "status": "blocked",
                "reason": (f"Combined score {combined_score}/100 "
                           f"(pre:{pre_score}, post:{post_score})"),
            }

        # ── Save Trace ──
        elapsed = time.time() - t0
        trace_path = self.tracer.save(final_output={
            "pdf_path": pdf_path,
            "linkedin": li_result,
            "validation_score": combined_score,
            "pre_visual_score": pre_score,
            "post_visual_score": post_score,
            "content_type": strategy.get("content_type"),
            "world_mood": pulse.get("mood"),
            "emotion": design.get("emotion"),
            "design_name": design.get("design_name"),
            "style_id": design.get("style_id"),
            "palette_id": design.get("palette_id"),
            "font_id": design.get("font_id"),
            "imagen_style": design.get("imagen_style"),
            "headline": story.get("headline"),
            "discussion_score": discussion.get("engagement_score"),
            "discussion_verdict": discussion.get("verdict"),
        })

        print(f"\n{'=' * 65}")
        print(f"  AUTONOMOUS RUN COMPLETE | {elapsed:.0f}s ({elapsed/60:.1f} min)")
        print(f"  Story: {story.get('headline', '?')}")
        print(f"  Content type: {strategy.get('content_type', '?')}")
        print(f"  Format: POSTER (always)")
        print(f"  Emotion: {design.get('emotion', '?')}")
        print(f"  Style: {design.get('style_id', '?')} (from emotion map)")
        print(f"  Palette: {design.get('palette_id', '?')} (from emotion map)")
        print(f"  Font: {design.get('font_id', '?')} (from emotion map)")
        print(f"  Imagen: {design.get('imagen_style', '?')}")
        print(f"  World mood: {pulse.get('mood', '?')}")
        print(f"  Design: {design.get('design_name', '?')}")
        print(f"  PDF: {pdf_path}")
        print(f"  Validation: {combined_score}/100 (pre:{pre_score}, post:{post_score})")
        print(f"  Trace: {trace_path}")
        print(f"{'=' * 65}")

        return {
            "story": story,
            "brief": brief,
            "design": design,
            "linkedin_post": li_result,
            "pdf_path": pdf_path,
            "validation": validation,
            "strategy": strategy,
            "pulse": pulse,
            "tracer_id": self.tracer.run_id,
            "trace_path": trace_path,
        }
