import {
  ENRAGE_CHARGES,
  ENRAGE_COOLDOWN,
  ENRAGE_CRIT_DAMAGE_BONUS,
  ENRAGE_DAMAGE_BONUS,
  FLURRY_COOLDOWN,
  FLURRY_STAMINA_BONUS,
  FRAGMENT_UPGRADES,
  GEM_UPGRADE_BONUSES,
  MOD_EXP_MULTIPLIER_AVG,
  MOD_LOOT_MULTIPLIER_AVG,
  MOD_SPEED_ATTACKS_AVG,
  MOD_STAMINA_BONUS_AVG,
  QUAKE_CHARGES,
  QUAKE_COOLDOWN,
  SKILL_BONUSES,
  SKILL_POINT_CAPS_BASE,
  SLOTS_PER_FLOOR,
  SUPER_CRIT_DMG_MULT_DEFAULT,
  ULTRA_CRIT_DMG_MULT_DEFAULT,
} from "./constants";
import { getBlockMixForFloor } from "./blockStats";
import { getNormalizedSpawnRates, getTotalSpawnProbability } from "./spawnRates";
import type { ArchBuild, ArchRunSummary, ArchStats, BlockTier, BlockType, Skill } from "./types";

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

export function getSkillPointCap(build: ArchBuild, skill: Skill): number {
  // "all_stat_cap" is +5 to all stat caps (max_level=1)
  const bonuses = getFragmentUpgradeBonuses(build.fragmentUpgradeLevels);
  const extra = Math.trunc(Number(bonuses.all_stat_cap ?? 0));
  return (SKILL_POINT_CAPS_BASE[skill] ?? 0) + extra;
}

export function getCalculationStage(build: ArchBuild): number {
  return Math.max(1, Math.trunc(build.goalStage) - 1);
}

export function getFragmentUpgradeBonuses(levels: Record<string, number>): Record<string, number> {
  const bonuses: Record<string, number> = {};
  for (const [upgradeKey, lvlRaw] of Object.entries(levels)) {
    const level = Math.trunc(Number(lvlRaw));
    if (level <= 0) continue;
    const info = FRAGMENT_UPGRADES[upgradeKey];
    if (!info) continue;
    for (const [k, v] of Object.entries(info)) {
      if (k === "max_level" || k === "stage_unlock" || k === "cost_type" || k === "display_name") continue;
      const n = Number(v);
      if (!Number.isFinite(n)) continue;
      bonuses[k] = (bonuses[k] ?? 0) + n * level;
    }
  }
  return bonuses;
}

export function getAbilityCooldownMultiplier(miscCardLevel: number): number {
  if (miscCardLevel === 1) return 0.97;
  if (miscCardLevel === 2) return 0.94;
  if (miscCardLevel === 3) return 0.9;
  return 1.0;
}

export function getAvadaKedaBonus(enabled: boolean): { duration_bonus: number; cooldown_reduction: number; instacharge_bonus: number } {
  if (enabled) return { duration_bonus: 5, cooldown_reduction: -10, instacharge_bonus: 0.03 };
  return { duration_bonus: 0, cooldown_reduction: 0, instacharge_bonus: 0.0 };
}

export function getBlockBonkerBonus(build: ArchBuild): { damage_percent: number; max_stamina_percent: number; speed_mod_gain: number; highest_stage: number } {
  if (!build.blockBonkerEnabled) return { damage_percent: 0, max_stamina_percent: 0, speed_mod_gain: 0, highest_stage: 0 };
  const highestStage = Math.min(Math.max(0, Math.trunc(build.goalStage) - 1), 100);
  return {
    damage_percent: highestStage * 0.01,
    max_stamina_percent: highestStage * 0.01,
    speed_mod_gain: highestStage,
    highest_stage: highestStage,
  };
}

export function getBlockCardLevel(build: ArchBuild, blockType: BlockType, tier: BlockTier): number {
  const k = `${blockType},${tier}`;
  return Math.trunc(Number(build.blockCards[k] ?? 0));
}

