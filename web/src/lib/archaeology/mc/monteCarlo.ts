import { BLOCK_TYPES, getBlockMixForFloor } from "../blockStats";
import { getNormalizedSpawnRates, getSpawnRatesForStage } from "../spawnRates";
import { ARCH_FRAGMENT_TYPES, type BlockTier, type BlockType } from "../types";
import type { Rng } from "./prng";
import { mulberry32, randUniform } from "./prng";

// Ported from ObeliskGemEV/archaeology/monte_carlo_crit.py (adapted for web + tiered cards).

/** Initial speed-mod hits when "permanent speed mod" is enabled (runs start with speed mod effectively always on). */
export const PERMANENT_SPEED_MOD_INITIAL_HITS = 1_000_000;

export type McBlockBreakdown = {
  by_type: Record<
    string,
    { blocks_destroyed_est: number; time_seconds_est: number; avg_hits_per_block_est: number }
  >;
  total_time_seconds_est: number;
  most_time_type: string | null;
  most_avg_hits_type: string | null;
  max_hits_single_block: number;
  max_hits_single_block_type: string | null;
  note: string;
};

export type McRunMetrics = {
  floors_cleared: number;
  max_stage_reached: number;
  starting_floor: number;
  fragments: Record<string, number>;
  total_fragments: number;
  xp_per_run: number;
  run_duration_seconds: number;
  total_hits: number;
  block_breakdown?: McBlockBreakdown | null;
  /** Stamina remaining at end of each completed stage (stage index -> stamina). Used for avg stamina-at-stage overview. */
  stamina_at_end_of_stage?: Record<number, number>;
};

export type McRunOptions = {
  use_crit: boolean;
  enrage_enabled: boolean;
  flurry_enabled: boolean;
  quake_enabled: boolean;
  return_block_metrics: boolean;
  /** When set, each run starts with this many speed-mod hits remaining (e.g. permanent speed mod). */
  initialSpeedModHits?: number;
  /** 0 = pre-ascension; 1+ enables divine blocks and ascension upgrades in spawn/block mix. */
  ascensionLevel?: 0 | 1 | 2;
};

type EnrageState = { charges_remaining: number; cooldown: number };
type QuakeState = { charges_remaining: number; cooldown: number };

export type CardConfig = {
  // Key can be either "common" or "common,2"
  blockCards: Record<string, number>;
  polychromeBonus: number; // 0.15 when upgrade enabled
};

export class MonteCarloArchaeologySimulator {
  // Constants matching Python MC module
  ENRAGE_CHARGES = 5;
  ENRAGE_COOLDOWN = 60;
  ENRAGE_DAMAGE_BONUS = 0.2;
  ENRAGE_CRIT_DAMAGE_BONUS = 1.0;
  SUPER_CRIT_DMG_MULT_DEFAULT = 2.0;
  ULTRA_CRIT_DMG_MULT_DEFAULT = 3.0;
  FLURRY_COOLDOWN = 120;
  FLURRY_STAMINA_BONUS = 5;
  /** Fixed buff duration in seconds (no upgrades increase this). */
  FLURRY_DURATION_SECONDS = 5;
  QUAKE_CHARGES = 5;
  QUAKE_COOLDOWN = 180;
  QUAKE_DAMAGE_MULTIPLIER = 0.2;
  // Real stamina mod range is 3..10; avg 6.5 (used as default in Python MC stats fallback)
  MOD_STAMINA_BONUS_AVG = 6.5;
  SLOTS_PER_FLOOR = 24;

  private persistent_enrage_state: EnrageState | null = null;
  private persistent_flurry_cooldown: number | null = null;
  private persistent_quake_state: QuakeState | null = null;
  /** Speed mod: remaining hits at 2x speed carried from previous run (the only mod that is a duration buff). */
  private persistent_speed_mod_hits_remaining: number | null = null;

  constructor(private rng: Rng) {}

  getAbilityCooldownMultiplier(misc_card_level: number): number {
    if (misc_card_level === 1) return 0.97;
    if (misc_card_level === 2) return 0.94;
    if (misc_card_level === 3) return 0.9;
    return 1.0;
  }

  private calculateEffectiveDamage(stats: any, block_armor: number): number {
    const total_damage = Number(stats.total_damage ?? 0);
    const armor_pen = Number(stats.armor_pen ?? 0);
    const effective_armor = Math.max(0, block_armor - armor_pen);
    return Math.max(1, Math.round(total_damage - effective_armor));
  }

  private getCardLevel(cardCfg: CardConfig | null, blockType: BlockType, tier: BlockTier): number {
    if (!cardCfg) return 0;
    const byTier = cardCfg.blockCards[`${blockType},${tier}`];
    if (Number.isFinite(Number(byTier))) return Math.trunc(Number(byTier));
    const byType = cardCfg.blockCards[String(blockType)];
    if (Number.isFinite(Number(byType))) return Math.trunc(Number(byType));
    return 0;
  }

  private applyCardHp(cardCfg: CardConfig | null, blockType: BlockType, tier: BlockTier, hp: number): number {
    const lvl = this.getCardLevel(cardCfg, blockType, tier);
    if (lvl === 1) return Math.round(hp * 0.9);
    if (lvl === 2) return Math.round(hp * 0.8);
    if (lvl === 3) {
      const reduce = 0.35 + (cardCfg?.polychromeBonus ?? 0);
      return Math.round(hp * (1.0 - reduce));
    }
    return hp;
  }

