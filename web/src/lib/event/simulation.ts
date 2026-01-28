// Ported (trimmed) from ObeliskGemEV/event/simulation.py

import { createBaseEnemyStats, createBasePlayerStats, type EnemyStats, type PlayerStats } from "./stats";
import type { Rng } from "../rng";

export function roundNumber(n: number, precision = 0): number {
  const f = 10 ** precision;
  return Math.round(n * f) / f;
}

export function applyUpgrades(
  upgrades: Record<number, number[]>,
  prestiges: number,
  gemUps: [number, number, number, number] = [0, 0, 0, 0],
): { player: PlayerStats; enemy: EnemyStats } {
  const p = { ...createBasePlayerStats() };
  const e = { ...createBaseEnemyStats() };

  if (upgrades[1]) {
    const u = upgrades[1];
    p.atk += u[0];
    p.health += 2 * u[1];
    p.atkSpeed += 0.02 * u[2];
    p.walkSpeed += 0.03 * u[3];
    p.gameSpeed += 0.03 * u[4]; // +3% Event Game Speed
    p.crit += u[5];
    p.critDmg += 0.1 * u[5];
    p.atk += u[6];
    p.health += 2 * u[6];
    // u[7] cap (no direct stat)
    p.prestigeBonusScale += 0.01 * u[8];
    p.health += 3 * u[9];
    p.atk += 3 * u[9];
  }

  if (upgrades[2]) {
    const u = upgrades[2];
    p.health += 3 * u[0];
    e.atkSpeed -= 0.02 * u[1];
    e.atk -= u[2];
    e.crit -= u[3];
    e.critDmg -= 0.1 * u[3];
    p.atk += u[4];
    p.atkSpeed += 0.01 * u[4];
    // u[5] cap
    p.prestigeBonusScale += 0.02 * u[6];
  }

  if (upgrades[3]) {
    const u = upgrades[3];
    p.atk += 2 * u[0];
    p.atkSpeed += 0.02 * u[1];
    p.crit += u[2];
    p.gameSpeed += 0.05 * u[3]; // +5% Event Game Speed
    p.atk += 3 * u[4];
    p.health += 3 * u[4];
    // u[5] cap
    p.x5Money += 3 * u[6];
    p.health += 5 * u[7];
    p.atkSpeed += 0.03 * u[7];
  }

  if (upgrades[4]) {
    const u = upgrades[4];
    p.blockChance += 0.01 * u[0];
    p.health += 5 * u[1];
    p.critDmg += 0.1 * u[2];
    e.critDmg -= 0.1 * u[2];
    p.atkSpeed += 0.02 * u[3];
    p.walkSpeed += 0.02 * u[3];
    p.atk += 4 * u[4];
    p.health += 4 * u[4];
    // u[5] cap
    // u[6] cap of caps
    p.health += 10 * u[7];
    p.atkSpeed += 0.05 * u[7];
  }

  // Prestige & gem multipliers (match Python behavior)
  p.atk = roundNumber(p.atk * (1 + p.prestigeBonusScale * prestiges) * (1 + 0.1 * gemUps[0]));
  p.health = roundNumber(p.health * (1 + p.prestigeBonusScale * prestiges) * (1 + 0.1 * gemUps[1]));
  p.gameSpeed = p.gameSpeed + 1.25 * gemUps[2]; // +125% per level (was +1.25 additive)
  p.x2Money = p.x2Money + gemUps[3];

  return { player: p, enemy: e };
}

