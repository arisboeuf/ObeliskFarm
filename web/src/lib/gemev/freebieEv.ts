// Ported from ObeliskGemEV/freebie_ev_calculator.py (Gem EV + Gift EV).
//
// Intent: match desktop math 1:1 (including the bomb refill recursion).
// Keep this file pure (no DOM / localStorage).
//
// NOTE: User-facing text should live in the React module; keep this file logic-only.
export type GameParameters = {
  // Base freebie parameters
  freebie_gems_base: number;
  freebie_timer_minutes: number;
  freebie_claim_percentage: number; // 0..100

  // Skill shards
  skill_shard_chance: number; // 0..1
  skill_shard_value_gems: number;

  // Stonks
  stonks_chance: number; // 0..1
  stonks_bonus_gems: number;

  // Jackpot
  jackpot_chance: number; // 0..1
  jackpot_rolls: number; // int

  // Refresh
  instant_refresh_chance: number; // 0..1

  // Founder supply drop
  vip_lounge_level: number; // 1..7
  founder_gems_base: number; // fixed 10.0 in desktop
  founder_gems_chance: number; // fixed 0.01 in desktop
  obelisk_level: number;
  founder_speed_multiplier: number; // fixed 2.0 in desktop
  founder_speed_duration_minutes: number; // fixed 5.0 in desktop

  // Bombs - general
  free_bomb_chance: number; // 0..1
  total_bomb_types: number; // int (default 12)

  // Recharge cards (0 none, 1 card, 2 gilded, 3 polychrome)
  gem_bomb_recharge_card_level: number;
  cherry_bomb_recharge_card_level: number;
  battery_bomb_recharge_card_level: number;
  d20_bomb_recharge_card_level: number;
  founder_bomb_recharge_card_level: number;

  // Gem Bomb
  gem_bomb_recharge_seconds: number;
  gem_bomb_gem_chance: number; // 0..1

  // Cherry Bomb
  cherry_bomb_recharge_seconds: number;
  cherry_bomb_triple_charge_chance: number; // 0..1

  // Battery Bomb
  battery_bomb_recharge_seconds: number;
  battery_bomb_charges_per_charge: number; // fixed 2.0 in desktop
  battery_bomb_cap_increase_chance: number; // fixed 0.001 in desktop (tooltip only)

  // D20 Bomb
  d20_bomb_recharge_seconds: number;
  d20_bomb_refill_chance: number; // 0..1
  d20_bomb_charges_distributed: number; // int

  // Founder Bomb
  founder_bomb_interval_seconds: number;
  founder_bomb_charges_per_drop: number; // fixed 2.0 in desktop
  founder_bomb_speed_chance: number; // 0..1
  founder_bomb_speed_multiplier: number;
  founder_bomb_speed_duration_seconds: number;
};

export function defaultGameParameters(): GameParameters {
  return {
    freebie_gems_base: 9.0,
    freebie_timer_minutes: 7.0,
    freebie_claim_percentage: 100.0,
    skill_shard_chance: 0.12,
    skill_shard_value_gems: 12.5,
    stonks_chance: 0.01,
    stonks_bonus_gems: 200.0,
    jackpot_chance: 0.08, // 5% + 3%
    jackpot_rolls: 5,
    instant_refresh_chance: 0.05,
    vip_lounge_level: 3,
    founder_gems_base: 10.0,
    founder_gems_chance: 0.01,
    obelisk_level: 29,
    founder_speed_multiplier: 2.0,
    founder_speed_duration_minutes: 5.0,
    free_bomb_chance: 0.16,
    total_bomb_types: 12,
    gem_bomb_recharge_card_level: 0,
    cherry_bomb_recharge_card_level: 0,
    battery_bomb_recharge_card_level: 0,
    d20_bomb_recharge_card_level: 0,
    founder_bomb_recharge_card_level: 0,
    gem_bomb_recharge_seconds: 46.0,
    gem_bomb_gem_chance: 0.03,
    cherry_bomb_recharge_seconds: 48.0,
    cherry_bomb_triple_charge_chance: 0.0,
    battery_bomb_recharge_seconds: 31.0,
    battery_bomb_charges_per_charge: 2.0,
    battery_bomb_cap_increase_chance: 0.001,
    d20_bomb_recharge_seconds: 36.0,
    d20_bomb_refill_chance: 0.05,
    d20_bomb_charges_distributed: 42,
    founder_bomb_interval_seconds: 87.0,
    founder_bomb_charges_per_drop: 2.0,
    founder_bomb_speed_chance: 0.10,
    founder_bomb_speed_multiplier: 2.0,
    founder_bomb_speed_duration_seconds: 10.0,
  };
}

