/**
 * Stargazing Calculator (web port)
 *
 * Ported 1:1 from `ObeliskGemEV/stargazing/calculator.py`.
 * Calculates stars and super stars per hour based on in-game stats.
 */
 
// Base game constants
export const BASE_STAR_SPAWN_CHANCE = 1 / 50; // 2% per floor clear
export const BASE_SUPER_STAR_SPAWN_CHANCE = 1 / 100; // 1% per spawn event

function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, x));
}
 
export type PlayerStats = {
  // Floor clears per hour
  floor_clears_per_hour: number;
 
  // Star spawn rate multiplier
  star_spawn_rate_mult: number;
 
  // Auto-catch chance (0.0 to 1.0)
  auto_catch_chance: number;
 
  // Double/Triple star chances (0.0 to 1.0)
  double_star_chance: number;
  triple_star_chance: number;
 
  // Super star spawn rate multiplier
  super_star_spawn_rate_mult: number;
 
  // Super star bonuses
  triple_super_star_chance: number;
  super_star_10x_chance: number;
 
  // Star multipliers
  star_supernova_chance: number;
  star_supernova_mult: number;
  star_supergiant_chance: number;
  star_supergiant_mult: number;
  star_radiant_chance: number;
  star_radiant_mult: number;
 
  // Super star multipliers
  super_star_supernova_chance: number;
  super_star_supernova_mult: number;
  super_star_supergiant_chance: number;
  super_star_supergiant_mult: number;
  super_star_radiant_chance: number;
  super_star_radiant_mult: number;
 
  // Global multipliers
  all_star_mult: number;
  novagiant_combo_mult: number;
 
  // CTRL+F Stars skill (multiplies offline gains by 5x)
  ctrl_f_stars_enabled: boolean;
};
 
export function defaultPlayerStats(): PlayerStats {
  // Matches defaults from desktop `StargazingWindow.reset_to_defaults()`.
  return {
    floor_clears_per_hour: 120.0,
    star_spawn_rate_mult: 1.0,
    auto_catch_chance: 0.0,
    double_star_chance: 0.0,
    triple_star_chance: 0.0,
    super_star_spawn_rate_mult: 1.0,
    triple_super_star_chance: 0.0,
    super_star_10x_chance: 0.0,
    star_supernova_chance: 0.0,
    star_supernova_mult: 10.0,
    star_supergiant_chance: 0.0,
    star_supergiant_mult: 3.0,
    star_radiant_chance: 0.0,
    star_radiant_mult: 10.0,
    super_star_supernova_chance: 0.0,
    super_star_supernova_mult: 10.0,
    super_star_supergiant_chance: 0.0,
    super_star_supergiant_mult: 3.0,
    super_star_radiant_chance: 0.0,
    super_star_radiant_mult: 10.0,
    all_star_mult: 1.0,
    novagiant_combo_mult: 1.0,
    ctrl_f_stars_enabled: false,
  };
}
 
export class StargazingCalculator {
  /**
   * Calculates stars and super stars per hour.
   *
   * Game mechanics:
   * 1. Base chance: 1/50 (2%) per floor clear for a star to spawn
   * 2. Star Spawn Rate Multiplier: Increases the effective spawn chance
   * 3. At each spawn event, either:
   *    - A Super Star spawns (exclusive with regular stars)
   *    - OR a Regular Star spawns (can be single/double/triple)
   * 4. Double/Triple Star Chance: Only applies to regular star spawns
   * 5. Supernova/Supergiant/Radiant: Multipliers on individual stars
   * 6. All Star Multiplier: Final multiplier on all stars
   */
  constructor(public readonly stats: PlayerStats) {}
 
  /** Calculate the number of star spawn events per hour. */
  calculate_star_spawn_rate_per_hour(): number {
    const base_chance = BASE_STAR_SPAWN_CHANCE; // 1/50 = 0.02
    let modified_chance = base_chance * this.stats.star_spawn_rate_mult;
    modified_chance = Math.min(modified_chance, 1.0); // cap at 100%
    return this.stats.floor_clears_per_hour * modified_chance;
  }
 
