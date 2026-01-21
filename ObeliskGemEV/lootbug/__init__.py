"""
Lootbug Module

Analyzes whether specific gem purchases are worth it based on current EV/h.
Also provides loot tables for lootbug rewards.
"""

from .analyzer import LootbugWindow, FREE_BUFFS, GEM_BUFFS

__all__ = ['LootbugWindow', 'FREE_BUFFS', 'GEM_BUFFS']
