"""Test semantic dedup — verify matching works correctly."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from aibrief.pipeline.dedup import is_duplicate

# Test 1: Should be DUPLICATE (same topic, different wording)
print("=== TEST 1: Claude-4 (should be DUPLICATE) ===")
dup1, sim1, match1 = is_duplicate({
    "headline": "Anthropic releases Claude 4 with improved reasoning",
    "summary": "New AI model from Anthropic with better safety features",
    "impact_areas": ["AI", "Enterprise"],
    "source": "Anthropic",
    "key_quote": "A leap in AI reasoning",
})
print(f"Result: dup={dup1}, sim={sim1:.1%}, match={match1}\n")

# Test 2: Should be UNIQUE (completely different topic)
print("=== TEST 2: Google Quantum (should be UNIQUE) ===")
dup2, sim2, match2 = is_duplicate({
    "headline": "Google achieves quantum computing breakthrough with 1000 qubits",
    "summary": "Google Willow chip reaches 1000 logical qubits milestone",
    "impact_areas": ["Quantum Computing", "Cryptography"],
    "source": "Google DeepMind",
    "key_quote": "This changes everything about computational limits",
})
print(f"Result: dup={dup2}, sim={sim2:.1%}, match={match2}\n")

# Test 3: Edge case — OpenAI but different product
print("=== TEST 3: OpenAI GPT-7 (borderline) ===")
dup3, sim3, match3 = is_duplicate({
    "headline": "OpenAI launches GPT-7 with multimodal capabilities",
    "summary": "GPT-7 can process video audio and text simultaneously",
    "impact_areas": ["AI Models", "Multimodal AI"],
    "source": "OpenAI",
    "key_quote": "The most capable model ever built",
})
print(f"Result: dup={dup3}, sim={sim3:.1%}, match={match3}")
