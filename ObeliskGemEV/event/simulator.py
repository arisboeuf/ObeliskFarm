"""
Event Simulator for Idle Obelisk Miner

Simulates the bimonthly event mechanics to calculate optimal upgrade paths.
Ported from Lua/LÖVE2D implementation by julk.
"""

import tkinter as tk
from tkinter import ttk
import random
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


@dataclass
class PlayerStats:
    """Player statistics for event simulation"""
    default_atk_time: float = 2.0
    default_walk_time: float = 4.0
    walk_speed: float = 1.0
    atk_speed: float = 1.0
    health: int = 100
    atk: int = 10
    crit: int = 0
    crit_dmg: float = 2.0
    block_chance: float = 0.0
    game_speed: float = 1.0
    prestige_bonus_scale: float = 0.1
    x2_money: int = 0
    x5_money: int = 0
    max_wave: int = 1


@dataclass
class EnemyStats:
    """Enemy statistics for event simulation"""
    default_atk_time: float = 2.0
    atk_speed: float = 0.8
    base_health: int = 4
    health_scaling: int = 7
    atk: float = 2.5
    atk_scaling: float = 0.6
    crit: int = 0
    crit_dmg: float = 1.0
    crit_dmg_scaling: float = 0.05


# Upgrade names for display
UPGRADE_NAMES = {
    1: ["+1 Atk Dmg", "+2 Max Hp", "+0.02 Atk Spd", "+0.03 Move Spd", 
        "+2% Event Game Spd", "+1% Crit Chance, +0.10 Crit Dmg", 
        "+1 Atk Dmg +2 Max Hp", "+1 Tier 1 Upgrade Caps", 
        "+1% Prestige Bonus", "+3 Atk Dmg, +3 Max Hp"],
    2: ["+3 Max Hp", "-0.02 Enemy Atk Spd", "-1 Enemy Atk Dmg", 
        "-1% E.Crt rate, -0.1 E.Crt Dmg", "+1 Atk Dmg, +0.01 Atk Spd", 
        "+1 Tier 2 Upgrade Caps", "+2% Prestige Bonus"],
    3: ["+2 Atk Dmg", "+0.02 Atk Spd", "+1% Crit Chance", "+3% Event Game Spd",
        "+3 Atk Dmg, +3 Max Hp", "+1 Tier 3 Upgrade Caps", 
        "+3% 5x Drop Chance", "+5 Max Hp, +0.03 Atk Spd"],
    4: ["+1% Block Chance", "+5 Max Hp", "+0.10 Crit Dmg, -0.10 Enemy Crit Dmg",
        "+0.02 Atk Spd, +0.02 Move Spd", "+4 Max Hp, +4 Atk Dmg", 
        "+1 Tier 4 Upgrade Caps", "+1 Cap Of Cap Upgrades", 
        "+10 Max Hp, +0.05 Atk Spd"]
}

GEM_UPGRADE_NAMES = ["+10% dmg", "+10% max hp", "+100% Event Game Spd", "2x Event Currencies"]

# Prestige unlock requirements for each upgrade
PRESTIGE_UNLOCKED = {
    1: [0, 0, 0, 0, 1, 2, 2, 4, 8, 10],
    2: [0, 0, 0, 3, 4, 5, 10],
    3: [1, 1, 2, 3, 4, 6, 8, 10],
    4: [1, 3, 4, 5, 6, 6, 7, 10]
}

# Maximum levels for each upgrade
MAX_LEVELS = {
    1: [50, 50, 25, 25, 25, 25, 25, 10, 5, 40],
    2: [25, 15, 10, 15, 25, 10, 15],
    3: [20, 20, 20, 20, 10, 10, 10, 40],
    4: [15, 15, 15, 15, 15, 10, 10, 40]
}

# Cap upgrade indices for each tier
CAP_UPGRADES = {1: 8, 2: 6, 3: 6, 4: 6}

# Base costs for each upgrade
COSTS = {
    1: [5, 6, 8, 10, 12, 20, 75, 2500, 25000, 5000],
    2: [5, 8, 12, 20, 40, 500, 650],
    3: [5, 8, 12, 18, 30, 250, 300, 125],
    4: [10, 12, 15, 20, 50, 250, 500, 150]
}


