"""Generate a shareable verification certificate: matched post, confidence
score, on-chain record details, and a QR code linking to the PolygonScan
transaction -- a concrete, demo-friendly artifact tying the whole pipeline
together.

Colors match the app's HH Goa theme (app/theme.css) -- cream background,
forest green / pink / yellow accents.
"""
import io
import os

import qrcode
import requests
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1000, 640

COLOR_CREAM = (253, 246, 231)
COLOR_CREAM_DEEP = (247, 234, 209)
COLOR_CARD = (255, 255, 255)
COLOR_FOREST = (20, 83, 45)
COLOR_FOREST_DEEP = (11, 61, 34)
COLOR_PINK = (224, 68, 127)
COLOR_PINK_DEEP = (194, 38, 101)
COLOR_YELLOW = (245, 197, 24)
COLOR_YELLOW_DEEP = (224, 172, 0)
COLOR_TEXT = (18, 51, 31)
COLOR_DIM = (91, 117, 102)

ROOFLINE_HEIGHT = 14
ROOFLINE_STRIPE_COLORS = [COLOR_FOREST, COLOR_PINK, COLOR_YELLOW]
ROOFLINE_STRIPE_WIDTH = 26

FONT_CANDIDATES_BOLD = [
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]
FONT_CANDIDATES_REGULAR = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]
FONT_CANDIDATES_MONO = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
]


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _fetch_face_thumbnail(url: str, size: int = 160) -> Image.Image | None:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content)).convert("RGB")
        img.thumbnail((size, size))
        return img
    except Exception:
        return None


def _draw_roofline(draw: ImageDraw.ImageDraw) -> None:
    """Diagonal-stripe banner matching the app's roof-tile motif."""
    step = ROOFLINE_STRIPE_WIDTH
    slant = ROOFLINE_HEIGHT
    x = -slant * 2
    i = 0
    while x < WIDTH + slant * 2:
        color = ROOFLINE_STRIPE_COLORS[i % len(ROOFLINE_STRIPE_COLORS)]
        points = [
            (x, 0),
            (x + step - 4, 0),
            (x + step - 4 - slant, ROOFLINE_HEIGHT),
            (x - slant, ROOFLINE_HEIGHT),
        ]
        draw.polygon(points, fill=color)
        x += step
        i += 1


def generate_certificate(
    evidence_bundle: dict,
    explorer_url: str,
    record_id: int,
    ipfs_cid: str,
    output_path: str,
    query_image_path: str | None = None,
) -> str:
    font_title = _load_font(FONT_CANDIDATES_BOLD, 40)
    font_label = _load_font(FONT_CANDIDATES_REGULAR, 16)
    font_value = _load_font(FONT_CANDIDATES_REGULAR, 20)
    font_mono = _load_font(FONT_CANDIDATES_MONO, 15)
    font_badge = _load_font(FONT_CANDIDATES_BOLD, 14)

    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_CREAM)
    draw = ImageDraw.Draw(img)

    _draw_roofline(draw)

    # Header
    badge_text = "HH GOA 2026 · SIGNAL TASK 3"
    badge_box = draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_w, badge_h = badge_box[2] - badge_box[0], badge_box[3] - badge_box[1]
    draw.rounded_rectangle(
        [(50, 40), (50 + badge_w + 28, 40 + badge_h + 20)],
        radius=14, fill=COLOR_YELLOW, outline=COLOR_FOREST_DEEP, width=2,
    )
    draw.text((64, 49), badge_text, font=font_badge, fill=COLOR_FOREST_DEEP)

    draw.text((50, 90), "Verification Certificate", font=font_title, fill=COLOR_FOREST_DEEP)
    draw.line([(50, 148), (WIDTH - 50, 148)], fill=COLOR_FOREST, width=2)

    # Query image preview (left)
    y = 178
    if query_image_path and os.path.exists(query_image_path):
        try:
            face_img = Image.open(query_image_path).convert("RGB")
            face_img.thumbnail((150, 150))
            border_box = [(48, y - 2), (48 + face_img.width + 4, y - 2 + face_img.height + 4)]
            draw.rounded_rectangle(border_box, radius=6, outline=COLOR_FOREST, width=2)
            img.paste(face_img, (50, y))
        except Exception:
            pass

    # Matched post details (middle)
    text_x = 260
    draw.text((text_x, y), "MATCHED POST", font=font_label, fill=COLOR_DIM)
    title = evidence_bundle.get("post_title") or evidence_bundle.get("post_source", "")
    draw.text((text_x, y + 22), title[:55], font=font_value, fill=COLOR_TEXT)
    draw.text((text_x, y + 52), evidence_bundle["post_url"][:65], font=font_mono, fill=COLOR_PINK_DEEP)

    confidence = evidence_bundle.get("face_match_confidence", 0)
    conf_text = f"Face match confidence: {confidence:.1%}"
    conf_box = draw.textbbox((0, 0), conf_text, font=font_value)
    conf_w, conf_h = conf_box[2] - conf_box[0], conf_box[3] - conf_box[1]
    draw.rounded_rectangle(
        [(text_x, y + 88), (text_x + conf_w + 24, y + 88 + conf_h + 16)],
        radius=10, fill=COLOR_YELLOW, outline=COLOR_YELLOW_DEEP, width=1,
    )
    draw.text((text_x + 12, y + 96), conf_text, font=font_value, fill=COLOR_FOREST_DEEP)

    # On-chain record card
    card_y = 348
    draw.rounded_rectangle(
        [(50, card_y), (WIDTH - 50, card_y + 220)],
        radius=14, fill=COLOR_CARD, outline=COLOR_FOREST, width=2,
    )
    draw.text((70, card_y + 20), "ON-CHAIN RECORD — POLYGON AMOY", font=font_label, fill=COLOR_DIM)
    draw.text((70, card_y + 48), f"Record #{record_id}", font=font_value, fill=COLOR_TEXT)
    draw.text((70, card_y + 82), f"IPFS CID: {ipfs_cid[:44]}...", font=font_mono, fill=COLOR_PINK_DEEP)
    draw.text((70, card_y + 108), f"Generated: {evidence_bundle.get('generated_at', '')}", font=font_mono, fill=COLOR_DIM)
    draw.text((70, card_y + 134), "Scan QR to view the transaction on PolygonScan ->", font=font_mono, fill=COLOR_DIM)

    # QR code
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(explorer_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=COLOR_FOREST_DEEP, back_color=COLOR_CARD).convert("RGB")
    qr_img = qr_img.resize((150, 150))
    img.paste(qr_img, (WIDTH - 220, card_y + 40))

    # Footer
    draw.text(
        (50, HEIGHT - 40),
        "Tamper-evident: this hash is verifiable against the on-chain record at any time.",
        font=font_mono,
        fill=COLOR_DIM,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    return output_path
