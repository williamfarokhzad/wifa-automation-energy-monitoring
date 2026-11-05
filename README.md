# Automation Energy Monitoring: Meter Interval Lab

Use exported interval energy to calculate total imported kWh and 15 minute average demand in kW. Compare two synthetic operating schedules, then see what a missing meter interval does to the result.

Full lesson: https://wifarobotics.com/learn/automation-energy-monitoring/

## Start from zero

1. Install [Python 3.12 or newer](https://www.python.org/downloads/). On Windows, use `py -3` instead of `python3`. No third party packages are needed.
2. Use **Code → Download ZIP** on GitHub, extract it, then open a terminal in the extracted folder containing `monitor.py`. If Git is installed, run `git clone https://github.com/williamfarokhzad/wifa-automation-energy-monitoring.git` and enter the cloned folder instead.
3. Check the interpreter with `python3 --version`. Run these commands from the project root:

```sh
python3 monitor.py examples/overlap.csv --start 2026-01-15T08:00Z --end 2026-01-15T08:30Z
python3 monitor.py examples/stagger.csv --start 2026-01-15T08:00Z --end 2026-01-15T08:30Z
python3 monitor.py examples/gap-and-zero.csv --start 2026-01-15T08:00Z --end 2026-01-15T08:30Z
python3 -m unittest discover -s tests -v
```

| Fixture | Coverage | Observed energy | Peak |
| :--- | :--- | :--- | :--- |
| overlap | 6/6 | 9 kWh | 24 kW at 08:00 UTC |
| stagger | 6/6 | 9 kWh | 18 kW at both 08:00 and 08:15 UTC |
| gap-and-zero | 5/6 | 6 kWh, partial | 8 kW at 08:15 UTC among complete blocks only |

## Input format

The CSV header is `interval_start_utc,import_kwh`. Each record carries energy accumulated over one complete interval, stamped at its beginning in UTC with a trailing `Z`. The start of the reporting period is inclusive; its end is exclusive. Set `--sample-minutes` to 1, 3, 5 (default) or 15. Both bounds must be on a UTC quarter hour. An explicit reporting range makes missing intervals at either end visible.

Use a nonnegative decimal with a dot, up to seven integer and six fractional digits. No repeated timestamps, blank readings or mixed durations. An absent row is unknown. A row containing 0 kWh is a known reading. The lab adds observed energy even from incomplete blocks but calculates average demand only for complete blocks.

If a valid file is rejected, check the header, timestamp grid and whether the exporter labels readings by interval end. Convert interval ends to starts before analyzing. A meter export in average kW needs a unit conversion first: multiply by the interval duration in hours to get kWh. A cumulative register is a different input type; never paste its totals into this CSV. Reconcile a real export with independent meter totals.

## Project files and diagrams

- `monitor.py`: input validation, coverage, energy and demand calculations.
- `examples/`: three deterministic synthetic exports.
- `tests/`: independently calculated expectations and input validation tests.
- `diagrams/`: editable SVGs and matching WebP versions. Run `python3 diagrams/render.py` to regenerate the SVGs from the examples. Export SVGs at native dimensions and encode them as lossless WebP if you update a chart. The peak comparison chart shows the overlap case at 24 and 12 kW and the staggered case at 18 kW in both blocks. The gap chart shows a missing 08:05 reading and a valid zero at 08:15.

The lab runs offline, has no meter or PLC interface, and does not model a tariff, rolling demand, reactive power, on site generation, regeneration or energy cost. Do not wire equipment, alter PLC behavior or use these example results as billing or savings evidence.

References: [BPA's guide to interval data and peak demand](https://www.bpa.gov/-/media/Aep/energy-efficiency/measurement-verification/11-bpa-mv-peak-demand-impacts-application-guide-v1.pdf) and [the DOE Energy Information Handbook](https://betterbuildingssolutioncenter.energy.gov/sites/default/files/attachments/energy-information-handbook.pdf).
