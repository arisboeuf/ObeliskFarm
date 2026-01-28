# ObeliskFarm Calculator

> ⚠️ **Data based on OB32 (Obelisk Level 32)** - All calculations and game data are based on OB32. Results may vary for different progression levels.

An interactive calculator toolkit for the Android game **Idle Obelisk Miner**.

**Core focus: Monte Carlo simulators** that optimize skill point and upgrade distributions across multiple game modes.

## Web App

Use the browser version (no install, cross-platform):

- **OPEN (GitHub Pages)**: [ObeliskFarm (Web)](https://arisboeuf.github.io/ObeliskFarm/)
- **Notes**: runs fully client-side; saves are stored via `localStorage` (per device/browser profile)

## Overview

The ObeliskFarm Calculator provides **Monte Carlo simulators** that optimize skill point and upgrade distributions to maximize your progress. The simulators test thousands of build configurations and rank them by your chosen objective (max stage, XP/hour, fragments/hour, etc.).

### Core: Monte Carlo Simulators

The heart of the toolkit is the **Monte Carlo optimization** system:

- **Archaeology Simulator**
  - Optimizes skill point distribution (STR/AGI/PER/INT/LCK) via MC search.
  - Multiple objectives: max stage reached, XP/hour, or fragments/hour (by fragment type).
  - Tests thousands of stat distributions and breaks ties intelligently (3% threshold, lexicographic tie-break).
  - Saves MC run history with detailed metrics and tie-break reports.
  - Also includes gem upgrades, fragment upgrades, and card configuration.
- **Event Budget Optimizer**
  - Guided Monte Carlo optimizer for the bimonthly event.
  - Optimizes upgrade distribution within your budget to maximize wave progression.
  - Detailed results: wave/time stats, recommended upgrade plan, player stats preview.
  - Saves prestige + upgrade levels automatically.

### Additional Calculators

- **Gem EV Calculator**
  - Calculates **Gem-equivalent per hour** from freebies (base rolls, jackpots, refresh chains, skill shards, stonks, founder drops, bombs, gift-EV).
  - Includes an **overview chart** (stacked contributions).
  - Saves your inputs automatically in the browser.
- **Stargazing Calculator**
  - Calculates **Stars/hour** and **Super Stars/hour**, each for **Online** and **Offline** modes.
  - Supports **CTRL+F Stars** toggle and **auto-catch**.
  - Defensive clamping for probabilities (0..1) to avoid edge-case bugs.

### What is calculated? (Gem EV)

- **Total EV per hour** in Gem-equivalent
- **Individual contributions** from all freebie sources
- **Gift-EV** (expected value per opened gift)
- **Multipliers** (rolls, refresh, total)
- **Visual representation** of all contributions as a bar chart

## Additional Tools

### Lootbug Analyzer
Analyze whether specific gem purchases are worth it based on your current EV/h. Example:
- **2× Game Speed** (15 Gems for 10 minutes) - checks if the additional gem income exceeds the cost.

### Notes on sprites/assets
The web app uses sprite assets from `ObeliskGemEV/sprites/` (copied to `web/public/sprites/` during build).  
If a sprite is missing, the web UI shows a small placeholder.

## Main Features

### FREEBIE Parameters

Controls the basic freebie mechanics:
- **Freebie Gems (Base)**: Base gems per roll (default: 9.0)
- **Freebie Timer**: Time between freebies in minutes (default: 7.0)
- **Skill Shards**: Chance (12%) and value (12.5 Gems) per shard
- **Stonks**: Enable/disable stonks bonus (1% chance for +200 Gems)
- **Jackpot**: Chance (5%) and number of additional rolls (default: 5)
- **Instant Refresh**: Chance (5%) for instant refresh (chainable)

### FOUNDER SUPPLY DROP

Calculates returns from founder supply drops:
- **VIP Lounge Level** (1-7): Automatically determines:
  - Drop interval: `60 - 2×(Level-1)` minutes
  - Double drop chance: 12% at Level 2, +6% per level
  - Triple drop chance: 16% at Level 7
- **Obelisk Level**: Used for bonus gem calculations (individual, based on your progress)
- **Founder Gems**: Fixed 10 Gems per drop + 1/100 chance for bonus gems
- **Founder Speed Boost**: 2× game speed for 5 minutes per drop (saves time → more freebies)
- **Gift Chance**: 1/1234 chance for 10 gifts per supply drop

### BOMBS

Controls all bomb-related mechanics and their gem generation:

#### General
- **Free Bomb Chance**: 16% chance that a bomb click consumes 0 charges (applies to ALL bombs, recursive multiplier → 1.19×)

#### Gem Bomb
- **Recharge Time**: Time between charges in seconds (default: 46.0)
- **Gem Chance**: 3% chance per charge to receive 1 Gem
- Primary gem source from bombs

#### Cherry Bomb
- **Recharge Time**: Time between charges in seconds (default: 48.0)
- **Effect**: Each Cherry Bomb click triggers a FREE Gem Bomb click
- Cherry → Gem Bomb is the highest value bomb interaction

#### Founder Bomb
- **Bomb Interval**: Time between bombs in seconds (default: 87.0 = 1:27 min)
- **Bomb Speed**: 10% chance for 2× game speed for 10 seconds
- Speed boost saves time → effectively increases freebies and bomb clicks per hour

**Note:** 2× Game Speed (from Founder Supply Drop or Founder Bomb) halves ALL bomb recharge times!

## GUI Features

### Live Updates
- **Automatic calculation**: All values are updated immediately when you change a parameter
- **Real-time visualization**: Bar chart shows all contributions in real-time

### Interactive Tooltips
- **❓ Icons**: Hover over the question mark icons for detailed information on each section
- **Gift-EV Tooltip**: Shows detailed breakdown of all gift contributions on hover

### Visualization
- **Bar Chart**: Displays all EV contributions visually (requires Matplotlib)
  - Horizontal bars for each EV item
  - Color coding: Different colors for Freebie (Blue), Founder (Green), and Bomb (Red)
  - Helps quickly compare the relative importance of each income source

### Results Overview
- **Multipliers**: Expected rolls, refresh multiplier, total multiplier
- **EV Contributions**: Detailed breakdown of all individual income sources
- **Total-EV**: Total gem-equivalent per hour (bold highlighted)
- **Gift-EV**: Separate expected value per opened gift

## Run from Source (for developers)

### Web App Development

```bash
cd web
npm install
npm run dev
```

Then open the URL shown in the terminal (usually `http://localhost:5173`).

### Python Tools (optional)

The repository also contains Python tools (`ObeliskGemEV/`):

```bash
cd ObeliskGemEV
pip install -r requirements.txt
python gui.py
```

## Example Output

With default parameters, you get approximately:

```
Expected Rolls per Claim:      1.2000
Refresh Multiplier:             1.0526
Total Multiplier:               1.2632

TOTAL:                          148.0 Gem-Eq/h

Gift-EV (per 1 opened gift):    XX.XX Gem-Eq
```

## Technical Details

### Calculated EV Contributions

1. **Gems (Base from Rolls)**: Base 9 gems × multipliers
2. **Gems (Stonks EV)**: Expected value from stonks (first roll only)
3. **Skill Shards (Gem-Eq)**: Shard chance × shard value × multipliers
4. **Founder Speed Boost**: Time saved through 2× speed → more freebies → gem-equivalent
5. **Founder Gems**: Direct gem drops from supply drops (incl. double/triple drops)
6. **Gem Bomb Gems**: Gems from Gem Bomb clicks (own clicks + Cherry Bomb free clicks) × Free Bomb Chance multiplier
7. **Founder Bomb Boost**: Time saved through bomb speed boosts

### Multipliers

- **Jackpot**: Average 1.2 rolls per claim (95% × 1 + 5% × 5)
- **Refresh**: Geometric series → 1/(1-0.05) = 1.0526 claims per start-freebie
- **Total**: Jackpot × Refresh = 1.2632

### Speed Boost Calculation

Speed boosts save time, which effectively enables more freebies per hour:
- **Founder Speed**: 2× speed for 5-15 minutes (depending on single/double/triple drop)
- **Bomb Speed**: 2× speed for 10 seconds at 10% chance

The time saved is converted into additional freebies and displayed as gem-equivalent.

## Notes

- All values are **per hour** and in **Gem-equivalent**
- Calculations are based on current game mechanics (see code for status)
- Parameters can be adjusted at any time if game values change
- **Stonks** can be enabled/disabled via checkbox (for testing/comparisons)
- All tool windows auto-save their state on close

## Project Structure

```
ObeliskGemEV/
├── gui.py                    # Main GUI application
├── freebie_ev_calculator.py  # Core EV calculations
├── ui_utils.py               # Shared UI utilities
├── archaeology/              # Archaeology Simulator module
│   ├── simulator.py          # Main GUI and calculations
│   ├── block_stats.py        # Block HP/Armor/XP data
│   └── block_spawn_rates.py  # Spawn rates by stage
├── event/                    # Event Simulator module
│   ├── simulator.py          # Main window with mode toggle
│   ├── gui_budget.py         # Budget Optimizer panel
│   ├── gui_love2d.py         # Love2D Simulator panel
│   ├── simulation.py         # Combat simulation logic
│   └── constants.py          # Upgrade data and costs
├── lootbug/                  # Lootbug Analyzer module
│   └── analyzer.py           # Purchase analysis
├── stargazing/               # Stargazing Calculator module
│   ├── gui.py                # Main GUI
│   ├── calculator.py         # Star income calculations
│   └── README.md             # Documentation
├── sprites/                  # UI icons and images
└── save/                     # Auto-saved configurations
```

## License

For personal use when playing Idle Obelisk Miner.

## Credits & Asset Rights

- **Event Simulator (Love2D mode)**: Ported from a Lua/LÖVE2D implementation by **julk** (see `ObeliskGemEV/event/`; original release: `https://github.com/Kommandant-Julk/shminer_event_sim/releases/tag/working`).
- **Idle Obelisk Miner**: Huge credit to the game developers for making a great game.
- **Images / game assets**: All rights to any images/assets originating from the game belong to the game developers/rightsholders. This is a fan-made tool and is not affiliated with the game.
