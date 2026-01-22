# GUI Startmenü und Image-Bug Fixes - Dokumentation

## Übersicht
Diese Datei dokumentiert die Strategie für:
1. **GUI Startmenü** - Neues Menü beim Start statt direktes Öffnen von Gem EV
2. **Image-Bug Fixes** - Lösung für "image pyimageX doesn't exist" Fehler

---

## 1. GUI Startmenü (MainMenuWindow)

### Konzept
- Beim Start wird ein Menü-Fenster angezeigt statt direkt Gem EV zu öffnen
- Benutzer wählt aus: Gem EV, Archaeology, Event, Stargazing, Option Analyzer
- Nur EIN Fenster ist gleichzeitig offen

### Implementierung

#### Neue Klasse: `MainMenuWindow`
- Erstellt in `gui.py` vor `ObeliskGemEVGUI`
- Zeigt Buttons für alle Module
- Zentrales Fenster (600x500), zentriert

#### `main()` Funktion geändert:
```python
def main():
    root = tk.Tk()
    menu = MainMenuWindow(root)  # Statt direkt ObeliskGemEVGUI
    root.mainloop()
```

#### Zwei verschiedene Öffnungsstrategien:

**1. Gem EV (nutzt Root-Fenster direkt):**
```python
def open_gem_ev(self):
    # Destroy menu widgets
    for widget in self.root.winfo_children():
        widget.destroy()
    # Create Gem EV GUI in the same root window
    app = ObeliskGemEVGUI(self.root)
```

**2. Andere Module (Toplevel-Fenster):**
```python
def _open_toplevel_module(self, module_class, *args):
    # Create hidden_root für Toplevel
    hidden_root = tk.Tk()
    hidden_root.withdraw()
    
    # WICHTIG: hidden_root temporär sichtbar machen für Image-Loading
    hidden_root.deiconify()
    hidden_root.update_idletasks()
    
    # Module erstellen
    toplevel_window = module_class(hidden_root, *args)
    
    # Mehrfache Updates für vollständige Initialisierung
    for _ in range(5):
        hidden_root.update_idletasks()
        toplevel_window.window.update_idletasks()
        hidden_root.update()
        toplevel_window.window.update()
    
    # hidden_root wieder verstecken (Images sind bereits geladen)
    hidden_root.withdraw()
    
    # Menü minimieren (nicht zerstören - bleibt für Image-Referenzen)
    self.root.lower()
    self.root.state('iconic')  # Minimize
    
    # Cleanup beim Schließen
    def check_and_close():
        if not toplevel_window.window.winfo_exists():
            hidden_root.quit()
            hidden_root.destroy()
            self.root.quit()
            self.root.destroy()
    
    hidden_root.after(100, check_and_close)
    hidden_root.mainloop()
```

### Wichtige Punkte:
- **Gem EV**: Nutzt Root-Fenster direkt, ersetzt Menü-Inhalt
- **Andere Module**: Erstellen `hidden_root`, Menü wird minimiert (nicht zerstört)
- **Cleanup**: Automatisches Schließen von hidden_root und Menü wenn Toplevel geschlossen wird

---

## 2. Image-Bug Fixes

### Problem
Fehler: `image "pyimageX" doesn't exist` beim Öffnen von Archaeology, Event, Stargazing

### Ursache
- Images wurden ohne `master` Parameter erstellt
- Tkinter verknüpft Images mit dem Default-Root-Fenster
- Wenn Menü-Fenster versteckt/minimiert wird, können Images nicht richtig geladen werden

### Lösung: `master` Parameter verwenden

#### 1. In allen Modulen: Images mit `master=self.window` verknüpfen

**ArchaeologySimulatorWindow:**
```python
# Fragment Icons
self.fragment_icons[frag_type] = ImageTk.PhotoImage(icon_image, master=self.window)

# Block Icons
self.block_icons[block_type] = ImageTk.PhotoImage(icon_image, master=self.window)

# Gem Icon
self.gem_icon_photo = ImageTk.PhotoImage(gem_image, master=self.window)

# Icon für Window
icon_photo = ImageTk.PhotoImage(icon_image, master=self.window)
self.window.iconphoto(False, icon_photo)
self.icon_photo = icon_photo  # Als Instanzvariable speichern
```

**StargazingWindow:**
```python
# Alle Sprites
self.sprites[key] = ImageTk.PhotoImage(img, master=self.window)
self.sprites[f'star_{key}'] = ImageTk.PhotoImage(img, master=self.window)
```

**EventSimulatorWindow (BudgetOptimizerPanel):**
```python
# Currency Icons
self.currency_icons[tier] = ImageTk.PhotoImage(icon_image, master=self.window)

# Upgrade Icons
self.upgrade_icons[(tier, idx)] = ImageTk.PhotoImage(icon_image, master=self.window)
```

#### 2. In Tooltips: Images mit `master=tooltip` verknüpfen

**ArchaeologySimulatorWindow Tooltips:**
```python
# In _create_fragment_upgrade_tooltip und _create_arch_xp_tooltip
tooltip.icon_photo = ImageTk.PhotoImage(icon_image, master=tooltip)
```

### Wichtige Punkte:
- **ALLE** `ImageTk.PhotoImage()` Aufrufe müssen `master=` Parameter haben
- Für Modul-Fenster: `master=self.window`
- Für Tooltips: `master=tooltip` (Toplevel)
- Images als Instanzvariablen speichern (`self.icon_photo`, `self.sprites`, etc.)

---

## 3. Zusätzliches: ImageManager (optional)

Ein zentrales Image-Loading-System wurde in `ui_utils.py` erstellt, wurde aber nicht vollständig verwendet. Es könnte in Zukunft nützlich sein für:
- Zentrales Caching
- Unabhängiges Image-Loading
- Bessere Performance bei vielen Images

### ImageManager Klasse:
```python
class ImageManager:
    def load_image(self, relative_path, size=None, root=None):
        # Lädt und cached Images
        # Verknüpft mit root wenn angegeben
```

---

## Zusammenfassung der Strategie

### GUI Startmenü:
1. `MainMenuWindow` Klasse erstellen
2. `main()` zeigt Menü statt direkt Gem EV
3. Gem EV nutzt Root-Fenster direkt
4. Andere Module nutzen `hidden_root` (Toplevel)
5. Menü minimieren statt zerstören
6. Cleanup beim Schließen

### Image-Bug Fixes:
1. **ALLE** `ImageTk.PhotoImage()` Aufrufe mit `master=` Parameter
2. `master=self.window` für Modul-Images
3. `master=tooltip` für Tooltip-Images
4. Images als Instanzvariablen speichern
5. `hidden_root` temporär sichtbar machen während Image-Loading
6. Mehrfache `update_idletasks()` und `update()` Aufrufe

### Dateien die geändert wurden:
- `ObeliskGemEV/gui.py` - MainMenuWindow hinzugefügt
- `ObeliskGemEV/archaeology/simulator.py` - master Parameter für alle Images
- `ObeliskGemEV/stargazing/simulator.py` - master Parameter für alle Images
- `ObeliskGemEV/event/gui_budget.py` - master Parameter für alle Images
- `ObeliskGemEV/ui_utils.py` - ImageManager hinzugefügt (optional)
