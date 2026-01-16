"""
Test-Skript für Icon-Erkennung
Testet die Icon-Erkennung für alle Screenshots im screenshots-Verzeichnis.
"""

import sys
from pathlib import Path

# Füge src-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from src.image_extractor import ImageExtractor

def test_all_screenshots():
    """
    Testet Icon-Erkennung für alle Screenshots.
    """
    screenshots_dir = Path("screenshots")
    
    if not screenshots_dir.exists():
        print(f"[FEHLER] Screenshots-Verzeichnis nicht gefunden: {screenshots_dir}")
        return
    
    # Finde alle JPG/PNG Screenshots
    screenshot_files = list(screenshots_dir.glob("*.jpg")) + list(screenshots_dir.glob("*.png"))
    
    if not screenshot_files:
        print(f"[FEHLER] Keine Screenshots gefunden in {screenshots_dir}")
        return
    
    print("=" * 70)
    print("ICON-ERKENNUNG TEST")
    print("=" * 70)
    print(f"\nGefundene Screenshots: {len(screenshot_files)}\n")
    
    # Initialisiere Image Extractor
    extractor = ImageExtractor(debug=True)
    
    results = []
    
    for screenshot_path in sorted(screenshot_files):
        print("\n" + "=" * 70)
        print(f"Verarbeite: {screenshot_path.name}")
        print("=" * 70)
        
        try:
            # Erkenne Icons
            result = extractor.detect_resource_icons(
                image_path=screenshot_path,
                search_height=300,  # Größerer Suchbereich
                icon_size=(60, 60),  # Etwas größere Icons
                min_icon_spacing=15
            )
            
            if result['success']:
                icons = result['icons']
                print(f"\n[OK] {len(icons)} Icons gefunden!")
                
                for icon in icons:
                    print(f"   Icon {icon['index']}: Position ({icon['x']}, {icon['y']}), "
                          f"Groesse {icon['width']}x{icon['height']}")
                    print(f"      Gespeichert in: {icon['image_path']}")
                
                results.append({
                    'screenshot': screenshot_path.name,
                    'success': True,
                    'icon_count': len(icons),
                    'icons': icons
                })
            else:
                print(f"\n[FEHLER] {result.get('error', 'Unbekannter Fehler')}")
                results.append({
                    'screenshot': screenshot_path.name,
                    'success': False,
                    'error': result.get('error', 'Unbekannter Fehler')
                })
        
        except Exception as e:
            print(f"\n[FEHLER] Ausnahme beim Verarbeiten: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'screenshot': screenshot_path.name,
                'success': False,
                'error': str(e)
            })
    
    # Zusammenfassung
    print("\n" + "=" * 70)
    print("ZUSAMMENFASSUNG")
    print("=" * 70)
    
    successful = sum(1 for r in results if r['success'])
    total_icons = sum(r.get('icon_count', 0) for r in results if r['success'])
    
    print(f"\nErfolgreich verarbeitet: {successful}/{len(results)}")
    print(f"Gesamt gefundene Icons: {total_icons}")
    
    print("\nDetails:")
    for result in results:
        status = "[OK]" if result['success'] else "[FEHLER]"
        icon_count = result.get('icon_count', 0) if result['success'] else 0
        print(f"  {status} {result['screenshot']}: {icon_count} Icons")
        if not result['success']:
            print(f"     Fehler: {result.get('error', 'Unbekannt')}")
    
    print(f"\n[INFO] Alle extrahierten Icons wurden gespeichert in: {extractor.output_dir}")
    print("=" * 70)

if __name__ == "__main__":
    test_all_screenshots()

