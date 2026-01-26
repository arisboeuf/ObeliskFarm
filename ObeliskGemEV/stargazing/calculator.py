"""
Stargazing Calculator

Calculates stars and super stars per hour based on in-game stats.
Supports both online and offline calculations with CTRL+F Stars skill.
"""

from dataclasses import dataclass
from typing import Dict


# Base game constants
BASE_STAR_SPAWN_CHANCE = 1 / 50  # 2% per floor clear
BASE_SUPER_STAR_SPAWN_CHANCE = 1 / 100  # 1% per spawn event


@dataclass
class PlayerStats:
    """
    Player stats from in-game stats page.
    
    All multipliers are stored as their actual value:
    - 1.0 = no bonus (100%)
    - 1.5 = 50% bonus (150%)
    
    All chances are stored as decimals (0.0 to 1.0):
    - 0.05 = 5% chance
    - 0.10 = 10% chance
    """
    
    # Floor clears per hour
    floor_clears_per_hour: float = 120.0
    
    # Star spawn rate multiplier
    star_spawn_rate_mult: float = 1.0
    
    # Auto-catch chance (0.0 to 1.0)
    auto_catch_chance: float = 0.0
    
    # Double/Triple star chances
    double_star_chance: float = 0.0
    triple_star_chance: float = 0.0
    
    # Super star spawn rate multiplier
    super_star_spawn_rate_mult: float = 1.0
    
    # Super star bonuses
    triple_super_star_chance: float = 0.0
    super_star_10x_chance: float = 0.0
    
    # Star multipliers
    star_supernova_chance: float = 0.0
    star_supernova_mult: float = 10.0
    star_supergiant_chance: float = 0.0
    star_supergiant_mult: float = 3.0
    star_radiant_chance: float = 0.0
    star_radiant_mult: float = 10.0
    
    # Super star multipliers
    super_star_supernova_chance: float = 0.0
    super_star_supernova_mult: float = 10.0
    super_star_supergiant_chance: float = 0.0
    super_star_supergiant_mult: float = 3.0
    super_star_radiant_chance: float = 0.0
    super_star_radiant_mult: float = 10.0
    
    # Global multipliers
    all_star_mult: float = 1.0
    novagiant_combo_mult: float = 1.0
    
    # CTRL+F Stars skill (multiplies offline gains by 5x)
    ctrl_f_stars_enabled: bool = False


