"""Public API request and response contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmployeeCreated(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str
    name: str
    image_filename: str


class EmployeeAttendance(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str
    name: str
    is_arrive: bool
    arrived_at: datetime | None
    departed_at: datetime | None = None


class FaceLocationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    top: int
    right: int
    bottom: int
    left: int


class RecognizedFaceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str | None
    name: str
    distance: float | None
    location: FaceLocationResponse


class RecognitionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    faces: list[RecognizedFaceResponse]
    attendance_updated: list[str]
