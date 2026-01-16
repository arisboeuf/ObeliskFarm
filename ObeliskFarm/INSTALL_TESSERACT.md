# Tesseract OCR Installation für Windows

## Schritt 1: Tesseract OCR herunterladen

**Download-Link:** https://github.com/UB-Mannheim/tesseract/wiki

Oder direkt: https://digi.bib.uni-mannheim.de/tesseract/

Wählen Sie die neueste Version (z.B. `tesseract-ocr-w64-setup-5.x.x.exe`)

## Schritt 2: Installation

1. **Führen Sie das Installationsprogramm aus**
2. **WICHTIG:** Stellen Sie sicher, dass Sie bei der Installation folgende Option aktivieren:
   - ✅ **"Add Tesseract to PATH"** (oder ähnlich)
   - Falls diese Option nicht vorhanden ist, notieren Sie sich den Installationspfad (normalerweise: `C:\Program Files\Tesseract-OCR`)

3. **Installation abschließen**

## Schritt 3: Pfad überprüfen (falls nicht automatisch hinzugefügt)

Falls Tesseract nicht automatisch im PATH ist, können Sie den Pfad manuell setzen:

1. Öffnen Sie die **Systemumgebungsvariablen**:
   - Windows-Taste + R
   - Geben Sie `sysdm.cpl` ein und drücken Enter
   - Tab "Erweitert" → "Umgebungsvariablen"
   - Unter "Systemvariablen" → "Path" → "Bearbeiten"
   - Fügen Sie hinzu: `C:\Program Files\Tesseract-OCR` (oder Ihren Installationspfad)

2. **Terminal neu starten** (PowerShell/CMD schließen und neu öffnen)

## Schritt 4: Installation testen

Öffnen Sie PowerShell und führen Sie aus:

```powershell
tesseract --version
```

Sie sollten die Versionsnummer sehen, z.B.: `tesseract 5.x.x`

## Schritt 5: Python-Test

Führen Sie aus:

```powershell
python test_main.py screenshots/photo_2026-01-01_16-46-14.jpg --gains
```

## Alternative: Manueller Pfad (falls PATH nicht funktioniert)

Falls Tesseract nicht im PATH gefunden wird, können Sie in Python den Pfad manuell setzen:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

Sie können dies auch in `src/offline_gains_calculator.py` hinzufügen, wenn nötig.

