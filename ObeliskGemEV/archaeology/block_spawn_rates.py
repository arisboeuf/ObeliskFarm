"""
Block Spawn Rates by Stage for Archaeology

This module provides block spawn chance data based on the current floor/stage.
These spawn chances are overridden by boss floors.

Block types:
- Dirt: Basic block, no special properties
- Common: Common block with low armor
- Rare: Rare block (unlocks at stage 3)
- Epic: Epic block (unlocks at stage 6)
- Legendary: Legendary block (unlocks at stage 12)
- Mythic: Mythic block (unlocks at stage 20)

Boss Floors:
Special floors where only one block type spawns (100% chance).
These override the normal spawn rates.
"""

from typing import Dict, Tuple, Optional

# Boss floors with 100% spawn rate for a single block type
# Format: floor -> block_type
BOSS_FLOORS: Dict[int, str] = {
    11: 'dirt',
    17: 'common',
    23: 'dirt',
    25: 'rare',
    29: 'epic',
    31: 'legendary',
    35: 'rare',
    41: 'epic',
    44: 'legendary',
    99: 'mythic',
}

# Block spawn rates by stage range
# Format: (min_stage, max_stage): {'dirt': %, 'common': %, 'rare': %, 'epic': %, 'legendary': %, 'mythic': %}
# Note: Percentages represent spawn weights, not absolute probabilities
# The sum of all non-zero values per row represents the total spawn pool

SPAWN_RATES_BY_STAGE: Dict[Tuple[int, int], Dict[str, float]] = {
    (1, 2): {
        'dirt': 28.57,
        'common': 14.29,
        'rare': 0.00,
        'epic': 0.00,
        'legendary': 0.00,
        'mythic': 0.00,
    },
    (3, 4): {
        'dirt': 25.40,
        'common': 12.70,
        'rare': 11.11,
        'epic': 0.00,
        'legendary': 0.00,
        'mythic': 0.00,
    },
    (5, 5): {
        'dirt': 25.52,
        'common': 10.94,
        'rare': 12.50,
        'epic': 0.00,
        'legendary': 0.00,
        'mythic': 0.00,
    },
    (6, 9): {
        'dirt': 22.97,
        'common': 9.84,
        'rare': 11.25,
        'epic': 10.00,
        'legendary': 0.00,
        'mythic': 0.00,
    },
    (10, 11): {
        'dirt': 23.41,
        'common': 8.78,
        'rare': 9.88,
        'epic': 11.11,
        'legendary': 0.00,
        'mythic': 0.00,
    },
    (12, 14): {
        'dirt': 21.74,
        'common': 8.15,
        'rare': 9.17,
        'epic': 10.32,
        'legendary': 7.14,
        'mythic': 0.00,
    },
    (15, 19): {
        'dirt': 21.27,
        'common': 7.98,
        'rare': 8.97,
        'epic': 11.54,
        'legendary': 7.69,
        'mythic': 0.00,
    },
    (20, 24): {
        'dirt': 19.50,
        'common': 7.31,
        'rare': 8.23,
        'epic': 12.34,
        'legendary': 8.64,
        'mythic': 5.00,
    },
    (25, 29): {
        'dirt': 18.47,
        'common': 7.92,
        'rare': 9.05,
        'epic': 12.06,
        'legendary': 10.56,
        'mythic': 5.00,
    },
    (30, 49): {
        'dirt': 18.10,
        'common': 9.05,
        'rare': 7.92,
        'epic': 11.88,
        'legendary': 11.88,
        'mythic': 5.00,
    },
    (50, 75): {
        'dirt': 16.87,
        'common': 8.43,
        'rare': 9.84,
        'epic': 13.77,
        'legendary': 11.81,
        'mythic': 5.56,
    },
    (76, float('inf')): {  # 75+ (stages above 75)
        'dirt': 16.81,
        'common': 10.08,
        'rare': 10.08,
        'epic': 11.76,
        'legendary': 11.76,
        'mythic': 5.88,
    },
}

# Block types in order of rarity
BLOCK_TYPES = ['dirt', 'common', 'rare', 'epic', 'legendary', 'mythic']

# Stage ranges for display purposes
STAGE_RANGES = [
    "1-2", "3-4", "5", "6-9", "10-11", "12-14", 
    "15-19", "20-24", "25-29", "30-49", "50-75", "75+"
]


def is_boss_floor(floor: int) -> bool:
    """Check if a floor is a boss floor."""
    return floor in BOSS_FLOORS


def get_boss_floor_block(floor: int) -> Optional[str]:
    """Get the block type for a boss floor, or None if not a boss floor."""
    return BOSS_FLOORS.get(floor)


def get_spawn_rates_for_stage(stage: int, ignore_boss: bool = False) -> Dict[str, float]:
    """
    Get block spawn rates for a specific stage.
    
    Args:
        stage: The current floor/stage number (1-based)
        ignore_boss: If True, return normal rates even for boss floors
    
    Returns:
        Dictionary mapping block types to their spawn percentages.
        Values are raw percentages (e.g., 28.57 means 28.57%).
        For boss floors, returns 100% for the boss block type.
    
    Example:
        >>> rates = get_spawn_rates_for_stage(1)
        >>> rates['dirt']
        28.57
        >>> rates = get_spawn_rates_for_stage(11)  # Boss floor
        >>> rates['dirt']
        100.0
    """
    # Check for boss floor
    if not ignore_boss and stage in BOSS_FLOORS:
        boss_block = BOSS_FLOORS[stage]
        return {
            'dirt': 100.0 if boss_block == 'dirt' else 0.0,
            'common': 100.0 if boss_block == 'common' else 0.0,
            'rare': 100.0 if boss_block == 'rare' else 0.0,
            'epic': 100.0 if boss_block == 'epic' else 0.0,
            'legendary': 100.0 if boss_block == 'legendary' else 0.0,
            'mythic': 100.0 if boss_block == 'mythic' else 0.0,
        }
    
    for (min_stage, max_stage), rates in SPAWN_RATES_BY_STAGE.items():
        if min_stage <= stage <= max_stage:
            return rates.copy()
    
    # Fallback to highest tier if somehow beyond defined ranges
    return SPAWN_RATES_BY_STAGE[(76, float('inf'))].copy()


