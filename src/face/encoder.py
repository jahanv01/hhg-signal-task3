"""Face encoding: turn a face crop into an ArcFace embedding vector."""
from dataclasses import dataclass

import numpy as np
from deepface import DeepFace

MODEL_NAME = "ArcFace"


@dataclass
class FaceEmbedding:
    vector: np.ndarray   # 512-d ArcFace embedding
    model: str = MODEL_NAME


def encode_face(face_crop: np.ndarray) -> FaceEmbedding:
    """Compute an ArcFace embedding for a BGR face crop (as produced by detector.py)."""
    result = DeepFace.represent(
        img_path=face_crop,
        model_name=MODEL_NAME,
        detector_backend="skip",  # crop is already a detected/aligned face
        enforce_detection=False,
    )
    vector = np.array(result[0]["embedding"], dtype=np.float32)
    return FaceEmbedding(vector=vector)


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """1 - cosine similarity. 0 = identical direction, 2 = opposite."""
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b) + 1e-10)
    return float(1.0 - np.dot(a_norm, b_norm))
