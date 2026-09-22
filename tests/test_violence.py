import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import RiotPhenomenon, ViolencePhenomenon


def _graph_with_valence(valence_a_to_b: float, valence_b_to_a: float = None) -> SocialGraph:
    if valence_b_to_a is None:
        valence_b_to_a = valence_a_to_b
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
                         valence_a_to_b=valence_a_to_b, valence_b_to_a=valence_b_to_a))
    return graph


def test_positive_valence_edges_never_fire():
    graph = _graph_with_valence(0.6)
    phenomenon = ViolencePhenomenon(base_rate=0.5)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_edge_probability_formula():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.4, intimacy=0.4, services=0.4,
                valence_a_to_b=-0.4, valence_b_to_a=-0.4)
    graph.add_edge(edge)
    phenomenon = ViolencePhenomenon(base_rate=0.1)
    state = phenomenon.init_state(graph)
    probability = phenomenon.edge_probability(edge, state[1], state[2], day=1)
    # tie_strength = mean(0.4, 0.4, 0.4, 0.4) = 0.4; probability = base_rate * hostility * tie_strength
    assert abs(probability - (0.1 * 0.4 * 0.4)) < 1e-9


def test_probability_driven_by_the_more_hostile_direction():
    # 1 despises 2 (-0.9), but 2 doesn't mind 1 at all (0.0) -- the pair's odds
    # should reflect 1's hostility, not an average that waters it down
    graph = _graph_with_valence(valence_a_to_b=-0.9, valence_b_to_a=0.0)
    phenomenon = ViolencePhenomenon(base_rate=0.5)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    probability = phenomenon.edge_probability(edge, state[1], state[2], day=1)
    # tie_strength = mean(0.5, 0.45, 0.5, 0.5) = 0.4875 (avg |valence| = 0.45)
    assert abs(probability - (0.5 * 0.9 * 0.4875)) < 1e-9


def test_probability_is_monotonic_in_animosity_magnitude():
    phenomenon = ViolencePhenomenon(base_rate=0.5)
    mild = _graph_with_valence(-0.2)
    severe = _graph_with_valence(-0.9)
    state_mild = phenomenon.init_state(mild)
    state_severe = phenomenon.init_state(severe)
    p_mild = phenomenon.edge_probability(mild.get_edge(1, 2), state_mild[1], state_mild[2], day=1)
    p_severe = phenomenon.edge_probability(severe.get_edge(1, 2), state_severe[1], state_severe[2], day=1)
    assert p_severe > p_mild


def test_aggressor_is_the_more_hostile_side_when_vulnerability_is_equal():
    # both poor (equal SES vulnerability), but only 1 has any animosity toward 2 --
    # 1 must be picked as the aggressor every time, never 2
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="poor", alive=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
                valence_a_to_b=-0.9, valence_b_to_a=0.0)
    graph.add_edge(edge)
    phenomenon = ViolencePhenomenon()
    for seed in range(20):
        assert phenomenon._pick_aggressor(graph, edge, 1, 2, random.Random(seed)) == 1


def test_loyalty_dampens_own_odds_of_being_the_aggressor():
    # equal hostility and equal SES vulnerability, but 1 is far more loyal
    # than 2 -- 2 should be picked as the aggressor every time
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True, loyalty=0.95))
    graph.add_node(Node(resident_id=2, ses="poor", alive=True, loyalty=0.05))
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
                valence_a_to_b=-0.9, valence_b_to_a=-0.9)
    graph.add_edge(edge)
    phenomenon = ViolencePhenomenon()
    for seed in range(20):
        assert phenomenon._pick_aggressor(graph, edge, 1, 2, random.Random(seed)) == 2


