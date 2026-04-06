/**
 * Fishing data types (Idle Obelisk Miner).
 * Catch chance % = 100 * (powerOnDock / fishPowerRating), cap 999%.
 * One fishing tick = 60s base (real time; game speed does not affect fishing).
 */

export type DockId =
  | "lake"
  | "desert"
  | "tundra"
  | "ocean"
  | "nuclear"
  | "abyss"
  | "cave"
  | "volcano"
  | "sky"
  | "solaris"
  | "galaxy";

/** Tier 1 = Lake–Abyss, Tier 2 = Cave–Galaxy (boat upgrade). */
export type DockTier = 1 | 2;

export interface DockDef {
  id: DockId;
  name: string;
  tier: DockTier;
  /** Ticks needed for the dock meter to fill (base, no upgrades). */
  baseTicksNeeded: number;
  /** Ticks needed with upgrades (e.g. Abyss Legendary T1, Motley School, T2 Dock Ticks Enhance). */
  upgradedTicksNeeded: number;
}

export interface FishDef {
  id: string;
  name: string;
  /** Power rating of the fish; catch chance = 100 * (dockPower / powerRating), cap 999%. */
  powerRating: number;
  /** Wiki file name for icon (e.g. "Guppy.png"). */
  iconFile: string;
  /** Short flavour text from wiki (optional). */
  description?: string;
}

/** Fish grouped by dock (each dock has 4 fish). */
export interface DockFishSet {
  dockId: DockId;
  fish: [FishDef, FishDef, FishDef, FishDef];
}

/** Base duration of one fishing tick in real-time seconds (game speed does not affect fishing). */
export const FISHING_TICK_BASE_SEC = 60;

/** Max catch chance in percent (extra rolls for multiple fish). */
export const CATCH_CHANCE_CAP_PERCENT = 999;

/**
 * Catch chance in percent: 100 * (powerOnDock / fishPowerRating).
 * Over 100% = guaranteed floor(percent/100) catches, plus (percent%100)% for one more.
 */
export function catchChancePercent(powerOnDock: number, fishPowerRating: number): number {
  if (fishPowerRating <= 0) return 0;
  const p = (100 * powerOnDock) / fishPowerRating;
  return Math.min(p, CATCH_CHANCE_CAP_PERCENT);
}

/**
 * Expected number of fish per successful dock fill (when rolling for this fish).
 * Rule: X% = floor(X/100) guaranteed + (X%100)% chance for one more.
 * E.g. 999% = 9 guaranteed + 99% chance for a 10th; 342% = 3 guaranteed + 42% for a 4th.
 */
export function expectedCatchesPerRoll(powerOnDock: number, fishPowerRating: number): number {
  const p = catchChancePercent(powerOnDock, fishPowerRating);
  const guaranteed = Math.floor(p / 100);
  const extraChance = (p % 100) / 100;
  return guaranteed + extraChance;
}

// ——— Upgrades (bought with fish) ———

export type FishingUpgradeId =
  // Tier 1
  | "fishing_rod"
  | "fishing_drone"
  | "upgrade_boat"
  | "tick_speed"
  | "fish_multiplier"
  | "rod_multiplier"
  | "drone_multiplier"
  | "double_tick_chance"
  | "fishing_drone_2"
  | "shiny_fish_chance"
  | "drone_base_power"
  | "triple_tick_chance"
  // Tier 2
  | "upgrade_t2_boat"
  | "shiny_multiplier"
  | "tier2_dock_power"
  | "super_shiny_chance"
  | "poly_card_multi"
  | "drone_cloner";

export interface UpgradeDef {
  id: FishingUpgradeId;
  name: string;
  /** Short perk label (e.g. "Fishing Rod", "Tick Speed"). */
  perk: string;
  /** Wiki icon filename (e.g. "Fishing_Rod_Power.png"). */
  iconFile: string;
  /** Human-readable increase per level (e.g. "x1.16", "+0.50s", "+0.50%"). */
  increasePerLevel: string;
  maxLevel: number;
  /** Tier 1 boat level required to unlock (0 = from start). */
  boatLevelRequired: number;
  /** Tier 2 boat level required (1–5); only for T2 upgrades, null otherwise. */
  t2BoatLevelRequired: number | null;
}

