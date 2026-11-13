import asyncio
import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import numpy as np

from backend.config import Settings
from backend.main import create_app
from backend.services.face_encoder import EncodedFace
from backend.services.face_recognizer import RecognitionResult


@dataclass
class ApiResponse:
    status_code: int
    body: bytes

    def json(self):
        return json.loads(self.body)


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        settings = Settings(
            data_dir=Path(self.temporary_directory.name),
            recognition_frame_scale=1.0,
        )
        self.app = create_app(settings)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _enroll_alice(self):
        encoded = EncodedFace(np.zeros(128), (10, 80, 90, 20))
        with patch.object(self.app.state.core.face_encoder, "encode", return_value=encoded):
            return self._request(
                "POST",
                "/api/employees",
                fields={"name": "  Alice   Nguyen "},
                image=("alice.jpg", b"fake-jpeg", "image/jpeg"),
            )

    def test_complete_enrollment_recognition_and_attendance_flow(self) -> None:
        enrollment = self._enroll_alice()
        self.assertEqual(enrollment.status_code, 201)
        self.assertEqual(
            enrollment.json(),
            {
                "employee_id": "emp_001",
                "name": "Alice Nguyen",
                "image_filename": "alice.jpg",
            },
        )

        employees = self._request("GET", "/api/employees")
        self.assertEqual(employees.status_code, 200)
        self.assertFalse(employees.json()[0]["is_arrive"])
        self.assertNotIn("face_encoding", employees.json()[0])

        recognized = RecognitionResult(
            employee_id="emp_001",
            name="Alice Nguyen",
            distance=0.41,
            location=(10, 80, 90, 20),
        )
        with patch.object(
            self.app.state.core.face_recognizer,
            "recognize",
            return_value=[recognized],
        ), patch.object(self.app.state.core.face_liveness_detector, "check"):
            recognition = self._request(
                "POST",
                "/api/recognize",
                image=("alice.jpg", b"fake-jpeg", "image/jpeg"),
            )

        self.assertEqual(recognition.status_code, 200)
        self.assertEqual(recognition.json()["attendance_updated"], ["emp_001"])
        self.assertEqual(
            recognition.json()["faces"][0]["location"],
            {"top": 10, "right": 80, "bottom": 90, "left": 20},
        )

        attendance = self._request("GET", "/api/attendance")
        self.assertEqual(attendance.status_code, 200)
        self.assertTrue(attendance.json()[0]["is_arrive"])
        self.assertIsNotNone(attendance.json()[0]["arrived_at"])

        with patch.object(self.app.state.core.face_recognizer, "recognize", return_value=[recognized]), patch.object(self.app.state.core.face_liveness_detector, "check"):
            checkout = self._request("POST", "/api/recognize", fields={"action": "out"}, image=("alice.jpg", b"fake-jpeg", "image/jpeg"))
        self.assertEqual(checkout.status_code, 200)
        self.assertEqual(checkout.json()["attendance_updated"], ["emp_001"])
        saved = self._request("GET", "/api/attendance").json()[0]
        self.assertGreaterEqual(saved["departed_at"], saved["arrived_at"])

    def test_spoof_does_not_record_attendance(self):
        from backend.services.face_liveness import SpoofDetectedError
        self._enroll_alice()
        with patch.object(self.app.state.core.face_liveness_detector, "check", side_effect=SpoofDetectedError("photo or screen replay")):
            response = self._request("POST", "/api/recognize", image=("alice.jpg", b"fake-jpeg", "image/jpeg"))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self._request("GET", "/api/attendance").json()[0]["is_arrive"])

    def test_multiple_faces_do_not_record_attendance(self):
        self._enroll_alice()
        match = RecognitionResult("emp_001", "Alice Nguyen", 0.2, (10, 80, 90, 20))
        with patch.object(self.app.state.core.face_liveness_detector, "check"), patch.object(self.app.state.core.face_recognizer, "recognize", return_value=[match, match]):
            response = self._request("POST", "/api/recognize", image=("alice.jpg", b"fake-jpeg", "image/jpeg"))
        self.assertEqual(response.status_code, 422)
        self.assertFalse(self._request("GET", "/api/attendance").json()[0]["is_arrive"])

    def test_duplicate_name_returns_conflict(self) -> None:
        self.assertEqual(self._enroll_alice().status_code, 201)
        response = self._enroll_alice()
        self.assertEqual(response.status_code, 409)

    def test_invalid_extension_returns_unsupported_media_type(self) -> None:
        response = self._request(
            "POST",
            "/api/employees",
            fields={"name": "Alice"},
            image=("alice.gif", b"image", "image/gif"),
        )
        self.assertEqual(response.status_code, 415)

    def _request(
        self,
        method: str,
        path: str,
        *,
        fields: dict[str, str] | None = None,
        image: tuple[str, bytes, str] | None = None,
    ) -> ApiResponse:
        headers: list[tuple[bytes, bytes]] = []
        body = b""
        if fields is not None or image is not None:
            boundary = "face-api-test-boundary"
            parts: list[bytes] = []
            for name, value in (fields or {}).items():
                parts.append(
                    (
                        f"--{boundary}\r\n"
                        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                        f"{value}\r\n"
                    ).encode()
                )
            if image is not None:
                filename, image_bytes, content_type = image
                parts.append(
                    (
                        f"--{boundary}\r\n"
                        'Content-Disposition: form-data; name="image"; '
                        f'filename="{filename}"\r\n'
                        f"Content-Type: {content_type}\r\n\r\n"
                    ).encode()
                    + image_bytes
                    + b"\r\n"
                )
            parts.append(f"--{boundary}--\r\n".encode())
            body = b"".join(parts)
            headers.append(
                ("content-type".encode(), f"multipart/form-data; boundary={boundary}".encode())
            )
            headers.append((b"content-length", str(len(body)).encode()))

        status_code = 0
        response_parts: list[bytes] = []
        request_sent = False

        async def receive():
            nonlocal request_sent
            if request_sent:
                return {"type": "http.disconnect"}
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                response_parts.append(message.get("body", b""))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": headers,
            "client": ("test", 1234),
            "server": ("testserver", 80),
            "root_path": "",
        }
        asyncio.run(self.app(scope, receive, send))
        return ApiResponse(status_code=status_code, body=b"".join(response_parts))


if __name__ == "__main__":
    unittest.main()
