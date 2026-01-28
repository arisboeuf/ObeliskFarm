import type { ArchGemUpgradeKey, BlockType, Skill } from "./types";

export const SKILL_POINT_CAPS_BASE: Record<Skill, number> = {
  strength: 50,
  agility: 50,
  perception: 25,
  intellect: 25,
  luck: 25,
};

export const SKILL_BONUSES: Record<
  Skill,
  Partial<{
    flat_damage: number;
    percent_damage: number;
    crit_damage: number;
    max_stamina: number;
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
  }>
> = {
  strength: { flat_damage: 1, percent_damage: 0.01, crit_damage: 0.03 },
  agility: { max_stamina: 5, crit_chance: 0.01, speed_mod_chance: 0.002 },
  perception: { fragment_gain: 0.04, loot_mod_chance: 0.003, armor_pen: 2 },
  intellect: { xp_bonus: 0.05, exp_mod_chance: 0.003, armor_pen_mult: 0.03 },
  luck: { crit_chance: 0.02, all_mod_chance: 0.002, one_hit_chance: 0.0004 },
};

export const ENRAGE_CHARGES = 5;
export const ENRAGE_COOLDOWN = 60;
export const ENRAGE_DAMAGE_BONUS = 0.2;
export const ENRAGE_CRIT_DAMAGE_BONUS = 1.0;

export const SUPER_CRIT_DMG_MULT_DEFAULT = 2.0;
export const ULTRA_CRIT_DMG_MULT_DEFAULT = 3.0;

export const FLURRY_COOLDOWN = 120;
export const FLURRY_STAMINA_BONUS = 5;

export const QUAKE_CHARGES = 5;
export const QUAKE_COOLDOWN = 180;
export const QUAKE_DAMAGE_MULTIPLIER = 0.2;

export const MOD_EXP_MULTIPLIER_AVG = 3.0;
export const MOD_LOOT_MULTIPLIER_AVG = 2.0;
export const MOD_SPEED_ATTACKS_AVG = 10.0;
export const MOD_STAMINA_BONUS_AVG = 3.0;

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
  { max_level: number; stage_unlock: number; cost_type: "common" | "rare" | "epic" | "legendary" | "mythic"; display_name: string } & Record<
    string,
    number | string
  >
