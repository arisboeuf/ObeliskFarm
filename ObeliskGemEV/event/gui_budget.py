"""
Budget Optimizer Mode GUI.
Helps players optimize upgrade paths with limited materials.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .constants import (
    get_prestige_wave_requirement, TIER_COLORS, UPGRADE_SHORT_NAMES,
    CURRENCY_ICONS, WAVE_REWARDS
)
from .utils import format_number
from .stats import PlayerStats, EnemyStats
from .simulation import (
    apply_upgrades, calculate_damage_breakpoints, calculate_breakpoint_efficiency,
    get_atk_breakpoint_table, get_enemy_hp_at_wave, calculate_hits_to_kill
)
from .optimizer import greedy_optimize, format_upgrade_summary, UpgradeState

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import get_resource_path


class BudgetOptimizerPanel:
    """Budget Optimizer mode panel"""
    
    def __init__(self, parent_frame, window_ref):
        self.parent = parent_frame
        self.window = window_ref
        
        # State
        self.material_budget = {1: 0, 2: 0, 3: 0, 4: 0}
        self.material_vars = {}
        
        # Load currency icons
        self.currency_icons = {}
        self._load_currency_icons()
        
        self.build_ui()
    
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
    
    def build_ui(self):
        """Build the Budget Optimizer UI"""
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Main scrollable area
        canvas = tk.Canvas(self.parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # === HEADER ===
        header_frame = tk.Frame(scrollable_frame, background="#4CAF50", relief=tk.RIDGE, borderwidth=2)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(header_frame, text="Event Budget Optimizer", font=("Arial", 14, "bold"),
                background="#4CAF50", foreground="white").pack(pady=10)
        tk.Label(header_frame, text="Enter your available materials and get optimal upgrade recommendations",
                font=("Arial", 10), background="#4CAF50", foreground="white").pack(pady=(0, 10))
        
        # === MATERIAL INPUT ===
        input_frame = tk.Frame(scrollable_frame, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(input_frame, text="Your Materials", font=("Arial", 11, "bold"),
                background="#E8F5E9").pack(anchor="w", padx=10, pady=(10, 5))
        
        mat_inner = tk.Frame(input_frame, background="#E8F5E9")
        mat_inner.pack(fill=tk.X, padx=10, pady=10)
        
        mat_names = ["Coins", "Mat 2", "Mat 3", "Mat 4"]
        mat_colors = ["#FFC107", "#9C27B0", "#00BCD4", "#E91E63"]
        
        for i in range(4):
            col_frame = tk.Frame(mat_inner, background="#E8F5E9")
            col_frame.pack(side=tk.LEFT, padx=20, pady=5)
            
            # Header with icon if available
            header_frame = tk.Frame(col_frame, background="#E8F5E9")
            header_frame.pack()
            
            tier = i + 1
            if tier in self.currency_icons:
                icon_label = tk.Label(header_frame, image=self.currency_icons[tier],
                                     background="#E8F5E9")
                icon_label.pack(side=tk.LEFT, padx=(0, 3))
            
            tk.Label(header_frame, text=mat_names[i], font=("Arial", 9, "bold"),
                    background="#E8F5E9", foreground=mat_colors[i]).pack(side=tk.LEFT)
            
            var = tk.StringVar(value="0")
            entry = ttk.Entry(col_frame, textvariable=var, width=12, font=("Arial", 10))
            entry.pack(pady=5)
            entry.bind('<Return>', lambda e: self.calculate_optimal_upgrades())
            
            self.material_vars[tier] = var
        
        # Prestige input
        prestige_frame = tk.Frame(mat_inner, background="#E8F5E9")
        prestige_frame.pack(side=tk.LEFT, padx=20, pady=5)
        
        tk.Label(prestige_frame, text="Prestiges", font=("Arial", 9, "bold"),
                background="#E8F5E9").pack()
        
        self.budget_prestige_var = tk.IntVar(value=0)
        prestige_spin = ttk.Spinbox(prestige_frame, from_=0, to=20, width=5,
                                    textvariable=self.budget_prestige_var)
        prestige_spin.pack(pady=5)
        
        # Calculate button
        calc_btn = tk.Button(input_frame, text="Calculate Optimal Upgrades", 
                            font=("Arial", 11, "bold"), bg="#4CAF50", fg="white",
                            command=self.calculate_optimal_upgrades)
        calc_btn.pack(pady=10)
        
        # === DAMAGE BREAKPOINTS SECTION ===
        breakpoint_frame = tk.Frame(scrollable_frame, background="#E3F2FD", relief=tk.RIDGE, borderwidth=2)
        breakpoint_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Header with help
        bp_header = tk.Frame(breakpoint_frame, background="#E3F2FD")
        bp_header.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        tk.Label(bp_header, text="Damage Breakpoints", font=("Arial", 11, "bold"),
                background="#E3F2FD").pack(side=tk.LEFT)
        
        bp_help_btn = tk.Label(bp_header, text="?", font=("Arial", 9, "bold"),
                               background="#1976D2", foreground="white", width=2, relief=tk.RAISED)
        bp_help_btn.pack(side=tk.LEFT, padx=5)
        self._create_breakpoint_help_tooltip(bp_help_btn)
        
        # ATK input for breakpoint calculation
        bp_input_frame = tk.Frame(breakpoint_frame, background="#E3F2FD")
        bp_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(bp_input_frame, text="Current ATK:", font=("Arial", 9),
                background="#E3F2FD").pack(side=tk.LEFT)
        
        self.bp_atk_var = tk.StringVar(value="10")
        bp_atk_entry = ttk.Entry(bp_input_frame, textvariable=self.bp_atk_var, width=8)
        bp_atk_entry.pack(side=tk.LEFT, padx=5)
        bp_atk_entry.bind('<Return>', lambda e: self.update_breakpoints_display())
        
        tk.Label(bp_input_frame, text="Target Wave:", font=("Arial", 9),
                background="#E3F2FD").pack(side=tk.LEFT, padx=(20, 0))
        
        self.bp_target_wave_var = tk.StringVar(value="10")
        bp_wave_entry = ttk.Entry(bp_input_frame, textvariable=self.bp_target_wave_var, width=8)
        bp_wave_entry.pack(side=tk.LEFT, padx=5)
        bp_wave_entry.bind('<Return>', lambda e: self.update_breakpoints_display())
        
        bp_calc_btn = tk.Button(bp_input_frame, text="Calculate", font=("Arial", 9),
                                command=self.update_breakpoints_display, bg="#1976D2", fg="white")
        bp_calc_btn.pack(side=tk.LEFT, padx=10)
        
        # Crit toggle and inputs (second row)
        bp_crit_frame = tk.Frame(breakpoint_frame, background="#E3F2FD")
        bp_crit_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Crit toggle checkbox
        self.bp_crit_enabled = tk.BooleanVar(value=False)
        crit_checkbox = ttk.Checkbutton(bp_crit_frame, text="Include Crit",
                                        variable=self.bp_crit_enabled,
                                        command=self.update_breakpoints_display)
        crit_checkbox.pack(side=tk.LEFT)
        
        # Help icon for crit toggle
        crit_help_btn = tk.Label(bp_crit_frame, text="?", font=("Arial", 8, "bold"),
                                 background="#9932CC", foreground="white", width=2, relief=tk.RAISED,
                                 cursor="hand2")
        crit_help_btn.pack(side=tk.LEFT, padx=(3, 10))
        self._create_crit_toggle_tooltip(crit_help_btn)
        
        # Crit chance input
        tk.Label(bp_crit_frame, text="Crit %:", font=("Arial", 9),
                background="#E3F2FD").pack(side=tk.LEFT)
        
        self.bp_crit_chance_var = tk.StringVar(value="0")
        crit_chance_entry = ttk.Entry(bp_crit_frame, textvariable=self.bp_crit_chance_var, width=6)
        crit_chance_entry.pack(side=tk.LEFT, padx=3)
        crit_chance_entry.bind('<Return>', lambda e: self.update_breakpoints_display())
        
        # Crit damage input
        tk.Label(bp_crit_frame, text="Crit Dmg:", font=("Arial", 9),
                background="#E3F2FD").pack(side=tk.LEFT, padx=(10, 0))
        
        self.bp_crit_dmg_var = tk.StringVar(value="1.5")
        crit_dmg_entry = ttk.Entry(bp_crit_frame, textvariable=self.bp_crit_dmg_var, width=6)
        crit_dmg_entry.pack(side=tk.LEFT, padx=3)
        
        # Breakpoint results area
        self.bp_results_frame = tk.Frame(breakpoint_frame, background="#E3F2FD")
        self.bp_results_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Breakpoint table header
        bp_table_header = tk.Frame(self.bp_results_frame, background="#E3F2FD")
        bp_table_header.pack(fill=tk.X)
        
        headers = ["Wave", "Enemy HP", "Hits Now", "Target", "ATK Needed", "+ATK", "Time/Wave"]
        widths = [6, 10, 8, 8, 10, 8, 10]
        
        for i, (header, width) in enumerate(zip(headers, widths)):
            tk.Label(bp_table_header, text=header, font=("Arial", 8, "bold"),
                    background="#E3F2FD", width=width, anchor="center").pack(side=tk.LEFT, padx=1)
        
        # Container for breakpoint rows
        self.bp_rows_frame = tk.Frame(self.bp_results_frame, background="#E3F2FD")
        self.bp_rows_frame.pack(fill=tk.X, pady=5)
        
        # Info label at bottom
        self.bp_info_label = tk.Label(breakpoint_frame, text="Enter your ATK and target wave to see breakpoints",
                                      font=("Arial", 8, "italic"), background="#E3F2FD", foreground="#666666")
        self.bp_info_label.pack(pady=(0, 10))
        
        # === ATK BREAKPOINT TABLE ===
        atk_table_frame = tk.Frame(scrollable_frame, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        atk_table_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(atk_table_frame, text="ATK Requirements by Wave & Hits", font=("Arial", 11, "bold"),
                background="#FFF3E0").pack(anchor="w", padx=10, pady=(10, 5))
        
        # Quick reference table
        self.atk_table_text = tk.Text(atk_table_frame, height=12, font=("Consolas", 9),
                                      background="#FFF3E0", relief=tk.FLAT, wrap=tk.NONE)
        self.atk_table_text.pack(fill=tk.X, padx=10, pady=10)
        
        # Generate initial ATK table
        self._generate_atk_table()
        
        # === RESULTS ===
        results_frame = tk.Frame(scrollable_frame, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        results_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(results_frame, text="Recommended Upgrades", font=("Arial", 11, "bold"),
                background="#E8F5E9").pack(anchor="w", padx=10, pady=(10, 5))
        
        self.budget_results_text = tk.Text(results_frame, height=20, font=("Consolas", 10),
                                           background="#E8F5E9", relief=tk.FLAT, wrap=tk.WORD)
        self.budget_results_text.pack(fill=tk.X, padx=10, pady=10)
        
        # Initial placeholder text
        self.show_initial_instructions()
    
    def show_initial_instructions(self):
        """Show initial instructions in results area"""
        self.budget_results_text.config(state=tk.NORMAL)
        self.budget_results_text.delete(1.0, tk.END)
        
        self.budget_results_text.insert(tk.END, "Enter your materials above and click 'Calculate Optimal Upgrades'\n\n")
        self.budget_results_text.insert(tk.END, "The optimizer will recommend:\n")
        self.budget_results_text.insert(tk.END, "  - Which upgrades to buy for each material type\n")
        self.budget_results_text.insert(tk.END, "  - Expected wave you can reach\n")
        self.budget_results_text.insert(tk.END, "  - Materials left over after upgrades\n\n")
        self.budget_results_text.insert(tk.END, "Note: Tier X upgrades cost Material X\n")
        self.budget_results_text.insert(tk.END, "  - Tier 1 = Coins (Mat 1)\n")
        self.budget_results_text.insert(tk.END, "  - Tier 2 = Mat 2\n")
        self.budget_results_text.insert(tk.END, "  - Tier 3 = Mat 3\n")
        self.budget_results_text.insert(tk.END, "  - Tier 4 = Mat 4\n\n")
        self.budget_results_text.insert(tk.END, "Prestige Wave Requirements (estimated):\n")
        for p in range(1, 11):
            self.budget_results_text.insert(tk.END, f"  Prestige {p}: Wave {get_prestige_wave_requirement(p)}\n")
        
        self.budget_results_text.config(state=tk.DISABLED)
    
    def calculate_optimal_upgrades(self):
        """Calculate optimal upgrades based on material budget"""
        # Parse material inputs
        try:
            for i in range(1, 5):
                val = self.material_vars[i].get().replace(",", "").replace(".", "")
                self.material_budget[i] = float(val) if val else 0
        except ValueError:
            self.budget_results_text.config(state=tk.NORMAL)
            self.budget_results_text.delete(1.0, tk.END)
            self.budget_results_text.insert(tk.END, "Error: Please enter valid numbers for materials")
            self.budget_results_text.config(state=tk.DISABLED)
            return
        
        prestige = self.budget_prestige_var.get()
        next_prestige_wave = get_prestige_wave_requirement(prestige + 1)
        
        self.budget_results_text.config(state=tk.NORMAL)
        self.budget_results_text.delete(1.0, tk.END)
        
        self.budget_results_text.insert(tk.END, "=== Optimizing... ===\n\n")
        self.budget_results_text.update()
        
        # Run optimizer
        try:
            result = greedy_optimize(
                budget=self.material_budget,
                prestige=prestige,
                target_wave=next_prestige_wave
            )
        except Exception as e:
            self.budget_results_text.delete(1.0, tk.END)
            self.budget_results_text.insert(tk.END, f"Error during optimization: {str(e)}")
            self.budget_results_text.config(state=tk.DISABLED)
            return
        
        # Display results
        self.budget_results_text.delete(1.0, tk.END)
        
        # Header
        self.budget_results_text.insert(tk.END, "═══════════════════════════════════════\n")
        self.budget_results_text.insert(tk.END, "        BUDGET OPTIMIZATION RESULTS\n")
        self.budget_results_text.insert(tk.END, "═══════════════════════════════════════\n\n")
        
        # Budget summary
        self.budget_results_text.insert(tk.END, "MATERIALS:\n")
        self.budget_results_text.insert(tk.END, f"  Budget      Spent       Remaining\n")
        for tier in range(1, 5):
            mat_name = f"Mat {tier}" if tier > 1 else "Coins"
            budget = self.material_budget[tier]
            spent = result.materials_spent[tier]
            remaining = result.materials_remaining[tier]
            self.budget_results_text.insert(
                tk.END, 
                f"  {mat_name:6} {budget:10,.0f} {spent:10,.0f} {remaining:10,.0f}\n"
            )
        
        self.budget_results_text.insert(tk.END, "\n")
        
        # Stats summary
        self.budget_results_text.insert(tk.END, "STATS:\n")
        self.budget_results_text.insert(tk.END, f"  ATK:        {result.player_stats.atk}\n")
        self.budget_results_text.insert(tk.END, f"  HP:         {result.player_stats.health}\n")
        self.budget_results_text.insert(tk.END, f"  Atk Speed:  {result.player_stats.atk_speed:.2f}\n")
        self.budget_results_text.insert(tk.END, f"  Move Speed: {result.player_stats.walk_speed:.2f}\n")
        self.budget_results_text.insert(tk.END, f"  Game Speed: {result.player_stats.game_speed:.2f}x\n")
        self.budget_results_text.insert(tk.END, f"  Crit:       {result.player_stats.crit}% @ {result.player_stats.crit_dmg:.1f}x\n")
        self.budget_results_text.insert(tk.END, f"  Block:      {result.player_stats.block_chance*100:.1f}%\n")
        
        self.budget_results_text.insert(tk.END, "\n")
        
        # Expected results
        self.budget_results_text.insert(tk.END, "EXPECTED RESULTS:\n")
        self.budget_results_text.insert(tk.END, f"  Wave:       ~{result.expected_wave:.1f}\n")
        self.budget_results_text.insert(tk.END, f"  Time/Run:   ~{result.expected_time:.1f}s\n")
        self.budget_results_text.insert(tk.END, f"  Target:     Wave {next_prestige_wave} (Prestige {prestige+1})\n")
        
        if result.expected_wave >= next_prestige_wave:
            self.budget_results_text.insert(tk.END, f"  Status:     ✓ Can reach next prestige!\n")
        else:
            deficit = next_prestige_wave - result.expected_wave
            self.budget_results_text.insert(tk.END, f"  Status:     ✗ ~{deficit:.1f} waves short\n")
        
        self.budget_results_text.insert(tk.END, "\n")
        
        # Upgrade recommendations
        self.budget_results_text.insert(tk.END, "RECOMMENDED UPGRADES:\n")
        self.budget_results_text.insert(tk.END, "─────────────────────────────────────\n")
        
        for tier in range(1, 5):
            upgrades_in_tier = []
            for idx, level in enumerate(result.upgrades.levels[tier]):
                if level > 0:
                    name = UPGRADE_SHORT_NAMES[tier][idx]
                    upgrades_in_tier.append(f"{name}: {level}")
            
            if upgrades_in_tier:
                self.budget_results_text.insert(tk.END, f"\nTier {tier}:\n")
                for upgrade in upgrades_in_tier:
                    self.budget_results_text.insert(tk.END, f"  • {upgrade}\n")
        
        self.budget_results_text.insert(tk.END, "\n")
        
        # Recommendations
        if result.recommendations:
            self.budget_results_text.insert(tk.END, "NOTES:\n")
            for rec in result.recommendations:
                self.budget_results_text.insert(tk.END, f"  • {rec}\n")
        
        # Breakpoint info
        self.budget_results_text.insert(tk.END, "\n")
        self.budget_results_text.insert(tk.END, "BREAKPOINT ANALYSIS:\n")
        enemy = EnemyStats()
        for wave in [next_prestige_wave - 5, next_prestige_wave, next_prestige_wave + 5]:
            if wave > 0:
                enemy_hp = get_enemy_hp_at_wave(enemy, wave)
                hits = calculate_hits_to_kill(result.player_stats.atk, enemy_hp)
                self.budget_results_text.insert(
                    tk.END, 
                    f"  Wave {wave:3}: {enemy_hp:3} HP → {hits} hit{'s' if hits > 1 else ''}\n"
                )
        
        # Rewards at target wave
        self.budget_results_text.insert(tk.END, "\n")
        self.budget_results_text.insert(tk.END, "WAVE REWARDS (up to target):\n")
        for wave, reward in sorted(WAVE_REWARDS.items()):
            if wave <= next_prestige_wave:
                self.budget_results_text.insert(tk.END, f"  Wave {wave:3}: {reward}\n")
        
        self.budget_results_text.config(state=tk.DISABLED)
    
    def _create_breakpoint_help_tooltip(self, widget):
        """Create tooltip explaining damage breakpoints for events"""
        tooltip = None
        
        def show_tooltip(event):
            nonlocal tooltip
            if tooltip:
                return
            
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            frame = tk.Frame(tooltip, background="#FFFFFF", relief=tk.SOLID, borderwidth=1)
            frame.pack()
            
            content = tk.Frame(frame, background="#FFFFFF", padx=10, pady=8)
            content.pack()
            
            tk.Label(content, text="Damage Breakpoints", font=("Arial", 10, "bold"),
                    background="#FFFFFF", foreground="#1976D2").pack(anchor="w")
            
            explanation = (
                "A breakpoint is the ATK where you need one fewer hit to kill enemies.\n\n"
                "Example (Wave 5, Enemy HP = 39):\n"
                "  13 ATK → 3 hits (ceil(39/13) = 3)\n"
                "  20 ATK → 2 hits (ceil(39/20) = 2) ← BREAKPOINT\n"
                "  39 ATK → 1 hit  (ceil(39/39) = 1) ← BREAKPOINT\n\n"
                "IMPORTANT: Unlike Archaeology, reaching a breakpoint\n"
                "does NOT save HP, because the next enemy inherits\n"
                "the attack progress of the previous one.\n\n"
                "However, breakpoints still save TIME:\n"
                "  - Fewer hits = faster kills\n"
                "  - Faster kills = more waves completed\n"
                "  - More waves = more materials per run"
            )
            
            tk.Label(content, text=explanation, font=("Arial", 9),
                    background="#FFFFFF", justify=tk.LEFT).pack(anchor="w", pady=5)
        
        def hide_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def _create_crit_toggle_tooltip(self, widget):
        """Create tooltip explaining the Crit toggle for events"""
        tooltip = None
        
        def show_tooltip(event):
            nonlocal tooltip
            if tooltip:
                return
            
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            frame = tk.Frame(tooltip, background="#FFFFFF", relief=tk.SOLID, borderwidth=1)
            frame.pack()
            
            content = tk.Frame(frame, background="#FFFFFF", padx=10, pady=8)
            content.pack()
            
            tk.Label(content, text="Crit Calculation Mode", font=("Arial", 10, "bold"),
                    background="#FFFFFF", foreground="#9932CC").pack(anchor="w")
            
            explanation = (
                "OFF (Deterministic):\n"
                "  Breakpoints calculated with pure ATK damage.\n"
                "  Best for early game when crit is low.\n\n"
                "ON (Crit-based):\n"
                "  Breakpoints include expected crit damage.\n"
                "  Uses average damage per hit formula:\n"
                "  avg_dmg = ATK × (1 + crit% × (crit_dmg - 1))\n\n"
                "Event Crit builds quickly:\n"
                "  T1 Upgrade 6: +1% Crit, +0.1 Crit Dmg\n"
                "  T3 Upgrade 3: +1% Crit Chance\n"
                "  T4 Upgrade 3: +0.1 Crit Dmg\n\n"
                "Recommendation:\n"
                "  Switch to ON once you have ~10-15% crit."
            )
            
            tk.Label(content, text=explanation, font=("Arial", 9),
                    background="#FFFFFF", justify=tk.LEFT).pack(anchor="w", pady=5)
        
        def hide_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def update_breakpoints_display(self):
        """Update the breakpoints display based on current ATK and target wave"""
        # Clear existing rows
        for widget in self.bp_rows_frame.winfo_children():
            widget.destroy()
        
        try:
            current_atk = int(self.bp_atk_var.get())
            target_wave = int(self.bp_target_wave_var.get())
        except ValueError:
            self.bp_info_label.config(text="Please enter valid numbers for ATK and Target Wave")
            return
        
        # Parse crit values
        try:
            crit_chance = float(self.bp_crit_chance_var.get()) if hasattr(self, 'bp_crit_chance_var') else 0
            crit_dmg = float(self.bp_crit_dmg_var.get()) if hasattr(self, 'bp_crit_dmg_var') else 1.5
        except ValueError:
            crit_chance = 0
            crit_dmg = 1.5
        
        use_crit = hasattr(self, 'bp_crit_enabled') and self.bp_crit_enabled.get()
        
        if current_atk < 1:
            self.bp_info_label.config(text="ATK must be at least 1")
            return
        
        if target_wave < 1:
            self.bp_info_label.config(text="Target wave must be at least 1")
            return
        
        # Create player and enemy stats
        player = PlayerStats(atk=current_atk, crit=crit_chance, crit_dmg=crit_dmg)
        enemy = EnemyStats()
        
        # Calculate breakpoints (with or without crit)
        breakpoints = calculate_damage_breakpoints(player, enemy, target_wave, max_breakpoints=8, use_crit=use_crit)
        breakpoints_with_eff = calculate_breakpoint_efficiency(breakpoints, player, enemy, target_wave)
        
        if not breakpoints_with_eff:
            self.bp_info_label.config(text=f"Already one-shotting all enemies up to wave {target_wave}!")
            return
        
        # Display breakpoints
        widths = [6, 10, 8, 8, 10, 8, 10]
        
        for i, bp in enumerate(breakpoints_with_eff[:8]):
            row_bg = "#BBDEFB" if i == 0 else "#E3F2FD"  # Highlight best
            row_frame = tk.Frame(self.bp_rows_frame, background=row_bg)
            row_frame.pack(fill=tk.X, pady=1)
            
            # Best indicator
            prefix = "★ " if i == 0 else "  "
            
            # Format hits - show avg in parentheses if using crit
            if use_crit and 'current_hits_float' in bp:
                hits_display = f"{bp['current_hits']} ({bp['current_hits_float']:.1f})"
            else:
                hits_display = f"{bp['current_hits']}"
            
            values = [
                f"{prefix}{bp['wave']}",
                f"{bp['enemy_hp']}",
                hits_display,
                f"{bp['target_hits']}",
                f"{bp['required_atk']}",
                f"+{bp['atk_increase']}",
                f"-{bp['time_saved_per_wave']:.1f}s"
            ]
            
            for val, width in zip(values, widths):
                fg_color = "#1976D2" if i == 0 else "#333333"
                tk.Label(row_frame, text=val, font=("Arial", 8),
                        background=row_bg, foreground=fg_color, 
                        width=width, anchor="center").pack(side=tk.LEFT, padx=1)
        
        # Update info label
        best = breakpoints_with_eff[0]
        total_time = best.get('total_time_saved', 0)
        waves_affected = best.get('waves_affected', 0)
        
        crit_suffix = " (with crit)" if use_crit else ""
        info_text = (f"★ Best: +{best['atk_increase']} ATK → {best['target_hits']}-hit kills "
                     f"(saves {total_time:.1f}s over {waves_affected} waves){crit_suffix}")
        self.bp_info_label.config(text=info_text, foreground="#1976D2")
    
    def _generate_atk_table(self):
        """Generate the ATK requirement table"""
        enemy = EnemyStats()
        
        self.atk_table_text.config(state=tk.NORMAL)
        self.atk_table_text.delete(1.0, tk.END)
        
        # Header
        header = "Wave │ Enemy HP │  1-hit │  2-hit │  3-hit │  4-hit │  5-hit\n"
        separator = "─────┼──────────┼────────┼────────┼────────┼────────┼────────\n"
        
        self.atk_table_text.insert(tk.END, header)
        self.atk_table_text.insert(tk.END, separator)
        
        import math
        
        # Generate rows for waves 1-30
        for wave in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 20, 25, 30, 35, 40, 50]:
            enemy_hp = get_enemy_hp_at_wave(enemy, wave)
            
            atk_values = []
            for hits in range(1, 6):
                required_atk = math.ceil(enemy_hp / hits)
                atk_values.append(required_atk)
            
            row = f" {wave:3} │   {enemy_hp:4}   │  {atk_values[0]:4}  │  {atk_values[1]:4}  │  {atk_values[2]:4}  │  {atk_values[3]:4}  │  {atk_values[4]:4}\n"
            self.atk_table_text.insert(tk.END, row)
        
        self.atk_table_text.insert(tk.END, "\n")
        self.atk_table_text.insert(tk.END, "Enemy HP formula: 4 + 7 × wave\n")
        self.atk_table_text.insert(tk.END, "ATK needed for X hits: ceil(Enemy HP / X)\n")
        
        self.atk_table_text.config(state=tk.DISABLED)