function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, x));
}

function clampPositive(x: number, fallback = 0): number {
  if (!Number.isFinite(x)) return fallback;
  return Math.max(0, x);
}

function clampInt(x: number, fallback = 0): number {
  if (!Number.isFinite(x)) return fallback;
  return Math.trunc(x);
}

function rechargeChargeMultiplier(cardLevel: number): number {
  // Matches FreebieEVCalculator._get_recharge_charge_multiplier
  const lvl = clampInt(cardLevel, 0);
  if (lvl === 1) return 1.5;
  if (lvl === 2) return 2.0;
  if (lvl === 3) return 3.0;
  return 1.0;
}

export function getFounderDropIntervalMinutes(params: GameParameters): number {
  return 60.0 - 2.0 * (clampInt(params.vip_lounge_level, 3) - 1);
}

export function getDoubleDropChance(params: GameParameters): number {
  const lvl = clampInt(params.vip_lounge_level, 3);
  if (lvl < 2) return 0.0;
  return 0.12 + 0.06 * (lvl - 2);
}

export function getTripleDropChance(params: GameParameters): number {
  const lvl = clampInt(params.vip_lounge_level, 3);
  return lvl >= 7 ? 0.16 : 0.0;
}

export function calculateExpectedRollsPerClaim(params: GameParameters): number {
  const normalRolls = 1.0;
  const jackpotRolls = clampPositive(params.jackpot_rolls, 5);
  const pJackpot = clamp01(params.jackpot_chance);
  return (1 - pJackpot) * normalRolls + pJackpot * jackpotRolls;
}

export function calculateRefreshMultiplier(params: GameParameters): number {
  const p = clamp01(params.instant_refresh_chance);
  if (p >= 1.0) return Number.POSITIVE_INFINITY;
  return 1.0 / (1.0 - p);
}

export function calculateTotalMultiplier(params: GameParameters): number {
  return calculateExpectedRollsPerClaim(params) * calculateRefreshMultiplier(params);
}

export function calculateFreebiesPerHour(params: GameParameters): number {
  const minutesPerHour = 60.0;
  const timer = clampPositive(params.freebie_timer_minutes, 7.0);
  const base = minutesPerHour / timer;
  const claim = clampPositive(params.freebie_claim_percentage, 100.0);
  return base * (claim / 100.0);
}

export function calculateGemsBasePerHour(params: GameParameters): number {
  const freebiesPerHour = calculateFreebiesPerHour(params);
  const expectedRolls = calculateExpectedRollsPerClaim(params);
  const refreshMult = calculateRefreshMultiplier(params);
  return freebiesPerHour * refreshMult * expectedRolls * clampPositive(params.freebie_gems_base, 9.0);
}

export function calculateStonksEvPerHour(params: GameParameters): number {
  const freebiesPerHour = calculateFreebiesPerHour(params);
  const refreshMult = calculateRefreshMultiplier(params);
  const stonksEvPerClaim = clamp01(params.stonks_chance) * clampPositive(params.stonks_bonus_gems, 200.0);
  return freebiesPerHour * refreshMult * stonksEvPerClaim;
}

export function calculateSkillShardsEvPerHour(params: GameParameters): number {
  const freebiesPerHour = calculateFreebiesPerHour(params);
  const expectedRolls = calculateExpectedRollsPerClaim(params);
  const refreshMult = calculateRefreshMultiplier(params);
  return (
    freebiesPerHour *
    refreshMult *
    expectedRolls *
    clamp01(params.skill_shard_chance) *
    clampPositive(params.skill_shard_value_gems, 12.5)
  );
}

