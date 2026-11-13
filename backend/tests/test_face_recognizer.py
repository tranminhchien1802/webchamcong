import unittest
from unittest.mock import patch

import numpy as np

from backend.config import Settings
from backend.services.face_recognizer import FaceRecognizer, KnownFace


class FaceRecognizerTests(unittest.TestCase):
    @patch("backend.services.face_recognizer.face_recognition.face_distance")
    @patch("backend.services.face_recognizer.face_recognition.face_encodings")
    @patch("backend.services.face_recognizer.face_recognition.face_locations")
    def test_ambiguous_identity_is_not_matched(self, locations, encodings, distances):
        locations.return_value = [(10, 80, 90, 20)]
        encodings.return_value = [np.full(128, 0.1)]
        distances.return_value = np.array([0.30, 0.32])
        result = self.recognizer.recognize(self.image, self.known_faces)[0]
        self.assertFalse(result.matched)

    def setUp(self) -> None:
        self.image = np.zeros((100, 200, 3), dtype=np.uint8)
        self.recognizer = FaceRecognizer(
            Settings(recognition_tolerance=0.55, recognition_frame_scale=1.0)
        )
        self.known_faces = [
            KnownFace("emp_001", "Alice", np.zeros(128, dtype=np.float64)),
            KnownFace("emp_002", "Bob", np.ones(128, dtype=np.float64)),
        ]

    @patch("backend.services.face_recognizer.face_recognition.face_distance")
    @patch("backend.services.face_recognizer.face_recognition.face_encodings")
    @patch("backend.services.face_recognizer.face_recognition.face_locations")
    def test_nearest_face_inside_tolerance_is_matched(
        self, face_locations, face_encodings, face_distance
    ) -> None:
        face_locations.return_value = [(10, 80, 90, 20)]
        face_encodings.return_value = [np.full(128, 0.1)]
        face_distance.return_value = np.array([0.3, 0.8])

        results = self.recognizer.recognize(self.image, self.known_faces)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].matched)
        self.assertEqual(results[0].employee_id, "emp_001")
        self.assertEqual(results[0].name, "Alice")
        self.assertEqual(results[0].distance, 0.3)

    @patch("backend.services.face_recognizer.face_recognition.face_distance")
    @patch("backend.services.face_recognizer.face_recognition.face_encodings")
    @patch("backend.services.face_recognizer.face_recognition.face_locations")
    def test_nearest_face_outside_tolerance_is_unknown(
        self, face_locations, face_encodings, face_distance
    ) -> None:
        face_locations.return_value = [(10, 80, 90, 20)]
        face_encodings.return_value = [np.full(128, 0.5)]
        face_distance.return_value = np.array([0.6, 0.7])

        result = self.recognizer.recognize(self.image, self.known_faces)[0]

        self.assertFalse(result.matched)
        self.assertEqual(result.name, "Unknown")
        self.assertEqual(result.distance, 0.6)

    @patch("backend.services.face_recognizer.face_recognition.face_encodings")
    @patch("backend.services.face_recognizer.face_recognition.face_locations")
    def test_detected_face_is_unknown_when_no_employees_are_enrolled(
        self, face_locations, face_encodings
    ) -> None:
        face_locations.return_value = [(10, 80, 90, 20)]
        face_encodings.return_value = [np.full(128, 0.5)]

        result = self.recognizer.recognize(self.image, [])[0]

        self.assertFalse(result.matched)
        self.assertIsNone(result.distance)


if __name__ == "__main__":
    unittest.main()
