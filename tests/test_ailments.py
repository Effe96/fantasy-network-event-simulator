import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import CommonAilmentsPhenomenon


def _pair(ses_a="poor", ses_b="poor"):
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses=ses_a, alive=True))
    graph.add_node(Node(resident_id=2, ses=ses_b, alive=True))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, 0.0, 0.0))
    return graph


def test_flu_edge_probability_zero_when_both_healthy():
    graph = _pair()
    phenomenon = CommonAilmentsPhenomenon(flu_transmission_rate=1.0)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_flu_edge_probability_zero_when_both_sick():
    graph = _pair()
    phenomenon = CommonAilmentsPhenomenon(flu_transmission_rate=1.0)
    state = phenomenon.init_state(graph)
    state[1]["flu"]["status"] = "sick"
    state[2]["flu"]["status"] = "sick"
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_flu_edge_probability_positive_when_one_sick():
    graph = _pair()
    phenomenon = CommonAilmentsPhenomenon(flu_transmission_rate=0.5, flu_winter_multiplier=1.0)
    state = phenomenon.init_state(graph)
    state[1]["flu"]["status"] = "sick"
    edge = graph.get_edge(1, 2)
    probability = phenomenon.edge_probability(edge, state[1], state[2], day=1)
    assert abs(probability - 0.5 * edge.tie_strength) < 1e-9


def test_diarrhea_never_fires_through_edges_even_when_one_side_sick():
    graph = _pair()
    phenomenon = CommonAilmentsPhenomenon(flu_transmission_rate=0.0)
    state = phenomenon.init_state(graph)
    state[1]["diarrhea"]["status"] = "sick"
    edge = graph.get_edge(1, 2)
    # flu_transmission_rate=0.0 isolates the check to diarrhea's own (nonexistent) edge path
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_flu_transmission_is_not_infectious_until_the_next_day():
    graph = _pair()
    phenomenon = CommonAilmentsPhenomenon(flu_duration_days=5, flu_spontaneous_rate=0.0)
    state = phenomenon.init_state(graph)
    state[1]["flu"]["status"] = "sick"

    phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))
    assert state[2]["flu"]["status"] == "healthy"  # staged, not applied yet

    phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert state[2]["flu"]["status"] == "sick"
    assert state[2]["flu"]["days_left"] == 5  # a day-1 case starts day 2 with the full counter


def test_flu_recovers_into_temporary_immunity_then_becomes_healthy_again():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    phenomenon = CommonAilmentsPhenomenon(
        flu_duration_days=2, flu_immunity_days=2, flu_case_fatality_rate=0.0, flu_spontaneous_rate=0.0
    )
    state = phenomenon.init_state(graph)
    state[1]["flu"] = {"status": "sick", "days_left": 2}

    phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert state[1]["flu"]["status"] == "sick"
    phenomenon.end_of_day(graph, state, day=2, rng=random.Random(0))
    assert state[1]["flu"]["status"] == "immune"  # recovered, but not immediately re-catchable

    phenomenon.end_of_day(graph, state, day=3, rng=random.Random(0))
    assert state[1]["flu"]["status"] == "immune"
    phenomenon.end_of_day(graph, state, day=4, rng=random.Random(0))
    assert state[1]["flu"]["status"] == "healthy"  # immunity has worn off -- catchable again


def test_immune_residents_cannot_be_infected_through_edges():
    graph = _pair()
    phenomenon = CommonAilmentsPhenomenon(flu_transmission_rate=1.0)
    state = phenomenon.init_state(graph)
    state[1]["flu"]["status"] = "sick"
    state[2]["flu"] = {"status": "immune", "days_left": 10}
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_flu_can_kill_instead_of_recovering():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    phenomenon = CommonAilmentsPhenomenon(flu_duration_days=1, flu_case_fatality_rate=1.0, flu_spontaneous_rate=0.0)
    state = phenomenon.init_state(graph)
    state[1]["flu"] = {"status": "sick", "days_left": 1}

    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))

    assert graph.nodes[1].alive is False
    assert any(event.kind == "flu_died" for event in events)
    assert phenomenon.summarize(state)["flu_deaths"] == 1


def test_diarrhea_can_kill_instead_of_recovering():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    phenomenon = CommonAilmentsPhenomenon(diarrhea_duration_days=1, diarrhea_case_fatality_rate=1.0, flu_spontaneous_rate=0.0)
    state = phenomenon.init_state(graph)
    state[1]["diarrhea"] = {"status": "sick", "days_left": 1}

    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))

    assert graph.nodes[1].alive is False
    assert any(event.kind == "diarrhea_died" for event in events)
    assert phenomenon.summarize(state)["diarrhea_deaths"] == 1


def test_dead_residents_do_not_progress():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=False))
    phenomenon = CommonAilmentsPhenomenon(diarrhea_duration_days=1, diarrhea_case_fatality_rate=0.0, flu_spontaneous_rate=0.0)
    state = phenomenon.init_state(graph)
    state[1]["diarrhea"] = {"status": "sick", "days_left": 1}

    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))

    assert events == []
    assert state[1]["diarrhea"]["days_left"] == 1  # frozen, not decremented


