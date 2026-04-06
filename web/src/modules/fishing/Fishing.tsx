import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import "./fishing.css";
import { Collapsible } from "../../components/Collapsible";
import { Tooltip } from "../../components/Tooltip";
import { formatCostCompact } from "../../lib/format";
import { mulberry32 } from "../../lib/rng";
import { loadJson, saveJson } from "../../lib/storage";
import {
  calculateGift5xTickUptimeFraction,
  calculateGiftSushiPerHour,
  calculateGiftSushiPerHourBySource,
  defaultGameParameters,
  type GameParameters,
} from "../../lib/gemev/freebieEv";
import {
  AQUARIUM,
  ALL_FISH,
  DOCKS,
  LEGENDARY_FISH,
  catchChancePercent,
  computeFishingStatsFromLevels,
  type ComputedFishingStats,
  dockIconUrl,
  effectiveFishingTickSec,
  ENHANCE_COSTS_T1,
  ENHANCE_COSTS_T2,
  ENHANCEMENTS_T1,
  ENHANCEMENTS_T2,
  expectedCatchesPerRoll,
  fishIconUrl,
  FISHING_SKILL_TREE,
  FISHING_UPGRADES_T1,
  FISHING_UPGRADES_T2,
  getFishById,
  getEffectiveTicksNeeded,
  getFishCardGildGemCost,
  getFishPolyShardOdds,
  FISHING_ROD_GILD_CARD_COST,
  upgradeIconUrl,
  enhanceIconUrl,
  fishReqIconUrl,
  UPGRADE_COSTS,
  type DockId,
  type EnhanceId,
  type FishingSkillId,
  type FishingUpgradeId,
} from "../../lib/fishing";

/** Fish card tier: 0 = none, 1 = Card (1.5×), 2 = Gilded (2×), 3 = Poly (4× base). */
export type FishCardTier = 0 | 1 | 2 | 3;

/** Sample from Poisson(lambda) using exponential inter-arrival. */
function samplePoisson(rng: () => number, lambda: number): number {
  if (lambda <= 0) return 0;
  let count = 0;
  let sum = 0;
  while (sum < lambda) {
    let u = rng();
    if (u <= 0) u = 1e-10;
    sum -= Math.log(u);
    count++;
  }
  return count - 1;
}

type SavedState = {
  dronesPerDock?: Partial<Record<DockId, number>>;
  activeDockId?: DockId | null;
  showDisabledFishGrayed?: boolean;
  showPolyShardDroprate?: boolean;
  useGemIncomeForCostEffic?: boolean;
  upgradeLevels?: Partial<Record<FishingUpgradeId, number>>;
  enhanceLevels?: Partial<Record<EnhanceId, number>>;
  fishCardTier?: Partial<Record<string, FishCardTier>>;
  sushiCardTier?: FishCardTier;
  fishingRodCardTier?: FishCardTier;
  valuePackPotencyPoly?: boolean;
  skillTreeLevels?: Partial<Record<FishingSkillId, number>>;
  legendaryFishFound?: number;
  /** Abyss Legendary (Cthulhu) tribute 1: All docks tick req -10% and Super Shiny Multi +3× */
  abyssLegendaryCaught?: boolean;
  /** Divine Relic points: +2% 5× tick chance per point (applies to all gains; Sushi does not get Gift +25%). */
  divineRelic5xPoints?: number;
  /** Variance (MC) simulation: hours to simulate. Default 8. */
  mcHours?: number;
  /** Variance (MC) simulation: number of runs (dock fill MC). Default 1000. */
  mcRuns?: number;
  /** Sushi variance MC: how many Sushi openings to simulate. Default 1000. */
  sushiMcSushis?: number;
  /** Pets: Mr Nibbles level. */
  mrNibblesLevel?: number;
  /** Pets: Mr Nibbles Quest unlocked (rank 0 = +5% T2 Dock Power). */
  mrNibblesQuestUnlocked?: boolean;
  /** Pets: Mr Nibbles Quest rank (0-based; only when unlocked). */
  mrNibblesQuestRank?: number;
  /** Pets: Mr Nibbles Pet Skin. +2% Shiny Fish Chance (flat). */
  mrNibblesSkin?: boolean;
  poseidonIdolLevel?: number;
  tethysIdolLevel?: number;
  astraeusIdolLevel?: number;
  fishingDroneBasePowerWorld3?: number;
  workshopSushiTicksWorld3?: number;
  legendaryHaulerBundle?: boolean;
  fishersBundle?: boolean;
  /** Store: Angler's Bundle. +6% Tiny Notice Chance (flat). */
  anglerBundle?: boolean;
  /** Store: Half Way Bundle! Fishing Rod Power ×1.10. */
  halfWayBundle?: boolean;
  /** Divine Challenge Coin: each level gives Shiny Fish Multiplier +10%. */
  divineChallengeCoinLevel?: number;
  /** Construct: Statue Craftmanship. At most one: gilded (×1.25) or platinized (×1.40) fish income. */
  constructStatue?: "none" | "gilded" | "platinized";
  /** Stargazing: Cetus level. +2% Fish Income per level. */
  cetusLevel?: number;
  /** Stargazing: Black Hole Bonus. Tier 2 Dock Power +25%. */
  blackHoleBonus?: boolean;
  /** Stargazing: Super Stars Fish Income Multiplier. +1.25% per level (max 15). */
  superStarsLevel?: number;
  /** Upgrades: Fishing Drone Power (World 3). +0.1 base drone power per level. */
  droneBasePowerWorld3Upgrade?: number;
  /** Cards: Infernal Mr Nibbles — % per level (flat 5× tick chance). */
  infernalMrNibblesPct?: number;
  /** Cards: Infernal Mr Nibbles — level. */
  infernalMrNibblesLevel?: number;
  /** Cards: Infernal Angler Drone Card — % per level (Tier 2 Dock Power). */
  infernalAnglerDronePct?: number;
  /** Cards: Infernal Angler Drone Card — level. */
  infernalAnglerDroneLevel?: number;
  /** Cards: Mr Nibbles Card. 0 = none, 1 = +1% Tiny Notice, 2 = Gilded +2%, 3 = Poly +4%. */
  mrNibblesCardTier?: FishCardTier;
};

/** Single persisted state (same pattern as Drone: one state, lazy load, save on change). */
type FishingState = {
  dronesPerDock: Record<DockId, number>;
  activeDockId: DockId;
  showDisabledFishGrayed: boolean;
  showPolyShardDroprate: boolean;
  useGemIncomeForCostEffic: boolean;
  upgradeLevels: Partial<Record<FishingUpgradeId, number>>;
  enhanceLevels: Partial<Record<EnhanceId, number>>;
  fishCardTier: Partial<Record<string, FishCardTier>>;
  /** Sushi Misc card: 0 = none, 1 = Card +5 ticks, 2 = Gilded +10, 3 = Poly +20. */
  sushiCardTier: FishCardTier;
  /** Fishing Rod card: 0 = none, 1 = Card 1.02×, 2 = Gilded 1.05×, 3 = Poly 1.10× rod power. */
  fishingRodCardTier: FishCardTier;
  /** Cards: Mr Nibbles Card. 0 = none, 1 = Card +1% Tiny Notice, 2 = Gilded +2%, 3 = Poly +4%. */
  mrNibblesCardTier: FishCardTier;
  valuePackPotencyPoly: boolean;
  skillTreeLevels: Partial<Record<FishingSkillId, number>>;
  legendaryFishFound: number;
  /** Abyss Legendary (Cthulhu) tribute 1: All docks tick req -10% and Super Shiny Multi +3× */
  abyssLegendaryCaught: boolean;
  /** Divine Relic points: +2% 5× tick chance per point. */
  divineRelic5xPoints: number;
  /** Variance (MC) simulation: hours to simulate. Default 8. */
  mcHours: number;
  /** Variance (MC) simulation: number of runs (dock fill MC). Default 1000. */
  mcRuns: number;
  /** Sushi variance MC: simulated Sushi count. Default 1000. */
  sushiMcSushis: number;
  /** Pets: Mr Nibbles level. +0.03× Shiny Multi per level (own mult), +1% Triple Tick Chance per level (flat). */
  mrNibblesLevel: number;
  /** Pets: Mr Nibbles Quest unlocked. When true, rank 0 = +5% T2 Dock Power (own mult). */
  mrNibblesQuestUnlocked: boolean;
  /** Pets: Mr Nibbles Quest rank (0-based). Mult = 1 + 0.05×(rank+1) when unlocked. */
  mrNibblesQuestRank: number;
  /** Pets: Mr Nibbles Pet Skin. +2% Shiny Fish Chance (flat). */
  mrNibblesSkin: boolean;
  /** Archaeology: Poseidon Idol level. +0.25 base drone power per level. */
  poseidonIdolLevel: number;
  /** Archaeology: Tethys Idol level. Tier 2 +0.05%, Drone multi +0.05%, Super shiny multi +0.05% per level. */
  tethysIdolLevel: number;
  /** Archaeology: Astraeus Idol level. +0.03% double tick chance per level (flat). */
  astraeusIdolLevel: number;
  /** Upgrades: Fishing Drone Power (World 3). +0.1 base drone power per level. */
  droneBasePowerWorld3Upgrade: number;
  /** Workshop: Fishing Drone Power (World 3). +0.02x multiplier per level. */
  fishingDroneBasePowerWorld3: number;
  /** Workshop: Sushi Fishing Ticks (World 3). +1 extra sushi tick per hour per level. */
  workshopSushiTicksWorld3: number;
  /** Store: Legendary Hauler Bundle. +3% 5× tick, Fish Income ×1.10, T2 Dock Power ×1.10. */
  legendaryHaulerBundle: boolean;
  /** Store: Fisher's Bundle. +10% triple tick chance. */
  fishersBundle: boolean;
  /** Store: Angler's Bundle. +6% Tiny Notice Chance (flat). */
  anglerBundle: boolean;
  /** Store: Half Way Bundle! Fishing Rod Power ×1.10. */
  halfWayBundle: boolean;
  /** Divine Challenge Coin: each level gives Shiny Fish Multiplier +10%. */
  divineChallengeCoinLevel: number;
  /** Construct: Statue Craftmanship. At most one: gilded (×1.25 fish income) or platinized (×1.40). */
  constructStatue: "none" | "gilded" | "platinized";
  /** Stargazing: Cetus level. +2% Fish Income per level (own mult). */
  cetusLevel: number;
  /** Stargazing: Black Hole Bonus. Tier 2 Dock Power +25%. */
  blackHoleBonus: boolean;
  /** Stargazing: Super Stars Fish Income Multiplier. +1.25% per level (max 15). */
  superStarsLevel: number;
  /** Cards: Infernal Mr Nibbles — % per level (flat 5× tick chance). */
  infernalMrNibblesPct: number;
  /** Cards: Infernal Mr Nibbles — level. */
  infernalMrNibblesLevel: number;
  /** Cards: Infernal Angler Drone Card — % per level (Tier 2 Dock Power). */
  infernalAnglerDronePct: number;
  /** Cards: Infernal Angler Drone Card — level. */
  infernalAnglerDroneLevel: number;
};

const STORAGE_KEY = "obeliskfarm:web:fishing_save.json:v1";
const FISHING_EXTERNAL_KEY = "obeliskfarm:web:fishing_external.json";

/** Sushi MC: min/max simulated openings (each = one Poisson draw for fish per Sushi). */
const SUSHI_MC_SUSHIS_MIN = 100;
const SUSHI_MC_SUSHIS_MAX = 100_000;

function getDefaultFishingState(): FishingState {
  const upgradeLevels: Partial<Record<FishingUpgradeId, number>> = {};
  const enhanceLevels: Partial<Record<EnhanceId, number>> = {};
  const computed = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels);
  const dronesPerDock: Record<DockId, number> = {} as Record<DockId, number>;
  DOCKS.forEach((d, i) => {
    dronesPerDock[d.id] = i === 0 ? Math.max(0, Math.round(computed.fishing_drone_cap)) : 0;
  });
  return {
    dronesPerDock,
    showDisabledFishGrayed: false,
    showPolyShardDroprate: true,
    useGemIncomeForCostEffic: true,
    activeDockId: "lake",
    upgradeLevels,
    enhanceLevels,
    fishCardTier: {},
    sushiCardTier: 0,
    fishingRodCardTier: 0,
    mrNibblesCardTier: 0,
    valuePackPotencyPoly: false,
    skillTreeLevels: {},
    legendaryFishFound: 0,
    abyssLegendaryCaught: false,
    divineRelic5xPoints: 0,
    mcHours: 8,
    mcRuns: 1000,
    sushiMcSushis: 1000,
    mrNibblesLevel: 0,
    mrNibblesQuestUnlocked: false,
    mrNibblesQuestRank: 0,
    mrNibblesSkin: false,
    poseidonIdolLevel: 0,
    tethysIdolLevel: 0,
    astraeusIdolLevel: 0,
    droneBasePowerWorld3Upgrade: 0,
    fishingDroneBasePowerWorld3: 0,
    workshopSushiTicksWorld3: 0,
    legendaryHaulerBundle: false,
    fishersBundle: false,
    anglerBundle: false,
    halfWayBundle: false,
    divineChallengeCoinLevel: 0,
    constructStatue: "none",
    cetusLevel: 0,
    blackHoleBonus: false,
    superStarsLevel: 0,
    infernalMrNibblesPct: 0,
    infernalMrNibblesLevel: 0,
    infernalAnglerDronePct: 0,
    infernalAnglerDroneLevel: 0,
  };
}
const GEMEV_EXTERNAL_KEY = "obeliskfarm:web:gemev_external.json";
const LOOTBUG_STORAGE_KEY = "obeliskfarm:web:lootbug_save.json:v1";
const GEMEV_STORAGE_KEY = "obeliskfarm:web:gemev_save.json:v1";

/** Sushi: base 90 ticks. Sushi Misc card: Card +5, Gilded +10, Poly +20. */
const SUSHI_BASE_TICKS = 90;
const SUSHI_CARD_TICKS: Record<FishCardTier, number> = { 0: 0, 1: 5, 2: 10, 3: 20 };
/** Fishing Rod card: Fishing Rod Power. Card 1.02×, Gilded 1.05×, Poly 1.10×. */
const FISHING_ROD_CARD_MULT: Record<FishCardTier, number> = { 0: 1, 1: 1.02, 2: 1.05, 3: 1.1 };

/** Legendary fish catch: 1/LEGENDARY_CATCH_BASE per 100% on last fish, max 9/LEGENDARY_CATCH_BASE. Angler fuel buff reduces effective base during buff uptime. */
const LEGENDARY_CATCH_BASE = 150_000;

/** Elixir 3× Fishing Tick Speed buff icon (same as Drone module). */
const ELIXIR_3X_FISHING_BUFF_ICON = "https://static.wikitide.net/shminerwiki/8/87/Triple_Fish_Tick_Chance.png";

const FISHING_ICON = "https://static.wikitide.net/shminerwiki/f/fb/Fishing_Button.png";
/** Divine Relic (5× tick chance): +2% per point. Wiki Divine Relic Cap. */
const CARDS_ICON_URL = "https://static.wikitide.net/shminerwiki/b/bc/Cards_Button.png";
const RELICS_ICON_URL = "https://static.wikitide.net/shminerwiki/4/45/Divine_Relic_Cap.png";

/** Gem icon for enhancement costs (wiki File:Gem.png). */
const GEM_ICON_URL = fishIconUrl("Gem.png");

/** Icon for Diverse Fishing Upgrades section (same as Drone Upgrades). */
const FISHING_UPGRADES_ICON = "https://static.wikitide.net/shminerwiki/4/4b/Upgrades_Button.png";

/** Skill point icon for Skill Tree costs (24px from wiki). */
const SKILL_POINT_ICON_URL = "https://static.wikitide.net/shminerwiki/thumb/5/51/Skill_Point.png/24px-Skill_Point.png";
/** 1 skill point = 125 gems (for cost efficiency: marginal % per gem). */
const GEMS_PER_SKILL_POINT = 125;

const WIKI_SPRITES = "https://static.wikitide.net/shminerwiki";
/** Wiki gift sprite URL (same as Gem EV Gift chart). */
const GIFT_SPRITE_URL = `${WIKI_SPRITES}/2/24/Gift.png`;
/** 5× Fishing Tick Chance icon for breakdown bar chart. */
const FISH_TICK_5X_ICON = `${WIKI_SPRITES}/8/8d/5x_Fish_Tick_Chance.png`;

/** Real gift sprite with yellowish filter for breakdown: Gift Sushi, Gift 5× Tick. */
function GiftIcon() {
  return (
    <span className="fishingGiftIcon" aria-hidden title="Gift">
      <img src={GIFT_SPRITE_URL} alt="" width={14} height={14} />
    </span>
  );
}

/** Notice Fish Req -10% per level (additive: 3 levels = -30% → 0.70x). First level: 1→0.9 = 1/0.9 − 1 ≈ +11.1% effective gains when notice farming. */
const FRIENDSHIP_ENDED_NOTICE_MARGINAL_PCT = (1 / 0.9 - 1) * 100;
/** Token Multiplier: +0.05 per level (1.05, 1.10, …). Marginal gain = relative to current mult, e.g. 1.05→1.10 = 0.05/1.05 ≈ 4.76%. */
function tokenMultiplierMarginalPct(currentLevel: number): number {
  const currentMult = 1 + 0.05 * currentLevel;
  return (0.05 / currentMult) * 100;
}
/** Tiny Notice: +0.5% chance per level; Tiny = 10× value. Expected mult = 1 + chance×9. Marginal = relative to current mult. */
function tinyNoticeMarginalPct(currentLevel: number): number {
  const currentMult = 1 + currentLevel * 0.005 * 9;
  return (0.005 * 9 / currentMult) * 100;
}


function parseNumber(raw: string): number | null {
  const cleaned = raw.trim().replaceAll(",", ".").replaceAll(" ", "");
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

function endsWithDecimalSeparator(raw: string): boolean {
  const t = raw.trim();
  return t.endsWith(".") || t.endsWith(",");
}

function clamp(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, n));
}

