"""Private, deterministic evidence images in Supabase Storage."""

from __future__ import annotations

import json
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import cv2

from backend.repositories.supabase_rest import SupabaseRequestError
from backend.services.image_loader import load_rgb_image

BUCKET = "attendance-photos"


class AttendancePhotoStore:
    def __init__(self, url: str, secret_key: str):
        self._base_url = url.rstrip("/") + "/storage/v1"
        self._headers = {"apikey": secret_key, "Authorization": f"Bearer {secret_key}"}

    def _request(self, method: str, path: str, body: bytes | None = None,
                 content_type: str = "application/json") -> bytes:
        request = Request(self._base_url + path, data=body, method=method,
                          headers={**self._headers, "Content-Type": content_type})
        try:
            with urlopen(request, timeout=20) as response:
                return response.read()
        except HTTPError as error:
            try:
                details = json.loads(error.read())
            except (ValueError, UnicodeDecodeError):
                details = {}
            status = int(details.get("statusCode", error.code))
            raise SupabaseRequestError("Attendance photo storage request failed",
                                       status=status) from error
        except (URLError, TimeoutError) as error:
            raise SupabaseRequestError("Could not reach attendance photo storage") from error

    def ensure_bucket(self) -> None:
        try:
            details = json.loads(self._request("GET", f"/bucket/{BUCKET}"))
        except SupabaseRequestError as error:
            if error.status != 404:
                raise
            self._request("POST", "/bucket", json.dumps({
                "id": BUCKET, "name": BUCKET, "public": False,
                "file_size_limit": 5242880, "allowed_mime_types": ["image/jpeg"],
            }).encode())
            return
        if details.get("public"):
            raise RuntimeError("Attendance photo bucket must be private")

    @staticmethod
    def object_path(employee_id: str, day: date, action: str) -> str:
        return f"{day.isoformat()}/{quote(employee_id, safe='')}/{action}.jpg"

    def save(self, employee_id: str, day: date, action: str, image: bytes) -> None:
        rgb = load_rgb_image(image)
        success, encoded = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if not success:
            raise ValueError("Could not encode attendance photo")
        path = self.object_path(employee_id, day, action)
        try:
            # No upsert: repeated frames never replace the first evidence image.
            self._request("POST", f"/object/{BUCKET}/{path}", encoded.tobytes(), "image/jpeg")
        except SupabaseRequestError as error:
            if error.status != 409:
                raise
