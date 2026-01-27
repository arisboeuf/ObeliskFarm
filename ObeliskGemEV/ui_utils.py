"""
Shared UI utilities for ObeliskFarm
"""

import tkinter as tk
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller bundle.
    
    Args:
        relative_path: Path relative to ObeliskFarm folder (e.g., 'sprites/common/gem.png')
    
    Returns:
        Absolute Path to the resource
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - use temp directory where PyInstaller extracts files
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script - use the ObeliskFarm directory
        base_path = Path(__file__).parent
    return base_path / relative_path


def calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height, position="auto"):
    """
    Calculate the optimal position for a tooltip to ensure it stays on screen.
    
    Args:
        event: The tkinter event with x_root and y_root cursor position
        tooltip_width: Estimated width of the tooltip
        tooltip_height: Estimated height of the tooltip
        screen_width: Width of the screen
        screen_height: Height of the screen
        position: "auto" (default), "left", or "right" - horizontal preference
    
    Returns:
        tuple: (x, y) coordinates for the tooltip position
    """
    margin = 10  # Minimum distance from screen edge
    cursor_offset = 10  # Distance from cursor
    
    # Smart horizontal positioning
    if position == "left":
        x = event.x_root - tooltip_width - cursor_offset
        if x < margin:
            x = event.x_root + cursor_offset
    elif position == "right":
        x = event.x_root + cursor_offset
        if x + tooltip_width > screen_width - margin:
            x = event.x_root - tooltip_width - cursor_offset
    else:  # auto
        # Prefer right, but switch to left if not enough space
        if event.x_root + tooltip_width + cursor_offset + margin > screen_width:
            x = event.x_root - tooltip_width - cursor_offset
        else:
            x = event.x_root + cursor_offset
    
    # Ensure x stays on screen
    if x < margin:
        x = margin
    if x + tooltip_width > screen_width - margin:
        x = screen_width - tooltip_width - margin
    
    # Smart vertical positioning
    # Prefer below cursor, but switch to above if not enough space
    if event.y_root + tooltip_height + cursor_offset + margin > screen_height:
        y = event.y_root - tooltip_height - cursor_offset
    else:
        y = event.y_root + cursor_offset
    
    # Ensure y stays on screen
    if y < margin:
        y = margin
    if y + tooltip_height > screen_height - margin:
        y = screen_height - tooltip_height - margin
    
    return x, y


def create_tooltip(widget, text, position="auto"):
    """
    Creates a styled tooltip with rich formatting.
    
    Args:
        widget: The tkinter widget to attach the tooltip to
        text: The tooltip text (supports newlines, headers end with ':')
        position: "auto" (default), "right", or "left" - where to position relative to cursor
                  "auto" will intelligently position to avoid going off-screen
    """
    def on_enter(event):
        # If a tooltip is already open for this widget, close it first
        try:
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        except Exception:
            pass
        
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        
        # Estimate tooltip dimensions based on content
        lines = text.split('\n')
        tooltip_width = min(max(len(line) for line in lines) * 8 + 30, 400) if lines else 250
        tooltip_height = len(lines) * 18 + 30
        
        # Get screen dimensions and calculate position
        screen_width = tooltip.winfo_screenwidth()
        screen_height = tooltip.winfo_screenheight()
        x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height, position)
        
        tooltip.wm_geometry(f"+{x}+{y}")
        
        # Outer frame for shadow effect
        outer_frame = tk.Frame(
            tooltip,
            background="#2C3E50",
            relief=tk.FLAT,
            borderwidth=0
        )
        outer_frame.pack(padx=2, pady=2)
        
        # Inner frame with content
        inner_frame = tk.Frame(
            outer_frame,
            background="#FFFFFF",
            relief=tk.FLAT,
            borderwidth=0
        )
        inner_frame.pack(padx=1, pady=1)
        
        # Text widget for rich text formatting
        text_widget = tk.Text(
            inner_frame,
            background="#FFFFFF",
            foreground="#2C3E50",
            font=("Arial", 9),
            wrap=tk.WORD,
            padx=12,
            pady=8,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0
        )
        
        # Tags for formatting
        text_widget.tag_config("bold", font=("Arial", 9, "bold"))
        text_widget.tag_config("header", font=("Arial", 10, "bold"), foreground="#1976D2")
        
        # Process and format text
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # First line or lines ending with ':' (not indented) as header
            if i == 0 or (line.endswith(':') and not line.startswith('   ')):
                text_widget.insert(tk.END, line + '\n', "header")
            else:
                text_widget.insert(tk.END, line + '\n')
        
        # Adjust size
        text_widget.config(height=len(lines), width=max(len(line) for line in lines) if lines else 20)
        text_widget.config(state=tk.DISABLED)  # Read-only
        text_widget.pack()
        
        widget.tooltip = tooltip
    
    def on_leave(event):
        try:
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        except Exception:
            pass
    
    # If the widget gets destroyed while the tooltip is open (e.g. UI refresh),
    # the <Leave> event never fires. Clean up the tooltip on destroy as well.
    def on_destroy(event):
        on_leave(event)
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)
    widget.bind("<Destroy>", on_destroy)


def create_simple_tooltip(widget, lines, title=None, title_color="#1976D2", border_color="#2C3E50", position="auto"):
    """
    Creates a simple tooltip with optional title and list of lines.
    
    Args:
        widget: The tkinter widget to attach the tooltip to
        lines: List of strings to display
        title: Optional title string (displayed bold at top)
        title_color: Color for the title text
        border_color: Color for the border/shadow
        position: "auto", "left", or "right"
    """
    def on_enter(event):
        # If a tooltip is already open for this widget, close it first
        try:
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        except Exception:
            pass
        
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        
        # Estimate tooltip dimensions
        tooltip_width = 300
        tooltip_height = 50 + len(lines) * 18
        if title:
            tooltip_height += 25
        
        # Get screen dimensions and calculate position
        screen_width = tooltip.winfo_screenwidth()
        screen_height = tooltip.winfo_screenheight()
        x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height, position)
        
        tooltip.wm_geometry(f"+{x}+{y}")
        
        # Outer frame for shadow effect
        outer_frame = tk.Frame(tooltip, background=border_color, relief=tk.FLAT)
        outer_frame.pack(padx=2, pady=2)
        
        # Inner frame
        inner_frame = tk.Frame(outer_frame, background="#FFFFFF")
        inner_frame.pack(padx=1, pady=1)
        
        content_frame = tk.Frame(inner_frame, background="#FFFFFF", padx=10, pady=8)
        content_frame.pack()
        
        # Title
        if title:
            tk.Label(content_frame, text=title, 
                    font=("Arial", 10, "bold"), foreground=title_color, 
                    background="#FFFFFF").pack(anchor=tk.W)
            tk.Label(content_frame, text="", background="#FFFFFF").pack()  # Spacer
        
        # Lines
        for line in lines:
            tk.Label(content_frame, text=line, font=("Arial", 9), 
                    background="#FFFFFF", anchor=tk.W).pack(anchor=tk.W)
        
        widget.tooltip = tooltip
    
    def on_leave(event):
        try:
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        except Exception:
            pass
    
    def on_destroy(event):
        on_leave(event)
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)
    widget.bind("<Destroy>", on_destroy)
