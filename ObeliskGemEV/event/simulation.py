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
        p.game_speed += 0.02 * u[4]  # +2% Event Game Spd
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
        p.game_speed += 0.03 * u[3]  # +3% Event Game Spd
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
