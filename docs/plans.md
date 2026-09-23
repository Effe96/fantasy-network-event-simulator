# Plans — queued work

> Session-continuation checklist: what's next and in what order, based on
> what we've actually discussed and decided. Distinct from
> `Project_Vision/01-network-simulation.md` (the full topic-organized
> feature backlog — still the source of truth for *scope* on each item
> below) and `docs/decisions.md` (*why* past choices were made). This file
> is *what's queued and in what order*, kept current as work lands or the
> plan changes. Last updated 2026-09-23 (Coup mechanic landed: all
> four Nobles items are done. Death record (`graph.deaths`) added, which
> unblocked Priests' disease-curer blame, now also done. Quarantine landed
> the same day, with a slower epidemic (base_rate 0.5 -> 0.06). Next up
> per the build order: population turnover (for multi-year runs), then
> Taxes, then town-wide dials.).

## Resume checklist

1. `py -3 tests/run_all.py` — should print `ALL OK`. If not, something's
   wrong before any new work starts.
2. Read every `open` entry in `docs/feedback.md` — that's the inbox for
   the user's own notes on simulation behavior (not code). Triage each
   into a fix, a calibration tweak, or a new item below, then flip its
   status once handled.
3. Skim `docs/decisions.md` (newest entries first) for anything that
   might trip up new work.
4. Check whether the results dashboard (Artifact) is current against the
   latest reference-town run before assuming it's stale or trusting a
   note here about it — see the visualize-every-change convention in
   memory, and verify by reading the live artifact rather than a
   possibly-outdated note like this one.

## Criminals — done (2026-09-21)

Per the agreed order (Guards → **Criminals** → Priests → Nobles →
Quarantine → Taxes → town-wide dials). All four scoped items from
`Project_Vision/01-network-simulation.md`'s Criminals section have
landed. Scope recap:

- ~~**Thief as an occupation.**~~ **Done (2026-09-21).** `TheftPhenomenon`
  in `phenomena.py`: a sticky per-resident `is_thief` flag rolled once in
  `end_of_day`, scaled by poverty (`THIEF_SES_FACTOR`), nobles excluded.
  Decision recorded in `docs/decisions.md`'s 2026-09-21 entry.
- ~~**Theft as a new event type**~~ **Done (2026-09-21).** Same
  `TheftPhenomenon`: fires on an edge with exactly one thief endpoint,
  scaled by the thief's cunning and the victim's wealth (reuses
  `BRIBE_WEALTH_FACTOR`). A discovery roll on each theft drops the
  victim's valence toward the thief and, if the thief has an edge to any
  guard, that guard's valence too — arrest/patron-protection itself stays
  deferred (needs the cross-phenomenon link noted below). Covered by
  `tests/test_theft.py`; wired into `demo.py`.
- ~~**Population plateau (arrests/deterrence)**~~ **Done (2026-09-21,
  user feedback) — took two tries.** Caught thieves can now be arrested
  (loses `is_thief`) or executed (low-loyalty towns, corruption proxy);
  every removal raises a decaying deterrence level that suppresses the
  become-a-thief roll. First version gated arrest on the thief having a
  guard *neighbor* — a 1-year trajectory looked flat (77→78) but a
  3-year check (prompted by "are you sure it plateaus?") showed it
  wasn't converging at all (94→221, no deceleration): only ~10% of
  catches led to a removal given how few guards there are relative to
  the town. Corrected to a flat, town-wide arrest chance (43% of
  catches now). A 2-year run with the fix shows real fluctuation,
  including genuine population declines, for the first time — the exact
  long-run equilibrium level isn't fully pinned down yet. Poverty-
  severity and a real corruption dial (vs. reusing guard loyalty) still
  deferred — see `Project_Vision`'s Economy & poverty section.
  `docs/decisions.md`'s two 2026-09-21 entries (the mistake and the
  correction are both recorded).
- ~~**Assassination refinement**~~ **Done (2026-09-21).** A violent
  attempt now has a success chance (`min(1.0, success_base_rate *
  victim_vulnerability / attacker_vulnerability)`, reusing
  `SES_VULNERABILITY` for both sides) instead of an automatic kill.
  Same-class violence stays close to the old behavior; poor-vs-rich
  succeeds rarely (~21%), rich-vs-poor almost always. A failed attempt
  never kills — the surviving victim's own valence toward the culprit
  drops sharply instead, no `grief_shock` (nobody died). Verified on a
  real run: 24 failed attempts / 109 total. `docs/decisions.md`'s
  2026-09-21 entry.
