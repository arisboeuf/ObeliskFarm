"""
Event Budget Optimizer.
Calculates optimal upgrade distribution for given materials and prestige level.
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from .constants import (
    COSTS, MAX_LEVELS, CAP_UPGRADES, PRESTIGE_UNLOCKED, 
    UPGRADE_SHORT_NAMES, PRESTIGE_BONUS_BASE, get_prestige_wave_requirement
)
from .stats import PlayerStats, EnemyStats
from .simulation import (
    apply_upgrades, get_enemy_hp_at_wave, calculate_hits_to_kill,
    run_full_simulation, calculate_materials,
    calculate_damage_breakpoints, calculate_breakpoint_efficiency
)


@dataclass
class UpgradeState:
    """Current state of all upgrades"""
    levels: Dict[int, List[int]] = field(default_factory=lambda: {
        1: [0] * 10,
        2: [0] * 7,
        3: [0] * 8,
        4: [0] * 8
    })
    gem_levels: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    
    def copy(self) -> 'UpgradeState':
        """Create a deep copy of this state"""
        new_state = UpgradeState()
        for tier in range(1, 5):
            new_state.levels[tier] = self.levels[tier].copy()
        new_state.gem_levels = self.gem_levels.copy()
        return new_state
    
    def get_level(self, tier: int, idx: int) -> int:
        """Get upgrade level"""
        return self.levels[tier][idx]
    
    def set_level(self, tier: int, idx: int, level: int):
        """Set upgrade level"""
        self.levels[tier][idx] = level


@dataclass
class OptimizationResult:
    """Result of the optimization"""
    upgrades: UpgradeState
    expected_wave: float
    expected_time: float
    materials_spent: Dict[int, float]
    materials_remaining: Dict[int, float]
    player_stats: PlayerStats
    enemy_stats: EnemyStats
    recommendations: List[str]
    breakpoints: List[Dict] = field(default_factory=list)  # Breakpoint analysis


def calculate_upgrade_cost(base_price: float, current_level: int, target_level: int) -> float:
    """Calculate cost to upgrade from current_level to target_level"""
    total = 0.0
    for i in range(current_level, target_level):
        total += round(base_price * (1.25 ** i))
    return total


def get_max_level_with_caps(tier: int, upgrade_idx: int, state: UpgradeState) -> int:
    """Get maximum level for an upgrade considering cap upgrades"""
    base_max = MAX_LEVELS[tier][upgrade_idx]
    cap_idx = CAP_UPGRADES[tier] - 1  # Convert to 0-indexed
    
    if upgrade_idx == cap_idx:
        # This is a cap upgrade itself
        if tier == 4 and upgrade_idx == 6:
            # Cap of caps doesn't get increased
            return base_max
        else:
            # Cap upgrades are increased by cap-of-caps
            return base_max + state.get_level(4, 6)
    else:
        # Regular upgrades are increased by their tier's cap upgrade
        return base_max + state.get_level(tier, cap_idx)


def is_upgrade_unlocked(tier: int, upgrade_idx: int, prestige: int) -> bool:
    """Check if an upgrade is unlocked at given prestige level"""
    required_prestige = PRESTIGE_UNLOCKED[tier][upgrade_idx]
    return prestige >= required_prestige


def calculate_player_stats(state: UpgradeState, prestige: int) -> Tuple[PlayerStats, EnemyStats]:
    """Calculate player and enemy stats from upgrade state"""
    player = PlayerStats()
    enemy = EnemyStats()
    return apply_upgrades(state.levels, player, enemy, prestige, state.gem_levels)


def estimate_max_wave(player: PlayerStats, enemy: EnemyStats, runs: int = 100) -> Tuple[float, float]:
    """
    Estimate the maximum wave reachable with given stats.
    Returns (avg_wave, avg_time)
    """
    results, avg_wave, avg_time = run_full_simulation(player, enemy, runs)
    return avg_wave, avg_time


def calculate_atk_for_breakpoint(target_wave: int, target_hits: int, enemy: EnemyStats) -> int:
    """Calculate ATK needed to kill enemies at target_wave in target_hits"""
    enemy_hp = get_enemy_hp_at_wave(enemy, target_wave)
    return math.ceil(enemy_hp / target_hits)


def calculate_breakpoint_value_for_upgrade(
    state: UpgradeState,
    tier: int,
    idx: int,
    prestige: int,
    enemy: EnemyStats,
    max_wave: int
) -> float:
    """
    Calculate the breakpoint value of buying this upgrade.
    
    Returns a score representing how many breakpoints this upgrade helps reach
    across all waves, with special weighting for prestige waves.
    
    Args:
        state: Current upgrade state
        tier: Upgrade tier
        idx: Upgrade index
        prestige: Current prestige level
        enemy: Enemy stats
        max_wave: Maximum wave to analyze (typically estimated max wave)
    
    Returns:
        Breakpoint value score (higher = better)
    """
    from .simulation import get_enemy_hp_at_wave, calculate_hits_to_kill_with_crit
    
    # Get current stats
    player_current, _ = calculate_player_stats(state, prestige)
    
    # Simulate buying this upgrade
    state_test = state.copy()
    current_level = state_test.get_level(tier, idx)
    max_level = get_max_level_with_caps(tier, idx, state_test)
    
    if current_level >= max_level:
        return 0.0  # Can't buy more
    
    state_test.set_level(tier, idx, current_level + 1)
    player_after, _ = calculate_player_stats(state_test, prestige)
    
    # Calculate ATK increase
    atk_increase = player_after.atk - player_current.atk
    
    if atk_increase <= 0:
        return 0.0  # This upgrade doesn't increase ATK
    
    # Analyze breakpoints across all waves
    total_value = 0.0
    use_crit = player_current.crit >= 5
    
    # Get all prestige waves up to max_wave
    prestige_waves = set()
    for p in range(prestige + 1, 20):  # Look ahead a few prestiges
        pw = get_prestige_wave_requirement(p)
        if pw <= max_wave:
            prestige_waves.add(pw)
    
    # Analyze waves 1 to max_wave
    for wave in range(1, min(max_wave + 1, 200)):  # Cap at wave 200 for performance
        enemy_hp = get_enemy_hp_at_wave(enemy, wave)
        
        # Calculate hits needed before and after upgrade
        if use_crit:
            hits_before = calculate_hits_to_kill_with_crit(
                player_current.atk, enemy_hp, player_current.crit, player_current.crit_dmg
            )
            hits_after = calculate_hits_to_kill_with_crit(
                player_after.atk, enemy_hp, player_after.crit, player_after.crit_dmg
            )
        else:
            hits_before = math.ceil(enemy_hp / player_current.atk) if player_current.atk > 0 else 999
            hits_after = math.ceil(enemy_hp / player_after.atk) if player_after.atk > 0 else 999
        
        # Check if we reach a breakpoint (fewer hits needed)
        if hits_after < hits_before:
            hits_saved = hits_before - hits_after
            
            # Base value: time saved per enemy (5 enemies per wave)
            time_per_hit = player_current.default_atk_time / player_current.atk_speed
            base_value = hits_saved * time_per_hit * 5
            
            # Weight by wave importance
            wave_weight = 1.0
            
            # Prestige waves are MUCH more important (3x weight)
            if wave in prestige_waves:
                wave_weight = 3.0
            
            # Early waves are less important (diminishing returns)
            if wave < 10:
                wave_weight *= 0.5
            elif wave < 20:
                wave_weight *= 0.75
            
            # Later waves are more important (harder to reach)
            if wave > 50:
                wave_weight *= 1.5
            if wave > 100:
                wave_weight *= 2.0
            
            total_value += base_value * wave_weight
    
    # Normalize by ATK increase (value per ATK point)
    if atk_increase > 0:
        return total_value / atk_increase
    
    return 0.0


def greedy_optimize(
    budget: Dict[int, float],
    prestige: int,
    target_wave: Optional[int] = None,
    initial_state: Optional[UpgradeState] = None
) -> OptimizationResult:
    """
    Greedy optimization algorithm.
    
    Strategy:
    1. First ensure enough ATK to reach target wave (breakpoint-aware)
    2. Then maximize survivability (HP, enemy debuffs)
    3. Finally add speed upgrades for efficiency
    
    Args:
        budget: Dict mapping tier (1-4) to available materials
        prestige: Current prestige level
        target_wave: Target wave to reach (optional, will estimate if not provided)
        initial_state: Initial upgrade state (optional)
    
    Returns:
        OptimizationResult with recommended upgrades
    """
    state = initial_state.copy() if initial_state else UpgradeState()
    remaining = {tier: budget[tier] for tier in range(1, 5)}
    spent = {tier: 0.0 for tier in range(1, 5)}
    recommendations = []
    
    enemy = EnemyStats()
    
    # Determine target wave and optimization mode
    wave_pusher_mode = target_wave is None
    
    # Estimate max wave for breakpoint analysis
    player_current, _ = calculate_player_stats(state, prestige)
    estimated_wave, _ = estimate_max_wave(player_current, enemy, runs=20)
    
    if wave_pusher_mode:
        # Wave Pusher Mode: Maximize wave reachable with budget
        # Rough estimate: aim for 20-30% wave increase
        target_wave = int(estimated_wave * 1.3)  # Aim 30% higher as target
        recommendations.append(f"Wave Pusher Mode: Maximizing wave with available budget")
        recommendations.append(f"Current estimated wave: {estimated_wave:.1f}, analyzing up to wave {target_wave}")
    else:
        # Target Wave Mode: Reach specific wave
        recommendations.append(f"Target Wave Mode: Reaching Wave {target_wave}")
        estimated_wave = target_wave  # Use target as estimate for analysis
    
    # Use estimated max wave for breakpoint analysis (with some buffer)
    max_wave_for_analysis = int(estimated_wave * 1.2)  # Analyze 20% beyond estimated
    recommendations.append(f"Breakpoint analysis: Analyzing waves 1-{max_wave_for_analysis} with prestige wave weighting")
    
    # Phase 2: Buy upgrades greedily
    # Priority order for each tier based on value
    
    # Tier priorities (index, priority_score, category)
    # Higher priority = buy first
    tier_priorities = {
        1: [
            (0, 100, "atk"),      # +1 ATK - highest priority early
            (9, 95, "atk_hp"),    # +3 ATK, +3 HP - very efficient
            (6, 90, "atk_hp"),    # +1 ATK, +2 HP
            (1, 80, "hp"),        # +2 HP
            (2, 70, "speed"),     # +0.02 Atk Speed
            (4, 65, "speed"),     # +3% Game Speed
            (3, 60, "speed"),     # +0.03 Move Speed
            (5, 50, "crit"),      # Crit (less reliable)
            (7, 40, "cap"),       # Cap upgrade
            (8, 30, "prestige"),  # Prestige bonus (late game)
        ],
        2: [
            (2, 100, "debuff"),   # -1 Enemy ATK - VERY strong early
            (0, 90, "hp"),        # +3 HP
            (1, 85, "debuff"),    # -0.02 Enemy Atk Speed
            (4, 80, "atk_speed"), # +1 ATK, +0.01 Atk Speed
            (3, 70, "debuff"),    # Enemy crit reduction
            (5, 50, "cap"),       # Cap upgrade
            (6, 40, "prestige"),  # Prestige bonus
        ],
        3: [
            (0, 100, "atk"),      # +2 ATK
            (4, 95, "atk_hp"),    # +3 ATK, +3 HP
            (7, 90, "hp_speed"),  # +5 HP, +0.03 Atk Speed
            (1, 85, "speed"),     # +0.02 Atk Speed
            (3, 80, "speed"),     # +5% Game Speed
            (2, 60, "crit"),      # Crit
            (6, 50, "money"),     # 5x drop chance
            (5, 40, "cap"),       # Cap upgrade
        ],
        4: [
            (4, 100, "atk_hp"),   # +4 ATK, +4 HP
            (7, 95, "hp_speed"),  # +10 HP, +0.05 Atk Speed
            (1, 90, "hp"),        # +5 HP
            (3, 85, "speed"),     # Atk/Move speed
            (0, 80, "block"),     # Block chance
            (2, 70, "crit"),      # Crit damage
            (5, 50, "cap"),       # Cap upgrade
            (6, 40, "cap"),       # Cap of caps
        ]
    }
    
    # Greedy loop: buy best available upgrade until budget exhausted
    max_iterations = 1000
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        best_buy = None
        best_score = -1
        
        for tier in range(1, 5):
            for idx, priority, category in tier_priorities[tier]:
                # Check if unlocked
                if not is_upgrade_unlocked(tier, idx, prestige):
                    continue
                
                # Check current level vs max
                current_level = state.get_level(tier, idx)
                max_level = get_max_level_with_caps(tier, idx, state)
                
                if current_level >= max_level:
                    continue
                
                # Calculate cost of next level
                base_cost = COSTS[tier][idx]
                next_cost = round(base_cost * (1.25 ** current_level))
                
                if next_cost > remaining[tier]:
                    continue
                
                # Calculate effective score
                # Adjust priority based on current needs
                effective_score = priority
                
                player, _ = calculate_player_stats(state, prestige)
                
                # Breakpoint-aware scoring: Calculate value across all waves
                if category in ["atk", "atk_hp", "atk_speed"]:
                    # Calculate breakpoint value for ATK upgrades
                    bp_value = calculate_breakpoint_value_for_upgrade(
                        state, tier, idx, prestige, enemy, max_wave_for_analysis
                    )
                    # Scale breakpoint value to score (normalize to 0-100 range)
                    effective_score += min(100, bp_value * 0.1)  # Scale factor may need tuning
                
                # HP and survivability upgrades
                if category in ["hp", "hp_speed", "atk_hp", "debuff"]:
                    # HP helps survive longer = reach higher waves
                    # Value increases with estimated wave (harder waves need more HP)
                    hp_bonus = min(50, estimated_wave * 0.5)
                    effective_score += hp_bonus
                
                # Speed upgrades help clear faster
                if category in ["speed"]:
                    # Speed is valuable but less than ATK/HP
                    speed_bonus = 20
                    effective_score += speed_bonus
                
                # Efficiency: lower cost = better (always)
                cost_efficiency = 100 / (next_cost + 1)
                effective_score += cost_efficiency * 0.5
                
                if effective_score > best_score:
                    best_score = effective_score
                    best_buy = (tier, idx, next_cost)
        
        if best_buy is None:
            break
        
        tier, idx, cost = best_buy
        state.levels[tier][idx] += 1
        remaining[tier] -= cost
        spent[tier] += cost
    
    # Calculate final stats
    player, enemy_modified = calculate_player_stats(state, prestige)
    
    # Estimate wave (use fewer runs for speed)
    avg_wave, avg_time = estimate_max_wave(player, enemy_modified, runs=50)
    
    # Calculate breakpoints for the optimized build
    # Use crit if player has meaningful crit stats
    use_crit = player.crit >= 5  # Use crit calculation if 5%+ crit
    
    # For wave pusher mode, calculate breakpoints up to estimated max wave
    bp_target_wave = int(avg_wave * 1.2) if wave_pusher_mode else target_wave
    breakpoints = calculate_damage_breakpoints(
        player, enemy_modified, bp_target_wave, max_breakpoints=10, use_crit=use_crit
    )
    breakpoints_with_eff = calculate_breakpoint_efficiency(
        breakpoints, player, enemy_modified, bp_target_wave
    )
    
    # Generate recommendations
    if wave_pusher_mode:
        recommendations.append(f"Final ATK: {player.atk}")
        recommendations.append(f"Final HP: {player.health}")
        recommendations.append(f"Estimated Max Wave: {avg_wave:.1f}")
        recommendations.append(f"Estimated Time: {avg_time:.1f}s per run")
    else:
        # Calculate required ATK for target wave (estimate based on enemy HP)
        required_atk = calculate_atk_for_breakpoint(target_wave, 1, enemy_modified)
        recommendations.append(f"Final ATK: {player.atk} (target wave {target_wave} needs ~{required_atk})")
        recommendations.append(f"Final HP: {player.health}")
        recommendations.append(f"Estimated Wave: {avg_wave:.1f}")
        recommendations.append(f"Estimated Time: {avg_time:.1f}s per run")
    
    # Add breakpoint info
    if breakpoints_with_eff:
        best_bp = breakpoints_with_eff[0]
        next_wave = best_bp['wave']
        next_atk = best_bp['required_atk']
        atk_needed = best_bp['atk_increase']
        if atk_needed > 0:
            recommendations.append(f"Next Breakpoint: Wave {next_wave} needs +{atk_needed} ATK (→ {next_atk} total)")
    
    # Check if we hit target (only in target wave mode)
    if not wave_pusher_mode and avg_wave < target_wave:
        recommendations.append(f"WARNING: May not reach target wave {target_wave}!")
        recommendations.append("Consider: More prestiges, gem upgrades, or lower target")
    
    return OptimizationResult(
        upgrades=state,
        expected_wave=avg_wave,
        expected_time=avg_time,
        materials_spent=spent,
        materials_remaining=remaining,
        player_stats=player,
        enemy_stats=enemy_modified,
        recommendations=recommendations,
        breakpoints=breakpoints_with_eff
    )


def format_upgrade_summary(state: UpgradeState, prestige: int) -> str:
    """Format upgrade state as readable summary"""
    lines = []
    
    for tier in range(1, 5):
        tier_upgrades = []
        for idx, level in enumerate(state.levels[tier]):
            if level > 0:
                name = UPGRADE_SHORT_NAMES[tier][idx]
                tier_upgrades.append(f"{name}: {level}")
        
        if tier_upgrades:
            lines.append(f"Tier {tier}: {', '.join(tier_upgrades)}")
    
    return '\n'.join(lines) if lines else "No upgrades"


def calculate_materials_for_wave(wave: int, player: PlayerStats) -> Dict[int, float]:
    """Calculate materials earned from reaching a wave"""
    mat1, mat2, mat3, mat4 = calculate_materials(wave, player)
    return {1: mat1, 2: mat2, 3: mat3, 4: mat4}
