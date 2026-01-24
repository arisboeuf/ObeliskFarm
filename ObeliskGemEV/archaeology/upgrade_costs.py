"""
Fragment Upgrade Costs for Archaeology

Data from: https://shminer.miraheze.org/wiki/Archaeology
Each upgrade has costs per level that scale with a 1.2x multiplier.
"""

from typing import Optional

# Fragment upgrade costs indexed by upgrade_key
# Format: upgrade_key -> list of costs per level (index 0 = level 1 cost)
FRAGMENT_UPGRADE_COSTS = {
    # Common Fragment Upgrades
    'flat_damage_c1': [  # Flat Damage +1
        0.50, 0.60, 0.72, 0.86, 1.04, 1.24, 1.49, 1.79, 2.15, 2.58,  # 1-10
        3.10, 3.72, 4.46, 5.35, 6.42, 7.70, 9.24, 11.09, 13.31, 15.97,  # 11-20
        19.17, 23.00, 27.60, 33.12, 39.75,  # 21-25
    ],
    'armor_pen_c1': [  # Armor Penetration +1
        0.75, 0.90, 1.08, 1.30, 1.56, 1.87, 2.24, 2.69, 3.22, 3.87,  # 1-10
        4.64, 5.57, 6.69, 8.02, 9.63, 11.56, 13.87, 16.64, 19.97, 23.96,  # 11-20
        28.75, 34.50, 41.40, 49.69, 59.62,  # 21-25
    ],
    'arch_xp_c1': [  # Archaeology Exp Gain +2%
        1.00, 1.20, 1.44, 1.73, 2.07, 2.49, 2.99, 3.58, 4.30, 5.16,  # 1-10
        6.19, 7.43, 8.92, 10.70, 12.84, 15.41, 18.49, 22.19, 26.62, 31.95,  # 11-20
        38.34, 46.01, 55.21, 66.25, 79.50,  # 21-25
    ],
    'crit_c1': [  # Crit Chance +0.25% / Crit Damage +1%
        2.00, 2.40, 2.88, 3.46, 4.15, 4.98, 5.97, 7.17, 8.60, 10.32,  # 1-10
        12.38, 14.86, 17.83, 21.40, 25.68, 30.81, 36.98, 44.37, 53.25, 63.90,  # 11-20
        76.68, 92.01, 110.00, 132.00, 158.00,  # 21-25
    ],
    'str_skill_buff': [  # Strength Skill Buff
        100.00, 120.00, 144.00, 172.00, 207.00,  # 1-5
    ],
    'polychrome_bonus': [  # Polychrome Archaeology Card Bonus +15%
        10000.00,  # 1
    ],
    
    # Rare Fragment Upgrades
    'stamina_r1': [  # Max Stamina +2 / Stamina Mod Chance +0.05%
        2.00, 2.40, 2.88, 3.46, 4.15, 4.98, 5.97, 7.17, 8.60, 10.32,  # 1-10
        12.38, 14.86, 17.83, 21.40, 25.68, 30.81, 36.98, 44.37, 53.25, 63.90,  # 11-20
    ],
    'flat_damage_r1': [  # Flat Damage +2
        3.00, 3.60, 4.32, 5.18, 6.22, 7.46, 8.96, 10.75, 12.90, 15.48,  # 1-10
        18.58, 22.29, 26.75, 32.10, 38.52, 46.22, 55.47, 66.56, 79.87, 95.84,  # 11-20
    ],
    'loot_mod_mult': [  # Loot Mod Gain +0.30x
        4.50, 5.40, 6.48, 7.78, 9.33, 11.20, 13.44, 16.12, 19.35, 23.22,  # 1-10
    ],
    'enrage_buff': [  # Enrage Damage/Crit Damage +2% / Enrage Cooldown -1s
        6.00, 7.20, 8.64, 10.37, 12.44, 14.93, 17.92, 21.50, 25.80, 30.96,  # 1-10
        37.15, 44.58, 53.50, 64.20, 77.04,  # 11-15
    ],
    'agi_skill_buff': [  # Agility Skill Buff
        50.00, 60.00, 72.00, 86.40, 103.00,  # 1-5
    ],
    'per_skill_buff': [  # Perception Skill Buff
        150.00, 180.00, 216.00, 259.00, 311.00,  # 1-5
    ],
    'fragment_gain_1x': [  # Fragment Gain 1.25x
        9000.00,  # 1
    ],
    
    # Epic Fragment Upgrades
    'flat_damage_e1': [  # Flat Damage +2 / Super Crit Chance +0.35%
        3.50, 4.20, 5.04, 6.05, 7.26, 8.71, 10.45, 12.54, 15.05, 18.06,  # 1-10
        21.67, 26.01, 31.21, 37.45, 44.94, 53.92, 64.71, 77.65, 93.18, 111.00,  # 11-20
        134.00, 161.00, 193.00, 231.00, 278.00,  # 21-25
    ],
    'arch_xp_frag_e1': [  # Archaeology Exp Gain +3% / Fragment Gain +2%
        5.00, 6.00, 7.20, 8.64, 10.37, 12.44, 14.93, 17.92, 21.50, 25.80,  # 1-10
        30.96, 37.15, 44.58, 53.50, 64.20, 77.04, 92.44, 110.00, 133.00, 159.00,  # 11-20
    ],
    'flurry_buff': [  # Flurry Stamina Gain +1 / Flurry Cooldown -1s
        7.50, 9.00, 10.80, 12.96, 15.55, 18.66, 22.39, 26.87, 32.25, 38.70,  # 1-10
    ],
    'stamina_e1': [  # Max Stamina +4 / Stamina Mod Gain +1
        25.00, 30.00, 36.00, 43.20, 51.84,  # 1-5
    ],
    'int_skill_buff': [  # Intellect Skill Buff
        125.00, 150.00, 180.00, 216.00, 259.00,  # 1-5
    ],
    'stamina_mod_gain_1': [  # Stamina Mod Gain +2
        8000.00,  # 1
    ],
    
    # Legendary Fragment Upgrades
    'arch_xp_stam_l1': [  # Archaeology Exp Gain +5% / Maximum Stamina +1%
        7.00, 8.40, 10.08, 12.10, 14.52, 17.42, 20.90, 25.08, 30.10, 36.12,  # 1-10
        43.34, 52.01, 62.41, 74.90, 89.87,  # 11-15
    ],
    'armor_pen_cd_l1': [  # Armor Penetration +2% / Ability Cooldown -1s
        9.00, 10.80, 12.96, 15.55, 18.66, 22.39, 26.87, 32.25, 38.70, 46.44,  # 1-10
    ],
    'crit_dmg_l1': [  # Crit Damage +2% / Super Crit Damage +2%
        12.00, 14.40, 17.28, 20.74, 24.88, 29.86, 35.83, 42.00, 51.60, 61.92,  # 1-10
        74.30, 89.16, 106.00, 128.00, 154.00, 184.00, 221.00, 266.00, 319.00, 383.00,  # 11-20
    ],
    'quake_buff': [  # Quake Attacks +1 / Cooldown -2s
        15.00, 18.00, 21.60, 25.92, 31.10, 37.32, 44.79, 53.75, 64.50, 77.40,  # 1-10
    ],
    'all_mod_chance': [  # All Mod Chances +1.50%
        7000.00,  # 1
    ],
    
    # Mythic Fragment Upgrades
    'damage_apen_m1': [  # Damage +2% / Armor Penetration +3
        6.00, 7.20, 8.64, 10.37, 12.44, 14.93, 17.92, 21.50, 25.80, 30.96,  # 1-10
        37.15, 44.58, 53.50, 64.20, 77.04, 92.44, 110.00, 133.00, 159.00, 191.00,  # 11-20
    ],
    'crit_chance_m1': [  # Super Crit Chance +0.35% / Ultra Crit Chance +1%
        10.00, 12.00, 14.40, 17.28, 20.74, 24.88, 29.86, 35.83, 42.00, 51.60,  # 1-10
        61.92, 74.30, 89.16, 106.00, 128.00, 154.00, 184.00, 221.00, 266.00, 319.00,  # 11-20
    ],
    'exp_mod_m1': [  # Exp Mod Gain +0.10x / Exp Mod Chance +0.10%
        15.00, 18.00, 21.60, 25.92, 31.10, 37.32, 44.79, 53.75, 64.50, 77.40,  # 1-10
        92.88, 111.00, 133.00, 160.00, 192.00, 231.00, 277.00, 332.00, 399.00, 479.00,  # 11-20
    ],
    'ability_stam_m1': [  # Ability Instacharge +0.30% / Max Stamina +4
        20.00, 24.00, 28.80, 34.56, 41.47, 49.77, 59.72, 71.66, 85.00, 103.00,  # 1-10
        123.00, 148.00, 178.00, 213.00, 256.00, 308.00, 369.00, 443.00, 532.00, 638.00,  # 11-20
    ],
    'exp_stat_cap_m1': [  # Exp Gain 2.00x / All Stat Point Caps +5
        5000.00,  # 1
    ],
}


