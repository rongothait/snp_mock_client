import io
import unittest
from datetime import date

from clinic.security import AccessDenied
from clinic.services.reporting import REPORT_COLUMNS, age_band
from tests.fixtures import ANALYST, PHYSICIAN, make_clinic


class ReportingTest(unittest.TestCase):
    def setUp(self):
        self.clinic = make_clinic()
        self.conn = self.clinic.db.connection

    def test_age_band(self):
        today = date(2030, 6, 1)
        self.assertEqual(age_band(date(2000, 1, 1), today), "30-39")
        self.assertEqual(age_band(date(1930, 1, 1), today), "90+")

    def test_export_is_deidentified(self):
        self.conn.queue_result([("pid-1", date(2000, 1, 1), 3, ["Z00", "J06"])])
        out = io.StringIO()
        count = self.clinic.reporting.export_utilization_csv(ANALYST, out, today=date(2030, 6, 1))

        self.assertEqual(count, 1)
        header, row = out.getvalue().strip().splitlines()
        self.assertEqual(header.split(","), list(REPORT_COLUMNS))
        self.assertNotIn("pid-1", row)
        self.assertNotIn("2000", row)
        self.assertTrue(row.endswith(",30-39,3,J06;Z00"))

    def test_only_analysts_export(self):
        with self.assertRaises(AccessDenied):
            self.clinic.reporting.export_utilization_csv(PHYSICIAN, io.StringIO())


if __name__ == "__main__":
    unittest.main()
