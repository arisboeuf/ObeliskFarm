"""Quick check ob Tesseract OCR installiert ist"""
import sys

try:
    import pytesseract
    print("[OK] pytesseract (Python-Paket) ist installiert")
except ImportError:
    print("[ERROR] pytesseract ist nicht installiert")
    print("Installieren Sie es mit: pip install pytesseract")
    sys.exit(1)

print("\nTeste Tesseract OCR...")
try:
    version = pytesseract.get_tesseract_version()
    print(f"[OK] Tesseract OCR ist installiert (Version: {version})")
    print("\nSie koennen jetzt test_main.py verwenden!")
except Exception as e:
    print(f"[ERROR] Tesseract OCR ist nicht installiert oder nicht im PATH")
    print(f"\nFehler: {e}")
    print("\nInstallationsanleitung:")
    print("1. Lade Tesseract OCR herunter: https://github.com/UB-Mannheim/tesseract/wiki")
    print("2. Installiere es und aktivieren Sie 'Add to PATH'")
    print("3. Oeffne ein neues Terminal und versuchen Sie es erneut")
    print("\nSiehe auch: INSTALL_TESSERACT.md")
    sys.exit(1)

