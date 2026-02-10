# How to Build Complex Multi-Agent Systems

## A Complete Blueprint — From Architecture to Production

**Author**: Bhasker Kumar
**System**: AI Brief v2.0 — Autonomous AI Thought Leadership Publisher
**Built with**: Claude (Cursor IDE), GPT-4o, Gemini Flash, DALL-E 3, Pillow
**Date**: February 2026

---

## Table of Contents

1. [What We Built](#1-what-we-built)
2. [Why Multi-Agent (Not Single-Agent)](#2-why-multi-agent-not-single-agent)
3. [The 5 Design Principles](#3-the-5-design-principles)
4. [Complete Architecture — 13 Phases](#4-complete-architecture--13-phases)
5. [Agent Roster — All 20+ Agents](#5-agent-roster--all-20-agents)
6. [The Debate Engine — How Agents Argue](#6-the-debate-engine--how-agents-argue)
7. [The Tracer — Full Provenance Chain](#7-the-tracer--full-provenance-chain)
8. [The Config — Fixed vs Variable Strings](#8-the-config--fixed-vs-variable-strings)
9. [Real Run Output — What Actually Happened](#9-real-run-output--what-actually-happened)
10. [Key Design Patterns](#10-key-design-patterns)
11. [Step-by-Step Build Guide](#11-step-by-step-build-guide)
12. [File Structure](#12-file-structure)
13. [Lessons Learned](#13-lessons-learned)
14. [Cost Breakdown](#14-cost-breakdown)

---

## 1. What We Built

An **autonomous AI publishing system** that:

1. Scans global news sentiment in real-time (Google Search grounding)
2. Decides what TYPE of content to publish based on world mood
3. Finds a unique topic (with semantic deduplication)
4. Creates a sentiment-aware visual identity (colors, fonts, theme)
5. Runs 4 analyst agents through structured debates with dedicated reviewers
6. Has analysts challenge each other in a Round Table
7. Synthesizes everything into luxury keynote-style slides
8. Checks for neutrality and ethical guardrails
9. Generates DALL-E images + Pillow infographics
10. Renders a landscape PDF slide deck
11. Audits every page for golden-ratio fill
12. Validates against 37 master rules (80% threshold to publish)
13. Posts to LinkedIn with a dynamic, catchy document title

**All of this runs autonomously in ~6-7 minutes with zero human input.**

Every agent invocation is fully traced — you can see exactly what fixed strings came from config, and what variable data came from which other agent.

---

## 2. Why Multi-Agent (Not Single-Agent)

### The Linear Pipeline Problem

Most developers build this:

```
Input → Agent 1 → Agent 2 → Agent 3 → Output
```

This fails because:
- No quality feedback loop — garbage propagates forward
- No debate — the first answer is always accepted
- No specialization — one prompt tries to do everything
- No traceability — you can't tell why the output looks the way it does

### What We Built Instead

```
World Pulse (Aria)
    ↓
Content Strategy (Marcus)  ← World Pulse
    ↓
Topic Discovery (Sable)    ← Content Strategy + World Pulse + Dedup
    ↓
Design DNA (Vesper) ←→ Design Reviewer (Onyx)     [2-3 rounds debate]
    ↓
┌── Historian (Clio) ←→ Reviewer (Theron)          [2-3 rounds debate]
├── Economist (Aurelia) ←→ Reviewer (Callisto)     [2-3 rounds debate]
├── Sociologist (Sage) ←→ Reviewer (Liora)         [2-3 rounds debate]
└── Futurist (Nova) ←→ Reviewer (Orion)            [2-3 rounds debate]
    ↓
Round Table — all analysts challenge each other
    ↓
Editor-in-Chief (Paramount) — quality gate
    ↓
Content Writer (Quill) ←→ Copy Reviewer (Sterling) [2-3 rounds debate]
    ↓
Neutrality Guard (Justice) — ethical gate
    ↓
Visual Generator (Prism) — DALL-E + Pillow
    ↓
PDF Renderer → Screen Auditor (Ratio)
    ↓
Final Validator (Sentinel) — 37 rules, 80% threshold
    ↓
LinkedIn Expert (Herald) — dynamic catchy title
```

**Key difference**: Agents argue. They go back and forth. The Historian writes, the Historian Reviewer tears it apart, the Historian revises. Then the Economist challenges the Historian in the Round Table. Then the Editor demands more. This is not a pipeline — it is a structured debate.

---

## 3. The 5 Design Principles

### Principle 1: Preparer/Reviewer Pairs
Every agent that creates content has a dedicated reviewer. They argue 2-3 rounds until the score reaches 7/10 or max rounds.

### Principle 2: Context-Aware (Not Static)
The system reads the WORLD before deciding what to create. Colors, content type, tone, length — all driven by real-time sentiment.

### Principle 3: Full Traceability
Every input to every agent is logged with its source. The tracer JSON shows: "ContentWriter received `content_type` from ContentStrategist (Marcus) who received `world_pulse` from WorldPulseScanner (Aria)."

### Principle 4: Ethical Guardrails at 3 Layers
The guardrail "Speak the truth, but never a truth that will hurt someone" is embedded in:
1. Editor-in-Chief (Paramount)
2. Content Writer (Quill)
3. Content Reviewer / Neutrality Guard (Justice)

### Principle 5: Master Config (Not Hardcoded)
All agent definitions, fixed strings, variable string sources, and control flags live in `agent_config.json`. A human or AI can read the config and understand the entire system without reading code.

---

## 4. Complete Architecture — 13 Phases

### Phase 0: World Pulse Scan
**Agent**: Aria (WorldPulseScanner)
**Model**: Gemini 2.0 Flash + Google Search Grounding
**Input**: Config only (no variable inputs — this is the root)
**Output**: Sentiment score (-100 to 100), mood, trending topics, AI news, market sentiment, recommended tone
**Purpose**: Read the room before publishing anything

### Phase 1: Content Strategy
**Agent**: Marcus (ContentStrategist)
**Model**: GPT-4o
**Input**: Fixed (12 content types, anchor filter) + Variable (World Pulse from Aria)
**Output**: Content type, page count (2-10), tone, topic direction
**Purpose**: Decide WHAT to publish. If world mood is extreme_sad, output "Silent" (don't post).

### Phase 2: Topic Discovery + Semantic Dedup
**Agent**: Sable (NewsScout)
**Model**: Gemini 2.0 Flash
**Input**: Fixed (search instructions) + Variable (content_type from Marcus, world_pulse from Aria, excluded topics from DedupEngine)
**Output**: Story (headline, summary, date, source, why_viral, key_quote, impact_areas)
**Purpose**: Find the exact topic. Checks against OpenAI embeddings (70% cosine similarity threshold) to avoid repeats. Up to 3 attempts if blocked.

### Phase 3: Design DNA + Debate
**Agent**: Vesper (DesignDNA) vs Onyx (DesignReviewer)
**Model**: GPT-4o (Vesper), Gemini Flash (Onyx)
**Input**: Fixed (available themes, fonts) + Variable (world_pulse, content_type, topic)
**Output**: Complete visual identity — 6 hex colors, font, theme, mood, image_generation_key
**Debate**: 2-3 rounds. Onyx checks: does the color psychology match today's world sentiment?

### Phase 4: Analyst Pairs (4 parallel debates)
**Agents**:
| Preparer | Codename | Reviewer | Codename | Domain |
|----------|----------|----------|----------|--------|
| Historian | Clio | HistorianReviewer | Theron | Historical parallels |
| Economist | Aurelia | EconomistReviewer | Callisto | Economic impact |
| Sociologist | Sage | SociologistReviewer | Liora | Social implications |
| Futurist | Nova | FuturistReviewer | Orion | Future predictions |

**Model**: Gemini Flash (preparers), GPT-4o (reviewers)
**Debate**: Each pair argues 2-3 rounds until score >= 7/10

### Phase 5: Round Table
**What happens**: Economist challenges Historian. Historian challenges Futurist. Futurist challenges Sociologist. Sociologist challenges Economist. Then each incorporates the incoming challenges into their work.
**Purpose**: Cross-pollinate perspectives. Force agents to defend their positions.

### Phase 6: Editorial Oversight
**Agent**: Paramount (EditorInChief)
**Model**: GPT-4o
**Input**: All analyst perspectives
**Output**: Quality score, feedback per agent, missing angles
**Purpose**: Final quality gate before synthesis. If score < 8, agents must revise.

### Phase 7: Content Synthesis + Copy Review
**Agent**: Quill (ContentWriter) vs Sterling (CopyReviewer)
**Model**: GPT-4o
**Input**: All perspectives + design DNA + content strategy
**Output**: Page-by-page brief (title, point, insight, quote per slide)
**Rule**: STRICT — max 1 point per slide. One diamond, not a bag of pebbles.
**Debate**: 2-3 rounds.

### Phase 8: Neutrality Check
**Agent**: Justice (NeutralityGuard)
**Model**: GPT-4o
**Input**: Final brief
**Output**: Approved/rejected, tone score
**Purpose**: Enforce the ethical guardrail. No attacks on individuals.

### Phase 9: Visual Generation
**Agent**: Prism (VisualGenerator)
**Tools**: DALL-E 3 (cover + section images), Pillow (stat cards, timelines, bar charts, donut charts)
**Key feature**: All DALL-E prompts include the `image_generation_key` from Design DNA for visual coherence across all pages.

### Phase 10: PDF Rendering
**Tool**: ReportLab
**Format**: Landscape (792x612 pts, like PPT slides)
**Features**: 6 rotating artistic background styles, big 40-44pt headers, author prominent at >= 75% of header size, luxury name generator for assistant credit

### Phase 11: Screen Real Estate Audit
**Agent**: Ratio (ScreenAuditor)
**Model**: GPT-4o
**Input**: Page-by-page content summary
**Output**: Fill percentage per page, golden ratio compliance
**Rule**: 55-65% fill. Never more than 45% empty.

### Phase 12: Final Validation (37 Rules)
**Agent**: Sentinel (FinalValidator)
**Model**: GPT-4o
**Input**: Everything (brief, design, audit, agent debate proof from tracer)
**Output**: Score 0-100, pass/fail per rule, critical failures
**Threshold**: 80% to publish. If <80%, regenerate with fix instructions.

### Phase 13: LinkedIn Post
**Agent**: Herald (LinkedInExpert)
**Model**: GPT-4o
**Input**: Brief + design mood
**Output**: Post text (Unicode bold/italic), dynamic document title, hashtags
**Key fix**: Document title is topic-specific and catchy (e.g., "Lloyds' $127M AI Leap: A New Banking Era") — NOT generic "AI Strategy Brief"

---

## 5. Agent Roster — All 20+ Agents

| # | Agent | Codename | Model | Role | Talks To |
|---|-------|----------|-------|------|----------|
| 1 | WorldPulseScanner | Aria | Gemini Flash + Search | Global sentiment scan | ContentStrategist |
| 2 | ContentStrategist | Marcus | GPT-4o | Choose content type + length | DesignDNA, NewsScout |
| 3 | NewsScout | Sable | Gemini Flash | Find unique topic | All analysts |
| 4 | DesignDNA | Vesper | GPT-4o | Visual identity creation | DesignReviewer, Visuals, PDF |
| 5 | DesignReviewer | Onyx | Gemini Flash | Critique design DNA | DesignDNA |
| 6 | Historian | Clio | Gemini Flash | Historical parallels | HistorianReviewer, RoundTable |
| 7 | HistorianReviewer | Theron | GPT-4o | Critique history analysis | Historian |
| 8 | Economist | Aurelia | Gemini Flash | Economic impact | EconomistReviewer, RoundTable |
| 9 | EconomistReviewer | Callisto | GPT-4o | Critique economic analysis | Economist |
| 10 | Sociologist | Sage | Gemini Flash | Social implications | SociologistReviewer, RoundTable |
| 11 | SociologistReviewer | Liora | GPT-4o | Critique social analysis | Sociologist |
| 12 | Futurist | Nova | Gemini Flash | Future predictions | FuturistReviewer, RoundTable |
| 13 | FuturistReviewer | Orion | GPT-4o | Critique predictions | Futurist |
| 14 | EditorInChief | Paramount | GPT-4o | Final editorial authority | ContentWriter |
| 15 | ContentWriter | Quill | GPT-4o | Luxury keynote synthesis | CopyReviewer |
| 16 | CopyReviewer | Sterling | GPT-4o | Luxury copy critique | ContentWriter |
| 17 | NeutralityGuard | Justice | GPT-4o | Ethical guardrail | ContentWriter |
| 18 | VisualGenerator | Prism | DALL-E 3 + Pillow | Images + infographics | PDFRenderer |
| 19 | ScreenAuditor | Ratio | GPT-4o | Page fill audit | FinalValidator |
| 20 | FinalValidator | Sentinel | GPT-4o | 37-rule master check | LinkedInExpert |
| 21 | LinkedInExpert | Herald | GPT-4o | Viral LinkedIn post | Publisher |

---

## 6. The Debate Engine — How Agents Argue

### Core Loop

```python
def _argue(preparer, reviewer, initial_work, label, context):
    work = initial_work
    for round in range(1, MAX_ROUNDS + 1):   # MAX_ROUNDS = 3
        review = reviewer.think(f"Review this {label} work. Round {round}.")
        score = review["overall_score"]
        approved = review["approved"]

        if approved and score >= 7:
            break  # Quality bar met

        if round < MAX_ROUNDS:
            work = preparer.respond_to_feedback(work, review)
            # Preparer revises based on reviewer's demands

    tracer.log_debate(f"{preparer} vs {reviewer}", rounds)
    return work
```

### What makes this different from a simple retry loop:

1. **The reviewer is a DIFFERENT agent** with a different persona and expertise
2. **The reviewer scores on 5 criteria** (depth, specificity, originality, tone, actionability)
3. **The reviewer gives specific demands** ("Add concrete $ figures", "This is boilerplate, give me a fresh take")
4. **The preparer sees the demands** and must address each one
5. **The tracer records every round** as proof of debate

### Example from real run:

```
[HISTORICAL]
  Preparer: Historian (Clio) | Reviewer: historical Reviewer (Theron)
    Round 1: score=6/10, approved=False, demands=4
    → Historian revised
    Round 2: score=7/10, approved=False, demands=2
    → Historian revised
    Round 3: score=8/10, approved=True, demands=0
    ✓ historical APPROVED after 3 rounds
```

The Historian's work improved from 6/10 to 8/10 across 3 rounds of critique.

---

## 7. The Tracer — Full Provenance Chain

### Why a Tracer?

In a multi-agent system, every agent receives input that is a combination of:
- **Fixed strings** — from config (the agent's instructions, prompts, rules)
- **Variable strings** — from other agents' outputs

The config file can only show EXAMPLES of what variable inputs look like. The tracer shows the REAL values from each run.

### Tracer Output Structure

```json
{
  "run_id": "run_20260210_231417",
  "mode": "autonomous",
  "total_duration_seconds": 401.82,
  "total_agent_calls": 15,
  "total_debates": 7,

  "agent_flow": [
    "WorldPulseScanner (Aria) ← [config only]",
    "ContentStrategist (Marcus) ← [WorldPulseScanner.world_pulse]",
    "NewsScout (Sable) ← [ContentStrategist.content_type + WorldPulseScanner.world_pulse + DedupEngine.excluded_topics]",
    "DesignDNA (Vesper) ← [WorldPulseScanner.world_pulse + ContentStrategist.content_type + NewsScout.topic]",
    "DEBATE: Design DNA vs Design Reviewer [visual_design] (2 rounds)",
    "Historian (Clio) ← [NewsScout.story + ContentStrategist.content_type]",
    "DEBATE: Historian vs historical Reviewer [historical] (3 rounds)",
    "..."
  ],

  "phases": [
    {
      "phase": "ContentStrategy",
      "agent_name": "ContentStrategist",
      "agent_codename": "Marcus",
      "model": "gpt-4o",
      "inputs": {
        "fixed": {
          "core_instruction": {
            "value": "Based on the world pulse, choose...",
            "source": "agent_config.json → agents.ContentStrategist.fixed_strings.core_instruction"
          }
        },
        "variable": {
          "world_pulse": {
            "value": {"sentiment_score": -15, "mood": "normal", "..."},
            "source_agent": "WorldPulseScanner",
            "source_codename": "Aria",
            "source_phase": "WorldPulse"
          }
        }
      },
      "output": {
        "content_type": "Trend Roundup",
        "page_count": 7,
        "tone": "informative and balanced"
      },
      "duration_seconds": 3.5
    }
  ]
}
```

### How to Read a Trace Entry

For any agent, you can answer:
1. **What fixed instructions did it have?** → `inputs.fixed` (from config)
2. **What data came from other agents?** → `inputs.variable` (with source agent name and phase)
3. **What did it produce?** → `output`
4. **How long did it take?** → `duration_seconds`

---

## 8. The Config — Fixed vs Variable Strings

### The Problem

In a multi-agent system, each agent's prompt is built from:
- **Fixed strings**: things that never change (instructions, rules, guardrails)
- **Variable strings**: data from other agents (changes every run)

### Solution: `agent_config.json`

```json
{
  "agents": {
    "ContentStrategist": {
      "name": "Marcus",
      "model": "gpt-4o",
      "fixed_strings": {
        "core_instruction": "Based on the world pulse, choose the best content type...",
        "content_types": ["Breaking News Analysis", "Historical Retrospective", "..."]
      },
      "variable_strings": {
        "world_pulse": {
          "source": "WorldPulseScanner",
          "description": "Current global sentiment data"
        }
      },
      "outputs_to": ["DesignDNA", "NewsScout"]
    }
  }
}
```

**Fixed strings** → defined in the config, same every run
**Variable strings** → the config only says WHERE the data comes from. The actual value is different every run (captured in the tracer).

### Control Flags

```json
{
  "controls": {
    "autonomous": true,
    "post_to_linkedin": true,
    "max_pages": 10,
    "min_pages": 2,
    "dedup_threshold": 0.70,
    "validation_threshold": 80,
    "max_design_rounds": 3,
    "max_topic_attempts": 3,
    "force_content_type": null,
    "force_topic": null
  }
}
```

Set `autonomous: false` to enable manual control. Set `force_content_type` to override the Content Strategist's decision.

---

## 9. Real Run Output — What Actually Happened

### Run: February 10, 2026 — 6.6 minutes

```
PHASE 0: WORLD PULSE SCAN (Aria)
  [Aria] Gemini+Search | 780 tok
  Score: -15, Mood: normal, Tone: neutral
  Trending: Winter Olympics 2026, Geopolitical Tensions, AI Integration
  AI News: OpenAI testing ads, Lloyds $127M AI, AI cancer diagnostics 95%
  Market: mixed

PHASE 1: CONTENT STRATEGY (Marcus)
  Content type: Trend Roundup (7 pages)
  Tone: informative and balanced
  Reasoning: Normal mood, AI monetization trending, good for trend roundup

PHASE 2: TOPIC DISCOVERY (Sable)
  Candidate: "Lloyds Banking Group Aims for $127M Boost with Generative AI"
  Dedup check: max 36.4% similarity to prior posts → UNIQUE

PHASE 3: DESIGN DNA (Vesper vs Onyx)
  Design: "Refined Deco Dynamics" — Art Deco theme
  Palette: #23395B (navy) / #A9A9A9 (silver) / accent gold
  Image key: "luxury editorial, refined art deco, antique gold, intricate geometric"
  Debate: 2 rounds (6/10 → 8/10, approved)

PHASE 4: ANALYST PAIRS (4 debates, 3 rounds each)
  Historical  (Clio vs Theron):    6→7→8, approved after 3 rounds
  Economic    (Aurelia vs Callisto): 6→7→8, approved after 3 rounds
  Social      (Sage vs Liora):      6→7→8, approved after 3 rounds
  Future      (Nova vs Orion):      6→7→8, approved after 3 rounds

PHASE 5: ROUND TABLE
  Economist → Historian: "Beyond Historical Parallels — Quantifying AI's..."
  Historian → Futurist: "Beyond Prediction: A Call for Proactive AI Governance..."
  Futurist → Sociologist: "Rebuttal: Beyond Human-Centric..."
  Sociologist → Economist: "Challenging the Economist: A Human-Centered Critique..."
  All agents incorporated cross-challenges.

PHASE 6: EDITORIAL OVERSIGHT (Paramount)
  Score: 8/10 — ready for synthesis

PHASE 7: CONTENT SYNTHESIS (Quill vs Sterling)
  Brief: "Generative AI: Elevating Banking's Horizon" — 8 slides
  Debate: 2 rounds (7/10 → 8/10, approved)

PHASE 8: NEUTRALITY CHECK (Justice)
  Approved: True, Tone score: 10/10

PHASE 9: VISUALS (Prism)
  8 visual elements: 1 DALL-E cover + 7 infographics (Pillow)

PHASE 10: PDF
  7843 KB, 8 luxury landscape slides

PHASE 11: SCREEN AUDIT (Ratio)
  PASS — golden ratio compliance

PHASE 12: FINAL VALIDATION (Sentinel)
  Score: 85/100 — APPROVED (threshold: 80%)

PHASE 13: LINKEDIN (Herald)
  Document title: "Lloyds' $127M AI Leap: A New Banking Era"
  Post: 1138 chars with Unicode bold formatting
  URL: linkedin.com/feed/update/urn:li:ugcPost:7427114391088582656
```

---

## 10. Key Design Patterns

### Pattern 1: Sentiment-Driven Everything
The World Pulse doesn't just decide content — it drives design (colors, fonts, theme), tone, and even whether to post at all. This is the core innovation: the system reads the world before acting.

### Pattern 2: Debate, Not Pipeline
Every creative agent has a paired critic. They argue for 2-3 rounds. Quality improves measurably (scores go from 6 to 8). This catches mediocre output before it propagates.

### Pattern 3: Cross-Agent Challenge (Round Table)
After individual debates, agents see each OTHER's work and challenge it. The Economist challenges the Historian. The Futurist challenges the Sociologist. This creates truly multi-perspective output.

### Pattern 4: Semantic Deduplication
Before any analysis begins, the topic is checked against all prior posts using OpenAI embeddings (text-embedding-3-small) with cosine similarity. Threshold: 70%. If blocked, the scout finds a new topic (up to 3 attempts).

### Pattern 5: Master Validation Gate
37 rules, weighted by severity. Score must be >= 80% to publish. If it fails, the system regenerates with specific fix instructions. This is the "client representative" — it never lets anything slide.

### Pattern 6: Config + Tracer = Reproducibility
The config defines WHAT each agent does (fixed strings) and WHERE its inputs come from (variable strings). The tracer captures the ACTUAL values for each run. Together they provide complete reproducibility.

### Pattern 7: Model Stratification
Cheap tasks (scanning, initial analysis) use Gemini Flash (~$0.0002/call). Strategic/creative tasks (content strategy, design DNA, copy review, validation) use GPT-4o (~$0.01/call). This optimizes cost while maintaining quality where it matters.

### Pattern 8: Ethical Guardrail at 3 Layers
The guardrail isn't just in one prompt — it's in the Editor-in-Chief, the Content Writer, AND the Neutrality Guard. If one misses something, the others catch it. Defense in depth.

---

## 11. Step-by-Step Build Guide

### Prerequisites
- Python 3.10+
- Cursor IDE (with Claude agent)
- API keys: OpenAI, Google Gemini, LinkedIn
- pip packages: `openai`, `google-genai`, `reportlab`, `Pillow`, `python-dotenv`, `requests`

### Step 1: Project Structure (10 min)

```
aibrief/
├── agent_config.json          # Master config — all agents defined here
├── config.py                  # API keys, model assignments, paths
├── main.py                    # Entry point (autonomous mode)
├── agents/
│   ├── base.py                # Base Agent class (OpenAI + Gemini)
│   ├── world_pulse.py         # WorldPulseScanner (Gemini + Google Search)
│   ├── content_strategist.py  # ContentStrategist (content type selection)
│   ├── design_dna.py          # DesignDNA (visual identity creation)
│   ├── specialists.py         # All specialist agents (analysts, writer, etc.)
│   ├── orchestrator.py        # AutonomousOrchestrator (13 phases)
│   └── validators.py          # FinalValidator + 37-rule checklist
├── pipeline/
│   ├── tracer.py              # RunTracer (full provenance tracking)
│   ├── pdf_gen.py             # ReportLab PDF generator (landscape slides)
│   ├── visuals.py             # DALL-E + Pillow infographics
│   ├── linkedin.py            # LinkedIn API posting
│   └── dedup.py               # Semantic deduplication (embeddings)
├── output/                    # Generated PDFs and visuals
├── traces/                    # One JSON per run — full provenance
├── feedback_log.json          # User feedback + 37 rules
└── post_log.json              # LinkedIn post history + embeddings
```

### Step 2: Base Agent Class (30 min)

Build a base `Agent` class that:
- Supports both OpenAI and Gemini (auto-selects by model name prefix)
- Has `think()` for primary calls, `critique()` for reviews, `respond_to_feedback()` for revisions
- Handles JSON parsing (Gemini sometimes returns lists, markdown fences)
- Falls back OpenAI → Gemini if one fails
- Tracks token usage and cost

### Step 3: World Pulse Scanner (20 min)

- Uses Gemini with Google Search grounding for real-time data
- Falls back to model knowledge if search fails
- Returns structured sentiment: score, mood, trending topics, AI news, market
- Calibrated: 80% of days should score NORMAL

### Step 4: Content Strategist (20 min)

- Receives World Pulse as input
- Chooses from 12+ content types
- Decides page count (2-10)
- Enforces the brand anchor (AI thought leadership)
- Has sentiment-driven rules (anxious → calming perspective, optimistic → bold prediction)

### Step 5: Design DNA Agent (20 min)

- Receives World Pulse + Content Strategy + Topic
- Generates complete visual identity (6 colors, font, theme, motif)
- Creates `image_generation_key` for DALL-E coherence
- Justifies every choice by design psychology
- Gets debated by Design Reviewer

### Step 6: Analyst Agents (30 min)

Build 4 analyst agents (Historian, Economist, Sociologist, Futurist) and 4 dedicated reviewers. Each reviewer has specific criteria (depth, specificity, originality, tone, actionability).

### Step 7: Debate Engine (20 min)

The `_argue()` method in the orchestrator runs preparer/reviewer pairs:
1. Reviewer critiques (scores 1-10, lists demands)
2. If approved and score >= 7: done
3. Else: preparer revises based on demands
4. Repeat up to MAX_ROUNDS (3)

### Step 8: Round Table (15 min)

After individual debates, agents see ALL perspectives:
- Economist challenges Historian's work
- Historian challenges Futurist's work
- Each incorporates incoming challenges

### Step 9: Content Writer + Copy Reviewer (20 min)

- Writer synthesizes all perspectives into page-by-page slides
- STRICT: 1 point per slide, 1 insight, 1 quote
- Copy Reviewer enforces luxury ad quality
- They argue 2-3 rounds

### Step 10: Validation Pipeline (30 min)

Build the pipeline:
1. Neutrality Guard (ethical check)
2. Screen Real Estate Auditor (55-65% fill, golden ratio)
3. Final Validator (37 weighted rules, 80% threshold)

### Step 11: Visuals + PDF (45 min)

- DALL-E 3 for cover and section images (with image_generation_key)
- Pillow for stat cards, timelines, bar charts, donut charts
- ReportLab for landscape PDF with artistic backgrounds

### Step 12: LinkedIn + Dedup (20 min)

- LinkedIn Documents API for PDF upload
- Dynamic document title (topic-specific, catchy)
- Unicode bold/italic formatting
- OpenAI embeddings for semantic dedup (70% threshold)

### Step 13: Tracer (30 min)

Build `RunTracer` class:
- `begin_phase()` — records fixed + variable inputs
- `end_phase()` — records output
- `log_debate()` — records debate rounds
- `save()` — writes full trace to JSON
- `var_ref()` — creates source-attributed variable references

### Step 14: Orchestrator (60 min)

The big one. Wire all 13 phases together:
- Load `agent_config.json`
- Initialize all agents
- Run phases sequentially, passing outputs as inputs
- Trace every invocation
- Handle the "Silent" case (don't post if world is extreme_sad)

### Step 15: Test + Run (30 min)

```bash
# Dry run (only World Pulse + Content Strategy)
python -m aibrief.main --dry-run

# Full run without posting
python -m aibrief.main --no-post

# Full autonomous run
python -m aibrief.main
```

**Total estimated build time: ~6-8 hours for an experienced developer with Cursor AI.**

---

## 12. File Structure

| File | Lines | Purpose |
|------|-------|---------|
| `agent_config.json` | 360 | Master config — all agents, strings, controls |
| `config.py` | 55 | API keys, model assignments, paths |
| `main.py` | 100 | Entry point with --dry-run, --no-post |
| `agents/base.py` | 143 | Base Agent class (OpenAI + Gemini) |
| `agents/world_pulse.py` | 180 | WorldPulseScanner with Google Search |
| `agents/content_strategist.py` | 120 | Content type + length selection |
| `agents/design_dna.py` | 110 | Sentiment-aware visual identity |
| `agents/specialists.py` | 440 | All specialist agents |
| `agents/orchestrator.py` | 600 | AutonomousOrchestrator — 13 phases |
| `agents/validators.py` | 145 | FinalValidator + 37 rules |
| `pipeline/tracer.py` | 170 | Full provenance tracking |
| `pipeline/pdf_gen.py` | 520 | Landscape PDF slide generator |
| `pipeline/visuals.py` | 420 | DALL-E + Pillow infographics |
| `pipeline/linkedin.py` | 190 | LinkedIn posting with dynamic title |
| `pipeline/dedup.py` | 190 | Semantic dedup with embeddings |
| **Total** | **~3,750** | |

---

## 13. Lessons Learned

### 1. Agents should argue, not just chain
The biggest quality improvement came from Preparer/Reviewer pairs. Scores consistently went from 6 to 8 across rounds. Without debate, the first mediocre answer would have been published.

### 2. Context-awareness is not optional
A system that publishes happy bright content on a day the world is mourning is worse than no system. The World Pulse solves this.

### 3. The config is the architecture
Anyone who reads `agent_config.json` understands the entire system — who talks to whom, what's fixed, what's variable. This is the real documentation.

### 4. The tracer is the debugger
When output quality is bad, the tracer shows exactly which agent produced garbage and what inputs it received. Without tracing, debugging multi-agent systems is impossible.

### 5. Model stratification saves money
Use cheap models (Gemini Flash) for scanning and initial drafts. Use expensive models (GPT-4o) for strategic decisions and reviews. Our run cost ~$0.15-0.25 total.

### 6. Guardrails must be layered
One guardrail is bypassed by one bad prompt. Three guardrails at different stages (creation, review, final check) create defense in depth.

### 7. Semantic dedup prevents embarrassment
Without dedup, the system would post about the same topic repeatedly. Embedding-based similarity (70% cosine threshold) catches topic overlap even when headlines differ.

### 8. Don't hardcode document titles
"AI Strategy Brief" every time = boring. Dynamic, topic-specific titles ("Lloyds' $127M AI Leap: A New Banking Era") increase click-through.

---

## 14. Cost Breakdown

### Per Run (approximate)

| Component | Model | Calls | Cost |
|-----------|-------|-------|------|
| World Pulse | Gemini Flash + Search | 1 | $0.0002 |
| Content Strategy | GPT-4o | 1 | $0.005 |
| Topic Discovery | Gemini Flash | 1 | $0.0002 |
| Design DNA + Debate | GPT-4o + Gemini Flash | 4 | $0.015 |
| 4 Analyst Pairs (3 rounds each) | Gemini Flash + GPT-4o | 24 | $0.07 |
| Round Table | Gemini Flash | 8 | $0.005 |
| Editorial | GPT-4o | 1 | $0.01 |
| Content Synthesis + Debate | GPT-4o | 4 | $0.05 |
| Neutrality | GPT-4o | 1 | $0.005 |
| Screen Audit | GPT-4o | 1 | $0.007 |
| Final Validation | GPT-4o | 1 | $0.022 |
| LinkedIn Expert | GPT-4o | 1 | $0.011 |
| DALL-E Cover Image | DALL-E 3 | 1 | $0.08 |
| Semantic Embedding | text-embedding-3-small | 2 | $0.0001 |
| **Total per run** | | **~50** | **$0.15-0.30** |

At $0.25/run, you can publish 4 times/day for ~$1/day or ~$30/month.

---

## Summary

This system proves that multi-agent AI is not about having MORE agents — it's about having agents that **argue, challenge, and improve each other's work** through structured debate, all driven by real-world context, and fully traced for auditability.

The 5 things that make this system production-grade:
1. **World Pulse** — reads the room before acting
2. **Debate Engine** — quality improves through structured argument
3. **Master Config** — the architecture is readable, not just code
4. **Run Tracer** — full provenance chain for every input/output
5. **37-Rule Validator** — nothing ships below the quality bar

---

*Built by Bhasker Kumar with AI assistance. System architecture: Claude (Cursor) + GPT-4o + Gemini Flash + DALL-E 3.*
