"""
Real Life Simulation GUI - Real-time event simulation with live statistics.
No animations, just real-time number and table updates.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys
import threading
import time
from datetime import datetime
from collections import deque

from .stats import PlayerStats, EnemyStats
from .simulation import simulate_event_run_realtime
from .constants import PRESTIGE_BONUS_BASE

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import get_resource_path


class RealLifeSimulationWindow:
    """Real-time event simulation window with live statistics (no animations)"""
    
    def __init__(self, parent, player: PlayerStats, enemy: EnemyStats):
        self.player = player
        self.enemy = enemy
        self.parent = parent
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Real Life Simulation")
        self.window.geometry("1000x800")
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
        self.simulation_paused = False
        self.simulation_thread = None
        self.current_wave = 0
        self.current_subwave = 0
        self.current_player_hp = player.health
        self.current_enemy_hp = 0
        self.simulation_time = 0.0  # Game time in seconds
        self.real_time_elapsed = 0.0  # Real time elapsed (accumulated from time_delta, like Godot)
        self.debug_mode = True  # Debug mode always ON for real-time sim
        
        # Statistics tracking
        self.total_player_damage = 0
        self.total_enemy_damage = 0
        self.player_crits = 0
        self.enemy_crits = 0
        self.blocks = 0
        self.total_attacks = 0
        self.enemy_kills = 0
        
        # Recent events log (last 50 events)
        self.event_log = deque(maxlen=50)
        
        # Build UI
        self.build_ui()
        
        # Start simulation
        self.start_simulation()
    
    def build_ui(self):
        """Build the user interface with tables and statistics"""
        # Main container
        main_frame = tk.Frame(self.window, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Event Simulation - Live Statistics",
            font=("Arial", 16, "bold"),
            bg="#f0f0f0"
        )
        title_label.pack(pady=(0, 10))
        
        # Top section - Current Wave and Time
        top_frame = tk.Frame(main_frame, bg="#ffffff", relief=tk.RAISED, borderwidth=2)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_frame = tk.Frame(top_frame, bg="#ffffff")
        info_frame.pack(padx=15, pady=10)
        
        self.wave_label = tk.Label(
            info_frame,
            text="Wave: 0-0",
            font=("Arial", 14, "bold"),
            bg="#ffffff",
            fg="#2c3e50"
        )
        self.wave_label.pack(side=tk.LEFT, padx=20)
        
        self.time_label = tk.Label(
            info_frame,
            text="Time: 0.00s",
            font=("Arial", 14, "bold"),
            bg="#ffffff",
            fg="#2c3e50"
        )
        self.time_label.pack(side=tk.LEFT, padx=20)
        
        # Control buttons frame
        control_frame = tk.Frame(info_frame, bg="#ffffff")
        control_frame.pack(side=tk.LEFT, padx=20)
        
        # Play/Pause button
        self.play_pause_button = tk.Button(
            control_frame,
            text="⏸ Pause",
            font=("Arial", 10, "bold"),
            bg="#27ae60",
            fg="white",
            activebackground="#229954",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            command=self.toggle_pause,
            state=tk.DISABLED  # Disabled until simulation starts
        )
        self.play_pause_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Reset button
        self.reset_button = tk.Button(
            control_frame,
            text="🔄 Reset",
            font=("Arial", 10, "bold"),
            bg="#e74c3c",
            fg="white",
            activebackground="#c0392b",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            command=self.reset_simulation,
            state=tk.DISABLED  # Disabled until simulation starts
        )
        self.reset_button.pack(side=tk.LEFT)
        
        # Main content area - two columns
        content_frame = tk.Frame(main_frame, bg="#f0f0f0")
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        
        # Left column - Current Stats
        left_frame = tk.Frame(content_frame, bg="#f0f0f0")
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Player Stats Panel
        player_panel = tk.LabelFrame(
            left_frame,
            text="Player Stats",
            font=("Arial", 11, "bold"),
            bg="#ffffff",
            fg="#2c3e50",
            relief=tk.RAISED,
            borderwidth=2
        )
        player_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        player_content = tk.Frame(player_panel, bg="#ffffff")
        player_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.player_hp_label = self._create_stat_row(player_content, "HP:", f"{int(self.player.health)}", "#e74c3c")
        self.player_atk_label = self._create_stat_row(player_content, "Attack:", f"{int(self.player.atk)}", "#34495e")
        self.player_atk_speed_label = self._create_stat_row(player_content, "Attack Speed:", f"{self.player.atk_speed:.2f}", "#34495e")
        self.player_crit_label = self._create_stat_row(player_content, "Crit Chance:", f"{self.player.crit}%", "#34495e")
        self.player_crit_dmg_label = self._create_stat_row(player_content, "Crit Damage:", f"{self.player.crit_dmg:.2f}x", "#34495e")
        self.player_block_label = self._create_stat_row(player_content, "Block Chance:", f"{self.player.block_chance*100:.1f}%", "#34495e")
        self.player_move_speed_label = self._create_stat_row(player_content, "Move Speed:", f"{self.player.walk_speed:.2f}", "#34495e")
        self.player_event_speed_label = self._create_stat_row(player_content, "Event Speed:", f"{self.player.game_speed:.2f}x", "#34495e")
        
        # Enemy Stats Panel
        enemy_panel = tk.LabelFrame(
            left_frame,
            text="Current Enemy Stats",
            font=("Arial", 11, "bold"),
            bg="#ffffff",
            fg="#2c3e50",
            relief=tk.RAISED,
            borderwidth=2
        )
        enemy_panel.pack(fill=tk.BOTH, expand=True)
        
        enemy_content = tk.Frame(enemy_panel, bg="#ffffff")
        enemy_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.enemy_hp_label = self._create_stat_row(enemy_content, "HP:", "0", "#e74c3c")
        self.enemy_atk_label = self._create_stat_row(enemy_content, "Attack:", "0", "#34495e")
        self.enemy_atk_speed_label = self._create_stat_row(enemy_content, "Attack Speed:", "0.00", "#34495e")
        self.enemy_crit_label = self._create_stat_row(enemy_content, "Crit Chance:", "0%", "#34495e")
        self.enemy_crit_dmg_label = self._create_stat_row(enemy_content, "Crit Damage:", "0.00x", "#34495e")
        
        # Right column - Statistics and Log
        right_frame = tk.Frame(content_frame, bg="#f0f0f0")
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        # Statistics Panel
        stats_panel = tk.LabelFrame(
            right_frame,
            text="Combat Statistics",
            font=("Arial", 11, "bold"),
            bg="#ffffff",
            fg="#2c3e50",
            relief=tk.RAISED,
            borderwidth=2
        )
        stats_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        stats_content = tk.Frame(stats_panel, bg="#ffffff")
        stats_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.total_damage_label = self._create_stat_row(stats_content, "Total Player Damage:", "0", "#27ae60")
        self.total_enemy_dmg_label = self._create_stat_row(stats_content, "Total Enemy Damage:", "0", "#c0392b")
        self.player_crits_label = self._create_stat_row(stats_content, "Player Crits:", "0", "#34495e")
        self.enemy_crits_label = self._create_stat_row(stats_content, "Enemy Crits:", "0", "#34495e")
        self.blocks_label = self._create_stat_row(stats_content, "Blocks:", "0", "#3498db")
        self.total_attacks_label = self._create_stat_row(stats_content, "Total Attacks:", "0", "#34495e")
        self.enemy_kills_label = self._create_stat_row(stats_content, "Enemies Killed:", "0", "#e67e22")
        
        # Event Log Panel
        log_panel = tk.LabelFrame(
            right_frame,
            text="Recent Events (Last 50)",
            font=("Arial", 11, "bold"),
            bg="#ffffff",
            fg="#2c3e50",
            relief=tk.RAISED,
            borderwidth=2
        )
        log_panel.pack(fill=tk.BOTH, expand=True)
        
        # Button frame for copy button
        log_button_frame = tk.Frame(log_panel, bg="#ffffff")
        log_button_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        self.copy_log_button = tk.Button(
            log_button_frame,
            text="📋 Copy Log to Clipboard",
            font=("Arial", 9),
            bg="#3498db",
            fg="white",
            activebackground="#2980b9",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            command=self.copy_log_to_clipboard
        )
        self.copy_log_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Debug toggle button (always ON for real-time sim)
        self.debug_button = tk.Button(
            log_button_frame,
            text="🔍 Debug: ON",
            font=("Arial", 9),
            bg="#27ae60",
            fg="white",
            activebackground="#229954",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            command=self.toggle_debug,
            state=tk.DISABLED  # Disabled since debug is always ON
        )
        self.debug_button.pack(side=tk.LEFT)
        
        log_content = tk.Frame(log_panel, bg="#ffffff")
        log_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Scrollable text widget for event log
        log_scroll = tk.Scrollbar(log_content)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.event_log_text = tk.Text(
            log_content,
            height=15,
            font=("Consolas", 9),
            bg="#2c3e50",
            fg="#ecf0f1",
            wrap=tk.WORD,
            yscrollcommand=log_scroll.set,
            state=tk.DISABLED
        )
        self.event_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.event_log_text.yview)
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def _create_stat_row(self, parent, label_text, value_text, value_color="#34495e"):
        """Create a stat row with label and value"""
        row_frame = tk.Frame(parent, bg="#ffffff")
        row_frame.pack(fill=tk.X, pady=3)
        
        label = tk.Label(
            row_frame,
            text=label_text,
            font=("Arial", 9),
            bg="#ffffff",
            fg="#7f8c8d",
            anchor="w"
        )
        label.pack(side=tk.LEFT, padx=(0, 10))
        
        value_label = tk.Label(
            row_frame,
            text=value_text,
            font=("Arial", 9, "bold"),
            bg="#ffffff",
            fg=value_color,
            anchor="e"
        )
        value_label.pack(side=tk.RIGHT)
        
        return value_label
    
    
    def start_simulation(self):
        """Start the simulation in a separate thread"""
        if self.simulation_running and not self.simulation_paused:
            return
        
        # If paused, resume
        if self.simulation_paused:
            self.simulation_paused = False
            try:
                if self.window.winfo_exists() and hasattr(self, 'play_pause_button'):
                    self.play_pause_button.config(text="⏸ Pause", bg="#27ae60")
            except (tk.TclError, RuntimeError):
                pass
            return
        
        # Start new simulation
        self.simulation_running = True
        self.simulation_paused = False
        self.current_player_hp = self.player.health
        self.simulation_start_real_time = time.time()  # Track actual system time
        self.real_time_elapsed = 0.0  # Reset real time tracking
        
        # Enable control buttons (safely)
        try:
            if self.window.winfo_exists() and hasattr(self, 'play_pause_button'):
                self.play_pause_button.config(state=tk.NORMAL, text="⏸ Pause", bg="#27ae60")
            if self.window.winfo_exists() and hasattr(self, 'reset_button'):
                self.reset_button.config(state=tk.NORMAL)
        except (tk.TclError, RuntimeError):
            pass
        
        # Reset statistics
        self.total_player_damage = 0
        self.total_enemy_damage = 0
        self.player_crits = 0
        self.enemy_crits = 0
        self.blocks = 0
        self.total_attacks = 0
        self.enemy_kills = 0
        self.event_log.clear()
        
        # Clear log
        self.event_log_text.config(state=tk.NORMAL)
        self.event_log_text.delete(1.0, tk.END)
        self.event_log_text.config(state=tk.DISABLED)
        
        def run_simulation():
            """Run simulation and process events with real-time timing (Godot-style delta-time accumulation)"""
            try:
                for event in simulate_event_run_realtime(self.player, self.enemy):
                    if not self.simulation_running:
                        break
                    
                    # Check for pause
                    while self.simulation_paused and self.simulation_running:
                        time.sleep(0.1)  # Wait while paused
                    
                    if not self.simulation_running:
                        break
                    
                    # Get time_delta from event
                    time_delta = event.get('time_delta', 0.0)
                    
                    # Godot-style: Accumulate real time from time_delta (fixed timestep)
                    # Real time is based on simulation delta-time, NOT actual sleep time
                    # This ensures simulation time and real time stay perfectly in sync
                    if time_delta > 0:
                        self.real_time_elapsed += time_delta
                    
                    # Wait for the real time that passed in the simulation
                    # Measure actual sleep time for debugging only
                    sleep_start_time = time.time()
                    
                    if time_delta > 0:
                        # Sleep in smaller chunks to keep UI responsive and allow pause
                        # Split sleep into 10ms chunks to allow UI updates
                        sleep_chunks = max(1, int(time_delta / 0.01) + 1)
                        chunk_time = time_delta / sleep_chunks
                        for _ in range(sleep_chunks):
                            if not self.simulation_running:
                                break
                            # Check for pause during sleep
                            while self.simulation_paused and self.simulation_running:
                                time.sleep(0.1)
                            if not self.simulation_running:
                                break
                            time.sleep(chunk_time)
                    else:
                        # Small delay for instant events (like wave_start, enemy_killed)
                        # Check for pause
                        while self.simulation_paused and self.simulation_running:
                            time.sleep(0.1)
                        if self.simulation_running:
                            time.sleep(0.01)
                    
                    if not self.simulation_running:
                        break
                    
                    # Measure actual sleep time for debugging (but don't use it for time calculation)
                    sleep_end_time = time.time()
                    actual_sleep_time = sleep_end_time - sleep_start_time if time_delta > 0 else 0.01
                    
                    # Calculate time error (for debugging only - not used for time calculation)
                    time_error = actual_sleep_time - time_delta if time_delta > 0 else 0.0
                    
                    # Process event with debug info (after waiting, but time is already accumulated)
                    # Note: We do NOT adjust real_time_elapsed based on sleep errors
                    # This is Godot's approach: simulation runs at fixed timestep,
                    # actual render/sleep time is separate and doesn't affect simulation time
                    self.process_simulation_event(event, time_delta, actual_sleep_time, time_error)
                    
            except Exception as e:
                print(f"Simulation error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.simulation_running = False
                self.simulation_paused = False
                # Disable control buttons when simulation ends (safely)
                self.window.after(0, lambda: self._safe_update_button_state(self.play_pause_button, tk.DISABLED))
                self.window.after(0, lambda: self._safe_update_button_state(self.reset_button, tk.NORMAL))  # Keep reset enabled
        
        self.simulation_thread = threading.Thread(target=run_simulation, daemon=True)
        self.simulation_thread.start()
        
        # Start UI update loop
        self.update_ui()
    
    def update_ui(self):
        """Update UI elements periodically"""
        try:
            if not self.window.winfo_exists():
                return
        except (tk.TclError, RuntimeError):
            return
        
        # Update time display
        time_text = f"Time: {self.simulation_time:.2f}s"
        self.time_label.config(text=time_text)
        
        # Schedule next update (every 50ms for smooth updates)
        try:
            self.window.after(50, self.update_ui)
        except (tk.TclError, RuntimeError):
            pass
    
    def process_simulation_event(self, event, time_delta=0.0, actual_sleep_time=0.0, time_error=0.0):
        """Process a simulation event and update UI
        Note: actual_sleep_time and time_error are for debugging only, not used for time calculation
        """
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
            
            # Update wave label
            wave_text = f"Wave: {self.current_wave}-{self.current_subwave}"
            self.window.after(0, lambda: self._safe_update_wave(wave_text))
            
            # Update enemy stats
            enemy_atk = max(1, int(self.enemy.atk + self.current_wave * self.enemy.atk_scaling))
            enemy_atk_speed = self.enemy.atk_speed + self.current_wave * 0.02
            enemy_crit_chance = self.enemy.crit + self.current_wave
            enemy_crit_dmg = self.enemy.crit_dmg + self.enemy.crit_dmg_scaling * self.current_wave
            
            self.window.after(0, lambda: self._safe_update_enemy_hp(int(self.current_enemy_hp)))
            self.window.after(0, lambda: self._safe_update_enemy_atk(enemy_atk))
            self.window.after(0, lambda: self._safe_update_enemy_atk_speed(enemy_atk_speed))
            self.window.after(0, lambda: self._safe_update_enemy_crit(int(enemy_crit_chance)))
            self.window.after(0, lambda: self._safe_update_enemy_crit_dmg(enemy_crit_dmg))
            self.window.after(0, lambda: self._safe_update_player_hp(int(self.current_player_hp)))
            
            # Get attack progress from event
            e_atk_prog = event.get('enemy_attack_progress', 0.0)
            p_atk_prog = event.get('player_attack_progress', 0.0)
            
            # Get system time
            system_time = datetime.now().strftime("%I:%M:%S %p")
            
            # Debug info
            debug_info = ""
            if self.debug_mode:
                debug_info = f" | delta={time_delta:.3f}s sleep={actual_sleep_time:.3f}s err={time_error:.3f}s"
            
            # Add to log (synchronously to maintain order)
            # Use accumulated real_time_elapsed (based on time_delta, like Godot)
            log_text = f"[{self.simulation_time:.2f}s / {self.real_time_elapsed:.2f}s / {system_time}] Wave {self.current_wave}-{self.current_subwave} started | Enemy HP: {int(self.current_enemy_hp)} | p_atk_prog: {p_atk_prog:.3f} e_atk_prog: {e_atk_prog:.3f}{debug_info}"
            self._safe_add_event_to_log(log_text)
        
        elif event_type == 'player_attack':
            self.current_enemy_hp = event['enemy_hp']
            self.current_player_hp = event['player_hp']
            self.simulation_time = event['time']
            
            dmg = event['damage']
            is_crit = event['is_crit']
            
            # Update statistics
            self.total_player_damage += dmg
            self.total_attacks += 1
            if is_crit:
                self.player_crits += 1
            
            # Update UI
            self.window.after(0, lambda: self._safe_update_enemy_hp(int(self.current_enemy_hp)))
            self.window.after(0, lambda: self._safe_update_player_hp(int(self.current_player_hp)))
            self.window.after(0, lambda: self._update_statistics())
            
            # Get attack progress from event
            e_atk_prog = event.get('enemy_attack_progress', 0.0)
            p_atk_prog = event.get('player_attack_progress', 0.0)
            
            # Get system time
            system_time = datetime.now().strftime("%I:%M:%S %p")
            
            # Debug info
            debug_info = ""
            if self.debug_mode:
                debug_info = f" | delta={time_delta:.3f}s sleep={actual_sleep_time:.3f}s err={time_error:.3f}s"
            
            # Add to log (synchronously to maintain order)
            # Use accumulated real_time_elapsed (based on time_delta, like Godot)
            crit_text = " CRIT!" if is_crit else ""
            log_text = f"[{self.simulation_time:.2f}s / {self.real_time_elapsed:.2f}s / {system_time}] Player attacks: {int(dmg)} damage{crit_text} | Enemy HP: {int(self.current_enemy_hp)} | p_atk_prog: {p_atk_prog:.3f} e_atk_prog: {e_atk_prog:.3f}{debug_info}"
            self._safe_add_event_to_log(log_text)
        
        elif event_type == 'enemy_attack':
            self.current_player_hp = event['player_hp']
            self.simulation_time = event['time']
            
            dmg = event['damage']
            is_crit = event['is_crit']
            is_blocked = event['is_blocked']
            
            # Update statistics
            if is_blocked:
                self.blocks += 1
            else:
                self.total_enemy_damage += dmg
            if is_crit:
                self.enemy_crits += 1
            
            # Update UI
            self.window.after(0, lambda: self._safe_update_player_hp(int(self.current_player_hp)))
            self.window.after(0, lambda: self._update_statistics())
            
            # Get attack progress from event
            e_atk_prog = event.get('enemy_attack_progress', 0.0)
            p_atk_prog = event.get('player_attack_progress', 0.0)
            
            # Get system time
            system_time = datetime.now().strftime("%I:%M:%S %p")
            
            # Debug info
            debug_info = ""
            if self.debug_mode:
                debug_info = f" | delta={time_delta:.3f}s sleep={actual_sleep_time:.3f}s err={time_error:.3f}s"
            
            # Add to log (synchronously to maintain order)
            # Use accumulated real_time_elapsed (based on time_delta, like Godot)
            if is_blocked:
                log_text = f"[{self.simulation_time:.2f}s / {self.real_time_elapsed:.2f}s / {system_time}] Enemy attacks: BLOCKED! | Player HP: {int(self.current_player_hp)} | p_atk_prog: {p_atk_prog:.3f} e_atk_prog: {e_atk_prog:.3f}{debug_info}"
            else:
                crit_text = " CRIT!" if is_crit else ""
                log_text = f"[{self.simulation_time:.2f}s / {self.real_time_elapsed:.2f}s / {system_time}] Enemy attacks: {int(dmg)} damage{crit_text} | Player HP: {int(self.current_player_hp)} | p_atk_prog: {p_atk_prog:.3f} e_atk_prog: {e_atk_prog:.3f}{debug_info}"
            self._safe_add_event_to_log(log_text)
        
        elif event_type == 'enemy_killed':
            self.current_enemy_hp = 0
            self.simulation_time = event['time']
            self.enemy_kills += 1
            
            # Update UI
            self.window.after(0, lambda: self._safe_update_enemy_hp(0))
            self.window.after(0, lambda: self._update_statistics())
            
            # Get attack progress from event
            e_atk_prog = event.get('enemy_attack_progress', 0.0)
            p_atk_prog = event.get('player_attack_progress', 0.0)
            
            # Get system time
            system_time = datetime.now().strftime("%I:%M:%S %p")
            
            # Debug info
            debug_info = ""
            if self.debug_mode:
                debug_info = f" | delta={time_delta:.3f}s sleep={actual_sleep_time:.3f}s err={time_error:.3f}s"
            
            # Add to log (synchronously to maintain order)
            # Use accumulated real_time_elapsed (based on time_delta, like Godot)
            log_text = f"[{self.simulation_time:.2f}s / {self.real_time_elapsed:.2f}s / {system_time}] Enemy killed! | Total kills: {self.enemy_kills} | p_atk_prog: {p_atk_prog:.3f} e_atk_prog: {e_atk_prog:.3f}{debug_info}"
            self._safe_add_event_to_log(log_text)
        
        elif event_type == 'walking_0pct':
            self.simulation_time = event['time']
            walk_duration = event.get('walk_duration', 0.0)
            
            # Get attack progress from event
            e_atk_prog = event.get('enemy_attack_progress', 0.0)
            p_atk_prog = event.get('player_attack_progress', 0.0)
            
            # Get system time
            system_time = datetime.now().strftime("%I:%M:%S %p")
            
            # Debug info
            debug_info = ""
            if self.debug_mode:
                debug_info = f" | delta={time_delta:.3f}s sleep={actual_sleep_time:.3f}s err={time_error:.3f}s"
            
            # Add to log (synchronously to maintain order)
            # Use accumulated real_time_elapsed (based on time_delta, like Godot)
            log_text = f"[{self.simulation_time:.2f}s / {self.real_time_elapsed:.2f}s / {system_time}] Walking 0% (start) | Duration: {walk_duration:.2f}s | p_atk_prog: {p_atk_prog:.3f} e_atk_prog: {e_atk_prog:.3f}{debug_info}"
            self._safe_add_event_to_log(log_text)
        
        elif event_type == 'walking_50pct':
            self.simulation_time = event['time']
            walk_duration = event.get('walk_duration', 0.0)
            
            # Get attack progress from event
            e_atk_prog = event.get('enemy_attack_progress', 0.0)
            p_atk_prog = event.get('player_attack_progress', 0.0)
            
            # Get system time
            system_time = datetime.now().strftime("%I:%M:%S %p")
            
            # Debug info
            debug_info = ""
            if self.debug_mode:
                debug_info = f" | delta={time_delta:.3f}s sleep={actual_sleep_time:.3f}s err={time_error:.3f}s"
            
            # Add to log (synchronously to maintain order)
            # Use accumulated real_time_elapsed (based on time_delta, like Godot)
            log_text = f"[{self.simulation_time:.2f}s / {self.real_time_elapsed:.2f}s / {system_time}] Walking 50% complete | p_atk_prog: {p_atk_prog:.3f} e_atk_prog: {e_atk_prog:.3f}{debug_info}"
            self._safe_add_event_to_log(log_text)
        
        elif event_type == 'walking_100pct':
            self.simulation_time = event['time']
            walk_duration = event.get('walk_duration', 0.0)
            
            # Get attack progress from event
            e_atk_prog = event.get('enemy_attack_progress', 0.0)
            p_atk_prog = event.get('player_attack_progress', 0.0)
            
            # Get system time
            system_time = datetime.now().strftime("%I:%M:%S %p")
            
            # Debug info
            debug_info = ""
            if self.debug_mode:
                debug_info = f" | delta={time_delta:.3f}s sleep={actual_sleep_time:.3f}s err={time_error:.3f}s"
            
            # Add to log (synchronously to maintain order)
            # Use accumulated real_time_elapsed (based on time_delta, like Godot)
            log_text = f"[{self.simulation_time:.2f}s / {self.real_time_elapsed:.2f}s / {system_time}] Walking 100% (complete) | p_atk_prog: {p_atk_prog:.3f} e_atk_prog: {e_atk_prog:.3f}{debug_info}"
            self._safe_add_event_to_log(log_text)
        
        elif event_type == 'run_end':
            self.simulation_running = False
            self.simulation_time = event['time']
            wave_val = event['wave']
            subwave_val = event['subwave']
            
            # Update final wave label
            wave_text = f"Run Ended - Wave: {wave_val}-{subwave_val}"
            self.window.after(0, lambda: self._safe_update_wave(wave_text))
            
            # Get system time
            system_time = datetime.now().strftime("%I:%M:%S %p")
            
            # Debug info
            debug_info = ""
            if self.debug_mode:
                debug_info = f" | delta={time_delta:.3f}s sleep={actual_sleep_time:.3f}s err={time_error:.3f}s"
            
            # Add to log (synchronously to maintain order)
            # Use accumulated real_time_elapsed (based on time_delta, like Godot)
            log_text = f"[{self.simulation_time:.2f}s / {self.real_time_elapsed:.2f}s / {system_time}] === RUN ENDED === Wave: {wave_val}-{subwave_val}{debug_info}"
            self._safe_add_event_to_log(log_text)
    
    def _update_statistics(self):
        """Update statistics labels"""
        try:
            if not self.window.winfo_exists():
                return
        except (tk.TclError, RuntimeError):
            return
        
        self.total_damage_label.config(text=f"{int(self.total_player_damage)}")
        self.total_enemy_dmg_label.config(text=f"{int(self.total_enemy_damage)}")
        self.player_crits_label.config(text=f"{self.player_crits}")
        self.enemy_crits_label.config(text=f"{self.enemy_crits}")
        self.blocks_label.config(text=f"{self.blocks}")
        self.total_attacks_label.config(text=f"{self.total_attacks}")
        self.enemy_kills_label.config(text=f"{self.enemy_kills}")
    
    def _safe_update_wave(self, text):
        """Safely update wave label"""
        try:
            if self.window.winfo_exists():
                self.wave_label.config(text=text)
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_player_hp(self, hp):
        """Safely update player HP label"""
        try:
            if self.window.winfo_exists():
                self.player_hp_label.config(text=f"{hp}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_hp(self, hp):
        """Safely update enemy HP label"""
        try:
            if self.window.winfo_exists():
                self.enemy_hp_label.config(text=f"{hp}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_atk(self, atk):
        """Safely update enemy attack label"""
        try:
            if self.window.winfo_exists():
                self.enemy_atk_label.config(text=f"{atk}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_atk_speed(self, speed):
        """Safely update enemy attack speed label"""
        try:
            if self.window.winfo_exists():
                self.enemy_atk_speed_label.config(text=f"{speed:.2f}")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_crit(self, crit):
        """Safely update enemy crit chance label"""
        try:
            if self.window.winfo_exists():
                self.enemy_crit_label.config(text=f"{crit}%")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_enemy_crit_dmg(self, crit_dmg):
        """Safely update enemy crit damage label"""
        try:
            if self.window.winfo_exists():
                self.enemy_crit_dmg_label.config(text=f"{crit_dmg:.2f}x")
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_add_event_to_log(self, text):
        """Safely add event to log (thread-safe, can be called from simulation thread)"""
        try:
            if self.window.winfo_exists():
                self.event_log.append(text)
                # Use window.after to update UI from simulation thread
                self.window.after(0, lambda t=text: self._update_log_text(t))
        except (tk.TclError, RuntimeError):
            pass
    
    def _update_log_text(self, text):
        """Update log text widget (must be called from main thread)"""
        try:
            if self.window.winfo_exists():
                self.event_log_text.config(state=tk.NORMAL)
                self.event_log_text.insert(tk.END, text + "\n")
                self.event_log_text.see(tk.END)
                self.event_log_text.config(state=tk.DISABLED)
        except (tk.TclError, RuntimeError):
            pass
    
    def _safe_update_button_state(self, button, state):
        """Safely update button state"""
        try:
            if button is not None and self.window.winfo_exists() and button.winfo_exists():
                button.config(state=state)
        except (tk.TclError, RuntimeError, AttributeError):
            pass
    
    def _safe_update_button_text(self, button, text):
        """Safely update button text"""
        try:
            if button is not None and self.window.winfo_exists() and button.winfo_exists():
                button.config(text=text)
        except (tk.TclError, RuntimeError, AttributeError):
            pass
    
    def toggle_debug(self):
        """Toggle debug mode on/off"""
        self.debug_mode = not self.debug_mode
        try:
            if self.window.winfo_exists() and hasattr(self, 'debug_button'):
                if self.debug_mode:
                    self.debug_button.config(text="🔍 Debug: ON", bg="#27ae60")
                else:
                    self.debug_button.config(text="🔍 Debug: OFF", bg="#95a5a6")
        except (tk.TclError, RuntimeError):
            pass
    
    def toggle_pause(self):
        """Toggle pause/resume simulation"""
        if not self.simulation_running:
            return
        
        self.simulation_paused = not self.simulation_paused
        try:
            if self.window.winfo_exists() and hasattr(self, 'play_pause_button'):
                if self.simulation_paused:
                    self.play_pause_button.config(text="▶ Play", bg="#f39c12")
                else:
                    self.play_pause_button.config(text="⏸ Pause", bg="#27ae60")
        except (tk.TclError, RuntimeError):
            pass
    
    def reset_simulation(self):
        """Reset and restart the simulation"""
        # Stop current simulation
        self.simulation_running = False
        self.simulation_paused = False
        
        # Wait for thread to finish
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=1.0)
        
        # Reset state
        self.current_wave = 0
        self.current_subwave = 0
        self.current_player_hp = self.player.health
        self.current_enemy_hp = 0
        self.simulation_time = 0.0
        self.real_time_elapsed = 0.0
        
        # Reset statistics
        self.total_player_damage = 0
        self.total_enemy_damage = 0
        self.player_crits = 0
        self.enemy_crits = 0
        self.blocks = 0
        self.total_attacks = 0
        self.enemy_kills = 0
        self.event_log.clear()
        
        # Clear log (safely)
        try:
            if self.window.winfo_exists():
                self.event_log_text.config(state=tk.NORMAL)
                self.event_log_text.delete(1.0, tk.END)
                self.event_log_text.config(state=tk.DISABLED)
        except (tk.TclError, RuntimeError):
            pass
        
        # Reset UI labels (safely)
        try:
            if self.window.winfo_exists():
                self.wave_label.config(text="Wave: 0-0")
                self.time_label.config(text="Time: 0.00s")
                self._update_statistics()
                self._safe_update_player_hp(int(self.player.health))
                self._safe_update_enemy_hp(0)
        except (tk.TclError, RuntimeError):
            pass
        
        # Disable control buttons (safely)
        self._safe_update_button_state(self.play_pause_button, tk.DISABLED)
        self._safe_update_button_state(self.reset_button, tk.DISABLED)
        
        # Restart simulation
        self.start_simulation()
    
    def copy_log_to_clipboard(self):
        """Copy the entire event log to clipboard"""
        try:
            if not self.window.winfo_exists():
                return
            
            # Get all text from the log widget
            self.event_log_text.config(state=tk.NORMAL)
            log_content = self.event_log_text.get(1.0, tk.END)
            self.event_log_text.config(state=tk.DISABLED)
            
            # Copy to clipboard
            self.window.clipboard_clear()
            self.window.clipboard_append(log_content.strip())
            
            # Show feedback (temporarily change button text)
            if hasattr(self, 'copy_log_button'):
                original_text = self.copy_log_button.cget("text")
                self._safe_update_button_text(self.copy_log_button, "✓ Copied!")
                self.window.after(2000, lambda: self._safe_update_button_text(self.copy_log_button, "📋 Copy Log to Clipboard"))
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
    
    def on_close(self):
        """Handle window close"""
        self.simulation_running = False
        if self.simulation_thread and self.simulation_thread.is_alive():
            # Wait a bit for thread to finish
            self.simulation_thread.join(timeout=1.0)
        self.window.destroy()