def test_poorer_residents_get_diarrhea_more_readily():
    trials = 200
    rate = 0.2

    def hits(ses):
        count = 0
        for seed in range(trials):
            graph = SocialGraph()
            graph.add_node(Node(resident_id=1, ses=ses, alive=True))
            phenomenon = CommonAilmentsPhenomenon(diarrhea_spontaneous_rate=rate, flu_spontaneous_rate=0.0)
            state = phenomenon.init_state(graph)
            phenomenon.end_of_day(graph, state, day=1, rng=random.Random(seed))
            count += state[1]["diarrhea"]["status"] == "sick"
        return count

    assert hits("poor") > hits("rich")


def test_poorer_residents_more_likely_to_die_of_diarrhea():
    trials = 300

    def death_rate(ses):
        deaths = 0
        for seed in range(trials):
            graph = SocialGraph()
            graph.add_node(Node(resident_id=1, ses=ses, alive=True))
            phenomenon = CommonAilmentsPhenomenon(
                diarrhea_duration_days=1, diarrhea_case_fatality_rate=0.3, flu_spontaneous_rate=0.0
            )
            state = phenomenon.init_state(graph)
            state[1]["diarrhea"] = {"status": "sick", "days_left": 1}
            phenomenon.end_of_day(graph, state, day=1, rng=random.Random(seed))
            deaths += not graph.nodes[1].alive
        return deaths / trials

    assert death_rate("poor") > death_rate("rich")


def test_flu_transmission_is_higher_in_winter_quarters():
    graph = _pair()
    phenomenon = CommonAilmentsPhenomenon(flu_transmission_rate=0.1, flu_winter_multiplier=3.0)
    state = phenomenon.init_state(graph)
    state[1]["flu"]["status"] = "sick"
    edge = graph.get_edge(1, 2)

    summer_p = phenomenon.edge_probability(edge, state[1], state[2], day=180)  # late June
    winter_p = phenomenon.edge_probability(edge, state[1], state[2], day=1)  # Jan 1
    late_winter_p = phenomenon.edge_probability(edge, state[1], state[2], day=365)  # Dec 31

    assert abs(summer_p - 0.1 * edge.tie_strength) < 1e-9
    assert abs(winter_p - 0.3 * edge.tie_strength) < 1e-9
    assert abs(late_winter_p - 0.3 * edge.tie_strength) < 1e-9


def test_flu_season_factor_recurs_every_calendar_year_in_multi_year_runs():
    graph = _pair()
    phenomenon = CommonAilmentsPhenomenon()
    # day 366 is day-of-year 1 again (a second Jan 1st), not a continuation
    # of a single 366-day winter
    assert phenomenon._flu_season_factor(366) == phenomenon._flu_season_factor(1)
    assert phenomenon._flu_season_factor(180) != phenomenon._flu_season_factor(1)


def test_diarrhea_has_no_seasonality():
    trials = 200
    rate = 0.2

    def hits(day):
        count = 0
        for seed in range(trials):
            graph = SocialGraph()
            graph.add_node(Node(resident_id=1, ses="poor", alive=True))
            phenomenon = CommonAilmentsPhenomenon(diarrhea_spontaneous_rate=rate, flu_spontaneous_rate=0.0)
            state = phenomenon.init_state(graph)
            phenomenon.end_of_day(graph, state, day=day, rng=random.Random(seed))
            count += state[1]["diarrhea"]["status"] == "sick"
        return count

    winter_hits, summer_hits = hits(day=1), hits(day=180)
    assert abs(winter_hits - summer_hits) <= trials * 0.15  # same rate both seasons, allow for RNG noise


def test_summarize_reports_both_ailments_independently():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="poor", alive=True))
    phenomenon = CommonAilmentsPhenomenon()
    state = phenomenon.init_state(graph)
    state[1]["flu"]["status"] = "sick"
    state[2]["diarrhea"]["status"] = "sick"
    summary = phenomenon.summarize(state)
    assert summary["flu_sick"] == 1
    assert summary["diarrhea_sick"] == 1


def _run_all():
    test_flu_edge_probability_zero_when_both_healthy()
    test_flu_edge_probability_zero_when_both_sick()
    test_flu_edge_probability_positive_when_one_sick()
    test_diarrhea_never_fires_through_edges_even_when_one_side_sick()
    test_flu_transmission_is_not_infectious_until_the_next_day()
    test_flu_recovers_into_temporary_immunity_then_becomes_healthy_again()
    test_immune_residents_cannot_be_infected_through_edges()
    test_flu_can_kill_instead_of_recovering()
    test_diarrhea_can_kill_instead_of_recovering()
    test_dead_residents_do_not_progress()
    test_poorer_residents_get_diarrhea_more_readily()
    test_poorer_residents_more_likely_to_die_of_diarrhea()
    test_flu_transmission_is_higher_in_winter_quarters()
    test_flu_season_factor_recurs_every_calendar_year_in_multi_year_runs()
    test_diarrhea_has_no_seasonality()
    test_summarize_reports_both_ailments_independently()
    print("OK")


if __name__ == "__main__":
    _run_all()
