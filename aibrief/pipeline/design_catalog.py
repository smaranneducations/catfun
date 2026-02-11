"""Design Catalog — Emotion-driven, hardcoded design system.

The LLM's ONLY job is to detect the dominant EMOTION of the news story.
Everything else (style, palette, font, image keywords) is HARDCODED here.

Flow:
  1. DesignDNA agent reads the story → returns ONE emotion word
  2. This module maps emotion → style + palette + font + image keywords
  3. Imagen prompt is constructed: hardcoded theme info + dynamic topic

This eliminates the LLM's tendency to always pick the same style.
"""
import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ═══════════════════════════════════════════════════════════════
#  EMOTION → DESIGN MAPPING (the core of the system)
# ═══════════════════════════════════════════════════════════════

EMOTION_DESIGN_MAP = {
    "trust": {
        "style_id": "luxury_minimalist",
        "palette_id": "ivory_charcoal",
        "font_id": "palatino",
        "imagen_style": "corporate minimal, professional, clean",
        "design_name": "Professional Trust",
        "mood": "corporate authority, trustworthy, polished",
        "bg_motifs": "subtle grid lines, clean geometric shapes, light marble texture",
        "fg_mood": "professional, corporate, authoritative, clean composition",
    },
    "excitement": {
        "style_id": "anime_pop",
        "palette_id": "electric_indigo",
        "font_id": "impact",
        "imagen_style": "anime, vibrant, dynamic",
        "design_name": "Electric Excitement",
        "mood": "vibrant energy, dynamic motion, bold celebration",
        "bg_motifs": "dynamic speed lines, sticker-like silhouettes, energetic shapes",
        "fg_mood": "vibrant, energetic, bold, dynamic composition, exciting",
    },
    "calm": {
        "style_id": "nordic_clean",
        "palette_id": "arctic_steel",
        "font_id": "calibri",
        "imagen_style": "minimalist, zen, soft pastel",
        "design_name": "Serene Clarity",
        "mood": "peaceful clarity, zen calm, natural warmth",
        "bg_motifs": "soft gradients, gentle circles, nature-inspired organic shapes",
        "fg_mood": "peaceful, calm, minimalist, nature-inspired, soft lighting",
    },
    "urgency": {
        "style_id": "swiss_international",
        "palette_id": "crimson_noir",
        "font_id": "segoe",
        "imagen_style": "breaking news, editorial, high-contrast",
        "design_name": "Breaking Signal",
        "mood": "urgent importance, breaking news gravity, immediate impact",
        "bg_motifs": "bold grid elements, sharp lines, signal dots, news-wire aesthetic",
        "fg_mood": "urgent, dramatic, high-contrast, editorial, impactful",
    },
    "fear": {
        "style_id": "gothic_editorial",
        "palette_id": "obsidian_chrome",
        "font_id": "times_nr",
        "imagen_style": "caution, hazard, tense",
        "design_name": "Dark Caution",
        "mood": "careful vigilance, serious warning, measured concern",
        "bg_motifs": "faint hazard patterns, angular shapes, subtle warning geometry",
        "fg_mood": "cautious, tense, dramatic shadows, serious, moody",
    },
    "anger": {
        "style_id": "heavy_metal",
        "palette_id": "crimson_noir",
        "font_id": "arial_black",
        "imagen_style": "protest, gritty editorial, harsh contrast",
        "design_name": "Raw Fury",
        "mood": "righteous intensity, fierce conviction, raw power",
        "bg_motifs": "distressed textures, angular shards, protest-art energy",
        "fg_mood": "gritty, harsh contrast, protest art, powerful, intense",
    },
    "sadness": {
        "style_id": "french_haute_couture",
        "palette_id": "rose_quartz",
        "font_id": "georgia",
        "imagen_style": "somber, memorial, muted monochrome",
        "design_name": "Quiet Remembrance",
        "mood": "solemn dignity, memorial grace, empathetic depth",
        "bg_motifs": "soft fading patterns, gentle monochrome gradients, memorial motifs",
        "fg_mood": "somber, memorial, muted, monochrome, dignified, respectful",
    },
    "hope": {
        "style_id": "african_futurism",
        "palette_id": "emerald_twilight",
        "font_id": "trebuchet",
        "imagen_style": "uplifting, optimistic, sunrise",
        "design_name": "Dawn Rising",
        "mood": "bright possibility, new beginnings, forward momentum",
        "bg_motifs": "sunrise gradients, upward-flowing shapes, growth motifs",
        "fg_mood": "uplifting, optimistic, sunrise colors, hopeful, bright future",
    },
    "mystery": {
        "style_id": "gothic_editorial",
        "palette_id": "midnight_gold",
        "font_id": "times_nr",
        "imagen_style": "gothic, medieval, ornate, moody",
        "design_name": "Gilded Shadow",
        "mood": "dark intrigue, hidden depth, intellectual gravity",
        "bg_motifs": "ornate gothic patterns, cathedral arches, mysterious shadows",
        "fg_mood": "gothic, moody, medieval atmosphere, ornate, mysterious",
    },
    "rebellion": {
        "style_id": "heavy_metal",
        "palette_id": "obsidian_chrome",
        "font_id": "arial_black",
        "imagen_style": "heavy metal, distressed, metallic",
        "design_name": "Chrome Defiance",
        "mood": "defiant energy, counter-culture power, metallic strength",
        "bg_motifs": "metallic textures, chrome reflections, distressed industrial patterns",
        "fg_mood": "heavy metal aesthetic, distressed, chrome, powerful, rebellious",
    },
}

