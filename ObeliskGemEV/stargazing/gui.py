"""
Stargazing GUI

Simple interface for calculating stars and super stars per hour
based on in-game stats.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import json
import traceback
from PIL import Image, ImageTk

from .calculator import StargazingCalculator, PlayerStats

import sys
import os
sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import calculate_tooltip_position, get_resource_path
from ui_utils import get_save_dir

# Save file path
SAVE_DIR = get_save_dir()
SAVE_FILE = SAVE_DIR / "stargazing_save.json"

# Section colors
COLOR_STATS = "#E8F5E9"      # Light Green for Stats input
COLOR_RESULTS = "#FFF3E0"    # Light Orange for Results


class StargazingWindow:
    """Window for Stargazing calculations"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Stargazing Calculator · Live")
        self.window.state('zoomed')
        self.window.resizable(True, True)
        self.window.minsize(800, 600)
        
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
        
        # Auto-calculate: debounce with cancel (reset timer on each keystroke)
        self.auto_calculate_enabled = True
        self._after_id = None
        
        # Create widgets
        self.create_widgets()
        
        # Load saved state
        self.load_state()
        
        # Initial calculation (with small delay to ensure widgets are ready)
        self.window.after(100, self.update_calculations)
        
        # Auto-save on close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def load_sprites(self):
        """Load all sprite icons"""
        self.sprites = {}
        
        sprite_files = {
            'auto_catch': 'Auto-Catch_Chance.png',
            'star_spawn_rate': 'Star_Spawn_Rate_Multiplier.png',
            'double_star': 'Star_Double_Spawn_Chance.png',
            'super_star_spawn': 'Super_Star_Spawn_Rate_Multiplier.png',
            'supernova': 'Star_Supernova_Chance.png',
            'super_10x': 'Super_Star_10x_Spawn_Chance.png',
            'supergiant': 'Star_Supergiant_Chance.png',
            'super_supergiant': 'Super_Star_Supergiant_Chance.png',
            'all_star_mult': 'All_Star_Multiplier.png',
            'super_radiant': 'Super_Star_Radiant_Chance.png',
            'ctrl_f_stars': 'Ctrl+F_Stars.png',
        }
        
        sprites_dir = get_resource_path("sprites/stargazing")
        
        for key, filename in sprite_files.items():
            try:
                path = sprites_dir / filename
                if path.exists():
                    img = Image.open(path)
                    img = img.resize((18, 18), Image.Resampling.LANCZOS)
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
            'floor_clears_per_minute': 2.0,  # 120/hour = 2/min
            'star_spawn_rate_mult': 1.0,
            'auto_catch_chance': 0.0,  # As percentage
            'double_star_chance': 0.0,  # As percentage
            'triple_star_chance': 0.0,  # As percentage
            'super_star_spawn_rate_mult': 1.0,
            'triple_super_star_chance': 0.0,  # As percentage
            'super_star_10x_chance': 0.0,  # As percentage
            'star_supernova_chance': 0.0,  # As percentage
            'star_supernova_mult': 10.0,
            'star_supergiant_chance': 0.0,  # As percentage
            'star_supergiant_mult': 3.0,
            'star_radiant_chance': 0.0,  # As percentage
            'star_radiant_mult': 10.0,
            'super_star_supernova_chance': 0.0,  # As percentage
            'super_star_supernova_mult': 10.0,
            'super_star_supergiant_chance': 0.0,  # As percentage
            'super_star_supergiant_mult': 3.0,
            'super_star_radiant_chance': 0.0,  # As percentage
            'super_star_radiant_mult': 10.0,
            'all_star_mult': 1.0,
            'novagiant_combo_mult': 1.0,
        }
        
        # CTRL+F Stars skill
        self.ctrl_f_stars_enabled = False
    
    def save_state(self):
        """Save current state to file"""
        # Update manual_stats from current UI values before saving (read from Entry widgets)
        if hasattr(self, 'stat_entries'):
            for key, entry in self.stat_entries.items():
                val = entry.get().strip()
                if val:
                    try:
                        self.manual_stats[key] = float(val)
                    except ValueError:
                        pass
        
        # Update CTRL+F Stars from checkbox
        if hasattr(self, 'ctrl_f_stars_var'):
            self.ctrl_f_stars_enabled = self.ctrl_f_stars_var.get()
        
        state = {
            'manual_stats': self.manual_stats,
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
            
            # Load CTRL+F Stars skill
            self.ctrl_f_stars_enabled = state.get('ctrl_f_stars_enabled', False)
            
            # Update UI
            self.update_ui_from_state()
            
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
    
    def update_ui_from_state(self):
        """Update UI elements to reflect current state"""
        # Update manual stat entries (update Entry widgets directly)
        if hasattr(self, 'stat_entries'):
            for key, entry in self.stat_entries.items():
                new_value = str(self.manual_stats.get(key, 0))
                entry.delete(0, tk.END)
                entry.insert(0, new_value)
        
        # Update CTRL+F Stars checkbox
        # Update toggle button visual state
        if hasattr(self, 'ctrl_f_toggle_button'):
            self._update_ctrl_f_button_visual()
    
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
                self.title_icon = ImageTk.PhotoImage(icon_image, master=self.window)
                tk.Label(title_frame, image=self.title_icon).pack(side=tk.LEFT, padx=(0, 8))
        except:
            pass
        
        ttk.Label(title_frame, text="Stargazing Calculator", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # Main horizontal layout
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Left: Stats Input
        self.create_stats_section(content_frame)
        
        # Right: Results
        self.create_results_section(content_frame)
    
    def create_stats_section(self, parent):
        """Create the stats input section with thematic tiles"""
        
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
        
        def update_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        stats_frame.bind("<Configure>", update_scrollregion)
        canvas.create_window((0, 0), window=stats_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Update scrollregion when content changes
        canvas.bind('<Configure>', update_scrollregion)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=3)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Configure grid for tiles (2 columns)
        stats_frame.columnconfigure(0, weight=1, uniform="tile")
        stats_frame.columnconfigure(1, weight=1, uniform="tile")
        
        self.stat_entries = {}  # Store Entry widgets directly (no StringVar - see README for why)
        
        # Define thematic tiles
        tiles = [
            # Basic Stats Tile
            {
                'title': 'Basic Stats',
                'color': '#E8F5E9',
                'stats': [
                    ('floor_clears_per_minute', 'Floor Clears/min', '', None),
                    ('star_spawn_rate_mult', 'Star Spawn Rate', 'x', 'star_spawn_rate'),
                    ('auto_catch_chance', 'Auto-Catch', '%', 'auto_catch'),
                ]
            },
            # Star Multipliers Tile
            {
                'title': '⭐ Star Multipliers',
                'color': '#E3F2FD',
                'stats': [
                    ('double_star_chance', 'Double Star', '%', 'double_star'),
                    ('triple_star_chance', 'Triple Star', '%', None),
                    ('star_supernova_chance', 'Star Supernova', '%', 'supernova'),
                    ('star_supernova_mult', 'Supernova Multi', 'x', None),
                    ('star_supergiant_chance', 'Star Supergiant', '%', 'supergiant'),
                    ('star_supergiant_mult', 'Supergiant Multi', 'x', None),
                    ('star_radiant_chance', 'Star Radiant', '%', None),
                    ('star_radiant_mult', 'Radiant Multi', 'x', None),
                ]
            },
            # Super Star Stats Tile
            {
                'title': '🌟 Super Star Stats',
                'color': '#FFF3E0',
                'stats': [
                    ('super_star_spawn_rate_mult', 'Super Star Spawn', 'x', 'super_star_spawn'),
                    ('triple_super_star_chance', 'Triple Super Star', '%', None),
                    ('super_star_10x_chance', 'Super Star 10x', '%', 'super_10x'),
                    ('super_star_supernova_chance', 'Super Star Supernova', '%', 'supernova'),
                    ('super_star_supernova_mult', 'SS Nova Multi', 'x', None),
                    ('super_star_supergiant_chance', 'Super Star Supergiant', '%', 'super_supergiant'),
                    ('super_star_supergiant_mult', 'SS Giant Multi', 'x', None),
                    ('super_star_radiant_chance', 'Super Star Radiant', '%', 'super_radiant'),
                    ('super_star_radiant_mult', 'SS Radiant Multi', 'x', None),
                ]
            },
            # Global Multipliers Tile
            {
                'title': 'Global Multipliers',
                'color': '#F3E5F5',
                'stats': [
                    ('all_star_mult', 'All Star Multi', 'x', 'all_star_mult'),
                    ('novagiant_combo_mult', 'Novagiant Combo Multi', 'x', None),
                ]
            },
        ]
        
        row = 0
        col = 0
        for tile in tiles:
            # Create tile frame
            tile_frame = tk.Frame(stats_frame, background=tile['color'], relief=tk.RIDGE, borderwidth=2)
            tile_frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            
            # Tile header
            header_frame = tk.Frame(tile_frame, background=tile['color'])
            header_frame.pack(fill=tk.X, padx=5, pady=(5, 3))
            tk.Label(header_frame, text=tile['title'], font=("Arial", 10, "bold"), 
                     background=tile['color'], fg="#2E7D32").pack(side=tk.LEFT)
            
            # Stats in tile
            stats_inner = tk.Frame(tile_frame, background=tile['color'])
            stats_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            for key, label, suffix, sprite_key in tile['stats']:
                stat_row = tk.Frame(stats_inner, background=tile['color'])
                stat_row.pack(fill=tk.X, pady=2)
                
                # Icon if available
                if sprite_key and sprite_key in self.sprites:
                    tk.Label(stat_row, image=self.sprites[sprite_key], background=tile['color']).pack(side=tk.LEFT, padx=(0, 5))
                
                # Label
                tk.Label(stat_row, text=f"{label}:", background=tile['color'], 
                         font=("Arial", 9), anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
                
                # Entry field - use Entry widget directly (no StringVar)
                # NOTE: ttk.Entry with textvariable=StringVar has binding issues where StringVar
                # doesn't update when users type. Solution: read directly from Entry widget.
                default_value = str(self.manual_stats.get(key, 0))
                entry = ttk.Entry(stat_row, width=8, font=("Arial", 9))
                entry.insert(0, default_value)  # Set initial value
                entry.pack(side=tk.LEFT, padx=2)
                
                # Store Entry widget directly (read with entry.get() instead of var.get())
                self.stat_entries[key] = entry
                
                # Live-Update: Trigger auto-calculate when user types (with debounce)
                entry.bind('<KeyRelease>', lambda e: self.trigger_auto_calculate())
                
                # Suffix
                if suffix:
                    tk.Label(stat_row, text=suffix, background=tile['color'], 
                             font=("Arial", 9), fg="gray").pack(side=tk.LEFT, padx=(2, 0))
            
            # Move to next position
            col += 1
            if col >= 2:
                col = 0
                row += 1
        
        # CTRL+F Stars skill tile (full width)
        if col > 0:
            row += 1
            col = 0
        
        ctrl_f_tile = tk.Frame(stats_frame, background="#E1F5FE", relief=tk.RIDGE, borderwidth=2)
        ctrl_f_tile.grid(row=row, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        ctrl_f_header = tk.Frame(ctrl_f_tile, background="#E1F5FE")
        ctrl_f_header.pack(fill=tk.X, padx=5, pady=(5, 3))
        
        tk.Label(ctrl_f_header, text="CTRL+F Stars Skill", font=("Arial", 10, "bold"), 
                 background="#E1F5FE", fg="#1565C0").pack(side=tk.LEFT)
        
        ctrl_f_help = tk.Label(ctrl_f_header, text="?", font=("Arial", 9, "bold"), 
                              cursor="hand2", foreground="#1565C0", background="#E1F5FE")
        ctrl_f_help.pack(side=tk.LEFT, padx=(5, 0))
        self._create_ctrl_f_help_tooltip(ctrl_f_help)
        
        ctrl_f_content = tk.Frame(ctrl_f_tile, background="#E1F5FE")
        ctrl_f_content.pack(fill=tk.X, padx=5, pady=5)
        
        # Toggle button with icon
        ctrl_f_icon = self.sprites.get('ctrl_f_stars')
        btn_kwargs = {
            'command': self.on_ctrl_f_toggle,
            'relief': tk.SUNKEN if self.ctrl_f_stars_enabled else tk.RAISED,
            'borderwidth': 2,
            'background': "#E1F5FE",
            'activebackground': "#B3E5FC",
            'cursor': 'hand2',
        }
        
        if ctrl_f_icon:
            btn_kwargs['image'] = ctrl_f_icon
            btn_kwargs['width'] = 34
            btn_kwargs['height'] = 34
        else:
            btn_kwargs['text'] = "CTRL+F"
            btn_kwargs['width'] = 10
            btn_kwargs['height'] = 2
        
        self.ctrl_f_toggle_button = tk.Button(ctrl_f_content, **btn_kwargs)
        self.ctrl_f_toggle_button.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 8))
        
        # Status label
        status_text = "Enabled" if self.ctrl_f_stars_enabled else "Disabled"
        self.ctrl_f_status_label = tk.Label(
            ctrl_f_content,
            text=status_text,
            font=("Arial", 9),
            background="#E1F5FE",
            fg="#1565C0" if self.ctrl_f_stars_enabled else "#757575"
        )
        self.ctrl_f_status_label.pack(side=tk.LEFT, anchor=tk.W)
    
    def create_results_section(self, parent):
        """Create the results display section - compact like Freebie Gem EV"""
        
        container = tk.Frame(parent, background=COLOR_RESULTS, relief=tk.RIDGE, borderwidth=2)
        container.grid(row=0, column=1, sticky="nsew", padx=(3, 0), pady=0)
        
        # Header
        header = tk.Frame(container, background=COLOR_RESULTS)
        header.pack(fill=tk.X, padx=5, pady=(5, 3))
        tk.Label(header, text="RESULTS", font=("Arial", 11, "bold"), background=COLOR_RESULTS).pack(side=tk.LEFT)
        
        results_frame = tk.Frame(container, background=COLOR_RESULTS)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.result_labels = {}
        
        # Star Results - Online
        star_online_row = tk.Frame(results_frame, background=COLOR_RESULTS)
        star_online_row.pack(fill=tk.X, pady=3)
        online_label = tk.Label(star_online_row, text="⭐ Stars/hour (Online):", background=COLOR_RESULTS, 
                 font=("Arial", 10))
        online_label.pack(side=tk.LEFT)
        self._create_online_tooltip(online_label)
        val_label = tk.Label(star_online_row, text="—", background=COLOR_RESULTS, 
                             font=("Arial", 11, "bold"), fg="#1565C0")
        val_label.pack(side=tk.RIGHT)
        self.result_labels['stars_online'] = val_label
        
        # Star Results - Offline
        star_offline_row = tk.Frame(results_frame, background=COLOR_RESULTS)
        star_offline_row.pack(fill=tk.X, pady=3)
        tk.Label(star_offline_row, text="⭐ Stars/hour (Offline):", background=COLOR_RESULTS, 
                 font=("Arial", 10)).pack(side=tk.LEFT)
        val_label = tk.Label(star_offline_row, text="—", background=COLOR_RESULTS, 
                             font=("Arial", 11, "bold"), fg="#1565C0")
        val_label.pack(side=tk.RIGHT)
        self.result_labels['stars_offline'] = val_label
        
        # Separator
        ttk.Separator(results_frame, orient='horizontal').pack(fill=tk.X, pady=8)
        
        # Super Star Results - Online
        super_online_row = tk.Frame(results_frame, background=COLOR_RESULTS)
        super_online_row.pack(fill=tk.X, pady=3)
        super_online_label = tk.Label(super_online_row, text="🌟 Super Stars/hour (Online):", background=COLOR_RESULTS, 
                 font=("Arial", 10))
        super_online_label.pack(side=tk.LEFT)
        self._create_online_tooltip(super_online_label)
        val_label = tk.Label(super_online_row, text="—", background=COLOR_RESULTS, 
                             font=("Arial", 11, "bold"), fg="#E65100")
        val_label.pack(side=tk.RIGHT)
        self.result_labels['super_stars_online'] = val_label
        
        # Super Star Results - Offline
        super_offline_row = tk.Frame(results_frame, background=COLOR_RESULTS)
        super_offline_row.pack(fill=tk.X, pady=3)
        tk.Label(super_offline_row, text="🌟 Super Stars/hour (Offline):", background=COLOR_RESULTS, 
                 font=("Arial", 10)).pack(side=tk.LEFT)
        val_label = tk.Label(super_offline_row, text="—", background=COLOR_RESULTS, 
                             font=("Arial", 11, "bold"), fg="#E65100")
        val_label.pack(side=tk.RIGHT)
        self.result_labels['super_stars_offline'] = val_label
        
        ttk.Separator(results_frame, orient='horizontal').pack(fill=tk.X, pady=8)
    
    def trigger_auto_calculate(self):
        """Schedule recalculation 500ms after last change. Cancel previous timer."""
        if not self.auto_calculate_enabled:
            return
        if self._after_id is not None:
            self.window.after_cancel(self._after_id)
            self._after_id = None
        self._after_id = self.window.after(500, self._perform_auto_calculate)
    
    def _perform_auto_calculate(self):
        """Run recalculation (called after debounce delay)."""
        self._after_id = None
        try:
            self.update_calculations()
        except Exception:
            pass
    
    def on_ctrl_f_toggle(self):
        """Handle CTRL+F Stars toggle button click"""
        self.ctrl_f_stars_enabled = not self.ctrl_f_stars_enabled
        self._update_ctrl_f_button_visual()
        # Force immediate update
        self.update_calculations()
    
    def _update_ctrl_f_button_visual(self):
        """Update the visual appearance of CTRL+F toggle button"""
        if hasattr(self, 'ctrl_f_toggle_button'):
            if self.ctrl_f_stars_enabled:
                self.ctrl_f_toggle_button.config(relief=tk.SUNKEN, borderwidth=2)
                if hasattr(self, 'ctrl_f_status_label'):
                    self.ctrl_f_status_label.config(text="Enabled", fg="#1565C0")
            else:
                self.ctrl_f_toggle_button.config(relief=tk.RAISED, borderwidth=2)
                if hasattr(self, 'ctrl_f_status_label'):
                    self.ctrl_f_status_label.config(text="Disabled", fg="#757575")
    
    def update_calculations(self):
        """Recalculate and update display"""
        if not hasattr(self, 'result_labels'):
            print("Warning: result_labels not yet created")
            return
        
        if not self.result_labels:
            print("Warning: result_labels is empty")
            return
        
        # Read all values from UI entries (read directly from Entry widgets)
        manual_stats = {}
        if hasattr(self, 'stat_entries'):
            for key, entry in self.stat_entries.items():
                try:
                    # Get raw value directly from Entry widget
                    raw_val = entry.get()
                    val = raw_val.strip() if raw_val else ""
                    
                    if val:
                        manual_stats[key] = float(val)
                    else:
                        # Use default value from manual_stats if empty
                        manual_stats[key] = self.manual_stats.get(key, 0)
                except (ValueError, AttributeError) as e:
                    # On error, use default value
                    manual_stats[key] = self.manual_stats.get(key, 0)
        
        # CTRL+F Stars is managed by toggle button, no need to read from var
        
        # Update manual_stats with new values
        self.manual_stats.update(manual_stats)
        
        # Create stats from manual input
        try:
            # Convert floor_clears_per_minute to floor_clears_per_hour for calculation
            floor_clears_per_minute = manual_stats.get('floor_clears_per_minute', 2.0)
            floor_clears_per_hour = floor_clears_per_minute * 60.0
            
            stats = PlayerStats(
                floor_clears_per_hour=floor_clears_per_hour,
                star_spawn_rate_mult=manual_stats.get('star_spawn_rate_mult', 1.0),
                auto_catch_chance=manual_stats.get('auto_catch_chance', 0) / 100,  # % to decimal
                double_star_chance=manual_stats.get('double_star_chance', 0) / 100,
                triple_star_chance=manual_stats.get('triple_star_chance', 0) / 100,
                super_star_spawn_rate_mult=manual_stats.get('super_star_spawn_rate_mult', 1.0),
                triple_super_star_chance=manual_stats.get('triple_super_star_chance', 0) / 100,
                super_star_10x_chance=manual_stats.get('super_star_10x_chance', 0) / 100,
                star_supernova_chance=manual_stats.get('star_supernova_chance', 0) / 100,
                star_supernova_mult=manual_stats.get('star_supernova_mult', 10.0),
                star_supergiant_chance=manual_stats.get('star_supergiant_chance', 0) / 100,
                star_supergiant_mult=manual_stats.get('star_supergiant_mult', 3.0),
                star_radiant_chance=manual_stats.get('star_radiant_chance', 0) / 100,
                star_radiant_mult=manual_stats.get('star_radiant_mult', 10.0),
                super_star_supernova_chance=manual_stats.get('super_star_supernova_chance', 0) / 100,
                super_star_supernova_mult=manual_stats.get('super_star_supernova_mult', 10.0),
                super_star_supergiant_chance=manual_stats.get('super_star_supergiant_chance', 0) / 100,
                super_star_supergiant_mult=manual_stats.get('super_star_supergiant_mult', 3.0),
                super_star_radiant_chance=manual_stats.get('super_star_radiant_chance', 0) / 100,
                super_star_radiant_mult=manual_stats.get('super_star_radiant_mult', 10.0),
                all_star_mult=manual_stats.get('all_star_mult', 1.0),
                novagiant_combo_mult=manual_stats.get('novagiant_combo_mult', 1.0),
                ctrl_f_stars_enabled=self.ctrl_f_stars_enabled,
            )
            
            calc = StargazingCalculator(stats)
            summary = calc.get_summary()
            
        except Exception as e:
            print(f"Error in update_calculations: {e}")
            traceback.print_exc()
            for key in self.result_labels:
                self.result_labels[key].config(text="Error")
            return
        
        # Update results - simple labels like Freebie Gem EV
        try:
            self.result_labels['stars_online'].config(text=f"{summary['stars_per_hour_online']:.4f}")
            self.result_labels['stars_offline'].config(text=f"{summary['stars_per_hour_offline']:.4f}")
            self.result_labels['super_stars_online'].config(text=f"{summary['super_stars_per_hour_online']:.4f}")
            self.result_labels['super_stars_offline'].config(text=f"{summary['super_stars_per_hour_offline']:.4f}")
            self.window.update_idletasks()
        except KeyError as e:
            print(f"KeyError updating results: {e}")
            print(f"Available labels: {list(self.result_labels.keys())}")
            print(f"Available summary keys: {list(summary.keys())}")
        except Exception as e:
            print(f"Error updating result labels: {e}")
            traceback.print_exc()
    
    def _create_ctrl_f_help_tooltip(self, widget):
        """Tooltip explaining CTRL+F Stars skill"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            # Better size estimation based on content
            tooltip_width = 350
            tooltip_height = 200  # Increased for better visibility
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height, position="auto")
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#1565C0", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text="CTRL+F Stars Skill", font=("Arial", 10, "bold"), 
                     foreground="#1565C0", background="#FFFFFF").pack(anchor=tk.W)
            
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
            ]
            
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
    
    def _create_online_tooltip(self, widget):
        """Tooltip explaining what 'Online' means"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 320
            tooltip_height = 120
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height, position="auto")
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#1565C0", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text="Online Mode", font=("Arial", 10, "bold"), 
                     foreground="#1565C0", background="#FFFFFF").pack(anchor=tk.W)
            
            lines = [
                "",
                "Online means you manually catch all stars",
                "and follow them through all floors.",
                "",
                "This corresponds to 100% auto catch rate,",
                "meaning you catch every star that spawns.",
            ]
            
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
