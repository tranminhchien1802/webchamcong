"""Daily attendance application service."""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable
from threading import RLock

from backend.models.domain import Attendance
from backend.repositories.interfaces import AttendanceRepository
from backend.repositories.attendance_photos import AttendancePhotoStore

Clock = Callable[[], datetime]


class AttendanceValidationError(ValueError):
    pass


class AttendanceService:
    def __init__(
        self, attendance_repository: AttendanceRepository, clock: Clock,
        photo_store: AttendancePhotoStore | None = None,
    ) -> None:
        self._attendance = attendance_repository
        self._clock = clock
        self._photos = photo_store
        self._lock = RLock()

    def date_or_today(self, attendance_date: date | None) -> date:
        return attendance_date or self._clock().date()

    def by_employee_for_date(
        self, attendance_date: date
    ) -> dict[str, Attendance]:
        return {
            item.employee_id: item
            for item in self._attendance.list_for_date(attendance_date)
            if item.is_arrive
        }

    def mark_arrived(self, employee_id: str, distance: float, image: bytes | None = None) -> bool:
        with self._lock:
            now = self._clock()
            if self._photos is not None:
                if self.by_employee_for_date(now.date()).get(employee_id):
                    return False
                if image is None:
                    raise AttendanceValidationError("Thiếu ảnh chấm công.")
                self._photos.save(employee_id, now.date(), "in", image)
            return self._attendance.mark_arrived(
                employee_id=employee_id, arrived_at=now, distance=distance,
            )

    def mark_departed(self, employee_id: str, distance: float, image: bytes | None = None) -> bool:
        with self._lock:
            return self._mark_departed(employee_id, distance, image)

    def _mark_departed(self, employee_id: str, distance: float, image: bytes | None) -> bool:
        now = self._clock()
        attendance = self.by_employee_for_date(now.date()).get(employee_id)
        if attendance is None:
            raise AttendanceValidationError("Chưa có giờ vào hôm nay; hãy chấm Vào ca trước.")
        if now < attendance.arrived_at:
            raise AttendanceValidationError("Giờ ra không thể trước giờ vào.")
        if attendance.departed_at is not None:
            return False
        if self._photos is not None:
            if image is None:
                raise AttendanceValidationError("Thiếu ảnh chấm công.")
            self._photos.save(employee_id, now.date(), "out", image)
        return self._attendance.mark_departed(employee_id, now, distance)
