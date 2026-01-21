"""
Event Simulator Module for ObeliskGemEV

Simulates the bimonthly event mechanics in Idle Obelisk Miner.
Ported from Lua/LÖVE2D implementation.

Module structure:
- stats.py: PlayerStats and EnemyStats dataclasses
- constants.py: Upgrade data, costs, prestige requirements
- simulation.py: Combat simulation and calculations
- utils.py: Utility functions (formatting, etc.)
- gui_budget.py: Budget Optimizer panel
- gui_love2d.py: Love2D Simulator panel
- simulator.py: Main window with mode toggle
"""

from .simulator import EventSimulatorWindow
from .stats import PlayerStats, EnemyStats
from .constants import (
    UPGRADE_NAMES, GEM_UPGRADE_NAMES, PRESTIGE_UNLOCKED,
    MAX_LEVELS, CAP_UPGRADES, COSTS, TIER_COLORS, TIER_MAT_NAMES,
    get_prestige_wave_requirement
)
from .simulation import (
    apply_upgrades, simulate_event_run, run_full_simulation,
    calculate_materials, calculate_upgrade_cost, calculate_total_costs,
    get_highest_wave_killed_in_x_hits, get_current_max_level, get_gem_max_level
)
from .utils import format_number, avg_mult, resources_per_minute, format_time

__all__ = [
    # Main window
    'EventSimulatorWindow',
    
    # Stats
    'PlayerStats',
    'EnemyStats',
    
    # Constants
    'UPGRADE_NAMES',
    'GEM_UPGRADE_NAMES', 
    'PRESTIGE_UNLOCKED',
    'MAX_LEVELS',
    'CAP_UPGRADES',
    'COSTS',
    'TIER_COLORS',
    'TIER_MAT_NAMES',
    'get_prestige_wave_requirement',
    
    # Simulation
    'apply_upgrades',
    'simulate_event_run',
    'run_full_simulation',
    'calculate_materials',
    'calculate_upgrade_cost',
    'calculate_total_costs',
    'get_highest_wave_killed_in_x_hits',
    'get_current_max_level',
    'get_gem_max_level',
    
    # Utils
    'format_number',
    'avg_mult',
    'resources_per_minute',
    'format_time',
]
