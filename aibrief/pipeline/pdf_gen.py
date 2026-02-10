"""High-end PDF generator — luxury editorial design.

Every page has visuals. Layout is balanced like a luxury brand website.
Design algorithm changes every time. Never looks like a text document.
Think Hermès editorial meets Bloomberg Businessweek.
"""
import math
import random
import re
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from aibrief import config

W, H = letter  # 612 x 792
M = 48


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


def _a(base: HexColor, alpha: float) -> Color:
    return Color(base.red, base.green, base.blue, alpha)


def _gradient(c, x, y, w, h, c1, c2, steps=50, horiz=False):
    if horiz:
        sw = w / steps
        for i in range(steps):
            t = i / steps
            c.setFillColor(Color(
                c1.red + (c2.red - c1.red) * t,
                c1.green + (c2.green - c1.green) * t,
                c1.blue + (c2.blue - c1.blue) * t))
            c.rect(x + i * sw, y, sw + 1, h, fill=1, stroke=0)
    else:
        sh = h / steps
        for i in range(steps):
            t = i / steps
            c.setFillColor(Color(
                c1.red + (c2.red - c1.red) * t,
                c1.green + (c2.green - c1.green) * t,
                c1.blue + (c2.blue - c1.blue) * t))
            c.rect(x, y + i * sh, w, sh + 1, fill=1, stroke=0)


def _text(c, txt, x, y, font, size, color, max_w=None, leading=None,
          align="left") -> float:
    if not txt:
        return y
    max_w = max_w or (W - 2 * M)
    leading = leading or size * 1.5
    al = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT,
          "justify": TA_JUSTIFY}.get(align, TA_LEFT)
    safe = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    style = ParagraphStyle("t", fontName=font, fontSize=size, leading=leading,
                           textColor=color, alignment=al)
    p = Paragraph(safe, style)
    pw, ph = p.wrap(max_w, H)
    if y - ph < 30:
        y = H - M
    p.drawOn(c, x, y - ph)
    return y - ph


def _place_image(c, img_path: str, x: float, y: float, w: float, h: float):
    """Place an image on the canvas, fitting within bounds."""
    if not img_path or not Path(img_path).exists():
        return
    try:
        c.drawImage(img_path, x, y, width=w, height=h,
                    preserveAspectRatio=True, mask="auto")
    except Exception as e:
        print(f"  [PDF] Image error: {e}")


# ═══════════════════════════════════════════════════════════════
#  COVER PAGE — full-bleed hero image + title overlay
# ═══════════════════════════════════════════════════════════════

