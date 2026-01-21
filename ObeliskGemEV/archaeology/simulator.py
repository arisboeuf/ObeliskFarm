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
    
    # Enrage ability constants
    # 5 charges every 60 seconds, +20% damage, +100% crit damage for those hits
    ENRAGE_CHARGES = 5
    ENRAGE_COOLDOWN = 60  # seconds
    ENRAGE_DAMAGE_BONUS = 0.20  # +20%
    ENRAGE_CRIT_DAMAGE_BONUS = 1.00  # +100% crit damage (additive)
    
    # Mod effects (applied per block when triggered)
    # Exp Mod: 3x to 5x XP (avg 4x)
    # Loot Mod: 2x to 5x Fragments (avg 3.5x)
    # Speed Mod: 2x attack speed for 10-110 attacks (avg 60 attacks)
    #   - Pure QoL: faster run completion, no resource benefit
    #   - Stamina drains faster too, so no floors/run advantage
    # Stamina Mod: +3 to +10 Stamina (avg +6.5)
    MOD_EXP_MULTIPLIER_AVG = 4.0  # Average of 3x-5x
    MOD_LOOT_MULTIPLIER_AVG = 3.5  # Average of 2x-5x
    MOD_SPEED_ATTACKS_AVG = 60.0  # Average of 10-110 attacks (QoL only, no EV impact)
    MOD_STAMINA_BONUS_AVG = 6.5  # Average of 3-10
    
    # Gem Upgrade bonuses per level
    GEM_UPGRADE_BONUSES = {
        'stamina': {
            'max_stamina': 2,
            'stamina_mod_chance': 0.0005,  # +0.05%
            'max_level': 50,
        },
        'xp': {
            'xp_bonus': 0.05,  # +5%
            'exp_mod_chance': 0.0005,  # +0.05%
            'max_level': 25,
        },
        'fragment': {
            'fragment_gain': 0.02,  # +2%
            'loot_mod_chance': 0.0005,  # +0.05%
            'max_level': 25,
        },
    }
    
    # Gem costs per level for each upgrade type
    GEM_COSTS = {
        'stamina': [
            300, 315, 330, 347, 364, 382, 402, 422, 443, 465,  # 1-10
            488, 513, 538, 565, 593, 623, 654, 687, 721, 758,  # 11-20
            795, 835, 877, 921, 967, 1000, 1000, 1000, 1000, 1000,  # 21-30
            1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000,  # 31-40
            1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000,  # 41-50
        ],
        'xp': [
            400, 420, 441, 463, 486, 510, 536, 562, 590, 620,  # 1-10
            651, 684, 718, 754, 791, 831, 873, 916, 962, 1000,  # 11-20
            1000, 1000, 1000, 1000, 1000,  # 21-25
        ],
        'fragment': [
            500, 525, 551, 578, 607, 638, 670, 703, 738, 775,  # 1-10
            814, 855, 897, 942, 989, 1000, 1000, 1000, 1000, 1000,  # 11-20
            1000, 1000, 1000, 1000, 1000,  # 21-25
        ],
    }
    
    # Colors for block types
    BLOCK_COLORS = {
        'dirt': '#8B4513',      # Brown
        'common': '#808080',    # Gray
        'rare': '#4169E1',      # Royal Blue
        'epic': '#9932CC',      # Dark Orchid (Purple)
        'legendary': '#FFD700', # Gold
        'mythic': '#FF4500',    # Orange Red
    }
    
    # Game constants
    BLOCKS_PER_FLOOR = 15
    
    def __init__(self, parent):
        self.parent = parent
        
        # Create new window
        self.window = tk.Toplevel(parent)
        self.window.title("Archaeology Simulator")
        self.window.geometry("1200x700")
        self.window.resizable(True, True)
        self.window.minsize(1000, 600)
        
        # Set icon
        try:
            icon_path = Path(__file__).parent.parent / "sprites" / "gem.png"
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.window.iconphoto(False, icon_photo)
        except:
            pass
        
        # Initialize character state
        self.reset_to_level1()
        
        self.create_widgets()
        self.load_state()
        self.update_display()
        
        # Auto-save on window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _on_close(self):
        self.save_state()
        self.window.destroy()
    
    def save_state(self):
        state = {
            'level': self.level,
            'current_stage': self.current_stage,
            'skill_points': self.skill_points,
            'upgrade_flat_damage': self.upgrade_flat_damage,
            'upgrade_armor_pen': self.upgrade_armor_pen,
            'gem_upgrades': self.gem_upgrades,
            'enrage_enabled': self.enrage_enabled.get() if hasattr(self, 'enrage_enabled') else True,
        }
        try:
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            with open(SAVE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def load_state(self):
        if not SAVE_FILE.exists():
            return
        
        try:
            with open(SAVE_FILE, 'r') as f:
                state = json.load(f)
            
            self.level = state.get('level', 1)
            self.current_stage = state.get('current_stage', 1)
            self.skill_points = state.get('skill_points', {
                'strength': 0, 'agility': 0, 'intellect': 0, 'perception': 0, 'luck': 0,
            })
            self.upgrade_flat_damage = state.get('upgrade_flat_damage', 0)
            self.upgrade_armor_pen = state.get('upgrade_armor_pen', 0)
            self.gem_upgrades = state.get('gem_upgrades', {
                'stamina': 0, 'xp': 0, 'fragment': 0,
            })
            
            # Update enrage checkbox
            if hasattr(self, 'enrage_enabled'):
                self.enrage_enabled.set(state.get('enrage_enabled', True))
            
            # Update stage combo
            stage_map_reverse = {
                1: "1-2", 3: "3-4", 5: "5", 6: "6-9", 10: "10-11",
                12: "12-14", 15: "15-19", 20: "20-24", 25: "25-29",
                30: "30-49", 50: "50-75", 76: "75+"
            }
            if hasattr(self, 'stage_var'):
                self.stage_var.set(stage_map_reverse.get(self.current_stage, "1-2"))
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
    
    def reset_to_level1(self):
        self.level = 1
        self.current_stage = 1
        self.skill_points = {
            'strength': 0, 'agility': 0, 'intellect': 0, 'perception': 0, 'luck': 0,
        }
        self.base_damage = 10
        self.base_armor_pen = 0
        self.base_stamina = 100
        self.base_crit_chance = 0.0
        self.base_crit_damage = 1.5
        self.base_xp_mult = 1.0
        self.base_fragment_mult = 1.0
        self.upgrade_flat_damage = 0
        self.upgrade_armor_pen = 0
        # Gem upgrades
        self.gem_upgrades = {
            'stamina': 0,
            'xp': 0,
            'fragment': 0,
        }
    
    def get_total_stats(self):
        str_pts = self.skill_points['strength']
        agi_pts = self.skill_points['agility']
        int_pts = self.skill_points['intellect']
        per_pts = self.skill_points['perception']
        luck_pts = self.skill_points['luck']
        
        # Gem upgrade levels
        gem_stamina = self.gem_upgrades.get('stamina', 0)
        gem_xp = self.gem_upgrades.get('xp', 0)
        gem_fragment = self.gem_upgrades.get('fragment', 0)
        
        flat_damage = self.base_damage + self.upgrade_flat_damage + str_pts * self.SKILL_BONUSES['strength']['flat_damage']
        percent_damage_bonus = str_pts * self.SKILL_BONUSES['strength']['percent_damage']
        # Damage is always integer (floored) - no decimal damage in game
        total_damage = int(flat_damage * (1 + percent_damage_bonus))
        armor_pen = self.base_armor_pen + self.upgrade_armor_pen + per_pts * self.SKILL_BONUSES['perception']['armor_pen']
        
        # Max stamina: base + agility + gem upgrade
        max_stamina = (self.base_stamina + 
                      agi_pts * self.SKILL_BONUSES['agility']['max_stamina'] +
                      gem_stamina * self.GEM_UPGRADE_BONUSES['stamina']['max_stamina'])
        
        crit_chance = (self.base_crit_chance + 
                      agi_pts * self.SKILL_BONUSES['agility']['crit_chance'] +
                      luck_pts * self.SKILL_BONUSES['luck']['crit_chance'])
        crit_damage = self.base_crit_damage + str_pts * self.SKILL_BONUSES['strength']['crit_damage']
        one_hit_chance = luck_pts * self.SKILL_BONUSES['luck']['one_hit_chance']
        
        # XP mult: base + intellect + gem upgrade
        xp_mult = (self.base_xp_mult + 
                  int_pts * self.SKILL_BONUSES['intellect']['xp_bonus'] +
                  gem_xp * self.GEM_UPGRADE_BONUSES['xp']['xp_bonus'])
        
        # Fragment mult: base + perception + gem upgrade
        fragment_mult = (self.base_fragment_mult + 
                        per_pts * self.SKILL_BONUSES['perception']['fragment_gain'] +
                        gem_fragment * self.GEM_UPGRADE_BONUSES['fragment']['fragment_gain'])
        
        # Mod chances (per block)
        # Luck adds to ALL mod chances
        all_mod_bonus = luck_pts * self.SKILL_BONUSES['luck']['all_mod_chance']
        
        # Exp mod: intellect + luck + gem upgrade
        exp_mod_chance = (int_pts * self.SKILL_BONUSES['intellect']['exp_mod_chance'] + 
                         all_mod_bonus +
                         gem_xp * self.GEM_UPGRADE_BONUSES['xp']['exp_mod_chance'])
        
        # Loot mod: perception + luck + gem upgrade
        loot_mod_chance = (per_pts * self.SKILL_BONUSES['perception']['loot_mod_chance'] + 
                          all_mod_bonus +
                          gem_fragment * self.GEM_UPGRADE_BONUSES['fragment']['loot_mod_chance'])
        
        speed_mod_chance = agi_pts * self.SKILL_BONUSES['agility']['speed_mod_chance'] + all_mod_bonus
        
        # Stamina mod: luck + gem upgrade
        stamina_mod_chance = (all_mod_bonus + 
                             gem_stamina * self.GEM_UPGRADE_BONUSES['stamina']['stamina_mod_chance'])
        
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
            # Mod chances
            'exp_mod_chance': min(1.0, exp_mod_chance),
            'loot_mod_chance': min(1.0, loot_mod_chance),
            'speed_mod_chance': min(1.0, speed_mod_chance),
            'stamina_mod_chance': min(1.0, stamina_mod_chance),
        }
    
    def calculate_effective_damage(self, stats, block_armor):
        effective_armor = max(0, block_armor - stats['armor_pen'])
        effective = max(1, int(stats['total_damage'] - effective_armor))
        return effective
    
    def calculate_damage_breakpoints(self, block_hp, block_armor, stats):
        """
        Calculate damage breakpoints for a specific block.
        Returns info about current hits and next breakpoint.
        
        A breakpoint is where you need one less hit to kill the block.
        Example: 20 HP block
          - At 10 dmg: 2 hits (ceil(20/10) = 2)
          - At 11 dmg: 2 hits (ceil(20/11) = 2) 
          - At 20 dmg: 1 hit (ceil(20/20) = 1) <-- breakpoint at 20
        """
        import math
        
        effective_armor = max(0, block_armor - stats['armor_pen'])
        current_eff_dmg = self.calculate_effective_damage(stats, block_armor)
        current_hits = math.ceil(block_hp / current_eff_dmg) if current_eff_dmg > 0 else float('inf')
        
        # Find next breakpoint: the minimum damage that results in one fewer hit
        # If current_hits = n, we need dmg such that ceil(hp/dmg) = n-1
        # That means dmg >= hp/(n-1), so min dmg = ceil(hp/(n-1))
        
        next_breakpoint_dmg = None
        next_breakpoint_hits = None
        dmg_needed = None
        
        if current_hits > 1:
            target_hits = current_hits - 1
            # Minimum effective damage needed for target_hits
            # ceil(hp/dmg) = target_hits  =>  dmg >= hp/target_hits
            min_eff_dmg_needed = math.ceil(block_hp / target_hits)
            
            # Total damage needed = effective damage + effective armor
            total_dmg_needed = min_eff_dmg_needed + effective_armor
            
            next_breakpoint_dmg = total_dmg_needed
            next_breakpoint_hits = target_hits
            dmg_needed = max(0, total_dmg_needed - stats['total_damage'])
        
        return {
            'block_hp': block_hp,
            'block_armor': block_armor,
            'effective_armor': effective_armor,
            'current_eff_dmg': current_eff_dmg,
            'current_hits': current_hits,
            'next_breakpoint_dmg': next_breakpoint_dmg,
            'next_breakpoint_hits': next_breakpoint_hits,
            'dmg_needed': dmg_needed,
        }
    
    def calculate_hits_to_kill(self, stats, block_hp, block_armor):
        """
        Calculate expected hits to kill a block, accounting for:
        - Base damage with armor penetration
        - Critical hits
        - One-hit chance
        - Enrage ability (5 charges every 60s with +20% dmg, +100% crit dmg) - if enabled
        """
        crit_chance = stats['crit_chance']
        crit_damage = stats['crit_damage']
        one_hit_chance = stats['one_hit_chance']
        
        # Calculate effective damage (base, no enrage)
        effective_dmg_base = self.calculate_effective_damage(stats, block_armor)
        
        # Check if Enrage is enabled
        enrage_active = getattr(self, 'enrage_enabled', None)
        if enrage_active is not None and enrage_active.get():
            # Enrage: 5 hits out of every 60 have +20% damage and +100% crit damage
            # Proportion of enrage hits: 5/60 = 0.0833...
            enrage_proportion = self.ENRAGE_CHARGES / self.ENRAGE_COOLDOWN
            normal_proportion = 1.0 - enrage_proportion
            
            # Enrage effective damage: base damage * 1.20 (floored), then subtract armor
            # Damage is always integer - enrage bonus is floored before armor calculation
            enrage_total_damage = int(stats['total_damage'] * (1 + self.ENRAGE_DAMAGE_BONUS))
            effective_armor = max(0, block_armor - stats['armor_pen'])
            effective_dmg_enrage = max(1, enrage_total_damage - effective_armor)
            
            # Enrage crit damage: normal crit damage + 1.0
            enrage_crit_damage = crit_damage + self.ENRAGE_CRIT_DAMAGE_BONUS
            
            # Average damage per hit for normal hits (with crits)
            avg_dmg_normal = effective_dmg_base * (1 + crit_chance * (crit_damage - 1))
            
            # Average damage per hit for enrage hits (with boosted crits)
            avg_dmg_enrage = effective_dmg_enrage * (1 + crit_chance * (enrage_crit_damage - 1))
            
            # Weighted average damage per hit
            avg_dmg_per_hit = (normal_proportion * avg_dmg_normal + 
                              enrage_proportion * avg_dmg_enrage)
        else:
            # No Enrage - just normal damage with crits
            avg_dmg_per_hit = effective_dmg_base * (1 + crit_chance * (crit_damage - 1))
        
        # Expected hits without one-hit
        hits_without_onehit = block_hp / avg_dmg_per_hit
        
        # With one-hit chance, expected hits is reduced
        if one_hit_chance > 0:
            expected_hits_to_onehit = 1 / one_hit_chance
            expected_hits = min(expected_hits_to_onehit, hits_without_onehit)
        else:
            expected_hits = hits_without_onehit
        
        return expected_hits
    
    def calculate_blocks_per_run(self, stats, floor: int):
        max_stamina = stats['max_stamina']
        spawn_rates = get_normalized_spawn_rates(floor)
        block_mix = get_block_mix_for_floor(floor)
        
        weighted_hits = 0
        for block_type, spawn_chance in spawn_rates.items():
            if spawn_chance <= 0:
                continue
            block_data = block_mix.get(block_type)
            if not block_data:
                continue
            hits = self.calculate_hits_to_kill(stats, block_data.health, block_data.armor)
            weighted_hits += spawn_chance * hits
        
        if weighted_hits > 0:
            return max_stamina / weighted_hits
        return 0
    
    def calculate_floors_per_run(self, stats, starting_floor: int, blocks_per_floor: int = 15):
        """
        Calculate floors per run, accounting for:
        - Stamina Mod: Each block has a chance to give +6.5 stamina (avg of 3-10)
        """
        max_stamina = stats['max_stamina']
        stamina_remaining = max_stamina
        floors_cleared = 0
        current_floor = starting_floor
        
        # Stamina mod: each block has stamina_mod_chance to give avg +6.5 stamina
        stamina_mod_chance = stats.get('stamina_mod_chance', 0)
        avg_stamina_per_block = stamina_mod_chance * self.MOD_STAMINA_BONUS_AVG
        
        for _ in range(100):
            spawn_rates = get_normalized_spawn_rates(current_floor)
            block_mix = get_block_mix_for_floor(current_floor)
            
            avg_hits_per_block = 0
            for block_type, spawn_chance in spawn_rates.items():
                if spawn_chance <= 0:
                    continue
                block_data = block_mix.get(block_type)
                if not block_data:
                    continue
                hits = self.calculate_hits_to_kill(stats, block_data.health, block_data.armor)
                avg_hits_per_block += spawn_chance * hits
            
            # Net stamina cost per block = hits - stamina gained from mod
            # But stamina gained can't exceed max_stamina, so we cap the effective gain
            net_stamina_per_block = max(0.1, avg_hits_per_block - avg_stamina_per_block)
            stamina_for_floor = net_stamina_per_block * blocks_per_floor
            
            if stamina_remaining >= stamina_for_floor:
                stamina_remaining -= stamina_for_floor
                floors_cleared += 1
                current_floor += 1
            else:
                if stamina_for_floor > 0:
                    floors_cleared += stamina_remaining / stamina_for_floor
                break
        
        return floors_cleared
    
    def calculate_skill_efficiency(self, skill_name):
        current_stats = self.get_total_stats()
        current_floors = self.calculate_floors_per_run(current_stats, self.current_stage)
        
        self.skill_points[skill_name] += 1
        new_stats = self.get_total_stats()
        new_floors = self.calculate_floors_per_run(new_stats, self.current_stage)
        self.skill_points[skill_name] -= 1
        
        if current_floors > 0:
            percent_improvement = ((new_floors - current_floors) / current_floors) * 100
        else:
            percent_improvement = 0
        
        return new_floors, percent_improvement
    
    def calculate_upgrade_efficiency(self, upgrade_name):
        current_stats = self.get_total_stats()
        current_floors = self.calculate_floors_per_run(current_stats, self.current_stage)
        
        if upgrade_name == 'flat_damage':
            self.upgrade_flat_damage += 1
        elif upgrade_name == 'armor_pen':
            self.upgrade_armor_pen += 1
        
        new_stats = self.get_total_stats()
        new_floors = self.calculate_floors_per_run(new_stats, self.current_stage)
        
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
        self.skill_points[skill_name] += 1
        self.level += 1
        self.update_display()
    
    def remove_skill_point(self, skill_name):
        if self.skill_points[skill_name] > 0:
            self.skill_points[skill_name] -= 1
            self.level = max(1, self.level - 1)
            self.update_display()
    
    def add_upgrade(self, upgrade_name):
        if upgrade_name == 'flat_damage':
            self.upgrade_flat_damage += 1
        elif upgrade_name == 'armor_pen':
            self.upgrade_armor_pen += 1
        self.update_display()
    
    def add_gem_upgrade(self, upgrade_name):
        """Add a gem upgrade level"""
        max_level = self.GEM_UPGRADE_BONUSES[upgrade_name]['max_level']
        if self.gem_upgrades[upgrade_name] < max_level:
            self.gem_upgrades[upgrade_name] += 1
            self.update_display()
    
    def remove_gem_upgrade(self, upgrade_name):
        """Remove a gem upgrade level"""
        if self.gem_upgrades[upgrade_name] > 0:
            self.gem_upgrades[upgrade_name] -= 1
            self.update_display()
    
    def get_gem_upgrade_cost(self, upgrade_name):
        """Get the cost of the next gem upgrade level"""
        current_level = self.gem_upgrades[upgrade_name]
        max_level = self.GEM_UPGRADE_BONUSES[upgrade_name]['max_level']
        if current_level >= max_level:
            return None
        return self.GEM_COSTS[upgrade_name][current_level]
    
    def get_total_gem_cost(self, upgrade_name):
        """Get total gems spent on this upgrade"""
        current_level = self.gem_upgrades[upgrade_name]
        if current_level == 0:
            return 0
        return sum(self.GEM_COSTS[upgrade_name][:current_level])
    
    def calculate_gem_upgrade_efficiency(self, upgrade_name):
        """Calculate the efficiency of adding one gem upgrade level"""
        max_level = self.GEM_UPGRADE_BONUSES[upgrade_name]['max_level']
        if self.gem_upgrades[upgrade_name] >= max_level:
            return 0, 0
        
        current_stats = self.get_total_stats()
        current_floors = self.calculate_floors_per_run(current_stats, self.current_stage)
        
        self.gem_upgrades[upgrade_name] += 1
        new_stats = self.get_total_stats()
        new_floors = self.calculate_floors_per_run(new_stats, self.current_stage)
        self.gem_upgrades[upgrade_name] -= 1
        
        if current_floors > 0:
            percent_improvement = ((new_floors - current_floors) / current_floors) * 100
        else:
            percent_improvement = 0
        
        return new_floors, percent_improvement
    
    def remove_upgrade(self, upgrade_name):
        if upgrade_name == 'flat_damage' and self.upgrade_flat_damage > 0:
            self.upgrade_flat_damage -= 1
        elif upgrade_name == 'armor_pen' and self.upgrade_armor_pen > 0:
            self.upgrade_armor_pen -= 1
        self.update_display()
    
    def create_widgets(self):
        # Header with title and controls
        header_frame = tk.Frame(self.window, background="#E3F2FD", relief=tk.RIDGE, borderwidth=1)
        header_frame.pack(fill=tk.X, padx=5, pady=(5, 2))
        
        # Left: Title
        title_label = tk.Label(
            header_frame,
            text="Archaeology Skill Point Optimizer",
            font=("Arial", 14, "bold"),
            background="#E3F2FD"
        )
        title_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Right: Stage selector, Enrage toggle, and Reset button
        controls_frame = tk.Frame(header_frame, background="#E3F2FD")
        controls_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        tk.Label(controls_frame, text="Stage:", font=("Arial", 10), 
                background="#E3F2FD").pack(side=tk.LEFT, padx=(0, 3))
        
        self.stage_var = tk.StringVar(value="1-2")
        self.stage_combo = ttk.Combobox(
            controls_frame, 
            textvariable=self.stage_var,
            values=STAGE_RANGES,
            state="readonly",
            width=7
        )
        self.stage_combo.pack(side=tk.LEFT, padx=(0, 3))
        self.stage_combo.bind("<<ComboboxSelected>>", self._on_stage_changed)
        
        # Help icon for stage selection
        stage_help_label = tk.Label(controls_frame, text="?", font=("Arial", 9, "bold"), 
                                   cursor="hand2", foreground="#1976D2", background="#E3F2FD")
        stage_help_label.pack(side=tk.LEFT, padx=(0, 10))
        self._create_stage_help_tooltip(stage_help_label)
        
        # Enrage toggle checkbox
        self.enrage_enabled = tk.BooleanVar(value=True)
        enrage_checkbox = ttk.Checkbutton(
            controls_frame,
            text="Enrage",
            variable=self.enrage_enabled,
            command=self.update_display
        )
        enrage_checkbox.pack(side=tk.LEFT, padx=(0, 10))
        
        reset_btn = ttk.Button(controls_frame, text="Reset", command=self.reset_and_update, width=8)
        reset_btn.pack(side=tk.LEFT)
        
        # Center: Level display
        self.level_label = tk.Label(header_frame, text="Level: 1", font=("Arial", 12, "bold"),
                                   background="#E3F2FD", foreground="#1976D2")
        self.level_label.pack(side=tk.LEFT, padx=20)
        
        # Main content - 3 columns
        content_frame = tk.Frame(self.window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.columnconfigure(2, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Column 1: Stats
        self.create_stats_column(content_frame)
        
        # Column 2: Skills & Upgrades
        self.create_skills_column(content_frame)
        
        # Column 3: Results & Chart
        self.create_results_column(content_frame)
    
    def create_stats_column(self, parent):
        """Left column: Current stats and allocations"""
        col_frame = tk.Frame(parent, background="#E3F2FD", relief=tk.RIDGE, borderwidth=2)
        col_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
        
        # Stats header
        tk.Label(col_frame, text="Current Stats", font=("Arial", 11, "bold"), 
                background="#E3F2FD").pack(pady=(5, 3))
        
        # Stats grid
        stats_grid = tk.Frame(col_frame, background="#E3F2FD")
        stats_grid.pack(fill=tk.X, padx=8, pady=2)
        
        self.stat_labels = {}
        stat_names = [
            ("Damage:", "total_damage"),
            ("Armor Pen:", "armor_pen"),
            ("Stamina:", "max_stamina"),
            ("Crit %:", "crit_chance"),
            ("Crit Dmg:", "crit_damage"),
            ("One-Hit %:", "one_hit_chance"),
        ]
        
        for i, (label_text, key) in enumerate(stat_names):
            tk.Label(stats_grid, text=label_text, background="#E3F2FD", 
                    font=("Arial", 9), anchor=tk.W).grid(row=i, column=0, sticky=tk.W, pady=1)
            value_label = tk.Label(stats_grid, text="—", background="#E3F2FD", 
                                  font=("Arial", 9, "bold"), anchor=tk.E, width=8)
            value_label.grid(row=i, column=1, sticky=tk.E, pady=1)
            self.stat_labels[key] = value_label
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Skill allocations
        tk.Label(col_frame, text="Skill Points", font=("Arial", 10, "bold"), 
                background="#E3F2FD").pack(pady=(0, 3))
        
        alloc_grid = tk.Frame(col_frame, background="#E3F2FD")
        alloc_grid.pack(fill=tk.X, padx=8, pady=2)
        
        self.alloc_labels = {}
        for i, skill in enumerate(['strength', 'agility', 'intellect', 'perception', 'luck']):
            tk.Label(alloc_grid, text=f"{skill[:3].upper()}:", background="#E3F2FD",
                    font=("Arial", 9)).grid(row=i, column=0, sticky=tk.W, pady=1)
            value_label = tk.Label(alloc_grid, text="0", background="#E3F2FD", 
                                  font=("Arial", 9, "bold"), width=4, anchor=tk.E)
            value_label.grid(row=i, column=1, sticky=tk.E, pady=1)
            self.alloc_labels[skill] = value_label
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Upgrades
        tk.Label(col_frame, text="Upgrades", font=("Arial", 10, "bold"), 
                background="#E3F2FD").pack(pady=(0, 3))
        
        upgrade_grid = tk.Frame(col_frame, background="#E3F2FD")
        upgrade_grid.pack(fill=tk.X, padx=8, pady=2)
        
        self.upgrade_labels = {}
        tk.Label(upgrade_grid, text="Flat Dmg:", background="#E3F2FD", font=("Arial", 9)).grid(
            row=0, column=0, sticky=tk.W, pady=1)
        self.upgrade_labels['flat_damage'] = tk.Label(upgrade_grid, text="+0", 
            background="#E3F2FD", font=("Arial", 9, "bold"), width=4, anchor=tk.E)
        self.upgrade_labels['flat_damage'].grid(row=0, column=1, sticky=tk.E, pady=1)
        
        tk.Label(upgrade_grid, text="Armor Pen:", background="#E3F2FD", font=("Arial", 9)).grid(
            row=1, column=0, sticky=tk.W, pady=1)
        self.upgrade_labels['armor_pen'] = tk.Label(upgrade_grid, text="+0", 
            background="#E3F2FD", font=("Arial", 9, "bold"), width=4, anchor=tk.E)
        self.upgrade_labels['armor_pen'].grid(row=1, column=1, sticky=tk.E, pady=1)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Mod Chances
        tk.Label(col_frame, text="Mod Chances", font=("Arial", 10, "bold"), 
                background="#E3F2FD").pack(pady=(0, 3))
        
        mod_grid = tk.Frame(col_frame, background="#E3F2FD")
        mod_grid.pack(fill=tk.X, padx=8, pady=2)
        
        self.mod_labels = {}
        mod_names = [
            ("Exp Mod:", "exp_mod_chance"),
            ("Loot Mod:", "loot_mod_chance"),
            ("Speed Mod:", "speed_mod_chance"),
            ("Stamina Mod:", "stamina_mod_chance"),
        ]
        
        for i, (label_text, key) in enumerate(mod_names):
            tk.Label(mod_grid, text=label_text, background="#E3F2FD", 
                    font=("Arial", 9), anchor=tk.W).grid(row=i, column=0, sticky=tk.W, pady=1)
            value_label = tk.Label(mod_grid, text="0.00%", background="#E3F2FD", 
                                  font=("Arial", 9, "bold"), anchor=tk.E, width=7,
                                  foreground="#9932CC")
            value_label.grid(row=i, column=1, sticky=tk.E, pady=1)
            self.mod_labels[key] = value_label
    
    def create_skills_column(self, parent):
        """Middle column: Skill and upgrade buttons"""
        col_frame = tk.Frame(parent, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        col_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=0)
        
        tk.Label(col_frame, text="Add Points", font=("Arial", 11, "bold"), 
                background="#E8F5E9").pack(pady=(5, 3))
        
        tk.Label(col_frame, text="% = improvement in floors/run", 
                font=("Arial", 8), foreground="gray", background="#E8F5E9").pack(pady=(0, 5))
        
        # Skills
        self.skill_buttons = {}
        self.skill_efficiency_labels = {}
        
        skills_frame = tk.Frame(col_frame, background="#E8F5E9")
        skills_frame.pack(fill=tk.X, padx=5, pady=2)
        
        skill_info = {
            'strength': "Dmg, Crit Dmg",
            'agility': "Stamina, Crit",
            'intellect': "XP Bonus",
            'perception': "Frags, Armor Pen",
            'luck': "Crit, One-Hit",
        }
        
        for i, (skill, info) in enumerate(skill_info.items()):
            row_frame = tk.Frame(skills_frame, background="#E8F5E9")
            row_frame.pack(fill=tk.X, pady=1)
            
            minus_btn = tk.Button(row_frame, text="-", width=2, font=("Arial", 8, "bold"),
                                 command=lambda s=skill: self.remove_skill_point(s))
            minus_btn.pack(side=tk.LEFT, padx=(0, 1))
            
            plus_btn = tk.Button(row_frame, text="+", width=2, font=("Arial", 8, "bold"),
                                command=lambda s=skill: self.add_skill_point(s))
            plus_btn.pack(side=tk.LEFT, padx=(0, 3))
            
            tk.Label(row_frame, text=f"{skill.capitalize()}", background="#E8F5E9", 
                    font=("Arial", 9, "bold"), width=9, anchor=tk.W).pack(side=tk.LEFT)
            
            eff_label = tk.Label(row_frame, text="—", background="#E8F5E9", 
                                font=("Arial", 9, "bold"), foreground="#2E7D32", width=7, anchor=tk.E)
            eff_label.pack(side=tk.LEFT, padx=(0, 3))
            self.skill_efficiency_labels[skill] = eff_label
            
            tk.Label(row_frame, text=info, background="#E8F5E9", 
                    font=("Arial", 7), foreground="gray").pack(side=tk.LEFT)
            
            self.skill_buttons[skill] = (minus_btn, plus_btn)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Upgrades
        tk.Label(col_frame, text="Upgrades", font=("Arial", 10, "bold"), 
                background="#E8F5E9").pack(pady=(0, 3))
        
        self.upgrade_buttons = {}
        self.upgrade_efficiency_labels = {}
        
        upgrades_frame = tk.Frame(col_frame, background="#E8F5E9")
        upgrades_frame.pack(fill=tk.X, padx=5, pady=2)
        
        for upgrade in ['flat_damage', 'armor_pen']:
            row_frame = tk.Frame(upgrades_frame, background="#E8F5E9")
            row_frame.pack(fill=tk.X, pady=1)
            
            minus_btn = tk.Button(row_frame, text="-", width=2, font=("Arial", 8, "bold"),
                                 command=lambda u=upgrade: self.remove_upgrade(u))
            minus_btn.pack(side=tk.LEFT, padx=(0, 1))
            
            plus_btn = tk.Button(row_frame, text="+", width=2, font=("Arial", 8, "bold"),
                                command=lambda u=upgrade: self.add_upgrade(u))
            plus_btn.pack(side=tk.LEFT, padx=(0, 3))
            
            label_text = "Flat Damage" if upgrade == 'flat_damage' else "Armor Pen"
            tk.Label(row_frame, text=label_text, background="#E8F5E9", 
                    font=("Arial", 9, "bold"), width=11, anchor=tk.W).pack(side=tk.LEFT)
            
            eff_label = tk.Label(row_frame, text="—", background="#E8F5E9", 
                                font=("Arial", 9, "bold"), foreground="#2E7D32", width=7, anchor=tk.E)
            eff_label.pack(side=tk.LEFT)
            self.upgrade_efficiency_labels[upgrade] = eff_label
            
            self.upgrade_buttons[upgrade] = (minus_btn, plus_btn)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Gem Upgrades Section - with gem icon and distinct styling
        gem_header_frame = tk.Frame(col_frame, background="#E8F5E9")
        gem_header_frame.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        # Load gem icon
        try:
            gem_icon_path = Path(__file__).parent.parent / "sprites" / "gem.png"
            if gem_icon_path.exists():
                gem_image = Image.open(gem_icon_path)
                gem_image = gem_image.resize((16, 16), Image.Resampling.LANCZOS)
                self.gem_icon_photo = ImageTk.PhotoImage(gem_image)
                gem_icon_label = tk.Label(gem_header_frame, image=self.gem_icon_photo, background="#E8F5E9")
                gem_icon_label.pack(side=tk.LEFT, padx=(0, 5))
        except:
            pass
        
        tk.Label(gem_header_frame, text="Gem Upgrades", font=("Arial", 10, "bold"), 
                background="#E8F5E9", foreground="#9932CC").pack(side=tk.LEFT)
        
        self.gem_upgrade_buttons = {}
        self.gem_upgrade_labels = {}
        self.gem_upgrade_efficiency_labels = {}
        
        gem_upgrades_frame = tk.Frame(col_frame, background="#E8F5E9")
        gem_upgrades_frame.pack(fill=tk.X, padx=5, pady=2)
        
        gem_upgrade_info = {
            'stamina': ("Stamina", "+2 Stam, +0.05% Stam Mod", 50),
            'xp': ("XP Boost", "+5% XP, +0.05% Exp Mod", 25),
            'fragment': ("Fragment", "+2% Frags, +0.05% Loot Mod", 25),
        }
        
        for gem_upgrade, (display_name, info, max_lvl) in gem_upgrade_info.items():
            row_frame = tk.Frame(gem_upgrades_frame, background="#E8F5E9")
            row_frame.pack(fill=tk.X, pady=1)
            
            minus_btn = tk.Button(row_frame, text="-", width=2, font=("Arial", 8, "bold"),
                                 command=lambda u=gem_upgrade: self.remove_gem_upgrade(u))
            minus_btn.pack(side=tk.LEFT, padx=(0, 1))
            
            plus_btn = tk.Button(row_frame, text="+", width=2, font=("Arial", 8, "bold"),
                                command=lambda u=gem_upgrade: self.add_gem_upgrade(u))
            plus_btn.pack(side=tk.LEFT, padx=(0, 3))
            
            # Level display with gem icon indicator
            level_label = tk.Label(row_frame, text="0", background="#E8F5E9", 
                                  font=("Arial", 9, "bold"), foreground="#9932CC", width=3, anchor=tk.E)
            level_label.pack(side=tk.LEFT, padx=(0, 3))
            self.gem_upgrade_labels[gem_upgrade] = level_label
            
            tk.Label(row_frame, text=display_name, background="#E8F5E9", 
                    font=("Arial", 9, "bold"), width=8, anchor=tk.W).pack(side=tk.LEFT)
            
            eff_label = tk.Label(row_frame, text="—", background="#E8F5E9", 
                                font=("Arial", 9, "bold"), foreground="#2E7D32", width=7, anchor=tk.E)
            eff_label.pack(side=tk.LEFT, padx=(0, 3))
            self.gem_upgrade_efficiency_labels[gem_upgrade] = eff_label
            
            # Info tooltip
            info_label = tk.Label(row_frame, text="?", background="#E8F5E9", 
                                 font=("Arial", 7), foreground="gray", cursor="hand2")
            info_label.pack(side=tk.LEFT)
            self._create_gem_upgrade_tooltip(info_label, gem_upgrade, info, max_lvl)
            
            self.gem_upgrade_buttons[gem_upgrade] = (minus_btn, plus_btn)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Recommendation
        tk.Label(col_frame, text="Best Next Point:", font=("Arial", 10, "bold"), 
                background="#E8F5E9").pack(pady=(0, 3))
        
        self.recommendation_label = tk.Label(col_frame, text="—", font=("Arial", 10, "bold"),
                                            background="#E8F5E9", foreground="#1976D2")
        self.recommendation_label.pack(pady=(0, 5))
    
    def _create_gem_upgrade_tooltip(self, widget, upgrade_name, info, max_level):
        """Creates a tooltip showing gem upgrade details and costs"""
        def on_enter(event):
            current_level = self.gem_upgrades[upgrade_name]
            next_cost = self.get_gem_upgrade_cost(upgrade_name)
            total_spent = self.get_total_gem_cost(upgrade_name)
            
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            # Outer frame for shadow effect
            outer_frame = tk.Frame(tooltip, background="#9932CC", relief=tk.FLAT, borderwidth=0)
            outer_frame.pack(padx=2, pady=2)
            
            # Inner frame
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF", relief=tk.FLAT, borderwidth=0)
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            # Title
            tk.Label(content_frame, text=f"Gem Upgrade: {upgrade_name.capitalize()}", 
                    font=("Arial", 10, "bold"), foreground="#9932CC", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            # Effect
            tk.Label(content_frame, text=f"Effect: {info}", 
                    font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W, pady=(2, 0))
            
            # Level
            tk.Label(content_frame, text=f"Level: {current_level} / {max_level}", 
                    font=("Arial", 9, "bold"), background="#FFFFFF").pack(anchor=tk.W, pady=(5, 0))
            
            # Next cost
            if next_cost:
                tk.Label(content_frame, text=f"Next Level: {next_cost} Gems", 
                        font=("Arial", 9), foreground="#2E7D32", 
                        background="#FFFFFF").pack(anchor=tk.W)
            else:
                tk.Label(content_frame, text="MAX LEVEL", 
                        font=("Arial", 9, "bold"), foreground="#C73E1D", 
                        background="#FFFFFF").pack(anchor=tk.W)
            
            # Total spent
            tk.Label(content_frame, text=f"Total Spent: {total_spent} Gems", 
                    font=("Arial", 9), foreground="gray", 
                    background="#FFFFFF").pack(anchor=tk.W, pady=(2, 0))
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _create_stage_help_tooltip(self, widget):
        """Creates a tooltip explaining how to use the Stage selector"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            # Position tooltip to the left of cursor to avoid going off-screen
            # Tooltip is roughly 320px wide, 400px tall
            tooltip_width = 320
            tooltip_height = 420
            
            # Get screen dimensions
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            
            # Calculate position - prefer left of cursor, with bounds checking
            x = event.x_root - tooltip_width - 10
            if x < 10:
                x = event.x_root + 20  # Fall back to right side if too close to left edge
            
            y = event.y_root - 50
            if y + tooltip_height > screen_height - 50:
                y = screen_height - tooltip_height - 50
            if y < 10:
                y = 10
            
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Outer frame for shadow effect
            outer_frame = tk.Frame(tooltip, background="#1976D2", relief=tk.FLAT, borderwidth=0)
            outer_frame.pack(padx=2, pady=2)
            
            # Inner frame
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF", relief=tk.FLAT, borderwidth=0)
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=12, pady=10)
            content_frame.pack()
            
            # Title
            tk.Label(content_frame, text="How to Choose Stage", 
                    font=("Arial", 11, "bold"), foreground="#1976D2", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()  # Spacer
            
            # Rule 1
            tk.Label(content_frame, text="Select your TARGET stage, not starting stage!", 
                    font=("Arial", 9, "bold"), foreground="#C73E1D", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()  # Spacer
            
            # Explanation
            lines = [
                "The Stage selector determines which blocks are",
                "used for efficiency calculations.",
                "",
                "Choose the stage where you typically END or",
                "where you get STUCK - that's your bottleneck.",
                "",
                "Examples:",
                "  - If you clear floors 1-3 easily but struggle",
                "    at floor 4 → select '3-4'",
                "  - If you can reach floor 6 → select '6-9'",
                "",
                "Why? You want to optimize for the blocks that",
                "slow you down, not the ones you breeze through.",
            ]
            
            for line in lines:
                tk.Label(content_frame, text=line, 
                        font=("Arial", 9), background="#FFFFFF",
                        anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()  # Spacer
            
            # Quick reference
            tk.Label(content_frame, text="Quick Reference:", 
                    font=("Arial", 9, "bold"), foreground="#2E7D32", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            ref_lines = [
                "  Stage 3+: Rare blocks appear (12 armor)",
                "  Stage 6+: Epic blocks appear (25 armor)",
                "  Stage 12+: Legendary blocks (50 armor)",
                "  Stage 20+: Mythic blocks (150 armor)",
            ]
            
            for line in ref_lines:
                tk.Label(content_frame, text=line, 
                        font=("Arial", 8), foreground="#555555",
                        background="#FFFFFF", anchor=tk.W).pack(anchor=tk.W)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def create_results_column(self, parent):
        """Right column: Results and spawn chart"""
        col_frame = tk.Frame(parent, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        col_frame.grid(row=0, column=2, sticky="nsew", padx=(2, 0), pady=0)
        
        # Results
        tk.Label(col_frame, text="Run Statistics", font=("Arial", 11, "bold"), 
                background="#FFF3E0").pack(pady=(5, 5))
        
        results_grid = tk.Frame(col_frame, background="#FFF3E0")
        results_grid.pack(fill=tk.X, padx=10, pady=2)
        
        # Floors per run - PRIMARY
        tk.Label(results_grid, text="Floors / Run:", font=("Arial", 10, "bold"), 
                background="#FFF3E0").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.floors_per_run_label = tk.Label(results_grid, text="—", 
                                             font=("Arial", 14, "bold"), 
                                             background="#FFF3E0", foreground="#2E7D32")
        self.floors_per_run_label.grid(row=0, column=1, sticky=tk.E, pady=2)
        
        # Blocks per run
        tk.Label(results_grid, text="Blocks / Run:", font=("Arial", 9), 
                background="#FFF3E0").grid(row=1, column=0, sticky=tk.W, pady=1)
        self.blocks_per_run_label = tk.Label(results_grid, text="—", 
                                             font=("Arial", 10, "bold"), 
                                             background="#FFF3E0", foreground="#1976D2")
        self.blocks_per_run_label.grid(row=1, column=1, sticky=tk.E, pady=1)
        
        # Avg hits
        tk.Label(results_grid, text="Avg Hits / Block:", font=("Arial", 9), 
                background="#FFF3E0").grid(row=2, column=0, sticky=tk.W, pady=1)
        self.avg_hits_label = tk.Label(results_grid, text="—", 
                                       font=("Arial", 10, "bold"), 
                                       background="#FFF3E0", foreground="#1976D2")
        self.avg_hits_label.grid(row=2, column=1, sticky=tk.E, pady=1)
        
        # Effective damage
        tk.Label(results_grid, text="Eff. Dmg (Dirt/Com):", font=("Arial", 9), 
                background="#FFF3E0").grid(row=3, column=0, sticky=tk.W, pady=1)
        self.eff_dmg_label = tk.Label(results_grid, text="—", 
                                      font=("Arial", 10, "bold"), 
                                      background="#FFF3E0", foreground="#C73E1D")
        self.eff_dmg_label.grid(row=3, column=1, sticky=tk.E, pady=1)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=8, padx=5)
        
        # Spawn distribution chart
        tk.Label(col_frame, text="Block Spawn Distribution", font=("Arial", 10, "bold"), 
                background="#FFF3E0").pack(pady=(0, 3))
        
        self.chart_canvas = tk.Canvas(col_frame, width=280, height=140, 
                                      background="#FFFFFF", highlightthickness=1,
                                      highlightbackground="#CCCCCC")
        self.chart_canvas.pack(padx=10, pady=(0, 5))
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Average block stats for current stage
        tk.Label(col_frame, text="Avg Block Stats (weighted)", font=("Arial", 10, "bold"), 
                background="#FFF3E0").pack(pady=(0, 3))
        
        avg_stats_grid = tk.Frame(col_frame, background="#FFF3E0")
        avg_stats_grid.pack(fill=tk.X, padx=10, pady=2)
        
        # HP
        tk.Label(avg_stats_grid, text="Avg HP:", font=("Arial", 9), 
                background="#FFF3E0").grid(row=0, column=0, sticky=tk.W, pady=1)
        self.avg_block_hp_label = tk.Label(avg_stats_grid, text="—", 
                                          font=("Arial", 9, "bold"), 
                                          background="#FFF3E0", foreground="#C73E1D")
        self.avg_block_hp_label.grid(row=0, column=1, sticky=tk.E, pady=1)
        
        # Armor
        tk.Label(avg_stats_grid, text="Avg Armor:", font=("Arial", 9), 
                background="#FFF3E0").grid(row=1, column=0, sticky=tk.W, pady=1)
        self.avg_block_armor_label = tk.Label(avg_stats_grid, text="—", 
                                             font=("Arial", 9, "bold"), 
                                             background="#FFF3E0", foreground="#1976D2")
        self.avg_block_armor_label.grid(row=1, column=1, sticky=tk.E, pady=1)
        
        # XP
        tk.Label(avg_stats_grid, text="Avg XP:", font=("Arial", 9), 
                background="#FFF3E0").grid(row=2, column=0, sticky=tk.W, pady=1)
        self.avg_block_xp_label = tk.Label(avg_stats_grid, text="—", 
                                          font=("Arial", 9, "bold"), 
                                          background="#FFF3E0", foreground="#2E7D32")
        self.avg_block_xp_label.grid(row=2, column=1, sticky=tk.E, pady=1)
        
        # Fragments
        tk.Label(avg_stats_grid, text="Avg Fragment:", font=("Arial", 9), 
                background="#FFF3E0").grid(row=3, column=0, sticky=tk.W, pady=1)
        self.avg_block_frag_label = tk.Label(avg_stats_grid, text="—", 
                                            font=("Arial", 9, "bold"), 
                                            background="#FFF3E0", foreground="#9932CC")
        self.avg_block_frag_label.grid(row=3, column=1, sticky=tk.E, pady=1)
        
        # Armor pen needed hint
        tk.Label(avg_stats_grid, text="Armor Pen needed:", font=("Arial", 8), 
                background="#FFF3E0", foreground="gray").grid(row=4, column=0, sticky=tk.W, pady=(3,1))
        self.armor_pen_hint_label = tk.Label(avg_stats_grid, text="—", 
                                            font=("Arial", 8, "bold"), 
                                            background="#FFF3E0", foreground="#555555")
        self.armor_pen_hint_label.grid(row=4, column=1, sticky=tk.E, pady=(3,1))
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Damage Breakpoints Section
        breakpoint_header = tk.Frame(col_frame, background="#FFF3E0")
        breakpoint_header.pack(fill=tk.X, padx=5)
        
        tk.Label(breakpoint_header, text="Damage Breakpoints", font=("Arial", 10, "bold"), 
                background="#FFF3E0").pack(side=tk.LEFT)
        
        # Help icon for breakpoints
        bp_help_label = tk.Label(breakpoint_header, text="?", font=("Arial", 9, "bold"), 
                                cursor="hand2", foreground="#C73E1D", background="#FFF3E0")
        bp_help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_breakpoint_help_tooltip(bp_help_label)
        
        # Best breakpoint recommendation
        self.best_bp_frame = tk.Frame(col_frame, background="#FFECB3", relief=tk.GROOVE, borderwidth=1)
        self.best_bp_frame.pack(fill=tk.X, padx=5, pady=(3, 2))
        
        best_bp_inner = tk.Frame(self.best_bp_frame, background="#FFECB3", padx=5, pady=3)
        best_bp_inner.pack(fill=tk.X)
        
        tk.Label(best_bp_inner, text="★ Best Next:", font=("Arial", 8, "bold"), 
                background="#FFECB3", foreground="#FF6F00").pack(side=tk.LEFT)
        
        self.best_bp_label = tk.Label(best_bp_inner, text="—", font=("Arial", 8), 
                                     background="#FFECB3", foreground="#333333")
        self.best_bp_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Help icon for best breakpoint
        best_bp_help = tk.Label(best_bp_inner, text="?", font=("Arial", 8, "bold"), 
                               cursor="hand2", foreground="#FF6F00", background="#FFECB3")
        best_bp_help.pack(side=tk.RIGHT)
        self._create_best_bp_help_tooltip(best_bp_help)
        
        # Container for breakpoint rows (will be dynamically sorted)
        self.bp_container = tk.Frame(col_frame, background="#FFF3E0")
        self.bp_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        
        # We'll store breakpoint labels in a dict for updating
        self.breakpoint_labels = {}
        
        # Create a label for each block type that can appear
        for block_type in BLOCK_TYPES:
            row_frame = tk.Frame(self.bp_container, background="#FFF3E0")
            # Don't pack yet - will be packed in sorted order during update
            
            color = self.BLOCK_COLORS.get(block_type, '#888888')
            
            # Block type name
            name_label = tk.Label(row_frame, text=f"{block_type.capitalize()[:4]}:", 
                                 font=("Arial", 8, "bold"), foreground=color,
                                 background="#FFF3E0", width=5, anchor=tk.W)
            name_label.pack(side=tk.LEFT)
            
            # Stamina impact indicator
            impact_label = tk.Label(row_frame, text="", font=("Arial", 7), 
                                   background="#FFF3E0", foreground="#888888", width=8, anchor=tk.W)
            impact_label.pack(side=tk.LEFT)
            
            # Current hits
            hits_label = tk.Label(row_frame, text="—", font=("Arial", 8), 
                                 background="#FFF3E0", width=6, anchor=tk.W)
            hits_label.pack(side=tk.LEFT)
            
            # Next breakpoint info
            bp_info_label = tk.Label(row_frame, text="", font=("Arial", 8), 
                                    background="#FFF3E0", foreground="#555555",
                                    anchor=tk.W)
            bp_info_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.breakpoint_labels[block_type] = {
                'row': row_frame,
                'name': name_label,
                'impact': impact_label,
                'hits': hits_label,
                'bp_info': bp_info_label,
                'tooltip_data': {}  # Will store data for dynamic tooltip
            }
            
            # Add hover tooltip for each row
            self._create_block_breakpoint_tooltip(row_frame, block_type)
    
    def _create_breakpoint_help_tooltip(self, widget):
        """Creates a tooltip explaining damage breakpoints"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            # Position tooltip smartly
            tooltip_width = 320
            x = event.x_root - tooltip_width - 10
            if x < 10:
                x = event.x_root + 20
            y = event.y_root - 20
            
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#C73E1D", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text="What are Breakpoints?", 
                    font=("Arial", 10, "bold"), foreground="#C73E1D", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            lines = [
                "",
                "A breakpoint is where your damage",
                "reduces hits-to-kill by 1.",
                "",
                "Example: Block with 20 HP",
                "  10 dmg → 2 hits (10+10=20)",
                "  15 dmg → 2 hits (15+5=20, wasted!)",
                "  20 dmg → 1 hit ← BREAKPOINT",
                "",
                "Damage between breakpoints is wasted.",
                "Focus upgrades to reach the next one!",
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
    
    def _create_best_bp_help_tooltip(self, widget):
        """Creates a tooltip explaining the 'Best Next Breakpoint' recommendation"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 340
            x = event.x_root - tooltip_width - 10
            if x < 10:
                x = event.x_root + 20
            y = event.y_root - 20
            
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#FF6F00", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text="Best Next Breakpoint", 
                    font=("Arial", 10, "bold"), foreground="#FF6F00", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            lines = [
                "",
                "This shows the most efficient breakpoint to aim for.",
                "",
                "How it's calculated:",
                "  1. Stamina Impact = Spawn% × Hits per block",
                "     (How much stamina this block costs on average)",
                "",
                "  2. Stamina Saved = Impact reduction at breakpoint",
                "     (How much you save by needing 1 less hit)",
                "",
                "  3. Efficiency = Stamina Saved / DMG needed",
                "     (Best ratio = easiest breakpoint with high impact)",
                "",
                "★ The recommended breakpoint has the best efficiency.",
                "",
                "Blocks are sorted by current Stamina Impact (highest first).",
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
    
    def _create_block_breakpoint_tooltip(self, widget, block_type):
        """Creates a dynamic tooltip for a block's breakpoint row"""
        def on_enter(event):
            # Get current tooltip data
            data = self.breakpoint_labels[block_type].get('tooltip_data', {})
            if not data:
                return
            
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 280
            x = event.x_root - tooltip_width - 10
            if x < 10:
                x = event.x_root + 20
            y = event.y_root - 10
            
            tooltip.wm_geometry(f"+{x}+{y}")
            
            color = self.BLOCK_COLORS.get(block_type, '#888888')
            
            outer_frame = tk.Frame(tooltip, background=color, relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text=f"{block_type.capitalize()} Block", 
                    font=("Arial", 10, "bold"), foreground=color, 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            # Block stats
            tk.Label(content_frame, text=f"HP: {data.get('hp', '?')}  |  Armor: {data.get('armor', '?')}", 
                    font=("Arial", 9), foreground="#555555",
                    background="#FFFFFF").pack(anchor=tk.W, pady=(2, 5))
            
            # Current status
            tk.Label(content_frame, text=f"Your effective damage: {data.get('eff_dmg', '?')}", 
                    font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W)
            tk.Label(content_frame, text=f"Hits to kill: {data.get('hits', '?')}", 
                    font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W)
            
            # Spawn and impact
            tk.Label(content_frame, text="", background="#FFFFFF").pack()
            tk.Label(content_frame, text=f"Spawn rate: {data.get('spawn_pct', '?')}", 
                    font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W)
            tk.Label(content_frame, text=f"Stamina Impact: {data.get('impact', '?')} per floor", 
                    font=("Arial", 9, "bold"), foreground="#C73E1D",
                    background="#FFFFFF").pack(anchor=tk.W)
            
            # Next breakpoint
            if data.get('has_next_bp'):
                tk.Label(content_frame, text="", background="#FFFFFF").pack()
                tk.Label(content_frame, text="Next Breakpoint:", 
                        font=("Arial", 9, "bold"), background="#FFFFFF").pack(anchor=tk.W)
                tk.Label(content_frame, text=f"  Need +{data.get('dmg_needed', '?')} total damage", 
                        font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W)
                tk.Label(content_frame, text=f"  Saves {data.get('stamina_saved', '?')} stamina/floor", 
                        font=("Arial", 9), foreground="#2E7D32",
                        background="#FFFFFF").pack(anchor=tk.W)
                tk.Label(content_frame, text=f"  Efficiency: {data.get('efficiency', '?')}", 
                        font=("Arial", 9), foreground="#1976D2",
                        background="#FFFFFF").pack(anchor=tk.W)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def update_breakpoints_display(self):
        """Update the breakpoints display for all block types, sorted by stamina impact"""
        if not hasattr(self, 'breakpoint_labels'):
            return
        
        import math
        
        stats = self.get_total_stats()
        spawn_rates = get_normalized_spawn_rates(self.current_stage)
        block_mix = get_block_mix_for_floor(self.current_stage)
        
        # Calculate data for all blocks
        block_data_list = []
        
        for block_type in BLOCK_TYPES:
            labels = self.breakpoint_labels[block_type]
            spawn_rate = spawn_rates.get(block_type, 0)
            
            # Hide rows for blocks that don't spawn in current stage
            if spawn_rate <= 0:
                labels['row'].pack_forget()
                labels['tooltip_data'] = {}
                continue
            
            block_data = block_mix.get(block_type)
            if not block_data:
                labels['row'].pack_forget()
                labels['tooltip_data'] = {}
                continue
            
            bp = self.calculate_damage_breakpoints(
                block_data.health, block_data.armor, stats
            )
            
            current_hits = bp['current_hits']
            if current_hits == float('inf'):
                current_hits = 9999
            
            # Stamina impact = spawn_rate * hits * blocks_per_floor (15)
            stamina_impact = spawn_rate * current_hits * self.BLOCKS_PER_FLOOR
            
            # Calculate breakpoint efficiency if there's a next breakpoint
            bp_efficiency = 0
            stamina_saved = 0
            if bp['dmg_needed'] is not None and bp['dmg_needed'] > 0:
                # Stamina saved per floor if we reach the breakpoint
                new_hits = bp['next_breakpoint_hits']
                stamina_saved = spawn_rate * (current_hits - new_hits) * self.BLOCKS_PER_FLOOR
                # Efficiency = stamina saved per damage point needed
                bp_efficiency = stamina_saved / bp['dmg_needed'] if bp['dmg_needed'] > 0 else 0
            
            block_data_list.append({
                'block_type': block_type,
                'spawn_rate': spawn_rate,
                'current_hits': current_hits,
                'stamina_impact': stamina_impact,
                'bp': bp,
                'bp_efficiency': bp_efficiency,
                'stamina_saved': stamina_saved,
                'block_stats': block_data,
            })
        
        # Sort by stamina impact (highest first)
        block_data_list.sort(key=lambda x: x['stamina_impact'], reverse=True)
        
        # Find best next breakpoint (highest efficiency among those with a reachable breakpoint)
        best_bp = None
        best_efficiency = 0
        for bd in block_data_list:
            if bd['bp']['dmg_needed'] is not None and bd['bp']['dmg_needed'] > 0:
                if bd['bp_efficiency'] > best_efficiency:
                    best_efficiency = bd['bp_efficiency']
                    best_bp = bd
        
        # Update best breakpoint label
        if best_bp:
            bt = best_bp['block_type']
            dmg = best_bp['bp']['dmg_needed']
            saved = best_bp['stamina_saved']
            self.best_bp_label.config(
                text=f"{bt.capitalize()} (+{dmg:.0f} dmg → saves {saved:.1f} stam/floor)"
            )
            self.best_bp_frame.pack(fill=tk.X, padx=5, pady=(3, 2))
        else:
            self.best_bp_label.config(text="All blocks at breakpoint or one-shot!")
            self.best_bp_frame.pack(fill=tk.X, padx=5, pady=(3, 2))
        
        # Unpack all rows first
        for labels in self.breakpoint_labels.values():
            labels['row'].pack_forget()
        
        # Pack rows in sorted order and update labels
        for bd in block_data_list:
            block_type = bd['block_type']
            labels = self.breakpoint_labels[block_type]
            bp = bd['bp']
            current_hits = bd['current_hits']
            spawn_rate = bd['spawn_rate']
            stamina_impact = bd['stamina_impact']
            block_stats = bd['block_stats']
            
            # Pack in sorted order
            labels['row'].pack(fill=tk.X, pady=1)
            
            # Highlight if this is the best breakpoint
            is_best = (best_bp and block_type == best_bp['block_type'])
            bg_color = "#FFECB3" if is_best else "#FFF3E0"
            labels['row'].config(background=bg_color)
            for child in labels['row'].winfo_children():
                try:
                    child.config(background=bg_color)
                except:
                    pass
            
            # Update impact label
            labels['impact'].config(text=f"({stamina_impact:.1f})")
            
            # Format current hits
            if current_hits >= 9999:
                labels['hits'].config(text="∞ hits", foreground="#C73E1D")
            elif current_hits == 1:
                labels['hits'].config(text="1 hit ✓", foreground="#2E7D32")
            else:
                labels['hits'].config(text=f"{current_hits:.0f} hits", foreground="#1976D2")
            
            # Format breakpoint info
            if bp['next_breakpoint_dmg'] is not None and bp['dmg_needed'] > 0:
                prefix = "★ " if is_best else ""
                labels['bp_info'].config(
                    text=f"{prefix}+{bp['dmg_needed']:.0f} → {bp['next_breakpoint_hits']}h",
                    foreground="#FF6F00" if is_best else "#C73E1D"
                )
            elif current_hits == 1:
                labels['bp_info'].config(text="(one-shot)", foreground="#2E7D32")
            else:
                labels['bp_info'].config(text="(at bp)", foreground="#2E7D32")
            
            # Store tooltip data
            labels['tooltip_data'] = {
                'hp': block_stats.health,
                'armor': block_stats.armor,
                'eff_dmg': bp['current_eff_dmg'],
                'hits': current_hits if current_hits < 9999 else "∞",
                'spawn_pct': f"{spawn_rate*100:.1f}%",
                'impact': f"{stamina_impact:.1f}",
                'has_next_bp': bp['dmg_needed'] is not None and bp['dmg_needed'] > 0,
                'dmg_needed': bp['dmg_needed'],
                'stamina_saved': f"{bd['stamina_saved']:.2f}",
                'efficiency': f"{bd['bp_efficiency']:.3f} stam/dmg",
            }
    
    def update_avg_block_stats(self):
        """Calculate and display weighted average block stats for current stage"""
        if not hasattr(self, 'avg_block_hp_label'):
            return
        
        spawn_rates = get_normalized_spawn_rates(self.current_stage)
        block_mix = get_block_mix_for_floor(self.current_stage)
        
        avg_hp = 0
        avg_armor = 0
        avg_xp = 0
        avg_frag = 0
        max_armor = 0
        
        for block_type, spawn_chance in spawn_rates.items():
            if spawn_chance <= 0:
                continue
            block_data = block_mix.get(block_type)
            if not block_data:
                continue
            
            avg_hp += spawn_chance * block_data.health
            avg_armor += spawn_chance * block_data.armor
            avg_xp += spawn_chance * block_data.xp
            avg_frag += spawn_chance * block_data.fragment
            
            # Track max armor for "armor pen needed" hint
            if block_data.armor > max_armor:
                max_armor = block_data.armor
        
        # Update labels
        self.avg_block_hp_label.config(text=f"{avg_hp:.0f}")
        self.avg_block_armor_label.config(text=f"{avg_armor:.1f}")
        self.avg_block_xp_label.config(text=f"{avg_xp:.2f}")
        self.avg_block_frag_label.config(text=f"{avg_frag:.3f}")
        
        # Armor pen hint: show how much pen is needed to negate average armor
        stats = self.get_total_stats()
        current_pen = stats['armor_pen']
        
        if avg_armor <= 0:
            self.armor_pen_hint_label.config(text="0 (no armor)", foreground="#2E7D32")
        elif current_pen >= max_armor:
            self.armor_pen_hint_label.config(text=f"OK ({current_pen:.0f} >= {max_armor:.0f})", foreground="#2E7D32")
        elif current_pen >= avg_armor:
            self.armor_pen_hint_label.config(text=f"{avg_armor:.0f} avg, {max_armor:.0f} max", foreground="#FF8C00")
        else:
            needed = avg_armor - current_pen
            self.armor_pen_hint_label.config(text=f"+{needed:.0f} for avg", foreground="#C73E1D")
    
    def update_spawn_chart(self):
        if not hasattr(self, 'chart_canvas'):
            return
            
        self.chart_canvas.delete("all")
        spawn_rates = get_normalized_spawn_rates(self.current_stage)
        
        # Chart layout
        canvas_width = 280
        margin_left = 70
        margin_right = 10
        margin_top = 5
        bar_height = 18
        bar_spacing = 4
        chart_width = canvas_width - margin_left - margin_right
        
        y = margin_top
        for block_type in BLOCK_TYPES:
            rate = spawn_rates.get(block_type, 0)
            color = self.BLOCK_COLORS.get(block_type, '#888888')
            
            # Label on left
            self.chart_canvas.create_text(
                margin_left - 5, y + bar_height/2,
                text=block_type.capitalize(), anchor=tk.E,
                font=("Arial", 8), fill="#333333"
            )
            
            if rate > 0:
                # Draw bar
                bar_width = max(2, int(chart_width * rate))
                self.chart_canvas.create_rectangle(
                    margin_left, y,
                    margin_left + bar_width, y + bar_height,
                    fill=color, outline=color
                )
                
                # Percentage label
                pct_text = f"{rate*100:.1f}%"
                if bar_width > 35:
                    self.chart_canvas.create_text(
                        margin_left + bar_width - 3, y + bar_height/2,
                        text=pct_text, anchor=tk.E,
                        font=("Arial", 7, "bold"), fill="white"
                    )
                else:
                    self.chart_canvas.create_text(
                        margin_left + bar_width + 3, y + bar_height/2,
                        text=pct_text, anchor=tk.W,
                        font=("Arial", 7), fill="#333333"
                    )
            else:
                # Gray placeholder for 0%
                self.chart_canvas.create_rectangle(
                    margin_left, y,
                    margin_left + 2, y + bar_height,
                    fill="#DDDDDD", outline="#DDDDDD"
                )
                self.chart_canvas.create_text(
                    margin_left + 5, y + bar_height/2,
                    text="0%", anchor=tk.W,
                    font=("Arial", 7), fill="#999999"
                )
            
            y += bar_height + bar_spacing
    
    def update_display(self):
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
        
        # Update allocations
        for skill, label in self.alloc_labels.items():
            label.config(text=str(self.skill_points[skill]))
        
        # Update upgrades
        self.upgrade_labels['flat_damage'].config(text=f"+{self.upgrade_flat_damage}")
        self.upgrade_labels['armor_pen'].config(text=f"+{self.upgrade_armor_pen}")
        
        # Update mod chances (show 2 decimal places since values are small, e.g. 0.20%)
        if hasattr(self, 'mod_labels'):
            self.mod_labels['exp_mod_chance'].config(text=f"{stats['exp_mod_chance']*100:.2f}%")
            self.mod_labels['loot_mod_chance'].config(text=f"{stats['loot_mod_chance']*100:.2f}%")
            self.mod_labels['speed_mod_chance'].config(text=f"{stats['speed_mod_chance']*100:.2f}%")
            self.mod_labels['stamina_mod_chance'].config(text=f"{stats['stamina_mod_chance']*100:.2f}%")
        
        # Update gem upgrade levels
        if hasattr(self, 'gem_upgrade_labels'):
            for gem_upgrade, label in self.gem_upgrade_labels.items():
                level = self.gem_upgrades.get(gem_upgrade, 0)
                max_level = self.GEM_UPGRADE_BONUSES[gem_upgrade]['max_level']
                label.config(text=f"{level}")
                # Color changes based on level
                if level >= max_level:
                    label.config(foreground="#C73E1D")  # Red when maxed
                elif level > 0:
                    label.config(foreground="#9932CC")  # Purple when active
                else:
                    label.config(foreground="gray")  # Gray when 0
        
        # Calculate efficiencies
        best_choice = None
        best_improvement = -float('inf')
        
        for skill in self.skill_efficiency_labels:
            _, improvement = self.calculate_skill_efficiency(skill)
            self.skill_efficiency_labels[skill].config(text=f"+{improvement:.2f}%")
            if improvement > best_improvement:
                best_improvement = improvement
                best_choice = (skill, 'skill')
        
        for upgrade in self.upgrade_efficiency_labels:
            _, improvement = self.calculate_upgrade_efficiency(upgrade)
            self.upgrade_efficiency_labels[upgrade].config(text=f"+{improvement:.2f}%")
            if improvement > best_improvement:
                best_improvement = improvement
                best_choice = (upgrade, 'upgrade')
        
        # Calculate gem upgrade efficiencies
        if hasattr(self, 'gem_upgrade_efficiency_labels'):
            for gem_upgrade in self.gem_upgrade_efficiency_labels:
                max_level = self.GEM_UPGRADE_BONUSES[gem_upgrade]['max_level']
                if self.gem_upgrades[gem_upgrade] >= max_level:
                    self.gem_upgrade_efficiency_labels[gem_upgrade].config(text="MAX", foreground="#C73E1D")
                else:
                    _, improvement = self.calculate_gem_upgrade_efficiency(gem_upgrade)
                    self.gem_upgrade_efficiency_labels[gem_upgrade].config(
                        text=f"+{improvement:.2f}%", foreground="#2E7D32")
                    # Note: We don't include gem upgrades in "best choice" since they cost gems
        
        # Update recommendation
        if best_choice:
            name, type_ = best_choice
            display_name = name.capitalize() if type_ == 'skill' else name.replace('_', ' ').title()
            self.recommendation_label.config(text=f"+1 {display_name}")
        
        # Update results
        floors_per_run = self.calculate_floors_per_run(stats, self.current_stage)
        self.floors_per_run_label.config(text=f"{floors_per_run:.2f}")
        
        blocks_per_run = self.calculate_blocks_per_run(stats, self.current_stage)
        self.blocks_per_run_label.config(text=f"{blocks_per_run:.1f}")
        
        # Average hits
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
        
        # Effective damage
        dirt_data = block_mix.get('dirt')
        common_data = block_mix.get('common')
        dirt_armor = dirt_data.armor if dirt_data else 0
        common_armor = common_data.armor if common_data else 5
        
        eff_dirt = self.calculate_effective_damage(stats, dirt_armor)
        eff_common = self.calculate_effective_damage(stats, common_armor)
        self.eff_dmg_label.config(text=f"{eff_dirt} / {eff_common}")
        
        # Update chart
        self.update_spawn_chart()
        
        # Update average block stats
        self.update_avg_block_stats()
        
        # Update damage breakpoints
        self.update_breakpoints_display()
    
    def reset_and_update(self):
        self.reset_to_level1()
        self.stage_var.set("1-2")
        self.update_display()
        self.save_state()
    
    def _on_stage_changed(self, event=None):
        stage_str = self.stage_var.get()
        stage_map = {
            "1-2": 1, "3-4": 3, "5": 5, "6-9": 6, "10-11": 10,
            "12-14": 12, "15-19": 15, "20-24": 20, "25-29": 25,
            "30-49": 30, "50-75": 50, "75+": 76,
        }
        self.current_stage = stage_map.get(stage_str, 1)
        self.update_display()
