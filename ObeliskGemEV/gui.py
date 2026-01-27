"""
GUI for ObeliskFarm Calculator
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import json
import copy
from pathlib import Path
from PIL import Image, ImageTk
from dataclasses import fields
import threading
import webbrowser


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - use temp directory where PyInstaller extracts files
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script - use the script's directory
        base_path = Path(__file__).parent
    return base_path / relative_path


from ui_utils import get_save_dir


# Save file path (in user data folder for persistence)
SAVE_DIR = get_save_dir()
SAVE_FILE = SAVE_DIR / "gemev_save.json"

# Matplotlib for Bar Chart
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Add module directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from freebie_ev_calculator import FreebieEVCalculator, GameParameters
from archaeology import ArchaeologySimulatorWindow
from lootbug import LootbugWindow
from event import EventSimulatorWindow
try:
    from stargazing import StargazingWindow
    STARGAZING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import StargazingWindow: {e}")
    StargazingWindow = None
    STARGAZING_AVAILABLE = False
from ui_utils import create_tooltip as _create_tooltip, calculate_tooltip_position

try:
    from build_info import APP_VERSION as CURRENT_VERSION, REPO as UPDATE_REPO
except Exception:
    CURRENT_VERSION = "0.0.0"
    UPDATE_REPO = "arisboeuf/ObeliskFarm"

try:
    import update_manager
except Exception:
    update_manager = None


def _load_saved_game_parameters() -> GameParameters:
    """Load GameParameters from the Gem-EV save file.
    
    This is used by the main menu when opening Lootbug directly, so the EV/h
    matches the last saved Gem EV settings (instead of defaults).
    """
    params = GameParameters()
    
    if not SAVE_FILE.exists():
        return params
    
    try:
        with open(SAVE_FILE, 'r') as f:
            state = json.load(f)
    except Exception:
        return params
    
    percent_keys = {
        'skill_shard_chance',
        'jackpot_chance',
        'instant_refresh_chance',
        'free_bomb_chance',
        'gem_bomb_gem_chance',
        'd20_bomb_refill_chance',
        'founder_bomb_speed_chance',
        'cherry_bomb_triple_charge_chance',
    }
    int_keys = {
        'jackpot_rolls',
        'vip_lounge_level',
        'obelisk_level',
        'total_bomb_types',
        'd20_bomb_charges_distributed',
        # recharge card levels
        'gem_bomb_recharge_card_level',
        'cherry_bomb_recharge_card_level',
        'battery_bomb_recharge_card_level',
        'd20_bomb_recharge_card_level',
        'founder_bomb_recharge_card_level',
    }
    
    field_names = {f.name for f in fields(GameParameters)}
    overrides = {}
    
    for key, raw in state.items():
        if key not in field_names:
            continue
        try:
            if key in int_keys:
                overrides[key] = int(raw)
            elif key in percent_keys:
                overrides[key] = float(raw) / 100.0
            else:
                overrides[key] = float(raw)
        except (TypeError, ValueError):
            # Ignore invalid saved values; keep default
            continue
    
    try:
        params = GameParameters(**overrides)
    except TypeError:
        # If something changed in the dataclass signature, fall back to defaults
        params = GameParameters()
    
    # Stonks checkbox is stored as a separate bool (not in GameParameters)
    stonks_enabled = state.get('stonks_enabled', True)
    params.stonks_chance = 0.0 if not stonks_enabled else 0.01
    params.stonks_bonus_gems = 200.0
    
    return params

# Import version/config info
try:
    from . import OBELISK_LEVEL
except ImportError:
    # Direct execution fallback
    OBELISK_LEVEL = 30


class MainMenuWindow:
    """Startup menu window for selecting which module to open"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ObeliskFarm - Select Module")
        # Fixed window size - calculated to fit all content without scrolling
        # 5 buttons in 2 columns (3 rows): 2×250px buttons + padding = ~550px width
        # Height: title + subtitle + 3 rows of buttons (120px each) + footer = ~650px
        self.root.geometry("600x650")
        self.root.resizable(False, False)  # Fixed size, no resizing
        
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Set icon
        try:
            icon_path = get_resource_path("sprites/common/gem.png")
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(False, icon_photo)
                self.icon_photo = icon_photo
        except:
            pass
        
        # Main container - no scrolling needed
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Main frame - no scrolling
        main_frame = ttk.Frame(main_container, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="ObeliskFarm",
            font=("Arial", 24, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="Select a module to open:",
            font=("Arial", 12)
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Buttons frame with grid layout (2 columns) - fixed size to fit buttons exactly
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(padx=20, pady=10)
        # Configure columns to be equal width but not expand unnecessarily
        buttons_frame.columnconfigure(0, weight=1, uniform="button")
        buttons_frame.columnconfigure(1, weight=1, uniform="button")
        
        # Load icons for buttons
        self._load_menu_icons()
        
        # Define buttons in order
        buttons = [
            ('gem', 'Gem EV Calculator', self.open_gem_ev),
            ('archaeology', 'Archaeology Simulator', self.open_archaeology),
            ('event', 'Event Simulator', self.open_event),
            ('lootbug', 'Lootbug Analyzer', self.open_lootbug),
            ('stargazing', 'Stargazing', self.open_stargazing),
        ]
        
        # Create buttons in grid (2 columns) - buttons will fill available space horizontally
        row = 0
        col = 0
        for icon_key, text, command in buttons:
            button = self._create_icon_button(
                buttons_frame,
                icon=self.menu_icons.get(icon_key),
                text=text,
                command=command
            )
            button.grid(row=row, column=col, padx=10, pady=10, sticky="ew")  # Expand horizontally only
            
            col += 1
            if col >= 2:
                col = 0
                row += 1
        
        # Footer with donation button and message - centered
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(pady=(20, 10))
        
        # Container for donation elements (to center them together)
        donation_container = ttk.Frame(footer_frame)
        donation_container.pack()
        
        # Blinking donation message
        self.donation_label = ttk.Label(
            donation_container,
            text="Buy me a coffee and support the tool development...",
            font=("Arial", 9, "italic"),
            foreground="#666666"
        )
        self.donation_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Blinking red "!" button with rounded corners
        self.donation_button = self._create_rounded_button(
            donation_container,
            text="!",
            bg="#FF0000",
            fg="white",
            command=self._open_donation_window,
            width=40,
            height=40,
            corner_radius=10
        )
        self.donation_button.pack(side=tk.LEFT)
        
        # Update button (self-update for EXE builds)
        update_button = ttk.Button(
            footer_frame,
            text="Check for Updates",
            command=lambda: self.check_for_updates(interactive=True),
        )
        update_button.pack(pady=(12, 0))

        # Start blinking animation
        self._blink_after_id = None
        self._blink_state = True
        self._blink_animation()
        
        # Silent update check shortly after start (EXE only)
        self.root.after(1500, lambda: self.check_for_updates(interactive=False))

        # Store reference to prevent garbage collection
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def check_for_updates(self, interactive: bool) -> None:
        """Check GitHub releases and optionally self-update (EXE builds)."""
        if update_manager is None:
            if interactive:
                messagebox.showinfo(
                    "Updates",
                    "Update checker is not available in this build.",
                )
            return

        if not getattr(sys, "frozen", False):
            # In source mode we only offer the download page.
            if interactive:
                if messagebox.askyesno(
                    "Updates",
                    "Updates are available via GitHub Releases.\nOpen the download page?",
                ):
                    webbrowser.open(f"https://github.com/{UPDATE_REPO}/releases/latest")
            return

        def _worker():
            try:
                info = update_manager.get_latest_release_info(UPDATE_REPO)
                if info is None:
                    if interactive:
                        self.root.after(
                            0,
                            lambda: messagebox.showinfo(
                                "Updates",
                                "Could not check for updates (network error).",
                            ),
                        )
                    return

                latest_version = info["version"]
                exe_url = info["exe_url"]
                html_url = info["html_url"]

                if not update_manager.is_newer_version(latest_version, CURRENT_VERSION):
                    if interactive:
                        self.root.after(
                            0,
                            lambda: messagebox.showinfo(
                                "Updates",
                                f"You are up to date.\n\nCurrent: {CURRENT_VERSION}\nLatest: {latest_version}",
                            ),
                        )
                    return

                def _prompt():
                    if not messagebox.askyesno(
                        "Update available",
                        f"A new version is available.\n\nCurrent: {CURRENT_VERSION}\nLatest: {latest_version}\n\nUpdate now?",
                    ):
                        return
                    try:
                        update_manager.perform_self_update(
                            exe_url=exe_url,
                            latest_version=latest_version,
                            current_pid=os.getpid(),
                        )
                    except Exception as e:
                        messagebox.showerror(
                            "Update failed",
                            f"Could not start the updater.\n\n{e}\n\nYou can download manually:\n{html_url}",
                        )

                self.root.after(0, _prompt)

            except Exception:
                if interactive:
                    self.root.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Updates",
                            "Could not check for updates.",
                        ),
                    )

        threading.Thread(target=_worker, daemon=True).start()
    
    def _load_menu_icons(self):
        """Load icons for menu buttons"""
        self.menu_icons = {}
        
        icon_paths = {
            'gem': 'sprites/common/gem.png',
            'archaeology': 'sprites/archaeology/archaeology.png',
            'event': 'sprites/event/event_button.png',
            'stargazing': 'sprites/stargazing/stargazing.png',
            'lootbug': 'sprites/lootbug/lootbug.png',
        }
        
        for key, relative_path in icon_paths.items():
            try:
                icon_path = get_resource_path(relative_path)
                if icon_path.exists():
                    icon_image = Image.open(icon_path)
                    icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                    self.menu_icons[key] = ImageTk.PhotoImage(icon_image, master=self.root)
            except Exception as e:
                print(f"Warning: Could not load {key} icon: {e}")
                self.menu_icons[key] = None
    
    def _create_icon_button(self, parent, icon, text, command):
        """Create a button with icon and text in tile format"""
        # Create a frame for the button content with nice styling (tile format)
        # Calculate width: (600px window - 40px padding - 30px button spacing) / 2 = 265px
        button_frame = tk.Frame(
            parent,
            relief=tk.RAISED,
            borderwidth=2,
            bg="#E3F2FD",
            highlightbackground="#1976D2",
            highlightthickness=1,
            width=265,  # Calculated to fit 2 columns in 600px window
            height=120  # Fixed height
        )
        button_frame.pack_propagate(False)  # Keep fixed size
        
        def on_enter(e):
            button_frame.config(bg="#BBDEFB", relief=tk.SUNKEN)
            content_frame.config(bg="#BBDEFB")
            if icon:
                icon_label.config(bg="#BBDEFB")
            text_label.config(bg="#BBDEFB")
        
        def on_leave(e):
            button_frame.config(bg="#E3F2FD", relief=tk.RAISED)
            content_frame.config(bg="#E3F2FD")
            if icon:
                icon_label.config(bg="#E3F2FD")
            text_label.config(bg="#E3F2FD")
        
        def on_click(e):
            command()
        
        # Make the entire frame clickable
        button_frame.bind("<Button-1>", on_click)
        button_frame.bind("<Enter>", on_enter)
        button_frame.bind("<Leave>", on_leave)
        button_frame.config(cursor="hand2")
        
        # Icon and text container (centered for tile format)
        content_frame = tk.Frame(button_frame, bg="#E3F2FD")
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        content_frame.bind("<Button-1>", on_click)
        content_frame.bind("<Enter>", on_enter)
        content_frame.bind("<Leave>", on_leave)
        content_frame.config(cursor="hand2")
        
        # Icon (centered above text)
        if icon:
            icon_label = tk.Label(
                content_frame,
                image=icon,
                cursor="hand2",
                bg="#E3F2FD"
            )
            icon_label.pack(pady=(0, 8))
            icon_label.bind("<Button-1>", on_click)
            icon_label.bind("<Enter>", on_enter)
            icon_label.bind("<Leave>", on_leave)
        else:
            # Fallback: use emoji if icon not available
            emoji_map = {
                'gem': '💎',
                'archaeology': '🔍',
                'event': '🎉',
                'stargazing': '⭐',
                'lootbug': '🐛',
            }
            emoji = emoji_map.get(text.lower().split()[0], '📦')
            emoji_label = tk.Label(
                content_frame,
                text=emoji,
                font=("Arial", 24),
                cursor="hand2",
                bg="#E3F2FD"
            )
            emoji_label.pack(pady=(0, 8))
            emoji_label.bind("<Button-1>", on_click)
            emoji_label.bind("<Enter>", on_enter)
            emoji_label.bind("<Leave>", on_leave)
        
        # Text (centered below icon)
        text_label = tk.Label(
            content_frame,
            text=text,
            font=("Arial", 10, "bold"),
            cursor="hand2",
            anchor="center",
            bg="#E3F2FD",
            fg="#1976D2",
            wraplength=200,
            justify=tk.CENTER
        )
        text_label.pack()
        text_label.bind("<Button-1>", on_click)
        text_label.bind("<Enter>", on_enter)
        text_label.bind("<Leave>", on_leave)
        
        return button_frame
    
    def _on_close(self):
        """Handle window close"""
        # Cancel any pending blink callback to avoid calling widgets after destroy()
        try:
            after_id = getattr(self, "_blink_after_id", None)
            if after_id:
                self.root.after_cancel(after_id)
                self._blink_after_id = None
        except tk.TclError:
            pass
        self.root.destroy()
    
    def _create_rounded_button(self, parent, text, bg, fg, command, width=40, height=40, corner_radius=10):
        """Create a rounded button using Canvas"""
        # Get parent background color - handle both tk.Frame and ttk.Frame
        parent_bg = '#f0f0f0'  # Default light gray
        try:
            # Try to get background from tk.Frame
            parent_bg = parent.cget('background')
        except:
            try:
                # Try alternative for some widgets
                parent_bg = parent.cget('bg')
            except:
                # For ttk.Frame, use system default or fallback
                if sys.platform == 'win32':
                    parent_bg = 'SystemButtonFace'
                else:
                    parent_bg = '#f0f0f0'
        
        canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bg=parent_bg,
            cursor="hand2"
        )
        
        def _canvas_exists() -> bool:
            """Return True if canvas still exists in Tk."""
            try:
                return bool(canvas.winfo_exists())
            except tk.TclError:
                return False

        def draw_rounded_rectangle(canvas, x1, y1, x2, y2, radius, fill, outline, width):
            """Draw a rounded rectangle on canvas"""
            # Draw the four corner arcs (filled)
            # Top-left
            canvas.create_arc(x1, y1, x1 + 2*radius, y1 + 2*radius, 
                            start=90, extent=90, fill=fill, outline="", style=tk.PIESLICE)
            # Top-right
            canvas.create_arc(x2 - 2*radius, y1, x2, y1 + 2*radius, 
                            start=0, extent=90, fill=fill, outline="", style=tk.PIESLICE)
            # Bottom-left
            canvas.create_arc(x1, y2 - 2*radius, x1 + 2*radius, y2, 
                            start=180, extent=90, fill=fill, outline="", style=tk.PIESLICE)
            # Bottom-right
            canvas.create_arc(x2 - 2*radius, y2 - 2*radius, x2, y2, 
                            start=270, extent=90, fill=fill, outline="", style=tk.PIESLICE)
            
            # Fill the center rectangles
            canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline="")
            canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline="")
            
            # Draw outline arcs
            canvas.create_arc(x1, y1, x1 + 2*radius, y1 + 2*radius, 
                            start=90, extent=90, fill="", outline=outline, width=width, style=tk.ARC)
            canvas.create_arc(x2 - 2*radius, y1, x2, y1 + 2*radius, 
                            start=0, extent=90, fill="", outline=outline, width=width, style=tk.ARC)
            canvas.create_arc(x1, y2 - 2*radius, x1 + 2*radius, y2, 
                            start=180, extent=90, fill="", outline=outline, width=width, style=tk.ARC)
            canvas.create_arc(x2 - 2*radius, y2 - 2*radius, x2, y2, 
                            start=270, extent=90, fill="", outline=outline, width=width, style=tk.ARC)
            
            # Draw outline lines
            canvas.create_line(x1 + radius, y1, x2 - radius, y1, fill=outline, width=width)
            canvas.create_line(x1 + radius, y2, x2 - radius, y2, fill=outline, width=width)
            canvas.create_line(x1, y1 + radius, x1, y2 - radius, fill=outline, width=width)
            canvas.create_line(x2, y1 + radius, x2, y2 - radius, fill=outline, width=width)
        
        # Draw rounded rectangle
        def draw_button(bg_color, fg_color):
            if not _canvas_exists():
                return
            try:
                canvas.delete("all")
                # Draw rounded rectangle
                draw_rounded_rectangle(canvas, 2, 2, width-2, height-2, 
                                     corner_radius, bg_color, "#CC0000", 2)
                # Draw text
                canvas.create_text(
                    width//2, height//2,
                    text=text,
                    fill=fg_color,
                    font=("Arial", 14, "bold")
                )
            except tk.TclError:
                # Widget might have been destroyed between scheduled callbacks.
                return
        
        # Initial draw
        draw_button(bg, fg)
        
        # Store colors for animation
        canvas.button_bg = bg
        canvas.button_fg = fg
        
        # Hover effects
        def on_enter(e):
            canvas.config(cursor="hand2")
        
        def on_leave(e):
            canvas.config(cursor="hand2")
        
        def on_click(e):
            command()
        
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<Button-1>", on_click)
        
        # Method to update button colors (for blinking)
        def update_colors(new_bg, new_fg):
            canvas.button_bg = new_bg
            canvas.button_fg = new_fg
            draw_button(new_bg, new_fg)
        
        canvas.update_colors = update_colors
        
        return canvas
    
    def _blink_animation(self):
        """Animate blinking of donation button and message"""
        if not self.root.winfo_exists():
            return

        # Stop animation if widgets are gone (e.g. during teardown / UI rebuild)
        try:
            if not hasattr(self, "donation_button") or not hasattr(self, "donation_label"):
                return
            if hasattr(self.donation_button, "winfo_exists") and not self.donation_button.winfo_exists():
                return
            if hasattr(self.donation_label, "winfo_exists") and not self.donation_label.winfo_exists():
                return
        except tk.TclError:
            return
        
        # Toggle blink state
        self._blink_state = not self._blink_state
        
        try:
            if self._blink_state:
                # Show button and message
                if hasattr(self.donation_button, 'update_colors'):
                    self.donation_button.update_colors("#FF0000", "white")
                else:
                    self.donation_button.config(bg="#FF0000", fg="white")
                self.donation_label.config(foreground="#666666")
            else:
                # Hide button and message (make transparent/light)
                if hasattr(self.donation_button, 'update_colors'):
                    self.donation_button.update_colors("#FFCCCC", "#FFCCCC")
                else:
                    self.donation_button.config(bg="#FFCCCC", fg="#FFCCCC")
                self.donation_label.config(foreground="#E0E0E0")
        except tk.TclError:
            # Widget got destroyed mid-callback; stop scheduling.
            self._blink_after_id = None
            return
        
        # Schedule next blink (every 800ms)
        try:
            self._blink_after_id = self.root.after(800, self._blink_animation)
        except tk.TclError:
            self._blink_after_id = None
    
    def _open_donation_window(self):
        """Open donation window with thank you message and link"""
        # Stop blinking when clicked
        self._blink_state = False
        if hasattr(self.donation_button, 'update_colors'):
            self.donation_button.update_colors("#FF0000", "white")
        else:
            self.donation_button.config(bg="#FF0000", fg="white")
        self.donation_label.config(foreground="#666666")
        
        # Create donation window
        donation_window = tk.Toplevel(self.root)
        donation_window.title("Support ObeliskFarm")
        donation_window.geometry("500x300")
        donation_window.resizable(False, False)
        
        # Center window
        donation_window.update_idletasks()
        width = donation_window.winfo_width()
        height = donation_window.winfo_height()
        x = (donation_window.winfo_screenwidth() // 2) - (width // 2)
        y = (donation_window.winfo_screenheight() // 2) - (height // 2)
        donation_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Main frame
        main_frame = ttk.Frame(donation_window, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Thank you message
        thank_you_label = ttk.Label(
            main_frame,
            text="Thank you for your interest in ObeliskFarm!",
            font=("Arial", 16, "bold"),
            justify=tk.CENTER
        )
        thank_you_label.pack(pady=(0, 20))
        
        # Description
        desc_label = ttk.Label(
            main_frame,
            text="If you find this tool helpful and would like to support its development,\nI would greatly appreciate a small donation.",
            font=("Arial", 11),
            justify=tk.CENTER
        )
        desc_label.pack(pady=(0, 30))
        
        # Donation link button
        link_frame = ttk.Frame(main_frame)
        link_frame.pack(pady=(0, 20))
        
        link_label = ttk.Label(
            link_frame,
            text="Donation Link:",
            font=("Arial", 10)
        )
        link_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Buy Me a Coffee donation link
        donation_link = "https://buymeacoffee.com/arisboeuf"
        
        link_button = tk.Button(
            link_frame,
            text="☕ Buy me a coffee",
            font=("Arial", 11, "bold"),
            fg="white",
            bg="#FF813F",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            command=lambda: self._open_link(donation_link)
        )
        link_button.pack(side=tk.LEFT)
        
        # Close button
        close_button = ttk.Button(
            main_frame,
            text="Close",
            command=donation_window.destroy
        )
        close_button.pack(pady=(20, 0))
    
    def _open_link(self, url):
        """Open URL in default browser"""
        import webbrowser
        webbrowser.open(url)
    
    def open_gem_ev(self):
        """Open Gem EV Calculator - replaces menu window"""
        # Destroy menu widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create Gem EV GUI in the same root window
        app = ObeliskFarmGUI(self.root)
        # Window will be maximized by ObeliskFarmGUI.__init__
    
    def _open_toplevel_module(self, module_class, *args):
        """Helper to open a Toplevel module window and handle cleanup"""
        # Create a hidden root for the Toplevel window
        hidden_root = tk.Tk()
        hidden_root.withdraw()  # Hide the root window
        
        # Track the Toplevel window
        toplevel_window = None
        
        def check_and_close():
            """Check if Toplevel is still alive, close root if not"""
            try:
                if toplevel_window and toplevel_window.window.winfo_exists():
                    # Toplevel still exists, check again later
                    hidden_root.after(100, check_and_close)
                else:
                    # Toplevel closed, close root and menu
                    hidden_root.quit()
                    hidden_root.destroy()
                    # Also destroy menu if it still exists
                    try:
                        if self.root.winfo_exists():
                            self.root.quit()
                            self.root.destroy()
                    except:
                        pass
            except:
                # Toplevel destroyed, close root and menu
                try:
                    hidden_root.quit()
                    hidden_root.destroy()
                except:
                    pass
                try:
                    if self.root.winfo_exists():
                        self.root.quit()
                        self.root.destroy()
                except:
                    pass
        
        # Open the module
        try:
            # Make hidden_root visible temporarily to allow image loading
            hidden_root.deiconify()
            hidden_root.update_idletasks()
            
            # Create the module window
            toplevel_window = module_class(hidden_root, *args)
            
            # Force multiple updates to ensure all widgets and images are fully loaded
            # Process updates multiple times to ensure everything is initialized
            for _ in range(5):
                hidden_root.update_idletasks()
                toplevel_window.window.update_idletasks()
                hidden_root.update()
                toplevel_window.window.update()
            
            # Now hide the hidden_root again (images are already loaded and associated with it)
            hidden_root.withdraw()
            
            # Lower menu window to back (but don't hide/destroy - keep it alive for image references)
            # This ensures images stay in memory while allowing the Toplevel to be in front
            try:
                if self.root.winfo_exists():
                    # Move menu to back and minimize it (but don't destroy)
                    self.root.lower()  # Send to back
                    try:
                        self.root.state('iconic')  # Minimize (Windows)
                    except:
                        try:
                            self.root.iconify()  # Alternative minimize method
                        except:
                            pass
            except:
                pass
            
            # Start checking for Toplevel closure
            hidden_root.after(100, check_and_close)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error opening module:\n{str(e)}"
            )
            hidden_root.destroy()
            return
        
        # Run the hidden root's mainloop
        hidden_root.mainloop()
    
    def open_archaeology(self):
        """Open Archaeology Simulator - opens in new window, closes menu"""
        self._open_toplevel_module(ArchaeologySimulatorWindow)
    
    def open_event(self):
        """Open Event Simulator - opens in new window, closes menu"""
        self._open_toplevel_module(EventSimulatorWindow)
    
    def open_stargazing(self):
        """Open Stargazing Calculator - opens in new window, closes menu"""
        if not STARGAZING_AVAILABLE or StargazingWindow is None:
            messagebox.showerror(
                "Error",
                "Stargazing Calculator is not available.\n"
                "Please check that the module is properly installed."
            )
            return
        self._open_toplevel_module(StargazingWindow)
    
    def open_lootbug(self):
        """Open Lootbug Analyzer - opens in new window, closes menu"""
        # Create a calculator for LootbugWindow
        try:
            params = _load_saved_game_parameters()
            calculator = FreebieEVCalculator(params)
            self._open_toplevel_module(LootbugWindow, calculator)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error opening Lootbug Analyzer:\n{str(e)}"
            )


class ObeliskFarmGUI:
    """GUI for the ObeliskFarm Calculator"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"ObeliskFarm Calculator (Data based on Obelisk Level {OBELISK_LEVEL})")
        # Maximized window on startup
        self.root.state('zoomed')  # Maximize window on Windows
        self.root.resizable(True, True)
        
        # Icon setzen (gem.png)
        try:
            icon_path = get_resource_path("sprites/common/gem.png")
            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(False, icon_photo)
        except:
            pass  # Ignore if icon can't be loaded
        
        # Optional: Mindestgröße setzen, damit das Layout nicht zu klein wird
        self.root.minsize(1000, 600)
        
        # Flag für Live-Updates
        self.auto_calculate_enabled = True
        self.calculation_pending = False
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Dezent farbliche Trennung für verschiedene Bereiche
        # Freebie-Bereich: sehr helles Blau
        style.configure('Freebie.TLabelframe.Label', foreground='#2E5F8F')
        # Founder-Bereich: sehr helles Grün
        style.configure('Founder.TLabelframe.Label', foreground='#5F8F2E')
        # Bomb-Bereich: sehr helles Rot
        style.configure('Bomb.TLabelframe.Label', foreground='#8F5F2E')
        
        # Variablen für Eingabefelder
        self.vars = {}

        # Bomb recharge card toggles (per bomb)
        # 0 = none, 1 = card (1.5x), 2 = gilded (2x), 3 = polychrome (3x)
        self.bomb_recharge_card_vars = {}
        self.bomb_recharge_card_labels = {}
        
        # Matplotlib Figure für Chart
        self.fig = None
        self.canvas = None
        
        # Erstelle GUI
        self.create_widgets()
        
        # Lade Standard-Werte
        self.load_defaults()
        
        # Lade gespeicherten Zustand (überschreibt Defaults)
        self.load_state()
        
        # Auto-save on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Initiale Berechnung
        self.root.after(100, self.calculate)
    
    def _on_close(self):
        """Handle window close - save state and destroy"""
        self.save_state()
        self.root.destroy()
    
    def save_state(self):
        """Save current parameter values to file"""
        state = {
            'stonks_enabled': self.stonks_enabled.get() if hasattr(self, 'stonks_enabled') else True,
        }
        
        # Save all parameter values
        for key, info in self.vars.items():
            state[key] = info['var'].get()
        
        # Save bomb recharge card levels (not part of self.vars)
        for bomb_key, var in getattr(self, 'bomb_recharge_card_vars', {}).items():
            state[f"{bomb_key}_recharge_card_level"] = int(var.get())
        
        try:
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            with open(SAVE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def load_state(self):
        """Load saved parameter values from file"""
        if not SAVE_FILE.exists():
            return
        
        try:
            with open(SAVE_FILE, 'r') as f:
                state = json.load(f)
            
            # Load stonks checkbox state
            if hasattr(self, 'stonks_enabled'):
                self.stonks_enabled.set(state.get('stonks_enabled', True))
            
            # Load all parameter values
            for key, info in self.vars.items():
                if key in state:
                    info['var'].set(state[key])
            
            # Load bomb recharge card levels
            for bomb_key, var in getattr(self, 'bomb_recharge_card_vars', {}).items():
                saved = state.get(f"{bomb_key}_recharge_card_level", None)
                if saved is not None:
                    try:
                        var.set(int(saved))
                    except (TypeError, ValueError):
                        var.set(0)
                self._update_bomb_recharge_card_visuals(bomb_key)
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
    
    def create_widgets(self):
        """Erstellt alle GUI-Widgets"""
        
        # Hauptcontainer - kompakteres Padding
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Linke Spalte (Parameter) feste Breite, rechte Spalte (Ergebnisse) flexibel
        main_frame.columnconfigure(0, weight=0, minsize=320)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Titel-Zeile: Kompakt mit Lootbug-Button direkt daneben
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(
            title_frame,
            text="ObeliskFarm Calculator",
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Linke Spalte: Parameter
        self.create_parameter_section(main_frame)
        
        # Rechte Spalte: Ergebnisse + Chart
        self.create_result_section(main_frame)
    
    def create_parameter_section(self, parent):
        """Erstellt die Parameter-Eingabefelder (links)"""
        
        # Frame für Parameter mit Scrollbar - kompakterer Abstand
        param_container = ttk.Frame(parent)
        param_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        param_container.columnconfigure(0, weight=1)
        param_container.rowconfigure(0, weight=1)
        
        # Canvas für Scrollbar
        canvas = tk.Canvas(param_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(param_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Mausrad-Scrolling aktivieren
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # ============================================
        # FREEBIE BEREICH
        # ============================================
        # Container mit Hintergrundfarbe
        freebie_container = tk.Frame(scrollable_frame, background="#E3F2FD", relief=tk.RIDGE, borderwidth=2)
        freebie_container.pack(fill=tk.X, padx=3, pady=(3, 8))
        
        freebie_header_frame = tk.Frame(freebie_container, background="#E3F2FD")
        freebie_header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        freebie_label = tk.Label(freebie_header_frame, text="🎁 FREEBIE", font=("Arial", 10, "bold"), background="#E3F2FD")
        freebie_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        freebie_help_label = tk.Label(freebie_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray", background="#E3F2FD")
        freebie_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        freebie_frame = tk.Frame(freebie_container, background="#E3F2FD")
        freebie_frame.pack(fill=tk.X, padx=5, pady=5)
        freebie_frame.columnconfigure(0, weight=0)  # Labels - fixed width
        freebie_frame.columnconfigure(1, weight=0)  # Entry fields - fixed width
        
        # Tooltip für Freebie-Info
        freebie_info = (
            "FREEBIE Parameters:\n"
            "\n"
            "Base Values:\n"
            "• Freebie Gems: Fixed 9.0\n"
            "• Freebie Timer: 7.0 minutes\n"
            "• Freebie Claim: % of freebies claimed per day (default: 100%)\n"
            "\n"
            "Special Drops:\n"
            "• Skill Shards: 12% chance, 12.5 Gems value\n"
            "• Stonks: 1% chance, 200 Gems bonus\n"
            "\n"
            "Multipliers:\n"
            "• Jackpot: 5% chance for 5 additional rolls\n"
            "• Refresh: 5% chance for instant refresh"
        )
        self.create_tooltip(freebie_help_label, freebie_info)
        
        row = 0
        
        # Basis-Parameter
        tk.Label(freebie_frame, text="Base:", font=("Arial", 9, "bold"), background="#E3F2FD").grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry_with_buttons(freebie_frame, "freebie_gems_base", "  Freebie Gems (Base):", row, "9.0", bg_color="#E3F2FD", show_marginal_ev=True)
        row += 1
        
        self.create_entry(freebie_frame, "freebie_timer_minutes", "  Freebie Timer (Minutes):", row, "7.0", bg_color="#E3F2FD")
        row += 1
        
        self.create_entry(freebie_frame, "freebie_claim_percentage", "  Freebie Claim (% per Day):", row, "100.0", bg_color="#E3F2FD")
        row += 1
        
        # Separator - kompakter
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Skill Shards (Freebie) - mit Icon
        skill_shard_header_frame = tk.Frame(freebie_frame, background="#E3F2FD")
        skill_shard_header_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))
        
        tk.Label(skill_shard_header_frame, text="Skill Shards (Freebie):", font=("Arial", 9, "bold"), background="#E3F2FD").pack(side=tk.LEFT)
        
        # Versuche, das Skill Shard Icon zu laden
        try:
            skill_shard_icon_path = get_resource_path("sprites/common/skill_shard.png")
            if skill_shard_icon_path.exists():
                skill_shard_image = Image.open(skill_shard_icon_path)
                skill_shard_image = skill_shard_image.resize((16, 16), Image.Resampling.LANCZOS)
                self.skill_shard_icon_photo = ImageTk.PhotoImage(skill_shard_image)
                skill_shard_icon_label = tk.Label(skill_shard_header_frame, image=self.skill_shard_icon_photo, background="#E3F2FD")
                skill_shard_icon_label.pack(side=tk.LEFT, padx=(5, 0))
        except:
            pass
        
        row += 1
        
        self.create_entry(freebie_frame, "skill_shard_chance", "  Skill Shard Chance (%):", row, "12.0", is_percent=True, bg_color="#E3F2FD")
        row += 1
        
        self.create_entry(freebie_frame, "skill_shard_value_gems", "  Skill Shard Value (Gems):", row, "12.5", bg_color="#E3F2FD")
        row += 1
        
        # Separator - kompakter
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Stonks (Freebie) - mit Icon
        stonks_header_frame = tk.Frame(freebie_frame, background="#E3F2FD")
        stonks_header_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=3)
        
        # Versuche, das Stonks Icon zu laden
        try:
            stonks_icon_path = get_resource_path("sprites/common/stonks_tree.png")
            if stonks_icon_path.exists():
                stonks_image = Image.open(stonks_icon_path)
                stonks_image = stonks_image.resize((20, 20), Image.Resampling.LANCZOS)
                self.stonks_icon_photo = ImageTk.PhotoImage(stonks_image)
                stonks_icon_label = tk.Label(stonks_header_frame, image=self.stonks_icon_photo, background="#E3F2FD")
                stonks_icon_label.pack(side=tk.LEFT, padx=(0, 5))
        except:
            pass
        
        stonks_var = tk.BooleanVar(value=True)  # Default: aktiviert
        self.stonks_enabled = stonks_var
        stonks_checkbox = ttk.Checkbutton(
            stonks_header_frame,
            text="Stonks enabled (1% chance, 200 Gems bonus)",
            variable=stonks_var,
            command=self.trigger_auto_calculate
        )
        stonks_checkbox.pack(side=tk.LEFT)
        
        row += 1
        
        # Separator - kompakter
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Jackpot (Freebie)
        tk.Label(freebie_frame, text="Jackpot (Freebie):", font=("Arial", 9, "bold"), background="#E3F2FD").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(freebie_frame, "jackpot_chance", "  Jackpot Chance (%):", row, "5.0", is_percent=True, bg_color="#E3F2FD")
        row += 1
        
        self.create_entry(freebie_frame, "jackpot_rolls", "  Jackpot Rolls:", row, "5", is_int=True, bg_color="#E3F2FD")
        row += 1
        
        # Separator - kompakter
        ttk.Separator(freebie_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Refresh (Freebie)
        tk.Label(freebie_frame, text="Refresh (Freebie):", font=("Arial", 9, "bold"), background="#E3F2FD").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        self.create_entry(freebie_frame, "instant_refresh_chance", "  Instant Refresh Chance (%):", row, "5.0", is_percent=True, bg_color="#E3F2FD")
        
        # ============================================
        # FOUNDER SUPPLY DROP BEREICH
        # ============================================
        # Container mit Hintergrundfarbe
        founder_container = tk.Frame(scrollable_frame, background="#E8F5E9", relief=tk.RIDGE, borderwidth=2)
        founder_container.pack(fill=tk.X, padx=3, pady=(3, 8))
        
        founder_header_frame = tk.Frame(founder_container, background="#E8F5E9")
        founder_header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        founder_label = tk.Label(founder_header_frame, text="📦 FOUNDER SUPPLY DROP", font=("Arial", 10, "bold"), background="#E8F5E9")
        founder_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        founder_help_label = tk.Label(founder_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray", background="#E8F5E9")
        founder_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        founder_frame = tk.Frame(founder_container, background="#E8F5E9")
        founder_frame.pack(fill=tk.X, padx=5, pady=5)
        founder_frame.columnconfigure(0, weight=0)  # Labels - fixed width
        founder_frame.columnconfigure(1, weight=0)  # Entry fields - fixed width
        
        # Tooltip für Founder Supply Drop Info
        founder_info = (
            "FOUNDER SUPPLY DROP:\n"
            "\n"
            "VIP Lounge Level:\n"
            "• Interval: 60 - 2×(Level-1) minutes\n"
            "• Double Chance: 12% at Lvl 2, +6% per level\n"
            "• Triple Chance: 16% at Level 7\n"
            "\n"
            "Rewards:\n"
            "• Founder Gems: Fixed 10 Gems per drop\n"
            "• Founder Speed: 2× speed for 5 minutes\n"
            "  (saves time → more freebies → gem-equivalent)\n"
            "• 1/1234 Chance: 10 gifts per supply drop\n"
            "\n"
            "Bonus:\n"
            "• Obelisk Level affects bonus gem amounts"
        )
        self.create_tooltip(founder_help_label, founder_info)
        
        row = 0
        
        self.create_entry(founder_frame, "vip_lounge_level", "VIP Lounge Level (1-7):", row, "2", is_int=True, bg_color="#E8F5E9")
        row += 1
        
        self.create_entry(founder_frame, "obelisk_level", "Obelisk Level:", row, "26", is_int=True, bg_color="#E8F5E9")
        
        # ============================================
        # BOMBS BEREICH
        # ============================================
        # Container mit Hintergrundfarbe
        bomb_container = tk.Frame(scrollable_frame, background="#FFF3E0", relief=tk.RIDGE, borderwidth=2)
        bomb_container.pack(fill=tk.X, padx=3, pady=(3, 8))
        
        bomb_header_frame = tk.Frame(bomb_container, background="#FFF3E0")
        bomb_header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        bomb_label = tk.Label(bomb_header_frame, text="💣 BOMBS", font=("Arial", 10, "bold"), background="#FFF3E0")
        bomb_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        bomb_help_label = tk.Label(bomb_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray", background="#FFF3E0")
        bomb_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        bomb_frame = tk.Frame(bomb_container, background="#FFF3E0")
        bomb_frame.pack(fill=tk.X, padx=5, pady=5)
        bomb_frame.columnconfigure(0, weight=0)  # Labels - fixed width
        bomb_frame.columnconfigure(1, weight=0)  # Entry fields - fixed width
        
        # Tooltip für Bombs-Info
        bombs_info = (
            "BOMB MECHANICS:\n"
            "\n"
            "Free Bomb Chance:\n"
            "• 16% chance that a bomb click consumes 0 charges\n"
            "• Applies to the ENTIRE dump (all charges at once)\n"
            "• Affects ALL bomb types\n"
            "\n"
            "Strategy Cycle:\n"
            "• Gem (to create space) → [Cherry → Battery → D20 → Gem] repeat\n"
            "• Cherry triggers many batteries, then D20, then Gem comes into play\n"
            "\n"
            "Recursive Refills:\n"
            "• Battery and D20 refill each other and Cherry\n"
            "• More Battery/D20 clicks → more refills → even more clicks\n"
            "• This creates a recursive amplification effect\n"
            "• All refills ultimately benefit Gem Bomb (directly or via Cherry)"
        )
        self.create_tooltip(bomb_help_label, bombs_info)
        
        row = 0
        
        # Free Bomb Chance (allgemein)
        self.create_entry(bomb_frame, "free_bomb_chance", "Free Bomb Chance (%):", row, "16.0", is_percent=True, bg_color="#FFF3E0")
        row += 1
        
        # Separator
        ttk.Separator(bomb_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8
        )
        row += 1
        
        # ============================================
        # FOUNDER BOMB (zusammengefasst mit Speed)
        # ============================================
        founder_bomb_bg = "#FFE9D6"  # Slightly different tint to visually separate the sub-section
        founder_bomb_container = tk.Frame(
            bomb_frame,
            background=founder_bomb_bg,
            relief=tk.RIDGE,
            borderwidth=2
        )
        founder_bomb_container.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6), padx=1)
        founder_bomb_container.columnconfigure(0, weight=0)
        founder_bomb_container.columnconfigure(1, weight=0)
        
        inner_row = 0
        
        founder_bomb_header_frame = tk.Frame(founder_bomb_container, background=founder_bomb_bg)
        founder_bomb_header_frame.grid(row=inner_row, column=0, columnspan=2, sticky=tk.W, pady=(5, 3), padx=5)
        
        tk.Label(
            founder_bomb_header_frame,
            text="Founder Bomb:",
            font=("Arial", 9, "bold"),
            background=founder_bomb_bg
        ).pack(side=tk.LEFT)

        # Recharge card toggles for Founder Bomb
        self._create_bomb_recharge_card_buttons(founder_bomb_header_frame, "founder_bomb", bg_color=founder_bomb_bg)
        
        # Versuche, das Founders Bomb Icon zu laden
        try:
            bomb_icon_path = get_resource_path("sprites/event/founderbomb.png")
            if bomb_icon_path.exists():
                bomb_image = Image.open(bomb_icon_path)
                bomb_image = bomb_image.resize((16, 16), Image.Resampling.LANCZOS)
                self.founder_bomb_icon_photo = ImageTk.PhotoImage(bomb_image)
                bomb_icon_label = tk.Label(founder_bomb_header_frame, image=self.founder_bomb_icon_photo, background=founder_bomb_bg)
                bomb_icon_label.pack(side=tk.LEFT, padx=(5, 0))
        except:
            pass
        
        inner_row += 1
        
        self.create_entry(founder_bomb_container, "founder_bomb_interval_seconds", "  Founder Bomb Interval (Seconds):", inner_row, "87.0", bg_color=founder_bomb_bg)
        inner_row += 1
        
        self.create_entry(founder_bomb_container, "founder_bomb_speed_chance", "  Speed Chance (%):", inner_row, "10.0", is_percent=True, bg_color=founder_bomb_bg)
        inner_row += 1
        
        self.create_entry(founder_bomb_container, "founder_bomb_speed_multiplier", "  Speed Multiplier:", inner_row, "2.0", bg_color=founder_bomb_bg)
        inner_row += 1
        
        self.create_entry(founder_bomb_container, "founder_bomb_speed_duration_seconds", "  Speed Duration (Seconds):", inner_row, "10.0", bg_color=founder_bomb_bg)
        
        # Advance outer grid row by one (the container occupies one row)
        row += 1
        
        # Separator
        ttk.Separator(bomb_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8
        )
        row += 1
        
        # ============================================
        # CHERRY, BATTERY, D20, GEM BOMB SECTION
        # ============================================
        tk.Label(bomb_frame, text="Cherry → Battery → D20 → Gem Cycle:", font=("Arial", 9, "bold"), background="#FFF3E0").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
        )
        row += 1
        
        # Total Bomb Types (für Battery/D20 Berechnung)
        self.create_entry(bomb_frame, "total_bomb_types", "  Total Bomb Types:", row, "12", is_int=True, bg_color="#FFF3E0")
        row += 1
        
        # Separator
        ttk.Separator(bomb_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Gem Bomb
        gem_bomb_header_frame = tk.Frame(bomb_frame, background="#FFF3E0")
        gem_bomb_header_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))
        
        tk.Label(gem_bomb_header_frame, text="Gem Bomb:", font=("Arial", 9, "bold"), background="#FFF3E0").pack(side=tk.LEFT)
        
        # Versuche, das Gem Bomb Icon zu laden
        try:
            gem_bomb_icon_path = get_resource_path("sprites/event/gembomb.png")
            if gem_bomb_icon_path.exists():
                gem_bomb_image = Image.open(gem_bomb_icon_path)
                gem_bomb_image = gem_bomb_image.resize((16, 16), Image.Resampling.LANCZOS)
                self.gem_bomb_icon_photo = ImageTk.PhotoImage(gem_bomb_image)
                gem_bomb_icon_label = tk.Label(gem_bomb_header_frame, image=self.gem_bomb_icon_photo, background="#FFF3E0")
                gem_bomb_icon_label.pack(side=tk.LEFT, padx=(5, 0))
        except:
            pass
        
        # Fragezeichen-Icon für Gem Bomb Tooltip
        gem_bomb_help_label = tk.Label(gem_bomb_header_frame, text="❓", font=("Arial", 8), cursor="hand2", foreground="gray", background="#FFF3E0")
        gem_bomb_help_label.pack(side=tk.LEFT, padx=(5, 0))

        # Recharge card toggles for Gem Bomb
        self._create_bomb_recharge_card_buttons(gem_bomb_header_frame, "gem_bomb", bg_color="#FFF3E0")
        
        gem_bomb_info = (
            "Gem Bomb:\n"
            "• 3% chance per charge to gain 1 Gem\n"
            "• Primary gem source from bombs\n"
            "• Receives refills from Battery and D20\n"
            "• Cherry Bomb gives free Gem Bomb clicks (no charge cost)\n"
            "• Benefits from recursive refill amplification"
        )
        self.create_tooltip(gem_bomb_help_label, gem_bomb_info)
        
        row += 1
        
        self.create_entry(bomb_frame, "gem_bomb_recharge_seconds", "  Gem Bomb Recharge (Seconds):", row, "46.0", bg_color="#FFF3E0")
        row += 1
        
        self.create_entry(bomb_frame, "gem_bomb_gem_chance", "  Gem Chance per Charge (%):", row, "3.0", is_percent=True, bg_color="#FFF3E0")
        row += 1
        
        # Separator
        ttk.Separator(bomb_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Cherry Bomb
        cherry_bomb_header_frame = tk.Frame(bomb_frame, background="#FFF3E0")
        cherry_bomb_header_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))
        
        tk.Label(cherry_bomb_header_frame, text="Cherry Bomb:", font=("Arial", 9, "bold"), background="#FFF3E0").pack(side=tk.LEFT)
        
        # Versuche, das Cherry Bomb Icon zu laden
        try:
            cherry_bomb_icon_path = get_resource_path("sprites/event/cherrybomb.png")
            if cherry_bomb_icon_path.exists():
                cherry_bomb_image = Image.open(cherry_bomb_icon_path)
                cherry_bomb_image = cherry_bomb_image.resize((16, 16), Image.Resampling.LANCZOS)
                self.cherry_bomb_icon_photo = ImageTk.PhotoImage(cherry_bomb_image)
                cherry_bomb_icon_label = tk.Label(cherry_bomb_header_frame, image=self.cherry_bomb_icon_photo, background="#FFF3E0")
                cherry_bomb_icon_label.pack(side=tk.LEFT, padx=(5, 0))
        except:
            pass
        
        # Fragezeichen-Icon für Cherry Bomb Tooltip
        cherry_bomb_help_label = tk.Label(cherry_bomb_header_frame, text="❓", font=("Arial", 8), cursor="hand2", foreground="gray", background="#FFF3E0")
        cherry_bomb_help_label.pack(side=tk.LEFT, padx=(5, 0))

        # Recharge card toggles for Cherry Bomb
        self._create_bomb_recharge_card_buttons(cherry_bomb_header_frame, "cherry_bomb", bg_color="#FFF3E0")
        
        cherry_bomb_info = (
            "Cherry Bomb:\n"
            "• Next bomb click consumes 0 charges\n"
            "• Applies to the ENTIRE dump (all charges at once)\n"
            "• Cherry → Gem Bomb is the highest value interaction\n"
            "• Receives refills from Battery and D20\n"
            "• More Cherry clicks → more free Gem Bomb clicks\n"
            "• Workshop: chance for 3x charges on recharge (stacks on top)"
        )
        self.create_tooltip(cherry_bomb_help_label, cherry_bomb_info)
        
        row += 1
        
        self.create_entry(bomb_frame, "cherry_bomb_recharge_seconds", "  Cherry Bomb Recharge (Seconds):", row, "48.0", bg_color="#FFF3E0")
        row += 1

        self.create_entry(bomb_frame, "cherry_bomb_triple_charge_chance", "  3x Charges Chance (%):", row, "0.0", is_percent=True, bg_color="#FFF3E0")
        row += 1
        
        # Separator
        ttk.Separator(bomb_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # Battery Bomb
        battery_header_frame = tk.Frame(bomb_frame, background="#FFF3E0")
        battery_header_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))
        
        tk.Label(battery_header_frame, text="Battery Bomb:", font=("Arial", 9, "bold"), background="#FFF3E0").pack(side=tk.LEFT)

        # Recharge card toggles for Battery Bomb
        self._create_bomb_recharge_card_buttons(battery_header_frame, "battery_bomb", bg_color="#FFF3E0")
        
        # Versuche, das Battery Bomb Icon zu laden
        try:
            battery_bomb_icon_path = get_resource_path("sprites/common/battery_bomb.png")
            if battery_bomb_icon_path.exists():
                battery_bomb_image = Image.open(battery_bomb_icon_path)
                battery_bomb_image = battery_bomb_image.resize((16, 16), Image.Resampling.LANCZOS)
                self.battery_bomb_icon_photo = ImageTk.PhotoImage(battery_bomb_image)
                battery_bomb_icon_label = tk.Label(battery_header_frame, image=self.battery_bomb_icon_photo, background="#FFF3E0")
                battery_bomb_icon_label.pack(side=tk.LEFT, padx=(5, 0))
        except:
            pass
        
        # Fragezeichen-Icon für Battery Tooltip
        battery_help_label = tk.Label(battery_header_frame, text="❓", font=("Arial", 8), cursor="hand2", foreground="gray", background="#FFF3E0")
        battery_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        battery_info = (
            "Battery Bomb:\n"
            "• Charges 2 random bombs (except itself)\n"
            "• Distributes to (Total Bomb Types - 1) bombs\n"
            "• Can refill Gem Bomb, Cherry, D20, and itself\n"
            "• Creates recursive amplification (more Battery → more refills → more Battery)\n"
            "• 0.1% chance to increase bomb cap by 1 (tooltip only)"
        )
        self.create_tooltip(battery_help_label, battery_info)
        
        row += 1
        
        self.create_entry(bomb_frame, "battery_bomb_recharge_seconds", "  Battery Bomb Recharge (Seconds):", row, "31.0", bg_color="#FFF3E0")
        row += 1
        
        # Separator
        ttk.Separator(bomb_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4
        )
        row += 1
        
        # D20 Bomb
        d20_header_frame = tk.Frame(bomb_frame, background="#FFF3E0")
        d20_header_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))
        
        tk.Label(d20_header_frame, text="D20 Bomb:", font=("Arial", 9, "bold"), background="#FFF3E0").pack(side=tk.LEFT)

        # Recharge card toggles for D20 Bomb
        self._create_bomb_recharge_card_buttons(d20_header_frame, "d20_bomb", bg_color="#FFF3E0")
        
        # Versuche, das D20 Bomb Icon zu laden
        try:
            d20_bomb_icon_path = get_resource_path("sprites/common/d20_bomb.png")
            if d20_bomb_icon_path.exists():
                d20_bomb_image = Image.open(d20_bomb_icon_path)
                d20_bomb_image = d20_bomb_image.resize((16, 16), Image.Resampling.LANCZOS)
                self.d20_bomb_icon_photo = ImageTk.PhotoImage(d20_bomb_image)
                d20_bomb_icon_label = tk.Label(d20_header_frame, image=self.d20_bomb_icon_photo, background="#FFF3E0")
                d20_bomb_icon_label.pack(side=tk.LEFT, padx=(5, 0))
        except:
            pass
        
        # Fragezeichen-Icon für D20 Tooltip
        d20_help_label = tk.Label(d20_header_frame, text="❓", font=("Arial", 8), cursor="hand2", foreground="gray", background="#FFF3E0")
        d20_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        d20_info = (
            "D20 Bomb:\n"
            "• 5% chance to refill other bomb charges\n"
            "• Distributes 42 charges randomly\n"
            "• Charges distributed to (Total Bomb Types - 1) bombs\n"
            "• Can refill Gem Bomb, Cherry, Battery, and itself\n"
            "• Creates recursive amplification (more D20 → more refills → more D20)"
        )
        self.create_tooltip(d20_help_label, d20_info)
        
        row += 1
        
        self.create_entry(bomb_frame, "d20_bomb_recharge_seconds", "  D20 Bomb Recharge (Seconds):", row, "36.0", bg_color="#FFF3E0")
        row += 1
        
        self.create_entry(bomb_frame, "d20_bomb_charges_distributed", "  Charges Distributed:", row, "42", is_int=True, bg_color="#FFF3E0")
        row += 1
        
        self.create_entry(bomb_frame, "d20_bomb_refill_chance", "  Refill Chance (%):", row, "5.0", is_percent=True, bg_color="#FFF3E0")
    
    def open_archaeology_simulator(self):
        """Opens the Archaeology Simulator window"""
        try:
            # Open the Archaeology Simulator window (standalone, no calculator needed)
            ArchaeologySimulatorWindow(self.root)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error opening Archaeology Simulator:\n{str(e)}"
            )
    
    def open_event_simulator(self):
        """Opens the Event Simulator window"""
        try:
            # Open the Event Simulator window
            EventSimulatorWindow(self.root)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error opening Event Simulator:\n{str(e)}"
            )
    
    def open_option_analyzer(self):
        """Öffnet das Lootbug Analyzer Fenster"""
        # Hole aktuelle Parameter und erstelle Calculator
        params = self.get_parameters()
        if params is None:
            messagebox.showwarning(
                "Parameter Error",
                "Bitte stelle sicher, dass alle Parameter korrekt eingegeben sind."
            )
            return
        
        try:
            calculator = FreebieEVCalculator(params)
            # Öffne das Analyzer-Fenster
            LootbugWindow(self.root, calculator)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Fehler beim Öffnen des Lootbug Analyzers:\n{str(e)}"
            )
    
    def create_tooltip(self, widget, text):
        """Creates a modern styled tooltip with rich formatting"""
        _create_tooltip(widget, text)
    
    def create_dynamic_gift_tooltip(self, widget):
        """Creates a modern styled dynamic tooltip for Gift-EV with contributions and percentages"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            
            # Estimate tooltip dimensions
            tooltip_width = 450
            tooltip_height = 280
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            x, y = calculate_tooltip_position(event, tooltip_width, tooltip_height, screen_width, screen_height)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Äußerer Rahmen für Schatten-Effekt
            outer_frame = tk.Frame(
                tooltip,
                background="#2C3E50",
                relief=tk.FLAT,
                borderwidth=0
            )
            outer_frame.pack(padx=2, pady=2)
            
            # Innerer Rahmen mit Inhalt
            inner_frame = tk.Frame(
                outer_frame,
                background="#FFFFFF",
                relief=tk.FLAT,
                borderwidth=0
            )
            inner_frame.pack(padx=1, pady=1)
            
            # Text-Widget für Rich-Text-Formatierung
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
                highlightthickness=0,
                width=60
            )
            
            # Tags für Formatierung
            text_widget.tag_config("header", font=("Arial", 10, "bold"), foreground="#1976D2")
            text_widget.tag_config("subheader", font=("Arial", 9, "bold"))
            text_widget.tag_config("normal", font=("Arial", 9))
            text_widget.tag_config("percentage", font=("Arial", 9), foreground="#2E7D32")
            
            # Header
            text_widget.insert(tk.END, "GIFT-EV Calculation:\n", "header")
            text_widget.insert(tk.END, "• Base Roll: Gems (20-40, 30-65), Skill Shards, Blue Cow, 2× Speed\n", "normal")
            text_widget.insert(tk.END, "• Rare Roll: 1/45 chance for 80-130 Gems\n", "normal")
            text_widget.insert(tk.END, "• Recursive Gifts: 1/40 chance for 3 additional gifts\n", "normal")
            text_widget.insert(tk.END, "• Multipliers: Obelisk × Lucky Multiplier\n", "normal")
            text_widget.insert(tk.END, "• All values are converted to gem-equivalent\n\n", "normal")
            
            # Contributions
            text_widget.insert(tk.END, "Contributions (current values):\n", "subheader")
            
            # Contributions aus den Labels holen (falls bereits berechnet)
            if hasattr(self, 'gift_contrib_labels'):
                total = 0.0
                contrib_values = {}
                
                for key, label in self.gift_contrib_labels.items():
                    value_text = label.cget('text')
                    if value_text and value_text != "" and value_text != "—":
                        try:
                            value = float(value_text.split()[0])
                            contrib_values[key] = value
                            total += value
                        except:
                            pass
                
                if contrib_values:
                    for key, value in contrib_values.items():
                        percentage = (value / total * 100) if total > 0 else 0
                        text_widget.insert(tk.END, f"• {self._get_contrib_label(key)}: ", "normal")
                        text_widget.insert(tk.END, f"{value:.1f} Gems ({percentage:.1f}%)\n", "percentage")
                else:
                    text_widget.insert(tk.END, "(Values will be displayed after calculation)\n", "normal")
            else:
                text_widget.insert(tk.END, "(Values will be displayed after calculation)\n", "normal")
            
            # Höhe anpassen
            text_widget.config(height=text_widget.get("1.0", tk.END).count('\n'))
            text_widget.config(state=tk.DISABLED)  # Read-only
            text_widget.pack()
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _get_contrib_label(self, key):
        """Returns the label for a contribution key"""
        labels = {
            'gems_20_40': 'Gems (20-40)',
            'gems_30_65': 'Gems (30-65)',
            'skill_shards': 'Skill Shards',
            'blue_cow': 'Blue Cow',
            'speed_boost': '2× Speed Boost',
            'rare_gems': 'Rare Roll Gems',
            'recursive_gifts': 'Recursive Gifts'
        }
        return labels.get(key, key)
    
    def create_entry(self, parent, var_name, label_text, row, default_value, is_percent=False, is_int=False, bg_color=None):
        """Creates an input field with label"""
        
        if bg_color:
            tk.Label(parent, text=label_text, background=bg_color).grid(row=row, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        else:
            ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        
        var = tk.StringVar(value=default_value)
        self.vars[var_name] = {'var': var, 'is_percent': is_percent, 'is_int': is_int}
        
        entry = ttk.Entry(parent, textvariable=var, width=10)
        entry.grid(row=row, column=1, sticky=tk.W, pady=2)
        
        # Live-Update: Berechne automatisch bei Änderung (mit Delay)
        var.trace_add('write', lambda *args: self.trigger_auto_calculate())
    
    def create_entry_with_buttons(self, parent, var_name, label_text, row, default_value, is_percent=False, is_int=False, bg_color=None, show_marginal_ev=False):
        """Creates an input field with +/- buttons and optional marginal EV display"""
        
        if bg_color:
            tk.Label(parent, text=label_text, background=bg_color).grid(row=row, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        else:
            ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        
        var = tk.StringVar(value=default_value)
        self.vars[var_name] = {'var': var, 'is_percent': is_percent, 'is_int': is_int}
        
        # Frame für Entry und Buttons
        entry_frame = tk.Frame(parent, background=bg_color if bg_color else parent.cget('background'))
        entry_frame.grid(row=row, column=1, sticky=tk.W, pady=2)
        
        # - Button
        def decrement():
            try:
                current = float(var.get())
                step = 1.0 if not is_int else 1
                new_value = current - step
                if new_value >= 0:  # Prevent negative values
                    if is_int:
                        var.set(str(int(new_value)))
                    else:
                        var.set(str(new_value))
            except ValueError:
                pass
        
        minus_btn = tk.Button(entry_frame, text="-", width=2, command=decrement, font=("Arial", 9, "bold"))
        minus_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        # Entry
        entry = ttk.Entry(entry_frame, textvariable=var, width=6)
        entry.pack(side=tk.LEFT)
        
        # + Button
        def increment():
            try:
                current = float(var.get())
                step = 1.0 if not is_int else 1
                new_value = current + step
                if is_int:
                    var.set(str(int(new_value)))
                else:
                    var.set(str(new_value))
            except ValueError:
                pass
        
        plus_btn = tk.Button(entry_frame, text="+", width=2, command=increment, font=("Arial", 9, "bold"))
        plus_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        # Marginal EV display (for freebie_gems_base)
        if show_marginal_ev:
            # Store reference to the label for updates
            marginal_label = tk.Label(entry_frame, text="", font=("Arial", 8), background=bg_color if bg_color else parent.cget('background'), foreground="#2E7D32")
            marginal_label.pack(side=tk.LEFT, padx=(6, 0))
            self.marginal_ev_label = marginal_label
        
        # Live-Update: Berechne automatisch bei Änderung (mit Delay)
        var.trace_add('write', lambda *args: self.trigger_auto_calculate())
    
    def create_result_section(self, parent):
        """Creates the results display (right side)"""
        
        # Frame für Ergebnisse - kompakteres Padding
        result_frame = ttk.LabelFrame(parent, text="Results", padding="5")
        result_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=0)  # EV Frame (kompakt)
        result_frame.rowconfigure(1, weight=1)  # Chart bekommt den meisten Platz
        
        # EV-Ergebnisse Frame (nur Total und Gift-EV)
        ev_frame = ttk.Frame(result_frame)
        ev_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        ev_frame.columnconfigure(1, weight=1)
        
        # Total
        ttk.Label(ev_frame, text="TOTAL:", font=("Arial", 11, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10), pady=3
        )
        self.total_label = ttk.Label(ev_frame, text="—", font=("Arial", 11, "bold"))
        self.total_label.grid(row=0, column=1, sticky=tk.W, pady=3)
        
        # Separator für Gift-EV - kompakter
        ttk.Separator(ev_frame, orient='horizontal').grid(
            row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(8, 3)
        )
        
        # Gift-EV Sektion mit Hover-Tooltip - kompakter
        gift_header_frame = ttk.Frame(ev_frame)
        gift_header_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))
        
        gift_label = ttk.Label(gift_header_frame, text="Gift-EV (per 1 opened gift):", font=("Arial", 10, "bold"))
        gift_label.pack(side=tk.LEFT)
        
        # Fragezeichen-Icon für Hover-Tooltip
        gift_help_label = tk.Label(gift_header_frame, text="❓", font=("Arial", 9), cursor="hand2", foreground="gray")
        gift_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Tooltip wird dynamisch erstellt (mit Contributions beim Hover)
        self.gift_help_label = gift_help_label
        self.create_dynamic_gift_tooltip(gift_help_label)
        
        ttk.Label(ev_frame, text="Gem-EV per Gift:").grid(
            row=3, column=0, sticky=tk.W, padx=(0, 10), pady=1
        )
        self.gift_ev_label = ttk.Label(ev_frame, text="—", font=("Arial", 11, "bold"))
        self.gift_ev_label.grid(row=3, column=1, sticky=tk.W, pady=1)
        
        # Gift-EV Contributions (für Tooltip, nicht im GUI angezeigt)
        self.gift_contrib_labels = {}
        gift_contrib_text = [
            ("Gems (20-40):", "gems_20_40"),
            ("Gems (30-65):", "gems_30_65"),
            ("Skill Shards:", "skill_shards"),
            ("Blue Cow:", "blue_cow"),
            ("2× Speed Boost:", "speed_boost"),
            ("Rare Roll Gems:", "rare_gems"),
            ("Recursive Gifts:", "recursive_gifts")
        ]
        
        # Gift-EV Contributions Labels (nur für Tooltip, nicht im GUI sichtbar)
        for label_text, key in gift_contrib_text:
            # Labels werden erstellt, aber nicht im GUI angezeigt (für Tooltip-Daten)
            value_label = tk.Label(ev_frame, text="—", font=("Arial", 8))
            self.gift_contrib_labels[key] = value_label
        
        # Bar Chart - nimmt verfügbaren Platz
        if MATPLOTLIB_AVAILABLE:
            chart_frame = ttk.LabelFrame(result_frame, text="Contributions (Bar Chart)", padding="3")
            chart_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
            chart_frame.columnconfigure(0, weight=1)
            chart_frame.rowconfigure(0, weight=1)
            
            # Matplotlib Figure - responsive, passt sich Fenstergröße an
            self.fig = Figure(figsize=(8, 5), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(
                result_frame,
                text="Matplotlib not available.\nBar Chart will not be displayed.",
                foreground="gray"
            ).grid(row=1, column=0, pady=5)
    
    def load_defaults(self):
        """Loads the default values"""
        defaults = GameParameters()
        
        self.vars['freebie_gems_base']['var'].set(str(defaults.freebie_gems_base))
        self.vars['freebie_timer_minutes']['var'].set(str(defaults.freebie_timer_minutes))
        self.vars['freebie_claim_percentage']['var'].set(str(defaults.freebie_claim_percentage))
        self.vars['skill_shard_chance']['var'].set(str(defaults.skill_shard_chance * 100))
        self.vars['skill_shard_value_gems']['var'].set(str(defaults.skill_shard_value_gems))
        # Stonks wird über Checkbox gesteuert, Standard-Werte sind fix
        self.vars['jackpot_chance']['var'].set(str(defaults.jackpot_chance * 100))
        self.vars['jackpot_rolls']['var'].set(str(defaults.jackpot_rolls))
        self.vars['instant_refresh_chance']['var'].set(str(defaults.instant_refresh_chance * 100))
        self.vars['vip_lounge_level']['var'].set(str(defaults.vip_lounge_level))
        # founder_gems_base ist fix (10.0), wird nicht im GUI angezeigt
        self.vars['obelisk_level']['var'].set(str(defaults.obelisk_level))
        # Founder Speed Parameter sind fix (2.0x für 5 Minuten), werden nicht im GUI angezeigt
        # Bombs
        self.vars['free_bomb_chance']['var'].set(str(defaults.free_bomb_chance * 100))
        self.vars['total_bomb_types']['var'].set(str(defaults.total_bomb_types))
        # Gem Bomb
        self.vars['gem_bomb_recharge_seconds']['var'].set(str(defaults.gem_bomb_recharge_seconds))
        self.vars['gem_bomb_gem_chance']['var'].set(str(defaults.gem_bomb_gem_chance * 100))
        # Cherry Bomb
        self.vars['cherry_bomb_recharge_seconds']['var'].set(str(defaults.cherry_bomb_recharge_seconds))
        self.vars['cherry_bomb_triple_charge_chance']['var'].set(str(defaults.cherry_bomb_triple_charge_chance * 100))
        # Battery Bomb
        self.vars['battery_bomb_recharge_seconds']['var'].set(str(defaults.battery_bomb_recharge_seconds))
        # D20 Bomb
        self.vars['d20_bomb_recharge_seconds']['var'].set(str(defaults.d20_bomb_recharge_seconds))
        self.vars['d20_bomb_charges_distributed']['var'].set(str(defaults.d20_bomb_charges_distributed))
        self.vars['d20_bomb_refill_chance']['var'].set(str(defaults.d20_bomb_refill_chance * 100))
        # Founder Bomb
        self.vars['founder_bomb_interval_seconds']['var'].set(str(defaults.founder_bomb_interval_seconds))
        self.vars['founder_bomb_speed_chance']['var'].set(str(defaults.founder_bomb_speed_chance * 100))
        self.vars['founder_bomb_speed_multiplier']['var'].set(str(defaults.founder_bomb_speed_multiplier))
        self.vars['founder_bomb_speed_duration_seconds']['var'].set(str(defaults.founder_bomb_speed_duration_seconds))

        # Recharge card defaults (toggle visuals too)
        for bomb_key, var in getattr(self, 'bomb_recharge_card_vars', {}).items():
            var.set(0)
            self._update_bomb_recharge_card_visuals(bomb_key)
    
    def get_parameters(self):
        """Reads parameters from input fields"""
        try:
            params = {}
            
            for key, info in self.vars.items():
                value = info['var'].get().strip()
                
                if not value:
                    raise ValueError(f"Please enter a value for {key}.")
                
                if info['is_percent']:
                    # Prozent in Dezimal umwandeln
                    params[key] = float(value) / 100.0
                elif info['is_int']:
                    params[key] = int(value)
                else:
                    params[key] = float(value)
            
            # Stonks: Wenn Checkbox deaktiviert, setze Chance auf 0
            # Standard-Werte für Stonks sind immer 1% Chance, 200 Gems
            if hasattr(self, 'stonks_enabled') and not self.stonks_enabled.get():
                params['stonks_chance'] = 0.0
            else:
                params['stonks_chance'] = 0.01  # 1% Chance wenn aktiviert
            params['stonks_bonus_gems'] = 200.0  # Immer 200 Gems Bonus

            # Bomb recharge card levels (0/1/2/3)
            params['gem_bomb_recharge_card_level'] = int(self.bomb_recharge_card_vars.get('gem_bomb', tk.IntVar(value=0)).get())
            params['cherry_bomb_recharge_card_level'] = int(self.bomb_recharge_card_vars.get('cherry_bomb', tk.IntVar(value=0)).get())
            params['battery_bomb_recharge_card_level'] = int(self.bomb_recharge_card_vars.get('battery_bomb', tk.IntVar(value=0)).get())
            params['d20_bomb_recharge_card_level'] = int(self.bomb_recharge_card_vars.get('d20_bomb', tk.IntVar(value=0)).get())
            params['founder_bomb_recharge_card_level'] = int(self.bomb_recharge_card_vars.get('founder_bomb', tk.IntVar(value=0)).get())
            
            return GameParameters(**params)
        
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
            return None

    def _create_bomb_recharge_card_buttons(self, parent, bomb_key: str, bg_color: str):
        """Create Card/Gild/Poly toggles for a bomb's recharge charge multiplier."""
        # Ensure var exists
        if bomb_key not in self.bomb_recharge_card_vars:
            self.bomb_recharge_card_vars[bomb_key] = tk.IntVar(value=0)
        
        # Right-aligned container
        right_frame = tk.Frame(parent, background=bg_color)
        right_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Small label to clarify what the buttons mean
        tk.Label(right_frame, text="Recharge:", font=("Arial", 7), foreground="#888888", background=bg_color).pack(side=tk.LEFT, padx=(0, 4))
        
        card_btn = tk.Label(right_frame, text="Card", font=("Arial", 7),
                            cursor="hand2", foreground="#888888", background=bg_color,
                            padx=3, relief=tk.RAISED, borderwidth=1)
        card_btn.pack(side=tk.LEFT, padx=(0, 2))
        card_btn.bind("<Button-1>", lambda e: self._toggle_bomb_recharge_card(bomb_key, 1))
        
        gilded_btn = tk.Label(right_frame, text="Gild", font=("Arial", 7),
                              cursor="hand2", foreground="#888888", background=bg_color,
                              padx=3, relief=tk.RAISED, borderwidth=1)
        gilded_btn.pack(side=tk.LEFT, padx=(0, 2))
        gilded_btn.bind("<Button-1>", lambda e: self._toggle_bomb_recharge_card(bomb_key, 2))
        
        polychrome_btn = tk.Label(right_frame, text="Poly", font=("Arial", 7),
                                  cursor="hand2", foreground="#888888", background=bg_color,
                                  padx=3, relief=tk.RAISED, borderwidth=1)
        polychrome_btn.pack(side=tk.LEFT)
        polychrome_btn.bind("<Button-1>", lambda e: self._toggle_bomb_recharge_card(bomb_key, 3))
        
        self.bomb_recharge_card_labels[bomb_key] = {
            'card_btn': card_btn,
            'gilded_btn': gilded_btn,
            'polychrome_btn': polychrome_btn,
            'bg_color': bg_color,
        }
        
        self._update_bomb_recharge_card_visuals(bomb_key)

    def _toggle_bomb_recharge_card(self, bomb_key: str, card_level: int):
        """Toggle recharge card for a specific bomb (click same again to disable)."""
        var = self.bomb_recharge_card_vars.get(bomb_key)
        if var is None:
            return
        
        current = int(var.get())
        var.set(0 if current == card_level else card_level)
        self._update_bomb_recharge_card_visuals(bomb_key)
        self.trigger_auto_calculate()

    def _update_bomb_recharge_card_visuals(self, bomb_key: str):
        """Update Card/Gild/Poly button visuals for a bomb."""
        labels = self.bomb_recharge_card_labels.get(bomb_key)
        var = self.bomb_recharge_card_vars.get(bomb_key)
        if not labels or var is None:
            return
        
        bg_color = labels.get('bg_color', '#FFFFFF')
        card_level = int(var.get())
        card_btn = labels.get('card_btn')
        gilded_btn = labels.get('gilded_btn')
        polychrome_btn = labels.get('polychrome_btn')
        
        if card_btn:
            if card_level == 1:
                card_btn.config(text="✓ Card", foreground="#FFFFFF", background="#4CAF50",
                                relief=tk.SUNKEN, borderwidth=2, font=("Arial", 7, "bold"))
            else:
                card_btn.config(text="Card", foreground="#888888", background=bg_color,
                                relief=tk.RAISED, borderwidth=1, font=("Arial", 7))
        
        if gilded_btn:
            if card_level == 2:
                gilded_btn.config(text="✓ Gild", foreground="#000000", background="#FFD700",
                                  relief=tk.SUNKEN, borderwidth=2, font=("Arial", 7, "bold"))
            else:
                gilded_btn.config(text="Gild", foreground="#888888", background=bg_color,
                                  relief=tk.RAISED, borderwidth=1, font=("Arial", 7))
        
        if polychrome_btn:
            if card_level == 3:
                polychrome_btn.config(text="✓ Poly", foreground="#FFFFFF", background="#9C27B0",
                                      relief=tk.SUNKEN, borderwidth=2, font=("Arial", 7, "bold"))
            else:
                polychrome_btn.config(text="Poly", foreground="#888888", background=bg_color,
                                      relief=tk.RAISED, borderwidth=1, font=("Arial", 7))
    
    def update_chart(self, ev, calculator):
        """Updates the bar chart with EV contributions"""
        if not MATPLOTLIB_AVAILABLE or self.fig is None:
            return
        
        # Hole die Aufschlüsselung
        breakdown = calculator.calculate_ev_breakdown()
        
        # Daten für Chart
        # Founder Speed und Founder Gems werden als gestapelte Bars in einer Kategorie dargestellt
        categories = [
            "Gems\n(Basis)",
            "Stonks\nEV",
            "Skill\nShards",
            "Founder\nSupply\nDrop",
            "Gem\nBomb",
            "Founder\nBomb"
        ]
        
        # Gestapelte Bars: Basis, Jackpot, Refresh (Base), Refresh (Jackpot)
        base_values = []
        jackpot_values = []
        refresh_base_values = []
        refresh_jackpot_values = []
        
        # Normale Keys (ohne Founder Speed, Gems, Gem Bomb und Founder Bomb)
        normal_keys = ['gems_base', 'stonks_ev', 'skill_shards_ev']
        
        for key in normal_keys:
            bd = breakdown[key]
            base_values.append(bd['base'])
            jackpot_values.append(bd['jackpot'])
            refresh_base_values.append(bd['refresh_base'])
            refresh_jackpot_values.append(bd['refresh_jackpot'])
        
        # Founder Supply Drop: Speed und Gems separat für die gestapelten Bars
        # Zuerst Speed (unten), dann Gems (oben)
        founder_speed_bd = breakdown['founder_speed_boost']
        founder_gems_bd = breakdown['founder_gems']
        
        # Speed (unten) - wird als Basis für die gestapelte Bar verwendet
        base_values.append(founder_speed_bd['base'])
        jackpot_values.append(founder_speed_bd['jackpot'])
        refresh_base_values.append(founder_speed_bd['refresh_base'])
        refresh_jackpot_values.append(founder_speed_bd['refresh_jackpot'])
        
        # Gem Bomb (nach Founder Supply Drop, vor Founder Bomb)
        gem_bomb_bd = breakdown['gem_bomb_gems']
        base_values.append(gem_bomb_bd['base'])
        jackpot_values.append(gem_bomb_bd['jackpot'])
        refresh_base_values.append(gem_bomb_bd['refresh_base'])
        refresh_jackpot_values.append(gem_bomb_bd['refresh_jackpot'])
        
        # Founder Bomb (nach Gem Bomb)
        founder_bomb_bd = breakdown['founder_bomb_boost']
        base_values.append(founder_bomb_bd['base'])
        jackpot_values.append(founder_bomb_bd['jackpot'])
        refresh_base_values.append(founder_bomb_bd['refresh_base'])
        refresh_jackpot_values.append(founder_bomb_bd['refresh_jackpot'])
        
        # Gems (oben) - wird auf Speed gestapelt
        founder_gems_base = [founder_gems_bd['base']]
        founder_gems_jackpot = [founder_gems_bd['jackpot']]
        founder_gems_refresh_base = [founder_gems_bd['refresh_base']]
        founder_gems_refresh_jackpot = [founder_gems_bd['refresh_jackpot']]
        
        # Prozentanteile berechnen (für normale Bars)
        total = ev['total']
        percentages = [(v / total * 100) if total > 0 else 0 for v in [
            ev['gems_base'],
            ev['stonks_ev'],
            ev['skill_shards_ev']
        ]]
        
        # Founder Supply Drop Prozentanteile (gesamt: Speed + Gems)
        founder_supply_total = ev['founder_speed_boost'] + ev['founder_gems']
        founder_supply_percentage = (founder_supply_total / total * 100) if total > 0 else 0
        percentages.append(founder_supply_percentage)
        
        # Gem Bomb Prozentanteile
        gem_bomb_percentage = (ev['gem_bomb_gems'] / total * 100) if total > 0 else 0
        percentages.append(gem_bomb_percentage)
        
        # Founder Bomb Prozentanteile
        founder_bomb_percentage = (ev['founder_bomb_boost'] / total * 100) if total > 0 else 0
        percentages.append(founder_bomb_percentage)
        
        # Chart aktualisieren
        self.ax.clear()
        
        # Gestapelte Bars erstellen
        x = range(len(categories))
        width = 0.6
        
        # Normale Bars (erste 3 Kategorien: Gems, Stonks, Skill Shards)
        x_normal = x[:3]
        base_values_normal = base_values[:3]
        jackpot_values_normal = jackpot_values[:3]
        refresh_base_values_normal = refresh_base_values[:3]
        refresh_jackpot_values_normal = refresh_jackpot_values[:3]
        
        # Basis (unten) - normale Bars
        bars_base = self.ax.bar(x_normal, base_values_normal, width, label='Base', 
                                color='#2E86AB', edgecolor='black', linewidth=1.0)
        
        # Jackpot (auf Basis) - normale Bars
        bars_jackpot = self.ax.bar(x_normal, jackpot_values_normal, width, bottom=base_values_normal,
                                   label='Jackpot', color='#A23B72', edgecolor='black', 
                                   linewidth=1.0, hatch='///', alpha=0.8)
        
        # Refresh Base (auf Basis+Jackpot) - normale Bars
        bottom_refresh_base_normal = [b + j for b, j in zip(base_values_normal, jackpot_values_normal)]
        bars_refresh_base = self.ax.bar(x_normal, refresh_base_values_normal, width, bottom=bottom_refresh_base_normal,
                                       label='Refresh (Base)', color='#F18F01', edgecolor='black',
                                       linewidth=1.0, hatch='...', alpha=0.8)
        
        # Refresh Jackpot (ganz oben) - normale Bars
        bottom_refresh_jackpot_normal = [b + j + r for b, j, r in zip(base_values_normal, jackpot_values_normal, refresh_base_values_normal)]
        bars_refresh_jackpot_normal = self.ax.bar(x_normal, refresh_jackpot_values_normal, width, bottom=bottom_refresh_jackpot_normal,
                                          label='Refresh (Jackpot)', color='#C73E1D', edgecolor='black',
                                          linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Founder Supply Drop: Speed (unten) und Gems (oben) gestapelt
        x_founder = x[3]  # Index 3: Founder Supply Drop
        
        # Gem Bomb (separate Bar)
        x_gem_bomb = x[4]  # Index 4: Gem Bomb
        
        # Founder Bomb (separate Bar)
        x_bomb = x[5]  # Index 5: Founder Bomb
        
        # Founder Speed - untere gestapelte Bar (wie normale Bars)
        founder_speed_base = base_values[3]
        founder_speed_jackpot = jackpot_values[3]
        founder_speed_refresh_base = refresh_base_values[3]
        founder_speed_refresh_jackpot = refresh_jackpot_values[3]
        
        # Speed-Bars (unten)
        self.ax.bar([x_founder], [founder_speed_base], width, color='#2E86AB', edgecolor='black', linewidth=1.0)
        self.ax.bar([x_founder], [founder_speed_jackpot], width, bottom=[founder_speed_base],
                    color='#A23B72', edgecolor='black', linewidth=1.0, hatch='///', alpha=0.8)
        self.ax.bar([x_founder], [founder_speed_refresh_base], width, bottom=[founder_speed_base + founder_speed_jackpot],
                    color='#F18F01', edgecolor='black', linewidth=1.0, hatch='...', alpha=0.8)
        self.ax.bar([x_founder], [founder_speed_refresh_jackpot], width, 
                    bottom=[founder_speed_base + founder_speed_jackpot + founder_speed_refresh_base],
                    color='#C73E1D', edgecolor='black', linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Founder Gems - obere gestapelte Bar (auf Speed)
        founder_speed_total = founder_speed_base + founder_speed_jackpot + founder_speed_refresh_base + founder_speed_refresh_jackpot
        founder_gems_bottom_base = founder_speed_total
        founder_gems_bottom_jackpot = founder_speed_total + founder_gems_base[0]
        founder_gems_bottom_refresh_base = founder_speed_total + founder_gems_base[0] + founder_gems_jackpot[0]
        
        # Gems-Bars (oben, auf Speed gestapelt)
        self.ax.bar([x_founder], founder_gems_base, width, bottom=[founder_gems_bottom_base],
                    color='#2E86AB', edgecolor='black', linewidth=1.0)
        self.ax.bar([x_founder], founder_gems_jackpot, width, bottom=[founder_gems_bottom_jackpot],
                    color='#A23B72', edgecolor='black', linewidth=1.0, hatch='///', alpha=0.8)
        self.ax.bar([x_founder], founder_gems_refresh_base, width, bottom=[founder_gems_bottom_refresh_base],
                    color='#F18F01', edgecolor='black', linewidth=1.0, hatch='...', alpha=0.8)
        self.ax.bar([x_founder], founder_gems_refresh_jackpot, width,
                    bottom=[founder_gems_bottom_refresh_base + founder_gems_refresh_base[0]],
                    color='#C73E1D', edgecolor='black', linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Gem Bomb Bar (normale gestapelte Bar)
        gem_bomb_base = base_values[4]
        gem_bomb_jackpot = jackpot_values[4]
        gem_bomb_refresh_base = refresh_base_values[4]
        gem_bomb_refresh_jackpot = refresh_jackpot_values[4]
        
        self.ax.bar([x_gem_bomb], [gem_bomb_base], width, color='#2E86AB', edgecolor='black', linewidth=1.0)
        self.ax.bar([x_gem_bomb], [gem_bomb_jackpot], width, bottom=[gem_bomb_base],
                    color='#A23B72', edgecolor='black', linewidth=1.0, hatch='///', alpha=0.8)
        self.ax.bar([x_gem_bomb], [gem_bomb_refresh_base], width, bottom=[gem_bomb_base + gem_bomb_jackpot],
                    color='#F18F01', edgecolor='black', linewidth=1.0, hatch='...', alpha=0.8)
        self.ax.bar([x_gem_bomb], [gem_bomb_refresh_jackpot], width,
                    bottom=[gem_bomb_base + gem_bomb_jackpot + gem_bomb_refresh_base],
                    color='#C73E1D', edgecolor='black', linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Founder Bomb Bar (normale gestapelte Bar)
        founder_bomb_base = base_values[5]
        founder_bomb_jackpot = jackpot_values[5]
        founder_bomb_refresh_base = refresh_base_values[5]
        founder_bomb_refresh_jackpot = refresh_jackpot_values[5]
        
        self.ax.bar([x_bomb], [founder_bomb_base], width, color='#2E86AB', edgecolor='black', linewidth=1.0)
        self.ax.bar([x_bomb], [founder_bomb_jackpot], width, bottom=[founder_bomb_base],
                    color='#A23B72', edgecolor='black', linewidth=1.0, hatch='///', alpha=0.8)
        self.ax.bar([x_bomb], [founder_bomb_refresh_base], width, bottom=[founder_bomb_base + founder_bomb_jackpot],
                    color='#F18F01', edgecolor='black', linewidth=1.0, hatch='...', alpha=0.8)
        self.ax.bar([x_bomb], [founder_bomb_refresh_jackpot], width,
                    bottom=[founder_bomb_base + founder_bomb_jackpot + founder_bomb_refresh_base],
                    color='#C73E1D', edgecolor='black', linewidth=1.0, hatch='xxx', alpha=0.8)
        
        # Werte und Prozentanteile auf Bars anzeigen (ganz oben)
        # Normale Bars (erste 3)
        normal_total_values = [ev['gems_base'], ev['stonks_ev'], ev['skill_shards_ev']]
        
        for i, (total_val, percentage) in enumerate(zip(normal_total_values, percentages[:3])):
            height = base_values[i] + jackpot_values[i] + refresh_base_values[i] + refresh_jackpot_values[i]
            self.ax.text(
                i, height,
                f'{total_val:.1f}\n({percentage:.1f}%)',
                ha='center', va='bottom', fontsize=8, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                         edgecolor='gray', linewidth=0.5)
            )
        
        # Gem Bomb Bar
        gem_bomb_height = base_values[4] + jackpot_values[4] + refresh_base_values[4] + refresh_jackpot_values[4]
        self.ax.text(
            x_gem_bomb, gem_bomb_height,
            f'{ev["gem_bomb_gems"]:.1f}\n({percentages[4]:.1f}%)',
            ha='center', va='bottom', fontsize=8, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                     edgecolor='gray', linewidth=0.5)
        )
        
        # Founder Bomb Bar
        founder_bomb_height = base_values[5] + jackpot_values[5] + refresh_base_values[5] + refresh_jackpot_values[5]
        self.ax.text(
            x_bomb, founder_bomb_height,
            f'{ev["founder_bomb_boost"]:.1f}\n({percentages[5]:.1f}%)',
            ha='center', va='bottom', fontsize=8, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                     edgecolor='gray', linewidth=0.5)
        )
        
        # Founder Supply Drop: Gesamtwert oben, aber auch Speed und Gems separat anzeigen
        founder_supply_total_height = (base_values[3] + jackpot_values[3] + refresh_base_values[3] + refresh_jackpot_values[3] +
                                      founder_gems_base[0] + founder_gems_jackpot[0] + founder_gems_refresh_base[0] + founder_gems_refresh_jackpot[0])
        
        # Gesamtwert oben (Index 3: Founder Supply Drop)
        self.ax.text(
            x_founder, founder_supply_total_height,
            f'{ev["founder_speed_boost"] + ev["founder_gems"]:.1f}\n({percentages[3]:.1f}%)',
            ha='center', va='bottom', fontsize=8, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, 
                     edgecolor='gray', linewidth=0.5)
        )
        
        # Speed-Wert auf dem Speed-Segment (Mitte)
        founder_speed_segment_height = base_values[3] + jackpot_values[3] + refresh_base_values[3] + refresh_jackpot_values[3]
        founder_speed_midpoint = founder_speed_segment_height / 2
        self.ax.text(
            x_founder, founder_speed_midpoint,
            f'Speed:\n{ev["founder_speed_boost"]:.1f}',
            ha='center', va='center', fontsize=7, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='lightblue', alpha=0.7, 
                     edgecolor='blue', linewidth=0.5)
        )
        
        # Gems-Wert auf dem Gems-Segment (oberer Teil)
        founder_gems_segment_height = founder_gems_base[0] + founder_gems_jackpot[0] + founder_gems_refresh_base[0] + founder_gems_refresh_jackpot[0]
        founder_gems_midpoint = founder_speed_segment_height + founder_gems_segment_height / 2
        self.ax.text(
            x_founder, founder_gems_midpoint,
            f'Gems:\n{ev["founder_gems"]:.1f}',
            ha='center', va='center', fontsize=7, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='lightgreen', alpha=0.7, 
                     edgecolor='green', linewidth=0.5)
        )
        
        # X-Achse Labels
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(categories)
        
        # Legende
        self.ax.legend(loc='upper right', fontsize=8, framealpha=0.9)
        
        self.ax.set_ylabel('Gem-Equivalent per Hour', fontsize=10, fontweight='bold')
        self.ax.set_title('EV Contributions', fontsize=12, fontweight='bold', pad=10)
        self.ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Y-Achse bei 0 starten
        self.ax.set_ylim(bottom=0)
        
        # Layout anpassen
        self.fig.tight_layout()
        self.canvas.draw()
    
    def calculate(self):
        """Performs the calculation"""
        params = self.get_parameters()
        if params is None:
            return
        
        try:
            calculator = FreebieEVCalculator(params)
            
            # EV berechnen
            ev = calculator.calculate_total_ev_per_hour()
            
            # Total anzeigen
            self.total_label.config(text=f"{ev['total']:.1f} Gem-Equivalent/h")
            
            # Gift-EV berechnen und anzeigen
            gift_ev = calculator.calculate_gift_ev_per_gift()
            self.gift_ev_label.config(text=f"{gift_ev:.1f} Gems per Gift")
            
            # Gift-EV Contributions anzeigen
            gift_contrib = calculator.calculate_gift_ev_breakdown()
            self.gift_contrib_labels['gems_20_40'].config(text=f"{gift_contrib['gems_20_40']:.1f} Gems")
            self.gift_contrib_labels['gems_30_65'].config(text=f"{gift_contrib['gems_30_65']:.1f} Gems")
            self.gift_contrib_labels['skill_shards'].config(text=f"{gift_contrib['skill_shards']:.1f} Gems")
            self.gift_contrib_labels['blue_cow'].config(text=f"{gift_contrib['blue_cow']:.1f} Gems")
            self.gift_contrib_labels['speed_boost'].config(text=f"{gift_contrib['speed_boost']:.1f} Gems")
            self.gift_contrib_labels['rare_gems'].config(text=f"{gift_contrib['rare_gems']:.1f} Gems")
            self.gift_contrib_labels['recursive_gifts'].config(text=f"{gift_contrib['recursive_gifts']:.1f} Gems")
            
            # Chart aktualisieren
            self.update_chart(ev, calculator)
            
            # Marginal EV berechnen (+1 Freebie Gem)
            if hasattr(self, 'marginal_ev_label'):
                self.update_marginal_ev(params, ev['total'])
        
        except Exception as e:
            # Bei Auto-Calculate keine Fehlermeldung anzeigen, nur bei manueller Berechnung
            if not hasattr(self, '_auto_calculating') or not self._auto_calculating:
                messagebox.showerror("Calculation Error", f"An error occurred:\n{str(e)}")
    
    def update_marginal_ev(self, current_params, current_total_ev):
        """
        Calculates and displays the marginal EV for +1 Freebie Gem.
        
        Args:
            current_params: Current GameParameters
            current_total_ev: Current total EV per hour
        """
        try:
            # Create params with +1 Freebie Gem
            params_plus_one = copy.copy(current_params)
            params_plus_one.freebie_gems_base = current_params.freebie_gems_base + 1.0
            
            # Calculate EV with +1 Gem
            calculator_plus_one = FreebieEVCalculator(params_plus_one)
            ev_plus_one = calculator_plus_one.calculate_total_ev_per_hour()
            
            # Marginal EV = difference
            marginal_ev = ev_plus_one['total'] - current_total_ev
            
            # Update label
            self.marginal_ev_label.config(text=f"+1 Gem = +{marginal_ev:.2f} EV/h")
        except Exception:
            self.marginal_ev_label.config(text="")
    
    def trigger_auto_calculate(self):
        """Triggers an automatic calculation with delay"""
        if not self.auto_calculate_enabled:
            return
        
        # Verhindere mehrere gleichzeitige Berechnungen
        if self.calculation_pending:
            return
        
        self.calculation_pending = True
        
        # Berechne nach 500ms Delay (wenn der Benutzer aufhört zu tippen)
        self.root.after(500, self._perform_auto_calculate)
    
    def _perform_auto_calculate(self):
        """Performs the automatic calculation"""
        self.calculation_pending = False
        self._auto_calculating = True
        try:
            self.calculate()
        finally:
            self._auto_calculating = False


def main():
    """Main function"""
    root = tk.Tk()
    menu = MainMenuWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
