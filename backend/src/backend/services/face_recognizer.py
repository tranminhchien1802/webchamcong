"""Detect and match faces against known employee encodings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import cv2
import face_recognition
import numpy as np

from backend.config import Settings
from backend.services.face_encoder import FaceEncoding, FaceLocation
from backend.services.image_loader import ImageInput, load_rgb_image


@dataclass(frozen=True, slots=True)
class KnownFace:
    """An employee identity and the encoding stored for it."""

    employee_id: str
    name: str
    encoding: FaceEncoding


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    """Recognition outcome for one detected face."""

    employee_id: str | None
    name: str
    distance: float | None
    location: FaceLocation

    @property
    def matched(self) -> bool:
        return self.employee_id is not None


class InvalidKnownFaceError(ValueError):
    """Raised when a stored known-face record is malformed."""


class FaceRecognizer:
    """Recognize every detectable face in an image."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def recognize(
        self, image: ImageInput, known_faces: Iterable[KnownFace]
    ) -> list[RecognitionResult]:
        """Match faces in ``image`` to the nearest accepted known encoding."""

        rgb_image = load_rgb_image(image)
        scaled_image = self._scale_image(rgb_image)
        locations = face_recognition.face_locations(
            scaled_image,
            number_of_times_to_upsample=self._settings.number_of_times_to_upsample,
            model=self._settings.detection_model,
        )
        encodings = face_recognition.face_encodings(
            scaled_image,
            known_face_locations=locations,
            num_jitters=self._settings.number_of_jitters,
            model=self._settings.encoding_model,
        )

        known = list(known_faces)
        known_matrix = self._known_encoding_matrix(known)
        results: list[RecognitionResult] = []

        for location, candidate in zip(locations, encodings, strict=True):
            original_location = self._restore_location(location, rgb_image.shape[:2])
            if len(known) == 0:
                results.append(self._unknown(original_location))
                continue

            distances = face_recognition.face_distance(known_matrix, candidate)
            best_index = int(np.argmin(distances))
            best_distance = float(distances[best_index])

            alternatives = [float(distance) for index, distance in enumerate(distances) if known[index].employee_id != known[best_index].employee_id]
            unambiguous = not alternatives or min(alternatives) - best_distance >= 0.05
            if np.isfinite(distances).all() and best_distance <= self._settings.recognition_tolerance and unambiguous:
                match = known[best_index]
                results.append(
                    RecognitionResult(
                        employee_id=match.employee_id,
                        name=match.name,
                        distance=best_distance,
                        location=original_location,
                    )
                )
            else:
                results.append(self._unknown(original_location, best_distance))

        return results

    def _scale_image(self, image: np.ndarray) -> np.ndarray:
        scale = self._settings.recognition_frame_scale
        if scale == 1.0:
            return image
        return cv2.resize(image, (0, 0), fx=scale, fy=scale)

    def _restore_location(
        self, location: FaceLocation, original_size: tuple[int, int]
    ) -> FaceLocation:
        scale = self._settings.recognition_frame_scale
        if scale == 1.0:
            return location

        height, width = original_size
        top, right, bottom, left = location
        return (
            max(0, min(height, round(top / scale))),
            max(0, min(width, round(right / scale))),
            max(0, min(height, round(bottom / scale))),
            max(0, min(width, round(left / scale))),
        )

    @staticmethod
    def _known_encoding_matrix(known_faces: list[KnownFace]) -> np.ndarray:
        if not known_faces:
            return np.empty((0, 128), dtype=np.float64)

        encodings: list[np.ndarray] = []
        for known_face in known_faces:
            encoding = np.asarray(known_face.encoding, dtype=np.float64)
            if encoding.shape != (128,) or not np.isfinite(encoding).all():
                raise InvalidKnownFaceError(
                    f"encoding for employee {known_face.employee_id!r} must have 128 values"
                )
            encodings.append(encoding)
        return np.stack(encodings)

    @staticmethod
    def _unknown(
        location: FaceLocation, distance: float | None = None
    ) -> RecognitionResult:
        return RecognitionResult(
            employee_id=None,
            name="Unknown",
            distance=distance,
            location=location,
        )
