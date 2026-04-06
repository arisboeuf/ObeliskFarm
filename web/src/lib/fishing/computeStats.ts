/**
 * Compute fishing stats from upgrade and enhancement levels (game formulas).
 * Source: https://shminer.miraheze.org/wiki/Fishing#Upgrades and #Enhancements
 */

import { ALL_FISH, LEGENDARY_FISH } from "./constants";
import type { DockDef, EnhanceId, FishingSkillId, FishingUpgradeId } from "./types";

/** Fish ids (regular + legendary). Used for With This Fish I Summon card count. Excludes misc cards: Fishing Rod Power, Mr Nibbles. */
const FISH_IDS = new Set([
  ...ALL_FISH.map((f) => f.id),
  ...LEGENDARY_FISH.map((f) => f.id),
]);

/** Options for effective dock tick requirement (reduces fills per hour = more fish/h). */
export interface EffectiveTicksOptions {
  /** Motley School skill level: Abyss -2 per level, Tier 2 docks -1 per level. */
  motleySchoolLevel?: number;
  /** Tier 2 Dock Ticks enhancement level: Tier 2 docks only, -1 per level (max 10). */
  enhanceT2DockTicksLevel?: number;
  /** Abyss Legendary (Cthulhu) caught: Tier 1 docks tick req -10%. */
  abyssLegendaryCaught?: boolean;
}

/**
 * Effective ticks needed to fill the dock meter. Lower = more dock fills per hour = more fish.
 * Reductions: Abyss Legendary T1 (all docks -10%), Motley School (Abyss -2/level, T2 -1/level), T2 Dock Ticks Enhance (-1/level for T2).
 */
export function getEffectiveTicksNeeded(
  dock: DockDef,
  opts: EffectiveTicksOptions = {},
): number {
  const motley = Math.max(0, Math.floor(opts.motleySchoolLevel ?? 0));
  const t2Enhance = Math.max(0, Math.min(10, Math.floor(opts.enhanceT2DockTicksLevel ?? 0)));
  const abyssT1 = opts.abyssLegendaryCaught === true;
  let ticks = dock.baseTicksNeeded;
  if (dock.id === "abyss") {
    ticks -= 2 * motley;
  } else if (dock.tier === 2) {
    ticks -= motley;
    ticks -= t2Enhance;
  }
  if (abyssT1 && dock.tier === 1) ticks = Math.floor(ticks * 0.9);
  return Math.max(1, ticks);
}

/** All stats computed from upgrade and enhancement levels (including boat levels). */
export interface ComputedFishingStats {
  boat_level: number;
  t2_boat_level: number;
  fishing_rod_power: number;
  fishing_drone_cap: number;
  drone_base_power: number;
  /** Raw base before multiplier (unrounded; used for gains). For display "Drone Base Power". */
  drone_base_power_base: number;
  /** Rounded base (game-style display only). */
  drone_base_power_base_rounded: number;
  /** Multiplier on Drone Base Power (from drone_multiplier + enhance). */
  drone_power_multiplier: number;
  /** Per-factor breakdown for Drone Power Multi (upgrade × enhance × fwf × completionist × workshop × tethys). */
  drone_power_multiplier_breakdown?: { upgrade: number; enhance: number; fwf: number; completionist: number; workshop: number; tethys: number };
  fish_income_multi: number;
  fishing_tick_reduction: number;
  /** Double Fish Tick Chance (%). When tick bar fills, chance to get 2 ticks at once. */
  double_tick_chance_pct: number;
  /** Triple Fish Tick Chance (%). */
  triple_tick_chance_pct: number;
  /** 5× Fish Tick Chance (%) – from Fishing only; game can add Relics/Store/Cards. */
  five_tick_chance_pct: number;
  token_gain_multi: number;
  notice_fish_req: number;
  /** Shiny Fish Chance (%). Shiny = crit-like; multiplier applies (base 5×). */
  shiny_fish_chance_pct: number;
  /** Super Shiny Chance (%). Only rolls when catch is already shiny; base mult 3×. */
  super_shiny_chance_pct: number;
  /** Tiny Notice Chance (%). Notice asks for 90% less fish. */
  tiny_notice_chance_pct: number;
  /** Tier 2 Dock Power multiplier (×) applied to power on T2 docks. */
  tier2_dock_power_mult: number;
  shiny_multiplier: number;
  super_shiny_multiplier: number;
  /** Multiplier on fish card gains from upgrades (poly_card_multi, enhance_poly_card_multi). Polychrome Potency Bundle (fish poly ×1.15) applied in UI. */
  poly_card_gain_multi: number;
}