def get_upgrade_cost(upgrade_key: str, level: int) -> Optional[float]:
    """
    Get the cost to upgrade from current level to level+1.
    
    Args:
        upgrade_key: The upgrade identifier (e.g., 'flat_damage_c1')
        level: Current level (0-based, so level 0 means buying level 1)
    
    Returns:
        Cost in fragments, or None if at max level or invalid upgrade
    """
    if upgrade_key not in FRAGMENT_UPGRADE_COSTS:
        return None
    
    costs = FRAGMENT_UPGRADE_COSTS[upgrade_key]
    if level >= len(costs):
        return None
    
    return costs[level]


def get_total_cost(upgrade_key: str, level: int) -> float:
    """
    Get the total cost spent to reach the current level.
    
    Args:
        upgrade_key: The upgrade identifier
        level: Current level (1-based)
    
    Returns:
        Total fragments spent to reach this level
    """
    if upgrade_key not in FRAGMENT_UPGRADE_COSTS:
        return 0
    
    costs = FRAGMENT_UPGRADE_COSTS[upgrade_key]
    if level <= 0:
        return 0
    
    return sum(costs[:level])


def get_max_level(upgrade_key: str) -> int:
    """Get the maximum level for an upgrade."""
    if upgrade_key not in FRAGMENT_UPGRADE_COSTS:
        return 0
    return len(FRAGMENT_UPGRADE_COSTS[upgrade_key])
