"""Internal domain records persisted by repositories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from backend.services.face_encoder import FaceEncoding


@dataclass(frozen=True, slots=True)
class Employee:
    employee_id: str
    name: str
    image_filename: str
    face_encoding: FaceEncoding
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Attendance:
    attendance_date: date
    employee_id: str
    is_arrive: bool
    arrived_at: datetime
    last_distance: float
    departed_at: datetime | None = None
