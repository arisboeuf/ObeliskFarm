"""
Lootbug - Option Analyzer

Analyzes whether specific gem purchases are worth it based on current EV/h.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_utils import create_tooltip as _create_tooltip


class LootbugWindow:
    """Window for analyzing various purchase options"""
    
    def __init__(self, parent, calculator):
        self.parent = parent
        self.calculator = calculator
        
        # Create new window - larger and resizable
        self.window = tk.Toplevel(parent)
        self.window.title("Option Analyzer")
        self.window.state('zoomed')  # Maximize window on Windows
        self.window.resizable(True, True)
        self.window.minsize(600, 500)
        
        # Set icon (if available)
        try:
            icon_path = Path(__file__).parent.parent / "sprites" / "lootbug.png"
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.window.iconphoto(False, icon_photo)
        except:
            pass  # Ignore if icon can't be loaded
        
        self.create_widgets()
    
    def create_widgets(self):
        """Creates the widgets in the window"""
        
        # Header
        header_frame = ttk.Frame(self.window, padding="5")
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            header_frame,
            text="🔍 Option Analyzer",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Find out if specific purchases are worth it!",
            font=("Arial", 9),
            foreground="gray"
        )
        subtitle_label.pack(pady=(3, 0))
        
        # Separator
        ttk.Separator(self.window, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Content Frame
        content_frame = ttk.Frame(self.window, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Option 1: 2x Game Speed
        self.create_speed_option(content_frame)
    
    def create_speed_option(self, parent):
        """Creates the 2x Game Speed option analysis"""
        
        # Frame for this option
        option_frame = ttk.LabelFrame(
            parent,
            text="",  # No text, we create our own header
            padding="8"
        )
        option_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Header with icon and text
        header_frame = ttk.Frame(option_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Try to load the 2x Speed icon
        try:
            speed_icon_path = Path(__file__).parent.parent / "sprites" / "gamespeed2x.png"
            if speed_icon_path.exists():
                speed_image = Image.open(speed_icon_path)
                speed_image = speed_image.resize((32, 32), Image.Resampling.LANCZOS)
                self.speed_icon_photo = ImageTk.PhotoImage(speed_image)
                speed_icon_label = tk.Label(header_frame, image=self.speed_icon_photo, background="white", relief=tk.RIDGE, borderwidth=1)
                speed_icon_label.pack(side=tk.LEFT, padx=(0, 8))
        except:
            pass
        
        ttk.Label(
            header_frame,
            text="⚡ 2× Game Speed",
            font=("Arial", 12, "bold")
        ).pack(side=tk.LEFT)
        
        # Separator after header
        ttk.Separator(option_frame, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Description
        desc_label = ttk.Label(
            option_frame,
            text="Cost: 15 Gems\nDuration: 10 minutes at 2× Game Speed",
            font=("Arial", 10)
        )
        desc_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Calculate if it's worth it
        is_worth, profit, affected_ev, total_ev = self.calculate_speed_option_worth()
        
        # Result frame
        result_frame = ttk.Frame(option_frame)
        result_frame.pack(fill=tk.X, pady=5)
        
        # Status (Worth it / Not worth it)
        if is_worth:
            status_text = "✅ WORTH IT!"
            status_color = "green"
        else:
            status_text = "❌ NOT WORTH IT"
            status_color = "red"
        
        status_label = tk.Label(
            result_frame,
            text=status_text,
            font=("Arial", 14, "bold"),
            foreground=status_color
        )
        status_label.pack(pady=(0, 5))
        
        # Details Frame
        details_frame = ttk.Frame(option_frame)
        details_frame.pack(fill=tk.BOTH, expand=True)
        details_frame.columnconfigure(0, weight=0)
        details_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Affected EV/h
        ttk.Label(details_frame, text="Affected EV/h:").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        ttk.Label(
            details_frame,
            text=f"{affected_ev:.1f} Gems/h",
            font=("Arial", 9, "bold")
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Gain in 10 minutes with 2x Speed
        ttk.Label(details_frame, text="With 2× Speed (10 min):").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        
        # Calculate gain in 10 minutes with 2× Speed
        # In 10 minutes with 2× Speed you collect as much as in 20 minutes normal
        gain_10min = affected_ev * (20.0 / 60.0)
        
        ttk.Label(
            details_frame,
            text=f"{gain_10min:.1f} Gems",
            font=("Arial", 9, "bold")
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Gain without Speed
        ttk.Label(details_frame, text="Normal (10 min):").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        
        gain_10min_normal = affected_ev * (10.0 / 60.0)
        
        ttk.Label(
            details_frame,
            text=f"{gain_10min_normal:.1f} Gems",
            font=("Arial", 9)
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Additional gain
        ttk.Label(details_frame, text="Additional Gain:").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        
        additional_gain = gain_10min - gain_10min_normal
        
        ttk.Label(
            details_frame,
            text=f"{additional_gain:.1f} Gems",
            font=("Arial", 9, "bold"),
            foreground="blue"
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Cost
        ttk.Label(details_frame, text="Cost:").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2
        )
        ttk.Label(
            details_frame,
            text="15.0 Gems",
            font=("Arial", 9),
            foreground="red"
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Separator
        ttk.Separator(details_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )
        row += 1
        
        # Net profit
        ttk.Label(
            details_frame,
            text="Net Profit:",
            font=("Arial", 10, "bold")
        ).grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        profit_color = "green" if profit > 0 else "red"
        profit_text = f"+{profit:.1f} Gems" if profit > 0 else f"{profit:.1f} Gems"
        
        ttk.Label(
            details_frame,
            text=profit_text,
            font=("Arial", 10, "bold"),
            foreground=profit_color
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Info icon with hover tooltip
        info_frame = ttk.Frame(option_frame)
        info_frame.pack(fill=tk.X, pady=(8, 0))
        
        info_icon = tk.Label(
            info_frame,
            text="ℹ️ Info (Hover for details)",
            font=("Arial", 9),
            foreground="#1976D2",
            cursor="hand2"
        )
        info_icon.pack(anchor=tk.W)
        
        # Tooltip text
        info_text = (
            "2× Game Speed Effects:\n"
            "\n"
            "Affected:\n"
            "• Gems (Base) - freebie-based\n"
            "• Stonks - freebie-based\n"
            "• Skill Shards - freebie-based\n"
            "• Gem Bomb - halves recharge time\n"
            "• Founder Bomb - halves recharge time\n"
            "\n"
            "NOT affected:\n"
            "• Founder Supply Drop - time-based, independent"
        )
        
        self.create_tooltip(info_icon, info_text)
    
    def create_tooltip(self, widget, text):
        """Creates a modern styled tooltip with rich formatting"""
        _create_tooltip(widget, text)
    
    def calculate_speed_option_worth(self):
        """
        Calculates whether the 2x Speed option is worth it.
        
        2x Game Speed affects:
        - Freebie-based incomes (gems, stonks, skill shards)
        - Founder Bomb (halves recharge time)
        
        NOT affected:
        - Founder Supply Drop (independent of game speed)
        
        Returns:
            (is_worth, profit, affected_ev, total_ev)
        """
        # Get current EV values
        ev = self.calculator.calculate_total_ev_per_hour()
        
        # Freebie-based incomes + bombs are affected
        # (2x Speed halves bomb recharge time)
        affected_ev = (
            ev['gems_base'] +
            ev['stonks_ev'] +
            ev['skill_shards_ev'] +
            ev['gem_bomb_gems'] +  # Gem Bomb recharge is affected by game speed
            ev['founder_bomb_boost']  # Founder Bomb recharge is affected by game speed
            # NOT: founder_speed_boost, founder_gems (independent of game speed)
        )
        
        # In 10 minutes with 2× Speed you collect as much as in 20 minutes normal
        # Additional gain = affected_ev * (20/60 - 10/60)
        gain_with_speed = affected_ev * (20.0 / 60.0)  # 20 minutes value
        gain_without_speed = affected_ev * (10.0 / 60.0)  # 10 minutes value
        additional_gain = gain_with_speed - gain_without_speed
        
        # Cost
        cost = 15.0
        
        # Net profit
        profit = additional_gain - cost
        
        # Worth it if profit > 0
        is_worth = profit > 0
        
        return is_worth, profit, affected_ev, ev['total']