def test_grief_shock_increases_neighbors_animosity_toward_culprit():
    graph = SocialGraph()
    for resident_id, ses in [(1, "poor"), (2, "rich"), (3, "middling")]:
        graph.add_node(Node(resident_id=resident_id, ses=ses, alive=True))
    # 1 and 2 are the violent pair; 3 is close to 1 (the victim) and already knows 2 (the culprit)
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, -0.9))
    graph.add_edge(Edge(1, 3, "sibling", "Communal Sharing", 0.8, 0.8, 0.8, 0.7, 0.7))
    graph.add_edge(Edge(2, 3, "coworker", "Authority Ranking", 0.4, 0.2, 0.3, 0.1, 0.1))

    phenomenon = ViolencePhenomenon(base_rate=1.0, grief_shock=0.15)
    state = phenomenon.init_state(graph)
    phenomenon._pick_aggressor = lambda graph, edge, a, b, rng: 2  # force resident 2 to be the culprit, 1 the victim

    events = phenomenon.apply_effect(graph, state, 1, 2, day=200, rng=random.Random(0))

    assert graph.nodes[1].alive is False
    assert state[1]["alive"] is False
    edge_2_3 = graph.get_edge(2, 3)
    # only 3's own feeling toward 2 should have moved -- 2's feeling toward 3 is untouched
    assert edge_2_3.valence_from(3) < 0.1  # nudged more negative from its starting 0.1
    assert edge_2_3.valence_from(2) == 0.1  # the culprit's own feelings aren't rewritten by grief
    assert any(event.kind == "grief_shock" and event.resident_a == 3 for event in events)


def test_poor_attacker_vs_rich_victim_succeeds_less_often_than_the_reverse():
    trials = 300

    def success_rate(attacker_ses, victim_ses):
        successes = 0
        for seed in range(trials):
            graph = SocialGraph()
            graph.add_node(Node(resident_id=1, ses=attacker_ses, alive=True))
            graph.add_node(Node(resident_id=2, ses=victim_ses, alive=True))
            graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, -0.9))
            phenomenon = ViolencePhenomenon(success_base_rate=0.85)
            phenomenon._pick_aggressor = lambda graph, edge, a, b, rng: 1  # force resident 1 as culprit
            state = phenomenon.init_state(graph)
            phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(seed))
            successes += not graph.nodes[2].alive
        return successes / trials

    poor_attacks_rich = success_rate("poor", "rich")
    rich_attacks_poor = success_rate("rich", "poor")
    assert poor_attacks_rich < rich_attacks_poor


def test_failed_attempt_leaves_victim_alive_and_drops_their_valence_toward_culprit():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5,
                         valence_a_to_b=-0.9, valence_b_to_a=0.2))
    # poor attacking rich: success_chance = min(1, 0.0 * ...) = 0 -- guaranteed failure
    phenomenon = ViolencePhenomenon(success_base_rate=0.0, discovery_shock=0.3)
    phenomenon._pick_aggressor = lambda graph, edge, a, b, rng: 1  # 1 (poor) attacks 2 (rich)
    state = phenomenon.init_state(graph)

    events = phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))

    assert graph.nodes[2].alive is True
    assert state[2]["alive"] is True
    edge = graph.get_edge(1, 2)
    assert abs(edge.valence_from(2) - (-0.1)) < 1e-9  # 0.2 - 0.3 discovery_shock
    assert any(event.kind == "failed_attempt" for event in events)


def test_summarize_counts_alive_and_dead():
    graph = _graph_with_valence(-0.5)
    phenomenon = ViolencePhenomenon()
    state = phenomenon.init_state(graph)
    state[1]["alive"] = False
    assert phenomenon.summarize(state) == {
        "alive": 1, "dead": 1, "group_kills": 0, "hired_assassinations": 0, "mercenaries_hired": 0,
    }


def test_noble_culprit_hires_an_assassin_with_reduced_grief_shock():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))  # noble culprit
    graph.nodes[1].is_noble = True
    graph.add_node(Node(resident_id=2, ses="poor", alive=True))  # victim
    graph.add_node(Node(resident_id=3, ses="middling", alive=True))  # victim's neighbor
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, -0.9))
    graph.add_edge(Edge(1, 3, "coworker", "Authority Ranking", 0.4, 0.2, 0.3, 0.1, 0.1))
    graph.add_edge(Edge(2, 3, "sibling", "Communal Sharing", 0.8, 0.8, 0.8, 0.7, 0.7))

    phenomenon = ViolencePhenomenon(
        base_rate=1.0, success_base_rate=1.0, grief_shock=0.15, noble_hired_assassin_shock_factor=0.5,
    )
    phenomenon._pick_aggressor = lambda graph, edge, a, b, rng: 1  # force the noble as culprit
    state = phenomenon.init_state(graph)

    edge_2_3_tie_strength = graph.get_edge(2, 3).tie_strength
    events = phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))

    assert graph.nodes[2].alive is False
    assert phenomenon._hired_assassinations == 1
    assert any(event.kind == "hired_assassination" for event in events)
    edge_1_3 = graph.get_edge(1, 3)
    full_shock = 0.15 * edge_2_3_tie_strength
    assert abs(edge_1_3.valence_from(3) - (0.1 - full_shock * 0.5)) < 1e-9  # halved, not zeroed


