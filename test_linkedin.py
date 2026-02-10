"""Standalone test: Generate LinkedIn post copy + upload existing Short Selling video."""
import json
from agents.linkedin_strategist import LinkedInStrategist
from pipeline.linkedin_post import post_video_to_linkedin
from pipeline.upload_tracker import log_upload

# --- Config ---
VIDEO_PATH = r"C:\Users\conta\OneDrive\Projects\catfun\output\FinanceCats_Short_Selling.mp4"
TERM = "Short Selling"
YOUTUBE_URL = "https://www.youtube.com/watch?v=xzFa8_rvTa8"

# --- Step 1: Generate LinkedIn post copy using the agent ---
print("=" * 60)
print("  STEP 1: LinkedIn Strategist — Generating Post Copy")
print("=" * 60)

strategist = LinkedInStrategist()
li_package = strategist.create_post(
    term=TERM,
    script_summary=(
        "Professor Whiskers and Cleo discuss short selling — what it is, "
        "how it works, the risks involved, and famous examples like the "
        "GameStop short squeeze. Simple explanations with real-life analogies."
    ),
    youtube_url=YOUTUBE_URL,
)

print("\n--- LinkedIn Package ---")
print(json.dumps(li_package, indent=2, ensure_ascii=False))

post_text = li_package.get("post_text", "")
hashtags = li_package.get("hashtags", [])

# Append hashtags to post text if not already included
if hashtags and not any(f"#{h}" in post_text for h in hashtags):
    hashtag_str = " ".join(f"#{h}" for h in hashtags)
    post_text = f"{post_text}\n\n{hashtag_str}"

print("\n--- Final Post Text ---")
print(post_text)
print("-" * 40)

# --- Step 2: Upload video + create post ---
print("\n" + "=" * 60)
print("  STEP 2: Uploading Video to LinkedIn")
print("=" * 60)

try:
    result = post_video_to_linkedin(
        video_path=VIDEO_PATH,
        commentary=post_text,
        video_title=f"What is {TERM}? | FinanceCats",
    )
    print("\n--- Upload Result ---")
    print(json.dumps(result, indent=2))

    # Log to upload tracker
    log_upload(
        term=TERM,
        title=f"What is {TERM}? | FinanceCats",
        video_path=VIDEO_PATH,
        status="success" if result.get("status") == "success" else "failed",
        error_message=result.get("error", ""),
        tags=hashtags,
        description=post_text[:200],
        # LinkedIn-specific fields reused in generic tracker
        youtube_video_id=result.get("post_id", ""),
        youtube_url=result.get("post_url", ""),
        news_source="LinkedIn",
        episode_number=5,
        series_id=1,
    )

except Exception as e:
    print(f"\n  ERROR: {e}")
    import traceback
    traceback.print_exc()

    log_upload(
        term=TERM,
        title=f"What is {TERM}? | FinanceCats",
        video_path=VIDEO_PATH,
        status="failed",
        error_message=str(e),
        news_source="LinkedIn",
    )

print("\nDone!")
