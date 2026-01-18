"""
GUI for ObeliskGemEV Calculator
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path
from PIL import Image, ImageTk

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


class OptionAnalyzerWindow:
    """Fenster zur Analyse verschiedener Kauf-Optionen"""
    
    def __init__(self, parent, calculator: FreebieEVCalculator):
        self.parent = parent
        self.calculator = calculator
        
        # Neues Fenster erstellen - größer und resizable
        self.window = tk.Toplevel(parent)
        self.window.title("Option Analyzer")
        self.window.geometry("650x520")
        self.window.resizable(True, True)
        self.window.minsize(600, 500)
        
        # Icon setzen (falls verfügbar)
        try:
            icon_path = Path(__file__).parent / "sprites" / "lootbug.png"
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.window.iconphoto(False, icon_photo)
        except:
            pass  # Ignore if icon can't be loaded
        
        self.create_widgets()
    
    def create_widgets(self):
        """Erstellt die Widgets im Fenster"""
        
        # Header - kompakter
        header_frame = ttk.Frame(self.window, padding="5")
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            header_frame,
            text="🔍 Option Analyzer",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Finde heraus, ob sich bestimmte Optionen lohnen!",
            font=("Arial", 9),
            foreground="gray"
        )
        subtitle_label.pack(pady=(3, 0))
        
        # Separator - kompakter
        ttk.Separator(self.window, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Content Frame - kompakter
        content_frame = ttk.Frame(self.window, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Option 1: 2x Game Speed
        self.create_speed_option(content_frame)
    
    def create_speed_option(self, parent):
        """Erstellt die Option für 2x Game Speed"""
        
        # Frame für diese Option - kompakter mit Icon-Header
        option_frame = ttk.LabelFrame(
            parent,
            text="",  # Kein Text, wir erstellen einen eigenen Header
            padding="8"
        )
        option_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Header mit Icon und Text
        header_frame = ttk.Frame(option_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Versuche, das 2x Speed Icon zu laden
        try:
            speed_icon_path = Path(__file__).parent / "sprites" / "gamespeed2x.png"
            if speed_icon_path.exists():
                speed_image = Image.open(speed_icon_path)
                speed_image = speed_image.resize((24, 24), Image.Resampling.LANCZOS)
                self.speed_icon_photo = ImageTk.PhotoImage(speed_image)
                speed_icon_label = tk.Label(header_frame, image=self.speed_icon_photo)
                speed_icon_label.pack(side=tk.LEFT, padx=(0, 8))
        except:
            pass
        
        ttk.Label(
            header_frame,
            text="⚡ 2× Game Speed",
            font=("Arial", 12, "bold")
        ).pack(side=tk.LEFT)
        
        # Separator nach Header
        ttk.Separator(option_frame, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Beschreibung - kompakter
        desc_label = ttk.Label(
            option_frame,
            text="Kosten: 15 Gems\nDauer: 10 Minuten 2× Game Speed",
            font=("Arial", 10)
        )
        desc_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Berechne, ob es sich lohnt
        is_worth, profit, affected_ev, total_ev = self.calculate_speed_option_worth()
        
        # Ergebnis Frame - kompakter
        result_frame = ttk.Frame(option_frame)
        result_frame.pack(fill=tk.X, pady=5)
        
        # Status (Lohnt sich / Lohnt sich nicht)
        if is_worth:
            status_text = "✅ LOHNT SICH!"
            status_color = "green"
        else:
            status_text = "❌ LOHNT SICH NICHT"
            status_color = "red"
        
        status_label = tk.Label(
            result_frame,
            text=status_text,
            font=("Arial", 14, "bold"),
            foreground=status_color
        )
        status_label.pack(pady=(0, 5))
        
        # Details Frame
        details_frame = ttk.Frame(option_frame)
        details_frame.pack(fill=tk.BOTH, expand=True)
        details_frame.columnconfigure(0, weight=0)
        details_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Betroffene EV/h
        ttk.Label(details_frame, text="Betroffene EV/h:").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        ttk.Label(
            details_frame,
            text=f"{affected_ev:.1f} Gems/h",
            font=("Arial", 9, "bold")
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Gewinn in 10 Minuten mit 2x Speed
        ttk.Label(details_frame, text="Mit 2× Speed (10 Min):").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        
        # Berechne Gewinn in 10 Minuten mit 2× Speed
        # In 10 Minuten mit 2× Speed sammelt man so viel wie in 20 Minuten normal
        gain_10min = affected_ev * (20.0 / 60.0)
        
        ttk.Label(
            details_frame,
            text=f"{gain_10min:.1f} Gems",
            font=("Arial", 9, "bold")
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Gewinn ohne Speed
        ttk.Label(details_frame, text="Normal (10 Min):").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        
        gain_10min_normal = affected_ev * (10.0 / 60.0)
        
        ttk.Label(
            details_frame,
            text=f"{gain_10min_normal:.1f} Gems",
            font=("Arial", 9)
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Zusätzlicher Gewinn
        ttk.Label(details_frame, text="Zusätzlicher Gewinn:").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        
        additional_gain = gain_10min - gain_10min_normal
        
        ttk.Label(
            details_frame,
            text=f"{additional_gain:.1f} Gems",
            font=("Arial", 9, "bold"),
            foreground="blue"
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Kosten
        ttk.Label(details_frame, text="Kosten:").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        ttk.Label(
            details_frame,
            text="15.0 Gems",
            font=("Arial", 9),
            foreground="red"
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Separator - kompakter
        ttk.Separator(details_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )
        row += 1
        
        # Netto-Gewinn
        ttk.Label(
            details_frame,
            text="Netto-Gewinn:",
            font=("Arial", 10, "bold")
        ).grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        profit_color = "green" if profit > 0 else "red"
        profit_text = f"+{profit:.1f} Gems" if profit > 0 else f"{profit:.1f} Gems"
        
        ttk.Label(
            details_frame,
            text=profit_text,
            font=("Arial", 10, "bold"),
            foreground=profit_color
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Info-Box - kompakter
        info_frame = ttk.Frame(option_frame)
        info_frame.pack(fill=tk.X, pady=(8, 0))
        
        info_text = (
            "ℹ️ Hinweis: 2× Game Speed wirkt nur auf freebie-basierte Incomes:\n"
            "   • Gems (Basis)\n"
            "   • Stonks\n"
            "   • Skill Shards\n"
            "\n"
            "   NICHT betroffen:\n"
            "   • Founder Supply Drop (zeitbasiert)\n"
            "   • Founder Bomb (zeitbasiert)"
        )
        
        info_label = tk.Label(
            info_frame,
            text=info_text,
            font=("Arial", 8),
            foreground="gray",
            justify=tk.LEFT,
            background="#f0f0f0",
            padx=8,
            pady=6,
            wraplength=550  # Text umbruch für bessere Darstellung
        )
        info_label.pack(fill=tk.BOTH, expand=True)
    
    def calculate_speed_option_worth(self):
        """
        Berechnet, ob sich die 2x Speed Option lohnt.
        
        Returns:
            (is_worth, profit, affected_ev, total_ev)
        """
        # Hole aktuelle EV-Werte
        ev = self.calculator.calculate_total_ev_per_hour()
        
        # Nur freebie-basierte Incomes sind betroffen
        affected_ev = (
            ev['gems_base'] +
            ev['stonks_ev'] +
            ev['skill_shards_ev']
            # NICHT: founder_speed_boost, founder_gems, founder_bomb_boost
        )
        
        # In 10 Minuten mit 2× Speed sammelt man so viel wie in 20 Minuten normal
        # Zusätzlicher Gewinn = affected_ev * (20/60 - 10/60)
        gain_with_speed = affected_ev * (20.0 / 60.0)  # 20 Minuten Wert
        gain_without_speed = affected_ev * (10.0 / 60.0)  # 10 Minuten Wert
        additional_gain = gain_with_speed - gain_without_speed
        
        # Kosten
        cost = 15.0
        
        # Netto-Gewinn
        profit = additional_gain - cost
        
        # Lohnt sich, wenn Profit > 0
        is_worth = profit > 0
        
        return is_worth, profit, affected_ev, ev['total']


class ObeliskGemEVGUI:
    """GUI for the ObeliskGemEV Calculator"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ObeliskGemEV Calculator")
        # Kompaktere Startgröße, passt sich aber an Bildschirmgröße an
        self.root.geometry("1400x800")
        self.root.resizable(True, True)
        
        # Icon setzen (gem.png)
        try:
            icon_path = Path(__file__).parent / "sprites" / "gem.png"
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(False, icon_photo)
        except:
            pass  # Ignore if icon can't be loaded
        
        # Optional: Mindestgröße setzen, damit das Layout nicht zu klein wird
        self.root.minsize(1000, 600)
        
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
        
        # Hauptcontainer - kompakteres Padding
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Flexible Spalten ohne minsize für besseres responsive Verhalten
        # Linke Spalte (Parameter) schmaler, rechte Spalte (Ergebnisse) breiter
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(1, weight=1)
        
        # Titel-Zeile: Kompakt mit Lootbug-Button direkt daneben
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(
            title_frame,
            text="ObeliskGemEV Calculator",
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Lootbug-Button direkt daneben (nicht weit entfernt)
        self.create_lootbug_button(title_frame)
        
        # Linke Spalte: Parameter
        self.create_parameter_section(main_frame)
        
        # Rechte Spalte: Ergebnisse + Chart
        self.create_result_section(main_frame)
    
    def create_parameter_section(self, parent):
        """Erstellt die Parameter-Eingabefelder (links)"""
        
        # Frame für Parameter mit Scrollbar - kompakterer Abstand
        param_container = ttk.Frame(parent)
        param_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
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
        
        # Mausrad-Scrolling aktivieren
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # ============================================
        # FREEBIE BEREICH
        # ============================================
        # Container mit Hintergrundfarbe
        freebie_container = tk.Frame(scrollable_frame, background="#E3F2FD", relief=tk.RIDGE, borderwidth=2)
        freebie_container.pack(fill=tk.X, padx=3, pady=(3, 8))
        
        freebie_header_frame = tk.Frame(freebie_container, background="#E3F2FD")
        freebie_header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        freebie_label = tk.Label(freebie_header_frame, text="🎁 FREEBIE", font=("Arial", 10, "bold"), background="#E3F2FD")
        freebie_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        freebie_help_label = tk.Label(freebie_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray", background="#E3F2FD")
        freebie_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        freebie_frame = tk.Frame(freebie_container, background="#E3F2FD")
        freebie_frame.pack(fill=tk.X, padx=5, pady=5)
        freebie_frame.columnconfigure(1, weight=1)
        
        # Tooltip für Freebie-Info
        freebie_info = (
            "FREEBIE Parameters:\n"
            "• Freebie Gems (Base): Fixed 9.0\n"
            "• Freebie Timer: 7.0 minutes\n"
            "• Skill Shards: 12% chance, 12.5 Gems value\n"
            "• Stonks: 1% chance, 200 Gems bonus (if enabled)\n"
            "• Jackpot: 5% chance for 5 additional rolls\n"
            "• Refresh: 5% chance for instant refresh"
        )
        self.create_tooltip(freebie_help_label, freebie_info)
        
        row = 0
        
        # Basis-Parameter
        tk.Label(freebie_frame, text="Base:", font=("Arial", 9, "bold"), background="#E3F2FD").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(freebie_frame, "freebie_gems_base", "  Freebie Gems (Base):", row, "9.0", bg_color="#E3F2FD")
        row += 1
        
        self.create_entry(freebie_frame, "freebie_timer_minutes", "  Freebie Timer (Minutes):", row, "7.0", bg_color="#E3F2FD")
        row += 1
        
        # Separator - kompakter
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Skill Shards (Freebie) - mit Icon
        skill_shard_header_frame = tk.Frame(freebie_frame, background="#E3F2FD")
        skill_shard_header_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))
        
        tk.Label(skill_shard_header_frame, text="Skill Shards (Freebie):", font=("Arial", 9, "bold"), background="#E3F2FD").pack(side=tk.LEFT)
        
        # Versuche, das Skill Shard Icon zu laden
        try:
            skill_shard_icon_path = Path(__file__).parent / "sprites" / "skill_shard.png"
            if skill_shard_icon_path.exists():
                skill_shard_image = Image.open(skill_shard_icon_path)
                skill_shard_image = skill_shard_image.resize((16, 16), Image.Resampling.LANCZOS)
                self.skill_shard_icon_photo = ImageTk.PhotoImage(skill_shard_image)
                skill_shard_icon_label = tk.Label(skill_shard_header_frame, image=self.skill_shard_icon_photo, background="#E3F2FD")
                skill_shard_icon_label.pack(side=tk.LEFT, padx=(5, 0))
        except:
            pass
        
        row += 1
        
        self.create_entry(freebie_frame, "skill_shard_chance", "  Skill Shard Chance (%):", row, "12.0", is_percent=True, bg_color="#E3F2FD")
        row += 1
        
        self.create_entry(freebie_frame, "skill_shard_value_gems", "  Skill Shard Value (Gems):", row, "12.5", bg_color="#E3F2FD")
        row += 1
        
        # Separator - kompakter
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Stonks (Freebie) - mit Icon
        stonks_header_frame = tk.Frame(freebie_frame, background="#E3F2FD")
        stonks_header_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=3)
        
        # Versuche, das Stonks Icon zu laden
        try:
            stonks_icon_path = Path(__file__).parent / "sprites" / "stonks_tree.png"
            if stonks_icon_path.exists():
                stonks_image = Image.open(stonks_icon_path)
                stonks_image = stonks_image.resize((20, 20), Image.Resampling.LANCZOS)
                self.stonks_icon_photo = ImageTk.PhotoImage(stonks_image)
                stonks_icon_label = tk.Label(stonks_header_frame, image=self.stonks_icon_photo, background="#E3F2FD")
                stonks_icon_label.pack(side=tk.LEFT, padx=(0, 5))
        except:
            pass
        
        stonks_var = tk.BooleanVar(value=True)  # Default: aktiviert
        self.stonks_enabled = stonks_var
        stonks_checkbox = ttk.Checkbutton(
            stonks_header_frame,
            text="Stonks enabled (1% chance, 200 Gems bonus)",
            variable=stonks_var,
            command=self.trigger_auto_calculate
        )
        stonks_checkbox.pack(side=tk.LEFT)
        
        row += 1
        
        # Separator - kompakter
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Jackpot (Freebie)
        tk.Label(freebie_frame, text="Jackpot (Freebie):", font=("Arial", 9, "bold"), background="#E3F2FD").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(freebie_frame, "jackpot_chance", "  Jackpot Chance (%):", row, "5.0", is_percent=True, bg_color="#E3F2FD")
        row += 1
        
        self.create_entry(freebie_frame, "jackpot_rolls", "  Jackpot Rolls:", row, "5", is_int=True, bg_color="#E3F2FD")
        row += 1
        
        # Separator - kompakter
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Refresh (Freebie)
        tk.Label(freebie_frame, text="Refresh (Freebie):", font=("Arial", 9, "bold"), background="#E3F2FD").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(freebie_frame, "instant_refresh_chance", "  Instant Refresh Chance (%):", row, "5.0", is_percent=True, bg_color="#E3F2FD")
        
        # ============================================
        # FOUNDER SUPPLY DROP BEREICH
        # ============================================
        # Container mit Hintergrundfarbe
        founder_container = tk.Frame(scrollable_frame, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        founder_container.pack(fill=tk.X, padx=3, pady=(3, 8))
        
        founder_header_frame = tk.Frame(founder_container, background="#E8F5E9")
        founder_header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        founder_label = tk.Label(founder_header_frame, text="📦 FOUNDER SUPPLY DROP", font=("Arial", 10, "bold"), background="#E8F5E9")
        founder_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        founder_help_label = tk.Label(founder_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray", background="#E8F5E9")
        founder_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        founder_frame = tk.Frame(founder_container, background="#E8F5E9")
        founder_frame.pack(fill=tk.X, padx=5, pady=5)
        founder_frame.columnconfigure(1, weight=1)
        
        # Tooltip für Founder Supply Drop Info
        founder_info = (
            "FOUNDER SUPPLY DROP:\n"
            "• VIP Lounge Level: Determines drop interval and double/triple chance\n"
            "  - Interval: 60 - 2×(Level-1) minutes\n"
            "  - Double Chance: 12% at Level 2, +6% per level\n"
            "  - Triple Chance: 16% at Level 7\n"
            "• Founder Gems Base: Fixed 10 Gems per drop\n"
            "• Founder Speed: 2× speed for 5 minutes per drop\n"
            "  (saves time → more freebies → gem-equivalent)\n"
            "• 1/1234 Chance: 10 gifts per supply drop\n"
            "• Obelisk Level: Used for bonus gems"
        )
        self.create_tooltip(founder_help_label, founder_info)
        
        row = 0
        
        self.create_entry(founder_frame, "vip_lounge_level", "VIP Lounge Level (1-7):", row, "2", is_int=True, bg_color="#E8F5E9")
        row += 1
        
        self.create_entry(founder_frame, "obelisk_level", "Obelisk Level:", row, "26", is_int=True, bg_color="#E8F5E9")
        
        # ============================================
        # FOUNDER BOMB BEREICH
        # ============================================
        # Container mit Hintergrundfarbe
        bomb_container = tk.Frame(scrollable_frame, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        bomb_container.pack(fill=tk.X, padx=3, pady=(3, 8))
        
        bomb_header_frame = tk.Frame(bomb_container, background="#FFF3E0")
        bomb_header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        bomb_label = tk.Label(bomb_header_frame, text="💣 FOUNDER BOMB", font=("Arial", 10, "bold"), background="#FFF3E0")
        bomb_label.pack(side=tk.LEFT)
        
        # Versuche, das Bomb Icon zu laden
        try:
            bomb_icon_path = Path(__file__).parent / "sprites" / "founderbomb.png"
            if bomb_icon_path.exists():
                bomb_image = Image.open(bomb_icon_path)
                bomb_image = bomb_image.resize((20, 20), Image.Resampling.LANCZOS)
                self.bomb_icon_photo = ImageTk.PhotoImage(bomb_image)
                bomb_icon_label = tk.Label(bomb_header_frame, image=self.bomb_icon_photo, background="#FFF3E0")
                bomb_icon_label.pack(side=tk.LEFT, padx=(5, 0))
        except:
            pass
        
        bomb_frame = tk.Frame(bomb_container, background="#FFF3E0")
        bomb_frame.pack(fill=tk.X, padx=5, pady=5)
        bomb_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        self.create_entry(bomb_frame, "founder_bomb_interval_seconds", "Founder Bomb Interval (Seconds):", row, "87.0", bg_color="#FFF3E0")
        row += 1
        
        # Separator
        ttk.Separator(bomb_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8
        )
        row += 1
        
        tk.Label(bomb_frame, text="Bomb Speed:", font=("Arial", 9, "bold"), background="#FFF3E0").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(bomb_frame, "founder_bomb_speed_chance", "  Speed Chance (%):", row, "10.0", is_percent=True, bg_color="#FFF3E0")
        row += 1
        
        self.create_entry(bomb_frame, "founder_bomb_speed_multiplier", "  Speed Multiplier:", row, "2.0", bg_color="#FFF3E0")
        row += 1
        
        self.create_entry(bomb_frame, "founder_bomb_speed_duration_seconds", "  Speed Duration (Seconds):", row, "10.0", bg_color="#FFF3E0")
    
    def create_lootbug_button(self, parent):
        """Erstellt den Lootbug-Button für den Option Analyzer"""
        
        # Versuche, das Lootbug-Logo zu laden
        try:
            lootbug_path = Path(__file__).parent / "sprites" / "lootbug.png"
            if lootbug_path.exists():
                # Lade und skaliere das Bild
                lootbug_image = Image.open(lootbug_path)
                lootbug_image = lootbug_image.resize((32, 32), Image.Resampling.LANCZOS)
                self.lootbug_photo = ImageTk.PhotoImage(lootbug_image)
                
                # Button mit Bild
                lootbug_button = tk.Button(
                    parent,
                    image=self.lootbug_photo,
                    command=self.open_option_analyzer,
                    cursor="hand2",
                    relief=tk.RAISED,
                    borderwidth=2
                )
                lootbug_button.pack(side=tk.LEFT)
                
                # Tooltip für den Button
                self.create_tooltip(
                    lootbug_button,
                    "Option Analyzer\nFinde heraus, ob sich bestimmte\nKauf-Optionen lohnen!"
                )
            else:
                # Fallback: Button mit Text
                lootbug_button = ttk.Button(
                    parent,
                    text="🐛 Option Analyzer",
                    command=self.open_option_analyzer
                )
                lootbug_button.pack(side=tk.LEFT)
        except Exception as e:
            # Fallback: Button mit Text
            lootbug_button = ttk.Button(
                parent,
                text="🐛 Option Analyzer",
                command=self.open_option_analyzer
            )
            lootbug_button.pack(side=tk.LEFT)
    
    def open_option_analyzer(self):
        """Öffnet das Option Analyzer Fenster"""
        # Hole aktuelle Parameter und erstelle Calculator
        params = self.get_parameters()
        if params is None:
            messagebox.showwarning(
                "Parameter Error",
                "Bitte stelle sicher, dass alle Parameter korrekt eingegeben sind."
            )
            return
        
        try:
            calculator = FreebieEVCalculator(params)
            # Öffne das Analyzer-Fenster
            OptionAnalyzerWindow(self.root, calculator)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Fehler beim Öffnen des Option Analyzers:\n{str(e)}"
            )
    
    def create_tooltip(self, widget, text):
        """Creates a tooltip that appears when hovering over a widget"""
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
        """Creates a dynamic tooltip for Gift-EV with contributions"""
        def on_enter(event):
            # Basis-Info
            base_info = (
                "GIFT-EV Calculation:\n"
                "• Base Roll: Gems (20-40, 30-65), Skill Shards, Blue Cow, 2× Speed\n"
                "• Rare Roll: 1/45 chance for 80-130 Gems\n"
                "• Recursive Gifts: 1/40 chance for 3 additional gifts\n"
                "• Multipliers: Obelisk × Lucky Multiplier\n"
                "• All values are converted to gem-equivalent\n"
                "\n"
                "Contributions (current values):\n"
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
                contrib_text = "(Values will be displayed after calculation)\n"
            
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
        """Returns the label for a contribution key"""
        labels = {
            'gems_20_40': 'Gems (20-40)',
            'gems_30_65': 'Gems (30-65)',
            'skill_shards': 'Skill Shards',
            'blue_cow': 'Blue Cow',
            'speed_boost': '2× Speed Boost',
            'rare_gems': 'Rare Roll Gems',
            'recursive_gifts': 'Recursive Gifts'
        }
        return labels.get(key, key)
    
    def create_entry(self, parent, var_name, label_text, row, default_value, is_percent=False, is_int=False, bg_color=None):
        """Creates an input field with label"""
        
        if bg_color:
            tk.Label(parent, text=label_text, background=bg_color).grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        else:
            ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        var = tk.StringVar(value=default_value)
        self.vars[var_name] = {'var': var, 'is_percent': is_percent, 'is_int': is_int}
        
        entry = ttk.Entry(parent, textvariable=var, width=20)
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        
        # Live-Update: Berechne automatisch bei Änderung (mit Delay)
        var.trace_add('write', lambda *args: self.trigger_auto_calculate())
    
    def create_result_section(self, parent):
        """Creates the results display (right side)"""
        
        # Frame für Ergebnisse - kompakteres Padding
        result_frame = ttk.LabelFrame(parent, text="Results", padding="5")
        result_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=0)  # Separator
        result_frame.rowconfigure(2, weight=0)  # EV Frame (kompakt)
        result_frame.rowconfigure(3, weight=1)  # Chart bekommt den meisten Platz
        
        # Multiplikatoren oben - kompakter
        mult_frame = ttk.Frame(result_frame)
        mult_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        mult_frame.columnconfigure(1, weight=1)
        
        self.mult_labels = {}
        mult_labels_text = [
            ("Expected Rolls per Claim:", "expected_rolls"),
            ("Refresh Multiplier:", "refresh_mult"),
            ("Total Multiplier:", "total_mult")
        ]
        
        for i, (label_text, key) in enumerate(mult_labels_text):
            ttk.Label(mult_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=(0, 10))
            value_label = ttk.Label(mult_frame, text="—", font=("Arial", 9))
            value_label.grid(row=i, column=1, sticky=tk.W)
            self.mult_labels[key] = value_label
        
        # Separator - kompakter
        ttk.Separator(result_frame, orient='horizontal').grid(
            row=1, column=0, sticky=(tk.W, tk.E), pady=5
        )
        
        # EV-Ergebnisse Frame (ohne Tabelle, nur Total und Gift-EV) - kompakter
        ev_frame = ttk.Frame(result_frame)
        ev_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
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
        
        # Total - kompakter
        ttk.Label(ev_frame, text="TOTAL:", font=("Arial", 11, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10), pady=3
        )
        self.total_label = ttk.Label(ev_frame, text="—", font=("Arial", 11, "bold"))
        self.total_label.grid(row=0, column=1, sticky=tk.W, pady=3)
        
        # Separator für Gift-EV - kompakter
        ttk.Separator(ev_frame, orient='horizontal').grid(
            row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(8, 3)
        )
        
        # Gift-EV Sektion mit Hover-Tooltip - kompakter
        gift_header_frame = ttk.Frame(ev_frame)
        gift_header_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))
        
        gift_label = ttk.Label(gift_header_frame, text="Gift-EV (per 1 opened gift):", font=("Arial", 10, "bold"))
        gift_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        gift_help_label = tk.Label(gift_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray")
        gift_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Tooltip wird dynamisch erstellt (mit Contributions beim Hover)
        self.gift_help_label = gift_help_label
        self.create_dynamic_gift_tooltip(gift_help_label)
        
        ttk.Label(ev_frame, text="Gem-EV per Gift:").grid(
            row=3, column=0, sticky=tk.W, padx=(0, 10), pady=1
        )
        self.gift_ev_label = ttk.Label(ev_frame, text="—", font=("Arial", 11, "bold"))
        self.gift_ev_label.grid(row=3, column=1, sticky=tk.W, pady=1)
        
        # Gift-EV Contributions (für Tooltip, nicht im GUI angezeigt)
        self.gift_contrib_labels = {}
        gift_contrib_text = [
            ("Gems (20-40):", "gems_20_40"),
            ("Gems (30-65):", "gems_30_65"),
            ("Skill Shards:", "skill_shards"),
            ("Blue Cow:", "blue_cow"),
            ("2× Speed Boost:", "speed_boost"),
            ("Rare Roll Gems:", "rare_gems"),
            ("Recursive Gifts:", "recursive_gifts")
        ]
        
        # Gift-EV Contributions Labels (nur für Tooltip, nicht im GUI sichtbar)
        for label_text, key in gift_contrib_text:
            # Labels werden erstellt, aber nicht im GUI angezeigt (für Tooltip-Daten)
            value_label = tk.Label(ev_frame, text="—", font=("Arial", 8))
            self.gift_contrib_labels[key] = value_label
        
        # Bar Chart - kompakter, nimmt verfügbaren Platz
        if MATPLOTLIB_AVAILABLE:
            chart_frame = ttk.LabelFrame(result_frame, text="Contributions (Bar Chart)", padding="3")
            chart_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
            chart_frame.columnconfigure(0, weight=1)
            chart_frame.rowconfigure(0, weight=1)
            
            # Matplotlib Figure - responsive, passt sich Fenstergröße an
            self.fig = Figure(figsize=(8, 5), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(
                result_frame,
                text="Matplotlib not available.\nBar Chart will not be displayed.",
                foreground="gray"
            ).grid(row=3, column=0, pady=5)
    
    def load_defaults(self):
        """Loads the default values"""
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
        """Reads parameters from input fields"""
        try:
            params = {}
            
            for key, info in self.vars.items():
                value = info['var'].get().strip()
                
                if not value:
                    raise ValueError(f"Please enter a value for {key}.")
                
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
            messagebox.showerror("Input Error", str(e))
            return None
    
    def update_chart(self, ev, calculator):
        """Updates the bar chart with EV contributions"""
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
        
        # Normale Keys (ohne Founder Speed, Gems und Bomb)
        normal_keys = ['gems_base', 'stonks_ev', 'skill_shards_ev']
        
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
        
        # Founder Bomb (nach Founder Supply Drop)
        founder_bomb_bd = breakdown['founder_bomb_boost']
        base_values.append(founder_bomb_bd['base'])
        jackpot_values.append(founder_bomb_bd['jackpot'])
        refresh_base_values.append(founder_bomb_bd['refresh_base'])
        refresh_jackpot_values.append(founder_bomb_bd['refresh_jackpot'])
        
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
            ev['skill_shards_ev']
        ]]
        
        # Founder Supply Drop Prozentanteile (gesamt: Speed + Gems)
        founder_supply_total = ev['founder_speed_boost'] + ev['founder_gems']
        founder_supply_percentage = (founder_supply_total / total * 100) if total > 0 else 0
        percentages.append(founder_supply_percentage)
        
        # Founder Bomb Prozentanteile
        founder_bomb_percentage = (ev['founder_bomb_boost'] / total * 100) if total > 0 else 0
        percentages.append(founder_bomb_percentage)
        
        # Chart aktualisieren
        self.ax.clear()
        
        # Gestapelte Bars erstellen
        x = range(len(categories))
        width = 0.6
        
        # Normale Bars (erste 3 Kategorien: Gems, Stonks, Skill Shards)
        x_normal = x[:3]
        base_values_normal = base_values[:3]
        jackpot_values_normal = jackpot_values[:3]
        refresh_base_values_normal = refresh_base_values[:3]
        refresh_jackpot_values_normal = refresh_jackpot_values[:3]
        
        # Basis (unten) - normale Bars
        bars_base = self.ax.bar(x_normal, base_values_normal, width, label='Base', 
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
        x_founder = x[3]  # Index 3: Founder Supply Drop
        
        # Founder Bomb (separate Bar)
        x_bomb = x[4]  # Index 4: Founder Bomb
        
        # Founder Speed - untere gestapelte Bar (wie normale Bars)
        founder_speed_base = base_values[3]
        founder_speed_jackpot = jackpot_values[3]
        founder_speed_refresh_base = refresh_base_values[3]
        founder_speed_refresh_jackpot = refresh_jackpot_values[3]
        
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
        
        # Founder Bomb Bar (normale gestapelte Bar)
        founder_bomb_base = base_values[4]
        founder_bomb_jackpot = jackpot_values[4]
        founder_bomb_refresh_base = refresh_base_values[4]
        founder_bomb_refresh_jackpot = refresh_jackpot_values[4]
        
        self.ax.bar([x_bomb], [founder_bomb_base], width, color='#2E86AB', edgecolor='black', linewidth=1.0)
        self.ax.bar([x_bomb], [founder_bomb_jackpot], width, bottom=[founder_bomb_base],
                    color='#A23B72', edgecolor='black', linewidth=1.0, hatch='///', alpha=0.8)
        self.ax.bar([x_bomb], [founder_bomb_refresh_base], width, bottom=[founder_bomb_base + founder_bomb_jackpot],
                    color='#F18F01', edgecolor='black', linewidth=1.0, hatch='...', alpha=0.8)
        self.ax.bar([x_bomb], [founder_bomb_refresh_jackpot], width,
                    bottom=[founder_bomb_base + founder_bomb_jackpot + founder_bomb_refresh_base],
                    color='#C73E1D', edgecolor='black', linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Werte und Prozentanteile auf Bars anzeigen (ganz oben)
        # Normale Bars (erste 3)
        normal_total_values = [ev['gems_base'], ev['stonks_ev'], ev['skill_shards_ev']]
        
        for i, (total_val, percentage) in enumerate(zip(normal_total_values, percentages[:3])):
            height = base_values[i] + jackpot_values[i] + refresh_base_values[i] + refresh_jackpot_values[i]
            self.ax.text(
                i, height,
                f'{total_val:.1f}\n({percentage:.1f}%)',
                ha='center', va='bottom', fontsize=8, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                         edgecolor='gray', linewidth=0.5)
            )
        
        # Founder Bomb Bar
        founder_bomb_height = base_values[4] + jackpot_values[4] + refresh_base_values[4] + refresh_jackpot_values[4]
        self.ax.text(
            x_bomb, founder_bomb_height,
            f'{ev["founder_bomb_boost"]:.1f}\n({percentages[4]:.1f}%)',
            ha='center', va='bottom', fontsize=8, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                     edgecolor='gray', linewidth=0.5)
        )
        
        # Founder Supply Drop: Gesamtwert oben, aber auch Speed und Gems separat anzeigen
        founder_supply_total_height = (base_values[3] + jackpot_values[3] + refresh_base_values[3] + refresh_jackpot_values[3] +
                                      founder_gems_base[0] + founder_gems_jackpot[0] + founder_gems_refresh_base[0] + founder_gems_refresh_jackpot[0])
        
        # Gesamtwert oben (Index 3: Founder Supply Drop)
        self.ax.text(
            x_founder, founder_supply_total_height,
            f'{ev["founder_speed_boost"] + ev["founder_gems"]:.1f}\n({percentages[3]:.1f}%)',
            ha='center', va='bottom', fontsize=8, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                     edgecolor='gray', linewidth=0.5)
        )
        
        # Speed-Wert auf dem Speed-Segment (Mitte)
        founder_speed_segment_height = base_values[3] + jackpot_values[3] + refresh_base_values[3] + refresh_jackpot_values[3]
        founder_speed_midpoint = founder_speed_segment_height / 2
        self.ax.text(
            x_founder, founder_speed_midpoint,
            f'Speed:\n{ev["founder_speed_boost"]:.1f}',
            ha='center', va='center', fontsize=7, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='lightblue', alpha=0.7, 
                     edgecolor='blue', linewidth=0.5)
        )
        
        # Gems-Wert auf dem Gems-Segment (oberer Teil)
        founder_gems_segment_height = founder_gems_base[0] + founder_gems_jackpot[0] + founder_gems_refresh_base[0] + founder_gems_refresh_jackpot[0]
        founder_gems_midpoint = founder_speed_segment_height + founder_gems_segment_height / 2
        self.ax.text(
            x_founder, founder_gems_midpoint,
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
        
        self.ax.set_ylabel('Gem-Equivalent per Hour', fontsize=10, fontweight='bold')
        self.ax.set_title('EV Contributions', fontsize=12, fontweight='bold', pad=10)
        self.ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Y-Achse bei 0 starten
        self.ax.set_ylim(bottom=0)
        
        # Layout anpassen
        self.fig.tight_layout()
        self.canvas.draw()
    
    def calculate(self):
        """Performs the calculation"""
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
            self.total_label.config(text=f"{ev['total']:.1f} Gem-Equivalent/h")
            
            # Gift-EV berechnen und anzeigen
            gift_ev = calculator.calculate_gift_ev_per_gift()
            self.gift_ev_label.config(text=f"{gift_ev:.1f} Gems per Gift")
            
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
                messagebox.showerror("Calculation Error", f"An error occurred:\n{str(e)}")
    
    def trigger_auto_calculate(self):
        """Triggers an automatic calculation with delay"""
        if not self.auto_calculate_enabled:
            return
        
        # Verhindere mehrere gleichzeitige Berechnungen
        if self.calculation_pending:
            return
        
        self.calculation_pending = True
        
        # Berechne nach 500ms Delay (wenn der Benutzer aufhört zu tippen)
        self.root.after(500, self._perform_auto_calculate)
    
    def _perform_auto_calculate(self):
        """Performs the automatic calculation"""
        self.calculation_pending = False
        self._auto_calculating = True
        try:
            self.calculate()
        finally:
            self._auto_calculating = False


def main():
    """Main function"""
    root = tk.Tk()
    app = ObeliskGemEVGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
