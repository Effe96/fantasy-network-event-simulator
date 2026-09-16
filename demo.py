# demo.py
import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from graph import import_snapshot
from phenomena import ContagionPhenomenon, ViolencePhenomenon
from engine import run_simulation


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Run the social-sim demo over a TownShape snapshot.")
    parser.add_argument("--db", required=True, help="Path to a TownShape .db snapshot")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="output")
    args = parser.parse_args(argv)

    graph = import_snapshot(args.db, args.seed)
    phenomena = [ContagionPhenomenon(), ViolencePhenomenon()]
    result = run_simulation(graph, phenomena, args.days, args.seed)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_summary_csv(out_dir / "summary.csv", result.daily_summaries)
    _write_events_json(out_dir / "events.json", result.events)
    _print_summary(result)


def _write_summary_csv(path: Path, daily_summaries) -> None:
    if not daily_summaries:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(daily_summaries[0].keys()))
        writer.writeheader()
        writer.writerows(daily_summaries)


def _write_events_json(path: Path, events) -> None:
    with open(path, "w") as f:
        json.dump([asdict(event) for event in events], f, indent=2)


def _print_summary(result) -> None:
    last = result.daily_summaries[-1] if result.daily_summaries else {}
    print(f"Simulated {len(result.daily_summaries)} days.")
    print(f"Final state: {last}")
    print(f"Total events logged: {len(result.events)}")


if __name__ == "__main__":
    main()