> = {
  flat_damage_c1: { flat_damage: 1, max_level: 25, stage_unlock: 0, cost_type: "common", display_name: "Flat Dmg +1" },
  armor_pen_c1: { armor_pen: 1, max_level: 25, stage_unlock: 2, cost_type: "common", display_name: "Armor Pen +1" },
  arch_xp_c1: { arch_xp_bonus: 0.02, max_level: 25, stage_unlock: 3, cost_type: "common", display_name: "Exp Gain +2%" },
  crit_c1: { crit_chance: 0.0025, crit_damage: 0.01, max_level: 25, stage_unlock: 4, cost_type: "common", display_name: "Crit +0.25%/+1%" },
  str_skill_buff: { flat_damage_skill: 0.2, percent_damage_skill: 0.001, max_level: 5, stage_unlock: 13, cost_type: "common", display_name: "STR Buff" },
  polychrome_bonus: { polychrome_bonus: 0.15, max_level: 1, stage_unlock: 34, cost_type: "common", display_name: "Polychrome +15%" },

  stamina_r1: { max_stamina: 2, stamina_mod_chance: 0.0005, max_level: 20, stage_unlock: 5, cost_type: "rare", display_name: "Stam +2/+0.05%" },
  flat_damage_r1: { flat_damage: 2, max_level: 20, stage_unlock: 6, cost_type: "rare", display_name: "Flat Dmg +2" },
  loot_mod_mult: { loot_mod_multiplier: 0.3, max_level: 10, stage_unlock: 6, cost_type: "rare", display_name: "Loot Mod +0.3x" },
  enrage_buff: { enrage_damage: 0.02, enrage_crit_damage: 0.02, enrage_cooldown: -1, max_level: 15, stage_unlock: 7, cost_type: "rare", display_name: "Enrage Buff" },
  agi_skill_buff: { max_stamina_skill: 1, mod_chance_skill: 0.0002, max_level: 5, stage_unlock: 15, cost_type: "rare", display_name: "AGI Buff" },
  per_skill_buff: { mod_chance_skill: 0.0001, armor_pen_skill: 1, max_level: 5, stage_unlock: 22, cost_type: "rare", display_name: "PER Buff" },
  fragment_gain_1x: { fragment_gain_mult: 1.25, max_level: 1, stage_unlock: 36, cost_type: "rare", display_name: "Frag Gain 1.25x" },

  flat_damage_e1: { flat_damage: 2, super_crit_chance: 0.0035, max_level: 25, stage_unlock: 9, cost_type: "epic", display_name: "Dmg +2/SCrit +0.35%" },
  arch_xp_frag_e1: { arch_xp_bonus: 0.03, fragment_gain: 0.02, max_level: 20, stage_unlock: 10, cost_type: "epic", display_name: "Exp +3%/Frag +2%" },
  flurry_buff: { flurry_stamina: 1, flurry_cooldown: -1, max_level: 10, stage_unlock: 11, cost_type: "epic", display_name: "Flurry Buff" },
  stamina_e1: { max_stamina: 4, stamina_mod_gain: 1, max_level: 5, stage_unlock: 12, cost_type: "epic", display_name: "Stam +4/+1 Mod" },
  int_skill_buff: { xp_bonus_skill: 0.01, mod_chance_skill: 0.0001, max_level: 5, stage_unlock: 24, cost_type: "epic", display_name: "INT Buff" },
  stamina_mod_gain_1: { stamina_mod_gain: 2, max_level: 1, stage_unlock: 38, cost_type: "epic", display_name: "Stam Mod +2" },

  arch_xp_stam_l1: { arch_xp_bonus: 0.05, max_stamina_percent: 0.01, max_level: 15, stage_unlock: 17, cost_type: "legendary", display_name: "Exp +5%/Stam +1%" },
  armor_pen_cd_l1: { armor_pen_percent: 0.02, ability_cooldown: -1, max_level: 10, stage_unlock: 18, cost_type: "legendary", display_name: "APen +2%/CD -1s" },
  crit_dmg_l1: { crit_damage: 0.02, super_crit_damage: 0.02, max_level: 20, stage_unlock: 20, cost_type: "legendary", display_name: "Crit Dmg +2%/+2%" },
  quake_buff: { quake_attacks: 1, quake_cooldown: -2, max_level: 10, stage_unlock: 20, cost_type: "legendary", display_name: "Quake Buff" },
  all_mod_chance: { all_mod_chance: 0.015, max_level: 1, stage_unlock: 40, cost_type: "legendary", display_name: "All Mod +1.5%" },

  damage_apen_m1: { percent_damage: 0.02, armor_pen: 3, max_level: 20, stage_unlock: 26, cost_type: "mythic", display_name: "Dmg +2%/APen +3" },
  crit_chance_m1: { super_crit_chance: 0.0035, ultra_crit_chance: 0.01, max_level: 20, stage_unlock: 28, cost_type: "mythic", display_name: "S/U Crit +0.35%/+1%" },
  exp_mod_m1: { exp_mod_gain: 0.1, exp_mod_chance: 0.001, max_level: 20, stage_unlock: 30, cost_type: "mythic", display_name: "Exp Mod +0.1x/+0.1%" },
  ability_stam_m1: { ability_instacharge: 0.003, max_stamina: 4, max_level: 20, stage_unlock: 32, cost_type: "mythic", display_name: "Insta +0.3%/Stam +4" },
  exp_stat_cap_m1: { xp_bonus_mult: 2.0, all_stat_cap: 5, max_level: 1, stage_unlock: 42, cost_type: "mythic", display_name: "Exp 2x/Caps +5" },
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

export const BLOCK_COLORS: Record<BlockType, string> = {
  dirt: "#8B4513",
  common: "#808080",
  rare: "#4169E1",
  epic: "#9932CC",
  legendary: "#6B5200",
  mythic: "#FF4500",
};

export const SLOTS_PER_FLOOR = 24;

