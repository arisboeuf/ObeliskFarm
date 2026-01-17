"""
GUI für ObeliskGemEV Calculator
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path

# Matplotlib für Bar Chart
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Füge das Modul-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from freebie_ev_calculator import FreebieEVCalculator, GameParameters


class ObeliskGemEVGUI:
    """GUI für den ObeliskGemEV Calculator"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ObeliskGemEV Calculator")
        self.root.geometry("1600x900")
        self.root.resizable(True, True)
        
        # Flag für Live-Updates
        self.auto_calculate_enabled = True
        self.calculation_pending = False
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Dezent farbliche Trennung für verschiedene Bereiche
        # Freebie-Bereich: sehr helles Blau
        style.configure('Freebie.TLabelframe.Label', foreground='#2E5F8F')
        # Founder-Bereich: sehr helles Grün
        style.configure('Founder.TLabelframe.Label', foreground='#5F8F2E')
        # Bomb-Bereich: sehr helles Rot
        style.configure('Bomb.TLabelframe.Label', foreground='#8F5F2E')
        
        # Variablen für Eingabefelder
        self.vars = {}
        
        # Matplotlib Figure für Chart
        self.fig = None
        self.canvas = None
        
        # Erstelle GUI
        self.create_widgets()
        
        # Lade Standard-Werte
        self.load_defaults()
        
        # Initiale Berechnung
        self.root.after(100, self.calculate)
    
    def create_widgets(self):
        """Erstellt alle GUI-Widgets"""
        
        # Hauptcontainer - zwei Spalten
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        # Linke Spalte (Parameter) schmaler, rechte Spalte (Ergebnisse) breiter
        main_frame.columnconfigure(0, weight=1, minsize=350)
        main_frame.columnconfigure(1, weight=3, minsize=700)
        main_frame.rowconfigure(0, weight=1)
        
        # Titel über beide Spalten
        title_label = ttk.Label(
            main_frame,
            text="ObeliskGemEV Calculator",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Linke Spalte: Parameter
        self.create_parameter_section(main_frame)
        
        # Rechte Spalte: Ergebnisse + Chart
        self.create_result_section(main_frame)
    
    def create_parameter_section(self, parent):
        """Erstellt die Parameter-Eingabefelder (links)"""
        
        # Frame für Parameter mit Scrollbar
        param_container = ttk.Frame(parent)
        param_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        param_container.columnconfigure(0, weight=1)
        param_container.rowconfigure(0, weight=1)
        
        # Canvas für Scrollbar
        canvas = tk.Canvas(param_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(param_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Container für alle Parameter-Bereiche
        param_container = ttk.Frame(scrollable_frame)
        param_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # ============================================
        # FREEBIE BEREICH
        # ============================================
        freebie_header_frame = ttk.Frame(scrollable_frame)
        freebie_header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        freebie_label = ttk.Label(freebie_header_frame, text="🎁 FREEBIE", font=("Arial", 10, "bold"))
        freebie_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        freebie_help_label = tk.Label(freebie_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray")
        freebie_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        freebie_frame = ttk.LabelFrame(scrollable_frame, padding="10", style='Freebie.TLabelframe')
        freebie_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        freebie_frame.columnconfigure(1, weight=1)
        
        # Tooltip für Freebie-Info
        freebie_info = (
            "FREEBIE Parameter:\n"
            "• Freebie Gems (Basis): Fix 9.0\n"
            "• Freebie Timer: 7.0 Minuten\n"
            "• Skill Shards: 12% Chance, 12.5 Gems Wert\n"
            "• Stonks: 1% Chance, 200 Gems Bonus (wenn aktiviert)\n"
            "• Jackpot: 5% Chance auf 5 zusätzliche Rolls\n"
            "• Refresh: 5% Chance auf sofortiges Refresh"
        )
        self.create_tooltip(freebie_help_label, freebie_info)
        
        row = 0
        
        # Basis-Parameter
        ttk.Label(freebie_frame, text="Basis:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(freebie_frame, "freebie_gems_base", "  Freebie Gems (Basis):", row, "9.0")
        row += 1
        
        self.create_entry(freebie_frame, "freebie_timer_minutes", "  Freebie Timer (Minuten):", row, "7.0")
        row += 1
        
        # Separator
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8
        )
        row += 1
        
        # Skill Shards (Freebie)
        ttk.Label(freebie_frame, text="Skill Shards (Freebie):", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(freebie_frame, "skill_shard_chance", "  Skill Shard Chance (%):", row, "12.0", is_percent=True)
        row += 1
        
        self.create_entry(freebie_frame, "skill_shard_value_gems", "  Skill Shard Wert (Gems):", row, "12.5")
        row += 1
        
        # Separator
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8
        )
        row += 1
        
        # Stonks (Freebie) - Checkbox statt Entry-Felder
        stonks_var = tk.BooleanVar(value=True)  # Default: aktiviert
        self.stonks_enabled = stonks_var
        stonks_checkbox = ttk.Checkbutton(
            freebie_frame,
            text="Stonks aktiviert (1% Chance, 200 Gems Bonus)",
            variable=stonks_var,
            command=self.trigger_auto_calculate
        )
        stonks_checkbox.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=3)
        row += 1
        
        # Separator
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8
        )
        row += 1
        
        # Jackpot (Freebie)
        ttk.Label(freebie_frame, text="Jackpot (Freebie):", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(freebie_frame, "jackpot_chance", "  Jackpot Chance (%):", row, "5.0", is_percent=True)
        row += 1
        
        self.create_entry(freebie_frame, "jackpot_rolls", "  Jackpot Rolls:", row, "5", is_int=True)
        row += 1
        
        # Separator
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8
        )
        row += 1
        
        # Refresh (Freebie)
        ttk.Label(freebie_frame, text="Refresh (Freebie):", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(freebie_frame, "instant_refresh_chance", "  Instant Refresh Chance (%):", row, "5.0", is_percent=True)
        
        # ============================================
        # FOUNDER SUPPLY DROP BEREICH
        # ============================================
        founder_header_frame = ttk.Frame(scrollable_frame)
        founder_header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        founder_label = ttk.Label(founder_header_frame, text="📦 FOUNDER SUPPLY DROP", font=("Arial", 10, "bold"))
        founder_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        founder_help_label = tk.Label(founder_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray")
        founder_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        founder_frame = ttk.LabelFrame(scrollable_frame, padding="10", style='Founder.TLabelframe')
        founder_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        founder_frame.columnconfigure(1, weight=1)
        
        # Tooltip für Founder Supply Drop Info
        founder_info = (
            "FOUNDER SUPPLY DROP:\n"
            "• VIP Lounge Level: Bestimmt Drop-Intervall und Double/Triple Chance\n"
            "  - Intervall: 60 - 2×(Level-1) Minuten\n"
            "  - Double Chance: 12% bei Level 2, +6% pro Level\n"
            "  - Triple Chance: 16% bei Level 7\n"
            "• Founder Gems Base: Fix 10 Gems pro Drop\n"
            "• Founder Speed: 2× Speed für 5 Minuten pro Drop\n"
            "  (spart Zeit → mehr Freebies → Gem-Äquivalent)\n"
            "• 1/1234 Chance: 10 Gifts pro Supply Drop\n"
            "• Obelisk Level: Wird für Bonus-Gems verwendet"
        )
        self.create_tooltip(founder_help_label, founder_info)
        
        row = 0
        
        self.create_entry(founder_frame, "vip_lounge_level", "VIP Lounge Level (1-7):", row, "2", is_int=True)
        row += 1
        
        self.create_entry(founder_frame, "obelisk_level", "Obelisk Level:", row, "26", is_int=True)
        
        # ============================================
        # FOUNDER BOMB BEREICH
        # ============================================
        bomb_frame = ttk.LabelFrame(scrollable_frame, text="💣 FOUNDER BOMB", padding="10", style='Bomb.TLabelframe')
        bomb_frame.pack(fill=tk.X, padx=5, pady=5)
        bomb_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        self.create_entry(bomb_frame, "founder_bomb_interval_seconds", "Founder Bomb Intervall (Sekunden):", row, "87.0")
        row += 1
        
        # Separator
        ttk.Separator(bomb_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8
        )
        row += 1
        
        ttk.Label(bomb_frame, text="Bomb Speed:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(bomb_frame, "founder_bomb_speed_chance", "  Speed Chance (%):", row, "10.0", is_percent=True)
        row += 1
        
        self.create_entry(bomb_frame, "founder_bomb_speed_multiplier", "  Speed Multiplikator:", row, "2.0")
        row += 1
        
        self.create_entry(bomb_frame, "founder_bomb_speed_duration_seconds", "  Speed Dauer (Sekunden):", row, "10.0")
    
    def create_tooltip(self, widget, text):
        """Erstellt einen Tooltip, der erscheint, wenn man über ein Widget hovert"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(
                tooltip,
                text=text,
                background="#ffffe0",
                relief="solid",
                borderwidth=1,
                font=("Arial", 8),
                justify=tk.LEFT,
                padx=5,
                pady=3
            )
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def create_dynamic_gift_tooltip(self, widget):
        """Erstellt einen dynamischen Tooltip für Gift-EV mit Contributions"""
        def on_enter(event):
            # Basis-Info
            base_info = (
                "GIFT-EV Berechnung:\n"
                "• Basis-Roll: Gems (20-40, 30-65), Skill Shards, Blue Cow, 2× Speed\n"
                "• Rare Roll: 1/45 Chance auf 80-130 Gems\n"
                "• Rekursive Gifts: 1/40 Chance auf 3 zusätzliche Gifts\n"
                "• Multiplikatoren: Obelisk × Lucky Multiplier\n"
                "• Alle Werte werden in Gem-Äquivalent umgerechnet\n"
                "\n"
                "Contributions (aktuelle Werte):\n"
            )
            
            # Contributions aus den Labels holen (falls bereits berechnet)
            contrib_text = ""
            if hasattr(self, 'gift_contrib_labels'):
                for key, label in self.gift_contrib_labels.items():
                    value = label.cget('text')
                    if value and value != "" and value != "—":
                        # Extrahiere nur den Wert (ohne "Gems" etc.)
                        contrib_text += f"• {self._get_contrib_label(key)}: {value}\n"
            
            if not contrib_text:
                contrib_text = "(Werte werden nach Berechnung angezeigt)\n"
            
            full_text = base_info + contrib_text
            
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(
                tooltip,
                text=full_text,
                background="#ffffe0",
                relief="solid",
                borderwidth=1,
                font=("Arial", 8),
                justify=tk.LEFT,
                padx=5,
                pady=3
            )
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _get_contrib_label(self, key):
        """Gibt das Label für einen Contribution-Key zurück"""
        labels = {
            'gems_20_40': 'Gems (20-40)',
            'gems_30_65': 'Gems (30-65)',
            'skill_shards': 'Skill Shards',
            'blue_cow': 'Blue Cow',
            'speed_boost': '2× Speed Boost',
            'rare_gems': 'Rare Roll Gems',
            'recursive_gifts': 'Rekursive Gifts'
        }
        return labels.get(key, key)
    
    def create_entry(self, parent, var_name, label_text, row, default_value, is_percent=False, is_int=False):
        """Erstellt ein Eingabefeld mit Label"""
        
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        var = tk.StringVar(value=default_value)
        self.vars[var_name] = {'var': var, 'is_percent': is_percent, 'is_int': is_int}
        
        entry = ttk.Entry(parent, textvariable=var, width=20)
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        
        # Live-Update: Berechne automatisch bei Änderung (mit Delay)
        var.trace_add('write', lambda *args: self.trigger_auto_calculate())
    
    def create_result_section(self, parent):
        """Erstellt die Ergebnis-Anzeige (rechts)"""
        
        # Frame für Ergebnisse
        result_frame = ttk.LabelFrame(parent, text="Ergebnisse", padding="10")
        result_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)
        result_frame.rowconfigure(3, weight=3)  # Chart bekommt mehr Platz
        
        # Multiplikatoren oben
        mult_frame = ttk.Frame(result_frame)
        mult_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        mult_frame.columnconfigure(1, weight=1)
        
        self.mult_labels = {}
        mult_labels_text = [
            ("Erwartete Rolls pro Claim:", "expected_rolls"),
            ("Refresh-Multiplikator:", "refresh_mult"),
            ("Gesamt-Multiplikator:", "total_mult")
        ]
        
        for i, (label_text, key) in enumerate(mult_labels_text):
            ttk.Label(mult_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=(0, 10))
            value_label = ttk.Label(mult_frame, text="—", font=("Arial", 9))
            value_label.grid(row=i, column=1, sticky=tk.W)
            self.mult_labels[key] = value_label
        
        # Separator
        ttk.Separator(result_frame, orient='horizontal').grid(
            row=1, column=0, sticky=(tk.W, tk.E), pady=10
        )
        
        # EV-Ergebnisse Frame (ohne Tabelle, nur Total und Gift-EV)
        ev_frame = ttk.Frame(result_frame)
        ev_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        ev_frame.columnconfigure(1, weight=1)
        
        # EV-Labels für Bar Chart (werden nicht angezeigt, aber für Chart benötigt)
        self.ev_labels = {}
        ev_labels_text = [
            ("Gems (Basis aus Rolls):", "gems_base"),
            ("Gems (Stonks EV):", "stonks_ev"),
            ("Skill Shards (Gem-Äq):", "skill_shards_ev"),
            ("Founder Speed Boost:", "founder_speed_boost"),
            ("Founder Gems:", "founder_gems"),
            ("Founder Bomb Boost:", "founder_bomb_boost")
        ]
        
        # Labels werden nicht angezeigt, aber erstellt für Chart-Updates
        for i, (label_text, key) in enumerate(ev_labels_text):
            value_label = ttk.Label(ev_frame, text="—", font=("Arial", 9))
            # Nicht im GUI anzeigen, nur für Daten
            self.ev_labels[key] = value_label
        
        # Total
        ttk.Label(ev_frame, text="TOTAL:", font=("Arial", 11, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5
        )
        self.total_label = ttk.Label(ev_frame, text="—", font=("Arial", 11, "bold"))
        self.total_label.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Separator für Gift-EV
        ttk.Separator(ev_frame, orient='horizontal').grid(
            row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(15, 5)
        )
        
        # Gift-EV Sektion mit Hover-Tooltip
        gift_header_frame = ttk.Frame(ev_frame)
        gift_header_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        gift_label = ttk.Label(gift_header_frame, text="Gift-EV (pro 1 geöffneten Gift):", font=("Arial", 10, "bold"))
        gift_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        gift_help_label = tk.Label(gift_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray")
        gift_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Tooltip wird dynamisch erstellt (mit Contributions beim Hover)
        self.gift_help_label = gift_help_label
        self.create_dynamic_gift_tooltip(gift_help_label)
        
        ttk.Label(ev_frame, text="Gem-EV pro Gift:").grid(
            row=3, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        self.gift_ev_label = ttk.Label(ev_frame, text="—", font=("Arial", 11, "bold"))
        self.gift_ev_label.grid(row=3, column=1, sticky=tk.W)
        
        # Gift-EV Contributions (für Tooltip, nicht im GUI angezeigt)
        self.gift_contrib_labels = {}
        gift_contrib_text = [
            ("Gems (20-40):", "gems_20_40"),
            ("Gems (30-65):", "gems_30_65"),
            ("Skill Shards:", "skill_shards"),
            ("Blue Cow:", "blue_cow"),
            ("2× Speed Boost:", "speed_boost"),
            ("Rare Roll Gems:", "rare_gems"),
            ("Rekursive Gifts:", "recursive_gifts")
        ]
        
        # Gift-EV Contributions Labels (nur für Tooltip, nicht im GUI sichtbar)
        for label_text, key in gift_contrib_text:
            # Labels werden erstellt, aber nicht im GUI angezeigt (für Tooltip-Daten)
            value_label = tk.Label(ev_frame, text="—", font=("Arial", 8))
            self.gift_contrib_labels[key] = value_label
        
        # Bar Chart
        if MATPLOTLIB_AVAILABLE:
            chart_frame = ttk.LabelFrame(result_frame, text="Contributions (Bar Chart)", padding="5")
            chart_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
            chart_frame.columnconfigure(0, weight=1)
            chart_frame.rowconfigure(0, weight=1)
            result_frame.rowconfigure(3, weight=2)
            
            # Matplotlib Figure - größer und höher
            self.fig = Figure(figsize=(8, 6), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(
                result_frame,
                text="Matplotlib nicht verfügbar.\nBar Chart wird nicht angezeigt.",
                foreground="gray"
            ).grid(row=3, column=0, pady=10)
    
    def load_defaults(self):
        """Lädt die Standard-Werte"""
        defaults = GameParameters()
        
        self.vars['freebie_gems_base']['var'].set(str(defaults.freebie_gems_base))
        self.vars['freebie_timer_minutes']['var'].set(str(defaults.freebie_timer_minutes))
        self.vars['skill_shard_chance']['var'].set(str(defaults.skill_shard_chance * 100))
        self.vars['skill_shard_value_gems']['var'].set(str(defaults.skill_shard_value_gems))
        # Stonks wird über Checkbox gesteuert, Standard-Werte sind fix
        self.vars['jackpot_chance']['var'].set(str(defaults.jackpot_chance * 100))
        self.vars['jackpot_rolls']['var'].set(str(defaults.jackpot_rolls))
        self.vars['instant_refresh_chance']['var'].set(str(defaults.instant_refresh_chance * 100))
        self.vars['vip_lounge_level']['var'].set(str(defaults.vip_lounge_level))
        # founder_gems_base ist fix (10.0), wird nicht im GUI angezeigt
        self.vars['obelisk_level']['var'].set(str(defaults.obelisk_level))
        # Founder Speed Parameter sind fix (2.0x für 5 Minuten), werden nicht im GUI angezeigt
        self.vars['founder_bomb_interval_seconds']['var'].set(str(defaults.founder_bomb_interval_seconds))
        self.vars['founder_bomb_speed_chance']['var'].set(str(defaults.founder_bomb_speed_chance * 100))
        self.vars['founder_bomb_speed_multiplier']['var'].set(str(defaults.founder_bomb_speed_multiplier))
        self.vars['founder_bomb_speed_duration_seconds']['var'].set(str(defaults.founder_bomb_speed_duration_seconds))
    
    def get_parameters(self):
        """Liest die Parameter aus den Eingabefeldern"""
        try:
            params = {}
            
            for key, info in self.vars.items():
                value = info['var'].get().strip()
                
                if not value:
                    raise ValueError(f"Bitte geben Sie einen Wert für {key} ein.")
                
                if info['is_percent']:
                    # Prozent in Dezimal umwandeln
                    params[key] = float(value) / 100.0
                elif info['is_int']:
                    params[key] = int(value)
                else:
                    params[key] = float(value)
            
            # Stonks: Wenn Checkbox deaktiviert, setze Chance auf 0
            # Standard-Werte für Stonks sind immer 1% Chance, 200 Gems
            if hasattr(self, 'stonks_enabled') and not self.stonks_enabled.get():
                params['stonks_chance'] = 0.0
            else:
                params['stonks_chance'] = 0.01  # 1% Chance wenn aktiviert
            params['stonks_bonus_gems'] = 200.0  # Immer 200 Gems Bonus
            
            return GameParameters(**params)
        
        except ValueError as e:
            messagebox.showerror("Eingabefehler", str(e))
            return None
    
    def update_chart(self, ev, calculator):
        """Aktualisiert den Bar Chart mit den EV-Contributions"""
        if not MATPLOTLIB_AVAILABLE or self.fig is None:
            return
        
        # Hole die Aufschlüsselung
        breakdown = calculator.calculate_ev_breakdown()
        
        # Daten für Chart
        # Founder Speed und Founder Gems werden als gestapelte Bars in einer Kategorie dargestellt
        categories = [
            "Gems\n(Basis)",
            "Stonks\nEV",
            "Skill\nShards",
            "Founder\nSupply\nDrop",
            "Founder\nBomb"
        ]
        
        # Gestapelte Bars: Basis, Jackpot, Refresh (Base), Refresh (Jackpot)
        base_values = []
        jackpot_values = []
        refresh_base_values = []
        refresh_jackpot_values = []
        
        # Normale Keys (ohne Founder Speed und Gems)
        normal_keys = ['gems_base', 'stonks_ev', 'skill_shards_ev', 'founder_bomb_boost']
        
        for key in normal_keys:
            bd = breakdown[key]
            base_values.append(bd['base'])
            jackpot_values.append(bd['jackpot'])
            refresh_base_values.append(bd['refresh_base'])
            refresh_jackpot_values.append(bd['refresh_jackpot'])
        
        # Founder Supply Drop: Speed und Gems separat für die gestapelten Bars
        # Zuerst Speed (unten), dann Gems (oben)
        founder_speed_bd = breakdown['founder_speed_boost']
        founder_gems_bd = breakdown['founder_gems']
        
        # Speed (unten) - wird als Basis für die gestapelte Bar verwendet
        base_values.append(founder_speed_bd['base'])
        jackpot_values.append(founder_speed_bd['jackpot'])
        refresh_base_values.append(founder_speed_bd['refresh_base'])
        refresh_jackpot_values.append(founder_speed_bd['refresh_jackpot'])
        
        # Gems (oben) - wird auf Speed gestapelt
        founder_gems_base = [founder_gems_bd['base']]
        founder_gems_jackpot = [founder_gems_bd['jackpot']]
        founder_gems_refresh_base = [founder_gems_bd['refresh_base']]
        founder_gems_refresh_jackpot = [founder_gems_bd['refresh_jackpot']]
        
        # Prozentanteile berechnen (für normale Bars)
        total = ev['total']
        percentages = [(v / total * 100) if total > 0 else 0 for v in [
            ev['gems_base'],
            ev['stonks_ev'],
            ev['skill_shards_ev'],
            ev['founder_bomb_boost']
        ]]
        
        # Founder Supply Drop Prozentanteile (gesamt: Speed + Gems)
        founder_supply_total = ev['founder_speed_boost'] + ev['founder_gems']
        founder_supply_percentage = (founder_supply_total / total * 100) if total > 0 else 0
        percentages.append(founder_supply_percentage)
        
        # Chart aktualisieren
        self.ax.clear()
        
        # Gestapelte Bars erstellen
        x = range(len(categories))
        width = 0.6
        
        # Normale Bars (erste 4 Kategorien)
        x_normal = x[:-1]
        base_values_normal = base_values[:-1]
        jackpot_values_normal = jackpot_values[:-1]
        refresh_base_values_normal = refresh_base_values[:-1]
        refresh_jackpot_values_normal = refresh_jackpot_values[:-1]
        
        # Basis (unten) - normale Bars
        bars_base = self.ax.bar(x_normal, base_values_normal, width, label='Basis', 
                                color='#2E86AB', edgecolor='black', linewidth=1.0)
        
        # Jackpot (auf Basis) - normale Bars
        bars_jackpot = self.ax.bar(x_normal, jackpot_values_normal, width, bottom=base_values_normal,
                                   label='Jackpot', color='#A23B72', edgecolor='black', 
                                   linewidth=1.0, hatch='///', alpha=0.8)
        
        # Refresh Base (auf Basis+Jackpot) - normale Bars
        bottom_refresh_base_normal = [b + j for b, j in zip(base_values_normal, jackpot_values_normal)]
        bars_refresh_base = self.ax.bar(x_normal, refresh_base_values_normal, width, bottom=bottom_refresh_base_normal,
                                       label='Refresh (Base)', color='#F18F01', edgecolor='black',
                                       linewidth=1.0, hatch='...', alpha=0.8)
        
        # Refresh Jackpot (ganz oben) - normale Bars
        bottom_refresh_jackpot_normal = [b + j + r for b, j, r in zip(base_values_normal, jackpot_values_normal, refresh_base_values_normal)]
        bars_refresh_jackpot_normal = self.ax.bar(x_normal, refresh_jackpot_values_normal, width, bottom=bottom_refresh_jackpot_normal,
                                                  label='Refresh (Jackpot)', color='#C73E1D', edgecolor='black',
                                                  linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Founder Supply Drop: Speed (unten) und Gems (oben) gestapelt
        x_founder = x[-1]
        
        # Founder Speed - untere gestapelte Bar (wie normale Bars)
        founder_speed_base = base_values[-1]
        founder_speed_jackpot = jackpot_values[-1]
        founder_speed_refresh_base = refresh_base_values[-1]
        founder_speed_refresh_jackpot = refresh_jackpot_values[-1]
        
        # Speed-Bars (unten)
        self.ax.bar([x_founder], [founder_speed_base], width, color='#2E86AB', edgecolor='black', linewidth=1.0)
        self.ax.bar([x_founder], [founder_speed_jackpot], width, bottom=[founder_speed_base],
                    color='#A23B72', edgecolor='black', linewidth=1.0, hatch='///', alpha=0.8)
        self.ax.bar([x_founder], [founder_speed_refresh_base], width, bottom=[founder_speed_base + founder_speed_jackpot],
                    color='#F18F01', edgecolor='black', linewidth=1.0, hatch='...', alpha=0.8)
        self.ax.bar([x_founder], [founder_speed_refresh_jackpot], width, 
                    bottom=[founder_speed_base + founder_speed_jackpot + founder_speed_refresh_base],
                    color='#C73E1D', edgecolor='black', linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Founder Gems - obere gestapelte Bar (auf Speed)
        founder_speed_total = founder_speed_base + founder_speed_jackpot + founder_speed_refresh_base + founder_speed_refresh_jackpot
        founder_gems_bottom_base = founder_speed_total
        founder_gems_bottom_jackpot = founder_speed_total + founder_gems_base[0]
        founder_gems_bottom_refresh_base = founder_speed_total + founder_gems_base[0] + founder_gems_jackpot[0]
        
        # Gems-Bars (oben, auf Speed gestapelt)
        self.ax.bar([x_founder], founder_gems_base, width, bottom=[founder_gems_bottom_base],
                    color='#2E86AB', edgecolor='black', linewidth=1.0)
        self.ax.bar([x_founder], founder_gems_jackpot, width, bottom=[founder_gems_bottom_jackpot],
                    color='#A23B72', edgecolor='black', linewidth=1.0, hatch='///', alpha=0.8)
        self.ax.bar([x_founder], founder_gems_refresh_base, width, bottom=[founder_gems_bottom_refresh_base],
                    color='#F18F01', edgecolor='black', linewidth=1.0, hatch='...', alpha=0.8)
        self.ax.bar([x_founder], founder_gems_refresh_jackpot, width,
                    bottom=[founder_gems_bottom_refresh_base + founder_gems_refresh_base[0]],
                    color='#C73E1D', edgecolor='black', linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Werte und Prozentanteile auf Bars anzeigen (ganz oben)
        # Normale Bars
        normal_total_values = [ev['gems_base'], ev['stonks_ev'], ev['skill_shards_ev'], ev['founder_bomb_boost']]
        
        for i, (total_val, percentage) in enumerate(zip(normal_total_values, percentages[:-1])):
            height = base_values[i] + jackpot_values[i] + refresh_base_values[i] + refresh_jackpot_values[i]
            self.ax.text(
                i, height,
                f'{total_val:.1f}\n({percentage:.1f}%)',
                ha='center', va='bottom', fontsize=8, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                         edgecolor='gray', linewidth=0.5)
            )
        
        # Founder Supply Drop: Gesamtwert oben, aber auch Speed und Gems separat anzeigen
        founder_supply_total_height = (base_values[-1] + jackpot_values[-1] + refresh_base_values[-1] + refresh_jackpot_values[-1] +
                                      founder_gems_base[0] + founder_gems_jackpot[0] + founder_gems_refresh_base[0] + founder_gems_refresh_jackpot[0])
        
        # Gesamtwert oben
        self.ax.text(
            len(x) - 1, founder_supply_total_height,
            f'{ev["founder_speed_boost"] + ev["founder_gems"]:.1f}\n({percentages[-1]:.1f}%)',
            ha='center', va='bottom', fontsize=8, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                     edgecolor='gray', linewidth=0.5)
        )
        
        # Speed-Wert auf dem Speed-Segment (Mitte)
        founder_speed_segment_height = base_values[-1] + jackpot_values[-1] + refresh_base_values[-1] + refresh_jackpot_values[-1]
        founder_speed_midpoint = founder_speed_segment_height / 2
        self.ax.text(
            len(x) - 1, founder_speed_midpoint,
            f'Speed:\n{ev["founder_speed_boost"]:.1f}',
            ha='center', va='center', fontsize=7, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='lightblue', alpha=0.7, 
                     edgecolor='blue', linewidth=0.5)
        )
        
        # Gems-Wert auf dem Gems-Segment (oberer Teil)
        founder_gems_segment_height = founder_gems_base[0] + founder_gems_jackpot[0] + founder_gems_refresh_base[0] + founder_gems_refresh_jackpot[0]
        founder_gems_midpoint = founder_speed_segment_height + founder_gems_segment_height / 2
        self.ax.text(
            len(x) - 1, founder_gems_midpoint,
            f'Gems:\n{ev["founder_gems"]:.1f}',
            ha='center', va='center', fontsize=7, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='lightgreen', alpha=0.7, 
                     edgecolor='green', linewidth=0.5)
        )
        
        # X-Achse Labels
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(categories)
        
        # Legende
        self.ax.legend(loc='upper right', fontsize=8, framealpha=0.9)
        
        self.ax.set_ylabel('Gems-Äquivalent pro Stunde', fontsize=10, fontweight='bold')
        self.ax.set_title('EV Contributions', fontsize=12, fontweight='bold', pad=10)
        self.ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Y-Achse bei 0 starten
        self.ax.set_ylim(bottom=0)
        
        # Layout anpassen
        self.fig.tight_layout()
        self.canvas.draw()
    
    def calculate(self):
        """Führt die Berechnung durch"""
        params = self.get_parameters()
        if params is None:
            return
        
        try:
            calculator = FreebieEVCalculator(params)
            
            # Multiplikatoren berechnen
            expected_rolls = calculator.calculate_expected_rolls_per_claim()
            refresh_mult = calculator.calculate_refresh_multiplier()
            total_mult = calculator.calculate_total_multiplier()
            
            # EV berechnen
            ev = calculator.calculate_total_ev_per_hour()
            
            # Multiplikatoren anzeigen
            self.mult_labels['expected_rolls'].config(text=f"{expected_rolls:.4f}")
            self.mult_labels['refresh_mult'].config(text=f"{refresh_mult:.4f}")
            self.mult_labels['total_mult'].config(text=f"{total_mult:.4f}")
            
            # EV-Ergebnisse für Chart aktualisieren (werden nicht angezeigt, aber für Chart benötigt)
            self.ev_labels['gems_base'].config(text=f"{ev['gems_base']:.1f} Gems/h")
            self.ev_labels['stonks_ev'].config(text=f"{ev['stonks_ev']:.1f} Gems/h")
            self.ev_labels['skill_shards_ev'].config(text=f"{ev['skill_shards_ev']:.1f} Gems/h")
            self.ev_labels['founder_speed_boost'].config(text=f"{ev['founder_speed_boost']:.1f} Gems/h")
            self.ev_labels['founder_gems'].config(text=f"{ev['founder_gems']:.1f} Gems/h")
            self.ev_labels['founder_bomb_boost'].config(text=f"{ev['founder_bomb_boost']:.1f} Gems/h")
            
            # Total anzeigen
            self.total_label.config(text=f"{ev['total']:.1f} Gems-Äquivalent/h")
            
            # Gift-EV berechnen und anzeigen
            gift_ev = calculator.calculate_gift_ev_per_gift()
            self.gift_ev_label.config(text=f"{gift_ev:.1f} Gems pro Gift")
            
            # Gift-EV Contributions anzeigen
            gift_contrib = calculator.calculate_gift_ev_breakdown()
            self.gift_contrib_labels['gems_20_40'].config(text=f"{gift_contrib['gems_20_40']:.1f} Gems")
            self.gift_contrib_labels['gems_30_65'].config(text=f"{gift_contrib['gems_30_65']:.1f} Gems")
            self.gift_contrib_labels['skill_shards'].config(text=f"{gift_contrib['skill_shards']:.1f} Gems")
            self.gift_contrib_labels['blue_cow'].config(text=f"{gift_contrib['blue_cow']:.1f} Gems")
            self.gift_contrib_labels['speed_boost'].config(text=f"{gift_contrib['speed_boost']:.1f} Gems")
            self.gift_contrib_labels['rare_gems'].config(text=f"{gift_contrib['rare_gems']:.1f} Gems")
            self.gift_contrib_labels['recursive_gifts'].config(text=f"{gift_contrib['recursive_gifts']:.1f} Gems")
            
            # Chart aktualisieren
            self.update_chart(ev, calculator)
        
        except Exception as e:
            # Bei Auto-Calculate keine Fehlermeldung anzeigen, nur bei manueller Berechnung
            if not hasattr(self, '_auto_calculating') or not self._auto_calculating:
                messagebox.showerror("Berechnungsfehler", f"Ein Fehler ist aufgetreten:\n{str(e)}")
    
    def trigger_auto_calculate(self):
        """Löst eine automatische Berechnung mit Delay aus"""
        if not self.auto_calculate_enabled:
            return
        
        # Verhindere mehrere gleichzeitige Berechnungen
        if self.calculation_pending:
            return
        
        self.calculation_pending = True
        
        # Berechne nach 500ms Delay (wenn der Benutzer aufhört zu tippen)
        self.root.after(500, self._perform_auto_calculate)
    
    def _perform_auto_calculate(self):
        """Führt die automatische Berechnung durch"""
        self.calculation_pending = False
        self._auto_calculating = True
        try:
            self.calculate()
        finally:
            self._auto_calculating = False


def main():
    """Hauptfunktion"""
    root = tk.Tk()
    app = ObeliskGemEVGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
