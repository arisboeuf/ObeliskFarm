"""
Stargazing Calculator Module

Calculates star and super star income rates based on player stats and upgrades.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .data import (
    STARS, STARGAZING_UPGRADES, SUPER_STAR_UPGRADES,
    BASE_STAR_SPAWN_CHANCE, BASE_SUPER_STAR_SPAWN_CHANCE,
    get_star_upgrade_cost, get_super_star_upgrade_cost, format_number
)


@dataclass
class PlayerStargazingStats:
    """
    Represents the player's current stargazing stats from all sources.
    
    All multipliers are stored as their actual value:
    - 1.0 = no bonus (100%)
    - 1.5 = 50% bonus (150%)
    - 2.0 = 100% bonus (200%)
    
    All chances are stored as decimals:
    - 0.05 = 5% chance
    - 0.10 = 10% chance
    """
    
    # Telescope level (determines how many stars can be unlocked)
    telescope_level: int = 1
    
    # Auto-catch chance (0.0 to 1.0)
    auto_catch_chance: float = 0.0
    
    # Star spawn rate multiplier (1.0 = base, 2.0 = 2x)
    star_spawn_rate_mult: float = 1.0
    
    # Double and triple star chances
    double_star_chance: float = 0.0
    triple_star_chance: float = 0.0
    
    # Super star stats
    super_star_spawn_rate_mult: float = 1.0
    triple_super_star_chance: float = 0.0  # From Leo star
    super_star_10x_chance: float = 0.0
    
    # Supernova (default 10x multiplier, but can be modified)
    star_supernova_chance: float = 0.0
    star_supernova_mult: float = 10.0  # Default 10x, can vary from game stats
    super_star_supernova_chance: float = 0.0
    super_star_supernova_mult: float = 10.0  # Default 10x
    
    # Supergiant (default 3x multiplier, but can be modified by upgrades)
    star_supergiant_chance: float = 0.0
    star_supergiant_mult: float = 3.0  # Default 3x, increased by Supergiant Star Multiplier upgrade
    super_star_supergiant_chance: float = 0.0
    super_star_supergiant_mult: float = 3.0  # Default 3x
    
    # Radiant (10x multiplier)
    star_radiant_chance: float = 0.0
    star_radiant_mult: float = 10.0
    super_star_radiant_chance: float = 0.0
    super_star_radiant_mult: float = 10.0
    
    # All star multiplier (affects both stars and super stars)
    all_star_mult: float = 1.0
    
    # Novagiant combo multiplier (when both supernova and supergiant)
    novagiant_combo_mult: float = 1.0
    
    # Floor clears per hour (depends on player's farming setup)
    floor_clears_per_hour: float = 120.0  # Default: 2 floors per minute
    
    # CTRL+F Stars skill (multiplies offline gains by 5x)
    # Without CTRL+F: offline gains = auto_catch * spawn_rate * 0.2 (1 of 5 floors)
    # With CTRL+F: offline gains = auto_catch * spawn_rate * 1.0 (follows star through all 5 floors)
    ctrl_f_stars_enabled: bool = False


class StargazingCalculator:
    """
    Calculates star and super star income rates.
    
    The calculation follows the game mechanics:
    1. Base chance: 1/50 (2%) per floor clear for a star to spawn
    2. Star Spawn Rate Multiplier: Increases the effective spawn chance
    3. At each spawn event, either:
       - A Super Star spawns (exclusive with regular stars)
       - OR a Regular Star spawns (can be single/double/triple)
    4. Double/Triple Star Chance: Only applies to regular star spawns
    5. Supernova/Supergiant/Radiant: Multipliers on individual stars
    6. All Star Multiplier: Final multiplier on all stars
    
    IMPORTANT: Super Star spawns and Double/Triple Star spawns are EXCLUSIVE.
    If a Super Star spawns, there is no Double/Triple Star, and vice versa.
    """
    
    def __init__(self, stats: PlayerStargazingStats):
        self.stats = stats
    
    def calculate_stars_per_spawn(self) -> float:
        """
        Calculate expected number of REGULAR stars per spawn event.
        
        This accounts for:
        - Double star chance (2 stars instead of 1)
        - Triple star chance (3 stars instead of 1)
        
        Note: Double and triple are exclusive - you get 1, 2, or 3 stars.
        IMPORTANT: This only applies to REGULAR star spawns, NOT super star spawns.
        Super star spawns are exclusive with double/triple star spawns.
        """
        # Probability of super star spawn (exclusive with regular stars)
        base_super_chance = BASE_SUPER_STAR_SPAWN_CHANCE  # 1/100 = 0.01
        p_super_star = base_super_chance * self.stats.super_star_spawn_rate_mult
        
        # Probability of regular star spawn (when not super star)
        p_regular_star = 1 - p_super_star
        
        # Probability distribution for regular stars (when it's a regular star spawn)
        p_triple = self.stats.triple_star_chance
        p_double = self.stats.double_star_chance * (1 - p_triple)  # Only if not triple
        p_single = 1 - p_triple - p_double
        
        # Expected regular stars per spawn event
        # = P(regular spawn) * E[stars | regular spawn]
        expected = p_regular_star * (1 * p_single + 2 * p_double + 3 * p_triple)
        return expected
    
    def calculate_star_multiplier_per_star(self) -> float:
        """
        Calculate expected multiplier per star from special effects.
        
        Effects:
        - Supernova: 10x stars (can be modified by supernova_mult)
        - Supergiant: 3x stars (can be modified by supergiant_mult)
        - Radiant: 10x stars (can be modified by radiant_mult)
        - Novagiant Combo: Extra multiplier when both supernova AND supergiant
        
        These effects can stack multiplicatively.
        """
        # Probability of each effect
        p_supernova = self.stats.star_supernova_chance
        p_supergiant = self.stats.star_supergiant_chance
        p_radiant = self.stats.star_radiant_chance
        
        # Expected multiplier from each effect
        # E[mult] = p * (mult - 1) + 1 = 1 + p * (mult - 1)
        supernova_contribution = 1 + p_supernova * (self.stats.star_supernova_mult - 1)
        supergiant_contribution = 1 + p_supergiant * (self.stats.star_supergiant_mult - 1)
        radiant_contribution = 1 + p_radiant * (self.stats.star_radiant_mult - 1)
        
        # Novagiant combo: when both supernova AND supergiant occur
        p_novagiant = p_supernova * p_supergiant
        novagiant_contribution = 1 + p_novagiant * (self.stats.novagiant_combo_mult - 1)
        
        # Total multiplier (multiplicative stacking)
        total_mult = supernova_contribution * supergiant_contribution * radiant_contribution * novagiant_contribution
        
        # Apply all star multiplier
        total_mult *= self.stats.all_star_mult
        
        return total_mult
    
    def calculate_expected_stars_per_spawn(self) -> float:
        """
        Calculate expected star value per spawn event.
        
        Combines:
        - Number of stars per spawn (1-3)
        - Multiplier per star (from supernova, supergiant, radiant, etc.)
        """
        stars_per_spawn = self.calculate_stars_per_spawn()
        mult_per_star = self.calculate_star_multiplier_per_star()
        
        return stars_per_spawn * mult_per_star
    
    def calculate_star_spawn_rate_per_hour(self) -> float:
        """
        Calculate the number of star spawn events per hour.
        
        Base: 1/50 chance per floor clear
        Modified by: Star Spawn Rate Multiplier
        """
        base_chance = BASE_STAR_SPAWN_CHANCE  # 1/50 = 0.02
        modified_chance = base_chance * self.stats.star_spawn_rate_mult
        
        # Cap at 100% (can't have more than 1 star per floor)
        modified_chance = min(modified_chance, 1.0)
        
        spawns_per_hour = self.stats.floor_clears_per_hour * modified_chance
        return spawns_per_hour
    
    def calculate_stars_per_hour(self) -> float:
        """
        Calculate total expected stars per hour.
        
        = spawn_rate * stars_per_spawn * multipliers
        """
        spawns_per_hour = self.calculate_star_spawn_rate_per_hour()
        stars_per_spawn = self.calculate_expected_stars_per_spawn()
        
        return spawns_per_hour * stars_per_spawn
    
    def calculate_auto_caught_stars_per_hour(self) -> float:
        """
        Calculate stars automatically caught per hour (offline gains).
        
        Important for offline/AFK farming.
        
        Offline gains formula:
        - Without CTRL+F Stars: auto_catch * spawn_rate * 0.2 (1 of 5 floors)
        - With CTRL+F Stars: auto_catch * spawn_rate * 1.0 (follows through all 5 floors)
        """
        total_stars = self.calculate_stars_per_hour()
        
        # Offline gains multiplier: 0.2 without CTRL+F, 1.0 with CTRL+F
        offline_mult = 1.0 if self.stats.ctrl_f_stars_enabled else 0.2
        
        return total_stars * self.stats.auto_catch_chance * offline_mult
    
    # =========================================================================
    # SUPER STAR CALCULATIONS
    # =========================================================================
    
    def calculate_super_stars_per_spawn(self) -> float:
        """
        Calculate expected number of super stars per super star spawn event.
        
        Accounts for:
        - Triple super star chance (from Leo)
        - 10x super star spawn chance
        """
        # Triple chance gives 3 instead of 1
        p_triple = self.stats.triple_super_star_chance
        # 10x chance gives 10 instead of 1
        p_10x = self.stats.super_star_10x_chance
        
        # These are likely exclusive, calculate expected value
        # Probability of 10x (highest priority assumed)
        # Probability of triple (if not 10x)
        # Probability of single (if neither)
        
        # Simplified: treat as independent multipliers
        base_count = 1
        base_count *= (1 + p_triple * 2)  # +2 additional on triple
        base_count *= (1 + p_10x * 9)     # +9 additional on 10x
        
        return base_count
    
    def calculate_super_star_multiplier_per_star(self) -> float:
        """
        Calculate expected multiplier per super star from special effects.
        """
        p_supernova = self.stats.super_star_supernova_chance
        p_supergiant = self.stats.super_star_supergiant_chance
        p_radiant = self.stats.super_star_radiant_chance
        
        supernova_contribution = 1 + p_supernova * (self.stats.super_star_supernova_mult - 1)
        supergiant_contribution = 1 + p_supergiant * (self.stats.super_star_supergiant_mult - 1)
        radiant_contribution = 1 + p_radiant * (self.stats.super_star_radiant_mult - 1)
        
        # Novagiant combo for super stars
        p_novagiant = p_supernova * p_supergiant
        novagiant_contribution = 1 + p_novagiant * (self.stats.novagiant_combo_mult - 1)
        
        total_mult = supernova_contribution * supergiant_contribution * radiant_contribution * novagiant_contribution
        total_mult *= self.stats.all_star_mult
        
        return total_mult
    
    def calculate_super_star_spawn_rate_per_hour(self) -> float:
        """
        Calculate the number of super star spawn events per hour.
        
        IMPORTANT: Super Star spawns are EXCLUSIVE with Double/Triple Star spawns.
        At each spawn event, either:
        - A Super Star spawns (with possible triple/10x effects)
        - OR a Regular Star spawns (with possible double/triple effects)
        
        The base chance is 1/100 per star spawn event, modified by Super Star Spawn Rate Multiplier.
        """
        # Number of star spawn events per hour
        star_spawn_events = self.calculate_star_spawn_rate_per_hour()
        
        # Chance that a spawn event is a Super Star (exclusive with regular stars)
        base_super_chance = BASE_SUPER_STAR_SPAWN_CHANCE  # 1/100 = 0.01
        modified_super_chance = base_super_chance * self.stats.super_star_spawn_rate_mult
        
        # Super star spawn events = total spawn events * chance per event
        super_spawns_per_hour = star_spawn_events * modified_super_chance
        return super_spawns_per_hour
    
    def calculate_super_stars_per_hour(self) -> float:
        """
        Calculate total expected super stars per hour.
        """
        spawns_per_hour = self.calculate_super_star_spawn_rate_per_hour()
        super_stars_per_spawn = self.calculate_super_stars_per_spawn()
        mult_per_star = self.calculate_super_star_multiplier_per_star()
        
        return spawns_per_hour * super_stars_per_spawn * mult_per_star
    
    def calculate_auto_caught_super_stars_per_hour(self) -> float:
        """
        Calculate super stars automatically caught per hour (offline gains).
        
        Offline gains formula:
        - Without CTRL+F Stars: auto_catch * spawn_rate * 0.2 (1 of 5 floors)
        - With CTRL+F Stars: auto_catch * spawn_rate * 1.0 (follows through all 5 floors)
        """
        total_super_stars = self.calculate_super_stars_per_hour()
        
        # Offline gains multiplier: 0.2 without CTRL+F, 1.0 with CTRL+F
        offline_mult = 1.0 if self.stats.ctrl_f_stars_enabled else 0.2
        
        return total_super_stars * self.stats.auto_catch_chance * offline_mult
    
    # =========================================================================
    # UPGRADE EFFICIENCY CALCULATIONS
    # =========================================================================
    
    def calculate_upgrade_efficiency(
        self,
        upgrade_type: str,
        upgrade_key: str,
        current_level: int,
        target_metric: str = 'stars_per_hour'
    ) -> Dict:
        """
        Calculate the efficiency of an upgrade (gain per cost).
        
        Args:
            upgrade_type: 'star', 'stargazing', or 'super_star'
            upgrade_key: The key of the upgrade
            current_level: Current level of the upgrade
            target_metric: 'stars_per_hour', 'super_stars_per_hour', or 'auto_catch'
        
        Returns:
            Dict with 'cost', 'gain', 'efficiency', 'new_value'
        """
        # Get current metric value
        if target_metric == 'stars_per_hour':
            current_value = self.calculate_stars_per_hour()
        elif target_metric == 'super_stars_per_hour':
            current_value = self.calculate_super_stars_per_hour()
        elif target_metric == 'auto_catch':
            current_value = self.stats.auto_catch_chance
        else:
            return {'cost': 0, 'gain': 0, 'efficiency': 0, 'new_value': 0}
        
        # Calculate cost
        if upgrade_type == 'star':
            cost = get_star_upgrade_cost(upgrade_key, current_level)
        elif upgrade_type == 'super_star':
            cost = get_super_star_upgrade_cost(upgrade_key, current_level)
        else:
            cost = 0  # TODO: Implement stargazing upgrade costs
        
        if cost == 0:
            return {'cost': 0, 'gain': 0, 'efficiency': 0, 'new_value': current_value}
        
        # Simulate upgrade and calculate new value
        # This requires modifying stats temporarily
        new_value = self._simulate_upgrade(upgrade_type, upgrade_key, target_metric)
        
        gain = new_value - current_value
        efficiency = gain / cost if cost > 0 else 0
        
        return {
            'cost': cost,
            'gain': gain,
            'efficiency': efficiency,
            'new_value': new_value,
            'current_value': current_value,
        }
    
    def _simulate_upgrade(
        self,
        upgrade_type: str,
        upgrade_key: str,
        target_metric: str
    ) -> float:
        """
        Simulate the effect of an upgrade and return the new metric value.
        
        This creates a temporary copy of stats with the upgrade applied.
        """
        # Create a copy of stats
        import copy
        temp_stats = copy.copy(self.stats)
        
        # Apply upgrade effect
        if upgrade_type == 'star':
            # Star upgrades affect various stats based on star type
            star = STARS.get(upgrade_key)
            if star:
                # Each star gives specific bonuses
                # This is simplified - full implementation would track all star levels
                pass
        
        elif upgrade_type == 'stargazing':
            upgrade = STARGAZING_UPGRADES.get(upgrade_key)
            if upgrade:
                effect = upgrade['effect_per_level']
                if upgrade_key == 'auto_catch':
                    temp_stats.auto_catch_chance += effect
                elif upgrade_key == 'star_spawn_rate':
                    temp_stats.star_spawn_rate_mult += effect
                elif upgrade_key == 'double_star_chance':
                    temp_stats.double_star_chance += effect
                elif upgrade_key == 'super_star_spawn_rate':
                    temp_stats.super_star_spawn_rate_mult += effect
                elif upgrade_key == 'star_supernova_chance':
                    temp_stats.star_supernova_chance += effect
                elif upgrade_key == 'star_supergiant_chance':
                    temp_stats.star_supergiant_chance += effect
        
        elif upgrade_type == 'super_star':
            upgrade = SUPER_STAR_UPGRADES.get(upgrade_key)
            if upgrade:
                effect = upgrade['effect_per_level']
                if upgrade_key == 'game_speed':
                    # Game speed increases floor clears per hour
                    temp_stats.floor_clears_per_hour *= (1 + effect)
                elif upgrade_key == 'supergiant_star_multiplier':
                    temp_stats.star_supergiant_mult += effect
                    temp_stats.super_star_supergiant_mult += effect
        
        # Create temporary calculator
        temp_calc = StargazingCalculator(temp_stats)
        
        # Calculate new metric
        if target_metric == 'stars_per_hour':
            return temp_calc.calculate_stars_per_hour()
        elif target_metric == 'super_stars_per_hour':
            return temp_calc.calculate_super_stars_per_hour()
        elif target_metric == 'auto_catch':
            return temp_stats.auto_catch_chance
        
        return 0
    
    def get_best_upgrade_for_stars(
        self,
        available_upgrades: List[Tuple[str, str, int]],
        max_cost: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Find the best upgrade for increasing stars per hour.
        
        Args:
            available_upgrades: List of (upgrade_type, upgrade_key, current_level)
            max_cost: Maximum cost to consider (None = no limit)
        
        Returns:
            Dict with best upgrade info, or None if no upgrades available
        """
        best = None
        best_efficiency = 0
        
        for upgrade_type, upgrade_key, current_level in available_upgrades:
            result = self.calculate_upgrade_efficiency(
                upgrade_type, upgrade_key, current_level, 'stars_per_hour'
            )
            
            if result['cost'] == 0:
                continue
            
            if max_cost is not None and result['cost'] > max_cost:
                continue
            
            if result['efficiency'] > best_efficiency:
                best_efficiency = result['efficiency']
                best = {
                    'upgrade_type': upgrade_type,
                    'upgrade_key': upgrade_key,
                    'current_level': current_level,
                    **result
                }
        
        return best
    
    # =========================================================================
    # SUMMARY AND DISPLAY
    # =========================================================================
    
    def get_summary(self) -> Dict:
        """
        Get a summary of all calculated values.
        """
        return {
            # Star calculations
            'star_spawn_rate_per_hour': self.calculate_star_spawn_rate_per_hour(),
            'stars_per_spawn': self.calculate_stars_per_spawn(),
            'star_multiplier': self.calculate_star_multiplier_per_star(),
            'stars_per_hour': self.calculate_stars_per_hour(),
            'auto_caught_stars_per_hour': self.calculate_auto_caught_stars_per_hour(),
            
            # Super star calculations
            'super_star_spawn_rate_per_hour': self.calculate_super_star_spawn_rate_per_hour(),
            'super_stars_per_spawn': self.calculate_super_stars_per_spawn(),
            'super_star_multiplier': self.calculate_super_star_multiplier_per_star(),
            'super_stars_per_hour': self.calculate_super_stars_per_hour(),
            'auto_caught_super_stars_per_hour': self.calculate_auto_caught_super_stars_per_hour(),
            
            # Key stats
            'auto_catch_chance': self.stats.auto_catch_chance,
            'floor_clears_per_hour': self.stats.floor_clears_per_hour,
        }


