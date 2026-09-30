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

### 6. The long-run review and its first round of fixes (2026-09-27)

The user added `medieval_italian_cities_population.md` (research notes:
cities as demographic sinks fed by rural migration, Florence's 1427
Catasto) and asked why married share, population and faith behaved as
they did. Answers and a plan went into a new commentable review file,
`Project_Vision/02-long-run-findings.md`; the user's `> Feedback:` lines
set the round (details: `docs/decisions.md`, 2026-09-27):
- Found in TownShape's generator: ages follow `0.97^age` (57% children,
  20% under 5) and spouse sexes are drawn independently (52% of couples
  same-sex by accident). Built the adapted importer (ages to the sim's
  settled shape, couples to a 10% same-sex share), same-sex marriage,
  old-age deaths, a faith-fade offset, stress, a stress threshold for
  thieves plus thieves going straight, and everyday favors and scorn.
- User rules: no Florence marriage ages (keep 18+); allow same-sex
  marriage; adoption deferred; town should be a demographic sink that
  still grows, with singles and families moving in for wages and work and
  moving out only in extreme cases with money.
- Three 25-year runs compared on "Riverport Runs Compared"
  (https://claude.ai/artifact/Mk2Vwrhb9Rg9aLRznuVJUG): dip and marriage fall
  gone; deaths now exceed births with arrivals making growth; thieves 2-13
  (was 67-82), executions ~2 a year (was ~10). Still open: faith creeps
  (0.54-0.55 at year 25), and favors/scorn make warm ties drift faster
  (15.7%): the pull back must be sized per tie.
- The user is writing a document on medieval markets, for class mobility
  and the rich tripling.
- 2026-09-28: favors and scorn balanced per tie (neutral alone: warm share
  flat at 8.57-8.59% for 25 years) and faith's correction measured as it
  runs (0.49-0.50 for 25 years). Run D added to the comparison page. The
  remaining warm-tie rise is tie composition, for the tie-formation design.
- 2026-09-29: ties follow TownShape's rules as people come and go (newborn
  neighbours, shop ties at 18 and at import, arrivals' shop ties fixed,
  jobs always refilled); ties of the dead archived to a file (user). Runs
  E-G: warm ties flat (8.0 -> 8.2%), ties per resident 83.5 -> 75.6 (was
  -> 59.2), runs 24-30 min (were 35). Growth target kept: without it
  +1.6%/yr. Friends proposed, awaiting the user.

### 6b. Friends (2026-09-29)

Built as proposed: warm ties (0.3+ both ways) become friendships, cool
back below 0.1; ~1 meeting a person a year through someone they know makes
acquaintances, which fade if they never warm. Run H (25 years): friends
2.76 -> 2.52 a person, love weddings 63 -> 78, the rest unchanged. Two
bugs found: stale riot/religion caches when a living tie fades, and
arrivals inheriting the dead person's friends. Economy design written for
the user to comment: `Project_Vision/03-economy-design.md`.

### 6c. The economy (2026-09-29/30)

The user's market parameter book (`medieval_city_sim_parameters.md`) led to
`Project_Vision/03-economy-design.md`; the user commented, decided (florins,
small city, before the plague, all children inherit, merchants first,
jobs from workshops/putting-out/day labour/farms set by the importer) and
added rules on the way: unemployment without its own stress, titles to
siblings and nephews, five classes 15/50/25/9/1 (a very poor class and a
very rich 1%). Built as `economy.py` (details in `docs/decisions.md`,
2026-09-30). Calibration found four money leaks before money held steady.
Refreshed dashboards with the current model (25-year v3/v4, runs compared
v3, 50-year v2). The first 25-year run with the economy: class moves, the
rich stop growing, but wealth drains through heirless estates, households
shrink (3.6 -> 2.2 people) and poverty grows (design file section 5b).
Runs slowed to 42 min for 25 years: **the user made speed the next priority.**

### 6d. Speed work (2026-09-30/10-01) — 58 -> 45 s a year, then PyPy

Details in `docs/decisions.md` (2026-10-01). Profile of one year before:
violence ~25% (two daily scans of all ~80k ties), engine overhead ~29%,
romance ~11%, favors ~8%, riots ~8%, guards ~7%. Exact speed-ups (a seed-1
fingerprint of deaths, events, last summary and sampled feelings unchanged)
took CPU time from 58 to 45 s per simulated year (commit `8eb5c53`).
Timing lesson: measure CPU time on an idle machine, alternating versions.

PyPy 3.11 (7.3.20, via winget; `python` stays CPython 3.12): 27-29 s a
year in the benchmark, ~20 s a year in a full run; a whole 25-year run
takes ~8-10 min (42 min before the speed work). The user chose it for
long runs. Its results equal CPython 3.11's; 3.12 differs (the version's
float `sum`), so compare runs on one interpreter.

### 6e. Economy findings 1-2 (2026-10-01)

From `Project_Vision/03-economy-design.md` §5b. Baseline and fixed runs
are both PyPy, seed 1, 25 quiet years.

