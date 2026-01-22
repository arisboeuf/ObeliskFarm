"""
Archaeology Skill Point Optimizer / Simulator

This module provides the GUI window for archaeology skill point optimization.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import json
import math
from PIL import Image, ImageTk

from .block_spawn_rates import get_block_mix_for_stage, get_stage_range_label, STAGE_RANGES, get_normalized_spawn_rates
from .block_stats import get_block_at_floor, get_block_mix_for_floor, BlockData, BLOCK_TYPES
from .upgrade_costs import get_upgrade_cost, get_total_cost, get_max_level
from .monte_carlo_crit import run_crit_analysis, MonteCarloCritSimulator, debug_single_run

import sys
import os
sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import calculate_tooltip_position, get_resource_path


def get_user_data_path() -> Path:
    """Get path for user data (saves) - persists outside of bundle."""
    if getattr(sys, 'frozen', False):
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        save_dir = Path(app_data) / 'ObeliskGemEV' / 'save'
    else:
        save_dir = Path(__file__).parent.parent / 'save'
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


# Save file path (in user data folder for persistence)
SAVE_DIR = get_user_data_path()
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
            'armor_pen_mult': 0.03,  # +3% armor pen multiplier per point
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
    
    # Flurry ability constants
    # +100% attack speed (QoL), +5 stamina on cast, 120s cooldown
    FLURRY_COOLDOWN = 120  # seconds
    FLURRY_STAMINA_BONUS = 5  # +5 stamina on cast (one time per activation)
    
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
    
    # Gem Upgrade bonuses per level (purchased with Gems, N/A = always unlocked)
    GEM_UPGRADE_BONUSES = {
        'stamina': {
            'max_stamina': 2,
            'stamina_mod_chance': 0.0005,  # +0.05%
            'max_level': 50,
            'stage_unlock': 0,  # N/A - always unlocked
        },
        'xp': {
            'xp_bonus': 0.05,  # +5%
            'exp_mod_chance': 0.0005,  # +0.05%
            'max_level': 25,
            'stage_unlock': 0,  # N/A - always unlocked
        },
        'fragment': {
            'fragment_gain': 0.02,  # +2%
            'loot_mod_chance': 0.0005,  # +0.05%
            'max_level': 25,
            'stage_unlock': 0,  # N/A - always unlocked
        },
        'arch_xp': {
            'arch_xp_bonus': 0.02,  # +2% Archaeology Exp
            'max_level': 25,
            'stage_unlock': 3,  # Unlocks at stage 3
        },
    }
    
    # Fragment upgrades with Stage to Unlock
    # Format: upgrade_key -> {bonuses, max_level, stage_unlock, cost_type, display_name}
    # cost_type: 'common', 'rare', 'epic', 'legendary', 'mythic'
    FRAGMENT_UPGRADES = {
        # Common Fragment Upgrades (gray)
        'flat_damage_c1': {
            'flat_damage': 1,
            'max_level': 25,
            'stage_unlock': 0,  # N/A
            'cost_type': 'common',
            'display_name': 'Flat Dmg +1',
        },
        'armor_pen_c1': {
            'armor_pen': 1,
            'max_level': 25,
            'stage_unlock': 2,
            'cost_type': 'common',
            'display_name': 'Armor Pen +1',
        },
        'arch_xp_c1': {
            'arch_xp_bonus': 0.02,  # +2%
            'max_level': 25,
            'stage_unlock': 3,
            'cost_type': 'common',
            'display_name': 'Exp Gain +2%',
        },
        'crit_c1': {
            'crit_chance': 0.0025,  # +0.25%
            'crit_damage': 0.01,  # +1%
            'max_level': 25,
            'stage_unlock': 4,
            'cost_type': 'common',
            'display_name': 'Crit +0.25%/+1%',
        },
        'str_skill_buff': {
            'flat_damage_skill': 0.2,  # +0.2 flat dmg from skill
            'percent_damage_skill': 0.001,  # +0.1% dmg from skill
            'max_level': 5,
            'stage_unlock': 13,
            'cost_type': 'common',
            'display_name': 'STR Buff',
        },
        'polychrome_bonus': {
            'polychrome_bonus': 0.15,  # +15%
            'max_level': 1,
            'stage_unlock': 34,
            'cost_type': 'common',
            'display_name': 'Polychrome +15%',
        },
        
        # Rare Fragment Upgrades (blue)
        'stamina_r1': {
            'max_stamina': 2,
            'stamina_mod_chance': 0.0005,  # +0.05%
            'max_level': 20,
            'stage_unlock': 5,
            'cost_type': 'rare',
            'display_name': 'Stam +2/+0.05%',
        },
        'flat_damage_r1': {
            'flat_damage': 2,
            'max_level': 20,
            'stage_unlock': 6,
            'cost_type': 'rare',
            'display_name': 'Flat Dmg +2',
        },
        'loot_mod_mult': {
            'loot_mod_multiplier': 0.30,  # +0.30x
            'max_level': 10,
            'stage_unlock': 6,
            'cost_type': 'rare',
            'display_name': 'Loot Mod +0.3x',
        },
        'enrage_buff': {
            'enrage_damage': 0.02,  # +2%
            'enrage_crit_damage': 0.02,  # +2%
            'enrage_cooldown': -1,  # -1s
            'max_level': 15,
            'stage_unlock': 7,
            'cost_type': 'rare',
            'display_name': 'Enrage Buff',
        },
        'agi_skill_buff': {
            'max_stamina_skill': 1,
            'mod_chance_skill': 0.0002,  # +0.02%
            'max_level': 5,
            'stage_unlock': 15,
            'cost_type': 'rare',
            'display_name': 'AGI Buff',
        },
        'per_skill_buff': {
            'mod_chance_skill': 0.0001,  # +0.01%
            'armor_pen_skill': 1,
            'max_level': 5,
            'stage_unlock': 22,
            'cost_type': 'rare',
            'display_name': 'PER Buff',
        },
        'fragment_gain_1x': {
            'fragment_gain_mult': 1.25,  # 1.25x
            'max_level': 1,
            'stage_unlock': 36,
            'cost_type': 'rare',
            'display_name': 'Frag Gain 1.25x',
        },
        
        # Epic Fragment Upgrades (purple)
        'flat_damage_e1': {
            'flat_damage': 2,
            'super_crit_chance': 0.0035,  # +0.35%
            'max_level': 25,
            'stage_unlock': 9,
            'cost_type': 'epic',
            'display_name': 'Dmg +2/SCrit +0.35%',
        },
        'arch_xp_frag_e1': {
            'arch_xp_bonus': 0.03,  # +3%
            'fragment_gain': 0.02,  # +2%
            'max_level': 20,
            'stage_unlock': 10,
            'cost_type': 'epic',
            'display_name': 'Exp +3%/Frag +2%',
        },
        'flurry_buff': {
            'flurry_stamina': 1,
            'flurry_cooldown': -1,  # -1s
            'max_level': 10,
            'stage_unlock': 11,
            'cost_type': 'epic',
            'display_name': 'Flurry Buff',
        },
        'stamina_e1': {
            'max_stamina': 4,
            'stamina_mod_gain': 1,
            'max_level': 5,
            'stage_unlock': 12,
            'cost_type': 'epic',
            'display_name': 'Stam +4/+1 Mod',
        },
        'int_skill_buff': {
            'xp_bonus_skill': 0.01,  # +1%
            'mod_chance_skill': 0.0001,  # +0.01%
            'max_level': 5,
            'stage_unlock': 24,
            'cost_type': 'epic',
            'display_name': 'INT Buff',
        },
        'stamina_mod_gain_1': {
            'stamina_mod_gain': 2,
            'max_level': 1,
            'stage_unlock': 38,
            'cost_type': 'epic',
            'display_name': 'Stam Mod +2',
        },
        
        # Legendary Fragment Upgrades (gold)
        'arch_xp_stam_l1': {
            'arch_xp_bonus': 0.05,  # +5%
            'max_stamina_percent': 0.01,  # +1%
            'max_level': 15,
            'stage_unlock': 17,
            'cost_type': 'legendary',
            'display_name': 'Exp +5%/Stam +1%',
        },
        'armor_pen_cd_l1': {
            'armor_pen_percent': 0.02,  # +2%
            'ability_cooldown': -1,  # -1s
            'max_level': 10,
            'stage_unlock': 18,
            'cost_type': 'legendary',
            'display_name': 'APen +2%/CD -1s',
        },
        'crit_dmg_l1': {
            'crit_damage': 0.02,  # +2%
            'super_crit_damage': 0.02,  # +2%
            'max_level': 20,
            'stage_unlock': 20,
            'cost_type': 'legendary',
            'display_name': 'Crit Dmg +2%/+2%',
        },
        'quake_buff': {
            'quake_attacks': 1,
            'quake_cooldown': -2,  # -2s
            'max_level': 10,
            'stage_unlock': 20,
            'cost_type': 'legendary',
            'display_name': 'Quake Buff',
        },
        'all_mod_chance': {
            'all_mod_chance': 0.015,  # +1.50%
            'max_level': 1,
            'stage_unlock': 40,
            'cost_type': 'legendary',
            'display_name': 'All Mod +1.5%',
        },
        
        # Mythic Fragment Upgrades (orange/red)
        'damage_apen_m1': {
            'percent_damage': 0.02,  # +2%
            'armor_pen': 3,
            'max_level': 20,
            'stage_unlock': 26,
            'cost_type': 'mythic',
            'display_name': 'Dmg +2%/APen +3',
        },
        'crit_chance_m1': {
            'super_crit_chance': 0.0035,  # +0.35%
            'ultra_crit_chance': 0.01,  # +1%
            'max_level': 20,
            'stage_unlock': 28,
            'cost_type': 'mythic',
            'display_name': 'S/U Crit +0.35%/+1%',
        },
        'exp_mod_m1': {
            'exp_mod_gain': 0.10,  # +0.10x
            'exp_mod_chance': 0.001,  # +0.10%
            'max_level': 20,
            'stage_unlock': 30,
            'cost_type': 'mythic',
            'display_name': 'Exp Mod +0.1x/+0.1%',
        },
        'ability_stam_m1': {
            'ability_instacharge': 0.003,  # +0.30%
            'max_stamina': 4,
            'max_level': 20,
            'stage_unlock': 32,
            'cost_type': 'mythic',
            'display_name': 'Insta +0.3%/Stam +4',
        },
        'exp_stat_cap_m1': {
            'xp_bonus_mult': 2.0,  # 2.00x
            'all_stat_cap': 5,
            'max_level': 1,
            'stage_unlock': 42,
            'cost_type': 'mythic',
            'display_name': 'Exp 2x/Caps +5',
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
    # Blocks per floor varies between 8-15, average ~11.5
    BLOCKS_PER_FLOOR_MIN = 8
    BLOCKS_PER_FLOOR_MAX = 15
    BLOCKS_PER_FLOOR = 11.5  # Average for calculations (8+15)/2
    
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
            icon_path = get_resource_path("sprites/common/gem.png")
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
            'unlocked_stage': self.get_unlocked_stage(),
            'skill_points': self.skill_points,
            'gem_upgrades': self.gem_upgrades,
            'fragment_upgrade_levels': getattr(self, 'fragment_upgrade_levels', {}),
            'block_cards': self.block_cards,
            'enrage_enabled': self.enrage_enabled.get() if hasattr(self, 'enrage_enabled') else True,
            'flurry_enabled': self.flurry_enabled.get() if hasattr(self, 'flurry_enabled') else True,
            'crit_calc_enabled': self.crit_calc_enabled.get() if hasattr(self, 'crit_calc_enabled') else False,
            'forecast_levels_1': self.forecast_levels_1.get() if hasattr(self, 'forecast_levels_1') else 5,
            'shared_planner_points': self.shared_planner_points.get() if hasattr(self, 'shared_planner_points') else 20,
            'frag_target_type': self.frag_target_var.get() if hasattr(self, 'frag_target_var') else 'common',
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
            self.gem_upgrades = state.get('gem_upgrades', {
                'stamina': 0, 'xp': 0, 'fragment': 0, 'arch_xp': 0,
            })
            # Ensure new upgrade types are present if loading old save
            if 'arch_xp' not in self.gem_upgrades:
                self.gem_upgrades['arch_xp'] = 0
            
            # Load fragment upgrade levels
            self.fragment_upgrade_levels = state.get('fragment_upgrade_levels', {})
            
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
            if hasattr(self, 'flurry_enabled'):
                self.flurry_enabled.set(state.get('flurry_enabled', True))
            if hasattr(self, 'crit_calc_enabled'):
                self.crit_calc_enabled.set(state.get('crit_calc_enabled', False))
            
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
            
            # Update shared planner points (used by all planners except Forecaster)
            if hasattr(self, 'shared_planner_points'):
                # Try to load shared_planner_points, fallback to old individual values for migration
                shared_points = state.get('shared_planner_points')
                if shared_points is None:
                    # Migration: use budget_points if available, otherwise default to 20
                    shared_points = state.get('budget_points', state.get('xp_budget_points', state.get('frag_budget_points', 20)))
                self.shared_planner_points.set(shared_points)
                self.shared_planner_points_label.config(text=str(self.shared_planner_points.get()))
            
            # Update Fragment Planner target type
            if hasattr(self, 'frag_target_var'):
                self.frag_target_var.set(state.get('frag_target_type', 'common'))
                self._update_frag_target_buttons()
            
            # Update unlocked stage and rebuild upgrade widgets
            if hasattr(self, 'unlocked_stage_var'):
                self.unlocked_stage_var.set(str(state.get('unlocked_stage', 1)))
            # Rebuild upgrade widgets after loading fragment_upgrade_levels
            if hasattr(self, 'upgrades_container'):
                self._rebuild_upgrade_widgets()
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
    
    def reset_to_level1(self):
        self.level = 1
        self.current_stage = 1
        self.unlocked_stage = 1
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
        # Gem upgrades
        self.gem_upgrades = {
            'stamina': 0,
            'xp': 0,
            'fragment': 0,
            'arch_xp': 0,
        }
        # Fragment upgrades (new system)
        self.fragment_upgrade_levels = {}
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
        
        # Collect all bonuses from fragment upgrades
        frag_bonuses = self._get_fragment_upgrade_bonuses()
        
        # Base flat damage from skills (with possible skill buff from fragment upgrades)
        flat_damage_per_str = self.SKILL_BONUSES['strength']['flat_damage'] + frag_bonuses.get('flat_damage_skill', 0)
        percent_damage_per_str = self.SKILL_BONUSES['strength']['percent_damage'] + frag_bonuses.get('percent_damage_skill', 0)
        
        flat_damage = (self.base_damage + 
                      str_pts * flat_damage_per_str +
                      frag_bonuses.get('flat_damage', 0))
        percent_damage_bonus = str_pts * percent_damage_per_str + frag_bonuses.get('percent_damage', 0)
        # Damage is always integer (floored) - no decimal damage in game
        total_damage = int(flat_damage * (1 + percent_damage_bonus))
        
        # Armor pen from skills (with possible skill buff)
        armor_pen_per_per = self.SKILL_BONUSES['perception']['armor_pen'] + frag_bonuses.get('armor_pen_skill', 0)
        armor_pen_base = (self.base_armor_pen + 
                    per_pts * armor_pen_per_per +
                    frag_bonuses.get('armor_pen', 0))
        # Apply percent armor pen bonus from fragment upgrades
        armor_pen_base = armor_pen_base * (1 + frag_bonuses.get('armor_pen_percent', 0))
        # INT gives +3% armor pen multiplier per point (rounds up)
        int_armor_pen_mult = 1 + int_pts * self.SKILL_BONUSES['intellect']['armor_pen_mult']
        armor_pen = math.ceil(armor_pen_base * int_armor_pen_mult)
        
        # Max stamina: base + agility + gem upgrade + fragment upgrades
        max_stamina_per_agi = self.SKILL_BONUSES['agility']['max_stamina'] + frag_bonuses.get('max_stamina_skill', 0)
        max_stamina = (self.base_stamina + 
                      agi_pts * max_stamina_per_agi +
                      gem_stamina * self.GEM_UPGRADE_BONUSES['stamina']['max_stamina'] +
                      frag_bonuses.get('max_stamina', 0))
        # Apply percent stamina bonus
        max_stamina = int(max_stamina * (1 + frag_bonuses.get('max_stamina_percent', 0)))
        
        crit_chance = (self.base_crit_chance + 
                      agi_pts * self.SKILL_BONUSES['agility']['crit_chance'] +
                      luck_pts * self.SKILL_BONUSES['luck']['crit_chance'] +
                      frag_bonuses.get('crit_chance', 0))
        # STR crit damage bonus is a MULTIPLIER on base crit damage, not additive
        str_crit_mult = 1 + str_pts * self.SKILL_BONUSES['strength']['crit_damage']
        crit_damage = (self.base_crit_damage * str_crit_mult +
                      frag_bonuses.get('crit_damage', 0))
        one_hit_chance = luck_pts * self.SKILL_BONUSES['luck']['one_hit_chance']
        
        # Super crit and ultra crit from fragment upgrades
        super_crit_chance = frag_bonuses.get('super_crit_chance', 0)
        super_crit_damage = frag_bonuses.get('super_crit_damage', 0)
        ultra_crit_chance = frag_bonuses.get('ultra_crit_chance', 0)
        
        # XP mult: base + intellect + gem upgrade + fragment upgrades
        xp_bonus_per_int = self.SKILL_BONUSES['intellect']['xp_bonus'] + frag_bonuses.get('xp_bonus_skill', 0)
        xp_mult = (self.base_xp_mult + 
                  int_pts * xp_bonus_per_int +
                  gem_xp * self.GEM_UPGRADE_BONUSES['xp']['xp_bonus'])
        # Apply XP multiplier from fragment upgrades
        if frag_bonuses.get('xp_bonus_mult', 0) > 0:
            xp_mult *= frag_bonuses.get('xp_bonus_mult', 1.0)
        
        # Fragment mult: base + perception + gem upgrade + fragment upgrades
        fragment_mult = (self.base_fragment_mult + 
                        per_pts * self.SKILL_BONUSES['perception']['fragment_gain'] +
                        gem_fragment * self.GEM_UPGRADE_BONUSES['fragment']['fragment_gain'] +
                        frag_bonuses.get('fragment_gain', 0))
        # Apply fragment gain multiplier
        if frag_bonuses.get('fragment_gain_mult', 0) > 0:
            fragment_mult *= frag_bonuses.get('fragment_gain_mult', 1.0)
        
        # Mod chances (per block)
        # Luck adds to ALL mod chances
        all_mod_bonus = (luck_pts * self.SKILL_BONUSES['luck']['all_mod_chance'] + 
                        frag_bonuses.get('all_mod_chance', 0))
        # Skill buff adds to all mod chances
        mod_chance_skill_bonus = frag_bonuses.get('mod_chance_skill', 0)
        
        # Exp mod: intellect + luck + gem upgrade + fragment upgrades
        exp_mod_chance = (int_pts * self.SKILL_BONUSES['intellect']['exp_mod_chance'] + 
                         all_mod_bonus + mod_chance_skill_bonus +
                         gem_xp * self.GEM_UPGRADE_BONUSES['xp']['exp_mod_chance'] +
                         frag_bonuses.get('exp_mod_chance', 0))
        
        # Loot mod: perception + luck + gem upgrade
        loot_mod_chance = (per_pts * self.SKILL_BONUSES['perception']['loot_mod_chance'] + 
                          all_mod_bonus + mod_chance_skill_bonus +
                          gem_fragment * self.GEM_UPGRADE_BONUSES['fragment']['loot_mod_chance'])
        
        speed_mod_chance = agi_pts * self.SKILL_BONUSES['agility']['speed_mod_chance'] + all_mod_bonus + mod_chance_skill_bonus
        
        # Stamina mod: luck + gem upgrade + fragment upgrades
        stamina_mod_chance = (all_mod_bonus + mod_chance_skill_bonus +
                             gem_stamina * self.GEM_UPGRADE_BONUSES['stamina']['stamina_mod_chance'] +
                             frag_bonuses.get('stamina_mod_chance', 0))
        
        # Archaeology XP bonus from gem upgrade + fragment upgrades
        arch_xp_mult = (1.0 + 
                       gem_arch_xp * self.GEM_UPGRADE_BONUSES['arch_xp']['arch_xp_bonus'] +
                       frag_bonuses.get('arch_xp_bonus', 0))
        
        # Loot mod multiplier bonus (affects average loot from loot mod)
        loot_mod_multiplier = self.MOD_LOOT_MULTIPLIER_AVG + frag_bonuses.get('loot_mod_multiplier', 0)
        
        # Exp mod gain bonus (affects average XP from exp mod)
        exp_mod_gain = self.MOD_EXP_MULTIPLIER_AVG + frag_bonuses.get('exp_mod_gain', 0)
        
        # Stamina mod gain bonus
        stamina_mod_gain = self.MOD_STAMINA_BONUS_AVG + frag_bonuses.get('stamina_mod_gain', 0)
        
        return {
            'flat_damage': flat_damage,
            'total_damage': total_damage,
            'armor_pen': armor_pen,
            'max_stamina': max_stamina,
            'crit_chance': min(1.0, crit_chance),
            'crit_damage': crit_damage,
            'super_crit_chance': min(1.0, super_crit_chance),
            'super_crit_damage': super_crit_damage,
            'ultra_crit_chance': min(1.0, ultra_crit_chance),
            'one_hit_chance': min(1.0, one_hit_chance),
            'xp_mult': xp_mult,
            'fragment_mult': fragment_mult,
            # Mod chances
            'exp_mod_chance': min(1.0, exp_mod_chance),
            'loot_mod_chance': min(1.0, loot_mod_chance),
            'speed_mod_chance': min(1.0, speed_mod_chance),
            'stamina_mod_chance': min(1.0, stamina_mod_chance),
            # Mod effect bonuses
            'loot_mod_multiplier': loot_mod_multiplier,
            'exp_mod_gain': exp_mod_gain,
            'stamina_mod_gain': stamina_mod_gain,
            # Archaeology XP multiplier (applies to leveling)
            'arch_xp_mult': arch_xp_mult,
        }
    
    def _get_fragment_upgrade_bonuses(self):
        """Collect all bonuses from fragment upgrades into a single dict"""
        bonuses = {}
        
        for upgrade_key, level in self.fragment_upgrade_levels.items():
            if level <= 0:
                continue
            
            upgrade_info = self.FRAGMENT_UPGRADES.get(upgrade_key, {})
            
            # Add each bonus type multiplied by level
            for bonus_key, bonus_value in upgrade_info.items():
                # Skip non-bonus keys
                if bonus_key in ('max_level', 'stage_unlock', 'cost_type', 'display_name'):
                    continue
                
                if bonus_key not in bonuses:
                    bonuses[bonus_key] = 0
                bonuses[bonus_key] += bonus_value * level
        
        return bonuses
    
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
        - Critical hits (if crit_calc_enabled is ON)
        - One-hit chance (if crit_calc_enabled is ON)
        - Enrage ability (5 charges every 60s with +20% dmg, +100% crit dmg) - if enabled
        - Card HP reduction (if block_type provided)
        
        If crit_calc_enabled is OFF (deterministic mode):
        - Only uses base damage, no crit averaging
        - Returns ceil(hp / damage) - exact number of hits needed
        """
        import math
        
        # Apply card HP reduction if block_type is provided
        if block_type:
            block_hp = self.get_block_hp_with_card(block_hp, block_type)
        
        # Calculate effective damage (base, no enrage)
        effective_dmg_base = self.calculate_effective_damage(stats, block_armor)
        
        # Check if Crit calculation is enabled
        crit_calc_active = getattr(self, 'crit_calc_enabled', None)
        use_crit = crit_calc_active is not None and crit_calc_active.get()
        
        if not use_crit:
            # DETERMINISTIC MODE: Pure damage without crits
            # Just calculate ceil(hp / damage)
            if effective_dmg_base > 0:
                return math.ceil(block_hp / effective_dmg_base)
            return float('inf')
        
        # CRIT MODE: Include crit calculations
        crit_chance = stats['crit_chance']
        crit_damage = stats['crit_damage']
        one_hit_chance = stats['one_hit_chance']
        
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
    
    def calculate_floors_per_run(self, stats, starting_floor: int, blocks_per_floor: float = None):
        """
        Calculate floors per run, accounting for:
        - Stamina Mod: Each block has a chance to give +6.5 stamina (avg of 3-10)
        - Flurry ability: 5 charges × 5 stamina every 120 seconds (if enabled)
        """
        # Use average blocks per floor (11.5) if not specified
        if blocks_per_floor is None:
            blocks_per_floor = self.BLOCKS_PER_FLOOR
        
        max_stamina = stats['max_stamina']
        stamina_remaining = max_stamina
        floors_cleared = 0
        current_floor = starting_floor
        
        # Stamina mod: each block has stamina_mod_chance to give avg +6.5 stamina
        stamina_mod_chance = stats.get('stamina_mod_chance', 0)
        stamina_mod_gain = stats.get('stamina_mod_gain', self.MOD_STAMINA_BONUS_AVG)
        avg_stamina_per_block = stamina_mod_chance * stamina_mod_gain
        
        # Flurry: +5 stamina on cast (once), 120s cooldown
        # Approximation: assume ~1 hit per second, so flurry stamina per hit = stamina / cooldown
        flurry_active = getattr(self, 'flurry_enabled', None)
        flurry_stamina_per_hit = 0
        if flurry_active is not None and flurry_active.get():
            # Get flurry upgrades from fragment bonuses
            frag_bonuses = self._get_fragment_upgrade_bonuses()
            flurry_stamina_bonus = frag_bonuses.get('flurry_stamina', 0)
            flurry_cooldown_reduction = frag_bonuses.get('flurry_cooldown', 0)
            
            # Calculate effective values
            stamina_on_cast = self.FLURRY_STAMINA_BONUS + flurry_stamina_bonus
            effective_cooldown = max(10, self.FLURRY_COOLDOWN + flurry_cooldown_reduction)  # min 10s
            
            # Stamina gained per hit (assuming ~1 hit per second)
            flurry_stamina_per_hit = stamina_on_cast / effective_cooldown
        
        # Add flurry stamina to the per-block stamina gain
        avg_stamina_per_block += flurry_stamina_per_hit
        
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
        arch_xp_mult = stats.get('arch_xp_mult', 1.0)  # Archaeology XP bonus
        exp_mod_chance = stats.get('exp_mod_chance', 0)
        exp_mod_gain = stats.get('exp_mod_gain', 0)  # Bonus to exp mod multiplier
        
        # Exp mod gives 3x-5x XP (avg 4x), plus any bonuses from upgrades
        exp_mod_multiplier = self.MOD_EXP_MULTIPLIER_AVG + exp_mod_gain
        # Expected XP multiplier from exp mod: (1-chance)*1 + chance*exp_mod_mult
        exp_mod_factor = 1 + exp_mod_chance * (exp_mod_multiplier - 1)
        
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
            
            # XP for this floor: blocks * avg_xp * xp_mult * arch_xp_mult * exp_mod_factor
            floor_total_xp = self.BLOCKS_PER_FLOOR * floor_xp * xp_mult * arch_xp_mult * exp_mod_factor
            total_xp += floor_total_xp * floor_mult
            
            current_floor += 1
        
        return total_xp
    
    def calculate_fragments_per_run(self, stats, starting_floor: int):
        """
        Calculate expected fragments gained per run, broken down by fragment type.
        
        Returns:
            dict with fragment counts per type: {'common': X, 'rare': Y, ...}
        """
        floors = self.calculate_floors_per_run(stats, starting_floor)
        if floors <= 0:
            return {'common': 0, 'rare': 0, 'epic': 0, 'legendary': 0, 'mythic': 0}
        
        fragment_mult = stats['fragment_mult']
        loot_mod_chance = stats.get('loot_mod_chance', 0)
        loot_mod_multiplier = stats.get('loot_mod_multiplier', self.MOD_LOOT_MULTIPLIER_AVG)
        
        # Loot mod effect: expected multiplier
        loot_mod_factor = 1 + loot_mod_chance * (loot_mod_multiplier - 1)
        
        # Track fragments by type
        fragments_by_type = {'common': 0.0, 'rare': 0.0, 'epic': 0.0, 'legendary': 0.0, 'mythic': 0.0}
        
        current_floor = starting_floor
        floors_to_process = int(floors)
        partial_floor = floors - floors_to_process
        
        for i in range(floors_to_process + 1):
            if i == floors_to_process:
                floor_mult = partial_floor
                if floor_mult <= 0:
                    break
            else:
                floor_mult = 1.0
            
            spawn_rates = get_normalized_spawn_rates(current_floor)
            block_mix = get_block_mix_for_floor(current_floor)
            
            for block_type, spawn_chance in spawn_rates.items():
                if spawn_chance <= 0 or block_type == 'dirt':
                    continue  # Dirt doesn't drop fragments
                block_data = block_mix.get(block_type)
                if not block_data:
                    continue
                
                # Base fragment per block
                base_frag = block_data.fragment
                
                # Fragments from this block type on this floor
                # blocks_per_floor * spawn_chance * base_frag * mult * loot_mod
                frag_gain = self.BLOCKS_PER_FLOOR * spawn_chance * base_frag * fragment_mult * loot_mod_factor * floor_mult
                
                # Map block_type to fragment type (they're the same names)
                if block_type in fragments_by_type:
                    fragments_by_type[block_type] += frag_gain
            
            current_floor += 1
        
        return fragments_by_type
    
    def calculate_run_duration(self, stats, starting_floor: int):
        """
        Calculate expected run duration in seconds.
        
        Base: 1 hit = 1 second
        Speed modifiers:
        - Speed Mod: 2x speed for avg 60 hits when triggered
        - Flurry: 2x speed during active (every 120s cooldown)
        
        Returns:
            Run duration in seconds
        """
        # Total hits = stamina (since 1 hit costs 1 stamina)
        total_hits = stats['max_stamina']
        
        # Add stamina from Stamina Mod
        stamina_mod_chance = stats.get('stamina_mod_chance', 0)
        blocks_per_run = self.calculate_blocks_per_run(stats, starting_floor)
        stamina_mod_gain = self.MOD_STAMINA_BONUS_AVG
        # Get bonus from fragment upgrades
        frag_bonuses = self._get_fragment_upgrade_bonuses()
        stamina_mod_gain += frag_bonuses.get('stamina_mod_gain', 0)
        avg_stamina_from_mod = blocks_per_run * stamina_mod_chance * stamina_mod_gain
        total_hits += avg_stamina_from_mod
        
        # Add stamina from Flurry
        flurry_active = getattr(self, 'flurry_enabled', None)
        if flurry_active and flurry_active.get():
            flurry_cooldown = self.FLURRY_COOLDOWN + frag_bonuses.get('flurry_cooldown', 0)
            flurry_cooldown = max(10, flurry_cooldown)
            flurry_stamina = self.FLURRY_STAMINA_BONUS + frag_bonuses.get('flurry_stamina', 0)
            # Estimate run duration first without flurry to see how many activations
            base_duration = total_hits  # 1 hit = 1 second base
            flurry_activations = base_duration / flurry_cooldown
            total_hits += flurry_activations * flurry_stamina
        
        # Base duration: 1 hit per second
        base_duration_seconds = total_hits
        
        # Speed Mod effect: 2x speed for avg 60 hits
        speed_mod_chance = stats.get('speed_mod_chance', 0)
        speed_mod_hits_avg = self.MOD_SPEED_ATTACKS_AVG  # 60 hits on average
        # Expected speed mod hits per run
        speed_mod_hits = blocks_per_run * speed_mod_chance * speed_mod_hits_avg
        # These hits take half the time (2x speed)
        time_saved_from_speed_mod = speed_mod_hits * 0.5  # Save 0.5s per hit
        
        # Flurry effect: 2x speed while active
        # Flurry is active for ~5 hits every cooldown period
        flurry_time_saved = 0
        if flurry_active and flurry_active.get():
            # Flurry gives 2x speed, but we already counted the stamina bonus
            # The 2x speed is active during the enrage-like window (5 charges)
            # Actually Flurry is +100% attack speed = 2x speed for some period
            # Let's estimate: during the run, we get multiple flurry activations
            # Each activation speeds up some hits
            flurry_cooldown = self.FLURRY_COOLDOWN + frag_bonuses.get('flurry_cooldown', 0)
            flurry_cooldown = max(10, flurry_cooldown)
            activations = base_duration_seconds / flurry_cooldown
            # Assume flurry lasts ~10 seconds at 2x speed = saves 10 seconds per activation
            # This is an approximation
            flurry_time_saved = activations * 5  # Save ~5 seconds per activation
        
        run_duration = base_duration_seconds - time_saved_from_speed_mod - flurry_time_saved
        return max(10, run_duration)  # Minimum 10 seconds
    
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
    
    def add_skill_point(self, skill_name):
        self.skill_points[skill_name] += 1
        self.level += 1
        self.update_display()
    
    def add_skill_points(self, skill_name, amount):
        """Add multiple skill points at once"""
        self.skill_points[skill_name] += amount
        self.level += amount
        self.update_display()
    
    def remove_skill_point(self, skill_name):
        if self.skill_points[skill_name] > 0:
            self.skill_points[skill_name] -= 1
            self.level = max(1, self.level - 1)
            self.update_display()
    
    def remove_skill_points(self, skill_name, amount):
        """Remove multiple skill points at once"""
        current = self.skill_points[skill_name]
        to_remove = min(amount, current)  # Don't go below 0
        if to_remove > 0:
            self.skill_points[skill_name] -= to_remove
            self.level = max(1, self.level - to_remove)
            self.update_display()
    
    def reset_all_skill_points(self):
        """Reset all skill points to 0"""
        total_points = sum(self.skill_points.values())
        self.skill_points = {
            'strength': 0, 'agility': 0, 'intellect': 0, 'perception': 0, 'luck': 0,
        }
        self.level = max(1, self.level - total_points)
        self.update_display()
    
    def reset_all_upgrades(self):
        """Reset all fragment upgrades to 0"""
        self.gem_upgrades['arch_xp'] = 0
        self.fragment_upgrade_levels = {}
        # Rebuild widgets to show reset values
        if hasattr(self, 'upgrades_container'):
            self._rebuild_upgrade_widgets()
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
    
    def calculate_fragment_upgrade_efficiency(self, upgrade_key):
        """Calculate the efficiency factor of adding one fragment upgrade level (Stage Rush = Floors/Run improvement per cost)"""
        upgrade_info = self.FRAGMENT_UPGRADES.get(upgrade_key, {})
        max_level = upgrade_info.get('max_level', 25)
        current_level = self.fragment_upgrade_levels.get(upgrade_key, 0)
        
        if current_level >= max_level:
            return 0, 0
        
        # Get cost for next level
        cost = get_upgrade_cost(upgrade_key, current_level)
        if cost is None or cost <= 0:
            return 0, 0
        
        current_stats = self.get_total_stats()
        current_floors = self.calculate_floors_per_run(current_stats, self.current_stage)
        
        # Temporarily add one level
        self.fragment_upgrade_levels[upgrade_key] = current_level + 1
        new_stats = self.get_total_stats()
        new_floors = self.calculate_floors_per_run(new_stats, self.current_stage)
        # Restore original level
        self.fragment_upgrade_levels[upgrade_key] = current_level
        
        # Calculate efficiency factor: floors improvement per fragment cost
        floors_improvement = new_floors - current_floors
        efficiency_factor = floors_improvement / cost if cost > 0 else 0
        
        return new_floors, efficiency_factor
    
    def calculate_fragment_upgrade_xp_efficiency(self, upgrade_key):
        """Calculate the XP efficiency factor of adding one fragment upgrade level (XP improvement per cost)"""
        upgrade_info = self.FRAGMENT_UPGRADES.get(upgrade_key, {})
        max_level = upgrade_info.get('max_level', 25)
        current_level = self.fragment_upgrade_levels.get(upgrade_key, 0)
        
        if current_level >= max_level:
            return 0, 0
        
        # Get cost for next level
        cost = get_upgrade_cost(upgrade_key, current_level)
        if cost is None or cost <= 0:
            return 0, 0
        
        current_stats = self.get_total_stats()
        current_xp = self.calculate_xp_per_run(current_stats, self.current_stage)
        
        # Temporarily add one level
        self.fragment_upgrade_levels[upgrade_key] = current_level + 1
        new_stats = self.get_total_stats()
        new_xp = self.calculate_xp_per_run(new_stats, self.current_stage)
        # Restore original level
        self.fragment_upgrade_levels[upgrade_key] = current_level
        
        # Calculate efficiency factor: XP improvement per fragment cost
        xp_improvement = new_xp - current_xp
        efficiency_factor = xp_improvement / cost if cost > 0 else 0
        
        return new_xp, efficiency_factor
    
    def calculate_fragment_upgrade_fragment_efficiency(self, upgrade_key):
        """
        Calculate the Fragment/Hour efficiency factor of adding one fragment upgrade level.
        
        Returns:
            (new_frags_per_hour, efficiency_factor) - Frag/h improvement per fragment cost
        """
        upgrade_info = self.FRAGMENT_UPGRADES.get(upgrade_key, {})
        max_level = upgrade_info.get('max_level', 25)
        current_level = self.fragment_upgrade_levels.get(upgrade_key, 0)
        
        if current_level >= max_level:
            return 0, 0
        
        # Get cost for next level
        cost = get_upgrade_cost(upgrade_key, current_level)
        if cost is None or cost <= 0:
            return 0, 0
        
        current_stats = self.get_total_stats()
        current_frags = self.calculate_fragments_per_run(current_stats, self.current_stage)
        current_total = sum(current_frags.values())
        current_duration = self.calculate_run_duration(current_stats, self.current_stage)
        
        # Calculate current frags/hour
        if current_duration > 0:
            current_frags_per_hour = current_total * (3600.0 / current_duration)
        else:
            current_frags_per_hour = 0
        
        # Temporarily add one level
        self.fragment_upgrade_levels[upgrade_key] = current_level + 1
        new_stats = self.get_total_stats()
        new_frags = self.calculate_fragments_per_run(new_stats, self.current_stage)
        new_total = sum(new_frags.values())
        new_duration = self.calculate_run_duration(new_stats, self.current_stage)
        # Restore original level
        self.fragment_upgrade_levels[upgrade_key] = current_level
        
        # Calculate new frags/hour
        if new_duration > 0:
            new_frags_per_hour = new_total * (3600.0 / new_duration)
        else:
            new_frags_per_hour = 0
        
        # Calculate efficiency factor: Frag/h improvement per fragment cost
        frag_improvement = new_frags_per_hour - current_frags_per_hour
        efficiency_factor = frag_improvement / cost if cost > 0 else 0
        
        return new_frags_per_hour, efficiency_factor
    
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
        
        # Right: Stage selector, Unlocked Stage, Enrage toggle, and Reset button
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
        
        # Unlocked Stage input - determines which upgrades are available
        tk.Label(controls_frame, text="Unlocked:", font=("Arial", 10), 
                background="#E3F2FD").pack(side=tk.LEFT, padx=(0, 3))
        
        # Minus button
        unlocked_minus_btn = tk.Button(controls_frame, text="-", width=2, font=("Arial", 8, "bold"),
                                       command=self._decrease_unlocked_stage)
        unlocked_minus_btn.pack(side=tk.LEFT, padx=(0, 1))
        
        self.unlocked_stage_var = tk.StringVar(value="1")
        self.unlocked_stage_entry = ttk.Entry(
            controls_frame,
            textvariable=self.unlocked_stage_var,
            width=4
        )
        self.unlocked_stage_entry.pack(side=tk.LEFT, padx=(0, 1))
        self.unlocked_stage_var.trace_add('write', self._on_unlocked_stage_changed)
        
        # Plus button
        unlocked_plus_btn = tk.Button(controls_frame, text="+", width=2, font=("Arial", 8, "bold"),
                                      command=self._increase_unlocked_stage)
        unlocked_plus_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        # Help icon for unlocked stage
        unlocked_help_label = tk.Label(controls_frame, text="?", font=("Arial", 9, "bold"), 
                                      cursor="hand2", foreground="#1976D2", background="#E3F2FD")
        unlocked_help_label.pack(side=tk.LEFT, padx=(0, 10))
        self._create_unlocked_stage_help_tooltip(unlocked_help_label)
        
        # Enrage toggle checkbox
        self.enrage_enabled = tk.BooleanVar(value=True)
        enrage_checkbox = ttk.Checkbutton(
            controls_frame,
            text="Enrage",
            variable=self.enrage_enabled,
            command=self.update_display
        )
        enrage_checkbox.pack(side=tk.LEFT, padx=(0, 5))
        
        # Flurry toggle checkbox
        self.flurry_enabled = tk.BooleanVar(value=True)
        flurry_checkbox = ttk.Checkbutton(
            controls_frame,
            text="Flurry",
            variable=self.flurry_enabled,
            command=self.update_display
        )
        flurry_checkbox.pack(side=tk.LEFT, padx=(0, 5))
        
        # Crit toggle checkbox - deterministic vs crit-based calculations
        # Highlighted frame for Crit and MC
        crit_mc_frame = tk.Frame(controls_frame, background="#FFD700", relief=tk.RAISED, borderwidth=2)
        crit_mc_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        inner_crit_mc = tk.Frame(crit_mc_frame, background="#FFF8DC", padx=3, pady=2)
        inner_crit_mc.pack()
        
        self.crit_calc_enabled = tk.BooleanVar(value=False)  # Default: deterministic
        crit_checkbox = ttk.Checkbutton(
            inner_crit_mc,
            text="Crit",
            variable=self.crit_calc_enabled,
            command=self.update_display
        )
        crit_checkbox.pack(side=tk.LEFT, padx=(0, 3))
        
        # Help icon for crit toggle
        crit_help_label = tk.Label(inner_crit_mc, text="?", font=("Arial", 9, "bold"), 
                                  cursor="hand2", foreground="#1976D2", background="#FFF8DC")
        crit_help_label.pack(side=tk.LEFT, padx=(0, 5))
        self._create_crit_toggle_help_tooltip(crit_help_label)
        
        # MC Stage Pusher button
        mc_stage_pusher_button = tk.Button(
            inner_crit_mc,
            text="MC Stage Pusher",
            command=self.run_mc_stage_pusher,
            font=("Arial", 9),
            bg="#9C27B0",
            fg="#FFFFFF",
            activebackground="#BA68C8",
            activeforeground="#FFFFFF",
            relief=tk.RAISED,
            borderwidth=2
        )
        mc_stage_pusher_button.pack(side=tk.LEFT, padx=(5, 0))
        
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
            'intellect': "XP, Armor Pen%",
            'perception': "Frags, Armor Pen",
            'luck': "Crit, One-Hit",
        }
        
        for i, (skill, info) in enumerate(skill_info.items()):
            row_frame = tk.Frame(skills_frame, background="#E8F5E9")
            row_frame.pack(fill=tk.X, pady=1)
            
            # -5 button
            minus5_btn = tk.Button(row_frame, text="-5", width=2, font=("Arial", 8, "bold"),
                                  command=lambda s=skill: self.remove_skill_points(s, 5))
            minus5_btn.pack(side=tk.LEFT, padx=(0, 1))
            
            # -1 button
            minus_btn = tk.Button(row_frame, text="-", width=2, font=("Arial", 8, "bold"),
                                 command=lambda s=skill: self.remove_skill_point(s))
            minus_btn.pack(side=tk.LEFT, padx=(0, 1))
            
            # +1 button
            plus_btn = tk.Button(row_frame, text="+", width=2, font=("Arial", 8, "bold"),
                                command=lambda s=skill: self.add_skill_point(s))
            plus_btn.pack(side=tk.LEFT, padx=(0, 1))
            
            # +5 button
            plus5_btn = tk.Button(row_frame, text="+5", width=2, font=("Arial", 8, "bold"),
                                 command=lambda s=skill: self.add_skill_points(s, 5))
            plus5_btn.pack(side=tk.LEFT, padx=(0, 3))
            
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
        
        # Fragment Upgrades Section - dynamically built based on unlocked stage
        upgrade_header_frame = tk.Frame(col_frame, background="#E8F5E9")
        upgrade_header_frame.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        tk.Label(upgrade_header_frame, text="Fragment Upgrades", font=("Arial", 10, "bold"), 
                background="#E8F5E9").pack(side=tk.LEFT)
        
        # Load fragment icons for each type
        self._load_fragment_icons()
        
        # Load block icons for cards section
        self._load_block_icons()
        
        # Reset button for upgrades
        tk.Button(upgrade_header_frame, text="Reset", font=("Arial", 7), 
                 command=self.reset_all_upgrades).pack(side=tk.RIGHT)
        
        # Container for dynamically built upgrades (will be rebuilt when unlocked_stage changes)
        self.upgrades_container = tk.Frame(col_frame, background="#E8F5E9")
        self.upgrades_container.pack(fill=tk.X, padx=5, pady=2)
        
        # Store reference to parent column frame for rebuilding
        self.skills_col_frame = col_frame
        
        # Initialize upgrade tracking dicts
        self.upgrade_buttons = {}
        self.upgrade_efficiency_labels = {}  # Stage Rush (Floors)
        self.upgrade_xp_efficiency_labels = {}  # XP efficiency
        self.upgrade_frag_efficiency_labels = {}  # Fragment efficiency
        self.upgrade_cost_labels = {}
        self.upgrade_level_labels = {}
        self.fragment_upgrade_levels = {}  # Track levels for new FRAGMENT_UPGRADES
        
        # Build initial upgrade widgets
        self._rebuild_upgrade_widgets()
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # Gem Upgrades Section - with gem icon and distinct styling
        gem_header_frame = tk.Frame(col_frame, background="#E8F5E9")
        gem_header_frame.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        # Load gem icon
        try:
            gem_icon_path = get_resource_path("sprites/common/gem.png")
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
        
        # === CARDS SECTION ===
        cards_header = tk.Frame(col_frame, background="#E8F5E9")
        cards_header.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        # Load cards icon
        try:
            cards_icon_path = get_resource_path("sprites/archaeology/cards.png")
            if cards_icon_path.exists():
                cards_icon_image = Image.open(cards_icon_path)
                cards_icon_image = cards_icon_image.resize((16, 16), Image.Resampling.LANCZOS)
                self.cards_icon = ImageTk.PhotoImage(cards_icon_image)
                tk.Label(cards_header, image=self.cards_icon, background="#E8F5E9").pack(side=tk.LEFT, padx=(0, 5))
        except:
            pass
        
        tk.Label(cards_header, text="Cards", font=("Arial", 10, "bold"), 
                background="#E8F5E9", foreground="#B8860B").pack(side=tk.LEFT)
        
        cards_help = tk.Label(cards_header, text="?", font=("Arial", 9, "bold"), 
                             cursor="hand2", foreground="#B8860B", background="#E8F5E9")
        cards_help.pack(side=tk.LEFT, padx=(5, 0))
        self._create_cards_help_tooltip(cards_help)
        
        # Cards container with scrollbar
        cards_scroll_frame = tk.Frame(col_frame, background="#E8F5E9")
        cards_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # Create canvas and scrollbar
        cards_canvas = tk.Canvas(cards_scroll_frame, background="#E8F5E9", highlightthickness=0)
        cards_scrollbar = tk.Scrollbar(cards_scroll_frame, orient="vertical", command=cards_canvas.yview)
        self.cards_container = tk.Frame(cards_canvas, background="#E8F5E9")
        
        # Create window in canvas
        canvas_window = cards_canvas.create_window((0, 0), window=self.cards_container, anchor="nw")
        
        # Configure scroll region and canvas width
        def update_scroll_region(event):
            cards_canvas.configure(scrollregion=cards_canvas.bbox("all"))
            # Update canvas window width to match canvas width
            canvas_width = cards_canvas.winfo_width()
            if canvas_width > 1:  # Only update if canvas has been rendered
                cards_canvas.itemconfig(canvas_window, width=canvas_width)
        
        self.cards_container.bind("<Configure>", update_scroll_region)
        cards_canvas.bind('<Configure>', lambda e: cards_canvas.itemconfig(canvas_window, width=e.width))
        
        # Configure canvas scrolling
        cards_canvas.configure(yscrollcommand=cards_scrollbar.set)
        
        # Pack canvas and scrollbar
        cards_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cards_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            cards_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        cards_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.card_labels = {}
        
        for block_type in BLOCK_TYPES:
            row_frame = tk.Frame(self.cards_container, background="#E8F5E9")
            row_frame.pack(fill=tk.X, pady=1)
            
            color = self.BLOCK_COLORS.get(block_type, '#888888')
            
            # Block icon if available
            if hasattr(self, 'block_icons') and block_type in self.block_icons:
                tk.Label(row_frame, image=self.block_icons[block_type], 
                        background="#E8F5E9").pack(side=tk.LEFT, padx=(0, 3))
            
            # Block name
            name_label = tk.Label(row_frame, text=f"{block_type.capitalize()}", 
                                 font=("Arial", 8, "bold"), foreground=color,
                                 background="#E8F5E9", width=8, anchor=tk.W)
            name_label.pack(side=tk.LEFT)
            
            # Card button (normal card: -10% HP, +10% XP)
            card_btn = tk.Label(row_frame, text="Card", font=("Arial", 8),
                               cursor="hand2", foreground="#888888", background="#E8F5E9",
                               padx=3, relief=tk.RAISED, borderwidth=1)
            card_btn.pack(side=tk.LEFT, padx=(0, 3))
            card_btn.bind("<Button-1>", lambda e, bt=block_type: self._toggle_card(bt, 1))
            
            # Gilded card button (gilded: -20% HP, +20% XP)
            gilded_btn = tk.Label(row_frame, text="Gilded", font=("Arial", 8),
                                 cursor="hand2", foreground="#888888", background="#E8F5E9",
                                 padx=3, relief=tk.RAISED, borderwidth=1)
            gilded_btn.pack(side=tk.LEFT, padx=(0, 3))
            gilded_btn.bind("<Button-1>", lambda e, bt=block_type: self._toggle_card(bt, 2))
            
            # Gilded improvement indicator
            gilded_improve_label = tk.Label(row_frame, text="", font=("Arial", 8),
                                           foreground="#B8860B", background="#E8F5E9",
                                           width=7, anchor=tk.W)
            gilded_improve_label.pack(side=tk.LEFT)
            
            self.card_labels[block_type] = {
                'row': row_frame,
                'name': name_label,
                'card_btn': card_btn,
                'gilded_btn': gilded_btn,
                'gilded_improve': gilded_improve_label,
            }
    
    def _create_cards_help_tooltip(self, widget):
        """Creates a tooltip explaining the Cards feature"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 280
            tooltip_height = 320
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#B8860B", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content.pack()
            
            tk.Label(content, text="Block Cards", font=("Arial", 10, "bold"),
                    background="#FFFFFF", foreground="#B8860B").pack(anchor="w")
            
            lines = [
                "",
                "Cards reduce block HP and boost XP.",
                "",
                "Card (Normal):",
                "  -10% Block HP",
                "  +10% XP from block",
                "",
                "Gilded Card:",
                "  -20% Block HP", 
                "  +20% XP from block",
                "",
                "The +X.XX% shows improvement in",
                "floors/run if you upgrade to Gilded.",
                "",
                "Click to toggle. Click same to remove.",
            ]
            
            for line in lines:
                tk.Label(content, text=line, font=("Arial", 9),
                        background="#FFFFFF", justify=tk.LEFT).pack(anchor="w")
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _load_fragment_icons(self):
        """Load fragment icons for each rarity type"""
        self.fragment_icons = {}
        icon_map = {
            'common': 'fragmentcommon.png',
            'rare': 'fragmentrare.png',
            'epic': 'fragmentepic.png',
            'legendary': 'fragmentlegendary.png',
            'mythic': 'fragmentmythic.png',
        }
        
        for frag_type, filename in icon_map.items():
            try:
                icon_path = get_resource_path(f"sprites/archaeology/{filename}")
                if icon_path.exists():
                    icon_image = Image.open(icon_path)
                    icon_image = icon_image.resize((12, 12), Image.Resampling.LANCZOS)
                    self.fragment_icons[frag_type] = ImageTk.PhotoImage(icon_image)
            except:
                pass
    
    def _load_block_icons(self):
        """Load block icons for each block type (Tier 1 icons)"""
        self.block_icons = {}
        icon_map = {
            'dirt': 'block_dirt_t1.png',
            'common': 'block_common_t1.png',
            'rare': 'block_rare_t1.png',
            'epic': 'block_epic_t1.png',
            'legendary': 'block_legendary_t1.png',
            'mythic': 'block_mythic_t1.png',
        }
        
        for block_type, filename in icon_map.items():
            try:
                icon_path = get_resource_path(f"sprites/archaeology/{filename}")
                if icon_path.exists():
                    icon_image = Image.open(icon_path)
                    icon_image = icon_image.resize((16, 16), Image.Resampling.LANCZOS)
                    self.block_icons[block_type] = ImageTk.PhotoImage(icon_image)
            except:
                pass
    
    def _rebuild_upgrade_widgets(self):
        """Rebuild the fragment upgrade widgets based on current unlocked stage"""
        # Clear existing widgets
        for widget in self.upgrades_container.winfo_children():
            widget.destroy()
        
        # Clear tracking dicts (but preserve levels)
        self.upgrade_buttons = {}
        self.upgrade_efficiency_labels = {}  # Stage Rush (Floors)
        self.upgrade_xp_efficiency_labels = {}  # XP efficiency
        self.upgrade_frag_efficiency_labels = {}  # Fragment efficiency
        self.upgrade_cost_labels = {}
        self.upgrade_level_labels = {}
        
        unlocked_stage = self.get_unlocked_stage()
        
        # Column headers for the three efficiency types
        header_row = tk.Frame(self.upgrades_container, background="#E8F5E9")
        header_row.pack(fill=tk.X, pady=(0, 3))
        
        # Spacer for buttons and level (left side)
        tk.Label(header_row, text="", background="#E8F5E9", width=28).pack(side=tk.LEFT)
        
        # Three efficiency column headers (RIGHT to LEFT order for pack)
        tk.Label(header_row, text="Frag", background="#E8F5E9", 
                font=("Arial", 7, "bold"), foreground="#9932CC", width=7, anchor=tk.E).pack(side=tk.RIGHT, padx=(2, 3))
        tk.Label(header_row, text="XP", background="#E8F5E9", 
                font=("Arial", 7, "bold"), foreground="#1976D2", width=7, anchor=tk.E).pack(side=tk.RIGHT, padx=(2, 0))
        tk.Label(header_row, text="Stage", background="#E8F5E9", 
                font=("Arial", 7, "bold"), foreground="#2E7D32", width=7, anchor=tk.E).pack(side=tk.RIGHT, padx=(2, 0))
        
        # Colors for each fragment type
        type_colors = {
            'common': '#808080',    # Gray
            'rare': '#4169E1',      # Blue
            'epic': '#9932CC',      # Purple
            'legendary': '#FFD700', # Gold
            'mythic': '#FF4500',    # Orange
        }
        
        # Group upgrades by cost_type
        upgrades_by_type = {'common': [], 'rare': [], 'epic': [], 'legendary': [], 'mythic': []}
        
        for upgrade_key, upgrade_info in self.FRAGMENT_UPGRADES.items():
            stage_required = upgrade_info.get('stage_unlock', 0)
            if unlocked_stage >= stage_required:
                cost_type = upgrade_info.get('cost_type', 'common')
                upgrades_by_type[cost_type].append((upgrade_key, upgrade_info))
        
        # Create widgets for each type that has unlocked upgrades
        for cost_type in ['common', 'rare', 'epic', 'legendary', 'mythic']:
            upgrades = upgrades_by_type[cost_type]
            if not upgrades:
                continue
            
            # Type header
            header_frame = tk.Frame(self.upgrades_container, background="#E8F5E9")
            header_frame.pack(fill=tk.X, pady=(3, 1))
            
            # Fragment icon if available
            if cost_type in self.fragment_icons:
                tk.Label(header_frame, image=self.fragment_icons[cost_type], 
                        background="#E8F5E9").pack(side=tk.LEFT, padx=(0, 3))
            
            tk.Label(header_frame, text=f"{cost_type.capitalize()}", 
                    font=("Arial", 8, "bold"), foreground=type_colors[cost_type],
                    background="#E8F5E9").pack(side=tk.LEFT)
            
            # Create row for each upgrade
            for upgrade_key, upgrade_info in upgrades:
                self._create_upgrade_row(upgrade_key, upgrade_info, type_colors[cost_type])
    
    def _create_upgrade_row(self, upgrade_key, upgrade_info, color):
        """Create a single upgrade row widget with three efficiency columns"""
        row_frame = tk.Frame(self.upgrades_container, background="#E8F5E9")
        row_frame.pack(fill=tk.X, pady=1)
        
        # Initialize level if not exists
        if upgrade_key not in self.fragment_upgrade_levels:
            self.fragment_upgrade_levels[upgrade_key] = 0
        
        minus_btn = tk.Button(row_frame, text="-", width=2, font=("Arial", 8, "bold"),
                             command=lambda u=upgrade_key: self._remove_fragment_upgrade(u))
        minus_btn.pack(side=tk.LEFT, padx=(0, 1))
        
        plus_btn = tk.Button(row_frame, text="+", width=2, font=("Arial", 8, "bold"),
                            command=lambda u=upgrade_key: self._add_fragment_upgrade(u))
        plus_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        # Level counter with max level (e.g. "5/25")
        current_level = self.fragment_upgrade_levels.get(upgrade_key, 0)
        max_level = upgrade_info.get('max_level', 25)
        level_label = tk.Label(row_frame, text=f"{current_level}/{max_level}", background="#E8F5E9", 
                              font=("Arial", 8), foreground=color, width=5, anchor=tk.CENTER)
        level_label.pack(side=tk.LEFT, padx=(0, 3))
        self.upgrade_level_labels[upgrade_key] = level_label
        
        # Display name
        display_name = upgrade_info.get('display_name', upgrade_key)
        tk.Label(row_frame, text=display_name, background="#E8F5E9", 
                font=("Arial", 8), width=14, anchor=tk.W).pack(side=tk.LEFT)
        
        # Help ? label with tooltip (includes stage unlock info)
        help_label = tk.Label(row_frame, text="?", background="#E8F5E9",
                             font=("Arial", 7, "bold"), foreground="#888888", cursor="hand2")
        help_label.pack(side=tk.LEFT, padx=(0, 2))
        self._create_fragment_upgrade_tooltip(help_label, upgrade_key, upgrade_info, color)
        
        # Three efficiency columns from RIGHT to LEFT (pack order matters)
        # Fragment Farming efficiency (rightmost)
        frag_eff_label = tk.Label(row_frame, text="+0.00%", background="#E8F5E9",
                                 font=("Arial", 8), foreground="#9932CC", width=7, anchor=tk.E)
        frag_eff_label.pack(side=tk.RIGHT, padx=(2, 3))
        self.upgrade_frag_efficiency_labels[upgrade_key] = frag_eff_label
        
        # XP efficiency (middle)
        xp_eff_label = tk.Label(row_frame, text="+0.00%", background="#E8F5E9",
                               font=("Arial", 8), foreground="#1976D2", width=7, anchor=tk.E)
        xp_eff_label.pack(side=tk.RIGHT, padx=(2, 0))
        self.upgrade_xp_efficiency_labels[upgrade_key] = xp_eff_label
        
        # Stage Rush efficiency (floors/run) - leftmost of the three
        eff_label = tk.Label(row_frame, text="+0.00%", background="#E8F5E9",
                            font=("Arial", 8), foreground="#2E7D32", width=7, anchor=tk.E)
        eff_label.pack(side=tk.RIGHT, padx=(2, 0))
        self.upgrade_efficiency_labels[upgrade_key] = eff_label
        
        self.upgrade_buttons[upgrade_key] = (minus_btn, plus_btn)
    
    def _add_fragment_upgrade(self, upgrade_key):
        """Add a level to a fragment upgrade"""
        if upgrade_key not in self.fragment_upgrade_levels:
            self.fragment_upgrade_levels[upgrade_key] = 0
        
        max_level = self.FRAGMENT_UPGRADES[upgrade_key].get('max_level', 25)
        if self.fragment_upgrade_levels[upgrade_key] < max_level:
            self.fragment_upgrade_levels[upgrade_key] += 1
            # Update the label directly with level/max format
            if upgrade_key in self.upgrade_level_labels:
                self.upgrade_level_labels[upgrade_key].config(
                    text=f"{self.fragment_upgrade_levels[upgrade_key]}/{max_level}")
            self.update_display()
    
    def _remove_fragment_upgrade(self, upgrade_key):
        """Remove a level from a fragment upgrade"""
        if upgrade_key not in self.fragment_upgrade_levels:
            self.fragment_upgrade_levels[upgrade_key] = 0
        
        max_level = self.FRAGMENT_UPGRADES[upgrade_key].get('max_level', 25)
        if self.fragment_upgrade_levels[upgrade_key] > 0:
            self.fragment_upgrade_levels[upgrade_key] -= 1
            # Update the label directly with level/max format
            if upgrade_key in self.upgrade_level_labels:
                self.upgrade_level_labels[upgrade_key].config(
                    text=f"{self.fragment_upgrade_levels[upgrade_key]}/{max_level}")
            self.update_display()
    
    def _create_fragment_upgrade_tooltip(self, widget, upgrade_key, upgrade_info, color):
        """Creates a tooltip for a fragment upgrade showing details and current bonuses"""
        
        # Map bonus keys to human-readable descriptions
        bonus_descriptions = {
            'flat_damage': ('Flat Damage', '+{:.0f}', ''),
            'armor_pen': ('Armor Penetration', '+{:.0f}', ''),
            'crit_chance': ('Crit Chance', '+{:.2f}', '%'),
            'crit_damage': ('Crit Damage', '+{:.0f}', '%'),
            'super_crit_chance': ('Super Crit Chance', '+{:.2f}', '%'),
            'super_crit_damage': ('Super Crit Damage', '+{:.0f}', '%'),
            'ultra_crit_chance': ('Ultra Crit Chance', '+{:.1f}', '%'),
            'max_stamina': ('Max Stamina', '+{:.0f}', ''),
            'max_stamina_percent': ('Max Stamina', '+{:.0f}', '%'),
            'stamina_mod_chance': ('Stamina Mod Chance', '+{:.2f}', '%'),
            'stamina_mod_gain': ('Stamina Mod Bonus', '+{:.1f}', ''),
            'arch_xp_bonus': ('Archaeology Exp', '+{:.0f}', '%'),
            'xp_bonus_skill': ('XP per INT point', '+{:.0f}', '%'),
            'xp_bonus_mult': ('XP Multiplier', '{:.1f}', 'x'),
            'fragment_gain': ('Fragment Gain', '+{:.0f}', '%'),
            'fragment_gain_mult': ('Fragment Multiplier', '{:.2f}', 'x'),
            'exp_mod_chance': ('Exp Mod Chance', '+{:.2f}', '%'),
            'exp_mod_gain': ('Exp Mod Bonus', '+{:.2f}', 'x'),
            'loot_mod_multiplier': ('Loot Mod Bonus', '+{:.2f}', 'x'),
            'all_mod_chance': ('All Mod Chances', '+{:.2f}', '%'),
            'mod_chance_skill': ('Mod Chance per skill pt', '+{:.2f}', '%'),
            'percent_damage': ('Percent Damage', '+{:.0f}', '%'),
            'flat_damage_skill': ('Flat Dmg per STR pt', '+{:.1f}', ''),
            'percent_damage_skill': ('% Dmg per STR pt', '+{:.1f}', '%'),
            'armor_pen_skill': ('Armor Pen per PER pt', '+{:.0f}', ''),
            'armor_pen_percent': ('Armor Pen %', '+{:.0f}', '%'),
            'max_stamina_skill': ('Stamina per AGI pt', '+{:.0f}', ''),
            'enrage_damage': ('Enrage Damage', '+{:.0f}', '%'),
            'enrage_crit_damage': ('Enrage Crit Damage', '+{:.0f}', '%'),
            'enrage_cooldown': ('Enrage Cooldown', '{:.0f}', 's'),
            'flurry_stamina': ('Flurry Stamina', '+{:.0f}', ''),
            'flurry_cooldown': ('Flurry Cooldown', '{:.0f}', 's'),
            'flurry_stamina': ('Flurry Stamina Cost', '-{:.0f}', ''),
            'flurry_cooldown': ('Flurry Cooldown', '{:.0f}', 's'),
            'quake_attacks': ('Quake Extra Attacks', '+{:.0f}', ''),
            'quake_cooldown': ('Quake Cooldown', '{:.0f}', 's'),
            'ability_cooldown': ('Ability Cooldown', '{:.0f}', 's'),
            'ability_instacharge': ('Ability Insta-Charge', '+{:.2f}', '%'),
            'polychrome_bonus': ('Polychrome Bonus', '+{:.0f}', '%'),
            'all_stat_cap': ('All Stat Caps', '+{:.0f}', ''),
        }
        
        # Type colors for border
        type_colors = {
            'common': '#808080',
            'rare': '#4169E1',
            'epic': '#9932CC',
            'legendary': '#FFD700',
            'mythic': '#FF4500',
        }
        
        def on_enter(event):
            current_level = self.fragment_upgrade_levels.get(upgrade_key, 0)
            max_level = upgrade_info.get('max_level', 25)
            cost_type = upgrade_info.get('cost_type', 'common')
            display_name = upgrade_info.get('display_name', upgrade_key)
            stage_unlock = upgrade_info.get('stage_unlock', 0)
            border_color = type_colors.get(cost_type, '#808080')
            
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
            
            # Title with icon
            title_frame = tk.Frame(content_frame, background="#FFFFFF")
            title_frame.pack(anchor=tk.W)
            
            # Try to load fragment icon
            try:
                icon_name = f"fragment{cost_type}.png"
                icon_path = get_resource_path(f"sprites/archaeology/{icon_name}")
                if icon_path.exists():
                    icon_image = Image.open(icon_path)
                    icon_image = icon_image.resize((16, 16), Image.Resampling.LANCZOS)
                    tooltip.icon_photo = ImageTk.PhotoImage(icon_image)
                    tk.Label(title_frame, image=tooltip.icon_photo, background="#FFFFFF").pack(side=tk.LEFT, padx=(0, 5))
            except:
                pass
            
            tk.Label(title_frame, text=f"{cost_type.capitalize()}: {display_name}", 
                    font=("Arial", 10, "bold"), foreground=border_color, 
                    background="#FFFFFF").pack(side=tk.LEFT)
            
            # Stage unlock
            if stage_unlock > 0:
                tk.Label(content_frame, text=f"Unlocks at Stage {stage_unlock}", 
                        font=("Arial", 8), foreground="#999999",
                        background="#FFFFFF").pack(anchor=tk.W)
            
            # Effects per level
            tk.Label(content_frame, text="Per Level:", 
                    font=("Arial", 9, "bold"), background="#FFFFFF").pack(anchor=tk.W, pady=(5, 2))
            
            for bonus_key, bonus_value in upgrade_info.items():
                if bonus_key in ('max_level', 'stage_unlock', 'cost_type', 'display_name'):
                    continue
                
                if bonus_key in bonus_descriptions:
                    name, fmt, suffix = bonus_descriptions[bonus_key]
                    # Handle percentage display (multiply by 100 for chances)
                    if 'chance' in bonus_key or bonus_key in ('percent_damage', 'crit_damage', 'super_crit_damage', 
                            'arch_xp_bonus', 'fragment_gain', 'enrage_damage', 'enrage_crit_damage',
                            'armor_pen_percent', 'max_stamina_percent', 'xp_bonus_skill', 'percent_damage_skill',
                            'polychrome_bonus', 'ability_instacharge', 'mod_chance_skill'):
                        display_value = bonus_value * 100
                    else:
                        display_value = bonus_value
                    value_str = fmt.format(display_value) + suffix
                    tk.Label(content_frame, text=f"  • {name}: {value_str}", 
                            font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W)
                else:
                    # Fallback for unknown bonuses
                    tk.Label(content_frame, text=f"  • {bonus_key}: {bonus_value}", 
                            font=("Arial", 9), background="#FFFFFF").pack(anchor=tk.W)
            
            # Current level and total bonus
            tk.Label(content_frame, text=f"\nLevel: {current_level} / {max_level}", 
                    font=("Arial", 9, "bold"), background="#FFFFFF").pack(anchor=tk.W)
            
            # Current total bonuses
            if current_level > 0:
                tk.Label(content_frame, text="Current Total:", 
                        font=("Arial", 9, "bold"), foreground="#2E7D32",
                        background="#FFFFFF").pack(anchor=tk.W, pady=(3, 2))
                
                for bonus_key, bonus_value in upgrade_info.items():
                    if bonus_key in ('max_level', 'stage_unlock', 'cost_type', 'display_name'):
                        continue
                    
                    total_value = bonus_value * current_level
                    if bonus_key in bonus_descriptions:
                        name, fmt, suffix = bonus_descriptions[bonus_key]
                        if 'chance' in bonus_key or bonus_key in ('percent_damage', 'crit_damage', 'super_crit_damage', 
                                'arch_xp_bonus', 'fragment_gain', 'enrage_damage', 'enrage_crit_damage',
                                'armor_pen_percent', 'max_stamina_percent', 'xp_bonus_skill', 'percent_damage_skill',
                                'polychrome_bonus', 'ability_instacharge', 'mod_chance_skill'):
                            display_value = total_value * 100
                        else:
                            display_value = total_value
                        value_str = fmt.format(display_value) + suffix
                        tk.Label(content_frame, text=f"  • {name}: {value_str}", 
                                font=("Arial", 9), foreground="#2E7D32",
                                background="#FFFFFF").pack(anchor=tk.W)
            
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
                icon_path = get_resource_path("sprites/archaeology/fragmentcommon.png")
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
    
    def _create_unlocked_stage_help_tooltip(self, widget):
        """Creates a tooltip explaining the Unlocked Stage input"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 320
            tooltip_height = 320
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
            tk.Label(content_frame, text="Unlocked Stage", 
                    font=("Arial", 11, "bold"), foreground="#1976D2", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()  # Spacer
            
            # Explanation
            lines = [
                "Enter your highest unlocked stage to filter",
                "which fragment upgrades are available.",
                "",
                "Many upgrades unlock at specific stages:",
                "",
                "  Stage 2: Armor Pen (Common)",
                "  Stage 3: Exp Gain +2% (Common)",
                "  Stage 4: Crit Chance/Dmg (Common)",
                "  Stage 5: Stamina (Rare)",
                "  Stage 6: Flat Dmg +2, Loot Mod (Rare)",
                "  Stage 9+: Epic upgrades",
                "  Stage 17+: Legendary upgrades",
                "  Stage 26+: Mythic upgrades",
                "",
                "The upgrades list will only show",
                "upgrades you can actually buy!",
            ]
            
            for line in lines:
                tk.Label(content_frame, text=line, 
                        font=("Arial", 9), background="#FFFFFF",
                        anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _create_crit_toggle_help_tooltip(self, widget):
        """Creates a tooltip explaining the Crit toggle for deterministic vs crit-based calculations"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 360
            tooltip_height = 280
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Outer frame for shadow effect
            outer_frame = tk.Frame(tooltip, background="#9932CC", relief=tk.FLAT, borderwidth=0)
            outer_frame.pack(padx=2, pady=2)
            
            # Inner frame
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF", relief=tk.FLAT, borderwidth=0)
            inner_frame.pack(padx=1, pady=1)
            
            content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=12, pady=10)
            content_frame.pack()
            
            # Title
            tk.Label(content_frame, text="Crit Calculation Mode", 
                    font=("Arial", 11, "bold"), foreground="#9932CC", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()  # Spacer
            
            # Explanation
            lines = [
                "Use Monte Carlo (MC) simulation to determine",
                "whether to enable Crit or not!",
                "",
                "The MC tool compares your build with and",
                "without crit mechanics, using optimal skill",
                "distributions for each mode.",
                "",
                "Use 'MC Stage Pusher' to run Monte Carlo",
                "simulations and see stage distribution.",
                "",
                "OFF = Deterministic (no crit averaging)",
                "ON  = Crit-based (includes crit in calculations)",
            ]
            
            for line in lines:
                tk.Label(content_frame, text=line, 
                        font=("Arial", 9), background="#FFFFFF",
                        anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W)
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _on_unlocked_stage_changed(self, *args):
        """Called when unlocked stage input changes"""
        try:
            unlocked = int(self.unlocked_stage_var.get())
            # Clamp to valid range
            unlocked = max(1, min(50, unlocked))
            self.unlocked_stage = unlocked
            # Rebuild upgrade widgets to show/hide based on new stage
            if hasattr(self, 'upgrades_container'):
                self._rebuild_upgrade_widgets()
            self.update_display()
        except ValueError:
            # Invalid input, ignore
            pass
    
    def _increase_unlocked_stage(self):
        """Increase unlocked stage by 1"""
        try:
            current = int(self.unlocked_stage_var.get())
            new_val = min(50, current + 1)
            self.unlocked_stage_var.set(str(new_val))
        except ValueError:
            self.unlocked_stage_var.set("1")
    
    def _decrease_unlocked_stage(self):
        """Decrease unlocked stage by 1"""
        try:
            current = int(self.unlocked_stage_var.get())
            new_val = max(1, current - 1)
            self.unlocked_stage_var.set(str(new_val))
        except ValueError:
            self.unlocked_stage_var.set("1")
    
    def get_unlocked_stage(self):
        """Get the current unlocked stage value"""
        try:
            return int(self.unlocked_stage_var.get())
        except (ValueError, AttributeError):
            return 1
    
    def is_upgrade_unlocked(self, upgrade_key):
        """Check if a fragment upgrade is unlocked based on current stage"""
        if upgrade_key in self.FRAGMENT_UPGRADES:
            stage_required = self.FRAGMENT_UPGRADES[upgrade_key].get('stage_unlock', 0)
            return self.get_unlocked_stage() >= stage_required
        return True  # Non-fragment upgrades are always available
    
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
                "• Crit Dmg: Base 1.5× × (1 + STR×3%)",
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
                "• INT: +5% XP Mult, +0.3% Exp Mod, +3% Armor Pen",
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
                    ('+3% Crit Damage', 'Multiplies base crit (1.5× × 1.03 per STR)'),
                ],
                'example': 'At 10 STR: +10 flat dmg, +10% dmg, 1.5×1.30=1.95× crit',
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
                    ('+3% Armor Pen', 'Multiplies total armor pen (rounds up)'),
                ],
                'example': 'At 10 INT: +50% XP, +3% exp mod, 1.30× armor pen',
                'tip': 'Best for: Leveling + armor pen scaling. Helps floors/run via pen!',
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
        
        # === LEVEL UP TIMER SECTION ===
        levelup_header = tk.Frame(col_frame, background="#E8F5E9")
        levelup_header.pack(fill=tk.X, padx=5)
        
        tk.Label(levelup_header, text="Level Up Timer", font=("Arial", 9, "bold"), 
                background="#E8F5E9").pack(side=tk.LEFT)
        
        levelup_help = tk.Label(levelup_header, text="?", font=("Arial", 8, "bold"), 
                               cursor="hand2", foreground="#2E7D32", background="#E8F5E9")
        levelup_help.pack(side=tk.LEFT, padx=(5, 0))
        self._create_levelup_help_tooltip(levelup_help)
        
        levelup_frame = tk.Frame(col_frame, background="#E8F5E9")
        levelup_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Row 1: XP/Run and Run Duration
        levelup_row1 = tk.Frame(levelup_frame, background="#E8F5E9")
        levelup_row1.pack(fill=tk.X)
        
        tk.Label(levelup_row1, text="XP/Run:", font=("Arial", 8), 
                background="#E8F5E9").pack(side=tk.LEFT)
        self.xp_per_run_label = tk.Label(levelup_row1, text="—", 
                                        font=("Arial", 8, "bold"), 
                                        background="#E8F5E9", foreground="#2E7D32")
        self.xp_per_run_label.pack(side=tk.LEFT, padx=(2, 10))
        
        tk.Label(levelup_row1, text="Run:", font=("Arial", 8), 
                background="#E8F5E9").pack(side=tk.LEFT)
        self.run_duration_label = tk.Label(levelup_row1, text="—", 
                                          font=("Arial", 8, "bold"), 
                                          background="#E8F5E9", foreground="#1976D2")
        self.run_duration_label.pack(side=tk.LEFT, padx=(2, 10))
        
        tk.Label(levelup_row1, text="XP/h:", font=("Arial", 8), 
                background="#E8F5E9").pack(side=tk.LEFT)
        self.xp_per_hour_label = tk.Label(levelup_row1, text="—", 
                                         font=("Arial", 8, "bold"), 
                                         background="#E8F5E9", foreground="#9932CC")
        self.xp_per_hour_label.pack(side=tk.LEFT, padx=(2, 0))
        
        # Row 2: XP needed input and time to level
        levelup_row2 = tk.Frame(levelup_frame, background="#E8F5E9")
        levelup_row2.pack(fill=tk.X, pady=(3, 0))
        
        tk.Label(levelup_row2, text="XP needed:", font=("Arial", 8), 
                background="#E8F5E9").pack(side=tk.LEFT)
        
        self.xp_needed_var = tk.StringVar(value="")
        xp_needed_entry = tk.Entry(levelup_row2, textvariable=self.xp_needed_var, 
                                  width=8, font=("Arial", 8))
        xp_needed_entry.pack(side=tk.LEFT, padx=(2, 5))
        xp_needed_entry.bind('<KeyRelease>', lambda e: self.update_levelup_time())
        
        tk.Label(levelup_row2, text="→", font=("Arial", 8), 
                background="#E8F5E9").pack(side=tk.LEFT)
        
        self.time_to_level_label = tk.Label(levelup_row2, text="—", 
                                           font=("Arial", 9, "bold"), 
                                           background="#E8F5E9", foreground="#C73E1D")
        self.time_to_level_label.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # === FRAGMENTS PER HOUR SECTION ===
        frag_hour_header = tk.Frame(col_frame, background="#F3E5F5")
        frag_hour_header.pack(fill=tk.X, padx=5)
        
        tk.Label(frag_hour_header, text="Fragments / Hour", font=("Arial", 10, "bold"), 
                background="#F3E5F5", foreground="#7B1FA2").pack(side=tk.LEFT)
        
        frag_help_label = tk.Label(frag_hour_header, text="?", font=("Arial", 9, "bold"), 
                                  cursor="hand2", foreground="#7B1FA2", background="#F3E5F5")
        frag_help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_fragments_hour_help_tooltip(frag_help_label)
        
        # Fragments per hour container
        frag_hour_frame = tk.Frame(col_frame, background="#F3E5F5", relief=tk.GROOVE, borderwidth=1)
        frag_hour_frame.pack(fill=tk.X, padx=5, pady=(3, 5))
        
        frag_hour_inner = tk.Frame(frag_hour_frame, background="#F3E5F5", padx=8, pady=5)
        frag_hour_inner.pack(fill=tk.X)
        
        # Total fragments per run/hour
        total_row = tk.Frame(frag_hour_inner, background="#F3E5F5")
        total_row.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(total_row, text="Total Frags/Run:", font=("Arial", 9, "bold"), 
                background="#F3E5F5").pack(side=tk.LEFT)
        self.frags_per_run_label = tk.Label(total_row, text="—", font=("Arial", 9, "bold"),
                                           background="#F3E5F5", foreground="#7B1FA2")
        self.frags_per_run_label.pack(side=tk.LEFT, padx=(5, 15))
        
        tk.Label(total_row, text="Frags/Hour:", font=("Arial", 9, "bold"), 
                background="#F3E5F5").pack(side=tk.LEFT)
        self.frags_per_hour_label = tk.Label(total_row, text="—", font=("Arial", 9, "bold"),
                                            background="#F3E5F5", foreground="#9932CC")
        self.frags_per_hour_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Fragment breakdown by type
        self.frag_hour_labels = {}
        
        # Header row
        header_row = tk.Frame(frag_hour_inner, background="#F3E5F5")
        header_row.pack(fill=tk.X, pady=(3, 2))
        
        tk.Label(header_row, text="Type", font=("Arial", 8, "bold"), 
                background="#F3E5F5", width=10, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(header_row, text="/Run", font=("Arial", 8, "bold"), 
                background="#F3E5F5", width=8, anchor=tk.E).pack(side=tk.LEFT)
        tk.Label(header_row, text="/Hour", font=("Arial", 8, "bold"), 
                background="#F3E5F5", width=8, anchor=tk.E).pack(side=tk.LEFT)
        
        # Fragment types (common, rare, epic, legendary, mythic - no dirt)
        frag_types = ['common', 'rare', 'epic', 'legendary', 'mythic']
        type_colors = {
            'common': '#808080',    # Gray
            'rare': '#4169E1',      # Blue  
            'epic': '#9932CC',      # Purple
            'legendary': '#FFD700', # Gold
            'mythic': '#FF4500',    # Orange
        }
        
        for frag_type in frag_types:
            row = tk.Frame(frag_hour_inner, background="#F3E5F5")
            row.pack(fill=tk.X, pady=1)
            
            color = type_colors.get(frag_type, '#888888')
            
            # Fragment icon if available
            if hasattr(self, 'fragment_icons') and frag_type in self.fragment_icons:
                tk.Label(row, image=self.fragment_icons[frag_type], 
                        background="#F3E5F5").pack(side=tk.LEFT, padx=(0, 3))
            
            tk.Label(row, text=f"{frag_type.capitalize()}", font=("Arial", 8, "bold"),
                    foreground="#333333", background="#F3E5F5", width=8, anchor=tk.W).pack(side=tk.LEFT)
            
            per_run_label = tk.Label(row, text="—", font=("Arial", 8),
                                    background="#F3E5F5", foreground="#555555", width=8, anchor=tk.E)
            per_run_label.pack(side=tk.LEFT)
            
            per_hour_label = tk.Label(row, text="—", font=("Arial", 8, "bold"),
                                     background="#F3E5F5", foreground="#333333", width=8, anchor=tk.E)
            per_hour_label.pack(side=tk.LEFT)
            
            self.frag_hour_labels[frag_type] = {
                'per_run': per_run_label,
                'per_hour': per_hour_label,
            }
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # === STAGE RUSHING FORECASTER ===
        forecast_header = tk.Frame(col_frame, background="#FFF3E0")
        forecast_header.pack(fill=tk.X, padx=5)
        
        tk.Label(forecast_header, text="Stage Rushing Forecaster", font=("Arial", 10, "bold"), 
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
        
        # === SHARED PLANNER POINTS ===
        # All planners (except Forecaster) share the same point value
        shared_points_header = tk.Frame(col_frame, background="#FFF3E0")
        shared_points_header.pack(fill=tk.X, padx=5, pady=(0, 3))
        
        tk.Label(shared_points_header, text="Planner Points (shared):", font=("Arial", 9, "bold"), 
                background="#FFF3E0", foreground="#7B1FA2").pack(side=tk.LEFT)
        
        # Shared points adjuster
        shared_points_frame = tk.Frame(shared_points_header, background="#FFF3E0")
        shared_points_frame.pack(side=tk.LEFT, padx=(8, 0))
        
        # Initialize shared planner points variable
        self.shared_planner_points = tk.IntVar(value=20)
        
        tk.Button(shared_points_frame, text="-5", width=2, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_shared_planner_points(-5)).pack(side=tk.LEFT)
        tk.Button(shared_points_frame, text="-", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_shared_planner_points(-1)).pack(side=tk.LEFT)
        self.shared_planner_points_label = tk.Label(shared_points_frame, text="20", font=("Arial", 11, "bold"), 
                                                     background="#FFF3E0", foreground="#7B1FA2", width=4)
        self.shared_planner_points_label.pack(side=tk.LEFT)
        tk.Button(shared_points_frame, text="+", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_shared_planner_points(1)).pack(side=tk.LEFT)
        tk.Button(shared_points_frame, text="+5", width=2, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_shared_planner_points(5)).pack(side=tk.LEFT)
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # === STAGE RUSHER PLANNER SECTION ===
        budget_header = tk.Frame(col_frame, background="#FFF3E0")
        budget_header.pack(fill=tk.X, padx=5)
        
        tk.Label(budget_header, text="Stage Rusher Planner", font=("Arial", 10, "bold"), 
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
        
        # Budget uses shared planner points (no separate input)
        
        # Header row for results
        header_row = tk.Frame(budget_inner, background="#F3E5F5", padx=5)
        header_row.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(header_row, text="Distribution", font=("Arial", 8, "bold"), 
                background="#F3E5F5", width=14, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(header_row, text="Stage/h", font=("Arial", 8, "bold"), 
                background="#F3E5F5", width=6, anchor=tk.E).pack(side=tk.LEFT)
        tk.Label(header_row, text="XP/h", font=("Arial", 8, "bold"), 
                background="#F3E5F5", width=7, anchor=tk.E).pack(side=tk.LEFT)
        tk.Label(header_row, text="Gain", font=("Arial", 8, "bold"), 
                background="#F3E5F5", anchor=tk.E).pack(side=tk.RIGHT)
        
        # Result row
        result_row = tk.Frame(budget_inner, background="#E1BEE7")
        result_row.pack(fill=tk.X, pady=(3, 0))
        
        result_inner = tk.Frame(result_row, background="#E1BEE7", padx=5, pady=4)
        result_inner.pack(fill=tk.X)
        
        self.budget_dist_label = tk.Label(result_inner, text="—", font=("Arial", 10, "bold"), 
                                         background="#E1BEE7", foreground="#333333", 
                                         width=14, anchor=tk.W)
        self.budget_dist_label.pack(side=tk.LEFT)
        self.budget_floors_label = tk.Label(result_inner, text="—", font=("Arial", 10, "bold"), 
                                           background="#E1BEE7", foreground="#333333", 
                                           width=6, anchor=tk.E)
        self.budget_floors_label.pack(side=tk.LEFT)
        self.budget_xp_label = tk.Label(result_inner, text="—", font=("Arial", 10, "bold"), 
                                       background="#E1BEE7", foreground="#333333", 
                                       width=7, anchor=tk.E)
        self.budget_xp_label.pack(side=tk.LEFT)
        self.budget_gain_label = tk.Label(result_inner, text="—", font=("Arial", 10, "bold"), 
                                         background="#E1BEE7", foreground="#2E7D32", anchor=tk.E)
        self.budget_gain_label.pack(side=tk.RIGHT)
        
        # Frags/h row (shows selected fragment type from Fragment Farm Planner)
        budget_frag_row = tk.Frame(budget_inner, background="#F3E5F5")
        budget_frag_row.pack(fill=tk.X, pady=(3, 0))
        
        self.budget_frag_icon_label = tk.Label(budget_frag_row, background="#F3E5F5")
        self.budget_frag_icon_label.pack(side=tk.LEFT, padx=(0, 3))
        self.budget_frag_type_label = tk.Label(budget_frag_row, text="Frags/h:", font=("Arial", 8, "bold"), 
                                              background="#F3E5F5", foreground="#7B1FA2")
        self.budget_frag_type_label.pack(side=tk.LEFT)
        self.budget_frag_value_label = tk.Label(budget_frag_row, text="—", font=("Arial", 9, "bold"), 
                                               background="#F3E5F5", foreground="#7B1FA2")
        self.budget_frag_value_label.pack(side=tk.LEFT, padx=(5, 0))
        
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
        
        # XP Budget uses shared planner points (no separate input)
        
        # Header row for results
        xp_header_row = tk.Frame(xp_budget_inner, background="#B2EBF2", padx=5)
        xp_header_row.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(xp_header_row, text="Distribution", font=("Arial", 8, "bold"), 
                background="#B2EBF2", width=14, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(xp_header_row, text="Stage/h", font=("Arial", 8, "bold"), 
                background="#B2EBF2", width=6, anchor=tk.E).pack(side=tk.LEFT)
        tk.Label(xp_header_row, text="XP/h", font=("Arial", 8, "bold"), 
                background="#B2EBF2", width=7, anchor=tk.E).pack(side=tk.LEFT)
        tk.Label(xp_header_row, text="Gain", font=("Arial", 8, "bold"), 
                background="#B2EBF2", anchor=tk.E).pack(side=tk.RIGHT)
        
        # Result row
        xp_result_row = tk.Frame(xp_budget_inner, background="#80DEEA")
        xp_result_row.pack(fill=tk.X, pady=(3, 0))
        
        xp_result_inner = tk.Frame(xp_result_row, background="#80DEEA", padx=5, pady=4)
        xp_result_inner.pack(fill=tk.X)
        
        self.xp_budget_dist_label = tk.Label(xp_result_inner, text="—", font=("Arial", 10, "bold"), 
                                            background="#80DEEA", foreground="#333333", 
                                            width=14, anchor=tk.W)
        self.xp_budget_dist_label.pack(side=tk.LEFT)
        self.xp_budget_floors_label = tk.Label(xp_result_inner, text="—", font=("Arial", 10, "bold"), 
                                              background="#80DEEA", foreground="#333333", 
                                              width=6, anchor=tk.E)
        self.xp_budget_floors_label.pack(side=tk.LEFT)
        self.xp_budget_xp_label = tk.Label(xp_result_inner, text="—", font=("Arial", 10, "bold"), 
                                          background="#80DEEA", foreground="#333333", 
                                          width=7, anchor=tk.E)
        self.xp_budget_xp_label.pack(side=tk.LEFT)
        self.xp_budget_gain_label = tk.Label(xp_result_inner, text="—", font=("Arial", 10, "bold"), 
                                            background="#80DEEA", foreground="#2E7D32", anchor=tk.E)
        self.xp_budget_gain_label.pack(side=tk.RIGHT)
        
        # Frags/h row (shows selected fragment type from Fragment Farm Planner)
        xp_budget_frag_row = tk.Frame(xp_budget_inner, background="#B2EBF2")
        xp_budget_frag_row.pack(fill=tk.X, pady=(3, 0))
        
        self.xp_budget_frag_icon_label = tk.Label(xp_budget_frag_row, background="#B2EBF2")
        self.xp_budget_frag_icon_label.pack(side=tk.LEFT, padx=(0, 3))
        self.xp_budget_frag_type_label = tk.Label(xp_budget_frag_row, text="Frags/h:", font=("Arial", 8, "bold"), 
                                                 background="#B2EBF2", foreground="#7B1FA2")
        self.xp_budget_frag_type_label.pack(side=tk.LEFT)
        self.xp_budget_frag_value_label = tk.Label(xp_budget_frag_row, text="—", font=("Arial", 9, "bold"), 
                                                  background="#B2EBF2", foreground="#7B1FA2")
        self.xp_budget_frag_value_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Detailed breakdown row
        xp_breakdown_row = tk.Frame(xp_budget_inner, background="#B2EBF2")
        xp_breakdown_row.pack(fill=tk.X, pady=(3, 0))
        
        tk.Label(xp_breakdown_row, text="Details:", font=("Arial", 7), 
                background="#B2EBF2", foreground="#555555").pack(side=tk.LEFT)
        self.xp_budget_breakdown_label = tk.Label(xp_breakdown_row, text="—", font=("Arial", 8), 
                                                 background="#B2EBF2", foreground="#333333")
        self.xp_budget_breakdown_label.pack(side=tk.LEFT, padx=(3, 0))
        
        ttk.Separator(col_frame, orient='horizontal').pack(fill=tk.X, pady=5, padx=5)
        
        # === FRAGMENT FARM PLANNER ===
        frag_planner_header = tk.Frame(col_frame, background="#F3E5F5")
        frag_planner_header.pack(fill=tk.X, padx=5)
        
        tk.Label(frag_planner_header, text="Fragment Farm Planner", font=("Arial", 10, "bold"), 
                background="#F3E5F5", foreground="#7B1FA2").pack(side=tk.LEFT)
        
        frag_planner_help = tk.Label(frag_planner_header, text="?", font=("Arial", 9, "bold"), 
                                    cursor="hand2", foreground="#7B1FA2", background="#F3E5F5")
        frag_planner_help.pack(side=tk.LEFT, padx=(5, 0))
        self._create_frag_planner_help_tooltip(frag_planner_help)
        
        # Fragment planner frame
        frag_planner_frame = tk.Frame(col_frame, background="#EDE7F6", relief=tk.GROOVE, borderwidth=1)
        frag_planner_frame.pack(fill=tk.X, padx=5, pady=(3, 5))
        
        frag_planner_inner = tk.Frame(frag_planner_frame, background="#EDE7F6", padx=8, pady=5)
        frag_planner_inner.pack(fill=tk.X)
        
        # Target fragment type selection
        target_row = tk.Frame(frag_planner_inner, background="#EDE7F6")
        target_row.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(target_row, text="Target:", font=("Arial", 9, "bold"), 
                background="#EDE7F6").pack(side=tk.LEFT)
        
        self.frag_target_var = tk.StringVar(value="common")
        frag_types = ['common', 'rare', 'epic', 'legendary', 'mythic']
        type_colors = {
            'common': '#808080', 'rare': '#4169E1', 'epic': '#9932CC',
            'legendary': '#FFD700', 'mythic': '#FF4500'
        }
        
        self.frag_target_buttons = {}
        for frag_type in frag_types:
            color = type_colors.get(frag_type, '#888888')
            btn = tk.Label(target_row, text=frag_type[:3].upper(), font=("Arial", 8, "bold"),
                          foreground=color, background="#EDE7F6", cursor="hand2",
                          padx=4, relief=tk.RAISED, borderwidth=1)
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind("<Button-1>", lambda e, ft=frag_type: self._set_frag_target(ft))
            self.frag_target_buttons[frag_type] = btn
        
        # Fragment Planner uses shared planner points (no separate input)
        
        # Result row 1: Best distribution
        result_row1 = tk.Frame(frag_planner_inner, background="#EDE7F6")
        result_row1.pack(fill=tk.X, pady=2)
        
        tk.Label(result_row1, text="Best:", font=("Arial", 9), 
                background="#EDE7F6").pack(side=tk.LEFT)
        self.frag_planner_dist_label = tk.Label(result_row1, text="—", font=("Arial", 9, "bold"),
                                               background="#EDE7F6", foreground="#7B1FA2")
        self.frag_planner_dist_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Result row 2: Frags/h and Stages/Run
        result_row2 = tk.Frame(frag_planner_inner, background="#EDE7F6")
        result_row2.pack(fill=tk.X, pady=2)
        
        tk.Label(result_row2, text="Frags/h:", font=("Arial", 9), 
                background="#EDE7F6").pack(side=tk.LEFT)
        self.frag_planner_result_label = tk.Label(result_row2, text="—", font=("Arial", 9, "bold"),
                                                  background="#EDE7F6", foreground="#2E7D32")
        self.frag_planner_result_label.pack(side=tk.LEFT, padx=(3, 10))
        
        tk.Label(result_row2, text="Stage/h:", font=("Arial", 9), 
                background="#EDE7F6").pack(side=tk.LEFT)
        self.frag_planner_stages_label = tk.Label(result_row2, text="—", font=("Arial", 9, "bold"),
                                                  background="#EDE7F6", foreground="#1976D2")
        self.frag_planner_stages_label.pack(side=tk.LEFT, padx=(3, 0))
        
        # Result row 3: XP/h and Gain
        result_row3 = tk.Frame(frag_planner_inner, background="#EDE7F6")
        result_row3.pack(fill=tk.X, pady=2)
        
        tk.Label(result_row3, text="XP/h:", font=("Arial", 9), 
                background="#EDE7F6").pack(side=tk.LEFT)
        self.frag_planner_xp_label = tk.Label(result_row3, text="—", font=("Arial", 9, "bold"),
                                             background="#EDE7F6", foreground="#FF6F00")
        self.frag_planner_xp_label.pack(side=tk.LEFT, padx=(3, 10))
        
        tk.Label(result_row3, text="Gain:", font=("Arial", 9), 
                background="#EDE7F6", foreground="#555555").pack(side=tk.LEFT)
        self.frag_planner_gain_label = tk.Label(result_row3, text="—", font=("Arial", 9, "bold"),
                                               background="#EDE7F6", foreground="#2E7D32")
        self.frag_planner_gain_label.pack(side=tk.LEFT, padx=(3, 0))
        
        # Initialize target button highlight
        self._update_frag_target_buttons()
    
    def _set_frag_target(self, frag_type):
        """Set the target fragment type and recalculate all planners"""
        self.frag_target_var.set(frag_type)
        self._update_frag_target_buttons()
        # Update all planners since they show this fragment type
        self.update_budget_display()
    
    def _update_frag_target_buttons(self):
        """Update visual state of fragment target buttons"""
        current = self.frag_target_var.get()
        for frag_type, btn in self.frag_target_buttons.items():
            if frag_type == current:
                btn.config(relief=tk.SUNKEN, background="#D1C4E9")
            else:
                btn.config(relief=tk.RAISED, background="#EDE7F6")
    
    # Removed _adjust_frag_budget and _adjust_xp_budget - now using _adjust_shared_planner_points
    
    def _create_frag_planner_help_tooltip(self, widget):
        """Creates a tooltip explaining the Fragment Farm Planner feature"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 320
            tooltip_height = 340
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#7B1FA2", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content.pack()
            
            tk.Label(content, text="Fragment Farm Planner", font=("Arial", 10, "bold"),
                    background="#FFFFFF", foreground="#7B1FA2").pack(anchor="w")
            
            lines = [
                "",
                "Optimize skill points for fragment farming.",
                "",
                "Select your target fragment type, then see",
                "the optimal skill distribution to maximize",
                "that specific fragment's income per hour.",
                "",
                "Key stats for fragment farming:",
                "  - PER: +4% Fragment Multiplier",
                "  - PER: +0.3% Loot Mod Chance",
                "  - LUK: +0.2% Loot Mod Chance",
                "  - AGI/STR: More floors = more drops",
                "",
                "Different fragments may favor different",
                "builds depending on which blocks drop them.",
            ]
            
            for line in lines:
                tk.Label(content, text=line, font=("Arial", 9),
                        background="#FFFFFF", justify=tk.LEFT).pack(anchor="w")
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
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
    
    # Removed _adjust_budget - now using _adjust_shared_planner_points
    
    def _create_budget_help_tooltip(self, widget):
        """Creates a tooltip explaining the Stage Rusher Planner feature"""
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
            
            tk.Label(content_frame, text="Stage Rusher Planner", 
                    font=("Arial", 10, "bold"), foreground="#7B1FA2", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            lines = [
                "",
                "Plan how to spend a fixed pool of points.",
                "",
                "Unlike Forecast (which adds to current stats),",
                "Stage Rusher Planner helps when you have unspent",
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
    
    def _adjust_shared_planner_points(self, delta: int):
        """Adjust shared planner points (used by all planners except Forecaster)"""
        new_val = max(1, min(100, self.shared_planner_points.get() + delta))
        self.shared_planner_points.set(new_val)
        self.shared_planner_points_label.config(text=str(new_val))
        # Update all planners that use shared points
        self.update_budget_display()
        self.update_xp_budget_display()
        self.update_frag_planner_display()
    
    def _adjust_forecast_level(self, row: int, delta: int):
        """Adjust the forecast level and recalculate"""
        new_val = max(1, min(20, self.forecast_levels_1.get() + delta))
        self.forecast_levels_1.set(new_val)
        self.forecast_1_level_label.config(text=f"+{new_val}")
        self.update_forecast_display()
    
    def _create_forecast_help_tooltip(self, widget):
        """Creates a tooltip explaining the Stage Rushing Forecaster feature"""
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
            
            tk.Label(content_frame, text="Stage Rushing Forecaster", 
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
    
    def _create_fragments_hour_help_tooltip(self, widget):
        """Creates a tooltip explaining the Fragments/Hour feature"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 300
            tooltip_height = 280
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#7B1FA2", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content.pack()
            
            tk.Label(content, text="Fragments / Hour", font=("Arial", 10, "bold"),
                    background="#FFFFFF", foreground="#7B1FA2").pack(anchor="w")
            
            lines = [
                "",
                "Estimated fragment income per hour.",
                "",
                "Based on:",
                "  - Floors/Run × Blocks/Floor",
                "  - Block spawn rates per stage",
                "  - Fragment drop per block type",
                "  - Fragment multiplier (PER + upgrades)",
                "  - Loot Mod chance & bonus",
                "  - Run duration",
                "",
                "Use this to plan upgrade purchases",
                "and estimate farming time.",
            ]
            
            for line in lines:
                tk.Label(content, text=line, font=("Arial", 9),
                        background="#FFFFFF", justify=tk.LEFT).pack(anchor="w")
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _create_levelup_help_tooltip(self, widget):
        """Creates a tooltip explaining the Level Up Timer feature"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 300
            tooltip_height = 320
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#2E7D32", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content.pack()
            
            tk.Label(content, text="Level Up Timer", font=("Arial", 10, "bold"),
                    background="#FFFFFF", foreground="#2E7D32").pack(anchor="w")
            
            lines = [
                "",
                "Calculates time to reach next level.",
                "",
                "XP/Run: Total XP earned per run",
                "  (blocks × XP × mults × exp mods)",
                "",
                "Run Duration: Time per run",
                "  Base: 1 hit = 1 second",
                "  Speed Mod: 2× speed (saves time)",
                "  Flurry: 2× speed + bonus stamina",
                "",
                "XP/h: XP per hour = XP/Run × Runs/h",
                "",
                "Enter 'XP needed' to see time estimate.",
                "Example: Need 61.89 XP → enter '61.89'",
            ]
            
            for line in lines:
                tk.Label(content, text=line, font=("Arial", 9),
                        background="#FFFFFF", justify=tk.LEFT).pack(anchor="w")
            
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
            
            tooltip_width = 320
            tooltip_height = 300
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
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
            tooltip_height = 340
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
        if not hasattr(self, 'card_labels'):
            return
        
        for block_type, labels in self.card_labels.items():
            card_level = self.block_cards.get(block_type, 0)
            card_btn = labels.get('card_btn')
            gilded_btn = labels.get('gilded_btn')
            
            if card_btn:
                if card_level == 1:
                    card_btn.config(foreground="#FFFFFF", background="#4CAF50", relief=tk.SUNKEN)
                else:
                    card_btn.config(foreground="#888888", background="#E8F5E9", relief=tk.RAISED)
            
            if gilded_btn:
                if card_level == 2:
                    gilded_btn.config(foreground="#FFFFFF", background="#FFD700", relief=tk.SUNKEN)
                else:
                    gilded_btn.config(foreground="#888888", background="#E8F5E9", relief=tk.RAISED)
    
    def _calculate_gilded_improvement(self, block_type, stats, spawn_rate):
        """
        Calculate the % improvement in floors/run from upgrading to gilded card.
        This shows the value of gilding a card (costs gems).
        
        Returns: percentage improvement in floors/run
        """
        # Get current floors/run
        current_floors = self.calculate_floors_per_run(stats, self.current_stage)
        if current_floors <= 0:
            return 0.0
        
        # Temporarily set this block to gilded and recalculate
        old_card_level = self.block_cards.get(block_type, 0)
        self.block_cards[block_type] = 2  # Gilded
        
        gilded_floors = self.calculate_floors_per_run(stats, self.current_stage)
        
        # Restore original card level
        self.block_cards[block_type] = old_card_level
        
        # Calculate percentage improvement
        if current_floors > 0:
            improvement = ((gilded_floors - current_floors) / current_floors) * 100
            return improvement
        return 0.0
    
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
            tooltip_height = 280
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
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
    
    def update_cards_display(self):
        """Update the cards display in the middle column"""
        if not hasattr(self, 'card_labels'):
            return
        
        stats = self.get_total_stats()
        spawn_rates = get_normalized_spawn_rates(self.current_stage)
        
        for block_type in BLOCK_TYPES:
            if block_type not in self.card_labels:
                continue
            
            labels = self.card_labels[block_type]
            spawn_rate = spawn_rates.get(block_type, 0)
            card_level = self.block_cards.get(block_type, 0)
            
            # Update card button states
            card_btn = labels.get('card_btn')
            gilded_btn = labels.get('gilded_btn')
            
            if card_btn:
                if card_level == 1:
                    card_btn.config(foreground="#FFFFFF", background="#4CAF50", relief=tk.SUNKEN)
                else:
                    card_btn.config(foreground="#888888", background="#E8F5E9", relief=tk.RAISED)
            
            if gilded_btn:
                if card_level == 2:
                    gilded_btn.config(foreground="#FFFFFF", background="#FFD700", relief=tk.SUNKEN)
                else:
                    gilded_btn.config(foreground="#888888", background="#E8F5E9", relief=tk.RAISED)
            
            # Calculate and display gilded improvement (only if normal card is present, not if no card or already gilded)
            gilded_improve_label = labels.get('gilded_improve')
            if gilded_improve_label:
                if card_level == 1 and spawn_rate > 0:
                    gilded_improvement = self._calculate_gilded_improvement(block_type, stats, spawn_rate)
                    if gilded_improvement > 0.005:
                        gilded_improve_label.config(text=f"+{gilded_improvement:.2f}%", foreground="#B8860B")
                    else:
                        gilded_improve_label.config(text="~0%", foreground="#AAAAAA")
                else:
                    gilded_improve_label.config(text="")
    
    def update_fragments_hour_display(self, stats):
        """Update the Fragments/Hour display"""
        if not hasattr(self, 'frag_hour_labels'):
            return
        
        # Calculate fragments per run
        frags_per_run = self.calculate_fragments_per_run(stats, self.current_stage)
        
        # Calculate run duration
        run_duration_sec = self.calculate_run_duration(stats, self.current_stage)
        runs_per_hour = 3600 / run_duration_sec if run_duration_sec > 0 else 0
        
        # Total fragments
        total_per_run = sum(frags_per_run.values())
        total_per_hour = total_per_run * runs_per_hour
        
        self.frags_per_run_label.config(text=f"{total_per_run:.3f}")
        self.frags_per_hour_label.config(text=f"{total_per_hour:.1f}")
        
        # Update per-type breakdown
        for frag_type, labels in self.frag_hour_labels.items():
            per_run = frags_per_run.get(frag_type, 0)
            per_hour = per_run * runs_per_hour
            
            labels['per_run'].config(text=f"{per_run:.4f}")
            labels['per_hour'].config(text=f"{per_hour:.3f}")
    
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
        
        # Update fragment upgrade level labels (colored by type)
        if hasattr(self, 'upgrade_level_labels'):
            for upgrade_key, label in self.upgrade_level_labels.items():
                level = self.fragment_upgrade_levels.get(upgrade_key, 0)
                label.config(text=str(level))
                if level > 0:
                    # Keep the original color set in _create_upgrade_row
                    pass
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
        
        # Calculate fragment upgrade efficiencies (3 types: Stage Rush, XP, Fragments)
        if hasattr(self, 'upgrade_efficiency_labels'):
            for upgrade_key in self.upgrade_efficiency_labels:
                upgrade_info = self.FRAGMENT_UPGRADES.get(upgrade_key, {})
                max_level = upgrade_info.get('max_level', 25)
                current_level = self.fragment_upgrade_levels.get(upgrade_key, 0)
                
                if current_level >= max_level:
                    # All three efficiency labels show MAX
                    self.upgrade_efficiency_labels[upgrade_key].config(text="MAX", foreground="#C73E1D")
                    if hasattr(self, 'upgrade_xp_efficiency_labels') and upgrade_key in self.upgrade_xp_efficiency_labels:
                        self.upgrade_xp_efficiency_labels[upgrade_key].config(text="MAX", foreground="#C73E1D")
                    if hasattr(self, 'upgrade_frag_efficiency_labels') and upgrade_key in self.upgrade_frag_efficiency_labels:
                        self.upgrade_frag_efficiency_labels[upgrade_key].config(text="MAX", foreground="#C73E1D")
                else:
                    # Stage Rush efficiency factor (floors improvement per fragment cost)
                    _, stage_efficiency = self.calculate_fragment_upgrade_efficiency(upgrade_key)
                    self.upgrade_efficiency_labels[upgrade_key].config(
                        text=f"{stage_efficiency:.3f}", foreground="#2E7D32")
                    
                    # XP efficiency factor (XP improvement per fragment cost)
                    if hasattr(self, 'upgrade_xp_efficiency_labels') and upgrade_key in self.upgrade_xp_efficiency_labels:
                        _, xp_efficiency = self.calculate_fragment_upgrade_xp_efficiency(upgrade_key)
                        self.upgrade_xp_efficiency_labels[upgrade_key].config(
                            text=f"{xp_efficiency:.3f}", foreground="#1976D2")
                    
                    # Fragment farming efficiency factor (Frag/h improvement per fragment cost)
                    if hasattr(self, 'upgrade_frag_efficiency_labels') and upgrade_key in self.upgrade_frag_efficiency_labels:
                        _, frag_efficiency = self.calculate_fragment_upgrade_fragment_efficiency(upgrade_key)
                        self.upgrade_frag_efficiency_labels[upgrade_key].config(
                            text=f"{frag_efficiency:.3f}", foreground="#9932CC")
        
        # Note: Greedy recommendation removed - use Planner/Forecaster on the right instead
        
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
        
        # Update cards display (middle column)
        self.update_cards_display()
        
        # Update fragments per hour
        self.update_fragments_hour_display(stats)
        
        # Update level up timer
        self.update_levelup_timer(stats)
        
        # Update skill forecast
        self.update_forecast_display()
    
    def update_levelup_timer(self, stats):
        """Update the Level Up Timer display"""
        if not hasattr(self, 'xp_per_run_label'):
            return
        
        # Calculate XP per run
        xp_per_run = self.calculate_xp_per_run(stats, self.current_stage)
        self.xp_per_run_label.config(text=f"{xp_per_run:.2f}")
        
        # Calculate run duration
        run_duration_sec = self.calculate_run_duration(stats, self.current_stage)
        run_duration_min = run_duration_sec / 60
        if run_duration_min >= 1:
            self.run_duration_label.config(text=f"{run_duration_min:.1f}m")
        else:
            self.run_duration_label.config(text=f"{run_duration_sec:.0f}s")
        
        # Calculate XP per hour
        if run_duration_sec > 0:
            runs_per_hour = 3600 / run_duration_sec
            xp_per_hour = xp_per_run * runs_per_hour
            self.xp_per_hour_label.config(text=f"{xp_per_hour:.1f}")
        else:
            self.xp_per_hour_label.config(text="—")
        
        # Store for time calculation
        self._cached_xp_per_hour = xp_per_hour if run_duration_sec > 0 else 0
        
        # Update time to level
        self.update_levelup_time()
    
    def update_levelup_time(self):
        """Update the time to level up based on XP needed input"""
        if not hasattr(self, 'time_to_level_label'):
            return
        
        try:
            xp_needed_str = self.xp_needed_var.get().strip()
            if not xp_needed_str:
                self.time_to_level_label.config(text="—")
                return
            
            xp_needed = float(xp_needed_str)
            if xp_needed <= 0:
                self.time_to_level_label.config(text="—")
                return
            
            xp_per_hour = getattr(self, '_cached_xp_per_hour', 0)
            if xp_per_hour <= 0:
                self.time_to_level_label.config(text="∞")
                return
            
            hours_to_level = xp_needed / xp_per_hour
            
            if hours_to_level < 1:
                minutes = hours_to_level * 60
                self.time_to_level_label.config(text=f"{minutes:.0f} min")
            elif hours_to_level < 24:
                self.time_to_level_label.config(text=f"{hours_to_level:.1f} h")
            else:
                days = hours_to_level / 24
                self.time_to_level_label.config(text=f"{days:.1f} days")
        except ValueError:
            self.time_to_level_label.config(text="—")
    
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
        """Update the stage rusher planner with optimal distribution for fixed points"""
        if not hasattr(self, 'budget_dist_label'):
            return
        
        budget = self.shared_planner_points.get()
        
        # Calculate optimal distribution for the budget
        # This uses the same algorithm as forecast
        result = self.calculate_forecast(budget)
        
        # Also calculate XP and frags for this distribution for comparison
        # Temporarily apply the distribution
        for skill, points in result['distribution'].items():
            self.skill_points[skill] += points
        
        new_stats = self.get_total_stats()
        xp_with_floors_build = self.calculate_xp_per_run(new_stats, self.current_stage)
        frags_with_build = self.calculate_fragments_per_run(new_stats, self.current_stage)
        run_duration = self.calculate_run_duration(new_stats, self.current_stage)
        runs_per_hour = 3600 / run_duration if run_duration > 0 else 0
        
        for skill, points in result['distribution'].items():
            self.skill_points[skill] -= points
        
        # Calculate Stage/h and XP/h
        stages_per_hour = result['floors_per_run'] * runs_per_hour
        xp_per_hour = xp_with_floors_build * runs_per_hour
        
        # Format and display
        dist_str = self.format_distribution(result['distribution'])
        self.budget_dist_label.config(text=dist_str)
        self.budget_floors_label.config(text=f"{stages_per_hour:.1f}")
        self.budget_xp_label.config(text=f"{xp_per_hour:.1f}")
        self.budget_gain_label.config(text=f"+{result['improvement_pct']:.1f}%")
        
        # Update frags/h display based on selected fragment type from Fragment Farm Planner
        if hasattr(self, 'frag_target_var'):
            target_frag = self.frag_target_var.get()
            frag_per_hour = frags_with_build.get(target_frag, 0) * runs_per_hour
            
            # Update icon
            if hasattr(self, 'fragment_icons') and target_frag in self.fragment_icons:
                self.budget_frag_icon_label.config(image=self.fragment_icons[target_frag])
            else:
                self.budget_frag_icon_label.config(image='')
            
            # Update label text with fragment type (neutral colors since icon distinguishes)
            self.budget_frag_type_label.config(text=f"{target_frag.capitalize()}/h:", foreground="#555555")
            self.budget_frag_value_label.config(text=f"{frag_per_hour:.1f}", foreground="#333333")
        
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
        
        budget = self.shared_planner_points.get()
        
        # Calculate optimal distribution for XP (not floors)
        result = self.calculate_xp_forecast(budget)
        
        # Also calculate floors and frags for this distribution for comparison
        # Temporarily apply the distribution
        for skill, points in result['distribution'].items():
            self.skill_points[skill] += points
        
        new_stats = self.get_total_stats()
        floors_with_xp_build = self.calculate_floors_per_run(new_stats, self.current_stage)
        frags_with_build = self.calculate_fragments_per_run(new_stats, self.current_stage)
        run_duration = self.calculate_run_duration(new_stats, self.current_stage)
        runs_per_hour = 3600 / run_duration if run_duration > 0 else 0
        
        for skill, points in result['distribution'].items():
            self.skill_points[skill] -= points
        
        # Calculate Stage/h and XP/h
        stages_per_hour = floors_with_xp_build * runs_per_hour
        xp_per_hour = result['xp_per_run'] * runs_per_hour
        
        # Format and display
        dist_str = self.format_distribution(result['distribution'])
        self.xp_budget_dist_label.config(text=dist_str)
        self.xp_budget_floors_label.config(text=f"{stages_per_hour:.1f}")
        self.xp_budget_xp_label.config(text=f"{xp_per_hour:.1f}")
        self.xp_budget_gain_label.config(text=f"+{result['improvement_pct']:.1f}%")
        
        # Update frags/h display based on selected fragment type from Fragment Farm Planner
        if hasattr(self, 'frag_target_var'):
            target_frag = self.frag_target_var.get()
            frag_per_hour = frags_with_build.get(target_frag, 0) * runs_per_hour
            
            # Update icon
            if hasattr(self, 'fragment_icons') and target_frag in self.fragment_icons:
                self.xp_budget_frag_icon_label.config(image=self.fragment_icons[target_frag])
            else:
                self.xp_budget_frag_icon_label.config(image='')
            
            # Update label text with fragment type (neutral colors since icon distinguishes)
            self.xp_budget_frag_type_label.config(text=f"{target_frag.capitalize()}/h:", foreground="#555555")
            self.xp_budget_frag_value_label.config(text=f"{frag_per_hour:.1f}", foreground="#333333")
        
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
        
        # Update fragment planner too
        self.update_frag_planner_display()
    
    def update_frag_planner_display(self):
        """Update the Fragment Farm Planner with optimal distribution"""
        if not hasattr(self, 'frag_planner_dist_label'):
            return
        
        budget = self.shared_planner_points.get()
        target_frag = self.frag_target_var.get()
        
        # Calculate optimal distribution for target fragment
        result = self.calculate_frag_forecast(budget, target_frag)
        
        # Format and display
        dist_str = self.format_distribution(result['distribution'])
        self.frag_planner_dist_label.config(text=dist_str)
        self.frag_planner_result_label.config(text=f"{result['frags_per_hour']:.1f}")
        self.frag_planner_stages_label.config(text=f"{result['stages_per_hour']:.1f}")
        self.frag_planner_xp_label.config(text=f"{result['xp_per_hour']:.1f}")
        self.frag_planner_gain_label.config(text=f"+{result['improvement_pct']:.1f}%")
    
    def calculate_frag_forecast(self, levels_ahead: int, target_frag_type: str):
        """
        Calculate the optimal skill point distribution for maximum fragment income of a specific type.
        
        Args:
            levels_ahead: Number of skill points to allocate
            target_frag_type: 'common', 'rare', 'epic', 'legendary', or 'mythic'
        
        Returns:
            dict with:
                - 'distribution': dict of skill -> points to add
                - 'frags_per_hour': resulting frags/hour for target type
                - 'stages_per_hour': stages cleared per hour with this build
                - 'xp_per_hour': XP earned per hour with this build
                - 'improvement_pct': percentage improvement
        """
        skills = ['strength', 'agility', 'intellect', 'perception', 'luck']
        
        # Calculate current frags per hour for target type
        stats = self.get_total_stats()
        current_frags = self.calculate_fragments_per_run(stats, self.current_stage)
        current_floors = self.calculate_floors_per_run(stats, self.current_stage)
        current_xp = self.calculate_xp_per_run(stats, self.current_stage)
        run_duration = self.calculate_run_duration(stats, self.current_stage)
        runs_per_hour = 3600 / run_duration if run_duration > 0 else 0
        current_frag_per_hour = current_frags.get(target_frag_type, 0) * runs_per_hour
        current_xp_per_hour = current_xp * runs_per_hour
        current_stages_per_hour = current_floors * runs_per_hour
        
        best_result = {
            'distribution': {s: 0 for s in skills},
            'frags_per_hour': current_frag_per_hour,
            'stages_per_hour': current_stages_per_hour,
            'xp_per_hour': current_xp_per_hour,
            'improvement_pct': 0.0,
        }
        
        # Generate all possible distributions
        def generate_distributions(n_points, n_skills):
            if n_skills == 1:
                yield (n_points,)
                return
            for i in range(n_points + 1):
                for rest in generate_distributions(n_points - i, n_skills - 1):
                    yield (i,) + rest
        
        best_frag_per_hour = current_frag_per_hour
        
        for dist_tuple in generate_distributions(levels_ahead, len(skills)):
            # Apply distribution temporarily
            for skill, points in zip(skills, dist_tuple):
                self.skill_points[skill] += points
            
            # Calculate frags with this distribution
            new_stats = self.get_total_stats()
            new_frags = self.calculate_fragments_per_run(new_stats, self.current_stage)
            new_floors = self.calculate_floors_per_run(new_stats, self.current_stage)
            new_xp = self.calculate_xp_per_run(new_stats, self.current_stage)
            new_run_duration = self.calculate_run_duration(new_stats, self.current_stage)
            new_runs_per_hour = 3600 / new_run_duration if new_run_duration > 0 else 0
            new_frag_per_hour = new_frags.get(target_frag_type, 0) * new_runs_per_hour
            new_xp_per_hour = new_xp * new_runs_per_hour
            new_stages_per_hour = new_floors * new_runs_per_hour
            
            if new_frag_per_hour > best_frag_per_hour:
                best_frag_per_hour = new_frag_per_hour
                best_result['distribution'] = {s: p for s, p in zip(skills, dist_tuple)}
                best_result['frags_per_hour'] = new_frag_per_hour
                best_result['stages_per_hour'] = new_stages_per_hour
                best_result['xp_per_hour'] = new_xp_per_hour
            
            # Revert changes
            for skill, points in zip(skills, dist_tuple):
                self.skill_points[skill] -= points
        
        # Calculate improvement percentage
        if current_frag_per_hour > 0:
            best_result['improvement_pct'] = ((best_frag_per_hour - current_frag_per_hour) / current_frag_per_hour) * 100
        
        return best_result
    
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
        
        # Auto-adjust unlocked stage to at least match the selected stage's minimum
        # If you're playing stage 3-4, you must have at least stage 3 unlocked
        current_unlocked = self.get_unlocked_stage()
        if current_unlocked < self.current_stage:
            self.unlocked_stage_var.set(str(self.current_stage))
            # Note: This will trigger _on_unlocked_stage_changed which rebuilds upgrades
        
        self.update_display()
    
    def run_mc_stage_pusher(self):
        """Run 1000 Monte Carlo simulations and show histogram with stage distribution
        
        Runs two simulations: one without crit and one with crit.
        Uses the recommended skill setup from Stage Pusher planner for each.
        Shows two histograms side by side for comparison.
        """
        import threading
        
        def run_in_thread():
            # Always start at Floor 1 (unbiased)
            starting_floor = 1
            
            # Get planner points (shared across all planners)
            num_points = self.shared_planner_points.get() if hasattr(self, 'shared_planner_points') else 20
            
            # Save original skill points and crit state
            original_points = self.skill_points.copy()
            original_crit_state = self.crit_calc_enabled.get() if hasattr(self, 'crit_calc_enabled') else False
            
            enrage_enabled = self.enrage_enabled.get() if hasattr(self, 'enrage_enabled') else True
            flurry_enabled = self.flurry_enabled.get() if hasattr(self, 'flurry_enabled') else True
            block_cards = self.block_cards if hasattr(self, 'block_cards') else None
            
            # ===== SIMULATION WITHOUT CRIT =====
            # Get planner distribution WITHOUT crit (crit disabled)
            if hasattr(self, 'crit_calc_enabled'):
                self.crit_calc_enabled.set(False)
            forecast_no_crit = self.calculate_forecast(num_points)
            planner_dist_no_crit = forecast_no_crit['distribution']
            
            # Get skill points for display (current + planner distribution)
            skill_points_display_no_crit = {}
            for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
                current = self.skill_points.get(skill, 0)
                added = planner_dist_no_crit.get(skill, 0)
                skill_points_display_no_crit[skill] = current + added
            
            # Apply planner distribution temporarily to get stats
            for skill, points in planner_dist_no_crit.items():
                self.skill_points[skill] += points
            
            stats_no_crit = self.get_total_stats()
            
            # Restore original skill points
            self.skill_points = original_points
            
            # ===== SIMULATION WITH CRIT =====
            # Get planner distribution WITH crit (crit enabled)
            if hasattr(self, 'crit_calc_enabled'):
                self.crit_calc_enabled.set(True)
            forecast_with_crit = self.calculate_forecast(num_points)
            planner_dist_with_crit = forecast_with_crit['distribution']
            
            # Get skill points for display (current + planner distribution)
            skill_points_display_with_crit = {}
            for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
                current = self.skill_points.get(skill, 0)
                added = planner_dist_with_crit.get(skill, 0)
                skill_points_display_with_crit[skill] = current + added
            
            # Apply planner distribution temporarily to get stats
            for skill, points in planner_dist_with_crit.items():
                self.skill_points[skill] += points
            
            stats_with_crit = self.get_total_stats()
            
            # Restore original skill points
            self.skill_points = original_points
            
            # Restore crit state
            if hasattr(self, 'crit_calc_enabled'):
                self.crit_calc_enabled.set(original_crit_state)
            
            # Run 1000 simulations for both scenarios
            from .monte_carlo_crit import MonteCarloCritSimulator
            simulator = MonteCarloCritSimulator()
            
            stage_counts_no_crit = {}  # stage -> count of simulations that reached this as max stage
            stage_counts_with_crit = {}
            raw_data_no_crit = []  # List of max_stage values for statistical test
            raw_data_with_crit = []
            
            for i in range(1000):
                # Run simulation WITHOUT crit
                result = simulator.simulate_run(
                    stats_no_crit, starting_floor, use_crit=False, 
                    enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled,
                    block_cards=block_cards, return_metrics=True
                )
                
                max_stage = int(result['max_stage_reached'])
                raw_data_no_crit.append(max_stage)
                if max_stage not in stage_counts_no_crit:
                    stage_counts_no_crit[max_stage] = 0
                stage_counts_no_crit[max_stage] += 1
            
            for i in range(1000):
                # Run simulation WITH crit
                result = simulator.simulate_run(
                    stats_with_crit, starting_floor, use_crit=True, 
                    enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled,
                    block_cards=block_cards, return_metrics=True
                )
                
                max_stage = int(result['max_stage_reached'])
                raw_data_with_crit.append(max_stage)
                if max_stage not in stage_counts_with_crit:
                    stage_counts_with_crit[max_stage] = 0
                stage_counts_with_crit[max_stage] += 1
            
            # Create window with histograms
            self.window.after(0, lambda: self._show_stage_pusher_results(
                stage_counts_no_crit, stage_counts_with_crit,
                skill_points_display_no_crit, skill_points_display_with_crit, num_points,
                raw_data_no_crit, raw_data_with_crit
            ))
        
        # Run in separate thread to avoid blocking UI
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    def _show_stage_pusher_results(self, stage_counts_no_crit, stage_counts_with_crit, 
                                   skill_points_display_no_crit, skill_points_display_with_crit, num_points,
                                   raw_data_no_crit, raw_data_with_crit):
        """Show histogram window with stage distribution and skill setup for both crit and no-crit"""
        try:
            import matplotlib
            matplotlib.use('TkAgg')
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            import numpy as np
            MATPLOTLIB_AVAILABLE = True
        except ImportError:
            MATPLOTLIB_AVAILABLE = False
            tk.messagebox.showerror("Error", "Matplotlib is required for histogram display.")
            return
        
        # Perform statistical test
        try:
            from scipy import stats
            SCIPY_AVAILABLE = True
        except ImportError:
            SCIPY_AVAILABLE = False
        
        # Create window in normal GUI style (not Matrix)
        result_window = tk.Toplevel(self.window)
        result_window.title("MC Stage Pusher Results")
        result_window.geometry("1400x800")
        result_window.transient(self.window)
        
        # Main container
        main_frame = ttk.Frame(result_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="MC Stage Pusher Results (1000 simulations each)", 
                               font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        
        # Statistical test results
        if SCIPY_AVAILABLE and raw_data_no_crit and raw_data_with_crit:
            # Perform Mann-Whitney U test (non-parametric test, good for non-normal distributions)
            statistic, p_value = stats.mannwhitneyu(raw_data_with_crit, raw_data_no_crit, 
                                                     alternative='two-sided')
            
            # Calculate descriptive statistics
            mean_no_crit = np.mean(raw_data_no_crit)
            mean_with_crit = np.mean(raw_data_with_crit)
            median_no_crit = np.median(raw_data_no_crit)
            median_with_crit = np.median(raw_data_with_crit)
            
            # Determine which is better
            if mean_with_crit > mean_no_crit:
                better = "With Crit"
                diff = mean_with_crit - mean_no_crit
                diff_pct = (diff / mean_no_crit * 100) if mean_no_crit > 0 else 0
            else:
                better = "No Crit"
                diff = mean_no_crit - mean_with_crit
                diff_pct = (diff / mean_with_crit * 100) if mean_with_crit > 0 else 0
            
            # Interpret p-value
            if p_value < 0.001:
                significance = "*** (p < 0.001)"
                interpretation = "Highly significant difference"
            elif p_value < 0.01:
                significance = "** (p < 0.01)"
                interpretation = "Very significant difference"
            elif p_value < 0.05:
                significance = "* (p < 0.05)"
                interpretation = "Significant difference"
            else:
                significance = f"(p = {p_value:.4f})"
                interpretation = "No significant difference"
            
            # Create statistics frame
            stats_frame = ttk.LabelFrame(main_frame, text="Statistical Analysis", padding="10")
            stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            
            # Results text
            stats_text = f"""Mann-Whitney U Test Results:
            
Mean Stage Reached:
  No Crit:    {mean_no_crit:.2f} (median: {median_no_crit:.1f})
  With Crit:  {mean_with_crit:.2f} (median: {median_with_crit:.1f})
  Difference: {diff:.2f} stages ({diff_pct:+.1f}%)

Statistical Test:
  {better} performs better {significance}
  {interpretation}"""
            
            stats_label = ttk.Label(stats_frame, text=stats_text, font=("Courier", 9), 
                                   justify=tk.LEFT)
            stats_label.pack(anchor=tk.W)
        else:
            # No statistical test available
            stats_frame = ttk.LabelFrame(main_frame, text="Statistical Analysis", padding="10")
            stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            if not SCIPY_AVAILABLE:
                stats_label = ttk.Label(stats_frame, 
                                       text="scipy not available - statistical test skipped", 
                                       foreground="gray")
            else:
                stats_label = ttk.Label(stats_frame, 
                                       text="Insufficient data for statistical test", 
                                       foreground="gray")
            stats_label.pack()
        
        # Skill distribution displays (above histograms)
        skill_frame_no_crit = ttk.LabelFrame(main_frame, text="Skill Distribution (No Crit)", padding="5")
        skill_frame_no_crit.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10), padx=(0, 5))
        
        skill_text_parts_no_crit = []
        for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
            points = skill_points_display_no_crit.get(skill, 0)
            skill_short = skill[:3].upper()
            skill_text_parts_no_crit.append(f"{skill_short}: {points}")
        
        skill_label_no_crit = ttk.Label(skill_frame_no_crit, text=" | ".join(skill_text_parts_no_crit), font=("Arial", 9))
        skill_label_no_crit.pack()
        
        skill_frame_with_crit = ttk.LabelFrame(main_frame, text="Skill Distribution (With Crit)", padding="5")
        skill_frame_with_crit.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 10), padx=(5, 0))
        
        skill_text_parts_with_crit = []
        for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
            points = skill_points_display_with_crit.get(skill, 0)
            skill_short = skill[:3].upper()
            skill_text_parts_with_crit.append(f"{skill_short}: {points}")
        
        skill_label_with_crit = ttk.Label(skill_frame_with_crit, text=" | ".join(skill_text_parts_with_crit), font=("Arial", 9))
        skill_label_with_crit.pack()
        
        # Histogram frame (spans both columns)
        hist_frame = ttk.LabelFrame(main_frame, text="Stage Distribution Comparison", padding="5")
        hist_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        hist_frame.columnconfigure(0, weight=1)
        hist_frame.rowconfigure(0, weight=1)
        
        # Create figure with two subplots side by side
        if stage_counts_no_crit or stage_counts_with_crit:
            # Determine common y-axis range for both histograms
            all_counts = []
            if stage_counts_no_crit:
                all_counts.extend(stage_counts_no_crit.values())
            if stage_counts_with_crit:
                all_counts.extend(stage_counts_with_crit.values())
            max_count = max(all_counts) if all_counts else 100
            
            # Create figure with two subplots
            fig = Figure(figsize=(12, 4), facecolor='white')
            
            # Helper function to create histogram subplot
            def create_histogram_subplot(stage_counts, subplot_idx, title, color, edge_color):
                """Create a histogram subplot"""
                if not stage_counts:
                    return None
                
                # Get all stages
                all_stages = sorted(stage_counts.keys())
                if not all_stages:
                    all_stages = [1]
                
                # Get counts for each stage
                counts = []
                bin_centers = []
                for stage in range(int(min(all_stages)), int(max(all_stages)) + 1):
                    count = stage_counts.get(stage, 0)
                    counts.append(count)
                    bin_centers.append(stage)
                
                # Create subplot
                ax = fig.add_subplot(1, 2, subplot_idx, facecolor='white')
                
                # Create bar chart (histogram-style)
                bars = ax.bar(bin_centers, counts, width=0.8, 
                             color=color, edgecolor=edge_color, 
                             linewidth=1.5, alpha=0.8)
                
                # Add labels on top of bars with count and percentage
                total = sum(counts)
                for bar, count in zip(bars, counts):
                    if count > 0:
                        height = bar.get_height()
                        pct = (count / total * 100) if total > 0 else 0
                        # Position label above bar
                        label_y = height + max(counts) * 0.02 if counts else 0
                        ax.text(bar.get_x() + bar.get_width()/2., label_y,
                               f'{count}\n({pct:.1f}%)',
                               ha='center', va='bottom', color=edge_color,
                               fontsize=8, fontweight='bold')
                
                ax.set_xlabel('Stage Reached', fontsize=10, fontweight='bold')
                ax.set_ylabel('Count', fontsize=10, fontweight='bold')
                ax.set_title(title, fontsize=11, fontweight='bold', pad=10)
                
                # Normal GUI style colors
                ax.tick_params(colors='black', labelsize=8)
                for spine in ax.spines.values():
                    spine.set_color('#CCCCCC')
                ax.grid(True, color='#E0E0E0', alpha=0.5, linestyle='--', linewidth=0.5)
                ax.set_xticks(bin_centers)
                ax.set_xticklabels([f'{int(x)}' for x in bin_centers])
                
                # Set y-axis to start at 0
                ax.set_ylim(0, max_count * 1.1)
                
                return ax
            
            # Create both histograms
            create_histogram_subplot(stage_counts_no_crit, 1, "No Crit", '#4CAF50', '#2E7D32')
            create_histogram_subplot(stage_counts_with_crit, 2, "With Crit", '#2196F3', '#1565C0')
            
            # Layout
            fig.tight_layout()
            
            # Create canvas
            canvas = FigureCanvasTkAgg(fig, hist_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            # No data
            ttk.Label(hist_frame, text="No simulation data available", 
                     foreground="gray").pack(pady=20)
        
        # Close button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        close_btn = ttk.Button(button_frame, text="Close", command=result_window.destroy)
        close_btn.pack()
