import io
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import cv2
import numpy as np

from backend.models.domain import Attendance
from backend.repositories.attendance_photos import AttendancePhotoStore
from backend.repositories.supabase_rest import SupabaseRequestError
from backend.services.attendance_service import AttendanceService


class AttendancePhotoTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 13, 17, tzinfo=timezone.utc)
        self.repository = Mock()
        self.repository.list_for_date.return_value = []
        self.photos = Mock()
        self.service = AttendanceService(self.repository, lambda: self.now, self.photos)

    def test_arrival_saves_photo_before_attendance(self):
        operations = Mock()
        operations.attach_mock(self.photos.save, "photo")
        operations.attach_mock(self.repository.mark_arrived, "record")
        self.service.mark_arrived("emp_001", 0.2, b"frame")
        self.assertEqual([call[0] for call in operations.mock_calls], ["photo", "record"])
        self.photos.save.assert_called_once_with("emp_001", self.now.date(), "in", b"frame")

    def test_photo_failure_does_not_record_arrival(self):
        self.photos.save.side_effect = SupabaseRequestError("unavailable")
        with self.assertRaises(SupabaseRequestError):
            self.service.mark_arrived("emp_001", 0.2, b"frame")
        self.repository.mark_arrived.assert_not_called()

    def test_duplicate_arrival_does_not_upload_again(self):
        self.repository.list_for_date.return_value = [Attendance(self.now.date(), "emp_001", True, self.now, 0.2)]
        self.assertFalse(self.service.mark_arrived("emp_001", 0.2, b"frame"))
        self.photos.save.assert_not_called()

    def test_checkout_saves_separate_photo(self):
        self.repository.list_for_date.return_value = [Attendance(self.now.date(), "emp_001", True, self.now.replace(hour=8), 0.2)]
        self.service.mark_departed("emp_001", 0.2, b"frame")
        self.photos.save.assert_called_once_with("emp_001", self.now.date(), "out", b"frame")

    def test_checkout_without_arrival_does_not_save_photo(self):
        with self.assertRaises(ValueError):
            self.service.mark_departed("emp_001", 0.2, b"frame")
        self.photos.save.assert_not_called()

    def test_storage_normalizes_images_to_jpeg_and_keeps_first_photo(self):
        store = AttendancePhotoStore("https://example.supabase.co", "test-secret")
        _, png = cv2.imencode(".png", np.zeros((10, 10, 3), dtype=np.uint8))
        with patch.object(store, "_request", side_effect=SupabaseRequestError("duplicate", status=409)) as request:
            store.save("emp_001", self.now.date(), "out", png.tobytes())
        args = request.call_args.args
        self.assertEqual(args[1], "/object/attendance-photos/2026-11-13/emp_001/out.jpg")
        self.assertTrue(args[2].startswith(b"\xff\xd8"))
        self.assertEqual(args[3], "image/jpeg")

    def test_bucket_is_created_private(self):
        store = AttendancePhotoStore("https://example.supabase.co", "test-secret")
        with patch.object(store, "_request", side_effect=[SupabaseRequestError("missing", status=404), b"{}"] ) as request:
            store.ensure_bucket()
        self.assertFalse(json.loads(request.call_args.args[2])["public"])

    def test_storage_reports_api_status_without_credentials(self):
        store = AttendancePhotoStore("https://example.supabase.co", "test-secret")
        error = HTTPError("https://example.supabase.co", 400, "Bad Request", {}, io.BytesIO(b'{"statusCode":"409"}'))
        with patch("backend.repositories.attendance_photos.urlopen", side_effect=error):
            with self.assertRaises(SupabaseRequestError) as caught:
                store._request("GET", "/bucket/attendance-photos")
        self.assertEqual(caught.exception.status, 409)
        self.assertNotIn("test-secret", str(caught.exception))