class StargazingCalculator:
    """
    Calculates stars and super stars per hour.
    
    Game mechanics:
    1. Base chance: 1/50 (2%) per floor clear for a star to spawn
    2. Star Spawn Rate Multiplier: Increases the effective spawn chance
    3. At each spawn event, either:
       - A Super Star spawns (exclusive with regular stars)
       - OR a Regular Star spawns (can be single/double/triple)
    4. Double/Triple Star Chance: Only applies to regular star spawns
    5. Supernova/Supergiant/Radiant: Multipliers on individual stars
    6. All Star Multiplier: Final multiplier on all stars
    """
    
    def __init__(self, stats: PlayerStats):
        self.stats = stats
    
    def calculate_star_spawn_rate_per_hour(self) -> float:
        """Calculate the number of star spawn events per hour."""
        base_chance = BASE_STAR_SPAWN_CHANCE  # 1/50 = 0.02
        modified_chance = base_chance * self.stats.star_spawn_rate_mult
        modified_chance = min(modified_chance, 1.0)  # Cap at 100%
        return self.stats.floor_clears_per_hour * modified_chance
    
    def calculate_stars_per_spawn(self) -> float:
        """
        Calculate expected number of REGULAR stars per spawn event.
        
        Accounts for:
        - Double star chance (2 stars instead of 1)
        - Triple star chance (3 stars instead of 1)
        
        Note: Super Star spawns are exclusive with regular stars.
        """
        # Probability of super star spawn (exclusive with regular stars)
        base_super_chance = BASE_SUPER_STAR_SPAWN_CHANCE  # 1/100 = 0.01
        p_super_star = base_super_chance * self.stats.super_star_spawn_rate_mult
        
        # Probability of regular star spawn (when not super star)
        p_regular_star = 1 - p_super_star
        
        # Probability distribution for regular stars
        p_triple = self.stats.triple_star_chance
        p_double = self.stats.double_star_chance * (1 - p_triple)  # Only if not triple
        p_single = 1 - p_triple - p_double
        
        # Expected regular stars per spawn event
        expected = p_regular_star * (1 * p_single + 2 * p_double + 3 * p_triple)
        return expected
    
    def calculate_star_multiplier_per_star(self) -> float:
        """
        Calculate expected multiplier per star from special effects.
        
        Effects:
        - Supernova: 10x stars (default)
        - Supergiant: 3x stars (default)
        - Radiant: 10x stars (default)
        - Novagiant Combo: Extra multiplier when both supernova AND supergiant
        """
        p_supernova = self.stats.star_supernova_chance
        p_supergiant = self.stats.star_supergiant_chance
        p_radiant = self.stats.star_radiant_chance
        
        # Expected multiplier from each effect
        supernova_contribution = 1 + p_supernova * (self.stats.star_supernova_mult - 1)
        supergiant_contribution = 1 + p_supergiant * (self.stats.star_supergiant_mult - 1)
        radiant_contribution = 1 + p_radiant * (self.stats.star_radiant_mult - 1)
        
        # Novagiant combo: when both supernova AND supergiant occur
        p_novagiant = p_supernova * p_supergiant
        novagiant_contribution = 1 + p_novagiant * (self.stats.novagiant_combo_mult - 1)
        
        # Total multiplier (multiplicative stacking)
        total_mult = (supernova_contribution * supergiant_contribution * 
                     radiant_contribution * novagiant_contribution)
        
        # Apply all star multiplier
        total_mult *= self.stats.all_star_mult
        
        return total_mult
    
    def calculate_stars_per_hour_online(self) -> float:
        """Calculate total expected stars per hour (online/manual)."""
        spawns_per_hour = self.calculate_star_spawn_rate_per_hour()
        stars_per_spawn = self.calculate_stars_per_spawn()
        mult_per_star = self.calculate_star_multiplier_per_star()
        
        return spawns_per_hour * stars_per_spawn * mult_per_star
    
    def calculate_stars_per_hour_offline(self) -> float:
        """
        Calculate stars automatically caught per hour (offline/AFK).
        
        Offline gains formula:
        - Without CTRL+F Stars: auto_catch * spawn_rate * 0.2 (1 of 5 floors)
        - With CTRL+F Stars: auto_catch * spawn_rate * 1.0 (all 5 floors)
        """
        total_stars = self.calculate_stars_per_hour_online()
        
        # Offline gains multiplier: 0.2 without CTRL+F, 1.0 with CTRL+F
        offline_mult = 1.0 if self.stats.ctrl_f_stars_enabled else 0.2
        
        return total_stars * self.stats.auto_catch_chance * offline_mult
    
    def calculate_super_stars_per_spawn(self) -> float:
        """
        Calculate expected number of super stars per super star spawn event.
        
        Accounts for:
        - Triple super star chance (3 instead of 1)
        - 10x super star spawn chance (10 instead of 1)
        """
        base_count = 1
        base_count *= (1 + self.stats.triple_super_star_chance * 2)  # +2 additional on triple
        base_count *= (1 + self.stats.super_star_10x_chance * 9)     # +9 additional on 10x
        
        return base_count
    
    def calculate_super_star_multiplier_per_star(self) -> float:
        """Calculate expected multiplier per super star from special effects."""
        p_supernova = self.stats.super_star_supernova_chance
        p_supergiant = self.stats.super_star_supergiant_chance
        p_radiant = self.stats.super_star_radiant_chance
        
        supernova_contribution = 1 + p_supernova * (self.stats.super_star_supernova_mult - 1)
        supergiant_contribution = 1 + p_supergiant * (self.stats.super_star_supergiant_mult - 1)
        radiant_contribution = 1 + p_radiant * (self.stats.super_star_radiant_mult - 1)
        
        # Novagiant combo for super stars
        p_novagiant = p_supernova * p_supergiant
        novagiant_contribution = 1 + p_novagiant * (self.stats.novagiant_combo_mult - 1)
        
        total_mult = (supernova_contribution * supergiant_contribution * 
                     radiant_contribution * novagiant_contribution)
        total_mult *= self.stats.all_star_mult
        
        return total_mult
    
    def calculate_super_star_spawn_rate_per_hour(self) -> float:
        """
        Calculate the number of super star spawn events per hour.
        
        IMPORTANT: Super Star spawns are EXCLUSIVE with Double/Triple Star spawns.
        """
        # Number of star spawn events per hour
        star_spawn_events = self.calculate_star_spawn_rate_per_hour()
        
        # Chance that a spawn event is a Super Star
        base_super_chance = BASE_SUPER_STAR_SPAWN_CHANCE  # 1/100 = 0.01
        modified_super_chance = base_super_chance * self.stats.super_star_spawn_rate_mult
        
        # Super star spawn events = total spawn events * chance per event
        return star_spawn_events * modified_super_chance
    
    def calculate_super_stars_per_hour_online(self) -> float:
        """Calculate total expected super stars per hour (online/manual)."""
        spawns_per_hour = self.calculate_super_star_spawn_rate_per_hour()
        super_stars_per_spawn = self.calculate_super_stars_per_spawn()
        mult_per_star = self.calculate_super_star_multiplier_per_star()
        
        return spawns_per_hour * super_stars_per_spawn * mult_per_star
    
    def calculate_super_stars_per_hour_offline(self) -> float:
        """
        Calculate super stars automatically caught per hour (offline/AFK).
        
        Offline gains formula:
        - Without CTRL+F Stars: auto_catch * spawn_rate * 0.2 (1 of 5 floors)
        - With CTRL+F Stars: auto_catch * spawn_rate * 1.0 (all 5 floors)
        """
        total_super_stars = self.calculate_super_stars_per_hour_online()
        
        # Offline gains multiplier: 0.2 without CTRL+F, 1.0 with CTRL+F
        offline_mult = 1.0 if self.stats.ctrl_f_stars_enabled else 0.2
        
        return total_super_stars * self.stats.auto_catch_chance * offline_mult
    
    def get_summary(self) -> Dict:
        """Get a summary of all calculated values."""
        return {
            # Star calculations
            'star_spawn_rate_per_hour': self.calculate_star_spawn_rate_per_hour(),
            'stars_per_hour_online': self.calculate_stars_per_hour_online(),
            'stars_per_hour_offline': self.calculate_stars_per_hour_offline(),
            
            # Super star calculations
            'super_star_spawn_rate_per_hour': self.calculate_super_star_spawn_rate_per_hour(),
            'super_stars_per_hour_online': self.calculate_super_stars_per_hour_online(),
            'super_stars_per_hour_offline': self.calculate_super_stars_per_hour_offline(),
            
            # Key stats
            'floor_clears_per_hour': self.stats.floor_clears_per_hour,
            'auto_catch_chance': self.stats.auto_catch_chance,
            'ctrl_f_stars_enabled': self.stats.ctrl_f_stars_enabled,
        }
