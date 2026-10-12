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
- **Step 3:** money in crime, with a payment log.
- **Merchant capital** is now split among the heirs: watch it over a long
  run.
- **The dashboard** has not been refreshed for this change.
- **Nothing is committed.**
