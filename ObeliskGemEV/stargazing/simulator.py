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

import sys
import os
sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import calculate_tooltip_position, get_resource_path


def get_user_data_path() -> Path:
    """Get path for user data (saves) - persists outside of bundle."""
    if getattr(sys, 'frozen', False):
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        save_dir = Path(app_data) / 'ObeliskGemEV' / 'save'
    else:
        save_dir = Path(__file__).parent.parent / 'save'
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


# Save file path
SAVE_DIR = get_user_data_path()
SAVE_FILE = SAVE_DIR / "stargazing_save.json"

# Section colors
COLOR_STATS = "#E8F5E9"      # Light Green for Stats input
COLOR_UPGRADES = "#E3F2FD"   # Light Blue for Upgrades
COLOR_STARS = "#E8EAF6"      # Light Indigo for Stars
COLOR_RESULTS = "#FFF3E0"    # Light Orange for Results


class StargazingWindow:
    """Window for Stargazing optimization and tracking"""
    
    # Version marker to force reload
    _version = "2.0"
    
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
            icon_path = get_resource_path("sprites/stargazing/stargazing.png")
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image, master=self.window)
                self.window.iconphoto(False, icon_photo)
                self.icon_photo = icon_photo
        except:
            pass
        
        # Load sprite icons
        self.load_sprites()
        
        # Initialize state
        self.reset_to_defaults()
        
        # Initialize update debouncing
        self._update_pending = None
        
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
        
        # Upgrade sprites
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
        
        # Star icons
        star_sprites = {
            'aries': 'Aries.png',
            'taurus': 'Taurus.png',
            'gemini': 'Gemini.png',
            'cancer': 'Cancer.png',
            'leo': 'Leo.png',
            'virgo': 'Virgo.png',
            'libra': 'Libra.png',
            'scorpio': 'Scorpio.png',
            'sagittarius': 'Sagittarius.png',
            'capricorn': 'Capricorn.png',
            'aquarius': 'Aquarius.png',
            'pisces': 'Pisces.png',
            'ophiuchus': 'Ophiuchus.png',
            'orion': 'Orion.png',
            'hercules': 'Hercules.png',
            'draco': 'Draco.png',
            'cetus': 'Cetus.png',
            'phoenix': 'Phoenix.png',
            'eridanus': 'Eridanus.png',
        }
        
        # Generic star/super star icons
        generic_sprites = {
            'star_generic': 'star.png',
            'super_star_generic': 'super_star.png',
        }
        
        sprites_dir = get_resource_path("sprites/stargazing")
        
        # Load upgrade sprites (18x18)
        for key, filename in sprite_files.items():
            try:
                path = sprites_dir / filename
                if path.exists():
                    img = Image.open(path)
                    img = img.resize((18, 18), Image.Resampling.LANCZOS)
                    # Use window as master to ensure image is associated with the correct root
                    self.sprites[key] = ImageTk.PhotoImage(img, master=self.window)
            except:
                pass
        
        # Load star sprites (16x16)
        for key, filename in star_sprites.items():
            try:
                path = sprites_dir / filename
                if path.exists():
                    img = Image.open(path)
                    img = img.resize((16, 16), Image.Resampling.LANCZOS)
                    # Use window as master to ensure image is associated with the correct root
                    self.sprites[f'star_{key}'] = ImageTk.PhotoImage(img, master=self.window)
            except:
                pass
        
        # Load generic star/super star icons (16x16)
        for key, filename in generic_sprites.items():
            try:
                path = sprites_dir / filename
                if path.exists():
                    img = Image.open(path)
                    img = img.resize((16, 16), Image.Resampling.LANCZOS)
                    # Use window as master to ensure image is associated with the correct root
                    self.sprites[key] = ImageTk.PhotoImage(img, master=self.window)
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
        
        # Floor clears input (floors + time -> floors/h)
        self.floors_cleared = 120
        self.time_hours = 1
        self.time_minutes = 0
        self.time_seconds = 0
        self.floor_clears_per_hour = 120.0
        
        # CTRL+F Stars skill (multiplies offline gains by 5x)
        self.ctrl_f_stars_enabled = False
        
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
        # Update manual_stats from current UI values before saving
        if hasattr(self, 'stat_vars'):
            for key, var in self.stat_vars.items():
                val = var.get().strip()
                if val:
                    try:
                        self.manual_stats[key] = float(val)
                    except ValueError:
                        pass  # Keep old value if invalid
        
        # Update floor/time values from UI
        if hasattr(self, 'floors_var'):
            try:
                floors_str = self.floors_var.get().strip()
                if floors_str:
                    self.floors_cleared = int(float(floors_str))
            except ValueError:
                pass
        
        if hasattr(self, 'time_h_var'):
            try:
                h_str = self.time_h_var.get().strip()
                self.time_hours = int(h_str) if h_str and h_str.isdigit() else self.time_hours
            except ValueError:
                pass
        
        if hasattr(self, 'time_m_var'):
            try:
                m_str = self.time_m_var.get().strip()
                self.time_minutes = int(m_str) if m_str and m_str.isdigit() else self.time_minutes
            except ValueError:
                pass
        
        if hasattr(self, 'time_s_var'):
            try:
                s_str = self.time_s_var.get().strip()
                self.time_seconds = int(s_str) if s_str and s_str.isdigit() else self.time_seconds
            except ValueError:
                pass
        
        # Update CTRL+F Stars from checkbox
        if hasattr(self, 'ctrl_f_stars_var'):
            self.ctrl_f_stars_enabled = self.ctrl_f_stars_var.get()
        
        state = {
            'manual_stats': self.manual_stats,
            'floors_cleared': self.floors_cleared,
            'time_hours': self.time_hours,
            'time_minutes': self.time_minutes,
            'time_seconds': self.time_seconds,
            'stargazing_upgrades': self.stargazing_upgrades,
            'super_star_upgrades': self.super_star_upgrades,
            'stars_owned': self.stars_owned,
            'star_levels': self.star_levels,
            'ctrl_f_stars_enabled': self.ctrl_f_stars_enabled,
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
            
            # Load floor/time values
            self.floors_cleared = state.get('floors_cleared', 120)
            self.time_hours = state.get('time_hours', 1)
            self.time_minutes = state.get('time_minutes', 0)
            self.time_seconds = state.get('time_seconds', 0)
            self._calculate_floors_per_hour()
            
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
            
            # Load CTRL+F Stars skill
            self.ctrl_f_stars_enabled = state.get('ctrl_f_stars_enabled', False)
            
            # Update UI
            self.update_ui_from_state()
            
            # Trigger calculation after loading state
            self.window.after(100, self.update_calculations)
            
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
    
    def _calculate_floors_per_hour(self):
        """Calculate floors per hour from floors and time inputs"""
        total_hours = self.time_hours + self.time_minutes / 60 + self.time_seconds / 3600
        if total_hours > 0:
            self.floor_clears_per_hour = self.floors_cleared / total_hours
        else:
            self.floor_clears_per_hour = 0.0
    
    def update_ui_from_state(self):
        """Update UI elements to reflect current state"""
        # Update manual stat entries
        if hasattr(self, 'stat_vars'):
            for key, var in self.stat_vars.items():
                var.set(str(self.manual_stats.get(key, 0)))
        
        # Update floor/time inputs
        if hasattr(self, 'floors_var'):
            self.floors_var.set(str(self.floors_cleared))
        if hasattr(self, 'time_h_var'):
            self.time_h_var.set(str(self.time_hours))
        if hasattr(self, 'time_m_var'):
            self.time_m_var.set(str(self.time_minutes))
        if hasattr(self, 'time_s_var'):
            self.time_s_var.set(str(self.time_seconds))
        
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
        
        # Update CTRL+F Stars checkbox
        if hasattr(self, 'ctrl_f_stars_var'):
            self.ctrl_f_stars_var.set(self.ctrl_f_stars_enabled)
    
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main container
        main_frame = ttk.Frame(self.window, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        try:
            icon_path = get_resource_path("sprites/stargazing/stargazing.png")
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_image = icon_image.resize((24, 24), Image.Resampling.LANCZOS)
                # Use window as master to ensure image is associated with the correct root
                self.title_icon = ImageTk.PhotoImage(icon_image, master=self.window)
                tk.Label(title_frame, image=self.title_icon).pack(side=tk.LEFT, padx=(0, 8))
        except:
            pass
        
        ttk.Label(title_frame, text="Stargazing Optimizer", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # Main horizontal layout
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Left: Manual Stats Input
        self.create_stats_section(content_frame)
        
        # Right: Results
        self.create_results_section(content_frame)
    
    def create_stats_section(self, parent):
        """Create the manual stats input section"""
        
        container = tk.Frame(parent, background=COLOR_STATS, relief=tk.RIDGE, borderwidth=2)
        container.grid(row=0, column=0, sticky="nsew", padx=(0, 3), pady=0)
        
        # Header with help tooltip
        header = tk.Frame(container, background=COLOR_STATS)
        header.pack(fill=tk.X, padx=5, pady=(5, 3))
        tk.Label(header, text="YOUR STATS (from game)", font=("Arial", 11, "bold"), 
                 background=COLOR_STATS).pack(side=tk.LEFT)
        
        # Help button with tooltip
        help_label = tk.Label(header, text="?", font=("Arial", 10, "bold"), 
                              cursor="hand2", foreground="#1565C0", background=COLOR_STATS)
        help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_stats_help_tooltip(help_label)
        
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
        
        # Configure grid columns for proper alignment
        stats_frame.columnconfigure(0, weight=0, minsize=20)  # Icon column
        stats_frame.columnconfigure(1, weight=1, minsize=140)  # Label column
        stats_frame.columnconfigure(2, weight=0, minsize=70)    # Entry column
        stats_frame.columnconfigure(3, weight=0, minsize=20)    # Suffix column
        
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
        
        row = 0
        for key, label, suffix, sprite_key, is_separator in stats_config:
            if key.startswith('_header'):
                # Section header - span all columns
                ttk.Separator(stats_frame, orient='horizontal').grid(row=row, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(8, 3), padx=2)
                row += 1
                tk.Label(stats_frame, text=label, font=("Arial", 9, "bold"), 
                         background=COLOR_STATS, fg="#2E7D32").grid(row=row, column=0, columnspan=4, sticky=tk.W, padx=2)
                row += 1
                continue
            
            # Icon if available
            if sprite_key and sprite_key in self.sprites:
                tk.Label(stats_frame, image=self.sprites[sprite_key], background=COLOR_STATS).grid(
                    row=row, column=0, sticky=tk.W, padx=(0, 3))
            else:
                # Empty space for alignment when no icon
                tk.Label(stats_frame, text="", background=COLOR_STATS, width=2).grid(
                    row=row, column=0, sticky=tk.W)
            
            # Label
            tk.Label(stats_frame, text=f"{label}:", background=COLOR_STATS, 
                     font=("Arial", 9), anchor=tk.W).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
            
            # Entry
            var = tk.StringVar(value=str(self.manual_stats.get(key, 0)))
            self.stat_vars[key] = var
            entry = ttk.Entry(stats_frame, textvariable=var, width=8, font=("Arial", 10))
            entry.grid(row=row, column=2, sticky=tk.W, padx=2)
            # Live calculation on any change
            var.trace_add('write', self._schedule_update)
            # Also bind key events as backup
            entry.bind('<KeyRelease>', self._schedule_update)
            entry.bind('<FocusOut>', self._schedule_update)
            self.stat_entries[key] = entry
            
            # Suffix
            tk.Label(stats_frame, text=suffix, background=COLOR_STATS, 
                     font=("Arial", 9), fg="gray").grid(row=row, column=3, sticky=tk.W, padx=(2, 0))
            
            row += 1
        
        # Floor clears section
        ttk.Separator(stats_frame, orient='horizontal').grid(row=row, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 5), padx=2)
        row += 1
        
        floor_header = tk.Frame(stats_frame, background=COLOR_STATS)
        floor_header.grid(row=row, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=2)
        tk.Label(floor_header, text="OFFLINE GAINS INPUT", font=("Arial", 9, "bold"), 
                 background=COLOR_STATS, fg="#1565C0").pack(side=tk.LEFT)
        
        # Help tooltip for floor input
        floor_help = tk.Label(floor_header, text="?", font=("Arial", 9, "bold"), 
                              cursor="hand2", foreground="#1565C0", background=COLOR_STATS)
        floor_help.pack(side=tk.LEFT, padx=(5, 0))
        self._create_floor_input_tooltip(floor_help)
        row += 1
        
        # Floors input
        tk.Label(stats_frame, text="Floors cleared:", background=COLOR_STATS, 
                 font=("Arial", 9), anchor=tk.W).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.floors_var = tk.StringVar(value=str(self.floors_cleared))
        floors_entry = ttk.Entry(stats_frame, textvariable=self.floors_var, width=8, font=("Arial", 10))
        floors_entry.grid(row=row, column=2, sticky=tk.W, padx=2)
        # Live calculation on any change
        self.floors_var.trace_add('write', self._schedule_update)
        floors_entry.bind('<KeyRelease>', self._schedule_update)
        floors_entry.bind('<FocusOut>', self._schedule_update)
        row += 1
        
        # Time input (h m s)
        tk.Label(stats_frame, text="Time:", background=COLOR_STATS, 
                 font=("Arial", 9), anchor=tk.W).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        time_entry_frame = tk.Frame(stats_frame, background=COLOR_STATS)
        time_entry_frame.grid(row=row, column=2, sticky=tk.W, padx=2)
        
        # Hours
        self.time_h_var = tk.StringVar(value=str(self.time_hours))
        h_entry = ttk.Entry(time_entry_frame, textvariable=self.time_h_var, width=3, font=("Arial", 10))
        h_entry.pack(side=tk.LEFT)
        self.time_h_var.trace_add('write', self._schedule_update)
        h_entry.bind('<KeyRelease>', self._schedule_update)
        h_entry.bind('<FocusOut>', self._schedule_update)
        tk.Label(time_entry_frame, text="h", background=COLOR_STATS, font=("Arial", 9)).pack(side=tk.LEFT, padx=(1, 5))
        
        # Minutes
        self.time_m_var = tk.StringVar(value=str(self.time_minutes))
        m_entry = ttk.Entry(time_entry_frame, textvariable=self.time_m_var, width=3, font=("Arial", 10))
        m_entry.pack(side=tk.LEFT)
        self.time_m_var.trace_add('write', self._schedule_update)
        m_entry.bind('<KeyRelease>', self._schedule_update)
        m_entry.bind('<FocusOut>', self._schedule_update)
        tk.Label(time_entry_frame, text="m", background=COLOR_STATS, font=("Arial", 9)).pack(side=tk.LEFT, padx=(1, 5))
        
        # Seconds
        self.time_s_var = tk.StringVar(value=str(self.time_seconds))
        s_entry = ttk.Entry(time_entry_frame, textvariable=self.time_s_var, width=3, font=("Arial", 10))
        s_entry.pack(side=tk.LEFT)
        self.time_s_var.trace_add('write', self._schedule_update)
        s_entry.bind('<KeyRelease>', self._schedule_update)
        s_entry.bind('<FocusOut>', self._schedule_update)
        tk.Label(time_entry_frame, text="s", background=COLOR_STATS, font=("Arial", 9)).pack(side=tk.LEFT, padx=(1, 0))
        row += 1
        
        # Calculated floors/hour display
        tk.Label(stats_frame, text="= Floors/hour:", background=COLOR_STATS, 
                 font=("Arial", 9, "bold"), anchor=tk.W).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.floors_per_hour_label = tk.Label(stats_frame, text=f"{self.floor_clears_per_hour:.2f}", 
                                               background=COLOR_STATS, font=("Arial", 10, "bold"), fg="#1565C0")
        self.floors_per_hour_label.grid(row=row, column=2, sticky=tk.W, padx=2)
        row += 1
        
        # CTRL+F Stars skill checkbox
        ttk.Separator(stats_frame, orient='horizontal').grid(row=row, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 5), padx=2)
        row += 1
        
        ctrl_f_header = tk.Frame(stats_frame, background=COLOR_STATS)
        ctrl_f_header.grid(row=row, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=2)
        tk.Label(ctrl_f_header, text="CTRL+F Stars Skill", font=("Arial", 9, "bold"), 
                 background=COLOR_STATS, fg="#1565C0").pack(side=tk.LEFT)
        
        # Help tooltip for CTRL+F Stars
        ctrl_f_help = tk.Label(ctrl_f_header, text="?", font=("Arial", 9, "bold"), 
                              cursor="hand2", foreground="#1565C0", background=COLOR_STATS)
        ctrl_f_help.pack(side=tk.LEFT, padx=(5, 0))
        self._create_ctrl_f_help_tooltip(ctrl_f_help)
        row += 1
        
        # Checkbox
        self.ctrl_f_stars_var = tk.BooleanVar(value=self.ctrl_f_stars_enabled)
        ctrl_f_checkbox = ttk.Checkbutton(
            stats_frame,
            text="CTRL+F Stars enabled (5x offline gains)",
            variable=self.ctrl_f_stars_var,
            command=self.on_ctrl_f_changed
        )
        ctrl_f_checkbox.grid(row=row, column=1, columnspan=3, sticky=tk.W, padx=2)
    
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
        self.upgrade_benefit_labels = {}  # Now stores tuples: (star_label, super_label)
        
        # Header row for benefit columns
        header_row = tk.Frame(scrollable, background=COLOR_UPGRADES)
        header_row.pack(fill=tk.X, pady=(0, 3))
        tk.Label(header_row, text="Upgrade", background=COLOR_UPGRADES, 
                 font=("Arial", 8, "bold"), width=28, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(header_row, text="Lvl", background=COLOR_UPGRADES, 
                 font=("Arial", 8, "bold"), width=6).pack(side=tk.LEFT)
        
        # Super Star header with icon
        super_header = tk.Frame(header_row, background=COLOR_UPGRADES)
        super_header.pack(side=tk.RIGHT)
        if 'super_star_generic' in self.sprites:
            tk.Label(super_header, image=self.sprites['super_star_generic'], 
                     background=COLOR_UPGRADES).pack(side=tk.LEFT)
        tk.Label(super_header, text="+%", background=COLOR_UPGRADES, 
                 font=("Arial", 8, "bold"), fg="#E65100", width=5).pack(side=tk.LEFT)
        
        # Star header with icon
        star_header = tk.Frame(header_row, background=COLOR_UPGRADES)
        star_header.pack(side=tk.RIGHT, padx=(0, 5))
        if 'star_generic' in self.sprites:
            tk.Label(star_header, image=self.sprites['star_generic'], 
                     background=COLOR_UPGRADES).pack(side=tk.LEFT)
        tk.Label(star_header, text="+%", background=COLOR_UPGRADES, 
                 font=("Arial", 8, "bold"), fg="#1565C0", width=5).pack(side=tk.LEFT)
        
        ttk.Separator(scrollable, orient='horizontal').pack(fill=tk.X, pady=2)
        
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
                     font=("Arial", 8), width=22, anchor=tk.W).pack(side=tk.LEFT)
            
            # - Button
            minus_btn = tk.Button(row, text="-", width=2, font=("Arial", 7, "bold"), 
                                  command=lambda k=key: self.change_upgrade(k, -1))
            minus_btn.pack(side=tk.LEFT, padx=1)
            
            # Level label
            level_label = tk.Label(row, text=str(self.stargazing_upgrades.get(key, 0)), 
                                   background=COLOR_UPGRADES, font=("Arial", 9, "bold"), width=3)
            level_label.pack(side=tk.LEFT)
            self.upgrade_level_labels[key] = level_label
            
            # + Button
            plus_btn = tk.Button(row, text="+", width=2, font=("Arial", 7, "bold"),
                                command=lambda k=key: self.change_upgrade(k, 1))
            plus_btn.pack(side=tk.LEFT, padx=1)
            
            # Max level
            tk.Label(row, text=f"/{upgrade['max_level']}", background=COLOR_UPGRADES, 
                     font=("Arial", 8), fg="gray").pack(side=tk.LEFT)
            
            # Super Star benefit label (right-most)
            super_benefit_label = tk.Label(row, text="", background=COLOR_UPGRADES, 
                                           font=("Arial", 8, "bold"), fg="#E65100", width=8)
            super_benefit_label.pack(side=tk.RIGHT)
            
            # Star benefit label
            star_benefit_label = tk.Label(row, text="", background=COLOR_UPGRADES, 
                                          font=("Arial", 8, "bold"), fg="#1565C0", width=8)
            star_benefit_label.pack(side=tk.RIGHT)
            
            self.upgrade_benefit_labels[key] = (star_benefit_label, super_benefit_label)
    
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
            
            # Star icon
            sprite_key = f'star_{key}'
            if sprite_key in self.sprites:
                tk.Label(row, image=self.sprites[sprite_key], background=COLOR_STARS).pack(side=tk.LEFT, padx=(0, 3))
            
            # Name
            tk.Label(row, text=star.name, background=COLOR_STARS, 
                     font=("Arial", 10), width=10, anchor=tk.W).pack(side=tk.LEFT)
            
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
        container.grid(row=0, column=1, sticky="nsew", padx=(3, 0), pady=0)
        
        # Header
        header = tk.Frame(container, background=COLOR_RESULTS)
        header.pack(fill=tk.X, padx=5, pady=(5, 3))
        tk.Label(header, text="RESULTS", font=("Arial", 11, "bold"), background=COLOR_RESULTS).pack(side=tk.LEFT)
        
        results_frame = tk.Frame(container, background=COLOR_RESULTS)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.result_labels = {}
        
        # Star Results
        star_header = tk.Frame(results_frame, background=COLOR_RESULTS)
        star_header.pack(fill=tk.X, pady=(0, 5))
        tk.Label(star_header, text="⭐ Star Income", font=("Arial", 11, "bold"), 
                 background=COLOR_RESULTS, fg="#1565C0").pack(side=tk.LEFT)
        
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
        
        # Auto-catch efficiency row
        eff_row = tk.Frame(results_frame, background=COLOR_RESULTS)
        eff_row.pack(fill=tk.X, pady=1)
        tk.Label(eff_row, text="  Auto-Catch Efficiency:", background=COLOR_RESULTS, 
                 font=("Arial", 9)).pack(side=tk.LEFT)
        self.result_labels['auto_efficiency'] = tk.Label(eff_row, text="—", background=COLOR_RESULTS, 
                                                          font=("Arial", 10, "bold"), fg="#6A1B9A")
        self.result_labels['auto_efficiency'].pack(side=tk.RIGHT)
        
        # Help for auto efficiency
        eff_help = tk.Label(eff_row, text="?", font=("Arial", 9, "bold"), 
                            cursor="hand2", foreground="#6A1B9A", background=COLOR_RESULTS)
        eff_help.pack(side=tk.RIGHT, padx=(0, 5))
        self._create_auto_efficiency_tooltip(eff_help)
        
        # Super Star Results
        ttk.Separator(results_frame, orient='horizontal').pack(fill=tk.X, pady=8)
        super_header = tk.Frame(results_frame, background=COLOR_RESULTS)
        super_header.pack(fill=tk.X, pady=(0, 5))
        tk.Label(super_header, text="🌟 Super Star Income", font=("Arial", 11, "bold"), 
                 background=COLOR_RESULTS, fg="#E65100").pack(side=tk.LEFT)
        
        # Help button for Super Star spawn info
        ss_help = tk.Label(super_header, text="?", font=("Arial", 10, "bold"), 
                           cursor="hand2", foreground="#E65100", background=COLOR_RESULTS)
        ss_help.pack(side=tk.LEFT, padx=(5, 0))
        self._create_super_star_help_tooltip(ss_help)
        
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
        
        # Super Star auto efficiency
        ss_eff_row = tk.Frame(results_frame, background=COLOR_RESULTS)
        ss_eff_row.pack(fill=tk.X, pady=1)
        tk.Label(ss_eff_row, text="  Auto-Catch Efficiency:", background=COLOR_RESULTS, 
                 font=("Arial", 9)).pack(side=tk.LEFT)
        self.result_labels['auto_efficiency_super'] = tk.Label(ss_eff_row, text="—", background=COLOR_RESULTS, 
                                                                font=("Arial", 10, "bold"), fg="#6A1B9A")
        self.result_labels['auto_efficiency_super'].pack(side=tk.RIGHT)
        
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
    
    def _schedule_update(self, *args):
        """Schedule an update with debouncing to avoid excessive recalculations"""
        # Initialize if not exists
        if not hasattr(self, '_update_pending'):
            self._update_pending = None
        
        # Cancel any pending update
        if self._update_pending is not None:
            try:
                self.window.after_cancel(self._update_pending)
            except:
                pass
        
        # Schedule new update after 200ms delay (debounce)
        self._update_pending = self.window.after(200, self._do_live_update)
    
    def _do_live_update(self):
        """Perform the actual live update"""
        self._update_pending = None
        self.update_calculations()
        
        # Update floors/hour display
        if hasattr(self, 'floors_per_hour_label'):
            try:
                self.floors_per_hour_label.config(text=f"{self.floor_clears_per_hour:.2f}")
            except:
                pass
    
    def on_ctrl_f_changed(self):
        """Handle CTRL+F Stars checkbox change"""
        if hasattr(self, 'ctrl_f_stars_var'):
            self.ctrl_f_stars_enabled = self.ctrl_f_stars_var.get()
        self.update_calculations()
    
    def update_calculations(self):
        """Recalculate and update display"""
        # Check if result labels exist
        if not hasattr(self, 'result_labels'):
            return
        
        # Read all values directly from UI entries
        manual_stats = {}
        if hasattr(self, 'stat_vars'):
            for key, var in self.stat_vars.items():
                try:
                    val = var.get().strip()
                    if val:
                        manual_stats[key] = float(val)
                    else:
                        manual_stats[key] = self.manual_stats.get(key, 0)
                except (ValueError, AttributeError):
                    manual_stats[key] = self.manual_stats.get(key, 0)
        
        # Update floor/time values from UI
        if hasattr(self, 'floors_var'):
            try:
                floors_str = self.floors_var.get().strip()
                if floors_str:
                    self.floors_cleared = int(float(floors_str))
            except (ValueError, AttributeError):
                pass
        
        if hasattr(self, 'time_h_var'):
            try:
                h_str = self.time_h_var.get().strip()
                if h_str and h_str.isdigit():
                    self.time_hours = int(h_str)
            except (ValueError, AttributeError):
                pass
        
        if hasattr(self, 'time_m_var'):
            try:
                m_str = self.time_m_var.get().strip()
                if m_str and m_str.isdigit():
                    self.time_minutes = int(m_str)
            except (ValueError, AttributeError):
                pass
        
        if hasattr(self, 'time_s_var'):
            try:
                s_str = self.time_s_var.get().strip()
                if s_str and s_str.isdigit():
                    self.time_seconds = int(s_str)
            except (ValueError, AttributeError):
                pass
        
        # Calculate floors per hour
        self._calculate_floors_per_hour()
        
        # Update CTRL+F Stars from checkbox
        if hasattr(self, 'ctrl_f_stars_var'):
            self.ctrl_f_stars_enabled = self.ctrl_f_stars_var.get()
        
        # Update manual_stats with new values
        self.manual_stats.update(manual_stats)
        
        # Create stats from manual input
        try:
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
                ctrl_f_stars_enabled=self.ctrl_f_stars_enabled,
            )
            
            calc = StargazingCalculator(stats)
            summary = calc.get_summary()
        except Exception as e:
            # On error, show error in results
            import traceback
            print(f"Error in update_calculations: {e}")
            traceback.print_exc()
            for key in self.result_labels:
                if key not in ['auto_efficiency', 'auto_efficiency_super']:
                    self.result_labels[key].config(text="Error")
            return
        
        # Update results
        try:
            self.result_labels['star_spawns'].config(text=f"{summary['star_spawn_rate_per_hour']:.2f}")
            self.result_labels['stars_per_hour'].config(text=f"{summary['stars_per_hour']:.4f}")
            self.result_labels['auto_stars'].config(text=f"{summary['auto_caught_stars_per_hour']:.4f}")
            self.result_labels['ss_spawns'].config(text=f"{summary['super_star_spawn_rate_per_hour']:.4f}")
            self.result_labels['super_stars_per_hour'].config(text=f"{summary['super_stars_per_hour']:.4f}")
            self.result_labels['auto_super'].config(text=f"{summary['auto_caught_super_stars_per_hour']:.4f}")
            self.result_labels['star_mult'].config(text=f"{summary['star_multiplier']:.2f}x")
            self.result_labels['super_mult'].config(text=f"{summary['super_star_multiplier']:.2f}x")
        except KeyError as e:
            print(f"KeyError updating results: {e}")
            print(f"Available keys in summary: {list(summary.keys())}")
            print(f"Available result_labels: {list(self.result_labels.keys())}")
        except Exception as e:
            print(f"Error updating result labels: {e}")
            import traceback
            traceback.print_exc()
        
        # Calculate auto-catch efficiency
        try:
            auto_catch_pct = self.manual_stats.get('auto_catch_chance', 0)
            if auto_catch_pct >= 100:
                self.result_labels['auto_efficiency'].config(text="100% (= manual)", fg="#2E7D32")
                self.result_labels['auto_efficiency_super'].config(text="100% (= manual)", fg="#2E7D32")
            elif auto_catch_pct > 0:
                slowdown = ((100 - auto_catch_pct) / 100) * 100
                self.result_labels['auto_efficiency'].config(
                    text=f"{auto_catch_pct:.1f}% ({slowdown:.1f}% slower)", fg="#E65100")
                self.result_labels['auto_efficiency_super'].config(
                    text=f"{auto_catch_pct:.1f}% ({slowdown:.1f}% slower)", fg="#E65100")
            else:
                self.result_labels['auto_efficiency'].config(text="0% (no auto-catch)", fg="#C62828")
                self.result_labels['auto_efficiency_super'].config(text="0% (no auto-catch)", fg="#C62828")
        except Exception as e:
            print(f"Error updating auto efficiency: {e}")
        
        # Calculate next upgrade benefits for each upgrade (only if upgrade panel exists)
        if hasattr(self, 'upgrade_benefit_labels'):
            try:
                self.update_upgrade_benefits(calc, summary)
            except Exception as e:
                print(f"Error updating upgrade benefits: {e}")
    
    def update_upgrade_benefits(self, calc: StargazingCalculator, current_summary: dict):
        """Calculate and display the benefit of +1 for each upgrade"""
        
        # Skip if upgrade panel is not created
        if not hasattr(self, 'upgrade_benefit_labels'):
            return
        
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
        
        import copy
        
        for key, benefit_labels in self.upgrade_benefit_labels.items():
            star_label, super_label = benefit_labels
            current_level = self.stargazing_upgrades.get(key, 0)
            max_level = STARGAZING_UPGRADES.get(key, {}).get('max_level', 0)
            
            if current_level >= max_level:
                star_label.config(text="MAX", fg="#888")
                super_label.config(text="MAX", fg="#888")
                continue
            
            if key not in upgrade_effects:
                star_label.config(text="—")
                super_label.config(text="—")
                continue
            
            stat_key, effect_per_level, _ = upgrade_effects[key]
            
            # Simulate +1 upgrade
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
            
            # Calculate percentage gains for both Stars and Super Stars
            if current_stars > 0:
                star_gain = ((new_stars - current_stars) / current_stars) * 100
                star_label.config(text=f"+{star_gain:.2f}%", fg="#1565C0")
            else:
                star_label.config(text="—", fg="#888")
            
            if current_super > 0:
                super_gain = ((new_super - current_super) / current_super) * 100
                super_label.config(text=f"+{super_gain:.2f}%", fg="#E65100")
            else:
                super_label.config(text="—", fg="#888")
    
    def _create_tooltip(self, widget, title, lines, title_color="#1565C0"):
        """Generic tooltip creator"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 320
            tooltip_height = 50 + len(lines) * 18
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background=title_color, relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text=title, font=("Arial", 10, "bold"), 
                     foreground=title_color, background="#FFFFFF").pack(anchor=tk.W)
            
            for line in lines:
                tk.Label(content_frame, text=line, font=("Arial", 9), 
                         background="#FFFFFF", anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _create_stats_help_tooltip(self, widget):
        """Tooltip explaining the stats input section"""
        lines = [
            "",
            "Enter your current stats from the game's",
            "Stats page. These values come from multiple",
            "sources (stars, upgrades, items, etc).",
            "",
            "BASE SPAWN RATES:",
            "  Star spawn: 1/50 (2%) per floor clear",
            "  At each spawn: either Super Star OR Regular",
            "  Super Star: 1/100 (1%) per spawn event",
            "",
            "IMPORTANT: Super Star and Double/Triple Star",
            "spawns are EXCLUSIVE. If Super Star spawns,",
            "no Double/Triple. If Double/Triple spawns,",
            "no Super Star.",
            "",
            "Example at 120 floors/h with 1.0x rates:",
            "  Spawns: 120 × 2% = 2.4 spawns/h",
            "  Super Stars: 2.4 × 1% = 0.024 spawns/h",
            "  Regular Stars: 2.4 × 99% = 2.376 spawns/h",
            "",
            "Multiplier values (x): Enter as shown",
            "  Example: 1.16 for 1.16x",
            "",
            "Percentage values (%): Enter as shown",
            "  Example: 25 for 25%",
        ]
        self._create_tooltip(widget, "Stats Input Help", lines, "#2E7D32")
    
    def _create_super_star_help_tooltip(self, widget):
        """Tooltip explaining Super Star spawn mechanics"""
        lines = [
            "",
            "At each star spawn event, either:",
            "  • A Super Star spawns (exclusive)",
            "  • OR a Regular Star spawns (can be single/double/triple)",
            "",
            "Base chance: 1/100 (1%) per spawn event",
            "",
            "This is multiplied by your Super Star Spawn",
            "Rate multiplier from upgrades.",
            "",
            "IMPORTANT: Super Star spawns are EXCLUSIVE",
            "with Double/Triple Star spawns. If a Super",
            "Star spawns, there is no Double/Triple Star,",
            "and vice versa.",
            "",
            "Example: With 1.5x Super Star Spawn Rate:",
            "  SS chance = 1% × 1.5 = 1.5% per spawn",
            "  Regular chance = 98.5% per spawn",
            "  (Double/Triple only applies to regular)",
        ]
        self._create_tooltip(widget, "Super Star Spawn Mechanics", lines, "#E65100")
    
    def _create_floor_input_tooltip(self, widget):
        """Tooltip explaining the floor/time input"""
        lines = [
            "",
            "Enter data from your Offline Gains screen.",
            "",
            "Example: If offline gains says:",
            "  '2,400 floors in 2h 30m'",
            "",
            "Enter:",
            "  Floors: 2400",
            "  Time: 2h 30m 0s",
            "",
            "The calculator will compute:",
            "  2400 / 2.5h = 960 floors/hour",
        ]
        self._create_tooltip(widget, "Offline Gains Input", lines, "#1565C0")
    
    def _create_auto_efficiency_tooltip(self, widget):
        """Tooltip explaining auto-catch efficiency"""
        lines = [
            "",
            "Shows how efficient your auto-catch is",
            "compared to manually tapping every star.",
            "",
            "100% = Same as manual (all stars caught)",
            "",
            "Example: 60% auto-catch means you get 60%",
            "of the stars you would get manually,",
            "which is 40% slower than manual tapping.",
            "",
            "To reach 100%, you need 100% Auto-Catch",
            "from upgrades, stars, and other sources.",
        ]
        self._create_tooltip(widget, "Auto-Catch Efficiency", lines, "#6A1B9A")
    
    def _create_ctrl_f_help_tooltip(self, widget):
        """Tooltip explaining CTRL+F Stars skill"""
        lines = [
            "",
            "CTRL+F Stars skill multiplies offline gains",
            "by 5x for both Stars and Super Stars.",
            "",
            "MECHANICS:",
            "  Each star type spawns on 5 different floors.",
            "  Without CTRL+F: You catch the star on 1 floor",
            "    → Offline gains = auto_catch × spawn_rate × 0.2",
            "",
            "  With CTRL+F: You follow the star through all 5 floors",
            "    → Offline gains = auto_catch × spawn_rate × 1.0",
            "",
            "This applies to both regular Stars and Super Stars.",
        ]
        self._create_tooltip(widget, "CTRL+F Stars Skill", lines, "#1565C0")
