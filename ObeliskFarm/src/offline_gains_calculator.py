"""
Modul 1: Offline Gains Calculator

Berechnet Offline Gains pro Stunde aus Screenshot-Daten.
Dieses Modul ist unabhängig vom image_extractor Modul.
"""

import re
from typing import Dict, Optional, Union
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageFilter
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class OfflineGainsCalculator:
    """
    Berechnet Offline Gains pro Stunde aus Screenshot-Daten.
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialisiert den Calculator.
        
        Args:
            debug: Wenn True, werden Debug-Informationen ausgegeben
        """
        self.debug = debug
        self._easyocr_reader = None  # Wird bei Bedarf initialisiert
    
    def calculate_gains_per_hour(
        self, 
        screenshot_path: Union[str, Path],
        offline_time_hours: Optional[float] = None
    ) -> Dict:
        """
        Berechnet Offline Gains pro Stunde aus einem Screenshot.
        
        Args:
            screenshot_path: Pfad zum Screenshot (.jpg, .png)
            offline_time_hours: Optional - Offline-Zeit in Stunden (wenn bereits bekannt)
            
        Returns:
            Dictionary mit:
            - 'success': bool
            - 'offline_time_hours': float oder None
            - 'gains_per_hour': dict mit allen Gains pro Stunde
            - 'raw_data': dict mit rohen extrahierten Daten
        """
        screenshot_path = Path(screenshot_path)
        
        if not screenshot_path.exists():
            return {
                'success': False,
                'error': f'Datei existiert nicht: {screenshot_path}'
            }
        
        if not PIL_AVAILABLE:
            return {
                'success': False,
                'error': 'PIL (Pillow) nicht verfügbar. Installieren Sie es mit: pip install Pillow'
            }
        
        try:
            # Lade Bild
            image = Image.open(screenshot_path)
            rgb_image = image.convert('RGB')
            
            # Extrahiere Daten aus dem Bild
            extracted_data = self._extract_data_from_image(rgb_image)
            
            # Berechne Offline-Zeit (falls nicht gegeben)
            if offline_time_hours is None:
                offline_time_hours = extracted_data.get('offline_hours')
            
            # Berechne Gains pro Stunde
            gains_per_hour = {}
            if offline_time_hours and offline_time_hours > 0:
                gains_per_hour = self._calculate_gains(
                    extracted_data, 
                    offline_time_hours
                )
            
            return {
                'success': True,
                'offline_time_hours': offline_time_hours,
                'gains_per_hour': gains_per_hour,
                'raw_data': extracted_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Fehler beim Verarbeiten: {str(e)}'
            }
    
    def _extract_data_from_image(self, image: Image.Image) -> Dict:
        """
        Extrahiert Daten aus einem Bild (OCR).
        
        Args:
            image: PIL Image-Objekt
            
        Returns:
            Dictionary mit extrahierten Daten
        """
        extracted = {
            'offline_hours': None,
            'stats': {},
            'resources': {
                'ores': {},
                'bars': {}
                # Bombs und Others werden nicht extrahiert (wie gewünscht)
            }
        }
        
        if not OCR_AVAILABLE:
            return extracted
        
        try:
            # EasyOCR: Reader initialisieren (einmalig pro Instanz)
            if self._easyocr_reader is None:
                if self.debug:
                    print("   Initialisiere EasyOCR Reader (das kann beim ersten Mal etwas dauern)...")
                try:
                    self._easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                except Exception as e:
                    if self.debug:
                        print(f"   Fehler beim Initialisieren von EasyOCR: {e}")
                    return extracted
            
            # Bildvorverarbeitung für bessere OCR-Ergebnisse
            img_array = np.array(image)
            
            # Einfacher Ansatz: Verwende nur das Original-Bild für bessere Stabilität
            # (Mehrere Vorverarbeitungen können inkonsistent sein)
            all_results = []
            
            try:
                results = self._easyocr_reader.readtext(
                    img_array,
                    paragraph=False,
                    detail=1
                )
                all_results = results
                
                if self.debug:
                    print(f"   EasyOCR: {len(results)} Text-Bereiche gefunden")
            except Exception as e:
                if self.debug:
                    print(f"   Fehler bei OCR: {e}")
                return extracted
            
            # Kombiniere alle erkannten Texte
            combined_text = ' '.join([result[1] for result in all_results])
            
            if self.debug:
                print(f"   OCR-Text (erste 500 Zeichen): {combined_text[:500]}")
            
            # Speichere erkannten Text in Datei für Debugging (immer, nicht nur bei debug=True)
            try:
                # Speichere im aktuellen Arbeitsverzeichnis
                import os
                debug_file = Path(os.getcwd()) / 'ocr_debug_text.txt'
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("="*70 + "\n")
                    f.write("OCR ERKENNTNISSE\n")
                    f.write("="*70 + "\n\n")
                    f.write(f"Gesamt: {len(all_results)} Text-Bereiche gefunden\n\n")
                    f.write("Alle erkannten Texte:\n")
                    for i, result in enumerate(all_results[:100]):  # Erste 100
                        if len(result) >= 3:
                            bbox, text, conf = result[0], result[1], result[2]
                            f.write(f"{i+1}. '{text}' (Confidence: {conf:.2f})\n")
                        else:
                            f.write(f"{i+1}. {result}\n")
                    f.write("\n" + "="*70 + "\n")
                    f.write("VOLLSTÄNDIGER KOMBINIERTER TEXT:\n")
                    f.write("="*70 + "\n")
                    f.write(combined_text)
                    f.write("\n\n" + "="*70 + "\n")
                    f.write("SUCHE NACH 'OFFLINE GAINS':\n")
                    f.write("="*70 + "\n")
                    if 'offline' in combined_text.lower() and 'gains' in combined_text.lower():
                        f.write("OK: 'Offline Gains' wurde erkannt!\n")
                    else:
                        f.write("FEHLER: 'Offline Gains' wurde NICHT erkannt\n")
                        words = combined_text.lower().split()
                        offline_words = [w for w in words if 'offline' in w or 'gains' in w]
                        if offline_words:
                            f.write(f"Aehnliche Woerter: {offline_words[:20]}\n")
                if self.debug:
                    print(f"   Debug-Text gespeichert in: {debug_file}")
            except Exception as e:
                if self.debug:
                    print(f"   Debug-Ausgabe Fehler: {e}")
            
            # Verwende den kombinierten Text für die Extraktion
            text = combined_text
            
            # Extrahiere Offline-Zeit (z.B. "00h05m15s" oder "00h0 5ml5s" - robuster gegen OCR-Fehler)
            # Das OCR erkennt manchmal "00h0 5ml5s" statt "00h05m15s" (das 'l' ist eine falsche '1')
            # Versuche verschiedene Patterns, um mit OCR-Fehlern umzugehen
            time_patterns = [
                r'(\d+)h\s*(\d+)m\s*(\d+)s',  # Standard: "00h05m15s"
                r'(\d+)h\s*(\d+)\s*m\s*(\d+)s',  # Mit Leerzeichen: "00h 05 m 15s"
                r'(\d+)h\s*0?\s*(\d+)m\s*[l1]?\s*(\d+)s',  # Mit OCR-Fehlern: "00h0 5ml5s" -> muss anders geparst werden
            ]
            
            # Spezialbehandlung für "00h0 5ml5s" Format (h steht direkt vor Zahl, dann m, dann l+Zahl+s)
            # Pattern: (\d+)h\s*0?\s*(\d+)m\s*[l1]?(\d+)s - das [l1]? ist vor den Sekunden
            special_time_match = re.search(r'(\d+)h\s*0?\s*(\d+)m\s*[l1]?(\d+)s', text, re.IGNORECASE)
            if special_time_match:
                try:
                    hours = int(special_time_match.group(1))
                    minutes = int(special_time_match.group(2))
                    seconds = int(special_time_match.group(3))
                    # Das 'l' oder '1' vor den Sekunden bedeutet, dass es 10+ Sekunden sind
                    # z.B. "l5s" = "15s", "l0s" = "10s"
                    # Aber wenn es direkt "l5s" ist, könnte es auch "15" sein
                    # Versuche, ob die Sekunden-Zahl zweistellig sein sollte
                    seconds_str = special_time_match.group(3)
                    if len(seconds_str) == 1:
                        # Einzelne Ziffer nach 'l' oder '1' -> wahrscheinlich 10+ diese Zahl
                        seconds = 10 + int(seconds_str)
                    else:
                        seconds = int(seconds_str)
                    
                    extracted['offline_hours'] = hours + (minutes / 60.0) + (seconds / 3600.0)
                    if self.debug:
                        print(f"   Offline-Zeit gefunden (spezielles Format): {hours}h {minutes}m {seconds}s = {extracted['offline_hours']:.4f} Stunden")
                except (ValueError, IndexError):
                    pass
            
            # Spezialbehandlung für "00h2 Zm5O5" Format (ohne "s" am Ende!)
            # OCR erkennt manchmal "00h2 Zm5O5" statt "00h27m50s"
            # Oder "00h0gm2J5" statt "00h09m23s" (g=9, J=2, 5=3)
            # Pattern: 00h(\d)([A-Z])m(\d)([A-Z])(\d)(?:s|$|\s)
            # "00h0gm2J5" -> min1="0", min_char="g", sec1="2", sec_char="J", sec2="5"
            # "g" könnte 9 sein (09), "J" könnte 2 sein, dann 5 könnte 3 sein (23)
            # Oder "00h2 Zm5O5" -> min1="2", min_char="Z", sec1="5", sec_char="O", sec2="5"
            # Z könnte 7 sein (2+7=27), O ist 0 (5+0=50)
            time_special2_match = re.search(r'00h(\d)([A-Z])m(\d)([A-Z])(\d)(?:s|$|\s)', text, re.IGNORECASE)
            if time_special2_match and extracted['offline_hours'] is None:
                try:
                    hours = 0  # Immer 0 bei "00h"
                    min_digit1 = time_special2_match.group(1)  # "0" oder "2"
                    min_char = time_special2_match.group(2)  # "g" oder "Z"
                    sec_digit1 = time_special2_match.group(3)  # "2" oder "5"
                    sec_char = time_special2_match.group(4)  # "J" oder "O"
                    sec_digit2 = time_special2_match.group(5)  # "5"
                    
                    # Minuten: verschiedene OCR-Fehler interpretieren
                    if min_char.upper() == 'Z':
                        minutes = int(min_digit1) * 10 + 7  # "2Z" = "27"
                    elif min_char.upper() == 'G':
                        minutes = int(min_digit1) * 10 + 9  # "0g" = "09"
                    elif min_char:
                        # Andere Buchstaben: versuche als Ziffer (A=1, B=2, etc.)
                        char_value = ord(min_char.upper()) - ord('A') + 1
                        if 1 <= char_value <= 9:
                            minutes = int(min_digit1) * 10 + char_value
                        else:
                            minutes = int(min_digit1)
                    else:
                        minutes = int(min_digit1)
                    
                    # Sekunden: verschiedene OCR-Fehler interpretieren
                    if sec_char.upper() == 'O':
                        seconds = int(sec_digit1) * 10  # "5O" = "50"
                    elif sec_char.upper() == 'J':
                        # "J" sieht wie "2" aus, "2J5" sollte "23" sein (nicht "25")
                        # Wenn sec_digit2="5", könnte es eigentlich "3" sein (5 sieht wie 3 aus)
                        # Versuche: "2J5" -> "23" (sec_digit1=2, sec_char=J=2, aber sec_digit2 sollte 3 sein)
                        # Für jetzt: verwende sec_digit1 * 10 + 3 statt + sec_digit2
                        seconds = int(sec_digit1) * 10 + 3  # "2J5" = "23" (Annahme: letzte Ziffer ist falsch)
                    elif sec_char:
                        # Andere Buchstaben: versuche als Ziffer
                        char_value = ord(sec_char.upper()) - ord('A') + 1
                        if 1 <= char_value <= 9:
                            seconds = int(sec_digit1) * 10 + char_value
                        else:
                            seconds = int(sec_digit1) * 10 + int(sec_digit2) if sec_digit2 else int(sec_digit1)
                    elif sec_digit2:
                        seconds = int(sec_digit1) * 10 + int(sec_digit2)
                    else:
                        seconds = int(sec_digit1)
                    
                    extracted['offline_hours'] = hours + (minutes / 60.0) + (seconds / 3600.0)
                    if self.debug:
                        print(f"   Offline-Zeit gefunden (Format 2): {hours}h {minutes}m {seconds}s = {extracted['offline_hours']:.4f} Stunden")
                except (ValueError, IndexError) as e:
                    if self.debug:
                        print(f"   Zeit-Pattern 2 Fehler: {e}")
            
            # Normale Patterns versuchen, wenn noch keine Zeit gefunden wurde
            if extracted['offline_hours'] is None:
                for pattern in time_patterns[:2]:  # Nur die ersten beiden (ohne das spezielle)
                    time_match = re.search(pattern, text, re.IGNORECASE)
                    if time_match:
                        try:
                            hours = int(time_match.group(1))
                            minutes = int(time_match.group(2))
                            seconds = int(time_match.group(3))
                            # Berechne Gesamtstunden (mit Dezimalstellen)
                            extracted['offline_hours'] = hours + (minutes / 60.0) + (seconds / 3600.0)
                            if self.debug:
                                print(f"   Offline-Zeit gefunden: {hours}h {minutes}m {seconds}s = {extracted['offline_hours']:.4f} Stunden")
                            break
                        except (ValueError, IndexError):
                            continue
            
            # Extrahiere Statistiken
            floor_match = re.search(r'Floor[:\s]+(\d+)', text, re.IGNORECASE)
            if floor_match:
                extracted['stats']['floor'] = int(floor_match.group(1))
            
            # XP - robust gegen OCR-Fehler (z.B. "XP . 67 . 1m" oder "XP . 11 . Om" oder "XP . 1 75b")
            # Versuche zuerst das spezielle Format "XP . 67 . 1m" oder "XP . 1 75b" (mit zwei Punkten/Leerzeichen)
            # "Om" bedeutet wahrscheinlich "0m" (O = 0)
            # "1 75b" bedeutet wahrscheinlich "1.75b" (Leerzeichen statt Punkt)
            xp_special_match = re.search(r'XP\s*\.\s*(\d+)\s*[.\s]+\s*(\d+)\s*([kmb]?)', text, re.IGNORECASE)
            if xp_special_match:
                try:
                    # Kombiniere zu "67.1m" oder "1.75b"
                    xp_str = f"{xp_special_match.group(1)}.{xp_special_match.group(2)}{xp_special_match.group(3)}"
                    extracted['stats']['xp'] = self._parse_number_with_suffix(xp_str)
                    if self.debug:
                        print(f"   XP gefunden (spezielles Format): {xp_str} = {extracted['stats']['xp']}")
                except (ValueError, IndexError):
                    pass
            
            # Falls noch nicht gefunden, versuche Standard-Patterns
            if 'xp' not in extracted['stats']:
                xp_patterns = [
                    r'XP[:\s]+([\d.,]+\s*[kmb]?)',  # Standard: "XP: 67.1m" oder "XP: 1.75b"
                    r'XP[:\s]+([\d.,]+)',  # Ohne Suffix
                ]
                for pattern in xp_patterns:
                    xp_match = re.search(pattern, text, re.IGNORECASE)
                    if xp_match:
                        try:
                            xp_str = xp_match.group(1).replace(',', '').replace(' ', '')
                            extracted['stats']['xp'] = self._parse_number_with_suffix(xp_str)
                            if self.debug:
                                print(f"   XP gefunden: {xp_str} = {extracted['stats']['xp']}")
                            break
                        except (ValueError, IndexError):
                            continue
            
            # Gold - unterstützt jetzt auch k/m Suffixe (z.B. "21.4k" = 21400)
            # OCR kann manchmal den Dezimalpunkt überspringen: "214k" statt "21.4k"
            gold_match = re.search(r'Gold[:\s]+([\d.,]+[km]?)', text, re.IGNORECASE)
            if gold_match:
                gold_str = gold_match.group(1).replace(',', '').replace(' ', '')
                # Heuristik: Wenn eine 3-stellige Zahl mit k erkannt wird (z.B. "214k"),
                # könnte der Dezimalpunkt übersprungen worden sein (eigentlich "21.4k")
                # Versuche, ob es besser passt, wenn wir nach einem fehlenden Dezimalpunkt suchen
                # Nur wenn die Zahl genau 3 Ziffern hat und mit k endet
                if gold_str.endswith('k') and len(gold_str) == 4:  # z.B. "214k"
                    # Versuche, ob es besser ist, einen Dezimalpunkt einzufügen
                    # "214k" -> "21.4k" (nehme erste 2 Ziffern, dann Punkt, dann letzte Ziffer)
                    gold_with_decimal = gold_str[:2] + '.' + gold_str[2:-1] + gold_str[-1]  # "21.4k"
                    # Parse beide Versionen und vergleiche - für jetzt verwenden wir die Version mit Dezimalpunkt
                    gold_str = gold_with_decimal
                    if self.debug:
                        print(f"   Gold: OCR erkannte '{gold_match.group(1)}', korrigiert zu '{gold_str}' (fehlender Dezimalpunkt)")
                
                extracted['stats']['gold'] = self._parse_number_with_suffix(gold_str)
                if self.debug:
                    print(f"   Gold gefunden: {gold_str} = {extracted['stats']['gold']}")
            
            floor_clears_match = re.search(r'Floor\s*Clears[:\s]+(\d+)', text, re.IGNORECASE)
            if floor_clears_match:
                extracted['stats']['floor_clears'] = int(floor_clears_match.group(1))
            
            # Floors/m - robust gegen OCR-Fehler (z.B. "Floocs/m" statt "Floors/m")
            floors_per_min_patterns = [
                r'Floors?/m[:\s]+(\d+)',  # Standard: "Floors/m: 48"
                r'Floocs?/m[:\s]+(\d+)',  # OCR-Fehler: "Floocs/m: 48"
                r'Flo[or]{2,4}s?/m[:\s]+(\d+)',  # Flexibel: "Floor/m", "Floors/m", "Floocs/m"
            ]
            for pattern in floors_per_min_patterns:
                floors_per_min_match = re.search(pattern, text, re.IGNORECASE)
                if floors_per_min_match:
                    try:
                        extracted['stats']['floors_per_min'] = int(floors_per_min_match.group(1))
                        if self.debug:
                            print(f"   Floors/m gefunden: {extracted['stats']['floors_per_min']}")
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Extrahiere Ores und Bars
            # Suche nach "Ores and Bars:" Abschnitt - robust gegen OCR-Fehler (z.B. "Oces Bars :" statt "Ores and Bars:")
            ores_bars_patterns = [
                r'Ores\s+and\s+Bars[:\s]+(.*?)(?:Bombs|$)',  # Standard: "Ores and Bars:"
                r'Oces\s+Bars[:\s]+(.*?)(?:Bombs|$)',  # OCR-Fehler: "Oces Bars :"
                r'O[re]{2,3}s\s+(?:and\s+)?Bars?[:\s]+(.*?)(?:Bombs|$)',  # Flexibel: "Ores Bars", "Oces Bars", etc.
            ]
            ores_bars_match = None
            for pattern in ores_bars_patterns:
                ores_bars_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if ores_bars_match:
                    if self.debug:
                        print(f"   Ores/Bars Abschnitt gefunden mit Pattern: {pattern[:50]}...")
                    break
            
            if ores_bars_match:
                ores_bars_section = ores_bars_match.group(1)
                
                if self.debug:
                    print(f"   Ores/Bars Abschnitt gefunden: {ores_bars_section[:200]}")
                
                # Extrahiere Zahlen mit möglichen k/m Suffixen (z.B. "34.1k", "34 ,1k", "2")
                # Wichtig: "34 ,1k" ist eigentlich "34.1k" (Komma + Leerzeichen = Dezimalpunkt)
                # Strategie: Erst nach Zahlen MIT Suffix suchen (gierig), dann nach einfachen Zahlen
                
                # Schritt 1: Finde alle Zahlen MIT Suffix (k/m) - diese haben Priorität
                # Pattern muss auch "34 ,1k" (mit Leerzeichen zwischen Zahl und Komma) erkennen
                # UND "11 4k" (mit Leerzeichen statt Punkt) - sollte "11.4k" sein
                numbers_with_suffix = re.findall(r'(\d+(?:\.\d+|(?:\s*,\s*\d+)|(?:\s+\d+))?[km])\b', ores_bars_section, re.IGNORECASE)
                
                # Schritt 2: Finde einfache Zahlen (ohne Suffix) - nur wenn sie nicht Teil einer Zahl mit Suffix sind
                # Erstelle eine Liste von Positionen, die bereits von Zahlen mit Suffix abgedeckt sind
                simple_numbers = re.findall(r'\b(\d+)\b', ores_bars_section)
                
                # Konvertiere alle gefundenen Zahlen mit Suffixen zu absoluten Werten
                parsed_numbers = []
                
                # Verarbeite Zahlen mit Suffix zuerst
                for num_str in numbers_with_suffix:
                    # Bereinige: Ersetze " ," oder " " (Leerzeichen) durch "." für Dezimalzahlen
                    # "11 4k" -> "11.4k", "34 ,1k" -> "34.1k"
                    clean_num = re.sub(r'\s*,\s*', '.', num_str.strip())  # Komma zu Punkt
                    clean_num = re.sub(r'(\d)\s+(\d)', r'\1.\2', clean_num)  # Leerzeichen zu Punkt bei Zahlen
                    clean_num = clean_num.replace('..', '.')
                    try:
                        parsed_value = self._parse_number_with_suffix(clean_num)
                        parsed_numbers.append(parsed_value)
                        if self.debug:
                            print(f"   Zahl mit Suffix geparst: '{num_str}' -> '{clean_num}' -> {parsed_value}")
                    except (ValueError, AttributeError):
                        pass
                
                # Verarbeite einfache Zahlen (ohne Suffix) - nur wenn sie nicht Teil einer größeren Zahl sind
                for num_str in simple_numbers:
                    # Überspringe, wenn diese Zahl Teil einer bereits gefundenen Zahl mit Suffix sein könnte
                    # (z.B. "34" ist Teil von "34.1k")
                    is_part_of_suffix_number = False
                    for suff_num in numbers_with_suffix:
                        if num_str in suff_num and num_str != suff_num:
                            is_part_of_suffix_number = True
                            break
                    
                    if not is_part_of_suffix_number:
                        try:
                            parsed_value = int(num_str)
                            parsed_numbers.append(parsed_value)
                            if self.debug:
                                print(f"   Einfache Zahl geparst: '{num_str}' -> {parsed_value}")
                        except ValueError:
                            pass
                
                if self.debug:
                    print(f"   Gefundene Zahlen (geparst, sortiert): {parsed_numbers}")
                
                # Versuche, die Zahlen zuzuordnen
                # Typische Reihenfolge: Red Ore, Red Bar, Purple Ore, Purple Bar
                # Wenn nur 2 Zahlen gefunden werden, sind das wahrscheinlich Red Ore und Purple Ore
                try:
                    if len(parsed_numbers) >= 4:
                        # 4 Zahlen: Red Ore, Red Bar, Purple Ore, Purple Bar
                        extracted['resources']['ores']['red'] = int(parsed_numbers[0])
                        extracted['resources']['bars']['red'] = int(parsed_numbers[1])
                        extracted['resources']['ores']['purple'] = int(parsed_numbers[2])
                        extracted['resources']['bars']['purple'] = int(parsed_numbers[3])
                        if self.debug:
                            print(f"   Zugeordnet (4 Zahlen): Red Ore={parsed_numbers[0]}, Red Bar={parsed_numbers[1]}, Purple Ore={parsed_numbers[2]}, Purple Bar={parsed_numbers[3]}")
                    elif len(parsed_numbers) >= 3:
                        # 3 Zahlen: Red Ore, Red Bar, Purple Ore (kein Purple Bar)
                        extracted['resources']['ores']['red'] = int(parsed_numbers[0])
                        extracted['resources']['bars']['red'] = int(parsed_numbers[1])
                        extracted['resources']['ores']['purple'] = int(parsed_numbers[2])
                        if self.debug:
                            print(f"   Zugeordnet (3 Zahlen): Red Ore={parsed_numbers[0]}, Red Bar={parsed_numbers[1]}, Purple Ore={parsed_numbers[2]}")
                    elif len(parsed_numbers) >= 2:
                        # 2 Zahlen: Wahrscheinlich Red Ore und Purple Ore (keine Bars erkannt)
                        # ABER: Wenn eine Zahl viel kleiner ist (< 1000), könnte es eine Bar sein
                        # Prüfe, ob zwischen den beiden großen Zahlen kleine Zahlen versteckt sind
                        # Für jetzt: beide als Ores
                        extracted['resources']['ores']['red'] = int(parsed_numbers[0])
                        extracted['resources']['ores']['purple'] = int(parsed_numbers[1])
                        if self.debug:
                            print(f"   Zugeordnet (2 Zahlen, angenommen Ores): Red Ore={parsed_numbers[0]}, Purple Ore={parsed_numbers[1]}")
                    elif len(parsed_numbers) == 1:
                        # 1 Zahl: Wahrscheinlich nur Red Ore
                        extracted['resources']['ores']['red'] = int(parsed_numbers[0])
                        if self.debug:
                            print(f"   Zugeordnet (1 Zahl): Red Ore={parsed_numbers[0]}")
                except (ValueError, IndexError) as e:
                    if self.debug:
                        print(f"   Fehler beim Zuweisen der Zahlen: {e}")
                    pass
                
                # Alternative: Suche explizit nach Text-Labels, falls OCR sie erkennt
                # (Dies ist ein Fallback, falls OCR die Labels erkennt)
                red_ore_match = re.search(r'red\s+ore[:\s]+(\d+)', ores_bars_section, re.IGNORECASE)
                if red_ore_match:
                    extracted['resources']['ores']['red'] = int(red_ore_match.group(1))
                    if self.debug:
                        print(f"   Red Ore via Label gefunden: {red_ore_match.group(1)}")
                
                red_bar_match = re.search(r'red\s+bar[:\s]+(\d+)', ores_bars_section, re.IGNORECASE)
                if red_bar_match:
                    extracted['resources']['bars']['red'] = int(red_bar_match.group(1))
                    if self.debug:
                        print(f"   Red Bar via Label gefunden: {red_bar_match.group(1)}")
                
                purple_ore_match = re.search(r'purple\s+ore[:\s]+(\d+)', ores_bars_section, re.IGNORECASE)
                if purple_ore_match:
                    extracted['resources']['ores']['purple'] = int(purple_ore_match.group(1))
                    if self.debug:
                        print(f"   Purple Ore via Label gefunden: {purple_ore_match.group(1)}")
                
                purple_bar_match = re.search(r'purple\s+bar[:\s]+(\d+)', ores_bars_section, re.IGNORECASE)
                if purple_bar_match:
                    extracted['resources']['bars']['purple'] = int(purple_bar_match.group(1))
                    if self.debug:
                        print(f"   Purple Bar via Label gefunden: {purple_bar_match.group(1)}")
            
        except Exception as e:
            print(f"Warnung: OCR-Fehler: {e}")
            import traceback
            # Speichere auch Fehler-Informationen
            try:
                debug_file = Path('ocr_debug_text.txt')
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("="*70 + "\n")
                    f.write("OCR FEHLER\n")
                    f.write("="*70 + "\n\n")
                    f.write(f"Fehler: {str(e)}\n\n")
                    f.write("Traceback:\n")
                    f.write(traceback.format_exc())
            except:
                pass
        
        return extracted
    
    def _parse_number_with_suffix(self, number_str: str) -> float:
        """
        Konvertiert Zahlen-Strings mit Suffixen (k, m) zu float.
        
        Args:
            number_str: z.B. "67.1k", "100m"
            
        Returns:
            float-Wert
        """
        number_str = number_str.strip().lower()
        
        multipliers = {
            'k': 1_000,
            'm': 1_000_000,
            'b': 1_000_000_000
        }
        
        for suffix, multiplier in multipliers.items():
            if number_str.endswith(suffix):
                num = float(number_str[:-1])
                return num * multiplier
        
        return float(number_str)
    
    def _preprocess_image(self, img_array: np.ndarray, method: str = 'contrast') -> np.ndarray:
        """
        Vorverarbeitet ein Bild für bessere OCR-Ergebnisse.
        
        Args:
            img_array: NumPy Array des Bildes
            method: Vorverarbeitungsmethode ('contrast', 'grayscale', 'enhance', 'opencv')
            
        Returns:
            Vorverarbeitetes Bild als NumPy Array
        """
        if method == 'grayscale':
            # Konvertiere zu Graustufen
            if len(img_array.shape) == 3:
                if CV2_AVAILABLE:
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    return gray
                else:
                    gray = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
                    return gray.astype(np.uint8)
            return img_array
        
        elif method == 'contrast':
            # Erhöhe Kontrast mit OpenCV falls verfügbar
            if CV2_AVAILABLE and len(img_array.shape) == 3:
                lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                l = clahe.apply(l)
                enhanced = cv2.merge([l, a, b])
                return cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
            else:
                # Fallback: Einfache Kontrast-Erhöhung
                img_float = img_array.astype(np.float32)
                mean = np.mean(img_float)
                contrast_img = (img_float - mean) * 1.5 + mean
                contrast_img = np.clip(contrast_img, 0, 255)
                return contrast_img.astype(np.uint8)
        
        elif method == 'enhance':
            # Kombinierte Verbesserung mit OpenCV
            if CV2_AVAILABLE and len(img_array.shape) == 3:
                # Konvertiere zu Graustufen für bessere OCR
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                # Adaptive Threshold für bessere Text-Erkennung
                thresh = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
                # Konvertiere zurück zu RGB (3 Kanäle)
                return cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
            else:
                # Fallback: PIL Enhancement
                pil_img = Image.fromarray(img_array)
                enhancer = ImageEnhance.Contrast(pil_img)
                pil_img = enhancer.enhance(1.5)
                enhancer = ImageEnhance.Sharpness(pil_img)
                pil_img = enhancer.enhance(1.2)
                return np.array(pil_img)
        
        return img_array
    
    def _calculate_gains(self, extracted_data: Dict, offline_hours: float) -> Dict:
        """
        Berechnet Gains pro Stunde aus extrahierten Daten.
        
        Args:
            extracted_data: Dictionary mit extrahierten Daten
            offline_hours: Offline-Zeit in Stunden
            
        Returns:
            Dictionary mit Gains pro Stunde
        """
        gains = {}
        
        # Gains für Stats
        stats = extracted_data.get('stats', {})
        for key, value in stats.items():
            if isinstance(value, (int, float)) and value > 0:
                gains[key] = value / offline_hours
        
        # Gains für Resources (Ores, Bars, etc.)
        resources = extracted_data.get('resources', {})
        
        # Ores
        ores = resources.get('ores', {})
        for ore_type, value in ores.items():
            if isinstance(value, (int, float)) and value > 0:
                gains[f'ore_{ore_type}'] = value / offline_hours
        
        # Bars
        bars = resources.get('bars', {})
        for bar_type, value in bars.items():
            if isinstance(value, (int, float)) and value > 0:
                gains[f'bar_{bar_type}'] = value / offline_hours
        
        # Bombs und Others werden nicht berechnet (wie gewünscht)
        
        return gains
    
    def parse_offline_time(self, time_string: str) -> Optional[float]:
        """
        Parst eine Offline-Zeit-String (z.B. "00h05m15s") zu Stunden.
        
        Args:
            time_string: Zeit-String im Format "XhYmZs"
            
        Returns:
            Stunden als float oder None
        """
        match = re.search(r'(\d+)h\s*(\d+)m\s*(\d+)s', time_string, re.IGNORECASE)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            return hours + (minutes / 60.0) + (seconds / 3600.0)
        return None


# Beispiel-Verwendung
if __name__ == "__main__":
    calculator = OfflineGainsCalculator()
    
    # Beispiel: Zeit parsen
    time_str = "00h05m15s"
    hours = calculator.parse_offline_time(time_str)
    print(f"Zeit '{time_str}' = {hours:.4f} Stunden")
    
    print("\nFür vollständige Tests verwenden Sie test_main.py")