# All valid emotions for prompt
VALID_EMOTIONS = list(EMOTION_DESIGN_MAP.keys())

# Default fallback
DEFAULT_EMOTION = "trust"


def resolve_design(emotion: str) -> dict:
    """Given an emotion string, return the full hardcoded design config.

    Returns a dict with: style_id, palette_id, font_id, imagen_style,
    design_name, mood, bg_motifs, fg_mood.
    """
    emotion = emotion.lower().strip()
    # Fuzzy match: find the closest emotion
    if emotion not in EMOTION_DESIGN_MAP:
        # Try partial match
        for key in EMOTION_DESIGN_MAP:
            if key in emotion or emotion in key:
                emotion = key
                break
        else:
            # Map common synonyms
            synonyms = {
                "joy": "excitement", "happy": "excitement", "elation": "excitement",
                "anxious": "fear", "anxiety": "fear", "worry": "fear",
                "risk": "fear", "concern": "fear",
                "peaceful": "calm", "serene": "calm", "tranquil": "calm",
                "confident": "trust", "professional": "trust", "stable": "trust",
                "hopeful": "hope", "optimistic": "hope", "anticipation": "hope",
                "curious": "mystery", "intrigue": "mystery", "dark": "mystery",
                "grief": "sadness", "sorrow": "sadness", "mourning": "sadness",
                "rage": "anger", "conflict": "anger", "outrage": "anger",
                "urgent": "urgency", "breaking": "urgency", "critical": "urgency",
                "defiant": "rebellion", "rebellious": "rebellion", "disruptive": "rebellion",
                "excited": "excitement", "thrilling": "excitement",
            }
            emotion = synonyms.get(emotion, DEFAULT_EMOTION)

    return EMOTION_DESIGN_MAP.get(emotion, EMOTION_DESIGN_MAP[DEFAULT_EMOTION])


# ═══════════════════════════════════════════════════════════════
#  STYLES (kept for poster_gen.py decorations)
# ═══════════════════════════════════════════════════════════════

STYLES = [
    {"id": "anime_pop", "name": "Anime Pop",
     "description": "Bold, vibrant, manga-inspired with dynamic energy"},
    {"id": "indian_classical", "name": "Indian Classical",
     "description": "Rich, ornate, Mughal miniatures with gold filigree"},
    {"id": "luxury_minimalist", "name": "Luxury Minimalist",
     "description": "Hermès meets Apple — extreme restraint, negative space"},
    {"id": "gothic_editorial", "name": "Gothic Editorial",
     "description": "Dark cathedral grandeur — pointed arches, medieval gravitas"},
    {"id": "heavy_metal", "name": "Heavy Metal",
     "description": "Raw power — chrome, fire, distressed textures"},
    {"id": "art_deco", "name": "Art Deco",
     "description": "1920s Gatsby glamour — geometric gold, symmetrical"},
    {"id": "swiss_international", "name": "Swiss International",
     "description": "Grid-based, rational, Helvetica-driven clarity"},
    {"id": "african_futurism", "name": "African Futurism",
     "description": "Wakanda-inspired — bold geometric, earth meets chrome"},
    {"id": "french_haute_couture", "name": "French Haute Couture",
     "description": "Chanel, Dior — understated Parisian elegance"},
    {"id": "cyberpunk_noir", "name": "Cyberpunk Noir",
     "description": "Blade Runner noir — neon on dark, synthwave"},
    {"id": "ancient_greek", "name": "Ancient Greek",
     "description": "Classical antiquity — marble, Doric columns"},
    {"id": "nordic_clean", "name": "Nordic Clean",
     "description": "Scandinavian — pale wood, warm light, hygge"},
]