def test_non_noble_culprit_gets_full_grief_shock_not_the_hired_discount():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))  # ordinary culprit, not a noble
    graph.add_node(Node(resident_id=2, ses="poor", alive=True))
    graph.add_node(Node(resident_id=3, ses="middling", alive=True))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, -0.9))
    graph.add_edge(Edge(1, 3, "coworker", "Authority Ranking", 0.4, 0.2, 0.3, 0.1, 0.1))
    graph.add_edge(Edge(2, 3, "sibling", "Communal Sharing", 0.8, 0.8, 0.8, 0.7, 0.7))

    phenomenon = ViolencePhenomenon(base_rate=1.0, success_base_rate=1.0, grief_shock=0.15)
    phenomenon._pick_aggressor = lambda graph, edge, a, b, rng: 1
    state = phenomenon.init_state(graph)

    edge_2_3_tie_strength = graph.get_edge(2, 3).tie_strength
    events = phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))

    assert phenomenon._hired_assassinations == 0
    assert any(event.kind == "violence" for event in events)
    edge_1_3 = graph.get_edge(1, 3)
    full_shock = 0.15 * edge_2_3_tie_strength
    assert abs(edge_1_3.valence_from(3) - (0.1 - full_shock)) < 1e-9  # full grief_shock, no discount


def test_noble_culprit_failed_attempt_gets_reduced_discovery_shock():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.nodes[1].is_noble = True
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5,
                         valence_a_to_b=-0.9, valence_b_to_a=0.2))
    # poor attacking rich: success_chance = 0 -- guaranteed failure
    phenomenon = ViolencePhenomenon(success_base_rate=0.0, discovery_shock=0.3, noble_hired_assassin_shock_factor=0.5)
    phenomenon._pick_aggressor = lambda graph, edge, a, b, rng: 1
    state = phenomenon.init_state(graph)

    events = phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))

    assert graph.nodes[2].alive is True
    edge = graph.get_edge(1, 2)
    assert abs(edge.valence_from(2) - (0.2 - 0.15)) < 1e-9  # 0.3 discovery_shock halved to 0.15
    assert any(event.kind == "hired_assassin_failed" for event in events)


def _noble_with_enemies(num_enemies, ex_soldier_ids=(), enemy_valence=-0.9):
    """A noble (id 100) hated by `num_enemies` distinct civilians (ids 1..N),
    each above the default mercenary_enemy_threshold. `ex_soldier_ids` marks
    which of those same neighbors are also is_ex_soldier=True candidates."""
    graph = SocialGraph()
    graph.add_node(Node(resident_id=100, ses="rich", alive=True, is_noble=True))
    for i in range(1, num_enemies + 1):
        graph.add_node(Node(resident_id=i, ses="poor", alive=True, is_ex_soldier=i in ex_soldier_ids))
        graph.add_edge(Edge(i, 100, "neighbor", "Equality Matching", 0.5, 0.5, 0.5,
                             valence_a_to_b=enemy_valence, valence_b_to_a=0.0))
    return graph


def test_no_hire_below_min_enemies_even_with_a_candidate_present():
    graph = _noble_with_enemies(num_enemies=3, ex_soldier_ids={1})  # 3 == min_enemies, not above it
    phenomenon = ViolencePhenomenon(mercenary_min_enemies=3, mercenary_hire_rate=1.0)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert events == []
    assert state[100]["mercenaries"] == []


def test_hire_rate_scales_with_how_far_past_the_enemy_threshold():
    # mercenary_hire_rate * excess must be a real probability (<=1); pick
    # values so the "just above threshold" case is far less likely to hire
    # than the "way above threshold" case, over many days
    def hires_within(num_enemies, days=30):
        hires = 0
        for seed in range(60):
            graph = _noble_with_enemies(num_enemies, ex_soldier_ids={1})
            phenomenon = ViolencePhenomenon(mercenary_min_enemies=3, mercenary_hire_rate=0.05)
            state = phenomenon.init_state(graph)
            for day in range(1, days + 1):
                phenomenon.end_of_day(graph, state, day=day, rng=random.Random(seed * 1000 + day))
                if state[100]["mercenaries"]:
                    break
            hires += bool(state[100]["mercenaries"])
        return hires

    assert hires_within(num_enemies=4) < hires_within(num_enemies=10)


