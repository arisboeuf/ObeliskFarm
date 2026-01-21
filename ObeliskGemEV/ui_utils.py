"""
Shared UI utilities for ObeliskGemEV
"""

import tkinter as tk


def create_tooltip(widget, text, position="right"):
    """
    Creates a styled tooltip with rich formatting.
    
    Args:
        widget: The tkinter widget to attach the tooltip to
        text: The tooltip text (supports newlines, headers end with ':')
        position: "right" (default) or "left" - where to position relative to cursor
    """
    def on_enter(event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        
        # Calculate position based on preference
        if position == "left":
            # Estimate tooltip width and position to the left
            x = event.x_root - 250
            if x < 10:
                x = event.x_root + 10
        else:
            x = event.x_root + 10
        y = event.y_root + 10
        
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
        if hasattr(widget, 'tooltip'):
            widget.tooltip.destroy()
            del widget.tooltip
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


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
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        
        # Smart positioning
        tooltip_width = 300
        tooltip_height = 50 + len(lines) * 18
        screen_width = tooltip.winfo_screenwidth()
        screen_height = tooltip.winfo_screenheight()
        
        if position == "left" or (position == "auto" and event.x_root > screen_width / 2):
            x = event.x_root - tooltip_width - 10
            if x < 10:
                x = event.x_root + 20
        else:
            x = event.x_root + 10
        
        y = event.y_root - 20
        if y + tooltip_height > screen_height - 50:
            y = screen_height - tooltip_height - 50
        if y < 10:
            y = 10
        
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
        if hasattr(widget, 'tooltip'):
            widget.tooltip.destroy()
            del widget.tooltip
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)
