"""
Modul 2: Image Extractor

Extrahiert Bildausschnitte aus Screenshots und speichert sie als PNG.
Dieses Modul ist unabhängig vom offline_gains_calculator Modul.
"""

from typing import List, Tuple, Union, Optional, Dict
from pathlib import Path
import re

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class ImageExtractor:
    """
    Extrahiert Bildausschnitte aus Screenshots.
    """
    
    def __init__(self, output_dir: Optional[Union[str, Path]] = None, debug: bool = False):
        """
        Initialisiert den Image Extractor.
        
        Args:
            output_dir: Optional - Ausgabe-Verzeichnis (Standard: output/extracted/)
            debug: Wenn True, werden Debug-Informationen ausgegeben
        """
        if output_dir is None:
            output_dir = Path("output/extracted")
        else:
            output_dir = Path(output_dir)
        
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.debug = debug
        self._easyocr_reader = None  # Wird bei Bedarf initialisiert
    
    def extract_region(
        self,
        image_path: Union[str, Path],
        x: int,
        y: int,
        width: int,
        height: int,
        output_path: Optional[Union[str, Path]] = None,
        output_name: Optional[str] = None
    ) -> str:
        """
        Extrahiert einen rechteckigen Bereich aus einem Bild und speichert ihn als PNG.
        
        Args:
            image_path: Pfad zum Quellbild (.jpg, .png, etc.)
            x: X-Koordinate der linken oberen Ecke
            y: Y-Koordinate der linken oberen Ecke
            width: Breite des Ausschnitts
            height: Höhe des Ausschnitts
            output_path: Optional - Vollständiger Pfad zur Ausgabedatei
            output_name: Optional - Name der Ausgabedatei (ohne Pfad)
            
        Returns:
            Pfad zur gespeicherten PNG-Datei
            
        Raises:
            FileNotFoundError: Wenn das Quellbild nicht existiert
            ValueError: Wenn die Koordinaten ungültig sind
        """
        if not PIL_AVAILABLE:
            raise ImportError(
                "PIL (Pillow) nicht verfügbar. Installieren Sie es mit: pip install Pillow"
            )
        
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Bild nicht gefunden: {image_path}")
        
        # Lade Bild
        image = Image.open(image_path)
        img_width, img_height = image.size
        
        # Validiere Koordinaten
        if x < 0 or y < 0:
            raise ValueError(f"Koordinaten müssen positiv sein (x={x}, y={y})")
        if x + width > img_width or y + height > img_height:
            raise ValueError(
                f"Ausschnitt geht über Bildgrenzen hinaus. "
                f"Bild: {img_width}x{img_height}, Ausschnitt: ({x},{y}) + {width}x{height}"
            )
        
        # Extrahiere Region
        region = image.crop((x, y, x + width, y + height))
        
        # Bestimme Ausgabe-Pfad
        if output_path:
            output_path = Path(output_path)
        elif output_name:
            output_path = self.output_dir / output_name
        else:
            # Generiere automatischen Namen
            stem = image_path.stem
            output_path = self.output_dir / f"{stem}_region_{x}_{y}_{width}x{height}.png"
        
        # Stelle sicher, dass die Datei .png Endung hat
        if output_path.suffix.lower() != '.png':
            output_path = output_path.with_suffix('.png')
        
        # Stelle sicher, dass das Verzeichnis existiert
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Speichere als PNG
        region.save(output_path, 'PNG')
        
        return str(output_path)
    
    def extract_multiple_regions(
        self,
        image_path: Union[str, Path],
        regions_config: List[Dict[str, Union[int, str]]]
    ) -> List[str]:
        """
        Extrahiert mehrere Regionen aus einem Bild.
        
        Args:
            image_path: Pfad zum Quellbild
            regions_config: Liste von Dictionaries mit:
                - 'x': int
                - 'y': int
                - 'width': int
                - 'height': int
                - 'name': str (optional) - Name der Ausgabedatei
                
        Returns:
            Liste von Pfaden zu den gespeicherten PNG-Dateien
        """
        output_paths = []
        
        for i, region_config in enumerate(regions_config):
            x = region_config['x']
            y = region_config['y']
            width = region_config['width']
            height = region_config['height']
            name = region_config.get('name')
            
            output_path = self.extract_region(
                image_path=image_path,
                x=x,
                y=y,
                width=width,
                height=height,
                output_name=name
            )
            output_paths.append(output_path)
        
        return output_paths
    
    def save_as_png(
        self,
        image: Image.Image,
        output_path: Union[str, Path],
        force: bool = False
    ) -> str:
        """
        Speichert ein PIL Image als PNG.
        
        Args:
            image: PIL Image-Objekt
            output_path: Pfad zur Ausgabedatei
            force: Wenn True, überschreibt existierende Dateien
            
        Returns:
            Pfad zur gespeicherten Datei
        """
        if not PIL_AVAILABLE:
            raise ImportError(
                "PIL (Pillow) nicht verfügbar. Installieren Sie es mit: pip install Pillow"
            )
        
        output_path = Path(output_path)
        
        # Stelle sicher, dass die Datei .png Endung hat
        if output_path.suffix.lower() != '.png':
            output_path = output_path.with_suffix('.png')
        
        # Prüfe, ob Datei existiert
        if output_path.exists() and not force:
            raise FileExistsError(
                f"Datei existiert bereits: {output_path}. "
                f"Verwenden Sie force=True zum Überschreiben."
            )
        
        # Stelle sicher, dass das Verzeichnis existiert
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Speichere als PNG
        image.save(output_path, 'PNG')
        
        return str(output_path)
    
    def detect_resource_icons(
        self,
        image_path: Union[str, Path],
        ores_bars_area_y: Optional[int] = None,
        search_height: int = 200,
        icon_size: Tuple[int, int] = (50, 50),
        min_icon_spacing: int = 10
    ) -> Dict:
        """
        Erkennt Icons/Sprites unterhalb der "Ores and Bars" Area.
        
        Args:
            image_path: Pfad zum Screenshot
            ores_bars_area_y: Optional - Y-Koordinate des "Ores and Bars" Texts (wird automatisch gefunden wenn None)
            search_height: Höhe des Suchbereichs unterhalb von "Ores and Bars" (in Pixeln)
            icon_size: Erwartete Größe der Icons (width, height)
            min_icon_spacing: Minimale Distanz zwischen Icons (in Pixeln)
            
        Returns:
            Dictionary mit:
            - 'success': bool
            - 'icons': Liste von Dictionaries mit:
                - 'index': int (0, 1, 2, 3 für die 4 Icons)
                - 'x': int (X-Koordinate)
                - 'y': int (Y-Koordinate)
                - 'width': int
                - 'height': int
                - 'image_path': str (Pfad zum extrahierten Icon)
            - 'search_area': Dict mit Koordinaten des Suchbereichs
        """
        if not PIL_AVAILABLE:
            return {
                'success': False,
                'error': 'PIL (Pillow) nicht verfügbar'
            }
        
        image_path = Path(image_path)
        if not image_path.exists():
            return {
                'success': False,
                'error': f'Bild nicht gefunden: {image_path}'
            }
        
        try:
            # Lade Bild
            image = Image.open(image_path)
            img_width, img_height = image.size
            
            # Finde "Ores and Bars" Position (falls nicht gegeben)
            if ores_bars_area_y is None:
                ores_bars_y = self._find_ores_bars_position(image)
                if ores_bars_y is None:
                    # Fallback: Verwende geschätzte Position basierend auf Bildgröße
                    # Typischerweise ist "Ores and Bars" im oberen bis mittleren Bereich
                    estimated_y = int(img_height * 0.3)  # 30% von oben
                    if self.debug:
                        print(f"   Verwende geschaetzte Y-Position: {estimated_y}")
                    ores_bars_y = estimated_y
            else:
                ores_bars_y = ores_bars_area_y
            
            # Finde "Bombs and Others" Position als obere Grenze
            bombs_others_y = self._find_bombs_others_position(image)
            if bombs_others_y is None:
                # Fallback: Verwende search_height wenn "Bombs and Others" nicht gefunden
                bombs_others_y = ores_bars_y + search_height
                if self.debug:
                    print(f"   'Bombs and Others' nicht gefunden, verwende geschaetzte Grenze: {bombs_others_y}")
            else:
                if self.debug:
                    print(f"   'Bombs and Others' gefunden bei Y={bombs_others_y}")
            
            # Definiere Suchbereich zwischen "Ores and Bars" und "Bombs and Others"
            # Starte direkt unter "Ores and Bars" Text (ca. 20-30px Abstand)
            search_y = ores_bars_y + 25  # Weniger Abstand, um direkt die Icons zu finden
            search_x = 0
            search_w = img_width
            
            # Suchbereich endet bei "Bombs and Others" (mit Puffer nach oben)
            # Wichtig: "Bombs and Others" wird dynamisch gefunden basierend auf dem Text
            if bombs_others_y is not None and bombs_others_y > search_y:
                # Berechne Höhe: von search_y bis kurz vor "Bombs and Others"
                search_h = bombs_others_y - search_y - 15  # 15px Puffer vor "Bombs and Others"
            else:
                # Falls "Bombs and Others" nicht gefunden, verwende einen kleinen Suchbereich
                # (Icons sollten direkt unter "Ores and Bars" sein)
                search_h = 60  # Nur ca. 60px direkt unter "Ores and Bars"
                if self.debug:
                    print(f"   'Bombs and Others' nicht gefunden, verwende kleinen Suchbereich: {search_h}px")
            
            # Stelle sicher, dass der Suchbereich nicht zu klein ist
            if search_h < 40:
                search_h = 40  # Mindestens 40px
            
            # Stelle sicher, dass wir nicht über Bildgrenzen hinausgehen
            if search_y + search_h > img_height:
                search_h = img_height - search_y
            
            if self.debug:
                print(f"   Suche Icons in Bereich: ({search_x}, {search_y}) - {search_w}x{search_h}")
            
            # Extrahiere Suchbereich
            search_region = image.crop((search_x, search_y, search_x + search_w, search_y + search_h))
            
            # Erkenne Icons im Suchbereich
            icons = self._detect_icons_in_region(
                search_region,
                icon_size=icon_size,
                min_spacing=min_icon_spacing
            )
            
            # Konvertiere relative Koordinaten zu absoluten Koordinaten
            for icon in icons:
                icon['x'] += search_x
                icon['y'] += search_y
            
            # Extrahiere Icons als separate Bilder
            icon_images = []
            for i, icon in enumerate(icons):
                icon_img = image.crop((
                    icon['x'],
                    icon['y'],
                    icon['x'] + icon['width'],
                    icon['y'] + icon['height']
                ))
                
                # Speichere Icon
                icon_filename = f"{image_path.stem}_icon_{i}.png"
                icon_path = self.output_dir / icon_filename
                icon_img.save(icon_path, 'PNG')
                icon['image_path'] = str(icon_path)
                icon_images.append(icon_img)
            
            if self.debug:
                print(f"   {len(icons)} Icons gefunden")
                for icon in icons:
                    print(f"      Icon {icon['index']}: ({icon['x']}, {icon['y']}) - {icon['width']}x{icon['height']}")
            
            return {
                'success': True,
                'icons': icons,
                'search_area': {
                    'x': search_x,
                    'y': search_y,
                    'width': search_w,
                    'height': search_h
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Fehler beim Erkennen der Icons: {str(e)}'
            }
    
    def _find_ores_bars_position(self, image: Image.Image) -> Optional[int]:
        """
        Findet die Y-Position des "Ores and Bars" Texts im Bild.
        
        Args:
            image: PIL Image-Objekt
            
        Returns:
            Y-Koordinate oder None wenn nicht gefunden
        """
        if not OCR_AVAILABLE:
            # Fallback: Verwende geschätzte Position (muss angepasst werden)
            return 300  # Beispiel-Wert
        
        try:
            # Initialisiere EasyOCR Reader
            if self._easyocr_reader is None:
                if self.debug:
                    print("   Initialisiere EasyOCR Reader...")
                self._easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            
            # Konvertiere zu NumPy Array
            img_array = np.array(image.convert('RGB'))
            
            # Führe OCR durch
            results = self._easyocr_reader.readtext(
                img_array,
                paragraph=False,
                detail=1
            )
            
            # Suche nach "Ores and Bars" oder ähnlichen Texten
            ores_bars_patterns = [
                r'ores\s+and\s+bars',
                r'oces\s+bars',
                r'o[re]{2,3}s\s+(?:and\s+)?bars?'
            ]
            
            # Strategie 1: Suche nach vollständigem Text
            for result in results:
                if len(result) >= 3:
                    bbox, text, conf = result[0], result[1], result[2]
                    text_lower = text.lower()
                    
                    # Prüfe, ob Text zu "Ores and Bars" passt
                    for pattern in ores_bars_patterns:
                        if re.search(pattern, text_lower):
                            # Berechne Y-Koordinate aus Bounding Box
                            # bbox ist eine Liste von 4 Punkten [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                            if bbox and len(bbox) >= 2:
                                y_coords = [point[1] for point in bbox]
                                y_position = int(min(y_coords))
                                if self.debug:
                                    print(f"   'Ores and Bars' gefunden bei Y={y_position} (Text: '{text}')")
                                return y_position
            
            # Strategie 2: Suche nach einzelnen Wörtern "Ores"/"Oces" und "Bars" in der Nähe
            ores_texts = []
            bars_texts = []
            
            for result in results:
                if len(result) >= 3:
                    bbox, text, conf = result[0], result[1], result[2]
                    text_lower = text.lower().strip()
                    
                    # Suche nach "Ores" oder "Oces"
                    if re.search(r'o[re]{2,3}s', text_lower) or text_lower in ['oces', 'ores']:
                        if bbox and len(bbox) >= 2:
                            y_coords = [point[1] for point in bbox]
                            y_pos = int(min(y_coords))
                            ores_texts.append((y_pos, text, bbox))
                    
                    # Suche nach "Bars"
                    if re.search(r'bars?', text_lower) and 'bars' in text_lower:
                        if bbox and len(bbox) >= 2:
                            y_coords = [point[1] for point in bbox]
                            y_pos = int(min(y_coords))
                            bars_texts.append((y_pos, text, bbox))
            
            # Wenn beide gefunden wurden, verwende die Position von "Bars" (ist weiter rechts/unten)
            if ores_texts and bars_texts:
                # Nimm die niedrigste Y-Position (höchste im Bild)
                all_y_positions = [y for y, _, _ in ores_texts] + [y for y, _, _ in bars_texts]
                y_position = min(all_y_positions)
                if self.debug:
                    print(f"   'Ores and Bars' gefunden via kombinierte Suche bei Y={y_position}")
                return y_position
            
            if self.debug:
                print("   'Ores and Bars' nicht gefunden via OCR")
            return None
            
        except Exception as e:
            if self.debug:
                print(f"   Fehler bei OCR-Suche: {e}")
            return None
    
    def _find_bombs_others_position(self, image: Image.Image) -> Optional[int]:
        """
        Findet die Y-Position des "Bombs and Others" Texts im Bild.
        
        Args:
            image: PIL Image-Objekt
            
        Returns:
            Y-Koordinate oder None wenn nicht gefunden
        """
        if not OCR_AVAILABLE:
            return None
        
        try:
            # Initialisiere EasyOCR Reader (falls noch nicht geschehen)
            if self._easyocr_reader is None:
                if self.debug:
                    print("   Initialisiere EasyOCR Reader...")
                self._easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            
            # Konvertiere zu NumPy Array
            img_array = np.array(image.convert('RGB'))
            
            # Führe OCR durch
            results = self._easyocr_reader.readtext(
                img_array,
                paragraph=False,
                detail=1
            )
            
            # Suche nach "Bombs and Others" oder ähnlichen Texten
            bombs_patterns = [
                r'bombs\s+and\s+others',
                r'bombs\s+and\s+other',
                r'bomb\s+and\s+others?'
            ]
            
            # Strategie 1: Suche nach vollständigem Text
            for result in results:
                if len(result) >= 3:
                    bbox, text, conf = result[0], result[1], result[2]
                    text_lower = text.lower()
                    
                    # Prüfe, ob Text zu "Bombs and Others" passt
                    for pattern in bombs_patterns:
                        if re.search(pattern, text_lower):
                            if bbox and len(bbox) >= 2:
                                y_coords = [point[1] for point in bbox]
                                y_position = int(min(y_coords))
                                if self.debug:
                                    print(f"   'Bombs and Others' gefunden bei Y={y_position} (Text: '{text}')")
                                return y_position
            
            # Strategie 2: Suche nach einzelnen Wörtern "Bombs" und "Others"
            bombs_texts = []
            others_texts = []
            
            for result in results:
                if len(result) >= 3:
                    bbox, text, conf = result[0], result[1], result[2]
                    text_lower = text.lower().strip()
                    
                    # Suche nach "Bombs" oder "Bomb"
                    if re.search(r'bombs?', text_lower) and 'bomb' in text_lower:
                        if bbox and len(bbox) >= 2:
                            y_coords = [point[1] for point in bbox]
                            y_pos = int(min(y_coords))
                            bombs_texts.append((y_pos, text, bbox))
                    
                    # Suche nach "Others" oder "Other"
                    if re.search(r'others?', text_lower) and 'other' in text_lower:
                        if bbox and len(bbox) >= 2:
                            y_coords = [point[1] for point in bbox]
                            y_pos = int(min(y_coords))
                            others_texts.append((y_pos, text, bbox))
            
            # Wenn beide gefunden wurden, verwende die Position von "Others" (ist weiter rechts/unten)
            if bombs_texts and others_texts:
                # Nimm die niedrigste Y-Position (höchste im Bild)
                all_y_positions = [y for y, _, _ in bombs_texts] + [y for y, _, _ in others_texts]
                y_position = min(all_y_positions)
                if self.debug:
                    print(f"   'Bombs and Others' gefunden via kombinierte Suche bei Y={y_position}")
                return y_position
            
            return None
            
        except Exception as e:
            if self.debug:
                print(f"   Fehler bei OCR-Suche nach 'Bombs and Others': {e}")
            return None
    
    def _detect_icons_in_region(
        self,
        region: Image.Image,
        icon_size: Tuple[int, int],
        min_spacing: int = 10
    ) -> List[Dict]:
        """
        Erkennt Icons/Sprites in einer Bildregion.
        
        Strategie:
        1. Konvertiere zu Graustufen
        2. Finde wiederkehrende Muster (Template Matching oder Clustering)
        3. Gruppiere ähnliche Bereiche als Icons
        
        Args:
            region: PIL Image-Objekt (Suchbereich)
            icon_size: Erwartete Größe der Icons (width, height)
            min_spacing: Minimale Distanz zwischen Icons
            
        Returns:
            Liste von Icon-Dictionaries mit Positionen
        """
        icons = []
        
        if CV2_AVAILABLE:
            # Verwende OpenCV für bessere Icon-Erkennung
            icons = self._detect_icons_opencv(region, icon_size, min_spacing)
        else:
            # Fallback: Einfache Erkennung durch Suche nach wiederkehrenden Mustern
            icons = self._detect_icons_simple(region, icon_size, min_spacing)
        
        # Filtere Icons: Nur die, die horizontal in einer Reihe sind
        # Bei "Ores and Bars" sind Icons in einer horizontalen Reihe, nicht vertikal gestapelt
        # WICHTIG: Die Icons sollten direkt unter "Ores and Bars" sein (oberste Reihe im Suchbereich)
        
        if len(icons) > 0:
            # Gruppiere Icons nach Y-Koordinate (ähnliche Y = gleiche Reihe)
            icons_by_y = {}
            for icon in icons:
                # Runde Y auf nächste 5er-Stelle für Gruppierung (genauer)
                y_group = round(icon['y'] / 5) * 5
                if y_group not in icons_by_y:
                    icons_by_y[y_group] = []
                icons_by_y[y_group].append(icon)
            
            # Finde die oberste Gruppe (kleinste Y-Koordinate) - das sind die Icons direkt unter "Ores and Bars"
            if icons_by_y:
                # Sortiere Gruppen nach Y-Koordinate (oberste zuerst)
                sorted_groups = sorted(icons_by_y.items(), key=lambda x: x[0])
                
                # Nimm die oberste Gruppe, die mindestens 2 Icons hat
                for y_group, group_icons in sorted_groups:
                    if len(group_icons) >= 2:
                        icons = group_icons
                        if self.debug:
                            print(f"   Oberste Icon-Reihe gefunden bei Y={y_group} mit {len(icons)} Icons")
                        break
                else:
                    # Falls keine Gruppe mit mindestens 2 Icons, nimm die oberste
                    if sorted_groups:
                        icons = sorted_groups[0][1]
        
        # Sortiere Icons von links nach rechts
        icons.sort(key=lambda i: i['x'])
        
        # Begrenze auf maximal 4 Icons (red_ore, red_bar, purple_ore, purple_bar)
        icons = icons[:4]
        
        # Weise Indizes zu
        for i, icon in enumerate(icons):
            icon['index'] = i
        
        return icons
    
    def _detect_icons_opencv(
        self,
        region: Image.Image,
        icon_size: Tuple[int, int],
        min_spacing: int
    ) -> List[Dict]:
        """
        Erkennt Icons mit OpenCV Template Matching.
        """
        icons = []
        
        try:
            # Konvertiere zu NumPy Array
            img_array = np.array(region.convert('RGB'))
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Verwende Template Matching mit dem ersten gefundenen Icon als Template
            # Oder verwende Feature Detection
            
            # Ansatz 1: Suche nach rechteckigen Bereichen mit ähnlicher Größe
            # Verwende Canny Edge Detection und finde Konturen
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filtere Konturen nach Größe (ungefähr icon_size)
            icon_width, icon_height = icon_size
            tolerance = 0.3  # 30% Toleranz
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Prüfe, ob Größe ungefähr icon_size entspricht
                width_ok = abs(w - icon_width) / icon_width <= tolerance
                height_ok = abs(h - icon_height) / icon_height <= tolerance
                
                if width_ok and height_ok and w > 20 and h > 20:
                    # Prüfe, ob nicht zu nah an bereits gefundenen Icons
                    too_close = False
                    for existing_icon in icons:
                        dist = ((x - existing_icon['x'])**2 + (y - existing_icon['y'])**2)**0.5
                        if dist < min_spacing:
                            too_close = True
                            break
                    
                    if not too_close:
                        icons.append({
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h
                        })
            
            # Wenn nicht genug Icons gefunden, versuche alternativen Ansatz
            if len(icons) < 4:
                # Ansatz 2: Suche nach horizontalen Mustern (Icons sind meist in einer Reihe)
                # Finde Bereiche mit hoher Varianz (Icons haben mehr Details als Hintergrund)
                block_size = min(icon_width, icon_height)
                step = block_size // 2
                
                candidates = []
                for y in range(0, gray.shape[0] - block_size, step):
                    for x in range(0, gray.shape[1] - block_size, step):
                        block = gray[y:y+block_size, x:x+block_size]
                        variance = np.var(block)
                        
                        # Icons haben typischerweise höhere Varianz als Hintergrund
                        if variance > 500:  # Schwellenwert anpassbar
                            candidates.append({
                                'x': x,
                                'y': y,
                                'width': block_size,
                                'height': block_size,
                                'variance': variance
                            })
                
                # Gruppiere Kandidaten nach Position (entferne Duplikate)
                if candidates:
                    # Sortiere nach Varianz (höhere = wahrscheinlicher Icon)
                    candidates.sort(key=lambda c: c['variance'], reverse=True)
                    
                    # Nimm die besten Kandidaten, die nicht zu nah beieinander sind
                    for candidate in candidates:
                        too_close = False
                        for existing_icon in icons:
                            dist = ((candidate['x'] - existing_icon['x'])**2 + 
                                   (candidate['y'] - existing_icon['y'])**2)**0.5
                            if dist < min_spacing:
                                too_close = True
                                break
                        
                        if not too_close:
                            icons.append({
                                'x': candidate['x'],
                                'y': candidate['y'],
                                'width': candidate['width'],
                                'height': candidate['height']
                            })
                            
                            if len(icons) >= 8:  # Erwarte max 4, aber sammle mehr für Filterung
                                break
            
        except Exception as e:
            if self.debug:
                print(f"   Fehler bei OpenCV Icon-Erkennung: {e}")
        
        return icons
    
    def _detect_icons_simple(
        self,
        region: Image.Image,
        icon_size: Tuple[int, int],
        min_spacing: int
    ) -> List[Dict]:
        """
        Einfache Icon-Erkennung ohne OpenCV (Fallback).
        """
        icons = []
        
        try:
            # Konvertiere zu Graustufen
            gray = region.convert('L')
            img_array = np.array(gray)
            
            icon_width, icon_height = icon_size
            
            # Suche nach Bereichen mit hoher Varianz (Icons haben mehr Details)
            block_size = min(icon_width, icon_height)
            step = block_size // 2
            
            candidates = []
            for y in range(0, img_array.shape[0] - block_size, step):
                for x in range(0, img_array.shape[1] - block_size, step):
                    block = img_array[y:y+block_size, x:x+block_size]
                    variance = np.var(block)
                    
                    if variance > 500:  # Schwellenwert
                        candidates.append({
                            'x': x,
                            'y': y,
                            'width': block_size,
                            'height': block_size,
                            'variance': variance
                        })
            
            # Sortiere nach Varianz und nimm die besten
            candidates.sort(key=lambda c: c['variance'], reverse=True)
            
            for candidate in candidates:
                too_close = False
                for existing_icon in icons:
                    dist = ((candidate['x'] - existing_icon['x'])**2 + 
                           (candidate['y'] - existing_icon['y'])**2)**0.5
                    if dist < min_spacing:
                        too_close = True
                        break
                
                if not too_close:
                    icons.append({
                        'x': candidate['x'],
                        'y': candidate['y'],
                        'width': candidate['width'],
                        'height': candidate['height']
                    })
                    
                    if len(icons) >= 8:  # Erwarte max 4, aber sammle mehr für Filterung
                        break
        
        except Exception as e:
            if self.debug:
                print(f"   Fehler bei einfacher Icon-Erkennung: {e}")
        
        return icons
    
    def assign_numbers_to_icons(
        self,
        icons: List[Dict],
        numbers: List[Union[int, float]]
    ) -> Dict[int, Union[int, float]]:
        """
        Ordnet Zahlen den Icons zu.
        
        Args:
            icons: Liste von Icon-Dictionaries (von detect_resource_icons)
            numbers: Liste von Zahlen (vom gains calculator)
                Erwartete Reihenfolge: [red_ore, red_bar, purple_ore, purple_bar]
                Oder: [red_ore, purple_ore] wenn nur 2 Zahlen
        
        Returns:
            Dictionary: {icon_index: number}
        """
        assignment = {}
        
        # Sortiere Icons von links nach rechts (sollte bereits sortiert sein)
        sorted_icons = sorted(icons, key=lambda i: i.get('x', 0))
        
        # Ordne Zahlen den Icons zu (von links nach rechts)
        for i, icon in enumerate(sorted_icons):
            icon_idx = icon.get('index', i)
            if i < len(numbers):
                assignment[icon_idx] = numbers[i]
            else:
                assignment[icon_idx] = None
        
        if self.debug:
            print(f"   Zahlen zu Icons zugeordnet:")
            for icon_idx, number in assignment.items():
                print(f"      Icon {icon_idx}: {number}")
        
        return assignment
    
    def extract_and_assign_resources(
        self,
        image_path: Union[str, Path],
        gains_data: Dict
    ) -> Dict:
        """
        Kombiniert Icon-Erkennung mit Zahlen-Zuordnung aus Gains Calculator.
        
        Args:
            image_path: Pfad zum Screenshot
            gains_data: Dictionary vom OfflineGainsCalculator mit 'raw_data' oder 'gains_per_hour'
                Erwartet: gains_data['raw_data']['resources']['ores'] und ['bars']
        
        Returns:
            Dictionary mit:
            - 'success': bool
            - 'icons': Liste von Icons
            - 'assignment': Dictionary {icon_index: number}
            - 'resource_mapping': Dictionary mit Zuordnung zu Resource-Typen
        """
        # Erkenne Icons
        icon_result = self.detect_resource_icons(image_path)
        
        if not icon_result['success']:
            return {
                'success': False,
                'error': icon_result.get('error', 'Icon-Erkennung fehlgeschlagen')
            }
        
        icons = icon_result['icons']
        
        # Extrahiere Zahlen aus gains_data
        numbers = []
        resource_types = []
        
        # Versuche, Zahlen aus raw_data zu extrahieren
        raw_data = gains_data.get('raw_data', {})
        resources = raw_data.get('resources', {})
        
        ores = resources.get('ores', {})
        bars = resources.get('bars', {})
        
        # Erwartete Reihenfolge: red_ore, red_bar, purple_ore, purple_bar
        if 'red' in ores:
            numbers.append(ores['red'])
            resource_types.append('red_ore')
        if 'red' in bars:
            numbers.append(bars['red'])
            resource_types.append('red_bar')
        if 'purple' in ores:
            numbers.append(ores['purple'])
            resource_types.append('purple_ore')
        if 'purple' in bars:
            numbers.append(bars['purple'])
            resource_types.append('purple_bar')
        
        # Ordne Zahlen zu
        assignment = self.assign_numbers_to_icons(icons, numbers)
        
        # Erstelle Resource-Mapping
        resource_mapping = {}
        sorted_icons = sorted(icons, key=lambda i: i.get('x', 0))
        for i, icon in enumerate(sorted_icons):
            icon_idx = icon.get('index', i)
            if i < len(resource_types):
                resource_mapping[icon_idx] = {
                    'type': resource_types[i],
                    'value': assignment.get(icon_idx)
                }
        
        return {
            'success': True,
            'icons': icons,
            'assignment': assignment,
            'resource_mapping': resource_mapping
        }


# Beispiel-Verwendung
if __name__ == "__main__":
    extractor = ImageExtractor(debug=True)
    
    print("Image Extractor Modul")
    print("=" * 50)
    print("\nVerwendung:")
    print("  extractor = ImageExtractor()")
    print("  output_path = extractor.extract_region(")
    print("      image_path='screenshot.jpg',")
    print("      x=100, y=200, width=300, height=150,")
    print("      output_name='extracted_region.png'")
    print("  )")
    print("\nIcon-Erkennung:")
    print("  result = extractor.detect_resource_icons(")
    print("      image_path='screenshot.jpg'")
    print("  )")
    print("  if result['success']:")
    print("      icons = result['icons']")
    print("      # Ordne Zahlen zu (vom gains calculator):")
    print("      numbers = [34100, 2, 34100, 2]  # red_ore, red_bar, purple_ore, purple_bar")
    print("      assignment = extractor.assign_numbers_to_icons(icons, numbers)")
    print("\nFür vollständige Tests verwenden Sie test_main.py")

