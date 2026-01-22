"""
Event simulation logic.
Combat simulation, upgrade application, and calculations.
"""

import random
import copy
from typing import List, Dict, Tuple

from .stats import PlayerStats, EnemyStats
from .constants import COSTS, CAP_UPGRADES, MAX_LEVELS


def round_number(number: float, precision: int = 0) -> float:
    """Round a number to specified precision"""
    return round(number, precision)


def apply_upgrades(upgrades: Dict[int, List[int]], player: PlayerStats, 
                   enemy: EnemyStats, prestiges: int, gem_ups: List[int]) -> Tuple[PlayerStats, EnemyStats]:
    """Apply all upgrades to player and enemy stats
    
    Args:
        upgrades: Dict mapping tier (1-4) to list of upgrade levels
        player: Base player stats
        enemy: Base enemy stats
        prestiges: Current prestige count
        gem_ups: List of 4 gem upgrade levels [atk%, hp%, game_speed, 2x_currency]
    
    Returns:
        Tuple of (modified_player, modified_enemy)
    """
    p = copy.deepcopy(player)
    e = copy.deepcopy(enemy)
    
    # Tier 1 upgrades (cost: Mat 1 / Coins)
    if 1 in upgrades:
        u = upgrades[1]
        p.atk += u[0]  # +1 Atk Dmg
        p.health += 2 * u[1]  # +2 Max Hp
        p.atk_speed += 0.02 * u[2]  # +0.02 Atk Spd
        p.walk_speed += 0.03 * u[3]  # +0.03 Move Spd
        p.game_speed += 0.03 * u[4]  # +3% Event Game Spd (wiki verified)
        p.crit += u[5]  # +1% Crit Chance
        p.crit_dmg += 0.1 * u[5]  # +0.10 Crit Dmg
        p.atk += u[6]  # +1 Atk Dmg
        p.health += 2 * u[6]  # +2 Max Hp
        # u[7] is cap upgrade (no direct stat effect)
        p.prestige_bonus_scale += 0.01 * u[8]  # +1% Prestige Bonus
        p.health += 3 * u[9]  # +3 Max Hp
        p.atk += 3 * u[9]  # +3 Atk Dmg
    
    # Tier 2 upgrades (cost: Mat 2)
    if 2 in upgrades:
        u = upgrades[2]
        p.health += 3 * u[0]  # +3 Max Hp
        e.atk_speed -= 0.02 * u[1]  # -0.02 Enemy Atk Spd
        e.atk -= u[2]  # -1 Enemy Atk Dmg (VERY STRONG early game!)
        e.crit -= u[3]  # -1% Enemy Crit Chance
        e.crit_dmg -= 0.10 * u[3]  # -0.10 Enemy Crit Dmg
        p.atk += u[4]  # +1 Atk Dmg
        p.atk_speed += 0.01 * u[4]  # +0.01 Atk Spd
        # u[5] is cap upgrade (no direct stat effect)
        p.prestige_bonus_scale += 0.02 * u[6]  # +2% Prestige Bonus
    
    # Tier 3 upgrades (cost: Mat 3)
    if 3 in upgrades:
        u = upgrades[3]
        p.atk += 2 * u[0]  # +2 Atk Dmg
        p.atk_speed += 0.02 * u[1]  # +0.02 Atk Spd
        p.crit += u[2]  # +1% Crit Chance
        p.game_speed += 0.05 * u[3]  # +5% Event Game Spd (wiki verified)
        p.atk += 3 * u[4]  # +3 Atk Dmg
        p.health += 3 * u[4]  # +3 Max Hp
        # u[5] is cap upgrade (no direct stat effect)
        p.x5_money += 3 * u[6]  # +3% 5x Drop Chance
        p.health += 5 * u[7]  # +5 Max Hp
        p.atk_speed += 0.03 * u[7]  # +0.03 Atk Spd
    
    # Tier 4 upgrades (cost: Mat 4)
    if 4 in upgrades:
        u = upgrades[4]
        p.block_chance += 0.01 * u[0]  # +1% Block Chance
        p.health += 5 * u[1]  # +5 Max Hp
        p.crit_dmg += 0.1 * u[2]  # +0.10 Crit Dmg
        e.crit_dmg -= 0.1 * u[2]  # -0.10 Enemy Crit Dmg
        p.atk_speed += 0.02 * u[3]  # +0.02 Atk Spd
        p.walk_speed += 0.02 * u[3]  # +0.02 Move Spd
        p.atk += 4 * u[4]  # +4 Atk Dmg
        p.health += 4 * u[4]  # +4 Max Hp
        # u[5] is cap upgrade (no direct stat effect)
        # u[6] is cap of cap upgrade (no direct stat effect)
        p.health += 10 * u[7]  # +10 Max Hp
        p.atk_speed += 0.05 * u[7]  # +0.05 Atk Spd
    
    # Apply prestige and gem multipliers
    p.atk = round_number(p.atk * (1 + p.prestige_bonus_scale * prestiges) * (1 + 0.1 * gem_ups[0]))
    p.health = round_number(p.health * (1 + p.prestige_bonus_scale * prestiges) * (1 + 0.1 * gem_ups[1]))
    p.game_speed = p.game_speed + gem_ups[2]
    p.x2_money = p.x2_money + gem_ups[3]
    
    return p, e


