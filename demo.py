# demo.py
import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from graph import import_snapshot
from phenomena import (
    CommonAilmentsPhenomenon,
    ContagionPhenomenon,
    GuardPhenomenon,
    RiotPhenomenon,
    RomancePhenomenon,
    TheftPhenomenon,
    ViolencePhenomenon,
)
from engine import run_simulation


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Run the Fantasy Network Event Simulator over a TownShape snapshot.")
    parser.add_argument("--db", required=True, help="Path to a TownShape .db snapshot")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="output")
    parser.add_argument("--transmission-rate", type=float, default=0.5,
                         help="per-edge daily transmission hazard before tie strength/type scaling")
    parser.add_argument("--infectious-days", type=int, default=7,
                         help="days an infected resident stays infectious before recovering or dying")
    parser.add_argument("--fatality-rate", type=float, default=0.03,
                         help="chance an infected resident dies instead of recovering (SES-weighted)")
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
    # ponytail: linear scale-up, 3x at max aggression (1.0); tune this constant if a
    # max-aggression town should feel more/less volatile than "three times as violent"
    aggression_factor = 1.0 + 2.0 * graph.town_aggression
    # constructed before violence so it can be wired into it below (group
    # violence's riot-escalation path calls straight into this instance)
    riot = RiotPhenomenon(unrest_threshold=0.15 / aggression_factor, riot_base_rate=0.03 * aggression_factor)
    violence = ViolencePhenomenon(base_rate=0.01 / average_degree * aggression_factor, riot_phenomenon=riot)
    contagion = ContagionPhenomenon(
        base_rate=args.transmission_rate,
        infectious_days=args.infectious_days,
        case_fatality_rate=args.fatality_rate,
    )
    # unlike violence, no degree-normalization needed here: on a real town most
    # residents are already married at import (see romance's design note), so
    # the eligible unmarried-and-connected pool is small on its own
    romance = RomancePhenomenon()
    # riot's own thresholds (set above, alongside its construction): same
    # aggression_factor as violence, since an aggressive town riots more
    # readily and reaches unrest sooner (vision doc: "more frequent riots").
    # unrest_threshold=0.15 (not the earlier 0.25) is a deliberate margin below
    # the reference town's natural baseline civilian-to-authority hostility
    # (~0.25-0.26) -- at 0.25 the threshold sat almost exactly ON that
    # baseline, so the daily trigger odds were negligible and riots were
    # effectively unreachable in a normal year, not just rare. Verified in
    # isolation (fresh RNG stream, no other phenomena running): 20/30
    # independent year-long trials produced at least one riot at these values.
    guards = GuardPhenomenon()
    theft = TheftPhenomenon()
    ailments = CommonAilmentsPhenomenon()
    phenomena = [contagion, violence, romance, riot, guards, theft, ailments]
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
    disease_deaths = last.get("deceased", 0)
    riot_deaths = (
        last.get("riot_guard_deaths", 0) + last.get("riot_noble_deaths", 0) + last.get("riot_rioter_deaths", 0)
    )
    executed_deaths = last.get("thefts_executed", 0)
    ailment_deaths = last.get("flu_deaths", 0) + last.get("diarrhea_deaths", 0)
    violence_deaths = last.get("dead", 0) - disease_deaths - riot_deaths - executed_deaths - ailment_deaths

    print("contagion:")
    print(f"  peak simultaneous infected: {peak.get('infected', 0)} (day {peak['day']})")
    print(f"  final susceptible/infected/recovered/deceased: "
          f"{last.get('susceptible', 0)}/{last.get('infected', 0)}/{last.get('recovered', 0)}/{disease_deaths}")
    print("violence:")
    print(f"  deaths: {violence_deaths}  (of which group violence: {last.get('group_kills', 0)})")
    print("romance:")
    print(f"  married residents: {last.get('married_residents', 0)}  births: {last.get('births', 0)}")
    print("riots:")
    print(f"  riots: {last.get('riots', 0)}  guards killed: {last.get('riot_guard_deaths', 0)}"
          f"  rioters killed: {last.get('riot_rioter_deaths', 0)}"
          f"  nobles killed: {last.get('riot_noble_deaths', 0)}")
    print("guards:")
    print(f"  bribes: {last.get('bribes', 0)}")
    print("theft:")
    print(f"  thieves: {last.get('thieves', 0)}  thefts: {last.get('thefts', 0)}"
          f"  caught: {last.get('thefts_caught', 0)}  arrested: {last.get('thefts_arrested', 0)}"
          f"  executed: {executed_deaths}")
    print("common ailments:")
    print(f"  flu: {last.get('flu_sick', 0)} currently sick, {last.get('flu_cases', 0)} cases this year,"
          f" {last.get('flu_deaths', 0)} deaths")
    print(f"  diarrhea: {last.get('diarrhea_sick', 0)} currently sick, {last.get('diarrhea_cases', 0)} cases this year,"
          f" {last.get('diarrhea_deaths', 0)} deaths")
    print("population:")
    print(f"  alive: {last.get('alive', 0)}  dead: {last.get('dead', 0)} "
          f"(violence {violence_deaths} + disease {disease_deaths} + riots {riot_deaths}"
          f" + executed {executed_deaths} + ailments {ailment_deaths})")
    print(f"Total events logged: {len(result.events)}")


if __name__ == "__main__":
    main()
