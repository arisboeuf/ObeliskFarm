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
from .block_spawn_rates import get_normalized_spawn_rates, spawn_block_for_slot


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
    QUAKE_CHARGES = 5
    QUAKE_COOLDOWN = 180
    QUAKE_DAMAGE_MULTIPLIER = 0.20  # 20% damage to all blocks
    MOD_STAMINA_BONUS_AVG = 6.5
    # Stage structure: 6 columns x 4 rows = 24 slots
    # Each slot CAN spawn a block (but doesn't have to)
    # Blocks per floor varies 0–24 in-game based on spawn probabilities
    SLOTS_PER_FLOOR = 24
    
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
    
    def calculate_quake_damage(self, stats: Dict) -> int:
        """Calculate quake damage (20% of base damage, ignores armor)"""
        total_damage = stats['total_damage']
        return max(1, int(total_damage * 0.20))
    
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
                           enrage_state: Optional[Dict] = None, block_cards: Optional[Dict] = None) -> Tuple[int, Dict]:
        """
        Simulate killing a single block, returning the number of hits needed and updated enrage state.
        
        Uses actual random crits/one-hits rather than expected values.
        
        Args:
            enrage_state: Dict with 'charges_remaining' and 'cooldown' keys, or None if not tracking
            block_cards: Dict mapping block_type to card level (0=none, 1=card, 2=gilded)
        
        Returns:
            (hits_needed, updated_enrage_state)
        """
        # Apply card HP reduction if needed
        if block_cards and block_type:
            card_level = block_cards.get(block_type, 0)
            if card_level == 1:
                block_hp = int(block_hp * 0.90)  # Card: -10% HP
            elif card_level == 2:
                block_hp = int(block_hp * 0.80)  # Gilded: -20% HP
        
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
                    flurry_enabled: bool = False, quake_enabled: bool = False,
                    block_cards: Optional[Dict] = None,
                    debug: bool = False, return_metrics: bool = False) -> float:
        """
        Simulate a complete run, returning floors cleared.
        
        Uses actual random crits/one-hits and mods rather than expected values.
        
        Args:
            debug: If True, print detailed debug information for each floor
            return_metrics: If True, return dict with metrics instead of just floors_cleared
        
        Returns:
            float: Number of floors cleared (0.0 if no floors cleared, 1.0+ if floors cleared)
            OR dict with metrics if return_metrics=True
        """
        max_stamina = stats['max_stamina']
        stamina_remaining = max_stamina
        floors_cleared = 0
        current_floor = starting_floor
        max_stage_reached = starting_floor  # Track the maximum stage reached during the run
        
        # Fragment tracking
        fragments_by_type = {'common': 0.0, 'rare': 0.0, 'epic': 0.0, 'legendary': 0.0, 'mythic': 0.0}
        fragment_mult = stats.get('fragment_mult', 1.0)
        loot_mod_chance = stats.get('loot_mod_chance', 0)
        loot_mod_multiplier = stats.get('loot_mod_multiplier', 3.5)
        
        # XP tracking
        total_xp = 0.0
        xp_mult = stats.get('xp_mult', 1.0)
        exp_mod_chance = stats.get('exp_mod_chance', 0)
        exp_mod_multiplier = stats.get('exp_mod_gain', 4.0)  # Average exp mod multiplier
        arch_xp_mult = stats.get('arch_xp_mult', 1.0)
        
        # Run duration tracking (1 hit = 1 second)
        total_hits = 0
        
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
        
        # Quake tracking (shared across all blocks in the run)
        quake_state = {'charges_remaining': 0, 'cooldown': 0} if quake_enabled else None
        
        if debug:
            # Extract key stats for display
            total_damage = stats.get('total_damage', 0)
            armor_pen = stats.get('armor_pen', 0)
            crit_chance = stats.get('crit_chance', 0) * 100
            crit_damage = stats.get('crit_damage', 1.5)
            skill_points = stats.get('skill_points', {})
            
        
        for floor_iter in range(1000):  # Max floors safety
            block_mix = get_block_mix_for_floor(current_floor)
            
            # Go through all 24 slots and spawn blocks based on spawn probabilities
            stamina_for_floor = 0
            blocks_killed = 0
            stamina_before_floor = stamina_remaining
            stamina_mods_this_floor = 0
            block_types_spawned = {}  # Track block types spawned this floor
            
            # For Quake: track all blocks on the floor and their HP
            floor_blocks = []  # List of (block_type, block_data, current_hp)
            
            # First pass: spawn all blocks
            for slot in range(self.SLOTS_PER_FLOOR):
                block_type = spawn_block_for_slot(current_floor, rng=random)
                if block_type:
                    block_data = block_mix.get(block_type)
                    if block_data:
                        # Apply card HP reduction if needed
                        block_hp = block_data.health
                        if block_cards and block_type in block_cards:
                            card_level = block_cards[block_type]
                            if card_level == 1:
                                block_hp = int(block_hp * 0.90)
                            elif card_level == 2:
                                block_hp = int(block_hp * 0.80)
                        
                        floor_blocks.append((block_type, block_data, block_hp))
                        
                        # Track block type
                        if block_type not in block_types_spawned:
                            block_types_spawned[block_type] = 0
                        block_types_spawned[block_type] += 1
            
            # Second pass: kill blocks one by one
            for block_idx, (block_type, block_data, block_hp) in enumerate(floor_blocks):
                # Simulate killing this block (pass enrage state and cards)
                hits, enrage_state = self.simulate_block_kill(
                    stats, block_hp, block_data.armor, 
                    block_type, use_crit, enrage_state, block_cards
                )
                stamina_for_floor += hits
                total_hits += hits
                blocks_killed += 1
                
                # Track XP from this block (only if not dirt)
                if block_type != 'dirt':
                    base_xp = block_data.xp
                    # Check for exp mod
                    exp_mod_active = random.random() < exp_mod_chance
                    exp_mult = exp_mod_multiplier if exp_mod_active else 1.0
                    # Apply XP multiplier and arch XP multiplier
                    xp_gain = base_xp * xp_mult * exp_mult * arch_xp_mult
                    total_xp += xp_gain
                
                # Quake: each hit on this block deals 20% damage to all other blocks
                if quake_state is not None:
                    # Check if quake is active (charges available)
                    is_quake_active = quake_state['charges_remaining'] > 0
                    
                    if is_quake_active:
                        # Calculate quake damage per hit (20% of base damage)
                        base_damage = self.calculate_effective_damage(stats, 0)  # No armor for quake
                        quake_damage_per_hit = int(base_damage * self.QUAKE_DAMAGE_MULTIPLIER)
                        
                        # Apply quake damage to all other blocks
                        for other_idx, (other_type, other_data, other_hp) in enumerate(floor_blocks):
                            if other_idx != block_idx and other_hp > 0:
                                # Apply quake damage (20% to all blocks)
                                quake_damage_total = quake_damage_per_hit * hits
                                # Quake damage ignores armor
                                floor_blocks[other_idx] = (other_type, other_data, max(0, other_hp - quake_damage_total))
                        
                        # Update quake charges
                        quake_state['charges_remaining'] -= 1
                        if quake_state['charges_remaining'] <= 0:
                            quake_state['cooldown'] = self.QUAKE_COOLDOWN
                    else:
                        # Update quake cooldown
                        quake_state['cooldown'] -= hits
                        if quake_state['cooldown'] <= 0:
                            quake_state['charges_remaining'] = self.QUAKE_CHARGES
                            quake_state['cooldown'] = self.QUAKE_COOLDOWN
                
                # Calculate fragments from this block (only if not dirt)
                if block_type != 'dirt' and block_type in fragments_by_type:
                    base_frag = block_data.fragment
                    # Check for loot mod
                    loot_mod_active = random.random() < loot_mod_chance
                    loot_mult = loot_mod_multiplier if loot_mod_active else 1.0
                    frag_gain = base_frag * fragment_mult * loot_mult
                    fragments_by_type[block_type] += frag_gain
                
                # Check for stamina mod (adds stamina immediately during the floor)
                if random.random() < stamina_mod_chance:
                    stamina_gain = random.uniform(3, 10)  # Actual range
                    stamina_remaining = min(max_stamina, stamina_remaining + stamina_gain)
                    stamina_mods_this_floor += stamina_gain
            
            # Check flurry (approximate: 1 hit = 1 second)
            flurry_triggered = False
            if flurry_enabled:
                flurry_cooldown -= stamina_for_floor
                if flurry_cooldown <= 0:
                    stamina_remaining = min(max_stamina, stamina_remaining + flurry_stamina_bonus)
                    flurry_cooldown = self.FLURRY_COOLDOWN
                    flurry_triggered = True
                    stamina_mods_this_floor += flurry_stamina_bonus
            
            # Format block types for display
            block_types_str = ", ".join([f"{bt}:{count}" for bt, count in sorted(block_types_spawned.items())])
            if len(block_types_str) > 28:
                block_types_str = block_types_str[:25] + "..."
            
            # Check if we can clear this floor
            stamina_after_floor = stamina_remaining - stamina_for_floor if stamina_remaining >= stamina_for_floor else stamina_remaining
            cleared = stamina_remaining >= stamina_for_floor
            
            
            if stamina_remaining >= stamina_for_floor:
                stamina_remaining -= stamina_for_floor
                floors_cleared += 1
                current_floor += 1
                max_stage_reached = current_floor  # Update max stage when we clear a floor
            else:
                # Partial floor - we didn't fully clear this floor, so we stay at current_floor
                # max_stage_reached remains at the last fully cleared floor
                if stamina_for_floor > 0:
                    floors_cleared += stamina_remaining / stamina_for_floor
                break
        
        
        if return_metrics:
            # Calculate total fragments
            total_fragments = sum(fragments_by_type.values())
            
            # Run duration in seconds (1 hit = 1 second, but speed mods/flurry can reduce it)
            # For simplicity, we use total_hits as duration (speed mods/flurry are QoL, not resource benefit)
            run_duration_seconds = max(1.0, float(total_hits))
            
            return {
                'floors_cleared': floors_cleared,
                'max_stage_reached': max_stage_reached,
                'starting_floor': starting_floor,
                'fragments': fragments_by_type.copy(),
                'total_fragments': total_fragments,
                'xp_per_run': total_xp,
                'run_duration_seconds': run_duration_seconds,
                'total_hits': total_hits,
            }
        
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
        
        for i in range(num_simulations):
            
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
        
        # Calculate difference
        mean_diff = stats_with_crit.mean - stats_without_crit.mean
        mean_diff_pct = (mean_diff / stats_without_crit.mean * 100) if stats_without_crit.mean > 0 else 0
        
        median_diff = stats_with_crit.median - stats_without_crit.median
        median_diff_pct = (median_diff / stats_without_crit.median * 100) if stats_without_crit.median > 0 else 0
        


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


