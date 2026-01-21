"""
Monte Carlo Simulation for Crit Analysis in Archaeology

This module provides Monte Carlo simulations to help decide whether to include
crit calculations in the archaeology simulator. It compares runs with crit enabled
vs disabled to show the actual impact and variance.
"""

import random
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import statistics

from .block_stats import get_block_at_floor, get_block_mix_for_floor, BlockData
from .block_spawn_rates import get_normalized_spawn_rates


@dataclass
class SimulationStats:
    """Statistics from a Monte Carlo simulation"""
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    percentile_5: float
    percentile_95: float
    samples: List[float]
    
    def __str__(self):
        return (f"Mean: {self.mean:.2f}, Median: {self.median:.2f}, "
                f"StdDev: {self.std_dev:.2f}, Range: [{self.min_value:.2f}, {self.max_value:.2f}], "
                f"5-95%: [{self.percentile_5:.2f}, {self.percentile_95:.2f}]")


class MonteCarloCritSimulator:
    """Monte Carlo simulator for crit analysis"""
    
    # Constants matching the main simulator
    ENRAGE_CHARGES = 5
    ENRAGE_COOLDOWN = 60
    ENRAGE_DAMAGE_BONUS = 0.20
    ENRAGE_CRIT_DAMAGE_BONUS = 1.00
    FLURRY_COOLDOWN = 120
    FLURRY_STAMINA_BONUS = 5
    MOD_STAMINA_BONUS_AVG = 6.5
    BLOCKS_PER_FLOOR = 15
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize simulator with optional random seed"""
        if seed is not None:
            random.seed(seed)
    
    def calculate_effective_damage(self, stats: Dict, block_armor: int) -> int:
        """Calculate effective damage after armor penetration"""
        total_damage = stats['total_damage']
        armor_pen = stats['armor_pen']
        effective_armor = max(0, block_armor - armor_pen)
        return max(1, int(total_damage - effective_armor))
    
    def simulate_hit_damage(self, stats: Dict, block_armor: int, 
                           is_enrage: bool = False, use_crit: bool = True) -> int:
        """
        Simulate a single hit's damage with random crit/one-hit.
        
        Returns the actual damage dealt (integer).
        """
        # Calculate base damage
        if is_enrage:
            enrage_total_damage = int(stats['total_damage'] * (1 + self.ENRAGE_DAMAGE_BONUS))
            effective_armor = max(0, block_armor - stats['armor_pen'])
            base_damage = max(1, enrage_total_damage - effective_armor)
        else:
            base_damage = self.calculate_effective_damage(stats, block_armor)
        
        if not use_crit:
            return base_damage
        
        # Check for one-hit kill
        one_hit_chance = stats.get('one_hit_chance', 0)
        if random.random() < one_hit_chance:
            # One-hit kills the block regardless of HP
            return 999999  # Effectively infinite damage
        
        # Check for crit
        crit_chance = stats.get('crit_chance', 0)
        is_crit = random.random() < crit_chance
        
        if is_crit:
            crit_damage_mult = stats.get('crit_damage', 1.5)
            if is_enrage:
                crit_damage_mult += self.ENRAGE_CRIT_DAMAGE_BONUS
            # Crit damage is multiplicative
            damage = int(base_damage * crit_damage_mult)
        else:
            damage = base_damage
        
        return max(1, damage)
    
    def simulate_block_kill(self, stats: Dict, block_hp: int, block_armor: int,
                           block_type: Optional[str] = None, use_crit: bool = True,
                           enrage_state: Optional[Dict] = None) -> Tuple[int, Dict]:
        """
        Simulate killing a single block, returning the number of hits needed and updated enrage state.
        
        Uses actual random crits/one-hits rather than expected values.
        
        Args:
            enrage_state: Dict with 'charges_remaining' and 'cooldown' keys, or None if not tracking
        
        Returns:
            (hits_needed, updated_enrage_state)
        """
        # Apply card HP reduction if needed (placeholder - would need card data)
        # block_hp = self.get_block_hp_with_card(block_hp, block_type)
        
        if enrage_state is None:
            enrage_state = {'charges_remaining': 0, 'cooldown': 0}
        
        hits = 0
        damage_dealt = 0
        
        while damage_dealt < block_hp:
            # Check if enrage is available
            is_enrage = False
            if enrage_state['charges_remaining'] > 0:
                is_enrage = True
                enrage_state['charges_remaining'] -= 1
            else:
                enrage_state['cooldown'] -= 1
                if enrage_state['cooldown'] <= 0:
                    enrage_state['charges_remaining'] = self.ENRAGE_CHARGES
                    enrage_state['cooldown'] = self.ENRAGE_COOLDOWN
            
            # Simulate hit
            hit_damage = self.simulate_hit_damage(stats, block_armor, is_enrage, use_crit)
            damage_dealt += hit_damage
            hits += 1
            
            # Safety check to prevent infinite loops
            if hits > 10000:
                break
        
        return hits, enrage_state
    
    def simulate_run(self, stats: Dict, starting_floor: int, 
                    use_crit: bool = True, enrage_enabled: bool = False,
                    flurry_enabled: bool = False) -> float:
        """
        Simulate a complete run, returning floors cleared.
        
        Uses actual random crits/one-hits and mods rather than expected values.
        """
        max_stamina = stats['max_stamina']
        stamina_remaining = max_stamina
        floors_cleared = 0
        current_floor = starting_floor
        
        # Stamina mod tracking
        stamina_mod_chance = stats.get('stamina_mod_chance', 0)
        stamina_mod_gain = stats.get('stamina_mod_gain', self.MOD_STAMINA_BONUS_AVG)
        
        # Flurry tracking
        flurry_stamina_bonus = 0
        flurry_cooldown = 0
        if flurry_enabled:
            flurry_stamina_bonus = self.FLURRY_STAMINA_BONUS
            flurry_cooldown = self.FLURRY_COOLDOWN
        
        # Enrage tracking (shared across all blocks in the run)
        enrage_state = {'charges_remaining': 0, 'cooldown': 0} if enrage_enabled else None
        
        for _ in range(1000):  # Max floors safety
            spawn_rates = get_normalized_spawn_rates(current_floor)
            block_mix = get_block_mix_for_floor(current_floor)
            
            # Simulate each block on this floor
            # Spawn blocks randomly based on spawn rates
            stamina_for_floor = 0
            for _ in range(self.BLOCKS_PER_FLOOR):
                # Randomly select block type based on spawn rates
                rand = random.random()
                cumulative = 0.0
                selected_type = None
                for block_type, spawn_chance in spawn_rates.items():
                    cumulative += spawn_chance
                    if rand <= cumulative:
                        selected_type = block_type
                        break
                
                if selected_type:
                    block_data = block_mix.get(selected_type)
                    if block_data:
                        # Simulate killing this block (pass enrage state)
                        hits, enrage_state = self.simulate_block_kill(
                            stats, block_data.health, block_data.armor, 
                            selected_type, use_crit, enrage_state
                        )
                        stamina_for_floor += hits
                        
                        # Check for stamina mod
                        if random.random() < stamina_mod_chance:
                            stamina_gain = random.uniform(3, 10)  # Actual range
                            stamina_remaining = min(max_stamina, stamina_remaining + stamina_gain)
            
            # Check flurry (approximate: 1 hit = 1 second)
            if flurry_enabled:
                flurry_cooldown -= stamina_for_floor
                if flurry_cooldown <= 0:
                    stamina_remaining = min(max_stamina, stamina_remaining + flurry_stamina_bonus)
                    flurry_cooldown = self.FLURRY_COOLDOWN
            
            # Check if we can clear this floor
            if stamina_remaining >= stamina_for_floor:
                stamina_remaining -= stamina_for_floor
                floors_cleared += 1
                current_floor += 1
            else:
                # Partial floor
                if stamina_for_floor > 0:
                    floors_cleared += stamina_remaining / stamina_for_floor
                break
        
        return floors_cleared
    
    def run_comparison(self, stats: Dict, starting_floor: int,
                      num_simulations: int = 1000,
                      enrage_enabled: bool = False,
                      flurry_enabled: bool = False) -> Tuple[SimulationStats, SimulationStats]:
        """
        Run Monte Carlo simulations comparing crit enabled vs disabled.
        
        Returns:
            (stats_with_crit, stats_without_crit)
        """
        results_with_crit = []
        results_without_crit = []
        
        print(f"Running {num_simulations} simulations...")
        for i in range(num_simulations):
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{num_simulations}")
            
            # Simulate with crit
            floors_crit = self.simulate_run(
                stats, starting_floor, use_crit=True,
                enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled
            )
            results_with_crit.append(floors_crit)
            
            # Simulate without crit
            floors_no_crit = self.simulate_run(
                stats, starting_floor, use_crit=False,
                enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled
            )
            results_without_crit.append(floors_no_crit)
        
        # Calculate statistics
        stats_with_crit = self._calculate_stats(results_with_crit)
        stats_without_crit = self._calculate_stats(results_without_crit)
        
        return stats_with_crit, stats_without_crit
    
    def _calculate_stats(self, samples: List[float]) -> SimulationStats:
        """Calculate statistics from a list of samples"""
        if not samples:
            return SimulationStats(0, 0, 0, 0, 0, 0, 0, [])
        
        sorted_samples = sorted(samples)
        n = len(samples)
        
        return SimulationStats(
            mean=statistics.mean(samples),
            median=statistics.median(samples),
            std_dev=statistics.stdev(samples) if n > 1 else 0,
            min_value=min(samples),
            max_value=max(samples),
            percentile_5=sorted_samples[int(n * 0.05)],
            percentile_95=sorted_samples[int(n * 0.95)],
            samples=samples
        )
    
    def print_comparison(self, stats_with_crit: SimulationStats,
                        stats_without_crit: SimulationStats):
        """Print a formatted comparison of the two scenarios"""
        print("\n" + "=" * 80)
        print("MONTE CARLO CRIT COMPARISON RESULTS")
        print("=" * 80)
        
        print("\nWITH CRIT:")
        print(f"  {stats_with_crit}")
        
        print("\nWITHOUT CRIT:")
        print(f"  {stats_without_crit}")
        
        # Calculate difference
        mean_diff = stats_with_crit.mean - stats_without_crit.mean
        mean_diff_pct = (mean_diff / stats_without_crit.mean * 100) if stats_without_crit.mean > 0 else 0
        
        median_diff = stats_with_crit.median - stats_without_crit.median
        median_diff_pct = (median_diff / stats_without_crit.median * 100) if stats_without_crit.median > 0 else 0
        
        print("\nDIFFERENCE (Crit - No Crit):")
        print(f"  Mean: {mean_diff:+.3f} floors ({mean_diff_pct:+.2f}%)")
        print(f"  Median: {median_diff:+.3f} floors ({median_diff_pct:+.2f}%)")
        print(f"  StdDev difference: {stats_with_crit.std_dev - stats_without_crit.std_dev:+.3f}")
        
        # Statistical significance (simple t-test approximation)
        if len(stats_with_crit.samples) > 1 and len(stats_without_crit.samples) > 1:
            pooled_std = math.sqrt(
                (stats_with_crit.std_dev ** 2 + stats_without_crit.std_dev ** 2) / 2
            )
            if pooled_std > 0:
                n = len(stats_with_crit.samples)
                se = pooled_std * math.sqrt(2 / n)
                if se > 0:
                    t_stat = mean_diff / se
                    print(f"  T-statistic: {t_stat:.3f}")
                    if abs(t_stat) > 1.96:
                        print("  → Statistically significant difference (p < 0.05)")
                    else:
                        print("  → Not statistically significant (p >= 0.05)")
        
        print("\n" + "=" * 80)
        
        # Recommendation
        if abs(mean_diff_pct) < 0.1:
            print("\nRECOMMENDATION: Crit has minimal impact (<0.1% difference).")
            print("  You can safely use deterministic mode (no crit) for simplicity.")
        elif abs(mean_diff_pct) < 1.0:
            print("\nRECOMMENDATION: Crit has small impact (<1% difference).")
            print("  Deterministic mode is acceptable, but crit mode is more accurate.")
        else:
            print("\nRECOMMENDATION: Crit has meaningful impact (>1% difference).")
            print("  You should use crit mode for accurate calculations.")
        
        print("=" * 80 + "\n")


def run_crit_analysis(stats: Dict, starting_floor: int,
                     num_simulations: int = 1000,
                     enrage_enabled: bool = False,
                     flurry_enabled: bool = False,
                     seed: Optional[int] = None):
    """
    Convenience function to run a full crit analysis.
    
    Args:
        stats: Character stats dictionary (from simulator)
        starting_floor: Starting floor for simulation
        num_simulations: Number of Monte Carlo runs
        enrage_enabled: Whether Enrage ability is enabled
        flurry_enabled: Whether Flurry ability is enabled
        seed: Random seed for reproducibility
    """
    simulator = MonteCarloCritSimulator(seed=seed)
    stats_with_crit, stats_without_crit = simulator.run_comparison(
        stats, starting_floor, num_simulations, enrage_enabled, flurry_enabled
    )
    simulator.print_comparison(stats_with_crit, stats_without_crit)
    return stats_with_crit, stats_without_crit


if __name__ == "__main__":
    # Example usage
    example_stats = {
        'total_damage': 50,
        'armor_pen': 10,
        'max_stamina': 200,
        'crit_chance': 0.15,  # 15%
        'crit_damage': 1.8,  # 1.8x
        'one_hit_chance': 0.001,  # 0.1%
        'stamina_mod_chance': 0.05,  # 5%
        'stamina_mod_gain': 6.5,
    }
    
    print("Example Monte Carlo Crit Analysis")
    print("=" * 80)
    run_crit_analysis(example_stats, starting_floor=1, num_simulations=500)