export function getBlockHpWithCard(build: ArchBuild, baseHp: number, blockType: BlockType, tier: BlockTier): number {
  const cardLevel = getBlockCardLevel(build, blockType, tier);
  if (cardLevel === 1) return Math.trunc(baseHp * 0.9);
  if (cardLevel === 2) return Math.trunc(baseHp * 0.8);
  if (cardLevel === 3) {
    const fragBonuses = getFragmentUpgradeBonuses(build.fragmentUpgradeLevels);
    const polyBonus = fragBonuses.polychrome_bonus ?? 0; // 0.15 when upgrade present
    const hpReduce = 0.35 + polyBonus; // 0.50 with upgrade
    return Math.trunc(baseHp * (1.0 - hpReduce));
  }
  return baseHp;
}

export function getBlockXpMultiplier(build: ArchBuild, blockType: BlockType, tier: BlockTier): number {
  const cardLevel = getBlockCardLevel(build, blockType, tier);
  if (cardLevel === 1) return 1.1;
  if (cardLevel === 2) return 1.2;
  if (cardLevel === 3) {
    const fragBonuses = getFragmentUpgradeBonuses(build.fragmentUpgradeLevels);
    const polyBonus = fragBonuses.polychrome_bonus ?? 0;
    const xpBonus = 0.35 + polyBonus;
    return 1.0 + xpBonus;
  }
  return 1.0;
}

export function calculateEffectiveDamage(stats: ArchStats, blockArmor: number): number {
  const effectiveArmor = Math.max(0, blockArmor - stats.armor_pen);
  return Math.max(1, Math.trunc(stats.total_damage - effectiveArmor));
}

