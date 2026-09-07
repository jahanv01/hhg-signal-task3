import os

import pytest

from src.face.detector import NoFaceFoundError, detect_primary_face
from src.face.encoder import cosine_distance, encode_face

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_images")
FACE_IMAGE = os.path.join(SAMPLE_DIR, "test1.jpg")
NO_FACE_IMAGE = os.path.join(SAMPLE_DIR, "no_face.jpg")


def test_detect_primary_face_finds_a_face():
    face = detect_primary_face(FACE_IMAGE)
    assert face.crop.size > 0
    assert face.confidence > 0
    assert len(face.box) == 4


def test_detect_primary_face_raises_on_no_face():
    with pytest.raises(NoFaceFoundError):
        detect_primary_face(NO_FACE_IMAGE)


def test_encode_face_returns_512d_embedding():
    face = detect_primary_face(FACE_IMAGE)
    embedding = encode_face(face.crop)
    assert embedding.vector.shape == (512,)


def test_encode_face_is_self_consistent():
    face = detect_primary_face(FACE_IMAGE)
    emb1 = encode_face(face.crop)
    emb2 = encode_face(face.crop)
    assert cosine_distance(emb1.vector, emb2.vector) < 1e-4
