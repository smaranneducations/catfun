"""Poster + Agent Credits + Decision Architecture PDF Generator.

Output structure:
  Section 1 — POSTER (pages 1–4):
    Page 1: Cover / Landing (massive title, prominent author names)
    Pages 2–4: Content in poster format (one bold statement per page)

  Section 2 — AGENT CREDITS (pages 5–6):
    All agents with codename, role, and mandate
    Clean document style with card-based layout

  Section 3 — DECISION ARCHITECTURE (page 7):
    Visual pipeline / mind map showing agent flow
    How data flowed between agents to create this poster
    Summary statistics

Page format: Portrait 612×792 (US Letter)
Fonts: Chosen from design_catalog based on LLM style selection
"""
import math
import random
import re
import json
from pathlib import Path

from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from aibrief import config
from aibrief.pipeline.design_catalog import (
    STYLES, COLOR_PALETTES, FONTS,
    register_font, lookup_style, lookup_palette, lookup_font,
    STYLE_FONT_MAP, STYLE_PALETTE_MAP,
)

# ═══════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════

W = 612    # US Letter width (points)
H = 792    # US Letter height (points)
PAGE_SIZE = (W, H)
M = 50     # margin
CW = W - 2 * M   # content width (~512)

# ═══════════════════════════════════════════════════════════════
#  UTILITIES
# ═══════════════════════════════════════════════════════════════


def _hex(c: str) -> HexColor:
    try:
        if not c or not isinstance(c, str):
            return HexColor("#1a1a2e")
        c = c.strip().lstrip("#")
        if len(c) != 6:
            return HexColor("#1a1a2e")
        return HexColor(f"#{c}")
    except Exception:
        return HexColor("#1a1a2e")


def _a(base, alpha: float) -> Color:
    return Color(base.red, base.green, base.blue, alpha)


def _gradient(cv, x, y, w, h, c1, c2, steps=60, horiz=False):
    if horiz:
        sw = w / steps
        for i in range(steps):
            t = i / steps
            cv.setFillColor(Color(
                c1.red + (c2.red - c1.red) * t,
                c1.green + (c2.green - c1.green) * t,
                c1.blue + (c2.blue - c1.blue) * t))
            cv.rect(x + i * sw, y, sw + 1, h, fill=1, stroke=0)
    else:
        sh = h / steps
        for i in range(steps):
            t = i / steps
            cv.setFillColor(Color(
                c1.red + (c2.red - c1.red) * t,
                c1.green + (c2.green - c1.green) * t,
                c1.blue + (c2.blue - c1.blue) * t))
            cv.rect(x, y + i * sh, w, sh + 1, fill=1, stroke=0)


def _text(cv, txt, x, y, font, size, color, max_w=None, leading=None,
          align="left") -> float:
    """Draw wrapped text. Returns the new Y position after the text."""
    if not txt:
        return y
    max_w = max_w or CW
    leading = leading or size * 1.25
    al = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT
          }.get(align, TA_LEFT)
    safe = (str(txt).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))
    style = ParagraphStyle("t", fontName=font, fontSize=size,
                           leading=leading, textColor=color, alignment=al)
    p = Paragraph(safe, style)
    pw, ph = p.wrap(max_w, H)
    p.drawOn(cv, x, y - ph)
    return y - ph


def _place_image(cv, img_path: str, x, y, w, h):
    if not img_path or not Path(img_path).exists():
        return
    try:
        cv.drawImage(img_path, x, y, width=w, height=h,
                     preserveAspectRatio=True, mask="auto")
    except Exception as e:
        print(f"  [Poster] Image error: {e}")