function lvl(
  levels: Partial<Record<string, number>>,
  id: string,
): number {
  const v = levels[id];
  if (v == null) return 0;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0;
}

export interface SkillTreeOptions {
  skillTreeLevels?: Partial<Record<FishingSkillId, number>>;
  /** Fish card tier per fish (0–3) for With This Fish I Summon: effective card count. */
  fishCardTier?: Partial<Record<string, number>>;
  /** Legendary fish found (0–6) for Completionist Gatekeeper. */
  legendaryFishFound?: number;
  /** Divine Relic points: each point gives +2% 5× tick chance (base; applies to all sources; Sushi does not get Gift's +25% on top). */
  relic5xPoints?: number;
  /** Pets: Mr Nibbles level. +0.03× Shiny Fish Multi per level (own mult), +1% Triple Tick Chance per level (flat). */
  mrNibblesLevel?: number;
  /** Pets: Mr Nibbles Quest. When unlocked, rank 0 = +5% T2 Dock Power (own mult); each rank adds +5%. */
  mrNibblesQuestUnlocked?: boolean;
  /** Pets: Mr Nibbles Quest rank (0-based). Only applies when mrNibblesQuestUnlocked. Mult = 1 + 0.05×(rank+1). */
  mrNibblesQuestRank?: number;
  /** Pets: Mr Nibbles Pet Skin. +2% Shiny Fish Chance (flat). */
  mrNibblesSkin?: boolean;
  /** Archaeology: Poseidon Idol level. +0.25 base fishing drone power per level (adds to base 3). */
  poseidonIdolLevel?: number;
  /** Archaeology: Tethys Idol level. Each point: Tier 2 dock power +0.05%, Drone power multi +0.05%, Super shiny multi +0.05% (each separate mult). */
  tethysIdolLevel?: number;
  /** Archaeology: Astraeus Idol level. +0.03% double tick chance per level (flat, added on top of existing). */
  astraeusIdolLevel?: number;
  /** Upgrades: Fishing Drone Power (World 3). +0.1 base drone power per level (adds to base before mult). */
  droneBasePowerWorld3Upgrade?: number;
  /** Workshop: Fishing Drone Power (World 3). +0.02x multiplier per level (own mult). */
  fishingDroneBasePowerWorld3?: number;
  /** Cards: Infernal Mr Nibbles. +X% 5× tick chance per level (flat); X and level are user inputs. */
  infernalMrNibblesPct?: number;
  infernalMrNibblesLevel?: number;
  /** Cards: Infernal Angler Drone Card. +X% Tier 2 Dock Power per level; X and level are user inputs. */
  infernalAnglerDronePct?: number;
  infernalAnglerDroneLevel?: number;
  /** Store: Legendary Hauler Bundle. +3% 5× tick chance (flat), Fish Income ×1.10 (own mult), Tier 2 Dock Power ×1.10 (own mult). */
  legendaryHaulerBundle?: boolean;
  /** Store: Fisher's Bundle. +10% triple tick chance (flat). */
  fishersBundle?: boolean;
  /** Store: Angler's Bundle. +6% Tiny Notice Chance (flat). */
  anglerBundle?: boolean;
  /** Divine Challenge Coin: each level gives Shiny Fish Multiplier +10% (own mult). */
  halfWayBundle?: boolean;
  /** Store: Half Way Bundle! Fishing Rod Multi 1.10x. */
  divineChallengeCoinLevel?: number;
  /** Construct: Statue Craftmanship. At most one. Gilded = Fish Income ×1.25, Platinized = Fish Income ×1.40 (own mult each). */
  constructStatue?: "none" | "gilded" | "platinized";
  /** Stargazing: Cetus level. +2% Fish Income per level (own mult: 1 + 0.02×level). */
  cetusLevel?: number;
  /** Stargazing: Black Hole Bonus. Tier 2 Dock Power +25% (own mult). */
  blackHoleBonus?: boolean;
  /** Stargazing: Super Stars Fish Income Multiplier. +1.25% per level (max 15, own mult). */
  superStarsLevel?: number;
  /** Legendary Fish Tribute: Cthulhu. All docks tick req -10%, Super Shiny Multi +3×. */
  abyssLegendaryCaught?: boolean;
  /** Cards: Mr Nibbles Card. 0 = none, 1 = Card +1% Tiny Notice, 2 = Gilded +2%, 3 = Poly +4% (flat). */
  mrNibblesCardTier?: number;
}

