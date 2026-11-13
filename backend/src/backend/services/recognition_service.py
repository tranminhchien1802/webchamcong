"""Recognize camera frames and apply daily attendance updates."""

from __future__ import annotations

import logging

from backend.models.schemas import (
    FaceLocationResponse,
    RecognitionResponse,
    RecognizedFaceResponse,
)
from backend.repositories.interfaces import EmployeeRepository
from backend.services.attendance_service import AttendanceService, AttendanceValidationError
from backend.services.face_liveness import FaceLivenessDetector
from backend.services.face_recognizer import FaceRecognizer, KnownFace

logger = logging.getLogger(__name__)


class RecognitionService:
    def __init__(
        self,
        employee_repository: EmployeeRepository,
        attendance_service: AttendanceService,
        face_recognizer: FaceRecognizer,
        face_liveness_detector: FaceLivenessDetector,
    ) -> None:
        self._employees = employee_repository
        self._attendance = attendance_service
        self._face_recognizer = face_recognizer
        self._face_liveness_detector = face_liveness_detector

    def recognize_and_mark_arrival(self, image: bytes, action: str = "in") -> RecognitionResponse:
        if action not in {"in", "out"}:
            raise AttendanceValidationError("Invalid attendance action")
        self._face_liveness_detector.check(image)
        employees = self._employees.list_all()
        known_faces = [
            KnownFace(
                employee_id=employee.employee_id,
                name=employee.name,
                encoding=employee.face_encoding,
            )
            for employee in employees
        ]
        logger.info(
            "Recognition processing started | image_bytes=%d | known_employees=%d",
            len(image),
            len(known_faces),
        )
        results = self._face_recognizer.recognize(image, known_faces)
        if len(results) > 1:
            raise AttendanceValidationError("Chỉ một người được đứng trước camera khi chấm công.")
        logger.info(
            "Face detection completed | detected=%d | matched=%d | unknown=%d",
            len(results),
            sum(result.matched for result in results),
            sum(not result.matched for result in results),
        )

        attendance_updated: list[str] = []
        processed_employee_ids: set[str] = set()
        for result in results:
            if (
                result.employee_id is None
                or result.distance is None
                or result.employee_id in processed_employee_ids
            ):
                if result.employee_id is None:
                    logger.info(
                        "Face not matched | name=%s | nearest_distance=%s | location=%s",
                        result.name,
                        (
                            f"{result.distance:.4f}"
                            if result.distance is not None
                            else "unavailable"
                        ),
                        result.location,
                    )
                continue
            processed_employee_ids.add(result.employee_id)
            record = self._attendance.mark_departed if action == "out" else self._attendance.mark_arrived
            created = record(
                result.employee_id, result.distance, image
            )
            logger.info(
                "Face matched | employee_id=%s | name=%r | distance=%.4f | "
                "attendance_created=%s | location=%s",
                result.employee_id,
                result.name,
                result.distance,
                created,
                result.location,
            )
            if created:
                attendance_updated.append(result.employee_id)

        faces = []
        for result in results:
            top, right, bottom, left = result.location
            faces.append(
                RecognizedFaceResponse(
                    employee_id=result.employee_id,
                    name=result.name,
                    distance=result.distance,
                    location=FaceLocationResponse(
                        top=top, right=right, bottom=bottom, left=left
                    ),
                )
            )
        return RecognitionResponse(
            faces=faces,
            attendance_updated=attendance_updated,
        )
