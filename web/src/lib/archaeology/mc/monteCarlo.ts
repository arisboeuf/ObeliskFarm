import { getBlockMixForFloor } from "../blockStats";
import { getNormalizedSpawnRates, getSpawnRatesForStage } from "../spawnRates";
import type { BlockTier, BlockType } from "../types";
import type { Rng } from "./prng";
import { mulberry32, randUniform } from "./prng";

// Ported from ObeliskGemEV/archaeology/monte_carlo_crit.py (adapted for web + tiered cards).

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
};

export type McRunOptions = {
  use_crit: boolean;
  enrage_enabled: boolean;
  flurry_enabled: boolean;
  quake_enabled: boolean;
  return_block_metrics: boolean;
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
  QUAKE_CHARGES = 5;
  QUAKE_COOLDOWN = 180;
  QUAKE_DAMAGE_MULTIPLIER = 0.2;
  // Real stamina mod range is 3..10; avg 6.5 (used as default in Python MC stats fallback)
  MOD_STAMINA_BONUS_AVG = 6.5;
  SLOTS_PER_FLOOR = 24;

  private persistent_enrage_state: EnrageState | null = null;
  private persistent_flurry_cooldown: number | null = null;
  private persistent_quake_state: QuakeState | null = null;

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
    return Math.max(1, Math.trunc(total_damage - effective_armor));
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
    if (lvl === 1) return Math.trunc(hp * 0.9);
    if (lvl === 2) return Math.trunc(hp * 0.8);
    if (lvl === 3) {
      const reduce = 0.35 + (cardCfg?.polychromeBonus ?? 0);
      return Math.trunc(hp * (1.0 - reduce));
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
      const enrage_total_damage = Math.trunc(Number(stats.total_damage ?? 0) * (1 + enrage_damage_bonus));
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
    const super_mult = this.SUPER_CRIT_DMG_MULT_DEFAULT * (1 + super_crit_damage_bonus);
    const ultra_mult = this.ULTRA_CRIT_DMG_MULT_DEFAULT * (1 + super_crit_damage_bonus);

    if (this.rng() < super_crit_chance) {
      if (this.rng() < ultra_crit_chance) return Math.max(1, Math.trunc(base_damage * crit_damage_mult * ultra_mult));
      return Math.max(1, Math.trunc(base_damage * crit_damage_mult * super_mult));
    }
    return Math.max(1, Math.trunc(base_damage * crit_damage_mult));
  }

  private simulateBlockKill(
    stats: any,
    block_hp: number,
    block_armor: number,
    block_type: BlockType,
    tier: BlockTier,
    use_crit: boolean,
    enrage_state: EnrageState | null,
    effective_enrage_cooldown: number,
  ): { hits: number; enrage_state: EnrageState | null } {
    let state = enrage_state;
    const enrage_was_enabled = state !== null;
    if (state === null) state = { charges_remaining: 0, cooldown: 0 };

    const ability_instacharge = Number(stats.ability_instacharge ?? 0);
    const effective_enrage_charges = Number(stats.enrage_charges ?? this.ENRAGE_CHARGES);

    let hits = 0;
    let damage_dealt = 0;
    while (damage_dealt < block_hp) {
      let is_enrage = false;
      if (state.charges_remaining > 0) {
        is_enrage = true;
        state.charges_remaining -= 1;
      } else {
        state.cooldown -= 1;
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
      if (hits > 10000) break;
    }

    return { hits, enrage_state: enrage_was_enabled ? state : null };
  }

  private spawnBlockForSlot(stage: number): BlockType | null {
    const raw = getSpawnRatesForStage(stage);
    const total_spawn_chance = Object.values(raw).reduce((a, b) => a + b, 0);
    if (this.rng() * 100.0 > total_spawn_chance) return null;

    const normalized = getNormalizedSpawnRates(stage);
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
    const { use_crit, enrage_enabled, flurry_enabled, quake_enabled, return_block_metrics } = options;

    const max_stamina = Number(stats.max_stamina ?? 0);
    let stamina_remaining = max_stamina;
    let floors_cleared = 0;
    let current_floor = starting_floor;
    let max_stage_reached = starting_floor;

    const fragments_by_type: Record<string, number> = { common: 0, rare: 0, epic: 0, legendary: 0, mythic: 0 };
    const fragment_mult = Number(stats.fragment_mult ?? 1.0);
    const loot_mod_chance = Number(stats.loot_mod_chance ?? 0);
    const loot_mod_multiplier = Number(stats.loot_mod_multiplier ?? 3.5);

    let total_xp = 0;
    const xp_mult = Number(stats.xp_mult ?? 1.0);
    const exp_mod_chance = Number(stats.exp_mod_chance ?? 0);
    const exp_mod_multiplier = Number(stats.exp_mod_gain ?? 4.0);
    const arch_xp_mult = Number(stats.arch_xp_mult ?? 1.0);

    let total_hits = 0;

    const track_blocks = Boolean(return_block_metrics);
    const block_hits_by_type: Record<string, number> = {};
    const blocks_destroyed_by_type: Record<string, number> = {};
    let max_hits_single_block = 0;
    let max_hits_single_block_type: string | null = null;

    const stamina_mod_chance = Number(stats.stamina_mod_chance ?? 0);
    const stamina_mod_gain = Number(stats.stamina_mod_gain ?? this.MOD_STAMINA_BONUS_AVG);

    const misc_card_level = Number(stats.misc_card_level ?? 0);
    const cooldown_multiplier = this.getAbilityCooldownMultiplier(misc_card_level);

    const base_enrage_cooldown = this.ENRAGE_COOLDOWN + Number(stats.enrage_cooldown ?? 0) + Number(stats.ability_cooldown ?? 0);
    const base_flurry_cooldown = this.FLURRY_COOLDOWN + Number(stats.flurry_cooldown ?? 0) + Number(stats.ability_cooldown ?? 0);
    const base_quake_cooldown = this.QUAKE_COOLDOWN + Number(stats.quake_cooldown ?? 0) + Number(stats.ability_cooldown ?? 0);

    const effective_enrage_cooldown = Math.trunc(base_enrage_cooldown * cooldown_multiplier);
    const effective_flurry_cooldown = Math.trunc(base_flurry_cooldown * cooldown_multiplier);
    const effective_quake_cooldown = Math.trunc(base_quake_cooldown * cooldown_multiplier);

    const ability_instacharge = Number(stats.ability_instacharge ?? 0);
    const quake_charges = Number(stats.quake_charges ?? this.QUAKE_CHARGES);

    let flurry_stamina_bonus = 0;
    let flurry_cooldown: number | null = null;
    if (flurry_enabled) {
      flurry_stamina_bonus = this.FLURRY_STAMINA_BONUS + Number(stats.flurry_stamina_bonus ?? 0);
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
      const block_mix = getBlockMixForFloor(current_floor);

      let stamina_for_floor = 0;
      let blocks_killed = 0;
      const floor_hits_by_type: Record<string, number> = {};
      const floor_blocks_by_type: Record<string, number> = {};

      // For Quake: track all blocks on the floor and their HP
      const floor_blocks: Array<{ block_type: BlockType; tier: BlockTier; armor: number; xp: number; fragment: number; hp: number }> = [];

      // Spawn all blocks
      for (let slot = 0; slot < this.SLOTS_PER_FLOOR; slot += 1) {
        const bt = this.spawnBlockForSlot(current_floor);
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

        const kill = this.simulateBlockKill(stats, b.hp, b.armor, b.block_type, b.tier, use_crit, enrage_state, effective_enrage_cooldown);
        const hits = kill.hits;
        enrage_state = kill.enrage_state;
        stamina_for_floor += hits;
        total_hits += hits;
        blocks_killed += 1;

        if (track_blocks) {
          floor_hits_by_type[b.block_type] = (floor_hits_by_type[b.block_type] ?? 0) + hits;
          floor_blocks_by_type[b.block_type] = (floor_blocks_by_type[b.block_type] ?? 0) + 1;
          if (hits > max_hits_single_block) {
            max_hits_single_block = hits;
            max_hits_single_block_type = b.block_type;
          }
        }

        // Flurry cooldown and stamina bonus
        if (flurry_enabled && flurry_cooldown !== null) {
          flurry_cooldown -= hits;
          if (flurry_cooldown <= 0) {
            stamina_remaining = Math.min(max_stamina, stamina_remaining + flurry_stamina_bonus);
            flurry_cooldown = effective_flurry_cooldown;
            if (ability_instacharge > 0 && this.rng() < ability_instacharge) {
              stamina_remaining = Math.min(max_stamina, stamina_remaining + flurry_stamina_bonus);
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
            const base_quake_damage_per_hit = Math.trunc(Number(stats.total_damage ?? 0) * this.QUAKE_DAMAGE_MULTIPLIER);
            const crit_chance = use_crit ? Number(stats.crit_chance ?? 0) : 0;
            const crit_damage_mult = use_crit ? Number(stats.crit_damage ?? 1.5) : 1.0;

            for (let j = 0; j < floor_blocks.length; j += 1) {
              if (j === idx) continue;
              const other = floor_blocks[j];
              if (other.hp <= 0) continue;
              let quake_total = 0;
              for (let h = 0; h < hits; h += 1) {
                const isCrit = crit_chance > 0 && this.rng() < crit_chance;
                quake_total += isCrit ? Math.trunc(base_quake_damage_per_hit * crit_damage_mult) : base_quake_damage_per_hit;
              }
              other.hp = Math.max(0, other.hp - quake_total);
            }

            quake_state.charges_remaining -= 1;
            if (quake_state.charges_remaining <= 0) quake_state.cooldown = effective_quake_cooldown;
          } else {
            quake_state.cooldown -= hits;
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
          fragments_by_type[b.block_type] = (fragments_by_type[b.block_type] ?? 0) + b.fragment * fragment_mult * loot_mult;
        }

        // Stamina mod (actual range)
        if (stamina_mod_chance > 0 && this.rng() < stamina_mod_chance) {
          const stamina_gain = randUniform(this.rng, 3, 10);
          stamina_remaining = Math.min(max_stamina, stamina_remaining + stamina_gain);
        }
      }

      // Clear floor?
      if (stamina_remaining >= stamina_for_floor) {
        stamina_remaining -= stamina_for_floor;
        floors_cleared += 1;
        current_floor += 1;
        max_stage_reached = current_floor;

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

    const total_fragments = Object.values(fragments_by_type).reduce((a, b) => a + b, 0);
    const run_duration_seconds = Math.max(1.0, total_hits);

    let block_breakdown: McBlockBreakdown | null = null;
    if (track_blocks) {
      const ordered: BlockType[] = ["dirt", "common", "rare", "epic", "legendary", "mythic"];
      const by_type: Record<string, { blocks_destroyed_est: number; time_seconds_est: number; avg_hits_per_block_est: number }> = {};
      const total_time = Object.values(block_hits_by_type).reduce((a, b) => a + b, 0);
      for (const bt of ordered) {
        const blocks_est = Number(blocks_destroyed_by_type[bt] ?? 0);
        const time_est = Number(block_hits_by_type[bt] ?? 0);
        if (blocks_est <= 0 && time_est <= 0) continue;
        by_type[bt] = {
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

export function fragmentSimsSummary(args: {
  stats: any;
  starting_floor: number;
  n_sims: number;
  options: Omit<McRunOptions, "return_block_metrics">;
  cardCfg: CardConfig | null;
  seed: number;
  target_frag: string;
}): { avg_frag_per_hour: number } {
  const rng = mulberry32(args.seed >>> 0);
  const sim = new MonteCarloArchaeologySimulator(rng);
  let sum = 0;
  const t = String(args.target_frag);
  for (let i = 0; i < Math.max(0, Math.trunc(args.n_sims)); i += 1) {
    const r = sim.simulateRun(args.stats, args.starting_floor, { ...args.options, return_block_metrics: false }, args.cardCfg) as McRunMetrics;
    const frag = Number(r.fragments?.[t] ?? 0);
    const dur = Number(r.run_duration_seconds ?? 1);
    const runs_per_hour = dur > 0 ? 3600.0 / dur : 0;
    sum += frag * runs_per_hour;
  }
  const n = Math.max(1, Math.trunc(args.n_sims));
  return { avg_frag_per_hour: sum / n };
}

