"""Einfacher Test für EasyOCR"""
import sys
import os

# Fix encoding für Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from src.offline_gains_calculator import OfflineGainsCalculator

print("Teste EasyOCR mit Screenshot...")
print("=" * 70)

calculator = OfflineGainsCalculator(debug=True)
result = calculator.calculate_gains_per_hour('screenshots/photo_2026-01-01_16-46-14.jpg')

print("\n" + "=" * 70)
print("ERGEBNIS:")
print("=" * 70)

if result['success']:
    print(f"Success: {result['success']}")
    print(f"Offline-Zeit (Stunden): {result.get('offline_time_hours')}")
    print(f"\nRaw Data Keys: {list(result.get('raw_data', {}).keys())}")
    
    raw_data = result.get('raw_data', {})
    if raw_data.get('stats'):
        print(f"\nStats: {raw_data['stats']}")
    if raw_data.get('resources'):
        print(f"Resources: {raw_data['resources']}")
    
    if result.get('gains_per_hour'):
        print(f"\nGains per hour: {result['gains_per_hour']}")
else:
    print(f"Error: {result.get('error')}")

