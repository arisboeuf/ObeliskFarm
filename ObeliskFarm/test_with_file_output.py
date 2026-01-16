"""Test mit Datei-Ausgabe für Debug-Informationen"""
import sys
from pathlib import Path
from src.offline_gains_calculator import OfflineGainsCalculator

# Setze UTF-8 Encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

calc = OfflineGainsCalculator(debug=True)
result = calc.calculate_gains_per_hour('screenshots/photo_2026-01-01_16-46-14.jpg')

# Schreibe Ergebnis in Datei
output_file = Path('ocr_debug_output.txt')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("="*70 + "\n")
    f.write("OCR DEBUG AUSGABE\n")
    f.write("="*70 + "\n\n")
    f.write(f"Success: {result['success']}\n")
    if not result['success']:
        f.write(f"Error: {result.get('error')}\n")
    else:
        f.write(f"\nOffline-Zeit: {result.get('offline_time_hours')}\n")
        f.write(f"\nGains pro Stunde:\n")
        gains = result.get("gains_per_hour", {})
        for key, value in gains.items():
            f.write(f"   {key}: {value}\n")
        f.write(f"\nRaw Data:\n")
        raw = result.get("raw_data", {})
        f.write(f"   Offline Hours: {raw.get('offline_hours')}\n")
        f.write(f"   Stats: {raw.get('stats', {})}\n")
        f.write(f"   Resources: {raw.get('resources', {})}\n")

print(f"\nErgebnis wurde in {output_file} gespeichert")



