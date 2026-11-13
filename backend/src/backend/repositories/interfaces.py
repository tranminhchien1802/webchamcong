"""Structural repository contracts shared by CSV and Supabase stores."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from backend.models.domain import Attendance, Employee


class EmployeeRepository(Protocol):
    def list_all(self) -> list[Employee]: ...

    def get_by_id(self, employee_id: str) -> Employee | None: ...

    def create(self, employee: Employee) -> Employee: ...


class AttendanceRepository(Protocol):
    def mark_departed(
        self, employee_id: str, departed_at: datetime, distance: float
    ) -> bool: ...

    def list_for_date(self, attendance_date: date) -> list[Attendance]: ...

    def mark_arrived(
        self, employee_id: str, arrived_at: datetime, distance: float
    ) -> bool: ...
