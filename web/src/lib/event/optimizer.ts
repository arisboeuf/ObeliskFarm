// Ported (trimmed) from ObeliskGemEV/event/optimizer.py

import { CAP_UPGRADES, COSTS, MAX_LEVELS, PRESTIGE_UNLOCKED, UPGRADE_SHORT_NAMES, getPrestigeWaveRequirement } from "./constants";
import { createBaseEnemyStats, type EnemyStats, type PlayerStats } from "./stats";
import { applyUpgrades, calculateBreakpointEfficiency, calculateDamageBreakpoints, getEnemyHpAtWave, runFullSimulation } from "./simulation";
import { mulberry32 } from "../rng";

export type Budget = Record<1 | 2 | 3 | 4, number>;

export interface UpgradeState {
  levels: Record<1 | 2 | 3 | 4, number[]>;
  gemLevels: [number, number, number, number];
}

export interface OptimizationResult {
  upgrades: UpgradeState;
  expectedWave: number;
  expectedTime: number;
  materialsSpent: Budget;
  materialsRemaining: Budget;
  playerStats: PlayerStats;
  enemyStats: EnemyStats;
  recommendations: string[];
  breakpoints: Array<Record<string, number>>;
}

export function createEmptyState(): UpgradeState {
  return {
    levels: {
      1: Array.from({ length: 10 }, () => 0),
      2: Array.from({ length: 7 }, () => 0),
      3: Array.from({ length: 8 }, () => 0),
      4: Array.from({ length: 8 }, () => 0),
    },
    gemLevels: [0, 0, 0, 0],
  };
}

export function copyState(state: UpgradeState): UpgradeState {
  return {
    levels: {
      1: state.levels[1].slice(),
      2: state.levels[2].slice(),
      3: state.levels[3].slice(),
      4: state.levels[4].slice(),
    },
    gemLevels: [...state.gemLevels] as [number, number, number, number],
  };
}

export function isUpgradeUnlocked(tier: 1 | 2 | 3 | 4, idx: number, prestige: number): boolean {
  return prestige >= PRESTIGE_UNLOCKED[tier][idx];
}

export function getMaxLevelWithCaps(tier: 1 | 2 | 3 | 4, upgradeIdx: number, state: UpgradeState): number {
  const baseMax = MAX_LEVELS[tier][upgradeIdx];
  const capIdx = CAP_UPGRADES[tier] - 1;
  if (upgradeIdx === capIdx) {
    // cap upgrade itself
    if (tier === 4 && upgradeIdx === 6) return baseMax; // cap of caps doesn't get increased
    return baseMax + state.levels[4][6]; // increased by cap of caps
  }
  return baseMax + state.levels[tier][capIdx];
}

export function formatUpgradeSummary(state: UpgradeState): string {
  const lines: string[] = [];
  for (const tier of [1, 2, 3, 4] as const) {
    const tierUpgrades: string[] = [];
    state.levels[tier].forEach((lvl, idx) => {
      if (lvl > 0) tierUpgrades.push(`${UPGRADE_SHORT_NAMES[tier][idx]}: ${lvl}`);
    });
    if (tierUpgrades.length) lines.push(`Tier ${tier}: ${tierUpgrades.join(", ")}`);
  }
  return lines.length ? lines.join("\n") : "No upgrades";
}

