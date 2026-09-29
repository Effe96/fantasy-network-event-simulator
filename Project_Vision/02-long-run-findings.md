# Long-Run Findings and Plan

### What the first 25- and 50-year runs showed, why, and what to do about each finding. Written 2026-09-27 for the user to read and comment on; the next session reads the comments back.

**How to comment:** add a line starting `> Feedback:` right under any
section or numbered item, the same way as in
[`01-network-simulation.md`](01-network-simulation.md). Agreeing,
disagreeing, a new idea, or "discuss first" are all useful. Items without
feedback stay at their current status.

**Sources:**
- The runs: seed 1, epidemics off, every mechanic on, on
  `demo_riverport_town.db` (1,889 residents). Dashboards:
  [Riverport, 25 Quiet Years](https://claude.ai/artifact/2kmbLQcyGg34eG1bcDSkqC)
  and [Riverport, 50 Years](https://claude.ai/artifact/Jt2wLKYAbNCQ5f3wuHsD6C).
  The first 25 years of the 50-year run are identical to the 25-year run.
- An 8-year diagnostic run (same seed) recording who is married by age
  and sex, and how many couples can still have children.
- [`../medieval_italian_cities_population.md`](../medieval_italian_cities_population.md),
  the user's research notes on medieval Italian cities, used here as the
  historical benchmark.

---

## Part 1. The user's three questions

### 1.1 Why does the share of married adults fall to about 50% and then flatten?

TownShape builds the town with almost everyone married young. The sim
then marries people much more slowly.

| Married, by age | At import | After 8 years | Florence, 1427 Catasto |
|---|---|---|---|
| Women 18-24 | 85% | 26% | most married by ~18 |
| Men 18-24 | 80% | 25% | few: men married at ~27 |
| Women 25-34 | 76% | 58% | nearly all |
| Men 25-34 | 87% | 53% | most |

- **The fall:** 421 children aged 10-17 come of age in the first 8
  years, all of them single. Arranged marriages pair off about 12% of
  single adults a year, at the same pace for men and women, so the new
  adults stay single for years. Meanwhile the heavily married imported
  adults age and die.
- **The flattening:** once the number of weddings a year matches the
  number of people coming of age or being widowed, the share stops
  moving, at about 50%.
- **A side effect:** nobody over 45 is ever matched again, so single and
  widowed people over 45 pile up: 37 at import, 88 by year 8.

**Against the history:** in Florence marriage was near-universal (only
0.45% of men and 0.50% of women never married) and differed by sex:
women at about 18, men at about 27. The sim treats both sexes the same
and marries everyone at about 27. See item 2.1.
> Feedback: We do not need to exactly match the marriage rate and ages to what was true in medieval Florence, because I do not think it works well with a Fantasy town. Is there another way not to have this dip at the beginning? A different starting state maybe? 

### 1.2 Why does the population dip first, then grow steadily?

TownShape's town has a baby-boom shape: **370 children under 5 (20% of
the town)**, 421 aged 10-17, and only 810 adults (43%).

- **The dip:** those 370 small children die at medieval child-mortality
  rates (68 deaths under 5 in year 1 alone). Arrivals only replace dead
  *adults*, so none of these deaths is made up. Births meanwhile fall
  to about 45 a year, well below the ~74 a year that TownShape's age
  structure implies, because couples able to have children drop from
  269 to 220 as young people now marry slowly.
- **The growth:** from about year 5 the large 10-17 group has grown up
  and started marrying, births rise, and the town climbs to its growth
  target (+0.5% a year). From then on it follows the target line, which
  is why the growth looks straight.

So the dip is the town adjusting from TownShape's assumptions to the
sim's own rules. Fixing marriage (item 2.1) should shrink it a lot. What
is left is item 3.4.

### 1.3 Why does religiousness climb to about 0.58 and then flatten?

Two forces pull against each other:
- **Up:** each recovery from flu or diarrhea makes a civilian a little
  more religious (gratitude). About 2,400 recoveries a year push the
  average up by roughly 0.015 a year.
- **Down:** faith drifts back 10% a year toward each person's starting
  level, and the further it has risen, the harder that pull.

It levels off where the two cancel, about 0.08 above the imported level.
That is a real balance point, but in the wrong place: by the equilibrium
principle the imported town should already be at balance and not move
at all. See item 2.2.

---

## Part 2. Fixes I can make directly

Status for each: **Proposed** until the user agrees.

### 2.1 Marriage by sex, following Florence — Proposed

Explains the married-share curve and most of the population dip.

- Families marry off **daughters** from about 16, most by 18-20.
- Husbands are **mostly in their mid-20s to 30s**, so men marry around
  27 on average.
- **Nearly everyone marries.** No permanent pool of never-married adults.
- **Widowers remarry**, with no age cap for men. **Widows remarry less
  as they age**, calibrated to Florence's share of women widowed: 3% at
  30, 10% at 40, 24% at 50.
- Check: a 25-year run should show the married share holding near the
  imported level and a much smaller early dip.

> **Update 2026-09-27 — Addressed as the user asked:** marriage stays 18+
> (no Florence ages), same-sex marriage added (`same_sex_share`, 10%),
> adoption deferred. The dip is fixed by the adapted importer (3.4).
> See `docs/decisions.md`, 2026-09-27.

> Feedback: We definitely DO NOT WANT the to apply the rules for marriage for realistic medieval cities regarding the age at which girls used to get married. It was messed up. Keep marriage age from 18 onwards. Still allow same same sex marriage. We should look into adopting and how it could work. 

### 2.2 Religiousness starts at its balance point — Proposed

Make the imported level the balance point, so gratitude from recoveries
and the yearly fade cancel there instead of 0.08 higher. The simplest
way: the fade pulls toward a point just below each person's starting
level, set so the average push from recoveries brings them back to it.

> **Update 2026-09-27 — Partly addressed:** the town starts where it was
> (0.50); the fade now aims 0.08 below each start. Creep halved (0.58 ->
> 0.54 at year 25) but still rising: the correction needs to be bigger.
> **Update 2026-09-28 — Addressed:** the correction is now measured as the
> town runs; religiousness holds at 0.49-0.50 for 25 years.

> Feedback: So you would start from a higher average religious point? Let's try, if that is what you are thinking. 

### 2.3 Unfilled places expire — Proposed

1,249 places left by dead adults were still waiting in the queue at year
50, because arrivals only fill them while the town is below target. A
place that stays unfilled for a while (say a year) should simply lapse.

> **Update 2026-09-27 — Folded into 3.1:** a vacancy is the whole place a
> dead adult leaves (home, job, class, ties). With organic migration homes
> and jobs are tracked separately, and empty homes draw newcomers.

> Feedback: Are you referring to homes? Empty homes should partly just make it easier from foreigners to move in. And what would lapse mean? Let's delve a bit more into this during our session. 

### 2.4 Why thieves keep multiplying — to measure first

Thieves go from 0.8% of the town at the end of year 1 to 5.6% at year
50, still rising. The likely cause is more young poor residents reaching
12, the minimum age for thieving, but I'd measure before changing
anything: who becomes a thief, at what age, and why so few stop.

> **Update 2026-09-27 — Addressed:** measured first. Thieves only stopped by
> being caught while stealing, so thieves with few victims piled up. Now
> becoming a thief needs stress above 0.6 (poverty plus a recent loss or
> illness) and thieves go straight on their own: 2-13 thieves instead of
> 67-82 by year 25.

> Feedback: I think that is smart. Let's also increase the level of stress a person has to go through to decide to become a thief. What parameter does becoming a thief depend on? 

---

## Part 3. To design together

These need decisions from the user, not just calibration. Each is also
on the running discussion list in `01-network-simulation.md`.

### 3.1 Organic migration — Open

The research notes are direct about this:
- Medieval cities **could not sustain themselves**: urban deaths
  exceeded births, and growth came from people moving in from the
  surrounding countryside (*inurbamento*). Florence grew "above all" by
  immigration from its contado.
- The birth rate was about **50 per 1,000**, with life expectancy at birth
  about 20 years and high adult mortality.
- Most migrants were poor peasants and landless labourers; the records
  over-represent landowners because the poor left none.
- After the Black Death the flow reversed and cities had to pay people to
  go back to the land.
- Piedmont's *villenove* and *borghi franchi*: new towns founded with tax
  and legal privileges to draw peasants in.

What the sim does today: an arrival only replaces a dead adult (home,
job, class and ties), only while the town is below its target. From
about year 40 births alone keep the town at target, so arrivals stop
entirely. That is the opposite of the historical pattern.

Questions to decide:
- Should the town be a **demographic sink** (deaths > births), with
  growth coming from arrivals? That means higher mortality or lower
  fertility in town, plus a steady flow in.
- **Who arrives**: mostly poor, single young adults looking for work?
  Whole families? A few landowners? The user has asked for families
  moving in, and for people moving out when stressed and able to afford it.
- **What draws them and what repels them**: work, wages, the town's
  reputation, franchises, and epidemics (the post-plague reversal).
- **Where they live**: ties into homeowners, landlords and new houses.

> Feedback: Yes, the town should act as a demographic sink, and still keep growing a bit. Moving in we want both single young adults and whole families. And yes, it shuold also be possible for people to move out, in very extreme situations and only if they have the money for it. I would not consider the post-plague reversal for now, maybe for the future. People should be attracted by wages and work (which are the main reason why they might leave their original villages in the first place).

### 3.2 Ties forming and fading, friends, favors and scorn — Open

Warm ties rise from 8.5% of all ties to 21.4% in 50 years, and faster in
the second half; hatred slowly falls. The likely cause: every birth adds
warm family ties, while nothing makes ties form among non-family,
fade, or cool. There are no friends, no everyday favors, and no everyday
scorn. Details in `01-network-simulation.md` under "Kinds of ties",
"Ties forming and fading" and "Everyday scorn".

> **Update 2026-09-27 — Favors and scorn built, not yet balanced:** warm
> ties drift faster (15.7% at year 25) because family ties get far more
> interactions than the average the pull back is sized on. Next: size it
> per tie. Tie formation and fading still to design.
> **Update 2026-09-28 — Favors balanced:** sized per tie, neutral on their
> own. The remaining rise in warm ties (8.6% -> 13.0%) comes from the mix
> of ties (newborns bring only warm family ties, the dead lose everything,
> nobody gains neighbours): it needs tie formation and fading.

> Feedback: I like what you described for ties formation and fading in 01-network-simulation.md, let's start from there. Ties formation is also very important for new people in the town. Also, we should add the Favor or Scorn interaction, which simply changes by a very, very small amount the affinity between people. The more favor, the higher the likelihood of an interaction even being a Favor event rather than scorn (and viceversa). 

### 3.3 Class mobility, merchants and homeowners — Open

The rich triple in 50 years (111 to 332, 6% to 14% of the town): the poor
die of disease 4 times as often, a baby takes its mother's class, and
nobody ever changes class. The notes give a target from Florence's 1427
Catasto: **14.6%** of city households had no taxable wealth, and the top
**137 households (about 1.4%)** held **29.8%** of the assessed wealth.
Also note that the imported town has only poor and rich residents, no
middling ones.

> Feedback: how should we deal with how much richness the rich people can amass? We have to discuss in more depth the way the market worked for medieval cities. 

### 3.4 The imported town isn't at the sim's balance — Open

Even with marriage fixed, TownShape's town may not match the sim's own
demography (for example, 20% of residents under 5). Options: accept a
settling-in period and discard it in reports; make TownShape and the sim
share the same demographic rules (integration option A); or run a quiet
warm-up before the "real" start.

> **Update 2026-09-27 — Addressed (first version):** the adapted importer
> keeps TownShape's town, households, jobs and ties, and re-draws ages to
> the sim's settled shape and couples' sexes to the town's share. Old-age
> deaths added. No more dip. Still to do: bring this into TownShape itself.

> Feedback: Can we import the TownShape population generation, and adapt it to our needs? We are going to anyways have to integrate it within TownShape in the future. 

---

## Part 4. Proposed order

1. Commit the current state (population turnover, child mortality, the
   docs), so each change after it is its own commit.
2. **2.1 marriage**, checked with a 25-year run.
3. **2.2 religiousness**, **2.3 vacancies**, and the **2.4 thieves**
   measurement.
4. Discuss **3.1 organic migration** with the research notes, then 3.2,
   3.3 and 3.4.

> Feedback: This works for me. 
