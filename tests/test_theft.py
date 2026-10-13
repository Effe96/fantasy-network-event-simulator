import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import TheftPhenomenon


def _thief_victim_graph(thief_ses="poor", victim_ses="rich", cunning=0.8, victim_valence_from_victim=0.0):
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses=thief_ses, alive=True, cunning=cunning))
    graph.add_node(Node(resident_id=2, ses=victim_ses, alive=True, age=30))
    graph.add_edge(
        Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=0.0, valence_b_to_a=victim_valence_from_victim)
    )
    return graph


def test_no_theft_edge_when_neither_side_is_a_thief():
    graph = _thief_victim_graph()
    phenomenon = TheftPhenomenon(theft_base_rate=1.0)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_no_theft_edge_when_both_sides_are_thieves():
    graph = _thief_victim_graph()
    phenomenon = TheftPhenomenon(theft_base_rate=1.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True
    state[2]["is_thief"] = True
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_richer_victims_are_more_attractive_targets():
    phenomenon = TheftPhenomenon(theft_base_rate=0.1)

    graph_rich = _thief_victim_graph(victim_ses="rich")
    state_rich = phenomenon.init_state(graph_rich)
    state_rich[1]["is_thief"] = True
    p_rich = phenomenon.edge_probability(graph_rich.get_edge(1, 2), state_rich[1], state_rich[2], day=1)

    graph_poor = _thief_victim_graph(victim_ses="poor")
    state_poor = phenomenon.init_state(graph_poor)
    state_poor[1]["is_thief"] = True
    p_poor = phenomenon.edge_probability(graph_poor.get_edge(1, 2), state_poor[1], state_poor[2], day=1)

    assert p_rich > p_poor


def test_apply_effect_records_a_theft_event_regardless_of_discovery():
    graph = _thief_victim_graph()
    phenomenon = TheftPhenomenon(discovery_chance=0.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    assert any(event.kind == "theft" and event.resident_a == 1 and event.resident_b == 2 for event in events)
    assert phenomenon.summarize(state)["thefts"] == 1
    assert phenomenon.summarize(state)["thefts_caught"] == 0


def test_when_caught_the_victims_valence_toward_the_thief_drops():
    graph = _thief_victim_graph(victim_valence_from_victim=0.5)
    phenomenon = TheftPhenomenon(discovery_chance=1.0, caught_animosity=0.3)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    edge = graph.get_edge(1, 2)
    assert abs(edge.valence_from(2) - 0.2) < 1e-9
    assert any(event.kind == "caught" for event in events)
    assert phenomenon.summarize(state)["thefts_caught"] == 1


def test_a_caught_thief_loses_the_work_and_the_tie_but_not_family():
    graph = _thief_victim_graph()
    graph.get_edge(1, 2).source_type = "coworker"  # an outworker robbing the merchant they spin for
    graph.nodes[1].occupation, graph.employer = "outworker", {1: 2}
    phenomenon = TheftPhenomenon(discovery_chance=1.0, arrest_chance=0.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True
    phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))
    assert graph.nodes[1].occupation is None and 1 not in graph.employer
    assert graph.open_jobs == [{"was": 1, "occupation": "outworker", "workplace": None, "ses": "poor"}]  # for a newcomer
    assert (1, 2, 5, "theft") in graph._ties_to_retire
    sister = _thief_victim_graph()
    sister.get_edge(1, 2).source_type = "sibling"  # family stays family
    state = phenomenon.init_state(sister)
    state[1]["is_thief"] = True
    phenomenon.apply_effect(sister, state, 1, 2, day=5, rng=random.Random(0))
    assert not sister._ties_to_retire


def test_when_caught_a_nearby_guards_valence_toward_the_thief_also_drops():
    graph = _thief_victim_graph()
    graph.add_node(Node(resident_id=3, ses="middling", alive=True, occupation="guard"))
    graph.add_edge(
        Edge(1, 3, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=0.0, valence_b_to_a=0.4)
    )
    phenomenon = TheftPhenomenon(discovery_chance=1.0, caught_animosity=0.3)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    guard_edge = graph.get_edge(1, 3)
    assert abs(guard_edge.valence_from(3) - 0.1) < 1e-9
    assert any(event.kind == "guard_notified" for event in events)


def test_nobles_never_become_thieves():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True, is_noble=True))
    phenomenon = TheftPhenomenon(become_thief_rate=1.0)
    state = phenomenon.init_state(graph)

    phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))

    assert state[1]["is_thief"] is False