def round_number(number: float, precision: int = 0) -> float:
    """Round a number to specified precision"""
    return round(number, precision)


def apply_upgrades(upgrades: Dict[int, List[int]], player: PlayerStats, 
                   enemy: EnemyStats, prestiges: int, gem_ups: List[int]) -> Tuple[PlayerStats, EnemyStats]:
    """Apply all upgrades to player and enemy stats"""
    p = copy.deepcopy(player)
    e = copy.deepcopy(enemy)
    
    # Tier 1 upgrades
    if 1 in upgrades:
        u = upgrades[1]
        p.atk += u[0]  # +1 Atk Dmg
        p.health += 2 * u[1]  # +2 Max Hp
        p.atk_speed += 0.02 * u[2]  # +0.02 Atk Spd
        p.walk_speed += 0.03 * u[3]  # +0.03 Move Spd
        p.game_speed += 0.02 * u[4]  # +2% Event Game Spd
        p.crit += u[5]  # +1% Crit Chance
        p.crit_dmg += 0.1 * u[5]  # +0.10 Crit Dmg
        p.atk += u[6]  # +1 Atk Dmg
        p.health += 2 * u[6]  # +2 Max Hp
        # u[7] is cap upgrade (no direct stat effect)
        p.prestige_bonus_scale += 0.01 * u[8]  # +1% Prestige Bonus
        p.health += 3 * u[9]  # +3 Max Hp
        p.atk += 3 * u[9]  # +3 Atk Dmg
    
    # Tier 2 upgrades
    if 2 in upgrades:
        u = upgrades[2]
        p.health += 3 * u[0]  # +3 Max Hp
        e.atk_speed -= 0.02 * u[1]  # -0.02 Enemy Atk Spd
        e.atk -= u[2]  # -1 Enemy Atk Dmg
        e.crit -= u[3]  # -1% Enemy Crit Chance
        e.crit_dmg -= 0.10 * u[3]  # -0.10 Enemy Crit Dmg
        p.atk += u[4]  # +1 Atk Dmg
        p.atk_speed += 0.01 * u[4]  # +0.01 Atk Spd
        # u[5] is cap upgrade (no direct stat effect)
        p.prestige_bonus_scale += 0.02 * u[6]  # +2% Prestige Bonus
    
    # Tier 3 upgrades
    if 3 in upgrades:
        u = upgrades[3]
        p.atk += 2 * u[0]  # +2 Atk Dmg
        p.atk_speed += 0.02 * u[1]  # +0.02 Atk Spd
        p.crit += u[2]  # +1% Crit Chance
        p.game_speed += 0.03 * u[3]  # +3% Event Game Spd
        p.atk += 3 * u[4]  # +3 Atk Dmg
        p.health += 3 * u[4]  # +3 Max Hp
        # u[5] is cap upgrade (no direct stat effect)
        p.x5_money += 3 * u[6]  # +3% 5x Drop Chance
        p.health += 5 * u[7]  # +5 Max Hp
        p.atk_speed += 0.03 * u[7]  # +0.03 Atk Spd
    
    # Tier 4 upgrades
    if 4 in upgrades:
        u = upgrades[4]
        p.block_chance += 0.01 * u[0]  # +1% Block Chance
        p.health += 5 * u[1]  # +5 Max Hp
        p.crit_dmg += 0.1 * u[2]  # +0.10 Crit Dmg
        e.crit_dmg -= 0.1 * u[2]  # -0.10 Enemy Crit Dmg
        p.atk_speed += 0.02 * u[3]  # +0.02 Atk Spd
        p.walk_speed += 0.02 * u[3]  # +0.02 Move Spd
        p.atk += 4 * u[4]  # +4 Atk Dmg
        p.health += 4 * u[4]  # +4 Max Hp
        # u[5] is cap upgrade (no direct stat effect)
        # u[6] is cap of cap upgrade (no direct stat effect)
        p.health += 10 * u[7]  # +10 Max Hp
        p.atk_speed += 0.05 * u[7]  # +0.05 Atk Spd
    
    # Apply prestige and gem multipliers
    p.atk = round_number(p.atk * (1 + p.prestige_bonus_scale * prestiges) * (1 + 0.1 * gem_ups[0]))
    p.health = round_number(p.health * (1 + p.prestige_bonus_scale * prestiges) * (1 + 0.1 * gem_ups[1]))
    p.game_speed = p.game_speed + gem_ups[2]
    p.x2_money = p.x2_money + gem_ups[3]
    
    return p, e


