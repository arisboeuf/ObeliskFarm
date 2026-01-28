// Ported from ObeliskGemEV/event/monte_carlo_optimizer.py (guided single-core MC).

import { COSTS } from "./constants";
import { applyUpgrades, runFullSimulation } from "./simulation";
import { createBaseEnemyStats, type EnemyStats, type PlayerStats } from "./stats";
import { greedyOptimize, type Budget, type UpgradeState, copyState, createEmptyState, getMaxLevelWithCaps, isUpgradeUnlocked } from "./optimizer";
import { mulberry32 } from "../rng";

export type ProgressCallback = (currentRun: number, totalRuns: number, currentWave: number, bestWave: number) => void;

export interface MCOptimizationResult {
  bestState: UpgradeState;
  bestWave: number;
  bestTime: number;
  materialsSpent: Budget;
  materialsRemaining: Budget;
  playerStats: PlayerStats;
  enemyStats: EnemyStats;
  allResults: Array<{ state: UpgradeState; wave: number; time: number }>;
  statistics: Record<string, number>;
}

type Rng = { random: () => number };

function makeRng(seed: number): Rng {
  const r = mulberry32(seed);
  return { random: r };
}

function weightedChoice<T>(items: T[], weights: number[], rng: Rng): T {
  let total = 0;
  for (const w of weights) total += w;
  if (total <= 0) return items[Math.floor(rng.random() * items.length)];
  const x = rng.random() * total;
  let acc = 0;
  for (let i = 0; i < items.length; i += 1) {
    acc += weights[i];
    if (x <= acc) return items[i];
  }
  return items[items.length - 1];
}

function buildCandidateState(args: {
  budget: Budget;
  prestige: number;
  initialState: UpgradeState;
  seed: number;
  epsilonGreedy: number;
}): UpgradeState {
  const { budget, prestige, initialState, seed, epsilonGreedy } = args;
  const rng = makeRng(seed);

  const state = copyState(initialState);
  const remaining: Budget = { 1: budget[1], 2: budget[2], 3: budget[3], 4: budget[4] };

  const available: Array<{ tier: 1 | 2 | 3 | 4; idx: number }> = [];
  for (const tier of [1, 2, 3, 4] as const) {
    for (let idx = 0; idx < COSTS[tier].length; idx += 1) {
      if (isUpgradeUnlocked(tier, idx, prestige)) available.push({ tier, idx });
    }
  }

  const tierPriorityScore: Record<number, Record<number, number>> = {
    1: { 0: 100, 9: 95, 6: 90, 1: 80, 2: 70, 4: 65, 3: 60, 5: 50, 7: 40, 8: 30 },
    2: { 2: 100, 0: 90, 1: 85, 4: 80, 3: 70, 5: 50, 6: 40 },
    3: { 0: 100, 4: 95, 7: 90, 1: 85, 3: 80, 2: 60, 6: 50, 5: 40 },
    4: { 4: 100, 7: 95, 1: 90, 3: 85, 0: 80, 2: 70, 5: 50, 6: 40 },
  };

  const maxIterations = 2000;
  for (let it = 0; it < maxIterations; it += 1) {
    const affordable: Array<{ tier: 1 | 2 | 3 | 4; idx: number; cost: number; eff: number }> = [];

    for (const a of available) {
      const currentLevel = state.levels[a.tier][a.idx];
      const maxLevel = getMaxLevelWithCaps(a.tier, a.idx, state);
      if (currentLevel >= maxLevel) continue;

      const baseCost = COSTS[a.tier][a.idx];
      const nextCost = Math.round(baseCost * 1.25 ** currentLevel);
      if (nextCost > remaining[a.tier]) continue;

      const prio = tierPriorityScore[a.tier]?.[a.idx] ?? 10;
      const eff = prio / (nextCost + 1) ** 0.35;
      affordable.push({ tier: a.tier, idx: a.idx, cost: nextCost, eff });
    }

    if (!affordable.length) break;

    let pick: { tier: 1 | 2 | 3 | 4; idx: number; cost: number };
    // Match Python logic:
    // if epsilon_greedy > 0 and rng.random() >= epsilon_greedy -> greedy; else exploratory weighted.
    if (epsilonGreedy > 0 && rng.random() >= epsilonGreedy) {
      const best = affordable.reduce((acc, cur) => (cur.eff > acc.eff ? cur : acc), affordable[0]);
      pick = { tier: best.tier, idx: best.idx, cost: best.cost };
    } else {
      const weights = affordable.map((x) => Math.max(1e-6, x.eff));
      const chosen = weightedChoice(affordable, weights, rng);
      pick = { tier: chosen.tier, idx: chosen.idx, cost: chosen.cost };
    }

    state.levels[pick.tier][pick.idx] += 1;
    remaining[pick.tier] -= pick.cost;
  }

  return state;
}

function evaluateStateSerial(args: { state: UpgradeState; prestige: number; runs: number; seed: number }): { wave: number; time: number; player: PlayerStats; enemy: EnemyStats } {
  const { state, prestige, runs, seed } = args;
  const rng = mulberry32(seed & 0x7fffffff);

  const { player, enemy } = applyUpgrades(state.levels, prestige, state.gemLevels);
  const sim = runFullSimulation(player, enemy, Math.max(1, runs), rng);
  return { wave: sim.avgWave, time: sim.avgTime, player, enemy };
}

