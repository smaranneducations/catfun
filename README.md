# AI Brief

Autonomous multi-agent system that generates professional, visually rich PDF thought-leadership documents and posts them to LinkedIn. Scans for trending news in economics, tech, science, and media — then produces a 6-page poster-format PDF with emotion-driven design, AI-generated visuals, and a full agent credits section.

## How It Works

1. **World Pulse** scans global sentiment to determine the emotional tone
2. **News Scout** finds a real, verified trending article via Google Search grounding
3. **Content Strategist** writes the brief (headline, 4 content pages, key insights)
4. **Design DNA** detects the dominant emotion and maps it to a hardcoded design palette
5. **Visual Generator** creates background + foreground images (Imagen 4.0 / DALL-E 3 / Pillow fallback)
6. **Poster Generator** renders a multi-page PDF with ReportLab
7. **Final Validator** checks 37 quality rules (80% pass threshold)
8. **LinkedIn Expert** crafts the post copy and publishes the PDF

## The Agents

| Agent | Model | Role |
|-------|-------|------|
| World Pulse (Aria) | Gemini Flash | Global sentiment scanner |
| News Scout (Kira) | Gemini Flash + Google Search | Finds real, verified trending news |
| Content Strategist | Gemini Pro | Writes the brief content |
| Design DNA | Gemini Pro | Detects emotion, maps to design catalog |
| Copy Reviewer | GPT-4o | Critiques and refines content |
| Visual Generator | Imagen 4.0 / DALL-E 3 | Generates background + foreground images |
| LinkedIn Expert | GPT-4o | Crafts LinkedIn post with Unicode formatting |
| Final Validator | GPT-4o | Validates PDF against 37 quality checkpoints |

**Author:** Bhasker Kumar
**Agent:** Orion Cael

## Quick Start

```bash
pip install -r requirements.txt

# Set up .env with API keys (OPENAI_API_KEY, GEMINI_API_KEY, LINKEDIN_ACCESS_TOKEN)

# Run the full pipeline
python -m aibrief.main

# Scheduler: 3x daily at random times
python -m aibrief.scheduler
```

## Project Structure

```
aibrief/
  main.py                  # Entry point
  config.py                # Central configuration
  agent_config.json        # Agent roles, models, prompts
  scheduler.py             # Runs pipeline 3x/day
  agents/
    base.py                # Base LLM agent (OpenAI + Gemini fallback)
    orchestrator.py        # 13-phase pipeline orchestrator
    specialists.py         # NewsScout, LinkedInExpert, CopyReviewer
    world_pulse.py         # Global sentiment scanner
    content_strategist.py  # Brief content writer
    design_dna.py          # Emotion detection -> design mapping
    validators.py          # 37-rule quality validator
  pipeline/
    design_catalog.py      # Emotion-to-design hardcoded map
    poster_gen.py          # PDF layout engine (ReportLab)
    visuals.py             # Image generation (Imagen/DALL-E/Pillow)
    linkedin.py            # LinkedIn API client
    dedup.py               # Semantic deduplication (embeddings)
    tracer.py              # Run logging and decision architecture
```

## API Keys

| Service | Env Var | Purpose |
|---------|---------|---------|
| OpenAI | `OPENAI_API_KEY` | GPT-4o, DALL-E 3, embeddings |
| Google | `GEMINI_API_KEY` | Gemini Flash/Pro, Imagen 4.0, Search grounding |
| LinkedIn | `LINKEDIN_ACCESS_TOKEN` | PDF upload + post creation |
