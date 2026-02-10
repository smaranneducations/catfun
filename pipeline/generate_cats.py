"""Generate the 30-cat repository using DALL-E.

Run this script once to populate assets/cats/repository/ with 30 professional cat images.
Each cat is unique (different breed/colour) but all wear professional attire.

Usage:
    python -m pipeline.generate_cats
    python -m pipeline.generate_cats --count 5   # Generate only 5 (for testing)
"""
import os
import sys
import time
import requests
from openai import OpenAI
import config


# Cat variations — different breeds, colours, and accessories
CAT_PROFILES = [
    {"breed": "Orange tabby", "accessory": "round gold reading glasses and a navy bow tie"},
    {"breed": "Black tuxedo cat", "accessory": "silver monocle and a tiny top hat"},
    {"breed": "White Persian", "accessory": "tortoiseshell glasses and a red bow tie"},
    {"breed": "Grey British Shorthair", "accessory": "wire-rimmed spectacles and a tweed flat cap"},
    {"breed": "Siamese", "accessory": "rectangular black glasses and a striped tie"},
    {"breed": "Calico", "accessory": "round rose-gold glasses and a pearl necklace"},
    {"breed": "Russian Blue", "accessory": "gold-framed aviator glasses and a fedora hat"},
    {"breed": "Maine Coon", "accessory": "thick-framed hipster glasses and a plaid scarf"},
    {"breed": "Bengal", "accessory": "sleek titanium glasses and a leather watch"},
    {"breed": "Ragdoll", "accessory": "pink cat-eye glasses and a silk bow"},
    {"breed": "Scottish Fold", "accessory": "round brass glasses and a newsboy cap"},
    {"breed": "Abyssinian", "accessory": "thin gold glasses and a burgundy cravat"},
    {"breed": "Norwegian Forest Cat", "accessory": "wooden-framed glasses and a knitted beanie"},
    {"breed": "Sphynx", "accessory": "oversized black glasses and a turtleneck sweater"},
    {"breed": "Birman", "accessory": "delicate silver glasses and a velvet bow tie"},
    {"breed": "American Shorthair (silver tabby)", "accessory": "square black glasses and suspenders"},
    {"breed": "Bombay (all black)", "accessory": "gold pince-nez and a white pocket square"},
    {"breed": "Chartreux", "accessory": "blue-tinted glasses and a beret"},
    {"breed": "Exotic Shorthair", "accessory": "round tortoiseshell glasses and a polka dot tie"},
    {"breed": "Turkish Angora (white)", "accessory": "diamond-studded glasses and a silk scarf"},
    {"breed": "Himalayan", "accessory": "half-moon reading glasses and a cardigan"},
    {"breed": "Cornish Rex", "accessory": "futuristic wrap-around glasses and a collar pin"},
    {"breed": "Devon Rex", "accessory": "tiny oval glasses and a bow tie with stars"},
    {"breed": "Manx (tailless ginger)", "accessory": "round John Lennon glasses and a waistcoat"},
    {"breed": "Burmese", "accessory": "cat-eye glasses with gems and a pearl choker"},
    {"breed": "Ocicat", "accessory": "sport glasses and a digital watch"},
    {"breed": "Tonkinese", "accessory": "classic wayfarers and a rolled-up sleeve look"},
    {"breed": "Egyptian Mau", "accessory": "pharaoh-style gold frames and an ankh pendant"},
    {"breed": "Snowshoe", "accessory": "half-frame reading glasses and a graduation cap"},
    {"breed": "Korat", "accessory": "minimalist silver glasses and a silk pocket square"},
]


def generate_cat_image(profile: dict, index: int) -> str:
    """Generate a single cat image using DALL-E 3."""
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    prompt = (
        f"A professional studio portrait photograph of a {profile['breed']} cat "
        f"wearing {profile['accessory']}. The cat is sitting upright on a chair "
        f"in a dignified, professor-like pose. The cat looks intelligent and "
        f"authoritative, as if about to give a lecture. Clean white studio background. "
        f"High quality, sharp focus, professional lighting. The cat takes up about "
        f"70% of the frame. Photorealistic style, not cartoon or illustration."
    )

    print(f"  Generating cat {index + 1}/30: {profile['breed']}...")

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url

        # Download the image
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            filename = f"cat_{index + 1:02d}_{profile['breed'].lower().replace(' ', '_')[:20]}.png"
            filepath = os.path.join(config.CATS_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(img_response.content)

            print(f"    Saved: {filename}")
            return filepath
        else:
            print(f"    Failed to download image: {img_response.status_code}")
            return ""

    except Exception as e:
        print(f"    Error generating cat {index + 1}: {e}")
        return ""


def generate_all_cats(count: int = 30):
    """Generate the full cat repository."""
    os.makedirs(config.CATS_DIR, exist_ok=True)

    # Check how many already exist
    existing = [
        f for f in os.listdir(config.CATS_DIR)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    ]
    print(f"\n=== CAT REPOSITORY GENERATION ===")
    print(f"  Target: {count} cats")
    print(f"  Already have: {len(existing)}")
    print(f"  Estimated cost: ~${count * 0.04:.2f} (DALL-E 3 standard)\n")

    if len(existing) >= count:
        print(f"  Repository already has {len(existing)} cats. Skipping generation.")
        return

    # Generate missing cats
    profiles = CAT_PROFILES[:count]
    generated = 0
    failed = 0

    for i, profile in enumerate(profiles):
        # Skip if a cat with this index already exists
        prefix = f"cat_{i + 1:02d}_"
        if any(f.startswith(prefix) for f in existing):
            print(f"  Cat {i + 1} already exists, skipping.")
            continue

        result = generate_cat_image(profile, i)
        if result:
            generated += 1
        else:
            failed += 1

        # Rate limiting — DALL-E has limits
        if i < len(profiles) - 1:
            time.sleep(2)

    print(f"\n  Generation complete!")
    print(f"  Generated: {generated}")
    print(f"  Failed: {failed}")
    print(f"  Total in repository: {len(existing) + generated}")


if __name__ == "__main__":
    count = 30
    if len(sys.argv) > 2 and sys.argv[1] == "--count":
        count = int(sys.argv[2])
    generate_all_cats(count)
