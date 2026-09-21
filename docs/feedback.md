# Feedback Log

> **What this file is for.** Your running notes on what the simulation
> *does*, not on the code that makes it do that — "riots feel too bloody,"
> "theft rate seems high for a rich town," "the bribery number surprised
> me." Write an entry any time something in a run or the dashboard looks
> off, interesting, or worth changing, whether or not you know the fix.
>
> Distinct from `docs/plans.md` (what's queued next) and
> `docs/decisions.md` (why a past choice was made) — this file is the
> *inbox* those two get fed from. At the start of a session, read every
> `open` entry here, decide whether it's a bug, a calibration tweak, or a
> new feature, and either fix it directly or fold it into `plans.md`. Once
> handled, flip its status and say what happened — don't delete entries,
> so there's a record of what was raised and how it was resolved.
>
> Add an entry with a dated `##` heading, newest at the top. Nothing fancy
> required — a sentence or two is enough.

<!-- Add new entries below this line, newest first. -->

## 2026-09-21 (common ailments follow-up)

- Diarrhea and flu should go up and down. Flu should have a higher chance
  and higher contagion factor in the last quarter and first quarter of
  the year. Also — are people considering that people can recover? It
  seems strange that diarrhea cases are just growing, seemingly
  indefinitely.
  **[fixed 2026-09-21 — two separate things. (1) Flu is now seasonal: a `flu_winter_multiplier` (3x default) applies to both its transmission rate and spontaneous rate during Q4+Q1. Diarrhea intentionally has no seasonality — the request only asked for it on flu. (2) Recovery already existed (`sick`→`immune`→`healthy`, see the common-ailments entry above) and currently-sick counts already fluctuated; the "indefinite growth" was the dashboard's cumulative-cases chart, which is a running total by construction. Fixed by charting currently-sick counts instead. See `docs/decisions.md`'s 2026-09-21 seasonality entry.]**

## 2026-09-21 (later, refined twice)

- There shouldn't just be one patient-zero-driven epidemic. There should
  also be common ailments — diarrhea, flu, this kind of thing that was
  easy to get in medieval times and could be fatal, though not always.
  Anyone can get diarrhea or flu with a probability tied to how poor
  they are, and the probability they die (low) also depends on how poor
  they are. Flu is contagious, diarrhea is not.
  **[fixed 2026-09-21 — implemented as `CommonAilmentsPhenomenon`: flu (contagious, reuses transmission + a small spontaneous "outside" rate) and diarrhea (non-contagious, per-resident roll), both poverty-scaled on incidence and fatality. A first version with zero post-recovery immunity produced a runaway (~29,500 flu cases/year, 562 deaths) on the dense reference-town graph before it was caught with a real run and fixed with temporary immunity windows + a ~75× transmission-rate cut. After the fix: flu 354 cases/year (1 death), diarrhea 1,628 cases/year (31 deaths). See `docs/decisions.md`'s 2026-09-21 entry and `tests/test_ailments.py`.]**

## 2026-09-21

- In a normal city, with average starting parameters (average loyalty, average religiosity, average richness and so), the amount of thieves should not just grow indefinitely. It cannot be that 27% of a town turns out to be thieves in just a year, that is not realistic at all. Number of thieves should reach a plateau at some point, and then slightly fluctuate. Tune down the probability of a poor person becoming a thief. This probability should also depend on how many thieves have been arrested recently: probability goes down if there have been many arrests recently, goes up if there have not been many at all. The probability of arrests should of course depend on number of guards, on corruption. Also, thieves are not just arrested. Let's say that in high corruption cities, thieves are often killed after being arrested. That lowers probability of new thieves appearing (people do not want to be killed). Probability should depend also on how effectively poor a person is.
  **[fixed 2026-09-21, took two tries — arrest/execution + decaying deterrence added to `TheftPhenomenon`. First version (gated on guard-neighbor adjacency) looked right on a 1-year trajectory but a 3-year check, prompted by the direct question "are you sure it plateaus?", showed it wasn't converging at all. Corrected to a flat town-wide arrest chance; a 2-year run now shows real fluctuation including genuine declines, though the exact equilibrium level isn't fully pinned down yet. Poverty-severity and a real corruption dial (vs. reusing guard loyalty) still deferred. See `docs/decisions.md`'s two 2026-09-21 entries.]**
- Are you giving any income to people that do not have a job, but daily jobs? They should also have irregular income, related to their sporadic day jobs.
  **[triaged → folded into Project_Vision's new §Economy & poverty, 2026-09-21. No income model exists at all today — `ses` is a static import, never earned/spent.]**
- For very poor people, there is a change also to become beggars, not just thieves.
  **[triaged → folded into Project_Vision §Criminals + §Economy & poverty, 2026-09-21.]**
- I would like to add a "dead because of hardships". First of all, very poor people are more likely to get sick and die because of a sickness. If a person is poor for too long, they cannot buy food or water, so they should die after a while that they are poor.
  **[triaged → folded into Project_Vision's new §Economy & poverty, 2026-09-21. Two distinct mechanics: elevated ambient sickness, and a separate hardship/starvation death from sustained poverty duration.]**
- It seems very hard to me that 24 guards died, more than the rioters. There must be some parameter that should be tweaked, unless the rioters are OVERHELMINLGY MORE than the guards (10-fold at least), more rioters should die than guards (in this case, just by heart, I think it should have been something like 15 guards and 28 rioters).
  **[fixed 2026-09-21 — verified as a real bug first (30-seed aggregate: 649 guard deaths vs. 539 rioter deaths under the old formula, guards dying more), then fixed by switching the per-day death-chance formula from a linear to a square-root size factor, which makes the casualty ratio depend only on `guard_lethality:rioter_lethality` (retuned to a clean 3:1) regardless of mob size. Post-fix aggregate: 381 guard deaths vs. 1,036 rioter deaths (ratio 0.368). See `docs/decisions.md`'s 2026-09-21 entry.]**
- I still do not understand why no one falls in love in these cities.
  **[triaged → Project_Vision §Romance's existing "not underfiring" explanation didn't land; flagged as needing revisit (rebalance or a more visible signal), 2026-09-21. Not fixed.]**
- Depending on how poor the town is, there should be continuous sickness events, not all of them too dangerous but people in a city get continuously sick, not just when there is a pandemic of some sort.
  **[triaged → superseded by the concrete "common ailments" version above (2026-09-21, later, refined twice) once the user spelled out what they meant (flu/diarrhea, contagious vs. not, poverty-scaled incidence and fatality) — same underlying request, now scoped precisely. See that entry, not the vaguer "Economy & poverty" mention this originally pointed to.]**
- What does grief shock affect?
  **[answered directly in chat, 2026-09-21 — no vision change needed, existing Project_Vision §Violence description already covers it accurately.]**
- Do we have a single-person property that represents their level of stress? Affected by poverty, by grief, sickness...?
  **[triaged → added as a new candidate personal property under Project_Vision §People, 2026-09-21. Not implemented — no consumer designed yet.]**