# Event Simulator Module

Simulates the bimonthly event mechanics in **Idle Obelisk Miner**.  
Ported from Lua/LÖVE2D implementation by julk.

## Module Structure

```
event/
├── __init__.py          # Module exports
├── stats.py             # PlayerStats, EnemyStats dataclasses
├── constants.py         # Upgrade data, costs, prestige requirements
├── simulation.py        # Combat simulation, upgrade application
├── utils.py             # Formatting utilities
├── gui_budget.py        # Budget Optimizer panel (WIP)
├── gui_love2d.py        # Love2D Simulator panel (original port)
├── simulator.py         # Main window with mode toggle
├── main.lua             # Original Lua reference
└── shminerEvent_stripped.lua  # Original Lua reference (stripped)
```

## Files

### `stats.py`
Dataclasses for player and enemy statistics:
- `PlayerStats`: HP, ATK, speeds, crit, block, prestige bonus, etc.
- `EnemyStats`: Base stats and per-wave scaling values

### `constants.py`
All game data constants:
- `UPGRADE_NAMES`: Display names for all upgrades (Tier 1-4)
- `GEM_UPGRADE_NAMES`: Gem upgrade names
- `PRESTIGE_UNLOCKED`: Prestige requirements per upgrade
- `MAX_LEVELS`: Base max levels per upgrade
- `CAP_UPGRADES`: Which upgrade is the "cap upgrade" per tier
- `COSTS`: Base costs per upgrade (scales with 1.25^level)
- `get_prestige_wave_requirement()`: Wave needed for prestige unlock

### `simulation.py`
Core simulation logic:
- `apply_upgrades()`: Apply all upgrades to player/enemy stats
- `simulate_event_run()`: Simulate one complete event run
- `run_full_simulation()`: Monte Carlo simulation (1000 runs)
- `calculate_materials()`: Materials gained from reaching a wave
- `calculate_upgrade_cost()`: Total cost for upgrade levels
- `calculate_total_costs()`: Sum costs per tier
- `get_current_max_level()`: Max level considering cap upgrades
- `get_gem_max_level()`: Max gem upgrade level by prestige

### `utils.py`
Utility functions:
- `format_number()`: Format with k/m/b/t suffixes
- `format_time()`: Format seconds as "Xm Ys"
- `avg_mult()`: Average multiplier from chance-based effects
- `resources_per_minute()`: Resource gain rate calculation

### `gui_budget.py`
Budget Optimizer mode (work in progress):
- Input available materials
- Get optimal upgrade recommendations
- Planned: Time-to-prestige optimization

### `gui_love2d.py`
Original Love2D simulator port:
- Manual upgrade level adjustment
- Live simulation results
- Player/enemy stats display
- Cost comparison tools

### `simulator.py`
Main window:
- Mode toggle between Budget Optimizer and Love2D Simulator
- Manages active panel switching

## Usage

```python
from ObeliskGemEV.event import EventSimulatorWindow

# Open from main GUI
window = EventSimulatorWindow(parent_tk_window)
```

## Game Mechanics

### Upgrade Tiers
- **Tier 1** upgrades cost **Mat 1 (Coins)**
- **Tier 2** upgrades cost **Mat 2**
- **Tier 3** upgrades cost **Mat 3**
- **Tier 4** upgrades cost **Mat 4**

### Material Gain per Wave
Materials are based on triangular numbers:
- Mat 1: Every wave (sum 1..wave)
- Mat 2: Every 5 waves
- Mat 3: Every 10 waves
- Mat 4: Every 15 waves

### Prestige Requirements (estimated)
Wave required = (Prestige + 1) × 5
- P1 → Wave 10
- P2 → Wave 15
- P3 → Wave 20
- ...

### Enemy Scaling per Wave
- HP = base_health + health_scaling × wave
- ATK = max(1, atk + atk_scaling × wave)
- ATK Speed = atk_speed + 0.02 × wave
- Crit Chance = crit + wave
- Crit Dmg = crit_dmg + crit_dmg_scaling × wave
