"""DeepFace anti-spoofing check for uploaded recognition frames."""

from __future__ import annotations

import logging
import sys

import cv2

from backend.config import Settings
from backend.services.image_loader import ImageInput, load_rgb_image

logger = logging.getLogger(__name__)


class SpoofDetectedError(ValueError):
    """Raised when DeepFace classifies a detected face as a spoof."""


class LivenessCheckUnavailableError(RuntimeError):
    """Raised when the anti-spoofing model cannot run safely."""


class FaceLivenessDetector:
    """Reject frames that DeepFace classifies as a photo or screen replay."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.anti_spoofing_enabled

    def check(self, image: ImageInput) -> None:
        """Verify every detected face is classified as real.

        DeepFace is imported lazily so application startup does not load its
        framework or weights. It caches the loaded anti-spoof model between
        requests after the first check.
        """

        if not self._enabled:
            return

        rgb_image = load_rgb_image(image)
        bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)

        try:
            # DeepFace prints Unicode status symbols; Windows console encodings
            # such as cp1252 cannot encode them and otherwise abort model setup.
            stdout = sys.stdout
            reconfigure_stdout = getattr(stdout, "reconfigure", None)
            if sys.platform == "win32" and callable(reconfigure_stdout):
                reconfigure_stdout(errors="backslashreplace")

            from deepface import DeepFace

            face_objects = DeepFace.extract_faces(
                img_path=bgr_image,
                detector_backend="opencv",
                enforce_detection=False,
                anti_spoofing=True,
            )
        except Exception as error:
            logger.exception("DeepFace anti-spoofing check failed")
            raise LivenessCheckUnavailableError(
                "face liveness check is temporarily unavailable"
            ) from error

        if not face_objects:
            raise SpoofDetectedError("Không xác minh được khuôn mặt thật; chưa ghi chấm công.")
        for face_object in face_objects:
            is_real = face_object.get("is_real")
            if is_real is None or not bool(is_real):
                score = face_object.get("antispoof_score")
                logger.warning(
                    "Spoof face rejected | antispoof_score=%s",
                    score if score is not None else "unavailable",
                )
                raise SpoofDetectedError(
                    "a photo or screen replay was detected; use a live face"
                )

        logger.info("DeepFace liveness check passed | faces=%d", len(face_objects))