# ═══════════════════════════════════════════════════════════════
#  COLOR PALETTES
# ═══════════════════════════════════════════════════════════════

COLOR_PALETTES = [
    {"id": "midnight_gold", "name": "Midnight Gold",
     "primary": "#0a0f1a", "secondary": "#1a2744", "accent": "#d4a843",
     "background": "#0f1520", "text": "#e8e2d4", "heading": "#d4a843"},
    {"id": "crimson_noir", "name": "Crimson Noir",
     "primary": "#1a0a0a", "secondary": "#3d0c0c", "accent": "#c41e3a",
     "background": "#120808", "text": "#e8dcd0", "heading": "#c41e3a"},
    {"id": "emerald_twilight", "name": "Emerald Twilight",
     "primary": "#0a1a12", "secondary": "#1a3d2a", "accent": "#2ecc71",
     "background": "#0d1710", "text": "#d4e8dc", "heading": "#2ecc71"},
    {"id": "ivory_charcoal", "name": "Ivory Charcoal",
     "primary": "#2d2d2d", "secondary": "#4a4a4a", "accent": "#c8a84e",
     "background": "#f5f0e6", "text": "#2d2d2d", "heading": "#1a1a1a"},
    {"id": "electric_indigo", "name": "Electric Indigo",
     "primary": "#1a0a3e", "secondary": "#2d1b69", "accent": "#7c4dff",
     "background": "#0e0625", "text": "#d4cce8", "heading": "#b388ff"},
    {"id": "terracotta_sage", "name": "Terracotta Sage",
     "primary": "#3d2b1f", "secondary": "#5c3d2e", "accent": "#c07850",
     "background": "#2a1f16", "text": "#e8dcc8", "heading": "#c07850"},
    {"id": "arctic_steel", "name": "Arctic Steel",
     "primary": "#1a2530", "secondary": "#2d3e4f", "accent": "#4fc3f7",
     "background": "#121c24", "text": "#c8dce8", "heading": "#4fc3f7"},
    {"id": "rose_quartz", "name": "Rose Quartz",
     "primary": "#2d1a28", "secondary": "#4a2d42", "accent": "#e91e63",
     "background": "#1f1018", "text": "#e8d0dc", "heading": "#f48fb1"},
    {"id": "obsidian_chrome", "name": "Obsidian Chrome",
     "primary": "#0a0a0a", "secondary": "#1a1a1a", "accent": "#c0c0c0",
     "background": "#050505", "text": "#b0b0b0", "heading": "#e0e0e0"},
    {"id": "saffron_dynasty", "name": "Saffron Dynasty",
     "primary": "#1a1008", "secondary": "#3d2810", "accent": "#ff9800",
     "background": "#140c04", "text": "#e8d4b8", "heading": "#ffb74d"},
]


# ═══════════════════════════════════════════════════════════════
#  10 FONT CONFIGURATIONS (Windows TTF + ReportLab fallbacks)
# ═══════════════════════════════════════════════════════════════

_WINFONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

