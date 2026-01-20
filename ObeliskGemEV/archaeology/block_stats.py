"""
Block Stats by Tier for Archaeology

This module provides block statistics (HP, XP, Armor, Fragments) organized by tier.
Each block type has 3 tiers that become available at different floor ranges.

Block types: Dirt, Common, Rare, Epic, Legendary, Mythic
Tiers: 1, 2, 3 (higher tiers have more HP/Armor but also more rewards)
"""

from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass


@dataclass
class BlockData:
    """Data for a single block type at a specific tier"""
    tier: int
    block_type: str
    health: int
    xp: float
    armor: int
    fragment: float
    floor_min: int
    floor_max: int  # Use float('inf') for "X+" ranges
    
    @property
    def display_floor_range(self) -> str:
        """Get display string for floor range"""
        if self.floor_max == float('inf'):
            return f"{self.floor_min}+"
        return f"{self.floor_min}-{self.floor_max}"


# All block data organized by (tier, block_type)
# Format: BlockData(tier, type, health, xp, armor, fragment, floor_min, floor_max)
BLOCK_DATA: List[BlockData] = [
    # Tier 1
    BlockData(1, 'dirt',      100,   0.05,   0,  0.00,  1, 11),
    BlockData(1, 'common',    250,   0.15,   5,  0.01,  1, 17),
    BlockData(1, 'rare',      550,   0.35,  12,  0.01,  3, 25),
    BlockData(1, 'epic',     1150,   1.00,  25,  0.01,  6, 29),
    BlockData(1, 'legendary', 1950,  3.50,  50,  0.01, 12, 31),
    BlockData(1, 'mythic',   3500,   7.50, 150,  0.01, 20, 34),
    
    # Tier 2
    BlockData(2, 'dirt',      300,   0.15,   0,  0.00, 12, 23),
    BlockData(2, 'common',    600,   0.45,   9,  0.02, 18, 28),
    BlockData(2, 'rare',     1650,   1.05,  21,  0.02, 26, 35),
    BlockData(2, 'epic',     3450,   3.00,  44,  0.02, 30, 41),
    BlockData(2, 'legendary', 5850, 10.50,  88,  0.02, 32, 44),
    BlockData(2, 'mythic',  10500,  22.50, 262,  0.02, 36, 49),
    
    # Tier 3
    BlockData(3, 'dirt',      900,   0.45,   0,  0.04, 24, float('inf')),
    BlockData(3, 'common',   2250,   1.35,  15,  0.04, 30, float('inf')),
    BlockData(3, 'rare',     4950,   3.15,  37,  0.04, 36, float('inf')),
    BlockData(3, 'epic',    10350,   9.00,  77,  0.04, 42, float('inf')),
    BlockData(3, 'legendary', 17500, 31.50, 153, 0.04, 45, float('inf')),
    BlockData(3, 'mythic',  31500,  67.50, 459,  0.04, 50, float('inf')),
]

# Block types in order of rarity
BLOCK_TYPES = ['dirt', 'common', 'rare', 'epic', 'legendary', 'mythic']

# Index for quick lookup: (tier, block_type) -> BlockData
_BLOCK_INDEX: Dict[Tuple[int, str], BlockData] = {
    (b.tier, b.block_type): b for b in BLOCK_DATA
}

# Index by block_type -> list of BlockData (all tiers)
_BLOCK_BY_TYPE: Dict[str, List[BlockData]] = {}
for block in BLOCK_DATA:
    if block.block_type not in _BLOCK_BY_TYPE:
        _BLOCK_BY_TYPE[block.block_type] = []
    _BLOCK_BY_TYPE[block.block_type].append(block)


def get_block_data(tier: int, block_type: str) -> Optional[BlockData]:
    """
    Get block data for a specific tier and type.
    
    Args:
        tier: Block tier (1, 2, or 3)
        block_type: Block type ('dirt', 'common', 'rare', 'epic', 'legendary', 'mythic')
    
    Returns:
        BlockData object or None if not found
    """
    return _BLOCK_INDEX.get((tier, block_type))


