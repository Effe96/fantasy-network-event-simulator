import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import RiotPhenomenon


def _town(num_hostile_civilians, num_guards=1, num_nobles=1, hostility=-0.9, guard_loyalty=0.5):
    """civilians (ids 1..N) each hostile toward guard #100 (a `neighbor` edge);
    guards get ids 100..; nobles get ids 200.. -- none connected to civilians
    directly, since RiotPhenomenon treats all living authority members as
    town-wide defenders regardless of adjacency."""
    graph = SocialGraph()
    for i in range(1, num_hostile_civilians + 1):
        graph.add_node(Node(resident_id=i, ses="poor", alive=True, loyalty=0.0))
    for g in range(num_guards):
        guard_id = 100 + g
        graph.add_node(Node(resident_id=guard_id, ses="middling", alive=True, occupation="guard", loyalty=guard_loyalty))
    for n in range(num_nobles):
        noble_id = 200 + n
        graph.add_node(Node(resident_id=noble_id, ses="rich", alive=True, is_noble=True))

    guard_target = 100 if num_guards > 0 else None
    if guard_target is not None:
        for i in range(1, num_hostile_civilians + 1):
            graph.add_edge(
                Edge(i, guard_target, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
                     valence_a_to_b=hostility, valence_b_to_a=0.0)
            )
    return graph


def _run_days(phenomenon, graph, days, seed=0):
    if not phenomenon._adjacency:
        phenomenon.init_state(graph)  # populates self._adjacency as a side effect
    rng = random.Random(seed)
    events = []
    for day in range(1, days + 1):
        events.extend(phenomenon.end_of_day(graph, None, day, rng))
    return events


def test_no_riot_below_unrest_threshold():
    graph = _town(num_hostile_civilians=5, hostility=-0.1)
    phenomenon = RiotPhenomenon(unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0)
    events = _run_days(phenomenon, graph, days=5)
    assert events == []
    assert phenomenon._riots == 0


def test_no_riot_when_too_few_join():
    # only 2 hostile civilians -- even if both join, that's below min_participants
    graph = _town(num_hostile_civilians=2)
    phenomenon = RiotPhenomenon(unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3)
    events = _run_days(phenomenon, graph, days=5)
    assert events == []
    assert phenomenon._riots == 0


def test_riot_starts_with_enough_hostile_joiners():
    graph = _town(num_hostile_civilians=5)
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3, guard_lethality=0.0
    )
    events = _run_days(phenomenon, graph, days=1)
    assert phenomenon._riots == 1
    assert any(event.kind == "riot" for event in events)


