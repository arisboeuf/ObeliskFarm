"""
Einfacher OCR-Test: Extrahiert Text aus einem Screenshot und gibt ihn aus.
Verwendet nur EasyOCR (kein pytesseract, keine Systeminstallationen nötig).
"""

import os
import sys
from pathlib import Path
from PIL import Image

# Setze UTF-8 Encoding für Windows-Konsolen
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("FEHLER: easyocr ist nicht installiert!")
    print("Installieren Sie es mit: pip install easyocr")
    exit(1)


def extract_text_from_image(image_path: str) -> None:
    """
    Extrahiert Text aus einem Screenshot und gibt ihn aus.
    
    Args:
        image_path: Pfad zum Screenshot
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        print(f"FEHLER: Datei existiert nicht: {image_path}")
        return
    
    print(f"Lade Bild: {image_path}")
    
    # Lade Bild
    try:
        image = Image.open(image_path)
        print(f"Bild geladen: {image.size[0]}x{image.size[1]} Pixel")
    except Exception as e:
        print(f"FEHLER beim Laden des Bildes: {e}")
        return
    
    # Konvertiere zu RGB
    rgb_image = image.convert('RGB')
    
    # Konvertiere PIL Image zu NumPy Array für EasyOCR
    import numpy as np
    img_array = np.array(rgb_image)
    
    # Initialisiere EasyOCR Reader (beim ersten Mal kann das etwas dauern)
    print("\nInitialisiere EasyOCR Reader...")
    print("HINWEIS: Beim ersten Mal werden die Modelle heruntergeladen (kann einige Minuten dauern).")
    print("Falls ein Encoding-Fehler auftritt, einfach nochmal ausfuehren - die Modelle sind dann schon da.\n")
    
    try:
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    except (UnicodeEncodeError, Exception) as e:
        print(f"\nFEHLER beim Initialisieren: {type(e).__name__}")
        if isinstance(e, UnicodeEncodeError):
            print("Encoding-Problem erkannt (normal beim ersten Download unter Windows).")
            print("Loesung: Einfach nochmal ausfuehren - beim zweiten Mal sollten die Modelle schon heruntergeladen sein.")
        else:
            print(f"Details: {e}")
        return
    
    print("EasyOCR Reader erfolgreich initialisiert!\n")
    
    # Führe OCR durch
    print("\nErkenne Text im Bild...")
    results = reader.readtext(img_array, paragraph=False, detail=1)
    
    print(f"\n{'='*70}")
    print(f"ERGEBNIS: {len(results)} Text-Bereiche gefunden")
    print(f"{'='*70}\n")
    
    # Gebe alle erkannten Texte aus
    all_text = []
    for i, (bbox, text, confidence) in enumerate(results, 1):
        print(f"{i:3d}. '{text}' (Confidence: {confidence:.2f})")
        all_text.append(text)
    
    # Gebe kombinierten Text aus
    combined_text = ' '.join(all_text)
    print(f"\n{'='*70}")
    print("KOMPLETTER TEXT:")
    print(f"{'='*70}")
    print(combined_text)
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # Pfad zum Screenshot
    screenshot_path = r"C:\Users\Aris Perrou (PAIA)\OneDrive - PAIA Biotech GmbH\python\Git supervised Skripte\Obelisk\ObeliskFarm\screenshots\photo_2026-01-01_16-46-14.jpg"
    
    extract_text_from_image(screenshot_path)

