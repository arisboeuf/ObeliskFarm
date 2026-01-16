"""Debug-Skript um zu sehen, was OCR tatsächlich erkennt"""
import sys
import easyocr
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

image_path = 'screenshots/photo_2026-01-01_16-46-14.jpg'
print(f"Lade Bild: {image_path}")

image = Image.open(image_path)
rgb_image = image.convert('RGB')
img_array = np.array(rgb_image)

print("\nInitialisiere EasyOCR Reader...")
reader = easyocr.Reader(['en'], gpu=False)

print("\nFühre OCR durch...")
results = reader.readtext(img_array)

print(f"\n{'='*70}")
print(f"OCR ERGEBNISSE: {len(results)} Text-Bereiche gefunden")
print(f"{'='*70}\n")

# Zeige alle erkannten Texte
full_text = []
for i, (bbox, text, confidence) in enumerate(results):
    print(f"{i+1}. Text: '{text}' (Confidence: {confidence:.2f})")
    full_text.append(text)

print(f"\n{'='*70}")
print("VOLLSTÄNDIGER TEXT (kombiniert):")
print(f"{'='*70}")
combined_text = ' '.join(full_text)
print(combined_text)

print(f"\n{'='*70}")
print("SUCHE NACH 'OFFLINE GAINS':")
print(f"{'='*70}")
if 'offline' in combined_text.lower() or 'gains' in combined_text.lower():
    print("✓ Gefunden!")
else:
    print("✗ NICHT gefunden!")

sys.stdout.flush()