  private getCardXpMult(cardCfg: CardConfig | null, blockType: BlockType, tier: BlockTier): number {
    const lvl = this.getCardLevel(cardCfg, blockType, tier);
    if (lvl === 1) return 1.1;
    if (lvl === 2) return 1.2;
    if (lvl === 3) return 1.0 + 0.35 + (cardCfg?.polychromeBonus ?? 0);
    return 1.0;
  }

  private simulateHitDamage(stats: any, block_armor: number, is_enrage: boolean, use_crit: boolean): number {
    let base_damage: number;
    if (is_enrage) {
      const enrage_damage_bonus = Number(stats.enrage_damage_bonus ?? this.ENRAGE_DAMAGE_BONUS);
      const enrage_total_damage = Math.round(Number(stats.total_damage ?? 0) * (1 + enrage_damage_bonus));
      const effective_armor = Math.max(0, block_armor - Number(stats.armor_pen ?? 0));
      base_damage = Math.max(1, enrage_total_damage - effective_armor);
    } else {
      base_damage = this.calculateEffectiveDamage(stats, block_armor);
    }

    if (!use_crit) return base_damage;

    const one_hit_chance = Number(stats.one_hit_chance ?? 0);
    if (one_hit_chance > 0 && this.rng() < one_hit_chance) return 999999;

    const crit_chance = Number(stats.crit_chance ?? 0);
    const is_crit = crit_chance > 0 && this.rng() < crit_chance;
    if (!is_crit) return base_damage;

    let crit_damage_mult = Number(stats.crit_damage ?? 1.5);
    if (is_enrage) {
      const enrage_crit_damage_bonus = Number(stats.enrage_crit_damage_bonus ?? this.ENRAGE_CRIT_DAMAGE_BONUS);
      crit_damage_mult *= 1 + enrage_crit_damage_bonus;
    }

    const super_crit_chance = Math.max(0, Math.min(1, Number(stats.super_crit_chance ?? 0)));
    const ultra_crit_chance = Math.max(0, Math.min(1, Number(stats.ultra_crit_chance ?? 0)));
    const super_crit_damage_bonus = Math.max(0, Number(stats.super_crit_damage ?? 0));
    const ultra_crit_damage_bonus = Math.max(0, Number(stats.ultra_crit_damage ?? 0));
    const super_mult = this.SUPER_CRIT_DMG_MULT_DEFAULT * (1 + super_crit_damage_bonus);
    const ultra_mult = Number(stats.ultra_crit_dmg_mult ?? this.ULTRA_CRIT_DMG_MULT_DEFAULT * (1 + ultra_crit_damage_bonus));

    if (this.rng() < super_crit_chance) {
      if (this.rng() < ultra_crit_chance) return Math.max(1, Math.round(base_damage * crit_damage_mult * ultra_mult));
      return Math.max(1, Math.round(base_damage * crit_damage_mult * super_mult));
    }
    return Math.max(1, Math.round(base_damage * crit_damage_mult));
  }

  /** speedModRemaining (hits) + flurryBuffSecondsRemaining (seconds): mutable refs. Speed mod = 2x (0.5s/hit), Flurry buff = 2x, both = 4x (0.25s/hit). Cooldowns tick in seconds. */
  private simulateBlockKill(
    stats: any,
    block_hp: number,
    block_armor: number,
    block_type: BlockType,
    tier: BlockTier,
    use_crit: boolean,
    enrage_state: EnrageState | null,
    effective_enrage_cooldown: number,
    speedModRemaining: { value: number },
    flurryBuffSecondsRemaining: { value: number },
  ): { hits: number; enrage_state: EnrageState | null; seconds_elapsed: number; speed_consumed: number } {
    let state = enrage_state;
    const enrage_was_enabled = state !== null;
    if (state === null) state = { charges_remaining: 0, cooldown: 0 };

    const ability_instacharge = Number(stats.ability_instacharge ?? 0);
    const effective_enrage_charges = Number(stats.enrage_charges ?? this.ENRAGE_CHARGES);

    let hits = 0;
    let damage_dealt = 0;
    let seconds_elapsed = 0;
    let speed_consumed = 0;
    while (damage_dealt < block_hp) {
      const speed_active = speedModRemaining.value > 0;
      const flurry_active = flurryBuffSecondsRemaining.value > 0;
      const seconds_this_hit = (speed_active ? 0.5 : 1.0) * (flurry_active ? 0.5 : 1.0);
      if (speed_active) {
        speedModRemaining.value -= 1;
        speed_consumed += 1;
      }
      if (flurry_active) {
        flurryBuffSecondsRemaining.value = Math.max(0, flurryBuffSecondsRemaining.value - seconds_this_hit);
      }

      let is_enrage = false;
      if (state.charges_remaining > 0) {
        is_enrage = true;
        state.charges_remaining -= 1;
      } else {
        state.cooldown -= seconds_this_hit;
        if (state.cooldown <= 0) {
          state.charges_remaining = effective_enrage_charges;
          state.cooldown = effective_enrage_cooldown;
          if (ability_instacharge > 0 && this.rng() < ability_instacharge) {
            state.charges_remaining += effective_enrage_charges;
          }
        }
      }

      damage_dealt += this.simulateHitDamage(stats, block_armor, is_enrage, use_crit);
      hits += 1;
      seconds_elapsed += seconds_this_hit;
      if (hits > 10000) break;
    }

    return { hits, enrage_state: enrage_was_enabled ? state : null, seconds_elapsed, speed_consumed };
  }

