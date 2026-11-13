"""Camera-frame face recognition route."""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.api.dependencies import get_core
from backend.api.errors import as_http_exception, database_http_exception
from backend.main import CoreServices
from backend.models.schemas import RecognitionResponse
from backend.services.face_liveness import (
    LivenessCheckUnavailableError,
    SpoofDetectedError,
)

router = APIRouter(prefix="/api", tags=["recognition"])
logger = logging.getLogger(__name__)


@router.post("/recognize", response_model=RecognitionResponse)
def recognize_faces(
    image: Annotated[UploadFile, File()],
    core: Annotated[CoreServices, Depends(get_core)],
    action: Annotated[Literal["in", "out"], Form()] = "in",
) -> RecognitionResponse:
    logger.info(
        "Recognition requested | filename=%r | content_type=%r",
        image.filename,
        image.content_type,
    )
    try:
        image_bytes = core.upload_service.read_image(
            image.file, image.filename, image.content_type
        )
        if action == "out":
            response = core.recognition_service.recognize_and_mark_arrival(image_bytes, action)
        else:
            response = core.recognition_service.recognize_and_mark_arrival(image_bytes)
        logger.info(
            "Recognition completed | image_bytes=%d | faces=%d | matched=%d | attendance_updated=%s",
            len(image_bytes),
            len(response.faces),
            sum(face.employee_id is not None for face in response.faces),
            response.attendance_updated,
        )
        return response
    except SpoofDetectedError as error:
        logger.warning("Recognition rejected as spoof | filename=%r", image.filename)
        raise HTTPException(status_code=403, detail=str(error)) from error
    except LivenessCheckUnavailableError as error:
        logger.exception("Recognition blocked because liveness check is unavailable")
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        logger.warning(
            "Recognition rejected | filename=%r | error=%s",
            image.filename,
            error,
        )
        raise as_http_exception(error) from error
    except Exception as error:
        logger.exception("Recognition storage failed")
        raise database_http_exception(error) from error
    finally:
        image.file.close()