def test_arrested_thief_loses_thief_status_but_stays_alive():
    graph = _thief_victim_graph()
    graph.money, graph.belongings = {("p", 1): 100.0, ("p", 2): 100.0}, {}  # a first offender who can pay
    graph.add_node(Node(resident_id=3, ses="middling", alive=True, occupation="guard", loyalty=1.0))
    graph.add_edge(
        Edge(1, 3, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=0.0, valence_b_to_a=0.0)
    )
    phenomenon = TheftPhenomenon(discovery_chance=1.0, arrest_chance=1.0, execution_weight=0.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    assert state[1]["is_thief"] is False
    assert graph.nodes[1].alive is True
    assert any(event.kind == "arrested" for event in events)
    assert phenomenon.summarize(state)["thefts_arrested"] == 1
    # pays back what was taken, and twice that to the commune
    # (the thief ends 2x the theft down, which is what the commune gets)
    assert any(e.kind == "fined" for e in events) and abs(graph.money[("p", 2)] - 100.0) < 1e-9
    assert graph.money[("p", 1)] < 100.0 and abs(graph.money["commune"] - (100.0 - graph.money[("p", 1)])) < 1e-9


def test_thief_can_be_arrested_with_no_guard_neighbor_at_all():
    # the original version required a guard *neighbor* to arrest at all --
    # with a sparse guard corps that meant most catches could never lead to
    # a removal. Arrest is now town-wide: no guard node exists in this
    # graph at all, and the thief should still be arrestable.
    graph = _thief_victim_graph()
    phenomenon = TheftPhenomenon(discovery_chance=1.0, arrest_chance=1.0, execution_weight=0.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    assert state[1]["is_thief"] is False
    assert any(event.kind == "arrested" for event in events)
    assert not any(event.kind == "guard_notified" for event in events)


def test_low_loyalty_guards_execute_instead_of_arresting():
    graph = _thief_victim_graph()
    graph.add_node(Node(resident_id=3, ses="middling", alive=True, occupation="guard", loyalty=0.0))
    graph.add_edge(
        Edge(1, 3, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=0.0, valence_b_to_a=0.0)
    )
    phenomenon = TheftPhenomenon(discovery_chance=1.0, arrest_chance=1.0, execution_weight=1.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True
    state[1]["convictions"] = 2  # the gallows only from the third conviction

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    assert graph.nodes[1].alive is False
    assert any(event.kind == "executed" for event in events)
    assert phenomenon.summarize(state)["thefts_executed"] == 1


def test_a_first_conviction_never_hangs():
    graph = _thief_victim_graph()
    graph.add_node(Node(resident_id=3, ses="middling", alive=True, occupation="guard", loyalty=0.0))
    phenomenon = TheftPhenomenon(discovery_chance=1.0, arrest_chance=1.0, execution_weight=1.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True
    phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))
    assert not graph.deaths and not state[1]["is_thief"] and state[1]["convictions"] == 1


def test_prison_holds_them_with_family_ties_live_and_lets_them_out_cooled():
    graph = _thief_victim_graph()
    graph.add_node(Node(resident_id=3, ses="poor", alive=True, household_id=7))
    graph.nodes[1].household_id, graph.nodes[1].occupation = 7, "day_labourer"
    graph.add_edge(Edge(1, 3, "sibling", "Communal Sharing", 0.8, 0.8, 0.8, 0.5, 0.5))
    graph.add_node(Node(resident_id=4, ses="poor", alive=True))
    graph.add_edge(Edge(1, 4, "friend", "Communal Sharing", 0.6, 0.6, 0.6, 0.5, 0.5))
    graph.money, graph.belongings = {("p", 2): 100.0, ("p", 3): 50.0}, {}  # the thief can't pay
    phenomenon = TheftPhenomenon(discovery_chance=1.0, arrest_chance=1.0, execution_weight=0.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True
    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))
    assert any(e.kind == "imprisoned" for e in events) and graph.prisoners[1]["until"] == 5 + 182
    assert not graph.nodes[1].alive and graph.nodes[1].occupation is None
    graph.retire_ties_of_dead(6)
    assert graph.get_edge(1, 3) is not None and graph.get_edge(1, 4) is None  # family visits; a friend waits
    phenomenon._keep_prisoners(graph, 30, random.Random(5))
    assert graph.money[("p", 3)] < 50.0 and graph.money["commune"] > 0  # the family pays their keep
    phenomenon._keep_prisoners(graph, 5 + 182, random.Random(0))
    assert graph.nodes[1].alive and 1 not in graph.prisoners
    assert abs(graph.get_edge(1, 4).valence_from(4) - 0.4) < 1e-9  # back, a little cooler
    # a second conviction goes to prison even for one who could pay, for a year
    graph.money[("p", 1)] = 1000.0
    state[1]["is_thief"] = True
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, 0.0, 0.0))
    events = phenomenon.apply_effect(graph, state, 1, 2, day=300, rng=random.Random(0))
    assert not any(e.kind == "fined" for e in events) and graph.prisoners[1]["until"] == 300 + 365


