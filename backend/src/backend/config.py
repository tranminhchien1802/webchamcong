"""Application configuration.

Settings are intentionally dependency-free. They can be constructed directly in
tests or loaded from environment variables by the application entry point.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

DetectionModel = Literal["hog", "cnn"]
EncodingModel = Literal["small", "large"]
StorageBackend = Literal["csv", "supabase"]
LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration used by the face encoding and recognition services."""

    recognition_tolerance: float = 0.45
    detection_model: DetectionModel = "hog"
    encoding_model: EncodingModel = "small"
    number_of_times_to_upsample: int = 1
    number_of_jitters: int = 1
    recognition_frame_scale: float = 0.5
    data_dir: Path = Path("data")
    max_upload_bytes: int = 5 * 1024 * 1024
    timezone: str = "Asia/Ho_Chi_Minh"
    log_level: str = "INFO"
    storage_backend: StorageBackend = "csv"
    supabase_url: str | None = None
    supabase_secret_key: str | None = None
    anti_spoofing_enabled: bool = True
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
    )

    def __post_init__(self) -> None:
        if not 0.0 < self.recognition_tolerance <= 1.0:
            raise ValueError("recognition_tolerance must be greater than 0 and at most 1")
        if self.detection_model not in {"hog", "cnn"}:
            raise ValueError("detection_model must be 'hog' or 'cnn'")
        if self.encoding_model not in {"small", "large"}:
            raise ValueError("encoding_model must be 'small' or 'large'")
        if self.number_of_times_to_upsample < 0:
            raise ValueError("number_of_times_to_upsample cannot be negative")
        if self.number_of_jitters < 1:
            raise ValueError("number_of_jitters must be at least 1")
        if not 0.0 < self.recognition_frame_scale <= 1.0:
            raise ValueError("recognition_frame_scale must be greater than 0 and at most 1")
        if self.max_upload_bytes < 1:
            raise ValueError("max_upload_bytes must be at least 1")
        if not self.timezone.strip():
            raise ValueError("timezone cannot be empty")
        if self.log_level.upper() not in LOG_LEVELS:
            raise ValueError(
                "log_level must be CRITICAL, ERROR, WARNING, INFO, or DEBUG"
            )
        if self.storage_backend not in {"csv", "supabase"}:
            raise ValueError("storage_backend must be 'csv' or 'supabase'")
        if self.storage_backend == "supabase":
            if not self.supabase_url or not self.supabase_url.startswith("https://"):
                raise ValueError("SUPABASE_URL must be an https URL when using Supabase")
            if not self.supabase_secret_key:
                raise ValueError(
                    "SUPABASE_SECRET_KEY is required when STORAGE_BACKEND=supabase"
                )

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from environment variables and validate them."""

        defaults = cls()
        storage_backend = os.getenv("STORAGE_BACKEND", defaults.storage_backend).lower()
        if storage_backend not in {"csv", "supabase"}:
            raise ValueError("STORAGE_BACKEND must be 'csv' or 'supabase'")
        detection_model = os.getenv("FACE_DETECTION_MODEL", defaults.detection_model)
        encoding_model = os.getenv("FACE_ENCODING_MODEL", defaults.encoding_model)

        if detection_model not in {"hog", "cnn"}:
            raise ValueError("FACE_DETECTION_MODEL must be 'hog' or 'cnn'")
        if encoding_model not in {"small", "large"}:
            raise ValueError("FACE_ENCODING_MODEL must be 'small' or 'large'")

        return cls(
            recognition_tolerance=_env_float(
                "FACE_RECOGNITION_TOLERANCE", defaults.recognition_tolerance
            ),
            detection_model=cast(DetectionModel, detection_model),
            encoding_model=cast(EncodingModel, encoding_model),
            number_of_times_to_upsample=_env_int(
                "FACE_DETECTION_UPSAMPLE", defaults.number_of_times_to_upsample
            ),
            number_of_jitters=_env_int(
                "FACE_ENCODING_JITTERS", defaults.number_of_jitters
            ),
            recognition_frame_scale=_env_float(
                "FACE_RECOGNITION_FRAME_SCALE", defaults.recognition_frame_scale
            ),
            data_dir=Path(os.getenv("FACE_DATA_DIR", str(defaults.data_dir))),
            max_upload_bytes=_env_int(
                "FACE_MAX_UPLOAD_BYTES", defaults.max_upload_bytes
            ),
            timezone=os.getenv("FACE_TIMEZONE", defaults.timezone),
            log_level=os.getenv("FACE_LOG_LEVEL", defaults.log_level).upper(),
            storage_backend=cast(StorageBackend, storage_backend),
            supabase_url=os.getenv("SUPABASE_URL") or None,
            supabase_secret_key=os.getenv("SUPABASE_SECRET_KEY") or None,
            anti_spoofing_enabled=_env_bool(
                "FACE_ANTI_SPOOFING_ENABLED", defaults.anti_spoofing_enabled
            ),
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv(
                    "FACE_CORS_ORIGINS", ",".join(defaults.cors_origins)
                ).split(",")
                if origin.strip()
            ),
        )


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number") from error


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean (true/false)")
