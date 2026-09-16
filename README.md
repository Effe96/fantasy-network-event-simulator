# Fantasy Network Event Simulator

Standalone prototype exploring a generic "phenomenon propagation" engine
over a social graph imported (read-only) from a TownShape town snapshot.
Two example phenomena: disease-like contagion, and animosity-driven
violence. Not part of the TownShape repo; never writes back to it.

See [`docs/2026-09-15-social-network-design.md`](docs/2026-09-15-social-network-design.md)
for the full design, including the concepts behind how edges are scored
(Granovetter tie strength, Fiske relational types, valence) with
plain-language explanations and worked examples.

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
