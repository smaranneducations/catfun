"""Semantic deduplication — prevents posting on the same topic twice.

Uses OpenAI embeddings + cosine similarity.
Threshold: 70% similarity = duplicate, skip and find new topic.

This runs IMMEDIATELY after NewsScout finds a story, BEFORE any analysis.
If the story is too similar to a previous post, the orchestrator must
ask NewsScout for a different story.
"""
import json
import math
from pathlib import Path
from openai import OpenAI
from aibrief import config

_openai = OpenAI(api_key=config.OPENAI_API_KEY)
POST_LOG = config.BASE_DIR / "post_log.json"
SIMILARITY_THRESHOLD = 0.70  # 70% = duplicate


def _get_embedding(text: str) -> list[float]:
    """Get embedding vector from OpenAI text-embedding-3-small."""
    resp = _openai.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000],  # max input safety
    )
    return resp.data[0].embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _build_topic_text(story: dict) -> str:
    """Build a rich text representation for embedding.

    Combines headline + summary + key entities for robust matching.
    This catches cases where headline differs but topic is the same.
    """
    parts = [
        story.get("headline", ""),
        story.get("summary", ""),
        ", ".join(story.get("impact_areas", [])),
        story.get("source", ""),
        story.get("key_quote", "")[:100],
    ]
    return " | ".join(p for p in parts if p)


def load_post_log() -> dict:
    """Load the post log."""
    if POST_LOG.exists():
        return json.loads(POST_LOG.read_text(encoding="utf-8"))
    return {"posts": [], "topics_covered": [], "embeddings": [],
            "total_posts": 0}


def save_post_log(log: dict):
    """Save the post log."""
    POST_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False),
                        encoding="utf-8")


def is_duplicate(story: dict) -> tuple[bool, float, str]:
    """Check if a story is semantically too similar to any previous post.

    Returns:
        (is_dup: bool, max_similarity: float, matched_topic: str)

    If max_similarity >= 0.70, it's a duplicate.
    """
    log = load_post_log()
    stored_embeddings = log.get("embeddings", [])

    if not stored_embeddings:
        print("  [Dedup] No previous posts — topic is unique")
        return False, 0.0, ""

    # Embed the new story
    new_text = _build_topic_text(story)
    print(f"  [Dedup] Embedding new story: '{story.get('headline', '?')[:60]}...'")
    new_embedding = _get_embedding(new_text)

    # Compare against all stored embeddings
    max_sim = 0.0
    matched_topic = ""

    for entry in stored_embeddings:
        stored_vec = entry.get("vector", [])
        stored_topic = entry.get("topic", "?")

        if not stored_vec:
            continue

        sim = _cosine_similarity(new_embedding, stored_vec)

        if sim > max_sim:
            max_sim = sim
            matched_topic = stored_topic

        print(f"    vs '{stored_topic[:50]}...' → {sim:.1%}")

    is_dup = max_sim >= SIMILARITY_THRESHOLD

    if is_dup:
        print(f"  [Dedup] DUPLICATE DETECTED: {max_sim:.1%} match with '{matched_topic}'")
        print(f"  [Dedup] Threshold: {SIMILARITY_THRESHOLD:.0%} — BLOCKING this topic")
    else:
        print(f"  [Dedup] UNIQUE: max similarity {max_sim:.1%} (threshold {SIMILARITY_THRESHOLD:.0%})")

    return is_dup, max_sim, matched_topic


def store_embedding(story: dict, post_id: str = ""):
    """Store the embedding for a newly posted story.

    Call this AFTER a successful LinkedIn post.
    """
    log = load_post_log()

    text = _build_topic_text(story)
    embedding = _get_embedding(text)

    if "embeddings" not in log:
        log["embeddings"] = []

    log["embeddings"].append({
        "topic": story.get("headline", "?"),
        "summary": story.get("summary", "")[:200],
        "post_id": post_id,
        "vector": embedding,
    })

    save_post_log(log)
    print(f"  [Dedup] Stored embedding for '{story.get('headline', '?')[:50]}...'")


def backfill_embeddings():
    """Backfill embeddings for existing posts that don't have them yet.

    Run this once to populate embeddings for historical posts.
    """
    log = load_post_log()
    existing = log.get("embeddings", [])
    existing_topics = {e.get("topic", "") for e in existing}

    posts = log.get("posts", [])
    added = 0

    for post in posts:
        topic = post.get("topic", "")
        if topic and topic not in existing_topics:
            # Build a minimal story dict from the post log
            story = {
                "headline": topic,
                "summary": post.get("brief_title", ""),
                "impact_areas": [],
                "source": "",
                "key_quote": "",
            }
            text = _build_topic_text(story)
            embedding = _get_embedding(text)

            if "embeddings" not in log:
                log["embeddings"] = []

            log["embeddings"].append({
                "topic": topic,
                "summary": post.get("brief_title", ""),
                "post_id": post.get("post_id", ""),
                "vector": embedding,
            })
            existing_topics.add(topic)
            added += 1
            print(f"  [Dedup] Backfilled: '{topic[:50]}...'")

    if added:
        save_post_log(log)
        print(f"  [Dedup] Backfilled {added} embeddings")
    else:
        print(f"  [Dedup] All posts already have embeddings")
