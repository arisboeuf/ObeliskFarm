"""
Real Life Simulation GUI - Animated event simulation with visual feedback.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys
import os
import math
import random
import threading
import time

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .stats import PlayerStats, EnemyStats
from .simulation import simulate_event_run_realtime
from .constants import PRESTIGE_BONUS_BASE

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import get_resource_path


class RealLifeSimulationWindow:
    """Real-time animated event simulation window"""
    
    def __init__(self, parent, player: PlayerStats, enemy: EnemyStats):
        self.player = player
        self.enemy = enemy
        self.parent = parent
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Real Life Simulation")
        self.window.geometry("900x700")
        self.window.minsize(800, 600)
        
        # Center window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Simulation state
        self.simulation_running = False
        self.simulation_thread = None
        self.current_wave = 0
        self.current_subwave = 0
        self.current_player_hp = player.health
        self.current_enemy_hp = 0
        self.simulation_time = 0.0  # Game time in seconds
        
        # Damage numbers (floating text)
        self.damage_numbers = []  # List of {x, y, text, color, age, is_crit}
        self.damage_numbers_lock = threading.Lock()  # Thread safety for damage numbers
        
        # Attack progress tracking (based on real game time)
        self.player_last_attack_time = 0.0  # Game time when player last attacked
        self.enemy_last_attack_time = 0.0  # Game time when enemy last attacked
        self.player_attack_cooldown = 0.0  # Time between player attacks (in game seconds)
        self.enemy_attack_cooldown = 0.0  # Time between enemy attacks (in game seconds)
        self.progress_lock = threading.Lock()  # Thread safety for progress
        
        # Movement state
        self.is_walking = False
        self.walk_start_game_time = 0.0  # Game time when walking started
        self.walk_duration = 0.0  # Total walk time in game seconds
        
        # Real-time tracking
        self.simulation_start_real_time = time.time()  # Real time when simulation started
        self.game_speed = player.game_speed  # Store game speed multiplier
        
        # Build UI
        self.build_ui()
        
        # Start simulation
        self.start_simulation()
    
    def build_ui(self):
        """Build the user interface"""
        # Main container
        main_frame = tk.Frame(self.window, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top section - Wave indicator (centered like in the image)
        top_frame = tk.Frame(main_frame, bg="#1a1a2e", height=60)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        top_frame.pack_propagate(False)
        
        self.wave_label = tk.Label(
            top_frame,
            text="Wave: 0-0",
            font=("Arial", 18, "bold"),
            bg="#1a1a2e",
            fg="white"
        )
        self.wave_label.pack(expand=True, pady=10)
        
        # Middle section - Game area with Canvas
        game_frame = tk.Frame(main_frame, bg="#0f3460", relief=tk.RAISED, borderwidth=2)
        game_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Canvas for game visualization
        self.canvas = tk.Canvas(
            game_frame,
            bg="#0f3460",
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind canvas resize
        self.canvas.bind('<Configure>', self.on_canvas_resize)
        
        # Bottom section - Stats panels
        stats_frame = tk.Frame(main_frame, bg="#1a1a2e")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Player stats (left)
        player_stats_frame = tk.Frame(stats_frame, bg="#2C2C2C", relief=tk.RAISED, borderwidth=1)
        player_stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(
            player_stats_frame,
            text="Player Stats",
            font=("Arial", 10, "bold"),
            bg="#2C2C2C",
            fg="white"
        ).pack(pady=5)
        
        self.player_hp_label = tk.Label(
            player_stats_frame,
            text=f"Hp: {self.player.health}",
            font=("Arial", 9),
            bg="#2C2C2C",
            fg="#ff4444"
        )
        self.player_hp_label.pack()
        
        self.player_atk_label = tk.Label(
            player_stats_frame,
            text=f"Attack Damage: {int(self.player.atk)}",
            font=("Arial", 8),
            bg="#2C2C2C",
            fg="white"
        )
        self.player_atk_label.pack()
        
        self.player_atk_speed_label = tk.Label(
            player_stats_frame,
            text=f"Attack Speed: {self.player.atk_speed:.2f}",
            font=("Arial", 8),
            bg="#2C2C2C",
            fg="white"
        )
        self.player_atk_speed_label.pack()
        
        self.player_move_speed_label = tk.Label(
            player_stats_frame,
            text=f"Move Speed: {self.player.walk_speed:.2f}",
            font=("Arial", 8),
            bg="#2C2C2C",
            fg="white"
        )
        self.player_move_speed_label.pack()
        
        self.player_crit_label = tk.Label(
            player_stats_frame,
            text=f"Crit Chance: {self.player.crit}%",
            font=("Arial", 8),
            bg="#2C2C2C",
            fg="white"
        )
        self.player_crit_label.pack()
        
        self.player_event_speed_label = tk.Label(
            player_stats_frame,
            text=f"Event Speed: {self.player.game_speed:.2f}x",
            font=("Arial", 8),
            bg="#2C2C2C",
            fg="white"
        )
        self.player_event_speed_label.pack()
        
        # Enemy stats (right)
        enemy_stats_frame = tk.Frame(stats_frame, bg="#2C2C2C", relief=tk.RAISED, borderwidth=1)
        enemy_stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(
            enemy_stats_frame,
            text="Enemy Stats",
            font=("Arial", 10, "bold"),
            bg="#2C2C2C",
            fg="white"
        ).pack(pady=5)
        
        self.enemy_hp_label = tk.Label(
            enemy_stats_frame,
            text="Hp: 0",
            font=("Arial", 9),
            bg="#2C2C2C",
            fg="#ff4444"
        )
        self.enemy_hp_label.pack()
        
        self.enemy_atk_label = tk.Label(
            enemy_stats_frame,
            text="Attack Damage: 0",
            font=("Arial", 8),
            bg="#2C2C2C",
            fg="white"
        )
        self.enemy_atk_label.pack()
        
        self.enemy_atk_speed_label = tk.Label(
            enemy_stats_frame,
            text="Attack Speed: 0.00",
            font=("Arial", 8),
            bg="#2C2C2C",
            fg="white"
        )
        self.enemy_atk_speed_label.pack()
        
        self.enemy_crit_label = tk.Label(
            enemy_stats_frame,
            text="Crit Chance: 0%",
            font=("Arial", 8),
            bg="#2C2C2C",
            fg="white"
        )
        self.enemy_crit_label.pack()
        
        self.enemy_crit_dmg_label = tk.Label(
            enemy_stats_frame,
            text="Crit Damage: 0.00x",
            font=("Arial", 8),
            bg="#2C2C2C",
            fg="white"
        )
        self.enemy_crit_dmg_label.pack()
        
        # Time display (in milliseconds)
        self.time_label = tk.Label(
            main_frame,
            text="Time: 0ms",
            font=("Arial", 10),
            bg="#1a1a2e",
            fg="white"
        )
        self.time_label.pack(pady=5)
        
        # Start animation loop
        self.animate()
        
        # Start game time timer (updates every 10ms for smooth millisecond display)
        self.update_game_time()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_canvas_resize(self, event):
        """Handle canvas resize"""
        self.draw_game_scene()
    
    def draw_game_scene(self):
        """Draw the game scene on canvas"""
        try:
            if not self.window.winfo_exists():
                return
        except (tk.TclError, RuntimeError):
            return
        
        try:
            self.canvas.delete("all")
            
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            
            if width <= 1 or height <= 1:
                return
        except (tk.TclError, RuntimeError):
            return
        
        # Draw background (snowy landscape effect)
        self.canvas.create_rectangle(0, 0, width, height, fill="#0f3460", outline="")
        
        # Draw ground
        ground_y = height - 100
        self.canvas.create_rectangle(0, ground_y, width, height, fill="#2a4a6a", outline="")
        
        # Player position (left side)
        player_x = width * 0.25
        player_y = ground_y - 50
        
        # Enemy position (right side)
        enemy_x = width * 0.75
        enemy_y = ground_y - 50
        
        # Draw player (simple rectangle representation - pixel art style)
        player_size = 50
        # Player body
        self.canvas.create_rectangle(
            player_x - player_size//2, player_y - player_size,
            player_x + player_size//2, player_y,
            fill="#4a90e2", outline="#2a5a9a", width=2
        )
        # Player head (smaller rectangle on top)
        head_size = 20
        self.canvas.create_rectangle(
            player_x - head_size//2, player_y - player_size - head_size//2,
            player_x + head_size//2, player_y - player_size + head_size//2,
            fill="#6aa0f2", outline="#2a5a9a", width=1
        )
        # Player label (red text like in the image)
        self.canvas.create_text(
            player_x, player_y + 15,
            text=f"Hp: {int(self.current_player_hp)}",
            fill="#ff4444",
            font=("Arial", 11, "bold")
        )
        
        # Player attack progress bar
        bar_width = 60
        bar_height = 6
        bar_x = player_x - bar_width // 2
        bar_y = player_y - player_size - 15
        
        # Attack label
        self.canvas.create_text(
            bar_x - 35, bar_y + bar_height // 2,
            text="Attack",
            fill="#ffffff",
            font=("Arial", 8),
            anchor="e"
        )
        
        # Background bar
        self.canvas.create_rectangle(
            bar_x, bar_y,
            bar_x + bar_width, bar_y + bar_height,
            fill="#333333", outline="#666666", width=1
        )
        
        # Calculate progress based on real game time
        with self.progress_lock:
            if self.current_enemy_hp > 0 and self.player_attack_cooldown > 0:
                time_since_last_attack = self.simulation_time - self.player_last_attack_time
                progress = min(1.0, time_since_last_attack / self.player_attack_cooldown)
            else:
                progress = 0.0
        
        progress_width = int(bar_width * progress)
        if progress_width > 0:
            self.canvas.create_rectangle(
                bar_x, bar_y,
                bar_x + progress_width, bar_y + bar_height,
                fill="#4CAF50", outline="", width=0
            )
        
        # Movement progress bar (above attack bar)
        if self.is_walking and self.walk_duration > 0:
            move_bar_y = bar_y - 10
            # Movement label
            self.canvas.create_text(
                bar_x - 35, move_bar_y + bar_height // 2,
                text="Movement",
                fill="#ffffff",
                font=("Arial", 8),
                anchor="e"
            )
            # Background
            self.canvas.create_rectangle(
                bar_x, move_bar_y,
                bar_x + bar_width, move_bar_y + bar_height,
                fill="#333333", outline="#666666", width=1
            )
            # Calculate progress based on real game time
            time_since_walk_start = self.simulation_time - self.walk_start_game_time
            walk_progress = min(1.0, time_since_walk_start / self.walk_duration)
            
            move_progress_width = int(bar_width * walk_progress)
            if move_progress_width > 0:
                self.canvas.create_rectangle(
                    bar_x, move_bar_y,
                    bar_x + move_progress_width, move_bar_y + bar_height,
                    fill="#2196F3", outline="", width=0
                )
        
        # Draw enemy (simple rectangle representation - pixel art style)
        if self.current_enemy_hp > 0:
            enemy_size = 50
            # Enemy body (brown like in the image)
            self.canvas.create_oval(
                enemy_x - enemy_size//2, enemy_y - enemy_size,
                enemy_x + enemy_size//2, enemy_y,
                fill="#8b4513", outline="#5a2a0a", width=2
            )
            # Enemy decoration (top)
            self.canvas.create_oval(
                enemy_x - 15, enemy_y - enemy_size - 5,
                enemy_x + 15, enemy_y - enemy_size + 10,
                fill="#2d5016", outline="#1a3009", width=1
            )
            # Enemy label (red text like in the image)
            self.canvas.create_text(
                enemy_x, enemy_y + 15,
                text=f"Hp: {int(self.current_enemy_hp)}",
                fill="#ff4444",
                font=("Arial", 11, "bold")
            )
            
            # Enemy attack progress bar
            bar_width = 60
            bar_height = 6
            bar_x = enemy_x - bar_width // 2
            bar_y = enemy_y - enemy_size - 15
            
            # Attack label
            self.canvas.create_text(
                bar_x + bar_width + 35, bar_y + bar_height // 2,
                text="Attack",
                fill="#ffffff",
                font=("Arial", 8),
                anchor="w"
            )
            
            # Background bar
            self.canvas.create_rectangle(
                bar_x, bar_y,
                bar_x + bar_width, bar_y + bar_height,
                fill="#333333", outline="#666666", width=1
            )
            
            # Calculate progress based on real game time
            with self.progress_lock:
                if self.enemy_attack_cooldown > 0:
                    time_since_last_attack = self.simulation_time - self.enemy_last_attack_time
                    progress = min(1.0, time_since_last_attack / self.enemy_attack_cooldown)
                else:
                    progress = 0.0
            
            progress_width = int(bar_width * progress)
            if progress_width > 0:
                self.canvas.create_rectangle(
                    bar_x, bar_y,
                    bar_x + progress_width, bar_y + bar_height,
                    fill="#F44336", outline="", width=0
                )
        
        # Draw floating damage numbers (thread-safe copy)
        with self.damage_numbers_lock:
            damage_numbers_copy = self.damage_numbers.copy()
        
        damage_numbers_to_remove = []
        
        for i, dmg_num in enumerate(damage_numbers_copy):
            # Update position (float upward)
            dmg_num['y'] += 2
            dmg_num['age'] += 0.03
            
            # Remove if too old
            if dmg_num['age'] > 1.5:
                damage_numbers_to_remove.append(i)
                continue
            
            # Calculate opacity (fade out)
            opacity = max(0, 1.0 - (dmg_num['age'] / 1.5))
            
            # Draw damage number
            font_size = 16 if dmg_num['is_crit'] else 12
            font_weight = "bold" if dmg_num['is_crit'] else "normal"
            
            # Determine position (player or enemy side)
            if dmg_num['target'] == 'player':
                x_pos = player_x + dmg_num['x']
                y_pos = player_y - 50 - dmg_num['y']
            else:  # enemy
                x_pos = enemy_x + dmg_num['x']
                y_pos = enemy_y - 50 - dmg_num['y']
            
            # Color with fade
            color = dmg_num['color']
            if opacity < 0.3:
                # Make very faded numbers lighter
                if color == "#ffffff":
                    color = "#aaaaaa"
                elif color == "#ffaa00":
                    color = "#cc8800"
                elif color == "#888888":
                    color = "#666666"
            
            self.canvas.create_text(
                x_pos, y_pos,
                text=dmg_num['text'],
                fill=color,
                font=("Arial", font_size, font_weight)
            )
        
        # Remove old damage numbers (thread-safe)
        if damage_numbers_to_remove:
            with self.damage_numbers_lock:
                # Remove in reverse order to maintain indices
                for i in reversed(sorted(damage_numbers_to_remove)):
                    if i < len(self.damage_numbers):
                        self.damage_numbers.pop(i)
    
    def add_damage_number(self, damage: float, is_crit: bool, target: str, is_blocked: bool = False):
        """Add a floating damage number (thread-safe)"""
        if is_blocked:
            text = "BLOCKED"
            color = "#888888"
            is_crit = False
        else:
            text = f"-{int(damage)}"
            if is_crit:
                color = "#ffaa00"  # Orange for crits
            else:
                color = "#ffffff"  # White for normal
        
        # Add to damage numbers list (thread-safe)
        with self.damage_numbers_lock:
            self.damage_numbers.append({
                'text': text,
                'color': color,
                'x': (random.random() - 0.5) * 40,  # Random offset (-20 to +20)
                'y': 0,
                'age': 0.0,
                'is_crit': is_crit,
                'target': target
            })
    
    def start_simulation(self):
        """Start the simulation in a separate thread"""
        if self.simulation_running:
            return
        
        self.simulation_running = True
        self.current_player_hp = self.player.health
        self.simulation_start_real_time = time.time()
        
        def run_simulation():
            """Run simulation and process events with real-time timing"""
            try:
                last_event_time = 0.0
                for event in simulate_event_run_realtime(self.player, self.enemy):
                    if not self.simulation_running:
                        break
                    
                    # Process event
                    self.process_simulation_event(event)
                    
                    # Wait for the real time that passed in the simulation
                    # Use time_delta from event if available, otherwise calculate from time
                    time_delta = event.get('time_delta', 0.0)
                    
                    if time_delta > 0:
                        # Sleep in smaller chunks to keep UI responsive
                        # Split sleep into 10ms chunks to allow UI updates
                        sleep_chunks = int(time_delta / 0.01) + 1
                        chunk_time = time_delta / sleep_chunks
                        for _ in range(sleep_chunks):
                            if not self.simulation_running:
                                break
                            time.sleep(chunk_time)
                    else:
                        # Small delay for instant events (like wave_start, enemy_killed)
                        time.sleep(0.01)
            except Exception as e:
                print(f"Simulation error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.simulation_running = False
        
        self.simulation_thread = threading.Thread(target=run_simulation, daemon=True)
        self.simulation_thread.start()
    
    def process_simulation_event(self, event):
        """Process a simulation event and update UI"""
        # Check if window still exists
        try:
            if not self.window.winfo_exists():
                return
        except (tk.TclError, RuntimeError):
            return
        
        event_type = event['type']
        
        if event_type == 'wave_start':
            self.current_wave = event['wave']
            self.current_subwave = event['subwave']
            self.current_enemy_hp = event['enemy_hp']
            self.current_player_hp = event['player_hp']
            self.simulation_time = event['time']
            
            # Initialize attack timing for new wave
            # Set initial attack times to current game time so progress starts at 0
            with self.progress_lock:
                self.player_last_attack_time = self.simulation_time
                self.enemy_last_attack_time = self.simulation_time
                # Calculate cooldowns (in game seconds, already adjusted by game_speed in simulation)
                self.player_attack_cooldown = self.player.default_atk_time / self.player.atk_speed
                enemy_atk_speed = self.enemy.atk_speed + self.current_wave * 0.02
                self.enemy_attack_cooldown = self.enemy.default_atk_time / enemy_atk_speed
            
            # Reset walking state
            self.is_walking = False
            self.walk_duration = 0.0
            
            # Capture values for lambda (avoid closure issues)
            wave_val = self.current_wave
            subwave_val = self.current_subwave
            enemy_hp_val = int(self.current_enemy_hp)
            enemy_atk = max(1, self.enemy.atk + self.current_wave * self.enemy.atk_scaling)
            enemy_atk_speed = self.enemy.atk_speed + self.current_wave * 0.02
            enemy_crit_chance = self.enemy.crit + self.current_wave
            enemy_crit_dmg = self.enemy.crit_dmg + self.enemy.crit_dmg_scaling * self.current_wave
            time_val = self.simulation_time
            
            # Update wave label
            self.window.after(0, lambda w=wave_val, s=subwave_val: self._safe_update_wave(w, s))
            
            # Update enemy stats
            self.window.after(0, lambda hp=enemy_hp_val: self._safe_update_enemy_hp(hp))
            self.window.after(0, lambda atk=int(enemy_atk): self._safe_update_enemy_atk(atk))
            self.window.after(0, lambda spd=enemy_atk_speed: self._safe_update_enemy_atk_speed(spd))
            self.window.after(0, lambda crit=enemy_crit_chance: self._safe_update_enemy_crit(crit))
            self.window.after(0, lambda crit_dmg=enemy_crit_dmg: self._safe_update_enemy_crit_dmg(crit_dmg))
            self.window.after(0, lambda t=time_val: self._safe_update_time(t))
        
        elif event_type == 'player_attack':
            self.current_enemy_hp = event['enemy_hp']
            self.current_player_hp = event['player_hp']
            self.simulation_time = event['time']
            
            # Update attack timing (based on real game time)
            with self.progress_lock:
                self.player_last_attack_time = self.simulation_time
                # Calculate cooldown: default_atk_time / atk_speed (in game seconds)
                self.player_attack_cooldown = self.player.default_atk_time / self.player.atk_speed
            
            # Capture values for lambda
            dmg = event['damage']
            is_crit = event['is_crit']
            enemy_hp_val = int(self.current_enemy_hp)
            player_hp_val = int(self.current_player_hp)
            time_val = self.simulation_time
            
            # Add damage number
            self.window.after(0, lambda d=dmg, c=is_crit: self.add_damage_number(d, c, 'enemy'))
            
            # Update labels
            self.window.after(0, lambda hp=enemy_hp_val: self._safe_update_enemy_hp(hp))
            self.window.after(0, lambda hp=player_hp_val: self._safe_update_player_hp(hp))
            self.window.after(0, lambda t=time_val: self._safe_update_time(t))
        
        elif event_type == 'enemy_attack':
            self.current_player_hp = event['player_hp']
            self.simulation_time = event['time']
            
            # Update attack timing (based on real game time)
            with self.progress_lock:
                self.enemy_last_attack_time = self.simulation_time
                # Calculate cooldown: default_atk_time / (enemy_atk_speed + wave * 0.02) (in game seconds)
                enemy_atk_speed = self.enemy.atk_speed + self.current_wave * 0.02
                self.enemy_attack_cooldown = self.enemy.default_atk_time / enemy_atk_speed
            
            # Capture values for lambda
            dmg = event['damage']
            is_crit = event['is_crit']
            is_blocked = event['is_blocked']
            player_hp_val = int(self.current_player_hp)
            time_val = self.simulation_time
            
            # Add damage number
            self.window.after(0, lambda d=dmg, c=is_crit, b=is_blocked: self.add_damage_number(d, c, 'player', b))
            
            # Update label
            self.window.after(0, lambda hp=player_hp_val: self._safe_update_player_hp(hp))
            self.window.after(0, lambda t=time_val: self._safe_update_time(t))
        
        elif event_type == 'enemy_killed':
            self.current_enemy_hp = 0
            self.simulation_time = event['time']
            time_val = self.simulation_time
            
            # Update label
            self.window.after(0, lambda: self._safe_update_enemy_hp(0))
            self.window.after(0, lambda t=time_val: self._safe_update_time(t))
            
            # Start movement immediately after enemy is killed (if not last enemy)
            if event.get('start_walking', False):
                self.is_walking = True
                self.walk_start_game_time = self.simulation_time  # Use game time, not real time
                self.walk_duration = event.get('walk_duration', 0.0)
        
        elif event_type == 'walking':
            self.simulation_time = event['time']
            time_val = self.simulation_time
            
            # Start walking animation (if not already started from enemy_killed)
            if not self.is_walking:
                self.is_walking = True
                self.walk_start_game_time = self.simulation_time  # Use game time
                self.walk_duration = event.get('walk_duration', 0.0)
            
            self.window.after(0, lambda t=time_val: self._safe_update_time(t))
        
        elif event_type == 'run_end':
            self.simulation_running = False
            self.simulation_time = event['time']
            wave_val = event['wave']
            subwave_val = event['subwave']
            time_val = self.simulation_time
            
            # Update final labels
            self.window.after(0, lambda w=wave_val, s=subwave_val: self._safe_update_wave_end(w, s))
            self.window.after(0, lambda t=time_val: self._safe_update_time(t))
    
    def _safe_update_wave(self, wave, subwave):
        """Safely update wave label"""
        try:
            if self.window.winfo_exists():
                self.wave_label.config(text=f"Wave: {wave}-{subwave}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_wave_end(self, wave, subwave):
        """Safely update wave label for run end"""
        try:
            if self.window.winfo_exists():
                self.wave_label.config(text=f"Run Ended - Wave: {wave}-{subwave}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_player_hp(self, hp):
        """Safely update player HP label"""
        try:
            if self.window.winfo_exists():
                self.player_hp_label.config(text=f"Hp: {hp}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_hp(self, hp):
        """Safely update enemy HP label"""
        try:
            if self.window.winfo_exists():
                self.enemy_hp_label.config(text=f"Hp: {hp}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_atk(self, atk):
        """Safely update enemy attack label"""
        try:
            if self.window.winfo_exists():
                self.enemy_atk_label.config(text=f"Attack Damage: {atk}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_atk_speed(self, speed):
        """Safely update enemy attack speed label"""
        try:
            if self.window.winfo_exists():
                self.enemy_atk_speed_label.config(text=f"Attack Speed: {speed:.2f}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_crit(self, crit):
        """Safely update enemy crit chance label"""
        try:
            if self.window.winfo_exists():
                self.enemy_crit_label.config(text=f"Crit Chance: {int(crit)}%")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_crit_dmg(self, crit_dmg):
        """Safely update enemy crit damage label"""
        try:
            if self.window.winfo_exists():
                self.enemy_crit_dmg_label.config(text=f"Crit Damage: {crit_dmg:.2f}x")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_time(self, time_val):
        """Safely update time label (called from events)"""
        # This is called from events, but we use update_game_time for display
        pass
    
    def _safe_update_time_ms(self, time_ms):
        """Safely update time label in milliseconds"""
        try:
            if self.window.winfo_exists():
                self.time_label.config(text=f"Time: {time_ms}ms")
        except (tk.TclError, RuntimeError):
            pass
    
    def animate(self):
        """Animation loop - runs at 60 FPS for smooth animation"""
        try:
            if not self.window.winfo_exists():
                return
        except (tk.TclError, RuntimeError):
            return
        
        # Always draw the scene (even if simulation hasn't started yet)
        # This ensures the initial state is visible
        self.draw_game_scene()
        
        # Schedule next frame (16ms = ~60 FPS for smooth animation)
        try:
            self.window.after(16, self.animate)
        except (tk.TclError, RuntimeError):
            pass
    
    def update_game_time(self):
        """Update game time display in milliseconds"""
        try:
            if not self.window.winfo_exists():
                return
        except (tk.TclError, RuntimeError):
            return
        
        # Update time label with milliseconds
        time_ms = int(self.simulation_time * 1000)
        self.window.after(0, lambda ms=time_ms: self._safe_update_time_ms(ms))
        
        # Check if walking should end (based on game time)
        if self.is_walking and self.walk_duration > 0:
            time_since_walk_start = self.simulation_time - self.walk_start_game_time
            if time_since_walk_start >= self.walk_duration:
                self.is_walking = False
                self.walk_duration = 0.0
        
        # Schedule next update (10ms for smooth millisecond display)
        try:
            self.window.after(10, self.update_game_time)
        except (tk.TclError, RuntimeError):
            pass
    
    def on_close(self):
        """Handle window close"""
        self.simulation_running = False
        if self.simulation_thread and self.simulation_thread.is_alive():
            # Wait a bit for thread to finish
            self.simulation_thread.join(timeout=1.0)
        self.window.destroy()
