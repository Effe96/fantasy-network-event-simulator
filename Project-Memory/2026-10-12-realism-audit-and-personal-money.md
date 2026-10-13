# 2026-10-12: realism audit, physical town, personal money (step 1)

## What happened
- **Realism audit:** run on 5 years of Riverport, written up as
  `Project_Vision/07-realism-audit.md`. The user's answers are recorded in
  its "Decided" section.
- **Proposals:** the physical town (`08-physical-town.md`, waiting for the
  user's feedback) and personal money (`09-personal-money.md`). The user
  answered all of 09, including belongings: one value per kind, wear
  drives buying, built together with money.
- **Built step 1 of 09:**
  - personal purses, keyed `("p", id)`;
  - the household's shared pot, paid by family (lodgers pay their own
    share);
  - children's wages go to a parent until 16, and rich children get an
    allowance from 12;
  - class per family;
  - inheritance from what each person owns;
  - belongings that wear out.
- **Reasons:** in `docs/decisions.md` (2026-10-12).

## How the check went
The quick check is the scratchpad script `money_check.py`: 2 quiet years,
PyPy, seeds 1 and 2, before against after, about 1 minute a run. The first
attempts drifted:
- **A famine** in only one of the two runs. Famines are now off in the
  check.
- **Parents weren't heirs.**
- **Widows paid their children rent.** The widow now keeps the house she
  lives in.
- **Each person decided their spending alone**, so cash piled up with
  wives. A family now decides together.
- **Rich people's basket bought no clothes**, and the unsold goods were
  exported, bringing money in.
- **Buying back everything missing as a need** deepened hunger.
- **Hunger was counted per household:** shared houses were 63% of the
  hunger.
- **Lodgers were put out at once**, then **friends taken in after an
  eviction were treated as lodgers**, then **a married newcomer became the
  head of the house he lodged in.**

**The final check matches the old run:** money, cash and inequality within
5%, classes within about 8%, hunger the same or lower, homelessness lower.
Evictions are 22–42% higher, partly lodgers put out on their own.

## Open
- **09 §7 choices:** the user agreed with all of them.
- **Step 3 built** (uncommitted): bribes, payoffs, theft, mercenaries and
  assassins move money; children are out of it; a payment log. The check
  (step 1 against step 3, 2 years, 2 seeds) held. 09 §8 lists the choices;
  the user agreed with all of them.
- **Merchant capital** is now split among the heirs: watch it over a long
  run.
- **Committed:** step 1 (d7c798d); step 3, the fix and the speed pass (aa4f154). The 25-year report is at v22 (step 3).
- **Step 3's 25-year drift** was a mercenary hiring loop (fixed: a month's
  wage paid on hiring) and an heirless estate going to the commune. Holds
  over seeds 1 and 2 now.
- **Run times:** not slower since the TownShape integration (one run alone
  12 min after, 10 before). It depends on how many run at once, and one
  batch froze 12 minutes, likely the computer idling.
- **Speed pass** (uncommitted): four changes, identical results, about
  2.5% faster. Bigger gains would change the exact runs (see
  docs/decisions.md).

## 2026-10-13: the physical town (08), steps 1-3
- **Steps 1-2 committed (99f734e):** neighbours from TownShape's map both
  ways, every move to a real building (newlyweds together, people taken
  in, heirs, the homeless at rough spots, sim-placed buildings), a mover's
  district follows them. Couples apart: 15-18% to 2-3%. The user chose
  faster fading: all old neighbours drift apart at 0.7 a year (17,000
  acquaintances at 0.4, about 10,000-11,000 now). The dashboard was not
  refreshed, at the user's request.
- **Step 3 (08 2.1), uncommitted:** ties have a place, and ties across a
  quarantine border pause. Fixed disease reading the districts people
  started in, which raised first-year plague deaths (about 196 to 231 on
  average over 4 seeds). Reasons and numbers in docs/decisions.md.
- **Step 3 committed (b1b21d9).**
- **Step 4 (08 2.4), uncommitted:** bread and workshop goods from the
  nearest seller; a mover's shops, taverns and smithy re-picked by
  distance, the old ones' ties drifting apart at 0.7. 25 years held;
  evictions in seed 2 (1,001) to watch.
- **Next:** 08 2.5, quarantine closes part of the town.