| | baseline | fixed | book |
|---|---|---|---|
| people per household, year 25 | 2.24 | 2.98 | ~4 (Florence 1427) |
| households' money, year 5 -> 25 | 92k -> 66k | 92k -> 81k (+14k commune) | steady |
| hungry households, year 25 | 136 | 81 | |
| very poor, year 25 | 23.4% | 16.5% | 15% at import |
| Gini, year 25 | 0.772 | 0.719 | ~0.70 |

What changed: heirless estates go to siblings, then nephews, else to the
commune, which keeps the land and spends its income in town; old widows
move in with a grown child and orphans with kin; single arrivals lodge
(with the household that lost someone, or one in the same building), one
in three arrives as a family (never a priest's replacement); a household
everyone has left hands its money on. Money of such emptied households
had been silently dropping out of every count.
The first try sold the commune's land for cash: 74k at year 25, since the
7% was lost. The main cause of shrinking households was the 724 arrivals,
each starting a household of one.
Two crashes found on the way, both newcomers registering while tied to a
newcomer not yet registered (romance, `_authority_ties`); the rule now:
a pair is recorded by whichever registers second. The mid-run newcomer
test covers it.
Then, per the user, the commune sells heirless land to whoever can pay
and its money pays the guards and public wages first (households' money
92k -> 90k; commune land 4.8k; few lots sell, as cash is scarce).
Left: very poor still rise from year 5 (10% ->
16.5%); thefts +13%. Slice 3 (debt, charity, beggars) is next for poverty.

### 6f. Slice 3 A-C (2026-10-01)

Plan and the user's decisions in `Project_Vision/03-economy-design.md`
("Slice 3 build plan"); reasons in `docs/decisions.md`. Built: hunger in
stress, debt (family, patrons, moneylenders), alms, the gabelle (2.5%) with
forced loans and public works, harvests and famine relief. Hungry
households at year 25 went 136 (first run) -> 51. Wrong turns: resentment
over unpaid debt had no end; a 6% gabelle made the commune hoard. Open:
executions ~5 a year, far above medieval norms; eviction waits for rent
(slice 5). Then D: beggars by household and hardship deaths (up to 49
beggars, 25 hardship deaths in 25 years; very poor 14.2% at year 25).
The user's four to-dos, done: executions 152 -> 10 (third conviction),
forgiveness by feeling, forced loans repaid in land, famine deaths ~1% of
the town in a famine year (forced-famine check). Next seen: riot deaths
~9-14 a year.

### 6g. Riots and justice for killers (2026-10-01)

Riots cut from ~1.7 a year to 1 in 25 years (daily rate 0.03 -> 0.0012):
the one riot, year 4, drew 78 people (~4% of the town), lasted two days,
killed 7 rioters and 1 guard, and broke against the guards. Killers are now
pursued (half caught; hanged or banished); a noble's assassin is a real
ex-soldier who can hang and name the noble. 44 executions in 25 years, 34
of them killers, follow from the user's own murder target: accepted by the
user as it is.

### 6h. Slice 4: organic migration (2026-10-01)

Growth target replaced: people come while work is easy to find and homes
have room; newcomers into trades bring capital; households under a year of
very high stress with money move out. 1,866 -> 2,185 in 25 years, flat
near the room limit from year 18. Wrong turns: unfilled day labour as the
pull (never happened), one strained month enough to leave (282 left).
The town now needs new houses to keep growing (TownShape).

### 7. Run times and scaling (measured 2026-09-29, for later)

The user asked how long runs take and how they scale; to be addressed in
the future ("towns becoming too slow"). Full model, epidemics off, 60
simulated days per town (`scratchpad/scaling.py`, rerun to re-measure):

| Town | Residents | Ties | Import | Per simulated year |
|---|---|---|---|---|
| small_town.db | 800 | 40,732 | 0.4 s | ~0.3 min |
| demo_riverport_town.db | 1,885 | 78,477 | 0.7 s | ~0.7 min (~1.2 min over a real 25-year run) |
| my_town.db | 5,035 | 434,256 | 4.0 s | ~3.6 min |
| test_town.db | 10,053 | 496,562 | 4.8 s | ~4.9 min |

- **Time follows ties, roughly linearly** (~0.1 s per 1,000 ties per 60
  days; ~1 min per simulated year per 100,000 ties), more than residents.
  Ties per resident depend on TownShape's density (neighbours = everyone
  in the 4 nearest buildings): ~80 in the reference town, ~170 in
  my_town, ~100 in test_town.
- Long runs cost ~1.5x a 60-day sample (year-end work, a growing town):
  reference town 25 years ~30 min, 50 years ~1 h; 5-10k residents
  25 years ~2-3 h, 50 years ~4-6 h.
- History: runs slowed from 19 to 35 min (25 years) when the ties of the
  dead piled up; retiring them to an archive brought them back to 24-30.
- Likely wins when this is tackled: the daily passes over every tie (the
  full scans some phenomena still do, favors' monthly pull back over all
  ties), and arranged marriages' scan of all singles per match (grows
  with the square of the population; not visible yet at 10k).

## Current repo state

Committed: population turnover in `fe14d97`, docs in `8154288`; the
2026-09-27 round in `3c706df`/`82f11c8`; the 2026-09-28/29 work (favors
per tie, faith measured, tie rules, archive, jobs refilled) in the
commits after them. Tests: 229 passing.
