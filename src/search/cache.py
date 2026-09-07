"""File-based response cache so repeated dev/test runs never re-spend
SerpApi quota on an image we've already searched."""
import hashlib
import json
import os

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "serpapi_cache")


def _key_for(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def get(image_path: str) -> dict | None:
    key = _key_for(image_path)
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def set(image_path: str, response: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = _key_for(image_path)
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(response, f)
