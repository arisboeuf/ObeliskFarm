// Ported (minimally) from ObeliskGemEV/event/constants.py

/** Labels match in-game Event Results (Upgrade column). Use \n for two-line upgrade names. */
export const UPGRADE_SHORT_NAMES: Record<number, string[]> = {
  1: [
    "+1 Attack Damage",
    "+2 Maximum Health",
    "+0.02 Attack Speed",
    "+0.03 Move Speed",
    "+3% Event Game Speed",
    "+1% Crit Chance\n+0.10 Crit Damage",
    "+1 Attack Damage\n+2 Maximum Health",
    "+1 Tier 1 Upgrade Caps",
    "+1% Prestige Bonus",
    "+3 Attack Damage\n+3 Maximum Health",
  ],
  2: [
    "+3 Maximum Health",
    "-0.02 Enemy Attack Speed",
    "-1 Enemy Attack Damage",
    "-1% Enemy Crit Chance\n-0.10 Enemy Crit Damage",
    "+1 Attack Damage\n+0.01 Attack Speed",
    "+1 Tier 2 Upgrade Caps",
    "+2% Prestige Bonus",
  ],
  3: [
    "+2 Attack Damage",
    "+0.02 Attack Speed",
    "+1% Crit Chance",
    "+5% Event Game Speed",
    "+3 Attack Damage\n+3 Maximum Health",
    "+1 Tier 3 Upgrade Caps",
    "+3% 5x Drop Chance",
    "+5 Maximum Health\n+0.03 Attack Speed",
  ],
  4: [
    "1% Block Chance",
    "+5 Maximum Health",
    "+0.10 Crit Damage\n-0.10 Enemy Crit Damage",
    "+0.02 Attack Speed\n+0.02 Move Speed",
    "+4 Maximum Health\n+4 Attack Damage",
    "+1 Tier 4 Upgrade Caps",
    "+1 Cap of Cap Upgrades",
    "+10 Maximum Health\n+0.05 Attack Speed",
  ],
};

export const PRESTIGE_UNLOCKED: Record<number, number[]> = {
  1: [0, 0, 0, 0, 1, 2, 2, 4, 8, 10],
  2: [0, 0, 0, 1, 3, 5, 10],
  3: [1, 1, 2, 3, 4, 6, 8, 10],
  4: [1, 1, 4, 5, 6, 6, 7, 10],
};

export const MAX_LEVELS: Record<number, number[]> = {
  1: [50, 50, 25, 25, 25, 25, 25, 10, 5, 40],
  2: [25, 15, 10, 15, 25, 10, 15],
  3: [20, 20, 20, 20, 10, 10, 10, 40],
  4: [15, 15, 15, 15, 15, 10, 10, 40],
};

// 1-indexed in original docs; stored as 1-indexed here to mirror Python constant usage.
export const CAP_UPGRADES: Record<number, number> = { 1: 8, 2: 6, 3: 6, 4: 6 };

export const COSTS: Record<number, number[]> = {
  1: [5, 6, 8, 10, 12, 20, 75, 2500, 25000, 5000],
  2: [5, 8, 12, 20, 40, 500, 650],
  3: [5, 8, 12, 18, 30, 250, 300, 125],
  4: [10, 12, 15, 20, 50, 250, 500, 150],
};

export const GEM_UPGRADE_NAMES = ["+10% Damage", "+10% Maximum Health", "+125% Event Game Speed", "2x Event Currencies"] as const;

export function getPrestigeWaveRequirement(prestige: number): number {
  return (prestige + 1) * 5;
}

/** Min/max bounds for user-specified target wave. */
export const TARGET_WAVE_MIN = 1;
export const TARGET_WAVE_MAX = 250;

/** Multiplier for required atk in target-wave mode (enemy HP at wave × this = requiredAtk). Slightly above 1 so MC runs reliably reach the target wave. */
export const TARGET_WAVE_ATK_BUFFER = 1.05;

/** Base prestige bonus scale (from stats). */
const PRESTIGE_BONUS_SCALE_BASE = 0.1;
/** Assumed max prestige bonus scale when capping raw atk (high prestige builds; 0.8 ~ 35× at prestige 43 so builds with 35×+ don't overshoot). */
const PRESTIGE_BONUS_SCALE_MAX = 0.8;

