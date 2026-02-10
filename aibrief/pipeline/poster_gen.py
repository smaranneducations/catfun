"""Poster/Banner PDF generator — bold, minimal, magazine editorial style.

Fundamentally different from slides:
  - Portrait orientation (612x792, standard letter)
  - Massive typography (72-96pt heroes, 48pt statements)
  - Full-bleed color blocks and images
  - Minimal text — each page is ONE visual statement
  - Extreme whitespace is intentional (it IS the design)
  - Think: Nike poster meets Apple product page meets Vogue editorial
  - 3-5 pages, not 8-10

Page types:
  hero     — full-bleed DALL-E image, massive title overlay
  impact   — solid color background, one centered powerful statement
  stat     — one massive number (120pt) + tiny context
  quote    — dramatic quote with editorial treatment
  closing  — author credit, closing statement, CTA
"""
import random
import re
from pathlib import Path
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from aibrief import config

# Portrait dimensions (standard letter)
W = 612    # 8.5 inches
H = 792    # 11 inches
PAGE_SIZE = (W, H)
M = 50     # margin
CW = W - 2 * M   # content width ~512


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
    if not txt:
        return y
    max_w = max_w or CW
    leading = leading or size * 1.25
    al = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT}.get(align, TA_LEFT)
    safe = str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    style = ParagraphStyle("t", fontName=font, fontSize=size, leading=leading,
                           textColor=color, alignment=al)
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
                "Marquis", "Rivière", "Tempest", "Cristal", "Platine"]
    suffixes = ["Phantom", "Prestige", "Éclat", "Lumière", "Royal",
                "Crown", "Sterling", "Heritage", "Atelier", "Opus"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"


# ═══════════════════════════════════════════════════════════════
#  PAGE BUILDERS
# ═══════════════════════════════════════════════════════════════

def _build_hero(cv, brief, story, design, visuals, font, bold,
                primary, secondary, accent):
    """Hero cover: full-bleed image, dramatic dark overlay, massive title."""
    cover_img = visuals.get("cover", "")
    if cover_img and Path(cover_img).exists():
        _place_image(cv, cover_img, 0, 0, W, H)
        # Heavy vignette overlay — dark at bottom, lighter at top
        for i in range(80):
            t = i / 80
            cv.setFillColor(Color(0, 0, 0, t * 0.85))
            sh = H / 80
            cv.rect(0, i * sh, W, sh + 1, fill=1, stroke=0)
    else:
        # Full primary color
        _gradient(cv, 0, 0, W, H, primary, secondary)

    # Thin accent bar at very top
    cv.setFillColor(accent)
    cv.rect(0, H - 4, W, 4, fill=1, stroke=0)

    # Hero title — MASSIVE (72pt), centered in the lower third
    title = brief.get("brief_title", "AI Brief")
    y = H * 0.38

    # Accent bar above title
    bar_w = 60
    cv.setFillColor(accent)
    cv.rect((W - bar_w) / 2, y + 25, bar_w, 4, fill=1, stroke=0)

    y = _text(cv, title, M, y, bold, 72, white,
              max_w=CW, leading=80, align="center")

    # Subtitle
    subtitle = brief.get("subtitle", "")
    if subtitle:
        y = _text(cv, subtitle, M, y - 12, font, 22, _a(white, 0.75),
                  max_w=CW * 0.8, leading=28, align="center")

    # Author block — prominent, bottom area
    by = H * 0.08
    cv.setFillColor(Color(0, 0, 0, 0.4))
    cv.roundRect(M, by - 15, CW, 60, 6, fill=1, stroke=0)

    _text(cv, "Bhasker Kumar", M, by + 30,
          bold, 28, white, max_w=CW, align="center")

    asst = brief.get("_assistant_name", "Jaguar Phantom")
    _text(cv, f"Assisted by {asst}  |  Multi-Agent AI System",
          M, by, font, 11, _a(white, 0.5), max_w=CW, align="center")

    # Bottom accent
    cv.setFillColor(accent)
    cv.rect(0, 0, W, 4, fill=1, stroke=0)


def _build_impact(cv, page, page_num, design, visuals, font, bold,
                  primary, secondary, accent, bg, text_col, heading_col):
    """Impact statement: bold color background, one massive centered statement."""
    ptype = page.get("page_type", "")

    # Full solid background — bold color choice
    if page_num % 2 == 0:
        # Dark primary background, white text
        cv.setFillColor(primary)
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        txt_color = white
        sub_color = _a(white, 0.6)
    else:
        # Light accent wash background, dark text
        _gradient(cv, 0, 0, W, H, bg, _a(accent, 0.08))
        txt_color = heading_col
        sub_color = _a(text_col, 0.6)

    # Subtle geometric accent — large circle
    cv.setFillColor(_a(accent, 0.06))
    cv.circle(W * 0.7, H * 0.3, 200, fill=1, stroke=0)

    # Accent bar — centered, above statement
    bar_w = 40
    bar_y = H * 0.58
    cv.setFillColor(accent)
    cv.rect((W - bar_w) / 2, bar_y, bar_w, 3, fill=1, stroke=0)

    # Hero statement — 48-56pt, centered
    statement = (page.get("hero_statement", "")
                 or page.get("point", "")
                 or page.get("title", ""))
    y = bar_y - 20
    y = _text(cv, statement, M + 10, y, bold, 48, txt_color,
              max_w=CW - 20, leading=58, align="center")

    # Supporting line — smaller, beneath
    supporting = (page.get("supporting_line", "")
                  or page.get("insight", ""))
    if supporting:
        y = _text(cv, supporting, M + 20, y - 25, font, 18, sub_color,
                  max_w=CW - 40, leading=26, align="center")

    # Visual if available (small, decorative, bottom area)
    vis_path = visuals.get(ptype, "")
    if vis_path and Path(vis_path).exists():
        vis_size = 180
        _place_image(cv, vis_path,
                     (W - vis_size) / 2, H * 0.08,
                     vis_size, vis_size)

    # Page number — very subtle
    _text(cv, f"{page_num}", W - M, 15, font, 9,
          _a(txt_color, 0.2), align="right")


def _build_stat(cv, page, page_num, design, font, bold,
                primary, accent, bg, heading_col, text_col):
    """Stat hero: one MASSIVE number centered, tiny context beneath."""
    # Background — accent-tinted
    cv.setFillColor(bg)
    cv.rect(0, 0, W, H, fill=1, stroke=0)

    # Large accent color block — top 40%
    block_h = H * 0.42
    _gradient(cv, 0, H - block_h, W, block_h, primary, _a(accent, 0.15))

    # The hero number — enormous (96-120pt)
    hero_num = (page.get("hero_number", "")
                or page.get("key_stat", "")
                or page.get("point", ""))
    y = H * 0.52
    y = _text(cv, hero_num, M, y, bold, 108, accent,
              max_w=CW, leading=110, align="center")

    # Label beneath the number
    hero_label = (page.get("hero_label", "")
                  or page.get("key_stat_label", "")
                  or page.get("title", ""))
    if hero_label:
        y = _text(cv, hero_label, M, y - 10, bold, 22, heading_col,
                  max_w=CW, leading=28, align="center")

    # Context line
    context = (page.get("context_line", "")
               or page.get("insight", ""))
    if context:
        y = _text(cv, context, M + 30, y - 25, font, 15,
                  _a(text_col, 0.6), max_w=CW - 60, leading=22, align="center")

    # Thin accent lines
    cv.setFillColor(accent)
    cv.rect(W * 0.35, H * 0.55, W * 0.3, 2, fill=1, stroke=0)

    _text(cv, f"{page_num}", W - M, 15, font, 9,
          _a(text_col, 0.2), align="right")


def _build_quote(cv, page, page_num, design, font, bold,
                 primary, secondary, accent, bg, heading_col, text_col):
    """Quote banner: dramatic editorial quote treatment."""
    # Rich background
    _gradient(cv, 0, 0, W, H, _a(primary, 0.03), bg)

    # Giant quotation mark — decorative, light
    cv.setFillColor(_a(accent, 0.08))
    cv.setFont(bold, 300)
    cv.drawString(M - 20, H * 0.55, "\u201c")

    # The quote — large, centered, elegant
    quote = page.get("quote", page.get("hero_statement", ""))
    y = H * 0.58
    y = _text(cv, f"\u201c{quote}\u201d", M + 30, y, bold, 36, heading_col,
              max_w=CW - 60, leading=48, align="center")

    # Attribution
    attr = page.get("attribution", page.get("quote_attribution", ""))
    if attr:
        y = _text(cv, f"\u2014 {attr}", M, y - 20, font, 16,
                  _a(text_col, 0.5), max_w=CW, leading=22, align="center")

    # Accent line below quote
    cv.setFillColor(accent)
    cv.rect(W * 0.4, y - 15, W * 0.2, 2.5, fill=1, stroke=0)

    _text(cv, f"{page_num}", W - M, 15, font, 9,
          _a(text_col, 0.2), align="right")


def _build_closing(cv, page, page_num, brief, design, font, bold,
                   primary, secondary, accent, bg, heading_col, text_col):
    """Closing page: author prominence, closing statement, CTA."""
    # Gradient background
    _gradient(cv, 0, 0, W, H, primary, _a(secondary, 0.4))

    # Closing statement — large, centered, upper area
    closing = (page.get("closing_statement", "")
               or page.get("hero_statement", "")
               or page.get("point", "The Future Is Being Written Now"))
    y = H * 0.65
    y = _text(cv, closing, M, y, bold, 42, white,
              max_w=CW, leading=52, align="center")

    # CTA
    cta = page.get("cta", page.get("insight", ""))
    if cta:
        y = _text(cv, cta, M + 20, y - 25, font, 18, _a(white, 0.7),
                  max_w=CW - 40, leading=24, align="center")

    # Accent divider
    cv.setFillColor(accent)
    cv.rect(W * 0.3, y - 30, W * 0.4, 3, fill=1, stroke=0)

    # Author block — MASSIVE, the star of this page
    ay = H * 0.22
    _text(cv, "Bhasker Kumar", M, ay, bold, 42, white,
          max_w=CW, align="center")

    asst = brief.get("_assistant_name", "Jaguar Phantom")
    _text(cv, f"Assisted by {asst}", M, ay - 45, font, 16,
          _a(white, 0.6), max_w=CW, align="center")

    _text(cv, "Multi-Agent System  \u2022  Claude  \u2022  Gemini  \u2022  ChatGPT",
          M, ay - 70, font, 10, _a(white, 0.35), max_w=CW, align="center")

    # Bottom accent
    cv.setFillColor(accent)
    cv.rect(0, 0, W, 5, fill=1, stroke=0)
    cv.rect(0, H - 5, W, 5, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════
#  MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_poster(brief: dict, design: dict, story: dict,
                    visuals: dict = None, output_path: str = None) -> str:
    """Generate a poster/banner style PDF — portrait, bold, minimal."""
    if not output_path:
        slug = brief.get("brief_title", "AI_Brief")[:35]
        slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
        output_path = str(config.OUTPUT_DIR / f"{slug}_poster.pdf")

    visuals = visuals or {}
    brief["_assistant_name"] = _luxury_name()

    font, bold_font = "Helvetica", "Helvetica-Bold"
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
    total = len(pages)

    for i, page in enumerate(pages):
        ptype = page.get("page_type", "")

        if ptype == "hero" or i == 0:
            _build_hero(pdf, brief, story, design, visuals, font, bold_font,
                        primary, secondary, accent)
        elif ptype == "stat":
            _build_stat(pdf, page, i + 1, design, font, bold_font,
                        primary, accent, bg, heading_col, text_col)
        elif ptype == "quote":
            _build_quote(pdf, page, i + 1, design, font, bold_font,
                         primary, secondary, accent, bg, heading_col, text_col)
        elif ptype == "closing" or i == total - 1:
            _build_closing(pdf, page, i + 1, brief, design, font, bold_font,
                           primary, secondary, accent, bg, heading_col, text_col)
        else:
            # Default: impact statement
            _build_impact(pdf, page, i + 1, design, visuals, font, bold_font,
                          primary, secondary, accent, bg, text_col, heading_col)

        pdf.showPage()

    pdf.save()
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [Poster] Saved: {output_path} ({size_kb:.0f} KB, {total} pages)")
    return output_path
