# Stargazing Optimizer

A calculator and tracker for the Stargazing minigame in Idle Obelisk Miner.

## Features

- **Star Income Calculation**: Calculate stars and super stars per hour based on your stats
- **Direct Stats Input**: Enter your current stats from the game's stats page
- **Upgrade Tracking**: Track upgrade levels to see percentage gains from next upgrades
- **Auto-Catch Analysis**: See how efficient your auto-catch is compared to manual play
- **Floor Clear Rate**: Calculate floors/hour from offline gains data
- **Auto-Save**: Your configuration persists between sessions

## Module Structure

```
stargazing/
├── __init__.py      # Module exports
├── README.md        # This documentation
├── simulator.py     # Main GUI window
├── calculator.py    # Star income calculations
└── data.py          # Star and upgrade definitions
```

## Core Mechanics

### Star Spawn System

| Mechanic | Base Value | Notes |
|----------|------------|-------|
| Star Spawn | 1/50 (2%) | Per floor clear |
| Super Star Spawn | 1/100 (1%) | When a star spawns |

### Multipliers

Stars can be multiplied by several effects:

| Effect | Multiplier | Description |
|--------|------------|-------------|
| Double Star | 2x stars | Chance for 2 stars instead of 1 |
| Triple Star | 3x stars | Chance for 3 stars instead of 1 |
| Supernova | 10x (default) | Multiplies individual stars |
| Supergiant | 3x (default) | Multiplies individual stars |
| Radiant | 10x | Multiplies individual stars |
| All Star Multi | Variable | Final multiplier on all stars |

### Super Star Bonuses

| Effect | Description |
|--------|-------------|
| Triple Super Star | Chance for 3 super stars (from Leo) |
| 10x Super Star | Chance for 10 super stars |
| Super Star Supergiant | Multiplier on super stars |
| Super Star Radiant | Multiplier on super stars |

## Stargazing Upgrades

Upgrades purchased with Stars:

| Upgrade | Effect per Level | Max Level |
|---------|-----------------|-----------|
| Auto-Catch | +4% | 25 |
| Star Spawn Rate | +5% | - |
| Double Star Chance | +5% | - |
| Super Star Spawn Rate | +2% | - |
| Star Supernova Chance | +0.5% | - |
| Super Star 10x Chance | +0.2% | - |
| Star Supergiant Chance | +0.2% | - |
| Super Star Supergiant | +0.15% | - |
| All Star Multiplier | +0.01x | - |
| Super Star Radiant | +0.15% | - |

## Stars (Zodiac & Constellation)

Stars provide passive bonuses. Notable bonuses:

| Star | Key Bonus |
|------|-----------|
| Taurus | Auto-Catch Chance |
| Gemini | Star Spawn Rate |
| Leo | Triple Super Star Chance |
| Virgo | Super Star Spawn Rate |
| Scorpio | All Star Multiplier |
| Sagittarius | Triple Star Chance |
| Hercules | Star Supernova Chance |

## Usage

### Input Your Stats

1. Open the Stargazing window from the main calculator
2. Enter your current stats from the game's Stats page
3. Enter multiplier values as shown (e.g., 1.16 for 1.16x)
4. Enter percentage values as shown (e.g., 25 for 25%)

### Floor Clear Rate

To calculate your floor clear rate:

1. Look at your Offline Gains screen
2. Enter the number of floors cleared
3. Enter the time (hours, minutes, seconds)
4. The calculator computes floors/hour automatically

Example: 2400 floors in 2h 30m = 960 floors/hour

### Upgrade Benefit Display

The upgrade section shows the percentage gain from leveling each upgrade by +1. This helps you decide which upgrade to buy next for maximum efficiency.

## Calculations

### Stars per Hour

```
stars_per_hour = floor_clears_per_hour
                 x star_spawn_chance (2% base)
                 x star_spawn_rate_mult
                 x stars_per_spawn (1-3)
                 x star_multiplier (supernova, supergiant, etc.)
                 x all_star_mult
```

### Super Stars per Hour

```
super_stars_per_hour = star_spawns_per_hour
                       x super_star_spawn_chance (1% base)
                       x super_star_spawn_rate_mult
                       x super_stars_per_spawn (1, 3, or 10)
                       x super_star_multiplier
                       x all_star_mult
```

### Auto-Catch Efficiency

Shows what percentage of manual tapping you achieve through auto-catch:

- 100% = Same as manual (all stars caught)
- 60% = You get 60% of stars, which is 40% slower than manual
- 0% = No auto-catch, must tap manually

## Technical Notes

### Assumptions

- Effects stack multiplicatively
- Double/Triple star chances are exclusive (you get 1, 2, or 3)
- Supernova/Supergiant/Radiant can all apply to the same star
- All Star Multiplier applies as a final multiplier

### Data Sources

Star and upgrade data is based on game mechanics as of January 2026. Values may change with game updates.