  private spawnBlockForSlot(stage: number, ascensionLevel: 0 | 1 | 2 = 0): BlockType | null {
    const ctx = { ascensionLevel };
    const raw = getSpawnRatesForStage(stage, ctx);
    const total_spawn_chance = Object.values(raw).reduce((a, b) => a + b, 0);
    if (this.rng() * 100.0 > total_spawn_chance) return null;

    const normalized = getNormalizedSpawnRates(stage, ctx);
    let r = this.rng();
    let cum = 0;
    for (const [bt, p] of Object.entries(normalized)) {
      cum += Number(p);
      if (r <= cum) return bt as BlockType;
    }
    return Object.keys(normalized)[0] ? (Object.keys(normalized)[0] as BlockType) : "dirt";
  }

  simulateRun(
    stats: any,
    starting_floor: number,
    options: McRunOptions,
    cardCfg: CardConfig | null,
  ): number | McRunMetrics {
    const { use_crit, enrage_enabled, flurry_enabled, quake_enabled, return_block_metrics, initialSpeedModHits } = options;
    const ascensionLevel = (options.ascensionLevel ?? 0) as 0 | 1 | 2;

    const max_stamina = Number(stats.max_stamina ?? 0);
    let stamina_remaining = max_stamina;
    let floors_cleared = 0;
    let current_floor = starting_floor;
    let max_stage_reached = starting_floor;
    const stamina_at_end_of_stage: Record<number, number> = {};

    const fragments_by_type: Record<string, number> = { common: 0, rare: 0, epic: 0, legendary: 0, mythic: 0, divine: 0 };
    const fragment_mult = Number(stats.fragment_mult ?? 1.0);
    const loot_mod_chance = Number(stats.loot_mod_chance ?? 0);
    const loot_mod_multiplier = Number(stats.loot_mod_multiplier ?? 3.5);
    const gleaming_floor_chance = Number(stats.gleaming_floor_chance ?? 0);
    const gleaming_floor_mult = Number(stats.gleaming_floor_mult ?? 3.0);

    let total_xp = 0;
    const xp_mult = Number(stats.xp_mult ?? 1.0);
    const exp_mod_chance = Number(stats.exp_mod_chance ?? 0);
    const exp_mod_multiplier = Number(stats.exp_mod_gain ?? 4.0);
    const arch_xp_mult = Number(stats.arch_xp_mult ?? 1.0);

    let total_hits = 0;
    let total_seconds_elapsed = 0;

    const track_blocks = Boolean(return_block_metrics);
    const block_hits_by_type: Record<string, number> = {};
    const blocks_destroyed_by_type: Record<string, number> = {};
    let max_hits_single_block = 0;
    let max_hits_single_block_type: string | null = null;

    const stamina_mod_chance = Number(stats.stamina_mod_chance ?? 0);
    const stamina_mod_gain = Number(stats.stamina_mod_gain ?? this.MOD_STAMINA_BONUS_AVG);

    const speed_mod_chance = Number(stats.speed_mod_chance ?? 0);
    const speed_mod_gain = Number(stats.speed_mod_gain ?? 10);
    let speed_mod_hits_remaining =
      initialSpeedModHits != null
        ? Math.max(0, Math.trunc(initialSpeedModHits))
        : Math.max(0, Math.trunc(this.persistent_speed_mod_hits_remaining ?? 0));
    let speed_mod_hits_consumed = 0;

    const misc_card_level = Number(stats.misc_card_level ?? 0);
    const cooldown_multiplier = this.getAbilityCooldownMultiplier(misc_card_level);

    const base_enrage_cooldown = this.ENRAGE_COOLDOWN + Number(stats.enrage_cooldown ?? 0) + Number(stats.ability_cooldown ?? 0);
    const base_flurry_cooldown = this.FLURRY_COOLDOWN + Number(stats.flurry_cooldown ?? 0) + Number(stats.ability_cooldown ?? 0);
    const base_quake_cooldown = this.QUAKE_COOLDOWN + Number(stats.quake_cooldown ?? 0) + Number(stats.ability_cooldown ?? 0);

    const effective_enrage_cooldown = Math.round(base_enrage_cooldown * cooldown_multiplier);
    const effective_flurry_cooldown = Math.round(base_flurry_cooldown * cooldown_multiplier);
    const effective_quake_cooldown = Math.round(base_quake_cooldown * cooldown_multiplier);

    const ability_instacharge = Number(stats.ability_instacharge ?? 0);
    const quake_charges = Number(stats.quake_charges ?? this.QUAKE_CHARGES);

    let flurry_stamina_bonus = 0;
    let flurry_duration_seconds = 0;
    let flurry_cooldown: number | null = null;
    let flurry_buff_seconds_remaining = 0;
    if (flurry_enabled) {
      flurry_stamina_bonus = this.FLURRY_STAMINA_BONUS + Number(stats.flurry_stamina_bonus ?? 0);
      flurry_duration_seconds = this.FLURRY_DURATION_SECONDS; // Fixed 5s; Flurry Buff only affects stamina on cast
      flurry_cooldown = this.persistent_flurry_cooldown ?? effective_flurry_cooldown;
    }

    let enrage_state: EnrageState | null = null;
    if (enrage_enabled) {
      enrage_state = this.persistent_enrage_state ? { ...this.persistent_enrage_state } : { charges_remaining: 0, cooldown: 0 };
    }

    let quake_state: QuakeState | null = null;
    if (quake_enabled) {
      quake_state = this.persistent_quake_state ? { ...this.persistent_quake_state } : { charges_remaining: 0, cooldown: 0 };
    }

    for (let floor_iter = 0; floor_iter < 1000; floor_iter += 1) {
      const block_mix = getBlockMixForFloor(current_floor, ascensionLevel);

      let stamina_for_floor = 0;
      let blocks_killed = 0;
      const floor_hits_by_type: Record<string, number> = {};
      const floor_blocks_by_type: Record<string, number> = {};

      // Gleaming Floor: one roll per floor; multiplies fragments from all blocks on that floor.
      const floor_gleam_mult =
        gleaming_floor_chance > 0 && this.rng() < gleaming_floor_chance ? gleaming_floor_mult : 1.0;

      // For Quake: track all blocks on the floor and their HP
      const floor_blocks: Array<{ block_type: BlockType; tier: BlockTier; armor: number; xp: number; fragment: number; hp: number }> = [];

      // Spawn all blocks
      for (let slot = 0; slot < this.SLOTS_PER_FLOOR; slot += 1) {
        const bt = this.spawnBlockForSlot(current_floor, ascensionLevel);
        if (!bt) continue;
        const bd = (block_mix as any)[bt] as { tier: BlockTier; armor: number; health: number; xp: number; fragment: number } | undefined;
        if (!bd) continue;
        const hp = this.applyCardHp(cardCfg, bt, bd.tier, bd.health);
        floor_blocks.push({ block_type: bt, tier: bd.tier, armor: bd.armor, xp: bd.xp, fragment: bd.fragment, hp });
      }

      // Kill blocks
      for (let idx = 0; idx < floor_blocks.length; idx += 1) {
        const b = floor_blocks[idx];
        if (b.hp <= 0) continue;

        const speedModRef = { value: speed_mod_hits_remaining };
        const flurryBuffRef = { value: flurry_buff_seconds_remaining };
        const kill = this.simulateBlockKill(stats, b.hp, b.armor, b.block_type, b.tier, use_crit, enrage_state, effective_enrage_cooldown, speedModRef, flurryBuffRef);
        const hits = kill.hits;
        enrage_state = kill.enrage_state;
        speed_mod_hits_remaining = speedModRef.value;
        flurry_buff_seconds_remaining = flurryBuffRef.value;
        const seconds_elapsed_block = kill.seconds_elapsed;
        const speed_consumed_this_block = kill.speed_consumed;
        speed_mod_hits_consumed += speed_consumed_this_block;
        total_seconds_elapsed += seconds_elapsed_block;
        stamina_for_floor += hits;
        total_hits += hits;
        blocks_killed += 1;

        if (track_blocks) {
          const key = `${b.block_type},${b.tier}`;
          floor_hits_by_type[key] = (floor_hits_by_type[key] ?? 0) + hits;
          floor_blocks_by_type[key] = (floor_blocks_by_type[key] ?? 0) + 1;
          if (hits > max_hits_single_block) {
            max_hits_single_block = hits;
            max_hits_single_block_type = key;
          }
        }

        // Flurry: cooldown in seconds. When it triggers, add stamina on cast + flurry_duration_seconds of 2x speed buff (stacking with speed mod = 4x).
        if (flurry_enabled && flurry_cooldown !== null) {
          flurry_cooldown -= seconds_elapsed_block;
          if (flurry_cooldown <= 0) {
            stamina_remaining = Math.min(max_stamina, stamina_remaining + flurry_stamina_bonus);
            flurry_buff_seconds_remaining += flurry_duration_seconds;
            flurry_cooldown = effective_flurry_cooldown;
            if (ability_instacharge > 0 && this.rng() < ability_instacharge) {
              stamina_remaining = Math.min(max_stamina, stamina_remaining + flurry_stamina_bonus);
              flurry_buff_seconds_remaining += flurry_duration_seconds;
              flurry_cooldown = effective_flurry_cooldown;
            }
          }
        }

        // XP (not dirt)
        if (b.block_type !== "dirt") {
          const exp_mod_active = this.rng() < exp_mod_chance;
          const exp_mult = exp_mod_active ? exp_mod_multiplier : 1.0;
          const card_xp_mult = this.getCardXpMult(cardCfg, b.block_type, b.tier);
          total_xp += b.xp * xp_mult * card_xp_mult * exp_mult * arch_xp_mult;
        }

        // Quake
        if (quake_state) {
          const is_active = quake_state.charges_remaining > 0;
          if (is_active) {
            const base_quake_damage_per_hit = Math.round(Number(stats.total_damage ?? 0) * this.QUAKE_DAMAGE_MULTIPLIER);
            const crit_chance = use_crit ? Number(stats.crit_chance ?? 0) : 0;
            const crit_damage_mult = use_crit ? Number(stats.crit_damage ?? 1.5) : 1.0;

            for (let j = 0; j < floor_blocks.length; j += 1) {
              if (j === idx) continue;
              const other = floor_blocks[j];
              if (other.hp <= 0) continue;
              let quake_total = 0;
              for (let h = 0; h < hits; h += 1) {
                const isCrit = crit_chance > 0 && this.rng() < crit_chance;
                quake_total += isCrit ? Math.round(base_quake_damage_per_hit * crit_damage_mult) : base_quake_damage_per_hit;
              }
              other.hp = Math.max(0, other.hp - quake_total);
            }

            quake_state.charges_remaining -= 1;
            if (quake_state.charges_remaining <= 0) quake_state.cooldown = effective_quake_cooldown;
          } else {
            quake_state.cooldown -= seconds_elapsed_block;
            if (quake_state.cooldown <= 0) {
              quake_state.charges_remaining = quake_charges;
              quake_state.cooldown = effective_quake_cooldown;
              if (ability_instacharge > 0 && this.rng() < ability_instacharge) quake_state.charges_remaining += quake_charges;
            }
          }
        }

        // Fragments (not dirt)
        if (b.block_type !== "dirt") {
          const loot_mod_active = this.rng() < loot_mod_chance;
          const loot_mult = loot_mod_active ? loot_mod_multiplier : 1.0;
          fragments_by_type[b.block_type] =
            (fragments_by_type[b.block_type] ?? 0) + b.fragment * fragment_mult * loot_mult * floor_gleam_mult;
        }

        // Stamina mod (actual range)
        if (stamina_mod_chance > 0 && this.rng() < stamina_mod_chance) {
          const stamina_gain = randUniform(this.rng, 3, 10);
          stamina_remaining = Math.min(max_stamina, stamina_remaining + stamina_gain);
        }

        // Speed mod proc: chance to add more hits at 2x speed (persists across runs)
        if (speed_mod_chance > 0 && this.rng() < speed_mod_chance) {
          speed_mod_hits_remaining += Math.max(0, Math.trunc(speed_mod_gain));
        }
      }

      // Clear floor?
      if (stamina_remaining >= stamina_for_floor) {
        stamina_remaining -= stamina_for_floor;
        floors_cleared += 1;
        current_floor += 1;
        max_stage_reached = current_floor;
        stamina_at_end_of_stage[current_floor - 1] = stamina_remaining;

        if (track_blocks) {
          for (const [bt, v] of Object.entries(floor_hits_by_type)) block_hits_by_type[bt] = (block_hits_by_type[bt] ?? 0) + v;
          for (const [bt, v] of Object.entries(floor_blocks_by_type)) blocks_destroyed_by_type[bt] = (blocks_destroyed_by_type[bt] ?? 0) + v;
        }
      } else {
        if (stamina_for_floor > 0) floors_cleared += stamina_remaining / stamina_for_floor;

        if (track_blocks) {
          const scale = stamina_for_floor > 0 ? Math.max(0, Math.min(1, stamina_remaining / stamina_for_floor)) : 0;
          for (const [bt, v] of Object.entries(floor_hits_by_type)) block_hits_by_type[bt] = (block_hits_by_type[bt] ?? 0) + v * scale;
          for (const [bt, v] of Object.entries(floor_blocks_by_type)) blocks_destroyed_by_type[bt] = (blocks_destroyed_by_type[bt] ?? 0) + v * scale;
        }
        break;
      }
    }

    // Persist ability states
    if (enrage_enabled && enrage_state) this.persistent_enrage_state = { ...enrage_state };
    else this.persistent_enrage_state = null;
    if (flurry_enabled && flurry_cooldown !== null) this.persistent_flurry_cooldown = flurry_cooldown;
    else this.persistent_flurry_cooldown = null;
    if (quake_enabled && quake_state) this.persistent_quake_state = { ...quake_state };
    else this.persistent_quake_state = null;

    // Persist speed mod only (stamina mod is one-time +stamina, not a duration buff)
    this.persistent_speed_mod_hits_remaining = Math.max(0, speed_mod_hits_remaining);

    const total_fragments = Object.values(fragments_by_type).reduce((a, b) => a + b, 0);
    // Run duration = sum of seconds per hit (1s base, 0.5s with speed or flurry, 0.25s with both = 4 attacks/sec)
    const run_duration_seconds = Math.max(1.0, total_seconds_elapsed);

    let block_breakdown: McBlockBreakdown | null = null;
    if (track_blocks) {
      const by_type: Record<string, { blocks_destroyed_est: number; time_seconds_est: number; avg_hits_per_block_est: number }> = {};
      const total_time = Object.values(block_hits_by_type).reduce((a, b) => a + b, 0);
      const allKeys = new Set([...Object.keys(block_hits_by_type), ...Object.keys(blocks_destroyed_by_type)]);
      for (const key of allKeys) {
        const blocks_est = Number(blocks_destroyed_by_type[key] ?? 0);
        const time_est = Number(block_hits_by_type[key] ?? 0);
        if (blocks_est <= 0 && time_est <= 0) continue;
        by_type[key] = {
          blocks_destroyed_est: blocks_est,
          time_seconds_est: time_est,
          avg_hits_per_block_est: blocks_est > 0 ? time_est / blocks_est : 0,
        };
      }
      let most_time_type: string | null = null;
      let most_avg_hits_type: string | null = null;
      const keys = Object.keys(by_type);
      if (keys.length) {
        most_time_type = keys.reduce((best, k) => (by_type[k].time_seconds_est > by_type[best].time_seconds_est ? k : best), keys[0]);
        most_avg_hits_type = keys.reduce((best, k) => (by_type[k].avg_hits_per_block_est > by_type[best].avg_hits_per_block_est ? k : best), keys[0]);
      }
      block_breakdown = {
        by_type,
        total_time_seconds_est: total_time,
        most_time_type,
        most_avg_hits_type,
        max_hits_single_block,
        max_hits_single_block_type,
        note: "Estimated for partial floors via scaled clear fraction.",
      };
    }

    return {
      floors_cleared,
      max_stage_reached,
      starting_floor,
      fragments: { ...fragments_by_type },
      total_fragments,
      xp_per_run: total_xp,
      run_duration_seconds,
      total_hits,
      stamina_at_end_of_stage: Object.keys(stamina_at_end_of_stage).length > 0 ? stamina_at_end_of_stage : undefined,
      ...(track_blocks ? { block_breakdown } : {}),
    };
  }
}

