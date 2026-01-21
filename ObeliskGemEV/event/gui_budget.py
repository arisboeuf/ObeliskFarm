"""
Budget Optimizer Mode GUI.
Helps players optimize upgrade paths with limited materials.
"""

import tkinter as tk
from tkinter import ttk

from .constants import get_prestige_wave_requirement
from .utils import format_number


class BudgetOptimizerPanel:
    """Budget Optimizer mode panel"""
    
    def __init__(self, parent_frame, window_ref):
        self.parent = parent_frame
        self.window = window_ref
        
        # State
        self.material_budget = {1: 0, 2: 0, 3: 0, 4: 0}
        self.material_vars = {}
        
        self.build_ui()
    
    def build_ui(self):
        """Build the Budget Optimizer UI"""
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Main scrollable area
        canvas = tk.Canvas(self.parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
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
        
        # === HEADER ===
        header_frame = tk.Frame(scrollable_frame, background="#4CAF50", relief=tk.RIDGE, borderwidth=2)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(header_frame, text="Event Budget Optimizer", font=("Arial", 14, "bold"),
                background="#4CAF50", foreground="white").pack(pady=10)
        tk.Label(header_frame, text="Enter your available materials and get optimal upgrade recommendations",
                font=("Arial", 10), background="#4CAF50", foreground="white").pack(pady=(0, 10))
        
        # === MATERIAL INPUT ===
        input_frame = tk.Frame(scrollable_frame, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(input_frame, text="Your Materials", font=("Arial", 11, "bold"),
                background="#E8F5E9").pack(anchor="w", padx=10, pady=(10, 5))
        
        mat_inner = tk.Frame(input_frame, background="#E8F5E9")
        mat_inner.pack(fill=tk.X, padx=10, pady=10)
        
        mat_names = ["Coins (Mat 1)", "Mat 2", "Mat 3", "Mat 4"]
        mat_colors = ["#FFC107", "#9C27B0", "#00BCD4", "#E91E63"]
        
        for i in range(4):
            col_frame = tk.Frame(mat_inner, background="#E8F5E9")
            col_frame.pack(side=tk.LEFT, padx=20, pady=5)
            
            tk.Label(col_frame, text=mat_names[i], font=("Arial", 9, "bold"),
                    background="#E8F5E9", foreground=mat_colors[i]).pack()
            
            var = tk.StringVar(value="0")
            entry = ttk.Entry(col_frame, textvariable=var, width=12, font=("Arial", 10))
            entry.pack(pady=5)
            entry.bind('<Return>', lambda e: self.calculate_optimal_upgrades())
            
            self.material_vars[i + 1] = var
        
        # Prestige input
        prestige_frame = tk.Frame(mat_inner, background="#E8F5E9")
        prestige_frame.pack(side=tk.LEFT, padx=20, pady=5)
        
        tk.Label(prestige_frame, text="Prestiges", font=("Arial", 9, "bold"),
                background="#E8F5E9").pack()
        
        self.budget_prestige_var = tk.IntVar(value=0)
        prestige_spin = ttk.Spinbox(prestige_frame, from_=0, to=20, width=5,
                                    textvariable=self.budget_prestige_var)
        prestige_spin.pack(pady=5)
        
        # Calculate button
        calc_btn = tk.Button(input_frame, text="Calculate Optimal Upgrades", 
                            font=("Arial", 11, "bold"), bg="#4CAF50", fg="white",
                            command=self.calculate_optimal_upgrades)
        calc_btn.pack(pady=10)
        
        # === RESULTS ===
        results_frame = tk.Frame(scrollable_frame, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        results_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(results_frame, text="Recommended Upgrades", font=("Arial", 11, "bold"),
                background="#FFF3E0").pack(anchor="w", padx=10, pady=(10, 5))
        
        self.budget_results_text = tk.Text(results_frame, height=20, font=("Consolas", 10),
                                           background="#FFF3E0", relief=tk.FLAT, wrap=tk.WORD)
        self.budget_results_text.pack(fill=tk.X, padx=10, pady=10)
        
        # Initial placeholder text
        self.show_initial_instructions()
    
    def show_initial_instructions(self):
        """Show initial instructions in results area"""
        self.budget_results_text.config(state=tk.NORMAL)
        self.budget_results_text.delete(1.0, tk.END)
        
        self.budget_results_text.insert(tk.END, "Enter your materials above and click 'Calculate Optimal Upgrades'\n\n")
        self.budget_results_text.insert(tk.END, "The optimizer will recommend:\n")
        self.budget_results_text.insert(tk.END, "  - Which upgrades to buy for each material type\n")
        self.budget_results_text.insert(tk.END, "  - Expected wave you can reach\n")
        self.budget_results_text.insert(tk.END, "  - Materials left over after upgrades\n\n")
        self.budget_results_text.insert(tk.END, "Note: Tier X upgrades cost Material X\n")
        self.budget_results_text.insert(tk.END, "  - Tier 1 = Coins (Mat 1)\n")
        self.budget_results_text.insert(tk.END, "  - Tier 2 = Mat 2\n")
        self.budget_results_text.insert(tk.END, "  - Tier 3 = Mat 3\n")
        self.budget_results_text.insert(tk.END, "  - Tier 4 = Mat 4\n\n")
        self.budget_results_text.insert(tk.END, "Prestige Wave Requirements (estimated):\n")
        for p in range(1, 11):
            self.budget_results_text.insert(tk.END, f"  Prestige {p}: Wave {get_prestige_wave_requirement(p)}\n")
        
        self.budget_results_text.config(state=tk.DISABLED)
    
    def calculate_optimal_upgrades(self):
        """Calculate optimal upgrades based on material budget"""
        # Parse material inputs
        try:
            for i in range(1, 5):
                val = self.material_vars[i].get().replace(",", "").replace(".", "")
                self.material_budget[i] = int(val) if val else 0
        except ValueError:
            self.budget_results_text.config(state=tk.NORMAL)
            self.budget_results_text.delete(1.0, tk.END)
            self.budget_results_text.insert(tk.END, "Error: Please enter valid numbers for materials")
            self.budget_results_text.config(state=tk.DISABLED)
            return
        
        prestige = self.budget_prestige_var.get()
        next_prestige_wave = get_prestige_wave_requirement(prestige + 1)
        
        # TODO: Implement actual optimization algorithm
        # For now, show a placeholder with the parsed values
        
        self.budget_results_text.config(state=tk.NORMAL)
        self.budget_results_text.delete(1.0, tk.END)
        
        self.budget_results_text.insert(tk.END, "=== Budget Analysis ===\n\n")
        self.budget_results_text.insert(tk.END, f"Available Materials:\n")
        self.budget_results_text.insert(tk.END, f"  Coins (T1): {format_number(self.material_budget[1])}\n")
        self.budget_results_text.insert(tk.END, f"  Mat 2 (T2): {format_number(self.material_budget[2])}\n")
        self.budget_results_text.insert(tk.END, f"  Mat 3 (T3): {format_number(self.material_budget[3])}\n")
        self.budget_results_text.insert(tk.END, f"  Mat 4 (T4): {format_number(self.material_budget[4])}\n\n")
        
        self.budget_results_text.insert(tk.END, f"Current Prestige: {prestige}\n")
        self.budget_results_text.insert(tk.END, f"Next Prestige: {prestige + 1} (requires Wave {next_prestige_wave})\n\n")
        
        self.budget_results_text.insert(tk.END, "=== Optimization Coming Soon ===\n\n")
        self.budget_results_text.insert(tk.END, "This feature is under development.\n\n")
        self.budget_results_text.insert(tk.END, "Planned features:\n")
        self.budget_results_text.insert(tk.END, "  - Greedy algorithm to maximize wave reached\n")
        self.budget_results_text.insert(tk.END, "  - Time-to-prestige optimization (including speed upgrades)\n")
        self.budget_results_text.insert(tk.END, "  - Show recommended upgrade levels per tier\n")
        self.budget_results_text.insert(tk.END, "  - Show expected wave with those upgrades\n")
        self.budget_results_text.insert(tk.END, "  - Show leftover materials\n\n")
        self.budget_results_text.insert(tk.END, "For now, use the 'Love2D Simulator' mode to\n")
        self.budget_results_text.insert(tk.END, "manually test different upgrade combinations.\n")
        
        self.budget_results_text.config(state=tk.DISABLED)
