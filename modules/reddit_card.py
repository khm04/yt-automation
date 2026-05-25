from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

CARD_W = 900
CARD_H = 320
CORNER = 24
BG = (26, 26, 27)          # Reddit dark background
CARD_BG = (39, 39, 41)     # slightly lighter card
ORANGE = (255, 69, 0)      # Reddit orange
WHITE = (255, 255, 255)
GRAY = (129, 129, 129)
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")


def _font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.ellipse([x0, y0, x0 + radius * 2, y0 + radius * 2], fill=fill)
    draw.ellipse([x1 - radius * 2, y0, x1, y0 + radius * 2], fill=fill)
    draw.ellipse([x0, y1 - radius * 2, x0 + radius * 2, y1], fill=fill)
    draw.ellipse([x1 - radius * 2, y1 - radius * 2, x1, y1], fill=fill)


def generate_reddit_card(subreddit: str, title: str, output_path: str) -> str:
    """Generate a Reddit-style post card image."""
    img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Card background with rounded corners
    _rounded_rect(draw, (0, 0, CARD_W - 1, CARD_H - 1), CORNER, CARD_BG)

    # Left orange upvote bar
    draw.rectangle([0, 0, 6, CARD_H], fill=ORANGE)

    # Reddit logo circle
    draw.ellipse([24, 20, 56, 52], fill=ORANGE)
    logo_font = _font(22, bold=True)
    draw.text((32, 22), "R", fill=WHITE, font=logo_font)

    # Subreddit name
    sub_font = _font(20, bold=True)
    draw.text((68, 22), f"r/{subreddit}", fill=WHITE, font=sub_font)

    # "Posted by" line
    by_font = _font(16)
    draw.text((68, 48), "Posted by u/throwaway • Reddit", fill=GRAY, font=by_font)

    # Divider
    draw.rectangle([24, 72, CARD_W - 24, 74], fill=(60, 60, 62))

    # Title text — wrapped
    title_font = _font(28, bold=True)
    wrapped = textwrap.wrap(title, width=42)[:3]  # max 3 lines
    y = 90
    for line in wrapped:
        draw.text((24, y), line, fill=WHITE, font=title_font)
        y += 38

    # Bottom stats bar
    stats_font = _font(17)
    draw.text((24, CARD_H - 36), "⬆ 12.4k   💬 843 comments   🔗 Share", fill=GRAY, font=stats_font)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