export function stageSimsSummary(args: {
  stats: any;
  starting_floor: number;
  n_sims: number;
  options: Omit<McRunOptions, "return_block_metrics">;
  cardCfg: CardConfig | null;
  seed: number;
}): { avg_max_stage: number; fragments_per_hour: number; xp_per_hour: number; stage_counts: Record<number, number>; max_stage_seen: number } {
  const rng = mulberry32(args.seed >>> 0);
  const sim = new MonteCarloArchaeologySimulator(rng);
  const stage_counts: Record<number, number> = {};
  let max_stage_seen = 0;
  let sum_max_stage = 0;
  let sum_fragments = 0;
  let sum_xp = 0;
  let sum_dur = 0;

  for (let i = 0; i < Math.max(0, Math.trunc(args.n_sims)); i += 1) {
    const r = sim.simulateRun(args.stats, args.starting_floor, { ...args.options, return_block_metrics: false }, args.cardCfg) as McRunMetrics;
    const max_stage = Number(r.max_stage_reached ?? 0);
    sum_max_stage += max_stage;
    const si = Math.trunc(max_stage);
    stage_counts[si] = (stage_counts[si] ?? 0) + 1;
    if (si > max_stage_seen) max_stage_seen = si;
    sum_fragments += Number(r.total_fragments ?? 0);
    sum_xp += Number(r.xp_per_run ?? 0);
    sum_dur += Number(r.run_duration_seconds ?? 1);
  }

  const n = Math.max(1, Math.trunc(args.n_sims));
  const avg_max_stage = sum_max_stage / n;
  const avg_frag = sum_fragments / n;
  const avg_xp = sum_xp / n;
  const avg_dur = sum_dur / n;
  const fragments_per_hour = avg_dur > 0 ? (avg_frag * 3600.0) / avg_dur : 0;
  const xp_per_hour = avg_dur > 0 ? (avg_xp * 3600.0) / avg_dur : 0;

  return { avg_max_stage, fragments_per_hour, xp_per_hour, stage_counts, max_stage_seen };
}

