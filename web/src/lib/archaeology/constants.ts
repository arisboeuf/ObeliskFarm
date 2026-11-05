import type { ArchGemUpgradeKey, BlockType, Skill } from "./types";

export const SKILL_POINT_CAPS_BASE: Record<Skill, number> = {
  strength: 50,
  agility: 50,
  perception: 25,
  intellect: 25,
  luck: 25,
  divinity: 10,
  corruption: 10,
};

export const SKILL_BONUSES: Record<
  Skill,
  Partial<{
    flat_damage: number;
    percent_damage: number;
    crit_damage: number;
    max_stamina: number;
    max_stamina_percent: number;
    crit_chance: number;
    speed_mod_chance: number;
    fragment_gain: number;
    loot_mod_chance: number;
    armor_pen: number;
    xp_bonus: number;
    exp_mod_chance: number;
    armor_pen_mult: number;
    all_mod_chance: number;
    one_hit_chance: number;
    super_crit_chance: number;
    mod_mult_bonus: number;
    crosshair_autotap_chance: number;
  }>
> = {
  strength: { flat_damage: 1, percent_damage: 0.01, crit_damage: 0.03 },
  agility: { max_stamina: 5, crit_chance: 0.01, speed_mod_chance: 0.002 },
  perception: { fragment_gain: 0.04, loot_mod_chance: 0.003, armor_pen: 2 },
  intellect: { xp_bonus: 0.05, exp_mod_chance: 0.003, armor_pen_mult: 0.03 },
  luck: { crit_chance: 0.02, all_mod_chance: 0.002, one_hit_chance: 0.0004 },
  divinity: { flat_damage: 2, super_crit_chance: 0.02, crosshair_autotap_chance: 0.02 },
  corruption: { percent_damage: 0.06, max_stamina_percent: -0.03, mod_mult_bonus: 0.01 },
};

export const ENRAGE_CHARGES = 5;
export const ENRAGE_COOLDOWN = 60;
export const ENRAGE_DAMAGE_BONUS = 0.2;
export const ENRAGE_CRIT_DAMAGE_BONUS = 1.0;

export const SUPER_CRIT_DMG_MULT_DEFAULT = 2.0;
export const ULTRA_CRIT_DMG_MULT_DEFAULT = 3.0;

export const FLURRY_COOLDOWN = 120;
/** Stamina gained when Flurry activates (Flurry Buff upgrade adds +1 per level). */
export const FLURRY_STAMINA_BONUS = 5;
/** Fixed buff duration in seconds (no upgrades increase this). */
export const FLURRY_DURATION_SECONDS = 5;

export const QUAKE_CHARGES = 5;
export const QUAKE_COOLDOWN = 180;
export const QUAKE_DAMAGE_MULTIPLIER = 0.2;

export const MOD_EXP_MULTIPLIER_AVG = 3.0;
export const MOD_LOOT_MULTIPLIER_AVG = 2.0;
/** Fixed number of attacks per Speed Mod proc (base). With Block Bonker: base + unlocked stage (e.g. 10 + 19 = 29). */
export const MOD_SPEED_ATTACKS_BASE = 10.0;
export const MOD_STAMINA_BONUS_AVG = 3.0;

/** Ascension 2 Gleaming Floor: base fragment multi when a floor procs; upgrade adds +% on top (multiplicative). */
export const GLEAMING_FLOOR_MULTI_BASE = 3.0;

export const GEM_UPGRADE_BONUSES: Record<
  ArchGemUpgradeKey,
  { max_level: number; stage_unlock: number } & Record<string, number>
> = {
  stamina: { max_stamina: 2, stamina_mod_chance: 0.0005, max_level: 50, stage_unlock: 0 },
  xp: { xp_bonus: 0.05, exp_mod_chance: 0.0005, max_level: 25, stage_unlock: 0 },
  fragment: { fragment_gain: 0.02, loot_mod_chance: 0.0005, max_level: 25, stage_unlock: 0 },
};

export const FRAGMENT_UPGRADES: Record<
  string,
  {
    max_level: number;
    stage_unlock: number;
    cost_type: "common" | "rare" | "epic" | "legendary" | "mythic" | "divine";
    display_name: string;
    /** 0 = base tree; 1 = Ascension 1; 2 = Ascension 2. */
    ascension_tier?: 0 | 1 | 2;
  } & Record<string, number | string>
