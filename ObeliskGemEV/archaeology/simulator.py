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

from .block_spawn_rates import get_block_mix_for_stage, get_stage_range_label, STAGE_RANGES, get_normalized_spawn_rates, spawn_block_for_slot, get_total_spawn_probability, get_available_blocks_at_stage
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


class CollapsibleFrame:
    """A collapsible/expandable frame with toggle button"""
    def __init__(self, parent, title, bg_color="#FFF3E0", expanded=True):
        self.expanded = expanded
        self.bg_color = bg_color
        
        # Main frame
        self.main_frame = tk.Frame(parent, background=bg_color)
        self.main_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Header with toggle button
        self.header = tk.Frame(self.main_frame, background=bg_color)
        self.header.pack(fill=tk.X)
        
        # Toggle button (arrow indicator)
        self.toggle_btn = tk.Label(self.header, text="▼" if expanded else "▶", 
                                   font=("Arial", 9, "bold"), 
                                   background=bg_color, cursor="hand2",
                                   foreground="#1976D2")
        self.toggle_btn.pack(side=tk.LEFT, padx=(0, 3))
        self.toggle_btn.bind("<Button-1>", self.toggle)
        
        # Title
        self.title_label = tk.Label(self.header, text=title, 
                                   font=("Arial", 10, "bold"), 
                                   background=bg_color)
        self.title_label.pack(side=tk.LEFT)
        self.title_label.bind("<Button-1>", self.toggle)
        
        # Content frame
        self.content = tk.Frame(self.main_frame, background=bg_color)
        if expanded:
            self.content.pack(fill=tk.X, padx=(15, 0), pady=2)
        else:
            self.content.pack_forget()
    
    def toggle(self, event=None):
        self.expanded = not self.expanded
        if self.expanded:
            self.content.pack(fill=tk.X, padx=(15, 0), pady=2)
            self.toggle_btn.config(text="▼")
        else:
            self.content.pack_forget()
            self.toggle_btn.config(text="▶")


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
    
    # Quake ability constants
    # 5 charges every 180 seconds, next 5 attacks deal 20% damage to all blocks
    QUAKE_CHARGES = 5
    QUAKE_COOLDOWN = 180  # seconds
    QUAKE_DAMAGE_MULTIPLIER = 0.20  # 20% damage to all blocks
    
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
    # Stage structure: 6 columns x 4 rows = 24 slots
    # Each slot CAN spawn a block (but doesn't have to)
    # Blocks per floor varies between 0-24 based on spawn probabilities
    SLOTS_PER_FLOOR = 24
    BLOCKS_PER_FLOOR_MIN = 0
    BLOCKS_PER_FLOOR_MAX = 24
    BLOCKS_PER_FLOOR = 19.0  # Average for calculations (realistic estimate, will be calculated dynamically)
    
    def __init__(self, parent):
        self.parent = parent
        # Flags to prevent recursive updates
        self._updating_stage = False
        self._updating_unlocked_stage = False
        
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
                icon_photo = ImageTk.PhotoImage(icon_image, master=self.window)
                self.window.iconphoto(False, icon_photo)
                self.icon_photo = icon_photo  # Store as instance variable to prevent GC
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
            'quake_enabled': self.quake_enabled.get() if hasattr(self, 'quake_enabled') else True,
            'quake_enabled': self.quake_enabled.get() if hasattr(self, 'quake_enabled') else True,
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
                enrage_val = state.get('enrage_enabled', True)
                self.enrage_enabled.set(bool(enrage_val))  # Ensure boolean value
                self._update_ability_button_visual('enrage', bool(enrage_val))
            if hasattr(self, 'flurry_enabled'):
                flurry_val = state.get('flurry_enabled', True)
                self.flurry_enabled.set(bool(flurry_val))  # Ensure boolean value
                self._update_ability_button_visual('flurry', bool(flurry_val))
            if hasattr(self, 'quake_enabled'):
                quake_val = state.get('quake_enabled', True)
                self.quake_enabled.set(bool(quake_val))  # Ensure boolean value
                self._update_ability_button_visual('quake', bool(quake_val))
            
            # Update stage label
            if hasattr(self, 'stage_label'):
                self.stage_label.config(text=str(self.current_stage))
            
            # Update Archaeology Level (used by MC optimizers)
            if hasattr(self, 'shared_planner_points'):
                # Try to load Archaeology Level, fallback to old individual values for migration
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
            unlocked_stage = state.get('unlocked_stage', 1)
            self.unlocked_stage = unlocked_stage
            if hasattr(self, 'unlocked_stage_label'):
                self.unlocked_stage_label.config(text=str(unlocked_stage))
            # Rebuild upgrade widgets after loading fragment_upgrade_levels
            if hasattr(self, 'upgrades_container'):
                self._rebuild_upgrade_widgets()
            
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
    
    def reset_stats_only(self):
        """Reset only stats (skill points, level, stage) but keep upgrades (fragment_upgrade_levels, gem_upgrades)"""
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
        # Note: fragment_upgrade_levels and gem_upgrades are NOT reset
    
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
    
    def _get_calculation_stage(self):
        """
        Get the stage used for calculations.
        
        When user enters Goal Stage N, we use Stage N-1 for calculations
        (to optimize for beating Stage N-1 to reach Stage N).
        Minimum is 1.
        
        Returns:
            int: Stage number to use for block stats and spawn rates
        """
        return max(1, self.current_stage - 1)
    
    def get_total_stats(self):
        """
        Calculate total character stats from skills, upgrades, and fragments.
        
        MULTIPLICATOR REGELN (Archaeology):
        ===================================
        
        MULTIPLIKATIV (Multiplikator auf Basis):
        - INT Armor Pen: Basis wird zuerst gerundet, dann mit (1 + INT * 0.03) multipliziert
        - Crit Damage: Basis 1.5 * (1 + STR*0.03 + Fragment %) — STR und Fragment ADDITIV im gleichen Mult
        - INT XP Gain: (Base + Gem + Fragment Upgrades) * (1 + INT * 0.05)
        - Fragment XP Multiplier: Wenn vorhanden, multipliziert XP Base
        
        ADDITIV (Werte werden addiert):
        - Flat Damage: Base + STR * 1 + Upgrades
        - Percent Damage: STR * 0.01 + Upgrades (dann multipliziert mit Flat)
        - Armor Pen Base: Base + PER * 2 + Upgrades (vor INT Multiplikator)
        - Max Stamina: Base + AGI * 5 + Upgrades
        - Crit Chance: Base + AGI * 0.01 + LUC * 0.02 + Upgrades
        - Fragment Gain: Base + PER * 0.04 + Gem + Upgrades
        - Mod Chances: Alle additiv
        
        WICHTIG:
        - Armor Pen wird ZUERST gerundet, DANN mit INT multipliziert
        - Crit Damage: STR-% und Fragment-% addieren im gleichen Mult (nicht nacheinander multiplizieren)
        - INT XP Gain multipliziert die gesamte XP Base (inkl. Upgrades)
        """
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
        # Round base armor pen to integer first (as game does)
        armor_pen_base = round(armor_pen_base)
        # INT gives +3% armor pen multiplier per point (applied to rounded base)
        int_armor_pen_mult = 1 + int_pts * self.SKILL_BONUSES['intellect']['armor_pen_mult']
        armor_pen = round(armor_pen_base * int_armor_pen_mult)
        
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
        # STR crit damage (+3%/pt) and fragment crit damage (+1% or +2%/lvl) ADD in one multiplier (ingame)
        # e.g. STR 5 + crit_c1 lv9: 1.5 * (1 + 0.15 + 0.09) = 1.86x (not 1.5*1.15*1.09 = 1.88x)
        total_crit_mult = 1 + str_pts * self.SKILL_BONUSES['strength']['crit_damage'] + frag_bonuses.get('crit_damage', 0)
        crit_damage = self.base_crit_damage * total_crit_mult
        one_hit_chance = luck_pts * self.SKILL_BONUSES['luck']['one_hit_chance']
        
        # Super crit and ultra crit from fragment upgrades
        super_crit_chance = frag_bonuses.get('super_crit_chance', 0)
        super_crit_damage = frag_bonuses.get('super_crit_damage', 0)
        ultra_crit_chance = frag_bonuses.get('ultra_crit_chance', 0)
        
        # XP mult: base + gem upgrade + fragment upgrades (additive)
        xp_mult_base = (self.base_xp_mult + 
                       gem_xp * self.GEM_UPGRADE_BONUSES['xp']['xp_bonus'])
        # Apply XP multiplier from fragment upgrades
        if frag_bonuses.get('xp_bonus_mult', 0) > 0:
            xp_mult_base *= frag_bonuses.get('xp_bonus_mult', 1.0)
        # INT gives +5% XP multiplier per point (multiplicative on base)
        xp_bonus_per_int = self.SKILL_BONUSES['intellect']['xp_bonus'] + frag_bonuses.get('xp_bonus_skill', 0)
        xp_mult = xp_mult_base * (1 + int_pts * xp_bonus_per_int)
        
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
        
        # Archaeology XP bonus from gem upgrade + fragment upgrades (multiplicative)
        # Each level gives +2%, so level 6 = 1.0 * 1.02^6 or additive: 1.0 + 6*0.02 = 1.12
        arch_xp_bonus_total = gem_arch_xp * self.GEM_UPGRADE_BONUSES['arch_xp']['arch_xp_bonus'] + frag_bonuses.get('arch_xp_bonus', 0)
        arch_xp_mult = 1.0 + arch_xp_bonus_total
        
        # Loot mod multiplier bonus (affects average loot from loot mod)
        loot_mod_multiplier = self.MOD_LOOT_MULTIPLIER_AVG + frag_bonuses.get('loot_mod_multiplier', 0)
        
        # Exp mod gain bonus (affects average XP from exp mod)
        exp_mod_gain = self.MOD_EXP_MULTIPLIER_AVG + frag_bonuses.get('exp_mod_gain', 0)
        
        # Stamina mod gain bonus
        stamina_mod_gain = self.MOD_STAMINA_BONUS_AVG + frag_bonuses.get('stamina_mod_gain', 0)
        
        # Enrage bonuses from fragment upgrades (additive to base enrage bonuses)
        enrage_damage_bonus = self.ENRAGE_DAMAGE_BONUS + frag_bonuses.get('enrage_damage', 0)
        enrage_crit_damage_bonus = self.ENRAGE_CRIT_DAMAGE_BONUS + frag_bonuses.get('enrage_crit_damage', 0)
        
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
            'xp_gain_total': xp_mult * arch_xp_mult,  # combined for display (incl. Arch XP upgrades)
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
            # Enrage bonuses (with fragment upgrades)
            'enrage_damage_bonus': enrage_damage_bonus,
            'enrage_crit_damage_bonus': enrage_crit_damage_bonus,
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
        - Critical hits (always included - MC handles exact simulation)
        - One-hit chance
        - Enrage ability (5 charges every 60s with +20% dmg, +100% crit dmg) - if enabled
        - Card HP reduction (if block_type provided)
        
        Note: MC simulations handle crits exactly, so this is just for deterministic estimates.
        """
        import math
        
        # Apply card HP reduction if block_type is provided
        if block_type:
            block_hp = self.get_block_hp_with_card(block_hp, block_type)
        
        # Calculate effective damage (base, no enrage)
        effective_dmg_base = self.calculate_effective_damage(stats, block_armor)
        
        # Always include crit calculations (MC handles exact simulation)
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
            
            # Enrage effective damage: base damage * (1 + enrage_damage_bonus) (floored), then subtract armor
            # Damage is always integer - enrage bonus is floored before armor calculation
            # Enrage damage bonus includes fragment upgrades (additive)
            enrage_damage_bonus = stats.get('enrage_damage_bonus', self.ENRAGE_DAMAGE_BONUS)
            enrage_total_damage = int(stats['total_damage'] * (1 + enrage_damage_bonus))
            effective_armor = max(0, block_armor - stats['armor_pen'])
            effective_dmg_enrage = max(1, enrage_total_damage - effective_armor)
            
            # Enrage crit: multiplier on current crit (ingame), e.g. +104% → crit * (1 + 1.04)
            # Tooltip "+104% crit dmg" → 1.64x becomes ~3.35x (not additive 2.68x)
            enrage_crit_damage_bonus = stats.get('enrage_crit_damage_bonus', self.ENRAGE_CRIT_DAMAGE_BONUS)
            enrage_crit_damage = crit_damage * (1 + enrage_crit_damage_bonus)
            
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
        # Calculate expected blocks per floor based on spawn probabilities if not specified
        if blocks_per_floor is None:
            # Will be calculated per floor based on spawn rates
            blocks_per_floor = None
        
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
            
            # Calculate expected blocks per floor: 24 slots * (total spawn probability / 100)
            if blocks_per_floor is None:
                total_spawn_prob = get_total_spawn_probability(current_floor)
                expected_blocks = self.SLOTS_PER_FLOOR * (total_spawn_prob / 100.0)
                floor_blocks = expected_blocks
            else:
                floor_blocks = blocks_per_floor
            
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
            stamina_for_floor = net_stamina_per_block * floor_blocks
            
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
            
            # Calculate expected blocks per floor: 24 slots * (total spawn probability / 100)
            total_spawn_prob = get_total_spawn_probability(current_floor)
            expected_blocks = self.SLOTS_PER_FLOOR * (total_spawn_prob / 100.0)
            
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
            
            # XP for this floor: expected_blocks * avg_xp * xp_mult * arch_xp_mult * exp_mod_factor
            floor_total_xp = expected_blocks * floor_xp * xp_mult * arch_xp_mult * exp_mod_factor
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
            
            # Calculate expected blocks per floor: 24 slots * (total spawn probability / 100)
            total_spawn_prob = get_total_spawn_probability(current_floor)
            expected_blocks = self.SLOTS_PER_FLOOR * (total_spawn_prob / 100.0)
            
            for block_type, spawn_chance in spawn_rates.items():
                if spawn_chance <= 0 or block_type == 'dirt':
                    continue  # Dirt doesn't drop fragments
                block_data = block_mix.get(block_type)
                if not block_data:
                    continue
                
                # Base fragment per block
                base_frag = block_data.fragment
                
                # Fragments from this block type on this floor
                # expected_blocks * spawn_chance * base_frag * mult * loot_mod
                frag_gain = expected_blocks * spawn_chance * base_frag * fragment_mult * loot_mod_factor * floor_mult
                
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
        calc_stage = self._get_calculation_stage()
        current_floors = self.calculate_floors_per_run(current_stats, calc_stage)
        
        # Temporarily add one level
        self.fragment_upgrade_levels[upgrade_key] = current_level + 1
        new_stats = self.get_total_stats()
        new_floors = self.calculate_floors_per_run(new_stats, calc_stage)
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
        calc_stage = self._get_calculation_stage()
        current_xp = self.calculate_xp_per_run(current_stats, calc_stage)
        
        # Temporarily add one level
        self.fragment_upgrade_levels[upgrade_key] = current_level + 1
        new_stats = self.get_total_stats()
        new_xp = self.calculate_xp_per_run(new_stats, calc_stage)
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
        calc_stage = self._get_calculation_stage()
        current_frags = self.calculate_fragments_per_run(current_stats, calc_stage)
        current_total = sum(current_frags.values())
        current_duration = self.calculate_run_duration(current_stats, calc_stage)
        
        # Calculate current frags/hour
        if current_duration > 0:
            current_frags_per_hour = current_total * (3600.0 / current_duration)
        else:
            current_frags_per_hour = 0
        
        # Temporarily add one level
        self.fragment_upgrade_levels[upgrade_key] = current_level + 1
        new_stats = self.get_total_stats()
        new_frags = self.calculate_fragments_per_run(new_stats, calc_stage)
        new_total = sum(new_frags.values())
        new_duration = self.calculate_run_duration(new_stats, calc_stage)
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
        
        # Goal Stage and MC Stage Optimizer moved to Fragment Planner section
        
        # Center: Level display and Archaeology Level
        center_frame = tk.Frame(header_frame, background="#E3F2FD")
        center_frame.pack(side=tk.LEFT, padx=20)
        
        self.level_label = tk.Label(center_frame, text="Level: 1", font=("Arial", 12, "bold"),
                                   background="#E3F2FD", foreground="#1976D2")
        self.level_label.pack()
        
        # Archaeology Level (for MC optimizers)
        arch_level_frame = tk.Frame(center_frame, background="#E3F2FD")
        arch_level_frame.pack(pady=(3, 0))
        
        tk.Label(arch_level_frame, text="Arch Level:", font=("Arial", 9), 
                background="#E3F2FD").pack(side=tk.LEFT, padx=(0, 3))
        
        # Initialize Archaeology Level variable (needed early for header)
        self.shared_planner_points = tk.IntVar(value=20)
        
        tk.Button(arch_level_frame, text="-", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_shared_planner_points(-1), background="#E3F2FD").pack(side=tk.LEFT)
        self.shared_planner_points_label = tk.Label(arch_level_frame, text="20", font=("Arial", 10, "bold"), 
                                                     background="#E3F2FD", foreground="#7B1FA2", width=3)
        self.shared_planner_points_label.pack(side=tk.LEFT, padx=2)
        tk.Button(arch_level_frame, text="+", width=1, font=("Arial", 7, "bold"),
                 command=lambda: self._adjust_shared_planner_points(1), background="#E3F2FD").pack(side=tk.LEFT)
        
        # Load ability icons early (needed by create_stats_column)
        # Initialize ability_icons dict first
        if not hasattr(self, 'ability_icons'):
            self.ability_icons = {}
        self._load_ability_icons()
        
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
            ("Exp Gain:", "xp_gain_total"),
            ("Fragment Gain:", "fragment_mult"),
            ("Damage:", "total_damage"),
            ("Armor Pen:", "armor_pen"),
            ("Stamina:", "max_stamina"),
            ("Crit %:", "crit_chance"),
            ("Crit Dmg:", "crit_damage"),
            ("One-Hit %:", "one_hit_chance"),
        ]
        
        for i, (label_text, key) in enumerate(stat_names):
            tk.Label(stats_grid, text=label_text, background="#E3F2FD", 
                    font=("Arial", 9), anchor=tk.W).grid(row=i, column=0, sticky=tk.W, pady=0)
            value_label = tk.Label(stats_grid, text="—", background="#E3F2FD", 
                                  font=("Arial", 9, "bold"), anchor=tk.E, width=8)
            value_label.grid(row=i, column=1, sticky=tk.E, pady=0)
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
        
        # Abilities section
        tk.Label(col_frame, text="Abilities", font=("Arial", 10, "bold"), 
                background="#E3F2FD").pack(pady=(0, 3))
        
        abilities_frame = tk.Frame(col_frame, background="#E3F2FD")
        abilities_frame.pack(fill=tk.X, padx=8, pady=2)
        
        # Initialize ability states
        self.enrage_enabled = tk.BooleanVar(value=True)
        self.flurry_enabled = tk.BooleanVar(value=True)
        self.quake_enabled = tk.BooleanVar(value=True)
        
        # Load ability icons (must be loaded before creating buttons)
        if not hasattr(self, 'ability_icons') or not self.ability_icons:
            self._load_ability_icons()
        
        # Enrage ability icon button
        enrage_frame = tk.Frame(abilities_frame, background="#E3F2FD")
        enrage_frame.pack(side=tk.LEFT, padx=(0, 5))
        
        enrage_icon = self.ability_icons.get('enrage')
        
        # Create button with icon
        btn_kwargs = {
            'command': lambda: self._toggle_ability('enrage'),
            'relief': tk.RAISED,
            'borderwidth': 2,
            'background': "#E3F2FD",
            'activebackground': "#BA68C8",
        }
        
        if enrage_icon:
            btn_kwargs['image'] = enrage_icon
            btn_kwargs['width'] = 34
            btn_kwargs['height'] = 34
        else:
            btn_kwargs['text'] = "⚔"
            btn_kwargs['width'] = 34
            btn_kwargs['height'] = 34
        
        self.enrage_icon_button = tk.Button(enrage_frame, **btn_kwargs)
        self.enrage_icon_button.pack()
        self._create_ability_tooltip(self.enrage_icon_button, 'enrage')
        
        # Flurry ability icon button
        flurry_frame = tk.Frame(abilities_frame, background="#E3F2FD")
        flurry_frame.pack(side=tk.LEFT, padx=(0, 5))
        
        flurry_icon = self.ability_icons.get('flurry')
        
        # Create button with icon
        btn_kwargs = {
            'command': lambda: self._toggle_ability('flurry'),
            'relief': tk.RAISED,
            'borderwidth': 2,
            'background': "#E3F2FD",
            'activebackground': "#BA68C8",
        }
        
        if flurry_icon:
            btn_kwargs['image'] = flurry_icon
            btn_kwargs['width'] = 34
            btn_kwargs['height'] = 34
        else:
            btn_kwargs['text'] = "⚡"
            btn_kwargs['width'] = 34
            btn_kwargs['height'] = 34
        
        self.flurry_icon_button = tk.Button(flurry_frame, **btn_kwargs)
        self.flurry_icon_button.pack()
        self._create_ability_tooltip(self.flurry_icon_button, 'flurry')
        
        # Quake ability icon button
        quake_frame = tk.Frame(abilities_frame, background="#E3F2FD")
        quake_frame.pack(side=tk.LEFT, padx=(0, 5))
        
        quake_icon = self.ability_icons.get('quake')
        
        # Create button with icon
        btn_kwargs = {
            'command': lambda: self._toggle_ability('quake'),
            'relief': tk.RAISED,
            'borderwidth': 2,
            'background': "#E3F2FD",
            'activebackground': "#BA68C8",
        }
        
        if quake_icon:
            btn_kwargs['image'] = quake_icon
            btn_kwargs['width'] = 34
            btn_kwargs['height'] = 34
        else:
            btn_kwargs['text'] = "🌍"
            btn_kwargs['width'] = 34
            btn_kwargs['height'] = 34
        
        self.quake_icon_button = tk.Button(quake_frame, **btn_kwargs)
        self.quake_icon_button.pack()
        self._create_ability_tooltip(self.quake_icon_button, 'quake')
        
        # Update initial visual state
        self._update_ability_button_visual('enrage', True)
        self._update_ability_button_visual('flurry', True)
        self._update_ability_button_visual('quake', True)
        
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
        
        # Header with Reset button
        skill_header = tk.Frame(col_frame, background="#E8F5E9")
        skill_header.pack(fill=tk.X, padx=5, pady=(5, 3))
        
        tk.Label(skill_header, text="Add Points", font=("Arial", 11, "bold"), 
                background="#E8F5E9").pack(side=tk.LEFT)
        
        tk.Button(skill_header, text="Reset", font=("Arial", 7), 
                 command=self.reset_all_skill_points).pack(side=tk.RIGHT)
        
        # Skills
        self.skill_buttons = {}
        
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
            row_frame.pack(fill=tk.X, pady=0)
            
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
        upgrade_header_frame.pack(fill=tk.X, padx=5, pady=(0, 2))
        
        tk.Label(upgrade_header_frame, text="Fragment Upgrades", font=("Arial", 10, "bold"), 
                background="#E8F5E9").pack(side=tk.LEFT)
        
        # Unlocked Stages input - moved here from header
        unlocked_frame = tk.Frame(upgrade_header_frame, background="#E8F5E9")
        unlocked_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Label(unlocked_frame, text="Unlocked Stages:", font=("Arial", 8), 
                background="#E8F5E9").pack(side=tk.LEFT, padx=(0, 2))
        
        # Minus button
        unlocked_minus_btn = tk.Button(unlocked_frame, text="-", width=2, font=("Arial", 7, "bold"),
                                       command=self._decrease_unlocked_stage)
        unlocked_minus_btn.pack(side=tk.LEFT, padx=(0, 1))
        
        # Unlocked stage label (non-editable, only changed via buttons)
        self.unlocked_stage_label = tk.Label(
            unlocked_frame,
            text="1",
            width=5,
            font=("Arial", 9, "bold"),
            background="#FFFFFF",
            foreground="#000000",
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.unlocked_stage_label.pack(side=tk.LEFT, padx=(0, 1))
        
        # Plus button
        unlocked_plus_btn = tk.Button(unlocked_frame, text="+", width=2, font=("Arial", 7, "bold"),
                                      command=self._increase_unlocked_stage)
        unlocked_plus_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        # Help icon for unlocked stage
        unlocked_help_label = tk.Label(unlocked_frame, text="?", font=("Arial", 8, "bold"), 
                                      cursor="hand2", foreground="#1976D2", background="#E8F5E9")
        unlocked_help_label.pack(side=tk.LEFT, padx=(0, 0))
        self._create_unlocked_stage_help_tooltip(unlocked_help_label)
        
        # Load fragment icons for each type
        self._load_fragment_icons()
        
        # Load block icons for cards section
        self._load_block_icons()
        
        # Load ability icons (must be loaded before create_stats_column which uses them)
        self._load_ability_icons()
        
        # Reset button for upgrades
        tk.Button(upgrade_header_frame, text="Reset", font=("Arial", 7), 
                 command=self.reset_all_upgrades).pack(side=tk.RIGHT)
        
        # Container for dynamically built upgrades (will be rebuilt when unlocked_stage changes)
        self.upgrades_container = tk.Frame(col_frame, background="#E8F5E9")
        self.upgrades_container.pack(fill=tk.X, padx=5, pady=1)
        
        # Store reference to parent column frame for rebuilding
        self.skills_col_frame = col_frame
        
        # Initialize upgrade tracking dicts
        self.upgrade_buttons = {}
        self.upgrade_efficiency_labels = {}  # Stage Rush (Floors)
        self.upgrade_xp_efficiency_labels = {}  # XP efficiency
        self.upgrade_frag_efficiency_labels = {}  # Fragment efficiency
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
                # Use window as master to ensure image is associated with the correct root
                self.gem_icon_photo = ImageTk.PhotoImage(gem_image, master=self.window)
                gem_icon_label = tk.Label(gem_header_frame, image=self.gem_icon_photo, background="#E8F5E9")
                gem_icon_label.pack(side=tk.LEFT, padx=(0, 5))
        except:
            pass
        
        tk.Label(gem_header_frame, text="Gem Upgrades", font=("Arial", 10, "bold"), 
                background="#E8F5E9", foreground="#9932CC").pack(side=tk.LEFT)
        
        self.gem_upgrade_buttons = {}
        self.gem_upgrade_labels = {}
        
        gem_upgrades_frame = tk.Frame(col_frame, background="#E8F5E9")
        gem_upgrades_frame.pack(fill=tk.X, padx=5, pady=2)
        
        gem_upgrade_info = {
            'stamina': ("Stamina", "+2 Stam, +0.05% Stam Mod", 50),
            'xp': ("XP Boost", "+5% XP, +0.05% Exp Mod", 25),
            'fragment': ("Fragment", "+2% Frags, +0.05% Loot Mod", 25),
        }
        
        # Single row for all gem upgrades (more compact)
        gem_row = tk.Frame(gem_upgrades_frame, background="#E8F5E9")
        gem_row.pack(fill=tk.X, pady=2)
        
        for gem_upgrade, (display_name, info, max_lvl) in gem_upgrade_info.items():
            # Each upgrade in its own frame within the row
            upgrade_frame = tk.Frame(gem_row, background="#E8F5E9")
            upgrade_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            minus_btn = tk.Button(upgrade_frame, text="-", width=2, font=("Arial", 8, "bold"),
                                 command=lambda u=gem_upgrade: self.remove_gem_upgrade(u))
            minus_btn.pack(side=tk.LEFT, padx=(0, 1))
            
            plus_btn = tk.Button(upgrade_frame, text="+", width=2, font=("Arial", 8, "bold"),
                                command=lambda u=gem_upgrade: self.add_gem_upgrade(u))
            plus_btn.pack(side=tk.LEFT, padx=(0, 2))
            
            # Level display with gem icon indicator
            level_label = tk.Label(upgrade_frame, text="0", background="#E8F5E9", 
                                  font=("Arial", 9, "bold"), foreground="#9932CC", width=2, anchor=tk.E)
            level_label.pack(side=tk.LEFT, padx=(0, 2))
            self.gem_upgrade_labels[gem_upgrade] = level_label
            
            tk.Label(upgrade_frame, text=display_name, background="#E8F5E9", 
                    font=("Arial", 8, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=(0, 2))
            
            
            # Info tooltip
            info_label = tk.Label(upgrade_frame, text="?", background="#E8F5E9", 
                                 font=("Arial", 8, "bold"), foreground="#1976D2", cursor="hand2")
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
                # Use window as master to ensure image is associated with the correct root
                self.cards_icon = ImageTk.PhotoImage(cards_icon_image, master=self.window)
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
        
        # Create cards in a grid layout (2 per row)
        current_row = None
        col_index = 0
        
        for i, block_type in enumerate(BLOCK_TYPES):
            # Create new row every 2 cards
            if col_index == 0:
                current_row = tk.Frame(self.cards_container, background="#E8F5E9")
                current_row.pack(fill=tk.X, pady=1)
            
            # Card frame (half width for 2 per row) - no border for cleaner look
            card_frame = tk.Frame(current_row, background="#E8F5E9")
            card_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
            
            color = self.BLOCK_COLORS.get(block_type, '#888888')
            
            # Block icon if available
            if hasattr(self, 'block_icons') and block_type in self.block_icons:
                tk.Label(card_frame, image=self.block_icons[block_type], 
                        background="#E8F5E9").pack(side=tk.LEFT, padx=(2, 2))
            
            # Block name
            name_label = tk.Label(card_frame, text=f"{block_type.capitalize()}", 
                                 font=("Arial", 8, "bold"), foreground=color,
                                 background="#E8F5E9", anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(0, 2))
            
            # Card button (normal card: -10% HP, +10% XP)
            card_btn = tk.Label(card_frame, text="Card", font=("Arial", 7),
                               cursor="hand2", foreground="#888888", background="#E8F5E9",
                               padx=2, relief=tk.RAISED, borderwidth=1)
            card_btn.pack(side=tk.LEFT, padx=(0, 1))
            card_btn.bind("<Button-1>", lambda e, bt=block_type: self._toggle_card(bt, 1))
            
            # Gilded card button (gilded: -20% HP, +20% XP)
            gilded_btn = tk.Label(card_frame, text="Gild", font=("Arial", 7),
                                 cursor="hand2", foreground="#888888", background="#E8F5E9",
                                 padx=2, relief=tk.RAISED, borderwidth=1)
            gilded_btn.pack(side=tk.LEFT, padx=(0, 1))
            gilded_btn.bind("<Button-1>", lambda e, bt=block_type: self._toggle_card(bt, 2))
            
            # Gilded improvement indicator (smaller)
            gilded_improve_label = tk.Label(card_frame, text="", font=("Arial", 7),
                                           foreground="#B8860B", background="#E8F5E9",
                                           width=5, anchor=tk.W)
            gilded_improve_label.pack(side=tk.LEFT)
            
            self.card_labels[block_type] = {
                'row': card_frame,
                'name': name_label,
                'card_btn': card_btn,
                'gilded_btn': gilded_btn,
                'gilded_improve': gilded_improve_label,
            }
            
            # Move to next column, wrap to new row if needed
            col_index += 1
            if col_index >= 2:
                col_index = 0
    
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
                    # Use window as master to ensure image is associated with the correct root
                    self.fragment_icons[frag_type] = ImageTk.PhotoImage(icon_image, master=self.window)
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
                    # Use window as master to ensure image is associated with the correct root
                    self.block_icons[block_type] = ImageTk.PhotoImage(icon_image, master=self.window)
            except:
                pass
    
    def _load_ability_icons(self):
        """Load ability icons from local sprites directory"""
        import urllib.request
        from io import BytesIO
        
        if not hasattr(self, 'ability_icons'):
            self.ability_icons = {}
        
        # Store icons as instance variables to prevent garbage collection
        if not hasattr(self, '_ability_icon_refs'):
            self._ability_icon_refs = {}
        
        # Local sprite paths
        ability_paths = {
            'enrage': 'sprites/archaeology/Archaeology_Ability_Enrage.png',
            'flurry': 'sprites/archaeology/Archaeology_Ability_Flurry.png',
            'quake': 'sprites/archaeology/Archaeology_Ability_Quake.png',
        }
        
        # Fallback URLs (if local files don't exist)
        ability_urls = {
            'enrage': 'https://static.wikitide.net/shminerwiki/2/2a/Archaeology_Ability_Enrage.png',
            'flurry': 'https://static.wikitide.net/shminerwiki/e/e4/Archaeology_Ability_Flurry.png',
            'quake': 'https://static.wikitide.net/shminerwiki/a/ab/Archaeology_Ability_Quake.png',
        }
        
        for ability_name in ability_paths.keys():
            if ability_name in self.ability_icons and self.ability_icons[ability_name] is not None:
                continue  # Already loaded
            try:
                # Try to load from local sprite file first
                local_path = get_resource_path(ability_paths[ability_name])
                if local_path.exists():
                    icon_image = Image.open(local_path)
                    # Convert to RGBA if needed for transparency
                    if icon_image.mode != 'RGBA':
                        icon_image = icon_image.convert('RGBA')
                    icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                    # Use window as master to ensure image is associated with the correct root
                    photo = ImageTk.PhotoImage(icon_image, master=self.window)
                    self.ability_icons[ability_name] = photo
                    # Store reference to prevent garbage collection
                    self._ability_icon_refs[ability_name] = photo
                else:
                    # Fallback to URL if local file doesn't exist
                    url = ability_urls[ability_name]
                    with urllib.request.urlopen(url, timeout=10) as response:
                        icon_data = response.read()
                    icon_image = Image.open(BytesIO(icon_data))
                    # Convert to RGBA if needed for transparency
                    if icon_image.mode != 'RGBA':
                        icon_image = icon_image.convert('RGBA')
                    icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                    # Use window as master to ensure image is associated with the correct root
                    photo = ImageTk.PhotoImage(icon_image, master=self.window)
                    self.ability_icons[ability_name] = photo
                    # Store reference to prevent garbage collection
                    self._ability_icon_refs[ability_name] = photo
            except Exception:
                # Fallback: create a simple colored square if both local and URL loading fail
                pass
                fallback_image = Image.new('RGBA', (32, 32), color=(200, 200, 200, 255))
                photo = ImageTk.PhotoImage(fallback_image, master=self.window)
                self.ability_icons[ability_name] = photo
                self._ability_icon_refs[ability_name] = photo
    
    def _toggle_ability(self, ability_name):
        """Toggle an ability on/off"""
        if ability_name == 'enrage':
            current = self.enrage_enabled.get()
            self.enrage_enabled.set(not current)
            self._update_ability_button_visual('enrage', not current)
        elif ability_name == 'flurry':
            current = self.flurry_enabled.get()
            self.flurry_enabled.set(not current)
            self._update_ability_button_visual('flurry', not current)
        elif ability_name == 'quake':
            current = self.quake_enabled.get()
            self.quake_enabled.set(not current)
            self._update_ability_button_visual('quake', not current)
        
        # Update display to reflect changes
        self.update_display()
    
    def _update_ability_button_visual(self, ability_name, enabled):
        """Update the visual appearance of an ability button"""
        button_map = {
            'enrage': self.enrage_icon_button,
            'flurry': self.flurry_icon_button,
            'quake': self.quake_icon_button,
        }
        
        button = button_map.get(ability_name)
        if button:
            if enabled:
                button.config(relief=tk.RAISED, borderwidth=2)
            else:
                button.config(relief=tk.SUNKEN, borderwidth=2)
    
    def _create_ability_tooltip(self, widget, ability_name):
        """Create a tooltip for an ability icon"""
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
            
            content = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content.pack()
            
            # Ability-specific info
            if ability_name == 'enrage':
                ability_title = "Enrage"
                ability_info = [
                    "5 Charges / 60s cooldown",
                    "",
                    "Next 5 Attacks:",
                    "  +20% Damage",
                    "  +100% Crit Damage",
                ]
            elif ability_name == 'flurry':
                ability_title = "Flurry"
                ability_info = [
                    "5 Charges / 120s cooldown",
                    "",
                    "Effect:",
                    "  +100% Attack Speed",
                    "  +5 Stamina On Cast",
                ]
            elif ability_name == 'quake':
                ability_title = "Quake"
                ability_info = [
                    "5 Charges / 180s cooldown",
                    "",
                    "Next 5 Attacks:",
                    "  Deal 20% Damage",
                    "  To All Blocks",
                ]
            else:
                ability_title = ability_name.capitalize()
                ability_info = []
            
            tk.Label(content, text=ability_title, font=("Arial", 10, "bold"),
                    background="#FFFFFF", foreground="#1976D2").pack(anchor="w")
            
            for line in ability_info:
                tk.Label(content, text=line, font=("Arial", 9),
                        background="#FFFFFF", justify=tk.LEFT).pack(anchor="w")
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
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
        self.upgrade_level_labels = {}
        
        unlocked_stage = self.get_unlocked_stage()
        
        # Column headers for the three efficiency types
        header_row = tk.Frame(self.upgrades_container, background="#E8F5E9")
        header_row.pack(fill=tk.X, pady=(0, 1))
        
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
            header_frame.pack(fill=tk.X, pady=(2, 0))
            
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
        row_frame.pack(fill=tk.X, pady=0)
        
        # Initialize level if not exists
        if upgrade_key not in self.fragment_upgrade_levels:
            self.fragment_upgrade_levels[upgrade_key] = 0
        
        # -5 button
        minus5_btn = tk.Button(row_frame, text="-5", width=3, font=("Arial", 7, "bold"),
                               command=lambda u=upgrade_key: self._remove_fragment_upgrade(u, 5))
        minus5_btn.pack(side=tk.LEFT, padx=(0, 1))
        
        # -1 button
        minus_btn = tk.Button(row_frame, text="-", width=2, font=("Arial", 8, "bold"),
                             command=lambda u=upgrade_key: self._remove_fragment_upgrade(u, 1))
        minus_btn.pack(side=tk.LEFT, padx=(0, 1))
        
        # +1 button
        plus_btn = tk.Button(row_frame, text="+", width=2, font=("Arial", 8, "bold"),
                            command=lambda u=upgrade_key: self._add_fragment_upgrade(u, 1))
        plus_btn.pack(side=tk.LEFT, padx=(0, 1))
        
        # +5 button
        plus5_btn = tk.Button(row_frame, text="+5", width=3, font=("Arial", 7, "bold"),
                              command=lambda u=upgrade_key: self._add_fragment_upgrade(u, 5))
        plus5_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        # Level counter with max level (e.g. "5/25") - larger and more visible
        current_level = self.fragment_upgrade_levels.get(upgrade_key, 0)
        max_level = upgrade_info.get('max_level', 25)
        level_label = tk.Label(row_frame, text=f"{current_level}/{max_level}", background="#E8F5E9", 
                              font=("Arial", 9, "bold"), foreground=color, width=6, anchor=tk.CENTER,
                              relief=tk.SUNKEN, borderwidth=1)
        level_label.pack(side=tk.LEFT, padx=(0, 3))
        self.upgrade_level_labels[upgrade_key] = level_label
        
        # Display name
        display_name = upgrade_info.get('display_name', upgrade_key)
        tk.Label(row_frame, text=display_name, background="#E8F5E9", 
                font=("Arial", 8), width=14, anchor=tk.W).pack(side=tk.LEFT)
        
        # Help ? label with tooltip (includes stage unlock info and costs)
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
        
        self.upgrade_buttons[upgrade_key] = (minus5_btn, minus_btn, plus_btn, plus5_btn)
    
    def _add_fragment_upgrade(self, upgrade_key, amount=1):
        """Add levels to a fragment upgrade"""
        if upgrade_key not in self.fragment_upgrade_levels:
            self.fragment_upgrade_levels[upgrade_key] = 0
        
        max_level = self.FRAGMENT_UPGRADES[upgrade_key].get('max_level', 25)
        current_level = self.fragment_upgrade_levels[upgrade_key]
        new_level = min(current_level + amount, max_level)
        
        if new_level > current_level:
            self.fragment_upgrade_levels[upgrade_key] = new_level
            # Update the label directly with level/max format
            if upgrade_key in self.upgrade_level_labels:
                self.upgrade_level_labels[upgrade_key].config(
                    text=f"{self.fragment_upgrade_levels[upgrade_key]}/{max_level}")
            self.update_display()
            self.save_state()  # Save immediately after upgrade change
    
    def _remove_fragment_upgrade(self, upgrade_key, amount=1):
        """Remove levels from a fragment upgrade"""
        if upgrade_key not in self.fragment_upgrade_levels:
            self.fragment_upgrade_levels[upgrade_key] = 0
        
        max_level = self.FRAGMENT_UPGRADES[upgrade_key].get('max_level', 25)
        current_level = self.fragment_upgrade_levels[upgrade_key]
        new_level = max(0, current_level - amount)
        
        if new_level < current_level:
            self.fragment_upgrade_levels[upgrade_key] = new_level
            # Update the label directly with level/max format
            if upgrade_key in self.upgrade_level_labels:
                self.upgrade_level_labels[upgrade_key].config(
                    text=f"{self.fragment_upgrade_levels[upgrade_key]}/{max_level}")
            self.update_display()
            self.save_state()  # Save immediately after upgrade change
    
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
                    # Use tooltip as master to ensure image is associated with the correct root
                    tooltip.icon_photo = ImageTk.PhotoImage(icon_image, master=tooltip)
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
            
            # Next upgrade cost
            if current_level < max_level:
                next_cost = get_upgrade_cost(upgrade_key, current_level)
                if next_cost is not None:
                    tk.Label(content_frame, text=f"\nNext Upgrade Cost: {next_cost:.1f} {cost_type.capitalize()} Fragments", 
                            font=("Arial", 9, "bold"), foreground="#1976D2",
                            background="#FFFFFF").pack(anchor=tk.W)
                else:
                    tk.Label(content_frame, text=f"\nNext Upgrade Cost: —", 
                            font=("Arial", 9, "bold"), foreground="#999999",
                            background="#FFFFFF").pack(anchor=tk.W)
            else:
                tk.Label(content_frame, text=f"\nNext Upgrade Cost: MAX", 
                        font=("Arial", 9, "bold"), foreground="#C73E1D",
                        background="#FFFFFF").pack(anchor=tk.W)
            
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
                    # Use tooltip as master to ensure image is associated with the correct root
                    tooltip.icon_photo = ImageTk.PhotoImage(icon_image, master=tooltip)
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
            tk.Label(content_frame, text="Goal Stage", 
                    font=("Arial", 11, "bold"), foreground="#1976D2", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()  # Spacer
            
            # Rule 1
            tk.Label(content_frame, text="Enter the Goal Stage you want to REACH!", 
                    font=("Arial", 9, "bold"), foreground="#C73E1D", 
                    background="#FFFFFF").pack(anchor=tk.W)
            
            tk.Label(content_frame, text="", background="#FFFFFF").pack()  # Spacer
            
            # Explanation
            lines = [
                "The Goal Stage is the stage you want to REACH.",
                "",
                "Internally, the calculator uses Stage N-1 for",
                "calculations (e.g., if you enter 7, it uses",
                "Stage 6 stats to optimize beating Stage 6 and",
                "reaching Stage 7).",
                "",
                "This ensures you optimize for the blocks that",
                "you need to beat to reach your goal stage.",
                "",
                "Use the +/- buttons to adjust the stage.",
                "The value is not editable (buttons only).",
                "",
                "Examples:",
                "  - Want to reach Stage 7? Enter 7",
                "    (uses Stage 6 stats for optimization)",
                "  - Want to reach Stage 4? Enter 4",
                "    (uses Stage 3 stats for optimization)",
                "",
                "Where is this used?",
                "  - Fragment Upgrade Efficiency calculations",
                "  - MC Fragment Farmer (fragment optimization)",
                "  - Normal efficiency calculations (floors/run, XP, etc.)",
                "  - Average Block Stats display",
                "  - Block spawn rates chart",
                "",
                "NOT used by:",
                "  - MC Stage Optimizer (always starts at Stage 1)",
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
                "MC simulations handle crit mechanics",
                "automatically and accurately.",
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
    
    def _update_unlocked_stage_display(self):
        """Update the unlocked stage label and handle side effects"""
        # Clamp to valid range
        self.unlocked_stage = max(1, min(50, self.unlocked_stage))
        # Update label
        self.unlocked_stage_label.config(text=str(self.unlocked_stage))
        # Rebuild upgrade widgets to show/hide based on new stage
        if hasattr(self, 'upgrades_container'):
            self._rebuild_upgrade_widgets()
        self.update_display()
    
    def _increase_unlocked_stage(self):
        """Increase unlocked stage by 1"""
        if not hasattr(self, 'unlocked_stage'):
            self.unlocked_stage = 1
        self.unlocked_stage = min(50, self.unlocked_stage + 1)
        self._update_unlocked_stage_display()
    
    def _decrease_unlocked_stage(self):
        """Decrease unlocked stage by 1"""
        if not hasattr(self, 'unlocked_stage'):
            self.unlocked_stage = 1
        self.unlocked_stage = max(1, self.unlocked_stage - 1)
        self._update_unlocked_stage_display()
    
    def get_unlocked_stage(self):
        """Get the current unlocked stage value"""
        if hasattr(self, 'unlocked_stage'):
            return self.unlocked_stage
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
                "• Crit Dmg: Base 1.5× × (1 + STR×3% + Fragment %)",
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
                    ('+3% Crit Damage', 'Adds 3% per STR to crit mult (same bracket as Fragment %)'),
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
                    ('+3% Armor Pen', 'Multiplies total armor pen'),
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
        """Right column: Fragment Planner and MC Optimizers at the top"""
        # Outer frame for the column
        col_outer = tk.Frame(parent, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        col_outer.grid(row=0, column=2, sticky="nsew", padx=(2, 0), pady=0)
        
        # Inner frame (no scrolling - Fragment Planner is at the top)
        col_frame = tk.Frame(col_outer, background="#FFF3E0")
        col_frame.pack(fill=tk.BOTH, expand=True, anchor="nw")
        
        # === MC FRAGMENT FARMER ===
        mc_fragment_farmer_section = tk.Frame(col_frame, background="#E1BEE7", relief=tk.RIDGE, borderwidth=2)
        mc_fragment_farmer_section.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        mc_fragment_farmer_header = tk.Frame(mc_fragment_farmer_section, background="#E1BEE7")
        mc_fragment_farmer_header.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        tk.Label(mc_fragment_farmer_header, text="MC Fragment Farmer", font=("Arial", 10, "bold"), 
                background="#E1BEE7", foreground="#7B1FA2").pack(side=tk.LEFT)
        
        mc_fragment_farmer_help = tk.Label(mc_fragment_farmer_header, text="?", font=("Arial", 9, "bold"), 
                                          cursor="hand2", foreground="#7B1FA2", background="#E1BEE7")
        mc_fragment_farmer_help.pack(side=tk.LEFT, padx=(5, 0))
        self._create_frag_planner_help_tooltip(mc_fragment_farmer_help)
        
        frag_planner_inner = tk.Frame(mc_fragment_farmer_section, background="#F3E5F5", padx=8, pady=5)
        frag_planner_inner.pack(fill=tk.X)
        
        # Target fragment type selection with sprites
        target_row = tk.Frame(frag_planner_inner, background="#F3E5F5")
        target_row.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(target_row, text="Target:", font=("Arial", 9, "bold"), 
                background="#F3E5F5").pack(side=tk.LEFT)
        
        self.frag_target_var = tk.StringVar(value="common")
        frag_types = ['common', 'rare', 'epic', 'legendary', 'mythic']
        type_colors = {
            'common': '#808080', 'rare': '#4169E1', 'epic': '#9932CC',
            'legendary': '#FFD700', 'mythic': '#FF4500'
        }
        
        # Load fragment icons if available
        fragment_icon_map = {
            'common': 'fragmentcommon.png',
            'rare': 'fragmentrare.png',
            'epic': 'fragmentepic.png',
            'legendary': 'fragmentlegendary.png',
            'mythic': 'fragmentmythic.png',
        }
        
        self.frag_target_buttons = {}
        for frag_type in frag_types:
            # Create button frame
            btn_frame = tk.Frame(target_row, background="#F3E5F5", relief=tk.RAISED, borderwidth=1)
            btn_frame.pack(side=tk.LEFT, padx=2)
            
            # Try to load icon
            icon_label = None
            try:
                icon_name = fragment_icon_map.get(frag_type)
                if icon_name and hasattr(self, 'fragment_icons') and frag_type in self.fragment_icons:
                    icon_label = tk.Label(btn_frame, image=self.fragment_icons[frag_type], 
                                        background="#F3E5F5", cursor="hand2")
                    icon_label.pack(side=tk.LEFT, padx=2)
            except:
                pass
            
            # Text label as fallback or addition
            color = type_colors.get(frag_type, '#888888')
            text_label = tk.Label(btn_frame, text=frag_type[:3].upper(), font=("Arial", 8, "bold"),
                                 foreground=color, background="#F3E5F5", cursor="hand2",
                                 padx=4 if icon_label is None else 2)
            text_label.pack(side=tk.LEFT)
            
            # Bind single click to set target
            btn_frame.bind("<Button-1>", lambda e, ft=frag_type: self._set_frag_target(ft))
            if icon_label:
                icon_label.bind("<Button-1>", lambda e, ft=frag_type: self._set_frag_target(ft))
            text_label.bind("<Button-1>", lambda e, ft=frag_type: self._set_frag_target(ft))
            
            self.frag_target_buttons[frag_type] = btn_frame
        
        # MC Fragment Farmer button
        mc_fragment_farmer_button = tk.Button(
            frag_planner_inner,
            text="MC Fragment Farmer",
            command=self.run_mc_fragment_farmer,
            font=("Arial", 9),
            bg="#7B1FA2",
            fg="#FFFFFF",
            activebackground="#9C27B0",
            activeforeground="#FFFFFF",
            relief=tk.RAISED,
            borderwidth=2
        )
        mc_fragment_farmer_button.pack(fill=tk.X, pady=(5, 3))
        
        # === MC STAGE OPTIMIZER ===
        mc_stage_optimizer_section = tk.Frame(col_frame, background="#CE93D8", relief=tk.RIDGE, borderwidth=2)
        mc_stage_optimizer_section.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        mc_stage_optimizer_header = tk.Frame(mc_stage_optimizer_section, background="#CE93D8")
        mc_stage_optimizer_header.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        tk.Label(mc_stage_optimizer_header, text="MC Stage Optimizer", font=("Arial", 10, "bold"), 
                background="#CE93D8", foreground="#4A148C").pack(side=tk.LEFT)
        
        mc_stage_optimizer_help = tk.Label(mc_stage_optimizer_header, text="?", font=("Arial", 9, "bold"), 
                                          cursor="hand2", foreground="#4A148C", background="#CE93D8")
        mc_stage_optimizer_help.pack(side=tk.LEFT, padx=(5, 0))
        self._create_mc_stage_optimizer_tooltip(mc_stage_optimizer_help)
        
        # MC Stage Optimizer button (directly under Fragment Farmer)
        mc_stage_optimizer_row = tk.Frame(mc_stage_optimizer_section, background="#E1BEE7")
        mc_stage_optimizer_row.pack(fill=tk.X, padx=5, pady=5)
        
        # Goal Stage selector (for MC Stage Optimizer)
        goal_stage_row = tk.Frame(mc_stage_optimizer_row, background="#E1BEE7")
        goal_stage_row.pack(fill=tk.X, pady=(0, 3))
        
        tk.Label(goal_stage_row, text="Goal Stage:", font=("Arial", 9), 
                background="#E1BEE7").pack(side=tk.LEFT, padx=(0, 3))
        
        # Stage selector with +/- buttons
        stage_frame = tk.Frame(goal_stage_row, background="#E1BEE7")
        stage_frame.pack(side=tk.LEFT, padx=(0, 3))
        
        # Minus button
        stage_minus_btn = tk.Button(stage_frame, text="-", width=2, font=("Arial", 8, "bold"),
                                    command=self._decrease_goal_stage, background="#E1BEE7")
        stage_minus_btn.pack(side=tk.LEFT, padx=(0, 1))
        
        # Stage label (non-editable, only changed via buttons)
        self.stage_label = tk.Label(
            stage_frame,
            text="1",
            width=5,
            font=("Arial", 9, "bold"),
            background="#FFFFFF",
            foreground="#000000",
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.stage_label.pack(side=tk.LEFT, padx=(0, 1))
        
        # Plus button
        stage_plus_btn = tk.Button(stage_frame, text="+", width=2, font=("Arial", 8, "bold"),
                                   command=self._increase_goal_stage, background="#E1BEE7")
        stage_plus_btn.pack(side=tk.LEFT)
        
        # Initialize current_stage if not already set
        if not hasattr(self, 'current_stage'):
            self.current_stage = 1
        
        # Help icon for stage selection
        stage_help_label = tk.Label(goal_stage_row, text="?", font=("Arial", 9, "bold"), 
                                   cursor="hand2", foreground="#4A148C", background="#E1BEE7")
        stage_help_label.pack(side=tk.LEFT, padx=(5, 0))
        self._create_stage_help_tooltip(stage_help_label)
        
        # MC Stage Optimizer button
        mc_stage_optimizer_button = tk.Button(
            mc_stage_optimizer_row,
            text="MC Stage Optimizer",
            command=self.run_mc_stage_optimizer,
            font=("Arial", 9),
            bg="#9C27B0",
            fg="#FFFFFF",
            activebackground="#BA68C8",
            activeforeground="#FFFFFF",
            relief=tk.RAISED,
            borderwidth=2
        )
        mc_stage_optimizer_button.pack(fill=tk.X)
        
        # Initialize target button highlight
        self._update_frag_target_buttons()
    
    def _set_frag_target(self, frag_type):
        """Set the target fragment type for MC Fragment Farmer"""
        self.frag_target_var.set(frag_type)
        self._update_frag_target_buttons()
    
    def _update_frag_target_buttons(self):
        """Update visual state of fragment target buttons"""
        current = self.frag_target_var.get()
        for frag_type, btn_frame in self.frag_target_buttons.items():
            if frag_type == current:
                btn_frame.config(relief=tk.SUNKEN, background="#D1C4E9")
                # Update all child labels
                for child in btn_frame.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(background="#D1C4E9")
            else:
                btn_frame.config(relief=tk.RAISED, background="#F3E5F5")
                # Update all child labels
                for child in btn_frame.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(background="#F3E5F5")
    
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
    
    def _create_mc_stage_optimizer_tooltip(self, widget):
        """Creates a tooltip explaining the MC Stage Optimizer feature"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            tooltip_width = 380
            tooltip_height = 480
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            outer_frame = tk.Frame(tooltip, background="#9C27B0", relief=tk.FLAT)
            outer_frame.pack(padx=2, pady=2)
            
            inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
            inner_frame.pack(padx=1, pady=1)
            
            content = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
            content.pack()
            
            tk.Label(content, text="MC Stage Optimizer", font=("Arial", 10, "bold"),
                    background="#FFFFFF", foreground="#9C27B0").pack(anchor="w")
            
            lines = [
                "",
                "Find the optimal skill distribution to reach",
                "the highest possible stage.",
                "",
                "Uses Monte Carlo simulation to test all",
                "possible skill distributions and finds the",
                "one that reaches the highest average stage.",
                "",
                "Requirements:",
                "  - STR must always be included (STR > 0)",
                "  - Uses Archaeology Level for skill points",
                "",
                "The simulation starts at Stage 1 and runs",
                "until stamina is depleted, tracking the",
                "maximum stage reached.",
                "",
                "Selection Logic (in order):",
                "  1. Maximum Stage (integer):",
                "     - 7.5 and 7.3 both count as Stage 7",
                "  2. Fragments/h:",
                "     - If difference > 15%: select best",
                "     - If difference ≤ 15%: tie-breaker",
                "  3. XP/h (tie-breaker):",
                "     - Used when Fragments/h are within",
                "       15% (considered equal)",
                "",
                "Note: The Goal Stage setting above is NOT",
                "used by this optimizer. MC Stage Optimizer",
                "always simulates from Stage 1 to find the",
                "maximum reachable stage.",
                "",
                "Results show:",
                "  - Optimal skill distribution",
                "  - Performance metrics (XP/h, Fragments/h)",
                "  - Stage distribution histogram",
                "  - Top candidates comparison (if tied)",
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
    
    def _adjust_shared_planner_points(self, delta: int):
        """Adjust Archaeology Level (used by MC optimizers)"""
        new_val = max(1, min(100, self.shared_planner_points.get() + delta))
        self.shared_planner_points.set(new_val)
        self.shared_planner_points_label.config(text=str(new_val))
    
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
        calc_stage = self._get_calculation_stage()
        current_floors = self.calculate_floors_per_run(stats, calc_stage)
        if current_floors <= 0:
            return 0.0
        
        # Temporarily set this block to gilded and recalculate
        old_card_level = self.block_cards.get(block_type, 0)
        self.block_cards[block_type] = 2  # Gilded
        
        gilded_floors = self.calculate_floors_per_run(stats, calc_stage)
        
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
        calc_stage = self._get_calculation_stage()
        spawn_rates = get_normalized_spawn_rates(calc_stage)
        
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
    
    def update_avg_block_stats(self):
        """Calculate and display weighted average block stats for current stage"""
        if not hasattr(self, 'avg_block_hp_label'):
            return
        
        calc_stage = self._get_calculation_stage()
        spawn_rates = get_normalized_spawn_rates(calc_stage)
        block_mix = get_block_mix_for_floor(calc_stage)
        
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
        calc_stage = self._get_calculation_stage()
        spawn_rates = get_normalized_spawn_rates(calc_stage)
        
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
        self.stat_labels['crit_chance'].config(text=f"{stats['crit_chance']*100:.2f}%")
        self.stat_labels['crit_damage'].config(text=f"{stats['crit_damage']:.2f}x")
        self.stat_labels['one_hit_chance'].config(text=f"{stats['one_hit_chance']*100:.2f}%")
        self.stat_labels['xp_gain_total'].config(text=f"{stats['xp_gain_total']:.2f}x")
        self.stat_labels['fragment_mult'].config(text=f"{stats['fragment_mult']:.2f}x")
        
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
        
        # Calculate fragment upgrade efficiencies (3 types: Stage Rush, XP, Fragments)
        if hasattr(self, 'upgrade_efficiency_labels'):
            for upgrade_key in self.upgrade_efficiency_labels:
                upgrade_info = self.FRAGMENT_UPGRADES.get(upgrade_key, {})
                max_level = upgrade_info.get('max_level', 25)
                current_level = self.fragment_upgrade_levels.get(upgrade_key, 0)
                
                # Cost is now shown in tooltip, no need to update label
                
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
        
        # Update cards display (middle column)
        self.update_cards_display()
    
    def find_optimal_stage_for_fragment_type(self, stats: dict, target_frag_type: str, max_stage_to_test: int = 100) -> tuple:
        """
        Find the optimal starting stage for farming a specific fragment type.
        
        Tests different stages to find where the target fragment type spawns best
        and where the build can farm most efficiently.
        
        Args:
            stats: Current stats dictionary
            target_frag_type: 'common', 'rare', 'epic', 'legendary', or 'mythic'
            max_stage_to_test: Maximum stage to test (default 100)
        
        Returns:
            tuple: (optimal_stage, frags_per_hour_at_optimal_stage)
        """
        # Check if target fragment type is available at all
        # Test stages where this fragment type can spawn
        best_stage = 1
        best_frag_per_hour = 0.0
        
        # Test stages in ranges where the fragment type is available
        # Common: stage 1+, Rare: stage 3+, Epic: stage 6+, Legendary: stage 12+, Mythic: stage 20+
        stage_ranges = {
            'common': (1, max_stage_to_test),
            'rare': (3, max_stage_to_test),
            'epic': (6, max_stage_to_test),
            'legendary': (12, max_stage_to_test),
            'mythic': (20, max_stage_to_test),
        }
        
        min_stage, max_stage = stage_ranges.get(target_frag_type, (1, max_stage_to_test))
        
        # Test stages, but sample efficiently (not every single stage)
        # Test key stages: min, and then every 5-10 stages up to max
        stages_to_test = [min_stage]
        if max_stage > min_stage:
            # Add stages at intervals
            interval = max(1, (max_stage - min_stage) // 20)  # Test ~20 stages max
            for stage in range(min_stage + interval, min(max_stage + 1, max_stage_to_test + 1), interval):
                stages_to_test.append(stage)
            if stages_to_test[-1] != max_stage and max_stage <= max_stage_to_test:
                stages_to_test.append(max_stage)
        
        for test_stage in stages_to_test:
            # Check if fragment type is available at this stage
            available_blocks = get_available_blocks_at_stage(test_stage)
            if target_frag_type not in available_blocks:
                continue
            
            # Calculate frags/hour at this stage
            frags = self.calculate_fragments_per_run(stats, test_stage)
            floors = self.calculate_floors_per_run(stats, test_stage)
            run_duration = self.calculate_run_duration(stats, test_stage)
            runs_per_hour = 3600 / run_duration if run_duration > 0 else 0
            frag_per_hour = frags.get(target_frag_type, 0) * runs_per_hour
            
            if frag_per_hour > best_frag_per_hour:
                best_frag_per_hour = frag_per_hour
                best_stage = test_stage
        
        return (best_stage, best_frag_per_hour)
    
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
        calc_stage = self._get_calculation_stage()
        current_frags = self.calculate_fragments_per_run(stats, calc_stage)
        current_floors = self.calculate_floors_per_run(stats, calc_stage)
        current_xp = self.calculate_xp_per_run(stats, calc_stage)
        run_duration = self.calculate_run_duration(stats, calc_stage)
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
            new_frags = self.calculate_fragments_per_run(new_stats, calc_stage)
            new_floors = self.calculate_floors_per_run(new_stats, calc_stage)
            new_xp = self.calculate_xp_per_run(new_stats, calc_stage)
            new_run_duration = self.calculate_run_duration(new_stats, calc_stage)
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
        self.current_stage = 1
        if hasattr(self, 'stage_label'):
            self.stage_label.config(text="1")
        self.update_display()
        self.save_state()
    
    def _update_stage_display(self):
        """Update the stage label and handle side effects"""
        # Update label
        self.stage_label.config(text=str(self.current_stage))
        
        # Auto-adjust unlocked stage to at least match the selected stage
        current_unlocked = self.get_unlocked_stage()
        if current_unlocked < self.current_stage:
            self.unlocked_stage = self.current_stage
            self.unlocked_stage_label.config(text=str(self.current_stage))
            # Rebuild upgrade widgets if needed
            if hasattr(self, 'upgrades_container'):
                self._rebuild_upgrade_widgets()
        
        # Update display to refresh Stage Statistics
        self.update_display()
    
    def _increase_goal_stage(self):
        """Increase goal stage by 1"""
        self.current_stage += 1
        self._update_stage_display()
    
    def _decrease_goal_stage(self):
        """Decrease goal stage by 1 (minimum 1)"""
        if self.current_stage > 1:
            self.current_stage -= 1
            self._update_stage_display()
    
    def _show_loading_dialog(self, message="Running Monte Carlo simulation..."):
        """Show a modal loading dialog that blocks interaction with main window"""
        import threading
        
        loading_window = tk.Toplevel(self.window)
        loading_window.title("Loading...")
        loading_window.transient(self.window)
        loading_window.grab_set()  # Make it modal
        loading_window.resizable(False, False)
        
        # Center the window (wider for progress bar, taller for multi-line messages)
        loading_window.update_idletasks()
        x = (loading_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (loading_window.winfo_screenheight() // 2) - (200 // 2)
        loading_window.geometry(f"450x200+{x}+{y}")
        
        # Disable main window
        self.window.attributes('-disabled', True)
        
        # Create cancel event for thread communication
        cancel_event = threading.Event()
        
        # Loading content
        main_frame = tk.Frame(loading_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Message with wrapping (support multi-line)
        message_label = tk.Label(main_frame, text=message, font=("Arial", 10), 
                                wraplength=410, justify=tk.LEFT, anchor=tk.W)
        message_label.pack(pady=(0, 10), anchor=tk.W, fill=tk.X)
        
        # Progress bar frame
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Progress bar (maximum=100 for percentage)
        progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=410, maximum=100)
        progress_bar.pack(fill=tk.X)
        
        # Progress percentage label
        progress_label = tk.Label(main_frame, text="0%", 
                                 font=("Arial", 11, "bold"), foreground="#1976D2")
        progress_label.pack()
        
        # Handle window close - set cancel event
        def on_close():
            cancel_event.set()
            loading_window.destroy()
            self.window.attributes('-disabled', False)
        
        loading_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Store references for cleanup and progress updates
        loading_window.loading_refs = {
            'window': loading_window,
            'message_label': message_label,
            'progress_label': progress_label,
            'progress_bar': progress_bar,
            'main_window': self.window,
            'cancel_event': cancel_event
        }
        
        loading_window.update()
        return loading_window
    
    def _update_loading_progress(self, loading_window, current, total):
        """Update the progress percentage in the loading dialog"""
        try:
            if loading_window and hasattr(loading_window, 'loading_refs') and loading_window.winfo_exists():
                percentage = int((current / total) * 100) if total > 0 else 0
                if 'progress_label' in loading_window.loading_refs:
                    loading_window.loading_refs['progress_label'].config(text=f"{percentage}%")
                    loading_window.update()
        except (tk.TclError, RuntimeError):
            # Window was destroyed or main loop not running
            pass
    
    def _safe_update_progress_label(self, loading_window, text, current=None, total=None):
        """Safely update progress label text and progress bar"""
        try:
            if loading_window and hasattr(loading_window, 'loading_refs') and loading_window.winfo_exists():
                refs = loading_window.loading_refs
                
                # Update message text
                if 'message_label' in refs:
                    refs['message_label'].config(text=text)
                
                # Update progress bar and percentage if values provided
                if current is not None and total is not None and total > 0:
                    percentage = int((current / total) * 100)
                    # Update progress bar
                    if 'progress_bar' in refs:
                        refs['progress_bar']['value'] = percentage
                    # Update percentage label
                    if 'progress_label' in refs:
                        refs['progress_label'].config(text=f"{percentage}%")
                elif 'progress_label' in refs:
                    # Just update text if no progress values
                    refs['progress_label'].config(text=text)
                
                loading_window.update()
        except (tk.TclError, RuntimeError):
            # Window was destroyed or main loop not running
            pass
    
    def _close_loading_dialog(self, loading_window):
        """Close the loading dialog and re-enable main window"""
        if loading_window and loading_window.winfo_exists():
            loading_window.grab_release()
            loading_window.destroy()
        self.window.attributes('-disabled', False)
        self.window.focus_set()
    
    def run_mc_fragment_farmer(self):
        """Run Monte Carlo simulations to find optimal skill distribution for fragment farming.
        
        Tests different skill distributions using brute-force approach and finds the optimal stage
        for the target fragment type. Runs MC simulations starting at Stage 1 (always unbiased).
        Breakpoints are automatically considered in the MC simulation.
        
        Shows a single histogram with fragment/hour distribution for the best skill setup.
        """
        import threading
        
        # Save original skill points BEFORE reset (so we know what the user currently has)
        original_points = self.skill_points.copy()
        
        # Get target fragment type from Fragment Planner
        target_frag = self.frag_target_var.get() if hasattr(self, 'frag_target_var') else 'common'
        
        # Get Archaeology Level (shared across all planners)
        # This represents how many ADDITIONAL skill points to allocate optimally
        num_points = self.shared_planner_points.get() if hasattr(self, 'shared_planner_points') else 20
        
        # Show loading dialog
        loading_window = self._show_loading_dialog(
            f"Running MC Fragment Farmer ({target_frag.upper()})...\n"
            f"Testing skill distributions and finding optimal stage..."
        )
        
        def run_in_thread():
            # Always start at Floor 1 (unbiased) - this is critical for proper simulation
            starting_floor = 1
            
            # Start with original skill points (current distribution)
            # We will add num_points additional points optimally
            self.skill_points = original_points.copy()
            
            enrage_enabled = self.enrage_enabled.get() if hasattr(self, 'enrage_enabled') else True
            flurry_enabled = self.flurry_enabled.get() if hasattr(self, 'flurry_enabled') else True
            quake_enabled = self.quake_enabled.get() if hasattr(self, 'quake_enabled') else True
            block_cards = self.block_cards if hasattr(self, 'block_cards') else None
            
            # Use brute-force approach to test ALL possible skill distributions
            # This ensures we find the truly optimal distribution, not just a greedy approximation
            skills = ['strength', 'agility', 'intellect', 'perception', 'luck']
            best_distribution = {s: 0 for s in skills}
            best_frag_per_hour_avg = 0.0
            best_optimal_stage = 1
            best_stats = None
            
            cancel_event = loading_window.loading_refs['cancel_event']
            
            # Generate all possible distributions of num_points among 5 skills
            # This is a "stars and bars" problem: C(n+k-1, k-1) combinations
            # For 21 points, 5 skills: C(25,4) = 12,650 combinations
            def generate_distributions(n_points, n_skills):
                """Generate all ways to distribute n_points among n_skills"""
                if n_skills == 1:
                    yield (n_points,)
                    return
                for i in range(n_points + 1):
                    for rest in generate_distributions(n_points - i, n_skills - 1):
                        yield (i,) + rest
            
            # Calculate total number of combinations for progress tracking
            total_combinations = 1
            for i in range(4):
                total_combinations = total_combinations * (num_points + 1 + i) // (i + 1)
            
            from .monte_carlo_crit import MonteCarloCritSimulator
            simulator = MonteCarloCritSimulator()
            
            # Two-phase optimization approach:
            # Phase 1: Quick screening with few sims to identify promising candidates
            # Phase 2: Detailed testing of top candidates with full sims
            screening_sims = 200  # Fast screening with 200 sims
            refinement_sims = 500  # Full accuracy with 500 sims for top candidates
            top_candidates_ratio = 0.05  # Keep top 5% for refinement
            
            combination_count = 0
            candidate_scores = []  # List of (dist_tuple, avg_frag_per_hour, optimal_stage, stats)
            
            # Phase 1: Quick screening of all distributions
            try:
                if self.window.winfo_exists():
                    self.window.after(0, lambda: 
                                     self._safe_update_progress_label(loading_window, 
                                                                      f"Phase 1: Screening all distributions... (0/{total_combinations})",
                                                                      current=0, total=total_combinations))
            except (tk.TclError, RuntimeError):
                pass
            
            for dist_tuple in generate_distributions(num_points, len(skills)):
                if cancel_event.is_set():
                    self.skill_points = original_points.copy()
                    return
                
                combination_count += 1
                
                # Update progress every 10 combinations for smoother progress
                if combination_count % 10 == 0 or combination_count == total_combinations:
                    try:
                        if self.window.winfo_exists():
                            self.window.after(0, lambda c=combination_count, t=total_combinations: 
                                             self._safe_update_progress_label(loading_window, 
                                                                              f"Phase 1: Screening distributions... ({c}/{t})",
                                                                              current=c, total=t))
                    except (tk.TclError, RuntimeError):
                        cancel_event.set()
                        return
                
                # Apply distribution temporarily (on top of original_points)
                for skill, points in zip(skills, dist_tuple):
                    self.skill_points[skill] = original_points.get(skill, 0) + points
                
                new_stats = self.get_total_stats()
                
                # Find optimal stage for this build
                optimal_stage, _ = self.find_optimal_stage_for_fragment_type(
                    new_stats, target_frag
                )
                
                # Quick screening: Run few MC simulations
                frag_per_hour_samples = []
                
                for _ in range(screening_sims):
                    result = simulator.simulate_run(
                        new_stats, starting_floor, use_crit=True,
                        enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled,
                        quake_enabled=quake_enabled, block_cards=block_cards, return_metrics=True
                    )
                    
                    floors_cleared = result['floors_cleared']
                    fragments = result.get('fragments', {})
                    target_frag_count = fragments.get(target_frag, 0)
                    
                    # Use MC run duration from metrics
                    run_duration_seconds = result.get('run_duration_seconds', 1.0)
                    runs_per_hour = 3600 / run_duration_seconds if run_duration_seconds > 0 else 0
                    frags_per_hour = target_frag_count * runs_per_hour
                    frag_per_hour_samples.append(frags_per_hour)
                
                avg_frag_per_hour = sum(frag_per_hour_samples) / len(frag_per_hour_samples) if frag_per_hour_samples else 0
                
                # Store candidate for potential refinement
                candidate_scores.append((dist_tuple, avg_frag_per_hour, optimal_stage, new_stats.copy()))
                
                # Revert changes
                self.skill_points = original_points.copy()
            
            if cancel_event.is_set():
                return
            
            # Sort candidates by performance (best first)
            candidate_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Phase 2: Refine top candidates with full simulations
            num_refinement = max(1, int(len(candidate_scores) * top_candidates_ratio))
            top_candidates = candidate_scores[:num_refinement]
            
            try:
                if self.window.winfo_exists():
                    self.window.after(0, lambda: 
                                     self._safe_update_progress_label(loading_window, 
                                                                      f"Phase 2: Refining top {num_refinement} candidates... (0/{num_refinement})",
                                                                      current=0, total=num_refinement))
            except (tk.TclError, RuntimeError):
                pass
            
            for refine_idx, (dist_tuple, screening_score, optimal_stage, stats_copy) in enumerate(top_candidates):
                if cancel_event.is_set():
                    self.skill_points = original_points.copy()
                    return
                
                # Update progress
                if (refine_idx + 1) % 5 == 0:
                    progress_pct = int(((refine_idx + 1) / num_refinement) * 100)
                    try:
                        if self.window.winfo_exists():
                            self.window.after(0, lambda p=progress_pct, c=refine_idx+1, t=num_refinement: 
                                             self._safe_update_progress_label(loading_window, 
                                                                              f"Phase 2: Refining {p}% ({c}/{t})"))
                    except (tk.TclError, RuntimeError):
                        cancel_event.set()
                        return
                
                # Apply distribution temporarily
                for skill, points in zip(skills, dist_tuple):
                    self.skill_points[skill] = original_points.get(skill, 0) + points
                
                new_stats = self.get_total_stats()
                
                # Run full MC simulations for accurate estimate
                frag_per_hour_samples = []
                
                for _ in range(refinement_sims):
                    result = simulator.simulate_run(
                        new_stats, starting_floor, use_crit=True,
                        enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled,
                        quake_enabled=quake_enabled, block_cards=block_cards, return_metrics=True
                    )
                    
                    floors_cleared = result['floors_cleared']
                    fragments = result.get('fragments', {})
                    target_frag_count = fragments.get(target_frag, 0)
                    
                    # Use MC run duration from metrics
                    run_duration_seconds = result.get('run_duration_seconds', 1.0)
                    runs_per_hour = 3600 / run_duration_seconds if run_duration_seconds > 0 else 0
                    frags_per_hour = target_frag_count * runs_per_hour
                    frag_per_hour_samples.append(frags_per_hour)
                
                avg_frag_per_hour = sum(frag_per_hour_samples) / len(frag_per_hour_samples) if frag_per_hour_samples else 0
                
                # Update best if this is better
                if avg_frag_per_hour > best_frag_per_hour_avg:
                    best_frag_per_hour_avg = avg_frag_per_hour
                    best_distribution = {s: p for s, p in zip(skills, dist_tuple)}
                    best_optimal_stage = optimal_stage
                    best_stats = new_stats.copy()
                
                # Revert changes
                self.skill_points = original_points.copy()
            
            if cancel_event.is_set():
                try:
                    if self.window.winfo_exists():
                        self.window.after(0, lambda: self._close_loading_dialog(loading_window))
                except (tk.TclError, RuntimeError):
                    pass
                return
            
            # Phase 2: Run full MC simulation (1000 runs) with best distribution
            # Apply best distribution
            for skill, points in best_distribution.items():
                self.skill_points[skill] = original_points.get(skill, 0) + points
            
            final_stats = self.get_total_stats()
            
            # Verify optimal stage (might have changed slightly)
            final_optimal_stage, _ = self.find_optimal_stage_for_fragment_type(
                final_stats, target_frag
            )
            
            # Run 1000 MC simulations starting at Stage 1
            frag_per_hour_samples = []
            metrics_samples = []  # List of dicts with xp_per_run, total_fragments, floors_cleared, run_duration_seconds
            total_sims = 1000
            sim_count = 0
            
            try:
                if self.window.winfo_exists():
                    self.window.after(0, lambda: 
                                     self._safe_update_progress_label(loading_window, 
                                                                      f"Phase 3: Running {total_sims} final simulations... (0/{total_sims})",
                                                                      current=0, total=total_sims))
            except (tk.TclError, RuntimeError):
                pass
            
            for i in range(total_sims):
                if cancel_event.is_set():
                    # Restore original skill points
                    self.skill_points = original_points.copy()
                    try:
                        if self.window.winfo_exists():
                            self.window.after(0, lambda: self._close_loading_dialog(loading_window))
                    except (tk.TclError, RuntimeError):
                        pass
                    return
                
                # Run simulation starting at Stage 1 (always unbiased)
                # Breakpoints are automatically considered in simulate_run
                result = simulator.simulate_run(
                    final_stats, starting_floor, use_crit=True,  # Use crit
                    enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled,
                    quake_enabled=quake_enabled, block_cards=block_cards, return_metrics=True
                )
                
                # Calculate fragments per hour using MC metrics
                floors_cleared = result['floors_cleared']
                fragments = result.get('fragments', {})
                target_frag_count = fragments.get(target_frag, 0)
                run_duration_seconds = result.get('run_duration_seconds', 1.0)
                
                runs_per_hour = 3600 / run_duration_seconds if run_duration_seconds > 0 else 0
                frags_per_hour = target_frag_count * runs_per_hour
                frag_per_hour_samples.append(frags_per_hour)
                
                # Collect metrics for this run
                metrics_samples.append({
                    'xp_per_run': result.get('xp_per_run', 0.0),
                    'total_fragments': result.get('total_fragments', 0.0),
                    'fragments': result.get('fragments', {}).copy(),  # Store fragments by type
                    'floors_cleared': result.get('floors_cleared', 0.0),
                    'run_duration_seconds': run_duration_seconds,
                })
                
                # Update progress
                sim_count += 1
                current_count = sim_count
                try:
                    if self.window.winfo_exists():
                        self.window.after(0, lambda c=current_count, t=total_sims: 
                                         self._update_loading_progress(loading_window, c, t))
                except (tk.TclError, RuntimeError):
                    # Window destroyed, cancel
                    cancel_event.set()
                    return
            
            # Restore original skill points
            self.skill_points = original_points.copy()
            
            if cancel_event.is_set():
                self.window.after(0, lambda: self._close_loading_dialog(loading_window))
                return
            
            # Get skill points for display
            skill_points_display = {}
            for skill in skills:
                current = original_points.get(skill, 0)
                added = best_distribution.get(skill, 0)
                skill_points_display[skill] = current + added
            
            # Restore original skill points after MC simulation (don't reset to 0)
            # Use a closure to capture original_points
            def restore_and_update():
                self.skill_points = original_points.copy()
                self.update_display()
            try:
                if self.window.winfo_exists():
                    self.window.after(0, restore_and_update)
            except (tk.TclError, RuntimeError):
                # Window destroyed, just restore skill points directly
                self.skill_points = original_points.copy()
            
            # Close loading dialog and show results
            try:
                if self.window.winfo_exists():
                    self.window.after(0, lambda: (
                        self._close_loading_dialog(loading_window),
                        self._show_fragment_farmer_results(
                            frag_per_hour_samples, skill_points_display, num_points,
                            target_frag, final_optimal_stage, metrics_samples
                        )
                    ))
            except (tk.TclError, RuntimeError):
                # Window destroyed, just restore skill points
                self.skill_points = original_points.copy()
        
        # Run in separate thread to avoid blocking UI
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    def run_mc_stage_optimizer(self):
        """Run Monte Carlo simulations to find optimal skill distribution for maximum stage reached.
        
        Tests different skill distributions using brute-force approach, but only considers
        distributions where STR > 0 (STR must always be included). Runs MC simulations starting
        at Stage 1 (always unbiased). Finds the skill distribution that reaches the highest
        average maximum stage.
        
        Shows a histogram with max stage distribution for the best skill setup.
        """
        import threading
        
        # Save original skill points BEFORE reset (so we know what the user currently has)
        original_points = self.skill_points.copy()
        
        # Get Archaeology Level (shared across all planners)
        # This represents how many ADDITIONAL skill points to allocate optimally
        num_points = self.shared_planner_points.get() if hasattr(self, 'shared_planner_points') else 20
        
        # Show loading dialog
        loading_window = self._show_loading_dialog(
            f"Running MC Stage Optimizer...\n"
            f"Testing {num_points} skill points (STR required)..."
        )
        
        def run_in_thread():
            # Always start at Floor 1 (unbiased) - this is critical for proper simulation
            starting_floor = 1
            
            # Start with original skill points (current distribution)
            # We will add num_points additional points optimally
            self.skill_points = original_points.copy()
            
            enrage_enabled = self.enrage_enabled.get() if hasattr(self, 'enrage_enabled') else True
            flurry_enabled = self.flurry_enabled.get() if hasattr(self, 'flurry_enabled') else True
            quake_enabled = self.quake_enabled.get() if hasattr(self, 'quake_enabled') else True
            block_cards = self.block_cards if hasattr(self, 'block_cards') else None
            
            # Use brute-force approach to test ALL possible skill distributions
            # But skip distributions where STR = 0 (STR must always be included)
            skills = ['strength', 'agility', 'intellect', 'perception', 'luck']
            best_distribution = {s: 0 for s in skills}
            best_avg_max_stage = 0.0
            best_stats = None
            best_fragments_per_hour = 0.0
            best_xp_per_hour = 0.0
            top_3_candidates = []  # List of (dist_dict, max_stage_int, fragments_per_hour, xp_per_hour)
            tied_distributions_count = 0  # Track how many distributions reached the best stage
            
            cancel_event = loading_window.loading_refs['cancel_event']
            
            # Generate all possible distributions of num_points among 5 skills
            # This is a "stars and bars" problem: C(n+k-1, k-1) combinations
            # For 21 points, 5 skills: C(25,4) = 12,650 combinations
            def generate_distributions(n_points, n_skills):
                """Generate all ways to distribute n_points among n_skills"""
                if n_skills == 1:
                    yield (n_points,)
                    return
                for i in range(n_points + 1):
                    for rest in generate_distributions(n_points - i, n_skills - 1):
                        yield (i,) + rest
            
            # Calculate total number of combinations for progress tracking
            total_combinations = 1
            for i in range(4):
                total_combinations = total_combinations * (num_points + 1 + i) // (i + 1)
            
            from .monte_carlo_crit import MonteCarloCritSimulator
            simulator = MonteCarloCritSimulator()
            
            # Two-phase optimization approach:
            # Phase 1: Quick screening with few sims to identify promising candidates
            # Phase 2: Detailed testing of top candidates with full sims
            screening_sims = 200  # Fast screening with 200 sims
            refinement_sims = 500  # Full accuracy with 500 sims for top candidates
            top_candidates_ratio = 0.05  # Keep top 5% for refinement
            
            combination_count = 0
            candidate_scores = []  # List of (dist_tuple, avg_max_stage, stats)
            
            # Track highest stage reached across all distributions for live display
            # Note: This tracks the ACTUAL highest stage reached in simulations (not goal-1)
            # If a simulation reaches goal+2, that will be counted as the highest stage
            global_highest_stage = 0.0
            stage_count_dict = {}  # Track how many times each stage was reached (counts each MC simulation)
            
            # Count actual valid distributions (where STR > 0) before screening
            # This ensures accurate progress tracking
            try:
                if self.window.winfo_exists():
                    self.window.after(0, lambda: 
                                     self._safe_update_progress_label(loading_window, 
                                                                      "Phase 1: Counting distributions...",
                                                                      current=0, total=100))
            except (tk.TclError, RuntimeError):
                pass
            
            actual_valid_count = 0
            for dist_tuple in generate_distributions(num_points, len(skills)):
                total_str = original_points.get('strength', 0) + dist_tuple[0]
                if total_str > 0:
                    actual_valid_count += 1
            
            # Phase 1: Quick screening of all distributions (only those with STR > 0)
            try:
                if self.window.winfo_exists():
                    self.window.after(0, lambda: 
                                     self._safe_update_progress_label(loading_window, 
                                                                      f"Phase 1: Screening distributions with STR... (0/{actual_valid_count})",
                                                                      current=0, total=actual_valid_count))
            except (tk.TclError, RuntimeError):
                pass
            
            for dist_tuple in generate_distributions(num_points, len(skills)):
                if cancel_event.is_set():
                    self.skill_points = original_points.copy()
                    return
                
                # Skip distributions where total STR would be 0 (STR must always be included)
                # Check if original STR + new STR points > 0
                total_str = original_points.get('strength', 0) + dist_tuple[0]
                if total_str == 0:
                    continue
                
                combination_count += 1
                
                # Apply distribution temporarily (on top of original_points)
                for skill, points in zip(skills, dist_tuple):
                    self.skill_points[skill] = original_points.get(skill, 0) + points
                
                new_stats = self.get_total_stats()
                
                # Quick screening: Run few MC simulations
                max_stage_samples = []
                metrics_samples_screening = []
                
                for _ in range(screening_sims):
                    result = simulator.simulate_run(
                        new_stats, starting_floor, use_crit=True,
                        enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled,
                        quake_enabled=quake_enabled, block_cards=block_cards, return_metrics=True
                    )
                    
                    max_stage = result['max_stage_reached']
                    max_stage_samples.append(max_stage)
                    metrics_samples_screening.append({
                        'total_fragments': result.get('total_fragments', 0.0),
                        'xp_per_run': result.get('xp_per_run', 0.0),
                        'run_duration_seconds': result.get('run_duration_seconds', 1.0),
                    })
                    
                    # Track highest stage reached (integer stage for counting)
                    stage_int = int(max_stage)
                    if stage_int > global_highest_stage:
                        global_highest_stage = stage_int
                    # Count how many times each stage was reached
                    stage_count_dict[stage_int] = stage_count_dict.get(stage_int, 0) + 1
                
                avg_max_stage = sum(max_stage_samples) / len(max_stage_samples) if max_stage_samples else 0
                # Calculate fragments/h and xp/h for screening
                avg_run_duration = sum(m['run_duration_seconds'] for m in metrics_samples_screening) / len(metrics_samples_screening) if metrics_samples_screening else 1.0
                avg_fragments = sum(m['total_fragments'] for m in metrics_samples_screening) / len(metrics_samples_screening) if metrics_samples_screening else 0.0
                avg_xp = sum(m['xp_per_run'] for m in metrics_samples_screening) / len(metrics_samples_screening) if metrics_samples_screening else 0.0
                fragments_per_hour_screening = (avg_fragments * 3600 / avg_run_duration) if avg_run_duration > 0 else 0.0
                xp_per_hour_screening = (avg_xp * 3600 / avg_run_duration) if avg_run_duration > 0 else 0.0
                
                # Store candidate for potential refinement (include fragments/h and xp/h for tie-breaking)
                candidate_scores.append((dist_tuple, avg_max_stage, new_stats.copy(), fragments_per_hour_screening, xp_per_hour_screening))
                
                # Revert changes
                self.skill_points = original_points.copy()
                
                # Update progress with live statistics about highest stage reached
                # Update every 10 combinations or on first combination for smoother updates
                if combination_count % 10 == 0 or combination_count == 1:
                    total_sims_so_far = combination_count * screening_sims
                    
                    # Show top 3 most frequently reached stages (sorted by stage number, highest first)
                    sorted_stages = sorted(stage_count_dict.items(), key=lambda x: x[0], reverse=True)
                    top_stages_info = []
                    for stage, count in sorted_stages[:3]:
                        pct = (count / total_sims_so_far * 100) if total_sims_so_far > 0 else 0.0
                        top_stages_info.append(f"Stage {stage}: {count}x ({pct:.1f}%)")
                    
                    # Format stages text with line breaks (one per line)
                    if top_stages_info:
                        stages_text = "\n".join(top_stages_info)
                    else:
                        stages_text = "No data yet"
                    
                    try:
                        if self.window.winfo_exists():
                            self.window.after(0, lambda c=combination_count, t=actual_valid_count, 
                                             stages_txt=stages_text: 
                                             self._safe_update_progress_label(loading_window, 
                                                                              f"Phase 1: Screening ({c}/{t})\n"
                                                                              f"{stages_txt}",
                                                                              current=c, total=t))
                    except (tk.TclError, RuntimeError):
                        pass
            
            if cancel_event.is_set():
                return
            
            # Sort candidates by performance (best first)
            candidate_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Check for ties at the top (same avg_max_stage) - show in progress
            if candidate_scores:
                best_screening_stage = candidate_scores[0][1]
                tied_at_top = sum(1 for c in candidate_scores if abs(c[1] - best_screening_stage) < 0.01)  # Within 0.01 tolerance
                if tied_at_top > 1:
                    try:
                        if self.window.winfo_exists():
                            self.window.after(0, lambda tied=tied_at_top, stage=best_screening_stage: 
                                             self._safe_update_progress_label(loading_window, 
                                                                              f"Phase 1: {tied} distributions reached Stage {stage:.1f}! Refining...",
                                                                              current=actual_valid_count, total=actual_valid_count))
                    except (tk.TclError, RuntimeError):
                        pass
            
            # Phase 2: Refine top candidates with full simulations
            num_refinement = max(1, int(len(candidate_scores) * top_candidates_ratio))
            top_candidates = candidate_scores[:num_refinement]
            
            try:
                if self.window.winfo_exists():
                    self.window.after(0, lambda: 
                                     self._safe_update_progress_label(loading_window, 
                                                                      f"Phase 2: Refining top {num_refinement} candidates... (0/{num_refinement})",
                                                                      current=0, total=num_refinement))
            except (tk.TclError, RuntimeError):
                pass
            
            for refine_idx, (dist_tuple, screening_score, stats_copy, screening_frags_h, screening_xp_h) in enumerate(top_candidates):
                if cancel_event.is_set():
                    self.skill_points = original_points.copy()
                    return
                
                # Update progress every candidate
                try:
                    if self.window.winfo_exists():
                        self.window.after(0, lambda c=refine_idx+1, t=num_refinement: 
                                         self._safe_update_progress_label(loading_window, 
                                                                          f"Phase 2: Refining top candidates... ({c}/{t})",
                                                                          current=c, total=t))
                except (tk.TclError, RuntimeError):
                    cancel_event.set()
                    return
                
                # Apply distribution temporarily
                for skill, points in zip(skills, dist_tuple):
                    self.skill_points[skill] = original_points.get(skill, 0) + points
                
                new_stats = self.get_total_stats()
                
                # Run full MC simulations for accurate estimate
                max_stage_samples = []
                metrics_samples_refinement = []
                
                for _ in range(refinement_sims):
                    result = simulator.simulate_run(
                        new_stats, starting_floor, use_crit=True,
                        enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled,
                        quake_enabled=quake_enabled, block_cards=block_cards, return_metrics=True
                    )
                    
                    max_stage = result['max_stage_reached']
                    max_stage_samples.append(max_stage)
                    metrics_samples_refinement.append({
                        'total_fragments': result.get('total_fragments', 0.0),
                        'xp_per_run': result.get('xp_per_run', 0.0),
                        'run_duration_seconds': result.get('run_duration_seconds', 1.0),
                    })
                
                avg_max_stage = sum(max_stage_samples) / len(max_stage_samples) if max_stage_samples else 0
                max_stage_int = int(avg_max_stage)  # Integer max stage for comparison
                
                # Calculate fragments/h and xp/h
                avg_run_duration = sum(m['run_duration_seconds'] for m in metrics_samples_refinement) / len(metrics_samples_refinement) if metrics_samples_refinement else 1.0
                avg_fragments = sum(m['total_fragments'] for m in metrics_samples_refinement) / len(metrics_samples_refinement) if metrics_samples_refinement else 0.0
                avg_xp = sum(m['xp_per_run'] for m in metrics_samples_refinement) / len(metrics_samples_refinement) if metrics_samples_refinement else 0.0
                fragments_per_hour = (avg_fragments * 3600 / avg_run_duration) if avg_run_duration > 0 else 0.0
                xp_per_hour = (avg_xp * 3600 / avg_run_duration) if avg_run_duration > 0 else 0.0
                
                # Store in top 3 candidates (for display if there's a tie)
                dist_dict = {s: p for s, p in zip(skills, dist_tuple)}
                top_3_candidates.append((dist_dict.copy(), max_stage_int, fragments_per_hour, xp_per_hour))
                
                # Update best if this is better
                # Compare by integer max stage first, then by fragments/h (with 15% relative tolerance), then by xp/h
                best_max_stage_int = int(best_avg_max_stage)
                
                is_better = False
                is_tie = False
                if max_stage_int > best_max_stage_int:
                    is_better = True
                    tied_distributions_count = 1  # Reset count when new best stage found
                elif max_stage_int == best_max_stage_int:
                    is_tie = True
                    # Same max stage - check fragments/h with relative tolerance (15%)
                    if best_fragments_per_hour > 0:
                        relative_diff = abs(fragments_per_hour - best_fragments_per_hour) / best_fragments_per_hour
                        if fragments_per_hour > best_fragments_per_hour and relative_diff > 0.15:
                            # Fragments/h is significantly better (>15% relative difference)
                            is_better = True
                            tied_distributions_count = 1  # Reset count when better found
                        elif relative_diff <= 0.15:
                            # Fragments/h are within 15% (tie) - use xp/h as tiebreaker
                            if xp_per_hour > best_xp_per_hour:
                                is_better = True
                                tied_distributions_count = 1  # Reset count when better found
                            else:
                                # Still a tie - increment counter
                                tied_distributions_count += 1
                        else:
                            # Fragments/h is worse by more than 15%, so not better, but still same stage
                            tied_distributions_count += 1
                    else:
                        # best_fragments_per_hour is 0, so any positive value is better
                        if fragments_per_hour > 0:
                            is_better = True
                            tied_distributions_count = 1  # Reset count when better found
                        elif fragments_per_hour == 0:
                            # Both are 0, use xp/h as tiebreaker
                            if xp_per_hour > best_xp_per_hour:
                                is_better = True
                                tied_distributions_count = 1  # Reset count when better found
                            else:
                                # Still a tie - increment counter
                                tied_distributions_count += 1
                
                if is_better:
                    best_avg_max_stage = avg_max_stage
                    best_distribution = dist_dict
                    best_stats = new_stats.copy()
                    best_fragments_per_hour = fragments_per_hour
                    best_xp_per_hour = xp_per_hour
                    
                    # Update progress to show tie information if applicable
                    if is_tie and tied_distributions_count > 1:
                        try:
                            if self.window.winfo_exists():
                                self.window.after(0, lambda c=refine_idx+1, t=num_refinement, tied=tied_distributions_count, stage=max_stage_int: 
                                                 self._safe_update_progress_label(loading_window, 
                                                                                  f"Phase 2: Refining... ({c}/{t}) | {tied} distributions reached Stage {stage}!",
                                                                                  current=c, total=t))
                        except (tk.TclError, RuntimeError):
                            pass
                elif is_tie:
                    # Update progress to show tie information
                    try:
                        if self.window.winfo_exists():
                            self.window.after(0, lambda c=refine_idx+1, t=num_refinement, tied=tied_distributions_count, stage=max_stage_int: 
                                             self._safe_update_progress_label(loading_window, 
                                                                              f"Phase 2: Refining... ({c}/{t}) | {tied} distributions reached Stage {stage}!",
                                                                              current=c, total=t))
                    except (tk.TclError, RuntimeError):
                        pass
                
                # Revert changes
                self.skill_points = original_points.copy()
            
            if cancel_event.is_set():
                try:
                    if self.window.winfo_exists():
                        self.window.after(0, lambda: self._close_loading_dialog(loading_window))
                except (tk.TclError, RuntimeError):
                    pass
                return
            
            # Phase 3: Run full MC simulation (1000 runs) with best distribution
            # Apply best distribution
            for skill, points in best_distribution.items():
                self.skill_points[skill] = original_points.get(skill, 0) + points
            
            final_stats = self.get_total_stats()
            
            # Run 1000 MC simulations starting at Stage 1
            max_stage_samples = []
            metrics_samples = []  # List of dicts with xp_per_run, total_fragments, floors_cleared, run_duration_seconds
            total_sims = 1000
            sim_count = 0
            
            try:
                if self.window.winfo_exists():
                    self.window.after(0, lambda: 
                                     self._safe_update_progress_label(loading_window, 
                                                                      f"Phase 3: Running {total_sims} final simulations... (0/{total_sims})",
                                                                      current=0, total=total_sims))
            except (tk.TclError, RuntimeError):
                pass
            
            for i in range(total_sims):
                if cancel_event.is_set():
                    # Restore original skill points
                    self.skill_points = original_points.copy()
                    try:
                        if self.window.winfo_exists():
                            self.window.after(0, lambda: self._close_loading_dialog(loading_window))
                    except (tk.TclError, RuntimeError):
                        pass
                    return
                
                # Run simulation starting at Stage 1 (always unbiased)
                result = simulator.simulate_run(
                    final_stats, starting_floor, use_crit=True,
                    enrage_enabled=enrage_enabled, flurry_enabled=flurry_enabled,
                    quake_enabled=quake_enabled, block_cards=block_cards, return_metrics=True
                )
                
                max_stage = result['max_stage_reached']
                max_stage_samples.append(max_stage)
                
                # Collect metrics for this run
                metrics_samples.append({
                    'xp_per_run': result.get('xp_per_run', 0.0),
                    'total_fragments': result.get('total_fragments', 0.0),
                    'fragments': result.get('fragments', {}).copy(),  # Store fragments by type
                    'floors_cleared': result.get('floors_cleared', 0.0),
                    'run_duration_seconds': result.get('run_duration_seconds', 1.0),
                })
                
                # Update progress every 10 simulations
                sim_count += 1
                if sim_count % 10 == 0 or sim_count == total_sims:
                    try:
                        if self.window.winfo_exists():
                            self.window.after(0, lambda c=sim_count, t=total_sims: 
                                             self._safe_update_progress_label(loading_window, 
                                                                              f"Phase 3: Running final simulations... ({c}/{t})",
                                                                              current=c, total=t))
                    except (tk.TclError, RuntimeError):
                        pass
            
            # Get skill points for display (current + best distribution)
            skill_points_display = {}
            added_distribution = {}  # Only the new points added
            for skill in skills:
                current = original_points.get(skill, 0)
                added = best_distribution.get(skill, 0)
                skill_points_display[skill] = current + added
                added_distribution[skill] = added
            
            # Sort top 3 candidates by max_stage (int) then fragments/h, then xp/h, and keep only top 3
            top_3_candidates.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
            top_3_candidates = top_3_candidates[:3]
            
            # Close loading dialog and show results
            try:
                if self.window.winfo_exists():
                    self.window.after(0, lambda: (
                        self._close_loading_dialog(loading_window),
                        self._show_stage_optimizer_results(
                            max_stage_samples, skill_points_display, added_distribution, num_points, metrics_samples, top_3_candidates
                        )
                    ))
            except (tk.TclError, RuntimeError):
                # Window destroyed, just restore skill points
                self.skill_points = original_points.copy()
        
        # Run in separate thread to avoid blocking UI
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    def _show_stage_optimizer_results(self, max_stage_samples, skill_points_display, added_distribution, num_points, metrics_samples, top_3_candidates=None):
        """Show histogram window with max stage distribution and optimal skill setup"""
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
        
        # Create window in normal GUI style (not Matrix)
        result_window = tk.Toplevel(self.window)
        result_window.title("MC Stage Optimizer Results")
        result_window.transient(self.window)
        
        # Set window to fullscreen (maximized)
        result_window.state('zoomed')  # Maximize on Windows
        result_window.resizable(True, True)
        
        # Main container
        main_frame = ttk.Frame(result_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, 
                               text=f"MC Stage Optimizer Results - 1000 simulations\n"
                                    f"Finding optimal skill distribution for maximum stage reached\n"
                                    f"Used {num_points} additional points (Arch Level: {num_points})", 
                               font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        if max_stage_samples:
            std_val = np.std(max_stage_samples)
            min_val = np.min(max_stage_samples)
            max_val = np.max(max_stage_samples)
            
            stats_text = f"""Stage Statistics:
Std Dev: {std_val:.2f} stages
Min: {min_val:.0f} stages
Max: {max_val:.0f} stages"""
            
            stats_label = ttk.Label(stats_frame, text=stats_text, font=("Courier", 9), 
                                   justify=tk.LEFT)
            stats_label.pack(anchor=tk.W)
        else:
            ttk.Label(stats_frame, text="No simulation data available", 
                     foreground="gray").pack()
        
        # Metrics frame (XP/h, Fragments/h, Floors/run)
        if metrics_samples:
            metrics_frame = ttk.LabelFrame(main_frame, text="Performance Metrics", padding="10")
            metrics_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            
            # Calculate averages
            avg_floors_per_run = np.mean([m['floors_cleared'] for m in metrics_samples])
            avg_xp_per_run = np.mean([m['xp_per_run'] for m in metrics_samples])
            avg_total_fragments = np.mean([m['total_fragments'] for m in metrics_samples])
            avg_run_duration = np.mean([m['run_duration_seconds'] for m in metrics_samples])
            
            # Calculate per hour
            runs_per_hour = 3600 / avg_run_duration if avg_run_duration > 0 else 0
            xp_per_hour = avg_xp_per_run * runs_per_hour
            fragments_per_hour = avg_total_fragments * runs_per_hour
            
            # Calculate fragments per hour by type
            frag_types = ['common', 'rare', 'epic', 'legendary', 'mythic']
            avg_frags_by_type = {}
            frags_per_hour_by_type = {}
            for frag_type in frag_types:
                avg_frags = np.mean([m.get('fragments', {}).get(frag_type, 0.0) for m in metrics_samples])
                avg_frags_by_type[frag_type] = avg_frags
                frags_per_hour_by_type[frag_type] = avg_frags * runs_per_hour
            
            metrics_text = f"""Floors/Run: {avg_floors_per_run:.2f}
XP/h: {xp_per_hour:.1f}
Fragments/h: {fragments_per_hour:.2f}"""
            
            metrics_label = ttk.Label(metrics_frame, text=metrics_text, font=("Courier", 9), 
                                     justify=tk.LEFT)
            metrics_label.pack(anchor=tk.W)
            
            # Fragments by type with icons
            frag_display_frame = tk.Frame(metrics_frame)
            frag_display_frame.pack(anchor=tk.W, pady=(5, 0))
            
            frag_icon_map = {
                'common': 'fragmentcommon.png',
                'rare': 'fragmentrare.png',
                'epic': 'fragmentepic.png',
                'legendary': 'fragmentlegendary.png',
                'mythic': 'fragmentmythic.png',
            }
            
            frag_labels = []
            for frag_type in frag_types:
                frag_per_hour = frags_per_hour_by_type.get(frag_type, 0.0)
                if frag_per_hour > 0.001:  # Only show if > 0.001
                    frag_item_frame = tk.Frame(frag_display_frame)
                    frag_item_frame.pack(side=tk.LEFT, padx=(0, 15))
                    
                    # Try to load icon
                    try:
                        icon_path = get_resource_path(f"sprites/archaeology/{frag_icon_map[frag_type]}")
                        if icon_path.exists():
                            icon_image = Image.open(icon_path)
                            icon_image = icon_image.resize((16, 16), Image.Resampling.LANCZOS)
                            icon_photo = ImageTk.PhotoImage(icon_image)
                            icon_label = tk.Label(frag_item_frame, image=icon_photo)
                            icon_label.image = icon_photo  # Keep reference
                            icon_label.pack(side=tk.LEFT, padx=(0, 3))
                    except:
                        pass
                    
                    # Fragment type and value
                    frag_label = tk.Label(
                        frag_item_frame,
                        text=f"{frag_type.capitalize()}: {frag_per_hour:.2f}/h",
                        font=("Arial", 9)
                    )
                    frag_label.pack(side=tk.LEFT)
                    frag_labels.append(frag_item_frame)
            
            # Adjust row numbers for subsequent elements
            skill_row = 3
            hist_row = 4
            button_row = 5
        else:
            skill_row = 2
            hist_row = 3
            button_row = 4
        
        # Set row weight for histogram row to allow expansion
        main_frame.rowconfigure(hist_row, weight=1)
        
        # Skill distribution display - show added points only
        skill_frame = ttk.LabelFrame(main_frame, text="Optimal Skill Distribution (Points Added)", padding="5")
        skill_frame.grid(row=skill_row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Track if we added top3 frame to adjust hist_row
        top3_added = False
        
        skill_text_parts = []
        for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
            points = added_distribution.get(skill, 0)
            skill_short = skill[:3].upper()
            skill_text_parts.append(f"{skill_short}: {points}")
        
        skill_label = ttk.Label(skill_frame, text=" | ".join(skill_text_parts), font=("Arial", 10, "bold"))
        skill_label.pack()
        
        # Verify total matches Arch Level
        total_added = sum(added_distribution.values())
        info_text = f"Total points added: {total_added} (Arch Level: {num_points})"
        if total_added != num_points:
            info_text += f" ⚠️ MISMATCH!"
        info_label = ttk.Label(skill_frame, text=info_text, font=("Arial", 8), 
                              foreground="#C73E1D" if total_added != num_points else "#666666")
        info_label.pack(pady=(3, 0))
        
        # Top 3 candidates comparison (if there were ties)
        if top_3_candidates is None:
            top_3_candidates = []
        
        if top_3_candidates and len(top_3_candidates) > 1:
            # Check if there's actually a tie (same max stage)
            best_max_stage = top_3_candidates[0][1] if top_3_candidates else 0
            tied_candidates = [c for c in top_3_candidates if c[1] == best_max_stage]
            
            # Further filter: if fragments/h are within 15% relative difference, also consider them tied
            if len(tied_candidates) > 1:
                best_frags_h = tied_candidates[0][2] if tied_candidates else 0.0
                # Check if any candidates have fragments/h within 15% relative difference of the best
                if best_frags_h > 0:
                    closely_tied = [c for c in tied_candidates if abs(c[2] - best_frags_h) / best_frags_h <= 0.15]
                else:
                    # If best is 0, only consider exact 0 as tied
                    closely_tied = [c for c in tied_candidates if c[2] == 0.0]
                if len(closely_tied) > 1:
                    tied_candidates = closely_tied
            
            if len(tied_candidates) > 1:
                # Determine tie-breaker text
                best_frags_h = tied_candidates[0][2] if tied_candidates else 0.0
                if best_frags_h > 0:
                    frags_within_tolerance = any(abs(c[2] - best_frags_h) / best_frags_h <= 0.15 for c in tied_candidates[1:])
                else:
                    frags_within_tolerance = any(c[2] == 0.0 for c in tied_candidates[1:])
                if frags_within_tolerance:
                    tie_text = "Top Candidates (Tie-Breaker: XP/h, Fragments/h within 15%)"
                else:
                    tie_text = "Top Candidates (Tie-Breaker: Fragments/h)"
                
                top3_frame = ttk.LabelFrame(main_frame, text=tie_text, padding="5")
                top3_frame.grid(row=skill_row + 1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
                
                # Create a small bar chart or list
                if MATPLOTLIB_AVAILABLE:
                    fig_top3 = Figure(figsize=(5, 2.5), dpi=100)
                    ax_top3 = fig_top3.add_subplot(111)
                    
                    # Prepare data
                    labels = []
                    frags_values = []
                    xp_values = []
                    colors = ['#9C27B0', '#BA68C8', '#CE93D8']  # Purple gradient
                    
                    for idx, (dist_dict, max_stage_int, frags_h, xp_h) in enumerate(tied_candidates[:3]):
                        # Create skill label
                        skill_parts = []
                        for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
                            points = dist_dict.get(skill, 0)
                            if points > 0:
                                skill_parts.append(f"{skill[:3].upper()}:{points}")
                        skill_label = " | ".join(skill_parts) if skill_parts else "All 0"
                        labels.append(f"#{idx+1}: {skill_label}")
                        frags_values.append(frags_h)
                        xp_values.append(xp_h)
                    
                    # Create grouped bar chart (fragments/h and xp/h side by side)
                    x_pos = np.arange(len(labels))
                    width = 0.35
                    
                    bars1 = ax_top3.barh(x_pos - width/2, frags_values, width, label='Fragments/h', 
                                        color=colors[:len(labels)], alpha=0.7, edgecolor='#4A148C', linewidth=1)
                    bars2 = ax_top3.barh(x_pos + width/2, xp_values, width, label='XP/h', 
                                        color=[c.replace('B0', '80') for c in colors[:len(labels)]], alpha=0.7, edgecolor='#4A148C', linewidth=1)
                    
                    # Add value labels on bars
                    for i, (bar1, bar2, frag_val, xp_val) in enumerate(zip(bars1, bars2, frags_values, xp_values)):
                        width1 = bar1.get_width()
                        width2 = bar2.get_width()
                        ax_top3.text(width1, bar1.get_y() + bar1.get_height()/2, 
                                   f' {frag_val:.2f}', ha='left', va='center', fontsize=7, fontweight='bold')
                        ax_top3.text(width2, bar2.get_y() + bar2.get_height()/2, 
                                   f' {xp_val:.1f}', ha='left', va='center', fontsize=7, fontweight='bold')
                    
                    ax_top3.set_yticks(x_pos)
                    ax_top3.set_yticklabels(labels, fontsize=8)
                    ax_top3.set_xlabel('Rate (/h)', fontsize=9, fontweight='bold')
                    ax_top3.set_title(f'Top {len(tied_candidates)} Candidates (Max Stage: {best_max_stage})', 
                                    fontsize=9, fontweight='bold')
                    ax_top3.legend(fontsize=8, loc='lower right')
                    ax_top3.grid(axis='x', alpha=0.3, linestyle='--')
                    
                    fig_top3.tight_layout(pad=1.5)
                    
                    canvas_top3 = FigureCanvasTkAgg(fig_top3, top3_frame)
                    canvas_top3.draw()
                    canvas_top3.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                    
                    top3_added = True
        
        # Adjust hist_row if top3 was added
        if top3_added:
            hist_row += 1
            button_row += 1
        
        # Histogram frame (single histogram)
        hist_frame = ttk.LabelFrame(main_frame, text="Maximum Stage Reached Distribution", padding="5")
        hist_frame.grid(row=hist_row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        hist_frame.columnconfigure(0, weight=1)
        hist_frame.rowconfigure(0, weight=1)
        
        if MATPLOTLIB_AVAILABLE and max_stage_samples:
            # Smaller figure size that fits nicely in the window (not too large)
            fig = Figure(figsize=(5, 2.5), dpi=100)
            ax = fig.add_subplot(111)
            
            # Determine number of bins based on stage range (use integer bins)
            min_stage = int(np.min(max_stage_samples))
            max_stage = int(np.max(max_stage_samples))
            num_bins = max_stage - min_stage + 1  # One bin per integer stage
            
            # Create histogram with integer bins, no spacing
            counts, bins, patches = ax.hist(max_stage_samples, bins=num_bins, 
                                           range=(min_stage - 0.5, max_stage + 0.5),
                                           color='#9C27B0', 
                                           edgecolor='#4A148C', linewidth=1.0, 
                                           alpha=0.7, align='mid')
            
            # Add bin content and percentage inside each bar (centered vertically)
            total_samples = len(max_stage_samples)  # Should be 1000
            for i, (count, patch) in enumerate(zip(counts, patches)):
                if count > 0:
                    bin_center = (bins[i] + bins[i+1]) / 2
                    percentage = (count / total_samples) * 100
                    # Add text inside bar (centered vertically)
                    bar_height = count
                    ax.text(bin_center, bar_height / 2, f'{int(count)}\n({percentage:.1f}%)',
                           ha='center', va='center', fontsize=7, fontweight='bold',
                           color='white' if bar_height > max(counts) * 0.3 else 'black')
            
            # Set x-axis to show only integers
            ax.set_xlim(min_stage - 0.5, max_stage + 0.5)
            ax.set_xticks(range(min_stage, max_stage + 1))
            ax.set_xticklabels([str(int(x)) for x in range(min_stage, max_stage + 1)])
            
            ax.set_xlabel('Maximum Stage Reached', fontsize=10, fontweight='bold')
            ax.set_ylabel('Frequency', fontsize=10, fontweight='bold')
            ax.set_title('Distribution of Maximum Stage Reached (1000 MC simulations)', 
                        fontsize=11, fontweight='bold')
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            
            # Layout - adjust padding for better fit
            fig.tight_layout(pad=2.0)
            
            # Create canvas
            canvas = FigureCanvasTkAgg(fig, hist_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        else:
            # No data
            ttk.Label(hist_frame, text="No simulation data available", 
                     foreground="gray").pack(pady=20)
        
        # Close button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=button_row, column=0, columnspan=2, pady=(10, 0))
        
        close_btn = ttk.Button(button_frame, text="Close", command=result_window.destroy)
        close_btn.pack()
    
    def _show_fragment_farmer_results(self, frag_per_hour_samples, skill_points_display, num_points,
                                     target_frag, optimal_stage, metrics_samples):
        """Show histogram window with fragment/hour distribution and optimal skill setup"""
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
        
        # Create window in normal GUI style (not Matrix)
        result_window = tk.Toplevel(self.window)
        result_window.title(f"MC Fragment Farmer Results ({target_frag.upper()})")
        result_window.transient(self.window)
        
        # Set window to fullscreen (maximized)
        result_window.state('zoomed')  # Maximize on Windows
        result_window.resizable(True, True)
        
        # Main container
        main_frame = ttk.Frame(result_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        
        # Title
        stage_label = get_stage_range_label(optimal_stage)
        title_label = ttk.Label(main_frame, 
                               text=f"MC Fragment Farmer Results ({target_frag.upper()}) - 1000 simulations\n"
                                    f"Optimal Stage: {stage_label} (Stage {optimal_stage})", 
                               font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(main_frame, text="Fragment Statistics", padding="10")
        stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        if frag_per_hour_samples:
            mean_val = np.mean(frag_per_hour_samples)
            median_val = np.median(frag_per_hour_samples)
            std_val = np.std(frag_per_hour_samples)
            min_val = np.min(frag_per_hour_samples)
            max_val = np.max(frag_per_hour_samples)
            
            stats_text = f"""Mean: {mean_val:.2f} frags/h
Median: {median_val:.2f} frags/h
Std Dev: {std_val:.2f} frags/h
Min: {min_val:.2f} frags/h
Max: {max_val:.2f} frags/h"""
            
            stats_label = ttk.Label(stats_frame, text=stats_text, font=("Courier", 9), 
                                   justify=tk.LEFT)
            stats_label.pack(anchor=tk.W)
        else:
            ttk.Label(stats_frame, text="No simulation data available", 
                     foreground="gray").pack()
        
        # Metrics frame (XP/h, Fragments/h, Floors/run)
        if metrics_samples:
            metrics_frame = ttk.LabelFrame(main_frame, text="Performance Metrics", padding="10")
            metrics_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            
            # Calculate averages
            avg_floors_per_run = np.mean([m['floors_cleared'] for m in metrics_samples])
            avg_xp_per_run = np.mean([m['xp_per_run'] for m in metrics_samples])
            avg_total_fragments = np.mean([m['total_fragments'] for m in metrics_samples])
            avg_run_duration = np.mean([m['run_duration_seconds'] for m in metrics_samples])
            
            # Calculate per hour
            runs_per_hour = 3600 / avg_run_duration if avg_run_duration > 0 else 0
            xp_per_hour = avg_xp_per_run * runs_per_hour
            fragments_per_hour = avg_total_fragments * runs_per_hour
            
            # Calculate fragments per hour by type
            frag_types = ['common', 'rare', 'epic', 'legendary', 'mythic']
            avg_frags_by_type = {}
            frags_per_hour_by_type = {}
            for frag_type in frag_types:
                avg_frags = np.mean([m.get('fragments', {}).get(frag_type, 0.0) for m in metrics_samples])
                avg_frags_by_type[frag_type] = avg_frags
                frags_per_hour_by_type[frag_type] = avg_frags * runs_per_hour
            
            metrics_text = f"""Floors/Run: {avg_floors_per_run:.2f}
XP/h: {xp_per_hour:.1f}
Fragments/h: {fragments_per_hour:.2f}"""
            
            metrics_label = ttk.Label(metrics_frame, text=metrics_text, font=("Courier", 9), 
                                     justify=tk.LEFT)
            metrics_label.pack(anchor=tk.W)
            
            # Fragments by type with icons
            frag_display_frame = tk.Frame(metrics_frame)
            frag_display_frame.pack(anchor=tk.W, pady=(5, 0))
            
            frag_icon_map = {
                'common': 'fragmentcommon.png',
                'rare': 'fragmentrare.png',
                'epic': 'fragmentepic.png',
                'legendary': 'fragmentlegendary.png',
                'mythic': 'fragmentmythic.png',
            }
            
            frag_labels = []
            for frag_type in frag_types:
                frag_per_hour = frags_per_hour_by_type.get(frag_type, 0.0)
                if frag_per_hour > 0.001:  # Only show if > 0.001
                    frag_item_frame = tk.Frame(frag_display_frame)
                    frag_item_frame.pack(side=tk.LEFT, padx=(0, 15))
                    
                    # Try to load icon
                    try:
                        icon_path = get_resource_path(f"sprites/archaeology/{frag_icon_map[frag_type]}")
                        if icon_path.exists():
                            icon_image = Image.open(icon_path)
                            icon_image = icon_image.resize((16, 16), Image.Resampling.LANCZOS)
                            icon_photo = ImageTk.PhotoImage(icon_image)
                            icon_label = tk.Label(frag_item_frame, image=icon_photo)
                            icon_label.image = icon_photo  # Keep reference
                            icon_label.pack(side=tk.LEFT, padx=(0, 3))
                    except:
                        pass
                    
                    # Fragment type and value
                    frag_label = tk.Label(
                        frag_item_frame,
                        text=f"{frag_type.capitalize()}: {frag_per_hour:.2f}/h",
                        font=("Arial", 9)
                    )
                    frag_label.pack(side=tk.LEFT)
                    frag_labels.append(frag_item_frame)
            
            # Adjust row numbers for subsequent elements
            skill_row = 3
            hist_row = 4
            button_row = 5
        else:
            skill_row = 2
            hist_row = 3
            button_row = 4
        
        # Set row weight for histogram row to allow expansion (but not too much)
        main_frame.rowconfigure(hist_row, weight=1)
        
        # Skill distribution display
        skill_frame = ttk.LabelFrame(main_frame, text="Optimal Skill Distribution", padding="5")
        skill_frame.grid(row=skill_row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        skill_text_parts = []
        for skill in ['strength', 'agility', 'intellect', 'perception', 'luck']:
            points = skill_points_display.get(skill, 0)
            skill_short = skill[:3].upper()
            skill_text_parts.append(f"{skill_short}: {points}")
        
        skill_label = ttk.Label(skill_frame, text=" | ".join(skill_text_parts), font=("Arial", 10, "bold"))
        skill_label.pack()
        
        # Histogram frame (single histogram)
        hist_frame = ttk.LabelFrame(main_frame, text="Fragment/Hour Distribution", padding="5")
        hist_frame.grid(row=hist_row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        hist_frame.columnconfigure(0, weight=1)
        hist_frame.rowconfigure(0, weight=1)
        
        if MATPLOTLIB_AVAILABLE and frag_per_hour_samples:
            # Smaller figure size that fits nicely in the window (not too large)
            fig = Figure(figsize=(5, 2.5), dpi=100)
            ax = fig.add_subplot(111)
            
            # Create histogram
            counts, bins, patches = ax.hist(frag_per_hour_samples, bins=30, color='#7B1FA2', 
                                           edgecolor='#4A148C', linewidth=1.5, alpha=0.7)
            
            # Add mean line
            mean_val = np.mean(frag_per_hour_samples)
            ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f}')
            
            # Add median line
            median_val = np.median(frag_per_hour_samples)
            ax.axvline(median_val, color='orange', linestyle='--', linewidth=2, label=f'Median: {median_val:.2f}')
            
            ax.set_xlabel(f'{target_frag.upper()} Fragments/Hour', fontsize=10, fontweight='bold')
            ax.set_ylabel('Frequency', fontsize=10, fontweight='bold')
            ax.set_title(f'Distribution of {target_frag.upper()} Fragments/Hour (1000 MC simulations)', 
                        fontsize=11, fontweight='bold')
            ax.legend(loc='upper right', fontsize=9)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            
            # Layout - adjust padding for better fit
            fig.tight_layout(pad=2.0)
            
            # Create canvas
            canvas = FigureCanvasTkAgg(fig, hist_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        else:
            # No data
            ttk.Label(hist_frame, text="No simulation data available", 
                     foreground="gray").pack(pady=20)
        
        # Close button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=button_row, column=0, columnspan=2, pady=(10, 0))
        
        close_btn = ttk.Button(button_frame, text="Close", command=result_window.destroy)
        close_btn.pack()
    