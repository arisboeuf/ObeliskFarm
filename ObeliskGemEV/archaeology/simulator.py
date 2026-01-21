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

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import calculate_tooltip_position

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
        'arch_xp': {
            'arch_xp_bonus': 0.02,  # +2% Archaeology Exp
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
        # Archaeology Exp Gain +2% per level (Common currency, not Gems)
        # Costs: 1.00, 1.20, 1.44, 1.73, 2.07, 2.49, 2.99, 3.58, 4.30, 5.16,
        #        6.19, 7.43, 8.92, 10.70, 12.84, 15.41, 18.49, 22.19, 26.62, 31.95,
        #        38.34, 46.01, 55.21, 66.25, 79.50
        'arch_xp': [
            1.00, 1.20, 1.44, 1.73, 2.07, 2.49, 2.99, 3.58, 4.30, 5.16,  # 1-10
            6.19, 7.43, 8.92, 10.70, 12.84, 15.41, 18.49, 22.19, 26.62, 31.95,  # 11-20
            38.34, 46.01, 55.21, 66.25, 79.50,  # 21-25
        ],
    }
    
    # Common costs for fragment upgrades (Flat Damage, Armor Pen)
    COMMON_UPGRADE_COSTS = {
        # Flat Damage +1 per level (0.50 base, 1.2x multiplier)
        'flat_damage': [
            0.50, 0.60, 0.72, 0.86, 1.04, 1.24, 1.49, 1.79, 2.15, 2.58,  # 1-10
            3.10, 3.72, 4.46, 5.35, 6.42, 7.70, 9.24, 11.09, 13.31, 15.97,  # 11-20
            19.17, 23.00, 27.60, 33.12, 39.75,  # 21-25
        ],
        # Armor Penetration +1 per level (0.75 base, 1.2x multiplier)
        'armor_pen': [
            0.75, 0.90, 1.08, 1.30, 1.56, 1.87, 2.24, 2.69, 3.22, 3.87,  # 1-10
            4.64, 5.57, 6.69, 8.02, 9.63, 11.56, 13.87, 16.64, 19.97, 23.96,  # 11-20
            28.75, 34.50, 41.40, 49.69, 59.62,  # 21-25
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
        # Maximized window on startup (like main window)
        self.window.state('zoomed')
        self.window.resizable(True, True)
        self.window.minsize(1000, 600)
        
        # Set icon
        try:
            icon_path = Path(__file__).parent.parent / "sprites" / "common" / "gem.png"
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
            'block_cards': self.block_cards,
            'enrage_enabled': self.enrage_enabled.get() if hasattr(self, 'enrage_enabled') else True,
            'forecast_levels_1': self.forecast_levels_1.get() if hasattr(self, 'forecast_levels_1') else 5,
            'budget_points': self.budget_points.get() if hasattr(self, 'budget_points') else 20,
            'xp_budget_points': self.xp_budget_points.get() if hasattr(self, 'xp_budget_points') else 20,
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
                'stamina': 0, 'xp': 0, 'fragment': 0, 'arch_xp': 0,
            })
            # Ensure new upgrade types are present if loading old save
            if 'arch_xp' not in self.gem_upgrades:
                self.gem_upgrades['arch_xp'] = 0
            
            # Load block cards
            self.block_cards = state.get('block_cards', {
                'dirt': 0, 'common': 0, 'rare': 0, 'epic': 0, 'legendary': 0, 'mythic': 0
            })
            # Ensure all block types are present
            for bt in ['dirt', 'common', 'rare', 'epic', 'legendary', 'mythic']:
                if bt not in self.block_cards:
                    self.block_cards[bt] = 0
            
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
            
            # Update forecast level
            if hasattr(self, 'forecast_levels_1'):
                self.forecast_levels_1.set(state.get('forecast_levels_1', 5))
                self.forecast_1_level_label.config(text=f"+{self.forecast_levels_1.get()}")
            
            # Update budget points
            if hasattr(self, 'budget_points'):
                self.budget_points.set(state.get('budget_points', 20))
                self.budget_points_label.config(text=str(self.budget_points.get()))
            
            # Update XP budget points
            if hasattr(self, 'xp_budget_points'):
                self.xp_budget_points.set(state.get('xp_budget_points', 20))
                self.xp_budget_points_label.config(text=str(self.xp_budget_points.get()))
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
            'arch_xp': 0,
        }
        # Block cards
        self.block_cards = {
            'dirt': 0, 'common': 0, 'rare': 0, 'epic': 0, 'legendary': 0, 'mythic': 0
        }
        # Block cards: 0 = none, 1 = normal card, 2 = gilded card
        # Card: -10% HP, +10% XP; Gilded: -20% HP, +20% XP
        self.block_cards = {
            'dirt': 0, 'common': 0, 'rare': 0, 'epic': 0, 'legendary': 0, 'mythic': 0
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
        gem_arch_xp = self.gem_upgrades.get('arch_xp', 0)
        
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
        
        # Archaeology XP bonus from common upgrade
        arch_xp_mult = 1.0 + gem_arch_xp * self.GEM_UPGRADE_BONUSES['arch_xp']['arch_xp_bonus']
        
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
            # Archaeology XP multiplier (applies to leveling)
            'arch_xp_mult': arch_xp_mult,
        }
    
    def calculate_effective_damage(self, stats, block_armor):
        effective_armor = max(0, block_armor - stats['armor_pen'])
        effective = max(1, int(stats['total_damage'] - effective_armor))
        return effective
    
    def get_block_hp_with_card(self, block_hp, block_type):
        """Apply card HP reduction: Card = -10%, Gilded = -20%"""
        card_level = self.block_cards.get(block_type, 0)
        if card_level == 1:
            return int(block_hp * 0.90)
        elif card_level == 2:
            return int(block_hp * 0.80)
        return block_hp
    
    def get_block_xp_multiplier(self, block_type):
        """Get XP multiplier from card: Card = +10%, Gilded = +20%"""
        card_level = self.block_cards.get(block_type, 0)
        if card_level == 1:
            return 1.10
        elif card_level == 2:
            return 1.20
        return 1.0
    
    def calculate_damage_breakpoints(self, block_hp, block_armor, stats, block_type=None):
        """
        Calculate damage breakpoints for a specific block.
        Returns info about current hits, avg hits with crits, and next breakpoint.
        
        A breakpoint is where you need one less hit to kill the block.
        Example: 20 HP block
          - At 10 dmg: 2 hits (ceil(20/10) = 2)
          - At 11 dmg: 2 hits (ceil(20/11) = 2) 
          - At 20 dmg: 1 hit (ceil(20/20) = 1) <-- breakpoint at 20
        
        If block_type is provided, card HP reduction is applied.
        """
        import math
        
        # Apply card HP reduction if block_type is provided
        if block_type:
            block_hp = self.get_block_hp_with_card(block_hp, block_type)
        
        effective_armor = max(0, block_armor - stats['armor_pen'])
        current_eff_dmg = self.calculate_effective_damage(stats, block_armor)
        current_hits = math.ceil(block_hp / current_eff_dmg) if current_eff_dmg > 0 else float('inf')
        
        # Calculate average hits with crits (using calculate_hits_to_kill logic)
        avg_hits = self.calculate_hits_to_kill(stats, block_hp, block_armor)
        
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
            'avg_hits': avg_hits,
            'next_breakpoint_dmg': next_breakpoint_dmg,
            'next_breakpoint_hits': next_breakpoint_hits,
            'dmg_needed': dmg_needed,
        }
    
    def calculate_hits_to_kill(self, stats, block_hp, block_armor, block_type=None):
        """
        Calculate expected hits to kill a block, accounting for:
        - Base damage with armor penetration
        - Critical hits
        - One-hit chance
        - Enrage ability (5 charges every 60s with +20% dmg, +100% crit dmg) - if enabled
        - Card HP reduction (if block_type provided)
        """
        # Apply card HP reduction if block_type is provided
        if block_type:
            block_hp = self.get_block_hp_with_card(block_hp, block_type)
        
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
            # Pass block_type to apply card HP reduction
            hits = self.calculate_hits_to_kill(stats, block_data.health, block_data.armor, block_type)
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
                # Pass block_type to apply card HP reduction
                hits = self.calculate_hits_to_kill(stats, block_data.health, block_data.armor, block_type)
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
    
    def calculate_xp_per_run(self, stats, starting_floor: int):
        """
        Calculate expected XP gained per run, accounting for:
        - XP from each block based on spawn rates and block XP values
        - XP multiplier from Intellect and Gem upgrades
        - Exp Mod chance (avg 4x XP when triggered)
        - Card XP bonuses per block type
        
        Returns:
            Expected total XP for one full run
        """
        floors = self.calculate_floors_per_run(stats, starting_floor)
        if floors <= 0:
            return 0.0
        
        xp_mult = stats['xp_mult']
        exp_mod_chance = stats.get('exp_mod_chance', 0)
        
        # Exp mod gives 3x-5x XP (avg 4x), so expected multiplier from mod is:
        # (1 - exp_mod_chance) * 1.0 + exp_mod_chance * 4.0 = 1 + exp_mod_chance * 3
        exp_mod_factor = 1 + exp_mod_chance * (self.MOD_EXP_MULTIPLIER_AVG - 1)
        
        total_xp = 0.0
        current_floor = starting_floor
        floors_to_process = int(floors)  # Full floors
        partial_floor = floors - floors_to_process  # Partial floor fraction
        
        for i in range(floors_to_process + 1):  # +1 for partial floor
            if i == floors_to_process:
                # Partial floor - scale by remaining fraction
                floor_mult = partial_floor
                if floor_mult <= 0:
                    break
            else:
                floor_mult = 1.0
            
            spawn_rates = get_normalized_spawn_rates(current_floor)
            block_mix = get_block_mix_for_floor(current_floor)
            
            floor_xp = 0.0
            for block_type, spawn_chance in spawn_rates.items():
                if spawn_chance <= 0:
                    continue
                block_data = block_mix.get(block_type)
                if not block_data:
                    continue
                
                # Block base XP
                block_xp = block_data.xp
                
                # Apply card XP bonus
                card_mult = self.get_block_xp_multiplier(block_type)
                block_xp *= card_mult
                
                # Weight by spawn chance
                floor_xp += spawn_chance * block_xp
            
            # XP for this floor: blocks * avg_xp * xp_mult * exp_mod_factor
            floor_total_xp = self.BLOCKS_PER_FLOOR * floor_xp * xp_mult * exp_mod_factor
            total_xp += floor_total_xp * floor_mult
            
            current_floor += 1
        
        return total_xp
    
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
    
    def reset_all_skill_points(self):
        """Reset all skill points to 0"""
        total_points = sum(self.skill_points.values())
        self.skill_points = {
            'strength': 0, 'agility': 0, 'intellect': 0, 'perception': 0, 'luck': 0,
        }
        self.level = max(1, self.level - total_points)
        self.update_display()
    
    def add_upgrade(self, upgrade_name):
        if upgrade_name == 'flat_damage':
            self.upgrade_flat_damage += 1
        elif upgrade_name == 'armor_pen':
            self.upgrade_armor_pen += 1
        self.update_display()
    
    def reset_all_upgrades(self):
        """Reset all common fragment upgrades to 0"""
        self.upgrade_flat_damage = 0
        self.upgrade_armor_pen = 0
        self.gem_upgrades['arch_xp'] = 0
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
    
    def get_common_upgrade_cost(self, upgrade_name):
        """Get the Common cost of the next upgrade level for Flat Damage or Armor Pen"""
        if upgrade_name not in self.COMMON_UPGRADE_COSTS:
            return None
        current_level = getattr(self, f'upgrade_{upgrade_name}', 0)
        max_level = len(self.COMMON_UPGRADE_COSTS[upgrade_name])
        if current_level >= max_level:
            return None
        return self.COMMON_UPGRADE_COSTS[upgrade_name][current_level]
    
    def get_total_common_cost(self, upgrade_name):
        """Get total Common spent on this upgrade"""
        if upgrade_name not in self.COMMON_UPGRADE_COSTS:
            return 0
        current_level = getattr(self, f'upgrade_{upgrade_name}', 0)
        if current_level == 0:
            return 0
        return sum(self.COMMON_UPGRADE_COSTS[upgrade_name][:current_level])
    
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
    
    def calculate_forecast(self, levels_ahead: int):
        """
        Calculate the optimal skill point distribution for the next N levels.
        
        Uses brute-force search for small N (5-10 levels).
        Returns the best distribution and the resulting floors/run improvement.
        
        Args:
            levels_ahead: Number of skill points to allocate (e.g., 5 or 10)
        
        Returns:
            dict with:
                - 'distribution': dict of skill -> points to add
                - 'floors_per_run': resulting floors/run
                - 'improvement_pct': percentage improvement
                - 'path': list of skills in order of allocation
        """
        skills = ['strength', 'agility', 'intellect', 'perception', 'luck']
        current_floors = self.calculate_floors_per_run(self.get_total_stats(), self.current_stage)
        
        best_result = {
            'distribution': {s: 0 for s in skills},
            'floors_per_run': current_floors,
            'improvement_pct': 0.0,
            'path': [],
        }
        
        # Generate all possible distributions of N points among 5 skills
        # This is a "stars and bars" problem: C(n+k-1, k-1) combinations
        # For 10 points, 5 skills: C(14,4) = 1001 combinations - very manageable
        
        def generate_distributions(n_points, n_skills):
            """Generate all ways to distribute n_points among n_skills"""
            if n_skills == 1:
                yield (n_points,)
                return
            for i in range(n_points + 1):
                for rest in generate_distributions(n_points - i, n_skills - 1):
                    yield (i,) + rest
        
        best_floors = current_floors
        best_dist_tuple = tuple(0 for _ in skills)
        
        for dist_tuple in generate_distributions(levels_ahead, len(skills)):
            # Apply distribution temporarily
            for skill, points in zip(skills, dist_tuple):
                self.skill_points[skill] += points
            
            # Calculate floors with this distribution
            new_floors = self.calculate_floors_per_run(self.get_total_stats(), self.current_stage)
            
            if new_floors > best_floors:
                best_floors = new_floors
                best_dist_tuple = dist_tuple
                best_result['distribution'] = {s: p for s, p in zip(skills, dist_tuple)}
                best_result['floors_per_run'] = new_floors
            
            # Revert changes
            for skill, points in zip(skills, dist_tuple):
                self.skill_points[skill] -= points
        
        # Calculate improvement percentage
        if current_floors > 0:
            best_result['improvement_pct'] = ((best_floors - current_floors) / current_floors) * 100
        
        # Build the optimal allocation path using greedy within the optimal endpoint
        # We know where we want to end up, now find the best order to get there
        remaining = {s: p for s, p in zip(skills, best_dist_tuple)}
        path = []
        
        for _ in range(levels_ahead):
            # Find which skill to add next that gives best immediate gain
            # (only considering skills that are part of the optimal final distribution)
            best_next = None
            best_next_floors = -1
            
            for skill in skills:
                if remaining[skill] > 0:
                    self.skill_points[skill] += 1
                    test_floors = self.calculate_floors_per_run(self.get_total_stats(), self.current_stage)
                    self.skill_points[skill] -= 1
                    
                    if test_floors > best_next_floors:
                        best_next_floors = test_floors
                        best_next = skill
            
            if best_next:
                path.append(best_next)
                remaining[best_next] -= 1
                self.skill_points[best_next] += 1
        
        # Revert all path changes
        for skill in path:
            self.skill_points[skill] -= 1
        
        best_result['path'] = path
        
        return best_result
    
    def calculate_xp_forecast(self, levels_ahead: int):
        """
        Calculate the optimal skill point distribution for maximum XP/run.
        
        Similar to calculate_forecast() but optimizes for XP instead of floors.
        This will value Intellect much more highly since it directly boosts XP.
        
        Args:
            levels_ahead: Number of skill points to allocate
        
        Returns:
            dict with:
                - 'distribution': dict of skill -> points to add
                - 'xp_per_run': resulting XP/run
                - 'improvement_pct': percentage improvement
                - 'path': list of skills in order of allocation
        """
        skills = ['strength', 'agility', 'intellect', 'perception', 'luck']
        current_xp = self.calculate_xp_per_run(self.get_total_stats(), self.current_stage)
        
        best_result = {
            'distribution': {s: 0 for s in skills},
            'xp_per_run': current_xp,
            'improvement_pct': 0.0,
            'path': [],
        }
        
        def generate_distributions(n_points, n_skills):
            """Generate all ways to distribute n_points among n_skills"""
            if n_skills == 1:
                yield (n_points,)
                return
            for i in range(n_points + 1):
                for rest in generate_distributions(n_points - i, n_skills - 1):
                    yield (i,) + rest
        
        best_xp = current_xp
        best_dist_tuple = tuple(0 for _ in skills)
        
        for dist_tuple in generate_distributions(levels_ahead, len(skills)):
            # Apply distribution temporarily
            for skill, points in zip(skills, dist_tuple):
                self.skill_points[skill] += points
            
            # Calculate XP with this distribution
            new_xp = self.calculate_xp_per_run(self.get_total_stats(), self.current_stage)
            
            if new_xp > best_xp:
                best_xp = new_xp
                best_dist_tuple = dist_tuple
                best_result['distribution'] = {s: p for s, p in zip(skills, dist_tuple)}
                best_result['xp_per_run'] = new_xp
            
            # Revert changes
            for skill, points in zip(skills, dist_tuple):
                self.skill_points[skill] -= points
        
        # Calculate improvement percentage
        if current_xp > 0:
            best_result['improvement_pct'] = ((best_xp - current_xp) / current_xp) * 100
        
        # Build the optimal allocation path using greedy within the optimal endpoint
        remaining = {s: p for s, p in zip(skills, best_dist_tuple)}
        path = []
        
        for _ in range(levels_ahead):
            best_next = None
            best_next_xp = -1
            
            for skill in skills:
                if remaining[skill] > 0:
                    self.skill_points[skill] += 1
                    test_xp = self.calculate_xp_per_run(self.get_total_stats(), self.current_stage)
                    self.skill_points[skill] -= 1
                    
                    if test_xp > best_next_xp:
                        best_next_xp = test_xp
                        best_next = skill
            
            if best_next:
                path.append(best_next)
                remaining[best_next] -= 1
                self.skill_points[best_next] += 1
        
        # Revert all path changes
        for skill in path:
            self.skill_points[skill] -= 1
        
        best_result['path'] = path
        
        return best_result
    
    def format_distribution(self, distribution: dict) -> str:
        """Format a skill distribution as a compact string like '3S 2A 1L'"""
        abbrev = {'strength': 'S', 'agility': 'A', 'intellect': 'I', 'perception': 'P', 'luck': 'L'}
        parts = []
        for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
            if distribution.get(skill, 0) > 0:
                parts.append(f"{distribution[skill]}{abbrev[skill]}")
        return ' '.join(parts) if parts else '—'
    
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
        
        # Stats header with help icon
        stats_header_frame = tk.Frame(col_frame, background="#E3F2FD")
        stats_header_frame.pack(pady=(5, 3))
        
        tk.Label(stats_header_frame, text="Current Stats", font=("Arial", 11, "bold"), 
                background="#E3F2FD").pack(side=tk.LEFT)
        
        stats_help_label = tk.Label(stats_header_frame, text="?", font=("Arial", 9, "bold"), 
                                   cursor="hand2", foreground="#1976D2", background="#E3F2FD")
        stats_help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_stats_help_tooltip(stats_help_label)
        
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
        
        # Upgrades header with common fragment icon
        upgrade_header = tk.Frame(col_frame, background="#E3F2FD")
        upgrade_header.pack(fill=tk.X, padx=8, pady=(0, 3))
        
        tk.Label(upgrade_header, text="Upgrades", font=("Arial", 10, "bold"), 
                background="#E3F2FD").pack(side=tk.LEFT)
        
        # Load common fragment icon for stats column
        try:
            stats_frag_icon_path = Path(__file__).parent.parent / "sprites" / "archaeology" / "fragmentcommon.png"
            if stats_frag_icon_path.exists():
                stats_frag_image = Image.open(stats_frag_icon_path)
                stats_frag_image = stats_frag_image.resize((12, 12), Image.Resampling.LANCZOS)
                self.stats_frag_photo = ImageTk.PhotoImage(stats_frag_image)
                tk.Label(upgrade_header, image=self.stats_frag_photo, background="#E3F2FD").pack(side=tk.LEFT, padx=(5, 0))
        except:
            pass
        
        upgrade_grid = tk.Frame(col_frame, background="#E3F2FD")
        upgrade_grid.pack(fill=tk.X, padx=8, pady=2)
        
        self.upgrade_labels = {}
        self.upgrade_cost_icon_labels = {}
        
        # Flat Damage row
        tk.Label(upgrade_grid, text="Flat Dmg:", background="#E3F2FD", font=("Arial", 9)).grid(
            row=0, column=0, sticky=tk.W, pady=1)
        fd_frame = tk.Frame(upgrade_grid, background="#E3F2FD")
        fd_frame.grid(row=0, column=1, sticky=tk.E, pady=1)
        self.upgrade_labels['flat_damage'] = tk.Label(fd_frame, text="+0", 
            background="#E3F2FD", font=("Arial", 9, "bold"), anchor=tk.E)
        self.upgrade_labels['flat_damage'].pack(side=tk.LEFT)
        self.upgrade_cost_icon_labels['flat_damage'] = tk.Label(fd_frame, text="", 
            background="#E3F2FD", font=("Arial", 9), foreground="#555555", anchor=tk.E)
        self.upgrade_cost_icon_labels['flat_damage'].pack(side=tk.LEFT, padx=(3, 0))
        # Add small fragment icon after cost
        if hasattr(self, 'stats_frag_photo'):
            tk.Label(fd_frame, image=self.stats_frag_photo, background="#E3F2FD").pack(side=tk.LEFT)
        
        # Armor Pen row
        tk.Label(upgrade_grid, text="Armor Pen:", background="#E3F2FD", font=("Arial", 9)).grid(
            row=1, column=0, sticky=tk.W, pady=1)
        ap_frame = tk.Frame(upgrade_grid, background="#E3F2FD")
        ap_frame.grid(row=1, column=1, sticky=tk.E, pady=1)
        self.upgrade_labels['armor_pen'] = tk.Label(ap_frame, text="+0", 
            background="#E3F2FD", font=("Arial", 9, "bold"), anchor=tk.E)
        self.upgrade_labels['armor_pen'].pack(side=tk.LEFT)
        self.upgrade_cost_icon_labels['armor_pen'] = tk.Label(ap_frame, text="", 
            background="#E3F2FD", font=("Arial", 9), foreground="#555555", anchor=tk.E)
        self.upgrade_cost_icon_labels['armor_pen'].pack(side=tk.LEFT, padx=(3, 0))
        # Add small fragment icon after cost
        if hasattr(self, 'stats_frag_photo'):
            tk.Label(ap_frame, image=self.stats_frag_photo, background="#E3F2FD").pack(side=tk.LEFT)
        
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
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Multipliers section
        tk.Label(col_frame, text="Multipliers", font=("Arial", 10, "bold"), 
                background="#E3F2FD").pack(pady=(0, 3))
        
        mult_grid = tk.Frame(col_frame, background="#E3F2FD")
        mult_grid.pack(fill=tk.X, padx=8, pady=2)
        
        self.mult_labels = {}
        mult_names = [
            ("XP Mult:", "xp_mult"),
            ("Frag Mult:", "fragment_mult"),
            ("Arch XP:", "arch_xp_mult"),
        ]
        
        for i, (label_text, key) in enumerate(mult_names):
            tk.Label(mult_grid, text=label_text, background="#E3F2FD", 
                    font=("Arial", 9), anchor=tk.W).grid(row=i, column=0, sticky=tk.W, pady=1)
            value_label = tk.Label(mult_grid, text="1.00x", background="#E3F2FD", 
                                  font=("Arial", 9, "bold"), anchor=tk.E, width=7,
                                  foreground="#2E7D32")
            value_label.grid(row=i, column=1, sticky=tk.E, pady=1)
            self.mult_labels[key] = value_label
    
    def create_skills_column(self, parent):
        """Middle column: Skill and upgrade buttons"""
        col_frame = tk.Frame(parent, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        col_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=0)
        
        # Header with Reset button
        skill_header = tk.Frame(col_frame, background="#E8F5E9")
        skill_header.pack(fill=tk.X, padx=5, pady=(5, 3))
        
        tk.Label(skill_header, text="Add Points", font=("Arial", 11, "bold"), 
                background="#E8F5E9").pack(side=tk.LEFT)
        
        tk.Button(skill_header, text="Reset", font=("Arial", 7), 
                 command=self.reset_all_skill_points).pack(side=tk.RIGHT)
        
        tk.Label(col_frame, text="% = improvement in floors/run", 
                font=("Arial", 9), foreground="#555555", background="#E8F5E9").pack(pady=(0, 5))
        
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
                    font=("Arial", 9), foreground="#555555").pack(side=tk.LEFT)
            
            # Help icon with tooltip for skill details
            skill_help_label = tk.Label(row_frame, text="?", background="#E8F5E9", 
                                       font=("Arial", 8, "bold"), foreground="#1976D2", cursor="hand2")
            skill_help_label.pack(side=tk.LEFT, padx=(3, 0))
            self._create_skill_tooltip(skill_help_label, skill)
            
            self.skill_buttons[skill] = (minus_btn, plus_btn)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Upgrades (Common Fragment cost) with Reset button
        upgrade_header_frame = tk.Frame(col_frame, background="#E8F5E9")
        upgrade_header_frame.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        tk.Label(upgrade_header_frame, text="Upgrades", font=("Arial", 10, "bold"), 
                background="#E8F5E9").pack(side=tk.LEFT)
        
        # Load common fragment icon for header
        try:
            common_frag_icon_path = Path(__file__).parent.parent / "sprites" / "archaeology" / "fragmentcommon.png"
            if common_frag_icon_path.exists():
                common_frag_image = Image.open(common_frag_icon_path)
                common_frag_image = common_frag_image.resize((14, 14), Image.Resampling.LANCZOS)
                self.common_frag_header_photo = ImageTk.PhotoImage(common_frag_image)
                common_frag_label = tk.Label(upgrade_header_frame, image=self.common_frag_header_photo, 
                                            background="#E8F5E9")
                common_frag_label.pack(side=tk.LEFT, padx=(5, 0))
        except:
            # Fallback to text
            tk.Label(upgrade_header_frame, text="(Common)", font=("Arial", 8), 
                    foreground="#808080", background="#E8F5E9").pack(side=tk.LEFT, padx=(3, 0))
        
        # Reset button for upgrades
        tk.Button(upgrade_header_frame, text="Reset", font=("Arial", 7), 
                 command=self.reset_all_upgrades).pack(side=tk.RIGHT)
        
        self.upgrade_buttons = {}
        self.upgrade_efficiency_labels = {}
        self.upgrade_cost_labels = {}
        self.upgrade_level_labels = {}
        
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
            
            # Level counter (like arch_xp)
            level_label = tk.Label(row_frame, text="0", background="#E8F5E9", 
                                  font=("Arial", 9, "bold"), foreground="#808080", width=2, anchor=tk.E)
            level_label.pack(side=tk.LEFT, padx=(0, 3))
            self.upgrade_level_labels[upgrade] = level_label
            
            label_text = "Flat Dmg" if upgrade == 'flat_damage' else "Armor Pen"
            tk.Label(row_frame, text=label_text, background="#E8F5E9", 
                    font=("Arial", 9, "bold"), width=8, anchor=tk.W).pack(side=tk.LEFT)
            
            # Efficiency label (% improvement)
            eff_label = tk.Label(row_frame, text="—", background="#E8F5E9", 
                                font=("Arial", 9, "bold"), foreground="#2E7D32", width=7, anchor=tk.E)
            eff_label.pack(side=tk.LEFT)
            self.upgrade_efficiency_labels[upgrade] = eff_label
            
            # Cost efficiency label (%/Common)
            cost_eff_label = tk.Label(row_frame, text="", background="#E8F5E9", 
                                     font=("Arial", 9), foreground="#555555", anchor=tk.W)
            cost_eff_label.pack(side=tk.LEFT, padx=(3, 0))
            self.upgrade_cost_labels[upgrade] = cost_eff_label
            
            # Info icon with tooltip
            info_label = tk.Label(row_frame, text="?", background="#E8F5E9", 
                                 font=("Arial", 9, "bold"), foreground="#1976D2", cursor="hand2")
            info_label.pack(side=tk.LEFT, padx=(2, 0))
            self._create_common_upgrade_tooltip(info_label, upgrade)
            
            self.upgrade_buttons[upgrade] = (minus_btn, plus_btn)
        
        # Arch XP Upgrade (also costs Common, but stored in gem_upgrades)
        arch_xp_frame = tk.Frame(upgrades_frame, background="#E8F5E9")
        arch_xp_frame.pack(fill=tk.X, pady=1)
        
        arch_xp_minus_btn = tk.Button(arch_xp_frame, text="-", width=2, font=("Arial", 8, "bold"),
                             command=lambda: self.remove_gem_upgrade('arch_xp'))
        arch_xp_minus_btn.pack(side=tk.LEFT, padx=(0, 1))
        
        arch_xp_plus_btn = tk.Button(arch_xp_frame, text="+", width=2, font=("Arial", 8, "bold"),
                            command=lambda: self.add_gem_upgrade('arch_xp'))
        arch_xp_plus_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        # Level display
        self.arch_xp_level_label = tk.Label(arch_xp_frame, text="0", background="#E8F5E9", 
                              font=("Arial", 9, "bold"), foreground="#808080", width=2, anchor=tk.E)
        self.arch_xp_level_label.pack(side=tk.LEFT, padx=(0, 3))
        
        tk.Label(arch_xp_frame, text="Exp Gain", background="#E8F5E9", 
                font=("Arial", 9, "bold"), width=8, anchor=tk.W).pack(side=tk.LEFT)
        
        # Efficiency label (shows +X% per level effect, not floors improvement)
        self.arch_xp_eff_label = tk.Label(arch_xp_frame, text="+2%", background="#E8F5E9", 
                            font=("Arial", 9), foreground="#2E7D32", width=5, anchor=tk.E)
        self.arch_xp_eff_label.pack(side=tk.LEFT)
        
        # Cost efficiency label
        self.arch_xp_cost_label = tk.Label(arch_xp_frame, text="", background="#E8F5E9", 
                                 font=("Arial", 9), foreground="#555555", anchor=tk.W)
        self.arch_xp_cost_label.pack(side=tk.LEFT, padx=(3, 0))
        
        # Add common fragment icon after cost
        if hasattr(self, 'common_frag_header_photo'):
            tk.Label(arch_xp_frame, image=self.common_frag_header_photo, background="#E8F5E9").pack(side=tk.LEFT)
        
        # Info icon with tooltip
        arch_xp_info_label = tk.Label(arch_xp_frame, text="?", background="#E8F5E9", 
                             font=("Arial", 9, "bold"), foreground="#1976D2", cursor="hand2")
        arch_xp_info_label.pack(side=tk.LEFT, padx=(2, 0))
        self._create_arch_xp_tooltip(arch_xp_info_label)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Gem Upgrades Section - with gem icon and distinct styling
        gem_header_frame = tk.Frame(col_frame, background="#E8F5E9")
        gem_header_frame.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        # Load gem icon
        try:
            gem_icon_path = Path(__file__).parent.parent / "sprites" / "common" / "gem.png"
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
                                 font=("Arial", 9, "bold"), foreground="#1976D2", cursor="hand2")
            info_label.pack(side=tk.LEFT)
            self._create_gem_upgrade_tooltip(info_label, gem_upgrade, info, max_lvl)
            
            self.gem_upgrade_buttons[gem_upgrade] = (minus_btn, plus_btn)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Simple Greedy Recommendation (Best Next Point)
        rec_frame = tk.Frame(col_frame, background="#FFECB3", relief=tk.GROOVE, borderwidth=1)
        rec_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        rec_inner = tk.Frame(rec_frame, background="#FFECB3", padx=8, pady=5)
        rec_inner.pack(fill=tk.X)
        
        tk.Label(rec_inner, text="Best Next (Greedy):", font=("Arial", 9, "bold"),
                background="#FFECB3", foreground="#FF6F00").pack(side=tk.LEFT)
        self.recommendation_label = tk.Label(rec_inner, text="—", font=("Arial", 11, "bold"),
                                            background="#FFECB3", foreground="#1976D2")
        self.recommendation_label.pack(side=tk.LEFT, padx=(8, 0))
        
        # Help icon
        rec_help = tk.Label(rec_inner, text="?", font=("Arial", 8, "bold"),
                           cursor="hand2", foreground="#FF6F00", background="#FFECB3")
        rec_help.pack(side=tk.RIGHT)
        self._create_greedy_help_tooltip(rec_help)
    
    def _create_greedy_help_tooltip(self, widget):
        """Creates a tooltip explaining the greedy recommendation"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 280
            tooltip_height = 200
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#FF6F00", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text="Greedy Recommendation", 
                    font=("Arial", 10, "bold"), foreground="#FF6F00", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            lines = [
                "",
                "Shows the single best next skill point.",
                "",
                "This is 'greedy' - it only looks one step ahead.",
                "Good for quick decisions, but may miss",
                "important damage breakpoints.",
                "",
                "For strategic planning, see the Skill Forecast",
                "section on the right which plans 5-10 levels ahead.",
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
    
    def _create_arch_xp_tooltip(self, widget):
        """Creates a tooltip for the Archaeology Exp Gain upgrade"""
        def on_enter(event):
            current_level = self.gem_upgrades.get('arch_xp', 0)
            max_level = self.GEM_UPGRADE_BONUSES['arch_xp']['max_level']
            next_cost = self.get_gem_upgrade_cost('arch_xp')
            total_spent = self.get_total_gem_cost('arch_xp')
            
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 300
            tooltip_height = 250
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Outer frame for shadow effect (gray for Common)
            outer_frame = tk.Frame(tooltip, background="#808080", relief=tk.FLAT, borderwidth=0)
            outer_frame.pack(padx=2, pady=2)
            
            # Inner frame
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF", relief=tk.FLAT, borderwidth=0)
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            # Title with icon
            title_frame = tk.Frame(content_frame, background="#FFFFFF")
            title_frame.pack(anchor=tk.W)
            
            # Try to load common fragment icon
            try:
                icon_path = Path(__file__).parent.parent / "sprites" / "archaeology" / "fragmentcommon.png"
                if icon_path.exists():
                    icon_image = Image.open(icon_path)
                    icon_image = icon_image.resize((16, 16), Image.Resampling.LANCZOS)
                    tooltip.icon_photo = ImageTk.PhotoImage(icon_image)
                    tk.Label(title_frame, image=tooltip.icon_photo, background="#FFFFFF").pack(side=tk.LEFT, padx=(0, 5))
            except:
                pass
            
            tk.Label(title_frame, text="Common Upgrade: Exp Gain +2%", 
                    font=("Arial", 10, "bold"), foreground="#808080", 
                    background="#FFFFFF").pack(side=tk.LEFT)
            
            # Effect
            tk.Label(content_frame, text="Effect: +2% Archaeology Exp per level", 
                    font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W, pady=(2, 0))
            
            # Current bonus
            current_bonus = current_level * 2
            tk.Label(content_frame, text=f"Current Bonus: +{current_bonus}% Archaeology Exp", 
                    font=("Arial", 9, "bold"), foreground="#2E7D32",
                    background="#FFFFFF").pack(anchor=tk.W, pady=(2, 0))
            
            # Level
            tk.Label(content_frame, text=f"Level: {current_level} / {max_level}", 
                    font=("Arial", 9, "bold"), background="#FFFFFF").pack(anchor=tk.W, pady=(5, 0))
            
            # Next cost with icon
            if next_cost:
                cost_frame = tk.Frame(content_frame, background="#FFFFFF")
                cost_frame.pack(anchor=tk.W)
                tk.Label(cost_frame, text=f"Next Level: {next_cost:.2f}", 
                        font=("Arial", 9), foreground="#2E7D32", 
                        background="#FFFFFF").pack(side=tk.LEFT)
                try:
                    if hasattr(tooltip, 'icon_photo'):
                        tk.Label(cost_frame, image=tooltip.icon_photo, background="#FFFFFF").pack(side=tk.LEFT, padx=(3, 0))
                except:
                    tk.Label(cost_frame, text=" Common", font=("Arial", 9), foreground="#2E7D32", 
                            background="#FFFFFF").pack(side=tk.LEFT)
            else:
                tk.Label(content_frame, text="MAX LEVEL", 
                        font=("Arial", 9, "bold"), foreground="#C73E1D", 
                        background="#FFFFFF").pack(anchor=tk.W)
            
            # Total spent with icon
            total_frame = tk.Frame(content_frame, background="#FFFFFF")
            total_frame.pack(anchor=tk.W, pady=(2, 0))
            tk.Label(total_frame, text=f"Total Spent: {total_spent:.2f}", 
                    font=("Arial", 9), foreground="gray", 
                    background="#FFFFFF").pack(side=tk.LEFT)
            try:
                if hasattr(tooltip, 'icon_photo'):
                    tk.Label(total_frame, image=tooltip.icon_photo, background="#FFFFFF").pack(side=tk.LEFT, padx=(3, 0))
            except:
                tk.Label(total_frame, text=" Common", font=("Arial", 9), foreground="gray", 
                        background="#FFFFFF").pack(side=tk.LEFT)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _create_common_upgrade_tooltip(self, widget, upgrade_name):
        """Creates a tooltip showing Common upgrade details and costs"""
        def on_enter(event):
            current_level = getattr(self, f'upgrade_{upgrade_name}', 0)
            next_cost = self.get_common_upgrade_cost(upgrade_name)
            total_spent = self.get_total_common_cost(upgrade_name)
            max_level = len(self.COMMON_UPGRADE_COSTS.get(upgrade_name, []))
            
            display_name = "Flat Damage +1" if upgrade_name == 'flat_damage' else "Armor Pen +1"
            
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 280
            tooltip_height = 220
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Outer frame for shadow effect (gray for Common)
            outer_frame = tk.Frame(tooltip, background="#808080", relief=tk.FLAT, borderwidth=0)
            outer_frame.pack(padx=2, pady=2)
            
            # Inner frame
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF", relief=tk.FLAT, borderwidth=0)
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            # Title with icon
            title_frame = tk.Frame(content_frame, background="#FFFFFF")
            title_frame.pack(anchor=tk.W)
            
            # Try to load common fragment icon
            try:
                icon_path = Path(__file__).parent.parent / "sprites" / "archaeology" / "fragmentcommon.png"
                if icon_path.exists():
                    icon_image = Image.open(icon_path)
                    icon_image = icon_image.resize((16, 16), Image.Resampling.LANCZOS)
                    tooltip.icon_photo = ImageTk.PhotoImage(icon_image)
                    tk.Label(title_frame, image=tooltip.icon_photo, background="#FFFFFF").pack(side=tk.LEFT, padx=(0, 5))
            except:
                pass
            
            tk.Label(title_frame, text=f"Common Upgrade: {display_name}", 
                    font=("Arial", 10, "bold"), foreground="#808080", 
                    background="#FFFFFF").pack(side=tk.LEFT)
            
            # Effect
            effect_text = "+1 Flat Damage per level" if upgrade_name == 'flat_damage' else "+1 Armor Penetration per level"
            tk.Label(content_frame, text=f"Effect: {effect_text}", 
                    font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W, pady=(2, 0))
            
            # Level
            tk.Label(content_frame, text=f"Level: {current_level} / {max_level}", 
                    font=("Arial", 9, "bold"), background="#FFFFFF").pack(anchor=tk.W, pady=(5, 0))
            
            # Next cost with icon
            if next_cost:
                cost_frame = tk.Frame(content_frame, background="#FFFFFF")
                cost_frame.pack(anchor=tk.W)
                tk.Label(cost_frame, text=f"Next Level: {next_cost:.2f}", 
                        font=("Arial", 9), foreground="#2E7D32", 
                        background="#FFFFFF").pack(side=tk.LEFT)
                try:
                    if hasattr(tooltip, 'icon_photo'):
                        tk.Label(cost_frame, image=tooltip.icon_photo, background="#FFFFFF").pack(side=tk.LEFT, padx=(3, 0))
                except:
                    tk.Label(cost_frame, text=" Common", font=("Arial", 9), foreground="#2E7D32", 
                            background="#FFFFFF").pack(side=tk.LEFT)
            else:
                tk.Label(content_frame, text="MAX LEVEL", 
                        font=("Arial", 9, "bold"), foreground="#C73E1D", 
                        background="#FFFFFF").pack(anchor=tk.W)
            
            # Total spent with icon
            total_frame = tk.Frame(content_frame, background="#FFFFFF")
            total_frame.pack(anchor=tk.W, pady=(2, 0))
            tk.Label(total_frame, text=f"Total Spent: {total_spent:.2f}", 
                    font=("Arial", 9), foreground="gray", 
                    background="#FFFFFF").pack(side=tk.LEFT)
            try:
                if hasattr(tooltip, 'icon_photo'):
                    tk.Label(total_frame, image=tooltip.icon_photo, background="#FFFFFF").pack(side=tk.LEFT, padx=(3, 0))
            except:
                tk.Label(total_frame, text=" Common", font=("Arial", 9), foreground="gray", 
                        background="#FFFFFF").pack(side=tk.LEFT)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _create_gem_upgrade_tooltip(self, widget, upgrade_name, info, max_level):
        """Creates a tooltip showing gem upgrade details and costs"""
        def on_enter(event):
            current_level = self.gem_upgrades[upgrade_name]
            next_cost = self.get_gem_upgrade_cost(upgrade_name)
            total_spent = self.get_total_gem_cost(upgrade_name)
            
            # Determine currency type (arch_xp uses Common, others use Gems)
            is_common_currency = (upgrade_name == 'arch_xp')
            currency_name = "Common" if is_common_currency else "Gems"
            border_color = "#808080" if is_common_currency else "#9932CC"  # Gray for Common, Purple for Gems
            
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 280
            tooltip_height = 200
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Outer frame for shadow effect
            outer_frame = tk.Frame(tooltip, background=border_color, relief=tk.FLAT, borderwidth=0)
            outer_frame.pack(padx=2, pady=2)
            
            # Inner frame
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF", relief=tk.FLAT, borderwidth=0)
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            # Title
            title_prefix = "Common Upgrade" if is_common_currency else "Gem Upgrade"
            display_name = "Arch XP" if upgrade_name == 'arch_xp' else upgrade_name.capitalize()
            tk.Label(content_frame, text=f"{title_prefix}: {display_name}", 
                    font=("Arial", 10, "bold"), foreground=border_color, 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            # Effect
            tk.Label(content_frame, text=f"Effect: {info}", 
                    font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W, pady=(2, 0))
            
            # Level
            tk.Label(content_frame, text=f"Level: {current_level} / {max_level}", 
                    font=("Arial", 9, "bold"), background="#FFFFFF").pack(anchor=tk.W, pady=(5, 0))
            
            # Next cost
            if next_cost:
                if is_common_currency:
                    cost_text = f"Next Level: {next_cost:.2f} {currency_name}"
                else:
                    cost_text = f"Next Level: {next_cost} {currency_name}"
                tk.Label(content_frame, text=cost_text, 
                        font=("Arial", 9), foreground="#2E7D32", 
                        background="#FFFFFF").pack(anchor=tk.W)
            else:
                tk.Label(content_frame, text="MAX LEVEL", 
                        font=("Arial", 9, "bold"), foreground="#C73E1D", 
                        background="#FFFFFF").pack(anchor=tk.W)
            
            # Total spent
            if is_common_currency:
                total_text = f"Total Spent: {total_spent:.2f} {currency_name}"
            else:
                total_text = f"Total Spent: {total_spent} {currency_name}"
            tk.Label(content_frame, text=total_text, 
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
            
            tooltip_width = 320
            tooltip_height = 420
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
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
    
    def _create_stats_help_tooltip(self, widget):
        """Creates a tooltip explaining all stats in detail"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 380
            tooltip_height = 520
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
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
            tk.Label(content_frame, text="Stats & Skills Explained", 
                    font=("Arial", 11, "bold"), foreground="#1976D2", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()
            
            # Combat Stats
            tk.Label(content_frame, text="Combat Stats:", 
                    font=("Arial", 9, "bold"), foreground="#C73E1D", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            combat_lines = [
                "• Damage: Base 10 + Flat Dmg upgrade + STR×1",
                "    → Total = Flat × (1 + STR×1% bonus)",
                "• Armor Pen: Reduces effective block armor",
                "    → PER gives +2 Armor Pen per point",
                "• Stamina: Base 100 + AGI×5 + Gem upgrade×2",
                "    → Determines blocks you can hit per run",
                "• Crit %: AGI×1% + LUK×2%",
                "• Crit Dmg: Base 1.5× + STR×0.03×",
                "• One-Hit %: LUK×0.04% (instant kill chance)",
            ]
            for line in combat_lines:
                tk.Label(content_frame, text=line, font=("Arial", 8), 
                        background="#FFFFFF", anchor=tk.W).pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()
            
            # Mod Chances
            tk.Label(content_frame, text="Mod Chances (per block hit):", 
                    font=("Arial", 9, "bold"), foreground="#9932CC", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            mod_lines = [
                "• Exp Mod: INT×0.3% + LUK×0.2% + Gem×0.05%",
                "    → Triggers 3×-5× XP for that block (avg 4×)",
                "• Loot Mod: PER×0.3% + LUK×0.2% + Gem×0.05%",
                "    → Triggers 2×-5× Fragments (avg 3.5×)",
                "• Speed Mod: AGI×0.2% + LUK×0.2%",
                "    → 2× attack speed for 10-110 hits (QoL only)",
                "• Stamina Mod: LUK×0.2% + Gem×0.05%",
                "    → Grants +3 to +10 Stamina (avg +6.5)",
            ]
            for line in mod_lines:
                tk.Label(content_frame, text=line, font=("Arial", 8), 
                        background="#FFFFFF", anchor=tk.W).pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()
            
            # Multipliers
            tk.Label(content_frame, text="Multipliers:", 
                    font=("Arial", 9, "bold"), foreground="#2E7D32", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            mult_lines = [
                "• XP Mult: Base 1.0× + INT×5% + Gem×5%",
                "    → Applied to all XP gained",
                "• Frag Mult: Base 1.0× + PER×4% + Gem×2%",
                "    → Applied to fragment drops",
                "• Arch XP: Common upgrade, +2% per level",
                "    → Speeds up leveling (not floors/run)",
            ]
            for line in mult_lines:
                tk.Label(content_frame, text=line, font=("Arial", 8), 
                        background="#FFFFFF", anchor=tk.W).pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()
            
            # Skill Summary
            tk.Label(content_frame, text="Skill Point Summary:", 
                    font=("Arial", 9, "bold"), foreground="#1976D2", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            skill_lines = [
                "• STR: +1 Flat Dmg, +1% Dmg, +3% Crit Dmg",
                "• AGI: +5 Stamina, +1% Crit, +0.2% Speed Mod",
                "• INT: +5% XP Mult, +0.3% Exp Mod",
                "• PER: +4% Frag Mult, +0.3% Loot Mod, +2 Armor Pen",
                "• LUK: +2% Crit, +0.2% ALL Mods, +0.04% One-Hit",
            ]
            for line in skill_lines:
                tk.Label(content_frame, text=line, font=("Arial", 8), 
                        background="#FFFFFF", anchor=tk.W).pack(anchor=tk.W)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _create_skill_tooltip(self, widget, skill_name):
        """Creates a tooltip explaining what a specific skill does"""
        # Detailed skill descriptions
        skill_details = {
            'strength': {
                'title': 'Strength (STR)',
                'color': '#C73E1D',
                'bonuses': [
                    ('+1 Flat Damage', 'Added to base damage before % bonus'),
                    ('+1% Damage Bonus', 'Multiplies total flat damage'),
                    ('+3% Crit Damage', 'Added to crit multiplier (base 1.5×)'),
                ],
                'example': 'At 10 STR: +10 flat dmg, +10% dmg bonus, +30% crit dmg',
                'tip': 'Best for: Raw damage output. Scales well with flat damage upgrades.',
            },
            'agility': {
                'title': 'Agility (AGI)',
                'color': '#2E7D32',
                'bonuses': [
                    ('+5 Max Stamina', 'More hits per run = more blocks'),
                    ('+1% Crit Chance', 'Chance to deal crit damage'),
                    ('+0.2% Speed Mod Chance', 'Per block: 2× attack speed for 10-110 hits'),
                ],
                'example': 'At 10 AGI: +50 stamina, +10% crit, +2% speed mod',
                'tip': 'Best for: Longer runs. Speed Mod is QoL only (no extra floors).',
            },
            'intellect': {
                'title': 'Intellect (INT)',
                'color': '#1976D2',
                'bonuses': [
                    ('+5% XP Multiplier', 'Applied to all XP gained from blocks'),
                    ('+0.3% Exp Mod Chance', 'Per block: 3×-5× XP (avg 4×) when triggered'),
                ],
                'example': 'At 10 INT: +50% XP mult, +3% exp mod chance',
                'tip': 'Best for: Faster leveling. Does NOT improve floors/run directly.',
            },
            'perception': {
                'title': 'Perception (PER)',
                'color': '#9932CC',
                'bonuses': [
                    ('+4% Fragment Multiplier', 'Applied to all fragment drops'),
                    ('+0.3% Loot Mod Chance', 'Per block: 2×-5× fragments (avg 3.5×)'),
                    ('+2 Armor Penetration', 'Reduces effective block armor'),
                ],
                'example': 'At 10 PER: +40% frags, +3% loot mod, +20 armor pen',
                'tip': 'Best for: Fragment farming AND damage vs armored blocks.',
            },
            'luck': {
                'title': 'Luck (LUK)',
                'color': '#FF6F00',
                'bonuses': [
                    ('+2% Crit Chance', 'Double the crit chance of AGI!'),
                    ('+0.2% ALL Mod Chances', 'Adds to Exp, Loot, Speed, AND Stamina mods'),
                    ('+0.04% One-Hit Chance', 'Instant kill any block (ignores HP/armor)'),
                ],
                'example': 'At 10 LUK: +20% crit, +2% all mods, +0.4% one-hit',
                'tip': 'Best for: Universal boost. One-hit is small but powerful.',
            },
        }
        
        def on_enter(event):
            details = skill_details.get(skill_name, {})
            if not details:
                return
            
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 320
            tooltip_height = 200
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Outer frame for shadow effect
            outer_frame = tk.Frame(tooltip, background=details['color'], relief=tk.FLAT, borderwidth=0)
            outer_frame.pack(padx=2, pady=2)
            
            # Inner frame
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF", relief=tk.FLAT, borderwidth=0)
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            # Title
            tk.Label(content_frame, text=details['title'], 
                    font=("Arial", 10, "bold"), foreground=details['color'], 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()
            
            # Bonuses per point
            tk.Label(content_frame, text="Per Skill Point:", 
                    font=("Arial", 9, "bold"), background="#FFFFFF").pack(anchor=tk.W)
            
            for bonus, desc in details['bonuses']:
                bonus_frame = tk.Frame(content_frame, background="#FFFFFF")
                bonus_frame.pack(anchor=tk.W, fill=tk.X)
                tk.Label(bonus_frame, text=f"• {bonus}", font=("Arial", 9, "bold"), 
                        foreground=details['color'], background="#FFFFFF").pack(side=tk.LEFT)
                tk.Label(content_frame, text=f"    {desc}", font=("Arial", 8), 
                        foreground="#555555", background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()
            
            # Example
            tk.Label(content_frame, text=details['example'], 
                    font=("Arial", 8, "italic"), foreground="#555555", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()
            
            # Tip
            tk.Label(content_frame, text=details['tip'], 
                    font=("Arial", 8, "bold"), foreground="#2E7D32", 
                    background="#FFFFFF", wraplength=280, justify=tk.LEFT).pack(anchor=tk.W)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def create_results_column(self, parent):
        """Right column: Results, spawn chart, breakpoints, and forecast - scrollable"""
        # Outer frame for the column
        col_outer = tk.Frame(parent, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        col_outer.grid(row=0, column=2, sticky="nsew", padx=(2, 0), pady=0)
        
        # Create canvas with scrollbar for scrollable content
        canvas = tk.Canvas(col_outer, background="#FFF3E0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(col_outer, orient="vertical", command=canvas.yview)
        
        # Scrollable frame inside canvas
        col_frame = tk.Frame(canvas, background="#FFF3E0")
        
        # Configure scrolling
        col_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=col_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Store canvas reference for width updates
        self.results_canvas = canvas
        self.results_inner_frame = col_frame
        
        # === TOP ROW: Run Statistics + Spawn Chart side by side ===
        top_row = tk.Frame(col_frame, background="#FFF3E0")
        top_row.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Left: Run Statistics
        stats_frame = tk.Frame(top_row, background="#FFF3E0")
        stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(stats_frame, text="Run Statistics", font=("Arial", 10, "bold"), 
                background="#FFF3E0").pack(anchor=tk.W)
        
        results_grid = tk.Frame(stats_frame, background="#FFF3E0")
        results_grid.pack(fill=tk.X, pady=2)
        
        # Floors per run - PRIMARY
        tk.Label(results_grid, text="Floors/Run:", font=("Arial", 9, "bold"), 
                background="#FFF3E0").grid(row=0, column=0, sticky=tk.W, pady=1)
        self.floors_per_run_label = tk.Label(results_grid, text="—", 
                                             font=("Arial", 12, "bold"), 
                                             background="#FFF3E0", foreground="#2E7D32")
        self.floors_per_run_label.grid(row=0, column=1, sticky=tk.E, pady=1)
        
        # Blocks per run
        tk.Label(results_grid, text="Blocks/Run:", font=("Arial", 8), 
                background="#FFF3E0").grid(row=1, column=0, sticky=tk.W, pady=1)
        self.blocks_per_run_label = tk.Label(results_grid, text="—", 
                                             font=("Arial", 9, "bold"), 
                                             background="#FFF3E0", foreground="#1976D2")
        self.blocks_per_run_label.grid(row=1, column=1, sticky=tk.E, pady=1)
        
        # Avg hits
        tk.Label(results_grid, text="Avg Hits:", font=("Arial", 8), 
                background="#FFF3E0").grid(row=2, column=0, sticky=tk.W, pady=1)
        self.avg_hits_label = tk.Label(results_grid, text="—", 
                                       font=("Arial", 9, "bold"), 
                                       background="#FFF3E0", foreground="#1976D2")
        self.avg_hits_label.grid(row=2, column=1, sticky=tk.E, pady=1)
        
        # Effective damage
        tk.Label(results_grid, text="Eff Dmg:", font=("Arial", 8), 
                background="#FFF3E0").grid(row=3, column=0, sticky=tk.W, pady=1)
        self.eff_dmg_label = tk.Label(results_grid, text="—", 
                                      font=("Arial", 9, "bold"), 
                                      background="#FFF3E0", foreground="#C73E1D")
        self.eff_dmg_label.grid(row=3, column=1, sticky=tk.E, pady=1)
        
        # Right: Spawn distribution chart
        chart_frame = tk.Frame(top_row, background="#FFF3E0")
        chart_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        tk.Label(chart_frame, text="Spawn Distribution", font=("Arial", 9, "bold"), 
                background="#FFF3E0").pack()
        
        self.chart_canvas = tk.Canvas(chart_frame, width=180, height=100, 
                                      background="#FFFFFF", highlightthickness=1,
                                      highlightbackground="#CCCCCC")
        self.chart_canvas.pack()
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # === SECOND ROW: Avg Block Stats (compact) ===
        avg_stats_header = tk.Frame(col_frame, background="#FFF3E0")
        avg_stats_header.pack(fill=tk.X, padx=5)
        tk.Label(avg_stats_header, text="Avg Block Stats", font=("Arial", 9, "bold"), 
                background="#FFF3E0").pack(side=tk.LEFT)
        
        avg_stats_grid = tk.Frame(col_frame, background="#FFF3E0")
        avg_stats_grid.pack(fill=tk.X, padx=5, pady=2)
        
        # Row 1: HP and Armor
        tk.Label(avg_stats_grid, text="HP:", font=("Arial", 8), 
                background="#FFF3E0").grid(row=0, column=0, sticky=tk.W)
        self.avg_block_hp_label = tk.Label(avg_stats_grid, text="—", 
                                          font=("Arial", 8, "bold"), 
                                          background="#FFF3E0", foreground="#C73E1D", width=6)
        self.avg_block_hp_label.grid(row=0, column=1, sticky=tk.W)
        
        tk.Label(avg_stats_grid, text="Armor:", font=("Arial", 8), 
                background="#FFF3E0").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.avg_block_armor_label = tk.Label(avg_stats_grid, text="—", 
                                             font=("Arial", 8, "bold"), 
                                             background="#FFF3E0", foreground="#1976D2", width=4)
        self.avg_block_armor_label.grid(row=0, column=3, sticky=tk.W)
        
        tk.Label(avg_stats_grid, text="Pen needed:", font=("Arial", 8), 
                background="#FFF3E0", foreground="#555555").grid(row=0, column=4, sticky=tk.W, padx=(10, 0))
        self.armor_pen_hint_label = tk.Label(avg_stats_grid, text="—", 
                                            font=("Arial", 8, "bold"), 
                                            background="#FFF3E0", foreground="#555555")
        self.armor_pen_hint_label.grid(row=0, column=5, sticky=tk.W)
        
        # Row 2: XP and Fragment
        tk.Label(avg_stats_grid, text="XP:", font=("Arial", 8), 
                background="#FFF3E0").grid(row=1, column=0, sticky=tk.W)
        self.avg_block_xp_label = tk.Label(avg_stats_grid, text="—", 
                                          font=("Arial", 8, "bold"), 
                                          background="#FFF3E0", foreground="#2E7D32", width=6)
        self.avg_block_xp_label.grid(row=1, column=1, sticky=tk.W)
        
        tk.Label(avg_stats_grid, text="Frag:", font=("Arial", 8), 
                background="#FFF3E0").grid(row=1, column=2, sticky=tk.W, padx=(10, 0))
        self.avg_block_frag_label = tk.Label(avg_stats_grid, text="—", 
                                            font=("Arial", 8, "bold"), 
                                            background="#FFF3E0", foreground="#9932CC", width=6)
        self.avg_block_frag_label.grid(row=1, column=3, sticky=tk.W)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # === DAMAGE BREAKPOINTS SECTION ===
        breakpoint_header = tk.Frame(col_frame, background="#FFF3E0")
        breakpoint_header.pack(fill=tk.X, padx=5)
        
        tk.Label(breakpoint_header, text="Damage Breakpoints", font=("Arial", 10, "bold"), 
                background="#FFF3E0").pack(side=tk.LEFT)
        
        bp_help_label = tk.Label(breakpoint_header, text="?", font=("Arial", 9, "bold"), 
                                cursor="hand2", foreground="#C73E1D", background="#FFF3E0")
        bp_help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_breakpoint_help_tooltip(bp_help_label)
        
        # Best breakpoint recommendation
        self.best_bp_frame = tk.Frame(col_frame, background="#FFECB3", relief=tk.GROOVE, borderwidth=1)
        self.best_bp_frame.pack(fill=tk.X, padx=5, pady=(3, 2))
        
        best_bp_inner = tk.Frame(self.best_bp_frame, background="#FFECB3", padx=5, pady=2)
        best_bp_inner.pack(fill=tk.X)
        
        tk.Label(best_bp_inner, text="★ Best:", font=("Arial", 8, "bold"), 
                background="#FFECB3", foreground="#FF6F00").pack(side=tk.LEFT)
        
        self.best_bp_label = tk.Label(best_bp_inner, text="—", font=("Arial", 8), 
                                     background="#FFECB3", foreground="#333333")
        self.best_bp_label.pack(side=tk.LEFT, padx=(5, 0))
        
        best_bp_help = tk.Label(best_bp_inner, text="?", font=("Arial", 8, "bold"), 
                               cursor="hand2", foreground="#FF6F00", background="#FFECB3")
        best_bp_help.pack(side=tk.RIGHT)
        self._create_best_bp_help_tooltip(best_bp_help)
        
        # Container for breakpoint rows
        self.bp_container = tk.Frame(col_frame, background="#FFF3E0")
        self.bp_container.pack(fill=tk.X, padx=5, pady=3)
        
        self.breakpoint_labels = {}
        
        for block_type in BLOCK_TYPES:
            row_frame = tk.Frame(self.bp_container, background="#FFF3E0")
            
            color = self.BLOCK_COLORS.get(block_type, '#888888')
            
            name_label = tk.Label(row_frame, text=f"{block_type.capitalize()[:4]}:", 
                                 font=("Arial", 8, "bold"), foreground=color,
                                 background="#FFF3E0", width=5, anchor=tk.W)
            name_label.pack(side=tk.LEFT)
            
            impact_label = tk.Label(row_frame, text="", font=("Arial", 8), 
                                   background="#FFF3E0", foreground="#888888", width=7, anchor=tk.W)
            impact_label.pack(side=tk.LEFT)
            
            hits_label = tk.Label(row_frame, text="—", font=("Arial", 8), 
                                 background="#FFF3E0", width=9, anchor=tk.W)
            hits_label.pack(side=tk.LEFT)
            
            bp_info_label = tk.Label(row_frame, text="", font=("Arial", 8), 
                                    background="#FFF3E0", foreground="#555555",
                                    anchor=tk.W)
            bp_info_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Card buttons frame (right side)
            card_frame = tk.Frame(row_frame, background="#FFF3E0")
            card_frame.pack(side=tk.RIGHT, padx=(3, 0))
            
            # Card button (normal card: -10% HP, +10% XP)
            card_btn = tk.Label(card_frame, text="Card", font=("Arial", 7),
                               cursor="hand2", foreground="#888888", background="#FFF3E0",
                               padx=2)
            card_btn.pack(side=tk.LEFT)
            card_btn.bind("<Button-1>", lambda e, bt=block_type: self._toggle_card(bt, 1))
            
            # Gilded card button (gilded: -20% HP, +20% XP)
            gilded_btn = tk.Label(card_frame, text="Gilded", font=("Arial", 7),
                                 cursor="hand2", foreground="#888888", background="#FFF3E0",
                                 padx=2)
            gilded_btn.pack(side=tk.LEFT)
            gilded_btn.bind("<Button-1>", lambda e, bt=block_type: self._toggle_card(bt, 2))
            
            # Help icon for tooltip (instead of hovering on whole row)
            help_label = tk.Label(card_frame, text="?", font=("Arial", 7, "bold"),
                                 cursor="hand2", foreground="#1976D2", background="#FFF3E0",
                                 padx=2)
            help_label.pack(side=tk.LEFT)
            
            self.breakpoint_labels[block_type] = {
                'row': row_frame,
                'name': name_label,
                'impact': impact_label,
                'hits': hits_label,
                'bp_info': bp_info_label,
                'card_btn': card_btn,
                'gilded_btn': gilded_btn,
                'help_label': help_label,
                'tooltip_data': {}
            }
            
            # Bind tooltip to help label only, not whole row
            self._create_block_breakpoint_tooltip(help_label, block_type)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # === SKILL FORECAST SECTION ===
        forecast_header = tk.Frame(col_frame, background="#FFF3E0")
        forecast_header.pack(fill=tk.X, padx=5)
        
        tk.Label(forecast_header, text="Skill Forecast", font=("Arial", 10, "bold"), 
                background="#FFF3E0").pack(side=tk.LEFT)
        
        forecast_help_label = tk.Label(forecast_header, text="?", font=("Arial", 9, "bold"), 
                                      cursor="hand2", foreground="#1976D2", background="#FFF3E0")
        forecast_help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_forecast_help_tooltip(forecast_help_label)
        
        # Forecast table frame
        forecast_frame = tk.Frame(col_frame, background="#E3F2FD", relief=tk.GROOVE, borderwidth=1)
        forecast_frame.pack(fill=tk.X, padx=5, pady=(3, 5))
        
        forecast_inner = tk.Frame(forecast_frame, background="#E3F2FD", padx=8, pady=5)
        forecast_inner.pack(fill=tk.X)
        
        # Initialize forecast level variable (single row now)
        self.forecast_levels_1 = tk.IntVar(value=5)
        
        # Header row
        header_frame = tk.Frame(forecast_inner, background="#E3F2FD")
        header_frame.pack(fill=tk.X)
        
        tk.Label(header_frame, text="Levels", font=("Arial", 8, "bold"), 
                background="#E3F2FD", width=8, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(header_frame, text="Optimal Build", font=("Arial", 8, "bold"), 
                background="#E3F2FD", width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(3, 0))
        tk.Label(header_frame, text="Floors", font=("Arial", 8, "bold"), 
                background="#E3F2FD", width=5, anchor=tk.E).pack(side=tk.LEFT, padx=(3, 0))
        tk.Label(header_frame, text="Gain", font=("Arial", 8, "bold"), 
                background="#E3F2FD", anchor=tk.E).pack(side=tk.RIGHT)
        
        # === Single forecast row ===
        row_1_frame = tk.Frame(forecast_inner, background="#E3F2FD")
        row_1_frame.pack(fill=tk.X, pady=(3, 0))
        
        # Top: Level selector + build and stats
        row_1_top = tk.Frame(row_1_frame, background="#E3F2FD")
        row_1_top.pack(fill=tk.X)
        
        # Level adjuster with +/- buttons
        level_1_frame = tk.Frame(row_1_top, background="#E3F2FD")
        level_1_frame.pack(side=tk.LEFT)
        
        tk.Button(level_1_frame, text="-", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_forecast_level(1, -1)).pack(side=tk.LEFT)
        self.forecast_1_level_label = tk.Label(level_1_frame, text="+5", font=("Arial", 9, "bold"), 
                                              background="#E3F2FD", foreground="#1976D2", width=3)
        self.forecast_1_level_label.pack(side=tk.LEFT)
        tk.Button(level_1_frame, text="+", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_forecast_level(1, 1)).pack(side=tk.LEFT)
        
        self.forecast_1_dist_label = tk.Label(row_1_top, text="—", font=("Arial", 9), 
                                             background="#E3F2FD", width=10, anchor=tk.W)
        self.forecast_1_dist_label.pack(side=tk.LEFT, padx=(5, 0))
        self.forecast_1_floors_label = tk.Label(row_1_top, text="—", font=("Arial", 9, "bold"), 
                                               background="#E3F2FD", foreground="#2E7D32", 
                                               width=5, anchor=tk.E)
        self.forecast_1_floors_label.pack(side=tk.LEFT, padx=(3, 0))
        self.forecast_1_gain_label = tk.Label(row_1_top, text="—", font=("Arial", 9, "bold"), 
                                             background="#E3F2FD", foreground="#2E7D32", anchor=tk.E)
        self.forecast_1_gain_label.pack(side=tk.RIGHT)
        
        # Path for row 1
        row_1_path = tk.Frame(row_1_frame, background="#E8F5E9")
        row_1_path.pack(fill=tk.X, pady=(1, 0))
        
        tk.Label(row_1_path, text="    Path:", font=("Arial", 7), 
                background="#E8F5E9", foreground="#555555").pack(side=tk.LEFT)
        self.forecast_1_path_label = tk.Label(row_1_path, text="—", font=("Arial", 8), 
                                             background="#E8F5E9", foreground="#333333")
        self.forecast_1_path_label.pack(side=tk.LEFT, padx=(3, 0))
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # === BUDGET PLANNER SECTION ===
        budget_header = tk.Frame(col_frame, background="#FFF3E0")
        budget_header.pack(fill=tk.X, padx=5)
        
        tk.Label(budget_header, text="Skill Budget Planner", font=("Arial", 10, "bold"), 
                background="#FFF3E0").pack(side=tk.LEFT)
        
        budget_help_label = tk.Label(budget_header, text="?", font=("Arial", 9, "bold"), 
                                    cursor="hand2", foreground="#9932CC", background="#FFF3E0")
        budget_help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_budget_help_tooltip(budget_help_label)
        
        # Budget frame with purple theme
        budget_frame = tk.Frame(col_frame, background="#F3E5F5", relief=tk.GROOVE, borderwidth=1)
        budget_frame.pack(fill=tk.X, padx=5, pady=(3, 5))
        
        budget_inner = tk.Frame(budget_frame, background="#F3E5F5", padx=8, pady=5)
        budget_inner.pack(fill=tk.X)
        
        # Initialize budget variable
        self.budget_points = tk.IntVar(value=20)
        
        # Input row: Points selector
        input_row = tk.Frame(budget_inner, background="#F3E5F5")
        input_row.pack(fill=tk.X)
        
        tk.Label(input_row, text="Available Points:", font=("Arial", 9, "bold"), 
                background="#F3E5F5", foreground="#7B1FA2").pack(side=tk.LEFT)
        
        # Points adjuster with +/- buttons
        points_frame = tk.Frame(input_row, background="#F3E5F5")
        points_frame.pack(side=tk.LEFT, padx=(8, 0))
        
        tk.Button(points_frame, text="-5", width=2, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_budget(-5)).pack(side=tk.LEFT)
        tk.Button(points_frame, text="-", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_budget(-1)).pack(side=tk.LEFT)
        self.budget_points_label = tk.Label(points_frame, text="20", font=("Arial", 11, "bold"), 
                                           background="#F3E5F5", foreground="#7B1FA2", width=4)
        self.budget_points_label.pack(side=tk.LEFT)
        tk.Button(points_frame, text="+", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_budget(1)).pack(side=tk.LEFT)
        tk.Button(points_frame, text="+5", width=2, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_budget(5)).pack(side=tk.LEFT)
        
        # Header row for results
        header_row = tk.Frame(budget_inner, background="#F3E5F5")
        header_row.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(header_row, text="Distribution", font=("Arial", 8, "bold"), 
                background="#F3E5F5", width=14, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(header_row, text="Floors", font=("Arial", 8, "bold"), 
                background="#F3E5F5", width=5, anchor=tk.E).pack(side=tk.LEFT)
        tk.Label(header_row, text="XP/Run", font=("Arial", 8, "bold"), 
                background="#F3E5F5", width=7, anchor=tk.E).pack(side=tk.LEFT)
        tk.Label(header_row, text="Gain", font=("Arial", 8, "bold"), 
                background="#F3E5F5", anchor=tk.E).pack(side=tk.RIGHT)
        
        # Result row
        result_row = tk.Frame(budget_inner, background="#E1BEE7")
        result_row.pack(fill=tk.X, pady=(3, 0))
        
        result_inner = tk.Frame(result_row, background="#E1BEE7", padx=5, pady=4)
        result_inner.pack(fill=tk.X)
        
        self.budget_dist_label = tk.Label(result_inner, text="—", font=("Arial", 10, "bold"), 
                                         background="#E1BEE7", foreground="#4A148C", 
                                         width=14, anchor=tk.W)
        self.budget_dist_label.pack(side=tk.LEFT)
        self.budget_floors_label = tk.Label(result_inner, text="—", font=("Arial", 10, "bold"), 
                                           background="#E1BEE7", foreground="#2E7D32", 
                                           width=5, anchor=tk.E)
        self.budget_floors_label.pack(side=tk.LEFT)
        self.budget_xp_label = tk.Label(result_inner, text="—", font=("Arial", 10, "bold"), 
                                       background="#E1BEE7", foreground="#00838F", 
                                       width=7, anchor=tk.E)
        self.budget_xp_label.pack(side=tk.LEFT)
        self.budget_gain_label = tk.Label(result_inner, text="—", font=("Arial", 10, "bold"), 
                                         background="#E1BEE7", foreground="#2E7D32", anchor=tk.E)
        self.budget_gain_label.pack(side=tk.RIGHT)
        
        # Detailed breakdown row
        breakdown_row = tk.Frame(budget_inner, background="#F3E5F5")
        breakdown_row.pack(fill=tk.X, pady=(3, 0))
        
        tk.Label(breakdown_row, text="Details:", font=("Arial", 7), 
                background="#F3E5F5", foreground="#555555").pack(side=tk.LEFT)
        self.budget_breakdown_label = tk.Label(breakdown_row, text="—", font=("Arial", 8), 
                                              background="#F3E5F5", foreground="#333333")
        self.budget_breakdown_label.pack(side=tk.LEFT, padx=(3, 0))
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # === XP BUDGET PLANNER SECTION ===
        xp_budget_header = tk.Frame(col_frame, background="#E0F7FA")
        xp_budget_header.pack(fill=tk.X, padx=5)
        
        tk.Label(xp_budget_header, text="XP/h Budget Planner", font=("Arial", 10, "bold"), 
                background="#E0F7FA").pack(side=tk.LEFT)
        
        xp_budget_help_label = tk.Label(xp_budget_header, text="?", font=("Arial", 9, "bold"), 
                                       cursor="hand2", foreground="#00838F", background="#E0F7FA")
        xp_budget_help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_xp_budget_help_tooltip(xp_budget_help_label)
        
        # XP Budget frame with cyan/teal theme
        xp_budget_frame = tk.Frame(col_frame, background="#B2EBF2", relief=tk.GROOVE, borderwidth=1)
        xp_budget_frame.pack(fill=tk.X, padx=5, pady=(3, 5))
        
        xp_budget_inner = tk.Frame(xp_budget_frame, background="#B2EBF2", padx=8, pady=5)
        xp_budget_inner.pack(fill=tk.X)
        
        # Initialize XP budget variable
        self.xp_budget_points = tk.IntVar(value=20)
        
        # Input row: Points selector
        xp_input_row = tk.Frame(xp_budget_inner, background="#B2EBF2")
        xp_input_row.pack(fill=tk.X)
        
        tk.Label(xp_input_row, text="Available Points:", font=("Arial", 9, "bold"), 
                background="#B2EBF2", foreground="#00695C").pack(side=tk.LEFT)
        
        # Points adjuster with +/- buttons
        xp_points_frame = tk.Frame(xp_input_row, background="#B2EBF2")
        xp_points_frame.pack(side=tk.LEFT, padx=(8, 0))
        
        tk.Button(xp_points_frame, text="-5", width=2, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_xp_budget(-5)).pack(side=tk.LEFT)
        tk.Button(xp_points_frame, text="-", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_xp_budget(-1)).pack(side=tk.LEFT)
        self.xp_budget_points_label = tk.Label(xp_points_frame, text="20", font=("Arial", 11, "bold"), 
                                              background="#B2EBF2", foreground="#00695C", width=4)
        self.xp_budget_points_label.pack(side=tk.LEFT)
        tk.Button(xp_points_frame, text="+", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_xp_budget(1)).pack(side=tk.LEFT)
        tk.Button(xp_points_frame, text="+5", width=2, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_xp_budget(5)).pack(side=tk.LEFT)
        
        # Header row for results
        xp_header_row = tk.Frame(xp_budget_inner, background="#B2EBF2")
        xp_header_row.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(xp_header_row, text="Distribution", font=("Arial", 8, "bold"), 
                background="#B2EBF2", width=14, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(xp_header_row, text="Floors", font=("Arial", 8, "bold"), 
                background="#B2EBF2", width=5, anchor=tk.E).pack(side=tk.LEFT)
        tk.Label(xp_header_row, text="XP/Run", font=("Arial", 8, "bold"), 
                background="#B2EBF2", width=7, anchor=tk.E).pack(side=tk.LEFT)
        tk.Label(xp_header_row, text="Gain", font=("Arial", 8, "bold"), 
                background="#B2EBF2", anchor=tk.E).pack(side=tk.RIGHT)
        
        # Result row
        xp_result_row = tk.Frame(xp_budget_inner, background="#80DEEA")
        xp_result_row.pack(fill=tk.X, pady=(3, 0))
        
        xp_result_inner = tk.Frame(xp_result_row, background="#80DEEA", padx=5, pady=4)
        xp_result_inner.pack(fill=tk.X)
        
        self.xp_budget_dist_label = tk.Label(xp_result_inner, text="—", font=("Arial", 10, "bold"), 
                                            background="#80DEEA", foreground="#006064", 
                                            width=14, anchor=tk.W)
        self.xp_budget_dist_label.pack(side=tk.LEFT)
        self.xp_budget_floors_label = tk.Label(xp_result_inner, text="—", font=("Arial", 10, "bold"), 
                                              background="#80DEEA", foreground="#7B1FA2", 
                                              width=5, anchor=tk.E)
        self.xp_budget_floors_label.pack(side=tk.LEFT)
        self.xp_budget_xp_label = tk.Label(xp_result_inner, text="—", font=("Arial", 10, "bold"), 
                                          background="#80DEEA", foreground="#2E7D32", 
                                          width=7, anchor=tk.E)
        self.xp_budget_xp_label.pack(side=tk.LEFT)
        self.xp_budget_gain_label = tk.Label(xp_result_inner, text="—", font=("Arial", 10, "bold"), 
                                            background="#80DEEA", foreground="#2E7D32", anchor=tk.E)
        self.xp_budget_gain_label.pack(side=tk.RIGHT)
        
        # Detailed breakdown row
        xp_breakdown_row = tk.Frame(xp_budget_inner, background="#B2EBF2")
        xp_breakdown_row.pack(fill=tk.X, pady=(3, 0))
        
        tk.Label(xp_breakdown_row, text="Details:", font=("Arial", 7), 
                background="#B2EBF2", foreground="#555555").pack(side=tk.LEFT)
        self.xp_budget_breakdown_label = tk.Label(xp_breakdown_row, text="—", font=("Arial", 8), 
                                                 background="#B2EBF2", foreground="#333333")
        self.xp_budget_breakdown_label.pack(side=tk.LEFT, padx=(3, 0))
    
    def _adjust_xp_budget(self, delta: int):
        """Adjust the XP budget points and recalculate"""
        new_val = max(1, min(100, self.xp_budget_points.get() + delta))
        self.xp_budget_points.set(new_val)
        self.xp_budget_points_label.config(text=str(new_val))
        self.update_xp_budget_display()
    
    def _create_xp_budget_help_tooltip(self, widget):
        """Creates a tooltip explaining the XP Budget Planner feature"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 340
            tooltip_height = 300
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#00838F", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text="XP/h Budget Planner", 
                    font=("Arial", 10, "bold"), foreground="#00838F", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            lines = [
                "",
                "Optimize for MAXIMUM XP per hour.",
                "",
                "Unlike the Floors/Run planner (above), this",
                "values Intellect highly because:",
                "  - +5% XP multiplier per point",
                "  - +0.3% Exp Mod chance (avg 4x XP)",
                "",
                "Use this when your goal is to level up",
                "as fast as possible, even if you clear",
                "fewer floors per run.",
                "",
                "XP/h = Floors/Run x XP/Floor x XP Mults",
                "",
                "Legend: S=Str, A=Agi, I=Int, P=Per, L=Luck",
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
    
    def _adjust_budget(self, delta: int):
        """Adjust the budget points and recalculate"""
        new_val = max(1, min(100, self.budget_points.get() + delta))
        self.budget_points.set(new_val)
        self.budget_points_label.config(text=str(new_val))
        self.update_budget_display()
    
    def _create_budget_help_tooltip(self, widget):
        """Creates a tooltip explaining the Budget Planner feature"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 320
            tooltip_height = 320
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#7B1FA2", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content_frame.pack()
            
            tk.Label(content_frame, text="Skill Budget Planner", 
                    font=("Arial", 10, "bold"), foreground="#7B1FA2", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            lines = [
                "",
                "Plan how to spend a fixed pool of points.",
                "",
                "Unlike Forecast (which adds to current stats),",
                "Budget Planner helps when you have unspent",
                "points and want to distribute them optimally.",
                "",
                "Use case: You saved up 20 skill points and",
                "want to know the best way to spend them all.",
                "",
                "Since you're spending them all at once,",
                "the order doesn't matter - only the final",
                "distribution counts.",
                "",
                "Legend: S=Str, A=Agi, I=Int, P=Per, L=Luck",
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
    
    def _adjust_forecast_level(self, row: int, delta: int):
        """Adjust the forecast level and recalculate"""
        new_val = max(1, min(20, self.forecast_levels_1.get() + delta))
        self.forecast_levels_1.set(new_val)
        self.forecast_1_level_label.config(text=f"+{new_val}")
        self.update_forecast_display()
    
    def _create_forecast_help_tooltip(self, widget):
        """Creates a tooltip explaining the Skill Forecast feature"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 340
            tooltip_height = 380
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
            
            tk.Label(content_frame, text="Skill Forecast", 
                    font=("Arial", 10, "bold"), foreground="#1976D2", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            lines = [
                "",
                "Plans ahead instead of greedy optimization!",
                "",
                "The greedy approach (Best Next Point) picks",
                "the skill that gives the best immediate gain.",
                "But this can miss important breakpoints.",
                "",
                "Forecast calculates the OPTIMAL distribution",
                "for the next 5 or 10 skill points combined.",
                "",
                "Example:",
                "  Greedy: +3A +2P = +8% (picks Agi each time)",
                "  Optimal: +4S +1A = +15% (hits STR breakpoint!)",
                "",
                "Legend: S=Str, A=Agi, I=Int, P=Per, L=Luck",
                "",
                "'Next 5' shows the optimal order to allocate",
                "your next 5 skill points.",
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
    
    def _toggle_card(self, block_type, card_level):
        """Toggle card status for a block type. 
        card_level: 1 = normal card, 2 = gilded card
        Clicking the same card again removes it.
        """
        current = self.block_cards.get(block_type, 0)
        if current == card_level:
            # Toggle off
            self.block_cards[block_type] = 0
        else:
            # Set to this card level
            self.block_cards[block_type] = card_level
        
        # Update card button visuals
        self._update_card_buttons()
        
        # Recalculate everything
        self.update_display()
    
    def _update_card_buttons(self):
        """Update the visual state of all card buttons based on current card levels"""
        for block_type, labels in self.breakpoint_labels.items():
            card_level = self.block_cards.get(block_type, 0)
            card_btn = labels.get('card_btn')
            gilded_btn = labels.get('gilded_btn')
            
            if card_btn:
                if card_level == 1:
                    card_btn.config(foreground="#FFFFFF", background="#4CAF50")  # Active green
                else:
                    card_btn.config(foreground="#888888", background="#FFF3E0")  # Inactive
            
            if gilded_btn:
                if card_level == 2:
                    gilded_btn.config(foreground="#FFFFFF", background="#FFD700")  # Active gold
                else:
                    gilded_btn.config(foreground="#888888", background="#FFF3E0")  # Inactive
    
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
            
            # Title with card indicator
            card_level = data.get('card_level', 0)
            card_text = ""
            if card_level == 1:
                card_text = " [Card]"
            elif card_level == 2:
                card_text = " [Gilded]"
            
            tk.Label(content_frame, text=f"{block_type.capitalize()} Block{card_text}", 
                    font=("Arial", 10, "bold"), foreground=color, 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            # Block stats (show original and effective HP if card is active)
            base_hp = data.get('hp', '?')
            effective_hp = data.get('effective_hp', base_hp)
            
            if card_level > 0 and base_hp != effective_hp:
                hp_text = f"HP: {base_hp} → {effective_hp}  |  Armor: {data.get('armor', '?')}"
            else:
                hp_text = f"HP: {base_hp}  |  Armor: {data.get('armor', '?')}"
            
            tk.Label(content_frame, text=hp_text, 
                    font=("Arial", 9), foreground="#555555",
                    background="#FFFFFF").pack(anchor=tk.W, pady=(2, 5))
            
            # Current status
            tk.Label(content_frame, text=f"Your effective damage: {data.get('eff_dmg', '?')}", 
                    font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W)
            
            # Show both deterministic hits and avg hits with crits
            hits = data.get('hits', '?')
            avg_hits = data.get('avg_hits', hits)
            
            if isinstance(avg_hits, (int, float)) and isinstance(hits, (int, float)) and abs(avg_hits - hits) > 0.05:
                tk.Label(content_frame, text=f"Hits to kill: {hits} (avg: {avg_hits:.1f} with crits)", 
                        font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W)
            else:
                tk.Label(content_frame, text=f"Hits to kill: {hits}", 
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
                block_data.health, block_data.armor, stats, block_type
            )
            
            current_hits = bp['current_hits']
            avg_hits = bp['avg_hits']
            if current_hits == float('inf'):
                current_hits = 9999
            if avg_hits == float('inf'):
                avg_hits = 9999
            
            # Stamina impact uses avg_hits (accounts for crits) = spawn_rate * avg_hits * blocks_per_floor (15)
            stamina_impact = spawn_rate * avg_hits * self.BLOCKS_PER_FLOOR
            
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
                'avg_hits': avg_hits,
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
            avg_hits = bd['avg_hits']
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
            
            # Update card button states (colors based on active state, not row highlight)
            card_level = self.block_cards.get(block_type, 0)
            card_btn = labels.get('card_btn')
            gilded_btn = labels.get('gilded_btn')
            
            if card_btn:
                if card_level == 1:
                    card_btn.config(foreground="#FFFFFF", background="#4CAF50")  # Active green
                else:
                    card_btn.config(foreground="#888888", background=bg_color)  # Inactive
            
            if gilded_btn:
                if card_level == 2:
                    gilded_btn.config(foreground="#FFFFFF", background="#FFD700")  # Active gold
                else:
                    gilded_btn.config(foreground="#888888", background=bg_color)  # Inactive
            
            # Update help label background
            help_label = labels.get('help_label')
            if help_label:
                help_label.config(background=bg_color)
            
            # Update impact label
            labels['impact'].config(text=f"({stamina_impact:.1f})")
            
            # Format current hits - show both deterministic and avg with crits
            # Format: "3h (2.4)" where 3 is deterministic, 2.4 is avg with crits
            if current_hits >= 9999:
                labels['hits'].config(text="∞ hits", foreground="#C73E1D")
            elif current_hits == 1:
                labels['hits'].config(text="1h ✓", foreground="#2E7D32")
            else:
                # Show avg_hits in parentheses if different from current_hits
                if abs(avg_hits - current_hits) > 0.05:
                    labels['hits'].config(text=f"{current_hits:.0f}h ({avg_hits:.1f})", foreground="#1976D2")
                else:
                    labels['hits'].config(text=f"{current_hits:.0f}h", foreground="#1976D2")
            
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
            # Check if card is applied
            card_level = self.block_cards.get(block_type, 0)
            effective_hp = bp['block_hp']  # Already has card reduction applied
            
            labels['tooltip_data'] = {
                'hp': block_stats.health,
                'effective_hp': effective_hp,
                'card_level': card_level,
                'armor': block_stats.armor,
                'eff_dmg': bp['current_eff_dmg'],
                'hits': current_hits if current_hits < 9999 else "∞",
                'avg_hits': avg_hits if avg_hits < 9999 else "∞",
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
        
        # Chart layout - compact version (180x100)
        canvas_width = 180
        margin_left = 45
        margin_right = 5
        margin_top = 3
        bar_height = 14
        bar_spacing = 2
        chart_width = canvas_width - margin_left - margin_right
        
        y = margin_top
        for block_type in BLOCK_TYPES:
            rate = spawn_rates.get(block_type, 0)
            color = self.BLOCK_COLORS.get(block_type, '#888888')
            
            # Label on left (abbreviated)
            self.chart_canvas.create_text(
                margin_left - 3, y + bar_height/2,
                text=block_type.capitalize()[:4], anchor=tk.E,
                font=("Arial", 7), fill="#333333"
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
                pct_text = f"{rate*100:.0f}%"
                if bar_width > 25:
                    self.chart_canvas.create_text(
                        margin_left + bar_width - 2, y + bar_height/2,
                        text=pct_text, anchor=tk.E,
                        font=("Arial", 6, "bold"), fill="white"
                    )
                else:
                    self.chart_canvas.create_text(
                        margin_left + bar_width + 2, y + bar_height/2,
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
                    font=("Arial", 7), fill="#666666"
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
        # Update upgrade labels with level and next cost (with icon)
        self.upgrade_labels['flat_damage'].config(text=f"+{self.upgrade_flat_damage}")
        fd_cost = self.get_common_upgrade_cost('flat_damage')
        if hasattr(self, 'upgrade_cost_icon_labels'):
            if fd_cost:
                self.upgrade_cost_icon_labels['flat_damage'].config(text=f"({fd_cost:.1f})")
            else:
                self.upgrade_cost_icon_labels['flat_damage'].config(text="(MAX)", foreground="#C73E1D")
        
        self.upgrade_labels['armor_pen'].config(text=f"+{self.upgrade_armor_pen}")
        ap_cost = self.get_common_upgrade_cost('armor_pen')
        if hasattr(self, 'upgrade_cost_icon_labels'):
            if ap_cost:
                self.upgrade_cost_icon_labels['armor_pen'].config(text=f"({ap_cost:.1f})")
            else:
                self.upgrade_cost_icon_labels['armor_pen'].config(text="(MAX)", foreground="#C73E1D")
        
        # Update upgrade level labels in the middle column
        if hasattr(self, 'upgrade_level_labels'):
            self.upgrade_level_labels['flat_damage'].config(text=str(self.upgrade_flat_damage))
            self.upgrade_level_labels['armor_pen'].config(text=str(self.upgrade_armor_pen))
            # Color based on level
            for upgrade, label in self.upgrade_level_labels.items():
                level = self.upgrade_flat_damage if upgrade == 'flat_damage' else self.upgrade_armor_pen
                if level > 0:
                    label.config(foreground="#808080")
                else:
                    label.config(foreground="gray")
        
        # Update mod chances (show 2 decimal places since values are small, e.g. 0.20%)
        if hasattr(self, 'mod_labels'):
            self.mod_labels['exp_mod_chance'].config(text=f"{stats['exp_mod_chance']*100:.2f}%")
            self.mod_labels['loot_mod_chance'].config(text=f"{stats['loot_mod_chance']*100:.2f}%")
            self.mod_labels['speed_mod_chance'].config(text=f"{stats['speed_mod_chance']*100:.2f}%")
            self.mod_labels['stamina_mod_chance'].config(text=f"{stats['stamina_mod_chance']*100:.2f}%")
        
        # Update multipliers
        if hasattr(self, 'mult_labels'):
            self.mult_labels['xp_mult'].config(text=f"{stats['xp_mult']:.2f}x")
            self.mult_labels['fragment_mult'].config(text=f"{stats['fragment_mult']:.2f}x")
            self.mult_labels['arch_xp_mult'].config(text=f"{stats['arch_xp_mult']:.2f}x")
        
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
        
        # Update Arch XP upgrade (Common cost upgrade)
        if hasattr(self, 'arch_xp_level_label'):
            arch_xp_level = self.gem_upgrades.get('arch_xp', 0)
            max_level = self.GEM_UPGRADE_BONUSES['arch_xp']['max_level']
            self.arch_xp_level_label.config(text=f"{arch_xp_level}")
            if arch_xp_level >= max_level:
                self.arch_xp_level_label.config(foreground="#C73E1D")
            elif arch_xp_level > 0:
                self.arch_xp_level_label.config(foreground="#808080")
            else:
                self.arch_xp_level_label.config(foreground="gray")
            
            # Update cost label
            next_cost = self.get_gem_upgrade_cost('arch_xp')
            if next_cost:
                self.arch_xp_cost_label.config(text=f"({next_cost:.2f})")
            else:
                self.arch_xp_cost_label.config(text="(MAX)", foreground="#C73E1D")
        
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
            
            # Update cost efficiency label (%/Common)
            if hasattr(self, 'upgrade_cost_labels') and upgrade in self.upgrade_cost_labels:
                next_cost = self.get_common_upgrade_cost(upgrade)
                if next_cost and next_cost > 0 and improvement > 0:
                    cost_efficiency = improvement / next_cost
                    self.upgrade_cost_labels[upgrade].config(
                        text=f"({cost_efficiency:.2f}%/C)",
                        foreground="#666666"
                    )
                elif next_cost is None:
                    self.upgrade_cost_labels[upgrade].config(text="(MAX)", foreground="#C73E1D")
                else:
                    self.upgrade_cost_labels[upgrade].config(text="")
        
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
        
        # Update skill forecast
        self.update_forecast_display()
    
    def update_forecast_display(self):
        """Update the skill forecast table with optimal distribution (single row)"""
        if not hasattr(self, 'forecast_1_dist_label'):
            return
        
        abbrev = {'strength': 'S', 'agility': 'A', 'intellect': 'I', 'perception': 'P', 'luck': 'L'}
        
        # Get current forecast level
        levels_1 = self.forecast_levels_1.get()
        
        # Calculate forecast
        forecast_1 = self.calculate_forecast(levels_1)
        dist_1_str = self.format_distribution(forecast_1['distribution'])
        self.forecast_1_dist_label.config(text=dist_1_str)
        self.forecast_1_floors_label.config(text=f"{forecast_1['floors_per_run']:.2f}")
        self.forecast_1_gain_label.config(text=f"+{forecast_1['improvement_pct']:.1f}%")
        
        # Path
        if forecast_1['path']:
            path_1_str = ' → '.join(abbrev[s] for s in forecast_1['path'])
            self.forecast_1_path_label.config(text=path_1_str)
        else:
            self.forecast_1_path_label.config(text="—")
        
        # Update budget planner too
        self.update_budget_display()
    
    def update_budget_display(self):
        """Update the budget planner with optimal distribution for fixed points"""
        if not hasattr(self, 'budget_dist_label'):
            return
        
        budget = self.budget_points.get()
        
        # Calculate optimal distribution for the budget
        # This uses the same algorithm as forecast
        result = self.calculate_forecast(budget)
        
        # Also calculate XP for this distribution for comparison
        # Temporarily apply the distribution to calculate XP
        for skill, points in result['distribution'].items():
            self.skill_points[skill] += points
        xp_with_floors_build = self.calculate_xp_per_run(self.get_total_stats(), self.current_stage)
        for skill, points in result['distribution'].items():
            self.skill_points[skill] -= points
        
        # Format and display
        dist_str = self.format_distribution(result['distribution'])
        self.budget_dist_label.config(text=dist_str)
        self.budget_floors_label.config(text=f"{result['floors_per_run']:.2f}")
        self.budget_xp_label.config(text=f"{xp_with_floors_build:.2f}")
        self.budget_gain_label.config(text=f"+{result['improvement_pct']:.1f}%")
        
        # Detailed breakdown showing exact values
        abbrev = {'strength': 'STR', 'agility': 'AGI', 'intellect': 'INT', 'perception': 'PER', 'luck': 'LUK'}
        parts = []
        for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
            points = result['distribution'].get(skill, 0)
            if points > 0:
                current = self.skill_points[skill]
                parts.append(f"{abbrev[skill]}: {current} → {current + points}")
        
        breakdown = ', '.join(parts) if parts else "No changes"
        self.budget_breakdown_label.config(text=breakdown)
        
        # Update XP budget planner too
        self.update_xp_budget_display()
    
    def update_xp_budget_display(self):
        """Update the XP budget planner with optimal distribution for maximum XP"""
        if not hasattr(self, 'xp_budget_dist_label'):
            return
        
        budget = self.xp_budget_points.get()
        
        # Calculate optimal distribution for XP (not floors)
        result = self.calculate_xp_forecast(budget)
        
        # Also calculate floors for this distribution for comparison
        # Temporarily apply the distribution to calculate floors
        for skill, points in result['distribution'].items():
            self.skill_points[skill] += points
        floors_with_xp_build = self.calculate_floors_per_run(self.get_total_stats(), self.current_stage)
        for skill, points in result['distribution'].items():
            self.skill_points[skill] -= points
        
        # Format and display
        dist_str = self.format_distribution(result['distribution'])
        self.xp_budget_dist_label.config(text=dist_str)
        self.xp_budget_floors_label.config(text=f"{floors_with_xp_build:.2f}")
        self.xp_budget_xp_label.config(text=f"{result['xp_per_run']:.2f}")
        self.xp_budget_gain_label.config(text=f"+{result['improvement_pct']:.1f}%")
        
        # Detailed breakdown showing exact values
        abbrev = {'strength': 'STR', 'agility': 'AGI', 'intellect': 'INT', 'perception': 'PER', 'luck': 'LUK'}
        parts = []
        for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
            points = result['distribution'].get(skill, 0)
            if points > 0:
                current = self.skill_points[skill]
                parts.append(f"{abbrev[skill]}: {current} → {current + points}")
        
        breakdown = ', '.join(parts) if parts else "No changes"
        self.xp_budget_breakdown_label.config(text=breakdown)
    
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
