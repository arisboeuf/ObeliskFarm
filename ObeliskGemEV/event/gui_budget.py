"""
Budget Optimizer Mode GUI.
Helps players optimize upgrade paths with limited materials.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import json
import sys
import os

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .constants import (
    get_prestige_wave_requirement, TIER_COLORS, TIER_MAT_NAMES, UPGRADE_SHORT_NAMES,
    CURRENCY_ICONS, WAVE_REWARDS, PRESTIGE_UNLOCKED, MAX_LEVELS, CAP_UPGRADES
)
from .utils import format_number
from .stats import PlayerStats, EnemyStats
from .simulation import (
    apply_upgrades, get_enemy_hp_at_wave, calculate_hits_to_kill,
    calculate_effective_hp
)
from .optimizer import greedy_optimize, format_upgrade_summary, UpgradeState

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import get_resource_path, create_tooltip


def get_user_data_path() -> Path:
    """Get path for user data (saves) - persists outside of bundle."""
    if getattr(sys, 'frozen', False):
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        save_dir = Path(app_data) / 'ObeliskGemEV' / 'save'
    else:
        save_dir = Path(__file__).parent.parent.parent / 'save'
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


# Save file path (in user data folder for persistence)
SAVE_DIR = get_user_data_path()
SAVE_FILE = SAVE_DIR / "event_budget_save.json"


class BudgetOptimizerPanel:
    """Budget Optimizer mode panel"""
    
    def __init__(self, parent_frame, window_ref):
        self.parent = parent_frame
        self.window = window_ref
        
        # State
        self.material_budget = {1: 0, 2: 0, 3: 0, 4: 0}
        self.material_vars = {}
        self.material_entries = {}  # Store entry widgets for direct access
        
        # Current upgrade levels (for forecast mode)
        self.current_upgrade_levels = {
            1: [0] * 10,
            2: [0] * 7,
            3: [0] * 8,
            4: [0] * 8
        }
        self.current_gem_levels = [0, 0, 0, 0]
        self.upgrade_level_labels = {}  # For updating display
        self.last_optimization_result = None  # Store last optimization result for applying
        self.apply_button = None  # Reference to apply button
        
        # Load currency icons
        self.currency_icons = {}
        self.upgrade_icons = {}  # Cache for upgrade icons
        self._load_currency_icons()
        self._load_upgrade_icons()
        
        self.build_ui()
        
        # Load saved state
        self.load_state()
        
        # Update player stats after loading (if upgrades were loaded)
        self._update_player_stats()
        
        # Update expected results after loading
        self._update_expected_results()
    
    def _load_currency_icons(self):
        """Load currency icons from sprites folder"""
        if not PIL_AVAILABLE:
            return
        
        try:
            for tier in range(1, 5):
                icon_path = get_resource_path(f"sprites/event/currency_{tier}.png")
                if icon_path.exists():
                    icon_image = Image.open(icon_path)
                    icon_image = icon_image.resize((24, 24), Image.Resampling.LANCZOS)
                    # Use window as master to ensure image is associated with the correct root
                    self.currency_icons[tier] = ImageTk.PhotoImage(icon_image, master=self.window)
        except Exception:
            pass  # Graceful fallback if icons can't be loaded
    
    def _load_upgrade_icons(self):
        """Load upgrade icons from event sprites folder"""
        if not PIL_AVAILABLE:
            return
        
        try:
            # Map upgrades to icon filenames based on upgrade type
            icon_mapping = {
                # Tier 1
                (1, 0): "upgrade_atk_dmg.png",      # +1 Atk Dmg
                (1, 1): "upgrade_max_hp.png",       # +2 Max Hp
                (1, 2): "upgrade_atk_speed.png",    # +0.02 Atk Spd
                (1, 3): "upgrade_move_speed.png",   # +0.03 Move Spd
                (1, 4): "upgrade_event_speed.png",  # +3% Event Game Spd
                (1, 5): "upgrade_crit_chance.png",  # +1% Crit Chance, +0.10 Crit Dmg
                (1, 6): "upgrade_atk_dmg.png",      # +1 Atk Dmg +2 Max Hp
                (1, 7): "upgrade_caps.png",         # +1 Tier 1 Upgrade Caps
                (1, 8): "upgrade_prestige_bonus.png", # +1% Prestige Bonus
                (1, 9): "upgrade_atk_dmg.png",      # +3 Atk Dmg, +3 Max Hp
                # Tier 2
                (2, 0): "upgrade_max_hp.png",       # +3 Max Hp
                (2, 1): "upgrade_enemy_atk_speed.png", # -0.02 Enemy Atk Spd
                (2, 2): "upgrade_enemy_atk_dmg.png",   # -1 Enemy Atk Dmg
                (2, 3): "upgrade_enemy_atk_speed.png", # -1% E.Crit, -0.10 E.Crit Dmg (using enemy icon)
                (2, 4): "upgrade_atk_speed.png",    # +1 Atk Dmg, +0.01 Atk Spd
                (2, 5): "upgrade_caps.png",         # +1 Tier 2 Upgrade Caps
                (2, 6): "upgrade_prestige_bonus.png", # +2% Prestige Bonus
                # Tier 3
                (3, 0): "upgrade_atk_dmg.png",      # +2 Atk Dmg
                (3, 1): "upgrade_atk_speed.png",    # +0.02 Atk Spd
                (3, 2): "upgrade_crit_chance.png",  # +1% Crit Chance
                (3, 3): "upgrade_event_speed.png",  # +5% Event Game Spd
                (3, 4): "upgrade_atk_dmg.png",     # +3 Atk Dmg, +3 Max Hp
                (3, 5): "upgrade_caps.png",         # +1 Tier 3 Upgrade Caps
                (3, 6): "upgrade_extra_currency.png", # +3% 5x Drop Chance
                (3, 7): "upgrade_atk_speed.png",    # +5 Max Hp, +0.03 Atk Spd
                # Tier 4
                (4, 0): "upgrade_block_chance.png", # +1% Block Chance
                (4, 1): "upgrade_max_hp.png",       # +5 Max Hp
                (4, 2): "upgrade_crit_dmg.png",     # +0.10 Crit Dmg, -0.10 E.Crit Dmg
                (4, 3): "upgrade_atk_speed.png",    # +0.02 Atk Spd, +0.02 Move Spd
                (4, 4): "upgrade_atk_dmg.png",      # +4 Max Hp, +4 Atk Dmg
                (4, 5): "upgrade_caps.png",          # +1 Tier 4 Upgrade Caps
                (4, 6): "upgrade_caps.png",          # +1 Cap Of Cap Upgrades
                (4, 7): "upgrade_atk_speed.png",     # +10 Max Hp, +0.05 Atk Spd
            }
            
            for (tier, idx), icon_name in icon_mapping.items():
                icon_path = get_resource_path(f"sprites/event/{icon_name}")
                if icon_path.exists():
                    icon_image = Image.open(icon_path)
                    icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                    # Use window as master to ensure image is associated with the correct root
                    self.upgrade_icons[(tier, idx)] = ImageTk.PhotoImage(icon_image, master=self.window)
        except Exception as e:
            print(f"Warning: Could not load upgrade icons: {e}")
            pass  # Graceful fallback
    
    def build_ui(self):
        """Build the Budget Optimizer UI - Three columns: Upgrades | Budget/Forecast | Stats"""
        # Initialize prestige var early (needed by _build_upgrade_level_inputs)
        self.budget_prestige_var = tk.IntVar(value=0)
        
        self.parent.columnconfigure(0, weight=2)  # Left (upgrades) - more space
        self.parent.columnconfigure(1, weight=2)  # Middle (budget + forecast) - more space
        self.parent.columnconfigure(2, weight=1)  # Right (player stats) - narrower
        self.parent.rowconfigure(0, weight=1)
        
        # Main container with three columns
        main_container = tk.Frame(self.parent)
        main_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        main_container.columnconfigure(0, weight=2)  # Left (upgrades) - more space
        main_container.columnconfigure(1, weight=2)   # Middle (budget + forecast) - more space
        main_container.columnconfigure(2, weight=1)   # Right (player stats) - narrower
        main_container.rowconfigure(0, weight=1)
        
        # === LEFT COLUMN: Upgrades only ===
        left_column = tk.Frame(main_container, background="#F5F5F5")
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        left_column.columnconfigure(0, weight=1)
        
        # === HEADER ===
        header_frame = tk.Frame(left_column, background="#4CAF50", relief=tk.RIDGE, borderwidth=2)
        header_frame.pack(fill=tk.X, padx=3, pady=2)
        
        # Header with title and prestige input
        header_content = tk.Frame(header_frame, background="#4CAF50")
        header_content.pack(fill=tk.X, padx=5, pady=3)
        
        tk.Label(header_content, text="Upgrades", font=("Arial", 10, "bold"),
                background="#4CAF50", foreground="white").pack(side=tk.LEFT)
        
        # Prestige input in header (right side)
        prestige_header_frame = tk.Frame(header_content, background="#4CAF50")
        prestige_header_frame.pack(side=tk.RIGHT)
        
        tk.Label(prestige_header_frame, text="Prestige:", font=("Arial", 9, "bold"),
                background="#4CAF50", foreground="white").pack(side=tk.LEFT, padx=(10, 5))
        
        prestige_spin_header = ttk.Spinbox(prestige_header_frame, from_=0, to=20, width=5,
                                          textvariable=self.budget_prestige_var,
                                          command=self._on_prestige_change)
        prestige_spin_header.pack(side=tk.LEFT)
        prestige_spin_header.bind('<Return>', lambda e: self._on_prestige_change())
        # Save when prestige changes
        self.budget_prestige_var.trace('w', lambda *args: self.save_state())
        
        # === CURRENT UPGRADE LEVELS (Forecast Mode) ===
        current_upgrades_frame = tk.Frame(left_column, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        current_upgrades_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
        
        # Header with reset button and total points
        upgrade_header = tk.Frame(current_upgrades_frame, background="#FFF3E0")
        upgrade_header.pack(fill=tk.X, padx=5, pady=(3, 2))
        
        tk.Label(upgrade_header, text="Current Upgrade Levels", font=("Arial", 9, "bold"),
                background="#FFF3E0").pack(side=tk.LEFT)
        
        # Total points label
        self.total_points_label = tk.Label(upgrade_header, text="Total: 0", 
                                          font=("Arial", 9, "bold"), background="#FFF3E0",
                                          foreground="#1976D2")
        self.total_points_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Reset button
        reset_btn = tk.Button(upgrade_header, text="Reset", 
                            font=("Arial", 8, "bold"), bg="#F44336", fg="white",
                            command=self._reset_upgrades, padx=8, pady=2)
        reset_btn.pack(side=tk.RIGHT)
        
        # Upgrade levels container (scrollable)
        upgrade_canvas = tk.Canvas(current_upgrades_frame, highlightthickness=0, background="#FFF3E0")
        upgrade_scrollbar = ttk.Scrollbar(current_upgrades_frame, orient="vertical", command=upgrade_canvas.yview)
        self.upgrades_container = tk.Frame(upgrade_canvas, background="#FFF3E0")
        
        self.upgrades_container.bind(
            "<Configure>",
            lambda e: upgrade_canvas.configure(scrollregion=upgrade_canvas.bbox("all"))
        )
        
        self.upgrade_canvas_window = upgrade_canvas.create_window((0, 0), window=self.upgrades_container, anchor="nw")
        upgrade_canvas.configure(yscrollcommand=upgrade_scrollbar.set)
        
        # Update canvas width when container width changes
        def configure_canvas_width(event):
            canvas_width = event.width
            upgrade_canvas.itemconfig(self.upgrade_canvas_window, width=canvas_width)
        upgrade_canvas.bind('<Configure>', configure_canvas_width)
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            upgrade_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        upgrade_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        upgrade_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=(0, 3))
        upgrade_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 3))
        
        self._build_upgrade_level_inputs()
        
        # === MIDDLE COLUMN: Budget + Forecast/Results ===
        middle_column = tk.Frame(main_container, background="#F5F5F5")
        middle_column.grid(row=0, column=1, sticky="nsew", padx=3)
        middle_column.columnconfigure(0, weight=1)
        
        # === MATERIAL INPUT (Budget) ===
        input_frame = tk.Frame(middle_column, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        input_frame.pack(fill=tk.X, padx=3, pady=2)
        
        tk.Label(input_frame, text="Materials", font=("Arial", 9, "bold"),
                background="#E8F5E9").pack(anchor="w", padx=5, pady=(3, 2))
        
        mat_inner = tk.Frame(input_frame, background="#E8F5E9")
        mat_inner.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        mat_names = ["Coins", "M2", "M3", "M4"]
        mat_colors = ["#FFC107", "#9C27B0", "#00BCD4", "#E91E63"]
        
        # Configure grid for uniform column widths (only 4 columns now, no prestige)
        mat_inner.columnconfigure(0, weight=1, uniform="mat_col")
        mat_inner.columnconfigure(1, weight=1, uniform="mat_col")
        mat_inner.columnconfigure(2, weight=1, uniform="mat_col")
        mat_inner.columnconfigure(3, weight=1, uniform="mat_col")
        
        # Compact grid layout for materials - uniform size
        for i in range(4):
            col_frame = tk.Frame(mat_inner, background="#E8F5E9")
            col_frame.grid(row=0, column=i, padx=2, sticky="ew")
            
            tier = i + 1
            if tier in self.currency_icons:
                icon_label = tk.Label(col_frame, image=self.currency_icons[tier],
                                     background="#E8F5E9")
                icon_label.pack()
            
            tk.Label(col_frame, text=mat_names[i], font=("Arial", 7, "bold"),
                    background="#E8F5E9").pack()
            
            var = tk.StringVar(value="0")
            entry = ttk.Entry(col_frame, textvariable=var, width=10, font=("Arial", 8))
            entry.pack(pady=2, fill=tk.X)
            entry.bind('<Return>', lambda e: self.calculate_optimal_upgrades())
            # Also trigger on focus out to ensure values are captured
            entry.bind('<FocusOut>', lambda e: self._validate_material_entry(tier))
            
            # Store both the StringVar and the Entry widget reference
            self.material_vars[tier] = var
            self.material_entries[tier] = entry
        
        # Prestige input removed from here - now in header
        
        # Calculate button (compact)
        calc_btn = tk.Button(input_frame, text="Forecast", 
                            font=("Arial", 9, "bold"), bg="#4CAF50", fg="white",
                            command=self.calculate_optimal_upgrades)
        calc_btn.pack(pady=3)
        
        # === RESULTS (fixed at top, no scrolling) ===
        results_frame = tk.Frame(middle_column, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
        results_frame.rowconfigure(0, weight=0)  # Expected Results - fixed at top
        results_frame.rowconfigure(1, weight=1)  # Rest of results - scrollable
        
        # === EXPECTED RESULTS (always visible at top) ===
        expected_results_frame = tk.Frame(results_frame, background="#E8F5E9", relief=tk.RAISED, borderwidth=1)
        expected_results_frame.grid(row=0, column=0, sticky="ew", padx=3, pady=(3, 2))
        
        # Header with title and refresh button
        header_frame = tk.Frame(expected_results_frame, background="#E8F5E9")
        header_frame.pack(fill=tk.X, padx=5, pady=(3, 2))
        
        tk.Label(header_frame, text="Expected Results", font=("Arial", 10, "bold"),
                background="#E8F5E9").pack(side=tk.LEFT)
        
        # Refresh button
        refresh_btn = tk.Button(header_frame, text="🔄", font=("Arial", 12),
                               command=self._refresh_stats_and_results,
                               bg="#E8F5E9", fg="#1976D2", relief=tk.FLAT,
                               cursor="hand2", padx=5, pady=2)
        refresh_btn.pack(side=tk.RIGHT)
        create_tooltip(refresh_btn, "Refresh stats and expected results")
        
        # Expected results container (will be updated manually)
        self.expected_results_container = tk.Frame(expected_results_frame, background="#E8F5E9")
        self.expected_results_container.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        # Initial expected results display
        self._update_expected_results()
        
        # === SCROLLABLE RESULTS CONTAINER ===
        # Canvas for scrollable content below expected results
        results_canvas = tk.Canvas(results_frame, highlightthickness=0, background="#E8F5E9")
        results_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=results_canvas.yview)
        self.results_container = tk.Frame(results_canvas, background="#E8F5E9")
        
        self.results_container.bind(
            "<Configure>",
            lambda e: results_canvas.configure(scrollregion=results_canvas.bbox("all"))
        )
        
        self.results_canvas_window = results_canvas.create_window((0, 0), window=self.results_container, anchor="nw")
        results_canvas.configure(yscrollcommand=results_scrollbar.set)
        
        # Update canvas width when container width changes
        def configure_results_canvas_width(event):
            canvas_width = event.width
            results_canvas.itemconfig(self.results_canvas_window, width=canvas_width)
        results_canvas.bind('<Configure>', configure_results_canvas_width)
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            results_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        results_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        results_canvas.grid(row=1, column=0, sticky="nsew", padx=3, pady=(0, 3))
        results_scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 3))
        
        # Initial placeholder
        self.show_initial_instructions()
        
        # === RIGHT COLUMN: Player Stats ===
        right_column = tk.Frame(main_container, background="#F5F5F5")
        right_column.grid(row=0, column=2, sticky="nsew", padx=(3, 0))
        right_column.columnconfigure(0, weight=1)
        
        # === PLAYER STATS PANEL (Game-style) ===
        stats_frame = tk.Frame(right_column, background="#2C2C2C", relief=tk.RAISED, borderwidth=2)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
        
        tk.Label(stats_frame, text="Player Stats", font=("Arial", 10, "bold"),
                background="#2C2C2C", foreground="white").pack(anchor="w", padx=10, pady=(5, 3))
        
        # Stats container
        self.stats_container = tk.Frame(stats_frame, background="#2C2C2C")
        self.stats_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        
        # Initial empty stats
        self.update_player_stats_display(None, None, None)
    
    def _build_upgrade_level_inputs(self):
        """Build upgrade level input rows with +/- buttons (compact, no scrolling)"""
        from .optimizer import get_max_level_with_caps, UpgradeState
        
        # Clear existing
        for widget in self.upgrades_container.winfo_children():
            widget.destroy()
        self.upgrade_level_labels = {}
        
        # Create state for max level calculation
        temp_state = UpgradeState()
        for t in range(1, 5):
            temp_state.levels[t] = self.current_upgrade_levels[t].copy()
        
        prestige = self.budget_prestige_var.get()
        
        # Configure grid with uniform column widths
        self.upgrades_container.columnconfigure(0, weight=1, uniform="col")
        self.upgrades_container.columnconfigure(1, weight=1, uniform="col")
        
        # Use grid for uniform layout
        row = 0
        for tier in range(1, 5):
            # Tier header
            tier_header = tk.Frame(self.upgrades_container, background=TIER_COLORS[tier], relief=tk.RAISED, borderwidth=1)
            tier_header.grid(row=row, column=0, columnspan=2, sticky="ew", padx=1, pady=(2, 1))
            row += 1
            
            tk.Label(tier_header, text=f"T{tier}", 
                    font=("Arial", 11, "bold"), background=TIER_COLORS[tier]).pack(side=tk.LEFT, padx=5, pady=2)
            
            # Upgrade rows (2 columns, uniform size)
            for idx, name in enumerate(UPGRADE_SHORT_NAMES[tier]):
                col = idx % 2
                if col == 0:
                    row += 1
                
                # Uniform row frame with fixed height
                row_frame = tk.Frame(self.upgrades_container, background="#FFFFFF", relief=tk.RAISED, borderwidth=1)
                row_frame.grid(row=row, column=col, sticky="ew", padx=2, pady=1)
                # Configure columns - buttons next to name, level with cost below
                row_frame.columnconfigure(0, weight=0, minsize=25)   # Buttons column (vertical)
                row_frame.columnconfigure(1, weight=1, minsize=100)  # Name column
                row_frame.columnconfigure(2, weight=0, minsize=60)  # Level + Cost column (wider for cost text)
                
                # Check if unlocked
                prestige_req = PRESTIGE_UNLOCKED[tier][idx]
                locked = prestige_req > prestige
                
                if locked:
                    row_frame.config(background="#CCCCCC")
                    tk.Label(row_frame, text=f"{name[:12]} (P{prestige_req})", 
                            font=("Arial", 9), background="#CCCCCC", 
                            foreground="#666666", anchor="w").grid(row=0, column=0, sticky="w", padx=3, pady=2)
                    continue
                
                # Get max level
                max_level = get_max_level_with_caps(tier, idx, temp_state)
                current_level = self.current_upgrade_levels[tier][idx]
                
                # Buttons column (vertical: + on top, - below)
                buttons_frame = tk.Frame(row_frame, background="#FFFFFF")
                buttons_frame.grid(row=0, column=0, padx=2, pady=2, sticky="n")
                
                # Plus button (on top)
                plus_btn = tk.Button(buttons_frame, text="+", width=2, height=1, font=("Arial", 9, "bold"),
                                   command=lambda t=tier, i=idx: self._increment_upgrade(t, i),
                                   state='disabled' if current_level >= max_level else 'normal',
                                   bg="#44AA44" if current_level < max_level else "#CCCCCC",
                                   fg="white" if current_level < max_level else "#666666",
                                   relief=tk.RAISED, borderwidth=1,
                                   cursor="hand2" if current_level < max_level else "arrow")
                plus_btn.pack(pady=(0, 1))
                
                # Minus button (below)
                minus_btn = tk.Button(buttons_frame, text="−", width=2, height=1, font=("Arial", 9, "bold"),
                                    command=lambda t=tier, i=idx: self._decrement_upgrade(t, i),
                                    state='disabled' if current_level == 0 else 'normal',
                                    bg="#FF4444" if current_level > 0 else "#CCCCCC",
                                    fg="white" if current_level > 0 else "#666666",
                                    relief=tk.RAISED, borderwidth=1,
                                    cursor="hand2" if current_level > 0 else "arrow")
                minus_btn.pack(pady=(1, 0))
                
                # Name (with tooltip for full name)
                name_display = name[:15] + "..." if len(name) > 15 else name
                name_label = tk.Label(row_frame, text=name_display, font=("Arial", 9), 
                                     background="#FFFFFF", anchor="w")
                name_label.grid(row=0, column=1, sticky="w", padx=3, pady=2)
                if len(name) > 15:
                    create_tooltip(name_label, name)  # Show full name on hover
                
                # Level display with cost below
                level_frame = tk.Frame(row_frame, background="#FFFFFF")
                level_frame.grid(row=0, column=2, padx=2, pady=2)
                
                # Level text
                level_text = f"{current_level}/{max_level}"
                level_label = tk.Label(level_frame, text=level_text, 
                                      font=("Arial", 9, "bold"), background="#FFFFFF", 
                                      anchor=tk.CENTER)
                level_label.pack()
                
                # Next cost (small, below level)
                if current_level < max_level:
                    from .constants import COSTS
                    base_cost = COSTS[tier][idx]
                    next_cost = round(base_cost * (1.25 ** current_level))
                    cost_text = f"{next_cost:,}" if next_cost < 1000 else f"{next_cost/1000:.1f}k"
                    cost_label = tk.Label(level_frame, text=cost_text, 
                                         font=("Arial", 7), background="#FFFFFF", 
                                         foreground="#666666", anchor=tk.CENTER)
                    cost_label.pack()
                else:
                    tk.Label(level_frame, text="MAX", font=("Arial", 7, "bold"), background="#FFFFFF", 
                            foreground="#999999", anchor=tk.CENTER).pack()
                
                # Store references for updates (also store cost_label and level_frame for updates)
                cost_label = None
                for child in level_frame.winfo_children():
                    if isinstance(child, tk.Label):
                        # Find the cost/MAX label (smaller font, below level label)
                        font_info = child.cget("font")
                        if isinstance(font_info, (tuple, list)) and len(font_info) >= 2:
                            if font_info[0] == "Arial" and font_info[1] == 7:
                                cost_label = child
                                break
                self.upgrade_level_labels[(tier, idx)] = (level_label, minus_btn, plus_btn, max_level, level_frame, cost_label)
        
        # Update total points display
        self._update_total_points()
    
    def _update_upgrade_display(self, tier: int, idx: int, update_total: bool = True):
        """Update display for a single upgrade without rebuilding the entire list"""
        from .optimizer import get_max_level_with_caps, UpgradeState
        from .constants import COSTS
        
        if (tier, idx) not in self.upgrade_level_labels:
            return
        
        # Get stored references
        stored = self.upgrade_level_labels[(tier, idx)]
        if len(stored) == 6:
            level_label, minus_btn, plus_btn, old_max_level, level_frame, cost_label = stored
        elif len(stored) == 4:
            # Old format without level_frame and cost_label - rebuild needed
            level_label, minus_btn, plus_btn, old_max_level = stored
            # Rebuild this upgrade's display (fallback)
            self._build_upgrade_level_inputs()
            return
        else:
            # Unknown format - rebuild needed
            self._build_upgrade_level_inputs()
            return
        
        # Recalculate max level
        state = UpgradeState()
        for t in range(1, 5):
            state.levels[t] = self.current_upgrade_levels[t].copy()
        
        max_level = get_max_level_with_caps(tier, idx, state)
        current_level = self.current_upgrade_levels[tier][idx]
        
        # Update level label
        level_text = f"{current_level}/{max_level}"
        level_label.config(text=level_text)
        
        # Update cost label
        # Clear existing cost label (all labels except the level label)
        # We identify the level label by comparing it to the stored level_label reference
        children_to_remove = []
        for child in level_frame.winfo_children():
            if isinstance(child, tk.Label) and child != level_label:
                # This is not the level label, so it must be a cost/MAX label - remove it
                children_to_remove.append(child)
        
        for child in children_to_remove:
            child.destroy()
        
        # Add new cost label or MAX label
        if current_level < max_level:
            base_cost = COSTS[tier][idx]
            next_cost = round(base_cost * (1.25 ** current_level))
            cost_text = f"{next_cost:,}" if next_cost < 1000 else f"{next_cost/1000:.1f}k"
            new_cost_label = tk.Label(level_frame, text=cost_text, 
                                     font=("Arial", 7), background="#FFFFFF", 
                                     foreground="#666666", anchor=tk.CENTER)
            new_cost_label.pack()
            # Update stored reference
            self.upgrade_level_labels[(tier, idx)] = (level_label, minus_btn, plus_btn, max_level, level_frame, new_cost_label)
        else:
            max_label = tk.Label(level_frame, text="MAX", font=("Arial", 7, "bold"), 
                                background="#FFFFFF", foreground="#999999", anchor=tk.CENTER)
            max_label.pack()
            # Update stored reference
            self.upgrade_level_labels[(tier, idx)] = (level_label, minus_btn, plus_btn, max_level, level_frame, max_label)
        
        # Update button states
        # Plus button
        if current_level >= max_level:
            plus_btn.config(state='disabled', bg="#CCCCCC", fg="#666666", cursor="arrow")
        else:
            plus_btn.config(state='normal', bg="#44AA44", fg="white", cursor="hand2")
        
        # Minus button
        if current_level == 0:
            minus_btn.config(state='disabled', bg="#CCCCCC", fg="#666666", cursor="arrow")
        else:
            minus_btn.config(state='normal', bg="#FF4444", fg="white", cursor="hand2")
        
        # Update total points display (only if requested, to avoid multiple updates)
        if update_total:
            self._update_total_points()
    
    def _on_prestige_change(self):
        """Update upgrade inputs when prestige changes"""
        self._build_upgrade_level_inputs()
        # Update player stats to reflect new prestige multiplier
        self._update_player_stats()
        # Save state when prestige changes
        self.save_state()
    
    def _update_total_points(self):
        """Update the total points display"""
        total = 0
        for tier in range(1, 5):
            for idx in range(len(self.current_upgrade_levels[tier])):
                total += self.current_upgrade_levels[tier][idx]
        
        if hasattr(self, 'total_points_label'):
            self.total_points_label.config(text=f"Total: {total}")
    
    def _calculate_wave_probability_info(self, result, prestige: int) -> str:
        """Calculate probability information for reaching waves and prestige requirements"""
        from .simulation import run_full_simulation
        from .constants import get_prestige_wave_requirement
        
        # Run more simulations for better probability estimate
        player = result.player_stats
        enemy = result.enemy_stats
        estimated_wave = result.expected_wave
        
        # Run 200 simulations for probability calculation
        sim_results, avg_wave, avg_time = run_full_simulation(player, enemy, runs=200)
        
        # Calculate probability of reaching estimated wave
        import math
        waves_reached = [r[0] + (1 - r[1] * 0.2) for r in sim_results]  # Convert to decimal wave
        times = [r[2] for r in sim_results]  # Extract times
        reached_count = sum(1 for w in waves_reached if w >= estimated_wave)
        probability = (reached_count / len(sim_results)) * 100
        
        # Calculate standard deviations
        if len(waves_reached) > 1:
            wave_variance = sum((w - avg_wave) ** 2 for w in waves_reached) / len(waves_reached)
            wave_sd = math.sqrt(wave_variance)
        else:
            wave_sd = 0.0
        
        if len(times) > 1:
            time_variance = sum((t - avg_time) ** 2 for t in times) / len(times)
            time_sd = math.sqrt(time_variance)
        else:
            time_sd = 0.0
        
        # Calculate time statistics
        min_time = min(times)
        max_time = max(times)
        min_wave = min(waves_reached)
        max_wave = max(waves_reached)
        
        # Calculate probability for next few prestiges
        prestige_info = []
        for p in range(prestige + 1, min(prestige + 4, 20)):
            prestige_wave = get_prestige_wave_requirement(p)
            if prestige_wave > estimated_wave * 1.5:  # Skip if way too high
                break
            reached_prestige = sum(1 for w in waves_reached if w >= prestige_wave)
            prestige_prob = (reached_prestige / len(sim_results)) * 100
            prestige_info.append(f"Prestige {p} (Wave {prestige_wave}): {prestige_prob:.1f}%")
        
        # Build tooltip text following design guidelines (headers end with ':')
        tooltip_text = f"Wave Reach Probability:\n"
        tooltip_text += f"  • Reach Wave {estimated_wave:.1f}: {probability:.1f}%\n"
        tooltip_text += f"  • Average Wave: {avg_wave:.1f} ± {wave_sd:.1f} (SD)\n"
        tooltip_text += f"  • Best Run: {max_wave:.1f}\n"
        tooltip_text += f"  • Worst Run: {min_wave:.1f}\n\n"
        
        tooltip_text += f"Run Duration:\n"
        tooltip_text += f"  • Average Time: {avg_time:.1f}s ± {time_sd:.1f}s (SD)\n"
        tooltip_text += f"  • Fastest Run: {min_time:.1f}s\n"
        tooltip_text += f"  • Slowest Run: {max_time:.1f}s\n\n"
        
        tooltip_text += f"Prestige Unlock Requirements:\n"
        tooltip_text += f"  • Current Prestige: {prestige}\n"
        tooltip_text += f"  • Next Prestige ({prestige + 1}): Wave {get_prestige_wave_requirement(prestige + 1)}\n"
        
        if prestige_info:
            tooltip_text += f"\nPrestige Reach Probability:\n"
            for info in prestige_info:
                tooltip_text += f"  • {info}\n"
        
        tooltip_text += f"\nNote:\n"
        tooltip_text += f"  • Probabilities based on 200 simulation runs\n"
        tooltip_text += f"  • Actual results may vary due to RNG (crits, blocks)"
        
        return tooltip_text
    
    def _increment_upgrade(self, tier: int, idx: int):
        """Increment upgrade level"""
        from .optimizer import get_max_level_with_caps, UpgradeState
        from .constants import CAP_UPGRADES
        
        if (tier, idx) not in self.upgrade_level_labels:
            return
        
        # Recalculate max level (it might have changed due to cap upgrades)
        state = UpgradeState()
        for t in range(1, 5):
            state.levels[t] = self.current_upgrade_levels[t].copy()
        
        max_level = get_max_level_with_caps(tier, idx, state)
        current = self.current_upgrade_levels[tier][idx]
        
        if current < max_level:
            self.current_upgrade_levels[tier][idx] += 1
            
            # Check if this is a cap upgrade that affects other upgrades
            cap_idx = CAP_UPGRADES[tier] - 1  # 0-indexed
            is_cap_upgrade = (idx == cap_idx)
            is_cap_of_caps = (tier == 4 and idx == 6)
            
            # Update only affected upgrades (no full rebuild)
            if is_cap_of_caps:
                # Cap of caps affects all cap upgrades
                self._update_upgrade_display(1, CAP_UPGRADES[1] - 1, update_total=False)
                self._update_upgrade_display(2, CAP_UPGRADES[2] - 1, update_total=False)
                self._update_upgrade_display(3, CAP_UPGRADES[3] - 1, update_total=False)
                self._update_upgrade_display(4, CAP_UPGRADES[4] - 1, update_total=False)
            elif is_cap_upgrade:
                # Cap upgrade affects all upgrades in this tier
                for i in range(len(self.current_upgrade_levels[tier])):
                    if i != idx:  # Don't update the cap upgrade itself (already done)
                        self._update_upgrade_display(tier, i, update_total=False)
            
            # Update the clicked upgrade itself (with total update)
            self._update_upgrade_display(tier, idx, update_total=True)
            
            self.save_state()  # Auto-save on change
    
    def _decrement_upgrade(self, tier: int, idx: int):
        """Decrement upgrade level"""
        from .optimizer import get_max_level_with_caps, UpgradeState
        from .constants import CAP_UPGRADES
        
        if (tier, idx) not in self.upgrade_level_labels:
            return
        
        if self.current_upgrade_levels[tier][idx] > 0:
            self.current_upgrade_levels[tier][idx] -= 1
            
            # Check if this is a cap upgrade that affects other upgrades
            cap_idx = CAP_UPGRADES[tier] - 1  # 0-indexed
            is_cap_upgrade = (idx == cap_idx)
            is_cap_of_caps = (tier == 4 and idx == 6)
            
            # Update only affected upgrades (no full rebuild)
            if is_cap_of_caps:
                # Cap of caps affects all cap upgrades
                self._update_upgrade_display(1, CAP_UPGRADES[1] - 1, update_total=False)
                self._update_upgrade_display(2, CAP_UPGRADES[2] - 1, update_total=False)
                self._update_upgrade_display(3, CAP_UPGRADES[3] - 1, update_total=False)
                self._update_upgrade_display(4, CAP_UPGRADES[4] - 1, update_total=False)
            elif is_cap_upgrade:
                # Cap upgrade affects all upgrades in this tier
                for i in range(len(self.current_upgrade_levels[tier])):
                    if i != idx:  # Don't update the cap upgrade itself (already done)
                        self._update_upgrade_display(tier, i, update_total=False)
            
            # Update the clicked upgrade itself (with total update)
            self._update_upgrade_display(tier, idx, update_total=True)
            
            self.save_state()  # Auto-save on change
    
    def _reset_upgrades(self):
        """Reset all upgrades to 0"""
        # Reset all upgrade levels
        for tier in range(1, 5):
            for idx in range(len(self.current_upgrade_levels[tier])):
                self.current_upgrade_levels[tier][idx] = 0
        
        # Reset gem levels
        self.current_gem_levels = [0, 0, 0, 0]
        
        # Rebuild UI
        self._build_upgrade_level_inputs()
        
        # Save state
        self.save_state()
    
    def _refresh_stats_and_results(self):
        """Refresh both player stats and expected results"""
        self._update_player_stats()
        self._update_expected_results()
    
    def _update_player_stats(self):
        """Update player stats display based on current upgrade levels"""
        from .simulation import apply_upgrades
        from .stats import PlayerStats, EnemyStats
        
        # Get current prestige
        prestige = self.budget_prestige_var.get()
        
        # Calculate player stats from current upgrades
        player, enemy = apply_upgrades(
            self.current_upgrade_levels,
            PlayerStats(),
            EnemyStats(),
            prestige,
            self.current_gem_levels
        )
        
        # Calculate eHP at a reference wave (wave 20 for example)
        from .simulation import calculate_effective_hp
        reference_wave = 20
        ehp_at_wave = calculate_effective_hp(player, enemy, reference_wave)
        
        # Create a simple result-like object for display
        class SimpleResult:
            def __init__(self, player_stats, enemy_stats=None):
                self.player_stats = player_stats
                self.enemy_stats = enemy_stats
        
        result = SimpleResult(player, enemy)
        
        # Update display (prestige multiplier will be calculated dynamically in update_player_stats_display)
        self.update_player_stats_display(result, reference_wave, ehp_at_wave)
    
    def _update_expected_results(self):
        """Update expected results display based on current upgrade levels"""
        from .simulation import apply_upgrades, run_full_simulation
        from .stats import PlayerStats, EnemyStats
        
        # Clear existing expected results
        for widget in self.expected_results_container.winfo_children():
            widget.destroy()
        
        # Calculate player stats from current upgrades
        player, enemy = apply_upgrades(
            self.current_upgrade_levels,
            PlayerStats(),
            EnemyStats(),
            self.budget_prestige_var.get(),
            self.current_gem_levels
        )
        
        # Run simulation to get expected wave and time
        sim_results, avg_wave, avg_time = run_full_simulation(player, enemy, runs=100)
        
        # Calculate standard deviations
        import math
        waves_reached = [r[0] + (1 - r[1] * 0.2) for r in sim_results]  # Convert to decimal wave
        times = [r[2] for r in sim_results]  # Extract times
        
        # Calculate SD for waves
        if len(waves_reached) > 1:
            wave_variance = sum((w - avg_wave) ** 2 for w in waves_reached) / len(waves_reached)
            wave_sd = math.sqrt(wave_variance)
        else:
            wave_sd = 0.0
        
        # Calculate SD for times
        if len(times) > 1:
            time_variance = sum((t - avg_time) ** 2 for t in times) / len(times)
            time_sd = math.sqrt(time_variance)
        else:
            time_sd = 0.0
        
        # Build tooltip with SD
        tooltip_text = f"Simulation Statistics ({len(sim_results)} runs):\n"
        tooltip_text += f"  • Average Wave: {avg_wave:.1f} ± {wave_sd:.1f} (SD)\n"
        tooltip_text += f"  • Average Time: {avg_time:.1f}s ± {time_sd:.1f}s (SD)\n"
        tooltip_text += f"  • Min Wave: {min(waves_reached):.1f}\n"
        tooltip_text += f"  • Max Wave: {max(waves_reached):.1f}"
        
        # Display expected results with tooltip
        header_frame = tk.Frame(self.expected_results_container, background="#E8F5E9")
        header_frame.pack(fill=tk.X, pady=1)
        
        wave_label = tk.Label(header_frame, 
                             text=f"Max Wave: {avg_wave:.1f}", 
                             font=("Arial", 9, "bold"), background="#E8F5E9",
                             foreground="#1976D2", wraplength=200, justify=tk.LEFT)
        wave_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Add help icon with tooltip
        help_label = tk.Label(header_frame, text="❓", font=("Arial", 10),
                            background="#E8F5E9", foreground="gray", cursor="hand2")
        help_label.pack(side=tk.LEFT)
        create_tooltip(help_label, tooltip_text)
        
        time_label = tk.Label(self.expected_results_container, 
                             text=f"Time/Run: {avg_time:.1f}s", 
                             font=("Arial", 9), background="#E8F5E9", 
                             wraplength=200, justify=tk.LEFT)
        time_label.pack(anchor="w", pady=1)
    
    def _apply_recommended_upgrades(self):
        """Apply recommended upgrades from last optimization to current upgrade levels"""
        if not self.last_optimization_result or not hasattr(self, 'last_initial_state'):
            return
        
        if not self.apply_button or self.apply_button.cget('state') == tk.DISABLED:
            return  # Already applied
        
        initial_state = self.last_initial_state
        recommended_state = self.last_optimization_result.upgrades
        
        # Calculate differences and apply them
        applied_count = 0
        for tier in range(1, 5):
            for idx in range(len(initial_state.levels[tier])):
                initial_level = initial_state.levels[tier][idx]
                recommended_level = recommended_state.levels[tier][idx]
                if recommended_level > initial_level:
                    # Apply the difference
                    current_level = self.current_upgrade_levels[tier][idx]
                    new_level = current_level + (recommended_level - initial_level)
                    self.current_upgrade_levels[tier][idx] = new_level
                    applied_count += (recommended_level - initial_level)
        
        # Rebuild UI to reflect changes
        self._build_upgrade_level_inputs()
        self.save_state()  # Auto-save
        
        # Update player stats with new upgrade levels
        self._update_player_stats()
        
        # Update expected results with new upgrade levels
        self._update_expected_results()
        
        # Disable button and show confirmation
        if applied_count > 0 and self.apply_button:
            self.apply_button.config(
                state=tk.DISABLED,
                text="✓ Points Added!",
                bg="#9E9E9E",  # Gray background
                fg="#FFFFFF",
                cursor="arrow"
            )
    
    def update_player_stats_display(self, result, next_prestige_wave, ehp_at_target):
        """Update player stats display in game-style format"""
        # Clear existing stats
        for widget in self.stats_container.winfo_children():
            widget.destroy()
        
        if result is None:
            # Show placeholder
            tk.Label(self.stats_container, text="Run optimization to see stats", 
                    font=("Arial", 9, "italic"), background="#2C2C2C", 
                    foreground="#888888").pack(anchor="w", pady=5)
            return
        
        player = result.player_stats
        prestige = self.budget_prestige_var.get()
        prestige_mult = 1 + prestige * player.prestige_bonus_scale
        
        # Define stat rows: (label, value_formatter, icon_symbol, tooltip_text)
        stat_rows = [
            ("Max Hp:", lambda: f"{int(player.health)}", "❤", None),
        ]
        
        # Add eHP directly after Max HP if calculated
        if ehp_at_target:
            ehp_mult = ehp_at_target / player.health if player.health > 0 else 1.0
            
            # Calculate detailed multiplier breakdown
            from .simulation import apply_upgrades, calculate_effective_hp
            from .stats import EnemyStats as BaseEnemyStats
            
            # Get enemy stats from result or calculate from current upgrades
            if hasattr(result, 'enemy_stats'):
                enemy_stats = result.enemy_stats
            else:
                # Calculate enemy stats from current upgrades
                _, enemy_stats = apply_upgrades(
                    self.current_upgrade_levels,
                    PlayerStats(),
                    BaseEnemyStats(),
                    self.budget_prestige_var.get(),
                    self.current_gem_levels
                )
            
            # Calculate multipliers
            block_mult = 1.0 / (1.0 - player.block_chance) if player.block_chance < 1.0 else float('inf')
            
            # Calculate base enemy damage (no debuffs)
            base_enemy_atk = 2.5 + next_prestige_wave * 0.6
            base_enemy_crit = 0 + next_prestige_wave
            base_enemy_crit_dmg = 1.0 + next_prestige_wave * 0.05
            base_enemy_crit_chance = max(0, base_enemy_crit / 100.0)
            base_avg_dmg = base_enemy_atk * (1.0 + base_enemy_crit_chance * (base_enemy_crit_dmg - 1.0))
            
            # Calculate actual enemy damage (with debuffs)
            actual_enemy_atk = max(1, enemy_stats.atk + next_prestige_wave * enemy_stats.atk_scaling)
            actual_enemy_crit_chance = max(0, (enemy_stats.crit + next_prestige_wave) / 100.0)
            actual_enemy_crit_dmg = enemy_stats.crit_dmg + enemy_stats.crit_dmg_scaling * next_prestige_wave
            actual_avg_dmg = actual_enemy_atk * (1.0 + actual_enemy_crit_chance * (actual_enemy_crit_dmg - 1.0))
            
            dmg_reduction_mult = base_avg_dmg / actual_avg_dmg if actual_avg_dmg > 0 else 1.0
            
            # Build detailed tooltip
            ehp_tooltip = f"Effective HP Breakdown (Wave {next_prestige_wave}):\n"
            ehp_tooltip += f"  • Base HP: {int(player.health)}\n"
            ehp_tooltip += f"  • Block Multiplier: {block_mult:.3f}x ({player.block_chance*100:.1f}% block)\n"
            ehp_tooltip += f"  • Damage Reduction: {dmg_reduction_mult:.3f}x\n"
            ehp_tooltip += f"    - Base Enemy Dmg: {base_avg_dmg:.1f}/hit\n"
            ehp_tooltip += f"    - Actual Enemy Dmg: {actual_avg_dmg:.1f}/hit\n"
            ehp_tooltip += f"    - ATK Debuff: -{base_enemy_atk - actual_enemy_atk:.1f} ATK\n"
            ehp_tooltip += f"    - Crit Debuff: -{base_enemy_crit - enemy_stats.crit:.1f}% crit, -{base_enemy_crit_dmg - actual_enemy_crit_dmg:.2f}x crit dmg\n"
            ehp_tooltip += f"\nTotal eHP: {ehp_at_target:.0f} ({ehp_mult:.2f}x base HP)\n"
            ehp_tooltip += f"Formula: HP × {block_mult:.3f} × {dmg_reduction_mult:.3f} = {ehp_at_target:.0f}"
            
            stat_rows.append((
                "Effective HP:", 
                lambda: f"{ehp_at_target:.0f} ({ehp_mult:.2f}x)", 
                "💚",
                ehp_tooltip
            ))
        
        # Add remaining stats
        stat_rows.extend([
            ("Attack Damage:", lambda: f"{int(player.atk)}", "⚔", None),
            ("Attack Speed:", lambda: f"{player.atk_speed:.2f}", "🌀", None),
            ("Move Speed:", lambda: f"{player.walk_speed:.2f}", "👢", None),
            ("Crit Chance:", lambda: f"{player.crit}%", "⭐", None),
            ("Crit Damage:", lambda: f"{player.crit_dmg:.2f}x", "⭐", None),
            ("Event Speed:", lambda: f"{player.game_speed:.2f}x", "⏱", None),
            ("Block Chance:", lambda: f"{player.block_chance*100:.0f}%", "🛡", None),
            ("Prestige Hp/Dmg:", lambda: f"{prestige_mult:.2f}x", "⬆", 
             f"Multiplier from Prestige {prestige}:\n• Base: +10% per prestige\n• Bonus: +{player.prestige_bonus_scale*100:.0f}% per prestige (from upgrades)\n• Total: {prestige_mult:.2f}x HP and ATK"),
            ("2x Currencies:", lambda: f"{player.x2_money}", "💰", None),
            ("5x Currencies:", lambda: f"{player.x5_money}%", "💎", None),
        ])
        
        # Create stat rows - centered and compact
        for label, value_func, icon, tooltip_text in stat_rows:
            row_frame = tk.Frame(self.stats_container, background="#2C2C2C")
            row_frame.pack(fill=tk.X, pady=1)
            
            # Center the row content
            inner_frame = tk.Frame(row_frame, background="#2C2C2C")
            inner_frame.pack(expand=True)
            
            # Label on left
            label_widget = tk.Label(inner_frame, text=label, font=("Arial", 8), 
                    background="#2C2C2C", foreground="white",
                    anchor="w", width=16)
            label_widget.pack(side=tk.LEFT, padx=(0, 3))
            
            # Help icon with tooltip if tooltip_text is provided
            if tooltip_text:
                help_icon = tk.Label(inner_frame, text="?", font=("Arial", 8, "bold"),
                        background="#2C2C2C", foreground="#888888",
                        cursor="hand2", width=2)
                help_icon.pack(side=tk.LEFT, padx=(0, 3))
                create_tooltip(help_icon, tooltip_text)
            
            # Icon
            icon_widget = tk.Label(inner_frame, text=icon, font=("Arial", 9),
                    background="#2C2C2C", foreground="#888888",
                    width=2)
            icon_widget.pack(side=tk.LEFT, padx=(0, 5))
            
            # Value on right
            value_label = tk.Label(inner_frame, text=value_func(), font=("Arial", 8, "bold"),
                                  background="#2C2C2C", foreground="white",
                                  anchor="e", width=18)
            value_label.pack(side=tk.LEFT)
    
    def save_state(self):
        """Save current state to file (upgrade levels and prestige, NOT currencies)"""
        try:
            # Ensure save directory exists
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            
            state = {
                'prestige': self.budget_prestige_var.get(),
                'upgrade_levels': {
                    tier: levels.copy() 
                    for tier, levels in self.current_upgrade_levels.items()
                },
                'gem_levels': self.current_gem_levels.copy()
            }
            
            # Write to temporary file first, then rename (atomic write)
            temp_file = SAVE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Atomic rename
            temp_file.replace(SAVE_FILE)
            
        except Exception as e:
            import traceback
            print(f"Warning: Could not save state: {e}")
            traceback.print_exc()
    
    def load_state(self):
        """Load saved state from file"""
        if not SAVE_FILE.exists():
            print(f"Save file does not exist: {SAVE_FILE}")
            return
        
        try:
            with open(SAVE_FILE, 'r') as f:
                state = json.load(f)
            
            # Debug prints removed
            # print(f"Loading state from: {SAVE_FILE}")
            # print(f"State keys: {state.keys()}")
            
            # Load prestige
            if 'prestige' in state:
                self.budget_prestige_var.set(state['prestige'])
                # Debug print removed: print(f"Loaded prestige: {state['prestige']}")
            
            # Load upgrade levels
            if 'upgrade_levels' in state:
                upgrade_levels = state['upgrade_levels']
                # JSON stores dict keys as strings, so we need to handle both int and str keys
                for tier in range(1, 5):
                    # Try both int and str key
                    tier_key = tier
                    if tier_key not in upgrade_levels:
                        tier_key = str(tier)
                    
                    if tier_key in upgrade_levels:
                        saved_levels = upgrade_levels[tier_key]
                        # Ensure we have the right length
                        if isinstance(saved_levels, list) and len(saved_levels) == len(self.current_upgrade_levels[tier]):
                            self.current_upgrade_levels[tier] = saved_levels.copy()
                            # Debug print removed: print(f"Loaded Tier {tier} upgrades: {saved_levels} (total: {sum(saved_levels)})")
                        else:
                            # Debug print removed: print(f"Warning: Tier {tier} upgrade levels length mismatch: {len(saved_levels)} != {len(self.current_upgrade_levels[tier])}")
                            pass
                    # else:
                        # Debug print removed: print(f"Warning: Tier {tier} not found in upgrade_levels")
            
            # Load gem levels
            if 'gem_levels' in state:
                saved_gems = state['gem_levels']
                if isinstance(saved_gems, list) and len(saved_gems) == len(self.current_gem_levels):
                    self.current_gem_levels = saved_gems.copy()
                    # Debug print removed: print(f"Loaded gem levels: {saved_gems}")
            
            # Rebuild UI to reflect loaded state
            self._build_upgrade_level_inputs()
            
        except Exception as e:
            import traceback
            print(f"Warning: Could not load state: {e}")
            traceback.print_exc()
    
    def show_initial_instructions(self):
        """Show initial instructions in results area"""
        # Clear container
        for widget in self.results_container.winfo_children():
            widget.destroy()
        
        info_frame = tk.Frame(self.results_container, background="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        text = "Enter your materials above and click 'Calculate Optimal Upgrades'\n\n"
        text += "The optimizer will recommend:\n"
        text += "  • Which upgrades to buy for each material type\n"
        text += "  • Expected wave you can reach\n"
        text += "  • Materials left over after upgrades"
        
        tk.Label(info_frame, text=text, font=("Arial", 9), 
                background="#FFFFFF", justify=tk.LEFT, anchor="nw",
                padx=10, pady=10).pack(fill=tk.BOTH, expand=True)
    
    def _validate_material_entry(self, tier):
        """Validate and update material entry when focus is lost"""
        if tier in self.material_vars:
            var = self.material_vars[tier]
            val = var.get().strip() if var.get() else ""
            # Clean the value
            val = val.replace(",", "").replace(" ", "")
            if val:
                try:
                    float(val)  # Validate it's a number
                except ValueError:
                    var.set("0")  # Reset to 0 if invalid
            else:
                var.set("0")
    
    def calculate_optimal_upgrades(self):
        """Calculate optimal upgrades based on material budget"""
        # Parse material inputs - read directly from entry widgets
        try:
            total_budget = 0
            for i in range(1, 5):
                # Get value directly from Entry widget (more reliable than StringVar)
                raw_val = ""
                if i in self.material_entries:
                    entry = self.material_entries[i]
                    raw_val = entry.get() if entry else ""
                elif i in self.material_vars:
                    # Fallback to StringVar if entry not available
                    var = self.material_vars[i]
                    raw_val = var.get() if var else ""
                else:
                    raw_val = ""
                
                # Clean the value
                if raw_val:
                    val = str(raw_val).strip()
                    # Remove thousand separators (commas) but keep decimal points
                    val = val.replace(",", "").replace(" ", "")
                else:
                    val = ""
                
                # Convert to float (handles both integers and decimals)
                if val:
                    try:
                        self.material_budget[i] = float(val)
                    except (ValueError, TypeError):
                        self.material_budget[i] = 0.0
                else:
                    self.material_budget[i] = 0.0
                
                total_budget += self.material_budget[i]
            
            # Check if any budget was entered
            if total_budget == 0 or total_budget < 0.001:
                # Show error in expected results container instead
                for widget in self.expected_results_container.winfo_children():
                    widget.destroy()
                error_label = tk.Label(self.expected_results_container, 
                                      text="Error: Please enter at least some materials", 
                                      font=("Arial", 9), foreground="red",
                                      background="#E8F5E9")
                error_label.pack(pady=20)
                return
            
            # Check if budget is large enough for at least one upgrade
            from .constants import COSTS, PRESTIGE_UNLOCKED
            min_cost = float('inf')
            prestige = self.budget_prestige_var.get()
            for tier in range(1, 5):
                for idx in range(len(COSTS[tier])):
                    if PRESTIGE_UNLOCKED[tier][idx] <= prestige:
                        base_cost = COSTS[tier][idx]
                        if base_cost < min_cost:
                            min_cost = base_cost
            
            if total_budget < min_cost:
                # Show error in expected results container instead
                for widget in self.expected_results_container.winfo_children():
                    widget.destroy()
                error_label = tk.Label(self.expected_results_container, 
                                      text=f"Error: Budget too small!\nMinimum cost: {int(min_cost)}\nYour budget: {int(total_budget)}", 
                                      font=("Arial", 9), foreground="red",
                                      background="#E8F5E9", justify=tk.LEFT)
                error_label.pack(pady=20)
                return
        except (ValueError, TypeError, AttributeError) as e:
            # Show error in expected results container instead
            for widget in self.expected_results_container.winfo_children():
                widget.destroy()
            error_label = tk.Label(self.expected_results_container, 
                                  text=f"Error: Please enter valid numbers for materials\n{str(e)}", 
                                  font=("Arial", 9), foreground="red",
                                  background="#E8F5E9")
            error_label.pack(pady=20)
            return
        
        prestige = self.budget_prestige_var.get()
        next_prestige_wave = get_prestige_wave_requirement(prestige + 1)
        
        # Show loading
        for widget in self.results_container.winfo_children():
            widget.destroy()
        loading_label = tk.Label(self.results_container, text="Forecasting...", 
                                font=("Arial", 10), background="#E8F5E9")
        loading_label.pack(pady=20)
        self.window.update()
        
        # Create initial state from current upgrade levels
        initial_state = UpgradeState()
        for t in range(1, 5):
            initial_state.levels[t] = self.current_upgrade_levels[t].copy()
        initial_state.gem_levels = self.current_gem_levels.copy()
        
        # Run optimizer with initial state (Wave Pusher mode - maximize wave)
        try:
            result = greedy_optimize(
                budget=self.material_budget,
                prestige=prestige,
                target_wave=None,  # None = maximize wave (Wave Pusher mode)
                initial_state=initial_state
            )
        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n\n{traceback.format_exc()}"
            # Show error in expected results container instead
            for widget in self.expected_results_container.winfo_children():
                widget.destroy()
            error_label = tk.Label(self.expected_results_container, 
                                  text=f"Error: {str(e)}", 
                                  font=("Arial", 9), foreground="red",
                                  background="#E8F5E9", justify=tk.LEFT, wraplength=300)
            error_label.pack(pady=20)
            return
        
        # Store result for applying upgrades
        self.last_optimization_result = result
        self.last_initial_state = initial_state
        
        # Update player stats with CURRENT upgrades (not recommended ones)
        # This ensures the stats display shows current state, not forecast state
        self._update_player_stats()
        
        # Reset apply button state (new optimization = button can be used again)
        self.apply_button = None
        
        # Clear and rebuild results display
        for widget in self.results_container.winfo_children():
            widget.destroy()
        
        # === MATERIAL SUMMARY (2x2 grid) ===
        mat_summary_frame = tk.Frame(self.results_container, background="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        mat_summary_frame.pack(fill=tk.X, padx=3, pady=2)
        
        tk.Label(mat_summary_frame, text="Materials", font=("Arial", 9, "bold"),
                background="#FFFFFF").pack(anchor="w", padx=5, pady=2)
        
        mat_grid = tk.Frame(mat_summary_frame, background="#FFFFFF")
        mat_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        mat_grid.columnconfigure(0, weight=1)
        mat_grid.columnconfigure(1, weight=1)
        mat_grid.rowconfigure(0, weight=1)
        mat_grid.rowconfigure(1, weight=1)
        
        # Arrange materials in 2x2 grid: T1 top-left, T2 top-right, T3 bottom-left, T4 bottom-right
        positions = [
            (0, 0),  # T1 top-left
            (0, 1),  # T2 top-right
            (1, 0),  # T3 bottom-left
            (1, 1),  # T4 bottom-right
        ]
        
        for tier in range(1, 5):
            row, col = positions[tier - 1]
            mat_name = f"Mat {tier}" if tier > 1 else "Coins"
            budget = self.material_budget[tier]
            spent = result.materials_spent[tier]
            remaining = result.materials_remaining[tier]
            
            tier_frame = tk.Frame(mat_grid, background="#FFFFFF", relief=tk.RAISED, borderwidth=1)
            tier_frame.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
            
            # Icon if available
            if tier in self.currency_icons:
                icon_label = tk.Label(tier_frame, image=self.currency_icons[tier],
                                     background="#FFFFFF")
                icon_label.pack(side=tk.LEFT, padx=(5, 3))
            
            text_frame = tk.Frame(tier_frame, background="#FFFFFF")
            text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            tk.Label(text_frame, text=f"{mat_name}:", font=("Arial", 9, "bold"),
                    background="#FFFFFF", anchor="w", wraplength=100).pack(anchor="w")
            tk.Label(text_frame, text=f"{int(spent):,}/{int(budget):,}", 
                    font=("Arial", 9, "bold"), background="#FFFFFF",
                    foreground="#4CAF50" if spent > 0 else "#999999",
                    anchor="w", wraplength=100).pack(anchor="w")
            if remaining > 0:
                tk.Label(text_frame, text=f"Remaining: {int(remaining):,}", 
                        font=("Arial", 8), background="#FFFFFF",
                        foreground="#666666", anchor="w", wraplength=100).pack(anchor="w")
        
        # === APPLY UPGRADES BUTTON (compact) ===
        apply_btn_frame = tk.Frame(self.results_container, background="#E8F5E9", relief=tk.RAISED, borderwidth=2)
        apply_btn_frame.pack(fill=tk.X, padx=3, pady=2)
        
        # Button and help icon in horizontal layout
        button_row = tk.Frame(apply_btn_frame, background="#E8F5E9")
        button_row.pack(pady=3)
        
        self.apply_button = tk.Button(button_row, text="✨ Add Points!", 
                             font=("Arial", 9, "bold"), bg="#4CAF50", fg="white",
                             command=self._apply_recommended_upgrades,
                             relief=tk.RAISED, borderwidth=2, padx=8, pady=4,
                             cursor="hand2", state=tk.NORMAL)
        self.apply_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Help icon with tooltip
        help_label = tk.Label(button_row, text="?", font=("Arial", 10, "bold"),
                             background="#E8F5E9", foreground="#666666", cursor="hand2",
                             width=2, height=1, relief=tk.RAISED, borderwidth=1)
        help_label.pack(side=tk.LEFT)
        create_tooltip(help_label, "Automatically apply recommended upgrades to your current levels")
        
        # === UPGRADE CARDS (Game-style) ===
        upgrades_frame = tk.Frame(self.results_container, background="#E8F5E9")
        upgrades_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
        
        tk.Label(upgrades_frame, text="Recommended Upgrades", font=("Arial", 9, "bold"),
                background="#E8F5E9").pack(anchor="w", padx=5, pady=2)
        
        # Scrollable upgrade area (more space now)
        upgrade_canvas = tk.Canvas(upgrades_frame, highlightthickness=0, height=350)
        upgrade_scrollbar = ttk.Scrollbar(upgrades_frame, orient="vertical", command=upgrade_canvas.yview)
        upgrade_scrollable = tk.Frame(upgrade_canvas)
        
        upgrade_scrollable.bind(
            "<Configure>",
            lambda e: upgrade_canvas.configure(scrollregion=upgrade_canvas.bbox("all"))
        )
        
        upgrade_canvas.create_window((0, 0), window=upgrade_scrollable, anchor="nw")
        upgrade_canvas.configure(yscrollcommand=upgrade_scrollbar.set)
        
        upgrade_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        upgrade_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create upgrade cards for each tier
        # Only show upgrades that would be ADDED (difference between current and recommended)
        has_upgrades = False
        for tier in range(1, 5):
            tier_upgrades = []
            for idx, recommended_level in enumerate(result.upgrades.levels[tier]):
                initial_level = initial_state.levels[tier][idx]
                # Only show if recommended level is higher than current level
                if recommended_level > initial_level:
                    added_levels = recommended_level - initial_level
                    tier_upgrades.append((idx, added_levels))
            
            if not tier_upgrades:
                continue
            
            has_upgrades = True
            
            # Tier header (compact)
            tier_header = tk.Frame(upgrade_scrollable, background=TIER_COLORS[tier], relief=tk.RAISED, borderwidth=1)
            tier_header.pack(fill=tk.X, padx=2, pady=(3, 1))
            
            tk.Label(tier_header, text=f"Tier {tier} ({TIER_MAT_NAMES[tier]})", 
                    font=("Arial", 8, "bold"), background=TIER_COLORS[tier]).pack(padx=5, pady=1)
            
            # Upgrade cards grid (3 per row for compactness)
            cards_frame = tk.Frame(upgrade_scrollable, background="#E8F5E9")
            cards_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
            cards_frame.columnconfigure(0, weight=1)
            cards_frame.columnconfigure(1, weight=1)
            cards_frame.columnconfigure(2, weight=1)
            
            # Create cards in a grid (3 per row)
            for i, (idx, level) in enumerate(tier_upgrades):
                row = i // 3
                col = i % 3
                
                # Upgrade card (compact, game-style)
                card = tk.Frame(cards_frame, background="#FFFFFF", relief=tk.RAISED, borderwidth=1)
                card.grid(row=row, column=col, padx=2, pady=1, sticky="ew")
                
                # Card content (compact) with icon
                name = UPGRADE_SHORT_NAMES[tier][idx]
                
                # Icon if available
                card_content = tk.Frame(card, background="#FFFFFF")
                card_content.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
                
                if (tier, idx) in self.upgrade_icons:
                    icon_label = tk.Label(card_content, image=self.upgrade_icons[(tier, idx)],
                                         background="#FFFFFF")
                    icon_label.pack(side=tk.LEFT, padx=(0, 3))
                
                # Text content
                text_frame = tk.Frame(card_content, background="#FFFFFF")
                text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                # Name (with word wrap)
                tk.Label(text_frame, text=name, font=("Arial", 8, "bold"),
                        background="#FFFFFF", anchor="w", wraplength=120, justify=tk.LEFT).pack(fill=tk.X, pady=1)
                # Show "+X" to indicate how many levels would be added
                tk.Label(text_frame, text=f"+{level}", font=("Arial", 8),
                        background="#FFFFFF", foreground="#4CAF50", anchor="w", wraplength=120).pack(fill=tk.X)
        
        # Show message if no upgrades were recommended
        if not has_upgrades:
            no_upgrades_label = tk.Label(upgrade_scrollable, 
                                        text="No upgrades recommended.\n\nPossible reasons:\n• Budget too small for any upgrade\n• All upgrades already at max level\n• No upgrades unlocked at current prestige",
                                        font=("Arial", 9), background="#E8F5E9",
                                        foreground="#666666", justify=tk.LEFT)
            no_upgrades_label.pack(pady=20, padx=10)
        