def test_guards_shield_nobles_until_they_retreat():
    # guard_lethality=0 -> no guard ever dies -> guards never retreat -> nobles untouched
    graph = _town(num_hostile_civilians=5, num_guards=2, num_nobles=1)
    graph.add_edge(Edge(1, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3,
        guard_lethality=0.0, noble_lethality=1000.0, death_cap=1.0,
    )
    _run_days(phenomenon, graph, days=20)
    assert phenomenon._guard_deaths == 0
    assert phenomenon._noble_deaths == 0  # shielded: guards never broke
    assert graph.nodes[200].alive is True


def test_nobles_are_exposed_once_guards_retreat():
    graph = _town(num_hostile_civilians=5, num_guards=2, num_nobles=1)
    graph.add_edge(Edge(1, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3,
        guard_lethality=1000.0, retreat_threshold=0.3, noble_lethality=1000.0, death_cap=1.0,
        riot_bar_per_participant=10.0,  # generous bar so it doesn't cap out mid-test
    )
    # day 1: riot starts; day 2: guards take casualties and (with default 0.5
    # loyalty) retreat once 1 of 2 has died; day 3: the noble is exposed
    events = _run_days(phenomenon, graph, days=3)
    assert phenomenon._guard_deaths >= 1
    assert any(event.kind == "guards_retreat" for event in events)
    assert phenomenon._noble_deaths == 1  # the only noble, guaranteed lethality, guards broke


def test_higher_loyalty_guards_get_a_higher_retreat_threshold():
    # guards and rioters now trade blows simultaneously each day (independent
    # per-individual rolls), so the exact casualty count before a threshold
    # trips is no longer deterministic from the outside -- check the
    # threshold formula itself instead, which is what "scales with loyalty"
    # actually means
    disloyal = _town(num_hostile_civilians=5, num_guards=10, num_nobles=1, guard_loyalty=0.0)
    loyal = _town(num_hostile_civilians=5, num_guards=10, num_nobles=1, guard_loyalty=1.0)

    def make_phenomenon():
        return RiotPhenomenon(unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3)

    disloyal_phenomenon = make_phenomenon()
    _run_days(disloyal_phenomenon, disloyal, days=1)
    loyal_phenomenon = make_phenomenon()
    _run_days(loyal_phenomenon, loyal, days=1)

    # disloyal: 0.3*(0.5+0.0) = 0.15   loyal: 0.3*(0.5+1.0) = 0.45
    assert abs(disloyal_phenomenon._active_riot["guard_retreat_threshold"] - 0.15) < 1e-9
    assert abs(loyal_phenomenon._active_riot["guard_retreat_threshold"] - 0.45) < 1e-9


def _aggregate_combat_deaths(num_guards, num_civilians, trials=30):
    total_guard_deaths = total_rioter_deaths = 0
    for seed in range(trials):
        graph = _town(num_hostile_civilians=num_civilians, num_guards=num_guards, num_nobles=0)
        phenomenon = RiotPhenomenon(unrest_threshold=0.05, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3)
        _run_days(phenomenon, graph, days=2, seed=seed)  # day 1 starts the riot, day 2 is the first combat round
        total_guard_deaths += phenomenon._guard_deaths
        total_rioter_deaths += phenomenon._rioter_deaths
    return total_guard_deaths, total_rioter_deaths


def test_guards_die_less_often_than_rioters_regardless_of_mob_size():
    # the lethality constants alone should decide who's more likely to die,
    # not how the mob's size happens to compare to the (small, fixed) guard
    # corps -- confirmed on a real 30-seed aggregate this was NOT true of an
    # earlier linear-ratio formula (649 guard deaths vs 539 rioter deaths,
    # guards dying *more*, since the mob is drawn from the whole town but
    # the guard corps is small and fixed) -- see docs/decisions.md's
    # 2026-09-21 entry
    matched_g, matched_r = _aggregate_combat_deaths(num_guards=10, num_civilians=10)
    lopsided_g, lopsided_r = _aggregate_combat_deaths(num_guards=10, num_civilians=80)

    assert matched_r > matched_g
    assert lopsided_r > lopsided_g

    # the guard:rioter casualty *ratio* should be roughly the same in both
    # scenarios (close to guard_lethality/rioter_lethality) -- it's the
    # ratio staying stable across very different mob sizes that the old
    # formula got wrong, not just "rioters die more" in any one scenario
    matched_ratio = matched_g / matched_r
    lopsided_ratio = lopsided_g / lopsided_r
    assert abs(matched_ratio - lopsided_ratio) < 0.15


def test_rioters_can_die_fighting_guards():
    graph = _town(num_hostile_civilians=5, num_guards=2)
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3,
        guard_lethality=0.0, rioter_lethality=1000.0, death_cap=1.0, rioter_retreat_threshold=1000.0,
    )
    # guard_lethality=0 -> guards never retreat on their own; rioter_retreat_threshold
    # effectively unreachable, so the mob fights to the last person instead of routing
    _run_days(phenomenon, graph, days=3)
    assert phenomenon._rioter_deaths == 5
    assert phenomenon._guard_deaths == 0


def test_rioters_rout_before_guards_ever_break():
    # guard_lethality=0 -> guards invincible, never retreat on their own;
    # rioter_lethality=1000/death_cap=1.0 -> every rioter dies in the first
    # simultaneous exchange, which both wipes out the mob AND crosses its
    # rout threshold in the same day -- guards still never took a scratch
    graph = _town(num_hostile_civilians=10, num_guards=50, hostility=-0.9)
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3,
        guard_lethality=0.0, rioter_lethality=1000.0, death_cap=1.0, rioter_retreat_threshold=0.3,
    )
    events = _run_days(phenomenon, graph, days=3)
    assert phenomenon._rioter_deaths == 10
    assert any(event.kind == "rioters_rout" for event in events)
    assert phenomenon._guard_deaths == 0
    assert phenomenon._noble_deaths == 0  # guards never broke, nobles were never exposed
    assert phenomenon._active_riot is None


