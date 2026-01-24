"""
Monte Carlo Optimizer for Event Budget Optimizer.
Generates random upgrade sequences and finds the best one through simulation.
"""

import random
import math
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass

from .constants import COSTS, MAX_LEVELS, CAP_UPGRADES, PRESTIGE_UNLOCKED
from .stats import PlayerStats, EnemyStats
from .simulation import apply_upgrades, run_full_simulation
from .optimizer import UpgradeState, calculate_player_stats, get_max_level_with_caps, is_upgrade_unlocked


@dataclass
class MCOptimizationResult:
    """Result from Monte Carlo optimization"""
    best_state: UpgradeState
    best_wave: float
    best_time: float
    materials_spent: Dict[int, float]
    materials_remaining: Dict[int, float]
    player_stats: PlayerStats
    enemy_stats: EnemyStats
    all_results: List[Tuple[UpgradeState, float, float]]  # (state, wave, time)
    statistics: Dict[str, float]  # mean, median, std_dev, etc.


def generate_random_upgrade_sequence(
    budget: Dict[int, float],
    prestige: int,
    initial_state: UpgradeState,
    event_runs: int = 5
) -> Tuple[UpgradeState, float, float]:
    """Generate a random upgrade sequence and simulate it"""
    """
    Generate a random upgrade sequence and simulate it.
    
    Args:
        budget: Available materials per tier
        prestige: Current prestige level
        initial_state: Starting upgrade state
    
    Returns:
        (final_state, reached_wave, run_time)
    """
    state = initial_state.copy()
    remaining = {tier: budget[tier] for tier in range(1, 5)}
    
    # Collect all available upgrades
    available_upgrades = []
    for tier in range(1, 5):
        for idx in range(len(COSTS[tier])):
            if is_upgrade_unlocked(tier, idx, prestige):
                available_upgrades.append((tier, idx))
    
    # Randomly buy upgrades until budget exhausted
    max_iterations = 1000
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Filter upgrades we can afford and haven't maxed
        affordable = []
        for tier, idx in available_upgrades:
            current_level = state.get_level(tier, idx)
            max_level = get_max_level_with_caps(tier, idx, state)
            
            if current_level >= max_level:
                continue
            
            base_cost = COSTS[tier][idx]
            next_cost = round(base_cost * (1.25 ** current_level))
            
            if next_cost <= remaining[tier]:
                affordable.append((tier, idx, next_cost))
        
        if not affordable:
            break  # Can't afford anything
        
        # Randomly select one upgrade to buy
        tier, idx, cost = random.choice(affordable)
        
        # Buy it
        current_level = state.get_level(tier, idx)
        state.set_level(tier, idx, current_level + 1)
        remaining[tier] -= cost
    
    # Simulate the final state (fewer runs for speed - events have less variance)
    try:
        player, enemy = calculate_player_stats(state, prestige)
        # Events have less variance (only block/crit RNG), so fewer sims needed
        sim_results, avg_wave, avg_time = run_full_simulation(player, enemy, runs=event_runs)
    except Exception as e:
        # Fallback if simulation fails
        print(f"Warning: Simulation failed in generate_random_upgrade_sequence: {e}")
        avg_wave = 0.0
        avg_time = 0.0
    
    return state, avg_wave, avg_time


def monte_carlo_optimize(
    budget: Dict[int, float],
    prestige: int,
    initial_state: Optional[UpgradeState] = None,
    num_runs: int = 1000,
    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
    event_runs_per_combination: int = 5
) -> MCOptimizationResult:
    """
    Monte Carlo optimization: test random upgrade sequences and find the best.
    
    Args:
        budget: Available materials per tier
        prestige: Current prestige level
        initial_state: Starting upgrade state
        num_runs: Number of random sequences to test
        progress_callback: Optional callback(current_run, total_runs, current_wave, best_wave)
    
    Returns:
        MCOptimizationResult with best state and statistics
    """
    if initial_state is None:
        initial_state = UpgradeState()
    
    all_results = []
    best_state = None
    best_wave = -1
    best_time = float('inf')
    
    for run_num in range(1, num_runs + 1):
        # Generate random sequence and simulate
        try:
            state, wave, time = generate_random_upgrade_sequence(
                budget, prestige, initial_state, event_runs_per_combination
            )
        except Exception as e:
            print(f"Error in generate_random_upgrade_sequence (run {run_num}): {e}")
            import traceback
            traceback.print_exc()
            # Skip this run and continue
            continue
        
        all_results.append((state, wave, time))
        
        # Track best result
        if wave > best_wave or (wave == best_wave and time < best_time):
            best_wave = wave
            best_time = time
            best_state = state.copy()
        
        # Update progress (call from main thread if callback provided)
        if progress_callback:
            try:
                progress_callback(run_num, num_runs, wave, best_wave)
            except Exception as e:
                print(f"Error in progress_callback: {e}")
                pass  # Ignore callback errors
    
    # Calculate statistics
    waves = [r[1] for r in all_results]
    times = [r[2] for r in all_results]
    
    waves_sorted = sorted(waves)
    times_sorted = sorted(times)
    n = len(waves)
    
    # Calculate mean
    mean_wave = sum(waves) / n if n > 0 else 0
    mean_time = sum(times) / n if n > 0 else 0
    
    # Calculate std dev
    if n > 1:
        wave_variance = sum((w - mean_wave) ** 2 for w in waves) / (n - 1)
        time_variance = sum((t - mean_time) ** 2 for t in times) / (n - 1)
        std_dev_wave = math.sqrt(wave_variance)
        std_dev_time = math.sqrt(time_variance)
    else:
        std_dev_wave = 0
        std_dev_time = 0
    
    # Calculate percentiles
    median_wave = waves_sorted[n // 2] if n > 0 else 0
    median_time = times_sorted[n // 2] if n > 0 else 0
    p5_wave = waves_sorted[int(n * 0.05)] if n > 0 else 0
    p95_wave = waves_sorted[int(n * 0.95)] if n > 0 else 0
    
    # Calculate materials spent for best state
    materials_spent = {tier: 0.0 for tier in range(1, 5)}
    materials_remaining = {tier: budget[tier] for tier in range(1, 5)}
    
    if best_state:
        for tier in range(1, 5):
            for idx in range(len(COSTS[tier])):
                initial_level = initial_state.get_level(tier, idx)
                final_level = best_state.get_level(tier, idx)
                
                for level in range(initial_level, final_level):
                    cost = round(COSTS[tier][idx] * (1.25 ** level))
                    materials_spent[tier] += cost
                    materials_remaining[tier] -= cost
    
    # Get final stats
    if best_state:
        player, enemy = calculate_player_stats(best_state, prestige)
    else:
        player, enemy = PlayerStats(), EnemyStats()
    
    statistics = {
        'mean_wave': mean_wave,
        'median_wave': median_wave,
        'std_dev_wave': std_dev_wave,
        'min_wave': min(waves) if waves else 0,
        'max_wave': max(waves) if waves else 0,
        'p5_wave': p5_wave,
        'p95_wave': p95_wave,
        'mean_time': mean_time,
        'median_time': median_time,
        'std_dev_time': std_dev_time,
    }
    
    return MCOptimizationResult(
        best_state=best_state or initial_state,
        best_wave=best_wave,
        best_time=best_time,
        materials_spent=materials_spent,
        materials_remaining=materials_remaining,
        player_stats=player,
        enemy_stats=enemy,
        all_results=all_results,
        statistics=statistics
    )
