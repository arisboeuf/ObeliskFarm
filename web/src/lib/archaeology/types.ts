export type Skill = "strength" | "agility" | "perception" | "intellect" | "luck";
export type BlockType = "dirt" | "common" | "rare" | "epic" | "legendary" | "mythic";
export type BlockTier = 1 | 2 | 3;
export type CardLevel = 0 | 1 | 2 | 3;

export type ArchGemUpgradeKey = "stamina" | "xp" | "fragment" | "arch_xp";

export type ArchBuild = {
  // Goal stage (Python UI: "Goal Stage"). Calculations use (goalStage - 1).
  goalStage: number;
  unlockedStage: number;

  // Archaeology level (TOTAL skill points available to distribute).
  archLevel: number;

  skillPoints: Record<Skill, number>;
  gemUpgrades: Record<ArchGemUpgradeKey, number>;
  fragmentUpgradeLevels: Record<string, number>;

  // Key: `${blockType},${tier}` like Python save format.
  blockCards: Record<string, CardLevel>;
  miscCardLevel: CardLevel;

  // Toggles
  enrageEnabled: boolean;
  flurryEnabled: boolean;
  quakeEnabled: boolean;
  avadaKedaEnabled: boolean;
  blockBonkerEnabled: boolean;
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
  one_hit_chance: number;

  xp_mult: number;
  arch_xp_mult: number;
  xp_gain_total: number;
  fragment_mult: number;

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