def debug_single_run(stats: Dict, starting_floor: int,
                     use_crit: bool = True,
                     enrage_enabled: bool = False,
                     flurry_enabled: bool = False,
                     block_cards: Optional[Dict] = None,
                     skill_points: Optional[Dict] = None,
                     seed: Optional[int] = None):
    """
    Run a single Monte Carlo simulation with detailed debug output.
    
    Shows stamina development per floor and which blocks spawned.
    
    Args:
        stats: Character stats dictionary (from simulator)
        starting_floor: Starting floor for simulation
        use_crit: Whether to use crit calculations
        enrage_enabled: Whether Enrage ability is enabled
        flurry_enabled: Whether Flurry ability is enabled
        block_cards: Dict mapping block_type to card level (0=none, 1=card, 2=gilded)
        skill_points: Dict with skill point distribution (for display)
        seed: Random seed for reproducibility
    """
    # Add skill_points to stats dict for debug display
    if skill_points:
        stats_with_skills = stats.copy()
        stats_with_skills['skill_points'] = skill_points
    else:
        stats_with_skills = stats
    
    simulator = MonteCarloCritSimulator(seed=seed)
    floors_cleared = simulator.simulate_run(
        stats_with_skills, starting_floor, use_crit, enrage_enabled, flurry_enabled, block_cards, debug=True
    )
    return floors_cleared


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
    
    # Uncomment to run debug single run:
    # print("Debug Single Run Example")
    # debug_single_run(example_stats, starting_floor=1, use_crit=True, enrage_enabled=False, flurry_enabled=False)
    
    run_crit_analysis(example_stats, starting_floor=1, num_simulations=1000)
