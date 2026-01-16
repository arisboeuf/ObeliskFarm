"""Test-Skript für einzelnes Bild mit vollständiger Ausgabe"""
import sys
import json
from src.offline_gains_calculator import OfflineGainsCalculator

sys.stdout.reconfigure(encoding='utf-8')

calc = OfflineGainsCalculator(debug=True)
result = calc.calculate_gains_per_hour('screenshots/photo_2026-01-01_16-46-14.jpg')

print('\n' + '='*70)
print('VOLLSTÄNDIGES ERGEBNIS')
print('='*70)
print(f'\nSuccess: {result["success"]}')
if not result['success']:
    print(f'Error: {result.get("error")}')
else:
    print(f'\nOffline-Zeit: {result.get("offline_time_hours")}')
    print(f'\nGains pro Stunde:')
    gains = result.get("gains_per_hour", {})
    if gains:
        for key, value in gains.items():
            print(f'   {key}: {value}')
    else:
        print('   (keine)')
    print(f'\nRaw Data:')
    raw = result.get("raw_data", {})
    print(f'   Offline Hours: {raw.get("offline_hours")}')
    print(f'   Stats: {raw.get("stats", {})}')
    print(f'   Resources: {raw.get("resources", {})}')
sys.stdout.flush()

