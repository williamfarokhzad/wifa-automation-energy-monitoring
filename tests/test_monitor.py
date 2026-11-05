import io
import subprocess
import sys
import unittest
from decimal import Decimal
from pathlib import Path

from monitor import report, summarize

ROOT = Path(__file__).resolve().parents[1]
START, END = "2026-01-15T08:00Z", "2026-01-15T08:30Z"
HEADER = "interval_start_utc,import_kwh\n"


def fixture(name):
    with (ROOT / "examples" / (name + ".csv")).open(newline="", encoding="utf-8") as stream:
        return summarize(stream, START, END)


def rows(*items, start=START, end=END, minutes=5):
    return summarize(io.StringIO(HEADER + "\n".join(items) + "\n" if items else HEADER), start, end, minutes)


class MeterTests(unittest.TestCase):
    def test_shift_preserves_energy_and_reduces_peak(self):
        overlap, stagger = fixture("overlap"), fixture("stagger")
        self.assertEqual(overlap["observed_kwh"], Decimal(9))
        self.assertEqual(stagger["observed_kwh"], Decimal(9))
        self.assertEqual(overlap["peak_kw"], Decimal(24))
        self.assertEqual(stagger["peak_kw"], Decimal(18))
        self.assertEqual(len(stagger["peak_starts"]), 2)

    def test_gap_does_not_become_zero_and_real_zero_counts(self):
        result = fixture("gap-and-zero")
        self.assertEqual(result["received"], 5)
        self.assertEqual(result["observed_kwh"], 6)
        self.assertEqual(result["peak_kw"], 8)
        self.assertIn("08:00Z: 2/3 samples; average demand withheld", report(result))
        self.assertIn("Peak among complete blocks only", report(result))

    def test_empty_log_keeps_explicit_trailing_gap(self):
        result = rows()
        self.assertEqual(result["expected"], 6)
        self.assertEqual(len(result["blocks"]), 2)
        self.assertIsNone(result["peak_kw"])

    def test_all_zero_is_complete(self):
        result = rows("2026-01-15T08:15Z,0", "2026-01-15T08:00Z,0", minutes=15)
        self.assertTrue(result["period_complete"])
        self.assertEqual(result["peak_kw"], 0)
        self.assertEqual(len(result["peak_starts"]), 2)

    def test_utc_day_boundary(self):
        result = rows("2026-01-15T23:45Z,1.234567", "2026-01-16T00:00Z,2",
                      start="2026-01-15T23:45Z", end="2026-01-16T00:15Z", minutes=15)
        self.assertEqual(result["observed_kwh"], Decimal("3.234567"))
        self.assertEqual(result["peak_kw"], Decimal(8))

    def test_rejects_duplicate_grid_mismatch_and_exclusive_end(self):
        for invalid in [
            ["2026-01-15T08:00Z,1"] * 2,
            ["2026-01-15T08:02Z,1"],
            ["2026-01-15T08:30Z,1"],
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                rows(*invalid)

    def test_rejects_invalid_or_ambiguous_readings(self):
        for value in ("-1", "NaN", "1e3", "", "1.2345678", " 2", "0,0"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                rows(f"2026-01-15T08:00Z,{value}")
        for stamp in ("2026-01-15T09:00+01:00", "2026-01-15T08:00", "2026-02-31T08:00Z"):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                rows(f"{stamp},1")

    def test_single_known_sample_cannot_report_a_peak(self):
        result = rows("2026-01-15T08:00Z,99")
        self.assertEqual(result["observed_kwh"], 99)
        self.assertIsNone(result["peak_kw"])

    def test_rejects_wrong_header_and_misaligned_range(self):
        with self.assertRaisesRegex(ValueError, "header"):
            summarize(io.StringIO("time,kw\n"), START, END)
        with self.assertRaisesRegex(ValueError, "align"):
            rows(end="2026-01-15T08:25Z")

    def test_cli_bad_file_returns_two_without_partial_report(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "monitor.py"), "does-not-exist.csv", "--start", START, "--end", END],
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("Input error", result.stderr)


if __name__ == "__main__":
    unittest.main()
