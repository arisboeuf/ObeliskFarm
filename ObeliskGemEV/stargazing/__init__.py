"""
Stargazing Module

Simple calculator for stars and super stars per hour based on in-game stats.
"""

from .calculator import StargazingCalculator, PlayerStats
from .gui import StargazingWindow

__all__ = ['StargazingCalculator', 'PlayerStats', 'StargazingWindow']