export function calculateFounderSpeedBoostPerHour(params: GameParameters): number {
  const founderDropInterval = getFounderDropIntervalMinutes(params);
  const founderDropsPerHour = 60.0 / founderDropInterval;

  const doubleChance = clamp01(getDoubleDropChance(params));
  const tripleChance = clamp01(getTripleDropChance(params));
  const singleChance = 1.0 - doubleChance - tripleChance;

  const expectedDropsPerEvent = 1.0 * singleChance + 2.0 * doubleChance + 3.0 * tripleChance;
  const expectedDurationMinutes = expectedDropsPerEvent * clampPositive(params.founder_speed_duration_minutes, 5.0);
  const speedMult = clampPositive(params.founder_speed_multiplier, 2.0);

  const timeSavedPerEvent = expectedDurationMinutes / speedMult;
  const timeSavedPerHour = founderDropsPerHour * timeSavedPerEvent;
  const effectiveMinutesPerHour = 60.0 - timeSavedPerHour;

  const normalFreebiesPerHour = calculateFreebiesPerHour(params);
  const baseEffectiveFreebiesPerHour = 60.0 / (clampPositive(params.freebie_timer_minutes, 7.0) * (effectiveMinutesPerHour / 60.0));
  const claim = clampPositive(params.freebie_claim_percentage, 100.0);
  const effectiveFreebiesPerHour = baseEffectiveFreebiesPerHour * (claim / 100.0);
  const additionalFreebies = effectiveFreebiesPerHour - normalFreebiesPerHour;

  const expectedRolls = calculateExpectedRollsPerClaim(params);
  const refreshMult = calculateRefreshMultiplier(params);
  return additionalFreebies * refreshMult * expectedRolls * clampPositive(params.freebie_gems_base, 9.0);
}

export function calculateObeliskMultiplier(params: GameParameters): number {
  return 1.0 + clampPositive(params.obelisk_level, 29) * 0.08;
}

export function calculateLuckyMultiplier(): number {
  // Matches python: two independent rolls (1/20 for 3x, 1/2500 for 50x)
  const neither = (19 / 20) * (2499 / 2500);
  const threeX = (1 / 20) * (2499 / 2500);
  const fiftyX = (19 / 20) * (1 / 2500);
  const both = (1 / 20) * (1 / 2500);
  return neither * 1.0 + threeX * 3.0 + fiftyX * 50.0 + both * 150.0;
}

export function convertTimeBoostToGemEquivalent(params: GameParameters, minutes2xSpeed: number): number {
  // Matches python convert_time_boost_to_gem_equivalent (simplified: treat minutes as time saved).
  const timeSavedMinutes = clampPositive(minutes2xSpeed, 0);
  const timeSavedHours = timeSavedMinutes / 60.0;
  const additionalFreebies = timeSavedHours * (60.0 / clampPositive(params.freebie_timer_minutes, 7.0));
  const expectedRolls = calculateExpectedRollsPerClaim(params);
  const refreshMult = calculateRefreshMultiplier(params);
  return additionalFreebies * refreshMult * expectedRolls * clampPositive(params.freebie_gems_base, 9.0);
}

export function calculateGiftEvPerGift(params: GameParameters): number {
  const obeliskMult = calculateObeliskMultiplier(params);
  const luckyMult = calculateLuckyMultiplier();
  const skillShardValue = clampPositive(params.skill_shard_value_gems, 12.5);

  // 1) Base roll EV (pre multipliers)
  const gems20_40 = 30.0;
  const gems30_65 = 47.5;
  const skillShardsBase = 3.5;
  const blueCowsBase = 3.0;
  const minutesPerBlueCow = 16.0;
  const speedMinutesBase = 32.5;
  const chancePerItem = 1.0 / 12.0;

  const baseRollGems = chancePerItem * (gems20_40 + gems30_65);
  const baseRollShards = chancePerItem * skillShardsBase * skillShardValue;
  const baseRollBlueCowMinutes = chancePerItem * blueCowsBase * minutesPerBlueCow;
  const baseRollSpeedMinutes = chancePerItem * speedMinutesBase;
  void 0; // keep alignment with python structure

  const baseRollTimeBoostGems =
    convertTimeBoostToGemEquivalent(params, baseRollBlueCowMinutes) + convertTimeBoostToGemEquivalent(params, baseRollSpeedMinutes);
  const baseRollEv = baseRollGems + baseRollShards + baseRollTimeBoostGems;
  void baseRollEv;

  // 2) Rare rolls (subset used by desktop):
  // 1/40: 3 gifts (recursive)
  const rareGifts3Chance = 1 / 40;
  // 1/45: 80-130 gems (avg 105), only if 3 gifts didn't trigger: (39/40)*(1/45)
  const rareGemsChance = (39 / 40) * (1 / 45);
  const rareGemsAvg = 105.0;
  const rareRollGemsEv = rareGemsChance * rareGemsAvg;

  // 3) Apply multipliers (Base -> Obelisk -> Lucky)
  const baseGemsWithMult = baseRollGems * obeliskMult * luckyMult;
  const baseShardsWithMult = baseRollShards * obeliskMult * luckyMult;

  const baseBlueCowMinutesMult = baseRollBlueCowMinutes * obeliskMult * luckyMult;
  const baseSpeedMinutesMult = baseRollSpeedMinutes * obeliskMult * luckyMult;
  const baseTimeBoostGemsMult =
    convertTimeBoostToGemEquivalent(params, baseBlueCowMinutesMult) + convertTimeBoostToGemEquivalent(params, baseSpeedMinutesMult);

  const rareGemsWithMult = rareRollGemsEv * obeliskMult * luckyMult;

  // 4) Solve recursion: GiftEV = A + B * GiftEV
  const A = baseGemsWithMult + baseShardsWithMult + baseTimeBoostGemsMult + rareGemsWithMult;
  const recursiveCoeff = rareGifts3Chance * 3.0 * obeliskMult * luckyMult;
  if (recursiveCoeff >= 1.0) return A * 10.0; // matches desktop fallback
  return A / (1.0 - recursiveCoeff);
}

