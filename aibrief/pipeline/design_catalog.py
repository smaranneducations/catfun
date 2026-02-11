"""Design Catalog — Curated styles, fonts, and color palettes.

The DesignDNA agent MUST pick from these catalogs based on content context.
This ensures:
  1. FORCED variety (12 styles, 10 fonts, 10 palettes — always different)
  2. Quality control (every option is pre-vetted for luxury quality)
  3. Technical reliability (fonts fallback to ReportLab built-ins)

The LLM selects one style_id, one palette_id, one font_id based on the
topic, world sentiment, and content type.
"""
import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ═══════════════════════════════════════════════════════════════
#  12 VISUAL STYLES
# ═══════════════════════════════════════════════════════════════

STYLES = [
    {
        "id": "anime_pop",
        "name": "Anime Pop",
        "description": "Bold, vibrant, manga-inspired with dynamic energy and flat color blocks",
        "dall_e_hint": "anime style, bold cel-shading, dynamic composition, vibrant saturated colors",
    },
    {
        "id": "indian_classical",
        "name": "Indian Classical",
        "description": "Rich, ornate, Mughal miniatures with gold filigree and sacred geometry",
        "dall_e_hint": "Indian classical art, Mughal miniature style, gold filigree, mandala, ornate",
    },
    {
        "id": "luxury_minimalist",
        "name": "Luxury Minimalist",
        "description": "Hermès meets Apple — extreme restraint, tactile materials, negative space",
        "dall_e_hint": "luxury minimalist, clean lines, premium materials, marble and gold, negative space",
    },
    {
        "id": "gothic_editorial",
        "name": "Gothic Editorial",
        "description": "Dark cathedral grandeur — pointed arches, stained glass, medieval gravitas",
        "dall_e_hint": "gothic editorial, dark dramatic, cathedral arches, stained glass, medieval grandeur",
    },
    {
        "id": "heavy_metal",
        "name": "Heavy Metal",
        "description": "Raw power — chrome, fire, distressed textures, industrial grit, album art",
        "dall_e_hint": "heavy metal album art, chrome textures, fire and smoke, industrial, powerful",
    },
    {
        "id": "art_deco",
        "name": "Art Deco",
        "description": "1920s Gatsby glamour — geometric gold, symmetrical, Jazz Age opulence",
        "dall_e_hint": "art deco, geometric gold patterns, 1920s glamour, symmetrical, Gatsby opulence",
    },
    {
        "id": "swiss_international",
        "name": "Swiss International",
        "description": "Grid-based, rational, Helvetica-driven clarity — Bauhaus adjacent",
        "dall_e_hint": "Swiss design, clean grid, Bauhaus, rational modernism, Helvetica aesthetic",
    },
    {
        "id": "african_futurism",
        "name": "African Futurism",
        "description": "Wakanda-inspired — bold geometric patterns, earth meets chrome, ancestral tech",
        "dall_e_hint": "Afrofuturism, bold tribal geometry, earth tones with chrome, ancestral technology",
    },
    {
        "id": "french_haute_couture",
        "name": "French Haute Couture",
        "description": "Chanel, Dior, Givenchy — understated Parisian elegance, ivory and charcoal",
        "dall_e_hint": "French haute couture, Parisian elegance, ivory, charcoal, subtle gold, refined",
    },
    {
        "id": "cyberpunk_noir",
        "name": "Cyberpunk Noir",
        "description": "Blade Runner noir — neon on dark, rain-soaked, synthwave, digital dystopia",
        "dall_e_hint": "cyberpunk noir, neon lights, dark rain, synthwave, Blade Runner, digital",
    },
    {
        "id": "ancient_greek",
        "name": "Ancient Greek",
        "description": "Classical antiquity — marble, Doric columns, terracotta, philosophical gravitas",
        "dall_e_hint": "ancient Greek classical, marble texture, Doric columns, terracotta, philosophical",
    },
    {
        "id": "nordic_clean",
        "name": "Nordic Clean",
        "description": "Scandinavian — pale wood, warm light, hygge, functional beauty, nature",
        "dall_e_hint": "Nordic Scandinavian design, pale birch wood, warm light, minimalist, nature",
    },
]