  /**
   * Calculate expected number of REGULAR stars per spawn event.
   *
   * Accounts for:
   * - Double star chance (2 stars instead of 1)
   * - Triple star chance (3 stars instead of 1)
   *
   * Note: Super Star spawns are exclusive with regular stars.
   */
  calculate_stars_per_spawn(): number {
    // Probability of super star spawn (exclusive with regular stars)
    const base_super_chance = BASE_SUPER_STAR_SPAWN_CHANCE; // 1/100 = 0.01
    const p_super_star = clamp01(base_super_chance * this.stats.super_star_spawn_rate_mult);
 
    // Probability of regular star spawn (when not super star)
    const p_regular_star = 1 - p_super_star;
 
    // Probability distribution for regular stars
    const p_triple = clamp01(this.stats.triple_star_chance);
    const p_double_raw = clamp01(this.stats.double_star_chance);
    const p_double = p_double_raw * (1 - p_triple); // only if not triple
    const p_single = Math.max(0, 1 - p_triple - p_double);
 
    // Expected regular stars per spawn event
    return p_regular_star * (1 * p_single + 2 * p_double + 3 * p_triple);
  }
 
  /**
   * Calculate expected multiplier per star from special effects.
   *
   * Effects:
   * - Supernova: 10x stars (default)
   * - Supergiant: 3x stars (default)
   * - Radiant: 10x stars (default)
   * - Novagiant Combo: Extra multiplier when both supernova AND supergiant
   */
  calculate_star_multiplier_per_star(): number {
    const p_supernova = clamp01(this.stats.star_supernova_chance);
    const p_supergiant = clamp01(this.stats.star_supergiant_chance);
    const p_radiant = clamp01(this.stats.star_radiant_chance);
 
    // Expected multiplier from each effect
    const supernova_contribution = 1 + p_supernova * (this.stats.star_supernova_mult - 1);
    const supergiant_contribution = 1 + p_supergiant * (this.stats.star_supergiant_mult - 1);
    const radiant_contribution = 1 + p_radiant * (this.stats.star_radiant_mult - 1);
 
    // Novagiant combo: when both supernova AND supergiant occur
    const p_novagiant = p_supernova * p_supergiant;
    const novagiant_contribution = 1 + p_novagiant * (this.stats.novagiant_combo_mult - 1);
 
    // Total multiplier (multiplicative stacking)
    let total_mult = supernova_contribution * supergiant_contribution * radiant_contribution * novagiant_contribution;
 
    // Apply all star multiplier
    total_mult *= this.stats.all_star_mult;
    return total_mult;
  }
 
  /** Calculate total expected stars per hour (online/manual). */
  calculate_stars_per_hour_online(): number {
    const spawns_per_hour = this.calculate_star_spawn_rate_per_hour();
    const stars_per_spawn = this.calculate_stars_per_spawn();
    const mult_per_star = this.calculate_star_multiplier_per_star();
    return spawns_per_hour * stars_per_spawn * mult_per_star;
  }
 
  /**
   * Calculate stars automatically caught per hour (offline/AFK).
   *
   * Offline gains formula:
   * - Without CTRL+F Stars: auto_catch * spawn_rate * 0.2 (1 of 5 floors)
   * - With CTRL+F Stars: auto_catch * spawn_rate * 1.0 (all 5 floors)
   */
  calculate_stars_per_hour_offline(): number {
    const total_stars = this.calculate_stars_per_hour_online();
 
    // Offline gains multiplier: 0.2 without CTRL+F, 1.0 with CTRL+F
    const offline_mult = this.stats.ctrl_f_stars_enabled ? 1.0 : 0.2;
 
    return total_stars * clamp01(this.stats.auto_catch_chance) * offline_mult;
  }
 
  /**
   * Calculate expected number of super stars per super star spawn event.
   *
   * Accounts for:
   * - Triple super star chance (3 instead of 1)
   * - 10x super star spawn chance (10 instead of 1)
   */
  calculate_super_stars_per_spawn(): number {
    let base_count = 1;
    base_count *= 1 + clamp01(this.stats.triple_super_star_chance) * 2; // +2 additional on triple
    base_count *= 1 + clamp01(this.stats.super_star_10x_chance) * 9; // +9 additional on 10x
    return base_count;
  }
 
