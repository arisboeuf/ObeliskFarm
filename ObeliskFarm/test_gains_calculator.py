"""
Test-Skript für den Offline Gains Calculator
Testet die Extraktion von Daten aus einem Screenshot.
"""

import os
import sys
from pathlib import Path
from src.offline_gains_calculator import OfflineGainsCalculator

# Setze UTF-8 Encoding für Windows-Konsolen
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

if __name__ == "__main__":
    # Pfad zum Screenshot
    screenshot_path = r"C:\Users\Aris Perrou (PAIA)\OneDrive - PAIA Biotech GmbH\python\Git supervised Skripte\Obelisk\ObeliskFarm\screenshots\photo_2026-01-01_19-42-36.jpg"
    
    print("="*70)
    print("OFFLINE GAINS CALCULATOR TEST")
    print("="*70)
    print(f"Screenshot: {Path(screenshot_path).name}\n")
    
    # Erstelle Calculator mit Debug-Ausgabe
    calculator = OfflineGainsCalculator(debug=True)
    
    # Berechne Gains
    result = calculator.calculate_gains_per_hour(screenshot_path)
    
    print("\n" + "="*70)
    print("ERGEBNIS")
    print("="*70)
    
    if result['success']:
        print(f"\n[OK] Erfolgreich verarbeitet!")
        print(f"\nOffline-Zeit: {result['offline_time_hours']:.4f} Stunden" if result['offline_time_hours'] else "\nOffline-Zeit: NICHT gefunden")
        
        print("\n--- Extrahierte Daten (RAW) ---")
        raw = result['raw_data']
        print(f"Stats: {raw.get('stats', {})}")
        print(f"Resources: {raw.get('resources', {})}")
        
        if result['gains_per_hour']:
            print("\n--- Gains pro Stunde ---")
            for key, value in result['gains_per_hour'].items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")
        else:
            print("\n[WARNUNG] Keine Gains berechnet (keine Offline-Zeit gefunden?)")
    else:
        print(f"\n[FEHLER] {result.get('error', 'Unbekannter Fehler')}")
    
    print("\n" + "="*70)

