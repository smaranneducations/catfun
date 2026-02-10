"""Autonomous Orchestrator — Full pipeline with World Pulse, Content Strategy,
Design DNA, multi-agent debate, and complete run tracing.

Architecture:
  Phase 0:  World Pulse → global sentiment scan (Gemini + Google Search)
  Phase 1:  Content Strategy → choose content type + length (GPT-4o)
  Phase 2:  Topic Discovery → find topic + semantic dedup (Gemini Flash)
  Phase 3:  Design DNA → visual identity + debate (GPT-4o)
  Phase 4:  Analyst Pairs → 4× preparer/reviewer argue (Gemini Flash + GPT-4o)
  Phase 5:  Round Table → cross-agent challenges
  Phase 6:  Editorial Oversight → editor reviews all perspectives (GPT-4o)
  Phase 7:  Content Synthesis → writer + copy reviewer argue (GPT-4o)
  Phase 8:  Neutrality Check → ethical guardrail enforcement (GPT-4o)
  Phase 9:  Visuals → DALL-E images + Pillow infographics
  Phase 10: PDF → luxury landscape slide deck
  Phase 11: Screen Audit → page fill golden ratio check (GPT-4o)
  Phase 12: Final Validation → 37 master checkpoints (GPT-4o)
  Phase 13: LinkedIn → post with dynamic catchy document title

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
    ContentWriter, DesignDirector, ContentReviewer, EditorInChief,
    LinkedInExpert,
)
from aibrief.agents.base import Agent
from aibrief.agents.validators import FinalValidatorAgent, GUARDRAIL
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
                "  \"overall_score\": number (1-10),\n"
                "  \"approved\": boolean,\n"
                "  \"page_scores\": [{\"page_type\": string, \"score\": number}],\n"
                "  \"demands\": [string],\n"
                "  \"tone_verdict\": string\n"
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
                "CRITICAL FOR THIS REVIEW: The design DNA must match the "
                "WORLD SENTIMENT. Don't approve happy bright colors when "
                "the world is anxious. Don't approve somber tones when "
                "the world is optimistic.\n\n"
                "REVIEW CRITERIA:\n"
                "1. SENTIMENT MATCH — Do colors match today's world mood?\n"
                "2. COLOR PSYCHOLOGY — Correct emotional associations?\n"
                "3. GOLDEN RATIO — Mathematically harmonious proportions?\n"
                "4. TYPOGRAPHY — Clear hierarchy (display, body, caption)?\n"
                "5. UNIQUENESS — Surprising and fresh?\n"
                "6. BACKGROUNDS — Rich textures, never plain white?\n\n"
                "Return JSON:\n"
                "{\n"
                "  \"overall_score\": number (1-10),\n"
                "  \"approved\": boolean,\n"
                "  \"sentiment_match\": string,\n"
                "  \"color_verdict\": string,\n"
                "  \"demands\": [string],\n"
                "  \"suggested_improvements\": [string]\n"
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
                "- Z-pattern reading flow\n"
                "- Visual weight: images/dark blocks anchor the page\n"
                "- Typography hierarchy: 3 sizes create order and rhythm\n"
                "- Color panels/backgrounds eliminate dead white space\n\n"
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
        self.design_reviewer = DesignReviewer()

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
        self.validator = FinalValidatorAgent()

    @staticmethod
    def _load_config() -> dict:
        cfg_path = config.BASE_DIR / "agent_config.json"
        if cfg_path.exists():
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        return {"mode": "autonomous", "controls": {}}

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
                print(f"    ✓ {label} APPROVED after {rnd} round(s)")
                break
            if rnd < self.MAX_ROUNDS:
                work = preparer.respond_to_feedback(work, review)
                print(f"    → {preparer.name} revised")

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

        # Get recent content types from post log to ensure variety
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
                    "core_instruction": cfg_agent.get("fixed_strings", {}).get(
                        "core_instruction", "Find topic"),
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

            if attempt == 1:
                candidate = self.scout.think(
                    f"Find THE best topic for a '{content_type}' piece. "
                    f"Topic direction: {topic_dir}. "
                    f"Current world mood: {pulse.get('mood', 'normal')}. "
                    f"Trending AI topics: {pulse.get('ai_news', [])}. "
                    f"This must connect to AI thought leadership.",
                    context={"content_type": content_type,
                             "world_pulse": pulse},
                )
            else:
                excluded_str = ", ".join(f'"{h}"' for h in excluded)
                candidate = self.scout.think(
                    f"Find a DIFFERENT topic. Do NOT pick: {excluded_str}. "
                    f"Content type: '{content_type}'. "
                    f"Find something completely new and different.",
                    context={"excluded_topics": excluded,
                             "content_type": content_type},
                )

            if isinstance(candidate, list):
                candidate = candidate[0] if candidate else {}

            self.tracer.end_phase(candidate)

            headline = candidate.get("headline", "?")
            print(f"  ▸ Candidate: {headline}")

            is_dup, similarity, matched = is_duplicate(candidate)
            if is_dup:
                print(f"  ✗ BLOCKED: {similarity:.0%} similar to '{matched}'")
                excluded.append(headline)
                continue
            else:
                print(f"  ✓ UNIQUE: max similarity {similarity:.0%}")
                story = candidate
                break

        if story is None:
            print("  ⚠ All attempts matched. Using last candidate.")
            story = candidate

        print(f"\n  ▸ Final topic: {story.get('headline', '?')}")
        return story

    # ═══════════════════════════════════════════════════════════
    #  PHASE 3: DESIGN DNA + DEBATE
    # ═══════════════════════════════════════════════════════════

    def _phase_design_dna(self, pulse: dict, strategy: dict,
                          story: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 3: DESIGN DNA + DEBATE (Vesper vs Onyx)")
        print("=" * 65)

        cfg_agent = self.cfg.get("agents", {}).get("DesignDNA", {})
        self.tracer.begin_phase(
            phase="DesignDNA",
            agent_name="DesignDNA",
            agent_codename=cfg_agent.get("name", "Vesper"),
            model=config.MODEL_DESIGN_DNA,
            fixed_inputs={
                "core_instruction": cfg_agent.get("fixed_strings", {}).get(
                    "core_instruction", "Create visual identity"),
                "available_themes": cfg_agent.get("fixed_strings", {}).get(
                    "available_themes", []),
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

        # Design debate
        design = self._argue(
            self.design_dna, self.design_reviewer, design,
            "visual_design", {"story": story, "world_pulse": pulse})

        print(f"  ▸ Design: {design.get('design_name', '?')}")
        print(f"  ▸ Theme: {design.get('theme', '?')}")
        print(f"  ▸ Palette: {design.get('primary_color', '?')} / "
              f"{design.get('accent_color', '?')}")
        print(f"  ▸ Image key: {design.get('image_generation_key', '?')[:60]}")
        return design

    # ═══════════════════════════════════════════════════════════
    #  PHASE 4: ANALYST PAIRS
    # ═══════════════════════════════════════════════════════════

    def _phase_analyst_pairs(self, story: dict, strategy: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 4: ANALYST PAIRS (Prepare → Review → Argue)")
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
        print("  PHASE 5: ROUND TABLE — Agents challenge each other")
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
            challenges[f"{challenger.name}→{target_name}"] = challenge
            summary = str(challenge)[:80]
            print(f"    {challenger.name} → {target_name}: {summary}")

        # Each agent incorporates incoming challenges
        for challenger, own_key, target_key, target_name in pairs:
            incoming = {k: v for k, v in challenges.items()
                        if k.endswith(f"→{challenger.name.split()[0]}")}
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
        print(f"  ▸ Editor score: {score}/10")

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
                    print(f"  ▸ {agent_name} revised per editor demands")

    # ═══════════════════════════════════════════════════════════
    #  PHASE 7: CONTENT SYNTHESIS + COPY REVIEW
    # ═══════════════════════════════════════════════════════════

    def _phase_synthesis(self, story: dict, perspectives: dict,
                         strategy: dict, design: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 7: CONTENT SYNTHESIS (Quill + Sterling argue)")
        print("=" * 65)

        page_count = strategy.get("page_count", 8)
        content_type = strategy.get("content_type", "")

        self.tracer.begin_phase(
            phase="ContentSynthesis",
            agent_name="ContentWriter",
            agent_codename="Quill",
            model=config.MODEL_CONTENT_WRITER,
            fixed_inputs={
                "core_instruction": "Synthesize into luxury keynote slides",
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
                "page_count": self.tracer.var_ref(
                    "ContentStrategist", "Marcus", "ContentStrategy",
                    page_count),
            },
        )

        brief = self.writer.synthesise(story, perspectives)
        self.tracer.end_phase(brief)

        # Copy review debate
        brief = self._argue(self.writer, self.copy_reviewer, brief,
                            "content_brief", story)

        pages = brief.get("pages", [])
        print(f"  ▸ Brief: {brief.get('brief_title', '?')}, {len(pages)} pages")
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
        print(f"  ▸ Approved: {approved}, "
              f"tone: {review.get('tone_score', '?')}/10")

        if not approved:
            editor_fix = self.editor.review_final_brief(brief, review)
            brief = self.writer.synthesise(story, perspectives,
                                           editor_notes=editor_fix)
            print(f"  ▸ Revised after neutrality feedback")

        return brief

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
        visuals = generate_all_visuals(brief, story, design, perspectives,
                                       run_id)
        self.tracer.end_phase(
            {"visual_count": len(visuals),
             "types": list(visuals.keys())})
        return visuals

    # ═══════════════════════════════════════════════════════════
    #  PHASE 10: PDF
    # ═══════════════════════════════════════════════════════════

    def _phase_pdf(self, brief: dict, design: dict, story: dict,
                   visuals: dict) -> str:
        print("\n" + "=" * 65)
        print("  PHASE 10: LUXURY SLIDE DECK PDF")
        print("=" * 65)

        import re
        from aibrief.pipeline.pdf_gen import generate_pdf

        slug = brief.get("brief_title", "AI_Brief")[:35]
        slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
        output_path = str(config.OUTPUT_DIR / f"{slug}_{self.tracer.run_id}.pdf")

        pdf_path = generate_pdf(brief, design, story, visuals=visuals,
                                output_path=output_path)
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
                "title": page.get("title", "?"),
                "has_point": bool(page.get("point")),
                "has_insight": bool(page.get("insight")),
                "has_key_stat": bool(page.get("key_stat")),
                "has_quote": bool(page.get("quote")),
                "has_visual": page.get("page_type", "") in visuals,
                "has_artistic_background": True,
                "format": "landscape slide",
            })

        audit = self.screen_auditor.think(
            "Audit this SLIDE DECK PDF. Each slide is landscape (11x8.5). "
            "Every slide has: artistic background + big header + content + "
            "visual. Check that no slide feels empty.",
            context={"pages": pages_info, "design": design},
        )
        self.tracer.end_phase(audit)

        approved = audit.get("approved", False)
        print(f"  ▸ Audit: {'PASS' if approved else 'NEEDS ATTENTION'}")
        return audit

    # ═══════════════════════════════════════════════════════════
    #  PHASE 12: FINAL VALIDATION (37 RULES)
    # ═══════════════════════════════════════════════════════════

    def _phase_validation(self, brief: dict, design: dict, story: dict,
                          visuals: dict, audit: dict) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 12: FINAL VALIDATION — 37 master checkpoints (Sentinel)")
        print("=" * 65)

        # Collect agent debate proof from tracer
        debates = [e for e in self.tracer.entries if e.get("phase") == "DEBATE"]
        agent_rounds = {
            d["pair"]: {"rounds": d.get("total_rounds", 0)}
            for d in debates
        }

        self.tracer.begin_phase(
            phase="FinalValidation",
            agent_name="FinalValidator",
            agent_codename="Sentinel",
            model="gpt-4o",
            fixed_inputs={"checklist": "37 master rules", "threshold": "80%"},
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
                "agent_rounds": self.tracer.var_ref(
                    "Tracer", "", "Debates", agent_rounds),
            },
        )

        validation = self.validator.validate(
            brief=brief, design=design, story=story,
            visuals_count=len(visuals),
            audit_result=audit, agent_rounds=agent_rounds,
        )
        self.tracer.end_phase(validation)

        total = validation.get("total_score", 0)
        approved = validation.get("approved", False)
        print(f"  ▸ Score: {total}/100, Approved: {approved}")

        if validation.get("critical_failures"):
            for cf in validation["critical_failures"][:5]:
                print(f"    ✗ {cf}")

        return validation

    # ═══════════════════════════════════════════════════════════
    #  PHASE 13: LINKEDIN POST
    # ═══════════════════════════════════════════════════════════

    def _phase_linkedin(self, brief: dict, story: dict, design: dict,
                        pdf_path: str) -> dict:
        print("\n" + "=" * 65)
        print("  PHASE 13: LINKEDIN POST (Herald)")
        print("=" * 65)

        # Generate post copy + dynamic document title
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
            },
        )

        li_post = self.linkedin_expert.craft_post(story, brief)
        self.tracer.end_phase(li_post)

        post_text = li_post.get("post_text", "")
        doc_title = li_post.get("document_title", "")
        if not doc_title:
            # Fallback: use brief title as document title
            doc_title = brief.get("brief_title", "AI Thought Leadership Brief")
        print(f"  ▸ Post: {len(post_text)} chars")
        print(f"  ▸ Document title: {doc_title}")

        # Post to LinkedIn
        if self.controls.get("post_to_linkedin", True):
            from aibrief.pipeline.linkedin import post_brief
            li_result = post_brief(
                pdf_path, post_text, story=story,
                document_title=doc_title)

            # Log to post_log.json
            self._log_post(story, brief, li_post, li_result, design)
            return li_result
        else:
            print("  ▸ LinkedIn posting disabled in config")
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
            "design_theme": design.get("theme", "?"),
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
            print("\n  ⚠ World sentiment too sensitive. Not posting today.")
            self.tracer.save({"decision": "SILENT", "reason": ct})
            return {"decision": "SILENT"}

        # ── Phase 2: Topic Discovery ──
        story = self._phase_topic_discovery(strategy, pulse)

        # ── Phase 3: Design DNA + Debate ──
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

        # ── Phase 9: Visuals ──
        visuals = self._phase_visuals(brief, story, design, perspectives)

        # ── Phase 10: PDF ──
        pdf_path = self._phase_pdf(brief, design, story, visuals)

        # ── Phase 11: Screen Audit ──
        audit = self._phase_screen_audit(brief, design, visuals)

        # ── Phase 12: Final Validation ──
        validation = self._phase_validation(brief, design, story, visuals, audit)

        # ── Phase 13: LinkedIn ──
        li_result = self._phase_linkedin(brief, story, design, pdf_path)

        # ── Save Trace ──
        elapsed = time.time() - t0
        trace_path = self.tracer.save(final_output={
            "pdf_path": pdf_path,
            "linkedin": li_result,
            "validation_score": validation.get("total_score"),
            "content_type": strategy.get("content_type"),
            "world_mood": pulse.get("mood"),
            "design_name": design.get("design_name"),
            "headline": story.get("headline"),
        })

        print(f"\n{'=' * 65}")
        print(f"  AUTONOMOUS RUN COMPLETE | {elapsed:.0f}s ({elapsed/60:.1f} min)")
        print(f"  Story: {story.get('headline', '?')}")
        print(f"  Content type: {strategy.get('content_type', '?')}")
        print(f"  World mood: {pulse.get('mood', '?')}")
        print(f"  Design: {design.get('design_name', '?')}")
        print(f"  PDF: {pdf_path}")
        print(f"  Validation: {validation.get('total_score', '?')}/100")
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
