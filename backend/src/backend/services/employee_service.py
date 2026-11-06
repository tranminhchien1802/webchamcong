"""Employee enrollment and attendance-list application service."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Callable

import numpy as np

from backend.models.domain import Employee
from backend.models.schemas import EmployeeAttendance, EmployeeCreated
from backend.repositories.interfaces import EmployeeRepository
from backend.services.attendance_service import AttendanceService
from backend.services.face_encoder import FaceEncoder

Clock = Callable[[], datetime]
logger = logging.getLogger(__name__)


class InvalidEmployeeNameError(ValueError):
    pass


class DuplicateFaceError(ValueError):
    pass


class EmployeeService:
    def __init__(
        self,
        employee_repository: EmployeeRepository,
        attendance_service: AttendanceService,
        face_encoder: FaceEncoder,
        clock: Clock,
    ) -> None:
        self._employees = employee_repository
        self._attendance = attendance_service
        self._face_encoder = face_encoder
        self._clock = clock

    def enroll(self, name: str, image_filename: str, image: bytes) -> EmployeeCreated:
        normalized_name = " ".join(name.split())
        if not normalized_name:
            raise InvalidEmployeeNameError("employee name cannot be empty")
        if len(normalized_name) > 120:
            raise InvalidEmployeeNameError("employee name cannot exceed 120 characters")

        logger.info(
            "Encoding enrollment face | name=%r | filename=%r | image_bytes=%d",
            normalized_name,
            image_filename,
            len(image),
        )
        encoded_face = self._face_encoder.encode(image)
        candidate_encoding = np.asarray(encoded_face.encoding, dtype=np.float64)
        for existing in self._employees.list_all():
            existing_encoding = np.asarray(existing.face_encoding, dtype=np.float64)
            if (
                existing_encoding.shape != (128,)
                or not np.isfinite(existing_encoding).all()
            ):
                continue
            if float(np.linalg.norm(candidate_encoding - existing_encoding)) <= 0.05:
                raise DuplicateFaceError(
                    f"this face is already enrolled as {existing.name!r}"
                )
        logger.info(
            "Enrollment face encoded | name=%r | face_location=%s",
            normalized_name,
            encoded_face.location,
        )
        employee = Employee(
            employee_id="",
            name=normalized_name,
            image_filename=image_filename,
            face_encoding=encoded_face.encoding,
            created_at=self._clock(),
        )
        employee = self._employees.create(employee)
        logger.info(
            "Employee persisted | employee_id=%s | name=%r",
            employee.employee_id,
            employee.name,
        )

        return EmployeeCreated(
            employee_id=employee.employee_id,
            name=employee.name,
            image_filename=employee.image_filename,
        )

    def list_with_attendance(
        self, attendance_date: date | None = None
    ) -> list[EmployeeAttendance]:
        selected_date = self._attendance.date_or_today(attendance_date)
        attendance_by_employee = self._attendance.by_employee_for_date(selected_date)
        employees = self._employees.list_all()
        result = [
            EmployeeAttendance(
                employee_id=employee.employee_id,
                name=employee.name,
                is_arrive=employee.employee_id in attendance_by_employee,
                arrived_at=(
                    attendance_by_employee[employee.employee_id].arrived_at
                    if employee.employee_id in attendance_by_employee
                    else None
                ),
            )
            for employee in employees
        ]
        logger.debug(
            "Employee attendance view composed | date=%s | employees=%d | arrivals=%d",
            selected_date,
            len(result),
            len(attendance_by_employee),
        )
        return result