/** Like stageSimsSummary but also returns std and n for Welch tests. */
export function stageSimsSummaryWithVariance(args: {
  stats: any;
  starting_floor: number;
  n_sims: number;
  options: Omit<McRunOptions, "return_block_metrics">;
  cardCfg: CardConfig | null;
  seed: number;
}): {
  avg_max_stage: number;
  std_max_stage: number;
  fragments_per_hour: number;
  std_fragments_per_hour: number;
  xp_per_hour: number;
  std_xp_per_hour: number;
  n: number;
} {
  const rng = mulberry32(args.seed >>> 0);
  const sim = new MonteCarloArchaeologySimulator(rng);
  const max_stages: number[] = [];
  const frags_per_hour: number[] = [];
  const xps_per_hour: number[] = [];

  for (let i = 0; i < Math.max(0, Math.trunc(args.n_sims)); i += 1) {
    const r = sim.simulateRun(args.stats, args.starting_floor, { ...args.options, return_block_metrics: false }, args.cardCfg) as McRunMetrics;
    const max_stage = Number(r.max_stage_reached ?? 0);
    const dur = Math.max(1e-6, Number(r.run_duration_seconds ?? 1));
    const runs_per_hour = 3600 / dur;
    max_stages.push(max_stage);
    frags_per_hour.push(Number(r.total_fragments ?? 0) * runs_per_hour);
    xps_per_hour.push(Number(r.xp_per_run ?? 0) * runs_per_hour);
  }

  const n = max_stages.length;
  if (n === 0) {
    return { avg_max_stage: 0, std_max_stage: 0, fragments_per_hour: 0, std_fragments_per_hour: 0, xp_per_hour: 0, std_xp_per_hour: 0, n: 0 };
  }
  const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / n;
  const variance = (xs: number[], m: number) => xs.reduce((s, x) => s + (x - m) ** 2, 0) / Math.max(1, n - 1);
  const std = (xs: number[], m: number) => Math.sqrt(variance(xs, m));
  const avg_max_stage = mean(max_stages);
  const avg_frag = mean(frags_per_hour);
  const avg_xp = mean(xps_per_hour);
  return {
    avg_max_stage,
    std_max_stage: std(max_stages, avg_max_stage),
    fragments_per_hour: avg_frag,
    std_fragments_per_hour: std(frags_per_hour, avg_frag),
    xp_per_hour: avg_xp,
    std_xp_per_hour: std(xps_per_hour, avg_xp),
    n,
  };
}

