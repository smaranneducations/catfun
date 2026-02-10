# FinanceCats v3

AI-powered finance education video generator. An AI news anchor reads viral economic/geopolitical news, then two professional cat characters explain the financial term embedded in the story — ultra-simple, with real-life analogies anyone can understand.

## What's New in V3

- **AI News Anchor** — A HeyGen-generated female anchor reads viral news in a high-end studio (no more third-party clips)
- **Viral-first approach** — Finds the most viral economic/geopolitical story of the week, then picks a teaching term to embed
- **100% original content** — No copyright risk from third-party news clips
- **Shorter, punchier videos** — 3-4 minutes total (anchor 60-90s + cat conversation 2-3 min)
- **Frozen anchor layout** — During cat explanation, the anchor frame freezes; cats overlay on one side
- **Anchor always starts with date** — "OK, this news is from [date]..."
- **Series tracking** — each episode teases the next term, creating binge-worthy series

## How It Works

1. **Viral News Scout** finds the most viral story from the last 7 days
2. **Scout picks a teaching term** that naturally connects to the story
3. **Script Writer** creates TWO scripts: anchor report + cat conversation
4. **HeyGen API** generates a realistic talking-head anchor video
5. **ElevenLabs** generates cat dialogue voices (Professor Whiskers + Cleo)
6. **Compose**: anchor video plays → frame freezes → cats overlay explaining the term
7. Upload to YouTube + LinkedIn

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API keys in .env (see .env for all required keys)
# Required: OPENAI_API_KEY, ELEVENLABS_API_KEY, HEYGEN_API_KEY
# Optional: YOUTUBE_API_KEY, LINKEDIN_ACCESS_TOKEN

# Generate 30 professional cat images (run once)
python main.py --generate-cats

# List available HeyGen avatars (pick a female anchor)
python main.py --list-avatars

# Run the full pipeline
python main.py

# Run without uploading (for testing)
python main.py --no-upload

# Retry failed uploads
python main.py --retry
```

## The Agents

| Agent | Role |
|-------|------|
| Viral News Scout | Finds the most viral economic/geopolitical news |
| Executive Producer | Brand guardian, manages series continuity |
| Financial Historian | Researches historical events tied to each term |
| Sociological Analyst | Adds social impact angles (when relevant) |
| Geopolitical Analyst | Adds geopolitical context (when relevant) |
| Script Writer | Writes anchor script + cat conversation script |
| Fact Checker | Verifies all claims, dates, and numbers |
| Creative Director | Selects two cat images and designs visual overlays |
| YouTube Strategist | Writes SEO titles, descriptions, and tags |
| LinkedIn Strategist | Creates LinkedIn post copy |

## The Characters

| Character | Voice | Role |
|-----------|-------|------|
| AI News Anchor | HeyGen AI (female) | Reads viral news, embeds financial term |
| Professor Whiskers | Daniel (British male, ElevenLabs) | The calm, knowledgeable explainer |
| Cleo | Charlotte (British female, ElevenLabs) | The curious questioner |

## Video Structure

```
0:00-1:30  AI Anchor reads viral news (embeds financial term naturally)
1:30-3:30  FROZEN ANCHOR FRAME + CAT OVERLAY
           - Anchor visible on left side
           - Cats on right side (slightly smaller)
           - Cats explain the term: definition, why now, history, takeaway
3:30-4:00  Cats wrap up + tease next episode's term
```

## Visual Layout (Cat Section)

```
┌────────────────────────────────────────────────┐
│                                                │
│  [FROZEN ANCHOR FRAME]    [Cat A]    [Cat B]   │
│  (left 55% of screen)    (right side, smaller) │
│                           [text + key points]  │
│                                                │
└────────────────────────────────────────────────┘
```

## API Keys Needed

| Service | Key | Purpose |
|---------|-----|---------|
| OpenAI | `OPENAI_API_KEY` | All agent LLM calls (GPT-4o) |
| HeyGen | `HEYGEN_API_KEY` | AI anchor video generation |
| ElevenLabs | `ELEVENLABS_API_KEY` | Cat voice generation (TTS) |
| YouTube | `YOUTUBE_API_KEY` + OAuth | Video upload |
| LinkedIn | `LINKEDIN_ACCESS_TOKEN` | Post creation |

## Series Tracking

Every video teases the next episode's term in the wrap-up. This term is saved in `episode_log.json` so the next run automatically picks it up, creating connected series of 10-15 episodes.

## HeyGen Setup

1. Sign up at [heygen.com](https://heygen.com)
2. Get your API key from Settings → API
3. Add `HEYGEN_API_KEY=your_key` to `.env`
4. Run `python main.py --list-avatars` to see available avatars
5. Optionally set `HEYGEN_AVATAR_ID=avatar_id` for a specific anchor

Without a HeyGen API key, the pipeline falls back to ElevenLabs TTS audio over a static news-style background frame.