def _luxury_name() -> str:
    prefixes = ["Jaguar", "Aurèle", "Maison", "Noir", "Velvet",
                "Luxe", "Sovereign", "Obsidian", "Ivory", "Sable",
                "Marquis", "Rivière", "Tempest", "Cristal", "Platine",
                "Cadence", "Meridian", "Ascent", "Soleil", "Nocturne"]
    suffixes = ["Phantom", "Prestige", "Éclat", "Lumière", "Royal",
                "Crown", "Sterling", "Heritage", "Atelier", "Opus",
                "Dominion", "Vanguard", "Essence", "Pinnacle", "Sovereign"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"


def _draw_rounded_rect(cv, x, y, w, h, r, fill_color=None, stroke_color=None,
                       stroke_w=1):
    """Draw a rounded rect with optional fill and stroke."""
    if fill_color:
        cv.setFillColor(fill_color)
    if stroke_color:
        cv.setStrokeColor(stroke_color)
        cv.setLineWidth(stroke_w)
    cv.roundRect(x, y, w, h, r,
                 fill=1 if fill_color else 0,
                 stroke=1 if stroke_color else 0)


# ═══════════════════════════════════════════════════════════════
#  STYLE-SPECIFIC DECORATIONS
# ═══════════════════════════════════════════════════════════════

def _style_decoration(cv, style_id: str, accent, secondary, page_num: int):
    """Draw decorative elements specific to the chosen visual style."""
    if style_id == "anime_pop":
        # Bold diagonal speed lines
        cv.setStrokeColor(_a(accent, 0.12))
        cv.setLineWidth(3)
        for i in range(0, W + H, 40):
            cv.line(i, H, i - H, 0)
        # Exclamation burst
        cv.setFillColor(_a(accent, 0.06))
        cv.circle(W * 0.85, H * 0.15, 80, fill=1, stroke=0)

    elif style_id == "indian_classical":
        # Concentric circles (mandala hint)
        cx, cy = W * 0.5, H * 0.5
        for r in range(50, 350, 40):
            cv.setStrokeColor(_a(accent, 0.04))
            cv.setLineWidth(1)
            cv.circle(cx, cy, r, fill=0, stroke=1)
        # Corner filigree dots
        for dx, dy in [(M, M), (W - M, M), (M, H - M), (W - M, H - M)]:
            cv.setFillColor(_a(accent, 0.08))
            cv.circle(dx, dy, 25, fill=1, stroke=0)

    elif style_id == "gothic_editorial":
        # Pointed arch at top
        cv.setFillColor(_a(accent, 0.05))
        p = cv.beginPath()
        p.moveTo(0, H)
        p.lineTo(W / 2, H - 120)
        p.lineTo(W, H)
        p.close()
        cv.drawPath(p, fill=1, stroke=0)
        # Vertical lines (column feel)
        cv.setStrokeColor(_a(accent, 0.04))
        cv.setLineWidth(1)
        for x in range(int(M), int(W - M), 60):
            cv.line(x, 0, x, H)

    elif style_id == "heavy_metal":
        # Diagonal scratches
        cv.setStrokeColor(_a(accent, 0.08))
        cv.setLineWidth(2)
        for i in range(8):
            x1 = random.randint(0, W)
            cv.line(x1, H, x1 + 200, 0)
        # Angular accent bar
        cv.setFillColor(_a(accent, 0.15))
        p = cv.beginPath()
        p.moveTo(0, H * 0.08)
        p.lineTo(W, H * 0.05)
        p.lineTo(W, 0)
        p.lineTo(0, 0)
        p.close()
        cv.drawPath(p, fill=1, stroke=0)

    elif style_id == "art_deco":
        # Geometric fan pattern at top
        cx = W / 2
        cv.setStrokeColor(_a(accent, 0.1))
        cv.setLineWidth(1.5)
        for angle in range(-60, 61, 12):
            rad = math.radians(angle)
            cv.line(cx, H, cx + 300 * math.sin(rad), H - 300 * math.cos(rad))
        # Horizontal gold lines
        for y_pos in [H * 0.02, H * 0.98]:
            cv.setFillColor(accent)
            cv.rect(M, y_pos, CW, 2, fill=1, stroke=0)

    elif style_id == "swiss_international":
        # Grid dots
        cv.setFillColor(_a(accent, 0.06))
        for gx in range(int(M), int(W - M), 30):
            for gy in range(int(M), int(H - M), 30):
                cv.circle(gx, gy, 1.5, fill=1, stroke=0)

    elif style_id == "african_futurism":
        # Bold triangular patterns
        cv.setFillColor(_a(accent, 0.06))
        for i in range(0, W, 60):
            p = cv.beginPath()
            p.moveTo(i, 0)
            p.lineTo(i + 30, 50)
            p.lineTo(i + 60, 0)
            p.close()
            cv.drawPath(p, fill=1, stroke=0)
        # Top triangles
        for i in range(0, W, 60):
            p = cv.beginPath()
            p.moveTo(i, H)
            p.lineTo(i + 30, H - 50)
            p.lineTo(i + 60, H)
            p.close()
            cv.drawPath(p, fill=1, stroke=0)

    elif style_id == "french_haute_couture":
        # Subtle diagonal crosshatch
        cv.setStrokeColor(_a(accent, 0.04))
        cv.setLineWidth(0.5)
        for i in range(-H, W + H, 25):
            cv.line(i, H, i + H, 0)
            cv.line(i, 0, i + H, H)

    elif style_id == "cyberpunk_noir":
        # Glitch blocks
        for _ in range(6):
            bx = random.randint(0, W - 80)
            by = random.randint(0, H - 15)
            cv.setFillColor(_a(accent, 0.08))
            cv.rect(bx, by, random.randint(40, 120), random.randint(3, 10),
                    fill=1, stroke=0)
        # Scan line
        cv.setStrokeColor(_a(accent, 0.05))
        cv.setLineWidth(0.5)
        for y_pos in range(0, H, 4):
            cv.line(0, y_pos, W, y_pos)

    elif style_id == "ancient_greek":
        # Column lines at edges
        cv.setStrokeColor(_a(accent, 0.06))
        cv.setLineWidth(2)
        cv.line(M - 10, M, M - 10, H - M)
        cv.line(W - M + 10, M, W - M + 10, H - M)
        # Meander / key pattern hint at bottom
        cv.setFillColor(_a(accent, 0.05))
        cv.rect(M, M - 10, CW, 8, fill=1, stroke=0)
        cv.rect(M, H - M + 2, CW, 8, fill=1, stroke=0)

    elif style_id == "nordic_clean":
        # Gentle organic circles
        cv.setFillColor(_a(accent, 0.03))
        cv.circle(W * 0.8, H * 0.7, 150, fill=1, stroke=0)
        cv.circle(W * 0.2, H * 0.3, 100, fill=1, stroke=0)

    else:
        # Default: subtle accent circles
        cv.setFillColor(_a(accent, 0.04))
        cv.circle(W * 0.7, H * 0.3, 180, fill=1, stroke=0)
        cv.circle(W * 0.3, H * 0.7, 120, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════
#  SECTION 1: POSTER PAGES
# ═══════════════════════════════════════════════════════════════

def _build_cover(cv, brief, story, design, visuals, font, bold,
                 colors, style_id):
    """Cover page: full-bleed image/gradient, massive title, prominent author."""
    primary, secondary, accent = colors["primary"], colors["secondary"], colors["accent"]

    # Background
    cover_img = (visuals or {}).get("cover", "")
    if cover_img and Path(cover_img).exists():
        _place_image(cv, cover_img, 0, 0, W, H)
        # Dark vignette overlay
        for i in range(80):
            t = i / 80
            cv.setFillColor(Color(0, 0, 0, t * 0.85))
            cv.rect(0, i * (H / 80), W, H / 80 + 1, fill=1, stroke=0)
    else:
        _gradient(cv, 0, 0, W, H, primary, secondary)

    # Style decoration
    _style_decoration(cv, style_id, accent, secondary, 0)

    # Top accent bar
    cv.setFillColor(accent)
    cv.rect(0, H - 5, W, 5, fill=1, stroke=0)

    # === MASSIVE TITLE (72pt) ===
    title = brief.get("brief_title", "AI Brief")
    y = H * 0.42

    # Accent bar above title
    cv.setFillColor(accent)
    cv.rect((W - 60) / 2, y + 25, 60, 4, fill=1, stroke=0)

    y = _text(cv, title, M, y, bold, 72, white,
              max_w=CW, leading=80, align="center")

    # Subtitle
    subtitle = brief.get("subtitle", "")
    if subtitle:
        y = _text(cv, subtitle, M, y - 12, font, 20, _a(white, 0.7),
                  max_w=CW * 0.85, leading=26, align="center")

    # === AUTHOR BLOCK (36pt — 50% of header) ===
    # Dark panel behind author names
    author_y = H * 0.10
    cv.setFillColor(Color(0, 0, 0, 0.45))
    cv.roundRect(M - 10, author_y - 20, CW + 20, 95, 8, fill=1, stroke=0)

    # Author name — 36pt (50% of 72pt header)
    _text(cv, "Bhasker Kumar", M, author_y + 60, bold, 36, white,
          max_w=CW, align="center")

    # Assistant name — 36pt
    asst = brief.get("_assistant_name", _luxury_name())
    _text(cv, f"with {asst}", M, author_y + 22, bold, 28, _a(accent, 0.9),
          max_w=CW, align="center")

    # System credit
    _text(cv, "Multi-Agent AI System  \u2022  Claude  \u2022  Gemini  \u2022  ChatGPT",
          M, author_y - 8, font, 10, _a(white, 0.4), max_w=CW, align="center")

    # Bottom accent
    cv.setFillColor(accent)
    cv.rect(0, 0, W, 5, fill=1, stroke=0)


def _build_content_page(cv, page, page_num, design, visuals, font, bold,
                        colors, style_id):
    """Content page: one bold statement per page, style-decorated."""
    primary = colors["primary"]
    secondary = colors["secondary"]
    accent = colors["accent"]
    bg = colors["bg"]
    text_col = colors["text"]
    heading_col = colors["heading"]

    ptype = page.get("page_type", "impact")

    # Background
    if ptype == "stat" or page_num % 2 == 0:
        # Dark background for stat pages or even pages
        _gradient(cv, 0, 0, W, H, primary, _a(secondary, 0.6))
        txt_c = white
        sub_c = _a(white, 0.6)
        num_c = accent
    else:
        # Light background
        cv.setFillColor(bg)
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        txt_c = heading_col
        sub_c = _a(text_col, 0.6)
        num_c = accent

    # Style decoration
    _style_decoration(cv, style_id, accent, secondary, page_num)

    # Visual (if available)
    vis = (visuals or {}).get(ptype, "")
    if vis and Path(vis).exists():
        _place_image(cv, vis, (W - 160) / 2, H * 0.06, 160, 160)

    if ptype == "stat":
        # === STAT HERO: massive number centered ===
        hero_num = (page.get("hero_number", "") or page.get("key_stat", "")
                    or page.get("hero_statement", ""))
        y = H * 0.55
        y = _text(cv, hero_num, M, y, bold, 108, num_c,
                  max_w=CW, leading=110, align="center")

        label = (page.get("hero_label", "") or page.get("key_stat_label", "")
                 or page.get("title", ""))
        if label:
            y = _text(cv, label, M, y - 8, bold, 22, txt_c,
                      max_w=CW, leading=28, align="center")

        ctx = (page.get("context_line", "") or page.get("supporting_line", "")
               or page.get("insight", ""))
        if ctx:
            y = _text(cv, ctx, M + 20, y - 20, font, 15, sub_c,
                      max_w=CW - 40, leading=22, align="center")

        # Accent divider
        cv.setFillColor(accent)
        cv.rect(W * 0.35, H * 0.58, W * 0.3, 2, fill=1, stroke=0)

    elif ptype == "quote":
        # === EDITORIAL QUOTE ===
        # Giant quote mark
        cv.setFillColor(_a(accent, 0.07))
        cv.setFont(bold, 280)
        cv.drawString(M - 15, H * 0.50, "\u201c")

        quote = page.get("quote", page.get("hero_statement", ""))
        y = H * 0.58
        y = _text(cv, f"\u201c{quote}\u201d", M + 25, y, bold, 36, txt_c,
                  max_w=CW - 50, leading=48, align="center")

        attr = page.get("attribution", page.get("quote_attribution", ""))
        if attr:
            y = _text(cv, f"\u2014 {attr}", M, y - 18, font, 16, sub_c,
                      max_w=CW, leading=22, align="center")

        cv.setFillColor(accent)
        cv.rect(W * 0.4, y - 12, W * 0.2, 2.5, fill=1, stroke=0)

    else:
        # === IMPACT STATEMENT (default) ===
        # Accent bar above statement
        cv.setFillColor(accent)
        cv.rect((W - 40) / 2, H * 0.60, 40, 3, fill=1, stroke=0)

        # Big geometric accent
        cv.setFillColor(_a(accent, 0.05))
        cv.circle(W * 0.72, H * 0.28, 200, fill=1, stroke=0)

        statement = (page.get("hero_statement", "") or page.get("point", "")
                     or page.get("title", ""))
        y = H * 0.57
        y = _text(cv, statement, M + 8, y, bold, 48, txt_c,
                  max_w=CW - 16, leading=58, align="center")

        supporting = (page.get("supporting_line", "")
                      or page.get("insight", ""))
        if supporting:
            y = _text(cv, supporting, M + 20, y - 22, font, 18, sub_c,
                      max_w=CW - 40, leading=26, align="center")

    # Page number — subtle
    _text(cv, f"{page_num}", W - M, 15, font, 9, _a(txt_c, 0.2),
          align="right")


# ═══════════════════════════════════════════════════════════════
#  SECTION 2: AGENT CREDITS
# ═══════════════════════════════════════════════════════════════

def _build_agent_credits(cv, agents_info, font, bold, colors, style_id):
    """Build agent credits pages — card layout with all agents."""
    if not agents_info:
        return

    accent = colors["accent"]
    bg = colors["bg"]
    text_col = colors["text"]
    heading_col = colors["heading"]
    primary = colors["primary"]

    # Cards layout: 2 columns, max 5 rows per page
    card_w = (CW - 20) / 2  # ~246 each
    card_h = 105
    col_gap = 20
    row_gap = 12
    cards_per_page = 10  # 2 columns × 5 rows

    pages = [agents_info[i:i + cards_per_page]
             for i in range(0, len(agents_info), cards_per_page)]

    for pi, page_agents in enumerate(pages):
        # Clean document background
        cv.setFillColor(_hex("#f8f6f1"))
        cv.rect(0, 0, W, H, fill=1, stroke=0)

        # Subtle accent bar at top
        cv.setFillColor(accent)
        cv.rect(0, H - 3, W, 3, fill=1, stroke=0)

        # Title (first page only)
        y = H - M
        if pi == 0:
            y = _text(cv, "The Intelligence Behind This Brief", M, y,
                      bold, 28, _hex("#1a1a2e"), max_w=CW, align="center")
            y = _text(cv, "A Multi-Agent AI System  \u2022  Claude  \u2022  Gemini  \u2022  ChatGPT",
                      M, y - 8, font, 11, _hex("#666666"),
                      max_w=CW, align="center")
            y -= 20
        else:
            y = _text(cv, "Agent Roster (continued)", M, y,
                      bold, 22, _hex("#1a1a2e"), max_w=CW, align="center")
            y -= 15

        # Draw cards
        for idx, agent in enumerate(page_agents):
            col = idx % 2
            row = idx // 2
            cx = M + col * (card_w + col_gap)
            cy = y - row * (card_h + row_gap) - card_h

            # Card background
            _draw_rounded_rect(cv, cx, cy, card_w, card_h,
                               6, fill_color=white,
                               stroke_color=_a(accent, 0.3), stroke_w=1)

            # Accent side bar
            cv.setFillColor(accent)
            cv.rect(cx, cy, 4, card_h, fill=1, stroke=0)

            # Codename (large, accent color)
            _text(cv, agent.get("codename", "?"), cx + 14, cy + card_h - 12,
                  bold, 16, accent, max_w=card_w - 20)

            # Agent name
            _text(cv, agent.get("name", ""), cx + 14, cy + card_h - 30,
                  font, 10, _hex("#333333"), max_w=card_w - 20)

            # Role
            _text(cv, agent.get("role", ""), cx + 14, cy + card_h - 44,
                  font, 9, _hex("#555555"), max_w=card_w - 20)

            # Mandate (truncated)
            mandate = agent.get("mandate", "")[:120]
            if len(agent.get("mandate", "")) > 120:
                mandate += "..."
            _text(cv, mandate, cx + 14, cy + card_h - 58,
                  font, 7.5, _hex("#777777"), max_w=card_w - 22,
                  leading=10)

        # Page number
        _text(cv, f"Agent Credits  \u2022  {pi + 1}/{len(pages)}",
              M, 20, font, 8, _hex("#999999"), max_w=CW, align="center")

        cv.showPage()


# ═══════════════════════════════════════════════════════════════
#  SECTION 3: DECISION ARCHITECTURE / MIND MAP
# ═══════════════════════════════════════════════════════════════

_PIPELINE_ROWS = [
    {
        "nodes": [("Aria", "World Pulse", "Scans global sentiment")],
        "phase": "Phase 0",
    },
    {
        "nodes": [("Marcus", "Content Strategy", "Picks type, tone, length")],
        "phase": "Phase 1",
    },
    {
        "nodes": [
            ("Sable", "Topic Discovery", "Finds & dedup topic"),
            ("Vesper", "Design DNA", "Visual identity"),
        ],
        "phase": "Phase 2–3",
    },
    {
        "nodes": [
            ("Clio", "Historian", ""),
            ("Aurelia", "Economist", ""),
            ("Sage", "Sociologist", ""),
            ("Nova", "Futurist", ""),
        ],
        "phase": "Phase 4",
    },
    {
        "nodes": [
            ("All Analysts", "Round Table", "Cross-challenges"),
            ("Paramount", "Editorial", "Quality gate"),
        ],
        "phase": "Phase 5–6",
    },
    {
        "nodes": [
            ("Quill", "Writer", "Synthesis"),
            ("Sterling", "Copy Review", "Luxury QC"),
        ],
        "phase": "Phase 7",
    },
    {
        "nodes": [
            ("Justice", "Neutrality", "Guardrail"),
            ("Prism", "Visuals", "DALL-E + Pillow"),
        ],
        "phase": "Phase 8–9",
    },
    {
        "nodes": [
            ("Ratio", "Screen Audit", "Golden ratio"),
            ("Sentinel", "Validation", "37 rules"),
        ],
        "phase": "Phase 11–12",
    },
    {
        "nodes": [("Herald", "LinkedIn Post", "Unicode formatting")],
        "phase": "Phase 13",
    },
]

# Branch colors for mind map (by function group)
_BRANCH_COLORS = [
    "#3498db",  # Row 0: discovery - blue
    "#2ecc71",  # Row 1: strategy - green
    "#9b59b6",  # Row 2: topic + design - purple
    "#e67e22",  # Row 3: analysts - orange
    "#e74c3c",  # Row 4: round table - red
    "#1abc9c",  # Row 5: synthesis - teal
    "#f39c12",  # Row 6: neutrality/visuals - yellow
    "#2c3e50",  # Row 7: validation - dark
    "#e91e63",  # Row 8: linkedin - pink
]


def _draw_pipeline_node(cv, x, y, w, h, codename, role, annotation,
                        fill_hex, font, bold):
    """Draw a single pipeline node."""
    fc = _hex(fill_hex)

    # Node background
    _draw_rounded_rect(cv, x, y, w, h, 6,
                       fill_color=_a(fc, 0.12),
                       stroke_color=_a(fc, 0.5), stroke_w=1.2)

    # Left accent bar
    cv.setFillColor(fc)
    cv.roundRect(x, y, 3, h, 1, fill=1, stroke=0)

    # Codename (bold)
    _text(cv, codename, x + 9, y + h - 6, bold, 10, fc, max_w=w - 14)

    # Role (smaller)
    if role:
        _text(cv, role, x + 9, y + 4, font, 7, _hex("#555555"),
              max_w=w - 14)


def _build_mind_map(cv, tracer_flow, topic, font, bold, colors):
    """Build the decision architecture page — visual pipeline diagram."""
    # Clean background
    cv.setFillColor(_hex("#faf9f5"))
    cv.rect(0, 0, W, H, fill=1, stroke=0)

    accent = colors["accent"]

    # Accent bar at top
    cv.setFillColor(accent)
    cv.rect(0, H - 3, W, 3, fill=1, stroke=0)

    # Title
    y = H - M
    y = _text(cv, "Decision Architecture", M, y, bold, 30,
              _hex("#1a1a2e"), max_w=CW, align="center")
    y = _text(cv, "How 15+ AI Agents Created This Poster", M, y - 4,
              font, 12, _hex("#666666"), max_w=CW, align="center")

    # Topic box (central, accent colored)
    topic_str = topic or "AI Thought Leadership"
    topic_h = 32
    topic_y = y - topic_h - 12
    _draw_rounded_rect(cv, M + 50, topic_y, CW - 100, topic_h, 8,
                       fill_color=_a(accent, 0.15),
                       stroke_color=_a(accent, 0.6), stroke_w=1.5)
    _text(cv, topic_str, M + 55, topic_y + topic_h - 8, bold, 12,
          accent, max_w=CW - 110, align="center")

    y = topic_y - 10

    # Draw pipeline rows
    node_h = 32
    row_gap = 8

    for ri, row in enumerate(_PIPELINE_ROWS):
        nodes = row["nodes"]
        n = len(nodes)
        branch_color = _BRANCH_COLORS[ri % len(_BRANCH_COLORS)]

        # Connecting line from previous row
        if ri > 0:
            line_x = W / 2
            cv.setStrokeColor(_a(_hex(branch_color), 0.3))
            cv.setLineWidth(1.5)
            cv.setDash(3, 3)
            cv.line(line_x, y + node_h + row_gap, line_x, y + node_h + 2)
            cv.setDash()

        if n == 1:
            nw = min(CW * 0.6, 320)
            nx = M + (CW - nw) / 2
            _draw_pipeline_node(cv, nx, y, nw, node_h,
                                nodes[0][0], nodes[0][1], nodes[0][2],
                                branch_color, font, bold)
        elif n == 2:
            gap = 14
            nw = (CW - gap) / 2
            for ci, (code, role, ann) in enumerate(nodes):
                nx = M + ci * (nw + gap)
                _draw_pipeline_node(cv, nx, y, nw, node_h,
                                    code, role, ann,
                                    branch_color, font, bold)
            # Horizontal connector
            cv.setStrokeColor(_a(_hex(branch_color), 0.2))
            cv.setLineWidth(1)
            mid_y = y + node_h / 2
            cv.line(M + nw, mid_y, M + nw + gap, mid_y)
        elif n == 4:
            gap = 8
            nw = (CW - 3 * gap) / 4
            for ci, (code, role, ann) in enumerate(nodes):
                nx = M + ci * (nw + gap)
                _draw_pipeline_node(cv, nx, y, nw, node_h,
                                    code, role, ann,
                                    branch_color, font, bold)
        else:
            gap = 10
            nw = (CW - (n - 1) * gap) / n
            for ci, (code, role, ann) in enumerate(nodes):
                nx = M + ci * (nw + gap)
                _draw_pipeline_node(cv, nx, y, nw, node_h,
                                    code, role, ann,
                                    branch_color, font, bold)

        # Phase label (left margin)
        _text(cv, row["phase"], 4, y + node_h / 2 - 4, font, 6,
              _hex("#aaaaaa"), max_w=M - 8)

        y -= (node_h + row_gap)

    # ── Summary statistics ──
    y -= 15
    cv.setStrokeColor(_hex("#dddddd"))
    cv.setLineWidth(0.5)
    cv.line(M, y, W - M, y)
    y -= 5

    # Pull stats from tracer_flow if available
    tf = tracer_flow or {}
    stats = [
        ("Agents", str(tf.get("total_agents", 15))),
        ("Debates", str(tf.get("total_debates", 8))),
        ("Duration", f"{tf.get('total_duration', 0):.0f}s"),
        ("Mood", tf.get("key_outputs", {}).get("world_mood", "normal")),
        ("Validation", f"{tf.get('key_outputs', {}).get('validation_score', '?')}/100"),
    ]

    stat_w = CW / len(stats)
    for si, (label, value) in enumerate(stats):
        sx = M + si * stat_w
        _text(cv, value, sx, y, bold, 14, _hex("#1a1a2e"),
              max_w=stat_w, align="center")
        _text(cv, label, sx, y - 16, font, 8, _hex("#888888"),
              max_w=stat_w, align="center")

    # Footer
    _text(cv, f"Run ID: {tf.get('run_id', 'N/A')}",
          M, 18, font, 7, _hex("#bbbbbb"), max_w=CW, align="center")

    cv.showPage()


# ═══════════════════════════════════════════════════════════════
#  MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_poster(brief: dict, design: dict, story: dict,
                    visuals: dict = None, agents_info: list = None,
                    tracer_flow: dict = None,
                    output_path: str = None) -> str:
    """Generate the complete poster PDF.

    Structure:
        Pages 1–4: Poster (cover + 3 content)
        Pages 5–6: Agent credits (document style)
        Page 7:    Decision architecture (pipeline mind map)
    """
    if not output_path:
        slug = brief.get("brief_title", "AI_Brief")[:35]
        slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
        output_path = str(config.OUTPUT_DIR / f"{slug}_poster.pdf")

    visuals = visuals or {}
    brief["_assistant_name"] = _luxury_name()

    # ── Resolve design from catalog ──
    style_id = design.get("style_id", "luxury_minimalist")
    palette_id = design.get("palette_id", "")
    font_id = design.get("font_id", "")

    # Look up catalog entries
    style = lookup_style(style_id)
    palette = lookup_palette(palette_id) if palette_id else None
    font_cfg = lookup_font(font_id) if font_id else None

    # Register font from catalog
    if font_id:
        font_name, bold_name = register_font(font_id)
    else:
        font_name, bold_name = "Helvetica", "Helvetica-Bold"

    # Build color dict — prefer catalog palette, fallback to design dict
    if palette:
        colors = {
            "primary": _hex(palette["primary"]),
            "secondary": _hex(palette["secondary"]),
            "accent": _hex(palette["accent"]),
            "bg": _hex(palette["background"]),
            "text": _hex(palette["text"]),
            "heading": _hex(palette["heading"]),
        }
    else:
        colors = {
            "primary": _hex(design.get("primary_color", "#0f1729")),
            "secondary": _hex(design.get("secondary_color", "#1e3a5f")),
            "accent": _hex(design.get("accent_color", "#c8a44e")),
            "bg": _hex(design.get("background_color", "#f0ede6")),
            "text": _hex(design.get("text_color", "#2d2d3a")),
            "heading": _hex(design.get("heading_color", "#0f1729")),
        }

    print(f"  [Poster] Style: {style['name']}")
    print(f"  [Poster] Font: {font_name} / {bold_name}")
    print(f"  [Poster] Palette: {palette['name'] if palette else 'custom'}")

    # ── Create PDF ──
    pdf = canvas.Canvas(output_path, pagesize=PAGE_SIZE)
    pdf.setTitle(brief.get("brief_title", "AI Brief"))
    pdf.setAuthor("Bhasker Kumar")

    # === SECTION 1: POSTER PAGES (cover + 3 content) ===
    pages = brief.get("pages", [])

    # Page 1: Cover
    _build_cover(pdf, brief, story, design, visuals,
                 font_name, bold_name, colors, style_id)
    pdf.showPage()

    # Pages 2-4: Content (max 3 content pages)
    content_pages = [p for p in pages if p.get("page_type") != "hero"][:3]
    for i, page in enumerate(content_pages):
        _build_content_page(pdf, page, i + 2, design, visuals,
                            font_name, bold_name, colors, style_id)
        pdf.showPage()

    # === SECTION 2: AGENT CREDITS ===
    if agents_info:
        _build_agent_credits(pdf, agents_info, font_name, bold_name,
                             colors, style_id)
        # (showPage is called inside _build_agent_credits)

    # === SECTION 3: DECISION ARCHITECTURE / MIND MAP ===
    topic = story.get("headline", brief.get("brief_title", ""))
    _build_mind_map(pdf, tracer_flow, topic, font_name, bold_name, colors)
    # (showPage is called inside _build_mind_map)

    # ── Save ──
    pdf.save()
    total_pages = 1 + len(content_pages)  # poster section
    if agents_info:
        total_pages += math.ceil(len(agents_info) / 10)  # agent credits
    total_pages += 1  # mind map
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [Poster] Saved: {output_path} ({size_kb:.0f} KB, "
          f"~{total_pages} pages)")
    return output_path