  /** Calculate expected multiplier per super star from special effects. */
  calculate_super_star_multiplier_per_star(): number {
    const p_supernova = clamp01(this.stats.super_star_supernova_chance);
    const p_supergiant = clamp01(this.stats.super_star_supergiant_chance);
    const p_radiant = clamp01(this.stats.super_star_radiant_chance);
 
    const supernova_contribution = 1 + p_supernova * (this.stats.super_star_supernova_mult - 1);
    const supergiant_contribution = 1 + p_supergiant * (this.stats.super_star_supergiant_mult - 1);
    const radiant_contribution = 1 + p_radiant * (this.stats.super_star_radiant_mult - 1);
 
    // Novagiant combo for super stars
    const p_novagiant = p_supernova * p_supergiant;
    const novagiant_contribution = 1 + p_novagiant * (this.stats.novagiant_combo_mult - 1);
 
    let total_mult = supernova_contribution * supergiant_contribution * radiant_contribution * novagiant_contribution;
    total_mult *= this.stats.all_star_mult;
    return total_mult;
  }
 
  /**
   * Calculate the number of super star spawn events per hour.
   *
   * IMPORTANT: Super Star spawns are EXCLUSIVE with Double/Triple Star spawns.
   */
  calculate_super_star_spawn_rate_per_hour(): number {
    // Number of star spawn events per hour
    const star_spawn_events = this.calculate_star_spawn_rate_per_hour();
 
    // Chance that a spawn event is a Super Star
    const base_super_chance = BASE_SUPER_STAR_SPAWN_CHANCE; // 1/100 = 0.01
    const modified_super_chance = clamp01(base_super_chance * this.stats.super_star_spawn_rate_mult);
 
    // Super star spawn events = total spawn events * chance per event
    return star_spawn_events * modified_super_chance;
  }
 
  /** Calculate total expected super stars per hour (online/manual). */
  calculate_super_stars_per_hour_online(): number {
    const spawns_per_hour = this.calculate_super_star_spawn_rate_per_hour();
    const super_stars_per_spawn = this.calculate_super_stars_per_spawn();
    const mult_per_star = this.calculate_super_star_multiplier_per_star();
    return spawns_per_hour * super_stars_per_spawn * mult_per_star;
  }
 
  /**
   * Calculate super stars automatically caught per hour (offline/AFK).
   *
   * Offline gains formula:
   * - Without CTRL+F Stars: auto_catch * spawn_rate * 0.2 (1 of 5 floors)
   * - With CTRL+F Stars: auto_catch * spawn_rate * 1.0 (all 5 floors)
   */
  calculate_super_stars_per_hour_offline(): number {
    const total_super_stars = this.calculate_super_stars_per_hour_online();
 
    // Offline gains multiplier: 0.2 without CTRL+F, 1.0 with CTRL+F
    const offline_mult = this.stats.ctrl_f_stars_enabled ? 1.0 : 0.2;
 
    return total_super_stars * clamp01(this.stats.auto_catch_chance) * offline_mult;
  }
 
  /** Get a summary of all calculated values. */
  get_summary(): {
    star_spawn_rate_per_hour: number;
    stars_per_hour_online: number;
    stars_per_hour_offline: number;
    super_star_spawn_rate_per_hour: number;
    super_stars_per_hour_online: number;
    super_stars_per_hour_offline: number;
    floor_clears_per_hour: number;
    auto_catch_chance: number;
    ctrl_f_stars_enabled: boolean;
  } {
    return {
      // Star calculations
      star_spawn_rate_per_hour: this.calculate_star_spawn_rate_per_hour(),
      stars_per_hour_online: this.calculate_stars_per_hour_online(),
      stars_per_hour_offline: this.calculate_stars_per_hour_offline(),
 
      // Super star calculations
      super_star_spawn_rate_per_hour: this.calculate_super_star_spawn_rate_per_hour(),
      super_stars_per_hour_online: this.calculate_super_stars_per_hour_online(),
      super_stars_per_hour_offline: this.calculate_super_stars_per_hour_offline(),
 
      // Key stats
      floor_clears_per_hour: this.stats.floor_clears_per_hour,
      auto_catch_chance: this.stats.auto_catch_chance,
      ctrl_f_stars_enabled: this.stats.ctrl_f_stars_enabled,
    };
  }
}