export function simulateEventRun(player: PlayerStats, enemy: EnemyStats, rng: Rng): { wave: number; subwave: number; time: number } {
  let playerHp = player.health;
  let time = 0.0;
  let pAtkProg = 0.0;
  let eAtkProg = 0.0;
  let wave = 0;
  let finalSubwave = 0;

  const maxWaves = 1000;

  // basic safety
  const atkSpeed = player.atkSpeed <= 0 ? 1.0 : player.atkSpeed;
  const walkSpeed = player.walkSpeed <= 0 ? 1.0 : player.walkSpeed;
  const gameSpeed = player.gameSpeed <= 0 ? 1.0 : player.gameSpeed;

  while (playerHp > 0 && wave < maxWaves) {
    wave += 1;
    for (let subwave = 5; subwave >= 1; subwave -= 1) {
      if (playerHp <= 0) break;

      let enemyHp = enemy.baseHealth + enemy.healthScaling * wave;
      let combatIterations = 0;
      const maxCombatIterations = 10000;

      while (enemyHp > 0 && playerHp > 0 && combatIterations < maxCombatIterations) {
        combatIterations += 1;

        const enemyAtkSpeed = enemy.atkSpeed + wave * 0.02;
        const pAtkTimeLeft = (1 - pAtkProg) / atkSpeed;
        const eAtkTimeLeft = (1 - eAtkProg) / enemyAtkSpeed;

        if (pAtkTimeLeft > eAtkTimeLeft) {
          // enemy attacks
          pAtkProg += (eAtkTimeLeft / enemyAtkSpeed) * atkSpeed;
          eAtkProg -= 1;

          let dmg = Math.max(1, roundNumber(enemy.atk + wave * enemy.atkScaling));

          const enemyCritChance = enemy.crit + wave;
          if (enemyCritChance > 0 && rng() * 100 <= enemyCritChance) {
            const enemyCritMult = enemy.critDmg + enemy.critDmgScaling * wave;
            if (enemyCritMult > 1) dmg = roundNumber(dmg * enemyCritMult);
          }

          if (player.blockChance > 0 && rng() <= player.blockChance) {
            dmg = 0;
          }

          playerHp -= dmg;
          time += eAtkTimeLeft / enemyAtkSpeed;
        } else {
          // player attacks
          const enemyAtkSpeed = enemy.atkSpeed + wave * 0.02;
          eAtkProg += (pAtkTimeLeft / atkSpeed) * enemyAtkSpeed;
          pAtkProg -= 1;

          let dmg = player.atk;
          if (player.crit > 0 && rng() * 100 <= player.crit) {
            dmg = roundNumber(player.atk * player.critDmg);
          }
          enemyHp -= dmg;
          time += pAtkTimeLeft / atkSpeed;
        }
      }

      time += player.defaultWalkTime / walkSpeed;

      if (playerHp <= 0 && finalSubwave === 0) finalSubwave = subwave;
    }
  }

  return { wave, subwave: finalSubwave, time: time / gameSpeed };
}

export function runFullSimulation(
  player: PlayerStats,
  enemy: EnemyStats,
  runs: number,
  rng: Rng,
): { results: Array<[number, number, number]>; avgWave: number; avgTime: number } {
  const results: Array<[number, number, number]> = [];
  let totalDistance = 0.0;
  let totalTime = 0.0;

  for (let i = 0; i < runs; i += 1) {
    const r = simulateEventRun(player, enemy, rng);
    results.push([r.wave, r.subwave, r.time]);
    totalDistance += r.wave + 1 - r.subwave * 0.2;
    totalTime += r.time;
  }

  results.sort((a, b) => (a[0] + 1 - a[1] * 0.2) - (b[0] + 1 - b[1] * 0.2));
  return { results, avgWave: totalDistance / runs, avgTime: totalTime / runs };
}

export function calculateMaterials(wave: number, player: PlayerStats): { mat1: number; mat2: number; mat3: number; mat4: number } {
  const triangular = (n: number) => (n * n + n) / 2;
  const multiplier = (1 + player.x2Money) * (1 + 4 * (player.x5Money / 100));
  return {
    mat1: triangular(wave) * multiplier,
    mat2: triangular(Math.floor(wave / 5)) * multiplier,
    mat3: triangular(Math.floor(wave / 10)) * multiplier,
    mat4: triangular(Math.floor(wave / 15)) * multiplier,
  };
}

export function calculateHitsToKill(playerAtk: number, enemyHp: number): number {
  if (playerAtk <= 0) return Number.POSITIVE_INFINITY;
  return Math.max(1, Math.ceil(enemyHp / playerAtk));
}

export function calculateHitsToKillWithCrit(playerAtk: number, enemyHp: number, critChancePct: number, critDmg: number): number {
  const critProb = Math.min(critChancePct / 100.0, 1.0);
  const avgDmgPerHit = playerAtk * (1 + critProb * (critDmg - 1));
  if (avgDmgPerHit <= 0) return Number.POSITIVE_INFINITY;
  return enemyHp / avgDmgPerHit;
}

export function getEnemyHpAtWave(enemy: EnemyStats, wave: number): number {
  return enemy.baseHealth + enemy.healthScaling * wave;
}

