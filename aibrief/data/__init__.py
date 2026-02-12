"""Centralized data storage for AI Brief — designed for meta-analysis.

Directory structure:
  data/
    runs_index.json       → Lightweight index of ALL runs (for cross-run analytics)
    debates/
      {run_id}.json       → Full debate conversations per run (chat-style)
    validations/
      {run_id}.json       → Pre + post validation results per run

Traces still live in aibrief/traces/ — they hold the full agent flow.
This data/ directory holds STRUCTURED, QUERYABLE extracts optimized
for meta-analysis across all documents ever produced.

Meta-analysis use cases:
  - Which reviewer is harshest? (avg score by reviewer across runs)
  - How many rounds does each debate typically take?
  - Do certain emotions/styles correlate with higher validation scores?
  - What are the most common reviewer demands?
  - Content quality trends over time
  - Cost and duration trends
"""