> = {
  flat_damage_c1: { flat_damage: 1, max_level: 25, stage_unlock: 0, cost_type: "common", display_name: "Flat Damage +1", ascension_tier: 0 },
  armor_pen_c1: { armor_pen: 1, max_level: 25, stage_unlock: 2, cost_type: "common", display_name: "Armor Penetration +1" },
  arch_xp_c1: { arch_xp_bonus: 0.02, max_level: 25, stage_unlock: 3, cost_type: "common", display_name: "Archaeology Exp Gain +2%" },
  crit_c1: { crit_chance: 0.0025, crit_damage: 0.01, max_level: 25, stage_unlock: 4, cost_type: "common", display_name: "Crit Chance +0.25%, Crit Damage +1%" },
  str_skill_buff: { flat_damage_skill: 0.2, percent_damage_skill: 0.001, max_level: 5, stage_unlock: 13, cost_type: "common", display_name: "Strength Skill Buff: Flat Damage +0.2, Damage +0.1%" },
  polychrome_bonus: { polychrome_bonus: 0.15, max_level: 1, stage_unlock: 34, cost_type: "common", display_name: "Polychrome Archaeology Card Bonus +15%" },

  stamina_r1: { max_stamina: 2, stamina_mod_chance: 0.0005, max_level: 20, stage_unlock: 5, cost_type: "rare", display_name: "Max Stamina +2, Stamina Mod Chance +0.05%" },
  flat_damage_r1: { flat_damage: 2, max_level: 20, stage_unlock: 6, cost_type: "rare", display_name: "Flat Damage +2" },
  loot_mod_mult: { loot_mod_multiplier: 0.3, max_level: 10, stage_unlock: 6, cost_type: "rare", display_name: "Loot Mod Gain Multiplier +0.30x" },
  enrage_buff: { enrage_damage: 0.02, enrage_crit_damage: 0.02, enrage_cooldown: -1, max_level: 15, stage_unlock: 7, cost_type: "rare", display_name: "Enrage Damage/Crit Damage +2%, Enrage Cooldown -1s" },
  agi_skill_buff: { max_stamina_skill: 1, mod_chance_skill: 0.0002, max_level: 5, stage_unlock: 15, cost_type: "rare", display_name: "Agility Skill Buff: Max Stamina +1, Mod Ch. +0.02%" },
  per_skill_buff: { mod_chance_skill: 0.0001, armor_pen_skill: 1, max_level: 5, stage_unlock: 22, cost_type: "rare", display_name: "Perception Skill Buff: Mod Ch. +0.01%, Armor Pen +1" },
  fragment_gain_1x: { fragment_gain_mult: 1.25, max_level: 1, stage_unlock: 36, cost_type: "rare", display_name: "Fragment Gain 1.25x" },

  flat_damage_e1: { flat_damage: 2, super_crit_chance: 0.0035, max_level: 25, stage_unlock: 9, cost_type: "epic", display_name: "Flat Damage +2, Super Crit Chance +0.35%" },
  arch_xp_frag_e1: { arch_xp_bonus: 0.03, fragment_gain: 0.02, max_level: 20, stage_unlock: 10, cost_type: "epic", display_name: "Archaeology Exp Gain +3%, Fragment Gain +2%" },
  flurry_buff: { flurry_stamina: 1, flurry_cooldown: -1, max_level: 10, stage_unlock: 11, cost_type: "epic", display_name: "Flurry Stamina Gain +1, Flurry Cooldown -1s" },
  stamina_e1: { max_stamina: 4, stamina_mod_gain: 1, max_level: 5, stage_unlock: 12, cost_type: "epic", display_name: "Max Stamina +4, Stamina Mod Gain +1" },
  int_skill_buff: { xp_bonus_skill: 0.01, mod_chance_skill: 0.0001, max_level: 5, stage_unlock: 24, cost_type: "epic", display_name: "Intellect Skill Buff: Exp Gain +1%, Mod Ch. +0.01%" },
  stamina_mod_gain_1: { stamina_mod_gain: 2, max_level: 1, stage_unlock: 38, cost_type: "epic", display_name: "Stamina Mod Gain +2" },

  arch_xp_stam_l1: { arch_xp_bonus: 0.05, max_stamina_percent: 0.01, max_level: 15, stage_unlock: 17, cost_type: "legendary", display_name: "Archaeology Exp Gain +5%, Maximum Stamina +1%" },
  armor_pen_cd_l1: { armor_pen_percent: 0.02, ability_cooldown: -1, max_level: 10, stage_unlock: 18, cost_type: "legendary", display_name: "Armor Penetration +2%, Ability Cooldown -1s" },
  crit_dmg_l1: { crit_damage: 0.02, super_crit_damage: 0.02, max_level: 20, stage_unlock: 20, cost_type: "legendary", display_name: "Crit Damage +2%, Super Crit Damage +2%" },
  quake_buff: { quake_attacks: 1, quake_cooldown: -2, max_level: 10, stage_unlock: 20, cost_type: "legendary", display_name: "Quake Attacks +1, Quake Cooldown -2s" },
  all_mod_chance: { all_mod_chance: 0.015, max_level: 1, stage_unlock: 40, cost_type: "legendary", display_name: "All Mod Chances +1.50%" },

  damage_apen_m1: { percent_damage: 0.02, armor_pen: 3, max_level: 20, stage_unlock: 26, cost_type: "mythic", display_name: "Damage +2%, Armor Penetration +3" },
  crit_chance_m1: { super_crit_chance: 0.0035, ultra_crit_chance: 0.01, max_level: 20, stage_unlock: 28, cost_type: "mythic", display_name: "Super Crit Chance +0.35%, Ultra Crit Chance +1%" },
  exp_mod_m1: { exp_mod_gain: 0.1, exp_mod_chance: 0.001, max_level: 20, stage_unlock: 30, cost_type: "mythic", display_name: "EXP Mod Gain +0.10x, EXP Mod Chance +0.10%" },
  ability_stam_m1: { ability_instacharge: 0.003, max_stamina: 4, max_level: 20, stage_unlock: 32, cost_type: "mythic", display_name: "Ability Instacharge +0.30%, Max Stamina +4" },
  exp_stat_cap_m1: { xp_bonus_mult: 2.0, all_stat_cap: 5, max_level: 1, stage_unlock: 42, cost_type: "mythic", display_name: "Exp Gain 2.00x, All Stat Point Caps +5", ascension_tier: 0 },

  // Ascension 1 (wiki Archaeology → Upgrades → Ascension 1)
  stat_points_a1: { extra_skill_points: 1, max_level: 5, stage_unlock: 4, cost_type: "common", display_name: "Stat Points +1", ascension_tier: 1 },
  crosshair_fairy_a1: { armor_pen: 3, max_level: 15, stage_unlock: 7, cost_type: "rare", display_name: "Crosshair Fairy Unlock, Armor Penetration +3", ascension_tier: 1 },
  all_mod_chance_a1: { all_mod_chance: 0.0002, max_level: 30, stage_unlock: 12, cost_type: "epic", display_name: "All Mod Chances +0.02%", ascension_tier: 1 },
  enrage_flat_a1: { flat_damage: 3, enrage_cooldown: -1, max_level: 5, stage_unlock: 21, cost_type: "legendary", display_name: "Flat Damage +3, Enrage Cooldown -1s", ascension_tier: 1 },
  ultra_crit_dmg_a1: { ultra_crit_damage: 0.02, stamina_mod_chance: 0.0003, max_level: 20, stage_unlock: 33, cost_type: "mythic", display_name: "Ultra Crit Damage +2%, Stamina Mod Chance +0.03%", ascension_tier: 1 },
  str_skill_buff_a1: { percent_damage_skill: 0.01, crit_damage: 0.01, max_level: 1, stage_unlock: 50, cost_type: "divine", display_name: "Strength Skill Buff: Damage +1%, Crit Damage +1%", ascension_tier: 1 },
  gold_crosshair_a1: { gold_crosshair_chance: 0.01, crosshair_autotap_chance: 0.01, max_level: 5, stage_unlock: 55, cost_type: "divine", display_name: "Gold Crosshair Chance +1%, Crosshair Auto-Tap +1%", ascension_tier: 1 },
  flat_ultra_a1: { flat_damage: 3, ultra_crit_chance: 0.005, max_level: 5, stage_unlock: 60, cost_type: "divine", display_name: "Flat Damage +3, Ultra Crit Chance +0.50%", ascension_tier: 1 },
  instacharge_a1: { ability_instacharge: 0.001, stamina_mod_chance: 0.001, max_level: 25, stage_unlock: 65, cost_type: "divine", display_name: "Ability Instacharge +0.10%, Stamina Mod Chance +0.10%", ascension_tier: 1 },
  dmg_xp_a1: { percent_damage: 0.1, arch_xp_bonus: 0.1, max_level: 5, stage_unlock: 70, cost_type: "divine", display_name: "Damage +10%, Archaeology Exp Gain +10%", ascension_tier: 1 },
  super_crit_exp_a1: { super_crit_damage: 0.005, exp_mod_gain: 0.02, max_level: 40, stage_unlock: 85, cost_type: "legendary", display_name: "Super Crit Damage +0.50%, Exp Mod Gain +2%", ascension_tier: 1 },
  stam_autotap_a1: { max_stamina_percent: 0.005, crosshair_autotap_chance: 0.002, max_level: 50, stage_unlock: 90, cost_type: "mythic", display_name: "Max Stamina +0.50%, Crosshair Auto-Tap +0.20%", ascension_tier: 1 },

  // Ascension 2
  gleaming_chance_a2: { gleaming_floor_chance: 0.001, max_level: 30, stage_unlock: 8, cost_type: "common", display_name: "Gleaming Floor Chance +0.10%", ascension_tier: 2 },
  ability_fairy_a2: { loot_mod_multiplier: 0.05, max_level: 30, stage_unlock: 16, cost_type: "rare", display_name: "Ability Fairy Unlock, Loot Mod Gain +0.05x", ascension_tier: 2 },
  divinity_buff_a2: { divinity_buff: 0.2, max_level: 5, stage_unlock: 23, cost_type: "epic", display_name: "Buff Divinity: All Div Stats +0.20", ascension_tier: 2 },
  gleaming_multi_a2: { gleaming_floor_mult: 0.03, max_level: 30, stage_unlock: 45, cost_type: "legendary", display_name: "Gleaming Floor Multi +3%", ascension_tier: 2 },
  corruption_buff_a2: { corruption_damage_buff: 0.002, corruption_speed_mod_buff: 0.001, max_level: 10, stage_unlock: 72, cost_type: "mythic", display_name: "Corruption Buff: Damage +0.2%, Speed Mod +0.1%", ascension_tier: 2 },
  all_mod_mult_a2: { mod_mult_bonus: 0.02, max_level: 10, stage_unlock: 92, cost_type: "divine", display_name: "All Mod Multipliers +2%", ascension_tier: 2 },
};

