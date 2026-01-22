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
                    self.currency_icons[tier] = ImageTk.PhotoImage(icon_image)
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
                    self.upgrade_icons[(tier, idx)] = ImageTk.PhotoImage(icon_image)
        except Exception as e:
            print(f"Warning: Could not load upgrade icons: {e}")
            pass  # Graceful fallback
    
    def build_ui(self):
        """Build the Budget Optimizer UI - Three columns: Budget/Upgrades | Forecast | Stats"""
        self.parent.columnconfigure(0, weight=1)
        self.parent.columnconfigure(1, weight=1)
        self.parent.columnconfigure(2, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Main container with three columns
        main_container = tk.Frame(self.parent)
        main_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        main_container.columnconfigure(0, weight=1)  # Left (budget + upgrades)
        main_container.columnconfigure(1, weight=1)   # Middle (forecast/results)
        main_container.columnconfigure(2, weight=1)   # Right (player stats)
        main_container.rowconfigure(0, weight=1)
        
        # === LEFT COLUMN: Budget + Upgrades (no scrolling) ===
        left_column = tk.Frame(main_container, background="#F5F5F5")
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        left_column.columnconfigure(0, weight=1)
        
        # === HEADER ===
        header_frame = tk.Frame(left_column, background="#4CAF50", relief=tk.RIDGE, borderwidth=2)
        header_frame.pack(fill=tk.X, padx=3, pady=2)
        
        tk.Label(header_frame, text="Budget & Upgrades", font=("Arial", 10, "bold"),
                background="#4CAF50", foreground="white").pack(pady=3)
        
        # === MATERIAL INPUT ===
        input_frame = tk.Frame(left_column, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        input_frame.pack(fill=tk.X, padx=3, pady=2)
        
        tk.Label(input_frame, text="Materials", font=("Arial", 9, "bold"),
                background="#E8F5E9").pack(anchor="w", padx=5, pady=(3, 2))
        
        mat_inner = tk.Frame(input_frame, background="#E8F5E9")
        mat_inner.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        mat_names = ["Coins", "M2", "M3", "M4"]
        mat_colors = ["#FFC107", "#9C27B0", "#00BCD4", "#E91E63"]
        
        # Compact grid layout for materials
        for i in range(4):
            col_frame = tk.Frame(mat_inner, background="#E8F5E9")
            col_frame.grid(row=0, column=i, padx=2)
            
            tier = i + 1
            if tier in self.currency_icons:
                icon_label = tk.Label(col_frame, image=self.currency_icons[tier],
                                     background="#E8F5E9")
                icon_label.pack()
            
            tk.Label(col_frame, text=mat_names[i], font=("Arial", 7, "bold"),
                    background="#E8F5E9", foreground=mat_colors[i]).pack()
            
            var = tk.StringVar(value="0")
            entry = ttk.Entry(col_frame, textvariable=var, width=8, font=("Arial", 8))
            entry.pack(pady=2)
            entry.bind('<Return>', lambda e: self.calculate_optimal_upgrades())
            
            self.material_vars[tier] = var
        
        # Prestige input (compact)
        prestige_frame = tk.Frame(mat_inner, background="#E8F5E9")
        prestige_frame.grid(row=0, column=4, padx=2)
        
        tk.Label(prestige_frame, text="P", font=("Arial", 7, "bold"),
                background="#E8F5E9").pack()
        
        self.budget_prestige_var = tk.IntVar(value=0)
        prestige_spin = ttk.Spinbox(prestige_frame, from_=0, to=20, width=4,
                                    textvariable=self.budget_prestige_var,
                                    command=self._on_prestige_change)
        prestige_spin.pack(pady=2)
        prestige_spin.bind('<Return>', lambda e: self._on_prestige_change())
        # Save when prestige changes
        self.budget_prestige_var.trace('w', lambda *args: self.save_state())
        
        # Calculate button (compact)
        calc_btn = tk.Button(input_frame, text="Forecast", 
                            font=("Arial", 9, "bold"), bg="#4CAF50", fg="white",
                            command=self.calculate_optimal_upgrades)
        calc_btn.pack(pady=3)
        
        # === CURRENT UPGRADE LEVELS (Forecast Mode) ===
        current_upgrades_frame = tk.Frame(left_column, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        current_upgrades_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
        
        tk.Label(current_upgrades_frame, text="Current Upgrade Levels", font=("Arial", 9, "bold"),
                background="#FFF3E0").pack(anchor="w", padx=5, pady=(3, 2))
        
        # Upgrade levels container (compact, no scrolling)
        self.upgrades_container = tk.Frame(current_upgrades_frame, background="#FFF3E0")
        self.upgrades_container.pack(fill=tk.BOTH, expand=True, padx=3, pady=(0, 3))
        self._build_upgrade_level_inputs()
        
        # === MIDDLE COLUMN: Forecast/Results ===
        middle_column = tk.Frame(main_container, background="#F5F5F5")
        middle_column.grid(row=0, column=1, sticky="nsew", padx=3)
        middle_column.columnconfigure(0, weight=1)
        
        # === RESULTS (fixed at top, no scrolling) ===
        results_frame = tk.Frame(middle_column, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
        
        tk.Label(results_frame, text="Forecast Results", font=("Arial", 10, "bold"),
                background="#E8F5E9").pack(anchor="w", padx=5, pady=(3, 2))
        
        # Results container (will be populated dynamically)
        self.results_container = tk.Frame(results_frame, background="#E8F5E9")
        self.results_container.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
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
        
        # Use grid for more compact layout
        row = 0
        for tier in range(1, 5):
            # Tier header (compact)
            tier_header = tk.Frame(self.upgrades_container, background=TIER_COLORS[tier], relief=tk.RAISED, borderwidth=1)
            tier_header.grid(row=row, column=0, columnspan=2, sticky="ew", padx=1, pady=(2, 1))
            row += 1
            
            tk.Label(tier_header, text=f"T{tier}", 
                    font=("Arial", 7, "bold"), background=TIER_COLORS[tier]).pack(side=tk.LEFT, padx=3, pady=1)
            
            # Upgrade rows (compact, 2 columns)
            for idx, name in enumerate(UPGRADE_SHORT_NAMES[tier]):
                col = idx % 2
                if idx % 2 == 0:
                    # New row every 2 upgrades
                    pass
                
                row_frame = tk.Frame(self.upgrades_container, background="#FFFFFF", relief=tk.FLAT, borderwidth=1)
                row_frame.grid(row=row, column=col, sticky="ew", padx=1, pady=0)
                
                if col == 0:
                    row += 1
                
                # Check if unlocked
                prestige_req = PRESTIGE_UNLOCKED[tier][idx]
                locked = prestige_req > prestige
                
                if locked:
                    row_frame.config(background="#CCCCCC")
                    tk.Label(row_frame, text=f"{name[:8]} (P{prestige_req})", 
                            font=("Arial", 6), background="#CCCCCC", 
                            foreground="#666666", anchor="w").pack(side=tk.LEFT, padx=2)
                    continue
                
                # Get max level
                max_level = get_max_level_with_caps(tier, idx, temp_state)
                current_level = self.current_upgrade_levels[tier][idx]
                
                # Compact layout: [Name] [Level] [Cost] [+/-]
                # Name (truncated)
                name_label = tk.Label(row_frame, text=name[:10], font=("Arial", 6), 
                                     background="#FFFFFF", anchor="w", width=10)
                name_label.pack(side=tk.LEFT, padx=2)
                
                # Level display (compact)
                level_text = f"{current_level}/{max_level}"
                level_label = tk.Label(row_frame, text=level_text, 
                                      font=("Arial", 6, "bold"), background="#FFFFFF", 
                                      width=5, anchor=tk.CENTER)
                level_label.pack(side=tk.LEFT, padx=1)
                
                # Next cost (compact)
                if current_level < max_level:
                    from .constants import COSTS
                    base_cost = COSTS[tier][idx]
                    next_cost = round(base_cost * (1.25 ** current_level))
                    cost_text = f"{next_cost:,}" if next_cost < 1000 else f"{next_cost/1000:.1f}k"
                    cost_label = tk.Label(row_frame, text=cost_text, 
                                         font=("Arial", 5), background="#FFFFFF", 
                                         foreground="#666666", anchor="e", width=6)
                    cost_label.pack(side=tk.LEFT, padx=1)
                else:
                    tk.Label(row_frame, text="MAX", font=("Arial", 5), background="#FFFFFF", 
                            foreground="#999999", anchor="e", width=6).pack(side=tk.LEFT, padx=1)
                
                # Minus button (compact)
                minus_btn = tk.Button(row_frame, text="-", width=1, font=("Arial", 6, "bold"),
                                    command=lambda t=tier, i=idx: self._decrement_upgrade(t, i),
                                    state='disabled' if current_level == 0 else 'normal')
                minus_btn.pack(side=tk.LEFT, padx=(1, 0))
                
                # Plus button (compact)
                plus_btn = tk.Button(row_frame, text="+", width=1, font=("Arial", 6, "bold"),
                                   command=lambda t=tier, i=idx: self._increment_upgrade(t, i),
                                   state='disabled' if current_level >= max_level else 'normal')
                plus_btn.pack(side=tk.LEFT, padx=(0, 2))
                
                # Store references for updates
                self.upgrade_level_labels[(tier, idx)] = (level_label, minus_btn, plus_btn, max_level)
        
        # Configure grid columns
        self.upgrades_container.columnconfigure(0, weight=1)
        self.upgrades_container.columnconfigure(1, weight=1)
    
    def _on_prestige_change(self):
        """Update upgrade inputs when prestige changes"""
        self._build_upgrade_level_inputs()
    
    def _increment_upgrade(self, tier: int, idx: int):
        """Increment upgrade level"""
        from .optimizer import get_max_level_with_caps, UpgradeState
        
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
            # Rebuild to update all max levels (cap upgrades might have changed other max levels)
            # This ensures all buttons are properly enabled/disabled
            self._build_upgrade_level_inputs()
            self.save_state()  # Auto-save on change
    
    def _decrement_upgrade(self, tier: int, idx: int):
        """Decrement upgrade level"""
        if (tier, idx) not in self.upgrade_level_labels:
            return
        
        if self.current_upgrade_levels[tier][idx] > 0:
            self.current_upgrade_levels[tier][idx] -= 1
            # Rebuild to update all max levels (cap upgrades might have changed other max levels)
            self._build_upgrade_level_inputs()
            self.save_state()  # Auto-save on change
    
    def _update_upgrade_display(self, tier: int, idx: int):
        """Update upgrade level display (not used anymore, we rebuild instead)"""
        # This function is kept for compatibility but not actively used
        # We rebuild the entire UI instead to handle cap upgrade changes
        pass
    
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
            stat_rows.append((
                "Effective HP:", 
                lambda: f"{ehp_at_target:.0f} ({ehp_mult:.2f}x)", 
                "💚",
                f"Effective HP accounts for:\n• Base HP: {int(player.health)}\n• Block Chance: {player.block_chance*100:.0f}% (reduces damage)\n• Enemy ATK Debuffs: reduces damage per hit\n\nAt Wave {next_prestige_wave}, you effectively have {ehp_at_target:.0f} HP\n({ehp_mult:.2f}x your base HP)"
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
            state = {
                'prestige': self.budget_prestige_var.get(),
                'upgrade_levels': {
                    tier: levels.copy() 
                    for tier, levels in self.current_upgrade_levels.items()
                },
                'gem_levels': self.current_gem_levels.copy()
            }
            
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
            
            # Load prestige
            if 'prestige' in state:
                self.budget_prestige_var.set(state['prestige'])
            
            # Load upgrade levels
            if 'upgrade_levels' in state:
                for tier in range(1, 5):
                    if tier in state['upgrade_levels']:
                        saved_levels = state['upgrade_levels'][tier]
                        # Ensure we have the right length
                        if isinstance(saved_levels, list) and len(saved_levels) == len(self.current_upgrade_levels[tier]):
                            self.current_upgrade_levels[tier] = saved_levels.copy()
            
            # Load gem levels
            if 'gem_levels' in state:
                saved_gems = state['gem_levels']
                if isinstance(saved_gems, list) and len(saved_gems) == len(self.current_gem_levels):
                    self.current_gem_levels = saved_gems.copy()
            
            # Rebuild UI to reflect loaded state
            self._build_upgrade_level_inputs()
            
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
    
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
    
    def calculate_optimal_upgrades(self):
        """Calculate optimal upgrades based on material budget"""
        # Parse material inputs
        try:
            for i in range(1, 5):
                val = self.material_vars[i].get().replace(",", "").replace(".", "")
                self.material_budget[i] = float(val) if val else 0
        except ValueError:
            # Show error in results container
            for widget in self.results_container.winfo_children():
                widget.destroy()
            error_label = tk.Label(self.results_container, 
                                  text="Error: Please enter valid numbers for materials", 
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
            for widget in self.results_container.winfo_children():
                widget.destroy()
            error_label = tk.Label(self.results_container, 
                                  text=f"Error: {str(e)}", 
                                  font=("Arial", 9), foreground="red",
                                  background="#E8F5E9")
            error_label.pack(pady=20)
            return
        
        # Calculate eHP at estimated max wave
        estimated_wave = int(result.expected_wave)
        ehp_at_target = calculate_effective_hp(result.player_stats, result.enemy_stats, estimated_wave)
        self.update_player_stats_display(result, estimated_wave, ehp_at_target)
        
        # Store result for applying upgrades
        self.last_optimization_result = result
        self.last_initial_state = initial_state
        
        # Reset apply button state (new optimization = button can be used again)
        self.apply_button = None
        
        # Clear and rebuild results display
        for widget in self.results_container.winfo_children():
            widget.destroy()
        
        # === MATERIAL SUMMARY (compact) ===
        mat_summary_frame = tk.Frame(self.results_container, background="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        mat_summary_frame.pack(fill=tk.X, padx=3, pady=2)
        
        tk.Label(mat_summary_frame, text="Materials", font=("Arial", 9, "bold"),
                background="#FFFFFF").pack(anchor="w", padx=5, pady=2)
        
        mat_grid = tk.Frame(mat_summary_frame, background="#FFFFFF")
        mat_grid.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        for tier in range(1, 5):
            mat_name = f"Mat {tier}" if tier > 1 else "Coins"
            budget = self.material_budget[tier]
            spent = result.materials_spent[tier]
            remaining = result.materials_remaining[tier]
            
            tier_frame = tk.Frame(mat_grid, background="#FFFFFF")
            tier_frame.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
            
            # Icon if available
            if tier in self.currency_icons:
                icon_label = tk.Label(tier_frame, image=self.currency_icons[tier],
                                     background="#FFFFFF")
                icon_label.pack(side=tk.LEFT, padx=(0, 3))
            
            tk.Label(tier_frame, text=f"{mat_name}:", font=("Arial", 8),
                    background="#FFFFFF").pack(side=tk.LEFT)
            tk.Label(tier_frame, text=f"{int(spent):,}/{int(budget):,}", 
                    font=("Arial", 8, "bold"), background="#FFFFFF",
                    foreground="#4CAF50" if spent > 0 else "#999999").pack(side=tk.LEFT, padx=(3, 0))
        
        # === APPLY UPGRADES BUTTON (prominent) ===
        apply_btn_frame = tk.Frame(self.results_container, background="#E8F5E9", relief=tk.RAISED, borderwidth=2)
        apply_btn_frame.pack(fill=tk.X, padx=3, pady=3)
        
        self.apply_button = tk.Button(apply_btn_frame, text="✨ Add Points!", 
                             font=("Arial", 11, "bold"), bg="#4CAF50", fg="white",
                             command=self._apply_recommended_upgrades,
                             relief=tk.RAISED, borderwidth=2, padx=15, pady=8,
                             cursor="hand2", state=tk.NORMAL)
        self.apply_button.pack(pady=5)
        
        tk.Label(apply_btn_frame, 
                text="Automatically apply recommended upgrades to your current levels",
                font=("Arial", 8, "italic"), background="#E8F5E9",
                foreground="#666666").pack(pady=(0, 5))
        
        # === EXPECTED RESULTS (compact) ===
        results_summary_frame = tk.Frame(self.results_container, background="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        results_summary_frame.pack(fill=tk.X, padx=3, pady=2)
        
        tk.Label(results_summary_frame, text="Expected Results", font=("Arial", 9, "bold"),
                background="#FFFFFF").pack(anchor="w", padx=5, pady=2)
        
        results_inner = tk.Frame(results_summary_frame, background="#FFFFFF")
        results_inner.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Wave Pusher Mode: Show max wave
        tk.Label(results_inner, text=f"Max Wave: {result.expected_wave:.1f} | ", 
                font=("Arial", 8, "bold"), background="#FFFFFF",
                foreground="#1976D2").pack(side=tk.LEFT)
        tk.Label(results_inner, text=f"Time/Run: {result.expected_time:.1f}s", 
                font=("Arial", 8), background="#FFFFFF").pack(side=tk.LEFT)
        
        # === UPGRADE CARDS (Game-style) ===
        upgrades_frame = tk.Frame(self.results_container, background="#E8F5E9")
        upgrades_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
        
        tk.Label(upgrades_frame, text="Recommended Upgrades", font=("Arial", 9, "bold"),
                background="#E8F5E9").pack(anchor="w", padx=5, pady=2)
        
        # Scrollable upgrade area (compact height)
        upgrade_canvas = tk.Canvas(upgrades_frame, highlightthickness=0, height=250)
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
        for tier in range(1, 5):
            tier_upgrades = []
            for idx, level in enumerate(result.upgrades.levels[tier]):
                if level > 0:
                    tier_upgrades.append((idx, level))
            
            if not tier_upgrades:
                continue
            
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
                
                # Name (truncate if too long)
                display_name = name[:15] + "..." if len(name) > 15 else name
                tk.Label(text_frame, text=display_name, font=("Arial", 7, "bold"),
                        background="#FFFFFF", anchor="w", wraplength=80).pack(fill=tk.X)
                tk.Label(text_frame, text=f"Lv.{level}", font=("Arial", 7),
                        background="#FFFFFF", foreground="#666666", anchor="w").pack(fill=tk.X)
        
        # === BREAKPOINT SUMMARY (compact) ===
        if result.breakpoints:
            bp_frame = tk.Frame(self.results_container, background="#FFFFFF", relief=tk.RAISED, borderwidth=1)
            bp_frame.pack(fill=tk.X, padx=3, pady=2)
            
            tk.Label(bp_frame, text="Next Breakpoint", font=("Arial", 8, "bold"),
                    background="#FFFFFF").pack(anchor="w", padx=5, pady=1)
            
            best_bp = result.breakpoints[0]
            bp_text = f"Wave {best_bp['wave']}: +{best_bp['atk_increase']} ATK → {best_bp['target_hits']}-hit kills"
            tk.Label(bp_frame, text=bp_text, font=("Arial", 7),
                    background="#FFFFFF").pack(anchor="w", padx=5, pady=(0, 3))