export function calculateGiftEvBreakdown(params: GameParameters): Record<string, number> {
  const obeliskMult = calculateObeliskMultiplier(params);
  const luckyMult = calculateLuckyMultiplier();
  const skillShardValue = clampPositive(params.skill_shard_value_gems, 12.5);
  const chancePerItem = 1.0 / 12.0;

  const gems20_40 = 30.0;
  const gems30_65 = 47.5;
  const skillShardsBase = 3.5;
  const blueCowsBase = 3.0;
  const minutesPerBlueCow = 16.0;
  const speedMinutesBase = 32.5;

  const gems20_40_base = chancePerItem * gems20_40;
  const gems30_65_base = chancePerItem * gems30_65;
  const skillShardsBaseEv = chancePerItem * skillShardsBase * skillShardValue;
  const blueCowMinutesBase = chancePerItem * blueCowsBase * minutesPerBlueCow;
  const speedMinutesBaseEv = chancePerItem * speedMinutesBase;

  const gems20_40_final = gems20_40_base * obeliskMult * luckyMult;
  const gems30_65_final = gems30_65_base * obeliskMult * luckyMult;
  const skillShards_final = skillShardsBaseEv * obeliskMult * luckyMult;

  const blueCowMinutes_final = blueCowMinutesBase * obeliskMult * luckyMult;
  const speedMinutes_final = speedMinutesBaseEv * obeliskMult * luckyMult;
  const blueCowGems_final = convertTimeBoostToGemEquivalent(params, blueCowMinutes_final);
  const speedGems_final = convertTimeBoostToGemEquivalent(params, speedMinutes_final);

  const rareGemsChance = (39 / 40) * (1 / 45);
  const rareGemsAvg = 105.0;
  const rareGems_final = rareGemsChance * rareGemsAvg * obeliskMult * luckyMult;

  const giftEvTotal = calculateGiftEvPerGift(params);
  const A =
    gems20_40_final +
    gems30_65_final +
    skillShards_final +
    blueCowGems_final +
    speedGems_final +
    rareGems_final;
  const recursiveGiftsContribution = giftEvTotal - A;

  return {
    gems_20_40: gems20_40_final,
    gems_30_65: gems30_65_final,
    skill_shards: skillShards_final,
    blue_cow: blueCowGems_final,
    speed_boost: speedGems_final,
    rare_gems: rareGems_final,
    recursive_gifts: recursiveGiftsContribution,
    total: giftEvTotal,
  };
}

export function calculateFounderGemsPerHour(params: GameParameters): number {
  const founderDropInterval = getFounderDropIntervalMinutes(params);
  const founderDropsPerHour = 60.0 / founderDropInterval;

  const doubleChance = clamp01(getDoubleDropChance(params));
  const tripleChance = clamp01(getTripleDropChance(params));
  const singleChance = 1.0 - doubleChance - tripleChance;
  const expectedDropsPerEvent = 1.0 * singleChance + 2.0 * doubleChance + 3.0 * tripleChance;

  const baseGems = founderDropsPerHour * expectedDropsPerEvent * clampPositive(params.founder_gems_base, 10.0);
  const bonusGemsPerDrop = 50.0 + 10.0 * clampPositive(params.obelisk_level, 29);
  const bonusGems =
    founderDropsPerHour * expectedDropsPerEvent * clamp01(params.founder_gems_chance) * bonusGemsPerDrop;

  const giftChance = 1.0 / 1234.0;
  const giftsPerDrop = 10.0;
  const giftEvPerGift = calculateGiftEvPerGift(params);
  const giftGems = founderDropsPerHour * giftChance * giftsPerDrop * giftEvPerGift;

  return baseGems + bonusGems + giftGems;
}