export function getTotalStats(build: ArchBuild): ArchStats {
  const strPts = build.skillPoints.strength;
  const agiPts = build.skillPoints.agility;
  const intPts = build.skillPoints.intellect;
  const perPts = build.skillPoints.perception;
  const luckPts = build.skillPoints.luck;

  // Base state (matches reset_to_level1)
  const base_damage = 10;
  const base_armor_pen = 0;
  const base_stamina = 100;
  const base_crit_chance = 0.0;
  const base_crit_damage = 1.5;
  const base_xp_mult = 1.0;
  const base_fragment_mult = 1.0;

  const gem_stamina = build.gemUpgrades.stamina ?? 0;
  const gem_xp = build.gemUpgrades.xp ?? 0;
  const gem_fragment = build.gemUpgrades.fragment ?? 0;
  const gem_arch_xp = build.gemUpgrades.arch_xp ?? 0;

  const frag = getFragmentUpgradeBonuses(build.fragmentUpgradeLevels);
  const blockBonker = getBlockBonkerBonus(build);

  const flat_damage_per_str = (SKILL_BONUSES.strength.flat_damage ?? 0) + (frag.flat_damage_skill ?? 0);
  const percent_damage_per_str = (SKILL_BONUSES.strength.percent_damage ?? 0) + (frag.percent_damage_skill ?? 0);
  const flat_damage = base_damage + strPts * flat_damage_per_str + (frag.flat_damage ?? 0);
  let percent_damage_bonus = strPts * percent_damage_per_str + (frag.percent_damage ?? 0);
  percent_damage_bonus += blockBonker.damage_percent;
  const total_damage = Math.trunc(flat_damage * (1 + percent_damage_bonus));

  const armor_pen_per_per = (SKILL_BONUSES.perception.armor_pen ?? 0) + (frag.armor_pen_skill ?? 0);
  let armor_pen_base = base_armor_pen + perPts * armor_pen_per_per + (frag.armor_pen ?? 0);
  armor_pen_base = armor_pen_base * (1 + (frag.armor_pen_percent ?? 0));
  armor_pen_base = Math.round(armor_pen_base);
  const int_armor_pen_mult = 1 + intPts * (SKILL_BONUSES.intellect.armor_pen_mult ?? 0);
  const armor_pen = Math.round(armor_pen_base * int_armor_pen_mult);

  const max_stamina_per_agi = (SKILL_BONUSES.agility.max_stamina ?? 0) + (frag.max_stamina_skill ?? 0);
  let max_stamina =
    base_stamina +
    agiPts * max_stamina_per_agi +
    gem_stamina * (GEM_UPGRADE_BONUSES.stamina.max_stamina ?? 0) +
    (frag.max_stamina ?? 0);
  max_stamina = Math.trunc(max_stamina * (1 + (frag.max_stamina_percent ?? 0) + blockBonker.max_stamina_percent));

  const crit_chance = base_crit_chance + agiPts * (SKILL_BONUSES.agility.crit_chance ?? 0) + luckPts * (SKILL_BONUSES.luck.crit_chance ?? 0) + (frag.crit_chance ?? 0);
  const total_crit_mult = 1 + strPts * (SKILL_BONUSES.strength.crit_damage ?? 0) + (frag.crit_damage ?? 0);
  const crit_damage = base_crit_damage * total_crit_mult;
  const one_hit_chance = luckPts * (SKILL_BONUSES.luck.one_hit_chance ?? 0);

  const super_crit_chance = frag.super_crit_chance ?? 0;
  const super_crit_damage = frag.super_crit_damage ?? 0;
  const ultra_crit_chance = frag.ultra_crit_chance ?? 0;

  const super_crit_dmg_mult = SUPER_CRIT_DMG_MULT_DEFAULT * (1 + super_crit_damage);
  const ultra_crit_dmg_mult = ULTRA_CRIT_DMG_MULT_DEFAULT * (1 + super_crit_damage);

  let xp_mult_base = base_xp_mult + gem_xp * (GEM_UPGRADE_BONUSES.xp.xp_bonus ?? 0);
  if ((frag.xp_bonus_mult ?? 0) > 0) xp_mult_base *= frag.xp_bonus_mult ?? 1.0;
  const xp_bonus_per_int = (SKILL_BONUSES.intellect.xp_bonus ?? 0) + (frag.xp_bonus_skill ?? 0);
  const xp_mult = xp_mult_base * (1 + intPts * xp_bonus_per_int);

  let fragment_mult =
    base_fragment_mult + perPts * (SKILL_BONUSES.perception.fragment_gain ?? 0) + gem_fragment * (GEM_UPGRADE_BONUSES.fragment.fragment_gain ?? 0) + (frag.fragment_gain ?? 0);
  if ((frag.fragment_gain_mult ?? 0) > 0) fragment_mult *= frag.fragment_gain_mult ?? 1.0;

  const all_mod_bonus = luckPts * (SKILL_BONUSES.luck.all_mod_chance ?? 0) + (frag.all_mod_chance ?? 0);
  const mod_chance_skill_bonus = frag.mod_chance_skill ?? 0;

  const exp_mod_chance = intPts * (SKILL_BONUSES.intellect.exp_mod_chance ?? 0) + all_mod_bonus + mod_chance_skill_bonus + gem_xp * (GEM_UPGRADE_BONUSES.xp.exp_mod_chance ?? 0) + (frag.exp_mod_chance ?? 0);
  const loot_mod_chance = perPts * (SKILL_BONUSES.perception.loot_mod_chance ?? 0) + all_mod_bonus + mod_chance_skill_bonus + gem_fragment * (GEM_UPGRADE_BONUSES.fragment.loot_mod_chance ?? 0);
  const speed_mod_chance = agiPts * (SKILL_BONUSES.agility.speed_mod_chance ?? 0) + all_mod_bonus + mod_chance_skill_bonus;
  const stamina_mod_chance = all_mod_bonus + mod_chance_skill_bonus + gem_stamina * (GEM_UPGRADE_BONUSES.stamina.stamina_mod_chance ?? 0) + (frag.stamina_mod_chance ?? 0);

  const arch_xp_bonus_total = gem_arch_xp * (GEM_UPGRADE_BONUSES.arch_xp.arch_xp_bonus ?? 0) + (frag.arch_xp_bonus ?? 0);
  const arch_xp_mult = 1.0 + arch_xp_bonus_total;

  const loot_mod_multiplier = MOD_LOOT_MULTIPLIER_AVG + (frag.loot_mod_multiplier ?? 0);
  const exp_mod_gain = MOD_EXP_MULTIPLIER_AVG + (frag.exp_mod_gain ?? 0);
  const stamina_mod_gain = MOD_STAMINA_BONUS_AVG + (frag.stamina_mod_gain ?? 0);

  const avada = getAvadaKedaBonus(build.avadaKedaEnabled);
  const enrage_damage_bonus = ENRAGE_DAMAGE_BONUS + (frag.enrage_damage ?? 0);
  const enrage_crit_damage_bonus = ENRAGE_CRIT_DAMAGE_BONUS + (frag.enrage_crit_damage ?? 0);
  const quake_charges = QUAKE_CHARGES + (frag.quake_attacks ?? 0) + avada.duration_bonus;
  const ability_instacharge = (frag.ability_instacharge ?? 0) + avada.instacharge_bonus;

  return {
    flat_damage,
    total_damage,
    armor_pen,
    max_stamina,
    crit_chance: clamp01(crit_chance),
    crit_damage,
    super_crit_chance: clamp01(super_crit_chance),
    super_crit_damage,
    ultra_crit_chance: clamp01(ultra_crit_chance),
    super_crit_dmg_mult,
    ultra_crit_dmg_mult,
    one_hit_chance: clamp01(one_hit_chance),
    xp_mult,
    xp_gain_total: xp_mult * arch_xp_mult,
    fragment_mult,
    exp_mod_chance: clamp01(exp_mod_chance),
    loot_mod_chance: clamp01(loot_mod_chance),
    speed_mod_chance: clamp01(speed_mod_chance),
    stamina_mod_chance: clamp01(stamina_mod_chance),
    loot_mod_multiplier,
    exp_mod_gain,
    stamina_mod_gain,
    speed_mod_gain: blockBonker.speed_mod_gain,
    arch_xp_mult,
    enrage_damage_bonus,
    enrage_crit_damage_bonus,
    misc_card_level: build.miscCardLevel ?? 0,
    enrage_cooldown: frag.enrage_cooldown ?? 0,
    flurry_cooldown: frag.flurry_cooldown ?? 0,
    quake_cooldown: frag.quake_cooldown ?? 0,
    ability_cooldown: (frag.ability_cooldown ?? 0) + avada.cooldown_reduction,
    avada_keda_duration_bonus: avada.duration_bonus,
    flurry_stamina_bonus: (frag.flurry_stamina ?? 0) + avada.duration_bonus,
    quake_charges,
    ability_instacharge,
  };
}