/** ATK multiplier from prestige + gem damage. levels: tier -> idx -> level (1-based tier). */
export function getPrestigeAtkMultiplier(
  levels: Record<number, number[]>,
  prestige: number,
  gemDamageLevel: number,
): number {
  const scale =
    PRESTIGE_BONUS_SCALE_BASE +
    (levels[1]?.[8] ?? 0) * 0.01 +
    (levels[2]?.[6] ?? 0) * 0.02;
  return (1 + scale * prestige) * (1 + 0.1 * gemDamageLevel);
}

/** Max possible ATK multiplier for this prestige (assumes max T1.8 + T2.7). Used to cap raw atk in target-wave mode. */
export function getMaxPrestigeAtkMultiplier(prestige: number, gemDamageLevel: number): number {
  return (1 + PRESTIGE_BONUS_SCALE_MAX * prestige) * (1 + 0.1 * gemDamageLevel);
}

/** True if this upgrade only adds crit/critDmg (no atk, HP, block, speed, or enemy debuffs). In target-wave mode these are never suggested. */
export function isPureCritUpgrade(tier: 1 | 2 | 3 | 4, idx: number): boolean {
  return (tier === 1 && idx === 5) || (tier === 3 && idx === 2);
}

/** True if this upgrade only adds atk/crit/critDmg (no HP, block, speed, or enemy debuffs). Used to skip damage when user already has enough atk for target wave. */
export function isDamageOnlyUpgrade(tier: 1 | 2 | 3 | 4, idx: number): boolean {
  const damageOnly: Record<number, number[]> = {
    1: [0, 5],   // +1 Attack Damage; +1% Crit / +0.10 Crit Damage
    2: [],       // (T2.4 is atk+atkSpeed – keep for speed)
    3: [0, 2],   // +2 Attack Damage; +1% Crit Chance
    4: [],       // T4.2 (+0.10 Crit Dmg / -0.10 Enemy Crit Dmg) has survival value → not skipped
  };
  return (damageOnly[tier]?.includes(idx)) === true;
}

/** Next prestige wave strictly after this wave (prestige milestones are 5, 10, 15, …). */
export function getNextPrestigeWaveAfter(wave: number): number {
  return Math.ceil((wave + 0.01) / 5) * 5;
}

/** Event reward waves: at these waves you get rewards. Used for tie-break band (highest reward wave reached). */
export const EVENT_REWARD_WAVES: number[] = [
  2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50,
  55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 115, 130, 150, 200, 250,
];

/** Highest reward wave that is <= wave (0 if wave &lt; first reward). */
export function getRewardBand(wave: number): number {
  let band = 0;
  for (const t of EVENT_REWARD_WAVES) {
    if (t <= wave) band = t;
    else break;
  }
  return band;
}

/** Next reward milestone wave strictly after the wave required for this prestige (you have cleared at least that). */
export function getNextRewardMilestoneAfterPrestige(prestige: number): number {
  const cleared = getPrestigeWaveRequirement(prestige);
  for (const w of EVENT_REWARD_WAVES) {
    if (w > cleared) return w;
  }
  return EVENT_REWARD_WAVES[EVENT_REWARD_WAVES.length - 1] ?? cleared + 5;
}

const REWARD_ICON_BASE = "https://static.wikitide.net/shminerwiki";

