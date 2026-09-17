# Fantasy Network Event Simulator

Standalone prototype exploring a generic "phenomenon propagation" engine
over a social graph imported (read-only) from a TownShape town snapshot.
Five phenomena so far: disease-like contagion, animosity-driven violence,
romance & marriage, guard/noble-targeted riots, and guard bribery. Not
part of the TownShape repo; never writes back to it.

See [`docs/2026-09-15-social-network-design.md`](docs/2026-09-15-social-network-design.md)
for the full design — every mechanic explained both technically (exact
formulas) and in plain language, with worked examples. This is a living
document: any new phenomenon or parameter gets a section there in the
same style before the work is considered done.

See [`docs/decisions.md`](docs/decisions.md) for *why* things are the way
they are — the constraint or feedback behind each design choice, and any
calibration numbers that turned out wrong and what fixed them. Check
there before re-litigating something that was already deliberately
chosen.

## Status

Implemented. `graph.py`, `phenomena.py`, `engine.py` and `demo.py` are all
in place, with assert-based tests in `tests/`.

## Usage

Run a simulation over a TownShape snapshot (the snapshot is opened
read-only and never modified):

```
py -3 demo.py --db <path-to-a-townshape-snapshot.db> --days 365 --seed 42
```

Writes `output/summary.csv` (per-day counts) and `output/events.json`
(the event log), and prints a short summary. `--out` picks a different
output directory. The same `(--db, --seed)` pair always produces the same
run.

Run the test suite (standard library only, no test framework):

```
py -3 tests/run_all.py
```
