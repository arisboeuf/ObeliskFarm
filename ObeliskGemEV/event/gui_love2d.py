"""
Love2D Simulator Mode GUI.
Original port of julk's LÖVE2D event simulator.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple

from .stats import PlayerStats, EnemyStats
from .constants import (
    UPGRADE_NAMES, GEM_UPGRADE_NAMES, PRESTIGE_UNLOCKED, 
    TIER_COLORS, TIER_MAT_NAMES
)
from .simulation import (
    apply_upgrades, run_full_simulation, calculate_materials,
    calculate_total_costs, get_highest_wave_killed_in_x_hits,
    get_current_max_level, get_gem_max_level
)
from .utils import format_number


class Love2DSimulatorPanel:
    """Love2D Simulator mode panel"""
    
    def __init__(self, parent_frame, window_ref):
        self.parent = parent_frame
        self.window = window_ref
        
        # State (shared with main window)
        self.prestige_count = 0
        self.upgrades = {
            1: [0] * 10,
            2: [0] * 7,
            3: [0] * 8,
            4: [0] * 8
        }
        self.gem_ups = [0, 0, 0, 0]
        self.base_costs = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        
        # UI references
        self.upgrade_spinboxes = {}
        self.gem_spinboxes = []
        
        self.build_ui()
        self.run_simulation()
    
    def build_ui(self):
        """Build the Love2D Simulator UI"""
        # Configure grid weights
        self.parent.columnconfigure(0, weight=1)
        self.parent.columnconfigure(1, weight=2)
        self.parent.rowconfigure(0, weight=1)
        
        # Left panel: Stats and controls
        left_frame = ttk.Frame(self.parent)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Right panel: Upgrades
        right_frame = ttk.Frame(self.parent)
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        self.create_left_panel(left_frame)
        self.create_right_panel(right_frame)
    
    def create_left_panel(self, parent):
        """Create left panel with stats and simulation results"""
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Simulation Results
        results_frame = tk.Frame(scrollable_frame, background="#E3F2FD", relief=tk.RIDGE, borderwidth=2)
        results_frame.pack(fill=tk.X, padx=3, pady=3)
        
        tk.Label(results_frame, text="Simulation Results", font=("Arial", 10, "bold"), 
                background="#E3F2FD").pack(anchor="w", padx=5, pady=2)
        
        self.results_text = tk.Text(results_frame, height=12, width=40, font=("Consolas", 9),
                                    background="#E3F2FD", relief=tk.FLAT)
        self.results_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Prestige Control
        prestige_frame = tk.Frame(scrollable_frame, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        prestige_frame.pack(fill=tk.X, padx=3, pady=3)
        
        prestige_inner = tk.Frame(prestige_frame, background="#E8F5E9")
        prestige_inner.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(prestige_inner, text="Prestiges:", font=("Arial", 10, "bold"),
                background="#E8F5E9").pack(side=tk.LEFT)
        
        self.prestige_var = tk.IntVar(value=0)
        prestige_spin = ttk.Spinbox(prestige_inner, from_=0, to=20, width=5,
                                    textvariable=self.prestige_var,
                                    command=self.on_prestige_change)
        prestige_spin.pack(side=tk.LEFT, padx=10)
        prestige_spin.bind('<Return>', lambda e: self.on_prestige_change())
        
        # Player Stats
        player_frame = tk.Frame(scrollable_frame, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        player_frame.pack(fill=tk.X, padx=3, pady=3)
        
        tk.Label(player_frame, text="Player Stats", font=("Arial", 10, "bold"),
                background="#FFF3E0").pack(anchor="w", padx=5, pady=2)
        
        self.player_stats_text = tk.Text(player_frame, height=11, width=40, font=("Consolas", 9),
                                         background="#FFF3E0", relief=tk.FLAT)
        self.player_stats_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Enemy Stats
        enemy_frame = tk.Frame(scrollable_frame, background="#FCE4EC", relief=tk.RIDGE, borderwidth=2)
        enemy_frame.pack(fill=tk.X, padx=3, pady=3)
        
        tk.Label(enemy_frame, text="Enemy Stats", font=("Arial", 10, "bold"),
                background="#FCE4EC").pack(anchor="w", padx=5, pady=2)
        
        self.enemy_stats_text = tk.Text(enemy_frame, height=5, width=40, font=("Consolas", 9),
                                        background="#FCE4EC", relief=tk.FLAT)
        self.enemy_stats_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Costs
        costs_frame = tk.Frame(scrollable_frame, background="#E1F5FE", relief=tk.RIDGE, borderwidth=2)
        costs_frame.pack(fill=tk.X, padx=3, pady=3)
        
        tk.Label(costs_frame, text="Upgrade Costs", font=("Arial", 10, "bold"),
                background="#E1F5FE").pack(anchor="w", padx=5, pady=2)
        
        self.costs_text = tk.Text(costs_frame, height=6, width=40, font=("Consolas", 9),
                                  background="#E1F5FE", relief=tk.FLAT)
        self.costs_text.pack(fill=tk.X, padx=5, pady=5)
        
        set_base_btn = ttk.Button(costs_frame, text="Set Current as Base Cost",
                                  command=self.set_base_cost)
        set_base_btn.pack(pady=5)
        
        # Gem Upgrades
        gem_frame = tk.Frame(scrollable_frame, background="#F3E5F5", relief=tk.RIDGE, borderwidth=2)
        gem_frame.pack(fill=tk.X, padx=3, pady=3)
        
        tk.Label(gem_frame, text="Gem Upgrades", font=("Arial", 10, "bold"),
                background="#F3E5F5").pack(anchor="w", padx=5, pady=2)
        
        gem_inner = tk.Frame(gem_frame, background="#F3E5F5")
        gem_inner.pack(fill=tk.X, padx=5, pady=5)
        
        for i, name in enumerate(GEM_UPGRADE_NAMES):
            row_frame = tk.Frame(gem_inner, background="#F3E5F5")
            row_frame.pack(fill=tk.X, pady=1)
            
            var = tk.IntVar(value=0)
            spin = ttk.Spinbox(row_frame, from_=0, to=get_gem_max_level(self.prestige_count, i), width=5,
                              textvariable=var)
            spin.pack(side=tk.LEFT)
            spin.bind('<Return>', lambda e, idx=i: self.on_gem_upgrade_change(idx))
            spin.bind('<<Increment>>', lambda e, idx=i: self.window.after(10, lambda: self.on_gem_upgrade_change(idx)))
            spin.bind('<<Decrement>>', lambda e, idx=i: self.window.after(10, lambda: self.on_gem_upgrade_change(idx)))
            
            tk.Label(row_frame, text=f"  {name}", background="#F3E5F5").pack(side=tk.LEFT)
            
            self.gem_spinboxes.append((var, spin))
        
        # Instructions
        instructions_frame = tk.Frame(scrollable_frame, background="#ECEFF1", relief=tk.RIDGE, borderwidth=2)
        instructions_frame.pack(fill=tk.X, padx=3, pady=3)
        
        tk.Label(instructions_frame, text="Instructions", font=("Arial", 10, "bold"),
                background="#ECEFF1").pack(anchor="w", padx=5, pady=2)
        
        instructions = (
            "- Adjust upgrade levels using spinboxes\n"
            "- Press Enter to confirm manual input\n"
            "- Set base cost to compare upgrades\n"
            "- Simulation runs 1000 iterations"
        )
        tk.Label(instructions_frame, text=instructions, justify=tk.LEFT,
                background="#ECEFF1", font=("Arial", 9)).pack(anchor="w", padx=5, pady=5)
    
    def create_right_panel(self, parent):
        """Create right panel with upgrade controls"""
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
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
        
        # Tier upgrades
        for tier in range(1, 5):
            tier_frame = tk.Frame(scrollable_frame, background=TIER_COLORS[tier], 
                                 relief=tk.RIDGE, borderwidth=2)
            tier_frame.pack(fill=tk.X, padx=3, pady=3)
            
            tk.Label(tier_frame, text=f"Tier {tier} Upgrades (cost: {TIER_MAT_NAMES[tier]})", 
                    font=("Arial", 10, "bold"),
                    background=TIER_COLORS[tier]).pack(anchor="w", padx=5, pady=2)
            
            upgrades_inner = tk.Frame(tier_frame, background=TIER_COLORS[tier])
            upgrades_inner.pack(fill=tk.X, padx=5, pady=5)
            
            self.upgrade_spinboxes[tier] = []
            
            for i, name in enumerate(UPGRADE_NAMES[tier]):
                row_frame = tk.Frame(upgrades_inner, background=TIER_COLORS[tier])
                row_frame.pack(fill=tk.X, pady=1)
                
                prestige_req = PRESTIGE_UNLOCKED[tier][i]
                locked = prestige_req > self.prestige_count
                
                var = tk.IntVar(value=0)
                max_lvl = get_current_max_level(self.upgrades, tier, i)
                
                spin = ttk.Spinbox(row_frame, from_=0, to=max_lvl, width=5,
                                  textvariable=var, state='disabled' if locked else 'normal')
                spin.pack(side=tk.LEFT)
                spin.bind('<Return>', lambda e, t=tier, idx=i: self.on_upgrade_change(t, idx))
                spin.bind('<<Increment>>', lambda e, t=tier, idx=i: self.window.after(10, lambda: self.on_upgrade_change(t, idx)))
                spin.bind('<<Decrement>>', lambda e, t=tier, idx=i: self.window.after(10, lambda: self.on_upgrade_change(t, idx)))
                
                label_text = f"  {name}"
                if locked:
                    label_text += f" (P{prestige_req})"
                
                label = tk.Label(row_frame, text=label_text, background=TIER_COLORS[tier],
                               foreground="red" if locked else "black")
                label.pack(side=tk.LEFT)
                
                self.upgrade_spinboxes[tier].append((var, spin, label, prestige_req))
    
    def on_prestige_change(self):
        """Handle prestige count change"""
        try:
            self.prestige_count = self.prestige_var.get()
        except:
            self.prestige_count = 0
        
        self.update_upgrade_states()
        self.run_simulation()
    
    def on_upgrade_change(self, tier: int, idx: int):
        """Handle upgrade level change"""
        try:
            var, spin, _, _ = self.upgrade_spinboxes[tier][idx]
            self.upgrades[tier][idx] = var.get()
        except:
            pass
        self.run_simulation()
    
    def on_gem_upgrade_change(self, idx: int):
        """Handle gem upgrade level change"""
        try:
            var, spin = self.gem_spinboxes[idx]
            self.gem_ups[idx] = var.get()
        except:
            pass
        self.run_simulation()
    
    def update_upgrade_states(self):
        """Update upgrade availability based on prestige count"""
        for tier in range(1, 5):
            for i, (var, spin, label, prestige_req) in enumerate(self.upgrade_spinboxes[tier]):
                locked = prestige_req > self.prestige_count
                
                spin.configure(state='disabled' if locked else 'normal')
                
                max_lvl = get_current_max_level(self.upgrades, tier, i)
                spin.configure(to=max_lvl)
                
                label.configure(foreground="red" if locked else "black")
                
                if locked and var.get() > 0:
                    var.set(0)
                    self.upgrades[tier][i] = 0
        
        for i, (var, spin) in enumerate(self.gem_spinboxes):
            max_lvl = get_gem_max_level(self.prestige_count, i)
            spin.configure(to=max_lvl)
            if var.get() > max_lvl:
                var.set(max_lvl)
                self.gem_ups[i] = max_lvl
    
    def set_base_cost(self):
        """Set current costs as base for comparison"""
        self.base_costs = calculate_total_costs(self.upgrades)
        self.update_costs_display()
    
    def run_simulation(self):
        """Run the event simulation and update displays"""
        player, enemy = apply_upgrades(
            self.upgrades,
            PlayerStats(),
            EnemyStats(),
            self.prestige_count,
            self.gem_ups
        )
        
        results, avg_distance, avg_time = run_full_simulation(player, enemy, 1000)
        
        self.update_results_display(results, avg_distance, avg_time, player)
        self.update_player_stats_display(player)
        self.update_enemy_stats_display(player, enemy)
        self.update_costs_display()
    
    def update_results_display(self, results: List[Tuple[int, int, float]], 
                               avg_distance: float, avg_time: float, player: PlayerStats):
        """Update the simulation results text"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        
        worst = results[0]
        best = results[-1]
        
        text = f"Worst run:   {worst[0]}-{worst[1]}  {worst[2]:.2f}s\n"
        text += f"Best run:    {best[0]}-{best[1]}  {best[2]:.2f}s\n"
        text += f"Avg distance: {int(avg_distance)}-{5 - (avg_distance % 1) * 5:.2f}\n"
        text += f"Avg time:    {avg_time:.2f}s\n\n"
        
        mats = calculate_materials(int(avg_distance) - 1, player)
        text += f"Avg Materials: {mats[0]:.0f} {mats[1]:.0f} {mats[2]:.0f} {mats[3]:.0f}\n\n"
        
        text += "Distribution:\n"
        counted = {}
        for wave, subwave, _ in results:
            key = (wave, subwave)
            counted[key] = counted.get(key, 0) + 1
        
        for key in sorted(counted.keys(), key=lambda x: x[0] + 1 - x[1] * 0.2):
            wave, subwave = key
            pct = counted[key] / len(results) * 100
            text += f"  {wave}-{subwave}: {pct:6.1f}%\n"
        
        self.results_text.insert(1.0, text)
        self.results_text.config(state=tk.DISABLED)
    
    def update_player_stats_display(self, player: PlayerStats):
        """Update player stats text"""
        self.player_stats_text.config(state=tk.NORMAL)
        self.player_stats_text.delete(1.0, tk.END)
        
        text = f"Max HP:         {int(player.health)}\n"
        text += f"Atk Dmg:        {int(player.atk)}\n"
        text += f"Atk Spd:        {player.atk_speed:.2f}\n"
        text += f"Move Spd:       {player.walk_speed:.2f}\n"
        text += f"Crit Chance:    {player.crit}%\n"
        text += f"Crit Dmg:       {player.crit_dmg:.2f}x\n"
        text += f"Block Chance:   {player.block_chance * 100:.0f}%\n"
        text += f"Event Speed:    {player.game_speed:.2f}x\n"
        text += f"2x Currencies:  {player.x2_money}\n"
        text += f"5x Currencies:  {player.x5_money}%\n"
        text += f"Prestige Mult:  {1 + self.prestige_count * player.prestige_bonus_scale:.2f}x"
        
        self.player_stats_text.insert(1.0, text)
        self.player_stats_text.config(state=tk.DISABLED)
    
    def update_enemy_stats_display(self, player: PlayerStats, enemy: EnemyStats):
        """Update enemy stats text"""
        self.enemy_stats_text.config(state=tk.NORMAL)
        self.enemy_stats_text.delete(1.0, tk.END)
        
        oneshot_wave = get_highest_wave_killed_in_x_hits(player, enemy, 1)
        atk1_until = max(0, int((-1 * enemy.atk + 1) / enemy.atk_scaling))
        no_crits_until = int((-1 * (enemy.crit_dmg - 1)) / enemy.crit_dmg_scaling)
        
        text = f"Max oneshot wave:  {oneshot_wave}\n"
        text += f"Enemy atk 1 until: wave {atk1_until}\n"
        text += f"Base atk speed:    {enemy.atk_speed:.2f}\n"
        text += f"No crits until:    wave {no_crits_until}"
        
        self.enemy_stats_text.insert(1.0, text)
        self.enemy_stats_text.config(state=tk.DISABLED)
    
    def update_costs_display(self):
        """Update costs text"""
        self.costs_text.config(state=tk.NORMAL)
        self.costs_text.delete(1.0, tk.END)
        
        current = calculate_total_costs(self.upgrades)
        
        text = "Base cost:\n"
        text += f"  {format_number(self.base_costs[1])} {format_number(self.base_costs[2])} {format_number(self.base_costs[3])} {format_number(self.base_costs[4])}\n"
        text += "Current cost:\n"
        text += f"  {format_number(current[1])} {format_number(current[2])} {format_number(current[3])} {format_number(current[4])}\n"
        text += "Difference:\n"
        text += f"  {format_number(current[1] - self.base_costs[1])} {format_number(current[2] - self.base_costs[2])} "
        text += f"{format_number(current[3] - self.base_costs[3])} {format_number(current[4] - self.base_costs[4])}"
        
        self.costs_text.insert(1.0, text)
        self.costs_text.config(state=tk.DISABLED)