def simulate_event_run(player: PlayerStats, enemy: EnemyStats) -> Tuple[int, int, float]:
    """
    Simulate a single event run.
    
    The event has waves, each wave has 5 sub-waves (enemies).
    Player attacks enemies, enemies attack back.
    Run ends when player HP reaches 0.
    
    Returns: (wave, subwave, time_in_seconds)
        - wave: The wave number where player died
        - subwave: The sub-wave (5=first enemy, 1=last enemy)
        - time: Total time of the run in seconds
    """
    player_hp = player.health
    time = 0.0
    p_atk_prog = 0.0  # Player attack progress (0 to 1)
    e_atk_prog = 0.0  # Enemy attack progress (0 to 1)
    
    wave = 0
    final_subwave = 0
    
    while player_hp > 0:
        wave += 1
        for subwave in range(5, 0, -1):
            if player_hp <= 0:
                break
            
            # Enemy stats scale with wave
            enemy_hp = enemy.base_health + enemy.health_scaling * wave
            
            while enemy_hp > 0 and player_hp > 0:
                # Calculate time until next attack for each
                p_atk_time_left = (1 - p_atk_prog) / player.atk_speed
                e_atk_time_left = (1 - e_atk_prog) / (enemy.atk_speed + wave * 0.02)
                
                if p_atk_time_left > e_atk_time_left:
                    # Enemy attacks first
                    p_atk_prog += (e_atk_time_left / (enemy.atk_speed + wave * 0.02)) * player.atk_speed
                    e_atk_prog -= 1
                    
                    # Calculate enemy damage
                    dmg = max(1, round_number(enemy.atk + wave * enemy.atk_scaling))
                    
                    # Enemy crit check
                    enemy_crit_chance = enemy.crit + wave
                    if enemy_crit_chance > 0 and random.random() * 100 <= enemy_crit_chance:
                        enemy_crit_mult = enemy.crit_dmg + enemy.crit_dmg_scaling * wave
                        if enemy_crit_mult > 1:
                            dmg = round_number(dmg * enemy_crit_mult)
                    
                    # Block check
                    if player.block_chance > 0 and random.random() <= player.block_chance:
                        dmg = 0
                    
                    player_hp -= dmg
                    time += enemy.default_atk_time * (e_atk_time_left / (enemy.atk_speed + wave * 0.02))
                else:
                    # Player attacks first
                    e_atk_prog += (p_atk_time_left / player.atk_speed) * (enemy.atk_speed + wave * 0.02)
                    p_atk_prog -= 1
                    
                    dmg = player.atk
                    
                    # Player crit check
                    if player.crit > 0 and random.random() * 100 <= player.crit:
                        dmg = round_number(player.atk * player.crit_dmg)
                    
                    enemy_hp -= dmg
                    time += player.default_atk_time * (p_atk_time_left / player.atk_speed)
            
            # Walk time between enemies
            time += player.default_walk_time / player.walk_speed
            
            if player_hp <= 0 and final_subwave == 0:
                final_subwave = subwave
    
    # Apply game speed multiplier to total time
    time = time / player.game_speed
    return wave, final_subwave, time


