"""
Beispiel-Skript für ObeliskGemEV Calculator
"""

import sys
from pathlib import Path

# Füge das Modul-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from freebie_ev_calculator import FreebieEVCalculator

if __name__ == "__main__":
    # Standard-Parameter verwenden
    calculator = FreebieEVCalculator()
    
    # Detaillierten Report ausgeben
    calculator.print_detailed_report()
    
    # Oder nur die Werte abrufen
    ev = calculator.calculate_total_ev_per_hour()
    print(f"\nGesamt-EV: {ev['total']:.1f} Gems-Äquivalent pro Stunde")
