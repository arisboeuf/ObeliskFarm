# Stargazing Calculator

Simple calculator for stars and super stars per hour based on in-game stats.

## Features

- **Direct Stats Input**: Enter your current stats from the game's stats page
- **Online Calculation**: Calculate stars and super stars per hour when playing manually
- **Offline Calculation**: Calculate stars and super stars per hour when AFK/offline
- **CTRL+F Stars Support**: Automatically accounts for CTRL+F Stars skill (5x offline gains)
- **Auto-Save**: Your configuration persists between sessions

## Usage

1. Open the Stargazing window from the main menu
2. Enter your current stats from the game's Stats page:
   - Multiplier values (x): Enter as shown (e.g., 1.16 for 1.16x)
   - Percentage values (%): Enter as shown (e.g., 25 for 25%)
3. Enable "CTRL+F Stars" checkbox if you have this skill unlocked
4. Click "Calculate" button to update results

## Game Mechanics

### Star Spawn System

- **Base Star Spawn**: 1/50 (2%) per floor clear
- **Base Super Star Spawn**: 1/100 (1%) per spawn event
- **Exclusivity**: At each spawn event, either a Super Star spawns OR a Regular Star spawns (with possible Double/Triple)

### Multipliers

Stars can be multiplied by several effects:
- **Double Star**: 2x stars
- **Triple Star**: 3x stars
- **Supernova**: 10x stars (default)
- **Supergiant**: 3x stars (default)
- **Radiant**: 10x stars
- **All Star Multiplier**: Final multiplier on all stars

### Offline Gains (CTRL+F Stars Skill)

**Star Floor Mechanics:**
- Each star type spawns on 5 different floors
- Without CTRL+F Stars: You catch the star on 1 of 5 floors
- With CTRL+F Stars: You follow the star through all 5 floors

**Offline Gains Formula:**
```
Without CTRL+F Stars:
  offline_gains = auto_catch × spawn_rate × 0.2

With CTRL+F Stars:
  offline_gains = auto_catch × spawn_rate × 1.0
```

The CTRL+F Stars skill multiplies offline gains by **5x** (from 0.2 to 1.0) for both regular Stars and Super Stars.

## Calculations

### Stars per Hour (Online)
```
stars_per_hour = floor_clears_per_minute × 60
                 × star_spawn_chance (2% base)
                 × star_spawn_rate_mult
                 × stars_per_spawn (1-3)
                 × star_multiplier (supernova, supergiant, etc.)
                 × all_star_mult
```

### Stars per Hour (Offline)
```
stars_per_hour_offline = stars_per_hour_online
                         × auto_catch_chance
                         × offline_multiplier (0.2 or 1.0)
```

### Super Stars per Hour

Similar calculation but with Super Star spawn mechanics:
- Super Star spawns are exclusive with Double/Triple Star spawns
- Super Stars have their own multipliers (Supernova, Supergiant, Radiant)

## Technical Notes

### Assumptions

- Effects stack multiplicatively
- Double/Triple star chances are exclusive (you get 1, 2, or 3 regular stars)
- **Super Star spawns are EXCLUSIVE with Double/Triple Star spawns**
- Supernova/Supergiant/Radiant can all apply to the same star
- All Star Multiplier applies as a final multiplier
- **Offline Gains:** Without CTRL+F Stars = 0.2x (1 of 5 floors), With CTRL+F Stars = 1.0x (all 5 floors)

### GUI Implementation Notes

**Important: ttk.Entry with StringVar Binding Issue**

When using `ttk.Entry` with `textvariable=StringVar`, the StringVar may not update reliably when users type into the Entry widget. This is a known issue with ttk widgets in some Tkinter versions.

**Solution:** Use Entry widgets directly without StringVar binding:
- Store Entry widgets in `self.stat_entries` dictionary
- Read values directly with `entry.get()` instead of `var.get()`
- Set values with `entry.delete(0, tk.END)` and `entry.insert(0, value)` instead of `var.set()`

This ensures that user input is always correctly captured and read from the Entry widgets.

## Module Structure

```
stargazing/
├── __init__.py      # Module exports
├── README.md        # This documentation
├── calculator.py    # Star income calculations
└── gui.py          # GUI interface
```