def test_recent_arrests_suppress_the_become_thief_probability():
    trials = 200
    become_thief_rate = 0.05

    def hits(deterrence):
        count = 0
        for seed in range(trials):
            graph = SocialGraph()
            graph.add_node(Node(resident_id=1, ses="poor", alive=True, stress=1.0))
            phenomenon = TheftPhenomenon(become_thief_rate=become_thief_rate)
            phenomenon._deterrence = deterrence
            state = phenomenon.init_state(graph)
            phenomenon.end_of_day(graph, state, day=1, rng=random.Random(seed))
            count += state[1]["is_thief"]
        return count

    assert hits(deterrence=0.0) > hits(deterrence=50.0)


def test_more_stressed_residents_become_thieves_more_readily():
    trials = 200
    become_thief_rate = 0.3
    strained_hits = 0
    calmer_hits = 0
    for seed in range(trials):
        graph = SocialGraph()
        graph.add_node(Node(resident_id=1, ses="poor", alive=True, stress=0.95))
        graph.add_node(Node(resident_id=2, ses="poor", alive=True, stress=0.65))
        graph.add_node(Node(resident_id=3, ses="poor", alive=True, stress=0.5))  # poverty alone
        phenomenon = TheftPhenomenon(become_thief_rate=become_thief_rate)
        state = phenomenon.init_state(graph)
        phenomenon.end_of_day(graph, state, day=1, rng=random.Random(seed))
        strained_hits += state[1]["is_thief"]
        calmer_hits += state[2]["is_thief"]
        assert not state[3]["is_thief"]

    assert strained_hits > calmer_hits


def test_a_thief_under_less_strain_goes_straight_sooner():
    def quits(stress):
        count = 0
        for seed in range(100):
            graph = SocialGraph()
            graph.add_node(Node(resident_id=1, ses="poor", alive=True, stress=stress))
            phenomenon = TheftPhenomenon(become_thief_rate=0.0, quit_per_year_calm=0.99, quit_per_year_strained=0.0)
            state = phenomenon.init_state(graph)
            state[1]["is_thief"] = True
            for day in range(1, 91):
                phenomenon.end_of_day(graph, state, day=day, rng=random.Random(seed * 1000 + day))
            count += not state[1]["is_thief"]
        return count

    assert quits(0.3) > 50 and quits(0.9) == 0


def test_a_theft_takes_money_or_belongings_never_from_home_or_a_child():
    # 07 1.4 and 4.1, 09 §6 step 3 (user, 2026-10-12)
    taken = set()
    for seed in range(10):
        graph = _thief_victim_graph(victim_ses="middling")
        graph.money, graph.belongings = {("p", 2): 5.0}, {2: {"clothing": 4.0}}
        phenomenon = TheftPhenomenon(discovery_chance=0.0)
        state = phenomenon.init_state(graph)
        state[1]["is_thief"] = True
        phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(seed))
        kind = graph.payments[0][1]
        taken.add(kind)
        if kind == "theft":
            assert graph.money == {("p", 2): 4.0, ("p", 1): 1.0}
        else:
            assert kind == "theft: clothing" and graph.belongings == {2: {"clothing": 3.0}, 1: {"clothing": 1.0}}
    assert taken == {"theft", "theft: clothing"}
    for household, age in ((7, 30), (None, 9)):  # same household; a child
        graph = _thief_victim_graph()
        graph.nodes[1].household_id = graph.nodes[2].household_id = household
        graph.nodes[2].age = age
        graph.money, graph.belongings = {("p", 2): 5.0}, {}
        phenomenon = TheftPhenomenon()
        state = phenomenon.init_state(graph)
        state[1]["is_thief"] = True
        assert phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0)) == []


def _run_all():
    test_a_theft_takes_money_or_belongings_never_from_home_or_a_child()
    test_no_theft_edge_when_neither_side_is_a_thief()
    test_no_theft_edge_when_both_sides_are_thieves()
    test_richer_victims_are_more_attractive_targets()
    test_apply_effect_records_a_theft_event_regardless_of_discovery()
    test_when_caught_the_victims_valence_toward_the_thief_drops()
    test_a_caught_thief_loses_the_work_and_the_tie_but_not_family()
    test_when_caught_a_nearby_guards_valence_toward_the_thief_also_drops()
    test_arrested_thief_loses_thief_status_but_stays_alive()
    test_thief_can_be_arrested_with_no_guard_neighbor_at_all()
    test_low_loyalty_guards_execute_instead_of_arresting()
    test_a_first_conviction_never_hangs()
    test_prison_holds_them_with_family_ties_live_and_lets_them_out_cooled()
    test_recent_arrests_suppress_the_become_thief_probability()
    test_nobles_never_become_thieves()
    test_more_stressed_residents_become_thieves_more_readily()
    test_a_thief_under_less_strain_goes_straight_sooner()
    print("OK")


if __name__ == "__main__":
    _run_all()
