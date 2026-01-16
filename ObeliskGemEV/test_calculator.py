"""
Test-Skript für Freebie EV Calculator
"""

import sys
from pathlib import Path

# Füge das Modul-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from freebie_ev_calculator import FreebieEVCalculator, GameParameters

def test_standard_parameters():
    """Test mit Standard-Parametern"""
    print("Test 1: Standard-Parameter")
    print("-" * 70)
    calculator = FreebieEVCalculator()
    ev = calculator.calculate_total_ev_per_hour()
    
    # Erwartete Werte aus README (ca.)
    expected_total = 148.0
    tolerance = 2.0
    
    print(f"Berechneter Total-EV: {ev['total']:.1f}")
    print(f"Erwarteter Total-EV: {expected_total:.1f}")
    print(f"Abweichung: {abs(ev['total'] - expected_total):.1f}")
    
    assert abs(ev['total'] - expected_total) < tolerance, \
        f"Total-EV weicht zu stark ab: {ev['total']:.1f} vs {expected_total:.1f}"
    
    print("✓ Test bestanden!")
    print()

def test_custom_parameters():
    """Test mit benutzerdefinierten Parametern"""
    print("Test 2: Benutzerdefinierte Parameter")
    print("-" * 70)
    
    params = GameParameters(
        freebie_gems_base=10.0,  # Höhere Basis-Gems
        jackpot_chance=0.1,  # 10% Jackpot-Chance
    )
    
    calculator = FreebieEVCalculator(params)
    ev = calculator.calculate_total_ev_per_hour()
    
    print(f"Total-EV mit erhöhten Parametern: {ev['total']:.1f}")
    print("✓ Test bestanden!")
    print()

def test_multipliers():
    """Test der Multiplikator-Berechnungen"""
    print("Test 3: Multiplikatoren")
    print("-" * 70)
    
    calculator = FreebieEVCalculator()
    
    expected_rolls = calculator.calculate_expected_rolls_per_claim()
    refresh_mult = calculator.calculate_refresh_multiplier()
    total_mult = calculator.calculate_total_multiplier()
    
    print(f"Erwartete Rolls pro Claim: {expected_rolls:.4f} (erwartet: ~1.2)")
    print(f"Refresh-Multiplikator: {refresh_mult:.4f} (erwartet: ~1.0526)")
    print(f"Gesamt-Multiplikator: {total_mult:.4f} (erwartet: ~1.2632)")
    
    assert abs(expected_rolls - 1.2) < 0.01
    assert abs(refresh_mult - 1.0526) < 0.01
    assert abs(total_mult - 1.2632) < 0.01
    
    print("✓ Test bestanden!")
    print()

if __name__ == "__main__":
    print("=" * 70)
    print("OBELISKGEMEV - TESTS")
    print("=" * 70)
    print()
    
    test_multipliers()
    test_standard_parameters()
    test_custom_parameters()
    
    print("=" * 70)
    print("ALLE TESTS ERFOLGREICH!")
    print("=" * 70)
