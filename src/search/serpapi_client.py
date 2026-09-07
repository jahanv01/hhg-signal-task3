"""Reverse image search via SerpApi's Google Lens engine.

Uses SerpApi's own /image upload endpoint (returns a short-lived
image_id) rather than hosting the image on a third-party public URL.
This was a deliberate fix: hosting via a public IPFS gateway (Pinata)
was observed to take ~7s to respond, which silently caused Google's
own Lens fetch to time out -- SerpApi reported "Success" but with zero
visual matches, even for well-indexed public figures. SerpApi's own
upload infrastructure is fast and reliable since Lens fetches directly
from it.

Responses are cached locally per source-image hash so repeated
dev/test runs don't burn SerpApi quota searching the same image twice.
"""
import io
from dataclasses import dataclass

import requests
from PIL import Image
from serpapi import GoogleSearch

from src.config import SERPAPI_API_KEY
from src.search import cache

SERPAPI_IMAGE_UPLOAD_URL = "https://serpapi.com/image"
MAX_UPLOAD_BYTES = 480_000  # SerpApi's /image endpoint caps at 500KB

SOCIAL_DOMAINS = (
    "instagram.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "linkedin.com",
    "tiktok.com",
    "pinterest.com",
    "reddit.com",
    "youtube.com",
)


class SearchError(Exception):
    """Raised when the reverse image search could not be completed."""


@dataclass
class SearchCandidate:
    title: str
    link: str
    source: str
    thumbnail: str
    position: int


def _prepare_image_bytes(image_path: str, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    """Re-encode as JPEG, shrinking dimensions/quality until under max_bytes."""
    img = Image.open(image_path).convert("RGB")
    max_dim = 1600
    quality = 88

    while True:
        resized = img.copy()
        resized.thumbnail((max_dim, max_dim))
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=quality)
        data = buf.getvalue()
        if len(data) <= max_bytes or (max_dim <= 400 and quality <= 40):
            return data
        # Still too big: shrink dimensions first, then drop quality.
        if max_dim > 400:
            max_dim = int(max_dim * 0.8)
        else:
            quality = max(40, quality - 15)


def _upload_image_for_lens(image_path: str) -> str:
    if not SERPAPI_API_KEY:
        raise SearchError("SERPAPI_API_KEY is not set in .env")

    image_bytes = _prepare_image_bytes(image_path)
    try:
        response = requests.post(
            SERPAPI_IMAGE_UPLOAD_URL,
            files={"image": ("query_image.jpg", image_bytes, "image/jpeg")},
            data={"api_key": SERPAPI_API_KEY},
            timeout=30,
        )
    except requests.RequestException as e:
        raise SearchError(f"SerpApi image upload failed: {e}") from e

    if response.status_code != 200:
        raise SearchError(f"SerpApi image upload failed ({response.status_code}): {response.text}")

    image_id = response.json().get("image_id")
    if not image_id:
        raise SearchError(f"SerpApi image upload returned no image_id: {response.text}")
    return image_id


def _run_google_lens(image_id: str) -> dict:
    search = GoogleSearch({
        "engine": "google_lens",
        "image_id": image_id,
        "api_key": SERPAPI_API_KEY,
    })
    result = search.get_dict()

    if "error" in result:
        raise SearchError(f"SerpApi error: {result['error']}")

    return result


def reverse_image_search(image_path: str, use_cache: bool = True) -> list[SearchCandidate]:
    """Search the web for pages visually matching the given local image.

    Returns candidates ranked as returned by Google Lens (most relevant first).
    """
    if use_cache:
        cached = cache.get(image_path)
        if cached is not None:
            raw = cached
        else:
            image_id = _upload_image_for_lens(image_path)
            raw = _run_google_lens(image_id)
            cache.set(image_path, raw)
    else:
        image_id = _upload_image_for_lens(image_path)
        raw = _run_google_lens(image_id)

    matches = raw.get("visual_matches", [])
    return [
        SearchCandidate(
            title=m.get("title", ""),
            link=m.get("link", ""),
            source=m.get("source", ""),
            thumbnail=m.get("thumbnail", ""),
            position=m.get("position", i),
        )
        for i, m in enumerate(matches)
    ]


def filter_social_candidates(candidates: list[SearchCandidate]) -> list[SearchCandidate]:
    """Prefer known social-media domains; fall back to all candidates if none match.

    General-purpose utility -- for the strict "must actually be a social media
    post" requirement the pipeline enforces, see social_only_candidates().
    """
    social = [c for c in candidates if any(domain in c.link for domain in SOCIAL_DOMAINS)]
    return social if social else candidates


def social_only_candidates(candidates: list[SearchCandidate]) -> list[SearchCandidate]:
    """Strictly known social-media domains only, no fallback. The task
    requires the final matched result to genuinely be a social media post,
    not just any visually-similar webpage."""
    return [c for c in candidates if any(domain in c.link for domain in SOCIAL_DOMAINS)]
