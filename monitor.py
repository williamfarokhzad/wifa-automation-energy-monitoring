"""Summarize fixed UTC blocks of imported electricity from interval energy."""
import argparse
import csv
import re
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z")
ENERGY = re.compile(r"[0-9]{1,7}(?:\.[0-9]{1,6})?")
HEADER = ["interval_start_utc", "import_kwh"]
BLOCK = timedelta(minutes=15)
MAX_SPAN = timedelta(days=31)


def parse_stamp(value):
    if not isinstance(value, str) or not STAMP.fullmatch(value):
        raise ValueError(f"expected UTC YYYY-MM-DDTHH:MMZ, got {value!r}")
    return datetime.strptime(value, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)


def summarize(stream, start, end, minutes=5):
    if minutes not in (1, 3, 5, 15):
        raise ValueError("sample minutes must be 1, 3, 5 or 15")
    start, end = parse_stamp(start), parse_stamp(end)
    if start.minute % 15 or end.minute % 15 or not timedelta() < end - start <= MAX_SPAN:
        raise ValueError("start/end must align to UTC quarters and span more than 0 to at most 31 days")
    step = timedelta(minutes=minutes)
    reader = csv.reader(stream, strict=True)
    if next(reader, None) != HEADER:
        raise ValueError("expected CSV header: " + ",".join(HEADER))
    values = {}
    for row in reader:
        if len(row) != 2:
            raise ValueError(f"line {reader.line_num}: expected two fields")
        try:
            stamp = parse_stamp(row[0])
            if not start <= stamp < end or (stamp - start) % step:
                raise ValueError("timestamp outside range or off the declared sample grid")
            if stamp in values:
                raise ValueError("duplicate interval start")
            if not ENERGY.fullmatch(row[1]):
                raise ValueError("expected nonnegative kWh with up to 7 integer and 6 decimal digits")
            values[stamp] = Decimal(row[1])
        except ValueError as exc:
            raise ValueError(f"line {reader.line_num}: {exc}") from exc
    expected = (end - start) // step
    totals = []
    for i in range((end - start) // BLOCK):
        block_start = start + i * BLOCK
        parts = [values.get(block_start + j * step) for j in range(BLOCK // step)]
        known = [item for item in parts if item is not None]
        totals.append((block_start, len(known), sum(known, Decimal(0))))
    complete = [(stamp, subtotal * 4) for stamp, n, subtotal in totals if n == BLOCK // step]
    peak = max((kw for _, kw in complete), default=None)
    return {
        "received": len(values),
        "expected": expected,
        "observed_kwh": sum(values.values(), Decimal(0)),
        "period_complete": len(values) == expected,
        "blocks": totals,
        "samples_per_block": BLOCK // step,
        "peak_kw": peak,
        "peak_starts": [stamp for stamp, kw in complete if kw == peak],
    }


def utc(stamp):
    return stamp.strftime("%Y-%m-%dT%H:%MZ")


def report(summary):
    lines = [
        f"Coverage: {summary['received']}/{summary['expected']} intervals",
        f"Observed energy: {summary['observed_kwh']:.6f} kWh"
        + ("" if summary["period_complete"] else " (partial; gaps not estimated)"),
    ]
    for stamp, known, subtotal in summary["blocks"]:
        needed = summary["samples_per_block"]
        reading = f"{subtotal * 4:.6f} kW" if known == needed else "withheld"
        lines.append(f"{utc(stamp)}: {known}/{needed} samples; average demand {reading}")
    peak = summary["peak_kw"]
    if peak is None:
        lines.append("Peak: unavailable (no complete block)")
    else:
        starts = ", ".join(map(utc, summary["peak_starts"]))
        label = "Peak" if summary["period_complete"] else "Peak among complete blocks only"
        lines.append(f"{label}: {peak:.6f} kW at {starts}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--start", required=True, help="inclusive UTC interval start")
    parser.add_argument("--end", required=True, help="exclusive UTC range end")
    parser.add_argument("--sample-minutes", type=int, choices=(1, 3, 5, 15), default=5)
    args = parser.parse_args(argv)
    try:
        with args.csv_file.open(newline="", encoding="utf-8") as stream:
            result = summarize(stream, args.start, args.end, args.sample_minutes)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    print(report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
