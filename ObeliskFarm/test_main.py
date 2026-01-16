"""
Hauptskript zum Testen der Bildverarbeitungs-Module

Verwendung:
    python test_main.py <screenshot.jpg> [--extract] [--gains]
    
Beispiele:
    # Beide Module testen
    python test_main.py screenshots/photo_2026-01-01_16-46-14.jpg
    
    # Nur Gains berechnen
    python test_main.py screenshots/photo_2026-01-01_16-46-14.jpg --gains
    
    # Nur Bildausschnitte extrahieren
    python test_main.py screenshots/photo_2026-01-01_16-46-14.jpg --extract
"""

import sys
import argparse
from pathlib import Path

# Importiere unsere Module
from src.offline_gains_calculator import OfflineGainsCalculator
from src.image_extractor import ImageExtractor


def test_offline_gains(screenshot_path: Path):
    """
    Testet das Offline Gains Calculator Modul.
    """
    print("\n" + "=" * 70)
    print("TEST: OFFLINE GAINS CALCULATOR")
    print("=" * 70)
    
    calculator = OfflineGainsCalculator(debug=True)
    result = calculator.calculate_gains_per_hour(screenshot_path)
    
    if result['success']:
        print(f"\n[OK] Erfolgreich verarbeitet!")
        offline_hours = result.get('offline_time_hours')
        if offline_hours is not None:
            print(f"\nOffline-Zeit: {offline_hours:.4f} Stunden")
        else:
            print(f"\nOffline-Zeit: Nicht gefunden")
        
        gains = result.get('gains_per_hour', {})
        if gains:
            print(f"\n[GAINS] Gains pro Stunde:")
            
            # Stats zuerst
            stats_gains = {k: v for k, v in gains.items() 
                          if not k.startswith('ore_') and not k.startswith('bar_')}
            if stats_gains:
                for key, value in stats_gains.items():
                    # Formatiere je nach Stat-Type
                    if key == 'xp':
                        print(f"   {key.upper()}: {value:,.0f}/h")
                    elif key == 'gold':
                        print(f"   {key.capitalize()}: {value:,.2f}/h")
                    else:
                        print(f"   {key.replace('_', ' ').title()}: {value:,.2f}/h")
            
            # Dann Ores
            ore_gains = {k: v for k, v in gains.items() if k.startswith('ore_')}
            if ore_gains:
                print(f"\n   Ores:")
                for key, value in ore_gains.items():
                    ore_type = key.replace('ore_', '')
                    ore_name = 'Red Ore' if ore_type == 'red' else 'Purple Ore'
                    print(f"      {ore_name}: {value:,.2f}/h")
            
            # Dann Bars
            bar_gains = {k: v for k, v in gains.items() if k.startswith('bar_')}
            if bar_gains:
                print(f"\n   Bars:")
                for key, value in bar_gains.items():
                    bar_type = key.replace('bar_', '')
                    bar_name = 'Red Bar' if bar_type == 'red' else 'Purple Bar'
                    print(f"      {bar_name}: {value:,.2f}/h")
        else:
            print("\n[WARN] Keine Gains pro Stunde berechnet (keine Offline-Zeit gefunden)")
        
        raw_data = result.get('raw_data', {})
        if raw_data.get('stats'):
            print(f"\n[STATS] Extrahierte Statistiken:")
            for key, value in raw_data['stats'].items():
                print(f"   {key}: {value}")
        
        # Zeige Ores und Bars
        resources = raw_data.get('resources', {})
        if resources.get('ores') or resources.get('bars'):
            print(f"\n[RESOURCES] Extrahierte Ressourcen:")
            ores = resources.get('ores', {})
            if ores:
                print(f"   Ores:")
                for ore_type, value in ores.items():
                    print(f"      {ore_type}: {value}")
            bars = resources.get('bars', {})
            if bars:
                print(f"   Bars:")
                for bar_type, value in bars.items():
                    print(f"      {bar_type}: {value}")
    else:
        print(f"\n[ERROR] Fehler: {result.get('error', 'Unbekannter Fehler')}")
    
    return result


