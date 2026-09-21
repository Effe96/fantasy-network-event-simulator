# Plans — queued work

> Session-continuation checklist: what's next and in what order, based on
> what we've actually discussed and decided. Distinct from
> `Project_Vision/01-network-simulation.md` (the full topic-organized
> feature backlog — still the source of truth for *scope* on each item
> below) and `docs/decisions.md` (*why* past choices were made). This file
> is *what's queued and in what order*, kept current as work lands or the
> plan changes. Last updated 2026-09-21 (thief plateau + riot lethality
> fix landed, then assassination refinement — Criminals' last remaining
> item is group violence, below).

## Resume checklist

1. `py -3 tests/run_all.py` — should print `ALL OK`. If not, something's
   wrong before any new work starts.
2. Read every `open` entry in `docs/feedback.md` — that's the inbox for
   the user's own notes on simulation behavior (not code). Triage each
   into a fix, a calibration tweak, or a new item below, then flip its
   status once handled.
3. Skim `docs/decisions.md` (newest entries first) for anything that
   might trip up new work.
4. The results dashboard (Artifact) needs refreshing as of this session
   (thief plateau + riot lethality fix landed after the last refresh) —
   see the visualize-every-change convention now in memory.

## Immediate next: Criminals

Per the agreed order (Guards → **Criminals** → Priests → Nobles →
Quarantine → Taxes → town-wide dials). Scope from
`Project_Vision/01-network-simulation.md`'s Criminals section:

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
- **Group violence**: enough people sharing high animosity toward the
  same target, with enough affinity among themselves, can attempt a
  killing together with a much higher success chance than any one alone —
  and if enough band together, this escalates directly into a riot.
  **This is the bottom-up riot trigger** flagged as "not yet built" in
  the design doc §12 — it should plug into the *existing*
  `RiotPhenomenon._active_riot` state machine (start one directly with a
  pre-formed participant list) rather than inventing a second riot
  concept. Worth designing this connection point deliberately once
  Criminals' group-violence mechanic exists, rather than bolting it on
  after the fact.

## After that: Priests

- Religious town → broad affinity boost from most residents; a small,
  deliberately-chosen set of heretics/skeptics get an animosity boost
  instead. (`religiousness`/`skepticism` traits already exist on `Node`,
  unconsumed — this is their first real use.)
- Corruption: priests accepting payment for services. Likely reuses the
  bribery *pattern* `GuardPhenomenon` established (edge-level, scaled by
  the payer's traits and the priest's own integrity) rather than
  reinventing it — good candidate for finally building the generic
  **favor** event type (documented in the design doc §"Event taxonomy",
  not yet implemented) if two phenomena end up wanting the same shape of
  mechanic.
- Priests as disease-curers: a bad outbreak raises animosity toward them
  (blame). Needs a way to read Contagion's death toll — check whether
  that's readable from the engine's daily summaries/state, or whether it
  needs the same kind of cross-phenomenon link Guards' patron-protection
  was blocked on.
- Quarantine authority (see Quarantine, below — cross-cutting with
  Nobles).

## After that: Nobles

- Noble/poor animosity skewed toward resentment on the poor side from the
  start, rising further with riots/unrest (especially from high taxes).
  Note: Riots' *risk* mechanic is already implemented and noble-aware
  (§12 of the design doc); this item is specifically about the *starting
  skew* and *tax-driven growth*, which aren't built yet — noble/civilian
  edges currently get the same neutral synthesis as everyone else.
- Mercenary hiring, scaling with animosity directed at a noble, with a
  cap — lowers an attacker's (or a riot's?) success chance against them.
  Consider whether this should feed into `RiotPhenomenon`'s
  `noble_lethality`/hatred-based targeting as a per-noble modifier.
- Nobles hire assassins rather than committing manslaughter themselves —
  ties into Criminals' assassination mechanic above.
- Coup mechanic: rising taxes → noble animosity toward the governor →
  mercenaries hired to move against them. **Needs a governor concept**,
  which doesn't exist yet — decide whether that's a real new `Node`
  attribute/role, or a derived "most powerful noble" convention, before
  building the coup logic on top of it.
- Bribing priests to improve reputation with poor residents, scaled by
  each individual's own `religiousness`.

## Quarantine (cross-cutting: Priests + Nobles)

Either priests or nobles can institute one for a dangerous/contagious
disease: raises death rate in the affected area, lowers it elsewhere, and
raises animosity toward whichever class made the call. Depends on both
Priests and Nobles existing first (above) — don't start this before them.

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
