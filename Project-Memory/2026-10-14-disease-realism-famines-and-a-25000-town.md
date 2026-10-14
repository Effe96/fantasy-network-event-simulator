# 2026-10-14 — Disease realism, long famines, step 4, and a 25,000-person town

## What was done

1. **Realism audit 5.1-5.3** (7779292, pushed). Immunity per disease: the
   user set influenza 6 months, dysentery 1 year, plague and measles for
   life (my first numbers were unsourced guesses, and the user corrected
   them); typhus 10 years is still mine. Anyone 5+ had measles as a child;
   measles kills adults x3 (user: far deadlier in adults). The old die of
   a sickness x2 in their 60s, x4 from 70. Quarantine for plague only.
   Found on the way: catching a disease wiped the record of the others.
2. **Attack rates** (71eab98). Measured one outbreak at a time, contagion
   alone: dysentery/typhus reached 72%, influenza 81%. Sourced targets
   (Shigella epidemics 6-39%, 1918 >50% infected). Tier 3 R0 2.0 -> 1.2,
   influenza 2.25 -> 1.5. Tried first and dropped: spreading
   dysentery/typhus only over close ties (no effect: neighbour ties mesh
   the whole town).
3. **Long famines** (71eab98). The famine draws were fair; the granary
   only refilled after a harvest priced at most 1.0, so after one famine it
   stayed empty 6-7 years. Now it refills below 1.3. Famine deaths 86 -> 15
   per 25-year run.
4. **Personal money step 4** (71eab98; Project_Vision/09 §9): weapons x1.3
   in a fight, survivors of an attack buy one from the nearest blacksmith,
   creditors take goods after land. The plan had no step 4: I had named it
   without reading the file, and built the rest of §5 as step 4.
5. **The tie archive** (0fe9cc5): ~1 GB per 25 years in Riverport, it would
   have filled the machine at 25,000 people. It can go to a file now;
   closed places' records leave memory. Results unchanged.
6. **25,000-person run**: 25 years, 4 h 6 min, peak 6.4 GB. Report:
   https://claude.ai/artifact/JdbPkSREo5xLd1T1FqGj8T. Over the user's
   2 hours, so the 40,000/10-year run was not started.

## Checks

25-year runs, 3 seeds, quiet and with epidemics, before against after each
step (scratchpad dis/disE, all/allE). Population, classes, hunger and
homelessness within seed noise. Main dashboard refreshed (v23).

## Open

- The big town riots 14x as often as Riverport, falls 5% after import and
  doesn't grow (tally entry added).
- Measles never broke out in a long run; only the test covers it.
- Typhus immunity (10 years) has no source.
- Evictions stay high.