def simulate_event_run(player: PlayerStats, enemy: EnemyStats) -> Tuple[int, int, float]:
    """
    Simulate a single event run.
    Returns: (wave, subwave, time)
    """
    player_hp = player.health
    time = 0.0
    p_atk_prog = 0.0
    e_atk_prog = 0.0
    
    wave = 0
    final_subwave = 0
    
    while player_hp > 0:
        wave += 1
        for subwave in range(5, 0, -1):
            if player_hp <= 0:
                break
            
            enemy_hp = enemy.base_health + enemy.health_scaling * wave
            
            while enemy_hp > 0 and player_hp > 0:
                p_atk_time_left = (1 - p_atk_prog) / player.atk_speed
                e_atk_time_left = (1 - e_atk_prog) / (enemy.atk_speed + wave * 0.02)
                
                if p_atk_time_left > e_atk_time_left:
                    # Enemy attacks first
                    p_atk_prog += (e_atk_time_left / (enemy.atk_speed + wave * 0.02)) * player.atk_speed
                    e_atk_prog -= 1
                    
                    dmg = max(1, round_number(enemy.atk + wave * enemy.atk_scaling))
                    
                    # Enemy crit check
                    enemy_crit_chance = enemy.crit + wave
                    if enemy_crit_chance > 0 and random.random() * 100 <= enemy_crit_chance:
                        enemy_crit_mult = enemy.crit_dmg + enemy.crit_dmg_scaling * wave
                        if enemy_crit_mult > 1:
                            dmg = round_number(dmg * enemy_crit_mult)
                    
                    # Block check
                    if player.block_chance > 0 and random.random() <= player.block_chance:
                        dmg = 0
                    
                    player_hp -= dmg
                    time += enemy.default_atk_time * (e_atk_time_left / (enemy.atk_speed + wave * 0.02))
                else:
                    # Player attacks first
                    e_atk_prog += (p_atk_time_left / player.atk_speed) * (enemy.atk_speed + wave * 0.02)
                    p_atk_prog -= 1
                    
                    dmg = player.atk
                    
                    # Player crit check
                    if player.crit > 0 and random.random() * 100 <= player.crit:
                        dmg = round_number(player.atk * player.crit_dmg)
                    
                    enemy_hp -= dmg
                    time += player.default_atk_time * (p_atk_time_left / player.atk_speed)
            
            # Walk time between enemies
            time += player.default_walk_time / player.walk_speed
            
            if player_hp <= 0 and final_subwave == 0:
                final_subwave = subwave
    
    time = time / player.game_speed
    return wave, final_subwave, time


def run_full_simulation(player: PlayerStats, enemy: EnemyStats, 
                        runs: int = 1000) -> Tuple[List[Tuple[int, int, float]], float, float]:
    """
    Run multiple event simulations and return statistics.
    Returns: (sorted_results, avg_distance, avg_time)
    """
    results = []
    total_distance = 0.0
    total_time = 0.0
    
    for _ in range(runs):
        wave, subwave, time = simulate_event_run(player, enemy)
        results.append((wave, subwave, time))
        total_distance += wave + 1 - (subwave * 0.2)
        total_time += time
    
    results.sort(key=lambda x: x[0] + 1 - x[1] * 0.2)
    avg_distance = total_distance / runs
    avg_time = total_time / runs
    
    return results, avg_distance, avg_time