export function stageSimsDetailed(args: {
  stats: any;
  starting_floor: number;
  n_sims: number;
  options: Omit<McRunOptions, "return_block_metrics">;
  cardCfg: CardConfig | null;
  seed: number;
  includeBlockMetrics: boolean;
}): { max_stage_samples: number[]; metrics_samples: McRunMetrics[] } {
  const rng = mulberry32(args.seed >>> 0);
  const sim = new MonteCarloArchaeologySimulator(rng);
  const max_stage_samples: number[] = [];
  const metrics_samples: McRunMetrics[] = [];
  for (let i = 0; i < Math.max(0, Math.trunc(args.n_sims)); i += 1) {
    const r = sim.simulateRun(
      args.stats,
      args.starting_floor,
      { ...args.options, return_block_metrics: Boolean(args.includeBlockMetrics) },
      args.cardCfg,
    ) as McRunMetrics;
    max_stage_samples.push(Number(r.max_stage_reached ?? 0));
    metrics_samples.push(r);
  }
  return { max_stage_samples, metrics_samples };
}

const FRAG_TYPES_ORDER = ARCH_FRAGMENT_TYPES;

/** Aggregated block breakdown for UI (time share %, destroyed/run, avg hits/block). */
export type BlockBreakdownAggregate = {
  by_type: Record<
    string,
    {
      blocks_destroyed_per_run: number;
      time_seconds_per_run: number;
      time_share: number; // 0..1
      avg_hits_per_block: number;
    }
  >;
  total_time_seconds_per_run: number;
  most_time_type: string | null;
  most_avg_hits_type: string | null;
  note: string | null;
};

