import unittest
from datetime import date, datetime, timezone
from unittest.mock import Mock

from backend.models.domain import Attendance
from backend.services.attendance_service import AttendanceService


class AttendanceServiceTests(unittest.TestCase):
    def test_checkout_without_checkin_does_not_write(self):
        repository = Mock()
        repository.list_for_date.return_value = []
        service = AttendanceService(repository, lambda: datetime(2026, 11, 13, 17, tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            service.mark_departed("emp_001", 0.2)
        repository.mark_departed.assert_not_called()

    def test_checkout_uses_server_clock(self):
        repository = Mock()
        now = datetime(2026, 11, 13, 17, tzinfo=timezone.utc)
        repository.list_for_date.return_value = [Attendance(now.date(), "emp_001", True, now.replace(hour=8), 0.2)]
        service = AttendanceService(repository, lambda: now)
        service.mark_departed("emp_001", 0.25)
        repository.mark_departed.assert_called_once_with("emp_001", now, 0.25)

    def test_by_employee_for_date_excludes_rows_marked_not_arrived(self) -> None:
        attendance_date = date(2026, 10, 18)
        repository = Mock()
        repository.list_for_date.return_value = [
            Attendance(
                attendance_date=attendance_date,
                employee_id="emp_arrived",
                is_arrive=True,
                arrived_at=datetime(2026, 10, 18, 9, tzinfo=timezone.utc),
                last_distance=0.2,
            ),
            Attendance(
                attendance_date=attendance_date,
                employee_id="emp_cleared",
                is_arrive=False,
                arrived_at=datetime(2026, 10, 18, 9, tzinfo=timezone.utc),
                last_distance=0.3,
            ),
        ]
        service = AttendanceService(repository, Mock())

        result = service.by_employee_for_date(attendance_date)

        self.assertEqual(list(result), ["emp_arrived"])


if __name__ == "__main__":
    unittest.main()