- ~~**Group violence**~~ **Done (2026-09-21).** `ViolencePhenomenon`
  gained a town-wide `end_of_day` check: haters of the same target who
  are also mutually tied to each other band together (union-find on
  affinity), with a much higher success chance than any solo attempt
  (`sqrt(band size)` boost). A large enough band skips the kill roll and
  becomes a riot directly via a new `RiotPhenomenon._begin_riot`
  (factored out of `_start_riot`'s own tail) — the bottom-up riot
  trigger plugged into the *existing* riot state machine, exactly as
  planned, not a second riot concept. A first version (looser
  thresholds, no "does this actually happen today" roll) produced 345
  riots in a year before being caught by the same real-run-verification
  habit that caught the thief-plateau and riot-lethality issues; fixed
  with stricter thresholds plus an explicit action-rate gate. See
  `docs/decisions.md`'s 2026-09-21 entry.

## Priests — in progress (started 2026-09-22)

- ~~**Religious town → broad affinity boost from most residents; a small,
  deliberately-chosen set of heretics/skeptics get an animosity boost
  instead.**~~ **Done (2026-09-22).** `ReligionPhenomenon`:
  `religiousness`/`skepticism` traits (already on `Node`, unconsumed
  until now) drive two per-edge events between a civilian and a priest —
  `devotion` (most civilians, scaled by their own religiousness, raises
  their own outgoing valence) and `friction` (a `skepticism`-threshold
  minority, ~7.7% of civilians, lowers it instead). Sticky classification
  decided once in `init_state`, same shape `TheftPhenomenon`'s
  `is_thief` flag uses. Verified on a real run: 98 devotions / 11
  frictions in a year, no runaway. `docs/decisions.md`'s 2026-09-22
  entry.
- ~~**Corruption: priests accepting payment for services.**~~ **Done
  (2026-09-22).** Reuses bribery's exact shape on the same civilian-priest
  edge devotion/friction already use — a `corruption` event, scaled by
  the civilian's own cunning/wealth and restrained by the priest's own
  loyalty (no new "integrity" trait needed). Shares a weighted roll with
  devotion/friction rather than a second independent check on the same
  edge. Verified on a real run: 67 devotions / 7 frictions / 4
  corruptions, no runaway. `docs/decisions.md`'s 2026-09-22 entry.
- ~~Priests as disease-curers: a bad outbreak raises animosity toward
  them (blame).~~ **Done 2026-09-23**, reading `graph.deaths`. Guards'
  patron-protection can read the same record.
- ~~Quarantine authority~~ **Done 2026-09-23** (see Quarantine, below).

## Nobles — in progress (started 2026-09-22)

- ~~**Noble/poor animosity skewed toward resentment on the poor side from
  the start**~~ **Done (2026-09-22).** `graph.py`'s `_apply_noble_poor_skew`,
  called from both edge-loading paths (`_load_relationships` and
  `_load_shopkeeper_customer`): where one edge endpoint is a noble and
  the other a poor resident, the poor party's own outgoing valence gets
  a fixed extra negative shift (0.1) on top of the plain synthesis draw
  — additive, real variance survives. Verified on the reference town:
  5,101 noble-poor edges, 61.3% now net hostile from the poor side (vs.
  a neutral ~50/50 baseline). The shift shipped at 0.25 and was corrected
  to 0.1 the same day after user feedback — 0.25 had never been checked
  against `RiotPhenomenon`'s `unrest_threshold`, and it raised the town's
  civ-authority hostility average 0.251→0.332. **Don't credit this shift
  for the town's riot count**: real `--seed 1..10` runs of the full
  engine average ~8.4 riots/year regardless, and 80% of those are group
  violence escalating into a riot, not organic Nobles-driven unrest (only
  ~1.7/year is organic). See `docs/decisions.md`'s two 2026-09-22
  entries (the shift correction, and the later seed/outlier
  investigation that superseded an earlier flawed 20-seed sweep).
  **Tax-driven growth is still deferred** —
  needs Taxes, which doesn't exist yet (see Taxes, below). `docs/decisions.md`'s
  2026-09-22 entry.
- ~~**Mercenary hiring, scaling with animosity directed at a noble, with
  a cap — lowers an attacker's success chance against them.**~~ **Done
  (2026-09-22).** Also covers priests, per the vision doc. New
  `Node.is_ex_soldier` trait (`graph.py`, civilians only, ~8% synthetic
  rate — no real TownShape data to derive this from, checked
  `town_db/military.py` and the reference town's own `military_service`
  table first: it only tracks *current* guards). `ViolencePhenomenon`'s
  `_check_mercenary_hiring` (`end_of_day`): a noble/priest with more
  hostile neighbors than `mercenary_min_enemies` rolls to hire an
  available `is_ex_soldier` resident as protection, hire chance scaling
  with how far past the threshold they are (same shape `RiotPhenomenon`'s
  own trigger uses), capped at `mercenary_cap`. **Not limited to a direct
  tie** (2026-09-22, user feedback) — `_mercenary_candidates` tries direct
  neighbors first and only widens to a friend-of-a-friend (2 hops) if none
  is available, still never inventing a new edge to a stranger. Each
  living mercenary multiplies an attacker's success chance by
  `mercenary_protection_factor` in `apply_effect`. Verified on the
  reference town (seed 5): 26 mercenaries hired across the year, no
  runaway. **Scoped to solo
  violence only for this slice** — riot lethality (`RiotPhenomenon`'s
  `noble_lethality`) doesn't see this protection yet; a mob attack on a
  protected noble/priest is unaffected. Revisit if that reads as an
  inconsistency once Quarantine/riots get more attention.
- ~~**Nobles hire assassins rather than committing manslaughter
  themselves**~~ **Done (2026-09-22).** `ViolencePhenomenon.apply_effect`:
  when `_pick_aggressor` picks a noble as culprit, the success-chance
  formula is untouched (their wealth already buys a skilled assassin via
  the existing SES-vulnerability math), but `noble_hired_assassin_shock_factor`
  (0.5) halves both `grief_shock` (neighbors' reaction if it succeeds) and
  `discovery_shock` (the victim's reaction if it fails) — a hired hand
  insulates the noble from the personal fallout a witnessed act would
  carry, without zeroing it. New `hired_assassinations` counter in
  `summarize`/`demo.py`. Verified on the reference town (seed 5): 4 hired
  assassinations in a year, out of 111 total violence deaths.
- ~~**Coup mechanic: rising taxes → noble animosity toward the governor →
  mercenaries hired to move against them.**~~ **Done 2026-09-23.**
  `graph.governor_id` (new, `graph.py`) — no real TownShape data models a
  governor, so it's a single town-wide fact (like `town_aggression`), not
  a `Node` field: the "most powerful noble" convention, lazily
  picked/re-picked (succession included) by `ViolencePhenomenon._ensure_governor`
  as the highest-degree living noble the first time it's needed, rather
  than duplicating selection logic at import time too. 36 of 39 other
  nobles already share a direct edge with that pick on the reference
  town. `_check_coup`/`_advance_coup`: one noble at a time
  (`_active_coup`, same "one active event" shape `RiotPhenomenon` uses)
  can plot against the governor once animosity over an *existing* edge
  crosses `coup_animosity_threshold`; hires coup mercenaries from the
  same pool/rules `_mercenary_candidates` already provides, each hire
  raising `suspicion`, which is *also* each day's chance of being
  discovered outright before the plot is ready. Reaching
  `coup_mercenary_cap` triggers the attempt, reusing the exact same
  `mercenary_protection_factor` defense formula against the governor's
  own hired protection. **Rising taxes as the animosity driver is
  deferred** — Taxes doesn't exist yet, same deferral Nobles' resentment
  skew already made. 10 new tests, full suite green. `docs/decisions.md`'s
  2026-09-22 entry.
- Bribing priests to improve reputation with poor residents, scaled by
  each individual's own `religiousness`.

## Quarantine (cross-cutting: Priests + Nobles) — done (2026-09-23)

`QuarantinePhenomenon` seals TownShape home districts on plague deaths
(2 in 14 days, 4 in poor districts); nobles take charge once one of their
own dies. Sealed boundaries leak at 2%; inside, people keep indoors
(non-household ties at 20%) and the sick die at 1.25×; residents inside
resent the sealing class. Re-tuned the same day on a regenerated reference
town (1,889 residents, nobles in the rich district) with epidemic tiers
from `medieval_diseases.md` (tier 3 default): quarantine cuts tier-3
infections 65% -> 48% and plague deaths 147 -> 116 a year. Required slowing the epidemic
(base_rate 0.5 -> 0.06). Full reasoning, including three revised first
guesses: `docs/decisions.md`'s 2026-09-23 quarantine entry. Open: check
quarantine's knock-on effect on mercenary hiring (same 0.7 hatred cutoff).

## Next up (queued 2026-09-23, after taming the over-violent town)

In the user's order of mention:
1. **Occasional epidemics**: stop seeding a tier-3 outbreak on day 1 of
   every run; a yearly chance of an outbreak instead. ~104 of the ~167
   yearly deaths are this. Overlaps with population turnover item 3.
2. **Smaller, rarer riots**: the organic riot trigger (average civilian
   hostility toward guards and nobles) still starts ~0.8 riots a year
   of 70-109 people (4-6% of the town).
3. **Coup redesign**: bribing guards to stand aside, recruiting allied
   nobles, a plotter's force that has to outweigh the governor's.
4. **Executions by aggression and crime severity** (user): ~11 thieves
   executed a year is high; the rate should depend on the town's
   aggression and on how serious the crime was, not a flat chance.

## Population turnover — needed before multi-year runs (added 2026-09-23)

Asked how long a 20-year run would take: runtime is fine (~3 min per
simulated year, ~1 hour for 20), but the town wouldn't survive it. About
300-380 residents die a year on the reference town and none are ever
added (births are log-only), so it would be nearly empty within ~5
years, and every crowd-driven mechanic (riots, group violence,
quarantine) would fade with it. Scope, per `Project_Vision`'s new "Long
runs: population turnover" section:

1. **Births as real residents**: new `Node`s with family-correlated
   traits, family ties and the parents' home district. Blocker first:
   every phenomenon's per-resident state is fixed on day 0, so the
   engine needs a way to add a resident mid-run to all of them.
2. **Replacement for the dead**: arrivals from outside, succession for
   clergy and guards, children growing into adults and jobs.
3. **Recurring epidemics**: the epidemic currently starts once, from one
   patient zero on day 1; over many years it needs a chance to return.

Comes before Taxes: taxes and coups really play out over years.

## Taxes

External stressor (disease, war) → governing body raises taxes → animosity
toward whoever governs. Overlaps with Nobles' coup mechanic (same lever,
triggered from a different direction) and needs the same governor concept
that mechanic needs.

## Town-wide dials: religiosity & loyalty as emergent aggregates

Per the vision doc's own framing, these should likely be *aggregates of
individual traits* (a town-wide religiosity number derived from residents'
own `religiousness`) rather than separately hand-set dials, with real
feedback loops (a disease hitting a religious town raises animosity toward
priests, which itself should lower the town's aggregate religiosity, so a
*second* disease event moves faster than the first did). This needs
Priests to exist first to have something for the loop to act on. Also
still open: what other town-wide parameters make sense (corruption,
wealth-inequality/Gini skew, justice fairness) — see the design doc §13's
open note on a **corruption** dial specifically, which bribery already
needs for a real high/low-corruption contrast.

## Known deferred items to fold in opportunistically

Not a separate project phase — fold each into whichever feature above
naturally needs it, rather than doing them standalone:

- ~~**Riot guard:rioter lethality ratio**~~ **Fixed (2026-09-21).** The
  old linear size-ratio formula let mob size swamp the lethality
  constants (guards were dying *more* than rioters on a real 30-seed
  aggregate: 649 vs. 539). Switched to a sqrt size factor, which makes
  the casualty ratio equal to `guard_lethality:rioter_lethality`
  regardless of mob size; retuned to a clean 3:1 (0.2/0.6). Same
  aggregate after the fix: 381 guard deaths vs. 1,036 rioter deaths
  (ratio 0.368, close to the 0.333 target). See `docs/decisions.md`'s
  2026-09-21 entry.
- **Births still don't create real `Node`s.** Needs a
  `Phenomenon.default_state(resident_id)`-style protocol addition so
  every phenomenon can produce sane starting state for a resident who
  joined after day 0. Blocks real multi-generational family-tie
  derivation too (see design doc §11, §16).
- **`favor`/`wrongdoing` generic event types** are documented (design doc
  event-taxonomy section) but not implemented as their own thing — watch
  for the second phenomenon that wants "raise affinity"/"raise animosity"
  in the same shape bribery already uses, and generalize then, not before.
- **Guards': arrest behavior, patron protection, built-in noble/poor
  skew** — all still deferred, per the design doc §13's scoping note.
  Patron protection specifically needs a cross-phenomenon event link
  (Guards observing what Violence produced) that doesn't exist anywhere
  yet — worth deciding as a general capability once *any* second
  phenomenon needs to react to a different phenomenon's events, rather
  than building a one-off link just for this.
- **Cross-class romance's differential growth rate** (affinity grows
  slowly, animosity grows fast, across class lines specifically) — not
  implemented; current romance/violence dynamics use the same rate
  regardless of class.
- **Riot resolution-phase valence shift** (catharsis vs. crackdown
  backlash after a riot ends) — deliberately left out since the source
  material doesn't commit to a direction; needs a decision, not just
  implementation, before it's picked up.
