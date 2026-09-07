import os
from unittest.mock import patch

import cv2

from src.face.detector import detect_primary_face
from src.face.encoder import encode_face
from src.search import matcher
from src.search.serpapi_client import SearchCandidate

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_images")
FACE_IMAGE = os.path.join(SAMPLE_DIR, "test1.jpg")
NO_FACE_IMAGE = os.path.join(SAMPLE_DIR, "no_face.jpg")


def _candidate(link: str) -> SearchCandidate:
    return SearchCandidate(title="t", link=link, source="s", thumbnail=link, position=0)


def test_verify_candidates_identifies_genuine_and_rejects_no_face():
    query_face = detect_primary_face(FACE_IMAGE)
    query_embedding = encode_face(query_face.crop).vector

    same_face_img = cv2.imread(FACE_IMAGE)
    no_face_img = cv2.imread(NO_FACE_IMAGE)

    candidates = [_candidate("https://example.com/same"), _candidate("https://example.com/blank")]

    def fake_download(url: str, timeout: int = 10):
        return same_face_img if "same" in url else no_face_img

    with patch.object(matcher, "_download_image", side_effect=fake_download):
        results = matcher.verify_candidates(query_embedding, candidates)

    assert len(results) == 2

    same = next(r for r in results if r.candidate.link == "https://example.com/same")
    blank = next(r for r in results if r.candidate.link == "https://example.com/blank")

    assert same.is_face_match is True
    assert same.face_distance < 0.05
    assert blank.is_face_match is False
    assert blank.face_distance is None

    best = matcher.best_match(results)
    assert best is not None
    assert best.candidate.link == "https://example.com/same"


def test_best_match_returns_none_when_no_genuine_match():
    results = [
        matcher.VerifiedMatch(_candidate("https://example.com/a"), None, False, 0.0),
    ]
    assert matcher.best_match(results) is None
