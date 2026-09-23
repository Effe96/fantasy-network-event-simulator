# Famous Medieval Diseases: Lethality, Contagion, and Timelines

These estimates are rough. Medieval figures come from reconstructions (parish records, chronicles, ancient DNA) or from modern data on untreated cases. Treat the ranges as order-of-magnitude guides, not measurements.

## Summary table

| Disease | CFR (untreated) | R₀ | Incubation | Infection → death (fatal cases) | Transmission |
|---|---|---|---|---|---|
| **Bubonic plague** (*Y. pestis*) | ~30–60% | ~1.5–2 (model-based, Black Death) | 2–8 days | ~6–15 days | Fleas or lice → human |
| **Pneumonic plague** | ~95–100% | ~1.3 (range ~0.8–3) | 1–4 days (sometimes <1) | ~2–6 days | Respiratory droplets, person-to-person |
| **Septicemic plague** | ~100% | — (rarely spreads directly) | 1–7 days | ~2–8 days (can kill within hours of symptoms) | Bloodstream infection, usually from a bite |
| **Smallpox** (*variola major*) | ~30% (up to 50%+ in populations never exposed before) | ~3.5–6 | 7–17 days (typically ~12) | ~3–4 weeks | Respiratory and contact |
| **Measles** | ~1–10% (much higher in never-exposed or malnourished populations) | ~12–18 | 10–14 days | ~3–5 weeks (mostly from secondary pneumonia) | Airborne |
| **Tuberculosis** ("consumption") | ~50–70% over ~5–10 years | ~1–4 (an active case infects ~10/year, most stay latent) | Weeks to years | ~2–5 years (median ~3) | Airborne, slow |
| **Epidemic typhus** ("gaol/camp fever") | ~10–60% | Depends on louse density | 7–14 days | ~3–4 weeks | Body lice |
| **Dysentery** ("bloody flux", *Shigella*) | ~5–20% in epidemics | Poorly defined; driven by sanitation | 1–3 days | ~5–20 days | Fecal-oral |
| **Influenza** (e.g., 1510 pandemic) | <1–2% | ~1.5–3 | 1–4 days | ~1–3 weeks (mostly from secondary pneumonia) | Respiratory |
| **English sweating sickness** (1485–1551) | ~30–50%? (very uncertain) | Unknown | ~1–2 days? | ~1–3 days (death often 3–24 h after symptoms) | Unknown pathogen, possibly a hantavirus |
| **Leprosy** | Low directly; it disables rather than kills | <1 effectively; ~95% of people are naturally resistant | 2–10+ years | Years to decades, indirectly | Prolonged close contact |

"Infection → death" is the typical time for **fatal cases only**: incubation plus the illness itself.

## Reading the numbers

1. **CFR is not population mortality.** The Black Death killed roughly 30–60% of Europe's *population* between 1347 and 1351. That number combines the share of people infected with the CFR, and the mix of plague forms varied by place.

2. **R₀ is not a property of the pathogen alone.** Mechanically, R₀ ≈ β · c · D:
   - β is the transmission probability per contact,
   - c is the number of contacts per unit time,
   - D is the infectious period.

   The same pathogen gives a different R₀ in a crowded walled city than in a scattered village. For vector-borne diseases like plague and typhus, you also need the vector's density and biting rate, so those R₀ values are model outputs, not observations.

3. **Deadly and contagious trade off.** Pneumonic plague kills almost everyone but has a low R₀, because victims die within ~2–3 days, so D is small. Measles has a low CFR but a huge R₀, from a long infectious window plus airborne spread. Smallpox was historically so destructive because it scored high on both.

4. **Time to death feeds back into R₀.** A fast death means a short D. That is why pneumonic plague and sweating sickness burned out locally despite being lethal, while smallpox's ~2–3-week illness gave it a long infectious window.

5. **What matters is whether transmission starts before symptoms.** A disease that spreads before people feel sick, such as influenza or measles near the end of incubation, is hard to contain by isolating the sick. Smallpox and pneumonic plague spread mainly *after* symptoms appear, which is why medieval quarantine (the 40-day *quaranta giorni*) had some real effect on them.

6. **Some "medieval plagues" weren't contagious.** St. Anthony's fire, for example, was ergotism, a poisoning from fungus on rye.

## Reliability

- Most reliable: smallpox and measles, which have abundant 19th–20th century data on untreated cases.
- Moderately reliable: the plague forms and typhus, where CFRs are well established but medieval R₀ values are model-dependent.
- Least reliable: English sweating sickness. The pathogen was never identified, and all figures rest on contemporary chronicles.