# ═══════════════════════════════════════════════════════════════
#  10 COLOR PALETTES
# ═══════════════════════════════════════════════════════════════

COLOR_PALETTES = [
    {
        "id": "midnight_gold", "name": "Midnight Gold",
        "primary": "#0a0f1a", "secondary": "#1a2744", "accent": "#d4a843",
        "background": "#0f1520", "text": "#e8e2d4", "heading": "#d4a843",
        "mood": "Opulent night, luxury authority",
    },
    {
        "id": "crimson_noir", "name": "Crimson Noir",
        "primary": "#1a0a0a", "secondary": "#3d0c0c", "accent": "#c41e3a",
        "background": "#120808", "text": "#e8dcd0", "heading": "#c41e3a",
        "mood": "Dramatic power, bold statement",
    },
    {
        "id": "emerald_twilight", "name": "Emerald Twilight",
        "primary": "#0a1a12", "secondary": "#1a3d2a", "accent": "#2ecc71",
        "background": "#0d1710", "text": "#d4e8dc", "heading": "#2ecc71",
        "mood": "Growth, vitality, optimistic future",
    },
    {
        "id": "ivory_charcoal", "name": "Ivory Charcoal",
        "primary": "#2d2d2d", "secondary": "#4a4a4a", "accent": "#c8a84e",
        "background": "#f5f0e6", "text": "#2d2d2d", "heading": "#1a1a1a",
        "mood": "Classic Parisian, understated elegance",
    },
    {
        "id": "electric_indigo", "name": "Electric Indigo",
        "primary": "#1a0a3e", "secondary": "#2d1b69", "accent": "#7c4dff",
        "background": "#0e0625", "text": "#d4cce8", "heading": "#b388ff",
        "mood": "Tech-forward innovation, futuristic",
    },
    {
        "id": "terracotta_sage", "name": "Terracotta Sage",
        "primary": "#3d2b1f", "secondary": "#5c3d2e", "accent": "#c07850",
        "background": "#2a1f16", "text": "#e8dcc8", "heading": "#c07850",
        "mood": "Earthy wisdom, grounded warmth",
    },
    {
        "id": "arctic_steel", "name": "Arctic Steel",
        "primary": "#1a2530", "secondary": "#2d3e4f", "accent": "#4fc3f7",
        "background": "#121c24", "text": "#c8dce8", "heading": "#4fc3f7",
        "mood": "Scandinavian clarity, cool precision",
    },
    {
        "id": "rose_quartz", "name": "Rose Quartz",
        "primary": "#2d1a28", "secondary": "#4a2d42", "accent": "#e91e63",
        "background": "#1f1018", "text": "#e8d0dc", "heading": "#f48fb1",
        "mood": "Warm empathy, human-centered",
    },
    {
        "id": "obsidian_chrome", "name": "Obsidian Chrome",
        "primary": "#0a0a0a", "secondary": "#1a1a1a", "accent": "#c0c0c0",
        "background": "#050505", "text": "#b0b0b0", "heading": "#e0e0e0",
        "mood": "Industrial power, heavy metal edge",
    },
    {
        "id": "saffron_dynasty", "name": "Saffron Dynasty",
        "primary": "#1a1008", "secondary": "#3d2810", "accent": "#ff9800",
        "background": "#140c04", "text": "#e8d4b8", "heading": "#ffb74d",
        "mood": "Royal heritage, warm regal tones",
    },
]

# ═══════════════════════════════════════════════════════════════
#  10 FONT CONFIGURATIONS (Windows TTF + ReportLab fallbacks)
# ═══════════════════════════════════════════════════════════════

_WINFONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