export function calculateGemBombGemsPerHour(params: GameParameters): number {
  const secondsPerHour = 3600.0;

  // Founder speed uptime fraction (minutes with 2x speed per hour)
  const founderDropInterval = getFounderDropIntervalMinutes(params);
  const founderDropsPerHour = 60.0 / founderDropInterval;

  const doubleChance = clamp01(getDoubleDropChance(params));
  const tripleChance = clamp01(getTripleDropChance(params));
  const singleChance = 1.0 - doubleChance - tripleChance;
  const expectedDropsPerEvent = 1.0 * singleChance + 2.0 * doubleChance + 3.0 * tripleChance;

  const speedMinutesPerHour = founderDropsPerHour * expectedDropsPerEvent * clampPositive(params.founder_speed_duration_minutes, 5.0);
  const speedPct = clamp01(speedMinutesPerHour / 60.0);

  // Weighted effective recharge times (base time for (1-speedPct), half time for speedPct)
  function effectiveRecharge(baseSeconds: number): number {
    const s = clampPositive(baseSeconds, 1);
    return s * (1.0 - speedPct) + (s / 2.0) * speedPct;
  }

  const effGem = effectiveRecharge(params.gem_bomb_recharge_seconds);
  const effCherry = effectiveRecharge(params.cherry_bomb_recharge_seconds);
  const effBattery = effectiveRecharge(params.battery_bomb_recharge_seconds);
  const effD20 = effectiveRecharge(params.d20_bomb_recharge_seconds);

  const freeBombMult = 1.0 / (1.0 - clamp01(params.free_bomb_chance));

  const gemMult = rechargeChargeMultiplier(params.gem_bomb_recharge_card_level);
  const cherryMult = rechargeChargeMultiplier(params.cherry_bomb_recharge_card_level);
  const batteryMult = rechargeChargeMultiplier(params.battery_bomb_recharge_card_level);
  const d20Mult = rechargeChargeMultiplier(params.d20_bomb_recharge_card_level);

  const gemClicksBase = (secondsPerHour / effGem) * gemMult;
  const cherryClicksBase = (secondsPerHour / effCherry) * cherryMult;
  const batteryClicksBase = (secondsPerHour / effBattery) * batteryMult;
  const d20ClicksBase = (secondsPerHour / effD20) * d20Mult;

  const gemClicks0 = gemClicksBase * freeBombMult;
  const cherryClicks0 = cherryClicksBase * freeBombMult;
  const batteryClicks0 = batteryClicksBase * freeBombMult;
  const d20Clicks0 = d20ClicksBase * freeBombMult;

  // Refill rates (per click of the source) to EACH target bomb (expected value per target).
  const totalBombTypes = Math.max(2, clampInt(params.total_bomb_types, 12));
  const batteryRefillPerClick = clampPositive(params.battery_bomb_charges_per_charge, 2.0) / (totalBombTypes - 1);
  const d20RefillPerClick = (clamp01(params.d20_bomb_refill_chance) * clampPositive(params.d20_bomb_charges_distributed, 42)) / (totalBombTypes - 1);

  // Iterative solution (matches python).
  let gemTotal = gemClicks0;
  let cherryTotal = cherryClicks0;
  let batteryTotal = batteryClicks0;
  let d20Total = d20Clicks0;

  const maxIterations = 100;
  const convergenceThreshold = 0.01;

  for (let iter = 0; iter < maxIterations; iter += 1) {
    // Battery refills to each bomb (including itself per python comment "self-refill")
    const batteryToGem = batteryTotal * batteryRefillPerClick;
    const batteryToCherry = batteryTotal * batteryRefillPerClick;
    const batteryToBattery = batteryTotal * batteryRefillPerClick;
    const batteryToD20 = batteryTotal * batteryRefillPerClick;

    // D20 refills to each bomb (including itself)
    const d20ToGem = d20Total * d20RefillPerClick;
    const d20ToCherry = d20Total * d20RefillPerClick;
    const d20ToBattery = d20Total * d20RefillPerClick;
    const d20ToD20 = d20Total * d20RefillPerClick;

    const gemNew = gemClicks0 + batteryToGem + d20ToGem;
    const cherryNew = cherryClicks0 + batteryToCherry + d20ToCherry;
    const batteryNew = batteryClicks0 + batteryToBattery + d20ToBattery;
    const d20New = d20Clicks0 + batteryToD20 + d20ToD20;

    const change = Math.abs(gemNew - gemTotal) + Math.abs(cherryNew - cherryTotal) + Math.abs(batteryNew - batteryTotal) + Math.abs(d20New - d20Total);
    if (change < convergenceThreshold) {
      gemTotal = gemNew;
      cherryTotal = cherryNew;
      batteryTotal = batteryNew;
      d20Total = d20New;
      break;
    }

    gemTotal = gemNew;
    cherryTotal = cherryNew;
    batteryTotal = batteryNew;
    d20Total = d20New;
  }

  // Cherry effect: expected free clicks multiplier = 1 + 2p (p = triple_charge_chance)
  const cherryEffectMult = 1.0 + 2.0 * clamp01(params.cherry_bomb_triple_charge_chance);
  const cherryFreeGemClicks = cherryTotal * cherryEffectMult;

  const totalGemBombClicks = gemTotal + cherryFreeGemClicks;
  const gemsPerHour = totalGemBombClicks * clamp01(params.gem_bomb_gem_chance);
  return gemsPerHour;
}