export function calculateHitsToKill(build: ArchBuild, stats: ArchStats, blockHpBase: number, blockArmor: number, blockType: BlockType, tier: BlockTier): number {
  const blockHp = getBlockHpWithCard(build, blockHpBase, blockType, tier);
  const effectiveDmgBase = calculateEffectiveDamage(stats, blockArmor);

  const critChance = stats.crit_chance;
  const critDamage = stats.crit_damage;
  const superCritChance = stats.super_crit_chance;
  const superCritDamage = stats.super_crit_damage;
  const ultraCritChance = stats.ultra_crit_chance;
  const oneHitChance = stats.one_hit_chance;

  function avgDmgWithCrits(baseDmg: number, critDmgMult: number): number {
    const sc = clamp01(superCritChance);
    const uc = clamp01(ultraCritChance);
    const cd = Math.max(0, superCritDamage);
    const superMult = SUPER_CRIT_DMG_MULT_DEFAULT * (1 + cd);
    const ultraMult = ULTRA_CRIT_DMG_MULT_DEFAULT * (1 + cd);
    const critMultExpected = (1 - sc) * critDmgMult + sc * ((1 - uc) * critDmgMult * superMult + uc * critDmgMult * ultraMult);
    return baseDmg * ((1 - critChance) + critChance * critMultExpected);
  }

  let avgDmgPerHit = avgDmgWithCrits(effectiveDmgBase, critDamage);

  if (build.enrageEnabled) {
    const frag = getFragmentUpgradeBonuses(build.fragmentUpgradeLevels);
    const avada = getAvadaKedaBonus(build.avadaKedaEnabled);
    const baseCooldown = ENRAGE_COOLDOWN + (frag.enrage_cooldown ?? 0) + (frag.ability_cooldown ?? 0) + avada.cooldown_reduction;
    const effectiveCooldown = baseCooldown * getAbilityCooldownMultiplier(build.miscCardLevel ?? 0);
    const effectiveCharges = ENRAGE_CHARGES + avada.duration_bonus;
    const enrageProportion = effectiveCooldown > 0 ? effectiveCharges / effectiveCooldown : 0;
    const normalProportion = 1 - enrageProportion;

    const enrageTotalDamage = Math.trunc(stats.total_damage * (1 + stats.enrage_damage_bonus));
    const effectiveArmor = Math.max(0, blockArmor - stats.armor_pen);
    const effectiveDmgEnrage = Math.max(1, enrageTotalDamage - effectiveArmor);

    const enrageCritDamage = critDamage * (1 + stats.enrage_crit_damage_bonus);
    const avgNormal = avgDmgWithCrits(effectiveDmgBase, critDamage);
    const avgEnrage = avgDmgWithCrits(effectiveDmgEnrage, enrageCritDamage);
    avgDmgPerHit = normalProportion * avgNormal + enrageProportion * avgEnrage;
  }

  const hitsWithoutOneHit = blockHp / avgDmgPerHit;
  let expectedHits = hitsWithoutOneHit;
  if (oneHitChance > 0) {
    const expectedHitsToOneHit = 1 / oneHitChance;
    expectedHits = Math.min(expectedHitsToOneHit, hitsWithoutOneHit);
  }
  return expectedHits;
}