/** Format minutes per hour as "m:ss" (e.g. 15.5 → "15:30"). */
function formatElixirMinSecPerHour(minPerHour: number): string {
  if (!Number.isFinite(minPerHour) || minPerHour < 0) return "0:00";
  const m = Math.floor(minPerHour);
  const s = Math.round((minPerHour - m) * 60);
  if (s >= 60) return `${m + 1}:00`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** Format hours as "h:mm h" (e.g. 5.2 → "5:12 h", 0.75 → "0:45 h"). */
function formatHoursToHhMin(hours: number): string {
  if (!Number.isFinite(hours) || hours < 0) return "0:00 h";
  const totalMin = Math.round(hours * 60);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${h}:${String(m).padStart(2, "0")} h`;
}

/** Toggles for fish card tier: None (0), Card 1.5× (1), Gilded 2× (2), Poly 4× (3). Same layout as Stargazing card tier row. */
function FishCardTierToggles(props: { value: FishCardTier; onChange: (t: FishCardTier) => void }) {
  const { value, onChange } = props;
  const cur = value;
  const mk = (tier: FishCardTier, label: string) => (
    <button
      type="button"
      className={`btn btnSecondary fishingCardTierBtn ${cur === tier ? "cardBtnActive" : ""}`}
      onClick={() => onChange(cur === tier ? 0 : tier)}
    >
      {label} {cur === tier ? "✓" : ""}
    </button>
  );
  return (
    <div className="fishingCardTierRow">
      {mk(1, "Card")}
      {mk(2, "Gilded")}
      {mk(3, "Poly")}
    </div>
  );
}


/** Interpolate green (t=1) → red (t=0). t in [0,1]. Muted palette. */
function heatmapColor(t: number): string {
  const clamped = Math.max(0, Math.min(1, t));
  const r = Math.round(140 + 70 * (1 - clamped));
  const g = Math.round(140 + 70 * clamped);
  const b = 120;
  return `rgb(${r},${g},${b})`;
}

/** Format "current→next" for the stat this upgrade changes. Used under upgrade name. Always show only this upgrade's own value (from 0), e.g. 0→1, 1.00×→1.05×. Pass upgradeLevels for level. */
function formatUpgradeNextEffect(
  upgradeId: FishingUpgradeId,
  current: ComputedFishingStats,
  next: ComputedFishingStats,
  upgradeLevels?: Partial<Record<FishingUpgradeId, number>>,
): string | null {
  switch (upgradeId) {
    case "fishing_rod": {
      const lvl = Math.floor(Number(upgradeLevels?.fishing_rod ?? 0));
      const base = 10;
      const cur = Math.round(base * Math.pow(1.16, lvl));
      const next = Math.round(base * Math.pow(1.16, lvl + 1));
      return `${cur}→${next}`;
    }
    case "fishing_drone": {
      const lvl = Math.floor(Number(upgradeLevels?.fishing_drone ?? 0));
      const perLvl = 1;
      return `${lvl * perLvl}→${(lvl + 1) * perLvl}`;
    }
    case "fishing_drone_2": {
      const lvl = Math.floor(Number(upgradeLevels?.fishing_drone_2 ?? 0));
      const perLvl = 2;
      return `${lvl * perLvl}→${(lvl + 1) * perLvl}`;
    }
    case "upgrade_boat": {
      const lvl = Math.floor(Number(upgradeLevels?.upgrade_boat ?? 0));
      return `${lvl}→${lvl + 1}`;
    }
    case "upgrade_t2_boat": {
      const lvl = Math.floor(Number(upgradeLevels?.upgrade_t2_boat ?? 0));
      return `${lvl}→${lvl + 1}`;
    }
    case "tick_speed": {
      const lvl = Math.floor(Number(upgradeLevels?.tick_speed ?? 0));
      const perLvl = -0.5;
      return `${(perLvl * lvl).toFixed(1)}s→${(perLvl * (lvl + 1)).toFixed(1)}s`;
    }
    case "fish_multiplier": {
      const lvl = Math.floor(Number(upgradeLevels?.fish_multiplier ?? 0));
      const curFactor = 1 + 0.03 * lvl;
      const nextFactor = 1 + 0.03 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "rod_multiplier": {
      const lvl = Math.floor(Number(upgradeLevels?.rod_multiplier ?? 0));
      const curFactor = 1 + 0.04 * lvl;
      const nextFactor = 1 + 0.04 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "drone_multiplier": {
      const lvl = Math.floor(Number(upgradeLevels?.drone_multiplier ?? 0));
      const curFactor = 1 + 0.06 * lvl;
      const nextFactor = 1 + 0.06 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "drone_base_power": {
      const lvl = Math.floor(Number(upgradeLevels?.drone_base_power ?? 0));
      const perLvl = 0.25;
      return `${(perLvl * lvl).toFixed(2)}→${(perLvl * (lvl + 1)).toFixed(2)}`;
    }
    case "drone_cloner": {
      const lvl = Math.floor(Number(upgradeLevels?.drone_cloner ?? 0));
      const curFactor = 1 + 0.05 * lvl;
      const nextFactor = 1 + 0.05 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "shiny_multiplier": {
      const lvl = Math.floor(Number(upgradeLevels?.shiny_multiplier ?? 0));
      const curFactor = 1 + 0.05 * lvl;
      const nextFactor = 1 + 0.05 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "poly_card_multi": {
      const lvl = Math.floor(Number(upgradeLevels?.poly_card_multi ?? 0));
      const curFactor = 1 + 0.08 * lvl;
      const nextFactor = 1 + 0.08 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "double_tick_chance": {
      const lvl = Math.floor(Number(upgradeLevels?.double_tick_chance ?? 0));
      const pct = 0.5;
      return `${(pct * lvl).toFixed(1)}→${(pct * (lvl + 1)).toFixed(2)}%`;
    }
    case "shiny_fish_chance": {
      const lvl = Math.floor(Number(upgradeLevels?.shiny_fish_chance ?? 0));
      const pct = 0.5;
      return `${(pct * lvl).toFixed(1)}→${(pct * (lvl + 1)).toFixed(2)}%`;
    }
    case "triple_tick_chance": {
      const lvl = Math.floor(Number(upgradeLevels?.triple_tick_chance ?? 0));
      const pct = 0.35;
      return `${(pct * lvl).toFixed(1)}→${(pct * (lvl + 1)).toFixed(2)}%`;
    }
    case "tier2_dock_power": {
      const lvl = Math.floor(Number(upgradeLevels?.tier2_dock_power ?? 0));
      const curFactor = 1 + 0.05 * lvl;
      const nextFactor = 1 + 0.05 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "super_shiny_chance": {
      const lvl = Math.floor(Number(upgradeLevels?.super_shiny_chance ?? 0));
      const pct = 1;
      return `${(pct * lvl).toFixed(1)}→${(pct * (lvl + 1)).toFixed(2)}%`;
    }
    default:
      return null;
  }
}

/** Format "current→next" for the stat this enhancement changes. Used under enhancement name. Always show only this enhancement's own value (from 0), e.g. 0→1, 1.00×→1.05×. Pass enhanceLevels for level. New enhancements must follow this pattern. */
function formatEnhanceNextEffect(
  enhanceId: EnhanceId,
  current: ComputedFishingStats,
  next: ComputedFishingStats,
  enhanceLevels?: Partial<Record<EnhanceId, number>>,
): string | null {
  switch (enhanceId) {
    case "enhance_fish_multiplier": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_fish_multiplier ?? 0));
      const curFactor = 1 + 0.05 * lvl;
      const nextFactor = 1 + 0.05 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "enhance_fishing_drone": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_fishing_drone ?? 0));
      const perLvl = 1;
      return `${lvl * perLvl}→${(lvl + 1) * perLvl}`;
    }
    case "enhance_fishing_drone_3": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_fishing_drone_3 ?? 0));
      const perLvl = 3;
      return `${lvl * perLvl}→${(lvl + 1) * perLvl}`;
    }
    case "enhance_rod_multiplier": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_rod_multiplier ?? 0));
      const curFactor = 1 + 0.05 * lvl;
      const nextFactor = 1 + 0.05 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "enhance_tick_speed": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_tick_speed ?? 0));
      const perLvl = -0.5;
      return `${(perLvl * lvl).toFixed(1)}s→${(perLvl * (lvl + 1)).toFixed(1)}s`;
    }
    case "enhance_drone_multiplier": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_drone_multiplier ?? 0));
      const curFactor = 1 + 0.08 * lvl;
      const nextFactor = 1 + 0.08 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "enhance_token_multiplier": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_token_multiplier ?? 0));
      const curFactor = 1 + 0.05 * lvl;
      const nextFactor = 1 + 0.05 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "enhance_shiny_multiplier": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_shiny_multiplier ?? 0));
      const curFactor = 1 + 0.05 * lvl;
      const nextFactor = 1 + 0.05 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "enhance_double_tick_chance": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_double_tick_chance ?? 0));
      const pct = 0.5;
      return `${(pct * lvl).toFixed(1)}→${(pct * (lvl + 1)).toFixed(2)}%`;
    }
    case "enhance_triple_tick_chance": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_triple_tick_chance ?? 0));
      const pct = 0.4;
      return `${(pct * lvl).toFixed(1)}→${(pct * (lvl + 1)).toFixed(2)}%`;
    }
    case "enhance_tier2_dock_power": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_tier2_dock_power ?? 0));
      const curFactor = 1 + 0.05 * lvl;
      const nextFactor = 1 + 0.05 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "enhance_tier2_dock_ticks": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_tier2_dock_ticks ?? 0));
      const perLvl = -1;
      return `${lvl * perLvl}→${(lvl + 1) * perLvl}`;
    }
    case "enhance_super_shiny_multi": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_super_shiny_multi ?? 0));
      const curFactor = 1 + 0.15 * lvl;
      const nextFactor = 1 + 0.15 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "enhance_poly_card_multi": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_poly_card_multi ?? 0));
      const curFactor = 1 + 0.1 * lvl;
      const nextFactor = 1 + 0.1 * (lvl + 1);
      return `${curFactor.toFixed(2)}×→${nextFactor.toFixed(2)}×`;
    }
    case "enhance_tiny_notice_chance": {
      const lvl = Math.floor(Number(enhanceLevels?.enhance_tiny_notice_chance ?? 0));
      const pct = 0.5;
      return `${(pct * lvl).toFixed(1)}→${(pct * (lvl + 1)).toFixed(2)}%`;
    }
    default:
      return null;
  }
}

/** Options for skill tree when computing total fish per hour (for marginal %). Includes store bundles and other SkillTreeOptions used by computeFishingStatsFromLevels. */
type TotalFishOptions = {
  skillTreeLevels?: Partial<Record<FishingSkillId, number>>;
  fishCardTier?: Partial<Record<string, number>>;
  legendaryFishFound?: number;
  /** Abyss Legendary (Cthulhu) tribute 1: All docks tick req -10% and Super Shiny Multi +3× */
  abyssLegendaryCaught?: boolean;
  /** Fishing Rod card tier (0–3) for rod power mult 1 / 1.02 / 1.05 / 1.10. */
  fishingRodCardTier?: FishCardTier;
  /** Mr Nibbles Card: 0 = none, 1 = +1% Tiny Notice, 2 = +2%, 3 = +4%. */
  mrNibblesCardTier?: FishCardTier;
  relic5xPoints?: number;
  mrNibblesLevel?: number;
  mrNibblesQuestRank?: number;
  poseidonIdolLevel?: number;
  tethysIdolLevel?: number;
  astraeusIdolLevel?: number;
  droneBasePowerWorld3Upgrade?: number;
  fishingDroneBasePowerWorld3?: number;
  legendaryHaulerBundle?: boolean;
  fishersBundle?: boolean;
  anglerBundle?: boolean;
  halfWayBundle?: boolean;
  divineChallengeCoinLevel?: number;
  infernalMrNibblesPct?: number;
  infernalMrNibblesLevel?: number;
  infernalAnglerDronePct?: number;
  infernalAnglerDroneLevel?: number;
  constructStatue?: "none" | "gilded" | "platinized";
  cetusLevel?: number;
  blackHoleBonus?: boolean;
  superStarsLevel?: number;
};

/**
 * Total fish per hour for given levels and dock assignment (same formula as Fishing gains list).
 * Used to compute marginal % gain from +1 level by comparing total with hypothetical levels.
 * When extraTicksPerHour is passed (Angler + Lootbug + Gift Sushi), fills use base + extra so the total matches the displayed gains list and marginal % is correct.
 */
function computeTotalFishPerHour(
  upgradeLevels: Partial<Record<FishingUpgradeId, number>>,
  enhanceLevels: Partial<Record<EnhanceId, number>>,
  dronesPerDock: Record<DockId, number>,
  activeDockId: DockId,
  elixir3xFishingExternal: { uptimeFraction: number },
  skillOptions?: TotalFishOptions,
  extraTicksPerHour: number = 0,
): number {
  const stats = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, skillOptions);
  const s = stats.shiny_fish_chance_pct / 100;
  const s2 = stats.super_shiny_chance_pct / 100;
  const expectedShinyMulti =
    (1 - s) * 1 +
    s * (1 - s2) * stats.shiny_multiplier +
    s * s2 * stats.shiny_multiplier * stats.super_shiny_multiplier;
  const tickDurationSec = Math.max(1, 60 + stats.fishing_tick_reduction);
  const effectiveTickSec = effectiveFishingTickSec(tickDurationSec, elixir3xFishingExternal.uptimeFraction);
  const doublePct = stats.double_tick_chance_pct / 100;
  const triplePct = stats.triple_tick_chance_pct / 100;
  const fivePct = stats.five_tick_chance_pct / 100;
  const expectedRollsPerFill = (1 + doublePct) * (1 + 2 * triplePct) * (1 + 4 * fivePct);
  const rodMult = (skillOptions?.fishingRodCardTier != null) ? FISHING_ROD_CARD_MULT[skillOptions.fishingRodCardTier] : 1;
  const baseRod = Math.round(stats.fishing_rod_power * rodMult); // round only once, after card mult
  const tickOpts = {
    motleySchoolLevel: skillOptions?.skillTreeLevels?.["motley_school"] ?? 0,
    enhanceT2DockTicksLevel: enhanceLevels["enhance_tier2_dock_ticks"] ?? 0,
    abyssLegendaryCaught: skillOptions?.abyssLegendaryCaught ?? false,
  };
  let total = 0;
  for (const set of AQUARIUM) {
    const dock = DOCKS.find((d) => d.id === set.dockId)!;
    const ticksNeeded = getEffectiveTicksNeeded(dock, tickOpts);
    const rod = activeDockId === set.dockId ? baseRod : 0;
    const n = dronesPerDock[set.dockId] ?? 0;
    const isT2 = dock.tier === 2;
    const powerOnThisDock = isT2
      ? (rod + n * stats.drone_base_power) * stats.tier2_dock_power_mult
      : rod + n * stats.drone_base_power;
    const dockFillsPerHour = 3600 / (ticksNeeded * effectiveTickSec);
    const fillsPerHour = dockFillsPerHour + extraTicksPerHour / ticksNeeded;
    for (const f of set.fish) {
      total +=
        fillsPerHour *
        expectedRollsPerFill *
        expectedCatchesPerRoll(powerOnThisDock, f.powerRating) *
        stats.fish_income_multi *
        expectedShinyMulti;
    }
  }
  return total;
}

/**
 * Greedy dock assignment for +% gains: rod and all drones on the highest unlocked dock (last in progression).
 * E.g. if you just unlocked T2 and Cave is your top dock, everything is assumed on Cave. Marginal % then reflects gain when everything is concentrated on that one dock.
 */
function getGreedyDockAssignment(
  upgradeLevels: Partial<Record<FishingUpgradeId, number>>,
  enhanceLevels: Partial<Record<EnhanceId, number>>,
  skillOptions: TotalFishOptions,
  _elixir3xFishingExternal: { uptimeFraction: number },
  _extraTicksPerHour: number,
): { activeDockId: DockId; dronesPerDock: Record<DockId, number> } {
  const stats = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, skillOptions);
  const droneCap = Math.floor(stats.fishing_drone_cap);
  const availableDocks = DOCKS.filter((d, i) => {
    if (d.tier === 1) return stats.boat_level >= i;
    return (stats.t2_boat_level ?? 0) >= i - 5;
  });
  if (availableDocks.length === 0) {
    const fallback: Record<DockId, number> = {} as Record<DockId, number>;
    DOCKS.forEach((d) => (fallback[d.id] = 0));
    return { activeDockId: DOCKS[0]!.id as DockId, dronesPerDock: fallback };
  }
  const maxDock = availableDocks[availableDocks.length - 1]!;
  const dronesPerDock: Record<DockId, number> = {} as Record<DockId, number>;
  for (const d of DOCKS) dronesPerDock[d.id as DockId] = d.id === maxDock.id ? droneCap : 0;
  return { activeDockId: maxDock.id as DockId, dronesPerDock };
}

/** Same formula as computeTotalFishPerHour but from precomputed stats (for skill breakdown). Includes extraTicksPerHour so breakdown totals match main total. effectiveTicksByDock: use when caller has it (Motley School, T2 Dock Ticks, Abyss Legendary). */
function computeTotalFishPerHourFromStats(
  stats: ComputedFishingStats,
  dronesPerDock: Record<DockId, number>,
  activeDockId: DockId,
  elixir3xFishingExternal: { uptimeFraction: number },
  effectiveRodPowerOverride?: number,
  extraTicksPerHour: number = 0,
  effectiveTicksByDock?: Partial<Record<DockId, number>>,
): number {
  const s = stats.shiny_fish_chance_pct / 100;
  const s2 = stats.super_shiny_chance_pct / 100;
  const expectedShinyMulti =
    (1 - s) * 1 +
    s * (1 - s2) * stats.shiny_multiplier +
    s * s2 * stats.shiny_multiplier * stats.super_shiny_multiplier;
  const tickDurationSec = Math.max(1, 60 + stats.fishing_tick_reduction);
  const effectiveTickSec = effectiveFishingTickSec(tickDurationSec, elixir3xFishingExternal.uptimeFraction);
  const doublePct = stats.double_tick_chance_pct / 100;
  const triplePct = stats.triple_tick_chance_pct / 100;
  const fivePct = stats.five_tick_chance_pct / 100;
  const expectedRollsPerFill = (1 + doublePct) * (1 + 2 * triplePct) * (1 + 4 * fivePct);
  const rodForActive = effectiveRodPowerOverride ?? stats.fishing_rod_power;
  let total = 0;
  for (const set of AQUARIUM) {
    const dock = DOCKS.find((d) => d.id === set.dockId)!;
    const ticksNeeded = effectiveTicksByDock?.[dock.id] ?? dock.baseTicksNeeded;
    const rod = activeDockId === set.dockId ? rodForActive : 0;
    const n = dronesPerDock[set.dockId] ?? 0;
    const isT2 = dock.tier === 2;
    const powerOnThisDock = isT2
      ? (rod + n * stats.drone_base_power) * stats.tier2_dock_power_mult
      : rod + n * stats.drone_base_power;
    const dockFillsPerHour = 3600 / (ticksNeeded * effectiveTickSec);
    const fillsPerHour = dockFillsPerHour + extraTicksPerHour / ticksNeeded;
    for (const f of set.fish) {
      total +=
        fillsPerHour *
        expectedRollsPerFill *
        expectedCatchesPerRoll(powerOnThisDock, f.powerRating) *
        stats.fish_income_multi *
        expectedShinyMulti;
    }
  }
  return total;
}

function NumberRow(props: {
  label: string;
  iconUrl?: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  decimals?: number;
  inputMode?: "decimal" | "numeric";
  suffix?: string;
}) {
  const {
    label,
    iconUrl,
    value,
    onChange,
    min = -Infinity,
    max = Infinity,
    decimals = 0,
    inputMode = "numeric",
    suffix = "",
  } = props;
  const [raw, setRaw] = useState<string>(Number.isFinite(value) ? String(value) : "");

  useEffect(() => {
    setRaw(Number.isFinite(value) ? String(value) : "");
  }, [value]);

  function commitFromRaw(nextRaw: string) {
    const trimmed = nextRaw.trim();
    if (!trimmed) {
      const v0 = clamp(0, min, max);
      onChange(v0);
      setRaw(String(v0));
      return;
    }
    const parsed = parseNumber(nextRaw);
    if (parsed === null) {
      setRaw(Number.isFinite(value) ? String(value) : "");
      return;
    }
    const v = clamp(parsed, min, max);
    onChange(v);
    setRaw(String(v));
  }

  const displayValue = Number.isFinite(value) ? value.toFixed(decimals) : "—";

  return (
    <div className="fishingRow">
      <div className="fishingLabel">
        <div className="fishingLabelLeft">
          {iconUrl ? (
            <img src={iconUrl} alt="" className="iconSmall" style={{ width: 18, height: 18, objectFit: "contain" }} />
          ) : null}
          <span className="fishingLabelName">{label}</span>
        </div>
      </div>
      <div className="fishingRowInputBlock">
        <div className="fishingInputWrap">
          <input
            className="input"
            inputMode={inputMode}
            value={raw}
            onChange={(e) => {
              const nextRaw = e.target.value;
              setRaw(nextRaw);
              if (endsWithDecimalSeparator(nextRaw)) return;
              const parsed = parseNumber(nextRaw);
              if (parsed === null) return;
              onChange(clamp(parsed, min, max));
            }}
            onBlur={() => commitFromRaw(raw)}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
            }}
          />
        </div>
        <span className="mono fishingRowValue">{displayValue}{suffix}</span>
      </div>
    </div>
  );
}

/** Inline rank stepper (minus, "rank", input, plus) with local input state. */
function InlineRankStepper(props: { value: number; min: number; max: number; onChange: (v: number) => void }) {
  const { value, min, max, onChange } = props;
  const [focused, setFocused] = useState(false);
  const [raw, setRaw] = useState(() => String(value));
  useEffect(() => {
    if (!focused) setRaw(String(value));
  }, [value, focused]);
  const commit = () => {
    setFocused(false);
    const parsed = parseInt(raw.trim().replaceAll(",", "."), 10);
    if (!Number.isFinite(parsed)) {
      setRaw(String(value));
      return;
    }
    onChange(clamp(Math.floor(parsed), min, max));
  };
  return (
    <div className="fishingStepperLvlBlock">
      <button type="button" className="btn fishingStepperMinusBtn" onClick={() => onChange(Math.max(min, value - 1))} disabled={value <= min} aria-label="Decrease by 1">−</button>
      <span className="fishingUpgradeLevelLabel">rank</span>
      <input
        type="text"
        inputMode="numeric"
        className="input mono fishingStepperLevelInput fishingStepperLevelInputWide"
        value={focused ? raw : String(value)}
        onChange={(e) => setRaw(e.target.value)}
        onFocus={() => { setFocused(true); setRaw(String(value)); }}
        onBlur={commit}
        onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); }}
        aria-label="Quest rank"
      />
      <button type="button" className="btn fishingStepperPlusBtn" onClick={() => onChange(Math.min(max, value + 1))} disabled={value >= max} aria-label="Increase by 1">+</button>
    </div>
  );
}

/** Row with icon + label, editable level (no cap shown), single +1 button, optional effect text. */
function StepperRow(props: {
  label: string;
  iconUrl?: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
  tooltipContent?: import("../../components/Tooltip").TooltipContent;
  effectText?: ReactNode;
  /** Optional extra class for the level input (e.g. wider for 3+ digits). */
  inputClassName?: string;
}) {
  const { label, iconUrl, value, min, max, onChange, tooltipContent, effectText, inputClassName } = props;
  const [focused, setFocused] = useState(false);
  const [raw, setRaw] = useState(() => String(value));

  useEffect(() => {
    if (!focused) setRaw(String(value));
  }, [value, focused]);

  const commit = () => {
    setFocused(false);
    const parsed = parseInt(raw.trim().replaceAll(",", "."), 10);
    if (!Number.isFinite(parsed)) {
      setRaw(String(value));
      return;
    }
    const clamped = clamp(Math.floor(parsed), min, max);
    onChange(clamped);
    setRaw(String(clamped));
  };

  return (
    <div className={`fishingStepperRow ${inputClassName ? "fishingStepperRowWideLvl" : ""}`.trim()}>
      <div className="fishingStepperNameBlock">
        {iconUrl ? (
          <img src={iconUrl} alt="" className="fishingUpgradeIcon" aria-hidden />
        ) : null}
        <div className="fishingStepperLabelBlock">
          <span className="fishingStepperRowLabel">{label}</span>
          {tooltipContent ? (
            <Tooltip content={tooltipContent} label="?" />
          ) : null}
        </div>
      </div>
      <div className="fishingStepperLvlBlock">
        <button
          type="button"
          className="btn fishingStepperMinusBtn"
          onClick={() => onChange(Math.max(min, value - 1))}
          disabled={value <= min}
          aria-label="Decrease by 1"
        >
          −
        </button>
        <span className="fishingUpgradeLevelLabel">lvl</span>
        <input
          type="text"
          inputMode="numeric"
          className={`input mono fishingStepperLevelInput ${inputClassName ?? ""}`.trim()}
          value={focused ? raw : String(value)}
          onChange={(e) => setRaw(e.target.value)}
          onFocus={() => {
            setFocused(true);
            setRaw(String(value));
          }}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.currentTarget.blur();
          }}
          aria-label={`Level for ${label}`}
        />
        <button
          type="button"
          className="btn fishingStepperPlusBtn"
          onClick={() => onChange(Math.min(max, value + 1))}
          disabled={value >= max}
          aria-label="Increase by 1"
        >
          +
        </button>
      </div>
      {effectText != null ? <span className="mono fishingStepperEffect">{effectText}</span> : null}
    </div>
  );
}

/** Read-only stat row: label and value on one line. */
function StatRow(props: {
  label: string;
  iconUrl?: string;
  statIconUrl?: string;
  value: number;
  decimals?: number;
  suffix?: string;
}) {
  const { label, iconUrl, statIconUrl, value, decimals = 0, suffix = "" } = props;
  const displayValue = Number.isFinite(value) ? value.toFixed(decimals) : "—";
  return (
    <div className="fishingRow fishingRowInline">
      <div className="fishingLabelLeft">
        {iconUrl ? (
          <img src={iconUrl} alt="" className="iconSmall" style={{ width: 18, height: 18, objectFit: "contain" }} />
        ) : null}
        {statIconUrl ? (
          <img src={statIconUrl} alt="" className="iconSmall" style={{ width: 18, height: 18, objectFit: "contain" }} />
        ) : null}
        <span className="fishingLabelName">{label}</span>
      </div>
      <span className="mono fishingRowValue">{displayValue}{suffix}</span>
    </div>
  );
}

const statsTooltip = {
  title: "Fishing stats",
  sections: [
    {
      heading: "Source",
      lines: [
        "Values from your upgrade and enhancement levels.",
        "Includes boat levels (Upgrade Boat / Upgrade T2 Boat).",
      ],
    },
    {
      heading: "Drones and gains",
      lines: [
        "Each fishing drone adds drone base power to its dock.",
        "Dock power = rod (on that dock) + drones there × drone base power.",
        "Higher power increases catch chance and fish per hour.",
      ],
    },
    {
      heading: "Tick reduction",
      lines: [
        "Seconds reduced from base 60s per tick.",
        "Example: -40 means 20s per tick.",
      ],
    },
    {
      heading: "Double / triple / 5× tick chance",
      lines: [
        "Three multipliers. When the tick bar fills: double 2×, triple 3×, 5× gives 5×.",
        "They multiply together (e.g. 2× and 3× and 5× → 30×).",
        "5× from fishing only is 0%; game can add more from relics, store, or cards.",
      ],
    },
    {
      heading: "Shiny and super shiny",
      lines: [
        "Shiny works like a crit: a chance to multiply the catch (base 5×).",
        "Super shiny only rolls when the catch is already shiny; base multiplier 3× on top.",
      ],
    },
    {
      heading: "Elixir buff",
      lines: [
        "Buff uptime is calculated in the Drone module and applied to fish/h.",
        "Open Drone to sync.",
      ],
    },
  ],
};

const costEfficUpgradeTooltip = {
  title: "Cost efficiency",
  sections: [
    {
      heading: "Formula",
      lines: [
        "Marginal % ÷ time to next (hours).",
        "Time = fish amount ÷ fish per hour.",
      ],
    },
    {
      heading: "Scale",
      lines: [
        "Same heatmap across upgrades, enhancements, skill tree, fish cards.",
        "Higher = more gain per hour.",
      ],
    },
  ],
};

const dockScoreTooltip = {
  title: "Dock Score",
  sections: [
    {
      heading: "What it is",
      lines: [
        "Sum of cost efficiency per cost fish.",
        "Per fish type (dock): only the highest cost effic. among upgrades that cost that fish.",
      ],
    },
    {
      heading: "Use",
      lines: [
        "Use it to see which dock to focus on for best efficiency.",
        "Higher score means this floor offers more strong upgrades across different fish.",
      ],
    },
  ],
};

const costEfficGemTooltip = {
  title: "Cost efficiency",
  sections: [
    {
      heading: "Toggle",
      lines: [
        "ON: Marginal % ÷ hours to earn gem cost.",
        "Hours = gem cost ÷ Gem EV gems/h.",
        "OFF: Marginal % ÷ gem cost × 100.",
        "Gem-absolute, own heatmap.",
      ],
    },
    {
      heading: "Scale",
      lines: [
        "Same heatmap across all sections.",
        "Higher = better.",
      ],
    },
    {
      heading: "Gem EV",
      lines: ["Open Gem EV Calculator to sync gems/h (when toggle ON)."],
    },
  ],
};

const costEfficSkillTooltip = {
  title: "Cost efficiency",
  sections: [
    {
      heading: "Toggle",
      lines: [
        "ON: Marginal % ÷ hours to earn gem cost. 1 SP = 125 gems.",
        "OFF: Marginal % ÷ gem cost × 100.",
        "Gem-absolute, own heatmap.",
      ],
    },
    {
      heading: "Scale",
      lines: [
        "Same heatmap across all sections.",
        "Higher = better.",
      ],
    },
    {
      heading: "Gem EV",
      lines: ["Open Gem EV Calculator to sync gems/h (when toggle ON)."],
    },
  ],
};

const costEfficFishCardTooltip = {
  title: "Cost efficiency",
  sections: [
    {
      heading: "Toggle",
      lines: [
        "ON: Marginal % ÷ hours to earn gem cost.",
        "Cost: gems or 1500 (Rod).",
        "OFF: Marginal % ÷ gem cost × 100.",
        "Gem-absolute, own heatmap.",
      ],
    },
    {
      heading: "Scale",
      lines: [
        "Same heatmap across all sections.",
        "Higher = better.",
      ],
    },
    {
      heading: "Gem EV",
      lines: ["Open Gem EV Calculator to sync gems/h (when toggle ON)."],
    },
  ],
};

const boxplotStatsTooltip = {
  title: "Box plot abbreviations",
  lines: [
    "min: minimum value in the MC sample.",
    "Q1: first quartile (25th percentile).",
    "med: median (50th percentile).",
    "Q3: third quartile (75th percentile).",
    "max: maximum value in the MC sample.",
  ],
};

/** Legendary fish card effects by id (FYI only; not used in any calculations). */
const LEGENDARY_FISH_CARD_EFFECTS: Record<string, { title: string; standard: string; gilded: string; polychrome: string }> = {
  lake_legendary: { title: "Rainbow Trout", standard: "Rainbow Floor Multi +25%", gilded: "+50%", polychrome: "+100%" },
  desert_legendary: { title: "Dune's Eelworm", standard: "Golden Portal Multi +40%", gilded: "+80%", polychrome: "+140%" },
  tundra_legendary: { title: "Glacial Shellstealer", standard: "Rainbow Vein Multi +30%", gilded: "+60%", polychrome: "+100%" },
  ocean_legendary: { title: "Megalodon", standard: "Star Supernova Multi +35%", gilded: "+70%", polychrome: "+125%" },
  nuclear_legendary: { title: "Radioactive Slug", standard: "Bomb Damage / Exp Gain +300%", gilded: "+500%", polychrome: "+1100%" },
  abyss_legendary: { title: "Cthulhu", standard: "Divine Relics Cap +1", gilded: "+2", polychrome: "+4" },
  cave_legendary: { title: "Glimmering Geoduck", standard: "Banked Freebie Cap +16%", gilded: "+32%", polychrome: "+64%" },
  volcano_legendary: { title: "Laviathan", standard: "Bar Output Multiplier +40%", gilded: "+80%", polychrome: "+140%" },
  sky_legendary: { title: "Storm Serpent", standard: "Super Stonks Multiplier +14%", gilded: "+28%", polychrome: "+56%" },
  solaris_legendary: { title: "Melting Gibbous", standard: "Gems From Freebie +10%", gilded: "+20%", polychrome: "+30%" },
  galaxy_legendary: { title: "Blackened Basker", standard: "Super Stonks Chance +0.15%", gilded: "+0.30%", polychrome: "+0.60%" },
};

export function Fishing() {
  const [state, setState] = useState<FishingState>(() => {
    const saved = loadJson<SavedState>(STORAGE_KEY);
    const upgradeLevels = saved?.upgradeLevels ?? {};
    const enhanceLevels = saved?.enhanceLevels ?? {};
    const computed = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels);
    const dronesPerDock: Record<DockId, number> = {} as Record<DockId, number>;
    DOCKS.forEach((d, i) => {
      dronesPerDock[d.id] = saved?.dronesPerDock?.[d.id] ?? (i === 0 ? Math.max(0, Math.round(computed.fishing_drone_cap)) : 0);
    });
    const showDisabledFishGrayed = saved?.showDisabledFishGrayed ?? false;
    const showPolyShardDroprate = saved?.showPolyShardDroprate ?? true;
    const useGemIncomeForCostEffic = saved?.useGemIncomeForCostEffic ?? true;
    const activeDockId: DockId = (saved?.activeDockId != null ? saved.activeDockId : "lake") as DockId;
    const fishCardTier = saved?.fishCardTier ?? {};
    const sushiCardTier = clamp(Math.trunc(Number(saved?.sushiCardTier ?? 0)), 0, 3) as FishCardTier;
    const valuePackPotencyPoly = saved?.valuePackPotencyPoly ?? false;
    const skillTreeLevels = saved?.skillTreeLevels ?? {};
    const legendaryFishFound = clamp(Number(saved?.legendaryFishFound ?? 0), 0, 11);
    const abyssLegendaryCaught = Boolean(saved?.abyssLegendaryCaught ?? false);
    const fishingRodCardTier = clamp(Math.trunc(Number(saved?.fishingRodCardTier ?? 0)), 0, 3) as FishCardTier;
    const mrNibblesCardTier = clamp(Math.trunc(Number(saved?.mrNibblesCardTier ?? 0)), 0, 3) as FishCardTier;
    const divineRelic5xPoints = Math.max(0, Math.trunc(Number(saved?.divineRelic5xPoints ?? 0)));
    const mcHours = clamp(Number(saved?.mcHours ?? 8), 0.1, 720);
    const mcRuns = clamp(Math.trunc(Number(saved?.mcRuns ?? 1000)), 1000, 100000);
    const sushiMcSushis = clamp(
      Math.trunc(Number(saved?.sushiMcSushis ?? 1000)),
      SUSHI_MC_SUSHIS_MIN,
      SUSHI_MC_SUSHIS_MAX,
    );
    const rawMrLvl = Number(saved?.mrNibblesLevel ?? 0);
    const mrNibblesLevel = Number.isFinite(rawMrLvl) ? Math.max(0, Math.trunc(rawMrLvl)) : 0;
    const rawMrQuest = Number(saved?.mrNibblesQuestRank ?? 0);
    const mrNibblesQuestRank = Number.isFinite(rawMrQuest) ? Math.max(0, Math.trunc(rawMrQuest)) : 0;
    const mrNibblesQuestUnlocked = saved?.mrNibblesQuestUnlocked === true || (saved?.mrNibblesQuestUnlocked === undefined && mrNibblesQuestRank > 0);
    const mrNibblesSkin = Boolean(saved?.mrNibblesSkin ?? false);
    const poseidonIdolLevel = Math.max(0, Math.trunc(Number(saved?.poseidonIdolLevel ?? 0)));
    const tethysIdolLevel = Math.max(0, Math.trunc(Number(saved?.tethysIdolLevel ?? 0)));
    const astraeusIdolLevel = Math.max(0, Math.trunc(Number(saved?.astraeusIdolLevel ?? 0)));
    const fishingDroneBasePowerWorld3 = Math.max(0, Math.trunc(Number(saved?.fishingDroneBasePowerWorld3 ?? 0)));
    const workshopSushiTicksWorld3 = Math.max(0, Math.trunc(Number(saved?.workshopSushiTicksWorld3 ?? 0)));
    const legendaryHaulerBundle = Boolean(saved?.legendaryHaulerBundle ?? false);
    const fishersBundle = Boolean(saved?.fishersBundle ?? false);
    const anglerBundle = Boolean(saved?.anglerBundle ?? false);
    const halfWayBundle = Boolean(saved?.halfWayBundle ?? false);
    const divineChallengeCoinLevel = Math.max(0, Math.trunc(Number(saved?.divineChallengeCoinLevel ?? 0)));
    const constructStatueRaw = saved?.constructStatue;
    const constructStatue =
      constructStatueRaw === "gilded" || constructStatueRaw === "platinized" ? constructStatueRaw : "none";
    const cetusLevel = Math.max(0, Math.trunc(Number(saved?.cetusLevel ?? 0)));
    const blackHoleBonus = Boolean(saved?.blackHoleBonus ?? false);
    const superStarsLevel = Math.max(0, Math.min(15, Math.trunc(Number(saved?.superStarsLevel ?? 0))));
    const droneBasePowerWorld3Upgrade = Math.max(0, Math.trunc(Number(saved?.droneBasePowerWorld3Upgrade ?? 0)));
    const infernalMrNibblesPct = Math.max(0, Number(saved?.infernalMrNibblesPct ?? 0));
    const infernalMrNibblesLevel = Math.max(0, Math.trunc(Number(saved?.infernalMrNibblesLevel ?? 0)));
    const infernalAnglerDronePct = Math.max(0, Number(saved?.infernalAnglerDronePct ?? 0));
    const infernalAnglerDroneLevel = Math.max(0, Math.trunc(Number(saved?.infernalAnglerDroneLevel ?? 0)));
    return { dronesPerDock, showDisabledFishGrayed, showPolyShardDroprate, useGemIncomeForCostEffic, activeDockId, upgradeLevels, enhanceLevels, fishCardTier, sushiCardTier, fishingRodCardTier, mrNibblesCardTier, valuePackPotencyPoly, skillTreeLevels, legendaryFishFound, abyssLegendaryCaught, divineRelic5xPoints, mcHours, mcRuns, sushiMcSushis, mrNibblesLevel, mrNibblesQuestUnlocked, mrNibblesQuestRank, mrNibblesSkin, poseidonIdolLevel, tethysIdolLevel, astraeusIdolLevel, droneBasePowerWorld3Upgrade, fishingDroneBasePowerWorld3, workshopSushiTicksWorld3, legendaryHaulerBundle, fishersBundle, anglerBundle, halfWayBundle, divineChallengeCoinLevel, constructStatue, cetusLevel, blackHoleBonus, superStarsLevel, infernalMrNibblesPct, infernalMrNibblesLevel, infernalAnglerDronePct, infernalAnglerDroneLevel };
  });

  useEffect(() => {
    saveJson(STORAGE_KEY, state);
  }, [state]);

  const [mcState, setMcState] = useState<{
    samples: number[] | null;
    samplesPerFish: Record<string, number[]> | null;
    running: boolean;
  }>({ samples: null, samplesPerFish: null, running: false });

  const [sushiMcState, setSushiMcState] = useState<{
    samples: number[] | null;
    samplesPerFish: Record<string, number[]> | null;
    running: boolean;
  }>({ samples: null, samplesPerFish: null, running: false });

  /** Bump when Drone (or other module) updates fishing_external so we re-read and re-render. */
  const [fishingExternalRevision, setFishingExternalRevision] = useState(0);
  const [tickChartOpen, setTickChartOpen] = useState(false);
  /** When user edits drone count in the input: { dockId, input }. On blur/Enter we parse and apply (capped to max). */
  const [editingDroneCount, setEditingDroneCount] = useState<{ dockId: DockId; input: string } | null>(null);
  useEffect(() => {
    const handler = () => setFishingExternalRevision((r) => r + 1);
    window.addEventListener("obelisk:fishing_external_updated", handler);
    return () => window.removeEventListener("obelisk:fishing_external_updated", handler);
  }, []);

  const upgradeLevels = state.upgradeLevels ?? {};
  const enhanceLevels = state.enhanceLevels ?? {};
  const skillTreeLevels = state.skillTreeLevels ?? {};
  const skillTreeOptions = {
    skillTreeLevels,
    fishCardTier: state.fishCardTier,
    legendaryFishFound: state.legendaryFishFound,
    relic5xPoints: state.divineRelic5xPoints,
    mrNibblesLevel: state.mrNibblesLevel,
    mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
    mrNibblesQuestRank: state.mrNibblesQuestRank,
    mrNibblesSkin: state.mrNibblesSkin,
    poseidonIdolLevel: state.poseidonIdolLevel,
    tethysIdolLevel: state.tethysIdolLevel,
    astraeusIdolLevel: state.astraeusIdolLevel,
    droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
    fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
    mrNibblesCardTier: state.mrNibblesCardTier,
    legendaryHaulerBundle: state.legendaryHaulerBundle,
    fishersBundle: state.fishersBundle,
    anglerBundle: state.anglerBundle,
    halfWayBundle: state.halfWayBundle,
    divineChallengeCoinLevel: state.divineChallengeCoinLevel,
    constructStatue: state.constructStatue,
    cetusLevel: state.cetusLevel,
    blackHoleBonus: state.blackHoleBonus,
    superStarsLevel: state.superStarsLevel,
    abyssLegendaryCaught: state.abyssLegendaryCaught,
    infernalMrNibblesPct: state.infernalMrNibblesPct,
    infernalMrNibblesLevel: state.infernalMrNibblesLevel,
    infernalAnglerDronePct: state.infernalAnglerDronePct,
    infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
  };
  const stats: ComputedFishingStats = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, skillTreeOptions);
  /** Effective ticks per dock (Motley School, T2 Dock Ticks Enhance, Abyss Legendary). Used for fills/h and display. */
  const effectiveTicksByDock = useMemo(() => {
    const opts = {
      motleySchoolLevel: skillTreeLevels["motley_school"] ?? 0,
      enhanceT2DockTicksLevel: enhanceLevels["enhance_tier2_dock_ticks"] ?? 0,
      abyssLegendaryCaught: state.abyssLegendaryCaught ?? false,
    };
    const out: Partial<Record<DockId, number>> = {};
    for (const dock of DOCKS) out[dock.id] = getEffectiveTicksNeeded(dock, opts);
    return out;
  }, [skillTreeLevels["motley_school"], enhanceLevels["enhance_tier2_dock_ticks"], state.abyssLegendaryCaught]);
  /** Rod power: base (from lib, unrounded) × Fishing Rod card mult (1× / 1.02× / 1.05× / 1.10×). Round only once at the end. */
  const effectiveRodPower = Math.round(stats.fishing_rod_power * FISHING_ROD_CARD_MULT[state.fishingRodCardTier]);

  /** Expected multiplier from Shiny (chance × multi) and Super Shiny (only when already shiny). */
  const expectedShinyMulti = useMemo(() => {
    const s = stats.shiny_fish_chance_pct / 100;
    const s2 = stats.super_shiny_chance_pct / 100;
    return (
      (1 - s) * 1 +
      s * (1 - s2) * stats.shiny_multiplier +
      s * s2 * stats.shiny_multiplier * stats.super_shiny_multiplier
    );
  }, [
    stats.shiny_fish_chance_pct,
    stats.super_shiny_chance_pct,
    stats.shiny_multiplier,
    stats.super_shiny_multiplier,
  ]);

  /** Card gain multiplier for a fish: tier 0 → 1×, Card → 1.5×, Gilded → 2×, Poly → 4×; when tier > 0 also × poly_card_gain_multi and Polychrome Potency Bundle 1.15 if active. */
  const getCardMulti = useMemo(() => {
    const poly = stats.poly_card_gain_multi * (state.valuePackPotencyPoly ? 1.15 : 1);
    return (fishId: string): number => {
      const tier = (state.fishCardTier[fishId] ?? 0) as FishCardTier;
      if (tier === 0) return 1;
      const base = tier === 1 ? 1.5 : tier === 2 ? 2 : 4;
      return base * poly;
    };
  }, [stats.poly_card_gain_multi, state.valuePackPotencyPoly, state.fishCardTier]);

  /** Docks reachable with current boat levels: T1 level 0 = Lake, 1 = +Desert, 2 = +Tundra, …; T2 level 1 = Cave, 2 = +Volcano, … (T2 only when t2_boat_level >= 1). */
  const availableDocks = useMemo(
    () =>
      DOCKS.filter((d, i) => {
        if (d.tier === 1) return stats.boat_level >= i;
        return (stats.t2_boat_level ?? 0) >= i - 5;
      }),
    [stats.boat_level, stats.t2_boat_level],
  );

  const totalDronesAssigned = useMemo(
    () => DOCKS.reduce((sum, d) => sum + (state.dronesPerDock[d.id] ?? 0), 0),
    [state.dronesPerDock],
  );
  const droneCap = Math.floor(stats.fishing_drone_cap);

  /** Fish from unlocked docks only (for fish cards display). */
  const availableFish = useMemo(() => {
    const dockIds = new Set(availableDocks.map((d) => d.id));
    return AQUARIUM.filter((s) => dockIds.has(s.dockId)).flatMap((s) => s.fish);
  }, [availableDocks]);

  /** Keep activeDockId on an available dock when boat levels change. */
  useEffect(() => {
    const ids = new Set(availableDocks.map((d) => d.id));
    if (!ids.has(state.activeDockId) && availableDocks.length > 0) {
      setState((prev) => ({ ...prev, activeDockId: availableDocks[0]!.id }));
    }
  }, [availableDocks, state.activeDockId]);

  function setDockDrones(dockId: DockId, delta: number) {
    setState((prev) => {
      const cur = prev.dronesPerDock[dockId] ?? 0;
      const total = DOCKS.reduce((s, d) => s + (prev.dronesPerDock[d.id] ?? 0), 0);
      const others = total - cur;
      const maxThis = Math.max(0, droneCap - others);
      const next = cur + delta;
      const clamped = Math.max(0, Math.min(maxThis, next));
      return { ...prev, dronesPerDock: { ...prev.dronesPerDock, [dockId]: clamped } };
    });
  }

  function setDockDronesTo(dockId: DockId, value: number) {
    setState((prev) => {
      const cur = prev.dronesPerDock[dockId] ?? 0;
      const total = DOCKS.reduce((s, d) => s + (prev.dronesPerDock[d.id] ?? 0), 0);
      const othersTotal = total - cur;
      const maxThis = Math.max(0, droneCap - othersTotal);
      const targetThis = Math.max(0, Math.min(droneCap, value));

      if (targetThis <= maxThis) {
        return { ...prev, dronesPerDock: { ...prev.dronesPerDock, [dockId]: targetThis } };
      }

      const remainingForOthers = droneCap - targetThis;
      if (remainingForOthers <= 0 || othersTotal <= 0) {
        const next: Record<DockId, number> = { ...prev.dronesPerDock };
        next[dockId] = targetThis;
        for (const d of DOCKS) if (d.id !== dockId) next[d.id] = 0;
        return { ...prev, dronesPerDock: next };
      }

      const otherDocks = DOCKS.filter((d) => d.id !== dockId);
      const scaled: { id: DockId; val: number; rounded: number }[] = otherDocks.map((d) => {
        const v = prev.dronesPerDock[d.id] ?? 0;
        const scaledVal = (remainingForOthers * v) / othersTotal;
        return { id: d.id, val: scaledVal, rounded: Math.max(0, Math.round(scaledVal)) };
      });
      let sumRounded = scaled.reduce((s, x) => s + x.rounded, 0);
      const diff = remainingForOthers - sumRounded;
      if (diff !== 0) {
        const idx = scaled.findIndex((x) => x.rounded > 0);
        if (idx >= 0) scaled[idx]!.rounded = Math.max(0, scaled[idx]!.rounded + diff);
      }
      const next: Record<DockId, number> = { ...prev.dronesPerDock };
      next[dockId] = targetThis;
      for (const x of scaled) next[x.id] = x.rounded;
      return { ...prev, dronesPerDock: next };
    });
  }

  function setFishingUpgradeLevel(upgradeId: FishingUpgradeId, delta: number) {
    const costs = UPGRADE_COSTS[upgradeId];
    if (!costs?.length) return;
    const maxLvl = costs[costs.length - 1]!.level;
    setState((prev) => {
      const prevLevels = prev.upgradeLevels ?? {};
      const cur = Math.max(0, Math.min(maxLvl, prevLevels[upgradeId] ?? 0));
      const next = Math.max(0, Math.min(maxLvl, cur + delta));
      return { ...prev, upgradeLevels: { ...prevLevels, [upgradeId]: next } };
    });
  }

  function setFishingEnhanceLevel(enhanceId: EnhanceId, delta: number) {
    const costsT1 = ENHANCE_COSTS_T1[enhanceId as keyof typeof ENHANCE_COSTS_T1];
    const costsT2 = ENHANCE_COSTS_T2[enhanceId as keyof typeof ENHANCE_COSTS_T2];
    const costs = costsT1 ?? costsT2;
    if (!costs?.length) return;
    const maxLvl = costs[costs.length - 1]!.level;
    setState((prev) => {
      const prevLevels = prev.enhanceLevels ?? {};
      const cur = Math.max(0, Math.min(maxLvl, prevLevels[enhanceId] ?? 0));
      const next = Math.max(0, Math.min(maxLvl, cur + delta));
      return { ...prev, enhanceLevels: { ...prevLevels, [enhanceId]: next } };
    });
  }

  function setSkillTreeLevel(skillId: FishingSkillId, delta: number) {
    const def = FISHING_SKILL_TREE.find((s) => s.id === skillId);
    if (!def || !def.costs.length) return;
    const maxLvl = def.costs.length;
    setState((prev) => {
      const prevLevels = prev.skillTreeLevels ?? {};
      const cur = Math.max(0, Math.min(maxLvl, prevLevels[skillId] ?? 0));
      const next = Math.max(0, Math.min(maxLvl, cur + delta));
      return { ...prev, skillTreeLevels: { ...prevLevels, [skillId]: next } };
    });
  }

  /** Power on a dock: rod only on active dock; plus drones. On T2 docks applies tier2_dock_power_mult. Tethys drone multi is global (in drone_base_power). */
  function powerForDock(dockId: DockId): number {
    const dock = DOCKS.find((d) => d.id === dockId)!;
    const rod = state.activeDockId === dockId ? effectiveRodPower : 0;
    const n = state.dronesPerDock[dockId] ?? 0;
    if (dock.tier === 2) {
      return (rod + n * stats.drone_base_power) * stats.tier2_dock_power_mult;
    }
    return rod + n * stats.drone_base_power;
  }

  /** Base tick duration in seconds (60 + reduction, e.g. -40 → 20). */
  const tickDurationSec = Math.max(1, 60 + stats.fishing_tick_reduction);
  /** Elixir 3× and Angler Drone: from Drone module (fishing_external.json). Open Drone to sync. */
  /** Gem EV total gems/h. Used for cost effic (marginal % per hour to earn gem cost). Open Gem EV to sync. */
  const gemEvGemsPerHour = (() => {
    const ext = loadJson<{ totalGemsPerHour?: number }>(GEMEV_EXTERNAL_KEY);
    return typeof ext?.totalGemsPerHour === "number" && ext.totalGemsPerHour > 0 ? ext.totalGemsPerHour : 0;
  })();

  const fishingExternalData = (() => {
    const ext = loadJson<{
      elixir3xFishingTickSpeedMinPerHour?: number;
      elixir3xFishingTickSpeedUptimeFraction?: number;
      anglerTicksPerHour?: number;
      anglerBaseTicksPerHour?: number;
      anglerBuffTicksPerHour?: number;
      anglerLegendaryBonusPct?: number;
      anglerBuffUptimeFraction?: number;
      lootbugFishing12TicksProcsPerHour?: number;
      giftSushiPerHour?: number;
      giftSushiFreebiePerHour?: number;
      giftSushiFounderPerHour?: number;
      lootfrogSushiPerHour?: number;
    }>(FISHING_EXTERNAL_KEY);
    const minPerHour = typeof ext?.elixir3xFishingTickSpeedMinPerHour === "number" ? ext.elixir3xFishingTickSpeedMinPerHour : 0;
    const uptimeFraction =
      typeof ext?.elixir3xFishingTickSpeedUptimeFraction === "number"
        ? Math.max(0, Math.min(1, ext.elixir3xFishingTickSpeedUptimeFraction))
        : 0;
    const anglerTicksPerHour = typeof ext?.anglerTicksPerHour === "number" ? Math.max(0, ext.anglerTicksPerHour) : 0;
    const anglerBaseTicksPerHour = typeof ext?.anglerBaseTicksPerHour === "number" ? Math.max(0, ext.anglerBaseTicksPerHour) : 0;
    const anglerBuffTicksPerHour = typeof ext?.anglerBuffTicksPerHour === "number" ? Math.max(0, ext.anglerBuffTicksPerHour) : 0;
    const anglerLegendaryBonusPct = typeof ext?.anglerLegendaryBonusPct === "number" ? Math.max(0, Math.min(52, ext.anglerLegendaryBonusPct)) : 0;
    const anglerBuffUptimeFraction = typeof ext?.anglerBuffUptimeFraction === "number" ? Math.max(0, Math.min(1, ext.anglerBuffUptimeFraction)) : 0;

    const rawLootbug = typeof ext?.lootbugFishing12TicksProcsPerHour === "number" ? Math.max(0, ext.lootbugFishing12TicksProcsPerHour) : 0;
    const lootbugState = loadJson<{ activeGemBuffs?: string[] }>(LOOTBUG_STORAGE_KEY);
    const buyGemBuffs = Array.isArray(lootbugState?.activeGemBuffs) ? lootbugState.activeGemBuffs : [];
    const lootbugFishing12TicksProcsPerHour = buyGemBuffs.includes("Fishing +12 Ticks") ? rawLootbug : 0;

    const gemevExt = loadJson<{ fishingUnlocked?: boolean }>(GEMEV_EXTERNAL_KEY);
    const fishingUnlocked = gemevExt?.fishingUnlocked !== false;
    let giftSushiPerHour = 0;
    let giftSushiFreebiePerHour = 0;
    let giftSushiFounderPerHour = 0;
    let giftPerHourFreebie = 0;
    let giftPerHourFounder = 0;
    let gift5xTickUptimeFraction = 0;
    if (fishingUnlocked) {
      const gemevSave = loadJson<{ params?: Partial<GameParameters>; statue_soprano_level?: number }>(GEMEV_STORAGE_KEY);
      const def = defaultGameParameters();
      const params: GameParameters = { ...def, ...gemevSave?.params } as GameParameters;
      if (typeof gemevSave?.statue_soprano_level === "number") {
        params.statue_soprano_level = Math.max(0, Math.min(3, gemevSave.statue_soprano_level));
      }
      giftSushiPerHour = Math.max(0, calculateGiftSushiPerHour(params));
      const bySource = calculateGiftSushiPerHourBySource(params);
      giftSushiFreebiePerHour = Math.max(0, bySource.freebie);
      giftSushiFounderPerHour = Math.max(0, bySource.founder);
      giftPerHourFreebie = Math.max(0, bySource.giftPerHourFreebie ?? 0);
      giftPerHourFounder = Math.max(0, bySource.giftPerHourFounder ?? 0);
      gift5xTickUptimeFraction = calculateGift5xTickUptimeFraction(params);
    }
    const lootfrogSushiPerHour = typeof ext?.lootfrogSushiPerHour === "number" ? Math.max(0, ext.lootfrogSushiPerHour) : 0;

    return { elixir3xFishingExternal: { minPerHour, uptimeFraction }, anglerTicksPerHour, anglerBaseTicksPerHour, anglerBuffTicksPerHour, anglerLegendaryBonusPct, anglerBuffUptimeFraction, lootbugFishing12TicksProcsPerHour, giftSushiPerHour, giftSushiFreebiePerHour, giftSushiFounderPerHour, giftPerHourFreebie, giftPerHourFounder, gift5xTickUptimeFraction, lootfrogSushiPerHour };
  })();
  const elixir3xFishingExternal = fishingExternalData.elixir3xFishingExternal;
  const anglerTicksPerHour = fishingExternalData.anglerTicksPerHour;
  const anglerBaseTicksPerHour = fishingExternalData.anglerBaseTicksPerHour;
  const anglerBuffTicksPerHour = fishingExternalData.anglerBuffTicksPerHour;
  const anglerLegendaryBonusPct = fishingExternalData.anglerLegendaryBonusPct;
  const anglerBuffUptimeFraction = fishingExternalData.anglerBuffUptimeFraction;
  const lootbugFishing12TicksProcsPerHour = fishingExternalData.lootbugFishing12TicksProcsPerHour;
  const giftSushiPerHour = fishingExternalData.giftSushiPerHour;
  const giftSushiFreebiePerHour = fishingExternalData.giftSushiFreebiePerHour ?? 0;
  const giftSushiFounderPerHour = fishingExternalData.giftSushiFounderPerHour ?? 0;
  const giftPerHourFreebie = fishingExternalData.giftPerHourFreebie ?? 0;
  const giftPerHourFounder = fishingExternalData.giftPerHourFounder ?? 0;
  const giftPerHourTotal = giftPerHourFreebie + giftPerHourFounder;
  const gift5xTickUptimeFraction = fishingExternalData.gift5xTickUptimeFraction ?? 0;
  const lootfrogSushiPerHour = fishingExternalData.lootfrogSushiPerHour ?? 0;
  /** Angler fuel buff: +X% Legendary Fish Chance during buff uptime. Effective base = 150k × (1 − bonus% × uptime) for rate. */
  const effectiveLegendaryCatchBase = Math.max(1, LEGENDARY_CATCH_BASE * (1 - (anglerLegendaryBonusPct / 100) * anglerBuffUptimeFraction));
  /** Display denominator: when Angler buff is on, show "when buff active" base (matches in-game tooltip), else effective base. */
  const effectiveLegendaryCatchBaseDisplay =
    anglerLegendaryBonusPct > 0
      ? Math.max(1, LEGENDARY_CATCH_BASE * (1 - anglerLegendaryBonusPct / 100))
      : effectiveLegendaryCatchBase;

  const effectiveTickSec = effectiveFishingTickSec(tickDurationSec, elixir3xFishingExternal.uptimeFraction);
  /** Fish/h multiplier from Elixir 3× buff (1 = no buff, 3 = 100% uptime). */
  const elixir3xFishingMulti =
    effectiveTickSec > 0 ? Math.min(3, tickDurationSec / effectiveTickSec) : 1;

  /** When a tick from Angler, Lootbug, or Sushi happens, it adds tick-bar units to every dock. Divide by baseTicksNeeded to get fills per dock (e.g. Desert: 8 ticks = 1 fill). */
  const ticksPerSushiForGift = SUSHI_BASE_TICKS + SUSHI_CARD_TICKS[state.sushiCardTier];
  const giftSushiTicksPerHour = giftSushiPerHour * ticksPerSushiForGift;
  const giftSushiFreebieTicksPerHour = giftSushiFreebiePerHour * ticksPerSushiForGift;
  const giftSushiFounderTicksPerHour = giftSushiFounderPerHour * ticksPerSushiForGift;
  const lootfrogSushiTicksPerHour = lootfrogSushiPerHour * ticksPerSushiForGift;
  const extraTicksPerHour = anglerTicksPerHour + lootbugFishing12TicksProcsPerHour + giftSushiTicksPerHour + lootfrogSushiTicksPerHour + (state.workshopSushiTicksWorld3 ?? 0);
  /** Raw tick-bar units per hour (before double/triple/5× mult). Used for Sushi correspondence. */
  const rawTicksPerHour = (effectiveTickSec > 0 ? 3600 / effectiveTickSec : 0) + extraTicksPerHour;
  /** Double/triple/5× tick chance: mult (2×, 3×, 5×) from stats, multiplied together. Applies to Base, Angler, Lootbug, Gift Sushi, Lootfrog Sushi. */
  const tickMult =
    (1 + stats.double_tick_chance_pct / 100) *
    (1 + 2 * stats.triple_tick_chance_pct / 100) *
    (1 + 4 * stats.five_tick_chance_pct / 100);
  /** Extra effective ticks from Gift basic reward "5× Fishing Tick Chance" (uptime × 4× on that slice). Gift +25% does not apply to Sushi ticks. */
  const nonSushiRawTicksPerHour = Math.max(0, rawTicksPerHour - giftSushiTicksPerHour - lootfrogSushiTicksPerHour);
  const gift5xTickContribution = nonSushiRawTicksPerHour * tickMult * 4 * gift5xTickUptimeFraction;
  /** Total effective fishing ticks per hour (base×mult + Gift 5× contribution). Used for display. */
  const totalEffectiveTicksPerHour = rawTicksPerHour * tickMult + gift5xTickContribution;

  /** Row colors for breakdown (Stargazing-style blue gradient). */
  const TICK_CHART_ROW_COLORS: Record<string, string> = {
    base: "#90caf9",
    angler: "#42a5f5",
    lootbug: "#2196f3",
    giftSushi: "#1e88e5",
    lootfrogSushi: "#2e7d32",
    gift5x: "#1565c0",
  };

  /** Rows for the effective-ticks breakdown bar chart (modal). Only when there is something to show. Workshop Sushi (W3) is shown in the Sushi section, not here. */
  const tickChartRows = useMemo(() => {
    if (anglerTicksPerHour <= 0 && lootbugFishing12TicksProcsPerHour <= 0 && giftSushiTicksPerHour <= 0 && lootfrogSushiTicksPerHour <= 0 && gift5xTickContribution <= 0 && tickMult <= 1) return [];
    const baseVal = (effectiveTickSec > 0 ? 3600 / effectiveTickSec : 0) * tickMult;
    type Row = { key: string; label: string; value: number; color: string; icon?: ReactNode; subtitle?: string; tooltip: { title: string; lines: string[] } | null };
    const rows: (Row | null)[] = [
      { key: "base", label: "Base", value: baseVal, color: TICK_CHART_ROW_COLORS.base, tooltip: null },
      anglerTicksPerHour > 0 ? { key: "angler", label: "Angler Drone", value: anglerTicksPerHour * tickMult, color: TICK_CHART_ROW_COLORS.angler, tooltip: null } : null,
      lootbugFishing12TicksProcsPerHour > 0 ? { key: "lootbug", label: "Lootbug", value: lootbugFishing12TicksProcsPerHour * tickMult, color: TICK_CHART_ROW_COLORS.lootbug, tooltip: null } : null,
      giftSushiTicksPerHour > 0
        ? {
            key: "giftSushi",
            label: "Gift Sushi",
            value: giftSushiTicksPerHour * tickMult,
            color: TICK_CHART_ROW_COLORS.giftSushi,
            icon: <GiftIcon />,
            tooltip: {
              title: "Gift Sushi",
              lines: [
                "Freebie: Statue of Soprano (freebie gift chance). Founder/Supply: supply drop (1/1234 rare per drop, 10 gifts).",
                giftPerHourTotal > 0
                  ? `Gifts/h: ${giftPerHourTotal.toFixed(2)} (Freebie: ${giftPerHourFreebie.toFixed(2)}, Founder: ${giftPerHourFounder.toFixed(2)}).`
                  : "",
                "Includes double/triple tick mult, but not the 5× tick multi from Gift's 5× tick buff.",
              ].filter(Boolean),
            },
          }
        : null,
      lootfrogSushiTicksPerHour > 0
        ? {
            key: "lootfrogSushi",
            label: "Lootfrog Sushi",
            value: lootfrogSushiTicksPerHour * tickMult,
            color: TICK_CHART_ROW_COLORS.lootfrogSushi,
            tooltip: {
              title: "Lootfrog Sushi",
              lines: [
                "Sushi from Lootfrog (Drone module). Same ticks per Sushi as Gift Sushi. Open Drone to refresh.",
              ],
            },
          }
        : null,
      gift5xTickContribution > 0
        ? {
            key: "gift5x",
            label: "Gift 5× Tick",
            value: gift5xTickContribution,
            color: TICK_CHART_ROW_COLORS.gift5x,
            icon: <img src={FISH_TICK_5X_ICON} alt="" width={14} height={14} style={{ display: "block" }} />,
            tooltip: {
              title: "Gift 5× Tick",
              lines: [
                "Basic reward from Gifts: 5× Fishing Tick Chance, ~12.5 min per proc.",
                "Chance = P(basic roll) × 1/12 (when no rare wins). Rare outcomes replace the basic roll.",
                "Uptime from Freebie + Founder gifts. Extra effective ticks during that buff.",
              ],
            },
          }
        : null,
    ];
    return rows.filter((r): r is Row => r != null && r.value > 0);
  }, [
    effectiveTickSec,
    tickMult,
    anglerTicksPerHour,
    lootbugFishing12TicksProcsPerHour,
    giftSushiTicksPerHour,
    lootfrogSushiTicksPerHour,
    gift5xTickContribution,
    giftPerHourTotal,
    giftPerHourFreebie,
    giftPerHourFounder,
  ]);

  const totalSushiPerHour = giftSushiPerHour + lootfrogSushiPerHour;

  const fishingGainsRows = useMemo(() => {
    const dockIds = new Set(availableDocks.map((d) => d.id));
    const rod = effectiveRodPower;

    function powerForSet(dockId: DockId, rodHere: number, dronesHere: number): number {
      const dock = DOCKS.find((d) => d.id === dockId)!;
      if (dock.tier === 2) {
        return (rodHere + dronesHere * stats.drone_base_power) * stats.tier2_dock_power_mult;
      }
      return rodHere + dronesHere * stats.drone_base_power;
    }

    /** Legendary rows (first group, always at top). One per dock. Eligible when all fish Poly + last fish 100%+ catch. */
    const legendaryRows: Array<{
      dockId: DockId;
      dockName: string;
      hasPower: boolean;
      fish: { id: string; name: string; iconFile?: string; iconUrl?: string };
      baseFishPerHour: number;
      fishPerHour: number;
      catchPct: number;
      totalMulti: number;
      isLegendary?: boolean;
      /** Legendary only: numerator of catch chance (1–9). */
      legendaryChanceNum?: number;
      /** Legendary only: denominator of catch chance (e.g. 150000). */
      legendaryChanceDenom?: number;
    }> = [];
    for (const leg of LEGENDARY_FISH) {
      if (!dockIds.has(leg.dockId)) continue;
      const set = AQUARIUM.find((s) => s.dockId === leg.dockId)!;
      const dock = DOCKS.find((d) => d.id === leg.dockId)!;
      const rodHere = state.activeDockId === leg.dockId ? rod : 0;
      const dronesHere = state.dronesPerDock[leg.dockId] ?? 0;
      const powerOnThisDock = powerForSet(leg.dockId, rodHere, dronesHere);
      const allPoly = set.fish.every((f) => (state.fishCardTier[f.id] ?? 0) === 3);
      const lastFish = set.fish[set.fish.length - 1]!;
      const lastCatchPct = catchChancePercent(powerOnThisDock, lastFish.powerRating);
      const eligible = allPoly && lastCatchPct >= 100 && powerOnThisDock > 0;
      const numerator = eligible ? Math.min(9, Math.floor(lastCatchPct / 100)) : 0;
      const legendaryChance = numerator / effectiveLegendaryCatchBase;
      const ticksNeeded = effectiveTicksByDock[dock.id] ?? dock.baseTicksNeeded;
      const dockFillsPerHour = 3600 / (ticksNeeded * effectiveTickSec);
      const fillsPerHour = dockFillsPerHour + extraTicksPerHour / ticksNeeded;
      const fishPerHour = fillsPerHour * legendaryChance;
      legendaryRows.push({
        dockId: leg.dockId,
        dockName: dock.name,
        hasPower: eligible,
        fish: { id: leg.id, name: leg.name, iconUrl: leg.iconUrl },
        baseFishPerHour: fishPerHour,
        fishPerHour,
        catchPct: legendaryChance * 100,
        totalMulti: 1,
        isLegendary: true,
        legendaryChanceNum: eligible ? numerator : undefined,
        legendaryChanceDenom: eligible ? effectiveLegendaryCatchBaseDisplay : undefined,
      });
    }

    const sets = AQUARIUM.filter((set) => dockIds.has(set.dockId));
    const regularRows = sets.flatMap((set) => {
      const dock = DOCKS.find((d) => d.id === set.dockId)!;
      const ticksNeeded = effectiveTicksByDock[dock.id] ?? dock.baseTicksNeeded;
      const rodHere = state.activeDockId === set.dockId ? rod : 0;
      const dronesHere = state.dronesPerDock[set.dockId] ?? 0;
      const powerOnThisDock = powerForSet(set.dockId, rodHere, dronesHere);
      const dockFillsPerHour = 3600 / (ticksNeeded * effectiveTickSec);
      const fillsPerHour = dockFillsPerHour + extraTicksPerHour / ticksNeeded;
      const doublePct = stats.double_tick_chance_pct / 100;
      const triplePct = stats.triple_tick_chance_pct / 100;
      const fivePct = stats.five_tick_chance_pct / 100;
      const expectedRollsPerFill = (1 + doublePct) * (1 + 2 * triplePct) * (1 + 4 * fivePct);
      return set.fish.map((f) => {
        const catchPct = catchChancePercent(powerOnThisDock, f.powerRating);
        const catchMulti =
          expectedRollsPerFill *
          expectedCatchesPerRoll(powerOnThisDock, f.powerRating) *
          stats.fish_income_multi *
          expectedShinyMulti;
        const cardMulti = getCardMulti(f.id);
        const baseFishPerHour = dockFillsPerHour * catchMulti * cardMulti;
        const fishPerHour = fillsPerHour * catchMulti * cardMulti;
        const totalMulti = stats.fish_income_multi * expectedShinyMulti * cardMulti;
        const hasPower = powerOnThisDock > 0;
        return {
          dockId: set.dockId,
          dockName: dock.name,
          hasPower,
          fish: f,
          baseFishPerHour,
          fishPerHour,
          catchPct,
          totalMulti,
          isLegendary: false,
          legendaryChanceNum: undefined,
          legendaryChanceDenom: undefined,
        };
      });
    });

    return [...legendaryRows, ...regularRows];
  }, [
    availableDocks,
    effectiveTickSec,
    extraTicksPerHour,
    effectiveLegendaryCatchBase,
    effectiveLegendaryCatchBaseDisplay,
    expectedShinyMulti,
    effectiveRodPower,
    effectiveTicksByDock,
    stats.drone_base_power,
    stats.tier2_dock_power_mult,
    stats.fish_income_multi,
    stats.double_tick_chance_pct,
    stats.triple_tick_chance_pct,
    stats.five_tick_chance_pct,
    state.dronesPerDock,
    state.activeDockId,
    state.fishCardTier,
    getCardMulti,
  ]);

  /** Displayed fish/h with greedy assignment (highest dock). Used so +% gains are independent of Docks area. current = with current rod card; withRodPoly = rod at 1.10× for Rod Card → Poly marginal. */
  const greedyDisplayedTotals = useMemo(() => {
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesCardTier: state.mrNibblesCardTier,
      relic5xPoints: state.divineRelic5xPoints,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesSkin: state.mrNibblesSkin,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const greedy = getGreedyDockAssignment(upgradeLevels, enhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
    const dockIds = new Set(availableDocks.map((d) => d.id));
    const doublePct = stats.double_tick_chance_pct / 100;
    const triplePct = stats.triple_tick_chance_pct / 100;
    const fivePct = stats.five_tick_chance_pct / 100;
    const expectedRollsPerFill = (1 + doublePct) * (1 + 2 * triplePct) * (1 + 4 * fivePct);
    const rodPoly = Math.round(stats.fishing_rod_power * 1.1);
    let current = 0;
    let withRodPoly = 0;
    for (const set of AQUARIUM) {
      if (!dockIds.has(set.dockId)) continue;
      const dock = DOCKS.find((d) => d.id === set.dockId)!;
      const ticksNeeded = effectiveTicksByDock[dock.id] ?? dock.baseTicksNeeded;
      const fillsPerHour = 3600 / (ticksNeeded * effectiveTickSec) + extraTicksPerHour / ticksNeeded;
      const dronesHere = greedy.dronesPerDock[set.dockId] ?? 0;
      const rodHere = greedy.activeDockId === set.dockId ? effectiveRodPower : 0;
      const rodPolyHere = greedy.activeDockId === set.dockId ? rodPoly : 0;
      const powerCurrent = dock.tier === 2
        ? (rodHere + dronesHere * stats.drone_base_power) * stats.tier2_dock_power_mult
        : rodHere + dronesHere * stats.drone_base_power;
      const powerPoly = dock.tier === 2
        ? (rodPolyHere + dronesHere * stats.drone_base_power) * stats.tier2_dock_power_mult
        : rodPolyHere + dronesHere * stats.drone_base_power;
      for (const f of set.fish) {
        const catchMultiCurrent =
          expectedRollsPerFill *
          expectedCatchesPerRoll(powerCurrent, f.powerRating) *
          stats.fish_income_multi *
          expectedShinyMulti *
          getCardMulti(f.id);
        const catchMultiPoly =
          expectedRollsPerFill *
          expectedCatchesPerRoll(powerPoly, f.powerRating) *
          stats.fish_income_multi *
          expectedShinyMulti *
          getCardMulti(f.id);
        current += fillsPerHour * catchMultiCurrent;
        withRodPoly += fillsPerHour * catchMultiPoly;
      }
    }
    return { current, withRodPoly };
  }, [
    upgradeLevels,
    enhanceLevels,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.abyssLegendaryCaught,
    state.fishingRodCardTier,
    state.mrNibblesCardTier,
    state.divineRelic5xPoints,
    state.mrNibblesLevel,
    state.mrNibblesQuestUnlocked,
    state.mrNibblesQuestRank,
    state.mrNibblesSkin,
    state.poseidonIdolLevel,
    state.tethysIdolLevel,
    state.astraeusIdolLevel,
    state.droneBasePowerWorld3Upgrade,
    state.fishingDroneBasePowerWorld3,
    state.legendaryHaulerBundle,
    state.fishersBundle,
    state.anglerBundle,
    state.halfWayBundle,
    state.divineChallengeCoinLevel,
    state.infernalMrNibblesPct,
    state.infernalMrNibblesLevel,
    state.infernalAnglerDronePct,
    state.infernalAnglerDroneLevel,
    state.constructStatue,
    state.cetusLevel,
    state.blackHoleBonus,
    state.superStarsLevel,
    elixir3xFishingExternal,
    extraTicksPerHour,
    availableDocks,
    effectiveTicksByDock,
    effectiveTickSec,
    effectiveRodPower,
    stats.drone_base_power,
    stats.tier2_dock_power_mult,
    stats.fish_income_multi,
    stats.double_tick_chance_pct,
    stats.triple_tick_chance_pct,
    stats.five_tick_chance_pct,
    stats.fishing_rod_power,
    expectedShinyMulti,
    getCardMulti,
  ]);

  /** Total fish/h with Rod at Poly (1.10×), greedy assignment. Used for Rod Card → Poly marginal; only relevant when rod at Card. */
  const totalFishPerHourWithRodPoly = state.fishingRodCardTier === 1 ? greedyDisplayedTotals.withRodPoly : 0;

  /** Fish only where power > 0. Visible = show-grayed ? all (gray where !hasPower) : only hasPower. */
  const visibleGainsRows = useMemo(() => {
    if (state.showDisabledFishGrayed) return fishingGainsRows;
    return fishingGainsRows.filter((r) => r.hasPower);
  }, [fishingGainsRows, state.showDisabledFishGrayed]);

  /** When W3 floor debuff is on in Gem EV: effective % reduction of total fish/h (30% × freebie-gift share). Exported for Gem EV table only; no UI here. */
  const w3FishPctLoss = useMemo(() => {
    const ext = loadJson<{ w3_floor_debuff?: boolean }>(GEMEV_EXTERNAL_KEY);
    if (!ext?.w3_floor_debuff) return null;
    const totalFish = visibleGainsRows.reduce((s, r) => s + r.fishPerHour, 0);
    if (totalFish <= 0 || totalEffectiveTicksPerHour <= 0) return null;
    const freebieShare = (giftSushiFreebieTicksPerHour * tickMult) / totalEffectiveTicksPerHour;
    if (freebieShare <= 0) return null;
    return 100 * 0.3 * freebieShare;
  }, [visibleGainsRows, totalEffectiveTicksPerHour, giftSushiFreebieTicksPerHour, tickMult]);

  /** Any non-legendary fish card in Card (ungilded) state. Used for "no un-gilded" banner; leg fish excluded (not upgraded for fishing gains). */
  const hasUngildedFishCard = useMemo(() => {
    const legIds = new Set(LEGENDARY_FISH.map((leg) => leg.id));
    return fishingGainsRows.some((r) => !legIds.has(r.fish.id) && (state.fishCardTier[r.fish.id] ?? 0) === 1);
  }, [fishingGainsRows, state.fishCardTier]);

  const hasUngildedRodCard = (state.fishingRodCardTier ?? 0) === 1;

  /** Angler breakdown for Drone: base = fish without Angler (base ticks + Lootbug + Gift Sushi), full = with Angler. So extra % = Angler gain as % of fish without Angler. */
  const anglerBreakdownForDrone = useMemo(() => {
    const dockIds = new Set(availableDocks.map((d) => d.id));
    const rod = effectiveRodPower;
    const powerOnDock = (dockId: DockId, rodHere: number, dronesHere: number) => {
      const dock = DOCKS.find((d) => d.id === dockId)!;
      if (dock.tier === 2) return (rodHere + dronesHere * stats.drone_base_power) * stats.tier2_dock_power_mult;
      return rodHere + dronesHere * stats.drone_base_power;
    };
    const doublePct = stats.double_tick_chance_pct / 100;
    const triplePct = stats.triple_tick_chance_pct / 100;
    const fivePct = stats.five_tick_chance_pct / 100;
    const expectedRollsPerFill = (1 + doublePct) * (1 + 2 * triplePct) * (1 + 4 * fivePct);
    const anglerSuitExtra = anglerBaseTicksPerHour;
    const anglerBuffExtra = anglerBuffTicksPerHour;
    const baseTicksPerHour = effectiveTickSec > 0 ? 3600 / effectiveTickSec : 0;
    const ticksWithoutAngler = baseTicksPerHour + lootbugFishing12TicksProcsPerHour + giftSushiTicksPerHour + lootfrogSushiTicksPerHour;

    let totalBase = 0;
    let totalAnglerSuit = 0;
    let totalAnglerFull = 0;
    let legendaryBase = 0;
    let legendaryAnglerSuit = 0;
    let legendaryAnglerFull = 0;
    const perFish: Array<{ fishId: string; fishName: string; base: number; suit: number; full: number; extraPct: number }> = [];

    for (const leg of LEGENDARY_FISH) {
      if (!dockIds.has(leg.dockId)) continue;
      const set = AQUARIUM.find((s) => s.dockId === leg.dockId)!;
      const dock = DOCKS.find((d) => d.id === leg.dockId)!;
      const rodHere = state.activeDockId === leg.dockId ? rod : 0;
      const dronesHere = state.dronesPerDock[leg.dockId] ?? 0;
      const powerOnThisDock = powerOnDock(leg.dockId, rodHere, dronesHere);
      const allPoly = set.fish.every((f) => (state.fishCardTier[f.id] ?? 0) === 3);
      const lastFish = set.fish[set.fish.length - 1]!;
      const lastCatchPct = catchChancePercent(powerOnThisDock, lastFish.powerRating);
      const eligible = allPoly && lastCatchPct >= 100 && powerOnThisDock > 0;
      const numerator = eligible ? Math.min(9, Math.floor(lastCatchPct / 100)) : 0;
      const chanceBase = numerator / LEGENDARY_CATCH_BASE;
      const chanceBuff = numerator / effectiveLegendaryCatchBase;
      const ticksNeeded = effectiveTicksByDock[dock.id] ?? dock.baseTicksNeeded;
      const fillsWithoutAngler = ticksWithoutAngler / ticksNeeded;
      const fillsWithAngler = fillsWithoutAngler + anglerTicksPerHour / ticksNeeded;
      const b = fillsWithoutAngler * chanceBase;
      const s = (fillsWithoutAngler + anglerSuitExtra / ticksNeeded) * chanceBase;
      const f = (fillsWithoutAngler + anglerSuitExtra / ticksNeeded) * chanceBase + (anglerBuffExtra / ticksNeeded) * chanceBuff;
      legendaryBase += b;
      legendaryAnglerSuit += s;
      legendaryAnglerFull += f;
      const extra = b > 0 ? ((f - b) / b) * 100 : 0;
      perFish.push({ fishId: leg.id, fishName: leg.name, base: b, suit: s, full: f, extraPct: extra });
    }
    const sets = AQUARIUM.filter((set) => dockIds.has(set.dockId));
    for (const set of sets) {
      const dock = DOCKS.find((d) => d.id === set.dockId)!;
      const ticksNeeded = effectiveTicksByDock[dock.id] ?? dock.baseTicksNeeded;
      const rodHere = state.activeDockId === set.dockId ? rod : 0;
      const dronesHere = state.dronesPerDock[set.dockId] ?? 0;
      const powerOnThisDock = powerOnDock(set.dockId, rodHere, dronesHere);
      const fillsWithoutAngler = ticksWithoutAngler / ticksNeeded;
      const fillsWithAngler = fillsWithoutAngler + anglerTicksPerHour / ticksNeeded;
      for (const f of set.fish) {
        const catchMulti =
          expectedRollsPerFill *
          expectedCatchesPerRoll(powerOnThisDock, f.powerRating) *
          stats.fish_income_multi *
          expectedShinyMulti *
          getCardMulti(f.id);
        const b = fillsWithoutAngler * catchMulti;
        const fu = fillsWithAngler * catchMulti;
        const s = (fillsWithoutAngler + anglerSuitExtra / ticksNeeded) * catchMulti;
        totalBase += b;
        totalAnglerSuit += s;
        totalAnglerFull += fu;
        const extra = b > 0 ? ((fu - b) / b) * 100 : 0;
        perFish.push({ fishId: f.id, fishName: f.name, base: b, suit: s, full: fu, extraPct: extra });
      }
    }
    const totalBaseAll = totalBase + legendaryBase;
    const totalSuitAll = totalAnglerSuit + legendaryAnglerSuit;
    const totalFullAll = totalAnglerFull + legendaryAnglerFull;
    const extraFromSuit = totalSuitAll - totalBaseAll;
    const extraFromBuff = totalFullAll - totalSuitAll;
    const legendaryPctIncrease = legendaryAnglerSuit > 0 ? ((legendaryAnglerFull - legendaryAnglerSuit) / legendaryAnglerSuit) * 100 : 0;
    return { extraFromSuit, extraFromBuff, legendaryPctIncrease, totalBaseAll, totalFullAll, perFish };
  }, [
    availableDocks,
    effectiveTickSec,
    effectiveRodPower,
    stats.drone_base_power,
    stats.tier2_dock_power_mult,
    stats.double_tick_chance_pct,
    stats.triple_tick_chance_pct,
    stats.five_tick_chance_pct,
    stats.fish_income_multi,
    state.dronesPerDock,
    state.activeDockId,
    state.fishCardTier,
    getCardMulti,
    anglerTicksPerHour,
    anglerBaseTicksPerHour,
    anglerBuffTicksPerHour,
    effectiveLegendaryCatchBase,
    expectedShinyMulti,
    lootbugFishing12TicksProcsPerHour,
    giftSushiTicksPerHour,
    lootfrogSushiTicksPerHour,
    effectiveTicksByDock,
  ]);

  /** Export for Drone (Angler) and Lootbug: raw total for share calc, angler breakdown. Display uses totalEffectiveTicksPerHour (incl. mult). */
  useEffect(() => {
    const ext = loadJson<Record<string, unknown>>(FISHING_EXTERNAL_KEY) ?? {};
    ext.effectiveTickSec = effectiveTickSec;
    ext.totalEffectiveTicksPerHour = rawTicksPerHour;
    ext.tickMult = tickMult;
    ext.effectiveAnglerTicksPerHour = anglerTicksPerHour * tickMult;
    ext.fishGains = visibleGainsRows
      .filter((r) => r.hasPower && (r.baseFishPerHour > 0 || r.fishPerHour > 0))
      .map((r) => ({
        fishId: r.fish.id,
        fishName: r.fish.name,
        baseFishPerHour: r.baseFishPerHour,
        fishPerHour: r.fishPerHour,
      }));
    ext.anglerBreakdown = anglerBreakdownForDrone;
    ext.anglerTicksUsedForFishGains = anglerTicksPerHour;
    saveJson(FISHING_EXTERNAL_KEY, ext);
  }, [effectiveTickSec, rawTicksPerHour, tickMult, visibleGainsRows, anglerBreakdownForDrone, anglerTicksPerHour]);

  /** Run MC: simulate each fill → tick mult (2×/3×/5×) → catch attempt per fish → shiny/super-shiny rolled per fish; record total and per-fish. */
  function runFishingMc() {
    const hours = state.mcHours;
    const runs = state.mcRuns;
    const dockIds = new Set(availableDocks.map((d) => d.id));
    const doublePct = stats.double_tick_chance_pct / 100;
    const triplePct = stats.triple_tick_chance_pct / 100;
    const fivePct = stats.five_tick_chance_pct / 100;
    type FishEntry = { fish: { id: string; name: string; powerRating: number }; ECR: number; totalMulti: number };
    type DockEntry = { dockId: string; dockName: string; fillsPerHour: number; fish: FishEntry[] };
    const docksWithPower: DockEntry[] = [];
    for (const set of AQUARIUM) {
      if (!dockIds.has(set.dockId)) continue;
      const dock = DOCKS.find((d) => d.id === set.dockId)!;
      const ticksNeeded = effectiveTicksByDock[dock.id] ?? dock.baseTicksNeeded;
      const power = powerForDock(set.dockId);
      if (power <= 0) continue;
      const fillsPerHour =
        3600 / (ticksNeeded * effectiveTickSec) + extraTicksPerHour / ticksNeeded;
      const fish: FishEntry[] = set.fish.map((f) => ({
        fish: f,
        ECR: expectedCatchesPerRoll(power, f.powerRating),
        totalMulti: stats.fish_income_multi * expectedShinyMulti * getCardMulti(f.id),
      }));
      docksWithPower.push({ dockId: set.dockId, dockName: dock.name, fillsPerHour, fish });
    }
    const s = stats.shiny_fish_chance_pct / 100;
    const s2 = stats.super_shiny_chance_pct / 100;
    const shinyMult = stats.shiny_multiplier;
    const superShinyMult = stats.super_shiny_multiplier;
    const fishIncomeMulti = stats.fish_income_multi;
    setMcState((s) => ({ ...s, running: true, samples: null, samplesPerFish: null }));
    window.setTimeout(() => {
      const rng = mulberry32((Date.now() & 0x7fffffff) >>> 0);
      const samples: number[] = [];
      const fishIds = new Set<string>();
      for (const d of docksWithPower) for (const { fish: f } of d.fish) fishIds.add(f.id);
      const samplesPerFish: Record<string, number[]> = {};
      for (const id of fishIds) samplesPerFish[id] = [];
      for (let i = 0; i < runs; i++) {
        let total = 0;
        const runPerFish: Record<string, number> = {};
        for (const id of fishIds) runPerFish[id] = 0;
        for (const { fillsPerHour, fish: fishList } of docksWithPower) {
          const numFills = Math.floor(hours * fillsPerHour);
          for (let f = 0; f < numFills; f++) {
            const multDouble = rng() < doublePct ? 2 : 1;
            const multTriple = rng() < triplePct ? 3 : 1;
            const mult5x = rng() < fivePct ? 5 : 1;
            const rolls = multDouble * multTriple * mult5x;
            for (let r = 0; r < rolls; r++) {
              for (const { fish: fDef, ECR } of fishList) {
                const g = Math.floor(ECR);
                const frac = ECR - g;
                const raw = g + (rng() < frac ? 1 : 0);
                const cardMulti = getCardMulti(fDef.id);
                let shinySum = 0;
                for (let _ = 0; _ < raw; _++) {
                  const isShiny = rng() < s;
                  const isSuperShiny = isShiny && rng() < s2;
                  shinySum += isSuperShiny ? shinyMult * superShinyMult : isShiny ? shinyMult : 1;
                }
                const count = shinySum * fishIncomeMulti * cardMulti;
                runPerFish[fDef.id] = (runPerFish[fDef.id] ?? 0) + count;
                total += count;
              }
            }
          }
        }
        samples.push(total);
        for (const id of fishIds) samplesPerFish[id].push(runPerFish[id] ?? 0);
      }
      const sortNum = (a: number, b: number) => a - b;
      samples.sort(sortNum);
      for (const id of fishIds) samplesPerFish[id].sort(sortNum);
      setMcState((s) => ({ ...s, running: false, samples, samplesPerFish }));
    }, 0);
  }

  /** Sushi: ticks per Sushi (90 + card bonus), EV fish per Sushi at current power (total + per fish). Uses raw ticks (Sushi gives raw ticks). */
  const ticksPerSushi = SUSHI_BASE_TICKS + SUSHI_CARD_TICKS[state.sushiCardTier];
  const sushiEvAndTotal = useMemo(() => {
    const rowsWithPower = visibleGainsRows.filter((r) => r.hasPower && r.fishPerHour > 0);
    const totalFishPerHour = rowsWithPower.reduce((s, r) => s + r.fishPerHour, 0);
    const fishPerSushiEv = rawTicksPerHour > 0 ? (ticksPerSushi * totalFishPerHour) / rawTicksPerHour : 0;
    const fishPerSushiEvPerFish = rowsWithPower.map((r) => ({
      fishId: r.fish.id,
      fishName: r.fish.name,
      iconFile: r.fish.iconFile,
      iconUrl: "iconUrl" in r.fish ? r.fish.iconUrl : undefined,
      fishPerSushiEv: rawTicksPerHour > 0 ? (ticksPerSushi * r.fishPerHour) / rawTicksPerHour : 0,
    }));
    return { totalFishPerHour, fishPerSushiEv, fishPerSushiEvPerFish };
  }, [visibleGainsRows, rawTicksPerHour, ticksPerSushi]);

  /** Fish per hour during 5× Tick Chance buff. totalFishPerHour already includes 2×/3×/5× tick mult; gift adds one more 5× (multiplicative). For Gem EV Gift chart: effective min + fish from that buff. */
  const giftFishPerHourDuring5xBuff = 5 * sushiEvAndTotal.totalFishPerHour;

  /** Export for Gem EV: fish EV per 1 Sushi; fish/h during 5× buff (for Gift chart); W3 debuff; fishing tick reduction (Founder supply drop: 0.5× per drop). */
  useEffect(() => {
    const ext = loadJson<Record<string, unknown>>(GEMEV_EXTERNAL_KEY) ?? {};
    ext.fishPerSushiEvForGift = sushiEvAndTotal.fishPerSushiEv;
    ext.giftFishPerHourDuring5xBuff = giftFishPerHourDuring5xBuff;
    if (w3FishPctLoss != null) ext.w3_debuff_fish_pct_loss = w3FishPctLoss;
    else delete ext.w3_debuff_fish_pct_loss;
    ext.founder_fishing_tick_reduction = Math.max(0, -stats.fishing_tick_reduction);
    saveJson(GEMEV_EXTERNAL_KEY, ext);
  }, [sushiEvAndTotal.fishPerSushiEv, giftFishPerHourDuring5xBuff, w3FishPctLoss, stats.fishing_tick_reduction]);

  function runSushiMc() {
    const { fishPerSushiEv, fishPerSushiEvPerFish } = sushiEvAndTotal;
    const meanFishPerSushi = fishPerSushiEv;
    setSushiMcState((s) => ({ ...s, running: true, samples: null, samplesPerFish: null }));
    window.setTimeout(() => {
      const rng = mulberry32((Date.now() & 0x7fffffff) >>> 0);
      const samples: number[] = [];
      const fishIds = fishPerSushiEvPerFish.map((f) => f.fishId);
      const sumEv = fishPerSushiEvPerFish.reduce((s, f) => s + f.fishPerSushiEv, 0);
      const probsNorm = sumEv > 0 ? fishPerSushiEvPerFish.map((f) => f.fishPerSushiEv / sumEv) : fishPerSushiEvPerFish.map(() => 0);
      const samplesPerFish: Record<string, number[]> = {};
      for (const id of fishIds) samplesPerFish[id] = [];
      for (let i = 0; i < state.sushiMcSushis; i++) {
        const totalFish = samplePoisson(rng, meanFishPerSushi);
        const runPerFish: Record<string, number> = {};
        for (const id of fishIds) runPerFish[id] = 0;
        for (let k = 0; k < totalFish; k++) {
          let u = rng();
          for (let j = 0; j < probsNorm.length; j++) {
            u -= probsNorm[j];
            if (u <= 0) {
              runPerFish[fishIds[j]] = (runPerFish[fishIds[j]] ?? 0) + 1;
              break;
            }
          }
        }
        const total = Object.values(runPerFish).reduce((a, b) => a + b, 0);
        samples.push(total);
        for (const id of fishIds) samplesPerFish[id].push(runPerFish[id] ?? 0);
      }
      samples.sort((a, b) => a - b);
      for (const id of fishIds) samplesPerFish[id].sort((a, b) => a - b);
      setSushiMcState((s) => ({ ...s, running: false, samples, samplesPerFish }));
    }, 0);
  }

  /** Total fish per hour by fish id (sum across docks) for "time to next upgrade". */
  const totalFishPerHourByFishId = useMemo(() => {
    const map: Record<string, number> = {};
    for (const r of fishingGainsRows) {
      const id = r.fish.id;
      map[id] = (map[id] ?? 0) + r.fishPerHour;
    }
    return map;
  }, [fishingGainsRows]);

  /** T1 upgrades available at current boat level. */
  const availableT1Upgrades = useMemo(
    () => FISHING_UPGRADES_T1.filter((def) => stats.boat_level >= def.boatLevelRequired),
    [stats.boat_level],
  );

  /** T2 upgrades available at current boat level and T2 boat level. */
  const availableT2Upgrades = useMemo(
    () =>
      FISHING_UPGRADES_T2.filter(
        (def) =>
          stats.boat_level >= def.boatLevelRequired &&
          (def.t2BoatLevelRequired == null || (stats.t2_boat_level ?? 0) >= def.t2BoatLevelRequired),
      ),
    [stats.boat_level, stats.t2_boat_level],
  );

  /** T1 enhancements available at current boat level. */
  const availableT1Enhancements = useMemo(
    () => ENHANCEMENTS_T1.filter((def) => stats.boat_level >= def.boatLevelRequired),
    [stats.boat_level],
  );

  /** T2 enhancements available at current boat level and T2 boat level. */
  const availableT2Enhancements = useMemo(
    () =>
      ENHANCEMENTS_T2.filter(
        (def) =>
          stats.boat_level >= def.boatLevelRequired &&
          (def.t2BoatLevelRequired == null || (stats.t2_boat_level ?? 0) >= def.t2BoatLevelRequired),
      ),
    [stats.boat_level, stats.t2_boat_level],
  );

  /** Total gems spent on enhancements so far (sum of cost to reach each current level). */
  const totalGemsSpentOnEnhancements = useMemo(() => {
    let total = 0;
    const enhanceCosts = (def: { id: EnhanceId }) => {
      const t1 = ENHANCE_COSTS_T1[def.id as keyof typeof ENHANCE_COSTS_T1];
      const t2 = ENHANCE_COSTS_T2[def.id as keyof typeof ENHANCE_COSTS_T2];
      return t1 ?? t2;
    };
    for (const def of [...ENHANCEMENTS_T1, ...ENHANCEMENTS_T2]) {
      const costs = enhanceCosts(def);
      if (!costs?.length) continue;
      const lvl = Math.max(0, Math.min(costs[costs.length - 1]!.level, Math.floor(enhanceLevels[def.id] ?? 0)));
      for (let i = 1; i <= lvl; i++) {
        const entry = costs.find((c) => c.level === i);
        if (entry) total += entry.gems;
      }
    }
    return total;
  }, [enhanceLevels]);

  const { heatMin, heatMax } = useMemo(() => {
    const enabled = visibleGainsRows.filter((r) => r.hasPower && r.fishPerHour > 0);
    if (enabled.length === 0) return { heatMin: 0, heatMax: 1 };
    const vals = enabled.map((r) => r.fishPerHour);
    return { heatMin: Math.min(...vals), heatMax: Math.max(...vals) };
  }, [visibleGainsRows]);

  /** +% gains = (total fish/h with +1 level − current total) / current total × 100. Uses greedy assignment: rod and all drones on the highest unlocked dock (e.g. Cave when you just got T2). Marginal % reflects gain when everything is on that one dock. Also next-level effect string (e.g. 10→12) for name cell. Use same skill options as main stats so effect strings (e.g. tick reduction) match "Your stats". */
  const { upgradeMarginalPct, enhanceMarginalPct, upgradeNextEffect, enhanceNextEffect } = useMemo(() => {
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesCardTier: state.mrNibblesCardTier,
      relic5xPoints: state.divineRelic5xPoints,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesSkin: state.mrNibblesSkin,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const currentStats = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, skillOpts);
    // Greedy: +% gains assume rod and all drones on the dock that maximizes total fish/h.
    const greedy = getGreedyDockAssignment(upgradeLevels, enhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
    const currentTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      greedy.dronesPerDock,
      greedy.activeDockId,
      elixir3xFishingExternal,
      skillOpts,
      extraTicksPerHour,
    );
    const upgradeMap = new Map<FishingUpgradeId, number | null>();
    const upgradeEffectMap = new Map<FishingUpgradeId, string | null>();
    for (const def of [...availableT1Upgrades, ...availableT2Upgrades]) {
      const costs = UPGRADE_COSTS[def.id];
      const maxLvl = costs?.length ? costs[costs.length - 1]!.level : 0;
      const lvl = Math.max(0, Math.min(maxLvl, upgradeLevels[def.id] ?? 0));
      if (lvl >= maxLvl) {
        upgradeMap.set(def.id, null);
        upgradeEffectMap.set(def.id, null);
        continue;
      }
      const newLevels = { ...upgradeLevels, [def.id]: lvl + 1 };
      const nextStats = computeFishingStatsFromLevels(newLevels, enhanceLevels, skillOpts);
      // Greedy for +1 level: best dock with new cap (drone cap upgrades add drones on that best dock).
      const newGreedy = getGreedyDockAssignment(newLevels, enhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
      const newTotal = computeTotalFishPerHour(
        newLevels,
        enhanceLevels,
        newGreedy.dronesPerDock,
        newGreedy.activeDockId,
        elixir3xFishingExternal,
        skillOpts,
        extraTicksPerHour,
      );
      upgradeMap.set(
        def.id,
        currentTotal > 0 ? ((newTotal - currentTotal) / currentTotal) * 100 : null,
      );
      upgradeEffectMap.set(def.id, formatUpgradeNextEffect(def.id, currentStats, nextStats, upgradeLevels));
    }
    const enhanceMap = new Map<EnhanceId, number | null>();
    const enhanceEffectMap = new Map<EnhanceId, string | null>();
    const enhanceCosts = (def: { id: EnhanceId }) => {
      const t1 = ENHANCE_COSTS_T1[def.id as keyof typeof ENHANCE_COSTS_T1];
      const t2 = ENHANCE_COSTS_T2[def.id as keyof typeof ENHANCE_COSTS_T2];
      return t1 ?? t2;
    };
    for (const def of [...availableT1Enhancements, ...availableT2Enhancements]) {
      const costs = enhanceCosts(def);
      const maxLvl = costs?.length ? costs[costs.length - 1]!.level : 0;
      const lvl = Math.max(0, Math.min(maxLvl, enhanceLevels[def.id] ?? 0));
      if (lvl >= maxLvl) {
        enhanceMap.set(def.id, null);
        enhanceEffectMap.set(def.id, null);
        continue;
      }
      const newLevels = { ...enhanceLevels, [def.id]: lvl + 1 };
      const nextStats = computeFishingStatsFromLevels(upgradeLevels, newLevels, skillOpts);
      // Greedy for +1 level: best dock with new cap (drone cap enhancements add drones on that best dock).
      const newGreedy = getGreedyDockAssignment(upgradeLevels, newLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
      const newTotal = computeTotalFishPerHour(
        upgradeLevels,
        newLevels,
        newGreedy.dronesPerDock,
        newGreedy.activeDockId,
        elixir3xFishingExternal,
        skillOpts,
        extraTicksPerHour,
      );
      let marginalPct = currentTotal > 0 ? ((newTotal - currentTotal) / currentTotal) * 100 : null;
      if (def.id === "enhance_token_multiplier" && (marginalPct == null || marginalPct < 0.1)) {
        marginalPct = tokenMultiplierMarginalPct(lvl);
      }
      if (def.id === "enhance_tiny_notice_chance" && (marginalPct == null || marginalPct < 0.1)) {
        marginalPct = tinyNoticeMarginalPct(lvl);
      }
      enhanceMap.set(def.id, marginalPct);
      enhanceEffectMap.set(def.id, formatEnhanceNextEffect(def.id, currentStats, nextStats, enhanceLevels));
    }
    return {
      upgradeMarginalPct: upgradeMap,
      enhanceMarginalPct: enhanceMap,
      upgradeNextEffect: upgradeEffectMap,
      enhanceNextEffect: enhanceEffectMap,
    };
  }, [
    upgradeLevels,
    enhanceLevels,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.fishingRodCardTier,
    elixir3xFishingExternal,
    extraTicksPerHour,
    availableT1Upgrades,
    availableT2Upgrades,
    availableT1Enhancements,
    availableT2Enhancements,
  ]);

  /** Best enhancement to fully max (excl. Fish Multiplier): largest total +% fish/h vs current; gem sum for all remaining levels. Same greedy dock model as +% gains. */
  const bestEnhancementToMaxExclFishMultiplier = useMemo(() => {
    const enhanceCosts = (def: { id: EnhanceId }) => {
      const t1 = ENHANCE_COSTS_T1[def.id as keyof typeof ENHANCE_COSTS_T1];
      const t2 = ENHANCE_COSTS_T2[def.id as keyof typeof ENHANCE_COSTS_T2];
      return t1 ?? t2;
    };
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesCardTier: state.mrNibblesCardTier,
      relic5xPoints: state.divineRelic5xPoints,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesSkin: state.mrNibblesSkin,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const greedy0 = getGreedyDockAssignment(upgradeLevels, enhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
    const currentTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      greedy0.dronesPerDock,
      greedy0.activeDockId,
      elixir3xFishingExternal,
      skillOpts,
      extraTicksPerHour,
    );
    if (currentTotal <= 0) return null;

    let best: {
      name: string;
      totalPct: number;
      totalGems: number;
      costEfficGemAbs: number | null;
      costEfficGemIncome: number | null;
    } | null = null;
    for (const def of [...availableT1Enhancements, ...availableT2Enhancements]) {
      if (def.id === "enhance_fish_multiplier") continue;
      const costs = enhanceCosts(def);
      if (!costs?.length) continue;
      const maxLvl = costs[costs.length - 1]!.level;
      const lvl = Math.max(0, Math.min(maxLvl, Math.floor(enhanceLevels[def.id] ?? 0)));
      if (lvl >= maxLvl) continue;

      let totalGems = 0;
      for (let L = lvl + 1; L <= maxLvl; L++) {
        const entry = costs.find((c) => c.level === L);
        if (entry) totalGems += entry.gems;
      }

      const maxEnhanceLevels = { ...enhanceLevels, [def.id]: maxLvl };
      const greedyMax = getGreedyDockAssignment(upgradeLevels, maxEnhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
      const finalTotal = computeTotalFishPerHour(
        upgradeLevels,
        maxEnhanceLevels,
        greedyMax.dronesPerDock,
        greedyMax.activeDockId,
        elixir3xFishingExternal,
        skillOpts,
        extraTicksPerHour,
      );
      const totalPct = ((finalTotal - currentTotal) / currentTotal) * 100;
      const costEfficGemAbs = totalGems > 0 ? (totalPct / totalGems) * 100 : null;
      const costEfficGemIncome =
        totalGems > 0 && gemEvGemsPerHour > 0 ? totalPct / (totalGems / gemEvGemsPerHour) : null;
      if (!best || totalPct > best.totalPct) {
        best = { name: def.name, totalPct, totalGems, costEfficGemAbs, costEfficGemIncome };
      }
    }
    return best;
  }, [
    upgradeLevels,
    enhanceLevels,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.fishingRodCardTier,
    elixir3xFishingExternal,
    extraTicksPerHour,
    availableT1Upgrades,
    availableT2Upgrades,
    availableT1Enhancements,
    availableT2Enhancements,
    gemEvGemsPerHour,
  ]);

  /** +% effective fish gain for +1 Tethys Idol at current build (for tooltip). */
  const tethysIdolMarginalFishPct = useMemo(() => {
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesCardTier: state.mrNibblesCardTier,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesSkin: state.mrNibblesSkin,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const greedy = getGreedyDockAssignment(upgradeLevels, enhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
    const currentTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      greedy.dronesPerDock,
      greedy.activeDockId,
      elixir3xFishingExternal,
      skillOpts,
      extraTicksPerHour,
    );
    const newOpts = { ...skillOpts, tethysIdolLevel: state.tethysIdolLevel + 1 };
    const newGreedy = getGreedyDockAssignment(upgradeLevels, enhanceLevels, newOpts, elixir3xFishingExternal, extraTicksPerHour);
    const newTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      newGreedy.dronesPerDock,
      newGreedy.activeDockId,
      elixir3xFishingExternal,
      newOpts,
      extraTicksPerHour,
    );
    return currentTotal > 0 ? ((newTotal - currentTotal) / currentTotal) * 100 : null;
  }, [
    upgradeLevels,
    enhanceLevels,
    state.tethysIdolLevel,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.abyssLegendaryCaught,
    state.fishingRodCardTier,
    state.mrNibblesCardTier,
    state.mrNibblesLevel,
    state.mrNibblesQuestUnlocked,
    state.mrNibblesQuestRank,
    state.mrNibblesSkin,
    state.poseidonIdolLevel,
    state.astraeusIdolLevel,
    state.droneBasePowerWorld3Upgrade,
    state.fishingDroneBasePowerWorld3,
    state.legendaryHaulerBundle,
    state.fishersBundle,
    state.anglerBundle,
    state.halfWayBundle,
    state.divineChallengeCoinLevel,
    state.infernalMrNibblesPct,
    state.infernalMrNibblesLevel,
    state.infernalAnglerDronePct,
    state.infernalAnglerDroneLevel,
    state.constructStatue,
    state.cetusLevel,
    state.blackHoleBonus,
    state.superStarsLevel,
    elixir3xFishingExternal,
    extraTicksPerHour,
  ]);

  /** +% effective fish gain for +1 Poseidon Idol at current build (for tooltip). */
  const poseidonIdolMarginalFishPct = useMemo(() => {
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesCardTier: state.mrNibblesCardTier,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesSkin: state.mrNibblesSkin,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const currentTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      state.dronesPerDock,
      state.activeDockId,
      elixir3xFishingExternal,
      skillOpts,
      extraTicksPerHour,
    );
    const newTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      state.dronesPerDock,
      state.activeDockId,
      elixir3xFishingExternal,
      { ...skillOpts, poseidonIdolLevel: state.poseidonIdolLevel + 1 },
      extraTicksPerHour,
    );
    return currentTotal > 0 ? ((newTotal - currentTotal) / currentTotal) * 100 : null;
  }, [
    upgradeLevels,
    enhanceLevels,
    state.dronesPerDock,
    state.activeDockId,
    state.poseidonIdolLevel,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.abyssLegendaryCaught,
    state.fishingRodCardTier,
    state.mrNibblesCardTier,
    state.mrNibblesLevel,
    state.mrNibblesQuestUnlocked,
    state.mrNibblesQuestRank,
    state.tethysIdolLevel,
    state.astraeusIdolLevel,
    state.droneBasePowerWorld3Upgrade,
    state.fishingDroneBasePowerWorld3,
    state.legendaryHaulerBundle,
    state.fishersBundle,
    state.anglerBundle,
    state.halfWayBundle,
    state.divineChallengeCoinLevel,
    state.infernalMrNibblesPct,
    state.infernalMrNibblesLevel,
    state.infernalAnglerDronePct,
    state.infernalAnglerDroneLevel,
    state.constructStatue,
    state.cetusLevel,
    state.blackHoleBonus,
    state.superStarsLevel,
    elixir3xFishingExternal,
    extraTicksPerHour,
  ]);

  /** +% effective fish gain for +1 Astraeus Idol at current build (for tooltip). */
  const astraeusIdolMarginalFishPct = useMemo(() => {
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesCardTier: state.mrNibblesCardTier,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const currentTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      state.dronesPerDock,
      state.activeDockId,
      elixir3xFishingExternal,
      skillOpts,
      extraTicksPerHour,
    );
    const newTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      state.dronesPerDock,
      state.activeDockId,
      elixir3xFishingExternal,
      { ...skillOpts, astraeusIdolLevel: state.astraeusIdolLevel + 1 },
      extraTicksPerHour,
    );
    return currentTotal > 0 ? ((newTotal - currentTotal) / currentTotal) * 100 : null;
  }, [
    upgradeLevels,
    enhanceLevels,
    state.dronesPerDock,
    state.activeDockId,
    state.astraeusIdolLevel,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.abyssLegendaryCaught,
    state.fishingRodCardTier,
    state.mrNibblesCardTier,
    state.mrNibblesLevel,
    state.mrNibblesQuestUnlocked,
    state.mrNibblesQuestRank,
    state.mrNibblesSkin,
    state.poseidonIdolLevel,
    state.tethysIdolLevel,
    state.droneBasePowerWorld3Upgrade,
    state.fishingDroneBasePowerWorld3,
    state.legendaryHaulerBundle,
    state.fishersBundle,
    state.anglerBundle,
    state.halfWayBundle,
    state.divineChallengeCoinLevel,
    state.infernalMrNibblesPct,
    state.infernalMrNibblesLevel,
    state.infernalAnglerDronePct,
    state.infernalAnglerDroneLevel,
    state.constructStatue,
    state.cetusLevel,
    state.blackHoleBonus,
    state.superStarsLevel,
    elixir3xFishingExternal,
    extraTicksPerHour,
  ]);

  /** Store bundles: expected +% gain for each package (same basis as upgrades: greedy total fish/h). Polychrome uses displayed total with card multis. */
  const storeBundleMarginalPct = useMemo(() => {
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesCardTier: state.mrNibblesCardTier,
      relic5xPoints: state.divineRelic5xPoints,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesSkin: state.mrNibblesSkin,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const greedy = getGreedyDockAssignment(upgradeLevels, enhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
    const currentTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      greedy.dronesPerDock,
      greedy.activeDockId,
      elixir3xFishingExternal,
      skillOpts,
      extraTicksPerHour,
    );
    const polychrome: number | null = (() => {
      const rows = visibleGainsRows.filter((r) => r.hasPower && r.fishPerHour > 0);
      const displayedTotal = rows.reduce((s, r) => s + r.fishPerHour, 0);
      if (displayedTotal <= 0) return null;
      if (state.valuePackPotencyPoly) return null; // already active
      const totalWithPoly = rows.reduce(
        (s, r) => s + r.fishPerHour * (((state.fishCardTier[r.fish.id] ?? 0) > 0 ? 1.15 : 1)),
        0,
      );
      return ((totalWithPoly - displayedTotal) / displayedTotal) * 100;
    })();
    const legendaryHauler: number | null = state.legendaryHaulerBundle
      ? null
      : currentTotal > 0
        ? (() => {
            const g = getGreedyDockAssignment(upgradeLevels, enhanceLevels, { ...skillOpts, legendaryHaulerBundle: true }, elixir3xFishingExternal, extraTicksPerHour);
            const newTotal = computeTotalFishPerHour(upgradeLevels, enhanceLevels, g.dronesPerDock, g.activeDockId, elixir3xFishingExternal, { ...skillOpts, legendaryHaulerBundle: true }, extraTicksPerHour);
            return ((newTotal - currentTotal) / currentTotal) * 100;
          })()
        : null;
    const fishers: number | null = state.fishersBundle
      ? null
      : currentTotal > 0
        ? (() => {
            const g = getGreedyDockAssignment(upgradeLevels, enhanceLevels, { ...skillOpts, fishersBundle: true }, elixir3xFishingExternal, extraTicksPerHour);
            const newTotal = computeTotalFishPerHour(upgradeLevels, enhanceLevels, g.dronesPerDock, g.activeDockId, elixir3xFishingExternal, { ...skillOpts, fishersBundle: true }, extraTicksPerHour);
            return ((newTotal - currentTotal) / currentTotal) * 100;
          })()
        : null;
    const halfWayBundlePct: number | null = state.halfWayBundle
      ? null
      : currentTotal > 0
        ? (() => {
            const g = getGreedyDockAssignment(upgradeLevels, enhanceLevels, { ...skillOpts, halfWayBundle: true }, elixir3xFishingExternal, extraTicksPerHour);
            const newTotal = computeTotalFishPerHour(upgradeLevels, enhanceLevels, g.dronesPerDock, g.activeDockId, elixir3xFishingExternal, { ...skillOpts, halfWayBundle: true }, extraTicksPerHour);
            return ((newTotal - currentTotal) / currentTotal) * 100;
          })()
        : null;
    // Angler's Bundle: +6% Tiny Notice (flat). Same effective assumed gain as Tiny Notice enhancement: expected mult = 1 + tinyPct/100×9 (Tiny = 10×).
    const angler: number | null = (() => {
      if (state.anglerBundle) return null;
      const statsWithoutAngler = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, { ...skillOpts, anglerBundle: false });
      const currentTinyPct = statsWithoutAngler.tiny_notice_chance_pct;
      const multWithout = 1 + (currentTinyPct / 100) * 9;
      const multWith = 1 + ((currentTinyPct + 6) / 100) * 9;
      return ((multWith - multWithout) / multWithout) * 100;
    })();
    const constructGilded: number | null =
      state.constructStatue !== "none"
        ? null
        : currentTotal > 0
          ? (() => {
              const g = getGreedyDockAssignment(upgradeLevels, enhanceLevels, { ...skillOpts, constructStatue: "gilded" }, elixir3xFishingExternal, extraTicksPerHour);
              const newTotal = computeTotalFishPerHour(upgradeLevels, enhanceLevels, g.dronesPerDock, g.activeDockId, elixir3xFishingExternal, { ...skillOpts, constructStatue: "gilded" }, extraTicksPerHour);
              return ((newTotal - currentTotal) / currentTotal) * 100;
            })()
          : null;
    const constructPlatinized: number | null =
      state.constructStatue === "platinized"
        ? null
        : currentTotal > 0
          ? (() => {
              const g = getGreedyDockAssignment(upgradeLevels, enhanceLevels, { ...skillOpts, constructStatue: "platinized" }, elixir3xFishingExternal, extraTicksPerHour);
              const newTotal = computeTotalFishPerHour(upgradeLevels, enhanceLevels, g.dronesPerDock, g.activeDockId, elixir3xFishingExternal, { ...skillOpts, constructStatue: "platinized" }, extraTicksPerHour);
              return ((newTotal - currentTotal) / currentTotal) * 100;
            })()
          : null;
    const blackHoleBonusPct: number | null = state.blackHoleBonus
      ? null
      : currentTotal > 0
        ? (() => {
            const g = getGreedyDockAssignment(upgradeLevels, enhanceLevels, { ...skillOpts, blackHoleBonus: true }, elixir3xFishingExternal, extraTicksPerHour);
            const newTotal = computeTotalFishPerHour(upgradeLevels, enhanceLevels, g.dronesPerDock, g.activeDockId, elixir3xFishingExternal, { ...skillOpts, blackHoleBonus: true }, extraTicksPerHour);
            return ((newTotal - currentTotal) / currentTotal) * 100;
          })()
        : null;
    return { polychrome, legendaryHauler, fishers, halfWayBundlePct, angler, constructGilded, constructPlatinized, blackHoleBonusPct };
  }, [
    upgradeLevels,
    enhanceLevels,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.fishingRodCardTier,
    state.mrNibblesCardTier,
    state.legendaryHaulerBundle,
    state.fishersBundle,
    state.halfWayBundle,
    state.anglerBundle,
    state.valuePackPotencyPoly,
    state.divineRelic5xPoints,
    state.mrNibblesLevel,
    state.mrNibblesQuestUnlocked,
    state.mrNibblesQuestRank,
    state.mrNibblesSkin,
    state.poseidonIdolLevel,
    state.tethysIdolLevel,
    state.astraeusIdolLevel,
    state.droneBasePowerWorld3Upgrade,
    state.fishingDroneBasePowerWorld3,
    state.divineChallengeCoinLevel,
    state.infernalMrNibblesPct,
    state.infernalMrNibblesLevel,
    state.infernalAnglerDronePct,
    state.infernalAnglerDroneLevel,
    state.constructStatue,
    state.cetusLevel,
    state.blackHoleBonus,
    state.superStarsLevel,
    elixir3xFishingExternal,
    extraTicksPerHour,
    visibleGainsRows,
  ]);

  /** Cost-efficiency heatmap: min/max across T1 + T2 upgrades (high = green, low = red). */
  const { costEfficHeatMin, costEfficHeatMax } = useMemo(() => {
    const vals: number[] = [];
    for (const def of [...availableT1Upgrades, ...availableT2Upgrades]) {
      const costs = UPGRADE_COSTS[def.id];
      const maxLvl = costs?.length ? costs[costs.length - 1]!.level : 0;
      const lvl = Math.max(0, Math.min(maxLvl, upgradeLevels[def.id] ?? 0));
      if (lvl >= maxLvl) continue;
      const marginalPct = upgradeMarginalPct.get(def.id);
      const nextLevel = lvl + 1;
      const nextCostEntry = costs?.find((c) => c.level === nextLevel);
      const fishPerHour = nextCostEntry
        ? (totalFishPerHourByFishId[nextCostEntry.fishId] ?? 0)
        : 0;
      if (
        marginalPct != null &&
        nextCostEntry &&
        fishPerHour > 0
      ) {
        const hoursToNext = nextCostEntry.amount / fishPerHour;
        vals.push(marginalPct / hoursToNext);
      }
    }
    if (vals.length === 0) return { costEfficHeatMin: 0, costEfficHeatMax: 1 };
    return {
      costEfficHeatMin: Math.min(...vals),
      costEfficHeatMax: Math.max(...vals),
    };
  }, [
    availableT1Upgrades,
    availableT2Upgrades,
    totalFishPerHourByFishId,
    upgradeLevels,
    upgradeMarginalPct,
    state.dronesPerDock,
  ]);

  /** Dock Score: sum of cost efficiency with max per cost fish. Each fish (dock) counts once with its best upgrade. */
  const dockScore = useMemo(() => {
    const byCostFish = new Map<string, number>();
    for (const def of [...availableT1Upgrades, ...availableT2Upgrades]) {
      const costs = UPGRADE_COSTS[def.id];
      const maxLvl = costs?.length ? costs[costs.length - 1]!.level : 0;
      const lvl = Math.max(0, Math.min(maxLvl, upgradeLevels[def.id] ?? 0));
      if (lvl >= maxLvl) continue;
      const marginalPct = upgradeMarginalPct.get(def.id);
      const nextLevel = lvl + 1;
      const nextCostEntry = costs?.find((c) => c.level === nextLevel);
      const fishPerHour = nextCostEntry ? (totalFishPerHourByFishId[nextCostEntry.fishId] ?? 0) : 0;
      if (marginalPct != null && nextCostEntry && fishPerHour > 0) {
        const hoursToNext = nextCostEntry.amount / fishPerHour;
        const costEffic = marginalPct / hoursToNext;
        const fishId = nextCostEntry.fishId;
        const prev = byCostFish.get(fishId);
        if (prev == null || costEffic > prev) byCostFish.set(fishId, costEffic);
      }
    }
    return [...byCostFish.values()].reduce((a, b) => a + b, 0);
  }, [
    availableT1Upgrades,
    availableT2Upgrades,
    totalFishPerHourByFishId,
    upgradeLevels,
    upgradeMarginalPct,
  ]);

  /** Cost-efficiency heatmap for enhancements: time-based (marginal % per hour) and gem-absolute (marginal % per gem × 100). */
  const { costEfficHeatMinEnhance, costEfficHeatMaxEnhance, costEfficHeatMinEnhanceGemAbs, costEfficHeatMaxEnhanceGemAbs } = useMemo(() => {
    const timeVals: number[] = [];
    const gemAbsVals: number[] = [];
    const enhanceCosts = (def: { id: EnhanceId }) => {
      const t1 = ENHANCE_COSTS_T1[def.id as keyof typeof ENHANCE_COSTS_T1];
      const t2 = ENHANCE_COSTS_T2[def.id as keyof typeof ENHANCE_COSTS_T2];
      return t1 ?? t2;
    };
    for (const def of [...availableT1Enhancements, ...availableT2Enhancements]) {
      if (def.id === "enhance_token_multiplier" || def.id === "enhance_tiny_notice_chance") continue;
      const costs = enhanceCosts(def);
      const maxLvl = costs?.length ? costs[costs.length - 1]!.level : 0;
      const lvl = Math.max(0, Math.min(maxLvl, enhanceLevels[def.id] ?? 0));
      if (lvl >= maxLvl) continue;
      const marginalPct = enhanceMarginalPct.get(def.id);
      const nextLevel = lvl + 1;
      const nextCostEntry = costs?.find((c) => c.level === nextLevel);
      if (marginalPct != null && nextCostEntry && nextCostEntry.gems > 0) {
        if (gemEvGemsPerHour > 0) {
          const hoursToEarn = nextCostEntry.gems / gemEvGemsPerHour;
          timeVals.push(marginalPct / hoursToEarn);
        }
        gemAbsVals.push((marginalPct / nextCostEntry.gems) * 100);
      }
    }
    const fallback = { min: 0, max: 1 };
    return {
      costEfficHeatMinEnhance: timeVals.length ? Math.min(...timeVals) : fallback.min,
      costEfficHeatMaxEnhance: timeVals.length ? Math.max(...timeVals) : fallback.max,
      costEfficHeatMinEnhanceGemAbs: gemAbsVals.length ? Math.min(...gemAbsVals) : fallback.min,
      costEfficHeatMaxEnhanceGemAbs: gemAbsVals.length ? Math.max(...gemAbsVals) : fallback.max,
    };
  }, [
    availableT1Enhancements,
    availableT2Enhancements,
    enhanceLevels,
    enhanceMarginalPct,
    gemEvGemsPerHour,
  ]);

  /** Skill tree: marginal % gain for +1 level, optional breakdown by effect, and cost-efficiency heatmap. */
  const { skillMarginalPct, skillMarginalBreakdown, costEfficHeatMinSkill, costEfficHeatMaxSkill, costEfficHeatMinSkillGemAbs, costEfficHeatMaxSkillGemAbs } = useMemo(() => {
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesCardTier: state.mrNibblesCardTier,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesSkin: state.mrNibblesSkin,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const currentStats = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, skillOpts);
    // Greedy: +% gains assume rod and all drones on the dock that maximizes total fish/h.
    const greedy = getGreedyDockAssignment(upgradeLevels, enhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
    const currentTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      greedy.dronesPerDock,
      greedy.activeDockId,
      elixir3xFishingExternal,
      skillOpts,
      extraTicksPerHour,
    );
    const marginalMap = new Map<FishingSkillId, number | null>();
    const breakdownMap = new Map<FishingSkillId, Array<{ label: string; pct: number }>>();
    const efficVals: number[] = [];
    const efficValsGemAbs: number[] = [];
    for (const def of FISHING_SKILL_TREE) {
      const maxLvl = def.costs.length;
      const lvl = Math.max(0, Math.min(maxLvl, state.skillTreeLevels[def.id] ?? 0));
      if (lvl >= maxLvl) {
        marginalMap.set(def.id, null);
        continue;
      }
      const newSkillLevels = { ...state.skillTreeLevels, [def.id]: lvl + 1 };
      const newSkillOpts = { ...skillOpts, skillTreeLevels: newSkillLevels };
      const extraDronesFromSkill =
        def.id === "fishing_with_friends" ? 5 : def.id === "motley_school" ? 5 : 0;
      // Greedy for +1 level: best dock with new stats (e.g. +5 drones from skill on that best dock).
      const newGreedy = getGreedyDockAssignment(upgradeLevels, enhanceLevels, newSkillOpts, elixir3xFishingExternal, extraTicksPerHour);
      const newTotal = computeTotalFishPerHour(
        upgradeLevels,
        enhanceLevels,
        newGreedy.dronesPerDock,
        newGreedy.activeDockId,
        elixir3xFishingExternal,
        newSkillOpts,
        extraTicksPerHour,
      );
      let marginalPct =
        currentTotal > 0 ? ((newTotal - currentTotal) / currentTotal) * 100 : null;
      if (def.id === "friendship_ended_tier1" && (marginalPct == null || marginalPct < 0.1)) {
        marginalPct = FRIENDSHIP_ENDED_NOTICE_MARGINAL_PCT;
        breakdownMap.set(def.id, [
          { label: "Notice -10% req ≈ +11.1% (notice farming)", pct: FRIENDSHIP_ENDED_NOTICE_MARGINAL_PCT },
        ]);
      }
      marginalMap.set(def.id, marginalPct);

      if (currentTotal > 0 && extraDronesFromSkill > 0) {
        // Same dock/drone count as current greedy, new skill stats only (no extra drones yet).
        const totalSameDrones = computeTotalFishPerHour(
          upgradeLevels,
          enhanceLevels,
          greedy.dronesPerDock,
          greedy.activeDockId,
          elixir3xFishingExternal,
          newSkillOpts,
          extraTicksPerHour,
        );
        const pctFromStats = ((totalSameDrones - currentTotal) / currentTotal) * 100;
        const pctFromDrones = ((newTotal - totalSameDrones) / currentTotal) * 100;
        if (def.id === "fishing_with_friends") {
          breakdownMap.set(def.id, [
            { label: "Drone power +10%", pct: pctFromStats / 2 },
            { label: "Fish mult +3%", pct: pctFromStats / 2 },
            { label: "Fishing Drones +5", pct: pctFromDrones },
          ]);
        } else if (def.id === "motley_school") {
          breakdownMap.set(def.id, [
            { label: "Rod mult +10%", pct: pctFromStats },
            { label: "Fishing Drones +5", pct: pctFromDrones },
          ]);
        }
      }

      if (currentTotal > 0 && def.id === "lets_pick_up_the_pace") {
        const newStats = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, { ...skillOpts, skillTreeLevels: newSkillLevels });
        const statsTickOnly: ComputedFishingStats = {
          ...newStats,
          double_tick_chance_pct: currentStats.double_tick_chance_pct,
          triple_tick_chance_pct: currentStats.triple_tick_chance_pct,
          five_tick_chance_pct: currentStats.five_tick_chance_pct,
        };
        const statsDoubleOnly: ComputedFishingStats = {
          ...newStats,
          triple_tick_chance_pct: currentStats.triple_tick_chance_pct,
          five_tick_chance_pct: currentStats.five_tick_chance_pct,
        };
        const totalTickOnly = computeTotalFishPerHourFromStats(statsTickOnly, greedy.dronesPerDock, greedy.activeDockId, elixir3xFishingExternal, effectiveRodPower, extraTicksPerHour, effectiveTicksByDock);
        const totalDoubleOnly = computeTotalFishPerHourFromStats(statsDoubleOnly, greedy.dronesPerDock, greedy.activeDockId, elixir3xFishingExternal, effectiveRodPower, extraTicksPerHour, effectiveTicksByDock);
        const totalAllNew = computeTotalFishPerHourFromStats(newStats, greedy.dronesPerDock, greedy.activeDockId, elixir3xFishingExternal, effectiveRodPower, extraTicksPerHour, effectiveTicksByDock);
        breakdownMap.set(def.id, [
          { label: "Tick -2s", pct: ((totalTickOnly - currentTotal) / currentTotal) * 100 },
          { label: "Double +2%", pct: ((totalDoubleOnly - totalTickOnly) / currentTotal) * 100 },
          { label: "Triple +1%", pct: ((totalAllNew - totalDoubleOnly) / currentTotal) * 100 },
        ]);
      }

      if (currentTotal > 0 && def.id === "with_this_fish_i_summon_two_more_fish") {
        const newStats = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, { ...skillOpts, skillTreeLevels: newSkillLevels });
        const statsFishMultiOnly: ComputedFishingStats = {
          ...newStats,
          shiny_fish_chance_pct: currentStats.shiny_fish_chance_pct,
        };
        const statsShinyOnly: ComputedFishingStats = {
          ...newStats,
          fish_income_multi: currentStats.fish_income_multi,
        };
        const totalFishMultiOnly = computeTotalFishPerHourFromStats(statsFishMultiOnly, greedy.dronesPerDock, greedy.activeDockId, elixir3xFishingExternal, effectiveRodPower, extraTicksPerHour, effectiveTicksByDock);
        const totalShinyOnly = computeTotalFishPerHourFromStats(statsShinyOnly, greedy.dronesPerDock, greedy.activeDockId, elixir3xFishingExternal, effectiveRodPower, extraTicksPerHour, effectiveTicksByDock);
        breakdownMap.set(def.id, [
          { label: "Fish mult +1%/card", pct: ((totalFishMultiOnly - currentTotal) / currentTotal) * 100 },
          { label: "Shiny +0.1%/card", pct: ((totalShinyOnly - currentTotal) / currentTotal) * 100 },
        ]);
      }

      if (currentTotal > 0 && def.id === "completionist_gatekeeper") {
        const newStats = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, { ...skillOpts, skillTreeLevels: newSkillLevels });
        const statsDroneOnly: ComputedFishingStats = {
          ...newStats,
          super_shiny_chance_pct: currentStats.super_shiny_chance_pct,
          tier2_dock_power_mult: currentStats.tier2_dock_power_mult,
        };
        const statsT2Only: ComputedFishingStats = {
          ...newStats,
          drone_base_power: currentStats.drone_base_power,
          super_shiny_chance_pct: currentStats.super_shiny_chance_pct,
        };
        const statsShinyOnly: ComputedFishingStats = {
          ...newStats,
          drone_base_power: currentStats.drone_base_power,
          tier2_dock_power_mult: currentStats.tier2_dock_power_mult,
        };
        const totalDroneOnly = computeTotalFishPerHourFromStats(statsDroneOnly, greedy.dronesPerDock, greedy.activeDockId, elixir3xFishingExternal, effectiveRodPower, extraTicksPerHour, effectiveTicksByDock);
        const totalT2Only = computeTotalFishPerHourFromStats(statsT2Only, greedy.dronesPerDock, greedy.activeDockId, elixir3xFishingExternal, effectiveRodPower, extraTicksPerHour, effectiveTicksByDock);
        const totalShinyOnly = computeTotalFishPerHourFromStats(statsShinyOnly, greedy.dronesPerDock, greedy.activeDockId, elixir3xFishingExternal, effectiveRodPower, extraTicksPerHour, effectiveTicksByDock);
        breakdownMap.set(def.id, [
          { label: "T2 dock +3%", pct: ((totalT2Only - currentTotal) / currentTotal) * 100 },
          { label: "Drone power +2%", pct: ((totalDroneOnly - currentTotal) / currentTotal) * 100 },
          { label: "Super shiny +1%", pct: ((totalShinyOnly - currentTotal) / currentTotal) * 100 },
        ]);
      }

      const costForNext = def.costs[lvl] ?? 0;
      const gemsForNext = costForNext * GEMS_PER_SKILL_POINT;
      if (def.id !== "friendship_ended_tier1" && marginalPct != null && gemsForNext > 0) {
        if (gemEvGemsPerHour > 0) efficVals.push(marginalPct / (gemsForNext / gemEvGemsPerHour));
        efficValsGemAbs.push((marginalPct / gemsForNext) * 100);
      }
    }
    return {
      skillMarginalPct: marginalMap,
      skillMarginalBreakdown: breakdownMap,
      costEfficHeatMinSkill: efficVals.length ? Math.min(...efficVals) : 0,
      costEfficHeatMaxSkill: efficVals.length ? Math.max(...efficVals) : 1,
      costEfficHeatMinSkillGemAbs: efficValsGemAbs.length ? Math.min(...efficValsGemAbs) : 0,
      costEfficHeatMaxSkillGemAbs: efficValsGemAbs.length ? Math.max(...efficValsGemAbs) : 1,
    };
  }, [
    upgradeLevels,
    enhanceLevels,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.fishingRodCardTier,
    state.mrNibblesLevel,
    state.mrNibblesQuestUnlocked,
    state.mrNibblesQuestRank,
    state.halfWayBundle,
    effectiveRodPower,
    elixir3xFishingExternal,
    extraTicksPerHour,
    gemEvGemsPerHour,
    effectiveTicksByDock,
  ]);

  /** Fish card gild (Card → Gilded): marginal % and cost efficiency. For each fish card we assume rod + all drones on that fish's dock (so Lake fish uses Lake total, etc.). Rod card uses greedy total (independent of Docks area); leg fish excluded. */
  const { fishCardGildMarginalPct, fishCardGildCostEffic, fishCardGildCostEfficGemAbs, fishingRodCardGildMarginalPct, fishingRodCardGildCostEffic, fishingRodCardGildCostEfficGemAbs, costEfficHeatMinFishCard, costEfficHeatMaxFishCard, costEfficHeatMinFishCardGemAbs, costEfficHeatMaxFishCardGemAbs } = useMemo(() => {
    const totalForRod = greedyDisplayedTotals.current;
    const marginalMap = new Map<string, number>();
    const efficMap = new Map<string, number>();
    const efficMapGemAbs = new Map<string, number>();
    const efficVals: number[] = [];
    const efficValsGemAbs: number[] = [];
    let rodMarginalPct: number | null = null;
    let rodCostEffic: number | null = null;
    let rodCostEfficGemAbs: number | null = null;
    const cardToGildedRatio = 2 / 1.5; // Card 1.5× → Gilded 2×
    const skillOptsBase = { skillTreeLevels: state.skillTreeLevels ?? {}, legendaryFishFound: state.legendaryFishFound, relic5xPoints: state.divineRelic5xPoints, mrNibblesLevel: state.mrNibblesLevel, mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked, mrNibblesQuestRank: state.mrNibblesQuestRank, mrNibblesSkin: state.mrNibblesSkin, poseidonIdolLevel: state.poseidonIdolLevel, tethysIdolLevel: state.tethysIdolLevel, astraeusIdolLevel: state.astraeusIdolLevel, droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade, fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3, mrNibblesCardTier: state.mrNibblesCardTier, legendaryHaulerBundle: state.legendaryHaulerBundle, fishersBundle: state.fishersBundle, anglerBundle: state.anglerBundle, halfWayBundle: state.halfWayBundle, divineChallengeCoinLevel: state.divineChallengeCoinLevel, infernalMrNibblesPct: state.infernalMrNibblesPct, infernalMrNibblesLevel: state.infernalMrNibblesLevel, infernalAnglerDronePct: state.infernalAnglerDronePct, infernalAnglerDroneLevel: state.infernalAnglerDroneLevel, constructStatue: state.constructStatue, cetusLevel: state.cetusLevel, blackHoleBonus: state.blackHoleBonus, superStarsLevel: state.superStarsLevel };
    const legFishIds = new Set(LEGENDARY_FISH.map((leg) => leg.id));
    const dockIdsAvailable = new Set(availableDocks.map((d) => d.id));
    const droneCap = Math.floor(stats.fishing_drone_cap);
    const doublePct = stats.double_tick_chance_pct / 100;
    const triplePct = stats.triple_tick_chance_pct / 100;
    const fivePct = stats.five_tick_chance_pct / 100;
    const expectedRollsPerFill = (1 + doublePct) * (1 + 2 * triplePct) * (1 + 4 * fivePct);
    for (const row of visibleGainsRows) {
      if (legFishIds.has(row.fish.id)) continue;
      const tier = (state.fishCardTier[row.fish.id] ?? 0) as FishCardTier;
      if (tier !== 1) continue;
      if (!dockIdsAvailable.has(row.dockId)) continue;
      const set = AQUARIUM.find((s) => s.dockId === row.dockId);
      if (!set) continue;
      const dock = DOCKS.find((d) => d.id === row.dockId)!;
      const powerOnDock =
        dock.tier === 2
          ? (effectiveRodPower + droneCap * stats.drone_base_power) * stats.tier2_dock_power_mult
          : effectiveRodPower + droneCap * stats.drone_base_power;
      const ticksNeeded = effectiveTicksByDock[dock.id] ?? dock.baseTicksNeeded;
      const fillsPerHour = 3600 / (ticksNeeded * effectiveTickSec) + extraTicksPerHour / ticksNeeded;
      let totalOnDock = 0;
      for (const f of set.fish) {
        totalOnDock +=
          fillsPerHour *
          expectedRollsPerFill *
          expectedCatchesPerRoll(powerOnDock, f.powerRating) *
          stats.fish_income_multi *
          expectedShinyMulti *
          getCardMulti(f.id);
      }
      if (totalOnDock <= 0) continue;
      const fishDef = set.fish.find((f) => f.id === row.fish.id)!;
      const fishPerHourForFish =
        fillsPerHour *
        expectedRollsPerFill *
        expectedCatchesPerRoll(powerOnDock, fishDef.powerRating) *
        stats.fish_income_multi *
        expectedShinyMulti *
        getCardMulti(row.fish.id);
      const totalAfterDirect = totalOnDock - fishPerHourForFish + fishPerHourForFish * cardToGildedRatio;
      let marginalPct: number;
      const withThisFishLevel = (state.skillTreeLevels ?? {})["with_this_fish_i_summon_two_more_fish"] ?? 0;
      if (withThisFishLevel > 0) {
        const hypotheticalTier = { ...state.fishCardTier, [row.fish.id]: 2 };
        const newStats = computeFishingStatsFromLevels(upgradeLevels, enhanceLevels, { ...skillOptsBase, fishCardTier: hypotheticalTier });
        const sNew = newStats.shiny_fish_chance_pct / 100;
        const s2New = newStats.super_shiny_chance_pct / 100;
        const newExpectedShinyMulti =
          (1 - sNew) * 1 +
          sNew * (1 - s2New) * newStats.shiny_multiplier +
          sNew * s2New * newStats.shiny_multiplier * newStats.super_shiny_multiplier;
        const skillFactor = (newStats.fish_income_multi / stats.fish_income_multi) * (newExpectedShinyMulti / expectedShinyMulti);
        const totalAfterGild = totalAfterDirect * skillFactor;
        marginalPct = ((totalAfterGild - totalOnDock) / totalOnDock) * 100;
      } else {
        marginalPct = ((totalAfterDirect - totalOnDock) / totalOnDock) * 100;
      }
      marginalMap.set(row.fish.id, marginalPct);
      const gems = getFishCardGildGemCost(row.fish.id);
      if (gems > 0) {
        if (gemEvGemsPerHour > 0) {
          const effic = marginalPct / (gems / gemEvGemsPerHour);
          efficMap.set(row.fish.id, effic);
          efficVals.push(effic);
        }
        const efficGemAbs = (marginalPct / gems) * 100;
        efficMapGemAbs.set(row.fish.id, efficGemAbs);
        efficValsGemAbs.push(efficGemAbs);
      }
    }
    if (state.fishingRodCardTier === 1 && greedyDisplayedTotals.withRodPoly > 0 && totalForRod > 0) {
      rodMarginalPct = ((greedyDisplayedTotals.withRodPoly - totalForRod) / totalForRod) * 100;
      if (gemEvGemsPerHour > 0) {
        rodCostEffic = rodMarginalPct / (FISHING_ROD_GILD_CARD_COST / gemEvGemsPerHour);
        efficVals.push(rodCostEffic);
      }
      rodCostEfficGemAbs = (rodMarginalPct / FISHING_ROD_GILD_CARD_COST) * 100;
      efficValsGemAbs.push(rodCostEfficGemAbs);
    }
    return {
      fishCardGildMarginalPct: marginalMap,
      fishCardGildCostEffic: efficMap,
      fishCardGildCostEfficGemAbs: efficMapGemAbs,
      fishingRodCardGildMarginalPct: rodMarginalPct,
      fishingRodCardGildCostEffic: rodCostEffic,
      fishingRodCardGildCostEfficGemAbs: rodCostEfficGemAbs,
      costEfficHeatMinFishCard: efficVals.length ? Math.min(...efficVals) : 0,
      costEfficHeatMaxFishCard: efficVals.length ? Math.max(...efficVals) : 1,
      costEfficHeatMinFishCardGemAbs: efficValsGemAbs.length ? Math.min(...efficValsGemAbs) : 0,
      costEfficHeatMaxFishCardGemAbs: efficValsGemAbs.length ? Math.max(...efficValsGemAbs) : 1,
    };
  }, [visibleGainsRows, state.fishCardTier, state.fishingRodCardTier, state.skillTreeLevels, state.legendaryFishFound, state.halfWayBundle, state.divineRelic5xPoints, state.infernalMrNibblesPct, state.infernalMrNibblesLevel, state.infernalAnglerDronePct, state.infernalAnglerDroneLevel, upgradeLevels, enhanceLevels, stats.fish_income_multi, stats.shiny_multiplier, stats.super_shiny_multiplier, stats.super_shiny_chance_pct, stats.drone_base_power, stats.tier2_dock_power_mult, stats.double_tick_chance_pct, stats.triple_tick_chance_pct, stats.five_tick_chance_pct, stats.fishing_drone_cap, expectedShinyMulti, greedyDisplayedTotals, gemEvGemsPerHour, availableDocks, effectiveTicksByDock, effectiveTickSec, extraTicksPerHour, effectiveRodPower, getCardMulti]);

  /** Mr Nibbles Card: effective assumed +% gain for next tier (Tiny Notice, same formula as Angler). Excluded from heatmap. */
  const mrNibblesCardNextMarginalPct = useMemo(() => {
    const tier = state.mrNibblesCardTier ?? 0;
    if (tier >= 3) return null;
    const currentTinyPct = stats.tiny_notice_chance_pct;
    const delta = tier === 0 || tier === 1 ? 1 : 2;
    const multWithout = 1 + (currentTinyPct / 100) * 9;
    const multWith = 1 + ((currentTinyPct + delta) / 100) * 9;
    return ((multWith - multWithout) / multWithout) * 100;
  }, [state.mrNibblesCardTier, stats.tiny_notice_chance_pct]);

  /** Mr Nibbles pet +1 level: marginal % total fish/h (greedy dock, same basis as skill / upgrade +% column). */
  const mrNibblesPetNextLevelFishMarginalPct = useMemo(() => {
    if (state.mrNibblesLevel >= 999) return null;
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesCardTier: state.mrNibblesCardTier,
      relic5xPoints: state.divineRelic5xPoints,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesSkin: state.mrNibblesSkin,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const greedy = getGreedyDockAssignment(upgradeLevels, enhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
    const currentTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      greedy.dronesPerDock,
      greedy.activeDockId,
      elixir3xFishingExternal,
      skillOpts,
      extraTicksPerHour,
    );
    if (!(currentTotal > 0)) return null;
    const nextOpts = { ...skillOpts, mrNibblesLevel: state.mrNibblesLevel + 1 };
    const nextTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      greedy.dronesPerDock,
      greedy.activeDockId,
      elixir3xFishingExternal,
      nextOpts,
      extraTicksPerHour,
    );
    return ((nextTotal - currentTotal) / currentTotal) * 100;
  }, [
    upgradeLevels,
    enhanceLevels,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.abyssLegendaryCaught,
    state.fishingRodCardTier,
    state.mrNibblesCardTier,
    state.divineRelic5xPoints,
    state.mrNibblesLevel,
    state.mrNibblesQuestUnlocked,
    state.mrNibblesQuestRank,
    state.mrNibblesSkin,
    state.poseidonIdolLevel,
    state.tethysIdolLevel,
    state.astraeusIdolLevel,
    state.droneBasePowerWorld3Upgrade,
    state.fishingDroneBasePowerWorld3,
    state.legendaryHaulerBundle,
    state.fishersBundle,
    state.anglerBundle,
    state.halfWayBundle,
    state.divineChallengeCoinLevel,
    state.infernalMrNibblesPct,
    state.infernalMrNibblesLevel,
    state.infernalAnglerDronePct,
    state.infernalAnglerDroneLevel,
    state.constructStatue,
    state.cetusLevel,
    state.blackHoleBonus,
    state.superStarsLevel,
    elixir3xFishingExternal,
    extraTicksPerHour,
  ]);

  /** Mr Nibbles Quest +1 rank (when unlocked): marginal % total fish/h (greedy dock, T2 dock power only on T2). */
  const mrNibblesQuestNextRankFishMarginalPct = useMemo(() => {
    if (!state.mrNibblesQuestUnlocked || state.mrNibblesQuestRank >= 999) return null;
    const skillOpts = {
      skillTreeLevels: state.skillTreeLevels,
      fishCardTier: state.fishCardTier,
      legendaryFishFound: state.legendaryFishFound,
      abyssLegendaryCaught: state.abyssLegendaryCaught,
      fishingRodCardTier: state.fishingRodCardTier,
      mrNibblesCardTier: state.mrNibblesCardTier,
      relic5xPoints: state.divineRelic5xPoints,
      mrNibblesLevel: state.mrNibblesLevel,
      mrNibblesQuestUnlocked: state.mrNibblesQuestUnlocked,
      mrNibblesQuestRank: state.mrNibblesQuestRank,
      mrNibblesSkin: state.mrNibblesSkin,
      poseidonIdolLevel: state.poseidonIdolLevel,
      tethysIdolLevel: state.tethysIdolLevel,
      astraeusIdolLevel: state.astraeusIdolLevel,
      droneBasePowerWorld3Upgrade: state.droneBasePowerWorld3Upgrade,
      fishingDroneBasePowerWorld3: state.fishingDroneBasePowerWorld3,
      legendaryHaulerBundle: state.legendaryHaulerBundle,
      fishersBundle: state.fishersBundle,
      anglerBundle: state.anglerBundle,
      halfWayBundle: state.halfWayBundle,
      divineChallengeCoinLevel: state.divineChallengeCoinLevel,
      infernalMrNibblesPct: state.infernalMrNibblesPct,
      infernalMrNibblesLevel: state.infernalMrNibblesLevel,
      infernalAnglerDronePct: state.infernalAnglerDronePct,
      infernalAnglerDroneLevel: state.infernalAnglerDroneLevel,
      constructStatue: state.constructStatue,
      cetusLevel: state.cetusLevel,
      blackHoleBonus: state.blackHoleBonus,
      superStarsLevel: state.superStarsLevel,
    };
    const greedy = getGreedyDockAssignment(upgradeLevels, enhanceLevels, skillOpts, elixir3xFishingExternal, extraTicksPerHour);
    const currentTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      greedy.dronesPerDock,
      greedy.activeDockId,
      elixir3xFishingExternal,
      skillOpts,
      extraTicksPerHour,
    );
    if (!(currentTotal > 0)) return null;
    const nextOpts = { ...skillOpts, mrNibblesQuestRank: state.mrNibblesQuestRank + 1 };
    const nextTotal = computeTotalFishPerHour(
      upgradeLevels,
      enhanceLevels,
      greedy.dronesPerDock,
      greedy.activeDockId,
      elixir3xFishingExternal,
      nextOpts,
      extraTicksPerHour,
    );
    return ((nextTotal - currentTotal) / currentTotal) * 100;
  }, [
    upgradeLevels,
    enhanceLevels,
    state.skillTreeLevels,
    state.fishCardTier,
    state.legendaryFishFound,
    state.abyssLegendaryCaught,
    state.fishingRodCardTier,
    state.mrNibblesCardTier,
    state.divineRelic5xPoints,
    state.mrNibblesLevel,
    state.mrNibblesQuestUnlocked,
    state.mrNibblesQuestRank,
    state.mrNibblesSkin,
    state.poseidonIdolLevel,
    state.tethysIdolLevel,
    state.astraeusIdolLevel,
    state.droneBasePowerWorld3Upgrade,
    state.fishingDroneBasePowerWorld3,
    state.legendaryHaulerBundle,
    state.fishersBundle,
    state.anglerBundle,
    state.halfWayBundle,
    state.divineChallengeCoinLevel,
    state.infernalMrNibblesPct,
    state.infernalMrNibblesLevel,
    state.infernalAnglerDronePct,
    state.infernalAnglerDroneLevel,
    state.constructStatue,
    state.cetusLevel,
    state.blackHoleBonus,
    state.superStarsLevel,
    elixir3xFishingExternal,
    extraTicksPerHour,
  ]);

  /** Unified cost-efficiency heatmap. Min/max over all sections with data. Highest value gets green (t=1), lowest red (t=0). Empty sections excluded; when only one value, scale so it is green. */
  const { costEfficHeatMinGlobal, costEfficHeatMaxGlobal, costEfficHeatMinGemAbsGlobal, costEfficHeatMaxGemAbsGlobal } = useMemo(() => {
    const timeRanges = [
      { min: costEfficHeatMin, max: costEfficHeatMax },
      { min: costEfficHeatMinEnhance, max: costEfficHeatMaxEnhance },
      { min: costEfficHeatMinSkill, max: costEfficHeatMaxSkill },
      { min: costEfficHeatMinFishCard, max: costEfficHeatMaxFishCard },
    ].filter((r) => r.max >= r.min);
    const gemAbsRanges = [
      { min: costEfficHeatMinEnhanceGemAbs, max: costEfficHeatMaxEnhanceGemAbs },
      { min: costEfficHeatMinSkillGemAbs, max: costEfficHeatMaxSkillGemAbs },
      { min: costEfficHeatMinFishCardGemAbs, max: costEfficHeatMaxFishCardGemAbs },
    ].filter((r) => r.max >= r.min);
    const timeMin = timeRanges.length ? Math.min(...timeRanges.map((r) => r.min)) : 0;
    const timeMax = timeRanges.length ? Math.max(...timeRanges.map((r) => r.max)) : 1;
    const gemAbsMin = gemAbsRanges.length ? Math.min(...gemAbsRanges.map((r) => r.min)) : 0;
    const gemAbsMax = gemAbsRanges.length ? Math.max(...gemAbsRanges.map((r) => r.max)) : 1;
    return {
      costEfficHeatMinGlobal: timeMax > timeMin ? timeMin : timeMax - 1,
      costEfficHeatMaxGlobal: timeMax,
      costEfficHeatMinGemAbsGlobal: gemAbsMax > gemAbsMin ? gemAbsMin : gemAbsMax - 1,
      costEfficHeatMaxGemAbsGlobal: gemAbsMax,
    };
  }, [
    costEfficHeatMin,
    costEfficHeatMax,
    costEfficHeatMinEnhance,
    costEfficHeatMaxEnhance,
    costEfficHeatMinEnhanceGemAbs,
    costEfficHeatMaxEnhanceGemAbs,
    costEfficHeatMinSkill,
    costEfficHeatMaxSkill,
    costEfficHeatMinSkillGemAbs,
    costEfficHeatMaxSkillGemAbs,
    costEfficHeatMinFishCard,
    costEfficHeatMaxFishCard,
    costEfficHeatMinFishCardGemAbs,
    costEfficHeatMaxFishCardGemAbs,
  ]);

  return (
    <div className="container fishingModule">
      <div className="header">
        <div>
          <h1 className="title">
            <span style={{ display: "inline-flex", gap: 10, alignItems: "center" }}>
              <img src={FISHING_ICON} alt="Fishing" className="fishingHeaderIcon" />
              <span>Fishing</span>
            </span>
          </h1>
          <p className="subtitle">Enter your fishing stats and toggle docks. Same formulas as game.</p>
        </div>
      </div>

      <div className="fishingTopBar">
        <button
          type="button"
          className="btn btnSecondary"
          onClick={() => {
            if (window.confirm("Reset all Fishing data (upgrades, enhancements, cards, options)? This cannot be undone.")) {
              setState(getDefaultFishingState());
            }
          }}
        >
          Reset all
        </button>
        <div className="fishingGemIncomeToggleWrap">
          <label className="fishingGemIncomeToggle">
            <input
              type="checkbox"
              checked={state.useGemIncomeForCostEffic}
              onChange={(e) => setState((prev) => ({ ...prev, useGemIncomeForCostEffic: e.target.checked }))}
            />
            <span className="fishingGemIncomeToggleLabel">Use Gem Income for Cost Efficiency calculations</span>
          </label>
        </div>
      </div>

      <div className="fishingLayoutGrid">

        <Collapsible
          id="fishing-gains"
          className="fishingGainsCollapsible"
          title={
            <span style={{ display: "flex", flex: 1, alignItems: "center", gap: 8, minWidth: 0 }}>
              Fishing gains (by fish)
              <span style={{ flex: 1, display: "flex", justifyContent: "flex-end", alignItems: "center" }}>
                <span className="mono fishingTotalRainbow" style={{ fontSize: "1.45em" }}>
                  {(() => {
                    const total = visibleGainsRows.reduce((s, r) => s + r.fishPerHour, 0);
                    return total.toLocaleString(undefined, total > 1000 ? { maximumFractionDigits: 0, minimumFractionDigits: 0 } : { maximumFractionDigits: 2, minimumFractionDigits: 2 });
                  })()}/h
                </span>
              </span>
            </span>
          }
          defaultExpanded={false}
          headerRight={
            <Tooltip
              content={{
                title: "Gains from power",
                sections: [
                  {
                    heading: "Legendary fish",
                    lines: [
                      "One per dock, shown first. Requires all fish on that dock at Polychrome and 100%+ catch on the dock's last fish.",
                      "Catch chance: 1/150k per 100% on last fish, max 9/150k per fill.",
                    ],
                  },
                  {
                    heading: "Dock power",
                    lines: [
                      "Each dock's power = rod (if you fish there) + every fishing drone on that dock × drone base power.",
                      "Power sets catch chance and fish per hour.",
                    ],
                  },
                ],
              }}
            />
          }
        >
          <div className="fishingSection">
            <div className="fishingSectionHeader">
              <div className="fishingSectionTitle">
                <span className="mono">Fish per hour</span>
              </div>
            </div>
            <div className="fishingGainsToggleWrap">
              <label className="fishingGainsToggleLabel">
                <input
                  type="checkbox"
                  checked={state.showDisabledFishGrayed}
                  onChange={(e) => setState((prev) => ({ ...prev, showDisabledFishGrayed: e.target.checked }))}
                />
                <span className="small">Show fish from docks with no power (grayed out)</span>
              </label>
              <label className="fishingGainsToggleLabel">
                <input
                  type="checkbox"
                  checked={state.showPolyShardDroprate}
                  onChange={(e) => setState((prev) => ({ ...prev, showPolyShardDroprate: e.target.checked }))}
                />
                <span className="small">Show Poly Shard droprate</span>
              </label>
            </div>
            <div className="fishingGainsList">
              {visibleGainsRows.map(({ dockId, dockName, hasPower, fish, fishPerHour, catchPct, totalMulti, isLegendary, legendaryChanceNum, legendaryChanceDenom }) => {
                const dock = DOCKS.find((d) => d.id === dockId);
                const isActive = hasPower;
                const heatT =
                  heatMax > heatMin && isActive && fishPerHour > 0
                    ? (fishPerHour - heatMin) / (heatMax - heatMin)
                    : 0.5;
                const rateColor = isActive ? heatmapColor(heatT) : undefined;
                const iconSrc = "iconUrl" in fish && fish.iconUrl ? fish.iconUrl : fishIconUrl(fish.iconFile!);
                const showLegendaryXY = isLegendary && isActive && legendaryChanceNum != null && legendaryChanceDenom != null;
                const denomStr = legendaryChanceDenom != null
                  ? (legendaryChanceDenom >= 1000 ? ((legendaryChanceDenom / 1000) % 1 === 0 ? `${legendaryChanceDenom / 1000}k` : `${(legendaryChanceDenom / 1000).toFixed(1)}k`) : String(legendaryChanceDenom))
                  : "";
                const hoursToCatchOne = isActive && fishPerHour > 0 ? 1 / fishPerHour : null;
                return (
                  <div
                    key={`${dockId}-${fish.id}`}
                    className={`fishingGainsRow ${!hasPower ? "fishingGainsRowDisabled" : ""} ${isLegendary ? "fishingGainsRowLegendary" : ""}`}
                    title={!hasPower ? (isLegendary ? `Need all Poly fish cards and 100%+ catch on last fish in ${dockName}` : `No power on dock “${dockName}”`) : undefined}
                  >
                    <img
                      src={iconSrc}
                      alt=""
                      className="fishingFishIcon"
                    />
                    <span className="fishingGainsFishName">
                      {fish.name} ({dockName})
                    </span>
                    {state.showPolyShardDroprate && (state.fishCardTier[fish.id] ?? 0) === 2 && (() => {
                      const odds = getFishPolyShardOdds(fish.id);
                      const polyShardsPerHour = Number.isFinite(odds) && odds > 0 && isActive ? fishPerHour / odds : null;
                      const hoursPerShard = polyShardsPerHour != null && polyShardsPerHour > 0 ? 1 / polyShardsPerHour : null;
                      const label =
                        hoursPerShard != null
                          ? (() => {
                              const totalMin = Math.round(hoursPerShard * 60);
                              const h = Math.floor(totalMin / 60);
                              const m = totalMin % 60;
                              const timeStr = `${h}:${String(m).padStart(2, "0")}`;
                              return `1 Shard ~ ${timeStr} ${hoursPerShard < 1 ? "hour" : "hours"}`;
                            })()
                          : "—";
                      return (
                        <span className="small mono fishingGainsPolyShards" title="Expected time for 1 Polychrome shard (1 in N per catch, Polychrome column from wiki). Only shown when this fish has a Gilded card.">
                          {label}
                        </span>
                      );
                    })()}
                    <span className="fishingGainsRateWrap">
                      {isActive && (
                        <span className="fishingGainsCatchPct" title={isLegendary && !showLegendaryXY ? "Catch chance (%)" : undefined}>
                          {showLegendaryXY ? `${legendaryChanceNum}/${denomStr}` : `${Math.round(catchPct)}%`}
                        </span>
                      )}
                      {!isLegendary && (
                        <span
                          className="mono fishingGainsRate"
                          style={rateColor ? { backgroundColor: rateColor, color: heatT > 0.5 ? "#0a0a0a" : "#fff" } : undefined}
                        >
                          {isActive
                            ? fishPerHour.toLocaleString(undefined, fishPerHour > 1000
                                ? { maximumFractionDigits: 0, minimumFractionDigits: 0 }
                                : { maximumFractionDigits: 2, minimumFractionDigits: 2 })
                            : "—"}
                          /h
                        </span>
                      )}
                      {isLegendary && hoursToCatchOne != null && (
                        <span className="small mono fishingGainsHoursToCatch" title="Expected hours to catch one (based on current effective ticks/h)">
                          ⇒ Will take ~ {hoursToCatchOne >= 1 ? hoursToCatchOne.toFixed(1) : hoursToCatchOne.toFixed(2)} h for 1 catch
                        </span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="fishingGainsElixirRow">
              <img
                src={ELIXIR_3X_FISHING_BUFF_ICON}
                alt=""
                className="fishingGainsElixirIcon"
              />
              <span className="fishingGainsElixirLabel">Elixir drone 3× fishing tick speed</span>
              <span className="fishingGainsElixirValue">
                {formatElixirMinSecPerHour(elixir3xFishingExternal.minPerHour)} / h (
                {Math.round(elixir3xFishingExternal.uptimeFraction * 100)}% uptime → {elixir3xFishingMulti.toFixed(2)}× multi)
              </span>
            </div>

            <Collapsible id="fishing-mc" title="Variance (MC simulation)" defaultExpanded={false}>
              <div className="fishingMcSection">
                <p className="small" style={{ marginBottom: 8 }}>
                  Simulate each fill → 2×/3×/5× tick mult → catch per fish → shiny/super-shiny rolled per fish (same as in-game). EV above is the average; variance can be high.
                </p>
                <div className="fishingMcInputRow">
                    <label className="fishingMcLabel">
                    {typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("de") ? "Stunden" : "Hours"}
                    <input
                      type="number"
                      inputMode="decimal"
                      min={0.1}
                      max={720}
                      step={0.5}
                      className="fishingMcInput"
                      value={state.mcHours}
                      onChange={(e) => {
                        const v = parseFloat(e.target.value);
                        if (Number.isFinite(v)) setState((s) => ({ ...s, mcHours: Math.max(0.1, Math.min(720, v)) }));
                      }}
                      disabled={mcState.running}
                      aria-label="Simulation hours"
                    />
                  </label>
                  <label className="fishingMcLabel">
                    {typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("de") ? "Durchläufe" : "Runs"}
                    <input
                      type="number"
                      min={1000}
                      max={100000}
                      step={1000}
                      className="fishingMcInput"
                      value={state.mcRuns}
                      onChange={(e) => {
                        const v = parseInt(e.target.value, 10);
                        if (Number.isFinite(v)) setState((s) => ({ ...s, mcRuns: Math.max(1000, Math.min(100000, v)) }));
                      }}
                      disabled={mcState.running}
                      aria-label="MC runs"
                    />
                  </label>
                  <button
                    type="button"
                    className="btn"
                    onClick={runFishingMc}
                    disabled={mcState.running || visibleGainsRows.filter((r) => r.hasPower && r.fishPerHour > 0).length === 0}
                  >
                    {mcState.running
                      ? (typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("de") ? "Läuft…" : "Running…")
                      : (typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("de") ? "Simulation starten" : "Run simulation")}
                  </button>
                </div>
                {mcState.samples && mcState.samples.length > 0 && (
                  <div className="fishingMcResults">
                    <div className="fishingMcResultsTitle">
                      Total fish over the next {state.mcHours} h (N={mcState.samples.length.toLocaleString()})
                    </div>
                    {(() => {
                      const s = mcState.samples;
                      const mean = s.reduce((a, b) => a + b, 0) / s.length;
                      const p10 = s[Math.floor(0.1 * s.length)] ?? 0;
                      const p25 = s[Math.floor(0.25 * s.length)] ?? 0;
                      const med = s[Math.floor(0.5 * s.length)] ?? 0;
                      const p75 = s[Math.floor(0.75 * s.length)] ?? 0;
                      const p90 = s[Math.floor(0.9 * s.length)] ?? 0;
                      const evTotal = visibleGainsRows.reduce((sum, r) => sum + (r.hasPower ? r.fishPerHour * state.mcHours : 0), 0);
                      const bins = 14;
                      const lo = s[0] ?? 0;
                      const hi = s[s.length - 1] ?? 0;
                      const span = hi - lo || 1;
                      const counts = new Array(bins).fill(0);
                      for (const v of s) {
                        const idx = Math.min(bins - 1, Math.floor(((v - lo) / span) * bins));
                        counts[idx]++;
                      }
                      const maxCount = Math.max(...counts);
                      return (
                        <>
                          <div className="fishingMcStats">
                            <div className="fishingMcStatRow">
                              <span className="fishingMcStatLabel">Mean (MC)</span>
                              <span className="mono">{mean.toLocaleString(undefined, { maximumFractionDigits: 1 })}</span>
                            </div>
                            <div className="fishingMcStatRow">
                              <span className="fishingMcStatLabel">EV (expected)</span>
                              <span className="mono">{evTotal.toLocaleString(undefined, { maximumFractionDigits: 1 })}</span>
                            </div>
                            <div className="fishingMcStatRow">
                              <span className="fishingMcStatLabel">Median</span>
                              <span className="mono">{med.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                            </div>
                            <div className="fishingMcStatRow fishingMcPercentiles">
                              <span className="fishingMcStatLabel">10th / 25th / 75th / 90th percentile</span>
                              <span className="mono">{p10.toLocaleString(undefined, { maximumFractionDigits: 0 })} / {p25.toLocaleString(undefined, { maximumFractionDigits: 0 })} / {p75.toLocaleString(undefined, { maximumFractionDigits: 0 })} / {p90.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                            </div>
                          </div>
                          <div className="fishingMcHistogramWrap">
                            <div className="fishingMcHistogramBarRow">
                              {counts.map((c, i) => {
                                const barHeightPx = maxCount > 0 ? Math.max(c > 0 ? 4 : 0, Math.round((c / maxCount) * 48)) : 0;
                                return (
                                <div key={i} className="fishingMcHistogramCell" title={`${(lo + (span * i) / bins).toLocaleString(undefined, { maximumFractionDigits: 0 })}–${(lo + (span * (i + 1)) / bins).toLocaleString(undefined, { maximumFractionDigits: 0 })}: ${c}`}>
                                  <div
                                    className="fishingMcHistogramBar"
                                    style={{ height: barHeightPx }}
                                  />
                                </div>
                                );
                              })}
                            </div>
                            <div className="fishingMcHistogramAxis small">
                              <span className="mono">{lo.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                              <span className="fishingMcHistogramAxisLabel">Fish count</span>
                              <span className="mono">{hi.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                            </div>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                )}
                {mcState.samplesPerFish && Object.keys(mcState.samplesPerFish).length > 0 && (() => {
                  const fishIdsWithPower = new Set(visibleGainsRows.filter((r) => r.hasPower && r.fishPerHour > 0).map((r) => r.fish.id));
                  const fishIds = Object.keys(mcState.samplesPerFish).filter((id) => fishIdsWithPower.has(id));
                  let globalHi = 0;
                  for (const id of fishIds) {
                    const a = mcState.samplesPerFish![id]!;
                    if (a.length === 0) continue;
                    const h = a[a.length - 1] ?? 0;
                    if (h > globalHi) globalHi = h;
                  }
                  const globalLo = 0;
                  const globalSpan = globalHi - globalLo || 1;
                  return (
                  <div className="fishingMcPerFishBoxplots">
                    <div className="fishingMcResultsTitle" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      Per fish – box plot (same scale)
                      <Tooltip content={boxplotStatsTooltip} />
                    </div>
                    {fishIds.map((fishId) => {
                        const fish = getFishById(fishId);
                        if (!fish) return null;
                        const arr = mcState.samplesPerFish![fishId]!;
                        const n = arr.length;
                        const q1 = arr[Math.floor(0.25 * n)] ?? 0;
                        const med = arr[Math.floor(0.5 * n)] ?? 0;
                        const q3 = arr[Math.floor(0.75 * n)] ?? 0;
                        const minV = arr[0] ?? 0;
                        const maxV = arr[n - 1] ?? 0;
                        const toPct = (v: number) => ((v - globalLo) / globalSpan) * 100;
                        const pctMin = toPct(minV);
                        const pctQ1 = toPct(q1);
                        const pctMed = toPct(med);
                        const pctQ3 = toPct(q3);
                        const pctMax = toPct(maxV);
                        return (
                          <div key={fishId} className="fishingMcPerFishRow fishingMcBoxplotRow">
                            <div className="fishingMcPerFishHead">
                              <img src={fishIconUrl(fish.iconFile)} alt="" className="fishingFishIcon" />
                              <span className="fishingMcPerFishName">{fish.name}</span>
                              <span className="fishingMcPerFishStats mono small">
                                min {minV.toLocaleString(undefined, { maximumFractionDigits: 0 })} · Q1 {q1.toLocaleString(undefined, { maximumFractionDigits: 0 })} · med {med.toLocaleString(undefined, { maximumFractionDigits: 0 })} · Q3 {q3.toLocaleString(undefined, { maximumFractionDigits: 0 })} · max {maxV.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                              </span>
                            </div>
                            <div className="fishingMcBoxplotTrack">
                              <div className="fishingMcBoxplotWhiskerLeft" style={{ left: `${pctMin}%`, width: `${pctQ1 - pctMin}%` }} />
                              <div className="fishingMcBoxplotBox" style={{ left: `${pctQ1}%`, width: `${pctQ3 - pctQ1}%` }}>
                                <div className="fishingMcBoxplotMedian" style={{ left: `${(pctQ3 - pctQ1 > 0 ? (pctMed - pctQ1) / (pctQ3 - pctQ1) : 0.5) * 100}%` }} />
                              </div>
                              <div className="fishingMcBoxplotWhiskerRight" style={{ left: `${pctQ3}%`, width: `${pctMax - pctQ3}%` }} />
                            </div>
                            <div className="fishingMcPerFishAxis small">
                              <div className="fishingMcPerFishAxisTicks">
                                {[0, 0.2, 0.4, 0.6, 0.8, 1].map((t) => (
                                  <span key={t} className="mono">
                                    {Math.round(globalLo + t * globalSpan).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                  );
                })()}
              </div>
            </Collapsible>
          </div>
        </Collapsible>

        <Collapsible id="fishing-sushi" title="Sushi" defaultExpanded={false}>
          <div className="fishingSection">
            <div className="fishingSectionHeader">
              <img src="https://static.wikitide.net/shminerwiki/6/6d/Sushi.png" alt="" className="fishingSushiIcon" aria-hidden />
              <span className="fishingSectionTitle">Sushi</span>
            </div>
            <p className="small" style={{ marginBottom: 4, opacity: 0.85 }}>
              Sushi gives <span className="mono">{ticksPerSushi + (state.workshopSushiTicksWorld3 ?? 0)}</span> fishing ticks. Effective: <span className="mono">{((ticksPerSushi + (state.workshopSushiTicksWorld3 ?? 0)) * tickMult).toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}</span>
              <Tooltip
                content={{
                  title: "Effective Fishing Ticks",
                  sections: [
                    {
                      heading: "Formula",
                      lines: [
                        "First number: ticks per Sushi (base + card) + Workshop (W3) ticks/h. Effective = that value × tick mult (2×, 3×, 5× from Your stats).",
                      ],
                    },
                    {
                      heading: "Tick mult (2×, 3×, 5×)",
                      lines: [
                        "Three multipliers from Your stats: double tick chance (up to 2×), triple (up to 3×), 5× (up to 5×). They multiply together, e.g. all at 100% → 2× × 3× × 5× = 30×.",
                        "Same formula is used everywhere in Fishing for effective ticks (gains, Sushi EV, MC).",
                      ],
                    },
                    {
                      heading: "Average and MC",
                      lines: [
                        "Average EV (fish per Sushi) and the MC simulation both use effective ticks: fish per hour is already based on effective ticks, so the per-Sushi EV reflects this value.",
                      ],
                    },
                  ],
                }}
                label="?"
              />
            </p>
            <div className="fishingSushiBarBlock">
              <div className="fishingSushiBarHeader">
                <span className="fishingSushiBarLabel">
                  Sushi income per hour
                  <Tooltip
                    content={{
                      title: "Sushi per hour",
                      sections: [
                        {
                          heading: "Sources",
                          lines: [
                            "Gift: Sushi from Statue of Soprano (freebie gift chance) and Founder supply drop (1/1234 × 10 gifts).",
                            "Lootfrog: Sushi from Lootfrog (Drone module). Same ticks per Sushi as Gift Sushi.",
                          ],
                        },
                      ],
                    }}
                    label="?"
                  />
                </span>
                <span className="mono fishingSushiBarValue">
                  {(giftSushiPerHour + lootfrogSushiPerHour).toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}
                </span>
              </div>
              {totalSushiPerHour > 0 ? (
                <div className="fishingSushiBarWrap">
                  <div className="fishingSushiBarBg" role="img" aria-label="Sushi per hour by source">
                    {giftSushiPerHour > 0 ? (
                      <div
                        className="fishingSushiBarSeg fishingSushiBarGift"
                        style={{ width: `${(giftSushiPerHour / totalSushiPerHour) * 100}%` }}
                        title={`Gift: ${giftSushiPerHour.toFixed(2)}/h`}
                      />
                    ) : null}
                    {lootfrogSushiPerHour > 0 ? (
                      <div
                        className="fishingSushiBarSeg fishingSushiBarLootfrog"
                        style={{ width: `${(lootfrogSushiPerHour / totalSushiPerHour) * 100}%` }}
                        title={`Lootfrog: ${lootfrogSushiPerHour.toFixed(2)}/h`}
                      />
                    ) : null}
                  </div>
                  <div className="fishingSushiBarLegend">
                    {giftSushiPerHour > 0 ? (
                      <span className="fishingSushiBarLegendItem">
                        <span className="fishingSushiBarLegendSwatch fishingSushiBarGift" />
                        Gift
                      </span>
                    ) : null}
                    {lootfrogSushiPerHour > 0 ? (
                      <span className="fishingSushiBarLegendItem">
                        <span className="fishingSushiBarLegendSwatch fishingSushiBarLootfrog" />
                        Lootfrog
                      </span>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>
            <div className="fishingFishCardsGrid fishingSushiCardGrid">
              <div className="fishingFishCardCell">
                <div className="fishingFishCardCellTop">
                  <span className="mono">Sushi Misc Card</span>
                </div>
                <FishCardTierToggles
                  value={state.sushiCardTier}
                  onChange={(t) => setState((prev) => ({ ...prev, sushiCardTier: t }))}
                />
              </div>
            </div>
            <div className="fishingSushiStats">
              <div className="fishingSushiStatRow">
                <span className="fishingSushiStatLabel">
                  Average EV (fish per Sushi)
                  <Tooltip
                    content={{
                      title: "Average EV (fish per Sushi)",
                      sections: [
                        { heading: "Meaning", lines: ["Expected fish from one Sushi at your current power and dock setup. Total and per fish."] },
                        { heading: "Formula", lines: ["Ticks per Sushi × (fish/h ÷ ticks/h). Uses same gains as the list above."] },
                      ],
                    }}
                  />
                </span>
                <span className="mono">{sushiEvAndTotal.fishPerSushiEv.toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 })} total</span>
              </div>
              {sushiEvAndTotal.fishPerSushiEvPerFish.length > 0 && (
                <div className="fishingSushiEvPerFish">
                  {sushiEvAndTotal.fishPerSushiEvPerFish.map(({ fishId, fishName, iconFile, iconUrl, fishPerSushiEv }) => {
                    const iconSrc = iconUrl ?? fishIconUrl(iconFile ?? "Gem.png");
                    return (
                    <div key={fishId} className="fishingSushiStatRow fishingSushiEvPerFishRow">
                      <span className="fishingSushiStatLabel">
                        <img src={iconSrc} alt="" className="fishingSushiEvFishIcon" aria-hidden />
                        {fishName}
                      </span>
                      <span className="mono">{fishPerSushiEv.toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}</span>
                    </div>
                    );
                  })}
                </div>
              )}
            </div>
            <Collapsible id="fishing-sushi-mc" title="Variance (MC simulation)" defaultExpanded={false}>
              <div className="fishingSushiMcSection">
                <p className="small" style={{ marginBottom: 8 }}>
                  Simulate opening N independent Sushis; each draw uses Poisson(mean fish per Sushi). Histogram: total fish in one opening.
                </p>
                <div className="fishingMcInputRow" style={{ marginBottom: 8 }}>
                  <label className="fishingMcLabel">
                    {typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("de") ? "Sushis" : "Sushis to simulate"}
                    <input
                      type="number"
                      inputMode="numeric"
                      min={SUSHI_MC_SUSHIS_MIN}
                      max={SUSHI_MC_SUSHIS_MAX}
                      step={100}
                      className="fishingMcInput"
                      value={state.sushiMcSushis}
                      onChange={(e) => {
                        const v = parseInt(e.target.value, 10);
                        if (Number.isFinite(v)) {
                          setState((s) => ({
                            ...s,
                            sushiMcSushis: Math.max(SUSHI_MC_SUSHIS_MIN, Math.min(SUSHI_MC_SUSHIS_MAX, v)),
                          }));
                        }
                      }}
                      disabled={sushiMcState.running}
                      aria-label="Sushi MC: number of Sushis to simulate"
                    />
                  </label>
                  <button
                    type="button"
                    className="btn"
                    onClick={runSushiMc}
                    disabled={sushiMcState.running || visibleGainsRows.filter((r) => r.hasPower && r.fishPerHour > 0).length === 0}
                  >
                    {sushiMcState.running ? "Running…" : "Run simulation"}
                  </button>
                </div>
                {sushiMcState.samples && sushiMcState.samples.length > 0 && sushiMcState.samplesPerFish && (() => {
                  const s = sushiMcState.samples;
                  const mean = s.reduce((a, b) => a + b, 0) / s.length;
                  const p10 = s[Math.floor(0.1 * s.length)] ?? 0;
                  const p25 = s[Math.floor(0.25 * s.length)] ?? 0;
                  const med = s[Math.floor(0.5 * s.length)] ?? 0;
                  const p75 = s[Math.floor(0.75 * s.length)] ?? 0;
                  const p90 = s[Math.floor(0.9 * s.length)] ?? 0;
                  const lo = s[0] ?? 0;
                  const hi = s[s.length - 1] ?? 0;
                  const bins = 14;
                  const span = hi - lo || 1;
                  const counts = new Array(bins).fill(0);
                  for (const v of s) {
                    const idx = Math.min(bins - 1, Math.floor(((v - lo) / span) * bins));
                    counts[idx]++;
                  }
                  const maxCount = Math.max(...counts);
                  const fishIdsWithSamples = sushiEvAndTotal.fishPerSushiEvPerFish.filter((f) => sushiMcState.samplesPerFish![f.fishId]?.length);
                  return (
                    <>
                      <div className="small mono" style={{ marginBottom: 6, opacity: 0.9 }}>
                        N={s.length.toLocaleString()} simulated Sushis
                      </div>
                      <div className="fishingSushiMcStats">
                        <div className="fishingSushiMcStatRow">
                          <span className="fishingSushiMcStatLabel">Mean (MC)</span>
                          <span className="mono">{mean.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                        </div>
                        <div className="fishingSushiMcStatRow">
                          <span className="fishingSushiMcStatLabel">EV (expected)</span>
                          <span className="mono">{sushiEvAndTotal.fishPerSushiEv.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                        </div>
                        <div className="fishingSushiMcStatRow">
                          <span className="fishingSushiMcStatLabel">Median</span>
                          <span className="mono">{med.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                        </div>
                        <div className="fishingSushiMcStatRow">
                          <span className="fishingSushiMcStatLabel">10th / 25th / 75th / 90th %</span>
                          <span className="mono">{p10.toLocaleString(undefined, { maximumFractionDigits: 0 })} / {p25.toLocaleString(undefined, { maximumFractionDigits: 0 })} / {p75.toLocaleString(undefined, { maximumFractionDigits: 0 })} / {p90.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                        </div>
                      </div>
                      <div className="fishingMcHistogramWrap">
                        <div className="fishingMcHistogramBarRow">
                          {counts.map((c, i) => {
                            const barHeightPx = maxCount > 0 ? Math.max(c > 0 ? 4 : 0, Math.round((c / maxCount) * 48)) : 0;
                            return (
                              <div key={i} className="fishingMcHistogramCell" title={`${(lo + (span * i) / bins).toLocaleString(undefined, { maximumFractionDigits: 0 })}–${(lo + (span * (i + 1)) / bins).toLocaleString(undefined, { maximumFractionDigits: 0 })}: ${c}`}>
                                <div className="fishingMcHistogramBar" style={{ height: barHeightPx }} />
                              </div>
                            );
                          })}
                        </div>
                        <div className="fishingMcHistogramAxis small">
                          <span className="mono">{lo.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                          <span className="fishingMcHistogramAxisLabel">Fish per Sushi (total)</span>
                          <span className="mono">{hi.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>
            </Collapsible>
          </div>
        </Collapsible>

        <Collapsible
          id="fishing-your-stats"
          title="Your stats"
          defaultExpanded={false}
          className="fishingLeftPanel"
          headerRight={
            <>
              <Tooltip content={statsTooltip} />
              <span className="small" style={{ opacity: 0.85 }}>Stats § Fishing</span>
            </>
          }
        >
          <div className="fishingSection fishingTickSection">
            <div className="fishingTickRows">
              <div className="fishingTickRow fishingTickRowBase">
                1 Fishing Tick = <span className="mono">{tickDurationSec.toFixed(2)}</span> Seconds
                <span style={{ marginLeft: 6 }}>→ Fishing Ticks per hour = <span className="mono">{tickDurationSec > 0 ? (3600 / tickDurationSec).toFixed(2) : "—"}</span></span>
              </div>
              <div className="fishingTickRow">
                <strong>Effective</strong> 1 Fishing Tick = <span className="mono">{effectiveTickSec.toFixed(2)}</span> Seconds
                <Tooltip
                  content={{
                    title: "Effective fishing tick",
                    lines: [
                      "Time per tick when Elixir Drone 3× Fishing Tick Speed is taken into account. When the buff is active, ticks run 3× faster (real time).",
                      "Fish per hour and fills per hour use this value.",
                    ],
                  }}
                  label="?"
                />
                {effectiveTickSec < tickDurationSec && tickDurationSec > 0 ? (
                  <span className="fishingTickBetterPulse">
                    (Your reality is {((1 - effectiveTickSec / tickDurationSec) * 100).toFixed(0)}% faster!)
                  </span>
                ) : null}
              </div>
              <div className="fishingTickFlowArrow">↓</div>
              <div className="fishingTickRow">
                {tickChartRows.length > 0 ? (
                  <button
                    type="button"
                    className="fishingTickChartBtn"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setTickChartOpen(true);
                    }}
                    title="Effective ticks breakdown"
                    aria-label="Open effective ticks breakdown"
                  >
                    <svg width={20} height={20} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
                      <rect x="5" y="14" width="4" height="6" rx="1.5" fill="currentColor" opacity={0.7} />
                      <rect x="11" y="10" width="4" height="10" rx="1.5" fill="currentColor" opacity={0.85} />
                      <rect x="17" y="6" width="4" height="14" rx="1.5" fill="currentColor" />
                    </svg>
                  </button>
                ) : null}
                <strong>Effective</strong> Fishing Ticks per hour = <span className="mono">{totalEffectiveTicksPerHour > 0 ? totalEffectiveTicksPerHour.toFixed(2) : "—"}</span>
                <Tooltip
                  content={{
                    title: "Effective fishing ticks per hour",
                    lines: [
                      "(Base + Angler + Lootbug + Gift Sushi + Workshop Sushi W3) × double/triple/5× tick mult, plus Gift 5× Tick (basic reward uptime).",
                      "Base ticks (3600 ÷ effective tick sec, incl. Elixir 3×) + Angler + Lootbug + Gift Sushi + Workshop Sushi (Diverse Upgrades) + Gift 5× Tick buff.",
                      "Values from Drone, Lootbug, Gem EV. Open those modules to refresh.",
                    ],
                  }}
                  label="?"
                />
                {rawTicksPerHour > 0 && ticksPerSushi > 0 ? (
                  <span className="fishingTickBetterPulse">
                    (It's like eating {(rawTicksPerHour / ticksPerSushi).toLocaleString(undefined, { maximumFractionDigits: 1, minimumFractionDigits: 1 })} Sushi per hour!)
                  </span>
                ) : null}
              </div>
              {tickChartOpen
                ? createPortal(
                    <div
                      className="modalOverlay fishingChartModalOverlay"
                      onMouseDown={() => setTickChartOpen(false)}
                      role="dialog"
                      aria-modal="true"
                      aria-labelledby="fishing-tick-chart-modal-title"
                    >
                      <div className="modalWindow fishingTickChartModal" onMouseDown={(e) => e.stopPropagation()}>
                        <div className="modalHeader fishingTickChartModalHeader">
                          <div id="fishing-tick-chart-modal-title" className="mono" style={{ fontWeight: 900 }}>
                            Effective Fishing Ticks per hour breakdown
                          </div>
                          <button className="btn btnSecondary" type="button" onClick={() => setTickChartOpen(false)}>
                            Close
                          </button>
                        </div>
                        <div className="modalBody fishingTickChartModalBody">
                          <div className="fishingTickContribBlock">
                            <div className="fishingTickContribTitle">Effective Ticks</div>
                            <div className="fishingTickContribBars" role="img" aria-label="Effective ticks contributions bar chart">
                              {tickChartRows.map((row) => {
                                const pct = totalEffectiveTicksPerHour > 0 ? (row.value / totalEffectiveTicksPerHour) * 100 : 0;
                                const maxVal = Math.max(...tickChartRows.map((r) => r.value), 1);
                                const widthPct = maxVal > 0 ? (row.value / maxVal) * 100 : 0;
                                return (
                                  <div key={row.key} className="fishingTickContribRow">
                                    <div className="fishingTickContribLabel">
                                      <span style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                                        <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                                          {row.icon ?? null}
                                          <span>{row.label}</span>
                                        </span>
                                        {row.subtitle ? (
                                          <span className="small" style={{ opacity: 0.9, fontSize: "11px" }}>{row.subtitle}</span>
                                        ) : null}
                                      </span>
                                    </div>
                                    <div className="fishingTickContribBarTrack">
                                      <div
                                        className="fishingTickContribBarFill"
                                        style={{ width: `${widthPct}%`, backgroundColor: row.color }}
                                      />
                                    </div>
                                    <span className="mono fishingTickContribValue" title={`${row.value.toFixed(1)}/h (${pct.toFixed(1)}%)`}>
                                      {row.value.toFixed(1)}
                                      <span className="fishingTickContribPct"> ({pct.toFixed(1)}%)</span>
                                    </span>
                                    {row.tooltip ? (
                                      <Tooltip content={{ title: row.tooltip.title, lines: row.tooltip.lines }} label="?" />
                                    ) : null}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>,
                    document.body
                  )
                : null}
            </div>
          </div>
          <div className="fishingBoatLevelRow">
            <StatRow
              label="Boat level (T1)"
              iconUrl={upgradeIconUrl("Fishing_Boat_Upgrade.png")}
              value={stats.boat_level}
            />
            <StatRow
              label="Boat level (T2)"
              iconUrl={upgradeIconUrl("Fishing_Boat_Upgrade_T2.png")}
              value={stats.t2_boat_level}
            />
          </div>
          <div className="fishingGrid">
            <div className="fishingSection">
              <div className="fishingSectionHeader">
                <div className="fishingSectionTitle">
                  <span className="mono">Fishing stats</span>
                </div>
              </div>
              <div className="fishingStatsTwoColWrap">
                <div className="fishingStatsCol">
                  <div className="fishingRow fishingRowInline">
                    <div className="fishingLabelLeft">
                      <img src={upgradeIconUrl("Fishing_Rod_Power.png")} alt="" className="iconSmall" style={{ width: 18, height: 18, objectFit: "contain" }} />
                      <span className="fishingLabelName">Fishing Rod Power</span>
                      <Tooltip
                        content={{
                          title: "Fishing Rod Power",
                          sections: [
                            {
                              heading: "Formula",
                              lines: [
                                "10 × 1.16^Fishing Rod level (rounded) × Rod Multiplier (upgrade + enhance) × Motley School.",
                                "Rod Multiplier: +4% per upgrade level, +5% per enhance level. Motley School: +10% per skill level.",
                              ],
                            },
                            { heading: "Card", lines: ["Fishing Rod card multiplies this value (1.02× / 1.05× / 1.10×)."] },
                          ],
                        }}
                      />
                    </div>
                    <span className="mono fishingRowValue">
                      {(stats.fishing_rod_power * FISHING_ROD_CARD_MULT[state.fishingRodCardTier]).toFixed(2)}
                    </span>
                  </div>
                  <StatRow
                    label="Fishing Drone Cap"
                    iconUrl={upgradeIconUrl("Fishing_Drone_Capacity.png")}
                    value={stats.fishing_drone_cap}
                    decimals={2}
                    suffix=""
                  />
                  <StatRow
                    label="Drone Base Power"
                    iconUrl={upgradeIconUrl("Fishing_Drone_Base_Power.png")}
                    value={stats.drone_base_power_base}
                    decimals={2}
                    suffix=""
                  />
                  <div className="fishingRow fishingRowInline">
                    <div className="fishingLabelLeft">
                      <img src={upgradeIconUrl("Drone_Power_Multiplier.png")} alt="" className="iconSmall" style={{ width: 18, height: 18, objectFit: "contain" }} />
                      <span className="fishingRowLabel">Drone Power Multi</span>
                      <Tooltip
                        content={{
                          title: "Drone Power Multi",
                          sections: stats.drone_power_multiplier_breakdown
                            ? [
                                {
                                  heading: "Breakdown (compare with game)",
                                  lines: [
                                    `Upgrade (1 + 0.06×lvl): ×${stats.drone_power_multiplier_breakdown.upgrade.toFixed(2)}`,
                                    `Enhance (1 + 0.08×lvl): ×${stats.drone_power_multiplier_breakdown.enhance.toFixed(2)}`,
                                    `FWF (1 + 0.1×lvl): ×${stats.drone_power_multiplier_breakdown.fwf.toFixed(2)}`,
                                    `Completionist (1 + (0.02×lvl)×leg): ×${stats.drone_power_multiplier_breakdown.completionist.toFixed(2)}`,
                                    `Workshop World 3 (1 + 0.02×lvl): ×${stats.drone_power_multiplier_breakdown.workshop.toFixed(2)}`,
                                    `Tethys Idol (1 + 0.05%×lvl): ×${stats.drone_power_multiplier_breakdown.tethys.toFixed(4)}`,
                                    `Total: ×${stats.drone_power_multiplier.toFixed(2)}`,
                                  ],
                                },
                              ]
                            : [{ heading: "Source", lines: ["Upgrade, Enhance, Skill, Workshop World 3, Tethys Idol."] }],
                        }}
                        label="?"
                      />
                    </div>
                    <span className="mono fishingRowValue">{Number.isFinite(stats.drone_power_multiplier) ? stats.drone_power_multiplier.toFixed(2) : "—"}×</span>
                  </div>
                  <StatRow
                    label="Tier 2 Dock Power"
                    iconUrl={upgradeIconUrl("Tier_2_Dock_Power.png")}
                    value={stats.tier2_dock_power_mult}
                    decimals={2}
                    suffix="×"
                  />
                  <StatRow
                    label="Fish Income Multi"
                    iconUrl={upgradeIconUrl("Fish_Income_Multiplier.png")}
                    value={stats.fish_income_multi}
                    decimals={2}
                    suffix="×"
                  />
                  <StatRow
                    label="Fishing Tick Reduc"
                    iconUrl={upgradeIconUrl("Fishing_Tick_Reduction.png")}
                    value={stats.fishing_tick_reduction}
                    decimals={1}
                    suffix="s"
                  />
                  <StatRow
                    label="Double Tick Chance"
                    iconUrl={upgradeIconUrl("Double_Fish_Tick_Chance.png")}
                    value={stats.double_tick_chance_pct}
                    decimals={2}
                    suffix="%"
                  />
                  <StatRow
                    label="Triple Tick Chance"
                    iconUrl={upgradeIconUrl("Triple_Fish_Tick_Chance.png")}
                    value={stats.triple_tick_chance_pct}
                    decimals={2}
                    suffix="%"
                  />
                </div>
                <div className="fishingStatsCol">
                  <StatRow
                    label="5× Tick Chance"
                    iconUrl={upgradeIconUrl("5x_Fish_Tick_Chance.png")}
                    value={stats.five_tick_chance_pct}
                    decimals={2}
                    suffix="%"
                  />
                  <StatRow
                    label="Token Gain Multi"
                    iconUrl={upgradeIconUrl("Fish_Token_Gain_Multiplier.png")}
                    value={stats.token_gain_multi}
                    decimals={2}
                    suffix="×"
                  />
                  <StatRow
                    label="Notice Fish Req"
                    statIconUrl={fishReqIconUrl("Notice_Fish_Requirement.png")}
                    value={stats.notice_fish_req}
                    decimals={2}
                    suffix="×"
                  />
                  <StatRow
                    label="Tiny Notice Chance"
                    iconUrl={upgradeIconUrl("Tiny_Notice_Chance.png")}
                    value={stats.tiny_notice_chance_pct}
                    decimals={2}
                    suffix="%"
                  />
                  <StatRow
                    label="Shiny Fish Chance"
                    iconUrl={upgradeIconUrl("Shiny_Fish_Chance.png")}
                    value={stats.shiny_fish_chance_pct}
                    decimals={2}
                    suffix="%"
                  />
                  <StatRow
                    label="Shiny Multiplier"
                    iconUrl={upgradeIconUrl("Shiny_Multiplier.png")}
                    value={stats.shiny_multiplier}
                    decimals={2}
                    suffix="×"
                  />
                  <StatRow
                    label="Super Shiny Chance"
                    iconUrl={upgradeIconUrl("Super_Shiny_Fish_Chance.png")}
                    value={stats.super_shiny_chance_pct}
                    decimals={2}
                    suffix="%"
                  />
                  <StatRow
                    label="Super Shiny Multi"
                    iconUrl={upgradeIconUrl("Super_Shiny_Multiplier.png")}
                    value={stats.super_shiny_multiplier}
                    decimals={2}
                    suffix="×"
                  />
                </div>
              </div>
            </div>
          </div>
        </Collapsible>

        <Collapsible id="fishing-docks" title="Docks" defaultExpanded={false}>
          <div className="fishingDocksBox">
            {totalDronesAssigned < droneCap && droneCap > 0 ? (
              <div className="fishingDroneCapWarning" role="alert">
                Assign more drones: {totalDronesAssigned} / {droneCap} (cap). Use + on a dock to add drones.
              </div>
            ) : (
              <div className="fishingDroneCapBar" aria-hidden="true" />
            )}
            <div className="fishingDockHeaderRow">
              <span className="fishingDockHeaderFisher">Fisher here</span>
            </div>
            {availableDocks.map((dock) => {
              const dockPower = powerForDock(dock.id);
              const dockDrones = state.dronesPerDock[dock.id] ?? 0;
              const isActiveDock = state.activeDockId === dock.id;
              const canAdd = totalDronesAssigned < droneCap;
              const canSub = dockDrones > 0;
              return (
                <div key={dock.id} className="fishingDockBlock">
                  <div className="fishingDockRow">
                    <label className="fishingDockRowLabel">
                      <input
                        type="radio"
                        name="fishing_fisher_dock"
                        value={dock.id}
                        checked={isActiveDock}
                        onChange={() => setState((prev) => ({ ...prev, activeDockId: dock.id }))}
                        aria-label={`Fisher at ${dock.name}`}
                      />
                      <span className="fishingDockRowNameBlock">
                        <span className="fishingDockRowName">
                          {dock.name}
                          <span className="fishingDockReqTicks"> (Req: {effectiveTicksByDock[dock.id] ?? dock.baseTicksNeeded} Ticks)</span>
                        </span>
                        <img
                          src={dockIconUrl(dock.id)}
                          alt=""
                          className="fishingDockRowDockImg"
                          onError={(e) => {
                            e.currentTarget.style.display = "none";
                          }}
                        />
                      </span>
                    </label>
                    <span className="fishingDockRowPower">Power: {Math.round(dockPower)}</span>
                    <span className="fishingDockRowDrones">Drones: {dockDrones}</span>
                  </div>
                  <div className="fishingDockDroneControls">
                    <span className="fishingDockDroneControlsLabel">Fishing drone count</span>
                    <button
                      type="button"
                      className="fishingDockDroneBtn fishingDockDroneBtnAll"
                      onClick={() => setDockDronesTo(dock.id, 0)}
                      disabled={dockDrones === 0}
                      aria-label="Remove all drones"
                    >
                      −all
                    </button>
                    <button
                      type="button"
                      className="fishingDockDroneBtn"
                      onClick={() => setDockDrones(dock.id, -1)}
                      disabled={!canSub}
                      aria-label="Remove drone"
                    >
                      −
                    </button>
                    <input
                      type="text"
                      inputMode="numeric"
                      className="fishingDockDroneCount fishingDockDroneCountInput"
                      value={editingDroneCount?.dockId === dock.id ? editingDroneCount.input : String(dockDrones)}
                      onChange={(e) => {
                        if (editingDroneCount?.dockId === dock.id) {
                          setEditingDroneCount({ dockId: dock.id, input: e.target.value });
                        }
                      }}
                      onFocus={() => {
                        if (editingDroneCount != null && editingDroneCount.dockId !== dock.id) {
                          const prev = state.dronesPerDock[editingDroneCount.dockId] ?? 0;
                          const raw = editingDroneCount.input.trim().replace(",", ".");
                          const num = raw === "" ? 0 : Math.trunc(Number(raw));
                          setDockDronesTo(editingDroneCount.dockId, Number.isFinite(num) ? num : prev);
                        }
                        setEditingDroneCount({ dockId: dock.id, input: String(dockDrones) });
                      }}
                      onBlur={() => {
                        if (editingDroneCount?.dockId !== dock.id) return;
                        const raw = editingDroneCount.input.trim().replace(",", ".");
                        const num = raw === "" ? 0 : Math.trunc(Number(raw));
                        setDockDronesTo(dock.id, Number.isFinite(num) ? num : dockDrones);
                        setEditingDroneCount(null);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && editingDroneCount?.dockId === dock.id) {
                          e.currentTarget.blur();
                        }
                      }}
                      aria-label={`Drones at ${dock.name}`}
                    />
                    <button
                      type="button"
                      className="fishingDockDroneBtn"
                      onClick={() => setDockDrones(dock.id, 1)}
                      disabled={!canAdd}
                      aria-label="Add drone"
                    >
                      +
                    </button>
                    <button
                      type="button"
                      className="fishingDockDroneBtn fishingDockDroneBtnAll"
                      onClick={() => setDockDronesTo(dock.id, droneCap - (totalDronesAssigned - dockDrones))}
                      disabled={!canAdd}
                      aria-label="Add all drones to this dock"
                    >
                      +all
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </Collapsible>

        <Collapsible id="fishing-upgrades" title="Available Fishing Upgrades" defaultExpanded={false}>
          <div className="fishingUpgradesPanel">
            <div className="fishingUpgradeSumBlock">
              <span className="fishingUpgradeSumLabel">Dock Score </span>
              <span className="mono">{dockScore.toFixed(2)}</span>
              <Tooltip content={dockScoreTooltip} />
            </div>
            <Collapsible id="fishing-upgrades-t1" title="Tier 1" defaultExpanded={true} className="fishingUpgradesTier">
              <div className="fishingUpgradesList">
                <table className="fishingUpgradeTable">
                  <thead>
                    <tr>
                      <th className="fishingUpgradeThName">Upgrade</th>
                      <th className="fishingUpgradeThLvl">Lvl</th>
                      <th className="fishingUpgradeThCostEffic">
                        Cost Effic.
                        <Tooltip content={costEfficUpgradeTooltip} />
                      </th>
                      <th className="fishingUpgradeThCost">Cost</th>
                      <th className="fishingUpgradeThTime">
                        Time to next
                        <Tooltip
                          content={{
                            title: "Time to next",
                            sections: [
                              {
                                heading: "What it means",
                                lines: [
                                  "Time to get enough of the cost fish for the next level.",
                                  "Assumes all fish per hour goes to that fish type.",
                                ],
                              },
                            ],
                          }}
                        />
                      </th>
                      <th className="fishingUpgradeThSpeed">
                        +% gains
                        <Tooltip
                          content={{
                            title: "+% gains",
                            sections: [
                              {
                                heading: "Marginal gain",
                                lines: [
                                  "Percent increase in total fish per hour for +1 level of this upgrade.",
                                  "Assumes rod and all drones on the highest unlocked dock.",
                                  "E.g. Cave when T2 is just unlocked.",
                                ],
                              },
                            ],
                          }}
                        />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                {availableT1Upgrades.map((def) => {
                  const costs = UPGRADE_COSTS[def.id];
                  const maxLvl = costs?.length ? costs[costs.length - 1]!.level : 0;
                  const lvl = Math.max(0, Math.min(maxLvl, upgradeLevels[def.id] ?? 0));
                  const nextLevel = lvl + 1;
                  const nextCostEntry = costs?.find((c) => c.level === nextLevel);
                  const fishPerHour = nextCostEntry
                    ? (totalFishPerHourByFishId[nextCostEntry.fishId] ?? 0)
                    : 0;
                  const hoursToNext =
                    nextCostEntry && fishPerHour > 0
                      ? nextCostEntry.amount / fishPerHour
                      : null;
                  const fishDef = nextCostEntry ? getFishById(nextCostEntry.fishId) : undefined;
                  const isMaxed = lvl >= maxLvl;
                  const marginalPct = upgradeMarginalPct.get(def.id) ?? null;
                  const nextEffect = upgradeNextEffect.get(def.id) ?? null;
                  return (
                    <tr key={def.id} className="fishingUpgradeRow">
                      <td className="fishingUpgradeTdName">
                        <img src={upgradeIconUrl(def.iconFile)} alt="" className="fishingUpgradeIcon" />
                        <div className="fishingUpgradeNameBlock">
                          <span className="fishingUpgradeName">{def.name}</span>
                          {nextEffect != null ? <span className="fishingUpgradeNextEffect">{nextEffect}</span> : null}
                        </div>
                      </td>
                      <td className="fishingUpgradeTdLvl">
                        {isMaxed ? (
                          <div className="fishingUpgradeLvlMaxedRow">
                            <span className="fishingUpgradeLevelLabel">
                              lvl <span className="mono">{lvl}</span> / {maxLvl}
                            </span>
                            <button
                              type="button"
                              className="btn btnSecondary fishingUpgradeBtnMaxed"
                              onClick={() => setFishingUpgradeLevel(def.id, -1)}
                              aria-label="Decrease level"
                            >
                              −
                            </button>
                          </div>
                        ) : (
                          <>
                            <span className="fishingUpgradeLevelLabel">
                              lvl <span className="mono">{lvl}</span> / {maxLvl}
                            </span>
                            <div className="btnRow fishingUpgradeButtons">
                              <button
                                type="button"
                                className="btn btnSecondary"
                                onClick={() => setFishingUpgradeLevel(def.id, -1)}
                                disabled={lvl <= 0}
                                aria-label="Decrease level"
                              >
                                −
                              </button>
                              <button
                                type="button"
                                className="btn"
                                onClick={() => setFishingUpgradeLevel(def.id, 1)}
                                aria-label="Increase level"
                              >
                                +
                              </button>
                            </div>
                          </>
                        )}
                      </td>
                      <td className="fishingUpgradeTdCostEffic">
                        {!isMaxed &&
                        marginalPct != null &&
                        marginalPct >= 0 &&
                        hoursToNext != null &&
                        hoursToNext > 0
                          ? (() => {
                              const costEffic = marginalPct / hoursToNext;
                              const useUpgradeScale = !state.useGemIncomeForCostEffic;
                              const heatMinU = useUpgradeScale ? costEfficHeatMin : costEfficHeatMinGlobal;
                              const heatMaxU = useUpgradeScale ? costEfficHeatMax : costEfficHeatMaxGlobal;
                              const heatT =
                                heatMaxU > heatMinU
                                  ? (costEffic - heatMinU) / (heatMaxU - heatMinU)
                                  : 0.5;
                              const rateColor = heatmapColor(heatT);
                              return (
                                <span
                                  style={{
                                    backgroundColor: rateColor,
                                    color: heatT > 0.5 ? "#0a0a0a" : "#fff",
                                    padding: "2px 6px",
                                    borderRadius: 4,
                                  }}
                                >
                                  {costEffic.toFixed(2)}
                                </span>
                              );
                            })()
                          : "—"}
                      </td>
                      <td className="fishingUpgradeTdCost">
                        {isMaxed ? (
                          <span className="fishingUpgradeMaxed">Maxed</span>
                        ) : nextCostEntry && fishDef ? (
                          <>
                            <span className="fishingUpgradeCostBox">
                              <img src={fishIconUrl(fishDef.iconFile)} alt="" className="fishingUpgradeCostFishIcon" />
                              <span className="mono">{formatCostCompact(nextCostEntry.amount)}</span>
                            </span>
                          </>
                        ) : nextCostEntry ? (
                          <span className="fishingUpgradeCostBox">
                            <span className="mono">{formatCostCompact(nextCostEntry.amount)}</span>
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="fishingUpgradeTdTime">
                        <span className="fishingUpgradeTimeToNext">
                          {!isMaxed && hoursToNext != null
                            ? formatHoursToHhMin(hoursToNext)
                            : isMaxed
                              ? ""
                              : "—"}
                        </span>
                      </td>
                      <td className="fishingUpgradeTdSpeed">
                        {marginalPct != null && marginalPct >= 0
                          ? `+${marginalPct.toFixed(1)}%`
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
                  </tbody>
                </table>
              </div>
            </Collapsible>
            <Collapsible id="fishing-upgrades-t2" title="Tier 2" defaultExpanded={false} className="fishingUpgradesTier">
              <div className="fishingUpgradesList">
                <table className="fishingUpgradeTable">
                  <thead>
                    <tr>
                      <th className="fishingUpgradeThName">Upgrade</th>
                      <th className="fishingUpgradeThLvl">Lvl</th>
                      <th className="fishingUpgradeThCostEffic">
                        Cost Effic.
                        <Tooltip content={costEfficUpgradeTooltip} />
                      </th>
                      <th className="fishingUpgradeThCost">Cost</th>
                      <th className="fishingUpgradeThTime">
                        Time to next
                        <Tooltip
                          content={{
                            title: "Time to next",
                            sections: [
                              {
                                heading: "What it means",
                                lines: [
                                  "Time to get enough of the cost fish for the next level.",
                                  "Assumes all fish per hour goes to that fish type.",
                                ],
                              },
                            ],
                          }}
                        />
                      </th>
                      <th className="fishingUpgradeThSpeed">
                        +% gains
                        <Tooltip
                          content={{
                            title: "+% gains",
                            sections: [
                              {
                                heading: "Marginal gain",
                                lines: [
                                  "Percent increase in total fish per hour for +1 level of this upgrade.",
                                  "Assumes rod and all drones on the highest unlocked dock.",
                                  "E.g. Cave when T2 is just unlocked.",
                                ],
                              },
                            ],
                          }}
                        />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                {availableT2Upgrades.map((def) => {
                  const costs = UPGRADE_COSTS[def.id];
                  const maxLvl = costs?.length ? costs[costs.length - 1]!.level : 0;
                  const lvl = Math.max(0, Math.min(maxLvl, upgradeLevels[def.id] ?? 0));
                  const nextLevel = lvl + 1;
                  const nextCostEntry = costs?.find((c) => c.level === nextLevel);
                  const fishPerHour = nextCostEntry
                    ? (totalFishPerHourByFishId[nextCostEntry.fishId] ?? 0)
                    : 0;
                  const hoursToNext =
                    nextCostEntry && fishPerHour > 0
                      ? nextCostEntry.amount / fishPerHour
                      : null;
                  const fishDef = nextCostEntry ? getFishById(nextCostEntry.fishId) : undefined;
                  const isMaxed = lvl >= maxLvl;
                  const marginalPct = upgradeMarginalPct.get(def.id) ?? null;
                  const nextEffect = upgradeNextEffect.get(def.id) ?? null;
                  return (
                    <tr key={def.id} className="fishingUpgradeRow">
                      <td className="fishingUpgradeTdName">
                        <img src={upgradeIconUrl(def.iconFile)} alt="" className="fishingUpgradeIcon" />
                        <div className="fishingUpgradeNameBlock">
                          <span className="fishingUpgradeName">{def.name}</span>
                          {nextEffect != null ? <span className="fishingUpgradeNextEffect">{nextEffect}</span> : null}
                        </div>
                      </td>
                      <td className="fishingUpgradeTdLvl">
                        {isMaxed ? (
                          <div className="fishingUpgradeLvlMaxedRow">
                            <span className="fishingUpgradeLevelLabel">
                              lvl <span className="mono">{lvl}</span> / {maxLvl}
                            </span>
                            <button
                              type="button"
                              className="btn btnSecondary fishingUpgradeBtnMaxed"
                              onClick={() => setFishingUpgradeLevel(def.id, -1)}
                              aria-label="Decrease level"
                            >
                              −
                            </button>
                          </div>
                        ) : (
                          <>
                            <span className="fishingUpgradeLevelLabel">
                              lvl <span className="mono">{lvl}</span> / {maxLvl}
                            </span>
                            <div className="btnRow fishingUpgradeButtons">
                              <button
                                type="button"
                                className="btn btnSecondary"
                                onClick={() => setFishingUpgradeLevel(def.id, -1)}
                                disabled={lvl <= 0}
                                aria-label="Decrease level"
                              >
                                −
                              </button>
                              <button
                                type="button"
                                className="btn"
                                onClick={() => setFishingUpgradeLevel(def.id, 1)}
                                aria-label="Increase level"
                              >
                                +
                              </button>
                            </div>
                          </>
                        )}
                      </td>
                      <td className="fishingUpgradeTdCostEffic">
                        {!isMaxed &&
                        marginalPct != null &&
                        marginalPct >= 0 &&
                        hoursToNext != null &&
                        hoursToNext > 0
                          ? (() => {
                              const costEffic = marginalPct / hoursToNext;
                              const useUpgradeScale = !state.useGemIncomeForCostEffic;
                              const heatMinU = useUpgradeScale ? costEfficHeatMin : costEfficHeatMinGlobal;
                              const heatMaxU = useUpgradeScale ? costEfficHeatMax : costEfficHeatMaxGlobal;
                              const heatT =
                                heatMaxU > heatMinU
                                  ? (costEffic - heatMinU) / (heatMaxU - heatMinU)
                                  : 0.5;
                              const rateColor = heatmapColor(heatT);
                              return (
                                <span
                                  style={{
                                    backgroundColor: rateColor,
                                    color: heatT > 0.5 ? "#0a0a0a" : "#fff",
                                    padding: "2px 6px",
                                    borderRadius: 4,
                                  }}
                                >
                                  {costEffic.toFixed(2)}
                                </span>
                              );
                            })()
                          : "—"}
                      </td>
                      <td className="fishingUpgradeTdCost">
                        {isMaxed ? (
                          <span className="fishingUpgradeMaxed">Maxed</span>
                        ) : nextCostEntry && fishDef ? (
                          <span className="fishingUpgradeCostBox">
                            <img src={fishIconUrl(fishDef.iconFile)} alt="" className="fishingUpgradeCostFishIcon" />
                            <span className="mono">{formatCostCompact(nextCostEntry.amount)}</span>
                          </span>
                        ) : nextCostEntry ? (
                          <span className="fishingUpgradeCostBox">
                            <span className="mono">{formatCostCompact(nextCostEntry.amount)}</span>
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="fishingUpgradeTdTime">
                        <span className="fishingUpgradeTimeToNext">
                          {!isMaxed && hoursToNext != null
                            ? formatHoursToHhMin(hoursToNext)
                            : isMaxed
                              ? ""
                              : "—"}
                        </span>
                      </td>
                      <td className="fishingUpgradeTdSpeed">
                        {marginalPct != null && marginalPct >= 0
                          ? `+${marginalPct.toFixed(1)}%`
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
                  </tbody>
                </table>
              </div>
            </Collapsible>
          </div>
        </Collapsible>

        <Collapsible id="fishing-enhancements" title="Available Fishing Enhancements" defaultExpanded={false}>
          <div className="fishingUpgradesPanel">
            <p className="fishingEnhancementsIntro">
              Enhancements cost <img src={GEM_ICON_URL} alt="gems" className="fishingGemIcon" /> gems. They do not count toward completion. See{" "}
              <a href="https://shminer.miraheze.org/wiki/Fishing#Enhancements" target="_blank" rel="noopener noreferrer">Fishing § Enhancements</a>.
            </p>
            <p className="fishingEnhancementsIntro fishingEnhancementsTotalSpent">
              Gems spent on enhancements so far:{" "}
              <span className="mono" style={{ fontVariantNumeric: "tabular-nums" }}>{totalGemsSpentOnEnhancements.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
              {" "}<img src={GEM_ICON_URL} alt="" className="fishingGemIcon" />
            </p>
            <p className="fishingEnhancementsIntro fishingEnhancementsBestToMax">
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
                Best to max for +% fish/h (excl. Fish Multiplier)
                <Tooltip
                  content={{
                    title: "Best enhancement to max",
                    sections: [
                      {
                        heading: "Meaning",
                        lines: [
                          "Which enhancement adds the most total fish per hour if you buy every remaining level up to max.",
                          "Fish Multiplier is excluded so you can compare the other lines.",
                        ],
                      },
                      {
                        heading: "Numbers",
                        lines: [
                          "Total % = (fish/h at max level − current fish/h) ÷ current fish/h.",
                          "Gem cost = sum of gem prices for each level from your next level through max.",
                        ],
                      },
                      {
                        heading: "Model",
                        lines: [
                          "Same greedy dock and total fish/h as the +% gains column.",
                        ],
                      },
                    ],
                  }}
                />
                :{" "}
                {bestEnhancementToMaxExclFishMultiplier ? (
                  <>
                    <span className="fishingUpgradeName">{bestEnhancementToMaxExclFishMultiplier.name}</span>
                    {" — "}
                    <span className="mono" style={{ fontVariantNumeric: "tabular-nums" }}>
                      +{bestEnhancementToMaxExclFishMultiplier.totalPct.toFixed(1)}%
                    </span>
                    {" total, "}
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                      <span className="mono" style={{ fontVariantNumeric: "tabular-nums" }}>
                        {bestEnhancementToMaxExclFishMultiplier.totalGems.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                      <img src={GEM_ICON_URL} alt="" className="fishingGemIcon" />
                      {bestEnhancementToMaxExclFishMultiplier.costEfficGemAbs != null ? (
                        <Tooltip
                          content={{
                            title: "Cost efficiency",
                            sections: [
                              {
                                heading: "This path",
                                lines: [
                                  `+${bestEnhancementToMaxExclFishMultiplier.totalPct.toFixed(1)}% total gain vs current fish/h.`,
                                  `${bestEnhancementToMaxExclFishMultiplier.totalGems.toLocaleString(undefined, { maximumFractionDigits: 0 })} gems for all remaining levels to max.`,
                                ],
                              },
                              {
                                heading: "Gem absolute",
                                lines: [
                                  `(${bestEnhancementToMaxExclFishMultiplier.totalPct.toFixed(1)}% ÷ ${bestEnhancementToMaxExclFishMultiplier.totalGems.toLocaleString(undefined, { maximumFractionDigits: 0 })}) × 100 = ${bestEnhancementToMaxExclFishMultiplier.costEfficGemAbs.toFixed(2)}.`,
                                  "Same scale as the Cost Effic. column when Use Gem Income for Cost Efficiency is OFF.",
                                ],
                              },
                              ...(gemEvGemsPerHour > 0 && bestEnhancementToMaxExclFishMultiplier.costEfficGemIncome != null
                                ? [
                                    {
                                      heading: "Gem income (EV)",
                                      lines: [
                                        `${gemEvGemsPerHour.toFixed(1)} gems/h from Gem EV (open Gem EV to sync).`,
                                        `Hours to earn this path: ${formatHoursToHhMin(bestEnhancementToMaxExclFishMultiplier.totalGems / gemEvGemsPerHour)}.`,
                                        `Cost efficiency: ${bestEnhancementToMaxExclFishMultiplier.costEfficGemIncome.toFixed(2)} = total % ÷ (total gems ÷ gems/h).`,
                                        "Same scale as the Cost Effic. column when Use Gem Income for Cost Efficiency is ON.",
                                      ],
                                    },
                                  ]
                                : [
                                    {
                                      heading: "Gem income (EV)",
                                      lines: [
                                        "Open Gem EV Calculator to sync gems/h.",
                                        "Then cost efficiency here matches the enhancement table with Use Gem Income for Cost Efficiency ON (total % ÷ hours to earn the full gem cost).",
                                      ],
                                    },
                                  ]),
                            ],
                          }}
                        />
                      ) : null}
                    </span>
                  </>
                ) : (
                  <span style={{ opacity: 0.85 }}>
                    All listed enhancements (excl. Fish Multiplier) are maxed, or fish/h is zero.
                  </span>
                )}
              </span>
            </p>
            <Collapsible id="fishing-enhancements-t1" title="Tier 1" defaultExpanded={true} className="fishingUpgradesTier">
              <div className="fishingUpgradesList">
                <table className="fishingUpgradeTable">
                  <thead>
                    <tr>
                      <th className="fishingUpgradeThName">Enhancement</th>
                      <th className="fishingUpgradeThLvl">Lvl</th>
                      <th className="fishingUpgradeThCostEffic">
                        Cost Effic.
                        <Tooltip content={costEfficGemTooltip} />
                      </th>
                      <th className="fishingUpgradeThCost">Cost</th>
                      <th className="fishingUpgradeThTime">
                        Time to next
                        <Tooltip
                          content={{
                            title: "Time to next",
                            lines: [
                              "Hours to earn the gem cost at your Gem EV rate. Open Gem EV to sync.",
                            ],
                          }}
                        />
                      </th>
                      <th className="fishingUpgradeThSpeed">
                        +% gains
                        <Tooltip
                          content={{
                            title: "+% gains",
                            sections: [
                              {
                                heading: "Marginal gain",
                                lines: [
                                  "Percent increase in total fish per hour for +1 level of this enhancement.",
                                  "Assumes rod and all drones on the highest unlocked dock.",
                                  "E.g. Cave when T2 is just unlocked.",
                                ],
                              },
                            ],
                          }}
                        />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {availableT1Enhancements.map((def) => {
                      const costs = ENHANCE_COSTS_T1[def.id as keyof typeof ENHANCE_COSTS_T1];
                      const maxLvl = costs?.length ? costs[costs.length - 1]!.level : 0;
                      const lvl = Math.max(0, Math.min(maxLvl, enhanceLevels[def.id] ?? 0));
                      const nextLevel = lvl + 1;
                      const nextCostEntry = costs?.find((c) => c.level === nextLevel);
                      const isMaxed = lvl >= maxLvl;
                      const marginalPct = enhanceMarginalPct.get(def.id) ?? null;
                      const nextEffect = enhanceNextEffect.get(def.id) ?? null;
                      return (
                        <tr key={def.id} className="fishingUpgradeRow">
                          <td className="fishingUpgradeTdName">
                            <img src={enhanceIconUrl(def.iconFile)} alt="" className="fishingUpgradeIcon" />
                            <div className="fishingUpgradeNameBlock">
                              <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                                <span className="fishingUpgradeName">{def.name}</span>
                                {def.id === "enhance_token_multiplier" ? (
                                  <Tooltip
                                    content={{
                                      title: "Effective fish gain",
                                      sections: [
                                        {
                                          heading: "Indirect gains",
                                          lines: [
                                            "Token Multiplier adds +0.05 per level (1.05x, 1.10x, …). The shown % is the marginal gain for the next level (e.g. 1.05→1.10 is 0.05/1.05 ≈ 4.76%).",
                                            "If you use tokens for fish-related gains, this is the effective relative gain. Cost efficiency shown but excluded from heatmap.",
                                          ],
                                        },
                                      ],
                                    }}
                                    label="?"
                                  />
                                ) : def.id === "enhance_tiny_notice_chance" ? (
                                  <Tooltip
                                    content={{
                                      title: "Effective fish gain (notice farming)",
                                      sections: [
                                        {
                                          heading: "Indirect gains",
                                          lines: [
                                            "Tiny is an attribute a Notice can have: it costs 90% less fish.",
                                            "Tiny Notice Chance +0.5% per level; Tiny = 10× value. The shown % is the marginal gain for the next level (relative to current expected mult; first level ≈ 4.5%, then slightly less).",
                                            "Fish/h does not change; the gain is in cheaper notices. Cost efficiency excluded from heatmap.",
                                          ],
                                        },
                                      ],
                                    }}
                                    label="?"
                                  />
                                ) : null}
                              </span>
                              {nextEffect != null ? <span className="fishingUpgradeNextEffect">{nextEffect}</span> : null}
                            </div>
                          </td>
                          <td className="fishingUpgradeTdLvl">
                            {isMaxed ? (
                              <div className="fishingUpgradeLvlMaxedRow">
                                <span className="fishingUpgradeLevelLabel">
                                  lvl <span className="mono">{lvl}</span> / {maxLvl}
                                </span>
                                <button
                                  type="button"
                                  className="btn btnSecondary fishingUpgradeBtnMaxed"
                                  onClick={() => setFishingEnhanceLevel(def.id, -1)}
                                  aria-label="Decrease level"
                                >
                                  −
                                </button>
                              </div>
                            ) : (
                              <>
                                <span className="fishingUpgradeLevelLabel">
                                  lvl <span className="mono">{lvl}</span> / {maxLvl}
                                </span>
                                <div className="btnRow fishingUpgradeButtons">
                                  <button
                                    type="button"
                                    className="btn btnSecondary"
                                    onClick={() => setFishingEnhanceLevel(def.id, -1)}
                                    disabled={lvl <= 0}
                                    aria-label="Decrease level"
                                  >
                                    −
                                  </button>
                                  <button
                                    type="button"
                                    className="btn"
                                    onClick={() => setFishingEnhanceLevel(def.id, 1)}
                                    aria-label="Increase level"
                                  >
                                    +
                                  </button>
                                </div>
                              </>
                            )}
                          </td>
                          <td className="fishingUpgradeTdCostEffic">
                            {!isMaxed &&
                            marginalPct != null &&
                            marginalPct >= 0 &&
                            nextCostEntry &&
                            nextCostEntry.gems > 0 &&
                            (state.useGemIncomeForCostEffic ? gemEvGemsPerHour > 0 : true)
                              ? (() => {
                                  const costEffic = state.useGemIncomeForCostEffic
                                    ? marginalPct / (nextCostEntry.gems / gemEvGemsPerHour)
                                    : (marginalPct / nextCostEntry.gems) * 100;
                                  const excludeFromHeatmap = def.id === "enhance_token_multiplier" || def.id === "enhance_tiny_notice_chance";
                                  const { min: heatMin, max: heatMax } = state.useGemIncomeForCostEffic
                                    ? { min: costEfficHeatMinGlobal, max: costEfficHeatMaxGlobal }
                                    : { min: costEfficHeatMinGemAbsGlobal, max: costEfficHeatMaxGemAbsGlobal };
                                  const heatT = !excludeFromHeatmap && heatMax > heatMin ? (costEffic - heatMin) / (heatMax - heatMin) : 0.5;
                                  const rateColor = excludeFromHeatmap ? "transparent" : heatmapColor(heatT);
                                  return (
                                    <span
                                      style={
                                        excludeFromHeatmap
                                          ? undefined
                                          : {
                                              backgroundColor: rateColor,
                                              color: heatT > 0.5 ? "#0a0a0a" : "#fff",
                                              padding: "2px 6px",
                                              borderRadius: 4,
                                            }
                                      }
                                    >
                                      {costEffic.toFixed(2)}
                                    </span>
                                  );
                                })()
                              : "—"}
                          </td>
                          <td className="fishingUpgradeTdCost">
                            {isMaxed ? (
                              <span className="fishingUpgradeMaxed">Maxed</span>
                            ) : nextCostEntry ? (
                              <span className="fishingUpgradeCostBox">
                                <img src={GEM_ICON_URL} alt="" className="fishingUpgradeCostFishIcon" />
                                <span className="mono">{formatCostCompact(nextCostEntry.gems)}</span>
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="fishingUpgradeTdTime">
                            {!isMaxed && nextCostEntry && nextCostEntry.gems > 0 && gemEvGemsPerHour > 0
                              ? formatHoursToHhMin(nextCostEntry.gems / gemEvGemsPerHour)
                              : "—"}
                          </td>
                          <td className="fishingUpgradeTdSpeed">
                            {marginalPct != null
                              ? marginalPct >= 0
                                ? `+${marginalPct.toFixed(1)}%`
                                : `${marginalPct.toFixed(1)}%`
                              : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Collapsible>
            <Collapsible id="fishing-enhancements-t2" title="Tier 2" defaultExpanded={false} className="fishingUpgradesTier">
              <div className="fishingUpgradesList">
                <table className="fishingUpgradeTable">
                  <thead>
                    <tr>
                      <th className="fishingUpgradeThName">Enhancement</th>
                      <th className="fishingUpgradeThLvl">Lvl</th>
                      <th className="fishingUpgradeThCostEffic">
                        Cost Effic.
                        <Tooltip content={costEfficGemTooltip} />
                      </th>
                      <th className="fishingUpgradeThCost">Cost</th>
                      <th className="fishingUpgradeThTime">
                        Time to next
                        <Tooltip
                          content={{
                            title: "Time to next",
                            lines: [
                              "Hours to earn the gem cost at your Gem EV rate. Open Gem EV to sync.",
                            ],
                          }}
                        />
                      </th>
                      <th className="fishingUpgradeThSpeed">
                        +% gains
                        <Tooltip
                          content={{
                            title: "+% gains",
                            sections: [
                              {
                                heading: "Marginal gain",
                                lines: [
                                  "Percent increase in total fish per hour for +1 level of this enhancement.",
                                  "Assumes rod and all drones on the highest unlocked dock.",
                                  "E.g. Cave when T2 is just unlocked.",
                                ],
                              },
                            ],
                          }}
                        />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {availableT2Enhancements.map((def) => {
                      const costs = ENHANCE_COSTS_T2[def.id as keyof typeof ENHANCE_COSTS_T2];
                      const maxLvl = costs?.length ? costs[costs.length - 1]!.level : 0;
                      const lvl = Math.max(0, Math.min(maxLvl, enhanceLevels[def.id] ?? 0));
                      const nextLevel = lvl + 1;
                      const nextCostEntry = costs?.find((c) => c.level === nextLevel);
                      const isMaxed = lvl >= maxLvl;
                      const marginalPct = enhanceMarginalPct.get(def.id) ?? null;
                      const nextEffect = enhanceNextEffect.get(def.id) ?? null;
                      return (
                        <tr key={def.id} className="fishingUpgradeRow">
                          <td className="fishingUpgradeTdName">
                            <img src={enhanceIconUrl(def.iconFile)} alt="" className="fishingUpgradeIcon" />
                            <div className="fishingUpgradeNameBlock">
                              <span className="fishingUpgradeName">{def.name}</span>
                              {nextEffect != null ? <span className="fishingUpgradeNextEffect">{nextEffect}</span> : null}
                            </div>
                          </td>
                          <td className="fishingUpgradeTdLvl">
                            {isMaxed ? (
                              <div className="fishingUpgradeLvlMaxedRow">
                                <span className="fishingUpgradeLevelLabel">
                                  lvl <span className="mono">{lvl}</span> / {maxLvl}
                                </span>
                                <button
                                  type="button"
                                  className="btn btnSecondary fishingUpgradeBtnMaxed"
                                  onClick={() => setFishingEnhanceLevel(def.id, -1)}
                                  aria-label="Decrease level"
                                >
                                  −
                                </button>
                              </div>
                            ) : (
                              <>
                                <span className="fishingUpgradeLevelLabel">
                                  lvl <span className="mono">{lvl}</span> / {maxLvl}
                                </span>
                                <div className="btnRow fishingUpgradeButtons">
                                  <button
                                    type="button"
                                    className="btn btnSecondary"
                                    onClick={() => setFishingEnhanceLevel(def.id, -1)}
                                    disabled={lvl <= 0}
                                    aria-label="Decrease level"
                                  >
                                    −
                                  </button>
                                  <button
                                    type="button"
                                    className="btn"
                                    onClick={() => setFishingEnhanceLevel(def.id, 1)}
                                    aria-label="Increase level"
                                  >
                                    +
                                  </button>
                                </div>
                              </>
                            )}
                          </td>
                          <td className="fishingUpgradeTdCostEffic">
                            {!isMaxed &&
                            marginalPct != null &&
                            marginalPct >= 0 &&
                            nextCostEntry &&
                            nextCostEntry.gems > 0 &&
                            (state.useGemIncomeForCostEffic ? gemEvGemsPerHour > 0 : true)
                              ? (() => {
                                  const costEffic = state.useGemIncomeForCostEffic
                                    ? marginalPct / (nextCostEntry.gems / gemEvGemsPerHour)
                                    : (marginalPct / nextCostEntry.gems) * 100;
                                  const excludeFromHeatmap = def.id === "enhance_token_multiplier" || def.id === "enhance_tiny_notice_chance";
                                  const { min: heatMin, max: heatMax } = state.useGemIncomeForCostEffic
                                    ? { min: costEfficHeatMinGlobal, max: costEfficHeatMaxGlobal }
                                    : { min: costEfficHeatMinGemAbsGlobal, max: costEfficHeatMaxGemAbsGlobal };
                                  const heatT = !excludeFromHeatmap && heatMax > heatMin ? (costEffic - heatMin) / (heatMax - heatMin) : 0.5;
                                  const rateColor = excludeFromHeatmap ? "transparent" : heatmapColor(heatT);
                                  return (
                                    <span
                                      style={
                                        excludeFromHeatmap
                                          ? undefined
                                          : {
                                              backgroundColor: rateColor,
                                              color: heatT > 0.5 ? "#0a0a0a" : "#fff",
                                              padding: "2px 6px",
                                              borderRadius: 4,
                                            }
                                      }
                                    >
                                      {costEffic.toFixed(2)}
                                    </span>
                                  );
                                })()
                              : "—"}
                          </td>
                          <td className="fishingUpgradeTdCost">
                            {isMaxed ? (
                              <span className="fishingUpgradeMaxed">Maxed</span>
                            ) : nextCostEntry ? (
                              <span className="fishingUpgradeCostBox">
                                <img src={GEM_ICON_URL} alt="" className="fishingUpgradeCostFishIcon" />
                                <span className="mono">{formatCostCompact(nextCostEntry.gems)}</span>
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="fishingUpgradeTdTime">
                            {!isMaxed && nextCostEntry && nextCostEntry.gems > 0 && gemEvGemsPerHour > 0
                              ? formatHoursToHhMin(nextCostEntry.gems / gemEvGemsPerHour)
                              : "—"}
                          </td>
                          <td className="fishingUpgradeTdSpeed">
                            {marginalPct != null
                              ? marginalPct >= 0
                                ? `+${marginalPct.toFixed(1)}%`
                                : `${marginalPct.toFixed(1)}%`
                              : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Collapsible>
          </div>
        </Collapsible>

        <Collapsible id="fishing-fish-cards" title="Fish Cards" defaultExpanded={false}>
          <Collapsible id="fishing-fish-card-gild-effic" title="How much do fish gains improve when I gild my cards?" defaultExpanded={true} className="fishingFishCardGildEffic">
            <div className="small" style={{ marginBottom: 8 }}>
              Cost efficiency = marginal % per hour to earn gem cost (uses Gem EV Calculator total). Fish cards: Card → Gilded (gems). Fishing Rod Power: Card → Poly, 1500 gems. Open Gem EV to sync.
              <div style={{ marginTop: 6 }}>Fishing Rod: upgrading from Gilded to Poly is trivial, so the jump is calculated directly to Poly.</div>
            </div>
            <div className="fishingUpgradesList">
              <table className="fishingUpgradeTable">
                <thead>
                  <tr>
                    <th className="fishingUpgradeThName">Fish Card</th>
                    <th className="fishingUpgradeThCostEffic">
                      Cost Effic.
                      <Tooltip content={costEfficFishCardTooltip} />
                    </th>
                    <th className="fishingUpgradeThCost"><img src={GEM_ICON_URL} alt="" className="fishingUpgradeCostFishIcon" /></th>
                    <th className="fishingUpgradeThTime">
                      Time to next
                      <Tooltip
                        content={{
                          title: "Time to next",
                          lines: [
                            "Hours to earn the gem cost at your Gem EV rate. Open Gem EV to sync.",
                          ],
                        }}
                      />
                    </th>
                    <th className="fishingUpgradeThSpeed">+% gains</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ...fishingGainsRows
                      .filter((r) => (state.fishCardTier[r.fish.id] ?? 0) === 1 && !LEGENDARY_FISH.some((leg) => leg.id === r.fish.id))
                      .map((row) => ({
                        type: "fish" as const,
                        id: `${row.dockId}-${row.fish.id}`,
                        effic:
                          row.hasPower && row.fishPerHour > 0
                            ? (state.useGemIncomeForCostEffic ? fishCardGildCostEffic.get(row.fish.id) : fishCardGildCostEfficGemAbs.get(row.fish.id)) ?? 0
                            : -1,
                        row,
                      })),
                    ...((state.useGemIncomeForCostEffic ? fishingRodCardGildCostEffic : fishingRodCardGildCostEfficGemAbs) != null
                      ? [{ type: "rod" as const, id: "fishing_rod_power", effic: (state.useGemIncomeForCostEffic ? fishingRodCardGildCostEffic : fishingRodCardGildCostEfficGemAbs)! }]
                      : []),
                    ...((state.mrNibblesCardTier ?? 0) >= 1 && (state.mrNibblesCardTier ?? 0) < 2
                      ? [{ type: "mrNibbles" as const, id: "mr_nibbles_card", effic: -1 }]
                      : []),
                  ]
                    .sort((a, b) => b.effic - a.effic)
                    .map((entry) => {
                      if (entry.type === "fish") {
                        const row = entry.row!;
                        const canCalculate = row.hasPower && row.fishPerHour > 0;
                        const marginalPct = fishCardGildMarginalPct.get(row.fish.id) ?? 0;
                        const costEffic = state.useGemIncomeForCostEffic ? fishCardGildCostEffic.get(row.fish.id) ?? null : fishCardGildCostEfficGemAbs.get(row.fish.id) ?? null;
                        const gems = getFishCardGildGemCost(row.fish.id);
                        const { min: heatMin, max: heatMax } = state.useGemIncomeForCostEffic
                          ? { min: costEfficHeatMinGlobal, max: costEfficHeatMaxGlobal }
                          : { min: costEfficHeatMinGemAbsGlobal, max: costEfficHeatMaxGemAbsGlobal };
                        const heatT =
                          costEffic != null && heatMax > heatMin
                            ? (costEffic - heatMin) / (heatMax - heatMin)
                            : 0.5;
                        return (
                          <tr key={entry.id} className="fishingUpgradeRow">
                            <td className="fishingUpgradeTdName">
                              <img src={fishIconUrl(row.fish.iconFile ?? "Gem.png")} alt="" className="fishingUpgradeIcon" />
                              <span className="fishingUpgradeName">{row.fish.name}</span>
                            </td>
                            {canCalculate ? (
                              <>
                                <td className="fishingUpgradeTdCostEffic">
                                  {costEffic != null ? (
                                    <span
                                      style={{
                                        backgroundColor: heatmapColor(heatT),
                                        color: heatT > 0.5 ? "#0a0a0a" : "#fff",
                                        padding: "2px 6px",
                                        borderRadius: 4,
                                      }}
                                    >
                                      {costEffic.toFixed(2)}
                                    </span>
                                  ) : (
                                    "—"
                                  )}
                                </td>
                                <td className="fishingUpgradeTdCost">
                                  <span className="fishingUpgradeCostBox">
                                    <img src={GEM_ICON_URL} alt="" className="fishingUpgradeCostFishIcon" />
                                    <span className="mono">{formatCostCompact(gems)}</span>
                                  </span>
                                </td>
                                <td className="fishingUpgradeTdTime">
                                  {gems > 0 && gemEvGemsPerHour > 0 ? formatHoursToHhMin(gems / gemEvGemsPerHour) : "—"}
                                </td>
                                <td className="fishingUpgradeTdSpeed">+{marginalPct.toFixed(1)}%</td>
                              </>
                            ) : (
                              <td colSpan={4} className="fishingUpgradeTdCostEffic" style={{ color: "var(--error, #b91c1c)", fontWeight: 500 }}>
                                Only calculated when power on {row.dockName}.
                              </td>
                            )}
                          </tr>
                        );
                      }
                      if (entry.type === "mrNibbles") {
                        const marginalPctMr = mrNibblesCardNextMarginalPct ?? 0;
                        return (
                          <tr key="mr_nibbles_card" className="fishingUpgradeRow">
                            <td className="fishingUpgradeTdName">
                              <img src="https://static.wikitide.net/shminerwiki/thumb/2/22/Mr_Nibbles_Default.png/36px-Mr_Nibbles_Default.png" alt="" className="fishingUpgradeIcon" />
                              <span className="fishingUpgradeName">Mr Nibbles Card</span>
                              <Tooltip
                                content={{
                                  title: "Mr Nibbles Card",
                                  sections: [
                                    {
                                      heading: "Indirect gains",
                                      lines: [
                                        "Tiny Notice Chance (flat). Card +1%, Gilded +2%, Poly +4%.",
                                        "Effective +% is the assumed gain from the Notice mechanic (Tiny = 10×). Not included in cost efficiency heatmap.",
                                      ],
                                    },
                                  ],
                                }}
                                label="?"
                              />
                            </td>
                            <td className="fishingUpgradeTdCostEffic">—</td>
                            <td className="fishingUpgradeTdCost">—</td>
                            <td className="fishingUpgradeTdTime">—</td>
                            <td className="fishingUpgradeTdSpeed">
                              {mrNibblesCardNextMarginalPct != null ? (
                                <span title="Tiny Notice: effective assumed gain">+{marginalPctMr.toFixed(1)}% (notice)</span>
                              ) : (
                                "—"
                              )}
                            </td>
                          </tr>
                        );
                      }
                      const costEffic = (state.useGemIncomeForCostEffic ? fishingRodCardGildCostEffic : fishingRodCardGildCostEfficGemAbs)!;
                      const marginalPct = fishingRodCardGildMarginalPct ?? 0;
                      const { min: heatMin, max: heatMax } = state.useGemIncomeForCostEffic
                        ? { min: costEfficHeatMinGlobal, max: costEfficHeatMaxGlobal }
                        : { min: costEfficHeatMinGemAbsGlobal, max: costEfficHeatMaxGemAbsGlobal };
                      const heatT =
                        heatMax > heatMin
                          ? (costEffic - heatMin) / (heatMax - heatMin)
                          : 0.5;
                      return (
                        <tr key="fishing_rod_power" className="fishingUpgradeRow">
                          <td className="fishingUpgradeTdName">
                            <img src={upgradeIconUrl("Fishing_Rod_Power.png")} alt="" className="fishingUpgradeIcon" />
                            <span className="fishingUpgradeName">Fishing Rod Power</span>
                          </td>
                          <td className="fishingUpgradeTdCostEffic">
                            <span
                              style={{
                                backgroundColor: heatmapColor(heatT),
                                color: heatT > 0.5 ? "#0a0a0a" : "#fff",
                                padding: "2px 6px",
                                borderRadius: 4,
                              }}
                            >
                              {costEffic.toFixed(2)}
                            </span>
                          </td>
                          <td className="fishingUpgradeTdCost">
                            <span className="fishingUpgradeCostBox">
                              <img src={GEM_ICON_URL} alt="" className="fishingUpgradeCostFishIcon" />
                              <span className="mono">{formatCostCompact(FISHING_ROD_GILD_CARD_COST)}</span>
                            </span>
                          </td>
                          <td className="fishingUpgradeTdTime">
                            {gemEvGemsPerHour > 0 ? formatHoursToHhMin(FISHING_ROD_GILD_CARD_COST / gemEvGemsPerHour) : "—"}
                          </td>
                          <td className="fishingUpgradeTdSpeed">+{marginalPct.toFixed(1)}%</td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
            {!hasUngildedFishCard && !hasUngildedRodCard && (state.useGemIncomeForCostEffic ? fishingRodCardGildCostEffic : fishingRodCardGildCostEfficGemAbs) == null && ((state.mrNibblesCardTier ?? 0) === 0 || (state.mrNibblesCardTier ?? 0) >= 3) ? (
              <div className="small" style={{ padding: 8, opacity: 0.85 }}>You currently have no un-gilded Fish cards and no un-gilded Fishing Rod Power Card.</div>
            ) : null}
          </Collapsible>
          <div className="fishingFishCardsPanel">
            <div className="fishingFishCardsGrid" style={{ marginBottom: 10 }}>
              <div className="fishingFishCardCell">
                <div className="fishingFishCardCellTop">
                  <img src={upgradeIconUrl("Fishing_Rod_Power.png")} alt="" className="fishingFishCardIcon" />
                  <span className="mono">Fishing Rod Power</span>
                  <Tooltip
                    content={{
                      title: "Fishing Rod card",
                      lines: ["Multiplies your Fishing Rod Power. Card 1.02×, Gilded 1.05×, Poly 1.10×."],
                    }}
                  />
                </div>
                <FishCardTierToggles
                  value={state.fishingRodCardTier}
                  onChange={(t) => setState((prev) => ({ ...prev, fishingRodCardTier: t }))}
                />
                <div className="small" style={{ marginTop: 4, opacity: 0.85 }}>Card 1.02× · Gilded 1.05× · Poly 1.10×</div>
              </div>
              <div className="fishingFishCardCell">
                <div className="fishingFishCardCellTop">
                  <img src="https://static.wikitide.net/shminerwiki/thumb/2/22/Mr_Nibbles_Default.png/36px-Mr_Nibbles_Default.png" alt="" className="fishingFishCardIcon" />
                  <span className="mono">Mr Nibbles</span>
                  <Tooltip
                    content={{
                      title: "Mr Nibbles Card",
                      lines: ["Tiny Notice Chance (flat). Card +1%, Gilded +2%, Poly +4%."],
                    }}
                  />
                </div>
                <FishCardTierToggles
                  value={state.mrNibblesCardTier}
                  onChange={(t) => setState((prev) => ({ ...prev, mrNibblesCardTier: t }))}
                />
                <div className="small" style={{ marginTop: 4, opacity: 0.85 }}>Card +1% · Gilded +2% · Poly +4% Tiny Notice</div>
              </div>
            </div>
            <div className="fishingFishCardsGrid">
              {availableFish.map((f) => {
                const tier = (state.fishCardTier[f.id] ?? 0) as FishCardTier;
                return (
                  <div key={f.id} className="fishingFishCardCell">
                    <div className="fishingFishCardCellTop">
                      <img src={fishIconUrl(f.iconFile)} alt="" className="fishingFishCardIcon" />
                      <span className="mono">{f.name}</span>
                    </div>
                    <FishCardTierToggles
                      value={tier}
                      onChange={(t) => setState((prev) => ({ ...prev, fishCardTier: { ...prev.fishCardTier, [f.id]: t } }))}
                    />
                  </div>
                );
              })}
            </div>
            <Collapsible id="fishing-legendary-fish-cards" title="Legendary Fish Cards" defaultExpanded={false}>
              <div className="small" style={{ marginBottom: 6, opacity: 0.85 }}>
                Count for With This Fish I Summon (Fish Multi +1% per card per level, Shiny +0.1% per card per level). Card / Gilded / Poly same as regular fish cards.
              </div>
              <div className="fishingFishCardsGrid">
                {LEGENDARY_FISH.map((leg) => {
                  const tier = (state.fishCardTier[leg.id] ?? 0) as FishCardTier;
                  const effects = LEGENDARY_FISH_CARD_EFFECTS[leg.id];
                  return (
                    <div key={leg.id} className="fishingFishCardCell">
                      <div className="fishingFishCardCellTop">
                        <img src={leg.iconUrl} alt="" className="fishingFishCardIcon fishingFishCardIconLegendary" />
                        <span className="mono">{leg.name}</span>
                        {effects ? (
                          <Tooltip
                            content={{
                              title: effects.title,
                              sections: [
                                { heading: "Standard", lines: [effects.standard] },
                                { heading: "Gilded", lines: [effects.gilded] },
                                { heading: "Polychrome", lines: [effects.polychrome] },
                              ],
                            }}
                            label="?"
                          />
                        ) : null}
                      </div>
                      <FishCardTierToggles
                        value={tier}
                        onChange={(t) => setState((prev) => ({ ...prev, fishCardTier: { ...prev.fishCardTier, [leg.id]: t } }))}
                      />
                    </div>
                  );
                })}
              </div>
            </Collapsible>
            <div className="small" style={{ marginTop: 6, opacity: 0.85 }}>
              Card: 50% second fish (1.5×). Gilded: 100% second fish (2×). Poly: 4× base. Poly multi from upgrades and Polychrome Potency Bundle applies on top.
            </div>
          </div>
        </Collapsible>

        <Collapsible id="fishing-skill-tree" title="Skill Tree" defaultExpanded={false}>
          <div className="small" style={{ marginBottom: 8 }}>
            Skills cost skill points (from Obelisk level). 1 skill point = 125 gems. Cost efficiency = marginal % per hour to earn gem cost (uses Gem EV Calculator). Open Gem EV to sync.
          </div>
          <div className="fishingUpgradesList">
            <table className="fishingUpgradeTable">
              <thead>
                <tr>
                  <th className="fishingUpgradeThName">Skill</th>
                  <th className="fishingUpgradeThLvl">Lvl</th>
                  <th className="fishingUpgradeThCostEffic">
                    Cost Effic.
                    <Tooltip content={costEfficSkillTooltip} />
                  </th>
                  <th className="fishingUpgradeThCost">Cost (next)</th>
                  <th className="fishingUpgradeThSpeed">+% gains</th>
                </tr>
              </thead>
              <tbody>
                {FISHING_SKILL_TREE.map((def) => {
                  const maxLvl = def.costs.length;
                  const lvl = Math.max(0, Math.min(maxLvl, state.skillTreeLevels[def.id] ?? 0));
                  const nextCost = lvl < maxLvl ? (def.costs[lvl] ?? 0) : null;
                  const isMaxed = lvl >= maxLvl;
                  const marginalPct = skillMarginalPct.get(def.id) ?? null;
                  const gemsForNext = nextCost != null ? nextCost * GEMS_PER_SKILL_POINT : 0;
                  const costEffic =
                    !isMaxed &&
                    marginalPct != null &&
                    marginalPct >= 0 &&
                    gemsForNext > 0 &&
                    (state.useGemIncomeForCostEffic ? gemEvGemsPerHour > 0 : true)
                      ? state.useGemIncomeForCostEffic
                        ? marginalPct / (gemsForNext / gemEvGemsPerHour)
                        : (marginalPct / gemsForNext) * 100
                      : null;
                  const { min: heatMin, max: heatMax } = state.useGemIncomeForCostEffic
                    ? { min: costEfficHeatMinGlobal, max: costEfficHeatMaxGlobal }
                    : { min: costEfficHeatMinGemAbsGlobal, max: costEfficHeatMaxGemAbsGlobal };
                  const heatT =
                    costEffic != null && heatMax > heatMin
                      ? (costEffic - heatMin) / (heatMax - heatMin)
                      : 0.5;
                  const isFriendshipEnded = def.id === "friendship_ended_tier1";
                  return (
                    <tr
                      key={def.id}
                      className={
                        "fishingUpgradeRow" +
                        (isFriendshipEnded ? " fishingSkillRowNoticeFarming" : "") +
                        (isMaxed ? " fishingUpgradeRowMaxed" : "")
                      }
                    >
                      <td className="fishingUpgradeTdName">
                        {isMaxed ? (
                          <span className="fishingUpgradeName fishingUpgradeNameMaxed">{def.name}</span>
                        ) : (
                          <>
                            <img src={fishIconUrl(def.iconFile)} alt="" className="fishingUpgradeIcon" />
                            <div className="fishingUpgradeNameBlock">
                              <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                                <span className="fishingUpgradeName">{def.name}</span>
                                {isFriendshipEnded ? (
                                  <Tooltip
                                    content={{
                                      title: "Notice farming",
                                      sections: [
                                        {
                                          heading: "Indirect gains",
                                          lines: [
                                            "Notice Fish Req -10% means you need 10% less fish per notice.",
                                            "Notice Fish Req -10% per level (additive; 3 levels = -30% → 0.70x). First level: 1→0.9 ≈ +11.1% effective gains when notice farming.",
                                            "Fish/h does not change; the gain is in completing notices faster.",
                                            "Cost efficiency value is shown but excluded from the heatmap (indirect gain).",
                                          ],
                                        },
                                      ],
                                    }}
                                    label="?"
                                  />
                                ) : null}
                              </span>
                              <div className="small" style={{ marginTop: 2, opacity: 0.9 }}>
                                {def.effectLines.map((line, i) => (
                                  <div key={i}>{line}</div>
                                ))}
                              </div>
                            </div>
                          </>
                        )}
                      </td>
                      <td className="fishingUpgradeTdLvl">
                        {isMaxed ? (
                          <div className="fishingUpgradeLvlMaxedRow">
                            <span className="fishingUpgradeLevelLabel">
                              <span className="mono">{lvl}</span> / {maxLvl}
                            </span>
                            <button
                              type="button"
                              className="btn btnSecondary fishingUpgradeBtnMaxed"
                              onClick={() => setSkillTreeLevel(def.id, -1)}
                              aria-label="Decrease level"
                            >
                              −
                            </button>
                          </div>
                        ) : (
                          <>
                            <span className="fishingUpgradeLevelLabel">
                              <span className="mono">{lvl}</span> / {maxLvl}
                            </span>
                            <div className="btnRow fishingUpgradeButtons">
                              <button
                                type="button"
                                className="btn btnSecondary"
                                onClick={() => setSkillTreeLevel(def.id, -1)}
                                disabled={lvl <= 0}
                                aria-label="Decrease level"
                              >
                                −
                              </button>
                              {!isMaxed ? (
                                <button
                                  type="button"
                                  className="btn"
                                  onClick={() => setSkillTreeLevel(def.id, 1)}
                                  aria-label="Increase level"
                                >
                                  +
                                </button>
                              ) : null}
                            </div>
                            {def.id === "with_this_fish_i_summon_two_more_fish" ? (
                              <div className="small" style={{ marginTop: 4, opacity: 0.9 }}>
                                Your Cards:{" "}
                                <span className="mono">
                                  {Object.values(state.fishCardTier ?? {}).reduce<number>(
                                    (sum, t) => sum + (t === 1 ? 1 : t === 2 ? 2 : t === 3 ? 3 : 0),
                                    0,
                                  )}
                                </span>
                              </div>
                            ) : null}
                          </>
                        )}
                      </td>
                      <td className="fishingUpgradeTdCostEffic">
                        {costEffic != null ? (
                          (() => {
                            const breakdown = skillMarginalBreakdown.get(def.id);
                            const totalPct = breakdown?.reduce((s, b) => s + b.pct, 0) ?? 0;
                            const hasBreakdown = (breakdown?.length ?? 0) > 0 && totalPct > 0;
                            const excludeFromHeatmap = isFriendshipEnded;
                            const heatTExcl = excludeFromHeatmap ? 0.5 : heatT;
                            return (
                              <span className="fishingCostEfficWrap">
                                {hasBreakdown ? (
                                  <div className="fishingCostEfficPop">
                                    <div className="fishingCostEfficPopTitle">Share of marginal gain (sum 100%)</div>
                                    {breakdown!.map((b, i) => (
                                      <span key={i} className="fishingCostEfficPopLine">
                                        {b.label}: {totalPct > 0 ? ((b.pct / totalPct) * 100).toFixed(1) : "0"}%
                                      </span>
                                    ))}
                                  </div>
                                ) : null}
                                <span
                                  style={
                                    excludeFromHeatmap
                                      ? undefined
                                      : {
                                          backgroundColor: heatmapColor(heatTExcl),
                                          color: heatTExcl > 0.5 ? "#0a0a0a" : "#fff",
                                          padding: "2px 6px",
                                          borderRadius: 4,
                                        }
                                  }
                                >
                                  {costEffic.toFixed(2)}
                                </span>
                              </span>
                            );
                          })()
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="fishingUpgradeTdCost">
                        {isMaxed ? (
                          <span className="fishingUpgradeMaxed">Maxed</span>
                        ) : nextCost != null ? (
                          <span className="fishingUpgradeCostBox" style={{ flexDirection: "column", alignItems: "flex-start", gap: 2 }}>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                              <img src={SKILL_POINT_ICON_URL} alt="" className="fishingUpgradeCostFishIcon" />
                              <span className="mono">{formatCostCompact(nextCost)}</span>
                            </span>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--muted, #64748b)" }}>
                              = <img src={GEM_ICON_URL} alt="" className="fishingUpgradeCostFishIcon" />
                              <span className="mono">{formatCostCompact(nextCost * GEMS_PER_SKILL_POINT)}</span> gems
                            </span>
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="fishingUpgradeTdSpeed">
                        {marginalPct != null ? (
                          <span title={isFriendshipEnded ? "Notice farming: effective +11.1% per level" : undefined}>
                            {marginalPct >= 0 ? "+" : ""}{marginalPct.toFixed(1)}%{isFriendshipEnded ? " (notice)" : ""}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="fishingSkillOptions">
              <div className="fishingSkillOptionRow">
                <img src={SKILL_POINT_ICON_URL} alt="" style={{ width: 20, height: 20, objectFit: "contain", flexShrink: 0 }} />
                <span>Legendary Fish Found (0–11)</span>
                <div className="fishingSkillOptionStepper">
                  <span className="fishingUpgradeLevelLabel">
                    <span className="mono">{state.legendaryFishFound}</span> / 11
                  </span>
                  <div className="btnRow fishingUpgradeButtons">
                    <button type="button" className="btn btnSecondary" onClick={() => setState((p) => ({ ...p, legendaryFishFound: Math.max(0, p.legendaryFishFound - 1) }))} disabled={state.legendaryFishFound <= 0} aria-label="Decrease">−</button>
                    <button type="button" className="btn" onClick={() => setState((p) => ({ ...p, legendaryFishFound: Math.min(11, p.legendaryFishFound + 1) }))} disabled={state.legendaryFishFound >= 11} aria-label="Increase">+</button>
                  </div>
                </div>
              </div>
              <div className="small" style={{ marginTop: 0, marginBottom: 2, opacity: 0.85 }}>Used for Completionist Gatekeeper bonus.</div>
            </div>
          </div>
        </Collapsible>

        <Collapsible id="fishing-diverse-upgrades" title="Diverse Fishing Upgrades (Mid-Late Game)" defaultExpanded={false} className="fishingDiverseEndgame">
          <div className="fishingDiverseSection">
            <div className="fishingUpgradesBlock" style={{ marginTop: 0 }}>
              <div className="fishingBlockHeader">
                <span className="fishingBlockHeaderTitle">Pets</span>
              </div>
              <StepperRow
                label="Mr Nibbles"
                iconUrl="https://static.wikitide.net/shminerwiki/thumb/2/22/Mr_Nibbles_Default.png/36px-Mr_Nibbles_Default.png"
                value={state.mrNibblesLevel}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, mrNibblesLevel: Math.max(0, n) }))}
                tooltipContent={{
                  title: "Mr Nibbles",
                  sections: [
                    {
                      heading: "Effect",
                      lines: [
                        "Pets: per level — Shiny Fish Multi +0.03× (own multiplier), Triple Tick Chance +1% (flat).",
                      ],
                    },
                  ],
                }}
                effectText={
                  <>
                    → Shiny ×{(1 + 0.03 * state.mrNibblesLevel).toFixed(2)}; triple tick +{state.mrNibblesLevel}%
                    {mrNibblesPetNextLevelFishMarginalPct != null ? (
                      <span className="fishingStepperNextLevelHint">
                        next level up: +{mrNibblesPetNextLevelFishMarginalPct.toFixed(1)}% fish gains
                      </span>
                    ) : null}
                  </>
                }
                inputClassName="fishingStepperLevelInputWide"
              />
              <div className="fishingStepperRow">
                <div className="fishingStepperNameBlock">
                  <img src="https://static.wikitide.net/shminerwiki/thumb/f/fa/Mr_Nibbles_Quest.png/36px-Mr_Nibbles_Quest.png" alt="" className="fishingUpgradeIcon" aria-hidden />
                  <div className="fishingStepperLabelBlock">
                    <span className="fishingStepperRowLabel">Mr Nibbles Quest</span>
                    <Tooltip
                      content={{
                        title: "Mr Nibbles Quest",
                        sections: [
                          {
                            heading: "Effect",
                            lines: [
                              "Pets: when unlocked, Tier 2 Dock Power +5% at rank 0 (own multiplier); each rank adds +5%. Applies only on T2 docks (Cave, Volcano, Sky, Solaris, Galaxy).",
                            ],
                          },
                        ],
                      }}
                      label="?"
                    />
                  </div>
                </div>
                <div className="fishingStepperLvlBlock" style={{ gap: 8 }}>
                  <label className="fishingStepperCheckboxWrap" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <input
                      type="checkbox"
                      id="fishing-mr-nibbles-quest-unlocked"
                      className="fishingCheckbox"
                      checked={state.mrNibblesQuestUnlocked}
                      onChange={(e) => setState((prev) => ({ ...prev, mrNibblesQuestUnlocked: e.target.checked }))}
                    />
                    <span className="fishingUpgradeLevelLabel">on</span>
                  </label>
                  {state.mrNibblesQuestUnlocked && (
                    <InlineRankStepper
                      value={state.mrNibblesQuestRank}
                      min={0}
                      max={999}
                      onChange={(n) => setState((prev) => ({ ...prev, mrNibblesQuestRank: n }))}
                    />
                  )}
                </div>
                {state.mrNibblesQuestUnlocked ? (
                  <span className="mono fishingStepperEffect">
                    → T2 Dock Power ×{(1 + 0.05 * (state.mrNibblesQuestRank + 1)).toFixed(2)} (+{(state.mrNibblesQuestRank + 1) * 5}%)
                    {mrNibblesQuestNextRankFishMarginalPct != null ? (
                      <span className="fishingStepperNextLevelHint">
                        next level up: +{mrNibblesQuestNextRankFishMarginalPct.toFixed(1)}% fish gains
                      </span>
                    ) : null}
                  </span>
                ) : (
                  <span className="fishingStepperEffect" style={{ opacity: 0.6 }}>—</span>
                )}
              </div>
              <div className="fishingStepperRow">
                <div className="fishingStepperNameBlock">
                  <img src="https://static.wikitide.net/shminerwiki/thumb/e/eb/Mr_Nibbles_Skin.png/36px-Mr_Nibbles_Skin.png" alt="" className="fishingUpgradeIcon" aria-hidden />
                  <div className="fishingStepperLabelBlock">
                    <span className="fishingStepperRowLabel">Mr Nibbles Pet Skin</span>
                    <Tooltip
                      content={{
                        title: "Mr Nibbles Pet Skin",
                        sections: [
                          {
                            heading: "Effect",
                            lines: [
                              "Pets: +2% Shiny Fish Chance (flat).",
                            ],
                          },
                        ],
                      }}
                      label="?"
                    />
                  </div>
                </div>
                <div className="fishingStepperLvlBlock">
                  <label className="fishingStepperCheckboxWrap" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <input
                      type="checkbox"
                      id="fishing-mr-nibbles-skin"
                      className="fishingCheckbox"
                      checked={state.mrNibblesSkin}
                      onChange={(e) => setState((prev) => ({ ...prev, mrNibblesSkin: e.target.checked }))}
                    />
                    <span className="fishingUpgradeLevelLabel">on</span>
                  </label>
                </div>
                <span className="mono fishingStepperEffect">{state.mrNibblesSkin ? "→ +2% Shiny Fish Chance" : "—"}</span>
              </div>
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <img src={CARDS_ICON_URL} alt="" className="fishingBlockHeaderIcon" aria-hidden />
                <span className="fishingBlockHeaderTitle">Cards</span>
              </div>
              <div className="fishingInfernalRow">
                <div className="fishingStepperNameBlock">
                  <span className="fishingStepperRowLabel">Infernal Mr Nibbles</span>
                  <Tooltip
                    content={{
                      title: "Infernal Mr Nibbles",
                      sections: [
                        {
                          heading: "Effect",
                          lines: [
                            "Cards: each level gives +X% 5× Fish Tick Chance (flat). Enter X as the % per level and the card level.",
                          ],
                        },
                      ],
                    }}
                    label="?"
                  />
                </div>
                <div className="fishingInfernalInputs">
                  <label className="fishingInfernalLabel">
                    % per level
                    <input
                      type="number"
                      inputMode="decimal"
                      min={0}
                      step={0.5}
                      className="input mono fishingInfernalInput"
                      value={state.infernalMrNibblesPct}
                      onChange={(e) => {
                        const v = Number(e.target.value.replace(",", "."));
                        if (!Number.isFinite(v)) return;
                        setState((prev) => ({ ...prev, infernalMrNibblesPct: Math.max(0, v) }));
                      }}
                      aria-label="Infernal Mr Nibbles % per level"
                    />
                  </label>
                  <label className="fishingInfernalLabel">
                    level
                    <input
                      type="number"
                      inputMode="numeric"
                      min={0}
                      step={1}
                      className="input mono fishingInfernalInput"
                      value={state.infernalMrNibblesLevel}
                      onChange={(e) => {
                        const v = parseInt(e.target.value.replace(",", "."), 10);
                        if (!Number.isFinite(v)) return;
                        setState((prev) => ({ ...prev, infernalMrNibblesLevel: Math.max(0, v) }));
                      }}
                      aria-label="Infernal Mr Nibbles level"
                    />
                  </label>
                </div>
                <span className="mono fishingStepperEffect">
                  → +{(state.infernalMrNibblesPct * state.infernalMrNibblesLevel).toFixed(1)}% 5× tick chance (flat)
                </span>
              </div>
              <div className="fishingInfernalRow">
                <div className="fishingStepperNameBlock">
                  <span className="fishingStepperRowLabel">Infernal Angler Drone Card</span>
                  <Tooltip
                    content={{
                      title: "Infernal Angler Drone Card",
                      sections: [
                        {
                          heading: "Effect",
                          lines: [
                            "Cards: each level gives +X% Tier 2 Dock Power. Enter X as the % per level and the card level.",
                          ],
                        },
                      ],
                    }}
                    label="?"
                  />
                </div>
                <div className="fishingInfernalInputs">
                  <label className="fishingInfernalLabel">
                    % per level
                    <input
                      type="number"
                      inputMode="decimal"
                      min={0}
                      step={0.5}
                      className="input mono fishingInfernalInput"
                      value={state.infernalAnglerDronePct}
                      onChange={(e) => {
                        const v = Number(e.target.value.replace(",", "."));
                        if (!Number.isFinite(v)) return;
                        setState((prev) => ({ ...prev, infernalAnglerDronePct: Math.max(0, v) }));
                      }}
                      aria-label="Infernal Angler Drone % per level"
                    />
                  </label>
                  <label className="fishingInfernalLabel">
                    level
                    <input
                      type="number"
                      inputMode="numeric"
                      min={0}
                      step={1}
                      className="input mono fishingInfernalInput"
                      value={state.infernalAnglerDroneLevel}
                      onChange={(e) => {
                        const v = parseInt(e.target.value.replace(",", "."), 10);
                        if (!Number.isFinite(v)) return;
                        setState((prev) => ({ ...prev, infernalAnglerDroneLevel: Math.max(0, v) }));
                      }}
                      aria-label="Infernal Angler Drone level"
                    />
                  </label>
                </div>
                <span className="mono fishingStepperEffect">
                  → T2 Dock Power +{(state.infernalAnglerDronePct * state.infernalAnglerDroneLevel).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <span className="fishingBlockHeaderTitle">Archaeology</span>
              </div>
              <StepperRow
                label="Poseidon Idol"
                iconUrl="https://static.wikitide.net/shminerwiki/6/63/Poseidon_Idol.png"
                value={state.poseidonIdolLevel}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, poseidonIdolLevel: Math.max(0, n) }))}
                effectText={`→ +${(state.poseidonIdolLevel * 0.25).toFixed(2)} base drone power`}
                inputClassName="fishingStepperLevelInputWide"
                tooltipContent={{
                  title: "Poseidon Idol",
                  sections: [
                    {
                      heading: "Effect",
                      lines: [
                        "Archaeology: +0.25 base drone power per level. Applies to all docks (adds to rod power on the dock you fish at).",
                      ],
                    },
                    {
                      heading: "+1 level (effective fish gain)",
                      lines: [
                        poseidonIdolMarginalFishPct != null
                          ? `About +${Math.abs(poseidonIdolMarginalFishPct) < 0.01 ? poseidonIdolMarginalFishPct.toFixed(4) : Math.abs(poseidonIdolMarginalFishPct) < 0.1 ? poseidonIdolMarginalFishPct.toFixed(3) : poseidonIdolMarginalFishPct.toFixed(2)}% total fish/h at your current build.`
                          : "No active docks with fish gain; +% cannot be computed.",
                      ],
                    },
                  ],
                }}
              />
              <StepperRow
                label="Astraeus Idol"
                iconUrl="https://static.wikitide.net/shminerwiki/1/1c/Astraeus_Idol.png"
                value={state.astraeusIdolLevel}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, astraeusIdolLevel: Math.max(0, n) }))}
                tooltipContent={{
                  title: "Astraeus Idol",
                  sections: [
                    {
                      heading: "Effect",
                      lines: [
                        "Archaeology: +0.03% Fishing double tick chance per level (flat, added on top of existing double tick chance).",
                      ],
                    },
                    {
                      heading: "+1 level (effective fish gain)",
                      lines: [
                        astraeusIdolMarginalFishPct != null
                          ? `About +${Math.abs(astraeusIdolMarginalFishPct) < 0.01 ? astraeusIdolMarginalFishPct.toFixed(4) : Math.abs(astraeusIdolMarginalFishPct) < 0.1 ? astraeusIdolMarginalFishPct.toFixed(3) : astraeusIdolMarginalFishPct.toFixed(2)}% total fish/h at your current build.`
                          : "No active docks with fish gain; +% cannot be computed.",
                      ],
                    },
                  ],
                }}
                effectText={`→ +${(state.astraeusIdolLevel * 0.03).toFixed(2)}% double tick chance`}
                inputClassName="fishingStepperLevelInputWide"
              />
                            <StepperRow
                label="Tethys Idol"
                iconUrl="https://static.wikitide.net/shminerwiki/a/a4/Tethys_Idol.png"
                value={state.tethysIdolLevel}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, tethysIdolLevel: Math.max(0, n) }))}
                inputClassName="fishingStepperLevelInputWide"
                tooltipContent={{
                  title: "Tethys Idol",
                  sections: [
                    {
                      heading: "Effect",
                      lines: [
                        "Each point: Tier 2 dock power +0.05% (T2 docks only), Drone power multi +0.05%, Super shiny multi +0.05%.",
                        "Drone and super shiny multis apply to all docks. Tier 2 dock power applies only on T2 docks (Cave, Volcano, Sky, Solaris, Galaxy).",
                      ],
                    },
                    {
                      heading: "+1 level (effective fish gain)",
                      lines: [
                        tethysIdolMarginalFishPct != null
                          ? `About +${Math.abs(tethysIdolMarginalFishPct) < 0.01 ? tethysIdolMarginalFishPct.toFixed(4) : Math.abs(tethysIdolMarginalFishPct) < 0.1 ? tethysIdolMarginalFishPct.toFixed(3) : tethysIdolMarginalFishPct.toFixed(2)}% total fish/h at your current build.`
                          : "No active docks with fish gain; +% cannot be computed.",
                      ],
                    },
                  ],
                }}
                effectText={
                  <>
                    → T2 Dock power +{(state.tethysIdolLevel * 0.05).toFixed(2)}%;
                    <br />
                    drone & super shiny +{(state.tethysIdolLevel * 0.05).toFixed(2)}% 
                  </>
                }
              />
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <span className="fishingBlockHeaderTitle">Relics</span>
              </div>
              <StepperRow
                label="Divine Relic (5× tick)"
                iconUrl={RELICS_ICON_URL}
                value={state.divineRelic5xPoints}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, divineRelic5xPoints: Math.max(0, n) }))}
                tooltipContent={{
                  title: "Divine Relic",
                  sections: [
                    {
                      heading: "Effect",
                      lines: [
                        "Each point gives +2% 5× tick chance. This is the base 5× chance that applies to all tick sources.",
                        "The Gift basic reward (+25% 5× chance) applies to Base, Angler, Lootbug ticks but not to Sushi.",
                        "Sushi uses only this base (relic) 5× chance.",
                      ],
                    },
                  ],
                }}
                effectText={`→ +${state.divineRelic5xPoints * 2}% 5× tick chance`}
                inputClassName="fishingStepperLevelInputWide"
              />
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <span className="fishingBlockHeaderTitle">Legendary Fish Tributes</span>
              </div>
              <div className="fishingStepperRow">
                <div className="fishingStepperNameBlock">
                  <img src="https://static.wikitide.net/shminerwiki/6/6f/Abyss_Legendary_Fish.png" alt="" className="fishingUpgradeIcon" aria-hidden />
                  <div className="fishingStepperLabelBlock">
                    <span className="fishingStepperRowLabel">Cthulhu</span>
                    <Tooltip
                      content={{
                        title: "Cthulhu Tribute 1",
                        lines: ["All Dock Tick Reqs -10%", "Super Shiny Multi +3x"],
                      }}
                      label="?"
                    />
                  </div>
                </div>
                <div className="fishingStepperLvlBlock">
                  <label className="fishingStepperCheckboxWrap" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <input
                      type="checkbox"
                      id="fishing-abyss-legendary-caught"
                      className="fishingCheckbox"
                      checked={state.abyssLegendaryCaught}
                      onChange={(e) => setState((prev) => ({ ...prev, abyssLegendaryCaught: e.target.checked }))}
                    />
                    <span className="fishingUpgradeLevelLabel">on</span>
                  </label>
                </div>
                <span className="mono fishingStepperEffect">{state.abyssLegendaryCaught ? "→ All Dock Tick Reqs -10%, Super Shiny Multi +3×" : "—"}</span>
              </div>
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <span className="fishingBlockHeaderTitle">Divine Challenge</span>
              </div>
              <StepperRow
                label=""
                iconUrl="https://static.wikitide.net/shminerwiki/thumb/a/ab/Divine_Challenge_Coin.png/24px-Divine_Challenge_Coin.png"
                value={state.divineChallengeCoinLevel}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, divineChallengeCoinLevel: Math.max(0, n) }))}
                tooltipContent={{
                  title: "Divine Challenge",
                  lines: ["Each level gives Shiny Fish Multiplier +10% (own multiplier)."],
                }}
                effectText={`→ Shiny ×${(1 + 0.1 * state.divineChallengeCoinLevel).toFixed(2)} (+${state.divineChallengeCoinLevel * 10}%)`}
                inputClassName="fishingStepperLevelInputWide"
              />
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <span className="fishingBlockHeaderTitle">Construct (W3)</span>
              </div>
              <div className="fishingCheckboxRow">
                <img
                  src="https://static.wikitide.net/shminerwiki/c/ce/10_Statue_Craftmanship_Gilded.png"
                  alt=""
                  className="fishingBlockIcon"
                  aria-hidden
                />
                <input
                  id="fishing-construct-gilded"
                  type="checkbox"
                  className="fishingCheckbox"
                  checked={state.constructStatue === "gilded"}
                  onChange={() =>
                    setState((prev) => ({
                      ...prev,
                      constructStatue: prev.constructStatue === "gilded" ? "none" : "gilded",
                    }))
                  }
                />
                <label htmlFor="fishing-construct-gilded" className="fishingBlockLabel">
                  Statue of Craftmanship Gilded — Fish Income ×1.25
                  {storeBundleMarginalPct.constructGilded != null && (
                    <span className="mono" style={{ marginLeft: 6 }}>(+{storeBundleMarginalPct.constructGilded.toFixed(1)}% gain)</span>
                  )}
                </label>
                <Tooltip
                  content={{
                    title: "Statue of Craftmanship Gilded",
                    lines: ["Construct: Fish Income Multi ×1.25 (own multiplier). Only one statue tier can be active."],
                  }}
                  label="?"
                />
              </div>
              <div className="fishingCheckboxRow">
                <img
                  src="https://static.wikitide.net/shminerwiki/a/ac/10_Statue_Craftmanship_Platinized.png"
                  alt=""
                  className="fishingBlockIcon"
                  aria-hidden
                />
                <input
                  id="fishing-construct-platinized"
                  type="checkbox"
                  className="fishingCheckbox"
                  checked={state.constructStatue === "platinized"}
                  onChange={() =>
                    setState((prev) => ({
                      ...prev,
                      constructStatue: prev.constructStatue === "platinized" ? "none" : "platinized",
                    }))
                  }
                />
                <label htmlFor="fishing-construct-platinized" className="fishingBlockLabel">
                  Statue of Craftmanship Platinized — Fish Income ×1.40
                  {storeBundleMarginalPct.constructPlatinized != null && (
                    <span className="mono" style={{ marginLeft: 6 }}>(+{storeBundleMarginalPct.constructPlatinized.toFixed(1)}% gain)</span>
                  )}
                </label>
                <Tooltip
                  content={{
                    title: "Statue of Craftmanship Platinized",
                    lines: ["Construct: Fish Income Multi ×1.40 (own multiplier). Only one statue tier can be active."],
                  }}
                  label="?"
                />
              </div>
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <span className="fishingBlockHeaderTitle">Stargazing</span>
              </div>
              <StepperRow
                label="Cetus"
                iconUrl="https://static.wikitide.net/shminerwiki/6/69/Cetus.png"
                value={state.cetusLevel}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, cetusLevel: Math.max(0, n) }))}
                tooltipContent={{
                  title: "Cetus",
                  sections: [
                    {
                      heading: "Effect",
                      lines: [
                        "Stargazing: +2% Fish Income per level (own multiplier).",
                        "Formula: Fish Income × (1 + 0.02 × level). Stacks with other fish income multis.",
                      ],
                    },
                  ],
                }}
                effectText={`→ Fish Income ×${(1 + 0.02 * state.cetusLevel).toFixed(2)} (+${state.cetusLevel * 2}%)`}
                inputClassName="fishingStepperLevelInputWide"
              />
              <StepperRow
                label="Fish Income Multiplier"
                iconUrl="https://static.wikitide.net/shminerwiki/7/78/Fish_Income_Multiplier.png"
                value={state.superStarsLevel}
                min={0}
                max={15}
                onChange={(n) => setState((prev) => ({ ...prev, superStarsLevel: Math.max(0, Math.min(15, n)) }))}
                tooltipContent={{
                  title: "Super Stars: Fish Income Multiplier",
                  lines: ["Each level gives Fish Income +1.25% (own multiplier)."],
                }}
                effectText={`→ Fish Income ×${(1 + 0.0125 * state.superStarsLevel).toFixed(4)} (+${(state.superStarsLevel * 1.25).toFixed(2)}%)`}
                inputClassName="fishingStepperLevelInputWide"
              />
              <div className="fishingCheckboxRow">
                <img
                  src="https://static.wikitide.net/shminerwiki/5/5f/Tier_2_Dock_Power.png"
                  alt=""
                  className="fishingBlockIcon"
                  aria-hidden
                />
                <input
                  id="fishing-stargazing-black-hole-bonus"
                  type="checkbox"
                  className="fishingCheckbox"
                  checked={state.blackHoleBonus}
                  onChange={(e) => setState((prev) => ({ ...prev, blackHoleBonus: e.target.checked }))}
                />
                <label htmlFor="fishing-stargazing-black-hole-bonus" className="fishingBlockLabel">
                  Black Hole Bonus
                  {storeBundleMarginalPct.blackHoleBonusPct != null && (
                    <span className="mono" style={{ marginLeft: 6 }}>(+{storeBundleMarginalPct.blackHoleBonusPct.toFixed(1)}% gain)</span>
                  )}
                </label>
                <Tooltip
                  content={{
                    title: "Black Hole Bonus",
                    lines: ["Stargazing: Tier 2 Dock Power +25% (own multiplier)."],
                  }}
                  label="?"
                />
              </div>
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <span className="fishingBlockHeaderTitle">Store</span>
              </div>
              <div className="fishingCheckboxRow">
                <img
                  src="https://static.wikitide.net/shminerwiki/thumb/0/04/Polychromepotency_vp.png/60px-Polychromepotency_vp.png"
                  alt=""
                  className="fishingBlockIcon"
                  aria-hidden
                />
                <input
                  id="fishing-store-polychrome-potency"
                  type="checkbox"
                  className="fishingCheckbox"
                  checked={state.valuePackPotencyPoly}
                  onChange={(e) => setState((prev) => ({ ...prev, valuePackPotencyPoly: e.target.checked }))}
                />
                <label htmlFor="fishing-store-polychrome-potency" className="fishingBlockLabel">
                  Polychrome Potency Bundle (fish poly ×1.15)
                  {storeBundleMarginalPct.polychrome != null && (
                    <span className="mono" style={{ marginLeft: 6 }}>(+{storeBundleMarginalPct.polychrome.toFixed(1)}% gain)</span>
                  )}
                </label>
              </div>
              <div className="fishingCheckboxRow">
                <img
                  src="https://static.wikitide.net/shminerwiki/thumb/1/1a/Legendaryhauler_vp.png/60px-Legendaryhauler_vp.png"
                  alt=""
                  className="fishingBlockIcon"
                  aria-hidden
                />
                <input
                  id="fishing-store-legendary-hauler"
                  type="checkbox"
                  className="fishingCheckbox"
                  checked={state.legendaryHaulerBundle}
                  onChange={(e) => setState((prev) => ({ ...prev, legendaryHaulerBundle: e.target.checked }))}
                />
                <label htmlFor="fishing-store-legendary-hauler" className="fishingBlockLabel">
                  Legendary Hauler Bundle
                  {storeBundleMarginalPct.legendaryHauler != null && (
                    <span className="mono" style={{ marginLeft: 6 }}>(+{storeBundleMarginalPct.legendaryHauler.toFixed(1)}% gain)</span>
                  )}
                </label>
                <Tooltip
                  content={{
                    title: "Legendary Hauler Bundle",
                    sections: [
                      {
                        heading: "Effect",
                        lines: [
                          "5× Fishing Tick Chance +3% (flat on top of existing 5× chance).",
                          "Fish Income Multi ×1.10 (own multiplier).",
                          "Tier 2 Dock Power ×1.10 (own multiplier).",
                        ],
                      },
                    ],
                  }}
                  label="?"
                />
              </div>
              <div className="fishingCheckboxRow">
                <img
                  src="https://static.wikitide.net/shminerwiki/thumb/d/d1/Halfway_vp.png/40px-Halfway_vp.png"
                  alt=""
                  className="fishingBlockIcon"
                  aria-hidden
                />
                <input
                  id="fishing-store-half-way-bundle"
                  type="checkbox"
                  className="fishingCheckbox"
                  checked={state.halfWayBundle}
                  onChange={(e) => setState((prev) => ({ ...prev, halfWayBundle: e.target.checked }))}
                />
                <label htmlFor="fishing-store-half-way-bundle" className="fishingBlockLabel">
                  Half Way Bundle!
                  {storeBundleMarginalPct.halfWayBundlePct != null && (
                    <span className="mono" style={{ marginLeft: 6 }}>(+{storeBundleMarginalPct.halfWayBundlePct.toFixed(1)}% gain)</span>
                  )}
                </label>
                <Tooltip
                  content={{
                    title: "Half Way Bundle!",
                    lines: ["Store: Fishing Rod Power ×1.10 (own multiplier, before Fishing Rod card)."],
                  }}
                  label="?"
                />
              </div>
              <div className="fishingCheckboxRow">
                <img
                  src="https://static.wikitide.net/shminerwiki/thumb/b/bf/Fishingbundle_vp.png/60px-Fishingbundle_vp.png"
                  alt=""
                  className="fishingBlockIcon"
                  aria-hidden
                />
                <input
                  id="fishing-store-fishers-bundle"
                  type="checkbox"
                  className="fishingCheckbox"
                  checked={state.fishersBundle}
                  onChange={(e) => setState((prev) => ({ ...prev, fishersBundle: e.target.checked }))}
                />
                <label htmlFor="fishing-store-fishers-bundle" className="fishingBlockLabel">
                  Fisher&apos;s Bundle
                  {storeBundleMarginalPct.fishers != null && (
                    <span className="mono" style={{ marginLeft: 6 }}>(+{storeBundleMarginalPct.fishers.toFixed(1)}% gain)</span>
                  )}
                </label>
                <Tooltip
                  content={{
                    title: "Fisher's Bundle",
                    sections: [
                      {
                        heading: "Effect",
                        lines: [
                          "+10% Triple Fishing Tick Chance (flat on top of existing 3× chance).",
                        ],
                      },
                    ],
                  }}
                  label="?"
                />
              </div>
              <div className="fishingCheckboxRow">
                <img
                  src="https://static.wikitide.net/shminerwiki/thumb/a/a4/Anglerbundle_vp.png/60px-Anglerbundle_vp.png"
                  alt=""
                  className="fishingBlockIcon"
                  aria-hidden
                />
                <input
                  id="fishing-store-angler-bundle"
                  type="checkbox"
                  className="fishingCheckbox"
                  checked={state.anglerBundle}
                  onChange={(e) => setState((prev) => ({ ...prev, anglerBundle: e.target.checked }))}
                />
                <label htmlFor="fishing-store-angler-bundle" className="fishingBlockLabel">
                  Angler&apos;s Bundle!
                  {storeBundleMarginalPct.angler != null && (
                    <span className="mono" style={{ marginLeft: 6 }}>(+{storeBundleMarginalPct.angler.toFixed(1)}% gain)</span>
                  )}
                </label>
                <Tooltip
                  content={{
                    title: "Angler's Bundle",
                    lines: ["Store: +6% Tiny Notice Chance (flat on top of existing)."],
                  }}
                  label="?"
                />
              </div>
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <span className="fishingBlockHeaderTitle">Workshop</span>
              </div>
              <StepperRow
                label="Fishing Drone Power (World 3)"
                iconUrl="https://static.wikitide.net/shminerwiki/f/f0/Drone_Power_Multiplier.png"
                value={state.fishingDroneBasePowerWorld3}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, fishingDroneBasePowerWorld3: Math.max(0, n) }))}
                effectText={`→ ×${(1 + state.fishingDroneBasePowerWorld3 * 0.02).toFixed(2)} Drone Power multi`}
                inputClassName="fishingStepperLevelInputWide"
              />
              <StepperRow
                label="Sushi Fishing Ticks (World 3)"
                iconUrl="https://static.wikitide.net/shminerwiki/6/6d/Sushi.png"
                value={state.workshopSushiTicksWorld3}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, workshopSushiTicksWorld3: Math.max(0, n) }))}
                effectText={`→ +${state.workshopSushiTicksWorld3} sushi ticks`}
                inputClassName="fishingStepperLevelInputWide"
              />
            </div>

            <div className="fishingUpgradesBlock" style={{ marginTop: 10 }}>
              <div className="fishingBlockHeader">
                <img src={FISHING_UPGRADES_ICON} alt="" className="fishingBlockHeaderIcon" aria-hidden />
                <span className="fishingBlockHeaderTitle">Upgrades</span>
              </div>
              <StepperRow
                label="Fishing Drone Power (World 3)"
                iconUrl="https://static.wikitide.net/shminerwiki/b/bc/Dynamite_Bar.png"
                value={state.droneBasePowerWorld3Upgrade}
                min={0}
                max={999}
                onChange={(n) => setState((prev) => ({ ...prev, droneBasePowerWorld3Upgrade: Math.max(0, n) }))}
                tooltipContent={{
                  title: "Fishing Drone Power (World 3)",
                  sections: [
                    {
                      heading: "Effect",
                      lines: [
                        "Diverse Upgrades: +0.1 base drone power per level. Adds to drone base before multipliers (same formula as main Drone Base Power upgrade).",
                        "Workshop has a separate World 3 upgrade: +0.02× multiplier per level.",
                      ],
                    },
                  ],
                }}
                effectText={`→ +${(state.droneBasePowerWorld3Upgrade * 0.1).toFixed(2)} base drone power`}
                inputClassName="fishingStepperLevelInputWide"
              />
            </div>
          </div>
        </Collapsible>
      </div>
    </div>
  );
}