/**
 * Compute all stats that derive from upgrade and enhancement levels.
 * Boat levels come from Upgrade Boat and Upgrade Tier 2 Boat upgrades.
 * Optional skill tree levels apply on top (Fishing With Friends, Motley School, etc.).
 */
export function computeFishingStatsFromLevels(
  upgradeLevels: Partial<Record<FishingUpgradeId, number>>,
  enhanceLevels: Partial<Record<EnhanceId, number>>,
  options?: SkillTreeOptions,
): ComputedFishingStats {
  const u = (id: FishingUpgradeId) => lvl(upgradeLevels, id);
  const e = (id: EnhanceId) => lvl(enhanceLevels, id);
  const skill = (id: FishingSkillId) => lvl(options?.skillTreeLevels ?? {}, id);

  // Boat levels: from Upgrade Boat (+1 per level, max 5) and Upgrade Tier 2 Boat (+1 per level, max 5).
  const boat_level = u("upgrade_boat");
  const t2_boat_level = u("upgrade_t2_boat");

  // Fishing Rod: base 10, ×1.16 per level. Three separate rod multis: upgrade +0.04x, enhance +0.05x, Motley School +10% per level.
  // Game rounds rodBase before applying multipliers (matches in-game display). Fishing Rod card is separate; applied in UI.
  const ROD_POWER_BASE = 10;
  const rodBase = Math.round(ROD_POWER_BASE * Math.pow(1.16, u("fishing_rod")));
  const rodMultiUpgrade = 1 + 0.04 * u("rod_multiplier");
  const rodMultiEnhance = 1 + 0.05 * e("enhance_rod_multiplier");
  const rodMultiMotleySchool = 1 + 0.1 * skill("motley_school");
  const halfWayBundleMult = options?.halfWayBundle ? 1.10 : 1;
  const fishing_rod_power = rodBase * rodMultiUpgrade * rodMultiEnhance * rodMultiMotleySchool * halfWayBundleMult;
  

  // Fish Income Multiplier: upgrade and enhancement are separate factors; the two skills (Fishing With Friends, With This Fish) add together into one factor (additive, not multiplicative).
  // (1 + 0.03×upgrade) × (1 + 0.05×enhance) × (1 + 0.03×Fishing With Friends + 0.01×With This Fish×cards).
  // With This Fish: only fish cards count; Fishing Rod Power and Mr Nibbles (misc cards) are excluded.
  const effectiveFishCardCount =
    (options?.fishCardTier &&
      Object.entries(options.fishCardTier).reduce<number>(
        (sum, [id, t]) => sum + (FISH_IDS.has(id) ? (t === 1 ? 1 : t === 2 ? 2 : t === 3 ? 3 : 0) : 0),
        0,
      )) ??
    0;
  const skillFishMulti =
    1 +
    0.03 * skill("fishing_with_friends") +
    0.01 * skill("with_this_fish_i_summon_two_more_fish") * effectiveFishCardCount;
  const fishIncomeBase =
    (1 + 0.03 * u("fish_multiplier")) * (1 + 0.05 * e("enhance_fish_multiplier")) * skillFishMulti;
  const constructMult =
    options?.constructStatue === "gilded" ? 1.25 : options?.constructStatue === "platinized" ? 1.4 : 1;
  const cetusLevel = Math.max(0, Math.floor(options?.cetusLevel ?? 0));
  const cetusFishIncomeMult = 1 + 0.02 * cetusLevel;
  const fish_income_multi =
    fishIncomeBase * (options?.legendaryHaulerBundle ? 1.1 : 1) * constructMult * cetusFishIncomeMult * (1 + 0.0125 * Math.max(0, Math.min(15, Math.floor(options?.superStarsLevel ?? 0))));

  // Tick reduction: each level reduces tick by 0.5s. Base 60s. Skill: Let's Pick Up The Pace -2s per level.
  const fishing_tick_reduction =
    -0.5 * u("tick_speed") -
    0.5 * e("enhance_tick_speed") -
    2 * skill("lets_pick_up_the_pace");

  // Drone Base Power: base 3, +0.25 per level (upgrade), +0.25 per Poseidon Idol (Archaeology), +0.1 per level Diverse Upgrades "Fishing Drone Power (World 3)". Game may round base for display; for gains we use the raw base (no rounding). Drone Power Multiplier: +0.06x (upgrade), +0.08x (enhance), Skill, Workshop World 3 +0.02x per level (own mult), Tethys Idol +0.05% per level (global, all docks).
  const poseidonIdol = Math.max(0, Math.floor(options?.poseidonIdolLevel ?? 0));
  const droneBasePowerWorld3Upgrade = Math.max(0, Math.floor(options?.droneBasePowerWorld3Upgrade ?? 0));
  const droneBaseRaw =
    3 + 0.25 * u("drone_base_power") + 0.25 * poseidonIdol + 0.1 * droneBasePowerWorld3Upgrade;
  const droneBase = Math.round(droneBaseRaw);
  const droneMultiUpgrade = 1 + 0.06 * u("drone_multiplier");
  const droneMultiEnhance = 1 + 0.08 * e("enhance_drone_multiplier");
  const legendary = Math.max(0, Math.min(11, options?.legendaryFishFound ?? 0));
  const droneMultFwf = 1 + 0.1 * skill("fishing_with_friends");
  const droneMultCompletionist = 1 + (0.02 * skill("completionist_gatekeeper")) * legendary;
  const workshopDroneMultiWorld3 = 1 + 0.02 * Math.max(0, Math.floor(options?.fishingDroneBasePowerWorld3 ?? 0));
  const tethysIdol = Math.max(0, Math.floor(options?.tethysIdolLevel ?? 0));
  const tethysDroneMult = 1 + 0.0005 * tethysIdol; // +0.05% per level; applies to all docks
  const drone_power_multiplier = droneMultiUpgrade * droneMultiEnhance * droneMultFwf * droneMultCompletionist * workshopDroneMultiWorld3 * tethysDroneMult;
  const drone_power_multiplier_breakdown = {
    upgrade: droneMultiUpgrade,
    enhance: droneMultiEnhance,
    fwf: droneMultFwf,
    completionist: droneMultCompletionist,
    workshop: workshopDroneMultiWorld3,
    tethys: tethysDroneMult,
  };
  /** Used for gains: raw base (no rounding) so e.g. 3.25 gives more power than 3. */
  const drone_base_power = droneBaseRaw * drone_power_multiplier;
  /** Raw base (unrounded) for display and gains. */
  const drone_base_power_base = droneBaseRaw;
  const drone_base_power_base_rounded = droneBase;

  // Fishing Drone Cap: base 0, then from upgrades (+1 per fishing_drone, +2 per fishing_drone_2) and enhancements (+1 per enhance_fishing_drone, +3 per enhance_fishing_drone_3); then Drone Cloner 1.05x. Skill: Fishing With Friends +5, Motley School +5 per level.
  const capFromUpgradesAndEnhancements =
    0 +
    1 * u("fishing_drone") +
    2 * u("fishing_drone_2") +
    1 * e("enhance_fishing_drone") +
    3 * e("enhance_fishing_drone_3") +
    5 * skill("fishing_with_friends") +
    5 * skill("motley_school");
  const fishing_drone_cap = capFromUpgradesAndEnhancements * (1 + 0.05 * u("drone_cloner"));

  // Token Gain Multiplier: only from enhancement +0.05x per level.
  const token_gain_multi = 1 + 0.05 * e("enhance_token_multiplier");

  // Notice fish requirement: no upgrade source in game; use 1. Skill: Friendship Ended -10% per level (additive: 3 levels = -30% → 0.70x).
  const notice_fish_req = Math.max(0.01, 1 - 0.1 * skill("friendship_ended_tier1"));

  // Tick chances (%): double +0.5% (upgrade), +0.5% (enhance); triple +0.35% (upgrade), +0.4% (enhance). Skill: Let's Pick Up The Pace +2% double, +1% triple per level. Archaeology: Astraeus Idol +0.03% double (flat).
  const astraeusIdol = Math.max(0, Math.floor(options?.astraeusIdolLevel ?? 0));
  const double_tick_chance_pct =
    0.5 * u("double_tick_chance") +
    0.5 * e("enhance_double_tick_chance") +
    2 * skill("lets_pick_up_the_pace") +
    0.03 * astraeusIdol;
  const mrNibblesLevel = Math.max(0, Math.floor(options?.mrNibblesLevel ?? 0));
  const triple_tick_chance_pct =
    0.35 * u("triple_tick_chance") +
    0.4 * e("enhance_triple_tick_chance") +
    1 * skill("lets_pick_up_the_pace") +
    (options?.fishersBundle ? 10 : 0) +
    1 * mrNibblesLevel;
  const infernalPct = Math.max(0, Number(options?.infernalMrNibblesPct ?? 0));
  const infernalLvl = Math.max(0, Math.floor(options?.infernalMrNibblesLevel ?? 0));
  const five_tick_chance_pct =
    2 * Math.max(0, Math.floor(options?.relic5xPoints ?? 0)) +
    (options?.legendaryHaulerBundle ? 3 : 0) +
    infernalPct * infernalLvl;

  // Shiny / Super Shiny chances (%): shiny_fish_chance +0.5% per level; super_shiny_chance +1% per level; tiny notice +0.5% (enhance). Skill: With This Fish I Summon +0.1% shiny per fish card per level; Completionist +1% super shiny per level per legendary. Pets: Mr Nibbles Skin +2% (flat).
  const shiny_fish_chance_pct =
    0.5 * u("shiny_fish_chance") +
    0.1 * skill("with_this_fish_i_summon_two_more_fish") * effectiveFishCardCount +
    (options?.mrNibblesSkin ? 2 : 0);
  const super_shiny_chance_pct =
    1 * u("super_shiny_chance") +
    1 * skill("completionist_gatekeeper") * legendary;
  const mrNibblesCardTier = Math.max(0, Math.min(3, Math.floor(Number(options?.mrNibblesCardTier ?? 0))));
  const tinyNoticeFromMrNibblesCard = mrNibblesCardTier === 1 ? 1 : mrNibblesCardTier === 2 ? 2 : mrNibblesCardTier === 3 ? 4 : 0;
  const tiny_notice_chance_pct = 0.5 * e("enhance_tiny_notice_chance") + (options?.anglerBundle ? 6 : 0) + tinyNoticeFromMrNibblesCard;

  // --- TIER 2 DOCK POWER CALCULATION ---
  // Different menus are multiplicative. Within the Fishing menu, Upgrade and Enhancement are additive ('+').

  // 1. Fishing Menu: Upgrade + Enhancement (additive within menu)
  const tier2FishingMenuFactor = 1 +
    0.05 * u("tier2_dock_power") +
    0.05 * e("enhance_tier2_dock_power");

  // 2. Skill-Tree Menu (multiplicative against other menus)
  const tier2SkillTreeFactor = 1 +
    0.03 * skill("completionist_gatekeeper") * legendary;

  // 3. Archaeology Menu
  const archaeologyFactor = 1 + (0.0005 * tethysIdol);

  // 4. Pets Menu (Mr Nibbles Quest)
  const mrNibblesQuestUnlocked = Boolean(options?.mrNibblesQuestUnlocked);
  const mrNibblesQuestRank = Math.max(0, Math.floor(options?.mrNibblesQuestRank ?? 0));
  const mrNibblesQuestMult = mrNibblesQuestUnlocked ? 1 + 0.05 * (mrNibblesQuestRank + 1) : 1;

  // 5. Card Menu (Infernal Angler)
  const infernalAnglerPct = Math.max(0, Number(options?.infernalAnglerDronePct ?? 0));
  const infernalAnglerLvl = Math.max(0, Math.floor(options?.infernalAnglerDroneLevel ?? 0));
  const cardFactor = 1 + (infernalAnglerPct * infernalAnglerLvl) / 100;

  // 6. Store Menu (Legendary Hauler)
  const storeFactor = options?.legendaryHaulerBundle ? 1.10 : 1;

  // 7. Stargazing Menu (Black Hole)
  const stargazingFactor = options?.blackHoleBonus ? 1.25 : 1;

  // FINAL: each menu factor is multiplicative
  const tier2_dock_power_mult =
    tier2FishingMenuFactor *
    tier2SkillTreeFactor *
    archaeologyFactor *
    mrNibblesQuestMult *
    cardFactor *
    storeFactor *
    stargazingFactor;

  // Shiny Multiplier: base 5×, +5% per level (T2 upgrade and enhance; additive mult: 1 + 0.05×level each). Pets: Mr Nibbles +0.03× per level (own mult). Divine Challenge Coin: +10% per level (own mult).
  const shinyBase = 5 * (1 + 0.05 * u("shiny_multiplier")) * (1 + 0.05 * e("enhance_shiny_multiplier"));
  const divineChallengeCoinLevel = Math.max(0, Math.floor(options?.divineChallengeCoinLevel ?? 0));
  const shiny_multiplier = shinyBase * (1 + 0.03 * mrNibblesLevel) * (1 + 0.1 * divineChallengeCoinLevel);

  // Super Shiny Multiplier: base 3× (only when catch is already shiny), +0.08x (poly_card_multi), +0.15x (enhance), +3 (Cthulhu tribute). Tethys Idol +0.05% per level (global, all docks).
  const superShinyBase = 3 +
    0.08 * u("poly_card_multi") +
    0.15 * e("enhance_super_shiny_multi") +
    (options?.abyssLegendaryCaught ? 3 : 0);
  const super_shiny_multiplier = superShinyBase * (1 + 0.0005 * tethysIdol);

  // Poly card gain multi: applies to fish card gains (Card 1.5×, Gilded 2×). Polychrome Potency Bundle fish poly ×1.15 in UI.
  const poly_card_gain_multi =
    0.08 * u("poly_card_multi") +
    0.1 * e("enhance_poly_card_multi");

  return {
    boat_level,
    t2_boat_level,
    fishing_rod_power,
    fishing_drone_cap,
    drone_base_power,
    drone_base_power_base,
    drone_base_power_base_rounded,
    drone_power_multiplier,
    drone_power_multiplier_breakdown,
    fish_income_multi,
    fishing_tick_reduction,
    double_tick_chance_pct,
    triple_tick_chance_pct,
    five_tick_chance_pct,
    token_gain_multi,
    notice_fish_req,
    shiny_fish_chance_pct,
    super_shiny_chance_pct,
    tiny_notice_chance_pct,
    tier2_dock_power_mult,
    shiny_multiplier,
    super_shiny_multiplier,
    poly_card_gain_multi,
  };
}