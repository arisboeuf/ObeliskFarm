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
        
        # Frame für Parameter
        param_frame = ttk.LabelFrame(scrollable_frame, text="Spielparameter", padding="10")
        param_frame.pack(fill=tk.BOTH, expand=True)
        param_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Basis-Parameter
        ttk.Label(param_frame, text="Basis-Parameter:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1
        
        self.create_entry(param_frame, "freebie_gems_base", "Freebie Gems (Basis):", row, "9.0")
        row += 1
        
        self.create_entry(param_frame, "freebie_timer_minutes", "Freebie Timer (Minuten):", row, "7.0")
        row += 1
        
        # Separator
        ttk.Separator(param_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Skill Shards
        ttk.Label(param_frame, text="Skill Shards:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1
        
        self.create_entry(param_frame, "skill_shard_chance", "Skill Shard Chance (%):", row, "12.0", is_percent=True)
        row += 1
        
        self.create_entry(param_frame, "skill_shard_value_gems", "Skill Shard Wert (Gems):", row, "12.5")
        row += 1
        
        # Separator
        ttk.Separator(param_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Stonks
        ttk.Label(param_frame, text="Stonks:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1
        
        self.create_entry(param_frame, "stonks_chance", "Stonks Chance (%):", row, "1.0", is_percent=True)
        row += 1
        
        self.create_entry(param_frame, "stonks_bonus_gems", "Stonks Bonus (Gems):", row, "200.0")
        row += 1
        
        # Separator
        ttk.Separator(param_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Jackpot
        ttk.Label(param_frame, text="Jackpot:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1
        
        self.create_entry(param_frame, "jackpot_chance", "Jackpot Chance (%):", row, "5.0", is_percent=True)
        row += 1
        
        self.create_entry(param_frame, "jackpot_rolls", "Jackpot Rolls:", row, "5", is_int=True)
        row += 1
        
        # Separator
        ttk.Separator(param_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Refresh
        ttk.Label(param_frame, text="Refresh:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1
        
        self.create_entry(param_frame, "instant_refresh_chance", "Instant Refresh Chance (%):", row, "5.0", is_percent=True)
        row += 1
        
        # Separator
        ttk.Separator(param_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Founder
        ttk.Label(param_frame, text="Founder:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1
        
        self.create_entry(param_frame, "founder_drop_interval_minutes", "Founder Drop Intervall (Minuten):", row, "58.0")
        row += 1
        
        self.create_entry(param_frame, "founder_gems_base", "Founder Gems Base:", row, "10.0")
        row += 1
        
        self.create_entry(param_frame, "obelisk_level", "Obelisk Level:", row, "26", is_int=True)
        row += 1
        
        self.create_entry(param_frame, "founder_speed_multiplier", "Founder Speed Multiplikator:", row, "2.0")
        row += 1
        
        self.create_entry(param_frame, "founder_speed_duration_minutes", "Founder Speed Dauer (Minuten):", row, "5.0")
        row += 1
        
        # Separator
        ttk.Separator(param_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Founder Bomb
        ttk.Label(param_frame, text="Founder Bomb:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1
        
        self.create_entry(param_frame, "founder_bomb_interval_seconds", "Founder Bomb Intervall (Sekunden):", row, "87.0")
        row += 1
        
        self.create_entry(param_frame, "founder_bomb_speed_chance", "Founder Bomb Speed Chance (%):", row, "10.0", is_percent=True)
        row += 1
        
        self.create_entry(param_frame, "founder_bomb_speed_multiplier", "Founder Bomb Speed Multiplikator:", row, "2.0")
        row += 1
        
        self.create_entry(param_frame, "founder_bomb_speed_duration_seconds", "Founder Bomb Speed Dauer (Sekunden):", row, "10.0")
    
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
        
        # EV-Ergebnisse
        ev_frame = ttk.Frame(result_frame)
        ev_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        ev_frame.columnconfigure(1, weight=1)
        
        ttk.Label(ev_frame, text="EV pro Stunde (Gem-Äquivalent):", font=("Arial", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        
        self.ev_labels = {}
        ev_labels_text = [
            ("Gems (Basis aus Rolls):", "gems_base"),
            ("Gems (Stonks EV):", "stonks_ev"),
            ("Skill Shards (Gem-Äq):", "skill_shards_ev"),
            ("Founder Speed Boost:", "founder_speed_boost"),
            ("Founder Gems:", "founder_gems"),
            ("Founder Bomb Boost:", "founder_bomb_boost")
        ]
        
        for i, (label_text, key) in enumerate(ev_labels_text, start=1):
            ttk.Label(ev_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            value_label = ttk.Label(ev_frame, text="—", font=("Arial", 9))
            value_label.grid(row=i, column=1, sticky=tk.W)
            self.ev_labels[key] = value_label
        
        # Separator
        ttk.Separator(ev_frame, orient='horizontal').grid(
            row=len(ev_labels_text) + 1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )
        
        # Total
        ttk.Label(ev_frame, text="TOTAL:", font=("Arial", 11, "bold")).grid(
            row=len(ev_labels_text) + 2, column=0, sticky=tk.W, padx=(0, 10), pady=5
        )
        self.total_label = ttk.Label(ev_frame, text="—", font=("Arial", 11, "bold"))
        self.total_label.grid(row=len(ev_labels_text) + 2, column=1, sticky=tk.W, pady=5)
        
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
        self.vars['stonks_chance']['var'].set(str(defaults.stonks_chance * 100))
        self.vars['stonks_bonus_gems']['var'].set(str(defaults.stonks_bonus_gems))
        self.vars['jackpot_chance']['var'].set(str(defaults.jackpot_chance * 100))
        self.vars['jackpot_rolls']['var'].set(str(defaults.jackpot_rolls))
        self.vars['instant_refresh_chance']['var'].set(str(defaults.instant_refresh_chance * 100))
        self.vars['founder_drop_interval_minutes']['var'].set(str(defaults.founder_drop_interval_minutes))
        self.vars['founder_gems_base']['var'].set(str(defaults.founder_gems_base))
        self.vars['obelisk_level']['var'].set(str(defaults.obelisk_level))
        self.vars['founder_speed_multiplier']['var'].set(str(defaults.founder_speed_multiplier))
        self.vars['founder_speed_duration_minutes']['var'].set(str(defaults.founder_speed_duration_minutes))
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
        categories = [
            "Gems\n(Basis)",
            "Stonks\nEV",
            "Skill\nShards",
            "Founder\nSpeed",
            "Founder\nGems",
            "Founder\nBomb"
        ]
        
        # Gestapelte Bars: Basis, Jackpot, Refresh (Base), Refresh (Jackpot)
        base_values = []
        jackpot_values = []
        refresh_base_values = []
        refresh_jackpot_values = []
        
        keys = ['gems_base', 'stonks_ev', 'skill_shards_ev', 'founder_speed_boost', 'founder_gems', 'founder_bomb_boost']
        
        for key in keys:
            bd = breakdown[key]
            base_values.append(bd['base'])
            jackpot_values.append(bd['jackpot'])
            refresh_base_values.append(bd['refresh_base'])
            refresh_jackpot_values.append(bd['refresh_jackpot'])
        
        # Prozentanteile berechnen
        total = ev['total']
        percentages = [(v / total * 100) if total > 0 else 0 for v in [
            ev['gems_base'],
            ev['stonks_ev'],
            ev['skill_shards_ev'],
            ev['founder_speed_boost'],
            ev['founder_gems'],
            ev['founder_bomb_boost']
        ]]
        
        # Chart aktualisieren
        self.ax.clear()
        
        # Gestapelte Bars erstellen
        x = range(len(categories))
        width = 0.6
        
        # Basis (unten)
        bars_base = self.ax.bar(x, base_values, width, label='Basis', 
                                color='#2E86AB', edgecolor='black', linewidth=1.0)
        
        # Jackpot (auf Basis)
        bars_jackpot = self.ax.bar(x, jackpot_values, width, bottom=base_values,
                                   label='Jackpot', color='#A23B72', edgecolor='black', 
                                   linewidth=1.0, hatch='///', alpha=0.8)
        
        # Refresh Base (auf Basis+Jackpot)
        bottom_refresh_base = [b + j for b, j in zip(base_values, jackpot_values)]
        bars_refresh_base = self.ax.bar(x, refresh_base_values, width, bottom=bottom_refresh_base,
                                       label='Refresh (Base)', color='#F18F01', edgecolor='black',
                                       linewidth=1.0, hatch='...', alpha=0.8)
        
        # Refresh Jackpot (ganz oben)
        bottom_refresh_jackpot = [b + j + r for b, j, r in zip(base_values, jackpot_values, refresh_base_values)]
        bars_refresh_jackpot = self.ax.bar(x, refresh_jackpot_values, width, bottom=bottom_refresh_jackpot,
                                          label='Refresh (Jackpot)', color='#C73E1D', edgecolor='black',
                                          linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Werte und Prozentanteile auf Bars anzeigen (ganz oben)
        total_values = [ev['gems_base'], ev['stonks_ev'], ev['skill_shards_ev'], 
                       ev['founder_speed_boost'], ev['founder_gems'], ev['founder_bomb_boost']]
        
        for i, (total_val, percentage) in enumerate(zip(total_values, percentages)):
            height = total_val
            self.ax.text(
                i, height,
                f'{total_val:.1f}\n({percentage:.1f}%)',
                ha='center', va='bottom', fontsize=8, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                         edgecolor='gray', linewidth=0.5)
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
            
            # EV-Ergebnisse anzeigen
            self.ev_labels['gems_base'].config(text=f"{ev['gems_base']:.1f} Gems/h")
            self.ev_labels['stonks_ev'].config(text=f"{ev['stonks_ev']:.1f} Gems/h")
            self.ev_labels['skill_shards_ev'].config(text=f"{ev['skill_shards_ev']:.1f} Gems/h")
            self.ev_labels['founder_speed_boost'].config(text=f"{ev['founder_speed_boost']:.1f} Gems/h")
            self.ev_labels['founder_gems'].config(text=f"{ev['founder_gems']:.1f} Gems/h")
            self.ev_labels['founder_bomb_boost'].config(text=f"{ev['founder_bomb_boost']:.1f} Gems/h")
            
            # Total anzeigen
            self.total_label.config(text=f"{ev['total']:.1f} Gems-Äquivalent/h")
            
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