def _build_cover(pdf, brief, story, design, visuals, font, bold,
                 primary, secondary, accent):
    """Cover: hero image fills page, dark overlay, title on top."""
    # Hero image — full bleed
    cover_img = visuals.get("cover", "")
    if cover_img and Path(cover_img).exists():
        _place_image(pdf, cover_img, 0, 0, W, H)
        # Dark overlay for text readability
        pdf.setFillColor(Color(0, 0, 0, 0.55))
        pdf.rect(0, 0, W, H, fill=1, stroke=0)
    else:
        _gradient(pdf, 0, 0, W, H, primary, secondary)

    # Accent line at top
    pdf.setFillColor(accent)
    pdf.rect(0, H - 4, W, 4, fill=1, stroke=0)

    # Title block — center-left, golden ratio position
    y = H * 0.58

    # Accent bar before title
    pdf.setFillColor(accent)
    pdf.rect(M, y + 15, 60, 3, fill=1, stroke=0)

    # Title
    y = _text(pdf, brief.get("brief_title", "AI Brief"), M, y,
              bold, 38, white, max_w=W * 0.7, leading=46)

    # Subtitle
    y = _text(pdf, brief.get("subtitle", ""), M, y - 10,
              font, 16, _a(white, 0.75), max_w=W * 0.65)

    # Divider
    pdf.setStrokeColor(_a(white, 0.2))
    pdf.setLineWidth(0.5)
    pdf.line(M, y - 15, M + 200, y - 15)

    # Author block — bottom
    by = H * 0.12
    _text(pdf, "Bhasker Kumar", M, by, bold, 13, white)
    asst = brief.get("_assistant_name", "Jaguar Phantom")
    _text(pdf, f"Assisted by {asst}", M, by - 18, font, 10, _a(white, 0.5))
    _text(pdf, "Multi-Agent System \u2022 Claude \u2022 Gemini \u2022 ChatGPT",
          M, by - 34, font, 8, _a(white, 0.35))
    _text(pdf, story.get("date", "February 2026"), M, by - 50,
          font, 9, _a(white, 0.4))

    # Bottom accent strip
    pdf.setFillColor(accent)
    pdf.rect(0, 0, W, 5, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════
#  CONTENT PAGE — balanced layout with visual
# ═══════════════════════════════════════════════════════════════

def _build_content(pdf, page, page_num, design, visuals, font, bold,
                   primary, secondary, accent, bg, text_col, heading_col):
    """Content page: visual on one side, text on other, balanced."""
    ptype = page.get("page_type", "")
    title = page.get("title", "")
    body = page.get("body", "")
    quote = page.get("quote", "")
    quote_attr = page.get("quote_attribution", "")
    vis_path = visuals.get(ptype, "")

    # Background
    pdf.setFillColor(bg)
    pdf.rect(0, 0, W, H, fill=1, stroke=0)

    # Top bar
    pdf.setFillColor(primary)
    pdf.rect(0, H - 5, W, 5, fill=1, stroke=0)

    # Bottom accent
    pdf.setFillColor(accent)
    pdf.rect(0, 0, W, 3, fill=1, stroke=0)

    # Layout varies by page — alternate visual position
    visual_top = page_num % 2 == 0  # Even pages: visual on top; odd: visual below text

    # ── Section label ──
    y = H - 35
    label = ptype.upper().replace("_", " ")
    _text(pdf, label, M, y, bold, 8, _a(accent, 0.55))

    # ── Accent + Title ──
    y -= 8
    pdf.setFillColor(accent)
    pdf.rect(M, y + 2, 45, 2.5, fill=1, stroke=0)
    y = _text(pdf, title, M, y - 8, bold, 24, heading_col,
              max_w=W - 2 * M, leading=30)

    if visual_top and vis_path:
        # ── VISUAL ON TOP ──
        y -= 12
        vis_h = 180
        _place_image(pdf, vis_path, M, y - vis_h, W - 2 * M, vis_h)
        y -= (vis_h + 15)

        # Body text below visual
        y = _text(pdf, body, M, y, font, 11.5, text_col,
                  max_w=W - 2 * M, leading=19, align="justify")

        # Quote at bottom
        if quote:
            y = _draw_quote(pdf, quote, quote_attr, y - 20,
                            accent, heading_col, text_col, font, bold)

    else:
        # ── TEXT FIRST, VISUAL BELOW ──
        y -= 15
        y = _text(pdf, body, M, y, font, 11.5, text_col,
                  max_w=W - 2 * M, leading=19, align="justify")

        # Quote
        if quote:
            y = _draw_quote(pdf, quote, quote_attr, y - 18,
                            accent, heading_col, text_col, font, bold)

        # Visual below text
        if vis_path:
            y -= 15
            remaining = y - 40
            vis_h = min(remaining, 200)
            if vis_h > 80:
                _place_image(pdf, vis_path, M, y - vis_h, W - 2 * M, vis_h)

    # ── Page number + footer ──
    pdf.setStrokeColor(_a(text_col, 0.08))
    pdf.setLineWidth(0.5)
    pdf.line(M, 22, W - M, 22)
    _text(pdf, f"{page_num}", W - M, 10, font, 8, _a(text_col, 0.3), align="right")
    _text(pdf, "AI BRIEF \u2022 Bhasker Kumar", M, 10, bold, 7, _a(text_col, 0.15))


def _draw_quote(pdf, quote, attribution, y, accent, heading_col, text_col,
                font, bold) -> float:
    """Draw a luxury-styled pull quote."""
    if not quote:
        return y

    box_x = M
    box_w = W - 2 * M

    # Light accent background
    pdf.saveState()
    pdf.setFillColor(_a(accent, 0.06))
    pdf.roundRect(box_x, y - 75, box_w, 70, 5, fill=1, stroke=0)
    pdf.restoreState()

    # Left accent bar
    pdf.setFillColor(accent)
    pdf.rect(box_x, y - 75, 3, 70, fill=1, stroke=0)

    # Quote text
    y2 = _text(pdf, f"\u201c{quote}\u201d", box_x + 18, y - 10,
               bold, 13, heading_col, max_w=box_w - 30, leading=18)

    if attribution:
        y2 = _text(pdf, f"\u2014 {attribution}", box_x + 18, y2 - 4,
                   font, 9, _a(text_col, 0.5), max_w=box_w - 30)

    return min(y2, y - 80)


# ═══════════════════════════════════════════════════════════════
#  LUXURY ASSISTANT NAME GENERATOR
# ═══════════════════════════════════════════════════════════════

def _generate_luxury_name() -> str:
    """Generate a luxury brand-style assistant name."""
    prefixes = ["Jaguar", "Aurèle", "Maison", "Noir", "Velvet",
                "Luxe", "Sovereign", "Obsidian", "Ivory", "Sable",
                "Argent", "Opale", "Ébène", "Cristal", "Platine"]
    suffixes = ["Phantom", "Noir", "Prestige", "Éclat", "Lumière",
                "Royal", "Crown", "Sterling", "Heritage", "Atelier",
                "Legacy", "Prism", "Soleil", "Crest", "Bespoke"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def generate_pdf(brief: dict, design: dict, story: dict,
                 visuals: dict = None, output_path: str = None) -> str:
    """Generate the luxury thought-leadership PDF with visuals."""
    if not output_path:
        slug = brief.get("brief_title", "AI_Brief")[:35]
        slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
        output_path = str(config.OUTPUT_DIR / f"{slug}.pdf")

    visuals = visuals or {}

    # Inject luxury assistant name
    brief["_assistant_name"] = _generate_luxury_name()

    # Fonts
    font, bold = "Helvetica", "Helvetica-Bold"

    # Colors
    primary = _hex(design.get("primary_color", "#0f1729"))
    secondary = _hex(design.get("secondary_color", "#1e3a5f"))
    accent = _hex(design.get("accent_color", "#00d4aa"))
    bg = _hex(design.get("background_color", "#f8f8fa"))
    text_col = _hex(design.get("text_color", "#2d2d3a"))
    heading_col = _hex(design.get("heading_color", "#0f1729"))

    pdf = canvas.Canvas(output_path, pagesize=letter)
    pdf.setTitle(brief.get("brief_title", "AI Brief"))
    pdf.setAuthor("Bhasker Kumar")

    pages = brief.get("pages", [])

    for i, page in enumerate(pages):
        ptype = page.get("page_type", "")

        if ptype == "cover" or i == 0:
            _build_cover(pdf, brief, story, design, visuals, font, bold,
                         primary, secondary, accent)
        else:
            _build_content(pdf, page, i + 1, design, visuals, font, bold,
                           primary, secondary, accent, bg, text_col, heading_col)

        pdf.showPage()

    pdf.save()
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [PDF] Saved: {output_path} ({size_kb:.0f} KB, {len(pages)} pages)")
    return output_path
