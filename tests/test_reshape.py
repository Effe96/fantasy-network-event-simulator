import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demography import old_age_death_chance, settled_age_weights
from graph import Edge, Node, SocialGraph, reshape_to_settled_town


def _family(spouse_gender="female"):
    """Household 7: two spouses (1, 2) with two children (3, 4)."""
    graph = SocialGraph()
    graph.reference_year = 1300
    for resident_id, gender, age in [(1, "female", 60), (2, spouse_gender, 25), (3, "male", 2), (4, "female", 0)]:
        graph.add_node(Node(resident_id=resident_id, ses="poor", gender=gender, age=age, household_id=7))
    graph.add_edge(Edge(1, 2, "spouse", "Communal Sharing", 0.7, 0.7, 0.7, 0.4, 0.4))
    for child in (3, 4):
        graph.add_edge(Edge(1, child, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.4, 0.4))
    return graph


def test_reshaped_families_stay_plausible():
    for seed in range(50):
        graph = _family()
        reshape_to_settled_town(graph, seed)
        parents, children = [graph.nodes[1], graph.nodes[2]], [graph.nodes[3], graph.nodes[4]]
        first = graph.nodes[1].age  # the household's first adult
        assert all(p.age >= 18 for p in parents) and all(c.age <= 29 for c in children)
        assert all(first - 45 <= c.age <= first - 18 for c in children)
        assert graph.nodes[1].birth_date == f"{1300 - graph.nodes[1].age:04d}-01-01"


def test_same_sex_couples_are_kept_only_up_to_the_town_s_share():
    graph = _family(spouse_gender="female")
    graph.params.same_sex_share = 0.0
    reshape_to_settled_town(graph, 1)
    assert graph.nodes[2].gender == "male"
    graph = _family(spouse_gender="female")
    graph.params.same_sex_share = 1.0
    reshape_to_settled_town(graph, 1)
    assert graph.nodes[2].gender == "female"


def test_the_old_die_more_and_the_settled_town_is_young():
    assert old_age_death_chance(40) == 0.0 < old_age_death_chance(60) < old_age_death_chance(80)
    weights = settled_age_weights()
    assert sum(weights[:18]) > sum(weights[60:])


def _run_all():
    test_reshaped_families_stay_plausible()
    test_same_sex_couples_are_kept_only_up_to_the_town_s_share()
    test_the_old_die_more_and_the_settled_town_is_young()
    print("OK")


if __name__ == "__main__":
    _run_all()