def test_image_extraction(screenshot_path: Path):
    """
    Testet das Image Extractor Modul.
    """
    print("\n" + "=" * 70)
    print("TEST: IMAGE EXTRACTOR")
    print("=" * 70)
    
    try:
        extractor = ImageExtractor()
        
        # Beispiel: Extrahiere einen Bereich (Koordinaten müssen angepasst werden)
        # Dies ist nur ein Beispiel - Sie müssen die richtigen Koordinaten für Ihr Screenshot-Schema finden
        print(f"\nExtrahiere Bildausschnitte...")
        print(f"(Hinweis: Verwenden Sie Beispiel-Koordinaten - passen Sie diese an Ihre Screenshots an)")
        
        try:
            # Beispiel-Koordinaten (müssen für Ihre Screenshots angepasst werden)
            # Format: (x, y, width, height)
            example_regions = [
                {
                    'x': 50,
                    'y': 100,
                    'width': 200,
                    'height': 100,
                    'name': 'region_header.png'
                },
                {
                    'x': 50,
                    'y': 250,
                    'width': 300,
                    'height': 150,
                    'name': 'region_stats.png'
                }
            ]
            
            # Lade Bild, um Dimensionen zu prüfen
            from PIL import Image
            img = Image.open(screenshot_path)
            img_width, img_height = img.size
            print(f"\nBild-Dimensionen: {img_width} x {img_height}")
            
            # Prüfe, ob Beispiel-Koordinaten gültig sind
            valid_regions = []
            for region in example_regions:
                x, y, w, h = region['x'], region['y'], region['width'], region['height']
                if x + w <= img_width and y + h <= img_height:
                    valid_regions.append(region)
                else:
                    print(f"⚠️  Region '{region['name']}' überschreitet Bildgrenzen - übersprungen")
            
            if valid_regions:
                output_paths = extractor.extract_multiple_regions(
                    screenshot_path,
                    valid_regions
                )
                print(f"\n✅ {len(output_paths)} Region(en) extrahiert:")
                for path in output_paths:
                    print(f"   {path}")
            else:
                print(f"\n⚠️  Keine gültigen Regionen gefunden.")
                print(f"   Passen Sie die Koordinaten in test_main.py an Ihre Screenshots an.")
                print(f"\n   Beispiel für manuelle Extraktion:")
                print(f"   extractor.extract_region(")
                print(f"       '{screenshot_path}',")
                print(f"       x=100, y=200, width=300, height=150,")
                print(f"       output_name='mein_ausschnitt.png'")
                print(f"   )")
        
        except Exception as e:
            print(f"\n⚠️  Fehler beim Extrahieren (Koordinaten möglicherweise ungültig): {e}")
            print(f"\n   Verwenden Sie diese Methode für manuelle Extraktion:")
            print(f"   extractor = ImageExtractor()")
            print(f"   path = extractor.extract_region(")
            print(f"       image_path='{screenshot_path}',")
            print(f"       x=100, y=200, width=300, height=150,")
            print(f"       output_name='mein_ausschnitt.png'")
            print(f"   )")
    
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        return False
    
    return True


def main():
    """Hauptfunktion"""
    parser = argparse.ArgumentParser(
        description='Testet die Bildverarbeitungs-Module',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Beide Module testen
  python test_main.py screenshots/photo.jpg
  
  # Nur Gains berechnen
  python test_main.py screenshots/photo.jpg --gains
  
  # Nur Bildausschnitte extrahieren
  python test_main.py screenshots/photo.jpg --extract
        """
    )
    
    parser.add_argument(
        'screenshot',
        type=str,
        help='Pfad zum Screenshot (.jpg, .png)'
    )
    
    parser.add_argument(
        '--gains',
        action='store_true',
        help='Nur Offline Gains Calculator testen'
    )
    
    parser.add_argument(
        '--extract',
        action='store_true',
        help='Nur Image Extractor testen'
    )
    
    args = parser.parse_args()
    
    screenshot_path = Path(args.screenshot)
    
    if not screenshot_path.exists():
        print(f"❌ Fehler: Screenshot nicht gefunden: {screenshot_path}")
        return 1
    
    print("=" * 70)
    print("OBELISK FARM - BILDVERARBEITUNGS-TEST")
    print("=" * 70)
    print(f"\nScreenshot: {screenshot_path}")
    
    # Teste Module
    if args.extract:
        # Nur Extraktion
        test_image_extraction(screenshot_path)
    elif args.gains:
        # Nur Gains
        test_offline_gains(screenshot_path)
    else:
        # Beide Module testen
        test_offline_gains(screenshot_path)
        test_image_extraction(screenshot_path)
    
    print("\n" + "=" * 70)
    print("TEST ABGESCHLOSSEN")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