def run_full_simulation(player: PlayerStats, enemy: EnemyStats, 
                        runs: int = 1000) -> Tuple[List[Tuple[int, int, float]], float, float]:
    """
    Run multiple event simulations and return statistics.
    
    Args:
        player: Player stats
        enemy: Enemy stats  
        runs: Number of simulation runs
    
    Returns: (sorted_results, avg_distance, avg_time)
        - sorted_results: List of (wave, subwave, time) sorted by distance
        - avg_distance: Average wave reached (as decimal)
        - avg_time: Average run time in seconds
    """
    results = []
    total_distance = 0.0
    total_time = 0.0
    
    for _ in range(runs):
        wave, subwave, time = simulate_event_run(player, enemy)
        results.append((wave, subwave, time))
        total_distance += wave + 1 - (subwave * 0.2)
        total_time += time
    
    results.sort(key=lambda x: x[0] + 1 - x[1] * 0.2)
    avg_distance = total_distance / runs
    avg_time = total_time / runs
    
    return results, avg_distance, avg_time


def calculate_materials(wave: int, player: PlayerStats) -> Tuple[float, float, float, float]:
    """Calculate materials gained from reaching a wave
    
    Materials are based on triangular numbers:
    - Mat 1: Sum of 1 to wave (every wave)
    - Mat 2: Sum of 1 to wave//5 (every 5 waves)
    - Mat 3: Sum of 1 to wave//10 (every 10 waves)
    - Mat 4: Sum of 1 to wave//15 (every 15 waves)
    
    Modified by x2_money and x5_money bonuses.
    """
    def triangular(n):
        return (n * n + n) / 2
    
    multiplier = (1 + player.x2_money) * (1 + 4 * (player.x5_money / 100))
    
    mat1 = triangular(wave) * multiplier
    mat2 = triangular(wave // 5) * multiplier
    mat3 = triangular(wave // 10) * multiplier
    mat4 = triangular(wave // 15) * multiplier
    
    return mat1, mat2, mat3, mat4


def get_highest_wave_killed_in_x_hits(player: PlayerStats, enemy: EnemyStats, hits: int) -> int:
    """Calculate the highest wave where enemies can be killed in x hits"""
    return int((hits * player.atk - enemy.base_health) / enemy.health_scaling)


def calculate_hits_to_kill(player_atk: float, enemy_hp: float) -> int:
    """Calculate how many hits needed to kill an enemy (without crits)
    
    Args:
        player_atk: Player attack damage
        enemy_hp: Enemy health points
    
    Returns:
        Number of hits needed (minimum 1)
    """
    import math
    return max(1, math.ceil(enemy_hp / player_atk))


def calculate_hits_to_kill_with_crit(player_atk: float, enemy_hp: float, 
                                      crit_chance: float, crit_dmg: float) -> float:
    """Calculate expected hits needed to kill an enemy with crits factored in
    
    Uses average damage per hit including crit probability.
    
    Args:
        player_atk: Player attack damage
        enemy_hp: Enemy health points
        crit_chance: Crit chance as percentage (e.g., 15 for 15%)
        crit_dmg: Crit damage multiplier (e.g., 1.5 for 150%)
    
    Returns:
        Expected number of hits (can be fractional)
    """
    # Convert crit chance from percentage to decimal
    crit_prob = min(crit_chance / 100.0, 1.0)  # Cap at 100%
    
    # Average damage per hit = base_dmg * (1 - crit_prob) + base_dmg * crit_dmg * crit_prob
    # Simplified: avg_dmg = base_dmg * (1 + crit_prob * (crit_dmg - 1))
    avg_dmg_per_hit = player_atk * (1 + crit_prob * (crit_dmg - 1))
    
    if avg_dmg_per_hit <= 0:
        return float('inf')
    
    return enemy_hp / avg_dmg_per_hit


def calculate_effective_hp(player: PlayerStats, enemy: EnemyStats, wave: int) -> float:
    """
    Calculate effective HP (eHP) at a specific wave.
    
    eHP accounts for all damage reduction factors:
    - Base HP
    - Block Chance: reduces damage by block% (eHP = HP / (1 - block))
    - Enemy ATK Debuffs: reduces base damage per hit
    - Enemy Crit Debuffs: reduces average damage per hit (via crit chance/dmg reduction)
    
    Formula:
    eHP = HP / (1 - block_chance) * (base_avg_dmg / actual_avg_dmg)
    
    Where:
    - base_avg_dmg = damage without debuffs
    - actual_avg_dmg = damage with debuffs applied
    
    Args:
        player: Player stats
        enemy: Enemy stats (with debuffs applied)
        wave: Wave number to calculate for
    
    Returns:
        Effective HP as float
    """
    import math
    
    # Base HP
    base_hp = player.health
    
    # Block chance: eHP multiplier = 1 / (1 - block)
    # Example: 15% block = 1 / 0.85 = 1.176x eHP
    block_multiplier = 1.0 / (1.0 - player.block_chance) if player.block_chance < 1.0 else float('inf')
    
    # Calculate actual enemy damage at this wave (with debuffs)
    actual_enemy_atk = max(1, enemy.atk + wave * enemy.atk_scaling)
    actual_enemy_crit_chance = max(0, (enemy.crit + wave) / 100.0)  # 0-1 range
    actual_enemy_crit_dmg = enemy.crit_dmg + enemy.crit_dmg_scaling * wave
    
    # Average damage per hit (with debuffs)
    actual_avg_dmg = actual_enemy_atk * (1.0 + actual_enemy_crit_chance * (actual_enemy_crit_dmg - 1.0))
    
    # Calculate base enemy damage (without debuffs) for comparison
    base_enemy_atk = 2.5 + wave * 0.6  # From ENEMY_BASE_STATS
    base_enemy_crit = 0 + wave  # Base crit = wave
    base_enemy_crit_dmg = 1.0 + wave * 0.05  # Base crit dmg scaling
    
    base_enemy_crit_chance = max(0, base_enemy_crit / 100.0)
    base_avg_dmg = base_enemy_atk * (1.0 + base_enemy_crit_chance * (base_enemy_crit_dmg - 1.0))
    
    # Damage reduction factor from debuffs
    # If actual_dmg < base_dmg, we get eHP boost
    dmg_reduction_factor = base_avg_dmg / actual_avg_dmg if actual_avg_dmg > 0 else 1.0
    
    # Effective HP = HP * block_multiplier * dmg_reduction_factor
    ehp = base_hp * block_multiplier * dmg_reduction_factor
    
    return ehp


def get_enemy_hp_at_wave(enemy: EnemyStats, wave: int) -> int:
    """Get enemy HP at a specific wave"""
    return enemy.base_health + enemy.health_scaling * wave


def calculate_damage_breakpoints(player: PlayerStats, enemy: EnemyStats, 
                                  target_wave: int = None, max_breakpoints: int = 10,
                                  use_crit: bool = False) -> List[Dict]:
    """
    Calculate damage breakpoints for event enemies.
    
    A breakpoint is the minimum ATK needed to kill enemies in fewer hits.
    Unlike archaeology, reaching a breakpoint does NOT save HP because
    the next enemy inherits the attack progress of the previous one.
    
    However, breakpoints DO affect:
    - Total time (fewer hits = faster kills = more waves per second)
    - Required HP (fewer total enemy attacks over time)
    
    Args:
        player: Player stats (uses player.atk for current damage)
        enemy: Enemy stats (base_health, health_scaling)
        target_wave: Optional specific wave to calculate for (default: use player stats)
        max_breakpoints: Maximum number of breakpoints to return
        use_crit: If True, include crit damage in calculations (average expected hits)
    
    Returns:
        List of breakpoint dicts with:
        - wave: The wave number this breakpoint applies to
        - current_hits: Hits needed with current ATK
        - target_hits: Hits needed after breakpoint
        - current_atk: Current player ATK
        - required_atk: ATK needed for the breakpoint
        - atk_increase: How much more ATK needed
        - enemy_hp: Enemy HP at that wave
        - time_saved_per_enemy: Seconds saved per enemy killed
    """
    import math
    
    results = []
    current_atk = player.atk
    
    # If no target wave specified, use a reasonable range
    if target_wave is None:
        # Calculate wave range based on current stats
        # Start from wave 1 and go up to where we need many hits
        start_wave = 1
        end_wave = 100  # Look ahead a bit
    else:
        start_wave = max(1, target_wave - 5)
        end_wave = target_wave + 5
    
    seen_breakpoints = set()  # Track unique (wave, target_hits) pairs
    
    for wave in range(start_wave, end_wave + 1):
        enemy_hp = get_enemy_hp_at_wave(enemy, wave)
        
        if use_crit:
            # Use expected hits with crit factored in
            current_hits_float = calculate_hits_to_kill_with_crit(
                current_atk, enemy_hp, player.crit, player.crit_dmg
            )
            current_hits = math.ceil(current_hits_float)
        else:
            current_hits = calculate_hits_to_kill(current_atk, enemy_hp)
        
        if current_hits <= 1:
            continue  # Already one-shotting, no breakpoint possible
        
        # Calculate the next breakpoint: ATK needed for one fewer hit
        target_hits = current_hits - 1
        
        if use_crit:
            # With crits, we need to find ATK where avg hits = target_hits
            # avg_dmg = atk * (1 + crit_prob * (crit_dmg - 1))
            # enemy_hp / avg_dmg = target_hits
            # => avg_dmg = enemy_hp / target_hits
            # => atk = (enemy_hp / target_hits) / (1 + crit_prob * (crit_dmg - 1))
            crit_prob = min(player.crit / 100.0, 1.0)
            crit_multiplier = 1 + crit_prob * (player.crit_dmg - 1)
            avg_dmg_needed = enemy_hp / target_hits
            required_atk = math.ceil(avg_dmg_needed / crit_multiplier) if crit_multiplier > 0 else math.ceil(avg_dmg_needed)
        else:
            # Required ATK to kill in target_hits: ceil(enemy_hp / atk) = target_hits
            # => enemy_hp / atk <= target_hits
            # => atk >= enemy_hp / target_hits
            required_atk = math.ceil(enemy_hp / target_hits)
        
        atk_increase = required_atk - current_atk
        
        if atk_increase <= 0:
            continue  # Already at or past this breakpoint
        
        # Calculate time saved per enemy
        # Time per hit = default_atk_time / atk_speed
        time_per_hit = player.default_atk_time / player.atk_speed
        time_saved = time_per_hit  # Save one hit worth of time
        
        # Create unique key
        bp_key = (wave, target_hits, required_atk)
        if bp_key in seen_breakpoints:
            continue
        seen_breakpoints.add(bp_key)
        
        results.append({
            'wave': wave,
            'enemy_hp': enemy_hp,
            'current_hits': current_hits,
            'current_hits_float': current_hits_float if use_crit else float(current_hits),
            'target_hits': target_hits,
            'current_atk': current_atk,
            'required_atk': required_atk,
            'atk_increase': atk_increase,
            'time_saved_per_enemy': time_saved,
            # Time saved per wave (5 enemies per wave)
            'time_saved_per_wave': time_saved * 5,
        })
        
        if len(results) >= max_breakpoints:
            break
    
    # Sort by ATK increase (easiest breakpoints first)
    results.sort(key=lambda x: x['atk_increase'])
    
    return results[:max_breakpoints]


def calculate_breakpoint_efficiency(breakpoints: List[Dict], player: PlayerStats, 
                                     enemy: EnemyStats, target_wave: int) -> List[Dict]:
    """
    Calculate efficiency of each breakpoint.
    
    Efficiency = cumulative time saved from current wave to target wave
    divided by the ATK investment needed.
    
    Args:
        breakpoints: List of breakpoint dicts from calculate_damage_breakpoints
        player: Player stats
        enemy: Enemy stats
        target_wave: The wave the player is trying to reach
    
    Returns:
        Breakpoints with added efficiency metrics
    """
    results = []
    
    for bp in breakpoints:
        # Calculate cumulative time saved from bp['wave'] to target_wave
        # For each wave at or above bp['wave'] where we'd benefit from fewer hits
        total_time_saved = 0.0
        waves_affected = 0
        
        for wave in range(bp['wave'], target_wave + 1):
            enemy_hp = get_enemy_hp_at_wave(enemy, wave)
            current_hits = calculate_hits_to_kill(bp['current_atk'], enemy_hp)
            new_hits = calculate_hits_to_kill(bp['required_atk'], enemy_hp)
            
            if new_hits < current_hits:
                hits_saved = current_hits - new_hits
                time_per_hit = player.default_atk_time / player.atk_speed
                total_time_saved += hits_saved * time_per_hit * 5  # 5 enemies per wave
                waves_affected += 1
        
        # Efficiency = time saved per ATK point invested
        efficiency = total_time_saved / bp['atk_increase'] if bp['atk_increase'] > 0 else 0
        
        bp_with_eff = bp.copy()
        bp_with_eff['total_time_saved'] = total_time_saved
        bp_with_eff['waves_affected'] = waves_affected
        bp_with_eff['efficiency'] = efficiency
        bp_with_eff['target_wave'] = target_wave
        
        results.append(bp_with_eff)
    
    # Sort by efficiency (best first)
    results.sort(key=lambda x: -x['efficiency'])
    
    return results


def get_atk_breakpoint_table(enemy: EnemyStats, max_wave: int = 50, max_hits: int = 10) -> Dict[int, List[int]]:
    """
    Generate a table showing ATK required to kill enemies in X hits at each wave.
    
    Args:
        enemy: Enemy stats
        max_wave: Maximum wave to calculate for
        max_hits: Maximum number of hits to show
    
    Returns:
        Dict mapping hits -> list of (wave, required_atk) tuples
        Example: {1: [(1, 11), (2, 18), ...], 2: [(1, 6), (2, 9), ...]}
    """
    import math
    
    result = {}
    
    for hits in range(1, max_hits + 1):
        result[hits] = []
        for wave in range(1, max_wave + 1):
            enemy_hp = get_enemy_hp_at_wave(enemy, wave)
            required_atk = math.ceil(enemy_hp / hits)
            result[hits].append((wave, required_atk))
    
    return result


def find_best_breakpoint_for_budget(player: PlayerStats, enemy: EnemyStats,
                                     available_atk_increase: int, target_wave: int) -> Dict:
    """
    Find the best breakpoint that can be reached with a given ATK budget.
    
    Args:
        player: Current player stats
        enemy: Enemy stats
        available_atk_increase: How much ATK can be added
        target_wave: The wave trying to reach
    
    Returns:
        Best breakpoint dict, or None if no breakpoint reachable
    """
    breakpoints = calculate_damage_breakpoints(player, enemy, target_wave, max_breakpoints=20)
    breakpoints_with_eff = calculate_breakpoint_efficiency(breakpoints, player, enemy, target_wave)
    
    # Filter to only reachable breakpoints
    reachable = [bp for bp in breakpoints_with_eff if bp['atk_increase'] <= available_atk_increase]
    
    if not reachable:
        return None
    
    # Return the one with highest efficiency
    return reachable[0]


def calculate_upgrade_cost(base_price: float, levels: int) -> float:
    """Calculate total cost for upgrading from 0 to a certain level
    
    Cost formula: sum of base_price * 1.25^i for i in 0..levels-1
    """
    total = 0.0
    for i in range(levels):
        total += round_number(base_price * (1.25 ** i))
    return total


def calculate_next_upgrade_cost(base_price: float, current_level: int) -> float:
    """Calculate cost of the next level of an upgrade"""
    return round_number(base_price * (1.25 ** current_level))


def calculate_total_costs(upgrades: Dict[int, List[int]]) -> Dict[int, float]:
    """Calculate total costs for all upgrades per tier
    
    Returns dict mapping tier to total material cost.
    """
    total_costs = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    
    for tier in range(1, 5):
        if tier in upgrades:
            for i, level in enumerate(upgrades[tier]):
                if i < len(COSTS[tier]):
                    total_costs[tier] += calculate_upgrade_cost(COSTS[tier][i], level)
    
    return total_costs


def get_current_max_level(upgrades: Dict[int, List[int]], tier: int, upgrade_idx: int) -> int:
    """Get current max level for an upgrade considering cap upgrades"""
    cap_idx = CAP_UPGRADES[tier]
    base_max = MAX_LEVELS[tier][upgrade_idx]
    
    if upgrade_idx == cap_idx - 1:  # Cap upgrade itself (0-indexed, so -1)
        return base_max + upgrades[4][6]  # Cap of caps
    elif tier == 4 and upgrade_idx == 6:  # Cap of caps upgrade
        return base_max
    else:
        return base_max + upgrades[tier][cap_idx - 1]


def get_gem_max_level(prestige_count: int, idx: int) -> int:
    """Get max level for gem upgrade based on prestige"""
    if idx < 2:  # ATK% and HP%
        return 5 + prestige_count
    elif idx == 2:  # Game Speed
        return 1 + min(2, prestige_count // 5)
    else:  # 2x Currency
        return 1
