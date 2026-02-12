"""Poster + Agent Credits + Run Info + Decision Architecture + Debates PDF Generator.

Output structure:
  Section 1 — POSTER:
    Page 1: Cover / Landing (massive title, prominent author names)
    Page 2: News Summary (original headline, publisher, link, 6 bullet points)
    Pages 3-6: Content (5 points each, background + foreground images, poster format)

  Section 2 — AGENT CREDITS:
    All agents: "Codename — Role" in large readable text

  Section 3 — RUN INFO:
    Topic, Style, Palette, Font, Design Name, Validation score

  Section 4 — DECISION ARCHITECTURE:
    Readable list format: each phase with one-liner of what happened

  Section 5 — DEBATES & JUDGMENTS:
    Each debate pair: persona images, round-by-round scores, demands, verdicts
"""
import math
import random
import re
import json
from pathlib import Path

from reportlab.lib.colors import HexColor, Color, white
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from aibrief import config
from aibrief.pipeline.design_catalog import (
    register_font, lookup_style, lookup_palette,
)

# ═══════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════

W = 612
H = 792
PAGE_SIZE = (W, H)
M = 50
CW = W - 2 * M


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


def _measure_text(txt, font, size, max_w=None, leading=None) -> float:
    """Measure the height a text block will consume WITHOUT drawing it."""
    if not txt:
        return 0
    max_w = max_w or CW
    leading = leading or size * 1.25
    safe = (str(txt).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))
    style = ParagraphStyle("m", fontName=font, fontSize=size, leading=leading)
    p = Paragraph(safe, style)
    pw, ph = p.wrap(max_w, H)
    return ph


def _place_image(cv, img_path: str, x, y, w, h):
    if not img_path or not Path(img_path).exists():
        return
    try:
        cv.drawImage(img_path, x, y, width=w, height=h,
                     preserveAspectRatio=True, mask="auto")
    except Exception as e:
        print(f"  [Poster] Image error: {e}")


def _agent_name() -> str:
    """Fixed agent author name."""
    return "Orion Cael"


# ═══════════════════════════════════════════════════════════════
#  STYLE DECORATIONS (light overlay patterns)
# ═══════════════════════════════════════════════════════════════

