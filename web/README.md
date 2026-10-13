# ObeliskFarm Web

Web-based calculator toolkit for **Idle Obelisk Miner**, focused on **Monte Carlo simulators** that optimize skill point and upgrade distributions.

## Core Features

- **Archaeology Simulator**: MC optimizer for skill point distribution (max stage, XP/hour, fragments/hour). See [How the Archaeology MC works](#how-the-archaeology-mc-works) below.
- **Event Budget Optimizer**: Guided MC optimizer for event upgrade planning
- **Gem EV Calculator**: Gem-equivalent per hour from freebies
- **Stargazing Calculator**: Stars/hour calculations (online/offline)

## Local Development

Prerequisite: Install Node.js (LTS).

```bash
cd web
npm install
npm run dev
```

Then open the URL shown in the terminal (usually `http://localhost:5173`).

## How the Archaeology MC works

In simple terms, the Monte Carlo optimizers (Stage Push, XP, Fragments) work like this:

1. **Screening (Phase 1)**  
   Many different ways to distribute your skill points (STR, AGI, PER, INT, LUCK) are tried. For each, a number of simulation runs are done. We get an average result (e.g. average max stage or XP per hour) and how much that result varies.  
   **Who goes further:** Only builds that are **not significantly worse** than the best (statistical test, α=0.05) go on. So we don’t use a fixed “top 5%” cut; we use a significance test. How many that is depends on the data.

2. **Refinement (Phase 2)**  
   We take the builds that passed and test small variations around them (a bit more STR here, a bit less AGI there). Again we run simulations and get averages and variance.  
   The **best** build after this step is the one with the highest primary value (e.g. max stage), then secondary, then tertiary. We still use the same runs to see **who is tied** with the best: everyone who is not significantly worse than #1 on the primary metric counts as “tied at primary”.

3. **Tie-break and winner**  
   If several builds are tied at primary (not significantly different), we look at the next metric (secondary), then tertiary. The **winner** is the single build that comes out on top in this order. The report shows how many were “tied at primary” and why the winner won.

4. **Final sims**  
   The chosen build is then run with a large number of final runs (e.g. 3000) to get the numbers and charts you see in the result (floors per run, XP/hour, etc.).

**Important:** There is no fixed “3%” or “5%” rule. At each step, **statistical tests** decide who is “the same” or “worse”. More simulation runs (higher N in screening/refinement) give more precise estimates and better significance decisions.

## Archaeology: active play (not modeled)

The simulator counts idle stats and the Enrage, Flurry, and Quake cooldowns. Click interactions are out of scope. Candidates if an active-play mode is added later:

- **Ability Fairy** (Ascension 2 upgrade `ability_fairy_a2`): after unlock, fairies appear at random in the Archaeology window. Clicking one instantly refreshes every other ability and fires them immediately. Loot Mod Gain +0.05x per level is already included. Spawn rate and click timing are not simulated.

## Notes

- Saves are stored automatically in the browser (`localStorage`).
- All calculations run client-side (no server required).

