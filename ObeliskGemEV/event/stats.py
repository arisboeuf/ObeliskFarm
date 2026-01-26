"""
Player and Enemy statistics for Event Simulator.
"""

from dataclasses import dataclass


@dataclass
class PlayerStats:
    """Player statistics for event simulation"""
    default_atk_time: float = 2.0
    default_walk_time: float = 4.0  # Time to walk between enemies (matches Lua original: defaultWalkTime=4)
    walk_speed: float = 1.0
    atk_speed: float = 1.0
    health: int = 100
    atk: int = 10
    crit: int = 0
    crit_dmg: float = 2.0
    block_chance: float = 0.0
    game_speed: float = 1.0
    prestige_bonus_scale: float = 0.1
    x2_money: int = 0
    x5_money: int = 0
    max_wave: int = 1


@dataclass
class EnemyStats:
    """Enemy statistics for event simulation
    
    Scaling per wave:
    - HP = base_health + health_scaling * wave
    - ATK = max(1, atk + atk_scaling * wave)
    - ATK Speed = atk_speed + 0.02 * wave
    - Crit Chance = crit + wave
    - Crit Dmg = crit_dmg + crit_dmg_scaling * wave
    """
    default_atk_time: float = 2.0
    atk_speed: float = 0.8
    base_health: int = 4
    health_scaling: int = 7
    atk: float = 2.5
    atk_scaling: float = 0.6
    crit: int = 0
    crit_dmg: float = 1.0
    crit_dmg_scaling: float = 0.05