def get_normalized_spawn_rates(stage: int, ignore_boss: bool = False) -> Dict[str, float]:
    """
    Get normalized spawn rates that sum to 1.0 (for use as probabilities).
    
    Args:
        stage: The current floor/stage number (1-based)
        ignore_boss: If True, return normal rates even for boss floors
    
    Returns:
        Dictionary mapping block types to their normalized spawn probabilities.
        Only includes block types with non-zero spawn rates.
        For boss floors, returns 1.0 for the boss block type only.
    
    Example:
        >>> rates = get_normalized_spawn_rates(1)
        >>> sum(rates.values())
        1.0
        >>> rates = get_normalized_spawn_rates(11)  # Boss floor
        >>> rates
        {'dirt': 1.0}
    """
    raw_rates = get_spawn_rates_for_stage(stage, ignore_boss)
    
    # Filter out zero values and calculate total
    active_rates = {k: v for k, v in raw_rates.items() if v > 0}
    total = sum(active_rates.values())
    
    if total == 0:
        return {'dirt': 1.0}  # Fallback
    
    return {k: v / total for k, v in active_rates.items()}


def get_block_mix_for_stage(stage: int) -> Dict[str, float]:
    """
    Get the block mix for a specific stage as spawn weights.
    This is the format expected by the Archaeology Simulator.
    
    Args:
        stage: The current floor/stage number (1-based)
    
    Returns:
        Dictionary mapping block types to their spawn weights.
        Only includes block types with non-zero spawn rates.
    
    Example:
        >>> mix = get_block_mix_for_stage(5)
        >>> 'dirt' in mix
        True
        >>> 'epic' in mix  # Epic not available until stage 6
        False
    """
    raw_rates = get_spawn_rates_for_stage(stage)
    
    # Return only non-zero rates as weights
    return {k: v for k, v in raw_rates.items() if v > 0}


def get_available_blocks_at_stage(stage: int) -> list:
    """
    Get list of block types available at a given stage.
    
    Args:
        stage: The current floor/stage number (1-based)
    
    Returns:
        List of block type names that can spawn at this stage.
    
    Example:
        >>> get_available_blocks_at_stage(1)
        ['dirt', 'common']
        >>> get_available_blocks_at_stage(20)
        ['dirt', 'common', 'rare', 'epic', 'legendary', 'mythic']
    """
    rates = get_spawn_rates_for_stage(stage)
    return [block for block in BLOCK_TYPES if rates.get(block, 0) > 0]


def get_stage_range_label(stage: int) -> str:
    """
    Get the stage range label for display purposes.
    
    Args:
        stage: The current floor/stage number (1-based)
    
    Returns:
        String label for the stage range (e.g., "1-2", "75+")
    """
    ranges = [
        (1, 2, "1-2"),
        (3, 4, "3-4"),
        (5, 5, "5"),
        (6, 9, "6-9"),
        (10, 11, "10-11"),
        (12, 14, "12-14"),
        (15, 19, "15-19"),
        (20, 24, "20-24"),
        (25, 29, "25-29"),
        (30, 49, "30-49"),
        (50, 75, "50-75"),
        (76, float('inf'), "75+"),
    ]
    
    for min_s, max_s, label in ranges:
        if min_s <= stage <= max_s:
            return label
    
    return "75+"


def get_all_boss_floors() -> Dict[int, str]:
    """Get all boss floors and their block types."""
    return BOSS_FLOORS.copy()


def print_spawn_table():
    """Print a formatted spawn rate table (for debugging/documentation)."""
    print("Block Spawn Chance by Stage")
    print("=" * 80)
    header = f"{'Stages':<10} {'Dirt':>8} {'Common':>8} {'Rare':>8} {'Epic':>8} {'Legend':>8} {'Mythic':>8}"
    print(header)
    print("-" * 80)
    
    for (min_stage, max_stage), rates in SPAWN_RATES_BY_STAGE.items():
        if max_stage == float('inf'):
            stage_str = f"{min_stage-1}+"
        elif min_stage == max_stage:
            stage_str = str(min_stage)
        else:
            stage_str = f"{min_stage}-{max_stage}"
        
        row = f"{stage_str:<10}"
        for block_type in BLOCK_TYPES:
            value = rates[block_type]
            row += f" {value:>7.2f}%"
        print(row)
    
    print("\nBoss Floors (100% single block type):")
    print("-" * 40)
    for floor, block_type in sorted(BOSS_FLOORS.items()):
        print(f"  Floor {floor:>3}: {block_type.capitalize()}")


if __name__ == "__main__":
    # Test the module
    print_spawn_table()
    print()
    
    # Test individual lookups
    test_stages = [1, 5, 10, 20, 50, 100]
    for stage in test_stages:
        print(f"\nStage {stage} ({get_stage_range_label(stage)}):")
        print(f"  Available blocks: {get_available_blocks_at_stage(stage)}")
        print(f"  Normalized rates: {get_normalized_spawn_rates(stage)}")
