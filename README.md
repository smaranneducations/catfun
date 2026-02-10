# FinanceCats

AI-powered finance education video generator. A professional cat character pauses real financial news clips to explain complex terminology, backed by historical examples and storytelling.

## How It Works

1. **7 AI agents** collaborate to find a trending finance term, research its history, write a script, fact-check it, and design the visuals
2. A real news clip is found where an anchor uses the target term
3. The video pauses the clip, and a cat narrator explains the term with historical examples
4. The final 4-6.5 minute video is composed with blurred backgrounds, text overlays, and professional voice narration

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate 30 professional cat images (run once, costs ~$1.20)
python main.py --generate-cats

# Auto-select a topic and generate a video
python main.py

# Use a specific news clip
python main.py "https://youtube.com/watch?v=EXAMPLE"
```

## The 7 Agents

| Agent | Role |
|-------|------|
| Executive Producer | Brand guardian, decides topics, approves scripts |
| Research Analyst | Finds trending news clips with complex terminology |
| Financial Historian | Researches historical events tied to each term |
| Script Writer | Crafts the 4-6.5 minute educational script |
| Fact Checker | Verifies all claims, dates, and numbers |
| Creative Director | Selects cat images and designs visual overlays |
| YouTube Strategist | Writes SEO titles, descriptions, and tags |

## Video Structure

```
0:00-0:20  News clip plays (hook)
0:20-0:50  Cat intro — "Watch for this..."
0:50-1:20  News clip again (context)
1:20-3:50  THE LECTURE (definition + historical examples)
3:50-4:10  Final news clip segment
4:10-4:40  Cat wrap-up + tease next episode
```

## Episode Log

Every video is logged in `episode_log.json` to maintain brand consistency — no repeated terms, cats, or historical events.