export function blockBreakdownSummary(args: {
  stats: any;
  starting_floor: number;
  n_sims: number;
  options: Omit<McRunOptions, "return_block_metrics">;
  cardCfg: CardConfig | null;
  seed: number;
}): BlockBreakdownAggregate {
  const out = stageSimsDetailed({
    ...args,
    includeBlockMetrics: true,
  });
  const samples = out.metrics_samples ?? [];
  const timeSumByType: Record<string, number> = {};
  const blocksSumByType: Record<string, number> = {};
  let runsWithData = 0;
  let note: string | null = null;

  for (const m of samples) {
    const bb = m?.block_breakdown;
    if (!bb?.by_type || typeof bb.by_type !== "object") continue;
    runsWithData += 1;
    note = note ?? bb.note ?? null;
    for (const [bt, vals] of Object.entries(bb.by_type)) {
      if (!vals || typeof vals !== "object") continue;
      const t = Number(vals.time_seconds_est ?? 0) || 0;
      const b = Number(vals.blocks_destroyed_est ?? 0) || 0;
      timeSumByType[bt] = (timeSumByType[bt] ?? 0) + t;
      blocksSumByType[bt] = (blocksSumByType[bt] ?? 0) + b;
    }
  }

  if (runsWithData <= 0) {
    return { by_type: {}, total_time_seconds_per_run: 0, most_time_type: null, most_avg_hits_type: null, note };
  }

  const totalTimeAvg =
    Object.values(timeSumByType).reduce((a, b) => a + b, 0) / runsWithData;
  const blockTypeOrder: BlockType[] = [...BLOCK_TYPES];
  const allKeys = [...new Set([...Object.keys(timeSumByType), ...Object.keys(blocksSumByType)])];
  const sortedKeys = allKeys.sort((a, b) => {
    const [typeA, tierA] = a.includes(",") ? (a.split(",") as [string, string]) : [a, "1"];
    const [typeB, tierB] = b.includes(",") ? (b.split(",") as [string, string]) : [b, "1"];
    const idxA = blockTypeOrder.indexOf(typeA as BlockType);
    const idxB = blockTypeOrder.indexOf(typeB as BlockType);
    if (idxA !== idxB) return idxA - idxB;
    return Number(tierA) - Number(tierB);
  });
  const by_type: BlockBreakdownAggregate["by_type"] = {};

  for (const key of sortedKeys) {
    const tAvg = (timeSumByType[key] ?? 0) / runsWithData;
    const bAvg = (blocksSumByType[key] ?? 0) / runsWithData;
    if (tAvg <= 0 && bAvg <= 0) continue;
    by_type[key] = {
      blocks_destroyed_per_run: bAvg,
      time_seconds_per_run: tAvg,
      time_share: totalTimeAvg > 0 ? tAvg / totalTimeAvg : 0,
      avg_hits_per_block: bAvg > 0 ? tAvg / bAvg : 0,
    };
  }

  const keys = Object.keys(by_type);
  const most_time_type = keys.length
    ? keys.reduce((best, k) => (by_type[k].time_seconds_per_run > by_type[best].time_seconds_per_run ? k : best), keys[0])
    : null;
  const most_avg_hits_type = keys.length
    ? keys.reduce((best, k) => (by_type[k].avg_hits_per_block > by_type[best].avg_hits_per_block ? k : best), keys[0])
    : null;

  return {
    by_type,
    total_time_seconds_per_run: totalTimeAvg,
    most_time_type,
    most_avg_hits_type,
    note,
  };
}

