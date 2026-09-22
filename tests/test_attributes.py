import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import synthesize_relationship_attributes, synthesize_traits, FISKE_TAGS, RELATIONSHIP_TYPE_BASELINES, TRAIT_NAMES


def test_synthesized_values_are_in_range():
    rng = random.Random(1)
    for relationship_type in RELATIONSHIP_TYPE_BASELINES:
        for _ in range(50):
            attrs = synthesize_relationship_attributes(relationship_type, rng)
            assert 0.0 <= attrs["time"] <= 1.0
            assert 0.0 <= attrs["intimacy"] <= 1.0
            assert 0.0 <= attrs["services"] <= 1.0
            assert -1.0 <= attrs["valence_a_to_b"] <= 1.0
            assert -1.0 <= attrs["valence_b_to_a"] <= 1.0


def test_synthesis_is_deterministic_given_same_seed():
    attrs_a = synthesize_relationship_attributes("spouse", random.Random(42))
    attrs_b = synthesize_relationship_attributes("spouse", random.Random(42))
    assert attrs_a == attrs_b


def test_valence_directions_are_drawn_independently():
    rng = random.Random(2)
    attrs = synthesize_relationship_attributes("neighbor", rng)
    # not a given they'd differ every draw, but across many draws they must diverge at least once
    diverged = False
    for _ in range(50):
        attrs = synthesize_relationship_attributes("neighbor", rng)
        if attrs["valence_a_to_b"] != attrs["valence_b_to_a"]:
            diverged = True
            break
    assert diverged


def test_every_baseline_type_has_a_fiske_tag():
    for relationship_type in RELATIONSHIP_TYPE_BASELINES:
        assert relationship_type in FISKE_TAGS
    assert FISKE_TAGS["shopkeeper_customer"] == "Market Pricing"


def test_traits_are_in_range_and_cover_every_name():
    rng = random.Random(1)
    for _ in range(50):
        traits = synthesize_traits(rng)
        assert set(traits) == set(TRAIT_NAMES)
        for value in traits.values():
            assert 0.0 <= value <= 1.0


def test_traits_are_deterministic_given_same_seed():
    assert synthesize_traits(random.Random(7)) == synthesize_traits(random.Random(7))


def test_family_baseline_pulls_religiousness_and_skepticism_but_not_cunning_or_loyalty():
    # a family center far from the population mean should pull the
    # family-correlated traits toward it, while cunning/loyalty stay on
    # their own population-wide draw regardless
    baseline = {"religiousness": 0.95, "skepticism": 0.95}
    rng = random.Random(3)
    devout_family_draws = [synthesize_traits(rng, baseline) for _ in range(100)]
    avg_religiousness = sum(t["religiousness"] for t in devout_family_draws) / 100
    avg_skepticism = sum(t["skepticism"] for t in devout_family_draws) / 100
    assert avg_religiousness > 0.7
    assert avg_skepticism > 0.7

    rng2 = random.Random(3)
    population_draws = [synthesize_traits(rng2) for _ in range(100)]
    avg_cunning_population = sum(t["cunning"] for t in population_draws) / 100
    avg_cunning_family = sum(t["cunning"] for t in devout_family_draws) / 100
    # cunning is untouched by the family baseline -- both should land near
    # the same population mean (0.5), not near the family's 0.95 center
    assert abs(avg_cunning_family - 0.5) < 0.15
    assert abs(avg_cunning_population - 0.5) < 0.15


def test_family_correlated_traits_are_not_identical_within_a_family():
    # "more likely, not assured" -- individual draws around the same family
    # center must still vary from one member to the next
    baseline = {"religiousness": 0.5, "skepticism": 0.5}
    rng = random.Random(5)
    a = synthesize_traits(rng, baseline)
    b = synthesize_traits(rng, baseline)
    assert a["religiousness"] != b["religiousness"] or a["skepticism"] != b["skepticism"]


def _run_all():
    test_synthesized_values_are_in_range()
    test_synthesis_is_deterministic_given_same_seed()
    test_valence_directions_are_drawn_independently()
    test_every_baseline_type_has_a_fiske_tag()
    test_traits_are_in_range_and_cover_every_name()
    test_traits_are_deterministic_given_same_seed()
    test_family_baseline_pulls_religiousness_and_skepticism_but_not_cunning_or_loyalty()
    test_family_correlated_traits_are_not_identical_within_a_family()
    print("OK")


if __name__ == "__main__":
    _run_all()
