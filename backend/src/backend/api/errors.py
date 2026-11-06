"""Translate domain validation errors into HTTP responses."""

from fastapi import HTTPException

from backend.repositories.employee_csv import DuplicateEmployeeError
from backend.repositories.supabase_rest import SupabaseRequestError
from backend.services.employee_service import (
    DuplicateFaceError,
    InvalidEmployeeNameError,
)
from backend.services.face_encoder import FaceEncodingError
from backend.services.image_loader import InvalidImageError
from backend.services.upload_service import UploadValidationError


def as_http_exception(error: ValueError) -> HTTPException:
    if isinstance(error, (DuplicateEmployeeError, DuplicateFaceError)):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, UploadValidationError):
        return HTTPException(status_code=error.status_code, detail=str(error))
    if isinstance(
        error, (InvalidEmployeeNameError, FaceEncodingError, InvalidImageError)
    ):
        return HTTPException(status_code=422, detail=str(error))
    return HTTPException(status_code=500, detail="internal application error")


def database_http_exception(error: Exception) -> HTTPException:
    """Map expected database failures to safe API responses."""

    if isinstance(error, DuplicateEmployeeError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, SupabaseRequestError):
        if error.status in {401, 403}:
            return HTTPException(status_code=503, detail="database credentials are invalid")
        if error.status in {400, 404, 409, 422}:
            return HTTPException(status_code=503, detail="database rejected the operation")
        return HTTPException(status_code=503, detail="database is temporarily unavailable")
    return HTTPException(status_code=500, detail="internal application error")
