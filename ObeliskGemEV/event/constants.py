"""
Constants and game data for Event Simulator.
All upgrade data, costs, prestige requirements etc.

Data sourced from: https://shminer.miraheze.org/wiki/Events
"""

# Upgrade names for display (matches wiki exactly)
UPGRADE_NAMES = {
    1: ["+1 Atk Dmg", "+2 Max Hp", "+0.02 Atk Spd", "+0.03 Move Spd", 
        "+2% Event Game Spd", "+1% Crit Chance, +0.10 Crit Dmg", 
        "+1 Atk Dmg +2 Max Hp", "+1 Tier 1 Upgrade Caps", 
        "+1% Prestige Bonus", "+3 Atk Dmg, +3 Max Hp"],
    2: ["+3 Max Hp", "-0.02 Enemy Atk Spd", "-1 Enemy Atk Dmg", 
        "-1% E.Crit, -0.10 E.Crit Dmg", "+1 Atk Dmg, +0.01 Atk Spd", 
        "+1 Tier 2 Upgrade Caps", "+2% Prestige Bonus"],
    3: ["+2 Atk Dmg", "+0.02 Atk Spd", "+1% Crit Chance", "+3% Event Game Spd",
        "+3 Atk Dmg, +3 Max Hp", "+1 Tier 3 Upgrade Caps", 
        "+3% 5x Drop Chance", "+5 Max Hp, +0.03 Atk Spd"],
    4: ["+1% Block Chance", "+5 Max Hp", "+0.10 Crit Dmg, -0.10 E.Crit Dmg",
        "+0.02 Atk Spd, +0.02 Move Spd", "+4 Max Hp, +4 Atk Dmg", 
        "+1 Tier 4 Upgrade Caps", "+1 Cap Of Cap Upgrades", 
        "+10 Max Hp, +0.05 Atk Spd"]
}

GEM_UPGRADE_NAMES = ["+10% Dmg", "+10% Max HP", "+125% Event Game Spd", "2x Event Currencies"]

# Short names for compact display
UPGRADE_SHORT_NAMES = {
    1: ["ATK +1", "HP +2", "ASpd +0.02", "MSpd +0.03", 
        "GSpd +2%", "Crit +1%", "ATK+1 HP+2", "T1 Caps +1", 
        "Prestige +1%", "ATK+3 HP+3"],
    2: ["HP +3", "E.ASpd -0.02", "E.ATK -1", 
        "E.Crit -1%", "ATK+1 ASpd+0.01", "T2 Caps +1", "Prestige +2%"],
    3: ["ATK +2", "ASpd +0.02", "Crit +1%", "GSpd +3%",
        "ATK+3 HP+3", "T3 Caps +1", "5x Drop +3%", "HP+5 ASpd+0.03"],
    4: ["Block +1%", "HP +5", "Crit Dmg +0.10", 
        "ASpd+0.02 MSpd+0.02", "HP+4 ATK+4", "T4 Caps +1", 
        "Cap of Caps +1", "HP+10 ASpd+0.05"]
}

# Prestige unlock requirements for each upgrade
# Value = minimum prestige needed to unlock
PRESTIGE_UNLOCKED = {
    1: [0, 0, 0, 0, 1, 2, 2, 4, 8, 10],
    2: [0, 0, 0, 3, 4, 5, 10],
    3: [1, 1, 2, 3, 4, 6, 8, 10],
    4: [1, 3, 4, 5, 6, 6, 7, 10]
}

# Maximum base levels for each upgrade (before cap upgrades)
MAX_LEVELS = {
    1: [50, 50, 25, 25, 25, 25, 25, 10, 5, 40],
    2: [25, 15, 10, 15, 25, 10, 15],
    3: [20, 20, 20, 20, 10, 10, 10, 40],
    4: [15, 15, 15, 15, 15, 10, 10, 40]
}

# Which upgrade index is the "cap upgrade" for each tier (1-indexed in original, 0-indexed here)
# Cap upgrades increase max level of other upgrades in the same tier
CAP_UPGRADES = {1: 8, 2: 6, 3: 6, 4: 6}

# Base costs for each upgrade (Tier X upgrades cost Material X)
# Cost scales as: base_cost * 1.25^level
COSTS = {
    1: [5, 6, 8, 10, 12, 20, 75, 2500, 25000, 5000],
    2: [5, 8, 12, 20, 40, 500, 650],
    3: [5, 8, 12, 18, 30, 250, 300, 125],
    4: [10, 12, 15, 20, 50, 250, 500, 150]
}

# Prestige wave requirements (estimated: wave = (prestige + 1) * 5)
def get_prestige_wave_requirement(prestige: int) -> int:
    """Get the wave required to unlock a prestige level"""
    return (prestige + 1) * 5


# GUI Colors
TIER_COLORS = {
    1: "#E3F2FD",  # Light Blue
    2: "#E8F5E9",  # Light Green
    3: "#FFF3E0",  # Light Orange
    4: "#FCE4EC"   # Light Pink
}

TIER_MAT_NAMES = {
    1: "Coins",
    2: "Currency 2", 
    3: "Currency 3",
    4: "Currency 4"
}

# Icon paths (relative to sprites folder)
CURRENCY_ICONS = {
    1: "event/currency_1.png",
    2: "event/currency_2.png",
    3: "event/currency_3.png",
    4: "event/currency_4.png"
}

GEM_UPGRADE_ICONS = {
    0: "event/gem_upgrade_0.png",  # +10% Dmg
    1: "event/gem_upgrade_1.png",  # +10% Max HP
    2: "event/gem_upgrade_2.png",  # +125% Event Game Spd
    3: "event/gem_upgrade_3.png"   # 2x Event Currencies
}

EVENT_BUTTON_ICON = "event/event_button.png"