export const GEM_COSTS: Record<ArchGemUpgradeKey, number[]> = {
  stamina: [
    300, 315, 330, 347, 364, 382, 402, 422, 443, 465, 488, 513, 538, 565, 593, 623, 654, 687, 721, 758, 795, 835, 877, 921, 967,
    1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000,
    1000, 1000, 1000,
  ],
  xp: [400, 420, 441, 463, 486, 510, 536, 562, 590, 620, 651, 684, 718, 754, 791, 831, 873, 916, 962, 1000, 1000, 1000, 1000, 1000, 1000],
  fragment: [
    500, 525, 551, 578, 607, 638, 670, 703, 738, 775, 814, 855, 897, 942, 989, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000,
  ],
};

/** Gem upgrade costs after Ascension 1 (wiki Archaeology/Costs#Ascension_1). */
export const GEM_COSTS_ASCENSION_1: Record<ArchGemUpgradeKey, number[]> = {
  stamina: [
    15000, 15800, 16500, 17400, 18200, 19100, 20100, 21100, 22200, 23300, 24400, 25700, 26900, 28300, 29700, 31200,
    32700, 34400, 36100, 37900, 39800, 41800, 43900, 46100, 48400, 50800, 53300, 56000, 58800, 61700, 64800, 68100,
    71500, 75000, 78800, 82700, 86900, 91200, 95800, 101000, 106000, 111000, 116000, 122000, 128000, 135000, 142000,
    149000, 156000, 164000,
  ],
  xp: [
    20000, 21000, 22100, 23200, 24300, 25500, 26800, 28100, 29500, 31000, 32600, 34200, 35900, 37700, 39600, 41600,
    43700, 45800, 48100, 50500, 53100, 55700, 58500, 61400, 64500,
  ],
  fragment: [
    25000, 26200, 27600, 28900, 30400, 31900, 33500, 35200, 36900, 38800, 40700, 42800, 44900, 47100, 49500, 52000,
    54600, 57300, 60200, 63200, 66300, 69600, 73100, 76800, 80600,
  ],
};