export function calculateFloorsPerRun(build: ArchBuild, stats: ArchStats, startingFloor: number): number {
  const maxStamina = stats.max_stamina;
  let staminaRemaining = maxStamina;
  let floorsCleared = 0;
  let currentFloor = startingFloor;

  const staminaModChance = stats.stamina_mod_chance ?? 0;
  const staminaModGain = stats.stamina_mod_gain ?? MOD_STAMINA_BONUS_AVG;
  let avgStaminaPerBlock = staminaModChance * staminaModGain;

  // Flurry stamina approximation (same as Python)
  if (build.flurryEnabled) {
    const frag = getFragmentUpgradeBonuses(build.fragmentUpgradeLevels);
    const avada = getAvadaKedaBonus(build.avadaKedaEnabled);
    const staminaOnCast = FLURRY_STAMINA_BONUS + (frag.flurry_stamina ?? 0) + avada.duration_bonus;
    const baseCooldown = FLURRY_COOLDOWN + (frag.flurry_cooldown ?? 0) + (frag.ability_cooldown ?? 0) + avada.cooldown_reduction;
    const effectiveCooldown = Math.trunc(baseCooldown * getAbilityCooldownMultiplier(build.miscCardLevel ?? 0));
    const flurryStaminaPerHit = effectiveCooldown > 0 ? staminaOnCast / effectiveCooldown : 0;
    avgStaminaPerBlock += flurryStaminaPerHit;
  }

  for (let i = 0; i < 100; i += 1) {
    const spawnRates = getNormalizedSpawnRates(currentFloor);
    const blockMix = getBlockMixForFloor(currentFloor);

    const totalSpawnProb = getTotalSpawnProbability(currentFloor);
    const expectedBlocks = SLOTS_PER_FLOOR * (totalSpawnProb / 100.0);
    const floorBlocks = expectedBlocks;

    let avgHitsPerBlock = 0;
    for (const [blockTypeRaw, spawnChanceRaw] of Object.entries(spawnRates)) {
      const blockType = blockTypeRaw as BlockType;
      const spawnChance = Number(spawnChanceRaw);
      if (spawnChance <= 0) continue;
      const blockData = (blockMix as any)[blockType] as { health: number; armor: number; tier: BlockTier } | undefined;
      if (!blockData) continue;
      const hits = calculateHitsToKill(build, stats, blockData.health, blockData.armor, blockType, blockData.tier);
      avgHitsPerBlock += spawnChance * hits;
    }

    const netStaminaPerBlock = Math.max(0.1, avgHitsPerBlock - avgStaminaPerBlock);
    const staminaForFloor = netStaminaPerBlock * floorBlocks;

    if (staminaRemaining >= staminaForFloor) {
      staminaRemaining -= staminaForFloor;
      floorsCleared += 1;
      currentFloor += 1;
    } else {
      if (staminaForFloor > 0) floorsCleared += staminaRemaining / staminaForFloor;
      break;
    }
  }

  return floorsCleared;
}