export function monteCarloOptimizeGuided(args: {
  budget: Budget;
  prestige: number;
  initialState?: UpgradeState | null;
  numRuns?: number;
  eventRunsPerCombination?: number;
  seedBase?: number | null;
  progressCallback?: ProgressCallback | null;
}): MCOptimizationResult {
  const {
    budget,
    prestige,
    initialState: initialStateArg = null,
    numRuns = 2000,
    eventRunsPerCombination = 5,
    seedBase = null,
    progressCallback = null,
  } = args;

  const initialState = initialStateArg ? copyState(initialStateArg) : createEmptyState();
  const nCandidates = Math.max(1, Math.trunc(numRuns));
  const runs = Math.max(1, Math.trunc(eventRunsPerCombination));
  const seedBaseLocal = (seedBase ?? (Date.now() & 0x7fffffff)) & 0x7fffffff;

  const candidates: UpgradeState[] = [];
  try {
    const greedy = greedyOptimize({ budget, prestige, initialState, targetWave: null, seed: seedBaseLocal + 123 });
    candidates.push(copyState(greedy.upgrades));
  } catch {
    // ignore
  }

  for (let i = 0; i < nCandidates; i += 1) {
    const eps = i % 5 !== 0 ? 0.2 : 1.0;
    candidates.push(
      buildCandidateState({
        budget,
        prestige,
        initialState,
        seed: seedBaseLocal + i,
        epsilonGreedy: eps,
      }),
    );
  }

  const allResults: Array<{ state: UpgradeState; wave: number; time: number }> = [];
  let bestState: UpgradeState | null = null;
  let bestWave = -1;
  let bestTime = Number.POSITIVE_INFINITY;

  for (let idx = 0; idx < candidates.length; idx += 1) {
    const cand = candidates[idx];
    const ev = evaluateStateSerial({ state: cand, prestige, runs, seed: seedBaseLocal + 10_000 + (idx + 1) });
    allResults.push({ state: copyState(cand), wave: ev.wave, time: ev.time });

    if (ev.wave > bestWave || (ev.wave === bestWave && ev.time < bestTime)) {
      bestWave = ev.wave;
      bestTime = ev.time;
      bestState = copyState(cand);
    }

    if (progressCallback) progressCallback(idx + 1, candidates.length, ev.wave, bestWave);
  }

  const waves = allResults.map((r) => r.wave);
  const times = allResults.map((r) => r.time);
  const wavesSorted = waves.slice().sort((a, b) => a - b);
  const timesSorted = times.slice().sort((a, b) => a - b);
  const n = waves.length;

  const meanWave = n ? waves.reduce((a, b) => a + b, 0) / n : 0;
  const meanTime = n ? times.reduce((a, b) => a + b, 0) / n : 0;

  const stdDevWave =
    n > 1 ? Math.sqrt(waves.reduce((acc, w) => acc + (w - meanWave) ** 2, 0) / (n - 1)) : 0;
  const stdDevTime =
    n > 1 ? Math.sqrt(times.reduce((acc, t) => acc + (t - meanTime) ** 2, 0) / (n - 1)) : 0;

  const medianWave = n ? wavesSorted[Math.floor(n / 2)] : 0;
  const medianTime = n ? timesSorted[Math.floor(n / 2)] : 0;
  const p5Wave = n ? wavesSorted[Math.floor(n * 0.05)] : 0;
  const p95Wave = n ? wavesSorted[Math.floor(n * 0.95)] : 0;

  const best = bestState ?? initialState;

  // spent/remaining relative to initial state (matches Python)
  const materialsSpent: Budget = { 1: 0, 2: 0, 3: 0, 4: 0 };
  const materialsRemaining: Budget = { 1: budget[1], 2: budget[2], 3: budget[3], 4: budget[4] };
  for (const tier of [1, 2, 3, 4] as const) {
    for (let uidx = 0; uidx < COSTS[tier].length; uidx += 1) {
      const initialLevel = initialState.levels[tier][uidx] ?? 0;
      const finalLevel = best.levels[tier][uidx] ?? 0;
      for (let level = initialLevel; level < finalLevel; level += 1) {
        const cost = Math.round(COSTS[tier][uidx] * 1.25 ** level);
        materialsSpent[tier] += cost;
        materialsRemaining[tier] -= cost;
      }
    }
  }

  const { playerStats, enemyStats } = (() => {
    const { player, enemy } = applyUpgrades(best.levels, prestige, best.gemLevels);
    return { playerStats: player, enemyStats: enemy };
  })();

  const statistics: Record<string, number> = {
    mean_wave: meanWave,
    median_wave: medianWave,
    std_dev_wave: stdDevWave,
    min_wave: n ? Math.min(...waves) : 0,
    max_wave: n ? Math.max(...waves) : 0,
    p5_wave: p5Wave,
    p95_wave: p95Wave,
    mean_time: meanTime,
    median_time: medianTime,
    std_dev_time: stdDevTime,
    min_time: n ? Math.min(...times) : 0,
    max_time: n ? Math.max(...times) : 0,
  };

  return {
    bestState: best,
    bestWave,
    bestTime,
    materialsSpent,
    materialsRemaining,
    playerStats,
    enemyStats,
    allResults,
    statistics,
  };
}