export function calculateFounderBombBoostPerHour(params: GameParameters): number {
  const secondsPerHour = 3600.0;
  const dropsPerHour = secondsPerHour / clampPositive(params.founder_bomb_interval_seconds, 87.0);

  const effectiveBombsPerCharge = 1.0 / (1.0 - clamp01(params.free_bomb_chance));
  const founderMult = rechargeChargeMultiplier(params.founder_bomb_recharge_card_level);
  const chargesPerDrop = clampPositive(params.founder_bomb_charges_per_drop, 2.0) * founderMult;
  const effectiveBombsPerDrop = chargesPerDrop * effectiveBombsPerCharge;

  const expectedSpeedActivations = dropsPerHour * effectiveBombsPerDrop * clamp01(params.founder_bomb_speed_chance);
  const timeSavedPerActivation = clampPositive(params.founder_bomb_speed_duration_seconds, 10.0) / clampPositive(params.founder_bomb_speed_multiplier, 2.0);

  const totalTimeSavedSeconds = expectedSpeedActivations * timeSavedPerActivation;
  const totalTimeSavedMinutes = totalTimeSavedSeconds / 60.0;

  const effectiveMinutesPerHour = 60.0 - totalTimeSavedMinutes;

  const normalFreebiesPerHour = calculateFreebiesPerHour(params);
  const baseEffectiveFreebiesPerHour = 60.0 / (clampPositive(params.freebie_timer_minutes, 7.0) * (effectiveMinutesPerHour / 60.0));
  const claim = clampPositive(params.freebie_claim_percentage, 100.0);
  const effectiveFreebiesPerHour = baseEffectiveFreebiesPerHour * (claim / 100.0);

  const additionalFreebies = effectiveFreebiesPerHour - normalFreebiesPerHour;
  const expectedRolls = calculateExpectedRollsPerClaim(params);
  const refreshMult = calculateRefreshMultiplier(params);

  return additionalFreebies * refreshMult * expectedRolls * clampPositive(params.freebie_gems_base, 9.0);
}

export type EvBreakdownEntry = { base: number; jackpot: number; refresh_base: number; refresh_jackpot: number };
export type EvBreakdown = Record<
  | "gems_base"
  | "stonks_ev"
  | "skill_shards_ev"
  | "founder_speed_boost"
  | "founder_gems"
  | "gem_bomb_gems"
  | "founder_bomb_boost",
  EvBreakdownEntry
>;