export function getGemMaxLevel(prestigeCount: number, idx: number): number {
  // Matches ObeliskGemEV/event/simulation.py:get_gem_max_level
  if (idx < 2) return 5 + prestigeCount; // dmg / hp
  if (idx === 2) return 1 + Math.min(2, Math.floor(prestigeCount / 5)); // game speed
  return 1; // 2x currencies
}

export function calculateDamageBreakpoints(
  player: PlayerStats,
  enemy: EnemyStats,
  targetWave: number | null,
  maxBreakpoints = 10,
  useCrit = false,
): Array<Record<string, number>> {
  const currentAtk = player.atk;
  const startWave = targetWave == null ? 1 : Math.max(1, targetWave - 5);
  const endWave = targetWave == null ? 100 : targetWave + 5;

  const seen = new Set<string>();
  const bps: Array<Record<string, number>> = [];

  for (let wave = startWave; wave <= endWave; wave += 1) {
    const enemyHp = getEnemyHpAtWave(enemy, wave);
    let currentHitsFloat = 0;
    let currentHits = 0;

    if (useCrit) {
      currentHitsFloat = calculateHitsToKillWithCrit(currentAtk, enemyHp, player.crit, player.critDmg);
      currentHits = Math.ceil(currentHitsFloat);
    } else {
      currentHits = calculateHitsToKill(currentAtk, enemyHp);
      currentHitsFloat = currentHits;
    }

    if (currentHits <= 1) continue;
    const targetHits = currentHits - 1;

    let requiredAtk = 0;
    if (useCrit) {
      const critProb = Math.min(player.crit / 100.0, 1.0);
      const critMultiplier = 1 + critProb * (player.critDmg - 1);
      const avgDmgNeeded = enemyHp / targetHits;
      requiredAtk = Math.ceil(avgDmgNeeded / (critMultiplier > 0 ? critMultiplier : 1));
    } else {
      requiredAtk = Math.ceil(enemyHp / targetHits);
    }

    const atkIncrease = requiredAtk - currentAtk;
    if (atkIncrease <= 0) continue;

    const timePerHit = 1.0 / (player.atkSpeed <= 0 ? 1 : player.atkSpeed);
    const timeSavedPerEnemy = timePerHit;

    const key = `${wave}:${targetHits}:${requiredAtk}`;
    if (seen.has(key)) continue;
    seen.add(key);

    bps.push({
      wave,
      enemy_hp: enemyHp,
      current_hits: currentHits,
      current_hits_float: currentHitsFloat,
      target_hits: targetHits,
      current_atk: currentAtk,
      required_atk: requiredAtk,
      atk_increase: atkIncrease,
      time_saved_per_enemy: timeSavedPerEnemy,
      time_saved_per_wave: timeSavedPerEnemy * 5,
    });

    if (bps.length >= maxBreakpoints) break;
  }

  bps.sort((a, b) => (a.atk_increase as number) - (b.atk_increase as number));
  return bps.slice(0, maxBreakpoints);
}

export function calculateBreakpointEfficiency(
  breakpoints: Array<Record<string, number>>,
  player: PlayerStats,
  enemy: EnemyStats,
  targetWave: number,
): Array<Record<string, number>> {
  const out: Array<Record<string, number>> = [];
  for (const bp of breakpoints) {
    let totalTimeSaved = 0.0;
    let wavesAffected = 0;
    for (let wave = bp.wave as number; wave <= targetWave; wave += 1) {
      const enemyHp = getEnemyHpAtWave(enemy, wave);
      const currentHits = calculateHitsToKill(bp.current_atk as number, enemyHp);
      const newHits = calculateHitsToKill(bp.required_atk as number, enemyHp);
      if (newHits < currentHits) {
        const hitsSaved = currentHits - newHits;
        const timePerHit = 1.0 / (player.atkSpeed <= 0 ? 1 : player.atkSpeed);
        totalTimeSaved += hitsSaved * timePerHit * 5;
        wavesAffected += 1;
      }
    }
    const atkIncrease = bp.atk_increase as number;
    const efficiency = atkIncrease > 0 ? totalTimeSaved / atkIncrease : 0;
    out.push({ ...bp, total_time_saved: totalTimeSaved, waves_affected: wavesAffected, efficiency, target_wave: targetWave });
  }
  out.sort((a, b) => (b.efficiency as number) - (a.efficiency as number));
  return out;
}

