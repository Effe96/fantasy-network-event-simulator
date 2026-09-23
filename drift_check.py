# drift_check.py
"""The "quiet town" check (docs/plans.md, pipeline step 1).

A town imported from TownShape has "existed" for decades, so with nothing
extraordinary happening it should already be at equilibrium: a quiet year
should end roughly where it started. This runs the standard phenomenon set
(demo.build_phenomena) for several years with epidemics switched off,
snapshots the town at the end of day 1 and at each year end, and flags any
stock that drifts more than a tolerance per year. Rates (deaths, riots) are
listed per year too: they should repeat, not trend.

    python drift_check.py --db ../TownShape/demo_riverport_town.db --years 3 --seeds 1 2
"""
import argparse
from typing import Dict, List

from demo import build_phenomena
from engine import run_simulation
from graph import import_snapshot

HATRED = 0.6  # the violence hatred floor
WARMTH = 0.5  # the romance love threshold

# stocks measured as averages on a 0..1 scale are judged on absolute drift,
# the rest on relative drift
# (tie counts fall ~2x as fast as population, since both ends must be
# alive, so feelings are judged as shares of living ties, not raw counts)
ABSOLUTE_METRICS = {"mean feeling (all ties)", f"share of ties past hatred {HATRED}",
                    f"share of warm ties (>= {WARMTH})", "mean religiousness"}


def snapshot(graph, states) -> Dict[str, float]:
    nodes = graph.nodes
    alive = [n for n in nodes.values() if n.alive]
    civilians = [n for n in alive if n.role == "civilian"]
    feelings = []
    for edge in graph.edges.values():
        if nodes[edge.resident_a].alive and nodes[edge.resident_b].alive:
            feelings.append(edge.valence_a_to_b)
            feelings.append(edge.valence_b_to_a)
    violence, theft, romance = states["violence"], states["theft"], states["romance"]
    return {
        "population": len(alive),
        "guards alive": sum(1 for n in alive if n.role == "guard"),
        "nobles alive": sum(1 for n in alive if n.role == "noble"),
        "clergy alive": sum(1 for n in alive if n.role == "priest"),
        "mean feeling (all ties)": sum(feelings) / max(1, len(feelings)),
        f"share of ties past hatred {HATRED}": sum(1 for v in feelings if -v > HATRED) / max(1, len(feelings)),
        f"share of warm ties (>= {WARMTH})": sum(1 for v in feelings if v >= WARMTH) / max(1, len(feelings)),
        "mean religiousness": sum(n.religiousness for n in civilians) / max(1, len(civilians)),
        "thieves": sum(1 for rid, rs in theft.items() if rs["is_thief"] and nodes[rid].alive),
        "bodyguards employed": sum(1 for rid, vs in violence.items()
                                   if vs["hired_by"] is not None and nodes[rid].alive and nodes[vs["hired_by"]].alive),
        "married residents": sum(1 for rid, rs in romance.items() if rs["married"] and nodes[rid].alive),
    }


def drift_per_year(values: List[float], years: int, absolute: bool) -> float:
    """Average change per year from the first snapshot to the last: absolute
    units for 0..1 averages, percent of the starting value otherwise."""
    change = (values[-1] - values[0]) / years
    if absolute:
        return change
    return 100.0 * change / values[0] if values[0] else 0.0


def check_seed(db: str, seed: int, years: int):
    graph = import_snapshot(db, seed)
    phenomena = build_phenomena(graph, outbreak_chance=0.0)
    checkpoints = {1} | {365 * y for y in range(1, years + 1)}
    snaps: Dict[int, Dict[str, float]] = {}

    def on_day_end(day, g, states):
        if day in checkpoints:
            snaps[day] = snapshot(g, states)

    result = run_simulation(graph, phenomena, 365 * years, seed, on_day_end=on_day_end)
    rates = []
    for y in range(1, years + 1):
        lo, hi = 365 * (y - 1), 365 * y
        deaths = [d for d in graph.deaths if lo < d["day"] <= hi]
        by_cause: Dict[str, int] = {}
        for d in deaths:
            by_cause[d["cause"]] = by_cause.get(d["cause"], 0) + 1
        riots = result.daily_summaries[hi - 1]["riots"] - (result.daily_summaries[lo - 1]["riots"] if lo else 0)
        rates.append({"deaths": len(deaths), "riots": riots, **by_cause})
    return snaps, rates


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1])
    parser.add_argument("--tolerance-pct", type=float, default=2.0, help="flag stocks drifting more than this %% a year")
    parser.add_argument("--tolerance-abs", type=float, default=0.01, help="flag 0..1 averages drifting more than this a year")
    args = parser.parse_args(argv)

    for seed in args.seeds:
        snaps, rates = check_seed(args.db, seed, args.years)
        days = sorted(snaps)
        print(f"\n=== seed {seed}: {args.years} quiet years (no epidemic) ===")
        print(f"{'stock':34s}" + "".join(f"{'day ' + str(d):>10s}" for d in days)
              + f"{'drift/yr':>11s}{'after y1':>11s}  flag (after year 1, i.e. once settled in)")
        for metric in snaps[days[0]]:
            values = [snaps[d][metric] for d in days]
            absolute = metric in ABSOLUTE_METRICS
            drift = drift_per_year(values, args.years, absolute)
            # a jump in year 1 is the town settling from its imported state;
            # steady drift after that is what the equilibrium principle forbids
            settled = drift_per_year(values[1:], args.years - 1, absolute) if args.years > 1 else drift
            too_much = abs(settled) > (args.tolerance_abs if absolute else args.tolerance_pct)
            cells = "".join(f"{v:10.3f}" if absolute else f"{v:10.0f}" for v in values)
            fmt = (lambda d: f"{d:+.4f}") if absolute else (lambda d: f"{d:+.1f}%")
            print(f"{metric:34s}{cells}{fmt(drift):>11s}{fmt(settled):>11s}  {'DRIFTS' if too_much else 'ok'}")
        print("rates per year: " + " | ".join(
            f"y{i + 1}: " + ", ".join(f"{k} {v}" for k, v in sorted(r.items())) for i, r in enumerate(rates)))


if __name__ == "__main__":
    main()
