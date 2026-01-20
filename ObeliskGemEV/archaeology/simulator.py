"""
Archaeology Skill Point Optimizer / Simulator

This module provides the GUI window for archaeology skill point optimization.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import json
from PIL import Image, ImageTk

from .block_spawn_rates import get_block_mix_for_stage, get_stage_range_label, STAGE_RANGES, get_normalized_spawn_rates
from .block_stats import get_block_at_floor, get_block_mix_for_floor, BlockData, BLOCK_TYPES

# Save file path (in central save folder)
SAVE_DIR = Path(__file__).parent.parent / "save"
SAVE_FILE = SAVE_DIR / "archaeology_save.json"


class ArchaeologySimulatorWindow:
    """Window for Archaeology skill point optimization simulation"""
    
    # Note: Block stats are now imported from block_stats.py
    # The old static BLOCKS dict has been replaced with dynamic tier-based lookups
    
    # Skill bonuses per point
    SKILL_BONUSES = {
        'strength': {
            'flat_damage': 1,
            'percent_damage': 0.01,
            'crit_damage': 0.03,
        },
        'agility': {
            'max_stamina': 5,
            'crit_chance': 0.01,
            'speed_mod_chance': 0.002,
        },
        'intellect': {
            'xp_bonus': 0.05,
            'exp_mod_chance': 0.003,
        },
        'perception': {
            'fragment_gain': 0.04,
            'loot_mod_chance': 0.003,
            'armor_pen': 2,
        },
        'luck': {
            'crit_chance': 0.02,
            'all_mod_chance': 0.002,
            'one_hit_chance': 0.0004,
        },
    }
    
    def __init__(self, parent):
        self.parent = parent
        
        # Create new window (fullscreen/maximized)
        self.window = tk.Toplevel(parent)
        self.window.title("Archaeology Simulator")
        self.window.state('zoomed')  # Maximize window on Windows
        self.window.resizable(True, True)
        self.window.minsize(900, 700)
        
        # Set icon (if available) - look in parent's sprites folder
        try:
            icon_path = Path(__file__).parent.parent / "sprites" / "gem.png"
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.window.iconphoto(False, icon_photo)
        except:
            pass  # Ignore if icon can't be loaded
        
        # Initialize character state (Level 1 baseline, will be overwritten by load)
        self.reset_to_level1()
        
        self.create_widgets()
        
        # Load saved state (after widgets are created so we can update stage combo)
        self.load_state()
        
        self.update_display()
        
        # Auto-save on window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _on_close(self):
        """Handle window close - save state and destroy window"""
        self.save_state()
        self.window.destroy()
    
    def save_state(self):
        """Save current state to file"""
        state = {
            'level': self.level,
            'current_stage': self.current_stage,
            'skill_points': self.skill_points,
            'upgrade_flat_damage': self.upgrade_flat_damage,
            'upgrade_armor_pen': self.upgrade_armor_pen,
        }
        try:
            # Ensure save directory exists
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            with open(SAVE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def load_state(self):
        """Load saved state from file"""
        if not SAVE_FILE.exists():
            return  # No save file, use defaults
        
        try:
            with open(SAVE_FILE, 'r') as f:
                state = json.load(f)
            
            self.level = state.get('level', 1)
            self.current_stage = state.get('current_stage', 1)
            self.skill_points = state.get('skill_points', {
                'strength': 0,
                'agility': 0,
                'intellect': 0,
                'perception': 0,
                'luck': 0,
            })
            self.upgrade_flat_damage = state.get('upgrade_flat_damage', 0)
            self.upgrade_armor_pen = state.get('upgrade_armor_pen', 0)
            
            # Update stage combo to match loaded state
            stage_map_reverse = {
                1: "1-2", 3: "3-4", 5: "5", 6: "6-9", 10: "10-11",
                12: "12-14", 15: "15-19", 20: "20-24", 25: "25-29",
                30: "30-49", 50: "50-75", 76: "75+"
            }
            stage_str = stage_map_reverse.get(self.current_stage, "1-2")
            if hasattr(self, 'stage_var'):
                self.stage_var.set(stage_str)
                
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
            # Keep default values on error
    
    def reset_to_level1(self):
        """Reset character to Level 1 baseline stats"""
        self.level = 1
        self.current_stage = 1  # Track current floor/stage for spawn rates
        self.skill_points = {
            'strength': 0,
            'agility': 0,
            'intellect': 0,
            'perception': 0,
            'luck': 0,
        }
        # Base stats at Level 1
        self.base_damage = 10
        self.base_armor_pen = 0
        self.base_stamina = 100
        self.base_crit_chance = 0.0
        self.base_crit_damage = 1.5
        self.base_xp_mult = 1.0
        self.base_fragment_mult = 1.0
        # Upgrade stats (separate from skills)
        self.upgrade_flat_damage = 0
        self.upgrade_armor_pen = 0
    
    def get_total_stats(self):
        """Calculate total stats from base + skills + upgrades"""
        str_pts = self.skill_points['strength']
        agi_pts = self.skill_points['agility']
        int_pts = self.skill_points['intellect']
        per_pts = self.skill_points['perception']
        luck_pts = self.skill_points['luck']
        
        # Flat damage: base + upgrades + strength skill
        flat_damage = self.base_damage + self.upgrade_flat_damage + str_pts * self.SKILL_BONUSES['strength']['flat_damage']
        
        # Percent damage bonus from strength
        percent_damage_bonus = str_pts * self.SKILL_BONUSES['strength']['percent_damage']
        
        # Total damage (flat * (1 + percent bonus))
        total_damage = flat_damage * (1 + percent_damage_bonus)
        
        # Armor penetration: base + upgrades + perception skill
        armor_pen = self.base_armor_pen + self.upgrade_armor_pen + per_pts * self.SKILL_BONUSES['perception']['armor_pen']
        
        # Max stamina: base + agility skill
        max_stamina = self.base_stamina + agi_pts * self.SKILL_BONUSES['agility']['max_stamina']
        
        # Crit chance: base + agility + luck
        crit_chance = (self.base_crit_chance + 
                      agi_pts * self.SKILL_BONUSES['agility']['crit_chance'] +
                      luck_pts * self.SKILL_BONUSES['luck']['crit_chance'])
        
        # Crit damage: base + strength
        crit_damage = self.base_crit_damage + str_pts * self.SKILL_BONUSES['strength']['crit_damage']
        
        # One-hit chance from luck
        one_hit_chance = luck_pts * self.SKILL_BONUSES['luck']['one_hit_chance']
        
        # XP multiplier: base + intellect
        xp_mult = self.base_xp_mult + int_pts * self.SKILL_BONUSES['intellect']['xp_bonus']
        
        # Fragment multiplier: base + perception
        fragment_mult = self.base_fragment_mult + per_pts * self.SKILL_BONUSES['perception']['fragment_gain']
        
        return {
            'flat_damage': flat_damage,
            'total_damage': total_damage,
            'armor_pen': armor_pen,
            'max_stamina': max_stamina,
            'crit_chance': min(1.0, crit_chance),
            'crit_damage': crit_damage,
            'one_hit_chance': min(1.0, one_hit_chance),
            'xp_mult': xp_mult,
            'fragment_mult': fragment_mult,
        }
    
    def calculate_effective_damage(self, stats, block_armor):
        """Calculate effective damage against a block with given armor"""
        # Armor penetration reduces armor, but can't make it negative
        # effective_armor = max(0, armor - armor_pen)
        # effective_damage = max(1, floor(damage - effective_armor))
        effective_armor = max(0, block_armor - stats['armor_pen'])
        effective = max(1, int(stats['total_damage'] - effective_armor))
        return effective
    
    def calculate_hits_to_kill(self, stats, block_hp, block_armor):
        """Calculate hits needed to destroy a block"""
        effective_dmg = self.calculate_effective_damage(stats, block_armor)
        
        # Account for crit chance and one-hit chance
        # Average damage per hit considering crits
        crit_chance = stats['crit_chance']
        crit_damage = stats['crit_damage']
        one_hit_chance = stats['one_hit_chance']
        
        # If one-hit procs, block dies instantly
        # Otherwise, average damage = effective_dmg * (1 + crit_chance * (crit_damage - 1))
        avg_dmg_per_hit = effective_dmg * (1 + crit_chance * (crit_damage - 1))
        
        # Expected hits without one-hit
        hits_without_onehit = block_hp / avg_dmg_per_hit
        
        # With one-hit chance, expected hits is reduced
        # E[hits] = sum over k of P(one-hit on hit k) * k + P(no one-hit) * normal_hits
        # Simplified: E[hits] ≈ 1/one_hit_chance if one_hit_chance > 0, but capped at normal hits
        if one_hit_chance > 0:
            # Geometric distribution: E[X] = 1/p where X = first success
            expected_hits_to_onehit = 1 / one_hit_chance
            # Take minimum of one-hit expected hits and normal kill
            expected_hits = min(expected_hits_to_onehit, hits_without_onehit)
        else:
            expected_hits = hits_without_onehit
        
        return expected_hits
    
    def calculate_blocks_per_run(self, stats, floor: int):
        """
        Calculate expected blocks destroyed per run at a given floor.
        Uses tier-appropriate block stats for the floor.
        
        Args:
            stats: Character stats dict
            floor: Current floor number
        
        Returns:
            Expected number of blocks destroyed per run
        """
        max_stamina = stats['max_stamina']
        
        # Get spawn rates and block data for this floor
        spawn_rates = get_normalized_spawn_rates(floor)
        block_mix = get_block_mix_for_floor(floor)
        
        # Calculate weighted average hits per block
        weighted_hits = 0
        
        for block_type, spawn_chance in spawn_rates.items():
            if spawn_chance <= 0:
                continue
            
            block_data = block_mix.get(block_type)
            if not block_data:
                continue
                
            hits = self.calculate_hits_to_kill(stats, block_data.health, block_data.armor)
            weighted_hits += spawn_chance * hits
        
        # Blocks per run = stamina / avg_hits_per_block
        # Note: 1 hit = 1 second = 1 stamina
        if weighted_hits > 0:
            blocks_per_run = max_stamina / weighted_hits
        else:
            blocks_per_run = 0
        
        return blocks_per_run
    
    def calculate_floors_per_run(self, stats, starting_floor: int, blocks_per_floor: int = 15):
        """
        Calculate expected floors cleared per run.
        
        This is the key metric for optimization - how many floors can you clear
        with your available stamina before you run out?
        
        Args:
            stats: Character stats dict
            starting_floor: Floor to start the run from
            blocks_per_floor: Number of blocks to clear per floor (default 15)
        
        Returns:
            Expected number of floors cleared per run
        """
        max_stamina = stats['max_stamina']
        stamina_remaining = max_stamina
        floors_cleared = 0
        current_floor = starting_floor
        
        # Simulate clearing floors until stamina runs out
        # We'll cap at 100 floors to avoid infinite loops
        max_floors_to_check = 100
        
        for _ in range(max_floors_to_check):
            # Get block data for this floor
            spawn_rates = get_normalized_spawn_rates(current_floor)
            block_mix = get_block_mix_for_floor(current_floor)
            
            # Calculate average hits needed per block at this floor
            avg_hits_per_block = 0
            for block_type, spawn_chance in spawn_rates.items():
                if spawn_chance <= 0:
                    continue
                block_data = block_mix.get(block_type)
                if not block_data:
                    continue
                hits = self.calculate_hits_to_kill(stats, block_data.health, block_data.armor)
                avg_hits_per_block += spawn_chance * hits
            
            # Stamina needed to clear this floor
            stamina_for_floor = avg_hits_per_block * blocks_per_floor
            
            if stamina_remaining >= stamina_for_floor:
                # Can clear this floor completely
                stamina_remaining -= stamina_for_floor
                floors_cleared += 1
                current_floor += 1
            else:
                # Partial floor - add fraction
                if stamina_for_floor > 0:
                    partial = stamina_remaining / stamina_for_floor
                    floors_cleared += partial
                break
        
        return floors_cleared
    
    def get_current_block_mix(self):
        """Get current block spawn mix based on highest floor reached"""
        return get_block_mix_for_floor(self.current_stage)
    
    def set_stage(self, stage: int):
        """Set the current stage and update display"""
        self.current_stage = max(1, stage)
        self.update_display()
    
    def calculate_skill_efficiency(self, skill_name):
        """
        Calculate the % improvement in floors/run if we add +1 to this skill.
        Returns (new_floors_per_run, percent_improvement)
        """
        # Current stats and floors/run
        current_stats = self.get_total_stats()
        current_floors = self.calculate_floors_per_run(current_stats, self.current_stage)
        
        # Temporarily add +1 to the skill
        self.skill_points[skill_name] += 1
        new_stats = self.get_total_stats()
        new_floors = self.calculate_floors_per_run(new_stats, self.current_stage)
        self.skill_points[skill_name] -= 1  # Revert
        
        # Calculate improvement
        if current_floors > 0:
            percent_improvement = ((new_floors - current_floors) / current_floors) * 100
        else:
            percent_improvement = 0
        
        return new_floors, percent_improvement
    
    def calculate_upgrade_efficiency(self, upgrade_name):
        """
        Calculate the % improvement in floors/run if we add +1 to this upgrade.
        Returns (new_floors_per_run, percent_improvement)
        """
        current_stats = self.get_total_stats()
        current_floors = self.calculate_floors_per_run(current_stats, self.current_stage)
        
        # Temporarily add +1 to the upgrade
        if upgrade_name == 'flat_damage':
            self.upgrade_flat_damage += 1
        elif upgrade_name == 'armor_pen':
            self.upgrade_armor_pen += 1
        
        new_stats = self.get_total_stats()
        new_floors = self.calculate_floors_per_run(new_stats, self.current_stage)
        
        # Revert
        if upgrade_name == 'flat_damage':
            self.upgrade_flat_damage -= 1
        elif upgrade_name == 'armor_pen':
            self.upgrade_armor_pen -= 1
        
        if current_floors > 0:
            percent_improvement = ((new_floors - current_floors) / current_floors) * 100
        else:
            percent_improvement = 0
        
        return new_floors, percent_improvement
    
    def add_skill_point(self, skill_name):
        """Add a skill point and update display"""
        self.skill_points[skill_name] += 1
        self.level += 1
        self.update_display()
    
    def remove_skill_point(self, skill_name):
        """Remove a skill point and update display (minimum 0)"""
        if self.skill_points[skill_name] > 0:
            self.skill_points[skill_name] -= 1
            self.level = max(1, self.level - 1)
            self.update_display()
    
    def add_upgrade(self, upgrade_name):
        """Add an upgrade and update display"""
        if upgrade_name == 'flat_damage':
            self.upgrade_flat_damage += 1
        elif upgrade_name == 'armor_pen':
            self.upgrade_armor_pen += 1
        self.update_display()
    
    def remove_upgrade(self, upgrade_name):
        """Remove an upgrade and update display (minimum 0)"""
        if upgrade_name == 'flat_damage' and self.upgrade_flat_damage > 0:
            self.upgrade_flat_damage -= 1
        elif upgrade_name == 'armor_pen' and self.upgrade_armor_pen > 0:
            self.upgrade_armor_pen -= 1
        self.update_display()
    
    def create_widgets(self):
        """Creates the widgets in the window"""
        
        # Header
        header_frame = ttk.Frame(self.window, padding="5")
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            header_frame,
            text="Archaeology Skill Point Optimizer",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Find the optimal skill point allocation for maximum blocks/run",
            font=("Arial", 9),
            foreground="gray"
        )
        subtitle_label.pack(pady=(3, 0))
        
        # Separator
        ttk.Separator(self.window, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Main content - two columns
        content_frame = ttk.Frame(self.window, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Left column: Current Stats
        self.create_stats_section(content_frame)
        
        # Right column: Skill/Upgrade buttons with efficiency
        self.create_skills_section(content_frame)
        
        # Bottom: Results and Recommendations
        self.create_results_section()
        
        # Reset button
        reset_frame = ttk.Frame(self.window, padding="5")
        reset_frame.pack(fill=tk.X)
        
        reset_btn = ttk.Button(
            reset_frame,
            text="Reset to Level 1",
            command=self.reset_and_update
        )
        reset_btn.pack(side=tk.RIGHT, padx=5)
    
    def create_stats_section(self, parent):
        """Create the current stats display section"""
        stats_frame = tk.Frame(parent, background="#E3F2FD", relief=tk.RIDGE, borderwidth=2)
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5), pady=5)
        
        # Header
        header = tk.Label(stats_frame, text="Current Stats", font=("Arial", 12, "bold"), 
                         background="#E3F2FD")
        header.pack(pady=(10, 5))
        
        # Level display
        self.level_label = tk.Label(stats_frame, text="Level: 1", font=("Arial", 11, "bold"),
                                   background="#E3F2FD", foreground="#1976D2")
        self.level_label.pack(pady=(0, 5))
        
        # Stage selector
        stage_frame = tk.Frame(stats_frame, background="#E3F2FD")
        stage_frame.pack(pady=(0, 10))
        
        tk.Label(stage_frame, text="Stage:", font=("Arial", 10), 
                background="#E3F2FD").pack(side=tk.LEFT, padx=(0, 5))
        
        self.stage_var = tk.StringVar(value="1-2")
        self.stage_combo = ttk.Combobox(
            stage_frame, 
            textvariable=self.stage_var,
            values=STAGE_RANGES,
            state="readonly",
            width=8
        )
        self.stage_combo.pack(side=tk.LEFT)
        self.stage_combo.bind("<<ComboboxSelected>>", self._on_stage_changed)
        
        # Stats grid
        stats_grid = tk.Frame(stats_frame, background="#E3F2FD")
        stats_grid.pack(fill=tk.X, padx=10, pady=5)
        
        self.stat_labels = {}
        stat_names = [
            ("Damage:", "total_damage"),
            ("Armor Penetration:", "armor_pen"),
            ("Max Stamina:", "max_stamina"),
            ("Crit Chance:", "crit_chance"),
            ("Crit Damage:", "crit_damage"),
            ("One-Hit Chance:", "one_hit_chance"),
            ("XP Multiplier:", "xp_mult"),
            ("Fragment Multiplier:", "fragment_mult"),
        ]
        
        for i, (label_text, key) in enumerate(stat_names):
            tk.Label(stats_grid, text=label_text, background="#E3F2FD", anchor=tk.W).grid(
                row=i, column=0, sticky=tk.W, padx=(0, 10), pady=2
            )
            value_label = tk.Label(stats_grid, text="—", background="#E3F2FD", 
                                  font=("Arial", 9, "bold"), anchor=tk.W)
            value_label.grid(row=i, column=1, sticky=tk.W, pady=2)
            self.stat_labels[key] = value_label
        
        # Separator
        ttk.Separator(stats_frame, orient='horizontal').pack(fill=tk.X, pady=10, padx=10)
        
        # Skill points allocation
        alloc_label = tk.Label(stats_frame, text="Skill Point Allocation:", 
                              font=("Arial", 10, "bold"), background="#E3F2FD")
        alloc_label.pack(pady=(0, 5))
        
        alloc_grid = tk.Frame(stats_frame, background="#E3F2FD")
        alloc_grid.pack(fill=tk.X, padx=10, pady=5)
        
        self.alloc_labels = {}
        for i, skill in enumerate(['strength', 'agility', 'intellect', 'perception', 'luck']):
            tk.Label(alloc_grid, text=f"{skill.capitalize()}:", background="#E3F2FD").grid(
                row=i, column=0, sticky=tk.W, padx=(0, 10), pady=1
            )
            value_label = tk.Label(alloc_grid, text="0", background="#E3F2FD", 
                                  font=("Arial", 9, "bold"))
            value_label.grid(row=i, column=1, sticky=tk.W, pady=1)
            self.alloc_labels[skill] = value_label
        
        # Separator
        ttk.Separator(stats_frame, orient='horizontal').pack(fill=tk.X, pady=10, padx=10)
        
        # Upgrades
        upgrade_label = tk.Label(stats_frame, text="Upgrades:", 
                                font=("Arial", 10, "bold"), background="#E3F2FD")
        upgrade_label.pack(pady=(0, 5))
        
        upgrade_grid = tk.Frame(stats_frame, background="#E3F2FD")
        upgrade_grid.pack(fill=tk.X, padx=10, pady=5)
        
        self.upgrade_labels = {}
        tk.Label(upgrade_grid, text="Flat Damage:", background="#E3F2FD").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10), pady=1
        )
        self.upgrade_labels['flat_damage'] = tk.Label(upgrade_grid, text="+0", 
                                                      background="#E3F2FD", font=("Arial", 9, "bold"))
        self.upgrade_labels['flat_damage'].grid(row=0, column=1, sticky=tk.W, pady=1)
        
        tk.Label(upgrade_grid, text="Armor Pen:", background="#E3F2FD").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=1
        )
        self.upgrade_labels['armor_pen'] = tk.Label(upgrade_grid, text="+0", 
                                                    background="#E3F2FD", font=("Arial", 9, "bold"))
        self.upgrade_labels['armor_pen'].grid(row=1, column=1, sticky=tk.W, pady=1)
    
    def create_skills_section(self, parent):
        """Create the skills and upgrades buttons section"""
        skills_frame = tk.Frame(parent, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        skills_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0), pady=5)
        
        # Header
        header = tk.Label(skills_frame, text="Add Skill Point / Upgrade", 
                         font=("Arial", 12, "bold"), background="#E8F5E9")
        header.pack(pady=(10, 5))
        
        desc_label = tk.Label(skills_frame, 
                             text="Click to add +1. Shows % improvement in floors/run.",
                             font=("Arial", 9), foreground="gray", background="#E8F5E9")
        desc_label.pack(pady=(0, 10))
        
        # Skills section
        skills_label = tk.Label(skills_frame, text="Skills (from Archaeology Level):", 
                               font=("Arial", 10, "bold"), background="#E8F5E9")
        skills_label.pack(pady=(5, 5), anchor=tk.W, padx=10)
        
        self.skill_buttons = {}
        self.skill_efficiency_labels = {}
        
        skills_grid = tk.Frame(skills_frame, background="#E8F5E9")
        skills_grid.pack(fill=tk.X, padx=10, pady=5)
        
        skill_info = {
            'strength': "+1 Flat Dmg, +1% Dmg, +3% Crit Dmg",
            'agility': "+5 Stamina, +1% Crit, +0.2% Speed Mod",
            'intellect': "+5% XP, +0.3% Exp Mod",
            'perception': "+4% Fragments, +0.3% Loot Mod, +2 Armor Pen",
            'luck': "+2% Crit, +0.2% All Mods, +0.04% One-Hit",
        }
        
        for i, (skill, info) in enumerate(skill_info.items()):
            btn_frame = tk.Frame(skills_grid, background="#E8F5E9")
            btn_frame.grid(row=i, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=3)
            
            # Minus button
            minus_btn = tk.Button(
                btn_frame,
                text="-",
                command=lambda s=skill: self.remove_skill_point(s),
                width=2,
                cursor="hand2",
                font=("Arial", 9, "bold")
            )
            minus_btn.pack(side=tk.LEFT, padx=(0, 2))
            
            # Plus button
            plus_btn = tk.Button(
                btn_frame,
                text="+",
                command=lambda s=skill: self.add_skill_point(s),
                width=2,
                cursor="hand2",
                font=("Arial", 9, "bold")
            )
            plus_btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # Skill name label
            skill_label = tk.Label(btn_frame, text=f"{skill.capitalize()}", 
                                  background="#E8F5E9", font=("Arial", 9, "bold"), width=10, anchor=tk.W)
            skill_label.pack(side=tk.LEFT, padx=(0, 5))
            
            self.skill_buttons[skill] = (minus_btn, plus_btn)
            
            eff_label = tk.Label(btn_frame, text="—", background="#E8F5E9", 
                                font=("Arial", 9, "bold"), foreground="#2E7D32", width=8)
            eff_label.pack(side=tk.LEFT, padx=(0, 10))
            self.skill_efficiency_labels[skill] = eff_label
            
            info_label = tk.Label(btn_frame, text=info, background="#E8F5E9", 
                                 font=("Arial", 8), foreground="gray")
            info_label.pack(side=tk.LEFT)
        
        # Separator
        ttk.Separator(skills_frame, orient='horizontal').pack(fill=tk.X, pady=10, padx=10)
        
        # Upgrades section
        upgrades_label = tk.Label(skills_frame, text="Upgrades (from Shop/Progress):", 
                                 font=("Arial", 10, "bold"), background="#E8F5E9")
        upgrades_label.pack(pady=(5, 5), anchor=tk.W, padx=10)
        
        self.upgrade_buttons = {}
        self.upgrade_efficiency_labels = {}
        
        upgrades_grid = tk.Frame(skills_frame, background="#E8F5E9")
        upgrades_grid.pack(fill=tk.X, padx=10, pady=5)
        
        upgrade_info = {
            'flat_damage': "+1 Flat Damage",
            'armor_pen': "+1 Armor Penetration",
        }
        
        for i, (upgrade, info) in enumerate(upgrade_info.items()):
            btn_frame = tk.Frame(upgrades_grid, background="#E8F5E9")
            btn_frame.grid(row=i, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=3)
            
            # Minus button
            minus_btn = tk.Button(
                btn_frame,
                text="-",
                command=lambda u=upgrade: self.remove_upgrade(u),
                width=2,
                cursor="hand2",
                font=("Arial", 9, "bold")
            )
            minus_btn.pack(side=tk.LEFT, padx=(0, 2))
            
            # Plus button
            plus_btn = tk.Button(
                btn_frame,
                text="+",
                command=lambda u=upgrade: self.add_upgrade(u),
                width=2,
                cursor="hand2",
                font=("Arial", 9, "bold")
            )
            plus_btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # Upgrade name label
            upgrade_label = tk.Label(btn_frame, text=f"{upgrade.replace('_', ' ').title()}", 
                                    background="#E8F5E9", font=("Arial", 9, "bold"), width=12, anchor=tk.W)
            upgrade_label.pack(side=tk.LEFT, padx=(0, 5))
            
            self.upgrade_buttons[upgrade] = (minus_btn, plus_btn)
            
            eff_label = tk.Label(btn_frame, text="—", background="#E8F5E9", 
                                font=("Arial", 9, "bold"), foreground="#2E7D32", width=8)
            eff_label.pack(side=tk.LEFT, padx=(0, 10))
            self.upgrade_efficiency_labels[upgrade] = eff_label
            
            info_label = tk.Label(btn_frame, text=info, background="#E8F5E9", 
                                 font=("Arial", 8), foreground="gray")
            info_label.pack(side=tk.LEFT)
        
        # Best choice highlight
        ttk.Separator(skills_frame, orient='horizontal').pack(fill=tk.X, pady=10, padx=10)
        
        rec_label = tk.Label(skills_frame, text="Recommendation:", 
                            font=("Arial", 10, "bold"), background="#E8F5E9")
        rec_label.pack(pady=(5, 5), anchor=tk.W, padx=10)
        
        self.recommendation_label = tk.Label(
            skills_frame, 
            text="—",
            font=("Arial", 11, "bold"),
            background="#E8F5E9",
            foreground="#1976D2"
        )
        self.recommendation_label.pack(pady=(0, 10), padx=10, anchor=tk.W)
    
    def create_results_section(self):
        """Create the results display section at the bottom"""
        results_frame = tk.Frame(self.window, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        results_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Header
        header = tk.Label(results_frame, text="Run Statistics", 
                         font=("Arial", 12, "bold"), background="#FFF3E0")
        header.pack(pady=(10, 5))
        
        # Stats row
        stats_row = tk.Frame(results_frame, background="#FFF3E0")
        stats_row.pack(fill=tk.X, padx=10, pady=10)
        
        # Floors per run (PRIMARY METRIC)
        floors_frame = tk.Frame(stats_row, background="#FFF3E0")
        floors_frame.pack(side=tk.LEFT, expand=True)
        
        tk.Label(floors_frame, text="Floors / Run:", font=("Arial", 10, "bold"), 
                background="#FFF3E0").pack()
        self.floors_per_run_label = tk.Label(floors_frame, text="—", 
                                             font=("Arial", 16, "bold"), 
                                             background="#FFF3E0", foreground="#2E7D32")
        self.floors_per_run_label.pack()
        
        # Blocks per run
        blocks_frame = tk.Frame(stats_row, background="#FFF3E0")
        blocks_frame.pack(side=tk.LEFT, expand=True)
        
        tk.Label(blocks_frame, text="Blocks / Run:", font=("Arial", 10), 
                background="#FFF3E0").pack()
        self.blocks_per_run_label = tk.Label(blocks_frame, text="—", 
                                             font=("Arial", 14, "bold"), 
                                             background="#FFF3E0", foreground="#1976D2")
        self.blocks_per_run_label.pack()
        
        # Avg hits per block
        hits_frame = tk.Frame(stats_row, background="#FFF3E0")
        hits_frame.pack(side=tk.LEFT, expand=True)
        
        tk.Label(hits_frame, text="Avg Hits / Block:", font=("Arial", 10), 
                background="#FFF3E0").pack()
        self.avg_hits_label = tk.Label(hits_frame, text="—", 
                                       font=("Arial", 14, "bold"), 
                                       background="#FFF3E0", foreground="#1976D2")
        self.avg_hits_label.pack()
        
        # Effective damage vs current tier blocks
        dmg_frame = tk.Frame(stats_row, background="#FFF3E0")
        dmg_frame.pack(side=tk.LEFT, expand=True)
        
        tk.Label(dmg_frame, text="Eff. Dmg (Dirt/Common):", font=("Arial", 10), 
                background="#FFF3E0").pack()
        self.eff_dmg_label = tk.Label(dmg_frame, text="—", 
                                      font=("Arial", 14, "bold"), 
                                      background="#FFF3E0", foreground="#C73E1D")
        self.eff_dmg_label.pack()
    
    def update_display(self):
        """Update all display elements with current stats"""
        stats = self.get_total_stats()
        
        # Update level
        self.level_label.config(text=f"Level: {self.level}")
        
        # Update stats
        self.stat_labels['total_damage'].config(text=f"{stats['total_damage']:.1f}")
        self.stat_labels['armor_pen'].config(text=f"{stats['armor_pen']:.0f}")
        self.stat_labels['max_stamina'].config(text=f"{stats['max_stamina']:.0f}")
        self.stat_labels['crit_chance'].config(text=f"{stats['crit_chance']*100:.1f}%")
        self.stat_labels['crit_damage'].config(text=f"{stats['crit_damage']:.2f}x")
        self.stat_labels['one_hit_chance'].config(text=f"{stats['one_hit_chance']*100:.2f}%")
        self.stat_labels['xp_mult'].config(text=f"{stats['xp_mult']:.2f}x")
        self.stat_labels['fragment_mult'].config(text=f"{stats['fragment_mult']:.2f}x")
        
        # Update skill allocation
        for skill, label in self.alloc_labels.items():
            label.config(text=str(self.skill_points[skill]))
        
        # Update upgrades
        self.upgrade_labels['flat_damage'].config(text=f"+{self.upgrade_flat_damage}")
        self.upgrade_labels['armor_pen'].config(text=f"+{self.upgrade_armor_pen}")
        
        # Calculate and update efficiencies
        best_choice = None
        best_improvement = -float('inf')
        
        # Skills
        for skill in self.skill_efficiency_labels:
            new_blocks, improvement = self.calculate_skill_efficiency(skill)
            self.skill_efficiency_labels[skill].config(text=f"+{improvement:.2f}%")
            if improvement > best_improvement:
                best_improvement = improvement
                best_choice = (skill, 'skill')
        
        # Upgrades
        for upgrade in self.upgrade_efficiency_labels:
            new_blocks, improvement = self.calculate_upgrade_efficiency(upgrade)
            self.upgrade_efficiency_labels[upgrade].config(text=f"+{improvement:.2f}%")
            if improvement > best_improvement:
                best_improvement = improvement
                best_choice = (upgrade, 'upgrade')
        
        # Update recommendation
        if best_choice:
            name, type_ = best_choice
            if type_ == 'skill':
                self.recommendation_label.config(
                    text=f"Best: +1 {name.capitalize()} (+{best_improvement:.2f}% floors/run)"
                )
            else:
                self.recommendation_label.config(
                    text=f"Best: +1 {name.replace('_', ' ').title()} (+{best_improvement:.2f}% floors/run)"
                )
        
        # Update run statistics
        # Floors per run (primary metric)
        floors_per_run = self.calculate_floors_per_run(stats, self.current_stage)
        self.floors_per_run_label.config(text=f"{floors_per_run:.2f}")
        
        # Blocks per run
        blocks_per_run = self.calculate_blocks_per_run(stats, self.current_stage)
        self.blocks_per_run_label.config(text=f"{blocks_per_run:.1f}")
        
        # Calculate average hits per block using tier-appropriate stats
        spawn_rates = get_normalized_spawn_rates(self.current_stage)
        block_mix = get_block_mix_for_floor(self.current_stage)
        
        weighted_hits = 0
        for block_type, spawn_chance in spawn_rates.items():
            if spawn_chance <= 0:
                continue
            block_data = block_mix.get(block_type)
            if not block_data:
                continue
            hits = self.calculate_hits_to_kill(stats, block_data.health, block_data.armor)
            weighted_hits += spawn_chance * hits
        self.avg_hits_label.config(text=f"{weighted_hits:.1f}")
        
        # Effective damage vs dirt and common at current tier
        dirt_data = block_mix.get('dirt')
        common_data = block_mix.get('common')
        
        dirt_armor = dirt_data.armor if dirt_data else 0
        common_armor = common_data.armor if common_data else 5
        
        eff_dirt = self.calculate_effective_damage(stats, dirt_armor)
        eff_common = self.calculate_effective_damage(stats, common_armor)
        self.eff_dmg_label.config(text=f"{eff_dirt} / {eff_common}")
    
    def reset_and_update(self):
        """Reset to level 1 and update display"""
        self.reset_to_level1()
        self.stage_var.set("1-2")
        self.update_display()
        # Save the reset state
        self.save_state()
    
    def _on_stage_changed(self, event=None):
        """Handle stage combobox selection change"""
        stage_str = self.stage_var.get()
        
        # Parse stage range to get a representative stage number
        stage_map = {
            "1-2": 1,
            "3-4": 3,
            "5": 5,
            "6-9": 6,
            "10-11": 10,
            "12-14": 12,
            "15-19": 15,
            "20-24": 20,
            "25-29": 25,
            "30-49": 30,
            "50-75": 50,
            "75+": 76,
        }
        
        stage = stage_map.get(stage_str, 1)
        self.current_stage = stage
        self.update_display()
