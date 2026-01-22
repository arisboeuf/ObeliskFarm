"""
Lootbug - Option Analyzer & Loot Tables

Analyzes whether specific gem purchases are worth it based on current EV/h.
Also shows lootbug reward tables with weights.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk
import json

import sys
import os
sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import create_tooltip as _create_tooltip, calculate_tooltip_position, get_resource_path


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
SAVE_FILE = SAVE_DIR / "lootbug_save.json"

# Lootbug Reward Data
# Free Buffs - no gem cost
FREE_BUFFS = [
    {
        'name': '+2 Gems',
        'duration': None,
        'weight': 30,
        'requirement': None,
    },
    {
        'name': '+1 Item Chest',
        'duration': None,
        'weight': 35,
        'requirement': None,
    },
    {
        'name': '+1 Relic Chest',
        'duration': None,
        'weight': 5,
        'requirement': None,
    },
    {
        'name': '+10 Cherry Charges',
        'duration': None,
        'weight': 20,
        'requirement': 'Cherry Bomb + Obelisk Lvl 10',
    },
    {
        'name': '2x Ore Income',
        'duration': '2 min',
        'weight': 15,
        'requirement': None,
    },
    {
        'name': '3x Vein Spawn Rate',
        'duration': '2 min',
        'weight': 20,
        'requirement': 'Stone Vein Research',
    },
    {
        'name': '2x Game Speed',
        'duration': '2 min',
        'weight': 15,
        'requirement': None,
    },
    {
        'name': '2x Star Spawn Rate',
        'duration': '2 min',
        'weight': (16, 26),  # 16 base, 26 if Auto-Catch >= 75%
        'requirement': 'Telescope Lvl 1',
        'weight_note': '16 → 26 at ≥75% Auto-Catch',
    },
    {
        'name': '100% Auto-Catch',
        'duration': '4 min',
        'weight': (20, 0),  # 20 base, 0 if Auto-Catch >= 75%
        'requirement': 'Telescope Lvl 1',
        'weight_note': '20 → 0 at ≥75% Auto-Catch',
    },
]

# Gem Buffs - cost gems
GEM_BUFFS = [
    {
        'name': '+3 Item Chests',
        'duration': None,
        'cost': 15,
        'weight': (18, 14, 0),  # 18 base, 14 at Obelisk 37, 0 with Fishing
        'requirement': None,
        'weight_note': '18 → 14 (Ob.37) → 0 (Fishing)',
    },
    {
        'name': '+1 Relic Chest',
        'duration': None,
        'cost': 15,
        'weight': 10,
        'requirement': None,
    },
    {
        'name': '+100 Cherry Charges',
        'duration': None,
        'cost': 15,
        'weight': (20, 0),  # 20 base, 0 with Fishing
        'requirement': 'Cherry Bomb + Obelisk Lvl 10',
        'weight_note': '20 → 0 (Fishing unlocked)',
    },
    {
        'name': '2x Ore Income',
        'duration': '10 min',
        'cost': 15,
        'weight': 24,
        'requirement': None,
    },
    {
        'name': '3x Vein Spawn Rate',
        'duration': '10 min',
        'cost': 15,
        'weight': 20,
        'requirement': 'Stone Vein Research',
    },
    {
        'name': '2x Game Speed',
        'duration': '10 min',
        'cost': 15,
        'weight': 24,
        'requirement': None,
    },
    {
        'name': '10x Bomb Recharge',
        'duration': '2 min',
        'cost': 15,
        'weight': 8,
        'requirement': None,
    },
    {
        'name': '2x Star Spawn Rate',
        'duration': '10 min',
        'cost': 25,
        'weight': (16, 26),  # 16 base, 26 if Auto-Catch >= 75%
        'requirement': 'Telescope Lvl 1',
        'weight_note': '16 → 26 at ≥75% Auto-Catch',
    },
    {
        'name': '100% Auto-Catch',
        'duration': '20 min',
        'cost': 25,
        'weight': (20, 0),  # 20 base, 0 if Auto-Catch >= 75%
        'requirement': 'Telescope Lvl 1',
        'weight_note': '20 → 0 at ≥75% Auto-Catch',
    },
    {
        'name': 'Archaeology +600 Attacks',
        'duration': None,
        'cost': 25,
        'weight': 10,
        'requirement': 'Obelisk Lvl 30',
    },
    {
        'name': 'Fishing +12 Ticks',
        'duration': None,
        'cost': 35,
        'weight': 10,
        'requirement': 'Obelisk Lvl 37',
    },
]


class LootbugWindow:
    """Window for analyzing various purchase options and showing loot tables"""
    
    def __init__(self, parent, calculator=None):
        self.parent = parent
        self.calculator = calculator
        
        # Cost reduction (flat amount to subtract from all gem costs, can be negative)
        self.gem_cost_reduction = 0
        
        # Create new window - larger and resizable
        self.window = tk.Toplevel(parent)
        self.window.title("Lootbug - Option Analyzer & Loot Tables")
        self.window.state('zoomed')  # Maximize window on Windows
        self.window.resizable(True, True)
        self.window.minsize(900, 600)
        
        # Set icon (if available)
        try:
            icon_path = get_resource_path("sprites/lootbug/lootbug.png")
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.window.iconphoto(False, icon_photo)
        except:
            pass  # Ignore if icon can't be loaded
        
        self.create_widgets()
        self.load_state()
        
        # Auto-save on window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _on_close(self):
        """Handle window close - save state and destroy"""
        self.save_state()
        self.window.destroy()
    
    def save_state(self):
        """Save current state to file"""
        state = {
            'gem_cost_reduction': self.gem_cost_reduction,
        }
        try:
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            with open(SAVE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save lootbug state: {e}")
    
    def load_state(self):
        """Load saved state from file"""
        if not SAVE_FILE.exists():
            return
        try:
            with open(SAVE_FILE, 'r') as f:
                state = json.load(f)
            # Support both old (modifier) and new (reduction) format for migration
            if 'gem_cost_reduction' in state:
                self.gem_cost_reduction = state.get('gem_cost_reduction', 0)
            elif 'gem_cost_modifier' in state:
                # Migrate old percentage-based modifier to flat reduction
                # Old: 0.0 = free, 1.0 = normal, 0.5 = half price
                # New: flat reduction in gems
                old_modifier = state.get('gem_cost_modifier', 1.0)
                # For migration, we can't perfectly convert, so set to 0
                self.gem_cost_reduction = 0
            else:
                self.gem_cost_reduction = 0
            if hasattr(self, 'cost_reduction_var'):
                self.cost_reduction_var.set(str(self.gem_cost_reduction))
            self._update_loot_tables()
        except Exception as e:
            print(f"Warning: Could not load lootbug state: {e}")
    
    def create_widgets(self):
        """Creates the widgets in the window"""
        
        # Header with title and cost modifier
        header_frame = tk.Frame(self.window, background="#E3F2FD", relief=tk.RIDGE, borderwidth=1)
        header_frame.pack(fill=tk.X, padx=5, pady=(5, 2))
        
        # Left: Title
        title_label = tk.Label(
            header_frame,
            text="Lootbug - Option Analyzer & Loot Tables",
            font=("Arial", 14, "bold"),
            background="#E3F2FD"
        )
        title_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Right: Cost reduction controls
        controls_frame = tk.Frame(header_frame, background="#E3F2FD")
        controls_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        tk.Label(controls_frame, text="Gem Cost Reduction:", font=("Arial", 10), 
                background="#E3F2FD").pack(side=tk.LEFT, padx=(0, 3))
        
        # Preset buttons
        tk.Button(controls_frame, text="-1", width=3, font=("Arial", 8),
                 command=lambda: self._set_cost_reduction(-1)).pack(side=tk.LEFT, padx=1)
        tk.Button(controls_frame, text="0", width=3, font=("Arial", 8),
                 command=lambda: self._set_cost_reduction(0)).pack(side=tk.LEFT, padx=1)
        tk.Button(controls_frame, text="+1", width=3, font=("Arial", 8),
                 command=lambda: self._set_cost_reduction(1)).pack(side=tk.LEFT, padx=1)
        
        # Custom entry
        self.cost_reduction_var = tk.StringVar(value="0")
        cost_entry = ttk.Entry(controls_frame, textvariable=self.cost_reduction_var, width=5)
        cost_entry.pack(side=tk.LEFT, padx=(5, 1))
        tk.Label(controls_frame, text="Gems", font=("Arial", 10), 
                background="#E3F2FD").pack(side=tk.LEFT)
        self.cost_reduction_var.trace_add('write', self._on_cost_reduction_changed)
        
        # Help icon
        help_label = tk.Label(controls_frame, text="?", font=("Arial", 9, "bold"), 
                             cursor="hand2", foreground="#1976D2", background="#E3F2FD")
        help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_cost_reduction_tooltip(help_label)
        
        # Main content - two columns
        content_frame = tk.Frame(self.window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=2)
        content_frame.rowconfigure(0, weight=1)
        
        # Left column: Option Analyzer - dynamic content based on selected buff
        self.analyzer_frame = tk.Frame(content_frame, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        self.analyzer_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        
        # Store reference for rebuilding
        self.selected_buff = None
        self._build_analyzer_content()
        
        # Right column: Loot Tables
        right_frame = tk.Frame(content_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)
        
        # Free Buffs Table
        self.create_free_buffs_table(right_frame)
        
        # Gem Buffs Table (clickable)
        self.create_gem_buffs_table(right_frame)
    
    def _build_analyzer_content(self):
        """Build or rebuild the analyzer content based on selected buff"""
        # Clear existing content
        for widget in self.analyzer_frame.winfo_children():
            widget.destroy()
        
        # Header
        tk.Label(self.analyzer_frame, text="Buff Analyzer", font=("Arial", 11, "bold"),
                background="#FFF3E0").pack(pady=(5, 3))
        
        tk.Label(self.analyzer_frame, text="Click a Gem Buff on the right to analyze",
                font=("Arial", 9), foreground="#666666", background="#FFF3E0").pack(pady=(0, 5))
        
        ttk.Separator(self.analyzer_frame, orient='horizontal').pack(fill=tk.X, padx=5, pady=5)
        
        if self.selected_buff:
            self._create_buff_analysis(self.analyzer_frame, self.selected_buff)
        else:
            # Default: show hint
            tk.Label(self.analyzer_frame, text="No buff selected\n\nSelect a Gem Buff from\nthe table on the right\nto see its EV analysis.",
                    font=("Arial", 10), foreground="gray", background="#FFF3E0",
                    justify=tk.CENTER).pack(pady=30)
    
    def _on_gem_buff_selected(self, event):
        """Called when a gem buff is clicked in the table"""
        selection = self.gem_buffs_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.gem_buffs_tree.item(item, 'values')
        buff_name = values[0]
        
        # Find the buff data
        for buff in GEM_BUFFS:
            if buff['name'] == buff_name:
                self.selected_buff = buff
                self._build_analyzer_content()
                break
    
    def _create_buff_analysis(self, parent, buff):
        """Create the analysis view for a specific buff"""
        bg_color = "#FFF3E0"
        
        # Buff name header
        tk.Label(parent, text=buff['name'], font=("Arial", 12, "bold"),
                background=bg_color, foreground="#E65100").pack(pady=(5, 3))
        
        # Duration and cost
        duration = buff['duration'] if buff['duration'] else "Instant"
        original_cost = buff['cost']
        actual_cost = max(0, original_cost - self.gem_cost_reduction)
        cost_str = "FREE" if actual_cost == 0 else f"{actual_cost:.0f} Gems"
        
        info_frame = tk.Frame(parent, background=bg_color)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(info_frame, text=f"Duration: {duration}", font=("Arial", 9),
                background=bg_color).pack(anchor=tk.W)
        
        cost_color = "green" if actual_cost == 0 else "#C73E1D"
        tk.Label(info_frame, text=f"Cost: {cost_str}", font=("Arial", 9, "bold"),
                background=bg_color, foreground=cost_color).pack(anchor=tk.W)
        
        if buff.get('requirement'):
            tk.Label(info_frame, text=f"Requires: {buff['requirement']}", font=("Arial", 8),
                    background=bg_color, foreground="gray").pack(anchor=tk.W)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, padx=5, pady=5)
        
        # Analysis based on buff type
        self._analyze_buff(parent, buff, actual_cost, bg_color)
    
    def _analyze_buff(self, parent, buff, cost, bg_color):
        """Analyze a specific buff and show EV calculation"""
        buff_name = buff['name']
        duration_str = buff['duration']
        
        # Parse duration to minutes
        duration_minutes = 0
        if duration_str:
            if 'min' in duration_str:
                duration_minutes = int(duration_str.replace(' min', ''))
        
        analysis_frame = tk.Frame(parent, background=bg_color)
        analysis_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Different analysis based on buff type
        if '2x Game Speed' in buff_name:
            self._analyze_game_speed(analysis_frame, cost, duration_minutes, bg_color)
        elif '2x Ore Income' in buff_name:
            self._analyze_ore_income(analysis_frame, cost, duration_minutes, bg_color)
        elif '2x Star Spawn' in buff_name:
            self._analyze_star_spawn(analysis_frame, cost, duration_minutes, bg_color)
        elif '10x Bomb Recharge' in buff_name:
            self._analyze_bomb_recharge(analysis_frame, cost, duration_minutes, bg_color)
        elif 'Item Chest' in buff_name:
            self._analyze_item_chests(analysis_frame, buff, cost, bg_color)
        elif 'Relic Chest' in buff_name:
            self._analyze_relic_chest(analysis_frame, cost, bg_color)
        elif 'Cherry Charges' in buff_name:
            self._analyze_cherry_charges(analysis_frame, buff, cost, bg_color)
        elif 'Auto-Catch' in buff_name:
            self._analyze_auto_catch(analysis_frame, cost, duration_minutes, bg_color)
        elif 'Archaeology' in buff_name:
            self._analyze_archaeology(analysis_frame, cost, bg_color)
        elif 'Fishing' in buff_name:
            self._analyze_fishing(analysis_frame, cost, bg_color)
        elif 'Vein Spawn' in buff_name:
            self._analyze_vein_spawn(analysis_frame, cost, duration_minutes, bg_color)
        else:
            tk.Label(analysis_frame, text="Analysis not available for this buff",
                    font=("Arial", 9), foreground="gray", background=bg_color).pack()
    
    def _analyze_game_speed(self, parent, cost, duration, bg_color):
        """Analyze 2x Game Speed buff"""
        tk.Label(parent, text="2x Game Speed Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        
        if self.calculator:
            ev = self.calculator.calculate_total_ev_per_hour()
            affected_ev = (ev['gems_base'] + ev['stonks_ev'] + ev['skill_shards_ev'] +
                          ev['gem_bomb_gems'] + ev['founder_bomb_boost'])
            
            # In X minutes with 2x speed = 2X minutes of value
            gain_with_speed = affected_ev * (duration * 2 / 60.0)
            gain_without = affected_ev * (duration / 60.0)
            additional_gain = gain_with_speed - gain_without
            profit = additional_gain - cost
            
            self._show_ev_result(parent, affected_ev, additional_gain, cost, profit, duration, bg_color)
        else:
            self._show_no_calculator(parent, bg_color)
    
    def _analyze_ore_income(self, parent, cost, duration, bg_color):
        """Analyze 2x Ore Income buff"""
        tk.Label(parent, text="2x Ore Income Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        tk.Label(parent, text=f"Doubles ore income for {duration} minutes.\n\nValue depends on your ore prices\nand mining speed.",
                font=("Arial", 9), background=bg_color, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        self._show_cost_note(parent, cost, bg_color)
    
    def _analyze_star_spawn(self, parent, cost, duration, bg_color):
        """Analyze 2x Star Spawn Rate buff"""
        tk.Label(parent, text="2x Star Spawn Rate Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        tk.Label(parent, text=f"Doubles star spawn rate for {duration} minutes.\n\nValue depends on your telescope level\nand star upgrades.",
                font=("Arial", 9), background=bg_color, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        self._show_cost_note(parent, cost, bg_color)
    
    def _analyze_bomb_recharge(self, parent, cost, duration, bg_color):
        """Analyze 10x Bomb Recharge buff"""
        tk.Label(parent, text="10x Bomb Recharge Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        
        # 10x Bomb Recharge means bombs recharge 10x faster
        # In 2 minutes: normally you'd get (2min/recharge_time) bombs
        # With buff: you get 10x that amount
        
        # The VALUE of this depends on:
        # 1. How many extra bomb charges you accumulate
        # 2. The average gem value per bomb
        
        if self.calculator:
            params = self.calculator.params
            
            # Gem Bomb: recharges every gem_bomb_recharge_seconds
            gem_bomb_recharge = getattr(params, 'gem_bomb_recharge_seconds', 150.0)
            # Founder Bomb: recharges every founder_bomb_interval_seconds
            founder_bomb_recharge = getattr(params, 'founder_bomb_interval_seconds', 60.0)
            
            duration_seconds = duration * 60
            
            # Normal charges in duration
            normal_gem_bombs = duration_seconds / gem_bomb_recharge
            normal_founder_bombs = duration_seconds / founder_bomb_recharge
            
            # With 10x recharge
            boosted_gem_bombs = (duration_seconds * 10) / gem_bomb_recharge
            boosted_founder_bombs = (duration_seconds * 10) / founder_bomb_recharge
            
            # Additional charges
            extra_gem_bombs = boosted_gem_bombs - normal_gem_bombs
            extra_founder_bombs = boosted_founder_bombs - normal_gem_bombs
            
            # Calculate value per bomb
            ev = self.calculator.calculate_total_ev_per_hour()
            
            # Gem Bomb: ev['gem_bomb_gems'] is per hour
            # Bombs per hour = 3600 / gem_bomb_recharge
            bombs_per_hour = 3600 / gem_bomb_recharge
            gem_value_per_bomb = ev['gem_bomb_gems'] / bombs_per_hour if bombs_per_hour > 0 else 0
            
            # Founder Bomb: ev['founder_bomb_boost'] is per hour
            founder_per_hour = 3600 / founder_bomb_recharge
            founder_value_per_bomb = ev['founder_bomb_boost'] / founder_per_hour if founder_per_hour > 0 else 0
            
            # Total additional value
            additional_gem_value = extra_gem_bombs * gem_value_per_bomb
            additional_founder_value = extra_founder_bombs * founder_value_per_bomb
            additional_gain = additional_gem_value + additional_founder_value
            
            profit = additional_gain - cost
            
            # Show detailed breakdown
            result_frame = tk.Frame(parent, background=bg_color)
            result_frame.pack(fill=tk.X, pady=5)
            
            tk.Label(result_frame, text=f"Duration: {duration} min",
                    font=("Arial", 9), background=bg_color).pack(anchor=tk.W)
            
            tk.Label(result_frame, text=f"\nExtra Gem Bombs: +{extra_gem_bombs:.1f}",
                    font=("Arial", 9), background=bg_color).pack(anchor=tk.W)
            tk.Label(result_frame, text=f"  Value: ~{gem_value_per_bomb:.1f} Gems each = {additional_gem_value:.1f} Gems",
                    font=("Arial", 9), background=bg_color, foreground="#2E7D32").pack(anchor=tk.W)
            
            tk.Label(result_frame, text=f"\nExtra Founder Bombs: +{extra_founder_bombs:.1f}",
                    font=("Arial", 9), background=bg_color).pack(anchor=tk.W)
            tk.Label(result_frame, text=f"  Value: ~{founder_value_per_bomb:.1f} Gems each = {additional_founder_value:.1f} Gems",
                    font=("Arial", 9), background=bg_color, foreground="#2E7D32").pack(anchor=tk.W)
            
            tk.Label(result_frame, text=f"\nTotal Extra Value: {additional_gain:.1f} Gems",
                    font=("Arial", 9, "bold"), background=bg_color, foreground="#2E7D32").pack(anchor=tk.W)
            
            tk.Label(result_frame, text=f"Cost: {cost:.1f} Gems" if cost > 0 else "Cost: FREE",
                    font=("Arial", 9), background=bg_color, 
                    foreground="#C73E1D" if cost > 0 else "green").pack(anchor=tk.W)
            
            ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=5)
            
            # Verdict
            if profit > 0:
                verdict = "WORTH IT!"
                color = "green"
                profit_text = f"+{profit:.1f} Gems profit"
            elif profit == 0:
                verdict = "BREAK EVEN"
                color = "#E65100"
                profit_text = "No profit or loss"
            else:
                verdict = "NOT WORTH IT"
                color = "red"
                profit_text = f"{profit:.1f} Gems loss"
            
            tk.Label(parent, text=verdict, font=("Arial", 14, "bold"),
                    background=bg_color, foreground=color).pack(pady=(5, 0))
            tk.Label(parent, text=profit_text, font=("Arial", 10),
                    background=bg_color, foreground=color).pack()
            
            # Note about stockpiling
            tk.Label(parent, text="\nNote: Value assumes you use all\nextra charges (stockpiling).",
                    font=("Arial", 8), foreground="gray", background=bg_color,
                    justify=tk.CENTER).pack(pady=(10, 0))
        else:
            self._show_no_calculator(parent, bg_color)
    
    def _analyze_item_chests(self, parent, buff, cost, bg_color):
        """Analyze Item Chests buff"""
        count = 3 if '+3' in buff['name'] else 1
        tk.Label(parent, text=f"+{count} Item Chest(s) Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        tk.Label(parent, text=f"Instantly receive {count} item chest(s).\n\nItem chests contain equipment\nand crafting materials.",
                font=("Arial", 9), background=bg_color, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        self._show_cost_note(parent, cost, bg_color)
    
    def _analyze_relic_chest(self, parent, cost, bg_color):
        """Analyze Relic Chest buff"""
        tk.Label(parent, text="+1 Relic Chest Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        tk.Label(parent, text="Instantly receive 1 relic chest.\n\nRelic chests contain valuable relics\nfor permanent upgrades.",
                font=("Arial", 9), background=bg_color, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        self._show_cost_note(parent, cost, bg_color)
    
    def _analyze_cherry_charges(self, parent, buff, cost, bg_color):
        """Analyze Cherry Charges buff"""
        count = 100 if '+100' in buff['name'] else 10
        tk.Label(parent, text=f"+{count} Cherry Charges Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        tk.Label(parent, text=f"Instantly receive {count} cherry bomb charges.\n\nCherry bombs save gem bomb charges\nfor free dumps.",
                font=("Arial", 9), background=bg_color, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        self._show_cost_note(parent, cost, bg_color)
    
    def _analyze_auto_catch(self, parent, cost, duration, bg_color):
        """Analyze 100% Auto-Catch buff"""
        tk.Label(parent, text="100% Auto-Catch Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        tk.Label(parent, text=f"100% auto-catch for {duration} minutes.\n\nNote: Weight goes to 0 if your\nbase auto-catch is already ≥75%.",
                font=("Arial", 9), background=bg_color, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        self._show_cost_note(parent, cost, bg_color)
    
    def _analyze_archaeology(self, parent, cost, bg_color):
        """Analyze Archaeology Attacks buff"""
        tk.Label(parent, text="Archaeology +600 Attacks Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        tk.Label(parent, text="Instantly receive 600 archaeology attacks.\n\nValue depends on your damage\nand current floor progress.",
                font=("Arial", 9), background=bg_color, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        self._show_cost_note(parent, cost, bg_color)
    
    def _analyze_fishing(self, parent, cost, bg_color):
        """Analyze Fishing Ticks buff"""
        tk.Label(parent, text="Fishing +12 Ticks Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        tk.Label(parent, text="Instantly receive 12 fishing ticks.\n\nValue depends on your fishing\nupgrades and bait.",
                font=("Arial", 9), background=bg_color, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        self._show_cost_note(parent, cost, bg_color)
    
    def _analyze_vein_spawn(self, parent, cost, duration, bg_color):
        """Analyze 3x Vein Spawn Rate buff"""
        tk.Label(parent, text="3x Vein Spawn Rate Analysis", font=("Arial", 10, "bold"),
                background=bg_color).pack(anchor=tk.W)
        tk.Label(parent, text=f"Triples stone vein spawn rate for {duration} min.\n\nValue depends on your ore prices\nand vein upgrades.",
                font=("Arial", 9), background=bg_color, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        self._show_cost_note(parent, cost, bg_color)
    
    def _show_ev_result(self, parent, affected_ev, gain, cost, profit, duration, bg_color):
        """Show the EV calculation result"""
        result_frame = tk.Frame(parent, background=bg_color)
        result_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(result_frame, text=f"Affected EV/h: {affected_ev:.1f} Gems/h",
                font=("Arial", 9), background=bg_color).pack(anchor=tk.W)
        tk.Label(result_frame, text=f"Gain in {duration} min: +{gain:.1f} Gems",
                font=("Arial", 9), background=bg_color, foreground="#2E7D32").pack(anchor=tk.W)
        tk.Label(result_frame, text=f"Cost: {cost:.1f} Gems" if cost > 0 else "Cost: FREE",
                font=("Arial", 9), background=bg_color, 
                foreground="#C73E1D" if cost > 0 else "green").pack(anchor=tk.W)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Verdict
        if profit > 0:
            verdict = "WORTH IT!"
            color = "green"
            profit_text = f"+{profit:.1f} Gems profit"
        elif profit == 0:
            verdict = "BREAK EVEN"
            color = "#E65100"
            profit_text = "No profit or loss"
        else:
            verdict = "NOT WORTH IT"
            color = "red"
            profit_text = f"{profit:.1f} Gems loss"
        
        tk.Label(parent, text=verdict, font=("Arial", 14, "bold"),
                background=bg_color, foreground=color).pack(pady=(5, 0))
        tk.Label(parent, text=profit_text, font=("Arial", 10),
                background=bg_color, foreground=color).pack()
    
    def _show_no_calculator(self, parent, bg_color):
        """Show message when calculator is not available"""
        tk.Label(parent, text="Open from main window to see\nEV calculations with your settings.",
                font=("Arial", 9), foreground="gray", background=bg_color,
                justify=tk.CENTER).pack(pady=10)
    
    def _show_cost_note(self, parent, cost, bg_color):
        """Show cost note for buffs without EV calculation"""
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=5)
        if cost == 0:
            reduction_text = f"FREE! ({self.gem_cost_reduction:+d} gem reduction)"
            tk.Label(parent, text=reduction_text,
                    font=("Arial", 10, "bold"), foreground="green", background=bg_color).pack()
        else:
            tk.Label(parent, text=f"Cost: {cost:.0f} Gems",
                    font=("Arial", 10), foreground="#C73E1D", background=bg_color).pack()
    
    def _set_cost_reduction(self, reduction):
        """Set cost reduction to a specific value"""
        self.cost_reduction_var.set(str(reduction))
    
    def _on_cost_reduction_changed(self, *args):
        """Called when cost reduction input changes"""
        try:
            value = int(self.cost_reduction_var.get())
            self.gem_cost_reduction = value
            self._update_loot_tables()
        except ValueError:
            pass
    
    def _update_loot_tables(self):
        """Update the gem buffs table with current cost reduction"""
        if hasattr(self, 'gem_buffs_tree'):
            # Update the cost column in gem buffs
            for item in self.gem_buffs_tree.get_children():
                values = list(self.gem_buffs_tree.item(item, 'values'))
                # Find original cost from GEM_BUFFS data
                buff_name = values[0]
                for buff in GEM_BUFFS:
                    if buff['name'] == buff_name:
                        original_cost = buff['cost']
                        new_cost = max(0, original_cost - self.gem_cost_reduction)
                        if new_cost == 0:
                            values[2] = "FREE"
                        else:
                            values[2] = f"{int(new_cost)} Gems"
                        self.gem_buffs_tree.item(item, values=values)
                        break
        
        # Also update the analyzer if a buff is selected
        if self.selected_buff:
            self._build_analyzer_content()
    
    def _create_cost_reduction_tooltip(self, widget):
        """Creates tooltip for cost reduction"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 280
            tooltip_height = 180
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#1976D2", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text="Gem Cost Reduction", 
                    font=("Arial", 10, "bold"), foreground="#1976D2", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            lines = [
                "",
                "Flat reduction applied to all gem costs:",
                "",
                "-1 = All costs reduced by 1 gem",
                "0 = Normal costs (no reduction)",
                "+1 = All costs increased by 1 gem",
                "",
                "Example: With -1 reduction,",
                "a 15 gem cost becomes 14 gems.",
                "",
                "This affects the Gem Buffs table",
                "and Option Analyzer calculations.",
            ]
            
            for line in lines:
                tk.Label(content_frame, text=line, font=("Arial", 9), 
                        background="#FFFFFF", anchor=tk.W).pack(anchor=tk.W)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def create_free_buffs_table(self, parent):
        """Creates the Free Buffs loot table"""
        frame = tk.Frame(parent, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        frame.grid(row=0, column=0, sticky="nsew", pady=(0, 3))
        
        # Header
        header_frame = tk.Frame(frame, background="#E8F5E9")
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(header_frame, text="Free Buffs", font=("Arial", 11, "bold"),
                background="#E8F5E9", foreground="#2E7D32").pack(side=tk.LEFT)
        
        # Calculate total weight
        total_weight = sum(b['weight'] if isinstance(b['weight'], int) else b['weight'][0] for b in FREE_BUFFS)
        tk.Label(header_frame, text=f"(Total Weight: {total_weight})", font=("Arial", 9),
                background="#E8F5E9", foreground="#666666").pack(side=tk.LEFT, padx=(10, 0))
        
        # Treeview for table
        columns = ('buff', 'duration', 'weight', 'chance', 'requirement')
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=9)
        
        tree.heading('buff', text='Buff')
        tree.heading('duration', text='Duration')
        tree.heading('weight', text='Weight')
        tree.heading('chance', text='Chance')
        tree.heading('requirement', text='Requirement')
        
        tree.column('buff', width=150)
        tree.column('duration', width=70, anchor=tk.CENTER)
        tree.column('weight', width=160, anchor=tk.CENTER)
        tree.column('chance', width=60, anchor=tk.CENTER)
        tree.column('requirement', width=180)
        
        # Add data
        for buff in FREE_BUFFS:
            weight = buff['weight']
            if isinstance(weight, tuple):
                weight_str = buff.get('weight_note', f"{weight[0]}→{weight[-1]}")
                chance = f"{weight[0]/total_weight*100:.1f}%"
            else:
                weight_str = str(weight)
                chance = f"{weight/total_weight*100:.1f}%"
            
            duration = buff['duration'] if buff['duration'] else "—"
            requirement = buff['requirement'] if buff['requirement'] else "—"
            
            tree.insert('', tk.END, values=(buff['name'], duration, weight_str, chance, requirement))
        
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        self.free_buffs_tree = tree
    
    def create_gem_buffs_table(self, parent):
        """Creates the Gem Buffs loot table (clickable)"""
        frame = tk.Frame(parent, background="#E3F2FD", relief=tk.RIDGE, borderwidth=2)
        frame.grid(row=1, column=0, sticky="nsew")
        
        # Header
        header_frame = tk.Frame(frame, background="#E3F2FD")
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(header_frame, text="Gem Buffs", font=("Arial", 11, "bold"),
                background="#E3F2FD", foreground="#1976D2").pack(side=tk.LEFT)
        
        tk.Label(header_frame, text="(click to analyze)", font=("Arial", 9),
                background="#E3F2FD", foreground="#666666").pack(side=tk.LEFT, padx=(5, 0))
        
        # Calculate total weight
        total_weight = sum(b['weight'] if isinstance(b['weight'], int) else b['weight'][0] for b in GEM_BUFFS)
        tk.Label(header_frame, text=f"Weight: {total_weight}", font=("Arial", 9),
                background="#E3F2FD", foreground="#666666").pack(side=tk.RIGHT)
        
        # Treeview for table
        columns = ('buff', 'duration', 'cost', 'weight', 'chance', 'requirement')
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=11, selectmode='browse')
        
        tree.heading('buff', text='Buff')
        tree.heading('duration', text='Duration')
        tree.heading('cost', text='Cost')
        tree.heading('weight', text='Weight')
        tree.heading('chance', text='Chance')
        tree.heading('requirement', text='Requirement')
        
        tree.column('buff', width=160)
        tree.column('duration', width=70, anchor=tk.CENTER)
        tree.column('cost', width=70, anchor=tk.CENTER)
        tree.column('weight', width=180, anchor=tk.CENTER)
        tree.column('chance', width=60, anchor=tk.CENTER)
        tree.column('requirement', width=150)
        
        # Add data
        for buff in GEM_BUFFS:
            weight = buff['weight']
            if isinstance(weight, tuple):
                weight_str = buff.get('weight_note', f"{weight[0]}→{weight[-1]}")
                chance = f"{weight[0]/total_weight*100:.1f}%"
            else:
                weight_str = str(weight)
                chance = f"{weight/total_weight*100:.1f}%"
            
            duration = buff['duration'] if buff['duration'] else "—"
            cost = f"{buff['cost']} Gems"
            requirement = buff['requirement'] if buff['requirement'] else "—"
            
            tree.insert('', tk.END, values=(buff['name'], duration, cost, weight_str, chance, requirement))
        
        # Bind click event
        tree.bind('<<TreeviewSelect>>', self._on_gem_buff_selected)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        self.gem_buffs_tree = tree
    
    def create_speed_option(self, parent):
        """Creates the 2x Game Speed option analysis"""
        
        # Frame for this option
        option_frame = tk.Frame(parent, background="#FFF3E0", padx=8, pady=8)
        option_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5), padx=5)
        
        # Header with icon and text
        header_frame = tk.Frame(option_frame, background="#FFF3E0")
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Try to load the 2x Speed icon
        try:
            speed_icon_path = get_resource_path("sprites/lootbug/gamespeed2x.png")
            if speed_icon_path.exists():
                speed_image = Image.open(speed_icon_path)
                speed_image = speed_image.resize((32, 32), Image.Resampling.LANCZOS)
                self.speed_icon_photo = ImageTk.PhotoImage(speed_image)
                speed_icon_label = tk.Label(header_frame, image=self.speed_icon_photo, background="white", relief=tk.RIDGE, borderwidth=1)
                speed_icon_label.pack(side=tk.LEFT, padx=(0, 8))
        except:
            pass
        
        tk.Label(
            header_frame,
            text="2x Game Speed",
            font=("Arial", 12, "bold"),
            background="#FFF3E0"
        ).pack(side=tk.LEFT)
        
        # Separator after header
        ttk.Separator(option_frame, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Description with dynamic cost
        cost = max(0, 15 - self.gem_cost_reduction)
        cost_str = "FREE" if cost == 0 else f"{cost:.0f} Gems"
        
        desc_label = tk.Label(
            option_frame,
            text=f"Cost: {cost_str}\nDuration: 10 minutes at 2x Game Speed",
            font=("Arial", 10),
            background="#FFF3E0",
            justify=tk.LEFT
        )
        desc_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Calculate if it's worth it
        is_worth, profit, affected_ev, total_ev = self.calculate_speed_option_worth()
        
        # Result frame
        result_frame = ttk.Frame(option_frame)
        result_frame.pack(fill=tk.X, pady=5)
        
        # Status (Worth it / Not worth it)
        if is_worth:
            status_text = "✅ WORTH IT!"
            status_color = "green"
        else:
            status_text = "❌ NOT WORTH IT"
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
        
        # Affected EV/h
        ttk.Label(details_frame, text="Affected EV/h:").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        ttk.Label(
            details_frame,
            text=f"{affected_ev:.1f} Gems/h",
            font=("Arial", 9, "bold")
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Gain in 10 minutes with 2x Speed
        ttk.Label(details_frame, text="With 2× Speed (10 min):").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        
        # Calculate gain in 10 minutes with 2× Speed
        # In 10 minutes with 2× Speed you collect as much as in 20 minutes normal
        gain_10min = affected_ev * (20.0 / 60.0)
        
        ttk.Label(
            details_frame,
            text=f"{gain_10min:.1f} Gems",
            font=("Arial", 9, "bold")
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Gain without Speed
        ttk.Label(details_frame, text="Normal (10 min):").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        
        gain_10min_normal = affected_ev * (10.0 / 60.0)
        
        ttk.Label(
            details_frame,
            text=f"{gain_10min_normal:.1f} Gems",
            font=("Arial", 9)
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Additional gain
        ttk.Label(details_frame, text="Additional Gain:").grid(
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
        
        # Cost (with reduction)
        ttk.Label(details_frame, text="Cost:").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        actual_cost = max(0, 15 - self.gem_cost_reduction)
        cost_display = "FREE!" if actual_cost == 0 else f"{actual_cost:.0f} Gems"
        cost_color = "green" if actual_cost == 0 else "red"
        ttk.Label(
            details_frame,
            text=cost_display,
            font=("Arial", 9),
            foreground=cost_color
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Separator
        ttk.Separator(details_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )
        row += 1
        
        # Net profit
        ttk.Label(
            details_frame,
            text="Net Profit:",
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
        
        # Info icon with hover tooltip
        info_frame = ttk.Frame(option_frame)
        info_frame.pack(fill=tk.X, pady=(8, 0))
        
        info_icon = tk.Label(
            info_frame,
            text="ℹ️ Info (Hover for details)",
            font=("Arial", 9),
            foreground="#1976D2",
            cursor="hand2"
        )
        info_icon.pack(anchor=tk.W)
        
        # Tooltip text
        info_text = (
            "2× Game Speed Effects:\n"
            "\n"
            "Affected:\n"
            "• Gems (Base) - freebie-based\n"
            "• Stonks - freebie-based\n"
            "• Skill Shards - freebie-based\n"
            "• Gem Bomb - halves recharge time\n"
            "• Founder Bomb - halves recharge time\n"
            "\n"
            "NOT affected:\n"
            "• Founder Supply Drop - time-based, independent"
        )
        
        self.create_tooltip(info_icon, info_text)
    
    def create_tooltip(self, widget, text):
        """Creates a modern styled tooltip with rich formatting"""
        _create_tooltip(widget, text)
    
    def calculate_speed_option_worth(self):
        """
        Calculates whether the 2x Speed option is worth it.
        
        2x Game Speed affects:
        - Freebie-based incomes (gems, stonks, skill shards)
        - Founder Bomb (halves recharge time)
        
        NOT affected:
        - Founder Supply Drop (independent of game speed)
        
        Returns:
            (is_worth, profit, affected_ev, total_ev)
        """
        if not self.calculator:
            return False, 0, 0, 0
        
        # Get current EV values
        ev = self.calculator.calculate_total_ev_per_hour()
        
        # Freebie-based incomes + bombs are affected
        # (2x Speed halves bomb recharge time)
        affected_ev = (
            ev['gems_base'] +
            ev['stonks_ev'] +
            ev['skill_shards_ev'] +
            ev['gem_bomb_gems'] +  # Gem Bomb recharge is affected by game speed
            ev['founder_bomb_boost']  # Founder Bomb recharge is affected by game speed
            # NOT: founder_speed_boost, founder_gems (independent of game speed)
        )
        
        # In 10 minutes with 2× Speed you collect as much as in 20 minutes normal
        # Additional gain = affected_ev * (20/60 - 10/60)
        gain_with_speed = affected_ev * (20.0 / 60.0)  # 20 minutes value
        gain_without_speed = affected_ev * (10.0 / 60.0)  # 10 minutes value
        additional_gain = gain_with_speed - gain_without_speed
        
        # Cost with reduction
        cost = max(0, 15.0 - self.gem_cost_reduction)
        
        # Net profit
        profit = additional_gain - cost
        
        # Worth it if profit > 0
        is_worth = profit > 0
        
        return is_worth, profit, affected_ev, ev['total']
