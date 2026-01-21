"""
Stargazing Simulator / Optimizer GUI

Provides a window for tracking stargazing stats and calculating star income.
Users input their current stats from the game's stats page directly.
Upgrade levels are tracked separately to calculate the benefit of next upgrades.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import json
from PIL import Image, ImageTk

from .data import (
    STARS, STARGAZING_UPGRADES, SUPER_STAR_UPGRADES,
    get_star_upgrade_cost, get_super_star_upgrade_cost, format_number
)
from .calculator import (
    StargazingCalculator, PlayerStargazingStats, create_calculator_from_upgrades
)

# Save file path
SAVE_DIR = Path(__file__).parent.parent / "save"
SAVE_FILE = SAVE_DIR / "stargazing_save.json"

# Section colors
COLOR_STATS = "#E8F5E9"      # Light Green for Stats input
COLOR_UPGRADES = "#E3F2FD"   # Light Blue for Upgrades
COLOR_STARS = "#E8EAF6"      # Light Indigo for Stars
COLOR_RESULTS = "#FFF3E0"    # Light Orange for Results


class StargazingWindow:
    """Window for Stargazing optimization and tracking"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Stargazing Optimizer")
        self.window.state('zoomed')
        self.window.resizable(True, True)
        self.window.minsize(1000, 650)
        
        # Set icon
        try:
            icon_path = Path(__file__).parent.parent / "sprites" / "stargazing" / "stargazing.png"
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.window.iconphoto(False, icon_photo)
                self.icon_photo = icon_photo
        except:
            pass
        
        # Load sprite icons
        self.load_sprites()
        
        # Initialize state
        self.reset_to_defaults()
        
        # Create widgets
        self.create_widgets()
        
        # Load saved state
        self.load_state()
        
        # Initial calculation
        self.update_calculations()
        
        # Auto-save on close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def load_sprites(self):
        """Load all sprite icons"""
        self.sprites = {}
        sprite_files = {
            'telescope': 'Telescope.png',
            'auto_catch': 'Auto-Catch_Chance.png',
            'star_spawn_rate': 'Star_Spawn_Rate_Multiplier.png',
            'double_star': 'Star_Double_Spawn_Chance.png',
            'super_star_spawn': 'Super_Star_Spawn_Rate_Multiplier.png',
            'supernova': 'Star_Supernova_Chance.png',
            'super_10x': 'Super_Star_10x_Spawn_Chance.png',
            'supergiant': 'Star_Supergiant_Chance.png',
            'star_cap': 'Star_Specific_Cap.png',
            'super_supergiant': 'Super_Star_Supergiant_Chance.png',
            'all_star_mult': 'All_Star_Multiplier.png',
            'super_radiant': 'Super_Star_Radiant_Chance.png',
        }
        
        sprites_dir = Path(__file__).parent.parent / "sprites" / "stargazing"
        for key, filename in sprite_files.items():
            try:
                path = sprites_dir / filename
                if path.exists():
                    img = Image.open(path)
                    img = img.resize((18, 18), Image.Resampling.LANCZOS)
                    self.sprites[key] = ImageTk.PhotoImage(img)
            except:
                pass
    
    def _on_close(self):
        self.save_state()
        self.window.destroy()
    
    def reset_to_defaults(self):
        """Reset all values to defaults"""
        # Manual stats from game (what user sees in stats page)
        self.manual_stats = {
            'star_spawn_rate_mult': 1.0,
            'auto_catch_chance': 0.0,
            'double_star_chance': 0.0,
            'triple_star_chance': 0.0,
            'super_star_spawn_rate_mult': 1.0,
            'triple_super_star_chance': 0.0,
            'super_star_10x_chance': 0.0,
            'star_supernova_chance': 0.0,
            'star_supernova_mult': 10.0,  # Base supernova multiplier
            'star_supergiant_chance': 0.0,
            'star_supergiant_mult': 3.0,  # Base supergiant multiplier
            'super_star_supernova_chance': 0.0,
            'super_star_supernova_mult': 10.0,
            'super_star_supergiant_chance': 0.0,
            'super_star_supergiant_mult': 3.0,
            'super_star_radiant_chance': 0.0,
            'all_star_mult': 1.0,
        }
        
        # Floor clears per hour
        self.floor_clears_per_hour = 120.0
        
        # Upgrade levels (for calculating next upgrade benefit)
        self.stargazing_upgrades = {key: 0 for key in STARGAZING_UPGRADES.keys()}
        self.super_star_upgrades = {key: 0 for key in SUPER_STAR_UPGRADES.keys()}
        
        # Stars owned (toggle)
        self.stars_owned = {key: False for key in STARS.keys()}
        # First 3 stars are always owned if telescope >= 3
        for star in ['aries', 'taurus', 'gemini']:
            self.stars_owned[star] = True
        
        # Star levels
        self.star_levels = {key: 1 for key in STARS.keys()}
    
    def save_state(self):
        """Save current state to file"""
        state = {
            'manual_stats': self.manual_stats,
            'floor_clears_per_hour': self.floor_clears_per_hour,
            'stargazing_upgrades': self.stargazing_upgrades,
            'super_star_upgrades': self.super_star_upgrades,
            'stars_owned': self.stars_owned,
            'star_levels': self.star_levels,
        }
        try:
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            with open(SAVE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def load_state(self):
        """Load saved state from file"""
        if not SAVE_FILE.exists():
            return
        
        try:
            with open(SAVE_FILE, 'r') as f:
                state = json.load(f)
            
            # Load manual stats
            for key in self.manual_stats:
                if key in state.get('manual_stats', {}):
                    self.manual_stats[key] = state['manual_stats'][key]
            
            self.floor_clears_per_hour = state.get('floor_clears_per_hour', 120.0)
            
            # Load upgrade levels
            for key in self.stargazing_upgrades:
                if key in state.get('stargazing_upgrades', {}):
                    self.stargazing_upgrades[key] = state['stargazing_upgrades'][key]
            
            for key in self.super_star_upgrades:
                if key in state.get('super_star_upgrades', {}):
                    self.super_star_upgrades[key] = state['super_star_upgrades'][key]
            
            # Load stars owned
            for key in self.stars_owned:
                if key in state.get('stars_owned', {}):
                    self.stars_owned[key] = state['stars_owned'][key]
            
            # Load star levels
            for key in self.star_levels:
                if key in state.get('star_levels', {}):
                    self.star_levels[key] = state['star_levels'][key]
            
            # Update UI
            self.update_ui_from_state()
            
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
    
    def update_ui_from_state(self):
        """Update UI elements to reflect current state"""
        # Update manual stat entries
        if hasattr(self, 'stat_vars'):
            for key, var in self.stat_vars.items():
                var.set(str(self.manual_stats.get(key, 0)))
        
        if hasattr(self, 'floor_clears_var'):
            self.floor_clears_var.set(str(self.floor_clears_per_hour))
        
        # Update upgrade labels
        if hasattr(self, 'upgrade_level_labels'):
            for key, label in self.upgrade_level_labels.items():
                label.config(text=str(self.stargazing_upgrades.get(key, 0)))
        
        # Update star checkboxes
        if hasattr(self, 'star_owned_vars'):
            for key, var in self.star_owned_vars.items():
                var.set(self.stars_owned.get(key, False))
        
        # Update star level labels
        if hasattr(self, 'star_level_labels'):
            for key, label in self.star_level_labels.items():
                label.config(text=str(self.star_levels.get(key, 1)))
    
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main container
        main_frame = ttk.Frame(self.window, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        try:
            icon_path = Path(__file__).parent.parent / "sprites" / "stargazing" / "stargazing.png"
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_image = icon_image.resize((24, 24), Image.Resampling.LANCZOS)
                self.title_icon = ImageTk.PhotoImage(icon_image)
                tk.Label(title_frame, image=self.title_icon).pack(side=tk.LEFT, padx=(0, 8))
        except:
            pass
        
        ttk.Label(title_frame, text="Stargazing Optimizer", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # Main horizontal layout
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.columnconfigure(2, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Left: Manual Stats Input
        self.create_stats_section(content_frame)
        
        # Middle: Upgrades & Stars
        self.create_upgrades_section(content_frame)
        
        # Right: Results
        self.create_results_section(content_frame)
    
    def create_stats_section(self, parent):
        """Create the manual stats input section"""
        
        container = tk.Frame(parent, background=COLOR_STATS, relief=tk.RIDGE, borderwidth=2)
        container.grid(row=0, column=0, sticky="nsew", padx=(0, 3), pady=0)
        
        # Header
        header = tk.Frame(container, background=COLOR_STATS)
        header.pack(fill=tk.X, padx=5, pady=(5, 3))
        tk.Label(header, text="YOUR STATS (from game)", font=("Arial", 11, "bold"), 
                 background=COLOR_STATS).pack(side=tk.LEFT)
        
        # Stats frame with scroll
        canvas = tk.Canvas(container, background=COLOR_STATS, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        stats_frame = tk.Frame(canvas, background=COLOR_STATS)
        
        stats_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=stats_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=3)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        self.stat_vars = {}
        self.stat_entries = {}
        
        # Stats to input - organized by category
        # Format: (key, label, suffix, sprite_key, is_separator)
        stats_config = [
            # Star Stats
            ('_header_star', 'STAR STATS', '', None, True),
            ('star_spawn_rate_mult', 'Star Spawn Rate', 'x', 'star_spawn_rate', False),
            ('auto_catch_chance', 'Auto-Catch', '%', 'auto_catch', False),
            ('double_star_chance', 'Double Star', '%', 'double_star', False),
            ('triple_star_chance', 'Triple Star', '%', None, False),
            ('star_supernova_chance', 'Star Supernova', '%', 'supernova', False),
            ('star_supernova_mult', 'Supernova Multi', 'x', None, False),
            ('star_supergiant_chance', 'Star Supergiant', '%', 'supergiant', False),
            ('star_supergiant_mult', 'Supergiant Multi', 'x', None, False),
            # Super Star Stats
            ('_header_super', 'SUPER STAR STATS', '', None, True),
            ('super_star_spawn_rate_mult', 'Super Star Spawn', 'x', 'super_star_spawn', False),
            ('triple_super_star_chance', 'Triple Super Star', '%', None, False),
            ('super_star_10x_chance', 'Super Star 10x', '%', 'super_10x', False),
            ('super_star_supernova_chance', 'Super Star Supernova', '%', 'supernova', False),
            ('super_star_supernova_mult', 'Super Star Nova Multi', 'x', None, False),
            ('super_star_supergiant_chance', 'Super Star Supergiant', '%', 'super_supergiant', False),
            ('super_star_supergiant_mult', 'Super Star Giant Multi', 'x', None, False),
            ('super_star_radiant_chance', 'Super Star Radiant', '%', 'super_radiant', False),
            # Global Stats
            ('_header_global', 'GLOBAL STATS', '', None, True),
            ('all_star_mult', 'All Star Multi', 'x', 'all_star_mult', False),
        ]
        
        for key, label, suffix, sprite_key, is_separator in stats_config:
            if key.startswith('_header'):
                # Section header
                ttk.Separator(stats_frame, orient='horizontal').pack(fill=tk.X, pady=(8, 3))
                tk.Label(stats_frame, text=label, font=("Arial", 9, "bold"), 
                         background=COLOR_STATS, fg="#2E7D32").pack(anchor=tk.W)
                continue
            
            row_frame = tk.Frame(stats_frame, background=COLOR_STATS)
            row_frame.pack(fill=tk.X, pady=2)
            
            # Icon if available
            if sprite_key and sprite_key in self.sprites:
                tk.Label(row_frame, image=self.sprites[sprite_key], background=COLOR_STATS).pack(side=tk.LEFT, padx=(0, 3))
            
            # Label
            tk.Label(row_frame, text=f"{label}:", background=COLOR_STATS, 
                     font=("Arial", 9), width=18, anchor=tk.W).pack(side=tk.LEFT)
            
            # Entry
            var = tk.StringVar(value=str(self.manual_stats.get(key, 0)))
            self.stat_vars[key] = var
            entry = ttk.Entry(row_frame, textvariable=var, width=8, font=("Arial", 10))
            entry.pack(side=tk.LEFT, padx=3)
            entry.bind('<Return>', lambda e: self.on_stat_changed())
            entry.bind('<FocusOut>', lambda e: self.on_stat_changed())
            self.stat_entries[key] = entry
            
            # Suffix
            tk.Label(row_frame, text=suffix, background=COLOR_STATS, 
                     font=("Arial", 9), fg="gray").pack(side=tk.LEFT)
        
        # Floor clears
        ttk.Separator(stats_frame, orient='horizontal').pack(fill=tk.X, pady=(10, 5))
        
        floor_frame = tk.Frame(stats_frame, background=COLOR_STATS)
        floor_frame.pack(fill=tk.X, pady=2)
        tk.Label(floor_frame, text="Floors/hour:", background=COLOR_STATS, 
                 font=("Arial", 9, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT)
        self.floor_clears_var = tk.StringVar(value=str(self.floor_clears_per_hour))
        floor_entry = ttk.Entry(floor_frame, textvariable=self.floor_clears_var, width=8, font=("Arial", 10))
        floor_entry.pack(side=tk.LEFT, padx=3)
        floor_entry.bind('<Return>', lambda e: self.on_stat_changed())
        floor_entry.bind('<FocusOut>', lambda e: self.on_stat_changed())
        
        # Info about Super Star spawn
        info_frame = tk.Frame(stats_frame, background=COLOR_STATS)
        info_frame.pack(fill=tk.X, pady=(10, 3))
        tk.Label(info_frame, text="ℹ️ Super Star Spawn:", font=("Arial", 8, "bold"), 
                 background=COLOR_STATS, fg="#1565C0").pack(anchor=tk.W)
        tk.Label(info_frame, text="Base 1/100 (1%) chance when a Star spawns,", 
                 font=("Arial", 8), background=COLOR_STATS, fg="#555").pack(anchor=tk.W)
        tk.Label(info_frame, text="multiplied by Super Star Spawn Rate.", 
                 font=("Arial", 8), background=COLOR_STATS, fg="#555").pack(anchor=tk.W)
    
    def create_upgrades_section(self, parent):
        """Create the upgrades tracking section"""
        
        container = tk.Frame(parent, background=COLOR_UPGRADES, relief=tk.RIDGE, borderwidth=2)
        container.grid(row=0, column=1, sticky="nsew", padx=3, pady=0)
        
        # Header
        header = tk.Frame(container, background=COLOR_UPGRADES)
        header.pack(fill=tk.X, padx=5, pady=(5, 3))
        tk.Label(header, text="UPGRADES (for +% calc)", font=("Arial", 11, "bold"), 
                 background=COLOR_UPGRADES).pack(side=tk.LEFT)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # Tab 1: Stargazing Upgrades
        upgrades_tab = tk.Frame(notebook, background=COLOR_UPGRADES)
        notebook.add(upgrades_tab, text="Upgrades")
        self.create_upgrade_controls(upgrades_tab)
        
        # Tab 2: Stars
        stars_tab = tk.Frame(notebook, background=COLOR_STARS)
        notebook.add(stars_tab, text="Stars")
        self.create_star_controls(stars_tab)
    
    def create_upgrade_controls(self, parent):
        """Create upgrade level controls with +/- buttons"""
        
        canvas = tk.Canvas(parent, background=COLOR_UPGRADES, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, background=COLOR_UPGRADES)
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        self.upgrade_level_labels = {}
        self.upgrade_benefit_labels = {}
        
        # Upgrades with their display names
        important_upgrades = [
            ('auto_catch', 'Auto-Catch', '+4%/lvl', 'auto_catch'),
            ('star_spawn_rate', 'Star Spawn Rate', '+5%/lvl', 'star_spawn_rate'),
            ('double_star_chance', 'Double Star', '+5%/lvl', 'double_star'),
            ('super_star_spawn_rate', 'Super Star Spawn', '+2%/lvl', 'super_star_spawn'),
            ('star_supernova_chance', 'Star Supernova', '+0.5%/lvl', 'supernova'),
            ('super_star_10x_chance', 'Super Star 10x', '+0.2%/lvl', 'super_10x'),
            ('star_supergiant_chance', 'Star Supergiant', '+0.2%/lvl', 'supergiant'),
            ('super_star_supergiant_chance', 'Super Star Supergiant', '+0.15%/lvl', 'super_supergiant'),
            ('all_star_multiplier', 'All Star Multi', '+0.01x/lvl', 'all_star_mult'),
            ('super_star_radiant_chance', 'Super Star Radiant', '+0.15%/lvl', 'super_radiant'),
        ]
        
        for key, label, effect, sprite_key in important_upgrades:
            if key not in STARGAZING_UPGRADES:
                continue
            
            upgrade = STARGAZING_UPGRADES[key]
            row = tk.Frame(scrollable, background=COLOR_UPGRADES)
            row.pack(fill=tk.X, pady=2)
            
            # Icon
            if sprite_key and sprite_key in self.sprites:
                tk.Label(row, image=self.sprites[sprite_key], background=COLOR_UPGRADES).pack(side=tk.LEFT, padx=(0, 3))
            
            # Label with effect
            tk.Label(row, text=f"{label} ({effect})", background=COLOR_UPGRADES, 
                     font=("Arial", 9), width=22, anchor=tk.W).pack(side=tk.LEFT)
            
            # - Button
            minus_btn = tk.Button(row, text="-", width=2, font=("Arial", 8, "bold"), 
                                  command=lambda k=key: self.change_upgrade(k, -1))
            minus_btn.pack(side=tk.LEFT, padx=1)
            
            # Level label
            level_label = tk.Label(row, text=str(self.stargazing_upgrades.get(key, 0)), 
                                   background=COLOR_UPGRADES, font=("Arial", 10, "bold"), width=3)
            level_label.pack(side=tk.LEFT)
            self.upgrade_level_labels[key] = level_label
            
            # + Button
            plus_btn = tk.Button(row, text="+", width=2, font=("Arial", 8, "bold"),
                                command=lambda k=key: self.change_upgrade(k, 1))
            plus_btn.pack(side=tk.LEFT, padx=1)
            
            # Max level
            tk.Label(row, text=f"/{upgrade['max_level']}", background=COLOR_UPGRADES, 
                     font=("Arial", 9), fg="gray").pack(side=tk.LEFT)
            
            # Benefit label (will show +X% Stars/h)
            benefit_label = tk.Label(row, text="", background=COLOR_UPGRADES, 
                                     font=("Arial", 9, "bold"), fg="#2E7D32")
            benefit_label.pack(side=tk.RIGHT, padx=(5, 0))
            self.upgrade_benefit_labels[key] = benefit_label
    
    def create_star_controls(self, parent):
        """Create star toggle and level controls"""
        
        canvas = tk.Canvas(parent, background=COLOR_STARS, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, background=COLOR_STARS)
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.star_owned_vars = {}
        self.star_level_labels = {}
        
        # Stars in unlock order
        star_order = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 
                      'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces',
                      'ophiuchus', 'orion', 'hercules', 'draco', 'cetus', 'phoenix', 'eridanus']
        
        for key in star_order:
            if key not in STARS:
                continue
            
            star = STARS[key]
            row = tk.Frame(scrollable, background=COLOR_STARS)
            row.pack(fill=tk.X, pady=2)
            
            # Owned checkbox
            owned_var = tk.BooleanVar(value=self.stars_owned.get(key, False))
            self.star_owned_vars[key] = owned_var
            cb = ttk.Checkbutton(row, variable=owned_var, command=lambda k=key: self.on_star_owned_changed(k))
            cb.pack(side=tk.LEFT)
            
            # Name
            tk.Label(row, text=star.name, background=COLOR_STARS, 
                     font=("Arial", 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
            
            # - Button
            minus_btn = tk.Button(row, text="-", width=2, font=("Arial", 8, "bold"),
                                  command=lambda k=key: self.change_star_level(k, -1))
            minus_btn.pack(side=tk.LEFT, padx=1)
            
            # Level label
            level_label = tk.Label(row, text=str(self.star_levels.get(key, 1)),
                                   background=COLOR_STARS, font=("Arial", 10, "bold"), width=3)
            level_label.pack(side=tk.LEFT)
            self.star_level_labels[key] = level_label
            
            # + Button
            plus_btn = tk.Button(row, text="+", width=2, font=("Arial", 8, "bold"),
                                command=lambda k=key: self.change_star_level(k, 1))
            plus_btn.pack(side=tk.LEFT, padx=1)
            
            # Max
            tk.Label(row, text=f"/{star.max_level}", background=COLOR_STARS, 
                     font=("Arial", 9), fg="gray").pack(side=tk.LEFT)
    
    def create_results_section(self, parent):
        """Create the results display section"""
        
        container = tk.Frame(parent, background=COLOR_RESULTS, relief=tk.RIDGE, borderwidth=2)
        container.grid(row=0, column=2, sticky="nsew", padx=(3, 0), pady=0)
        
        # Header
        header = tk.Frame(container, background=COLOR_RESULTS)
        header.pack(fill=tk.X, padx=5, pady=(5, 3))
        tk.Label(header, text="RESULTS", font=("Arial", 11, "bold"), background=COLOR_RESULTS).pack(side=tk.LEFT)
        
        results_frame = tk.Frame(container, background=COLOR_RESULTS)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.result_labels = {}
        
        # Star Results
        tk.Label(results_frame, text="⭐ Star Income", font=("Arial", 11, "bold"), 
                 background=COLOR_RESULTS, fg="#1565C0").pack(anchor=tk.W, pady=(0, 5))
        
        star_metrics = [
            ('Star Spawns/hour:', 'star_spawns'),
            ('Stars/hour:', 'stars_per_hour'),
            ('Auto-caught/hour:', 'auto_stars'),
        ]
        
        for label, key in star_metrics:
            row = tk.Frame(results_frame, background=COLOR_RESULTS)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"  {label}", background=COLOR_RESULTS, 
                     font=("Arial", 10)).pack(side=tk.LEFT)
            val_label = tk.Label(row, text="—", background=COLOR_RESULTS, 
                                 font=("Arial", 11, "bold"))
            val_label.pack(side=tk.RIGHT)
            self.result_labels[key] = val_label
        
        # Super Star Results
        ttk.Separator(results_frame, orient='horizontal').pack(fill=tk.X, pady=8)
        tk.Label(results_frame, text="🌟 Super Star Income", font=("Arial", 11, "bold"), 
                 background=COLOR_RESULTS, fg="#E65100").pack(anchor=tk.W, pady=(0, 5))
        
        super_metrics = [
            ('Super Star Spawns/hour:', 'ss_spawns'),
            ('Super Stars/hour:', 'super_stars_per_hour'),
            ('Auto-caught/hour:', 'auto_super'),
        ]
        
        for label, key in super_metrics:
            row = tk.Frame(results_frame, background=COLOR_RESULTS)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"  {label}", background=COLOR_RESULTS, 
                     font=("Arial", 10)).pack(side=tk.LEFT)
            val_label = tk.Label(row, text="—", background=COLOR_RESULTS, 
                                 font=("Arial", 11, "bold"))
            val_label.pack(side=tk.RIGHT)
            self.result_labels[key] = val_label
        
        # Multiplier breakdown
        ttk.Separator(results_frame, orient='horizontal').pack(fill=tk.X, pady=8)
        tk.Label(results_frame, text="📊 Multipliers", font=("Arial", 10, "bold"), 
                 background=COLOR_RESULTS, fg="#6A1B9A").pack(anchor=tk.W, pady=(0, 3))
        
        mult_metrics = [
            ('Star Multiplier:', 'star_mult'),
            ('Super Star Multiplier:', 'super_mult'),
        ]
        
        for label, key in mult_metrics:
            row = tk.Frame(results_frame, background=COLOR_RESULTS)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"  {label}", background=COLOR_RESULTS, 
                     font=("Arial", 9)).pack(side=tk.LEFT)
            val_label = tk.Label(row, text="—", background=COLOR_RESULTS, 
                                 font=("Arial", 10, "bold"), fg="#6A1B9A")
            val_label.pack(side=tk.RIGHT)
            self.result_labels[key] = val_label
    
    def change_upgrade(self, key, delta):
        """Change upgrade level by delta"""
        if key not in STARGAZING_UPGRADES:
            return
        
        upgrade = STARGAZING_UPGRADES[key]
        current = self.stargazing_upgrades.get(key, 0)
        new_level = max(0, min(upgrade['max_level'], current + delta))
        
        self.stargazing_upgrades[key] = new_level
        self.upgrade_level_labels[key].config(text=str(new_level))
        self.update_calculations()
    
    def change_star_level(self, key, delta):
        """Change star level by delta"""
        if key not in STARS:
            return
        
        star = STARS[key]
        current = self.star_levels.get(key, 1)
        new_level = max(1, min(star.max_level, current + delta))
        
        self.star_levels[key] = new_level
        self.star_level_labels[key].config(text=str(new_level))
        self.update_calculations()
    
    def on_star_owned_changed(self, key):
        """Handle star owned toggle"""
        self.stars_owned[key] = self.star_owned_vars[key].get()
        self.update_calculations()
    
    def on_stat_changed(self):
        """Handle manual stat changes"""
        try:
            for key, var in self.stat_vars.items():
                val = var.get().strip()
                if val:
                    self.manual_stats[key] = float(val)
            
            val = self.floor_clears_var.get().strip()
            if val:
                self.floor_clears_per_hour = float(val)
        except:
            pass
        
        self.update_calculations()
    
    def update_calculations(self):
        """Recalculate and update display"""
        
        # Create stats from manual input
        # Convert percentages to decimals where needed
        stats = PlayerStargazingStats(
            star_spawn_rate_mult=self.manual_stats.get('star_spawn_rate_mult', 1.0),
            auto_catch_chance=self.manual_stats.get('auto_catch_chance', 0) / 100,  # % to decimal
            double_star_chance=self.manual_stats.get('double_star_chance', 0) / 100,
            triple_star_chance=self.manual_stats.get('triple_star_chance', 0) / 100,
            super_star_spawn_rate_mult=self.manual_stats.get('super_star_spawn_rate_mult', 1.0),
            triple_super_star_chance=self.manual_stats.get('triple_super_star_chance', 0) / 100,
            super_star_10x_chance=self.manual_stats.get('super_star_10x_chance', 0) / 100,
            star_supernova_chance=self.manual_stats.get('star_supernova_chance', 0) / 100,
            star_supernova_mult=self.manual_stats.get('star_supernova_mult', 10.0),
            star_supergiant_chance=self.manual_stats.get('star_supergiant_chance', 0) / 100,
            star_supergiant_mult=self.manual_stats.get('star_supergiant_mult', 3.0),
            super_star_supernova_chance=self.manual_stats.get('super_star_supernova_chance', 0) / 100,
            super_star_supernova_mult=self.manual_stats.get('super_star_supernova_mult', 10.0),
            super_star_supergiant_chance=self.manual_stats.get('super_star_supergiant_chance', 0) / 100,
            super_star_supergiant_mult=self.manual_stats.get('super_star_supergiant_mult', 3.0),
            super_star_radiant_chance=self.manual_stats.get('super_star_radiant_chance', 0) / 100,
            all_star_mult=self.manual_stats.get('all_star_mult', 1.0),
            floor_clears_per_hour=self.floor_clears_per_hour,
        )
        
        calc = StargazingCalculator(stats)
        summary = calc.get_summary()
        
        # Update results
        self.result_labels['star_spawns'].config(text=f"{summary['star_spawn_rate_per_hour']:.1f}")
        self.result_labels['stars_per_hour'].config(text=f"{summary['stars_per_hour']:.1f}")
        self.result_labels['auto_stars'].config(text=f"{summary['auto_caught_stars_per_hour']:.1f}")
        self.result_labels['ss_spawns'].config(text=f"{summary['super_star_spawn_rate_per_hour']:.2f}")
        self.result_labels['super_stars_per_hour'].config(text=f"{summary['super_stars_per_hour']:.2f}")
        self.result_labels['auto_super'].config(text=f"{summary['auto_caught_super_stars_per_hour']:.2f}")
        self.result_labels['star_mult'].config(text=f"{summary['star_multiplier']:.2f}x")
        self.result_labels['super_mult'].config(text=f"{summary['super_star_multiplier']:.2f}x")
        
        # Calculate next upgrade benefits for each upgrade
        self.update_upgrade_benefits(calc, summary)
    
    def update_upgrade_benefits(self, calc: StargazingCalculator, current_summary: dict):
        """Calculate and display the benefit of +1 for each upgrade"""
        
        current_stars = current_summary['stars_per_hour']
        current_super = current_summary['super_stars_per_hour']
        
        # Mapping upgrade key to the stat it affects
        upgrade_effects = {
            'auto_catch': ('auto_catch_chance', 0.04, 'stars'),
            'star_spawn_rate': ('star_spawn_rate_mult', 0.05, 'stars'),
            'double_star_chance': ('double_star_chance', 0.05, 'stars'),
            'super_star_spawn_rate': ('super_star_spawn_rate_mult', 0.02, 'super'),
            'star_supernova_chance': ('star_supernova_chance', 0.005, 'stars'),
            'super_star_10x_chance': ('super_star_10x_chance', 0.002, 'super'),
            'star_supergiant_chance': ('star_supergiant_chance', 0.002, 'stars'),
            'super_star_supergiant_chance': ('super_star_supergiant_chance', 0.0015, 'super'),
            'all_star_multiplier': ('all_star_mult', 0.01, 'both'),
            'super_star_radiant_chance': ('super_star_radiant_chance', 0.0015, 'super'),
        }
        
        for key, benefit_label in self.upgrade_benefit_labels.items():
            current_level = self.stargazing_upgrades.get(key, 0)
            max_level = STARGAZING_UPGRADES.get(key, {}).get('max_level', 0)
            
            if current_level >= max_level:
                benefit_label.config(text="MAX", fg="#888")
                continue
            
            if key not in upgrade_effects:
                benefit_label.config(text="")
                continue
            
            stat_key, effect_per_level, affects = upgrade_effects[key]
            
            # Simulate +1 upgrade
            import copy
            new_stats = copy.copy(calc.stats)
            
            # Apply the upgrade effect
            if stat_key == 'auto_catch_chance':
                new_stats.auto_catch_chance += effect_per_level
            elif stat_key == 'star_spawn_rate_mult':
                new_stats.star_spawn_rate_mult += effect_per_level
            elif stat_key == 'double_star_chance':
                new_stats.double_star_chance += effect_per_level
            elif stat_key == 'super_star_spawn_rate_mult':
                new_stats.super_star_spawn_rate_mult += effect_per_level
            elif stat_key == 'star_supernova_chance':
                new_stats.star_supernova_chance += effect_per_level
            elif stat_key == 'super_star_10x_chance':
                new_stats.super_star_10x_chance += effect_per_level
            elif stat_key == 'star_supergiant_chance':
                new_stats.star_supergiant_chance += effect_per_level
            elif stat_key == 'super_star_supergiant_chance':
                new_stats.super_star_supergiant_chance += effect_per_level
            elif stat_key == 'all_star_mult':
                new_stats.all_star_mult += effect_per_level
            elif stat_key == 'super_star_radiant_chance':
                new_stats.super_star_radiant_chance += effect_per_level
            
            new_calc = StargazingCalculator(new_stats)
            new_stars = new_calc.calculate_stars_per_hour()
            new_super = new_calc.calculate_super_stars_per_hour()
            
            # Calculate percentage gain
            if affects == 'stars' and current_stars > 0:
                gain_pct = ((new_stars - current_stars) / current_stars) * 100
                benefit_label.config(text=f"+{gain_pct:.2f}% Stars", fg="#2E7D32")
            elif affects == 'super' and current_super > 0:
                gain_pct = ((new_super - current_super) / current_super) * 100
                benefit_label.config(text=f"+{gain_pct:.2f}% Super", fg="#E65100")
            elif affects == 'both':
                star_gain = ((new_stars - current_stars) / current_stars) * 100 if current_stars > 0 else 0
                super_gain = ((new_super - current_super) / current_super) * 100 if current_super > 0 else 0
                benefit_label.config(text=f"+{star_gain:.2f}%/+{super_gain:.2f}%", fg="#6A1B9A")
            else:
                benefit_label.config(text="", fg="#888")
