"""
Event Simulator Window - Main entry point.

Provides toggle between Budget Optimizer and Love2D Simulator modes.
"""

import tkinter as tk
from tkinter import ttk

from .gui_budget import BudgetOptimizerPanel
from .gui_love2d import Love2DSimulatorPanel


class EventSimulatorWindow:
    """Event Simulator Window - Tkinter GUI with mode toggle"""
    
    MODE_LOVE2D = "love2d"
    MODE_BUDGET = "budget"
    
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Event Simulator")
        self.window.geometry("1100x750")
        self.window.minsize(900, 650)
        
        # Current mode
        self.current_mode = self.MODE_BUDGET  # Start with our mode
        
        # Active panel reference
        self.active_panel = None
        
        # Main container
        self.main_container = ttk.Frame(self.window, padding="5")
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Mode toggle at top
        self.create_mode_toggle()
        
        # Content frame (will be replaced when switching modes)
        self.content_frame = ttk.Frame(self.main_container)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Build initial mode
        self.build_current_mode()
    
    def create_mode_toggle(self):
        """Create the mode toggle bar at the top"""
        toggle_frame = tk.Frame(self.main_container, background="#37474F", relief=tk.RAISED, borderwidth=1)
        toggle_frame.pack(fill=tk.X, pady=(0, 5))
        
        inner_frame = tk.Frame(toggle_frame, background="#37474F")
        inner_frame.pack(pady=5, padx=10)
        
        tk.Label(inner_frame, text="Mode:", font=("Arial", 10, "bold"),
                background="#37474F", foreground="white").pack(side=tk.LEFT, padx=(0, 10))
        
        # Budget Optimizer button (our mode)
        self.budget_btn = tk.Button(
            inner_frame, text="Budget Optimizer", 
            font=("Arial", 9, "bold"),
            command=lambda: self.switch_mode(self.MODE_BUDGET),
            relief=tk.SUNKEN if self.current_mode == self.MODE_BUDGET else tk.RAISED,
            bg="#4CAF50" if self.current_mode == self.MODE_BUDGET else "#757575",
            fg="white", width=16
        )
        self.budget_btn.pack(side=tk.LEFT, padx=2)
        
        # Love2D Simulator button
        self.love2d_btn = tk.Button(
            inner_frame, text="Love2D Simulator",
            font=("Arial", 9, "bold"),
            command=lambda: self.switch_mode(self.MODE_LOVE2D),
            relief=tk.SUNKEN if self.current_mode == self.MODE_LOVE2D else tk.RAISED,
            bg="#2196F3" if self.current_mode == self.MODE_LOVE2D else "#757575",
            fg="white", width=16
        )
        self.love2d_btn.pack(side=tk.LEFT, padx=2)
        
        # Info label
        self.mode_info_label = tk.Label(
            inner_frame, text="", font=("Arial", 8),
            background="#37474F", foreground="#B0BEC5"
        )
        self.mode_info_label.pack(side=tk.LEFT, padx=(20, 0))
        self.update_mode_info()
    
    def update_mode_info(self):
        """Update the mode info label"""
        if self.current_mode == self.MODE_BUDGET:
            self.mode_info_label.config(text="Enter your materials, get optimal upgrade recommendations")
        else:
            self.mode_info_label.config(text="Original Love2D simulator port - manual upgrade testing")
    
    def switch_mode(self, new_mode: str):
        """Switch between modes"""
        if new_mode == self.current_mode:
            return
        
        self.current_mode = new_mode
        
        # Update button states
        if new_mode == self.MODE_BUDGET:
            self.budget_btn.config(relief=tk.SUNKEN, bg="#4CAF50")
            self.love2d_btn.config(relief=tk.RAISED, bg="#757575")
        else:
            self.budget_btn.config(relief=tk.RAISED, bg="#757575")
            self.love2d_btn.config(relief=tk.SUNKEN, bg="#2196F3")
        
        self.update_mode_info()
        
        # Rebuild content
        self.build_current_mode()
    
    def build_current_mode(self):
        """Build the UI for the current mode"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if self.current_mode == self.MODE_BUDGET:
            self.active_panel = BudgetOptimizerPanel(self.content_frame, self.window)
        else:
            self.active_panel = Love2DSimulatorPanel(self.content_frame, self.window)
