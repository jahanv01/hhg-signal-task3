import os

import pytest

from src.search import cache
from src.search.serpapi_client import filter_social_candidates, reverse_image_search

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_images")
FACE_IMAGE = os.path.join(SAMPLE_DIR, "test1.jpg")


@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path, monkeypatch):
    """Point the search cache at a throwaway directory for every test in
    this module, so seeding fixtures here never overwrites the real
    dev/app cache at data/serpapi_cache/ (which happened before this fix
    and silently broke a real cached SerpApi response)."""
    monkeypatch.setattr(cache, "CACHE_DIR", str(tmp_path))

FIXTURE_RESPONSE = {
    "visual_matches": [
        {
            "position": 1,
            "title": "Random blog post",
            "link": "https://someblog.example.com/post/1",
            "source": "someblog.example.com",
            "thumbnail": "https://example.com/thumb1.jpg",
        },
        {
            "position": 2,
            "title": "Jane Doe on Instagram",
            "link": "https://www.instagram.com/p/abc123/",
            "source": "instagram.com",
            "thumbnail": "https://example.com/thumb2.jpg",
        },
        {
            "position": 3,
            "title": "Jane Doe on X",
            "link": "https://x.com/janedoe/status/123",
            "source": "x.com",
            "thumbnail": "https://example.com/thumb3.jpg",
        },
    ]
}


def test_reverse_image_search_parses_cached_response():
    # Seed the cache so this test never calls the real SerpApi/Pinata APIs
    # and never spends quota.
    cache.set(FACE_IMAGE, FIXTURE_RESPONSE)

    candidates = reverse_image_search(FACE_IMAGE, use_cache=True)

    assert len(candidates) == 3
    assert candidates[0].link == "https://someblog.example.com/post/1"
    assert candidates[1].source == "instagram.com"


def test_filter_social_candidates_prefers_known_domains():
    cache.set(FACE_IMAGE, FIXTURE_RESPONSE)
    candidates = reverse_image_search(FACE_IMAGE, use_cache=True)

    social = filter_social_candidates(candidates)

    assert len(social) == 2
    assert all(
        any(d in c.link for d in ("instagram.com", "x.com")) for c in social
    )


def test_filter_social_candidates_falls_back_to_all_when_no_social_match():
    no_social = {
        "visual_matches": [
            {
                "position": 1,
                "title": "Random blog post",
                "link": "https://someblog.example.com/post/1",
                "source": "someblog.example.com",
                "thumbnail": "https://example.com/thumb1.jpg",
            }
        ]
    }
    cache.set(FACE_IMAGE, no_social)
    candidates = reverse_image_search(FACE_IMAGE, use_cache=True)

    social = filter_social_candidates(candidates)

    assert len(social) == 1
    assert social[0].link == "https://someblog.example.com/post/1"