export function greedyOptimize(args: {
  budget: Budget;
  prestige: number;
  targetWave?: number | null;
  initialState?: UpgradeState;
  seed?: number;
}): OptimizationResult {
  const { budget, prestige, targetWave: targetWaveArg = null, initialState, seed } = args;

  const state = initialState ? copyState(initialState) : createEmptyState();
  const remaining: Budget = { 1: budget[1], 2: budget[2], 3: budget[3], 4: budget[4] };
  const spent: Budget = { 1: 0, 2: 0, 3: 0, 4: 0 };
  const recommendations: string[] = [];

  const enemyBase = createBaseEnemyStats();
  const rng = mulberry32(seed ?? (Date.now() & 0xffffffff));

  const { player: player0 } = applyUpgrades(state.levels, prestige, state.gemLevels);
  const estimated0 = runFullSimulation(player0, enemyBase, 20, rng);
  let estimatedWave = estimated0.avgWave;

  const wavePusherMode = targetWaveArg == null;
  let targetWave = targetWaveArg == null ? null : Math.max(1, Math.floor(targetWaveArg));

  if (wavePusherMode) {
    targetWave = Math.max(1, Math.floor(estimatedWave * 1.3));
    recommendations.push("Wave Pusher Mode: Maximizing wave with available budget");
    recommendations.push(`Current estimated wave: ${estimatedWave.toFixed(1)}, analyzing up to wave ${targetWave}`);
  } else {
    recommendations.push(`Target Wave Mode: Reaching Wave ${targetWave}`);
    estimatedWave = targetWave!;
  }

  const maxWaveForAnalysis = Math.max(1, Math.floor(estimatedWave * 1.2));
  recommendations.push(`Breakpoint analysis: Analyzing waves 1-${maxWaveForAnalysis} with prestige wave weighting`);

  const tierPriorities: Record<1 | 2 | 3 | 4, Array<[number, number, string]>> = {
    1: [
      [0, 100, "atk"],
      [9, 95, "atk_hp"],
      [6, 90, "atk_hp"],
      [1, 80, "hp"],
      [2, 70, "speed"],
      [4, 65, "speed"],
      [3, 60, "speed"],
      [5, 50, "crit"],
      [7, 40, "cap"],
      [8, 30, "prestige"],
    ],
    2: [
      [2, 100, "debuff"],
      [0, 90, "hp"],
      [1, 85, "debuff"],
      [4, 80, "atk_speed"],
      [3, 70, "debuff"],
      [5, 50, "cap"],
      [6, 40, "prestige"],
    ],
    3: [
      [0, 100, "atk"],
      [4, 95, "atk_hp"],
      [7, 90, "hp_speed"],
      [1, 85, "speed"],
      [3, 80, "speed"],
      [2, 60, "crit"],
      [6, 50, "money"],
      [5, 40, "cap"],
    ],
    4: [
      [4, 100, "atk_hp"],
      [7, 95, "hp_speed"],
      [1, 90, "hp"],
      [3, 85, "speed"],
      [0, 80, "block"],
      [2, 70, "crit"],
      [5, 50, "cap"],
      [6, 40, "cap"],
    ],
  };

  const prestigeWaves = new Set<number>();
  for (let p = prestige + 1; p < 20; p += 1) {
    const pw = getPrestigeWaveRequirement(p);
    if (pw <= maxWaveForAnalysis) prestigeWaves.add(pw);
  }

  const maxIterations = 1000;
  for (let iter = 0; iter < maxIterations; iter += 1) {
    let bestBuy: { tier: 1 | 2 | 3 | 4; idx: number; cost: number } | null = null;
    let bestScore = -1;

    // Compute once per iteration
    const { player: playerCurrent, enemy: enemyCurrent } = applyUpgrades(state.levels, prestige, state.gemLevels);

    for (const tier of [1, 2, 3, 4] as const) {
      for (const [idx, priority, category] of tierPriorities[tier]) {
        if (!isUpgradeUnlocked(tier, idx, prestige)) continue;

        const currentLevel = state.levels[tier][idx];
        const maxLevel = getMaxLevelWithCaps(tier, idx, state);
        if (currentLevel >= maxLevel) continue;

        const baseCost = COSTS[tier][idx];
        const nextCost = Math.round(baseCost * 1.25 ** currentLevel);
        if (nextCost > remaining[tier]) continue;

        let effectiveScore = priority;

        // Breakpoint-aware scoring for ATK-ish categories
        if (category === "atk" || category === "atk_hp" || category === "atk_speed") {
          // Value of +1 level for this upgrade across waves (weighted)
          const testState = copyState(state);
          testState.levels[tier][idx] = currentLevel + 1;

          const { player: playerAfter } = applyUpgrades(testState.levels, prestige, testState.gemLevels);
          const atkIncrease = playerAfter.atk - playerCurrent.atk;

          if (atkIncrease > 0) {
            const useCrit = playerCurrent.crit >= 5;
            let totalValue = 0.0;
            for (let wave = 1; wave <= Math.min(maxWaveForAnalysis, 200); wave += 1) {
              const enemyHp = getEnemyHpAtWave(enemyCurrent, wave);

              const hitsBefore = useCrit
                ? Math.ceil((enemyHp / (playerCurrent.atk * (1 + Math.min(playerCurrent.crit / 100, 1) * (playerCurrent.critDmg - 1)))))
                : Math.ceil(enemyHp / Math.max(1, playerCurrent.atk));
              const hitsAfter = useCrit
                ? Math.ceil((enemyHp / (playerAfter.atk * (1 + Math.min(playerAfter.crit / 100, 1) * (playerAfter.critDmg - 1)))))
                : Math.ceil(enemyHp / Math.max(1, playerAfter.atk));

              if (hitsAfter < hitsBefore) {
                const hitsSaved = hitsBefore - hitsAfter;
                const timePerHit = playerCurrent.defaultAtkTime / Math.max(1e-6, playerCurrent.atkSpeed);
                let waveWeight = 1.0;
                if (prestigeWaves.has(wave)) waveWeight = 3.0;
                if (wave < 10) waveWeight *= 0.5;
                else if (wave < 20) waveWeight *= 0.75;
                if (wave > 50) waveWeight *= 1.5;
                if (wave > 100) waveWeight *= 2.0;

                totalValue += hitsSaved * timePerHit * 5 * waveWeight;
              }
            }
            const bpValue = totalValue / atkIncrease;
            effectiveScore += Math.min(100, bpValue * 0.1);
          }
        }

        if (category === "hp" || category === "hp_speed" || category === "atk_hp" || category === "debuff") {
          const hpBonus = Math.min(50, estimatedWave * 0.5);
          effectiveScore += hpBonus;
        }

        if (category === "speed") {
          effectiveScore += 20;
        }

        const costEfficiency = 100 / (nextCost + 1);
        effectiveScore += costEfficiency * 0.5;

        if (effectiveScore > bestScore) {
          bestScore = effectiveScore;
          bestBuy = { tier, idx, cost: nextCost };
        }
      }
    }

    if (!bestBuy) break;
    state.levels[bestBuy.tier][bestBuy.idx] += 1;
    remaining[bestBuy.tier] -= bestBuy.cost;
    spent[bestBuy.tier] += bestBuy.cost;
  }

  const { player, enemy } = applyUpgrades(state.levels, prestige, state.gemLevels);
  const sim = runFullSimulation(player, enemy, 50, rng);

  const useCrit = player.crit >= 5;
  const bpTargetWave = wavePusherMode ? Math.floor(sim.avgWave * 1.2) : (targetWave ?? Math.floor(sim.avgWave));
  const breakpoints = calculateBreakpointEfficiency(
    calculateDamageBreakpoints(player, enemy, wavePusherMode ? bpTargetWave : targetWave, 10, useCrit),
    player,
    enemy,
    bpTargetWave,
  );

  if (wavePusherMode) {
    recommendations.push(`Final ATK: ${player.atk}`);
    recommendations.push(`Final HP: ${player.health}`);
    recommendations.push(`Estimated Max Wave: ${sim.avgWave.toFixed(1)}`);
    recommendations.push(`Estimated Time: ${sim.avgTime.toFixed(1)}s per run`);
  } else {
    recommendations.push(`Final ATK: ${player.atk}`);
    recommendations.push(`Final HP: ${player.health}`);
    recommendations.push(`Estimated Wave: ${sim.avgWave.toFixed(1)}`);
    recommendations.push(`Estimated Time: ${sim.avgTime.toFixed(1)}s per run`);
  }

  if (breakpoints.length) {
    const best = breakpoints[0];
    const atkNeeded = (best.atk_increase as number) ?? 0;
    if (atkNeeded > 0) {
      recommendations.push(`Next Breakpoint: Wave ${best.wave} needs +${atkNeeded} ATK (→ ${best.required_atk} total)`);
    }
  }

  if (!wavePusherMode && targetWave != null && sim.avgWave < targetWave) {
    recommendations.push(`WARNING: May not reach target wave ${targetWave}!`);
    recommendations.push("Consider: More prestiges, gem upgrades, or lower target");
  }

  return {
    upgrades: state,
    expectedWave: sim.avgWave,
    expectedTime: sim.avgTime,
    materialsSpent: spent,
    materialsRemaining: remaining,
    playerStats: player,
    enemyStats: enemy,
    recommendations,
    breakpoints,
  };
}