type RewardMilestoneEntry = {
  label: string;
  iconUrl: string;
  /** If true, amount is multiplied by 2^worldMonuments (Gifts, Mythic Chests, Skins are false). */
  monumentMultiplied?: boolean;
  /** Base amount for display when monumentMultiplied (e.g. 20 for "20 Gems"). */
  baseAmount?: number;
  /** Unit for display when monumentMultiplied (e.g. "Gems"). */
  unit?: string;
};/** Wave → reward label and icon URL for display (e.g. "Wave 40 (Seasonal Miner + Lootbug Skin)" with icon). */
export const EVENT_REWARD_MILESTONE_INFO: Record<number, RewardMilestoneEntry> = {
  2: { label: "20 Gems", iconUrl: `${REWARD_ICON_BASE}/a/aa/Gem.png`, monumentMultiplied: true, baseAmount: 20, unit: "Gems" },
  4: { label: "6 Item Chests", iconUrl: `${REWARD_ICON_BASE}/thumb/a/a8/Item_Chest.png/30px-Item_Chest.png`, monumentMultiplied: true, baseAmount: 6, unit: "Item Chests" },
  6: { label: "2 Gifts", iconUrl: `${REWARD_ICON_BASE}/thumb/2/24/Gift.png/27px-Gift.png`, monumentMultiplied: false },
  8: { label: "30 Gems", iconUrl: `${REWARD_ICON_BASE}/a/aa/Gem.png`, monumentMultiplied: true, baseAmount: 30, unit: "Gems" },
  10: { label: "10 Charge Magnets", iconUrl: `${REWARD_ICON_BASE}/thumb/f/fc/Charge_Magnet.png/28px-Charge_Magnet.png`, monumentMultiplied: true, baseAmount: 10, unit: "Charge Magnets" },
  12: { label: "5 Relic Chests", iconUrl: `${REWARD_ICON_BASE}/thumb/6/6d/Relic_Chest.png/30px-Relic_Chest.png`, monumentMultiplied: true, baseAmount: 5, unit: "Relic Chests" },
  14: { label: "15 Item Chests", iconUrl: `${REWARD_ICON_BASE}/thumb/a/a8/Item_Chest.png/30px-Item_Chest.png`, monumentMultiplied: true, baseAmount: 15, unit: "Item Chests" },
  16: { label: "40 Gems", iconUrl: `${REWARD_ICON_BASE}/a/aa/Gem.png`, monumentMultiplied: true, baseAmount: 40, unit: "Gems" },
  18: { label: "3 Blue Cows", iconUrl: `${REWARD_ICON_BASE}/thumb/9/98/Blue_Cow.png/15px-Blue_Cow.png`, monumentMultiplied: true, baseAmount: 3, unit: "Blue Cows" },
  20: { label: "5 Gifts", iconUrl: `${REWARD_ICON_BASE}/thumb/2/24/Gift.png/27px-Gift.png`, monumentMultiplied: false },
  22: { label: "50 Gems", iconUrl: `${REWARD_ICON_BASE}/a/aa/Gem.png`, monumentMultiplied: true, baseAmount: 50, unit: "Gems" },
  24: { label: "20 Item Chests", iconUrl: `${REWARD_ICON_BASE}/thumb/a/a8/Item_Chest.png/30px-Item_Chest.png`, monumentMultiplied: true, baseAmount: 20, unit: "Item Chests" },
  26: { label: "10 Skill Shards", iconUrl: `${REWARD_ICON_BASE}/a/aa/Skill_Shard.png`, monumentMultiplied: true, baseAmount: 10, unit: "Skill Shards" },
  28: { label: "5 Primal Meat", iconUrl: `${REWARD_ICON_BASE}/thumb/2/26/Primal_Meat.png/28px-Primal_Meat.png`, monumentMultiplied: true, baseAmount: 5, unit: "Primal Meat" },
  30: { label: "8 Relic Chests", iconUrl: `${REWARD_ICON_BASE}/thumb/6/6d/Relic_Chest.png/30px-Relic_Chest.png`, monumentMultiplied: true, baseAmount: 8, unit: "Relic Chests" },
  32: { label: "65 Gems", iconUrl: `${REWARD_ICON_BASE}/a/aa/Gem.png`, monumentMultiplied: true, baseAmount: 65, unit: "Gems" },
  34: { label: "12 Skill Shards", iconUrl: `${REWARD_ICON_BASE}/a/aa/Skill_Shard.png`, monumentMultiplied: true, baseAmount: 12, unit: "Skill Shards" },
  36: { label: "10 Relic Chests", iconUrl: `${REWARD_ICON_BASE}/thumb/6/6d/Relic_Chest.png/30px-Relic_Chest.png`, monumentMultiplied: true, baseAmount: 10, unit: "Relic Chests" },
  38: { label: "80 Gems", iconUrl: `${REWARD_ICON_BASE}/a/aa/Gem.png`, monumentMultiplied: true, baseAmount: 80, unit: "Gems" },
  40: {
    label: "Seasonal Miner + Lootbug Skin",
    iconUrl: `${REWARD_ICON_BASE}/thumb/3/30/Valentines_Event_Skin_Icon.png/30px-Valentines_Event_Skin_Icon.png`,
    monumentMultiplied: false,
  },
  42: { label: "5 Blue Cows", iconUrl: `${REWARD_ICON_BASE}/thumb/9/98/Blue_Cow.png/15px-Blue_Cow.png`, monumentMultiplied: true, baseAmount: 5, unit: "Blue Cows" },
  44: { label: "30 Item Chests", iconUrl: `${REWARD_ICON_BASE}/thumb/a/a8/Item_Chest.png/30px-Item_Chest.png`, monumentMultiplied: true, baseAmount: 30, unit: "Item Chests" },
  46: { label: "14 Skill Shards", iconUrl: `${REWARD_ICON_BASE}/a/aa/Skill_Shard.png`, monumentMultiplied: true, baseAmount: 14, unit: "Skill Shards" },
  48: { label: "100 Gems", iconUrl: `${REWARD_ICON_BASE}/a/aa/Gem.png`, monumentMultiplied: true, baseAmount: 100, unit: "Gems" },
  50: { label: "1 Mythic Chest", iconUrl: `${REWARD_ICON_BASE}/thumb/1/12/Mythic_Chest.png/30px-Mythic_Chest.png`, monumentMultiplied: false },
  55: { label: "12 Relic Chests", iconUrl: `${REWARD_ICON_BASE}/thumb/6/6d/Relic_Chest.png/30px-Relic_Chest.png`, monumentMultiplied: true, baseAmount: 12, unit: "Relic Chests" },
  60: { label: "16 Skill Shards", iconUrl: `${REWARD_ICON_BASE}/a/aa/Skill_Shard.png`, monumentMultiplied: true, baseAmount: 16, unit: "Skill Shards" },
  65: { label: "120 Gems", iconUrl: `${REWARD_ICON_BASE}/a/aa/Gem.png`, monumentMultiplied: true, baseAmount: 120, unit: "Gems" },
  70: { label: "8 Gifts", iconUrl: `${REWARD_ICON_BASE}/thumb/2/24/Gift.png/27px-Gift.png`, monumentMultiplied: false },
  75: { label: "150 Gems", iconUrl: `${REWARD_ICON_BASE}/a/aa/Gem.png`, monumentMultiplied: true, baseAmount: 150, unit: "Gems" },
  80: {
    label: "Seasonal Bag Skin",
    iconUrl: `${REWARD_ICON_BASE}/thumb/1/12/Event_Bag_Skin_Icon.png/30px-Event_Bag_Skin_Icon.png`,
    monumentMultiplied: false,
  },
  85: { label: "30 Relic Chests", iconUrl: `${REWARD_ICON_BASE}/thumb/6/6d/Relic_Chest.png/30px-Relic_Chest.png`, monumentMultiplied: true, baseAmount: 30, unit: "Relic Chests" },
  90: { label: "20 Skill Shards", iconUrl: `${REWARD_ICON_BASE}/a/aa/Skill_Shard.png`, monumentMultiplied: true, baseAmount: 20, unit: "Skill Shards" },
  95: { label: "10 Gifts", iconUrl: `${REWARD_ICON_BASE}/thumb/2/24/Gift.png/27px-Gift.png`, monumentMultiplied: false },
  100: { label: "1 Mythic Chest", iconUrl: `${REWARD_ICON_BASE}/thumb/1/12/Mythic_Chest.png/30px-Mythic_Chest.png`, monumentMultiplied: false },
  115: { label: "2 Gifts", iconUrl: `${REWARD_ICON_BASE}/thumb/2/24/Gift.png/27px-Gift.png`, monumentMultiplied: false },
  130: { label: "3 Gifts", iconUrl: `${REWARD_ICON_BASE}/thumb/2/24/Gift.png/27px-Gift.png`, monumentMultiplied: false },
  150: { label: "5 Gifts", iconUrl: `${REWARD_ICON_BASE}/thumb/2/24/Gift.png/27px-Gift.png`, monumentMultiplied: false },
  200: { label: "10 Gifts", iconUrl: `${REWARD_ICON_BASE}/thumb/2/24/Gift.png/27px-Gift.png`, monumentMultiplied: false },
  250: { label: "15 Gifts", iconUrl: `${REWARD_ICON_BASE}/thumb/2/24/Gift.png/27px-Gift.png`, monumentMultiplied: false },
};

export function getRewardMilestoneLabel(wave: number): { label: string; iconUrl: string } | null {
  return EVENT_REWARD_MILESTONE_INFO[wave] ?? null;
}

/** Returns display label with monument multiplier applied. World 1 = 0 monuments = ×1; World 2 = 1 monument = ×2; World 3 = ×4; World 4 = ×8. Gifts, Mythic Chests, Skins unchanged. */
export function getRewardMilestoneDisplayLabel(wave: number, maxWorld: number): { label: string; iconUrl: string } | null {
  const info = EVENT_REWARD_MILESTONE_INFO[wave];
  if (!info) return null;
  const monumentsBuilt = Math.max(0, Math.min(3, maxWorld - 1));
  const mult = 2 ** monumentsBuilt;
  if (info.monumentMultiplied !== false && info.baseAmount != null && info.unit != null) {
    return { label: `${info.baseAmount * mult} ${info.unit}`, iconUrl: info.iconUrl };
  }
  return { label: info.label, iconUrl: info.iconUrl };
}