# Upgrade stat effects for simulation (how each upgrade affects stats)
# Format: (stat_name, value_per_level)
# Negative values for enemy debuffs
UPGRADE_EFFECTS = {
    1: [
        ("atk", 1),           # +1 Attack Damage
        ("health", 2),        # +2 Maximum Health
        ("atk_speed", 0.02),  # +0.02 Attack Speed
        ("walk_speed", 0.03), # +0.03 Move Speed
        ("game_speed", 0.02), # +2% Event Game Speed (matches Lua original: 0.02*j)
        ("crit", 1, "crit_dmg", 0.10),  # +1% Crit, +0.10 Crit Dmg
        ("atk", 1, "health", 2),        # +1 ATK, +2 HP
        ("cap", 1),           # Cap upgrade (special)
        ("prestige_bonus", 0.01),  # +1% Prestige Bonus
        ("atk", 3, "health", 3),   # +3 ATK, +3 HP
    ],
    2: [
        ("health", 3),           # +3 Maximum Health
        ("e_atk_speed", -0.02),  # -0.02 Enemy Attack Speed
        ("e_atk", -1),           # -1 Enemy Attack Damage
        ("e_crit", -1, "e_crit_dmg", -0.10),  # -1% E.Crit, -0.10 E.Crit Dmg
        ("atk", 1, "atk_speed", 0.01),  # +1 ATK, +0.01 Atk Spd
        ("cap", 1),              # Cap upgrade
        ("prestige_bonus", 0.02),  # +2% Prestige Bonus
    ],
    3: [
        ("atk", 2),           # +2 Attack Damage
        ("atk_speed", 0.02),  # +0.02 Attack Speed
        ("crit", 1),          # +1% Crit Chance
        ("game_speed", 0.03), # +3% Event Game Speed (matches Lua original: 0.03*j)
        ("atk", 3, "health", 3),  # +3 ATK, +3 HP
        ("cap", 1),           # Cap upgrade
        ("x5_money", 3),      # +3% 5x Drop Chance
        ("health", 5, "atk_speed", 0.03),  # +5 HP, +0.03 Atk Spd
    ],
    4: [
        ("block_chance", 0.01),  # +1% Block Chance
        ("health", 5),           # +5 Maximum Health
        ("crit_dmg", 0.10, "e_crit_dmg", -0.10),  # +0.10 Crit Dmg, -0.10 E.Crit Dmg
        ("atk_speed", 0.02, "walk_speed", 0.02),  # +0.02 Atk Spd, +0.02 Move Spd
        ("health", 4, "atk", 4),  # +4 HP, +4 ATK
        ("cap", 1),              # Cap upgrade
        ("cap_of_caps", 1),      # Cap of caps (special)
        ("health", 10, "atk_speed", 0.05),  # +10 HP, +0.05 Atk Spd
    ]
}

# Enemy base stats
ENEMY_BASE_STATS = {
    'health': 4,           # Base HP at wave 0
    'health_scaling': 7,   # +7 HP per wave (so wave 1 = 11 HP)
    'atk': 2.5,            # Base attack damage
    'atk_scaling': 0.6,    # +0.6 ATK per wave
    'atk_speed': 0.8,      # Base attack speed
    'atk_speed_scaling': 0.02,  # +0.02 per wave
    'crit': 0,             # Base crit chance (0%)
    'crit_scaling': 1,     # +1% crit per wave
    'crit_dmg': 1.0,       # Base crit damage (1x)
    'crit_dmg_scaling': 0.05,  # +0.05 per wave
}

# Player base stats
PLAYER_BASE_STATS = {
    'health': 100,
    'atk': 10,
    'atk_speed': 1.0,
    'walk_speed': 1.0,
    'crit': 0,
    'crit_dmg': 2.0,
    'block_chance': 0.0,
    'game_speed': 1.0,
    'x2_money': 0,
    'x5_money': 0,
}

# Prestige bonus: +10% ATK and HP per prestige tier (base, can be increased)
PRESTIGE_BONUS_BASE = 0.10

# Recommended prestige strategy from wiki
PRESTIGE_STRATEGY = [
    (0, 20, "First prestige: Push to Wave 20 (Prestige 3)"),
    (3, 30, "Second prestige: Push to Wave 30 (Prestige 5)"),
    (5, 55, "Third prestige: Push to Wave 55 (Prestige 10)"),
    (10, 100, "Fourth prestige: Push to Wave 100 (Prestige 19)"),
    (19, 200, "Fifth prestige: Push to Wave 200 if possible"),
]

# Wave rewards (excluding gifts after wave 100)
WAVE_REWARDS = {
    2: "20 Gems",
    4: "6 Item Chests",
    6: "2 Gifts",
    8: "30 Gems",
    10: "10 Charge Magnets",
    12: "5 Relic Chests",
    14: "15 Item Chests",
    16: "40 Gems",
    18: "3 Blue Cows",
    20: "5 Gifts",
    22: "50 Gems",
    24: "20 Item Chests",
    26: "10 Skill Shards",
    28: "5 Primal Meat",
    30: "8 Relic Chests",
    32: "65 Gems",
    34: "12 Skill Shards",
    36: "10 Relic Chests",
    38: "80 Gems",
    40: "Seasonal Skin",
    42: "5 Blue Cows",
    44: "30 Item Chests",
    46: "14 Skill Shards",
    48: "100 Gems",
    50: "1 Mythic Chest",
    55: "12 Relic Chests",
    60: "16 Skill Shards",
    65: "120 Gems",
    70: "8 Gifts",
    75: "150 Gems",
    80: "Seasonal Bag Skin",
    85: "30 Relic Chests",
    90: "20 Skill Shards",
    95: "10 Gifts",
    100: "1 Mythic Chest",
}
