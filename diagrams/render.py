"""Regenerate editable SVG charts from the supplied CSVs; no dependencies."""
from pathlib import Path
import sys
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from monitor import summarize

BASE, END = "2026-01-15T08:00Z", "2026-01-15T08:30Z"
INK, TEAL, AMBER, GRID = "#14324a", "#006d72", "#b04828", "#c9d9df"


def load(name):
    with (ROOT / "examples" / (name + ".csv")).open(newline="", encoding="utf-8") as stream:
        return summarize(stream, BASE, END)


def txt(x, y, label, size=25, color=INK, align="start", weight="normal"):
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="DejaVu Sans,sans-serif" font-size="{size}" text-anchor="{align}" font-weight="{weight}">{label}</text>'


def svg(name, body, height):
    text = f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}"><rect width="960" height="{height}" rx="20" fill="#f4f9fa"/>{"".join(body)}</svg>\n'
    (ROOT / "diagrams" / (name + ".svg")).write_text(text, encoding="utf-8")


def shift():
    cases = [("Overlap", AMBER, load("overlap")), ("Stagger", TEAL, load("stagger"))]
    body = [txt(48, 55, "Same energy, different peak demand", 37, weight="bold"),
            txt(48, 95, "Synthetic meter data · 15-minute average demand", 25),
            txt(52, 142, "kW", 24)]
    bottom, scale = 412, 10
    for kw in range(0, 25, 6):
        y = bottom - kw * scale
        body += [f'<path d="M115 {y} H880" stroke="{GRID}" stroke-width="2"/>', txt(90, y + 8, kw, 23, align="end")]
    for i in range(2):
        for j, (_, color, result) in enumerate(cases):
            kw = result["blocks"][i][2] * 4
            x, h = 210 + 373 * i + 112 * j, int(kw) * scale
            body += [f'<rect x="{x}" y="{bottom-h}" width="85" height="{h}" fill="{color}"/>',
                     txt(x + 42, bottom - h - 10, f"{kw:g}", 24, color, "middle", "bold")]
        t = cases[0][2]["blocks"][i][0]
        body.append(txt(309 + 373 * i, 450, f'{t:%H:%M} to {t+timedelta(minutes=15):%H:%M} UTC', 22, align="middle"))
    for i, (label, color, result) in enumerate(cases):
        x = 125 + i * 430
        body += [f'<rect x="{x}" y="491" width="24" height="24" fill="{color}"/>',
                 txt(x + 38, 512, f'{label}: {result["observed_kwh"]:g} kWh total', 24)]
    svg("energy-peak-comparison", body, 550)


def gaps():
    import csv
    result = load("gap-and-zero")
    with (ROOT / "examples" / "gap-and-zero.csv").open(newline="", encoding="utf-8") as stream:
        readings = {row["interval_start_utc"][11:16]: row["import_kwh"] for row in csv.DictReader(stream)}
    body = [txt(48, 55, "A missing interval is not zero", 37, weight="bold"),
            txt(48, 95, "Each tile covers five minutes and starts at the shown UTC time.", 25)]
    for i, (start, n, amount) in enumerate(result["blocks"]):
        left = 46 + 444 * i
        body += [txt(left, 153, f"Block {start:%H:%M} UTC", 26, weight="bold"),
                 f'<path d="M{left} 169 H{left+416}" stroke="{GRID}" stroke-width="3"/>']
        for j in range(3):
            t = (start + timedelta(minutes=5*j)).strftime("%H:%M")
            value = readings.get(t)
            x = left + j * 139
            fill = "#f4ded5" if value is None else "#d8eeee"
            body += [f'<rect x="{x}" y="192" width="129" height="94" rx="9" fill="{fill}"/>',
                     txt(x + 64, 226, t, 23, align="middle"),
                     txt(x + 64, 263, "Missing" if value is None else value+" kWh", 25, align="middle", weight="bold")]
        label = f"{n}/3 · demand withheld" if n != 3 else f"{n}/3 · {amount*4:g} kW"
        body += [txt(left, 338, label, 28, AMBER if n != 3 else TEAL, weight="bold")]
    body += [txt(48, 400, f'Observed: {result["observed_kwh"]:g} kWh (partial)', 25)]
    svg("energy-meter-gaps", body, 435)


if __name__ == "__main__":
    shift()
    gaps()
