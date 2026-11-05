export type Skill = "strength" | "agility" | "perception" | "intellect" | "luck" | "divinity" | "corruption";
export type AscensionLevel = 0 | 1 | 2;
export type BlockType = "dirt" | "common" | "rare" | "epic" | "legendary" | "mythic" | "divine";

/** Block types that drop fragments (wiki: Common+ includes Divine). Order used for MC/UI tie-breaks. */
export const ARCH_FRAGMENT_TYPES = ["common", "rare", "epic", "legendary", "mythic", "divine"] as const satisfies readonly BlockType[];
export type ArchFragmentType = (typeof ARCH_FRAGMENT_TYPES)[number];
export type BlockTier = 1 | 2 | 3 | 4;
export type CardLevel = 0 | 1 | 2 | 3;

// Gem upgrades in the desktop Arch simulator (cost type: Gems)
export type ArchGemUpgradeKey = "stamina" | "xp" | "fragment";

export type AscensionUpgradeSnapshot = {
  fragmentUpgradeLevels: Record<string, number>;
  gemUpgrades: Record<ArchGemUpgradeKey, number>;
};

export type AscensionUpgradeSnapshots = Partial<Record<AscensionLevel, AscensionUpgradeSnapshot>>;

export type ArchBuild = {
  /** 0 = pre-ascension, 1 = ascended once, 2 = ascended twice (requires stage 150+ to select). */
  ascensionLevel: AscensionLevel;

  // Goal stage (Python UI: "Goal Stage"). Calculations use (goalStage - 1).
  goalStage: number;
  unlockedStage: number;

  // Archaeology level (TOTAL skill points available to distribute).
  archLevel: number;

  skillPoints: Record<Skill, number>;
  gemUpgrades: Record<ArchGemUpgradeKey, number>;
  fragmentUpgradeLevels: Record<string, number>;
  /** Per-ascension fragment/gem upgrade levels (0 = No Ascension, 1, 2). */
  ascensionUpgradeSnapshots?: AscensionUpgradeSnapshots;

  // Key: `${blockType},${tier}` like Python save format.
  blockCards: Record<string, CardLevel>;
  miscCardLevel: CardLevel;

  // Toggles
  enrageEnabled: boolean;
  flurryEnabled: boolean;
  quakeEnabled: boolean;
  avadaKedaEnabled: boolean;
  blockBonkerEnabled: boolean;
  /** When true, all MC runs start with speed mod effectively always active (for late-game when you have more procs than you consume). */
  permanentSpeedModEnabled: boolean;

  /** Whether you have the Axolotl Skin Quest. When true, rank 0 = +3% fragment gain, each rank adds another +3%. */
  axolotlQuestOwned?: boolean;
  /** Axolotl Skin Quest rank (0–20). Only used when axolotlQuestOwned; rank 0 already gives +3%. */
  axolotlQuestRank?: number;

  /** Level 1 Tribute (Cave Legendary Fish): when enabled, fragment gain +0.25% per mythic chest owned (additive). */
  level1TributeEnabled?: boolean;
  /** Number of mythic chests owned (used when level1TributeEnabled). */
  mythicChestsOwned?: number;

  /** Archaeology Bundle!: when enabled, fragment gain ×1.25. */
  archBundleEnabled?: boolean;
};

export type ArchStats = {
  flat_damage: number;
  total_damage: number;
  armor_pen: number;
  max_stamina: number;

  crit_chance: number;
  crit_damage: number;
  super_crit_chance: number;
  super_crit_damage: number;
  ultra_crit_chance: number;
  super_crit_dmg_mult: number;
  ultra_crit_dmg_mult: number;
  /** Ultra crit damage bonus (fraction); applied to ultra crit mult like super crit damage. */
  ultra_crit_damage: number;
  one_hit_chance: number;

  xp_mult: number;
  arch_xp_mult: number;
  xp_gain_total: number;
  fragment_mult: number;

  /** Chance per floor for Gleaming Floor (Ascension 2). */
  gleaming_floor_chance: number;
  /** Fragment multi applied to all blocks on a gleaming floor (base 3× × upgrade). */
  gleaming_floor_mult: number;

  exp_mod_chance: number;
  loot_mod_chance: number;
  speed_mod_chance: number;
  stamina_mod_chance: number;

  loot_mod_multiplier: number;
  exp_mod_gain: number;
  stamina_mod_gain: number;
  speed_mod_gain: number;

  enrage_damage_bonus: number;
  enrage_crit_damage_bonus: number;

  misc_card_level: number;

  enrage_cooldown: number;
  flurry_cooldown: number;
  quake_cooldown: number;
  ability_cooldown: number;
  avada_keda_duration_bonus: number;
  flurry_stamina_bonus: number;
  quake_charges: number;
  ability_instacharge: number;
};

export type ArchRunSummary = {
  floorsPerRun: number;
  xpPerRun: number;
  fragmentsPerRun: Record<Exclude<BlockType, "dirt">, number>;
  durationSeconds: number;
  fragmentsPerHour: number;
};