def test_no_hire_without_an_ex_soldier_candidate_among_neighbors():
    graph = _noble_with_enemies(num_enemies=5, ex_soldier_ids=())  # nobody eligible
    phenomenon = ViolencePhenomenon(mercenary_min_enemies=3, mercenary_hire_rate=1.0)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert events == []
    assert state[100]["mercenaries"] == []


def test_hiring_is_capped():
    graph = _noble_with_enemies(num_enemies=5, ex_soldier_ids={1, 2, 3, 4, 5})
    phenomenon = ViolencePhenomenon(mercenary_min_enemies=0, mercenary_hire_rate=1.0, mercenary_cap=2)
    state = phenomenon.init_state(graph)
    for day in range(1, 10):
        phenomenon.end_of_day(graph, state, day=day, rng=random.Random(day))
    assert len(state[100]["mercenaries"]) == 2


def test_hired_mercenary_marks_ex_soldier_as_unavailable_to_others():
    graph = _noble_with_enemies(num_enemies=5, ex_soldier_ids={1})
    graph.add_node(Node(resident_id=200, ses="rich", alive=True, is_noble=True))
    graph.add_edge(Edge(1, 200, "coworker", "Authority Ranking", 0.5, 0.5, 0.5, -0.9, 0.0))
    # both 100 and 200 want to hire, only one ex-soldier (1) exists town-wide
    phenomenon = ViolencePhenomenon(mercenary_min_enemies=0, mercenary_hire_rate=1.0)
    state = phenomenon.init_state(graph)
    phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert state[1]["hired_by"] in (100, 200)
    only_one_hired = (state[100]["mercenaries"] == [1]) != (state[200]["mercenaries"] == [1])
    assert only_one_hired


def test_ex_soldier_becomes_available_again_once_employer_dies():
    graph = _noble_with_enemies(num_enemies=5, ex_soldier_ids={1})
    # a second noble, also with enemies and also tied to the same ex-soldier,
    # present from the start (the engine never adds nodes mid-run -- Romance's
    # own "not yet a tracked resident" note for newborns says the same)
    graph.add_node(Node(resident_id=200, ses="rich", alive=True, is_noble=True))
    graph.add_edge(Edge(1, 200, "coworker", "Authority Ranking", 0.5, 0.5, 0.5, -0.9, 0.0))
    graph.add_edge(Edge(2, 200, "coworker", "Authority Ranking", 0.5, 0.5, 0.5, -0.9, 0.0))
    graph.add_edge(Edge(3, 200, "coworker", "Authority Ranking", 0.5, 0.5, 0.5, -0.9, 0.0))

    phenomenon = ViolencePhenomenon(mercenary_min_enemies=0, mercenary_hire_rate=1.0)
    state = phenomenon.init_state(graph)
    phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert state[1]["hired_by"] in (100, 200)
    first_employer = state[1]["hired_by"]
    other_noble = 200 if first_employer == 100 else 100

    graph.nodes[first_employer].alive = False  # the employer dies
    phenomenon.end_of_day(graph, state, day=2, rng=random.Random(1))
    assert state[1]["hired_by"] == other_noble


def test_living_mercenaries_reduce_an_attackers_success_chance():
    trials = 200

    def build(mercenary_alive):
        graph = SocialGraph()
        # matched SES so the plain success formula alone gives exactly
        # success_base_rate, leaving only mercenary protection to vary
        graph.add_node(Node(resident_id=1, ses="middling", alive=True))  # attacker
        graph.add_node(Node(resident_id=100, ses="middling", alive=True, is_noble=True))  # protected victim
        graph.add_node(Node(resident_id=5, ses="poor", alive=mercenary_alive))  # the hired mercenary
        graph.add_edge(Edge(1, 100, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, -0.9))
        phenomenon = ViolencePhenomenon(success_base_rate=1.0, mercenary_protection_factor=0.5)
        phenomenon._pick_aggressor = lambda graph, edge, a, b, rng: 1
        state = phenomenon.init_state(graph)
        state[100]["mercenaries"] = [5]
        return graph, phenomenon, state

    def kill_rate(mercenary_alive):
        kills = 0
        for seed in range(trials):
            graph, phenomenon, state = build(mercenary_alive)
            phenomenon.apply_effect(graph, state, 1, 100, day=1, rng=random.Random(seed))
            kills += not graph.nodes[100].alive
        return kills / trials

    # success_base_rate=1.0 -- a dead mercenary gives no protection, so this
    # must stay a guaranteed kill; a living one (factor=0.5) must cut it down
    assert kill_rate(mercenary_alive=False) == 1.0
    assert kill_rate(mercenary_alive=True) < 1.0