FONTS = [
    {
        "id": "georgia", "name": "Georgia",
        "style_desc": "Warm, elegant serif with calligraphic touches",
        "ttf": os.path.join(_WINFONTS, "georgia.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "georgiab.ttf"),
        "reg": "Georgia", "reg_bold": "Georgia-Bold",
        "fallback": "Times-Roman", "fallback_bold": "Times-Bold",
    },
    {
        "id": "palatino", "name": "Palatino Linotype",
        "style_desc": "Classical calligraphic warmth, Renaissance-inspired",
        "ttf": os.path.join(_WINFONTS, "pala.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "palab.ttf"),
        "reg": "PalatinoLT", "reg_bold": "PalatinoLT-Bold",
        "fallback": "Times-Roman", "fallback_bold": "Times-Bold",
    },
    {
        "id": "times_nr", "name": "Times New Roman",
        "style_desc": "Classic newspaper authority, traditional gravitas",
        "ttf": os.path.join(_WINFONTS, "times.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "timesbd.ttf"),
        "reg": "TimesNR", "reg_bold": "TimesNR-Bold",
        "fallback": "Times-Roman", "fallback_bold": "Times-Bold",
    },
    {
        "id": "trebuchet", "name": "Trebuchet MS",
        "style_desc": "Humanist sans-serif, friendly yet professional",
        "ttf": os.path.join(_WINFONTS, "trebuc.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "trebucbd.ttf"),
        "reg": "Trebuchet", "reg_bold": "Trebuchet-Bold",
        "fallback": "Helvetica", "fallback_bold": "Helvetica-Bold",
    },
    {
        "id": "segoe", "name": "Segoe UI",
        "style_desc": "Clean modern tech-company aesthetic",
        "ttf": os.path.join(_WINFONTS, "segoeui.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "segoeuib.ttf"),
        "reg": "SegoeUI", "reg_bold": "SegoeUI-Bold",
        "fallback": "Helvetica", "fallback_bold": "Helvetica-Bold",
    },
    {
        "id": "impact", "name": "Impact",
        "style_desc": "Ultra-bold condensed, maximum visual punch",
        "ttf": os.path.join(_WINFONTS, "impact.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "impact.ttf"),
        "reg": "ImpactFont", "reg_bold": "ImpactFont",
        "fallback": "Helvetica-Bold", "fallback_bold": "Helvetica-Bold",
    },
    {
        "id": "verdana", "name": "Verdana",
        "style_desc": "Wide, clear, screen-optimized readability",
        "ttf": os.path.join(_WINFONTS, "verdana.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "verdanab.ttf"),
        "reg": "Verdana", "reg_bold": "Verdana-Bold",
        "fallback": "Helvetica", "fallback_bold": "Helvetica-Bold",
    },
    {
        "id": "calibri", "name": "Calibri",
        "style_desc": "Modern warmth, humanist sans, Microsoft flagship",
        "ttf": os.path.join(_WINFONTS, "calibri.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "calibrib.ttf"),
        "reg": "Calibri", "reg_bold": "Calibri-Bold",
        "fallback": "Helvetica", "fallback_bold": "Helvetica-Bold",
    },
    {
        "id": "consolas", "name": "Consolas",
        "style_desc": "Monospaced tech, code-inspired modernity",
        "ttf": os.path.join(_WINFONTS, "consola.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "consolab.ttf"),
        "reg": "Consolas", "reg_bold": "Consolas-Bold",
        "fallback": "Courier", "fallback_bold": "Courier-Bold",
    },
    {
        "id": "arial_black", "name": "Arial Black",
        "style_desc": "Heavy grotesque, bold industrial presence",
        "ttf": os.path.join(_WINFONTS, "ariblk.ttf"),
        "ttf_bold": os.path.join(_WINFONTS, "ariblk.ttf"),
        "reg": "ArialBlack", "reg_bold": "ArialBlack",
        "fallback": "Helvetica-Bold", "fallback_bold": "Helvetica-Bold",
    },
]

# ═══════════════════════════════════════════════════════════════
#  RECOMMENDED PAIRINGS (style → font, style → palette)
# ═══════════════════════════════════════════════════════════════

STYLE_FONT_MAP = {
    "anime_pop": "impact",
    "indian_classical": "georgia",
    "luxury_minimalist": "palatino",
    "gothic_editorial": "times_nr",
    "heavy_metal": "arial_black",
    "art_deco": "georgia",
    "swiss_international": "segoe",
    "african_futurism": "trebuchet",
    "french_haute_couture": "palatino",
    "cyberpunk_noir": "consolas",
    "ancient_greek": "times_nr",
    "nordic_clean": "calibri",
}

STYLE_PALETTE_MAP = {
    "anime_pop": "electric_indigo",
    "indian_classical": "saffron_dynasty",
    "luxury_minimalist": "ivory_charcoal",
    "gothic_editorial": "crimson_noir",
    "heavy_metal": "obsidian_chrome",
    "art_deco": "midnight_gold",
    "swiss_international": "arctic_steel",
    "african_futurism": "terracotta_sage",
    "french_haute_couture": "rose_quartz",
    "cyberpunk_noir": "electric_indigo",
    "ancient_greek": "terracotta_sage",
    "nordic_clean": "arctic_steel",
}

# ═══════════════════════════════════════════════════════════════
#  FONT REGISTRATION
# ═══════════════════════════════════════════════════════════════

_registered: set[str] = set()


def register_font(font_id: str) -> tuple[str, str]:
    """Register a font pair with ReportLab. Returns (regular_name, bold_name).

    Tries to load the Windows TTF file first; falls back to a built-in
    ReportLab font if the TTF is missing.
    """
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
                reg_b = reg  # use regular as bold fallback
            _registered.add(reg)
            print(f"  [Font] Registered: {cfg['name']}")
            return reg, reg_b
    except Exception as e:
        print(f"  [Font] Could not register {cfg['name']}: {e}")

    # Fallback
    _registered.add(reg)
    fb, fb_b = cfg["fallback"], cfg["fallback_bold"]
    print(f"  [Font] Using fallback: {fb}")
    return fb, fb_b


def lookup_style(style_id: str) -> dict:
    """Look up a style by ID. Returns the style dict or the first one."""
    return next((s for s in STYLES if s["id"] == style_id), STYLES[0])


def lookup_palette(palette_id: str) -> dict:
    """Look up a palette by ID. Returns the palette dict or the first one."""
    return next((p for p in COLOR_PALETTES if p["id"] == palette_id),
                COLOR_PALETTES[0])


def lookup_font(font_id: str) -> dict:
    """Look up a font by ID. Returns the font dict or the first one."""
    return next((f for f in FONTS if f["id"] == font_id), FONTS[0])


def get_catalog_for_prompt() -> str:
    """Format the catalog for inclusion in LLM prompts."""
    lines = [
        "AVAILABLE STYLES (pick ONE style_id):",
    ]
    for s in STYLES:
        lines.append(f"  {s['id']}: {s['name']} — {s['description']}")

    lines.append("\nAVAILABLE COLOR PALETTES (pick ONE palette_id):")
    for p in COLOR_PALETTES:
        lines.append(f"  {p['id']}: {p['name']} — {p['mood']}")

    lines.append("\nAVAILABLE FONTS (pick ONE font_id):")
    for f in FONTS:
        lines.append(f"  {f['id']}: {f['name']} — {f['style_desc']}")

    lines.append("\nRECOMMENDED PAIRINGS (optional, you can mix):")
    for sid, fid in STYLE_FONT_MAP.items():
        pid = STYLE_PALETTE_MAP.get(sid, "")
        lines.append(f"  {sid} → font: {fid}, palette: {pid}")

    return "\n".join(lines)
