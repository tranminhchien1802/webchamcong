import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

from backend.repositories.attendance_csv import AttendanceCsvRepository
from backend.repositories.attendance_supabase import AttendanceSupabaseRepository


class CheckoutTests(unittest.TestCase):
    def test_csv_keeps_first_arrival_and_departure_on_repeated_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = AttendanceCsvRepository(Path(directory) / "attendance.csv")
            arrival = datetime(2026, 11, 13, 8, tzinfo=timezone.utc)
            departure = arrival.replace(hour=17)
            self.assertTrue(repository.mark_arrived("emp_001", arrival, 0.2))
            self.assertFalse(repository.mark_arrived("emp_001", arrival.replace(hour=9), 0.2))
            self.assertTrue(repository.mark_departed("emp_001", departure, 0.2))
            self.assertFalse(repository.mark_departed("emp_001", departure.replace(hour=18), 0.2))
            reloaded = AttendanceCsvRepository(Path(directory) / "attendance.csv")
            row, = reloaded.list_for_date(arrival.date())
            self.assertEqual(row.arrived_at, arrival)
            self.assertEqual(row.departed_at, departure)

    def test_supabase_checkout_only_updates_empty_departure(self):
        client = Mock()
        client.request.return_value = [{"employee_id": "emp_001"}]
        repository = AttendanceSupabaseRepository(client)
        now = datetime(2026, 11, 13, 17, tzinfo=timezone.utc)
        self.assertTrue(repository.mark_departed("emp_001", now, 0.2))
        query = client.request.call_args.kwargs["query"]
        self.assertEqual(query["departed_at"], "is.null")
        self.assertEqual(query["attendance_date"], "eq.2026-11-13")
        self.assertEqual(query["arrived_at"], f"lte.{now.isoformat()}")