export function calculateEvBreakdown(params: GameParameters): EvBreakdown {
  const freebiesPerHour = calculateFreebiesPerHour(params);
  const baseRolls = 1.0;
  const expectedRolls = calculateExpectedRollsPerClaim(params);
  const refreshMult = calculateRefreshMultiplier(params);

  // Gems base
  const baseGems = freebiesPerHour * baseRolls * clampPositive(params.freebie_gems_base, 9.0);
  const jackpotGems = freebiesPerHour * (expectedRolls - baseRolls) * clampPositive(params.freebie_gems_base, 9.0);
  const refreshGemsBase = baseGems * (refreshMult - 1.0);
  const refreshGemsJackpot = jackpotGems * (refreshMult - 1.0);

  // Stonks (no jackpot)
  const baseStonks = freebiesPerHour * clamp01(params.stonks_chance) * clampPositive(params.stonks_bonus_gems, 200.0);
  const refreshStonks = baseStonks * (refreshMult - 1.0);

  // Skill shards (jackpot applies)
  const baseShards =
    freebiesPerHour * baseRolls * clamp01(params.skill_shard_chance) * clampPositive(params.skill_shard_value_gems, 12.5);
  const jackpotShards =
    freebiesPerHour * (expectedRolls - baseRolls) * clamp01(params.skill_shard_chance) * clampPositive(params.skill_shard_value_gems, 12.5);
  const refreshShardsBase = baseShards * (refreshMult - 1.0);
  const refreshShardsJackpot = jackpotShards * (refreshMult - 1.0);

  // Founder speed boost (modeled as refresh-only for breakdown)
  const founderSpeedTotal = calculateFounderSpeedBoostPerHour(params);
  const founderSpeedBase = refreshMult > 0 ? founderSpeedTotal / refreshMult : 0;
  const founderSpeedRefresh = founderSpeedTotal - founderSpeedBase;

  // Founder gems (no multipliers in breakdown)
  const founderGems = calculateFounderGemsPerHour(params);

  // Gem bomb gems (independent)
  const gemBombGems = calculateGemBombGemsPerHour(params);

  // Founder bomb boost (modeled as refresh-only for breakdown)
  const founderBombTotal = calculateFounderBombBoostPerHour(params);
  const founderBombBase = refreshMult > 0 ? founderBombTotal / refreshMult : 0;
  const founderBombRefresh = founderBombTotal - founderBombBase;

  return {
    gems_base: { base: baseGems, jackpot: jackpotGems, refresh_base: refreshGemsBase, refresh_jackpot: refreshGemsJackpot },
    stonks_ev: { base: baseStonks, jackpot: 0.0, refresh_base: refreshStonks, refresh_jackpot: 0.0 },
    skill_shards_ev: { base: baseShards, jackpot: jackpotShards, refresh_base: refreshShardsBase, refresh_jackpot: refreshShardsJackpot },
    founder_speed_boost: { base: founderSpeedBase, jackpot: 0.0, refresh_base: founderSpeedRefresh, refresh_jackpot: 0.0 },
    founder_gems: { base: founderGems, jackpot: 0.0, refresh_base: 0.0, refresh_jackpot: 0.0 },
    gem_bomb_gems: { base: gemBombGems, jackpot: 0.0, refresh_base: 0.0, refresh_jackpot: 0.0 },
    founder_bomb_boost: { base: founderBombBase, jackpot: 0.0, refresh_base: founderBombRefresh, refresh_jackpot: 0.0 },
  };
}

export type TotalEv = {
  gems_base: number;
  stonks_ev: number;
  skill_shards_ev: number;
  founder_speed_boost: number;
  founder_gems: number;
  gem_bomb_gems: number;
  founder_bomb_boost: number;
  total: number;
};

export function calculateTotalEvPerHour(params: GameParameters): TotalEv {
  const gems_base = calculateGemsBasePerHour(params);
  const stonks_ev = calculateStonksEvPerHour(params);
  const skill_shards_ev = calculateSkillShardsEvPerHour(params);
  const founder_speed_boost = calculateFounderSpeedBoostPerHour(params);
  const founder_gems = calculateFounderGemsPerHour(params);
  const gem_bomb_gems = calculateGemBombGemsPerHour(params);
  const founder_bomb_boost = calculateFounderBombBoostPerHour(params);

  const total = gems_base + stonks_ev + skill_shards_ev + founder_speed_boost + founder_gems + gem_bomb_gems + founder_bomb_boost;
  return { gems_base, stonks_ev, skill_shards_ev, founder_speed_boost, founder_gems, gem_bomb_gems, founder_bomb_boost, total };
}