def calculate_materials(wave: int, player: PlayerStats) -> Tuple[float, float, float, float]:
    """Calculate materials gained from reaching a wave"""
    def triangular(n):
        return (n * n + n) / 2
    
    multiplier = (1 + player.x2_money) * (1 + 4 * (player.x5_money / 100))
    
    mat1 = triangular(wave) * multiplier
    mat2 = triangular(wave // 5) * multiplier
    mat3 = triangular(wave // 10) * multiplier
    mat4 = triangular(wave // 15) * multiplier
    
    return mat1, mat2, mat3, mat4


def get_highest_wave_killed_in_x_hits(player: PlayerStats, enemy: EnemyStats, hits: int) -> int:
    """Calculate the highest wave where enemies can be killed in x hits"""
    return int((hits * player.atk - enemy.base_health) / enemy.health_scaling)


def calculate_upgrade_cost(base_price: float, levels: int) -> float:
    """Calculate total cost for upgrading to a certain level"""
    total = 0.0
    for i in range(levels):
        total += round_number(base_price * (1.25 ** i))
    return total


def calculate_total_costs(upgrades: Dict[int, List[int]]) -> Dict[int, float]:
    """Calculate total costs for all upgrades per tier"""
    total_costs = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    
    for tier in range(1, 5):
        if tier in upgrades:
            for i, level in enumerate(upgrades[tier]):
                if i < len(COSTS[tier]):
                    total_costs[tier] += calculate_upgrade_cost(COSTS[tier][i], level)
    
    return total_costs


def format_number(number: float) -> str:
    """Format a number with suffixes (k, m, b, t)"""
    if number < 1000:
        return str(int(round_number(number)))
    
    endings = ["", "k", "m", "b", "t"]
    oom = int(len(str(int(number))) - 1) // 3
    oom = min(oom, len(endings) - 1)
    
    return f"{number / (10 ** (oom * 3)):.2f}{endings[oom]}"


def avg_mult(chance: float, mult: float) -> float:
    """Calculate average multiplier from chance-based effect"""
    return 1 + chance * (mult - 1)


def resources_per_minute(wave_data: Tuple[int, int, float], resource: int, player: PlayerStats) -> float:
    """Calculate resources per minute based on simulation results"""
    resource_wave_reqs = [1, 5, 10, 15]
    avg_wave = int((wave_data[0] + (((5 - wave_data[1]) / 5 - 1) if resource == 1 else 0)) / resource_wave_reqs[resource - 1])
    return (avg_wave ** 2 + avg_wave) * 120 / wave_data[2] * avg_mult(player.x5_money / 100, 5) * avg_mult(player.x2_money, 2)


class EventSimulatorWindow:
    """Event Simulator Window - Tkinter GUI"""
    
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Event Simulator")
        self.window.geometry("1100x750")
        self.window.minsize(900, 650)
        
        # Initialize state
        self.prestige_count = 0
        self.upgrades = {
            1: [0] * 10,
            2: [0] * 7,
            3: [0] * 8,
            4: [0] * 8
        }
        self.gem_ups = [0, 0, 0, 0]
        self.current_resource = 1
        self.base_costs = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        
        # Store upgrade spinboxes for updating
        self.upgrade_spinboxes = {}
        self.gem_spinboxes = []
        
        self.create_widgets()
        self.run_simulation()
    
    def get_current_max_level(self, tier: int, upgrade_idx: int) -> int:
        """Get current max level for an upgrade considering cap upgrades"""
        cap_idx = CAP_UPGRADES[tier]
        base_max = MAX_LEVELS[tier][upgrade_idx]
        
        if upgrade_idx == cap_idx - 1:  # Cap upgrade itself (0-indexed, so -1)
            return base_max + self.upgrades[4][6]  # Cap of caps
        elif tier == 4 and upgrade_idx == 6:  # Cap of caps upgrade
            return base_max
        else:
            return base_max + self.upgrades[tier][cap_idx - 1]
    
    def get_gem_max_level(self, idx: int) -> int:
        """Get max level for gem upgrade"""
        if idx < 2:
            return 5 + self.prestige_count
        elif idx == 2:
            return 1 + min(2, self.prestige_count // 5)
        else:
            return 1
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.window, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)
        
        # Left panel: Stats and controls
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Right panel: Upgrades
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        self.create_left_panel(left_frame)
        self.create_right_panel(right_frame)
    
    def create_left_panel(self, parent):
        """Create left panel with stats and simulation results"""
        # Create scrollable canvas
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
        
        # Set Base Cost Button
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
            spin = ttk.Spinbox(row_frame, from_=0, to=self.get_gem_max_level(i), width=5,
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
            "- Hold Shift + click arrows for ±10\n"
            "- Press Enter to confirm manual input\n"
            "- Set base cost to compare upgrades\n"
            "- Simulation runs 1000 iterations"
        )
        tk.Label(instructions_frame, text=instructions, justify=tk.LEFT,
                background="#ECEFF1", font=("Arial", 9)).pack(anchor="w", padx=5, pady=5)
    
    def create_right_panel(self, parent):
        """Create right panel with upgrade controls"""
        # Create scrollable canvas
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
        
        # Bind mousewheel
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Resource selector
        resource_frame = ttk.Frame(scrollable_frame)
        resource_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(resource_frame, text="Resource for efficiency calc:").pack(side=tk.LEFT)
        self.resource_var = tk.IntVar(value=1)
        for i in range(1, 5):
            ttk.Radiobutton(resource_frame, text=f"Mat {i}", variable=self.resource_var,
                           value=i, command=self.run_simulation).pack(side=tk.LEFT, padx=5)
        
        # Tier upgrades
        tier_colors = {1: "#E3F2FD", 2: "#E8F5E9", 3: "#FFF3E0", 4: "#FCE4EC"}
        
        for tier in range(1, 5):
            tier_frame = tk.Frame(scrollable_frame, background=tier_colors[tier], 
                                 relief=tk.RIDGE, borderwidth=2)
            tier_frame.pack(fill=tk.X, padx=3, pady=3)
            
            tk.Label(tier_frame, text=f"Tier {tier} Upgrades", font=("Arial", 10, "bold"),
                    background=tier_colors[tier]).pack(anchor="w", padx=5, pady=2)
            
            upgrades_inner = tk.Frame(tier_frame, background=tier_colors[tier])
            upgrades_inner.pack(fill=tk.X, padx=5, pady=5)
            
            self.upgrade_spinboxes[tier] = []
            
            for i, name in enumerate(UPGRADE_NAMES[tier]):
                row_frame = tk.Frame(upgrades_inner, background=tier_colors[tier])
                row_frame.pack(fill=tk.X, pady=1)
                
                # Check prestige requirement
                prestige_req = PRESTIGE_UNLOCKED[tier][i]
                locked = prestige_req > self.prestige_count
                
                var = tk.IntVar(value=0)
                max_lvl = self.get_current_max_level(tier, i)
                
                spin = ttk.Spinbox(row_frame, from_=0, to=max_lvl, width=5,
                                  textvariable=var, state='disabled' if locked else 'normal')
                spin.pack(side=tk.LEFT)
                spin.bind('<Return>', lambda e, t=tier, idx=i: self.on_upgrade_change(t, idx))
                spin.bind('<<Increment>>', lambda e, t=tier, idx=i: self.window.after(10, lambda: self.on_upgrade_change(t, idx)))
                spin.bind('<<Decrement>>', lambda e, t=tier, idx=i: self.window.after(10, lambda: self.on_upgrade_change(t, idx)))
                
                # Label with prestige requirement if locked
                label_text = f"  {name}"
                if locked:
                    label_text += f" (P{prestige_req})"
                
                label = tk.Label(row_frame, text=label_text, background=tier_colors[tier],
                               foreground="red" if locked else "black")
                label.pack(side=tk.LEFT)
                
                # Efficiency label
                eff_label = tk.Label(row_frame, text="", background=tier_colors[tier],
                                    font=("Arial", 8), foreground="green")
                eff_label.pack(side=tk.RIGHT, padx=5)
                
                self.upgrade_spinboxes[tier].append((var, spin, label, eff_label, prestige_req))
    
    def on_prestige_change(self):
        """Handle prestige count change"""
        try:
            self.prestige_count = self.prestige_var.get()
        except:
            self.prestige_count = 0
        
        # Update upgrade availability and max levels
        self.update_upgrade_states()
        self.run_simulation()
    
    def on_upgrade_change(self, tier: int, idx: int):
        """Handle upgrade level change"""
        try:
            var, spin, _, _, _ = self.upgrade_spinboxes[tier][idx]
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
        tier_colors = {1: "#E3F2FD", 2: "#E8F5E9", 3: "#FFF3E0", 4: "#FCE4EC"}
        
        for tier in range(1, 5):
            for i, (var, spin, label, eff_label, prestige_req) in enumerate(self.upgrade_spinboxes[tier]):
                locked = prestige_req > self.prestige_count
                
                # Update spinbox state
                spin.configure(state='disabled' if locked else 'normal')
                
                # Update max level
                max_lvl = self.get_current_max_level(tier, i)
                spin.configure(to=max_lvl)
                
                # Update label color
                label.configure(foreground="red" if locked else "black")
                
                # Reset if locked
                if locked and var.get() > 0:
                    var.set(0)
                    self.upgrades[tier][i] = 0
        
        # Update gem upgrade max levels
        for i, (var, spin) in enumerate(self.gem_spinboxes):
            max_lvl = self.get_gem_max_level(i)
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
        # Get current stats
        player, enemy = apply_upgrades(
            self.upgrades,
            PlayerStats(),
            EnemyStats(),
            self.prestige_count,
            self.gem_ups
        )
        
        # Run simulation
        results, avg_distance, avg_time = run_full_simulation(player, enemy, 1000)
        
        # Update results display
        self.update_results_display(results, avg_distance, avg_time, player)
        
        # Update stats displays
        self.update_player_stats_display(player)
        self.update_enemy_stats_display(player, enemy)
        self.update_costs_display()
        
        # Update efficiency labels
        self.update_efficiency_labels(player, enemy)
    
    def update_results_display(self, results: List[Tuple[int, int, float]], 
                               avg_distance: float, avg_time: float, player: PlayerStats):
        """Update the simulation results text"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        
        # Format results
        worst = results[0]
        best = results[-1]
        
        text = f"Worst run:   {worst[0]}-{worst[1]}  {worst[2]:.2f}s\n"
        text += f"Best run:    {best[0]}-{best[1]}  {best[2]:.2f}s\n"
        text += f"Avg distance: {int(avg_distance)}-{5 - (avg_distance % 1) * 5:.2f}\n"
        text += f"Avg time:    {avg_time:.2f}s\n\n"
        
        # Materials
        mats = calculate_materials(int(avg_distance) - 1, player)
        text += f"Avg Materials: {mats[0]:.0f} {mats[1]:.0f} {mats[2]:.0f} {mats[3]:.0f}\n\n"
        
        # Distribution summary
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
    
    def update_efficiency_labels(self, player: PlayerStats, enemy: EnemyStats):
        """Update efficiency labels for each upgrade"""
        resource = self.resource_var.get()
        
        # Calculate base efficiency
        base_results, base_avg, base_time = run_full_simulation(player, enemy, 100)
        base_eff = resources_per_minute((int(base_avg), 5 - int((base_avg % 1) * 5), base_time), resource, player)
        
        for tier in range(1, 5):
            for i, (var, spin, label, eff_label, prestige_req) in enumerate(self.upgrade_spinboxes[tier]):
                if prestige_req > self.prestige_count:
                    eff_label.configure(text="")
                    continue
                
                # Temporarily increase this upgrade
                old_val = self.upgrades[tier][i]
                max_lvl = self.get_current_max_level(tier, i)
                
                if old_val >= max_lvl:
                    eff_label.configure(text="MAX")
                    continue
                
                self.upgrades[tier][i] = old_val + 1
                
                # Calculate new stats and efficiency
                new_player, new_enemy = apply_upgrades(
                    self.upgrades, PlayerStats(), EnemyStats(),
                    self.prestige_count, self.gem_ups
                )
                
                new_results, new_avg, new_time = run_full_simulation(new_player, new_enemy, 100)
                new_eff = resources_per_minute((int(new_avg), 5 - int((new_avg % 1) * 5), new_time), resource, new_player)
                
                # Restore
                self.upgrades[tier][i] = old_val
                
                # Show difference
                diff = new_eff - base_eff
                if diff > 0:
                    eff_label.configure(text=f"+{diff:.1f}", foreground="green")
                else:
                    eff_label.configure(text=f"{diff:.1f}", foreground="red" if diff < 0 else "gray")