export function calculateXpPerRun(build: ArchBuild, stats: ArchStats, startingFloor: number): number {
  const floors = calculateFloorsPerRun(build, stats, startingFloor);
  if (floors <= 0) return 0;

  const xpMult = stats.xp_mult;
  const archXpMult = stats.arch_xp_mult ?? 1.0;
  const expModChance = stats.exp_mod_chance ?? 0;
  const expModGain = stats.exp_mod_gain ?? 0;

  const expModMultiplier = MOD_EXP_MULTIPLIER_AVG + expModGain;
  const expModFactor = 1 + expModChance * (expModMultiplier - 1);

  let totalXp = 0;
  let currentFloor = startingFloor;
  const floorsToProcess = Math.trunc(floors);
  const partial = floors - floorsToProcess;

  for (let i = 0; i < floorsToProcess + 1; i += 1) {
    const floorMult = i === floorsToProcess ? partial : 1.0;
    if (floorMult <= 0) break;

    const spawnRates = getNormalizedSpawnRates(currentFloor);
    const blockMix = getBlockMixForFloor(currentFloor);
    const totalSpawnProb = getTotalSpawnProbability(currentFloor);
    const expectedBlocks = SLOTS_PER_FLOOR * (totalSpawnProb / 100.0);

    let floorXp = 0;
    for (const [blockTypeRaw, spawnChanceRaw] of Object.entries(spawnRates)) {
      const blockType = blockTypeRaw as BlockType;
      const spawnChance = Number(spawnChanceRaw);
      if (spawnChance <= 0) continue;
      const blockData = (blockMix as any)[blockType] as { xp: number; tier: BlockTier } | undefined;
      if (!blockData) continue;
      let blockXp = blockData.xp;
      blockXp *= getBlockXpMultiplier(build, blockType, blockData.tier);
      floorXp += spawnChance * blockXp;
    }

    totalXp += expectedBlocks * floorXp * xpMult * archXpMult * expModFactor * floorMult;
    currentFloor += 1;
  }

  return totalXp;
}

export function calculateFragmentsPerRun(build: ArchBuild, stats: ArchStats, startingFloor: number): Record<Exclude<BlockType, "dirt">, number> {
  const floors = calculateFloorsPerRun(build, stats, startingFloor);
  const out: Record<Exclude<BlockType, "dirt">, number> = { common: 0, rare: 0, epic: 0, legendary: 0, mythic: 0 };
  if (floors <= 0) return out;

  const fragmentMult = stats.fragment_mult;
  const lootModChance = stats.loot_mod_chance ?? 0;
  const lootModMultiplier = stats.loot_mod_multiplier ?? MOD_LOOT_MULTIPLIER_AVG;
  const lootModFactor = 1 + lootModChance * (lootModMultiplier - 1);

  let currentFloor = startingFloor;
  const floorsToProcess = Math.trunc(floors);
  const partial = floors - floorsToProcess;

  for (let i = 0; i < floorsToProcess + 1; i += 1) {
    const floorMult = i === floorsToProcess ? partial : 1.0;
    if (floorMult <= 0) break;

    const spawnRates = getNormalizedSpawnRates(currentFloor);
    const blockMix = getBlockMixForFloor(currentFloor);
    const totalSpawnProb = getTotalSpawnProbability(currentFloor);
    const expectedBlocks = SLOTS_PER_FLOOR * (totalSpawnProb / 100.0);

    for (const [blockTypeRaw, spawnChanceRaw] of Object.entries(spawnRates)) {
      const blockType = blockTypeRaw as BlockType;
      const spawnChance = Number(spawnChanceRaw);
      if (spawnChance <= 0 || blockType === "dirt") continue;
      const blockData = (blockMix as any)[blockType] as { fragment: number } | undefined;
      if (!blockData) continue;
      const baseFrag = blockData.fragment;
      const fragGain = expectedBlocks * spawnChance * baseFrag * fragmentMult * lootModFactor * floorMult;
      out[blockType] += fragGain;
    }

    currentFloor += 1;
  }

  return out;
}