def _group_town(num_haters, victim_id=100, victim_ses="poor", hater_ses="poor", hate=-0.9, affinity=0.6):
    """A victim hated independently by `num_haters` people (ids 1..N), who are
    themselves chained together (1-2, 2-3, ...) by mutual affinity -- a single
    connected band, without needing every pair directly tied. Equal SES by
    default so success chance reduces to a clean function of band size."""
    graph = SocialGraph()
    graph.add_node(Node(resident_id=victim_id, ses=victim_ses, alive=True))
    for i in range(1, num_haters + 1):
        graph.add_node(Node(resident_id=i, ses=hater_ses, alive=True))
        graph.add_edge(Edge(i, victim_id, "neighbor", "Equality Matching", 0.5, 0.5, 0.5,
                             valence_a_to_b=hate, valence_b_to_a=0.0))
    for i in range(1, num_haters):
        graph.add_edge(Edge(i, i + 1, "coworker", "Authority Ranking", 0.5, 0.5, 0.5,
                             valence_a_to_b=affinity, valence_b_to_a=affinity))
    return graph, victim_id


def test_haters_with_no_tie_to_each_other_do_not_band_together():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=100, ses="poor", alive=True))
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="poor", alive=True))
    graph.add_edge(Edge(1, 100, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    graph.add_edge(Edge(2, 100, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    # no edge between 1 and 2 at all -- sharing a grudge alone isn't enough
    phenomenon = ViolencePhenomenon(success_base_rate=1.0, min_group_size=2)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert events == []
    assert graph.nodes[100].alive is True


def test_haters_who_dislike_each_other_do_not_band_together():
    graph, victim_id = _group_town(num_haters=2, affinity=-0.9)  # haters despise each other
    phenomenon = ViolencePhenomenon(success_base_rate=1.0, min_group_size=2)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert events == []
    assert graph.nodes[victim_id].alive is True


def test_mutually_tied_haters_band_together_and_can_kill():
    graph, victim_id = _group_town(num_haters=2)
    # sqrt(2) boost guarantees success; group_action_rate=1.0 makes the "does
    # this band act today" roll deterministic, isolating the kill logic itself
    phenomenon = ViolencePhenomenon(success_base_rate=1.0, min_group_size=2, group_action_rate=1.0)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert graph.nodes[victim_id].alive is False
    assert any(event.kind == "group_violence" for event in events)
    assert phenomenon._group_kills == 1


def test_group_success_chance_grows_with_band_size():
    # mismatched vulnerability (rich victim, poor haters) keeps the success
    # chance away from the 1.0 ceiling so the sqrt(band size) boost is visible
    trials = 200

    def kill_rate(num_haters):
        kills = 0
        for seed in range(trials):
            graph, victim_id = _group_town(num_haters, victim_ses="rich", hater_ses="poor")
            phenomenon = ViolencePhenomenon(success_base_rate=1.0, min_group_size=2, group_action_rate=1.0)
            state = phenomenon.init_state(graph)
            phenomenon.end_of_day(graph, state, day=1, rng=random.Random(seed))
            kills += not graph.nodes[victim_id].alive
        return kills / trials

    assert kill_rate(9) > kill_rate(4)


def test_failed_group_attempt_drops_victims_valence_toward_every_band_member():
    graph, victim_id = _group_town(num_haters=2)
    phenomenon = ViolencePhenomenon(success_base_rate=0.0, discovery_shock=0.3, min_group_size=2, group_action_rate=1.0)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))

    assert graph.nodes[victim_id].alive is True
    for hater_id in (1, 2):
        edge = graph.get_edge(hater_id, victim_id)
        assert edge.valence_from(victim_id) < 0  # dropped from its starting 0.0
    assert any(event.kind == "group_failed_attempt" for event in events)


def test_large_enough_band_escalates_into_a_riot_instead_of_a_kill():
    graph, victim_id = _group_town(num_haters=5)
    riot = RiotPhenomenon(min_participants=3)
    phenomenon = ViolencePhenomenon(success_base_rate=1.0, min_group_size=2, riot_phenomenon=riot, group_action_rate=1.0)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))

    assert riot._riots == 1
    assert riot._active_riot is not None
    assert set(riot._active_riot["participants"]) == {1, 2, 3, 4, 5}
    assert any(event.kind == "group_escalates_to_riot" for event in events)
    assert any(event.kind == "riot" for event in events)
    assert phenomenon._group_kills == 0  # handed off to the riot, not killed directly