def create_calculator_from_upgrades(
    telescope_level: int,
    stargazing_upgrades: Dict[str, int],
    super_star_upgrades: Dict[str, int],
    star_levels: Dict[str, int],
    floor_clears_per_hour: float = 120.0
) -> StargazingCalculator:
    """
    Create a calculator from upgrade levels.
    
    This is the main factory function for creating a calculator with all bonuses applied.
    """
    stats = PlayerStargazingStats(
        telescope_level=telescope_level,
        floor_clears_per_hour=floor_clears_per_hour
    )
    
    # Apply stargazing upgrade bonuses
    for key, level in stargazing_upgrades.items():
        if key not in STARGAZING_UPGRADES:
            continue
        
        upgrade = STARGAZING_UPGRADES[key]
        effect = upgrade['effect_per_level'] * level
        
        if key == 'auto_catch':
            stats.auto_catch_chance += effect
        elif key == 'star_spawn_rate':
            stats.star_spawn_rate_mult += effect
        elif key == 'double_star_chance':
            stats.double_star_chance += effect
        elif key == 'super_star_spawn_rate':
            stats.super_star_spawn_rate_mult += effect
        elif key == 'star_supernova_chance':
            stats.star_supernova_chance += effect
        elif key == 'super_star_10x_chance':
            stats.super_star_10x_chance += effect
        elif key == 'star_supergiant_chance':
            stats.star_supergiant_chance += effect
        elif key == 'super_star_supergiant_chance':
            stats.super_star_supergiant_chance += effect
        elif key == 'all_star_multiplier':
            stats.all_star_mult += effect
        elif key == 'super_star_radiant_chance':
            stats.super_star_radiant_chance += effect
    
    # Apply super star upgrade bonuses
    for key, level in super_star_upgrades.items():
        if key not in SUPER_STAR_UPGRADES:
            continue
        
        upgrade = SUPER_STAR_UPGRADES[key]
        effect = upgrade['effect_per_level'] * level
        
        if key == 'game_speed':
            # Game speed increases floor clears per hour
            stats.floor_clears_per_hour *= (1 + effect)
        elif key == 'supergiant_star_multiplier':
            stats.star_supergiant_mult += effect
            stats.super_star_supergiant_mult += effect
        elif key == 'novagiant_combo_multiplier':
            stats.novagiant_combo_mult += effect
    
    # Apply star bonuses
    for star_key, level in star_levels.items():
        if star_key not in STARS:
            continue
        
        star = STARS[star_key]
        
        # Apply star-specific bonuses
        if star_key == 'taurus':
            # Taurus gives auto-catch
            stats.auto_catch_chance += star.perk2_value * level
        elif star_key == 'gemini':
            # Gemini gives star spawn rate
            stats.star_spawn_rate_mult += star.perk2_value * level
        elif star_key == 'leo':
            # Leo gives triple super star chance
            stats.triple_super_star_chance += star.perk2_value * level
        elif star_key == 'virgo':
            # Virgo gives super star spawn rate
            stats.super_star_spawn_rate_mult += star.perk2_value * level
        elif star_key == 'sagittarius':
            # Sagittarius gives triple star chance
            stats.triple_star_chance += star.perk2_value * level
        elif star_key == 'scorpio':
            # Scorpio gives all star multi
            stats.all_star_mult += star.perk2_value * level
        elif star_key == 'hercules':
            # Hercules gives star supernova chance
            stats.star_supernova_chance += star.perk1_value * level
    
    return StargazingCalculator(stats)
