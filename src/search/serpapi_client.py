"""Reverse image search via SerpApi's Google Lens engine.

Requires a public image URL (see image_host.py). Responses are cached
locally per source-image hash so repeated dev/test runs don't burn
SerpApi quota searching the same image twice.
"""
from dataclasses import dataclass

from serpapi import GoogleSearch

from src.config import SERPAPI_API_KEY
from src.search import cache
from src.search.image_host import upload_image_get_public_url

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


def _run_google_lens(image_url: str) -> dict:
    if not SERPAPI_API_KEY:
        raise SearchError("SERPAPI_API_KEY is not set in .env")

    search = GoogleSearch({
        "engine": "google_lens",
        "url": image_url,
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
            public_url = upload_image_get_public_url(image_path)
            raw = _run_google_lens(public_url)
            cache.set(image_path, raw)
    else:
        public_url = upload_image_get_public_url(image_path)
        raw = _run_google_lens(public_url)

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
    """Prefer known social-media domains; fall back to all candidates if none match."""
    social = [c for c in candidates if any(domain in c.link for domain in SOCIAL_DOMAINS)]
    return social if social else candidates
