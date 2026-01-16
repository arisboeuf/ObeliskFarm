# Obelisk Farm - Python Screenshot-Verarbeitung

Python-Skripte zum Testen und Verarbeiten von Screenshots aus dem Obelisk Farm Spiel.

## 📁 Repository-Struktur

```
ObeliskFarm/
├── src/                                    # Python-Module
│   ├── __init__.py
│   ├── offline_gains_calculator.py        # Modul 1: Offline Gains pro Stunde berechnen
│   └── image_extractor.py                 # Modul 2: Bildausschnitte extrahieren
│
├── test_main.py                            # Hauptskript zum Testen der Module
│
├── screenshots/                            # Input: Screenshots (.jpg)
│   └── ...
│
├── output/                                 # Output: Extrahierte Bildausschnitte (.png)
│   └── extracted/                          # Extrahierte Bildteile
│
├── android_app/                            # Android-App (archiviert, optional)
│   └── ...
│
├── requirements.txt                        # Python-Abhängigkeiten
└── README.md                               # Diese Datei
```

## 🚀 Schnellstart

### 1. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

**Wichtig für OCR (Text-Erkennung):**
- Das Python-Paket `pytesseract` allein reicht nicht aus
- Sie müssen auch **Tesseract OCR** installieren:
  - **Windows**: https://github.com/UB-Mannheim/tesseract/wiki
  - **Mac**: `brew install tesseract`
  - **Linux**: `sudo apt-get install tesseract-ocr`

### 2. Testen

```bash
# Beide Module testen
python test_main.py screenshots/photo_2026-01-01_16-46-14.jpg

# Nur Offline Gains berechnen
python test_main.py screenshots/photo_2026-01-01_16-46-14.jpg --gains

# Nur Bildausschnitte extrahieren
python test_main.py screenshots/photo_2026-01-01_16-46-14.jpg --extract
```

## 📦 Module

### Modul 1: `offline_gains_calculator.py`

Berechnet Offline Gains pro Stunde aus Screenshot-Daten.

**Verwendung:**

```python
from src.offline_gains_calculator import OfflineGainsCalculator

calculator = OfflineGainsCalculator()
result = calculator.calculate_gains_per_hour('screenshot.jpg')

if result['success']:
    print(f"Offline-Zeit: {result['offline_time_hours']:.4f} Stunden")
    print(f"Gains pro Stunde: {result['gains_per_hour']}")
```

**Funktionen:**
- `calculate_gains_per_hour(screenshot_path)` - Berechnet Gains pro Stunde
- `parse_offline_time(time_string)` - Parst Zeit-Strings (z.B. "00h05m15s")

### Modul 2: `image_extractor.py`

Extrahiert Bildausschnitte aus Screenshots und speichert sie als PNG.

**Verwendung:**

```python
from src.image_extractor import ImageExtractor

extractor = ImageExtractor(output_dir='output/extracted')

# Einzelnen Bereich extrahieren
output_path = extractor.extract_region(
    image_path='screenshot.jpg',
    x=100,          # X-Koordinate
    y=200,          # Y-Koordinate
    width=300,      # Breite
    height=150,     # Höhe
    output_name='mein_ausschnitt.png'
)

# Mehrere Bereiche extrahieren
regions = [
    {'x': 50, 'y': 100, 'width': 200, 'height': 100, 'name': 'header.png'},
    {'x': 50, 'y': 250, 'width': 300, 'height': 150, 'name': 'stats.png'}
]
output_paths = extractor.extract_multiple_regions('screenshot.jpg', regions)
```

**Funktionen:**
- `extract_region(...)` - Extrahiert einen einzelnen Bereich
- `extract_multiple_regions(...)` - Extrahiert mehrere Bereiche
- `save_as_png(image, output_path)` - Speichert ein PIL Image als PNG

## 🔧 Entwicklung

Die Module sind **unabhängig voneinander** entwickelt:

- **`offline_gains_calculator.py`** benötigt keine Funktionen aus `image_extractor.py`
- **`image_extractor.py`** benötigt keine Funktionen aus `offline_gains_calculator.py`
- Beide können separat getestet und weiterentwickelt werden

## 📝 Beispiel-Workflow

1. **Screenshot analysieren:**
   ```bash
   python test_main.py screenshots/mein_screenshot.jpg --gains
   ```

2. **Bildausschnitte extrahieren:**
   ```python
   from src.image_extractor import ImageExtractor
   extractor = ImageExtractor()
   
   # Koordinaten müssen für Ihre Screenshots angepasst werden
   extractor.extract_region(
       'screenshots/mein_screenshot.jpg',
       x=100, y=200, width=300, height=150,
       output_name='header.png'
   )
   ```

3. **Extrahierte Daten verwenden:**
   ```python
   from src.offline_gains_calculator import OfflineGainsCalculator
   calculator = OfflineGainsCalculator()
   result = calculator.calculate_gains_per_hour('screenshots/mein_screenshot.jpg')
   # ... verwende result['gains_per_hour']
   ```

## 📋 Abhängigkeiten

- **Pillow** (PIL) - Bildverarbeitung (erforderlich)
- **numpy** - Numerische Operationen (empfohlen)
- **pytesseract** - OCR/Text-Erkennung (optional, für Modul 1)
- **opencv-python** - Erweiterte Bildverarbeitung (optional)

Siehe `requirements.txt` für Details.

## 🎯 Nächste Schritte

1. **Koordinaten für Bildausschnitte finden:**
   - Öffnen Sie einen Screenshot in einem Bildeditor
   - Notieren Sie die X/Y-Koordinaten der Bereiche, die Sie extrahieren möchten
   - Passen Sie die Koordinaten in `test_main.py` oder Ihren eigenen Skripten an

2. **OCR verbessern:**
   - Modul 1 verwendet aktuell pytesseract für Text-Erkennung
   - Für bessere Ergebnisse können Sie die OCR-Parameter anpassen
   - Oder Machine Learning-Modelle integrieren

3. **Module erweitern:**
   - Beide Module sind bewusst einfach gehalten
   - Erweitern Sie sie nach Bedarf für Ihre spezifischen Anforderungen

## 📚 Weitere Informationen

- Siehe `REPOSITORY_STRUCTURE.md` für Details zur Repository-Struktur
- Die Android-App-Code befindet sich in `android_app/` (falls später benötigt)
