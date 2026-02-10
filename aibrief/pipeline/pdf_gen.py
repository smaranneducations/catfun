"""Luxury SLIDE-DECK PDF generator — every page is a presentation slide.

Design principles enforced:
  - Landscape orientation (like PPT slides)
  - EVERY page has artistic background (light patterns, gradients, textures)
  - Big commanding headers (40-48pt)
  - Bullet points, NOT paragraphs
  - Cover is SUPER exciting (hero image, dramatic overlay)
  - Author 'Bhasker Kumar' at >= 75% of header font size
  - Golden ratio, color psychology, 3-level typography
  - One idea per slide
"""
import math
import random
import re
from pathlib import Path
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from aibrief import config

# Landscape slide dimensions (16:9-ish, like PPT)
W = 792   # 11 inches
H = 612   # 8.5 inches
PAGE_SIZE = (W, H)

# Margins
M = 55
CONTENT_W = W - 2 * M  # ~682


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
    """Smooth gradient fill."""
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
    """Draw wrapped text. Returns Y after text."""
    if not txt:
        return y
    max_w = max_w or CONTENT_W
    leading = leading or size * 1.35
    al = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT}.get(align, TA_LEFT)
    safe = str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    style = ParagraphStyle("t", fontName=font, fontSize=size, leading=leading,
                           textColor=color, alignment=al)
    p = Paragraph(safe, style)
    pw, ph = p.wrap(max_w, H)
    p.drawOn(cv, x, y - ph)
    return y - ph


def _place_image(cv, img_path: str, x: float, y: float, w: float, h: float):
    if not img_path or not Path(img_path).exists():
        return
    try:
        cv.drawImage(img_path, x, y, width=w, height=h,
                     preserveAspectRatio=True, mask="auto")
    except Exception as e:
        print(f"  [PDF] Image error: {e}")


# ═══════════════════════════════════════════════════════════════
#  ARTISTIC BACKGROUNDS — Every page gets one, never plain
# ═══════════════════════════════════════════════════════════════