export function calculateRunDurationSeconds(build: ArchBuild, stats: ArchStats, startingFloor: number): number {
  let totalHits = stats.max_stamina;

  const blocksPerRun = calculateBlocksPerRun(build, stats, startingFloor);
  const frag = getFragmentUpgradeBonuses(build.fragmentUpgradeLevels);
  const staminaModChance = stats.stamina_mod_chance ?? 0;
  const staminaModGain = MOD_STAMINA_BONUS_AVG + (frag.stamina_mod_gain ?? 0);
  const avgStaminaFromMod = blocksPerRun * staminaModChance * staminaModGain;
  totalHits += avgStaminaFromMod;

  if (build.flurryEnabled) {
    const avada = getAvadaKedaBonus(build.avadaKedaEnabled);
    const baseFlurryCooldown = FLURRY_COOLDOWN + (frag.flurry_cooldown ?? 0) + (frag.ability_cooldown ?? 0) + avada.cooldown_reduction;
    const flurryCooldown = Math.trunc(baseFlurryCooldown * getAbilityCooldownMultiplier(build.miscCardLevel ?? 0));
    const flurryStamina = FLURRY_STAMINA_BONUS + (frag.flurry_stamina ?? 0) + avada.duration_bonus;
    const baseDuration = totalHits;
    const activations = flurryCooldown > 0 ? baseDuration / flurryCooldown : 0;
    totalHits += activations * flurryStamina;
  }

  const baseDurationSeconds = totalHits;
  const speedModChance = stats.speed_mod_chance ?? 0;
  const speedHitsAvg = MOD_SPEED_ATTACKS_AVG + (stats.speed_mod_gain ?? 0);
  const speedModHits = blocksPerRun * speedModChance * speedHitsAvg;
  const timeSavedFromSpeedMod = speedModHits * 0.5;

  let flurryTimeSaved = 0;
  if (build.flurryEnabled) {
    const avada = getAvadaKedaBonus(build.avadaKedaEnabled);
    const baseFlurryCooldown = FLURRY_COOLDOWN + (frag.flurry_cooldown ?? 0) + (frag.ability_cooldown ?? 0) + avada.cooldown_reduction;
    const flurryCooldown = Math.trunc(baseFlurryCooldown * getAbilityCooldownMultiplier(build.miscCardLevel ?? 0));
    const activations = flurryCooldown > 0 ? baseDurationSeconds / flurryCooldown : 0;
    flurryTimeSaved = activations * 5; // Python approximation
  }

  const runDuration = baseDurationSeconds - timeSavedFromSpeedMod - flurryTimeSaved;
  return Math.max(10, runDuration);
}

export function calculateBlocksPerRun(build: ArchBuild, stats: ArchStats, floor: number): number {
  const maxStamina = stats.max_stamina;
  const spawnRates = getNormalizedSpawnRates(floor);
  const blockMix = getBlockMixForFloor(floor);

  let weightedHits = 0;
  for (const [btRaw, spawnChanceRaw] of Object.entries(spawnRates)) {
    const bt = btRaw as BlockType;
    const spawnChance = Number(spawnChanceRaw);
    if (spawnChance <= 0) continue;
    const blockData = (blockMix as any)[bt] as { health: number; armor: number; tier: BlockTier } | undefined;
    if (!blockData) continue;
    const hits = calculateHitsToKill(build, stats, blockData.health, blockData.armor, bt, blockData.tier);
    weightedHits += spawnChance * hits;
  }
  if (weightedHits > 0) return maxStamina / weightedHits;
  return 0;
}

export function computeRunSummary(build: ArchBuild): { stats: ArchStats; summary: ArchRunSummary } {
  const stats = getTotalStats(build);
  const calcStage = getCalculationStage(build);
  const floorsPerRun = calculateFloorsPerRun(build, stats, calcStage);
  const xpPerRun = calculateXpPerRun(build, stats, calcStage);
  const frags = calculateFragmentsPerRun(build, stats, calcStage);
  const durationSeconds = calculateRunDurationSeconds(build, stats, calcStage);
  const totalFrags = Object.values(frags).reduce((a, b) => a + b, 0);
  const fragmentsPerHour = durationSeconds > 0 ? totalFrags * (3600.0 / durationSeconds) : 0;
  return { stats, summary: { floorsPerRun, xpPerRun, fragmentsPerRun: frags, durationSeconds, fragmentsPerHour } };
}

