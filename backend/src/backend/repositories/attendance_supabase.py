"""Supabase Data API implementation of daily attendance persistence."""

from __future__ import annotations

import logging
from datetime import date, datetime

from backend.models.domain import Attendance
from backend.repositories.supabase_rest import SupabaseRestClient

logger = logging.getLogger(__name__)


class AttendanceSupabaseRepository:
    def __init__(self, client: SupabaseRestClient) -> None:
        self._client = client

    def list_for_date(self, attendance_date: date) -> list[Attendance]:
        rows = self._client.request(
            "GET",
            "attendance",
            query={
                "select": "*",
                "attendance_date": f"eq.{attendance_date.isoformat()}",
                "order": "arrived_at.asc",
            },
        )
        return [self._deserialize(row) for row in rows]

    def mark_arrived(
        self, employee_id: str, arrived_at: datetime, distance: float
    ) -> bool:
        row = {
            "attendance_date": arrived_at.date().isoformat(),
            "employee_id": employee_id,
            "is_arrive": True,
            "arrived_at": arrived_at.isoformat(),
            "last_distance": distance,
        }
        created = self._client.request(
            "POST",
            "attendance",
            query={"on_conflict": "attendance_date,employee_id"},
            payload=row,
            prefer="resolution=ignore-duplicates,return=representation",
        )
        logger.info(
            "Attendance %s in Supabase | employee_id=%s | date=%s",
            "created" if created else "already existed",
            employee_id,
            arrived_at.date(),
        )
        return bool(created)

    @staticmethod
    def _deserialize(row: dict[str, object]) -> Attendance:
        return Attendance(
            attendance_date=date.fromisoformat(str(row["attendance_date"])),
            employee_id=str(row["employee_id"]),
            is_arrive=bool(row["is_arrive"]),
            arrived_at=datetime.fromisoformat(str(row["arrived_at"]).replace("Z", "+00:00")),
            last_distance=float(row["last_distance"]),
            departed_at=datetime.fromisoformat(str(row["departed_at"]).replace("Z", "+00:00")) if row.get("departed_at") else None,
        )

    def mark_departed(self, employee_id: str, departed_at: datetime, distance: float) -> bool:
        updated = self._client.request(
            "PATCH", "attendance",
            query={
                "employee_id": f"eq.{employee_id}",
                "attendance_date": f"eq.{departed_at.date().isoformat()}",
                "departed_at": "is.null",
                "arrived_at": f"lte.{departed_at.isoformat()}",
            },
            payload={"departed_at": departed_at.isoformat(), "last_distance": distance},
            prefer="return=representation",
        )
        return bool(updated)