def get_block_at_floor(floor: int, block_type: str) -> Optional[BlockData]:
    """
    Get the appropriate block data for a given floor and block type.
    Returns the highest tier block that can spawn at this floor.
    
    Args:
        floor: Current floor number (1-based)
        block_type: Block type name
    
    Returns:
        BlockData for the appropriate tier, or None if block can't spawn at this floor
    """
    blocks = _BLOCK_BY_TYPE.get(block_type, [])
    
    # Find all tiers that can spawn at this floor
    valid_blocks = [b for b in blocks if b.floor_min <= floor <= b.floor_max]
    
    if not valid_blocks:
        return None
    
    # Return the highest tier among valid blocks
    return max(valid_blocks, key=lambda b: b.tier)


def get_available_blocks_at_floor(floor: int) -> List[BlockData]:
    """
    Get all block types/tiers that can spawn at a given floor.
    
    Args:
        floor: Current floor number (1-based)
    
    Returns:
        List of BlockData objects for all blocks that can spawn
    """
    return [b for b in BLOCK_DATA if b.floor_min <= floor <= b.floor_max]


def get_block_mix_for_floor(floor: int) -> Dict[str, BlockData]:
    """
    Get the block mix for a specific floor.
    Returns a dict mapping block_type to the BlockData that spawns at this floor.
    
    For floors where multiple tiers can spawn, returns the highest tier.
    
    Args:
        floor: Current floor number (1-based)
    
    Returns:
        Dict mapping block_type -> BlockData
    """
    result = {}
    for block_type in BLOCK_TYPES:
        block = get_block_at_floor(floor, block_type)
        if block:
            result[block_type] = block
    return result


def get_tier_transition_floors() -> List[int]:
    """
    Get the floors where tier transitions occur.
    These are important breakpoints for optimization.
    
    Returns:
        Sorted list of floor numbers where new tiers become available
    """
    floors = set()
    for block in BLOCK_DATA:
        floors.add(block.floor_min)
    return sorted(floors)


def print_block_table():
    """Print a formatted block stats table (for debugging/documentation)."""
    print("Block Stats by Tier")
    print("=" * 100)
    header = f"{'Tier':<6} {'Type':<12} {'Health':>8} {'XP':>8} {'Armor':>8} {'Fragment':>10} {'Floors':<10}"
    print(header)
    print("-" * 100)
    
    for block in BLOCK_DATA:
        floor_str = block.display_floor_range
        print(f"{block.tier:<6} {block.block_type:<12} {block.health:>8} {block.xp:>8.2f} "
              f"{block.armor:>8} {block.fragment:>10.2f} {floor_str:<10}")


def print_floor_analysis(floor: int):
    """Print analysis of what blocks spawn at a specific floor."""
    print(f"\nFloor {floor} Analysis:")
    print("-" * 50)
    
    blocks = get_available_blocks_at_floor(floor)
    if not blocks:
        print("  No blocks spawn at this floor!")
        return
    
    # Group by type
    by_type = {}
    for b in blocks:
        if b.block_type not in by_type:
            by_type[b.block_type] = []
        by_type[b.block_type].append(b)
    
    for block_type in BLOCK_TYPES:
        if block_type not in by_type:
            continue
        type_blocks = by_type[block_type]
        for b in type_blocks:
            print(f"  T{b.tier} {b.block_type.capitalize():<10}: HP={b.health:>5}, Armor={b.armor:>3}, "
                  f"XP={b.xp:.2f}, Frag={b.fragment:.2f}")


if __name__ == "__main__":
    print_block_table()
    
    print("\n" + "=" * 100)
    print("Tier Transition Floors:", get_tier_transition_floors())
    
    # Analyze some key floors
    for floor in [1, 5, 12, 20, 30, 50]:
        print_floor_analysis(floor)
