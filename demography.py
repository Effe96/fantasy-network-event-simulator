# demography.py
"""How long people live in the sim, in one place: the old-age death chance
PopulationPhenomenon rolls, and the settled age structure the importer
reshapes TownShape's town into (2026-09-27)."""
import math
from typing import List

OLD_AGE_ONSET = 50
# yearly chance of dying of old age: 1% at 50, x e every 10 years
# (2.7% at 60, 7.4% at 70, 20% at 80, 54% at 90), on top of disease and
# violence -- close to a medieval life table once those are added
OLD_AGE_BASE = 0.01
OLD_AGE_RATE = 0.1
MAX_AGE = 99

# ponytail: measured, not derived -- share of residents per 5-year band
# (0-4 ... 75-79, 80+) averaged over years 40, 45 and 50 of the 50-year run
# (seed 1, epidemics off, 2026-09-25), i.e. what the sim itself settles into,
# arrivals included. That run had no old-age deaths, so bands from 50 up are
# thinned by old-age survival in settled_age_weights. Re-measure after a long
# run whenever births, deaths or arrivals change much.
SETTLED_BAND_SHARES = [12.1, 11.2, 9.1, 7.9, 8.2, 8.5, 7.9, 6.4, 5.2, 4.4, 4.3, 3.9, 3.3, 2.4, 1.7, 1.1, 2.5]


def old_age_death_chance(age: int) -> float:
    if age < OLD_AGE_ONSET:
        return 0.0
    return min(1.0, OLD_AGE_BASE * math.exp(OLD_AGE_RATE * (age - OLD_AGE_ONSET)))


def settled_age_weights() -> List[float]:
    """Relative share of residents at each age 0..MAX_AGE in a town settled
    under the sim's rules: the measured band shares spread evenly within
    each band (80+ over 80-99), times the chance of surviving old age."""
    weights, surviving = [], 1.0
    for age in range(MAX_AGE + 1):
        band = min(age // 5, len(SETTLED_BAND_SHARES) - 1)
        width = 5 if band < len(SETTLED_BAND_SHARES) - 1 else MAX_AGE + 1 - 80
        weights.append(SETTLED_BAND_SHARES[band] / width * surviving)
        surviving *= 1.0 - old_age_death_chance(age)
    return weights


if __name__ == "__main__":
    w = settled_age_weights()
    total = sum(w)
    bands = [sum(w[a:a + 5]) / total for a in range(0, 80, 5)] + [sum(w[80:]) / total]
    print("share by 5-year band:", [round(100 * b, 1) for b in bands])
    assert abs(sum(bands) - 1.0) < 1e-9 and bands[0] > bands[12] and old_age_death_chance(49) == 0.0
    print(f"old-age chance at 60/70/80: {old_age_death_chance(60):.3f} {old_age_death_chance(70):.3f} {old_age_death_chance(80):.3f}")
