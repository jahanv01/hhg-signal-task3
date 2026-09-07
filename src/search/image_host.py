"""Temporarily host a local image publicly (via Pinata/IPFS) so SerpApi's
Google Lens engine — which requires a public image URL, not raw bytes — can
fetch it.
"""
import requests

from src.config import PINATA_JWT

PINATA_PIN_FILE_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
IPFS_GATEWAY_URL = "https://gateway.pinata.cloud/ipfs/{cid}"


class ImageHostError(Exception):
    """Raised when the query image could not be pinned/hosted publicly."""


def upload_image_get_public_url(image_path: str) -> str:
    if not PINATA_JWT:
        raise ImageHostError("PINATA_JWT is not set in .env")

    with open(image_path, "rb") as f:
        files = {"file": (image_path.split("\\")[-1].split("/")[-1], f)}
        response = requests.post(
            PINATA_PIN_FILE_URL,
            files=files,
            headers={"Authorization": f"Bearer {PINATA_JWT}"},
            timeout=30,
        )

    if response.status_code != 200:
        raise ImageHostError(f"Pinata upload failed ({response.status_code}): {response.text}")

    cid = response.json()["IpfsHash"]
    return IPFS_GATEWAY_URL.format(cid=cid)