export function fragmentSimsSummary(args: {
  stats: any;
  starting_floor: number;
  n_sims: number;
  options: Omit<McRunOptions, "return_block_metrics">;
  cardCfg: CardConfig | null;
  seed: number;
  target_frag: string;
}): {
  avg_frag_per_hour: number;
  xp_per_hour: number;
  frag_per_hour_by_type: Record<string, number>;
} {
  const rng = mulberry32(args.seed >>> 0);
  const sim = new MonteCarloArchaeologySimulator(rng);
  const t = String(args.target_frag);
  const sumsByType: Record<string, number> = {};
  for (const k of FRAG_TYPES_ORDER) sumsByType[k] = 0;
  let sumXp = 0;
  let sumDur = 0;
  for (let i = 0; i < Math.max(0, Math.trunc(args.n_sims)); i += 1) {
    const r = sim.simulateRun(args.stats, args.starting_floor, { ...args.options, return_block_metrics: false }, args.cardCfg) as McRunMetrics;
    const dur = Number(r.run_duration_seconds ?? 1);
    const runs_per_hour = dur > 0 ? 3600.0 / dur : 0;
    for (const k of FRAG_TYPES_ORDER) {
      const frag = Number(r.fragments?.[k] ?? 0);
      sumsByType[k] += frag * runs_per_hour;
    }
    sumXp += Number(r.xp_per_run ?? 0);
    sumDur += dur;
  }
  const n = Math.max(1, Math.trunc(args.n_sims));
  const frag_per_hour_by_type: Record<string, number> = {};
  for (const k of FRAG_TYPES_ORDER) frag_per_hour_by_type[k] = sumsByType[k] / n;
  const avg_frag_per_hour = frag_per_hour_by_type[t] ?? 0;
  const xp_per_hour = sumDur > 0 ? (sumXp * 3600.0) / sumDur : 0;
  return { avg_frag_per_hour, xp_per_hour, frag_per_hour_by_type };
}

/** Like fragmentSimsSummary but also returns std and n for primary and by-type (for Welch). */
export function fragmentSimsSummaryWithVariance(args: {
  stats: any;
  starting_floor: number;
  n_sims: number;
  options: Omit<McRunOptions, "return_block_metrics">;
  cardCfg: CardConfig | null;
  seed: number;
  target_frag: string;
}): {
  avg_frag_per_hour: number;
  std_frag_per_hour: number;
  xp_per_hour: number;
  std_xp_per_hour: number;
  frag_per_hour_by_type: Record<string, number>;
  std_by_type: Record<string, number>;
  n: number;
} {
  const rng = mulberry32(args.seed >>> 0);
  const sim = new MonteCarloArchaeologySimulator(rng);
  const t = String(args.target_frag);
  const runs: { fragByType: Record<string, number>; xpPerHour: number }[] = [];

  for (let i = 0; i < Math.max(0, Math.trunc(args.n_sims)); i += 1) {
    const r = sim.simulateRun(args.stats, args.starting_floor, { ...args.options, return_block_metrics: false }, args.cardCfg) as McRunMetrics;
    const dur = Math.max(1e-6, Number(r.run_duration_seconds ?? 1));
    const runs_per_hour = 3600 / dur;
    const fragByType: Record<string, number> = {};
    for (const k of FRAG_TYPES_ORDER) {
      fragByType[k] = Number(r.fragments?.[k] ?? 0) * runs_per_hour;
    }
    runs.push({
      fragByType,
      xpPerHour: Number(r.xp_per_run ?? 0) * runs_per_hour,
    });
  }

  const n = runs.length;
  if (n === 0) {
    const empty: Record<string, number> = {};
    for (const k of FRAG_TYPES_ORDER) empty[k] = 0;
    return { avg_frag_per_hour: 0, std_frag_per_hour: 0, xp_per_hour: 0, std_xp_per_hour: 0, frag_per_hour_by_type: empty, std_by_type: empty, n: 0 };
  }
  const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
  const variance = (xs: number[], m: number) => xs.reduce((s, x) => s + (x - m) ** 2, 0) / Math.max(1, xs.length - 1);
  const std = (xs: number[], m: number) => Math.sqrt(variance(xs, m));

  const primaryVals = runs.map((row) => row.fragByType[t] ?? 0);
  const xpVals = runs.map((row) => row.xpPerHour);
  const frag_per_hour_by_type: Record<string, number> = {};
  const std_by_type: Record<string, number> = {};
  for (const k of FRAG_TYPES_ORDER) {
    const vals = runs.map((row) => row.fragByType[k] ?? 0);
    frag_per_hour_by_type[k] = mean(vals);
    std_by_type[k] = std(vals, frag_per_hour_by_type[k]);
  }
  const avg_frag_per_hour = mean(primaryVals);
  const xp_per_hour = mean(xpVals);

  return {
    avg_frag_per_hour,
    std_frag_per_hour: std(primaryVals, avg_frag_per_hour),
    xp_per_hour,
    std_xp_per_hour: std(xpVals, xp_per_hour),
    frag_per_hour_by_type,
    std_by_type,
    n,
  };
}