def _style_decoration(cv, style_id: str, accent, secondary, page_num: int):
    if style_id == "anime_pop":
        cv.setStrokeColor(_a(accent, 0.12))
        cv.setLineWidth(3)
        for i in range(0, W + H, 40):
            cv.line(i, H, i - H, 0)
        cv.setFillColor(_a(accent, 0.06))
        cv.circle(W * 0.85, H * 0.15, 80, fill=1, stroke=0)
    elif style_id == "indian_classical":
        cx, cy = W * 0.5, H * 0.5
        for r in range(50, 350, 40):
            cv.setStrokeColor(_a(accent, 0.04))
            cv.setLineWidth(1)
            cv.circle(cx, cy, r, fill=0, stroke=1)
    elif style_id == "gothic_editorial":
        cv.setFillColor(_a(accent, 0.05))
        p = cv.beginPath()
        p.moveTo(0, H)
        p.lineTo(W / 2, H - 120)
        p.lineTo(W, H)
        p.close()
        cv.drawPath(p, fill=1, stroke=0)
    elif style_id == "heavy_metal":
        cv.setStrokeColor(_a(accent, 0.08))
        cv.setLineWidth(2)
        for i in range(8):
            x1 = random.randint(0, W)
            cv.line(x1, H, x1 + 200, 0)
    elif style_id == "art_deco":
        cx = W / 2
        cv.setStrokeColor(_a(accent, 0.1))
        cv.setLineWidth(1.5)
        for angle in range(-60, 61, 12):
            rad = math.radians(angle)
            cv.line(cx, H, cx + 300 * math.sin(rad), H - 300 * math.cos(rad))
    elif style_id == "swiss_international":
        cv.setFillColor(_a(accent, 0.06))
        for gx in range(int(M), int(W - M), 30):
            for gy in range(int(M), int(H - M), 30):
                cv.circle(gx, gy, 1.5, fill=1, stroke=0)
    elif style_id == "african_futurism":
        cv.setFillColor(_a(accent, 0.06))
        for i in range(0, W, 60):
            p = cv.beginPath()
            p.moveTo(i, 0)
            p.lineTo(i + 30, 50)
            p.lineTo(i + 60, 0)
            p.close()
            cv.drawPath(p, fill=1, stroke=0)
    elif style_id == "french_haute_couture":
        cv.setStrokeColor(_a(accent, 0.04))
        cv.setLineWidth(0.5)
        for i in range(-H, W + H, 25):
            cv.line(i, H, i + H, 0)
    elif style_id == "cyberpunk_noir":
        for _ in range(6):
            bx = random.randint(0, W - 80)
            by = random.randint(0, H - 15)
            cv.setFillColor(_a(accent, 0.08))
            cv.rect(bx, by, random.randint(40, 120), random.randint(3, 10),
                    fill=1, stroke=0)
        cv.setStrokeColor(_a(accent, 0.05))
        cv.setLineWidth(0.5)
        for y_pos in range(0, H, 4):
            cv.line(0, y_pos, W, y_pos)
    elif style_id == "ancient_greek":
        cv.setStrokeColor(_a(accent, 0.06))
        cv.setLineWidth(2)
        cv.line(M - 10, M, M - 10, H - M)
        cv.line(W - M + 10, M, W - M + 10, H - M)
    elif style_id == "nordic_clean":
        cv.setFillColor(_a(accent, 0.03))
        cv.circle(W * 0.8, H * 0.7, 150, fill=1, stroke=0)
        cv.circle(W * 0.2, H * 0.3, 100, fill=1, stroke=0)
    else:
        cv.setFillColor(_a(accent, 0.04))
        cv.circle(W * 0.7, H * 0.3, 180, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════
#  SECTION 1A: COVER PAGE
# ═══════════════════════════════════════════════════════════════

def _build_cover(cv, brief, story, design, visuals, font, bold,
                 colors, style_id):
    primary, secondary, accent = colors["primary"], colors["secondary"], colors["accent"]
    cover_img = (visuals or {}).get("cover", "")
    if cover_img and Path(cover_img).exists():
        _place_image(cv, cover_img, 0, 0, W, H)
        for i in range(80):
            t = i / 80
            cv.setFillColor(Color(0, 0, 0, t * 0.85))
            cv.rect(0, i * (H / 80), W, H / 80 + 1, fill=1, stroke=0)
    else:
        _gradient(cv, 0, 0, W, H, primary, secondary)

    _style_decoration(cv, style_id, accent, secondary, 0)
    cv.setFillColor(accent)
    cv.rect(0, H - 5, W, 5, fill=1, stroke=0)

    # ──────────────────────────────────────────────────
    #  CONTAINER-BASED LAYOUT (measure → stack → draw)
    # ──────────────────────────────────────────────────
    #  Three containers stacked vertically:
    #    [1] TITLE  (big bold text)
    #    [2] SUBTITLE (smaller light text)
    #    [3] AUTHOR BOX (name + assistant + tagline)
    #  Gaps between containers: 30pt, 40pt
    #  The whole stack is vertically centered on page.
    # ──────────────────────────────────────────────────

    title = brief.get("brief_title", "AI Brief")
    subtitle = brief.get("subtitle", "")
    asst = brief.get("_assistant_name", _agent_name())

    GAP_TITLE_SUB = 30     # gap between title and subtitle
    GAP_SUB_AUTHOR = 40    # gap between subtitle and author box
    AUTHOR_BOX_PAD = 15    # padding inside author box (top & bottom)

    # Measure author box contents to size the box correctly
    name_h = _measure_text("Bhasker Kumar", bold, 36, max_w=CW)
    asst_line = f"with {asst}, The Agentic AI"
    asst_h = _measure_text(asst_line, bold, 19, max_w=CW)
    tag_line = "Multi-Agent AI  \u2022  Search Grounding  \u2022  Claude  \u2022  Gemini  \u2022  ChatGPT"
    tag_h = _measure_text(tag_line, font, 12, max_w=CW)
    AUTHOR_INNER_GAP = 8   # gap between lines inside box
    AUTHOR_BOX_H = (AUTHOR_BOX_PAD + name_h + AUTHOR_INNER_GAP
                    + asst_h + AUTHOR_INNER_GAP + tag_h + AUTHOR_BOX_PAD)

    # 1. Measure each container's height
    title_h = _measure_text(title, bold, 64, max_w=CW, leading=72)
    sub_h = _measure_text(subtitle, font, 18, max_w=CW * 0.85,
                          leading=24) if subtitle else 0

    # 2. Total stack height
    total = title_h
    if sub_h:
        total += GAP_TITLE_SUB + sub_h
    total += GAP_SUB_AUTHOR + AUTHOR_BOX_H

    # 3. Center the stack vertically (with slight upward bias)
    top_y = (H + total) / 2 + 30       # top of title block
    top_y = min(top_y, H - 50)         # don't clip top edge

    # 4. Draw: Title (full width, truly centered)
    y = top_y
    cv.setFillColor(accent)
    cv.rect((W - 60) / 2, y + 8, 60, 4, fill=1, stroke=0)  # accent bar
    y = _text(cv, title, M, y, bold, 64, white,
              max_w=CW, leading=72, align="center")

    # 5. Draw: Subtitle (with gap, centered on page)
    if subtitle:
        y -= GAP_TITLE_SUB
        sub_w = CW * 0.85
        sub_x = M + (CW - sub_w) / 2   # center the narrower block
        y = _text(cv, subtitle, sub_x, y, font, 18, _a(white, 0.65),
                  max_w=sub_w, leading=24, align="center")

    # 6. Draw: Author box (with gap, sized to fit contents)
    author_y = y - GAP_SUB_AUTHOR - AUTHOR_BOX_H
    author_y = max(author_y, 20)        # safety floor
    cv.setFillColor(Color(0, 0, 0, 0.45))
    cv.roundRect(M - 10, author_y, CW + 20, AUTHOR_BOX_H, 8,
                 fill=1, stroke=0)
    # Stack inside box: name → asst → tagline (top-down from box top)
    iy = author_y + AUTHOR_BOX_H - AUTHOR_BOX_PAD
    iy = _text(cv, "Bhasker Kumar", M, iy, bold, 36, white,
               max_w=CW, align="center")
    iy -= AUTHOR_INNER_GAP
    iy = _text(cv, asst_line, M, iy, bold, 19, _a(accent, 0.9),
               max_w=CW, align="center")
    iy -= AUTHOR_INNER_GAP
    _text(cv, tag_line, M, iy, font, 12, _a(white, 0.4),
          max_w=CW, align="center")

    cv.setFillColor(accent)
    cv.rect(0, 0, W, 5, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════
#  SECTION 1B: NEWS SUMMARY PAGE (page 2)
# ═══════════════════════════════════════════════════════════════

def _build_news_summary(cv, page, story, design, visuals, font, bold,
                        colors, style_id, page_idx):
    primary = colors["primary"]
    secondary = colors["secondary"]
    accent = colors["accent"]

    # Background image
    bg_img = (visuals or {}).get(f"bg_{page_idx}", "")
    if bg_img and Path(bg_img).exists():
        _place_image(cv, bg_img, 0, 0, W, H)
        cv.setFillColor(Color(0, 0, 0, 0.60))
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        txt_c = white
        sub_c = _a(white, 0.75)
    else:
        _gradient(cv, 0, 0, W, H, primary, _a(secondary, 0.6))
        txt_c = white
        sub_c = _a(white, 0.65)

    _style_decoration(cv, style_id, accent, secondary, 1)

    # Title bar — bold accent stripe
    y = H - M
    cv.setFillColor(accent)
    cv.rect(M, y - 2, CW, 4, fill=1, stroke=0)
    y -= 12
    y = _text(cv, "THE SOURCE", M, y, bold, 16, accent, max_w=CW)
    y -= 12

    # Original news headline — BIG and BOLD
    headline = (page.get("news_headline", "") or
                story.get("exact_news_headline", "") or
                story.get("headline", ""))
    # Draw headline twice for extra boldness (offset shadow trick)
    y = _text(cv, headline, M, y, bold, 30, txt_c, max_w=CW, leading=36)
    y -= 14

    # Publisher and date
    publisher = (page.get("news_publisher", "") or
                 story.get("publisher", ""))
    date = story.get("date", "")
    pub_line = f"Published by {publisher}" if publisher else ""
    if date:
        pub_line += f"  \u2022  {date}" if pub_line else date
    if pub_line:
        y = _text(cv, pub_line, M, y, bold, 12, _a(accent, 0.9), max_w=CW)
        y -= 10

    # ── SOURCE REFERENCE BOX (black bg, white text, underlined link) ──
    url = (page.get("news_url", "") or story.get("news_url", ""))
    if url:
        box_h = 42
        box_y = y - box_h
        # Black reference box
        cv.setFillColor(Color(0, 0, 0, 0.85))
        cv.roundRect(M, box_y, CW, box_h, 4, fill=1, stroke=0)

        # "SOURCE" label
        _text(cv, "\u25b8  ORIGINAL SOURCE", M + 12, y - 14, bold, 9,
              _a(white, 0.6), max_w=CW - 24)

        # Underlined clickable URL (opens in new tab)
        url_y = y - 30
        # Draw text
        url_display = url if len(url) <= 75 else url[:72] + "..."
        _text(cv, url_display, M + 12, url_y, font, 10, white,
              max_w=CW - 24)
        # Draw underline
        url_w = min(cv.stringWidth(url_display, font, 10), CW - 24)
        cv.setStrokeColor(white)
        cv.setLineWidth(0.5)
        cv.line(M + 12, url_y - 2, M + 12 + url_w, url_y - 2)
        # Clickable link rect — PDF viewers open URLs in default browser
        link_rect = (M + 12, url_y - 4, M + 12 + url_w, url_y + 12)
        cv.linkURL(url, link_rect, relative=0, thickness=0)

        y = box_y - 14
    else:
        y -= 14

    # Divider
    cv.setFillColor(accent)
    cv.rect(M, y, CW * 0.3, 2, fill=1, stroke=0)
    y -= 18

    # 6 summary bullet points
    y = _text(cv, "Key Facts", M, y, bold, 16, accent, max_w=CW)
    y -= 8

    points = (page.get("summary_points", []) or
              story.get("summary_points", []))
    for i, pt in enumerate(points[:6]):
        bullet = f"\u25b8  {pt}"
        y = _text(cv, bullet, M + 8, y, font, 13, txt_c,
                  max_w=CW - 16, leading=18)
        y -= 8

    # Foreground image in bottom-right
    fg_img = (visuals or {}).get(f"fg_{page_idx}", "")
    if fg_img and Path(fg_img).exists():
        img_size = 180
        _place_image(cv, fg_img,
                     W - M - img_size, M + 10,
                     img_size, img_size)

    # Page number
    _text(cv, "2", W - M, 15, font, 9, _a(txt_c, 0.25), align="right")


# ═══════════════════════════════════════════════════════════════
#  SECTION 1C: CONTENT PAGES (5 points each, dual images)
# ═══════════════════════════════════════════════════════════════

def _build_content_page(cv, page, page_num, page_idx, design, visuals,
                        font, bold, colors, style_id):
    """Build a content page with 5 bullet points, background + foreground image."""
    primary = colors["primary"]
    secondary = colors["secondary"]
    accent = colors["accent"]

    ptype = page.get("page_type", "impact")

    # ── BACKGROUND IMAGE (subtle, low-contrast) ──
    bg_img = (visuals or {}).get(f"bg_{page_idx}", "")
    if bg_img and Path(bg_img).exists():
        _place_image(cv, bg_img, 0, 0, W, H)
        # Dark overlay for text readability
        cv.setFillColor(Color(0, 0, 0, 0.55))
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        txt_c = white
        sub_c = _a(white, 0.70)
        num_c = _a(accent, 1.0)
    elif page_num % 2 == 0:
        _gradient(cv, 0, 0, W, H, primary, _a(secondary, 0.6))
        txt_c = white
        sub_c = _a(white, 0.65)
        num_c = accent
    else:
        cv.setFillColor(colors["bg"])
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        txt_c = colors["heading"]
        sub_c = _a(colors["text"], 0.6)
        num_c = accent

    _style_decoration(cv, style_id, accent, secondary, page_num)

    # ── PAGE TITLE ──
    page_title = page.get("page_title", "")
    y = H - M

    if ptype == "stat":
        # Show hero number prominently
        hero_num = (page.get("hero_number", "") or page.get("key_stat", ""))
        hero_label = (page.get("hero_label", "") or page.get("key_stat_label", ""))
        if hero_num:
            y = _text(cv, hero_num, M, y, bold, 72, num_c,
                      max_w=CW, leading=76, align="center")
        if hero_label:
            y = _text(cv, hero_label, M, y - 4, bold, 16, txt_c,
                      max_w=CW, align="center")
            y -= 10
    elif ptype == "quote":
        quote = page.get("quote", "")
        attr = page.get("attribution", "")
        if quote:
            cv.setFillColor(_a(accent, 0.06))
            cv.setFont(bold, 200)
            cv.drawString(M - 10, y - 40, "\u201c")
            y = _text(cv, f"\u201c{quote}\u201d", M + 10, y, bold, 24, txt_c,
                      max_w=CW - 20, leading=32, align="center")
        if attr:
            y = _text(cv, f"\u2014 {attr}", M, y - 6, font, 13, sub_c,
                      max_w=CW, align="center")
            y -= 10
    else:
        if page_title:
            cv.setFillColor(accent)
            cv.rect(M, y - 2, 40, 3, fill=1, stroke=0)
            y -= 8
            y = _text(cv, page_title, M, y, bold, 28, txt_c,
                      max_w=CW, leading=34)
            y -= 12

    # ── DIVIDER ──
    cv.setFillColor(accent)
    cv.rect(M, y, CW * 0.25, 2, fill=1, stroke=0)
    y -= 16

    # ── 5 BULLET POINTS ──
    points = page.get("points", [])
    for i, pt in enumerate(points[:5]):
        if isinstance(pt, dict):
            statement = pt.get("point", "")
            detail = pt.get("detail", "")
        else:
            statement = str(pt)
            detail = ""

        # Bold bullet number + statement
        bullet_text = f"{i + 1}.  {statement}"
        y = _text(cv, bullet_text, M + 8, y, bold, 14, txt_c,
                  max_w=CW - 16, leading=18)
        # Detail line
        if detail:
            y = _text(cv, detail, M + 28, y - 2, font, 11, sub_c,
                      max_w=CW - 40, leading=15)
        y -= 12  # gap between points

    # ── FOREGROUND IMAGE (prominent, contrasting) ──
    fg_img = (visuals or {}).get(f"fg_{page_idx}", "")
    if fg_img and Path(fg_img).exists():
        # Place foreground image in the remaining bottom area
        remaining_h = y - M
        if remaining_h > 100:
            img_h = min(remaining_h - 20, 220)
            img_w = img_h  # square
            img_x = (W - img_w) / 2
            img_y = M + 10
            _place_image(cv, fg_img, img_x, img_y, img_w, img_h)

    # Page number
    _text(cv, str(page_num), W - M, 15, font, 9, _a(txt_c, 0.25),
          align="right")


# ═══════════════════════════════════════════════════════════════
#  SECTION 2: AGENT CREDITS (big text, role next to name)
# ═══════════════════════════════════════════════════════════════

def _build_agent_credits(cv, agents_info, font, bold, colors, style_id,
                         persona_paths=None):
    if not agents_info:
        return

    ppaths = persona_paths or {}
    accent = colors["accent"]
    icon_size = 42
    agents_per_page = 5  # fewer per page to fit icons
    pages = [agents_info[i:i + agents_per_page]
             for i in range(0, len(agents_info), agents_per_page)]

    for pi, page_agents in enumerate(pages):
        cv.setFillColor(_hex("#f8f6f1"))
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        cv.setFillColor(accent)
        cv.rect(0, H - 4, W, 4, fill=1, stroke=0)

        y = H - M
        if pi == 0:
            y = _text(cv, "The Intelligence Behind This Brief", M, y,
                      bold, 28, _hex("#1a1a2e"), max_w=CW, align="center")
            y =     _text(cv, "Multi-Agent AI System with Search Grounding  \u2022  Claude  \u2022  Gemini  \u2022  ChatGPT",
                      M, y - 6, font, 11, _hex("#888888"),
                      max_w=CW, align="center")
            y -= 18
        else:
            y = _text(cv, "Agent Roster (continued)", M, y,
                      bold, 22, _hex("#1a1a2e"), max_w=CW, align="center")
            y -= 12

        for agent in page_agents:
            codename = agent.get("codename", "?")
            agent_name = agent.get("name", "")
            role = agent.get("role", "")
            mandate = agent.get("mandate", "")[:120]
            if len(agent.get("mandate", "")) > 120:
                mandate += "..."

            # Resolve codename for persona image lookup
            img_code = codename
            if not img_code or img_code not in ppaths:
                img_code = _CONFIG_NAME_TO_CODENAME.get(agent_name, "")

            # Text positioning: shift right if we have an icon
            has_icon = img_code and img_code in ppaths
            text_left = M + icon_size + 14 if has_icon else M + 14
            text_w = CW - icon_size - 20 if has_icon else CW - 20

            # Persona icon
            if has_icon:
                _place_image(cv, ppaths[img_code],
                             M, y - icon_size - 8, icon_size, icon_size)

            # Accent bar
            cv.setFillColor(accent)
            cv.rect(text_left - 6, y - icon_size - 8, 3,
                    icon_size + 4 if has_icon else 62, fill=1, stroke=0)

            header = f"{codename} \u2014 {role}"
            y_text = _text(cv, header, text_left, y, bold, 14,
                           _hex("#1a1a2e"), max_w=text_w, leading=17)
            y_text = _text(cv, mandate, text_left, y_text - 3, font, 9,
                           _hex("#666666"), max_w=text_w, leading=11)

            y = min(y_text, y - icon_size - 14) if has_icon else y_text
            y -= 8
            cv.setStrokeColor(_hex("#e0ddd5"))
            cv.setLineWidth(0.5)
            cv.line(M, y, W - M, y)
            y -= 8

        _text(cv, f"Agent Credits  \u2022  {pi + 1}/{len(pages)}",
              M, 18, font, 8, _hex("#aaaaaa"), max_w=CW, align="center")
        cv.showPage()


# ═══════════════════════════════════════════════════════════════
#  SECTION 3: RUN INFO
# ═══════════════════════════════════════════════════════════════

def _build_run_info(cv, design, story, strategy, tracer_flow,
                    font, bold, colors):
    accent = colors["accent"]

    cv.setFillColor(_hex("#f8f6f1"))
    cv.rect(0, 0, W, H, fill=1, stroke=0)
    cv.setFillColor(accent)
    cv.rect(0, H - 4, W, 4, fill=1, stroke=0)

    y = H - M
    y = _text(cv, "Run Configuration", M, y, bold, 30,
              _hex("#1a1a2e"), max_w=CW, align="center")
    y -= 20

    tf = tracer_flow or {}
    ko = tf.get("key_outputs", {})
    style_obj = lookup_style(design.get("style_id", ""))
    palette_obj = lookup_palette(design.get("palette_id", ""))

    items = [
        ("Topic", story.get("headline", "N/A")),
        ("Category", story.get("news_category", ko.get("content_type", "N/A"))),
        ("Content Type", (strategy or {}).get("content_type", ko.get("content_type", "N/A"))),
        ("Detected Emotion", design.get("emotion", "N/A")),
        ("Style", f"{style_obj['name']} ({design.get('style_id', '')})"),
        ("Palette", f"{palette_obj['name']} ({design.get('palette_id', '')})"),
        ("Font", design.get("font_id", "N/A")),
        ("Design Name", design.get("design_name", "N/A")),
        ("Imagen Style", design.get("imagen_style", "N/A")),
        ("World Mood", ko.get("world_mood", "N/A")),
        ("Validation Score", f"{ko.get('validation_score', '?')} / 100"),
        ("Run ID", tf.get("run_id", "N/A")),
        ("Duration", f"{tf.get('total_duration', 0):.0f} seconds"),
        ("Total Agents", str(tf.get("total_agents", "?"))),
        ("Total Debates", str(tf.get("total_debates", "?"))),
    ]

    for label, value in items:
        _text(cv, label, M + 10, y, font, 12, _hex("#888888"), max_w=120)
        _text(cv, value, M + 140, y, bold, 14, _hex("#1a1a2e"),
              max_w=CW - 150, leading=18)
        y -= 38
        cv.setStrokeColor(_hex("#e8e5de"))
        cv.setLineWidth(0.5)
        cv.line(M + 10, y + 12, W - M, y + 12)

    cv.showPage()


# ═══════════════════════════════════════════════════════════════
#  SECTION 4: DECISION ARCHITECTURE (readable list)
# ═══════════════════════════════════════════════════════════════

_PHASE_COLORS = {
    "discovery": "#3498db",
    "strategy": "#2ecc71",
    "topic": "#9b59b6",
    "design": "#e67e22",
    "analysis": "#e74c3c",
    "debate": "#c0392b",
    "editorial": "#f39c12",
    "synthesis": "#1abc9c",
    "quality": "#2c3e50",
    "publishing": "#e91e63",
}


def _build_mind_map(cv, tracer_flow, topic, font, bold, colors):
    accent = colors["accent"]

    cv.setFillColor(_hex("#faf9f5"))
    cv.rect(0, 0, W, H, fill=1, stroke=0)
    cv.setFillColor(accent)
    cv.rect(0, H - 4, W, 4, fill=1, stroke=0)

    y = H - M
    y = _text(cv, "Decision Architecture", M, y, bold, 30,
              _hex("#1a1a2e"), max_w=CW, align="center")
    y = _text(cv, "How 15+ AI Agents Created This Poster", M, y - 4,
              font, 12, _hex("#888888"), max_w=CW, align="center")
    y -= 20

    tf = tracer_flow or {}
    ko = tf.get("key_outputs", {})

    phases = [
        {
            "label": "Phase 0 \u2014 WORLD PULSE",
            "agents": "Aria",
            "detail": f"Scanned global sentiment \u2192 Mood: {ko.get('world_mood', 'normal')}",
            "color": _PHASE_COLORS["discovery"],
        },
        {
            "label": "Phase 1 \u2014 CONTENT STRATEGY",
            "agents": "Marcus",
            "detail": f"Chose content type \u2192 {ko.get('content_type', '?')[:50]}",
            "color": _PHASE_COLORS["strategy"],
        },
        {
            "label": "Phase 2 \u2014 TOPIC DISCOVERY (Google Search Grounding)",
            "agents": "Sable (Gemini + Google Search)",
            "detail": f"Found topic via live search \u2192 \"{(topic or '?')[:50]}\"",
            "color": _PHASE_COLORS["topic"],
        },
        {
            "label": "Phase 3 \u2014 EMOTION \u2192 HARDCODED DESIGN",
            "agents": "Vesper (emotion detection only)",
            "detail": f"Detected emotion \u2192 hardcoded style/palette/font \u2192 {ko.get('design_name', '?')}",
            "color": _PHASE_COLORS["design"],
        },
        {
            "label": "Phase 4 \u2014 ANALYSIS",
            "agents": "Clio \u2022 Aurelia \u2022 Sage \u2022 Nova (+ 4 reviewers)",
            "detail": "Historical, economic, social, future perspectives \u2192 multi-round debates",
            "color": _PHASE_COLORS["analysis"],
        },
        {
            "label": "Phase 5\u20136 \u2014 ROUND TABLE + EDITORIAL",
            "agents": "All Analysts + Paramount",
            "detail": "Cross-challenges between analysts, editor quality gate",
            "color": _PHASE_COLORS["debate"],
        },
        {
            "label": "Phase 7 \u2014 CONTENT SYNTHESIS",
            "agents": "Quill \u2194 Sterling",
            "detail": "Writer created poster pages, copy reviewer ensured luxury quality",
            "color": _PHASE_COLORS["synthesis"],
        },
        {
            "label": "Phase 8\u20139 \u2014 NEUTRALITY + VISUALS",
            "agents": "Justice + Prism",
            "detail": "Guardrail check passed, Imagen backgrounds + foregrounds generated",
            "color": _PHASE_COLORS["quality"],
        },
        {
            "label": "Phase 11\u201312 \u2014 AUDIT + VALIDATION",
            "agents": "Ratio + Sentinel",
            "detail": f"Screen fill audit \u2192 PASS, 37-rule validation \u2192 {ko.get('validation_score', '?')}/100",
            "color": _PHASE_COLORS["quality"],
        },
        {
            "label": "Phase 13 \u2014 LINKEDIN POST",
            "agents": "Herald",
            "detail": "Crafted Unicode-formatted post with dynamic document title",
            "color": _PHASE_COLORS["publishing"],
        },
    ]

    for phase in phases:
        pc = _hex(phase["color"])
        cv.setFillColor(pc)
        cv.rect(M, y - 48, 5, 45, fill=1, stroke=0)
        y = _text(cv, phase["label"], M + 14, y, bold, 13, pc,
                  max_w=CW - 20)
        y = _text(cv, phase["agents"], M + 14, y - 2, bold, 10,
                  _hex("#444444"), max_w=CW - 20)
        y = _text(cv, phase["detail"], M + 14, y - 2, font, 9,
                  _hex("#777777"), max_w=CW - 20, leading=12)
        y -= 14

    y -= 8
    cv.setStrokeColor(_hex("#dddddd"))
    cv.setLineWidth(0.5)
    cv.line(M, y, W - M, y)
    y -= 10

    stats = [
        ("Agents", str(tf.get("total_agents", 15))),
        ("Debates", str(tf.get("total_debates", 7))),
        ("Duration", f"{tf.get('total_duration', 0):.0f}s"),
        ("Score", f"{ko.get('validation_score', '?')}/100"),
    ]
    stat_w = CW / len(stats)
    for si, (label, value) in enumerate(stats):
        sx = M + si * stat_w
        _text(cv, value, sx, y, bold, 16, _hex("#1a1a2e"),
              max_w=stat_w, align="center")
        _text(cv, label, sx, y - 18, font, 9, _hex("#999999"),
              max_w=stat_w, align="center")

    _text(cv, f"Run ID: {tf.get('run_id', 'N/A')}",
          M, 18, font, 7, _hex("#cccccc"), max_w=CW, align="center")

    cv.showPage()


# ═══════════════════════════════════════════════════════════════
#  AGENT PERSONA DEFINITIONS
# ═══════════════════════════════════════════════════════════════

# ── Agent persona definitions ──
# Each agent has a fixed character identity (gender, hair, features)
# and an anime-style futuristic portrait prompt.
# These are REUSABLE across projects — see personas/manifest.json.
#
# Style: Head-and-shoulder portrait, anime art, futuristic,
#        identifiable human face, clean background.

_PERSONA_STYLE = (
    "anime style head and shoulders portrait, identifiable human face, "
    "futuristic sci-fi aesthetic, clean gradient background, "
    "detailed expressive eyes, soft cinematic lighting, "
    "no text, no words, no letters, no logos"
)

# {codename: {description, gender, prompt}}
AGENT_PERSONA_DEFS = {
    "Aria": {
        "description": "World Pulse Scanner — senses global sentiment",
        "gender": "female",
        "hair": "flowing silver-white hair with faint blue glow",
        "features": "calm serene expression, pale blue eyes, translucent holographic earpiece",
        "accent_color": "soft cyan",
    },
    "Marcus": {
        "description": "Content Strategist — decides what to publish",
        "gender": "male",
        "hair": "short dark brown hair, neatly combed back",
        "features": "sharp focused gaze, dark-rimmed smart glasses with HUD reflection, strong jawline",
        "accent_color": "deep navy blue",
    },
    "Sable": {
        "description": "News Scout — finds trending stories via search",
        "gender": "female",
        "hair": "jet black asymmetric bob cut with one side longer",
        "features": "intense amber eyes, dark high-collar jacket, holographic press badge",
        "accent_color": "warm amber",
    },
    "Vesper": {
        "description": "Design DNA — detects emotion and picks visual style",
        "gender": "female",
        "hair": "wavy purple-violet hair with paint-streak highlights",
        "features": "dreamy artistic expression, large expressive violet eyes, colorful paint smudge on cheek",
        "accent_color": "violet purple",
    },
    "Clio": {
        "description": "Historian — provides historical perspective",
        "gender": "female",
        "hair": "long auburn-red hair in a loose braid",
        "features": "warm wise smile, green eyes, small round antique-gold spectacles, subtle freckles",
        "accent_color": "warm gold",
    },
    "Theron": {
        "description": "Historical Reviewer — critiques historical analysis",
        "gender": "male",
        "hair": "grey-streaked dark hair, slicked back",
        "features": "stern authoritative look, deep brown eyes, thin-framed titanium glasses, furrowed brow",
        "accent_color": "steel grey",
    },
    "Aurelia": {
        "description": "Economist — analyzes economic impact",
        "gender": "female",
        "hair": "sleek golden-blonde hair in a professional updo",
        "features": "confident calculating gaze, hazel-gold eyes, minimalist gold earring, sharp cheekbones",
        "accent_color": "gold",
    },
    "Callisto": {
        "description": "Economic Reviewer — critiques economic analysis",
        "gender": "male",
        "hair": "platinum silver undercut",
        "features": "analytical cold gaze, ice-blue eyes, translucent data-visor over one eye",
        "accent_color": "ice blue",
    },
    "Sage": {
        "description": "Sociologist — analyzes social implications",
        "gender": "male",
        "hair": "natural black curly hair with a few silver streaks",
        "features": "kind thoughtful expression, warm dark brown eyes, short beard, earth-tone scarf",
        "accent_color": "earth green",
    },
    "Liora": {
        "description": "Sociological Reviewer — critiques social analysis",
        "gender": "female",
        "hair": "soft chestnut-brown wavy hair past shoulders",
        "features": "empathetic gentle smile, warm hazel eyes, teardrop pendant necklace",
        "accent_color": "rose pink",
    },
    "Nova": {
        "description": "Futurist — predicts future scenarios",
        "gender": "female",
        "hair": "short electric-blue pixie cut with neon tips",
        "features": "visionary wide-eyed look, bright teal eyes, chrome collar, star-field reflected in pupils",
        "accent_color": "electric teal",
    },
    "Orion": {
        "description": "Future Reviewer — critiques predictions for groundedness",
        "gender": "male",
        "hair": "dark navy-blue wavy hair, medium length",
        "features": "contemplative steady gaze, deep indigo eyes, constellation tattoo on temple, subtle stubble",
        "accent_color": "deep indigo",
    },
    "Quill": {
        "description": "Content Writer — synthesizes luxury keynote content",
        "gender": "male",
        "hair": "tousled dark auburn hair, slightly long",
        "features": "passionate inspired expression, bright green eyes, ink smudge on finger, open collar",
        "accent_color": "ink blue",
    },
    "Sterling": {
        "description": "Copy Reviewer — ensures luxury-quality writing",
        "gender": "male",
        "hair": "distinguished silver-white hair, perfectly groomed",
        "features": "refined critical eye, grey-blue eyes, monocle-style smart lens, slight smirk",
        "accent_color": "polished silver",
    },
    "Justice": {
        "description": "Neutrality Guard — enforces ethical guardrails",
        "gender": "female",
        "hair": "straight platinum-blonde hair, shoulder length, parted in center",
        "features": "solemn unwavering gaze, striking grey eyes, blindfold pulled up on forehead, symmetrical face",
        "accent_color": "pure white",
    },
    "Paramount": {
        "description": "Editor-in-Chief — final editorial authority",
        "gender": "male",
        "hair": "salt-and-pepper hair, swept back with authority",
        "features": "commanding presence, piercing dark eyes, strong brow, high-tech earpiece, tailored collar",
        "accent_color": "charcoal black",
    },
    "Prism": {
        "description": "Visual Generator — creates images and infographics",
        "gender": "female",
        "hair": "iridescent rainbow-gradient hair flowing down",
        "features": "joyful creative spark in eyes, multicolored heterochromia eyes, prismatic light on skin",
        "accent_color": "rainbow iridescent",
    },
    "Ratio": {
        "description": "Screen Auditor — checks layout proportions",
        "gender": "male",
        "hair": "clean-shaven head with geometric tattoo patterns",
        "features": "precise measured look, amber-brown eyes, golden-ratio spiral overlay faintly on skin",
        "accent_color": "golden bronze",
    },
    "Sentinel": {
        "description": "Final Validator — quality gate, checks all rules",
        "gender": "male",
        "hair": "short military-cut black hair",
        "features": "vigilant protective glare, glowing orange-amber eyes, armored high collar, scar across cheek",
        "accent_color": "dark crimson",
    },
    "Spark": {
        "description": "Discussion Potential Analyst — scores engagement potential",
        "gender": "female",
        "hair": "wild spiky orange-red hair with electric highlights",
        "features": "excited energetic grin, bright yellow-green eyes, electric sparks around hair tips",
        "accent_color": "electric orange",
    },
    "Herald": {
        "description": "LinkedIn Expert — crafts and publishes posts",
        "gender": "male",
        "hair": "medium brown wavy hair, professionally styled",
        "features": "charismatic warm smile, confident blue eyes, crisp futuristic lapel with small emblem",
        "accent_color": "LinkedIn blue",
    },
}

# Build the prompt map from the structured definitions
AGENT_PERSONAS = {}
for _code, _def in AGENT_PERSONA_DEFS.items():
    AGENT_PERSONAS[_code] = (
        f"Anime style head and shoulders portrait of a {_def['gender']} character. "
        f"{_def['hair']}. {_def['features']}. "
        f"Futuristic sci-fi aesthetic, {_def['accent_color']} color accent, "
        f"clean dark gradient background, detailed expressive anime eyes, "
        f"soft cinematic lighting. "
        f"No text, no words, no letters, no logos."
    )

PERSONAS_DIR = config.OUTPUT_DIR / "visuals" / "personas"
PERSONAS_DIR.mkdir(parents=True, exist_ok=True)


def generate_persona_images(force: bool = False) -> dict:
    """Generate persona images for all agents. Cached — only generates once.

    Args:
        force: If True, delete existing images and regenerate all.

    Returns dict: codename -> image file path
    """
    import json as _json
    from aibrief.pipeline.visuals import _generate_imagen, _generate_dalle

    # Save the manifest for cross-project reuse
    manifest_path = PERSONAS_DIR / "manifest.json"
    manifest = {}
    for codename, defs in AGENT_PERSONA_DEFS.items():
        manifest[codename] = {
            **defs,
            "prompt": AGENT_PERSONAS[codename],
            "image_file": f"{codename.lower()}.png",
        }
    manifest_path.write_text(
        _json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    persona_paths = {}
    for codename, prompt in AGENT_PERSONAS.items():
        path = str(PERSONAS_DIR / f"{codename.lower()}.png")

        if force and Path(path).exists():
            Path(path).unlink()

        if Path(path).exists() and Path(path).stat().st_size > 1000:
            persona_paths[codename] = path
            continue

        print(f"  [Persona] Generating {codename}...")
        result = _generate_imagen(prompt, path, aspect="1:1", size="1K")
        if not result:
            result = _generate_dalle(prompt, path, size="1024x1024")
        if result:
            persona_paths[codename] = path
            print(f"  [Persona] {codename} saved")
        else:
            print(f"  [Persona] {codename} FAILED — will skip image")

    return persona_paths


# Agent codename lookup: from agent name to codename
_AGENT_NAME_TO_CODENAME = {
    "Historian": "Clio",
    "historical Reviewer": "Theron",
    "Economist": "Aurelia",
    "economic Reviewer": "Callisto",
    "Sociologist": "Sage",
    "sociological Reviewer": "Liora",
    "Futurist": "Nova",
    "future/predictions Reviewer": "Orion",
    "Content Writer": "Quill",
    "Copy Reviewer": "Sterling",
    "Pre-Visual Validator": "Sentinel",
    "Post-Visual Validator": "Sentinel",
    "Discussion Potential Analyst": "Spark",
    "Editor-in-Chief": "Paramount",
    "Screen Real Estate Auditor": "Ratio",
}

# Also map config agent names to codenames (for agent credits)
_CONFIG_NAME_TO_CODENAME = {
    "WorldPulseScanner": "Aria",
    "ContentStrategist": "Marcus",
    "NewsScout": "Sable",
    "DesignDNA": "Vesper",
    "Historian": "Clio",
    "HistorianReviewer": "Theron",
    "Economist": "Aurelia",
    "EconomistReviewer": "Callisto",
    "Sociologist": "Sage",
    "SociologistReviewer": "Liora",
    "Futurist": "Nova",
    "FuturistReviewer": "Orion",
    "ContentWriter": "Quill",
    "CopyReviewer": "Sterling",
    "NeutralityGuard": "Justice",
    "EditorInChief": "Paramount",
    "VisualGenerator": "Prism",
    "ScreenAuditor": "Ratio",
    "FinalValidator": "Sentinel",
    "DiscussionPotentialAnalyst": "Spark",
    "LinkedInExpert": "Herald",
}


def _resolve_debate_codenames(deb: dict) -> tuple:
    """Resolve preparer and reviewer codenames from a debate entry.

    Works with both new traces (have preparer_name/reviewer_name) and
    old traces (only have pair string like 'Historian vs historical Reviewer [historical]').
    """
    prep_name = deb.get("preparer_name", "")
    rev_name = deb.get("reviewer_name", "")

    # If already have names, just look up codenames
    if prep_name and rev_name:
        return (_AGENT_NAME_TO_CODENAME.get(prep_name, ""),
                _AGENT_NAME_TO_CODENAME.get(rev_name, ""))

    # Parse from pair string: "Historian vs historical Reviewer [historical]"
    pair = deb.get("pair", "")
    # Remove the [label] part
    if "[" in pair:
        pair = pair[:pair.index("[")].strip()
    # Also handle "RoundTable (all analysts)"
    if "RoundTable" in pair:
        return ("", "")

    parts = pair.split(" vs ")
    if len(parts) == 2:
        prep_name = parts[0].strip()
        rev_name = parts[1].strip()
        return (_AGENT_NAME_TO_CODENAME.get(prep_name, ""),
                _AGENT_NAME_TO_CODENAME.get(rev_name, ""))

    return ("", "")


# ═══════════════════════════════════════════════════════════════
#  SECTION 5: DEBATES & JUDGMENTS
# ═══════════════════════════════════════════════════════════════

def _find_analyst_output(entries, debate_entry) -> dict:
    """Find the analyst output that immediately precedes a DEBATE entry.

    The trace stores phases like:
      Analyst_historical → DEBATE (Historian vs historical Reviewer)
    So the analyst output is the entry right before the DEBATE.
    """
    for i, e in enumerate(entries):
        if e is debate_entry and i > 0:
            prev = entries[i - 1]
            if prev.get("phase", "").startswith("Analyst") or \
               prev.get("phase", "") == "ContentSynthesis":
                return prev.get("output", {})
    return {}


def _debate_new_page(cv, accent, title_text, font, bold):
    """Start a fresh debate page with consistent header."""
    cv.showPage()
    cv.setFillColor(_hex("#faf9f5"))
    cv.rect(0, 0, W, H, fill=1, stroke=0)
    cv.setFillColor(accent)
    cv.rect(0, H - 4, W, 4, fill=1, stroke=0)
    y = H - M
    if title_text:
        y = _text(cv, title_text, M, y, bold, 14,
                  _hex("#888888"), max_w=CW, align="center")
        y -= 12
    return y


def _draw_chat_bubble(cv, x, y, w, lines_text, font_name, bold_name,
                      header, header_color, body_color, bg_color,
                      persona_img=None, icon_size=36, is_right=False):
    """Draw a chat-message bubble with optional persona icon.

    Returns the new y position after the bubble.

    Layout (left-aligned):
      [icon]  ┌─ header ─────────────┐
              │ body text...          │
              └───────────────────────┘

    Layout (right-aligned):
              ┌─ header ─────────────┐  [icon]
              │ body text...          │
              └───────────────────────┘
    """
    BUBBLE_PAD = 10
    ICON_GAP = 8
    TAIL_SIZE = 6

    # Measure content height
    text_w = w - 2 * BUBBLE_PAD
    header_h = _measure_text(header, bold_name, 10, max_w=text_w) if header else 0
    body_h = 0
    for line in lines_text:
        body_h += _measure_text(line, font_name, 9, max_w=text_w, leading=12)
        body_h += 3  # inter-line gap

    total_h = BUBBLE_PAD + header_h + 4 + body_h + BUBBLE_PAD
    total_h = max(total_h, icon_size + 4)  # at least as tall as icon

    # Position bubble and icon
    if is_right:
        bubble_x = x + (W - 2 * M) - w
        icon_x = bubble_x + w + ICON_GAP
    else:
        icon_x = x
        bubble_x = x + icon_size + ICON_GAP
        # Adjust width to not overflow
        w = min(w, W - 2 * M - icon_size - ICON_GAP)
        text_w = w - 2 * BUBBLE_PAD

    bubble_y = y - total_h

    # Draw bubble background
    cv.setFillColor(bg_color)
    cv.roundRect(bubble_x, bubble_y, w, total_h, 6, fill=1, stroke=0)

    # Draw tail triangle pointing toward the icon
    cv.setFillColor(bg_color)
    p = cv.beginPath()
    if is_right:
        # Tail on the right side
        tx = bubble_x + w
        ty = y - icon_size / 2
        p.moveTo(tx, ty + TAIL_SIZE)
        p.lineTo(tx + TAIL_SIZE, ty)
        p.lineTo(tx, ty - TAIL_SIZE)
    else:
        # Tail on the left side
        tx = bubble_x
        ty = y - icon_size / 2
        p.moveTo(tx, ty + TAIL_SIZE)
        p.lineTo(tx - TAIL_SIZE, ty)
        p.lineTo(tx, ty - TAIL_SIZE)
    p.close()
    cv.drawPath(p, fill=1, stroke=0)

    # Draw persona icon
    if persona_img and Path(persona_img).exists():
        _place_image(cv, persona_img, icon_x, y - icon_size,
                     icon_size, icon_size)

    # Draw header text
    ty = y - BUBBLE_PAD
    if header:
        ty = _text(cv, header, bubble_x + BUBBLE_PAD, ty,
                   bold_name, 10, header_color, max_w=text_w, leading=12)
        ty -= 4

    # Draw body lines
    for line in lines_text:
        ty = _text(cv, line, bubble_x + BUBBLE_PAD, ty,
                   font_name, 9, body_color, max_w=text_w, leading=12)
        ty -= 3

    return bubble_y - 8  # gap after bubble


def _build_debates(cv, tracer_flow, persona_paths, font, bold, colors):
    """Build debate pages as chat-style conversations between agents.

    Uses chat bubbles:
      - Preparer on the LEFT (blue-tinted bubbles)
      - Reviewer on the RIGHT (warm-tinted bubbles)
      - Each round shows the actual exchange text
    """
    if not tracer_flow:
        return 0

    entries = tracer_flow.get("entries", [])
    debates = [e for e in entries if e.get("phase") == "DEBATE"]
    if not debates:
        return 0

    accent = colors["accent"]
    pages_created = 0

    # ── Colors for chat bubbles ──
    PREP_BG = Color(0.90, 0.94, 0.98, 1)     # light blue
    PREP_HEADER = _hex("#1a5276")
    PREP_BODY = _hex("#2c3e50")
    REV_BG = Color(0.98, 0.93, 0.90, 1)      # warm peach
    REV_HEADER = _hex("#922b21")
    REV_BODY = _hex("#4a2520")
    REVISION_BG = Color(0.92, 0.97, 0.92, 1)  # light green (revision)

    # ══════ SECTION TITLE PAGE ══════
    cv.setFillColor(_hex("#faf9f5"))
    cv.rect(0, 0, W, H, fill=1, stroke=0)
    cv.setFillColor(accent)
    cv.rect(0, H - 4, W, 4, fill=1, stroke=0)

    y = H - M
    y = _text(cv, "Debates & Judgments", M, y, bold, 32,
              _hex("#1a1a2e"), max_w=CW, align="center")
    y = _text(cv, "How AI Agents Argued to Improve Quality", M, y - 6,
              font, 13, _hex("#888888"), max_w=CW, align="center")
    y -= 30

    total_rounds = sum(d.get("total_rounds", 0) for d in debates)
    y = _text(cv, f"{len(debates)} Debates  \u2022  {total_rounds} Total Rounds",
              M, y, bold, 16, _hex("#1a1a2e"), max_w=CW, align="center")
    y -= 40

    # Quick summary of all debates on title page
    for deb in debates:
        pair = deb.get("pair", "?")
        rounds_data = deb.get("rounds", [])
        n_rounds = deb.get("total_rounds", len(rounds_data))
        final_score = rounds_data[-1].get("score", "?") if rounds_data else "?"
        approved = rounds_data[-1].get("approved", False) if rounds_data else False

        bar_color = _hex("#2ecc71") if approved else _hex("#e74c3c")
        cv.setFillColor(bar_color)
        cv.rect(M, y - 28, 5, 25, fill=1, stroke=0)

        pair_short = pair.split("[")[0].strip() if "[" in pair else pair
        y = _text(cv, pair_short, M + 14, y, bold, 13,
                  _hex("#1a1a2e"), max_w=CW - 20)
        status = (f"{'✓ APPROVED' if approved else '✗ REJECTED'} "
                  f"after {n_rounds} round(s) \u2014 Final score: {final_score}/10")
        y = _text(cv, status, M + 14, y - 2, font, 10,
                  bar_color, max_w=CW - 20)
        y -= 16

        if y < 80:
            break

    _text(cv, "Chat-style debate breakdowns on the following pages \u2192",
          M, 30, font, 9, _hex("#aaaaaa"), max_w=CW, align="center")
    cv.showPage()
    pages_created += 1

    # ══════ INDIVIDUAL DEBATE PAGES (CHAT STYLE) ══════
    for deb in debates:
        pair = deb.get("pair", "?")
        rounds_data = deb.get("rounds", [])
        label = deb.get("label", "")

        if "RoundTable" in pair:
            continue

        if not label and "[" in pair:
            label = pair[pair.index("[") + 1:].rstrip("]").strip()

        prep_code, rev_code = _resolve_debate_codenames(deb)
        prep_img = persona_paths.get(prep_code, "")
        rev_img = persona_paths.get(rev_code, "")

        # ── Page header ──
        cv.setFillColor(_hex("#faf9f5"))
        cv.rect(0, 0, W, H, fill=1, stroke=0)
        cv.setFillColor(accent)
        cv.rect(0, H - 4, W, 4, fill=1, stroke=0)

        y = H - M
        pair_short = pair.split("[")[0].strip() if "[" in pair else pair
        y = _text(cv, pair_short, M, y, bold, 20,
                  _hex("#1a1a2e"), max_w=CW, align="center")
        if label:
            y = _text(cv, f"Topic: {label}", M, y - 4, font, 11,
                      _hex("#888888"), max_w=CW, align="center")
        y -= 10

        # ── Personas header row (smaller, inline) ──
        icon_sm = 44
        left_x = M + 20
        right_x = W - M - icon_sm - 20
        if prep_code and prep_img:
            _place_image(cv, prep_img, left_x, y - icon_sm, icon_sm, icon_sm)
            _text(cv, prep_code, left_x + icon_sm + 6, y - 14,
                  bold, 11, PREP_HEADER, max_w=120)
            _text(cv, "Preparer", left_x + icon_sm + 6, y - 28,
                  font, 8, _hex("#888888"), max_w=80)
        if rev_code and rev_img:
            _place_image(cv, rev_img, right_x, y - icon_sm, icon_sm, icon_sm)
            _text(cv, rev_code, right_x - 80, y - 14,
                  bold, 11, REV_HEADER, max_w=120, align="right")
            _text(cv, "Reviewer", right_x - 80, y - 28,
                  font, 8, _hex("#888888"), max_w=80, align="right")

        y -= icon_sm + 12

        # ── Separator ──
        cv.setStrokeColor(_hex("#e0ddd5"))
        cv.setLineWidth(0.5)
        cv.line(M, y, W - M, y)
        y -= 12

        page_title_for_cont = f"{pair_short} (continued)"
        BUBBLE_W = CW * 0.72  # bubbles take ~72% of content width

        # ── Chat conversation per round ──
        for rd in rounds_data:
            rnd_num = rd.get("round", 0)
            score = rd.get("score", 0)
            approved = rd.get("approved", False)

            # Need space for at least one bubble (~100pt minimum)
            if y < 120:
                y = _debate_new_page(cv, accent, page_title_for_cont,
                                     font, bold)
                pages_created += 1

            # ── Round divider ──
            score_color = (_hex("#2ecc71") if score >= 8
                           else _hex("#f39c12") if score >= 6
                           else _hex("#e74c3c"))
            cv.setFillColor(_hex("#e8e5de"))
            cv.roundRect(W / 2 - 60, y - 14, 120, 16, 8, fill=1, stroke=0)
            _text(cv, f"Round {rnd_num}", W / 2 - 55, y - 1,
                  bold, 9, _hex("#666666"), max_w=110, align="center")
            y -= 22

            # ── PREPARER BUBBLE (left) ──
            prep_sub = rd.get("preparer_submission", {})
            prep_lines = []
            if prep_sub:
                if prep_sub.get("title"):
                    prep_lines.append(f"\u201c{prep_sub['title']}\u201d")
                if prep_sub.get("key_insight"):
                    prep_lines.append(prep_sub["key_insight"][:200])
                args = prep_sub.get("key_arguments", [])
                for arg in args[:2]:
                    prep_lines.append(f"\u25b8 {str(arg)[:120]}")
                if prep_sub.get("confidence"):
                    prep_lines.append(
                        f"Confidence: {prep_sub['confidence']}/10")
            else:
                # Fallback for old traces without conversation data
                prep_lines.append("(Submitted analysis for review)")

            if y < 100:
                y = _debate_new_page(cv, accent, page_title_for_cont,
                                     font, bold)
                pages_created += 1

            prep_header = f"{prep_code or 'Preparer'} submits:"
            y = _draw_chat_bubble(
                cv, M, y, BUBBLE_W, prep_lines, font, bold,
                header=prep_header,
                header_color=PREP_HEADER, body_color=PREP_BODY,
                bg_color=PREP_BG, persona_img=prep_img,
                is_right=False,
            )

            # ── REVIEWER BUBBLE (right) ──
            rev_fb = rd.get("reviewer_feedback", {})
            rev_lines = []
            if rev_fb:
                rev_lines.append(f"Score: {rev_fb.get('score', score)}/10")
                if rev_fb.get("verdict"):
                    rev_lines.append(rev_fb["verdict"][:200])
                for d in rev_fb.get("demands", [])[:3]:
                    rev_lines.append(f"\u2192 {str(d)[:140]}")
                for s in rev_fb.get("strengths", [])[:2]:
                    rev_lines.append(f"\u2713 {str(s)[:120]}")
            else:
                # Fallback for old traces
                rev_lines.append(f"Score: {score}/10")
                verdict_text = rd.get("verdict", "")
                if verdict_text:
                    rev_lines.append(verdict_text[:180])
                for d in rd.get("demands", [])[:3]:
                    rev_lines.append(f"\u2192 {str(d)[:120]}")

            if approved:
                rev_lines.append("\u2705 APPROVED")

            if y < 100:
                y = _debate_new_page(cv, accent, page_title_for_cont,
                                     font, bold)
                pages_created += 1

            rev_header = f"{rev_code or 'Reviewer'} responds:"
            y = _draw_chat_bubble(
                cv, M, y, BUBBLE_W, rev_lines, font, bold,
                header=rev_header,
                header_color=REV_HEADER, body_color=REV_BODY,
                bg_color=REV_BG, persona_img=rev_img,
                is_right=True,
            )

            # ── REVISION BUBBLE (left, green) — if preparer revised ──
            revision = rd.get("preparer_revision", {})
            if revision and not approved:
                rev_lines2 = []
                if revision.get("title"):
                    rev_lines2.append(f"\u201c{revision['title']}\u201d")
                if revision.get("key_insight"):
                    rev_lines2.append(revision["key_insight"][:200])
                args2 = revision.get("key_arguments", [])
                for arg in args2[:2]:
                    rev_lines2.append(f"\u25b8 {str(arg)[:120]}")
                if revision.get("confidence"):
                    rev_lines2.append(
                        f"Confidence: {revision['confidence']}/10")

                if rev_lines2:
                    if y < 100:
                        y = _debate_new_page(
                            cv, accent, page_title_for_cont, font, bold)
                        pages_created += 1

                    y = _draw_chat_bubble(
                        cv, M, y, BUBBLE_W, rev_lines2, font, bold,
                        header=f"{prep_code or 'Preparer'} revises:",
                        header_color=_hex("#1e8449"),
                        body_color=_hex("#2d572c"),
                        bg_color=REVISION_BG,
                        persona_img=prep_img,
                        is_right=False,
                    )

        # ── Final verdict box at bottom ──
        if rounds_data:
            final = rounds_data[-1]
            final_approved = final.get("approved", False)
            final_score = final.get("score", 0)
            n_rounds = len(rounds_data)

            if y < 60:
                y = _debate_new_page(cv, accent, page_title_for_cont,
                                     font, bold)
                pages_created += 1

            box_color = _hex("#2ecc71") if final_approved else _hex("#e74c3c")
            box_y = max(y - 40, 20)
            cv.setFillColor(_a(box_color, 0.1))
            cv.roundRect(M, box_y, CW, 35, 6, fill=1, stroke=0)
            cv.setFillColor(box_color)
            cv.rect(M, box_y, 5, 35, fill=1, stroke=0)

            verdict_label = ("\u2713 APPROVED" if final_approved
                             else "\u2717 NOT APPROVED (max rounds reached)")
            _text(cv, f"{verdict_label}  \u2014  Score: {final_score}/10 "
                  f"after {n_rounds} round(s)",
                  M + 14, box_y + 22, bold, 13, box_color, max_w=CW - 30)

        cv.showPage()
        pages_created += 1

    return pages_created


def _build_judgments(cv, tracer_flow, persona_paths, font, bold, colors):
    """Build validation judgment pages showing pre-visual and post-visual results."""
    if not tracer_flow:
        return 0

    entries = tracer_flow.get("entries", [])
    validations = [e for e in entries
                   if e.get("phase") in ("PreVisualValidation", "PostVisualValidation")]
    if not validations:
        return 0

    accent = colors["accent"]

    cv.setFillColor(_hex("#faf9f5"))
    cv.rect(0, 0, W, H, fill=1, stroke=0)
    cv.setFillColor(accent)
    cv.rect(0, H - 4, W, 4, fill=1, stroke=0)

    y = H - M
    y = _text(cv, "Quality Judgments", M, y, bold, 28,
              _hex("#1a1a2e"), max_w=CW, align="center")
    y = _text(cv, "How the Validators Scored This Brief", M, y - 6,
              font, 12, _hex("#888888"), max_w=CW, align="center")
    y -= 30

    # Sentinel persona image centered
    sentinel_path = persona_paths.get("Sentinel", "")
    if sentinel_path and Path(sentinel_path).exists():
        img_size = 70
        _place_image(cv, sentinel_path, W / 2 - img_size / 2,
                     y - img_size, img_size, img_size)
        y -= img_size + 8
        _text(cv, "Sentinel — Quality Gate", M, y, bold, 11,
              _hex("#1a1a2e"), max_w=CW, align="center")
        y -= 20

    for val_entry in validations:
        phase = val_entry.get("phase", "")
        output = val_entry.get("output", {})
        if not output:
            continue

        total_score = output.get("total_score", 0)
        approved = output.get("approved", False)
        explanation = output.get("explanation", "")
        critical = output.get("critical_failures", [])
        verdict = output.get("verdict", "")

        # Phase label
        label = ("Pre-Visual Validation (Content & Structure)"
                 if "Pre" in phase
                 else "Post-Visual Validation (Layout & Visuals)")

        score_color = (_hex("#2ecc71") if total_score >= 70
                       else _hex("#f39c12") if total_score >= 50
                       else _hex("#e74c3c"))

        # Score box
        cv.setFillColor(_a(score_color, 0.08))
        cv.roundRect(M, y - 50, CW, 48, 6, fill=1, stroke=0)
        cv.setFillColor(score_color)
        cv.rect(M, y - 50, 5, 48, fill=1, stroke=0)

        status = "✓ PASS" if approved else "✗ FAIL"
        _text(cv, f"{label}", M + 14, y - 8, bold, 13,
              _hex("#1a1a2e"), max_w=CW - 70)
        _text(cv, f"{total_score}/100 {status}", W - M - 90, y - 8,
              bold, 15, score_color, max_w=90)

        if explanation:
            expl_short = explanation[:200]
            if len(explanation) > 200:
                expl_short += "..."
            _text(cv, expl_short, M + 14, y - 28, font, 9,
                  _hex("#555555"), max_w=CW - 30, leading=11)

        y -= 60

        # Critical failures
        if critical:
            y = _text(cv, "Critical Failures:", M + 14, y, bold, 10,
                      _hex("#e74c3c"), max_w=CW - 20)
            for cf in critical[:4]:
                cf_short = str(cf)[:100]
                y = _text(cv, f"  ✗ {cf_short}", M + 14, y - 3, font, 9,
                          _hex("#666666"), max_w=CW - 30, leading=11)
            y -= 12

        if y < 100:
            break

    # Overall verdict
    if y > 60:
        ko = tracer_flow.get("key_outputs", {})
        combined = ko.get("validation_score", "?")
        _text(cv, f"Combined Score: {combined}/100",
              M, 30, bold, 11, _hex("#1a1a2e"), max_w=CW, align="center")

    cv.showPage()
    return 1


# ═══════════════════════════════════════════════════════════════
#  MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_poster(brief: dict, design: dict, story: dict,
                    visuals: dict = None, agents_info: list = None,
                    tracer_flow: dict = None, strategy: dict = None,
                    output_path: str = None,
                    persona_paths: dict = None) -> str:
    """Generate the complete poster PDF.

    Structure:
        Page 1:     Cover (landing page)
        Page 2:     News Summary (headline, publisher, URL, 6 points)
        Pages 3-6:  Content (5 points each, bg + fg images)
        Pages 7-8:  Agent credits
        Page 9:     Run info summary
        Page 10:    Decision architecture
        Pages 11+:  Debates & Judgments (with persona images)
    """
    if not output_path:
        slug = brief.get("brief_title", "AI_Brief")[:35]
        slug = re.sub(r'[<>:"/\\|?*]', '', slug).replace(" ", "_").strip("_")
        output_path = str(config.OUTPUT_DIR / f"{slug}_poster.pdf")

    visuals = visuals or {}
    brief["_assistant_name"] = _agent_name()

    # ── Resolve design from catalog ──
    style_id = design.get("style_id", "luxury_minimalist")
    palette_id = design.get("palette_id", "")
    font_id = design.get("font_id", "")

    style = lookup_style(style_id)
    palette = lookup_palette(palette_id) if palette_id else None

    if font_id:
        font_name, bold_name = register_font(font_id)
    else:
        font_name, bold_name = "Helvetica", "Helvetica-Bold"

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

    pdf = canvas.Canvas(output_path, pagesize=PAGE_SIZE)
    pdf.setTitle(brief.get("brief_title", "AI Brief"))
    pdf.setAuthor("Bhasker Kumar")

    # === PAGE 1: COVER ===
    _build_cover(pdf, brief, story, design, visuals,
                 font_name, bold_name, colors, style_id)
    pdf.showPage()

    # === PAGE 2: NEWS SUMMARY ===
    pages = brief.get("pages", [])
    news_page = None
    content_pages = []
    for p in pages:
        if p.get("page_type") == "hero":
            continue
        elif p.get("page_type") == "news_summary" and news_page is None:
            news_page = p
        else:
            content_pages.append(p)

    # Build news summary (page index 0 for visuals = first content page)
    if news_page:
        _build_news_summary(pdf, news_page, story, design, visuals,
                            font_name, bold_name, colors, style_id, 0)
    else:
        # Fallback: build news summary from story data
        fallback = {
            "page_type": "news_summary",
            "news_headline": story.get("exact_news_headline", story.get("headline", "")),
            "news_publisher": story.get("publisher", ""),
            "news_url": story.get("news_url", ""),
            "summary_points": story.get("summary_points", []),
        }
        _build_news_summary(pdf, fallback, story, design, visuals,
                            font_name, bold_name, colors, style_id, 0)
    pdf.showPage()

    # === PAGES 3-6: CONTENT (5 points each) ===
    for i, page in enumerate(content_pages[:4]):
        _build_content_page(pdf, page, i + 3, i + 1, design, visuals,
                            font_name, bold_name, colors, style_id)
        pdf.showPage()

    # === AGENT CREDITS ===
    if agents_info:
        _build_agent_credits(pdf, agents_info, font_name, bold_name,
                             colors, style_id, persona_paths=persona_paths)

    # === RUN INFO ===
    _build_run_info(pdf, design, story, strategy, tracer_flow,
                    font_name, bold_name, colors)

    # === DECISION ARCHITECTURE ===
    topic = story.get("headline", brief.get("brief_title", ""))
    _build_mind_map(pdf, tracer_flow, topic, font_name, bold_name, colors)

    # === DEBATES & JUDGMENTS ===
    ppaths = persona_paths or {}
    debate_pages = _build_debates(pdf, tracer_flow, ppaths,
                                  font_name, bold_name, colors)
    judgment_pages = _build_judgments(pdf, tracer_flow, ppaths,
                                     font_name, bold_name, colors)

    pdf.save()
    total_pages = 2 + min(len(content_pages), 4)  # cover + news + content
    if agents_info:
        total_pages += math.ceil(len(agents_info) / 7)
    total_pages += 2  # run info + mind map
    total_pages += debate_pages + judgment_pages
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [Poster] Saved: {output_path} ({size_kb:.0f} KB, "
          f"~{total_pages} pages)")
    return output_path
