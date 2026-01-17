# ObeliskGemEV Calculator 🎮

An interactive GUI tool for calculating the **Expected Value (EV)** for freebies in the Android game **Idle Obelisk Miner**.

## 📋 Overview

The ObeliskGemEV Calculator helps you calculate the optimal return from various freebie mechanisms in the game. The tool automatically calculates the **Gem-equivalent value per hour** based on all active game mechanics such as jackpots, refresh chains, skill shards, founder drops, and more.

### What is calculated?

- **Total EV per hour** in Gem-equivalent
- **Individual contributions** from all freebie sources
- **Gift-EV** (expected value per opened gift)
- **Multipliers** (rolls, refresh, total)
- **Visual representation** of all contributions as a bar chart

## 🎯 Main Features

### 🎁 **FREEBIE Parameters**

Controls the basic freebie mechanics:
- **Freebie Gems (Base)**: Base gems per roll (default: 9.0)
- **Freebie Timer**: Time between freebies in minutes (default: 7.0)
- **Skill Shards**: Chance (12%) and value (12.5 Gems) per shard
- **Stonks**: Enable/disable stonks bonus (1% chance for +200 Gems)
- **Jackpot**: Chance (5%) and number of additional rolls (default: 5)
- **Instant Refresh**: Chance (5%) for instant refresh (chainable)

### 📦 **FOUNDER SUPPLY DROP**

Calculates returns from founder supply drops:
- **VIP Lounge Level** (1-7): Automatically determines:
  - Drop interval: `60 - 2×(Level-1)` minutes
  - Double drop chance: 12% at Level 2, +6% per level
  - Triple drop chance: 16% at Level 7
- **Obelisk Level**: Used for bonus gem calculations (default: 26)
- **Founder Gems**: Fixed 10 Gems per drop + 1/100 chance for bonus gems
- **Founder Speed Boost**: 2× game speed for 5 minutes per drop (saves time → more freebies)
- **Gift Chance**: 1/1234 chance for 10 gifts per supply drop

### 💣 **FOUNDER BOMB**

Calculates speed boost from founder bombs:
- **Bomb Interval**: Time between bombs in seconds (default: 87.0 = 1:27 min)
- **Bomb Speed**: 10% chance for 2× game speed for 10 seconds
- Purely time-based: Saves time → effectively increases the number of freebies per hour

## 🖥️ GUI Features

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

## 🚀 Installation & Start

### Requirements

```bash
cd ObeliskGemEV
pip install -r requirements.txt
```

### Starting the GUI

**Windows:**
```bash
cd ObeliskGemEV
start_gui.bat
```

**Linux/macOS:**
```bash
cd ObeliskGemEV
python gui.py
```

Or directly:
```bash
python ObeliskGemEV/gui.py
```

## 📊 Example Output

With default parameters, you get approximately:

```
Expected Rolls per Claim:      1.2000
Refresh Multiplier:             1.0526
Total Multiplier:               1.2632

TOTAL:                          148.0 Gem-Eq/h

Gift-EV (per 1 opened gift):    XX.XX Gem-Eq
```

## 🔧 Technical Details

### Calculated EV Contributions

1. **Gems (Base from Rolls)**: Base 9 gems × multipliers
2. **Gems (Stonks EV)**: Expected value from stonks (first roll only)
3. **Skill Shards (Gem-Eq)**: Shard chance × shard value × multipliers
4. **Founder Speed Boost**: Time saved through 2× speed → more freebies → gem-equivalent
5. **Founder Gems**: Direct gem drops from supply drops (incl. double/triple drops)
6. **Founder Bomb Boost**: Time saved through bomb speed boosts

### Multipliers

- **Jackpot**: Average 1.2 rolls per claim (95% × 1 + 5% × 5)
- **Refresh**: Geometric series → 1/(1-0.05) = 1.0526 claims per start-freebie
- **Total**: Jackpot × Refresh = 1.2632

### Speed Boost Calculation

Speed boosts save time, which effectively enables more freebies per hour:
- **Founder Speed**: 2× speed for 5-15 minutes (depending on single/double/triple drop)
- **Bomb Speed**: 2× speed for 10 seconds at 10% chance

The time saved is converted into additional freebies and displayed as gem-equivalent.

## 📝 Notes

- All values are **per hour** and in **Gem-equivalent**
- Calculations are based on current game mechanics (see code for status)
- Parameters can be adjusted at any time if game values change
- **Stonks** can be enabled/disabled via checkbox (for testing/comparisons)

## 📄 License

For personal use when playing Idle Obelisk Miner.

---

**Good luck optimizing your freebie returns! 🎉**
