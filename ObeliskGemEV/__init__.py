"""
ObeliskFarm - Erwartungswert-Berechnung für Gems (Freebies)
"""

__version__ = "1.0.6"

# Data is based on this Obelisk level - update this when your save changes
OBELISK_LEVEL = 30

from .freebie_ev_calculator import FreebieEVCalculator

__all__ = ['FreebieEVCalculator']