def _draw_artistic_bg(cv, primary, secondary, accent, bg, page_num, total_pages):
    """Draw a unique artistic background for each slide.

    Cycles through multiple styles so no two consecutive pages look the same.
    Every page gets a rich, textured background — never plain/dull/white.
    """
    style = page_num % 6

    if style == 0:
        # Deep gradient background
        _gradient(cv, 0, 0, W, H, bg, _a(secondary, 0.12))
        # Subtle geometric circles
        for _ in range(random.randint(4, 8)):
            cx = random.randint(0, int(W))
            cy = random.randint(0, int(H))
            r = random.randint(40, 150)
            cv.setFillColor(_a(accent, random.uniform(0.02, 0.06)))
            cv.circle(cx, cy, r, fill=1, stroke=0)

    elif style == 1:
        # Two-tone diagonal split
        cv.setFillColor(bg)
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        # Accent panel on right 30%
        _gradient(cv, W * 0.7, 0, W * 0.3, H, _a(primary, 0.06), _a(accent, 0.08), horiz=True)
        # Subtle dot grid
        for ix in range(0, int(W), 40):
            for iy in range(0, int(H), 40):
                cv.setFillColor(_a(accent, 0.03))
                cv.circle(ix, iy, 1.5, fill=1, stroke=0)

    elif style == 2:
        # Rich warm wash
        _gradient(cv, 0, 0, W, H, _a(primary, 0.04), bg)
        # Flowing curves (bezier-like arcs)
        cv.setStrokeColor(_a(accent, 0.05))
        cv.setLineWidth(2)
        for i in range(3):
            y_start = random.randint(int(H * 0.2), int(H * 0.8))
            cv.bezier(0, y_start, W * 0.3, y_start + random.randint(-100, 100),
                      W * 0.7, y_start + random.randint(-100, 100), W, y_start)

    elif style == 3:
        # Color-blocked with texture
        cv.setFillColor(bg)
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        # Bottom color block (golden ratio: 38.2% height)
        block_h = H * 0.382
        _gradient(cv, 0, 0, W, block_h, _a(primary, 0.08), _a(secondary, 0.04))
        # Subtle diagonal lines
        cv.setStrokeColor(_a(accent, 0.03))
        cv.setLineWidth(0.5)
        for x in range(-int(H), int(W), 25):
            cv.line(x, 0, x + int(H), int(H))

    elif style == 4:
        # Gradient mesh feel
        _gradient(cv, 0, 0, W, H, bg, _a(accent, 0.05))
        # Large soft circles (bokeh effect)
        for _ in range(5):
            cx = random.randint(int(W * 0.3), int(W))
            cy = random.randint(0, int(H))
            r = random.randint(80, 200)
            cv.setFillColor(_a(secondary, random.uniform(0.02, 0.05)))
            cv.circle(cx, cy, r, fill=1, stroke=0)
        # Small accent dots
        for _ in range(20):
            cv.setFillColor(_a(accent, 0.04))
            cv.circle(random.randint(0, int(W)), random.randint(0, int(H)),
                      2, fill=1, stroke=0)

    else:
        # Radial gradient feel from center
        cv.setFillColor(bg)
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        # Concentric circles from center
        cx, cy = W * 0.6, H * 0.5
        for r in range(300, 20, -30):
            alpha = 0.02 + (300 - r) / 300 * 0.04
            cv.setFillColor(_a(accent, alpha))
            cv.circle(cx, cy, r, fill=1, stroke=0)

    # ALWAYS: top accent line
    cv.setFillColor(accent)
    cv.rect(0, H - 3, W, 3, fill=1, stroke=0)

    # ALWAYS: bottom accent line
    cv.setFillColor(_a(accent, 0.6))
    cv.rect(0, 0, W, 2.5, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════
#  COVER SLIDE — Super exciting, hero image, dramatic
# ═══════════════════════════════════════════════════════════════

def _build_cover(cv, brief, story, design, visuals, font, bold,
                 primary, secondary, accent):
    """Cover slide: full hero image, dramatic overlay, BIG title, prominent author."""
    cover_img = visuals.get("cover", "")
    if cover_img and Path(cover_img).exists():
        _place_image(cv, cover_img, 0, 0, W, H)
        # Dramatic vignette overlay (darker at bottom)
        for i in range(50):
            t = i / 50
            cv.setFillColor(Color(0, 0, 0, t * 0.65))
            sh = H / 50
            cv.rect(0, i * sh, W, sh + 1, fill=1, stroke=0)
    else:
        _gradient(cv, 0, 0, W, H, primary, secondary)

    # Top accent stripe (thick, bold)
    cv.setFillColor(accent)
    cv.rect(0, H - 6, W, 6, fill=1, stroke=0)

    # ── TITLE — golden ratio position, commanding ──
    y = H * 0.55

    # Accent bar
    cv.setFillColor(accent)
    cv.rect(M, y + 20, 80, 4, fill=1, stroke=0)

    # Main title: 44pt (commanding, slide-style)
    TITLE_SIZE = 44
    y = _text(cv, brief.get("brief_title", "AI Brief"), M, y,
              bold, TITLE_SIZE, white, max_w=W * 0.7, leading=52)

    # Subtitle: 18pt
    subtitle = brief.get("subtitle", "")
    if subtitle:
        y = _text(cv, subtitle, M, y - 6,
                  font, 18, _a(white, 0.8), max_w=W * 0.65, leading=24)

    # Divider
    cv.setStrokeColor(_a(white, 0.3))
    cv.setLineWidth(0.7)
    cv.line(M, y - 18, M + 300, y - 18)

    # ── AUTHOR BLOCK — PROMINENT (>= 75% of title = 33pt) ──
    AUTHOR_SIZE = max(int(TITLE_SIZE * 0.75), 33)
    ASSIST_SIZE = max(int(TITLE_SIZE * 0.4), 18)

    by = H * 0.16

    # Author background panel
    cv.setFillColor(Color(0, 0, 0, 0.35))
    cv.roundRect(M - 12, by - 75, 450, 100, 6, fill=1, stroke=0)

    _text(cv, "Bhasker Kumar", M, by,
          bold, AUTHOR_SIZE, white)

    asst = brief.get("_assistant_name", "Jaguar Phantom")
    _text(cv, f"Assisted by {asst}", M, by - AUTHOR_SIZE * 0.85,
          font, ASSIST_SIZE, _a(white, 0.7))

    _text(cv, "Multi-Agent System  \u2022  Claude  \u2022  Gemini  \u2022  ChatGPT",
          M, by - AUTHOR_SIZE * 0.85 - ASSIST_SIZE - 2,
          font, 11, _a(white, 0.45))

    # Date on right
    _text(cv, story.get("date", "February 2026"), W - M - 120, by,
          font, 13, _a(white, 0.5))

    # Bottom accent strip
    cv.setFillColor(accent)
    cv.rect(0, 0, W, 6, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════
#  CONTENT SLIDE — Bullets, visual, big header, one idea
# ═══════════════════════════════════════════════════════════════

def _build_slide(cv, page, page_num, total_pages, design, visuals,
                 font, bold, primary, secondary, accent, bg, text_col, heading_col):
    """Content slide: artistic bg, big header, bullets, visual, quote."""
    ptype = page.get("page_type", "")
    title = page.get("title", "")
    bullets = page.get("bullets", [])
    # Fallback: if old-format body text exists, split into bullets
    if not bullets and page.get("body"):
        body = page.get("body", "")
        bullets = [s.strip() for s in body.split(".") if s.strip()][:6]
    quote = page.get("quote", "")
    quote_attr = page.get("quote_attribution", "")
    key_stat = page.get("key_stat", "")
    key_stat_label = page.get("key_stat_label", "")
    vis_path = visuals.get(ptype, "")

    # ── Artistic background (EVERY page — never dull) ──
    _draw_artistic_bg(cv, primary, secondary, accent, bg, page_num, total_pages)

    # ── Layout: choose variant ──
    layout = page_num % 3

    y = H - M - 5

    # ── Section label (small, accent color) ──
    label = ptype.upper().replace("_", " ")
    cv.setFillColor(_a(accent, 0.7))
    cv.setFont(bold, 9)
    cv.drawString(M, y, label)
    y -= 6

    # Accent line under label
    cv.setFillColor(accent)
    cv.rect(M, y, 50, 2.5, fill=1, stroke=0)
    y -= 28

    # ── BIG TITLE (40-44pt, commanding, slide-style) ──
    y = _text(cv, title, M, y, bold, 40, heading_col,
              max_w=CONTENT_W * 0.85, leading=48)
    y -= 18

    if layout == 0:
        # ═══ LAYOUT A: Bullets left, Visual right ═══
        split_x = W * 0.55
        bullet_w = split_x - M - 20
        vis_x = split_x + 10
        vis_w = W - M - vis_x

        # Bullets
        y_bullets = y
        for i, bullet in enumerate(bullets[:6]):
            bullet_text = f"\u25b8  {bullet}"
            y_bullets = _text(cv, bullet_text, M, y_bullets,
                              font, 15, text_col, max_w=bullet_w, leading=22)
            y_bullets -= 6

        # Visual on right
        if vis_path:
            vis_h = min(280, y - M - 80)
            if vis_h > 60:
                _place_image(cv, vis_path, vis_x, y - vis_h, vis_w, vis_h)

        # Key stat (if present) below bullets
        if key_stat:
            y_stat = y_bullets - 15
            _text(cv, key_stat, M, y_stat, bold, 36, accent,
                  max_w=bullet_w)
            if key_stat_label:
                _text(cv, key_stat_label, M, y_stat - 40, font, 12,
                      _a(text_col, 0.6), max_w=bullet_w)

        y = y_bullets

    elif layout == 1:
        # ═══ LAYOUT B: Visual top-left, bullets right ═══
        vis_w_b = W * 0.38
        bullet_x = M + vis_w_b + 20
        bullet_w = W - M - bullet_x

        # Visual on left
        if vis_path:
            vis_h = min(220, y - M - 60)
            if vis_h > 60:
                _place_image(cv, vis_path, M, y - vis_h, vis_w_b - 20, vis_h)

        # Bullets on right
        y_bullets = y
        for bullet in bullets[:6]:
            bullet_text = f"\u25b8  {bullet}"
            y_bullets = _text(cv, bullet_text, bullet_x, y_bullets,
                              font, 15, text_col, max_w=bullet_w, leading=22)
            y_bullets -= 6

        # Key stat on right below bullets
        if key_stat:
            y_stat = y_bullets - 15
            _text(cv, key_stat, bullet_x, y_stat, bold, 36, accent,
                  max_w=bullet_w)
            if key_stat_label:
                _text(cv, key_stat_label, bullet_x, y_stat - 40, font, 12,
                      _a(text_col, 0.6), max_w=bullet_w)

        y = y_bullets

    else:
        # ═══ LAYOUT C: Key stat centered + bullets below + visual side ═══
        if key_stat:
            # Big stat centered
            cv.setFillColor(_a(accent, 0.08))
            cv.roundRect(M, y - 80, CONTENT_W, 75, 8, fill=1, stroke=0)
            _text(cv, key_stat, M + 20, y - 10, bold, 42, accent,
                  max_w=CONTENT_W * 0.5)
            if key_stat_label:
                _text(cv, key_stat_label, M + 20, y - 55, font, 14,
                      _a(text_col, 0.6))
            y -= 95

        # Bullets full width
        y_bullets = y
        for bullet in bullets[:6]:
            bullet_text = f"\u25b8  {bullet}"
            y_bullets = _text(cv, bullet_text, M, y_bullets,
                              font, 15, text_col, max_w=CONTENT_W * 0.6, leading=22)
            y_bullets -= 6

        # Visual on right side
        if vis_path:
            vis_h = min(180, y - M - 40)
            vis_x = W * 0.62
            if vis_h > 60:
                _place_image(cv, vis_path, vis_x, y_bullets, W - M - vis_x, vis_h)

        y = y_bullets

    # ── Quote block (bottom area) ──
    if quote:
        q_y = max(y - 15, M + 90)
        # Quote background
        cv.setFillColor(_a(accent, 0.07))
        cv.roundRect(M, q_y - 65, CONTENT_W, 60, 5, fill=1, stroke=0)
        cv.setFillColor(accent)
        cv.rect(M, q_y - 65, 4, 60, fill=1, stroke=0)

        _text(cv, f"\u201c{quote}\u201d", M + 18, q_y - 8,
              bold, 14, heading_col, max_w=CONTENT_W - 30, leading=19)
        if quote_attr:
            _text(cv, f"\u2014 {quote_attr}", M + 18, q_y - 42,
                  font, 10, _a(text_col, 0.5), max_w=CONTENT_W - 30)

    # ── Footer ──
    cv.setStrokeColor(_a(text_col, 0.08))
    cv.setLineWidth(0.4)
    cv.line(M, 22, W - M, 22)
    _text(cv, "AI BRIEF  \u2022  Bhasker Kumar", M, 8,
          bold, 8, _a(text_col, 0.2))
    _text(cv, f"{page_num}", W - M - 15, 8,
          font, 8, _a(text_col, 0.25), align="right")


# ═══════════════════════════════════════════════════════════════
#  LUXURY NAME GENERATOR
# ═══════════════════════════════════════════════════════════════

def _generate_luxury_name() -> str:
    prefixes = ["Jaguar", "Aurèle", "Maison", "Noir", "Velvet",
                "Luxe", "Sovereign", "Obsidian", "Ivory", "Sable",
                "Argent", "Opale", "Ébène", "Cristal", "Platine",
                "Marquis", "Pavillon", "Rivière", "Tempest", "Balmoral"]
    suffixes = ["Phantom", "Noir", "Prestige", "Éclat", "Lumière",
                "Royal", "Crown", "Sterling", "Heritage", "Atelier",
                "Legacy", "Prism", "Soleil", "Crest", "Bespoke",
                "Opus", "Serenade", "Meridian", "Regent", "Haute"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def generate_pdf(brief: dict, design: dict, story: dict,
                 visuals: dict = None, output_path: str = None) -> str:
    if not output_path:
        slug = brief.get("brief_title", "AI_Brief")[:35]
        slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
        output_path = str(config.OUTPUT_DIR / f"{slug}.pdf")

    visuals = visuals or {}
    brief["_assistant_name"] = _generate_luxury_name()

    font, bold = "Helvetica", "Helvetica-Bold"
    primary = _hex(design.get("primary_color", "#0f1729"))
    secondary = _hex(design.get("secondary_color", "#1e3a5f"))
    accent = _hex(design.get("accent_color", "#c8a44e"))
    bg = _hex(design.get("background_color", "#f0ede6"))
    text_col = _hex(design.get("text_color", "#2d2d3a"))
    heading_col = _hex(design.get("heading_color", "#0f1729"))

    pdf = canvas.Canvas(output_path, pagesize=PAGE_SIZE)
    pdf.setTitle(brief.get("brief_title", "AI Brief"))
    pdf.setAuthor("Bhasker Kumar")

    pages = brief.get("pages", [])
    total_pages = len(pages)

    for i, page in enumerate(pages):
        if page.get("page_type") == "cover" or i == 0:
            _build_cover(pdf, brief, story, design, visuals, font, bold,
                         primary, secondary, accent)
        else:
            _build_slide(pdf, page, i + 1, total_pages, design, visuals,
                         font, bold, primary, secondary, accent, bg,
                         text_col, heading_col)
        pdf.showPage()

    pdf.save()
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [PDF] Saved: {output_path} ({size_kb:.0f} KB, {total_pages} slides)")
    return output_path
