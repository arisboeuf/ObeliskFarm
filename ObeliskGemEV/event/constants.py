"""
Constants and game data for Event Simulator.
All upgrade data, costs, prestige requirements etc.
"""

# Upgrade names for display
UPGRADE_NAMES = {
    1: ["+1 Atk Dmg", "+2 Max Hp", "+0.02 Atk Spd", "+0.03 Move Spd", 
        "+2% Event Game Spd", "+1% Crit Chance, +0.10 Crit Dmg", 
        "+1 Atk Dmg +2 Max Hp", "+1 Tier 1 Upgrade Caps", 
        "+1% Prestige Bonus", "+3 Atk Dmg, +3 Max Hp"],
    2: ["+3 Max Hp", "-0.02 Enemy Atk Spd", "-1 Enemy Atk Dmg", 
        "-1% E.Crt rate, -0.1 E.Crt Dmg", "+1 Atk Dmg, +0.01 Atk Spd", 
        "+1 Tier 2 Upgrade Caps", "+2% Prestige Bonus"],
    3: ["+2 Atk Dmg", "+0.02 Atk Spd", "+1% Crit Chance", "+3% Event Game Spd",
        "+3 Atk Dmg, +3 Max Hp", "+1 Tier 3 Upgrade Caps", 
        "+3% 5x Drop Chance", "+5 Max Hp, +0.03 Atk Spd"],
    4: ["+1% Block Chance", "+5 Max Hp", "+0.10 Crit Dmg, -0.10 Enemy Crit Dmg",
        "+0.02 Atk Spd, +0.02 Move Spd", "+4 Max Hp, +4 Atk Dmg", 
        "+1 Tier 4 Upgrade Caps", "+1 Cap Of Cap Upgrades", 
        "+10 Max Hp, +0.05 Atk Spd"]
}

GEM_UPGRADE_NAMES = ["+10% dmg", "+10% max hp", "+100% Event Game Spd", "2x Event Currencies"]

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
    2: "Mat 2", 
    3: "Mat 3",
    4: "Mat 4"
}
