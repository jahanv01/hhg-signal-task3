"""Face detection: locate and crop the primary face in an image."""
from dataclasses import dataclass

import cv2
import numpy as np
from deepface import DeepFace


class NoFaceFoundError(Exception):
    """Raised when no face can be detected in the given image."""


@dataclass
class DetectedFace:
    crop: np.ndarray          # BGR face crop, ready for the encoder
    confidence: float         # detector confidence score
    box: tuple[int, int, int, int]  # x, y, w, h in the original image


def detect_primary_face(image_path: str, detector_backend: str = "opencv") -> DetectedFace:
    """Detect all faces in the image and return the largest one.

    Raises NoFaceFoundError if no face is detected.
    """
    try:
        faces = DeepFace.extract_faces(
            img_path=image_path,
            detector_backend=detector_backend,
            enforce_detection=True,
            align=True,
        )
    except ValueError as exc:
        raise NoFaceFoundError(f"No face detected in {image_path}") from exc

    if not faces:
        raise NoFaceFoundError(f"No face detected in {image_path}")

    def area(face: dict) -> int:
        region = face["facial_area"]
        return region["w"] * region["h"]

    best = max(faces, key=area)
    region = best["facial_area"]
    crop_float = best["face"]  # RGB float array in [0, 1]
    crop_bgr = cv2.cvtColor((crop_float * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)

    return DetectedFace(
        crop=crop_bgr,
        confidence=float(best.get("confidence", 0.0)),
        box=(region["x"], region["y"], region["w"], region["h"]),
    )