def test_band_too_small_for_a_riot_still_just_kills_the_victim():
    graph, victim_id = _group_town(num_haters=2)
    riot = RiotPhenomenon(min_participants=3)  # band of 2 stays below this
    phenomenon = ViolencePhenomenon(success_base_rate=1.0, min_group_size=2, riot_phenomenon=riot, group_action_rate=1.0)
    state = phenomenon.init_state(graph)
    phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))

    assert riot._riots == 0
    assert graph.nodes[victim_id].alive is False
    assert phenomenon._group_kills == 1


def test_large_band_without_a_riot_phenomenon_wired_in_still_just_kills():
    graph, victim_id = _group_town(num_haters=5)
    # riot_phenomenon left as None
    phenomenon = ViolencePhenomenon(success_base_rate=1.0, min_group_size=2, group_action_rate=1.0)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))

    assert graph.nodes[victim_id].alive is False
    assert any(event.kind == "group_violence" for event in events)


def test_group_action_rate_gates_whether_a_qualifying_band_acts_today():
    # a qualifying band exists every single day here (nothing removes it),
    # but with group_action_rate=0.0 it must never act
    graph, victim_id = _group_town(num_haters=2)
    phenomenon = ViolencePhenomenon(success_base_rate=1.0, min_group_size=2, group_action_rate=0.0)
    state = phenomenon.init_state(graph)
    for day in range(1, 31):
        events = phenomenon.end_of_day(graph, state, day=day, rng=random.Random(day))
        assert events == []
    assert graph.nodes[victim_id].alive is True
    assert phenomenon._group_kills == 0


def _run_all():
    test_positive_valence_edges_never_fire()
    test_edge_probability_formula()
    test_probability_driven_by_the_more_hostile_direction()
    test_probability_is_monotonic_in_animosity_magnitude()
    test_aggressor_is_the_more_hostile_side_when_vulnerability_is_equal()
    test_loyalty_dampens_own_odds_of_being_the_aggressor()
    test_grief_shock_increases_neighbors_animosity_toward_culprit()
    test_poor_attacker_vs_rich_victim_succeeds_less_often_than_the_reverse()
    test_failed_attempt_leaves_victim_alive_and_drops_their_valence_toward_culprit()
    test_summarize_counts_alive_and_dead()
    test_noble_culprit_hires_an_assassin_with_reduced_grief_shock()
    test_non_noble_culprit_gets_full_grief_shock_not_the_hired_discount()
    test_noble_culprit_failed_attempt_gets_reduced_discovery_shock()
    test_no_hire_below_min_enemies_even_with_a_candidate_present()
    test_hire_rate_scales_with_how_far_past_the_enemy_threshold()
    test_no_hire_without_an_ex_soldier_candidate_among_neighbors()
    test_hiring_is_capped()
    test_hired_mercenary_marks_ex_soldier_as_unavailable_to_others()
    test_ex_soldier_becomes_available_again_once_employer_dies()
    test_living_mercenaries_reduce_an_attackers_success_chance()
    test_haters_with_no_tie_to_each_other_do_not_band_together()
    test_haters_who_dislike_each_other_do_not_band_together()
    test_mutually_tied_haters_band_together_and_can_kill()
    test_group_success_chance_grows_with_band_size()
    test_failed_group_attempt_drops_victims_valence_toward_every_band_member()
    test_large_enough_band_escalates_into_a_riot_instead_of_a_kill()
    test_band_too_small_for_a_riot_still_just_kills_the_victim()
    test_large_band_without_a_riot_phenomenon_wired_in_still_just_kills()
    test_group_action_rate_gates_whether_a_qualifying_band_acts_today()
    print("OK")


if __name__ == "__main__":
    _run_all()
