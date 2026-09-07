"""Pin the full evidence bundle (JSON) to IPFS via Pinata.

Only the bundle's hash + this CID go on-chain (see blockchain/hasher.py and
blockchain/chain_client.py) -- the full bundle itself lives here, off-chain,
cheaply and durably.
"""
import requests

from src.config import PINATA_JWT

PINATA_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
IPFS_GATEWAY_URL = "https://gateway.pinata.cloud/ipfs/{cid}"


class IpfsError(Exception):
    """Raised when the evidence bundle could not be pinned to IPFS."""


def pin_json(bundle: dict, name: str = "evidence-bundle") -> str:
    """Pin a JSON evidence bundle to IPFS. Returns the CID."""
    if not PINATA_JWT:
        raise IpfsError("PINATA_JWT is not set in .env")

    payload = {
        "pinataContent": bundle,
        "pinataMetadata": {"name": name},
    }
    response = requests.post(
        PINATA_PIN_JSON_URL,
        json=payload,
        headers={"Authorization": f"Bearer {PINATA_JWT}"},
        timeout=30,
    )

    if response.status_code != 200:
        raise IpfsError(f"Pinata pinJSONToIPFS failed ({response.status_code}): {response.text}")

    return response.json()["IpfsHash"]


def gateway_url(cid: str) -> str:
    return IPFS_GATEWAY_URL.format(cid=cid)
