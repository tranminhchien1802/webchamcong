"""CSV implementation of daily attendance persistence."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from threading import RLock

from backend.models.domain import Attendance
from backend.repositories.csv_utils import atomic_write_rows, ensure_csv, read_rows

FIELDS = (
    "attendance_date",
    "employee_id",
    "is_arrive",
    "arrived_at",
    "last_distance",
    "departed_at",
)
logger = logging.getLogger(__name__)


class AttendanceCsvRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = RLock()
        with self._lock:
            ensure_csv(self._path, FIELDS)
        logger.info("Attendance CSV ready | path=%s", self._path.resolve())

    def list_for_date(self, attendance_date: date) -> list[Attendance]:
        with self._lock:
            attendance = [
                self._deserialize(row)
                for row in read_rows(self._path)
                if row["attendance_date"] == attendance_date.isoformat()
            ]
        logger.debug(
            "Attendance CSV read | path=%s | date=%s | rows=%d",
            self._path.resolve(),
            attendance_date,
            len(attendance),
        )
        return attendance

    def mark_arrived(
        self, employee_id: str, arrived_at: datetime, distance: float
    ) -> bool:
        """Create today's arrival once and return whether a row was created."""

        attendance_date = arrived_at.date()
        with self._lock:
            rows = read_rows(self._path)
            already_arrived = any(
                row["attendance_date"] == attendance_date.isoformat()
                and row["employee_id"] == employee_id
                and row["is_arrive"].casefold() == "true"
                for row in rows
            )
            if already_arrived:
                logger.info(
                    "Attendance already recorded | path=%s | employee_id=%s | date=%s",
                    self._path.resolve(),
                    employee_id,
                    attendance_date,
                )
                return False

            rows.append(
                self._serialize(
                    Attendance(
                        attendance_date=attendance_date,
                        employee_id=employee_id,
                        is_arrive=True,
                        arrived_at=arrived_at,
                        last_distance=distance,
                    )
                )
            )
            atomic_write_rows(self._path, FIELDS, rows)
            logger.info(
                "Attendance CSV written | path=%s | employee_id=%s | date=%s | "
                "distance=%.4f | rows=%d",
                self._path.resolve(),
                employee_id,
                attendance_date,
                distance,
                len(rows),
            )
            return True

    @staticmethod
    def _serialize(attendance: Attendance) -> dict[str, object]:
        return {
            "attendance_date": attendance.attendance_date.isoformat(),
            "employee_id": attendance.employee_id,
            "is_arrive": str(attendance.is_arrive).lower(),
            "arrived_at": attendance.arrived_at.isoformat(),
            "last_distance": attendance.last_distance,
            "departed_at": attendance.departed_at.isoformat() if attendance.departed_at else "",
        }

    @staticmethod
    def _deserialize(row: dict[str, str]) -> Attendance:
        return Attendance(
            attendance_date=date.fromisoformat(row["attendance_date"]),
            employee_id=row["employee_id"],
            is_arrive=row["is_arrive"].casefold() == "true",
            arrived_at=datetime.fromisoformat(row["arrived_at"]),
            last_distance=float(row["last_distance"]),
            departed_at=datetime.fromisoformat(row["departed_at"]) if row.get("departed_at") else None,
        )

    def mark_departed(self, employee_id: str, departed_at: datetime, distance: float) -> bool:
        with self._lock:
            rows = read_rows(self._path)
            for row in rows:
                if row["employee_id"] == employee_id and row["attendance_date"] == departed_at.date().isoformat():
                    if row.get("departed_at"):
                        return False
                    if departed_at < datetime.fromisoformat(row["arrived_at"]):
                        raise ValueError("Giờ ra không thể trước giờ vào.")
                    row["departed_at"] = departed_at.isoformat()
                    row["last_distance"] = distance
                    atomic_write_rows(self._path, FIELDS, rows)
                    return True
            raise ValueError("Chưa có giờ vào hôm nay.")
