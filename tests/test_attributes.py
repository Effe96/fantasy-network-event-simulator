import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import synthesize_relationship_attributes, FISKE_TAGS, RELATIONSHIP_TYPE_BASELINES


def test_synthesized_values_are_in_range():
    rng = random.Random(1)
    for relationship_type in RELATIONSHIP_TYPE_BASELINES:
        for _ in range(50):
            attrs = synthesize_relationship_attributes(relationship_type, rng)
            assert 0.0 <= attrs["time"] <= 1.0
            assert 0.0 <= attrs["intimacy"] <= 1.0
            assert 0.0 <= attrs["services"] <= 1.0
            assert -1.0 <= attrs["valence"] <= 1.0


def test_synthesis_is_deterministic_given_same_seed():
    attrs_a = synthesize_relationship_attributes("spouse", random.Random(42))
    attrs_b = synthesize_relationship_attributes("spouse", random.Random(42))
    assert attrs_a == attrs_b


def test_every_baseline_type_has_a_fiske_tag():
    for relationship_type in RELATIONSHIP_TYPE_BASELINES:
        assert relationship_type in FISKE_TAGS
    assert FISKE_TAGS["shopkeeper_customer"] == "Market Pricing"


def _run_all():
    test_synthesized_values_are_in_range()
    test_synthesis_is_deterministic_given_same_seed()
    test_every_baseline_type_has_a_fiske_tag()
    print("OK")


if __name__ == "__main__":
    _run_all()