def test_angrier_mobs_get_a_higher_rout_threshold():
    # same reasoning as the guard-loyalty test: check the threshold formula
    # itself rather than emergent casualty timing under simultaneous combat
    calm = _town(num_hostile_civilians=10, num_guards=50, hostility=-0.1)
    furious = _town(num_hostile_civilians=10, num_guards=50, hostility=-0.9)

    def make_phenomenon():
        return RiotPhenomenon(unrest_threshold=0.05, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3)

    calm_phenomenon = make_phenomenon()
    _run_days(calm_phenomenon, calm, days=1)
    furious_phenomenon = make_phenomenon()
    _run_days(furious_phenomenon, furious, days=1)

    # calm: 0.3*(0.5+0.1) = 0.18   furious: 0.3*(0.5+0.9) = 0.42
    assert abs(calm_phenomenon._active_riot["rioter_retreat_threshold"] - 0.18) < 1e-9
    assert abs(furious_phenomenon._active_riot["rioter_retreat_threshold"] - 0.42) < 1e-9


def test_riot_bar_depletion_stops_the_riot():
    # exactly 3 hostile civilians (== min_participants), one per noble: once the
    # bar caps the riot at 2 kills, only 1 hostile civilian (tied to the
    # surviving noble) is left -- too few to start a second riot -- so this
    # isolates the bar's own stopping effect from a fresh riot re-triggering
    graph = _town(num_hostile_civilians=3, num_guards=0, num_nobles=3)
    for i in range(1, 4):
        graph.add_edge(
            Edge(i, 199 + i, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0)
        )
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3,
        noble_lethality=1000.0, death_cap=1.0, riot_bar_per_participant=0.7,  # bar = round(0.7*3) = 2
    )
    events = _run_days(phenomenon, graph, days=10)
    assert phenomenon._noble_deaths == 2  # exactly the bar, not all 3 living nobles
    assert any(event.kind == "riot_ends" for event in events)
    assert phenomenon._active_riot is None
    # further days must not kill any more nobles -- the mob already dispersed
    # and too few grievances remain to start a second riot
    _run_days(phenomenon, graph, days=10, seed=1)
    assert phenomenon._noble_deaths == 2


def test_nobles_are_exposed_immediately_when_no_guards_exist():
    graph = _town(num_hostile_civilians=5, num_guards=0, num_nobles=1)
    # civilians need an authority-adjacency edge to trigger the riot at all;
    # with no guards, wire the hostility straight to the noble instead
    graph.add_edge(Edge(1, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    graph.add_edge(Edge(2, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    graph.add_edge(Edge(3, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3,
        noble_lethality=1000.0, death_cap=1.0, riot_bar_per_participant=10.0,
    )
    events = _run_days(phenomenon, graph, days=2)
    assert phenomenon._noble_deaths == 1


def test_hatred_toward_sums_only_hostile_incoming_valence():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="poor", alive=True))
    graph.add_node(Node(resident_id=200, ses="rich", alive=True, is_noble=True))
    graph.add_edge(Edge(1, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, valence_a_to_b=-0.6, valence_b_to_a=0.9))
    graph.add_edge(Edge(2, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, valence_a_to_b=-0.3, valence_b_to_a=0.0))
    # only the negative valence *directed at* 200 counts; 200's own outgoing feelings don't
    assert abs(RiotPhenomenon._hatred_toward(graph, 200) - 0.9) < 1e-9


def test_a_guard_in_the_mob_is_not_also_defending_against_it():
    graph = _town(num_hostile_civilians=3, num_guards=2)
    riot = RiotPhenomenon()
    riot.init_state(graph)
    riot._begin_riot(graph, day=1, participants=[1, 2, 101], avg_participant_hostility=0.9)
    assert riot._active_riot["guards_remaining"] == [100]
    assert riot._active_riot["initial_guard_count"] == 1


def _run_all():
    test_no_riot_below_unrest_threshold()
    test_no_riot_when_too_few_join()
    test_riot_starts_with_enough_hostile_joiners()
    test_guards_shield_nobles_until_they_retreat()
    test_nobles_are_exposed_once_guards_retreat()
    test_higher_loyalty_guards_get_a_higher_retreat_threshold()
    test_guards_die_less_often_than_rioters_regardless_of_mob_size()
    test_rioters_can_die_fighting_guards()
    test_rioters_rout_before_guards_ever_break()
    test_angrier_mobs_get_a_higher_rout_threshold()
    test_riot_bar_depletion_stops_the_riot()
    test_nobles_are_exposed_immediately_when_no_guards_exist()
    test_hatred_toward_sums_only_hostile_incoming_valence()
    test_a_guard_in_the_mob_is_not_also_defending_against_it()
    print("OK")


if __name__ == "__main__":
    _run_all()
