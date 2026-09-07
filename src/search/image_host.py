"""Temporarily host a local image publicly (via Pinata/IPFS) so SerpApi's
Google Lens engine — which requires a public image URL, not raw bytes — can
fetch it.
"""
import io

import requests
from PIL import Image

from src.config import PINATA_JWT

PINATA_PIN_FILE_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
IPFS_GATEWAY_URL = "https://gateway.pinata.cloud/ipfs/{cid}"
MAX_DIMENSION = 1600  # live-eval photos (phone cameras etc.) can be huge; downscale for fast, reliable upload


class ImageHostError(Exception):
    """Raised when the query image could not be pinned/hosted publicly."""


def _prepare_upload_bytes(image_path: str) -> bytes:
    """Downscale oversized images before upload -- large phone-camera
    photos (multi-MB, 4000px+) were observed to cause slow/failing
    uploads. Search image quality doesn't need full resolution."""
    img = Image.open(image_path)
    img = img.convert("RGB")
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def upload_image_get_public_url(image_path: str) -> str:
    if not PINATA_JWT:
        raise ImageHostError("PINATA_JWT is not set in .env")

    image_bytes = _prepare_upload_bytes(image_path)
    files = {"file": ("query_image.jpg", image_bytes)}
    try:
        response = requests.post(
            PINATA_PIN_FILE_URL,
            files=files,
            headers={"Authorization": f"Bearer {PINATA_JWT}"},
            timeout=60,
        )
    except requests.RequestException as e:
        raise ImageHostError(f"Pinata upload failed: {e}") from e

    if response.status_code != 200:
        raise ImageHostError(f"Pinata upload failed ({response.status_code}): {response.text}")

    cid = response.json()["IpfsHash"]
    return IPFS_GATEWAY_URL.format(cid=cid)
