# Population turnover (step 4, option B), child mortality, and the first 25- and 50-year runs

### Resumed after the computer shut down mid-session (the previous session had already picked option B and nearly finished it, uncommitted). Finished and calibrated sim-side population turnover, recorded several new user rules and ideas in Project_Vision, and ran the first multi-decade simulation with a dedicated dashboard. Spans 2026-09-24 and 2026-09-25.

## What this session did

### 1. Population turnover, sim-side (option B)

Picked up uncommitted work: babies are real residents (mother's SES,
household, home; parent and sibling ties), `PopulationPhenomenon` ages
everyone yearly and refills the places dead adults leave, families
arrange marriages for single adults, widow(er)s can remarry, priests stay
celibate, children under 12 never turn thief. All tests passed on resume.

User rules added along the way (all in Project_Vision and
`docs/decisions.md`'s 2026-09-24 entry):
- **Nobles are never replaced by outsiders.** The eldest living child in
  the household inherits the title (even a minor); otherwise it lapses.
  TownShape flags only the head of a noble family as `is_noble`.
- **A town at equilibrium grows slowly**, it doesn't hold a fixed size.
  Ordinary arrivals fill up to a target growing ~0.5% a year
  (`PopulationPhenomenon.annual_growth`).
- The user pointed out that topics to discuss and rules belong in
  Project_Vision / Project-Memory, not `docs/plans.md` or my own memory.
  The running tally now lives in Project_Vision, "To discuss with the
  user (running tally)".

### 2. Calibration: child mortality, then fewer arranged marriages

Quiet-town drift check (seed 1, 10 years) showed population +1.2%/yr,
overshooting: babies almost never died and births outran deaths.
- **Child mortality (user chose option A over lowering births):** sick
  children are likelier to die of flu, diarrhea and the epidemic
  (`child_fatality_factor`: infants x20, ages 1-4 x3; first try x8/x2 gave
  only ~9% infant deaths).
- **Births then climbed to 57-70 per 1,000** (medieval ~35-45): arranged
  marriages at ~50% of singles a year turned every single adult into a
  young fertile couple. **User chose A: fewer arranged marriages**
  (`ARRANGED_MATCH_RATE` 0.001 -> 0.00017, ~12% of singles a year; median
  wedding age 25).

### 3. The 25-year run (seed 1, epidemics off, every mechanic)

Dashboard: "Riverport, 25 Quiet Years",
https://claude.ai/artifact/2kmbLQcyGg34eG1bcDSkqC. Findings:
- **Settled:** population 1,889 -> 2,140 (+0.50%/yr, on target; dips in
  years 1-4, climbs 1-2%/yr in 7-17, then rides the target). Married share
  of adults falls from 81% at import (few adults, many children) to ~50%
  by year 6, then holds at 51-56%. Religiousness climbs 0.50 -> 0.58 by
  year 12, then flat (the known creep is bounded). Hatred flat at
  3.6-4.0% of ties; guards 28-31, clergy 3; 6 nobles died, all 6 titles
  passed to a child. ~1.6 riots, ~4.1 murders, ~10 executions a year;
  one coup, failed.
- **Too high:** 50-65% of babies born in years 1-20 died by the end
  (norm 30-50%); births 41 and deaths 49 per 1,000, at the historical top
  and above it. Suggested fix: infant multiplier 20 -> ~12.
- **Watch:** arrivals nearly stop once the town reaches its target
  (1-21 a year in years 14-22); 497 unfilled vacancies pile up by year 25
  and should probably expire.
- **Drifts:** thieves 16 -> 67, rising steadily from year 10 (likely more
  poor youths reaching 12). Warm ties 8.5% -> 13.1% and mean feeling
  0.020 -> 0.065, accelerating (likely every baby adding warm family ties).

### 4. New ideas recorded in Project_Vision (user, 2026-09-25)

Clergy size follows town religiousness; garrison size follows town
aggression; organic migration (whole families, newcomers with their own
trade who look for work, create jobs or open shops; people moving out
when stressed and able to afford it). Discussion tally: homeowners, the
merchant class, merchants as landlords, organic migration, what causes an
epidemic, new houses being built (mostly TownShape).

### 5. The 50-year run

On request, the same seed run to 50 years (deterministic: the first 25
years matched the 25-year run exactly, year by year). Dashboard
"Riverport, 50 Years": https://claude.ai/artifact/Jt2wLKYAbNCQ5f3wuHsD6C
(adds a years 1-25 vs 26-50 table, a year-25 marker, a year-25 pyramid,
median wedding age). Years 1-25 vs 26-50:
- **Still settled:** growth +0.50%/yr in both halves (2,140 -> 2,425);
  from ~year 40 births alone keep the town just above target, arrivals
  stop. Married share 55% -> 51% average; median wedding age 27 in both.
  Religiousness 0.573-0.585. Guards 27-31, clergy 2-3; 8 titles
  inherited over 50 years, one lapsed (~year 30, 13 nobles left); 2 coups,
  both failed.
- **Now in range:** births 41 -> 38 and deaths 49 -> 40 per 1,000; deaths
  under 5 44 -> 36 per 100 births. The first half's excess was the
  imported town's young age structure, so the infant-multiplier cut
  suggested after 25 years may not be needed.
- **Order calmer:** riots 1.6 -> 1.0, murders 4.1 -> 2.1, executions ~10 a
  year in both.
- **Worse:** warm ties 13.1% -> 21.4% (mean feeling 0.065 -> 0.156),
  accelerating; hatred 3.7% -> 3.2%. Thieves 67 -> 135-149 (5.6% of town).
- **New:** the rich triple, 111 -> 143 -> 332 (6% -> 14%): poor die of
  disease 4x as often, babies take the mother's class, no class mobility.
- **Watch:** vacancy queue 497 -> 1,249, never used once at target.

Correction: the first 25-year dashboard verdict said ~1.6 murders a year;
that was the riot rate. Murders were 4.1 a year. Fixed on the page (v2).

## Current repo state

**Uncommitted** on top of `750fb52`: all of the above (code, tests, docs).
Tests: 209 passing.
