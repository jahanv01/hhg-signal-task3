"""Generate a shareable verification certificate: matched post, confidence
score, on-chain record details, and a QR code linking to the PolygonScan
transaction -- a concrete, demo-friendly artifact tying the whole pipeline
together.
"""
import io
import os

import qrcode
import requests
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1000, 640

COLOR_BG = (11, 18, 32)
COLOR_CARD = (16, 26, 46)
COLOR_TEAL = (20, 184, 166)
COLOR_GOLD = (245, 158, 11)
COLOR_SAND = (245, 240, 230)
COLOR_DIM = (144, 160, 189)

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

    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((50, 40), "HH GOA 2026 · SIGNAL TASK 3", font=font_badge, fill=COLOR_GOLD)
    draw.text((50, 68), "Verification Certificate", font=font_title, fill=COLOR_SAND)
    draw.line([(50, 130), (WIDTH - 50, 130)], fill=(255, 255, 255, 20), width=1)

    # Query image preview (left)
    y = 160
    if query_image_path and os.path.exists(query_image_path):
        try:
            face_img = Image.open(query_image_path).convert("RGB")
            face_img.thumbnail((150, 150))
            img.paste(face_img, (50, y))
        except Exception:
            pass

    # Matched post details (middle)
    text_x = 260
    draw.text((text_x, y), "MATCHED POST", font=font_label, fill=COLOR_DIM)
    title = evidence_bundle.get("post_title") or evidence_bundle.get("post_source", "")
    draw.text((text_x, y + 22), title[:55], font=font_value, fill=COLOR_SAND)
    draw.text((text_x, y + 52), evidence_bundle["post_url"][:65], font=font_mono, fill=COLOR_TEAL)

    confidence = evidence_bundle.get("face_match_confidence", 0)
    draw.text((text_x, y + 90), f"Face match confidence: {confidence:.1%}", font=font_value, fill=COLOR_GOLD)

    # On-chain record card
    card_y = 330
    draw.rounded_rectangle([(50, card_y), (WIDTH - 50, card_y + 220)], radius=14, fill=COLOR_CARD)
    draw.text((70, card_y + 20), "ON-CHAIN RECORD — POLYGON AMOY", font=font_label, fill=COLOR_DIM)
    draw.text((70, card_y + 48), f"Record #{record_id}", font=font_value, fill=COLOR_SAND)
    draw.text((70, card_y + 82), f"IPFS CID: {ipfs_cid[:44]}...", font=font_mono, fill=COLOR_TEAL)
    draw.text((70, card_y + 108), f"Generated: {evidence_bundle.get('generated_at', '')}", font=font_mono, fill=COLOR_DIM)
    draw.text((70, card_y + 134), "Scan QR to view the transaction on PolygonScan ->", font=font_mono, fill=COLOR_DIM)

    # QR code
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(explorer_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=COLOR_SAND, back_color=COLOR_CARD).convert("RGB")
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
