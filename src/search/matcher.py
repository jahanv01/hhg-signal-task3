"""Re-verify search candidates by re-running face recognition on each
candidate's image and comparing it against the original query face.

This is what separates "visually similar image" (what Google Lens gives us)
from "genuinely the same face" (what the task actually needs).
"""
from dataclasses import dataclass

import cv2
import numpy as np
import requests

from src.config import FACE_MATCH_DISTANCE_THRESHOLD
from src.face.detector import NoFaceFoundError, detect_primary_face
from src.face.encoder import cosine_distance, encode_face
from src.search.serpapi_client import SearchCandidate


@dataclass
class VerifiedMatch:
    candidate: SearchCandidate
    face_distance: float | None  # None if no face could be found in the candidate image
    is_face_match: bool
    confidence: float  # 0..1, higher = more confident same-face match


def _download_image(url: str, timeout: int = 10) -> np.ndarray | None:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        arr = np.frombuffer(response.content, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def verify_candidates(
    query_embedding: np.ndarray,
    candidates: list[SearchCandidate],
    top_n: int = 10,
    threshold: float = FACE_MATCH_DISTANCE_THRESHOLD,
) -> list[VerifiedMatch]:
    """Download each candidate's thumbnail, re-encode any face found, and
    score it against the query embedding. Ranked highest-confidence first.
    """
    results: list[VerifiedMatch] = []

    for candidate in candidates[:top_n]:
        image = _download_image(candidate.thumbnail or candidate.link)
        if image is None:
            results.append(VerifiedMatch(candidate, None, False, 0.0))
            continue

        try:
            face = detect_primary_face(image)
            embedding = encode_face(face.crop)
        except NoFaceFoundError:
            results.append(VerifiedMatch(candidate, None, False, 0.0))
            continue

        distance = cosine_distance(query_embedding, embedding.vector)
        is_match = distance <= threshold
        confidence = max(0.0, 1.0 - distance)
        results.append(VerifiedMatch(candidate, distance, is_match, confidence))

    results.sort(key=lambda r: r.confidence, reverse=True)
    return results


def best_match(verified: list[VerifiedMatch]) -> VerifiedMatch | None:
    """Highest-confidence candidate that genuinely passed the face-match threshold."""
    genuine = [r for r in verified if r.is_face_match]
    return genuine[0] if genuine else None
