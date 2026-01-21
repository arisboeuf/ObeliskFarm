"""
Stargazing Data Module

Contains all constants, upgrade costs, and star data from the Idle Obelisk Miner wiki.
Source: https://shminer.miraheze.org/wiki/Stargazing
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# =============================================================================
# GAME CONSTANTS
# =============================================================================

# Base spawn rates
BASE_STAR_SPAWN_CHANCE = 1 / 50  # 2% base chance per floor clear
BASE_SUPER_STAR_SPAWN_CHANCE = 1 / 100  # 1% base chance when regular star spawns

# Floor changes every 30 minutes (at xx:00 and xx:30)
FLOOR_CHANGE_INTERVAL_MINUTES = 30

# =============================================================================
# STAR DATA
# =============================================================================

@dataclass
class StarInfo:
    """Information about a star type"""
    name: str
    perk1: str
    perk1_value: float
    perk2: str
    perk2_value: float
    base_max_level: int
    max_level: int  # After all cap increases
    unlock_order: int  # 1=Aries, 2=Taurus, etc.
    cost_multiplier: float  # Cost scaling per level (usually 1.25)
    base_cost: int  # Cost for level 2


# Stars data from wiki
STARS: Dict[str, StarInfo] = {
    'aries': StarInfo(
        name='Aries',
        perk1='Vein Spawn Rate', perk1_value=0.03,
        perk2='Golden Vein Chance', perk2_value=0.01,
        base_max_level=20, max_level=28,
        unlock_order=1, cost_multiplier=1.25, base_cost=150
    ),
    'taurus': StarInfo(
        name='Taurus',
        perk1='Pickaxe Damage', perk1_value=0.12,
        perk2='Auto catch Stars', perk2_value=0.02,
        base_max_level=20, max_level=22,
        unlock_order=2, cost_multiplier=1.25, base_cost=150
    ),
    'gemini': StarInfo(
        name='Gemini',
        perk1='Golden Floor Multi', perk1_value=0.02,  # 1.02x
        perk2='Star Spawn Rate', perk2_value=0.02,
        base_max_level=20, max_level=34,
        unlock_order=3, cost_multiplier=1.25, base_cost=150
    ),
    'cancer': StarInfo(
        name='Cancer',
        perk1='Double Contract Point Chance', perk1_value=0.01,
        perk2='Contract Upgrade Cost', perk2_value=-0.01,
        base_max_level=20, max_level=48,
        unlock_order=4, cost_multiplier=1.25, base_cost=300
    ),
    'leo': StarInfo(
        name='Leo',
        perk1='Workshop Cap', perk1_value=1,
        perk2='Triple Super Star Chance', perk2_value=0.04,
        base_max_level=3, max_level=5,
        unlock_order=5, cost_multiplier=3.0, base_cost=10000
    ),
    'virgo': StarInfo(
        name='Virgo',
        perk1='Bomb Recharge Rate', perk1_value=0.01,
        perk2='Super Star Spawn Rate', perk2_value=0.01,
        base_max_level=25, max_level=30,
        unlock_order=6, cost_multiplier=1.25, base_cost=300
    ),
    'libra': StarInfo(
        name='Libra',
        perk1='Prestige Points Gain', perk1_value=0.05,
        perk2='Triple Lootbug Chance', perk2_value=0.01,
        base_max_level=20, max_level=22,
        unlock_order=7, cost_multiplier=1.25, base_cost=300
    ),
    'scorpio': StarInfo(
        name='Scorpio',
        perk1='Pickaxe Damage', perk1_value=0.15,
        perk2='All Star Multi', perk2_value=0.005,
        base_max_level=50, max_level=117,
        unlock_order=8, cost_multiplier=1.15, base_cost=150
    ),
    'sagittarius': StarInfo(
        name='Sagittarius',
        perk1='Lootbug Spawn Rate', perk1_value=0.02,
        perk2='Triple Star Chance', perk2_value=0.01,
        base_max_level=15, max_level=17,
        unlock_order=9, cost_multiplier=1.25, base_cost=500
    ),
    'capricorn': StarInfo(
        name='Capricorn',
        perk1='Experience Gain', perk1_value=0.15,
        perk2='Item Duration', perk2_value=0.01,
        base_max_level=20, max_level=63,
        unlock_order=10, cost_multiplier=1.25, base_cost=300
    ),
    'aquarius': StarInfo(
        name='Aquarius',
        perk1='Bar Craft Costs', perk1_value=-0.01,
        perk2='Golden Lootbug Chance', perk2_value=0.01,
        base_max_level=10, max_level=25,
        unlock_order=11, cost_multiplier=1.40, base_cost=3000
    ),
    'pisces': StarInfo(
        name='Pisces',
        perk1='Pet Level Cap', perk1_value=1,
        perk2='Rainbow Floor Multi', perk2_value=10,  # 10x
        base_max_level=2, max_level=4,
        unlock_order=12, cost_multiplier=1.69, base_cost=100000
    ),
    'ophiuchus': StarInfo(
        name='Ophiuchus',
        perk1='Banked Freebie Cap', perk1_value=1,
        perk2='Banked Lootbug Cap', perk2_value=1,
        base_max_level=2, max_level=19,
        unlock_order=13, cost_multiplier=1.80, base_cost=125000
    ),
    'orion': StarInfo(
        name='Orion',
        perk1='100x Craft Chance', perk1_value=0.001,
        perk2='Golden Ore Chance', perk2_value=0.0025,
        base_max_level=20, max_level=43,
        unlock_order=14, cost_multiplier=1.27, base_cost=125000
    ),
    'hercules': StarInfo(
        name='Hercules',
        perk1='Star Supernova Chance', perk1_value=0.0015,
        perk2='Golden Ore Multi', perk2_value=0.08,
        base_max_level=20, max_level=55,
        unlock_order=15, cost_multiplier=1.29, base_cost=175000
    ),
    'draco': StarInfo(
        name='Draco',
        perk1='Galactic Rainbow Chance', perk1_value=0.0025,
        perk2='Galactic Rainbow Multi', perk2_value=0.10,
        base_max_level=20, max_level=30,
        unlock_order=16, cost_multiplier=1.30, base_cost=250000
    ),
    'cetus': StarInfo(
        name='Cetus',
        perk1='Polychrome Ore Card Multi', perk1_value=0.15,
        perk2='Fish Income Multi', perk2_value=0.02,
        base_max_level=20, max_level=32,
        unlock_order=17, cost_multiplier=1.30, base_cost=1020000
    ),
    'phoenix': StarInfo(
        name='Phoenix',
        perk1='Chain, Midas, Veinseeker, Starburst grade caps', perk1_value=1,
        perk2='', perk2_value=0,
        base_max_level=18, max_level=20,
        unlock_order=18, cost_multiplier=1.30, base_cost=2020000
    ),
    'eridanus': StarInfo(
        name='Eridanus',
        perk1='All Floor Multi', perk1_value=0.02,
        perk2='Stonks Multi +2%, Super Stonks Chance', perk2_value=0.001,
        base_max_level=20, max_level=22,
        unlock_order=19, cost_multiplier=1.30, base_cost=500_000_000_000  # 500b
    ),
}

# Star discovery costs: 1 gem for Aries, then 250*(N+1) for subsequent stars
def get_star_discovery_cost(stars_owned: int) -> int:
    """Get the cost to discover the next star"""
    if stars_owned == 0:
        return 1  # First star (Aries) costs 1 gem
    return 250 * (stars_owned + 1)


# =============================================================================
# STARGAZING UPGRADES (Regular Upgrades Tab)
# =============================================================================

@dataclass
class UpgradeInfo:
    """Information about a stargazing upgrade"""
    name: str
    description: str
    effect_per_level: float
    max_level: int
    telescope_required: int  # Telescope level required to unlock
    costs: List[Tuple[str, int]]  # List of (currency_type, amount) per level


# Upgrade costs from wiki - these are complex with different currencies
# Simplified to store just the Super Star costs where applicable

STARGAZING_UPGRADES: Dict[str, dict] = {
    'telescope': {
        'name': 'Upgrade Telescope',
        'description': 'Unlocks ability to discover more Stars +1',
        'effect_per_level': 1,
        'max_level': 19,
        'telescope_required': 0,
        # Mixed costs (Veins + Super Stars), simplified
    },
    'auto_catch': {
        'name': 'Auto-catch Stars',
        'description': 'Chance to automatically catch a star +4%',
        'effect_per_level': 0.04,
        'max_level': 15,
        'telescope_required': 0,
    },
    'star_spawn_rate': {
        'name': 'Star Spawn Rate',
        'description': 'Increases rate that Stars appear +5%',
        'effect_per_level': 0.05,
        'max_level': 20,
        'telescope_required': 0,
    },
    'double_star_chance': {
        'name': 'Double Star Chance',
        'description': 'Chance for 2 Stars to appear at once +5%',
        'effect_per_level': 0.05,
        'max_level': 20,
        'telescope_required': 0,
    },
    'super_star_spawn_rate': {
        'name': 'Super Star Spawn Rate',
        'description': 'Increases rate that Super Stars appear +2%',
        'effect_per_level': 0.02,
        'max_level': 25,  # Can go to 25 with Capper Upper
        'telescope_required': 0,
    },
    'star_supernova_chance': {
        'name': 'Star Supernova Chance',
        'description': 'Stars can Supernova, giving 10x stars +0.5%',
        'effect_per_level': 0.005,
        'max_level': 25,  # Can go to 25 with Capper Upper
        'telescope_required': 10,
    },
    'super_star_10x_chance': {
        'name': 'Super Star 10x Chance',
        'description': 'Chance for 10x Super Stars to spawn at once +0.2%',
        'effect_per_level': 0.002,
        'max_level': 25,  # Can go to 25 with Capper Upper
        'telescope_required': 12,
    },
    'star_supergiant_chance': {
        'name': 'Star Supergiant Chance',
        'description': 'Stars can Supergiant, giving bonus multipliers +0.2%',
        'effect_per_level': 0.002,
        'max_level': 25,  # Can go to 25 with Capper Upper
        'telescope_required': 14,
    },
    'capper_upper': {
        'name': 'Capper Upper',
        'description': 'Increases the cap of the previous four upgrades',
        'effect_per_level': 1,  # +1 max level to those upgrades
        'max_level': 5,
        'telescope_required': 17,
    },
    'super_star_supergiant_chance': {
        'name': 'Super Star Supergiant Chance',
        'description': 'Chance for Super Stars to Supergiant +0.15%',
        'effect_per_level': 0.0015,
        'max_level': 20,
        'telescope_required': 18,
    },
    'all_star_multiplier': {
        'name': 'All Star Multiplier',
        'description': 'Increase the value of all Stars +0.01x',
        'effect_per_level': 0.01,
        'max_level': 30,
        'telescope_required': 18,
    },
    'super_star_radiant_chance': {
        'name': 'Super Star Radiant Chance',
        'description': 'Chance for Super Stars to become Radiant +0.15%',
        'effect_per_level': 0.0015,
        'max_level': 25,
        'telescope_required': 19,
    },
}


# =============================================================================
# SUPER STAR UPGRADES
# =============================================================================

SUPER_STAR_UPGRADES: Dict[str, dict] = {
    'rainbow_vein_chance': {
        'name': 'Rainbow Vein Chance',
        'description': 'Rainbow Vein Chance +1%',
        'effect_per_level': 0.01,
        'max_level': 10,
        'unlock_level': 0,  # Stars needed in previous upgrade to unlock
        'costs': [15, 20, 25, 33, 43, 56, 72, 94, 122, 159],  # Super Stars
    },
    'double_contract_points': {
        'name': 'Double Contract Points',
        'description': 'Double Contract Points +2%',
        'effect_per_level': 0.02,
        'max_level': 10,
        'unlock_level': 5,
        'costs': [20, 26, 34, 44, 57, 74, 97, 125, 163, 212],
    },
    'experience_gain': {
        'name': 'Experience Gain',
        'description': 'Experience +25%',
        'effect_per_level': 0.25,
        'max_level': 10,
        'unlock_level': 5,
        'costs': [25, 33, 42, 55, 71, 93, 121, 157, 204, 265],
    },
    'item_duration': {
        'name': 'Item Duration',
        'description': 'Item duration +3%',
        'effect_per_level': 0.03,
        'max_level': 10,
        'unlock_level': 5,
        'costs': [30, 39, 51, 66, 86, 111, 145, 188, 245, 318],
    },
    'game_speed': {
        'name': 'Base Game Speed',
        'description': 'Game speed +2%',
        'effect_per_level': 0.02,
        'max_level': 10,
        'unlock_level': 5,
        'costs': [150, 195, 254, 330, 428, 557, 724, 941, 1224, 1591],
    },
    'star_level_caps': {
        'name': 'Star Level Caps',
        'description': 'Star Level Caps +1',
        'effect_per_level': 1,
        'max_level': 2,
        'unlock_level': 5,
        'costs': [1500, 6900],
    },
    'aries_gemini_cancer_cap': {
        'name': 'Aries, Gemini, Cancer Cap',
        'description': 'Aries, Gemini, Cancer Cap +2',
        'effect_per_level': 2,
        'max_level': 3,
        'unlock_level': 2,
        'costs': [2000, 3500, 6125],
    },
    'virgo_aqua_ophi_cap': {
        'name': 'Virgo, Aqua, Ophi Cap',
        'description': 'Virgo, Aquarius, Ophiuchus Cap +1',
        'effect_per_level': 1,
        'max_level': 3,
        'unlock_level': 3,
        'costs': [3500, 6125, 9750],
    },
    'supergiant_star_multiplier': {
        'name': 'Supergiant Star Multiplier',
        'description': 'Supergiant Star Multiplier +10%',
        'effect_per_level': 0.10,
        'max_level': 20,
        'unlock_level': 3,
        'telescope_required': 14,
        'costs': [3000, 3900, 5070, 6591, 8568, 11100, 14500, 18800, 24500, 31800,
                  41400, 53800, 69900, 90900, 118000, 154000, 200000, 260000, 337000, 439000],
    },
    'golden_ore_multiplier': {
        'name': 'Golden Ore Multiplier',
        'description': 'Golden Ore Multiplier +0.06x',
        'effect_per_level': 0.06,
        'max_level': 15,
        'unlock_level': 15,
        'telescope_required': 17,
        'costs': [50000, 62500, 78100, 97700, 122000, 153000, 191000, 238000, 298000, 373000,
                  466000, 582000, 728000, 909000, 1140000],
    },
    'banked_freebies_lootbugs': {
        'name': 'Banked Freebies & Lootbugs',
        'description': 'Banked Freebies & Lootbugs +1',
        'effect_per_level': 1,
        'max_level': 5,
        'unlock_level': 5,
        'telescope_required': 17,
        'costs': [100000, 130000, 169000, 220000, 286000],
    },
    'elixir_void_grade_cap': {
        'name': 'Elixir & Void Grade Cap',
        'description': 'Elixir & Void Grade Cap +2',
        'effect_per_level': 2,
        'max_level': 5,
        'unlock_level': 5,
        'telescope_required': 17,
        'costs': [175000, 228000, 296000, 384000, 500000],
    },
    'unlock_black_hole': {
        'name': 'Unlock the Black Hole',
        'description': 'Unlock the Black Hole',
        'effect_per_level': 1,
        'max_level': 1,
        'unlock_level': 5,
        'telescope_required': 18,
        'costs': [2500000],
    },
    'lootbug_loot_multiplier': {
        'name': 'Lootbug Loot Multiplier',
        'description': 'Lootbug Loot Multiplier +1.5%',
        'effect_per_level': 0.015,
        'max_level': 20,
        'unlock_level': 1,
        'telescope_required': 18,
        'costs': [875000, 1180000, 1590000, 2150000, 2910000, 3920000, 5300000, 7150000, 9650000, 13000000,
                  17600000, 23800000, 32100000, 43300000, 58400000, 78900000, 106000000, 144000000, 194000000, 262000000],
    },
    'novagiant_combo_multiplier': {
        'name': 'Novagiant Combo Multiplier',
        'description': 'Novagiant Combo Multiplier +2%',
        'effect_per_level': 0.02,
        'max_level': 15,
        'unlock_level': 5,
        'telescope_required': 18,
        'costs': [1150000, 1550000, 2100000, 2830000, 3820000, 5160000, 6960000, 9400000, 12700000, 17100000,
                  23100000, 31200000, 42100000, 56900000, 76800000],
    },
    'fish_income_multiplier': {
        'name': 'Fish Income Multiplier',
        'description': 'Fish Income Multiplier +1.25%',
        'effect_per_level': 0.0125,
        'max_level': 15,
        'unlock_level': 5,
        'telescope_required': 18,
        'costs': [1350000, 1820000, 2460000, 3320000, 4480000, 6050000, 8170000, 11000000, 14900000, 20100000,
                  27100000, 36600000, 49500000, 66800000, 90200000],
    },
    'galactic_floor_chance': {
        'name': 'Galactic Floor Chance',
        'description': 'Galactic Floor Chance +0.25%',
        'effect_per_level': 0.0025,
        'max_level': 20,
        'unlock_level': 5,
        'telescope_required': 19,
        # Costs not provided in wiki extract, estimated
    },
    'golden_ore_chance': {
        'name': 'Golden Ore Chance',
        'description': 'Golden Ore Chance +0.3%',
        'effect_per_level': 0.003,
        'max_level': 20,
        'unlock_level': 5,
        'telescope_required': 19,
    },
    'star_radiant_chance': {
        'name': 'Star Radiant Chance',
        'description': 'Star Radiant Chance +0.1%',
        'effect_per_level': 0.001,
        'max_level': 20,
        'unlock_level': 5,
        'telescope_required': 19,
    },
}


# =============================================================================
# STAR STAT CATEGORIES
# =============================================================================

# Stats that affect star income rate
STAR_RATE_STATS = [
    'star_spawn_rate_mult',      # Multiplicative increase to star spawn rate
    'double_star_chance',        # Chance for 2 stars
    'triple_star_chance',        # Chance for 3 stars
    'star_supernova_chance',     # 10x stars chance
    'star_supernova_mult',       # Increases supernova multiplier
    'star_supergiant_chance',    # 3x stars chance
    'star_supergiant_mult',      # Increases supergiant multiplier
    'star_radiant_chance',       # 10x stars chance (radiant)
    'star_radiant_mult',         # Increases radiant multiplier
    'all_star_mult',             # Multiplies all star income
    'novagiant_combo_mult',      # Multiplier when both supernova and supergiant
]

SUPER_STAR_RATE_STATS = [
    'super_star_spawn_rate_mult',    # Multiplicative increase to super star spawn rate
    'triple_super_star_chance',      # Chance for 3 super stars (from Leo)
    'super_star_10x_chance',         # Chance for 10 super stars
    'super_star_supernova_chance',   # 10x super stars chance
    'super_star_supernova_mult',     # Increases super star supernova multiplier
    'super_star_supergiant_chance',  # 3x super stars chance
    'super_star_supergiant_mult',    # Increases super star supergiant multiplier
    'super_star_radiant_chance',     # 10x super stars chance
    'super_star_radiant_mult',       # Increases super star radiant multiplier
    'all_star_mult',                 # Multiplies all star income (affects super stars too)
]

AUTO_CATCH_STATS = [
    'auto_catch_chance',  # Chance to auto-catch stars
]


# =============================================================================
# FLOOR DATA FOR STAR SPAWNS
# =============================================================================

# Stars spawn on specific floors - this affects offline farming strategy
# Each star can appear on 5 different floor sets

STAR_FLOORS: Dict[str, List[int]] = {
    'aries': [19, 8, 12, 26, 22],
    'taurus': [9, 6, 27, 36, 3],
    'gemini': [50, 40, 18, 60, 55],
    'cancer': [39, 28, 4, 47, 41],
    'leo': [43, 58, 5, 13, 26],
    'virgo': [17, 23, 58, 41, 12],
    'libra': [42, 13, 39, 4, 17],
    'scorpio': [27, 59, 44, 21, 36],
    'sagittarius': [59, 17, 21, 7, 46],
    'capricorn': [2, 30, 57, 54, 5],
    'aquarius': [12, 51, 34, 17, 29],
    'pisces': [60, 18, 17, 3, 13],
    'ophiuchus': [48, 45, 52, 56, 53],
    'orion': [65, 67, 69, 73, 75],
    'hercules': [67, 73, 76, 79, 81],
    'draco': [82, 84, 86, 88, 90],
    'cetus': [91, 94, 95, 98, 99],
    'phoenix': [92, 93, 100, 97, 102],
    'eridanus': [105, 106, 110, 113, 115],
}


# =============================================================================
# BLACK HOLE BONUSES
# =============================================================================

BLACK_HOLE_BONUSES = [
    {'level': 1, 'bonus': 'Frogger Drone Enhancement (Unlocks Lootfrogs)'},
    {'level': 2, 'bonus': 'Leprechaun Pet Cap +2'},
    {'level': 3, 'bonus': 'Super Stonks Chance +2%'},
    {'level': 4, 'bonus': 'Unlock Item: Golden Strawberries'},
    {'level': 5, 'bonus': 'Galactic Floor Chance +3%'},
    {'level': 6, 'bonus': 'Golden Lootfrog Chance +2%'},
    {'level': 7, 'bonus': 'Draco and Orion Star Cap +5'},
    {'level': 8, 'bonus': 'Lootbug Banked Cap 1.20x'},
    {'level': 9, 'bonus': 'Bear Drone Cap +10'},
    {'level': 10, 'bonus': 'Tier 2 Dock Power +25%'},
    {'level': 11, 'bonus': 'Rainbow Void Portal Chance +5%'},
    {'level': 12, 'bonus': 'Mr Nibbles Pet Cap +2'},
    {'level': 13, 'bonus': 'Unlock Item: Golden Primal Meat'},
    {'level': 14, 'bonus': 'Gleaming Vein Chance +5%'},
    {'level': 15, 'bonus': 'Scorpio Star Cap +40'},
    {'level': 16, 'bonus': 'Unlock Bomb: Golden Veinmorpher'},
    {'level': 17, 'bonus': 'Ultra Stonks Chance +2%'},
    {'level': 18, 'bonus': 'Unlock Item: Golden Lollipop'},
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_star_upgrade_cost(star_key: str, current_level: int) -> int:
    """
    Calculate the cost to upgrade a star from current_level to current_level + 1.
    
    Formula: base_cost * (cost_multiplier ^ (level - 2))
    Level 2 costs base_cost, level 3 costs base_cost * multiplier, etc.
    """
    if star_key not in STARS:
        return 0
    
    star = STARS[star_key]
    if current_level < 1 or current_level >= star.max_level:
        return 0
    
    # Cost for going from level N to level N+1
    # Level 2 is base_cost, level 3 is base_cost * mult, etc.
    return int(star.base_cost * (star.cost_multiplier ** (current_level - 1)))


def get_total_star_cost(star_key: str, from_level: int, to_level: int) -> int:
    """Calculate total cost to upgrade a star from from_level to to_level"""
    total = 0
    for lvl in range(from_level, to_level):
        total += get_star_upgrade_cost(star_key, lvl)
    return total


def get_super_star_upgrade_cost(upgrade_key: str, current_level: int) -> int:
    """Get the cost to upgrade a super star upgrade from current_level to current_level + 1"""
    if upgrade_key not in SUPER_STAR_UPGRADES:
        return 0
    
    upgrade = SUPER_STAR_UPGRADES[upgrade_key]
    costs = upgrade.get('costs', [])
    
    if current_level < 0 or current_level >= len(costs):
        return 0
    
    return costs[current_level]


def format_number(n: float) -> str:
    """Format large numbers with k, m, b, t suffixes"""
    if n >= 1_000_000_000_000:
        return f"{n / 1_000_000_000_000:.2f}t"
    elif n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}b"
    elif n >= 1_000_000:
        return f"{n / 1_000_000:.2f}m"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}k"
    else:
        return f"{n:.0f}"