/** Gem upgrade costs after Ascension 2 (wiki Archaeology/Costs#Ascension_2). */
export const GEM_COSTS_ASCENSION_2: Record<ArchGemUpgradeKey, number[]> = {
  stamina: [
    30000, 31500, 33100, 34700, 36500, 38300, 40200, 42200, 44300, 46500, 48900, 51300, 53900, 56600, 59400, 62400,
    65500, 68800, 72200, 75800, 79600, 83600, 87800, 92100, 96800, 102000, 107000, 112000, 118000, 123000, 130000,
    136000, 143000, 150000, 158000, 165000, 174000, 182000, 192000, 201000, 211000, 222000, 233000, 244000, 257000,
    270000, 283000, 297000, 312000, 328000,
  ],
  xp: [
    40000, 42000, 44100, 46300, 48600, 51100, 53600, 56300, 59100, 62100, 65200, 68400, 71800, 75400, 79200, 83200,
    87300, 91700, 96300, 101000, 106000, 111000, 117000, 123000, 129000,
  ],
  fragment: [
    50000, 52500, 55100, 57900, 60800, 63800, 67000, 70400, 73900, 77600, 81400, 85500, 89800, 94300, 99000, 104000,
    109000, 115000, 120000, 126000, 133000, 139000, 146000, 154000, 161000,
  ],
};

export const BLOCK_COLORS: Record<BlockType, string> = {
  dirt: "#8B4513",
  common: "#808080",
  rare: "#4169E1",
  epic: "#9932CC",
  legendary: "#6B5200",
  mythic: "#FF4500",
  divine: "#E8E8FF",
};

export const SLOTS_PER_FLOOR = 24;