FONTS = [
    {"id": "georgia", "name": "Georgia",
     "style_desc": "Warm, elegant serif with calligraphic touches",
     "ttf": os.path.join(_WINFONTS, "georgia.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "georgiab.ttf"),
     "reg": "Georgia", "reg_bold": "Georgia-Bold",
     "fallback": "Times-Roman", "fallback_bold": "Times-Bold"},
    {"id": "palatino", "name": "Palatino Linotype",
     "style_desc": "Classical calligraphic warmth, Renaissance-inspired",
     "ttf": os.path.join(_WINFONTS, "pala.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "palab.ttf"),
     "reg": "PalatinoLT", "reg_bold": "PalatinoLT-Bold",
     "fallback": "Times-Roman", "fallback_bold": "Times-Bold"},
    {"id": "times_nr", "name": "Times New Roman",
     "style_desc": "Classic newspaper authority, traditional gravitas",
     "ttf": os.path.join(_WINFONTS, "times.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "timesbd.ttf"),
     "reg": "TimesNR", "reg_bold": "TimesNR-Bold",
     "fallback": "Times-Roman", "fallback_bold": "Times-Bold"},
    {"id": "trebuchet", "name": "Trebuchet MS",
     "style_desc": "Humanist sans-serif, friendly yet professional",
     "ttf": os.path.join(_WINFONTS, "trebuc.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "trebucbd.ttf"),
     "reg": "Trebuchet", "reg_bold": "Trebuchet-Bold",
     "fallback": "Helvetica", "fallback_bold": "Helvetica-Bold"},
    {"id": "segoe", "name": "Segoe UI",
     "style_desc": "Clean modern tech-company aesthetic",
     "ttf": os.path.join(_WINFONTS, "segoeui.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "segoeuib.ttf"),
     "reg": "SegoeUI", "reg_bold": "SegoeUI-Bold",
     "fallback": "Helvetica", "fallback_bold": "Helvetica-Bold"},
    {"id": "impact", "name": "Impact",
     "style_desc": "Ultra-bold condensed, maximum visual punch",
     "ttf": os.path.join(_WINFONTS, "impact.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "impact.ttf"),
     "reg": "ImpactFont", "reg_bold": "ImpactFont",
     "fallback": "Helvetica-Bold", "fallback_bold": "Helvetica-Bold"},
    {"id": "verdana", "name": "Verdana",
     "style_desc": "Wide, clear, screen-optimized readability",
     "ttf": os.path.join(_WINFONTS, "verdana.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "verdanab.ttf"),
     "reg": "Verdana", "reg_bold": "Verdana-Bold",
     "fallback": "Helvetica", "fallback_bold": "Helvetica-Bold"},
    {"id": "calibri", "name": "Calibri",
     "style_desc": "Modern warmth, humanist sans, Microsoft flagship",
     "ttf": os.path.join(_WINFONTS, "calibri.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "calibrib.ttf"),
     "reg": "Calibri", "reg_bold": "Calibri-Bold",
     "fallback": "Helvetica", "fallback_bold": "Helvetica-Bold"},
    {"id": "consolas", "name": "Consolas",
     "style_desc": "Monospaced tech, code-inspired modernity",
     "ttf": os.path.join(_WINFONTS, "consola.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "consolab.ttf"),
     "reg": "Consolas", "reg_bold": "Consolas-Bold",
     "fallback": "Courier", "fallback_bold": "Courier-Bold"},
    {"id": "arial_black", "name": "Arial Black",
     "style_desc": "Heavy grotesque, bold industrial presence",
     "ttf": os.path.join(_WINFONTS, "ariblk.ttf"),
     "ttf_bold": os.path.join(_WINFONTS, "ariblk.ttf"),
     "reg": "ArialBlack", "reg_bold": "ArialBlack",
     "fallback": "Helvetica-Bold", "fallback_bold": "Helvetica-Bold"},
]


# ═══════════════════════════════════════════════════════════════
#  FONT REGISTRATION
# ═══════════════════════════════════════════════════════════════

_registered: set[str] = set()


def register_font(font_id: str) -> tuple[str, str]:
    """Register a font pair with ReportLab. Returns (regular_name, bold_name)."""
    cfg = next((f for f in FONTS if f["id"] == font_id), FONTS[0])
    reg, reg_b = cfg["reg"], cfg["reg_bold"]
    if reg in _registered:
        return reg, reg_b
    try:
        ttf, ttf_b = cfg["ttf"], cfg["ttf_bold"]
        if Path(ttf).exists():
            pdfmetrics.registerFont(TTFont(reg, ttf))
            if Path(ttf_b).exists() and ttf_b != ttf:
                pdfmetrics.registerFont(TTFont(reg_b, ttf_b))
            else:
                reg_b = reg
            _registered.add(reg)
            print(f"  [Font] Registered: {cfg['name']}")
            return reg, reg_b
    except Exception as e:
        print(f"  [Font] Could not register {cfg['name']}: {e}")
    _registered.add(reg)
    fb, fb_b = cfg["fallback"], cfg["fallback_bold"]
    print(f"  [Font] Using fallback: {fb}")
    return fb, fb_b


def lookup_style(style_id: str) -> dict:
    return next((s for s in STYLES if s["id"] == style_id), STYLES[0])

def lookup_palette(palette_id: str) -> dict:
    return next((p for p in COLOR_PALETTES if p["id"] == palette_id),
                COLOR_PALETTES[0])

