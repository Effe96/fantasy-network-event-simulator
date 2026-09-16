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
    # ponytail: base_rate is a per-edge daily probability (see design doc §8's worked
    # example, which implicitly assumes a person has a handful of ties). It was never
    # scaled by graph density, so on a real town where the average resident has ~63
    # ties the unscaled 0.01 default produces implausible mass-casualty outcomes
    # (609 of 832 dead in one year). Dividing by average degree keeps each *person's*
    # aggregate daily risk at the spec's per-tie scale, so the demo shows a believable,
    # occasional pattern of violence rather than a mass extinction event. The divisor
    # is the calibration knob: raise it for a quieter town, lower it for a bloodier one.
    average_degree = max(1.0, 2 * len(graph.edges) / max(1, len(graph.nodes)))
    violence = ViolencePhenomenon(base_rate=0.01 / average_degree)
    phenomena = [ContagionPhenomenon(), violence]
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
    print(f"Simulated {len(result.daily_summaries)} days.")
    if not result.daily_summaries:
        print("No days simulated.")
        return

    last = result.daily_summaries[-1]
    peak = max(result.daily_summaries, key=lambda row: row.get("infected", 0))

    print("contagion:")
    print(f"  peak simultaneous infected: {peak.get('infected', 0)} (day {peak['day']})")
    print(f"  final susceptible/infected/recovered: "
          f"{last.get('susceptible', 0)}/{last.get('infected', 0)}/{last.get('recovered', 0)}")
    print("violence:")
    print(f"  total deaths: {last.get('dead', 0)}")
    print(f"  final alive: {last.get('alive', 0)}")
    print(f"Total events logged: {len(result.events)}")


if __name__ == "__main__":
    main()