/** Cost for one level of an upgrade: fish id (from aquarium) and amount. */
export interface UpgradeCostEntry {
  level: number;
  /** Fish id (e.g. "guppy", "golden_trout"). */
  fishId: string;
  amount: number;
}

// ——— Enhancements (bought with gems, do not count toward completion) ———

export type EnhanceId =
  // Tier 1
  | "enhance_fish_multiplier"
  | "enhance_fishing_drone"
  | "enhance_rod_multiplier"
  | "enhance_tick_speed"
  | "enhance_drone_multiplier"
  | "enhance_token_multiplier"
  | "enhance_double_tick_chance"
  | "enhance_tiny_notice_chance"
  | "enhance_shiny_multiplier"
  | "enhance_fishing_drone_3"
  // Tier 2
  | "enhance_tier2_dock_ticks"
  | "enhance_triple_tick_chance"
  | "enhance_super_shiny_multi"
  | "enhance_tier2_dock_power"
  | "enhance_poly_card_multi";

/** Tier 1 enhancement ids (boat level unlock). */
export type EnhanceIdT1 =
  | "enhance_fish_multiplier"
  | "enhance_fishing_drone"
  | "enhance_rod_multiplier"
  | "enhance_tick_speed"
  | "enhance_drone_multiplier"
  | "enhance_token_multiplier"
  | "enhance_double_tick_chance"
  | "enhance_tiny_notice_chance"
  | "enhance_shiny_multiplier"
  | "enhance_fishing_drone_3";

/** Tier 2 enhancement ids (T2 boat level unlock). */
export type EnhanceIdT2 =
  | "enhance_tier2_dock_ticks"
  | "enhance_triple_tick_chance"
  | "enhance_super_shiny_multi"
  | "enhance_tier2_dock_power"
  | "enhance_poly_card_multi";

export interface EnhanceDef {
  id: EnhanceId;
  name: string;
  perk: string;
  iconFile: string;
  increasePerLevel: string;
  maxLevel: number;
  /** Tier 1 boat level required (0 = from start). */
  boatLevelRequired: number;
  /** Tier 2 boat level required (1–5); only for T2 enhancements. */
  t2BoatLevelRequired: number | null;
}

export interface EnhanceCostEntry {
  level: number;
  gems: number;
}

// ——— Skill Tree (cost: skill points) ———

export type FishingSkillId =
  | "fishing_with_friends"
  | "friendship_ended_tier1"
  | "motley_school"
  | "lets_pick_up_the_pace"
  | "with_this_fish_i_summon_two_more_fish"
  | "completionist_gatekeeper";

export interface FishingSkillDef {
  id: FishingSkillId;
  name: string;
  /** Wiki icon filename (e.g. "Fishing_With_Friends.png"). */
  iconFile: string;
  /** Optional wiki icon filename for a stat related to the skill (e.g. "Notice_Fish_Requirement.png"). */
  statIconFile?: string;
  /** Obelisk level required to unlock. */
  obeliskLevel: number;
  /** Short effect lines for tooltip/display. */
  effectLines: string[];
  /** Skill point cost for level 1, 2, 3 (length = max level). */
  costs: number[];
}

// ——— Effective fishing tick (Elixir 3x buff) ———

/**
 * Effective seconds per fishing tick when Elixir drone's 3× Fishing Tick Speed buff is applied part of the time.
 * During buff: tick duration = baseSec/3. Effective = baseSec * (1 - uptime) + (baseSec/3) * uptime.
 * @param baseTickSec Base seconds per tick (e.g. FISHING_TICK_BASE_SEC or reduced by Tick Speed upgrade).
 * @param elixir3xUptimeFraction Fraction of time the 3× buff is active (0..1).
 */
export function effectiveFishingTickSec(baseTickSec: number, elixir3xUptimeFraction: number): number {
  if (elixir3xUptimeFraction <= 0) return baseTickSec;
  const uptime = Math.max(0, Math.min(1, elixir3xUptimeFraction));
  return baseTickSec * (1 - uptime) + (baseTickSec / 3) * uptime;
}
